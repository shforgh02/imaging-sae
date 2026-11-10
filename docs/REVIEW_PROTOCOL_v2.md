# Review of Stage 1a and the draft SAE_PROTOCOL_v2 (2026-11-10)

For Shayan and his agent. This is a desk analysis of the committed per-feature tables (`imgsae/exploratory/v2_ct/results/tables/*.csv.gz`, reps 0–2, 'neutral' rule). Nothing was refitted.
- **Recomputation.** v = min(t, sel, r_pert) on features that pass V0, are not chimeric, are gated and are not 'other'. Area = the mean over τ ∈ {0.50, …, 0.90} of (the number of concepts with max v ≥ τ) / 32. 'Matched' = 20 random subsamples of 425 features.
- **Check.** This reproduces `area_neutral` in s1a_*.json exactly, and the matched areas within subsampling noise.

**Verdict.**
- Stage 1a was run cleanly: the sanity rows are exact, G1 was fixed before running, and the deviations are logged.
- The SAE advantage is real, robust, and about **+0.10**, not +0.25.
- The rest of the headline comes from an asymmetry in the matched-425 rule, and that asymmetry also carries H3c and H2b.
- Fix it before registration (P1–P3). All fixes are on dev data and cost about $0.

## 1. Findings
**F1. The matched-425 rule favours the consensus.**
- The consensus has about 408 features, fewer than 425, so it is never subsampled. Every 1,024-feature method loses 58% of its features at random.
- The consensus vote is therefore a label-free feature selection that no baseline gets.
- (mean − boundary) / SD is given in brackets. A pass needs about 2.4–3.3 (protocol §9).

| Contrast (dev mean, 3 reps) | Matched 425 (as drafted) | All features |
|---|---|---|
| H2: consensus − best baseline | +0.252 (6.0) | +0.124 (2.3) |
| Single SAE − best single baseline | **+0.101 (7.1)** | +0.106 (2.7) |
| H3: consensus − single | +0.150 (5.3) | **+0.019** (1.3) |
| H2b: consensus − physics consensus, margin 0.05 | +0.209 (4.5) | +0.146 (2.3) |
| Single SAE − physics single, margin 0.05 | +0.064 (0.9) | +0.057 (0.2) |

- **A label-free stand-in for consensus lifts every method.** Keeping each method's 425 features with the highest twin score t gives:
  - single SAE 0.528 (consensus: 0.549);
  - k-means 0.370 (from 0.293);
  - ICA 0.424 (from 0.274).
- **So:**
  - H3c's coverage gain is an artifact of the rule.
  - H2b passes only in the asymmetric form.
  - The physics consensus is *worse* than the physics single fit at all features (0.403 vs 0.473), because its config is untuned for 74-dimensional input.

**F2. The SAE's edge is robustness to the shift, not selectivity or reproducibility.** Area with one link removed (all features):

| Method | sel only | min(sel, r_pert) | min(sel, t) | full v |
|---|---|---|---|---|
| SAE single | 0.894 | 0.792 | 0.554 | 0.530 |
| k-means | 0.830 | 0.520 | 0.528 | 0.382 |
| ICA | 0.811 | 0.544 | 0.454 | 0.424 |
| physics SAE | 0.667 | 0.649 | 0.475 | 0.473 |

- **Where the methods differ.** Among selective features (sel ≥ 0.7, passing the validity gates):

  | Method | Median r_shift | Median r_noise |
  |---|---|---|
  | SAE | 0.84 | 0.96 |
  | k-means | 0.63 | 0.89 |
  | ICA | 0.31 | 0.76 |
  | raw channels | 0.46 | |
  | oracle | 0.86 | |
  | untrained SAE | 0.18 | |

- **Where they don't.** The share of these features with t ≥ 0.7 is similar: 27% for the SAE, 21% for k-means.
- **This explains T6.** On selectivity alone the SAE's edge is small, and that is what k = 1 probing measures.
- **What the shift test is.** It moves the volume by +8 voxels in z and x, then re-samples the grid by averaging 2×2 neighbouring token embeddings (`scripts/p1_encode.py:57`). So r_shift mixes translation with spatial smoothing. One perturbation, on 20 scans, carries most of H2.

## 2. Changes proposed before registration
- **P1. Make H2 symmetric.** Primary: single SAE vs the best single baseline, matched 425. All five baselines and the SAE have 1,024 features, so the subsampling hits every method equally. Dev: +0.101, SD 0.014. The consensus enters H3 only.
  - Optional dev check on CPU: run the same 5-fit cannot-link consensus on the k-means and ICA codes. For ICA this is ICASSO, the standard. If either consensus beats its own single fit, add consensus candidates to every family and compare family-best with family-best.
- **P2. H3.**
  - Non-inferiority of the consensus vs the single fit, on coverage *at all features*. Dev: +0.019; (0.019 + 0.05) / 0.014 ≈ 4.9.
  - Plus R1 superiority, as drafted.
  - Drop H3c.
  - Claim: "the same coverage with 40% of the features, and more reproducible".
- **P3. H2b becomes descriptive (m = 3).** Like-for-like, the dev gain is +0.06 against a 0.05 margin, so it would fail. The drafted form passes mainly through F1. Report the beyond-physics gaps for each link: selectivity-only 0.894 vs 0.667, and k = 1 vertebral level.
  - If "beyond physics" must be confirmatory, first tune the physics SAE on the same rep-0 grid (8 singles, about $1 on Modal), then test single vs single.
- **P4. Pre-register the F2 decomposition as key secondaries:**
  - the areas with each link removed;
  - the medians of r_shift, r_noise and r_huoff among selective features.

  Word H2's claim to match: "as selective and as reproducible as k-means and ICA, and more stable under sub-token shift and noise".
- **P5. Smoothing control for r_shift** (CPU, no encodes, minutes). Apply the same 2×2 neighbour averaging to the *unperturbed* embeddings and score r_interp for every method.
  - If the baselines' r_interp ≈ their r_shift, the SAE's edge is spatial smoothness, not translation robustness. Word the claim accordingly.
  - Fix this reading before unsealing.

**Unchanged:**
- D2: H5 descriptive;
- D3: laptop;
- D4: 20 scans;
- D6: skip;
- E1–E5 and checks C1–C5;
- J = 10 and Holm.

**New family {H2 (P1), H3 (P2), H1}.** The dev ratios are 7.1, 4.9 / 10.3 and 10.1, all comfortable. The H1 null as drafted (θ ≥ 0.75) is near-certain to be rejected (dev 0.653, SD 0.010). Also report whether its CI excludes 0.5 (t is informative but inadequate).
