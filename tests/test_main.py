import logging
from pathlib import Path

import cv2
import numpy as np
import torch
import yaml

from xqi import __main__ as cli
from xqi.explain.cause_model import build_model, save_checkpoint
from xqi.explain.conformal import save_qhat
from xqi.store import Store
from xqi.types import CAUSES, Detection

ROOT = Path(__file__).resolve().parents[1]


def _always(cls):
    return lambda frame: [Detection(frame.frame_id, cls, 0.9, (0.0, 0.0, 4.0, 4.0), 0.25)]


def _config(tmp_path, monkeypatch, with_model):
    """advisory + fake printer + 6 black replay frames; a tiny flow_low checkpoint + qhat if with_model."""
    frames = tmp_path / "frames_in"
    frames.mkdir()
    for i in range(6):
        assert cv2.imwrite(str(frames / f"{i:03d}.png"), np.zeros((8, 8, 3), np.uint8))
    data = yaml.safe_load((ROOT / "config" / "default.yaml").read_text(encoding="utf-8"))
    data.update(mode="advisory", run_dir=str(tmp_path / "runs"), causes_file=str(ROOT / "config" / "causes.yaml"))
    data["printer"]["kind"] = "fake"
    data["detector"]["weights"] = "stub.pt"  # Detector is monkeypatched below
    data["camera"]["source"] = f"replay:{frames}"
    data["cause_model"].update(weights=str(tmp_path / "final.pt"), device="cpu")
    data["conformal"]["qhat_file"] = str(tmp_path / "qhat.json")
    data["proactive"]["enabled"] = False  # T-0061's path; this test is the reactive wiring only
    if with_model:
        model = build_model(len(CAUSES), 0, pretrained=False)
        with torch.no_grad():  # random backbone, head pinned to flow_low → deterministic set {flow_low}
            model.head.weight.zero_()
            model.head.bias.zero_()
            model.head.bias[CAUSES.index("flow_low")] = 10.0
        save_checkpoint(model, tmp_path / "final.pt")
        save_qhat(tmp_path / "qhat.json", 0.5, 0.1, 100)
    path = tmp_path / "cfg.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    monkeypatch.setattr(cli, "Detector", lambda *a, **k: _always("under_extrusion"))
    return path


def _db(tmp_path):
    (db_path,) = (tmp_path / "runs").glob("*/events.sqlite")
    return Store.open_readonly(db_path)


def test_explainer_wired(tmp_path, monkeypatch):
    config = _config(tmp_path, monkeypatch, with_model=True)

    assert cli.main(["run", "--config", str(config), "--max-frames", "6"]) == 0

    db = _db(tmp_path)
    (expl,) = db.query("SELECT set_json FROM explanations")
    assert expl["set_json"] == '["flow_low"]'
    (p,) = db.query("SELECT cause, var, passed FROM proposals")
    assert p == {"cause": "flow_low", "var": "flow", "passed": 1}
    assert db.query("SELECT verdict, pending FROM verdicts") == [{"verdict": "PROPOSE", "pending": 1}]


def test_no_model_fallback(tmp_path, monkeypatch, caplog):
    config = _config(tmp_path, monkeypatch, with_model=False)

    with caplog.at_level(logging.WARNING, logger="xqi.explain"):
        assert cli.main(["run", "--config", str(config), "--max-frames", "6"]) == 0

    warnings = [r for r in caplog.records if r.name == "xqi.explain"]
    assert len(warnings) == 1 and "final.pt" in warnings[0].getMessage()
    db = _db(tmp_path)
    assert db.query("SELECT COUNT(*) AS n FROM explanations")[0]["n"] == 0
    assert db.query("SELECT verdict, reason FROM verdicts") == [
        {"verdict": "ESCALATE", "reason": "no_confident_cause"}]
