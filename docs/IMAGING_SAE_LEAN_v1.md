# Imaging SAE: lean plan v1 FINAL (2026-11-06). Phase 1 = merit in 7 days; Phase 2 = lean paper by about week 4

## Context
The v0 design (`IMAGING_SAE_DESIGN_v0.md`) was rigorous but about 4× too wide: 3 domains, about 12 encoders, about 12 SAE variants, a lesion simulator and about 130 h of radiologist time.

Goals:
- the width cut, not the rigour;
- one or two datasets;
- a definitive merit verdict within 1 week;
- a lean paper in about 1 month;
- everything on the Mac, with no paid GPUs.

Three reviews (R1, R2 on v0; R3 on v1) were read and each point checked (verdicts below).

Three decisions follow:
1. Use PUBLIC data only. This means no ethics approval, no de-identification and no hard-drive data on the critical path.
2. Run ZERO segmentation, because both datasets ship masks.
3. Do no human labelling. The only human time is about 3 h of blinded reading at the end.

The internal breast, CTA and prostate data become papers 2–3, reusing the validated framework. v0 stays as that roadmap.

## Review response (accepted or rejected after checking)
| # | Point (source) | Verdict | Reason and action |
|---|---|---|---|
| 1 | Plan 3–4× too big (R1, R2) | ACCEPT | It is cut to one CT dataset plus one MRI dataset, one encoder per modality, and 4 primaries. |
| 2 | People are the bottleneck; 130 h of reads (R1, R2) | ACCEPT | No reader-made labels. V4 only: 40 features, 2 readers, about 1.5 h each, on a static HTML page. Readers are needed in week 4, not before. |
| 3 | 4–6 months even for the lean plan (R1) | REJECT for this plan | That estimate assumes ethics approval, internal data and readers. All three are now off the critical path. The full v0 plan does take 12–18 months; I agree with that. |
| 4 | Laptop risky; use Modal GPUs (R1) | PARTIAL | The risk is real: MPS conv3d memory and throttling. It is handled by a day-2 engineering gate with fallbacks (1.5–2 mm spacing, DINOv3 2D, CPU fp32). Cloud only if that gate fails and the signal looks promising; Mac-only is preferred until merit is shown. |
| 5 | Lesion insertion is a research project in itself (R1, R2) | ACCEPT | Dropped. R2's "3 simple planted objects" is also REJECTED, because unvalidated insertion invites dismissal. Planted truth stays in embedding-space unit tests. Dose-response uses natural ladders, as association, not causation. |
| 6 | Too many single cut-offs; conjunctive gates send C3 → 0 (R1, R2) | ACCEPT | Thresholds are calibrated on positive controls and nulls in Phase 1 (rule below). Results also go into a threshold-free weakest-link curve C(τ), which becomes the primary metric. R2's 0.85^10 arithmetic assumes the gates are independent, so it overstates the risk, but the point stands. |
| 7 | H1 may be undecidable (R1) | ACCEPT | Estimability is checked in Phase 1 (≥ 20 features per class). If that fails, the pre-stated fallback is a continuous Spearman version. |
| 8 | N mismatch (R1) | PARTIAL | Breast 200 + 50 + 20 = 250 + 20 is correct, so REJECT. The CTA count (350 vs 451) is a real ambiguity, but CTA is out of the lean plan. Fix it before the CTA paper. |
| 9 | Missing papers: MedConcept 2604.11868, Sparse Concept Channels 2607.20993 (R1) | ACCEPT | Checked. Sparse Concept Channels is probe-based (about 10 raw channels per finding, ablation; Pillar-0/Merlin). MedConcept uses an LLM judge. Neither reports seeds, rotation baselines or readers, so the novelty holds. Both are cited, and a raw-channel sparse basis is added as a baseline. |
| 10 | saegt fixes may touch the BiB paper (R1) | ACCEPT | The new `imgsae` package keeps fixes behind default-off flags, sae-groundtruth stays frozen, and an equivalence test runs with flags off. (Checked: for the best Hallmark set the code's q = p × m, i.e. Bonferroni, so the BiB text is correct; no change needed.) |
| 11 | Triad pretraining includes PI-CAI and PROSTATEx (R2) | ACCEPT | Verified: the TriadMR-131K figure lists PROSTATEx (17,313) and PI-CAI (5,995). v0's check was wrong. Triad is dropped, and DINOv3 (leak-free) is used on PI-CAI. |
| 12 | Clinicians only for V4; about 6 h total (R2) | ACCEPT | See #2. |
| 13 | TotalSegmentator inference and PyRadiomics are underestimated (R2) | ACCEPT | Removed by design: masks are shipped with the data, and texture features are vectorised torch conv3d/2d (first-order, gradient, LoG, local variance) instead of PyRadiomics. |
| 14 | CTA has poor cost-to-payoff (R2) | ACCEPT | Deferred to its own paper. |
| 15 | Keep H1–H5 unchanged (R2) | REJECT | Lean plan uses 4 primaries. Variants (Matryoshka) become a secondary estimate. |
| 16 | V1b/V1c descriptive; continuous score; lock after development (R2) | ACCEPT | These are built into Phase 2. |
| 17 | Breast + prostate as the 2 domains (R2) | REJECT for the lean paper | The internal breast data need ethics approval, RTSTRUCT parsing and laterality QC, which would blow the 1-month target. The CT leg is TotalSegmentator instead: public, many concepts, and the exact dataset of the closest prior work (Wesp). The breast 2×2 design is kept for paper 2. |
| 18 | Selectivity shrinks as the number of concepts K grows (R3 trap 1) | ACCEPT problem, MODIFY fix | The problem is real: Σ over K = 60 dilutes a pure feature to about 0.46. R3's fix (μ* vs 6 × the mean of the others) would let a feature that fires equally on 5 of 60 organs pass (0.71). The fix adopted is sel_f = μ* / (μ* + the sum of the 6 largest other concept means). At K = 7 this is identical to the omics formula, it ignores irrelevant concepts, and it still fails multi-organ features (0.2). A two-level atlas is added: about 25–30 group concepts (primary) and the 117 leaves (secondary, like omics fine types). |
| 19 | Integer-stride jitter is trivially about 1 for a stride-16 CNN (R3 trap 2) | ACCEPT | Correct: the interior convolution is shift-equivariant, and GroupNorm barely changes with padding. Integer-stride jitter tests crop-locking only for position-aware encoders. The rule becomes r_pert = min(r_shift, r_noise, and r_HUoffset for anat-class features only). r_shift is a half-stride 8 mm shift, interpolated to token centres, for CNNs (this catches stride-2 aliasing), and integer-stride for ViTs/DINOv3. |
| 20 | PI-CAI has only about 3 spatial concepts (R3 trap 3) | ACCEPT | C(τ), θ and the chimera rule are degenerate on PI-CAI. PI-CAI endpoints become R1, lesion selectivity/AUROC, shortcut share, P8 and H4. The secondary H1–H3 replication moves to DINOv3 on TotalSegmentator only. |
| 21 | PI-CAI human lesion masks split across 2 folders (R3) | ACCEPT (verify at download) | The loader merges human_expert/resampled (220 positives) with Pooch25 (205 positives), giving 425. It resamples T2W, ADC and HBV to one physical space before gridding. |

## Scope, kept vs cut
- **KEPT (the rigour):**
  - patient-grouped split halves; cross-fitted scoring;
  - nulls: random-init encoder and frozen-decoder SAE;
  - the HU/intensity + context + position reference (beyond-HU tier);
  - acquisition features as a shortcut ledger, never counted as wins;
  - validated coverage;
  - θ as the central test;
  - Zenodo registration before confirmation, falsifiers, the Nadeau–Bengio corrected t, cluster bootstrap, Holm, and a deviation log.
- **CUT (the width):** CTA, breast, the internal prostate set, lesion insertion, TotalSegmentator inference, COLIPRI, VoxelFM, Pillar-0, SPECTRE, Triad, ProFound, the 8-variant SAE zoo, DL+OMP, NMF, ICA, the Gerasimov and decoder-direction consensus sweeps, levels L2–L4, and S5 reads (except V4).

## PHASE 1: fast-track feasibility (7 days; Mac only; one public dataset; decision rules written before running)
- **Question.** On a real 3D CT foundation model, do SAE features carry concept information that is (a) technically feasible to extract here, (b) beyond intensity and position, and (c) different from what the baselines get, or do they give a clean reproducibility-vs-validity dissociation? A yes or no answer decides whether a paper exists.
- **Data.** 150 CTs from TotalSegmentator v2 (Zenodo, CC-BY, 23.6 GB; 117 expert-reviewed masks).
  - Chosen from meta.csv (columns to verify on day 1): thorax/abdomen field of view, at least 20 structures present, stratified by institute, scanner and contrast.
  - These 150 become development data and never enter confirmation.
- **Encoders.** CT-FM (lighter-zoo, Apache-2.0; pretrained on IDC, which does not include TotalSegmentator), plus a random-init CT-FM null.
  - Grid: 16 mm tokens at 1 mm, or 1.5 mm if memory requires; one whole-volume pass; tokens within 32 mm of the edge dropped; padding set to −1024.
  - Fallback encoder: DINOv3 ViT-L 2D slices mapped onto the same grid (Wesp's encoder).
- **Concepts.**
  - anat: a two-level atlas. Group level (primary, about 25–30 groups such as lungs, liver, vertebrae, ribs and muscles, with an adjacency table for the chimera rule) and leaf level (the 117 structures, secondary). Eligible if at least 10 patients have a core token (occupancy ≥ 0.8). The atlas is fixed before any fit.
  - acq: scanner, kVp, contrast, institute, slice thickness (meta.csv plus an aorta-HU contrast flag).
  - HU-derived path, always HU tier: liver HU, lung LAA−950, L1 HU, aortic calcium.
- **Methods (same rows).**
  - SAEs: plain BatchTopK single fit and 5-fit symmetric consensus (≥ 3 of 5, r ≥ 0.7), with M = min(4d, n_eff/50) and k = M/16.
  - Baselines: PCA, varimax, sparse varimax at the consensus L0, soft k-means, raw-channel sparse basis, an HU-histogram SAE and a frozen-decoder null.
- **Metrics.**
  - V0 (technical).
  - V1a twin score t_f, from patient-grouped halves, J = 3.
  - V2: probe gate (lower 95% AUROC bound ≥ 0.70); selectivity sel_f = μ*/(μ* + the sum of the 6 largest other concept means); non-chimeric; HU vs beyond-HU tier (dense − reference ΔAUROC ≥ 0.05, lower bound > 0).
  - V3-lite on 20 scans: r_pert = min(r_shift, r_noise, and r_HUoffset for anat features). r_shift uses an 8 mm half-stride shift for CT-FM and integer strides for DINOv3. Noise is +50%; the HU offset is +20.
  - Weakest-link validity v_f = min(t_f, sel_f, r_pert,f), and the curve C(τ) over τ ∈ [0.5, 0.9].
  - θ, and the shortcut share.
- **Day plan**
  - D1: installs (nibabel, SimpleITK, monai, lighter-zoo); download; port the `imgsae` kernel and run its tests (bitwise equal to saegt with flags off; planted-truth unit tests).
  - D2: engineering gate on 5 scans, then encode 150 scans plus the null encoder overnight via `prun`.
  - D3: token table, reference features, probes, signal gate.
  - D4: SAEs and baselines at J = 3.
  - D5: ladder, funnel, θ; perturbation re-encodes overnight.
  - D6: V3-lite, shortcut audit, threshold sweeps. Optionally, if time remains: DINOv3 arm, or a 200-case PI-CAI lesion-signal check.
  - D7: one-page decision memo.

**Decision table (fixed now)**

| Gate | Pass rule |
|---|---|
| E, engineering | CT-FM (or the DINOv3 fallback) needs ≤ 5 min per scan, a memory footprint ≤ 12 GB, CPU parity cosine ≥ 0.995, and all 150 scans encoded within 24 h of wall time |
| S, signal | ≥ 15 gated anat concepts and ≥ 3 beyond-HU concepts from the dense probe |
| D1, SAE advantage | Consensus or single-fit area under C(τ) above the strongest baseline in all 3 replicates, with mean gain ≥ 0.05 (normalised) |
| D2, dissociation | Consensus R1 ≥ 0.60, and the upper bound of θ < 0.75 (or Spearman < 0.3 if θ cannot be estimated) |
| D3, shortcut | ≥ 20% of reproducible consensus features encode acquisition (scan-mean AUROC ≥ 0.8) or are crop-locked |
| Degeneracy | C(0.7) > 0 for at least 2 methods, and at least 20 features in each class for θ |

- **GO-positive:** E + S + D1. Headline: "SAE features are valid where baselines are not, and reproducibility misleads."
- **GO-cautionary:** E + S + (D2 or D3), without D1. Headline: "Imaging SAE features are reproducible but mostly intensity, position or shortcut features." Publishable, but at a lower tier.
- **NO-GO:** E fails on both encoders; or S fails (the model adds nothing beyond intensity and position at 16 mm); or none of D1–D3 holds; or the degeneracy check fails. Stop, and write the 1-page memo.

## PHASE 2: lean protocol → lean paper (weeks 2–4, only after GO)
- **Week-2 registration** (about 3 pages on Zenodo, reusing the spatialfloors PROTOCOL skeleton).
  - Locked from Phase 1: M*, s*, the strongest baseline (chosen among sparse varimax, soft k-means, raw-channel basis and HU-histogram SAE), the spacing, and the concept list.
  - Thresholds are set by rules, not by looking at results:
    - t_f cut = max(0.7, the 99th percentile of the random-code twin score);
    - r_jit cut = the 5th percentile among organ positive-control probe directions;
    - selectivity and AUROC cuts are kept from omics (0.7 / 0.80) and reported with sweeps.
  - Sealed job list and manifests. Deviations log.
- **Data.**
  - (1) TotalSegmentator confirmation set: every other eligible scan (about 700–900). Transport by institute and scanner is reported descriptively.
  - (2) PI-CAI: 1,500 bpMRI, 425 csPCa, human lesion masks for all cases, CC-BY-NC. Split 50/50 by patient, stratified by centre × csPCa, sealed.
- **Encoders.**
  - CT-FM on TotalSegmentator.
  - DINOv3 ViT-L on TotalSegmentator (2D; the Wesp head-to-head) and on PI-CAI (2.5D, with T2W, ADC and HBV each encoded and the tokens concatenated; leak-free).
  - Random-init nulls of both.
  - DINOv3 is gated: its licence must be accepted on Hugging Face.
- **Methods.** As in Phase 1, plus a Matryoshka consensus (a secondary estimate; this is Wesp's SAE). On PI-CAI the intensity reference is the T2/ADC/HBV histogram + context + position, and the texture baseline is the vectorised filters.
- **Ladder.**
  - Gates: V0, V1a, V2 and V3-lite (with natural ladders on PI-CAI: lesion size, ISUP grade).
  - Descriptive only: V1b and V1c.
  - V4: 40 features (20 consensus, 10 sparse varimax, 10 null), 2 readers × 3 region-matched intruder trials, a static HTML page, about 1.5 h per reader. If no readers are available, report it as not done.
- **Primary hypotheses** (Holm over 4; patient as the unit; corrected t over J = 10 on TotalSegmentator and J = 5 on PI-CAI; cluster bootstrap):
  - **H1 (proxy):** θ = AUROC of t_f for validity (V2 ∧ V3), within single fits, adjusted for activation frequency (CT-FM on TotalSegmentator). Adequate if lower bound ≥ 0.70; inadequate if upper bound < 0.75.
  - **H2 (baselines):** consensus − strongest baseline, normalised area under C(τ) over gated anat+path concepts. Superiority. Key secondary: the beyond-HU-only version.
  - **H3 (consensus vs single):** area under C(τ), non-inferiority margin 0.05. Key secondary: R1 superiority.
  - **H4 (clinical, PI-CAI confirmation half):** the increment in csPCa AUROC of the frozen SAE score set over PSAD + age + volume, minus the texture-baseline increment. Non-inferiority margin 0.03.
    - Scores are selected outcome-blind on the development half, using concept alignment to the lesion masks.
    - Centre is excluded as a confounder (AUROC < 0.6).
  - **Secondaries:** H1–H3 replicated on DINOv3-TotalSegmentator only; Matryoshka vs plain.
  - **PI-CAI endpoints** (only about 3 spatial concepts there): R1, lesion selectivity/AUROC, shortcut share (centre, b-value), P8 and H4. No C(τ), θ or chimera rule on PI-CAI. Lesion labels = human_expert/resampled + Pooch25 (425 positives).
- **Predictions** (each with its falsifier, F):
  - P1: single-fit R1_g is 0.20–0.45 and consensus R1_g 0.65–0.90. F: consensus < 0.60 or single > 0.60.
  - P2: θ is 0.55–0.70. F: lower bound ≥ 0.75.
  - P3: varimax passes V1 at ≥ 0.95 but V2 at ≤ 0.10; consensus precision ≥ single + 0.15. F: consensus ≤ single.
  - P4: the HU-histogram SAE and sparse varimax are within 1 concept of the consensus on HU-tier concepts, and the consensus leads by ≥ 2 on beyond-HU concepts. F: either pattern reversed.
  - P5: the consensus covers 1 concept fewer than the single fit (range −2 to 0), the omics cost.
  - P6: ≥ 20% of reproducible features are shortcuts. F: < 5%.
  - P7: H4 non-inferiority holds. F: lower bound < −0.03.
  - P8: on PI-CAI, the SAE lesion-detection threshold (by lesion size) sits above varimax's: the omics weak-state miss on a natural ladder. F: SAE ≤ varimax.
- **Weeks.**
  - W2: register; encode TotalSegmentator confirmation (CT-FM and DINOv3) and PI-CAI at night.
  - W3: confirmatory runs, ladder, H1–H4, build the V4 page.
  - W4: V4 reads; figures; manuscript (IMRaD, cautious claims); code and benchmark release; arXiv/medRxiv preprint.
- **Compute.** About 60 GPU h, about 5 wall days at throttled speed:
  - TotalSegmentator encodes: CT-FM about 27 h, DINOv3 about 10 h;
  - PI-CAI encodes: about 5 h;
  - SAE fits: about 15 h;
  - perturbations: about 5 h.
  Disk: about 70 GB, which fits in the 205 GB free.
- **Venue.** With V4 and the PI-CAI leg: *Radiology: AI* (short original research). Without readers: *MedIA* / *TMI* / *MIDL*.

## Deferred (papers 2–3, framework reused)
Breast RT CT (the 2×2 natural experiment, needs ethics approval and RTSTRUCT parsing), CTA + MACE (estimation; the 350 vs 451 count to be fixed), internal prostate (transport), lesion insertion, the SAE variant zoo, and the remaining encoders. Ethics applications for these can start now, in parallel.

## Machine rules
- One GPU job at a time, with a footprint watchdog at about 12 GB.
- Profile 5 scans and state the ETA before any long run.
- Long jobs go through a launchd runner (`prun`) at normal priority, with ≤ 4 threads and a completion line written to the log.
- Check `macperf` before launching, and never stop another project's job.

## Files and reuse
- **Docs** in `N2/paper/imaging SAE/`: IMAGING_SAE_LEAN_v1.md (this plan), REVIEW_RESPONSE.md, PROTOCOL_lean.md (week 2), DECISION_MEMO_P1.md (day 7).
- **Code:** a new package at `/Users/Hemato/project_3/imgsae`. It ports from saegt/sae.py: MSAE (:20), _init (:40), fit (:48), the threshold (:85–91), encode (:98), fits_codes (:248), consensus_codes_cl (:268), control_codes (:129), split_signed (:120), topk_rows (:123), act_match (:152), alive (:149), lineage_selectivity (:163). Template: scripts/run_llm.py.
- **New modules:** grid and token table, occupancy labels, reference features (histogram, context, Fourier position, vectorised texture), ladder and C(τ), θ, stats (corrected t, cluster bootstrap, Holm).

## Verification
- **D1:** bitwise equivalence to saegt with flags off. Unit tests: random-code R1 ≤ 0.05; identical-code R1 = 1; the θ estimator recovers a planted θ within ±0.03; the cluster-bootstrap CI covers 0.93–0.97 in simulation; MPS and CPU L0 within 1%.
- **D2:** encoder parity and memory gate.
- **D7:** the decision table, applied as written.
- **Phase 2:** jobs from the sealed list only; ≥ 95% pass QC; the tier-1 report is written before any secondary analysis.

## Next steps (plan final)
2. Environment: a venv at /Users/Hemato/project_3/imgsae/.venv (miniforge Python 3.11, `--system-site-packages`, so torch 2.10 with MPS is reused and the base environment is untouched). pip install nibabel, SimpleITK, monai, lighter-zoo. Check the torch version and MPS afterwards.
3. Data: TotalSegmentator v2 from Zenodo (resolve the latest-version file URL through the API), downloaded in the background with resume (`curl -C -`) to /Users/Hemato/project_3/imgsae_data/totalseg. Unzip, then read meta.csv.
4. Pipeline, day 1:
   - `imgsae` package (sae.py, consensus.py, baselines.py, metrics.py with the K-robust selectivity, stats.py);
   - tests/test_equivalence.py (bitwise equal to saegt with flags off);
   - tests/test_units.py (planted-truth gates);
   - `encoders/ctfm.py` stub, plus the 5-scan engineering-gate script (`scripts/p1_d2_engineering.py`).
   Command output goes to logs; long jobs use `prun`.
5. In parallel: ask 2 radiologists for about 1.5 h each in week 4; accept the DINOv3 licence on Hugging Face.
