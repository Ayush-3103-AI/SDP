import json

import numpy as np
from caxton_fixture import load_script

recal = load_script("recalibrate")

K = 4
PRIOR = np.array([0.55, 0.25, 0.15, 0.05])


def _balanced_overconfident(rng, n):
    """y ~ PRIOR; the 'model' outputs p(y|x)/π(y), sharpened (what class-weighted CE that overfits gives)."""
    y = rng.choice(K, n, p=PRIOR)
    logits = rng.normal(0, 1, (n, K))
    logits[np.arange(n), y] += 1.0
    p_true = np.exp(logits + np.log(PRIOR))
    p_true /= p_true.sum(1, keepdims=True)
    y = np.array([rng.choice(K, p=q) for q in p_true])  # labels drawn from the true posterior
    out = np.exp(3 * (np.log(p_true) - np.log(PRIOR)))  # balanced, T = 1/3
    return (out / out.sum(1, keepdims=True)).astype(np.float32), y


def test_fit_undoes_class_weighting_and_overconfidence():
    rng = np.random.default_rng(0)
    p, y = _balanced_overconfident(rng, 6000)
    log_prior = recal.log_prior(y, K)
    t, tau = recal.fit(p, y, log_prior)
    assert 2.0 < t < 4.5 and 0.75 <= tau <= 1.25, (t, tau)
    q = recal.adjust(p, t, tau, log_prior)
    assert recal.nll(q, y) < recal.nll(p, y) - 0.2
    assert (q.argmax(1) == y).mean() > (p.argmax(1) == y).mean()


def test_identity_params_change_nothing():
    rng = np.random.default_rng(1)
    p = rng.dirichlet(np.ones(K), 50).astype(np.float32)
    np.testing.assert_allclose(recal.adjust(p, 1.0, 0.0, np.zeros(K)), p, atol=1e-6)


def test_window_is_causal_and_stays_inside_a_print_and_gap():
    p = np.array([[0.9, 0.1], [0.1, 0.9], [0.1, 0.9], [0.9, 0.1]], np.float32)
    trial = np.array(["a", "a", "a", "b"])
    ts = np.array([0.0, 0.5, 100.0, 0.0])
    w = recal.window(p, trial, ts, k=3, max_gap_s=10)
    np.testing.assert_allclose(w[0], p[0], atol=1e-6)  # nothing before it
    assert abs(w[1, 0] - w[1, 1]) < 1e-6  # mean of rows 0 and 1 → equal
    np.testing.assert_allclose(w[2], p[2], atol=1e-6)  # 99.5 s gap resets the window
    np.testing.assert_allclose(w[3], p[3], atol=1e-6)  # new print resets it


def test_main_writes_recalibrated_preds_and_params(tmp_path):
    rng = np.random.default_rng(2)
    src, dst = tmp_path / "src", tmp_path / "dst"
    src.mkdir()
    labels = np.array(["none", "a", "b", "c"])
    for name in ("preds_fold0", "preds_final"):
        pc, yc = _balanced_overconfident(rng, 3000)
        pt, yt = _balanced_overconfident(rng, 0 if name == "preds_final" else 2000)
        yc[:30] = -1  # multi rows are kept in the npz but not fitted on
        n_c, n_t = len(yc), len(yt)
        np.savez(src / f"{name}.npz", labels=labels, probs_calib=pc, y_calib=yc,
                 calib_trial=np.array([f"p{i % 20}" for i in range(n_c)]), calib_ts=np.arange(n_c, dtype=float),
                 probs_test=pt.reshape(-1, K), y_test=yt, test_trial=np.array(["t"] * n_t),
                 test_ts=np.arange(n_t, dtype=float), test_cls=np.zeros((n_t, 4), int))
    report = tmp_path / "recal.md"
    assert recal.main(["--model-dir", str(src), "--out-dir", str(dst), "--report", str(report)]) == 0

    params = json.loads((dst / "calibration.json").read_text())
    assert set(params) == {"fold0", "final"} and len(params["final"]["log_prior"]) == K
    d = np.load(dst / "preds_fold0.npz")
    assert set(d.files) == set(np.load(src / "preds_fold0.npz").files)
    np.testing.assert_allclose(d["probs_test"].sum(1), 1, atol=1e-5)
    assert recal.nll(d["probs_calib"][30:], d["y_calib"][30:]) < recal.nll(
        np.load(src / "preds_fold0.npz")["probs_calib"][30:], d["y_calib"][30:])
    assert "cross-fit" in report.read_text(encoding="utf-8")


def test_temperature_only_keeps_the_argmax(tmp_path):
    rng = np.random.default_rng(3)
    src = tmp_path / "src"
    src.mkdir()
    pc, yc = _balanced_overconfident(rng, 2000)
    np.savez(src / "preds_final.npz", labels=np.array(list("wxyz")), probs_calib=pc, y_calib=yc,
             probs_test=np.zeros((0, K), np.float32), y_test=np.zeros(0, int))
    assert recal.main(["--model-dir", str(src), "--out-dir", str(tmp_path / "d"), "--report", str(tmp_path / "r.md"),
                       "--temperature-only"]) == 0
    assert json.loads((tmp_path / "d" / "calibration.json").read_text())["final"]["tau"] == 0.0
    q = np.load(tmp_path / "d" / "preds_final.npz")["probs_calib"]
    assert (q.argmax(1) == pc.argmax(1)).all()
