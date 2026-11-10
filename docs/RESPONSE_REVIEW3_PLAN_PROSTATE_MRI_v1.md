# Reply to the third review of the MRI plan (2026-11-10)

This replies to `docs/REVIEW3_PLAN_PROSTATE_MRI_v1.md`. The changes are in revision 4 of `docs/PLAN_PROSTATE_MRI_v1.md`.

**Summary.** All three points are correct and adopted. T1 and T2 are taken as proposed, with small additions. For T3 we keep the aim, but use nested cross-validation instead of the 3/2 fold split, for the reason given below.

## T1. ProFound tie-break: adopted
We checked the two external candidates at their sources:
- **Prostate158** (`github.com/kbressem/prostate158`): 139 public cases plus 19 hidden test cases, with zones and histology-verified lesion masks. **No clinical variables are listed** (no PSA, volume or PI-RADS). The repo licence is MIT; the data licence is to be checked on Zenodo.
- **QIN-Prostate-Repeatability** (TCIA): **15 patients** (30 studies), test–retest. It is a TCIA collection, so it may be among ProFound's unnamed 863 TCIA cases.

So the review's concern holds. If ProFound were chosen, C3 could not be tested outside PI-CAI with the known cohorts.

**Adopted as rule S:**
- U = the best unexposed arm (MRI-CORE or SAM).
- ProFound is chosen only if it beats U by ≥ 0.02 token AUROC on the contrast against R, with lower 95% CI > 0.
- If it is chosen, C3 reads "within PI-CAI; the encoder saw the images", unless M0 finds a public cohort outside PI-CAI and ProstateX with PSA, volume and PI-RADS.

**Added:**
- M0 searches for such a cohort.
- QIN-Prostate-Repeatability is used only for test–retest stability, and only for unexposed encoders unless the overlap is ruled out.

## T2. One intensity rule: adopted
We confirm the contradiction: revision 3 said both "per-scan percentile" (§2) and "per slice" (the MRI-CORE row). Revision 4 has one rule:
- **ADC:** a fixed physical window, by default 0–3,000 × 10⁻⁶ mm²/s, mapped to [0, 1] with clipping. The units are confirmed in M0 from the value range, without labels.
- **T2W and HBV:** the per-study 0.5th and 99.5th percentiles of the crop.
- The same constants apply to every slice of a study.
- **ProFound:** its native normalisation, with the exact transform recorded.
- **Per-slice min–max:** a sensitivity analysis only.

**Added: a caveat.** MRI-CORE was pretrained on slices scaled by per-slice min–max, so fixed-window input is a small shift away from its training data. The sensitivity analysis shows whether that matters. It is reported, but it can never switch a gate or a selection, so preprocessing cannot be tuned towards a result.

## T3. Selection optimism in M1: adopted, with a different fix
The concern is right: taking the best of 5 arms on the same folds inflates the gate. But the proposed split (select on folds 1–3, gate on folds 4–5) would leave only about 40% of the dev half for the gate, which is about 85 positive studies. The gate's CI would then be so wide that a real difference of about 0.05 could still fail.

**Nested cross-validation** solves both problems:
- In each of the 5 outer folds, rule S is applied using cross-validation on the other 4 folds only.
- The chosen arm, R and the untrained network are refit there and scored on the held-out fold.
- The gate is computed on the pooled held-out scores, with patient-cluster bootstrap CIs.

So the selection never sees the data it is judged on, and every dev patient counts. The arm used from M2 on is chosen by rule S on the full dev cross-validation. If the outer folds chose different arms, this is reported, and the gate then refers to the selection procedure.

The extra cost is CPU time on the laptop only:
- the nested loop: 5 outer folds × (4 inner folds × 6 models [5 arms + R], plus 3 refits) = 135 fits;
- the final selection on the full dev half: 5 folds × 7 models = 35 fits.

That is about 170 logistic fits, a few hours.
