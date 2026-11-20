# Latency and VRAM report (T-0036)

Runs: runs/20261120T113620Z/events.sqlite, runs/20261120T114045Z/events.sqlite, runs/20261120T114455Z/events.sqlite, runs/20261120T115038Z/events.sqlite, runs/20261120T115550Z/events.sqlite, runs/20261120T120028Z/events.sqlite, runs/20261120T120458Z/events.sqlite

## Run stores (07 §7, monotonic clock)

| stage | n | p50 ms | p95 ms | max ms |
|---|---|---|---|---|
| confirm → cause (t_cause − t_conf) | 7 | 0.0 | 15.7 | 16.0 |
| cause → gate (t_gate − t_cause) | 7 | 0.0 | 0.0 | 0.0 |
| added action path (t_gate − t_conf), NFR-001 | 7 | 0.0 | 15.7 | 16.0 |
| gate → dispatch, auto (t_disp − t_gate) | 0 | – | – | – |
| end-to-end, auto (t_disp − t0), NFR-002 | 0 | – | – | – |
| critical end-to-end (t_disp − t0), NFR-002 | 0 | – | – | – |

## Requirements

- NFR-001: NO DATA (run --bench on the RTX 3050)
- NFR-002: NO DATA (auto p95 – ms ≤ 300 ms, n=0: NO DATA; critical p95 – ms ≤ 270 ms, n=0: NO DATA)
- NFR-011: NO DATA (run --bench on the RTX 3050)
