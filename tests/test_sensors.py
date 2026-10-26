from pathlib import Path

import pytest

from xqi.config import load
from xqi.explain.sensors import check
from xqi.types import PrinterState

CFG = load(Path(__file__).resolve().parents[1] / "config" / "default.yaml")


def _state(ts, nozzle=210.0, nozzle_target=210.0, bed=60.0, bed_target=60.0,
           state="Printing", last_change_ts=None):
    return PrinterState(
        ts=ts,
        state=state,
        nozzle_actual_c=nozzle,
        nozzle_target_c=nozzle_target,
        bed_actual_c=bed,
        bed_target_c=bed_target,
        flow_pct=100.0,
        speed_pct=100.0,
        progress_pct=50.0,
        last_change_ts=last_change_ts or {},
    )


def _history(seconds, **deviating):
    """1 Hz samples t=100..200; the last `seconds` of them carry `deviating`."""
    return [
        _state(float(t), **(deviating if t >= 200 - seconds else {}))
        for t in range(100, 201)
    ]


@pytest.mark.parametrize(
    ("seconds", "deviating", "expected"),
    [
        (12, {"nozzle": 204.0}, ("heater_deviation:nozzle",)),
        (8, {"nozzle": 204.0}, ()),
        (12, {"bed": 66.0}, ("heater_deviation:bed",)),
        (12, {"nozzle": 205.0}, ()),  # exactly delta_T is not "> delta_T"
        (12, {"state": "Paused"}, ("printer_not_printing",)),
        (0, {}, ()),
    ],
)
def test_heater_and_state_flags(seconds, deviating, expected):
    assert check(_history(seconds, **deviating), 200.0, CFG) == expected


def test_deviation_that_recovered_does_not_flag():
    history = _history(30, nozzle=204.0)
    history[-1] = _state(200.0)

    assert check(history, 200.0, CFG) == ()


def test_target_changed_30s_ago_is_settling():
    history = _history(30, nozzle_target=215.0, nozzle=215.0)

    assert check(history, 200.0, CFG) == ("settling:nozzle_temp",)


def test_tracked_change_30s_ago_is_settling():
    history = [_state(200.0, last_change_ts={"nozzle_temp": 170.0})]

    assert check(history, 200.0, CFG) == ("settling:nozzle_temp",)


def test_bed_change_past_nozzle_window_still_settling():
    history = [_state(200.0, last_change_ts={"nozzle_temp": 140.0, "bed_temp": 140.0})]

    assert check(history, 200.0, CFG) == ("settling:bed_temp",)


def test_empty_history_is_state_unavailable():
    assert check([], 200.0, CFG) == ("state_unavailable",)
