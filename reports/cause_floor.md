# Cause floor (T-0010)

Input: data/crops.csv

Floor = the fold's training-print majority cause, predicted for every test image (07 §9); top-3 = the three most frequent training causes. `multi` rows are excluded.

| fold | majority | top-3 causes | test images | top-1 | top-3 |
|---|---|---|---|---|---|
| 0 | z_offset_high | z_offset_high, speed_low, none | 2912 | 0.514 | 0.704 |
| 1 | z_offset_high | z_offset_high, speed_low, flow_low | 2984 | 0.767 | 0.815 |
| 2 | z_offset_high | z_offset_high, none, speed_low | 2231 | 0.670 | 0.812 |
| 3 | z_offset_high | z_offset_high, none, flow_high | 3278 | 0.628 | 0.742 |
| 4 | z_offset_high | z_offset_high, speed_low, none | 3442 | 0.543 | 0.678 |
| mean ± std | | | 14847 | 0.625 ± 0.091 | 0.750 ± 0.056 |
