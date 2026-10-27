import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from xqi.detect import Detector
from xqi.types import DEFECTS, Frame

NAMES = {0: "Over-extr.", 1: "Stringing", 2: "no defect", 3: "Layer Shift"}


class StubModel:
    def __init__(self, names, xyxy, conf, cls):
        self.names = names
        self.boxes = SimpleNamespace(
            xyxy=np.array(xyxy, dtype=np.float32).reshape(-1, 4),
            conf=np.array(conf, dtype=np.float32),
            cls=np.array(cls, dtype=np.float32),
        )
        self.kwargs = None

    def __call__(self, image, **kwargs):
        self.kwargs = kwargs
        return [SimpleNamespace(boxes=self.boxes)]


def make_frame(h=100, w=200):
    return Frame(
        frame_id=7,
        ts=1.0,
        wall_iso="2026-01-01T00:00:00",
        image=np.zeros((h, w, 3), dtype=np.uint8),
    )


def make_detector(model):
    return Detector("unused.pt", 640, 0.25, "cpu", model=model)


def test_class_mapping_drops_no_defect():
    model = StubModel(
        NAMES,
        xyxy=[[0, 0, 10, 10], [0, 0, 20, 20], [0, 0, 30, 30], [0, 0, 5, 5]],
        conf=[0.9, 0.8, 0.95, 0.5],
        cls=[0, 1, 2, 3],
    )
    dets = make_detector(model)(make_frame())

    assert [d.cls for d in dets] == [
        "over_extrusion",
        "stringing",
        "layer_shift",
    ]
    assert all(d.cls in DEFECTS for d in dets)
    assert all(d.frame_id == 7 for d in dets)
    assert model.kwargs["imgsz"] == 640
    assert model.kwargs["conf"] == 0.25
    assert model.kwargs["device"] == "cpu"


def test_conf_filter():
    model = StubModel(
        NAMES,
        xyxy=[[0, 0, 10, 10], [0, 0, 10, 10]],
        conf=[0.1, 0.25],
        cls=[0, 1],
    )
    dets = make_detector(model)(make_frame())

    assert [(d.cls, d.conf) for d in dets] == [("stringing", 0.25)]


def test_area_frac_and_xyxy():
    model = StubModel(NAMES, xyxy=[[10, 20, 60, 70]], conf=[0.9], cls=[1])
    (det,) = make_detector(model)(make_frame(h=100, w=200))

    assert det.xyxy == (10.0, 20.0, 60.0, 70.0)
    assert det.area_frac == pytest.approx(50 * 50 / (100 * 200))
    assert 0 < det.area_frac <= 1
    assert isinstance(det.conf, float)


def test_empty_result():
    model = StubModel(NAMES, xyxy=[], conf=[], cls=[])
    assert make_detector(model)(make_frame()) == []


def test_unknown_name_raises_at_init():
    model = StubModel({0: "stringing", 1: "blob"}, [], [], [])
    with pytest.raises(ValueError, match="blob"):
        make_detector(model)


@pytest.mark.gpu
def test_best_pt_one_frame_under_60ms():
    from xqi.config import load

    cfg = load(Path("config/default.yaml"))
    if cfg.detector.weights is None:
        pytest.skip("detector.weights is null (ADR-0009: the detector is the integrating team's)")
    det = Detector(
        cfg.detector.weights,
        cfg.detector.imgsz,
        cfg.detector.conf,
        cfg.detector.device,
    )
    frame = make_frame(h=cfg.camera.height, w=cfg.camera.width)
    for _ in range(3):
        det(frame)

    t0 = time.perf_counter()
    dets = det(frame)
    elapsed = time.perf_counter() - t0

    assert all(d.cls in DEFECTS for d in dets)
    assert elapsed < 0.060, f"{elapsed * 1000:.1f} ms"
