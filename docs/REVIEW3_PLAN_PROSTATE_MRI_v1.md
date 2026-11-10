# Third review: PLAN_PROSTATE_MRI_v1 revision 3 (2026-11-10)

For Shayan and his agent. Revision 3 adopts Q1 and Q2 well; the refinements, especially the label-blind visual check and the agreement of both zone masks, improve on the review. This is a desk review of revision 3 only. There are three points, and all of them are decisions to fix before M1 at no cost.

## T1. Choosing ProFound weakens what M5 can confirm. Fix the tie-break now
- **ProFound saw all 1,500 PI-CAI images, sealed half included.** Under leak rule 2, any confirmatory claim from it needs an external cohort it never saw. The two candidates may not serve:
  - QIN-Prostate-Repeatability is a TCIA collection, and ProFound's 863 TCIA cases are not named.
  - Prostate158 is small: 139 cases, so the SE of an external AUROC is about 0.04 or more.
  - If neither cohort has PSA, prostate volume and PI-RADS, then C3 (the clinical increment) cannot be tested externally at all.
- **Proposed rule, fixed before M1:** prefer the best unexposed encoder (MRI-CORE or SAM). Choose ProFound only if it beats that encoder by ≥ 0.02 token AUROC, with the lower CI > 0, on the M1 contrast against R.
- **If ProFound is chosen:** state now that C3 will read "within PI-CAI; the encoder saw the images", unless M0 finds an external cohort that has the clinical variables.

## T2. Intensity scaling: one rule, with no per-slice min–max
**The contradiction.** §2 step 2 says "fixed ADC windows and per-scan percentile scaling", but the MRI-CORE row says "scaled to [0, 1] per slice". If per-slice min–max is applied:
- absolute ADC is lost, and low ADC is the main csPCa sign;
- slices of one study are scaled differently;
- R keeps physical ADC, so the M1 gate would lean towards R because of preprocessing.

**Proposed:**
- **MRI-CORE, SAM and the untrained null:** [0, 1] = a fixed linear map of the windowed values. ADC uses a fixed physical window; T2W and HBV use per-study percentiles. The same constants apply to every slice of a study.
- **ProFound:** its native normalisation, with the exact transform recorded.
- **Sensitivity only:** per-slice min–max.

## T3. The M1 gate picks the best of about 6 encoder–mode arms on the same folds
- The gate's estimate is the maximum over the arms, so it is optimistic.
- **Proposed:** choose the arm on folds 1–3, then evaluate the gate (≥ 0.03 over R, lower CI > 0) on folds 4–5. Alternatively, use a bootstrap CI of the maximum.
- M5 still confirms, but this keeps M1's stop or go honest.
