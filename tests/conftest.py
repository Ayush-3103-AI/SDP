"""Shared fakes: a hand-driven clock and a stub detector with a seeded defect schedule."""

import random

import pytest

from xqi.types import Detection


class FastClock:
    """time.monotonic stand-in that moves only on tick(), so simulated hours cost no wall time."""

    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t

    def tick(self, dt):
        self.t += dt
        return self.t


class StubDetector:
    """Seeded random defect schedule: bursts of one class on consecutive frames; silent from stop_ts on."""

    def __init__(self, classes, seed=0, p_burst=0.01, burst=(1, 12), stop_ts=float("inf")):
        self.classes, self.p_burst, self.burst, self.stop_ts = classes, p_burst, burst, stop_ts
        self.rng = random.Random(seed)
        self.cls, self.left = None, 0

    def __call__(self, frame):
        if frame.ts >= self.stop_ts:
            return []
        if self.left == 0 and self.rng.random() < self.p_burst:
            self.cls, self.left = self.rng.choice(self.classes), self.rng.randint(*self.burst)
        if self.left == 0:
            return []
        self.left -= 1
        return [Detection(frame.frame_id, self.cls, 0.9, (0.0, 0.0, 4.0, 4.0), 0.25)]


@pytest.fixture
def fast_clock():
    return FastClock()


@pytest.fixture
def stub_detector():
    return StubDetector
