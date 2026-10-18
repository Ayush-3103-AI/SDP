"""Audit the deck recipes against the safety envelope (T-0023).

Each ``DECK_RECIPES`` entry is pushed from the printer nominal through the gate
(L2 -> L1 -> L3) and the report records the raw Δ, the layer that clipped or
blocked it, and why. This is the "fixed recipes violate the envelope" result:
the recipes request edits larger than the per-action step, so the gate clips
them before dispatch.

Run from the repo root: ``python scripts/gate_audit.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xqi.config import load
from xqi.explain.counterfactual import recipe_to_proposals
from xqi.gate import gate
from xqi.types import DECK_RECIPES, GateDecision, PrinterState

REPORT = ROOT / "reports" / "recipe_audit.md"


def nominal_state(cfg) -> PrinterState:
    nominal = cfg.printer.nominal

    return PrinterState(
        ts=0.0,
        state="Printing",
        nozzle_actual_c=nominal["nozzle_temp"],
        nozzle_target_c=nominal["nozzle_temp"],
        bed_actual_c=nominal["bed_temp"],
        bed_target_c=nominal["bed_temp"],
        flow_pct=nominal["flow"],
        speed_pct=nominal["speed"],
        progress_pct=None,
        last_change_ts={},
    )


def layer_note(decision: GateDecision) -> tuple[str, str]:
    """Return ``(layer, detail)`` for the layer that blocked or clipped."""

    if not decision.passed:
        for layer in decision.layers:
            if not layer.passed:
                return layer.layer, layer.reason
        return "-", "rejected"

    if decision.clipped:
        for layer in decision.layers:
            if layer.layer == "L2":
                return "L2 (clipped)", layer.reason

    return "-", "within envelope"


def main() -> int:
    cfg = load(ROOT / "config" / "default.yaml")
    state = nominal_state(cfg)

    rows: list[tuple[str, str, float, float, str, str, str]] = []
    clipped = 0
    blocked = 0
    raw_outside = 0

    for defect in DECK_RECIPES:
        for proposal in recipe_to_proposals(defect, state, defect):
            decision = gate(proposal, state, now=1e9, cfg=cfg)
            layer, detail = layer_note(decision)

            lo3, hi3 = cfg.envelope.L3.window[proposal.var]
            raw_target = proposal.to_value
            l3_raw = "in" if lo3 <= raw_target <= hi3 else "out"

            if not decision.passed:
                blocked += 1
            elif decision.clipped:
                clipped += 1

            if l3_raw == "out":
                raw_outside += 1

            rows.append(
                (defect, proposal.var, proposal.delta, raw_target, l3_raw, layer, detail)
            )

    lines = [
        "# Deck-recipe audit (T-0023)",
        "",
        (
            "Each deck recipe is pushed from the printer nominal through the "
            "safety gate (L2 -> L1 -> L3). The table shows the raw recipe Δ, "
            "the raw recipe target against the L3 process window, and the layer "
            "that clipped or blocked the change."
        ),
        "",
        f"- variables audited: {len(rows)}",
        f"- raw targets outside the L3 window: {raw_outside}",
        f"- clipped by L2: {clipped}",
        f"- blocked: {blocked}",
        "",
        "| Recipe | Variable | Δ | Raw target | L3 | Layer | Detail |",
        "|---|---|---|---|---|---|---|",
    ]

    lines += [
        (
            f"| {defect} | {var} | {delta:+g} | {raw_target:g} | {l3} | "
            f"{layer} | {detail} |"
        )
        for defect, var, delta, raw_target, l3, layer, detail in rows
    ]

    lines += [
        "",
        (
            "Conclusion: the fixed deck recipes request edits larger than the "
            "per-action step and some raw recipe targets sit outside the L3 "
            "process window, so the recipes are not applied raw: the gate clips "
            "every oversized step and rejects any target that would leave the "
            "envelope."
        ),
        "",
    ]

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")

    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(
        f"variables={len(rows)} raw_outside_L3={raw_outside} "
        f"clipped={clipped} blocked={blocked}"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
