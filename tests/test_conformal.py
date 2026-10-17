import numpy as np
import pytest

from xqi.explain.conformal import (
    calibrate,
    load_qhat,
    predict_set,
    save_qhat,
)

# --------------------------------------------------------------------------- #
# calibrate — numerical behaviour and boundaries
# --------------------------------------------------------------------------- #


def test_small_calibration_dataset_is_rejected():
    probs = np.full((19, 2), 0.5)
    y = np.zeros(19, dtype=int)

    with pytest.raises(ValueError, match="at least 20"):
        calibrate(probs, y, 0.1)


def test_exactly_twenty_examples_is_allowed():
    probs = np.full((20, 2), 0.5)
    y = np.zeros(20, dtype=int)

    assert calibrate(probs, y, 0.1) == pytest.approx(0.5)


def test_constant_scores_give_that_score():
    # p_y = 0.6 everywhere -> every score is 0.4.
    probs = np.full((20, 2), 0.2)
    probs[:, 0] = 0.6
    y = np.zeros(20, dtype=int)

    assert calibrate(probs, y, 0.10) == pytest.approx(0.4)


def test_quantile_level_exactly_one_returns_max_score():
    # n = 20, alpha = 0.05 -> ceil(21 * 0.95) = 20 -> level exactly 1.0.
    probs = np.full((20, 3), 0.1)
    probs[:, 0] = 0.8
    probs[:5, 0] = 0.3  # five larger scores of 0.7
    y = np.zeros(20, dtype=int)

    qhat = calibrate(probs, y, 0.05)

    assert qhat == pytest.approx(0.7)


def test_quantile_level_above_one_returns_one():
    # n = 20, alpha = 0.01 -> ceil(21 * 0.99) = 21 -> level 1.05 > 1.
    probs = np.full((20, 2), 0.5)
    y = np.zeros(20, dtype=int)

    assert calibrate(probs, y, 0.01) == 1.0


def test_quantile_uses_higher_method():
    # Scores 0.1..0.5 (n = 20 style set), alpha=0.5 -> level ceil(21*0.5)/20 = 11/20.
    scores = np.concatenate([np.full(10, 0.1), np.full(10, 0.5)])
    probs = np.zeros((20, 2))
    probs[:, 0] = 1.0 - scores  # p_y = 1 - score
    probs[:, 1] = 1.0 - probs[:, 0]
    y = np.zeros(20, dtype=int)

    qhat = calibrate(probs, y, 0.5)

    # level = 11/20 = 0.55 -> higher picks the smallest score >= the 55th
    # percentile of the ordered scores, i.e. 0.5.
    assert qhat == pytest.approx(0.5)


# --------------------------------------------------------------------------- #
# calibrate — validation
# --------------------------------------------------------------------------- #


def test_non_2d_probs_rejected():
    with pytest.raises(ValueError, match="2-dimensional"):
        calibrate(np.zeros(30), np.zeros(30, dtype=int), 0.1)


def test_mismatched_y_length_rejected():
    with pytest.raises(ValueError, match="one label per probability row"):
        calibrate(np.full((30, 2), 0.5), np.zeros(29, dtype=int), 0.1)


def test_label_out_of_range_rejected():
    y = np.zeros(30, dtype=int)
    y[0] = 2

    with pytest.raises(ValueError, match=r"outside \[0, K\)"):
        calibrate(np.full((30, 2), 0.5), y, 0.1)


def test_non_finite_probs_rejected():
    probs = np.full((30, 2), 0.5)
    probs[0, 0] = np.nan

    with pytest.raises(ValueError, match="finite"):
        calibrate(probs, np.zeros(30, dtype=int), 0.1)


@pytest.mark.parametrize("alpha", [0.0, 1.0, -0.1, 1.5])
def test_invalid_alpha_rejected(alpha):
    with pytest.raises(ValueError, match="alpha"):
        calibrate(np.full((30, 2), 0.5), np.zeros(30, dtype=int), alpha)


# --------------------------------------------------------------------------- #
# predict_set
# --------------------------------------------------------------------------- #


def test_predict_set_threshold_inclusive_on_ties():
    probs = [0.5, 0.4, 0.6, 0.5]
    labels = ["a", "b", "c", "d"]

    # qhat = 0.5 -> threshold 0.5 -> a, c, d (ties included, order preserved).
    assert predict_set(probs, 0.5, labels) == ("a", "c", "d")


def test_predict_set_preserves_label_order():
    probs = [0.9, 0.1, 0.8]
    labels = ["z", "y", "x"]

    # qhat = 1.0 -> threshold 0.0 -> every label, still in the original order.
    assert predict_set(probs, 1.0, labels) == ("z", "y", "x")


def test_predict_set_qhat_one_includes_everything():
    probs = [0.0, 0.3, 1.0]
    labels = ["a", "b", "c"]

    assert predict_set(probs, 1.0, labels) == ("a", "b", "c")


def test_predict_set_empty_when_nothing_passes():
    assert predict_set([0.1, 0.2], 0.0, ["a", "b"]) == ()


def test_predict_set_length_mismatch_rejected():
    with pytest.raises(ValueError, match="same length"):
        predict_set([0.1, 0.2], 0.1, ["a"])


def test_predict_set_bad_qhat_rejected():
    with pytest.raises(ValueError, match="qhat"):
        predict_set([0.1, 0.2], 1.5, ["a", "b"])


# --------------------------------------------------------------------------- #
# save / load
# --------------------------------------------------------------------------- #


def test_save_and_load_qhat_round_trip(tmp_path):
    path = tmp_path / "nested" / "qhat.json"

    save_qhat(path, 0.25, 0.10, 500)
    data = load_qhat(path)

    assert data == {"qhat": 0.25, "alpha": 0.10, "n": 500}


def test_load_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_qhat(tmp_path / "nope.json")


def test_load_malformed_file_raises(tmp_path):
    path = tmp_path / "qhat.json"
    path.write_text('{"qhat": 0.2}', encoding="utf-8")

    with pytest.raises(ValueError, match="missing"):
        load_qhat(path)


# --------------------------------------------------------------------------- #
# empirical coverage on synthetic calibrated draws (ticket acceptance)
# --------------------------------------------------------------------------- #


def _coverage(alpha: float, n_cal: int = 2000, n_test: int = 20000, k: int = 4):
    rng = np.random.default_rng(0)

    cal_probs = rng.dirichlet(np.ones(k), size=n_cal)
    cal_y = np.array([rng.choice(k, p=row) for row in cal_probs])
    qhat = calibrate(cal_probs, cal_y, alpha)

    test_probs = rng.dirichlet(np.ones(k), size=n_test)
    test_y = np.array([rng.choice(k, p=row) for row in test_probs])

    labels = [f"c{i}" for i in range(k)]
    covered = 0
    for row, truth in zip(test_probs, test_y):
        if labels[truth] in predict_set(row, qhat, labels):
            covered += 1

    return qhat, covered / n_test


@pytest.mark.parametrize("alpha", [0.05, 0.10, 0.20])
def test_empirical_coverage_matches_nominal(alpha):
    qhat, coverage = _coverage(alpha)

    assert 0.0 <= qhat <= 1.0
    assert 1.0 - alpha - 0.01 <= coverage <= 1.0 - alpha + 0.03
