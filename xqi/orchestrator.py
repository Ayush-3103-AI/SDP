"""The main loop (08-pseudocode P1) with the P3 action branches (T-0033).

This wires the frame source, the detector, the confirmation tracker, the
printer and the outcome verifier into one synchronous loop. Two action paths
are due in P3 and implemented here:

- critical classes act first (FR-005): the configured estop or pause, with no
  gate, before any other work for that frame;
- baseline mode sends the deck recipe as absolute setpoints (FR-023), which is
  the REU parity mode of ADR-0001.

The cause-model paths (gated-recipe, auto, advisory) belong to T-0034 (P5) and
need the P4 ``Explainer``, which does not exist yet. This loop never guesses a
cause and never dispatches anything on those paths; it records the event and
leaves it for the operator.
"""

from __future__ import annotations

import subprocess
import time
import uuid
from collections.abc import Callable, Iterator
from dataclasses import asdict
from datetime import UTC, datetime

from xqi.config import Config
from xqi.detect import ConfirmationTracker
from xqi.explain.counterfactual import recipe_to_proposals
from xqi.store import Store
from xqi.types import ConfirmedDefect, EventVerdict, Frame, PrinterState
from xqi.verify import Verifier

# 08-pseudocode P1: consecutive detector failures before the loop stops.
MAX_DETECTOR_FAILURES = 10

_CRITICAL_GCODE = ("M112",)


class DetectorFailure(RuntimeError):
    """Raised after MAX_DETECTOR_FAILURES consecutive detector failures."""


def git_sha() -> str:
    """Return the current commit, or ``"nogit"`` outside a repository."""

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "nogit"

    if result.returncode != 0:
        return "nogit"

    return result.stdout.strip() or "nogit"


class Orchestrator:
    """One run of the loop. ``source`` is any iterator of :class:`Frame`."""

    def __init__(
        self,
        cfg: Config,
        printer,
        source: Iterator[Frame],
        detector,
        explainer,
        store: Store,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.cfg = cfg
        self.printer = printer
        self.source = source
        self.detector = detector
        self.explainer = explainer
        self.store = store
        self._clock = clock

        self.mode = cfg.mode
        self.tracker = ConfirmationTracker(
            cfg.confirm.hits,
            cfg.confirm.rearm_frames,
            cfg,
        )
        self.verifier = Verifier(cfg.verify.window_s, cfg.verify.settle_s)

        self._detector_failures = 0

    # -- lifecycle --------------------------------------------------------- #

    def run(self, max_frames: int | None = None) -> None:
        self._write_run_header()

        processed = 0
        last_frame_ts = self._clock()

        try:
            for frame in self.source:
                if max_frames is not None and processed >= max_frames:
                    break

                now = self._clock()
                if now - last_frame_ts > self.cfg.camera.max_gap_s:
                    self._pause(
                        "camera_gap",
                        f"no frame for {now - last_frame_ts:.1f}s "
                        f"(> {self.cfg.camera.max_gap_s:g}s)",
                    )

                last_frame_ts = frame.ts
                self._process_frame(frame)
                processed += 1
        except KeyboardInterrupt:
            self.store.write_alert(self._clock(), "interrupted", "keyboard interrupt")
        finally:
            for outcome in self.verifier.close():
                self.store.write_outcome(outcome)
            self.store.close()

    def _write_run_header(self) -> None:
        self.store.write_run(
            {
                "run_id": self.store.run_id,
                "mode": self.mode,
                "cfg_json": asdict(self.cfg),
                "git_sha": git_sha(),
                "started_iso": datetime.now(UTC).isoformat(),
            }
        )

    # -- one frame --------------------------------------------------------- #

    def _process_frame(self, frame: Frame) -> None:
        try:
            detections = list(self.detector(frame))
            self._detector_failures = 0
        except Exception as exc:
            self._detector_failures += 1
            self.store.write_alert(
                self._clock(),
                "detector_error",
                str(exc),
            )
            if self._detector_failures >= MAX_DETECTOR_FAILURES:
                self._pause(
                    "detector_failure",
                    f"{self._detector_failures} consecutive detector failures",
                )
                raise DetectorFailure(
                    f"{self._detector_failures} consecutive detector failures"
                ) from exc
            return

        for detection in detections:
            self.store.write_detection(detection, frame.ts)

        present = {detection.cls for detection in detections}
        events = self.tracker.update(frame, detections)

        # FR-005: critical events act before any other work in this frame.
        for event in sorted(events, key=lambda item: not item.critical):
            self._handle_event(event, frame)

        for outcome in self.verifier.tick(frame.ts, present):
            self.store.write_outcome(outcome)

    # -- event handling ---------------------------------------------------- #

    def _handle_event(self, defect: ConfirmedDefect, frame: Frame) -> None:
        now = self._clock()
        self.store.write_defect(defect)
        self.store.write_timing(defect.defect_id, "t0", defect.t0)
        self.store.write_timing(defect.defect_id, "t_conf", defect.t_conf)

        if defect.critical:
            self._handle_critical(defect, now)
            return

        if self.mode == "baseline":
            self._handle_baseline(defect, now)
            return

        self._handle_nonbaseline(defect, now)

    def _handle_critical(self, defect: ConfirmedDefect, now: float) -> None:
        action = getattr(self.cfg.critical, defect.cls, "estop")

        if action == "pause":
            ok = self.printer.pause()
            gcode: tuple[str, ...] = ()
        else:
            ok = self.printer.estop()
            gcode = _CRITICAL_GCODE

        t_disp = self._clock()
        self.store.write_action(
            uuid.uuid4().hex,
            defect.defect_id,
            None,
            "critical",
            gcode,
            t_disp,
            ok,
        )
        self.store.write_timing(defect.defect_id, "t_disp", t_disp)
        self.store.write_verdict(
            EventVerdict(defect.defect_id, "CRITICAL", f"critical:{defect.cls}", ()),
            t_gate=now,
        )

    def _handle_baseline(self, defect: ConfirmedDefect, now: float) -> None:
        state = self._nominal_state()
        proposals = recipe_to_proposals(defect.cls, state, defect.defect_id)
        lines = [line for proposal in proposals for line in proposal.gcode]

        if not lines:
            self.store.write_alert(
                self._clock(),
                "baseline_no_recipe",
                f"no deck recipe for {defect.cls}",
            )
            self.store.write_verdict(
                EventVerdict(defect.defect_id, "NOOP", "no_recipe", ()),
                t_gate=now,
            )
            return

        ok = self.printer.send_gcode(lines)
        t_disp = self._clock()
        action_id = uuid.uuid4().hex
        self.store.write_action(
            action_id,
            defect.defect_id,
            None,
            "baseline",
            lines,
            t_disp,
            ok,
        )
        self.store.write_timing(defect.defect_id, "t_disp", t_disp)
        self.store.write_verdict(
            EventVerdict(defect.defect_id, "APPLY_RAW", "baseline", ()),
            t_gate=now,
        )

        if ok:
            self.verifier.watch(action_id, defect.defect_id, defect.cls, t_disp)

    def _handle_nonbaseline(self, defect: ConfirmedDefect, now: float) -> None:
        # T-0034 (P5) owns cause model -> conformal -> proposals -> gate ->
        # verdict. The Explainer (T-0020) is P4, so P3 does not guess a cause.
        # Fail safe: record the event, send nothing.
        self.store.write_verdict(
            EventVerdict(defect.defect_id, "NOOP", "explanation_unavailable_p3", ()),
            t_gate=now,
        )
        self.store.write_alert(
            now,
            "explanation_unavailable",
            f"{defect.cls}: non-baseline path is T-0034 (P5)",
        )

    # -- helpers ----------------------------------------------------------- #

    def _nominal_state(self) -> PrinterState:
        nominal = self.cfg.printer.nominal

        return PrinterState(
            ts=self._clock(),
            state="Printing",
            nozzle_actual_c=float(nominal["nozzle_temp"]),
            nozzle_target_c=float(nominal["nozzle_temp"]),
            bed_actual_c=float(nominal["bed_temp"]),
            bed_target_c=float(nominal["bed_temp"]),
            flow_pct=float(nominal["flow"]),
            speed_pct=float(nominal["speed"]),
            progress_pct=None,
            last_change_ts={},
        )

    def _pause(self, kind: str, message: str) -> None:
        ok = self.printer.pause()
        self.store.write_alert(self._clock(), kind, message)

        if not ok:
            self.store.write_alert(
                self._clock(),
                f"{kind}_pause_failed",
                "printer.pause() returned False",
            )


__all__ = ["DetectorFailure", "Orchestrator", "git_sha"]
