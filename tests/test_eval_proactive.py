from dataclasses import replace

import numpy as np
import pandas as pd
from caxton_fixture import ROOT, load_script

from xqi.config import load

eval_proactive = load_script("eval_proactive")

LABELS = ["none", "flow_low", "flow_high", "speed_low", "speed_high", "nozzle_temp_low", "nozzle_temp_high",
          "z_offset_low", "z_offset_high"]
CLS = ["flow_cls", "speed_cls", "z_cls", "nozzle_cls"]
PCFG = replace(load(ROOT / "config" / "default.yaml").proactive, beta=0.8, theta_on=0.6, theta_off=0.4, m=3, cooldown_s=60,
               max_gap_s=10)


def planted():
    """0..200 s at 1 fps; flow_low (flow_cls = 0) from t = 100 s, its probability 1.0 from t = 104 s."""
    ts = np.arange(201.0)
    cls = np.ones((len(ts), 4), int)
    cls[ts >= 100, 0] = 0
    probs = np.zeros((len(ts), len(LABELS)), np.float32)
    probs[:, 0] = 1.0
    probs[ts >= 104] = 0.0
    probs[ts >= 104, LABELS.index("flow_low")] = 1.0
    return ts, probs, cls


def noise():
    """One print hour, nothing deviates; background U(0, 0.3), flow_high = 1.0 for 10 s at 0, 30, 200, 230, 400."""
    ts = np.arange(3601.0)
    probs = np.random.default_rng(0).uniform(0, 0.3, (len(ts), len(LABELS))).astype(np.float32)
    for s in (0, 30, 200, 230, 400):
        probs[s:s + 10, LABELS.index("flow_high")] = 1.0
    return ts, probs, np.ones((len(ts), 4), int)


def test_planted_onset_time_to_warning_by_hand():
    # β = 0.8: p̄(104 + k) = 1 − 0.8^(k+1) ≥ 0.6 first at k = 4 (0.672, t = 108); run = 3 at t = 110 → ttw 10 s.
    r = eval_proactive.evaluate_print(*planted(), LABELS, PCFG)
    assert r["onsets"] == [("flow_low", 100.0, 10.0)] and r["false"] == []
    # β = 0 floor: p̄ = p ≥ 0.6 at t = 104, run = 3 at t = 106 → 6 s.
    r0 = eval_proactive.evaluate_print(*planted(), LABELS, replace(PCFG, beta=0.0))
    assert r0["onsets"] == [("flow_low", 100.0, 6.0)]
    s = eval_proactive.summarize([r])
    assert s["median"] == 10.0 and s["recall"] == 1.0 and s["rate"] == 0.0


def test_noise_print_false_rate_by_hand():
    # burst 0: warns at t = 2, inside the first 6 s → not counted; 30: cooldown (60 s after t = 2);
    # 200: false; 230: cooldown; 400: false → 2 false in 1 print-hour.
    r = eval_proactive.evaluate_print(*noise(), LABELS, PCFG)
    assert r["onsets"] == [] and r["false"] == ["flow_high", "flow_high"] and r["hours"] == 1.0
    s = eval_proactive.summarize([r])
    assert s["rate"] == 2.0 and np.isnan(s["recall"]) and np.isnan(s["median"])


def bursts(level):
    """One print hour, nothing deviates; flow_high at `level` for 20 s every 100 s, 0 elsewhere."""
    ts = np.arange(3601.0)
    probs = np.zeros((len(ts), len(LABELS)), np.float32)
    for s in range(10, 3500, 100):
        probs[s:s + 20, LABELS.index("flow_high")] = level
    return ts, probs, np.ones((len(ts), 4), int)


def _write(tmp_path, test_prints):
    """Fold 0: calib = 0.55 bursts (θ = 0.5 → a false warning per burst, θ = 0.6 → none), so θ_on = 0.6."""
    c_ts, c_probs, c_cls = bursts(0.55)
    ts, probs, cls, trial = [], [], [], []
    for name, (t, p, c) in test_prints.items():
        ts.append(t), probs.append(p), cls.append(c)
        trial += [name] * len(t)
    np.savez(tmp_path / "preds_fold0.npz", labels=np.array(LABELS), probs_calib=c_probs,
             y_calib=np.zeros(len(c_ts), int), calib_trial=np.array(["c1"] * len(c_ts)), calib_ts=c_ts,
             probs_test=np.concatenate(probs), y_test=np.zeros(len(trial), int), test_trial=np.array(trial),
             test_ts=np.concatenate(ts), test_cls=np.concatenate(cls))
    crops = pd.DataFrame(c_cls, columns=CLS).assign(trial_id="c1", ts_s=c_ts)  # calib classes come from crops.csv
    crops.to_csv(tmp_path / "crops.csv", index=False)


def _run(tmp_path):
    out = tmp_path / "proactive.md"
    assert eval_proactive.main(["--model-dir", str(tmp_path), "--crops", str(tmp_path / "crops.csv"),
                                "--out", str(out)]) == 0
    return out.read_text(encoding="utf-8")


def test_theta_is_chosen_on_calibration_prints_only(tmp_path):
    _write(tmp_path, {"t1": planted()})
    text = _run(tmp_path)
    assert text.splitlines()[0] == "NFR-012: PASS (median 10.0 s, recall 1.00, 0.00 false/h; need ≤ 10 s, ≥ 0.70, " \
                                   "≤ 1 /h; pooled over 1 fold, θ_on from calibration prints)"
    assert "| 0 | 0.6 |" in text and "β = 0" in text and "## Per cause" in text
    calib = eval_proactive.split_prints(dict(np.load(tmp_path / "preds_fold0.npz")), "calib",
                                        pd.read_csv(tmp_path / "crops.csv"))
    assert eval_proactive.choose(calib, LABELS, PCFG)[0] == 0.6

    # A test print whose 0.65 bursts would push the choice to 0.7 must not change it: θ stays 0.6, the test FAILs.
    _write(tmp_path, {"t1": planted(), "t2": bursts(0.65)})
    text = _run(tmp_path)
    assert text.startswith("NFR-012: FAIL") and "| 0 | 0.6 |" in text
