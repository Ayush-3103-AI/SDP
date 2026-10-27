import numpy as np
import pandas as pd
from caxton_fixture import load_script

from xqi.types import CAUSES

eval_counterfactual = load_script("eval_counterfactual")

K = len(CAUSES)
TEST = ["flow_low"] * 30 + ["flow_high"] * 20 + ["none"] * 10 + ["z_offset_low"] * 5  # + 3 multi rows


def _onehot(idx, p=0.95):
    probs = np.full((len(idx), K), (1 - p) / (K - 1), np.float32)
    probs[np.arange(len(idx)), idx] = p
    return probs


def _npz(path, swap_flow: bool):
    """Calib: an always-right model on 200 images. Test: right, or flow_low ↔ flow_high swapped."""
    y_cal = np.arange(200) % K
    y = np.array([CAUSES.index(c) for c in TEST] + [-1] * 3)
    pred = y.copy()
    lo, hi = CAUSES.index("flow_low"), CAUSES.index("flow_high")
    if swap_flow:
        pred = np.where(y == lo, hi, np.where(y == hi, lo, y))
    np.savez(path, labels=np.array(CAUSES), probs_calib=_onehot(y_cal), y_calib=y_cal,
             probs_test=_onehot(np.maximum(pred, 0)), y_test=y, test_trial=np.array(["p0"] * len(y)),
             test_ts=np.arange(len(y), dtype=float))


def _crops(tmp_path):
    """flow_low images at 80 %, flow_high at 115 %, good rows at 100 %: median |deviation| 20 and 15."""
    rows = [("p0", float(i), {"flow_low": 80.0, "flow_high": 115.0}.get(c, 100.0), int(c != "flow_low") + int(
        c == "flow_high")) for i, c in enumerate(TEST + ["multi"] * 3)]
    df = pd.DataFrame(rows, columns=["trial_id", "ts_s", "flow_pct", "flow_cls"])
    df = df.assign(speed_pct=100.0, speed_cls=1, nozzle_target_c=210.0, nozzle_cls=1)
    df.to_csv(tmp_path / "crops.csv", index=False)
    return tmp_path / "crops.csv"


def _report(tmp_path, swap_flow):
    _npz(tmp_path / "preds_fold0.npz", swap_flow)
    out = tmp_path / "counterfactual.md"
    assert eval_counterfactual.main(["--model-dir", str(tmp_path), "--crops", str(_crops(tmp_path)),
                                     "--out", str(out)]) == 0
    return out.read_text(encoding="utf-8")


def test_always_right_model_has_fidelity_one(tmp_path):
    text = _report(tmp_path, swap_flow=False)
    assert text.splitlines()[0].startswith("NFR-007: PASS (direction fidelity 1.000 on 50 confident events")
    assert "confident fraction 1.000 of 50 actionable" in text.splitlines()[0]  # none / manual / multi excluded
    assert "| flow_low | flow | 30 | 30 | 1.000 | 1.000 | 20 % |" in text
    assert "| flow_high | flow | 20 | 20 | 1.000 | 1.000 | 15 % |" in text


def test_flow_low_high_confusion_has_fidelity_zero(tmp_path):
    text = _report(tmp_path, swap_flow=True)
    assert text.splitlines()[0].startswith("NFR-007: FAIL (direction fidelity 0.000 on 50 confident events")
