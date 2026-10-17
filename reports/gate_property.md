# Gate property test (T-0023 / NFR-004)

- seed: 0
- cases: 100000
- dispatched: 42947
- violations: 0

Invariant (07-math.md §3): every dispatched setpoint change satisfies |Δ'| ≤ step, stays inside L1, is in the L3 window or moves toward it, and respects the per-variable cooldown.

Result: 0 violations.
