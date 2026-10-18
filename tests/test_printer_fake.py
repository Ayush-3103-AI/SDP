"""T-0026 — the Printer protocol and the FakePrinter simulator."""

from __future__ import annotations

import math

import pytest

from xqi.printer import TAU_BED_S, TAU_NOZZLE_S, FakePrinter, Printer, PrinterError


class Clock:
    """A monotonic clock the test controls."""

    def __init__(self, t: float = 0.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def test_fake_printer_satisfies_the_protocol():
    assert isinstance(FakePrinter(), Printer)


def test_m104_reaches_one_time_constant_after_tau():
    clock = Clock()
    printer = FakePrinter(clock=clock)

    assert printer.send_gcode(["M104 S220"]) is True
    assert printer.nozzle_target_c == 220

    clock.advance(TAU_NOZZLE_S)
    state = printer.get_state()

    expected = 210.0 + (220.0 - 210.0) * (1.0 - math.exp(-1.0))
    assert state.nozzle_target_c == 220
    assert abs(state.nozzle_actual_c - expected) < 0.5


def test_bed_lag_uses_its_own_time_constant():
    clock = Clock()
    printer = FakePrinter(clock=clock)

    printer.send_gcode(["M140 S70"])
    clock.advance(TAU_BED_S)

    state = printer.get_state()
    expected = 60.0 + (70.0 - 60.0) * (1.0 - math.exp(-1.0))
    assert abs(state.bed_actual_c - expected) < 0.5


def test_temperature_converges_to_target():
    clock = Clock()
    printer = FakePrinter(clock=clock)

    printer.send_gcode(["M104 S230"])
    clock.advance(20.0 * TAU_NOZZLE_S)

    assert abs(printer.get_state().nozzle_actual_c - 230.0) < 0.5


def test_m221_applies_flow_immediately():
    clock = Clock()
    printer = FakePrinter(clock=clock)

    assert printer.send_gcode(["M221 S110"]) is True

    state = printer.get_state()
    assert printer.flow_pct == 110
    assert state.flow_pct == 110
    assert state.last_change_ts["flow"] == 0.0


def test_m220_applies_speed_immediately():
    printer = FakePrinter()

    printer.send_gcode(["M220 S80"])

    state = printer.get_state()
    assert state.speed_pct == 80
    assert "speed" in state.last_change_ts


def test_two_variables_track_their_own_change_time():
    clock = Clock()
    printer = FakePrinter(clock=clock)

    printer.send_gcode(["M104 S215"])
    clock.advance(5.0)
    printer.send_gcode(["M221 S105"])

    state = printer.get_state()
    assert state.last_change_ts["nozzle_temp"] == 0.0
    assert state.last_change_ts["flow"] == 5.0


def test_m112_sets_error_and_blocks_further_sends():
    printer = FakePrinter()

    assert printer.estop() is True
    assert printer.state == "Error"
    assert printer.send_gcode(["M104 S220"]) is False
    assert [line for _, line in printer.sent] == ["M112"]


def test_send_records_every_line_with_its_time():
    clock = Clock()
    printer = FakePrinter(clock=clock)

    printer.send_gcode(["M104 S205", "M220 S80", "M221 S110"])

    assert [line for _, line in printer.sent] == [
        "M104 S205",
        "M220 S80",
        "M221 S110",
    ]
    assert {ts for ts, _ in printer.sent} == {0.0}


def test_pause_and_resume_state_machine():
    printer = FakePrinter()

    assert printer.pause() is True
    assert printer.state == "Paused"
    assert printer.get_state().state == "Paused"

    assert printer.resume() is True
    assert printer.state == "Printing"

    assert printer.resume() is False  # already printing
    assert printer.pause() is True
    assert printer.pause() is False  # already paused


def test_pause_fails_after_estop():
    printer = FakePrinter()
    printer.estop()

    assert printer.pause() is False
    assert printer.resume() is False


def test_disconnected_get_state_raises():
    printer = FakePrinter()
    printer.connected = False

    with pytest.raises(PrinterError):
        printer.get_state()


def test_disconnected_sends_fail_and_record_nothing():
    printer = FakePrinter()
    printer.connected = False

    assert printer.send_gcode(["M104 S220"]) is False
    assert printer.sent == []
    assert printer.pause() is False


def test_send_failure_leaves_state_and_log_untouched():
    printer = FakePrinter()
    printer.fail_next = 1

    assert printer.send_gcode(["M104 S220"]) is False
    assert printer.sent == []
    assert printer.nozzle_target_c == 210

    assert printer.send_gcode(["M104 S220"]) is True
    assert printer.nozzle_target_c == 220


def test_missing_s_value_is_ignored_but_recorded():
    printer = FakePrinter()

    assert printer.send_gcode(["M104"]) is True
    assert printer.nozzle_target_c == 210
    assert printer.sent == [(printer.sent[0][0], "M104")]


def test_nominal_is_configurable():
    printer = FakePrinter(nominal={"nozzle_temp": 195, "flow": 95})

    state = printer.get_state()
    assert state.nozzle_target_c == 195
    assert state.flow_pct == 95
    assert state.bed_target_c == 60
