# Reporting checklists for the paper: TRIPOD+AI and CLAIM 2024, mapped to this project (22 Nov 2026)

**In simple words.** Journals will ask for two checklists. TRIPOD+AI (27 items) is for studies that build or test a prediction model; CLAIM 2024 (44 items) is for AI in medical imaging. Our paper tests Sybil (evaluation), and it also builds two small forms from the radiologists' record (F1 and the portable form P, development). For each item the table says where the content already is, and what is missing. **Most items are covered by existing project files.** The real gaps are few: (1) results by sex and race (fairness), (2) a participant flow diagram and a "Table 1" of the people in each split, (3) four decisions only the lead can make (ethics statement, funding and conflicts, registration, licence).

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
| 23 | Software libraries | sybil package version, torch 1.13 (TF32 off), numpy, pandas | have |
| 24 | Initialisation of parameters | N/A for Sybil (published weights); forms: logistic fit | write |
| 25 | Training approach | forms only (X10) | have |
| 26 | Selection of the final model | X10: fixed before test | have |
| 27 | Ensembling | Sybil's 5-member ensemble (as published) | write |
| 28 | Performance metrics | AUROC, calibration, sensitivity, specificity, PPV, rates per 1,000 | have |
| 29 | Significance and uncertainty | participant bootstrap, Holm (frozen) | have |
| 30 | Robustness or sensitivity analysis | X7, X9, X11 | have |
| 31 | Explainability methods | shared axes of `pooled`, attention (H6, R3, X11) | have |
| 32 | Evaluation on internal data | dev / test | have |
| 33 | Testing on external data | LIDC-IDRI (X5); O2 never-used; partner kit (planned) | have / planned |
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
