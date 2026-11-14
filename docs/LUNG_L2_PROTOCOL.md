# Lung L2 protocol: a feature-level audit of Sybil on NLST

- **Date fixed:** 2026-11-13, before any Sybil activation exists. **Status:** DRAFT, waiting for the lead's OK (Part A of the hand-over prompt).
- **Plan it executes:** `docs/PLAN_SYBIL_AUDIT_v1.md`. Section 1 lists what this protocol changes in the plan, and why.
- **Budget approved by the lead (2026-11-13):** ledger task `lung_l2_audit` $45.00 for S2 to S6; guard project limit `project_cap_usd` 72.00; monthly stop $29 per account unchanged; November on account `shforghani2002` only.
- **Rule from now on:** no test activation is extracted and no new outcome analysis of the existing L1 test scores is made before the hypothesis file (S5) is approved by the lead.

## 1. What changed from plan v1, and why
| # | Change | Why |
|---|---|---|
| C1 | The reconstruction-pair sub-study is kept but reframed: score-level and feature-level change, not AUROC | Simon et al., *Invest Radiol* 2025, already ran Sybil on 1,049 standard/bone, 1,961 standard/lung and 1,288 2 mm/5 mm pairs of NLST test participants and found no AUROC difference. Their abstract reports AUROC comparisons (DeLong) only; I could not open the full text. What moves inside one exam when only the kernel changes is, as far as I found, not published |
| C2 | New technical sub-study: true slice spacing ("z-fix") | Sybil's loader places slices at `SliceThickness`, not at the real distance between slices (pinned commit and current `main`, `sybil/serie.py`). In 44% of selected dev series the spacing is smaller than the thickness (ratio 0.5 to 0.9). At ratio 0.5 (578 dev, 400 test series) the chest is stretched 2× along z, and the 200-slice grid (500 mm) cuts its ends. Not raised in Sybil's GitHub issues. Cost: one extra inference per affected series |
| C3 | Image-derived measures computed in the same job, on the exact volume Sybil sees: lung volume, emphysema (% below −950 HU), lung 15th-percentile HU, body area, air noise, crop and pad flags | Naming features needs measured lung and body variables, not only the radiologist's form. CPU work that overlaps GPU time; no extra GPU cost |
| C4 | Score-level composition by known factors (Q1a) is the primary composition analysis; the unsupervised decomposition explains the rest | A regression of Sybil's logit on known variable groups is exact, cheap and does not depend on a dictionary passing its validity checks |
| C5 | The recorded-findings comparator is refitted on Sybil's **train** participants only, and used unchanged on dev and test | Dev is now analysis data. L1's comparator (train + dev) is kept as a reference only |
| C6 | Dev is called "used for model selection" | Sybil's `scripts/train.py` fits on train and validates on dev (`trainer.fit(module, train, dev)`). Sybil's dev accuracy is mildly optimistic. Test is clean |
| C7 | The linear probe on **h** is a reference, not a strict ceiling | A predictor built on nonlinear features of **h** can in principle beat a linear probe; Sybil's own head is a second reference |
| C8 | "Auditing Sybil" is corrected in the claims | It uses real nodule malignancy labels (LUNA25, a subset of NLST, biopsy or 2-year stability) and shows single false-alarm and miss cases. It has no patient-level outcome analysis, no radiologist form, no scanner or reconstruction analysis (it does show artefacts such as ECG leads and metal) and no held-out confirmation. Its findings (upper-lobe weighting, weaker response near the pleura, age in the background term, artefacts) become candidate checks on real outcomes |
| C9 | Series rule built and tested now (section 5); test exams use the split file's 6,715 series exactly as in L1 | Gate of plan section 4. 385 of the 6,715 test series are thicker than 2.5 mm (Sybil's paper dropped such series); they are kept and analysed as a technical stratum |
| C10 | Confirmatory hypotheses must involve a quantity never computed on test | The 15% to 19% "explained by the form", r = 0.61 within person and the false-alarm overlap were computed on test (post hoc). They cannot be "confirmed" there |
| C11 | Radiologist image-quality flags (`screen` table) and tumour location (`prsn` location flags) added | Second, human-recorded source for technical factors; location coding for misses |
| C12 | Extra pilot checks: repeat determinism, image-measure plausibility, measured z-stretch; extra S6 check: re-extracted test scores equal the L1 scores | Pipeline identity before any result is used |

## 2. Verified facts this protocol rests on
| Fact | Checked how | Source |
|---|---|---|
| Split: 10,179 train, 2,493 dev, 2,347 test participants; 6,715 test series, all found in IDC | split file and IDC index | `lung_l0/results/l0_results.json`, `lung_l1/results/s1_index.json` |
| Dev outcomes (exams): 1-year cancer 88 (baseline 38), 2-year 150 (65), 6-year 319 (137); 6-year negatives 2,463 (baseline 2,050); 149 participants with cancer | NLST tables | `lung_l2/results/s0_dev_counts.json` |
| Dev cancers: adenocarcinoma 60, squamous 38, small cell 20, other 31; stage IA/IB 73, II 12, III 20, IV 35; location central 19, upper 83, middle/lingula 9, lower 46 | NLST tables | same |
| Dev radiologist positive calls without cancer at 1 year: 2,476; their 1-year sensitivity 0.909 | NLST tables | same |
| Sybil structure at commit `d9fc81b9…`: 3D ResNet-18 → map 512 × 25 × 16 × 16; three pooled vectors (attention over slices of per-slice attention pools; attention over slices after a 1-D convolution of per-slice max pools; global max), joined to 1,536 → `hidden_fc` → 512 → ReLU = **h**; logit for year t = `base_hazard_fc(h)` + Σ_{j≤t} ReLU(`hazard_fc(h)`)_j | code read | `sybil/models/*.py` |
| Ensemble: mean of the five member probabilities, then per-year calibrator (linear map, clip, interpolation, averaged over its sub-calibrators); monotone, so ranks are kept except for ties | code read | `sybil/model.py`, `sybil/models/calibrator.py` |
| Input: lung window (center −600, width 1,500 HU), 8-bit, each slice resized to 256 × 256, resampled to 1.40625 × 1.40625 × 2.5 mm, centre crop or pad to 200 slices; padding value 0 after normalisation (≈ −600 HU) | code read; issue #74 | `sybil/serie.py`, `sybil/loaders/image_loaders.py` |
| Bulk cost on T4: 7.6 container-seconds and $0.0021 per series; all-in L1 $0.0023 per series | ledger runs 024 to 029 and result files | `lung_l1/results/run_*.json`, ledger |
| Month usage on `shforghani2002` on 2026-11-13: $21.07 | `budget.py` check | ledger `checks` |

## 3. Questions
Fixed now. Sybil's score is studied as a model output; claims about cancer need the test split.

- **Q1, composition. What is Sybil's score made of?**
  - Q1a (known factors): share of the variation of Sybil's 1-year and 6-year logit explained by each variable group (section 9.3): nodule findings on the form (N), other recorded findings (B), demographics and study year (D), image measures (I), technical factors (T); and the unexplained share.
  - Q1b (features): which internal features carry each share, and which carry the unexplained part. Does the unexplained part predict cancer beyond the form?
  - Q1c (stability): how much of the within-person stable part of the score comes from each group.
  - Q1d (causal technical tests): change of the score and of each feature group (i) between two kernels of the same acquisition, (ii) when slices are placed at their true spacing.
- **Q2, errors. Why is Sybil wrong?** False alarms in three classes (Sybil only, shared with the form model, form only); missed cancers at 1, 2 and 6 years by location, histology, stage, size, time to diagnosis and crop status.
- **Q3, use. Can the features be used?** U1 remove technical content (U1a feature subspace, U1b z-fix); U2 a reliability flag; U3 Sybil plus the form at the radiologists' sensitivity; U4 the probe reference.

## 4. Data and roles
| Group | Participants | Role | Rule |
|---|---|---|---|
| Dev | 2,493 | Discovery: decompositions, naming, thresholds, candidate hypotheses | All outcome-linked estimates cross-validated by participant (5 folds, seed 0) |
| Test | 2,347 | Confirmation, once | Closed until the hypothesis file is approved |
| Train | 10,179 | Fitting the form comparator only | No Sybil activation is extracted for train participants |
| Never used by Sybil | 11,432 (34 cancers) | Not used in S1 to S6 | S7 needs its own approval |

- **Outcomes:** exactly as in L0 and L1 (`nlst_l0.build`): `y1`, `y2`, `y6` per exam; a negative needs t cancer-free years; "late" = cancer 1 to 6 years after a negative baseline screen.
- **Form comparator F (L2):** `nlst_l0.logit_model()` (standardise + logistic, C = 0.3) on the recorded findings plus age, sex and smoking (`features_for`), fitted on train participants only: one model for `y1` on all screens, one for `y6` on baseline screens. Frozen in `lung_l2/l2_form.py` before S4.
- **Second dataset:** none open to an individual without an agreement. Duke DLCS (1,613 scans): all five Zenodo records "restricted", CC BY-NC-ND, request needed. P-ELCAP (Pamplona, 211 participants, 67 cancers, case-control): Zenodo request box, no formal agreement, CC BY-NC-SA. LUNA25 and NLSTseg are NLST subsets. Claims are limited to NLST unless the lead requests P-ELCAP or DLCS access (optional, section 15).

## 5. Series selection (done in S0, metadata only)
- **Source:** IDC index release 25.0.5 (`idc_index`, `ct_index`, `volume_geometry_index`; SHA-256 checked against the release files), joined to `imgsae_data/idc_index_25.0.5/nlst_series_meta.csv` (203,111 NLST CT series; SHA-256 `7712A8B8…1A1198E`). No image and no outcome was read. Sybil's annotations are not used (its own dev rule prefers an annotated series, and annotations exist only for cancers).
- **Rule `sharp_thin`** (`lung_l2/series_rule.py`): drop localizers and series with fewer than 40 images; then sharper kernel class first, then thinnest slices, then most slices, then lowest series number, then UID.
- **Test of the rule** against the split file's choice (`results/s0_series_rule.json`): chosen among five fixed candidate rules on a random half of test participants (seed 0), checked on the other half.

| Rule | Exact, half A | Exact, half B | Same kernel class and thickness, all |
|---|---|---|---|
| **sharp_thin (kept)** | **0.989** | **0.986** | **0.991** |
| thin | 0.970 | 0.960 | 0.968 |
| count (Sybil's own dev rule, without annotations) | 0.948 | 0.943 | 0.950 |
| thin_soft (control) | 0.446 | 0.420 | 0.435 |

- Gate (≥ 0.90 same kernel class and thickness): **passed**.
- **Dev:** a series for 7,348 of 7,361 dev CT studies (99.8%). Six person-years have two studies; both studies of each are dropped (12 studies, outcome-blind). Expected dev exams: 7,336.
- **Test:** the split file's 6,715 series, exactly as in L1. No other test series is scored except the T4 and T5 variants (section 7).
- **Kernel pairs available** (same thickness, other kernel class, slice count within 2%): dev 3,895 exams, test 3,523 (`results/s0_pairs_count.json`).

## 6. What is saved for every series (one pass)
One `.npz` and one `.json` per series and variant on the volume (`/vol/l2/<variant>/<series_uid>.*`), committed every 25 series. No image is kept.

**Per ensemble member (5):** `h` (512, float32); the 512 numbers before ReLU; the joined pooled vector (1,536) entering `hidden_fc`; raw hazards (6); base hazard (1); member logits (6); `volume_attention_1` (25), `volume_attention_2` (25), `image_attention_1` (25 × 256) as float16.
**Per series:** calibrated ensemble probabilities (6); mean member probability (6); DICOM tags of one image (maker, model, kernel, slice thickness, pixel spacing, kVp, exposure, tube current, exposure time, reconstruction diameter, gantry tilt, spiral pitch, CTDIvol if present, image type); number of files and of readable images; sorted slice positions; true spacing (median difference of positions); thickness/spacing ratio; number of real (not padded) slices in the 200 grid; in-plane pad or crop fraction; the image measures below; timings; errors.
**Once per run:** head weights of each member (`hidden_fc`, `hazard_fc`, `base_hazard_fc`), the calibrator JSON, the SHA-256 of every checkpoint, the Sybil commit, package versions, GPU name.

**Image measures** (computed on the tensor fed to the network, converted back to HU: v = x · 87.1849 + 128.1722, HU ≈ −600.5 + (v/256 − 0.5) · 1499, to within one 8-bit step of 5.9 HU; padded voxels, known from the resampled shape before crop or pad, are excluded; the pilot checks the inversion: median HU of outside air within −1,000 ± 30):
- lung mask: HU < −400, minus 3-D connected components touching the real in-plane border (outside air), keep the two largest components;
- `lung_vol_app_ml` (apparent, 1.40625² × 2.5 mm³ per voxel) and `lung_vol_ml` (true = apparent ÷ z-stretch);
- `laa950_pct` (share of lung voxels below −950 HU), `lung_p15_hu`, `lung_mean_hu`;
- `body_area_cm2` at the lung's middle slice (true in-plane area);
- `air_noise_sd_hu`: SD of HU in outside air at least 10 voxels from body and border, on the middle 50 real slices;
- `lung_cut_z` (lung voxels in the first or last real slice of a z-cropped volume), `lung_cut_xy` (lung voxels within 2 voxels of a real in-plane border), `n_real_slices`, `lung_z_extent_app_mm`.

**Variants:**
- `main`: the selected series, Sybil exactly as published.
- `zfix` (dev D5, test T5): series with spacing/thickness ≤ 0.65; identical, except that the z voxel size given to Sybil's resampling is the true spacing.
- `pair` (dev D4, test T4): the soft-kernel partner of the selected series, Sybil as published.

## 7. Steps, gates and cost
| Step | What | Series | Projected cost | Gate to continue |
|---|---|---|---|---|
| S1 | Dev manifest (rule of section 5), fixed random participant order (seed 0) per tier; D4 and D5 lists | — | free | ≥ 95% of dev exams (pid × year in the tables, 7,362) get a series; 0 duplicate pid-year |
| S2 | Pilot: the first 300 series of the D1 order, all saves, `zfix` also for every pilot series with ratio < 0.95; 50 of the 300 also on L4 | ≈ 300 + 130 variants + 50 | ≈ $1.2 (allocation $2.00) | All checks of section 8 |
| S3 | Dev extraction: D1 baseline (remaining 2,184 of 2,484), D2 year 1 (2,442), D3 year 2 (2,410), D4 500 kernel partners of D1 exams (seed 0, stratified by maker), D5 `zfix` for all dev series with ratio ≤ 0.65 (≈ 909) | ≈ 8,445 | ≈ $20.2 (allocation $22.00) | < 5% failures per tier; every saved series passes the recomputation check of G2b |
| S4 | Analysis on the PC (section 9) | — | free | Section 9.8 |
| S5 | Freeze ≤ 5 hypotheses (section 10). **Stop for the lead's OK** | — | free | Hashed; second reviewer; lead OK |
| S6 | Test extraction: T1 baseline 2,279, T2 year 1 2,243, T3 year 2 2,193 (all 6,715 split-file series); T4 500 kernel partners and T5 `zfix` (≈ 743) only if a frozen hypothesis uses them; then the frozen analysis once | 6,715 to ≈ 7,958 | ≈ $15.5 to $18.4 (allocation $20.00) | Section 11 |
| S7 | Optional, separate approval: never-used participants; full maps for a few hundred scans | — | ≈ $10 | S6 confirmed something worth showing |
| S8 | `RESULTS_L2.md`, figures, manuscript outline | — | free | — |

Projection rule (after S2): cost = series × measured container-seconds per series ÷ 3,600 × hourly rate × 1.2. The numbers above use L1's 7.6 s on T4 ($0.9072 per hour with 4 cores and 16 GiB). Expected total ≈ $39.8 of $45.00.
**Priority if money is short:** D1 → D2 → D5 for done tiers → D4 → D3. Minimum useful set D1 + D2 and T1 + T2.
**Stop points without spending more:** after S2 (a pilot check fails), after S4 (nothing holds on dev, section 9.8).

## 8. Pilot checks (S2), each a stop if it fails
| Check | Pass mark |
|---|---|
| G2a demo | Sybil's published demo case: six calibrated probabilities within 0.005 of the published values (L1 got 0.0) |
| G2b recomputation | For every pilot series and member, on the PC: (i) ReLU of the saved pre-ReLU vector equals `h` exactly; (ii) `hidden_fc` applied to the saved 1,536 vector equals the pre-ReLU vector within 1e-3 (max abs); (iii) the six logits recomputed from `h` and the saved head weights equal the saved logits within 1e-4 |
| G2c ensemble | Calibrated probabilities recomputed from the five member logits and the saved calibrator equal the saved ones within 1e-4 |
| G2d determinism | 20 pilot series run twice in different containers: max difference of calibrated probabilities ≤ 1e-4 |
| G2e image measures | Computed for ≥ 98% of pilot series; true lung volume 2,000 to 9,000 ml and emphysema 0% to 60% for ≥ 95%; median outside-air HU within −1,000 ± 30 for ≥ 95%; added CPU time does not raise the mean seconds per series by more than 10% |
| G2f z-stretch is real | For pilot series with ratio ≤ 0.65, apparent ÷ true lung z-extent is within 10% of thickness ÷ spacing in ≥ 90% of them. If not, D5, T5 and every z-fix question are dropped and this is logged |
| G2g cost and GPU | Seconds and dollars per series measured on T4 and on L4 (50 series); the cheaper one is used from S3 on; projection made |
| G2h failures | < 5% of pilot series fail |

## 9. Analysis on dev (S4)
All on the PC with the project venv. Participant-grouped 5-fold cross-validation (seed 0) wherever a model sees outcomes. Participant bootstrap, 2,000 draws, for intervals. Within each table, Benjamini–Hochberg FDR at q < 0.05. Dev results are discovery; none is a confirmed claim.

### 9.1 Scores
- Published score `s_t`: calibrated ensemble probability for year t. Used for AUROC and thresholds.
- Analysed score `ℓ̄_t`: mean of the five member logits for year t. Used for decomposition, because it is linear in each member's contributions.
- Check P1: Spearman(`ℓ̄_t`, `s_t`) ≥ 0.98 on dev for t = 1 and 6. If it fails, the decomposition is reported per member only.
- Primary horizons: t = 1 on all screens (`y1`), t = 6 on baseline screens (`y6`). Secondary: t = 2 on baseline screens.
- Gating: hazard unit j is "on" for member m and exam x if its raw hazard > 0. The share of (exam, member, unit) that are on is reported.

### 9.2 Exact contributions
For member m, year t, exam x: effective weight `w = W_base + Σ_{j≤t, unit j on} W_haz,j` and bias `b` likewise, so `ℓ_{m,t}(x) = w · h_m(x) + b` exactly. With a decomposition `h = μ + Σ_i a_i d_i + r`: contribution of feature i is `a_i (w · d_i)`; plus an intercept term `b + w · μ` (it varies with gating) and a residual term `w · r`. Group contribution `G_g` = mean over members of the sum over features of group g. Share of group g = Cov(G_g, ℓ̄_t) / Var(ℓ̄_t); shares of all terms sum to 1.

### 9.3 Variable groups (for Q1a and naming; no outcome)
- **N, nodule findings on the form:** all `read` variables of `nlst_l0` except the `ab` flags (largest nodule size, margins, attenuation, upper-lobe location, counts, screen result categories, comparison-with-prior items for follow-up exams).
- **B, other recorded findings:** `ab52` to `ab65` (adds `ab60` significant cardiovascular abnormality, `ab64`, `ab65`, which the L1 comparator did not use; naming only).
- **D, demographics and time:** age at scan, sex, current smoking, race (white, black, other), study year.
- **I, image measures:** section 6.
- **T, technical:** maker; scanner model (models with < 50 dev exams pooled); kernel class; kernel sharpness rank within maker; slice thickness; z-stretch (thickness ÷ spacing); kVp; exposure; tube current; reconstruction diameter; number of images; scan length; gantry tilt ≠ 0; regular-3-D flag; thickness > 2.5 mm; `n_real_slices`; `lung_cut_z`; `lung_cut_xy`; the radiologist's image-quality items (`ctdxqual` and its sub-items).

### 9.4 Decomposition arms
- **Input:** `h_m` of all dev `main` exams, per member, each dimension z-scored with dev mean and SD; dimensions with SD < 1e-6 (dead units) dropped and counted.
- **Arms, K = 64 features each (K = 128 as sensitivity):**
  - A1 sparse autoencoder: `imgsae/imgsae/sae.py` `fit` (Matryoshka BatchTopK; k = K/16 = 4; defaults otherwise), 5 seeds, symmetric consensus (`consensus_codes_cl`, r ≥ 0.7, ≥ 3 of 5 seeds);
  - A2 PCA, first K components;
  - A3 ICA (FastICA after PCA to K), 5 seeds, same consensus rule;
  - A4 NMF on `h_m / SD` (non-negative), 5 seeds, same consensus rule;
  - A5 k-means, K clusters, hard assignment, 5 seeds, same consensus rule;
  - A6 raw units: the K units with the largest variance of contribution to `ℓ_{m,6}` (|w_j| × SD(h_j)), a label-free rule.
- **Same rules for all arms:** same K, same consensus rule where a seed exists, same replication, naming and contribution code.

### 9.5 Validity pass marks (per arm; held-out folds)
| Mark | Pass |
|---|---|
| V1 function kept | `h` replaced by the arm's reconstruction: Pearson r(ℓ_{m,t}(ĥ), ℓ_{m,t}(h)) ≥ 0.98 for t = 1 and 6 (mean over members), and |ΔAUROC| ≤ 0.005 for `y1` (all screens) and `y6` (baseline) using ℓ̄_t(ĥ) |
| V2 seed stability | Two disjoint seed sets (0–4 and 10–14): median best-match activation correlation ≥ 0.70 and ≥ 50% of features matched at r ≥ 0.7 (PCA and raw units pass by construction) |
| V3 replication across members | A feature family = matched features (Hungarian, activation r ≥ 0.7 across dev exams) present in ≥ 3 of 5 members. Pass: ≥ 16 families (25% of K) |
| V4 split-half naming | Two halves of dev participants (seed 0): median correlation of a family's association vector between halves ≥ 0.70, and the same group label in both halves for ≥ 70% of named families |

An arm is valid if V1 to V4 pass. **Primary arm** = the valid arm with the most named, replicated families; on a tie, the simpler arm in the order raw units, PCA, ICA, NMF, k-means, sparse autoencoder. If the sparse autoencoder is not best, this is reported as it is. If no arm is valid, feature-level claims are dropped; Q1a, Q1d, U1b, U2 (fixed rule) and U3 continue.

### 9.6 Naming (replicated families; family activation = mean of the members' z-scored activations)
- Associations with every variable of section 9.3: Spearman ρ; binary variables as rank-biserial r (= 2 · AUROC − 1). FDR over all family × variable tests.
- Group label: participant-grouped 5-fold CV ridge of the family activation on all groups' variables; group shares by Shapley values over the five groups (32 subset fits). **Named g** if CV R² ≥ 0.10 and the share of g ≥ 0.50 of the R²; **mixed** if CV R² ≥ 0.10 and no group reaches 0.50; **unnamed** if CV R² < 0.10.
- Reported per family, not used for the label: AUROC for `y1`, `y2`, `y6`; added value over F (cross-fitted, likelihood-ratio test); within-person correlation between T0 and T1.

### 9.7 Analyses per question
- **Q1a:** CV R² of ridge and of gradient boosting (`HistGradientBoostingRegressor`, max_iter 300, learning rate 0.05, as in L1 post hoc) of `ℓ̄_1` (all screens) and `ℓ̄_6` (baseline) on all groups; Shapley shares by group from ridge (32 subset fits). For all exams and for non-cancer exams. Unexplained part U = ℓ̄ minus the out-of-fold ridge prediction.
- **Q1b:** group shares of section 9.2 with the primary arm; covariance of each family's contribution with U; does U add to F (cross-fitted logistic `y ~ F + U` versus `y ~ F`: ΔAUROC with interval, likelihood-ratio test) for `y1` and `y6`.
- **Q1c:** participants with T0 and T1 exams. Stable share of group g = Cov(G_g(T0), ℓ̄(T1)) / Cov(ℓ̄(T0), ℓ̄(T1)); for all and for participants without cancer within 2 years of T0.
- **Q1d (i) kernel pairs (D4):** Δ = ℓ̄_t(sharp) − ℓ̄_t(soft): mean, SD, intraclass correlation, SD(Δ) ÷ SD(ℓ̄_t across exams), share of pairs whose flag at τ90 differs, change of each G_g; by maker.
- **Q1d (ii) z-fix (D5):** same statistics for ℓ̄_t(zfix) − ℓ̄_t(main); separately for exams with `lung_cut_z`; AUROC of main and zfix in the D5 exams (descriptive: few cancers).
- **Q2:** τ90 = 90th percentile of `s_1` among dev exams with `y1` = 0; τ_rad = the threshold with the radiologists' dev positive-call rate (2,573 of 7,362). τ90 for F likewise.
  - False alarms (`y1` = 0): Sybil only, shared, form only, versus true negatives (both below). Standardised mean difference (SMD) of every family activation, every G_g and every I and T variable; FDR.
  - Misses at 1 year (all screens), 2 and 6 years (baseline): missed (`s_t` < τ90 of that horizon) versus caught; SMDs as above; counts by location (central, upper, middle or lingula, lower), histology (adenocarcinoma, squamous, small cell, other), stage (I, II–III, IV), lesion size tertile, time to diagnosis, `lung_cut_z`, z-stretch ≥ 1.54. Exact binomial intervals. No claim for a subgroup with fewer than 10 cancers.
- **U1a technical removal:** per fold, ridge of `h_m` on T (one-hot categoricals) fitted on training folds; held-out `h'_m = h_m − (T-fit − its dev mean)`; logits recomputed with Sybil's head (gating recomputed), ensemble through Sybil's calibrator. Report ΔAUROC (`y1` all, `y6` baseline) and the false-alarm-rate spread: SD of the false-alarm rate at the overall 90%-specificity threshold across maker × kernel-class groups with ≥ 100 non-cancer exams, after ÷ before; the same spread for F as a case-mix reference. Dev qualification for a hypothesis: ΔAUROC ≥ −0.01 at both horizons, spread ratio ≤ 0.80, and Sybil's spread before removal larger than F's.
- **U1b z-fix:** as Q1d (ii); qualification: |Δℓ̄_6| ≥ 0.25 × SD(ℓ̄_6) in ≥ 30% of D5 exams, or a flag change at τ90 in ≥ 10%.
- **U2 reliability flag:** two candidate rules. R-fixed: flag if T-share |G_T| ÷ Σ_g |G_g| is above its dev 80th percentile, or z-stretch ≥ 1.54, or thickness > 2.5 mm, or any radiologist quality item, or air noise above its dev 90th percentile. R-learned: CV logistic model of "Sybil-only false alarm" on families and I and T variables; flag the top 20%. Measure E = Sybil false-alarm rate − F false-alarm rate (τ90 each) among `y1` = 0 exams; statistic E(flagged) − E(unflagged); Sybil's sensitivity in flagged and unflagged (descriptive). The rule with the larger dev CV statistic is the one that can be frozen.
- **U3 Sybil plus form:** cross-fitted logistic combination C of logit(`s_1`) and F's logit (as in L1). At the radiologists' dev sensitivity for `y1` (0.909): false alarms per 1,000 screens for the radiologists' call, Sybil, F and C. Dev qualification: C ≤ 0.80 × the better of Sybil and F. For exams where C removes a Sybil false alarm: SMDs of families and groups.
- **U4 references:** L2-logistic probe on the five members' `h` joined (2,560 numbers; C by inner CV), the logistic model on each arm's family activations, and Sybil's own `s_t`: CV AUROC for `y1` and `y6`.

### 9.8 Gate S4 → S5 and S6
- At least one candidate hypothesis holds on dev: effect in the stated direction, dev 95% interval excluding the null value, and the same sign in both dev halves.
- A feature-based hypothesis also needs at least one valid arm (section 9.5).
- If no candidate holds: stop before any test spending, report plainly; the L1 paired result is the fallback paper.

### 9.9 Power on dev, stated in advance
- 7,226 exams without 1-year cancer, about 723 Sybil false alarms at τ90 and 2,476 radiologist false alarms: false-alarm analyses are well powered (an SMD of 0.15 is detectable).
- 88 one-year cancers (≈ 10 one-year misses expected at τ90): misses at 1 year are descriptive only. 6-year baseline: 137 cancers against 2,050 negatives.
- Kernel pairs (500) and z-fix exams (≈ 909) are paired, outcome-free comparisons: well powered for score change; not for AUROC change.

## 10. Hypothesis freeze (S5)
- At most five hypotheses, chosen from dev results. Each states: the statistic, the population (exams, horizon), the direction, the margin, the null value and its test.
- Each must involve at least one quantity never computed on test: a family activation, a group contribution, an image measure, a kernel-pair or z-fix change, or a feature-based rule.
- A hypothesis computable from the L1 test scores and the form alone is "partly seen". At most one may enter the family, and every report labels it.
- Holm correction across the family, family-wise α = 0.05, one-sided in the stated direction. Intervals by participant bootstrap, 2,000 draws.
- Candidate templates (not commitments): H-T1 kernel sensitivity (Q1d i); H-T2 z-fix change (U1b); H-C1 technical share of `ℓ̄_6` ≥ a margin (Q1a); H-E1 a named group enriched in Sybil-only false alarms (Q2); H-U1 technical removal non-inferior with narrower spread (U1a); H-U3 false alarms cut at the radiologists' sensitivity (U3, partly seen).
- The file `lung_l2/HYPOTHESES_L2.md` and the frozen analysis script are hashed (SHA-256), checked by a second reviewer, and approved by the lead before any test activation is extracted. The thresholds set on dev (τ90, τ_rad, rule cut-offs, ridge settings, family definitions) are frozen in a JSON file with the same hash list.

## 11. Test confirmation (S6)
- Extraction checks before the analysis: G2a demo; failures < 5% per tier; G2b and G2c on every saved series; **identity check:** calibrated probabilities of the re-extracted `main` series equal the L1 scores within 1e-4 for ≥ 99% of the 5,412 L1 series.
- The frozen analysis runs once on the frozen thresholds and definitions. Families are carried to test by encoding test `h` with the frozen dev dictionaries; nothing is refitted on test.
- Anything outside the frozen file is labelled exploratory. Every number states its exams, participants and cancers.

## 12. Budget rule
- Every launch goes through the guard (`imgsae/exploratory/p1b_sanity/cloud/budget.py`): task `lung_l2_audit` ≤ $45.00; project ≤ `project_cap_usd` 72.00; month (Modal billing + open worst cases) ≤ $29.00. A refused launch is not made. Usage is checked before every launch.
- Step allocations inside the task: S2 $2.00, S3 $22.00, S6 $20.00, collection and surprises $1.00. If measured plus projected cost of a step exceeds its allocation by more than 10%, stop and report.
- Account `shforghani2002` only. The reserve and the second account are not used. The lead's volumes and apps (`vs-workspace-data`, `vs-radiomics-vol`, `picai-dataset-vol`, `lupi-data`) are never touched.
- T4 or L4 only; container timeout ≤ 60 minutes; ≤ 4 containers at once; detached spawn; one saved unit per series; volume committed every 25 series; images deleted after each series; results copied to the PC and checked (file count, hashes) before the volume `imgsae-nlst-l2` is deleted.
- **November 2026:** month room ≈ $7.90 on 2026-11-13. Pilot first; then D1 in the fixed order, in launches of ≤ 4 containers, as long as the month check allows. The rest waits for 1 December.

## 13. Who runs what
- Paid runs: a lower-cost agent (Sonnet) with this protocol, the exact run plan and the stop list. It does not change thresholds, code or the order of tiers.
- Before any result is used, I check its report against the files: ledger runs opened and closed, per-series files = manifest rows (minus logged failures), head-weight and checkpoint hashes, the volume list (only `imgsae-nlst-l2`), and the PC copy.
- All analysis on the PC by me. Every decision, deviation and result goes into `docs/EXECUTION_LOG.md`; the current state into `STATUS.md`.

## 14. Not allowed
- Extracting test activations, image measures or variants, or making any new outcome analysis of the L1 test scores, before the hypothesis file is approved.
- Using outcomes, Sybil's annotations or the split file's `cancer_in_1` to choose series.
- Using train participants for anything except fitting F.
- Changing a threshold, gate, pass mark, hypothesis or the frozen analysis after the data it governs are seen. A later change is a logged deviation and is reported.
- Refitting anything on test.
- Exceeding a budget, bypassing the guard, using the reserve or the second account without the lead's word; GPUs other than T4 or L4; timeouts above 60 minutes; more than 4 containers.
- Touching any volume or app other than `imgsae-nlst-l2` and the app `imgsae-lung-l2`.
- Claiming more than a test showed; dropping a failed gate or a negative result from the report.

## 15. Open items for the lead
1. OK for this protocol (and the budget diff in the report).
2. Second reviewer for the hypothesis file: a colleague, or a fresh reviewer agent?
3. Optional, free: request access to P-ELCAP (Zenodo request box) or Duke DLCS (restricted). Both need the lead's name; they would allow a small external check of one or two confirmed findings.

## 16a. Amendments after the pilot (logged deviations, approved by the lead on 2026-11-14)
- **A1, G2f:** judged on the pilot series whose lung is not cut by the 200-slice grid (all 7 within 0.5%); the series where the crop cuts the lung (30 of 37; 26 of 27 at stretch 2.0) show the predicted effect of the stretch. z-fix (D5, T5, U1b, Q1d ii) is kept. The share of series with `lung_cut_z` is reported by stretch.
- **A2, G2e:** accepted. Analysis rule: if `lung_vol_ml` < 1,500, all image measures of that series are set missing and the flag `T_lung_at_edge` = 1 is added to the technical group. Toshiba's air offset (about −38 HU) is reported; the cloud job is unchanged.

## 16. Files
- Work folder `imgsae/exploratory/lung_l2/`: `series_rule.py`, `s0_idc_meta.py`, `s0_series_explore.py`, `s0_series_rule_test.py`, `s0_pairs_count.py`, `s0_dev_counts.py`, `results/` (S0 outputs), later `cloud/`, `l2_form.py`, `s4_*.py`, `HYPOTHESES_L2.md`, `RESULTS_L2.md`.
- Data (not in git): `imgsae_data/idc_index_25.0.5/` (IDC release files with their SHA-256 files; `nlst_series_meta.csv`).
- Literature read in S0: Sobieski et al., *Auditing Sybil*, arXiv 2602.02560v2 (ICML 2026), full text; Mikhael et al., *J Clin Oncol* 2023, full text with appendix; Simon et al., *Invest Radiol* 2025 (abstract); Zhuang et al., IEEE EMBC 2024 (abstract); Reeves et al., *Radiol Cardiothorac Imaging* 2026; Lee et al., *Radiology* 2025; Phellan Aro et al., *Chest* 2026; Gaur et al., MELBA 2025 (arXiv 2512.22242); Wang et al., *Eur Radiol* 2025; Simon et al., *Sci Rep* 2023; Mammo-FM (arXiv 2512.00198, a sparse autoencoder on a breast risk model, preprint). No published work decomposes Sybil's or another lung screening model's internal representation against real outcomes, radiologist findings and technical factors.
