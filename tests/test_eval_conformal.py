import json

import numpy as np
from caxton_fixture import load_script

eval_conformal = load_script("eval_conformal")

K, N = 4, 5000


def _split(rng, n):
    """Exchangeable calib/test: y drawn from the model's own probs, so split-conformal covers at 1 − α."""
    probs = rng.dirichlet(np.ones(K) * 0.7, n).astype(np.float32)
    y = np.minimum((rng.random((n, 1)) > probs.cumsum(1)).sum(1), K - 1)
    return probs, y


def _npz(path, rng, multi=0):
    pc, yc = _split(rng, N)
    pt, yt = _split(rng, N)
    yt[:multi] = -1  # multi rows are excluded
    np.savez(path, labels=np.array(["none", "flow_low", "flow_high", "speed_low"]), probs_calib=pc, y_calib=yc,
             probs_test=pt, y_test=yt, test_trial=np.array(["p"] * N))


def test_coverage_is_one_minus_alpha_and_qhat_is_saved(tmp_path):
    rng = np.random.default_rng(0)
    for k in range(2):
        _npz(tmp_path / f"preds_fold{k}.npz", rng, multi=50)
    _npz(tmp_path / "preds_final.npz", rng)
    out, qhat = tmp_path / "conformal.md", tmp_path / "qhat.json"
    assert eval_conformal.main(["--model-dir", str(tmp_path), "--out", str(out), "--qhat", str(qhat)]) == 0

    folds = eval_conformal.fold_results(tmp_path)
    assert len(folds) == 2
    for _, res in folds:
        for alpha, r in res.items():
            assert abs(r["coverage"] - (1 - alpha)) < 0.02, (alpha, r)
            assert r["n_test"] == N - 50

    q = json.loads(qhat.read_text())
    assert q["alpha"] == 0.10 and q["n"] == N and 0 < q["qhat"] < 1  # load_qhat format, cfg α
    text = out.read_text(encoding="utf-8")
    assert text.splitlines()[0].startswith("NFR-006: ")
    assert "## Coverage per cause" in text and "## Set sizes" in text


def test_no_final_preds_means_no_qhat(tmp_path, capsys):
    _npz(tmp_path / "preds_fold0.npz", np.random.default_rng(1))
    qhat = tmp_path / "qhat.json"
    assert eval_conformal.main(["--model-dir", str(tmp_path), "--out", str(tmp_path / "c.md"),
                                "--qhat", str(qhat)]) == 0
    assert not qhat.exists() and "preds_final.npz" in capsys.readouterr().out
