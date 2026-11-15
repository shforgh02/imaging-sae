# Prompt for the executing session (Opus 5.5, xhigh effort), version 2

Version 2, written after the Fable 5.2 review of 2026-11-15. Paste everything below the line into a fresh session (model Opus 5.5, effort xhigh, working folder `D:\Shayan`). The block "The lead's OK" is the approval: change it before pasting if you do not agree with a default.

---

You continue a research project as its executing scientist. Repository: `D:\Shayan`, git branch `prostate-mri-plan` (pushed to GitHub). The project is a feature-level audit of the lung cancer screening model Sybil on public NLST data ("Lung L2"). The aim is the highest-impact paper the data can honestly support.

**Your job:** execute `docs/PLAN_L2_NEXT_v1.md`, steps P1 to P5, in order. **Stop at the end of P5 (the S5 freeze) and wait for my OK.** Do not start P6.

## The lead's OK (I am the lead; this block is my approval)
- I approve the plan `docs/PLAN_L2_NEXT_v1.md` as reviewed by Fable 5.2, with all its `[Fable edit]` changes.
- I approve amendments **A3** (two simple references), **A4** (Modal account `armanfo` for S3 D2, D3, D4 and the P2 runs) and **A5** (the unattended driver runs the paid jobs).
- My answers to the three questions of `docs/REVIEW_PLAN_L2_NEXT_v1.md`:
  1. This project may use at most **$17.00** on `armanfo` in November. The `armanfo` month cap is $29.50.
  2. **Keep both cloud volumes.** Delete nothing on Modal.
  3. **Yes**, F+I uses the 5 patient measures as its primary model.
- I will keep the laptop on, plugged in and awake during P3. Tell me before P3 starts.

## Read first, in this order
1. `docs/PLAN_L2_NEXT_v1.md`: the plan. It is your task list. Every `[Fable edit]` is part of it.
2. `docs/REVIEW_PLAN_L2_NEXT_v1.md`: the review. Its table "Errors and gaps found" (F1 to F8) lists things you must handle.
3. `docs/LUNG_L2_PROTOCOL.md`: the rule book. Exact definitions and pass marks come from here (sections 7 to 14, amendments in 16a), not from the plan's short text.
4. `STATUS.md` (top part), `docs/EXECUTION_LOG.md` (from 2026-11-13), `docs/PROGRESS_REPORT_L2_2026-11-15.md`.
5. The code:
   - `imgsae/exploratory/lung_l2/` and its `cloud/` folder;
   - the guard `imgsae/exploratory/p1b_sanity/cloud/budget.py` with `ledger.json`;
   - the run plans `cloud/RUN_PLAN_S2.md` and `cloud/RUN_PLAN_S3_D1.md`.

## Step 0: before any work (free)
1. Check that git is clean and equal to `origin/prostate-mri-plan`. One known exception: `ledger.json` has an uncommitted 6-line `checks` entry from a read-only status call. Keep it, and commit it with your first ledger change.
2. Record my OK:
   - add A3, A4 and A5 to protocol section 16a, with today's date and the three answers above;
   - correct the protocol's status line (it still says "DRAFT", but it was approved on 2026-11-13);
   - add a log entry.
3. Commit and push. Report to me in three lines.

## Step P1: the guard knows two accounts (free, code only; no Modal job)
Do every item of plan section "P1", including its `[Fable edit]` items. In short:
1. **`ledger.json`:**
   - back it up first, then change it through code;
   - add `accounts` (`shforghani2002` cap 29.0, `armanfo` cap 29.5) and `armanfo_project_limit_usd` 17.0;
   - give every run a `profile` (old runs = `shforghani2002`).
2. **`budget.py`:**
   - month usage, open worst cases and the cap are taken per account;
   - a fourth test: this project's runs on `armanfo` (worst case for open runs) ≤ $17.00;
   - the task and project tests still sum over all accounts;
   - an unknown profile is refused;
   - `save` is atomic (temporary file, then replace);
   - `status` gets a no-log mode.
3. **`launch.py`, `l2_sybil_modal.py` (local entry point), `collect.py`, `drive_runs.py`, `drive_plan.py`, `reconcile_billing.py`:**
   - take `--profile`, store it in the run record, and pass it to every Modal call. Use the CLI's own `--profile` option where it exists; otherwise set `MODAL_PROFILE` for that one subprocess.
   - **Never run `modal profile activate`.**
4. **`drive_runs.py` and `drive_plan.py`:**
   - `precheck` uses the account's cap;
   - `lag_extra` uses only that account's runs;
   - the copy destination depends on the account (`D:\Shayan\imgsae_data\lung_l2_vol_armanfo` for `armanfo`);
   - the driver refuses to start if its environment's profile differs from `--profile`.
5. **The app check for `armanfo`:**
   - Read `modal app list --json --profile armanfo` once (free, read only). Write the field names into the code and the log.
   - Rule: no other app with running containers.
     - If there is one: wait 30 minutes and look again.
     - After 2 hours: stop.
6. **Tests:**
   - a unit test of `budget.py` on a copy of the ledger: per-account limits, the $17 limit, a refusal at the cap, open runs counted on the right account;
   - `budget.py status` for each profile in no-log mode: `armanfo` should show about $1.62 used and cap $29.50; `shforghani2002` about $28.17 and cap $29;
   - a dry run of the driver for `armanfo`.
7. **Gate:** all tests pass, and no Modal job has run. Commit, push, log, and report to me in a few lines.

## Step P2: smoke and identity on `armanfo` (≈ $0.40 worst case)
1. List the `armanfo` volumes (read only). Write their names in the log. Touch none of them.
2. **Smoke step** on `armanfo`, through the guard. **Pass marks:**
   - the demo case is exact (within 0.005; expected 0.0);
   - 3 of 3 dev volumes equal Sybil's own;
   - the checkpoint hashes and the head-weight hash equal the main account's record (`results/runs/smoke.json`; head weights `ba2d6d85…009bac`).
3. **Identity run:** `--step run --tier D1 --lo 0 --hi 20 --nshard 1 --root xacct --zfix-max 0.65` on `armanfo`.
   - Copy the result to `D:\Shayan\imgsae_data\lung_l2_vol_armanfo\`.
   - Compare with the saved D1 files: calibrated probabilities within 1e-4 and `h` within 1e-4.
   - Also compare the 3 smoke series that the smoke step wrote into root `dev`.
4. Collect and close the runs. Write `results/p2_identity.json`.
5. **Gate:** all pass. If anything fails, **stop and report**; D2 to D4 then do not run on `armanfo`. Commit, push, log, report.

## Step P3: D2, D3 and D4 on `armanfo` (≈ $14.50; about 6 hours, unattended)
1. Write `cloud/RUN_PLAN_S3_REST.md` and a wrapper `cloud/run_s3rest.cmd`. The wrapper sets the profile itself and runs:
   `drive_plan.py --profile armanfo --tag arm --plan D2:0:2442,D3:0:2410,D4:0:500 --zfix-max 0.65 --root dev`
2. **Tell me that P3 is about to start,** so that I keep the laptop awake.
3. **Start the wrapper** as a one-time Windows task that starts at once (as done for D1 with `run_d1b.cmd`), so that your usage limit cannot stop it. If the permission system blocks this, give me the exact command and wait.
4. **While the driver runs:** use only the no-log status mode, and do not run `reconcile_billing.py`. Use this time for step P4a.
5. **When the driver has finished, read its log and state file.** If it stopped early, find the reason and report before any restart.
6. **Merge** `lung_l2_vol_armanfo\l2\dev` into `lung_l2_vol\l2\dev` with a script that never overwrites.
   - New files must be D2, D3 or D4 rows of the manifest, or their z-fix files.
   - A file that already exists is compared and skipped if equal.
   - Any other case stops the merge.
7. **Checks:**
   - failures < 5% per tier;
   - G2b and G2c on every new file;
   - file counts = manifest rows minus logged failures.
   - Write `results/s3_checks_all.json`.
8. **Reconcile the `armanfo` billing** at least 70 minutes after the last run closed.
9. **Delete no cloud volume.**
10. Commit, push, log, and update `STATUS.md`. Report to me: files per tier, failures, cost on each account, task and project totals.

## Step P4a: the S4 scripts (free; start while P3 runs)
1. **Write the missing scripts** with the exact definitions of protocol sections 9.1 to 9.8:
   - `s4_scores.py`: check P1, hazard gating shares, dev AUROC of Sybil and F;
   - `s4_q1b_u.py`, `s4_q1c.py`, `s4_q2.py`, `s4_u1a.py`, `s4_u2.py`, `s4_u3.py`, `s4_u4.py`;
   - `s4_refs.py`: A3, with R-size; F+I with 5 measures; the test "does Sybil add to F+I"; the 7-measure run; the "lung not cut" run; F+I by maker;
   - `s4_gate.py`: the 9.8 table. It also checks that no S4 script reads `lung_l1/results/scores.csv` or any test file.
2. **Test each script** on synthetic data with a known answer, then on the pilot. Pilot numbers are code tests only: do not report them and do not use them to choose anything.
3. **Commit and push all S4 scripts before step P4b.** Write the commit hash in the log as "S4 analysis code fixed".

## Step P4b: S4 on all dev data (free, on the PC)
1. **`l2_data.py` for dev.** Check the assemble report: 7,336 exams, the outcome counts of `results/s0_dev_counts.json`, and the non-missing share of every I and T variable. An empty column is a stop.
2. **Run in this order:**
   1. `s4_scores.py`;
   2. `s4_q1a.py`;
   3. `s4_decomp.py`: all six arms with K = 64, then K = 128 as a check; `--device cuda` for the sparse autoencoder;
   4. `s4_q1b_u.py`;
   5. `s4_q1c.py`;
   6. `s4_q1d.py`;
   7. `s4_q2.py`;
   8. `s4_u1a.py`, `s4_u2.py`, `s4_u3.py`, `s4_u4.py`;
   9. `s4_refs.py`;
   10. `s4_gate.py`.
3. **Logging:** any change to a script after its full-dev result is seen goes into the log, with the reason.
4. **Write `imgsae/exploratory/lung_l2/RESULTS_S4_dev.md`:**
   - every number with its exams, participants and cancers;
   - failed marks written as failed;
   - the simple arms, R-size, F, F+I and the probe next to the sparse autoencoder;
   - the note that Sybil's dev accuracy is mildly optimistic (protocol C6);
   - both participant counts (2,493 in the split, 2,492 with a usable exam).
5. **Gate 9.8:**
   - If no candidate holds: **stop**. Write the plain report and the fallback proposal, and wait for me.
   - If something holds: commit, push, report to me in a few lines, and go on to P5.

## Step P5: the S5 freeze (free). Then stop.
1. **`imgsae/exploratory/lung_l2/HYPOTHESES_L2.md`:** at most 5 hypotheses, by the rules of protocol section 10. For each one:
   - statistic, population, direction, margin, null value, test;
   - the dev evidence, with file names and counts;
   - an honest chance estimate, with your reasons.
   - At most one "partly seen" hypothesis, labelled.
2. **`frozen_thresholds_L2.json`** and the frozen dictionaries, with their hashes.
3. **`s6_frozen_analysis.py`:** it reads only frozen files and refits nothing. Test it end to end on dev ("dev as if test").
4. **The S6 run plan inside the S5 file:**
   - order T1 → T2 → T5 and T4 (only those a frozen hypothesis uses) → T3;
   - a cost projection from the billed S3 cost per series;
   - if the projection is above the task's remaining budget minus $1.00, say so and give me the options.
5. **Hashes and brief:** the SHA-256 list in `HYPOTHESES_L2.md`; update `docs/REVIEWER_BRIEF_L2.md` if needed.
6. **Commit and push.** Do not build a test manifest and do not touch test data.
7. **Stop.** Show me the hypothesis file, the dev evidence and the chance estimates, and tell me what to send to the external reviewer. Wait for my OK.

## Rules for the whole run
- **Test data stay closed until I approve the S5 file.** No test activation is extracted, and no new outcome analysis of the existing L1 test scores is made, before that.
- **Fair comparisons:**
  - Every decomposition arm gets the same number of features and the same selection rule.
  - Always report the simple baselines and the raw-probe ceiling next to the sparse autoencoder.
- **Honest results:**
  - A failed gate is reported as failed.
  - A negative result is written as clearly as a positive one.
  - No claim goes beyond what its test showed.
  - Say how many patients and cancers each number rests on.
- **Paid runs:**
  - Every launch goes through the guard, and usage is checked before every launch.
  - Limits: task `lung_l2_audit` ≤ $45; project ≤ $72; `shforghani2002` ≤ $29 a month; `armanfo` ≤ $29.50 a month, and this project ≤ $17 on it.
  - T4 or L4, container timeout ≤ 60 minutes, at most 4 containers at once over both accounts.
  - The `reserve` and the profile `forghanishayan` are not used.
- **Never touch:** the volumes and apps `vs-workspace-data`, `vs-radiomics-vol`, `picai-dataset-vol`, `lupi-data`, and any app or volume on `armanfo` other than this project's `imgsae-lung-l2` and `imgsae-nlst-l2`.
- **Save everything as it finishes:** detached launches, one saved unit per series, a killed client must lose nothing.
- **Stop and ask me when:**
  - the guard refuses a launch, or a check or gate fails;
  - failures are above 5%;
  - a step's cost goes more than 10% over its allocation (S3: $22.00);
  - something would touch another app, volume or account;
  - anything is unclear about test data.
- **Environment:**
  - PowerShell, not Bash.
  - Scripts run with `D:\Shayan\imgsae\.venv\Scripts\python.exe`.
  - `budget.py` and the Modal tools run with `C:\Users\Arman\miniconda3\python.exe` (Modal CLI: `C:\Users\Arman\miniconda3\Scripts\modal.exe`).
  - Do not install packages without telling me.
- **Records:**
  - Every decision, deviation and result goes into `docs/EXECUTION_LOG.md`, and the current state into `STATUS.md`.
  - **Commit and push after each step.** Keep `New report .txt` and `imgsae/exploratory/ucla_audit/` out of git.
- **Privacy:** do not put my name, email or project name into requests to outside services.
- **Subagents:** do not spawn them unless a step really needs it.

## How to write to me
English is not my first language. Use short, plain sentences. Lead with the result, then the numbers, then what you need from me. Report at the end of each step in a few lines.
