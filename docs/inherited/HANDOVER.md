# REU inheritance package: hand-over record (T-0002, #2)

Status of the six items T-0002 asks for. The team lead updates each row as items arrive.

| # | Item | Status | Path / source | Notes |
|---|---|---|---|---|
| 1 | YOLO11-S `best.pt` + `data.yaml` + training args | not in this drop | — | |
| 2 | 6,454-image YOLO dataset + REU train/val/test split files | **partial** | Drive "Camera Roll" folder (owner kirtisomannavar379), received 2026-10-26 | 5,490 unlabelled 1280×720 webcam stills of one print, 2025-04-29. No labels, no splits. See `camera_roll_report.html`. |
| 3 | Induction log + image↔trial mapping | not in this drop | — | |
| 4 | Loop code (confirmation counts, OctoPrint client, recipes) | not in this drop | — | |
| 5 | OctoPrint URL + key, hotend type, bed max temp | not in this drop | — | Photos show a dual-hotend toolhead; the deck says Ender 5 Plus. Confirm which rig. |
| 6 | Induction protocol document | not in this drop | — | |

**Is the REU split image-level or trial-level?** Unknown. No split files were received.

## Open questions for the REU team
1. Is the camera roll everything, or is the labelled YOLO export somewhere else?
2. Was any fault induced during the 2025-04-29 print, and at what times?
3. Were these frames the source of the REU training images? If so, 41 % of consecutive frames are near-copies, so leakage risk A7 is high.
