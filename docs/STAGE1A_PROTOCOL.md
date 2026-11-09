# Stage 1a protocol: SAE vs equally tuned decompositions on CT-FM (exploratory, 150 dev scans)

**Fixed:** 2026-11-09, before any Stage 1a test was run. It is committed to git before the first job.
**Source:** the colleague review `docs/REVIEW_AND_PROPOSAL_v2.md` (received 2026-11-09). This protocol adopts it, with the corrections and amendments in §1.
**Scope:** it replaces Stage 1 of plan v2 (`docs/SAE_v2_REVIEW_PACKET.md`, PR #1) for now.
**Data:** only the development data, already analysed many times. Nothing here is confirmatory. The 555 confirmation scans stay sealed.

## 1. Assessment of the review
Every number in the review was checked against `imgsae/exploratory/p1b_sanity/results/{a2_sae_audit,a3_cpu,a3_sae}.json`.

**Verified and agreed:**

| Claim in the review | Our value | Match |
|---|---|---|
| Untuned comparison, M 425 L0 6 (rep 0, 'neutral'): SAE vs k-means | 0.328 vs 0.273 | ✓ |
| Tuned SAE vs best baseline (425 features, 'neutral', reps 0–2) | 0.39–0.40 vs ≤ 0.27 | ✓ |
| Median selectivity | k-means 0.48–0.50; raw / sparse varimax 0.40–0.44; SAE 0.60–0.62 | ✓ |
| Median r_pert | k-means 0.64; raw / sparse varimax 0.46–0.49; SAE 0.79 | ✓ |
| Consensus at the tuned config (rep 0) | 423 / 396 features; area 0.562 vs 0.561 single; at 425 features 0.562 vs 0.432; median t 0.71 vs 0.49; R1 0.51 vs 0.20; r_pert 0.90 vs 0.79 | ✓ |

- **Gaps 1–9 are valid.** In particular, gap 5: raw channels are the identity map, so their R1 is 1 by construction, and sparse varimax's is nearly 1. A method-level "R1–validity inversion" is therefore partly an artefact, and C4 must rest on feature-level θ.
- **Agreed:**
  - narrow the scope (one question first);
  - a same-embedding supervised reference instead of an nnU-Net encoder for now;
  - the encoder tests (S2, nulls) are descriptive at this stage.

**Corrections:**
- **C1. Wrong number.** Under the rule as run, at 425 features, the tuned SAE scores **0.18–0.19** against ≤ 0.05 for baselines. The 0.26–0.28 in the review is the full 1,024-feature area. The conclusion stands.
- **C2. Missing column.** The review's median table leaves out the baselines' twin scores. **The SAE has the lowest per-feature reproducibility of all methods:**

  | Method | Median t |
  |---|---|
  | SAE | 0.47 |
  | k-means | 0.63 |
  | Sparse varimax | 0.93 |
  | Raw channels | 0.96 |

  A second seed on the same half gives R1 0.24, so the SAE's instability comes from the seed. The SAE wins on selectivity and robustness but loses on reproducibility. This is reported, not hidden, and it is the main case for the consensus.
- **C3. The oracle is not an exact ceiling.** It is a supervised reference on the same embedding, and an unsupervised feature can score above it on t or r_pert. It is called the *supervised reference* here, and "SAE as % of reference" is descriptive.

**Amendments** (they make the test harder for the SAE, not easier):
- **M1. One SAE representative.** "Single or consensus" in G1-main would give the SAE two chances. Instead, the SAE family gets one representative, chosen on rep 0 by the same rule as every baseline family (§3). A2's rep-0 numbers already fix that choice: **the consensus at M1024 k6 12k** (0.562, vs 0.432 for the single SAE). This is written down before running.
- **M2. Equal tuning count.** The SAE had 9 rep-0 candidates (8 single configurations plus the consensus). The baselines get as many or comparable numbers (§3): k-means 9, ICA 2, dictionary learning 3, raw channels 2, sparse varimax 2. More baseline candidates raise the bar for the SAE.
- **M3. Nulls are run, not only described (T9).** The review lists nulls as descriptive, but none of its tests runs them. T9 adds the untrained-CT-FM SAE and the physics (R3) SAE at the tuned single config, reps 0–2, for about $1 on Modal. They are needed to tell "the FM helps" from "the SAE method helps", and to read T6.
- **M4. T6 details fixed.**
  - Positive direction only: the feature must fire for the concept.
  - The feature is chosen on the fit half, tested on the other half, and the two directions are averaged.
  - Results are reported at the native feature count and with 425 random candidate features (20 draws), so dictionary size does not buy extra chances.
  - Dense references: CT-FM, label-free R4, and the untrained CT-FM.
- **M5. Dictionary-learning solver** (a change from the review's spec, for engineering reasons).
  - A timing test of scikit-learn's lasso-LARS `MiniBatchDictionaryLearning` (1,024 atoms) had not finished one pass over 20k tokens after more than 5 minutes. The α calibration plus 6 fits per config would not be feasible.
  - Replaced by **k-sparse dictionary learning: OMP coding with k non-zeros plus MOD dictionary updates** (Engan et al. 1999; the K-SVD family). It uses 30 iterations on 100k rows of the fit half, starts from the SAE's own initialisation (`sae._init`), and re-seeds unused atoms.
  - This solves the TopK SAE's own L0-constrained objective per token, without an amortised encoder. It is the most direct answer to "isn't this just sparse coding?".
  - Timing (no validity numbers seen): about 2.7 min per fit at 1,024 atoms with k 6; reconstruction R² on the fit rows 0.775.
- **M6. G1-cal measure.** The mean over the 6 half-models (reps 0–2) of C(0.7) under 'neutral'.

**Open questions for the project lead (they do not block Stage 1a):**
- **Q1.** The review calls FM-vs-physics "a separate question (user decision)". The v1 plan made "beyond intensity and position" part of the core question (gate S). Taking it out of the gates changes the paper's headline, so it needs an explicit decision before the confirmatory protocol. Stage 1a reports it either way (S2, T6, T9).
- **Q2.** The review's G1-main fail branch is "stop the SAE paper, write a methods note". A methods paper was rejected earlier. If G1-main fails, work stops, the result is reported, and the lead decides.

## 2. Common setup (as A3)
- **Input:** CT-FM tokens `X_ctfm`, 1,021,303 tokens from 150 scans.
- **Replicates:** the production patient halves, reps 0–2 (`p1_fit.halves`), with production seeds rep × 7 + half.
- **Ladder:** the production validity ladder (`p1b_sanity/common.evaluate` → `p1_fit.feature_table`), with both chimera rules ('orig' as run; 'neutral' = 'other' adjacent to every concept).
- **Primary metric:** area under C(τ), τ ∈ [0.5, 0.9], with features subsampled to **425** (20 draws), under the 'neutral' rule. Methods with ≤ 425 features use all of them.
- **Sensitivity:** the 'orig' rule; areas without subsampling.
- **Code:**
  - `imgsae/exploratory/v2_ct/s1a_lib.py` and `s1a_run.py` (CPU);
  - `v2_ct/cloud/s1a_sae_modal.py` (SAE rows on a Modal L4, same code path).
  - Stage A and v1 code are not edited.

## 3. Methods and the selection rule
| Family | Candidates on rep 0 | Notes |
|---|---|---|
| SAE (BatchTopK) | A2's 8 single configs + 5-fit consensus at the best | Already run (A2). Representative = **consensus M1024 k6 12k** (M1) |
| Soft k-means | M ∈ {425, 1024, 2048} × L0 ∈ {1, 6, 27} | `p1_fit.Model('soft_kmeans')`; one fit per M shared across L0 |
| FastICA | L0 ∈ {6, 27} | 512 components, whitened (unit variance), fit on 100k rows; split-signed (1,024 features), top-L0 |
| Dictionary learning | (atoms, k) ∈ {(1024, 6), (2048, 6), (1024, 27)} | OMP + MOD (M5); split-signed (2 × atoms features), L0 = k |
| Raw channels | L0 ∈ {6, 27} | As Phase 1 / A3 |
| Sparse varimax | L0 ∈ {6, 27} | As Phase 1 / A3 |
| Supervised reference | 1 | Multinomial LR (C 1, balanced) on the fit half's labels with T1b caps (≤ 2,000 core tokens per eligible concept, 20,000 'other'). Features = probabilities of the 33 eligible concepts. Not a competitor |
| Nulls (T9) | SAE M1024 k6 12k on untrained CT-FM, and on physics R3 | Descriptive |

**Selection rule** (all families the same):
1. Within a family, the representative is the rep-0 candidate with the highest primary metric (ties → higher R1).
2. Only the representative runs on reps 1–2.
3. The SAE representative is re-run on rep 0 on the L4, so all three replicates come from the same hardware.

## 4. Tests
| ID | What | Output |
|---|---|---|
| T1 | k-means at equal tuning (§3) | Family representative |
| T2 | FastICA and dictionary learning (§3) | Family representatives |
| T3 | Supervised reference through the same ladder | G1-cal; SAE as % of reference |
| T4 | Precision: share of V0 features with v ≥ 0.7; C(0.7); feature count; share of V0 features assigned to 'other' (gap 9) | Descriptive |
| T5 | θ exactly as `p1_fit` (valid = sel ≥ 0.7, not chimeric, gated, r_pert ≥ 0.7, V0; predictor = twin score), both rules; single SAE and consensus | The original D2, descriptive |
| T6 | k = 1 sparse probing (M4) on Stage A's A1 token sets: T1b organ groups (33), T3 vertebral level (24), T3 lung lobe (5) | Descriptive; becomes H5 at confirmation |
| T7 | Consensus at M1024 k6 12k, reps 0–2 | Needed for G1-main (M1) |
| T8 | D3 shortcut share at each representative (as `p1_fit`) | Descriptive |
| T9 | Nulls (M3) | Descriptive |

## 5. Gate G1 (fixed now; read once, after all representatives have reps 0–2)
- **G1-cal.** The supervised reference covers **≥ 20 of the 32 gated concepts** at C(0.7) ('neutral'; mean over the 6 half-models).
  - If it fails, the ladder thresholds are the bottleneck. Stop and report before any confirmation work; a threshold sweep would need a new decision.
- **G1-main.** For each rep r ∈ {0, 1, 2}: gain_r = (SAE representative's primary metric) − (the maximum, over the k-means, ICA, dictionary-learning, raw and sparse-varimax representatives, of their rep-r primary metric).
  - **Pass** if gain_r > 0 in all 3 reps **and** the mean gain is ≥ 0.05.
  - **Fail, and dictionary learning is the strongest baseline in ≥ 2 reps:** the "sparse coding" branch. Report; the lead decides on reframing.
  - **Fail otherwise:** stop the SAE paper and report; the lead decides (Q2).
- **Both pass:** freeze the SAE and baseline configs under the same tuning budget, write the confirmation protocol, then register (the review's order, steps 2–3).
- **Descriptive only:**
  - SAE as % of the reference; precision (T4); θ (T5); k = 1 probing per concept tier (T6); the single SAE; nulls (T9); shortcut share (T8); S2;
  - every number under the 'orig' rule and without subsampling.

## 6. Sanity rows (every job checks a known number first)
- **CPU** (raw channels, sparse varimax and k-means M425 at L0 6 and 27, on every rep they run): R1 and all four areas must **equal** `a3_cpu.json` exactly. Any mismatch stops the runner.
- **Single SAE on the L4, reps 0–2:** must match the A3 L4 rows (`a3_sae.json`, `sae_best_k6`), exactly or within seed noise (≤ 0.01 area). Reported.
- **Consensus, rep 0:** within seed noise of A2's row (local GPU). Reported.
- **T6 token sets** equal A1's (same builder, same seeds; checked by token count and class list).

## 7. Compute and budget
- **CPU parts:** this laptop, about 4–5 h. **SAE parts:** Modal L4.
- **Modal budget.**
  - Task `v2s1a_sae` gets **$5**, on account shforghani2002.
  - User rule: $29 per Modal account per month; usage is checked before every launch, and no task exceeds its budget.
  - Worst cases are bounded by the job timeouts: about $3.2 for 9 single jobs at 15 min, and about $2.2 for 3 consensus jobs at 35 min. They launch in two batches; the expected total is about $2.5.
  - The X_null array goes to the existing volume `imgsae-p1b` (`/p1/rows_extra.npz`, 2.1 GB).
- The superseded Phase 1b Stage C/D budgets in the ledger are set to 0 and marked.

## 8. Outputs
- `v2_ct/results/s1a_cpu.json`, `s1a_sae.json`, `s1a_refs.json`, `s1a_selection.json`;
- per-feature tables `results/tables/*.csv.gz`;
- `v2_ct/RESULTS_S1A.md` with the G1 read-out;
- logs in `v2_ct/logs/`;
- an entry in `docs/EXECUTION_LOG.md`.

After G1 the work stops for the project lead's decision.
