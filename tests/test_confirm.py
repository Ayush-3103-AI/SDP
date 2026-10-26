import uuid
from types import SimpleNamespace

import numpy as np
import pytest

from xqi.detect import ConfirmationTracker
from xqi.explain.counterfactual import severity
from xqi.types import DEFECTS, Detection, Frame

SEV = SimpleNamespace(a_ref=0.02, h_ref=15, window=30)
HITS = {k: 3 for k in DEFECTS}


def frame(i):
    return Frame(i, 100.0 + i, "2026-01-01T00:00:00", np.empty((0, 0, 3)))


def det(i, cls="stringing", conf=0.5, area=0.01):
    return Detection(i, cls, conf, (0.0, 0.0, 10.0, 10.0), area)


def run(tracker, pattern, cls="stringing"):
    """Feed one frame per char ('T' = detected); return [(frame_id, event)]."""
    out = []
    for i, c in enumerate(pattern, start=1):
        dets = [det(i, cls)] if c == "T" else []
        out += [(i, cd) for cd in tracker.update(frame(i), dets)]
    return out


def test_three_hits_fire_once_at_frame_three():
    events = run(ConfirmationTracker(HITS, 50, SEV), "TTT")
    assert len(events) == 1
    i, cd = events[0]
    assert i == 3 and cd.frame_id == 3 and cd.cls == "stringing"
    assert cd.t0 == frame(1).ts
    assert uuid.UUID(cd.defect_id).version == 4
    assert cd.recent_hits == 3
    assert cd.severity == pytest.approx(severity(0.01, 3, SimpleNamespace(severity=SEV)))
    assert cd.critical is False


def test_miss_resets_streak():
    assert run(ConfirmationTracker(HITS, 50, SEV), "TFTT") == []


def test_no_refire_until_rearmed():
    tracker = ConfirmationTracker(HITS, 5, SEV)
    # still present, then a short gap (< rearm) → no re-fire
    assert [i for i, _ in run(tracker, "TTTTTFFFFTTT")] == [3]
    tracker = ConfirmationTracker(HITS, 5, SEV)
    # 5 misses re-arm, then 3 hits fire again
    assert [i for i, _ in run(tracker, "TTTFFFFFTTT")] == [3, 11]


def test_two_classes_in_parallel():
    hits = dict(HITS, clog=2)
    tracker = ConfirmationTracker(hits, 50, SEV)
    got = []
    for i in range(1, 4):
        dets = [det(i, "stringing"), det(i, "clog")]
        got += [(i, cd.cls, cd.critical) for cd in tracker.update(frame(i), dets)]
    assert got == [(2, "clog", True), (3, "stringing", False)]


def test_max_conf_box_used():
    tracker = ConfirmationTracker(HITS, 50, SEV)
    events = []
    for i in range(1, 4):
        dets = [det(i, conf=0.3, area=0.001), det(i, conf=0.9, area=0.02),
                det(i, conf=0.5, area=0.005)]
        events += tracker.update(frame(i), dets)
    assert len(events) == 1
    assert events[0].conf == pytest.approx(0.9)
    assert events[0].area_frac == pytest.approx(0.02)
