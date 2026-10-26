"""Severity, proposals and counterfactual text (07-math §1, §2)."""

import math

from xqi.types import CAUSE_ACTION, DECK_RECIPES, PrinterState, Proposal

GCODE = {"nozzle_temp": "M104", "bed_temp": "M140", "flow": "M221", "speed": "M220"}
UNIT = {"nozzle_temp": "°C", "bed_temp": "°C", "flow": "%", "speed": "%"}


def round_half_up(x: float) -> int:
    """G-code rounding shared with the gate; never Python's banker's round()."""
    return math.floor(x + 0.5)


def gcode(var: str, value: float) -> tuple[str, ...]:
    return (f"{GCODE[var]} S{round_half_up(value)}",)


def severity(area_frac: float, recent_hits: int, cfg) -> float:
    a = min(1.0, area_frac / cfg.severity.a_ref)
    h = min(1.0, recent_hits / cfg.severity.h_ref)
    return min(1.0, max(0.0, 0.5 * a + 0.5 * h))


def make_proposal(
    cause: str,
    p: float,
    severity: float,
    state: PrinterState,
    cfg,
    defect_id: str = "",
) -> Proposal | None:
    action = CAUSE_ACTION.get(cause)
    if action is None:  # none, misalignment
        return None
    var, d = action
    d_min, d_max = cfg.correction.d_min[var], cfg.correction.d_max[var]
    delta = -d * (d_min + severity * (d_max - d_min))
    x = state.setpoint(var)
    to_value = x + delta
    clear_s = cfg.verify.settle_s + cfg.verify.window_s
    sentence = (
        f"Most likely cause: {cause.replace('_', ' ')} (p={p:.2f}). "
        f"Smallest in-envelope change that undoes it: "
        f"{var} {x:g}→{to_value:g} {UNIT[var]} ({delta:+g}). "
        f"Expected to clear within {clear_s:g} s if the cause is right."
    )
    return Proposal(
        proposal_id=f"{defect_id}-{cause}",
        defect_id=defect_id,
        cause=cause,
        var=var,
        from_value=x,
        delta=delta,
        to_value=to_value,
        gcode=gcode(var, to_value),
        counterfactual=sentence,
    )


def recipe_to_proposals(defect: str, state: PrinterState, defect_id: str) -> list[Proposal]:
    """Deck's absolute recipe as one Proposal per variable (gated-recipe mode)."""
    proposals = []
    for var, target in DECK_RECIPES.get(defect, {}).items():
        x = state.setpoint(var)
        delta = target - x
        proposals.append(
            Proposal(
                proposal_id=f"{defect_id}-recipe-{var}",
                defect_id=defect_id,
                cause="recipe",
                var=var,
                from_value=x,
                delta=delta,
                to_value=float(target),
                gcode=gcode(var, target),
                counterfactual=(
                    f"Deck recipe for {defect}: "
                    f"{var} {x:g}→{target:g} {UNIT[var]} ({delta:+g})."
                ),
            )
        )
    return proposals
