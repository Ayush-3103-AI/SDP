from caxton_fixture import load_script

acceptance = load_script("acceptance")

JUNIT = """<?xml version="1.0" encoding="utf-8"?><testsuites><testsuite name="pytest" tests="4" time="42.0">
<testcase classname="tests.test_orchestrator" name="test_modes" time="0.1"/>
<testcase classname="tests.test_orchestrator" name="test_critical_first" time="0.1"><failure message="x"/></testcase>
<testcase classname="tests.test_gate" name="test_l2_clips" time="0.1"/>
<testcase classname="tests.test_gate_property" name="test_gate_property_1000" time="0.1"/>
<testcase classname="tests.test_printer_contract" name="test_estop[fake]" time="0.1"><skipped/></testcase>
</testsuite></testsuites>"""


def _run(tmp_path, capsys):
    out = tmp_path / "acceptance.md"
    assert acceptance.main(["--root", str(tmp_path), "--junit", str(tmp_path / "pytest.xml"), "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    rows = {r.req: r for r in acceptance.matrix(acceptance.DONE)}
    got = {line.split(" | ")[0].lstrip("| "): line.split(" | ")[2] for line in text.splitlines()
           if line.startswith("| ") and line.split(" | ")[0].lstrip("| ") in rows}
    assert got.keys() == rows.keys()  # every 10-done matrix row, once
    return text, got, capsys.readouterr().out.strip().splitlines()


def test_no_evidence_is_no_data_never_pass(tmp_path, capsys):
    text, got, printed = _run(tmp_path, capsys)
    assert set(got.values()) == {"NO DATA"}
    assert printed[-1].startswith(f"acceptance: 0 PASS · 0 FAIL · {len(got)} NO DATA")
    assert text.splitlines()[0] == printed[-1]
    assert "- [x]" not in text and text.count("- [ ]") == 8
    assert "CAXTON is a nozzle close-up on CR-20 Pro printers in PLA; another camera needs new data (T-0067)." in text


def test_reports_and_pytest_result_map_to_rows(tmp_path, capsys):
    (tmp_path / "pytest.xml").write_text(JUNIT, encoding="utf-8")
    rep = tmp_path / "reports"
    rep.mkdir()
    (rep / "conformal.md").write_text("NFR-006: PASS (coverage 0.900)\n\n# Conformal\n", encoding="utf-8")
    (rep / "proactive.md").write_text("NFR-012: FAIL (median 12.0 s)\n", encoding="utf-8")
    (rep / "cause_eval.md").write_text("K2: PASS (top-1 = floor + 12.0 pp)\nNFR-005: PASS (x)\n", encoding="utf-8")
    (rep / "latency.md").write_text("# Latency\n\n## Requirements\n\n- NFR-001: PASS (p95 12 ms)\n"
                                    "- NFR-002: NO DATA (n=0)\n- NFR-011: PASS (1.2 GB)\n", encoding="utf-8")
    (rep / "gate_property.md").write_text("# Gate\n\n**Violations: 0 / 100000** (5 dispatched)\n", encoding="utf-8")
    (rep / "soak_T-0052.txt").write_text("PASSED tests/test_soak.py::test_soak_2h\n1 passed\n", encoding="utf-8")
    text, got, _ = _run(tmp_path, capsys)

    assert got["FR-001"] == "PASS" and got["FR-005"] == "FAIL"     # junit pass / failure
    assert got["FR-002"] == "NO DATA"                             # no matching test case
    assert got["FR-032"] == "NO DATA"                             # skipped only, and no HANDOFF.md under root
    assert got["FR-012"] == "PASS"                                # test_gate + test_gate_property + 0 violations
    assert got["NFR-004"] == "NO DATA"                            # gate half PASS, replay half (demo.md) missing
    assert got["NFR-001/011"] == "PASS" and got["NFR-002/003"] == "NO DATA"  # NFR-003 line missing → NO DATA
    assert got["NFR-005"] == "PASS" and got["NFR-006"] == "PASS" and got["NFR-012"] == "FAIL"
    assert got["NFR-007"] == "NO DATA" and got["NFR-008"] == "PASS" and got["NFR-009"] == "PASS"
    assert "- [x] conformal coverage" in text and "- [ ] proactive warnings" in text
    assert "- [x] leave-parts-out cause top-1" in text


def test_gate_violations_fail(tmp_path, capsys):
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "gate_property.md").write_text("**Violations: 3 / 100000**\n", encoding="utf-8")
    (tmp_path / "reports" / "proactive.md").write_text("NFR-012: PASS (median 8.0 s)\n", encoding="utf-8")
    (tmp_path / "pytest.xml").write_text(JUNIT, encoding="utf-8")
    text, got, _ = _run(tmp_path, capsys)
    assert got["FR-012"] == "FAIL" and got["NFR-004"] == "FAIL"
    assert "- [x] proactive warnings" in text  # its (S5) tag is on the wrapped second line
