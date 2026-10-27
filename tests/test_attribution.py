import time
from pathlib import Path

import cv2
import numpy as np
import pytest
import torch
from torch import nn

from xqi.explain.attribution import eigencam, save_heatmap_png
from xqi.explain.cause_model import CauseModel, build_model, save_checkpoint
from xqi.types import CAUSES, DEFECTS, Frame


class TinyCNN(nn.Module):
    # features.0 copies each channel (1x1 conv, identity weights); features.1 halves h, w.
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(nn.Conv2d(3, 3, 1, bias=False), nn.MaxPool2d(2))
        with torch.no_grad():
            self.features[0].weight.copy_(torch.eye(3).view(3, 3, 1, 1))

    def forward(self, x):
        return self.features(x).mean()


def tiny_cnn() -> nn.Module:
    return TinyCNN().eval()


def frame(image: np.ndarray) -> Frame:
    return Frame(frame_id=0, ts=0.0, wall_iso="2026-01-01T00:00:00", image=image)


def test_heatmap_max_in_hot_quadrant():
    image = np.zeros((64, 64, 3), np.uint8)
    image[32:, :32] = (40, 200, 120)  # bottom-left quadrant only
    heat = eigencam(tiny_cnn(), frame(image), "features.1", (0, 0, 64, 64))

    assert heat.shape == (64, 64) and heat.dtype == np.float32
    assert heat.min() >= 0.0 and heat.max() == pytest.approx(1.0)
    y, x = np.unravel_index(np.argmax(heat), heat.shape)
    assert y >= 32 and x < 32
    assert heat[:24, :].max() == 0.0 and heat[:, 40:].max() == 0.0


def test_heatmap_is_cropped_to_bbox():
    image = np.zeros((64, 64, 3), np.uint8)
    image[32:, :32] = 255
    heat = eigencam(tiny_cnn(), frame(image), "features.1", (8, 40, 30, 60))

    assert heat.shape == (20, 22)
    assert heat.min() > 0.9


def test_zero_activations_give_zero_heatmap():
    image = np.zeros((32, 48, 3), np.uint8)
    heat = eigencam(tiny_cnn(), frame(image), "features.1", (0, 0, 48, 32))

    assert heat.shape == (32, 48)
    assert not np.isnan(heat).any()
    assert heat.max() == 0.0


def test_save_heatmap_png(tmp_path):
    crop = np.full((20, 30, 3), 100, np.uint8)
    heat = np.zeros((20, 30), np.float32)
    heat[:, 15:] = 1.0
    path = tmp_path / "heat" / "d1.png"
    save_heatmap_png(heat, crop, path)

    out = cv2.imread(str(path))
    assert out.shape == crop.shape
    assert not np.array_equal(out[:, :15], out[:, 15:])


def test_cause_model_backbone(tmp_path):
    torch.manual_seed(0)
    weights = tmp_path / "cause.pt"
    save_checkpoint(build_model(len(CAUSES), 0, pretrained=False), weights)
    cause_model = CauseModel(weights, CAUSES, DEFECTS, "cpu")
    # Grey ≈ the ImageNet mean, so the background normalises to ~0 (black would light up the zero-padded border).
    image = np.full((224, 224, 3), 128, np.uint8)
    image[96:160, 32:96] = 255  # one bright square
    seen = []
    cause_model.model.register_forward_pre_hook(lambda _m, args: seen.append(args[0]))

    heat = eigencam(cause_model.model, frame(image), "backbone.layer4", (0, 0, 224, 224))
    cause_model.predict(image, "under_extrusion")

    assert heat.shape == (224, 224) and heat.dtype == np.float32
    assert heat.min() >= 0.0 and 0.9 < heat.max() <= 1.0  # max 1 on the 7x7 map; the 32x upsample shaves the peak
    y, x = np.unravel_index(np.argmax(heat), heat.shape)
    assert 96 <= y < 160 and 32 <= x < 96
    torch.testing.assert_close(seen[0], seen[1])  # the same tensor CauseModel.predict classifies


@pytest.mark.gpu
def test_real_best_pt_heatmap_fast():
    weights = Path("models/yolo/best.pt")
    if not weights.exists():
        pytest.skip("models/yolo/best.pt not present (T-0002 / T-0008)")
    from ultralytics import YOLO

    layer = "model.model.9"  # YOLO11 SPPF; cfg.attribution.layer now names the cause model's layer (T-0059)
    model = YOLO(str(weights))
    model.to("cuda")
    image = np.random.default_rng(0).integers(0, 255, (720, 1280, 3), np.uint8)
    xyxy = (400, 200, 700, 500)
    for _ in range(3):  # warm-up: predictor setup, cuDNN autotune
        eigencam(model, frame(image), layer, xyxy)

    t0 = time.perf_counter()
    heat = eigencam(model, frame(image), layer, xyxy)
    dt = time.perf_counter() - t0

    assert heat.shape == (300, 300) and heat.dtype == np.float32
    assert 0.0 <= heat.min() and heat.max() <= 1.0
    assert dt < 0.025, f"eigencam took {dt * 1000:.1f} ms"
