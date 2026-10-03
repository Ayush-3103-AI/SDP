from dataclasses import dataclass
from typing import Literal

import numpy as np

SCHEMA_VERSION = 1

Var = Literal["nozzle_temp", "bed_temp", "flow", "speed"]


@dataclass(frozen=True, slots=True)
class Frame:
    frame_id: int
    ts: float
    wall_iso: str
    image: np.ndarray

    def to_dict(self) -> dict:
        return {
            "frame_id": self.frame_id,
            "ts": self.ts,
            "wall_iso": self.wall_iso,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Frame":
        return cls(
            frame_id=data["frame_id"],
            ts=data["ts"],
            wall_iso=data["wall_iso"],
            image=np.empty((0, 0, 3), dtype=np.uint8),
        )


@dataclass(frozen=True, slots=True)
class Detection:
    frame_id: int
    cls: str
    conf: float
    xyxy: tuple[float, float, float, float]
    area_frac: float

    def to_dict(self) -> dict:
        return {
            "frame_id": self.frame_id,
            "cls": self.cls,
            "conf": self.conf,
            "xyxy": list(self.xyxy),
            "area_frac": self.area_frac,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Detection":
        return cls(
            frame_id=data["frame_id"],
            cls=data["cls"],
            conf=data["conf"],
            xyxy=tuple(data["xyxy"]),
            area_frac=data["area_frac"],
        )


@dataclass(frozen=True, slots=True)
class ConfirmedDefect:
    defect_id: str
    cls: str
    frame_id: int
    t0: float
    t_conf: float
    conf: float
    xyxy: tuple[float, ...]
    area_frac: float
    recent_hits: int
    severity: float
    critical: bool

    def to_dict(self) -> dict:
        return {
            "defect_id": self.defect_id,
            "cls": self.cls,
            "frame_id": self.frame_id,
            "t0": self.t0,
            "t_conf": self.t_conf,
            "conf": self.conf,
            "xyxy": list(self.xyxy),
            "area_frac": self.area_frac,
            "recent_hits": self.recent_hits,
            "severity": self.severity,
            "critical": self.critical,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConfirmedDefect":
        return cls(
            defect_id=data["defect_id"],
            cls=data["cls"],
            frame_id=data["frame_id"],
            t0=data["t0"],
            t_conf=data["t_conf"],
            conf=data["conf"],
            xyxy=tuple(data["xyxy"]),
            area_frac=data["area_frac"],
            recent_hits=data["recent_hits"],
            severity=data["severity"],
            critical=data["critical"],
        )


@dataclass(frozen=True, slots=True)
class PrinterState:
    ts: float
    state: str
    nozzle_actual_c: float
    nozzle_target_c: float
    bed_actual_c: float
    bed_target_c: float
    flow_pct: float
    speed_pct: float
    progress_pct: float | None
    last_change_ts: dict[Var, float]

    def setpoint(self, v: Var) -> float:
        if v == "nozzle_temp":
            return self.nozzle_target_c
        if v == "bed_temp":
            return self.bed_target_c
        if v == "flow":
            return self.flow_pct
        if v == "speed":
            return self.speed_pct
        raise ValueError(f"Unknown variable: {v}")

    def to_dict(self) -> dict:
        return {
            "ts": self.ts,
            "state": self.state,
            "nozzle_actual_c": self.nozzle_actual_c,
            "nozzle_target_c": self.nozzle_target_c,
            "bed_actual_c": self.bed_actual_c,
            "bed_target_c": self.bed_target_c,
            "flow_pct": self.flow_pct,
            "speed_pct": self.speed_pct,
            "progress_pct": self.progress_pct,
            "last_change_ts": dict(self.last_change_ts),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PrinterState":
        return cls(
            ts=data["ts"],
            state=data["state"],
            nozzle_actual_c=data["nozzle_actual_c"],
            nozzle_target_c=data["nozzle_target_c"],
            bed_actual_c=data["bed_actual_c"],
            bed_target_c=data["bed_target_c"],
            flow_pct=data["flow_pct"],
            speed_pct=data["speed_pct"],
            progress_pct=data["progress_pct"],
            last_change_ts=dict(data["last_change_ts"]),
        )


@dataclass(frozen=True, slots=True)
class CauseEstimate:
    probs: dict[str, float]
    top: str
    p_top: float

    def to_dict(self) -> dict:
        return {
            "probs": dict(self.probs),
            "top": self.top,
            "p_top": self.p_top,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CauseEstimate":
        return cls(
            probs=dict(data["probs"]),
            top=data["top"],
            p_top=data["p_top"],
        )


@dataclass(frozen=True, slots=True)
class CauseSet:
    members: tuple[str, ...]
    alpha: float
    qhat: float

    def to_dict(self) -> dict:
        return {
            "members": list(self.members),
            "alpha": self.alpha,
            "qhat": self.qhat,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CauseSet":
        return cls(
            members=tuple(data["members"]),
            alpha=data["alpha"],
            qhat=data["qhat"],
        )


@dataclass(frozen=True, slots=True)
class Proposal:
    proposal_id: str
    defect_id: str
    cause: str
    var: Var
    from_value: float
    delta: float
    to_value: float
    gcode: tuple[str, ...]
    counterfactual: str

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "defect_id": self.defect_id,
            "cause": self.cause,
            "var": self.var,
            "from_value": self.from_value,
            "delta": self.delta,
            "to_value": self.to_value,
            "gcode": list(self.gcode),
            "counterfactual": self.counterfactual,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Proposal":
        return cls(
            proposal_id=data["proposal_id"],
            defect_id=data["defect_id"],
            cause=data["cause"],
            var=data["var"],
            from_value=data["from_value"],
            delta=data["delta"],
            to_value=data["to_value"],
            gcode=tuple(data["gcode"]),
            counterfactual=data["counterfactual"],
        )


@dataclass(frozen=True, slots=True)
class LayerResult:
    layer: Literal["L1", "L2", "L3", "L4"]
    passed: bool
    reason: str

    def to_dict(self) -> dict:
        return {
            "layer": self.layer,
            "passed": self.passed,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LayerResult":
        return cls(
            layer=data["layer"],
            passed=data["passed"],
            reason=data["reason"],
        )


@dataclass(frozen=True, slots=True)
class GateDecision:
    proposal_id: str
    passed: bool
    clipped: bool
    final_delta: float
    final_value: float
    final_gcode: tuple[str, ...]
    layers: tuple[LayerResult, ...]

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "passed": self.passed,
            "clipped": self.clipped,
            "final_delta": self.final_delta,
            "final_value": self.final_value,
            "final_gcode": list(self.final_gcode),
            "layers": [layer.to_dict() for layer in self.layers],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GateDecision":
        return cls(
            proposal_id=data["proposal_id"],
            passed=data["passed"],
            clipped=data["clipped"],
            final_delta=data["final_delta"],
            final_value=data["final_value"],
            final_gcode=tuple(data["final_gcode"]),
            layers=tuple(
                LayerResult.from_dict(layer)
                for layer in data["layers"]
            ),
        )


@dataclass(frozen=True, slots=True)
class EventVerdict:
    defect_id: str
    verdict: Literal[
        "CRITICAL",
        "APPLY_RAW",
        "APPLY",
        "PROPOSE",
        "ESCALATE",
        "NOOP",
    ]
    reason: str
    proposal_ids: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "defect_id": self.defect_id,
            "verdict": self.verdict,
            "reason": self.reason,
            "proposal_ids": list(self.proposal_ids),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EventVerdict":
        return cls(
            defect_id=data["defect_id"],
            verdict=data["verdict"],
            reason=data["reason"],
            proposal_ids=tuple(data["proposal_ids"]),
        )


@dataclass(frozen=True, slots=True)
class OperatorDecision:
    proposal_id: str | None
    defect_id: str
    choice: Literal[
        "apply",
        "modify",
        "reject",
        "pause",
        "stop",
        "timeout",
    ]
    modified_delta: float | None
    operator: str
    wall_iso: str
    latency_s: float

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "defect_id": self.defect_id,
            "choice": self.choice,
            "modified_delta": self.modified_delta,
            "operator": self.operator,
            "wall_iso": self.wall_iso,
            "latency_s": self.latency_s,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OperatorDecision":
        return cls(
            proposal_id=data["proposal_id"],
            defect_id=data["defect_id"],
            choice=data["choice"],
            modified_delta=data["modified_delta"],
            operator=data["operator"],
            wall_iso=data["wall_iso"],
            latency_s=data["latency_s"],
        )


@dataclass(frozen=True, slots=True)
class Outcome:
    action_id: str
    defect_id: str
    cls: str
    verdict: Literal[
        "resolved",
        "persisted",
        "worsened",
        "unknown",
    ]
    r_before: float
    r_after: float
    window_s: float

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "defect_id": self.defect_id,
            "cls": self.cls,
            "verdict": self.verdict,
            "r_before": self.r_before,
            "r_after": self.r_after,
            "window_s": self.window_s,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Outcome":
        return cls(
            action_id=data["action_id"],
            defect_id=data["defect_id"],
            cls=data["cls"],
            verdict=data["verdict"],
            r_before=data["r_before"],
            r_after=data["r_after"],
            window_s=data["window_s"],
        )


DEFECTS = (
    "clog",
    "layer_shift",
    "over_extrusion",
    "spaghetti",
    "stringing",
    "under_extrusion",
    "warping",
)


CAUSES = (
    "none",
    "nozzle_temp_low",
    "nozzle_temp_high",
    "flow_low",
    "flow_high",
    "speed_low",
    "speed_high",
    "bed_temp_low",
    "misalignment",
)


CAUSE_ACTION = {
    "nozzle_temp_low": ("nozzle_temp", -1),
    "nozzle_temp_high": ("nozzle_temp", +1),
    "flow_low": ("flow", -1),
    "flow_high": ("flow", +1),
    "speed_low": ("speed", -1),
    "speed_high": ("speed", +1),
    "bed_temp_low": ("bed_temp", -1),
    "none": None,
    "misalignment": None,
}


CAUSE_DEFECTS = {
    "nozzle_temp_high": ["stringing", "over_extrusion"],
    "nozzle_temp_low": ["under_extrusion", "clog"],
    "flow_high": ["over_extrusion"],
    "flow_low": ["under_extrusion"],
    "speed_high": ["under_extrusion"],
    "speed_low": ["over_extrusion", "stringing"],
    "bed_temp_low": ["warping", "spaghetti"],
    "misalignment": ["layer_shift"],
}


DECK_RECIPES = {
    "over_extrusion": {
        "nozzle_temp": 190,
        "speed": 95,
        "flow": 80,
    },
    "under_extrusion": {
        "nozzle_temp": 205,
        "speed": 80,
        "flow": 110,
    },
    "stringing": {
        "nozzle_temp": 190,
        "speed": 80,
        "flow": 95,
    },
    "warping": {
        "bed_temp": 65,
    },
}