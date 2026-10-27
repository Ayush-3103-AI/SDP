"""The L3 process window from CAXTON's "good" class ranges (T-0024; 07 §3, 09 §Config envelope.L3).

    python scripts/derive_window.py [--images data/images.csv] [--config config/default.yaml]
        [--out reports/l3_window.md]

Per variable: the 1st–99th percentile of the logged setpoint over images whose class for that variable is good
(1). Bed stays at the config value (CAXTON bed is 60/65 °C only). The report proposes a config edit; the config
itself is changed in a separate commit after the user reads it.
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from xqi.config import load

# var → (logged setpoint column, class column). The gate acts on setpoints, so nozzle uses the target, not hotend.
VARS = {"flow": ("flow_pct", "flow_cls"), "speed": ("speed_pct", "speed_cls"),
        "nozzle_temp": ("nozzle_target_c", "nozzle_cls")}
ORDER = ("nozzle_temp", "bed_temp", "flow", "speed")  # config order


def derive(images: pd.DataFrame) -> dict[str, tuple[float, float, int]]:
    """{var: (p1, p99, n good images)}, numpy's default (linear) percentiles."""
    out = {}
    for var, (col, cls) in VARS.items():
        x = images.loc[images[cls] == 1, col].to_numpy(float)
        out[var] = (float(np.percentile(x, 1)), float(np.percentile(x, 99)), len(x))
    return out


def propose(derived: dict, cfg) -> dict[str, tuple[float, float]]:
    """Integer window rounded outward and clipped to L1 (L3 ⊆ L1 is a config rule); bed unchanged."""
    l1 = cfg.envelope.L1
    out = {"bed_temp": tuple(cfg.envelope.L3.window["bed_temp"])}
    for var, (lo, hi, _) in derived.items():
        lo1, hi1 = getattr(l1, var)
        out[var] = (max(math.floor(lo), int(lo1)), min(math.ceil(hi), int(hi1)))
    return out


def _fmt(w):
    return f"[{w[0]:g}, {w[1]:g}]"


def render(derived, proposed, cfg, images_path) -> str:
    cur, l1 = cfg.envelope.L3.window, cfg.envelope.L1
    lines = ["# L3 process window from CAXTON good-class ranges (T-0024)", "", f"Input: {images_path}", "",
             "## Derived window", "", "| var | p1 | p99 | good images | L1 |", "|---|---|---|---|---|"]
    for var, (lo, hi, n) in derived.items():
        lines.append(f"| {var} | {lo:.2f} | {hi:.2f} | {n} | {_fmt(getattr(l1, var))} |")
    lines += ["", "bed_temp: not derived (CAXTON bed is 60/65 °C only); the config value stays.", "",
              "## Current config window", "", f"material: {cfg.envelope.L3.material}"]
    lines += [f"- {v}: {_fmt(cur[v])}" for v in ORDER]
    lines += ["", "## Proposed config edit", "",
              "config/default.yaml, envelope.L3.window (rounded outward to integers, clipped to L1):", "", "```yaml"]
    lines += [f"{v}: {_fmt(proposed[v])}" for v in ORDER]
    lines += ["```", "", ("Changed in a separate commit after the user reads this report; the config loader checks "
                          "L3 ⊆ L1."), ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", default="data/images.csv")
    ap.add_argument("--config", default=str(ROOT / "config" / "default.yaml"))
    ap.add_argument("--out", default="reports/l3_window.md")
    a = ap.parse_args(argv)
    cfg = load(a.config)
    derived = derive(pd.read_csv(a.images))
    text = render(derived, propose(derived, cfg), cfg, a.images)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
