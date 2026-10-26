"""Telemetry-only sensor checks (07-math §5). Pure: no I/O, no clock."""

from collections.abc import Sequence
from itertools import pairwise

from xqi.types import PrinterState

HEATERS = (
    ("nozzle", "nozzle_actual_c", "nozzle_target_c"),
    ("bed", "bed_actual_c", "bed_target_c"),
)


def _deviating_since(history, actual, target, dev_c):
    """ts at which the run of |actual - target| > dev_c ending at the latest sample began."""
    since = None
    for s in reversed(history):
        if abs(getattr(s, actual) - getattr(s, target)) <= dev_c:
            break
        since = s.ts
    return since


def _last_target_change(history, v):
    """Latest ts the target for v changed: tracked by us, or seen in the history."""
    last = history[-1].last_change_ts.get(v)
    for prev, cur in pairwise(history):
        if cur.setpoint(v) != prev.setpoint(v) and (last is None or cur.ts > last):
            last = cur.ts
    return last


def check(history: Sequence[PrinterState], now: float, cfg) -> tuple[str, ...]:
    if not history:
        return ("state_unavailable",)
    history = sorted(history, key=lambda s: s.ts)
    sensors = cfg.sensors
    flags = []

    for name, actual, target in HEATERS:
        since = _deviating_since(history, actual, target, sensors.temp_dev_c)
        if since is not None and now - since > sensors.temp_dev_s:
            flags.append(f"heater_deviation:{name}")

    for v, settle_s in sensors.settle_s.items():
        changed = _last_target_change(history, v)
        if changed is not None and now - changed < settle_s:
            flags.append(f"settling:{v}")

    if history[-1].state != "Printing":
        flags.append("printer_not_printing")

    return tuple(flags)
