# Post-hoc recalibration on calibration prints (2026-11-21)

Source: models/cause/preds_*.npz. q = softmax(log p / T + τ·log π̂), (T, τ) by calib NLL; π̂ = calib label frequencies. Test rows are transformed with these calib-fitted values only (no test choice). Cross-fit = fit on half the calib prints, score the other half: the recipe-comparison score. Window = causal mean log-prob of the last k frames (k by calib NLL), report only.

| preds | T | τ | calib NLL | calib ECE | calib top-1 | calib balanced | calib floor | cross-fit top-1 (− floor) | cross-fit balanced | window k | window calib top-1 | window test top-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| final | 3.25 | 0.000 | 2.406 → 2.127 | 0.195 → 0.025 | 0.179 → 0.179 | 0.141 → 0.141 | 0.265 | 0.179 (-8.6 pp) | 0.141 | 15 | 0.203 | – |
| fold0 | 2.83 | 0.000 | 2.370 → 2.081 | 0.173 → 0.038 | 0.250 → 0.250 | 0.203 → 0.203 | 0.221 | 0.250 (+2.9 pp) | 0.203 | 15 | 0.272 | 0.216 |
| fold1 | 2.30 | 0.000 | 2.176 → 1.851 | 0.244 → 0.045 | 0.322 → 0.322 | 0.274 → 0.274 | 0.247 | 0.322 (+16.2 pp) | 0.274 | 15 | 0.336 | 0.206 |
| fold2 | 2.64 | 0.000 | 2.365 → 2.038 | 0.233 → 0.043 | 0.233 → 0.233 | 0.209 → 0.209 | 0.293 | 0.233 (-6.0 pp) | 0.209 | 15 | 0.251 | 0.226 |
| fold3 | 5.28 | 0.000 | 2.570 → 2.170 | 0.204 → 0.024 | 0.178 → 0.178 | 0.151 → 0.151 | 0.233 | 0.178 (-1.9 pp) | 0.151 | 15 | 0.185 | 0.210 |
| fold4 | 4.29 | 0.000 | 2.671 → 2.117 | 0.251 → 0.039 | 0.200 → 0.200 | 0.161 → 0.161 | 0.229 | 0.200 (+1.8 pp) | 0.161 | 15 | 0.227 | 0.245 |

Mean cross-fit top-1 − floor over 5 folds: +2.6 pp; balanced 0.200.
