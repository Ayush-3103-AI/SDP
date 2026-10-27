"""The CAXTON sample (tests/fixtures/caxton_sample/): 40 label rows in the real column layout, prints 0, 1, 2 and 185.

Print 0: none ×4, flow_low ×4, speed_high ×2, multi ×2, one z < 0.08 mm row, nozzle_temp_high ×1.
Print 1: none ×6, z_offset_high ×4, speed_low ×2; its first nozzle sits at the frame corner (10, 715).
Print 2: nozzle_temp_low ×5, flow_high ×5. Print 185: none ×4 (excluded, print_id ≥ 183, no images).
"""
import importlib.util
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CSV = ROOT / "tests" / "fixtures" / "caxton_sample" / "caxton_sample.csv"


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_images(root: Path, csv: Path = SAMPLE_CSV) -> Path:
    """Write a 1280×720 JPEG for every sample row of prints < 183 under root; returns root."""
    df = pd.read_csv(csv)
    for r in df[df.print_id < 183].itertuples():
        img = np.full((720, 1280, 3), 40, np.uint8)
        x, y = int(r.nozzle_tip_x), int(r.nozzle_tip_y)
        img[max(y - 20, 0):y + 20, max(x - 20, 0):x + 20] = 255  # the "nozzle"
        path = root / r.img_path
        path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(path), img)
    return root


def adapt(tmp_path: Path, *extra) -> Path:
    """Images under tmp_path/raw, adapter output in tmp_path/data; returns the data dir."""
    raw, out = make_images(tmp_path / "raw"), tmp_path / "data"
    rc = load_script("adapt_caxton").main(["--csv", str(SAMPLE_CSV), "--root", str(raw), "--out", str(out), *extra])
    assert rc == 0
    return out
