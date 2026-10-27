<!-- HEAD
FILE:     08-pseudocode.md
PHASE:    2 — SPECIFY (delta 2026-10-27, ADR-0009)
UPDATED:  2026-10-27
STATUS:   accepted delta
SUMMARY:  Eight algorithms with failure notes:
          P1 main loop tick (+ proactive evaluation every n frames; detector optional); P2 confirmation
          tracker; P3 handle_event (critical-first, then explain → gate → verdict; early warnings never
          APPLY); P4 gate; P5 leave-parts-out training + conformal calibration on CAXTON ROI crops;
          P6 outcome verifier; P7 early warning (EWMA + hysteresis); P8 CAXTON adapter + crops.
          Failure rules: printer errors never crash the loop; missing state → ESCALATE;
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
    dets = detector(frame) if detector else []          # list[Detection]; detector is optional (FR-003)
    store.write_detections(frame, dets)                 # batched every N frames
    for cd in tracker.update(frame, dets):              # ConfirmedDefect(s)
        handle_event(cd, frame)                         # P3, synchronous
    if proactive and frame.frame_id % every_n == 0:     # FR-029
        roi = crop_roi(frame.image, cfg.proactive.roi)  # null → whole frame
        est = explainer.estimate(roi)                   # cause model only
        for w in early_warning.update(frame.ts, est.probs):   # P7, 0 or 1 warning
            handle_event(warning_event(w, frame, roi), frame) # P3 with cd.cls = "early_warning"
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
if mode in (baseline, gated-recipe) and cd.cls == "early_warning": return   # recipes are per defect class
if mode == baseline: send recipe raw; return
if mode == gated-recipe: proposals = recipe_to_proposals(cd.cls, state); gate each; send survivors; return
probs  = early-warning raw probs if cd.cls == "early_warning" else cause_model.predict(crop(frame, cd.xyxy), cd.cls)  # t_cause
C      = conformal.predict_set(probs)
flags  = sensors.check(state_history)
props  = [make_proposal(c, cd.severity, state) for c in C if actionable(c)]
gated  = [gate(p, state, C, probs, flags, cfg, now()) for p in props]
verdict = event_verdict(mode, cd, C, gated, state)                  # 07 §4, t_gate; early warning → never APPLY (row 9)
store.write_explanation(...); store.write_proposals(gated); store.write_verdict(verdict)
match verdict:
    APPLY    -> dispatch(gated.final_gcode); tracker_state.update; verifier.watch(action)
    PROPOSE  -> store.mark_pending(event_id, deadline=now()+timeout_s)
    ESCALATE -> (printer.pause() unless early warning); store.mark_pending(...)
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
Data: data/crops.csv (P8): 224 px nozzle-ROI crops, cause ∈ CAUSES (07 §15; `multi` rows excluded), one group = one print.
```
for fold k in splits.folds:                          # leave-parts-out, 5 folds (logo.json)
    train_prints, calib_prints = fold.train_trials, fold.calib_trials      # calib = 20 % of training prints
    model = ResNet18(imagenet) + Linear(512 [+|DEFECTS| if use_defect] -> |CAUSES|)   # use_defect=false for CAXTON
    train with AdamW lr 3e-4, wd 1e-4, batch 32, ≤ 15 epochs, class-weighted CE (weights from train prints only),
          aug: color jitter 0.2, random resized crop (0.8–1.0), hflip; no vertical flip (gravity-dependent extrudate)
    per epoch: sample ≤ cfg max_per_print images per print (default 300) so long prints don't dominate
    early stop on calib loss (patience 3); save models/cause/fold{k}.pt
    probs_cal = predict(calib); qhat[k] = conformal.calibrate(probs_cal, y_cal, alpha)
    probs_test = predict(test prints) → metrics (07 §9) per fold
    also predict EVERY image of the calib and test prints, including `multi` rows, in ts order
          → preds_fold{k}.npz (for 07 §14 proactive eval and the replay)
report mean ± std over folds + bootstrap CI over prints, plus floor and gap-to-oracle
final runtime model: retrain on all training prints with a calib split → models/cause/final.pt + qhat.json
```
Failure notes:
- A cause with < 200 training crops or < 5 training prints in a fold → drop it from the taxonomy at T-0007 (decided
  once on the audit, recorded in the report). Never silently per fold.
- VRAM 4 GB → batch 32 at 224 px fits ResNet18 (~1.5 GB). On OOM, halve the batch.
- Seeds fixed (python, numpy, torch); cudnn deterministic off for speed, with the seed recorded.
- Normalisation = ImageNet mean/std (the backbone's). The CAXTON dataset mean/std is recorded but not used.

## P6 — Outcome verifier (`xqi/verify.py`)
```
watch(action): pending.append(Watch(action, k, t_a, before=window_rate(k, t_a-W, t_a)))
tick(ts): for w in pending: if ts >= w.t_a + S + W: classify per 07 §6 → store.write_outcome; remove
on run end: remaining → "unknown"
```
Needs a per-class ring buffer of (ts, present) covering the last S + 2W seconds. Memory ≈ 25 fps × 270 s × 7 classes of booleans: negligible.

## P7 — Early warning (`xqi/proactive.py: EarlyWarning.update`, pure; 07 §13)
```
state: pbar=None, last_ts=None, run[c]=0, armed[c]=True, last_warn[c]=-inf   for c in CAUSES \ {none}
def update(ts, probs) -> list[Warning]:
    if last_ts is not None and ts - last_ts > max_gap_s: reset()
    last_ts = ts
    pbar = probs if pbar is None else beta*pbar + (1-beta)*probs
    ready = []
    for c in causes:
        run[c] = run[c] + 1 if pbar[c] >= theta_on else 0
        if pbar[c] < theta_off: armed[c] = True
        if armed[c] and run[c] >= m and ts - last_warn[c] >= T_w: ready.append(c)
    if not ready: return []
    c = argmax over ready of pbar[c]
    armed[c] = False; last_warn[c] = ts
    return [Warning(cause=c, p=pbar[c], ts=ts, probs=probs)]
```
Edge cases: probs must cover every cause (KeyError otherwise); θ_off ≥ θ_on → config validation error.

## P8 — CAXTON adapter + crops (`scripts/adapt_caxton.py`, `scripts/build_crops.py`)
```
adapt_caxton.py --csv <caxton_dataset_filtered.csv> --root <dir holding caxton_dataset/> --out data/
                [--per-print N=500] [--seed 0] [--keep-z-suspect] [--list-needed needed.txt]
    rows = read csv; check required columns (09 §Data) → missing → exit 2 naming them
    drop print_id >= 183 and z_offset < 0.08 (unless --keep-z-suspect); count both
    cause = label(row) per 07 §15
    subset: per print, keep every image of `multi`/`none`/single rows up to N, stratified by cause
            (take all of a rare cause first, then fill with the rest in ts order)
    write data/trials.csv (one row per print) and data/images.csv (one row per kept image)
    --list-needed: write the kept img_path values only (lets the teammate fetch just those images if the
                   archive is per print); never touches the network itself
build_crops.py --images data/images.csv --root <dir> --out data/crops [--size 320] [--px 224] [--workers 4]
    for each row: read image; box = 320×320 centred on (nozzle_x, nozzle_y), shifted to stay inside the frame;
                  resize to 224; write data/crops/<print>/<image>.jpg (quality 95); skip if it exists (resumable)
    write data/crops.csv; missing or unreadable images are counted, listed in data/crops_missing.txt, not fatal
```
Cost: ~100 k JPEG decodes + writes, ≈ 20–40 min on a laptop CPU with 4 workers; output ≈ 1.5–2 GB.
