"""Split-conformal (LAC) cause sets (07-math §8, ADR-0003)."""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from pathlib import Path

import numpy as np

MIN_CALIBRATION = 20


def calibrate(probs: np.ndarray, y: np.ndarray, alpha: float) -> float:
    """Return qhat from calibration probs[n, K] and true labels y[n]."""
    n = len(y)
    if n < MIN_CALIBRATION:
        raise ValueError(f"need at least {MIN_CALIBRATION} calibration samples, got {n}")

    scores = 1.0 - probs[np.arange(n), y]
    level = math.ceil((n + 1) * (1 - alpha)) / n
    if level > 1:
        return 1.0
    return float(np.quantile(scores, level, method="higher"))


def predict_set(probs: np.ndarray, qhat: float, labels: Sequence[str]) -> tuple[str, ...]:
    """Labels with p >= 1 - qhat, in label order. Ties are inclusive."""
    # Compare scores, not 1 - qhat, so ties match calibrate bit for bit.
    return tuple(label for label, p in zip(labels, probs) if 1.0 - p <= qhat)


def save_qhat(path: str | Path, qhat: float, alpha: float, n: int) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"qhat": qhat, "alpha": alpha, "n": n}))


def load_qhat(path: str | Path) -> dict:
    """Return {"qhat", "alpha", "n"} as written by save_qhat."""
    return json.loads(Path(path).read_text())
