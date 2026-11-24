"""Replay trace for the "Replay" section of docs/sdp-showcase.html.

    uv run python docs/showcase_replay.py [--preds models/cause] [--fold 0] [--hit p156] [--miss p172]
        [--config config/default.yaml] [--label "..."] [--html docs/sdp-showcase.html]

Walks the held-out frames of two test prints (one hit, one miss) in ts order and pushes every frame through the
project's own code, the way xqi/orchestrator.py's proactive path does:
  - probabilities: the saved per-frame probs_test of preds_fold<k>.npz (no model is run here);
  - conformal: xqi.explain.conformal.calibrate on the fold's calibration probs, then the Explainer's set;
  - early warning: xqi.proactive.EarlyWarning with cfg.proactive;
  - on a warning: Explainer.explain_estimate (set, sensor flags, counterfactual proposals) with a
    FakePrinter's PrinterState history, then xqi.gate.gate per proposal and xqi.gate.event_verdict.
The FakePrinter stays at cfg.printer.nominal: CAXTON's logged setpoint values (crops.csv) are not on the dev machine,
so set_process seeding is skipped and the trace says so. EigenCAM needs final.pt and is not run.

Without --hit/--miss the prints are picked by rule: hit = most warnings whose cause is in the frame's true deviation
set and has a G-code action; miss = most warnings whose cause is NOT in the true deviation set, with no correct one.
Re-run after the GPU sitting with --preds pointing at the new preds_fold*.npz and a new --label.

Writes docs/showcase-replay.json, slices reports/img/crop_sheet.jpg into docs/showcase-assets/, and replaces the
text between the REPLAY:BEGIN / REPLAY:END markers in --html.
"""

import argparse
import json
import re
import sys
import uuid
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from xqi.config import load
from xqi.explain import Explainer
from xqi.explain.conformal import calibrate
from xqi.gate import _l4_fail, event_verdict, gate
from xqi.orchestrator import HISTORY_LEN
from xqi.printer import FakePrinter
from xqi.proactive import EarlyWarning
from xqi.types import CAUSE_ACTION, EARLY_WARNING, MANUAL_ADVICE, CauseEstimate, ConfirmedDefect

CLS_CAUSE = ("flow", "speed", "z_offset", "nozzle_temp")  # test_cls column order (train_cause.CLS_COLS)
SHEET = ROOT / "reports/img/crop_sheet.jpg"
SHEET_LABEL_W, SHEET_TILE = 190, 140  # crop_sheet.jpg: label column, then 8 tiles of 140 px per cause row


def deviations(row) -> list[str]:
    return [f"{c}_{'low' if k == 0 else 'high'}" for c, k in zip(CLS_CAUSE, row) if k != 1]


def print_frames(npz, trial):
    m = npz["test_trial"] == trial
    o = np.argsort(npz["test_ts"][m], kind="stable")
    return (npz["test_ts"][m][o], npz["probs_test"][m][o], npz["y_test"][m][o], npz["test_cls"][m][o])


def warnings_of(npz, trial, labels, pcfg):
    ts, P, _, C = print_frames(npz, trial)
    ew, out = EarlyWarning(labels, pcfg), []
    for t, p, row in zip(ts, P, C):
        for w in ew.update(float(t), dict(zip(labels, p))):
            out.append((w.cause, w.cause in deviations(row)))
    return out


def pick(npz, labels, pcfg):
    """(hit, miss) by the rule in the module docstring; ties go to the print with more frames."""
    scored = []
    for t in sorted(set(npz["test_trial"])):
        ws = warnings_of(npz, t, labels, pcfg)
        good_act = sum(ok and CAUSE_ACTION.get(c) is not None for c, ok in ws)
        good, bad = sum(ok for _, ok in ws), sum(not ok for _, ok in ws)
        scored.append((t, good_act, good, bad, int((npz["test_trial"] == t).sum())))
    hit = max(scored, key=lambda s: (s[1], s[2] - s[3], s[4]))[0]
    miss = max((s for s in scored if s[2] == 0 and s[0] != hit), key=lambda s: (s[3], s[4]))[0]
    return hit, miss


def replay(npz, trial, labels, qhat, cfg, max_frames):
    """One print through EarlyWarning → Explainer.explain_estimate → gate → event_verdict (orchestrator P1/P3)."""
    ts, P, Y, C = print_frames(npz, trial)
    now = {"t": float(ts[0])}
    printer = FakePrinter(clock=lambda: now["t"], nozzle_c=cfg.printer.nominal["nozzle_temp"],
                          bed_c=cfg.printer.nominal["bed_temp"])
    explainer = Explainer(None, qhat, labels, cfg)  # cause_model unused: explain_estimate takes saved probs
    ew = EarlyWarning(labels, cfg.proactive)
    history, frames, events = [], [], []
    keep = set(np.linspace(0, len(ts) - 1, min(len(ts), max_frames)).round().astype(int).tolist())
    for i, (t, p, y, row) in enumerate(zip(ts, P, Y, C)):
        now["t"] = float(t)
        history = (history + [printer.get_state()])[-HISTORY_LEN:]
        probs = {c: float(v) for c, v in zip(labels, p)}
        prev_ts = ew.last_ts
        warns = ew.update(float(t), probs)
        reset = prev_ts is not None and float(t) - prev_ts > cfg.proactive.max_gap_s
        est = CauseEstimate(probs=probs, top=max(probs, key=probs.get), p_top=max(probs.values()))
        cd = ConfirmedDefect("frame", EARLY_WARNING, i, float(t), float(t), 0.0, (), 0.0, 0, 0.0, False)
        _, cset, _, _ = explainer.explain_estimate(cd, est, [])  # the set alone; shown for every frame
        ev_ids = []
        for w in warns:
            # orchestrator._proactive: no box, severity = p̄ (07 §1)
            cd = ConfirmedDefect(str(uuid.uuid4())[:8], EARLY_WARNING, i, w.ts, w.ts, w.p, (), 0.0, 0, w.p, False)
            est_w, cset_w, flags, props = explainer.explain_estimate(cd, est, history)
            state = history[-1]
            decisions = [gate(pr, state, float(t), cfg) for pr in props]
            v = event_verdict(cfg.mode, cd, cset_w, est_w, flags, decisions, state, cfg)
            events.append({
                "i": i, "ts": round(float(t), 2), "cause": w.cause, "pbar": round(w.p, 3),
                "correct": w.cause in deviations(row), "set": list(cset_w.members), "flags": list(flags),
                "proposals": [{
                    "cause": pr.cause, "var": pr.var, "from": pr.from_value, "delta": round(pr.delta, 2),
                    "to": round(pr.to_value, 2), "gcode": list(pr.gcode), "sentence": pr.counterfactual,
                    "passed": g.passed, "final_gcode": list(g.final_gcode),
                    "layers": [{"layer": lr.layer, "passed": lr.passed, "why": lr.reason} for lr in g.layers],
                } for pr, g in zip(props, decisions, strict=True)],
                "manual": {c: MANUAL_ADVICE[c] for c in cset_w.members if c in MANUAL_ADVICE},
                "l4": _l4_fail(cset_w, est_w, flags, cfg) or "pass",  # shown only; row 9 never applies a warning
                "verdict": v.verdict, "reason": v.reason,
            })
            ev_ids.append(len(events) - 1)
        if i in keep or ev_ids:
            frames.append({
                "i": i, "ts": round(float(t), 2), "y": int(y), "dev": deviations(row),
                "p": [round(float(x), 3) for x in p], "set": [labels.index(c) for c in cset.members],
                "pbar": [round(ew.pbar[c], 3) for c in ew.causes], "reset": reset, "ev": ev_ids,
            })
    yv = Y[Y >= 0]
    top1 = float((P.argmax(1)[Y >= 0] == yv).mean()) if len(yv) else None
    return {"trial": trial, "n_frames": int(len(ts)), "top1": None if top1 is None else round(top1, 3),
            "single": int(len(yv)), "frames": frames, "events": events}


def slice_sheet(out_dir: Path, labels) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    im, paths = Image.open(SHEET).convert("RGB"), {}
    for r, c in enumerate(labels):
        tile = im.crop((SHEET_LABEL_W, r * SHEET_TILE, SHEET_LABEL_W + SHEET_TILE, (r + 1) * SHEET_TILE))
        tile.save(out_dir / f"cause_{c}.jpg", quality=86)
        paths[c] = f"{out_dir.name}/cause_{c}.jpg"
    return paths


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preds", default="models/cause", help="directory holding preds_fold<k>.npz")
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument("--hit", help="trial id of the hit print (default: picked by rule)")
    ap.add_argument("--miss", help="trial id of the miss print (default: picked by rule)")
    ap.add_argument("--config", default="config/default.yaml")
    ap.add_argument("--label", default="11-11 fine-tune, incomplete data, K2 FAIL; replay will be regenerated "
                                        "with final.pt")
    ap.add_argument("--max-frames", type=int, default=200, help="per print; warning frames are always kept")
    ap.add_argument("--json", default="docs/showcase-replay.json")
    ap.add_argument("--html", default="docs/sdp-showcase.html", help="'' to skip embedding")
    a = ap.parse_args(argv)

    cfg = load(ROOT / a.config)
    npz = dict(np.load(ROOT / a.preds / f"preds_fold{a.fold}.npz"))
    labels = [str(x) for x in npz["labels"]]
    cal = npz["y_calib"] >= 0
    qhat = calibrate(npz["probs_calib"][cal], npz["y_calib"][cal], cfg.conformal.alpha)
    auto_hit, auto_miss = pick(npz, labels, cfg.proactive) if not (a.hit and a.miss) else (None, None)
    hit, miss = a.hit or auto_hit, a.miss or auto_miss

    trace = {
        "label": a.label, "preds": f"{a.preds}/preds_fold{a.fold}.npz", "fold": a.fold, "config": a.config,
        "labels": labels, "qhat": round(qhat, 4), "alpha": cfg.conformal.alpha, "n_calib": int(cal.sum()),
        "proactive": {k: getattr(cfg.proactive, k) for k in ("beta", "theta_on", "theta_off", "m", "cooldown_s",
                                                              "max_gap_s")},
        "tau": cfg.envelope.L4.tau, "mode": cfg.mode,
        "hitl": {"timeout_s": cfg.hitl.timeout_s, "timeout_action": cfg.hitl.timeout_action},
        "nominal": dict(cfg.printer.nominal),
        "crops": slice_sheet(ROOT / "docs/showcase-assets", labels),
        "prints": {"hit": replay(npz, hit, labels, qhat, cfg, a.max_frames),
                   "miss": replay(npz, miss, labels, qhat, cfg, a.max_frames)},
    }
    text = json.dumps(trace, separators=(",", ":"), ensure_ascii=False)
    (ROOT / a.json).write_text(text, encoding="utf-8")
    print(f"qhat {qhat:.4f} (n={int(cal.sum())}), hit {hit}, miss {miss}, {len(text) / 1024:.0f} KB -> {a.json}")
    for k, pr in trace["prints"].items():
        print(f"  {k} {pr['trial']}: {pr['n_frames']} frames ({len(pr['frames'])} kept), top-1 {pr['top1']}, "
              + ", ".join(f"{e['cause']}@{e['ts']:g}s {e['verdict']}" for e in pr["events"]))
    if a.html:
        html_path = ROOT / a.html
        html = html_path.read_text(encoding="utf-8")
        new, n = re.subn(r"(/\* REPLAY:BEGIN \*/).*?(/\* REPLAY:END \*/)",
                         lambda m: f"{m.group(1)}{text}{m.group(2)}", html, flags=re.S)
        if n != 1:
            print(f"no REPLAY:BEGIN/END markers in {a.html}; JSON written only", file=sys.stderr)
            return 1
        html_path.write_text(new, encoding="utf-8")
        print(f"embedded in {a.html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
