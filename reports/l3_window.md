# L3 process window from CAXTON good-class ranges (T-0024)

Input: data/images.csv

## Derived window

| var | p1 | p99 | good images | L1 |
|---|---|---|---|---|
| flow | 86.00 | 130.00 | 27890 | [50, 150] |
| speed | 86.00 | 130.00 | 28920 | [50, 150] |
| nozzle_temp | 182.00 | 235.00 | 45629 | [170, 240] |

bed_temp: not derived (CAXTON bed is 60/65 °C only); the config value stays.

## Current config window

material: PLA
- nozzle_temp: [195, 225]
- bed_temp: [50, 70]
- flow: [90, 110]
- speed: [80, 110]

## Proposed config edit

config/default.yaml, envelope.L3.window (rounded outward to integers, clipped to L1):

```yaml
nozzle_temp: [182, 235]
bed_temp: [50, 70]
flow: [86, 130]
speed: [86, 130]
```

Changed in a separate commit after the user reads this report; the config loader checks L3 ⊆ L1.
