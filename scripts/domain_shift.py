"""Domain shift on the inherited camera roll (T-0067, FR-028; ADR-0009 D6). No training.

    python scripts/domain_shift.py --frames D:/reu/camera_roll [--n 500] [--seed 0] --out reports/domain_shift.md
    python scripts/domain_shift.py --selftest

final.pt + qhat.json (cfg.cause_model / cfg.conformal) on n seeded camera-roll frames, two views: the whole frame and a
centre crop with CAXTON's ROI fraction (320 px of a 720 px frame). Reports the top-1 cause distribution, mean set size
and the share of empty / full conformal sets, next to the same numbers on the CAXTON test prints (the out-of-fold
probs_test of models/cause/preds_fold*.npz, with the same qhat). The camera roll has no labels: this measures shift, not
accuracy.
"""
import argparse
import glob
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from xqi.config import load, load_causes
from xqi.explain import build_explainer
from xqi.types import EARLY_WARNING

ROI_FRAC = 320 / 720  # CAXTON crop side / frame height (ADR-0009)


def centre_crop(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    s = round(min(h, w) * ROI_FRAC)
    y0, x0 = (h - s) // 2, (w - s) // 2
    return img[y0:y0 + s, x0:x0 + s]


def stats(probs: np.ndarray, qhat: float, labels) -> dict:
    """Set sizes at qhat (member iff 1 − p ≤ qhat, 07 §5) and the top-1 share per cause."""
    size = (1.0 - probs <= qhat).sum(axis=1)
    top = np.bincount(probs.argmax(axis=1), minlength=len(labels)) / len(probs)
    return {"n": len(probs), "mean_size": float(size.mean()), "empty": float((size == 0).mean()),
            "full": float((size == len(labels)).mean()), "mean_ptop": float(probs.max(axis=1).mean()),
            "top": {c: float(t) for c, t in zip(labels, top)}}


def predict(model, frames, view) -> np.ndarray:
    return np.array([list(model.predict(view(f), EARLY_WARNING).probs.values()) for f in frames])


def reference(pattern: str, labels) -> np.ndarray | None:
    parts = []
    for f in sorted(glob.glob(pattern)):
        npz = np.load(f)
        if tuple(npz["labels"]) != tuple(labels):
            raise ValueError(f"{f}: labels {tuple(npz['labels'])} differ from the model's {tuple(labels)}")
        parts.append(npz["probs_test"])
    return np.concatenate(parts) if parts else None


def render(cols: dict, labels, qhat: float, n_frames: int, n_files: int, pattern: str) -> str:
    ref, cam = cols.get("CAXTON test"), cols["camera roll, centre crop"]
    head = (f"Domain shift: mean set size {cam['mean_size']:.2f} (camera roll, centre crop) vs "
            + (f"{ref['mean_size']:.2f} (CAXTON test prints)" if ref else "NO DATA (no CAXTON preds)"))
    names = list(cols)
    lines = [head, "", "# Domain shift on the inherited camera roll (T-0067)", "",
             f"Frames: {n_frames} sampled of {n_files} · qhat {qhat:.4f} · reference: {pattern}",
             ("The camera roll has no labels, so this measures shift (set size, empty/full sets, which causes win), "
              "not accuracy. Larger sets and more full sets = the model is less sure off its training domain."), "",
             "| | " + " | ".join(names) + " |", "|---" * (len(names) + 1) + "|"]
    rows = [("images", "n", "{:d}"), ("mean set size", "mean_size", "{:.2f}"), ("empty sets", "empty", "{:.1%}"),
            ("full sets (all causes)", "full", "{:.1%}"), ("mean top-1 p", "mean_ptop", "{:.3f}")]
    lines += [f"| {name} | " + " | ".join(fmt.format(cols[c][k]) for c in names) + " |" for name, k, fmt in rows]
    lines += ["", "## Top-1 cause share", "", "| cause | " + " | ".join(names) + " |", "|---" * (len(names) + 1) + "|"]
    lines += [f"| {c} | " + " | ".join(f"{cols[n]['top'][c]:.1%}" for n in names) + " |" for c in labels]
    return "\n".join(lines) + "\n"


def run(cfg, frames_dir: Path, pattern: str, n: int, seed: int) -> str:
    ex = build_explainer(cfg)
    if ex is None:
        raise SystemExit("no cause model: models/cause/final.pt and qhat.json are needed (T-0013, T-0015)")
    files = sorted(p for p in frames_dir.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    if not files:
        raise SystemExit(f"no images in {frames_dir}")
    pick = np.random.default_rng(seed).choice(len(files), min(n, len(files)), replace=False)
    frames = [f for f in (cv2.imread(str(files[i])) for i in sorted(pick)) if f is not None]
    labels = ex.labels
    cols = {"camera roll, whole frame": stats(predict(ex.cause_model, frames, lambda f: f), ex.qhat, labels),
            "camera roll, centre crop": stats(predict(ex.cause_model, frames, centre_crop), ex.qhat, labels)}
    ref = reference(pattern, labels)
    if ref is not None:
        cols["CAXTON test"] = stats(ref, ex.qhat, labels)
    return render(cols, labels, ex.qhat, len(frames), len(files), pattern)


def selftest() -> int:
    """5 synthetic frames, a random-init model on CPU, fake CAXTON preds → a complete report."""
    import torch  # noqa: F401 - checkpoint helpers below need it

    from xqi.explain.cause_model import build_model, save_checkpoint
    from xqi.explain.conformal import save_qhat

    cfg = load(ROOT / "config/default.yaml")
    causes = load_causes(cfg.causes_file).causes
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        (t / "frames").mkdir()
        rng = np.random.default_rng(0)
        for i in range(5):
            cv2.imwrite(str(t / "frames" / f"{i}.jpg"), rng.integers(0, 255, (720, 1280, 3), dtype=np.uint8))
        save_checkpoint(build_model(len(causes), 0, pretrained=False), t / "final.pt", causes=list(causes))
        save_qhat(t / "qhat.json", 0.9, 0.1, 100)
        np.savez(t / "preds_fold0.npz", labels=np.array(causes), probs_test=rng.dirichlet(np.ones(len(causes)), 50))
        cfg = replace(cfg, cause_model=replace(cfg.cause_model, weights=str(t / "final.pt"), device="cpu"),
                      conformal=replace(cfg.conformal, qhat_file=str(t / "qhat.json")))
        text = run(cfg, t / "frames", str(t / "preds_fold*.npz"), 500, 0)
    assert text.startswith("Domain shift: mean set size ") and "(CAXTON test prints)" in text, text
    assert "Frames: 5 sampled of 5" in text and "| none |" in text, text
    print("selftest ok")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", help="the camera-roll folder (D:/reu/camera_roll); never inside the repo")
    ap.add_argument("--config", default="config/default.yaml")
    ap.add_argument("--preds", default="models/cause/preds_fold*.npz", help="CAXTON out-of-fold test probs")
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="reports/domain_shift.md")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.frames:
        ap.error("--frames is required")
    text = run(load(a.config), Path(a.frames), a.preds, a.n, a.seed)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text.splitlines()[0])
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
