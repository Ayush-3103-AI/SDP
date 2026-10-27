"""Counterfactual direction fidelity on confident events (T-0017; 07 §2, §9; NFR-007).

    python scripts/eval_counterfactual.py [--model-dir models/cause] [--crops data/crops.csv]
        [--config config/default.yaml] [--out reports/counterfactual.md]

Per fold (preds_fold<k>.npz): qhat at the config α from the fold's calibration prints (T-0015's method). Test images
whose true cause is actionable (has a setpoint action; not none, not manual, not multi) are confident when L4 would
pass: |C| = 1, C ≠ {none}, p_top ≥ τ. Fidelity = the top-1 proposal (make_proposal at the nominal setpoints) changes
the true cause's variable in the undoing direction (v̂ = v*, sign Δ̂ = −d*). The confident fraction is reported next
to it, so a model cannot pass by abstaining. Steps-to-undo is not computable on CAXTON (magnitudes vary), so the
report gives the median |logged deviation| per cause (setpoint minus the median of that variable's good-class images,
from crops.csv). Line 1 is the NFR-007 verdict, pooled over folds.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from eval_cause import load_preds
from eval_conformal import sets

from xqi.config import load, load_causes
from xqi.explain.conformal import calibrate
from xqi.explain.counterfactual import UNIT, make_proposal
from xqi.types import PrinterState

NFR007 = 0.85
SETPOINT = {"flow": ("flow_pct", "flow_cls"), "speed": ("speed_pct", "speed_cls"),
            "nozzle_temp": ("nozzle_target_c", "nozzle_cls")}  # as in derive_window.py


def nominal_state(cfg) -> PrinterState:
    n = cfg.printer.nominal
    return PrinterState(ts=0.0, state="Printing", nozzle_actual_c=n["nozzle_temp"], nozzle_target_c=n["nozzle_temp"],
                        bed_actual_c=n["bed_temp"], bed_target_c=n["bed_temp"], flow_pct=n["flow"],
                        speed_pct=n["speed"], progress_pct=None, last_change_ts={})


def fold_events(npz: dict, cfg, cause_action: dict) -> dict:
    """Per actionable test image: y, confident, right (direction of the top-1 proposal)."""
    labels = [str(x) for x in npz["labels"]]
    cal = npz["y_calib"] >= 0
    qhat = calibrate(npz["probs_calib"][cal], npz["y_calib"][cal], cfg.conformal.alpha)
    act = np.array([y >= 0 and cause_action.get(labels[y]) is not None for y in npz["y_test"]])
    probs, y = npz["probs_test"][act], npz["y_test"][act]
    member, top = sets(probs, qhat), probs.argmax(1)
    p_top = probs[np.arange(len(y)), top]
    confident = (member.sum(1) == 1) & (top != labels.index("none")) & (p_top >= cfg.envelope.L4.tau)
    state, right = nominal_state(cfg), np.zeros(len(y), bool)
    for i in np.flatnonzero(confident):
        prop = make_proposal(labels[top[i]], float(p_top[i]), 0.5, state, cfg)  # the sign does not depend on s
        var, d = cause_action[labels[y[i]]]
        right[i] = prop is not None and prop.var == var and np.sign(prop.delta) == -d
    return {"qhat": qhat, "labels": labels, "y": y, "confident": confident, "right": right,
            "trial": npz["test_trial"][act], "ts": npz["test_ts"][act]}


def deviations(crops: pd.DataFrame, events: list[dict], cause_action: dict) -> dict[str, float]:
    """Median |setpoint − good-class median| over each actionable cause's test images."""
    good = {v: crops.loc[crops[cls] == 1, col].median() for v, (col, cls) in SETPOINT.items()}
    out = {}
    for e in events:
        df = pd.DataFrame({"trial_id": e["trial"], "ts_s": e["ts"], "cause": [e["labels"][y] for y in e["y"]]})
        df = df.merge(crops, on=["trial_id", "ts_s"], how="left")
        for cause, g in df.groupby("cause"):
            var = cause_action[cause][0]
            out.setdefault(cause, []).extend((g[SETPOINT[var][0]] - good[var]).abs().dropna())
    return {c: float(np.median(v)) for c, v in out.items() if v}


def _table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return out + ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]


def _frac(a, b) -> str:
    return f"{a / b:.3f}" if b else "–"


def render(folds, cfg, cause_action, dev, model_dir) -> str:
    conf = np.concatenate([e["confident"] for _, e in folds])
    right = np.concatenate([e["right"] for _, e in folds])
    y = np.concatenate([e["y"] for _, e in folds])
    n_conf, n_act = int(conf.sum()), len(conf)
    fid = right[conf].mean() if n_conf else 0.0
    verdict = "PASS" if n_conf and fid >= NFR007 else "FAIL"
    labels = folds[0][1]["labels"]
    lines = [(f"NFR-007: {verdict} (direction fidelity {fid:.3f} on {n_conf} confident events, need ≥ {NFR007}; "
              f"confident fraction {_frac(n_conf, n_act)} of {n_act} actionable test images; pooled over "
              f"{len(folds)} folds)"), "",
             "# Counterfactual direction fidelity on confident events (T-0017)", "",
             (f"Predictions: {model_dir}/preds_fold*.npz. Confident = |C| = 1, C ≠ {{none}}, p_top ≥ τ = "
              f"{cfg.envelope.L4.tau} (L4 would pass), qhat per fold at α = {cfg.conformal.alpha} from its "
              "calibration prints. Fidelity = the top-1 proposal changes the true cause's variable in the undoing "
              "direction. Actionable true causes only; none, manual (z_offset) and multi images are excluded."),
             "", "## Per fold", ""]
    lines += _table(["fold", "qhat", "actionable", "confident", "confident fraction", "fidelity"],
                    [(k, f"{e['qhat']:.4f}", len(e["y"]), int(e["confident"].sum()),
                      _frac(e["confident"].sum(), len(e["y"])),
                      _frac(e["right"][e["confident"]].sum(), e["confident"].sum())) for k, e in folds])
    lines += ["", "## Per cause (pooled)", ""]
    rows = []
    for i, c in enumerate(labels):
        if cause_action.get(c) is None:
            continue
        var, m = cause_action[c][0], y == i
        rows.append((c, var, int(m.sum()), int((m & conf).sum()), _frac((m & conf).sum(), m.sum()),
                     _frac((m & conf & right).sum(), (m & conf).sum()),
                     f"{dev[c]:g} {UNIT[var]}" if c in dev else "–"))
    lines += _table(["cause", "var", "actionable", "confident", "confident fraction", "fidelity",
                     "median abs logged deviation"], rows)
    lines += ["", ("Steps-to-undo (07 §9) is not computed: CAXTON's deviation magnitudes vary within a cause, so the "
                   "median |logged deviation| from the good-class median stands in for it."), ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", default="models/cause")
    ap.add_argument("--crops", default="data/crops.csv")
    ap.add_argument("--config", default=str(ROOT / "config" / "default.yaml"))
    ap.add_argument("--out", default="reports/counterfactual.md")
    a = ap.parse_args(argv)
    cfg = load(a.config)
    causes_file = Path(cfg.causes_file)
    cause_action = load_causes(causes_file if causes_file.is_absolute() else ROOT / causes_file).cause_action
    preds = load_preds(Path(a.model_dir))
    if not preds:
        print(f"no preds_fold*.npz in {a.model_dir}", file=sys.stderr)
        return 1
    folds = [(k, fold_events(npz, cfg, cause_action)) for k, npz in preds]
    crops = Path(a.crops)
    dev = deviations(pd.read_csv(crops), [e for _, e in folds], cause_action) if crops.exists() else {}
    text = render(folds, cfg, cause_action, dev, a.model_dir)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text.splitlines()[0])
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
