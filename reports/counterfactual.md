NFR-007: FAIL (direction fidelity 0.723 on 137 confident events, need ≥ 0.85; confident fraction 0.007 of 20819 actionable test images; pooled over 5 folds)

# Counterfactual direction fidelity on confident events (T-0017)

Predictions: models/cause/preds_fold*.npz. Confident = |C| = 1, C ≠ {none}, p_top ≥ τ = 0.6 (L4 would pass), qhat per fold at α = 0.1 from its calibration prints. Fidelity = the top-1 proposal changes the true cause's variable in the undoing direction. Actionable true causes only; none, manual (z_offset) and multi images are excluded.

## Per fold

| fold | qhat | actionable | confident | confident fraction | fidelity |
|---|---|---|---|---|---|
| 0 | 0.9866 | 4594 | 19 | 0.004 | 0.000 |
| 1 | 0.9881 | 3868 | 11 | 0.003 | 0.091 |
| 2 | 0.9874 | 4348 | 2 | 0.000 | 0.000 |
| 3 | 0.9850 | 4075 | 5 | 0.001 | 1.000 |
| 4 | 0.9953 | 3934 | 100 | 0.025 | 0.930 |

## Per cause (pooled)

| cause | var | actionable | confident | confident fraction | fidelity | median abs logged deviation |
|---|---|---|---|---|---|---|
| flow_low | flow | 3168 | 1 | 0.000 | 0.000 | 58 % |
| flow_high | flow | 6574 | 111 | 0.017 | 0.838 | 63 % |
| speed_low | speed | 4761 | 1 | 0.000 | 1.000 | 52 % |
| speed_high | speed | 4128 | 14 | 0.003 | 0.000 | 61 % |
| nozzle_temp_low | nozzle_temp | 1358 | 10 | 0.007 | 0.500 | 15 °C |
| nozzle_temp_high | nozzle_temp | 830 | 0 | 0.000 | – | 18 °C |

Steps-to-undo (07 §9) is not computed: CAXTON's deviation magnitudes vary within a cause, so the median |logged deviation| from the good-class median stands in for it.
