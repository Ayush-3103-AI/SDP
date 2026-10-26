import time
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np
import pytest
import yaml

from xqi import __main__ as cli
from xqi.camera import open_source
from xqi.config import load
from xqi.orchestrator import Orchestrator
from xqi.printer import FakePrinter
from xqi.store import Store
from xqi.types import CauseEstimate, CauseSet, Detection, Frame

ROOT = Path(__file__).resolve().parents[1]
CFG = load(ROOT / "config" / "default.yaml")


def _replay(tmp_path, n=6):
    folder = tmp_path / "frames_in"
    folder.mkdir()
    for i in range(n):
        assert cv2.imwrite(str(folder / f"{i:03d}.png"), np.zeros((8, 8, 3), np.uint8))
    return open_source(f"replay:{folder}", 0, 0)


def _always(cls):
    return lambda frame: [Detection(frame.frame_id, cls, 0.9, (0.0, 0.0, 4.0, 4.0), 0.25)]


def _run(tmp_path, mode, detector, explainer=None, source=None, max_frames=None):
    printer = FakePrinter()
    store = Store(tmp_path / "run" / "events.sqlite")
    cfg = replace(CFG, mode=mode)
    orch = Orchestrator(cfg, printer, source or _replay(tmp_path), detector, explainer, store)
    orch.run(max_frames)
    return printer, Store.open_readonly(store.path)


class StubExplainer:
    def __init__(self, printer, store):
        self.printer, self.store, self.seen = printer, store, None

    def explain(self, cd, frame, history):
        store = Store.open_readonly(self.store.path)
        self.seen = (
            [line for _, line in self.printer.sent],
            store.query("SELECT COUNT(*) AS n FROM explanations")[0]["n"],
        )
        est = CauseEstimate({"bed_temp_low": 1.0}, "bed_temp_low", 1.0)
        return est, CauseSet(("bed_temp_low",), 0.1, 0.5), (), []


def test_critical_first(tmp_path):
    printer = FakePrinter()
    store = Store(tmp_path / "run" / "events.sqlite")
    explainer = StubExplainer(printer, store)
    orch = Orchestrator(replace(CFG, mode="auto"), printer, _replay(tmp_path),
                        _always("spaghetti"), explainer, store)
    orch.run()

    sent, n_explanations = explainer.seen
    assert sent == ["M112"] and n_explanations == 0  # acted before any explanation work
    db = Store.open_readonly(store.path)
    action = db.query("SELECT * FROM actions")
    expl = db.query("SELECT * FROM explanations")
    assert [a["source"] for a in action] == ["critical"] and action[0]["ok"] == 1
    assert len(expl) == 1 and action[0]["t_disp"] < expl[0]["t_cause"]
    assert db.query("SELECT verdict FROM verdicts")[0]["verdict"] == "CRITICAL"


def test_baseline_parity(tmp_path):
    start = time.perf_counter()
    printer, db = _run(tmp_path, "baseline", _always("under_extrusion"))

    assert [line for _, line in printer.sent] == ["M104 S205", "M220 S80", "M221 S110"]
    assert time.perf_counter() - start < 10  # Done when: end-to-end < 10 s
    assert db.query("SELECT source, ok FROM actions") == [{"source": "baseline", "ok": 1}]
    assert db.query("SELECT verdict FROM verdicts")[0]["verdict"] == "APPLY_RAW"
    assert db.query("SELECT mode, git_sha, ended_iso FROM runs")[0]["ended_iso"]
    assert (tmp_path / "run" / "frames" / "latest.jpg").exists()


def test_advisory_sends_nothing_for_non_critical(tmp_path):
    printer, db = _run(tmp_path, "advisory", _always("under_extrusion"))

    assert printer.sent == []
    assert len(db.query("SELECT * FROM defects")) == 1


def test_timings_logged(tmp_path):
    _, db = _run(tmp_path, "baseline", _always("under_extrusion"))

    defect_id = db.query("SELECT defect_id FROM defects")[0]["defect_id"]
    rows = db.query("SELECT stage, t FROM timings WHERE defect_id = ? ORDER BY id", (defect_id,))
    t = {r["stage"]: r["t"] for r in rows}
    assert set(t) == {"t0", "t_conf", "t_disp"}
    assert t["t0"] <= t["t_conf"] <= t["t_disp"]


def _frames(ts_list):
    img = np.zeros((8, 8, 3), np.uint8)
    for i, ts in enumerate(ts_list):
        yield Frame(i, ts, "", img)


def test_camera_gap_pauses(tmp_path):
    now = time.monotonic()
    printer, db = _run(tmp_path, "advisory", lambda f: [],
                       source=_frames([now, now + 1, now + 1 + CFG.camera.max_gap_s + 1]))

    assert printer.state == "Paused"
    assert [a["kind"] for a in db.query("SELECT kind FROM alerts")] == ["camera_gap"]


def test_detector_failures_pause_and_exit(tmp_path):
    def broken(frame):
        raise ValueError("boom")

    printer = FakePrinter()
    store = Store(tmp_path / "run" / "events.sqlite")
    orch = Orchestrator(CFG, printer, _frames([time.monotonic()] * 12), broken, None, store)
    with pytest.raises(RuntimeError):
        orch.run()

    assert printer.state == "Paused"
    db = Store.open_readonly(store.path)
    assert [a["kind"] for a in db.query("SELECT kind FROM alerts")] == ["detector_failure"]


def test_max_frames_stops_early(tmp_path):
    printer, _ = _run(tmp_path, "baseline", _always("under_extrusion"), max_frames=3)

    assert printer.sent == []  # under_extrusion needs 4 hits


def test_cli_run_mode_overrides_config(tmp_path, monkeypatch):
    data = yaml.safe_load((ROOT / "config" / "default.yaml").read_text(encoding="utf-8"))
    data["printer"]["kind"] = "fake"
    data["camera"]["source"] = f"replay:{tmp_path / 'frames_in'}"
    data["run_dir"] = str(tmp_path / "runs")
    _replay(tmp_path)
    config = tmp_path / "cfg.yaml"
    config.write_text(yaml.safe_dump(data), encoding="utf-8")
    monkeypatch.setattr(cli, "Detector", lambda *a, **k: _always("under_extrusion"))

    assert cli.main(["run", "--config", str(config), "--mode", "baseline", "--max-frames", "5"]) == 0

    (db_path,) = (tmp_path / "runs").glob("*/events.sqlite")
    assert db_path.parent.name.endswith("Z")  # run_id = UTC timestamp
    db = Store.open_readonly(db_path)
    assert db.query("SELECT mode FROM runs")[0]["mode"] == "baseline"
    assert db.query("SELECT source FROM actions") == [{"source": "baseline"}]
