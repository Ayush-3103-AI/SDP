# STATE — SDP: Explainable, safe HITL correction for FFF (CARR 4.1.3 slice)

PHASE:        5 — EXECUTE
LAST SESSION: 2026-10-15 — implemented the whole P3 loop/environment batch: T-0026 (Printer protocol + FakePrinter),
              T-0027 (OctoPrint client), T-0029 (frame sources), T-0030 (YOLO11 detector wrapper),
              T-0031 (confirmation tracker + severity), T-0033 (orchestrator baseline + critical-first + CLI).
              Fast suite 255 passed / 3 deselected, slow property run green, ruff clean, baseline CLI runs offline.
NEXT ACTION:  SEQUENCE.md step 19 = T-0020 (Explainer, P4) — the first ticket after P3. P1/P2/P3 code paths are
              built; P4/P5+ (T-0020, T-0034, T-0036..) are NOT started. T-0002 (HUMAN) is still open.

## Load for next session
- project-context/STATE.md (this file)
- project-context/11-tickets/SEQUENCE.md (canonical order)
- project-context/11-tickets/T-0020.md (next ticket) or T-0034.md
- the sections its Context: line names
Nothing else.

## P3 acceptance checklist (T-0026, T-0027, T-0029, T-0030, T-0031, T-0033)
All items below are met; evidence is in tests/ and in LOGBOOK.md 2026-10-15 (P3) entries.
- [x] T-0026 Printer protocol + FakePrinter: 5 operations; thermal lag per 07-math §12; M112 -> Error; flow/speed
      immediate; injected clock; disconnected/fail_next test controls; 16 tests.
- [x] T-0027 OctoPrint client: X-Api-Key from the cfg-named env var (never logged); GET /api/printer, /api/job;
      POST /api/printer/command, /api/job pause/resume; M112 estop; timeout = cfg.printer.timeout_s; one retry on a
      connection error; timeout -> False with setpoints unchanged; unavailable/malformed state -> PrinterError;
      23 tests, HTTP mocked (no real network).
- [x] T-0029 Frame sources: open_source("<int>") -> VideoCapture at the cfg resolution; "replay:<dir>[@<fps>]";
      ts = monotonic (strictly increasing), frame_id from 0; failed reads skipped; CameraError on an unopenable /
      exhausted camera or a missing replay dir; 13 tests + 1 hw test.
- [x] T-0030 Detector wrapper: lazy ultralytics.YOLO; name normalisation ("Over-extr." -> over_extrusion); unknown
      name raises at init; no-defect class dropped; area_frac = box/frame; injected model; missing weights / load
      failure -> DetectorError; inference errors propagate; 10 tests + 1 gpu test.
- [x] T-0031 Confirmation tracker: per-class streak/rearm exactly per P2; ConfirmedDefect with uuid4 id, t0 = first
      streak ts, severity() from T-0016, critical = cls in cfg.critical; 12 tests.
- [x] T-0033 Orchestrator: P1 loop with camera-gap pause, detector-failure handling (10 in a row -> pause + exit
      non-zero), critical-first (M112/pause before any other work), baseline deck recipe as absolute setpoints,
      t0/t_conf/t_disp timing rows, verifier tick/close wiring; CLI `python -m xqi run --config --mode --max-frames`
      with run_id = UTC timestamp and git sha (or "nogit"); 24 tests incl. an offline end-to-end run < 10 s.
- [x] No P4+ work: cause model / Explainer (P4) and the non-baseline action paths (T-0034, P5) are not implemented;
      the non-baseline path is a documented NOOP phase boundary.
- [x] Offline: no test needs a printer, camera, internet or downloaded weights; `hw`/`gpu`/`slow` tests are marked
      and deselected by default (3 deselected).

## Built so far (P1 done except T-0002; P2 done; P3 done)
- xqi/types.py: §Types dataclasses + §Constants defaults, SCHEMA_VERSION = 1; round_half_up() shared helper (T-0021)
- xqi/config.py: load(path) -> frozen Config; load_causes(cfg.causes_file) -> Causes (runtime taxonomy; T-0007 edits
  causes.yaml, the test pinning it to the types.py defaults must be updated then); ConfigError("<dotted.key>: <why>")
- xqi/store.py: Store(path) WAL, busy_timeout 2000 ms; open_readonly + insert_decision for the UI;
  write_detection(det, ts) is batched every 25 frames and flushed on close; query() enforces PRAGMA query_only
- xqi/gate.py: pure gate(p, state, now, cfg) -> GateDecision and event_verdict(...) -> EventVerdict. Layers L2 then
  L1 then L3 (L3 = in the characterised window or strictly closer to it); L4 confidence is evaluated per event in
  event_verdict (07-math §4, first matching row wins). Rejected decisions never carry G-code; missing/NaN
  setpoint, last-change, delta or time is fail-closed.
- xqi/explain/conformal.py: calibrate (LAC qhat, n >= 20, level > 1 -> 1.0, method="higher"), predict_set
  (threshold 1 - qhat, ties inclusive), save_qhat / load_qhat (JSON).
- xqi/explain/counterfactual.py: severity (§1), make_proposal (severity-scaled Δ, integer G-code, §2 sentence),
  recipe_to_proposals (deck recipe -> per-variable proposals, deterministic "<defect_id>:<var>" ids).
- xqi/explain/sensors.py: check(history, now, cfg) -> flags (heater_deviation:*, settling:*, printer_not_printing;
  "state_unavailable" when history is empty).
- xqi/verify.py: Verifier(window_s, settle_s) with watch/tick/close; classify_rate() is the pure §6 classifier
  (resolved / persisted / worsened / unknown; unknown when a window has < 10 frames or the run ended).
- tests/test_gate_property.py + scripts/gate_audit.py: 1 000-case fast invariant test, 100 000-case slow test
  (reports/gate_property.md, 0 violations), and the deck-recipe envelope audit (reports/recipe_audit.md).
- xqi/printer.py: Printer protocol (get_state/send_gcode/pause/resume/estop), FakePrinter (07-math §12 thermal lag,
  injected clock, `connected`/`fail_next` test controls), OctoPrintClient (X-Api-Key from the cfg env var, one retry
  on a connection error, timeout -> False, malformed/unavailable state -> PrinterError) — T-0026/T-0027.
- xqi/camera.py: open_source(spec, width, height) for "<int>" (VideoCapture) and "replay:<dir>[@<fps>]"; ts from
  monotonic made strictly increasing; CameraError — T-0029.
- xqi/detect.py: Detector (lazy ultralytics, name normalisation, injected model), ReplayDetector (recorded
  detections for offline runs, detector.kind: replay), ConfirmationTracker (P2 streak/rearm + severity) — T-0030/T-0031.
- xqi/orchestrator.py + xqi/__main__.py: the P1 loop with the P3 critical + baseline branches, camera-gap pause,
  detector-failure handling, t0/t_conf/t_disp timings, and `python -m xqi run --config --mode --max-frames` — T-0033.
- config/baseline_demo.yaml + demo/ + scripts/make_demo_assets.py: a fully offline deterministic baseline run
  (fake printer, replay frames, recorded detections) — no camera, weights or network.

## Settled — do not relitigate
- Implementation order = 11-tickets/SEQUENCE.md, 52 steps; changes need user approval + scripts/check_sequence.py OK
- New standalone `xqi` package; REU code is reference only — ADR-0001
- Image-only learned cause model; telemetry never a model input — ADR-0002 (one-way for eval validity)
- Split-conformal LAC sets, α = 0.10 — ADR-0003
- Pure 4-layer gate: L2 clips, L1/L3 reject, L4 routes; fail-closed — ADR-0004
- Streamlit + SQLite, two processes; UI only inserts operator_decisions — ADR-0005
- Critical classes default M112 (deck parity) — ADR-0006
- LOGO by trial is the frozen eval — ADR-0007 (frozen at T-0007)
- Non-goals: RL, firmware changes, new sensors, new DOE, generative counterfactuals — 06-requirements §Non-goals
- Tooling: uv + hatchling, Python pinned 3.11 (.python-version), torch/torchvision from the pytorch-cu126 index, pytest addopts skip gpu/hw/slow

## Open branches
- B1 cause taxonomy → T-0007
- B2 envelope numbers → T-0024 / T-0025
- B3 clog: estop vs pause → T-0025 (Dr. Meti)
- B4 leave-one-printer-out → T-0050 (COULD)

## Questions for the human (answer at the gate; recommended answer in brackets)
- Q1 Semester end date / demo date? [assume ~14 weeks from 2026-10-05; the week plan in BOARD.md uses that]
- Q2 Team size and who is the HUMAN owner for T-0002, T-0025, T-0041, T-0045? [team lead owns 0002; two people for 0041]
- Q3 Any KLE SDP rubric or CARR lab standard to follow (doctrine hook)? [none → this framework governs]
- Q4 Does Dr. Meti accept the charter thresholds S1–S5? [accept as written; revisit at the T-0013 gate review]
- Q5 Teammates: please update BOARD.md / STATE.md / LOGBOOK.md in the same PR as the ticket (CLAUDE.md step 7).

## Highest unretired risk
A1 [unknown]: whether the REU induction log can be joined to individual boxes (K1, at the T-0006 audit).
If it fails, the learned cause model (the core of the explanation layer) is replaced by the ADR-0002 fallback.
T-0002 is the head of the critical path and is still open.

## Kill criteria watch
- K1 at T-0006 · K2 at T-0013 · K3 at week 6 (T-0028 / T-0039)

## Deferred questions raised out of phase
- C: drive has < 1 GB free, so `uv sync` fails unpacking CUDA torch into the default uv cache. Free space on C:
  or set UV_CACHE_DIR to a D: path permanently (this session used D:/uv-cache per command).
- T-0021: the "shared round-half-up helper" both T-0021 and T-0016 name did not exist. Added round_half_up() to
  xqi/types.py (additive; no §Types/§Store/§Data break, no SCHEMA_VERSION bump). 09-interfaces §Module APIs does
  not list it yet — recording it there is a candidate DESCEND and needs user approval before editing 06–09.
- T-0014: 09-interfaces §Module APIs lists only calibrate() and predict_set(); save_qhat()/load_qhat() (JSON
  qhat + alpha + n) were added as the ticket requires persistent calibration metadata. Additive — no schema break.
- T-0019/T-0035: sensors.check() and Verifier match the frozen signatures; verify.py additionally exports the pure
  classifier classify_rate() and MIN_WINDOW_FRAMES so the §6 thresholds are unit-testable. Additive.
- T-0022: §4 lists mode = gated-recipe (row 3) before "state missing" (row 4), so in gated-recipe mode a missing
  state yields NOOP(recipe_blocked) via the empty survivor set, not ESCALATE. This follows the explicit
  first-match row order; if the human prefers fail-closed to win over row 3, swap rows 3 and 4.
- T-0023: the physical envelope is still provisional (T-0024/T-0025). The recipe audit is therefore a run against
  the current default.yaml numbers, not the frozen ones.
- T-0033: (1) ADDITIVE config key `detector.kind: yolo | replay` (default "yolo") which selects ReplayDetector —
  needed for a deterministic offline CLI baseline because no YOLO11 weights exist yet; config/default.yaml is
  unchanged. This is a candidate edit to 09-interfaces §Config (needs approval). (2) 09-interfaces §Module APIs
  names ConfirmationTracker's third argument `severity_cfg`; it receives the full Config (the tracker needs
  cfg.severity and cfg.critical). Positional signature unchanged. (3) camera frames nudge equal timestamps by 1 µs
  so ts is strictly increasing (Windows monotonic is ~15 ms coarse). (4) the non-baseline (cause) paths are a
  documented NOOP phase boundary — T-0034 (P5) replaces them; the P4 Explainer is not built.
- T-0030: the model→DEFECTS name map is strict (an unknown class name raises at init). The shipped legacy .pt files
  carry junk classes, so they will be rejected by construction, as the spec requires.
