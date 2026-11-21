NFR-012: FAIL (median 1.6 s, recall 0.00, 0.08 false/h; need ≤ 10 s, ≥ 0.70, ≤ 1 /h; pooled over 5 folds, θ_on from calibration prints)

# Proactive early warning on held-out prints (T-0063)

Predictions: models\cause\recal_t/preds_fold*.npz, replayed per print in ts order through EarlyWarning (β = 0.8, θ_off = 0.4, m = 3, cooldown 60 s, gap reset 10 s). Onset = a cause entering D(i) at a segment start; a warning is true iff its cause is in D at that image; false warnings in the first 6 s of a segment are not counted; missed = no true warning within 30 s or before the segment ends (07 §14). θ_on is chosen per fold on its calibration prints only; the floor is the same rule with β = 0.

Floor (β = 0): median 12.8 s, recall 0.00, 0.16 false/h.

## θ_on choice (calibration prints only)

| fold | rung | θ_on | false/h | median ttw (s) | recall@30 s | chosen |
|---|---|---|---|---|---|---|
| 0 | ewma | 0.5 | 0.04 | – | 0.00 | ✔ |
| 0 | ewma | 0.6 | 0.00 | – | 0.00 |  |
| 0 | ewma | 0.7 | 0.00 | – | 0.00 |  |
| 0 | ewma | 0.8 | 0.00 | – | 0.00 |  |
| 0 | floor | 0.5 | 0.04 | – | 0.00 | ✔ |
| 0 | floor | 0.6 | 0.00 | – | 0.00 |  |
| 0 | floor | 0.7 | 0.00 | – | 0.00 |  |
| 0 | floor | 0.8 | 0.00 | – | 0.00 |  |
| 1 | ewma | 0.5 | 0.04 | 11.6 | 0.00 | ✔ |
| 1 | ewma | 0.6 | 0.04 | 3.7 | 0.00 |  |
| 1 | ewma | 0.7 | 0.04 | 11.2 | 0.00 |  |
| 1 | ewma | 0.8 | 0.00 | 18.4 | 0.00 |  |
| 1 | floor | 0.5 | 0.13 | 11.1 | 0.00 | ✔ |
| 1 | floor | 0.6 | 0.04 | 8.1 | 0.00 |  |
| 1 | floor | 0.7 | 0.04 | 3.7 | 0.00 |  |
| 1 | floor | 0.8 | 0.04 | 3.7 | 0.00 |  |
| 2 | ewma | 0.5 | 0.00 | 8.8 | 0.00 | ✔ |
| 2 | ewma | 0.6 | 0.00 | – | 0.00 |  |
| 2 | ewma | 0.7 | 0.00 | – | 0.00 |  |
| 2 | ewma | 0.8 | 0.00 | – | 0.00 |  |
| 2 | floor | 0.5 | 0.07 | 3.7 | 0.00 | ✔ |
| 2 | floor | 0.6 | 0.00 | 21.4 | 0.00 |  |
| 2 | floor | 0.7 | 0.00 | – | 0.00 |  |
| 2 | floor | 0.8 | 0.00 | – | 0.00 |  |
| 3 | ewma | 0.5 | 0.00 | – | 0.00 | ✔ |
| 3 | ewma | 0.6 | 0.00 | – | 0.00 |  |
| 3 | ewma | 0.7 | 0.00 | – | 0.00 |  |
| 3 | ewma | 0.8 | 0.00 | – | 0.00 |  |
| 3 | floor | 0.5 | 0.00 | – | 0.00 | ✔ |
| 3 | floor | 0.6 | 0.00 | – | 0.00 |  |
| 3 | floor | 0.7 | 0.00 | – | 0.00 |  |
| 3 | floor | 0.8 | 0.00 | – | 0.00 |  |
| 4 | ewma | 0.5 | 0.18 | – | 0.00 | ✔ |
| 4 | ewma | 0.6 | 0.05 | – | 0.00 |  |
| 4 | ewma | 0.7 | 0.00 | – | 0.00 |  |
| 4 | ewma | 0.8 | 0.00 | – | 0.00 |  |
| 4 | floor | 0.5 | 0.23 | 13.9 | 0.00 | ✔ |
| 4 | floor | 0.6 | 0.05 | 29.7 | 0.00 |  |
| 4 | floor | 0.7 | 0.00 | – | 0.00 |  |
| 4 | floor | 0.8 | 0.00 | – | 0.00 |  |

## Test prints per fold (frozen θ_on)

| fold | θ_on | prints | hours | onsets | median ttw (s) | recall@30 s | false/h | β = 0 θ_on | β = 0 median | β = 0 recall | β = 0 false/h |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 0.5 | 28 | 27.34 | 1598 | – | 0.00 | 0.00 | 0.5 | – | 0.00 | 0.04 |
| 1 | 0.5 | 67 | 29.03 | 2007 | 2.3 | 0.00 | 0.28 | 0.5 | 12.6 | 0.00 | 0.45 |
| 2 | 0.5 | 28 | 31.44 | 1692 | 0.9 | 0.00 | 0.06 | 0.5 | – | 0.00 | 0.25 |
| 3 | 0.5 | 29 | 28.28 | 1715 | – | 0.00 | 0.00 | 0.5 | – | 0.00 | 0.00 |
| 4 | 0.5 | 29 | 32.22 | 1799 | – | 0.00 | 0.06 | 0.5 | 13.0 | 0.00 | 0.03 |

## Per cause (pooled test prints)

| cause | onsets | warned | median ttw (s) | recall@30 s | false | false/h | β = 0 median | β = 0 recall | β = 0 false/h |
|---|---|---|---|---|---|---|---|---|---|
| flow_high | 1138 | 2 | 1.6 | 0.00 | 3 | 0.02 | 7.7 | 0.00 | 0.03 |
| flow_low | 1050 | 0 | – | 0.00 | 1 | 0.01 | – | 0.00 | 0.00 |
| nozzle_temp_high | 793 | 0 | – | 0.00 | 0 | 0.00 | – | 0.00 | 0.03 |
| nozzle_temp_low | 1230 | 0 | – | 0.00 | 0 | 0.00 | – | 0.00 | 0.01 |
| speed_high | 1075 | 0 | – | 0.00 | 6 | 0.04 | – | 0.00 | 0.07 |
| speed_low | 1044 | 0 | – | 0.00 | 1 | 0.01 | 12.6 | 0.00 | 0.02 |
| z_offset_high | 1425 | 2 | 13.8 | 0.00 | 1 | 0.01 | 25.8 | 0.00 | 0.01 |
| z_offset_low | 1056 | 0 | – | 0.00 | 0 | 0.00 | – | 0.00 | 0.00 |

## Runtime θ_on

θ_on = 0.5 from the calibration prints of models\cause\recal_t\preds_final.npz (set cfg.proactive.theta_on; the config has 0.6).
