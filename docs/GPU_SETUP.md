# GPU Laptop Manual (for the team)

This applies whenever Claude Code stops with **⚠ GPU REQUIRED — T-00NN**. That means the code for that step is already pushed and tested on CPU. You only have to run it on a GPU laptop (RTX 3050, 4 GB) and push the results back. Each GPU step has its own runbook at `docs/gpu-runs/T-00NN.md`. This file covers the parts every runbook shares.

---

## A. One-time setup (≈ 30 min, once per laptop)

Open **PowerShell** (not as admin unless noted).

1. **NVIDIA driver.** Run `nvidia-smi`. It must print the GPU name and a "CUDA Version" ≥ 12.6. If it fails or shows a lower version, update the driver from nvidia.com (GeForce Game Ready or Studio driver) and reboot.
2. **Git + GitHub CLI.**
   ```powershell
   winget install --id Git.Git -e
   winget install --id GitHub.cli -e
   gh auth login        # pick GitHub.com → HTTPS → log in with the browser
   ```
   Your GitHub account needs write access to `Ayush-3103-AI/SDP`. Ask Ayush to add you as a collaborator.
3. **uv (the Python manager this repo uses).**
   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
   Close and reopen PowerShell afterwards.
4. **Clone and install.**
   ```powershell
   cd $HOME\Documents
   git clone https://github.com/Ayush-3103-AI/SDP.git
   cd SDP
   uv sync
   ```
   `uv sync` installs the CUDA build of PyTorch (configured in `pyproject.toml`). The first time it downloads ≈ 3 GB.
5. **Check the GPU from Python.**
   ```powershell
   uv run python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
   ```
   Expected output: `<version>+cu126 True NVIDIA GeForce RTX 3050 Laptop GPU`. If it prints `False`, see Troubleshooting.
6. **Data and weights.** These are gitignored, so copy them yourself from the shared folder listed in `docs/inherited/HANDOVER.md`:
   - REU dataset → `SDP\data\raw\dataset\`
   - induction log → `SDP\data\raw\induction\`
   - YOLO11-S weights → `SDP\models\yolo\best.pt`

---

## B. Every GPU run

1. **Before you start**
   - Plug the laptop in. Close games, browsers with video, and anything else using the GPU (`nvidia-smi` should show < 300 MB used).
   - Optional, for runs longer than 30 min: stop the laptop sleeping. Run `powercfg /change standby-timeout-ac 0`, and undo it afterwards with `powercfg /change standby-timeout-ac 30`.
2. **Get the latest code**
   ```powershell
   cd $HOME\Documents\SDP
   git pull
   uv sync
   ```
3. **Open the runbook** `docs/gpu-runs/T-00NN.md` and run its commands **exactly as written, in order**. Each command lists its expected output and run time. If the output looks different, stop and go to step 5. Don't improvise.
4. **Send the results back.** The runbook lists exactly which files to add, usually `reports/...` plus small files in `models/cause/`.
   ```powershell
   git pull --rebase
   git add <files listed in the runbook>
   git commit -m "T-00NN: GPU run results (refs #NN)"
   git push
   gh issue comment NN --body "GPU run done on <laptop name>, <date>. Results pushed in <commit hash>. Notes: <anything odd>"
   ```
   Use **refs**, never **closes**. Claude Code closes the ticket after it has checked the results.
5. **If something fails**
   - Copy the **whole** error output into a comment on the issue: `gh issue comment NN --body-file error.txt`, or paste it on github.com.
   - Don't edit code on the GPU laptop. Claude Code fixes it and pushes; you then pull and re-run.
6. **Tell Ayush** "GPU results for T-00NN are pushed". The next Claude Code session then pulls, verifies and continues.

---

## C. Troubleshooting
| Symptom | Fix |
|---|---|
| `torch.cuda.is_available()` → False | Driver too old (step A1), or a CPU torch got installed: run `uv sync --reinstall-package torch` and re-check |
| `CUDA out of memory` | Close other GPU apps; re-run with the smaller `--batch` value the runbook gives. The training script also halves the batch automatically once |
| `FileNotFoundError: data/...` | Data not copied (A6), or a data-prep command in the runbook was skipped |
| `git push` rejected | `git pull --rebase`, then push again. If a conflict appears in anything other than the files you added, stop and comment on the issue |
| Laptop very hot or throttling | Raise it for airflow and keep it plugged in; long runs are expected to take the runbook's stated time ×1.5 at most |

---

## D. Runbook template (Claude Code writes one per GPU step)

```markdown
# ⚠ GPU RUN — T-00NN <title>  (issue #NN)
Written against commit: <short sha>   ·   Est. time: <min>   ·   Peak VRAM: <GB>   ·   Needs data: yes/no
Batch: <which other GPU steps can be run in the same sitting, if any>

## Prerequisites
- [ ] Setup A done on this laptop   - [ ] `git pull && uv sync` done   - [ ] data present: <paths>

## Steps
1. `<command>`
   Expected: <what success looks like>   Time: <min>
2. ...

## Success check
- <file> exists and its first line says <...>

## Send back (exact list)
git add <files>
git commit -m "T-00NN: GPU run results (refs #NN)"

## If it fails
<known failure modes + the exact alternative command, e.g. --batch 16>
```
