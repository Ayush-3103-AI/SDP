import sqlite3
from multiprocessing import Process
from pathlib import Path

from xqi.store import SCHEMA_VERSION, Store
from xqi.types import (
    CauseEstimate,
    CauseSet,
    ConfirmedDefect,
    Detection,
    EventVerdict,
    GateDecision,
    LayerResult,
    OperatorDecision,
    Outcome,
    PrinterState,
    Proposal,
)


def make_store(tmp_path: Path) -> Store:
    return Store(tmp_path / "run-001" / "events.sqlite")


def test_schema_and_wal(tmp_path):
    store = make_store(tmp_path)

    row = store.query(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name='runs'"
    )

    assert row
    assert store.query(
        "PRAGMA journal_mode"
    )[0]["journal_mode"].lower() == "wal"

    columns = store.query("PRAGMA table_info(detections)")
    names = {row["name"] for row in columns}

    assert "schema_version" in names
    assert "run_id" in names

    store.close()


def test_run_round_trip(tmp_path):
    store = make_store(tmp_path)

    store.write_run(
        {
            "run_id": "run-001",
            "mode": "advisory",
            "cfg": {"mode": "advisory"},
            "git_sha": "abc123",
            "started_iso": "2026-10-03T10:00:00Z",
            "ended_iso": None,
        }
    )

    rows = store.query("SELECT * FROM runs")

    assert len(rows) == 1
    assert rows[0]["run_id"] == "run-001"
    assert rows[0]["schema_version"] == SCHEMA_VERSION
    assert rows[0]["mode"] == "advisory"

    store.close()


def test_detection_batching(tmp_path):
    store = make_store(tmp_path)

    for frame_id in range(24):
        store.write_detection(
            Detection(
                frame_id=frame_id,
                cls="stringing",
                conf=0.9,
                xyxy=(1.0, 2.0, 3.0, 4.0),
                area_frac=0.1,
            ),
            ts=0.0,
        )

    assert store.query("SELECT COUNT(*) AS n FROM detections")[0]["n"] == 0

    store.write_detection(
        Detection(
            frame_id=24,
            cls="stringing",
            conf=0.9,
            xyxy=(1.0, 2.0, 3.0, 4.0),
            area_frac=0.1,
        ),
        ts=0.0,
    )

    assert store.query("SELECT COUNT(*) AS n FROM detections")[0]["n"] == 25

    store.close()


def test_detection_flush_on_close(tmp_path):
    store = make_store(tmp_path)

    store.write_detection(
        Detection(
            frame_id=1,
            cls="clog",
            conf=0.95,
            xyxy=(1.0, 2.0, 3.0, 4.0),
            area_frac=0.2,
        ),
        ts=0.0,
    )

    store.close()

    with sqlite3.connect(tmp_path / "run-001" / "events.sqlite") as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM detections"
        ).fetchone()[0]

    assert count == 1


def test_detection_keeps_frame_ts(tmp_path):
    store = make_store(tmp_path)

    store.write_detection(
        Detection(
            frame_id=7,
            cls="clog",
            conf=0.95,
            xyxy=(1.0, 2.0, 3.0, 4.0),
            area_frac=0.2,
        ),
        ts=123.5,
    )
    store.flush()

    assert store.query("SELECT ts FROM detections")[0]["ts"] == 123.5

    store.close()


def test_telemetry_round_trip(tmp_path):
    store = make_store(tmp_path)

    state = PrinterState(
        ts=10.0,
        state="printing",
        nozzle_actual_c=205.0,
        nozzle_target_c=210.0,
        bed_actual_c=58.0,
        bed_target_c=60.0,
        flow_pct=100.0,
        speed_pct=95.0,
        progress_pct=50.0,
        last_change_ts={
            "nozzle_temp": 1.0,
            "bed_temp": 2.0,
            "flow": 3.0,
            "speed": 4.0,
        },
    )

    store.write_telemetry(state)

    row = store.query("SELECT * FROM telemetry")[0]

    assert row["state"] == "printing"
    assert row["nozzle_actual_c"] == 205.0
    assert row["flow_pct"] == 100.0
    assert row["schema_version"] == SCHEMA_VERSION
    assert row["run_id"] == "run-001"

    store.close()


def test_defect_round_trip(tmp_path):
    store = make_store(tmp_path)

    defect = ConfirmedDefect(
        defect_id="d1",
        cls="stringing",
        frame_id=10,
        t0=1.0,
        t_conf=2.0,
        conf=0.92,
        xyxy=(1.0, 2.0, 3.0, 4.0),
        area_frac=0.1,
        recent_hits=3,
        severity=0.7,
        critical=False,
    )

    store.write_defect(
        defect,
        crop_path="crops/d1.png",
        heatmap_path="heatmaps/d1.png",
    )

    row = store.query("SELECT * FROM defects")[0]

    assert row["defect_id"] == "d1"
    assert row["cls"] == "stringing"
    assert row["critical"] == 0
    assert row["crop_path"] == "crops/d1.png"
    assert row["heatmap_path"] == "heatmaps/d1.png"

    store.close()


def test_explanation_round_trip(tmp_path):
    store = make_store(tmp_path)

    estimate = CauseEstimate(
        probs={
            "none": 0.1,
            "speed_low": 0.9,
        },
        top="speed_low",
        p_top=0.9,
    )

    cause_set = CauseSet(
        members=("speed_low",),
        alpha=0.1,
        qhat=0.2,
    )

    store.write_explanation(
        "d1",
        estimate,
        cause_set,
        qhat=0.2,
        flags=("heater_deviation:nozzle",),
        t_cause=3.0,
    )

    row = store.query("SELECT * FROM explanations")[0]

    assert row["defect_id"] == "d1"
    assert '"speed_low"' in row["probs_json"]
    assert row["qhat"] == 0.2

    store.close()


def test_proposal_and_gate_round_trip(tmp_path):
    store = make_store(tmp_path)

    proposal = Proposal(
        proposal_id="p1",
        defect_id="d1",
        cause="speed_low",
        var="speed",
        from_value=100.0,
        delta=-5.0,
        to_value=95.0,
        gcode=("M220 S95",),
        counterfactual="Reduce speed to reduce the defect.",
    )

    gate = GateDecision(
        proposal_id="p1",
        passed=True,
        clipped=False,
        final_delta=-5.0,
        final_value=95.0,
        final_gcode=("M220 S95",),
        layers=(
            LayerResult(
                layer="L1",
                passed=True,
                reason="within envelope",
            ),
        ),
    )

    store.write_proposal(proposal, gate)

    row = store.query("SELECT * FROM proposals")[0]

    assert row["proposal_id"] == "p1"
    assert row["passed"] == 1
    assert '"M220 S95"' in row["gcode_json"]

    store.close()


def test_verdict_pending_events(tmp_path):
    store = make_store(tmp_path)

    verdict = EventVerdict(
        defect_id="d1",
        verdict="PROPOSE",
        reason="operator review required",
        proposal_ids=("p1",),
    )

    store.write_verdict(
        verdict,
        t_gate=5.0,
        pending=True,
        deadline_ts=95.0,
    )

    events = store.pending_events()

    assert len(events) == 1
    assert events[0]["defect_id"] == "d1"
    assert events[0]["pending"] == 1

    store.close()


def test_operator_decision_visible_and_consumable(tmp_path):
    db = tmp_path / "run-001" / "events.sqlite"

    loop_store = Store(db)
    ui_store = Store.open_readonly(db)

    decision = OperatorDecision(
        proposal_id="p1",
        defect_id="d1",
        choice="apply",
        modified_delta=None,
        operator="operator-1",
        wall_iso="2026-10-03T10:00:00Z",
        latency_s=2.5,
    )

    decision_id = ui_store.insert_decision(decision)

    decisions = loop_store.new_decisions()

    assert len(decisions) == 1
    assert decisions[0]["id"] == decision_id
    assert decisions[0]["choice"] == "apply"

    loop_store.mark_consumed(decision_id)

    assert loop_store.new_decisions() == []

    ui_store.close()
    loop_store.close()


def test_outcome_round_trip(tmp_path):
    store = make_store(tmp_path)

    outcome = Outcome(
        action_id="a1",
        defect_id="d1",
        cls="stringing",
        verdict="resolved",
        r_before=0.8,
        r_after=0.2,
        window_s=120.0,
    )

    store.write_outcome(outcome)

    row = store.query("SELECT * FROM outcomes")[0]

    assert row["action_id"] == "a1"
    assert row["verdict"] == "resolved"
    assert row["r_before"] == 0.8
    assert row["r_after"] == 0.2

    store.close()


def test_query_is_read_only(tmp_path):
    store = make_store(tmp_path)

    try:
        store.query("DELETE FROM runs")
    except ValueError as exc:
        assert "read-only" in str(exc)
    else:
        raise AssertionError("query() allowed a write operation")

    store.close()


def test_query_rejects_write_hidden_in_cte(tmp_path):
    store = make_store(tmp_path)
    store.write_run({"mode": "advisory"})

    try:
        store.query("WITH x AS (SELECT 1) DELETE FROM runs")
    except ValueError as exc:
        assert "read-only" in str(exc)
    else:
        raise AssertionError("query() allowed a write operation")

    assert store.query("SELECT COUNT(*) AS n FROM runs")[0]["n"] == 1

    store.close()


def test_detections_batch_by_frame_not_by_detection(tmp_path):
    store = make_store(tmp_path)

    def det(frame_id):
        return Detection(
            frame_id=frame_id,
            cls="stringing",
            conf=0.9,
            xyxy=(1.0, 2.0, 3.0, 4.0),
            area_frac=0.1,
        )

    for _ in range(30):
        store.write_detection(det(0), ts=0.0)

    assert store.query("SELECT COUNT(*) AS n FROM detections")[0]["n"] == 0

    for frame_id in range(1, 25):
        store.write_detection(det(frame_id), ts=float(frame_id))

    assert store.query("SELECT COUNT(*) AS n FROM detections")[0]["n"] == 54

    store.close()


def test_concurrent_ui_decision_during_loop_write(tmp_path):
    db = tmp_path / "run-001" / "events.sqlite"

    setup = Store(db)
    setup.close()

    process = Process(
        target=_insert_decision_process,
        args=(str(db),),
    )

    loop_store = Store(db)

    for frame_id in range(25):
        loop_store.write_detection(
            Detection(
                frame_id=frame_id,
                cls="clog",
                conf=0.95,
                xyxy=(1.0, 2.0, 3.0, 4.0),
                area_frac=0.2,
            ),
            ts=0.0,
        )

    process.start()

    loop_store.flush()
    loop_store.close()

    process.join(timeout=5)

    assert process.exitcode == 0

    check = Store(db)

    decisions = check.new_decisions()

    assert len(decisions) == 1
    assert decisions[0]["choice"] == "pause"

    check.close()


def _insert_decision_process(db_path: str) -> None:
    store = Store.open_readonly(db_path)

    decision = OperatorDecision(
        proposal_id="p1",
        defect_id="d1",
        choice="pause",
        modified_delta=None,
        operator="ui",
        wall_iso="2026-10-03T10:00:00Z",
        latency_s=1.0,
    )

    store.insert_decision(decision)
    store.close()