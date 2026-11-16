import json

import numpy as np
import pandas as pd
from caxton_fixture import load_script

from xqi.types import CAUSES

probe = load_script("probe_features")

CLS = {"none": (1, 1, 1, 1), "flow_low": (0, 1, 1, 1), "speed_high": (1, 2, 1, 1), "multi": (0, 2, 1, 1)}


def test_joint_to_causes_one_hot_heads_give_the_single_cause():
    labels = list(CAUSES)
    heads = np.full((3, 4, 3), 0.01)
    for i, cls in enumerate([(1, 1, 1, 1), (0, 1, 1, 1), (1, 1, 1, 2)]):
        heads[i, range(4), cls] = 0.98
    p = probe.joint_to_causes(heads, labels)
    assert np.allclose(p.sum(1), 1)
    assert [labels[j] for j in p.argmax(1)] == ["none", "flow_low", "nozzle_temp_high"]


def _fixture(tmp_path):
    """6 prints × 16 rows; features = a noisy one-hot of the cause, so a linear head separates them."""
    rng = np.random.default_rng(0)
    rows, feats = [], []
    names = list(CLS)
    for p in range(6):
        for i, c in enumerate(rng.permutation(names * 4)):
            rows.append((f"c/p{p}/{i}.jpg", f"p{p}", 0.5 * i, c, *CLS[c]))
            feats.append(np.eye(8)[names.index(c)] * 3 + rng.normal(0, 0.3, 8))
    crops = pd.DataFrame(rows, columns=["crop_path", "trial_id", "ts_s", "cause", "flow_cls", "speed_cls", "z_cls",
                                        "nozzle_cls"])
    crops.to_csv(tmp_path / "crops.csv", index=False)
    np.savez(tmp_path / "f.npz", feats=np.array(feats, np.float32), crop_path=crops.crop_path.to_numpy(str))
    folds = [{"train_trials": ["p2", "p3", "p4"], "calib_trials": ["p5"], "test_trials": ["p0", "p1"]},
             {"train_trials": ["p0", "p1", "p4"], "calib_trials": ["p5"], "test_trials": ["p2", "p3"]}]
    (tmp_path / "logo.json").write_text(json.dumps({"folds": folds}))
    return tmp_path


def _run(tmp_path, head):
    d = _fixture(tmp_path)
    out = d / head
    assert probe.main(["fit", "--head", head, "--crops", str(d / "crops.csv"), "--splits", str(d / "logo.json"),
                       "--features", str(d / "f.npz"), "--out", str(out)]) == 0
    return out


def test_fit_single_writes_train_cause_preds(tmp_path):
    out = _run(tmp_path, "single")
    z = np.load(out / "preds_fold0.npz")
    assert {"labels", "probs_calib", "y_calib", "probs_test", "y_test", "test_trial", "test_ts", "test_cls"} <= set(z)
    keep = z["y_test"] >= 0
    assert len(z["y_test"]) == 32 and keep.sum() == 24  # multi rows kept, y = -1
    assert (z["probs_test"][keep].argmax(1) == z["y_test"][keep]).mean() > 0.9


def test_fit_multi_learns_from_multi_rows_and_reports_per_variable_accuracy(tmp_path):
    out = _run(tmp_path, "multi")
    z = np.load(out / "preds_fold1.npz")
    keep = z["y_test"] >= 0
    assert np.allclose(z["probs_test"].sum(1), 1, atol=1e-4)
    assert (z["probs_test"][keep].argmax(1) == z["y_test"][keep]).mean() > 0.9
    s = json.loads((out / "summary.json").read_text())
    assert s["fold1"]["var_acc"]["flow"] > 0.9
