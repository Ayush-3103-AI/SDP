# LOGBOOK (append-only; newest at the bottom)

## 2026-10-03 — Phases 0–4 (compressed) — Charter, spec, tickets
BUILT:     00-charter, 01-understanding, 02-stakeholders, 03-landscape, 04-patterns, ADR-0001..0007,
           06-requirements (25 MUST/SHOULD FRs + 3 COULD, 11 NFRs), 07-math, 08-pseudocode,
           09-interfaces, 10-done, 52 tickets + BOARD.md, root CLAUDE.md
RESULT:    Gate pending
SURPRISE:  - The model files in the repo root (AM_1/AM_2 .pt) are older YOLOv8n iterations: one has junk
             classes (defect/object/p/s); the other has a duplicated typo class "under exstrosion". They are
             NOT the deck's YOLO11-S. The 2025/26 papers' metrics don't match the shipped files either.
           - Defects were induced by commanding setpoints, so any model that sees setpoints or telemetry
             would score ~100 % on the cause — this became ADR-0002's one-way rule.
           - The deck's fixed recipes (e.g. M104 S190 from 210 = −20 °C) will violate our own L2 step
             limit; the recipe audit (T-0023) turns that into a result.
BROKE:     Nothing (no code yet)
NEXT:      Gate approval → T-0001 (Claude Code), T-0002 (human, day 1)

## 2026-10-03 — T-0001 Scaffold the repo
SKIP:      SEQUENCE step 1 (T-0002) is HUMAN-owned; skipped per rule 2. It still has to start on day 1.
BUILT:     pyproject.toml (uv + hatchling, deps per ticket, dev group pytest/ruff, markers gpu/hw/slow,
           addopts excludes them; torch/torchvision from the explicit pytorch-cu126 index), .python-version (3.11),
           uv.lock (torch 2.14.1+cu126), xqi/__init__.py (__version__ 0.1.0), tests/test_smoke.py.
           .gitignore += data/* (not data/splits/), runs/, models/* with the models/cause/{final.pt,qhat.json,
           preds_*.npz} whitelist, graphify-out/, .graphify/; graphify-out untracked.
RESULT:    `uv run pytest` → 1 passed; `uv run ruff check .` clean; check_sequence.py OK; check-ignore verified.
SURPRISE:  - T-0001 was revised mid-session (commit a8e9ad8: cu126 source + models/cause whitelist). The first
             pass built the old spec; /code-review caught both gaps and they were fixed before commit.
           - Default ruff flags `re.M` in scripts/check_sequence.py (FURB167); fixed to re.MULTILINE.
           - C: has < 1 GB free; the 2.4 GB CUDA torch wheel can't unpack into uv's default cache there.
             Synced with UV_CACHE_DIR=D:/uv-cache (per command, not persisted).
BROKE:     Nothing.
NEXT:      SEQUENCE step 3 = T-0003 (contracts module).

## 2026-10-03 — Ticket edit: /ml-model-builder gates in the cause-model tickets (user request)
BUILT:     A `Skill:` line plus gate-specific spec items in T-0006, 0007, 0009, 0010, 0011, 0012, 0013, 0015, 0017:
           Gate 0 frame (cause_model.py docstring), Gate 1 near-duplicate audit + split check, Gate 2 ladder
           (frozen-backbone linear probe vs fine-tune; fine-tune kept only if it beats the probe by > fold std),
           Gate 3 overfit-20 check + reproducibility hashes + fold-local class weights, Gate 4 ECE / slices /
           worst-error grid / staleness, Gate 5 self-describing final.pt + golden-crop artifact test.
RESULT:    check_sequence.py OK (no dependency or order change). GitHub issue bodies synced.
SURPRISE:  sklearn isn't installed, so the linear probe is the same torch model with the backbone frozen
           (no new dependency, no API change to 09's build_model()).
BROKE:     Nothing. 08-pseudocode P5 doesn't mention the probe rung yet (edit 06–09 only with approval).
NEXT:      SEQUENCE step 3 = T-0003.

## 2026-10-04 — Review of teammate's P1 (T-0003, T-0004, T-0032; PRs #53–#55)
BUILT:     Review only, plus two fixes. xqi/store.py: SCHEMA_VERSION is now imported from xqi.types (the
           duplicate copy would have silently diverged on a bump, which breaks the Versioning rule);
           write_detection(obj, ts) now stores the frame's ts (before, every detections.ts was hard-coded 0.0).
           tests: test_detection_keeps_frame_ts; test_causes_yaml_matches_type_defaults (causes.yaml vs types.py).
           BOARD rows for T-0003/0004/0032 → DONE (the PRs closed the issues but left BOARD/STATE/LOGBOOK alone).
RESULT:    Each Done-when checked against 09-interfaces: every type round-trips through JSON; default.yaml loads
           and all 6 validation rules raise ConfigError naming the key; store round-trips every table with WAL and
           the two-process decision insert works. `uv run pytest` → 40 passed; ruff clean.
SURPRISE:  - Nothing reads config/causes.yaml at runtime yet. 09 §Module APIs only lists config.load(), so no loader
             was added (that would be an API change). The drift test keeps it equal to the types.py defaults until
             T-0007 edits it, and at that point a loader has to exist (DESCEND to add it to 09).
           - Store detections are batched every 25 detections, not every 25 frames. That's harmless at this scale.
           - Store.query()'s read-only check is a prefix match ("WITH … DELETE" would get through on the loop
             connection). The UI side is safe because open_readonly uses mode=ro.
BROKE:     Store.write_detection signature (ts now required). No callers yet.
NEXT:      SEQUENCE step 6 = T-0021 (gate L1+L2). T-0002 (HUMAN) is still open.

## 2026-10-04 — DESCEND (user-approved): load_causes() + the remaining P1 review fixes
BUILT:     09-interfaces §Module APIs: added `load_causes(path) -> Causes`. This is the DESCEND, approved by the
           user ("fix the issues"). xqi/config.py: frozen Causes dataclass and load_causes(), which validate that
           every cause_action/cause_defects key is in causes, each var is in Var, each direction is ±1, and every
           defect is in DEFECTS. A violation raises ConfigError naming the key. xqi/store.py: detections are now
           flushed every 25 distinct frames (the spec says frames, not detections); query() runs under
           PRAGMA query_only, so "WITH … DELETE" can no longer write.
RESULT:    `uv run pytest` → 45 passed (+5: 3 load_causes rejections, CTE write rejected, frame batching); ruff clean.
           No SCHEMA_VERSION bump: the change is additive config API, not §Types/§Store/§Data.
SURPRISE:  Nothing.
BROKE:     Nothing.
NEXT:      SEQUENCE step 6 = T-0021 (gate L1+L2). T-0002 (HUMAN) is still open.

## 2026-10-15 — T-0021 Safety gate L2 + L1
BUILT:     xqi/gate.py: pure gate(p, state, now, cfg) -> GateDecision, fail-closed. L2 first (reject when
           now - last_change[v] < cool[v]; else clip |Δ| to step[v] and flag clipped), then round the target to an
           integer (round_half_up) and check L1 (physical envelope). L3 is a passing stub; L4 comes in T-0022.
           Missing/NaN required state -> passed=False, reason "state_unavailable". Layers tuple = (L2, L1, L3), each
           with a human-readable reason ("clipped +15 → +5 °C", "245 outside [170, 240] °C").
           tests/test_gate.py: 10 tests (clip; cooldown reject and allow-at-limit; 245 °C reject; flow 150.5 → 151
           half-up over L1; 206.5 → M104 S207; None/NaN setpoint; NaN last_change; layer order with no L4).
DISCREPANCY: The "shared round-half-up helper" named by T-0021 and T-0016 did not exist. Added round_half_up() to the
           shared xqi/types.py (math.floor(x + 0.5)); T-0016 will import the same one. Additive only — no
           §Types/§Store/§Data change, so no SCHEMA_VERSION bump. 09-interfaces does not list the helper; adding it
           there is a candidate DESCEND needing user approval (did not edit 06–09).
RESULT:    `uv run --no-sync pytest tests/test_gate.py` → 10 passed; full fast suite → 55 passed; `ruff check .` clean;
           `scripts/check_sequence.py` → OK (52 tickets). Env note: `uv` was not installed on this machine; installed it
           and a minimal Python 3.11 `.venv` (numpy, pyyaml, pytest, ruff) to avoid the multi-GB CUDA torch sync.
SURPRISE:  With an integer physical limit, round-half-up can only let a boundary value through (240.4 → 240), never push
           an in-range value out; the "rounding pushes over the limit" case is a raw target at/over the limit that rounds
           up (150.5 → 151). Both behaviours are pinned by tests.
BROKE:     Nothing.
NEXT:      SEQUENCE step 7 = T-0022 (gate L3 + event-verdict truth table). T-0002 (HUMAN) is still open.

## 2026-10-15 — T-0022 Gate L3 + event-verdict truth table
BUILT:     xqi/gate.py: real L3 (_window_result: pass iff the rounded target is in the L3 window or strictly closer
           to it than the current setpoint, via dist(y,[lo,hi]) = max(lo-y, 0, y-hi)); event_verdict(mode, cd, cset,
           est, flags, decisions, state, cfg) implementing the 07 §4 table (rows evaluated in order, first match
           wins; L4 = |C| = 1 and p_top >= tau and no flags is evaluated here, not in gate()). fail-closed guards:
           non-finite delta -> "invalid_delta", non-finite now -> "invalid_time"; passed=False always strips G-code.
           tests/test_gate.py: 37 tests (L2/L1 regressions, the L3 toward/away rule, a 10-row parametrised verdict
           table, recipe_blocked, L4-fail variants, NaN/inf delta and time).
RESULT:    `pytest tests/test_gate.py` -> 37 passed; full fast suite -> 157 passed; ruff clean.
SURPRISE:  - T-0022's example "220 -> 230 rejects" cannot reject through the whole gate: L2 clips +10 to +5 first,
             so the target is 225 which is inside [195,225] and passes. The reject is pinned directly on
             _window_result("nozzle_temp", 220, 230) and an end-to-end "away" case uses speed (110 + 10 = 120,
             step 10 so no clip, outside [80,110]).
           - §4 row 3 (gated-recipe) precedes row 4 (state missing), so gated-recipe with no survivors -> NOOP.
             Documented in STATE as a possible swap if the human wants fail-closed first.
BROKE:     Nothing.
NEXT:      SEQUENCE step 8 = T-0014 (split-conformal).

## 2026-10-15 — T-0014 Split-conformal calibration and prediction sets
BUILT:     xqi/explain/__init__.py (package docstring) + xqi/explain/conformal.py: calibrate(probs, y, alpha) -> qhat
           (LAC scores 1 - p_y; level = ceil((n+1)(1-alpha))/n; numpy.quantile method="higher"; level > 1 -> 1.0;
           n < 20 ValueError; validates shapes, finiteness, integer labels in [0,K), alpha in (0,1));
           predict_set(probs, qhat, labels) -> tuple (threshold 1 - qhat, ties inclusive, label order preserved);
           save_qhat / load_qhat for JSON metadata. tests/test_conformal.py: 26 tests including 20 000-draw
           empirical coverage at alpha in {0.05, 0.10, 0.20}.
RESULT:    `pytest tests/test_conformal.py` -> 26 passed; ruff clean.
SURPRISE:  save_qhat/load_qhat are not in 09 §Module APIs (only calibrate/predict_set are listed) but the ticket
           requires persisted calibration; added as additive API (recorded in STATE).
BROKE:     Nothing.
NEXT:      SEQUENCE step 9 = T-0016 (proposals/counterfactuals).

## 2026-10-15 — T-0016 Proposal and counterfactual generation
BUILT:     xqi/explain/counterfactual.py: severity(area_frac, recent_hits, cfg) (07 §1); make_proposal(cause, p,
           severity, state, cfg) -> Proposal | None (Δ = -d_c (d_min + s (d_max - d_min)), to_value unrounded,
           integer G-code M104/M140/M221/M220 via round_half_up, the §2 counterfactual sentence, "none" and
           "misalignment" -> None); recipe_to_proposals(defect, state, defect_id) (deck recipe -> one proposal per
           variable in yaml order, deterministic "<defect_id>:<var>" ids). tests/test_counterfactual.py: 15 tests.
RESULT:    `pytest tests/test_counterfactual.py` -> 15 passed; ruff clean.
SURPRISE:  None.
BROKE:     Nothing.
NEXT:      SEQUENCE step 10 = T-0019 (sensor checks).

## 2026-10-15 — T-0019 Deterministic telemetry sensor checks
BUILT:     xqi/explain/sensors.py: check(history, now, cfg) -> tuple[str, ...]. Flags: heater_deviation:nozzle|bed
           (|actual-target| > temp_dev_c continuously for > temp_dev_s), settling:<var> (target changed < settle_s
           ago, strict), printer_not_printing (state != "Printing" exactly), state_unavailable (empty history).
           tests/test_sensors.py: 15 tests incl. magnitude/duration boundaries, recovery, NaN last-change.
RESULT:    `pytest tests/test_sensors.py` -> 15 passed; ruff clean.
SURPRISE:  None (telemetry stays a safety signal only, never a model input — ADR-0002).
BROKE:     Nothing.
NEXT:      SEQUENCE step 11 = T-0023 (property test + recipe audit).

## 2026-10-15 — T-0023 Randomised gate property test + deck-recipe audit
BUILT:     tests/test_gate_property.py: fixed-seed random driver (state setpoints sampled in the L1 box widened by
           20 %, Δ in [-50,50], random last-change times; sequential dispatch of passing decisions) asserting the
           §3 invariant on every dispatch (|Δ'| <= step, L1 box, L3 inside-or-closer, cooldown). Fast 1 000 cases in
           the default suite; 100 000-case version marked slow writes reports/gate_property.md. scripts/gate_audit.py
           pushes each DECK_RECIPE from nominal through the gate and writes reports/recipe_audit.md.
RESULT:    fast -> 1 passed (1 deselected); `pytest -m slow tests/test_gate_property.py` -> 1 passed, dispatched
           42 947, 0 violations / 100 000; gate_audit -> 10 variables, 3 raw targets outside L3, 5 clipped, 0 blocked.
SURPRISE:  The recipes are never blocked because L2 clips the oversized step and the clipped target lands back
           inside L3; the "violates the envelope" evidence is the 3 raw recipe targets outside the L3 window plus
           the 5 clips (recipes are not applied raw). Rerun the audit after T-0024/T-0025 freeze the envelope.
BROKE:     Nothing (created reports/).
NEXT:      SEQUENCE step 12 = T-0035 (outcome verifier).

## 2026-10-15 — T-0035 Outcome verifier
BUILT:     xqi/verify.py: Verifier(window_s, settle_s) with a per-class ring buffer of (ts, present); watch() takes
           r_before over [t_a-W, t_a]; tick(frame_ts, present) appends and returns outcomes once ts >= t_a+S+W;
           close() flushes pending as unknown. classify_rate() is the pure §6 classifier: resolved if r_after <=
           0.5 r_before and <= 0.10; worsened if r_after >= 1.5 r_before and >= 0.20; unknown if a window has < 10
           frames or the run ended; persisted otherwise. tests/test_verify.py: 18 tests at a synthetic 10 fps.
RESULT:    `pytest tests/test_verify.py` -> 18 passed; ruff clean.
SURPRISE:  None.
BROKE:     Nothing.
NEXT:      SEQUENCE step 13 = T-0026 (Printer + FakePrinter) — P3. T-0002 (HUMAN) is still open.

## 2026-10-15 — P3 (T-0026, T-0027, T-0029, T-0030, T-0031, T-0033) — loop and environment
Checklist: the P3 acceptance checklist is in STATE.md ("P3 acceptance checklist"); every item is met.

## 2026-10-15 — T-0026 Printer protocol + FakePrinter
BUILT:     xqi/printer.py: Printer protocol (get_state/send_gcode/pause/resume/estop), PrinterError, FakePrinter.
           Thermal lag per 07-math §12 as explicit Euler with <= 0.25 s sub-steps (tau 8 s nozzle / 60 s bed) so
           M104 S220 from 210 reaches ~216.38 °C after 8 s (within 0.5 of 1-e^-1); flow/speed apply immediately and
           are recorded in last_change_ts; M112 -> state Error and every later send returns False. The clock is
           injectable; `connected` and `fail_next` are test controls. tests/test_printer_fake.py: 16 tests.
RESULT:    `pytest tests/test_printer_fake.py` -> 16 passed; ruff clean.
SURPRISE:  Windows time.monotonic() is coarse; the FakePrinter takes an injected clock so tests never depend on it.
BROKE:     Nothing.
NEXT:      T-0027.

## 2026-10-15 — T-0027 OctoPrint REST client
BUILT:     xqi/printer.py: OctoPrintClient. requests.Session with X-Api-Key read from the env var named in the
           config (never logged). GET /api/printer (temps + state), GET /api/job (progress); POST
           /api/printer/command {"commands": [...]}; POST /api/job {"command": "pause", "action": pause|resume};
           estop = M112. Timeout = cfg.printer.timeout_s; one retry on a connection error; a timeout returns False
           with flow/speed setpoints unchanged (they are tracked from successfully sent M221/M220, initialised from
           cfg.printer.nominal). Unavailable HTTP status, malformed JSON or a missing temperature field raises
           PrinterError (never a fabricated reading). tests/test_octoprint.py: 23 tests, Session.request mocked.
RESULT:    `pytest tests/test_octoprint.py` -> 23 passed (no real network); ruff clean.
SURPRISE:  requests.ConnectTimeout subclasses both ConnectionError and Timeout; Timeout is caught first so a
           connect timeout is treated as a timeout (no retry), matching "a timeout -> returns False".
BROKE:     Nothing.
NEXT:      T-0029.

## 2026-10-15 — T-0029 Frame sources
BUILT:     xqi/camera.py: open_source(spec, width, height) -> Iterator[Frame]. "<int>" opens cv2.VideoCapture at
           the configured resolution and skips failed reads (100 consecutive failures -> CameraError);
           "replay:<dir>" replays images sorted by filename and "replay:<dir>@<fps>" paces playback; ts =
           time.monotonic() and frame_id counts from 0; CameraError on an unopenable camera or a missing replay
           directory. tests/test_camera.py: 13 tests (+1 hw test).
RESULT:    `pytest tests/test_camera.py` -> 13 passed, 1 deselected; ruff clean.
SURPRISE:  Windows monotonic is ~15 ms coarse, so back-to-back replay frames can share a tick; frame ts is nudged
           forward by 1 µs on a tie to keep it strictly increasing (base is still time.monotonic()).
BROKE:     Nothing.
NEXT:      T-0030.

## 2026-10-15 — T-0030 YOLO11 detector wrapper
BUILT:     xqi/detect.py: DetectorError, Detector(weights, imgsz, conf, device, model=None). ultralytics.YOLO is
           imported lazily (torch need not be installed for the wrapper or its tests); model class names normalise
           (lower-case, spaces/hyphens -> "_", dots dropped, e.g. "Over-extr." -> over_extrusion); the no-defect
           class is dropped; an unknown name raises at init; area_frac = box area / frame area; malformed boxes are
           skipped; a missing weights file or a load failure raises DetectorError before ultralytics is imported;
           inference exceptions propagate. tests/test_detect.py: 10 tests (+1 gpu test).
RESULT:    `pytest tests/test_detect.py` -> 10 passed, 1 deselected; ruff clean.
SURPRISE:  The legacy AM_*.pt files carry junk classes (defect/object/p/s), so the strict name map rejects them by
           construction — the intended behaviour, and consistent with the P0 observation in this logbook.
BROKE:     Nothing.
NEXT:      T-0031.

## 2026-10-15 — T-0031 Confirmation tracker (with severity)
BUILT:     xqi/detect.py: ConfirmationTracker(hits, rearm_frames, cfg). Per class it keeps a streak, the first
           streak ts, an armed flag, an absent counter and a recent deque of length cfg.severity.window. `hits`
           consecutive present frames confirm one ConfirmedDefect (uuid4 id, t0 = first streak ts, t_conf = frame
           ts, conf/xyxy/area_frac from the highest-confidence box of that class, recent_hits = sum(recent),
           severity() from T-0016, critical = cls in cfg.critical); rearm_frames misses re-arm. tests/test_confirm.py:
           12 tests (streak, gap, rearm, two classes, max-conf box, severity, critical, window cap, determinism).
RESULT:    `pytest tests/test_confirm.py` -> 12 passed; ruff clean.
SURPRISE:  deque(maxlen=...) needs an int; cfg.severity.window loads as a float, so it is cast with int().
BROKE:     Nothing.
NEXT:      T-0033.

## 2026-10-15 — T-0033 Orchestrator (baseline, critical-first, timings, CLI)
BUILT:     xqi/orchestrator.py: Orchestrator(cfg, printer, source, detector, explainer, store, *, clock) builds the
           ConfirmationTracker and Verifier from cfg and runs the P1 loop: camera-gap pause + camera_gap alert when a
           frame is late; detector errors are logged as detector_error and the frame is skipped (10 in a row ->
           pause + DetectorFailure, so the CLI exits non-zero); confirmed events are handled critical-first (sorted
           critical before non-critical) and a critical class dispatches M112 (estop) or pause before any other work
           for that frame; baseline mode sends recipe_to_proposals(cls, nominal_state, defect_id) G-code as absolute
           setpoints (under_extrusion -> M104 S205, M220 S80, M221 S110); t0/t_conf/t_disp timing rows and an
           APPLY_RAW/CRITICAL verdict are written; passing baseline actions feed verifier.watch and outcomes are
           written on tick/close. The non-baseline (cause) path is a NOOP phase boundary with an alert — T-0034 (P5)
           replaces it. xqi/__main__.py: `run --config --mode --max-frames`, run_id = UTC timestamp, git sha or
           "nogit". config/baseline_demo.yaml + demo/ + scripts/make_demo_assets.py give a fully offline run.
           tests/test_orchestrator.py: 24 tests (parity, streak, timings, outcome, critical-first, failure handling,
           disconnected printer, camera gap, cleanup, multi-run isolation, gate->dispatch/cooldown/fail-closed, e2e < 10 s, CLI).
RESULT:    `pytest tests/test_orchestrator.py` -> 24 passed; `python -m xqi run --config config/baseline_demo.yaml
           --mode baseline` -> exit 0, run wrote 6 detections, 1 defect, 1 action (gcode ["M104 S205","M220 S80",
           "M221 S110"], ok=1), 1 APPLY_RAW verdict and 3 timings; `python -m xqi run --mode baseline` -> exit 2
           (--config required); ruff clean.
SURPRISE:  - The baseline path needs a *deterministic* detector to run offline, since no YOLO11 weights exist. Added
             the additive `detector.kind: yolo | replay` config key + ReplayDetector (recorded detections JSON);
             config/default.yaml is unchanged. Recorded in STATE as a candidate 09 §Config edit.
           - Baseline uses the nominal setpoints (cfg.printer.nominal) as the "from" state, so the deck-recipe G-code
             is absolute and deterministic; it does not read live telemetry (ADR-0002).
           - The orchestrator does not read printer state for the baseline or critical paths, so it never fabricates
             a reading; missing telemetry fail-closed behaviour is in the gate/event_verdict (test_gate, T-0021/0022).
BROKE:     Nothing.
NEXT:      SEQUENCE step 19 = T-0020 (Explainer, P4). P3 is complete.
