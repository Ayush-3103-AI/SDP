"""Printer abstraction: the protocol, a simulator and the OctoPrint adapter.

09-interfaces.md §Module APIs defines one ``Printer`` protocol with five
operations. ``FakePrinter`` implements it deterministically for every test (no
hardware); ``OctoPrintClient`` implements it against the real REST API
(T-0027). Both are interchangeable, so the orchestrator cannot tell them apart
and the safety gate stays the only authority over what is dispatched.

``FakePrinter`` follows 07-math.md §12 for the thermal lag and is a simulation
only — it makes no physical claim.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Protocol, runtime_checkable

import requests

from xqi.types import PrinterState

logger = logging.getLogger("xqi.printer")

# 07-math.md §12: first-order thermal lag, simulation only.
TAU_NOZZLE_S = 8.0
TAU_BED_S = 60.0

# Explicit Euler at the call rate; small sub-steps keep the integrator close to
# the ODE it approximates (07-math.md §12).
_MAX_EULER_STEP_S = 0.25

_STATE_PRINTING = "Printing"
_STATE_PAUSED = "Paused"
_STATE_ERROR = "Error"

# G-code whose S value is a tracked setpoint.
_TEMP_COMMANDS = {"M104": "nozzle_temp", "M140": "bed_temp"}
_RATE_COMMANDS = {"M220": "speed", "M221": "flow"}


class PrinterError(RuntimeError):
    """A printer operation could not be completed."""


@runtime_checkable
class Printer(Protocol):
    """The five operations the orchestrator dispatches through."""

    def get_state(self) -> PrinterState: ...

    def send_gcode(self, lines: Sequence[str]) -> bool: ...

    def pause(self) -> bool: ...

    def resume(self) -> bool: ...

    def estop(self) -> bool: ...


def _command(line: str) -> str:
    parts = line.strip().split()
    return parts[0].upper() if parts else ""


def _s_value(line: str) -> float | None:
    """Return the ``S`` parameter of a G-code line, or ``None`` if absent."""

    for token in line.split():
        if len(token) > 1 and token[0].upper() == "S":
            try:
                return float(token[1:])
            except ValueError:
                return None
    return None


class FakePrinter(Printer):
    """Deterministic in-process printer (T-0026).

    ``clock`` is injectable so tests control simulated time; the default clock
    is real monotonic time. Temperatures relax to their target per 07-math.md
    §12, while flow and speed apply immediately.

    Test controls (attributes, not part of the protocol):
    - ``connected``: when ``False``, ``get_state`` raises and sends fail;
    - ``fail_next``: the next N ``send_gcode`` calls return ``False``;
    - ``progress_pct``: reported verbatim by ``get_state``.
    """

    def __init__(
        self,
        clock: Callable[[], float] = time.monotonic,
        nominal: Mapping[str, float] | None = None,
    ) -> None:
        self._clock = clock

        nominal = dict(nominal) if nominal is not None else {}
        nozzle = float(nominal.get("nozzle_temp", 210.0))
        bed = float(nominal.get("bed_temp", 60.0))
        flow = float(nominal.get("flow", 100.0))
        speed = float(nominal.get("speed", 100.0))

        self.nozzle_target_c = nozzle
        self.nozzle_actual_c = nozzle
        self.bed_target_c = bed
        self.bed_actual_c = bed
        self.flow_pct = flow
        self.speed_pct = speed

        self.state = _STATE_PRINTING
        self.progress_pct: float | None = 0.0

        self.connected = True
        self.fail_next = 0

        self.sent: list[tuple[float, str]] = []
        self.last_change_ts: dict[str, float] = {}

        self._last_update = self._clock()

    # -- simulation -------------------------------------------------------- #

    def _advance(self) -> float:
        """Integrate the thermal model up to ``clock()`` and return the time."""

        now = self._clock()
        remaining = now - self._last_update
        self._last_update = now

        while remaining > 0.0:
            step = min(remaining, _MAX_EULER_STEP_S)
            self.nozzle_actual_c += (
                (self.nozzle_target_c - self.nozzle_actual_c)
                * step
                / TAU_NOZZLE_S
            )
            self.bed_actual_c += (
                (self.bed_target_c - self.bed_actual_c) * step / TAU_BED_S
            )
            remaining -= step

        return now

    def _apply(self, line: str, now: float) -> None:
        command = _command(line)
        value = _s_value(line)

        if command == "M112":
            self.state = _STATE_ERROR
            return

        variable = _TEMP_COMMANDS.get(command) or _RATE_COMMANDS.get(command)
        if variable is None or value is None:
            return

        if variable == "nozzle_temp":
            self.nozzle_target_c = value
        elif variable == "bed_temp":
            self.bed_target_c = value
        elif variable == "flow":
            self.flow_pct = value
        else:
            self.speed_pct = value

        self.last_change_ts[variable] = now

    # -- Printer protocol -------------------------------------------------- #

    def get_state(self) -> PrinterState:
        if not self.connected:
            raise PrinterError("printer not connected")

        now = self._advance()

        return PrinterState(
            ts=now,
            state=self.state,
            nozzle_actual_c=self.nozzle_actual_c,
            nozzle_target_c=self.nozzle_target_c,
            bed_actual_c=self.bed_actual_c,
            bed_target_c=self.bed_target_c,
            flow_pct=self.flow_pct,
            speed_pct=self.speed_pct,
            progress_pct=self.progress_pct,
            last_change_ts=dict(self.last_change_ts),
        )

    def send_gcode(self, lines: Sequence[str]) -> bool:
        if not self.connected or self.state == _STATE_ERROR:
            return False

        if self.fail_next > 0:
            self.fail_next -= 1
            return False

        now = self._clock()

        for line in lines:
            self._apply(line, now)
            self.sent.append((now, line))

        return True

    def pause(self) -> bool:
        if not self.connected or self.state != _STATE_PRINTING:
            return False

        self.state = _STATE_PAUSED
        return True

    def resume(self) -> bool:
        if not self.connected or self.state != _STATE_PAUSED:
            return False

        self.state = _STATE_PRINTING
        return True

    def estop(self) -> bool:
        return self.send_gcode(["M112"])


def _parse_setpoints(lines: Sequence[str]) -> dict[str, float]:
    """Extract the tracked flow/speed setpoints from M221/M220 lines."""

    updates: dict[str, float] = {}

    for line in lines:
        variable = _RATE_COMMANDS.get(_command(line))
        if variable is None:
            continue
        value = _s_value(line)
        if value is not None:
            updates[variable] = value

    return updates


class OctoPrintClient(Printer):
    """OctoPrint REST adapter (T-0027).

    The API key is read from the environment variable named by the config and
    is only ever placed in the ``X-Api-Key`` header — never logged. Every
    request uses ``cfg.printer.timeout_s`` and a connection error is retried
    once; any other failure returns ``False`` (or raises from ``get_state``)
    rather than being silently treated as success.
    """

    def __init__(
        self,
        url: str,
        api_key_env: str,
        timeout_s: float,
        nominal: Mapping[str, float] | None = None,
        *,
        session: requests.Session | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._url = url.rstrip("/")
        self._timeout_s = float(timeout_s)
        self._clock = clock
        self._session = session if session is not None else requests.Session()

        api_key = os.environ.get(api_key_env)
        if api_key:
            self._session.headers["X-Api-Key"] = api_key

        nominal = dict(nominal) if nominal is not None else {}
        self.flow_pct = float(nominal.get("flow", 100.0))
        self.speed_pct = float(nominal.get("speed", 100.0))
        self.last_change_ts: dict[str, float] = {}

    # -- HTTP -------------------------------------------------------------- #

    def _request(
        self,
        method: str,
        path: str,
        payload: Mapping[str, Any] | None = None,
    ) -> requests.Response | None:
        url = f"{self._url}{path}"

        try:
            return self._session.request(
                method,
                url,
                json=payload,
                timeout=self._timeout_s,
            )
        except requests.Timeout:
            logger.warning("octoprint timeout: %s %s", method, path)
            return None
        except requests.ConnectionError:
            logger.warning("octoprint connection error: %s %s", method, path)
            try:
                return self._session.request(
                    method,
                    url,
                    json=payload,
                    timeout=self._timeout_s,
                )
            except requests.RequestException:
                logger.warning("octoprint retry failed: %s %s", method, path)
                return None
        except requests.RequestException:
            logger.warning("octoprint request failed: %s %s", method, path)
            return None

    @staticmethod
    def _ok(response: requests.Response | None) -> bool:
        return response is not None and response.ok

    @staticmethod
    def _json(response: requests.Response) -> Any:
        try:
            return response.json()
        except ValueError as exc:
            raise PrinterError("octoprint: malformed JSON") from exc

    @staticmethod
    def _temperature(block: Mapping[str, Any], key: str) -> tuple[float, float]:
        entry = block.get(key)

        if not isinstance(entry, Mapping):
            raise PrinterError(f"octoprint: missing temperature {key}")

        try:
            actual = float(entry["actual"])
            target = float(entry["target"])
        except (KeyError, TypeError, ValueError) as exc:
            raise PrinterError(
                f"octoprint: malformed temperature {key}"
            ) from exc

        return actual, target

    # -- Printer protocol -------------------------------------------------- #

    def get_state(self) -> PrinterState:
        printer_response = self._request("GET", "/api/printer")

        if not self._ok(printer_response):
            raise PrinterError("octoprint: /api/printer unavailable")

        assert printer_response is not None
        data = self._json(printer_response)

        if not isinstance(data, Mapping):
            raise PrinterError("octoprint: /api/printer is not an object")

        temperature = data.get("temperature")
        if not isinstance(temperature, Mapping):
            raise PrinterError("octoprint: /api/printer has no temperature")

        nozzle_actual, nozzle_target = self._temperature(temperature, "tool0")
        bed_actual, bed_target = self._temperature(temperature, "bed")

        state_block = data.get("state")
        if isinstance(state_block, Mapping):
            state_text = str(state_block.get("text", "Unknown"))
        else:
            state_text = str(data.get("state", "Unknown"))

        progress: float | None = None
        job_response = self._request("GET", "/api/job")
        if self._ok(job_response):
            assert job_response is not None
            try:
                job = self._json(job_response)
            except PrinterError:
                job = None
            if isinstance(job, Mapping):
                job_progress = job.get("progress")
                if isinstance(job_progress, Mapping):
                    completion = job_progress.get("completion")
                    if completion is not None:
                        progress = float(completion)

        return PrinterState(
            ts=self._clock(),
            state=state_text,
            nozzle_actual_c=nozzle_actual,
            nozzle_target_c=nozzle_target,
            bed_actual_c=bed_actual,
            bed_target_c=bed_target,
            flow_pct=self.flow_pct,
            speed_pct=self.speed_pct,
            progress_pct=progress,
            last_change_ts=dict(self.last_change_ts),
        )

    def send_gcode(self, lines: Sequence[str]) -> bool:
        lines = list(lines)
        response = self._request(
            "POST",
            "/api/printer/command",
            {"commands": lines},
        )

        if not self._ok(response):
            return False

        now = self._clock()
        for variable, value in _parse_setpoints(lines).items():
            if variable == "flow":
                self.flow_pct = value
            else:
                self.speed_pct = value
            self.last_change_ts[variable] = now

        return True

    def _job_action(self, action: str) -> bool:
        response = self._request(
            "POST",
            "/api/job",
            {"command": "pause", "action": action},
        )
        return self._ok(response)

    def pause(self) -> bool:
        return self._job_action("pause")

    def resume(self) -> bool:
        return self._job_action("resume")

    def estop(self) -> bool:
        return self.send_gcode(["M112"])


__all__ = [
    "FakePrinter",
    "OctoPrintClient",
    "Printer",
    "PrinterError",
]
