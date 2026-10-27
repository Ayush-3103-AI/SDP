import json

import numpy as np
import pandas as pd
import pytest
from caxton_fixture import adapt, load_script

from xqi.types import CAUSES

eval_cause = load_script("eval_cause")
build_crops = load_script("build_crops")

N_FOLDS, PRINTS, PER_PRINT = 3, 6, 40  # test prints per fold, images per print


def _synthetic(tmp_path, acc_pair=(0.7, 0.9), seed=0):
    """3 folds × 6 test prints × 40 images. Half the images are `none` (the training majority), so floor top-1 = 0.5.
    Prints alternate between acc_pair[0] and acc_pair[1] correct top-1, so every fold's top-1 is their mean."""
    rng = np.random.default_rng(seed)
    k = len(CAUSES)
    folds, crops = [], []
    model_dir = tmp_path / "models" / "cause"
    model_dir.mkdir(parents=True)
    for f in range(N_FOLDS):
        test = [f"p{f}_{i}" for i in range(PRINTS)]
        train = [f"t{f}_{i}" for i in range(4)]
        folds.append({"test_geometries": test, "train_trials": train, "calib_trials": [], "test_trials": test})
        for t in train:  # training prints: none is the majority, flow_low second, speed_high third
            crops += [(t, "none")] * 10 + [(t, "flow_low")] * 6 + [(t, "speed_high")] * 3 + [(t, "multi")] * 20
        y, probs, trial = [], [], []
        for i, t in enumerate(test):
            yt = np.array([0] * (PER_PRINT // 2) + list(rng.integers(1, k, PER_PRINT // 2)))
            n_right = round(acc_pair[i % 2] * PER_PRINT)
            for j, c in enumerate(yt):
                p = rng.dirichlet(np.ones(k)) * 0.5
                pred = c if j < n_right else (c + 1 + rng.integers(0, k - 1)) % k
                p[pred] += 1.0
                probs.append(p / p.sum())
            y += list(yt) + [-1, -1]  # two multi rows per print: excluded
            probs += [np.full(k, 1 / k)] * 2
            trial += [t] * (PER_PRINT + 2)
        np.savez(model_dir / f"preds_fold{f}.npz", labels=np.array(CAUSES), probs_test=np.array(probs, np.float32),
                 y_test=np.array(y), test_trial=np.array(trial), test_ts=np.arange(len(y), dtype=float))
    pd.DataFrame(crops, columns=["trial_id", "cause"]).to_csv(tmp_path / "crops.csv", index=False)
    splits = tmp_path / "logo.json"
    splits.write_text(json.dumps({"version": 2, "kind": "leave-parts-out", "seed": 0, "folds": folds}))
    return model_dir, tmp_path / "crops.csv", splits


def _model_report(tmp_path, model_dir, crops, splits):
    out = tmp_path / "cause_eval.md"
    assert eval_cause.main(["--model-dir", str(model_dir), "--crops", str(crops), "--splits", str(splits),
                            "--out", str(out)]) == 0
    return out.read_text(encoding="utf-8")


def test_planted_accuracy_ci_and_k2_pass(tmp_path):
    text = _model_report(tmp_path, *_synthetic(tmp_path))
    assert text.splitlines()[0] == "K2: PASS (top-1 = floor + 30.0 pp)"
    mean = next(line for line in text.splitlines() if line.startswith("| mean"))
    cells = [c.strip() for c in mean.split("|")[1:-1]]
    assert cells[3] == "0.800 ± 0.000"  # top-1
    lo, hi = (float(x) for x in cells[4].strip("[]").split(","))
    assert lo < 0.8 < hi and hi - lo < 0.15
    assert cells[6] == "0.500 ± 0.000"  # floor top-1
    assert "| none | 360 | 1.000 |" in text  # per-class recall: every none image is in a print's right share


def test_k2_fail_when_model_is_near_the_floor(tmp_path):
    text = _model_report(tmp_path, *_synthetic(tmp_path, acc_pair=(0.5, 0.55)))
    assert text.splitlines()[0].startswith("K2: FAIL (top-1 = floor + 2.5 pp")


def test_bootstrap_ci_is_over_prints():
    correct = np.repeat([1.0, 0.0], 50)  # one perfect print, one hopeless print
    groups = np.repeat(["a", "b"], 50)
    lo, hi = eval_cause.bootstrap([(correct, groups)])
    assert lo == 0.0 and hi == 1.0  # resampling prints, not images, shows how little two prints say
    lo, hi = eval_cause.bootstrap([(correct, np.arange(100))])
    assert 0.35 < lo < 0.5 < hi < 0.65


def test_ece_of_a_calibrated_and_an_overconfident_model():
    y = np.array([0, 0, 1, 1])
    assert eval_cause.ece(np.array([[1.0, 0.0], [1.0, 0.0], [0.0, 1.0], [0.0, 1.0]]), y) == pytest.approx(0.0)
    assert eval_cause.ece(np.array([[1.0, 0.0]] * 4), y) == pytest.approx(0.5)


def test_floor_on_the_caxton_fixture(tmp_path):
    data = adapt(tmp_path)
    assert build_crops.main(["--images", str(data / "images.csv"), "--root", str(tmp_path / "raw"),
                             "--out", str(data / "crops"), "--workers", "2"]) == 0
    prints = ["p0", "p1", "p2"]
    folds = [{"test_geometries": [t], "train_trials": [p for p in prints if p != t], "calib_trials": [],
              "test_trials": [t]} for t in prints]
    splits = tmp_path / "logo.json"
    splits.write_text(json.dumps({"version": 2, "kind": "leave-parts-out", "seed": 0, "folds": folds}))
    out = tmp_path / "cause_floor.md"
    assert eval_cause.main(["--floor", "--crops", str(data / "crops.csv"), "--splits", str(splits),
                            "--out", str(out)]) == 0
    rows = [line for line in out.read_text(encoding="utf-8").splitlines() if line.startswith("| 0 ")]
    # fold 0 tests p0 (none 4 of 11 single-cause or none images; multi excluded); p1 + p2 train: none 6 is the majority
    assert rows == ["| 0 | none | none, flow_high, nozzle_temp_low | 11 | 0.364 | 0.364 |"]
