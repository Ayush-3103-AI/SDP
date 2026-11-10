# Cause model, fold 0: early read on A3 (T-0012)

Rung 1 = frozen-backbone probe, rung 4 = full fine-tune (08 P5, Gate 2). Floor = the fold-0 training majority cause predicted for every test image.

| rung | epochs | best calib loss | test top-1 | test top-3 | floor top-1 | gap to floor (pp) |
|---|---|---|---|---|---|---|
| probe | 5 | 1.9427 | 0.297 | 0.621 | 0.514 (z_offset_high) | -21.7 |
| finetune | 5 | 2.1757 | 0.249 | 0.578 | 0.514 (z_offset_high) | -26.5 |

## probe

Diagnosis (auto; edit after reading the curve): underfit: train top-1 is within 5 pp of the floor; climb a rung or check the labels

| epoch | train loss | train acc | calib loss | calib acc | s |
|---|---|---|---|---|---|
| 1 | 1.9803 | 0.371 | 2.0792 | 0.304 | 120.4 |
| 2 | 1.6607 | 0.459 | 1.9427 | 0.416 | 127.9 |
| 3 | 1.5004 | 0.493 | 2.0708 | 0.342 | 126.0 |
| 4 | 1.4199 | 0.498 | 2.1324 | 0.338 | 118.6 |
| 5 | 1.3485 | 0.510 | 2.0670 | 0.385 | 118.2 |

## finetune

Diagnosis (auto; edit after reading the curve): overfit / part shift: train 0.804 vs calib 0.424; more augmentation or fewer epochs

| epoch | train loss | train acc | calib loss | calib acc | s |
|---|---|---|---|---|---|
| 1 | 1.2691 | 0.529 | 2.3552 | 0.359 | 138.3 |
| 2 | 0.8356 | 0.696 | 2.1757 | 0.415 | 129.1 |
| 3 | 0.6772 | 0.762 | 2.8105 | 0.384 | 159.3 |
| 4 | 0.5848 | 0.794 | 2.3667 | 0.375 | 164.5 |
| 5 | 0.5330 | 0.804 | 2.5320 | 0.424 | 158.8 |
