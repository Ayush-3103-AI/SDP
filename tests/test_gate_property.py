"""NFR-004 offline: the 07 §3 safety invariant holds on every dispatched change (seed 0, no hypothesis)."""
import importlib.util
import math
import random
from collections import Counter
from pathlib import Path

import pytest

from xqi.config import load
from xqi.gate import GCODE, gate
from xqi.types import PrinterState, Proposal

ROOT = Path(__file__).resolve().parents[1]
CFG = load(ROOT / "config" / "default.yaml")
VARS = ("nozzle_temp", "bed_temp", "flow", "speed")
EPISODE = 10  # proposals per random start state


def _dist(y, lo, hi):
    return max(lo - y, 0.0, y - hi)


def _random_state(rng, now):
    """Integer setpoints (Marlin keeps targets and percentages as integers) in the L1 box ±20 %."""
    env = CFG.envelope
    x = {}
    for v in VARS:
        lo, hi = getattr(env.L1, v)
        pad = 0.2 * (hi - lo)
        x[v] = float(rng.randint(math.floor(lo - pad), math.ceil(hi + pad)))
    last = {v: now - rng.uniform(0, 2 * env.L2.cooldown_s[v]) for v in VARS if rng.random() < 0.7}
    return x, last


def _pstate(x, last, now):
    return PrinterState(
        ts=now, state="printing",
        nozzle_actual_c=x["nozzle_temp"], nozzle_target_c=x["nozzle_temp"],
        bed_actual_c=x["bed_temp"], bed_target_c=x["bed_temp"],
        flow_pct=x["flow"], speed_pct=x["speed"], progress_pct=50.0,
        last_change_ts=dict(last),
    )


def _violations(v, x, x2, now, prev):
    """07 §3 safety invariant, checked from config, independently of the gate's code."""
    env = CFG.envelope
    lo1, hi1 = getattr(env.L1, v)
    lo3, hi3 = env.L3.window[v]
    bad = []
    if abs(x2 - x) > env.L2.step[v]:
        bad.append("step")
    if not lo1 <= x2 <= hi1:
        bad.append("L1")
    if not (lo3 <= x2 <= hi3 or _dist(x2, lo3, hi3) < _dist(x, lo3, hi3)):
        bad.append("L3")
    if now - prev < env.L2.cooldown_s[v]:
        bad.append("cooldown")
    return bad


def run_property(n, seed=0):
    """Sequential dispatch of n random proposals; returns counts for the report."""
    rng = random.Random(seed)
    stats = Counter()
    now = 0.0
    for i in range(n):
        if i % EPISODE == 0:
            now += 1000.0
            x, last = _random_state(rng, now)
        now += rng.uniform(0, 30)
        v = rng.choice(VARS)
        delta = rng.uniform(-50, 50)
        p = Proposal(f"p{i}", "d", "prop", v, x[v], delta, x[v] + delta, (), "")
        d = gate(p, _pstate(x, last, now), now, CFG)
        stats["cases"] += 1
        if not d.passed:
            stats[f"blocked_{d.layers[-1].layer}"] += 1
            continue
        stats["dispatched"] += 1
        stats["clipped"] += d.clipped
        x2 = d.final_value
        for kind in _violations(v, x[v], x2, now, last.get(v, -math.inf)):
            stats[f"violation_{kind}"] += 1
            stats["violations"] += 1
        assert d.final_gcode == (f"{GCODE[v]} S{int(x2)}",)
        x[v], last[v] = x2, now
    return stats


def _report(stats, seed):
    rows = "\n".join(f"| {k} | {stats[k]} |" for k in sorted(stats))
    return (
        "# Gate property test (NFR-004, offline half)\n\n"
        f"Seed {seed}, {stats['cases']} random proposals, episodes of {EPISODE} with sequential dispatch.\n"
        "Start states: integer setpoints in the L1 box ±20 %, random last-change times; Δ ∈ [−50, 50].\n"
        "Out of scope: fractional setpoints. 210.5 + 5 rounds to M104 S216 (Δ 5.5 > step 5).\n\n"
        f"**Violations: {stats['violations']} / {stats['cases']}** "
        f"({stats['dispatched']} dispatched, {stats['clipped']} clipped).\n\n"
        "| count | value |\n|---|---|\n" + rows + "\n"
    )


def _check(stats, n):
    assert stats["cases"] == n
    assert stats["violations"] == 0, stats
    # Not vacuous: every layer both passes and blocks something.
    assert stats["dispatched"] > n // 10 and stats["clipped"] > 0
    assert all(stats[f"blocked_{layer}"] > 0 for layer in ("L1", "L2", "L3")), stats


def test_gate_property_1000():
    _check(run_property(1000), 1000)


def test_violation_checker_catches_a_bad_change():
    assert _violations("nozzle_temp", 210, 216, 100.0, 0.0) == ["step"]
    assert _violations("nozzle_temp", 238, 241, 100.0, 0.0) == ["L1", "L3"]
    assert _violations("nozzle_temp", 225, 228, 100.0, 0.0) == ["L3"]
    assert _violations("nozzle_temp", 230, 228, 100.0, 0.0) == []
    assert _violations("nozzle_temp", 210, 212, 100.0, 60.0) == ["cooldown"]


@pytest.mark.slow
def test_gate_property_100000():
    stats = run_property(100_000)
    out = ROOT / "reports" / "gate_property.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(_report(stats, 0), encoding="utf-8")
    _check(stats, 100_000)


def _audit():
    spec = importlib.util.spec_from_file_location("gate_audit", ROOT / "scripts" / "gate_audit.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_recipe_audit_rows():
    rows = {(r["recipe"], r["var"]): r for r in _audit().audit(CFG)}

    assert len(rows) == 10
    r = rows[("over_extrusion", "nozzle_temp")]
    assert (r["delta"], r["final"], r["layer"]) == (-20, 205, "L2")
    assert r["raw_breaks"] == "step, L3"
    r = rows[("under_extrusion", "nozzle_temp")]
    assert (r["delta"], r["final"], r["layer"], r["raw_breaks"]) == (-5, 205, "", "")
