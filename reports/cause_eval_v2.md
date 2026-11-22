K2: FAIL (top-1 = floor + 2.2 pp ≤ 5 pp)
NFR-005: FAIL (top-1 = floor + 2.2 pp, need ≥ 10; 95 % CI [0.256, 0.332]; top-3 = 0.629, need ≥ 0.9)

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

Predictions: models\cause\v2\a1/preds_fold*.npz (5 folds; `multi` rows excluded). CIs: bootstrap over test prints (B = 1000), stratified by fold.
- fold 0: 6 epochs, batch 32, best calib loss 1.9726
- fold 1: 7 epochs, batch 32, best calib loss 1.8310
- fold 2: 5 epochs, batch 32, best calib loss 1.9144
- fold 3: 5 epochs, batch 32, best calib loss 1.9483
- fold 4: 5 epochs, batch 32, best calib loss 1.9199

## Result

### Per fold

| fold | test prints | test images | top-1 | 95 % CI | top-3 | floor top-1 | floor top-3 | gap to floor (pp) | gap to oracle | ECE |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 27 | 6663 | 0.282 | [0.213, 0.367] | 0.614 | 0.198 | 0.573 | +8.4 | 0.718 | 0.079 |
| 1 | 46 | 7125 | 0.336 | [0.270, 0.407] | 0.681 | 0.287 | 0.691 | +4.8 | 0.664 | 0.031 |
| 2 | 27 | 6178 | 0.289 | [0.200, 0.390] | 0.646 | 0.247 | 0.625 | +4.2 | 0.711 | 0.012 |
| 3 | 29 | 5944 | 0.287 | [0.214, 0.375] | 0.609 | 0.315 | 0.601 | -2.8 | 0.713 | 0.025 |
| 4 | 27 | 6273 | 0.257 | [0.179, 0.344] | 0.597 | 0.295 | 0.592 | -3.8 | 0.743 | 0.050 |
| mean ± std | 156 | 32183 | 0.290 ± 0.025 | [0.256, 0.332] | 0.629 ± 0.031 | 0.269 ± 0.042 | 0.617 ± 0.041 | +2.2 | 0.710 | 0.039 ± 0.023 |

### Per-class recall (pooled over folds)

| cause | test images | recall |
|---|---|---|
| none | 5594 | 0.456 |
| flow_low | 2725 | 0.003 |
| flow_high | 5683 | 0.157 |
| speed_low | 4121 | 0.028 |
| speed_high | 3503 | 0.016 |
| nozzle_temp_low | 1209 | 0.000 |
| nozzle_temp_high | 721 | 0.000 |
| z_offset_low | 7 | 0.000 |
| z_offset_high | 8620 | 0.667 |

Balanced accuracy (mean recall over the 9 causes present; report only, not K2): 0.147 (always-majority = 1/9 = 0.111).

### Confusion matrix (pooled; rows = true, columns = predicted)

| true \ pred | none | flow_low | flow_high | speed_low | speed_high | nozzle_temp_low | nozzle_temp_high | z_offset_low | z_offset_high |
|---|---|---|---|---|---|---|---|---|---|
| none | 2551 | 3 | 300 | 58 | 42 | 0 | 0 | 0 | 2640 |
| flow_low | 345 | 8 | 164 | 59 | 19 | 0 | 0 | 0 | 2130 |
| flow_high | 1346 | 11 | 891 | 64 | 60 | 0 | 0 | 0 | 3311 |
| speed_low | 1303 | 3 | 402 | 116 | 35 | 0 | 0 | 0 | 2262 |
| speed_high | 550 | 6 | 360 | 19 | 57 | 0 | 0 | 0 | 2511 |
| nozzle_temp_low | 217 | 2 | 196 | 0 | 23 | 0 | 0 | 0 | 771 |
| nozzle_temp_high | 233 | 2 | 13 | 8 | 1 | 0 | 0 | 0 | 464 |
| z_offset_low | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 |
| z_offset_high | 1646 | 43 | 967 | 116 | 96 | 0 | 0 | 0 | 5752 |

## Risks

- Most confident wrong test crops: reports/cause_errors.png. What the reviewer saw: <fill in after looking: e.g. mislabelled transition frames, nozzle out of the crop, blur>
- Staleness: trained on CAXTON's nozzle close-up camera, its printer and PLA. A new printer, camera pose or zoom, or material is a new distribution: re-run T-0013 on its data before trusting top-1 (NFR-005) or the conformal coverage (T-0015).
- Within-print leakage reference (random-by-image split on fold 0, SHOULD): not run.
