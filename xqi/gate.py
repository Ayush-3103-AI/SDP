import math

from xqi.config import Config
from xqi.types import GateDecision, LayerResult, PrinterState, Proposal

GCODE = {"nozzle_temp": "M104", "bed_temp": "M140", "flow": "M221", "speed": "M220"}
UNIT = {"nozzle_temp": "°C", "bed_temp": "°C", "flow": "%", "speed": "%"}


def round_half_up(x: float) -> int:
    """G-code rounding; never Python's banker's round() (07 §2, P4)."""
    return math.floor(x + 0.5)


def _reject(p: Proposal, x: float, clipped: bool, layers: list[LayerResult]) -> GateDecision:
    return GateDecision(p.proposal_id, False, clipped, 0.0, x, (), tuple(layers))


def gate(p: Proposal, state: PrinterState | None, now: float, cfg: Config) -> GateDecision:
    """07 §3 / P4, layers L2 → L1 → L3. Pure: no I/O, no globals beyond constants."""
    v = p.var
    x = state.setpoint(v) if state is not None else math.nan
    last = state.last_change_ts.get(v, -math.inf) if state is not None else math.nan
    if math.isnan(x) or math.isnan(last) or math.isnan(p.delta):
        return _reject(p, p.from_value, False, [LayerResult("L1", False, "state_unavailable")])

    env = cfg.envelope
    unit = UNIT[v]
    layers = []

    cool = env.L2.cooldown_s[v]
    if now - last < cool:
        layers.append(LayerResult("L2", False, f"L2: cooldown {now - last:.0f}s < {cool:g}s"))
        return _reject(p, x, False, layers)
    step = env.L2.step[v]
    d = math.copysign(min(abs(p.delta), step), p.delta)
    clipped = d != p.delta
    if clipped:
        layers.append(LayerResult("L2", True, f"L2: clipped {p.delta:+g} → {d:+g} {unit}"))
    else:
        layers.append(LayerResult("L2", True, f"L2: {d:+g} {unit} within ±{step:g}"))

    # Round before L1 so the check sees exactly what the G-code will send.
    x2 = round_half_up(x + d)
    lo, hi = getattr(env.L1, v)
    if not lo <= x2 <= hi:
        layers.append(LayerResult("L1", False, f"L1: {x2} {unit} outside [{lo:g}, {hi:g}]"))
        return _reject(p, x, clipped, layers)
    layers.append(LayerResult("L1", True, f"L1: {x2} {unit} within [{lo:g}, {hi:g}]"))

    # ponytail: L3 window check lands in its own ticket; passes for now.
    layers.append(LayerResult("L3", True, "L3: not checked (stub)"))

    return GateDecision(
        p.proposal_id, True, clipped, x2 - x, float(x2), (f"{GCODE[v]} S{x2}",), tuple(layers)
    )
