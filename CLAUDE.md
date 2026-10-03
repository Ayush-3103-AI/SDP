# CLAUDE.md — SDP: Explainable, safe human-in-the-loop correction for FFF printing

This repo implements a UG-scale piece of CARR Topic 4.1.3 (deck: `context`). The project's memory is `project-context/`; the code is its output.

## Every session (one ticket per session)
1. Read `project-context/STATE.md` and `project-context/11-tickets/SEQUENCE.md`. The ticket to do is the lowest-numbered step that isn't DONE in BOARD.md, applying SEQUENCE.md's skip rules if it's blocked. Read that ticket.
2. Read **only** the context sections the ticket's `Context:` line names. Don't open other spec files "just in case".
3. Check the ticket's `Depends on:` are DONE in `11-tickets/BOARD.md`. If not, stop and say which ones are blocking.
4. Owner HUMAN → don't execute it; tell the user what they need to do. Owner PAIR → do the CODE part, then hand the human their part with exact commands.
5. Build test-first: write the ticket's `Test:` first, see it fail, then implement.
6. Run `uv run pytest` (default markers exclude gpu/hw/slow) and `uv run ruff check .`. Done means the ticket's `Done when:` is observably true. "Mostly working" is not done.
7. Append a LOGBOOK.md entry (BUILT / RESULT / SURPRISE / BROKE / NEXT). Fully rewrite STATE.md (< 200 lines). Update the ticket's row in BOARD.md. Commit with message `T-00NN: <title> (closes #NN)` and push. GitHub issue #NN is ticket T-00NN in github.com/Ayush-3103-AI/SDP. For HUMAN/PAIR tickets, comment progress on the issue with `gh issue comment NN`.
8. Stop. Report the outcome and name the next step from SEQUENCE.md. Do not start it. Never reorder SEQUENCE.md without the user's approval.

## GPU steps (standing instruction from the user)
This dev machine has CPU-only torch. Whenever the next step needs a GPU (marked 🖥 in SEQUENCE.md, or any `Done when` that
needs a CUDA run or `-m gpu`):
1. **Build and test everything CPU-side first**: scripts, unit tests, and a `--limit`/`--epochs 1` CPU smoke run.
2. **Write the runbook** `docs/gpu-runs/T-00NN.md` from the template in `docs/GPU_SETUP.md` §D. It needs exact commands
   (including any data-prep commands), expected output, estimated time and VRAM, the success check, the exact files to send back,
   and the known failure fixes. Say which other GPU steps could run in the same sitting.
3. **Commit and push everything**: `T-00NN: ready for GPU run (refs #NN)` (use refs, not closes). Then post
   `gh issue comment NN` with the runbook link. Mark the ticket's BOARD.md row `WAITING-GPU`.
4. **Warn the user** at the very top of the reply:
   `⚠ GPU REQUIRED — T-00NN (#NN): <what> · runbook: docs/gpu-runs/T-00NN.md · est. <time> · send back: <files>`
5. Continue with the next non-GPU step per SEQUENCE.md rule 2. Never run the GPU part on this machine beyond the CPU smoke run.
6. When the team says results are pushed: `git pull`, verify `Done when` against the pushed files, then close the ticket the
   normal way (`closes #NN`). Bad or missing results → comment on the issue with what's wrong, then fix the code and push.

## Hard rules
- **Never feed setpoints or telemetry into the cause model** (ADR-0002). `CauseModel.predict` takes only (crop, defect).
- **Never send printer commands outside `gate()`**, except the critical-class estop/pause and baseline mode. The UI never talks to OctoPrint.
- **Never edit `data/splits/logo.json`** after T-0007, and never tune anything on test folds.
- **Never send heater, motion or M112 commands from a script against a real printer** unless the ticket says so and the user is present.
- **If a ticket reveals a spec error**, stop and propose a DESCEND (edit `06`–`09` only with the user's approval). Don't patch around it.
- **Kill criteria K1 (T-0006), K2 (T-0013), K3 (week 6):** when one fires, report it and stop. Don't push on.
- Breaking change to `xqi/types.py`, the store schema or the data CSVs → bump `SCHEMA_VERSION` and log a DESCEND.
- Secrets: the OctoPrint key comes from the env var `XQI_OCTOPRINT_KEY`. Never write it to files or logs.
- Write code that reads like the code around it. Smallest diff that meets `Done when`. No new dependency if stdlib or an installed one does it.

## Commands
- Tests: `uv run pytest` · slow: `uv run pytest -m slow` · GPU: `uv run pytest -m gpu` · hardware: `uv run pytest -m hw`
- Lint: `uv run ruff check .`
- Run the loop: `uv run python -m xqi run --config config/default.yaml --mode advisory`
- Dashboard: `uv run python -m xqi ui --run latest`

## Environment
- Dev machine: Windows 11, Python 3.11. The rig laptop has an RTX 3050 (4 GB VRAM).
- GPU laptops: `uv sync` installs CUDA torch (configured in pyproject by T-0001). Team setup and run procedure: `docs/GPU_SETUP.md`.
- Large inherited files (`*.zip`, `AM_*_Model_*.pt/`) are old YOLOv8n models. They are not the deck's YOLO11-S; ignore them.
