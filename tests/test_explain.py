from pathlib import Path

import numpy as np

from xqi.config import load
from xqi.explain import Explainer, crop
from xqi.types import CAUSES, CauseEstimate, ConfirmedDefect, Frame, PrinterState

CFG = load(Path(__file__).resolve().parents[1] / "config" / "default.yaml")
NOW = 1000.0


class StubCauseModel:
    def __init__(self, probs):
        self.probs = {c: probs.get(c, 0.0) for c in CAUSES}
        self.calls = []

    def predict(self, crop_bgr, defect):
        self.calls.append((crop_bgr.shape, defect))
        top = max(self.probs, key=self.probs.get)
        return CauseEstimate(probs=self.probs, top=top, p_top=self.probs[top])


def _state(ts=NOW - 1):
    return PrinterState(
        ts=ts, state="Printing", nozzle_actual_c=210.0, nozzle_target_c=210.0,
        bed_actual_c=60.0, bed_target_c=60.0, flow_pct=100.0, speed_pct=100.0,
        progress_pct=None, last_change_ts={},
    )


def _cd():
    return ConfirmedDefect(
        defect_id="d1", cls="under_extrusion", frame_id=1, t0=NOW - 5, t_conf=NOW, conf=0.9,
        xyxy=(20.0, 10.0, 60.0, 30.0), area_frac=0.01, recent_hits=4, severity=0.5,
        critical=False,
    )


FRAME = Frame(frame_id=1, ts=NOW, wall_iso="", image=np.zeros((100, 200, 3), np.uint8))


HISTORY = (_state(),)


def _explain(probs, qhat=0.8, history=HISTORY):
    model = StubCauseModel(probs)
    out = Explainer(model, qhat, CAUSES, CFG).explain(_cd(), FRAME, history)
    return model, *out


def test_two_member_set_gives_two_proposals_by_probability():
    model, est, cset, flags, props = _explain(
        {"nozzle_temp_low": 0.3, "flow_low": 0.6, "none": 0.1}
    )

    assert model.calls == [((28, 56, 3), "under_extrusion")]
    assert est.top == "flow_low"
    assert set(cset.members) == {"flow_low", "nozzle_temp_low"}
    assert (cset.alpha, cset.qhat) == (CFG.conformal.alpha, 0.8)
    assert flags == ()
    assert [p.cause for p in props] == ["flow_low", "nozzle_temp_low"]
    assert [p.var for p in props] == ["flow", "nozzle_temp"]
    assert all(p.defect_id == "d1" for p in props)


def test_none_only_set_gives_no_proposals():
    _, _, cset, _, props = _explain({"none": 0.9, "flow_low": 0.1})

    assert cset.members == ("none",)
    assert props == []


def test_non_actionable_member_is_skipped():
    _, _, cset, _, props = _explain({"misalignment": 0.5, "flow_low": 0.4, "none": 0.1})

    assert set(cset.members) == {"misalignment", "flow_low"}
    assert [p.cause for p in props] == ["flow_low"]


def test_no_history_flags_state_and_proposes_nothing():
    _, _, cset, flags, props = _explain({"flow_low": 0.9, "none": 0.1}, history=())

    assert cset.members == ("flow_low",)
    assert flags == ("state_unavailable",)
    assert props == []


def test_crop_pads_and_clips_to_image():
    image = np.zeros((100, 200, 3), np.uint8)

    assert crop(image, (20, 10, 60, 30), 0.2).shape == (28, 56, 3)
    assert crop(image, (0, 0, 200, 100), 0.2).shape == (100, 200, 3)
