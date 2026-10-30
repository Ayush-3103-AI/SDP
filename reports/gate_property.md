# Gate property test (NFR-004, offline half)

Seed 0, 100000 random proposals, episodes of 10 with sequential dispatch.
Start states: integer setpoints in the L1 box ±20 %, random last-change times; Δ ∈ [−50, 50].
Out of scope: fractional setpoints. 210.5 + 5 rounds to M104 S216 (Δ 5.5 > step 5).

**Violations: 0 / 100000** (35746 dispatched, 30105 clipped).

| count | value |
|---|---|
| blocked_L1 | 23930 |
| blocked_L2 | 19135 |
| blocked_L3 | 21189 |
| cases | 100000 |
| clipped | 30105 |
| dispatched | 35746 |
