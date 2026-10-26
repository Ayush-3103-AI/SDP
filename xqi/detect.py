import re
import time
import uuid
from collections import deque
from dataclasses import fields
from types import SimpleNamespace

from xqi.config import CriticalConfig
from xqi.explain.counterfactual import severity
from xqi.types import DEFECTS, ConfirmedDefect, Detection, Frame

# Normalised model class names that are not in DEFECTS verbatim.
ALIASES = {
    "over_extr": "over_extrusion",
    "under_extr": "under_extrusion",
}
NO_DEFECT = {"no_defect", "none", "normal", "good"}


def normalise(name: str) -> str | None:
    """Map a model class name to a DEFECTS entry, or None for no-defect."""
    key = re.sub(r"[\s\-]+", "_", name.strip().lower()).strip("._")
    key = ALIASES.get(key, key)
    if key in NO_DEFECT:
        return None
    if key not in DEFECTS:
        raise ValueError(f"Unknown detector class: {name!r}")
    return key


class Detector:
    def __init__(self, weights, imgsz, conf, device, model=None):
        if model is None:
            from ultralytics import YOLO

            model = YOLO(weights)
        self.model = model
        self.imgsz = imgsz
        self.conf = conf
        self.device = device
        self.classes = {
            int(i): normalise(name) for i, name in model.names.items()
        }

    def __call__(self, frame: Frame) -> list[Detection]:
        boxes = self.model(
            frame.image,
            imgsz=self.imgsz,
            conf=self.conf,
            device=self.device,
            verbose=False,
        )[0].boxes
        h, w = frame.image.shape[:2]
        dets = []
        for xyxy, conf, cls in zip(
            boxes.xyxy.tolist(), boxes.conf.tolist(), boxes.cls.tolist()
        ):
            name = self.classes[int(cls)]
            if name is None or conf < self.conf:
                continue
            x1, y1, x2, y2 = xyxy
            dets.append(
                Detection(
                    frame_id=frame.frame_id,
                    cls=name,
                    conf=float(conf),
                    xyxy=(x1, y1, x2, y2),
                    area_frac=(x2 - x1) * (y2 - y1) / (w * h),
                )
            )
        return dets


# Critical classes are fixed by the config schema (CriticalConfig's fields).
CRITICAL = tuple(f.name for f in fields(CriticalConfig))


class ConfirmationTracker:
    """08 P2: confirm after hits[k] consecutive frames, once per episode."""

    def __init__(self, hits, rearm_frames, severity_cfg, critical=CRITICAL):
        if any(hits[k] < 1 for k in DEFECTS):
            raise ValueError("confirm.hits must be >= 1 for every defect")
        self.hits = hits
        self.rearm_frames = rearm_frames
        self.sev_cfg = SimpleNamespace(severity=severity_cfg)
        self.critical = set(critical)
        self.streak = dict.fromkeys(DEFECTS, 0)
        self.first_ts = dict.fromkeys(DEFECTS)
        self.armed = dict.fromkeys(DEFECTS, True)
        self.absent = dict.fromkeys(DEFECTS, 0)
        self.recent = {
            k: deque(maxlen=int(severity_cfg.window)) for k in DEFECTS
        }

    def update(self, frame: Frame, dets: list[Detection]) -> list[ConfirmedDefect]:
        present = {}
        for d in dets:
            if d.cls not in present or d.conf > present[d.cls].conf:
                present[d.cls] = d
        out = []
        for k in DEFECTS:
            self.recent[k].append(k in present)
            if k in present:
                self.absent[k] = 0
                self.streak[k] += 1
                if self.first_ts[k] is None:
                    self.first_ts[k] = frame.ts
                if self.armed[k] and self.streak[k] >= self.hits[k]:
                    self.armed[k] = False
                    out.append(self._emit(k, present[k], frame))
            else:
                self.streak[k] = 0
                self.first_ts[k] = None
                self.absent[k] += 1
                if self.absent[k] >= self.rearm_frames:
                    self.armed[k] = True
        return out

    def _emit(self, k, d, frame):
        h = sum(self.recent[k])
        return ConfirmedDefect(
            defect_id=str(uuid.uuid4()),
            cls=k,
            frame_id=frame.frame_id,
            t0=self.first_ts[k],
            t_conf=time.monotonic(),  # same clock as Frame.ts
            conf=d.conf,
            xyxy=d.xyxy,
            area_frac=d.area_frac,
            recent_hits=h,
            severity=severity(d.area_frac, h, self.sev_cfg),
            critical=k in self.critical,
        )
