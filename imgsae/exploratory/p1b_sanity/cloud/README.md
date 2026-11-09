# Modal (cloud GPU) for Phase 1b

**Budget rule (user, 2026-11-09).** Modal's free credit is $30 of compute per month. The whole project stops at **$29**.
- Every task has its own budget in `ledger.json`. Using the reserve or moving money between tasks needs the user's OK.
- Usage is checked before every launch, and each check is logged in `ledger.json` under `checks`.

| task | budget | what |
|---|---|---|
| a3_sae | $3 | A3 `--part sae`: 4 SAE methods × 3 replicates on L4 |
| stageC_encode | $10 | held-out scans: CT-FM + untrained encodes, perturbations (placeholder until Stage C is planned) |
| stageC_fit | $4 | frozen A1–A3 rerun on held-out data (placeholder) |
| stageD_dinov3 | $6 | optional 2D DINOv3 arm (placeholder) |
| reserve | $6 | retries and surprises (only with the user's OK) |

## How the guard works
`budget.py check` allows a launch only if all three checks pass:
1. **Task:** the task's committed cost plus this launch's worst case stays within the task's budget.
2. **Project:** all committed costs plus this worst case stay ≤ $29.
3. **Month:** Modal's own billing summary (metered cost minus free storage, the whole workspace including other apps) plus open worst cases plus this worst case stays ≤ $29.

**Worst case.** It equals containers × (timeout + 3 min) × hourly rate.
- Rates (`modal billing rates`, 2026-11-09): L4 $0.80/h, CPU $0.047/core/h, memory $0.008/GiB/h. One L4 container with 4 cores and 16 GiB costs $1.12/h.
- Modal stops each call at its timeout, so a launch can't cost more than its worst case. The only extra is a $0.10 allowance for the image build.
- After a run, its measured cost (container minutes + 3 min each) replaces the worst case in the ledger.

`python budget.py status` prints month usage, project total and per-task totals. Run it with miniconda's python, which has the Modal client.

## Files
- `upload_p1.ps1` puts the inputs on the volume `imgsae-p1b`, about 3 GB:
  - rows.npz cut to `X_ctfm`, lab, scan, gidx and the prep parameters (byte copies);
  - perturbation files;
  - concepts.json and gates.json.

  Storage costs about $0.27/month. Delete the volume with `modal volume delete imgsae-p1b` when the project ends.
- `a3_sae_modal.py` runs one L4 container per (method, replicate) with the same code as the local run (`a3_decomp_fair.load_input`, `fit_eval`). It merges results into `results/a3_sae.json` and stops before launch if the budget check fails.
- `logs/a3_sae.done` tells `run_stageA.ps1` to skip the local A3 GPU step. After the cloud run, `a3_decomp_fair.py --part sae` runs locally: every row is already present, so it only writes the sanity block. Then `a4_summarize.py` runs.

**Note.** The A3 SAE rows run on an L4. The A2 rows ran on the local RTX 3050 Ti. GPU arithmetic differs slightly, so the run-config row is the check: it must reproduce the Phase 1 numbers (R1 0.042, area 0.007) within seed tolerance.
