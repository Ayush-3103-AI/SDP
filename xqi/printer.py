import math
import time
from collections.abc import Callable, Sequence
from typing import Protocol, runtime_checkable

from xqi.types import PrinterState, Var


@runtime_checkable
class Printer(Protocol):
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
            words = line.split(";")[0].upper().split()
            if not words:
                continue
            if words[0] == "M112":
                self.state = "Error"
                return True
            var = GCODE_VAR.get(words[0])
            s = [w[1:] for w in words[1:] if w.startswith("S")]
            if var and s:
                self.target[var] = float(s[0])
                self.last_change_ts[var] = now
        return True

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
