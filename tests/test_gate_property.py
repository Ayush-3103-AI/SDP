"""Randomised gate property test (T-0023, NFR-004, 07-math.md §3).

No hypothesis library: a fixed-seed ``random.Random`` drives ~100 000 random
gate calls and simulates sequential dispatch of the passing decisions. Every
dispatch is checked against the four-clause safety invariant:

* ``|Δ'| ≤ step_v``;
* ``lo1_v ≤ x'' ≤ hi1_v``;
* ``x''`` is in the L3 window or strictly closer to it than before;
* no two dispatched changes to the same variable are closer than ``cool_v``.

The default (fast) suite runs 1 000 cases; the 100 000-case version is marked
``slow`` and writes ``reports/gate_property.md``.
"""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from xqi.config import load
from xqi.gate import gate
from xqi.types import PrinterState, Proposal

ROOT = Path(__file__).resolve().parents[1]
CFG = load(ROOT / "config" / "default.yaml")
REPORT = ROOT / "reports" / "gate_property.md"

VARS = ("nozzle_temp", "bed_temp", "flow", "speed")
SEED = 0
RANDOM_CHANGE_PROB = 0.3
MARGIN = 1e-9


def _dist(y: float, lo: float, hi: float) -> float:
    return max(lo - y, 0.0, y - hi)


def _sample_setpoint(rng: random.Random, var: str) -> float:
    """Sample a setpoint inside the L1 box widened by 20 % of its span."""

    lo, hi = getattr(CFG.envelope.L1, var)
    span = hi - lo

    return rng.uniform(lo - 0.2 * span, hi + 0.2 * span)


def _state(
    current: dict[str, float],
    last: dict[str, float],
    now: float,
) -> PrinterState:
    return PrinterState(
        ts=now,
        state="Printing",
        nozzle_actual_c=current["nozzle_temp"],
        nozzle_target_c=current["nozzle_temp"],
        bed_actual_c=current["bed_temp"],
        bed_target_c=current["bed_temp"],
        flow_pct=current["flow"],
        speed_pct=current["speed"],
        progress_pct=50.0,
        last_change_ts=dict(last),
    )


def run_property(
    iterations: int,
    seed: int = SEED,
) -> tuple[int, list[tuple[str, str, float]]]:
    """Return ``(dispatched, violations)`` for ``iterations`` random cases."""

    rng = random.Random(seed)

    current = {var: _sample_setpoint(rng, var) for var in VARS}
    last = {var: rng.uniform(-500.0, 0.0) for var in VARS}
    now = 0.0

    dispatched = 0
    violations: list[tuple[str, str, float]] = []

    for _ in range(iterations):
        var = rng.choice(VARS)
        now += rng.uniform(0.0, 30.0)

        # Occasionally model an external edit to the target.
        if rng.random() < RANDOM_CHANGE_PROB:
            last[var] = now - rng.uniform(-2.0, 60.0)

        state = _state(current, last, now)
        before = current[var]
        delta = rng.uniform(-50.0, 50.0)

        proposal = Proposal(
            proposal_id="p",
            defect_id="d",
            cause="flow_low",
            var=var,  # type: ignore[arg-type]
            from_value=before,
            delta=delta,
            to_value=before + delta,
            gcode=(),
            counterfactual="",
        )

        decision = gate(proposal, state, now, CFG)

        if not decision.passed:
            continue

        dispatched += 1

        step = CFG.envelope.L2.step[var]
        cool = CFG.envelope.L2.cooldown_s[var]
        lo1, hi1 = getattr(CFG.envelope.L1, var)
        lo3, hi3 = CFG.envelope.L3.window[var]
        value = decision.final_value

        if abs(decision.final_delta) > step + MARGIN:
            violations.append((var, "step", decision.final_delta))

        if not (lo1 - MARGIN <= value <= hi1 + MARGIN):
            violations.append((var, "L1", value))

        inside_or_closer = (
            lo3 - MARGIN <= value <= hi3 + MARGIN
            or _dist(value, lo3, hi3) < _dist(before, lo3, hi3)
        )
        if not inside_or_closer:
            violations.append((var, "L3", value))

        if now - last[var] < cool - MARGIN:
            violations.append((var, "cooldown", now - last[var]))

        current[var] = value
        last[var] = now

    return dispatched, violations


def test_gate_invariant_1000_cases():
    dispatched, violations = run_property(1000, seed=SEED)

    assert dispatched > 0
    assert violations == []


@pytest.mark.slow
def test_gate_invariant_100000_cases():
    iterations = 100_000
    dispatched, violations = run_property(iterations, seed=SEED)

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "\n".join(
            [
                "# Gate property test (T-0023 / NFR-004)",
                "",
                f"- seed: {SEED}",
                f"- cases: {iterations}",
                f"- dispatched: {dispatched}",
                f"- violations: {len(violations)}",
                "",
                (
                    "Invariant (07-math.md §3): every dispatched setpoint change "
                    "satisfies |Δ'| ≤ step, stays inside L1, is in the L3 window "
                    "or moves toward it, and respects the per-variable cooldown."
                ),
                "",
                (
                    "Result: 0 violations."
                    if not violations
                    else f"VIOLATIONS: {violations}"
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )

    assert violations == []
