"""T-0031 — the multi-frame confirmation tracker with severity."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from xqi.config import load
from xqi.detect import ConfirmationTracker
from xqi.explain.counterfactual import severity
from xqi.types import DEFECTS, Detection, Frame

ROOT = Path(__file__).resolve().parents[1]
CFG = load(ROOT / "config" / "default.yaml")


def detection(cls="over_extrusion", conf=0.9, frame_id=0, xyxy=(0.0, 0.0, 10.0, 10.0), area=0.01):
    return Detection(frame_id=frame_id, cls=cls, conf=conf, xyxy=xyxy, area_frac=area)


def frame(ts: float, frame_id: int = 0) -> Frame:
    return Frame(
        frame_id=frame_id,
        ts=ts,
        wall_iso="t",
        image=np.zeros((4, 4, 3), dtype=np.uint8),
    )


def make_tracker(hits: int = 3, rearm: int = 50) -> ConfirmationTracker:
    return ConfirmationTracker({cls: hits for cls in DEFECTS}, rearm, CFG)


def test_three_hits_confirm_on_the_third_frame():
    tracker = make_tracker(3)

    events = []
    for index in range(3):
        events += tracker.update(
            frame(float(index), index),
            [detection(frame_id=index)],
        )

    assert len(events) == 1
    event = events[0]
    assert event.cls == "over_extrusion"
    assert event.frame_id == 2
    assert event.t0 == 0.0
    assert event.t_conf == 2.0
    assert event.recent_hits == 3
    assert event.defect_id


def test_a_miss_breaks_the_streak():
    tracker = make_tracker(3)
    pattern = [True, False, True, True]

    events = []
    for index, present in enumerate(pattern):
        dets = [detection(frame_id=index)] if present else []
        events += tracker.update(frame(float(index), index), dets)

    assert events == []


def test_no_refire_until_rearm():
    tracker = make_tracker(3, rearm=2)
    confirmed_at = []

    for index in range(10):
        present = index not in (5, 6)
        dets = [detection(frame_id=index)] if present else []
        for event in tracker.update(frame(float(index), index), dets):
            confirmed_at.append(index)

    # event at frame 2; frames 3-4 disarmed; frames 5-6 re-arm; event again at 9.
    assert confirmed_at == [2, 9]


def test_two_classes_confirm_in_defect_order():
    tracker = make_tracker(3)

    events = []
    for index in range(3):
        events += tracker.update(
            frame(float(index), index),
            [
                detection(cls="warping", frame_id=index),
                detection(cls="over_extrusion", frame_id=index),
            ],
        )

    assert [event.cls for event in events] == ["over_extrusion", "warping"]


def test_highest_confidence_box_of_a_class_is_used():
    tracker = make_tracker(1)

    events = tracker.update(
        frame(0.0),
        [
            detection(cls="warping", conf=0.4, xyxy=(0, 0, 5, 5)),
            detection(cls="warping", conf=0.9, xyxy=(1, 1, 9, 9)),
            detection(cls="warping", conf=0.6, xyxy=(2, 2, 4, 4)),
        ],
    )

    assert len(events) == 1
    assert events[0].conf == 0.9
    assert events[0].xyxy == (1.0, 1.0, 9.0, 9.0)


def test_severity_matches_the_shared_helper():
    tracker = make_tracker(1)

    events = tracker.update(
        frame(0.0),
        [detection(cls="over_extrusion", area=0.02)],
    )

    assert events[0].severity == severity(0.02, 1, CFG)


def test_critical_flag_follows_config():
    tracker = make_tracker(1)

    events = tracker.update(
        frame(0.0),
        [
            detection(cls="clog"),
            detection(cls="over_extrusion"),
        ],
    )

    critical = {event.cls: event.critical for event in events}
    assert critical == {"clog": True, "over_extrusion": False}


def test_recent_hits_counts_the_window():
    tracker = make_tracker(4)
    pattern = [True, True, True, False, True, True, True, True]

    events = []
    for index, present in enumerate(pattern):
        dets = [detection(frame_id=index)] if present else []
        events += tracker.update(frame(float(index), index), dets)

    assert len(events) == 1
    assert events[0].frame_id == 7
    assert events[0].recent_hits == 7  # frames 0,1,2,4,5,6,7


def test_recent_hits_is_capped_by_the_severity_window():
    window = int(CFG.severity.window)
    tracker = make_tracker(window + 5)

    events = []
    for index in range(window + 5):
        events += tracker.update(frame(float(index), index), [detection(frame_id=index)])

    assert len(events) == 1
    assert events[0].recent_hits == window


def test_tracker_is_deterministic():
    def run() -> list[tuple[str, int, float]]:
        tracker = make_tracker(3)
        out = []
        for index in range(4):
            present = index != 1
            dets = [detection(frame_id=index)] if present else []
            out += [
                (event.cls, event.frame_id, event.t_conf)
                for event in tracker.update(frame(float(index), index), dets)
            ]
        return out

    assert run() == run()


def test_independent_trackers_do_not_share_state():
    first = make_tracker(3)
    second = make_tracker(3)

    for index in range(3):
        first_events = first.update(frame(float(index), index), [detection(frame_id=index)])
    second_events = second.update(frame(0.0), [detection(frame_id=0)])

    assert len(first_events) == 1
    assert second_events == []


def test_out_of_order_timestamps_confirm_by_frame_count():
    tracker = make_tracker(3)

    events = []
    for index, ts in enumerate([5.0, 3.0, 4.0]):
        events += tracker.update(frame(ts, index), [detection(frame_id=index)])

    assert len(events) == 1
    assert events[0].t0 == 5.0
    assert events[0].t_conf == 4.0
