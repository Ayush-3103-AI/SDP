# Deck-recipe audit (T-0023)

Each deck recipe is pushed from the printer nominal through the safety gate (L2 -> L1 -> L3). The table shows the raw recipe Δ, the raw recipe target against the L3 process window, and the layer that clipped or blocked the change.

- variables audited: 10
- raw targets outside the L3 window: 3
- clipped by L2: 5
- blocked: 0

| Recipe | Variable | Δ | Raw target | L3 | Layer | Detail |
|---|---|---|---|---|---|---|
| over_extrusion | nozzle_temp | -20 | 190 | out | L2 (clipped) | clipped -20 → -5 °C |
| over_extrusion | speed | -5 | 95 | in | - | within envelope |
| over_extrusion | flow | -20 | 80 | out | L2 (clipped) | clipped -20 → -10 pp |
| under_extrusion | nozzle_temp | -5 | 205 | in | - | within envelope |
| under_extrusion | speed | -20 | 80 | in | L2 (clipped) | clipped -20 → -10 pp |
| under_extrusion | flow | +10 | 110 | in | - | within envelope |
| stringing | nozzle_temp | -20 | 190 | out | L2 (clipped) | clipped -20 → -5 °C |
| stringing | speed | -20 | 80 | in | L2 (clipped) | clipped -20 → -10 pp |
| stringing | flow | -5 | 95 | in | - | within envelope |
| warping | bed_temp | +5 | 65 | in | - | within envelope |

Conclusion: the fixed deck recipes request edits larger than the per-action step and some raw recipe targets sit outside the L3 process window, so the recipes are not applied raw: the gate clips every oversized step and rejects any target that would leave the envelope.
