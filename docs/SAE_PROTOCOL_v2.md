# Confirmation protocol v2: SAE vs equally tuned decompositions on CT-FM (555 sealed scans)

**Status:** DRAFT, revision 2 (2026-11-10), for the project lead's review. Not registered. Nothing in it has been run. The 555 confirmation scans have not been downloaded, opened or encoded.

**Revision 2** adopts the colleague review `docs/REVIEW_PROTOCOL_v2.md` with refinements. The point-by-point reply, including an independent recomputation of the review's numbers, is in `docs/RESPONSE_REVIEW_PROTOCOL_v2.md`.

Changes from revision 1:
- **H2 now tests the single SAE against the best single-fit baseline.**
  - Revision 1 used the consensus. Its ~400 features escape the 425-feature subsampling that every 1,024-feature baseline gets, which favoured it (review F1).
  - All methods in H2 now have 1,024 features.
- **H3** compares consensus and single fit at all features (non-inferiority), plus R1. H3c (coverage superiority) is dropped.
- **H1** becomes "informative but inadequate": 0.5 < θ < 0.75.
- **H2b** (beyond physics) and **H5** (k = 1 probing) are descriptive. The confirmatory family has m = 3.
- **New pre-specified key secondaries** (§8), with fixed wording rules:
  - the per-link decomposition;
  - a smoothing control for the shift test;
  - a label-free selection stand-in;
  - a sensitivity analysis for missing twin scores.
- The physics consensus is no longer run; the physics single SAE is.

**Sources:**
- Stage 1a protocol `docs/STAGE1A_PROTOCOL.md` and results `imgsae/exploratory/v2_ct/RESULTS_S1A.md`: gate G1 passed, plus post-G1 checks 1 and 2.
- Review of plan v2, `docs/REVIEW_AND_PROPOSAL_v2.md` §4.
- Review of this protocol, `docs/REVIEW_PROTOCOL_v2.md`.
- Lean plan v1 and its draft protocol `docs/PROTOCOL_lean_DRAFT.md`, for the H1 wording and the deviation rules.

**Decided by the lead (2026-11-10):**
- the frozen methods and the primary metric (§3);
- J = 10 halves on the 555 scans, with Holm correction (§7);
- after the review: the changes above, which settle D1 and D2 as descriptive.

The open choices are in §0.

**Dev numbers.** These come from the 150 dev scans, which were analysed many times, with configs chosen on rep 0. They are used here for planning only and are never pooled with confirmation data.

## 0. Decisions
| ID | Question | Options | Recommendation | Reason |
|---|---|---|---|---|
| D1 (Q1) | H2b: beyond physics | — | **Decided: descriptive** (2026-11-10) | Like for like (single vs single), the dev gain is +0.044, below the 0.05 margin. Revision 1's consensus form passed only through the subsampling asymmetry. To make it confirmatory before registration: tune the physics SAE on the same 8-config rep-0 grid (task `conf_phys_tune`, §11.3), then test single vs single. On dev that test fails with margin 0.05 (−0.4 SDs) and only just passes with margin 0 (2.9; 2.37–3.26 needed). |
| D2 | H5: k = 1 probing | — | **Decided: descriptive** (2026-11-10) | With the single SAE (425 random candidates for every method), the dev gains are negative on all three tasks: vertebral level −0.007, lobe −0.040, organs −0.015. |
| D3 | Where the CPU baselines run | laptop / Modal CPU | **Laptop** | Free. Same machine and 4 BLAS threads as Stage 1a, so its sanity rows can be exact. Modal CPU would add about $5–7. Needs memory-mapped input (E3) and about 10–12 GB of free RAM. |
| D4 | Number of perturbed scans | 20 (as dev) / 40 / 74 (dev share) | **20** | Same number of perturbed scans per half as Stage 1a, so r_pert behaves as on dev. r_shift now carries most of the H2 gain (K1), so more scans would make it more precise, but would change the assay relative to dev. Each step up adds about $0.5–1.5. |
| D5 | Modal budgets (§11.3), and the ledger's all-time $29 check | approve / change | Approve; decide whether the all-time check stays | Expected about $15.7 (range $14.5–18) on account shforghani2002, which has $7.74 committed. The caps total $22.00. Under the all-time check about $5.5 is left for retries. Your current rule is $29 per account per month; without the all-time check, only the month check applies. |
| D6 | Untrained-CT-FM null SAE (descriptive) | skip / run | Skip unless ≥ $5 headroom is left after the main fits | No hypothesis needs it. About $2.5; worst case $2.24 per launch of 5. |
| D7 | Zenodo registration | — | Your call, after the dev checks in §10.1 pass | — |
| D8 | Consensus for k-means and ICA (review P1, optional) | skip / dev check only / also in the confirmation | **Dev check only** (descriptive) | No hypothesis compares a consensus with a baseline, so no claim depends on it. It shows whether consensus also makes k-means and ICA compact and reproducible, which bears on how H3 is read. Judged at all features and on R1, not on the 425-matched area (that would repeat F1). Laptop, rep 0, about 1.5–2 h, $0. In the confirmation it would add about 25 h of laptop time. |

The confirmatory family is {H2, H3, H1}, so m = 3.

## 1. Question and claims
**Core question** (lean v1, unchanged): on fixed CT-FM token embeddings, do SAE features cover more valid concepts than equally tuned decompositions? And does a feature's reproducibility predict its validity?

**Confirmatory claims.** Each is made only if its test passes (§6):
- **H2:** single SAE fits cover more valid concepts than the best of five equally tuned single-fit decompositions, at the same number of features.
- **H3:** the 5-fit consensus loses at most 0.05 of coverage against a single fit (at all features) while keeping about 40% of the features, and it is more reproducible (R1).
- **H1:** the twin score predicts validity better than chance, but it is an inadequate proxy for it (0.5 < θ < 0.75).

**Descriptive only, no claims (§8):** beyond physics; k = 1 probing; consensus vs baselines; which ladder link carries the H2 gain. The wording rules for the last one are fixed in §8.

**Not claimed:**
- anything about other FMs, other datasets, PI-CAI, readers, or causal use of features;
- that the SAE consensus beats a consensus of another method;
- any equivalence ("as selective as …"), since no equivalence test is planned.

## 2. Data
- **Dataset:** TotalSegmentator v2.0.1 (Zenodo record 10047292, zip md5 `fe250e57…`; the HF mirror is the same zip).
- **Confirmation set:** the 555 scans in `imgsae/data/p2_conf_ids.txt` (SHA256 `8dfc5b2d…3caa`). It was fixed by `scripts/p1_select.py` before Phase 1: 705 eligible scans (thorax and/or abdomen study types, institute known) minus the 150 dev scans (seed 0, stratified by study type × institute group).
- **Unit:** the scan. The metadata has no patient ID, so each scan counts as one patient, as in Phase 1. "Patient" below means scan.
- **QC:** the dev rule, applied by `p1_assemble.py` before any fit. Scans with fewer than 20 non-empty structures are excluded and logged. No scan is excluded after scoring.
- **Metadata used:** study type (to stratify the halves); manufacturer, institute, kVp and contrast (shortcut audit).
- The 150 dev scans enter no confirmatory estimate.

## 3. The freeze
- **Methods:** the entries named below in `s1a_lib.methods()`, at the registration commit.
- **Rules:** the production ladder as run in Stage 1a.

Nothing else enters the confirmation.

### 3.1 Methods
All models use seeds s = 7r + h (replicate r; h = 0 for half A, 1 for half B). They are fitted on the fit half only. The input is the assembled tokens: centred, unit norm per row, one global scale. Dev values are means over reps 0–2: **P** is the primary metric (425 features, §3.3), **A** the area at all features.

**Single SAE `sae_M1024_k6_s12000`** (the SAE arm of H2; also used in H3 and H1). P 0.398 (0.400 / 0.403 / 0.392); A 0.530; 1,024 features, L0 6.
- BatchTopK SAE: M 1,024, k 6, 12,000 steps, batch 4,096.
- Adam at 3e-3, with a 100-step warm-up and cosine decay.
- Input noise 0.02, falling to 0 at 80% of the steps.
- Auxiliary loss on dead latents: aux-k 16, weight 1/32; a latent counts as dead after 300 steps without firing.
- No resampling, no Matryoshka.
- Decoder initialised from k-means++ seeds of 20,000 centred rows.
- One fit, seed 10s. In the confirmation this is consensus member 0 (E2).
- Runs on a Modal L4.

**SAE consensus `cons_M1024_k6_s12000`** (H3). A = P = 0.549 (0.526 / 0.585 / 0.535); 396–414 features, L0 ≈ 6.
- 5 fits of the single SAE's config (seeds 10s + i, i = 0–4).
- Cannot-link consensus on ≤ 30,000 fit-half rows: matched r ≥ 0.7, at least 3 of 5 votes. A consensus feature is the mean of its members' activations.
- Runs on a Modal L4.

**Baselines.** All have 1,024 features and L0 6.

| Name | Specification | Dev P | Dev A |
|---|---|---|---|
| `km_M1024_L6` | Soft k-means: MiniBatchKMeans (1,024 centres, 3 inits, batch 8,192). Codes exp(−d²/τ), where τ = median squared distance on 20,000 rows; top 6 | 0.290 | 0.382 |
| `ica_L6` | FastICA (512 components, unit-variance whitening, max 400 iterations, tol 1e-4) on 100,000 fit-half rows. Sources split into positive and negative parts; top 6 | 0.279 | 0.426 |
| `dl_nn_A1024_k6` | Nonnegative k-sparse dictionary learning (deviation M7): nonnegative OMP with k 6 plus MOD updates. 30 iterations on 100,000 rows, SAE initialisation, unused atoms re-seeded | 0.049 | 0.104 |
| `raw_L6` | Raw channels, z-scored on the fit half, split into positive and negative parts; top 6 | 0.148 | 0.227 |
| `svx_L6` | PCA, then varimax rotation of the loadings, split into positive and negative parts; top 6 | 0.045 | 0.092 |

**Reference and comparators:**

| Name | Role | Specification | Features | Dev P | Dev A |
|---|---|---|---|---|---|
| `oracle` | Reference only (not a competitor) | Multinomial logistic regression (C 1, balanced) on the fit half's labels, with ≤ 2,000 core tokens per eligible concept and 20,000 'other'. Features = the class probabilities | 33 | 0.611 | 0.611 |
| `physsae_M1024_k6_s12000` | Descriptive comparator for "beyond physics" (K6) | The single SAE's config and code, on R3: 74 label-free physics features (HU histogram, mean and SD, texture, 48 mm context, body x/y; no z). The config is not tuned for R3 (§3.2) | 1,024 | 0.354 | 0.495 |
| `nullsae_M1024_k6_s12000` | Descriptive null (D6) | Single SAE on the untrained CT-FM | 1,024 | 0.100 | — |
| `physcons_M1024_k6_s12000` | **Not run** (revision 2) | — | — | 0.346 | 0.403 |

### 3.2 Tuning record (dev, rep 0)
- **Candidates per family:**
  - SAE 9 (8 single configs plus the consensus);
  - k-means 9;
  - ICA 2;
  - dictionary learning 6 (3 signed plus 3 nonnegative, M7);
  - raw channels 2;
  - sparse varimax 2.
- **Rule (every family):** the highest rep-0 primary metric wins; ties go to the higher R1.
- **SAE arm of H2.**
  - Stage 1a's gate G1 used the consensus as the SAE family's representative (amendment M1).
  - Revision 2 uses the single SAE, so every method compared in H2 is a single fit with 1,024 features.
  - The single SAE is the best of A2's 8 single configs on rep 0 (0.432), by the same rule.
  - With it, G1-main would also have passed: gains +0.090 / +0.122 / +0.100, mean +0.104.
- **Not tuned:** the physics and untrained SAEs use the CT-FM SAE's config. This is reported as a limitation.

### 3.3 Ladder and metric (frozen rules)
**Features that enter the ladder (V0):**
- activation frequency ≥ 1e-3;
- active in ≥ 10 patients;
- not a near-duplicate (r ≥ 0.9) of a more frequent feature.

**Scores.** Selectivity, chimera and r_pert are measured on the other half's patients:
- **Selectivity:** K-robust, on patient means; the top concept against the next 6.
- **Chimera rule:** a feature is chimeric if ≥ 20% of its top 1% activation mass falls in a class that is neither its own nor adjacent to it.
- **r_pert:** the minimum of the shift and noise correlations; for anatomical concepts the HU-offset correlation is included too.
- **Twin score t:** measured on the own half. It is the Hungarian-matched activation r with the other half's model.

**Validity:**
- v = min(t, selectivity, r_pert) for V0 features that are not chimeric and not assigned to 'other'. Every other feature gets 0.
- The minimum uses `np.fmin`, as in `p1_fit.feature_table`, so a missing twin score is skipped. A twin score is missing when the feature fires on fewer than 0.1% of its own half's evaluation tokens (`sae.alive`).
- A missing r_pert makes the feature not evaluable, which counts as 0 in areas.
- Sensitivity S5 counts a missing twin score as 0 instead.

**Chimera rules:** 'neutral' ('other' counts as adjacent to every concept) is primary. 'orig' (as run in Phase 1) is a sensitivity analysis.

**C(τ)** = the number of gated concepts with at least one feature of v ≥ τ, for τ ∈ {0.50, 0.55, …, 0.90}. Area = mean C(τ) / number of gated concepts.

**Primary metric P:**
- the area with features subsampled to 425 (20 draws, seeded by the replicate); methods with ≤ 425 features use all of them;
- averaged over the two directions (A → B and B → A);
- code: `p1b_sanity/common.evaluate`, key `area_matched_neutral`;
- in H2 every method has exactly 1,024 features per half, so the subsampling treats them all alike.

**All-feature area A:** the same area without subsampling (key `area_neutral`). It is used in H3a. There the consensus has about 40% of the single fit's features, so this comparison does not favour it.

**R1:** the activation match between the A and B models (`sae.act_match`).

**Gated concepts:**
- the 32 concepts gated in the dev `data/p1/gates.json`, copied unchanged and hashed;
- restricted to concepts eligible on the confirmation data (≥ 10 scans with a core token, recomputed by `p1_assemble.py`).

Adjacency and eligibility are recomputed by the same code. They use labels only, never method output.

θ, precision, shortcut share and k = 1 probing are computed as in `s1a_lib.table_metrics` and `k1_probe` (§6, §8).

### 3.4 Fixed code, versions, hardware
**Code:**
- `imgsae/imgsae/`: sae, consensus, ladder, atlas, tokens, stats;
- `scripts/`: `p1_encode.py`, `p1_assemble.py`, `p1_fit.py`, `p1_probe.py`;
- `exploratory/p1_checks/c1b_chimera_other.py`;
- `exploratory/p1b_sanity/common.py` and `a1_probe_ladder.build_tasks`;
- `exploratory/v2_ct/s1a_lib.py`.

**Versions:** `imgsae/requirements-lock.txt`. The Modal image pins torch 2.10.0, numpy 2.4.6, scipy 1.17.1, scikit-learn 1.9.1 and pandas 3.1.1.

**Hardware:**
- **SAE rows:** all on a Modal L4. The consensus is sensitive to the GPU: on rep 0 it scored 0.526 on the L4 and 0.562 on the laptop GPU.
- **Encodes:** on a Modal L4, in fp16, at 1.0 mm, with tiles 192/48 as on dev. The tiles are not enlarged, because tiling changes the features (cosine 0.990 between 160 and 192 tiles).
- **CPU rows:** on the laptop, with OMP/MKL threads = 4 (D3).

### 3.5 Engineering changes needed before registration
None of these changes a method, rule or threshold. Each is checked on dev data (§10.1).
- **E1. Cloud encode job.** Runs the per-scan steps of `p1_encode.py`. The token tables are built in parallel worker processes, and the GPU encode runs in the main process. Every finished scan is saved to the volume at once, so the job can resume.
- **E2. Combined consensus + single job.**
  - The single SAE is consensus member 0 (same seed, same data). It is scored as its own model in the same container, which saves 10 L4 fits.
  - The single SAE is now H2's SAE arm, so its dev check (C2) must match exactly. If C2 fails, the single SAE runs as separate jobs.
- **E3. Memory-mapped input.**
  - `X_ctfm` is written once as a `.npy` file (a byte copy from rows.npz) and memory-mapped, so a job holds only the rows it uses. This applies on the laptop and on Modal.
  - The dense references read only the task rows.
- **E4. Confirmation mode.**
  - Some dev paths are hard-coded: the reference cache `p1b_sanity/results/cache_refpos.npz`, the folder `v2_ct/results/` and `s1a_tasks.npz`. In confirmation mode all of them are keyed to the data folder, so no dev file can be read.
  - `step_tasks` keeps the A1 equality check for dev only.
  - Confirmation jobs log progress and sanity diffs only, never metric values, so there are no interim looks.
- **E5. Analysis script** `v2_ct/s2_confirm.py`. It computes:
  - the corrected t, Holm and the intersection–union tests;
  - S1–S5 and K1–K6;
  - the wording rules W1–W2;
  - the report.

  Everything comes from the result JSONs and the per-feature tables.
- **E6. Smoothing control** (K3). The smoothed embeddings are scored next to r_shift in each fit job. This reads the raw CT-FM embeddings (`feat_ctfm`) from the original per-scan files of the 20 perturbed scans.

## 4. Pipeline (run once, after registration)
1. **Fetch** the 555 scans with `fetch_subset.py get` (CRC32-verified) into a new Modal volume, `imgsae-conf`. Nothing goes to the laptop.
2. **Encode** with CT-FM and with the untrained CT-FM (seed 0), at 1.0 mm (E1).
3. **Assemble** with `p1_assemble.py` (ids = `p2_conf_ids.txt`, output `data/p2`). This builds the rows, QC, eligibility, adjacency and the input transform. The transform is fitted on all confirmation tokens; it is label-free, as on dev.
4. **Gates.** The frozen dev `gates.json` is copied in. `p1_probe.py` also runs, but only for sensitivity analysis S3.
5. **Perturbation list.** 20 QC-passing scans are chosen by the production rule (`run_phase1.py`: `default_rng(7).choice` over the assembled scan IDs, sorted). Each gets shift, noise and HU-offset re-encodes with both encoders. After this step, the raw scans are deleted from the volume.
6. **k = 1 task sets:** organ groups, vertebral level and lung lobe. Built by `a1_probe_ladder.build_tasks` with the same caps and seeds; a class needs ≥ 10 patients.
7. **Fits and ladder** for r = 0–9 (§5):
   - on the L4: the consensus + single job (CT-FM) and the physics single SAE;
   - on the laptop: the CPU jobs, using the downloaded rows, the perturbation files and the 20 perturbed scans' original per-scan files.
8. **Analysis**, once (E5), writes `results/conf/*.json` and `RESULTS_CONF.md`.

## 5. Replicates
- J = 10 replicates, r = 0–9.
- **Halves:** `p1_fit.halves(scans, r)`, seed 1000 + r, stratified by study type. About 278 scans per half.
- **Evaluation rows:** up to 300 tokens per scan (seeds r and r + 50).
- Each half's model is scored on the other half's scans. The twin score uses the own half's evaluation tokens. Per-replicate numbers average the two directions.
- Every method runs on every replicate with the same halves, so all contrasts are paired by replicate.

## 6. Hypotheses
For each replicate r there is a contrast d_r; the tests are in §7. "Best baseline" means the maximum, in that replicate, over the five frozen baselines.

| ID | Contrast d_r | Null H0 (mean μ of d) | Claim if H0 is rejected | Dev, reps 0–2 |
|---|---|---|---|---|
| H2 | P(single SAE) − max over baselines of P | μ ≤ 0 | Single SAE fits beat every equally tuned single-fit baseline | +0.104 (+0.090 / +0.122 / +0.100) |
| H3a | A(consensus) − A(single) | μ ≤ −0.05 | The consensus loses at most 0.05 of coverage | +0.019 (+0.010 / +0.035 / +0.010) |
| H3b | R1(consensus) − R1(single) | μ ≤ 0 | The consensus is more reproducible | +0.304 (+0.280 / +0.294 / +0.337) |
| H1a | θ_r of the single SAE | μ ≤ 0.5 | The twin score is informative about validity | 0.653 (0.664 / 0.646 / 0.649) |
| H1b | θ_r of the single SAE | μ ≥ 0.75 | The twin score is an inadequate proxy for validity | same |

**H2.**
- Every arm has 1,024 features, so the 425-feature subsampling is the same for all.
- The differences to each baseline separately are secondary (S4).
- No hypothesis compares the consensus with a baseline; that contrast is descriptive (K5).

**H3** = H3a and H3b together. It is an intersection–union test: both parts must pass, and p_H3 = max(p_H3a, p_H3b).
- **Pairing.** The single SAE is consensus member 0 (E2), so the two arms share their fits.
- **Wording if it passes:** "coverage within 0.05 of a single fit with about N% of the features, and more reproducible". N is the measured feature share (dev 39%).
- Non-inferiority does not show equal coverage, so "the same coverage" is not used.

**H1** = H1a and H1b together. It is an intersection–union test: p_H1 = max(p_H1a, p_H1b).
- **Estimand:** θ_r = AUROC of the twin score t for validity y, among the single SAE's V0 features, pooled over both half models ('neutral' rule; `ladder.theta`).
- **Validity y:** selectivity ≥ 0.7, not chimeric, gated concept, r_pert ≥ 0.7, V0 (as `p1_fit` and T5).
- **Origin of the 0.75 bound:** v1's prediction P2 (θ 0.55–0.70; falsified by a lower bound ≥ 0.75).
- **Estimability:** θ_r must be estimable (≥ 20 valid and ≥ 20 invalid features) in every replicate. Dev had 468–480 valid and 1,546–1,553 invalid.
- **Secondary:**
  - the coefficient adjusted for frequency and magnitude (beta_t);
  - θ for the consensus and every baseline.

**If an intersection–union test fails,** the estimates, CIs and p-values of its parts are reported, but no claim is made from a single part.

**H2b and H5** are descriptive (D1, D2): see K6 and the k = 1 outputs in §8.

## 7. Inference
**Each contrast:**
- the mean over the J = 10 replicates;
- the Nadeau–Bengio corrected standard error SE = SD × √(1/J + 1) (half splits; `imgsae/stats.corrected_t`);
- t = (mean − boundary) / SE, on 9 df;
- a one-sided p in the claimed direction.

**Holm** step-down over {H2, H3, H1} (m = 3), at familywise one-sided α = 0.025 (equivalent to two-sided 0.05).
- H3 and H1 each enter with their intersection–union p (the larger p of their two parts). This is a valid level-α test of the union of the two nulls, so it needs no further correction.
- If D1 or D2 were reversed before registration, each would add one member to the family.

**Reported for each hypothesis:** the estimate, the two-sided 95% corrected-t CI, the one-sided p, the Holm-adjusted p and the decision. For H3 and H1, the same is reported for each part.

**One analysis run:** no interim looks and no change of rules after unsealing.

**Missing replicates:**
- A failed job is rerun unchanged (same seeds).
- If a replicate still cannot be completed for a technical reason after two reruns, it is dropped for all methods and logged. Inference then uses the remaining replicates.
- A replicate is never dropped because of its results.

## 8. Secondary, sensitivity and descriptive outputs (no claims)
All secondary contrasts are per replicate, with two-sided 95% corrected-t CIs and no multiplicity correction. They are labelled as secondary in every report.

### Sensitivity analyses (pre-specified)
- **S1:** the 'orig' chimera rule, for H2, H3 and H1.
- **S2:** H2 at all features, without subsampling.
- **S3:** the gated set recomputed on confirmation data by the v1 rule (`p1_probe.py`).
- **S4:** H2 against each baseline separately.
- **S5:** a missing twin score counted as 0 in v, instead of skipped (the review's choice), for H2, H3a and K1.

### Key secondary outputs
These come from review points P4 and P5, with refinements.
- **K1. Link decomposition.** For every method, the all-feature area with one ladder link removed, on the features that enter v (V0, not chimeric, not 'other'). There are four variants:
  - selectivity only;
  - min(selectivity, r_pert);
  - min(selectivity, t);
  - full v.

  Missing values follow the v rules of §3.3. Contrasts: single SAE − each baseline.
- **K2. Selective features.** These are features with selectivity ≥ 0.7, V0, not chimeric, a gated concept, not 'other', pooled over the two half models of a replicate. For each method:
  - the medians of r_pert, r_shift, r_noise, r_huoff and t;
  - the share with t ≥ 0.7.

  Contrasts: single SAE − each baseline.
- **K3. Smoothing control for the shift test.**
  - **The shift test** (`p1_encode.py`): the volume is moved by +8 voxels in z and in x. Each token embedding is then replaced by the mean of the 2 × 2 block (z, z+1) × (x, x+1) of the shifted volume's embeddings. That block is centred on the original token, and the averaging spreads it by a variance of ¼ token² per axis.
  - **r_interp** (as in the review): the same 2 × 2 mean of the *unperturbed* embeddings, with no shift. Its centre is half a token off in z and in x.
  - **r_interp_c** (added): a centred smoothing of the unperturbed embeddings, with weights (1/8, 3/4, 1/8) along z and along x, over the 3 × 3 block in the z–x plane. It has the same variance (¼ token² per axis) and no offset.
  - **How the smoothing is applied:** to the raw CT-FM embeddings, before the stored input transform (as `load_perturb` treats the shift encode). For R3, only the 56 HU, texture and context columns are averaged; the position columns are left unchanged, as in the shift encode.
  - **Tokens:** the tokens of the 20 perturbed scans in the scoring half whose needed neighbours are all valid tokens of the same scan.
  - **Scores:** per feature, the Pearson r between its codes on the original and on the smoothed embeddings (as in `feature_table`). r_shift is recomputed on the same tokens. Medians are taken over K2's selective features.
- **K4. Label-free selection stand-in.** For each method and half, the all-feature area of its 425 features with the highest twin score; a method with fewer than 425 features uses all of them. Contrast: single SAE − best baseline.
- **K5. Consensus vs baselines** (revision 1's H2), at all features and at 425 features. It is reported with a note that the consensus escapes the subsampling.
- **K6. Beyond physics.** Single CT-FM SAE − single physics SAE on P, on A, on every K1 variant, on the K2 medians, and on k = 1 vertebral level. The physics SAE's config was not tuned.

### Wording rules (fixed now, before any confirmation or K3 result is seen)
**W1, per ladder link.** This applies to each baseline b, using the K1 and K2 contrasts of the single SAE against b:
- "more selective than b" only if the CI of the selectivity-only K1 contrast lies above 0;
- "more stable under the perturbations than b" only if the CI of the K2 median-r_pert contrast lies above 0; which perturbation is named follows W2;
- "more reproducible per feature than b" only if the CI of the K2 median-t contrast lies above 0;
- "less …" if the CI lies below 0, and "not shown to differ" otherwise. "As … as" is never used.

**W2, shift vs interpolation.** Let δ_b = median r_interp_c(b) − median r_shift(b), on the same tokens and averaged over replicates, for b = k-means and ICA (the two strongest baselines on dev).
- **δ_b ≤ 0.10 for both:** smoothing alone reproduces their drop. The SAE's advantage is then described as "more stable when neighbouring embeddings are averaged (sub-token interpolation)", not as robustness to translation.
- **δ_b > 0.10 for both:** "more stable under a half-token shift".
- **Mixed:** each baseline is described by its own case.
- r_interp (the off-centre version) is reported next to it, but it does not enter the rule.

### Descriptive outputs
- **Supervised reference:** its C(0.7) (the assay check, §10.2), and the SAE as a % of the reference.
- **Per method:**
  - precision (the share of V0 features with v ≥ 0.7), C(0.7) and feature counts;
  - the share of V0 features assigned to 'other';
  - θ; shortcut share; the medians of t, selectivity and r_pert.
- **Nulls:** the untrained-CT-FM SAE, if D6 says so.
- **k = 1 probing** on all three tasks, for the single SAE, the consensus and the baselines (native, and with 425 candidates). The dense CT-FM, R4 and untrained probes serve as references.
- **R1 for all methods.** Raw channels and sparse varimax have R1 ≈ 1 by construction, so their R1 is not compared.
- **The D8 dev check,** if it is run.

### Limits stated in every report
- Validity counts only the 33 labelled groups, so precision is underestimated for every method.
- One FM and one dataset.
- Scan = patient.

## 9. Planning numbers from dev (not evidence)
With half splits, the corrected SE is about 1.05 × the between-replicate SD. With m = 3, a test therefore passes when (estimate − boundary) / SD is at least about **3.08** at Holm's first step, **2.82** at the second and **2.37** at the last (9 df).

| Test | Dev estimate | Dev SD (3 reps) | (estimate − boundary) / SD | Estimate needed at the dev SD (last–first step) |
|---|---|---|---|---|
| H2 | +0.104 | 0.016 | 6.4 | ≥ 0.04–0.05 |
| H3a | +0.019 | 0.014 | 4.9 | ≥ −0.02 to −0.01 |
| H3b | +0.304 | 0.030 | 10.3 | ≥ 0.07–0.09 |
| H1a | 0.653 | 0.010 | 15.9 | ≥ 0.52–0.53 |
| H1b | 0.653 | 0.010 | 10.1 | ≤ 0.72–0.73 |

- For H3 and H1 the weaker part counts: 4.9 and 10.1.
- **Sensitivity on dev:**
  - S1 ('orig' rule): H2 +0.088 (9.4); H3a +0.038 (4.2); H1b θ 0.698 (3.9).
  - S2 (H2 at all features): +0.104 (2.6). Its headroom is smaller because the all-feature contrast varied more across dev replicates (SD 0.040).
  - K4 (top 425 by twin score): +0.104 (2.6).
- **The SDs are imprecise:** they come from 3 replicates. Confirmation halves are about 3.7× larger than dev halves, which should lower them.
- **Winner's curse:** the single SAE was still chosen from 8 configs on rep 0, so its dev estimate is somewhat inflated. H2 fails if the gain shrinks below about 0.04–0.05.

## 10. Checks
### 10.1 Before registration (dev data only)
| Check | Where | Pass |
|---|---|---|
| C1. E1 encode of the 5 gate-E dev scans (s0006, s0015, s0024, s0038, s0040), fetched in the container from HF | Modal L4 | Token tables (occ, ref, pos, gidx) equal the laptop's `data/p1/scans/*.npz`. Median per-token cosine of feat_ctfm and feat_null ≥ 0.995 (the gate E parity rule). The measured seconds per scan set the encode plan (§11) |
| C2. E2 combined job, dev rep 0, with E6 | Modal L4 | Single row = `s1a_sae.json` sae_M1024_k6_s12000_rep0, **exactly** (it is H2's SAE arm). Consensus row = cons_M1024_k6_s12000_rep0, exactly or within 0.01 on P. K3 values recorded for both |
| C3. CPU runner with memory-mapped input (E3) and E6, dev rep 0, the five baselines plus the reference | laptop | Equals `s1a_cpu.json` exactly (R1 and all four areas). K3 values recorded |
| C4. E5 analysis script on the Stage 1a rows (J = 3) | laptop | Reproduces the dev values in §6, §9 and `docs/RESPONSE_REVIEW_PROTOCOL_v2.md` §1 (H2 +0.090 / +0.122 / +0.100; H3a +0.010 / +0.035 / +0.010; θ 0.664 / 0.646 / 0.649; K1 and K4) |
| C5. E4 confirmation mode, dry run on a dummy data folder | laptop | Reads no file in the dev folders |
| C6. K3 on dev rep 0 (from C2, C3) | — | Descriptive. Recorded in this protocol before registration. The W2 rule above is already fixed and does not change |

If a check fails, the fix is metric-blind and the check is repeated. Registration waits until C1–C5 pass and C6 is recorded.

### 10.2 During the confirmation
- **Encode:** no SPILL or ABORT, `DONE 555/555`, and the token count of each scan logged.
- **QC:** exclusions logged before any fit.
- **Completeness:** the analysis starts only when all methods × 10 replicates are present.
- **Assay check:** the reference's C(0.7) must reach ≥ 20 of the gated concepts (mean over the 20 half-models; on dev, G1-cal gave 21.7 of 32).
  - It does not gate the hypotheses.
  - If it fails, the report flags it, and no threshold is changed.

## 11. Compute and cost
### 11.1 Sizes
Dev values are measured; confirmation values are scaled by 555/150.

| | Dev, 150 scans | Confirmation, 555 scans |
|---|---|---|
| Download | 3.67 GB, 17,700 files | about 13.6 GB, about 65,500 files |
| Tokens | 1,021,303 | about 3.8 million |
| Per-scan encodes | 1.89 GB | about 7.0 GB |
| rows.npz | 4.57 GB | about 17 GB (X_ctfm alone about 7.7 GB in float32) |
| Perturbation encodes (20 scans × 3) | — | about 0.8 GB |

### 11.2 Time and cost per step
Container rates come from `budget.py`. Expected costs include the ledger's 3 minutes per container for start-up.

| Step | Where | Time | Expected $ | Basis |
|---|---|---|---|---|
| Dev checks C1, C2 (before registration) | Modal L4 | About 30 min | 0.6 | §10.1 |
| Fetch | Modal CPU: 2 cores, 4 GiB ($0.13/h) | 0.5–3 h | 0.2 | Limited by request latency; on dev the laptop took 53 min for 3.67 GB |
| Encode: 555 scans + 60 perturbation scan-encodes, both encoders | Modal L4: 8 cores, 32 GiB ($1.43/h); 4 + 1 containers | About 1.2 h wall; about 3.8 h billed at 20 s per scan | 5.4 (4.2 at 15 s; 7.8 at 30 s) | **Not measured: a projection, which C1 measures.** On the laptop a scan took 36 s (table) + 200 s (encode), with the GPU stuck at 210 MHz |
| Assemble, gate probe, task sets, reference cache, `.npy` | Modal CPU: 4 cores, 64 or 32 GiB | About 1 h | 0.6 | Dev assemble took 2.9 min; at 555 scans it peaks at about 35 GB of RAM |
| SAE consensus + single (CT-FM), 10 jobs | Modal L4: 4 cores, 16 GiB ($1.12/h) | About 26 min each | 5.4 | A dev job took 17.6 min. The fits do not grow with tokens (12k steps × 4,096); scoring grows about 3.7×. 16 GiB needs E3; without it, 32 GiB (+$0.6) |
| Physics single SAE (R3), 10 jobs | Same | About 10 min each | 2.4 | Dev: about 4 min per job |
| Image builds | | | 1.1 | $0.10 per launch, 11 launches |
| CPU baselines + reference + dense references + K3, 10 replicates | Laptop | About 75–80 min per replicate; about 13 h in total | 0 | Dev took about 40 min per replicate. The k-means fit and the scoring grow about 3.7×; ICA and DL fit on a fixed 100k rows |
| Download of the CPU inputs from the volume | Laptop | 0.5–3 h | 0 | About 10 GB, plus 0.25 GB for the 20 perturbed scans' original files |
| Analysis | Laptop | Minutes | 0 | |
| **Modal total** | | | **about 15.7 (range 14.5–18)** | |

If C1 projects more than $8.5 for the encodes, the work stops for the lead's decision. The options then are: the laptop (about 41 h, $0), more budget, or the second account.

### 11.3 Modal budgets for approval
These are on account shforghani2002, in the ledger `p1b_sanity/cloud/ledger.json`. The worst case of a launch = containers × (timeout + 3 min) × rate + $0.10 for the image.

| Task | Launches | Container | Timeout | Worst case per launch | Expected | Budget |
|---|---|---|---|---|---|---|
| `conf_check` | C1; C2 | L4 8c/32G; L4 4c/16G | 30; 30 min | $0.89; $0.71 | $0.8 | **$1.70** |
| `conf_prep` | fetch; assemble; prep steps | CPU 2c/4G; 4c/64G; 4c/32G | 240; 60; 60 min | $0.61; $0.84; $0.57 | $1.1 | **$2.10** |
| `conf_encode` | main 4 containers (or 2 × 2); perturbations 1 | L4 8c/32G | 1.5 × the time C1 projects | ≤ $7.1 at 20 s per scan | $5.6 | **$9.00** |
| `conf_fit_gpu` | consensus + single 2 × 5; physics single 2 × 5 | L4 4c/16G | 40; 20 min | $4.10; $2.24 | $8.2 | **$9.20** |
| `conf_null` (D6) | 2 × 5 | L4 4c/16G | 20 min | $2.24 | $2.5 | $0 unless approved |
| `conf_phys_tune` (only if D1 is reversed) | 2 × 4 dev singles on R3 | L4 4c/16G | 15 min | $1.44 | $1.2 | $0 unless D1 is reversed (then $2.10) |
| **Total** | | | | | **about $15.7** | **$22.00** |

**How the caps are set:**
- Each cap covers the expected spend plus the worst case of the last launch.
- Launch sizes are chosen so that committed + worst case stays inside the cap.
- Every launch saves each finished unit to the volume, so a timeout loses at most the unit in progress.

### 11.4 Guard and accounts
**Each launch:**
- passes `budget.py check` (task, project and month);
- uses `modal run --detach`;
- writes every finished unit to the volume;
- is closed in the ledger from its measured container minutes.

**Account shforghani2002 now:**
- $7.74 committed: a3_sae $1.68, v2s1a_sae $6.06.
- Modal billing showed $3.20 at 03:35; billing lags.

**Project check (all runs ever ≤ $29):**
- It leaves $21.26: enough for the expected $15.7, with about $5.5 to spare for retries.
- The task caps sum to $22.00, more than that, but the check stays on top of them, so actual spending cannot pass $29.

**Month check:** it also passes for November; about $3 has been used so far.

**Proposed ledger edits (with your OK):**
- add the new tasks above;
- close a3_sae and v2s1a_sae at their committed amounts;
- leave the $6 reserve as it is; it still needs your OK to use.

**If you drop the all-time check:** your current rule is $29 per account per month, so only the month check applies. November then has about $25 left.

**Second account:** forghanishayan is not used. Using it would need its own ledger and a copy of the data.

### 11.5 Storage
- The volume `imgsae-conf` peaks at about 38 GB (raw 13.6 + per-scan encodes 7 + rows 17). After the raw scans are deleted (§4 step 5) it holds about 25 GB.
- At the rate implied in `cloud/README.md` (about $0.09 per GB-month; check `modal billing` before launch), that is about $2–3 for each month the data are kept. Storage counts against the month check.
- After the run:
  - keep the per-scan encodes and the results on the laptop's D: drive (122 GB free);
  - delete the volume's rows.npz.

## 12. Order, blinding, deviations
**Order:**
1. The lead reviews revision 2 and decides D3–D8.
2. Engineering changes E1–E6, then the dev checks C1–C6 (task `conf_check`, plus the laptop). C1 fixes the encode plan; C6 is recorded here.
3. Freeze:
   - update this protocol with the decisions, C1's measured rate and C6;
   - commit, and tag `v2-conf-lock`;
   - record the SHA256 of this protocol, the frozen `gates.json`, `p2_conf_ids.txt`, `s1a_lib.py`, `s2_confirm.py` and the job list;
   - Zenodo registration (D7).
4. Unseal and run §4 once.
5. Report (§13). Then the lead decides on the paper.

**Rules** (as v1 §5):
- Jobs come only from the sealed job list.
- Only metric-blind crash fixes are allowed. Every deviation goes in `docs/EXECUTION_LOG.md`, with date and reason.
- No scan is excluded after scoring. No method, config, threshold, test or wording rule changes after unsealing.
- No metric is looked at until all jobs are done (E4).
- Any post-hoc analysis is labelled post hoc and reported separately.

## 13. Reporting and interpretation
`RESULTS_CONF.md` is generated by `s2_confirm.py` from the JSONs, with no hand-copied numbers. It contains:
- every hypothesis, reported as in §7;
- S1–S5, K1–K6 and the W1–W2 readings;
- the descriptive outputs;
- every deviation;
- the ledger's spending.

| Outcome | What the paper may say |
|---|---|
| H2 passes | On CT-FM, single-fit SAE features cover more valid concepts than equally tuned single-fit k-means, ICA, nonnegative sparse coding, raw channels and sparse varimax, at the same number of features. Which link carries the gain is worded by W1–W2 only |
| H2 fails | No SAE-superiority claim; the estimates are reported. The lead decides on the paper (Q2). No reframing after unsealing |
| H3 passes | The 5-fit consensus loses at most 0.05 of coverage against a single fit, with about N% of the features (measured), and it is more reproducible |
| H1 passes | The twin score carries information about validity (θ > 0.5), but it is an inadequate proxy (θ < 0.75), so validity must be checked directly |
| H3 or H1 fails | No claim; the parts are reported |
| Descriptive | Beyond physics (K6), k = 1 probing, consensus vs baselines (K5) and D8 are reported without claims |

## 14. Registration package
- This protocol, with the decisions, C1's rate and C6 filled in, and its SHA256.
- The review `docs/REVIEW_PROTOCOL_v2.md` and the reply `docs/RESPONSE_REVIEW_PROTOCOL_v2.md`.
- Git tag `v2-conf-lock`: the code of §3.4 and E1–E6.
- Hashes:
  - `p2_conf_ids.txt` (`8dfc5b2d…3caa`);
  - the dev `gates.json`;
  - `s1a_lib.py` and `s2_confirm.py`;
  - the job list.
- The dev results it rests on: `RESULTS_S1A.md`, `s1a_selection.json`, `s1a_selection_m7.json` and `s1a_g1.json`.
