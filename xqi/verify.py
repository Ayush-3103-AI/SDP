"""Outcome verifier (07-math.md §6, 08-pseudocode.md P6, FR-020).

The verifier watches applied actions and classifies what happened to the defect
after the correction: ``resolved``, ``persisted``, ``worsened`` or ``unknown``.

It keeps a per-class ring buffer of ``(ts, present)`` samples fed by ``tick``;
classification only needs the last ``settle_s + 2 * window_s`` seconds. The
rates are coverage fractions over fixed windows, so an incomplete window (fewer
than 10 frames, or a print that ended early) is reported as ``unknown`` rather
than guessed.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass

from xqi.types import DEFECTS, Outcome

# A window needs at least this many frames before a rate is trusted.
MIN_WINDOW_FRAMES = 10


@dataclass(slots=True)
class _Watch:
    action_id: str
    defect_id: str
    cls: str
    t_a: float
    r_before: float
    n_before: int


def _rate(present: int, total: int) -> float:
    return present / total if total else 0.0


def classify_rate(
    r_before: float,
    r_after: float,
    n_before: int,
    n_after: int,
    *,
    ended: bool = False,
) -> str:
    """Classify a rate pair per 07-math.md §6.

    Extracted so the thresholds can be tested directly. An incomplete window
    (fewer than :data:`MIN_WINDOW_FRAMES` frames) or an early end is always
    ``unknown``.
    """

    if ended or n_before < MIN_WINDOW_FRAMES or n_after < MIN_WINDOW_FRAMES:
        return "unknown"

    if r_after <= 0.5 * r_before and r_after <= 0.10:
        return "resolved"

    if r_after >= 1.5 * r_before and r_after >= 0.20:
        return "worsened"

    return "persisted"


class Verifier:
    """Track applied actions and classify their outcome per 07-math.md §6."""

    def __init__(self, window_s: float, settle_s: float) -> None:
        self.window_s = float(window_s)
        self.settle_s = float(settle_s)

        self._buffer: dict[str, deque[tuple[float, bool]]] = {
            cls: deque() for cls in DEFECTS
        }
        self._pending: list[_Watch] = []

    # -- buffer ------------------------------------------------------------ #

    def _samples(self, cls: str) -> deque[tuple[float, bool]]:
        buffer = self._buffer.get(cls)

        if buffer is None:
            buffer = deque()
            self._buffer[cls] = buffer

        return buffer

    def _prune(self, newest: float) -> None:
        horizon = newest - (self.settle_s + 2.0 * self.window_s)

        for buffer in self._buffer.values():
            while buffer and buffer[0][0] < horizon:
                buffer.popleft()

    def _count(self, cls: str, lo: float, hi: float) -> tuple[int, int]:
        present = 0
        total = 0

        for ts, is_present in self._buffer.get(cls, ()):
            if lo <= ts <= hi:
                total += 1
                present += int(is_present)

        return present, total

    # -- public API -------------------------------------------------------- #

    def watch(
        self,
        action_id: str,
        defect_id: str,
        cls: str,
        t_a: float,
    ) -> None:
        """Start watching class ``cls`` after an action dispatched at ``t_a``."""

        present, total = self._count(cls, t_a - self.window_s, t_a)

        self._pending.append(
            _Watch(
                action_id=action_id,
                defect_id=defect_id,
                cls=cls,
                t_a=float(t_a),
                r_before=_rate(present, total),
                n_before=total,
            )
        )

        self._samples(cls)
        self._prune(float(t_a))

    def tick(
        self,
        frame_ts: float,
        present: Iterable[str],
    ) -> list[Outcome]:
        """Record one frame and return any outcomes that are now ready."""

        names = set(present)

        for cls, buffer in self._buffer.items():
            buffer.append((frame_ts, cls in names))

        for cls in names - self._buffer.keys():
            self._buffer[cls] = deque([(frame_ts, True)])

        self._prune(frame_ts)

        ready: list[Outcome] = []
        pending: list[_Watch] = []

        for watch in self._pending:
            if frame_ts >= watch.t_a + self.settle_s + self.window_s:
                ready.append(self._classify(watch))
            else:
                pending.append(watch)

        self._pending = pending

        return ready

    def close(self) -> list[Outcome]:
        """Flush pending watches as ``unknown`` (the print ended early)."""

        outcomes = [self._classify(watch, ended=True) for watch in self._pending]
        self._pending.clear()

        return outcomes

    # -- classification ---------------------------------------------------- #

    def _classify(self, watch: _Watch, *, ended: bool = False) -> Outcome:
        present, total = self._count(
            watch.cls,
            watch.t_a + self.settle_s,
            watch.t_a + self.settle_s + self.window_s,
        )
        r_after = _rate(present, total)

        verdict = classify_rate(
            watch.r_before,
            r_after,
            watch.n_before,
            total,
            ended=ended,
        )

        return Outcome(
            action_id=watch.action_id,
            defect_id=watch.defect_id,
            cls=watch.cls,
            verdict=verdict,
            r_before=watch.r_before,
            r_after=r_after,
            window_s=self.window_s,
        )


__all__ = ["MIN_WINDOW_FRAMES", "Verifier", "classify_rate"]
