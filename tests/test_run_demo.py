import pytest
from caxton_fixture import load_script

run_demo = load_script("run_demo")


@pytest.mark.slow
def test_selftest_plans_runs_and_reports():
    assert run_demo.selftest() == 0


def test_violations_flags_step_l1_and_cooldown():
    from xqi.config import load

    cfg = load("config/caxton_demo.yaml")
    rows = [{"gcode_json": '["M221 S105"]', "t_disp": 0.0, "from_value": 100.0},  # ok
            {"gcode_json": '["M221 S120"]', "t_disp": 5.0, "from_value": 105.0},  # step 15 > 10, 5 s < 20 s cooldown
            {"gcode_json": '["M104 S250"]', "t_disp": 100.0, "from_value": 248.0}]  # outside L1 [170, 240]
    bad = run_demo.violations(rows, cfg)
    assert any("step +15" in b for b in bad) and any("after the last flow" in b for b in bad)
    assert any("outside L1" in b for b in bad)
    assert run_demo.violations(rows[:1], cfg) == []
