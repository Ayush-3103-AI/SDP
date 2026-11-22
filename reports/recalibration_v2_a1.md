# Post-hoc recalibration on calibration prints (2026-11-21)

Source: models/cause/v2/a1/preds_*.npz. q = softmax(log p / T + τ·log π̂), (T, τ) by calib NLL; π̂ = calib label frequencies. Test rows are transformed with these calib-fitted values only (no test choice). Cross-fit = fit on half the calib prints, score the other half: the recipe-comparison score. Window = causal mean log-prob of the last k frames (k by calib NLL), report only.

| preds | T | τ | calib NLL | calib ECE | calib top-1 | calib balanced | calib floor | cross-fit top-1 (− floor) | cross-fit balanced | window k | window calib top-1 | window test top-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fold0 | 2.30 | 0.500 | 1.973 → 1.925 | 0.060 → 0.052 | 0.282 → 0.281 | 0.175 → 0.159 | 0.238 | 0.284 (+4.5 pp) | 0.164 | 15 | 0.289 | 0.255 |
| fold1 | 1.74 | 0.500 | 1.831 → 1.783 | 0.058 → 0.033 | 0.305 → 0.307 | 0.176 → 0.157 | 0.264 | 0.235 (+6.7 pp) | 0.119 | 15 | 0.317 | 0.335 |

Mean cross-fit top-1 − floor over 2 folds: +5.6 pp; balanced 0.142.
