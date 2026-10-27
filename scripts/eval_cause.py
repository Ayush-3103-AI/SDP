"""Cause-model evaluation: the majority floor and the per-fold report with the K2 line (T-0010; 07 §9, 06 §Baseline).

    python scripts/eval_cause.py --floor [--crops data/crops.csv] [--splits data/splits/logo.json]
        [--out reports/cause_floor.md]
    python scripts/eval_cause.py --model-dir models/cause [--crops ...] [--splits ...] [--out reports/cause_eval.md]

Floor = the fold's training-print majority cause, predicted for every test image (top-3 = the three most frequent).
The model report reads preds_fold<k>.npz (09 §Data); `multi` rows (y = −1) and causes outside the npz labels are
excluded. CIs: bootstrap over test prints (B = 1000, percentile 95 %), stratified by fold for the mean. Line 1 is the
K2 verdict (charter: K2 fires when the leave-parts-out mean top-1 ≤ floor + 5 pp).
"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from xqi.config import load_causes

K2_PP, B = 5, 1000


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
    return {"probs": probs, "y": y, "trial": trial, "labels": labels,
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


def render_model(folds: list[tuple[int, dict]], model_dir: str) -> str:
    rows = []
    for k, m in folds:
        lo, hi = bootstrap([(m["top1"], m["trial"])])
        rows.append((k, len(np.unique(m["trial"])), len(m["y"]), f"{m['top1'].mean():.3f}", f"[{lo:.3f}, {hi:.3f}]",
                     f"{m['top3'].mean():.3f}", f"{m['floor1'].mean():.3f}", f"{m['floor3'].mean():.3f}",
                     f"{100 * (m['top1'].mean() - m['floor1'].mean()):+.1f}", f"{ece(m['probs'], m['y']):.3f}"))
    t1 = [m["top1"].mean() for _, m in folds]
    f1 = [m["floor1"].mean() for _, m in folds]
    lo, hi = bootstrap([(m["top1"], m["trial"]) for _, m in folds])
    ms = [m for _, m in folds]
    lines = [k2_line(np.mean(t1), np.mean(f1)), "", "# Cause model evaluation (T-0010)", "",
             f"Predictions: {model_dir}/preds_fold*.npz ({len(folds)} folds; `multi` rows excluded)", "",
             "## Per fold", ""]
    lines += _table(["fold", "test prints", "test images", "top-1", "95 % CI", "top-3", "floor top-1", "floor top-3",
                     "gap to floor (pp)", "ECE"], rows)
    lines.append(f"| mean ± std | {sum(r[1] for r in rows)} | {sum(r[2] for r in rows)} | {_ms(t1)} | "
                 f"[{lo:.3f}, {hi:.3f}] | {_ms([m['top3'].mean() for m in ms])} | {_ms(f1)} | "
                 f"{_ms([m['floor3'].mean() for m in ms])} | {100 * (np.mean(t1) - np.mean(f1)):+.1f} | "
                 f"{_ms([ece(m['probs'], m['y']) for m in ms])} |")
    labels = ms[0]["labels"]
    y = np.concatenate([m["y"] for m in ms])
    pred = np.concatenate([m["probs"].argmax(1) for m in ms])
    cm = np.zeros((len(labels), len(labels)), int)
    np.add.at(cm, (y, pred), 1)
    lines += ["", "## Per-class recall (pooled over folds)", ""]
    lines += _table(["cause", "test images", "recall"],
                    [(c, cm[i].sum(), f"{cm[i, i] / cm[i].sum():.3f}" if cm[i].sum() else "–")
                     for i, c in enumerate(labels)])
    lines += ["", "## Confusion matrix (pooled; rows = true, columns = predicted)", ""]
    lines += _table(["true \\ pred", *labels], [(c, *cm[i]) for i, c in enumerate(labels)])
    return "\n".join(lines + [""])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--floor", action="store_true", help="majority-cause floor per fold")
    mode.add_argument("--model-dir", help="folder with preds_fold<k>.npz")
    ap.add_argument("--crops", default="data/crops.csv")
    ap.add_argument("--splits", default="data/splits/logo.json")
    ap.add_argument("--causes", default=str(ROOT / "config" / "causes.yaml"))
    ap.add_argument("--out", help="default: reports/cause_floor.md (--floor) or reports/cause_eval.md")
    a = ap.parse_args(argv)
    crops = pd.read_csv(a.crops)
    splits = json.loads(Path(a.splits).read_text(encoding="utf-8"))
    if a.floor:
        text = render_floor(crops, splits, list(load_causes(a.causes).causes), a.crops)
        out = Path(a.out or "reports/cause_floor.md")
    else:
        preds = load_preds(Path(a.model_dir))
        if not preds:
            print(f"no preds_fold*.npz in {a.model_dir}", file=sys.stderr)
            return 1
        text = render_model([(k, fold_metrics(npz, splits["folds"][k], crops)) for k, npz in preds], a.model_dir)
        out = Path(a.out or "reports/cause_eval.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text.splitlines()[0])
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
