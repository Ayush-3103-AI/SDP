<!-- HEAD
FILE:     08-pseudocode.md
PHASE:    2 — SPECIFY
UPDATED:  2026-10-03
STATUS:   draft (awaiting gate)
SUMMARY:  Six algorithms with failure notes:
          P1 the main loop tick (single thread; the action path is synchronous; heatmap and
          outcome work go on a worker queue); P2 confirmation tracker; P3 handle_event
          (critical-first, then explain → gate → verdict); P4 gate; P5 LOGO train + conformal
          calibrate; P6 outcome verifier.
          Failure rules: OctoPrint errors never crash the loop; missing state → ESCALATE;
          camera loss → pause after cfg.camera.max_gap_s.
OPEN:     none
-->

# Pseudocode

## P1 — Main loop (`xqi/orchestrator.py: Orchestrator.run`)
```
init: cfg, store(run_id), printer, source, detector, tracker, explainer, worker_queue
store.write_run(mode, cfg_hash, git_sha)
last_frame_ts = now()
for frame in source:                                   # blocking iterator
    if now() - last_frame_ts > cfg.camera.max_gap_s:   # camera stalled
        printer.pause(); store.alert("camera_gap")
    last_frame_ts = frame.ts
    dets = detector(frame)                              # list[Detection]
    store.write_detections(frame, dets)                 # batched every N frames
    for cd in tracker.update(frame, dets):              # ConfirmedDefect(s)
        handle_event(cd, frame)                         # P3, synchronous
    process_operator_decisions()                        # read new operator_decisions rows; re-gate Modify
    check_timeouts()                                    # FR-019
    verifier.tick(frame.ts)                             # P6, cheap counters
on KeyboardInterrupt / end: drain worker_queue (≤ 5 s); store.close()
```
Complexity: O(#detections) per frame. Failure notes:
- `detector` raises → log it, skip the frame, and continue. After 10 consecutive failures, pause the printer and exit with a non-zero code.
- The store is written in a single thread; the UI only writes `operator_decisions` (09 §Store), so writers never conflict on the same table.

## P2 — Confirmation tracker (`xqi/detect.py: ConfirmationTracker.update`)
```
state per class k: streak[k]=0, first_ts[k]=None, armed[k]=True, absent[k]=0, recent[k]=deque(maxlen=cfg.severity.window)
present = {d.cls: max-conf detection of that class in this frame}
for k in DEFECTS:
    recent[k].append(k in present)
    if k in present:
        absent[k] = 0
        streak[k] += 1; first_ts[k] = first_ts[k] or frame.ts
        if armed[k] and streak[k] >= hits[k]:
            armed[k] = False
            emit ConfirmedDefect(k, det=present[k], t0=first_ts[k], h=sum(recent[k]))
    else:
        streak[k]=0; first_ts[k]=None; absent[k]+=1
        if absent[k] >= cfg.confirm.rearm_frames: armed[k] = True
```
Edge cases: several boxes of one class in a frame → use the highest-conf box. hits[k] < 1 → config validation error.

## P3 — handle_event (`xqi/orchestrator.py`)
```
t_conf = now(); store.write_defect(cd)
if cd.cls in cfg.critical:                               # FR-005: act first
    printer.estop() if cfg.critical[cd.cls]=="estop" else printer.pause()
    store.write_action(...); worker_queue.put(explain_only(cd, frame)); return
state = printer.get_state()                              # may raise → state=None
if mode == baseline: send recipe raw; return
if mode == gated-recipe: proposals = recipe_to_proposals(cd.cls, state); gate each; send survivors; return
probs  = cause_model.predict(crop(frame, cd.xyxy), cd.cls)          # t_cause
C      = conformal.predict_set(probs)
flags  = sensors.check(state_history)
props  = [make_proposal(c, cd.severity, state) for c in C if actionable(c)]
gated  = [gate(p, state, C, probs, flags, cfg, now()) for p in props]
verdict = event_verdict(mode, cd, C, gated, state)                  # 07 §4, t_gate
store.write_explanation(...); store.write_proposals(gated); store.write_verdict(verdict)
match verdict:
    APPLY    -> dispatch(gated.final_gcode); tracker_state.update; verifier.watch(action)
    PROPOSE  -> store.mark_pending(event_id, deadline=now()+timeout_s)
    ESCALATE -> printer.pause(); store.mark_pending(...)
    NOOP     -> pass
worker_queue.put(heatmap_job(cd, frame))                             # FR-009, after dispatch
```
Failure notes:
- `get_state` failure → state=None → ESCALATE (row 4). If the pause also fails → store an alert row; the UI shows a red banner.
- Dispatch failure (non-2xx or timeout > cfg.printer.timeout_s) → retry once. If it still fails, write an action with `ok=false` and do not update the tracked setpoints.

## P4 — gate (`xqi/gate.py`, pure; see 07 §3)
```
def gate(p, state, now, cfg) -> GateDecision:
    if state is None or any NaN in needed fields: return escalate("state_unavailable")
    v = p.var; x = state.setpoint(v); last = state.last_change.get(v, -inf)
    L2: if now-last < cool[v]: reject("cooldown {now-last:.0f}s < {cool[v]}s")
        d = sign(p.delta)*min(|p.delta|, step[v]); clipped = (d != p.delta); x2 = x + d
    L1: if not lo1[v] <= x2 <= hi1[v]: reject("physical {x2} outside [{lo1},{hi1}]")
    L3: if not (lo3<=x2<=hi3 or dist(x2,W3) < dist(x,W3)): reject("outside characterised window")
    return pass(x2, d, gcode(v, x2), reasons)
def event_verdict(...)   # 07 §4 table, rows in order; L4 evaluated here
```
Numerical notes: compare after rounding x2 to integers (G-code is integer). If rounding pushes x2 out of L1, reject. No floats in G-code strings.

## P5 — Cause model training + conformal calibration (`scripts/train_cause.py`, `scripts/eval_cause.py`)
```
for fold g in splits.folds:                          # LOGO
    train_trials, calib_trials = split_by_trial(trials not in g, 0.8, seed=fold)
    model = ResNet18(imagenet) + Linear(512+|DEFECTS| -> |CAUSES|)
    train with AdamW lr 3e-4, wd 1e-4, batch 32, 15 epochs, class-weighted CE,
          aug: color jitter 0.2, random resized crop (0.8–1.0), hflip; no vertical flip (gravity-dependent defects)
    early stop on calib loss (patience 3); save models/cause/fold{g}.pt
    probs_cal = predict(calib); qhat[g] = conformal.calibrate(probs_cal, y_cal, alpha)
    probs_test = predict(geometry g) → metrics (07 §9) per fold
report mean ± std over folds, plus floor and gap-to-oracle
final runtime model: retrain on all geometries with calib split → models/cause/final.pt + qhat.json
```
Failure notes:
- A class with < 10 training crops in a fold → merge it into `other`, or drop it and record that in the report. Never silently.
- VRAM 4 GB → batch 32 at 224 px fits ResNet18 (~1.5 GB). On OOM, halve the batch.
- Seeds fixed (python, numpy, torch); cudnn deterministic off for speed, with the seed recorded.

## P6 — Outcome verifier (`xqi/verify.py`)
```
watch(action): pending.append(Watch(action, k, t_a, before=window_rate(k, t_a-W, t_a)))
tick(ts): for w in pending: if ts >= w.t_a + S + W: classify per 07 §6 → store.write_outcome; remove
on run end: remaining → "unknown"
```
Needs a per-class ring buffer of (ts, present) covering the last S + 2W seconds. Memory ≈ 25 fps × 270 s × 7 classes of booleans: negligible.
