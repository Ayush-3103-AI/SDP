"""Offline end-to-end HITL demo on held-out CAXTON prints (T-0066; 10-done §Five-minute demo).

    python scripts/run_demo.py plan [--crops data/crops.csv] [--splits data/splits/logo.json] [--seed 0] [--fps 2]
    python scripts/run_demo.py run --mode auto|advisory [--print pK] [--max-frames N]
    python scripts/run_demo.py report [--out reports/demo.md]
    python scripts/run_demo.py --selftest

plan: one held-out print from each of 3 different test folds, a seeded draw made before any run (runs/demo/plan.json),
and one config per print: config/caxton_demo.yaml with the camera on that print at --fps.
run: replays the planned prints through `xqi run` (FakePrinter seeded from the logged process); each run is appended
to runs/demo/runs.json. In advisory mode a person clicks the cards in `python -m xqi ui --run latest` meanwhile.
report: reports/demo.md with per-run verdict counts, warnings vs logged deviation onsets, and
  NFR-002 = p95 of t_gate − t0 (frame → verdict), NFR-003 = p95 of t_card − t_conf (event → card first shown, written
  by the dashboard), NFR-004 = every dispatched setpoint command re-checked against L1, the L2 step and cooldown, L3.
Times are the loop's monotonic clock (D6 definitions, proposed 2026-11-16).
"""
import argparse
import json
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from xqi import __main__ as cli
from xqi.config import load
from xqi.gate import l3_pass
from xqi.store import Store

DEMO = Path("runs/demo")
NFR_002_S, NFR_003_S = 0.30, 1.0
GCODE_VAR = {"M104": "nozzle_temp", "M140": "bed_temp", "M221": "flow", "M220": "speed"}
SETPOINT_SOURCES = ("auto", "operator")


def plan(crops_csv: str, splits: str, seed: int, fps: float, base: str, demo: Path) -> dict:
    crops = pd.read_csv(crops_csv)
    have = set(crops.trial_id)
    folds = json.loads(Path(splits).read_text(encoding="utf-8"))["folds"]
    rng = np.random.default_rng(seed)
    picks = []
    for k in sorted(rng.choice(len(folds), size=min(3, len(folds)), replace=False).tolist()):
        cands = sorted(t for t in folds[k]["test_trials"] if t in have)
        picks.append({"fold": k, "print": str(rng.choice(cands))})
    demo.mkdir(parents=True, exist_ok=True)
    data = yaml.safe_load(Path(base).read_text(encoding="utf-8"))
    for p in picks:
        data["camera"]["source"] = f"caxton:{crops_csv}#{p['print']}@{fps:g}"
        p["config"] = (demo / f"{p['print']}.yaml").as_posix()
        Path(p["config"]).write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    out = {"seed": seed, "fps": fps, "crops": crops_csv, "prints": picks}
    (demo / "plan.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def run(demo: Path, mode: str, only: str | None, max_frames: int | None) -> list[dict]:
    pl = json.loads((demo / "plan.json").read_text(encoding="utf-8"))
    log = demo / "runs.json"
    done = json.loads(log.read_text(encoding="utf-8")) if log.exists() else []
    for p in pl["prints"]:
        if only and p["print"] != only:
            continue
        run_dir = Path(load(p["config"]).run_dir)
        before = set(run_dir.glob("*/events.sqlite"))
        argv = ["run", "--config", p["config"], "--mode", mode]
        cli.main(argv + (["--max-frames", str(max_frames)] if max_frames else []))
        (db,) = set(run_dir.glob("*/events.sqlite")) - before
        done.append({"print": p["print"], "fold": p["fold"], "mode": mode, "db": db.as_posix()})
        log.write_text(json.dumps(done, indent=1), encoding="utf-8")
        print(f"{p['print']} {mode}: {db}", flush=True)
    return done


def onsets(crops: pd.DataFrame, trial: str) -> int:
    """Logged deviation onsets in the replayed rows: a change of the set of non-good variables to a non-empty set."""
    rows = crops[crops.trial_id == trial].sort_values("ts_s")
    bad = rows[["flow_cls", "speed_cls", "z_cls", "nozzle_cls"]].to_numpy() != 1
    keys = [tuple(b) for b in bad]
    return sum(1 for a, b in zip([(False,) * 4] + keys[:-1], keys, strict=True) if a != b and any(b))


def violations(rows: list[dict], cfg) -> list[str]:
    """Re-check each dispatched setpoint command (07 §3 invariant): L1 bounds, |Δ| ≤ step, L3, cooldown per var."""
    env, bad, last = cfg.envelope, [], {}
    for r in sorted(rows, key=lambda r: r["t_disp"]):
        for line in json.loads(r["gcode_json"]):
            m = re.fullmatch(r"(M10[4]|M140|M22[01])\s+S(-?[\d.]+)", line.strip())
            if not m:
                continue
            v, x2 = GCODE_VAR[m[1]], float(m[2])
            x = r["from_value"]
            lo, hi = getattr(env.L1, v)
            if not lo <= x2 <= hi:
                bad.append(f"{line}: outside L1 [{lo:g}, {hi:g}]")
            if x is not None and abs(x2 - x) > env.L2.step[v]:
                bad.append(f"{line}: step {x2 - x:+g} > {env.L2.step[v]:g} from {x:g}")
            if x is not None and not l3_pass(x, x2, env.L3.window[v]):
                bad.append(f"{line}: leaves L3 {env.L3.window[v]} from {x:g}")
            if v in last and r["t_disp"] - last[v] < env.L2.cooldown_s[v]:
                bad.append(f"{line}: {r['t_disp'] - last[v]:.1f} s after the last {v} change")
            last[v] = r["t_disp"]
    return bad


def p95(xs) -> float | None:
    return float(np.percentile(xs, 95)) if len(xs) else None


def _line(name, xs, limit) -> str:
    if not len(xs):
        return f"{name}: NO DATA (no events with both timestamps)"
    v = p95(xs)
    return f"{name}: {'PASS' if v <= limit else 'FAIL'} (p95 {1000 * v:.0f} ms ≤ {1000 * limit:.0f} ms, n={len(xs)})"


def report(demo: Path, out: Path) -> str:
    pl = json.loads((demo / "plan.json").read_text(encoding="utf-8"))
    runs = json.loads((demo / "runs.json").read_text(encoding="utf-8"))
    crops = pd.read_csv(pl["crops"])
    rows, e2v, e2c, bad = [], [], [], []
    for r in runs:
        cfg = load(next(p["config"] for p in pl["prints"] if p["print"] == r["print"]))
        s = Store.open_readonly(r["db"])
        try:
            ev = s.query("SELECT d.defect_id, d.cls, d.t0, d.t_conf, d.critical, v.verdict, v.t_gate, "
                         "(SELECT MIN(t) FROM timings t WHERE t.defect_id = d.defect_id AND t.stage = 't_card') AS t_card "
                         "FROM defects d LEFT JOIN verdicts v ON v.defect_id = d.defect_id")
            acts = s.query("SELECT a.source, a.gcode_json, a.t_disp, p.from_value FROM actions a "
                           "LEFT JOIN proposals p ON p.proposal_id = a.proposal_id WHERE a.ok = 1")
            n_dec = s.query("SELECT COUNT(*) AS n FROM operator_decisions")[0]["n"]
        finally:
            s.close()
        e2v += [e["t_gate"] - e["t0"] for e in ev if e["t_gate"] is not None and not e["critical"]]
        e2c += [e["t_card"] - e["t_conf"] for e in ev if e["t_card"] is not None]
        v = [f"{r['print']} {r['mode']}: {x}" for x in violations([a for a in acts if a["source"] in SETPOINT_SOURCES],
                                                                    cfg)]
        bad += v
        verdicts = Counter(e["verdict"] or "none" for e in ev)
        rows.append([r["print"], r["fold"], r["mode"], onsets(crops, r["print"]), len(ev),
                     ", ".join(f"{k} {n}" for k, n in sorted(verdicts.items())) or "-", n_dec, len(acts), len(v)])
    n_cmd = sum(r[7] for r in rows)
    lines = [
        _line("NFR-002", e2v, NFR_002_S) + " · frame → verdict (t_gate − t0)",
        _line("NFR-003", e2c, NFR_003_S) + " · event → card first shown (t_card − t_conf)",
        f"NFR-004: {'PASS' if not bad else 'FAIL'} ({len(bad)} violations in {n_cmd} dispatched commands)",
        "",
        "# Offline HITL demo on held-out CAXTON prints (T-0066)",
        "",
        f"Prints drawn before any run (seed {pl['seed']}, one per test fold): "
        + ", ".join(f"{p['print']} (fold {p['fold']})" for p in pl["prints"]) + f". Replay at {pl['fps']:g} fps, "
        "FakePrinter seeded from the logged process, no detector (early warnings raise the events).",
        "",
        "| print | fold | mode | logged onsets | events | verdicts | operator decisions | commands sent | violations |",
        "|---|---|---|---|---|---|---|---|---|",
        *("| " + " | ".join(str(x) for x in row) + " |" for row in rows),
        "",
        "Logged onsets = changes to a non-empty set of off-nominal variables in the replayed rows. Warnings are never",
        "auto-applied (07 §4 row 9), so auto runs dispatch nothing but critical actions; setpoint commands come from",
        "operator decisions in the advisory runs.",
    ]
    if bad:
        lines += ["", "## Violations", "", *(f"- {b}" for b in bad)]
    text = "\n".join(lines) + "\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print("\n".join(lines[:3]))
    print(f"wrote {out}")
    return text


def selftest() -> int:
    """Fixture crops + a random-weight checkpoint: plan → auto run → report, CPU, a few seconds."""
    import cv2
    import torch

    from xqi.explain.cause_model import build_model, save_checkpoint
    from xqi.explain.conformal import save_qhat
    from xqi.types import CAUSES

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        rows = []
        for p in range(3):
            for i in range(8):
                path = tmp / "crops" / f"p{p}" / f"{i}.jpg"
                path.parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(path), np.full((32, 32, 3), 30 * i, np.uint8))
                cls = (0, 1, 1, 1) if i >= 4 else (1, 1, 1, 1)
                rows.append((path.as_posix(), f"p{p}", 0.1 * i, *cls, 100.0, 100.0, 210.0))
        crops = tmp / "crops.csv"
        pd.DataFrame(rows, columns=["crop_path", "trial_id", "ts_s", "flow_cls", "speed_cls", "z_cls", "nozzle_cls",
                                    "flow_pct", "speed_pct", "nozzle_target_c"]).to_csv(crops, index=False)
        folds = [{"train_trials": [], "calib_trials": [], "test_trials": [f"p{k}"]} for k in range(3)]
        (tmp / "logo.json").write_text(json.dumps({"folds": folds}))
        model = build_model(len(CAUSES), 0, pretrained=False)
        with torch.no_grad():  # head pinned to flow_low, so the proactive path raises a warning event
            model.head.weight.zero_()
            model.head.bias.zero_()
            model.head.bias[CAUSES.index("flow_low")] = 10.0
        save_checkpoint(model, tmp / "final.pt")
        save_qhat(tmp / "qhat.json", 0.9, 0.1, 100)
        base = yaml.safe_load((ROOT / "config" / "caxton_demo.yaml").read_text(encoding="utf-8"))
        base.update(run_dir=str(tmp / "runs"), causes_file=str(ROOT / "config" / "causes.yaml"))
        base["cause_model"].update(weights=str(tmp / "final.pt"), device="cpu")
        base["conformal"]["qhat_file"] = str(tmp / "qhat.json")
        base["attribution"]["enabled"] = False
        (tmp / "base.yaml").write_text(yaml.safe_dump(base), encoding="utf-8")
        demo = tmp / "demo"
        plan(str(crops), str(tmp / "logo.json"), 0, 50, str(tmp / "base.yaml"), demo)
        run(demo, "auto", None, None)
        text = report(demo, tmp / "demo.md")
    # CPU timings say nothing about NFR-002; the selftest checks the events were timed and nothing broke the envelope
    ok = text.startswith("NFR-002: ") and "NO DATA" not in text.splitlines()[0] and "\nNFR-004: PASS" in text
    print("selftest ok" if ok else "selftest FAILED")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", choices=["plan", "run", "report"])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--crops", default="data/crops.csv")
    ap.add_argument("--splits", default="data/splits/logo.json")
    ap.add_argument("--config", default="config/caxton_demo.yaml", help="base config for plan")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--fps", type=float, default=2.0)
    ap.add_argument("--mode", choices=["auto", "advisory"], default="advisory")
    ap.add_argument("--print", dest="only", help="run one planned print only")
    ap.add_argument("--max-frames", type=int)
    ap.add_argument("--out", default="reports/demo.md")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.cmd == "plan":
        p = plan(a.crops, a.splits, a.seed, a.fps, a.config, DEMO)
        print("planned: " + ", ".join(f"{x['print']} (fold {x['fold']})" for x in p["prints"]))
    elif a.cmd == "run":
        run(DEMO, a.mode, a.only, a.max_frames)
    elif a.cmd == "report":
        report(DEMO, Path(a.out))
    else:
        ap.error("give plan, run, report or --selftest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
