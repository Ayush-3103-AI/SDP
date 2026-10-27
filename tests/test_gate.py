import math
from dataclasses import replace
from pathlib import Path

import pytest

from xqi.config import load
from xqi.gate import event_verdict, gate, l3_pass, round_half_up
from xqi.types import (
    CauseEstimate,
    CauseSet,
    ConfirmedDefect,
    GateDecision,
    PrinterState,
    Proposal,
)

ROOT = Path(__file__).resolve().parents[1]
CFG = load(ROOT / "config" / "default.yaml")
NOW = 1000.0


def _state(nozzle=210.0, last_change_ts=None):
    return PrinterState(
        ts=NOW,
        state="printing",
        nozzle_actual_c=nozzle,
        nozzle_target_c=nozzle,
        bed_actual_c=60.0,
        bed_target_c=60.0,
        flow_pct=100.0,
        speed_pct=100.0,
        progress_pct=50.0,
        last_change_ts=last_change_ts or {},
    )


def _proposal(var="nozzle_temp", from_value=210.0, delta=3.0):
    return Proposal(
        proposal_id="p1",
        defect_id="d1",
        cause="nozzle_temp_low",
        var=var,
        from_value=from_value,
        delta=delta,
        to_value=from_value + delta,
        gcode=(),
        counterfactual="",
    )


def test_round_half_up_is_not_bankers():
    assert round_half_up(206.5) == 207
    assert round_half_up(212.5) == 213
    assert round_half_up(-2.5) == -2


def test_in_bounds_passes_with_integer_gcode():
    d = gate(_proposal(delta=3.0), _state(), NOW, CFG)

    assert d.passed and not d.clipped
    assert d.final_value == 213 and d.final_delta == 3
    assert d.final_gcode == ("M104 S213",)
    assert [r.layer for r in d.layers] == ["L2", "L1", "L3"]
    assert all(r.passed and r.reason for r in d.layers)


def test_l2_clips_plus_15_to_plus_5():
    d = gate(_proposal(var="flow", from_value=100.0, delta=15.0), _state(), NOW, CFG)

    assert d.passed and d.clipped
    assert d.final_delta == 10 and d.final_gcode == ("M221 S110",)

    d = gate(_proposal(delta=15.0), _state(), NOW, CFG)

    assert d.passed and d.clipped
    assert d.final_value == 215 and d.final_delta == 5
    assert d.layers[0].reason == "L2: clipped +15 → +5 °C"


def test_l2_cooldown_rejects_at_10s():
    state = _state(last_change_ts={"nozzle_temp": NOW - 10})

    d = gate(_proposal(), state, NOW, CFG)

    assert not d.passed and d.final_gcode == ()
    assert [r.layer for r in d.layers] == ["L2"]
    assert d.layers[0].reason == "L2: cooldown 10s < 45s"


def test_l1_rejects_245():
    d = gate(_proposal(from_value=240.0, delta=5.0), _state(nozzle=240.0), NOW, CFG)

    assert not d.passed and d.final_gcode == ()
    assert d.layers[-1].layer == "L1" and not d.layers[-1].passed
    assert d.layers[-1].reason == "L1: 245 °C outside [170, 240]"


def test_rounding_pushes_over_l1_limit():
    # 235.5 + 5 = 240.5 is ≤ 240 only before rounding; G-code would send 241.
    d = gate(_proposal(from_value=235.5, delta=5.0), _state(nozzle=235.5), NOW, CFG)

    assert not d.passed
    assert d.layers[-1].reason == "L1: 241 °C outside [170, 240]"


@pytest.mark.parametrize(
    "state",
    [
        None,
        _state(nozzle=math.nan),
        _state(last_change_ts={"nozzle_temp": math.nan}),
    ],
)
def test_state_unavailable_fails_closed(state):
    d = gate(_proposal(), state, NOW, CFG)

    assert not d.passed and d.final_gcode == ()
    assert d.layers[0].reason == "state_unavailable"


def test_nan_delta_fails_closed():
    d = gate(replace(_proposal(), delta=math.nan), _state(), NOW, CFG)

    assert not d.passed
    assert d.layers[0].reason == "state_unavailable"


def test_l3_toward_window_passes_from_outside():
    # 235 is above the window max 225, but 230 is closer to it.
    d = gate(_proposal(from_value=235.0, delta=-5.0), _state(nozzle=235.0), NOW, CFG)

    assert d.passed and d.final_gcode == ("M104 S230",)
    assert d.layers[-1].layer == "L3" and d.layers[-1].passed


def test_l3_rules():
    window = (195.0, 225.0)
    assert l3_pass(235.0, 230.0, window)
    assert not l3_pass(220.0, 230.0, window)
    assert l3_pass(220.0, 225.0, window)
    assert not l3_pass(230.0, 230.0, window)  # equal distance is not a decrease


def test_l3_rejects_moving_out_of_window():
    d = gate(_proposal(from_value=225.0, delta=5.0), _state(nozzle=225.0), NOW, CFG)

    assert not d.passed and d.final_gcode == ()
    assert d.layers[-1].layer == "L3" and not d.layers[-1].passed
    assert d.layers[-1].reason == "L3: 230 °C moves away from [195, 225]"


def _cd(cls="under_extrusion"):
    return ConfirmedDefect(
        defect_id="d1", cls=cls, frame_id=1, t0=NOW - 5, t_conf=NOW, conf=0.9,
        xyxy=(0.0, 0.0, 1.0, 1.0), area_frac=0.01, recent_hits=4, severity=0.5,
        critical=cls in ("clog", "layer_shift", "spaghetti"),
    )


def _dec(pid="p1", passed=True):
    return GateDecision(pid, passed, False, 3.0 if passed else 0.0, 213.0, (), ())


EST = CauseEstimate({"nozzle_temp_low": 0.8, "none": 0.2}, "nozzle_temp_low", 0.8)
ONE = CauseSet(("nozzle_temp_low",), 0.1, 0.5)


@pytest.mark.parametrize(
    "row, kw, verdict, reason, ids",
    [
        (1, {"cd": _cd("spaghetti")}, "CRITICAL", "estop", ()),
        (2, {"mode": "baseline"}, "APPLY_RAW", "deck_recipe", ()),
        (3, {"mode": "gated-recipe", "decisions": [_dec("a"), _dec("b", False)]}, "APPLY",
         "recipe", ("a",)),
        (3, {"mode": "gated-recipe", "decisions": [_dec("a", False)]}, "NOOP", "recipe_blocked", ()),
        (4, {"state": _state(nozzle=math.nan)}, "ESCALATE", "state_unavailable", ()),
        (4, {"state": None}, "ESCALATE", "state_unavailable", ()),
        (5, {"cset": CauseSet((), 0.1, 0.5)}, "ESCALATE", "no_confident_cause", ()),
        (5, {"cset": None}, "ESCALATE", "no_confident_cause", ()),
        (6, {"cset": CauseSet(("none",), 0.1, 0.5)}, "NOOP", "no_actionable_cause", ()),
        (7, {"cset": CauseSet(("flow_low", "z_offset_high"), 0.1, 0.5)}, "ESCALATE",
         "manual:z_offset_high", ()),
        (8, {"decisions": [_dec("a", False)]}, "ESCALATE", "outside_envelope", ()),
        (8, {"decisions": []}, "ESCALATE", "outside_envelope", ()),
        (9, {}, "APPLY", "L4: pass", ("p1",)),
        (10, {"mode": "advisory"}, "PROPOSE", "advisory", ("p1",)),
        (10, {"est": CauseEstimate({"nozzle_temp_low": 0.55}, "nozzle_temp_low", 0.55)},
         "PROPOSE", "L4: p_top 0.55 < 0.6", ("p1",)),
        (10, {"est": None}, "PROPOSE", "L4: no cause estimate", ("p1",)),
        (10, {"flags": ("temp_unstable",)}, "PROPOSE", "L4: sensor flags temp_unstable", ("p1",)),
        (10, {"cset": CauseSet(("nozzle_temp_low", "flow_low"), 0.1, 0.5),
                  "decisions": [_dec("a"), _dec("b")]}, "PROPOSE", "L4: |C| = 2", ("a", "b")),
        (10, {"decisions": [_dec("a"), _dec("b")]}, "PROPOSE", "2 surviving proposals",
         ("a", "b")),
    ],
)
def test_event_verdict_table(row, kw, verdict, reason, ids):
    args = {"mode": "auto", "cd": _cd(), "cset": ONE, "est": EST, "flags": (), "decisions": [_dec()],
                "state": _state()}
    args.update(kw)

    v = event_verdict(cfg=CFG, **args)

    assert (v.defect_id, v.verdict, v.reason, v.proposal_ids) == (
        args["cd"].defect_id, verdict, reason, ids
    )


@pytest.mark.parametrize("cause", ["z_offset_low", "z_offset_high", "misalignment"])
def test_manual_cause_escalates(cause):
    # misalignment left CAUSES but the integrating team's detector may still emit it (T-0057).
    v = event_verdict("auto", _cd(), CauseSet((cause, "nozzle_temp_low"), 0.1, 0.5), EST, (), [_dec()],
                      _state(), CFG)

    assert (v.verdict, v.reason, v.proposal_ids) == ("ESCALATE", f"manual:{cause}", ())
