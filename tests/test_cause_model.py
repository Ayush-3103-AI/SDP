import inspect

import numpy as np
import torch

from xqi.explain.cause_model import CauseModel, build_model, train_one_epoch
from xqi.types import CAUSES, DEFECTS


def _cause_model(tmp_path):
    weights = tmp_path / "cause.pt"
    torch.save(build_model(len(CAUSES), len(DEFECTS), pretrained=False).state_dict(), weights)
    return CauseModel(weights, CAUSES, DEFECTS, "cpu")


def test_predict_probs_sum_to_one(tmp_path):
    model = _cause_model(tmp_path)
    crop = np.random.default_rng(0).integers(0, 256, (50, 80, 3), dtype=np.uint8)

    est = model.predict(crop, "stringing")

    assert set(est.probs) == set(CAUSES)
    assert abs(sum(est.probs.values()) - 1.0) < 1e-5
    assert est.top == max(est.probs, key=est.probs.get)
    assert est.p_top == est.probs[est.top]


def test_predict_takes_only_crop_and_defect(tmp_path):
    # Leakage guard (ADR-0002): no setpoint or telemetry argument.
    params = inspect.signature(_cause_model(tmp_path).predict).parameters
    assert list(params) == ["crop_bgr", "defect"]


def test_overfits_two_colour_coded_causes():
    torch.manual_seed(0)
    n = 64
    y = torch.arange(n) % 2
    x = torch.zeros(n, 3, 32, 32)  # small for CPU speed; the backbone is size-agnostic
    x[y == 0, 0] = 1.0  # cause 0: red
    x[y == 1, 2] = 1.0  # cause 1: blue
    x += 0.1 * torch.randn_like(x)
    defect = torch.zeros(n, dtype=torch.long)
    loader = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(x, defect, y), batch_size=16, shuffle=True
    )
    model = build_model(2, len(DEFECTS), pretrained=False)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-4)

    for _ in range(5):
        _, acc = train_one_epoch(model, loader, opt, torch.ones(2))

    assert acc > 0.9
