import os

import cv2
import numpy as np
import pytest

from xqi import ui_data
from xqi.store import Store
from xqi.types import (
    CauseEstimate,
    CauseSet,
    ConfirmedDefect,
    Detection,
    EventVerdict,
    GateDecision,
    LayerResult,
    PrinterState,
    Proposal,
)


def make_state(ts: float, state: str = "Printing") -> PrinterState:
    return PrinterState(
        ts=ts,
        state=state,
        nozzle_actual_c=200.0,
        nozzle_target_c=200.0,
        bed_actual_c=60.0,
        bed_target_c=60.0,
        flow_pct=100.0,
        speed_pct=100.0,
        progress_pct=None,
        last_change_ts={},
    )


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "runs" / "run-001" / "events.sqlite"
    with Store(path) as store:
        store.write_run({"run_id": "run-001", "mode": "advisory", "cfg": {}})
        store.write_telemetry(make_state(1.0, "Operational"))
        store.write_telemetry(make_state(2.0, "Printing"))
        store.write_defect(
            ConfirmedDefect(
                defect_id="d1", cls="stringing", frame_id=3, t0=2.5, t_conf=3.0,
                conf=0.8, xyxy=(0, 0, 10, 10), area_frac=0.01, recent_hits=3,
                severity=0.4, critical=False,
            )
        )
        store.write_verdict(
            EventVerdict("d1", "PROPOSE", "low confidence", ()), t_gate=3.1, pending=True
        )
        store.write_action("a1", "d1", None, "critical", ["M112"], 3.2, True)
        for i in range(60):
            store.write_alert(10.0 + i, "stale_telemetry", f"alert {i}")
    return path


def test_latest_state_and_mode(db):
    with Store.open_readonly(db) as store:
        assert ui_data.latest_state(store)["state"] == "Printing"
        assert ui_data.run_mode(store) == "advisory"


def test_empty_db(tmp_path):
    path = tmp_path / "run-x" / "events.sqlite"
    Store(path).close()
    with Store.open_readonly(path) as store:
        assert ui_data.latest_state(store) is None
        assert ui_data.run_mode(store) is None
        assert ui_data.last_events(store) == []
        assert ui_data.recent_alerts(store) == []


def test_last_events_newest_first_capped(db):
    with Store.open_readonly(db) as store:
        events = ui_data.last_events(store)
        assert len(events) == 50
        assert [e["t"] for e in events] == sorted((e["t"] for e in events), reverse=True)
        assert events[0]["message"] == "stale_telemetry: alert 59"

        few = ui_data.last_events(store, n=63)
        assert [e["kind"] for e in few[-3:]] == ["action", "verdict", "defect"]
        assert few[-1]["message"] == "stringing conf=0.80 severity=0.40"
        assert few[-2]["message"] == "PROPOSE (pending): low confidence"
        assert few[-3]["message"] == "critical: M112 ok"


def test_recent_alerts(db):
    with Store(db) as store:
        store.write_alert(-100.0, "stale_frame", "long ago")
    with Store.open_readonly(db) as store:
        alerts = ui_data.recent_alerts(store, n=3)
        assert [a["message"] for a in alerts] == ["alert 59", "alert 58", "alert 57"]
        assert "long ago" not in [a["message"] for a in ui_data.recent_alerts(store, n=100)]


def test_resolve_run(db, tmp_path):
    runs = tmp_path / "runs"
    newer = runs / "run-002" / "events.sqlite"
    Store(newer).close()
    os.utime(db, (1, 1))
    assert ui_data.resolve_run(runs, "latest") == newer
    assert ui_data.resolve_run(runs, "run-001") == db
    with pytest.raises(FileNotFoundError):
        ui_data.resolve_run(runs, "nope")
    with pytest.raises(FileNotFoundError):
        ui_data.resolve_run(tmp_path / "empty", "latest")


def test_save_latest_frame(tmp_path):
    image = np.zeros((480, 1280, 3), dtype=np.uint8)
    det = Detection(1, "spaghetti", 0.9, (100.0, 100.0, 300.0, 300.0), 0.05)
    path = ui_data.save_latest_frame(tmp_path, image, [det], width=640)

    assert path == tmp_path / "frames" / "latest.jpg"
    saved = cv2.imread(str(path))
    assert saved.shape == (240, 640, 3)
    assert saved.any()  # the box was drawn
    assert image.sum() == 0  # caller's frame untouched
    assert list((tmp_path / "frames").iterdir()) == [path]


def test_live_view_shows_all_elements(db, monkeypatch):
    from streamlit.testing.v1 import AppTest

    image = np.zeros((480, 640, 3), dtype=np.uint8)
    ui_data.save_latest_frame(db.parent, image, [Detection(1, "stringing", 0.8, (1, 1, 50, 50), 0.01)])
    monkeypatch.setattr("sys.argv", ["ui.py", "--run", "run-001", "--run-dir", str(db.parent.parent)])

    at = AppTest.from_file("../xqi/ui.py").run(timeout=30)

    assert not at.exception
    assert at.error[0].value.startswith("stale_telemetry: alert 59")  # red alert banner
    assert {m.label: m.value for m in at.metric}["Mode"] == "advisory"
    assert {m.label: m.value for m in at.metric}["Printer"] == "Printing"
    assert len(at.dataframe[0].value) == 50
    assert at.get("image")  # latest frame


def make_gate(pid: str, delta: float) -> GateDecision:
    layers = (
        LayerResult("L2", True, f"L2: {delta:+g} % within ±10"),
        LayerResult("L1", True, "L1: 108 % within [80, 120]"),
        LayerResult("L3", True, "L3: 108 % inside [80, 120]"),
    )
    return GateDecision(pid, True, False, delta, 100 + delta, (f"M221 S{100 + delta:g}",), layers)


@pytest.fixture
def card_db(db):
    with Store(db) as store:
        store.write_run({"run_id": "run-001", "mode": "advisory", "cfg": {"conformal": {"alpha": 0.1}}})
        store.write_telemetry(make_state(33.1))
        store.write_explanation(
            "d1",
            CauseEstimate({"flow_low": 0.64, "nozzle_cold": 0.22, "speed_high": 0.14}, "flow_low", 0.64),
            CauseSet(("flow_low", "nozzle_cold"), 0.1, 0.7), 0.7, ["telemetry_stale"], 3.05,
        )
        store.write_proposal(
            Proposal("d1-flow_low", "d1", "flow_low", "flow", 100.0, 8.0, 108.0, ("M221 S108",), "Flow sentence."),
            make_gate("d1-flow_low", 8.0),
        )
        store.write_proposal(
            Proposal("d1-nozzle_cold", "d1", "nozzle_cold", "nozzle_temp", 200.0, 4.0, 204.0, ("M104 S204",), "N."),
        )
        store.write_verdict(
            EventVerdict("d1", "PROPOSE", "two causes in the set", ("d1-flow_low", "d1-nozzle_cold")),
            t_gate=3.1, pending=True, deadline_ts=93.1,
        )
    return db


def test_card_model(card_db):
    with Store.open_readonly(card_db) as store:
        assert [e["defect_id"] for e in store.pending_events()] == ["d1"]
        card = ui_data.card_model(store, "d1")
        assert ui_data.card_model(store, "nope") is None

    assert (card["defect_id"], card["cls"], card["severity"]) == ("d1", "stringing", pytest.approx(0.4))
    assert card["crop_path"] is None and card["heatmap_path"] is None  # UI shows "computing…"
    assert card["causes"] == [("flow_low", 0.64), ("nozzle_cold", 0.22)]  # set members, most likely first
    assert card["alpha"] == 0.1
    assert card["flags"] == ["telemetry_stale"]
    assert (card["verdict"], card["reason"]) == ("PROPOSE", "two causes in the set")
    assert card["remaining_s"] == pytest.approx(93.1 - 33.1)  # deadline - latest telemetry (loop clock)
    assert card["latency_s"] == pytest.approx(33.1 - 3.1)

    flow, nozzle = card["proposals"]
    assert (flow["proposal_id"], flow["var"], flow["from_value"], flow["to_value"], flow["delta"], flow["unit"]) == (
        "d1-flow_low", "flow", 100.0, 108.0, 8.0, "%")
    assert flow["passed"] is True and flow["clipped"] is False
    assert [(lay["layer"], lay["passed"]) for lay in flow["layers"]] == [("L2", True), ("L1", True), ("L3", True)]
    assert flow["layers"][0]["reason"] == "L2: +8 % within ±10"
    assert flow["counterfactual"] == "Flow sentence."
    assert nozzle["passed"] is None and nozzle["layers"] == []  # not gated yet


def test_card_model_without_explanation(db):
    with Store.open_readonly(db) as store:
        card = ui_data.card_model(store, "d1")
    assert card["causes"] == [] and card["flags"] == [] and card["alpha"] is None
    assert card["proposals"] == [] and card["remaining_s"] is None


def decisions(path):
    with Store(path) as store:
        return store.new_decisions()


def test_insert_decision_writes_row(card_db):
    with Store.open_readonly(card_db) as store:
        card = ui_data.card_model(store, "d1")
        row_id = ui_data.insert_decision(store, card, "modify", "asha", proposal_id="d1-flow_low", modified_delta=5.0)
        ui_data.insert_decision(store, card, "reject", "asha")

    first, second = decisions(card_db)
    assert first["id"] == row_id
    assert (first["defect_id"], first["proposal_id"], first["choice"], first["modified_delta"], first["operator"]) == (
        "d1", "d1-flow_low", "modify", 5.0, "asha")
    assert first["latency_s"] == pytest.approx(30.0)
    assert first["wall_iso"] and first["consumed"] == 0
    assert (second["choice"], second["proposal_id"], second["modified_delta"]) == ("reject", None, None)


def test_stop_needs_confirm(card_db):
    with Store.open_readonly(card_db) as store:
        card = ui_data.card_model(store, "d1")
        assert ui_data.insert_decision(store, card, "stop", "asha") is None
        assert decisions(card_db) == []
        assert ui_data.insert_decision(store, card, "stop", "asha", confirm=True) is not None
    assert [d["choice"] for d in decisions(card_db)] == ["stop"]


def test_card_buttons_only_insert_decisions(card_db, monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setattr("sys.argv", ["ui.py", "--run", "run-001", "--run-dir", str(card_db.parent.parent)])
    at = AppTest.from_file("../xqi/ui.py").run(timeout=30)
    assert not at.exception
    text = " ".join(m.value for m in at.markdown)
    assert "two causes in the set" in text and "Flow sentence." in text and "telemetry_stale" in text

    at.sidebar.text_input[0].set_value("asha").run(timeout=30)
    at.button(key="apply-d1-flow_low").click().run(timeout=30)
    at.button(key="stop-d1").click().run(timeout=30)  # confirm box unticked: no row
    assert not at.exception
    assert [(d["choice"], d["proposal_id"], d["operator"]) for d in decisions(card_db)] == [
        ("apply", "d1-flow_low", "asha")]


def test_apply_on_loop_card_dispatches(tmp_path):
    """Done-when, CPU side: Apply on a card the replay loop built leads to a dispatched action row."""
    from dataclasses import replace
    from pathlib import Path

    from xqi.camera import open_source
    from xqi.config import load
    from xqi.explain.counterfactual import make_proposal
    from xqi.orchestrator import Orchestrator
    from xqi.printer import FakePrinter

    cfg = replace(load(Path(__file__).resolve().parents[1] / "config" / "default.yaml"), mode="advisory")
    cfg = replace(cfg, proactive=replace(cfg.proactive, enabled=False))  # FlowExplainer has no estimate()
    folder = tmp_path / "frames_in"
    folder.mkdir()
    for i in range(6):
        assert cv2.imwrite(str(folder / f"{i:03d}.png"), np.zeros((8, 8, 3), np.uint8))
    store = Store(tmp_path / "run" / "events.sqlite")

    class FlowExplainer:
        def explain(self, cd, frame, history):
            est = CauseEstimate({"flow_low": 0.9}, "flow_low", 0.9)
            return est, CauseSet(("flow_low",), 0.1, 0.5), (), [
                make_proposal("flow_low", 0.9, cd.severity, history[-1], cfg, cd.defect_id)]

    def detector(frame):
        if frame.frame_id == 5:  # the operator clicks Apply on the card
            with Store.open_readonly(store.path) as ui:
                (event,) = ui.pending_events()
                card = ui_data.card_model(ui, event["defect_id"])
                ui_data.insert_decision(ui, card, "apply", "asha", proposal_id=card["proposals"][0]["proposal_id"])
        return [Detection(frame.frame_id, "under_extrusion", 0.9, (0.0, 0.0, 4.0, 4.0), 0.25)]

    printer = FakePrinter()
    Orchestrator(cfg, printer, open_source(f"replay:{folder}", 0, 0), detector, FlowExplainer(), store).run()

    with Store.open_readonly(store.path) as db:
        (action,) = db.query("SELECT source, proposal_id, gcode_json, ok FROM actions")
        (proposal,) = db.query("SELECT proposal_id FROM proposals")
    assert action == {"source": "operator", "proposal_id": proposal["proposal_id"],
                      "gcode_json": '["M221 S108"]', "ok": 1}
    assert [line for _, line in printer.sent] == ["M221 S108"]


def test_card_carries_manual_advice(db):
    from xqi.types import MANUAL_ADVICE

    with Store(db) as store:
        store.write_run({"run_id": "run-001", "mode": "advisory", "cfg": {"conformal": {"alpha": 0.1}}})
        store.write_explanation(
            "d1", CauseEstimate({"z_offset_low": 0.6, "flow_low": 0.4}, "z_offset_low", 0.6),
            CauseSet(("z_offset_low", "flow_low"), 0.1, 0.7), 0.7, [], 3.05,
        )
        store.write_verdict(EventVerdict("d1", "ESCALATE", "manual:z_offset_low", ()), t_gate=3.1, pending=True)
    with Store.open_readonly(db) as store:
        card = ui_data.card_model(store, "d1")

    assert card["advice"] == [("z_offset_low", MANUAL_ADVICE["z_offset_low"])]
