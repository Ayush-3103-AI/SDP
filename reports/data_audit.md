K1′: PASS

# CAXTON data audit (T-0006)

Kept images: 79515 in 181 prints (181 rows in trials.csv). K1′ threshold per cause: ≥ 200 single-cause images in ≥ 5 prints.

## Images and prints per cause

| cause | single images | single prints | in multi images | multi prints |
|---|---|---|---|---|
| flow_low | 3168 | 45 | 14499 | 153 |
| flow_high | 6574 | 64 | 17736 | 155 |
| speed_low | 4761 | 59 | 14901 | 156 |
| speed_high | 4128 | 55 | 16794 | 155 |
| nozzle_temp_low | 1358 | 22 | 12741 | 157 |
| nozzle_temp_high | 830 | 18 | 6085 | 139 |
| z_offset_low | 1522 | 84 | 1861 | 145 |
| z_offset_high | 9922 | 102 | 33090 | 167 |

none: 6968 images in 95 prints · multi: 40284 images in 170 prints

## Single-deviation share

Kept subset: 32263 / 79515 = 40.6% (the subset is stratified, so this is inflated).
All labelled images before the subset: 53592 / 816952 = 6.6%.

## Exclusions

Images in the CSV: 1072500

| reason | images |
|---|---|
| print_id>=183 | 0 |
| z_offset_ambiguous | 255548 |

## Images per print

min 13 · median 500 · max 500 (kept images per print)

## Segments

6930 segments of constant deviation set (07 §14) in the kept subset.

## Missing crops

43168 of 79515 kept images have no crop.

## Proposed frozen taxonomy (T-0007)

Keep: none, flow_low, flow_high, speed_low, speed_high, nozzle_temp_low, nozzle_temp_high, z_offset_low, z_offset_high

Drop: none

The user and Dr. Meti confirm this before causes.yaml is edited (T-0007).
