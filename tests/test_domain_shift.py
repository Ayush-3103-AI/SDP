import numpy as np
import pytest
from caxton_fixture import load_script

domain_shift = load_script("domain_shift")


def test_centre_crop_matches_the_caxton_roi_fraction():
    img = np.zeros((720, 1280, 3), np.uint8)
    img[200:520, 480:800] = 255  # the centre 320 × 320
    c = domain_shift.centre_crop(img)
    assert c.shape == (320, 320, 3) and c.min() == 255


def test_stats_counts_sets_and_top1():
    labels = ("none", "flow_low", "flow_high")
    probs = np.array([[0.95, 0.03, 0.02],   # {none}
                      [0.50, 0.45, 0.05],   # {none, flow_low}
                      [0.34, 0.33, 0.33],   # empty
                      [0.10, 0.10, 0.80]])  # {flow_high}
    s = domain_shift.stats(probs, 0.6, labels)  # member iff p >= 0.4
    assert s["n"] == 4 and s["mean_size"] == pytest.approx(1.0)  # sizes 1, 2, 0, 1
    assert s["empty"] == pytest.approx(0.25) and s["full"] == 0
    assert s["top"] == {"none": 0.75, "flow_low": 0.0, "flow_high": 0.25}
    assert domain_shift.stats(np.full((2, 3), 1 / 3), 0.7, labels)["full"] == 1.0


def test_selftest_runs_end_to_end_on_synthetic_frames():
    assert domain_shift.main(["--selftest"]) == 0
