K2: FAIL (top-1 = floor + 4.1 pp ≤ 5 pp)
NFR-005: FAIL (top-1 = floor + 4.1 pp, need ≥ 10; 95 % CI [0.257, 0.336]; top-3 = 0.603, need ≥ 0.9)

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

Predictions: models/cause/recal/preds_fold*.npz (5 folds; `multi` rows excluded). CIs: bootstrap over test prints (B = 1000), stratified by fold.

## Result

### Per fold

| fold | test prints | test images | top-1 | 95 % CI | top-3 | floor top-1 | floor top-3 | gap to floor (pp) | gap to oracle | ECE |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 28 | 8088 | 0.300 | [0.215, 0.414] | 0.567 | 0.195 | 0.558 | +10.5 | 0.700 | 0.046 |
| 1 | 49 | 8694 | 0.301 | [0.232, 0.389] | 0.668 | 0.271 | 0.678 | +3.1 | 0.699 | 0.024 |
| 2 | 28 | 7605 | 0.254 | [0.183, 0.338] | 0.569 | 0.228 | 0.602 | +2.6 | 0.746 | 0.064 |
| 3 | 29 | 7108 | 0.350 | [0.270, 0.449] | 0.619 | 0.306 | 0.590 | +4.4 | 0.650 | 0.099 |
| 4 | 29 | 7736 | 0.267 | [0.179, 0.376] | 0.592 | 0.269 | 0.554 | -0.2 | 0.733 | 0.035 |
| mean ± std | 163 | 39231 | 0.294 ± 0.033 | [0.257, 0.336] | 0.603 ± 0.037 | 0.254 ± 0.038 | 0.596 ± 0.045 | +4.1 | 0.706 | 0.053 ± 0.026 |

### Per-class recall (pooled over folds)

| cause | test images | recall |
|---|---|---|
| none | 6968 | 0.444 |
| flow_low | 3168 | 0.012 |
| flow_high | 6574 | 0.165 |
| speed_low | 4761 | 0.011 |
| speed_high | 4128 | 0.001 |
| nozzle_temp_low | 1358 | 0.000 |
| nozzle_temp_high | 830 | 0.000 |
| z_offset_low | 1522 | 0.000 |
| z_offset_high | 9922 | 0.731 |

Balanced accuracy (mean recall over the 9 causes present; report only, not K2): 0.152 (always-majority = 1/9 = 0.111).

### Confusion matrix (pooled; rows = true, columns = predicted)

| true \ pred | none | flow_low | flow_high | speed_low | speed_high | nozzle_temp_low | nozzle_temp_high | z_offset_low | z_offset_high |
|---|---|---|---|---|---|---|---|---|---|
| none | 3095 | 19 | 532 | 87 | 37 | 4 | 24 | 0 | 3170 |
| flow_low | 108 | 39 | 327 | 12 | 12 | 0 | 0 | 0 | 2670 |
| flow_high | 532 | 23 | 1084 | 51 | 37 | 0 | 1 | 0 | 4846 |
| speed_low | 577 | 13 | 622 | 51 | 5 | 0 | 0 | 0 | 3493 |
| speed_high | 191 | 60 | 381 | 15 | 5 | 0 | 0 | 0 | 3476 |
| nozzle_temp_low | 77 | 1 | 124 | 2 | 6 | 0 | 0 | 0 | 1148 |
| nozzle_temp_high | 92 | 0 | 17 | 4 | 0 | 0 | 0 | 0 | 717 |
| z_offset_low | 39 | 3 | 134 | 3 | 49 | 0 | 0 | 0 | 1294 |
| z_offset_high | 913 | 43 | 1175 | 48 | 485 | 0 | 1 | 0 | 7257 |

## Risks

- Most confident wrong test crops: reports/cause_errors.png. What the reviewer saw: <fill in after looking: e.g. mislabelled transition frames, nozzle out of the crop, blur>
- Staleness: trained on CAXTON's nozzle close-up camera, its printer and PLA. A new printer, camera pose or zoom, or material is a new distribution: re-run T-0013 on its data before trusting top-1 (NFR-005) or the conformal coverage (T-0015).
- Within-print leakage reference (random-by-image split on fold 0, SHOULD): not run.
