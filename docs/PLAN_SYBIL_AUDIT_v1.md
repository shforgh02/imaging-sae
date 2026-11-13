# Plan v1: a feature-level audit of Sybil on real screening patients ("Lung L2")

- **Date:** 2026-11-13. **Status:** proposed by the planning session, to be executed by a new session. Replaces v0.
- **Asked by the lead (2026-11-13):** open the model's black box in this project. Why is it right, why is it wrong, and can its features be used to improve prediction or reduce false positives and false negatives. Aim for the highest-impact paper the data can honestly support.
- **Read first:** `STATUS.md`; `imgsae/exploratory/lung_l0/RESULTS_L0.md`; `imgsae/exploratory/lung_l1/RESULTS_L1.md`; `docs/LUNG_L1_PROTOCOL.md`; `imgsae/exploratory/lung_l1/posthoc/` (scripts and outputs).

## 1. What is already established
| Fact | Source |
|---|---|
| Sybil's NLST split is public: 10,179 train, 2,493 dev and 2,347 test participants. The file lists series only for the test participants (6,715 series) | `imgsae_data/nlst_public/Shetty_et_al(Google)_data_splits.p` |
| On the test split Sybil does not beat a logistic regression on the radiologists' recorded findings: 0.927 vs 0.929 at one year, 0.724 vs 0.745 at six years (baseline scans, paired) | `RESULTS_L1.md` |
| The recorded findings add to Sybil at 2 and 6 years; a small gain from Sybil at one year is not excluded (+0.026, lower bound −0.004; likelihood-ratio test p about 1e-8) | `RESULTS_L1.md` |
| The recorded findings explain only 15% to 19% of the variation in Sybil's one-year score (rank correlation 0.33) | `posthoc/`, exploratory |
| Same participant one year apart: r = 0.61 for Sybil's score, 0.33 for the recorded-findings model | `posthoc/`, exploratory |
| At 90% specificity each, Sybil flags 615 non-cancers and the findings model 531; 212 are shared. Of 131 six-year cancers on baseline scans, both miss 62 | `posthoc/`, exploratory |
| Clean cancers: dev 149 participants (88 exams with cancer within one year, 319 within six); test 154 (91, 346). About 2,500 positive screens without cancer in each split | `posthoc/posthoc_counts_output.txt` |
| Measured cost of scoring: about 7.3 s and $0.0022 per series on a T4 | `RESULTS_L1.md`, ledger |

**The open question these facts create:** Sybil and the radiologist's form reach the same accuracy with mostly different content. Most of what Sybil computes is not on the form, is stable within a person, and nobody has shown what it is, whether it is signal or scanner, or how it relates to Sybil's errors.

## 2. Sybil's structure (read in its code on 2026-11-13; confirm at the pinned commit `d9fc81b9…`)
1. A 3D ResNet-18 encoder turns the scan (200 × 256 × 256) into a map of 512-number vectors.
2. `MultiAttentionPool` makes three pooled vectors (two attention pools and one global max pool, 512 numbers each), joins them (1,536 numbers) and applies one linear layer (`hidden_fc`) to get 512 numbers.
3. ReLU gives the vector **h** (512 numbers). Dropout is off at prediction time.
4. The hazard layer: logit for year t = `base_hazard_fc(h)` + sum over years j ≤ t of ReLU(`hazard_fc(h)`_j). The probability is the sigmoid of the logit.
5. The published model averages the probabilities of five separately trained members and then applies a per-year calibrator.

**What this allows.** For one member and one exam, the year-t logit is a linear function of **h** once we know which of the six hazard units are switched on. So each feature's contribution to that logit is computed exactly. The ensemble score is not linear in any single vector; contributions are computed per member and summarised across members, and the gap between "mean of member logits" and the calibrated ensemble score is measured and reported.

**Correction to v0:** v0 said the risk is a plain linear function of 512 numbers. That left out the six hazard ReLUs and the ensemble step. The statement above is the accurate one.

## 3. Questions (fixed before any activation is analysed)
- **Q1, composition.** What is the score made of? Split each exam's logit into feature contributions. How much of the score, and of its stable within-person part, comes from nodule features, from the rest of the lung, from demographics visible in the image, and from technical factors (scanner maker and model, reconstruction kernel, slice thickness)? Which features carry the part of the score that the radiologist's form does not explain, and is that part predictive of cancer?
- **Q2, errors.** Why is it wrong?
  - False alarms: which features drive high scores in people with no cancer, separately for alarms shared with the radiologist and alarms raised by Sybil alone.
  - Misses: in cancers with a low score, which features are absent or pull the score down, by tumour location, histology, stage, size and time to diagnosis.
- **Q3, use.** Can the features be used?
  - U1: remove technical features and recompute the score. Does accuracy hold, and does the spread of false-alarm rates between scanner groups shrink?
  - U2: a reliability rule built from features marks exams where Sybil should not be trusted. Is Sybil's accuracy lower there on unseen patients?
  - U3: Sybil plus the radiologist's form. How many false alarms per 1,000 screens are removed at the same sensitivity, and which feature groups make the two complementary?
  - U4 (ceiling): a fresh linear probe on **h**. No predictor built from features can beat it, so every feature-based result is reported next to it.

**Designed sub-study, technical sensitivity on real scans.** Many NLST exams have more than one reconstruction of the same acquisition (different kernel). Scoring two reconstructions of the same exam shows directly how much the score and each feature move when only the reconstruction changes. This is causal evidence on real data and costs about $1 per 500 pairs.

## 4. Data and roles
| Group | Participants | Role | Rule |
|---|---|---|---|
| Dev | 2,493 | Discovery: fit decompositions, name features, form hypotheses, set thresholds | All estimates cross-validated by participant |
| Test | 2,347 | Confirmation, once | No activation is extracted and no further outcome analysis of the existing test scores is made before the hypotheses are frozen |
| Never used by Sybil | 11,432 (34 cancers) | Optional: more scans for dictionary fitting; false-alarm rates | Unlabelled use only, or false alarms |
| Train | 10,179 | Not used | The model has seen their labels |

- **Series for dev exams.** The split file names series only for test. A selection rule is needed for dev: learn it from scan metadata only (kernel, slice thickness, number of slices, series description) by comparing the split file's test choices with all series of the same studies in the IDC index, and check Sybil's dataset code and paper for the authors' own rule. Gate: the rule picks the split file's series, or one with the same kernel class and thickness, for at least 90% of test exams. No outcome is used for this.
- **Outcomes and recorded findings:** the NLST package in `imgsae_data/nlst_public/tables/`, built by `nlst_l0.build`. Histology, stage, tumour location and lesion size are in the `prsn` and `canc` tables.
- **External data.** NLST is one trial. Step 0 checks whether a second low-dose CT set with outcomes is open to an individual (the Duke DLCS set on Zenodo is restricted and needs a request). None is promised; without one the claims are limited to NLST and this is stated.

## 5. What to save for every series (one pass, so nothing is paid for twice)
Per ensemble member:
- **h** (512, after ReLU) and the 512 numbers before ReLU;
- the joined pooled vector (1,536) that enters `hidden_fc`;
- raw hazards (6), base hazard (1), logits (6);
- `volume_attention_1`, `volume_attention_2`, `image_attention_1` (16-bit floats).

Per series: the calibrated ensemble probabilities (6); DICOM technical tags (maker, model, kernel, slice thickness, kVp, exposure, pixel spacing, reconstruction diameter, number of slices); timings; errors.
Once: the head weights of each member (`hidden_fc`, `hazard_fc`, `base_hazard_fc`) and the calibrator, with hashes.

The full encoder map is not saved in bulk (about 33 MB per scan). Localisation (step 7) reruns a few hundred chosen scans.

**Checks on saved data (gate of the pilot):**
- Sybil's published demo case reproduces within 0.005.
- For every pilot series and member, the logits recomputed on the PC from the saved **h** and head weights equal the saved logits within 1e-4.
- The calibrated ensemble probability recomputed from the member logits equals the saved one within 1e-4.

## 6. Analysis (to be fixed in `docs/LUNG_L2_PROTOCOL.md` before dev activations are analysed)
The protocol sets every threshold below as a number. Defaults are given; change them only before data.

### 6.1 Decomposition
- **Input:** **h** of each member, exam level.
- **Arms, same number of features each:** sparse autoencoder with consensus fitting (reuse `imgsae/` and `imgsae/exploratory/v2_ct/s1a_lib.py`), PCA, ICA, NMF, k-means, and the raw 512 units.
- **Fair comparison:** same feature counts and the same selection rule for every arm; results recomputed from tables.
- **Validity, each with a pre-set pass mark:**
  - function kept: replacing **h** by its reconstruction changes the member's logit little (default: correlation ≥ 0.98 and AUROC change ≤ 0.005);
  - stability across seeds;
  - replication across members: a feature counts only if a matching feature (default: correlation of activations across exams ≥ 0.7) exists in at least three of the five members;
  - split-half agreement of feature-label associations inside dev.
- The paper is about Sybil. If the sparse autoencoder does not beat the simpler arms, the best valid arm is used and the comparison is reported as it is.
- If dev alone gives unstable dictionaries, scans of never-used participants may be added for fitting (unlabelled), inside the budget.

### 6.2 Naming
Each replicated feature is tested against: the 39 recorded findings; age, sex, smoking; technical tags; cancer at 1, 2 and 6 years; histology group, stage, tumour location, lesion size; and its own stability within a person across years. False discovery rate control over all tests. Each feature gets one group: nodule, lung background, demographic, technical, or unnamed.

### 6.3 Composition (Q1)
- Contribution of feature i to an exam's logit = effective head weight (given the hazard units that are on) × decoder direction i × activation i, plus the reconstruction residual as its own term.
- Share of score variation by group = covariance of the group's summed contribution with the logit, divided by the variance of the logit. Reported for all exams, for non-cancers, and for one-year and six-year logits.
- The same split for (a) the part of the score not predicted by the recorded findings and (b) the within-person stable part.
- Paired reconstructions: change in score and in each feature group between two kernels of the same exam.

### 6.4 Errors (Q2)
- Thresholds fixed on dev: Sybil at 90% specificity, and at the radiologists' positive-call rate.
- False alarms in three classes (Sybil only, shared, form only) against true negatives: enriched features and their contributions.
- Missed against caught cancers at 1, 2 and 6 years: features, and tumour location (central or peripheral), histology, stage, size.
- Power is stated with every table. One-year misses are few (about 11 of 72 in the scored test exams), so claims about them are descriptive.

### 6.5 Use (Q3)
U1 to U4 as in section 3, each with its comparison arm, its margin and its test written in the protocol.

### 6.6 Confirmation on test
- At most five hypotheses, chosen from dev, each with one test, one margin and Holm correction. Written to a file, hashed, checked by a second reviewer and approved by the lead before any test activation is extracted.
- The frozen analysis runs once. Participant bootstrap, 2,000 draws.
- Anything else found on test is labelled exploratory.

## 7. Steps, gates and cost
| Step | What | Cost | Gate to continue |
|---|---|---|---|
| S0 | Read *Auditing Sybil* (arXiv 2602.02560) in full, Sybil's paper and dataset code; repeat the literature search; look for an open external set. Write `docs/LUNG_L2_PROTOCOL.md`. **Stop for the lead's OK** | free | No published work already answers Q1 to Q3 on real outcomes. Series rule passes (section 4) |
| S1 | Build the dev manifest with the series rule; list paired reconstructions | free | At least 95% of dev exams get a series |
| S2 | Pilot: 300 dev series with all saves; 50 of them also on an L4 to pick the cheaper GPU per series | about $2 | The three checks of section 5; cost per series measured; projection made |
| S3 | Dev extraction in tiers, each series saved at once: D1 baseline scans, D2 year-1 scans, D3 year-2 scans, D4 500 paired reconstructions | about $19 | Fewer than 5% failures per tier |
| S4 | Decompose, validate, name, composition, errors, use, on the PC | free | Validity pass marks met by at least one arm; at least one hypothesis holds in cross-validation inside dev |
| S5 | Freeze up to five hypotheses. **Stop for the lead's OK** | free | File hashed, second reviewer's check done |
| S6 | Test extraction (T1 baseline, T2 year 1, T3 year 2, T4 500 paired reconstructions), then the frozen analysis once | about $18 | — |
| S7 (optional, separate OK) | Never-used participants for false-alarm rates; full maps for a few hundred chosen scans to show where confirmed features look | about $10 | S6 confirmed something worth showing |
| S8 | `RESULTS_L2.md`, figures, manuscript draft | free | — |

**Stop points without spending more:** after S0 (already answered elsewhere), after S2 (pilot fails), after S4 (nothing holds on dev).
**Minimum useful set if money is short:** D1 + D2 and T1 + T2 (about 9,400 series).

## 8. Budget
- **Proposed:** new ledger task `lung_l2_audit`, $45.00 in total for S2 to S6, spread over months. S7 needs its own approval.
- **The guard as it stands blocks this.** `budget.py` uses one number ($29) for the monthly check and for an all-time project check, and the project has used $25.39. The lead must approve a separate all-time project limit. The monthly stop at $29 stays.
- **November 2026 on account `shforghani2002`:** Modal's billing shows $21.12 used, so about $7.90 before the $29 stop. That covers the pilot and part of D1. The rest waits for 1 December unless the lead allows the second account.
- **Rules carried over from L1:** every launch through the guard; T4 or L4; container timeout at most 60 minutes; at most 4 containers; each series saved at once; detached launch; images not kept; the lead's other volumes and apps not touched; projection after the pilot = series × measured seconds ÷ 3,600 × rate × 1.2.
- **Who runs it:** the lead asked that paid runs are planned by the main session and executed by a lower-cost agent under the written protocol.

## 9. What the paper would be
- **Working title:** "What a lung cancer screening AI sees: a feature-level audit of Sybil in 4,800 trial participants with radiologist findings and six-year outcomes".
- **Core results the design can deliver:**
  1. Same accuracy as the radiologist's form with under one fifth shared score (done, paired).
  2. What the rest is: shares from nodules, lung background, demographics, technical factors.
  3. Direct technical sensitivity: same exam, two reconstructions.
  4. Named reasons for false alarms and the profile of missed cancers.
  5. Three use tests confirmed or refuted on unseen patients.
- **What would make it high impact:** a confirmed statement that changes how the model should be used. Examples: a named technical dependence with a safe correction; a reliability rule that holds on unseen patients; a false-alarm reduction from combining model and form.
- **Journals:** Radiology: Artificial Intelligence as the realistic home. Radiology, The Lancet Digital Health or npj Digital Medicine if a use test is confirmed, better still with a second dataset.
- **Fallback if S4 finds nothing:** a short report of the paired L1 result with the disagreement tables. It is already complete.

## 10. Risks, stated in advance
- **Few one-year misses.** Real power exists for false alarms and for cancers at two to six years.
- **Small sample for dictionary fitting** (about 7,000 exam vectors per member). The validity gates decide; the never-used participants are the reserve.
- **The sparse autoencoder may not beat simpler arms** on a 512-number vector.
- **Competing audit:** *Auditing Sybil* (ICML 2026) inserts synthetic nodules and reports a location bias and artifact sensitivity. It has no real outcomes, real errors or radiologist findings. Known here only from summaries; S0 reads it in full and adjusts the claims.
- **One trial, one model.**

## 11. Not allowed
- Extracting test activations, or making new outcome analyses of the existing test scores, before the hypotheses are frozen.
- Using train participants for any outcome analysis.
- Changing thresholds, gates, hypotheses or the frozen analysis after the data they govern are seen. Any later change is a logged deviation.
- Exceeding a budget, bypassing the guard, using the reserve or the second account without the lead's word.
- Committing or pushing to git unless the lead asks.

## 12. Files
- Protocol: `docs/LUNG_L2_PROTOCOL.md`. Work folder: `imgsae/exploratory/lung_l2/` (cloud job, launch and collect scripts, `results/`, `RESULTS_L2.md`).
- Reuse: `imgsae/exploratory/lung_l1/cloud/` (working Sybil image, IDC download with `s5cmd`, sharded runs), `imgsae/exploratory/lung_l0/nlst_l0.py` (tables, labels, recorded-findings model), `imgsae/exploratory/v2_ct/` (SAE, consensus, baselines, validity checks), `imgsae/exploratory/p1b_sanity/cloud/budget.py` (guard).
- Every decision and result goes into `docs/EXECUTION_LOG.md`; the current state into `STATUS.md`.
