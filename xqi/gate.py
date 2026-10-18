"""Safety gate for one proposed correction, plus the event verdict.

Pure and fail-closed (ADR-0004): no I/O, no printer commands, no global state.

* T-0021 implements the proposal-level layers L2 (rate/step + cooldown) and L1
  (physical limits), with the required state checked first.
* T-0022 implements the real L3 (characterised process window, with the
  "moving toward the window is allowed" rule) and ``event_verdict`` (the §4
  truth table, where L4 confidence is evaluated per event).

See 07-math.md §3-§4', 08-pseudocode.md P4 and ADR-0004.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import fields

from xqi.config import Config
from xqi.types import (
    CauseEstimate,
    CauseSet,
    ConfirmedDefect,
    EventVerdict,
    GateDecision,
    LayerResult,
    PrinterState,
    Proposal,
    Var,
    round_half_up,
)

# Flow and speed are quoted relative to the sliced value.
_VARS: tuple[Var, ...] = ("nozzle_temp", "bed_temp", "flow", "speed")

_UNIT: dict[str, str] = {
    "nozzle_temp": "°C",
    "bed_temp": "°C",
    "flow": "pp",
    "speed": "pp",
}

_GCODE_CMD: dict[str, str] = {
    "nozzle_temp": "M104",
    "bed_temp": "M140",
    "flow": "M221",
    "speed": "M220",
}


def _unit(var: Var) -> str:
    return _UNIT[var]


def _gcode(var: Var, value: int) -> tuple[str, ...]:
    return (f"{_GCODE_CMD[var]} S{value}",)


def _rejected(
    proposal_id: str,
    layer: str,
    reason: str,
) -> GateDecision:
    """A fail-closed decision that never carries executable G-code."""

    return GateDecision(
        proposal_id=proposal_id,
        passed=False,
        clipped=False,
        final_delta=0.0,
        final_value=0.0,
        final_gcode=(),
        layers=(
            LayerResult(layer=layer, passed=False, reason=reason),  # type: ignore[arg-type]
        ),
    )


def _distance(y: float, lo: float, hi: float) -> float:
    """Distance from ``y`` to the closed interval ``[lo, hi]`` (0 if inside)."""

    return max(lo - y, 0.0, y - hi)


def _window_result(
    var: Var,
    current: float,
    target: float,
    cfg: Config,
) -> LayerResult:
    """L3: inside the characterised window, or strictly closer to it."""

    lo, hi = cfg.envelope.L3.window[var]
    inside = lo <= target <= hi

    if inside:
        return LayerResult(
            layer="L3",
            passed=True,
            reason=f"target {target} inside window [{lo:g}, {hi:g}] {_unit(var)}",
        )

    d_target = _distance(target, lo, hi)
    d_current = _distance(current, lo, hi)

    if d_target < d_current:
        return LayerResult(
            layer="L3",
            passed=True,
            reason=(
                f"target {target} moves toward window [{lo:g}, {hi:g}] "
                f"({d_target:g} < {d_current:g})"
            ),
        )

    return LayerResult(
        layer="L3",
        passed=False,
        reason=(
            f"target {target} outside window [{lo:g}, {hi:g}] and no closer "
            f"({d_target:g} >= {d_current:g})"
        ),
    )


def _state_available(state: PrinterState, var: Var) -> bool:
    """True iff the state fields the gate needs for ``var`` are finite."""

    if not math.isfinite(state.setpoint(var)):
        return False

    changes = state.last_change_ts or {}
    last = changes.get(var)

    return last is None or math.isfinite(last)


def gate(
    p: Proposal,
    state: PrinterState | None,
    now: float,
    cfg: Config,
) -> GateDecision:
    """Run the proposal-level safety checks L2 → L1 → L3.

    The decision is rejected (``passed=False``) if the variable is in cooldown,
    if the target leaves the physical envelope or the characterised window, or
    if the required state/time/delta is missing, NaN or infinite. A rejected
    decision never carries executable G-code. L4 is evaluated per event in
    :func:`event_verdict`.
    """

    var = p.var

    if state is None or not _state_available(state, var):
        return _rejected(p.proposal_id, "L1", "state_unavailable")

    if not math.isfinite(p.delta):
        return _rejected(p.proposal_id, "L2", "invalid_delta")

    if not math.isfinite(now):
        return _rejected(p.proposal_id, "L2", "invalid_time")

    current = state.setpoint(var)
    changes = state.last_change_ts or {}
    last = changes.get(var, float("-inf"))

    step = cfg.envelope.L2.step[var]
    cooldown = cfg.envelope.L2.cooldown_s[var]

    # L2 — cooldown, then clip the step magnitude.
    elapsed = now - last
    in_cooldown = elapsed < cooldown
    magnitude = min(abs(p.delta), step)
    delta = magnitude if p.delta >= 0 else -magnitude
    clipped = delta != p.delta

    if in_cooldown:
        l2 = LayerResult(
            layer="L2",
            passed=False,
            reason=f"cooldown {elapsed:.0f}s < {cooldown:g}s",
        )
    elif clipped:
        l2 = LayerResult(
            layer="L2",
            passed=True,
            reason=f"clipped {p.delta:+g} → {delta:+g} {_unit(var)}",
        )
    else:
        l2 = LayerResult(
            layer="L2",
            passed=True,
            reason=f"Δ {delta:+g} {_unit(var)} within step {step:g}",
        )

    # Rounding happens before the L1/L3 comparisons (G-code is integer).
    target = round_half_up(current + delta)

    # L1 — physical envelope.
    lo, hi = getattr(cfg.envelope.L1, var)
    if lo <= target <= hi:
        l1 = LayerResult(
            layer="L1",
            passed=True,
            reason=f"{target} within [{lo:g}, {hi:g}] {_unit(var)}",
        )
    else:
        l1 = LayerResult(
            layer="L1",
            passed=False,
            reason=f"{target} outside [{lo:g}, {hi:g}] {_unit(var)}",
        )

    # L3 — characterised process window (toward-window rule in _window_result).
    l3 = _window_result(var, current, target, cfg)

    passed = l2.passed and l1.passed and l3.passed

    return GateDecision(
        proposal_id=p.proposal_id,
        passed=passed,
        clipped=clipped,
        final_delta=delta,
        final_value=float(target),
        final_gcode=_gcode(var, target) if passed else (),
        layers=(l2, l1, l3),
    )


def _critical_classes(cfg: Config) -> set[str]:
    return {field.name for field in fields(cfg.critical)}


def _survivors(decisions: Sequence[GateDecision]) -> list[GateDecision]:
    return [d for d in decisions if d.passed]


def _state_missing(state: PrinterState | None) -> bool:
    if state is None:
        return True

    for var in _VARS:
        if not math.isfinite(state.setpoint(var)):
            return True

    changes = state.last_change_ts or {}
    return any(not math.isfinite(value) for value in changes.values())


def event_verdict(
    mode: str,
    cd: ConfirmedDefect,
    cset: CauseSet | None,
    est: CauseEstimate | None,
    flags: Sequence[str],
    decisions: Sequence[GateDecision],
    state: PrinterState | None,
    cfg: Config,
) -> EventVerdict:
    """Route one confirmed defect using the 07-math.md §4 truth table.

    Rows are evaluated in order and the first match wins. L4 (confidence) is
    evaluated here, not in :func:`gate`.
    """

    members = () if cset is None else cset.members
    survivors = _survivors(decisions)

    # Row 1 — critical classes act first, no gate (FR-005).
    if cd.cls in _critical_classes(cfg):
        action = getattr(cfg.critical, cd.cls)
        return EventVerdict(
            defect_id=cd.defect_id,
            verdict="CRITICAL",
            reason=f"critical {cd.cls}: {action}",
            proposal_ids=(),
        )

    # Row 2 — baseline reproduces the deck raw (no gate).
    if mode == "baseline":
        return EventVerdict(
            defect_id=cd.defect_id,
            verdict="APPLY_RAW",
            reason="baseline mode: deck recipe, ungated",
            proposal_ids=(),
        )

    # Row 3 — gated-recipe: apply the surviving recipe variables, else NOOP.
    if mode == "gated-recipe":
        if survivors:
            return EventVerdict(
                defect_id=cd.defect_id,
                verdict="APPLY",
                reason="gated recipe: survivors applied",
                proposal_ids=tuple(d.proposal_id for d in survivors),
            )
        return EventVerdict(
            defect_id=cd.defect_id,
            verdict="NOOP",
            reason="recipe_blocked",
            proposal_ids=(),
        )

    # Row 4 — required state missing or NaN.
    if _state_missing(state):
        return EventVerdict(
            defect_id=cd.defect_id,
            verdict="ESCALATE",
            reason="state_unavailable",
            proposal_ids=(),
        )

    # Row 5 — empty cause set.
    if not members:
        return EventVerdict(
            defect_id=cd.defect_id,
            verdict="ESCALATE",
            reason="no_confident_cause",
            proposal_ids=(),
        )

    # Row 6 — only "none".
    if members == ("none",):
        return EventVerdict(
            defect_id=cd.defect_id,
            verdict="NOOP",
            reason="no_actionable_cause",
            proposal_ids=(),
        )

    # Row 7 — misalignment forces escalation.
    if "misalignment" in members:
        return EventVerdict(
            defect_id=cd.defect_id,
            verdict="ESCALATE",
            reason="mechanical",
            proposal_ids=(),
        )

    # Row 8 — nothing survives the gate.
    if not survivors:
        return EventVerdict(
            defect_id=cd.defect_id,
            verdict="ESCALATE",
            reason="outside_envelope",
            proposal_ids=(),
        )

    # Row 9 — auto + L4 pass + exactly one survivor → apply it.
    l4_pass = (
        len(members) == 1
        and est is not None
        and est.p_top >= cfg.envelope.L4.tau
        and not flags
    )
    if mode == "auto" and l4_pass and len(survivors) == 1:
        return EventVerdict(
            defect_id=cd.defect_id,
            verdict="APPLY",
            reason=f"auto: L4 pass, p={est.p_top:.2f}",  # type: ignore[union-attr]
            proposal_ids=(survivors[0].proposal_id,),
        )

    # Row 10 — otherwise propose the survivors (auto or advisory).
    return EventVerdict(
        defect_id=cd.defect_id,
        verdict="PROPOSE",
        reason="operator review required",
        proposal_ids=tuple(d.proposal_id for d in survivors),
    )


__all__ = ["event_verdict", "gate"]
