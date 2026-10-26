import json
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
from xqi.explain.counterfactual import make_proposal
from xqi.orchestrator import Orchestrator
from xqi.printer import FakePrinter
from xqi.store import Store
from xqi.types import (
    CauseEstimate,
    CauseSet,
    ConfirmedDefect,
    Detection,
    Frame,
    OperatorDecision,
)

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


def _run(tmp_path, mode, detector, explainer=None, source=None, max_frames=None, printer=None):
    printer = printer or FakePrinter()
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


class SetExplainer:
    """Fixed cause set; proposals from the latest state, like the real Explainer."""

    def __init__(self, *members, p_top=0.9):
        self.members, self.p_top = members, p_top

    def explain(self, cd, frame, history):
        probs = {c: self.p_top / len(self.members) for c in self.members}
        est = CauseEstimate(probs, self.members[0], self.p_top)
        props = [make_proposal(c, probs[c], cd.severity, history[-1], CFG, cd.defect_id)
                 for c in self.members]
        return est, CauseSet(self.members, 0.1, 0.5), (), [p for p in props if p]


def _verdict(db):
    return db.query("SELECT verdict, pending, deadline_ts, t_gate FROM verdicts")[0]


def test_modes(tmp_path):
    printer, db = _run(tmp_path / "a", "auto", _always("under_extrusion"), SetExplainer("flow_low"))
    assert [line for _, line in printer.sent] == ["M221 S108"]  # severity 0.63 → +8.2 % (07 §2)
    assert _verdict(db)["verdict"] == "APPLY"
    assert db.query("SELECT source, proposal_id, ok FROM actions") == [
        {"source": "auto", "proposal_id": db.query("SELECT proposal_id FROM proposals")[0]["proposal_id"],
         "ok": 1}]

    printer, db = _run(tmp_path / "b", "auto", _always("under_extrusion"),
                       SetExplainer("flow_low", "speed_high"))
    v = _verdict(db)
    assert printer.sent == [] and v["verdict"] == "PROPOSE" and v["pending"] == 1
    assert v["deadline_ts"] == pytest.approx(v["t_gate"] + CFG.hitl.timeout_s)
    assert db.query("SELECT COUNT(*) AS n FROM proposals WHERE passed = 1")[0]["n"] == 2

    printer, db = _run(tmp_path / "c", "advisory", _always("under_extrusion"), SetExplainer("flow_low"))
    assert printer.sent == [] and _verdict(db)["verdict"] == "PROPOSE"
    assert db.query("SELECT COUNT(*) AS n FROM actions")[0]["n"] == 0

    printer, db = _run(tmp_path / "d", "auto", _always("under_extrusion"), SetExplainer("misalignment"))
    assert printer.sent == [] and printer.state == "Paused"
    assert _verdict(db)["verdict"] == "ESCALATE" and _verdict(db)["pending"] == 1

    printer = FakePrinter()
    printer.send_gcode(["M104 S210"])  # nozzle in cooldown → L2 blocks that recipe line
    printer.sent.clear()
    printer, db = _run(tmp_path / "e", "gated-recipe", _always("under_extrusion"), printer=printer)
    assert [line for _, line in printer.sent] == ["M220 S90", "M221 S110"]  # L2-clipped survivors
    assert _verdict(db)["verdict"] == "APPLY"
    assert db.query("SELECT COUNT(*) AS n FROM proposals WHERE passed = 0")[0]["n"] == 1
    assert db.query("SELECT COUNT(*) AS n FROM explanations")[0]["n"] == 0  # no cause model, no L4


def test_apply_updates_state(tmp_path):
    printer, db = _run(tmp_path, "auto", _always("under_extrusion"), SetExplainer("flow_low"))

    state = printer.get_state()
    (t_disp,) = [a["t_disp"] for a in db.query("SELECT t_disp FROM actions")]
    assert state.flow_pct == 108 and state.last_change_ts["flow"] == pytest.approx(t_disp, abs=0.1)
    assert db.query("SELECT COUNT(*) AS n FROM outcomes")[0]["n"] == 1  # Verifier.watch started


class ModelDetector:
    model = object()  # stands in for the YOLO backbone; eigencam is stubbed

    def __call__(self, frame):
        return _always("under_extrusion")(frame)


def test_heatmap_after_dispatch(tmp_path, monkeypatch):
    from xqi.explain import attribution

    # 20 ms like a real pass; Windows' monotonic clock is too coarse to order two instant writes.
    monkeypatch.setattr(attribution, "eigencam",
                        lambda *a: time.sleep(0.02) or np.ones((4, 4), np.float32))
    _, db = _run(tmp_path, "auto", ModelDetector(), SetExplainer("flow_low"))

    (row,) = db.query("SELECT defect_id, heatmap_path FROM defects")
    assert Path(row["heatmap_path"]) == tmp_path / "run" / "heatmaps" / f"{row['defect_id']}.png"
    assert Path(row["heatmap_path"]).exists()
    t = {r["stage"]: r["t"] for r in db.query("SELECT stage, t FROM timings")}
    assert t["t_heatmap"] > db.query("SELECT t_disp FROM actions")[0]["t_disp"]


class DeadPrinter(FakePrinter):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def send_gcode(self, lines):
        self.calls += 1
        return False


def test_dispatch_failure(tmp_path):
    printer = DeadPrinter()
    before = printer.get_state()
    printer, db = _run(tmp_path, "auto", _always("under_extrusion"), SetExplainer("flow_low"),
                       printer=printer)

    assert printer.calls == 2  # one retry
    assert db.query("SELECT ok FROM actions") == [{"ok": 0}]
    after = printer.get_state()
    assert (after.flow_pct, after.last_change_ts) == (before.flow_pct, before.last_change_ts)
    assert [a["kind"] for a in db.query("SELECT kind FROM alerts")] == ["dispatch_failed"]
    assert db.query("SELECT COUNT(*) AS n FROM outcomes")[0]["n"] == 0


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


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


def _pending(tmp_path, cause, cls="under_extrusion", cfg=CFG):
    """Advisory loop with one PROPOSE event pending; returns (orch, printer, clock, defect_id)."""
    clock = Clock()
    printer = FakePrinter(clock=clock)
    store = Store(tmp_path / "run" / "events.sqlite")
    orch = Orchestrator(replace(cfg, mode="advisory"), printer, iter(()), None,
                        SetExplainer(cause), store, clock=clock)
    cd = ConfirmedDefect("d1", cls, 0, clock.t, clock.t, 0.9, (0.0, 0.0, 4.0, 4.0), 0.25, 4, 0.63, False)
    orch.handle_event(cd, Frame(0, clock.t, "", np.zeros((8, 8, 3), np.uint8)))
    assert _verdict(store)["pending"] == 1 and printer.sent == []
    return orch, printer, clock, cd.defect_id


def _decide(orch, defect_id, choice, delta=None):
    pid = orch.store.query("SELECT proposal_id FROM proposals")[0]["proposal_id"]
    ui =Store.open_readonly(orch.store.path)  # the UI's only write path
    ui.insert_decision(OperatorDecision(pid, defect_id, choice, delta, "op", "", 1.0))
    ui.close()


def _sent(printer):
    return [line for _, line in printer.sent]


def test_modify_regated(tmp_path):
    orch, printer, _, d = _pending(tmp_path, "nozzle_temp_low")
    _decide(orch, d, "modify", 15.0)
    orch.process_operator_decisions()

    assert _sent(printer) == ["M104 S215"]  # 210 + 15 clipped to the L2 step (+5 °C)
    (p,) = orch.store.query("SELECT delta, gate_json FROM proposals WHERE cause = 'operator'")
    g = json.loads(p["gate_json"])
    assert p["delta"] == 15.0 and g["clipped"] and g["layers"][0]["reason"] == "L2: clipped +15 → +5 °C"
    assert orch.store.query("SELECT source FROM actions") == [{"source": "operator"}]
    assert orch.store.new_decisions() == [] and _verdict(orch.store)["pending"] == 0


def test_apply_rechecks_cooldown(tmp_path):
    orch, printer, clock, d = _pending(tmp_path, "flow_low")
    clock.t += 5
    printer.send_gcode(["M221 S100"])  # flow changed after the proposal: L2 cooldown now applies
    printer.sent.clear()
    clock.t += 5
    _decide(orch, d, "apply")
    orch.process_operator_decisions()

    assert printer.sent == []
    (a,) = orch.store.query("SELECT kind, message FROM alerts")
    assert a["kind"] == "decision_blocked" and "L2: cooldown 5s < 20s" in a["message"]
    assert orch.store.new_decisions() == [] and _verdict(orch.store)["pending"] == 0


def test_pause_stop(tmp_path):
    orch, printer, _, d = _pending(tmp_path / "a", "flow_low")
    _decide(orch, d, "pause")
    orch.process_operator_decisions()
    assert printer.state == "Paused" and printer.sent == []

    orch, printer, _, d = _pending(tmp_path / "b", "flow_low")
    _decide(orch, d, "stop")
    orch.process_operator_decisions()
    assert _sent(printer) == ["M112"] and printer.state == "Error"
    assert orch.store.query("SELECT source, gcode_json FROM actions") == [
        {"source": "operator", "gcode_json": '["M112"]'}]


@pytest.mark.parametrize("action, state", [("noop", "Printing"), ("pause", "Paused")])
def test_timeout(tmp_path, action, state):
    cfg = replace(CFG, hitl=replace(CFG.hitl, timeout_action=action))
    orch, printer, clock, d = _pending(tmp_path, "flow_low", cfg=cfg)
    clock.t += CFG.hitl.timeout_s - 1
    orch.check_timeouts()
    assert _verdict(orch.store)["pending"] == 1  # not yet

    clock.t += 2
    orch.check_timeouts()
    assert printer.state == state and printer.sent == []
    assert _verdict(orch.store)["pending"] == 0
    (row,) = orch.store.query("SELECT defect_id, choice, consumed, latency_s FROM operator_decisions")
    assert row == {"defect_id": d, "choice": "timeout", "consumed": 1,
                   "latency_s": pytest.approx(CFG.hitl.timeout_s + 1)}
    sources = [a["source"] for a in orch.store.query("SELECT source FROM actions")]
    assert sources == (["timeout"] if action == "pause" else [])


def test_duplicate_decision_ignored(tmp_path):
    orch, printer, _, d = _pending(tmp_path, "flow_low")
    _decide(orch, d, "apply")
    _decide(orch, d, "apply")  # double click
    orch.process_operator_decisions()
    _decide(orch, d, "modify", 5.0)  # late, after the event was consumed
    _decide(orch, "nope", "apply")  # unknown event
    orch.process_operator_decisions()

    assert _sent(printer) == ["M221 S108"]  # dispatched once
    assert [a["kind"] for a in orch.store.query("SELECT kind FROM alerts")] == ["decision_ignored"] * 3
    assert orch.store.new_decisions() == []


def test_decisions_processed_in_loop(tmp_path):
    store = Store(tmp_path / "run" / "events.sqlite")

    def detector(frame):  # the operator answers the card while frame 5 is being processed
        if frame.frame_id == 5:
            (p,) = store.query("SELECT proposal_id, defect_id FROM proposals")
            store.insert_decision(OperatorDecision(p["proposal_id"], p["defect_id"], "apply", None,
                                                   "op", "", 1.0))
        return _always("under_extrusion")(frame)

    printer = FakePrinter()
    Orchestrator(replace(CFG, mode="advisory"), printer, _replay(tmp_path), detector,
                 SetExplainer("flow_low"), store).run()
    assert _sent(printer) == ["M221 S108"]


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
