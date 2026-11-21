import pandas as pd
from caxton_fixture import load_script

clean = load_script("clean_labels")


def _raw():
    """Print 0: setpoints change at row 3; print 1 starts fresh. One bogus z, one near-boundary flow."""
    rows = []
    for i in range(6):
        flow = 100 if i < 3 else 150
        rows.append((f"caxton_dataset/print0/image-{i}.jpg", 0, f"2020-10-08T13:12:{50 + i:02d}-00", flow, 100,
                     0.02, 210, 209.0))
    for i in range(3):
        rows.append((f"caxton_dataset/print1/image-{i}.jpg", 1, f"2020-10-08T14:00:{10 + i:02d}-00", 128, 100,
                     -2.5 if i == 2 else 0.02, 210, 210.0))
    return pd.DataFrame(rows, columns=["img_path", "print_id", "timestamp", "flow_rate", "feed_rate", "z_offset",
                                       "target_hotend", "hotend"])


def test_age_counts_frames_since_any_setpoint_change_per_print():
    assert clean.annotate(_raw()).age.tolist() == [0, 1, 2, 0, 1, 2, 0, 1, 0]  # the z change resets it


def test_filters():
    a = clean.annotate(_raw())
    assert a.bogus_z.tolist() == [False] * 8 + [True]
    assert a.near_boundary.tolist() == [False] * 6 + [True] * 3  # flow 128 is within 5 pp of 130.5


def test_main_writes_clean_and_margin_files(tmp_path):
    raw = _raw()
    raw_csv = tmp_path / "raw.csv"
    raw.to_csv(raw_csv, index=False)
    crops = pd.DataFrame({"crop_path": [f"c{i}.jpg" for i in range(len(raw))], "image_path": raw.img_path,
                          "trial_id": "p" + raw.print_id.astype(str), "ts_s": range(len(raw)),
                          "cause": ["none"] * 3 + ["flow_high"] * 3 + ["none"] * 2 + ["z_offset_low"]})
    crops_csv = tmp_path / "crops.csv"
    crops.to_csv(crops_csv, index=False)
    out, margin, report = tmp_path / "clean.csv", tmp_path / "margin.csv", tmp_path / "audit.md"
    assert clean.main(["--csv", str(raw_csv), "--crops", str(crops_csv), "--out", str(out), "--margin-out",
                       str(margin), "--report", str(report), "--gap", "2"]) == 0
    kept = pd.read_csv(out)
    assert kept.crop_path.tolist() == ["c2.jpg", "c5.jpg"]  # gap drops ages 0–1 (c8 is bogus z too)
    assert list(kept.columns) == list(crops.columns)
    assert pd.read_csv(margin).crop_path.tolist() == ["c2.jpg", "c5.jpg"]
    assert "bogus_z" in report.read_text(encoding="utf-8")
