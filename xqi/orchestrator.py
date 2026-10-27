"""Main loop (08 P1) and event handling (08 P3): every mode's action path."""

from __future__ import annotations

import copy
import json
import logging
import math
import queue
import subprocess
import threading
import time
import uuid
from collections import deque
from dataclasses import asdict, replace
from datetime import UTC, datetime
from functools import partial
from itertools import islice
from types import SimpleNamespace

from xqi import ui_data
from xqi.detect import ConfirmationTracker
from xqi.explain import crop
from xqi.explain.counterfactual import gcode, recipe_to_proposals
from xqi.gate import event_verdict, gate
from xqi.store import Store
from xqi.types import (
    DECK_RECIPES,
    ConfirmedDefect,
    EventVerdict,
    Frame,
    OperatorDecision,
    PrinterState,
    Proposal,
)
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
        self.jobs = queue.Queue()  # off-latency-path work (FR-009 heatmaps)
        # The heatmap worker gets its own copy of the cause net (07 §11), so its forward hook never
        # sees the explainer's passes on the loop thread and neither waits for the other.
        net = getattr(getattr(explainer, "cause_model", None), "model", None)
        self.heat_model = copy.deepcopy(net) if net is not None else None

    def run(self, max_frames: int | None = None) -> None:
        run = {"mode": self.cfg.mode, "cfg": self.cfg, "git_sha": git_sha(), "started_iso": _iso()}
        self.store.write_run(run)
        worker = threading.Thread(target=self._work, name="xqi-worker", daemon=True)
        worker.start()
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
                    self._state()

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
                self.process_operator_decisions()
                self.check_timeouts()
                for outcome in self.verifier.tick(frame.ts, {d.cls for d in dets}):
                    self.store.write_outcome(outcome)
        except KeyboardInterrupt:
            log.info("stopped by operator")
        finally:
            for outcome in self.verifier.close():
                self.store.write_outcome(outcome)
            self.store.write_run({**run, "ended_iso": _iso()})
            self.jobs.put(None)
            worker.join()
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
            t_disp = self._dispatch(cd, "baseline", lines)
            verdict = EventVerdict(cd.defect_id, "APPLY_RAW", "deck_recipe", ())
            self.store.write_verdict(verdict, t_gate=t_disp)
            return

        state = self._state()
        est = cset = None
        flags, props = (), []
        if self.cfg.mode == "gated-recipe":  # 07 §4 row 3: L1–L3 on the recipe, no cause model, no L4
            if state is not None:
                props = recipe_to_proposals(cd.cls, state, cd.defect_id)
        elif self.explainer is not None:
            try:
                est, cset, flags, props = self.explainer.explain(cd, frame, list(self.history))
            except Exception:  # no cause set → 07 §4 row 5 escalates
                log.exception("explanation failed for %s", cd.defect_id)
            else:
                self.store.write_explanation(cd.defect_id, est, cset, cset.qhat, flags, self.clock())
        now = self.clock()
        decisions = [gate(p, state, now, self.cfg) for p in props]
        verdict = event_verdict(self.cfg.mode, cd, cset, est, flags, decisions, state, self.cfg)
        t_gate = self.clock()
        for p, g in zip(props, decisions, strict=True):
            self.store.write_proposal(p, g)
        pending = verdict.verdict in ("PROPOSE", "ESCALATE")
        deadline = t_gate + self.cfg.hitl.timeout_s if pending else None
        self.store.write_verdict(verdict, t_gate=t_gate, pending=pending, deadline_ts=deadline)
        log.info("%s %s: %s %s", cd.defect_id, cd.cls, verdict.verdict, verdict.reason)

        if verdict.verdict == "APPLY":
            ids = verdict.proposal_ids
            lines = [line for g in decisions if g.proposal_id in ids for line in g.final_gcode]
            self._dispatch(cd, "auto", lines, ids[0] if len(ids) == 1 else None)
        elif verdict.verdict == "ESCALATE" and not self.printer.pause():
            self.store.write_alert(self.clock(), "pause_failed", f"escalate {verdict.reason} for {cd.cls}")
        if self.cfg.mode != "gated-recipe" and self.cfg.attribution.enabled and self.heat_model is not None:
            roi = crop(frame.image, cd.xyxy, self.cfg.cause_model.crop_pad)  # the crop the cause model classified
            self.jobs.put(partial(self._heatmap, cd, replace(frame, image=roi)))  # FR-009: after dispatch

    def process_operator_decisions(self) -> None:
        """FR-017/018: the UI is untrusted, so every apply/modify is re-gated on the current state."""
        pending = {row["defect_id"]: row for row in self.store.pending_events()}
        for dec in self.store.new_decisions():
            self.store.mark_consumed(dec["id"])
            event = pending.pop(dec["defect_id"], None)
            if event is None:  # unknown event, or one an earlier decision already consumed
                self._ignore(dec, "no pending event")
                continue
            self._clear_pending(event)
            choice, cd = dec["choice"], self._event(event)
            if choice in ("pause", "stop"):
                ok = self.printer.pause() if choice == "pause" else self.printer.estop()
                self._log_action(cd, "operator", ["pause"] if choice == "pause" else ["M112"], ok, self.clock())
            elif choice in ("apply", "modify"):
                self._regate(cd, dec)
            else:
                log.info("%s %s: operator %s", cd.defect_id, cd.cls, choice)  # reject

    def _regate(self, cd, dec) -> None:
        rows = self.store.query(
            "SELECT proposal_id, defect_id, cause, var, from_value, delta, to_value, gcode_json, counterfactual"
            " FROM proposals WHERE proposal_id = ? AND defect_id = ?", (dec["proposal_id"], cd.defect_id))
        if not rows:
            self._ignore(dec, f"unknown proposal {dec['proposal_id']}")
            return
        row = rows[0]
        row["gcode"] = tuple(json.loads(row.pop("gcode_json")))
        p = Proposal(**row)
        state = self._state()
        if dec["choice"] == "modify":
            delta = dec["modified_delta"]
            if delta is None or not math.isfinite(delta):
                self._ignore(dec, f"bad modified_delta {delta}")
                return
            x = state.setpoint(p.var) if state is not None else p.from_value
            p = Proposal(f"{p.proposal_id}-op{dec['id']}", cd.defect_id, "operator", p.var, x, delta, x + delta,
                         gcode(p.var, x + delta), f"Operator modify: {p.var} {x:g}→{x + delta:g} ({delta:+g}).")
        g = gate(p, state, self.clock(), self.cfg)
        if dec["choice"] == "modify":
            self.store.write_proposal(p, g)  # gate_json carries the clip reason
        if not g.passed:
            self.store.write_alert(self.clock(), "decision_blocked",
                                   f"{dec['choice']} {p.proposal_id}: {g.layers[-1].reason}")
            return
        self._dispatch(cd, "operator", list(g.final_gcode), p.proposal_id)

    def check_timeouts(self) -> None:
        """FR-019: an unanswered card past its deadline gets cfg.hitl.timeout_action."""
        now = self.clock()
        for event in self.store.pending_events():
            if event["deadline_ts"] is None or now < event["deadline_ts"]:
                continue
            decision = OperatorDecision(None, event["defect_id"], "timeout", None, "loop", _iso(),
                                        now - event["t_gate"])
            self.store.mark_consumed(self.store.insert_decision(decision))
            self._clear_pending(event)
            if self.cfg.hitl.timeout_action == "pause":
                self._log_action(self._event(event), "timeout", ["pause"], self.printer.pause(), self.clock())

    def _event(self, event) -> SimpleNamespace:
        """The defect_id/cls pair _dispatch and _log_action need, for a stored event."""
        rows = self.store.query("SELECT cls FROM defects WHERE defect_id = ?", (event["defect_id"],))
        return SimpleNamespace(defect_id=event["defect_id"], cls=rows[0]["cls"] if rows else "?")

    def _clear_pending(self, event) -> None:
        verdict = EventVerdict(event["defect_id"], event["verdict"], event["reason"],
                               tuple(json.loads(event["proposal_ids_json"])))
        self.store.write_verdict(verdict, t_gate=event["t_gate"], deadline_ts=event["deadline_ts"])

    def _ignore(self, dec, why) -> None:
        self.store.write_alert(self.clock(), "decision_ignored",
                               f"decision {dec['id']} ({dec['choice']} {dec['defect_id']}): {why}")

    def _dispatch(self, cd, source, lines, proposal_id=None) -> float:
        ok = self.printer.send_gcode(lines) or self.printer.send_gcode(lines)  # P3: one retry
        t_disp = self.clock()
        action_id = self._log_action(cd, source, lines, ok, t_disp, proposal_id)
        if ok:  # the printer client updates tracked setpoints / last_change_ts only on success
            self.verifier.watch(action_id, cd.defect_id, cd.cls, t_disp)
        return t_disp

    def _work(self) -> None:
        store = Store(self.store.path)  # the worker's own SQLite connection
        try:
            for job in iter(self.jobs.get, None):
                try:
                    job(store)
                except Exception:
                    log.exception("worker job failed")
        finally:
            store.close()

    def _heatmap(self, cd, roi: Frame, store) -> None:
        """EigenCAM on the cause net; roi.image is the crop it classified (a defect's box or a warning's ROI)."""
        # Lazy: keeps the torch import off the start-up path.
        from xqi.explain import attribution

        h, w = roi.image.shape[:2]
        heat = attribution.eigencam(self.heat_model, roi, self.cfg.attribution.layer, (0, 0, w, h),
                                    self.cfg.cause_model.input_px)
        path = self.store.path.parent / "heatmaps" / f"{cd.defect_id}.png"
        attribution.save_heatmap_png(heat, roi.image, path)
        store.write_defect(cd, heatmap_path=str(path))
        store.write_timing(cd.defect_id, "t_heatmap", self.clock())

    def _log_defect(self, cd: ConfirmedDefect) -> None:
        self.store.write_defect(cd)
        self.store.write_timing(cd.defect_id, "t0", cd.t0)
        self.store.write_timing(cd.defect_id, "t_conf", cd.t_conf)

    def _log_action(self, cd, source, lines, ok, t_disp, proposal_id=None) -> str:
        action_id = str(uuid.uuid4())
        self.store.write_action(action_id, cd.defect_id, proposal_id, source, lines, t_disp, ok)
        if ok:
            self.store.write_timing(cd.defect_id, "t_disp", t_disp)
        else:
            self.store.write_alert(t_disp, "dispatch_failed", f"{source} {' '.join(lines)} for {cd.cls}")
        return action_id

    def _explain_only(self, cd, frame) -> None:
        # ponytail: synchronous after the estop/pause (P3 queues it); move it to self.jobs if the
        # cause model must stay single-threaded with heatmaps or a critical stall matters.
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

    def _state(self) -> PrinterState | None:
        try:
            state = self.printer.get_state()
        except OSError as exc:  # telemetry is best-effort; P3: state=None → ESCALATE
            log.warning("get_state failed: %s", type(exc).__name__)
            return None
        self.store.write_telemetry(state)
        self.history.append(state)
        return state
