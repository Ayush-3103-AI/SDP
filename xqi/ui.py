"""Dashboard live view and proposal cards (FR-015/016, ADR-0005). Layout only; data comes from xqi/ui_data.py.

The only write is ui_data.insert_decision (an operator_decisions row); this page never talks to OctoPrint.
Start with `streamlit run xqi/ui.py -- --run <id|latest>` (or `launch(run)`).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REFRESH_S = 0.5


def launch(run: str, run_dir: str = "runs") -> int:
    """Back end of `python -m xqi ui --run R`."""
    cmd = [sys.executable, "-m", "streamlit", "run", __file__, "--", "--run", run, "--run-dir", run_dir]
    return subprocess.call(cmd)


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", default="latest")
    parser.add_argument("--run-dir", default="runs")
    return parser.parse_known_args()[0]


def main() -> None:
    import streamlit as st

    from xqi import ui_data
    from xqi.store import Store

    args = _args()
    st.set_page_config(page_title="XQI live", layout="wide")
    try:
        db = ui_data.resolve_run(args.run_dir, args.run)
    except FileNotFoundError as exc:
        st.error(f"Run not found: {exc}")
        return

    @st.cache_resource
    def open_store(path: Path) -> Store:
        return Store.open_readonly(path)

    store = open_store(db)
    frame_path = db.parent / ui_data.LATEST_FRAME
    st.title(f"XQI live: {db.parent.name}")

    @st.fragment(run_every=REFRESH_S)
    def live() -> None:
        for alert in ui_data.recent_alerts(store):
            st.error(f"{alert['kind']}: {alert['message']}  (t={alert['ts']:.1f})")

        left, right = st.columns([2, 1])
        try:
            left.image(frame_path.read_bytes(), caption="latest frame", width="stretch")
        except FileNotFoundError:
            left.info("Waiting for the first frame.")

        state = ui_data.latest_state(store)
        right.metric("Mode", ui_data.run_mode(store) or "-")
        if state is None:
            right.info("No telemetry yet.")
        else:
            right.metric("Printer", state["state"])
            right.metric("Nozzle (C)", f"{state['nozzle_actual_c']:.0f} / {state['nozzle_target_c']:.0f}")
            right.metric("Bed (C)", f"{state['bed_actual_c']:.0f} / {state['bed_target_c']:.0f}")
            right.metric("Flow / speed (%)", f"{state['flow_pct']:.0f} / {state['speed_pct']:.0f}")

        for event in store.pending_events():
            card = ui_data.card_model(store, event["defect_id"])
            if card is not None:
                proposal_card(card)

        st.subheader("Last 50 events")
        st.dataframe(ui_data.last_events(store), hide_index=True)

    def proposal_card(card: dict) -> None:
        """FR-016. Every button only inserts an operator_decisions row; the loop re-gates and acts."""
        d = card["defect_id"]

        def decide(choice: str, **kw) -> None:
            if ui_data.insert_decision(store, card, choice, operator, **kw) is not None:
                st.toast(f"{choice} sent for {d}")

        with st.container(border=True):
            left, right = st.columns([1, 2])
            left.markdown(f"**{card['cls']}** · severity {card['severity']:.2f} · `{d}`")
            images = [p for p in (card["crop_path"], card["heatmap_path"]) if p and Path(p).exists()]
            if images:
                left.image(images, width=160)
            if not card["heatmap_path"]:
                left.caption("Heatmap computing…")
            if card["remaining_s"] is not None:
                left.markdown(f"Timeout in **{card['remaining_s']:.0f} s**")

            alpha = f" (α = {card['alpha']:g})" if card["alpha"] is not None else ""
            right.markdown(f"**Cause set**{alpha}")
            for cause, p in card["causes"]:
                right.progress(p, text=f"{cause.replace('_', ' ')}  p={p:.2f}")
            flags = ", ".join(card["flags"]) or "No sensor flags"
            right.markdown(f"Sensor flags: {flags}")
            right.markdown(f"Not auto-applied: **{card['verdict']}**: {card['reason']}")

            for p in card["proposals"]:
                pid = p["proposal_id"]
                x, to = p["from_value"], p["final_value"]  # final_value: what the G-code would set
                layers = " ".join(f"{lay['layer']} {'✓' if lay['passed'] else '✗'}" for lay in p["layers"]) or "not gated"
                st.markdown(f"**{p['var']}** {x:g} → {to:g} {p['unit']} ({to - x:+g}). Gate: {layers}")
                for lay in p["layers"]:
                    st.caption(lay["reason"])
                st.markdown(p["counterfactual"])
                a, m, s = st.columns([1, 2, 1])
                if a.button("Apply", key=f"apply-{pid}", disabled=not operator):
                    decide("apply", proposal_id=pid)
                delta = m.number_input("Modify Δ", value=float(p["delta"]), key=f"delta-{pid}")
                if s.button("Modify", key=f"modify-{pid}", disabled=not operator):
                    decide("modify", proposal_id=pid, modified_delta=delta)

            r, pa, st_, c = st.columns(4)
            if r.button("Reject", key=f"reject-{d}", disabled=not operator):
                decide("reject")
            if pa.button("Pause", key=f"pause-{d}", disabled=not operator):
                decide("pause")
            confirm = c.checkbox("Confirm Stop (M112)", key=f"confirm-{d}")
            if st_.button("Stop", key=f"stop-{d}", type="primary", disabled=not operator):
                decide("stop", confirm=confirm)
                if not confirm:
                    st.warning("Tick 'Confirm Stop (M112)' first.")

    operator = st.sidebar.text_input("Operator", key="operator").strip()
    if not operator:
        st.sidebar.warning("Enter your name to enable the card buttons.")
    live()


if __name__ == "__main__":
    main()
