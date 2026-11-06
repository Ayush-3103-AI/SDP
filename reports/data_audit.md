K1′: FAIL (only 0 actionable causes have ≥ 200 single-cause images in ≥ 5 prints; need 4)

# CAXTON data audit (T-0006)

Kept images: 72323 in 169 prints (169 rows in trials.csv). K1′ threshold per cause: ≥ 200 single-cause images in ≥ 5 prints.

## Images and prints per cause

| cause | single images | single prints | in multi images | multi prints |
|---|---|---|---|---|
| flow_low | 0 | 0 | 20500 | 145 |
| flow_high | 0 | 0 | 23933 | 153 |
| speed_low | 0 | 0 | 19702 | 145 |
| speed_high | 0 | 0 | 23701 | 149 |
| nozzle_temp_low | 0 | 0 | 17901 | 151 |
| nozzle_temp_high | 0 | 0 | 8793 | 136 |
| z_offset_low | 0 | 0 | 0 | 0 |
| z_offset_high | 15687 | 102 | 56636 | 167 |

none: 0 images in 0 prints · multi: 56636 images in 167 prints

## Single-deviation share

Kept subset: 15687 / 72323 = 21.7% (the subset is stratified, so this is inflated).
All labelled images before the subset: 21087 / 598937 = 3.5%.

## Exclusions

Images in the CSV: 1072500

| reason | images |
|---|---|
| print_id>=183 | 0 |
| z_offset<0.08 | 473563 |

## Images per print

min 13 · median 500 · max 500 (kept images per print)

## Segments

6743 segments of constant deviation set (07 §14) in the kept subset.

## Missing crops

17 of 72323 kept images have no crop.

## Proposed frozen taxonomy (T-0007)

Keep: none, z_offset_high

- flow_low: drop at T-0007 (0 single-cause images in 0 prints)
- flow_high: drop at T-0007 (0 single-cause images in 0 prints)
- speed_low: drop at T-0007 (0 single-cause images in 0 prints)
- speed_high: drop at T-0007 (0 single-cause images in 0 prints)
- nozzle_temp_low: drop at T-0007 (0 single-cause images in 0 prints)
- nozzle_temp_high: drop at T-0007 (0 single-cause images in 0 prints)
- z_offset_low: drop at T-0007 (0 single-cause images in 0 prints)

The user and Dr. Meti confirm this before causes.yaml is edited (T-0007).
