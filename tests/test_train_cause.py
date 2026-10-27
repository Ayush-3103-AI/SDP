import json

import cv2
import numpy as np
import pandas as pd
import torch
from caxton_fixture import load_script

from xqi.explain.cause_model import CauseModel
from xqi.types import CAUSES, DEFECTS

train_cause = load_script("train_cause")

PX = 32
COLOUR = {"none": (128, 128, 128), "flow_low": (0, 0, 255), "flow_high": (255, 0, 0), "multi": (0, 255, 0)}
NPZ_KEYS = {"labels", "probs_calib", "y_calib", "calib_trial", "calib_ts", "probs_test", "y_test", "test_trial",
            "test_ts", "test_cls"}


def _fixture(tmp_path):
    """6 prints × 14 colour-coded 32 px crops (4 per cause + 2 multi), crops.csv in 09 §Data layout, 2 folds."""
    rng = np.random.default_rng(0)
    rows = []
    for p in range(6):
        t = f"p{p}"
        causes = ["none", "flow_low", "flow_high"] * 4 + ["multi"] * 2
        for i, c in enumerate(rng.permutation(causes)):
            img = np.clip(np.array(COLOUR[c], float) + rng.normal(0, 10, (PX, PX, 3)), 0, 255).astype(np.uint8)
            path = tmp_path / "crops" / t / f"image-{i}.jpg"
            path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(path), img)
            rows.append((path.as_posix(), f"{t}/image-{i}.jpg", t, t, 0.5 * (13 - i), c, 0, 1, 1, 1, 90.0, 100.0, 210.0))
    crops = tmp_path / "crops.csv"
    pd.DataFrame(rows, columns=["crop_path", "image_path", "trial_id", "geometry", "ts_s", "cause", "flow_cls",
                                "speed_cls", "z_cls", "nozzle_cls", "flow_pct", "speed_pct",
                                "nozzle_target_c"]).to_csv(crops, index=False)
    folds = [{"test_geometries": ["p0", "p1"], "train_trials": ["p2", "p3", "p4"], "calib_trials": ["p5"],
              "test_trials": ["p0", "p1"]},
             {"test_geometries": ["p2", "p3"], "train_trials": ["p0", "p1", "p4"], "calib_trials": ["p5"],
              "test_trials": ["p2", "p3"]}]
    splits = tmp_path / "logo.json"
    splits.write_text(json.dumps({"version": 2, "kind": "leave-parts-out", "seed": 0, "folds": folds}))
    return ["--crops", str(crops), "--splits", str(splits), "--px", str(PX), "--no-pretrained", "--workers", "0"]


def test_class_weights_balance_the_train_counts():
    w = train_cause.class_weights(np.array([0, 0, 0, 1]), 3)
    assert w.tolist() == [4 / 6, 2.0, 0.0]  # n / (classes present · count); absent classes get 0


def test_epoch_sample_caps_images_per_print():
    df = pd.DataFrame({"trial_id": ["a"] * 10 + ["b"] * 2})
    idx = train_cause.epoch_sample(df, 3, np.random.default_rng(0))
    assert sorted(df.trial_id.iloc[idx]) == ["a"] * 3 + ["b"] * 2


def test_overfit_check_passes(tmp_path, capsys):
    args = _fixture(tmp_path)
    assert train_cause.main(["--overfit", "20", "--out", str(tmp_path / "m"), *args]) == 0
    assert "overfit: PASS" in capsys.readouterr().out


def test_fold0_both_rungs(tmp_path):
    args = _fixture(tmp_path)
    root, report = tmp_path / "models" / "cause", tmp_path / "reports" / "cause_fold0.md"
    for rung, extra in (("probe", ["--freeze-backbone"]), ("finetune", [])):
        assert train_cause.main(["--fold", "0", "--epochs", "1", "--limit", "64", "--batch", "8", "--out",
                                 str(root / rung), "--report", str(report), *extra, *args]) == 0

    out = root / "finetune"
    model = CauseModel(out / "fold0.pt", CAUSES, DEFECTS, "cpu", input_px=PX)  # saved via save_checkpoint
    est = model.predict(np.zeros((PX, PX, 3), np.uint8), "stringing")
    assert abs(sum(est.probs.values()) - 1) < 1e-5

    ckpt = torch.load(out / "fold0.pt", weights_only=True)
    header = json.loads((out / "fold0.log").read_text(encoding="utf-8").splitlines()[0])
    for meta in (ckpt, header):
        assert meta["seed"] == 0 and meta["git_sha"] and set(meta["sha256"]) == {"logo.json", "crops.csv"}
        assert meta["config"]["fold"] == 0

    npz = np.load(out / "preds_fold0.npz")
    assert set(npz.files) == NPZ_KEYS
    assert list(npz["labels"]) == list(CAUSES)
    assert len(npz["y_test"]) == 28 and (npz["y_test"] == -1).sum() == 4  # every test image, multi rows included
    assert len(npz["y_calib"]) == 14 and npz["probs_test"].shape == (28, len(CAUSES))
    assert npz["test_cls"].shape == (28, 4)
    trial, ts = npz["test_trial"], npz["test_ts"]
    assert list(trial) == sorted(trial) and all(np.all(np.diff(ts[trial == t]) > 0) for t in ("p0", "p1"))

    text = report.read_text(encoding="utf-8")
    assert "## probe" in text and "## finetune" in text and "floor" in text


def test_probe_trains_the_head_only(tmp_path):
    model = train_cause.make_model(len(CAUSES), freeze=True, pretrained=False)
    trainable = {n for n, p in model.named_parameters() if p.requires_grad}
    assert trainable == {"head.weight", "head.bias"}


def test_cuda_oom_halves_the_batch(tmp_path, monkeypatch, capsys):
    args = _fixture(tmp_path)
    real, seen = train_cause.train_one_epoch, []

    def oom_at_8(model, loader, opt, weights, scaler=None):
        seen.append(loader.batch_size)
        if loader.batch_size == 8:
            raise torch.cuda.OutOfMemoryError("fake")
        return real(model, loader, opt, weights, scaler)

    monkeypatch.setattr(train_cause, "train_one_epoch", oom_at_8)
    assert train_cause.main(["--fold", "1", "--epochs", "1", "--batch", "8", "--out", str(tmp_path / "m"),
                             *args]) == 0
    assert seen == [8, 4] and "halving the batch to 4" in capsys.readouterr().out
