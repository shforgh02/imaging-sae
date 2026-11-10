# Reply to the review of PLAN_PROSTATE_MRI_v1 (2026-11-10)

This replies to `docs/REVIEW_PLAN_PROSTATE_MRI_v1.md`. The changes are in revision 2 of `docs/PLAN_PROSTATE_MRI_v1.md`.

We checked every fact against the PI-CAI clinical sheet ourselves, at `picai_labels` commit `ce4a472` (2026-07-13), `marksheet.csv` SHA256 `23EAB237…72CF0AE`. No images were used.

**Summary.**
- All facts in the review are correct. All six changes are adopted; R1, R2, R3c and R6 are taken further.
- The biggest change comes from R1: the primary clinical population is now the **biopsy cohort** (verified, PI-RADS ≥ 3).

## 1. Facts: review vs our recomputation
| Fact | Review | Ours |
|---|---|---|
| Studies without histopathology | 468 (31%), all negative, highest PI-RADS ≤ 2 (425 × PI-RADS 2, 43 × PI-RADS 1) | Same (31.2%) |
| Share of negatives decided by the radiologist's read | 44% | 43.5% (468 of 1,075) |
| Verified studies | 1,032 (425 positive, 607 negative) | Same |
| Centre: verified share / prevalence | PCNN 100% / 0.31; RUMC 61% / 0.30; ZGT 56% / 0.23 | PCNN 100% / 0.31; RUMC 61% / 0.29; ZGT 56% / 0.23 |
| Studies with an ISUP-1 lesion (csPCa-negative) | 282 (228) | Same |
| Missing PSAD / PSA / volume | 30.1% / 2.7% / 1.8% | Same |

**Added by us:**
- PSAD is missing for **99% of PCNN** (RUMC 7%, ZGT 13%).
- Where all three values exist, the reported PSAD is within 5% of PSA ÷ volume for only 73% of studies. It is rounded to 2 decimals.
- Recomputing PSAD leaves 3.5% missing.
- PI-RADS is complete.
- 23 patients have more than one study.
- The verified studies are 580 targeted biopsies, 217 systematic, 210 both, and 25 prostatectomies.
- **Biopsy cohort** (verified, PI-RADS ≥ 3): 884 studies, 417 positive, 467 negative.

## 2. Point by point
**R1 (PI-RADS is part of the reference standard): agree, and taken one step further.**
- Restricting the PI-RADS model to verified studies removes the 468 negatives that PI-RADS itself decided.
- But the verified set still mixes in 148 men with PI-RADS ≤ 2 who were biopsied anyway, for other reasons.
- So revision 2 makes the **biopsy cohort** primary: men with PI-RADS ≥ 3 who had a biopsy. Reasons:
  - every case is biopsy-proven;
  - PI-RADS is a fair covariate there, not part of the outcome;
  - it is the real clinical decision: 53% of these biopsies found no csPCa.
- All verified studies and all studies are reported as secondary analyses.
- In M1 the gate must pass on all studies **and** on verified studies.

**R2 (the M3 gate against controls): agree, with two additions.**
1. **Equal capacity.** Every patient score, whether SAE, best baseline decomposition, intensity reference R or texture, is a logistic model of at most 5 of that method's features. A dense model on R's 80-odd features against 5 SAE features would not be like for like.
2. **Two levels of claim:**
   - C3a: non-inferior to R and texture, with margin 0.03 (v1's H4 margin). We use 0.03 rather than 0.02 because, with dev precision (SE about 0.015), 0.02 fails even for truly equal scores.
   - C3b: superiority over R ("beyond known intensity signs"). It is tested at M5 only if dev shows a difference of at least +0.02.
- We also state the power limit: the sealed biopsy cohort (about 440 studies, about 210 positive) can confirm only differences of about 0.035–0.045 AUROC or larger.

**R3 (token labels and units): agree.**
- (a) Partial tokens (0 < occupancy < 0.5) are excluded.
- (b) Clean-normal sensitivity analysis: no ISUP-1 lesion and PI-RADS ≤ 2.
- (c) Made into a rule: the largest of 8, 6 or 4 mm tokens that gives ≥ 90% lesion recall, chosen from the dev masks before any model runs. If none reaches 90%, 4 mm is used and the recall is reported. Smaller tokens are reached by resampling the input.
- (d) Patient-equal weighting, with cluster bootstrap.

**R4 (centre as confounder): agree.** Within-centre and leave-one-centre-out results in M1 and M3, as descriptive outputs. They don't gate, because the smallest centre gives wide CIs. Folds are stratified by centre × outcome group (csPCa / verified negative / unverified negative).

**R5 (like for like, and expectations): agree.**
- The same validity rule for every method and for the untrained null.
- The wording rule is fixed now: "SAE features" only if the SAE's best matched held-out lesion AUROC beats the best baseline's with CI > 0; otherwise "foundation-model features".
- The centred smoothing control is used from the start.
- The best baseline decomposition's score also goes through M3.
- Expectation stated: parity on lesion AUROC is likely (as on CT); any edge is more likely in stability.

**R6 (PSAD): agree, changed.** We do not fill the gaps; we recompute PSA ÷ volume for every study. Filling only the gaps would mix the rounded reported values with exact recomputed ones, and the mix would differ by centre, since almost all of PCNN would be recomputed. The reported PSAD becomes a sensitivity analysis. The remaining 3.5% are left out of the PSAD models (complete-case), with counts by centre.

**§3 answers:**
- **Bias-field perturbation:** added to the M2 stability tests.
- **External cohorts** (Prostate158; QIN-Prostate-Repeatability for test–retest): added to M0 as checks of overlap and licence.
- **Briefing wording:** corrected. Against ICA, the SAE's edge is also reproducibility (median twin score 0.55 vs 0.19).
