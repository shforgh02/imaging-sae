# Review of PLAN_PROSTATE_MRI_v1 and the reviewer briefing (2026-11-10)

For Shayan and his agent.

**Sources:**
- the plan and the briefing;
- the PI-CAI clinical sheet, `picai_labels` main, `clinical_information/marksheet.csv`, with 1,500 rows. All numbers below come from it.

Nothing else was run.

**Verdict.** The pivot is sound, and the plan carries over the CT lessons (leak rule, probe before the SAE, sealed half, like-for-like comparisons). Six changes are needed before the M0–M1 protocol is written; three of them come from the label sheet.

## 1. Facts from the marksheet
- **468 of the 1,500 studies (31%) have no histopathology.** All of them are negative with a highest PI-RADS of ≤ 2 (425 with PI-RADS 2, 43 with PI-RADS 1).
  - So 44% of the negatives are negative because of the radiologist's own read.
  - Every positive is verified by biopsy or prostatectomy.
- **By centre:**

  | Centre | Verified share | csPCa prevalence |
  |---|---|---|
  | PCNN | 100% | 0.31 |
  | RUMC | 61% | 0.30 |
  | ZGT | 56% | 0.23 |

- **282 studies have an ISUP-1 lesion,** and 228 of these are csPCa-negative. The masks cover ISUP ≥ 2 lesions only, so ISUP-1 cancer sits inside the "normal prostate" tokens.
- **`psad` is missing in 30.1% of studies,** `psa` in 2.7% and `prostate_volume` in 1.8%.

## 2. Changes
**R1. PI-RADS is part of the reference standard (M3, model b).**
- Because PI-RADS defines 468 of the negatives, its AUROC is inflated, and any SAE increment over it is biased towards 0.
- Primary for model (b): the histology-verified studies only (1,032 studies; 425 positive, 607 negative). Report all studies as a sensitivity analysis.
- Also report the M1 and M3 AUROCs on verified studies only. The unverified negatives are an easy spectrum, selected by the radiologists.

**R2. The M3 gate must be set against the controls.**
- "Increment over PSAD + age + volume with lower CI > 0" passes for almost any image score; mean gland ADC would pass it.
- Gate instead on the SAE increment minus R's increment, and minus the texture baseline's increment (non-inferior or better, as in v1's H4). Run the best baseline decomposition's lesion score through the same pipeline.

**R3. Token labels and units.**
- (a) State explicitly that tokens with 0 < lesion occupancy < 0.5 are excluded, not counted as normal.
- (b) Sensitivity analysis: take normal tokens only from studies with no ISUP-1 lesion and no PI-RADS ≥ 3 lesion (§1).
- (c) Fix the crop scaling and token size in M0 so that small lesions survive. Report lesion recall (the share of csPCa lesions with ≥ 1 token at occupancy ≥ 0.5) and aim for ≥ 90%.
- (d) Weight each patient equally in token AUROCs, and use patient-cluster bootstrap CIs. Pooled tokens let large lesions dominate.

**R4. Centre is a confounder.** Verification and prevalence differ by centre (§1).
- Report within-centre AUROCs and leave-one-centre-out results in M1 and M3.
- Fold stratification by centre alone is not enough.

**R5. In M2, compare like for like, and set expectations from CT.**
- On CT the SAE had no single-feature advantage (vertebral level −0.007, lobe −0.040). Its edge was shift and noise stability, and, against ICA, reproducibility.
- M2's held-out lesion AUROC is the same single-feature measure, so expect parity there.
- Apply the identical validity rule to every baseline and to the untrained null.
- Say "SAE features" only if the SAE beats the best baseline like for like. Otherwise say "FM features". Fix which before M2 runs.
- Use the centred smoothing control (CT K3) for the shift test from the start.

**R6. PSAD.** Where `psad` is missing, recompute it as PSA / volume, in M0 and before any model. This should take missing values from 30% down to a few %.

## 3. Short answers to briefing §5
1. **M1 gate:** good as a stop rule. Compute it patient-weighted (R3d), on all studies and on verified studies (R1).
2. **M2 rule:** reasonable thresholds. Add R3a and R5. For scale, on CT only 27% of selective SAE features reached t ≥ 0.7.
3. **M3:** R1, R2 and R6.
4. **Encoders:** nothing to add without the leak check.
5. **Preprocessing:** R3c. For stability, use the centred smoothing control. An MRI-specific option is a bias-field perturbation.
6. **External validation** (candidates, not checked here):
   - Prostate158 (Charité; biparametric MRI with lesion masks; outside PI-CAI's Dutch centres);
   - for a true test–retest stability check, QIN-Prostate-Repeatability (TCIA).

   Verify overlap and licence in M0.
7. **Briefing wording:** "Where the SAE wins: mainly stability" holds against k-means. Against ICA it is also reproducibility (median t 0.55 vs 0.19), per `RESPONSE_REVIEW_PROTOCOL_v2.md`.
