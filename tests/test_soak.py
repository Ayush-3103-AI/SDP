"""NFR-008 soak: 2 simulated hours of replay + FakePrinter in auto mode, with a random operator."""

import itertools
import json
import random
import threading
from dataclasses import asdict, replace
from pathlib import Path

import cv2
import numpy as np
import psutil  # ponytail: arrives with ultralytics; declare it in pyproject's dev group on the next uv lock
import pytest

from xqi.camera import open_source
from xqi.config import load
from xqi.explain.counterfactual import make_proposal
from xqi.orchestrator import Orchestrator
from xqi.printer import FakePrinter
from xqi.store import Store
from xqi.types import (
    CAUSE_DEFECTS,
    DEFECTS,
    CauseEstimate,
    CauseSet,
    Frame,
    OperatorDecision,
)

ROOT = Path(__file__).resolve().parents[1]
CFG = load(ROOT / "config" / "default.yaml")
CFG = replace(CFG, proactive=replace(CFG.proactive, enabled=False))  # RandomExplainer has no estimate()
FPS = 10
N_REPLAY = 200
RSS_EVERY = 1000  # frames
MAX_RSS_GROWTH = 200 * 2**20  # NFR-008
# Criticals latch the FakePrinter in Error (M112), which would turn the rest of the soak into dispatch failures.
NON_CRITICAL = [c for c in DEFECTS if c not in asdict(CFG.critical)]


class RandomExplainer:
    """Seeded random cause set for the class: 1–2 actionable causes, sometimes none or misalignment."""

    def __init__(self, seed=0):
        self.rng = random.Random(seed)

    def explain(self, cd, frame, history):
        roll = self.rng.random()
        if roll < 0.1:
            members = ("misalignment",)  # ESCALATE
        elif roll < 0.2:
            members = ("none",)  # NOOP
        else:
            options = [c for c, defects in CAUSE_DEFECTS.items() if cd.cls in defects]
            members = tuple(self.rng.sample(options, min(len(options), self.rng.randint(1, 2))))
        p_top = self.rng.uniform(0.4, 0.95)  # below L4 tau → PROPOSE
        probs = {c: p_top / len(members) for c in members}
        props = [make_proposal(c, probs[c], cd.severity, history[-1], CFG, cd.defect_id) for c in members]
        est = CauseEstimate(probs, members[0], p_top)
        return est, CauseSet(members, 0.1, 0.5), (), [p for p in props if p]


def _operator(path, clock, quiet_ts, done, errors):
    """The UI's part: answer about half the cards at random via insert_decision; the rest time out."""
    rng, seen = random.Random(1), set()
    ui = Store.open_readonly(path)
    try:
        while clock() < quiet_ts and not done.is_set():
            for event in ui.pending_events():
                if event["defect_id"] in seen:
                    continue
                seen.add(event["defect_id"])
                if rng.random() < 0.5:
                    continue
                ids = json.loads(event["proposal_ids_json"])
                # No "stop": M112 latches the FakePrinter in Error for the rest of the run.
                choice = rng.choice(["apply", "modify", "reject", "pause"] if ids else ["reject", "pause"])
                delta = rng.uniform(-10, 10) if choice == "modify" else None
                ui.insert_decision(OperatorDecision(rng.choice(ids) if ids else None, event["defect_id"],
                                                    choice, delta, "soak", "", 1.0))
            done.wait(0.005)
    except Exception as exc:  # a dead thread would just stop deciding; the assert below surfaces it
        errors.append(exc)
        raise
    finally:
        ui.close()


def _soak(tmp_path, clock, stub_detector, sim_s, cfg=CFG, n_replay=N_REPLAY):
    folder = tmp_path / "frames_in"
    folder.mkdir()
    noise = np.random.default_rng(0)
    for i in range(n_replay):
        assert cv2.imwrite(str(folder / f"{i:03d}.png"), noise.integers(0, 256, (48, 64, 3), np.uint8))
    proc, rss = psutil.Process(), []

    def frames():  # loop the replay folder, restamped on the fast clock: frames are not slept
        ids = itertools.count()
        while True:
            for f in open_source(f"replay:{folder}", 0, 0):
                i = next(ids)
                if i % RSS_EVERY == 0:
                    rss.append(proc.memory_info().rss)
                yield Frame(i, clock.tick(1 / FPS), f.wall_iso, f.image)

    quiet_ts = clock() + sim_s - cfg.hitl.timeout_s - 10  # silent tail: every open card times out
    printer = FakePrinter(clock=clock)
    store = Store(tmp_path / "run" / "events.sqlite")
    detector = stub_detector(NON_CRITICAL, seed=0, stop_ts=quiet_ts)
    orch = Orchestrator(replace(cfg, mode="auto"), printer, frames(), detector, RandomExplainer(), store,
                        clock=clock)
    done, errors = threading.Event(), []
    operator = threading.Thread(target=_operator, args=(store.path, clock, quiet_ts, done, errors), daemon=True)
    operator.start()
    try:
        orch.run(int(sim_s * FPS))  # no exception
    finally:
        done.set()
        operator.join()
    rss.append(proc.memory_info().rss)

    assert errors == []
    assert max(rss) - rss[0] < MAX_RSS_GROWTH, f"RSS grew {(max(rss) - rss[0]) / 2**20:.0f} MB"
    db = Store.open_readonly(store.path)
    assert db.pending_events() == [] and db.new_decisions() == []  # all resolved or timed out
    return db


def _count(db, sql):
    return {r["k"]: r["n"] for r in db.query(sql)}


def test_soak_smoke(tmp_path, fast_clock, stub_detector):
    # The whole harness in seconds: 40 simulated s, a 10 s card timeout, a 20-frame folder
    # (a freshly written PNG costs ~17 ms to read on Windows).
    cfg = replace(CFG, hitl=replace(CFG.hitl, timeout_s=10))
    db = _soak(tmp_path, fast_clock, stub_detector, sim_s=40, cfg=cfg, n_replay=20)

    assert db.query("SELECT COUNT(*) AS n FROM defects")[0]["n"] > 0
    assert db.query("SELECT ended_iso FROM runs")[0]["ended_iso"]


@pytest.mark.slow
def test_soak_2h(tmp_path, fast_clock, stub_detector):
    db = _soak(tmp_path, fast_clock, stub_detector, sim_s=2 * 3600)

    verdicts = _count(db, "SELECT verdict AS k, COUNT(*) AS n FROM verdicts GROUP BY verdict")
    choices = _count(db, "SELECT choice AS k, COUNT(*) AS n FROM operator_decisions GROUP BY choice")
    print(f"verdicts {verdicts}  decisions {choices}")
    assert {"APPLY", "PROPOSE", "ESCALATE"} <= set(verdicts)  # every auto-mode path exercised
    assert "timeout" in choices and {"apply", "modify", "reject"} & set(choices)
