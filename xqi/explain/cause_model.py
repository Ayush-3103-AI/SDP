"""Image-only cause model (ADR-0002): ResNet18 on the defect crop + defect-class one-hot.

Gate 0 frame:
- Decision: which setpoint proposal(s) the operator sees for a confirmed defect.
- Unit: one confirmed defect box (224 px crop + defect class) at confirmation time.
- Target: the induced cause of the box's trial (09 §Data label rule).
- Metric: LOGO mean top-1 (NFR-005). Error cost: a wrong actionable cause proposes a
  wrong-direction change (bounded by the gate), so per-class recall on actionable causes
  is the main diagnostic.
- Baseline: the floor, i.e. the majority cause per defect class (T-0010).

Never feed setpoints or telemetry into this model: `predict` takes only (crop, defect).
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

_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


class _CauseNet(nn.Module):
    def __init__(self, n_causes: int, n_defects: int, pretrained: bool):
        super().__init__()
        self.backbone = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1 if pretrained else None)
        self.backbone.fc = nn.Identity()
        self.n_defects = n_defects
        self.head = nn.Linear(512 + n_defects, n_causes)

    def forward(self, x: torch.Tensor, defect: torch.Tensor) -> torch.Tensor:
        onehot = F.one_hot(defect, self.n_defects).to(x.dtype)
        return self.head(torch.cat([self.backbone(x), onehot], dim=1))


def build_model(n_causes: int, n_defects: int, pretrained: bool = True) -> nn.Module:
    """ResNet18 (ImageNet) features ++ defect one-hot -> Linear -> cause logits.

    `pretrained=False` skips the weight download (tests, or before loading a state dict).
    """
    return _CauseNet(n_causes, n_defects, pretrained)


def train_one_epoch(model, loader, opt, class_weights) -> tuple[float, float]:
    """One pass of class-weighted CE over (image, defect_idx, cause_idx) batches.

    Returns (mean loss, accuracy) over the epoch, measured in train mode.
    """
    device = next(model.parameters()).device
    weight = None if class_weights is None else class_weights.to(device)
    model.train()
    loss_sum, correct, n = 0.0, 0, 0
    for x, defect, y in loader:
        x, defect, y = x.to(device), defect.to(device), y.to(device)
        logits = model(x, defect)
        loss = F.cross_entropy(logits, y, weight=weight)
        opt.zero_grad()
        loss.backward()
        opt.step()
        loss_sum += loss.item() * len(y)
        correct += (logits.argmax(1) == y).sum().item()
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
    ):
        self.causes = tuple(causes)
        self.defects = tuple(defects)
        self.device = torch.device(device)
        self.input_px = input_px
        self.model = build_model(len(self.causes), len(self.defects), pretrained=False)
        self.model.load_state_dict(torch.load(weights, map_location=self.device, weights_only=True))
        self.model.to(self.device).eval()

    def predict(self, crop_bgr: np.ndarray, defect: str) -> CauseEstimate:
        rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
        rgb = cv2.resize(rgb, (self.input_px, self.input_px), interpolation=cv2.INTER_AREA)
        x = (rgb.astype(np.float32) / 255.0 - _MEAN) / _STD
        x = torch.from_numpy(x.transpose(2, 0, 1)).unsqueeze(0).to(self.device)
        d = torch.tensor([self.defects.index(defect)], device=self.device)
        with torch.no_grad():
            p = torch.softmax(self.model(x, d), dim=1)[0].cpu().tolist()
        probs = dict(zip(self.causes, p, strict=True))
        top = max(probs, key=probs.get)
        return CauseEstimate(probs=probs, top=top, p_top=probs[top])
