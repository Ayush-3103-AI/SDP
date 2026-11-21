"""Cached-feature cause models that run on a CPU (exploratory, 2026-11-16; after K2 fired on incomplete crops).

    python scripts/probe_features.py extract [--crops data/crops.csv] [--out data/features.npz] [--batch 64]
    python scripts/probe_features.py fit --head single|multi [--features data/features.npz] [--out DIR]
    then: python scripts/eval_cause.py --model-dir DIR --out reports/cause_eval_<head>_cached.md --errors ""

extract: frozen ImageNet ResNet18 (eval mode, no augmentation) 512-d features for every crop, in crops.csv order.
fit: per fold, a linear head on the fold's train prints (≤ 300 seeded rows per print, as train_cause), its weight
decay chosen on the calib prints by the 9-cause NLL, the test prints predicted once and never used for a choice.
Writes preds_fold<k>.npz in the train_cause format, so eval_cause.py writes the K2 / NFR-005 report.
  single: 9-way soft-max, class-weighted CE on single-cause rows (rung 1 of T-0013 without augmentation).
  multi:  4 heads × {low, good, high} (CAXTON's own formulation), trained on every row including `multi`, each head
          class-weighted. The 9 cause probabilities are the heads' joint probabilities of each single-deviation
          outcome, renormalised: P(none) ∝ Π_v P(good_v), P(v_low) ∝ P(low_v) Π_{u≠v} P(good_u) (heads assumed
          independent given the image).
Image-only (ADR-0002): the model sees crops only; the class columns are targets.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]

from train_cause import CLS_COLS, Crops, class_weights, nll

from xqi.config import load_causes
from xqi.explain.cause_model import HEAD_VARS, joint_to_causes

VARS = list(HEAD_VARS)  # CLS_COLS order; 0 = low, 1 = good, 2 = high
WD_GRID = (1e-4, 1e-3, 1e-2, 1e-1)
MAX_PER_PRINT, STEPS = 300, 300


def extract(crops: pd.DataFrame, batch: int, workers: int) -> np.ndarray:
    from torchvision.models import ResNet18_Weights, resnet18
    net = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
    net.fc = torch.nn.Identity()
    net.eval()
    loader = DataLoader(Crops(crops.crop_path, np.zeros(len(crops), int), 224, aug=False), batch, num_workers=workers)
    out = []
    with torch.no_grad():
        for i, (x, _, _) in enumerate(loader):
            out.append(net(x).numpy())
            if i % 100 == 0:
                print(f"  {i * batch} / {len(crops)}", flush=True)
    return np.concatenate(out).astype(np.float32)


def sample(df: pd.DataFrame, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.concatenate([rng.permutation(ix)[:MAX_PER_PRINT] for ix in df.groupby("trial_id").indices.values()])


def fit_linear(x, targets, weights, wd, n_out):
    """Full-batch L-BFGS on soft-max heads. targets: (n, h) ints; returns a predict fn → (n, h, n_out) probs."""
    torch.manual_seed(0)
    x = torch.from_numpy(x)
    h = targets.shape[1]
    w = torch.zeros(x.shape[1], h * n_out, requires_grad=True)
    b = torch.zeros(h * n_out, requires_grad=True)
    t = torch.from_numpy(targets).long()
    cw = [torch.tensor(c, dtype=torch.float32) for c in weights]
    opt = torch.optim.LBFGS([w, b], max_iter=STEPS, line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        logits = (x @ w + b).view(-1, h, n_out)
        loss = sum(F.cross_entropy(logits[:, k], t[:, k], weight=cw[k]) for k in range(h)) / h
        loss = loss + wd * (w ** 2).sum()
        loss.backward()
        return loss

    opt.step(closure)
    w, b = w.detach(), b.detach()
    return lambda z: torch.softmax((torch.from_numpy(z) @ w + b).view(-1, h, n_out), -1).numpy()


def fit_fold(head, feats, crops, fold, labels, seed, train_keep=None):
    n = len(labels)
    idx = {k: crops.index[crops.trial_id.isin(fold[f"{k}_trials"])].to_numpy() for k in ("train", "calib", "test")}
    train = crops.loc[idx["train"]]
    if train_keep is not None:  # --train-rows: cleaner training targets; calib and test rows untouched
        train = train[train_keep[train.index]]
    if head == "single":
        train = train[train.y >= 0]
    rows = train.index.to_numpy()[sample(train.reset_index(drop=True), seed)]
    mu, sd = feats[rows].mean(0), feats[rows].std(0) + 1e-6
    z = {k: (feats[v] - mu) / sd for k, v in idx.items()}
    zt = (feats[rows] - mu) / sd
    if head == "single":
        y = crops.y.to_numpy()[rows][:, None]
        weights = [class_weights(y[:, 0], n)]
        n_out = n
    else:
        y = crops[CLS_COLS].to_numpy(int)[rows]
        weights = [class_weights(y[:, k], 3) for k in range(4)]
        n_out = 3

    def causes(pred, zz):
        p = pred(zz)
        return p[:, 0] if head == "single" else joint_to_causes(p, labels)

    yc = crops.y.to_numpy()[idx["calib"]]
    best = None
    for wd in WD_GRID:
        pred = fit_linear(zt, y, weights, wd, n_out)
        pc = causes(pred, z["calib"])
        loss = nll(pc[yc >= 0], yc[yc >= 0])
        print(f"    wd {wd:g}: calib nll {loss:.4f} · calib top-1 {(pc[yc >= 0].argmax(1) == yc[yc >= 0]).mean():.3f}")
        if best is None or loss < best[0]:
            best = (loss, wd, pred, pc)
    loss, wd, pred, pc = best
    out = {"probs_calib": pc, "probs_test": causes(pred, z["test"]), "wd": wd, "calib_nll": loss}
    if head == "multi":
        out["heads_test"] = pred(z["test"])
    return idx, out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["extract", "fit"])
    ap.add_argument("--head", choices=["single", "multi"], default="single")
    ap.add_argument("--crops", default="data/crops.csv")
    ap.add_argument("--splits", default="data/splits/logo.json")
    ap.add_argument("--causes", default=str(ROOT / "config" / "causes.yaml"))
    ap.add_argument("--features", default="data/features.npz")
    ap.add_argument("--out")
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--train-rows", help="fit: train only on rows whose (trial_id, ts_s) are in this crops CSV")
    a = ap.parse_args(argv)
    crops = pd.read_csv(a.crops)
    if a.mode == "extract":
        feats = extract(crops, a.batch, a.workers)
        np.savez(a.features, feats=feats, crop_path=crops.crop_path.to_numpy(str))
        print(f"wrote {a.features} {feats.shape}")
        return 0

    d = np.load(a.features)
    if not np.array_equal(d["crop_path"], crops.crop_path.to_numpy(str)):
        print("features.npz rows do not match crops.csv; re-run extract", file=sys.stderr)
        return 2
    feats = d["feats"]
    labels = list(load_causes(a.causes).causes)
    crops["y"] = crops.cause.map({c: i for i, c in enumerate(labels)}).fillna(-1).astype(int)
    folds = json.loads(Path(a.splits).read_text(encoding="utf-8"))["folds"]
    out = Path(a.out or f"models/cause/{a.head}_cached")
    out.mkdir(parents=True, exist_ok=True)
    summary, keep = {}, None
    if a.train_rows:
        rows = pd.read_csv(a.train_rows, usecols=["trial_id", "ts_s"])
        keep = pd.MultiIndex.from_frame(crops[["trial_id", "ts_s"]]).isin(pd.MultiIndex.from_frame(rows))
    for k, fold in enumerate(folds):
        print(f"fold {k} ({a.head})", flush=True)
        idx, r = fit_fold(a.head, feats, crops, fold, labels, a.seed, keep)
        cal, te = crops.loc[idx["calib"]], crops.loc[idx["test"]]
        np.savez(out / f"preds_fold{k}.npz", labels=np.array(labels), probs_calib=r["probs_calib"],
                 y_calib=cal.y.to_numpy(), calib_trial=cal.trial_id.to_numpy(str), calib_ts=cal.ts_s.to_numpy(float),
                 probs_test=r["probs_test"], y_test=te.y.to_numpy(), test_trial=te.trial_id.to_numpy(str),
                 test_ts=te.ts_s.to_numpy(float), test_cls=te[CLS_COLS].to_numpy(int).reshape(-1, 4))
        s = {"wd": r["wd"], "calib_nll": r["calib_nll"]}
        if a.head == "multi":  # per-variable accuracy on every test row (CAXTON's metric), report only
            cls = te[CLS_COLS].to_numpy(int)
            s["var_acc"] = {v: float((r["heads_test"][:, i].argmax(1) == cls[:, i]).mean()) for i, v in enumerate(VARS)}
        summary[f"fold{k}"] = s
        print(f"  {json.dumps(s)}", flush=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
