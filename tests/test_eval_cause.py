import json

import cv2
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


def test_rung_rule_needs_more_than_the_probe_std():
    probe = [0.7, 0.8, 0.9]  # std 0.082
    assert eval_cause.choose_rung([0.8, 0.8, 0.8], probe) == "probe"
    assert eval_cause.choose_rung([0.87, 0.87, 0.87], probe) == "probe"
    assert eval_cause.choose_rung([0.9, 0.9, 0.9], probe) == "finetune"


def test_report_sections_rung_choice_and_copy(tmp_path, capsys):
    ft_dir, crops, splits = _synthetic(tmp_path / "ft", acc_pair=(0.8, 0.9))
    probe_dir, _, _ = _synthetic(tmp_path / "probe")
    runtime, out = tmp_path / "runtime", tmp_path / "cause_eval.md"
    assert eval_cause.main(["--model-dir", str(ft_dir), "--probe-dir", str(probe_dir), "--copy-to", str(runtime),
                            "--crops", str(crops), "--splits", str(splits), "--out", str(out)]) == 0
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "K2: PASS (top-1 = floor + 35.0 pp)"
    assert lines[1].startswith("NFR-005: ") and "floor + 35.0 pp" in lines[1]
    for h in ("## Frame", "## Baseline", "## Model", "## Result", "## Risks"):
        assert h in lines
    assert any(line.startswith("Rung: finetune") for line in lines)
    assert sorted(p.name for p in runtime.iterdir()) == [f"preds_fold{k}.npz" for k in range(N_FOLDS)]
    assert "train_cause.py --final" in capsys.readouterr().out


def test_suspected_leakage_stops(tmp_path):
    model_dir, crops, splits = _synthetic(tmp_path, acc_pair=(1.0, 1.0))
    out = tmp_path / "cause_eval.md"
    assert eval_cause.main(["--model-dir", str(model_dir), "--crops", str(crops), "--splits", str(splits),
                            "--out", str(out)]) == 3
    assert out.read_text(encoding="utf-8").splitlines()[1].startswith("suspected leakage: fold 0 top-1 = 1.000")


def test_most_confident_wrong_crops_png(tmp_path):
    rows = []
    for i in range(3):
        path = tmp_path / f"c{i}.jpg"
        cv2.imwrite(str(path), np.full((16, 16, 3), 60 * i, np.uint8))
        rows.append(("q", float(i), path.as_posix(), "none"))
    rows.append(("t", 0.0, "", "flow_low"))  # a training print
    crops = pd.DataFrame(rows, columns=["trial_id", "ts_s", "crop_path", "cause"])
    probs = np.array([[0.9, 0.1], [0.2, 0.8], [0.4, 0.6]])  # rows 1 and 2 are wrong (true 0)
    npz = {"labels": np.array(["none", "flow_low"]), "probs_test": probs, "y_test": np.array([0, 0, 0]),
           "test_trial": np.array(["q"] * 3), "test_ts": np.arange(3.0)}
    m = eval_cause.fold_metrics(npz, {"train_trials": ["t"]}, crops)
    out = tmp_path / "cause_errors.png"
    assert eval_cause.errors_png([(0, m)], crops, out) == 2
    assert cv2.imread(str(out)) is not None
