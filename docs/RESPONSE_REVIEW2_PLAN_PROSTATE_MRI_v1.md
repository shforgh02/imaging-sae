# Reply to the second review of the MRI plan (2026-11-10)

This replies to `docs/REVIEW2_PLAN_PROSTATE_MRI_v1.md`. The changes are in revision 3 of `docs/PLAN_PROSTATE_MRI_v1.md`, which also changes the encoders (see its header).

We checked both points against `picai_labels` at commit `ce4a472`, using the full git tree (10,325 files) and `marksheet.csv`. No images were used.

**Summary.** Both points are correct and both are adopted, with four refinements.

## 1. Facts: review vs our recomputation
| Fact | Review | Ours |
|---|---|---|
| Outline source by centre (Pooch25 / resampled) | PCNN 0 / 109; RUMC 125 / 111; ZGT 80 / 0 | Same. Each positive is in exactly one source; none in both, none in neither |
| Systematic + targeted biopsy, by source | 109 / 1 | Same |
| Years | 2014–2015 Pooch25 only; 2012 resampled only | Same. Also 2011 and 2013 are resampled only, and 2021 is Pooch25 only |
| Zone and second gland masks | `HeviAI23`, `Yuan23`, `Guerbet23` for all 1,500 | Same (1,501 files each, including a README) |

**Added by us: the case mix also differs by source.** ISUP 5 is 34 of 205 cases (17%) in Pooch25, against 18 of 220 (8%) in resampled. So outline sizes must be compared within ISUP grade, as the review proposes, and not pooled.

## 2. Point by point
**Q1 (outline source tied to centre): adopted.**
- The source of each positive is recorded.
- Within RUMC, the sources are compared on lesion volume per ISUP grade, token occupancy and lesion recall.
- The token-size rule is run per source, and the **smaller** of the two sizes is used.
- Token AUROCs are reported by source within RUMC.
- The materiality rule is fixed: if the ISUP-matched median volume ratio is outside 0.8–1.25, cross-centre token-level results are labelled annotation-dependent, and the clinical claim rests on patient-level M3.
- The leave-one-centre-out caveat is stated next to those results.

**Refinement 1.** The M1 and M2 gates are contrasts on the same tokens and labels: an encoder minus R, or minus the untrained network. An outline-source effect moves both arms together, so the gates stay valid. Only absolute token AUROCs are annotation-dependent. The plan now says this.

**Refinement 2.** Within RUMC, the two sources still differ in year and in biopsy type. So the within-RUMC comparison removes centre, but not all confounding. This is reported as a limitation.

**Q2 (zones and the second gland mask): adopted.**
- Zone (PZ / TZ) enters the intensity reference R, and token AUROCs are reported within each zone.
- Gland and zone QC is done for every dev case from the agreement of the two AI masks: gland Dice < 0.8, or mean PZ/TZ Dice < 0.7, triggers a visual check.

**Refinement 3.** A token's zone is PZ or TZ only where **both** zone models agree on the majority zone; otherwise it is "zone uncertain". This uses both masks, rather than trusting one.

**Refinement 4.** The visual check shows T2W with the gland and zone outlines only, **never the lesion masks**. It decides between keeping Bosma22b, using Guerbet23, or excluding the case. This keeps the QC label-blind in practice, not only in its trigger.
