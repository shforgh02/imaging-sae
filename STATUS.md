# Imaging SAE — status and handover

**Updated:** 2026-11-16 · **Phase:** Lung L2 S5 frozen (commit `c593005`); stopped for the external reviewer and the lead's OK. S3 is complete: all 7,336 dev exams + 998 z-fix + 500 kernel-pair series, 0 failures, S3 gate passed. · **Machine:** ASUS Vivobook Pro 16X (M7600QE), RTX 3050 Ti 4 GB (CUDA; capped at 210 MHz by a power setting on 16 Nov)

**Latest (2026-11-16, evening):** the S5 review is done: `docs/REVIEW_S5_L2.md`, verdict **approve with changes** (H1 to H4 approved; H5 not approved as frozen; proposal H5′). The whole project in simple words and the step-by-step plan from here are in **`docs/PROJECT_GUIDE.md`** (read its parts 7 to 9 before any work). **N0 done (lead, 16 Nov): H5 → H5′, new freeze OK, S6 in December OK.** **Next: the executor (Opus 5.5, xhigh) with `docs/HANDOVER_PROMPT_L2_N1.md`: step NF (more feature work on dev, amendment A6, free, until 26 Nov) and step N1 (the new freeze), then stop for the re-check and the lead's OK.** The test split is still closed.

**Now (2026-11-16, execution of `docs/PLAN_L2_NEXT_v1.md` by Opus 5.5):**
- Step 0 and P1 to P3 done. P1: the guard knows two accounts (per-account caps, $17 limit for this project on `armanfo`, atomic ledger, no-log status, app check). P2: smoke and identity on `armanfo` equal to the main account (max difference 0.0). P3: D2, D3, D4 on `armanfo` (one Modal preemption stopped the first driver by its 80-minute rule; restarted; no data lost); merged into `imgsae_data/lung_l2_vol/l2` (no overwrite); `results/s3_checks_all.json`.
- P4a done: S4 code fixed at commit `a536192` before any full-dev run (synthetic test 50/50; a pandas-3 bug that dropped scanner maker and model was found and fixed).
- P4b done: `imgsae/exploratory/lung_l2/RESULTS_S4_dev.md`. Check P1 passed; raw units is the only valid arm (the SAE fails V1 and V3); z-fix moves Sybil's score clearly, the kernel hardly; U1a and U3 fail gate 9.8; gate 9.8 holds → S5. K = 128 check finished (dev only): raw units again the only valid arm (the SAE fails V1 and V4 there).
- **P5 done, STOPPED for the lead's OK:** `imgsae/exploratory/lung_l2/HYPOTHESES_L2.md` (5 hypotheses: H1 to H3 z-fix, H4 kernel flag robustness, H5 technical-named features; Holm), frozen files `lung_l2/results/s5/`, frozen analysis `lung_l2/s6_frozen_analysis.py` (dev as if test reproduces S4 exactly). Final freeze commit `c593005`. Next: the external reviewer (`docs/REVIEWER_BRIEF_L2.md`), then the lead's OK, then P6 (test, December, main account).
- Money (billing reconciled): task `lung_l2_audit` $21.70 of $45; project $47.09 of $72; `armanfo` this project $14.03 of $17.00 (month $15.69 of $29.50); `shforghani2002` $28.17 of $29.00. S3 total $19.75 of $22.00. No open run. No cloud volume deleted.
- Next: the external reviewer's note → the lead's OK on `HYPOTHESES_L2.md` → P6 (test, December, `shforghani2002`). Test data stay closed.

**Next (2026-11-15):** plan `docs/PLAN_L2_NEXT_v1.md` is reviewed by Fable 5.2: approve with edits (`docs/REVIEW_PLAN_L2_NEXT_v1.md`, 15 edits, 3 questions for the lead with defaults). It waits for the lead's OK; then a fresh Opus 5.5 session executes P1 to P5 with the prompt `docs/HANDOVER_PROMPT_L2_EXEC.md` (version 2; pasting it gives the OK). The lead decided to use account `armanfo` (cap $29.50) for S3 D2 to D4 now, under proposed amendment A4.

**Progress report for the lead (2026-11-15):** `docs/PROGRESS_REPORT_L2_2026-11-15.md` (steps, findings so far, money, why we wait, plan, decisions needed). The December task `imgsae_l2_dec` is not created yet (checked 2026-11-15).

**Now (2026-11-15):** spend task $7.67 of $45 (Modal billing reconciled; preemption restarts are billed); month $28.17 of $29. December driver ready (`imgsae/exploratory/lung_l2/cloud/run_dec.cmd`); its scheduled task is created by the lead with `schedule_dec.ps1` (the permission system blocked me from creating unattended future spending). Next: D2 + D3 + D4 (≈ $14.5) from 1 December, then S4 on the PC.

**Now (2026-11-13, S2):** protocol approved; S1 dev manifest done (7,336 exams); pilot of 300 dev series done ($1.96 spent of $45; month $22.54 of $29). All recomputation and determinism checks passed. G2e (air HU check) and G2f (z-stretch check) failed as written; diagnosis in `docs/EXECUTION_LOG.md` and `imgsae/exploratory/lung_l2/results/s2_diagnose.json`. The z-stretch is real and cuts the lungs in 26 of 27 series at 2× stretch; correcting it moves Sybil's logit by about half the between-exam spread. Next: the lead's decision on the two checks, then D1 in November as the monthly budget allows.

**Now (2026-11-13, S0 done): protocol `docs/LUNG_L2_PROTOCOL.md` written; stopped for the lead's OK (Part A).**
- Series rule for dev exams built from metadata only: reproduces the split file's test series in 98.7% of exams (gate 90% passed); dev 7,336 exams.
- New technical point: Sybil places slices at the slice thickness, not the true spacing; 44% of series are stretched along z (up to 2×). Added as a cheap `zfix` sub-study, to be confirmed in the pilot.
- Literature: *Auditing Sybil* (synthetic nodules, LUNA25) and Simon 2025 (kernel pairs, AUROC only) overlap partly; nobody has decomposed Sybil against real outcomes, the form and technical factors. No second screening dataset is fully open (Duke DLCS restricted; P-ELCAP by request).
- Budget: `project_cap_usd` 72 and task `lung_l2_audit` $45 added (approved); month usage $21.07 of $29. Nothing spent in S0.
- Next after the lead's OK: S1 dev manifest, S2 pilot (≈ $1.2), S3 dev extraction (≈ $20), S4 analysis.

**Before (2026-11-13): restart proposed as a feature-level audit of Sybil ("Lung L2").** Plan: `docs/PLAN_SYBIL_AUDIT_v1.md`. Hand-over prompt for the executing session: `docs/HANDOVER_PROMPT_SYBIL_AUDIT.md`.
- **Lead's direction (2026-11-13):** no two-cancer paper. In this project, open the model: why it is right, why it is wrong, and whether its features can be used.
- **Next step:** S0 of the plan (free): read the competing audit, write `docs/LUNG_L2_PROTOCOL.md`, stop for the lead's OK. Nothing is approved to spend until the lead gives the budget.
- **Why Sybil:** same accuracy as the radiologist's form, but the form explains only 15% to 19% of Sybil's score; the score is stable within a person (r = 0.61 one year apart); the two make mostly different false alarms. Exploratory numbers, in `imgsae/exploratory/lung_l1/posthoc/`.
- **Rule from now on:** no test activation and no new outcome analysis of the existing test scores before the hypotheses are frozen.
- **Budget facts (before the S0 change):** the guard's all-time project check had $3.61 left ($25.39 of $29 used). Modal's monthly usage on account `shforghani2002` was $21.12. No open runs.

**Before (2026-11-12): lung re-checked at no cost, then the paired test L1.** Results in `imgsae/exploratory/lung_l0/RESULTS_L0.md` and `imgsae/exploratory/lung_l1/RESULTS_L1.md`.
- **Sybil's split is published** (branch `train` of its repository), so lung was not blocked as the feasibility scan said.
- **No gap over the doctor in lung (L0, unpaired).** On Sybil's test participants, a logistic regression on the NLST radiologists' recorded findings scores 0.93 for cancer within one year and 0.75 within six years. Sybil's published figures are 0.93 and 0.75.
- **Clean lung test data:** Sybil's test split only (2,347 participants, 154 with cancer). The 11,432 CT-arm participants outside Sybil's splits hold 34 cancers.
- **Lung L1 done (paired test, approved by the lead with a $15 cap, run by a lower-cost agent).**
  - Scored: all 2,279 baseline series and 3,133 of 4,436 follow-up series of Sybil's test split. All gates passed.
  - One year, baseline: Sybil 0.927, recorded findings 0.929, difference −0.003 [−0.063, +0.058].
  - Six years, baseline: Sybil 0.724, recorded findings 0.745, difference −0.021 [−0.073, +0.034].
  - Verdict by the fixed rules: no evidence that Sybil carries information beyond the recorded findings. The findings add to Sybil at 2 and 6 years. A small gain from Sybil at one year is not excluded (+0.026, lower bound −0.004).
- **Spend:** lung L1 $12.53 of its $15 cap. The L1 volume is deleted.
**Before (2026-11-11): PAUSED by the lead's decision.** The plain-language summary is `docs/PAUSE_NOTE_2026-11-11.md`.
- **The lead's own cancer model** (SegResNet, trained on PI-CAI folds 0-2) on held-out folds 3 + 4, 357 biopsied PI-RADS ≥ 3 men:
  - +0.022 AUROC over PI-RADS + PSAD + age (p 0.0002);
  - +0.021 after the lesion's ADC, DWI and size;
  - unstable between folds.
  - On UCLA (the lead's earlier work) such PI-CAI models fall to about 0.66, below radiologists.
  - Too small to justify training a model for SAE discovery.
- **Feasibility scan** (`docs/FEASIBILITY_SCAN_breast_lung.md`):
  - lung (Sybil/NLST) blocked: unpublished training split; weak beyond-nodule signal;
  - breast (Mirai/EMBED) is the best fit, pending whether the lead's institution can sign the EMBED data agreement.
- **Kept:** all code (tested); the verified PI-CAI copy with its sealed half unopened; the 555 sealed CT scans unused.
- **Spend:** Modal total $12.86 (CT 7.74, MRI 5.12). No open runs.

**Before (2026-11-10):** **Prostate MRI M1 gate FAILED; stopped per the protocol.** Results in
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
