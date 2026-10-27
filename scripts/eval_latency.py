"""Per-stage latency from run stores, plus the GPU action-path and VRAM bench (T-0036, 07 §7).

    python scripts/eval_latency.py --runs runs/<id>/events.sqlite ... --out reports/latency.md
    python scripts/eval_latency.py --runs ... --bench --out reports/latency.md   # GPU laptop
    python scripts/eval_latency.py --selftest
"""
import argparse
import sys
import tempfile
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from xqi.config import load, load_causes
from xqi.explain import Explainer
from xqi.gate import event_verdict, gate
from xqi.store import Store
from xqi.types import (
    DEFECTS,
    CauseEstimate,
    CauseSet,
    ConfirmedDefect,
    EventVerdict,
    Frame,
    PrinterState,
)

NFR_001_P95_S = 0.030  # added action path (crop + cause model + conformal + gate)
NFR_002_P95_S = 0.30  # first defect frame -> dispatch, auto mode
NFR_002_CRIT_P95_S = 0.27  # same, critical classes
NFR_011_GB = 3.5  # YOLO11-S + cause model at inference
BENCH_N = 500

# One row per defect; actions only count once OctoPrint returned 2xx (07 §7 t_disp).
SQL = """
SELECT d.critical, d.t0, d.t_conf, e.t_cause, v.verdict, v.t_gate,
  (SELECT MIN(t_disp) FROM actions a WHERE a.defect_id = d.defect_id AND a.ok = 1 AND a.source = 'auto') AS t_auto,
  (SELECT MIN(t_disp) FROM actions a WHERE a.defect_id = d.defect_id AND a.ok = 1 AND a.source = 'critical')
    AS t_crit
FROM defects d
LEFT JOIN explanations e ON e.defect_id = d.defect_id
LEFT JOIN verdicts v ON v.defect_id = d.defect_id
"""

STAGES = (
    ("confirm_to_cause", "confirm → cause (t_cause − t_conf)"),
    ("cause_to_gate", "cause → gate (t_gate − t_cause)"),
    ("added", "added action path (t_gate − t_conf), NFR-001"),
    ("gate_to_dispatch", "gate → dispatch, auto (t_disp − t_gate)"),
    ("end_to_end", "end-to-end, auto (t_disp − t0), NFR-002"),
    ("critical_end_to_end", "critical end-to-end (t_disp − t0), NFR-002"),
)


def stages(db_paths) -> dict[str, list[float]]:
    """Seconds per stage across all runs. Critical and baseline events have t_gate = t_disp and
    explain after dispatching, so only gated events feed the cause/gate stages."""
    out = {k: [] for k, _ in STAGES}
    for path in db_paths:
        store = Store.open_readonly(path)
        try:
            rows = store.query(SQL)
        finally:
            store.close()
        for r in rows:
            if r["critical"]:
                if r["t_crit"] is not None:
                    out["critical_end_to_end"].append(r["t_crit"] - r["t0"])
                continue
            gated = r["t_gate"] is not None and r["verdict"] not in ("CRITICAL", "APPLY_RAW")
            if r["t_cause"] is not None:
                out["confirm_to_cause"].append(r["t_cause"] - r["t_conf"])
                if gated:
                    out["cause_to_gate"].append(r["t_gate"] - r["t_cause"])
            if gated:
                out["added"].append(r["t_gate"] - r["t_conf"])
                if r["t_auto"] is not None:
                    out["gate_to_dispatch"].append(r["t_auto"] - r["t_gate"])
            if r["t_auto"] is not None:
                out["end_to_end"].append(r["t_auto"] - r["t0"])
    return out


def summarise(times: dict[str, list[float]]) -> dict[str, dict]:
    """{stage: {n, p50, p95, max}} in seconds; numpy's default (linear) percentiles."""
    out = {}
    for k, xs in times.items():
        a = np.asarray(xs, dtype=float)
        out[k] = {"n": len(a)} | (
            {"p50": float(np.percentile(a, 50)), "p95": float(np.percentile(a, 95)), "max": float(a.max())}
            if len(a) else {}
        )
    return out


def bench_added(explainer, cfg, n=BENCH_N, warmup=20, seed=0) -> tuple[list[float], set[str]]:
    """Time crop + cause model + conformal + sensors + proposals + gate + verdict on n random boxes.

    Random pixels are timing-equivalent: the cost does not depend on what the crop shows.
    """
    rng = np.random.default_rng(seed)
    w, h = cfg.camera.width, cfg.camera.height
    frame = Frame(0, 0.0, "", rng.integers(0, 256, (h, w, 3), dtype=np.uint8))
    nom = cfg.printer.nominal
    state = PrinterState(
        0.0, "Printing", nom["nozzle_temp"], nom["nozzle_temp"], nom["bed_temp"], nom["bed_temp"],
        nom["flow"], nom["speed"], None, {},
    )
    critical = asdict(cfg.critical)
    classes = [d for d in DEFECTS if d not in critical]
    times, verdicts = [], set()
    for i in range(warmup + n):
        bw, bh = rng.uniform(64, 480, size=2)
        x1, y1 = rng.uniform(0, w - bw), rng.uniform(0, h - bh)
        box = (x1, y1, x1 + bw, y1 + bh)
        cd = ConfirmedDefect(f"bench-{i}", classes[i % len(classes)], i, 0.0, 0.0, 0.9, box, bw * bh / (w * h), 3, 0.5, False)
        t = time.perf_counter()
        est, cset, flags, props = explainer.explain(cd, frame, [state])
        decisions = [gate(p, state, 0.0, cfg) for p in props]
        v = event_verdict("auto", cd, cset, est, flags, decisions, state, cfg)
        dt = time.perf_counter() - t
        if i >= warmup:
            times.append(dt)
            verdicts.add(v.verdict)
    return times, verdicts


def run_bench(cfg) -> dict:
    """GPU laptop only: YOLO loaded and run once, then the action-path bench, then peak VRAM."""
    import torch

    from xqi.detect import Detector
    from xqi.explain.cause_model import CauseModel, build_model, save_checkpoint
    from xqi.explain.conformal import load_qhat

    if not torch.cuda.is_available():
        raise SystemExit("--bench needs CUDA (run it on the GPU laptop)")
    torch.cuda.reset_peak_memory_stats()
    d = cfg.detector
    detector = Detector(d.weights, d.imgsz, d.conf, d.device)
    frame = Frame(0, 0.0, "", np.zeros((cfg.camera.height, cfg.camera.width, 3), np.uint8))
    detector(frame)
    causes = load_causes(cfg.causes_file).causes
    weights, note = Path(cfg.cause_model.weights), ""
    if not weights.exists():  # latency does not depend on the trained weights; say so in the report
        weights = Path(tempfile.mkdtemp()) / "random.pt"
        n_defects = len(DEFECTS) if cfg.cause_model.use_defect else 0
        save_checkpoint(build_model(len(causes), n_defects, pretrained=False), weights)
        note = f"{cfg.cause_model.weights} missing, random-init cause model (same timing)"
    cm = CauseModel(weights, causes, DEFECTS, cfg.cause_model.device, cfg.cause_model.input_px,
                    cfg.cause_model.use_defect)
    qfile = Path(cfg.conformal.qhat_file)
    qhat = load_qhat(qfile)["qhat"] if qfile.exists() else 1 - cfg.conformal.alpha
    if not qfile.exists():
        note = "; ".join(filter(None, [note, f"{qfile} missing, qhat = 1 − α"]))
    times, verdicts = bench_added(Explainer(cm, qhat, causes, cfg), cfg)
    for _ in range(5):  # YOLO and the cause model both resident, as in the loop
        detector(frame)
    torch.cuda.synchronize()
    return {
        "gpu": torch.cuda.get_device_name(0),
        "times": times,
        "verdicts": sorted(verdicts),
        "max_allocated_gb": torch.cuda.max_memory_allocated() / 1e9,
        "max_reserved_gb": torch.cuda.max_memory_reserved() / 1e9,
        "note": note,
    }


def _ms(s: dict, k: str) -> str:
    return f"{s[k] * 1000:.1f}" if k in s else "–"


def _verdict(s: dict, limit: float) -> str:
    if not s.get("n"):
        return "NO DATA"
    return "PASS" if s["p95"] <= limit else "FAIL"


def render(stats: dict, bench: dict | None, runs) -> str:
    lines = [
        "# Latency and VRAM report (T-0036)",
        "",
        f"Runs: {', '.join(str(r) for r in runs) or 'none'}",
        "",
        "## Run stores (07 §7, monotonic clock)",
        "",
        "| stage | n | p50 ms | p95 ms | max ms |",
        "|---|---|---|---|---|",
    ]
    for k, label in STAGES:
        s = stats.get(k, {"n": 0})
        lines.append(f"| {label} | {s['n']} | {_ms(s, 'p50')} | {_ms(s, 'p95')} | {_ms(s, 'max')} |")

    if bench:
        b = summarise({"bench": bench["times"]})["bench"]
        lines += [
            "",
            f"## Bench: {b['n']} crops through cause model + conformal + gate on {bench['gpu']}",
            "",
            (
                f"p50 {_ms(b, 'p50')} ms · p95 {_ms(b, 'p95')} ms · max {_ms(b, 'max')} ms · "
                f"verdicts seen: {', '.join(bench['verdicts'])}"
            ),
            "",
            (
                f"torch.cuda.max_memory_allocated with YOLO loaded: {bench['max_allocated_gb']:.2f} GB "
                f"(reserved {bench['max_reserved_gb']:.2f} GB)"
            ),
        ]
        if bench["note"]:
            lines += ["", f"Note: {bench['note']}"]
        nfr1 = f"{_verdict(b, NFR_001_P95_S)} (bench p95 {_ms(b, 'p95')} ms ≤ 30 ms on {bench['gpu']})"
        ok = bench["max_allocated_gb"] <= NFR_011_GB
        nfr11 = f"{'PASS' if ok else 'FAIL'} ({bench['max_allocated_gb']:.2f} GB ≤ 3.5 GB on {bench['gpu']})"
    else:
        nfr1 = "NO DATA (run --bench on the RTX 3050)"
        nfr11 = "NO DATA (run --bench on the RTX 3050)"

    e2e = stats.get("end_to_end", {"n": 0})
    crit = stats.get("critical_end_to_end", {"n": 0})
    parts = [_verdict(e2e, NFR_002_P95_S), _verdict(crit, NFR_002_CRIT_P95_S)]
    if "FAIL" in parts:
        nfr2 = "FAIL"
    elif "PASS" in parts:
        nfr2 = "PASS" if "NO DATA" not in parts else "PASS (partial)"
    else:
        nfr2 = "NO DATA"
    lines += [
        "",
        "## Requirements",
        "",
        f"- NFR-001: {nfr1}",
        (
            f"- NFR-002: {nfr2} (auto p95 {_ms(e2e, 'p95')} ms ≤ 300 ms, n={e2e['n']}: {parts[0]}; "
            f"critical p95 {_ms(crit, 'p95')} ms ≤ 270 ms, n={crit['n']}: {parts[1]})"
        ),
        f"- NFR-011: {nfr11}",
        "",
    ]
    return "\n".join(lines)


def _defect(defect_id, cls, t0, t_conf, critical) -> ConfirmedDefect:
    return ConfirmedDefect(defect_id, cls, 0, t0, t_conf, 0.9, (0, 0, 1, 1), 0.01, 3, 0.5, critical)


def selftest() -> int:
    """Synthetic store with known gaps → known percentiles. Returns 0 on success."""
    with tempfile.TemporaryDirectory() as tmp:
        store = Store(Path(tmp) / "run" / "events.sqlite")
        est, cset = CauseEstimate({"flow_high": 1.0}, "flow_high", 1.0), CauseSet(("flow_high",), 0.1, 0.5)
        for i in range(1, 101):  # added = i ms, auto end-to-end = 100 + i ms
            dt, cd = i / 1000, _defect(f"d{i}", "stringing", 10.0, 10.05, False)
            store.write_defect(cd)
            store.write_explanation(cd.defect_id, est, cset, 0.5, (), 10.05)
            store.write_verdict(EventVerdict(cd.defect_id, "APPLY", "L4: pass", ()), t_gate=10.05 + dt)
            store.write_action(f"a{i}", cd.defect_id, None, "auto", [], 10.1 + dt, True)
        # A critical event, and an auto dispatch that failed (must not count).
        store.write_defect(_defect("c", "spaghetti", 20.0, 20.1, True))
        store.write_action("ac", "c", None, "critical", ["M112"], 20.2, True)
        store.write_action("bad", "d1", None, "auto", [], 9.0, False)
        store.close()
        stats = summarise(stages([store.path]))
    expect = {  # numpy linear percentiles of 1..100 ms: p50 50.5, p95 95.05
        "added": (100, 0.0505, 0.09505, 0.100),
        "confirm_to_cause": (100, 0.0, 0.0, 0.0),
        "end_to_end": (100, 0.1505, 0.19505, 0.200),
        "critical_end_to_end": (1, 0.2, 0.2, 0.2),
    }
    for k, (n, p50, p95, mx) in expect.items():
        s = stats[k]
        assert s["n"] == n, (k, s)
        assert np.allclose([s["p50"], s["p95"], s["max"]], [p50, p95, mx], atol=1e-9), (k, s)
    text = render(stats, None, ["selftest"])
    assert "NFR-002: PASS" in text and "NFR-001: NO DATA" in text, text
    print("selftest ok")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="*", default=[], help="runs/<id>/events.sqlite files")
    ap.add_argument("--config", default="config/default.yaml")
    ap.add_argument("--bench", action="store_true", help="GPU: 500-crop action path + peak VRAM")
    ap.add_argument("--out", default="reports/latency.md")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    bench = run_bench(load(a.config)) if a.bench else None
    text = render(summarise(stages(a.runs)), bench, a.runs)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
