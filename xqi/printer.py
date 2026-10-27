import logging
import math
import os
import time
from collections.abc import Callable, Sequence
from typing import Any, Protocol, runtime_checkable

import requests

from xqi.config import Config
from xqi.types import PrinterState, Var

log = logging.getLogger(__name__)


@runtime_checkable
class Printer(Protocol):
    """The hand-off boundary (docs/HANDOFF.md; conformance: tests/test_printer_contract.py).

    - get_state(): a fresh PrinterState. Temperatures in °C; flow/speed in % of the sliced value (M221/M220 S);
      ts and last_change_ts on time.monotonic(), the clock Frame.ts uses. last_change_ts[v] is when setpoint v
      last changed through send_gcode (key absent = never). On failure raise OSError (the loop then escalates);
      any other exception stops the loop.
    - send_gcode(lines): True once the printer accepted every line, False otherwise; never raises for a refused
      or failed command. M104/M140/M220/M221 must show in the next get_state and in last_change_ts. The loop
      retries a False once and calls it only with gate()-checked lines (or the critical/baseline paths).
    - pause()/resume(): True if the printer is now paused/printing because of this call, False if refused or
      failed (the loop writes an alert row). Never raises.
    - estop(): stop motion and heaters now (M112 or the hardware equivalent); True once halted. After it,
      send_gcode returns False until a human resets the printer.
    Each call should answer within cfg.printer.timeout_s (one retry inside is fine).
    """

    def get_state(self) -> PrinterState: ...

    def send_gcode(self, lines: Sequence[str]) -> bool: ...

    def pause(self) -> bool: ...

    def resume(self) -> bool: ...

    def estop(self) -> bool: ...


TAU_S = {"nozzle_temp": 8.0, "bed_temp": 60.0}  # 07-math §12
EULER_STEP_S = 0.1
GCODE_VAR: dict[str, Var] = {
    "M104": "nozzle_temp",
    "M140": "bed_temp",
    "M220": "speed",
    "M221": "flow",
}


def _words(line: str) -> list[str]:
    return line.split(";")[0].upper().split()


def _setpoint(line: str) -> tuple[Var, float] | None:
    """`M221 S95` → ("flow", 95.0); None for any other line."""
    words = _words(line)
    var = GCODE_VAR.get(words[0]) if words else None
    s = [w[1:] for w in words[1:] if w.startswith("S")]
    return (var, float(s[0])) if var and s else None


class FakePrinter(Printer):
    """Simulated printer: 07-math §12 thermal lag, instant flow/speed."""

    def __init__(
        self,
        clock: Callable[[], float] = time.monotonic,
        nozzle_c: float = 210.0,
        bed_c: float = 60.0,
    ) -> None:
        self.clock = clock
        self.sent: list[tuple[float, str]] = []
        self.state = "Printing"
        self.target: dict[Var, float] = {
            "nozzle_temp": nozzle_c,
            "bed_temp": bed_c,
            "flow": 100.0,
            "speed": 100.0,
        }
        self.actual = {"nozzle_temp": nozzle_c, "bed_temp": bed_c}
        # -inf = never changed, so cooldowns pass from the start.
        self.last_change_ts: dict[Var, float] = {
            v: float("-inf") for v in self.target
        }
        self.t = clock()

    def _advance(self) -> float:
        now = self.clock()
        # Explicit Euler in sub-steps, so one long gap between calls stays stable.
        n = max(0, math.ceil((now - self.t) / EULER_STEP_S))
        for _ in range(n):
            dt = (now - self.t) / n
            for v, tau in TAU_S.items():
                self.actual[v] += dt * (self.target[v] - self.actual[v]) / tau
        self.t = max(self.t, now)
        return now

    def get_state(self) -> PrinterState:
        now = self._advance()
        return PrinterState(
            ts=now,
            state=self.state,
            nozzle_actual_c=self.actual["nozzle_temp"],
            nozzle_target_c=self.target["nozzle_temp"],
            bed_actual_c=self.actual["bed_temp"],
            bed_target_c=self.target["bed_temp"],
            flow_pct=self.target["flow"],
            speed_pct=self.target["speed"],
            progress_pct=None,
            last_change_ts=dict(self.last_change_ts),
        )

    def send_gcode(self, lines: Sequence[str]) -> bool:
        if self.state == "Error":
            return False
        now = self._advance()
        for line in lines:
            self.sent.append((now, line))
            if _words(line)[:1] == ["M112"]:
                self.state = "Error"
                return True
            sp = _setpoint(line)
            if sp:
                self.target[sp[0]] = sp[1]
                self.last_change_ts[sp[0]] = now
        return True

    def set_process(self, flow: float, speed: float, nozzle_target: float) -> None:
        """CAXTON replay seeding (07 §12): the dataset's own setpoints, outside the gate.

        Not a command: nothing goes to `sent` and last_change_ts is untouched, so gating is unchanged.
        """
        self._advance()  # integrate the old nozzle target up to now
        self.target.update(flow=flow, speed=speed, nozzle_temp=nozzle_target)

    def pause(self) -> bool:
        if self.state != "Printing":
            return False
        self.state = "Paused"
        return True

    def resume(self) -> bool:
        if self.state != "Paused":
            return False
        self.state = "Printing"
        return True

    def estop(self) -> bool:
        return self.send_gcode(["M112"]) or self.state == "Error"


class OctoPrintClient(Printer):
    """OctoPrint REST client. Flow/speed are tracked locally (OctoPrint never reports them)."""

    def __init__(self, cfg: Config, clock: Callable[[], float] = time.monotonic) -> None:
        self.url = cfg.printer.url.rstrip("/")
        self.timeout_s = cfg.printer.timeout_s
        self.clock = clock
        self.session = requests.Session()
        # KeyError names the env var, never the key.
        self.session.headers["X-Api-Key"] = os.environ[cfg.printer.api_key_env]
        self.tracked = {v: float(cfg.printer.nominal[v]) for v in ("flow", "speed")}
        self.last_change_ts: dict[Var, float] = {}

    def __repr__(self) -> str:
        return f"OctoPrintClient({self.url!r})"

    def _request(self, method: str, path: str, body: Any = None) -> requests.Response | None:
        """One retry on a connection error, timeout or non-2xx (P3); None if both fail."""
        for _ in range(2):
            try:
                r = self.session.request(method, self.url + path, json=body, timeout=self.timeout_s)
            except requests.RequestException as exc:
                # Class name only: an exception message is not ours to vet for the key.
                log.warning("%s %s failed: %s", method, path, type(exc).__name__)
                continue
            if r.ok:
                return r
            log.warning("%s %s failed: HTTP %d", method, path, r.status_code)
        return None

    def get_state(self) -> PrinterState:
        r = self._request("GET", "/api/printer")
        if r is None:
            raise OSError("GET /api/printer failed")  # P3: caller sets state=None → ESCALATE
        p = r.json()
        temp = p["temperature"]
        job = self._request("GET", "/api/job")
        progress = (job.json().get("progress") or {}).get("completion") if job else None
        return PrinterState(
            ts=self.clock(),
            state=p["state"]["text"],
            nozzle_actual_c=float(temp["tool0"]["actual"]),
            nozzle_target_c=float(temp["tool0"]["target"]),
            bed_actual_c=float(temp["bed"]["actual"]),
            bed_target_c=float(temp["bed"]["target"]),
            flow_pct=self.tracked["flow"],
            speed_pct=self.tracked["speed"],
            progress_pct=None if progress is None else float(progress),
            last_change_ts=dict(self.last_change_ts),
        )

    def send_gcode(self, lines: Sequence[str]) -> bool:
        if self._request("POST", "/api/printer/command", {"commands": list(lines)}) is None:
            return False
        now = self.clock()
        for line in lines:
            sp = _setpoint(line)
            if sp:
                if sp[0] in self.tracked:
                    self.tracked[sp[0]] = sp[1]
                self.last_change_ts[sp[0]] = now
        return True

    def _job(self, action: str) -> bool:
        body = {"command": "pause", "action": action}
        return self._request("POST", "/api/job", body) is not None

    def pause(self) -> bool:
        return self._job("pause")

    def resume(self) -> bool:
        return self._job("resume")

    def estop(self) -> bool:
        return self.send_gcode(["M112"])
