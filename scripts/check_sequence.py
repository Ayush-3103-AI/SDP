"""Check that 11-tickets/SEQUENCE.md lists every ticket once and never puts a ticket before its dependencies."""
import re
import sys
from pathlib import Path

TICKETS = Path(__file__).resolve().parent.parent / "project-context" / "11-tickets"


def main() -> int:
    deps = {}
    for f in TICKETS.glob("T-*.md"):
        text = f.read_text(encoding="utf-8")
        deps[f.stem] = re.findall(r"T-\d{4}", re.search(r"Depends on:\s*(.*)", text).group(1))
    seq = re.findall(r"^\| \d+ \| \[#\d+\]\([^)]*\) (T-\d{4})", (TICKETS / "SEQUENCE.md").read_text(encoding="utf-8"), re.MULTILINE)
    pos = {t: i for i, t in enumerate(seq)}
    errors = [f"missing from sequence: {t}" for t in sorted(set(deps) - set(pos))]
    errors += [f"listed twice: {t}" for t in sorted({t for t in seq if seq.count(t) > 1})]
    errors += [f"{t} (step {pos[t] + 1}) comes before its dependency {d}" for t in seq for d in deps.get(t, []) if pos.get(d, -1) > pos[t]]
    print("\n".join(errors) or f"OK: {len(seq)} tickets, dependency order holds")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
