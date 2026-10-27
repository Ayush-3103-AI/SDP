"""CAXTON label CSV → data/trials.csv + data/images.csv (T-0005; 08 P8, 07 §15, 09 §Data).

    python scripts/adapt_caxton.py --csv D:/caxton/caxton_dataset_filtered.csv --root D:/caxton --out data
        [--per-print 500] [--seed 0] [--keep-z-suspect] [--list-needed needed.txt]

Reads the CSV only: it never opens an image, never writes under --root and never touches the network.
Also writes <out>/adapt_counts.json (the printed counts) for the audit (T-0006).
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REQUIRED = ("img_path", "timestamp", "flow_rate", "feed_rate", "z_offset", "target_hotend", "hotend", "bed",
            "nozzle_tip_x", "nozzle_tip_y", "print_id", "flow_rate_class", "feed_rate_class", "z_offset_class",
            "hotend_class")
CLASS_VAR = {"flow_rate_class": "flow", "feed_rate_class": "speed", "z_offset_class": "z_offset",
             "hotend_class": "nozzle_temp"}  # 07 §15; 0 = low, 1 = good, 2 = high
FIRST_EXCLUDED_PRINT = 183  # prints 183–191: large errors / poor lighting (the authors exclude them too)
Z_SUSPECT_MM = 0.08  # README: lower Z offsets are incorrectly labelled
TRIALS_COLS = ["trial_id", "printer", "geometry", "material", "t_start_iso", "t_end_iso", "n_images", "n_kept",
               "source"]
IMAGES = {  # 09 §Data images.csv column ← CAXTON column, in order
    "image_path": "img_path", "trial_id": None, "geometry": None, "ts_iso": None, "ts_s": None,
    "flow_pct": "flow_rate", "speed_pct": "feed_rate", "z_offset_mm": "z_offset", "nozzle_target_c": "target_hotend",
    "nozzle_c": "hotend", "bed_c": "bed", "flow_cls": "flow_rate_class", "speed_cls": "feed_rate_class",
    "z_cls": "z_offset_class", "nozzle_cls": "hotend_class", "cause": None, "nozzle_x": "nozzle_tip_x",
    "nozzle_y": "nozzle_tip_y",
}


def label(df: pd.DataFrame) -> pd.Series:
    """07 §15: all four classes good → none; exactly one not good → <var>_low/_high; more → multi."""
    bad = df[list(CLASS_VAR)] != 1
    n_bad = bad.sum(axis=1)
    cause = pd.Series("multi", index=df.index, dtype=object)
    cause[n_bad == 0] = "none"
    for col, var in CLASS_VAR.items():
        one = (n_bad == 1) & bad[col]
        cause[one] = np.where(df.loc[one, col] == 0, f"{var}_low", f"{var}_high")
    return cause


def parse_ts(s: pd.Series) -> pd.Series:
    """CAXTON timestamps look like 2020-10-08T13:12:50-49: the last two digits are hundredths of a second."""
    t = pd.to_datetime(s.str[:19], format="%Y-%m-%dT%H:%M:%S")
    return t + pd.to_timedelta(s.str[20:].astype(int) * 10, unit="ms")


def subset(df: pd.DataFrame, per_print: int, seed: int) -> pd.DataFrame:
    """Per print, at most per_print rows stratified by cause (multi and none are strata too).

    Strata are filled smallest first with an equal share of what is left, so a rare cause is taken whole and the
    unused budget passes to the larger ones. A stratum over its share gets a seeded random sample. Output is in
    (print, ts) order.
    """
    rng = np.random.default_rng(seed)
    keep = []
    for _, g in df.groupby("print_id", sort=True):
        strata = sorted(g.groupby("cause").groups.items(), key=lambda kv: (len(kv[1]), kv[0]))
        budget = per_print
        for i, (_, idx) in enumerate(strata):
            share = budget // (len(strata) - i)
            take = list(idx) if len(idx) <= share else list(rng.choice(idx, share, replace=False))
            keep += take
            budget -= len(take)
    return df.loc[keep].sort_values(["print_id", "ts"], kind="stable")


def adapt(raw: pd.DataFrame, per_print: int, seed: int, keep_z_suspect: bool):
    """Returns (trials, images, counts)."""
    df = raw.assign(ts=parse_ts(raw.timestamp.astype(str)))
    excluded = {"print_id>=183": int((df.print_id >= FIRST_EXCLUDED_PRINT).sum())}
    df = df[df.print_id < FIRST_EXCLUDED_PRINT]
    per = df.groupby("print_id").ts.agg(["min", "max", "size"])  # print span and size before the z filter
    z_bad = df.z_offset < Z_SUSPECT_MM
    excluded["z_offset<0.08"] = 0 if keep_z_suspect else int(z_bad.sum())
    if not keep_z_suspect:
        df = df[~z_bad]
    df = df.assign(cause=label(df))
    kept = subset(df, per_print, seed)

    trial = "p" + kept.print_id.astype(int).astype(str)
    t0 = kept.print_id.map(per["min"])
    images = pd.DataFrame({
        k: kept[v] if v else None for k, v in IMAGES.items()
    }).assign(
        trial_id=trial, geometry=trial, ts_iso=kept.ts.dt.strftime("%Y-%m-%dT%H:%M:%S.%f").str[:-3],
        ts_s=(kept.ts - t0).dt.total_seconds().round(3), cause=kept.cause,
    )[list(IMAGES)]

    n_kept = kept.groupby("print_id").size()
    ids = n_kept.index
    trials = pd.DataFrame({
        "trial_id": "p" + ids.astype(str), "printer": "unknown", "geometry": "p" + ids.astype(str),
        "material": "PLA",
        "t_start_iso": per.loc[ids, "min"].dt.strftime("%Y-%m-%dT%H:%M:%S.%f").str[:-3].to_numpy(),
        "t_end_iso": per.loc[ids, "max"].dt.strftime("%Y-%m-%dT%H:%M:%S.%f").str[:-3].to_numpy(),
        "n_images": per.loc[ids, "size"].to_numpy(), "n_kept": n_kept.to_numpy(), "source": "caxton",
    })[TRIALS_COLS]

    def by_cause(s):
        return {k: int(v) for k, v in s.value_counts().sort_index().items()}

    counts = {
        "prints": len(trials), "images_in": len(raw), "excluded": excluded,
        "labelled_by_cause": by_cause(df.cause), "kept": len(images), "kept_by_cause": by_cause(images.cause),
        "per_print": per_print, "seed": seed, "keep_z_suspect": keep_z_suspect,
    }
    return trials, images, counts


def _under(path: Path, root: Path) -> bool:
    return path.resolve().is_relative_to(root.resolve())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="caxton_dataset_filtered.csv")
    ap.add_argument("--root", required=True, help="the folder holding caxton_dataset/ (read-only)")
    ap.add_argument("--out", default="data")
    ap.add_argument("--per-print", type=int, default=500)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--keep-z-suspect", action="store_true", help=f"keep z_offset < {Z_SUSPECT_MM} mm rows")
    ap.add_argument("--list-needed", help="write the kept img_path values here, one per line")
    a = ap.parse_args(argv)
    out, root = Path(a.out), Path(a.root)
    if _under(out, root) or (a.list_needed and _under(Path(a.list_needed), root)):
        print(f"refusing to write under --root {root}", file=sys.stderr)
        return 2

    raw = pd.read_csv(a.csv)
    missing = [c for c in REQUIRED if c not in raw.columns]
    if missing:
        print(f"missing columns: {', '.join(missing)}", file=sys.stderr)
        return 2
    odd = [c for c in CLASS_VAR if not raw[c].isin([0, 1, 2]).all()]
    if odd:  # the class encoding is a PAIR question (T-0005), never a guess
        print(f"class columns with values outside {{0, 1, 2}}: {', '.join(odd)}", file=sys.stderr)
        return 2

    trials, images, counts = adapt(raw, a.per_print, a.seed, a.keep_z_suspect)
    out.mkdir(parents=True, exist_ok=True)
    trials.to_csv(out / "trials.csv", index=False)
    images.to_csv(out / "images.csv", index=False)
    (out / "adapt_counts.json").write_text(json.dumps(counts, indent=2), encoding="utf-8")
    if a.list_needed:
        Path(a.list_needed).write_text("".join(p + "\n" for p in images.image_path), encoding="utf-8")

    print(f"prints: {counts['prints']}")
    print(f"images in: {counts['images_in']}")
    for k, v in counts["excluded"].items():
        print(f"excluded {k}: {v}")
    print(f"kept: {counts['kept']}")
    for k, v in counts["kept_by_cause"].items():
        print(f"  {k}: {v}")
    print(f"wrote {out / 'trials.csv'}, {out / 'images.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
