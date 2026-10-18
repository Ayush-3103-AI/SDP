"""Detection: the YOLO11 wrapper (T-0030) and the confirmation tracker (T-0031).

``Detector`` turns a :class:`xqi.types.Frame` into canonical detections; the
ultralytics runtime is imported lazily so the wrapper (and its tests) work
without torch installed. ``ConfirmationTracker`` implements 08-pseudocode P2:
per-class streaks confirm an event after ``hits`` frames and re-arm after
``rearm_frames`` misses. ``ReplayDetector`` serves checked-in detections for
offline, deterministic runs — it is a testing/diagnostic backend selected
explicitly with ``detector.kind: replay`` and never fabricates a detection for a
frame it has no record of.
"""

from __future__ import annotations

import json
import uuid
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

from xqi.config import Config
from xqi.explain.counterfactual import severity
from xqi.types import DEFECTS, ConfirmedDefect, Detection, Frame


class DetectorError(RuntimeError):
    """A detector could not be created or its output could not be read."""


# Model class names that are not defects and are dropped at load (T-0030).
_DROP_NAMES = frozenset(
    {
        "background",
        "defect",
        "no_defect",
        "no_defects",
        "none",
        "normal",
        "object",
    }
)

# Normalised model name -> canonical DEFECTS entry. Normalisation is
# lower-case, spaces/hyphens -> "_", dots removed ("Over-extr." -> over_extrusion).
_NAME_ALIASES = {
    "clog": "clog",
    "layer_shift": "layer_shift",
    "layershift": "layer_shift",
    "over_extr": "over_extrusion",
    "over_extrusion": "over_extrusion",
    "overextrusion": "over_extrusion",
    "spaghetti": "spaghetti",
    "stringing": "stringing",
    "under_extr": "under_extrusion",
    "under_extrusion": "under_extrusion",
    "underextrusion": "under_extrusion",
    "warping": "warping",
}


def _normalise_name(name: str) -> str:
    normalised = str(name).strip().lower()
    normalised = normalised.replace("-", "_").replace(" ", "_")
    normalised = normalised.replace(".", "")
    while "__" in normalised:
        normalised = normalised.replace("__", "_")
    return normalised.strip("_")


def _to_numpy(value: Any) -> np.ndarray | None:
    if value is None:
        return None
    if hasattr(value, "detach"):  # torch.Tensor
        value = value.detach().cpu().numpy()
    return np.asarray(value, dtype=float)


def _as_sequence(results: Any) -> list[Any]:
    if isinstance(results, (list, tuple)):
        return list(results)
    return [results]


class Detector:
    """YOLO11 detector wrapper (T-0030).

    ``model`` may be injected (tests); otherwise the ultralytics runtime is
    imported lazily and a missing runtime or weights file raises
    :class:`DetectorError` rather than silently returning nothing.
    """

    def __init__(
        self,
        weights: str,
        imgsz: int,
        conf: float,
        device: str,
        *,
        model: Any | None = None,
    ) -> None:
        self.weights = str(weights)
        self.imgsz = int(imgsz)
        self.conf = float(conf)
        self.device = str(device)

        self._model = model if model is not None else self._load(self.weights)
        self._classes = self._build_class_map(getattr(self._model, "names", None))

    @staticmethod
    def _load(weights: str) -> Any:
        path = Path(weights)
        if not path.is_file():
            raise DetectorError(f"weights not found: {weights}")

        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise DetectorError(
                "ultralytics is not installed; cannot load YOLO11 weights"
            ) from exc

        try:
            return YOLO(weights)
        except Exception as exc:
            raise DetectorError(f"could not load YOLO model {weights}") from exc

    @staticmethod
    def _build_class_map(names: Any) -> dict[int, str | None]:
        if names is None:
            raise DetectorError("model exposes no class names")

        if isinstance(names, Mapping):
            items = {int(key): str(value) for key, value in names.items()}
        elif isinstance(names, (list, tuple)):
            items = {index: str(value) for index, value in enumerate(names)}
        else:
            raise DetectorError("model class names must be a mapping or sequence")

        mapping: dict[int, str | None] = {}

        for index, raw in items.items():
            normalised = _normalise_name(raw)
            if normalised in _DROP_NAMES:
                mapping[index] = None
                continue

            resolved = _NAME_ALIASES.get(normalised)
            if resolved is None:
                raise DetectorError(f"unknown model class name: {raw!r}")

            mapping[index] = resolved

        return mapping

    def __call__(self, frame: Frame) -> list[Detection]:
        height, width = frame.image.shape[:2]
        frame_area = float(height * width)

        results = self._model(
            frame.image,
            imgsz=self.imgsz,
            conf=self.conf,
            device=self.device,
            verbose=False,
        )

        detections: list[Detection] = []

        for result in _as_sequence(results):
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue

            xyxy = _to_numpy(getattr(boxes, "xyxy", None))
            if xyxy is None or xyxy.size == 0:
                continue

            xyxy = xyxy.reshape(-1, 4)
            confs = _to_numpy(getattr(boxes, "conf", None))
            classes = _to_numpy(getattr(boxes, "cls", None))
            if confs is None or classes is None:
                continue

            count = min(xyxy.shape[0], confs.reshape(-1).shape[0], classes.reshape(-1).shape[0])

            for index in range(count):
                resolved = self._classes.get(int(classes.reshape(-1)[index]))
                if resolved is None:
                    continue

                confidence = float(confs.reshape(-1)[index])
                if not np.isfinite(confidence) or confidence < self.conf:
                    continue

                x1, y1, x2, y2 = (float(value) for value in xyxy[index])
                if not all(np.isfinite(value) for value in (x1, y1, x2, y2)):
                    continue

                box_width = max(0.0, x2 - x1)
                box_height = max(0.0, y2 - y1)
                if box_width <= 0.0 or box_height <= 0.0 or frame_area <= 0.0:
                    continue

                detections.append(
                    Detection(
                        frame_id=frame.frame_id,
                        cls=resolved,
                        conf=confidence,
                        xyxy=(x1, y1, x2, y2),
                        area_frac=(box_width * box_height) / frame_area,
                    )
                )

        return detections


def _record_to_detection(frame_id: int, record: Any) -> Detection:
    if not isinstance(record, Mapping):
        raise DetectorError("replay detections: each record must be an object")

    cls = str(record.get("cls", ""))
    if cls not in DEFECTS:
        raise DetectorError(f"replay detections: unknown class {cls!r}")

    try:
        conf = float(record["conf"])
        xyxy = tuple(float(value) for value in record["xyxy"])
    except (KeyError, TypeError, ValueError) as exc:
        raise DetectorError("replay detections: record needs conf and xyxy") from exc

    if len(xyxy) != 4:
        raise DetectorError("replay detections: xyxy must have four numbers")

    return Detection(
        frame_id=frame_id,
        cls=cls,
        conf=conf,
        xyxy=xyxy,  # type: ignore[arg-type]
        area_frac=0.0,
    )


class ReplayDetector:
    """Deterministic detections from a checked-in JSON fixture (offline runs)."""

    def __init__(self, frames: Mapping[int, Sequence[Detection]], conf: float = 0.0) -> None:
        self._frames = {int(key): list(value) for key, value in frames.items()}
        self.conf = float(conf)

    @classmethod
    def from_file(cls, path: str | Path, conf: float = 0.0) -> ReplayDetector:
        source = Path(path)
        if not source.is_file():
            raise DetectorError(f"replay detections not found: {path}")

        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise DetectorError(f"replay detections are not valid JSON: {path}") from exc

        if not isinstance(data, Mapping) or "frames" not in data:
            raise DetectorError("replay detections must be an object with a 'frames' key")

        raw_frames = data["frames"]
        if not isinstance(raw_frames, Mapping):
            raise DetectorError("replay detections 'frames' must be an object")

        frames: dict[int, list[Detection]] = {}
        for key, records in raw_frames.items():
            try:
                frame_id = int(key)
            except (TypeError, ValueError) as exc:
                raise DetectorError(
                    f"replay detections: bad frame id {key!r}"
                ) from exc
            if not isinstance(records, list):
                raise DetectorError(
                    f"replay detections: frame {key} must be a list"
                )
            frames[frame_id] = [
                _record_to_detection(frame_id, record) for record in records
            ]

        return cls(frames, conf=conf)

    def __call__(self, frame: Frame) -> list[Detection]:
        records = self._frames.get(int(frame.frame_id), [])

        height, width = frame.image.shape[:2]
        frame_area = float(height * width)

        detections: list[Detection] = []

        for record in records:
            if record.conf < self.conf:
                continue

            if frame_area > 0.0:
                x1, y1, x2, y2 = record.xyxy
                area = max(0.0, x2 - x1) * max(0.0, y2 - y1)
                detections.append(replace(record, area_frac=area / frame_area))
            else:
                detections.append(record)

        return detections


def _critical_names(cfg: Config) -> frozenset[str]:
    return frozenset(name for name in DEFECTS if hasattr(cfg.critical, name))


class ConfirmationTracker:
    """Multi-frame confirmation with severity (08-pseudocode P2, 07-math §1).

    09-interfaces.md names the third argument ``severity_cfg``; it is the full
    :class:`xqi.config.Config` because the tracker needs ``cfg.severity`` for
    :func:`severity` and ``cfg.critical`` for the critical flag. The positional
    signature is unchanged.
    """

    def __init__(self, hits: Mapping[str, int], rearm_frames: int, severity_cfg: Config) -> None:
        self.cfg = severity_cfg
        self.hits = {cls: int(hits[cls]) for cls in DEFECTS}
        self.rearm_frames = int(rearm_frames)

        window = max(1, int(severity_cfg.severity.window))
        self._recent: dict[str, deque[bool]] = {
            cls: deque(maxlen=window) for cls in DEFECTS
        }
        self._streak = {cls: 0 for cls in DEFECTS}
        self._first_ts: dict[str, float | None] = {cls: None for cls in DEFECTS}
        self._armed = {cls: True for cls in DEFECTS}
        self._absent = {cls: 0 for cls in DEFECTS}
        self._critical = _critical_names(severity_cfg)

    def update(self, frame: Frame, dets: Sequence[Detection]) -> list[ConfirmedDefect]:
        present: dict[str, Detection] = {}
        for detection in dets:
            current = present.get(detection.cls)
            if current is None or detection.conf > current.conf:
                present[detection.cls] = detection

        events: list[ConfirmedDefect] = []

        for cls in DEFECTS:
            self._recent[cls].append(cls in present)
            detection = present.get(cls)

            if detection is not None:
                self._absent[cls] = 0
                self._streak[cls] += 1
                if self._first_ts[cls] is None:
                    self._first_ts[cls] = frame.ts

                if self._armed[cls] and self._streak[cls] >= self.hits[cls]:
                    self._armed[cls] = False
                    recent_hits = int(sum(self._recent[cls]))
                    events.append(
                        ConfirmedDefect(
                            defect_id=uuid.uuid4().hex,
                            cls=cls,
                            frame_id=detection.frame_id,
                            t0=float(self._first_ts[cls]),
                            t_conf=float(frame.ts),
                            conf=float(detection.conf),
                            xyxy=tuple(float(value) for value in detection.xyxy),
                            area_frac=float(detection.area_frac),
                            recent_hits=recent_hits,
                            severity=severity(
                                float(detection.area_frac),
                                recent_hits,
                                self.cfg,
                            ),
                            critical=cls in self._critical,
                        )
                    )
            else:
                self._streak[cls] = 0
                self._first_ts[cls] = None
                self._absent[cls] += 1
                if self._absent[cls] >= self.rearm_frames:
                    self._armed[cls] = True

        return events


__all__ = ["ConfirmationTracker", "Detector", "DetectorError", "ReplayDetector"]
