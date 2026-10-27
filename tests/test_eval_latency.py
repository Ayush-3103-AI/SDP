import importlib.util
from pathlib import Path

import cv2
import numpy as np
import yaml

from xqi.config import load
from xqi.explain import Explainer
from xqi.types import CAUSES, CauseEstimate

ROOT = Path(__file__).resolve().parents[1]
CFG = load(ROOT / "config" / "default.yaml")
spec = importlib.util.spec_from_file_location("eval_latency", ROOT / "scripts" / "eval_latency.py")
eval_latency = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eval_latency)


def test_selftest_known_percentiles():
    assert eval_latency.selftest() == 0


def test_render_has_nfr_lines_and_no_data_without_bench():
    stats = eval_latency.summarise({"end_to_end": [0.1, 0.2], "critical_end_to_end": [0.5]})
    text = eval_latency.render(stats, None, ["runs/x/events.sqlite"])
    assert "NFR-001: NO DATA" in text
    assert "NFR-002: FAIL" in text  # critical p95 0.5 s > 0.27 s
    assert "NFR-011: NO DATA" in text


class StubCauseModel:
    def predict(self, crop_bgr, defect):
        assert crop_bgr.size > 0
        return CauseEstimate({c: 1.0 if c == "flow_high" else 0.0 for c in CAUSES}, "flow_high", 1.0)


def test_bench_added_times_the_whole_action_path():
    explainer = Explainer(StubCauseModel(), 0.5, CAUSES, CFG)
    crops, source = eval_latency.load_crops(None, 12)
    times, verdicts = eval_latency.bench_added(explainer, CFG, crops, warmup=2)
    assert source.startswith("synthetic") and len(times) == 12 and all(t > 0 for t in times)
    assert verdicts == {"APPLY"}  # one confident actionable cause → one passing proposal in auto mode


def test_load_crops_cycles_crops_csv(tmp_path):
    lines = ["crop_path,trial_id,ts_s"]
    for i in range(3):
        cv2.imwrite(str(tmp_path / f"{i}.jpg"), np.full((8, 8, 3), 50 * i, np.uint8))
        lines.append(f"{(tmp_path / f'{i}.jpg').as_posix()},p0,{i}")
    (tmp_path / "crops.csv").write_text("\n".join(lines) + "\n")

    crops, source = eval_latency.load_crops(tmp_path / "crops.csv", 5)
    assert len(crops) == 5 and crops[0].shape == (8, 8, 3) and "CAXTON crops (3 distinct" in source
    assert [int(c[0, 0, 0]) for c in crops] == [0, 50, 100, 0, 50]


def test_cpu_bench_smoke(tmp_path):
    """CPU `--bench --limit`: random-init cause model, synthetic crops, EigenCAM timed, no NFR verdicts off the GPU."""
    raw = yaml.safe_load((ROOT / "config" / "default.yaml").read_text(encoding="utf-8"))
    raw["causes_file"] = str(ROOT / "config" / "causes.yaml")
    raw["cause_model"] |= {"weights": str(tmp_path / "none.pt"), "device": "cpu"}
    raw["conformal"]["qhat_file"] = str(tmp_path / "none.json")
    (tmp_path / "cfg.yaml").write_text(yaml.safe_dump(raw), encoding="utf-8")
    out = tmp_path / "latency.md"

    rc = eval_latency.main(["--bench", "--limit", "5", "--config", str(tmp_path / "cfg.yaml"),
                            "--crops", str(tmp_path / "none.csv"), "--out", str(out)])
    text = out.read_text(encoding="utf-8")
    assert rc == 0
    assert "## Bench: 5 synthetic" in text and "p99" in text and "EigenCAM" in text
    assert "random-init cause model" in text and "detector: not configured" in text
    assert "NFR-001: NO DATA" in text and "NFR-011: NO DATA" in text
