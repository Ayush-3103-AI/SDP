K2: FAIL (top-1 = floor + -18.0 pp ≤ 5 pp)
NFR-005: FAIL (top-1 = floor + -18.0 pp, need ≥ 10; 95 % CI [0.381, 0.532]; top-3 = 0.694, need ≥ 0.9)

# Cause model evaluation (T-0010, T-0013)

## Frame

- Decision: which setpoint proposal(s) the operator sees for a confirmed defect.
- Unit: one 224 px crop (nozzle ROI, or a confirmed defect box) at decision time.
- Target: the image's process deviation (07 §15 label rule).
- Metric: LOGO mean top-1 (NFR-005). Error cost: a wrong actionable cause proposes a
  wrong-direction change (bounded by the gate), so per-class recall on actionable causes
  is the main diagnostic.
- Baseline: the floor, i.e. the training prints' majority cause (T-0010; CAXTON has no defect class).

## Baseline

Floor = the fold's training-print majority cause, predicted for every test image (07 §9; reports/cause_floor.md). Oracle = the CAXTON parameter class (top-1 = 1.0), so gap to oracle = 1 − top-1. K2 fires at ≤ floor + 5 pp (charter); NFR-005 needs ≥ floor + 10 pp and top-3 ≥ 0.90.

## Model

Predictions: models/cause/finetune/preds_fold*.npz (5 folds; `multi` rows excluded). CIs: bootstrap over test prints (B = 1000), stratified by fold.

Rung: finetune (fine-tune mean top-1 0.445 vs probe 0.327 ± 0.022; the fine-tune is chosen only if it beats the probe by more than the probe's fold std)
- fold 0: 5 epochs, batch 32, best calib loss 2.1757
- fold 1: 4 epochs, batch 32, best calib loss 2.0051
- fold 2: 7 epochs, batch 32, best calib loss 1.8037
- fold 3: 6 epochs, batch 32, best calib loss 2.5424
- fold 4: 7 epochs, batch 32, best calib loss 2.2200

## Result

### Per fold

| fold | test prints | test images | top-1 | 95 % CI | top-3 | floor top-1 | floor top-3 | gap to floor (pp) | gap to oracle | ECE |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 20 | 2912 | 0.249 | [0.142, 0.380] | 0.578 | 0.514 | 0.704 | -26.5 | 0.751 | 0.485 |
| 1 | 27 | 2984 | 0.474 | [0.309, 0.643] | 0.721 | 0.767 | 0.815 | -29.3 | 0.526 | 0.158 |
| 2 | 20 | 2231 | 0.533 | [0.349, 0.731] | 0.711 | 0.670 | 0.812 | -13.6 | 0.467 | 0.205 |
| 3 | 20 | 3278 | 0.511 | [0.364, 0.713] | 0.758 | 0.628 | 0.742 | -11.7 | 0.489 | 0.263 |
| 4 | 24 | 3442 | 0.457 | [0.324, 0.643] | 0.699 | 0.543 | 0.678 | -8.7 | 0.543 | 0.291 |
| mean ± std | 111 | 14847 | 0.445 ± 0.102 | [0.381, 0.532] | 0.694 ± 0.061 | 0.625 ± 0.091 | 0.750 ± 0.056 | -18.0 | 0.555 | 0.280 ± 0.112 |

### Per-class recall (pooled over folds)

| cause | test images | recall |
|---|---|---|
| none | 1234 | 0.372 |
| flow_low | 787 | 0.020 |
| flow_high | 930 | 0.004 |
| speed_low | 1124 | 0.046 |
| speed_high | 740 | 0.135 |
| nozzle_temp_low | 392 | 0.000 |
| nozzle_temp_high | 137 | 0.022 |
| z_offset_low | 293 | 0.283 |
| z_offset_high | 9210 | 0.636 |

### Confusion matrix (pooled; rows = true, columns = predicted)

| true \ pred | none | flow_low | flow_high | speed_low | speed_high | nozzle_temp_low | nozzle_temp_high | z_offset_low | z_offset_high |
|---|---|---|---|---|---|---|---|---|---|
| none | 459 | 160 | 7 | 8 | 89 | 0 | 10 | 14 | 487 |
| flow_low | 32 | 16 | 5 | 19 | 0 | 0 | 4 | 114 | 597 |
| flow_high | 369 | 79 | 4 | 4 | 5 | 14 | 8 | 11 | 436 |
| speed_low | 106 | 114 | 11 | 52 | 6 | 0 | 14 | 35 | 786 |
| speed_high | 19 | 99 | 0 | 4 | 100 | 0 | 1 | 109 | 408 |
| nozzle_temp_low | 3 | 17 | 0 | 6 | 39 | 0 | 0 | 114 | 213 |
| nozzle_temp_high | 1 | 8 | 0 | 6 | 8 | 0 | 3 | 3 | 108 |
| z_offset_low | 12 | 9 | 2 | 16 | 8 | 0 | 0 | 83 | 163 |
| z_offset_high | 551 | 760 | 460 | 271 | 315 | 178 | 105 | 711 | 5859 |

## Risks

- Most confident wrong test crops: reports/cause_errors.png. What the reviewer saw: misclassifications predominantly occurring at parameter transition points, subtle visual distinction between under-extrusion/speed versus z-offset, and heavy majority-class bias toward z_offset_high.
- Staleness: trained on CAXTON's nozzle close-up camera, its printer and PLA. A new printer, camera pose or zoom, or material is a new distribution: re-run T-0013 on its data before trusting top-1 (NFR-005) or the conformal coverage (T-0015).
- Within-print leakage reference (random-by-image split on fold 0, SHOULD): not run.
