K2: FAIL (top-1 = floor + -9.0 pp ≤ 5 pp)
NFR-005: FAIL (top-1 = floor + -9.0 pp, need ≥ 10; 95 % CI [0.140, 0.193]; top-3 = 0.425, need ≥ 0.9)

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

Predictions: models/cause/multi_cached/preds_fold*.npz (5 folds; `multi` rows excluded). CIs: bootstrap over test prints (B = 1000), stratified by fold.

## Result

### Per fold

| fold | test prints | test images | top-1 | 95 % CI | top-3 | floor top-1 | floor top-3 | gap to floor (pp) | gap to oracle | ECE |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 28 | 8088 | 0.178 | [0.121, 0.253] | 0.437 | 0.195 | 0.558 | -1.7 | 0.822 | 0.025 |
| 1 | 49 | 8694 | 0.188 | [0.153, 0.229] | 0.477 | 0.271 | 0.678 | -8.3 | 0.812 | 0.067 |
| 2 | 28 | 7605 | 0.179 | [0.101, 0.298] | 0.397 | 0.228 | 0.602 | -5.0 | 0.821 | 0.036 |
| 3 | 29 | 7108 | 0.152 | [0.121, 0.186] | 0.434 | 0.306 | 0.590 | -15.5 | 0.848 | 0.027 |
| 4 | 29 | 7736 | 0.121 | [0.091, 0.156] | 0.382 | 0.269 | 0.554 | -14.8 | 0.879 | 0.076 |
| mean ± std | 163 | 39231 | 0.163 ± 0.025 | [0.140, 0.193] | 0.425 ± 0.033 | 0.254 ± 0.038 | 0.596 ± 0.045 | -9.0 | 0.837 | 0.046 ± 0.021 |

### Per-class recall (pooled over folds)

| cause | test images | recall |
|---|---|---|
| none | 6968 | 0.170 |
| flow_low | 3168 | 0.100 |
| flow_high | 6574 | 0.277 |
| speed_low | 4761 | 0.224 |
| speed_high | 4128 | 0.092 |
| nozzle_temp_low | 1358 | 0.060 |
| nozzle_temp_high | 830 | 0.067 |
| z_offset_low | 1522 | 0.376 |
| z_offset_high | 9922 | 0.097 |

Balanced accuracy (mean recall over the 9 causes present; report only, not K2): 0.163 (always-majority = 1/9 = 0.111).

### Confusion matrix (pooled; rows = true, columns = predicted)

| true \ pred | none | flow_low | flow_high | speed_low | speed_high | nozzle_temp_low | nozzle_temp_high | z_offset_low | z_offset_high |
|---|---|---|---|---|---|---|---|---|---|
| none | 1187 | 540 | 1016 | 1243 | 463 | 458 | 564 | 641 | 856 |
| flow_low | 301 | 317 | 139 | 373 | 451 | 166 | 184 | 828 | 409 |
| flow_high | 346 | 502 | 1823 | 786 | 555 | 187 | 403 | 1195 | 777 |
| speed_low | 248 | 485 | 518 | 1068 | 319 | 291 | 345 | 1012 | 475 |
| speed_high | 273 | 571 | 325 | 466 | 381 | 213 | 278 | 1134 | 487 |
| nozzle_temp_low | 84 | 152 | 123 | 78 | 98 | 81 | 103 | 452 | 187 |
| nozzle_temp_high | 77 | 60 | 119 | 142 | 41 | 43 | 56 | 222 | 70 |
| z_offset_low | 117 | 124 | 83 | 142 | 208 | 88 | 101 | 572 | 87 |
| z_offset_high | 953 | 940 | 877 | 1157 | 1050 | 615 | 730 | 2640 | 960 |

## Risks

- Most confident wrong test crops: reports/cause_errors.png. What the reviewer saw: <fill in after looking: e.g. mislabelled transition frames, nozzle out of the crop, blur>
- Staleness: trained on CAXTON's nozzle close-up camera, its printer and PLA. A new printer, camera pose or zoom, or material is a new distribution: re-run T-0013 on its data before trusting top-1 (NFR-005) or the conformal coverage (T-0015).
- Within-print leakage reference (random-by-image split on fold 0, SHOULD): not run.
