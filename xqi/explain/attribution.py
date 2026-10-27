"""EigenCAM on one backbone layer: one forward pass, no gradients (07-math §11)."""

from __future__ import annotations

from collections.abc import Sequence
from operator import attrgetter
from pathlib import Path

import cv2
import numpy as np
import torch

from xqi.explain.cause_model import _CauseNet, to_input
from xqi.types import Frame


def _activations(model, image: np.ndarray, layer: str, input_px: int) -> np.ndarray:
    """Run one forward pass and return the (C, h, w) output of `layer`."""
    captured = []
    handle = attrgetter(layer)(model).register_forward_hook(
        lambda _m, _i, out: captured.append(out[0].detach())
    )
    try:
        if hasattr(model, "predict"):  # ultralytics YOLO
            # ponytail: predict letterboxes the frame; the small pad is upsampled with
            # the map rather than stripped. Undo the letterbox if alignment matters.
            model.predict(image, verbose=False)
        else:
            device = next(model.parameters()).device
            if isinstance(model, _CauseNet):  # the tensor CauseModel.predict classifies
                x = to_input(image, input_px)
            else:
                x = torch.from_numpy(image[..., ::-1].copy()).permute(2, 0, 1)[None].float() / 255  # BGR -> RGB
            with torch.no_grad():
                model(x.to(device))
    finally:
        handle.remove()
    return captured[-1].float().cpu().numpy()


def eigencam(model, frame: Frame, layer: str, xyxy: Sequence[float], input_px: int = 224) -> np.ndarray:
    """Return a float32 heatmap in [0, 1], the size of the bbox crop of `frame`.

    For the cause model, pass the crop it classified as `frame`, the full-crop box and cfg.cause_model.input_px.
    """
    act = _activations(model, frame.image, layer, input_px)
    c, h, w = act.shape
    a = act.reshape(c, h * w).T
    a_bar = a - a.mean(axis=0)
    v1 = np.linalg.svd(a_bar, full_matrices=False)[2][0]
    heat = (a_bar @ v1).reshape(h, w)
    # Orient by the uncentered A: Σ(Ā v1) is always 0, so it cannot fix the SVD sign.
    if (a @ v1).sum() < 0:
        heat = -heat
    heat = np.maximum(heat, 0)
    peak = heat.max()
    heat = heat / peak if peak > 0 else np.zeros_like(heat)

    fh, fw = frame.image.shape[:2]
    heat = cv2.resize(heat.astype(np.float32), (fw, fh), interpolation=cv2.INTER_LINEAR)
    x1, y1, x2, y2 = (round(float(v)) for v in xyxy)
    x1, y1 = min(max(x1, 0), fw - 1), min(max(y1, 0), fh - 1)
    x2, y2 = min(max(x2, x1 + 1), fw), min(max(y2, y1 + 1), fh)
    return np.clip(heat[y1:y2, x1:x2], 0, 1)


def save_heatmap_png(heat: np.ndarray, crop_bgr: np.ndarray, path: str | Path) -> None:
    """Overlay `heat` on the crop with COLORMAP_JET at alpha 0.4 and write a PNG."""
    color = cv2.applyColorMap(np.uint8(np.clip(heat, 0, 1) * 255), cv2.COLORMAP_JET)
    color = cv2.resize(color, (crop_bgr.shape[1], crop_bgr.shape[0]))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), cv2.addWeighted(color, 0.4, crop_bgr, 0.6, 0))
