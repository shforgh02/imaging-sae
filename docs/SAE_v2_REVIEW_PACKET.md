# Imaging SAE project: results so far and plan v2 (external review packet, 2026-11-09)

**Status:** final plan, sent for external peer review. No v2 work has started; implementation waits for the review.

This file is self-contained for external reviewers. Per-concept and per-replicate tables are in Appendix D. It covers:
1. the question and the pre-registered Phase 1 design;
2. the Phase 1 result (NO-GO);
3. post hoc checks;
4. Phase 1b Stage A diagnostics (exploratory);
5. what the new evidence means for the Phase 1 decision rules;
6. interpretation;
7. **plan v2** to restart the SAE paper;
8. limitations;
9. questions for reviewers.

A glossary is at the end. All numbers come from the project's result files (paths given); none are hand-copied estimates.

---

## 1. Question and pre-registered Phase 1 design (`docs/IMAGING_SAE_LEAN_v1.md`, rules fixed before running)

**Question.** On a real 3D CT foundation model (FM), do sparse autoencoder (SAE) features carry concept information that is:
- (a) technically feasible to extract;
- (b) **beyond intensity and position**;
- (c) better than simple baselines.

Alternatively, do they show a clean reproducibility-vs-validity dissociation? The answer decides whether a paper exists.

**Data.** TotalSegmentator v2: 1,228 CTs, 117 expert-reviewed masks per scan, CC-BY.
- Eligible: 705 scans whose study types cover thorax and/or abdomen, with the institute known.
- **150 development scans** were drawn at random (seed 0), stratified by study type × institute group.
- **555 confirmation scans are sealed** (`data/p2_conf_ids.txt`, SHA-256 recorded) and never used so far.

**Encoder.**
- CT-FM (`project-lighter/ct_fm_feature_extractor`, Apache-2.0; pretrained on IDC, not TotalSegmentator). We use its last stage, 512-d at stride 16 voxels.
- Spacing 1.0 mm, so each token is 16 mm. Tokens within 32 mm of the volume edge are dropped.
- A **random-init CT-FM** is the null encoder.
- 150 scans → **1,021,303 tokens**.

**Reference ("physics") features** (83 per token):

| Block | Features | Contents |
|---|---|---|
| Local | 28 | 22-bin HU histogram, mean, SD, gradient, LoG σ1.5, LoG σ3, local SD |
| Context | 28 | The same 28, averaged over 3×3×3 tokens (48 mm) |
| Position | 27 | [z, y, x] + sin/cos(2^k π c), k < 4 |

As run, the z coordinate was the **vertebral level derived from the masks**. That is label-derived; see §3–4.

**Concepts.**
- Two-level atlas: 117 leaf structures map to 43 groups. A group is eligible if ≥ 10 patients have a core token (occupancy ≥ 0.8), which gives **33 eligible groups**.
- Token labels: core (≥ 0.8) → that group; 'other' (labelled structure ≤ 0.2; fat or unlabelled tissue, about 45% of tokens); partial tokens are not scored.

**Methods** (all fitted on the same rows):
- **SAE**: BatchTopK with the plan's size rule, M = min(4d, n_eff/50) = **425** (n_eff 21,277) and k = M/16 = **27**; 3,000 steps, batch 4,096, lr 3e-3.
  - **Single fit.**
  - **5-fit consensus** (≥ 3 of 5 fits, r ≥ 0.7): 34–38 features, L0 ≈ 6.
- **Baselines**:
  - PCA and varimax;
  - sparse varimax (L0 6);
  - soft k-means (M 425, L0 6);
  - raw sparse channels (1,024 signed, L0 6);
  - HU-histogram SAE (consensus on the reference features).
- **Nulls**: an SAE on the random-init encoder, and a frozen-decoder SAE.

**Replication.** J = 3 patient-grouped halves, stratified by study type. The model fitted on half h is scored on the other half's patients, using 300 evaluation tokens per patient.

**Validity ladder, per feature f:**
- **V0** (technical): activation frequency ≥ 1e-3, ≥ 10 patients, not a duplicate (r ≥ 0.9).
- **Twin score t_f**: match between the two halves' models on the own half's evaluation tokens.
- **Selectivity**: sel_f = μ* / (μ* + the sum of the 6 largest other concept means), computed patient-grouped.
- **Chimera rule**: in the top 1% of activations, ≥ 20% of the weight comes from a non-adjacent concept → reject.
- **V3-lite perturbation robustness** on 20 scans: r_pert = min(r_shift (8 mm half-stride), r_noise (+50%), r_HUoffset (+20 HU, anatomical features only)).
- **v_f** = min(t_f, sel_f, r_pert) for features that pass V0, are not chimeric and are not 'other'; otherwise 0.
- **C(τ)** = the number of gated concepts with at least one feature having v ≥ τ, for τ ∈ [0.5, 0.9]. The primary metric is the normalised area under C(τ).

**Gate S probe.**
- Multinomial logistic regression (C = 1, balanced) on 60,000 uniformly sampled tokens, GroupKFold(5) by patient.
- A concept is **gated** if the lower 95% bound of its AUROC is ≥ 0.70.
- It is **beyond-HU** if dense FM − reference ΔAUROC ≥ 0.05 with lower bound > 0.

**Decision table (fixed before running).**

| Gate | Pass rule |
|---|---|
| E, engineering | ≤ 5 min per scan, ≤ 12 GB, CPU parity cosine ≥ 0.995, all 150 scans encoded within 24 h |
| S, signal | ≥ 15 gated concepts **and** ≥ 3 beyond-HU concepts |
| D1, SAE advantage | Consensus or single-fit area above the strongest baseline in all 3 replicates, mean gain ≥ 0.05 |
| D2, dissociation | Consensus R1 ≥ 0.60 and θ upper bound < 0.75 (or Spearman < 0.3 if θ can't be estimated) |
| D3, shortcut | ≥ 20% of reproducible consensus features encode acquisition (scan-mean AUROC ≥ 0.8) or are crop-locked |
| Degeneracy | C(0.7) > 0 for ≥ 2 methods, and ≥ 20 features in each class for θ |

Outcomes:
- **GO-positive** = E + S + D1.
- **GO-cautionary** = E + S + (D2 or D3).
- **NO-GO** = S fails, or none of D1–D3 holds, or the degeneracy check fails.

## 2. Phase 1 result: NO-GO (`docs/DECISION_MEMO_P1.md`, `data/p1/decision.json`, `data/p1/fit/summary.json`)
| Gate | Result |
|---|---|
| E | **Pass.** Encode 9.8 h for the dev set, at 1.0 mm |
| S | **Fail.** 32 gated, **0 beyond-HU** |
| D1 | **Fail.** Strongest baseline is soft k-means, area 0.046. Consensus gain −0.046, single-fit gain −0.038 |
| D2 | **Fail.** Consensus R1 0.56. θ not estimable (2 valid vs 2,547 invalid features; estimate 0.50, CI 0.24–0.76) |
| D3 | **Fail.** Shortcut share of reproducible consensus features 0.01 |
| Degeneracy | **Fail.** C(0.7) > 0 only for soft k-means |

Normalised area under C(τ), per replicate (0 / 1 / 2), and between-half reproducibility R1:

| Method | Area (rep 0 / 1 / 2) | R1 (rep 0 / 1 / 2) | Features (rep 0) | L0 | Shortcut share of reproducible features (rep 0) |
|---|---|---|---|---|---|
| SAE consensus | 0.000 / 0.000 / 0.000 | 0.56 / 0.52 / 0.60 | 34–38 | 6 | 0.00 |
| SAE single | 0.007 / 0.007 / 0.009 | 0.04 / 0.05 / 0.07 | 425 | 27 | 0.03 |
| Soft k-means | 0.042 / 0.045 / 0.050 | 0.32 / 0.33 / 0.32 | 425 | 6 | 0.26 |
| Raw sparse channels | 0.005 / 0.002 / 0.003 | 1.00 / 1.00 / 1.00 | 1,024 | 6 | 0.66 |
| Sparse varimax | 0.000 / 0.005 / 0.002 | 1.00 / 0.97 / 1.00 | 1,024 | 6 | 0.52 |
| PCA | 0 / 0 / 0 | 0.49 / 0.51 / 0.53 | | | |
| Varimax | 0 / 0 / 0 | 1.00 / 1.00 / 1.00 | | | |
| HU-histogram SAE (consensus) | 0 / 0 / 0 | 0.67 / 0.63 / 0.61 | 18–19 | 3–4 | 0.00 |
| Null-encoder SAE (consensus) | 0.003 / 0.003 / 0.003 | 0.81 / 0.86 / 0.87 | 222 | 32 | 0.11 |
| Frozen decoder | 0 / 0 / 0 | 0 / 0 / 0 | | | |

## 3. Post hoc checks after the NO-GO (`imgsae/exploratory/p1_checks/README.md`)
These are exploratory. Each first reproduces the official number exactly, then changes one thing.

**Check 1: chimera rule.**
- The chimera step removed 79–100% of V0 features for **every** method.
- 94–100% of those flags were caused by the 'other' class, which the rule counts as a foreign concept for every organ.
- With 'other' treated as adjacent to all concepts ("neutral"), on replicate 0:

  | Method | Area as run | Area, 'other' neutral |
  |---|---|---|
  | Soft k-means | 0.042 | **0.273** |
  | Raw sparse | 0.005 | **0.217** |
  | Sparse varimax | 0.000 | 0.095 |
  | SAE single | 0.007 | 0.066 |
  | Null-encoder SAE | 0.003 | 0.031 |
  | HU-histogram SAE | 0.000 | 0.016 |
  | **SAE consensus** | 0.000 | **0.000** |

- The degeneracy disappears, but the method ranking stays the same. The consensus features are reproducible (median t 0.80) and perturbation-stable (median r 0.92), but none is organ-selective (median sel 0.31). They look like broad tissue-type features.

**Check 2: gate S and position.** Same probe and tokens; only the reference changes.

| Reference | Beyond-HU concepts |
|---|---|
| HU + context + position, as run (z from masks) | 0 |
| HU + context + label-free x/y (no z) | 0 |
| HU + context, no position | **4** (iliac vessels, prostate, small bowel, bladder) |

CT-FM's advantage over intensity is mostly *where the token is*.

**Check 3: small samples in the gate S probe.**
- Several gated concepts rest on very few probe tokens (oesophagus 3, clavicle 2, iliac vessels 2), because the probe sample is uniform and 68% 'other'.
- The oesophagus AUROC of 0.30 is small-sample noise.

## 4. Phase 1b Stage A diagnostics (exploratory, the same 150 dev scans; `imgsae/exploratory/p1b_sanity/RESULTS.md`)
This was prompted by an external suggestion to reframe the paper as "CT FMs don't beat physics, SAEs don't beat clustering".
- Reading rules were written before running: R-sat, R-fm, R-sae.
- Every script reproduces an official number first. All sanity rows pass, and the local ones are exact.
- The A3 SAE rows ran on a cloud L4 GPU and match within seed noise. Replicate 1 is exact; replicates 0 and 2 differ by ≤ 0.005 in R1 and ≤ 0.004 in area.

**Label-free reference ladder:**

| Set | Contents | Features |
|---|---|---|
| R0 | HU stats | 24 |
| R1 | + texture | 28 |
| R2 | + 48 mm context | 56 |
| R3 | + body x/y | 74 |
| R4 | + scan-relative z (from the token grid, no labels) | 83 |
| run | As run (z from masks; leaky) | 83 |

### A1: probe ladder (median one-vs-rest AUROC; patient-cluster bootstrap)
| Task | Tokens | Patients | Classes | CT-FM | Untrained CT-FM | R0 | R2 | R3 | R4 | run | CT-FM+R3 | untrained+R3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T1a organ groups, uniform 60k (sanity) | 60,000 | 150 | 33 | 0.998 | 0.947 | – | – | – | – | 0.998 | – | – |
| T1b organ groups, stratified | 59,294 | 150 | 33 | 0.999 | 0.960 | 0.930 | 0.973 | 0.995 | 0.997 | 0.999 | 0.999 | 0.996 |
| T2 boundary tokens | 47,965 | 150 | 33 | 0.997 | 0.944 | 0.909 | 0.965 | 0.991 | 0.995 | 0.998 | 0.999 | 0.991 |
| T3 vertebra level (leaf) | 11,145 | 149 | 24 | **0.982** | 0.874 | 0.637 | 0.872 | 0.903 | **0.930** | 0.999 | 0.982 | 0.933 |
| T3 lung lobe (leaf) | 10,000 | 142 | 5 | 0.986 | 0.853 | 0.595 | 0.641 | 0.956 | 0.966 | 0.987 | 0.988 | 0.962 |
| T3 left vs right (16 paired structures) | 13,031 | 145 | 1 | 0.999 | 0.833 | 0.503 | 0.510 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

Sanity: T1a reproduces `gates.json` exactly. Rib level couldn't be estimated at 16 mm (only rib 1 has ≥ 10 patients), so it was skipped.

**Paired differences** (counts are numbers of classes):

| Task | Difference | Median Δ | CI > 0 | Δ ≥ 0.05 and CI > 0 |
|---|---|---|---|---|
| T1b | CT-FM − R4 | 0.002 | 21/33 | **0** |
| T1b | CT-FM − untrained | 0.038 | 33/33 | 12 |
| T1b | CT-FM+R3 − R3 | 0.004 | 28/33 | 0 |
| T1b | untrained+R3 − R3 | 0.000 | 12/33 | 0 |
| T2 | CT-FM − R4 | 0.004 | 24/33 | 0 |
| T3 vertebra | CT-FM − R4 | **0.058** | 21/24 | **13** |
| T3 vertebra | CT-FM − untrained | 0.108 | 24/24 | 19 |
| T3 vertebra | CT-FM+R3 − R3 | 0.086 | 21/24 | 16 |
| T3 lobe | CT-FM − R4 | 0.018 | 5/5 | 0 |
| T3 lobe | CT-FM − untrained | 0.125 | 5/5 | 5 |

**Left vs right without any coordinates** (R2): about 0.5 for every paired structure. CT-FM 0.95–1.00, so the FM infers side from context.

**T4: few labels** (median AUROC; n = training patients per fold, 3 draws):

| Task | n | CT-FM | Untrained | R3 | R4 |
|---|---|---|---|---|---|
| Organ groups | 3 | 0.931 | 0.807 | 0.856 | 0.866 |
| Organ groups | 30 | 0.997 | 0.930 | 0.988 | 0.990 |
| Vertebra level | 3 | **0.815** | 0.689 | 0.686 | 0.704 |
| Vertebra level | 10 | 0.905 | 0.743 | 0.787 | 0.805 |
| Vertebra level | 30 | 0.959 | 0.804 | 0.845 | 0.870 |
| Lung lobe | 3 | **0.921** | 0.681 | 0.820 | 0.820 |
| Lung lobe | 30 | 0.980 | 0.789 | 0.945 | 0.956 |

**Reading rules:**
- **R-sat** (benchmark saturated: CT-FM, untrained and R3 all ≥ 0.97, and |CT-FM − R3| ≤ 0.01) = **false as written**. The untrained network scores 0.960. CT-FM vs physics *is* saturated (Δ 0.003).
- **R-fm** (on ≥ 1/3 of classes, CT-FM beats the best label-free reference **and** the untrained network by ≥ 0.05, CI > 0) = **true**. The share of classes meeting it, by task:

  | Task | Share of classes |
  |---|---|
  | Vertebra level, all data | 0.54 |
  | Vertebra level, n = 3 / 10 / 30 patients | 0.67 / 0.62 / 0.58 |
  | Lung lobe, n = 3 patients | 0.60 |

### A2: SAE adequacy and size / sparsity sweep (replicate 0; local RTX 3050 Ti)
| Config | M | k | Steps | Held-out R² | Dead share | R1 | Area as run | Area, 'other' neutral | Neutral, 425 random features | Median sel |
|---|---|---|---|---|---|---|---|---|---|---|
| **Phase 1 config** | 425 | 27 | 3k | 0.801 | 0.000 | 0.042 | 0.007 | 0.066 | 0.066 | 0.33 |
| M425_k6 | 425 | 6 | 3k | 0.680 | 0.061 | 0.228 | 0.089 | 0.328 | 0.328 | 0.51 |
| M1024_k27 | 1024 | 27 | 3k | 0.822 | 0.016 | 0.047 | 0.028 | 0.139 | 0.078 | 0.42 |
| M1024_k6 | 1024 | 6 | 3k | 0.696 | 0.157 | 0.146 | 0.186 | 0.462 | 0.340 | 0.60 |
| M2048_k27 | 2048 | 27 | 3k | 0.829 | 0.055 | 0.031 | 0.052 | 0.274 | 0.102 | 0.47 |
| M2048_k6 | 2048 | 6 | 3k | 0.704 | 0.241 | 0.080 | 0.260 | 0.512 | 0.283 | 0.67 |
| M1024_k27 | 1024 | 27 | 12k | 0.852 | 0.110 | 0.196 | 0.198 | 0.448 | 0.311 | 0.49 |
| **M1024_k6** (best) | 1024 | 6 | 12k | 0.707 | 0.007 | 0.203 | 0.292 | 0.561 | 0.432 | 0.61 |
| **Consensus at best** (5 fits) | 1024 | 6 | 12k | – | – | **0.513** | 0.269 | 0.562 | 0.562 | 0.65 |

- **Seed check.** R1 within one half (2 seeds) vs between halves: 0.056 vs 0.042 at the Phase 1 config, and 0.242 vs 0.203 at the best config. The instability is seed-driven, not data-driven.
- The Phase 1 SAE was adequately reconstructing (R² 0.80, no dead latents). It was too dense (k 27) and too briefly trained for concept validity.

### A3: fair comparison (replicates 0–2; matched L0 6 and 27; areas raw and with 425 random features, 20 draws)
| Method | L0 | Features | R1 | Area as run | Area, 'other' neutral | Neutral, 425 features | Median sel |
|---|---|---|---|---|---|---|---|
| **SAE best k 6** (M1024, 12k) | 6 | 1,024 | 0.20 | **0.274** | **0.530** | **0.398** | 0.61 |
| SAE best k 27 (M1024, 12k) | 27 | 1,024 | 0.19 | 0.144 | 0.399 | 0.279 | 0.48 |
| SAE Phase 1 config | 27 | 425 | 0.05 | 0.007 | 0.062 | 0.062 | 0.33 |
| SAE consensus, Phase 1 config | 6 | 34 | 0.51 | 0.000 | 0.006 | 0.006 | 0.29 |
| Soft k-means, CT-FM | 6 | 425 | 0.32 | 0.046 | 0.261 | 0.261 | 0.49 |
| Soft k-means, CT-FM | 27 | 425 | 0.61 | 0.011 | 0.085 | 0.085 | 0.31 |
| Raw channels, CT-FM | 6 | 1,024 | 1.00 | 0.003 | 0.227 | 0.148 | 0.43 |
| Sparse varimax, CT-FM | 6 | 1,024 | 0.99 | 0.002 | 0.092 | 0.045 | 0.41 |
| Soft k-means, physics R3 | 6 | 425 | 0.46 | 0.016 | 0.215 | 0.215 | 0.42 |
| Raw channels, physics R3 | 6 | 148 | 0.99 | 0.004 | 0.077 | 0.077 | 0.33 |
| Soft k-means, untrained CT-FM | 6 | 425 | 0.43 | 0.023 | 0.149 | 0.149 | 0.54 |
| Raw channels, untrained CT-FM | 6 | 1,024 | 1.00 | 0.001 | 0.007 | 0.003 | 0.43 |

Additional detail:
- **Organs with v ≥ 0.7, as-run rule** (per half, replicates 0–2):
  - best SAE k 6: 6–10;
  - soft k-means: 0–1;
  - raw channels: 0.
- **R-sae** ("simple beats SAE", checked at each L0, every replicate, both rules, on the 425-feature area) = **does not hold**. The best SAE wins every comparison:

  | L0 | Rule | Simple, best | SAE |
  |---|---|---|---|
  | 6 | 'Other' neutral | 0.25–0.27 | 0.39–0.40 |
  | 6 | As run | 0.04–0.05 | 0.18–0.19 |
  | 27 | 'Other' neutral | 0.11–0.12 | 0.28 |

**Caveats on Stage A:**
- The SAE was tuned over 8 configurations on replicate 0, while soft k-means was run at M 425 only.
- No SAE was run on the untrained network or on physics features at the tuned configuration.
- The 'other'-neutral rule is post hoc.
- Everything uses development scans that have been analysed many times.

## 5. The Phase 1 decision table re-scored with the new evidence (post hoc; not a verdict)
| Gate | Phase 1 | Stage A | Status |
|---|---|---|---|
| S (≥ 3 concepts beyond physics) | 0 of 33 groups | Still 0 at group level (label-free R4, Δ 0.002). At **leaf level, 13 of 24 vertebrae** are beyond R4 and the untrained network | Fails as defined. Would pass with leaf-level concepts and the label-free reference (both changes made after seeing data) |
| D1 (SAE > strongest baseline, all replicates, gain ≥ 0.05) | −0.046 | Tuned SAE **+0.22 / +0.23 / +0.23** (as-run rule) | Would pass (post hoc config) |
| D2 (consensus R1 ≥ 0.60) | 0.56 | 0.51 at the tuned config (rep 0) | Fails |
| D3 (shortcut share ≥ 20%) | 0.01 | Not retested | Fails |
| Degeneracy | Only k-means > 0 | Tuned SAE C(0.7) 6–10 per half, as-run rule | Would pass |

**Under the original rules, the verdict is still NO-GO, because S fails.** S depends on the concept list and the reference, not on the SAE.

## 6. Interpretation
1. **The organ-level validation target is saturated at 16 mm.** Physics + position identifies organs as well as CT-FM, so gate S could not pass with organ groups. The test was too easy; that doesn't mean the model knows nothing beyond physics.
2. **CT-FM carries anatomy beyond physics, and it comes from pretraining.**
   - Vertebral level, few-label lobes, and side inferred from context.
   - The untrained network is far worse and adds nothing on top of physics.
3. **The SAE "failure" was a configuration effect.** The size rule (k = M/16, M = n_eff/50) gave a dense, briefly trained SAE.
   - With k 6, M 1,024 and 12,000 steps, SAEs beat all decompositions under both rules in all replicates.
   - The consensus at that config is stable (R1 0.51).
4. **Reproducibility and validity come apart at method level.** The most reproducible methods (varimax, raw channels: R1 ≈ 1) have about zero validity. Their reproducible features are often acquisition shortcuts (shortcut share 0.52–0.66). The Phase 1 consensus (R1 0.56) had 0 valid features.
5. **Open:**
   - whether SAE features themselves capture the beyond-physics concepts (vertebral level etc.);
   - whether validity depends on pretraining at the tuned config (the null SAEs);
   - whether all this holds on sealed data.

---

## 7. Plan v2: restart the original SAE paper

### Context and decisions (user, 2026-11-09)
- The user rejected a methods-only sanity paper. The aim is to restart the original SAE paper as **one flagship journal paper**: Radiology: AI or MedIA, with Nature Communications as a stretch, in about 4–6 months.
- **Resources:**

  | Kind | What |
  |---|---|
  | Public data | TotalSegmentator; PI-CAI (1,500 bpMRI); TCIA Prostate-MRI-US-Biopsy (about 900); TCIA vestibular schwannoma (240 + 190 follow-up) |
  | Local data (ethics approved, cloud allowed) | Breast RT planning CT after lumpectomy (200 + 40 external, RTSTRUCT); CTA with 2-year MACE (350); vestibular schwannoma ceT1 + T2 (100, RTSTRUCT) |
  | Readers | 2 radiologists |
  | Public supervised models | nnU-Nets: TotalSegmentator, PI-CAI baseline, Kujawa vestibular schwannoma, a public breast model |
  | Compute | 2 Modal accounts at $29/month each; an M5 fanless Mac; this laptop (RTX 3050 Ti, power-capped) |

- **Honesty rule.** The Phase 1 NO-GO memo stays as written. v2 is a new study:
  - explored on development data (§3–4 count as exploration);
  - then frozen, registered, and confirmed on sealed data;
  - every v1 → v2 change is logged with the evidence that prompted it.

### Target headline and contributions
"Sparse autoencoders recover valid concepts from medical imaging models — beyond intensity, beyond simple decompositions, and beyond what reproducibility predicts — in a pre-registered study across CT and MRI, with dense ground truth, positive and negative control encoders, clinical endpoints and radiologist validation."

| Contribution | Claim | Test |
|---|---|---|
| C1 | SAEs beat tuned baselines (k-means, PCA/varimax, raw channels) on mask-grounded validated coverage, at matched sparsity and feature count | H2 |
| C2 | Validity comes from pretraining: the pretrained-encoder SAE beats an untrained-encoder SAE and a physics-feature SAE | H2b |
| C3 | SAE features capture concepts physics can't | S2 + the feature-level test |
| C4 | Reproducibility is an inadequate proxy for validity, at feature level and method level | H1, θ |
| C5 | SAE concept scores add to clinical predictors (csPCa on PI-CAI), with external validation | H4 |
| C6 | Radiologists recognise SAE features better than baseline features | V4 intruder test |

### Design: pillars and encoders
| Pillar | Data | Ground truth | Encoders | Role |
|---|---|---|---|---|
| **P1 CT anatomy (core)** | TotalSegmentator: 150 dev, 555 sealed | Dense masks for 117 leaf structures; perturbation re-encodes | CT-FM (self-supervised); **TotalSegmentator nnU-Net (supervised positive control)**; untrained CT-FM (negative control); one more self-supervised 3D FM (SPECTRE / Merlin / Pillar-0 / CT-CLIP, picked in Stage 0) | C1–C4, ladder calibration |
| **P2 prostate MRI (core)** | PI-CAI, 50/50 patient split with the second half sealed; external: Prostate-MRI-US-Biopsy | Lesion masks, ISUP ladder, AI zonal masks, PSA/PSAD/age/volume | PI-CAI nnU-Net (supervised); a self-supervised encoder (DINOv3 2.5D as in the v1 plan, or an MRI FM); untrained null | C1, C2, C4, **C5**, centre shortcut |
| **P3 extension (one only, after gates)** | Vestibular schwannoma (TCIA 240 + local 100 + 190 follow-up) **or** CTA 350 with MACE | Tumour/cochlea masks and growth, **or** cardiac anatomy and 2-year MACE | Kujawa vestibular schwannoma nnU-Net / TotalSegmentator on CTA, plus an FM | Generalisation; second clinical endpoint |
| Later papers | Breast RT CT (2×2 natural experiment); the unused P3 cohort | RTSTRUCT | Public breast model, CT-FM | Paper 2 / 3 |

**Why the positive control matters.** A supervised encoder trained on these exact labels should give highly valid SAE features. If the ladder can't find them, the ladder is broken, not the SAE. Together with the untrained encoder, it brackets every result.

### Options assessed
**Kept:**
- **Fixes for the Phase 1 failures:** the label-free reference (R4), leaf-level concepts, and the 'other'-neutral chimera rule as primary ('orig' as a sensitivity analysis).
- **SAE and fairness:**
  - an SAE configuration tuned on development data, with Matryoshka (Wesp et al.'s SAE) as a secondary;
  - equal tuning for baselines (k-means M sweep);
  - nulls at the tuned configuration: untrained encoder, physics SAE, frozen decoder.
- **Supervised positive-control encoders.**
- **New tests:**
  - **Feature-level beyond-physics test.** A cross-fitted regressor predicts each feature's activation from R4. The feature counts as beyond-physics if R² < 0.5 and it stays concept-selective.
  - **Causal specificity.** Ablate a feature and measure the drop for its own concept vs others, in linear leaf probes, and in the segmentation decoder for nnU-Nets.
  - **Transfer and invariance.** Contrast vs non-contrast scans; institute I vs others.
  - **Label efficiency.** How many labelled patients a physics probe needs to match one SAE feature.
  - **Reproducibility vs validity.** θ, plus the R1–validity inversion across methods.
- **Rigour:** J = 10 sealed replicate halves, corrected t, cluster bootstrap, Holm, Zenodo registration.
- **Readers:** the V4 reader study.
- **Clinical:** the PI-CAI clinical increment (H4), with external validation.

**Later:**
- 8 mm tokens (ribs and small organs; 8× more tokens);
- archetypal SAE (its stability claim is disputed, arXiv 2606.02061);
- the full SAE variant zoo;
- scan-level pathology labels (weak, no masks);
- breast RT CT;
- the second extension cohort.

**Dropped:**
- more organ-level probes (saturated);
- the mask-derived z position (label leak).

### Stages and gates (each stage needs the user's go; gates are fixed now)
**Stage 0: inventory and feasibility (about 1 week).**
- **Data inventory**, per dataset: location, format, N, labels, licence, de-identification. Also check the Prostate-MRI-US-Biopsy sequences (T2 only, or full bpMRI).
- **Model inventory**: weights, licence, input spec and a feature hook for every candidate encoder (the DINOv3 licence needs the user). Pick the second 3D CT FM and the prostate self-supervised encoder.
- **Benchmarks:** encode 2 scans per encoder on a Modal L4, so the cost is known before any encode. Check the M5 Mac.
- **Budget guard v2:** per Modal profile (shforghani2002 + forghanishayan, to be confirmed), $29/month each, per-task budgets, a usage check before every launch.
- **Docs:** save this file as `docs/SAE_PAPER_v2_PLAN.md`; log the v1 → v2 change in `docs/EXECUTION_LOG.md`; update `STATUS.md`. The Phase 1b sanity plan is marked superseded.

**Stage 1: P1 CT development (exploratory, 150 dev scans; about 2–3 weeks; code in `imgsae/exploratory/v2_ct/`).**
1. **Leaf atlas.** `atlas.partition` and `atlas.adjacency` on the leaf occupancy (117 columns). Eligible if ≥ 10 patients have core tokens. Leaf adjacency feeds the chimera rule.
2. **Gate S2 probe.** CT-FM vs R4 vs untrained vs CT-FM+R4 on every eligible leaf. This reuses the A1 task builder and `p1_probe`.
3. **SAE grid v2 on Modal.**
   - Grid: k ∈ {4, 6, 8}, M ∈ {1024, 2048}, steps ∈ {12k, 24k}.
   - At the best configuration: Matryoshka, the 5-fit consensus, and the nulls (untrained encoder, R4 physics SAE, frozen decoder).
4. **Equal tuning for baselines.**
   - Soft k-means with M ∈ {425, 1024, 2048} at L0 ∈ {4, 6, 8}.
   - Raw channels, sparse varimax and PCA at matched L0.
5. **Positive control.** TotalSegmentator nnU-Net encoder features, sampled at our token centres. Encode 150 dev + 20 perturbation scans.
6. **Second self-supervised 3D FM.** Wrap it, then encode the dev and perturbation scans.
7. **New analyses:** physics-explainability R², causal specificity, transfer, label efficiency, θ and the R1–validity inversion. Each comes with planted-truth unit tests.
8. **Gate G1.** Go to confirmation only if all of (a)–(d) hold:
   - (a) **S2:** ≥ 3 leaf concepts where CT-FM beats R4 *and* the untrained encoder by ΔAUROC ≥ 0.05 (CI lower bound > 0).
   - (b) **D1v2:** the best tuned SAE beats the best tuned baseline in all 3 replicates, mean gain ≥ 0.05, on the primary rule at matched L0 and 425 features.
   - (c) **Nulls:** the CT-FM SAE beats both the untrained-encoder SAE and the physics SAE by ≥ 0.05 in all replicates.
   - (d) **Calibration:** the positive-control SAE has C(0.7) ≥ 10 leaf concepts.

   Then **(e)**, which sets the headline tier: ≥ 5 valid, beyond-physics CT-FM SAE features on S2 concepts, more than the physics SAE has.
   - If (a)–(d) hold but (e) fails, the framing is cautionary.
   - If (b) or (c) fails, stop and report.
   - If (d) fails, fix the ladder first.

**Stage 2: P2 prostate development (overlaps Stage 1; about 3 weeks).**
- PI-CAI 50/50 patient split, stratified by centre × csPCa. The sealed half stays unopened until registration.
- Data come from the user's existing Modal volume `picai-dataset-vol`, read-only, with the user's OK.
- Tokens cover the prostate region.
- Reference: T2/ADC/HBV histograms + context + position.
- Concepts: zonal masks, csPCa lesions, the ISUP ladder.
- Endpoints:
  - lesion selectivity and AUROC, R1, θ;
  - centre and b-value shortcut share;
  - a development estimate of H4: the increment of the SAE score set over PSAD + age + volume, minus the texture-baseline increment.
- **Gate G2:** C(0.7) > 0 on lesion concepts for an SAE, and the development H4 increment ≥ the texture increment − 0.03.

**Stage 3: freeze and register (about 1 week).** `docs/SAE_PROTOCOL_v2.md` fixes:
- concepts, references, the SAE and baseline configurations, the primary rule, thresholds;
- H1–H5 with Holm, J = 10, N and the sealed job lists.

The user decides on Zenodo registration.

**Stage 4: confirmation (about 3 weeks).**
- Encode the 555 sealed TotalSegmentator scans and 20 perturbation scans with all P1 encoders.
- Run the PI-CAI sealed half and the external Prostate-MRI-US-Biopsy set.
- The frozen pipeline runs once, from the sealed job list. The tier-1 report is written before any secondary analysis.

**Stage 5: V4 reader study.**
- 40–60 features: CT-FM SAE, best baseline, null, positive control.
- 2 readers, region-matched intruder trials, on a static HTML page; about 1.5 h per reader.
- Inter-reader agreement.

**Stage 6: extension and write-up.**
- One P3 cohort, if the gates passed and time allows.
- Figures, manuscript (CLAIM and TRIPOD+AI checklists), code and benchmark release.
- Submission about March–April 2027.

### Compute and budget
- **Public and approved data → Modal L4.** Each job has a timeout, so the worst case is a hard bound. **Light CPU work → laptop + M5 Mac.**
- **Rough needs.** Each task gets a ledger budget at its stage start, after the Stage 0 benchmarks.

  | Item | Estimate |
  |---|---|
  | Stage 1 grid, nulls, baselines | $6–10 |
  | Development encodes | $5–8 |
  | Confirmation encodes | $15–25 |
  | PI-CAI encodes | $15–25 |
  | Confirmation fits | about $10 |
  | **Total** | **about $50–80 over 3–4 months, vs $58/month capacity** |

- **Used so far:** about $1.68 (Stage A SAE rows on an L4).

### Rules
- **Code:** new code goes in `imgsae/exploratory/v2_*` (development) and `scripts/v2_*` (frozen pipeline). The v1 production code is never edited.
- **Checks and logs:**
  - every script reproduces a known number first;
  - deviations are logged in `docs/EXECUTION_LOG.md`;
  - `STATUS.md` is kept current.
- **Sealed data:** not opened before registration.
- **Modal:** usage is checked before every launch, and no task exceeds its budget. The user's other volumes are read-only, and only with the user's OK.

### Reused code
| File | What it gives |
|---|---|
| `scripts/p1_fit.py` | `Model`, `feature_table`, `halves`, `eval_rows`, `load_perturb` |
| `scripts/p1_probe.py` | `oof_proba`, `boot_auc` |
| `scripts/p1_assemble.py` | `prep`; `IMGSAE_P1` data folder |
| `imgsae/atlas.py`, `ladder.py`, `stats.py`, `consensus.py`, `sae.py` | Atlas, ladder metrics (incl. `theta`), statistics, consensus, SAE fitting (Matryoshka, freeze_D) |
| `imgsae/tokens.py`, `imgsae/encoders/ctfm.py`, `scripts/p1_encode.py` | Token tables and encodes |
| `exploratory/p1b_sanity/common.py`, `a3_decomp_fair.py` | R4 reference, `evaluate`, `fit_eval` |
| `exploratory/p1b_sanity/cloud/` | Modal job pattern, `budget.py`, volume `imgsae-p1b` |

### Verification
- **Sanity rows.** The leaf pipeline run on group labels reproduces A3. The grid's run config reproduces A2 (R1 0.042, area 0.007). Encoder wrappers reach cosine ≥ 0.995 against the reference outputs.
- **Controls bracket every result:** positive control ≥ CT-FM SAE ≥ untrained / physics.
- **Unit tests** recover planted values (explainability R², causal specificity, θ).
- **Budget:** a status check before every launch, and the ledger is reconciled with `modal billing report`.
- **Gates** are applied exactly as written. After each gate, the read-out goes to the user, who decides.

### Main risks
| Risk | Mitigation |
|---|---|
| Beyond-physics concepts limited to vertebral level | Test all leaf families, transfer and label efficiency; (e) only sets the headline tier |
| MRI lesion concepts are intensity-dominated (low ADC) | ISUP ladder and a texture baseline; C5 rests on the increment |
| Encoder integration takes too long | Time box per model; the second FM is dropped first |
| Scope creep | One P3 cohort only, after the gates |

---

## 8. Limitations of the evidence so far
- **Reuse of development data.** All of §2–4 uses the same 150 development scans, analysed many times. Nothing is confirmatory. The 555 confirmation scans are untouched.
- **Post hoc choices.** The tuned SAE configuration, the leaf-level concepts, the label-free reference and the 'other'-neutral chimera rule were all chosen after seeing results.
- **Unequal tuning.** The SAE was tuned over 8 configurations on replicate 0; soft k-means was run only at M 425.
- **Missing nulls.** No null SAEs at the tuned configuration yet.
- **GPU differences.** Stage A SAE rows mix a local RTX 3050 Ti (A2) and a cloud L4 (A3). They match within seed noise, not bit for bit.
- **Token size.** 16 mm tokens can't resolve ribs or very thin structures (oesophagus).
- **Shortcut test.** The D3 shortcut audit was not repeated at the tuned configuration.

## 9. Questions for reviewers
1. Is the v1 → v2 transition defensible? Phase 1 was pre-registered and failed; v2 changes concepts, reference, chimera rule and SAE configuration based on the same development scans, then confirms on sealed data. What must be disclosed or added?
2. Is a **supervised positive-control encoder** (TotalSegmentator nnU-Net, trained on these labels) a sound way to calibrate the validity ladder?
3. Is the **feature-level beyond-physics test** (cross-fitted R² < 0.5 from physics features, while still selective) a convincing operationalisation of "beyond intensity and position"? Are there better alternatives?
4. Are the G1 / G2 thresholds and the J = 10 halves on 555 scans sensible and adequately powered?
5. Is the scope (CT anatomy + prostate MRI + readers + one extension cohort) right for Radiology: AI / MedIA / Nature Communications? What else would those venues require?
6. Is the SAE vs baseline comparison fair as designed: matched L0, matched feature count, equal tuning?
7. Which second self-supervised 3D CT FM is the most convincing to include?
8. Should H4 (clinical increment) be superiority or non-inferiority, and against which clinical baseline?

## Appendix D: detailed results (generated from the result files)

### D1. Phase 1 gate S probe per concept (60k uniform tokens; reference as run, z from masks; `data/p1/gates.json`)
| Concept | CT-FM AUROC [95% CI] | Reference AUROC | Δ [95% CI] | Gated | Beyond-HU |
|---|---|---|---|---|---|
| aorta | 0.999 [0.999, 1.000] | 0.993 | +0.006 [0.003, 0.009] | yes | no |
| autochthon | 1.000 [1.000, 1.000] | 0.998 | +0.001 [0.001, 0.002] | yes | no |
| clavicula | 0.991 [0.988, 0.993] | 0.999 | −0.008 [−0.011, −0.006] | yes | no |
| colon | 0.983 [0.977, 0.989] | 0.983 | +0.000 [−0.006, 0.007] | yes | no |
| duodenum | 0.977 [0.944, 0.996] | 0.995 | −0.019 [−0.051, 0.001] | yes | no |
| esophagus | 0.299 [0.249, 0.394] | 0.989 | −0.689 [−0.745, −0.582] | no | no |
| femur | 0.999 [0.998, 1.000] | 0.999 | −0.000 [−0.001, 0.001] | yes | no |
| gallbladder | 0.996 [0.990, 0.999] | 1.000 | −0.004 [−0.009, −0.001] | yes | no |
| gluteal | 0.998 [0.997, 0.998] | 0.998 | +0.000 [−0.001, 0.002] | yes | no |
| great_veins | 0.996 [0.990, 0.999] | 0.998 | −0.002 [−0.008, 0.001] | yes | no |
| heart | 0.998 [0.997, 0.999] | 0.991 | +0.007 [0.001, 0.016] | yes | no |
| hip | 0.999 [0.997, 1.000] | 0.999 | −0.000 [−0.002, 0.001] | yes | no |
| humerus | 0.999 [0.999, 1.000] | 0.998 | +0.002 [−0.000, 0.005] | yes | no |
| iliac_vessels | 0.925 [0.877, 0.970] | 0.885 | +0.040 [0.030, 0.048] | yes | no |
| iliopsoas | 0.998 [0.997, 0.999] | 0.997 | +0.001 [0.000, 0.003] | yes | no |
| kidney | 0.998 [0.997, 0.999] | 0.998 | −0.000 [−0.001, 0.001] | yes | no |
| liver | 0.997 [0.996, 0.998] | 0.998 | −0.001 [−0.002, −0.000] | yes | no |
| lung_left | 0.999 [0.998, 1.000] | 0.999 | −0.000 [−0.001, 0.000] | yes | no |
| lung_right | 0.999 [0.997, 1.000] | 0.998 | +0.000 [−0.001, 0.003] | yes | no |
| pancreas | 0.995 [0.988, 0.999] | 0.995 | −0.000 [−0.004, 0.003] | yes | no |
| prostate | 1.000 [0.999, 1.000] | 0.999 | +0.001 [−0.000, 0.001] | yes | no |
| sacrum | 1.000 [1.000, 1.000] | 0.999 | +0.000 [0.000, 0.001] | yes | no |
| scapula | 0.989 [0.972, 1.000] | 0.998 | −0.010 [−0.025, 0.001] | yes | no |
| skull | 0.999 [0.997, 1.000] | 1.000 | −0.001 [−0.003, −0.000] | yes | no |
| small_bowel | 0.983 [0.979, 0.986] | 0.986 | −0.003 [−0.007, 0.002] | yes | no |
| spinal_cord | 0.993 [0.987, 1.000] | 0.998 | −0.005 [−0.013, 0.000] | yes | no |
| spine_lumbar | 0.999 [0.999, 1.000] | 1.000 | −0.000 [−0.001, 0.000] | yes | no |
| spine_thoracic | 1.000 [1.000, 1.000] | 1.000 | −0.000 [−0.000, 0.000] | yes | no |
| spleen | 0.997 [0.994, 0.999] | 0.999 | −0.002 [−0.005, −0.000] | yes | no |
| sternum | 0.993 [0.972, 1.000] | 1.000 | −0.007 [−0.028, 0.000] | yes | no |
| stomach | 0.984 [0.979, 0.990] | 0.989 | −0.005 [−0.014, 0.007] | yes | no |
| trachea | 1.000 [1.000, 1.000] | 1.000 | +0.000 [−0.000, 0.001] | yes | no |
| urinary_bladder | 0.997 [0.994, 0.999] | 0.981 | +0.017 [−0.001, 0.043] | yes | no |

The oesophagus value rests on 3 probe tokens from 2 patients (check 3). In the stratified sample (D4) it is 0.963.

### D2. A1 vertebra level, per level (11,145 tokens, 149 patients; dominant leaf occupancy ≥ 0.5)
| Level | Tokens / patients | CT-FM | R4 (label-free physics) | Untrained | Run (leaky z) | CT-FM − R4 [95% CI] | CT-FM − untrained [95% CI] |
|---|---|---|---|---|---|---|---|
| S1 | 811 / 100 | 0.998 | 0.974 | 0.985 | 1.000 | +0.023 [0.015, 0.032] | +0.013 [0.007, 0.020] |
| L5 | 1119 / 102 | 0.988 | 0.926 | 0.917 | 0.999 | +0.062 [0.048, 0.078] | +0.071 [0.061, 0.084] |
| L4 | 1137 / 107 | 0.973 | 0.888 | 0.841 | 0.999 | +0.085 [0.065, 0.105] | +0.132 [0.116, 0.148] |
| L3 | 1147 / 111 | 0.959 | 0.896 | 0.810 | 0.999 | +0.063 [0.044, 0.081] | +0.149 [0.134, 0.163] |
| L2 | 1009 / 112 | 0.957 | 0.898 | 0.839 | 0.999 | +0.059 [0.042, 0.076] | +0.118 [0.104, 0.132] |
| L1 | 994 / 123 | 0.967 | 0.882 | 0.823 | 1.000 | +0.085 [0.065, 0.106] | +0.144 [0.126, 0.159] |
| T12 | 921 / 130 | 0.967 | 0.854 | 0.833 | 1.000 | +0.112 [0.088, 0.139] | +0.134 [0.113, 0.154] |
| T11 | 846 / 133 | 0.965 | 0.872 | 0.811 | 1.000 | +0.093 [0.073, 0.113] | +0.154 [0.136, 0.171] |
| T10 | 661 / 122 | 0.967 | 0.889 | 0.800 | 1.000 | +0.078 [0.062, 0.096] | +0.167 [0.150, 0.185] |
| T9 | 503 / 104 | 0.959 | 0.894 | 0.816 | 0.999 | +0.064 [0.043, 0.087] | +0.143 [0.125, 0.164] |
| T8 | 397 / 98 | 0.962 | 0.894 | 0.816 | 0.999 | +0.068 [0.044, 0.090] | +0.145 [0.124, 0.169] |
| T7 | 309 / 90 | 0.971 | 0.888 | 0.827 | 1.000 | +0.083 [0.056, 0.112] | +0.144 [0.121, 0.173] |
| T6 | 276 / 89 | 0.981 | 0.921 | 0.865 | 1.000 | +0.060 [0.044, 0.080] | +0.116 [0.098, 0.138] |
| T5 | 218 / 86 | 0.982 | 0.940 | 0.883 | 1.000 | +0.042 [0.029, 0.056] | +0.099 [0.078, 0.123] |
| T4 | 200 / 85 | 0.986 | 0.966 | 0.900 | 1.000 | +0.019 [0.010, 0.030] | +0.086 [0.063, 0.115] |
| T3 | 189 / 88 | 0.994 | 0.977 | 0.939 | 0.999 | +0.017 [0.012, 0.023] | +0.055 [0.039, 0.072] |
| T2 | 174 / 83 | 0.996 | 0.984 | 0.969 | 0.998 | +0.011 [0.006, 0.017] | +0.026 [0.017, 0.038] |
| T1 | 101 / 47 | 0.995 | 0.993 | 0.974 | 0.998 | +0.002 [−0.002, 0.005] | +0.021 [0.011, 0.036] |
| C7 | 33 / 19 | 0.996 | 0.938 | 0.908 | 0.997 | +0.058 [0.021, 0.118] | +0.088 [0.010, 0.184] |
| C6 | 20 / 14 | 0.989 | 0.950 | 0.960 | 0.998 | +0.039 [−0.014, 0.126] | +0.030 [0.003, 0.062] |
| C5 | 23 / 13 | 0.996 | 0.977 | 0.970 | 0.999 | +0.020 [0.007, 0.035] | +0.026 [0.008, 0.050] |
| C4 | 15 / 10 | 0.983 | 0.935 | 0.908 | 0.992 | +0.048 [0.003, 0.107] | +0.075 [0.007, 0.152] |
| C3 | 16 / 11 | 0.992 | 0.947 | 0.845 | 0.969 | +0.045 [−0.012, 0.117] | +0.147 [0.068, 0.249] |
| C2 | 26 / 14 | 0.998 | 0.987 | 0.941 | 1.000 | +0.012 [0.002, 0.024] | +0.057 [0.023, 0.099] |

**Pattern.** The FM's advantage is largest in the thoracolumbar region, T6 to L5 (Δ 0.06–0.11). There, consecutive vertebrae look alike, and z alone does not fix the level across patients. It shrinks at the ends of the spine (S1, T1–T4, C2), where shape or z position is distinctive.

### D3. A1 lung lobe, per lobe (10,000 tokens, 142 patients)
| Lobe | Tokens / patients | CT-FM | R4 | Untrained | Run | CT-FM − R4 [95% CI] | CT-FM − untrained [95% CI] |
|---|---|---|---|---|---|---|---|
| Left upper | 2000 / 107 | 0.989 | 0.980 | 0.891 | 0.994 | +0.008 [0.004, 0.012] | +0.097 [0.088, 0.106] |
| Left lower | 2000 / 139 | 0.989 | 0.981 | 0.842 | 0.994 | +0.008 [0.004, 0.012] | +0.147 [0.135, 0.160] |
| Right upper | 2000 / 90 | 0.986 | 0.940 | 0.894 | 0.987 | +0.046 [0.036, 0.057] | +0.092 [0.080, 0.102] |
| Right middle | 2000 / 118 | 0.978 | 0.951 | 0.853 | 0.977 | +0.027 [0.020, 0.034] | +0.125 [0.107, 0.147] |
| Right lower | 2000 / 134 | 0.984 | 0.966 | 0.810 | 0.985 | +0.018 [0.011, 0.027] | +0.174 [0.162, 0.188] |

### D4. A1 organ groups, stratified sample (T1b; 59,294 tokens, 150 patients; ≤ 2,000 tokens per concept)
| Concept | Tokens / patients | CT-FM | R4 | Untrained | Run | CT-FM − R4 [95% CI] | CT-FM − untrained [95% CI] |
|---|---|---|---|---|---|---|---|
| aorta | 2000 / 134 | 0.999 | 0.989 | 0.968 | 0.995 | +0.010 [0.007, 0.013] | +0.031 [0.025, 0.038] |
| autochthon | 2000 / 141 | 1.000 | 0.997 | 0.973 | 0.999 | +0.003 [0.002, 0.004] | +0.027 [0.023, 0.030] |
| clavicula | 44 / 29 | 0.999 | 0.999 | 0.973 | 1.000 | +0.000 [−0.000, 0.002] | +0.027 [0.006, 0.055] |
| colon | 2000 / 121 | 0.986 | 0.974 | 0.856 | 0.982 | +0.013 [0.006, 0.024] | +0.130 [0.114, 0.148] |
| duodenum | 235 / 79 | 0.995 | 0.989 | 0.873 | 0.996 | +0.006 [0.002, 0.010] | +0.121 [0.094, 0.154] |
| esophagus | 47 / 19 | 0.963 | 0.978 | 0.881 | 0.989 | −0.015 [−0.027, 0.006] | +0.082 [0.004, 0.118] |
| femur | 2000 / 90 | 1.000 | 0.999 | 0.962 | 0.999 | +0.000 [0.000, 0.001] | +0.038 [0.033, 0.042] |
| gallbladder | 185 / 64 | 0.999 | 0.999 | 0.937 | 0.999 | +0.000 [−0.001, 0.001] | +0.062 [0.039, 0.090] |
| gluteal | 2000 / 99 | 0.999 | 0.996 | 0.939 | 0.999 | +0.003 [0.002, 0.004] | +0.060 [0.054, 0.066] |
| great_veins | 550 / 129 | 0.999 | 0.993 | 0.955 | 0.995 | +0.005 [0.003, 0.008] | +0.044 [0.035, 0.053] |
| heart | 2000 / 129 | 0.998 | 0.980 | 0.950 | 0.995 | +0.018 [0.012, 0.024] | +0.048 [0.040, 0.056] |
| hip | 2000 / 99 | 1.000 | 0.998 | 0.960 | 0.999 | +0.002 [0.001, 0.002] | +0.039 [0.033, 0.045] |
| humerus | 503 / 57 | 1.000 | 0.998 | 0.943 | 0.999 | +0.002 [0.000, 0.005] | +0.057 [0.043, 0.071] |
| iliac_vessels | 24 / 18 | 0.971 | 0.943 | 0.883 | 0.958 | +0.027 [−0.039, 0.132] | +0.088 [0.036, 0.134] |
| iliopsoas | 2000 / 110 | 0.999 | 0.996 | 0.972 | 0.998 | +0.003 [0.002, 0.005] | +0.027 [0.021, 0.033] |
| kidney | 2000 / 118 | 0.998 | 0.996 | 0.960 | 0.998 | +0.002 [0.000, 0.004] | +0.038 [0.032, 0.043] |
| liver | 2000 / 139 | 0.997 | 0.994 | 0.955 | 0.998 | +0.003 [0.002, 0.004] | +0.042 [0.036, 0.048] |
| lung_left | 2000 / 132 | 0.999 | 0.998 | 0.980 | 0.999 | +0.001 [−0.000, 0.004] | +0.018 [0.013, 0.026] |
| lung_right | 2000 / 132 | 1.000 | 0.999 | 0.981 | 1.000 | +0.000 [−0.000, 0.002] | +0.019 [0.014, 0.024] |
| pancreas | 418 / 105 | 0.997 | 0.989 | 0.932 | 0.995 | +0.008 [0.005, 0.012] | +0.065 [0.055, 0.077] |
| prostate | 97 / 39 | 1.000 | 0.999 | 0.963 | 0.999 | +0.000 [−0.000, 0.001] | +0.037 [0.014, 0.080] |
| sacrum | 1600 / 100 | 1.000 | 0.998 | 0.981 | 0.999 | +0.001 [0.001, 0.002] | +0.018 [0.015, 0.021] |
| scapula | 143 / 62 | 1.000 | 1.000 | 0.974 | 1.000 | +0.000 [−0.000, 0.000] | +0.026 [0.017, 0.037] |
| skull | 153 / 14 | 0.999 | 1.000 | 0.946 | 1.000 | −0.001 [−0.002, −0.000] | +0.053 [0.037, 0.071] |
| small_bowel | 2000 / 109 | 0.986 | 0.978 | 0.849 | 0.984 | +0.009 [0.005, 0.012] | +0.137 [0.124, 0.153] |
| spinal_cord | 50 / 31 | 1.000 | 1.000 | 0.990 | 1.000 | −0.000 [−0.001, 0.000] | +0.010 [0.005, 0.015] |
| spine_lumbar | 1709 / 121 | 0.999 | 0.998 | 0.976 | 1.000 | +0.001 [−0.000, 0.001] | +0.023 [0.020, 0.027] |
| spine_thoracic | 1330 / 141 | 1.000 | 0.999 | 0.985 | 1.000 | +0.001 [0.000, 0.001] | +0.015 [0.012, 0.018] |
| spleen | 2000 / 136 | 0.998 | 0.996 | 0.967 | 0.999 | +0.003 [0.001, 0.004] | +0.031 [0.025, 0.037] |
| sternum | 133 / 60 | 1.000 | 1.000 | 0.990 | 1.000 | +0.000 [−0.000, 0.001] | +0.010 [0.002, 0.021] |
| stomach | 2000 / 132 | 0.989 | 0.978 | 0.868 | 0.991 | +0.012 [0.005, 0.021] | +0.122 [0.109, 0.137] |
| trachea | 73 / 35 | 1.000 | 1.000 | 1.000 | 1.000 | +0.000 [0.000, 0.000] | +0.000 [0.000, 0.000] |
| urinary_bladder | 2000 / 91 | 0.999 | 0.992 | 0.926 | 0.996 | +0.007 [0.001, 0.016] | +0.073 [0.045, 0.111] |

### D5. A3 per replicate
Each cell: area as run / area with 'other' neutral / 'other' neutral at 425 features; then R1.

Name key: `km` = soft k-means (M 425); `raw` = raw sparse channels; `svx` = sparse varimax. `_ctfm` / `_R3` / `_null` = input (CT-FM / label-free physics without z / untrained CT-FM). `_L6` / `_L27` = L0.

| Method | Replicate 0 | Replicate 1 | Replicate 2 |
|---|---|---|---|
| SAE best k 6 (M1024, 12k) | 0.262 / 0.516 / 0.400; R1 0.19 | 0.280 / 0.550 / 0.403; R1 0.21 | 0.281 / 0.524 / 0.392; R1 0.21 |
| SAE best k 27 (M1024, 12k) | 0.111 / 0.396 / 0.280; R1 0.18 | 0.167 / 0.401 / 0.276; R1 0.20 | 0.153 / 0.401 / 0.281; R1 0.20 |
| SAE Phase 1 config | 0.009 / 0.064 / 0.064; R1 0.04 | 0.007 / 0.062 / 0.062; R1 0.05 | 0.005 / 0.061 / 0.061; R1 0.06 |
| SAE consensus, Phase 1 config | 0.000 / 0.002 / 0.002; R1 0.55 | 0.000 / 0.014 / 0.014; R1 0.53 | 0.000 / 0.002 / 0.002; R1 0.44 |
| km_ctfm_L6 | 0.042 / 0.273 / 0.273; R1 0.32 | 0.045 / 0.253 / 0.253; R1 0.33 | 0.050 / 0.257 / 0.257; R1 0.32 |
| km_ctfm_L27 | 0.012 / 0.082 / 0.082; R1 0.59 | 0.005 / 0.089 / 0.089; R1 0.63 | 0.016 / 0.085 / 0.085; R1 0.62 |
| raw_ctfm_L6 | 0.005 / 0.217 / 0.146; R1 1.00 | 0.002 / 0.229 / 0.148; R1 1.00 | 0.003 / 0.234 / 0.149; R1 1.00 |
| raw_ctfm_L27 | 0.000 / 0.177 / 0.123; R1 1.00 | 0.000 / 0.160 / 0.107; R1 1.00 | 0.000 / 0.146 / 0.106; R1 1.00 |
| svx_ctfm_L6 | 0.000 / 0.095 / 0.046; R1 1.00 | 0.005 / 0.090 / 0.045; R1 0.97 | 0.002 / 0.090 / 0.043; R1 1.00 |
| svx_ctfm_L27 | 0.002 / 0.064 / 0.035; R1 0.99 | 0.002 / 0.054 / 0.034; R1 0.99 | 0.002 / 0.052 / 0.027; R1 0.99 |
| km_R3_L6 | 0.010 / 0.214 / 0.214; R1 0.48 | 0.019 / 0.214 / 0.214; R1 0.47 | 0.017 / 0.219 / 0.219; R1 0.41 |
| km_R3_L27 | 0.000 / 0.056 / 0.056; R1 0.72 | 0.000 / 0.047 / 0.047; R1 0.70 | 0.000 / 0.040 / 0.040; R1 0.66 |
| raw_R3_L6 | 0.002 / 0.076 / 0.076; R1 1.00 | 0.007 / 0.076 / 0.076; R1 0.97 | 0.003 / 0.078 / 0.078; R1 0.99 |
| raw_R3_L27 | 0.000 / 0.056 / 0.056; R1 0.98 | 0.003 / 0.038 / 0.038; R1 0.96 | 0.000 / 0.043 / 0.043; R1 0.98 |
| km_null_L6 | 0.030 / 0.160 / 0.160; R1 0.46 | 0.017 / 0.146 / 0.146; R1 0.40 | 0.021 / 0.142 / 0.142; R1 0.43 |
| km_null_L27 | 0.009 / 0.082 / 0.082; R1 0.77 | 0.014 / 0.087 / 0.087; R1 0.78 | 0.007 / 0.062 / 0.062; R1 0.76 |
| raw_null_L6 | 0.000 / 0.002 / 0.001; R1 1.00 | 0.000 / 0.014 / 0.005; R1 1.00 | 0.002 / 0.005 / 0.002; R1 1.00 |
| raw_null_L27 | 0.005 / 0.042 / 0.020; R1 1.00 | 0.000 / 0.043 / 0.024; R1 1.00 | 0.002 / 0.043 / 0.020; R1 1.00 |

## Glossary
| Term | Meaning |
|---|---|
| Token | The feature vector for one 16 mm³ block of the CT, from the FM's last stage |
| Physics / reference features | HU intensity statistics + texture + 48 mm context + position. R0–R4 are increasingly rich label-free versions |
| Untrained / null encoder | The same network with random weights |
| Beyond-HU / beyond-physics | The FM beats the reference by ΔAUROC ≥ 0.05 (CI > 0) |
| L0 | Number of active features per token |
| R1 | Share of features matched (r ≥ 0.7) between models trained on different patient halves (reproducibility) |
| Twin score t_f | Per-feature version of R1 |
| sel_f | Concept selectivity of a feature |
| r_pert | Correlation of a feature's activations before and after shift / noise / HU-offset perturbations |
| v_f | min(t_f, sel_f, r_pert): weakest-link validity |
| C(τ) | Number of gated concepts covered by at least one feature with v_f ≥ τ; the area under C(τ) over τ ∈ [0.5, 0.9] is the primary metric (normalised, 0–1) |
| Chimera | A feature whose strongest activations mix non-adjacent concepts. As run, 'other' tissue counted as foreign; 'neutral' treats it as adjacent to everything |
| θ | AUROC of the twin score for predicting validity (does reproducibility predict validity?) |
| Consensus SAE | Features found in ≥ 3 of 5 SAE fits (r ≥ 0.7) |

**Source files** (in the project):
- `docs/IMAGING_SAE_LEAN_v1.md` (v1 plan), `docs/DECISION_MEMO_P1.md`, `docs/SANITY_PLAN_v1.md`, `docs/EXECUTION_LOG.md`
- `imgsae/data/p1/decision.json`, `fit/summary.json`, `gates.json`, `concepts.json`
- `imgsae/exploratory/p1_checks/README.md`
- `imgsae/exploratory/p1b_sanity/RESULTS.md` and `results/*.json`
