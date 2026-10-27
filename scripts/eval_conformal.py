"""Conformal coverage on the leave-parts-out folds and the runtime qhat (T-0015; 07 §8, NFR-006).

    python scripts/eval_conformal.py [--model-dir models/cause] [--config config/default.yaml]
        [--out reports/conformal.md] [--qhat models/cause/qhat.json]

Per fold (preds_fold<k>.npz, 09 §Data): qhat from probs_calib / y_calib (the fold's calibration prints are training
prints, ADR-0009), then coverage and mean set size on the test prints at α ∈ {0.05, 0.10, 0.20}; `multi` rows
(y = −1) excluded. Set-size histogram and per-cause coverage at the config α, pooled over folds. qhat.json comes from
preds_final.npz at the config α, in the load_qhat format. Line 1 is the NFR-006 verdict (α = 0.10, mean over folds).
CPU only.
"""
import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from eval_cause import load_preds

from xqi.config import load
from xqi.explain.conformal import calibrate, save_qhat

ALPHAS = (0.05, 0.10, 0.20)
NFR006_ALPHA, NFR006_COVERAGE, NFR006_SIZE = 0.10, 0.85, 2.0


def sets(probs: np.ndarray, qhat: float) -> np.ndarray:
    """Boolean [n, K] membership, the same comparison as conformal.predict_set (ties inclusive)."""
    return 1.0 - probs <= qhat


def evaluate(npz: dict, alpha: float) -> dict:
    cal, test = npz["y_calib"] >= 0, npz["y_test"] >= 0
    qhat = calibrate(npz["probs_calib"][cal], npz["y_calib"][cal], alpha)
    member = sets(npz["probs_test"][test], qhat)
    y = npz["y_test"][test]
    covered = member[np.arange(len(y)), y]
    return {"qhat": qhat, "n_calib": int(cal.sum()), "n_test": int(test.sum()), "coverage": float(covered.mean()),
            "size": float(member.sum(1).mean()), "covered": covered, "sizes": member.sum(1), "y": y}


def fold_results(model_dir: Path, alphas=ALPHAS) -> list[tuple[int, dict]]:
    return [(k, {a: evaluate(npz, a) for a in alphas}) for k, npz in load_preds(model_dir)]


def _table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return out + ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]


def render(folds, labels, alpha: float, model_dir, qhat_line: str) -> str:
    mean = {a: (np.mean([r[a]["coverage"] for _, r in folds]), np.mean([r[a]["size"] for _, r in folds]))
            for a in ALPHAS}
    cov, size = mean[NFR006_ALPHA]
    ok = cov >= NFR006_COVERAGE and size <= NFR006_SIZE
    lines = [(f"NFR-006: {'PASS' if ok else 'FAIL'} (coverage {cov:.3f}, need ≥ {NFR006_COVERAGE}; mean set size "
              f"{size:.2f}, need ≤ {NFR006_SIZE}; α = {NFR006_ALPHA}, mean over {len(folds)} folds)"), "",
             "# Conformal coverage on the leave-parts-out folds (T-0015)", "",
             (f"Predictions: {model_dir}/preds_fold*.npz. qhat per fold from its calibration prints (training prints); "
              "coverage on its held-out test prints; `multi` rows excluded. Leave-parts-out is a shift, so the "
              "1 − α guarantee does not hold: these are empirical values (07 §8)."), "", "## Per fold", ""]
    lines += _table(["fold", "α", "calib images", "qhat", "test images", "coverage", "mean set size"],
                    [(k, a, r[a]["n_calib"], f"{r[a]['qhat']:.4f}", r[a]["n_test"], f"{r[a]['coverage']:.3f}",
                      f"{r[a]['size']:.2f}") for k, r in folds for a in ALPHAS])
    lines += ["", "## Mean over folds", ""]
    lines += _table(["α", "target 1 − α", "coverage", "mean set size"],
                    [(a, f"{1 - a:.2f}", f"{c:.3f}", f"{s:.2f}") for a, (c, s) in mean.items()])
    sizes = np.concatenate([r[alpha]["sizes"] for _, r in folds])
    lines += ["", f"## Set sizes at α = {alpha} (pooled)", ""]
    lines += _table(["set size", "test images", "share"],
                    [(s, int((sizes == s).sum()), f"{(sizes == s).mean():.3f}") for s in range(len(labels) + 1)
                     if (sizes == s).any()])
    y = np.concatenate([r[alpha]["y"] for _, r in folds])
    covered = np.concatenate([r[alpha]["covered"] for _, r in folds])
    lines += ["", f"## Coverage per cause at α = {alpha} (pooled)", ""]
    lines += _table(["cause", "test images", "coverage"],
                    [(c, int((y == i).sum()), f"{covered[y == i].mean():.3f}" if (y == i).any() else "–")
                     for i, c in enumerate(labels)])
    lines += ["", "## Runtime qhat", "", qhat_line, ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", default="models/cause")
    ap.add_argument("--config", default=str(ROOT / "config" / "default.yaml"))
    ap.add_argument("--out", default="reports/conformal.md")
    ap.add_argument("--qhat", help="default: the config's conformal.qhat_file")
    a = ap.parse_args(argv)
    cfg = load(a.config)
    alpha, model_dir = cfg.conformal.alpha, Path(a.model_dir)
    preds = load_preds(model_dir)
    if not preds:
        print(f"no preds_fold*.npz in {model_dir}", file=sys.stderr)
        return 1
    folds = fold_results(model_dir, sorted({*ALPHAS, alpha}))
    final = model_dir / "preds_final.npz"
    if final.exists():
        npz = np.load(final)
        cal = npz["y_calib"] >= 0
        qhat, n = calibrate(npz["probs_calib"][cal], npz["y_calib"][cal], alpha), int(cal.sum())
        qhat_path = Path(a.qhat or cfg.conformal.qhat_file)
        save_qhat(qhat_path, qhat, alpha, n)
        qhat_line = f"{qhat_path}: qhat = {qhat:.4f} at α = {alpha} from {n} calibration images of {final}."
    else:
        qhat_line = f"{final} not found: qhat.json not written (run train_cause.py --final first)."
    print(qhat_line)
    text = render(folds, [str(x) for x in preds[0][1]["labels"]], alpha, model_dir, qhat_line)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text.splitlines()[0])
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
