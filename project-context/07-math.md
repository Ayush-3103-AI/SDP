<!-- HEAD
FILE:     07-math.md
PHASE:    2 — SPECIFY (delta 2026-10-27, ADR-0009)
UPDATED:  2026-10-27
STATUS:   accepted delta
SUMMARY:  Every formula the code depends on:
          §1 severity (early warnings: s = smoothed p); §2 correction size + G-code, manual causes;
          §3 the four gate layers (+ rounding note); §4 event-verdict truth table (early warnings never
          APPLY); §5 sensor checks; §6 outcome classification; §7 latency; §8 split-conformal;
          §9 evaluation metrics (floor, CIs, confident-event fidelity); §10 overshoot; §11 EigenCAM on
          the cause-model backbone; §12 FakePrinter (+ CAXTON process seeding); §13 early warning (EWMA +
          hysteresis); §14 proactive evaluation; §15 CAXTON label rule.
          Envelope defaults are config keys; the integrating team signs them off for their printer.
OPEN:     θ_on chosen in T-0063 on calibration prints; L3 from CAXTON good ranges (T-0024).
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

Validity: fixed camera pose and zoom. A heuristic, not a physical defect size; recalibrate a_ref if the camera moves.

**Early warnings (§13)** have no box: s = p̄_c, the smoothed probability that raised the warning. So a firmer
warning proposes a larger (still L2-clipped) change. [assumed]

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

Special causes: `none` → no proposal. **Manual causes** M = {z_offset_low, z_offset_high, misalignment} → no setpoint
proposal (live Z changes are firmware-specific babysteps, sub-integer, and belong to the operator); the card shows
MANUAL_ADVICE[c] (09 §Constants), e.g. "Nozzle likely too close to the bed: raise Z offset by ~0.05 mm"; forces
ESCALATE (§4 row 7).

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
- **Rounding (D2, documented 2026-10-27):** x'' is rounded half-up to an integer after the L2 clip. With a
  fractional tracked setpoint, |x''−x| can exceed step_v by up to 0.5 (210.5 + 5 → S216). Real setpoints are
  integers (they come from integer G-code), so this never happens in practice; the property test (T-0023) uses
  integer setpoints and the invariant below is stated for them.

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
| 7 | C ∩ M ≠ ∅ (manual causes, §2) | ESCALATE(`manual:<cause>`) → pause + card with MANUAL_ADVICE |
| 8 | no proposal survives L1–L3 | ESCALATE(`outside_envelope`) |
| 9 | mode = auto ∧ event is not an early warning ∧ L4 pass ∧ exactly 1 surviving proposal | APPLY(that proposal) |
| 10 | otherwise (auto or advisory) | PROPOSE(surviving proposals) |

ESCALATE = Printer.pause() + card. For an early warning (§13) row 7 does not pause (nothing is visibly wrong yet): ESCALATE = card only. A response timeout applies `cfg.hitl.timeout_action` (FR-019).

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

Offline (CAXTON replay) the images don't respond to our commands, so outcomes are not evidence of anything there;
the verifier is part of the hand-off and is measured by the integrating team on their rig.

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
- top-k = mean 1[y ∈ top-k(p̂)]. Floor = the training folds' majority cause, predicted for every image. Gap-to-oracle = 1 − top-1.
- **CIs:** bootstrap over test prints (resample prints with replacement, B = 1000, percentile 95 %), because images in a
  print are not independent.
- **Direction fidelity** (NFR-007) on **confident events**: samples whose true cause is actionable (has v*, d*) and where
  L4 would pass (|C| = 1, C ≠ {none}, p_top ≥ τ): mean 1[v̂ = v* ∧ sign(Δ̂) = −d*] using the top-1 proposal. Report the
  confident fraction = #confident / #actionable next to it (a model that is never confident must not pass by abstaining).
- **Steps-to-undo:** ⌈|m*| / step_{v*}⌉ where m* is the induced magnitude. Reported, not thresholded.
- Rig counterfactual validity = resolved rate over applied top-1 proposals (§6): the integrating team's measurement.

## §10 Overshoot metrics (per run, per variable)
- reversals_v = number of consecutive dispatched Δ pairs on v with opposite sign within 300 s.
- max_dev_v = max_t |x_v(t) − x^{nom}_v|, where nominal = the sliced setpoint at print start.

## §11 EigenCAM (one forward pass, no gradients)
A ∈ ℝ^{(h·w)×C} = activations of layer `cfg.attribution.layer` of the **cause model** (default `backbone.layer4`, 7×7×512 at
224 px) for the crop it classified.
- Ā = A − mean over rows.
- v₁ = first right-singular vector of Ā; H = reshape(Ā v₁, h, w).
- If Σ(A v₁) < 0 then H ← −H (orient v₁ by the uncentred activations: Ā is row-centred, so ΣĀv₁ ≡ 0); then H ← ReLU(H) / max(H) (if max = 0, H = 0).
- Bilinear upsample to the crop size (the cause model already ran on the crop, so no bbox crop step).
- Cost: an SVD of an (h·w)×C matrix, ≈ 5–20 ms; it runs after dispatch (D10).

## §12 FakePrinter thermal model (simulation only)
$$ \frac{dT}{dt} = \frac{T_{tgt} - T}{\tau_{th}} $$
τ_th = 8 s (nozzle), 60 s (bed); integrated with explicit Euler at the call rate. Flow and speed change instantly. Not a physical claim; it only exists so the loop runs in tests.

**CAXTON seeding (T-0062):** during a `caxton:` replay the source calls `FakePrinter.set_process(flow, speed, nozzle_target)`
with each row's logged values. That is the "disturbance": it changes the setpoints outside the gate, as the dataset's
printer did. Proposals then read real from→to values (e.g. flow 62 → 72 %). Operator-applied commands still go through
the gate and are recorded, but the next row's logged values overwrite them (the images can't react).

## §13 Early warning (proactive, per print; `xqi/proactive.py`)
Evaluated every `every_n` frames on the cause probabilities p(t) of the nozzle ROI.
$$ \bar p_c(t) = \beta\,\bar p_c(t^-) + (1-\beta)\,p_c(t),\qquad \bar p_c(t_{first}) = p_c(t_{first}) $$
State per cause c ≠ none: `armed_c` (start True), `run_c` (consecutive evaluations with p̄_c ≥ θ_on), `last_warn_c`.
- **Raise** a warning for c iff armed_c ∧ run_c ≥ m ∧ (t − last_warn_c ≥ T_w). Then armed_c ← False, last_warn_c ← t.
  If several causes qualify in one evaluation, raise only the one with the largest p̄_c.
- **Re-arm** c when p̄_c < θ_off (hysteresis, θ_off < θ_on).
- `none` never warns. A warning carries (c, p̄_c, t, the raw p(t)).
- Time is the frame ts (monotonic in a live run, CSV timestamp in a replay); a gap > `max_gap_s` resets p̄ and all runs.

| Symbol | Meaning | Default |
|---|---|---|
| β | EWMA weight on the past | 0.8 (`cfg.proactive.beta`) |
| θ_on / θ_off | raise / re-arm thresholds | 0.60 / 0.40 [θ_on chosen in T-0063] |
| m | consecutive evaluations above θ_on | 3 |
| T_w | per-cause cooldown | 60 s |
| every_n | frames between evaluations | 1 (CAXTON is ~2.5 fps) |

Validity: assumes the ROI shows the nozzle and fresh extrudate (CAXTON geometry). On another camera, re-check T-0067.

## §14 Proactive evaluation (`scripts/eval_proactive.py`, per held-out print)
Per image i of a print: D(i) = {(param, dir) : class ≠ good}, mapped to causes (§15 names). The print is cut into
**segments** where D is constant (CAXTON resamples every 150 images).
- **Onset** of cause c at segment start t_b when c ∈ D(segment) and c ∉ D(previous segment) (first segment: c ∈ D).
- A warning (c, t_w) is **true** iff c ∈ D at t_w, else **false**. False warnings in the first 6 s after a segment start
  are not counted (the README's transitional images).
- **Time-to-warning** for an onset = t_w − t_b of the first true warning of c inside that segment; **missed** if none
  within 30 s or before the segment ends. Report the median over warned onsets and **recall@30 s** = warned / onsets.
- **False-warning rate** = #false / (total printing hours of the evaluated prints).
- θ_on is picked from {0.5, 0.6, 0.7, 0.8} on **calibration prints only**: the smallest θ_on with ≤ 1 false warning per
  hour, ties → lower median time-to-warning. Then frozen and applied once to the test prints.
- Floor: the same rule with β = 0 (no smoothing).
- Inputs come from saved per-image probabilities (T-0013 `preds_fold*.npz` with ts and print ids), so it is CPU-only.

## §15 CAXTON label rule (`scripts/adapt_caxton.py`)
Class columns k ∈ {flow_rate, feed_rate, z_offset, hotend}, values 0 = low, 1 = good, 2 = high.
Cause names: flow_rate → flow, feed_rate → speed, z_offset → z_offset, hotend → nozzle_temp; class 0 → `_low`, 2 → `_high`.
- All four good → `none`.
- Exactly one not good → that cause (e.g. feed_rate_class = 2 → `speed_high`).
- Two or more not good → `multi` (kept in images.csv with all four classes, excluded from cause training/eval, used by
  §14 and the replay).
- Excluded and counted: print_id ≥ 183; z_offset < 0.08 mm (README: incorrectly labelled; `--keep-z-suspect` keeps them).
Direction note: `flow_low` means the flow was too low, so the correction raises it (CAUSE_ACTION d = −1, §2).
Z-offset direction: z_offset_low = nozzle too close to the bed.
