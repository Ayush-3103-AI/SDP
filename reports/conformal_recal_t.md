NFR-006: FAIL (coverage 0.918, need ≥ 0.85; mean set size 7.11, need ≤ 2.0; α = 0.1, mean over 5 folds)

# Conformal coverage on the leave-parts-out folds (T-0015)

Predictions: models\cause\recal_t/preds_fold*.npz. qhat per fold from its calibration prints (training prints); coverage on its held-out test prints; `multi` rows excluded. Leave-parts-out is a shift, so the 1 − α guarantee does not hold: these are empirical values (07 §8).

## Per fold

| fold | α | calib images | qhat | test images | coverage | mean set size |
|---|---|---|---|---|---|---|
| 0 | 0.05 | 5743 | 0.9444 | 8088 | 0.935 | 7.52 |
| 0 | 0.1 | 5743 | 0.9353 | 8088 | 0.892 | 6.88 |
| 0 | 0.2 | 5743 | 0.9213 | 8088 | 0.833 | 5.82 |
| 1 | 0.05 | 6827 | 0.9584 | 8694 | 0.936 | 7.31 |
| 1 | 0.1 | 6827 | 0.9429 | 8694 | 0.881 | 6.42 |
| 1 | 0.2 | 6827 | 0.9159 | 8694 | 0.764 | 4.92 |
| 2 | 0.05 | 7031 | 0.9507 | 7605 | 0.948 | 7.80 |
| 2 | 0.1 | 7031 | 0.9378 | 7605 | 0.908 | 6.94 |
| 2 | 0.2 | 7031 | 0.9175 | 7605 | 0.782 | 5.54 |
| 3 | 0.05 | 7435 | 0.9192 | 7108 | 0.992 | 8.34 |
| 3 | 0.1 | 7435 | 0.9123 | 7108 | 0.978 | 7.81 |
| 3 | 0.2 | 7435 | 0.9047 | 7108 | 0.928 | 6.93 |
| 4 | 0.05 | 5845 | 0.9427 | 7736 | 0.968 | 8.21 |
| 4 | 0.1 | 5845 | 0.9302 | 7736 | 0.929 | 7.51 |
| 4 | 0.2 | 5845 | 0.9088 | 7736 | 0.806 | 5.84 |

## Mean over folds

| α | target 1 − α | coverage | mean set size |
|---|---|---|---|
| 0.05 | 0.95 | 0.956 | 7.84 |
| 0.1 | 0.90 | 0.918 | 7.11 |
| 0.2 | 0.80 | 0.823 | 5.81 |

## Set sizes at α = 0.1 (pooled)

| set size | test images | share |
|---|---|---|
| 1 | 73 | 0.002 |
| 2 | 311 | 0.008 |
| 3 | 772 | 0.020 |
| 4 | 1885 | 0.048 |
| 5 | 3476 | 0.089 |
| 6 | 6293 | 0.160 |
| 7 | 8300 | 0.212 |
| 8 | 9070 | 0.231 |
| 9 | 9051 | 0.231 |

## Coverage per cause at α = 0.1 (pooled)

| cause | test images | coverage |
|---|---|---|
| none | 6968 | 0.927 |
| flow_low | 3168 | 0.933 |
| flow_high | 6574 | 0.954 |
| speed_low | 4761 | 0.871 |
| speed_high | 4128 | 0.898 |
| nozzle_temp_low | 1358 | 0.574 |
| nozzle_temp_high | 830 | 0.587 |
| z_offset_low | 1522 | 0.954 |
| z_offset_high | 9922 | 0.973 |

## Runtime qhat

models\cause\recal_t\qhat.json: qhat = 0.9214 at α = 0.1 from 5657 calibration images of models\cause\recal_t\preds_final.npz.
