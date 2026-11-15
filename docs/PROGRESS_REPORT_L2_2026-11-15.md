# Lung L2: progress report, 15 November 2026

For the lead. The external reviewer can read it too.
All numbers come from committed files. The file paths are listed in section 11.

## 1. Summary
- We are in step **S3**, the extraction of Sybil's internal data on the dev split.
- **D1 is done.** All 2,484 baseline dev scans are saved, with 0 failures and all checks passed.
- **We are waiting for money, not for a problem.** November's Modal budget is used up ($28.17 of $29). The rest of S3 (D2, D3, D4, about $14.50) can start on **1 December**.
- **The test split is still closed.** No test data has been extracted, and no new outcome analysis has been done.
- **One decision is needed now:** how the December run starts (section 9).

## 2. The project in short
- **Model:** Sybil, a public deep-learning model. It predicts lung cancer within 1 to 6 years from one low-dose CT scan.
- **Data:** NLST, the US lung screening trial, which is public through IDC. We use Sybil's own split: dev for discovery, test for one confirmation.
- **What we already know (L1, done earlier):** on Sybil's test split, Sybil is about as accurate as a simple model of the radiologists' recorded findings (the "form").
- **What L2 asks:**
  - **Q1, what is Sybil's score made of?** How much comes from nodule findings, other findings, age and smoking, image measures, and scanner or technical factors. How much is unexplained.
  - **Q1d, technical tests:** two direct experiments on the same exam. (i) The same scan rebuilt with a soft and a sharp kernel. (ii) The slices placed at their true spacing ("z-fix", see 4.2).
  - **Q2, why is Sybil wrong?** What is different about its false alarms and its missed cancers.
  - **Q3, can its features be used?** For example, by removing technical content, adding a reliability flag, or combining Sybil with the form.
- **How we stay honest:**
  - Everything is discovered on dev first.
  - Then at most 5 hypotheses are frozen in a hashed file and checked by the external reviewer.
  - Then the lead says OK.
  - Only then is test data extracted, and the frozen analysis runs once.

## 3. The steps and where we are
| Step | What | State | Cost |
|---|---|---|---|
| S0 | Reading, literature, series rule, protocol | **Done** (13 Nov); lead approved | free |
| S1 | Dev list of scans (manifest) | **Done** (13 Nov). 7,336 exams = 99.65% of dev exams (gate 95%) | free |
| S2 | Pilot, 300 scans | **Done** (13 Nov). 2 checks failed as written; the lead accepted fixes A1 and A2 (14 Nov) | $1.96 |
| S3 | Dev extraction | **D1 done** (15 Nov): 2,484 scans + 430 z-fix versions. **D2, D3, D4 wait for 1 December** | $5.72 so far; ≈ $14.50 still to come |
| S4 | Analysis on the PC | Code partly written and tested on the pilot; full run after D2 to D4 | free |
| S5 | Freeze ≤ 5 hypotheses; reviewer check; **stop for the lead's OK** | Not started | free |
| S6 | Test extraction + the frozen analysis, run once | Not started; most likely January | ≈ $15.50 to $18.40 |
| S7 | Optional extra scans | Needs a new approval | ≈ $10 |
| S8 | Results file, figures, manuscript outline, target journal | Not started | free |

What the dev tiers are:
- **D1:** the baseline screen (T0).
- **D2:** the year-1 screen (T1), 2,442 scans.
- **D3:** the year-2 screen (T2), 2,410 scans.
- **D4:** 500 "kernel pairs", where the same acquisition was rebuilt with a second kernel.
- **D5:** the z-fix versions. They are made automatically in D1 to D3 for every scan with a stretch of 1.54 or more (spacing ÷ thickness ≤ 0.65), about 908 in all dev.

## 4. What we know so far
### 4.1 From earlier work (L0, L1; already reported)
- **One year, baseline, test split:** Sybil 0.927 AUROC, the form 0.929. The difference is −0.003 [−0.063, +0.058].
- **Six years:** Sybil 0.724, the form 0.745. The difference is −0.021 [−0.073, +0.034].
- **Verdict by the fixed rules:** no evidence that Sybil carries information beyond the recorded findings.
- **Exploratory, on test:**
  - The form explains only 15% to 19% of Sybil's score.
  - The score is stable within a person (r = 0.61 one year apart).
  - Sybil and the form make mostly different false alarms.
  - This is why L2 opens the model: Sybil is equally accurate but largely "different", and we do not know what that difference is.

### 4.2 New in L2 (dev only, no outcomes used)
1. **Our pipeline reproduces Sybil exactly.**
   - Sybil's demo case matches the published scores exactly (difference 0.0).
   - Running the same scan twice gives identical results (0.0).
   - T4 and L4 GPUs agree within 7e-7.
   - From the saved internal vector, the six risk numbers can be recomputed within 7e-7. The split into feature contributions adds up exactly (1e-14).
   - So every later number about "what the score is made of" is exact, not an approximation.
2. **The series choice can be rebuilt from metadata alone.**
   - Sybil's split file names the scan used for each test exam, but not for dev exams.
   - Our rule ("sharpest kernel class, then thinnest slices, then most slices") picks the same scan as Sybil's file in **98.7%** of test exams (gate 90%).
   - We use the same rule on dev.
3. **Sybil stretches many scans along the body axis (z-stretch). This is a new technical finding.**
   - Sybil places the slices at the *slice thickness*, not at the true spacing between slices.
   - In **44%** of dev scans the spacing is smaller than the thickness, so the chest is stretched. At ratio 0.5 (578 dev and 400 test scans) it is stretched 2×.
   - Sybil then keeps only 200 slices (500 mm). At 2× stretch, the lung is **cut off** in **26 of 27** pilot scans. At 1.6× it is cut in 4 of 10. Below 1.6× it is cut in 0 of 263.
   - Fixing the spacing moves Sybil's 6-year score by **0.46 SD** of the spread between exams, on average, at 2× stretch (27 exams; 70% of them move by ≥ 0.25 SD; mean shift −0.29 logits). The move is 0.42 SD at 1.6× (10 exams) and 0.27 SD at 1.1 to 1.33× (74 exams).
   - We found no report of this in Sybil's GitHub issues or in the literature.
   - **Not yet known:** whether this changes accuracy. Few cancers are in the stretched group, so the accuracy part will be descriptive only.
   - These are pilot numbers. The full dev numbers (about 908 scans) come in S4.
4. **Part of Sybil's "year" structure is unused.**
   - Sybil is 5 models averaged. In 3 of the 5, the units that should make the risk grow with the years are **always off** (pilot, all exams). Their score is the same for all six years.
   - In the other 2, only the units for years 2 and 3 ever switch on, in 18% and 16% of exams.
   - This is descriptive and outcome-free. We will report it with the full dev data.
5. **Scanner differences in the raw images.**
   - Toshiba scans read air about **38 HU too low**. This is a scanner offset, and it also inflates the emphysema %.
   - Some GE scans have too little outside air to measure.
   - About 6 GE scans had a lung mask that leaked outside the body.
   - Fix A2 (approved) sets the image measures to missing when lung volume is < 1,500 ml, and marks the scan with a flag.
6. **Literature (searched again, 13 Nov).**
   - *Auditing Sybil* (ICML 2026) uses synthetic nodules, not real outcomes or radiologist findings.
   - Simon 2025 tested kernel pairs, but only for AUROC.
   - Nobody has split a lung screening model's score into its features and tested them against real outcomes, the radiologists' form and technical factors. The gap is still open.
7. **No second fully open dataset with outcomes.** Duke DLCS is restricted, and P-ELCAP is by request only. As you decided, there is no request for now.

### 4.3 How the work runs (operations)
- **Usage limit:** the cloud runs are now started by a plain Windows script, not by an AI agent. Before, the agent hit its 5-hour usage limit in the middle of D1. Now a usage limit cannot stop a run. Every launch still goes through the budget guard. This is a logged deviation: the protocol said "a lower-cost agent runs the paid runs".
- **Modal preemption:**
  - Modal sometimes takes a cloud machine back in the middle of a job and restarts the job on another machine. This happened once in D1.
  - **The data are safe.** Finished scans are skipped, and the results are identical.
  - **But Modal bills both attempts**, and our ledger had counted only the last one.
  - Fixed: the ledger now reads the real billed cost from Modal's billing report (`reconcile_billing.py`). The guard uses the higher of measured and billed.

## 5. What we do not know yet
- **The main questions are not answered yet.** No outcome analysis has been made in L2. By design, it waits until all dev data are in. So we do not yet know what Sybil's score is made of, why it is wrong, or whether its features can be used.
- Whether the feature decompositions (sparse autoencoder and the 5 simpler methods) pass their validity checks. If none passes, feature-level claims are dropped.
- **Kernel-pair sensitivity:** D4 is not run yet.
- Whether anything holds on dev strongly enough to become a hypothesis (gate 9.8).
- **The test split is closed.** Nothing about test is new since L1.

## 6. Money (ledger, 15 Nov, after billing reconciliation)
| | Used | Limit | Left |
|---|---|---|---|
| Task `lung_l2_audit` (S2 to S6) | $7.67 | $45.00 | $37.33 |
| Project, all tasks | $33.06 | $72.00 | $38.94 |
| November, account `shforghani2002` | $28.17 | $29.00 | $0.83 (used up) |

Expected from here:
| Step | Cost | Task total after |
|---|---|---|
| D2 + D3 + D4 (December) | ≈ $14.50 | ≈ $22.20 of $45 |
| S6 test | ≈ $15.50 to $18.40 | ≈ $37.70 to $40.60 of $45 |

- **Second account `armanfo`** (not used for this project without the lead's word; checked 15 Nov, read only):
  - November $1.62 used, all by that account's own other apps, which are not this project.
  - $27.88 left of its $29.50 cap. Nothing is running.
- After S6, the project would be at about $63 to $66 of $72.
- S7 (≈ $10) would need a new approval and a higher project cap.

## 7. Why we are waiting
- Your rule is a monthly stop of **$29 per account**. On this account, November is at $28.17.
- The second Modal account and the reserve are not used without your word.
- The analysis (S4) needs all the dev data, not only D1:
  - Year-1 cancers are counted on all screens. With D1 alone there are far fewer cancers.
  - The stability question (Q1c) needs the same person at T0 and T1.
  - The kernel question (Q1d i) needs D4.
- So D2, D3 and D4 wait for the new month. **This is a budget wait, not a failure.**

## 8. Plan from here (dates are estimates)
| When | What | Cost |
|---|---|---|
| Now to 30 Nov | **Free work on the PC, no outcomes:** write the missing S4 scripts (Q2 errors, U1a, U2, U3, U4) and test them. Run the outcome-free parts on D1: build the data table, fit the decompositions (SAE on the GPU), run the validity checks, and measure the z-fix change for the 430 D1 scans. | free |
| 1 Dec | **D2, D3, D4 run by themselves**, through the guard, about 4 to 6 hours. It stops on any problem, then copies the data to the PC and reconciles the billing. | ≈ $14.50 |
| 1 to 3 Dec | Check every new file (the same recomputation checks as D1); commit | free |
| December | **Full S4 on all dev data.** Gate 9.8: does any candidate hold on dev (right direction, interval excludes null, same sign in both halves)? **If nothing holds: stop, no test spending, report plainly.** The fallback paper is then L1 plus the technical findings. | free |
| Late December | **S5:** hypothesis file (≤ 5), frozen thresholds and script, all hashed. Then the external reviewer's check (8 yes/no items) and an honest chance estimate per hypothesis. **Stop for your OK.** | free |
| January | **S6:** test extraction, then the identity check (it must reproduce the L1 test scores), then the frozen analysis, run once | ≈ $15.50 to $18.40 |
| After S6 | **S8:** `RESULTS_L2.md`, figures, manuscript outline with a target journal | free |

Note on S6 timing:
- After D2 to D4, December has about $14.50 left.
- The test baseline and year-1 tiers (about $12) would fit if S5 is approved early enough.
- But the frozen analysis runs only once, after all test tiers are in. So S6 most likely ends in January.

**Early view of the paper.** This is an opinion, not a result. Formal chance estimates come at S5.
- **The most solid candidate so far is the z-stretch finding.** It is outcome-free, and it is checked in the code and in the images. It affects many NLST scans.
- **Kernel sensitivity at the score and feature level is likely to be measurable.** Simon 2025 tested AUROC only.
- **The feature-level findings are still unknown.** They are the higher-impact part, and the riskier one.
- If nothing holds, the honest fallback is still a paper:
  - Sybil is equal to the radiologists' form on accuracy (L1).
  - Sybil has technical sensitivities.

## 9. Decisions needed from the lead
1. **How should the December run start?**
   - **(a) Automatically (my suggestion).** Run this once, or type it in the chat with `!` in front:
     `powershell -NoProfile -ExecutionPolicy Bypass -File D:\Shayan\imgsae\exploratory\lung_l2\cloud\schedule_dec.ps1`
     - It creates a Windows task that starts on 1 December at 01:00. If the laptop is off at that time, the task starts when it is turned on.
     - On that day, keep the laptop on, logged in, plugged in and not asleep for about 6 hours. If it sleeps, the cloud work continues and is saved, but the script may stop, and I would restart it.
     - To cancel: `Unregister-ScheduledTask -TaskName imgsae_l2_dec -Confirm:$false`
   - **(b) Manually.** Tell me on or after 1 December, and I start the same script.
   - *Why I cannot do (a) myself:* the permission system blocks me from setting up unattended future spending.
2. **Use the second Modal account to avoid the wait?**
   - It would let D2 to D4 run now and save about 2 weeks.
   - My suggestion is **no**. There is free work to do until 1 December, and your one-account rule stays clean. It is your call.
3. **Free work on D1 now** (section 8, first row): I will do this unless you say no. It uses no outcomes. All outcome analyses wait for the full dev data.
4. **The external reviewer:** nothing is needed from them yet. Their main check is at S5 (late December). Section 10 gives a short message you can send now.

## 10. Short message for the external reviewer (optional, now)
> The Lung L2 audit is at step S3 (dev data extraction). The baseline dev tier is done; the rest runs in December. No test data has been opened. Two pilot checks were amended with the lead's OK (protocol section 16a, A1 and A2), and the paid runs are now started by a script instead of an agent (logged deviation, 15 Nov). Your main check comes at S5, probably late December; the brief is `docs/REVIEWER_BRIEF_L2.md`. Comments on the protocol before then are welcome.

## 11. Where the files are (branch `prostate-mri-plan`)
- **Protocol:** `docs/LUNG_L2_PROTOCOL.md` (amendments A1 and A2 in section 16a).
- **Every decision and result, in order:** `docs/EXECUTION_LOG.md`.
- **Current state:** `STATUS.md`.
- **Reviewer brief:** `docs/REVIEWER_BRIEF_L2.md`.
- **Check results:**
  - `imgsae/exploratory/lung_l2/results/s2_pilot_checks.json`
  - `s2_diagnose.json`
  - `s3_d1_checks.json`
  - `s1_manifest.json`
  - `s0_series_rule.json`
- **Run records:** `imgsae/exploratory/lung_l2/results/runs/`. **Ledger:** `imgsae/exploratory/p1b_sanity/cloud/ledger.json`.
- **Data (on the PC only, too large for git):**
  - `D:\Shayan\imgsae_data\lung_l2_vol\l2\` (dev/main 2,484 files, dev/zfix 430)
  - `D:\Shayan\imgsae_data\idc_index_25.0.5\`

## 12. Added 15 Nov: the three data groups, and how the feature methods are tested
### The three groups of Sybil's split
| Group | Participants | Scans | Did Sybil see them? | What we do with them |
|---|---|---|---|---|
| Train | 10,179 | — | **Yes.** Sybil learned its weights from them | **We do not run Sybil on them.** Sybil's features on its own training data are over-fitted and would mislead. We only use their recorded findings to fit the form model F. |
| Dev | 2,493 | 7,336 exams (D1 2,484 baseline, D2 2,442 year 1, D3 2,410 year 2) + 500 kernel pairs | **Partly.** No weights were learned from them, but Sybil's authors used dev to choose when to stop training. | Discovery: fit and test all feature methods, choose thresholds, write the hypotheses |
| Test | 2,347 | 6,715 | **No** | Confirmation, once, after the freeze |
| Never used by Sybil | 11,432 (34 cancers) | — | No | Only in S7, with a new approval |

### S4, the feature step, in detail (all on dev, on the PC, free)
1. **Input:**
   - For every dev exam, we take the 512 numbers that each of Sybil's 5 models makes just before its risk layer (`h`).
   - The risk is an exact linear function of `h`. So every feature's part in the score can be computed exactly.
2. **Six methods ("arms"), each with exactly 64 features, under the same rules:**
   - sparse autoencoder (SAE);
   - PCA;
   - ICA;
   - NMF;
   - k-means;
   - Sybil's own 64 most important units ("raw").
   - Same number of features, same seeds and consensus rule, same naming code. K = 128 is run as a check.
3. **Is a method good? Four pass marks, on held-out folds:**
   - **V1, function kept:** rebuilt from its features, Sybil's score must stay almost the same (r ≥ 0.98, AUROC change ≤ 0.005).
   - **V2, stable:** two different sets of random seeds must give the same features.
   - **V3, replicated:** a feature must appear in at least 3 of Sybil's 5 models, and there must be at least 16 such feature families.
   - **V4, the name is reliable:** each family is linked to nodules, other findings, demographics, image measures or technical factors. The two halves of dev must give the same name.
   - A method is valid only if it passes all four.
   - The **primary method** is the valid one with the most named families. If the SAE is not the best, we report that plainly. If no method is valid, feature claims are dropped, and the questions that need no features go on.
4. **References shown next to every method:**
   - a probe on all 2,560 numbers (the ceiling);
   - Sybil's own score;
   - the form model F.
5. **Use of the valid features:**
   - which families carry Sybil's score and its unexplained part (Q1b);
   - which families are high in Sybil's false alarms and low in its misses (Q2);
   - removing technical content (U1a);
   - a reliability flag (U2).
6. **Gate 9.8:** a candidate becomes a hypothesis only if it holds on dev (right direction, interval excludes the null, same sign in both halves of dev).

### Then S5 and S6
- **S5:** the fitted methods are frozen and hashed, together with the thresholds and at most 5 hypotheses. Then the reviewer's check and the lead's OK.
- **S6:** Sybil is run on the test scans. The test `h` is encoded with the frozen methods. **Nothing is refitted on test.** The frozen analysis runs once.

### What can start now
- The S4 code can be run on D1 (2,484 baseline exams) now. This covers fitting the six methods, V2, V3, the V1 score part, and V4 naming. None of these uses outcomes.
- This is a dry run. The protocol fits the methods on all dev exams, so the final numbers come after D2 and D3 are in.
