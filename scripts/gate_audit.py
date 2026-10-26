"""Push each DECK_RECIPE from nominal through the gate and write the recipe audit table (T-0023).

    python scripts/gate_audit.py --config config/default.yaml --out reports/recipe_audit.md
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from xqi.config import load
from xqi.explain.counterfactual import recipe_to_proposals
from xqi.gate import gate, l3_pass
from xqi.types import DECK_RECIPES, PrinterState


def audit(cfg) -> list[dict]:
    """One row per recipe variable: what the raw recipe breaks, and what the gate did with it."""
    n = cfg.printer.nominal
    state = PrinterState(
        0.0, "printing", n["nozzle_temp"], n["nozzle_temp"], n["bed_temp"], n["bed_temp"],
        n["flow"], n["speed"], None, {},
    )
    env = cfg.envelope
    rows = []
    for recipe in DECK_RECIPES:
        for p in recipe_to_proposals(recipe, state, recipe):
            v, x, target = p.var, p.from_value, p.to_value
            lo1, hi1 = getattr(env.L1, v)
            breaks = [name for name, bad in (
                ("step", abs(p.delta) > env.L2.step[v]),
                ("L1", not lo1 <= target <= hi1),
                ("L3", not l3_pass(x, target, env.L3.window[v])),
            ) if bad]
            d = gate(p, state, 0.0, cfg)
            hit = next((r for r in d.layers if not r.passed or "clipped" in r.reason), None)
            rows.append({
                "recipe": recipe, "var": v, "from": x, "target": target, "delta": p.delta,
                "raw_breaks": ", ".join(breaks), "passed": d.passed, "final": d.final_value,
                "layer": hit.layer if hit else "", "why": hit.reason if hit else d.layers[-1].reason,
            })
    return rows


def render(rows: list[dict]) -> str:
    lines = [
        "# Deck-recipe audit (T-0023)",
        "",
        "Each DECK_RECIPE pushed from the nominal setpoints through the gate (no cooldown pending).",
        "\"Raw recipe breaks\" is what baseline mode (APPLY_RAW) would send past: the L2 step limit, L1, or L3.",
        "",
        "| recipe | variable | from → target | Δ | raw recipe breaks | gate | layer | why |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        gate_col = f"pass → {r['final']:g}" if r["passed"] else "blocked"
        lines.append(
            f"| {r['recipe']} | {r['var']} | {r['from']:g} → {r['target']:g} | {r['delta']:+g} "
            f"| {r['raw_breaks'] or '–'} | {gate_col} | {r['layer'] or '–'} | {r['why']} |"
        )
    bad = sum(1 for r in rows if r["raw_breaks"])
    lines += ["", f"**{bad} of {len(rows)} fixed recipe changes violate the envelope as written.**", ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/default.yaml")
    ap.add_argument("--out", default="reports/recipe_audit.md")
    a = ap.parse_args()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(audit(load(a.config))), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
