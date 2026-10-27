"""Printer conformance test (docs/HANDOFF.md, 09 §Hand-off).

The integrating team points `printer_impl` at their own Printer with a zero-argument factory:

    XQI_PRINTER_IMPL=my_pkg.printer:make_printer uv run pytest tests/test_printer_contract.py

Their printer must be printing, on a part they don't mind losing: the last test sends M112.
"""

import importlib
import math
import os

import pytest

from xqi.printer import FakePrinter, Printer
from xqi.types import PrinterState


@pytest.fixture
def printer_impl():
    spec = os.environ.get("XQI_PRINTER_IMPL")
    if not spec:
        return FakePrinter()
    module, _, factory = spec.partition(":")
    return getattr(importlib.import_module(module), factory)()


def test_is_a_printer(printer_impl):
    assert isinstance(printer_impl, Printer)


def test_get_state_fields_and_units(printer_impl):
    s = printer_impl.get_state()
    assert isinstance(s, PrinterState) and isinstance(s.state, str)
    for value in (s.ts, s.nozzle_actual_c, s.nozzle_target_c, s.bed_actual_c, s.bed_target_c,
                  s.flow_pct, s.speed_pct):
        assert isinstance(value, float) and math.isfinite(value)
    assert 0 <= s.nozzle_actual_c < 400 and 0 <= s.bed_actual_c < 150  # °C, not K or tenths
    assert 1 <= s.flow_pct <= 300 and 1 <= s.speed_pct <= 300  # % of the sliced value, not a fraction
    assert s.progress_pct is None or 0 <= s.progress_pct <= 100
    assert set(s.last_change_ts) <= {"nozzle_temp", "bed_temp", "flow", "speed"}
    assert printer_impl.get_state().ts >= s.ts  # same monotonic clock as Frame.ts


@pytest.mark.parametrize("line, field, value", [
    ("M104 S205", "nozzle_target_c", 205.0),
    ("M221 S95", "flow_pct", 95.0),
    ("M220 S90", "speed_pct", 90.0),
])
def test_setpoint_reflected_in_next_state(printer_impl, line, field, value):
    before = printer_impl.get_state()
    ok = printer_impl.send_gcode([line])

    assert ok is True
    after = printer_impl.get_state()
    assert getattr(after, field) == value
    var = {"nozzle_target_c": "nozzle_temp", "flow_pct": "flow", "speed_pct": "speed"}[field]
    assert after.last_change_ts[var] >= before.ts  # L2 cooldowns read this


def test_pause_resume_return_bool(printer_impl):
    assert printer_impl.pause() is True
    assert printer_impl.get_state().state == "Paused"
    assert printer_impl.pause() is False  # refused, not raised: already paused
    assert printer_impl.resume() is True
    assert printer_impl.get_state().state == "Printing"


def test_refused_commands_return_false_without_raising(printer_impl):
    assert printer_impl.resume() is False  # not paused
    assert isinstance(printer_impl.send_gcode(["G4 P0"]), bool)  # a line it doesn't track still returns a bool


def test_estop_halts(printer_impl):
    assert printer_impl.estop() is True
    assert printer_impl.get_state().state not in ("Printing", "Paused")
    assert printer_impl.send_gcode(["M221 S100"]) is False  # halted: refused, no exception
    assert isinstance(printer_impl.pause(), bool)
