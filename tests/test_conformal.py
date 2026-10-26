import numpy as np
import pytest

from xqi.explain.conformal import calibrate, load_qhat, predict_set, save_qhat

LABELS = ("a", "b", "c", "d", "e")


def draw(rng: np.random.Generator, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Calibrated categorical model: y is drawn from the predicted probs."""
    probs = rng.dirichlet(np.ones(len(LABELS)), size=n)
    y = (rng.random((n, 1)) > probs.cumsum(axis=1)).sum(axis=1)
    return probs, np.minimum(y, len(LABELS) - 1)


@pytest.mark.parametrize("alpha", [0.05, 0.1, 0.2])
def test_coverage(alpha):
    rng = np.random.default_rng(0)
    qhat = calibrate(*draw(rng, 5000), alpha)

    probs, y = draw(rng, 20_000)
    covered = [LABELS[t] in predict_set(p, qhat, LABELS) for p, t in zip(probs, y)]

    assert 1 - alpha - 0.01 <= np.mean(covered) <= 1 - alpha + 0.03


def test_too_few_samples():
    probs = np.full((19, 2), 0.5)
    with pytest.raises(ValueError):
        calibrate(probs, np.zeros(19, dtype=int), 0.1)


def test_level_above_one():
    # n=20, alpha=0.01: ceil(21 * 0.99) / 20 = 21/20 > 1.
    probs = np.tile([0.9, 0.1], (20, 1))
    qhat = calibrate(probs, np.zeros(20, dtype=int), 0.01)

    assert qhat == 1.0
    assert predict_set(np.array([1.0, 0.0]), qhat, ("x", "y")) == ("x", "y")


def test_ties_inclusive_and_label_order():
    probs = np.tile([0.3, 0.7], (20, 1))
    qhat = calibrate(probs, np.ones(20, dtype=int), 0.1)

    assert qhat == pytest.approx(0.3)
    # 0.7 sits exactly at 1 - qhat and stays in; 0.3 is out.
    assert predict_set(np.array([0.3, 0.7]), qhat, ("x", "y")) == ("y",)
    assert predict_set(np.array([0.7, 0.3]), qhat, ("x", "y")) == ("x",)
    assert predict_set(np.array([0.5, 0.5]), 0.5, ("x", "y")) == ("x", "y")


def test_save_load_roundtrip(tmp_path):
    path = tmp_path / "cause" / "qhat.json"
    save_qhat(path, 0.42, 0.1, 500)

    assert load_qhat(path) == {"qhat": 0.42, "alpha": 0.1, "n": 500}
