# Deck-recipe audit (T-0023)

Each DECK_RECIPE pushed from the nominal setpoints through the gate (no cooldown pending).
"Raw recipe breaks" is what baseline mode (APPLY_RAW) would send past: the L2 step limit, L1, or L3.

| recipe | variable | from → target | Δ | raw recipe breaks | gate | layer | why |
|---|---|---|---|---|---|---|---|
| over_extrusion | nozzle_temp | 210 → 190 | -20 | step, L3 | pass → 205 | L2 | L2: clipped -20 → -5 °C |
| over_extrusion | speed | 100 → 95 | -5 | – | pass → 95 | – | L3: 95 % within [80, 110] |
| over_extrusion | flow | 100 → 80 | -20 | step, L3 | pass → 90 | L2 | L2: clipped -20 → -10 % |
| under_extrusion | nozzle_temp | 210 → 205 | -5 | – | pass → 205 | – | L3: 205 °C within [195, 225] |
| under_extrusion | speed | 100 → 80 | -20 | step | pass → 90 | L2 | L2: clipped -20 → -10 % |
| under_extrusion | flow | 100 → 110 | +10 | – | pass → 110 | – | L3: 110 % within [90, 110] |
| stringing | nozzle_temp | 210 → 190 | -20 | step, L3 | pass → 205 | L2 | L2: clipped -20 → -5 °C |
| stringing | speed | 100 → 80 | -20 | step | pass → 90 | L2 | L2: clipped -20 → -10 % |
| stringing | flow | 100 → 95 | -5 | – | pass → 95 | – | L3: 95 % within [90, 110] |
| warping | bed_temp | 60 → 65 | +5 | – | pass → 65 | – | L3: 65 °C within [50, 70] |

**5 of 10 fixed recipe changes violate the envelope as written.**
