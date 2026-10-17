"""Deterministic telemetry sensor checks (07-math.md §5, FR-010).

Pure function over a ``PrinterState`` history. These flags are a *safety*
signal that blocks L4/APPLY; telemetry must never become an input feature of the
learned cause model (ADR-0002).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence

from xqi.config import Config
from xqi.types import PrinterState


def _deviation_streak(
    history: Sequence[PrinterState],
    now: float,
    actual: Callable[[PrinterState], float],
    target: Callable[[PrinterState], float],
    delta_t: float,
    t_delta: float,
) -> bool:
    """True if |actual - target| > delta_t held continuously for > t_delta."""

    start: float | None = None

    for state in history:
        if abs(actual(state) - target(state)) > delta_t:
            if start is None:
                start = state.ts
        else:
            start = None

    return start is not None and (now - start) > t_delta


def check(
    history: Sequence[PrinterState],
    now: float,
    cfg: Config,
) -> tuple[str, ...]:
    """Return the sensor flags for the current telemetry window.

    Flags per 07-math.md §5:

    * ``heater_deviation:nozzle`` / ``heater_deviation:bed`` — a heater has
      been off-target by more than ``cfg.sensors.temp_dev_c`` for longer than
      ``cfg.sensors.temp_dev_s`` continuously;
    * ``settling:<var>`` — the target for ``var`` changed less than its settle
      time ago;
    * ``printer_not_printing`` — the printer is not in the ``Printing`` state;
    * ``state_unavailable`` — no telemetry at all.
    """

    if not history:
        return ("state_unavailable",)

    latest = history[-1]
    flags: list[str] = []

    delta_t = cfg.sensors.temp_dev_c
    t_delta = cfg.sensors.temp_dev_s

    if _deviation_streak(
        history,
        now,
        lambda s: s.nozzle_actual_c,
        lambda s: s.nozzle_target_c,
        delta_t,
        t_delta,
    ):
        flags.append("heater_deviation:nozzle")

    if _deviation_streak(
        history,
        now,
        lambda s: s.bed_actual_c,
        lambda s: s.bed_target_c,
        delta_t,
        t_delta,
    ):
        flags.append("heater_deviation:bed")

    for var, settle_s in cfg.sensors.settle_s.items():
        last = latest.last_change_ts.get(var)

        if last is not None and math.isfinite(last) and (now - last) < settle_s:
            flags.append(f"settling:{var}")

    if latest.state != "Printing":
        flags.append("printer_not_printing")

    return tuple(flags)


__all__ = ["check"]
