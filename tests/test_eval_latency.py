import importlib.util
from pathlib import Path

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
    times, verdicts = eval_latency.bench_added(explainer, CFG, n=12, warmup=2)
    assert len(times) == 12 and all(t > 0 for t in times)
    assert verdicts == {"APPLY"}  # one confident actionable cause → one passing proposal in auto mode
