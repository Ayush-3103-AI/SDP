from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from xqi.types import DEFECTS, Outcome

MIN_FRAMES = 10


@dataclass(slots=True)
class _Watch:
    action_id: str
    defect_id: str
    cls: str
    t_a: float
    r_before: float
    n_before: int


class Verifier:
    """Classifies the outcome of each applied action from the defect rate before and after it (07 §6, 08 P6)."""

    def __init__(self, window_s: float, settle_s: float) -> None:
        self.window_s = window_s
        self.settle_s = settle_s
        self._buf: dict[str, deque[tuple[float, bool]]] = {k: deque() for k in DEFECTS}
        self._pending: list[_Watch] = []

    def watch(self, action_id: str, defect_id: str, cls: str, t_a: float) -> None:
        r, n = self._rate(cls, t_a - self.window_s, t_a)
        self._pending.append(_Watch(action_id, defect_id, cls, t_a, r, n))

    def tick(self, frame_ts: float, present: set[str]) -> list[Outcome]:
        horizon = frame_ts - (self.settle_s + 2 * self.window_s)
        for k, buf in self._buf.items():
            buf.append((frame_ts, k in present))
            while buf[0][0] < horizon:
                buf.popleft()
        done = [w for w in self._pending if frame_ts >= w.t_a + self.settle_s + self.window_s]
        self._pending = [w for w in self._pending if w not in done]
        return [self._classify(w, ended=False) for w in done]

    def close(self) -> list[Outcome]:
        out = [self._classify(w, ended=True) for w in self._pending]
        self._pending = []
        return out

    def _rate(self, cls: str, t0: float, t1: float) -> tuple[float, int]:
        hits = [p for ts, p in self._buf[cls] if t0 <= ts <= t1]
        return (sum(hits) / len(hits) if hits else 0.0), len(hits)

    def _classify(self, w: _Watch, ended: bool) -> Outcome:
        start = w.t_a + self.settle_s
        r_after, n_after = self._rate(w.cls, start, start + self.window_s)
        rb = w.r_before
        if ended or w.n_before < MIN_FRAMES or n_after < MIN_FRAMES:
            verdict = "unknown"
        elif r_after <= 0.5 * rb and r_after <= 0.10:
            verdict = "resolved"
        elif r_after >= 1.5 * rb and r_after >= 0.20:
            verdict = "worsened"
        else:
            verdict = "persisted"
        return Outcome(w.action_id, w.defect_id, w.cls, verdict, rb, r_after, self.window_s)
