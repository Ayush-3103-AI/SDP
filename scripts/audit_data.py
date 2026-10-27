"""Data audit of the adapted CAXTON subset, with the K1′ kill check (T-0006; ADR-0009 §Metrics, 07 §14–15).

    python scripts/audit_data.py [--data data] [--provenance docs/data/CAXTON.md] [--out reports/data_audit.md]

Reads <data>/trials.csv, images.csv, adapt_counts.json and crops.csv (the last two if present). Line 1 of the
report is "K1′: PASS" or "K1′: FAIL (<reason>)".
"""
import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from xqi.config import load_causes

MIN_IMAGES, MIN_PRINTS, MIN_ACTIONABLE = 200, 5, 4  # K1′ (T-0006)
CLS_VAR = {"flow_cls": "flow", "speed_cls": "speed", "z_cls": "z_offset", "nozzle_cls": "nozzle_temp"}  # 07 §15


def licence_ok(text: str) -> bool:
    """The provenance file's Licence line has a value that is not the template's <...>."""
    m = re.search(r"^Licen[cs]e[^:\n]*:[ \t]*(\S.*)$", text, re.MULTILINE)
    return bool(m) and not m.group(1).startswith("<")


def deviations(images: pd.DataFrame) -> pd.Series:
    """Per image, the tuple of causes whose class is not good (07 §14 D(i)), in CLS_VAR order."""
    names = {col: (f"{var}_low", None, f"{var}_high") for col, var in CLS_VAR.items()}
    return pd.Series(
        [tuple(names[c][v] for c, v in zip(CLS_VAR, row) if v != 1) for row in images[list(CLS_VAR)].itertuples(False)],
        index=images.index, dtype=object,
    )


def segments(images: pd.DataFrame) -> int:
    """07 §14 segments: runs of constant D within a print, in ts order."""
    df = images.sort_values(["trial_id", "ts_s"], kind="stable")
    d = deviations(df)
    new = (d != d.shift()) | (df.trial_id != df.trial_id.shift())
    return int(new.sum())


def coverage(images: pd.DataFrame, causes) -> pd.DataFrame:
    """Per cause: single-cause images and prints, and multi images and prints it takes part in."""
    multi = images[images.cause == "multi"]
    d = deviations(multi)
    rows = []
    for c in causes:
        single = images[images.cause == c]
        m = multi[d.map(lambda t, c=c: c in t).astype(bool)]
        rows.append({"cause": c, "single_images": len(single), "single_prints": single.trial_id.nunique(),
                     "multi_images": len(m), "multi_prints": m.trial_id.nunique()})
    return pd.DataFrame(rows).set_index("cause")


def k1(cov: pd.DataFrame, cause_action: dict, licence: bool):
    """(first line, keep, drop) per T-0006: every failing cause is dropped at T-0007; PASS needs the licence
    and ≥ MIN_ACTIONABLE setpoint causes left."""
    ok = (cov.single_images >= MIN_IMAGES) & (cov.single_prints >= MIN_PRINTS)
    keep = ["none"] + [c for c in cov.index if c != "none" and ok[c]]
    drop = [c for c in cov.index if c != "none" and not ok[c]]
    n_act = sum(cause_action.get(c) is not None for c in keep)
    if not licence:
        line = "K1′: FAIL (licence line in docs/data/CAXTON.md not filled in)"
    elif n_act < MIN_ACTIONABLE:
        line = (f"K1′: FAIL (only {n_act} actionable causes have ≥ {MIN_IMAGES} single-cause images in "
                f"≥ {MIN_PRINTS} prints; need {MIN_ACTIONABLE})")
    else:
        line = "K1′: PASS"
    return line, keep, drop


def _table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return out + ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]


def render(images, trials, counts, crops, causes, licence) -> str:
    cov = coverage(images, [c for c in causes.causes if c != "none"])
    line, keep, drop = k1(cov, causes.cause_action, licence)
    n, n_single = len(images), int((~images.cause.isin(["none", "multi"])).sum())
    per = images.groupby("trial_id").size()
    lines = [line, "", "# CAXTON data audit (T-0006)", "",
             (f"Kept images: {n} in {images.trial_id.nunique()} prints ({len(trials)} rows in trials.csv). "
              f"K1′ threshold per cause: ≥ {MIN_IMAGES} single-cause images in ≥ {MIN_PRINTS} prints."), "",
             "## Images and prints per cause", ""]
    lines += _table(["cause", "single images", "single prints", "in multi images", "multi prints"],
                    [tuple(r) for r in cov.itertuples()])
    none, multi = images[images.cause == "none"], images[images.cause == "multi"]
    lines += ["", (f"none: {len(none)} images in {none.trial_id.nunique()} prints · "
                   f"multi: {len(multi)} images in {multi.trial_id.nunique()} prints"), "",
              "## Single-deviation share", "",
              f"Kept subset: {n_single} / {n} = {n_single / n:.1%} (the subset is stratified, so this is inflated)."]
    if counts:
        lab = counts["labelled_by_cause"]
        tot, single = sum(lab.values()), sum(v for k, v in lab.items() if k not in ("none", "multi"))
        lines.append(f"All labelled images before the subset: {single} / {tot} = {single / tot:.1%}.")
    lines += ["", "## Exclusions", ""]
    if counts:
        lines += [f"Images in the CSV: {counts['images_in']}", ""]
        lines += _table(["reason", "images"], counts["excluded"].items())
        if counts["keep_z_suspect"]:
            lines += ["", "z_offset < 0.08 mm rows were KEPT (--keep-z-suspect)."]
    else:
        lines.append("adapt_counts.json not present (re-run scripts/adapt_caxton.py).")
    lines += ["", "## Images per print", "",
              f"min {per.min()} · median {per.median():g} · max {per.max()} (kept images per print)", "",
              "## Segments", "", f"{segments(images)} segments of constant deviation set (07 §14) in the kept subset.",
              "", "## Missing crops", ""]
    if crops is None:
        lines.append("crops.csv not present (run scripts/build_crops.py).")
    else:
        miss = images[~images.image_path.isin(crops.image_path)]
        lines.append(f"{len(miss)} of {n} kept images have no crop.")
    lines += ["", "## Proposed frozen taxonomy (T-0007)", "", f"Keep: {', '.join(keep)}", ""]
    for c in drop:
        r = cov.loc[c]
        lines.append(f"- {c}: drop at T-0007 ({r.single_images} single-cause images in {r.single_prints} prints)")
    if not drop:
        lines.append("Drop: none")
    lines += ["", "The user and Dr. Meti confirm this before causes.yaml is edited (T-0007).", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data", help="folder with trials.csv, images.csv, crops.csv")
    ap.add_argument("--provenance", default="docs/data/CAXTON.md")
    ap.add_argument("--causes", default=str(ROOT / "config" / "causes.yaml"))
    ap.add_argument("--out", default="reports/data_audit.md")
    a = ap.parse_args(argv)
    data, prov = Path(a.data), Path(a.provenance)
    counts_file, crops_file = data / "adapt_counts.json", data / "crops.csv"
    text = render(
        pd.read_csv(data / "images.csv"), pd.read_csv(data / "trials.csv"),
        json.loads(counts_file.read_text(encoding="utf-8")) if counts_file.exists() else None,
        pd.read_csv(crops_file) if crops_file.exists() else None,
        load_causes(a.causes), prov.exists() and licence_ok(prov.read_text(encoding="utf-8")),
    )
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text.splitlines()[0])
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
