NFR-006: FAIL (coverage 0.910, need ≥ 0.85; mean set size 5.65, need ≤ 2.0; α = 0.1, mean over 5 folds)

# Conformal coverage on the leave-parts-out folds (T-0015)

Predictions: models\cause\v2\a1\recal_t/preds_fold*.npz. qhat per fold from its calibration prints (training prints); coverage on its held-out test prints; `multi` rows excluded. Leave-parts-out is a shift, so the 1 − α guarantee does not hold: these are empirical values (07 §8).

## Per fold

| fold | α | calib images | qhat | test images | coverage | mean set size |
|---|---|---|---|---|---|---|
| 0 | 0.05 | 4680 | 0.9380 | 6663 | 0.902 | 5.87 |
| 0 | 0.1 | 4680 | 0.9239 | 6663 | 0.867 | 5.35 |
| 0 | 0.2 | 4680 | 0.9094 | 6663 | 0.824 | 4.78 |
| 1 | 0.05 | 5627 | 0.9503 | 7125 | 0.936 | 6.11 |
| 1 | 0.1 | 5627 | 0.9311 | 7125 | 0.877 | 5.23 |
| 1 | 0.2 | 5627 | 0.9036 | 7125 | 0.794 | 4.13 |
| 2 | 0.05 | 5860 | 0.9469 | 6178 | 0.938 | 6.40 |
| 2 | 0.1 | 5860 | 0.9288 | 6178 | 0.903 | 5.56 |
| 2 | 0.2 | 5860 | 0.9063 | 6178 | 0.804 | 4.47 |
| 3 | 0.05 | 6066 | 0.9570 | 5944 | 0.995 | 7.10 |
| 3 | 0.1 | 6066 | 0.9362 | 5944 | 0.950 | 6.14 |
| 3 | 0.2 | 6066 | 0.9079 | 5944 | 0.833 | 4.75 |
| 4 | 0.05 | 4851 | 0.9497 | 6273 | 0.984 | 6.73 |
| 4 | 0.1 | 4851 | 0.9351 | 6273 | 0.951 | 5.97 |
| 4 | 0.2 | 4851 | 0.9090 | 6273 | 0.813 | 4.60 |

## Mean over folds

| α | target 1 − α | coverage | mean set size |
|---|---|---|---|
| 0.05 | 0.95 | 0.951 | 6.44 |
| 0.1 | 0.90 | 0.910 | 5.65 |
| 0.2 | 0.80 | 0.814 | 4.55 |

## Set sizes at α = 0.1 (pooled)

| set size | test images | share |
|---|---|---|
| 2 | 27 | 0.001 |
| 3 | 289 | 0.009 |
| 4 | 3037 | 0.094 |
| 5 | 10151 | 0.315 |
| 6 | 13680 | 0.425 |
| 7 | 4731 | 0.147 |
| 8 | 268 | 0.008 |

## Coverage per cause at α = 0.1 (pooled)

| cause | test images | coverage |
|---|---|---|
| none | 5594 | 0.964 |
| flow_low | 2725 | 0.774 |
| flow_high | 5683 | 0.977 |
| speed_low | 4121 | 0.932 |
| speed_high | 3503 | 0.966 |
| nozzle_temp_low | 1209 | 0.191 |
| nozzle_temp_high | 721 | 0.118 |
| z_offset_low | 7 | 0.000 |
| z_offset_high | 8620 | 1.000 |

## Runtime qhat

models\cause\v2\a1\recal_t\preds_final.npz not found: qhat.json not written (run train_cause.py --final first).
