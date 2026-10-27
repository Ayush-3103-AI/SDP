"""Acceptance report: every 10-done matrix row → PASS / FAIL / NO DATA with its evidence (T-0046).

    uv run pytest --junitxml reports/pytest.xml        # the pytest result this script reads (default markers)
    python scripts/acceptance.py [--root .] [--junit reports/pytest.xml] [--out reports/acceptance.md]

Rows come from 10-done.md §Acceptance matrix; CHECKS says how each row is verified. A pytest check passes when the
junit file has a case of that test module or test function and none failed (all skipped or none found = NO DATA).
A report check reads the row's verdict line ("NFR-006: PASS ..." or "- NFR-001: PASS ..."); NFR-002/003 come from
reports/latency.md (or reports/demo.md once T-0066 writes them), as written there. Missing evidence is NO DATA and
never counts as PASS; a row is PASS only when every check is. The verdict section is 10-done §Verdict statement with
each bullet ticked when its row passes, and the domain-gap paragraph verbatim. Line 1 = the printed summary.
"""
import argparse
import re
import sys
import xml.etree.ElementTree as ET
from collections import namedtuple
from itertools import takewhile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DONE = ROOT / "project-context" / "10-done.md"
REQS = ROOT / "project-context" / "06-requirements.md"
SUITE_S, GATE_CASES = 120.0, 100_000  # NFR-009, NFR-004

Row = namedtuple("Row", "req verification evidence ticket")


def tests(*names):
    def check(ctx):
        if ctx["cases"] is None:
            return "NO DATA", "no junit file"
        hit = [c for c in ctx["cases"] if c[0] in names or c[1] in names]
        bad = [f"{m}::{f}" for m, f, s in hit if s == "failed"]
        if bad:
            return "FAIL", "failed: " + ", ".join(bad)
        ran = sum(s == "passed" for _, _, s in hit)
        return ("PASS", f"{ran} passed") if ran else ("NO DATA", f"no passing case of {', '.join(names)}")
    return check


def line(req, *paths):
    """The first `REQ: PASS|FAIL|NO DATA` line found in paths (relative to --root)."""
    pat = re.compile(rf"^(?:- )?{re.escape(req)}: (PASS|FAIL|NO DATA)\b.*$", re.MULTILINE)
    def check(ctx):
        for p in paths:
            f = ctx["root"] / p
            m = f.exists() and pat.search(f.read_text(encoding="utf-8"))
            if m:
                return m.group(1), f"{p}: {m.group(0).removeprefix('- ')}"
        return "NO DATA", f"no {req} line in {' / '.join(paths)}"
    return check


def exists(*patterns):
    """Any file (or folder) matching any of the glob patterns under --root."""
    def check(ctx):
        hit = next((p for p in patterns if any(ctx["root"].glob(p))), None)
        return ("PASS", f"{hit} present") if hit else ("NO DATA", f"missing: {' or '.join(patterns)}")
    return check


def gate(path="reports/gate_property.md"):
    def check(ctx):
        f = ctx["root"] / path
        m = f.exists() and re.search(r"\*\*Violations: (\d+) / (\d+)\*\*", f.read_text(encoding="utf-8"))
        if not m:
            return "NO DATA", f"no Violations line in {path}"
        v, n = int(m.group(1)), int(m.group(2))
        return ("FAIL" if v else "PASS" if n >= GATE_CASES else "NO DATA"), f"{path}: {v} violations / {n} cases"
    return check


def soak(path="reports/soak_T-0052.txt"):
    def check(ctx):
        f = ctx["root"] / path
        m = f.exists() and re.search(r"\b(PASSED|FAILED|ERROR) tests/test_soak.py::test_soak_2h", f.read_text(
            encoding="utf-8", errors="replace"))
        return ("PASS" if m.group(1) == "PASSED" else "FAIL", f"{path}: {m.group(0)}") if m else (
            "NO DATA", f"no test_soak_2h result in {path}")
    return check


def suite_time(ctx):
    t = ctx["time"]
    if t is None:
        return "NO DATA", "no junit file"
    return ("PASS" if t < SUITE_S else "FAIL"), f"suite {t:.1f} s (need < {SUITE_S:g} s)"


REPORTS = ["data_audit.md", "l3_window.md", "cause_floor.md", "cause_fold0.md", "cause_eval.md", "conformal.md",
           "counterfactual.md", "proactive.md", "gate_property.md", "recipe_audit.md", "latency.md", "demo.md",
           "soak_T-0052.txt"]  # 10-done §Finished artifact tree, MUST reports (not operator_study, domain_shift)

CHECKS = {
    "FR-001": [tests("test_modes")],
    "FR-002": [tests("test_camera")],
    "FR-003": [tests("test_detect", "test_detector_optional")],
    "FR-004": [tests("test_confirm")],
    "FR-005": [tests("test_critical_first")],
    "FR-006": [tests("test_severity")],
    "FR-007": [tests("test_cause_model")],
    "FR-008": [tests("test_conformal")],
    "FR-009": [tests("test_attribution"), exists("runs/*/heatmaps/*.png", "reports/img/demo_*.png")],
    "FR-010": [tests("test_sensors")],
    "FR-011": [tests("test_counterfactual")],
    "FR-012": [tests("test_gate", "test_gate_property"), gate()],
    "FR-013": [tests("test_event_verdict_table")],
    "FR-014": [tests("test_apply_updates_state")],
    "FR-015": [tests("test_ui_data"), exists("reports/img/ui_live.png")],
    "FR-016": [tests("test_ui_data"), exists("reports/img/ui_card.png")],
    "FR-017": [tests("test_modify_regated")],
    "FR-018": [tests("test_pause_stop")],
    "FR-019": [tests("test_timeout")],
    "FR-020": [tests("test_verify")],
    "FR-021": [tests("test_store")],
    "FR-022": [tests("test_timings_logged")],
    "FR-023": [tests("test_baseline_parity")],
    "FR-024": [exists(f"reports/{r}") for r in REPORTS],
    "FR-025": [tests("test_study"), exists("reports/study/*.sqlite", "reports/operator_study.md")],
    "FR-029": [tests("test_proactive")],
    "FR-030": [tests("test_early_warning_never_auto")],
    "FR-031": [tests("test_adapt_caxton", "test_build_crops"), exists("reports/data_audit.md")],
    "FR-032": [tests("test_printer_contract"), exists("docs/HANDOFF.md")],
    "NFR-001/011": [line("NFR-001", "reports/latency.md"), line("NFR-011", "reports/latency.md")],
    "NFR-002/003": [line("NFR-002", "reports/latency.md", "reports/demo.md"),
                    line("NFR-003", "reports/latency.md", "reports/demo.md")],
    "NFR-004": [gate(), line("NFR-004", "reports/demo.md")],
    "NFR-005": [line("NFR-005", "reports/cause_eval.md")],
    "NFR-006": [line("NFR-006", "reports/conformal.md")],
    "NFR-007": [line("NFR-007", "reports/counterfactual.md")],
    "NFR-008": [soak()],
    "NFR-009": [suite_time],
    "NFR-012": [line("NFR-012", "reports/proactive.md")],
}
# 10-done §Verdict statement bullet tag → the matrix row that carries it
BULLETS = {"S1": "NFR-005", "S2": "NFR-006", "S3": "NFR-004", "S4": "NFR-001/011", "S5": "NFR-012", "S6": "NFR-007",
           "S7": "FR-025", "FR-032": "FR-032"}


def section(text: str, title: str) -> list[str]:
    lines = text.splitlines()
    start = lines.index(f"## {title}") + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    return lines[start:end]


def matrix(done: Path) -> list[Row]:
    cells = [[c.strip() for c in r.strip().strip("|").split("|")]
             for r in section(done.read_text(encoding="utf-8"), "Acceptance matrix") if r.startswith("|")]
    return [Row(*c) for c in cells[2:]]


def priorities(reqs: Path) -> dict[str, str]:
    """FR id → MUST/SHOULD/... from 06 (NFRs have no priority column: MUST)."""
    out, req = {}, None
    for text in reqs.read_text(encoding="utf-8").splitlines():
        if m := re.match(r"(FR-\d+) \|", text):
            req = m.group(1)
        elif req and (m := re.match(r"\s+Priority:\s+(\S+)", text)):
            out[req], req = m.group(1), None
    return out


def junit(path: Path):
    """[(module, function, passed|failed|skipped)] and the suite time, or (None, None) without the file."""
    if not path.exists():
        return None, None
    root = ET.parse(path).getroot()
    cases = []
    for c in root.iter("testcase"):
        module = c.get("classname", "").split(".")[-1]
        status = ("failed" if c.find("failure") is not None or c.find("error") is not None
                  else "skipped" if c.find("skipped") is not None else "passed")
        cases.append((module, c.get("name", "").split("[")[0], status))
    suites = [root, *root.iter("testsuite")]
    return cases, max(float(s.get("time", 0)) for s in suites)


def combine(results) -> str:
    vs = [v for v, _ in results]
    return "FAIL" if "FAIL" in vs else "PASS" if vs and set(vs) == {"PASS"} else "NO DATA"


def _cell(s: str) -> str:
    return s.replace("|", "\\|")


def render(rows, verdicts, details, prio, done_text, junit_path) -> tuple[str, str]:
    count = {v: list(verdicts.values()).count(v) for v in ("PASS", "FAIL", "NO DATA")}
    must = [verdicts[r.req] for r in rows if prio.get(r.req, "MUST") == "MUST"]
    summary = (f"acceptance: {count['PASS']} PASS · {count['FAIL']} FAIL · {count['NO DATA']} NO DATA of {len(rows)} "
               f"matrix rows (MUST: {must.count('PASS')} PASS, {must.count('FAIL')} FAIL, "
               f"{must.count('NO DATA')} NO DATA)")
    lines = [summary, "", "# Acceptance report (T-0046)", "",
             (f"Generated by `scripts/acceptance.py` from 10-done.md §Acceptance matrix, the reports and the pytest "
              f"result `{junit_path}`. NO DATA = the evidence is missing; it never counts as PASS."), "",
             "## Acceptance matrix", "",
             "| Req | Priority | Verdict | Verification | Evidence | Ticket | Detail |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r.req} | {prio.get(r.req, 'MUST')} | {verdicts[r.req]} | {r.verification} | {r.evidence} | "
                     f"{r.ticket} | {_cell(details[r.req])} |")
    lines += ["", "## Verdict statement", ""]
    verdict = section(done_text, "Verdict statement")
    for i, text in enumerate(verdict):
        if text.startswith("- "):
            rest = "".join(takewhile(lambda t: t.startswith("  "), verdict[i + 1:]))  # a wrapped bullet's tag
            tag = re.search(r"\((S\d|FR-\d+)\)", text + rest)
            ok = tag and verdicts.get(BULLETS.get(tag.group(1))) == "PASS"
            text = f"- [{'x' if ok else ' '}] " + text[2:]
        lines.append(text)
    return summary, "\n".join(lines).rstrip() + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT), help="where reports/, docs/ and runs/ are looked up")
    ap.add_argument("--junit", default="reports/pytest.xml")
    ap.add_argument("--out", default="reports/acceptance.md")
    a = ap.parse_args(argv)
    cases, t = junit(Path(a.junit))
    ctx = {"root": Path(a.root), "cases": cases, "time": t}
    rows, verdicts, details = matrix(DONE), {}, {}
    for r in rows:
        results = [c(ctx) for c in CHECKS.get(r.req, [])] or [("NO DATA", "no check defined for this row")]
        verdicts[r.req] = combine(results)
        details[r.req] = "; ".join(d for _, d in results)
    summary, text = render(rows, verdicts, details, priorities(REQS), DONE.read_text(encoding="utf-8"), a.junit)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out}")
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
