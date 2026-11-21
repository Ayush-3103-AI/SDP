# Label audit (2026-11-21)

Single-cause rows of crops.csv. bogus_z = z_offset below the cut (CAXTON README: incorrectly labelled); gap = within CAXTON's post-change gap; clean = neither; margin = clean and no setpoint near a class edge (train rows only). Filters overlap, so columns don't add up.

| cause | rows | bogus_z | gap | clean | margin |
|---|---|---|---|---|---|
| flow_high | 6574 | 0 | 891 | 5683 | 4167 |
| flow_low | 3168 | 0 | 443 | 2725 | 1429 |
| none | 6968 | 0 | 1374 | 5594 | 4134 |
| nozzle_temp_high | 830 | 0 | 109 | 721 | 315 |
| nozzle_temp_low | 1358 | 0 | 149 | 1209 | 262 |
| speed_high | 4128 | 0 | 625 | 3503 | 1993 |
| speed_low | 4761 | 0 | 640 | 4121 | 2717 |
| z_offset_high | 9922 | 0 | 1302 | 8620 | 4655 |
| z_offset_low | 1522 | 1491 | 1324 | 7 | 0 |
| all | 39231 | 1491 | 6857 | 32183 | 19672 |
