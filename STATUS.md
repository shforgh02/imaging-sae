# Imaging SAE — status and handover

**Updated:** 2026-11-10 04:00 · **Phase:** v2, Stage 1a done (exploratory); earlier Phase 1 (7-day feasibility, `docs/IMAGING_SAE_LEAN_v1.md`) · **Machine:** ASUS Vivobook Pro 16X (M7600QE), RTX 3050 Ti 4 GB (CUDA)

**State in one line:** Phase 1 DONE (verdict **NO-GO**, memo `docs/DECISION_MEMO_P1.md`). Exploratory checks done (`imgsae/exploratory/p1_checks/README.md`): NO-GO stands.
**Now (2026-11-10):** **Stage 1a DONE, gate G1 PASSED, both post-G1 fixes done; waiting for the user's decision.** Protocol `docs/STAGE1A_PROTOCOL.md` (colleague review of plan v2, adopted with amendments; G1 fixed before running). Results `imgsae/exploratory/v2_ct/RESULTS_S1A.md`.
- G1-cal pass: the supervised reference (oracle) covers 21.7 of 32 concepts at C(0.7).
- G1-main pass: SAE consensus beats the best equally tuned baseline (k-means / ICA) by +0.22 / +0.30 / +0.24 (mean +0.25); it reaches 86–94% of the oracle.
- Flags: the physics-feature SAE comes close on organ concepts; no SAE advantage on vertebral level at k = 1.
- **Post-G1 checks done (2026-11-10, user: "do the two fixes"; sensitivity only, G1 stands; RESULTS_S1A.md checks 1–2, EXECUTION_LOG):**
  - Physics-feature SAE consensus 0.35 / 0.34 / 0.35; CT-FM consensus beats it by +0.18 / +0.25 / +0.19 (≥ 0.05 in every rep).
  - Nonnegative DL (deviation M7): 0.063 / 0.046 / 0.038, still far below k-means / ICA; G1-main unchanged. A label-free check shows the
    two halves' dictionaries agree but the OMP codes don't: the instability is in the coding step.
- Open: Q1 (keep "beyond physics" in the gates / headline?) and the freeze decision. Code `imgsae/exploratory/v2_ct/`; Modal task v2s1a_sae $6.06 of $7.
- **Next (review order, `docs/REVIEW_AND_PROPOSAL_v2.md` §4 "Order", step 2):** freeze the SAE and baseline configs, write the confirmation
  protocol `docs/SAE_PROTOCOL_v2.md` (H1 θ, H2 SAE vs best baseline, H3 consensus vs single, H5 k = 1 probing; J = 10 halves on the 555 sealed
  scans, Holm), then the user decides on registration (Zenodo). Only after registration: encode the 555 sealed scans and run once (step 3).
  Needs the user's decisions first: Q1, whether H5 stays confirmatory (dev data: no SAE advantage at k = 1), and the confirmation compute budget.
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
