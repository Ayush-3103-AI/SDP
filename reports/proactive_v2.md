NFR-012: FAIL (median – s, recall 0.00, 0.00 false/h; need ≤ 10 s, ≥ 0.70, ≤ 1 /h; pooled over 5 folds, θ_on from calibration prints)

# Proactive early warning on held-out prints (T-0063)

Predictions: models\cause\v2\a1\recal_t/preds_fold*.npz, replayed per print in ts order through EarlyWarning (β = 0.8, θ_off = 0.4, m = 3, cooldown 60 s, gap reset 10 s). Onset = a cause entering D(i) at a segment start; a warning is true iff its cause is in D at that image; false warnings in the first 6 s of a segment are not counted; missed = no true warning within 30 s or before the segment ends (07 §14). θ_on is chosen per fold on its calibration prints only; the floor is the same rule with β = 0.

Floor (β = 0): median – s, recall 0.00, 0.01 false/h.

## θ_on choice (calibration prints only)

| fold | rung | θ_on | false/h | median ttw (s) | recall@30 s | chosen |
|---|---|---|---|---|---|---|
| 0 | ewma | 0.5 | 0.00 | – | 0.00 | ✔ |
| 0 | ewma | 0.6 | 0.00 | – | 0.00 |  |
| 0 | ewma | 0.7 | 0.00 | – | 0.00 |  |
| 0 | ewma | 0.8 | 0.00 | – | 0.00 |  |
| 0 | floor | 0.5 | 0.00 | – | 0.00 | ✔ |
| 0 | floor | 0.6 | 0.00 | – | 0.00 |  |
| 0 | floor | 0.7 | 0.00 | – | 0.00 |  |
| 0 | floor | 0.8 | 0.00 | – | 0.00 |  |
| 1 | ewma | 0.5 | 0.00 | – | 0.00 | ✔ |
| 1 | ewma | 0.6 | 0.00 | – | 0.00 |  |
| 1 | ewma | 0.7 | 0.00 | – | 0.00 |  |
| 1 | ewma | 0.8 | 0.00 | – | 0.00 |  |
| 1 | floor | 0.5 | 0.00 | 13.0 | 0.00 | ✔ |
| 1 | floor | 0.6 | 0.00 | – | 0.00 |  |
| 1 | floor | 0.7 | 0.00 | – | 0.00 |  |
| 1 | floor | 0.8 | 0.00 | – | 0.00 |  |
| 2 | ewma | 0.5 | 0.00 | – | 0.00 | ✔ |
| 2 | ewma | 0.6 | 0.00 | – | 0.00 |  |
| 2 | ewma | 0.7 | 0.00 | – | 0.00 |  |
| 2 | ewma | 0.8 | 0.00 | – | 0.00 |  |
| 2 | floor | 0.5 | 0.00 | – | 0.00 | ✔ |
| 2 | floor | 0.6 | 0.00 | – | 0.00 |  |
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
| 4 | ewma | 0.5 | 0.00 | – | 0.00 | ✔ |
| 4 | ewma | 0.6 | 0.00 | – | 0.00 |  |
| 4 | ewma | 0.7 | 0.00 | – | 0.00 |  |
| 4 | ewma | 0.8 | 0.00 | – | 0.00 |  |
| 4 | floor | 0.5 | 0.00 | – | 0.00 | ✔ |
| 4 | floor | 0.6 | 0.00 | – | 0.00 |  |
| 4 | floor | 0.7 | 0.00 | – | 0.00 |  |
| 4 | floor | 0.8 | 0.00 | – | 0.00 |  |

## Test prints per fold (frozen θ_on)

| fold | θ_on | prints | hours | onsets | median ttw (s) | recall@30 s | false/h | β = 0 θ_on | β = 0 median | β = 0 recall | β = 0 false/h |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 0.5 | 27 | 27.09 | 1119 | – | 0.00 | 0.00 | 0.5 | – | 0.00 | 0.00 |
| 1 | 0.5 | 67 | 28.67 | 1471 | – | 0.00 | 0.00 | 0.5 | – | 0.00 | 0.03 |
| 2 | 0.5 | 28 | 31.33 | 1240 | – | 0.00 | 0.00 | 0.5 | – | 0.00 | 0.00 |
| 3 | 0.5 | 29 | 28.10 | 1211 | – | 0.00 | 0.00 | 0.5 | – | 0.00 | 0.00 |
| 4 | 0.5 | 29 | 31.86 | 1286 | – | 0.00 | 0.00 | 0.5 | – | 0.00 | 0.00 |

## Per cause (pooled test prints)

| cause | onsets | warned | median ttw (s) | recall@30 s | false | false/h | β = 0 median | β = 0 recall | β = 0 false/h |
|---|---|---|---|---|---|---|---|---|---|
| flow_high | 999 | 0 | – | 0.00 | 0 | 0.00 | – | 0.00 | 0.00 |
| flow_low | 921 | 0 | – | 0.00 | 0 | 0.00 | – | 0.00 | 0.00 |
| nozzle_temp_high | 661 | 0 | – | 0.00 | 0 | 0.00 | – | 0.00 | 0.00 |
| nozzle_temp_low | 1098 | 0 | – | 0.00 | 0 | 0.00 | – | 0.00 | 0.00 |
| speed_high | 958 | 0 | – | 0.00 | 0 | 0.00 | – | 0.00 | 0.00 |
| speed_low | 905 | 0 | – | 0.00 | 0 | 0.00 | – | 0.00 | 0.00 |
| z_offset_high | 731 | 0 | – | 0.00 | 0 | 0.00 | – | 0.00 | 0.01 |
| z_offset_low | 54 | 0 | – | 0.00 | 0 | 0.00 | – | 0.00 | 0.00 |

## Runtime θ_on

models\cause\v2\a1\recal_t\preds_final.npz not found: no runtime θ_on (run train_cause.py --final first).
