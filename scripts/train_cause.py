"""Train the image-only cause model on the leave-parts-out folds (T-0012, T-0013; 08 P5, 09 §Data).

    python scripts/train_cause.py --overfit 20                     # Gate 3 sanity check, before any fold run
    python scripts/train_cause.py --fold 0 [--freeze-backbone]     # one fold (G2: both rungs on fold 0)
    python scripts/train_cause.py --all [--freeze-backbone]        # every fold (G3)
    python scripts/train_cause.py --final [--freeze-backbone]      # runtime model: every print, 20 % calib split
    common: [--crops data/crops.csv] [--splits data/splits/logo.json] [--out DIR] [--epochs 15] [--batch 32]
            [--seed 0] [--limit N] [--max-per-print 300] [--workers 4] [--px 224] [--device cuda:0] [--no-pretrained]

Rungs (Gate 2): --freeze-backbone = rung 1, the frozen-backbone probe (out: models/cause/probe); without it = rung 4,
the full fine-tune (out: models/cause/finetune). --final writes to models/cause (the runtime path).
Per fold: AdamW lr 3e-4 wd 1e-4, class-weighted CE (weights from the fold's train prints only), aug = colour jitter
0.2 + random resized crop (0.8–1.0) + hflip (no vertical flip), ≤ max-per-print images per print per epoch, early
stop on calib loss (patience 3), use_defect=false. AMP on CUDA; a CUDA OOM halves the batch and restarts the fold.
Writes <out>/fold<k>.pt (best calib loss, via save_checkpoint), fold<k>.log, fold<k>.json and preds_fold<k>.npz
(every calib + test image incl. `multi` rows, in ts order). A fold-0 run rewrites --report from every rung found
next to <out>. Test predictions are written and reported, never used for a choice (no tuning on test).
Checkpoints are the Gate 5 dict (state_dict, use_defect, causes, rung, input_px, normalisation, sha256 of logo.json
and crops.csv, git SHA, seed, config, metrics). --final also writes the golden fixture (--golden, 8 calib crops and
the model's CPU probabilities) that tests/test_cause_artifact.py checks.
"""
import argparse
import hashlib
import json
import random
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset, Subset
from torchvision.transforms import v2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from xqi.config import load_causes
from xqi.explain.cause_model import (
    _MEAN,
    _STD,
    CauseModel,
    build_model,
    save_checkpoint,
    train_one_epoch,
)
from xqi.types import DEFECTS

CLS_COLS = ["flow_cls", "speed_cls", "z_cls", "nozzle_cls"]  # 09 §Data test_cls order
LR, WD, PATIENCE, CALIB_FRAC, OVERFIT_STEPS, OVERFIT_LOSS = 3e-4, 1e-4, 3, 0.2, 100, 0.05
RUNGS = ("probe", "finetune")


class Crops(Dataset):
    """(x, defect=0, y) from crop files, preprocessed exactly like CauseModel.predict (+ aug when training)."""

    def __init__(self, paths, y, px: int, aug: bool):
        self.paths, self.y, self.px = list(paths), torch.tensor(np.asarray(y)), px
        self.aug = v2.Compose([v2.ColorJitter(0.2, 0.2, 0.2), v2.RandomResizedCrop(px, scale=(0.8, 1.0)),
                               v2.RandomHorizontalFlip()]) if aug else None
        self.mean, self.std = torch.from_numpy(_MEAN)[:, None, None], torch.from_numpy(_STD)[:, None, None]

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, i):
        img = cv2.imread(self.paths[i])
        if img is None:
            raise FileNotFoundError(self.paths[i])
        rgb = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), (self.px, self.px), interpolation=cv2.INTER_AREA)
        x = torch.from_numpy(np.ascontiguousarray(rgb.transpose(2, 0, 1))).float() / 255
        if self.aug is not None:
            x = self.aug(x)
        return (x - self.mean) / self.std, 0, self.y[i]


def class_weights(y: np.ndarray, n: int) -> np.ndarray:
    """Balanced CE weights n_images / (classes present · count); classes absent from train get 0."""
    c = np.bincount(y, minlength=n).astype(float)
    return np.where(c > 0, c.sum() / ((c > 0).sum() * np.maximum(c, 1)), 0.0)


def epoch_sample(df: pd.DataFrame, max_per_print: int, rng) -> np.ndarray:
    """Positional indices: at most max_per_print random rows per print (P5), so long prints don't dominate."""
    return np.concatenate([rng.permutation(ix)[:max_per_print] for ix in df.groupby("trial_id").indices.values()])


def make_model(n_causes: int, freeze: bool, pretrained: bool):
    model = build_model(n_causes, 0, pretrained=pretrained)
    if freeze:  # ponytail: backbone weights frozen, BN statistics still adapt in train mode (probe, not pure)
        model.backbone.requires_grad_(False)
    return model


def predict(model, df: pd.DataFrame, a, device, n: int) -> np.ndarray:
    if df.empty:
        return np.zeros((0, n), np.float32)
    loader = DataLoader(Crops(df.crop_path, df.y, a.px, aug=False), a.batch, num_workers=a.workers)
    model.eval()
    out = []
    with torch.no_grad(), torch.autocast(device.type, enabled=device.type == "cuda"):
        for x, d, _ in loader:
            out.append(torch.softmax(model(x.to(device), d.to(device)).float(), 1).cpu())
    return torch.cat(out).numpy().astype(np.float32)


def nll(p: np.ndarray, y: np.ndarray) -> float:
    return float(-np.log(np.clip(p[np.arange(len(y)), y], 1e-12, None)).mean())


def fit(train, calib, n, a, device, log):
    """Train until early stop on calib loss; returns (model at the best calib loss, curve)."""
    torch.manual_seed(a.seed)
    model = make_model(n, a.freeze_backbone, not a.no_pretrained).to(device)
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=LR, weight_decay=WD)
    scaler = torch.amp.GradScaler("cuda") if device.type == "cuda" else None
    weights = torch.tensor(class_weights(train.y.to_numpy(), n), dtype=torch.float32)
    ds = Crops(train.crop_path, train.y, a.px, aug=True)
    rng = np.random.default_rng(a.seed)
    best, best_loss, bad, curve = None, float("inf"), 0, []
    for epoch in range(1, a.epochs + 1):
        t0 = time.monotonic()
        idx = epoch_sample(train, a.max_per_print, rng)
        loader = DataLoader(Subset(ds, idx), a.batch, shuffle=True, num_workers=a.workers,
                            drop_last=len(idx) > a.batch, generator=torch.Generator().manual_seed(a.seed + epoch))
        loss, acc = train_one_epoch(model, loader, opt, weights, scaler)
        p = predict(model, calib, a, device, n)
        cal_loss, cal_acc = nll(p, calib.y.to_numpy()), float((p.argmax(1) == calib.y.to_numpy()).mean())
        curve.append({"epoch": epoch, "train_loss": loss, "train_acc": acc, "calib_loss": cal_loss,
                      "calib_acc": cal_acc, "s": round(time.monotonic() - t0, 1)})
        log(f"epoch {epoch}: train loss {loss:.4f} acc {acc:.3f} · calib loss {cal_loss:.4f} acc {cal_acc:.3f} · "
            f"{curve[-1]['s']} s · batch {a.batch}")
        if cal_loss < best_loss:
            best, best_loss, bad = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}, cal_loss, 0
        else:
            bad += 1
            if bad >= PATIENCE:
                log(f"early stop: calib loss has not improved for {PATIENCE} epochs")
                break
    model.load_state_dict(best)
    return model, curve


def fit_halving(train, calib, n, a, device, log):
    while True:
        try:
            return fit(train, calib, n, a, device, log)
        except torch.cuda.OutOfMemoryError:
            if a.batch <= 4:
                raise
            a.batch //= 2
            torch.cuda.empty_cache()
            log(f"CUDA OOM: halving the batch to {a.batch} and restarting the fold")


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_sha() -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False)
    return r.stdout.strip() or "unknown"


def rows(df: pd.DataFrame, trials, a) -> pd.DataFrame:
    """The split's rows in (print, ts) order; --limit keeps a seeded sample of at most N rows."""
    out = df[df.trial_id.isin(trials)]
    if a.limit:
        out = out.sample(n=min(a.limit, len(out)), random_state=a.seed)
    return out.sort_values(["trial_id", "ts_s"], kind="stable").reset_index(drop=True)


def run(name, train, calib, test, labels, a, device, meta, out: Path) -> dict:
    """Train one split and write <name>.pt / .log / .json and preds_<name>.npz."""
    out.mkdir(parents=True, exist_ok=True)
    n = len(labels)
    with open(out / f"{name}.log", "w", encoding="utf-8") as fh:
        def log(msg):
            print(msg, flush=True)
            fh.write(msg + "\n")
            fh.flush()

        log(json.dumps(meta))
        train, cal_y = train[train.y >= 0], calib[calib.y >= 0]
        log(f"{name}: train {len(train)} crops in {train.trial_id.nunique()} prints · calib {len(cal_y)} · "
            f"test {len(test)} (incl. multi) · device {device}")
        model, curve = fit_halving(train, cal_y, n, a, device, log)
        p_cal, p_test = predict(model, calib, a, device, n), predict(model, test, a, device, n)
        np.savez(out / f"preds_{name}.npz", labels=np.array(labels), probs_calib=p_cal, y_calib=calib.y.to_numpy(),
                 calib_trial=calib.trial_id.to_numpy(str), calib_ts=calib.ts_s.to_numpy(float), probs_test=p_test,
                 y_test=test.y.to_numpy(), test_trial=test.trial_id.to_numpy(str), test_ts=test.ts_s.to_numpy(float),
                 test_cls=test[CLS_COLS].to_numpy(int).reshape(-1, 4))
        y_t, t = test.y.to_numpy(), test.y.to_numpy() >= 0
        floor = np.bincount(train.y, minlength=n).argmax()
        top3 = np.argsort(-p_test[t], axis=1)[:, :3] if t.any() else np.zeros((0, 3), int)
        summary = {"name": name, "rung": meta["rung"], "curve": curve, "batch": a.batch,
                   "floor_cause": labels[floor], "floor_top1": float((y_t[t] == floor).mean()) if t.any() else None,
                   "test_top1": float((p_test[t].argmax(1) == y_t[t]).mean()) if t.any() else None,
                   "test_top3": float((top3 == y_t[t][:, None]).any(1).mean()) if t.any() else None}
        (out / f"{name}.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
        best = min(curve, key=lambda c: c["calib_loss"])
        metrics = {"calib_loss": best["calib_loss"], "calib_top1": best["calib_acc"], "epochs": len(curve),
                   **{k: summary[k] for k in ("test_top1", "test_top3", "floor_top1")}}
        save_checkpoint(model, out / f"{name}.pt", **meta, causes=list(labels), input_px=a.px, metrics=metrics,
                        normalisation={"mean": _MEAN.tolist(), "std": _STD.tolist()})  # Gate 5 artifact dict
        log(f"{name}: test top-1 {summary['test_top1']} · floor top-1 {summary['floor_top1']} ({labels[floor]})")
    return summary


def write_golden(calib: pd.DataFrame, labels, weights: Path, px: int, golden: Path, n: int = 8) -> None:
    """Gate 5 golden fixture: n calib crops (round-robin over causes) + the shipped model's CPU probabilities."""
    queues = [list(zip(g.crop_path, g.cause)) for _, g in calib[calib.y >= 0].groupby("y")]
    picks = []
    while len(picks) < n and any(queues):
        picks += [q.pop(0) for q in queues if q][: n - len(picks)]
    model = CauseModel(weights, labels, DEFECTS, "cpu", input_px=px)
    golden.mkdir(parents=True, exist_ok=True)
    crops = []
    for i, (src, cause) in enumerate(picks):
        img = cv2.imread(src)
        name = f"{i}_{cause}.png"  # lossless, so the test reads the exact pixels
        cv2.imwrite(str(golden / name), img)
        probs = model.predict(img, "unknown").probs
        crops.append({"file": name, "cause": cause, "source": Path(src).as_posix(),
                      "probs": [probs[c] for c in labels]})
    (golden / "expected.json").write_text(json.dumps({"weights": "models/cause/final.pt", "causes": list(labels),
                                                      "input_px": px, "crops": crops}, indent=1), encoding="utf-8")
    print(f"wrote {golden} ({len(crops)} crops)")


def diagnosis(s: dict) -> str:
    """One automatic line per rung; the human edits it after reading the curves."""
    last = s["curve"][-1]
    if last["train_acc"] < s["floor_top1"] + 0.05:
        return "underfit: train top-1 is within 5 pp of the floor; climb a rung or check the labels"
    if last["train_acc"] - last["calib_acc"] > 0.15:
        return (f"overfit / part shift: train {last['train_acc']:.3f} vs calib {last['calib_acc']:.3f}; "
                "more augmentation or fewer epochs")
    return f"fits; test top-1 = floor {100 * (s['test_top1'] - s['floor_top1']):+.1f} pp"


def write_fold0_report(root: Path, path: Path) -> None:
    found = [json.loads((root / r / "fold0.json").read_text(encoding="utf-8")) for r in RUNGS
             if (root / r / "fold0.json").exists()]
    lines = ["# Cause model, fold 0: early read on A3 (T-0012)", "",
             ("Rung 1 = frozen-backbone probe, rung 4 = full fine-tune (08 P5, Gate 2). Floor = the fold-0 training "
              "majority cause predicted for every test image."), "",
             "| rung | epochs | best calib loss | test top-1 | test top-3 | floor top-1 | gap to floor (pp) |",
             "|---|---|---|---|---|---|---|"]
    for s in found:
        lines.append(f"| {s['rung']} | {len(s['curve'])} | {min(c['calib_loss'] for c in s['curve']):.4f} | "
                     f"{s['test_top1']:.3f} | {s['test_top3']:.3f} | {s['floor_top1']:.3f} ({s['floor_cause']}) | "
                     f"{100 * (s['test_top1'] - s['floor_top1']):+.1f} |")
    for s in found:
        lines += ["", f"## {s['rung']}", "", f"Diagnosis (auto; edit after reading the curve): {diagnosis(s)}", "",
                  "| epoch | train loss | train acc | calib loss | calib acc | s |", "|---|---|---|---|---|---|"]
        lines += [f"| {c['epoch']} | {c['train_loss']:.4f} | {c['train_acc']:.3f} | {c['calib_loss']:.4f} | "
                  f"{c['calib_acc']:.3f} | {c['s']} |" for c in s["curve"]]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines + [""]), encoding="utf-8")
    print(f"wrote {path}")


def overfit(train: pd.DataFrame, n: int, a, device) -> bool:
    """Gate 3: full-batch training on N crops (no aug) must reach train loss < 0.05 within 100 steps."""
    sub = train[train.y >= 0].sample(n=min(a.overfit, int((train.y >= 0).sum())), random_state=a.seed)
    ds = Crops(sub.crop_path, sub.y, a.px, aug=False)
    x = torch.stack([ds[i][0] for i in range(len(ds))]).to(device)
    y = torch.tensor(sub.y.to_numpy()).to(device)
    torch.manual_seed(a.seed)
    model = make_model(n, a.freeze_backbone, not a.no_pretrained).to(device).train()
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=LR, weight_decay=WD)
    for step in range(1, OVERFIT_STEPS + 1):
        loss = F.cross_entropy(model(x), y)
        opt.zero_grad()
        loss.backward()
        opt.step()
        if loss.item() < OVERFIT_LOSS:
            print(f"overfit: PASS (train loss {loss.item():.4f} at step {step} on {len(sub)} crops)")
            return True
    print(f"overfit: FAIL (train loss {loss.item():.4f} after {OVERFIT_STEPS} steps on {len(sub)} crops)")
    return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fold", type=int)
    mode.add_argument("--all", action="store_true")
    mode.add_argument("--final", action="store_true")
    mode.add_argument("--overfit", type=int, metavar="N")
    ap.add_argument("--crops", default="data/crops.csv")
    ap.add_argument("--splits", default="data/splits/logo.json")
    ap.add_argument("--causes", default=str(ROOT / "config" / "causes.yaml"))
    ap.add_argument("--out", help="default: models/cause/probe | models/cause/finetune; --final: models/cause")
    ap.add_argument("--report", default="reports/cause_fold0.md", help="rewritten after a fold-0 run")
    ap.add_argument("--golden", default="tests/fixtures/cause_golden", help="--final writes the golden fixture here")
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--limit", type=int, help="at most N crops per split (smoke runs)")
    ap.add_argument("--max-per-print", type=int, default=300)
    ap.add_argument("--freeze-backbone", action="store_true", help="rung 1: train the head only")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--px", type=int, default=224)
    ap.add_argument("--device", default="cuda:0" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--no-pretrained", action="store_true", help="random init (tests; no weight download)")
    a = ap.parse_args(argv)

    random.seed(a.seed)
    np.random.seed(a.seed)
    torch.manual_seed(a.seed)
    torch.backends.cudnn.benchmark = True  # deterministic off for speed (P5); the seed is recorded
    device = torch.device(a.device)
    rung = RUNGS[0] if a.freeze_backbone else RUNGS[1]
    out = Path(a.out or ("models/cause" if a.final else f"models/cause/{rung}"))
    labels = list(load_causes(a.causes).causes)
    crops = pd.read_csv(a.crops)
    crops["y"] = crops.cause.map({c: i for i, c in enumerate(labels)}).fillna(-1).astype(int)
    unknown = crops[(crops.y < 0) & (crops.cause != "multi")]
    if len(unknown):
        print(f"{len(unknown)} crops have a cause outside causes.yaml; treated like multi (not trained or scored)")
    folds = json.loads(Path(a.splits).read_text(encoding="utf-8"))["folds"]

    if a.overfit:
        return 0 if overfit(rows(crops, folds[0]["train_trials"], a), len(labels), a, device) else 1

    meta = {"seed": a.seed, "config": {k: v for k, v in vars(a).items()}, "git_sha": git_sha(), "rung": rung,
            "sha256": {"logo.json": sha256(a.splits), "crops.csv": sha256(a.crops)}}
    if a.final:
        prints = sorted({t for f in folds[:1] for k in ("train_trials", "calib_trials", "test_trials") for t in f[k]})
        random.Random(a.seed).shuffle(prints)
        n_cal = max(1, round(CALIB_FRAC * len(prints)))
        calib = rows(crops, prints[:n_cal], a)
        run("final", rows(crops, prints[n_cal:], a), calib, rows(crops, [], a), labels, a, device, meta, out)
        write_golden(calib, labels, out / "final.pt", a.px, Path(a.golden))
        return 0
    for k in range(len(folds)) if a.all else [a.fold]:
        f = folds[k]
        meta["config"]["fold"] = k
        run(f"fold{k}", rows(crops, f["train_trials"], a), rows(crops, f["calib_trials"], a),
            rows(crops, f["test_trials"], a), labels, a, device, meta, out)
        if k == 0:
            write_fold0_report(out.parent, Path(a.report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
