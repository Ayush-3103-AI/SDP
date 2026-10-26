import sqlite3

import pytest

from xqi import study
from xqi.store import Store
from xqi.types import (
    CauseEstimate,
    CauseSet,
    ConfirmedDefect,
    EventVerdict,
    GateDecision,
    LayerResult,
    Proposal,
)

CAUSE_DEFECTS = {"flow_low": ("under_extrusion",), "nozzle_temp_high": ("stringing",)}


def make_run(root, run_id, n, cls="under_extrusion"):
    """A replayed run: n PROPOSE events with flow_low + nozzle_temp_low proposals, plus one critical event."""
    path = root / run_id / "events.sqlite"
    with Store(path) as store:
        store.write_run({"run_id": run_id, "mode": "advisory", "cfg": {"conformal": {"alpha": 0.1}}})
        for i in range(n + 1):
            d = f"{run_id}-d{i}"
            store.write_defect(ConfirmedDefect(d, cls, i, float(i), i + 0.5, 0.8, (0, 0, 10, 10), 0.01, 3, 0.4,
                                               critical=i == n))
            store.write_explanation(d, CauseEstimate({"flow_low": 0.7, "nozzle_temp_low": 0.3}, "flow_low", 0.7),
                                    CauseSet(("flow_low", "nozzle_temp_low"), 0.1, 0.6), 0.6, ["telemetry_stale"],
                                    i + 0.6)
            layers = (LayerResult("L2", True, "L2: +8 % within ±10"),)
            store.write_proposal(Proposal(f"{d}-flow_low", d, "flow_low", "flow", 100.0, 8.0, 108.0, ("M221 S108",),
                                          "Flow sentence."),
                                 GateDecision(f"{d}-flow_low", True, False, 8.0, 108.0, ("M221 S108",), layers))
            store.write_proposal(Proposal(f"{d}-nozzle_temp_low", d, "nozzle_temp_low", "nozzle_temp", 200.0, 4.0,
                                          204.0, ("M104 S204",), "Nozzle sentence."))
            store.write_verdict(EventVerdict(d, "PROPOSE", "two causes in the set", (f"{d}-flow_low",)), t_gate=i + 0.7)
    return path


@pytest.fixture
def runs(tmp_path):
    root = tmp_path / "runs"
    make_run(root, "r-flow", 3)
    make_run(root, "r-string", 2)  # under_extrusion boxes, but nozzle_temp_high only explains stringing: dropped
    make_run(root, "r-unlisted", 2)  # not in campaign.csv: dropped
    campaign = tmp_path / "campaign.csv"
    campaign.write_text("run_no,cause,mode,run_id\n1,flow_low,advisory,r-flow\n2,nozzle_temp_high,auto,r-string\n"
                        "3,flow_high,auto,\n", encoding="utf-8")
    return root, campaign


def test_block_order_counterbalanced_by_id_parity():
    assert study.block_order(2) == ("on", "off")
    assert study.block_order(7) == ("off", "on")
    orders = [study.block_order(p) for p in range(1, 21)]
    assert orders.count(("on", "off")) == orders.count(("off", "on")) == 10


def test_load_cards_joins_known_cause(runs):
    cards = study.load_cards(*runs, CAUSE_DEFECTS)
    assert [c["defect_id"] for c in cards] == ["r-flow-d0", "r-flow-d1", "r-flow-d2"]  # critical event excluded
    assert {(c["run_id"], c["known_cause"]) for c in cards} == {("r-flow", "flow_low")}
    assert [p["cause"] for p in cards[0]["proposals"]] == ["flow_low", "nozzle_temp_low"]


def test_card_selection_reproducible_per_seed():
    pool = [{"run_id": f"r{i % 3}", "defect_id": f"d{i}"} for i in range(40)]
    a = study.select_cards(pool, seed=0)
    assert a == study.select_cards(list(reversed(pool)), seed=0)  # independent of load order
    assert a != study.select_cards(pool, seed=1)
    assert [len(b) for b in a] == [12, 12]
    ids = [c["defect_id"] for b in a for c in b]
    assert len(set(ids)) == 24
    with pytest.raises(ValueError, match="24"):
        study.select_cards(pool[:23], seed=0)


def test_on_off_cards_differ_only_in_explanation(runs):
    card = study.load_cards(*runs, CAUSE_DEFECTS)[0]
    on, off = study.study_card(card, True), study.study_card(card, False)

    assert set(on) - set(off) == set(study.EXPLANATION_FIELDS)
    assert {k: v for k, v in on.items() if k != "proposals" and k in off} == {
        k: v for k, v in off.items() if k != "proposals"}
    for p_on, p_off in zip(on["proposals"], off["proposals"], strict=True):
        assert set(p_on) - set(p_off) == set(study.PROPOSAL_EXPLANATION_FIELDS)
        assert {k: p_on[k] for k in p_off} == p_off
    assert "remaining_s" not in on and "latency_s" not in on  # replayed cards have no timeout
    assert card["causes"] and card["proposals"][0]["counterfactual"]  # the source card is untouched


def rows(path, table):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(f"SELECT * FROM {table} ORDER BY id")]
    finally:
        conn.close()


def test_pilot_completes_both_blocks(runs, tmp_path, monkeypatch):
    """Done-when, CPU side: one participant runs both blocks; choices + surveys land in study.sqlite."""
    from streamlit.testing.v1 import AppTest

    out = tmp_path / "study.sqlite"
    root, campaign = runs
    monkeypatch.setattr("sys.argv", ["study.py", "--events", str(root), "--out", str(out), "--campaign",
                                     str(campaign), "--per-block", "1"])
    at = AppTest.from_file("../xqi/study.py").run(timeout=30)
    assert not at.exception
    at.number_input(key="participant").set_value(3)
    at.button(key="start").click().run(timeout=30)

    # block 1 (odd ID: explanation OFF): no cause, probability or counterfactual text
    text = " ".join(m.value for m in at.markdown)
    assert "Flow sentence." not in text and "two causes" not in text and "p=" not in " ".join(
        p.value for p in at.get("progress"))
    first = at.session_state["cards"][0]["proposals"][0]["proposal_id"]
    at.button(key=f"apply-{first}").click().run(timeout=30)
    at.button(key="survey-submit").click().run(timeout=30)

    # block 2 (ON): the explanation is back
    text = " ".join(m.value for m in at.markdown)
    assert "Flow sentence." in text and "two causes in the set" in text
    at.button(key=f"reject-{at.session_state['cards'][1]['defect_id']}").click().run(timeout=30)
    at.button(key="survey-submit").click().run(timeout=30)
    assert not at.exception
    assert "complete" in " ".join(s.value for s in at.success)

    choices = rows(out, "choices")
    assert [(c["participant"], c["block"], c["condition"], c["choice"], c["correct"]) for c in choices] == [
        (3, 1, "off", "apply", 1), (3, 2, "on", "reject", 0)]
    assert choices[0]["known_cause"] == choices[0]["chosen_cause"] == "flow_low"
    assert all(c["decision_s"] >= 0 for c in choices)
    surveys = rows(out, "surveys")
    assert [(s["block"], s["condition"]) for s in surveys] == [(1, "off"), (2, "on")]
    assert surveys[0]["tlx_mental"] == 50 and surveys[0]["trust_1"] == 4


def test_cli_launches_study(monkeypatch):
    from xqi.__main__ import main

    calls = []
    monkeypatch.setattr(study, "launch", lambda *a: calls.append(a) or 0)
    assert main(["study", "--events", "runs", "--out", "study.sqlite"]) == 0
    assert calls == [("runs", "study.sqlite", "docs/campaign.csv", 0)]
