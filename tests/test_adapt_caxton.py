import json

import pandas as pd
import pytest
from caxton_fixture import SAMPLE_CSV, adapt, load_script

adapt_caxton = load_script("adapt_caxton")

TRIALS_COLS = ["trial_id", "printer", "geometry", "material", "t_start_iso", "t_end_iso", "n_images", "n_kept", "source"]
IMAGES_COLS = ["image_path", "trial_id", "geometry", "ts_iso", "ts_s", "flow_pct", "speed_pct", "z_offset_mm",
               "nozzle_target_c", "nozzle_c", "bed_c", "flow_cls", "speed_cls", "z_cls", "nozzle_cls", "cause",
               "nozzle_x", "nozzle_y"]
KEPT = {"none": 10, "flow_low": 4, "flow_high": 5, "speed_low": 2, "speed_high": 2, "nozzle_temp_low": 5,
        "nozzle_temp_high": 1, "z_offset_high": 4, "multi": 2}


def _classes(flow=1, feed=1, z=1, hot=1):
    return {"flow_rate_class": flow, "feed_rate_class": feed, "z_offset_class": z, "hotend_class": hot}


@pytest.mark.parametrize("classes, cause", [
    (_classes(), "none"),
    (_classes(flow=0), "flow_low"), (_classes(flow=2), "flow_high"),
    (_classes(feed=0), "speed_low"), (_classes(feed=2), "speed_high"),
    (_classes(z=0), "z_offset_low"), (_classes(z=2), "z_offset_high"),
    (_classes(hot=0), "nozzle_temp_low"), (_classes(hot=2), "nozzle_temp_high"),
    (_classes(flow=2, hot=0), "multi"), (_classes(flow=0, feed=0, z=2, hot=2), "multi"),
])
def test_label_rule_truth_table(classes, cause):
    assert adapt_caxton.label(pd.DataFrame([classes])).tolist() == [cause]


def test_timestamp_hundredths():
    ts = adapt_caxton.parse_ts(pd.Series(["2020-10-08T13:12:50-49"]))
    assert ts[0] == pd.Timestamp("2020-10-08 13:12:50.490")


def test_fixture_csvs_columns_and_counts(tmp_path, capsys):
    out = adapt(tmp_path)
    trials, images = pd.read_csv(out / "trials.csv"), pd.read_csv(out / "images.csv")
    assert list(trials.columns) == TRIALS_COLS
    assert list(images.columns) == IMAGES_COLS
    assert trials.trial_id.tolist() == ["p0", "p1", "p2"]  # p185 excluded
    assert (trials.geometry == trials.trial_id).all() and set(trials.source) == {"caxton"}
    assert set(trials.material) == {"PLA"} and set(trials.printer) == {"unknown"}
    assert trials.n_images.tolist() == [14, 12, 10] and trials.n_kept.tolist() == [13, 12, 10]
    assert images.cause.value_counts().to_dict() == KEPT
    assert (images.z_offset_mm >= 0.08).all()
    p0 = images[images.trial_id == "p0"]
    assert p0.ts_s.iloc[0] == 0 and p0.ts_s.is_monotonic_increasing and p0.ts_s.iloc[1] == pytest.approx(0.4)
    assert p0.ts_iso.iloc[0] == "2020-10-08T13:12:50.490"
    assert images.image_path.iloc[0] == "caxton_dataset/print0/image-0.jpg"
    counts = json.loads((out / "adapt_counts.json").read_text())
    assert counts["images_in"] == 40 and counts["prints"] == 3 and counts["kept"] == 35
    assert counts["excluded"] == {"print_id>=183": 4, "z_offset<0.08": 1}
    assert counts["kept_by_cause"] == KEPT
    printed = capsys.readouterr().out
    assert "images in: 40" in printed and "z_offset<0.08: 1" in printed and "flow_low: 4" in printed


def test_keep_z_suspect(tmp_path):
    images = pd.read_csv(adapt(tmp_path, "--keep-z-suspect") / "images.csv")
    assert len(images) == 36 and images.cause.value_counts()["z_offset_low"] == 1


def test_stratified_subset_takes_rare_causes_whole_and_is_deterministic():
    df = pd.read_csv(SAMPLE_CSV)
    df = df[df.print_id == 0].assign(cause=lambda d: adapt_caxton.label(d), ts=lambda d: adapt_caxton.parse_ts(d.timestamp))
    df = df[df.z_offset >= 0.08]  # none 4, flow_low 4, speed_high 2, multi 2, nozzle_temp_high 1
    a = adapt_caxton.subset(df, 6, seed=0)
    assert len(a) == 6 and set(a.cause) == set(df.cause)  # every stratum survives
    assert a.ts.is_monotonic_increasing
    assert a.index.tolist() == adapt_caxton.subset(df, 6, seed=0).index.tolist()
    seeds = {tuple(adapt_caxton.subset(df, 6, seed=s).index) for s in range(10)}
    assert len(seeds) > 1  # the seed matters
    assert len(adapt_caxton.subset(df, 500, seed=0)) == len(df)


def test_per_print_cap(tmp_path):
    images = pd.read_csv(adapt(tmp_path, "--per-print", "5") / "images.csv")
    assert images.trial_id.value_counts().max() == 5


def test_missing_column_exits_2_naming_it(tmp_path, capsys):
    bad = tmp_path / "bad.csv"
    pd.read_csv(SAMPLE_CSV).drop(columns=["hotend_class", "nozzle_tip_x"]).to_csv(bad, index=False)
    rc = adapt_caxton.main(["--csv", str(bad), "--root", str(tmp_path / "raw"), "--out", str(tmp_path / "data")])
    assert rc == 2
    err = capsys.readouterr().err
    assert "hotend_class" in err and "nozzle_tip_x" in err
    assert not (tmp_path / "data").exists()


def test_unknown_class_value_exits_2(tmp_path, capsys):
    bad = tmp_path / "bad.csv"
    pd.read_csv(SAMPLE_CSV).assign(feed_rate_class=3).to_csv(bad, index=False)
    assert adapt_caxton.main(["--csv", str(bad), "--root", str(tmp_path / "raw"), "--out", str(tmp_path / "data")]) == 2
    assert "feed_rate_class" in capsys.readouterr().err


def test_list_needed(tmp_path):
    needed = tmp_path / "needed.txt"
    out = adapt(tmp_path, "--list-needed", str(needed))
    assert needed.read_text().split() == pd.read_csv(out / "images.csv").image_path.tolist()


def test_refuses_to_write_under_root(tmp_path):
    rc = adapt_caxton.main(["--csv", str(SAMPLE_CSV), "--root", str(tmp_path), "--out", str(tmp_path / "data")])
    assert rc == 2 and not (tmp_path / "data").exists()
