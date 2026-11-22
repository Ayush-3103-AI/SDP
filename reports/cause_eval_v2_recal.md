K2: FAIL (top-1 = floor + 1.7 pp ≤ 5 pp)
NFR-005: FAIL (top-1 = floor + 1.7 pp, need ≥ 10; 95 % CI [0.252, 0.325]; top-3 = 0.617, need ≥ 0.9)

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

Predictions: models\cause\v2\a1\recal/preds_fold*.npz (5 folds; `multi` rows excluded). CIs: bootstrap over test prints (B = 1000), stratified by fold.

## Result

### Per fold

| fold | test prints | test images | top-1 | 95 % CI | top-3 | floor top-1 | floor top-3 | gap to floor (pp) | gap to oracle | ECE |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 27 | 6663 | 0.252 | [0.192, 0.310] | 0.598 | 0.198 | 0.573 | +5.4 | 0.748 | 0.035 |
| 1 | 46 | 7125 | 0.332 | [0.268, 0.405] | 0.696 | 0.287 | 0.691 | +4.5 | 0.668 | 0.032 |
| 2 | 27 | 6178 | 0.247 | [0.161, 0.349] | 0.590 | 0.247 | 0.625 | +0.0 | 0.753 | 0.059 |
| 3 | 29 | 5944 | 0.314 | [0.242, 0.408] | 0.605 | 0.315 | 0.601 | -0.1 | 0.686 | 0.048 |
| 4 | 27 | 6273 | 0.284 | [0.205, 0.378] | 0.597 | 0.295 | 0.592 | -1.1 | 0.716 | 0.036 |
| mean ± std | 156 | 32183 | 0.286 ± 0.033 | [0.252, 0.325] | 0.617 ± 0.040 | 0.269 ± 0.042 | 0.617 ± 0.041 | +1.7 | 0.714 | 0.042 ± 0.010 |

### Per-class recall (pooled over folds)

| cause | test images | recall |
|---|---|---|
| none | 5594 | 0.241 |
| flow_low | 2725 | 0.000 |
| flow_high | 5683 | 0.049 |
| speed_low | 4121 | 0.005 |
| speed_high | 3503 | 0.000 |
| nozzle_temp_low | 1209 | 0.000 |
| nozzle_temp_high | 721 | 0.000 |
| z_offset_low | 7 | 0.000 |
| z_offset_high | 8620 | 0.879 |

Balanced accuracy (mean recall over the 9 causes present; report only, not K2): 0.130 (always-majority = 1/9 = 0.111).

### Confusion matrix (pooled; rows = true, columns = predicted)

| true \ pred | none | flow_low | flow_high | speed_low | speed_high | nozzle_temp_low | nozzle_temp_high | z_offset_low | z_offset_high |
|---|---|---|---|---|---|---|---|---|---|
| none | 1349 | 0 | 97 | 6 | 0 | 0 | 0 | 0 | 4142 |
| flow_low | 61 | 0 | 65 | 6 | 0 | 0 | 0 | 0 | 2593 |
| flow_high | 357 | 0 | 278 | 1 | 0 | 0 | 0 | 0 | 5047 |
| speed_low | 371 | 0 | 231 | 22 | 0 | 0 | 0 | 0 | 3497 |
| speed_high | 164 | 0 | 131 | 0 | 0 | 0 | 0 | 0 | 3208 |
| nozzle_temp_low | 80 | 0 | 58 | 0 | 0 | 0 | 0 | 0 | 1071 |
| nozzle_temp_high | 61 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 654 |
| z_offset_low | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 |
| z_offset_high | 649 | 0 | 394 | 1 | 0 | 0 | 0 | 0 | 7576 |

## Risks

- Most confident wrong test crops: reports/cause_errors.png. What the reviewer saw: <fill in after looking: e.g. mislabelled transition frames, nozzle out of the crop, blur>
- Staleness: trained on CAXTON's nozzle close-up camera, its printer and PLA. A new printer, camera pose or zoom, or material is a new distribution: re-run T-0013 on its data before trusting top-1 (NFR-005) or the conformal coverage (T-0015).
- Within-print leakage reference (random-by-image split on fold 0, SHOULD): not run.
