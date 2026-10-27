"""Gate 5: the shipped cause model (models/cause/final.pt) still predicts its golden crops (T-0013)."""
import json
from pathlib import Path

import cv2
import numpy as np
import pytest
import torch
from caxton_fixture import load_script
from test_train_cause import _fixture

from xqi.explain.cause_model import CauseModel, build_model, save_checkpoint
from xqi.types import CAUSES, DEFECTS

ROOT = Path(__file__).resolve().parents[1]
FINAL, GOLDEN = ROOT / "models" / "cause" / "final.pt", ROOT / "tests" / "fixtures" / "cause_golden"
GATE5_KEYS = {"state_dict", "causes", "use_defect", "rung", "input_px", "normalisation", "sha256", "git_sha", "metrics"}


def check_golden(weights: Path, golden: Path) -> None:
    exp = json.loads((golden / "expected.json").read_text(encoding="utf-8"))
    ckpt = torch.load(weights, map_location="cpu", weights_only=True)
    assert GATE5_KEYS <= set(ckpt) and set(ckpt["sha256"]) == {"logo.json", "crops.csv"}
    assert ckpt["causes"] == exp["causes"] and len(exp["crops"]) == 8
    model = CauseModel(weights, exp["causes"], DEFECTS, "cpu", input_px=exp["input_px"])
    for c in exp["crops"]:
        est = model.predict(cv2.imread(str(golden / c["file"])), "unknown")
        assert np.allclose([est.probs[k] for k in exp["causes"]], c["probs"], atol=1e-3), c["file"]


@pytest.mark.skipif(not (FINAL.exists() and (GOLDEN / "expected.json").exists()),
                    reason="final.pt / golden fixture not pushed yet (T-0013 G3)")
def test_final_model_matches_its_golden_crops():
    check_golden(FINAL, GOLDEN)


def test_final_run_writes_the_gate5_artifact_and_golden(tmp_path):
    args = _fixture(tmp_path)
    out, golden = tmp_path / "models" / "cause", tmp_path / "golden"
    assert load_script("train_cause").main(["--final", "--epochs", "1", "--batch", "8", "--out", str(out),
                                            "--golden", str(golden), *args]) == 0
    check_golden(out / "final.pt", golden)
    npz = np.load(out / "preds_final.npz")
    assert len(npz["y_calib"]) == 14 and len(npz["y_test"]) == 0  # one calib print (20 % of 6), no test split


def test_causes_order_mismatch_refused(tmp_path):
    weights = tmp_path / "final.pt"
    save_checkpoint(build_model(len(CAUSES), 0, pretrained=False), weights, causes=list(reversed(CAUSES)))
    with pytest.raises(ValueError, match="causes"):
        CauseModel(weights, CAUSES, DEFECTS, "cpu")
