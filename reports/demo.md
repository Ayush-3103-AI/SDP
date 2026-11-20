NFR-002: PASS (p95 47 ms ≤ 300 ms, n=7) · frame → verdict (t_gate − t0)
NFR-003: FAIL (p95 35440 ms ≤ 1000 ms, n=4) · event → card first shown (t_card − t_conf)
NFR-004: PASS (0 violations in 0 dispatched commands)

# Offline HITL demo on held-out CAXTON prints (T-0066)

Prints drawn before any run (seed 0, one per test fold): p102 (fold 2), p103 (fold 3), p107 (fold 4). Replay at 2 fps, FakePrinter seeded from the logged process, no detector (early warnings raise the events).

| print | fold | mode | logged onsets | events | verdicts | operator decisions | commands sent | violations |
|---|---|---|---|---|---|---|---|---|
| p102 | 2 | auto | 7 | 2 | ESCALATE 2 | 2 | 0 | 0 |
| p103 | 3 | auto | 56 | 1 | ESCALATE 1 | 1 | 0 | 0 |
| p107 | 4 | auto | 54 | 0 | - | 0 | 0 | 0 |
| p102 | 2 | advisory | 7 | 2 | ESCALATE 2 | 2 | 0 | 0 |
| p103 | 3 | advisory | 56 | 1 | ESCALATE 1 | 1 | 0 | 0 |
| p103 | 3 | advisory | 56 | 1 | ESCALATE 1 | 1 | 0 | 0 |
| p107 | 4 | advisory | 54 | 0 | - | 0 | 0 | 0 |

Logged onsets = changes to a non-empty set of off-nominal variables in the replayed rows. Warnings are never
auto-applied (07 §4 row 9), so auto runs dispatch nothing but critical actions; setpoint commands come from
operator decisions in the advisory runs.
