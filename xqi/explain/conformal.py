"""Split-conformal (LAC) calibration and prediction sets.

Implements 07-math.md §8 and ADR-0003. The nonconformity score is the LAC score
``s_i = 1 - p_hat_{y_i}(x_i)``; the set is ``C(x) = {y : p_hat_y(x) >= 1 - qhat}``.
The guarantee is marginal and only holds under exchangeability, so callers on a
geometry shift must report empirical coverage rather than "guaranteed".
"""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from pathlib import Path

import numpy as np

MIN_CALIBRATION = 20

_QHAT_KEYS = ("qhat", "alpha", "n")


def _as_probs(probs, *, ndim: int) -> np.ndarray:
    array = np.asarray(probs, dtype=float)

    if array.ndim != ndim:
        raise ValueError(
            f"conformal: probs must be {ndim}-dimensional, got {array.ndim}"
        )

    if not np.all(np.isfinite(array)):
        raise ValueError("conformal: probabilities must be finite")

    return array


def _check_alpha(alpha: float) -> float:
    value = float(alpha)

    if not (0.0 < value < 1.0):
        raise ValueError("conformal: alpha must be strictly between 0 and 1")

    return value


def calibrate(probs, y, alpha: float) -> float:
    """Return the LAC quantile ``qhat`` from a calibration split.

    ``probs`` is ``[n, K]`` and ``y`` is ``[n]``. Uses ``numpy.quantile`` with
    ``method="higher"`` at level ``ceil((n + 1) * (1 - alpha)) / n``; if that
    level exceeds 1 the function returns ``1.0``. Fewer than 20 examples is a
    ``ValueError`` (07-math.md §8).
    """

    alpha = _check_alpha(alpha)

    probabilities = _as_probs(probs, ndim=2)
    labels = np.asarray(y)

    if labels.ndim != 1:
        raise ValueError("conformal: y must be 1-dimensional")

    n, k = probabilities.shape

    if labels.shape[0] != n:
        raise ValueError(
            "conformal: y must have one label per probability row"
        )

    if n < MIN_CALIBRATION:
        raise ValueError(
            f"conformal: need at least {MIN_CALIBRATION} calibration "
            f"examples, got {n}"
        )

    if not np.issubdtype(labels.dtype, np.integer):
        raise ValueError("conformal: y must contain integer class indices")

    if labels.min() < 0 or labels.max() >= k:
        raise ValueError("conformal: y contains a label outside [0, K)")

    scores = 1.0 - probabilities[np.arange(n), labels]
    level = math.ceil((n + 1) * (1.0 - alpha)) / n

    if level > 1.0:
        return 1.0

    return float(np.quantile(scores, level, method="higher"))


def predict_set(
    probs,
    qhat: float,
    labels: Sequence[str],
) -> tuple[str, ...]:
    """Return the labels whose probability is ``>= 1 - qhat`` (ties included).

    The returned tuple preserves the original ``labels`` order.
    """

    probabilities = _as_probs(probs, ndim=1)
    label_tuple = tuple(labels)

    if probabilities.shape[0] != len(label_tuple):
        raise ValueError(
            "conformal: probs and labels must have the same length"
        )

    threshold_value = float(qhat)
    if not (0.0 <= threshold_value <= 1.0):
        raise ValueError("conformal: qhat must be within [0, 1]")

    threshold = 1.0 - threshold_value

    return tuple(
        label
        for label, probability in zip(label_tuple, probabilities)
        if probability >= threshold
    )


def save_qhat(
    path: str | Path,
    qhat: float,
    alpha: float,
    n: int,
) -> None:
    """Persist the calibration metadata as JSON."""

    data = {
        "qhat": float(qhat),
        "alpha": float(alpha),
        "n": int(n),
    }

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    with target.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")


def load_qhat(path: str | Path) -> dict[str, float | int]:
    """Load the calibration metadata saved by :func:`save_qhat`."""

    target = Path(path)

    if not target.exists():
        raise FileNotFoundError(f"conformal: {target} not found")

    with target.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict) or any(
        key not in data for key in _QHAT_KEYS
    ):
        raise ValueError(
            f"conformal: {target} is missing one of {_QHAT_KEYS}"
        )

    return {
        "qhat": float(data["qhat"]),
        "alpha": float(data["alpha"]),
        "n": int(data["n"]),
    }


__all__ = ["calibrate", "load_qhat", "predict_set", "save_qhat"]
