"""T-0030 — the YOLO11 detector wrapper, with a stub model (no torch)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from xqi.detect import Detector, DetectorError
from xqi.types import Frame

ROOT = Path(__file__).resolve().parents[1]


class FakeBoxes:
    def __init__(self, xyxy, conf, cls) -> None:
        self.xyxy = np.asarray(xyxy, dtype=float).reshape(-1, 4)
        self.conf = np.asarray(conf, dtype=float).reshape(-1)
        self.cls = np.asarray(cls, dtype=float).reshape(-1)


class FakeResult:
    def __init__(self, boxes: FakeBoxes) -> None:
        self.boxes = boxes


class StubModel:
    def __init__(self, names, result=None, error: Exception | None = None) -> None:
        self.names = names
        self._result = result
        self._error = error
        self.calls: list[dict] = []

    def __call__(self, source, **kwargs):
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return self._result


def make_frame(frame_id: int = 0, shape=(100, 200, 3)) -> Frame:
    image = np.zeros(shape, dtype=np.uint8)
    return Frame(frame_id=frame_id, ts=0.0, wall_iso="t", image=image)


def detector(names, boxes=None, conf=0.25, error=None) -> Detector:
    result = [FakeResult(FakeBoxes(*boxes))] if boxes is not None else []
    model = StubModel(names, result=result, error=error)
    return Detector("unused.pt", 640, conf, "cpu", model=model)


NAMES = {0: "Over-extr.", 1: "under-extrusion", 2: "defect", 3: "Layer Shift"}


def test_class_names_are_normalised():
    det = detector(NAMES)

    assert det._classes == {
        0: "over_extrusion",
        1: "under_extrusion",
        2: None,  # the no-defect class is dropped
        3: "layer_shift",
    }


def test_unknown_class_name_raises_at_init():
    with pytest.raises(DetectorError):
        detector({0: "wobbling"})


def test_missing_weights_raise_at_init():
    with pytest.raises(DetectorError):
        Detector(str(ROOT / "models" / "yolo" / "missing.pt"), 640, 0.25, "cpu")


def test_detections_are_mapped_with_area_fraction():
    det = detector(
        NAMES,
        boxes=(
            [[0, 0, 20, 10], [10, 10, 30, 30]],
            [0.9, 0.8],
            [0, 1],
        ),
    )

    detections = det(make_frame())

    assert [d.cls for d in detections] == ["over_extrusion", "under_extrusion"]
    assert detections[0].xyxy == (0.0, 0.0, 20.0, 10.0)
    assert detections[0].area_frac == pytest.approx(200 / 20000)
    assert detections[1].area_frac == pytest.approx(400 / 20000)


def test_confidence_filter_includes_the_boundary():
    det = detector(
        NAMES,
        boxes=([[0, 0, 10, 10]] * 2, [0.24, 0.25], [0, 0]),
    )

    detections = det(make_frame())

    assert len(detections) == 1
    assert detections[0].conf == 0.25


def test_no_defect_class_is_dropped():
    det = detector(
        NAMES,
        boxes=([[0, 0, 10, 10]], [0.9], [2]),
    )

    assert det(make_frame()) == []


def test_empty_results_yield_no_detections():
    det = detector(NAMES, boxes=(np.empty((0, 4)), [], []))

    assert det(make_frame()) == []


def test_malformed_boxes_are_skipped():
    det = detector(
        NAMES,
        boxes=(
            [[0, 0, 0, 10], [np.nan, 0, 10, 10], [1, 1, 11, 21]],
            [0.9, 0.9, 0.9],
            [0, 0, 0],
        ),
    )

    detections = det(make_frame())

    assert len(detections) == 1
    assert detections[0].xyxy == (1.0, 1.0, 11.0, 21.0)


def test_inference_exception_propagates():
    det = detector(NAMES, error=RuntimeError("cuda blew up"))

    with pytest.raises(RuntimeError, match="cuda blew up"):
        det(make_frame())


def test_inference_is_called_with_the_configured_settings():
    det = detector(NAMES, boxes=(np.empty((0, 4)), [], []), conf=0.4)
    frame = make_frame()

    det(frame)

    call = det._model.calls[0]
    assert call["imgsz"] == 640
    assert call["conf"] == 0.4
    assert call["device"] == "cpu"


@pytest.mark.gpu
def test_gpu_inference_latency():
    """best.pt on one frame in < 60 ms — runs in GPU batch G1 (T-0008)."""

    weights = ROOT / "models" / "yolo" / "best.pt"
    if not weights.is_file():
        pytest.skip("models/yolo/best.pt not present; runs in GPU batch G1")

    import time

    det = Detector(str(weights), 1088, 0.25, "cuda:0")
    frame = make_frame(shape=(1056, 1920, 3))

    det(frame)  # warm up

    start = time.perf_counter()
    det(frame)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms < 60
