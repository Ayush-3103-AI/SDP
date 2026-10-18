from pathlib import Path

import pytest

from xqi.config import load
from xqi.gate import _window_result, event_verdict, gate
from xqi.types import (
    CauseEstimate,
    CauseSet,
    ConfirmedDefect,
    GateDecision,
    LayerResult,
    PrinterState,
    Proposal,
)

ROOT = Path(__file__).resolve().parents[1]
CFG = load(ROOT / "config" / "default.yaml")


def make_state(**overrides) -> PrinterState:
    base = {
        "ts": 0.0,
        "state": "Printing",
        "nozzle_actual_c": 210.0,
        "nozzle_target_c": 210.0,
        "bed_actual_c": 60.0,
        "bed_target_c": 60.0,
        "flow_pct": 100.0,
        "speed_pct": 100.0,
        "progress_pct": 50.0,
        "last_change_ts": {},
    }
    base.update(overrides)
    return PrinterState(**base)


def make_proposal(var, delta, from_value, cause="flow_low") -> Proposal:
    return Proposal(
        proposal_id="p1",
        defect_id="d1",
        cause=cause,
        var=var,
        from_value=from_value,
        delta=delta,
        to_value=from_value + delta,
        gcode=(),
        counterfactual="",
    )


def make_defect(cls="stringing", defect_id="d1") -> ConfirmedDefect:
    return ConfirmedDefect(
        defect_id=defect_id,
        cls=cls,
        frame_id=1,
        t0=0.0,
        t_conf=1.0,
        conf=0.9,
        xyxy=(1.0, 1.0, 2.0, 2.0),
        area_frac=0.1,
        recent_hits=5,
        severity=0.5,
        critical=cls in {"clog", "layer_shift", "spaghetti"},
    )


def make_cset(members, alpha=0.10, qhat=0.2) -> CauseSet:
    return CauseSet(members=tuple(members), alpha=alpha, qhat=qhat)


def make_est(top="flow_low", p_top=0.9) -> CauseEstimate:
    return CauseEstimate(
        probs={top: p_top},
        top=top,
        p_top=p_top,
    )


def make_gate_decision(proposal_id="p1", passed=True) -> GateDecision:
    return GateDecision(
        proposal_id=proposal_id,
        passed=passed,
        clipped=False,
        final_delta=-5.0,
        final_value=205.0,
        final_gcode=("M104 S205",) if passed else (),
        layers=(LayerResult(layer="L3", passed=passed, reason="test"),),
    )


# --------------------------------------------------------------------------- #
# T-0021 — L2 and L1
# --------------------------------------------------------------------------- #


def test_l2_clips_plus_15_to_plus_5():
    state = make_state(nozzle_target_c=200.0)
    proposal = make_proposal("nozzle_temp", +15.0, 200.0)

    decision = gate(proposal, state, now=1000.0, cfg=CFG)

    assert decision.clipped is True
    assert decision.final_delta == 5.0
    assert decision.final_value == 205.0
    assert decision.final_gcode == ("M104 S205",)
    assert decision.passed is True

    assert decision.layers[0].layer == "L2"
    assert "clipped" in decision.layers[0].reason
    assert "+15" in decision.layers[0].reason
    assert "+5" in decision.layers[0].reason


def test_l2_cooldown_rejects_before_45s():
    state = make_state(
        nozzle_target_c=210.0,
        last_change_ts={"nozzle_temp": 90.0},
    )
    proposal = make_proposal("nozzle_temp", -5.0, 210.0)

    decision = gate(proposal, state, now=100.0, cfg=CFG)

    assert decision.passed is False
    l2 = decision.layers[0]
    assert l2.layer == "L2"
    assert l2.passed is False
    assert "cooldown" in l2.reason


def test_l2_cooldown_allows_change_at_the_limit():
    state = make_state(
        nozzle_target_c=210.0,
        last_change_ts={"nozzle_temp": 55.0},
    )
    proposal = make_proposal("nozzle_temp", -5.0, 210.0)

    decision = gate(proposal, state, now=100.0, cfg=CFG)

    assert decision.passed is True


def test_l1_rejects_target_of_245():
    state = make_state(nozzle_target_c=240.0)
    proposal = make_proposal("nozzle_temp", +5.0, 240.0)

    decision = gate(proposal, state, now=1000.0, cfg=CFG)

    assert decision.passed is False
    assert decision.final_value == 245.0
    l1 = decision.layers[1]
    assert l1.layer == "L1"
    assert l1.passed is False
    assert "245" in l1.reason


def test_round_half_up_pushes_target_over_physical_limit():
    # 145 + 5.5 = 150.5; half-up rounds to 151 > 150 (flow hi) so L1 rejects.
    # Banker's rounding would give 150 and wrongly pass.
    state = make_state(flow_pct=145.0)
    proposal = make_proposal("flow", +5.5, 145.0)

    decision = gate(proposal, state, now=1000.0, cfg=CFG)

    assert decision.final_value == 151.0
    assert decision.passed is False
    assert decision.layers[1].layer == "L1"
    assert decision.layers[1].passed is False


def test_round_half_up_is_used_for_integer_gcode():
    # 210 - 3.5 = 206.5 -> half-up rounds to 207 (matches T-0016).
    state = make_state(nozzle_target_c=210.0)
    proposal = make_proposal(
        "nozzle_temp",
        -3.5,
        210.0,
        cause="nozzle_temp_high",
    )

    decision = gate(proposal, state, now=1000.0, cfg=CFG)

    assert decision.final_value == 207.0
    assert decision.final_gcode == ("M104 S207",)
    assert decision.passed is True


def test_none_state_is_rejected_as_unavailable():
    proposal = make_proposal("nozzle_temp", -5.0, 210.0)

    decision = gate(proposal, None, now=1000.0, cfg=CFG)

    assert decision.passed is False
    assert decision.final_gcode == ()
    assert any(
        layer.reason == "state_unavailable" for layer in decision.layers
    )


def test_nan_state_is_rejected_as_unavailable():
    state = make_state(nozzle_target_c=float("nan"))
    proposal = make_proposal("nozzle_temp", -5.0, 210.0)

    decision = gate(proposal, state, now=1000.0, cfg=CFG)

    assert decision.passed is False
    assert any(
        layer.reason == "state_unavailable" for layer in decision.layers
    )


def test_nan_last_change_is_rejected_as_unavailable():
    state = make_state(last_change_ts={"nozzle_temp": float("nan")})
    proposal = make_proposal("nozzle_temp", -5.0, 210.0)

    decision = gate(proposal, state, now=1000.0, cfg=CFG)

    assert decision.passed is False
    assert any(
        layer.reason == "state_unavailable" for layer in decision.layers
    )


def test_layer_order_is_l2_l1_l3_and_l4_absent():
    state = make_state(nozzle_target_c=210.0)
    proposal = make_proposal("nozzle_temp", -5.0, 210.0)

    decision = gate(proposal, state, now=1000.0, cfg=CFG)

    assert [layer.layer for layer in decision.layers] == ["L2", "L1", "L3"]
    assert decision.layers[2].passed is True


# --------------------------------------------------------------------------- #
# T-0022 — defensive cases on gate()
# --------------------------------------------------------------------------- #


def test_nan_delta_is_rejected_without_gcode():
    state = make_state(nozzle_target_c=210.0)
    proposal = make_proposal("nozzle_temp", float("nan"), 210.0)

    decision = gate(proposal, state, now=1000.0, cfg=CFG)

    assert decision.passed is False
    assert decision.final_gcode == ()
    assert any(
        layer.reason == "invalid_delta" for layer in decision.layers
    )


def test_infinite_delta_is_rejected():
    state = make_state(nozzle_target_c=210.0)
    proposal = make_proposal("nozzle_temp", float("inf"), 210.0)

    decision = gate(proposal, state, now=1000.0, cfg=CFG)

    assert decision.passed is False
    assert decision.final_gcode == ()


def test_nan_and_infinite_time_are_rejected():
    state = make_state(nozzle_target_c=210.0)
    proposal = make_proposal("nozzle_temp", -5.0, 210.0)

    for bad_now in (float("nan"), float("inf")):
        decision = gate(proposal, state, now=bad_now, cfg=CFG)
        assert decision.passed is False
        assert any(
            layer.reason == "invalid_time" for layer in decision.layers
        )


def test_rejected_decision_never_carries_gcode():
    # L1 rejection at 245 °C must not hand back an executable command.
    state = make_state(nozzle_target_c=240.0)
    proposal = make_proposal("nozzle_temp", +5.0, 240.0)

    decision = gate(proposal, state, now=1000.0, cfg=CFG)

    assert decision.passed is False
    assert decision.final_gcode == ()


def test_passed_decision_carries_gcode():
    state = make_state(nozzle_target_c=210.0)
    proposal = make_proposal("nozzle_temp", -5.0, 210.0)

    decision = gate(proposal, state, now=1000.0, cfg=CFG)

    assert decision.passed is True
    assert decision.final_gcode == ("M104 S205",)


# --------------------------------------------------------------------------- #
# T-0022 — L3 toward-window rule
# --------------------------------------------------------------------------- #


def test_l3_toward_window_from_outside_passes_through_gate():
    # Current 235 (outside [195, 225]) -> 230 is still outside but closer.
    state = make_state(nozzle_target_c=235.0)
    proposal = make_proposal("nozzle_temp", -5.0, 235.0)

    decision = gate(proposal, state, now=1000.0, cfg=CFG)

    assert decision.final_value == 230.0
    assert decision.passed is True
    assert decision.layers[2].layer == "L3"
    assert decision.layers[2].passed is True


def test_l3_rule_rejects_moving_away_from_window():
    # Documented example: current 220 -> target 230 moves away from [195, 225].
    layer = _window_result("nozzle_temp", 220.0, 230.0, CFG)

    assert layer.passed is False


def test_l3_rule_accepts_moving_toward_window():
    layer = _window_result("nozzle_temp", 235.0, 230.0, CFG)

    assert layer.passed is True


def test_l3_clipped_change_lands_inside_window():
    # Honest note on the ticket's "220 -> 230 rejects" example: through the full
    # gate L2 clips +10 to +5 first, so the target is 225 which *is* in-window.
    # The reject behaviour is exercised directly above on the L3 rule.
    state = make_state(nozzle_target_c=220.0)
    proposal = make_proposal("nozzle_temp", +10.0, 220.0)

    decision = gate(proposal, state, now=1000.0, cfg=CFG)

    assert decision.clipped is True
    assert decision.final_value == 225.0
    assert decision.passed is True


def test_l3_rejects_moving_away_through_gate():
    # speed step is 10, so +10 is not clipped: 110 -> 120 leaves [80, 110].
    state = make_state(speed_pct=110.0)
    proposal = make_proposal("speed", +10.0, 110.0)

    decision = gate(proposal, state, now=1000.0, cfg=CFG)

    assert decision.passed is False
    l3 = decision.layers[2]
    assert l3.layer == "L3"
    assert l3.passed is False


# --------------------------------------------------------------------------- #
# T-0022 — event_verdict truth table (07-math.md §4)
# --------------------------------------------------------------------------- #


def run_verdict(
    mode="auto",
    cls="stringing",
    members=("flow_low",),
    p_top=0.9,
    flags=(),
    passed=(True,),
    state="ok",
):
    if state is None:
        printer_state = None
    elif state == "nan":
        printer_state = make_state(nozzle_target_c=float("nan"))
    else:
        printer_state = make_state()

    decisions = [
        make_gate_decision(f"p{index}", ok)
        for index, ok in enumerate(passed)
    ]

    return event_verdict(
        mode=mode,
        cd=make_defect(cls=cls),
        cset=make_cset(members),
        est=make_est(p_top=p_top),
        flags=flags,
        decisions=decisions,
        state=printer_state,
        cfg=CFG,
    )


# (id, kwargs, expected_verdict, expected_reason_substring)
VERDICT_ROWS = [
    (
        "row1_critical",
        {"cls": "clog"},
        "CRITICAL",
        "critical clog",
    ),
    (
        "row2_baseline",
        {"mode": "baseline", "cls": "stringing"},
        "APPLY_RAW",
        "baseline",
    ),
    (
        "row3_gated_recipe_survivors",
        {"mode": "gated-recipe", "passed": (True,)},
        "APPLY",
        "gated recipe",
    ),
    (
        "row4_state_unavailable",
        {"mode": "advisory", "state": None},
        "ESCALATE",
        "state_unavailable",
    ),
    (
        "row5_empty_cause_set",
        {"mode": "advisory", "members": ()},
        "ESCALATE",
        "no_confident_cause",
    ),
    (
        "row6_none_cause",
        {"mode": "advisory", "members": ("none",)},
        "NOOP",
        "no_actionable_cause",
    ),
    (
        "row7_misalignment",
        {"mode": "advisory", "members": ("misalignment",)},
        "ESCALATE",
        "mechanical",
    ),
    (
        "row8_no_survivor",
        {"mode": "advisory", "passed": (False,)},
        "ESCALATE",
        "outside_envelope",
    ),
    (
        "row9_auto_l4_pass_single",
        {"mode": "auto", "members": ("flow_low",), "p_top": 0.9},
        "APPLY",
        "auto",
    ),
    (
        "row10_otherwise_propose",
        {"mode": "advisory", "members": ("flow_low",)},
        "PROPOSE",
        "operator review",
    ),
]


@pytest.mark.parametrize(
    ("kwargs", "expected", "reason"),
    [row[1:] for row in VERDICT_ROWS],
    ids=[row[0] for row in VERDICT_ROWS],
)
def test_event_verdict_table(kwargs, expected, reason):
    verdict = run_verdict(**kwargs)

    assert verdict.verdict == expected
    assert reason in verdict.reason


def test_event_verdict_table_has_ten_rows():
    assert len(VERDICT_ROWS) == 10


def test_gated_recipe_without_survivors_is_recipe_blocked():
    verdict = run_verdict(mode="gated-recipe", passed=(False,))

    assert verdict.verdict == "NOOP"
    assert verdict.reason == "recipe_blocked"


def test_l4_fails_with_sensor_flag_so_advisory_proposes():
    verdict = run_verdict(
        mode="auto",
        members=("flow_low",),
        flags=("heater_deviation:nozzle",),
    )

    assert verdict.verdict == "PROPOSE"


def test_l4_fails_with_two_causes_so_advisory_proposes():
    verdict = run_verdict(
        mode="auto",
        members=("flow_low", "nozzle_temp_low"),
    )

    assert verdict.verdict == "PROPOSE"


def test_l4_fails_below_tau_so_advisory_proposes():
    verdict = run_verdict(mode="auto", members=("flow_low",), p_top=0.5)

    assert verdict.verdict == "PROPOSE"


def test_row4_nan_state_escalates():
    verdict = run_verdict(mode="advisory", state="nan")

    assert verdict.verdict == "ESCALATE"
    assert verdict.reason == "state_unavailable"


def test_event_verdict_returns_survivor_ids_when_applying():
    verdict = run_verdict(mode="auto", members=("flow_low",), passed=(True,))

    assert verdict.verdict == "APPLY"
    assert verdict.proposal_ids == ("p0",)
