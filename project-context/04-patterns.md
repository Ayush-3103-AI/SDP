<!-- HEAD
FILE:     04-patterns.md
PHASE:    1 — UNDERSTAND
UPDATED:  2026-10-03
STATUS:   draft (awaiting gate)
SUMMARY:  6 patterns and 4 anti-patterns; each one ends in an ADR. Key ones:
          ground truth by construction, explanation = actionable variable, safety as a
          pure projection, A/B on the same rig, and an uncertainty set as the options menu.
OPEN:     none
-->

# Patterns

| Pattern | Evidence | Applies here because | ADR |
|---|---|---|---|
| Ground truth by construction (induce the cause) | Deck "induced-cause labels"; CAXTON | 6,454 induced images already exist | ADR-0002, ADR-0007 |
| Explanations in the actuator's variables | Senoner 2021/2024 | Operators act on temp/flow/speed/bed, not on pixels | ADR-0002 |
| Safety as a pure projection/filter in front of the actuator | González-Potes 2026; CBF literature | Setpoints are box-bounded scalars, so projection is trivial | ADR-0004 |
| Uncertainty set → options menu | Conformal prediction | Singleton → auto; multi → human chooses among the set | ADR-0003 |
| A/B every claim on the same rig | Deck "claims must survive a rig" | Four run modes, same campaign | ADR-0001 (modes) |
| Keep slow explanation off the control path | Deck latency budget | EigenCAM after dispatch | ADR-0001 |

# Anti-patterns
| Anti-pattern | Failure signature | ADR |
|---|---|---|
| Image-level splits on video frames | Test ≫ new-geometry performance | ADR-0007 |
| Telemetry/setpoints as model input during induced trials | Too-good cause accuracy | ADR-0002 |
| Fixed absolute setpoint recipes | Reversals, overshoot | ADR-0004 |
| E-stop as the only safety response | Unrecoverable prints | ADR-0006 |
