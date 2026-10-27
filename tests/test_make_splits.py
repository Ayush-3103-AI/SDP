import hashlib
import json
import subprocess

import pandas as pd
from caxton_fixture import load_script

make_splits = load_script("make_splits")

N_PRINTS = 12


def _data(tmp_path):
    data = tmp_path / "data"
    data.mkdir(parents=True)
    ids = [f"p{i}" for i in range(N_PRINTS)]
    pd.DataFrame({"trial_id": ids, "geometry": ids}).to_csv(data / "trials.csv", index=False)
    rows = []
    for i, t in enumerate(ids):  # print i: i + 1 single-cause images, plus none and multi rows that don't count
        rows += [(t, "flow_low")] * (i + 1) + [(t, "none")] * 7 + [(t, "multi")] * 3
    pd.DataFrame(rows, columns=["trial_id", "cause"]).to_csv(data / "images.csv", index=False)
    return data


def _run(data, *extra):
    return make_splits.main(["--data", str(data), "--out", str(data / "splits" / "logo.json"), *extra])


def test_folds_are_disjoint_complete_and_balanced(tmp_path):
    data = _data(tmp_path)
    assert _run(data) == 0
    s = json.loads((data / "splits" / "logo.json").read_text())
    assert (s["version"], s["kind"], s["seed"], len(s["folds"])) == (2, "leave-parts-out", 0, 5)
    every = {f"p{i}" for i in range(N_PRINTS)}
    tests = [t for f in s["folds"] for t in f["test_trials"]]
    assert sorted(tests) == sorted(every)  # each print in exactly one test fold
    for f in s["folds"]:
        tr, ca, te = set(f["train_trials"]), set(f["calib_trials"]), set(f["test_trials"])
        assert not (tr & ca or tr & te or ca & te) and tr | ca | te == every
        assert f["test_geometries"] == f["test_trials"]
        assert len(ca) == round(0.2 * (len(tr) + len(ca)))
    weight = [sum(int(t[1:]) + 1 for t in f["test_trials"]) for f in s["folds"]]
    assert max(weight) - min(weight) <= N_PRINTS  # greedy balance by single-cause count (total 78)
    assert s["sha256"] == {n: hashlib.sha256((data / n).read_bytes()).hexdigest() for n in ("trials.csv", "images.csv")}


def test_deterministic_for_a_seed(tmp_path):
    a, b = _data(tmp_path / "a"), _data(tmp_path / "b")
    assert _run(a) == 0 and _run(b) == 0
    assert (a / "splits" / "logo.json").read_text() == (b / "splits" / "logo.json").read_text()


def test_refuses_to_overwrite(tmp_path, capsys):
    data = _data(tmp_path)
    out = data / "splits" / "logo.json"
    assert _run(data) == 0
    before = out.read_text()
    assert _run(data, "--seed", "1") == 1 and out.read_text() == before
    assert "refusing" in capsys.readouterr().err
    assert _run(data, "--seed", "1", "--force") == 0  # not tracked by git yet → --force may overwrite
    assert json.loads(out.read_text())["seed"] == 1


def test_force_refused_once_tracked_by_git(tmp_path):
    data = _data(tmp_path)
    out = data / "splits" / "logo.json"
    assert _run(data) == 0
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "data/splits/logo.json"], cwd=tmp_path, check=True)
    before = out.read_text()
    assert _run(data, "--force") == 1 and out.read_text() == before


def test_too_few_prints(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    pd.DataFrame({"trial_id": ["p0", "p1"], "geometry": ["p0", "p1"]}).to_csv(data / "trials.csv", index=False)
    pd.DataFrame({"trial_id": ["p0", "p1"], "cause": ["none", "flow_low"]}).to_csv(data / "images.csv", index=False)
    assert _run(data) == 2
