# Imaging SAE — status and handover

**Updated:** 2026-11-08 20:00 · **Phase:** 1 (7-day feasibility, `docs/IMAGING_SAE_LEAN_v1.md`) · **Machine:** ASUS Vivobook Pro 16X (M7600QE), RTX 3050 Ti 4 GB (CUDA)

**State in one line:** Phase 1 DONE (verdict **NO-GO**, memo `docs/DECISION_MEMO_P1.md`). Exploratory checks done (`imgsae/exploratory/p1_checks/README.md`): NO-GO stands.
**Now:** Phase 1b sanity-check pivot, Stage A **DONE** 2026-11-09 14:00 (exploratory, dev data; `imgsae/exploratory/p1b_sanity/RESULTS.md`).
- Rules: R-sat false (CT-FM ≈ physics on organs, but untrained 0.960 < 0.97); R-fm true (vertebra level, few labels); R-sae does not hold (trained SAE beats clustering).
- **Waiting for the user's framing decision** before Stage B.
- Modal GPU in use under a $29 hard budget: `p1b_sanity/cloud/README.md`, ledger `cloud/ledger.json`.

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
