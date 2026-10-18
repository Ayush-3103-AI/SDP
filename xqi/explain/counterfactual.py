"""Severity-scaled correction proposals and counterfactual text.

Implements 07-math.md §1 (severity) and §2 (correction size, G-code and the
counterfactual sentence). A proposal is only ever a *candidate* correction: the
caller must still pass it through the safety gate, and nothing here claims a
proposal is guaranteed to clear the physical defect.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping

from xqi.config import Config
from xqi.types import (
    CAUSE_ACTION,
    DECK_RECIPES,
    PrinterState,
    Proposal,
    Var,
    round_half_up,
)

_GCODE_CMD: dict[str, str] = {
    "nozzle_temp": "M104",
    "bed_temp": "M140",
    "flow": "M221",
    "speed": "M220",
}

# Flow and speed are quoted relative to the sliced value (07-math.md §2).
_VALUE_UNIT: dict[str, str] = {
    "nozzle_temp": "°C",
    "bed_temp": "°C",
    "flow": "%",
    "speed": "%",
}

ACTIONABLE_CAUSES: tuple[str, ...] = tuple(
    cause for cause, action in CAUSE_ACTION.items() if action is not None
)


def severity(area_frac: float, recent_hits: float, cfg: Config) -> float:
    """Severity ``s`` in [0, 1] per 07-math.md §1.

    A heuristic from the detection's area fraction and its recent persistence,
    not a physical defect size.
    """

    a_term = min(1.0, float(area_frac) / cfg.severity.a_ref)
    h_term = min(1.0, float(recent_hits) / cfg.severity.h_ref)

    return max(0.0, min(1.0, 0.5 * a_term + 0.5 * h_term))


def _gcode(var: Var, value: float) -> tuple[str, ...]:
    return (f"{_GCODE_CMD[var]} S{round_half_up(value)}",)


def _counterfactual(
    cause: str,
    p: float,
    var: Var,
    current: float,
    to_value: float,
    delta: float,
    cfg: Config,
) -> str:
    clear_s = cfg.verify.settle_s + cfg.verify.window_s

    return (
        f"Most likely cause: {cause} (p={p:.2f}). "
        f"Smallest in-envelope change that undoes it: "
        f"{var} {current:g}→{to_value:g} {_VALUE_UNIT[var]} ({delta:+g}). "
        f"Expected to clear within {clear_s:g} s if the cause is right."
    )


def make_proposal(
    cause: str,
    p: float,
    severity: float,
    state: PrinterState,
    cfg: Config,
) -> Proposal | None:
    """Build one severity-scaled proposal for an actionable cause.

    Returns ``None`` for ``none`` and ``misalignment`` (07-math.md §2). The
    ``defect_id`` is left empty because the documented signature does not carry
    one; the orchestrator stamps it when it links proposals to an event.
    """

    action = CAUSE_ACTION.get(cause)

    if action is None:
        return None

    var = action[0]
    direction = action[1]
    s = float(severity)

    d_min = cfg.correction.d_min[var]
    d_max = cfg.correction.d_max[var]

    # Δ = -d_c (d_min + s (d_max - d_min))   (07-math.md §2)
    delta = -direction * (d_min + s * (d_max - d_min))

    current = float(state.setpoint(var))
    to_value = current + delta

    return Proposal(
        proposal_id=uuid.uuid4().hex,
        defect_id="",
        cause=cause,
        var=var,  # type: ignore[arg-type]
        from_value=current,
        delta=float(delta),
        to_value=float(to_value),
        gcode=_gcode(var, to_value),
        counterfactual=_counterfactual(
            cause,
            p,
            var,
            current,
            to_value,
            delta,
            cfg,
        ),
    )


def recipe_to_proposals(
    defect: str,
    state: PrinterState,
    defect_id: str,
) -> list[Proposal]:
    """Turn a deck recipe into one proposal per variable (Δ = target - current).

    Used by ``gated-recipe`` mode. Returns an empty list for a defect with no
    configured recipe.
    """

    recipe: Mapping[str, float] | None = DECK_RECIPES.get(defect)

    if recipe is None:
        return []

    proposals: list[Proposal] = []

    for var, target in recipe.items():
        current = float(state.setpoint(var))  # type: ignore[arg-type]
        target_value = float(target)
        delta = target_value - current

        proposals.append(
            Proposal(
                proposal_id=f"{defect_id}:{var}",
                defect_id=defect_id,
                cause="recipe",
                var=var,  # type: ignore[arg-type]
                from_value=current,
                delta=delta,
                to_value=target_value,
                gcode=_gcode(var, target_value),  # type: ignore[arg-type]
                counterfactual=(
                    f"Deck recipe for {defect}: "
                    f"{var} {current:g}→{target_value:g} "
                    f"{_VALUE_UNIT[var]} ({delta:+g})."
                ),
            )
        )

    return proposals


__all__ = [
    "ACTIONABLE_CAUSES",
    "make_proposal",
    "recipe_to_proposals",
    "severity",
]
