"""Image-only cause model (ADR-0002): ResNet18 on the crop (+ defect-class one-hot if use_defect).

Gate 0 frame:
- Decision: which setpoint proposal(s) the operator sees for a confirmed defect.
- Unit: one 224 px crop (nozzle ROI, or a confirmed defect box) at decision time.
- Target: the image's process deviation (07 §15 label rule).
- Metric: LOGO mean top-1 (NFR-005). Error cost: a wrong actionable cause proposes a
  wrong-direction change (bounded by the gate), so per-class recall on actionable causes
  is the main diagnostic.
- Baseline: the floor, i.e. the training prints' majority cause (T-0010; CAXTON has no defect class).

Never feed setpoints or telemetry into this model: `predict` takes only (crop, defect), and with
use_defect=false (the CAXTON default) it ignores the defect too.
"""

from collections.abc import Sequence
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from torch import nn
from torchvision.models import ResNet18_Weights, resnet18

from xqi.types import CauseEstimate

HEAD_VARS = ("flow", "speed", "z_offset", "nozzle_temp")  # 4-head order = crops.csv class columns; 0 low 1 good 2 high
_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


class _CauseNet(nn.Module):
    def __init__(self, n_causes: int, n_defects: int, pretrained: bool):
        super().__init__()
        self.backbone = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1 if pretrained else None)
        self.backbone.fc = nn.Identity()
        self.n_defects = n_defects
        self.head = nn.Linear(512 + n_defects, n_causes)

    def forward(self, x: torch.Tensor, defect: torch.Tensor | None = None) -> torch.Tensor:
        features = self.backbone(x)
        if self.n_defects == 0:
            return self.head(features)
        onehot = F.one_hot(defect, self.n_defects).to(x.dtype)
        return self.head(torch.cat([features, onehot], dim=1))


def build_model(n_causes: int, n_defects: int, pretrained: bool = True) -> nn.Module:
    """ResNet18 (ImageNet) features [++ defect one-hot] -> Linear -> cause logits.

    `n_defects=0` (use_defect=false) gives a 512 -> n_causes head that ignores the defect input.
    `pretrained=False` skips the weight download (tests, or before loading a state dict).
    """
    return _CauseNet(n_causes, n_defects, pretrained)


def joint_to_causes(p_heads: np.ndarray, labels: Sequence[str]) -> np.ndarray:
    """(n, 4, 3) per-head probabilities → (n, len(labels)) single-deviation cause probabilities, renormalised.

    Heads assumed independent given the image: P(none) ∝ Π_v P(good_v), P(v_low) ∝ P(low_v) Π_{u≠v} P(good_u).
    """
    good = p_heads[:, :, 1]
    all_good = good.prod(1)
    out = np.zeros((len(p_heads), len(labels)), np.float64)
    for j, c in enumerate(labels):
        if c == "none":
            out[:, j] = all_good
            continue
        var, side = c.rsplit("_", 1)
        v = HEAD_VARS.index(var)
        others = all_good / np.clip(good[:, v], 1e-12, None)
        out[:, j] = p_heads[:, v, 0 if side == "low" else 2] * others
    return (out / out.sum(1, keepdims=True)).astype(np.float32)


def to_input(crop_bgr: np.ndarray, input_px: int) -> torch.Tensor:
    """BGR crop -> the (1, 3, input_px, input_px) ImageNet-normalised RGB tensor the net classifies."""
    rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
    rgb = cv2.resize(rgb, (input_px, input_px), interpolation=cv2.INTER_AREA)
    x = (rgb.astype(np.float32) / 255.0 - _MEAN) / _STD
    return torch.from_numpy(x.transpose(2, 0, 1)).unsqueeze(0)


def save_checkpoint(model: nn.Module, path: str | Path, **meta) -> None:
    """Save {"use_defect", "state_dict", **meta} so CauseModel can refuse a mismatched config.

    meta = provenance (seed, config, git SHA, data sha256 ...); plain types only, so weights_only loading works.
    """
    torch.save({"use_defect": model.n_defects > 0, "state_dict": model.state_dict(), **meta}, path)


def _loss(logits, y, weight, heads: int):
    """Class-weighted CE; heads=4: mean of the 4 per-head 3-way CEs (y: (n, 4), weight: (4, 3) or None)."""
    if heads == 1:
        return F.cross_entropy(logits, y, weight=weight), (logits.argmax(1) == y).float()
    lg = logits.view(len(y), heads, 3)
    loss = sum(F.cross_entropy(lg[:, k], y[:, k], weight=None if weight is None else weight[k])
               for k in range(heads)) / heads
    return loss, (lg.argmax(2) == y).float().mean(1)


def train_one_epoch(model, loader, opt, class_weights, scaler=None, heads=1, ema=None,
                    freeze_bn=False) -> tuple[float, float]:
    """One pass of class-weighted CE over (image, defect_idx, target) batches.

    scaler = a torch.amp.GradScaler turns on float16 autocast (CUDA AMP). heads=4: targets are (n, 4) class
    columns and the accuracy is the mean per-head accuracy. ema = a swa_utils.AveragedModel updated every step.
    freeze_bn keeps the backbone's BN statistics fixed (the linear-probe phase of LP-FT). Returns (mean loss,
    accuracy) over the epoch, measured in train mode.
    """
    device = next(model.parameters()).device
    weight = None if class_weights is None else class_weights.to(device)
    model.train()
    if freeze_bn:
        model.backbone.eval()
    loss_sum, correct, n = 0.0, 0.0, 0
    for x, defect, y in loader:
        x, defect, y = x.to(device), defect.to(device), y.to(device)
        with torch.autocast(device.type, enabled=scaler is not None):
            logits = model(x, defect)
            loss, right = _loss(logits.float(), y, weight, heads)
        opt.zero_grad()
        if scaler is None:
            loss.backward()
            opt.step()
        else:
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
        if ema is not None:
            ema.update_parameters(model)
        loss_sum += loss.item() * len(y)
        correct += right.sum().item()
        n += len(y)
    return loss_sum / n, correct / n


class CauseModel:
    def __init__(
        self,
        weights: str | Path,
        causes: Sequence[str],
        defects: Sequence[str],
        device: str,
        input_px: int = 224,
        use_defect: bool = False,
        calibration: dict | None = None,
    ):
        self.causes = tuple(causes)
        self.defects = tuple(defects)
        self.device = torch.device(device)
        self.input_px = input_px
        self.use_defect = use_defect
        ckpt = torch.load(weights, map_location=self.device, weights_only=True)
        if ckpt.get("use_defect") is not use_defect:
            raise ValueError(f"{weights}: checkpoint use_defect={ckpt.get('use_defect')}, config {use_defect}")
        if "causes" in ckpt and tuple(ckpt["causes"]) != self.causes:
            raise ValueError(f"{weights}: checkpoint causes {ckpt['causes']} differ from config {self.causes}")
        self.heads = int(ckpt.get("heads", 1))
        if self.heads not in (1, 4) or (self.heads == 4 and use_defect):
            raise ValueError(f"{weights}: heads={self.heads} (use_defect={use_defect}) is not supported")
        n_out = 3 * self.heads if self.heads > 1 else len(self.causes)
        self.model = build_model(n_out, len(self.defects) if use_defect else 0, pretrained=False)
        # Post-hoc calibration fitted on calibration prints (scripts/recalibrate.py): softmax(log p / T + τ log π).
        self.calibration = None if calibration is None else (
            float(calibration["T"]), float(calibration["tau"]), np.asarray(calibration["log_prior"], np.float64))
        self.model.load_state_dict(ckpt["state_dict"])
        self.model.to(self.device).eval()

    def predict(self, crop_bgr: np.ndarray, defect: str) -> CauseEstimate:
        x = to_input(crop_bgr, self.input_px).to(self.device)
        d = torch.tensor([self.defects.index(defect)], device=self.device) if self.use_defect else None
        with torch.no_grad():
            logits = self.model(x, d).float()
        if self.heads == 1:
            p = torch.softmax(logits, dim=1)[0].cpu().numpy().astype(np.float64)
        else:
            p = joint_to_causes(torch.softmax(logits.view(1, self.heads, 3), -1).cpu().numpy(), self.causes)[0]
        if self.calibration is not None:
            t, tau, log_prior = self.calibration
            z = np.log(np.clip(p, 1e-12, None)) / t + tau * log_prior
            p = np.exp(z - z.max())
            p /= p.sum()
        probs = dict(zip(self.causes, p.tolist(), strict=True))
        top = max(probs, key=probs.get)
        return CauseEstimate(probs=probs, top=top, p_top=probs[top])
