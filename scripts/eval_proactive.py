"""Proactive early warning on the held-out prints (T-0063; 07 §13, §14; NFR-012).

    python scripts/eval_proactive.py [--model-dir models/cause] [--crops data/crops.csv]
        [--config config/default.yaml] [--out reports/proactive.md]

Per fold (preds_fold<k>.npz, 09 §Data): every print's per-image probabilities are replayed in ts order through
xqi.proactive.EarlyWarning (the config's proactive settings). D(i) = the image's non-good class columns as causes
(07 §15); test prints use test_cls, calibration prints the class columns of crops.csv joined on (trial_id, ts_s)
(the npz has no calib_cls). θ_on is picked from GRID on the fold's calibration prints only (smallest θ_on with ≤ 1
false warning per print-hour; none qualifies → fewest false/h, then lower median time-to-warning), then applied once
to its test prints. The floor is the same rule with β = 0. preds_final.npz's calibration prints give the runtime θ_on
(reported, not written). Line 1 is the NFR-012 verdict, pooled over the folds' test prints. CPU only.
"""
import argparse
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from eval_cause import load_preds
from train_cause import CLS_COLS

from xqi.config import load
from xqi.proactive import EarlyWarning

GRID = (0.5, 0.6, 0.7, 0.8)
CLS_CAUSE = ("flow", "speed", "z_offset", "nozzle_temp")  # CLS_COLS order, 07 §15 names
WINDOW_S, SETTLE_S = 30.0, 6.0
NFR012_TTW, NFR012_RECALL, NFR012_RATE = 10.0, 0.70, 1.0


def deviations(cls_row) -> frozenset:
    return frozenset(f"{c}_{'low' if k == 0 else 'high'}" for c, k in zip(CLS_CAUSE, cls_row) if k != 1)


def evaluate_print(ts, probs, cls, labels, pcfg) -> dict:
    """onsets = [(cause, t_b, ttw | None)], false = [cause per counted false warning], hours of printing."""
    ew, onsets, false, prev = EarlyWarning(labels, pcfg), {}, [], None
    for t, p, row in zip(ts, probs, cls):
        d = deviations(row)
        if d != prev:
            start = float(t)
            for c in sorted(d - (prev or frozenset())):
                onsets[(c, start)] = None
            prev = d
        for w in ew.update(float(t), dict(zip(labels, p))):
            key = (w.cause, start)
            if w.cause not in d:
                if t - start >= SETTLE_S:
                    false.append(w.cause)
            elif key in onsets and onsets[key] is None and t - start <= WINDOW_S:
                onsets[key] = float(t) - start
    hours = float(ts[-1] - ts[0]) / 3600 if len(ts) else 0.0
    return {"onsets": [(c, tb, ttw) for (c, tb), ttw in onsets.items()], "false": false, "hours": hours}


def summarize(results, cause=None) -> dict:
    ons = [o for r in results for o in r["onsets"] if cause in (None, o[0])]
    ttw = [o[2] for o in ons if o[2] is not None]
    n_false = sum(cause in (None, c) for r in results for c in r["false"])
    hours = sum(r["hours"] for r in results)
    return {"onsets": len(ons), "warned": len(ttw), "median": float(np.median(ttw)) if ttw else float("nan"),
            "recall": len(ttw) / len(ons) if ons else float("nan"), "false": n_false,
            "hours": hours, "rate": n_false / hours if hours else float("nan")}


def split_prints(npz: dict, split: str, crops: pd.DataFrame | None) -> list[tuple]:
    """[(ts, probs, cls)] per print of the split, in ts order."""
    trial, ts = npz[f"{split}_trial"].astype(str), npz[f"{split}_ts"].astype(float)
    if f"{split}_cls" in npz:
        cls = npz[f"{split}_cls"]
    else:
        if crops is None:
            raise SystemExit(f"preds have no {split}_cls: pass --crops (data/crops.csv)")
        df = pd.DataFrame({"trial_id": trial, "ts_s": ts}).merge(
            crops[["trial_id", "ts_s", *CLS_COLS]], on=["trial_id", "ts_s"], how="left", validate="m:1")
        if df[CLS_COLS].isna().any(axis=None):
            raise SystemExit(f"{int(df[CLS_COLS[0]].isna().sum())} {split} images are not in crops.csv")
        cls = df[CLS_COLS].to_numpy(int)
    order = np.lexsort((ts, trial))
    trial, ts, probs, cls = trial[order], ts[order], npz[f"probs_{split}"][order], cls[order]
    cuts = np.flatnonzero(trial[1:] != trial[:-1]) + 1
    return list(zip(np.split(ts, cuts), np.split(probs, cuts), np.split(cls, cuts)))


def run(prints, labels, pcfg) -> list[dict]:
    return [evaluate_print(ts, p, c, labels, pcfg) for ts, p, c in prints]


def _key(s):
    return np.inf if np.isnan(s) else s


def choose(prints, labels, pcfg) -> tuple[float, list[tuple[float, dict]]]:
    """θ_on from GRID on these (calibration) prints: smallest with ≤ 1 false/h, else fewest false/h, then lower ttw."""
    grid = [(th, summarize(run(prints, labels, replace(pcfg, theta_on=th)))) for th in GRID]
    ok = [th for th, s in grid if s["rate"] <= NFR012_RATE]
    if ok:
        return min(ok), grid
    return min(grid, key=lambda g: (_key(g[1]["rate"]), _key(g[1]["median"])))[0], grid


def evaluate_fold(npz: dict, crops, pcfg) -> dict:
    """Both rungs (EWMA at the config β, floor at β = 0): θ_on from calib, applied once to test."""
    labels = [str(x) for x in npz["labels"]]
    calib, test = split_prints(npz, "calib", crops), split_prints(npz, "test", None)
    out = {"prints": len(test)}
    for name, cfg in (("ewma", pcfg), ("floor", replace(pcfg, beta=0.0))):
        th, grid = choose(calib, labels, cfg)
        out[name] = {"theta": th, "grid": grid, "results": run(test, labels, replace(cfg, theta_on=th))}
    return out


def _f(x, fmt=".2f") -> str:
    return "–" if np.isnan(x) else format(x, fmt)


def _table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return out + ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]


def nfr_line(s: dict, n_folds: int) -> str:
    ok = s["median"] <= NFR012_TTW and s["recall"] >= NFR012_RECALL and s["rate"] <= NFR012_RATE  # nan → FAIL
    return (f"NFR-012: {'PASS' if ok else 'FAIL'} (median {_f(s['median'], '.1f')} s, recall {_f(s['recall'])}, "
            f"{_f(s['rate'])} false/h; need ≤ {NFR012_TTW:g} s, ≥ {NFR012_RECALL:.2f}, ≤ {NFR012_RATE:g} /h; "
            f"pooled over {n_folds} fold{'s' * (n_folds != 1)}, θ_on from calibration prints)")


def render(folds, pcfg, model_dir, runtime_line: str) -> str:
    pooled = {n: [r for _, f in folds for r in f[n]["results"]] for n in ("ewma", "floor")}
    ew, fl = summarize(pooled["ewma"]), summarize(pooled["floor"])
    lines = [nfr_line(ew, len(folds)), "",
             "# Proactive early warning on held-out prints (T-0063)", "",
             (f"Predictions: {model_dir}/preds_fold*.npz, replayed per print in ts order through EarlyWarning "
              f"(β = {pcfg.beta}, θ_off = {pcfg.theta_off}, m = {pcfg.m}, cooldown {pcfg.cooldown_s:g} s, "
              f"gap reset {pcfg.max_gap_s:g} s). Onset = a cause entering D(i) at a segment start; a warning is true "
              f"iff its cause is in D at that image; false warnings in the first {SETTLE_S:g} s of a segment are not "
              f"counted; missed = no true warning within {WINDOW_S:g} s or before the segment ends (07 §14). θ_on is "
              f"chosen per fold on its calibration prints only; the floor is the same rule with β = 0."), "",
             (f"Floor (β = 0): median {_f(fl['median'], '.1f')} s, recall {_f(fl['recall'])}, "
              f"{_f(fl['rate'])} false/h."), "", "## θ_on choice (calibration prints only)", ""]
    lines += _table(["fold", "rung", "θ_on", "false/h", "median ttw (s)", "recall@30 s", "chosen"],
                    [(k, n, th, _f(s["rate"]), _f(s["median"], ".1f"), _f(s["recall"]), "✔" * (th == f[n]["theta"]))
                     for k, f in folds for n in ("ewma", "floor") for th, s in f[n]["grid"]])
    lines += ["", "## Test prints per fold (frozen θ_on)", ""]
    rows = []
    for k, f in folds:
        e, b = summarize(f["ewma"]["results"]), summarize(f["floor"]["results"])
        rows.append((k, f["ewma"]["theta"], f["prints"], f"{e['hours']:.2f}", e["onsets"], _f(e["median"], ".1f"),
                     _f(e["recall"]), _f(e["rate"]), f["floor"]["theta"], _f(b["median"], ".1f"), _f(b["recall"]),
                     _f(b["rate"])))
    lines += _table(["fold", "θ_on", "prints", "hours", "onsets", "median ttw (s)", "recall@30 s", "false/h",
                     "β = 0 θ_on", "β = 0 median", "β = 0 recall", "β = 0 false/h"], rows)
    causes = sorted({o[0] for r in pooled["ewma"] for o in r["onsets"]} | {c for r in pooled["ewma"] for c in r["false"]}
                    | {c for r in pooled["floor"] for c in r["false"]})
    lines += ["", "## Per cause (pooled test prints)", ""]
    rows = []
    for c in causes:
        e, b = summarize(pooled["ewma"], c), summarize(pooled["floor"], c)
        rows.append((c, e["onsets"], e["warned"], _f(e["median"], ".1f"), _f(e["recall"]), e["false"],
                     _f(e["rate"]), _f(b["median"], ".1f"), _f(b["recall"]), _f(b["rate"])))
    lines += _table(["cause", "onsets", "warned", "median ttw (s)", "recall@30 s", "false", "false/h",
                     "β = 0 median", "β = 0 recall", "β = 0 false/h"], rows)
    lines += ["", "## Runtime θ_on", "", runtime_line, ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", default="models/cause")
    ap.add_argument("--crops", default="data/crops.csv")
    ap.add_argument("--config", default=str(ROOT / "config" / "default.yaml"))
    ap.add_argument("--out", default="reports/proactive.md")
    a = ap.parse_args(argv)
    pcfg, model_dir = load(a.config).proactive, Path(a.model_dir)
    preds = load_preds(model_dir)
    if not preds:
        print(f"no preds_fold*.npz in {model_dir}", file=sys.stderr)
        return 1
    crops = pd.read_csv(a.crops) if Path(a.crops).exists() else None
    folds = [(k, evaluate_fold(npz, crops, pcfg)) for k, npz in preds]
    final = model_dir / "preds_final.npz"
    if final.exists():
        npz = dict(np.load(final))
        th, _ = choose(split_prints(npz, "calib", crops), [str(x) for x in npz["labels"]], pcfg)
        runtime = (f"θ_on = {th} from the calibration prints of {final} (set cfg.proactive.theta_on; the config "
                   f"has {pcfg.theta_on}).")
    else:
        runtime = f"{final} not found: no runtime θ_on (run train_cause.py --final first)."
    print(runtime)
    text = render(folds, pcfg, model_dir, runtime)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text.splitlines()[0])
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
