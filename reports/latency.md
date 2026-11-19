# Latency and VRAM report (T-0036)

Runs: none

## Run stores (07 §7, monotonic clock)

| stage | n | p50 ms | p95 ms | max ms |
|---|---|---|---|---|
| confirm → cause (t_cause − t_conf) | 0 | – | – | – |
| cause → gate (t_gate − t_cause) | 0 | – | – | – |
| added action path (t_gate − t_conf), NFR-001 | 0 | – | – | – |
| gate → dispatch, auto (t_disp − t_gate) | 0 | – | – | – |
| end-to-end, auto (t_disp − t0), NFR-002 | 0 | – | – | – |
| critical end-to-end (t_disp − t0), NFR-002 | 0 | – | – | – |

## Bench: 500 CAXTON crops (500 distinct, data/crops.csv) through crop + cause model + conformal + gate on NVIDIA GeForce RTX 4050 Laptop GPU

Action path: p50 3.9 ms · p95 4.4 ms · p99 4.9 ms · max 5.7 ms · verdicts seen: ESCALATE, PROPOSE

EigenCAM (after dispatch, not in NFR-001): p50 6.9 ms · p95 7.5 ms · p99 9.0 ms

Peak VRAM (torch.cuda.max_memory_allocated), cause model + EigenCAM copy: 0.11 GB; detector: not configured

## Requirements

- NFR-001: PASS (bench p95 4.4 ms ≤ 30 ms on NVIDIA GeForce RTX 4050 Laptop GPU)
- NFR-002: NO DATA (auto p95 – ms ≤ 300 ms, n=0: NO DATA; critical p95 – ms ≤ 270 ms, n=0: NO DATA)
- NFR-011: PASS (0.11 GB ≤ 3.5 GB, cause model, on NVIDIA GeForce RTX 4050 Laptop GPU)
