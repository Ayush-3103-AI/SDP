<!-- HEAD
FILE:     07-math.md
PHASE:    2 — SPECIFY
UPDATED:  2026-10-03
STATUS:   draft (awaiting gate)
SUMMARY:  Every formula the code depends on:
          §1 severity; §2 correction size + G-code; §3 the four gate layers (L3 lets a
          move back *toward* the window through, so induced trials can be corrected);
          §4 event-verdict truth table; §5 sensor checks; §6 outcome classification;
          §7 latency definitions; §8 split-conformal; §9 evaluation metrics; §10 overshoot;
          §11 EigenCAM; §12 FakePrinter thermal model.
          All defaults are config keys and are [assumed] until T-0025 sign-off.
OPEN:     L1/L3 numbers (T-0024, T-0025); cause list (T-0007).
-->

# Math

Process variables `v ∈ V = {nozzle_temp, bed_temp, flow, speed}`. Units: temperatures °C; flow and speed in % of the sliced value (M221/M220 `S` values). Δ for flow/speed is in percentage points (pp).

## §1 Severity
$$ s = \mathrm{clip}\Big(\tfrac12\min(1, a/a_{ref}) + \tfrac12\min(1, h/h_{ref}),\ 0,\ 1\Big) $$
| Symbol | Meaning | Unit | Default / range |
|---|---|---|---|
| a | bbox area / frame area of the confirming detection | – | (0, 1] |
| a_ref | area treated as "large" | – | 0.02 (`cfg.severity.a_ref`) |
| h | frames in the last `cfg.severity.window` frames where the class was detected | frames | 0..30 |
| h_ref | persistence treated as "full" | frames | 15 |

Validity: fixed camera pose and zoom (Pi HQ, 16 mm). A heuristic, not a physical defect size; recalibrate a_ref if the camera moves.

## §2 Correction size, G-code, counterfactual text
Each actionable cause c maps to (v_c, d_c) with d_c = −1 for `*_low` and +1 for `*_high`:
$$ \Delta_v = -d_c\,\big(d^{min}_v + s\,(d^{max}_v - d^{min}_v)\big),\qquad x'_v = x_v + \Delta_v $$
x_v is the current tracked setpoint. Defaults: d^min / d^max = nozzle 2/5 °C, bed 2/5 °C, flow 5/10 pp, speed 5/10 pp. **Constraint:** d^max_v ≤ step_v (§3).

G-code (rounded to integers):

| v | Command |
|---|---|
| nozzle_temp | `M104 S{x'}` (no wait) |
| bed_temp | `M140 S{x'}` |
| flow | `M221 S{x'}` |
| speed | `M220 S{x'}` |

Counterfactual sentence:
`"Most likely cause: {label(c)} (p={p:.2f}). Smallest in-envelope change that undoes it: {v} {x_v}→{x'_v} {unit} ({Δ:+}). Expected to clear within {S+W} s if the cause is right."`

Special causes: `none` → no proposal. `misalignment` → no setpoint proposal; forces ESCALATE (§4).

## §3 Safety gate (applied per proposal; order L2 → L1 → L3 → L4)
| Symbol | Meaning | Unit | Default |
|---|---|---|---|
| lo1_v, hi1_v | physical limits | °C / % | nozzle [170, 240] (PTFE-lined hotend, A5); bed [0, 100]; flow [50, 150]; speed [50, 150] |
| step_v | max \|Δ\| per action | °C / pp | nozzle 5, bed 5, flow 10, speed 10 |
| cool_v | min time between changes to v | s | nozzle 45, bed 90, flow 20, speed 20 |
| lo3_v, hi3_v | characterised window (PLA) | °C / % | nozzle [195, 225], bed [50, 70], flow [90, 110], speed [80, 110] |
| τ | auto-apply probability floor | – | 0.60 |

The layers:
- **L2 (rate):** if `now − last_change_v < cool_v` → reject (`cooldown`). Otherwise
  $$\Delta'_v = \mathrm{sign}(\Delta_v)\min(|\Delta_v|, step_v),\quad x''_v = x_v + \Delta'_v$$
  If clipped, record `clipped`.
- **L1 (physical):** pass iff lo1_v ≤ x''_v ≤ hi1_v, else reject.
- **L3 (window):** pass iff lo3_v ≤ x''_v ≤ hi3_v, **or** dist(x''_v, W3) < dist(x_v, W3), where dist(y, [lo, hi]) = max(lo − y, 0, y − hi). Moving toward the window is allowed even from outside it. This is needed because induced trials start outside it.
- **L4 (confidence), evaluated per event:** pass iff |C| = 1 ∧ C ≠ {none} ∧ p_top ≥ τ ∧ no sensor flags.
- **Fail-closed:** any required state field missing or NaN → the event verdict is ESCALATE.

**Safety invariant (property-tested, NFR-004):** every dispatched setpoint change satisfies
- |Δ'| ≤ step_v;
- lo1_v ≤ x'' ≤ hi1_v;
- (x'' ∈ W3 ∨ dist decreased);
- no two dispatched changes to the same v closer than cool_v.

## §4 Event verdict truth table (first matching row wins)
| # | Condition | Verdict |
|---|---|---|
| 1 | class ∈ cfg.critical | CRITICAL → configured estop/pause, no gate (FR-005) |
| 2 | mode = baseline | APPLY_RAW: deck recipe, absolute setpoints, no gate |
| 3 | mode = gated-recipe | the recipe split into per-variable proposals and gated by L1–L3; send the survivors (APPLY); if none survive → NOOP(`recipe_blocked`) |
| 4 | required state missing / NaN | ESCALATE(`state_unavailable`) |
| 5 | C = ∅ | ESCALATE(`no_confident_cause`) |
| 6 | C = {none} | NOOP(`no_actionable_cause`) |
| 7 | misalignment ∈ C | ESCALATE(`mechanical`) → pause + card |
| 8 | no proposal survives L1–L3 | ESCALATE(`outside_envelope`) |
| 9 | mode = auto ∧ L4 pass ∧ exactly 1 surviving proposal | APPLY(that proposal) |
| 10 | otherwise (auto or advisory) | PROPOSE(surviving proposals) |

ESCALATE = OctoPrint pause + card. A response timeout applies `cfg.hitl.timeout_action` (FR-019).

## §5 Sensor checks (deterministic, telemetry-only)
- `heater_deviation:{nozzle|bed}`: |T_act − T_tgt| > δ_T for > t_δ continuously (δ_T = 5 °C, t_δ = 10 s).
- `settling:{v}`: the target for v changed less than t_settle ago (45 s nozzle, 90 s bed).
- `printer_not_printing`: OctoPrint state ≠ "Printing".

Any flag blocks APPLY (L4). Flags are shown on the card.

## §6 Outcome classification (after an applied action at t_a, defect class k)
$$ r_{before} = \frac{\#\text{frames with }k\text{ in }[t_a - W, t_a]}{\#\text{frames}},\quad r_{after} = \frac{\#\text{frames with }k\text{ in }[t_a + S, t_a + S + W]}{\#\text{frames}} $$
- **resolved** if r_after ≤ 0.5·r_before ∧ r_after ≤ 0.10
- **worsened** if r_after ≥ 1.5·r_before ∧ r_after ≥ 0.20
- **unknown** if either window has < 10 frames or the print ended
- **persisted** otherwise

Defaults: W = 120 s, S = 30 s (thermal settling).

## §7 Latency definitions (monotonic clock, seconds)
| Timestamp | Meaning |
|---|---|
| t0 | capture ts of the first frame in the confirming streak |
| t_conf | confirmation emitted |
| t_cause | cause probabilities ready |
| t_gate | event verdict ready |
| t_disp | OctoPrint HTTP call returned 2xx |

- end-to-end = t_disp − t0 (NFR-002)
- added = t_gate − t_conf (NFR-001)
- card latency = UI first-render ts − t_conf (NFR-003; wall clock, same host)

## §8 Split-conformal (LAC)
Calibration pairs (x_i, y_i), i = 1..n; score s_i = 1 − p̂_{y_i}(x_i).
$$ \hat q = \mathrm{Quantile}\big(\{s_i\};\ \lceil (n+1)(1-\alpha)\rceil / n\big)\ \text{(method="higher")};\quad \hat q = 1 \text{ if the level} > 1 $$
$$ C(x) = \{y : \hat p_y(x) \ge 1 - \hat q\} $$
- Guarantee: P(y ∈ C) ≥ 1 − α only under exchangeability. LOGO is a shift, so report empirical values.
- Empirical coverage = mean 1[y_i ∈ C(x_i)]; mean set size = mean |C(x_i)|.
- Edge cases: n < 20 → raise (too few to calibrate). Ties are inclusive.

## §9 Evaluation metrics
- top-k = mean 1[y ∈ top-k(p̂)]. Floor = majority cause per defect class (training folds). Gap-to-oracle = 1 − top-1.
- **Direction fidelity** (NFR-007), on samples whose true cause is actionable (has v*, d*): mean 1[v̂ = v* ∧ sign(Δ̂) = −d*], using the top-1 proposal.
- **Steps-to-undo:** ⌈|m*| / step_{v*}⌉ where m* is the induced magnitude. Reported, not thresholded.
- Rig counterfactual validity = resolved rate over applied top-1 proposals (§6).

## §10 Overshoot metrics (per run, per variable)
- reversals_v = number of consecutive dispatched Δ pairs on v with opposite sign within 300 s.
- max_dev_v = max_t |x_v(t) − x^{nom}_v|, where nominal = the sliced setpoint at print start.

## §11 EigenCAM (one forward pass, no gradients)
A ∈ ℝ^{(h·w)×C} = activations of layer `cfg.attribution.layer` for the frame.
- Ā = A − mean over rows.
- v₁ = first right-singular vector of Ā; H = reshape(Ā v₁, h, w).
- If ΣH < 0 then H ← −H; then H ← ReLU(H) / max(H) (if max = 0, H = 0).
- Bilinear upsample to the frame size, then crop to the bbox.
- Cost: an SVD of an (h·w)×C matrix, ≈ 5–20 ms; it runs after dispatch (D10).

## §12 FakePrinter thermal model (simulation only)
$$ \frac{dT}{dt} = \frac{T_{tgt} - T}{\tau_{th}} $$
τ_th = 8 s (nozzle), 60 s (bed); integrated with explicit Euler at the call rate. Flow and speed change instantly. Not a physical claim; it only exists so the loop runs in tests.
