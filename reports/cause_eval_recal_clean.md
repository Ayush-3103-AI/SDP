K2: FAIL (top-1 = floor + 2.2 pp ≤ 5 pp)
NFR-005: FAIL (top-1 = floor + 2.2 pp, need ≥ 10; 95 % CI [0.250, 0.335]; top-3 = 0.633, need ≥ 0.9)

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

Predictions: models/cause/recal_clean/preds_fold*.npz (5 folds; `multi` rows excluded). CIs: bootstrap over test prints (B = 1000), stratified by fold.

## Result

### Per fold

| fold | test prints | test images | top-1 | 95 % CI | top-3 | floor top-1 | floor top-3 | gap to floor (pp) | gap to oracle | ECE |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 27 | 6663 | 0.296 | [0.208, 0.406] | 0.578 | 0.198 | 0.573 | +9.7 | 0.704 | 0.062 |
| 1 | 46 | 7125 | 0.295 | [0.221, 0.378] | 0.682 | 0.287 | 0.691 | +0.7 | 0.705 | 0.040 |
| 2 | 27 | 6178 | 0.259 | [0.184, 0.349] | 0.607 | 0.247 | 0.625 | +1.2 | 0.741 | 0.067 |
| 3 | 29 | 5944 | 0.334 | [0.251, 0.442] | 0.665 | 0.315 | 0.601 | +1.9 | 0.666 | 0.077 |
| 4 | 27 | 6273 | 0.269 | [0.178, 0.382] | 0.630 | 0.295 | 0.592 | -2.6 | 0.731 | 0.038 |
| mean ± std | 156 | 32183 | 0.290 ± 0.026 | [0.250, 0.335] | 0.633 ± 0.038 | 0.269 ± 0.042 | 0.617 ± 0.041 | +2.2 | 0.710 | 0.057 ± 0.016 |

### Per-class recall (pooled over folds)

| cause | test images | recall |
|---|---|---|
| none | 5594 | 0.365 |
| flow_low | 2725 | 0.019 |
| flow_high | 5683 | 0.162 |
| speed_low | 4121 | 0.011 |
| speed_high | 3503 | 0.001 |
| nozzle_temp_low | 1209 | 0.000 |
| nozzle_temp_high | 721 | 0.000 |
| z_offset_low | 7 | 0.000 |
| z_offset_high | 8620 | 0.728 |

Balanced accuracy (mean recall over the 9 causes present; report only, not K2): 0.143 (always-majority = 1/9 = 0.111).

### Confusion matrix (pooled; rows = true, columns = predicted)

| true \ pred | none | flow_low | flow_high | speed_low | speed_high | nozzle_temp_low | nozzle_temp_high | z_offset_low | z_offset_high |
|---|---|---|---|---|---|---|---|---|---|
| none | 2044 | 24 | 461 | 88 | 25 | 5 | 26 | 0 | 2921 |
| flow_low | 62 | 52 | 256 | 14 | 9 | 0 | 0 | 0 | 2332 |
| flow_high | 314 | 25 | 918 | 38 | 17 | 0 | 1 | 0 | 4370 |
| speed_low | 407 | 26 | 505 | 46 | 3 | 0 | 0 | 0 | 3134 |
| speed_high | 88 | 61 | 335 | 9 | 4 | 0 | 0 | 0 | 3006 |
| nozzle_temp_low | 59 | 3 | 145 | 0 | 6 | 0 | 0 | 0 | 996 |
| nozzle_temp_high | 80 | 0 | 16 | 3 | 0 | 0 | 0 | 0 | 622 |
| z_offset_low | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 |
| z_offset_high | 725 | 54 | 1080 | 48 | 433 | 0 | 1 | 0 | 6279 |

## Risks

- Most confident wrong test crops: reports/cause_errors.png. What the reviewer saw: <fill in after looking: e.g. mislabelled transition frames, nozzle out of the crop, blur>
- Staleness: trained on CAXTON's nozzle close-up camera, its printer and PLA. A new printer, camera pose or zoom, or material is a new distribution: re-run T-0013 on its data before trusting top-1 (NFR-005) or the conformal coverage (T-0015).
- Within-print leakage reference (random-by-image split on fold 0, SHOULD): not run.
