"""Post-hoc recalibration of saved cause probabilities, fitted on calibration prints only (CPU; 2026-11-21).

    python scripts/recalibrate.py [--model-dir models/cause] [--out-dir models/cause/recal]
        [--report reports/recalibration.md]

Why: train_cause uses class-weighted CE, so its softmax estimates a *balanced* posterior p(y|x)/π(y), and it is
over-confident on new prints (ECE ≈ 0.26). K2 / NFR-005 score plain top-1 against the majority floor, so the
balanced argmax under-predicts the majority cause by design. Per fold, on the fold's calibration prints:

    q(y|x) = softmax(log p(y|x) / T + τ · log π̂(y))     π̂ = calib label frequencies (+1 smoothing)

T and τ minimise calib NLL on a grid (τ = 1, T = 1 undoes class weighting exactly). Writes, in --out-dir, every
preds_*.npz with probs_calib / probs_test replaced (same keys, so eval_cause / eval_conformal / eval_counterfactual
/ eval_proactive read it unchanged) and calibration.json ({name: {T, tau, log_prior}}); the "final" entry is what
CauseModel applies at runtime (cause_model.calibration). The report adds a cross-fit calib top-1 (fit on half
the calib prints, score the other half): the score to compare training recipes by without touching test folds.
--temperature-only fixes τ = 0: honest confidence without moving the argmax towards the majority cause. That is the
runtime card's choice: the prior term raises top-1 against the majority floor by predicting the majority cause more
often (z_offset_high, a manual cause), which helps K2 but tells the operator nothing.
A causal window (mean log-prob of the last k frames of the same print, gap ≤ 10 s) is reported next to it, with k
chosen on calib NLL; the written preds stay per-frame. Test rows are transformed with calib-fitted values only.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from eval_cause import ece

TAUS = np.round(np.arange(0.0, 1.51, 0.125), 3)
TS = np.geomspace(0.5, 8.0, 41)
WINDOWS = (1, 3, 5, 9, 15)
MAX_GAP_S = 10.0


def _log(p: np.ndarray) -> np.ndarray:
    return np.log(np.clip(p.astype(np.float64), 1e-12, None))


def _softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(1, keepdims=True)


def log_prior(y: np.ndarray, n: int) -> np.ndarray:
    c = np.bincount(y[y >= 0], minlength=n) + 1.0
    return np.log(c / c.sum())


def adjust(p: np.ndarray, t: float, tau: float, lp: np.ndarray) -> np.ndarray:
    return _softmax(_log(p) / t + tau * np.asarray(lp)).astype(np.float32)


def nll(p: np.ndarray, y: np.ndarray) -> float:
    return float(-_log(p[np.arange(len(y)), y]).mean())


def fit(p: np.ndarray, y: np.ndarray, lp: np.ndarray, taus=TAUS) -> tuple[float, float]:
    """(T, τ) on the grid with the lowest NLL on (p, y); y has no multi rows."""
    z = _log(p)
    best = (np.inf, 1.0, 0.0)
    for tau in taus:
        for t in TS:
            s = z / t + tau * lp
            m = s.max(1, keepdims=True)
            loss = float((np.log(np.exp(s - m).sum(1)) + m[:, 0] - s[np.arange(len(y)), y]).mean())
            if loss < best[0]:
                best = (loss, float(t), float(tau))
    return best[1], best[2]


def window(p: np.ndarray, trial: np.ndarray, ts: np.ndarray, k: int, max_gap_s: float = MAX_GAP_S) -> np.ndarray:
    """Causal mean of log p over the last k rows of the same print with no gap > max_gap_s (rows in ts order)."""
    lp, out = _log(p), np.empty(p.shape, np.float64)
    start = 0
    for i in range(len(p)):
        if i == 0 or trial[i] != trial[i - 1] or ts[i] - ts[i - 1] > max_gap_s:
            start = i
        out[i] = lp[max(start, i - k + 1): i + 1].mean(0)
    return _softmax(out).astype(np.float32)


def _scores(p, y, floor_cls):
    pred = p.argmax(1)
    rec = [(pred[y == c] == c).mean() for c in np.unique(y)]
    return float((pred == y).mean()), float(np.mean(rec)), float((y == floor_cls).mean())


def cross_fit(p, y, trial, n, taus=TAUS) -> tuple[float, float, float]:
    """Fit on half the calib prints, score the other half, both ways: (top-1, balanced, floor top-1) pooled."""
    prints = np.unique(trial)
    half = np.isin(trial, prints[::2])
    pred, floor = np.empty(len(y), int), np.empty(len(y), bool)
    for a in (half, ~half):
        lp = log_prior(y[a], n)
        t, tau = fit(p[a], y[a], lp, taus)
        pred[~a] = adjust(p[~a], t, tau, lp).argmax(1)
        floor[~a] = y[~a] == lp.argmax()
    rec = [(pred[y == c] == c).mean() for c in np.unique(y)]
    return float((pred == y).mean()), float(np.mean(rec)), float(floor.mean())


def recalibrate(d: dict, taus=TAUS) -> tuple[dict, dict, dict]:
    """One preds npz → (new npz dict, params, report row)."""
    n = len(d["labels"])
    keep = d["y_calib"] >= 0
    pc, yc = d["probs_calib"][keep], d["y_calib"][keep]
    lp = log_prior(yc, n)
    t, tau = fit(pc, yc, lp, taus)
    out = dict(d)
    out["probs_calib"] = adjust(d["probs_calib"], t, tau, lp)
    out["probs_test"] = adjust(d["probs_test"], t, tau, lp) if len(d["probs_test"]) else d["probs_test"]
    qc = out["probs_calib"][keep]
    floor_cls = int(lp.argmax())
    row = {"T": t, "tau": tau, "nll": (nll(pc, yc), nll(qc, yc)), "ece": (ece(pc, yc), ece(qc, yc)),
           "before": _scores(pc, yc, floor_cls), "after": _scores(qc, yc, floor_cls)}
    if "calib_trial" in d:
        tr, ts = d["calib_trial"], d["calib_ts"]
        row["cross"] = cross_fit(pc, yc, tr[keep], n, taus)
        wins = {k: window(out["probs_calib"], tr, ts, k)[keep] for k in WINDOWS}
        k_best = min(WINDOWS, key=lambda k: nll(wins[k], yc))
        row["win"] = (k_best, _scores(wins[k_best], yc, floor_cls))
        yt = d["y_test"]
        if len(yt) and (yt >= 0).any():
            wt = window(out["probs_test"], d["test_trial"], d["test_ts"], k_best)[yt >= 0]
            row["win_test"] = _scores(wt, yt[yt >= 0], floor_cls)[0]
    return out, {"T": t, "tau": tau, "log_prior": lp.tolist()}, row


def render(rows: dict, src: str) -> str:
    lines = ["# Post-hoc recalibration on calibration prints (2026-11-21)", "",
             (f"Source: {src}/preds_*.npz. q = softmax(log p / T + τ·log π̂), (T, τ) by calib NLL; π̂ = calib label "
              "frequencies. Test rows are transformed with these calib-fitted values only (no test choice). "
              "Cross-fit = fit on half the calib prints, score the other half: the recipe-comparison score. "
              "Window = causal mean log-prob of the last k frames (k by calib NLL), report only."), "",
             ("| preds | T | τ | calib NLL | calib ECE | calib top-1 | calib balanced | calib floor | cross-fit top-1 "
              "(− floor) | cross-fit balanced | window k | window calib top-1 | window test top-1 |"),
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, r in rows.items():
        b, a = r["before"], r["after"]
        cross = r.get("cross")
        win = r.get("win")
        lines.append(
            f"| {name} | {r['T']:.2f} | {r['tau']:.3f} | {r['nll'][0]:.3f} → {r['nll'][1]:.3f} | "
            f"{r['ece'][0]:.3f} → {r['ece'][1]:.3f} | {b[0]:.3f} → {a[0]:.3f} | {b[1]:.3f} → {a[1]:.3f} | "
            f"{a[2]:.3f} | "
            + (f"{cross[0]:.3f} ({100 * (cross[0] - cross[2]):+.1f} pp) | {cross[1]:.3f} | " if cross else "– | – | ")
            + (f"{win[0]} | {win[1][0]:.3f} | " if win else "– | – | ")
            + (f"{r['win_test']:.3f} |" if "win_test" in r else "– |"))
    folds = [r for k, r in rows.items() if k.startswith("fold") and "cross" in r]
    if folds:
        gap = np.mean([100 * (r["cross"][0] - r["cross"][2]) for r in folds])
        lines += ["", (f"Mean cross-fit top-1 − floor over {len(folds)} folds: {gap:+.1f} pp; balanced "
                       f"{np.mean([r['cross'][1] for r in folds]):.3f}.")]
    return "\n".join(lines + [""])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", default="models/cause")
    ap.add_argument("--out-dir", default="models/cause/recal")
    ap.add_argument("--report", default="reports/recalibration.md")
    ap.add_argument("--temperature-only", action="store_true",
                    help="τ = 0: calibrated confidence, balanced argmax kept (the runtime card's choice)")
    ap.add_argument("--only", help="crops CSV (e.g. data/crops_clean.csv): calib/test rows not in it get y = −1")
    a = ap.parse_args(argv)
    src, dst = Path(a.model_dir), Path(a.out_dir)
    only = None
    if a.only:
        o = pd.read_csv(a.only, usecols=["trial_id", "ts_s"])
        only = set(zip(o.trial_id, o.ts_s.round(3)))
    files = sorted(src.glob("preds_*.npz"))
    if not files:
        print(f"no preds_*.npz in {src}", file=sys.stderr)
        return 2
    dst.mkdir(parents=True, exist_ok=True)
    params, rows = {}, {}
    for f in files:
        name = f.stem.removeprefix("preds_")
        d = dict(np.load(f))
        if only is not None:  # excluded like multi rows (y = −1) by every eval script
            for s in ("calib", "test"):
                inside = np.array([(t, round(float(x), 3)) in only for t, x in zip(d[f"{s}_trial"], d[f"{s}_ts"])],
                                  bool)
                d[f"y_{s}"] = np.where(inside, d[f"y_{s}"], -1)
        out, params[name], rows[name] = recalibrate(d, (0.0,) if a.temperature_only else TAUS)
        np.savez(dst / f.name, **out)
        print(f"{name}: T {params[name]['T']:.2f} tau {params[name]['tau']:.3f}")
    (dst / "calibration.json").write_text(json.dumps(params, indent=1), encoding="utf-8")
    Path(a.report).parent.mkdir(parents=True, exist_ok=True)
    Path(a.report).write_text(render(rows, src.as_posix()), encoding="utf-8")
    print(f"wrote {dst / 'calibration.json'}, {a.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
