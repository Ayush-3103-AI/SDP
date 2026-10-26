"""Dashboard live view (FR-015, ADR-0005). Layout only; data comes from xqi/ui_data.py.

Read-only: this page never writes the store and never talks to OctoPrint.
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

        st.subheader("Last 50 events")
        st.dataframe(ui_data.last_events(store), hide_index=True)

    live()


if __name__ == "__main__":
    main()
