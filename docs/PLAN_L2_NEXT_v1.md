# Lung L2: plan from 15 November 2026 to the paper (v1)

**Status:** DRAFT, written 2026-11-15. To be reviewed by Fable 5.2, then approved by the lead. Nothing in this plan that spends money or changes the protocol is done before the lead's OK.
**Binding rules:** `docs/LUNG_L2_PROTOCOL.md` (with amendments A1 and A2, section 16a) stays the rule book. This plan only (1) puts the remaining steps in order with their gates and outputs, and (2) proposes three amendments (A3, A4, A5) that need the lead's OK.
**Who does what:**
- Fable 5.2 reviews this plan.
- A fresh Opus 5.5 session (xhigh effort) executes it, up to the S5 stop.
- The lead decides at the marked points.
- The external reviewer checks the hypothesis file at S5 (`docs/REVIEWER_BRIEF_L2.md`).

## 1. Where we are (15 Nov)
Details: `docs/PROGRESS_REPORT_L2_2026-11-15.md`, `STATUS.md`, `docs/EXECUTION_LOG.md`.

| Step | State |
|---|---|
| S0 protocol, series rule (98.7% match), literature | done, approved |
| S1 dev manifest (7,336 exams, 2,492 participants; D1 2,484, D2 2,442, D3 2,410, D4 500) | done |
| S2 pilot (300) | done; G2e and G2f amended (A1, A2) with the lead's OK |
| S3 D1 | **done**: 2,484 main + 430 z-fix files, 0 failures, all pass G2b/G2c (`results/s3_d1_checks.json`) |
| S3 D2, D3, D4 (+ their z-fix rows) | **not run**; ≈ $14.50 |
| S4 code | written and tested: `l2_data.py`, `s4_core.py` (+ test), `s4_q1a.py`, `s4_decomp.py` (arms, V1–V4, naming, Q1b shares), `s4_q1d.py`. **Missing:** Q1b "does U add to F", Q1c, Q2, U1a, U2, U3, U4, gate summary |
| S5 to S8 | not started |

Money (ledger after billing reconciliation):
- Task `lung_l2_audit`: $7.67 of $45.
- Project: $33.06 of $72.
- Account `shforghani2002`: November $28.17 of $29 (used up).
- Account `armanfo`: November $1.62 of $29.50. This was all its own other apps; nothing of this project.

## 2. The lead's decisions of 15 Nov (quoted)
1. "i want to use arman fo and not wait". Use account `armanfo` (cap $29.50 per month) for the rest of S3 now, instead of waiting for 1 December. The formal rule is amendment A4.
2. "if so forget then": no S4 dry run on D1 alone. S4 runs once, on all dev data.
3. "i want to call on fable 5.2 … then run its plan by another opus 5.5 xhigh": this plan is reviewed by Fable 5.2, then executed in a fresh session.

## 3. Proposed amendments (need the lead's OK; logged as deviations from the protocol)
### A3: two simple references, added before S4 (no dev outcome has been looked at yet)
- **R-size:** the largest nodule's long diameter (`max_dia`, 0 if no nodule), with no fitting.
  - AUROC for `y1` on all screens and `y6` on baseline screens, on dev in S4 and on test in S6.
  - It was already computed on test in L0, so it counts as "partly seen": a reference only, never a hypothesis.
- **F+I:** the form plus simple image measures.
  - **Inputs:**
    - F's logit (F1 for `y1`, F6 for `y6`; frozen, fitted on train);
    - the 7 image measures of `l2_data.MEASURES` (lung volume, emphysema % LAA-950, lung 15th-percentile HU, lung mean HU, body area, air noise, lung z-extent), with rule A2 (all missing if lung volume < 1,500 ml);
    - one indicator "any measure missing". Medians are imputed inside each training fold.
  - **Model:** `nlst_l0.logit_model()` (standardise + logistic, C = 0.3).
  - **Dev:** participant-grouped 5-fold CV (seed 0), AUROC with a participant bootstrap (2,000 draws).
  - **S6:** one fit on all dev, its parameters hashed and frozen with the S5 files, then applied to test unchanged.
  - **Why F's logit and not its 43 inputs:** F keeps its large train fit (29,752 screens). Dev fits only about 9 coefficients against 88 one-year cancers.
  - **Why no technical factors:** they should carry no cancer information. If they do, the model would learn site or scanner confounding. Technical factors are studied in Q1a and U1a instead.
  - **Question it answers:** is what Sybil adds beyond the form explained by simple, measurable image facts such as emphysema and body size?
  - **Where it is reported:** next to Sybil, F, C (Sybil + F, U3) and the probe (U4), and in the U3 table (false alarms per 1,000 at the radiologists' sensitivity). It is a reference. It becomes a hypothesis only by the normal rules (section 9.8 and section 10).

### A4: the second Modal account for the rest of S3
- **Scope:** account `armanfo`, for S3 tiers D2, D3, D4 (with their z-fix rows) and the small smoke and identity runs of P2. Nothing else.
- **S6:** stays on `shforghani2002` in December, which starts with a full $29, unless the lead decides otherwise.
- **Unchanged limits:** task $45; project $72; T4 (or L4); timeout ≤ 60 min; ≤ 4 containers at once across both accounts; detached spawn; one saved unit per series.
- **Per-account month check:** `armanfo` usage (its whole workspace, from Modal's billing) + open worst cases on `armanfo` + this launch's worst case ≤ $29.50.
- **Protection for the lead's other work on `armanfo`:**
  - Before each launch, `modal app list` on `armanfo` must show no running app other than `imgsae-lung-l2`. Otherwise the cost of the other app is not yet in the billing.
  - If one is running: wait 30 minutes and check again. After 2 hours, stop and report.
  - No other app or volume on `armanfo` is touched or deleted.
- **Identity across accounts (gate of P2):** 20 D1 series re-run on `armanfo` must equal the saved D1 files: calibrated probabilities within 1e-4 and `h` within 1e-4 (L1 and S2 gave 0.0). The checkpoint and head-weight hashes must equal those of the main account.

### A5: the executor of paid runs
- **What changes:** the hand-over rule "paid runs by a lower-cost subagent" is replaced by the unattended driver (`cloud/drive_runs.py`, `cloud/drive_plan.py`). The driver is started as a one-time Windows task, so that a usage limit of the assistant cannot stop a run.
- **How it works:** every launch still goes through the guard. The driver follows the written run plan and stops on any failure.
- **History:** this was used for D1 (logged deviation, 15 Nov). A5 makes it the rule.

**Not changed by this plan:** questions, data roles, pass marks, gates, analyses, the hypothesis rules, and the test rules. The test split stays closed until the lead approves the S5 file.

## 4. Work plan
Each step ends with a few-line report to the lead, a log entry, and a commit and push.

### P0: review and OK (free)
- Fable 5.2 reviews this plan (prompt: `docs/PROMPT_REVIEW_FABLE_L2.md`). It writes `docs/REVIEW_PLAN_L2_NEXT_v1.md` and may edit this file, marking each edit.
- The lead approves A3, A4, A5 and the plan as reviewed.
- **Stop:** the lead's OK. Without it, the executor does nothing that spends money or changes the protocol.

### P1: the guard knows two accounts (free, code)
1. **`ledger.json`:**
   - add `accounts: {"shforghani2002": {"cap_usd": 29.0}, "armanfo": {"cap_usd": 29.5}}`;
   - every run gets `profile`; old runs = `shforghani2002`.
   - Edit through code, with a backup copy first.
2. **`budget.py`:**
   - `month_used(profile)` runs `modal billing summary` with `MODAL_PROFILE=<profile>` set for that one command.
   - `status(profile)` and `check(task, worst, profile)`: the month test uses that account's usage, that account's open worst cases and that account's cap.
   - The task and project tests sum over all accounts (unchanged).
   - A profile that is not in `accounts` is refused.
3. **`launch.py`, the local entry point of `l2_sybil_modal.py`, `collect.py`, `drive_runs.py`, `drive_plan.py`, `reconcile_billing.py`:**
   - take `--profile`, record it in the run, and set `MODAL_PROFILE` in every Modal subprocess.
   - **Never** `modal profile activate`.
   - `reconcile_billing.py` reconciles per account.
4. **`drive_runs.py`:** adds the A4 app-list check before each launch on `armanfo`.
5. **Tests:**
   - a unit test of `budget.py` on a copy of the ledger with both accounts: limits per account, open runs counted on the right account, a refusal at the cap;
   - `budget.py status --profile armanfo` shows $1.62 used and cap $29.50;
   - `--profile shforghani2002` shows $28.17 and cap $29;
   - a dry run of the driver on `armanfo` prints its prechecks.
6. **Gate:** all tests pass; no Modal job has run.

### P2: smoke and identity on `armanfo` (≈ $0.40 worst case)
1. List the `armanfo` volumes (read only) and note them in the log. The app creates its own `imgsae-nlst-l2` there.
2. **Smoke step:**
   - G2a: the demo case exact;
   - 3 dev volumes equal Sybil's own;
   - checkpoint and head-weight SHA-256 equal to the main account's smoke record.
3. **Identity:** D1 rows 0–20 under root `xacct`, compared on the PC with the saved D1 files (rule A4).
4. **Gate:** both pass. If one fails, stop and report. D2 to D4 do not run on `armanfo`, and they wait for December on the main account.

### P3: D2, D3, D4 on `armanfo` (≈ $14.50; unattended, about 6 hours)
1. **Run plan file:** `cloud/RUN_PLAN_S3_REST.md` (as `RUN_PLAN_S3_D1.md`, with the profile).
   - Driver: `drive_plan.py --profile armanfo --tag arm --plan D2:0:2442,D3:0:2410,D4:0:500 --zfix-max 0.65 --root dev`.
   - Started as a one-time Windows task that starts at once. If the permission system blocks it, the lead runs the prepared command.
   - Laptop on, plugged in and awake for the run.
2. **The driver's rules (as D1):**
   - nshard 4 → 3 → 2 → 1, as the month allows;
   - stop on a guard refusal, a collect error, errors > 5%, or 80 minutes without a result;
   - the billing lag rule;
   - a plan step starts only if the one before it finished cleanly.
3. **PC copy:**
   - Copy into a separate folder `D:\Shayan\imgsae_data\lung_l2_vol_armanfo\l2\`.
   - Then a merge script copies the files into the main PC copy. It refuses any overwrite and checks counts and hashes.
   - The `xacct` files stay separate.
4. **Checks on every new file (S3 gate):**
   - failures < 5% per tier;
   - G2b and G2c on every saved series;
   - file count = manifest rows minus logged failures.
   - Output: `results/s3_checks_all.json`.
5. **Afterwards:**
   - Reconcile `armanfo` billing (after 70 minutes).
   - Ledger and log.
   - Delete the dev volumes on both accounts only after the PC copy is verified (protocol section 12). Delete only `imgsae-nlst-l2`, nothing else.
6. **Expected:** `armanfo` about $16.50 of $29.50; task about $22.60 of $45; S3 total about $20.60 of its $22.00 allocation (stop rule: +10%).

### P4: S4 on all dev data (free, on the PC; about 1 to 2 weeks)
1. `l2_data.py`: assemble the dev table (7,336 main exams, z-fix and pair variants) and the arrays file. Rule A2 applied.
2. **Scripts already there:**
   - `s4_q1a.py`: Shapley R² by group, plus U;
   - `s4_decomp.py`: 6 arms × K 64 (and K 128 as a check), SAE on the GPU (`--device cuda`), V1–V4, families, naming, Q1b shares, arms saved;
   - `s4_q1d.py`: kernel pairs D4 and z-fix D5.
3. **Scripts to write.** Each is tested first on synthetic data and on the pilot, with exact definitions from protocol section 9.7:
   - `s4_q1b_u.py`: does U add to F (ΔAUROC, likelihood-ratio test);
   - `s4_q1c.py`: stable shares, T0 against T1;
   - `s4_q2.py`: false-alarm classes and misses, SMDs, FDR, counts by location, histology, stage and size;
   - `s4_u1a.py`: technical removal, with Sybil's head and calibrator;
   - `s4_u2.py`: reliability flag, R-fixed against R-learned;
   - `s4_u3.py`: Sybil + F at the radiologists' sensitivity;
   - `s4_u4.py`: probe and family-activation references;
   - `s4_refs.py`: A3, R-size and F+I;
   - `s4_gate.py`: section 9.8, one table of all candidates (direction, 95% interval, sign in both dev halves).
4. **Report:** `lung_l2/RESULTS_S4_dev.md`, with every number giving its exams, participants and cancers. Next to the SAE, always the simple arms, R-size, F, F+I and the probe ceiling.
5. **Gate 9.8:**
   - If no candidate holds, **stop**. There is no test spending. Report plainly. The fallback paper is L1 plus the technical findings.
   - If something holds, go on to P5.

### P5: S5 freeze (free). **Stop for the lead's OK.**
1. **`lung_l2/HYPOTHESES_L2.md`:** at most 5 hypotheses. Each has its statistic, population, direction, margin, null value and test; its dev evidence; and an honest chance estimate. Holm correction; at most one "partly seen" hypothesis, labelled.
2. **`lung_l2/frozen_thresholds_L2.json`:** τ90, τ_rad, rule cut-offs, ridge settings, family definitions, F+I parameters. The frozen dictionaries (arms) are saved with their hashes.
3. **`lung_l2/s6_frozen_analysis.py`:**
   - It reads only frozen files, refits nothing and runs once.
   - Tested end to end on dev ("dev as if test"), so that S6 cannot fail on code.
4. **SHA-256 list** in `HYPOTHESES_L2.md`. `docs/REVIEWER_BRIEF_L2.md` is updated if needed.
5. **Stop.** The lead sends the files to the external reviewer. Their note and the lead's OK are logged.

### P6: S6 test (≈ $15.50 to $18.40; main account, December)
1. **Extraction:**
   - T1 baseline 2,279, T2 year 1 2,243, T3 year 2 2,193, root `test`;
   - T4 kernel pairs and T5 z-fix only if a frozen hypothesis uses them;
   - run by the driver under the guard.
2. **Checks:**
   - G2a;
   - failures < 5% per tier;
   - G2b and G2c on every file;
   - identity: re-extracted calibrated scores equal the L1 scores within 1e-4 for ≥ 99% of the 5,412 L1 series.
3. **The frozen analysis, once.** The results file is committed before any reading or comment. Anything outside the frozen file is labelled exploratory.

### P7: S7 (optional; needs a new approval and a higher project cap)

### P8: S8 results and manuscript outline (free)
- `lung_l2/RESULTS_L2.md`, figures, a manuscript outline, and a target journal with the reasons.
- Every failed gate and every negative result is reported as clearly as the positive ones.
- Possible shapes of the paper, decided by the results, not now:
  - **(a)** valid features plus a confirmed hypothesis: a feature-level audit of Sybil against outcomes, the form and technical factors;
  - **(b)** only the technical findings confirmed (z-stretch, kernels): a technical audit;
  - **(c)** nothing confirmed: the L1 paired result plus a descriptive technical audit.

## 5. Money
| | Now | After P2 + P3 | After P6 | Limit |
|---|---|---|---|---|
| Task `lung_l2_audit` | 7.67 | ≈ 22.60 | ≈ 38 to 41 | 45.00 |
| Project | 33.06 | ≈ 48.00 | ≈ 64 to 67 | 72.00 |
| `armanfo`, November | 1.62 | ≈ 16.50 | — | 29.50 |
| `shforghani2002`, December | — | — | ≈ 15.50 to 18.40 | 29.00 |

## 6. Timeline (estimates)
| When | Step |
|---|---|
| 15 to 16 Nov | P0 review and OK |
| 16 to 17 Nov | P1 code and tests; P2 smoke and identity |
| 17 to 18 Nov | P3 runs (about 6 hours unattended), copy and checks |
| 18 Nov to early Dec | P4 S4 |
| Early Dec | P5 freeze; external reviewer; the lead's OK |
| December | P6 test (main account) |
| December to January | P8 results and outline |

## 7. The executor stops and asks when
- the guard refuses a launch, or a check fails;
- failures are > 5%, or the identity check fails;
- a step's measured plus projected cost goes more than 10% over its allocation;
- anything would touch another app or volume, or another account than the one planned;
- anything is unclear about test data;
- gate 9.8 fails;
- it reaches S5, which is always a stop.

## 8. Rules that stay (from the hand-over prompt)
- **Test closed:** no test activation and no new outcome analysis of the L1 test scores before the S5 file is approved.
- **Fair comparisons:** the same number of features and the same selection rule for every arm. The simple baselines and the probe ceiling are always reported next to the SAE.
- **Honest results:** a failed gate is reported as failed; a negative result is written as clearly as a positive one; no claim goes beyond its test; every number gives its patients and cancers.
- **Saving:** detached launches, one saved unit per series, the PC copy checked before any cloud deletion, and a killed client loses nothing.
- **Environment:**
  - PowerShell, not Bash.
  - Scripts run with `D:\Shayan\imgsae\.venv\Scripts\python.exe`; `budget.py` and Modal tools with `C:\Users\Arman\miniconda3\python.exe`.
  - No package is installed without telling the lead.
- **Records:** decisions, deviations and results go into `docs/EXECUTION_LOG.md`, the state into `STATUS.md`. Commit and push after each step. `New report .txt` and `imgsae/exploratory/ucla_audit/` stay out of git.
- **Privacy:** no name, email or project name goes into requests to outside services.
- **Never touched:** the lead's volumes and apps (`vs-workspace-data`, `vs-radiomics-vol`, `picai-dataset-vol`, `lupi-data`, and the other apps on `armanfo`). The `reserve` is not used. The third profile `forghanishayan` is not used.
- **Writing to the lead:** short, plain sentences. The result first, then the numbers, then what is needed.

## 9. Risks and how they are handled
| Risk | Handling |
|---|---|
| The lead's other work on `armanfo` spends at the same time | Per-account month check, plus the app-list check before each launch |
| Wrong account used | `MODAL_PROFILE` set per command; profile stored per run; no `profile activate`; P2 check |
| Results differ between accounts | P2 identity gate (expected 0.0) |
| Modal preemption is billed twice | Per-account billing reconciliation; the guard uses max(measured, billed) |
| The assistant's usage limit | Unattended driver as a Windows task |
| The laptop sleeps during P3 | Cloud work continues and is saved; the driver stops; restart from the log |
| A merge overwrites files | Separate folder; a merge that refuses any overwrite; hash check |

## 10. Considered and not added (for the reviewer to judge)
- **Running Sybil on the train set, or fitting the SAE on train `h`:** Sybil learned these scans, so its features there are over-fitted. It would cost about $80. The protocol rules it out.
- **Attention location against the recorded cancer lobe** (the attention maps are already saved): possible only as a descriptive, exploratory addition after S4. The 25 × 16 × 16 grid and the lobe-level location are both coarse. It is not a hypothesis.
- **Retraining Sybil with the true slice spacing:** out of scope and too costly.
- **A second dataset:** the lead said not now. DLCS is restricted, and P-ELCAP is by request.
- **Telling Sybil's developers about the z-stretch:** the lead's decision. The suggestion is at submission or after the paper.

## 11. Files
- **Protocol:** `docs/LUNG_L2_PROTOCOL.md`.
- **Progress report:** `docs/PROGRESS_REPORT_L2_2026-11-15.md`.
- **Reviewer brief:** `docs/REVIEWER_BRIEF_L2.md`.
- **This plan:** `docs/PLAN_L2_NEXT_v1.md`.
- **Review prompt:** `docs/PROMPT_REVIEW_FABLE_L2.md`.
- **Execution prompt:** `docs/HANDOVER_PROMPT_L2_EXEC.md`.
- **Code:** `imgsae/exploratory/lung_l2/` (cloud jobs in `cloud/`).
- **Guard:** `imgsae/exploratory/p1b_sanity/cloud/budget.py`, `ledger.json`.
- **Data on the PC only:** `D:\Shayan\imgsae_data\lung_l2_vol\l2\`, `D:\Shayan\imgsae_data\idc_index_25.0.5\`.
