import math

import pytest

from xqi.printer import FakePrinter, Printer


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


def test_nozzle_follows_first_order_lag():
    clock = FakeClock()
    printer = FakePrinter(clock=clock)

    assert printer.get_state().nozzle_actual_c == 210.0
    assert printer.send_gcode(["M104 S220"])

    clock.t = 8.0
    state = printer.get_state()

    assert state.nozzle_target_c == 220.0
    assert state.nozzle_actual_c == pytest.approx(
        210 + 10 * (1 - math.exp(-1)), abs=0.5
    )
    assert state.last_change_ts["nozzle_temp"] == 0.0


def test_bed_lag_uses_its_own_tau():
    clock = FakeClock()
    printer = FakePrinter(clock=clock)

    printer.send_gcode(["M140 S70"])
    clock.t = 60.0

    assert printer.get_state().bed_actual_c == pytest.approx(
        60 + 10 * (1 - math.exp(-1)), abs=0.5
    )


def test_flow_and_speed_change_immediately():
    clock = FakeClock()
    printer = FakePrinter(clock=clock)
    clock.t = 3.0

    assert printer.send_gcode(["M221 S110", "M220 S90"])
    state = printer.get_state()

    assert state.flow_pct == 110.0
    assert state.speed_pct == 90.0
    assert state.last_change_ts["flow"] == 3.0
    assert state.last_change_ts["speed"] == 3.0
    assert printer.sent == [(3.0, "M221 S110"), (3.0, "M220 S90")]


def test_pause_resume_and_estop():
    printer = FakePrinter(clock=FakeClock())
    assert isinstance(printer, Printer)

    assert printer.get_state().state == "Printing"
    assert printer.pause()
    assert printer.get_state().state == "Paused"
    assert printer.resume()
    assert printer.get_state().state == "Printing"

    assert printer.send_gcode(["M112"])
    assert printer.get_state().state == "Error"
    assert not printer.send_gcode(["M221 S110"])
    assert not printer.resume()
    assert printer.get_state().flow_pct == 100.0
