"""Explainer: cause model -> conformal set -> sensor flags -> proposals (08 P3). No gating here."""

from collections.abc import Sequence

import numpy as np

from xqi.explain import conformal, sensors
from xqi.explain.counterfactual import make_proposal
from xqi.types import (
    CauseEstimate,
    CauseSet,
    ConfirmedDefect,
    Frame,
    PrinterState,
    Proposal,
)


def crop(image: np.ndarray, xyxy, pad: float) -> np.ndarray:
    """Box padded by pad x its width/height on each side, clipped to the image."""
    x1, y1, x2, y2 = xyxy
    px, py = pad * (x2 - x1), pad * (y2 - y1)
    h, w = image.shape[:2]
    return image[
        max(0, int(y1 - py)) : min(h, int(y2 + py)),
        max(0, int(x1 - px)) : min(w, int(x2 + px)),
    ]


class Explainer:
    def __init__(self, cause_model, qhat: float, labels: Sequence[str], cfg):
        self.cause_model = cause_model
        self.qhat = qhat
        self.labels = tuple(labels)
        self.cfg = cfg

    def explain(
        self, cd: ConfirmedDefect, frame: Frame, history: Sequence[PrinterState]
    ) -> tuple[CauseEstimate, CauseSet, tuple[str, ...], list[Proposal]]:
        box = crop(frame.image, cd.xyxy, self.cfg.cause_model.crop_pad)
        est = self.cause_model.predict(box, cd.cls)
        probs = np.array([est.probs[c] for c in self.labels])
        members = conformal.predict_set(probs, self.qhat, self.labels)
        cset = CauseSet(members=members, alpha=self.cfg.conformal.alpha, qhat=self.qhat)
        flags = sensors.check(history, cd.t_conf, self.cfg)
        if not history:  # no setpoints to move from; the gate escalates on state=None
            return est, cset, flags, []
        state = max(history, key=lambda s: s.ts)
        proposals = [
            make_proposal(c, est.probs[c], cd.severity, state, self.cfg, cd.defect_id)
            for c in sorted(members, key=est.probs.get, reverse=True)
        ]
        return est, cset, flags, [p for p in proposals if p is not None]
