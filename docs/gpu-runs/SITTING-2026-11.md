# Teammate sitting, November 2026: data → model → evaluations → dashboard + study
Written 2026-11-05 against main. For the team's GPU laptop (RTX 4050) and the Claude Code session running there.
Total ≈ 6–8 h, most of it unattended (subset fetch ~2–3 h, T-0013 ~3 h). The CPU block (step 6) can run in between.

## Rules for the runner (they override the "Every session" and "GPU steps" parts of CLAUDE.md, which are for the dev laptop)
- This IS the GPU laptop: GPU runs and `-m slow` belong here.
- Run each runbook exactly as written. Do not edit tracked files except the result files a runbook's "Send back" lists:
  no code fixes, no edits to STATE.md / LOGBOOK.md / BOARD.md / SEQUENCE.md / config/*.yaml, no closing issues.
  Commits use `refs #NN`, never `closes`.
- Scratch files go under `runs\` (gitignored) or outside the repo. Never commit `data\` (except `data\splits\logo.json`),
  `D:\caxton`, crops, data CSVs or secrets.
- `scripts\make_splits.py` runs once, never with `--force`. Never edit `data\splits\logo.json`.
- If a command fails: stop that ticket, post the full error (`gh issue comment NN --body-file err.txt`), skip the tickets
  that depend on it, carry on with the independent ones.
- **Hard stops:** the T-0065 stop gate (K1′ FAIL or a proposed cause drop) stops steps 2–5. K2 firing in
  `reports\cause_eval.md` stops steps 4–5. Push what you have and comment on the issue.
- After each push: `gh issue comment NN --body "Run done on <laptop, GPU>, <date>. Results in <sha>. Notes: <...>"`.
- If you redirect script output to a file, set `$env:PYTHONUTF8=1` first (the scripts print α, θ, K1′, →).

## Steps
0. Setup (10 min): `git pull`, `uv sync`, the GPU check from docs/GPU_SETUP.md §A5, then `uv run pytest -q` (must pass;
   if not, post the output on #65 and stop). Note the GPU name for every issue comment.
1. **T-0065 Part 2 (#65)**: docs/gpu-runs/T-0065.md, Part 2. Step 1b fetches only the ~91 k images the pipeline uses
   (~4–5 GB) straight out of the remote zips. You can stop the full 54 GB download once step 1b reports `failed 0`.
   Do not apply anything `reports\l3_window.md` suggests; Ayush reviews it. Obey the runbook's stop gate.
2. **T-0012 (#12)**: docs/gpu-runs/T-0012.md (GPU ~35 min).
3. **T-0013 (#13)**: docs/gpu-runs/T-0013.md (GPU ~3 h, unattended; disable sleep first, restore it afterwards).
4. **T-0015 (#15) → T-0017 (#17) → T-0063 (#63)**: their runbooks (CPU, minutes each), on the T-0013 outputs.
5. **T-0036 (#36)**: docs/gpu-runs/T-0036.md (GPU ~15 min). Put the GPU name at the top of the issue comment: the spec's
   S4 target is written for an RTX 3050.
6. **CPU block** (independent; can run while T-0013 trains; Krish takes the screenshots and joins the pilot):
   T-0037 (#37) → T-0038 (#38) → T-0043 (#43) → T-0044 (#44), each from its runbook.
7. **Sir's Drive camera roll** (data only; the analysis script T-0067 is not built yet). Ayush sends the link privately.
   Never write that link into the repo, an issue or a commit: the repo is public. Download the camera-roll JPGs
   (~5,490 images, ~300 MB) to `D:\reu\camera_roll\` and the old models (AM_1/AM_2 .pt) to `D:\reu\models\`. Commit
   nothing; post the image count and folder size on #67.

## Send back (every file, from the runbooks)
| Ticket | Files |
|---|---|
| T-0065 | docs/data/CAXTON.md, reports/data_audit.md, reports/l3_window.md, data/splits/logo.json |
| T-0012 | reports/cause_floor.md, reports/cause_fold0.md, fold-0 logs (`git add -f`) |
| T-0013 | reports/cause_eval.md, reports/cause_errors.png, reports/cause_fold0.md, models/cause/final.pt, models/cause/preds_fold0–4.npz, models/cause/preds_final.npz, tests/fixtures/cause_golden, logs (`git add -f`) |
| T-0015 | reports/conformal.md, models/cause/qhat.json |
| T-0017 | reports/counterfactual.md |
| T-0063 | reports/proactive.md |
| T-0036 | reports/latency.md |
| T-0037 / T-0038 | reports/img/ui_live.png, reports/img/ui_card.png |
| T-0043 / T-0044 | reports/study/pilot.sqlite (`git add -f`), reports/img/study_off.png, reports/img/study_on.png, reports/operator_study.md |

## Finish
Post one summary comment on #65: a table of ticket | PASS / FAIL / skipped (why) | commit sha | time taken. Everything
must be pushed before you stop.
