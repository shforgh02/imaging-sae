# Execution and deviation log (lean plan v1)

Every deviation from `IMAGING_SAE_LEAN_v1.md` or from the code as delivered goes here, with date and reason.
Rule (protocol §5): only metric-blind changes are allowed without a plan decision. Nothing below changes a threshold, rule, metric or method.

## 2026-11-06 — Phase 1 moved from the Apple M5 to the Windows laptop

### Machine
| | Plan (Mac) | This laptop |
|---|---|---|
| CPU | Apple M5, 4P+6E | AMD Ryzen 9 5900HX, 8 cores / 16 threads |
| GPU | 10-core M5 GPU, MPS, 24 GB unified memory | NVIDIA RTX 3050 Laptop, CUDA 12.7 driver 566.07, **4 GB VRAM** |
| RAM | 24 GB (shared with GPU) | 31 GB (separate from GPU) |
| Disk | 205 GB free | D: 144 GB free (project + data on D:) |
| Python | miniforge 3.11, torch 2.10 (MPS) | uv venv, CPython 3.11.15, torch 2.10 + CUDA 12.6 wheels |

Main consequence: GPU memory is 4 GB, not up to ~12 GB. The encoder runs in 160³ tiles, so memory depends on the tile, not the scan size;
gate E measures it. On Windows, going over VRAM does not crash, it pages into shared RAM (slow), so the encode logs a `SPILL` warning.

### State inherited from the Mac (logs in `imgsae/logs/mac_m5/`)
- Done: venv, CT-FM weights check, subject selection (705 eligible → 150 dev / 555 confirmation, hashes in `imgsae/data/SHA256SUMS`, re-verified here: OK),
  zip index, kernel tests (10/10 equivalence, 16/16 units), CPU smoke test of the whole chain (SMOKE OK).
- Not done: the data fetch stopped at 5,000 / 17,700 files and those files were not transferred. No real scan had been encoded. No gate had run on real data.

### Changes (all engineering; no analysis logic touched)
1. **Folder layout.** The zip nested `imgsae/imgsae/`; flattened to `D:\Shayan\imgsae\` (code) with data in `D:\Shayan\imgsae_data\` (same sibling layout as on the Mac,
   so no data path changed). Plan docs moved to `D:\Shayan\docs\`. Mac artefacts (`__MACOSX`, `.DS_Store`, Mac `.venv`, duplicate runbook) moved to `D:\Shayan\_trash\` (safe to delete).
2. **Device handling.** New `imgsae/accel.py` (pick cuda > mps > cpu; cache clearing; peak memory). Scripts default to `--device auto`.
   Edited: `encoders/ctfm.py` (default device, cache clear), `scripts/p1_d2_engineering.py`, `scripts/p1_encode.py`, `scripts/p1_fit.py`, `tests/test_units.py`.
   **Unchanged:** `sae.py`, `consensus.py`, `ladder.py`, `stats.py`, `atlas.py`, `tokens.py`, `synth_omics.py`, and all thresholds.
3. **Gate E measurement.** Same rules (≤ 300 s/scan, ≤ 12 GB, parity cosine ≥ 0.995, seam cosine ≥ 0.95). Memory is now CUDA peak reserved memory
   (was MPS driver-allocated memory). JSON keys renamed `mps_seconds → gpu_seconds`, `mps_driver_gb → gpu_peak_gb`, `parity_cos_mps16_vs_cpu32 → parity_cos_gpu16_vs_cpu32`;
   `mean_seconds` and `gate_E_partial` (read by the driver and the memo) unchanged. Added informational fields: device name, VRAM, spill flag.
4. **Footprint watchdog** (encode): still aborts above 12 GB as in the plan; additionally prints `SPILL` if the peak exceeds physical VRAM.
5. **Unit test** "MPS vs CPU L0 within 1%" now runs on whatever accelerator exists ("CUDA vs CPU L0 within 1%"), same tolerance.
6. **Runner.** Mac `prun` (launchd) + `macperf` replaced by `scripts/run_phase1.ps1`: refuses to start if another compute process uses the GPU,
   4 threads (OMP/MKL), detached, log `logs/phase1.log`, `-Status` mode. The driver uses its own interpreter (`sys.executable`), forces UTF-8 logs,
   and blocks Windows sleep while it runs.
7. **Decision memo path** default: `D:\Shayan\docs\DECISION_MEMO_P1.md` (was a Mac path).
8. **Fetch parallelism** 6 → 24 connections for the manual fetch (download is latency-bound: 17,700 small files at ~0.2 MB/s with 6). Same files, same CRC check.
   The driver's own fetch step still uses 6 and will only re-verify CRCs.
9. **Smoke test**: explicit UTF-8 when writing the phantom `meta.csv` (Windows default encoding cannot write its BOM).

10. **Smoke-test phantoms** (`scripts/smoke_phase1.py`, test code only — not a plan gate): masks mutually exclusive, structure centres spread ×1.2
    (was ×0.8) and radii r = 13 + 2·(j mod 5) (was 7 + 2·(j mod 5)).
    Reason: with the delivered phantoms the smoke failed here: 5–6 of 12 scans fell below the 20-structure QC and no group had core tokens in ≥ 10 scans,
    so `p1_probe` crashed (one class) and fit/decide had no inputs. The Mac log (12 scans, 4 eligible groups) most likely predates the current
    `tokens.label_volume` (single label map, later leaf wins); the old per-mask `tokens.load_mask` is still in the file, unused. Could not be proven:
    file timestamps were reset by the transfer. Geometry chosen by a small search (min 21 structures per scan, 3 eligible groups).
    Checked on real data: TotalSegmentator masks overlap by only ~3,000 voxels per scan (s0006: 55 non-empty masks → 54 in the label map; s0015: 83 → 83),
    so the merge rule behaves as documented ("on rare overlaps the later leaf wins"). Not changed.

### Progress
- Environment: torch 2.10.0+cu126 sees the RTX 3050 Ti Laptop GPU (4.29 GB). Exact package versions in `imgsae/requirements-lock.txt`.
- Data: 150/150 dev scans, 17,700 files, 3.67 GB, all CRC32-verified, 53 min at ~1.1 MB/s (24 connections). Each scan has 117 mask files.
- Unit tests here: 16/16 pass, identical values to the Mac run, incl. "CUDA vs CPU L0 within 1%" (4.000 vs 4.000).
- CT-FM weights: HF snapshot 527b0d1c… (same revision as the Mac).
- Smoke test (CPU, phantoms): SMOKE OK — 12 scans, 0 excluded, 3 eligible groups, every step DONE, verdict NO-GO (expected on phantoms; Mac also NO-GO).

### Gate E, first attempt (2026-11-07, 2 scans at 1.0 mm, rule of `run_phase1.py`) — not accepted, machine was power-capped
| scan | shape @1 mm | windows | GPU s | GPU peak GB (encode) | parity | seam |
|---|---|---|---|---|---|---|
| s0006 | 326×324×324 | 64 | 85 | 1.68 | 1.000 | 0.981 |
| s0015 | 516×440×440 | 252 | 335 | 1.53 | 1.000 | 0.977 |
- Mean 210 s → projected 22.8 h > 16 h, and s0015 > 300 s → the rule would pick 1.5 mm.
- Memory: the production tiling (160³) needs ~1.7 GB, fits the 4 GB card. Only the seam check's 224³ tiles exceed VRAM (5.3 GB, spill) — check only, not production.
- **Cause found:** the GPU ran pinned at 210 MHz of 2,100 MHz (`sw_power_cap` active, 56 °C, on AC). Windows power mode overlay = "Best power efficiency"
  (961cc777-…). A repeat of s0015 took 501 s. These timings reflect the power setting, not the hardware. Gate E will be re-run after the power mode is fixed;
  this attempt is kept here for the record and its JSON was overwritten by the re-run.
- Launcher fix: on Windows `nvidia-smi` lists every desktop app as a GPU process; "another GPU job" now means python/julia/matlab/R/ollama/java only.

- Follow-up (user approved): Windows power mode on AC set to "Best performance" (`powercfg /overlaysetactive ded574b5-…`; battery mode unchanged);
  user confirmed the 120 W charger and ASUS "Performance" fan mode. GPU still pinned at 210 MHz under load (1.13 s per 160³ window).
- **Root cause:** the GPU power sensor reads a constant **752.67 W** (enforced limit 50 W, default 35 W), already at idle at the session start. The driver
  therefore applies `sw_power_cap` and holds the minimum clock. Driver 566.07, VBIOS 94.07.3b.40.63, ASUS Vivobook Pro 16X M7600QE.
  Fix needs the user: reboot, then if still 752 W, a clean install of the current NVIDIA driver (CUDA 12.6 torch wheels work with newer drivers).
- Decision: Phase 1 is NOT launched in this state. The spacing rule (1.0 vs 1.5 mm) is decided once by gate E and written to `data/p1/spacing.json`;
  measuring it on a GPU running at ~10 % clock would lock in 1.5 mm because of a sensor fault, not the hardware.

### GPU diagnosis (2026-11-07, after reboot + clean install of driver 621.14)
- Still `SW Power Cap: Active`, P8, SM 210 MHz / memory 405 MHz; power reading **752.67 W — identical to the value under driver 566.07**, across 2 reboots.
  Power-cap counter 20.3 min of 25 min uptime. Limits: current 50 W, default 35 W, min 1 W. No thermal or HW slowdown (42 °C).
- Ruled out: driver version (new driver, same value), Windows power mode, fan mode, charger/platform power — the **CPU boosts normally**
  (126 % processor performance ≈ 4.2 GHz under 8-thread load), so the laptop receives full power; only the GPU is limited.
- Present and OK: NVIDIA Platform Controllers and Framework, ASUS System Control Interface v3, ASUS services. BIOS M7600QE.312, VBIOS 94.07.3b.40.63, PCIe x8.
- Event log: Kernel-Power 41 (unclean shutdown / power loss) on 2026-11-06 21:57, just before this session; nvlddmkm 153 (GPU reset) on 2026-11-07 01:05.
- Conclusion: a stuck power-sensor reading below the driver (board power monitor or ASUS embedded controller), not software. A normal restart does
  not reset the embedded controller (it stays powered from the battery). Next test: EC hard reset (shut down, unplug charger, hold power 40 s).
  If unchanged: hardware/firmware fault → ASUS BIOS update or ASUS service; Phase 1 can run meanwhile at reduced GPU speed (see below).
- `nvidia-smi -lgc` clock lock could not be tried (needs an administrator shell).

### Workaround test (admin, `scripts/gpu_unlock_test.ps1`, log `imgsae/logs/gpu_unlock_test.log`) — nothing helped, system restored
| state | s per 160³ window | power reading | limit |
|---|---|---|---|
| baseline | 1.052 | 752.67 W | 50 W |
| clock lock `nvidia-smi -lgc 1200,2100` | 1.055 | 752.67 W | 50 W |
| NVPCF (`ACPI\NVDA0820\NPCF`) disabled | 1.053 | 752.67 W | **35 W** |
| both | 1.053 | 752.67 W | 35 W |
Disabling the ASUS↔NVIDIA power bridge did change the limit (50 → 35 W), yet the reading stayed 752.67 W: the bad value comes from the GPU's own
board power sensor, not from ASUS software. Not fixable in software; needs ASUS repair. GPU results themselves are correct (parity cosine 1.000).

### Decisions by the user (2026-11-07)
1. **Equivalence test skipped on this machine.** Accepted evidence: Mac run 2026-11-06, 10/10 PASS (`imgsae/logs/mac_m5/test_equivalence.log`); the port did not
   modify `sae.py`, `consensus.py`, `ladder.py` or `stats.py`; the test compares old vs new code on the same machine, so platform does not enter.
   Residual risk: an edit to those files on the Mac after that test would go unnoticed. Re-run the test if `sae-groundtruth/` becomes available.
2. **Production tiling 192/48 (was 160/48)** for all encodes (dev and perturbation). Benchmark s0006 @1.0 mm (`logs/tile_bench_s0006.json`):
   160 → 68 s, 1.68 GB; 192 → 48 s, 3.38 GB, cosine vs 160 = 0.990; 208 → 62 s, 4.24 GB (at VRAM limit). Same 48-voxel border margin.
   Gate E now times the production tiling and checks seams as 192/48 vs 224/64 (key renamed `seam_cos_tiling_vs_224`).
3. **Spacing 1.0 mm (16 mm tokens), precision over speed** — the user's instruction was to keep 1.0 mm even if slow. In the end no override was needed:
   with 192 tiles the plan's own rule selects 1.0 mm (see gate E below). Note: all 150 dev scans are stored at 1.5 mm isotropic, so 1.0 mm is
   linear upsampling — it gives a finer token grid (16 vs 24 mm), not new image detail.
4. **Gate E time-waiver mechanism** added to `p1_decide.py` (field `gate_E_time_waived` in `spacing.json`; if true, E judged on memory, parity and seam
   only, waiver printed in the memo). **Not used:** `gate_E_time_waived = false`, the gate passed on all criteria.

### Gate E, final (2026-11-07, 5 scans at 1.0 mm, production tiling 192/48, GPU still power-capped) — PASS
| scan | shape @1 mm | tiles | GPU s | peak GB | parity | seam (192/48 vs 224/64) |
|---|---|---|---|---|---|---|
| s0006 | 326×324×324 | 27 | 48 | 2.63 | 1.000 | 0.9945 |
| s0015 | 516×440×440 | 80 | 142 | 3.38 | 1.000 | 0.9942 |
| s0024 | 729×430×430 | 112 | 198 | 3.38 | 1.000 | 0.9909 |
| s0038 | 500×360×360 | 45 | 80 | 3.38 | 1.000 | 0.9956 |
| s0040 | 632×436×436 | 96 | 170 | 3.38 | 1.000 | 0.9938 |
- All ≤ 300 s, ≤ 12 GB, parity ≥ 0.995, seam ≥ 0.95 → `gate_E_partial = true`. Mean 127.5 s → projected 150 × 2 × 127.5 × 1.3 = **13.8 h ≤ 16 h → rule: 1.0 mm**.
- Profiled on 5 scans (the driver's own first probe uses 2); marker `data/p1/steps/eng10.done` written so the driver does not repeat it.
  `data/p1/spacing.json` written with the same fields the driver writes, plus provenance.
- The 224/64 comparison tiling spilled VRAM on s0006 (check only; not production).

### Open items
- GPU power-sensor fault (above): reboot / update NVIDIA driver, then re-test with `imgsae\scripts\gpu_check.py`:
  expect clocks well above 210 MHz under load and power.draw ≤ 50 W.
- `tests/test_equivalence.py` needs the frozen reference package `sae-groundtruth/` (with `saegt/`) next to `imgsae/`, i.e. `D:\Shayan\sae-groundtruth\`.
  It was not in the transferred folder. The driver stops with `STOP tests` until it is present (decision pending with the user).

### Phase 1 run (launched 2026-11-07 16:02, pid 5232)
- Encode 150/150 dev scans (CT-FM + random-init null) done 2026-11-08 01:53: ~9.8 h, no SPILL/ABORT. Gate E 24 h wall-time criterion met.
- Assemble 2.9 min: 1,021,303 token rows, 150 scans, 0 excluded, 33 eligible concept groups.
- Probe 13.6 min (60,000-token subsample, patient-grouped 5-fold CV) -> **gate S FAIL: 32 gated concepts (need >= 15, met), 0 beyond-HU (need >= 3, not met).**
  - Reference (HU histogram + texture + 3x3x3 context + position) already reaches AUROC >= 0.98 for most organs, so a dAUROC >= 0.05 margin is
    rarely possible. Closest: iliac_vessels +0.040 (CI 0.030-0.048), urinary_bladder +0.017 (CI lower < 0).
  - Anomaly to check: esophagus dense AUROC 0.30 (ref 0.99) — below chance; not gated, so it does not change the gate count.
  - Scan level (not part of gate S): manufacturer Siemens dense 0.77 vs ref 0.52 (acquisition shortcut signal); tumour dense 0.53 vs ref 0.70.
  - Per the pre-written table (plan L102) S fail => **NO-GO**. Driver continues (perturbations, fits) because `p1_decide.py` needs the fit
    summaries to write the memo; no change made to the plan or thresholds.
- Perturbation encodes: shift 94 min, noise 94 min, huoff ~44 min (20/20 each). Fits 151 min (GPU). Decide 0.1 min. **PHASE1 DONE 2026-11-08 09:23.**
- **Verdict (pre-written table): NO-GO.** E pass (9.8 h); S FAIL; D1 no (strongest baseline soft_kmeans area 0.046; sae_cons gain -0.046,
  sae_single -0.038); D2 no (consensus R1 0.56 < 0.60; theta 0.50, CI 0.24-0.76); D3 no (shortcut share 0.01); degeneracy check FAILED
  (only soft_kmeans has C(0.7) > 0). Memo: `docs/DECISION_MEMO_P1.md`; numbers: `imgsae/data/p1/decision.json`, `imgsae/logs/p1_fit.log`.
- Observation (not acted on): validated coverage is ~0 for every method, and single-fit SAE R1 is 0.04-0.07 — to be checked for a pipeline
  cause before the result is taken at face value.
- Observation (not acted on): the reference "position" features use the vertebral level computed from the ground-truth vertebra masks
  (`tokens.position_features`), so the reference gets label-derived information CT-FM does not. The plan says only "position". This makes
  gate S's beyond-HU criterion harder to pass. Exploratory re-probe with label-free position proposed to the user; not run.

### Exploratory checks after the memo (user-requested, 2026-11-08) — `imgsae/exploratory/p1_checks/README.md`
Post hoc; the verdict, plan, main code and main results are unchanged. Each check reproduces the run's numbers exactly first.
- Chimera rule counts 'other' (45% of tokens) as a foreign concept -> 79-100% of features rejected for every method (the cause of the
  degeneracy). 'other' neutral: soft_kmeans 0.273, raw_sparse 0.217, sparse_varimax 0.095, sae_single 0.066, sae_cons 0.000 -> D1 still no.
- Consensus SAE features (34-38) are reproducible and stable but none organ-selective (median sel 0.31).
- Gate S: removing the label-derived z position changes nothing (0 beyond-HU); removing all position gives 4 beyond-HU. Correction to my
  earlier statement: the label leak is real but does not decide gate S.
- Esophagus 0.30 = 3 tokens / 2 patients in the probe sample (noise). 11/33 concepts have <= 15 sample tokens.

## 2026-11-09 — Phase 1b: sanity-check pivot (plan `docs/SANITY_PLAN_v1.md`, approved by the user)
New question (prompted by an external suggestion to "flip the paper"): do CT-FM and SAEs beat simple physical and clustering baselines?
The Phase 1 verdict (NO-GO for the SAE paper) is unchanged. Stage A is exploratory on the 150 dev scans; code in `imgsae/exploratory/p1b_sanity/`;
production code and results untouched. Reading rules (R-sat, R-fm, R-sae) fixed in the plan before any Stage A result. Stop after Stage A for a
framing decision; held-out confirmation (Stage C) only with a frozen protocol.
Known confounds to remove before any claim (found while planning, from `fit/summary.json` and `gates.json`):
- organ probe is at ceiling: median AUROC CT-FM 0.998, reference 0.998, on clean tokens only (partial tokens, label -2, not scored);
- sparse baselines ran at L0 = 6 (consensus L0), single SAE at L0 = 27; feature counts 35 (consensus) to 1,024 (raw sparse, sparse varimax);
- SAE is undercomplete (M = 425 < d = 512), 3,000 steps;
- the 'other'-neutral chimera numbers are post hoc and rep 0 only.

Progress (2026-11-09):
- A0 novelty check done (`p1b_sanity/NOVELTY.md`): Wesp et al. (MICCAI 2026) = 2D slices, LLM-judged features, no simple baselines in the abstract.
- A1 and the A2 smoke test ran in parallel. Claude Code stopped both for low system memory (about 25 GB in use with other apps open). All 197 A1 probe
  predictions were already cached; only A1's bootstrap step was lost. Memory use cut: feature matrices are loaded only when needed, unused
  perturbation inputs are dropped, and A3 holds one input at a time. Restarted on the user's instruction as one job at a time
  (`p1b_sanity/run_stageA.ps1`, log `p1b_sanity/logs/stageA.log`).
- T3_rib not estimable (only rib 1 has >= 10 patients at >= 50% occupancy in 16 mm tokens) -> skipped per the plan's class rule, not redefined.
- A3 smoke (rep 0) reproduces the run: soft k-means L0 6 area 0.042 (as run), 0.273 ('other' neutral), R1 0.32. At L0 27 soft k-means falls to
  0.082 'neutral' (single SAE at L0 27: 0.066), so the L0 mismatch drove much of the gap.
- Runner stopped by Claude Code for low memory a second time, during A2 config 5 (M 2048). A1 complete, A2 4 of 8 configs saved. About 17 GB
  of the 33.4 GB commit limit (31.4 GB RAM + about 2 GB page file) is used by other software when nothing of ours runs. A2/A3 perturbation codes
  are now encoded per kind on access (`common.LazyPert`; same values).
- Interim, A1 complete (`p1b_sanity/RESULTS.md`; sanity T1a = gates.json exactly):
  - organ identity is saturated for CT-FM vs physics (T1b median 0.999 vs 0.997 R4; no concept with Δ >= 0.05), but not for the untrained
    CT-FM (0.960). So R-sat as written is false.
  - R-fm true: vertebra level — CT-FM 0.982 vs label-free 0.930 vs untrained 0.874, 13/24 levels Δ >= 0.05. Few labels: vertebra n = 3
    0.815 vs 0.704; lobes n = 3 0.921 vs 0.820. Left/right without coordinates: CT-FM 0.999 vs physics without position 0.51.
  - untrained CT-FM + R3 adds nothing over R3.
- Interim, A2 4/8: the run config reproduces the run (R1 0.042, area 0.007 / 0.066). Held-out R² 0.80, 0 dead latents. Seed R1 within a half 0.056
  ≈ between halves 0.042 (seed noise, not data). At L0 6 with 425 features, the SAE area 'neutral' is 0.328, above soft k-means 0.273 at the same L0 and count.
- Restarted 09:41 on the user's instruction (runner skips finished steps). A2 single configs 8/8 done, rep 0 (area 'orig' / 'neutral' / 'neutral' matched to 425 features):
  M2048 k27 3k 0.052 / 0.274 / 0.102; M2048 k6 3k 0.260 / 0.512 / 0.283 (dead 0.24); M1024 k27 12k 0.198 / 0.448 / 0.311;
  M1024 k6 12k 0.292 / 0.561 / 0.432 (C07 21 / 19 of 32; held-out R² 0.71; dead 0.01) = best single. Longer training helps at both k
  (k6 0.462 -> 0.561, k27 0.139 -> 0.448 'neutral'). R1 stays low (0.20; within half 0.24), so features still depend on the seed.
  Caveat: the SAE was tuned over 8 configs on rep 0; soft k-means only at M 425. A3 reps 1-2 reduce the selection bias, not remove it.
  5-fit consensus at the best config started about 11:20 (about 2 h on the local GPU).
- Modal (modal.com) checked 11:30: CLI 1.5.5 in miniconda, logged in (active workspace shforghani2002, no apps). Not used yet; any paid GPU run needs the user's go.
- Modal approved by the user 11:35 with a budget rule: free credit $30/month, hard stop at $29 for the whole project, a budget per task.
  Guard `p1b_sanity/cloud/budget.py` (task, project and month checks before every launch; worst case = containers x (timeout + 3 min) x rate;
  Modal timeouts make it a hard bound), ledger `cloud/ledger.json` (a3_sae $3, stageC_encode $10, stageC_fit $4, stageD_dinov3 $6, reserve $6).
  A3 --part sae moved to Modal L4 (`cloud/a3_sae_modal.py`; same code via new `a3_decomp_fair.load_input` / `fit_eval`, a refactor with no change
  in maths); `logs/a3_sae.done` makes the local runner skip it. Inputs uploaded to volume imgsae-p1b (about 3 GB). First a 1-job test
  (sae_run rep 0, worst case $0.34) that must reproduce the run config; then the rest.
- A3 --part sae done on Modal (12/12 jobs, 3 launches; ledger estimate $1.68 of the $3 task budget, Modal billing $0.73 at 13:12, which lags).
  Sanity vs fit/summary.json: sae_run rep 1 exact (R1 0.052, area 0.007); reps 0 / 2 within seed noise (R1 0.038 / 0.064 vs 0.042 / 0.066;
  area 0.009 / 0.005 vs 0.007 / 0.009); consensus area 0 in all reps (as run). Not bit-exact because of a different GPU (L4 vs RTX 3050 Ti).
  Areas, reps 0-2 (orig / neutral / neutral at 425 features): sae_run 0.005-0.009 / 0.061-0.064; sae_cons_run 0 / 0.002-0.014;
  best k 6 (M1024, 12k steps) 0.26-0.28 / 0.52-0.55 / 0.39-0.40, C07 17-21; best k 27 (M1024, 12k) 0.11-0.17 / 0.40 / 0.28.
  Volume imgsae-p1b kept for Stage C (about $0.25/month).
- STAGE A DONE 14:00 (runner: A2 215 min, A3 cpu 42 min, a4). All local sanity rows exact (A1 T1a = gates.json; A2 run config; A3 km / raw / svx
  at L0 6, reps 0-2 = fit/summary.json, rep 0 'neutral' = c1b). Read-out (`p1b_sanity/RESULTS.md`):
  - R-sat false as written (untrained CT-FM 0.960 < 0.97); the CT-FM vs physics part is saturated (T1b Δ(ctfm - R3) 0.003, 0/33 concepts >= 0.05).
  - R-fm true: vertebra level (13/24 levels), few-label vertebra (n 3/10/30: 0.67/0.62/0.58 of levels) and lobes (n 3: 0.60).
  - R-sae does not hold: at matched L0 and 425 features the best SAE beats the best simple baseline in every rep under both rules
    (L0 6 'neutral' 0.39-0.40 vs 0.25-0.27; 'orig' 0.18-0.19 vs 0.04-0.05; L0 27 'neutral' 0.28 vs 0.11-0.12).
  - Consensus at the best config (rep 0): R1 0.51 (single 0.20), area 0.269 / 0.562.
  Caveats: SAE tuned over 8 configs on rep 0, k-means at M 425 only; no SAE on untrained CT-FM or R3 at the best config yet (needed to tell
  'the FM helps' from 'the SAE method helps' on this ladder); 'neutral' rule post hoc; all on dev scans seen many times.
  Stopped for the user's framing decision (plan).

## 2026-11-09 evening: colleague review of plan v2 adopted as Stage 1a (exploratory, dev data)
- Review received via the user: `docs/REVIEW_AND_PROPOSAL_v2.md` (desk review; nothing re-run). Every number was checked against
  `p1b_sanity/results/{a2_sae_audit,a3_cpu,a3_sae}.json`; all are correct except one. The as-run area at 425 features is 0.18-0.19, not 0.26-0.28
  (that is the 1,024-feature area). Missing from the review: the SAE has the lowest per-feature twin score of all methods (0.47 vs k-means 0.63,
  sparse varimax 0.93, raw 0.96).
- Adopted with amendments. The protocol, gate G1 included, is fixed before running: `docs/STAGE1A_PROTOCOL.md`.
  - One SAE representative, chosen on rep 0 by the same rule as the baselines; this gives the consensus at M1024 k6 12k.
  - Equal tuning counts.
  - Nulls run (T9).
  - T6 details.
  - G1-cal measure.
- Deviation M5: dictionary learning uses OMP + MOD (k-sparse, the TopK SAE's objective) instead of sklearn lasso-LARS, which took more than 5 min for 1 pass over 20k
  tokens at 1,024 atoms (timing test only). OMP + MOD: about 2.7 min per fit at 1,024 atoms, k 6 (reconstruction R2 0.775 on the fit rows; no validity numbers seen).
  FastICA: about 10 min per fit (100k rows, 512 components).
- Open for the user: Q1, whether FM-vs-physics is out of the gates (it was in v1's gate S); Q2, the review's fail branch is a methods note.
- Modal: task budget `v2s1a_sae` $5 (account shforghani2002). Superseded Stage C/D budgets set to 0. Ledger rule updated to the user's
  2 accounts x $29/month.
- Stage 1a run notes:
  - Sanity stop: svx_L6 rep 0 'neutral' area was 0.0035 off A3 (R1 and 'orig' areas exact), in a fresh process too. Cause: BLAS thread
    count. Stage A ran with OMP/MKL_NUM_THREADS = 4, and the first Stage 1a run with the default 16. With 4 threads the row is exact.
    run_s1a_cpu.ps1 now sets 4 threads. The 11 rows computed with 16 threads were dropped and rerun, so all rows share one environment.
  - Modal: test job sae_M1024_k6_s12000 rep 0 equals the A3 L4 row bit for bit (R1 and all four areas; $0.23). An earlier attempt failed
    on return because torch.__version__ is a torch type; fixed with str(). Booked at its worst case, $0.44. The 8 remaining single-SAE jobs
    (tuned SAE reps 1-2, null SAEs reps 0-2) launched; L4 capacity was queued at times (no cost while queued).
  - 2026-11-09 about 20:00: Claude Code's memory guard stopped both background jobs, the local CPU runner and the local Modal client of the 3
    consensus jobs. Per the guard's rule they were not restarted; waiting for the user.
    - CPU rows saved, rep 0 (4 threads): k-means 9/9, ICA 2/2, raw 2/2, sparse varimax 2/2, DL 1/3. All sanity rows exact.
      Not done: DL A2048 k6 and A1024 k27, oracle, selection, reps 1-2, dense references.
    - Modal SAE rows saved: tuned single SAE reps 0-2 (reps 0-2 = A3 L4 rows), null SAE (untrained) reps 0-2, physics SAE reps 0-2.
    - Consensus: the cloud app kept running with no client. It was stopped at 20:29 (no results collected), and run v2s1a_sae-007 was booked
      at its worst case, $2.22. Task v2s1a_sae committed $3.97 of $5, conservatively (Modal billing at 20:29: $1.63 for the month, lagging).
    - Code changes, no maths changed:
      - cloud jobs also write their result to the volume (/s1a_out);
      - launches use `modal run --detach`, with cloud/s1a_collect.ps1 + s1a_merge.py to recover;
      - k = 1 probing ranks are chunked float32 (identical AUROCs, checked).
  - 2026-11-09 evening, restart (user: "go ... always put save"): task budget raised $5 -> $7 with the user's OK; CPU runner restarted
    (4 threads, resumes from saved rows); consensus relaunched detached (run v2s1a_sae-008, ok 3/3, $1.25; results also on the volume).
  - Consensus rep 0 on L4 = 0.526 vs 0.562 for the A2 consensus on the local RTX 3050 Ti (abs diff 0.04). The single SAE is bit-identical
    on L4 across runs, so the 5-fit consensus is the GPU-sensitive step. Selection used A2's rep-0 value, as written in M1 before running;
    G1 uses the L4 rows for all 3 reps.
  - refs step failed at start on an unused import (`sklearn.utils.parallel_backend`, removed in this sklearn); the line was deleted and
    only that step was rerun. No result changed.
  - G1 read-out (`v2_ct/RESULTS_S1A.md`, `results/s1a_g1.json`): G1-cal PASS (oracle C(0.7) mean 21.7 of 32 over 6 half-models);
    G1-main PASS (gains +0.216 / +0.304 / +0.243, mean +0.254; strongest baseline k-means, k-means, ICA). Branch: pass.
    Descriptive flags for the user: physics (R3) SAE 0.34-0.36 vs single CT-FM SAE 0.39-0.40; k = 1 vertebral-level probing shows no SAE
    advantage over k-means / ICA / sparse varimax; DL rows implausibly weak (R1 0.00-0.01), implementation to be checked before any claim.
- 2026-11-10, after G1, at the user's request ("do the two fixes"). G1 stays as read; both are sensitivity checks, written here before results.
  - Deviation M7, dictionary learning. Diagnosis (label-free, from the saved rows): the signed DL reconstructs better than the SAE (fit R2 0.775
    vs held-out 0.707; no dead atoms; converged), but its features are unstable: median twin score 0.13 (SAE 0.48) and perturbation r 0.19
    (SAE 0.79). Cause: the codes are signed. Least-squares coefficients on correlated atoms cancel and flip sign; the TopK SAE's codes are
    nonnegative. M5 called the signed DL "the TopK SAE's objective"; that was wrong on nonnegativity.
    Fix: nonnegative k-sparse DL (nonnegative OMP, Bruckstein et al. 2008: largest positive residual correlation, nonnegative least squares
    on the support by FISTA; same MOD update, init, 100k fit rows, 30 iterations), the same 3 configs (dl_nn_*), codes not split. Unit
    checks: NNLS = scipy nnls (objective gap <= 4e-6 at 27 atoms); the signed OMP path is bit-identical to before. The DL family is
    re-selected over all 6 candidates by the same rep-0 rule (results/s1a_selection_m7.json; s1a_selection.json untouched); the new
    representative runs reps 1-2; G1-main is re-read with it (RESULTS_S1A.md, check 1).
  - Physics-feature SAE consensus (physcons_M1024_k6_s12000, R3 input, reps 0-2, Modal L4, run v2s1a_sae-009, timeout 25 min, worst
    case $1.66, inside the $7 task budget), so the null comparison is consensus vs consensus (RESULTS_S1A.md, check 2).
  - Results, 2026-11-10 03:35 (`v2_ct/RESULTS_S1A.md`, `results/s1a_g1.json` keys G1_main_m7 and physcons):
    - Physics consensus (run v2s1a_sae-009, ok 3/3, closed at $0.84; task v2s1a_sae now $6.06 of $7): primary 0.350 / 0.339 / 0.349
      (R1 0.72). CT-FM consensus minus physics consensus: +0.176 / +0.246 / +0.186 (mean +0.202), >= 0.05 in every rep ('orig' rule:
      +0.31 / +0.31 / +0.29). Consensus adds nothing on physics features (single physics SAE 0.34-0.36); on CT-FM it adds 0.40 -> 0.55.
    - Nonnegative DL, rep 0: dl_nn_A1024_k6 0.063, dl_nn_A2048_k6 0.033, dl_nn_A1024_k27 0.002 (signed: 0.046 / 0.019 / 0.014).
      Re-selection: dl_nn_A1024_k6 -> reps 1-2: 0.063 / 0.046 / 0.038 (mean 0.049; signed rep 0.032), R1 0.00-0.01 in every row.
      Nonnegativity raised median twin score and perturbation r (A1024 k6: t 0.13 -> 0.26, r_pert 0.19 -> 0.37) but not to SAE level.
      G1-main re-read with the M7 DL representative: unchanged (DL is not the strongest baseline in any rep), PASS.
    - Label-free coding diagnostic (`v2_ct/s1a_dl_diag.py`, results/s1a_dl_diag.json; rep 0 half-A vs half-B dictionaries, 20k tokens):
      the two halves' dictionaries agree (median max cosine 0.84 / 0.82 / 0.75; share >= 0.7: 0.82 / 0.77 / 0.59), and OMP codes are
      stable under small input noise for k 6 (median r 0.93 / 0.91), but OMP codes do not match between halves (twin share >= 0.7:
      0.003 / 0.005 / 0.001). On the same dictionaries, top-k thresholding of ReLU(D(x - b)) gives twin share 0.17 / 0.13 / 0.32 (about the
      SAE's R1 0.20; it does not reconstruct, so it is a probe, not a method). Reading: greedy OMP on correlated atoms turns small
      dictionary differences into different supports; the DL's instability is in the coding step, not in the dictionary. Exploratory.

## 2026-11-10: confirmation protocol drafted (review order step 2; writing only)
- User decisions: frozen methods = SAE consensus M1024 k6 12k (L4); baselines km_M1024_L6, ica_L6, dl_nn_A1024_k6, raw_L6, svx_L6;
  oracle as reference only. Primary metric = 425-matched 'neutral' area, 'orig' as sensitivity. Hypotheses H2, H3, H1, H2b (margin 0.05),
  H5; J = 10 halves on the 555 sealed scans, Holm.
- Draft `docs/SAE_PROTOCOL_v2.md` written; not registered. No Modal run; the 555 scans were not downloaded or opened (only the ID list and
  its hash were read). Left open for the user in its §0: D1 = Q1 (H2b keep / drop), D2 (H5 descriptive / confirmatory), D3–D7 (where the
  CPU baselines run, perturbation subset, Modal budgets, null SAE, registration).
- Found while drafting (to fix before any confirmation run): dev paths are hard-coded in `p1b_sanity/common.refpos` (cache) and in
  `v2_ct/s1a_lib` (results, tables, tasks), and the Modal job prints metric values. Both are covered by E4 in the draft.

## 2026-11-10: colleague review of the draft protocol; protocol revision 2
- Review pushed by the colleague to branch protocol-v2-review: `docs/REVIEW_PROTOCOL_v2.md` (desk analysis of the committed tables).
  Recomputed independently from s1a_*.json and the per-feature tables (read-only scripts, nothing refitted).
  - Main finding confirmed (F1): the consensus (396-414 features) escapes the 425-feature subsampling that the 1,024-feature methods get.
    Like-for-like, the SAE's gain is about +0.10, not +0.25: single SAE - best baseline +0.104 at 425 features, +0.104 at all features,
    +0.104 with each method's top 425 features by twin score. Consensus - single at all features: +0.019.
  - Differences explained: the review counted a missing twin score as 0, while production v (np.fmin) skips it. With the review's rule its
    ICA and physics-SAE link values (0.454, 0.475, 0.473) reproduce exactly. Single SAE - physics single is therefore +0.044 at 425
    features (review +0.064) and +0.035 at all features (review +0.057).
- Lead's decision (2026-11-10, "yes do"): adopt the review with the refinements in `docs/RESPONSE_REVIEW_PROTOCOL_v2.md`. Protocol
  `docs/SAE_PROTOCOL_v2.md` revision 2:
  - H2 = single SAE vs best single-fit baseline, at 425 features; all arms have 1,024 features. Dev +0.104 (6.4 SDs). The single SAE is
    also the best of A2's 8 single configs on rep 0; with it, G1-main would also have passed (+0.090 / +0.122 / +0.100).
  - H3 = consensus non-inferior to the single fit at all features (margin 0.05) and superior on R1; H3c (coverage superiority) dropped.
  - H1 = 0.5 < theta < 0.75, as one intersection-union test.
  - H2b (D1) and H5 (D2) descriptive; family {H2, H3, H1}, m = 3.
  - New key secondaries K1-K6, with wording rules W1-W2 fixed before any K3 value is computed. New sensitivity analysis S5: missing
    twin score counted as 0. K3 adds a centred smoothing control (1/8, 3/4, 1/8), because the review's 2 x 2 control is half a token off centre.
  - Physics consensus dropped from the confirmation; the physics single SAE runs (descriptive). Modal estimate about $15.7, caps $22.00.
- Nothing run on Modal; the sealed scans were not touched. Open for the lead: D3-D8 and the budgets.

## 2026-11-10: CT confirmation stopped; clinical leg (prostate MRI) planned
- User's decision: the project's goal is a clinical finding (e.g. an SAE feature for cancer), not a methods result. The CT confirmation
  (SAE_PROTOCOL_v2) is stopped, unregistered. The 555 TotalSegmentator scans stay sealed.
- Reason, checked from the metadata only (no scan opened): TotalSegmentator has no tumour masks, only a scan-level "pathology" tag
  ("tumor": 32 of 150 dev, 136 of 555 sealed, at many sites). CT-FM's Phase 1 scan-level tumour probe: AUROC 0.53 (reference 0.70, n = 75).
  Kidney cysts (the only lesion masks) have core tokens in 5 dev patients and are not eligible.
- PI-CAI data: the user allowed the Modal volume `picai-dataset-vol` (another project) only if certainly unaltered. It was inspected
  read-only, by file names only, and is NOT used: 1,500 sessions with `t2_norm`, `adc_norm`, `prostate_mask`, `target_1_mask` and
  `ai_heatmap` files. The intensities are normalised and HBV is missing. The plan uses a fresh download (Zenodo 10.5281/zenodo.6624726 +
  `picai_labels` at a pinned commit). Zenodo did not answer from the laptop (SSL errors), so the fetch will run on Modal.
- Checked for the plan (web):
  - `picai_labels`: expert csPCa labels for all 1,500 studies (`human_expert/resampled` 1,295 incl. 220 positives + `Pooch25` 205
    positives); the clinical sheet includes `lesion_PIRADS`; CC BY-NC 4.0; 328 ProstateX cases inside PI-CAI; a 2026 note says the
    public set is convenience-sampled and not for AI benchmarking.
  - Encoders: ProFound (pretrained on PI-CAI) and Triad (PI-CAI + ProstateX) are excluded as leaks. DINOv3 ViT-L/16 is leak-free
    (gated licence). MRI-CORE is a candidate pending a leak and weights check.
- Plan written: `docs/PLAN_PROSTATE_MRI_v1.md` (DRAFT). Nothing run, nothing downloaded. Budgets asked for M0-M1: $4.10 in caps.
- Briefing for reviewers `docs/BRIEFING_FOR_REVIEWERS.md`; README and DATA updated; plan v2 review packet copied onto the branch.

## 2026-11-10: colleague review of the MRI plan; plan revision 2
- Review `docs/REVIEW_PLAN_PROSTATE_MRI_v1.md` (R1-R6) pushed to branch prostate-mri-plan.
- Checked independently from the PI-CAI clinical sheet only (metadata; no images): `picai_labels` commit
  ce4a4723d7c46d882a6cbaacb40ed6c4be86282f (2026-07-13), `marksheet.csv` SHA256 23EAB23790886258440B4AF2842733332003F2C59F0A007B1E7B6B44572CF0AE
  (kept in the session scratchpad, not in git).
  - All review facts reproduced: 468 unverified negatives (PI-RADS <= 2); 1,032 verified; centres; 282 ISUP-1 studies; PSAD 30.1% missing.
  - Found in addition:
    - PSAD is missing for 99% of PCNN;
    - reported PSAD is rounded (73% within 5% of PSA/volume);
    - PI-RADS is complete;
    - biopsy cohort (verified, PI-RADS >= 3): 884 studies, 417 positive.
- Plan revision 2:
  - all six changes adopted;
  - R1 extended: the biopsy cohort is the primary clinical population (needs the lead's OK, P6);
  - R2 extended: equal-capacity patient scores (<= 5 features each), C3a non-inferior with margin 0.03, C3b superiority only if dev
    shows >= +0.02;
  - R6 changed: PSAD recomputed for every study;
  - R3c made into a token-size rule;
  - a power statement for M5 (about 0.04 AUROC detectable).
- Reply: `docs/RESPONSE_REVIEW_PLAN_PROSTATE_MRI_v1.md`. Briefing wording fixed (ICA reproducibility).

## 2026-11-10: MRI plan revision 3 (encoders)
- The user questioned DINOv3 (a natural-image model) as the main encoder. The user's Hugging Face request for DINOv3 was rejected by
  Meta (status "rejected", 2026-11-10). DINOv3 is removed; no attempt is made to obtain it another way.
- My error, corrected: revision 1/2 applied the v1 rule "the encoder must never have seen PI-CAI" without separating label exposure from
  self-supervised image exposure. That excluded the prostate-MRI models.
  - New two-level rule: label exposure excludes. Image exposure (self-supervised, no labels) is allowed with disclosure plus an external
    test on a cohort the encoder never saw.
- Checked at the sources (web):
  - ProFound: 3D MAE, no labels in pretraining as described; PI-CAI 1,500 + TCIA 863 + ReIMAGINE 491 + private 2,146; T2W/HBV/ADC
    3-channel, 1 mm isotropic. Code Apache 2.0, weights on a UCL OneDrive link with no stated licence; feature-extraction code "ongoing".
  - MRI-CORE: SAM ViT-B + DINOv2 on Duke-110K (Duke only; prostate coverage not stated); Apache 2.0; Google Drive weights;
    `model.image_encoder` on 3 x 1024 x 1024 in [0, 1].
  - SAM ViT-B: Apache 2.0, public checkpoint. It is the natural-image comparison (MRI-CORE's initialisation).
  - Prostate158: 139 public cases, Charité; licence to check in M0.
- Design fixes found while revising:
  - all encoders are compared on one common token grid (feature maps differ: 64 x 64 per slice vs 3D patches);
  - features are stored for gland tokens only (full slices would need hundreds of GB);
  - probe samples are capped at 200 normal tokens per study;
  - encode budget raised to $5.00 (about 135k slice images), with a 10-study benchmark first.
- No Hugging Face token needed. Nothing run, nothing downloaded.
