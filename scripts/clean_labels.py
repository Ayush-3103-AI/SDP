"""Label hygiene for crops.csv from the CAXTON label CSV (CPU; 2026-11-21; reports/label_audit.md).

    python scripts/clean_labels.py --csv D:/caxton/caxton_dataset_filtered.csv [--crops data/crops.csv]
        [--out data/crops_clean.csv] [--margin-out data/crops_margin.csv] [--gap 15] [--z-min -0.5]
        [--margin-pct 5] [--margin-c 3] [--report reports/label_audit.md]

Row filters only: crops keep their paths and columns, data/splits/logo.json is untouched, nothing is re-cropped.
--out drops, from every split:
  bogus_z   z_offset < --z-min mm. CAXTON README: "very low values in Z offset ... are incorrectly labelled and
            should be ignored"; z ≤ −1 mm would put the nozzle into the bed. 98 % of single-cause z_offset_low
            images are these.
  gap       the first --gap frames after any setpoint change (flow, feed, z, target hotend) in a print: CAXTON's own
            classification3_gaps rule ("15 images, ~6 s ... until a parameter update is visible").
--margin-out further drops near_boundary rows: flow or speed within --margin-pct pp of a class edge (85.5 / 130.5 %)
or the measured hotend within --margin-c °C of 195 / 220 °C (CAXTON's hotend class is the measured temperature).
Meant for train_cause --train-rows only (cleaner training targets); scoring on it would move the goal posts.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SETPOINTS = ["flow_rate", "feed_rate", "z_offset", "target_hotend"]
PCT_EDGES, HOTEND_EDGES = (85.5, 130.5), (195.0, 220.0)


def annotate(raw: pd.DataFrame, z_min: float = -0.5, margin_pct: float = 5, margin_c: float = 3) -> pd.DataFrame:
    """raw label rows → (img_path, age, bogus_z, near_boundary), in (print, timestamp) order."""
    df = raw.sort_values(["print_id", "timestamp"], kind="stable").reset_index(drop=True)
    new_print = df.print_id.ne(df.print_id.shift())
    changed = new_print | df[SETPOINTS].ne(df[SETPOINTS].shift()).any(axis=1)
    age = df.groupby(changed.cumsum()).cumcount()

    def near(v, edges, w):
        return np.abs(v.to_numpy(float)[:, None] - np.array(edges)[None]).min(1) < w

    nb = near(df.flow_rate, PCT_EDGES, margin_pct) | near(df.feed_rate, PCT_EDGES, margin_pct) | near(
        df.hotend, HOTEND_EDGES, margin_c)
    return pd.DataFrame({"img_path": df.img_path, "age": age, "bogus_z": (df.z_offset < z_min).to_numpy(),
                         "near_boundary": nb})


def audit(crops: pd.DataFrame, keep: pd.Series, margin: pd.Series) -> str:
    single = crops.cause != "multi"
    rows = []
    for cause, g in crops[single].groupby("cause"):
        i = g.index
        rows.append(f"| {cause} | {len(g)} | {int(crops.bogus_z[i].sum())} | {int(crops.gap[i].sum())} | "
                    f"{int(keep[i].sum())} | {int(margin[i].sum())} |")
    n = int(single.sum())
    return "\n".join([
        "# Label audit (2026-11-21)", "",
        ("Single-cause rows of crops.csv. bogus_z = z_offset below the cut (CAXTON README: incorrectly labelled); "
         "gap = within CAXTON's post-change gap; clean = neither; margin = clean and no setpoint near a class edge "
         "(train rows only). Filters overlap, so columns don't add up."), "",
        "| cause | rows | bogus_z | gap | clean | margin |", "|---|---|---|---|---|---|", *rows,
        (f"| all | {n} | {int(crops.bogus_z[single].sum())} | {int(crops.gap[single].sum())} | "
         f"{int(keep[single].sum())} | {int(margin[single].sum())} |"), ""])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="caxton_dataset_filtered.csv")
    ap.add_argument("--crops", default="data/crops.csv")
    ap.add_argument("--out", default="data/crops_clean.csv")
    ap.add_argument("--margin-out", default="data/crops_margin.csv")
    ap.add_argument("--report", default="reports/label_audit.md")
    ap.add_argument("--gap", type=int, default=15)
    ap.add_argument("--z-min", type=float, default=-0.5)
    ap.add_argument("--margin-pct", type=float, default=5)
    ap.add_argument("--margin-c", type=float, default=3)
    a = ap.parse_args(argv)
    raw = pd.read_csv(a.csv, usecols=["img_path", "print_id", "timestamp", *SETPOINTS, "hotend"])
    crops = pd.read_csv(a.crops)
    cols = list(crops.columns)
    ann = annotate(raw, a.z_min, a.margin_pct, a.margin_c)
    crops = crops.merge(ann, left_on="image_path", right_on="img_path", how="left", validate="one_to_one")
    if crops.age.isna().any():
        print(f"{int(crops.age.isna().sum())} crops are not in {a.csv}", file=sys.stderr)
        return 2
    crops["gap"] = crops.age < a.gap
    keep = ~crops.bogus_z & ~crops.gap
    margin = keep & ~crops.near_boundary
    for path, mask in ((a.out, keep), (a.margin_out, margin)):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        crops.loc[mask, cols].to_csv(path, index=False)
    Path(a.report).parent.mkdir(parents=True, exist_ok=True)
    Path(a.report).write_text(audit(crops, keep, margin), encoding="utf-8")
    print(f"clean {int(keep.sum())} / {len(crops)} -> {a.out}; margin {int(margin.sum())} -> {a.margin_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
