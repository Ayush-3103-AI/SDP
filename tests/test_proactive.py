from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from xqi.config import ConfigError, load
from xqi.proactive import EarlyWarning
from xqi.types import CAUSES, CauseWarning

ROOT = Path(__file__).resolve().parents[1]
CFG = load(ROOT / "config" / "default.yaml").proactive


def probs(**high):
    """Cause probabilities: the named causes get their value, `none` takes the rest."""
    p = dict.fromkeys(CAUSES, 0.0)
    p.update(high)
    p["none"] = 1.0 - sum(high.values())
    return p


def run(ew, seq, t0=0.0, dt=0.4):
    return [w for i, p in enumerate(seq) for w in ew.update(t0 + i * dt, p)]


def test_default_proactive_config():
    assert (CFG.enabled, CFG.every_n, CFG.roi) == (True, 1, None)
    assert (CFG.beta, CFG.theta_on, CFG.theta_off, CFG.m) == (0.8, 0.60, 0.40, 3)
    assert (CFG.cooldown_s, CFG.max_gap_s) == (60, 10)


def test_steady_high_warns_once_after_m():
    ew = EarlyWarning(CAUSES, CFG)
    p = probs(flow_low=0.9)

    assert ew.update(0.0, p) == []
    assert ew.update(0.4, p) == []
    [w] = ew.update(0.8, p)
    assert isinstance(w, CauseWarning)
    assert (w.cause, w.ts, w.probs) == ("flow_low", 0.8, p)
    assert w.p == pytest.approx(0.9)
    assert run(ew, [p] * 500, t0=1.2) == []        # armed stays False while p̄ ≥ θ_off


def test_rearm_needs_drop_below_theta_off_and_cooldown():
    ew = EarlyWarning(CAUSES, CFG)
    hi, mid, lo = probs(flow_low=0.9), probs(flow_low=0.5), probs()

    assert len(run(ew, [hi] * 3)) == 1                       # warns at t=0.8
    assert run(ew, [mid] * 40 + [hi] * 40, t0=1.2) == []     # p̄ never < θ_off → not re-armed
    assert run(ew, [lo] * 10 + [hi] * 10, t0=33.2) == []     # re-armed, but within T_w of t=0.8
    [w] = run(ew, [lo] * 50 + [hi] * 10, t0=41.2)            # re-armed and cooled down
    assert w.cause == "flow_low"


def test_none_never_warns():
    ew = EarlyWarning(CAUSES, CFG)
    assert run(ew, [probs()] * 200) == []


def test_larger_pbar_wins():
    cfg = replace(CFG, theta_on=0.3, theta_off=0.2)
    p = probs(flow_low=0.35, speed_high=0.55)

    ws = run(EarlyWarning(CAUSES, cfg), [p] * 3)
    assert [w.cause for w in ws] == ["speed_high"]
    # flow_low qualified too and is still armed: it warns at the next evaluation
    ws = run(EarlyWarning(CAUSES, cfg), [p] * 4)
    assert [w.cause for w in ws] == ["speed_high", "flow_low"]


def test_gap_resets_pbar_and_runs():
    ew = EarlyWarning(CAUSES, CFG)
    hi = probs(flow_low=0.9)
    assert run(ew, [hi] * 2) == []
    assert run(ew, [hi] * 2, t0=20.0) == []      # gap 19.6 s > 10 s: run restarts at 1
    assert len(run(ew, [hi], t0=20.8)) == 1


def test_gap_resets_pbar_to_raw():
    ew = EarlyWarning(CAUSES, CFG)
    run(ew, [probs()] * 5)                        # p̄_flow_low = 0
    [w] = run(ew, [probs(flow_low=0.9)] * 3, t0=50.0)
    assert w.p == pytest.approx(0.9)


def test_beta_zero_is_raw_rule():
    ew = EarlyWarning(CAUSES, replace(CFG, beta=0.0))
    hi, lo = probs(flow_low=0.9), probs()
    seq = [hi, hi, lo, hi, hi, hi]
    ws = [(i, w) for i, p in enumerate(seq) for w in ew.update(i * 0.4, p)]
    assert [i for i, _ in ws] == [5]              # raw run reset by the one low frame
    assert ws[0][1].p == 0.9


def test_smoothing_delays_the_raw_rule():
    smooth = run(EarlyWarning(CAUSES, CFG), [probs()] + [probs(flow_low=0.9)] * 10)
    raw = run(EarlyWarning(CAUSES, replace(CFG, beta=0.0)), [probs()] + [probs(flow_low=0.9)] * 10)
    assert raw[0].ts < smooth[0].ts


def test_missing_cause_raises():
    p = probs()
    del p["flow_low"]
    with pytest.raises(KeyError):
        EarlyWarning(CAUSES, CFG).update(0.0, p)


def _cfg(tmp_path, **proactive):
    data = yaml.safe_load((ROOT / "config" / "default.yaml").read_text(encoding="utf-8"))
    data["proactive"].update(proactive)
    path = tmp_path / "c.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


@pytest.mark.parametrize("bad", [
    {"theta_off": 0.6}, {"theta_off": 0.7}, {"theta_on": 1.1}, {"theta_off": -0.1},
    {"beta": 1.0}, {"beta": -0.1}, {"m": 0}, {"every_n": 0},
])
def test_config_validation(tmp_path, bad):
    with pytest.raises(ConfigError, match=rf"proactive\.{next(iter(bad))}"):
        load(_cfg(tmp_path, **bad))


def test_roi_parsed(tmp_path):
    assert load(_cfg(tmp_path, roi=[1, 2, 30, 40])).proactive.roi == (1, 2, 30, 40)
    with pytest.raises(ConfigError, match=r"proactive\.roi"):
        load(_cfg(tmp_path, roi=[1, 2, 3]))
