# Imaging SAE — status and handover

**Updated:** 2026-11-10 · **Phase:** clinical leg, prostate MRI (PI-CAI): M1 gate FAILED, waiting for the lead's decision · **Machine:** ASUS Vivobook Pro 16X (M7600QE), RTX 3050 Ti 4 GB (CUDA)

**Now (2026-11-10):** **Prostate MRI M1 gate FAILED; stopped per the protocol, waiting for the lead's decision.** Results in
`imgsae/mri/RESULTS_M1.md`.
- **Gate (nested CV):** Δ vs the intensity reference R = −0.022 [−0.038, −0.007] (needed ≥ +0.03); Δ vs the untrained network
  −0.005 (needed ≥ +0.05). Same on verified studies.
- **AUROC by arm:** R 0.912; MRI-CORE B 0.909; untrained 0.894; SAM 0.879–0.894; ProFound 0.882.
- **Post hoc checks:**
  - the mapping is correct (no bug);
  - MRI-CORE A with strong regularisation is +0.014 over R;
  - R + MRI-CORE is +0.013 over R + untrained.
  - So MRI-CORE has a small extra signal (about 0.01), under half the margin.
- **Patient level, biopsy cohort:** 0.66 for both MRI-CORE and R, below PI-RADS alone (0.72).
- **Recommendation:** stop the frozen-encoder SAE line (no M2). Optional next step, a no-cost laptop feasibility check of the hard
  clinical question (csPCa within PI-RADS ≥ 3); it needs a new protocol.
- **MRI Modal spend:** $5.12 (fetch 0.37, prep 0.30, encode 4.45 of the 5.00 cap). No run is open.

**Earlier: M0 DONE** (results `imgsae/mri/RESULTS_M0.md`).
- **Data:** split 738/738 patients; fetch MD5-checked (26.9 GB); dev prep 754/754; 1 study excluded by the label-blind QC (11050_1001070,
  README-documented faulty gland mask); 753 dev studies used, 212 positive.
- **Decisions:**
  - ADC units ok;
  - **token size 4 mm**;
  - **outline difference material** (RUMC Pooch25/resampled volume ratio 0.60): cross-centre token results are annotation-dependent,
    and the clinical claim rests on patient-level M3.
- **Encoders, all usable after the fixes:**
  - MRI-CORE runs as its trained DINOv2 ViT-B/16 (the repo loader would use a random neck and drop the position embedding);
  - ProFound-alpha is the ConvNeXt variant (stage 0, 4 mm);
  - SAM via the official loader; untrained null.
- M0 spend $1.10; the user approved M1 after reviewing M0.

**Earlier (2026-11-10):** CT confirmation STOPPED by the user's decision (goal = a clinical finding, not a methods result).
- **Plan revision 2 (2026-11-10)**, after the colleague review (`docs/REVIEW_PLAN_PROSTATE_MRI_v1.md`, R1–R6, all facts recomputed:
  `docs/RESPONSE_REVIEW_PLAN_PROSTATE_MRI_v1.md`).
  - Primary clinical population is now the biopsy cohort (verified, PI-RADS ≥ 3: 884 studies, 467 without csPCa).
  - Equal-capacity scores against intensity and texture controls; PSAD recomputed for every study; token size by a lesion-recall rule;
    within-centre results.
  - **Revision 3 (2026-11-10): encoders changed.** The user asked why a natural-image model, and Meta rejected the DINOv3 request.
    - ProFound (prostate MRI; saw PI-CAI images, no labels; disclosure + external test) and MRI-CORE (Duke MRI only) are the main
      candidates; SAM ViT-B is the comparison.
    - Two-level leak rule; common token grid; gland-only storage. No Hugging Face token needed.
    - Also adopts the colleague's second review (`docs/REVIEW2_PLAN_PROSTATE_MRI_v1.md`; reply `docs/RESPONSE_REVIEW2_PLAN_PROSTATE_MRI_v1.md`):
      - Q1: the outline source (Pooch25 / resampled) is tied to centre, so the sources are compared within RUMC, with a per-source
        token-size rule and a materiality rule;
      - Q2: zone enters R; gland and zone QC uses the agreement of two AI masks, label-blind.
  - **Revision 4 (2026-11-10)** adopts the third review (`docs/REVIEW3_PLAN_PROSTATE_MRI_v1.md`; reply
    `docs/RESPONSE_REVIEW3_PLAN_PROSTATE_MRI_v1.md`):
    - T1: rule S prefers an unexposed encoder (ProFound only if ≥ 0.02 better with CI > 0);
    - T2: one intensity rule (fixed ADC window; per-study percentiles for T2W and HBV; per-slice min–max as sensitivity only);
    - T3: nested cross-validation for the M1 gate.
    - Still waiting for the user's OK and the M0–M1 budget ($6.60).
  - Waiting for the user's OK on revision 3 and the M0–M1 budget.
- **Plan:** `docs/PLAN_PROSTATE_MRI_v1.md` (DRAFT; branch `prostate-mri-plan`). Stages:
  - M0 setup: fresh PI-CAI download, split, QC;
  - M1 "does the model know cancer?" gate;
  - M2 features; M3 clinical value; M4 readers; M5 sealed confirmation.
- Budgets asked for M0–M1: $6.60 in caps (expected about $4): mri_fetch $0.80, mri_prep $0.80, mri_m1_encode $5.00.
- **PI-CAI data:** fresh download from Zenodo + `picai_labels` (user's rule: any doubt → fresh). The Modal volume `picai-dataset-vol` (another
  project) is NOT used: it holds processed images (t2_norm, adc_norm, no HBV, ai_heatmap). It was inspected read-only, by file names only.
- **CT:** the 555 TotalSegmentator scans stay sealed. They have no tumour masks, only a scan-level "tumor" tag (136 of 555, mixed sites).
  CT protocol revision 2 is archived unregistered on branch `protocol-v2-review`. Stage 1a is kept as method evidence.

**State in one line (history):** Phase 1 DONE (verdict **NO-GO**, memo `docs/DECISION_MEMO_P1.md`). Exploratory checks done (`imgsae/exploratory/p1_checks/README.md`): NO-GO stands.
**Stage 1a (2026-11-10):** DONE, gate G1 PASSED, both post-G1 fixes done. Protocol `docs/STAGE1A_PROTOCOL.md` (colleague review of plan v2, adopted with amendments; G1 fixed before running). Results `imgsae/exploratory/v2_ct/RESULTS_S1A.md`.
- G1-cal pass: the supervised reference (oracle) covers 21.7 of 32 concepts at C(0.7).
- G1-main pass: SAE consensus beats the best equally tuned baseline (k-means / ICA) by +0.22 / +0.30 / +0.24 (mean +0.25); it reaches 86–94% of the oracle.
  **Correction (colleague review, 2026-11-10):** this is inflated. The consensus (~400 features) escapes the 425-feature subsampling.
  Like for like (single SAE vs best single baseline), the gain is +0.090 / +0.122 / +0.100 (mean +0.104), and G1 still passes.
- Flags: the physics-feature SAE comes close on organ concepts; no SAE advantage on vertebral level at k = 1.
- **Post-G1 checks done (2026-11-10, user: "do the two fixes"; sensitivity only, G1 stands; RESULTS_S1A.md checks 1–2, EXECUTION_LOG):**
  - Physics-feature SAE consensus 0.35 / 0.34 / 0.35; CT-FM consensus beats it by +0.18 / +0.25 / +0.19 (≥ 0.05 in every rep).
  - Nonnegative DL (deviation M7): 0.063 / 0.046 / 0.038, still far below k-means / ICA; G1-main unchanged. A label-free check shows the
    two halves' dictionaries agree but the OMP codes don't: the instability is in the coding step.
- Open: Q1 (keep "beyond physics" in the gates / headline?) and the freeze decision. Code `imgsae/exploratory/v2_ct/`; Modal task v2s1a_sae $6.06 of $7.
- **CT confirmation protocol, revision 2 (2026-11-10): ARCHIVED, stopped by the user before registration** (branch `protocol-v2-review`):
  `docs/SAE_PROTOCOL_v2.md` (DRAFT, not registered, nothing run). It adopts the colleague's review `docs/REVIEW_PROTOCOL_v2.md` with
  refinements; the reply is `docs/RESPONSE_REVIEW_PROTOCOL_v2.md`.
  - Family {H2, H3, H1}, m = 3: H2 single SAE vs best single baseline (dev +0.104); H3 consensus non-inferior at all features + R1;
    H1 0.5 < theta < 0.75. H2b and H5 descriptive (D1, D2 decided).
  - Open in its §0: D3 (CPU baselines on the laptop), D4 (20 perturbed scans), D5 (Modal budgets: caps $22.00, expected ~$15.7; the
    ledger's all-time $29 check leaves ~$5.5), D6 (null SAE), D7 (Zenodo), D8 (dev-only consensus check for k-means and ICA).
  - Then: engineering E1–E6, dev checks C1–C6, freeze, register, run once (step 3).
- Earlier: Phase 1b Stage A DONE (`imgsae/exploratory/p1b_sanity/RESULTS.md`); plan v2 review packet `docs/SAE_v2_REVIEW_PACKET.md` (PR #1).

## Check progress
```
cd D:\Shayan\imgsae
powershell -File scripts\run_phase1.ps1 -Status        # running? last log lines, GPU state
Get-Content logs\p1_encode_dev.log -Tail 5            # per-scan encode progress (n/150)
```
Finished when `logs\phase1.log` ends with `PHASE1 DONE` (memo: `docs\DECISION_MEMO_P1.md`) or a `STOP ...` line.
If the laptop crashes or restarts: run `powershell -File scripts\run_phase1.ps1` again; it resumes (finished scans and steps are kept).
Keep the charger in and the lid open while it runs.

## Where things are
| What | Path |
|---|---|
| Plan (final, unchanged) | `docs/IMAGING_SAE_LEAN_v1.md` |
| Protocol draft (Phase 2 registration) | `docs/PROTOCOL_lean_DRAFT.md` |
| Deviation / execution log (all changes, decisions, measurements) | `docs/EXECUTION_LOG.md` |
| How to run Phase 1 | `imgsae/RUNBOOK.md` |
| Code | `imgsae/` (venv `imgsae/.venv`, versions `imgsae/requirements-lock.txt`) |
| Data: 150 dev scans, verified | `imgsae_data/totalseg/` |
| Phase 1 results | `imgsae/data/p1/`, memo `docs/DECISION_MEMO_P1.md` |
| Mac-era logs | `imgsae/logs/mac_m5/` |
| Mac leftovers, safe to delete | `_trash/` |

## Phase 1 checklist (day plan D1–D7)
- [x] Plan, code, Mac logs reviewed; folders organised; subject lists verified (SHA256)
- [x] Code ported MPS → CUDA; analysis logic untouched
- [x] Environment: Python 3.11, torch 2.10 + CUDA 12.6; NVIDIA driver 621.14
- [x] D1 data: 150/150 dev scans, 17,700 files, CRC-verified
- [x] D1 unit tests 16/16; smoke test SMOKE OK
- [x] D1 equivalence test — skipped by user decision (Mac pass 10/10), logged
- [x] D2 gate E — PASS on 5 scans at 1.0 mm (tiles 192/48): ≤ 198 s/scan, 3.4 GB, parity 1.000, seam ≥ 0.991; projected 13.8 h → 1.0 mm
- [x] D2–D3 encode 150 scans + null encoder — done 2026-11-08 01:53 (~9.8 h)
- [x] D3 assemble, probes — **gate S FAIL** (32 gated ≥ 15 ok; 0 beyond-HU < 3)
- [x] D5–D6 perturbation re-encodes (20 scans × 3) — done
- [x] D4–D5 SAEs + baselines (J = 3), ladder, θ — done (151 min)
- [x] D7 decision memo — **NO-GO**

## Known issues
1. GPU power-sensor hardware fault (reads 752.67 W constantly) → GPU held at 210 MHz. Costs time only; results verified correct (GPU = CPU, cosine 1.000).
   Needs ASUS repair; not needed for Phase 1. Health check: `imgsae\.venv\Scripts\python imgsae\scripts\gpu_check.py`.
2. Laptop logged an unexpected shutdown (2026-11-06) and a GPU reset (2026-11-07). The run is resumable if it happens again.
3. `sae-groundtruth` not on this machine; re-run `tests\test_equivalence.py` if it is ever copied to `D:\Shayan\sae-groundtruth\`.
4. Exploratory post-hoc checks (chimera rule, position, esophagus): `imgsae/exploratory/p1_checks/README.md`. They do not change the verdict.
