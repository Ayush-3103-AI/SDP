import json

import numpy as np
import pytest

from xqi.types import (
    CauseEstimate,
    CauseSet,
    ConfirmedDefect,
    Detection,
    EventVerdict,
    Frame,
    GateDecision,
    LayerResult,
    OperatorDecision,
    Outcome,
    PrinterState,
    Proposal,
)


@pytest.fixture
def sample_objects():
    layer = LayerResult(
        layer="L1",
        passed=True,
        reason="within limits",
    )

    return [
        Frame(
            frame_id=1,
            ts=123.45,
            wall_iso="2026-10-03T19:00:00",
            image=np.zeros((10, 10, 3), dtype=np.uint8),
        ),
        Detection(
            frame_id=1,
            cls="stringing",
            conf=0.95,
            xyxy=(10.0, 20.0, 100.0, 200.0),
            area_frac=0.08,
        ),
        ConfirmedDefect(
            defect_id="D001",
            cls="stringing",
            frame_id=1,
            t0=123.0,
            t_conf=124.0,
            conf=0.95,
            xyxy=(10.0, 20.0, 100.0, 200.0),
            area_frac=0.08,
            recent_hits=3,
            severity=0.7,
            critical=False,
        ),
        PrinterState(
            ts=123.45,
            state="printing",
            nozzle_actual_c=205.0,
            nozzle_target_c=210.0,
            bed_actual_c=58.0,
            bed_target_c=60.0,
            flow_pct=100.0,
            speed_pct=100.0,
            progress_pct=50.0,
            last_change_ts={
                "nozzle_temp": 120.0,
                "bed_temp": 121.0,
                "flow": 122.0,
                "speed": 123.0,
            },
        ),
        CauseEstimate(
            probs={
                "nozzle_temp_high": 0.8,
                "flow_high": 0.2,
            },
            top="nozzle_temp_high",
            p_top=0.8,
        ),
        CauseSet(
            members=("nozzle_temp_high", "flow_high"),
            alpha=0.10,
            qhat=0.25,
        ),
        Proposal(
            proposal_id="P001",
            defect_id="D001",
            cause="nozzle_temp_high",
            var="nozzle_temp",
            from_value=210.0,
            delta=-5.0,
            to_value=205.0,
            gcode=("M104 S205",),
            counterfactual="Reduce nozzle temperature",
        ),
        LayerResult(
            layer="L1",
            passed=True,
            reason="within limits",
        ),
        GateDecision(
            proposal_id="P001",
            passed=True,
            clipped=False,
            final_delta=-5.0,
            final_value=205.0,
            final_gcode=("M104 S205",),
            layers=(layer,),
        ),
        EventVerdict(
            defect_id="D001",
            verdict="APPLY",
            reason="safe proposal available",
            proposal_ids=("P001",),
        ),
        OperatorDecision(
            proposal_id="P001",
            defect_id="D001",
            choice="apply",
            modified_delta=None,
            operator="operator1",
            wall_iso="2026-10-03T19:00:00",
            latency_s=1.5,
        ),
        Outcome(
            action_id="A001",
            defect_id="D001",
            cls="stringing",
            verdict="resolved",
            r_before=0.8,
            r_after=0.2,
            window_s=120.0,
        ),
    ]


@pytest.mark.parametrize("index", range(12))
def test_dataclass_json_round_trip(sample_objects, index):
    original = sample_objects[index]

    data = original.to_dict()
    encoded = json.dumps(data)
    decoded = json.loads(encoded)

    restored = type(original).from_dict(decoded)

    assert restored.to_dict() == original.to_dict()


@pytest.mark.parametrize(
    ("variable", "expected"),
    [
        ("nozzle_temp", 210.0),
        ("bed_temp", 60.0),
        ("flow", 100.0),
        ("speed", 100.0),
    ],
)
def test_printer_state_setpoint(variable, expected):
    state = PrinterState(
        ts=123.45,
        state="printing",
        nozzle_actual_c=205.0,
        nozzle_target_c=210.0,
        bed_actual_c=58.0,
        bed_target_c=60.0,
        flow_pct=100.0,
        speed_pct=100.0,
        progress_pct=50.0,
        last_change_ts={
            "nozzle_temp": 120.0,
            "bed_temp": 121.0,
            "flow": 122.0,
            "speed": 123.0,
        },
    )

    assert state.setpoint(variable) == expected