# Reporting checklists for the paper: TRIPOD+AI and CLAIM 2024, mapped to this project (22 Nov 2026)

**In simple words.** Journals will ask for two checklists. TRIPOD+AI (27 items) is for studies that build or test a prediction model; CLAIM 2024 (44 items) is for AI in medical imaging. Our paper tests Sybil (evaluation), and it also builds two small forms from the radiologists' record (F1 and the portable form P, development). For each item the table says where the content already is, and what is missing. **Revised the same day after Neon's independent assessment (`gemini_review/gemini_task6_step2.txt`): my first version called several items "have" that are only partly covered, one software statement was wrong, and O2 was wrongly listed as external.** The corrections are in the section "Corrections after Neon's assessment" at the end; where the two disagree, that section wins. The gaps now ranked by reviewer concern: (1) flow diagram with full attrition and a "Table 1" per split that includes the CT acquisition parameters; (2) calibration of the portable form P and calibration plots for Sybil, F and P; (3) a clear internal vs external framing (only LIDC-IDRI is external, and only for the mechanism); (4) the lead's ethics, funding and conflict statements; then code release and licence, results by sex and race, and performance by scanner maker.

Status words: **have** = the content exists in a project file and only needs writing into the paper; **write** = a short statement, no new work; **gap** = new work or a decision is needed; **N/A** = not applicable, say so in one line.

Sources: TRIPOD+AI, Collins et al., *BMJ* 2024;385:e078378 (Table 2, read from the official full text); CLAIM 2024, Tejani et al., *Radiol Artif Intell* 2024;6(4):e240300 (official checklist page). Item titles are shortened here; use the official wording in the submission.

## The gaps, and what to do (in order of value)

| Gap | Items | Proposal | Who |
|---|---|---|---|
| Fairness: results by sex and race | TRIPOD 3c, 14, 23a; CLAIM 36 | An exploratory, descriptive check on the test split (already open): AUROC of Sybil and of the forms, and the size of the slice-spacing effect, by sex and by race group (NLST is about 90% white, so the Black subgroup is small: report counts and wide intervals, no test). CPU only, no money. | me, after the lead's OK |
| Participant flow diagram | TRIPOD 20a; CLAIM 35 | Part of task 5 (figures): NLST → IDC series → selection → train / dev / test / never-used, with exclusions at each step. | me (task 5) |
| "Table 1": characteristics per split | TRIPOD 20b, 20c; CLAIM 36 | Age, sex, smoking, nodule findings, scanner maker, slice ratio, cancers, per split; dev vs test vs O2 side by side. | me (task 5) |
| Ethics statement | TRIPOD 17 | Public, de-identified NLST data (IDC / TCIA). Whether an ethics waiver is needed depends on the lead's institution. | the lead |
| Funding and conflicts of interest | TRIPOD 18a, 18b; CLAIM 44 | Statement. | the lead |
| Registration | TRIPOD 18d | No registry exists for this kind of study, but the plans are frozen in git with hashes. **Option:** a public, time-stamped copy of the O2 plan (for example on OSF) before the first O2 scan on 1 December would make the pre-registration visible to reviewers. | the lead (an outside action) |
| Code and data sharing | TRIPOD 18e, 18f; CLAIM 43 | Data: public (IDC / TCIA). Code: the repository and the partner kit; the licence is still open (MIT proposed). | the lead |

## TRIPOD+AI (27 items; D = development, E = evaluation)

| Item | Short title | Where in the project | Status |
|---|---|---|---|
| 1 | Title | to write: "evaluating" Sybil and "developing" the forms | write |
| 2 | Abstract (TRIPOD+AI for Abstracts) | — | write |
| 3a | Context and rationale | `RESULTS_L2.md` 6; `LITERATURE_AND_PAPER_STRATEGY_R3.md` | have |
| 3b | Target population, intended use | screening low-dose CT (NLST eligibility) | write |
| 3c | Known health inequalities | NLST about 90% white; Sybil in a mostly Black cohort (table ref. 5) | gap (fairness) |
| 4 | Objectives (development and/or evaluation) | `LUNG_L2_PROTOCOL.md` 3 | have |
| 5a | Data sources | NLST via IDC (protocol 4); LIDC-IDRI (X5); IDC metadata (X12) | have |
| 5b | Dates of accrual and follow-up | NLST 2002–2004 enrolment, follow-up from the NLST tables | write |
| 6a | Setting, number and location of centres | NLST: 33 US centres | write |
| 6b | Eligibility | NLST criteria; our series selection (protocol 5) | have |
| 6c | Treatments | N/A (screening; outcome is diagnosis) | N/A |
| 7 | Data preparation, quality checks | protocol 5–6, 8; the slice-spacing (z-fix) handling; gates G1/G2 | have; by group: gap (fairness) |
| 8a | Outcome, time horizon | lung cancer within 1 and 6 years of the exam (protocol 9–10) | have |
| 8b | Subjective outcome assessors | N/A (NLST diagnosis records) | N/A |
| 8c | Blinding of outcome | outcome recorded by NLST, independent of the models | write |
| 9a | Choice of predictors (D) | form F1 (protocol), portable form P (`RESULTS_L2.md` 3h) | have |
| 9b | Predictor definitions | `RESULTS_L2.md` 2.1b, 3h; `partner_kit/CODING_SHEET.md` | have |
| 9c | Predictor assessors (radiologists) | NLST radiologists' structured reports | write |
| 10 | Sample size | protocol 9.9 (power on dev); `O2_PLAN.md` | have |
| 11 | Missing data | form items (X10), Sybil failures (protocol 8) | have |
| 12a | Data use and partitioning | train / dev / test / never-used (protocol 4; O2) | have |
| 12b | Predictor handling | X10 (standardised, logistic) | have |
| 12c | Model type, tuning, internal validation | X10: logistic, C = 0.3, fit on train, checked on dev, frozen before test | have |
| 12d | Heterogeneity | by scanner maker (X11, X12, H7) | have |
| 12e | Performance measures | AUROC, calibration, X9 measures at cuts, IPCW | have |
| 12f | Model updating | none for Sybil; dev-set cuts tested for transfer (X9) | have |
| 12g | How predictions were calculated | Sybil code and calibrator versions (hashes, protocol 6) | have |
| 13 | Class imbalance | none used | write |
| 14 | Fairness | — | gap |
| 15 | Model output, thresholds | Sybil calibrated risks; cuts set on dev (X9) | have |
| 16 | Training vs evaluation differences | Sybil was trained on NLST; our test split and the O2 never-used participants (`O2_PLAN.md` 0) | have; state very clearly |
| 17 | Ethics approval | — | gap (the lead) |
| 18a–f | Funding, conflicts, protocol, registration, data, code | protocol and plans in git with hashes | gap (the lead) for a, b, d, licence |
| 19 | Patient and public involvement | none | write ("none") |
| 20a | Participant flow | `RESULTS_L2.md` 5 (numbers) | gap (diagram, task 5) |
| 20b | Characteristics | — | gap (Table 1) |
| 20c | Evaluation vs development data | — | gap (Table 1) |
| 21 | Participants and events per analysis | `RESULTS_L2.md` 1–3 | have |
| 22 | Full model specification | `results/x10/x10_portable_form_params.json`; F1 parameters (frozen) | have |
| 23a | Performance with intervals, subgroups | `RESULTS_L2.md` 1–3; subgroups by sex/race: gap | have / gap |
| 23b | Heterogeneity across clusters | by maker | have |
| 24 | Model updating results | N/A (no updating) | N/A |
| 25 | Interpretation, incl. fairness | `RESULTS_L2.md` 4, 6 | have (fairness: gap) |
| 26 | Limitations | `RESULTS_L2.md` 4 | have |
| 27a | Poor-quality or unavailable input | the central finding: overlapping series are mis-read; X12 prevalence | have |
| 27b | User interaction and expertise | Sybil is automatic; the series choice is a human step (X12) | write |
| 27c | Next steps | O2, the partner kit, outside cohorts | have |

## CLAIM 2024 (44 items)

| Item | Short title | Where | Status |
|---|---|---|---|
| 1 | AI methodology in title or abstract (deep learning) | — | write |
| 2 | Structured summary | — | write |
| 3 | Background, intended use | `RESULTS_L2.md` 6 | have |
| 4 | Aims, hypotheses | frozen H1–H7, O2 family | have |
| 5 | Prospective or retrospective | retrospective | write |
| 6 | Study goal | audit of an existing model | write |
| 7 | Data sources | NLST (IDC), LIDC-IDRI, IDC metadata | have |
| 8 | Inclusion and exclusion | protocol 5; O2 lists | have |
| 9 | Data pre-processing | Sybil's own pre-processing, the z-fix, padding (X11) | have |
| 10 | Selection of data subsets | train / dev / test / never-used | have |
| 11 | De-identification | public de-identified collections | write |
| 12 | Missing data | protocol 8; X10 | have |
| 13 | Image acquisition protocol | NLST protocol; slice thickness and spacing by maker (X12) | have |
| 14 | Reference standard definition | NLST lung cancer diagnosis | write |
| 15 | Rationale for the reference standard | trial outcome ascertainment | write |
| 16 | Source of reference standard | NLST tables | write |
| 17 | Annotation of the test set | N/A (no new annotation; radiologists' findings are NLST's) | N/A |
| 18 | Inter- and intra-rater variability | NLST single reads; LIDC multi-reader (X5) | write |
| 19 | Assignment to partitions | Sybil's NLST splits; never-used participants (O2) | have |
| 20 | Level at which partitions are disjoint | participant level | write |
| 21 | Intended sample size | protocol 9.9; O2 power | have |
| 22 | Detailed model description | Sybil (published); forms F1, P | have |
| 23 | Software libraries | two environments: the cloud scoring image (pinned in `cloud/l2_sybil_modal.py`: torch 1.13.1, torchvision 0.14.1, torchio, pydicom, Sybil at a fixed commit; **T4 GPUs**, which have no TF32; the run records hold the GPU name) and the PC analysis environment (`imgsae/requirements-lock.txt`). *[corrected: "TF32 off" applied only to the local GPU check, not to the cloud runs]* | have (write out the versions) |
| 24 | Initialisation of parameters | N/A for Sybil (published weights); forms: logistic fit | write |
| 25 | Training approach | forms only (X10) | have |
| 26 | Selection of the final model | X10: fixed before test | have |
| 27 | Ensembling | Sybil's 5-member ensemble (as published) | write |
| 28 | Performance metrics | AUROC, calibration, sensitivity, specificity, PPV, rates per 1,000 | have |
| 29 | Significance and uncertainty | participant bootstrap, Holm (frozen) | have |
| 30 | Robustness or sensitivity analysis | X7, X9, X11 | have |
| 31 | Explainability methods | shared axes of `pooled`, attention (H6, R3, X11) | have |
| 32 | Evaluation on internal data | dev / test | have |
| 33 | Testing on external data | LIDC-IDRI (X5): external, but **only for the outcome-free mechanism** (no cancer outcome); partner kit: planned external clinical testing. *[corrected: O2 is NOT external; it is more NLST, the same trial]* All cancer-outcome comparisons are internal (NLST) so far. | partly / planned |
| 34 | Clinical trial registration | N/A (not a trial) | N/A |
| 35 | Numbers included and excluded | `RESULTS_L2.md` 5 | have (diagram: gap) |
| 36 | Characteristics per partition | — | gap (Table 1; fairness) |
| 37 | Performance with uncertainty | `RESULTS_L2.md` 1–3 | have |
| 38 | Diagnostic performance and precision | X9 | have |
| 39 | Failure analysis | the slice-spacing mechanism; misses (N6) | have |
| 40 | Limitations | `RESULTS_L2.md` 4 | have |
| 41 | Implications for practice | series choice, guideline-conformant overlap (`LITERATURE_CHECK_2026-11-22.md` 3) | have |
| 42 | Protocol or technical details | protocol, O2 plan, hashes | have |
| 43 | Availability of software, model, data | the repository, the partner kit (licence open), public data | gap (licence) |
| 44 | Funding | — | gap (the lead) |

## Corrections after Neon's assessment (22 Nov; these override the tables above)

**Items I marked "have" that are only partly covered** (Neon's reading; I checked the file references, the numbers must be re-read from the named files before they go into the paper):

| Item | What is missing |
|---|---|
| TRIPOD 4 | The protocol's questions (section 3) are the original dev audit questions; the objectives of X5, X8–X12 and O2 must be added. |
| TRIPOD 6b; CLAIM 8 | NLST participant eligibility (age, pack-years, years since quitting), the LIDC-IDRI scan selection (X5) and the X12 filters are not in protocol section 5. |
| TRIPOD 10; CLAIM 21 | No events-per-item argument for fitting F1, F6, P1, P6; the test-split power is in `HYPOTHESES_L2.md`, not protocol 9.9; nothing for LIDC. |
| TRIPOD 11; CLAIM 12 | Missing-data rules are scattered: nodule size fills in `lung_l0/nlst_l0.py`, failed lung segmentation (image measures imputed with an indicator), censored outcomes, blank spacing ratios; they need one table. |
| TRIPOD 12d, 23b | No centre-level analysis (NLST centre is not in the public tables: say so) and **no test AUROC or calibration by scanner maker** (section 3 stratifies the z-fix, H6, H7 only). → **gap** |
| TRIPOD 12e, 23a | **No calibration for the portable form P** (X10) and **no calibration plots** for Sybil, F or P. → **gap** |
| CLAIM 9, 30, 31 | X11 is still running: "in progress", not "have". |
| CLAIM 13 | The acquisition parameters of the cohorts we actually evaluated (makers, models, kVp, mAs, kernel, thickness, spacing) are not tabulated; X12 is about all IDC. → part of Table 1 |
| CLAIM 35 | `RESULTS_L2.md` 5 has the S6 extraction counts only; the attrition from the NLST CT arm to train / dev / test / never-used, outcome exclusions, O2 blank-ratio exclusions and LIDC 1,010 → 197 must be compiled. |
| CLAIM 39 | Failure analysis covers missed cancers only; false positives and one or two visual examples are missing. |
| TRIPOD 3a | `LITERATURE_AND_PAPER_STRATEGY_R3.md` is out of date (old reference 18 wording, framing before X9–X12): do not copy from it without updating. |
| TRIPOD 12b–c, 12g, 21; CLAIM 19 | Partly: P only (F1, F6, F+I, C = 0.3 rationale, linearity, clustering of repeat scans in fitting are not described); hashes and formulas are spread over `HYPOTHESES_L2.md`, smoke files and `l2_form.py`; train counts for the forms; the provenance of Sybil's split file and how the never-used participants differ (cancer-poor). P's 14 items were chosen after F's test results were seen (weights fitted on train only): say so. |

**Items whose status was wrong:**
- TRIPOD 8c: not just "write". The radiologists' positive calls triggered the work-up, so the form, the call and Lung-RADS are **not blind to the 1-year outcome** (incorporation / work-up bias); point to the bias-resistant checks (W1–W3 in X7, the 6-year and late endpoints). → **write, as a limitation**
- TRIPOD 6c, 8a: not "N/A": deaths from other causes before 6 years (competing risk) and how they were handled (censored; complete-case; IPCW assumes independent censoring). → **write, as a limitation**
- TRIPOD 12f, 24: not "N/A": X7 tested recalibration of Sybil on dev (it made test calibration worse) and X1, X3, X8–X10 tested extensions (form + Sybil, Lung-RADS + Sybil, Sybil + demographics); say that no updated Sybil is proposed. → **have**

**Internal vs external (TRIPOD 16; CLAIM 19, 32, 33).** Sybil was trained and tuned on NLST. Our dev split was used by Sybil's developers for model selection (in-sample for Sybil: dev results are optimistic, which also explains why dev-tuned cuts did not transfer). Our test split is a held-out NLST split: participant-disjoint, but the same trial, centres, era, scanners and reporting forms, so it is **internal** testing for Sybil and for F and P (fitted on Sybil's train split). O2 (never-used NLST participants) is **internal** too, only better separated. **LIDC-IDRI is external, but only for the outcome-free mechanism.** X12 is a deployment-context audit, not a model test. The partner kit is the planned external clinical test. The paper must never call any NLST result "external validation".

**Further reviewer flags to address in the manuscript:**
1. Repeated use of the opened test split (L1, S6, X1, X3, X7–X10, the proposed fairness check): a clear wall in Methods between the two pre-registered families (S6 H1–H4, H6, H7, with H7 "partly seen"; O2, with amendment A1 disclosed) and everything post hoc.
2. Sybil's calibrated score takes few distinct values (steps; many ties at the bottom): achieved false-alarm shares miss targets by up to about 2 points (X9, X10); say so under TRIPOD 15 / CLAIM 28.
3. Lung-RADS and Brock were reconstructed from NLST forms (not prospective reads): part-solid size assumption, family history absent (set to 0 in Brock); NLST single reads, so reader variability is unmeasured (CLAIM 17–18; TRIPOD 9c).
4. Repeat scans of one person entered the form fitting as separate rows (no cluster weights), while all evaluation intervals are clustered by participant: one sentence (TRIPOD 12c–d).
5. De-identification shifts study dates in IDC / TCIA (why X12 uses scanner launch years and collection eras): CLAIM 11.
6. The abstract has its own 13-item TRIPOD+AI for Abstracts list (include calibration, dates, both evaluation and development).
7. Code release: the exact Sybil commit, whether Sybil's current code still reads SliceThickness as the z spacing at submission, the disclosure timeline to Sybil's developers, and a release copy without hard-coded `D:\Shayan` paths (keep the frozen script hashes).
8. Results by sex and race: worth doing (closes TRIPOD 3c, 14, 23a; CLAIM 36). Sex is well powered and may matter for the mechanism (shorter chests fill the box differently). Frame it as exploratory and descriptive (point estimates and 95% participant-bootstrap intervals, no p-values, no "no bias" claims); race groups with fewer than 10 cancers get counts only; report the outcome-free z-fix shift and the stretch exposure by group too; say plainly that NLST (about 90% white) cannot show equity, citing the predominantly Black cohort study (reference 5).
