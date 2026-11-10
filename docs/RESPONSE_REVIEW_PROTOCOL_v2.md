# Reply to the review of Stage 1a and SAE_PROTOCOL_v2 (2026-11-10)

This replies to `docs/REVIEW_PROTOCOL_v2.md`. The changes are in revision 2 of `docs/SAE_PROTOCOL_v2.md`. Nothing was refitted: every number below comes from the committed `v2_ct/results/s1a_*.json` and the per-feature tables (dev, reps 0–2, 'neutral' rule).

**Summary.**
- We agree with the main finding (F1) and its consequence: the SAE's advantage is about +0.10, not +0.25.
- P1, P2, P3 and P5 are adopted, the latter two with refinements. P4 is adopted without the fixed claim sentence. H1 is tightened as suggested.
- A few of the review's numbers use a different rule for missing twin scores (§1).

## 1. Independent recomputation
| Quantity | Review | Ours |
|---|---|---|
| Consensus − best baseline, 425 features | +0.252 (6.0) | +0.254 (5.6) |
| Consensus − best baseline, all features | +0.124 (2.3) | +0.123 (2.3) |
| Single SAE − best baseline, 425 features | +0.101 (7.1) | +0.104 (6.4) |
| Single SAE − best baseline, all features | +0.106 (2.7) | +0.104 (2.6) |
| Consensus − single, all features | +0.019 | +0.019 (4.9 against the −0.05 boundary) |
| Consensus − physics consensus, 425 features, margin 0.05 | +0.209 (4.5) | +0.202 (4.0) |
| Consensus − physics consensus, all features, margin 0.05 | +0.146 (2.3) | +0.146 (2.3) |
| Single SAE − physics single, 425 features, margin 0.05 | +0.064 (0.9) | **+0.044 (−0.4)** |
| Single SAE − physics single, all features, margin 0.05 | +0.057 (0.2) | **+0.035 (−0.5)** |
| Top 425 features by twin score: SAE / k-means / ICA | 0.528 / 0.370 / 0.424 | 0.528 / 0.370 / 0.424 |
| Links, SAE: sel / min(sel, r_pert) / min(sel, t) / v | 0.894 / 0.792 / 0.554 / 0.530 | same |
| Links, k-means | 0.830 / 0.520 / 0.528 / 0.382 | same |
| Links, ICA | 0.811 / 0.544 / **0.454** / 0.424 | 0.811 / 0.544 / **0.509** / 0.426 |
| Links, physics SAE | 0.667 / 0.649 / **0.475 / 0.473** | 0.667 / 0.649 / **0.502 / 0.495** |
| Median r_shift / r_noise of selective features | SAE 0.84 / 0.96; k-means 0.63 / 0.89; ICA 0.31 / 0.76 | SAE 0.84 / 0.96; k-means 0.62 / 0.89; ICA 0.31 / 0.76 |
| Share of selective features with t ≥ 0.7 | SAE 27%, k-means 21% | SAE 27%, k-means 21%, ICA 21% |

**Where the numbers differ:**
- **Missing twin scores.**
  - Production v (`p1_fit.feature_table`) takes the minimum with `np.fmin`, which skips a missing twin score. The review counted it as 0.
  - A twin score is missing when the feature fires on fewer than 0.1% of its own half's evaluation tokens. That happens for 2.7% of ICA's features that enter v, 0.8% of the physics SAE's and 0.1% of the SAE's.
  - With the review's rule we reproduce 0.454, 0.475 and 0.473 exactly.
  - Revision 2 keeps the frozen rule and adds the review's rule as sensitivity analysis S5.
- **The like-for-like beyond-physics gap** is therefore smaller than the review states: +0.044 at 425 features and +0.035 at all features. This strengthens P3.
- **H3 ratios.** The review's ratios for consensus vs single (5.3 at 425 features, 1.3 at all features) are measured against 0. Against the −0.05 non-inferiority boundary they are 6.9 and 4.9; P2 already uses 4.9.
- **425-feature values** differ by up to 0.007, which is consistent with different subsampling draws.

## 2. Point by point
**F1: agree.**
- It was already visible in Stage A: at all features the consensus and the single fit tie (0.562 vs 0.561).
- Revision 1's H3c (coverage superiority) measured only this artifact. It is dropped.

**F2: agree, with one qualification.**
- **Against k-means,** the SAE's edge is almost all in r_pert:
  - selectivity only: +0.064;
  - min(sel, r_pert): +0.273;
  - min(sel, t): +0.025;
  - median t of selective features: 0.55 vs 0.57.
- **Against ICA,** the SAE is also far more reproducible per feature: median t 0.55 vs 0.19 (+0.32 to +0.39 in every rep), and min(sel, t) +0.045.
- So "the edge is robustness, not reproducibility" holds against k-means but not against ICA.
- **Physics consensus below the physics single fit** at all features (0.403 vs 0.495): part of this is feature count (about 640 vs 1,024 features in an all-feature area). The untuned config may add to it, but that is not shown.

**P1: adopted.** H2 is now the single SAE against the best single-fit baseline. All arms have 1,024 features; dev +0.104 (6.4 SDs).
- The optional consensus for k-means and ICA is listed as a descriptive dev check (D8), not as a rule that could change H2. Two reasons:
  - no hypothesis compares a consensus with a baseline any more;
  - a family-best comparison on the 425-matched metric would bring F1 back, unless the metric changed too.
- If run, the check is judged at all features and on R1.

**P2: adopted, with one wording change.** Non-inferiority shows "within 0.05", not "the same coverage". The claim becomes: "coverage within 0.05 of a single fit, with about N% of the features (dev 39%), and more reproducible".

**P3: adopted.** H2b is descriptive (K6). If the lead wants it confirmatory, the physics SAE is first tuned on the same 8-config grid (budgeted as `conf_phys_tune`), then single is tested against single. On dev (untuned) that gives −0.4 SDs at margin 0.05 and 2.9 at margin 0.

**P4: adopted as K1 and K2, without the fixed sentence.** "As selective and as reproducible as k-means and ICA" is not what the dev data show:
- the SAE's selectivity-only area is higher than both in every rep (+0.050 to +0.073 vs k-means; +0.073 to +0.099 vs ICA);
- per feature, it is much more reproducible than ICA;
- "as … as" would need an equivalence test.

Revision 2 fixes directional wording rules instead: under W1, a link is named only when its contrast's CI excludes 0.

**P5: adopted as K3, with two changes.**
1. **Centring.**
   - The shift test's 2 × 2 average is centred on the original token: shifted tokens i and i+1 sit half a token on either side of it.
   - The same 2 × 2 average of *unperturbed* tokens is centred half a token off in z and in x, so it mixes smoothing with a displacement.
   - Revision 2 adds a centred smoothing, with weights (1/8, 3/4, 1/8) along z and x and the same variance (¼ token² per axis). It uses that version for the reading rule W2: δ ≤ 0.10 for both k-means and ICA leads to the "interpolation" wording. The review's version is reported next to it.
2. **Cost.** The dev models were not saved, so the dev values need refits. These are part of checks C2 (Modal, inside its existing budget) and C3 (laptop), so the step is not just minutes of CPU.

In both versions the smoothing is applied to the raw CT-FM embeddings, before the input transform, as in the shift encode. Only tokens whose neighbours are valid tokens are used.

**H1: adopted.** It is now one test of 0.5 < θ < 0.75: an intersection–union test that uses one Holm slot. Dev: 15.9 SDs above 0.5 and 10.1 below 0.75.

**Unchanged items** (D2, D3, D4, D6, E1–E5, C1–C5, J = 10, Holm): agreed. The new family is {H2, H3, H1}.

## 3. Still open for the lead
D3–D8 in revision 2 §0, and the Modal budgets: about $15.7 expected, with caps totalling $22.00.
