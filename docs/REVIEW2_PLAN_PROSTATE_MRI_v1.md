# Second review: PLAN_PROSTATE_MRI_v1 revision 2 (2026-11-10)

For Shayan and his agent. Revision 2 and the reply adopt R1–R6 well. The biopsy cohort is a good primary population, and since every PI-RADS ≥ 3 study was biopsied, it carries no selection by verification.

**Sources** (`picai_labels` at the pinned commit `ce4a472`):
- the git tree, which lists the label files;
- `marksheet.csv`.

No images were used. There are two new points; both are checks in M0 and cost $0.

## Q1. The lesion annotation source is confounded with centre
The 425 csPCa masks come from two expert sources: `human_expert/resampled` (220) and `Pooch25` (205). By centre:

| Centre | Pooch25 | resampled |
|---|---|---|
| PCNN | 0 | 109 |
| RUMC | 125 | 111 |
| ZGT | 80 | 0 |

The source also tracks the biopsy type and the year:
- systematic + targeted biopsy: 109 Pooch25 vs 1 resampled;
- 2014–2015: Pooch25 only;
- 2012: resampled only.

**Why it matters.** Annotators and protocols differ in how tight their outlines are. That changes the occupancy-based token labels, the token-size rule (lesion recall) and every token-level AUROC, and it does so by centre.
- The leave-one-centre-out result for ZGT tests on Pooch25 masks only, and the one for PCNN on resampled masks only.
- Patient-level csPCa (M3) is unaffected, because it comes from the marksheet.

**Proposed (M0):**
- Record the annotation source for each positive.
- **Compare the sources within RUMC,** the only centre that has both, so centre does not enter the comparison:
  - lesion volume per ISUP grade;
  - token occupancy;
  - lesion recall at each candidate token size.
- Apply the token-size rule to each source separately and use the stricter result.
- Report token-level AUROCs (M1, M2) by source within RUMC.
- **If the sources differ materially** (fix the threshold in the M0 protocol, e.g. a median volume ratio outside 0.8–1.25), call token-level results across centres annotation-dependent, and let patient-level M3 carry the clinical claim.

## Q2. Use the zonal masks and the second gland mask
The pinned commit also has:
- AI zonal PZ/TZ masks for all 1,500 studies (`zonal_pz_tz/AI/HeviAI23`, `Yuan23`);
- a second AI whole-gland mask (`whole_gland/AI/Guerbet23`).

**Zone.** Normal ADC and T2 values differ between PZ and TZ, and PI-RADS uses a different dominant sequence in each zone.
- Add the zone (PZ / TZ / boundary) to the intensity reference R.
- Report token AUROCs within each zone.
- Otherwise a feature that only tells PZ from TZ can look like a lesion feature, and R stays weaker than a radiologist's reading.

**Label-blind gland QC.** For every dev case, compute the Dice agreement between Bosma22b and Guerbet23 (gland) and between HeviAI23 and Yuan23 (zones). Fix the fix-or-exclude rule on that agreement (e.g. gland Dice < 0.8 → visual check). This covers every case, not only the 20 reviewed by eye, and never looks at cancer labels.
