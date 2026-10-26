import importlib.util
from pathlib import Path

from xqi import study

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("analyze_study", ROOT / "scripts" / "analyze_study.py")
analyze_study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analyze_study)


def test_selftest_planted_effect_ci_excludes_zero():
    assert analyze_study.selftest() == 0


def test_correct_rule_misalignment_wants_pause_or_stop():
    no_action = {"misalignment"}
    assert analyze_study.correct({"known_cause": "flow_low", "choice": "apply", "chosen_cause": "flow_low"}, no_action)
    assert not analyze_study.correct({"known_cause": "flow_low", "choice": "pause", "chosen_cause": None}, no_action)
    assert analyze_study.correct({"known_cause": "misalignment", "choice": "stop", "chosen_cause": None}, no_action)
    assert not analyze_study.correct({"known_cause": "misalignment", "choice": "reject", "chosen_cause": None},
                                     no_action)


def test_single_participant_report_states_n_and_underpowered(tmp_path):
    db = tmp_path / "pilot.sqlite"
    for blk, cond in enumerate(study.block_order(1), 1):
        for pos in range(1, 13):
            ok = cond == "on" or pos % 2 == 0
            study.record(db, "choices", {
                "participant": 1, "block": blk, "condition": cond, "position": pos, "run_id": "r",
                "defect_id": f"{cond}{pos}", "known_cause": "flow_low", "choice": "apply", "proposal_id": "p",
                "chosen_cause": "flow_low" if ok else "speed_high", "modified_delta": None, "correct": int(ok),
                "decision_s": 5.0, "wall_iso": "x"})
        study.record(db, "surveys", {"participant": 1, "block": blk, "condition": cond}
                     | {f"tlx_{k}": 40.0 for k in study.TLX} | {f"trust_{i}": 5 for i in range(1, 6)}
                     | {"wall_iso": "x"})
    rows = analyze_study.per_participant(*analyze_study.load(db), {"misalignment"})
    assert rows[1]["on"]["accuracy"] == 1.0 and rows[1]["off"]["accuracy"] == 0.5
    text = analyze_study.render(rows, analyze_study.excluded(rows, set()), str(db))
    assert "n = 1" in text and "underpowered" in text and "+7.7 pp" in text
    assert "+50.0 pp" in text
