import numpy as np
import pandas as pd
import pytest
from caxton_fixture import ROOT, adapt, load_script

from xqi.config import load

derive_window = load_script("derive_window")
CFG = load(ROOT / "config" / "default.yaml")


def _images():
    good = pd.DataFrame({"flow_pct": np.arange(1, 102), "flow_cls": 1, "speed_pct": np.arange(50, 151),
                         "speed_cls": 1, "nozzle_target_c": np.linspace(200, 220, 101), "nozzle_cls": 1})
    # Rows whose class for a variable is not good never count for that variable.
    bad = pd.DataFrame({"flow_pct": [1000, -5], "flow_cls": [2, 0], "speed_pct": [999, 0], "speed_cls": [2, 0],
                        "nozzle_target_c": [300, 100], "nozzle_cls": [2, 0]})
    return pd.concat([good, bad], ignore_index=True)


def test_known_good_values_give_the_expected_percentiles():
    d = derive_window.derive(_images())
    assert d["flow"] == pytest.approx((2.0, 100.0, 101))
    assert d["speed"] == pytest.approx((51.0, 149.0, 101))
    assert d["nozzle_temp"] == pytest.approx((200.2, 219.8, 101))


def test_proposal_rounds_outward_keeps_bed_and_stays_inside_l1():
    d = derive_window.derive(_images())
    p = derive_window.propose(d, CFG)
    assert p["flow"] == (50, 100)  # floor(2) = 2 is clipped to L1's 50
    assert p["speed"] == (51, 149)
    assert p["nozzle_temp"] == (200, 220)
    assert p["bed_temp"] == CFG.envelope.L3.window["bed_temp"]


def test_runs_on_the_adapter_fixture(tmp_path):
    data = adapt(tmp_path)
    out = tmp_path / "l3_window.md"
    assert derive_window.main(["--images", str(data / "images.csv"), "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    for s in ("## Derived window", "## Current config window", "## Proposed config edit"):
        assert s in text
    assert "nozzle_temp: [210, 210]" in text  # every good-class fixture row is at 210 °C
