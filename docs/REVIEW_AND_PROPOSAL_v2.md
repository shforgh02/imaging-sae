# Review of Phase 1, Stage A and plan v2, with the proposal (2026-11-09)

For Shayan and his agent. This is a desk review of the evidence in this repo; nothing was re-run. Ideas that have not been tested appear as **tests** in §4, not as findings. If this is adopted, log it in `docs/EXECUTION_LOG.md`.

## 0. Goal (unchanged from lean v1)
- **Core question.** Given fixed foundation-model (FM) embeddings, do SAEs give more valid, interpretable and reproducible features than other decompositions? And does reproducibility predict validity?
- **FM vs physics is a separate question** (user decision). It is used only to tier concepts by difficulty, never as a gate on the SAE question.

## 1. What the data show
**Phase 1 NO-GO.** The verdict is valid as registered but says little about SAEs. It came from faults in the plan's design, not in its execution:
1. **Chimera rule.** It counted 'other' as a foreign concept, which rejected 79–100% of features for every method. This produced the degeneracy.
2. **Size rule.** M 425, k 27 and 3k steps gave a dense SAE (R1 0.04). The resulting consensus was 34 broad tissue features.
3. **Gate S.** It was run on organ groups that physics already saturates, and its reference leaked a z coordinate derived from the masks.

**Stage A** was executed well: every script reproduces an official number first, and one thing changes at a time. Evidence on the core question:
- **Same configuration, no tuning edge (rep 0).** At M 425 and L0 6, the SAE scores 0.328 against k-means 0.273 ('other'-neutral area).
- **Tuned SAE (M1024 k6, 12k steps).** At L0 6 and 425 matched features it beats k-means, raw channels and sparse varimax in 3 of 3 replicates, under both rules:
  - 0.39–0.40 vs ≤ 0.27 on the 'other'-neutral rule;
  - 0.26–0.28 vs ≤ 0.05 on the rule as run.
- **Where the baselines lose (medians):**

  | Method | Selectivity | r_pert | Twin score |
  |---|---|---|---|
  | k-means | 0.50 | 0.64 | |
  | Raw channels / sparse varimax | 0.40–0.44 | 0.46–0.49 | |
  | SAE | 0.61 | 0.79 | 0.47 |

- **Consensus at the tuned configuration (rep 0 only).** About 410 features cover as much as the 1,024 single-fit features (area 0.562 vs 0.561). At 425 matched features it scores 0.562 vs 0.432. It is also more reproducible (twin score 0.71 vs 0.49; R1 0.51 vs 0.20) and more robust (r_pert 0.90 vs 0.79). This is the omics pattern again.
- **The FM knows anatomy beyond physics** (A1): vertebral level (13 of 24 levels), lobes when labels are few, and side from context. The untrained network adds nothing over physics.

**Bottom line:** there is a credible SAE signal on the core question. It is not yet a result; the gaps are in §2.

## 2. Gaps (adequacy of the trials so far)
1. **Unequal tuning.** The SAE got 8 configurations, chosen on rep 0; k-means only ran at M 425. There is no ICA and no sparse dictionary learning, so the reviewer's first question ("isn't this just sparse coding?") is open.
2. **No ceiling.** An area of 0.40 cannot be interpreted without the maximum achievable on this embedding under this ladder, and the ladder itself is uncalibrated.
3. **Coverage only, no precision.** Interpretability is a property of each feature, so the share of valid features is needed.
4. **θ (the original D2) has never been estimated.** Phase 1 had only 2 valid features; at the tuned configuration it is now estimable.
5. **The method-level R1–validity inversion is partly built in.** Raw channels are the identity and varimax is deterministic, so their R1 ≈ 1 by construction. Claim C4 must rest on feature-level θ.
6. **Organ concepts are saturated by physics.** A method that "finds organs" may only be finding HU and position. A concept tier where the FM carries more than physics is needed: vertebral level, lobe, side.
7. **Weak independence.** All replicates re-split the same 150 patients, and the configuration was picked on rep 0. Only the sealed 555 scans fix this.
8. **D3 shortcut audit** has not been repeated at the tuned configuration.
9. **Validity counts only the 33 labelled groups.** Features for unlabelled tissue (fat, bowel content, air) count as invalid, so precision is underestimated for every method. Say so in reports.

## 3. Plan v2: assessment
**Keep:**
- 'other'-neutral as the primary rule, with 'orig' as a sensitivity analysis;
- the label-free R4 reference;
- leaf concepts;
- equal tuning;
- nulls;
- θ;
- 555 sealed scans with J = 10, Holm correction, registration and logging.

**Change:**
- **Scope is back to v0 width.** Three pillars, nnU-Net controls, a second CT FM, causal ablation, transfer, label efficiency, readers and external PI-CAI, all within 4–6 months. Answer one question first.
- **G1(a) S2 and G1(c) test the encoder, not the decomposition.**
  - G1(c) on organ groups can fail even if the SAE is the best decomposition. k-means scores 0.27 on CT-FM, 0.21 on physics and 0.16 on the untrained network.
  - S2 already passes on dev (13 of 24 vertebrae).
  - → Make both descriptive or secondary, not stop rules.
- **G1(d), the nnU-Net positive control.** It is a different embedding and needs encoder engineering. A supervised oracle on the same embedding is cheaper and gives the exact ceiling (test T3). Keep nnU-Net as a later option.

## 4. Proposal
### Stage 1a: tests on dev data first
- 150 scans, existing arrays, about 1 day. Code goes in `imgsae/exploratory/v2_ct/`.
- Each test first reproduces an A3 row.
- Setup: CT-FM input, production halves for reps 0–2, the production ladder (`common.evaluate`), both chimera rules, and the area at 425 matched features.

| ID | What | Spec | Decides |
|---|---|---|---|
| T1 | Equal tuning | soft k-means at M 1024 and 2048 with L0 6, plus M 1024 with L0 1 (`p1_fit.Model('soft_kmeans')`) | D1v2 |
| T2 | Classical decompositions | FastICA (d components, whitened, fit on 100k rows), split-signed, top-6. Sparse dictionary learning with 1,024 atoms and OMP k 6, split-signed; the fit-phase lasso α is set to give about k non-zeros | Is the gain specific to the SAE or to sparse coding? |
| T3 | Ceiling | Oracle: multinomial LR (C 1, balanced, T1b caps) trained on the fit half's labels. Its class probabilities are the features, run through the same ladder | Ladder calibration; the SAE as % of the ceiling |
| T4 | Precision | Share of V0 features with v ≥ 0.7, plus C(0.7) and the feature count | Interpretability per feature |
| T5 | θ | Exactly as `p1_fit`: valid = sel ≥ 0.7, not chimeric, gated, r_pert ≥ 0.7, V0. For the tuned single SAE and its consensus | The original D2 |
| T6 | k = 1 sparse probing | For each concept, pick the best single feature by AUROC on the fit half, then test it on the other half. Organ groups, vertebral level and lung lobe (dominant leaf ≥ 0.5, as in A1 T3). References: dense CT-FM and dense R4 probes on the same split | Do single features capture FM-specific concepts? (threshold-free, SAEBench-style) |
| T7 | Consensus | 5-fit consensus at M1024 k6 12k, for reps 1–2 | H3 |
| T8 | Shortcut | D3 share at the tuned configuration | D3 |

- **Cost.** T1–T6 and T8 run on CPU; the slowest is k-means at M 2048. The SAE rows run on a Modal L4 for about $1–2 including T7.
- **Further SAE grid points.** If any are added (k 4/8, M 2048), the baselines get the same number of configurations, chosen on the same replicate.

### Revised gate G1 (fix before running T1–T8)
- **G1-main.** The best tuned SAE (single or consensus) beats the best equally tuned baseline, including ICA and dictionary learning. The comparison uses the matched-425 'neutral' area, must hold in 3 of 3 reps, with a mean gain ≥ 0.05.
  - If it fails and dictionary learning ≈ SAE: reframe as "sparse coding beats clustering and rotations".
  - If it fails against k-means or ICA: stop the SAE paper and write a methods note.
- **G1-cal.** The oracle covers ≥ 20 of the 32 gated concepts at C(0.7). If it doesn't, the ladder thresholds are the bottleneck: fix them with sweeps before going further.
- **Descriptive only:** SAE as % of the oracle, precision, θ, k = 1 probing per concept tier, nulls (untrained and physics SAE at the tuned configuration), S2.

### Confirmation: 555 sealed scans, J = 10, Holm
- **H2:** tuned SAE vs the best tuned baseline (area at matched L0 and 425 features); superiority.
- **H3:** consensus vs single fit; non-inferiority on area (margin 0.05), and superiority on R1.
- **H1:** θ.
- **H5 (new):** k = 1 AUROC, SAE vs the best baseline, on FM-specific concepts (vertebral level, lobe).
- **Secondary:** precision, % of the oracle, nulls, shortcut share.
- **Encoding:** CT-FM plus perturbations. Untrained-network encodes only if compute allows.

### Order
1. Stage 1a (T1–T8), then G1.
2. Freeze the SAE and baseline configurations on the same tuning budget, then register.
3. Encode the 555 scans and run the confirmation once. This is the core of the CT paper (Radiology: AI or MedIA).
4. Then the second leg: PI-CAI (H4, non-inferior to the texture increment over PSAD + age + volume, as in v1) and the V4 readers.
5. Later: nnU-Net control, a second FM, causal ablation, transfer, the P3 cohorts.

## 5. Short answers to the packet's §9 questions
1. **Is the v1 → v2 transition defensible?** Yes, if:
   - the Phase 1 memo stays as written;
   - every change is logged with the evidence that prompted it;
   - both chimera rules are reported;
   - confirmation runs only on the 555 sealed scans with a frozen protocol.
2. **Positive control.** Use the same-embedding oracle (T3); nnU-Net is optional.
3. **Beyond-physics test.** The R² < 0.5 threshold is arbitrary. Prefer T6 on FM-specific concepts, and report R² descriptively.
4. **Gates and power.** G1 as revised above. J = 10 on 555 scans (about 278 patients per half) is adequate.
5. **Scope.** CT plus PI-CAI plus readers is enough for Radiology: AI or MedIA. Nature Communications would need at least 2 FMs and a clinical leg, so later.
6. **Fairness.** Matched L0 and feature count, the same tuning budget on the same replicate, plus ICA and dictionary learning.
7. **Second CT FM.** Defer until after the CT confirmation.
8. **H4.** Non-inferiority against the texture-baseline increment over PSAD + age + volume (as in v1).
