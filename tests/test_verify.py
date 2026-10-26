from __future__ import annotations

import math

from xqi.verify import Verifier

FPS = 10
W, S = 120.0, 30.0
A_FRAME = 2000  # action at t_a = 200 s


def _present(i: int, rate: float) -> bool:
    # Spreads exactly `rate` of the frames evenly over any long-enough window.
    return math.floor((i + 1) * rate) > math.floor(i * rate)


def _run(r_before: float, r_after: float, end_frame: int | None = None):
    """Frames at 10 fps from t=0; `stringing` at r_before until t_a, r_after after."""
    v = Verifier(window_s=W, settle_s=S)
    t_a = A_FRAME / FPS
    if end_frame is None:
        end_frame = A_FRAME + int((S + W) * FPS) + 50
    outcomes = []
    for i in range(end_frame + 1):
        if i == A_FRAME:
            v.watch("a1", "d1", "stringing", t_a)
        rate = r_before if i <= A_FRAME else r_after
        outcomes += v.tick(i / FPS, {"stringing"} if _present(i, rate) else set())
    return outcomes, v.close()


def test_resolved():
    (o,), rest = _run(0.5, 0.0)
    assert rest == []
    assert o.verdict == "resolved"
    assert (o.action_id, o.defect_id, o.cls, o.window_s) == ("a1", "d1", "stringing", W)
    assert abs(o.r_before - 0.5) < 0.01 and o.r_after == 0.0


def test_worsened():
    (o,), _ = _run(0.2, 0.4)
    assert o.verdict == "worsened"
    assert abs(o.r_before - 0.2) < 0.01 and abs(o.r_after - 0.4) < 0.01


def test_persisted():
    (o,), _ = _run(0.3, 0.25)
    assert o.verdict == "persisted"
    assert abs(o.r_before - 0.3) < 0.01 and abs(o.r_after - 0.25) < 0.01


def test_run_ends_early_is_unknown():
    outcomes, (o,) = _run(0.5, 0.0, end_frame=A_FRAME + int((S + 10) * FPS))
    assert outcomes == []
    assert o.verdict == "unknown"


def test_too_few_before_frames_is_unknown():
    v = Verifier(window_s=W, settle_s=S)
    v.tick(0.0, {"stringing"})
    v.watch("a1", "d1", "stringing", 0.0)
    out = []
    for i in range(1, int((S + W) * FPS) + 1):
        out += v.tick(i / FPS, set())
    (o,) = out
    assert o.verdict == "unknown"
    assert v.close() == []
