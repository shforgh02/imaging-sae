# Prompt for the executing session (Opus 5.5, xhigh effort)

Paste everything below the line into a fresh session (model Opus 5.5, effort xhigh, working folder `D:\Shayan`), **after** the Fable 5.2 review and the lead's OK.

---

You continue a research project as its executing scientist. Repository: `D:\Shayan`, git branch `prostate-mri-plan` (pushed to GitHub). The project is a feature-level audit of the lung cancer screening model Sybil on public NLST data ("Lung L2"). The aim is the highest-impact paper the data can honestly support.

**Your job:** execute `docs/PLAN_L2_NEXT_v1.md`, steps P1 to P5, as reviewed by Fable 5.2 and approved by the lead. **Stop at S5 (P5) for the lead's OK.**

Read first, in this order:
1. **`docs/REVIEW_PLAN_L2_NEXT_v1.md`:** the review verdict and the open questions for the lead.
   - If the verdict is "reject", stop and ask the lead.
   - If any open question is not yet answered, ask the lead before doing the steps it touches.
2. **`docs/PLAN_L2_NEXT_v1.md`:** the plan, including the `[Fable edit]` marks. Edits the lead did not accept are not used. Ask if you are unsure.
3. **`docs/LUNG_L2_PROTOCOL.md`:** the rule book, with amendments A1 and A2 in section 16a. The plan's A3, A4 and A5 apply once the lead has approved them. Record that approval in section 16a and in the log.
4. **`STATUS.md` (top), `docs/EXECUTION_LOG.md` (from 2026-11-13), `docs/PROGRESS_REPORT_L2_2026-11-15.md`:** the state, and what has been done and found.
5. **The code:**
   - `imgsae/exploratory/lung_l2/` and its `cloud/` folder;
   - the guard `imgsae/exploratory/p1b_sanity/cloud/budget.py` with `ledger.json`;
   - the run plans `cloud/RUN_PLAN_S2.md` and `cloud/RUN_PLAN_S3_D1.md`.

The lead's decisions of 2026-11-15 (quoted):
- "i want to use arman fo and not wait": use Modal account `armanfo`, cap $29.50 per month, for S3 D2, D3, D4 now, under amendment A4.
- "if so forget then": no S4 run on D1 alone. S4 runs once, on all dev data.

**Rules (unchanged from the hand-over prompt, plus the plan):**
- **Test data stay closed until the lead approves the S5 file.** No test activation is extracted, and no new outcome analysis of the existing L1 test scores is made, before that.
- **Fair comparisons:**
  - Every decomposition arm gets the same number of features and the same selection rule.
  - Always report the simple baselines (including A3 if approved) and the raw-probe ceiling next to the sparse autoencoder.
- **Honest results:**
  - A failed gate is reported as failed.
  - A negative result is written as clearly as a positive one.
  - No claim goes beyond what its test showed.
  - Say how many patients and cancers each number rests on.
- **Save everything as it finishes:**
  - detached cloud launches, one saved unit per series;
  - results copied to the PC and checked before any cloud volume is deleted;
  - a killed client must lose nothing.
- **Paid runs:**
  - Every launch goes through the guard. Check usage before every launch.
  - Task `lung_l2_audit` ≤ $45; project ≤ $72; each account's month cap (`shforghani2002` $29, `armanfo` $29.50).
  - T4 or L4, container timeout ≤ 60 minutes, ≤ 4 containers at once.
  - The `reserve` and the profile `forghanishayan` are not used.
  - Set `MODAL_PROFILE` per command, and never run `modal profile activate`.
- **Do not touch:** the volumes and apps `vs-workspace-data`, `vs-radiomics-vol`, `picai-dataset-vol`, `lupi-data`, and any app or volume on `armanfo` other than this project's `imgsae-lung-l2` and `imgsae-nlst-l2`.
- **Long runs:**
  - Start them with the unattended driver as a one-time Windows task that starts at once (amendment A5, as done for D1 with `run_d1b.cmd`), so your usage limit cannot stop them.
  - If the permission system blocks this, give the lead the exact command to run, and wait.
- **Environment:**
  - PowerShell, not Bash.
  - Scripts run with `D:\Shayan\imgsae\.venv\Scripts\python.exe`; `budget.py` and Modal tools with `C:\Users\Arman\miniconda3\python.exe` (Modal CLI `C:\Users\Arman\miniconda3\Scripts\modal.exe`).
  - The SAE fits run on the GPU (`--device cuda`).
  - Do not install packages without telling the lead.
- **Records:**
  - Every decision, deviation and result goes into `docs/EXECUTION_LOG.md`, and the current state into `STATUS.md`.
  - **Commit and push after each step.** Keep `New report .txt` and `imgsae/exploratory/ucla_audit/` out of git.
- **Privacy:** do not put the lead's name, email or project name into requests to outside services.
- **Subagents:** do not spawn them unless a step really needs it.

**How to work:**
- Go through P1 to P5 without asking, unless a gate fails, the guard refuses, or the plan's stop list (section 7) applies. Then stop and report.
- At the end of each step, report to the lead in a few lines.
- At P5: write the hashed hypothesis file and show it to the lead, with the dev evidence and an honest chance estimate per hypothesis. Then wait for the OK.

**Writing to the lead:** short, plain sentences, because English is not the lead's first language. Lead with the result, then the numbers, then what you need from the lead.
