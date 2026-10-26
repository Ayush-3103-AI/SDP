"""Main loop (08 P1) and event handling (08 P3): critical-first and baseline branches."""

from __future__ import annotations

import logging
import subprocess
import time
import uuid
from collections import deque
from dataclasses import asdict
from datetime import UTC, datetime
from itertools import islice

from xqi import ui_data
from xqi.detect import ConfirmationTracker
from xqi.explain.counterfactual import gcode
from xqi.types import DECK_RECIPES, ConfirmedDefect, EventVerdict, Frame
from xqi.verify import Verifier

log = logging.getLogger(__name__)

MAX_DETECTOR_FAILURES = 10
FRAME_SAVE_S = 0.5  # T-0037: runs/<id>/frames/latest.jpg for the dashboard
# ponytail: ~5 min of telemetry at poll_s=1; grow it if a sensors window ever exceeds that.
HISTORY_LEN = 300


def git_sha() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return "nogit"
    return out.stdout.strip()


def new_run_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Orchestrator:
    def __init__(self, cfg, printer, source, detector, explainer, store, clock=time.monotonic):
        self.cfg = cfg
        self.printer = printer
        self.source = source
        self.detector = detector
        self.explainer = explainer
        self.store = store
        self.clock = clock  # same monotonic clock as Frame.ts
        self.critical = asdict(cfg.critical)  # cls -> "estop" | "pause"
        self.tracker = ConfirmationTracker(
            cfg.confirm.hits, cfg.confirm.rearm_frames, cfg.severity, critical=self.critical
        )
        self.verifier = Verifier(cfg.verify.window_s, cfg.verify.settle_s)
        self.history = deque(maxlen=HISTORY_LEN)

    def run(self, max_frames: int | None = None) -> None:
        run = {"mode": self.cfg.mode, "cfg": self.cfg, "git_sha": git_sha(), "started_iso": _iso()}
        self.store.write_run(run)
        last_frame_ts = self.clock()
        last_poll = last_save = float("-inf")
        failures = 0
        try:
            for frame in islice(self.source, max_frames):
                if frame.ts - last_frame_ts > self.cfg.camera.max_gap_s:
                    self._pause("camera_gap", f"no frame for {frame.ts - last_frame_ts:.1f} s")
                last_frame_ts = frame.ts
                if frame.ts - last_poll >= self.cfg.printer.poll_s:
                    last_poll = frame.ts
                    self._poll()

                try:
                    dets = self.detector(frame)
                except Exception:
                    failures += 1
                    log.exception("detector failed on frame %d (%d in a row)", frame.frame_id, failures)
                    if failures >= MAX_DETECTOR_FAILURES:
                        self._pause("detector_failure", f"{failures} consecutive detector failures")
                        raise RuntimeError("detector keeps failing; printer paused") from None
                    continue
                failures = 0

                for d in dets:
                    self.store.write_detection(d, frame.ts)
                if frame.ts - last_save >= FRAME_SAVE_S:
                    last_save = frame.ts
                    ui_data.save_latest_frame(self.store.path.parent, frame.image, dets)
                for cd in self.tracker.update(frame, dets):
                    self.handle_event(cd, frame)
                for outcome in self.verifier.tick(frame.ts, {d.cls for d in dets}):
                    self.store.write_outcome(outcome)
        except KeyboardInterrupt:
            log.info("stopped by operator")
        finally:
            for outcome in self.verifier.close():
                self.store.write_outcome(outcome)
            self.store.write_run({**run, "ended_iso": _iso()})
            self.store.close()

    def handle_event(self, cd: ConfirmedDefect, frame: Frame) -> None:
        action = self.critical.get(cd.cls)
        if action is not None:  # FR-005: act before any other work
            ok = self.printer.estop() if action == "estop" else self.printer.pause()
            t_disp = self.clock()
            self._log_defect(cd)
            self._log_action(cd, "critical", ["M112"] if action == "estop" else ["pause"], ok, t_disp)
            self.store.write_verdict(EventVerdict(cd.defect_id, "CRITICAL", action, ()), t_gate=t_disp)
            self._explain_only(cd, frame)
            return

        self._log_defect(cd)
        if self.cfg.mode == "baseline":  # FR-023: deck recipe as absolute setpoints, no gate
            lines = [line for var, value in DECK_RECIPES[cd.cls].items() for line in gcode(var, value)]
            ok = self.printer.send_gcode(lines)
            t_disp = self.clock()
            action_id = self._log_action(cd, "baseline", lines, ok, t_disp)
            if ok:
                self.verifier.watch(action_id, cd.defect_id, cd.cls, t_disp)
            verdict = EventVerdict(cd.defect_id, "APPLY_RAW", "deck_recipe", ())
            self.store.write_verdict(verdict, t_gate=t_disp)
        # gated-recipe / auto / advisory branches: T-0034. Until then nothing is sent.

    def _log_defect(self, cd: ConfirmedDefect) -> None:
        self.store.write_defect(cd)
        self.store.write_timing(cd.defect_id, "t0", cd.t0)
        self.store.write_timing(cd.defect_id, "t_conf", cd.t_conf)

    def _log_action(self, cd, source, lines, ok, t_disp) -> str:
        action_id = str(uuid.uuid4())
        self.store.write_action(action_id, cd.defect_id, None, source, lines, t_disp, ok)
        if ok:
            self.store.write_timing(cd.defect_id, "t_disp", t_disp)
        else:
            self.store.write_alert(t_disp, "dispatch_failed", f"{source} {' '.join(lines)} for {cd.cls}")
        return action_id

    def _explain_only(self, cd, frame) -> None:
        # ponytail: synchronous after the action; T-0034 moves explanation work onto the worker queue.
        if self.explainer is None:
            return
        try:
            est, cset, flags, _ = self.explainer.explain(cd, frame, list(self.history))
        except Exception:
            log.exception("explanation failed for %s", cd.defect_id)
            return
        self.store.write_explanation(cd.defect_id, est, cset, cset.qhat, flags, self.clock())

    def _pause(self, kind: str, message: str) -> None:
        ok = self.printer.pause()
        self.store.write_alert(self.clock(), kind, message if ok else f"{message}; pause failed")

    def _poll(self) -> None:
        try:
            state = self.printer.get_state()
        except OSError as exc:  # telemetry is best-effort; P3 handles a missing state per event
            log.warning("get_state failed: %s", type(exc).__name__)
            return
        self.store.write_telemetry(state)
        self.history.append(state)
