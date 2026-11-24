"""Demo core: real cause model + Grad-CAM + proposals + safety gate, packaged as JSON-ready dicts for the web UI."""
from __future__ import annotations

import base64
import sys
import time
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from xqi.config import load
from xqi.explain.cause_model import CauseModel, to_input
from xqi.explain.counterfactual import UNIT, make_proposal
from xqi.gate import gate
from xqi.types import CAUSE_ACTION, CAUSES, MANUAL_ADVICE, PrinterState

SHOW_PX = 512

# What the operator would see, and why it happens (extrusion physics; high Z and low flow look alike, CAXTON notes).
TEXT = {
    "none": ("The fresh line behind the nozzle looks normal.", "No print setting appears to be off."),
    "flow_low": ("The fresh line looks thin and patchy, with gaps: too little plastic is coming out.",
                 "The extruder is feeding too little filament, so the flow rate is too low."),
    "flow_high": ("The fresh line looks wide and blobby, with ridges: too much plastic is coming out.",
                  "The extruder is feeding too much filament, so the flow rate is too high."),
    "speed_low": ("The line looks thick and over-filled for its path.",
                  "The print head moves slower than the extrusion expects, so the print speed is too low."),
    "speed_high": ("The line looks stretched thin and may not bond to the layer below.",
                   "The print head moves too fast for the plastic to keep up, so the print speed is too high."),
    "nozzle_temp_low": ("The line looks dull and rough, and is poorly fused.",
                        "The nozzle is too cold, so the plastic does not melt and flow properly."),
    "nozzle_temp_high": ("The line looks glossy and runny, with oozing or strings.",
                         "The nozzle is too hot, so the plastic is too runny."),
    "z_offset_low": ("The line looks squashed flat and spread out; the nozzle may be scraping it.",
                     "The nozzle sits too close to the layer below (Z offset too low)."),
    "z_offset_high": ("The line looks round and loosely laid instead of pressed down.",
                      "The nozzle sits too far from the layer below (Z offset too high)."),
}
VAR = {"flow": "flow rate", "speed": "print speed", "nozzle_temp": "nozzle temperature"}


def nice(c: str) -> str:
    return c.replace("_", " ").replace("nozzle temp", "nozzle temperature")


@lru_cache(maxsize=1)
def model_and_cfg():
    cfg = load(ROOT / "config" / "caxton_demo.yaml")
    model = CauseModel(ROOT / "models" / "cause" / "final.pt", CAUSES, (), "cpu")
    blank = np.zeros((224, 224, 3), np.uint8)  # warm-up, so the timings shown are steady-state
    model.predict(blank, "")
    gradcam(model.model, blank, 0)
    return model, cfg


def gradcam(net, crop: np.ndarray, cls: int) -> np.ndarray:
    """Grad-CAM for one class on backbone.layer4, resized to the crop, in [0, 1]."""
    acts, grads = [], []
    layer = net.backbone.layer4
    h1 = layer.register_forward_hook(lambda _m, _i, out: acts.append(out))
    h2 = layer.register_full_backward_hook(lambda _m, _gi, go: grads.append(go[0]))
    try:
        with torch.enable_grad():
            net.zero_grad()
            net(to_input(crop, 224))[0, cls].backward()
    finally:
        h1.remove()
        h2.remove()
    a, g = acts[0][0].detach(), grads[0][0]
    cam = torch.relu((g.mean(dim=(1, 2))[:, None, None] * a).sum(0)).numpy()
    cam = cam / cam.max() if cam.max() > 0 else cam
    return cv2.resize(cam.astype(np.float32), (crop.shape[1], crop.shape[0]))


def _png(img: np.ndarray) -> str:
    return "data:image/png;base64," + base64.b64encode(cv2.imencode(".png", img)[1].tobytes()).decode()


def where(heat: np.ndarray) -> str:
    """Plain words for the hottest region: position on a 3×3 grid and how spread out it is."""
    mask = heat >= 0.6
    ys, xs = np.nonzero(mask)
    h, w = heat.shape
    row = ("top", "middle", "bottom")[min(2, int(3 * ys.mean() / h))]
    col = ("left", "centre", "right")[min(2, int(3 * xs.mean() / w))]
    pos = "centre" if (row, col) == ("middle", "centre") else f"{row} {col}" if row != "middle" else f"middle {col}"
    spread = "a small, focused" if mask.mean() < 0.12 else "a broad" if mask.mean() > 0.35 else "a medium-sized"
    return f"{spread} area at the {pos} of the frame"


def nominal_state(cfg) -> PrinterState:
    n = cfg.printer.nominal
    return PrinterState(ts=time.monotonic(), state="Printing", nozzle_actual_c=n["nozzle_temp"],
                        nozzle_target_c=n["nozzle_temp"], bed_actual_c=n["bed_temp"], bed_target_c=n["bed_temp"],
                        flow_pct=n["flow"], speed_pct=n["speed"], progress_pct=None, last_change_ts={})


def options(probs: dict, ranked: list[str], cfg) -> list[dict]:
    """Top-3 non-'none' causes → a fix each (real make_proposal + gate), plus 'inspect first'."""
    state, out = nominal_state(cfg), []
    for c in [c for c in ranked if c != "none"][:3]:
        p = probs[c]
        if CAUSE_ACTION[c] is None:
            out.append({"cause": c, "p": p, "kind": "manual", "title": "Adjust the Z offset by hand", "change": None,
                        "detail": MANUAL_ADVICE[c], "gcode": None, "layers": []})
            continue
        prop = make_proposal(c, p, p, state, cfg, "demo")
        g = gate(prop, state, time.monotonic(), cfg)
        out.append({"cause": c, "p": p, "kind": "gcode" if g.passed else "blocked",
                    "title": f"{'Raise' if prop.delta > 0 else 'Lower'} the {VAR[prop.var]}",
                    "change": f"{prop.from_value:g} → {g.final_value:g} {UNIT[prop.var]}",
                    "detail": TEXT[c][1], "gcode": " ".join(g.final_gcode) if g.passed else None,
                    "layers": [{"layer": lr.layer, "passed": lr.passed, "reason": lr.reason} for lr in g.layers]})
    out.append({"cause": None, "p": None, "kind": "inspect", "title": "Inspect the print first", "change": None,
                "detail": "Change nothing yet; look at the part yourself.", "gcode": None, "layers": []})
    return out


def analyse(crop: np.ndarray) -> dict:
    """Everything the UI shows for one frame."""
    model, cfg = model_and_cfg()
    t0 = time.perf_counter()
    est = model.predict(crop, "")
    t1 = time.perf_counter()
    ranked = sorted(est.probs, key=est.probs.get, reverse=True)
    explain_cls = est.top if est.top != "none" else ranked[1]
    heat = gradcam(model.model, crop, CAUSES.index(explain_cls))
    t2 = time.perf_counter()

    big = cv2.resize(crop, (SHOW_PX, SHOW_PX), interpolation=cv2.INTER_CUBIC)
    h = cv2.resize(heat, (SHOW_PX, SHOW_PX))
    rgba = cv2.cvtColor(cv2.applyColorMap(np.uint8(h * 255), cv2.COLORMAP_INFERNO), cv2.COLOR_BGR2BGRA)
    rgba[..., 3] = np.uint8(255 * np.clip(h, 0, 1) ** 0.7)  # cold pixels fade out, so the overlay stays readable
    contours, _ = cv2.findContours(np.uint8(h >= 0.6), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    outline = [(c[:, 0, :] / SHOW_PX).round(4).tolist() for c in contours if len(c) >= 3]

    look, why = TEXT[est.top]
    return {
        "top": est.top, "top_label": nice(est.top), "p_top": est.p_top, "explain_cls": nice(explain_cls),
        "probs": [{"cause": c, "label": c.replace("_", " "), "p": est.probs[c]} for c in ranked],
        "look": look, "why": why if est.top != "none" else None,
        "evidence": f"The model focused on {where(heat)}." if est.top != "none" else None,
        "image": _png(big), "heat": _png(rgba), "outline": outline,
        "ms_model": round(1000 * (t1 - t0)), "ms_cam": round(1000 * (t2 - t1)),
        "fixes": options(est.probs, ranked, cfg), "verify_s": cfg.verify.window_s,
    }
