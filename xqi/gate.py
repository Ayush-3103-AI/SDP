import math

from xqi.config import Config
from xqi.types import (
    MANUAL_ADVICE,
    CauseEstimate,
    CauseSet,
    ConfirmedDefect,
    EventVerdict,
    GateDecision,
    LayerResult,
    PrinterState,
    Proposal,
)

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

    lo, hi = env.L3.window[v]
    if not l3_pass(x, x2, (lo, hi)):
        layers.append(LayerResult("L3", False, f"L3: {x2} {unit} moves away from [{lo:g}, {hi:g}]"))
        return _reject(p, x, clipped, layers)
    where = "within" if lo <= x2 <= hi else "toward"
    layers.append(LayerResult("L3", True, f"L3: {x2} {unit} {where} [{lo:g}, {hi:g}]"))

    return GateDecision(
        p.proposal_id, True, clipped, x2 - x, float(x2), (f"{GCODE[v]} S{x2}",), tuple(layers)
    )


def _dist(y: float, lo: float, hi: float) -> float:
    return max(lo - y, 0.0, y - hi)


def l3_pass(x: float, x2: float, window: tuple[float, float]) -> bool:
    """07 §3 L3: inside the window, or strictly closer to it than the current setpoint."""
    lo, hi = window
    return lo <= x2 <= hi or _dist(x2, lo, hi) < _dist(x, lo, hi)


_SETPOINTS = ("nozzle_temp", "bed_temp", "flow", "speed")


def _l4_fail(cset: CauseSet, est: CauseEstimate | None, flags, cfg: Config) -> str:
    """07 §3 L4; '' on pass, else why it failed."""
    if len(cset.members) != 1:
        return f"L4: |C| = {len(cset.members)}"
    if est is None:
        return "L4: no cause estimate"
    tau = cfg.envelope.L4.tau
    if not est.p_top >= tau:
        return f"L4: p_top {est.p_top:.2f} < {tau:g}"
    if flags:
        return f"L4: sensor flags {', '.join(flags)}"
    return ""


def event_verdict(
    mode: str,
    cd: ConfirmedDefect,
    cset: CauseSet | None,
    est: CauseEstimate | None,
    flags,
    decisions: list[GateDecision],
    state: PrinterState | None,
    cfg: Config,
) -> EventVerdict:
    """07 §4 truth table, first matching row wins. Pure."""
    passed = tuple(d.proposal_id for d in decisions if d.passed)

    def out(verdict: str, reason: str, ids: tuple[str, ...] = ()) -> EventVerdict:
        return EventVerdict(cd.defect_id, verdict, reason, ids)

    action = getattr(cfg.critical, cd.cls, None)
    if action is not None:  # 1
        return out("CRITICAL", action)
    if mode == "baseline":  # 2
        return out("APPLY_RAW", "deck_recipe")
    if mode == "gated-recipe":  # 3
        return out("APPLY", "recipe", passed) if passed else out("NOOP", "recipe_blocked")
    if state is None or any(math.isnan(state.setpoint(v)) for v in _SETPOINTS):  # 4
        return out("ESCALATE", "state_unavailable")
    if cset is None or not cset.members:  # 5
        return out("ESCALATE", "no_confident_cause")
    if cset.members == ("none",):  # 6
        return out("NOOP", "no_actionable_cause")
    manual = [c for c in cset.members if c in MANUAL_ADVICE]
    if manual:  # 7
        return out("ESCALATE", f"manual:{manual[0]}")
    if not passed:  # 8
        return out("ESCALATE", "outside_envelope")
    l4 = _l4_fail(cset, est, flags, cfg)
    if mode == "auto" and not l4 and len(passed) == 1:  # 9
        return out("APPLY", "L4: pass", passed)
    if mode != "auto":  # 10
        return out("PROPOSE", mode, passed)
    return out("PROPOSE", l4 or f"{len(passed)} surviving proposals", passed)
