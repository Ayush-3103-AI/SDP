from pathlib import Path

import pytest

from xqi.config import load
from xqi.explain.counterfactual import (
    make_proposal,
    recipe_to_proposals,
    round_half_up,
    severity,
)
from xqi.types import PrinterState

ROOT = Path(__file__).resolve().parents[1]
CFG = load(ROOT / "config" / "default.yaml")


def _state(nozzle=210.0, bed=60.0, flow=100.0, speed=100.0) -> PrinterState:
    return PrinterState(
        ts=0.0,
        state="Printing",
        nozzle_actual_c=nozzle,
        nozzle_target_c=nozzle,
        bed_actual_c=bed,
        bed_target_c=bed,
        flow_pct=flow,
        speed_pct=speed,
        progress_pct=None,
        last_change_ts={},
    )


@pytest.mark.parametrize(
    ("area_frac", "recent_hits", "expected"),
    [
        (0.01, 0, 0.25),
        (0.02, 15, 1.0),
        (0.5, 30, 1.0),
        (0.0, 0, 0.0),
        (0.01, 7.5, 0.5),
    ],
)
def test_severity(area_frac, recent_hits, expected):
    assert severity(area_frac, recent_hits, CFG) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("x", "expected"),
    [(206.5, 207), (110.0, 110), (2.5, 3), (3.5, 4), (-0.5, 0), (99.49, 99)],
)
def test_round_half_up(x, expected):
    assert round_half_up(x) == expected


@pytest.mark.parametrize(
    ("cause", "s", "state", "var", "delta", "to_value", "gcode"),
    [
        ("flow_low", 0.0, _state(), "flow", 5.0, 105.0, "M221 S105"),
        ("flow_low", 1.0, _state(), "flow", 10.0, 110.0, "M221 S110"),
        ("nozzle_temp_high", 0.5, _state(), "nozzle_temp", -3.5, 206.5, "M104 S207"),
        ("bed_temp_low", 0.0, _state(), "bed_temp", 2.0, 62.0, "M140 S62"),
        ("speed_high", 1.0, _state(), "speed", -10.0, 90.0, "M220 S90"),
    ],
)
def test_make_proposal(cause, s, state, var, delta, to_value, gcode):
    p = make_proposal(cause, 0.8, s, state, CFG, defect_id="d1")

    assert p.var == var
    assert p.cause == cause
    assert p.defect_id == "d1"
    assert p.from_value == state.setpoint(var)
    assert p.delta == pytest.approx(delta)
    assert p.to_value == pytest.approx(to_value)
    assert p.gcode == (gcode,)


def test_counterfactual_sentence():
    p = make_proposal("flow_low", 0.83, 1.0, _state(), CFG)

    assert p.counterfactual == (
        "Most likely cause: flow low (p=0.83). Smallest in-envelope change that "
        "undoes it: flow 100→110 % (+10). Expected to clear within 150 s if the "
        "cause is right."
    )


@pytest.mark.parametrize("cause", ["none", "misalignment"])
def test_non_setpoint_causes_give_no_proposal(cause):
    assert make_proposal(cause, 0.9, 1.0, _state(), CFG) is None


def test_under_extrusion_recipe_from_nominal():
    nominal = CFG.printer.nominal
    state = _state(
        nominal["nozzle_temp"], nominal["bed_temp"], nominal["flow"], nominal["speed"]
    )

    props = recipe_to_proposals("under_extrusion", state, "d7")

    assert {p.var: p.delta for p in props} == {
        "nozzle_temp": -5,
        "speed": -20,
        "flow": 10,
    }
    assert {p.gcode for p in props} == {("M104 S205",), ("M220 S80",), ("M221 S110",)}
    assert all(p.defect_id == "d7" for p in props)
    assert len({p.proposal_id for p in props}) == 3


def test_defect_without_recipe_gives_no_proposals():
    assert recipe_to_proposals("clog", _state(), "d1") == []
