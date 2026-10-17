import pytest

from xqi.types import DEFECTS
from xqi.verify import MIN_WINDOW_FRAMES, Verifier, classify_rate

DT = 0.1
T_A = 10.0

# Window boundaries as frame indices (ts = idx * DT).
BEFORE_LO, BEFORE_HI = 80, 100  # [t_a - 2.0, t_a]
AFTER_LO, AFTER_HI = 110, 130  # [t_a + 1.0, t_a + 3.0]


def idx(ts: float) -> int:
    return round(ts / DT)


def frames(start: float, end: float, dt: float = DT) -> list[float]:
    steps = round((end - start) / dt)
    return [round(start + i * dt, 6) for i in range(steps + 1)]


def run(before, after, t_a: float = T_A, cls: str = "stringing"):
    verifier = Verifier(window_s=2.0, settle_s=1.0)

    for ts in frames(0.0, t_a):
        verifier.tick(ts, {cls} if before(ts) else set())

    verifier.watch("a1", "d1", cls, t_a)

    outcomes = []
    for ts in frames(t_a + DT, t_a + 1.0 + 2.0):
        outcomes += verifier.tick(ts, {cls} if after(ts) else set())

    return outcomes, verifier


# --------------------------------------------------------------------------- #
# classification (07-math.md §6)
# --------------------------------------------------------------------------- #


def test_before_half_after_zero_is_resolved():
    outcomes, _ = run(lambda ts: idx(ts) % 2 == 0, lambda ts: False)

    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.verdict == "resolved"
    assert outcome.cls == "stringing"
    assert outcome.action_id == "a1"
    assert outcome.defect_id == "d1"
    assert outcome.window_s == 2.0
    assert outcome.r_after == 0.0
    assert 0.40 <= outcome.r_before <= 0.60


def test_before_twenty_after_forty_is_worsened():
    outcomes, _ = run(lambda ts: idx(ts) % 5 == 0, lambda ts: idx(ts) % 2 == 0)

    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.verdict == "worsened"
    assert outcome.r_after >= 1.5 * outcome.r_before
    assert outcome.r_after >= 0.20


def test_before_thirty_after_twentyfive_is_persisted():
    outcomes, _ = run(lambda ts: idx(ts) % 3 == 0, lambda ts: idx(ts) % 4 == 0)

    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.verdict == "persisted"
    assert outcome.r_after < 1.5 * outcome.r_before
    assert outcome.r_after > 0.5 * outcome.r_before


def test_run_ends_early_is_unknown():
    verifier = Verifier(window_s=2.0, settle_s=1.0)

    for ts in frames(0.0, T_A):
        verifier.tick(ts, {"stringing"})

    verifier.watch("a1", "d1", "stringing", T_A)

    for ts in frames(T_A + DT, T_A + 1.0):  # only ~10 frames, window unfinished
        verifier.tick(ts, {"stringing"})

    outcomes = verifier.close()

    assert len(outcomes) == 1
    assert outcomes[0].verdict == "unknown"


def test_too_few_before_frames_is_unknown():
    verifier = Verifier(window_s=2.0, settle_s=1.0)

    for ts in frames(T_A - 0.5, T_A):  # only ~5 frames before the action
        verifier.tick(ts, set())

    verifier.watch("a1", "d1", "stringing", T_A)

    outcomes = []
    for ts in frames(T_A + DT, T_A + 3.0):
        outcomes += verifier.tick(ts, set())

    assert outcomes[0].verdict == "unknown"


def test_too_few_after_frames_is_unknown():
    verifier = Verifier(window_s=2.0, settle_s=1.0)

    # Sparse 1 s sampling: the after window holds only ~3 frames.
    for ts in range(11):
        verifier.tick(float(ts), {"stringing"})

    verifier.watch("a1", "d1", "stringing", T_A)

    outcomes = []
    for ts in range(11, 14):
        outcomes += verifier.tick(float(ts), {"stringing"})

    assert outcomes[0].verdict == "unknown"
    assert MIN_WINDOW_FRAMES == 10


# --------------------------------------------------------------------------- #
# timing and bookkeeping
# --------------------------------------------------------------------------- #


def test_no_outcome_before_the_window_completes():
    verifier = Verifier(window_s=2.0, settle_s=1.0)

    for ts in frames(0.0, T_A):
        verifier.tick(ts, {"stringing"})

    verifier.watch("a1", "d1", "stringing", T_A)

    for ts in frames(T_A + DT, T_A + 2.9):
        assert verifier.tick(ts, {"stringing"}) == []


def test_tick_without_watchers_returns_empty():
    verifier = Verifier(window_s=2.0, settle_s=1.0)

    assert verifier.tick(0.0, {"stringing"}) == []


def test_close_is_idempotent():
    verifier = Verifier(window_s=2.0, settle_s=1.0)
    verifier.watch("a1", "d1", "stringing", T_A)

    assert len(verifier.close()) == 1
    assert verifier.close() == []


def test_watches_are_independent_per_class():
    verifier = Verifier(window_s=2.0, settle_s=1.0)

    for ts in frames(0.0, T_A):
        idx_ts = idx(ts)
        present = set()
        if idx_ts % 2 == 0:
            present.add("stringing")
        if idx_ts % 5 == 0:
            present.add("warping")
        verifier.tick(ts, present)

    verifier.watch("a1", "d1", "stringing", T_A)
    verifier.watch("a2", "d2", "warping", T_A)

    outcomes = []
    for ts in frames(T_A + DT, T_A + 3.0):
        idx_ts = idx(ts)
        present = set()
        if idx_ts % 4 == 0:
            present.add("warping")
        outcomes += verifier.tick(ts, present)

    by_action = {outcome.action_id: outcome for outcome in outcomes}
    assert by_action["a1"].verdict == "resolved"
    assert by_action["a2"].verdict == "persisted"


def test_verifier_tracks_all_defect_classes():
    verifier = Verifier(window_s=1.0, settle_s=0.5)

    for cls in DEFECTS:
        verifier.tick(0.0, {cls})

    assert set(verifier._buffer) == set(DEFECTS)


@pytest.mark.parametrize(
    ("r_before", "r_after", "expected"),
    [
        (0.40, 0.10, "resolved"),  # r_after exactly 0.10 and <= 0.5 r_before
        (0.40, 0.15, "persisted"),  # above the 0.10 resolved cap
        (0.10, 0.20, "worsened"),  # exactly 1.5x and >= 0.20
        (0.20, 0.20, "persisted"),  # 0.20 < 1.5 * 0.20
        (0.00, 0.00, "resolved"),  # r_after == 0
        (0.20, 0.19, "persisted"),
    ],
)
def test_classification_thresholds(r_before, r_after, expected):
    assert classify_rate(r_before, r_after, 20, 20) == expected


def test_too_few_frames_forces_unknown():
    assert classify_rate(0.0, 0.0, 9, 20) == "unknown"
    assert classify_rate(0.0, 0.0, 20, 9) == "unknown"
    assert classify_rate(0.0, 0.0, 20, 20, ended=True) == "unknown"
