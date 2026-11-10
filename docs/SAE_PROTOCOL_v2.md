# Confirmation protocol v2: SAE vs equally tuned decompositions on CT-FM (555 sealed scans)

**Status:** DRAFT for the project lead's review, 2026-11-10. Not registered. Nothing in it has been run. The 555 confirmation scans have not been downloaded, opened or encoded.

**Sources:**
- Stage 1a protocol `docs/STAGE1A_PROTOCOL.md` and results `imgsae/exploratory/v2_ct/RESULTS_S1A.md`: gate G1 passed, plus post-G1 checks 1 and 2.
- Colleague review `docs/REVIEW_AND_PROPOSAL_v2.md` §4, "Confirmation" and "Order" step 2.
- Lean plan v1 and its draft protocol `docs/PROTOCOL_lean_DRAFT.md`, for the H1 wording and the deviation rules.

**Already decided by the lead (2026-11-10):**
- the frozen methods and the primary metric (§3);
- hypotheses H2, H3, H1, H2b and H5 (§6);
- J = 10 halves on the 555 scans, with Holm correction (§7).

The open choices are in §0.

**Dev numbers.** These come from the 150 dev scans, which were analysed many times, with configs chosen on rep 0. They are used here for planning only and are never pooled with confirmation data.

## 0. Open decisions, with recommendations
| ID | Question | Options | Recommendation | Reason |
|---|---|---|---|---|
| D1 (Q1) | H2b: CT-FM consensus vs physics (R3) consensus, margin 0.05 | keep in the Holm family / descriptive only | **Keep** | v1's core question included "beyond intensity and position". The physics SAE came close on organ concepts (single fit 0.35 vs 0.40), so reviewers will ask. Dev headroom is good (§9). It costs one Holm slot. Caveat: the comparator is not tuned (§3.2). |
| D2 | H5: k = 1 probing on vertebral level | descriptive / confirmatory | **Descriptive** | On dev the SAE beats the best baseline by only +0.018 (−0.003, +0.006, +0.052). A pass needs about 2.4–3.3 between-replicate SDs, and dev gives 0.6. The test would very likely fail, and a failed superiority test does not show "no advantage". The confirmatory version is written out in §6 in case you choose it. |
| D3 | Where the CPU baselines run | laptop / Modal CPU | **Laptop** | Free. Same machine and 4 BLAS threads as Stage 1a, so its sanity rows can be exact. Modal CPU would add about $5–7 and would not fit the ledger's $29 all-time check together with the GPU tasks (§11.4). Needs memory-mapped input (E3) and about 10–12 GB of free RAM. |
| D4 | Number of perturbed scans | 20 (as dev) / 40 / 74 (dev share) | **20** | Same number of perturbed scans per half as Stage 1a, so r_pert behaves as on dev. Each step up adds about $0.5–1.5 of encodes. |
| D5 | Modal budgets (§11.3) and the ledger's all-time $29 check | approve / change | Approve; decide whether the all-time check stays | Expected about $17 (range $15–20) on account shforghani2002, which has $7.74 committed. Under the all-time check about $4 is left for retries. Your current rule is $29 per account per month: without the all-time check, only the month check applies. |
| D6 | Untrained-CT-FM null SAE (descriptive) | skip / run | Skip unless ≥ $5 headroom is left after the main fits | No hypothesis needs it. About $2.5; worst case $2.24 per launch of 5. |
| D7 | Zenodo registration | — | Your call, after the dev checks in §10.1 pass | — |

Under these recommendations the confirmatory family is {H2, H3, H1, H2b}, so m = 4.

## 1. Question and claims
**Core question** (lean v1, unchanged): on fixed CT-FM token embeddings, do SAE features cover more valid concepts than equally tuned decompositions? And does a feature's reproducibility predict its validity?

**Confirmatory claims.** Each is made only if its test passes (§6):
- **H2:** the SAE consensus covers more valid concepts than the best of five equally tuned decompositions.
- **H3:** the consensus is no worse than a single SAE fit on coverage, and it is more reproducible.
- **H1:** reproducibility (twin score) is an inadequate proxy for validity (θ < 0.75).
- **H2b (D1):** SAE features of CT-FM cover more valid concepts than SAE features of a label-free physics reference (HU statistics, texture, 48 mm context, body x/y), by more than 0.05.

**Not claimed:** anything about other FMs, other datasets, PI-CAI, readers, or causal use of features.

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
All models use seeds s = 7r + h (replicate r; h = 0 for half A, 1 for half B). They are fitted on the fit half only. The input is the assembled tokens: centred, unit norm per row, one global scale.

**SAE consensus `cons_M1024_k6_s12000` (the SAE representative).** Dev primary 0.549 (0.526 / 0.585 / 0.535); about 400 features at L0 ≈ 6.
- BatchTopK SAE: M 1,024, k 6, 12,000 steps, batch 4,096.
- Adam at 3e-3, with a 100-step warm-up and cosine decay.
- Input noise 0.02, falling to 0 at 80% of the steps.
- Auxiliary loss on dead latents: aux-k 16, weight 1/32; a latent counts as dead after 300 steps without firing.
- No resampling, no Matryoshka.
- Decoder initialised from k-means++ seeds of 20,000 centred rows.
- 5 fits (seeds 10s + i, i = 0–4).
- Cannot-link consensus on ≤ 30,000 fit-half rows: matched r ≥ 0.7, at least 3 of 5 votes. A consensus feature is the mean of its members' activations.
- Runs on a Modal L4.

**Single SAE `sae_M1024_k6_s12000`** (used in H3 and H1). Dev primary 0.398; 1,024 features, L0 6. The same SAE with one fit, seed 10s. This is consensus member 0 (E2).

**Baselines.** All have 1,024 features and L0 6.

| Name | Specification | Dev primary |
|---|---|---|
| `km_M1024_L6` | Soft k-means: MiniBatchKMeans (1,024 centres, 3 inits, batch 8,192). Codes exp(−d²/τ), where τ = median squared distance on 20,000 rows; top 6 | 0.290 |
| `ica_L6` | FastICA (512 components, unit-variance whitening, max 400 iterations, tol 1e-4) on 100,000 fit-half rows. Sources split into positive and negative parts; top 6 | 0.279 |
| `dl_nn_A1024_k6` | Nonnegative k-sparse dictionary learning (deviation M7): nonnegative OMP with k 6 plus MOD updates. 30 iterations on 100,000 rows, SAE initialisation, unused atoms re-seeded | 0.049 |
| `raw_L6` | Raw channels, z-scored on the fit half, split into positive and negative parts; top 6 | 0.148 |
| `svx_L6` | PCA, then varimax rotation of the loadings, split into positive and negative parts; top 6 | 0.045 |

**Reference and comparators:**

| Name | Role | Specification | Features | Dev primary |
|---|---|---|---|---|
| `oracle` | Reference only (not a competitor) | Multinomial logistic regression (C 1, balanced) on the fit half's labels, with ≤ 2,000 core tokens per eligible concept and 20,000 'other'. Features = the class probabilities | 33 | 0.611 |
| `physcons_M1024_k6_s12000` | Comparator in H2b | The SAE representative's config and code, on R3 (74 label-free physics features) | about 630 | 0.346 |
| `physsae_M1024_k6_s12000` | Descriptive null | Single SAE on R3 | 1,024 | 0.354 |
| `nullsae_M1024_k6_s12000` | Descriptive null (D6) | Single SAE on the untrained CT-FM | 1,024 | 0.100 |

### 3.2 Tuning record (dev, rep 0)
- **Candidates per family:**
  - SAE 9 (8 single configs plus the consensus);
  - k-means 9;
  - ICA 2;
  - dictionary learning 6 (3 signed plus 3 nonnegative, M7);
  - raw channels 2;
  - sparse varimax 2.
- **Rule (every family):** the highest rep-0 primary metric wins; ties go to the higher R1.
- The SAE representative was fixed before Stage 1a ran (amendment M1), from A2's rep-0 value on the local GPU (0.562).
- **Not tuned:** the physics and untrained SAEs use the CT-FM SAE's config. This may favour the CT-FM SAE in H2b, and it is reported as a limitation.

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

**Validity** v = min(t, selectivity, r_pert) for V0 features that are not chimeric and not assigned to 'other'. Every other feature gets 0. A feature that cannot be evaluated counts as 0 in areas.

**Chimera rules:** 'neutral' ('other' counts as adjacent to every concept) is primary. 'orig' (as run in Phase 1) is a sensitivity analysis.

**C(τ)** = the number of gated concepts with at least one feature of v ≥ τ, for τ ∈ {0.50, 0.55, …, 0.90}. Area = mean C(τ) / number of gated concepts.

**Primary metric P:**
- the area with features subsampled to 425 (20 draws, seeded by the replicate); methods with ≤ 425 features use all of them;
- averaged over the two directions (A → B and B → A);
- code: `p1b_sanity/common.evaluate`, key `area_matched_neutral`.

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
  - If E2's dev check fails, the single SAE runs as separate jobs.
- **E3. Memory-mapped input.**
  - `X_ctfm` is written once as a `.npy` file (a byte copy from rows.npz) and memory-mapped, so a job holds only the rows it uses. This applies on the laptop and on Modal.
  - The dense references read only the task rows.
- **E4. Confirmation mode.**
  - Some dev paths are hard-coded: the reference cache `p1b_sanity/results/cache_refpos.npz`, the folder `v2_ct/results/` and `s1a_tasks.npz`. In confirmation mode all of them are keyed to the data folder, so no dev file can be read.
  - `step_tasks` keeps the A1 equality check for dev only.
  - Confirmation jobs log progress and sanity diffs only, never metric values, so there are no interim looks.
- **E5. Analysis script** `v2_ct/s2_confirm.py`. It computes the corrected t, Holm, the intersection–union test (H3) and the fixed sequence, and writes the report, all from the result JSONs.

## 4. Pipeline (run once, after registration)
1. **Fetch** the 555 scans with `fetch_subset.py get` (CRC32-verified) into a new Modal volume, `imgsae-conf`. Nothing goes to the laptop.
2. **Encode** with CT-FM and with the untrained CT-FM (seed 0), at 1.0 mm (E1).
3. **Assemble** with `p1_assemble.py` (ids = `p2_conf_ids.txt`, output `data/p2`). This builds the rows, QC, eligibility, adjacency and the input transform. The transform is fitted on all confirmation tokens; it is label-free, as on dev.
4. **Gates.** The frozen dev `gates.json` is copied in. `p1_probe.py` also runs, but only for sensitivity analysis S3.
5. **Perturbation list.** 20 QC-passing scans are chosen by the production rule (`run_phase1.py`: `default_rng(7).choice` over the assembled scan IDs, sorted). Each gets shift, noise and HU-offset re-encodes with both encoders. After this step, the raw scans are deleted from the volume.
6. **k = 1 task sets:** organ groups, vertebral level and lung lobe. Built by `a1_probe_ladder.build_tasks` with the same caps and seeds; a class needs ≥ 10 patients.
7. **Fits and ladder** for r = 0–9 (§5). SAE jobs run on the L4, CPU jobs on the laptop.
8. **Analysis**, once (E5), writes `results/conf/*.json` and `RESULTS_CONF.md`.

## 5. Replicates
- J = 10 replicates, r = 0–9.
- **Halves:** `p1_fit.halves(scans, r)`, seed 1000 + r, stratified by study type. About 278 scans per half.
- **Evaluation rows:** up to 300 tokens per scan (seeds r and r + 50).
- Each half's model is scored on the other half's scans. The twin score uses the own half's evaluation tokens. Per-replicate numbers average the two directions.
- Every method runs on every replicate with the same halves, so all contrasts are paired by replicate.

## 6. Hypotheses
For each replicate r there is a contrast d_r; the tests are in §7. "Best baseline" means the maximum, in that replicate, over the five frozen baselines (as in G1-main).

| ID | Contrast d_r | Null H0 (mean μ of d) | Claim if H0 is rejected | Dev, reps 0–2 |
|---|---|---|---|---|
| H2 | P(consensus) − max over baselines of P | μ ≤ 0 | The SAE consensus beats every equally tuned baseline | +0.254 (+0.216 / +0.304 / +0.243) |
| H3a | P(consensus) − P(single) | μ ≤ −0.05 | The consensus is not worse on coverage (margin 0.05) | +0.150 |
| H3b | R1(consensus) − R1(single) | μ ≤ 0 | The consensus is more reproducible | +0.303 |
| H3c | P(consensus) − P(single) | μ ≤ 0 | The consensus is better on coverage (tested only if H3 passes) | +0.150 |
| H1 | θ_r of the single SAE | μ ≥ 0.75 | The twin score is an inadequate proxy for validity | 0.653 (0.664 / 0.646 / 0.649) |
| H2b (D1) | P(consensus, CT-FM) − P(consensus, R3) | μ ≤ 0.05 | The CT-FM SAE beats the physics SAE by more than 0.05 | +0.203 (+0.176 / +0.246 / +0.186) |
| H5 (D2) | k = 1 vertebral level: consensus − best baseline | μ ≤ 0 | Single SAE features capture vertebral level better | +0.018 (−0.003 / +0.006 / +0.052) |

**H2.** The differences to each baseline separately are secondary (S4).

**H3** = H3a and H3b together. It is an intersection–union test: both must pass, and p_H3 = max(p_H3a, p_H3b).
- If H3 passes, H3c is tested at the same Holm level. This is a fixed sequence, so it needs no extra alpha.
- The single SAE gets the 425-feature subsampling, like every method with more than 425 features.

**H1.**
- **Estimand:** θ_r = AUROC of the twin score t for validity y, among the single SAE's V0 features, pooled over both half models ('neutral' rule; `ladder.theta`).
- **Validity y:** selectivity ≥ 0.7, not chimeric, gated concept, r_pert ≥ 0.7, V0 (as `p1_fit` and T5).
- **Direction:** from v1's prediction P2 (θ 0.55–0.70; falsified by a lower bound ≥ 0.75).
- **Secondary:**
  - the coefficient adjusted for frequency and magnitude (beta_t);
  - θ for the consensus and the baselines;
  - v1's "adequate" reading (lower 95% bound ≥ 0.70), which is reported but not claimed, so H1 uses one Holm slot.
- **Estimability:** θ_r must be estimable (≥ 20 valid and ≥ 20 invalid features) in every replicate. Dev had about 470 valid and 1,550 invalid.

**H2b.** The comparator uses the CT-FM SAE's config, not one tuned on R3 (§3.2). R3 = HU histogram, mean, SD, texture, 48 mm context and body x/y. It is label-free and contains no z position.

**H5.**
- **If confirmatory (D2):** the matched median AUROC over the vertebral-level classes (`k1_probe` `auc_matched`). For each class, the best single feature among 425 random candidates is chosen on the fit half and tested on the other half (20 draws). The lobe and organ tasks stay descriptive.
- **If descriptive:** the same contrasts are reported for all three tasks, with CIs and no test.

## 7. Inference
**Each contrast:**
- the mean over the J = 10 replicates;
- the Nadeau–Bengio corrected standard error SE = SD × √(1/J + 1) (half splits; `imgsae/stats.corrected_t`);
- t = (mean − boundary) / SE, on 9 df;
- a one-sided p in the claimed direction.

**Holm** step-down over the confirmatory family, at familywise one-sided α = 0.025 (equivalent to two-sided 0.05).
- Recommended family: H2, H3, H1, H2b (m = 4).
- m = 3 if D1 = drop; one more if D2 = confirmatory.

**Reported for each hypothesis:** the estimate, the two-sided 95% corrected-t CI, the one-sided p, the Holm-adjusted p and the decision.

**One analysis run:** no interim looks and no change of rules after unsealing.

**Missing replicates:**
- A failed job is rerun unchanged (same seeds).
- If a replicate still cannot be completed for a technical reason after two reruns, it is dropped for all methods and logged. Inference then uses the remaining replicates.
- A replicate is never dropped because of its results.

## 8. Secondary, sensitivity and descriptive outputs (no claims)
**Sensitivity analyses (pre-specified):**
- **S1:** the 'orig' chimera rule, for H2, H3, H1 and H2b.
- **S2:** areas without subsampling.
- **S3:** the gated set recomputed on confirmation data by the v1 rule (`p1_probe.py`).
- **S4:** H2 against each baseline separately.

**Descriptive:**
- supervised reference: its C(0.7) (the assay check, §10.2), and the SAE as a % of the reference;
- precision (the share of V0 features with v ≥ 0.7), C(0.7), feature counts, and the share of V0 features assigned to 'other';
- θ for all methods; shortcut share; medians of t, selectivity and r_pert;
- nulls: the single physics SAE, and the untrained-CT-FM SAE if D6 says so;
- k = 1 probing on all three tasks (native, and with 425 candidates), with the dense CT-FM, R4 and untrained references;
- R1 for all methods. Raw channels and sparse varimax have R1 ≈ 1 by construction, so their R1 is not compared.

**Limits stated in every report:**
- validity counts only the 33 labelled groups, so precision is underestimated for every method;
- one FM and one dataset;
- scan = patient.

## 9. Planning numbers from dev (not evidence)
With half splits, the corrected SE is about 1.05 × the between-replicate SD. A test therefore passes when (estimate − boundary) / SD is at least about **3.26** at Holm's first step and **2.37** at the last (m = 4, 9 df).

| Hypothesis | Dev estimate | Dev SD (3 reps) | (estimate − boundary) / SD | Estimate needed at the dev SD (last–first step) |
|---|---|---|---|---|
| H2 | 0.254 | 0.045 | 5.6 | ≥ 0.11–0.15 |
| H3a | 0.150 | 0.029 | 7.0 | ≥ 0.02–0.04 |
| H3b | 0.303 | 0.029 | 10.3 | ≥ 0.07–0.10 |
| H1 | 0.653 | 0.010 | 10.1 | ≤ 0.727–0.719 |
| H2b | 0.203 | 0.038 | 4.0 | ≥ 0.14–0.17 |
| H5 (vertebral) | 0.018 | 0.030 | 0.6 | ≥ 0.07–0.10 |

- The SDs come from 3 replicates, so they are imprecise. Confirmation halves are about 3.7× larger than dev halves, which should lower them.
- Choosing configs on rep 0 inflates the dev estimates (winner's curse).
- H2b has the least headroom: it fails if the gain shrinks below about 0.14–0.17.
- H5 would need a gain 4–5× larger than dev showed.

## 10. Checks
### 10.1 Before registration (dev data only)
| Check | Where | Pass |
|---|---|---|
| C1. E1 encode of the 5 gate-E dev scans (s0006, s0015, s0024, s0038, s0040), fetched in the container from HF | Modal L4 | Token tables (occ, ref, pos, gidx) equal the laptop's `data/p1/scans/*.npz`. Median per-token cosine of feat_ctfm and feat_null ≥ 0.995 (the gate E parity rule). The measured seconds per scan set the encode plan (§11) |
| C2. E2 combined job, dev rep 0 | Modal L4 | Single row = `s1a_sae.json` sae_M1024_k6_s12000_rep0, exactly. Consensus row = cons_M1024_k6_s12000_rep0, exactly or within 0.01 on the primary metric |
| C3. CPU runner with memory-mapped input (E3), dev rep 0, the five baselines plus the reference | laptop | Equals `s1a_cpu.json` exactly (R1 and all four areas) |
| C4. E5 analysis script on the Stage 1a rows (J = 3) | laptop | Reproduces RESULTS_S1A: G1 gains +0.216 / +0.304 / +0.243 and physics deltas +0.176 / +0.246 / +0.186 |
| C5. E4 confirmation mode, dry run on a dummy data folder | laptop | Reads no file in the dev folders |

If a check fails, the fix is metric-blind and the check is repeated. Registration waits until all five pass.

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
| Physics consensus (R3), 10 jobs | Same | About 17 min each | 3.7 | Dev: 9–12 min |
| Image builds | | | 1.1 | $0.10 per launch, 11 launches |
| CPU baselines + reference + dense references, 10 replicates | Laptop | About 75 min per replicate; about 13 h in total | 0 | Dev took about 40 min per replicate. The k-means fit and the scoring grow about 3.7×; ICA and DL fit on a fixed 100k rows |
| Download of the CPU inputs from the volume | Laptop | 0.5–3 h | 0 | About 10 GB |
| Analysis | Laptop | Minutes | 0 | |
| **Modal total** | | | **about 17 (range 15–20)** | |

If C1 projects more than $8.5 for the encodes, the work stops for the lead's decision. The options then are: the laptop (about 41 h, $0), more budget, or the second account.

### 11.3 Modal budgets for approval
These are on account shforghani2002, in the ledger `p1b_sanity/cloud/ledger.json`. The worst case of a launch = containers × (timeout + 3 min) × rate + $0.10 for the image.

| Task | Launches | Container | Timeout | Worst case per launch | Expected | Budget |
|---|---|---|---|---|---|---|
| `conf_check` | C1; C2 | L4 8c/32G; L4 4c/16G | 30; 30 min | $0.89; $0.71 | $0.8 | **$1.70** |
| `conf_prep` | fetch; assemble; prep steps | CPU 2c/4G; 4c/64G; 4c/32G | 240; 60; 60 min | $0.61; $0.84; $0.57 | $1.1 | **$2.10** |
| `conf_encode` | main 4 containers (or 2 × 2); perturbations 1 | L4 8c/32G | 1.5 × the time C1 projects | ≤ $7.1 at 20 s per scan | $5.6 | **$9.00** |
| `conf_fit_gpu` | consensus + single 2 × 5; physics 2 × 5 | L4 4c/16G | 40; 30 min | $4.10; $3.17 | $9.5 | **$10.80** |
| `conf_null` (D6) | 2 × 5 | L4 4c/16G | 20 min | $2.24 | $2.5 | $0 unless approved |
| **Total** | | | | | **about $17** | **$23.60** |

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
- It leaves $21.26: enough for the expected $17, with about $4 to spare for retries.
- The task caps sum to more than that, but the check stays on top of them, so actual spending cannot pass $29.

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
1. The lead reviews this draft and decides D1–D7.
2. Engineering changes E1–E5, then the dev checks C1–C5 (task `conf_check`, plus the laptop). C1 fixes the encode plan.
3. Freeze:
   - update this protocol with the decisions and C1's measured rate;
   - commit, and tag `v2-conf-lock`;
   - record the SHA256 of this protocol, the frozen `gates.json`, `p2_conf_ids.txt`, `s1a_lib.py`, `s2_confirm.py` and the job list;
   - Zenodo registration (D7).
4. Unseal and run §4 once.
5. Report (§13). Then the lead decides on the paper.

**Rules** (as v1 §5):
- Jobs come only from the sealed job list.
- Only metric-blind crash fixes are allowed. Every deviation goes in `docs/EXECUTION_LOG.md`, with date and reason.
- No scan is excluded after scoring. No method, config, threshold or test changes after unsealing.
- No metric is looked at until all jobs are done (E4).
- Any post-hoc analysis is labelled post hoc and reported separately.

## 13. Reporting and interpretation
`RESULTS_CONF.md` is generated by `s2_confirm.py` from the JSONs, with no hand-copied numbers. It contains:
- every hypothesis, reported as in §7;
- all secondary outputs;
- every deviation;
- the ledger's spending.

| Outcome | What the paper may say |
|---|---|
| H2 passes | On CT-FM, SAE consensus features cover more valid concepts than equally tuned k-means, ICA, nonnegative sparse coding, raw channels and sparse varimax |
| H2 fails | No SAE-superiority claim; the estimates are reported. The lead decides on the paper (Q2). No reframing after unsealing |
| H3 passes (and H3c) | The consensus keeps coverage (or improves it, if H3c passes) and is more reproducible than a single fit |
| H1 passes | Reproducibility alone is an inadequate proxy for validity (θ < 0.75), so validity must be checked directly |
| H2b passes | Under the same SAE, CT-FM features yield more valid concepts than a label-free physics reference. Caveat: the comparator's config was not tuned |
| H2b fails (D1 = keep) | The SAE advantage is not shown to go beyond HU, texture, context and position |
| H5 / k = 1 | Reported per concept tier, with no claim (D2 = descriptive) |

## 14. Registration package
- This protocol, with D1–D7 filled in and C1's rate, and its SHA256.
- Git tag `v2-conf-lock`: the code of §3.4 and E1–E5.
- Hashes:
  - `p2_conf_ids.txt` (`8dfc5b2d…3caa`);
  - the dev `gates.json`;
  - `s1a_lib.py` and `s2_confirm.py`;
  - the job list.
- The dev results it rests on: `RESULTS_S1A.md`, `s1a_selection.json`, `s1a_selection_m7.json` and `s1a_g1.json`.
