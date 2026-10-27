"""Early warning on the cause probabilities of the nozzle ROI (07 §13, P7). Pure: no I/O, ts is passed in."""

from collections.abc import Sequence

from xqi.types import CauseWarning


class EarlyWarning:
    def __init__(self, causes: Sequence[str], cfg):
        self.causes = tuple(c for c in causes if c != "none")
        self.cfg = cfg
        self.armed = dict.fromkeys(self.causes, True)
        self.last_warn = dict.fromkeys(self.causes, float("-inf"))
        self.reset()

    def reset(self) -> None:
        """Forget p̄ and the runs (a ts gap); armed and the cooldowns are kept."""
        self.pbar = None
        self.last_ts = None
        self.run = dict.fromkeys(self.causes, 0)

    def update(self, ts: float, probs: dict[str, float]) -> list[CauseWarning]:
        cfg = self.cfg
        if self.last_ts is not None and ts - self.last_ts > cfg.max_gap_s:
            self.reset()
        self.last_ts = ts
        p = {c: float(probs[c]) for c in self.causes}
        if self.pbar is None:
            self.pbar = p
        else:
            self.pbar = {c: cfg.beta * self.pbar[c] + (1 - cfg.beta) * p[c] for c in self.causes}

        ready = []
        for c in self.causes:
            self.run[c] = self.run[c] + 1 if self.pbar[c] >= cfg.theta_on else 0
            if self.pbar[c] < cfg.theta_off:
                self.armed[c] = True
            if self.armed[c] and self.run[c] >= cfg.m and ts - self.last_warn[c] >= cfg.cooldown_s:
                ready.append(c)
        if not ready:
            return []
        c = max(ready, key=self.pbar.__getitem__)
        self.armed[c] = False
        self.last_warn[c] = ts
        return [CauseWarning(cause=c, p=self.pbar[c], ts=ts, probs=dict(probs))]
