import os

import cv2
import numpy as np
import pytest

from xqi import ui_data
from xqi.store import Store
from xqi.types import ConfirmedDefect, Detection, EventVerdict, PrinterState


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
