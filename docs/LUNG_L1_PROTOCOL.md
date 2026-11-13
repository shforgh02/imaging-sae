# Lung L1 protocol: Sybil against the radiologists' recorded findings, paired, on Sybil's test split

- **Date fixed:** 2026-11-12, before any Sybil score was computed.
- **Approved by the lead:** 2026-11-12 ("1.yes"), with a **$15.00 cap**. The lead asked that a lower-cost agent runs it under this plan.
- **Background:** `imgsae/exploratory/lung_l0/RESULTS_L0.md`. On Sybil's test participants, a logistic regression on the NLST radiologists' recorded findings scores the same as Sybil's *published* accuracy. That comparison was unpaired. L1 makes it paired.

## 1. Question
On the same exams of Sybil's own test participants:
1. Does Sybil beat the radiologists' recorded findings?
2. Does Sybil add information on top of them?

## 2. Data
| Item | Source | Where |
|---|---|---|
| Test series | Sybil's split file: 2,347 test participants, 6,715 series (one per exam) | `imgsae_data/nlst_public/Shetty_et_al(Google)_data_splits.p` (SHA-256 `BF58BC09…4F83B949`) |
| Images | NLST collection on the NCI Imaging Data Commons (public, no account) | downloaded per series inside the cloud job, then deleted |
| Outcomes and recorded findings | NLST clinical package for IDC | `imgsae_data/nlst_public/tables/` |

- Only the series named in the split file are scored. No other series is chosen.
- Study year: T0, T1 or T2. NLST study dates are shifted so that the year gives the study year (1999 = T0, 2000 = T1, 2001 = T2). This is checked in step S1 and again by the analysis (section 6, mapping check).
- Train and dev participants are never scored.

## 3. Model
- Sybil, `sybil_ensemble` (five models plus calibrator), installed from `github.com/reginabarzilaygroup/Sybil` at a pinned commit. Nothing is retrained or tuned.
- The commit and the SHA-256 of every checkpoint file are recorded in the result file.

## 4. Steps and gates
Each step stops and reports if its gate fails. No gate may be changed after it is read.

| Step | What | Gate |
|---|---|---|
| **S0** | `budget.py status`. Record month usage and project total | The guard's three checks must leave room for the first launch |
| **S1** | Manifest: one row per test series (series, participant, the split file's `cancer_in_1`). Join with the IDC index for study date, size and download address | ≥ 95% of the 6,715 series found in IDC; at most one series per participant and study year |
| **S2** | Smoke and benchmark on a GPU container: (a) Sybil's published demo case; (b) 20 test series, with seconds per series split into download, loading and inference | (a) the six demo risks match the published values within 0.005; (b) projected cost of the whole run is computed by the rule in section 5 |
| **S3** | Full run in tiers, each series saved at once: **P1** all baseline (T0) series; then **P2** the T1 and T2 series, participants in a fixed random order (seed 0) | P1 must complete. P2 runs as far as the budget rule allows |
| **S4** | Export `scores.csv`: `series_uid, pid, study_yr, y1 … y6` | Row count equals the number of saved series; no duplicate participant-year |
| **S5** | Run the frozen analysis once (section 6) | Its own mapping check and sanity check |
| **S6** | Write `RESULTS_L1.md`; close the ledger runs with measured costs; list any deviation | — |

**If a series fails** (download or loading error): record the series and the error, continue. More than 5% failures in a tier is a stop.

## 5. Budget (task `lung_l1_sybil`, cap $15.00)
- Every launch goes through the budget guard (`imgsae/exploratory/p1b_sanity/cloud/budget.py`, used as in `imgsae/mri/cloud/launch.py`). A launch that the guard refuses is not made.
- GPU: T4 or L4 only. One container timeout ≤ 60 minutes. At most 4 containers at once.
- **Projection rule after S2:** projected cost = series × measured seconds per series ÷ 3,600 × hourly rate × 1.2.
  - If spent + projected (P1 + P2) ≤ $13.00: run everything.
  - Otherwise run P1, then as many P2 participants (in the fixed order) as keep the committed total ≤ $13.00.
  - If even P1 does not fit: stop and report.
- **Hard stop:** committed total (measured + open worst cases) never above $15.00. The last $2.00 is for collection, export and surprises.
- Raw images are not kept on a Modal volume. The volume holds only the manifest, per-series score files and logs. It is deleted at the end, after the scores are on the project PC.
- Account `shforghani2002` only. No other volume or app in the workspace is touched. The second account is not used.

## 6. Analysis (frozen)
Code: `imgsae/exploratory/lung_l1/l1_analysis.py` (SHA-256 `1781679E…2091FC1D`), which imports the L0 comparator from `imgsae/exploratory/lung_l0/nlst_l0.py` (SHA-256 `135689F2…E5369E7F`). It was dry-run on fake scores only. It is run once on the real scores and not edited after that; any later change is a logged deviation.

- **Comparator:** logistic regression on the recorded findings plus age, sex and smoking status, fitted on Sybil's train and dev participants only (exactly the L0 model).
- **Paired:** both arms are scored on the same exams (those with a Sybil score and a known outcome).
- **Intervals:** participant bootstrap, 2,000 draws. The two primary analyses use 97.5% intervals.

| Analysis | Outcome | Exams | Sybil score |
|---|---|---|---|
| **A1 (primary)** | cancer within 1 year | baseline scans | year 1 |
| **A2 (primary)** | cancer within 6 years | baseline scans | year 6 |
| A3 | cancer within 1 year | all screens (the recorded findings may use earlier scans) | year 1 |
| A4 | cancer within 2 years | baseline scans | year 2 |
| A5 | cancer 1 to 6 years after a negative baseline screen | baseline scans | year 6 |

For each: both AUROCs; Sybil minus recorded findings; the cross-fitted combination minus recorded findings (added value of Sybil); the combination minus Sybil (added value of the findings); likelihood-ratio tests both ways.

**Checks inside the analysis, before any reading:**
- **Mapping:** the split file's `cancer_in_1` must agree with the table-derived label for ≥ 99% of scored exams, and every scored series must belong to a test participant. Otherwise: stop, no interpretation.
- **Sanity:** Sybil's own AUROC must fall in 0.88 to 0.97 for A1 (published 0.93) and 0.86 to 0.96 for A3 (published 0.92). Otherwise the pipeline is suspect: stop, no interpretation.

**Verdict rules (A1 or A2):**
| Verdict | Rule |
|---|---|
| Sybil beats the recorded findings | Sybil minus findings ≥ +0.03, lower bound > 0 |
| Sybil adds to the recorded findings | combination minus findings ≥ +0.02, lower bound > 0 |
| No evidence of information beyond the recorded findings | neither rule holds; the intervals are reported |

**Power, stated in advance.** The baseline set has about 41 cancers within one year and about 140 within six. A true difference under about 0.03 to 0.04 can be missed. A null result here means "no large gap", not "equal".

## 7. Not allowed
- Editing the analysis, the comparator, the gates or the verdict rules after scores exist.
- Scoring any train or dev participant, or any series not in the split file.
- Exceeding the cap, bypassing the guard, using the reserve or the second account.
- Committing or pushing to git. The lead decides that.

## 8. Outputs
- `imgsae/exploratory/lung_l1/`: the cloud job, launch and collect scripts, `results/scores.csv`, `results/l1_results.json`, `results/run_info.json` (Sybil commit, checkpoint hashes, timings, failures), `RESULTS_L1.md`.
- Ledger: every run opened and closed under `lung_l1_sybil`.
