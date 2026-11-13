You are taking over my imaging project in `D:\Shayan` (git branch `prostate-mri-plan`). The project was paused and now restarts with one piece of work: a feature-level audit of the lung cancer screening model Sybil on the public NLST trial. My goal is the highest-impact paper that the data can honestly support. I am the lead; you are the main analyst.

## Read first, in this order, before you do anything
1. `STATUS.md`
2. `docs/PLAN_SYBIL_AUDIT_v1.md` (the plan you execute)
3. `imgsae/exploratory/lung_l1/RESULTS_L1.md` and `docs/LUNG_L1_PROTOCOL.md`
4. `imgsae/exploratory/lung_l0/RESULTS_L0.md`
5. `imgsae/exploratory/lung_l1/posthoc/` (scripts and their saved outputs)
6. `imgsae/exploratory/lung_l1/cloud/` (the working Sybil cloud job), and `imgsae/exploratory/p1b_sanity/cloud/budget.py` with `ledger.json`
7. The last two entries of `docs/EXECUTION_LOG.md` (2026-11-12 "lung L1 run and result" and 2026-11-13)

## What I want from you
**Part A (free, do it now).** Step S0 of the plan:
- Read the paper "Auditing Sybil" (arXiv 2602.02560) in full, Sybil's own paper (Mikhael et al., JCO 2023) and Sybil's dataset code. Repeat the literature search for any work that explains Sybil or another lung screening model with real outcomes. Check whether a second low-dose CT dataset with cancer outcomes is open to an individual without an institutional agreement.
- Check the plan itself. Do not trust it blindly. Confirm the model structure at the pinned commit, the counts, and the cost figures from the files. If something in the plan is wrong or can be made stronger, say so and fix it in the protocol.
- Build and test the series-selection rule for dev exams (plan section 4), using scan metadata only.
- Write `docs/LUNG_L2_PROTOCOL.md`: questions, data roles, what is saved, every threshold as a number, the validity pass marks, the analysis for each question, the gates, the budget rule, the list of what is not allowed. Fix everything before any activation exists.
- Then stop. Give me the file path, a short summary, the main risks you see, and anything you changed from the plan. Wait for my OK.

**Part B (after my OK).** Steps S1 to S4: dev manifest, pilot, dev extraction, analysis on the PC. Go on without asking me again unless a gate fails or the budget blocks you. Report at the end of each step in a few lines.

**Part C.** Step S5: freeze at most five hypotheses in a hashed file. Stop and show me the file, the dev evidence for each hypothesis, and your honest estimate of the chance each one is confirmed. Wait for my OK.

**Part D (after my OK).** Step S6: test extraction and the frozen analysis, once. Then `RESULTS_L2.md` and a manuscript outline with the journal you would aim for and why.

## How to work
- **Paid cloud runs are executed by a lower-cost subagent (Sonnet) under the written protocol, not by you.** You plan the run, give the agent the protocol, and check its report against the files (hashes, row counts, ledger, volume list) before you use any result.
- **Test data stay closed until the freeze.** No test activation is extracted, and no new outcome analysis of the existing test scores is made, before Part C is approved.
- **Fair comparisons.** Every decomposition arm gets the same number of features and the same selection rule. Always report the simple baselines and the raw-probe ceiling next to the sparse autoencoder.
- **Honest results.** A failed gate is reported as failed. A negative result is written as clearly as a positive one. No claim goes beyond what its test showed. Say how many patients and cancers each number rests on.
- **Save everything as it finishes.** Detached cloud launches, one saved unit per series, results copied to the PC, then the cloud volume deleted. A killed client must lose nothing.
- **Environment.** Use PowerShell, not Bash. Scripts run with `D:\Shayan\imgsae\.venv\Scripts\python.exe`; `budget.py` runs with `C:\Users\Arman\miniconda3\python.exe`. Do not install packages without telling me.
- **Records.** Every decision, deviation and result goes into `docs/EXECUTION_LOG.md`; the current state into `STATUS.md`. Do not commit or push to git unless I ask.
- **Privacy.** Do not put my name, email or project name into requests to outside services.
- **Write to me in short, plain sentences.** English is not my first language. Lead with the result, then the numbers, then what you need from me.

## Budget (my approvals; follow them exactly)
- New ledger task `lung_l2_audit`: **$45.00 in total** for steps S2 to S6, spread over months. Step S7 needs a new approval from me.
- The monthly stop of **$29 per account stays**. Check usage before every launch. Every launch goes through the guard.
- The guard's all-time project check has only $3.61 left and would block this work. I approve one change: add a separate `project_cap_usd` of **72.00** to `ledger.json` and make the project check in `budget.py` use it. Leave the monthly check and `cap_usd` = 29 as they are. Show me the diff in your first report after Part A.
- **November 2026:** only account `shforghani2002`, and only what the monthly check allows (about $8 to $9 is left). That is the pilot and the first part of the dev baseline tier, in a fixed random order. The rest waits for 1 December.
- The second Modal account and the `reserve` are not used unless I say so. My other volumes and apps (`vs-workspace-data`, `vs-radiomics-vol`, `picai-dataset-vol`, `lupi-data`) are never touched.
- GPU T4 or L4, container timeout at most 60 minutes, at most 4 containers at once.

## What success looks like
A paper that says, on patients the model never saw: what Sybil's score is made of, how much of it is technical, why it raises false alarms and misses cancers, and whether any of that can be used, with each claim confirmed once on the test split under a frozen analysis. If the dev step finds nothing that holds, stop before paying for the test split and tell me plainly; the paired result in `RESULTS_L1.md` is the fallback paper.

Start with Part A.
