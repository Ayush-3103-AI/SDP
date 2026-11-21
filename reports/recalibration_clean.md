# Post-hoc recalibration on calibration prints (2026-11-21)

Source: models/cause/preds_*.npz. q = softmax(log p / T + τ·log π̂), (T, τ) by calib NLL; π̂ = calib label frequencies. Test rows are transformed with these calib-fitted values only (no test choice). Cross-fit = fit on half the calib prints, score the other half: the recipe-comparison score. Window = causal mean log-prob of the last k frames (k by calib NLL), report only.

| preds | T | τ | calib NLL | calib ECE | calib top-1 | calib balanced | calib floor | cross-fit top-1 (− floor) | cross-fit balanced | window k | window calib top-1 | window test top-1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| final | 5.28 | 1.000 | 2.433 → 1.707 | 0.198 → 0.036 | 0.170 → 0.302 | 0.140 → 0.161 | 0.280 | 0.310 (+3.0 pp) | 0.169 | 15 | 0.303 | – |
| fold0 | 4.00 | 0.750 | 2.338 → 1.910 | 0.165 → 0.048 | 0.254 → 0.263 | 0.223 → 0.150 | 0.238 | 0.250 (+1.2 pp) | 0.142 | 15 | 0.265 | 0.308 |
| fold1 | 2.83 | 0.750 | 2.168 → 1.669 | 0.236 → 0.034 | 0.329 → 0.385 | 0.301 → 0.225 | 0.264 | 0.331 (+16.3 pp) | 0.195 | 15 | 0.395 | 0.300 |
| fold2 | 4.29 | 0.750 | 2.404 → 1.805 | 0.242 → 0.053 | 0.223 → 0.313 | 0.198 → 0.148 | 0.302 | 0.311 (+0.9 pp) | 0.145 | 9 | 0.312 | 0.255 |
| fold3 | 7.46 | 1.000 | 2.633 → 1.920 | 0.209 → 0.085 | 0.171 → 0.271 | 0.153 → 0.147 | 0.246 | 0.253 (+5.3 pp) | 0.145 | 15 | 0.274 | 0.343 |
| fold4 | 6.50 | 0.875 | 2.695 → 1.823 | 0.245 → 0.029 | 0.206 → 0.269 | 0.159 → 0.144 | 0.225 | 0.194 (+2.3 pp) | 0.107 | 15 | 0.284 | 0.281 |

Mean cross-fit top-1 − floor over 5 folds: +5.2 pp; balanced 0.147.
