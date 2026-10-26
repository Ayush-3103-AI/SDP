"""Operator-study mode (FR-025): replay logged campaign events as cards, explanation ON vs OFF.

`python -m xqi study --events R --out S` runs `streamlit run xqi/study.py -- ...`. The page reuses ui.proposal_card,
but its buttons only write rows to study.sqlite: nothing goes to the run's store or to a printer.
Procedure, consent and exclusion rules: docs/study_protocol.md.
"""

from __future__ import annotations

import argparse
import csv
import random
import sqlite3
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from xqi import ui_data
from xqi.store import Store

CARDS_PER_BLOCK = 12
EXPLANATION_FIELDS = ("causes", "alpha", "flags", "heatmap_path", "verdict", "reason")
PROPOSAL_EXPLANATION_FIELDS = ("counterfactual", "layers")
LIVE_FIELDS = ("remaining_s", "latency_s")  # replayed cards have no timeout
TLX = {  # NASA-TLX raw (unweighted), 0-100 in steps of 5
    "mental": "Mental demand: how mentally demanding was the task?",
    "physical": "Physical demand: how physically demanding was the task?",
    "temporal": "Temporal demand: how hurried or rushed was the pace of the task?",
    "performance": "Performance: how successful were you at what you were asked to do? (0 = perfect, 100 = failure)",
    "effort": "Effort: how hard did you have to work to reach your level of performance?",
    "frustration": "Frustration: how insecure, discouraged, irritated, stressed or annoyed were you?",
}
TRUST = (  # [assumed] 5 items adapted from Jian et al. 2000 / Hoffman et al. 2018; 1 = strongly disagree, 7 = agree
    "The system's proposals are reliable.",
    "I am confident in the system's proposals.",
    "I understand why the system proposed what it did.",
    "I can depend on the system to propose a safe correction.",
    "I would accept the system's proposals on a real print.",
)

_EVENTS_SQL = """
SELECT defect_id FROM defects d
WHERE critical = 0 AND EXISTS (SELECT 1 FROM proposals p WHERE p.defect_id = d.defect_id)
ORDER BY t_conf
"""
_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS choices (
    id INTEGER PRIMARY KEY AUTOINCREMENT, participant INTEGER NOT NULL, block INTEGER NOT NULL,
    condition TEXT NOT NULL, position INTEGER NOT NULL, run_id TEXT NOT NULL, defect_id TEXT NOT NULL,
    known_cause TEXT NOT NULL, choice TEXT NOT NULL, proposal_id TEXT, chosen_cause TEXT, modified_delta REAL,
    correct INTEGER NOT NULL, decision_s REAL NOT NULL, wall_iso TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS surveys (
    id INTEGER PRIMARY KEY AUTOINCREMENT, participant INTEGER NOT NULL, block INTEGER NOT NULL,
    condition TEXT NOT NULL, {", ".join(f"tlx_{k} REAL NOT NULL" for k in TLX)},
    {", ".join(f"trust_{i} INTEGER NOT NULL" for i in range(1, len(TRUST) + 1))}, wall_iso TEXT NOT NULL
);
"""


def block_order(participant: int) -> tuple[str, str]:
    """Counterbalancing: even IDs see explanation ON first, odd IDs OFF first."""
    return ("on", "off") if participant % 2 == 0 else ("off", "on")


def load_cards(events: str | Path, campaign: str | Path, cause_defects: Mapping[str, Sequence[str]]) -> list[dict]:
    """Card models of every non-critical event with proposals in runs/<run_id>/events.sqlite under ``events``
    whose run has a cause in campaign.csv (run_id, cause columns) that explains the defect class (§Data label rule)."""
    with open(campaign, newline="", encoding="utf-8") as f:
        causes = {r["run_id"]: r["cause"] for r in csv.DictReader(f) if r.get("run_id") and r.get("cause")}
    cards = []
    for db in sorted(Path(events).glob(f"**/{ui_data.DB_NAME}")):
        cause = causes.get(db.parent.name)
        if cause is None:
            continue
        with Store.open_readonly(db) as store:
            for row in store.query(_EVENTS_SQL):
                card = ui_data.card_model(store, row["defect_id"])
                if card is not None and card["cls"] in cause_defects.get(cause, ()):
                    cards.append(card | {"run_id": db.parent.name, "known_cause": cause})
    return cards


def select_cards(cards: Sequence[dict], seed: int, per_block: int = CARDS_PER_BLOCK) -> list[list[dict]]:
    """Two disjoint blocks of ``per_block`` cards; the same seed gives the same blocks for every participant."""
    if len(cards) < 2 * per_block:
        raise ValueError(f"{len(cards)} events with a known cause; the study needs {2 * per_block}")
    pool = sorted(cards, key=lambda c: (c["run_id"], c["defect_id"]))
    chosen = random.Random(seed).sample(pool, 2 * per_block)
    return [chosen[:per_block], chosen[per_block:]]


def study_card(card: Mapping[str, Any], explain: bool) -> dict:
    """The card a participant sees. OFF drops the explanation: cause set, probabilities, flags, heatmap, verdict,
    gate reasons and counterfactual text. Frame/box, class and the proposal buttons stay."""
    drop = LIVE_FIELDS if explain else LIVE_FIELDS + EXPLANATION_FIELDS
    out = {k: v for k, v in card.items() if k not in drop}
    out["proposals"] = [
        {k: v for k, v in p.items() if explain or k not in PROPOSAL_EXPLANATION_FIELDS} for p in card["proposals"]
    ]
    return out


def record(out: str | Path, table: str, row: Mapping[str, Any]) -> None:
    """Append one row to study.sqlite (created on first use)."""
    conn = sqlite3.connect(out)
    try:
        conn.executescript(_SCHEMA)
        conn.execute(f"INSERT INTO {table} ({', '.join(row)}) VALUES ({', '.join('?' * len(row))})", tuple(row.values()))
        conn.commit()
    finally:
        conn.close()


def launch(events: str, out: str, campaign: str, seed: int) -> int:
    """Back end of `python -m xqi study --events R --out S`."""
    cmd = [sys.executable, "-m", "streamlit", "run", __file__, "--", "--events", events, "--out", out,
           "--campaign", campaign, "--seed", str(seed)]
    return subprocess.call(cmd)


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", default="runs")
    parser.add_argument("--out", default="study.sqlite")
    parser.add_argument("--campaign", default="docs/campaign.csv")
    parser.add_argument("--causes", default="config/causes.yaml")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--per-block", type=int, default=CARDS_PER_BLOCK)
    return parser.parse_known_args()[0]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def main() -> None:
    import streamlit as st

    from xqi.config import load_causes
    from xqi.ui import proposal_card

    args = _args()
    n = args.per_block
    ss = st.session_state
    st.set_page_config(page_title="XQI study", layout="wide")

    if "cards" not in ss:
        st.title("Operator study")
        pid = st.number_input("Participant ID", min_value=1, step=1, key="participant")
        if not st.button("Start", key="start"):
            return
        try:
            cards = load_cards(args.events, args.campaign, load_causes(args.causes).cause_defects)
            blocks = select_cards(cards, args.seed, n)
        except (OSError, ValueError) as exc:
            st.error(str(exc))
            return
        ss.pid, ss.cards, ss.pos, ss.surveys = int(pid), blocks[0] + blocks[1], 0, 0

    blk = ss.surveys
    if blk == 2:
        st.success("Study complete. Thank you.")
        return
    condition = block_order(ss.pid)[blk]
    base = {"participant": ss.pid, "block": blk + 1, "condition": condition}

    if ss.pos == (blk + 1) * n:  # block finished: NASA-TLX + trust
        st.title(f"Block {blk + 1} of 2: questionnaire")
        with st.form(f"survey-{blk}"):
            tlx = {f"tlx_{k}": st.slider(q, 0, 100, 50, 5, key=f"tlx-{blk}-{k}") for k, q in TLX.items()}
            trust = {f"trust_{i}": st.slider(q, 1, 7, 4, key=f"trust-{blk}-{i}") for i, q in enumerate(TRUST, 1)}
            if st.form_submit_button("Submit", key="survey-submit"):
                record(args.out, "surveys", base | tlx | trust | {"wall_iso": _now_iso()})
                ss.surveys += 1
                st.rerun()
        return

    card = ss.cards[ss.pos]
    if ss.get("shown") != ss.pos:
        ss.shown, ss.t_shown = ss.pos, time.monotonic()

    def decide(choice: str, proposal_id: str | None = None, modified_delta: float | None = None,
               confirm: bool = False) -> None:
        if choice == "stop" and not confirm:
            return
        chosen = next((p["cause"] for p in card["proposals"] if p["proposal_id"] == proposal_id), None)
        record(args.out, "choices", base | {
            "position": ss.pos - blk * n + 1, "run_id": card["run_id"], "defect_id": card["defect_id"],
            "known_cause": card["known_cause"], "choice": choice, "proposal_id": proposal_id,
            "chosen_cause": chosen, "modified_delta": modified_delta,
            "correct": int(choice in ("apply", "modify") and chosen == card["known_cause"]),
            "decision_s": time.monotonic() - ss.t_shown, "wall_iso": _now_iso(),
        })
        ss.pos += 1
        st.rerun()

    st.title(f"Block {blk + 1} of 2 · card {ss.pos - blk * n + 1} of {n}")
    st.caption("Choose what you would do about this defect. Nothing is sent to a printer.")
    proposal_card(study_card(card, condition == "on"), decide, enabled=True)


if __name__ == "__main__":
    main()
