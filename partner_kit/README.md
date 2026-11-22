# Partner kit v1.0 — independent check of the Sybil lung-cancer risk model on your own data

**What it is.** A small, offline Python program that your team runs inside your institution. It compares Sybil (Mikhael et al., *J Clin Oncol* 2023) with a 14-item model of the radiologist's structured findings that was frozen on public NLST data, and it measures how often your CT series have overlapping slices (the condition under which Sybil places slices at the wrong distance). It returns **one file of aggregate numbers**, which you review before deciding to share it. No patient-level data, identifier, date, free text or file path leaves your site.

**What it is not.** Not a medical device; not for clinical decisions; research use only. It does not run Sybil in v1.0: you provide Sybil's published 1-year and 6-year risks for each exam if you have already run Sybil (v1.1 will add an optional offline Sybil runner).

## Requirements
- Python 3.10 to 3.12 with `numpy` and `pandas` (`requirements.txt`); `pydicom` only for the geometry audit and the self-test. CPU only; no network; no GPU; no deep-learning library.
- Run time: a few minutes for tens of thousands of exams.

## Steps
1. `python run_partner.py --selftest --out test_output` — runs on synthetic data shipped with the kit and must print `PASS`.
2. Prepare your exam table (and, if you have one, your nodule table) as described in `CODING_SHEET.md`.
3. `python run_partner.py --compare exams.csv [--nodules nodules.csv] --out site_output --min-cell 10 --lung-rads-version 1.1 --diameter-type longest --cancer-ascertainment registry` (the last three describe your records; give what is true for your site, or leave them out)
4. Optional, outcome-free: `python run_partner.py --geometry <folder with your CT DICOM files> [--series-manifest series_sent_to_sybil.csv] --out site_output`
5. Review `site_output/TO_RETURN/SUMMARY_FOR_REVIEW.txt` (the full content of the file to share, with its SHA-256). Row-level warnings stay in `site_output/LOCAL_DO_NOT_SEND/` and are never shared.

## What is computed (`--compare`; fixed before any partner data are seen)
- Endpoints: cancer within 1 year of an exam (all screens; primary), within 1 year of a baseline screen, and within 6 years of a baseline screen (only when follow-up allows; at least `--min-cell` cancers and controls).
- AUROC of Sybil, of the frozen form P, of "Sybil + age, sex, smoking" (cross-fitted, 5 participant-grouped folds), of "P + Sybil" (cross-fitted), and of your recorded Lung-RADS if present; paired differences with 95% participant-bootstrap intervals (2,000 draws, seed 0), logit-AUROC standard errors and the bootstrap correlation of the two AUROCs (for meta-analysis); inverse-probability-of-censoring AUROC when more than 5% of exams are censored.
- Sybil's coefficient given P; calibration (observed / expected, calibration intercept and slope, Brier score) for **both** Sybil and P.
- Sensitivity, specificity, PPV, false alarms and missed cancers per 1,000 exams at (a) the NLST cuts frozen in `frozen/nlst_dev_cuts.json` ("transportability without local recalibration") and (b) 90% and 95% specificity on your cancer-free exams, re-estimated in every bootstrap draw ("discrimination at matched false-alarm workload").
- An aggregate case-mix table (age mean and SD, shares, follow-up median).
- **When the form is evaluated:** each form item is checked where it applies (nodule items on exams with a nodule ≥ 4 mm; growth and new nodule on repeat screens with one). If any item is less than 80% complete there, the form is not evaluated at your site and Sybil (and Lung-RADS) are analysed on all exams; no exam is dropped because a column is missing. Otherwise exams with a missing form item are left out of every comparison (their number is reported).

## Frozen files (`frozen/`, hashes in `MANIFEST.sha256`)
- `x10_portable_form_params.json`: the 14-item form (SHA-256 `106da977…`; the program refuses to run if it differs).
- `nlst_dev_cuts.json`: the NLST development-split cuts with their source.
- `selftest_expected.*`: the reference self-test output.

Questions go through the study lead who invited you. See `GOVERNANCE.md` for the one-page brief for your ethics, data-protection and IT offices, `OUTPUT_SCHEMA.md` for every field of the returned file, and `NOTICE.md` for third-party notices.
