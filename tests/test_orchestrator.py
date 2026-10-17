"""T-0033 — the orchestrator: baseline, critical-first, timings, CLI, cleanup.

Also the gate -> dispatch integration scenarios of the P3 brief: a permitted
decision is the only thing that can reach the printer, a rejected decision
dispatches nothing, and a cooldown blocks a repeat.
"""

from __future__ import annotations

import dataclasses
import time
from pathlib import Path

import numpy as np
import pytest

from xqi.camera import CameraError, open_source
from xqi.config import load
from xqi.detect import DetectorError
from xqi.explain.counterfactual import make_proposal
from xqi.gate import event_verdict, gate
from xqi.orchestrator import DetectorFailure, Orchestrator
from xqi.printer import FakePrinter
from xqi.store import Store
from xqi.types import ConfirmedDefect, Detection, Frame, PrinterState

ROOT = Path(__file__).resolve().parents[1]
CFG = load(ROOT / "config" / "default.yaml")

IMAGE = np.zeros((8, 8, 3), dtype=np.uint8)


# -- helpers --------------------------------------------------------------- #

class FakeClock:
    def __init__(self, t: float = 1000.0) -> None:
        self.t = float(t)

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


class StubDetector:
    def __init__(self, by_frame=None, *, fail_first=0, always_fail=False) -> None:
        self._by_frame = dict(by_frame or {})
        self._fail_first = fail_first
        self._always_fail = always_fail

    def __call__(self, frame: Frame) -> list[Detection]:
        if self._always_fail or self._fail_first > 0:
            if self._fail_first > 0:
                self._fail_first -= 1
            raise RuntimeError("detector boom")
        return list(self._by_frame.get(frame.frame_id, []))


def clocked_source(clock: FakeClock, count: int, step: float = 1.0):
    for index in range(count):
        clock.advance(step)
        yield Frame(frame_id=index, ts=clock(), wall_iso="t", image=IMAGE)


def detection(cls: str, frame_id: int = 0, conf: float = 0.9) -> Detection:
    return Detection(
        frame_id=frame_id,
        cls=cls,
        conf=conf,
        xyxy=(0.0, 0.0, 4.0, 4.0),
        area_frac=0.25,
    )


def detections_for(count: int, classes=("under_extrusion",)) -> dict[int, list[Detection]]:
    return {
        index: [detection(cls, frame_id=index) for cls in classes]
        for index in range(count)
    }


def config(mode: str = "baseline", **nested) -> object:
    cfg = dataclasses.replace(CFG, mode=mode)

    if "hits" in nested:
        hits = dict(cfg.confirm.hits)
        hits.update(nested.pop("hits"))
        cfg = dataclasses.replace(cfg, confirm=dataclasses.replace(cfg.confirm, hits=hits))

    if "critical" in nested:
        cfg = dataclasses.replace(
            cfg,
            critical=dataclasses.replace(cfg.critical, **nested.pop("critical")),
        )

    if "verify" in nested:
        cfg = dataclasses.replace(
            cfg,
            verify=dataclasses.replace(cfg.verify, **nested.pop("verify")),
        )

    assert not nested
    return cfg


def run_loop(cfg, detector, count, tmp_path, *, step=1.0, printer=None, clock=None):
    clock = clock or FakeClock()
    printer = printer or FakePrinter(clock=clock, nominal=cfg.printer.nominal)
    db_path = tmp_path / "events.sqlite"
    store = Store(db_path)
    orchestrator = Orchestrator(
        cfg,
        printer,
        clocked_source(clock, count, step),
        detector,
        None,
        store,
        clock=clock,
    )
    orchestrator.run()
    return printer, db_path


def rows(db_path: Path, table: str) -> list[dict]:
    store = Store.open_readonly(db_path)
    try:
        return store.query(f"SELECT * FROM {table} ORDER BY rowid")
    finally:
        store.close()


# -- baseline (FR-023, ADR-0001) ------------------------------------------- #

def test_baseline_parity_sends_the_deck_recipe(tmp_path):
    cfg = config("baseline")
    printer, db = run_loop(cfg, StubDetector(detections_for(4)), 4, tmp_path)

    assert [line for _, line in printer.sent] == ["M104 S205", "M220 S80", "M221 S110"]

    actions = rows(db, "actions")
    assert len(actions) == 1
    assert actions[0]["source"] == "baseline"
    assert actions[0]["ok"] == 1

    verdicts = rows(db, "verdicts")
    assert [verdict["verdict"] for verdict in verdicts] == ["APPLY_RAW"]


def test_baseline_needs_the_confirmation_streak(tmp_path):
    cfg = config("baseline")
    # hits: under_extrusion = 4; only 3 frames present.
    printer, _ = run_loop(cfg, StubDetector(detections_for(3)), 3, tmp_path)

    assert printer.sent == []


def test_baseline_timings_are_logged(tmp_path):
    cfg = config("baseline")
    _, db = run_loop(cfg, StubDetector(detections_for(4)), 4, tmp_path)

    timings = rows(db, "timings")
    stages = {row["stage"] for row in timings}
    assert {"t0", "t_conf", "t_disp"} <= stages

    defect_id = rows(db, "defects")[0]["defect_id"]
    assert {row["stage"] for row in timings if row["defect_id"] == defect_id} >= {
        "t0",
        "t_conf",
        "t_disp",
    }


def test_baseline_outcome_is_written_when_the_window_closes(tmp_path):
    cfg = config("baseline", hits={"under_extrusion": 12}, verify={"window_s": 20, "settle_s": 2})
    _, db = run_loop(cfg, StubDetector(detections_for(45)), 45, tmp_path)

    outcomes = rows(db, "outcomes")
    assert len(outcomes) == 1
    assert outcomes[0]["cls"] == "under_extrusion"
    assert outcomes[0]["verdict"] in {"resolved", "persisted", "worsened"}


# -- critical-first (FR-005) ----------------------------------------------- #

def test_critical_first_estop_before_any_explanation(tmp_path):
    cfg = config("advisory", hits={"over_extrusion": 2, "spaghetti": 2})
    detector = StubDetector(detections_for(2, classes=("over_extrusion", "spaghetti")))

    printer, db = run_loop(cfg, detector, 2, tmp_path)

    assert [line for _, line in printer.sent] == ["M112"]
    assert printer.state == "Error"

    actions = rows(db, "actions")
    assert [action["source"] for action in actions] == ["critical"]

    # Critical acts before any explanation; P3 writes none at all.
    assert rows(db, "explanations") == []

    # The non-critical class did not dispatch anything.
    verdicts = {row["verdict"] for row in rows(db, "verdicts")}
    assert "CRITICAL" in verdicts
    assert "APPLY_RAW" not in verdicts


def test_critical_first_orders_before_a_noncritical_action(tmp_path):
    cfg = config(
        "baseline",
        hits={"over_extrusion": 2, "spaghetti": 2},
        critical={"spaghetti": "pause"},
    )
    detector = StubDetector(detections_for(2, classes=("over_extrusion", "spaghetti")))

    printer, db = run_loop(cfg, detector, 2, tmp_path)

    # The critical pause is handled before the over_extrusion baseline recipe,
    # even though over_extrusion comes first in DEFECTS.
    actions = rows(db, "actions")
    assert [action["source"] for action in actions] == ["critical", "baseline"]
    assert printer.state == "Paused"
    assert [line for _, line in printer.sent] == ["M104 S190", "M220 S95", "M221 S80"]


def test_critical_pause_action_sends_no_gcode(tmp_path):
    cfg = config("advisory", hits={"clog": 1}, critical={"clog": "pause"})
    printer, db = run_loop(cfg, StubDetector(detections_for(1, classes=("clog",))), 1, tmp_path)

    assert printer.sent == []
    assert printer.state == "Paused"
    assert rows(db, "actions")[0]["gcode_json"] == "[]"


# -- failure handling ------------------------------------------------------ #

def test_detector_failure_skips_the_frame(tmp_path):
    cfg = config("baseline")
    detector = StubDetector(detections_for(4), fail_first=1)
    # Shift the detections so frame 1 still confirms after the dropped frame 0.
    detector._by_frame[4] = [detection("under_extrusion", frame_id=4)]

    printer, db = run_loop(cfg, detector, 5, tmp_path)

    assert [line for _, line in printer.sent] == ["M104 S205", "M220 S80", "M221 S110"]
    alerts = rows(db, "alerts")
    assert [alert["kind"] for alert in alerts] == ["detector_error"]


def test_ten_detector_failures_stop_the_loop(tmp_path):
    cfg = config("baseline")
    clock = FakeClock()
    printer = FakePrinter(clock=clock, nominal=cfg.printer.nominal)
    db_path = tmp_path / "events.sqlite"
    store = Store(db_path)
    orchestrator = Orchestrator(
        cfg,
        printer,
        clocked_source(clock, 12),
        StubDetector(always_fail=True),
        None,
        store,
        clock=clock,
    )

    with pytest.raises(DetectorFailure):
        orchestrator.run()

    assert printer.state == "Paused"
    kinds = [alert["kind"] for alert in rows(db_path, "alerts")]
    assert kinds.count("detector_error") == 10
    assert "detector_failure" in kinds


def test_inference_failure_does_not_fabricate_a_correction(tmp_path):
    cfg = config("baseline")
    detector = StubDetector(detections_for(4), fail_first=2)

    printer, db = run_loop(cfg, detector, 6, tmp_path)

    assert printer.sent == []
    assert rows(db, "actions") == []
    assert rows(db, "defects") == []


def test_disconnected_printer_blocks_baseline_dispatch(tmp_path):
    cfg = config("baseline")
    printer = FakePrinter(nominal=cfg.printer.nominal)
    printer.connected = False

    _, db = run_loop(cfg, StubDetector(detections_for(4)), 4, tmp_path, printer=printer)

    assert printer.sent == []
    action = rows(db, "actions")[0]
    assert action["source"] == "baseline"
    assert action["ok"] == 0
    assert rows(db, "outcomes") == []


def test_camera_gap_pauses_the_printer(tmp_path):
    cfg = config("baseline")
    printer, db = run_loop(
        cfg,
        StubDetector({}),
        3,
        tmp_path,
        step=10.0,  # > max_gap_s (3.0)
    )

    assert printer.state == "Paused"
    assert "camera_gap" in [alert["kind"] for alert in rows(db, "alerts")]


def test_camera_failure_cleans_up_and_dispatches_nothing(tmp_path):
    cfg = config("baseline")
    clock = FakeClock()
    printer = FakePrinter(clock=clock, nominal=cfg.printer.nominal)
    db_path = tmp_path / "events.sqlite"
    store = Store(db_path)

    def failing_source():
        clock.advance(1.0)
        yield Frame(frame_id=0, ts=clock(), wall_iso="t", image=IMAGE)
        raise CameraError("camera unplugged")

    orchestrator = Orchestrator(
        cfg, printer, failing_source(), StubDetector({}), None, store, clock=clock
    )

    with pytest.raises(CameraError):
        orchestrator.run()

    assert printer.sent == []
    # The store was flushed and closed on the way out.
    assert rows(db_path, "runs")


def test_detector_init_failure_is_explicit(tmp_path):
    from xqi.__main__ import _build_detector

    cfg = dataclasses.replace(
        CFG,
        detector=dataclasses.replace(CFG.detector, kind="yolo", weights="missing.pt"),
    )

    with pytest.raises(DetectorError):
        _build_detector(cfg)


def test_multiple_runs_do_not_leak_confirmation_state(tmp_path):
    cfg = config("baseline")

    first_printer, _ = run_loop(cfg, StubDetector(detections_for(4)), 4, tmp_path)
    assert len(first_printer.sent) == 3

    second_dir = tmp_path / "second"
    second_dir.mkdir()
    second_printer, _ = run_loop(cfg, StubDetector(detections_for(1)), 1, second_dir)
    assert second_printer.sent == []


# -- gate -> dispatch integration (P3 brief, scenarios 2/3/9) -------------- #

def state_at(*, flow=100.0, last_change=None) -> PrinterState:
    return PrinterState(
        ts=0.0,
        state="Printing",
        nozzle_actual_c=210.0,
        nozzle_target_c=210.0,
        bed_actual_c=60.0,
        bed_target_c=60.0,
        flow_pct=flow,
        speed_pct=100.0,
        progress_pct=50.0,
        last_change_ts=dict(last_change or {}),
    )


def test_permitted_decision_is_the_only_thing_dispatched(tmp_path):
    state = state_at()
    printer = FakePrinter()

    proposal = make_proposal("flow_low", 0.9, 0.5, state, CFG)
    decision = gate(proposal, state, now=1000.0, cfg=CFG)

    assert decision.passed is True
    assert decision.final_gcode

    if decision.passed:
        printer.send_gcode(decision.final_gcode)

    assert [line for _, line in printer.sent] == list(decision.final_gcode)


def test_rejected_decision_dispatches_nothing(tmp_path):
    printer = FakePrinter()

    # Outside the characterised window, and moving away from it -> L3 rejects.
    state = state_at(flow=105.0)
    proposal = make_proposal("flow_low", 0.9, 1.0, state, CFG)
    decision = gate(proposal, state, now=1000.0, cfg=CFG)

    assert decision.passed is False
    assert decision.final_gcode == ()

    if decision.passed:
        printer.send_gcode(decision.final_gcode)

    assert printer.sent == []


def test_cooldown_blocks_a_repeat(tmp_path):
    printer = FakePrinter()

    hot = state_at(last_change={"flow": 999.0})
    proposal = make_proposal("flow_low", 0.9, 0.5, hot, CFG)
    decision = gate(proposal, hot, now=1000.0, cfg=CFG)

    assert decision.passed is False  # 1s since the last flow change < 20s cooldown

    if decision.passed:
        printer.send_gcode(decision.final_gcode)

    assert printer.sent == []


def test_missing_telemetry_fails_closed(tmp_path):
    printer = FakePrinter()

    # No state at all: the gate refuses and carries no G-code.
    proposal = make_proposal("flow_low", 0.9, 0.5, state_at(), CFG)
    decision = gate(proposal, None, now=1000.0, cfg=CFG)

    assert decision.passed is False
    assert decision.final_gcode == ()
    assert "state_unavailable" in [layer.reason for layer in decision.layers]

    defect = ConfirmedDefect(
        defect_id="d",
        cls="under_extrusion",
        frame_id=0,
        t0=0.0,
        t_conf=1.0,
        conf=0.9,
        xyxy=(0.0, 0.0, 1.0, 1.0),
        area_frac=0.1,
        recent_hits=4,
        severity=0.5,
        critical=False,
    )
    verdict = event_verdict("advisory", defect, None, None, [], [decision], None, CFG)

    assert verdict.verdict == "ESCALATE"
    assert verdict.reason == "state_unavailable"

    if decision.passed:
        printer.send_gcode(decision.final_gcode)

    assert printer.sent == []


# -- end to end ------------------------------------------------------------ #

def test_end_to_end_replay_under_ten_seconds(tmp_path):
    import cv2

    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    for index in range(4):
        image = np.full((16, 16, 3), 20 + index, dtype=np.uint8)
        assert cv2.imwrite(str(frames_dir / f"frame_{index:02d}.png"), image)

    cfg = config("baseline")
    printer = FakePrinter(nominal=cfg.printer.nominal)
    detector = StubDetector({index: [detection("under_extrusion", frame_id=index)] for index in range(4)})

    db_path = tmp_path / "events.sqlite"
    store = Store(db_path)
    source = open_source(f"replay:{frames_dir}", 16, 16)
    orchestrator = Orchestrator(cfg, printer, source, detector, None, store)

    start = time.perf_counter()
    orchestrator.run()
    elapsed = time.perf_counter() - start

    assert elapsed < 10.0
    assert [line for _, line in printer.sent] == ["M104 S205", "M220 S80", "M221 S110"]
    assert len(rows(db_path, "defects")) == 1
    assert len(rows(db_path, "actions")) == 1


def test_run_header_records_mode_and_git_sha(tmp_path):
    cfg = config("baseline")
    _, db = run_loop(cfg, StubDetector({}), 1, tmp_path)

    run = rows(db, "runs")[0]
    assert run["mode"] == "baseline"
    assert run["git_sha"]


# -- CLI ------------------------------------------------------------------- #

def _demo_config_path(tmp_path) -> Path:
    import yaml

    with (ROOT / "config" / "baseline_demo.yaml").open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    data["run_dir"] = str(tmp_path / "runs")
    data["camera"]["source"] = f"replay:{ROOT / 'demo' / 'frames'}"
    data["detector"]["weights"] = str(ROOT / "demo" / "detections.json")

    path = tmp_path / "demo.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_cli_runs_baseline_offline(tmp_path):
    from xqi.__main__ import main

    config_path = _demo_config_path(tmp_path)

    code = main(
        ["run", "--config", str(config_path), "--mode", "baseline", "--max-frames", "8"]
    )

    assert code == 0
    db_path = next((tmp_path / "runs").glob("*/events.sqlite"))
    actions = rows(db_path, "actions")
    assert actions[0]["gcode_json"] == '["M104 S205","M220 S80","M221 S110"]'
    assert rows(db_path, "runs")[0]["mode"] == "baseline"


def test_cli_max_frames_zero_runs_nothing(tmp_path):
    from xqi.__main__ import main

    config_path = _demo_config_path(tmp_path)

    code = main(["run", "--config", str(config_path), "--max-frames", "0"])

    assert code == 0
    db_path = next((tmp_path / "runs").glob("*/events.sqlite"))
    assert rows(db_path, "actions") == []


def test_cli_reports_a_bad_config(tmp_path):
    from xqi.__main__ import main

    code = main(["run", "--config", str(tmp_path / "missing.yaml")])

    assert code == 1
