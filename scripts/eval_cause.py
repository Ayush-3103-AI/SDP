"""Cause-model evaluation: the majority floor and the per-fold report with the K2 line (T-0010, T-0013; 07 §9).

    python scripts/eval_cause.py --floor [--crops data/crops.csv] [--splits data/splits/logo.json]
        [--out reports/cause_floor.md]
    python scripts/eval_cause.py --model-dir models/cause/finetune [--probe-dir models/cause/probe]
        [--copy-to models/cause] [--errors reports/cause_errors.png] [--crops ...] [--splits ...]
        [--out reports/cause_eval.md]

Floor = the fold's training-print majority cause, predicted for every test image (top-3 = the three most frequent).
The model report reads preds_fold<k>.npz (09 §Data); `multi` rows (y = −1) and causes outside the npz labels are
excluded. CIs: bootstrap over test prints (B = 1000, percentile 95 %), stratified by fold for the mean. Line 1 is the
K2 verdict (charter: K2 fires when the leave-parts-out mean top-1 ≤ floor + 5 pp); then the NFR-005 line.
With --probe-dir the rung rule picks the reported rung, and --copy-to copies its preds to the runtime folder.
Any fold top-1 > 0.98 → "suspected leakage" on line 2, exit code 3, nothing copied.
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from xqi.config import load_causes
from xqi.explain import cause_model

K2_PP, B, LEAK = 5, 1000, 0.98
NFR005_PP, NFR005_TOP3 = 10, 0.90


def topk(probs: np.ndarray, y: np.ndarray, k: int) -> np.ndarray:
    """Per image: 1.0 if y is among the k largest probs."""
    top = np.argsort(-probs, axis=1, kind="stable")[:, :k]
    return (top == y[:, None]).any(1).astype(float)


def bootstrap(folds, b: int = B, seed: int = 0) -> tuple[float, float]:
    """95 % CI of the mean over folds of per-fold accuracy; folds = [(correct, print_ids)], prints resampled per fold."""
    rng = np.random.default_rng(seed)
    means = np.zeros(b)
    for correct, groups in folds:
        _, g = np.unique(groups, return_inverse=True)
        s, n = np.bincount(g, correct), np.bincount(g)
        idx = rng.integers(0, len(n), (b, len(n)))
        means += s[idx].sum(1) / n[idx].sum(1)
    lo, hi = np.percentile(means / len(folds), [2.5, 97.5])
    return float(lo), float(hi)


def ece(probs: np.ndarray, y: np.ndarray, bins: int = 15) -> float:
    """Expected calibration error of the top-1 confidence, equal-width bins."""
    conf, right = probs.max(1), (probs.argmax(1) == y).astype(float)
    b = np.minimum((conf * bins).astype(int), bins - 1)
    return float(sum(abs(right[b == i].mean() - conf[b == i].mean()) * (b == i).mean()
                     for i in range(bins) if (b == i).any()))


def train_rank(crops: pd.DataFrame, fold: dict, labels) -> list[str]:
    """Labels by training-print frequency, most frequent first (ties in label order)."""
    c = crops[crops.trial_id.isin(fold["train_trials"])].cause.value_counts()
    counts = np.array([c.get(label, 0) for label in labels])
    return [labels[i] for i in np.argsort(-counts, kind="stable")]


def load_preds(model_dir: Path) -> list[tuple[int, dict]]:
    files = sorted(model_dir.glob("preds_fold*.npz"), key=lambda p: int(re.search(r"\d+", p.stem).group()))
    return [(int(re.search(r"\d+", p.stem).group()), dict(np.load(p))) for p in files]


def fold_metrics(npz: dict, fold: dict, crops: pd.DataFrame) -> dict:
    labels = [str(x) for x in npz["labels"]]
    keep = npz["y_test"] >= 0
    probs, y, trial = npz["probs_test"][keep], npz["y_test"][keep], npz["test_trial"][keep]
    rank = [labels.index(c) for c in train_rank(crops, fold, labels)]
    return {"probs": probs, "y": y, "trial": trial, "ts": npz["test_ts"][keep], "labels": labels,
            "top1": topk(probs, y, 1), "top3": topk(probs, y, 3),
            "floor1": (y == rank[0]).astype(float), "floor3": np.isin(y, rank[:3]).astype(float)}


def _table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return out + ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]


def _ms(x) -> str:
    return f"{np.mean(x):.3f} ± {np.std(x):.3f}"


def k2_line(top1: float, floor1: float) -> str:
    gap = 100 * (top1 - floor1)
    if gap > K2_PP:
        return f"K2: PASS (top-1 = floor + {gap:.1f} pp)"
    return f"K2: FAIL (top-1 = floor + {gap:.1f} pp ≤ {K2_PP} pp)"


def render_floor(crops: pd.DataFrame, splits: dict, labels, src: str) -> str:
    crops = crops[crops.cause.isin(labels)]
    rows, t1, t3, n = [], [], [], 0
    for k, fold in enumerate(splits["folds"]):
        rank = train_rank(crops, fold, labels)
        test = crops[crops.trial_id.isin(fold["test_trials"])].cause
        a1, a3 = (test == rank[0]).mean(), test.isin(rank[:3]).mean()
        rows.append((k, rank[0], ", ".join(rank[:3]), len(test), f"{a1:.3f}", f"{a3:.3f}"))
        t1, t3, n = t1 + [a1], t3 + [a3], n + len(test)
    lines = ["# Cause floor (T-0010)", "", f"Input: {src}", "",
             ("Floor = the fold's training-print majority cause, predicted for every test image (07 §9); top-3 = the "
              "three most frequent training causes. `multi` rows are excluded."), ""]
    lines += _table(["fold", "majority", "top-3 causes", "test images", "top-1", "top-3"], rows)
    lines += [f"| mean ± std | | | {n} | {_ms(t1)} | {_ms(t3)} |", ""]
    return "\n".join(lines)


def choose_rung(finetune_top1, probe_top1) -> str:
    """T-0013 rung rule: the fine-tune only if its mean top-1 beats the probe's by more than the probe's fold std."""
    return "finetune" if np.mean(finetune_top1) - np.mean(probe_top1) > np.std(probe_top1) else "probe"


def nfr005_line(top1: float, floor1: float, top3: float, ci) -> str:
    gap = 100 * (top1 - floor1)
    ok = gap >= NFR005_PP and top3 >= NFR005_TOP3
    return (f"NFR-005: {'PASS' if ok else 'FAIL'} (top-1 = floor + {gap:.1f} pp, need ≥ {NFR005_PP}; 95 % CI "
            f"[{ci[0]:.3f}, {ci[1]:.3f}]; top-3 = {top3:.3f}, need ≥ {NFR005_TOP3})")


def errors_png(folds, crops: pd.DataFrame, path: Path, n: int = 20) -> int:
    """Grid of the n most confident wrong test crops (pooled over folds); returns how many it drew."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    where = {(t, float(s)): p for t, s, p in zip(crops.trial_id, crops.ts_s, crops.crop_path)}
    wrong = sorted(((m["probs"][i].max(), m["trial"][i], float(m["ts"][i]), m["labels"][m["y"][i]],
                     m["labels"][m["probs"][i].argmax()]) for _, m in folds for i in np.flatnonzero(m["top1"] == 0)),
                   key=lambda w: -w[0])[:n]
    fig, axes = plt.subplots(4, 5, figsize=(12, 10.5))
    for ax in axes.flat:
        ax.axis("off")
    for ax, (p, trial, ts, true, pred) in zip(axes.flat, wrong):
        img = cv2.imread(str(where.get((trial, ts), "")))
        if img is not None:
            ax.imshow(img[..., ::-1])
        ax.set_title(f"{trial} t={ts:g}s\ntrue {true}\npred {pred} ({p:.2f})", fontsize=7)
    fig.suptitle(f"{len(wrong)} most confident wrong test crops")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=100)
    plt.close(fig)
    return len(wrong)


def frame() -> list[str]:
    """The Gate 0 frame, quoted from the cause model's docstring (T-0011 keeps it in one place)."""
    return cause_model.__doc__.split("Gate 0 frame:\n")[1].split("\n\n")[0].splitlines()


def render_model(folds: list[tuple[int, dict]], model_dir: str, rung_line: str | None = None):
    """(report text, the first fold with top-1 > LEAK or None)."""
    rows = []
    for k, m in folds:
        lo, hi = bootstrap([(m["top1"], m["trial"])])
        rows.append((k, len(np.unique(m["trial"])), len(m["y"]), f"{m['top1'].mean():.3f}", f"[{lo:.3f}, {hi:.3f}]",
                     f"{m['top3'].mean():.3f}", f"{m['floor1'].mean():.3f}", f"{m['floor3'].mean():.3f}",
                     f"{100 * (m['top1'].mean() - m['floor1'].mean()):+.1f}", f"{1 - m['top1'].mean():.3f}",
                     f"{ece(m['probs'], m['y']):.3f}"))
    t1 = [m["top1"].mean() for _, m in folds]
    f1 = [m["floor1"].mean() for _, m in folds]
    ci = bootstrap([(m["top1"], m["trial"]) for _, m in folds])
    ms = [m for _, m in folds]
    t3 = [m["top3"].mean() for m in ms]
    leak = next((k for k, m in folds if m["top1"].mean() > LEAK), None)
    lines = [k2_line(np.mean(t1), np.mean(f1))]
    if leak is not None:
        lines.append(f"suspected leakage: fold {leak} top-1 = {t1[[k for k, _ in folds].index(leak)]:.3f} > {LEAK}. "
                     "Stop: check that no print is in both train and test before reading anything else.")
    lines += [nfr005_line(np.mean(t1), np.mean(f1), np.mean(t3), ci), "", "# Cause model evaluation (T-0010, T-0013)",
              "", "## Frame", "", *frame(), "", "## Baseline", "",
              ("Floor = the fold's training-print majority cause, predicted for every test image (07 §9; "
               "reports/cause_floor.md). Oracle = the CAXTON parameter class (top-1 = 1.0), so gap to oracle = "
               "1 − top-1. K2 fires at ≤ floor + 5 pp (charter); NFR-005 needs ≥ floor + 10 pp and top-3 ≥ 0.90."),
              "", "## Model", "", (f"Predictions: {model_dir}/preds_fold*.npz ({len(folds)} folds; `multi` rows "
                                   "excluded). CIs: bootstrap over test prints (B = 1000), stratified by fold.")]
    if rung_line:
        lines += ["", rung_line]
    for k, _ in folds:
        summary = Path(model_dir) / f"fold{k}.json"
        if summary.exists():
            s = json.loads(summary.read_text(encoding="utf-8"))
            lines.append(f"- fold {k}: {len(s['curve'])} epochs, batch {s['batch']}, best calib loss "
                         f"{min(c['calib_loss'] for c in s['curve']):.4f}")
    lines += ["", "## Result", "", "### Per fold", ""]
    lines += _table(["fold", "test prints", "test images", "top-1", "95 % CI", "top-3", "floor top-1", "floor top-3",
                     "gap to floor (pp)", "gap to oracle", "ECE"], rows)
    lines.append(f"| mean ± std | {sum(r[1] for r in rows)} | {sum(r[2] for r in rows)} | {_ms(t1)} | "
                 f"[{ci[0]:.3f}, {ci[1]:.3f}] | {_ms(t3)} | {_ms(f1)} | "
                 f"{_ms([m['floor3'].mean() for m in ms])} | {100 * (np.mean(t1) - np.mean(f1)):+.1f} | "
                 f"{1 - np.mean(t1):.3f} | {_ms([ece(m['probs'], m['y']) for m in ms])} |")
    labels = ms[0]["labels"]
    y = np.concatenate([m["y"] for m in ms])
    pred = np.concatenate([m["probs"].argmax(1) for m in ms])
    cm = np.zeros((len(labels), len(labels)), int)
    np.add.at(cm, (y, pred), 1)
    lines += ["", "### Per-class recall (pooled over folds)", ""]
    lines += _table(["cause", "test images", "recall"],
                    [(c, cm[i].sum(), f"{cm[i, i] / cm[i].sum():.3f}" if cm[i].sum() else "–")
                     for i, c in enumerate(labels)])
    lines += ["", "### Confusion matrix (pooled; rows = true, columns = predicted)", ""]
    lines += _table(["true \\ pred", *labels], [(c, *cm[i]) for i, c in enumerate(labels)])
    lines += ["", "## Risks", "",
              ("- Most confident wrong test crops: reports/cause_errors.png. What the reviewer saw: <fill in after "
               "looking: e.g. mislabelled transition frames, nozzle out of the crop, blur>"),
              ("- Staleness: trained on CAXTON's nozzle close-up camera, its printer and PLA. A new printer, camera "
               "pose or zoom, or material is a new distribution: re-run T-0013 on its data before trusting top-1 "
               "(NFR-005) or the conformal coverage (T-0015)."),
              "- Within-print leakage reference (random-by-image split on fold 0, SHOULD): not run.", ""]
    return "\n".join(lines), leak


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--floor", action="store_true", help="majority-cause floor per fold")
    mode.add_argument("--model-dir", help="folder with preds_fold<k>.npz")
    ap.add_argument("--crops", default="data/crops.csv")
    ap.add_argument("--splits", default="data/splits/logo.json")
    ap.add_argument("--causes", default=str(ROOT / "config" / "causes.yaml"))
    ap.add_argument("--probe-dir", help="rung 1 preds; the rung rule picks between it and --model-dir (fine-tune)")
    ap.add_argument("--copy-to", help="copy the chosen rung's preds_fold*.npz here (the runtime folder)")
    ap.add_argument("--errors", default="reports/cause_errors.png", help="most confident wrong test crops")
    ap.add_argument("--out", help="default: reports/cause_floor.md (--floor) or reports/cause_eval.md")
    a = ap.parse_args(argv)
    crops = pd.read_csv(a.crops)
    splits = json.loads(Path(a.splits).read_text(encoding="utf-8"))
    if a.floor:
        text = render_floor(crops, splits, list(load_causes(a.causes).causes), a.crops)
        write(Path(a.out or "reports/cause_floor.md"), text)
        return 0

    dirs = {"finetune": a.model_dir, **({"probe": a.probe_dir} if a.probe_dir else {})}
    folds = {}
    for rung, d in dirs.items():
        preds = load_preds(Path(d))
        if not preds:
            print(f"no preds_fold*.npz in {d}", file=sys.stderr)
            return 1
        folds[rung] = [(k, fold_metrics(npz, splits["folds"][k], crops)) for k, npz in preds]
    rung, rung_line = "finetune", None
    if a.probe_dir:
        ft, pr = ([m["top1"].mean() for _, m in folds[r]] for r in ("finetune", "probe"))
        rung = choose_rung(ft, pr)
        rung_line = (f"Rung: {rung} (fine-tune mean top-1 {np.mean(ft):.3f} vs probe {_ms(pr)}; the fine-tune is "
                     "chosen only if it beats the probe by more than the probe's fold std)")
    text, leak = render_model(folds[rung], dirs[rung], rung_line)
    out = Path(a.out or "reports/cause_eval.md")
    write(out, text)
    if a.errors and {"crop_path", "ts_s"} <= set(crops.columns):
        print(f"wrote {a.errors} ({errors_png(folds[rung], crops, Path(a.errors))} crops)")
    if leak is not None:
        print(text.splitlines()[1], file=sys.stderr)
        return 3
    if a.copy_to:
        Path(a.copy_to).mkdir(parents=True, exist_ok=True)
        for k, _ in folds[rung]:
            shutil.copy2(Path(dirs[rung]) / f"preds_fold{k}.npz", Path(a.copy_to) / f"preds_fold{k}.npz")
        print(f"copied the {rung} preds to {a.copy_to}")
    if a.probe_dir:
        print(f"rung: {rung}. Next: uv run python scripts/train_cause.py --final"
              + (" --freeze-backbone" if rung == "probe" else ""))
    return 0


def write(out: Path, text: str) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text.splitlines()[0])
    print(f"wrote {out}")


if __name__ == "__main__":
    sys.exit(main())
