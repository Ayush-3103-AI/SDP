from pathlib import Path

import pytest

from xqi.config import load
from xqi.explain.counterfactual import (
    make_proposal,
    recipe_to_proposals,
    severity,
)
from xqi.types import PrinterState

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


# --------------------------------------------------------------------------- #
# severity (07-math.md §1)
# --------------------------------------------------------------------------- #


def test_severity_zero_when_small_and_absent():
    assert severity(0.0, 0, CFG) == pytest.approx(0.0)


def test_severity_one_when_large_and_persistent():
    assert severity(1.0, 1000, CFG) == pytest.approx(1.0)


def test_severity_is_half_area_and_half_persistence():
    # a/a_ref = 0.01/0.02 = 0.5 ; h/h_ref = 15/15 = 1 -> 0.5*0.5 + 0.5*1 = 0.75
    assert severity(0.01, 15, CFG) == pytest.approx(0.75)


def test_severity_clipped_to_one():
    assert severity(10.0, 10000, CFG) == pytest.approx(1.0)


# --------------------------------------------------------------------------- #
# make_proposal (07-math.md §2)
# --------------------------------------------------------------------------- #


def test_flow_low_at_severity_zero_is_plus_five():
    proposal = make_proposal("flow_low", 0.6, 0.0, make_state(), CFG)

    assert proposal is not None
    assert proposal.var == "flow"
    assert proposal.delta == pytest.approx(5.0)
    assert proposal.to_value == pytest.approx(105.0)


def test_flow_low_at_severity_one_is_plus_ten_and_m221_s110():
    proposal = make_proposal("flow_low", 0.6, 1.0, make_state(), CFG)

    assert proposal is not None
    assert proposal.delta == pytest.approx(10.0)
    assert proposal.to_value == pytest.approx(110.0)
    assert proposal.gcode == ("M221 S110",)


def test_nozzle_temp_high_at_half_severity_rounds_half_up():
    proposal = make_proposal("nozzle_temp_high", 0.7, 0.5, make_state(), CFG)

    assert proposal is not None
    assert proposal.var == "nozzle_temp"
    assert proposal.delta == pytest.approx(-3.5)
    assert proposal.to_value == pytest.approx(206.5)
    assert proposal.gcode == ("M104 S207",)


def test_none_cause_returns_no_proposal():
    assert make_proposal("none", 0.9, 0.5, make_state(), CFG) is None


def test_misalignment_returns_no_proposal():
    assert make_proposal("misalignment", 0.9, 0.5, make_state(), CFG) is None


def test_counterfactual_contains_template_fields():
    proposal = make_proposal("flow_low", 0.64, 0.0, make_state(), CFG)

    assert proposal is not None
    text = proposal.counterfactual
    assert "Most likely cause: flow_low (p=0.64)" in text
    assert "flow 100→105 % (+5)" in text
    assert "150 s" in text  # settle 30 + window 120


def test_every_actionable_cause_maps_to_a_proposal():
    for cause in (
        "nozzle_temp_low",
        "nozzle_temp_high",
        "flow_low",
        "flow_high",
        "speed_low",
        "speed_high",
        "bed_temp_low",
    ):
        assert make_proposal(cause, 0.5, 0.5, make_state(), CFG) is not None


# --------------------------------------------------------------------------- #
# recipe_to_proposals
# --------------------------------------------------------------------------- #


def test_under_extrusion_recipe_makes_three_proposals_from_nominal():
    proposals = recipe_to_proposals("under_extrusion", make_state(), "d1")

    assert [p.var for p in proposals] == ["nozzle_temp", "speed", "flow"]
    assert [p.delta for p in proposals] == pytest.approx([-5.0, -20.0, +10.0])
    assert [p.to_value for p in proposals] == pytest.approx([205.0, 80.0, 110.0])
    assert all(p.defect_id == "d1" for p in proposals)


def test_recipe_proposals_carry_integer_gcode():
    proposals = recipe_to_proposals("under_extrusion", make_state(), "d1")
    gcode = {p.var: p.gcode for p in proposals}

    assert gcode["nozzle_temp"] == ("M104 S205",)
    assert gcode["speed"] == ("M220 S80",)
    assert gcode["flow"] == ("M221 S110",)


def test_warping_recipe_only_touches_bed():
    proposals = recipe_to_proposals("warping", make_state(), "d2")

    assert [p.var for p in proposals] == ["bed_temp"]
    assert proposals[0].delta == pytest.approx(5.0)


def test_unknown_defect_recipe_is_empty():
    assert recipe_to_proposals("stringing", make_state(), "d3")[0].var == "nozzle_temp"
    assert recipe_to_proposals("not_a_defect", make_state(), "d4") == []
