from pathlib import Path

from xqi.config import load
from xqi.explain.sensors import check
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
# state availability
# --------------------------------------------------------------------------- #


def test_empty_history_reports_state_unavailable():
    assert check([], now=0.0, cfg=CFG) == ("state_unavailable",)


def test_healthy_window_has_no_flags():
    history = [make_state(ts=0.0), make_state(ts=1.0)]

    assert check(history, now=1.0, cfg=CFG) == ()


# --------------------------------------------------------------------------- #
# heater deviation
# --------------------------------------------------------------------------- #


def test_nozzle_deviation_longer_than_threshold_flags():
    # 216 vs 210 = 6 °C > 5 °C, held for 12 s > 10 s.
    history = [
        make_state(ts=0.0, nozzle_actual_c=216.0),
        make_state(ts=12.0, nozzle_actual_c=216.0),
    ]

    flags = check(history, now=12.0, cfg=CFG)

    assert "heater_deviation:nozzle" in flags


def test_nozzle_deviation_shorter_than_threshold_is_quiet():
    # Same 6 °C error but only 8 s of persistence.
    history = [
        make_state(ts=0.0, nozzle_actual_c=216.0),
        make_state(ts=8.0, nozzle_actual_c=216.0),
    ]

    flags = check(history, now=8.0, cfg=CFG)

    assert "heater_deviation:nozzle" not in flags


def test_deviation_exactly_at_duration_boundary_is_not_flagged():
    # now - start == 10 s, and the rule is strictly greater than.
    history = [
        make_state(ts=0.0, nozzle_actual_c=216.0),
        make_state(ts=10.0, nozzle_actual_c=216.0),
    ]

    flags = check(history, now=10.0, cfg=CFG)

    assert "heater_deviation:nozzle" not in flags


def test_deviation_exactly_at_magnitude_boundary_is_not_flagged():
    # |actual - target| == 5 °C is not "more than" 5 °C.
    history = [
        make_state(ts=0.0, nozzle_actual_c=215.0),
        make_state(ts=20.0, nozzle_actual_c=215.0),
    ]

    flags = check(history, now=20.0, cfg=CFG)

    assert "heater_deviation:nozzle" not in flags


def test_deviation_that_recovers_is_not_flagged():
    # Deviates at t=0, recovers at t=5, only evaluated at now=20.
    history = [
        make_state(ts=0.0, nozzle_actual_c=216.0),
        make_state(ts=5.0, nozzle_actual_c=210.0),
    ]

    flags = check(history, now=20.0, cfg=CFG)

    assert "heater_deviation:nozzle" not in flags


def test_bed_deviation_flags_independently():
    history = [
        make_state(ts=0.0, bed_actual_c=68.0),
        make_state(ts=15.0, bed_actual_c=68.0),
    ]

    flags = check(history, now=15.0, cfg=CFG)

    assert "heater_deviation:bed" in flags
    assert "heater_deviation:nozzle" not in flags


# --------------------------------------------------------------------------- #
# settling
# --------------------------------------------------------------------------- #


def test_settling_flag_when_target_changed_recently():
    history = [make_state(ts=0.0, last_change_ts={"nozzle_temp": 970.0})]

    flags = check(history, now=1000.0, cfg=CFG)  # 30 s ago < settle_s

    assert "settling:nozzle_temp" in flags


def test_settling_flag_clears_after_settle_time():
    history = [make_state(ts=0.0, last_change_ts={"nozzle_temp": 900.0})]

    flags = check(history, now=1000.0, cfg=CFG)  # 100 s ago > settle_s

    assert "settling:nozzle_temp" not in flags


def test_settling_boundary_is_exclusive():
    settle_s = CFG.sensors.settle_s["nozzle_temp"]
    history = [
        make_state(ts=0.0, last_change_ts={"nozzle_temp": 1000.0 - settle_s})
    ]

    flags = check(history, now=1000.0, cfg=CFG)

    assert "settling:nozzle_temp" not in flags


def test_nan_last_change_does_not_crash_or_flag_settling():
    history = [
        make_state(ts=0.0, last_change_ts={"nozzle_temp": float("nan")})
    ]

    flags = check(history, now=1000.0, cfg=CFG)

    assert "settling:nozzle_temp" not in flags


# --------------------------------------------------------------------------- #
# printer state
# --------------------------------------------------------------------------- #


def test_printer_not_printing_flags_when_paused():
    history = [make_state(ts=0.0, state="Paused")]

    flags = check(history, now=0.0, cfg=CFG)

    assert "printer_not_printing" in flags


def test_printer_state_is_compared_exactly():
    history = [make_state(ts=0.0, state="printing")]

    flags = check(history, now=0.0, cfg=CFG)

    assert "printer_not_printing" in flags


def test_flags_are_deterministic_and_ordered():
    history = [
        make_state(
            ts=0.0,
            nozzle_actual_c=216.0,
            state="Paused",
            last_change_ts={"nozzle_temp": 995.0},
        ),
        make_state(
            ts=12.0,
            nozzle_actual_c=216.0,
            state="Paused",
            last_change_ts={"nozzle_temp": 995.0},
        ),
    ]

    flags = check(history, now=12.0, cfg=CFG)

    assert flags == (
        "heater_deviation:nozzle",
        "settling:nozzle_temp",
        "printer_not_printing",
    )
