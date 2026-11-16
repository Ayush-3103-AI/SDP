# Cause floor (T-0010)

Input: data/crops.csv

Floor = the fold's training-print majority cause, predicted for every test image (07 §9); top-3 = the three most frequent training causes. `multi` rows are excluded.

| fold | majority | top-3 causes | test images | top-1 | top-3 |
|---|---|---|---|---|---|
| 0 | z_offset_high | z_offset_high, flow_high, none | 8088 | 0.195 | 0.558 |
| 1 | z_offset_high | z_offset_high, flow_high, none | 8694 | 0.271 | 0.678 |
| 2 | z_offset_high | z_offset_high, none, flow_high | 7605 | 0.228 | 0.602 |
| 3 | z_offset_high | z_offset_high, none, flow_high | 7108 | 0.306 | 0.590 |
| 4 | z_offset_high | z_offset_high, flow_high, none | 7736 | 0.269 | 0.554 |
| mean ± std | | | 39231 | 0.254 ± 0.038 | 0.596 ± 0.045 |
