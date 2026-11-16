K2: FAIL (top-1 = floor + -3.4 pp ≤ 5 pp)
NFR-005: FAIL (top-1 = floor + -3.4 pp, need ≥ 10; 95 % CI [0.190, 0.254]; top-3 = 0.506, need ≥ 0.9)

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

Predictions: models/cause/single_cached/preds_fold*.npz (5 folds; `multi` rows excluded). CIs: bootstrap over test prints (B = 1000), stratified by fold.

## Result

### Per fold

| fold | test prints | test images | top-1 | 95 % CI | top-3 | floor top-1 | floor top-3 | gap to floor (pp) | gap to oracle | ECE |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 28 | 8088 | 0.248 | [0.156, 0.344] | 0.536 | 0.195 | 0.558 | +5.3 | 0.752 | 0.077 |
| 1 | 49 | 8694 | 0.264 | [0.211, 0.337] | 0.550 | 0.271 | 0.678 | -0.7 | 0.736 | 0.030 |
| 2 | 28 | 7605 | 0.215 | [0.132, 0.323] | 0.486 | 0.228 | 0.602 | -1.3 | 0.785 | 0.110 |
| 3 | 29 | 7108 | 0.179 | [0.137, 0.224] | 0.466 | 0.306 | 0.590 | -12.8 | 0.821 | 0.113 |
| 4 | 29 | 7736 | 0.194 | [0.146, 0.260] | 0.493 | 0.269 | 0.554 | -7.5 | 0.806 | 0.109 |
| mean ± std | 163 | 39231 | 0.220 ± 0.032 | [0.190, 0.254] | 0.506 ± 0.032 | 0.254 ± 0.038 | 0.596 ± 0.045 | -3.4 | 0.780 | 0.088 ± 0.032 |

### Per-class recall (pooled over folds)

| cause | test images | recall |
|---|---|---|
| none | 6968 | 0.515 |
| flow_low | 3168 | 0.164 |
| flow_high | 6574 | 0.292 |
| speed_low | 4761 | 0.152 |
| speed_high | 4128 | 0.070 |
| nozzle_temp_low | 1358 | 0.142 |
| nozzle_temp_high | 830 | 0.107 |
| z_offset_low | 1522 | 0.189 |
| z_offset_high | 9922 | 0.111 |

Balanced accuracy (mean recall over the 9 causes present; report only, not K2): 0.194 (always-majority = 1/9 = 0.111).

### Confusion matrix (pooled; rows = true, columns = predicted)

| true \ pred | none | flow_low | flow_high | speed_low | speed_high | nozzle_temp_low | nozzle_temp_high | z_offset_low | z_offset_high |
|---|---|---|---|---|---|---|---|---|---|
| none | 3589 | 359 | 727 | 630 | 265 | 268 | 350 | 297 | 483 |
| flow_low | 202 | 521 | 188 | 409 | 408 | 424 | 192 | 400 | 424 |
| flow_high | 879 | 458 | 1917 | 731 | 486 | 469 | 539 | 541 | 554 |
| speed_low | 664 | 459 | 497 | 725 | 430 | 477 | 655 | 417 | 437 |
| speed_high | 498 | 508 | 437 | 470 | 287 | 411 | 287 | 623 | 607 |
| nozzle_temp_low | 126 | 157 | 53 | 101 | 89 | 193 | 259 | 200 | 180 |
| nozzle_temp_high | 110 | 69 | 89 | 189 | 57 | 56 | 89 | 109 | 62 |
| z_offset_low | 44 | 211 | 116 | 169 | 202 | 253 | 131 | 287 | 109 |
| z_offset_high | 1591 | 1089 | 1032 | 979 | 1139 | 999 | 744 | 1251 | 1098 |

## Risks

- Most confident wrong test crops: reports/cause_errors.png. What the reviewer saw: <fill in after looking: e.g. mislabelled transition frames, nozzle out of the crop, blur>
- Staleness: trained on CAXTON's nozzle close-up camera, its printer and PLA. A new printer, camera pose or zoom, or material is a new distribution: re-run T-0013 on its data before trusting top-1 (NFR-005) or the conformal coverage (T-0015).
- Within-print leakage reference (random-by-image split on fold 0, SHOULD): not run.
