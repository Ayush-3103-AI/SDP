import pandas as pd
from caxton_fixture import adapt, load_script

audit_data = load_script("audit_data")

LICENCE = "# CAXTON provenance\nLicence (copy the text from the record's box): CC BY 4.0\n"
TEMPLATE = "# CAXTON provenance\nLicence (copy the text from the record's \"Rights and licensing\" box): <...>\n"
CLS = {"flow": "flow_cls", "speed": "speed_cls", "z_offset": "z_cls", "nozzle_temp": "nozzle_cls"}


def _rows(cause, trial, n):
    """n images.csv rows of one single cause in one print."""
    cls = dict.fromkeys(CLS.values(), 1)
    if cause != "none":
        var, d = cause.rsplit("_", 1)
        cls[CLS[var]] = 0 if d == "low" else 2
    return [{"trial_id": trial, "ts_s": float(i), "cause": cause, **cls} for i in range(n)]


def _images(per_cause_print):
    """{cause: (n_prints, images per print)} → images.csv-like frame."""
    rows = []
    for cause, (n_prints, n) in per_cause_print.items():
        for p in range(n_prints):
            rows += _rows(cause, f"p{p}", n)
    return pd.DataFrame(rows)


def _run(tmp_path, images, provenance=LICENCE):
    data = tmp_path / "data"
    data.mkdir(exist_ok=True)
    images.to_csv(data / "images.csv", index=False)
    pd.DataFrame({"trial_id": sorted(set(images.trial_id))}).to_csv(data / "trials.csv", index=False)
    prov = tmp_path / "CAXTON.md"
    prov.write_text(provenance, encoding="utf-8")
    out = tmp_path / "data_audit.md"
    assert audit_data.main(["--data", str(data), "--provenance", str(prov), "--out", str(out)]) == 0
    return out.read_text(encoding="utf-8")


ACTIONABLE = ("flow_low", "flow_high", "speed_low", "speed_high", "nozzle_temp_low", "nozzle_temp_high")


def test_k1_pass_when_every_actionable_cause_is_covered(tmp_path):
    text = _run(tmp_path, _images({c: (5, 40) for c in ("none", *ACTIONABLE)}))
    assert text.splitlines()[0] == "K1′: PASS"
    assert "z_offset_low: drop at T-0007" in text  # no images → dropped, 6 actionable remain


def test_k1_fail_when_fewer_than_4_actionable_causes_remain(tmp_path):
    cover = {c: (5, 40) for c in ("none", *ACTIONABLE)}
    cover |= {"flow_low": (5, 39), "speed_low": (4, 60), "nozzle_temp_high": (1, 300)}  # 195 · 4 prints · 1 print
    text = _run(tmp_path, _images(cover))
    assert text.splitlines()[0].startswith("K1′: FAIL (only 3 actionable causes")
    for c in ("flow_low", "speed_low", "nozzle_temp_high"):
        assert f"{c}: drop at T-0007" in text


def test_k1_fail_without_licence(tmp_path):
    text = _run(tmp_path, _images({c: (5, 40) for c in ("none", *ACTIONABLE)}), provenance=TEMPLATE)
    assert text.splitlines()[0] == "K1′: FAIL (licence line in docs/data/CAXTON.md not filled in)"


def test_licence_line():
    assert audit_data.licence_ok(LICENCE)
    assert not audit_data.licence_ok(TEMPLATE)
    assert not audit_data.licence_ok("Licence:   \n")
    assert audit_data.licence_ok("License: CC BY 4.0 (Except where otherwise noted)")


def test_segments_count_changes_of_the_deviation_set():
    df = pd.DataFrame(_rows("none", "p0", 3) + _rows("flow_low", "p0", 2) + _rows("none", "p0", 1)
                      + _rows("speed_high", "p1", 2))
    df["ts_s"] = range(len(df))
    assert audit_data.segments(df) == 4


def test_runs_on_the_adapter_fixture_and_writes_every_section(tmp_path):
    data = adapt(tmp_path)
    prov = tmp_path / "CAXTON.md"
    prov.write_text(LICENCE, encoding="utf-8")
    out = tmp_path / "data_audit.md"
    assert audit_data.main(["--data", str(data), "--provenance", str(prov), "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert text.startswith("K1′: FAIL (only 0 actionable causes")  # 40 rows are far below 200 per cause
    for section in ("## Images and prints per cause", "## Single-deviation share", "## Exclusions",
                    "## Images per print", "## Segments", "## Missing crops", "## Proposed frozen taxonomy"):
        assert section in text
    assert "| z_offset<0.08 | 1 |" in text and "| print_id>=183 | 4 |" in text
    assert "| flow_low | 4 | 1 | 0 | 0 |" in text
    assert "| flow_high | 5 | 1 | 2 | 1 |" in text  # 5 single images in p2; flow_high is in p0's 2 multi rows
    assert "crops.csv not present" in text
