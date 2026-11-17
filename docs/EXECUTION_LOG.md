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
- While revision 3 was being written, the colleague pushed a second review (`docs/REVIEW2_PLAN_PROSTATE_MRI_v1.md`, against revision 2).
  The push was refused as non-fast-forward. I rebased onto it (no conflict; nothing overwritten).
- Second review checked from the `picai_labels` git tree at ce4a472 (10,325 files) and the marksheet; no images.
  - Q1 reproduced exactly: outline source by centre PCNN 0/109, RUMC 125/111, ZGT 80/0 (Pooch25/resampled); SysBx+MRBx 109/1;
    years as stated.
  - Added: ISUP 5 is 17% of Pooch25 vs 8% of resampled.
  - Q2 masks present: HeviAI23, Yuan23, Guerbet23.
  - Both adopted in revision 3, with refinements (gates are contrasts; RUMC sources still differ by year and biopsy type; zone from
    agreement of the two models; visual QC without lesion masks).
  - Reply: `docs/RESPONSE_REVIEW2_PLAN_PROSTATE_MRI_v1.md`.

## 2026-11-10: third review of the MRI plan; plan revision 4
- Review `docs/REVIEW3_PLAN_PROSTATE_MRI_v1.md` (T1-T3, a desk review of revision 3) pushed by the colleague.
- Checked at the sources:
  - Prostate158: 139 public + 19 hidden cases, zones and lesion masks, no clinical variables listed; repo MIT, data licence to check.
  - QIN-Prostate-Repeatability: TCIA, 15 patients, 30 studies.
  - So T1's concern holds.
- Revision 4:
  - T1 adopted as rule S, plus an M0 search for an external cohort with PSA, volume and PI-RADS;
  - T2 adopted: one intensity rule, plus a caveat on MRI-CORE's min-max pretraining (sensitivity only, never switches a gate);
  - T3: the concern is adopted, but the fix is nested cross-validation instead of a 3/2 fold split (the split would leave about 85
    positive studies for the gate).
- Reply: `docs/RESPONSE_REVIEW3_PLAN_PROSTATE_MRI_v1.md`. Nothing run.

## 2026-11-10: MRI M0 started (user: "OK" to revision 4 and the M0-M1 budgets)
- Ledger: new tasks mri_fetch $0.80, mri_prep $0.80, mri_m1_encode $5.00 (account shforghani2002; $7.74 committed before, month
  billing $3.20).
- Protocol `docs/MRI_M0M1_PROTOCOL.md`, fixed before running. Two engineering refinements made before any run, no change in rules:
  - one-step resampling onto the final grid (avoids interpolating ADC/HBV twice);
  - the prep job is split into a 5-study smoke run (15 min) and a full run (60 min), so both fit the $0.80 cap.
- Code `imgsae/mri/`; unit tests on synthetic data 7/7 pass.
- Split (M0.1) from the marksheet only (SHA256 checked):
  - 738 dev / 738 sealed patients; 754 dev / 746 sealed studies; strata balanced (difference <= 1);
  - 438 dev biopsy-cohort studies;
  - `split.json` SHA256 4211975b...; committed before any image download.
- M0.2 fetch:
  - **First attempt mri_fetch-010 was cancelled.** At 14:27 the laptop's network dropped (DNS error `getaddrinfo failed`). The local Modal
    client raised, and Modal cancelled the running call even though it was launched with `--detach`.
    - 12.1 GiB of partial downloads were kept.
    - Ledger reconciled from the $0.62 worst case to $0.21 (23.2 container minutes).
  - **Fix:**
    - spawn-based launch (`imgsae/mri/cloud/launch.py`; the client returns at once; collect with `collect.py` / `wait_collect.ps1`);
    - resumable downloads (HTTP Range, MD5 over the whole file, commit about every GB);
    - all 7 files in parallel; timeout 90 min.
    - Memory `always-save-work` updated.
  - **Relaunch mri_fetch-011: done** in 9.9 container minutes ($0.15).
    - All 7 files MD5 ok (26.87 GB; folds 0-4, LICENSE, README); Zenodo licence cc-by-nc-4.0.
    - Index: 1,500 studies, all with t2w/adc/hbv.
    - picai_labels zip SHA256 f122ebeb...; marksheet SHA256 matches.
- M0.3 prep smoke mri_prep-012 (5 studies, all negatives): no errors, about 10 s per study, $0.13.
  - Gland Dice 0.98, zone Dice 0.90-0.93; gland ADC p50 1,101-1,437; one zone mask (HeviAI23) not on the T2W grid, resampled.
  - T2W in-plane 0.28-0.5 mm, slices 3.0-3.6 mm; ADC/HBV 1.75-2.0 mm in-plane.
  - The lesion-mask path was not exercised (no positives among the first 5). It is checked in the full run's outputs, because a second
    smoke run would not fit the $0.80 cap together with the full run.
- Full prep launched: mri_prep-013 (749 studies). **Done:** 754/754 dev studies, 0 errors, 6.1 container minutes. `imgsae/mri/RESULTS_M0.md`.
- **M0 decisions** (rules of the protocol, section 4):
  - **ADC units:** 10^-6 mm2/s (gland p50 median 1,410).
  - **Token size 4 mm:** lesion recall Pooch25 0.689 / 0.874 / 1.000 and resampled 0.841 / 0.956 / 1.000 at 8 / 6 / 4 mm.
  - **Outline materiality:** RUMC, ISUP-matched ratio of median lesion volume, Pooch25 / resampled = 0.60 (CI 0.35-0.93), so
    **material**. Cross-centre token-level results are labelled annotation-dependent, and the clinical claim rests on patient-level M3.
  - **Masks:** Pooch25 lesion masks are binary (0/1); resampled masks carry ISUP 2-5. Some masks were not on the T2W grid and were
    resampled (lesion 6, HeviAI23 zones 183).
- **QC** (gland Dice median 0.986, zone Dice median 0.909): 3 flagged (zone disagreement). Label-blind check: keep Bosma22b for all three.
- **Exclusion: 11050_1001070.**
  - The picai_labels README names it as a faulty AI segmentation; M0 also surfaced it as the one positive with an empty lesion crop.
  - The label-blind wide-field render (T2W + gland outline only) shows the gland mask on anterior pelvic tissue, not the prostate.
    Guerbet23 agrees with it (Dice 0.87), so both AI masks are unusable.
  - Decision taken on the label-blind image. 753 dev studies used, 212 positive (PCNN 54, RUMC 118, ZGT 40).
- **Deviation (label-blind, added after M0 ran):** an extra QC screen, AI gland volume / reported prostate_volume outside 0.5-2.0.
  - Reason: agreement of two AI masks cannot catch a case where both are wrong.
  - Result: 2 studies (10541_1000552 ratio 2.29; 11051_1001071 ratio 6.15, reported 4 ml); both masks are correct on the label-blind
    render, so they are kept. 11050_1001070 has ratio 1.80, so this screen would not have caught it.
  - For M3: the reported volume of 11051_1001071 looks wrong, which affects its PSAD.
  - Decisions: `imgsae/mri/results/m0_qc_decisions.json`; render script `imgsae/mri/m0_render_pf_qc.py`.
- QC images (random 20 with lesion outlines): the outlines sit on low ADC / high HBV, and ADC/HBV are aligned with T2W after resampling.
- **Encoder check** (M0.5): the first build failed on a dependency conflict (monai 1.5.0 needs torch < 2.7; no cost, the build failed
  before launch). Changed to torch 2.6.0 / torchvision 0.21.0, ProFound's documented environment. Launched mri_m1_encode-014.
- **Encoder check 1** (mri_m1_encode-014, $0.23): SAM ok. MRI-CORE: 150 of 153 encoder tensors were not matched by my check. ProFound:
  the checkpoint is not the ViT. Both were investigated from the checkpoints (torch safe loader, weights_only=True) and the repo code:
  - **MRI-CORE's checkpoint** is a DINOv2 teacher ViT-B/16: cls token, pos embed (1, 197, 768) = 14x14 at 224 px, final norm, chunked
    blocks, no layer scale, no SAM neck, plus dino_head.
  - The repo's SAM-shaped loader (`build_sam.py`) would therefore:
    - (a) run the features through a randomly initialised neck (no neck weights in the checkpoint);
    - (b) drop the trained position embedding: it stores it under the original key `backbone.pos_embed`, not `image_encoder.pos_embed`,
      and `strict=False` hides this;
    - (c) use windowed attention at 1024 px.
  - **Fix:** a timm ViT-B/16 loaded strictly with the 150 backbone tensors; 480 px input, so 30x30 tokens = exactly 4 mm on the 120 mm
    crop; ImageNet normalisation (DINOv2 default; MRI-CORE's training config is not released; [0, 1] input becomes a descriptive
    sensitivity analysis).
  - **ProFound-alpha** (checkpoint-799): args model=convnext, input (64, 224, 224), mask ratio 0.6, norm_pix_loss, epoch 799. FCMAE
    ConvNeXtV2-tiny 3D with sparse kernels. Built with its own `convnextv2_tiny` + `remap_checkpoint_keys`. Stage 0 (stride 4, 96-d)
    per the protocol rule; input = the centre 64x224x224 of our 1 mm grid.
  - Protocol section 5 and the M1 arm list updated (dated, before M1).
- **Encoder check 2** (mri_m1_encode-015, $0.20): **all usable.**
  - MRI-CORE: 150/150 tensors, strict "All keys matched", 0 not equal; only mask_token and dino_head dropped.
  - ProFound: only the final norm missing, 0 unexpected, deterministic.
  - SAM: strict.
  - All features finite, 0 constant channels.
  - Seconds per study: MRI-CORE A/B 0.32/0.10, SAM A/B 6.12/2.04, untrained 2.04, ProFound 0.03.
  - Weights SHA256 recorded in `RESULTS_M0.md`.
- **M0 DONE.** MRI Modal spend $1.10 (fetch 0.37, prep 0.30, encode 0.43). Stopped for the user's review before M1.

## 2026-11-10: MRI M1 started (user: "yes!" to M1 after the M0 review)
- M1 implementation notes and deviations written into the protocol (section 6) before any result:
  - storage without dilation;
  - MRI-CORE sensitivity arms on the probe sample only;
  - SAM per-slice min-max sensitivity not run (budget);
  - verified analysis restricts the evaluation;
  - descriptive bootstraps use 500 draws;
  - patient-level probe defined.
- Code: `encoders_lib.py` (the M0-verified loaders, one shared module), `m1_lib.py` (4 mm grid, labels, R = 66, sample), `cloud/m1_encode_modal.py`
  (SHA256 of the weights checked against M0; fail-fast if the first studies all fail), `m1_analysis.py`; `launch.py` gains `launch_many`.
  Unit tests 4/4 and 6/6.
- **Smoke mri_m1_encode-016** (2 studies, $0.17): ok, 13.8 s per study. One feature file inspected: 873 kept cells, 200 sampled,
  R 66 columns, all arms finite with no constant columns.
- **Full encode mri_m1_encode-017:** 4 shards in parallel, timeout 54 min, worst case $4.35 (task: 0.60 + 4.35 <= 5.00).
  - **Done:** 753/753 dev studies, 0 errors; 14.0-14.7 s per study; ProFound cell centres all inside its field of view.
  - One shard started late (L4 capacity queue), so the first watcher gave up after 75 min (exit 6, no harm); a second watcher collected.
  - Cost $3.85 (189.4 container min), so task mri_m1_encode is at $4.45 of $5.00. Features (about 9 GB) downloaded to the laptop
    (`results/prep_cache/m1_feats`, not in git).
- **Analysis checks before the run** (committed bfa2699 before any result):
  - marksheet SHA256 check;
  - fast weighted AUROC for the bootstrap (equal to sklearn in the tests);
  - outer-fold fits shared with the identical full-CV fits;
  - computed outline-source counts.
- **M1 analysis** (laptop): 164,116 tokens (13,516 lesion), 211 cached fits of about 20 s each (2,304-d).
  - **Gate FAILED:** nested Δ vs R −0.022 [−0.038, −0.007] (all studies) and −0.023 [−0.039, −0.007] (verified); Δ vs untrained
    −0.005 and −0.004.
  - Rule S picked MRI-CORE B in folds 0, 2 and 3, MRI-CORE A in fold 1 and SAM A in fold 4; ProFound was below U in every fold.
  - Full-CV AUROC: R 0.912, MRI-CORE B 0.909, MRI-CORE A 0.903, untrained 0.894, SAM A 0.894, ProFound 0.882, SAM B 0.879.
  - Patient level, biopsy cohort (437 studies, 206 csPCa): MRI-CORE B 0.658, R 0.656; PI-RADS alone 0.718 (reference).
- **Post hoc diagnostics** (`m1_diagnostics.py`, descriptive, the gate unchanged):
  - D1 alignment: all arms best at zero shift (no mapping bug).
  - D2: at C = 0.001, MRI-CORE A is +0.014 [+0.001, +0.026] over R's best C; other arms are not above R.
  - D3: R + MRI-CORE B is +0.013 [+0.003, +0.022] over R + untrained.
  - Per-fold mean of the gate Δ is −0.015 (pooled −0.022). Part of the pooled figure comes from pooling scores of different arms
    across folds; the conclusion is unchanged.
- **Stopped per the protocol** ("if the gate fails: stop and report; the lead decides"). Report in `imgsae/mri/RESULTS_M1.md`.
  Recommendation: no M2; the optional next step is a laptop feasibility check of csPCa within PI-RADS ≥ 3, under a new protocol.
  MRI Modal spend $5.12.

## 2026-11-10: check of the user's earlier PI-CAI cancer model (user asked: "can't we simply use that? check it")
- **Inputs:** read-only from `picai-dataset-vol`; nothing written there.
  - Checkpoints:
    - `picai_3d_unet_fold012.pth`: MONAI UNet, 4.8 M params;
    - `picai_segresnet_best_{dice,loss}.pth`: MONAI SegResNet, 18.8 M params;
    - `picai_training_checkpoint.pth`: epoch 120, best validation Dice 0.43.
  - Both networks take **2 input channels** (most likely T2W + ADC, no high-b DWI).
  - The folds are PI-CAI's public folds 0-4; train 0-2, validation 3, test 4.
- **Missing:** the training code is not on this computer (needed for the input channels, the preprocessing, and which checkpoint made the scores).
- **Scores:** per study, the highest blob probability from `Phase2_Blob_Candidates_Isotropic.csv`. The non-isotropic table is about 0.53 everywhere and is ignored.
- **Labels:** the official marksheet (SHA checked); the user's labels agree 100%.
- **Test fold 4** (296 studies, 90 csPCa):

| Population | Model | PI-RADS |
|---|---|---|
| All studies | 0.779 (matches the user's figure) | 0.857 |
| Biopsy cohort (180 studies, 88 csPCa) | 0.729 | 0.707 |

  - Within PI-RADS 3 / 4 / 5: model AUROC 0.81 / 0.64 / 0.72 (n 31 / 71 / 78).
  - **Pooled within-PI-RADS AUROC 0.689 [0.598, 0.775]** (patient bootstrap, 2,000 draws): the model ranks csPCa beyond PI-RADS on unseen cases.
  - Training folds 0.78-0.81, so there is little case-level memorisation.
- **Leak constraint:** only fold 4 is label-clean. 454 of our 746 sealed studies are in its training folds, so this exact checkpoint cannot be confirmed on our sealed half.
- **Next (pending the user):** get the training code; retrain the same recipe on our split so the sealed half stays clean; new protocol and budget first.

## 2026-11-11: added value of the user's model over the clinical baseline (test fold 4, biopsy cohort; post hoc, descriptive)
- **Data:** 180 studies, 88 csPCa (verified, PI-RADS ≥ 3). PSAD from the marksheet (9 missing, median-imputed); 11051_1001071 is not in this set.
- **Within-PI-RADS AUROC** (ranking inside each PI-RADS category): model 0.689, PSAD 0.618, age 0.544.
- **Added value** (logistic regression, no penalty), base = PI-RADS (one-hot) + log PSAD + age:

| Model | In-sample AUROC | Optimism-corrected AUROC (Harrell, 1,000 bootstraps) |
|---|---|---|
| Base | 0.747 | 0.730 |
| Base + model score (rank) | 0.803 | 0.785 |

  - Corrected gain **+0.055** (bootstrap interval of the gain +0.014 to +0.098); likelihood-ratio χ² 14.7, p = 0.0001.
- **Method note:** a first pass used pooled 5-fold CV AUROC. It gave PI-RADS alone 0.579 against 0.707 direct, the known downward bias of pooled CV AUROC for coarse predictors, so the likelihood-ratio and bootstrap method was used instead. The CV gain was similar (+0.053).
- **Caveats:**
  - one fold, post hoc;
  - which checkpoint produced the isotropic table, and whether anything was tuned on fold 4, must be confirmed from the user's code.
- **Context:** the user shared a review of Gemini's suggestions; the assessment was given in chat (no protocol change).

## 2026-11-11: the user's newer model (repo shforgh02/prostate-bpmri-cade; Modal account forghanishayan, read-only)
- **The repo:**
  - preprocessing: 1 mm isotropic; T2W z-scored in the prostate; ADC and DWI divided by their 99th percentile in the prostate;
  - SegResNet design: 3 inputs, init 32, blocks (1, 2, 2, 4), dropout 0.2, instance norm;
  - loss: 0.5 Dice + 0.5 Focal; folds 0-2 train, 3 validation, 4 test;
  - the UCLA external pipeline.
- **Missing from the repo:** the training loop and the PI-CAI scoring step.
- **Found in `forghanishayan`, volume `picai-dataset-vol`:**
  - `models/picai_*_new.pth`: 3 inputs, 18.8 M params, epoch 101, best validation Dice 0.504;
  - `Phase2_Blob_Candidates_Isotropic_New.csv` (scores for folds 3 and 4 only).
- **Recipe recovered from the checkpoint:**
  - AdamW, weight decay 1e-4, final LR 5e-5;
  - ReduceLROnPlateau on validation loss (factor 0.5, patience 10, min 1e-6);
  - mixed precision; early stopping.
  - Still unknown: starting LR, patch size, batch size, augmentation.
- **Test fold 4:**
  - All studies: AUROC 0.774 (the user's figure: 0.774); PI-RADS 0.857.
  - Biopsy cohort (180 studies, 88 csPCa): 0.711 vs PI-RADS 0.707.
  - Within-PI-RADS AUROC **0.695 [0.604, 0.780]** (PSAD 0.618).
  - Over PI-RADS + PSAD + age: optimism-corrected 0.730 → 0.774, **+0.044** [bootstrap +0.010, +0.096]; likelihood-ratio p = 0.0001.
  - The same finding as the older 2-input model (+0.055).

## 2026-11-11: go/no-go check before any training (user: "are you sure? limited resources")
- **Question:** does the model's added value survive the lesion's own ADC, DWI and size (measured at the model's top lesion), and does it replicate on fold 3?
  - Fold 3 was used only to pick the checkpoint by validation loss; its biopsy cohort is 177 studies, 80 csPCa.
- **Gains in optimism-corrected AUROC:**

| Model and data | Over clinic | Over clinic + ADC/DWI/size |
|---|---|---|
| New model, fold 4 | +0.041 (p 0.0002) | +0.027 (p 0.0007) |
| New model, fold 3 | +0.010 (p 0.12) | +0.004 (p 0.15) |
| **New model, pooled folds 3 + 4** (357 studies, 168 csPCa) | **+0.022** [+0.006, +0.050] (p 0.0002) | **+0.021** [+0.005, +0.046] (p 0.0002) |
| Old model, fold 3 | +0.014 (p 0.02) | +0.000 (p 0.18) |
| Old model, fold 4 | +0.054 (p 0.0001) | +0.052 (p 0.0001) |

- **Reading:** a real but small signal beyond the clinic and the lesion's ADC/DWI/size (about +0.02 AUROC). It varies a lot between folds; fold 4 was the favourable fold, and the earlier +0.044 to +0.055 were optimistic.
- **Decision proposed to the user:** no model training now; first, no-cost feasibility checks of a stronger-model or external-data route.
- **The lead's UCLA experience** (reported by the lead, not recomputed here): a PI-CAI-trained model reached about AUROC 0.66 and sensitivity about 70% on UCLA, below the radiologists. UCLA differs in scanners and coil, so both UCLA routes were dropped.

## 2026-11-11: feasibility scan, then PAUSE
- **Scan:** `docs/FEASIBILITY_SCAN_breast_lung.md` (no compute). Lung (Sybil/NLST) blocked; breast (Mirai/EMBED) is the best fit, with caveats on novelty and data access.
- **The lead's decision:** push all notes for colleagues, and pause to find a better clinical question.
- **Plain-language summary:** `docs/PAUSE_NOTE_2026-11-11.md`. README, STATUS and the reviewer briefing point to it.
- **Project Modal total:** $12.86 (CT 7.74, MRI 5.12); no open runs; sealed halves (PI-CAI 746 studies, CT 555 scans) unopened.

## 2026-11-12: lung route re-checked at no cost (user: "do what you think its best"); still paused
- **Correction of the feasibility scan.** Sybil's split is published: `files/Shetty_et_al(Google)_data_splits.p` on the `train` branch of its repository (15,019 participants: train 10,179, dev 2,493, test 2,347). The scan's "blocked" verdict was wrong and now carries a correction note.
- **Lung L0** (`imgsae/exploratory/lung_l0/`; public NLST tables joined with the split; no images, no Modal):
  - The 11,432 CT-arm participants in no Sybil split hold only 34 cancers, so they are not a test set. The clean test data are Sybil's test split (154 participants with cancer).
  - A logistic regression on the trial radiologists' recorded findings, fitted on Sybil's train and dev participants, scores on Sybil's test participants:
    - cancer within 1 year, baseline scans: 0.929 [0.879, 0.971], against Sybil's published 0.93;
    - cancer within 6 years, baseline scans: 0.745 [0.699, 0.790], against Sybil's published 0.75.
  - **Reading:** no gap over the doctor in lung either (condition 1 fails). The comparison is unpaired; a paired test needs Sybil's scores on the test scans (a paid run, not approved).
  - Exploratory: nothing was fixed in a protocol beforehand. If a confirmatory test follows, the comparator is frozen as in `nlst_l0.py` before any Sybil score is computed.
- **UCLA high-b audit** (`imgsae/exploratory/ucla_audit/`; read-only on the lead's copy of TCIA Prostate-MRI-US-Biopsy; DICOM headers only):
  - **Question:** the lead's earlier pipeline picks the high-b series by name, so could a wrong series explain the fall to about 0.66 on UCLA?
  - **Answer: no.** Of 975 sessions, 960 use an image with b ≥ 1,400 (955 at b = 1,400; 863 of them computed). No series mixes b-values.
  - 15 sessions are wrong or unknown: 7 at b = 0 (the series is named CALCBVAL but holds b = 0 trace images), 1 at b = 50, 1 at b = 1,000, and 6 with no b-value in the header. They are listed in `highb_series_audit.csv`.
  - The UCLA spreadsheets hold a UCLA score per target (1,617 targets), PSA and prostate volume for nearly all 1,150 patients; 551 patients have a Gleason ≥ 7 core.
- **UCLA scanner and coil headers** (one DICOM header per series; the lead's copy; read-only). This corrects the 2026-11-11 entry, which put the fall on UCLA down to "scanners and coil":
  - Of the 800 examinations in the lead's UCLA study, 598 are on a Siemens Skyra 3 T, 92 on Prisma or Vida, 62 on Verio or Trio, 32 on a Siemens 1.5 T, and 16 on GE or Philips.
  - An endorectal coil shows in the headers of 12 of 800 (my reading of the coil strings; to be confirmed by a radiologist).
  - On the Skyra examinations alone the picture is the same as overall: SegResNet 0.657, nnU-Net 0.688, UCLA score 0.685, PSA density 0.713. So coil and scanner do not explain the modest AUROC; the biopsy-referred population does most of it. Real shift shows only in the 48 examinations at 1.5 T or on other vendors.
- **Checks of the lead's UCLA manuscript** (on its own `source_data` tables; handover file in the manuscript folder, `REFRAMING_HANDOVER_2026-11-12/`):
  - The headline increment (AI top-3 added to radiologist targets: +16 of 36 missed) is not above the manuscript's chance model (12.6 expected, P = 0.12).
  - The models add nothing to UCLA score + PSA density at examination level: −0.001 [−0.004, +0.001] and +0.000 [−0.002, +0.003].
  - This is the same pattern as in PI-CAI and in lung: the model matches what the radiologist already recorded.
- **Lung L1** fixed and launched: protocol `docs/LUNG_L1_PROTOCOL.md`; analysis frozen before any score (`imgsae/exploratory/lung_l1/l1_analysis.py`); ledger task `lung_l1_sybil`, cap $15.00, approved by the lead ("1.yes"). The run is executed by a delegated lower-cost agent at the lead's request.
- **Data kept (git-ignored):** `imgsae_data/nlst_public/` (the NLST clinical package, its tables, the split file; SHA-256 in `RESULTS_L0.md`).
- **Spend:** none. Modal total unchanged at $12.86.

## 2026-11-12: lung L1 run and result (Sybil against the recorded findings, paired)

- **Who ran it:** a lower-cost agent (Sonnet), under `docs/LUNG_L1_PROTOCOL.md`, as the lead asked. I checked its report against the files afterwards (analysis hash, `scores.csv` row count, ledger, volume list).
- **What was scored:** all 2,279 baseline series and 3,133 of the 4,436 follow-up series of Sybil's test split (5,412 series, 2,331 participants). The follow-up tier stopped at the $13.00 line of the protocol. No series failed in the final runs.
- **Gates:** all passed. Every one of the 6,715 series was found in IDC; Sybil reproduced its published demo scores exactly; labels agree with the split file for 99.87% of scored exams; Sybil's own AUROC is 0.927 at one year on baseline scans (published 0.93) and 0.914 on all scored screens (published 0.92).
- **Verdict by the fixed rules:** "No evidence that Sybil carries information beyond the recorded findings, at the precision of this test set."

| Analysis | Exams / cancers | Sybil | Recorded findings | Sybil minus findings | Both minus findings | Both minus Sybil |
|---|---|---|---|---|---|---|
| A1, 1 year, baseline (primary) | 2,278 / 41 | 0.927 | 0.929 | −0.003 [−0.063, +0.058] | +0.026 [−0.004, +0.061] | +0.025 [−0.014, +0.069] |
| A2, 6 years, baseline (primary) | 2,002 / 131 | 0.724 | 0.745 | −0.021 [−0.073, +0.034] | +0.011 [−0.019, +0.040] | +0.040 [+0.012, +0.072] |
| A3, 1 year, all scored screens | 5,380 / 72 | 0.914 | 0.945 | −0.031 [−0.072, +0.008] | +0.000 [−0.030, +0.021] | +0.035 [+0.012, +0.064] |
| A4, 2 years, baseline | 2,270 / 57 | 0.877 | 0.891 | −0.014 [−0.067, +0.034] | +0.015 [−0.016, +0.045] | +0.030 [+0.005, +0.056] |
| A5, negative baseline, cancer at 1 to 6 years | 1,140 / 51 | 0.580 | 0.644 | −0.064 [−0.160, +0.030] | −0.008 [−0.026, +0.011] | +0.086 [+0.005, +0.169] |

Intervals: 97.5% for A1 and A2, 95% for the others (participant bootstrap, 2,000 draws).

- **What it does and does not show:**
  - Sybil does not beat a 39-variable logistic regression on the radiologists' form in any of the five analyses.
  - The form adds to Sybil at 2 and 6 years, on all screens and after a negative baseline (the intervals exclude zero).
  - Sybil is not empty of new information: the likelihood-ratio test for Sybil given the findings is significant in A1 to A4 (p about 1e-8), and at one year the combination is +0.026 over the findings with a lower bound of −0.004. The fixed "adds" rule is not met, but a small real gain is not excluded.
  - With 41 and 131 cancers, a true gap under about 0.03 to 0.04 can be missed. The claim is "no large gap", not "equal".
  - After a negative baseline screen Sybil scores 0.58, in line with the published range for cancers without a visible nodule.
- **Deviations** (all listed in `imgsae/exploratory/lung_l1/RESULTS_L1.md`): torch installed from PyPI because the pinned CUDA build is not on the mirror; two failed smoke attempts and one hung download test before the fixes (non-DICOM files in the demo zip; `idc-index` replaced by direct `s5cmd`); one run with a stale address map in two containers, rescored; the follow-up tier is partial; the export was built on the PC from the per-series files after the cloud export call timed out; the agent was interrupted twice by its usage limit between launches.
- **Spend:** $12.53 of the $15.00 cap. Project total $25.39 of the $29 cap on account shforghani2002; month usage $21.12. No run is open; the volume `imgsae-nlst-l1` is deleted; the lead's other volumes were not touched.
- **Consequence for the plan:** the lung leg of the proposed clinical paper now has a paired result on the model's own test split. About $3.60 is left under the project cap on this account this month, so any further paid step waits for the lead's decision on budget.

## 2026-11-13: direction after L1 (lead's decision), free checks, draft plan

- **Lead's decision:** no two-cancer paper ("2 cancer only makes it hetrogen"). The lead's earlier prostate manuscript is handled outside this project. For this project the lead asks to open the model: why it is right, why wrong, and whether features can improve prediction or cut false positives and negatives.
- **Free checks on the L1 scores (post hoc, exploratory; `imgsae/exploratory/lung_l1/posthoc/`):**
  - The recorded findings explain only 15% (boosting) to 19% (ridge) of the variation in Sybil's one-year score; rank correlation 0.33.
  - Same participant one year apart: r = 0.61 for Sybil's score, 0.33 for the recorded-findings model.
  - At 90% specificity each: 615 and 531 non-cancers flagged, 212 shared. Of 72 one-year cancers: both 56, Sybil only 5, findings only 8, neither 3. Of 131 six-year cancers on baseline scans: both 41, Sybil only 18, findings only 10, neither 62.
  - Within radiologist-positive screens (2,062 exams, 68 cancers): Sybil 0.898, recorded findings 0.932.
  - Clean cancers: dev 149 participants (88 exams within one year, 319 within six); test 154 (91, 346).
- **Sybil's code checked:** the risk is a linear function of a 512-number vector (three pooled vectors, one linear layer, ReLU, then the hazard layer), so feature contributions to a prediction can be computed exactly.
- **Literature:** *Auditing Sybil* (arXiv 2602.02560, ICML 2026) audits Sybil with synthetic nodules; no real outcomes. No feature-decomposition study of a lung screening model found.
- **Draft plan:** `docs/PLAN_SYBIL_AUDIT_v1.md` (v0 was replaced the same day). Not approved. About $39 to $49 in gated steps.
- **Spend:** none.
- **Later the same day (lead: run the work with Opus 5.5 at xhigh effort in a fresh session; keep the old prostate manuscript out of this project):**
  - Plan v1 written, with three changes from v0: (1) Sybil's head is not plainly linear: the year-t logit is the base hazard plus a sum of ReLU hazards, and the published score is the calibrated mean of five members, so contributions are exact per member and exam only; (2) the split file lists series only for test participants, so dev needs a series-selection rule learned from metadata; (3) a paired-reconstruction sub-study (same exam, two kernels) is added as direct evidence of technical sensitivity.
  - Rule added: no new outcome analysis of the existing test scores before the hypotheses are frozen.
  - Budget fact: the guard's all-time project check has $3.61 left (used $25.39 of $29); Modal's monthly usage is $21.12. The new work needs the lead's approval of a separate project limit.
  - Hand-over prompt for the new session: `docs/HANDOVER_PROMPT_SYBIL_AUDIT.md`.

## 2026-11-13: Lung L2, step S0 (free): literature, plan check, series rule, protocol
- **Lead's instructions (hand-over prompt, this session):** Part A = S0; budget approvals ($45 task `lung_l2_audit`, `project_cap_usd` 72, monthly $29 unchanged); commit and push to GitHub now and after each step (new instruction from the lead in this session).
- **Git:** committed and pushed the lung L0/L1 work, plan v1 and the hand-over prompt (`33feef4`). Left out on purpose: `New report .txt` (a colleague's chat messages, with a third person's name) and `imgsae/exploratory/ucla_audit/` (old prostate manuscript, kept out of this project). Waiting for the lead's word on both.
- **Literature (read in full: *Auditing Sybil* arXiv 2602.02560v2; Mikhael et al. JCO 2023 with appendix):**
  - *Auditing Sybil* uses LUNA25 (an NLST subset with biopsy or stability labels) and an internal set of 243 scans, with diffusion-based nodule removal and insertion. Findings: Sybil is close to additive over nodules; many cancers get near-zero nodule contribution; upper-lobe weighting; weaker response near the pleura; background term linked to age; artefacts (ECG leads, gown snaps, goiter). No patient-level outcome analysis, no radiologist form, no scanner analysis, no held-out confirmation. Plan v1's "no real outcomes" was too strong and is corrected in the protocol.
  - Sybil's paper: one series per exam, "thinnest" (code: most slices, annotated series first), slices thicker than 2.5 mm dropped; dev used for validation during training (`scripts/train.py`); its appendix already shows that age, sex and smoking duration can be predicted from the image.
  - Simon et al., *Invest Radiol* 2025: Sybil on 1,049 + 1,961 kernel pairs and 1,288 thickness pairs of NLST test participants; no AUROC difference (abstract; full text not accessible). The plan's reconstruction sub-study is therefore reframed to score- and feature-level change.
  - Also found: Phellan Aro *Chest* 2026 (Sybil weak without nodules, AUROC 0.64 at 6 years; clinical data help); Lee *Radiology* 2025 (weak for future cancers in never/light smokers); Gaur MELBA 2025 (Sybil AUROC women 0.88 vs men 0.81 on NLST); Wang *Eur Radiol* 2025 (body composition predicts lung cancer); Reeves RCI 2026 (Sybil plus a nodule model); Mammo-FM preprint (sparse autoencoder on a breast risk model). No work decomposes a lung screening model's representation against real outcomes, radiologist findings and technical factors.
  - **Second dataset:** none fully open. Duke DLCS: all five Zenodo records restricted (checked through the Zenodo API). P-ELCAP (211 participants, 67 cancers, case-control): Zenodo request box. Both need the lead's name; optional.
- **Plan check (from the files):** split counts, dev and test outcome counts, cost per series (bulk $0.0021, all-in L1 $0.0023, 7.6 container-seconds) and Sybil's structure at the pinned commit all confirmed. Ensemble = mean of member probabilities, then a monotone per-year calibrator.
- **New technical finding (from code + IDC metadata):** Sybil places slices at `SliceThickness`, not at the true spacing (pinned commit and current `main`). In 44% of selected dev series the spacing is smaller than the thickness; at ratio 0.5 (578 dev, 400 test series) the chest is stretched 2× in z and the 500 mm grid cuts its ends. Not raised in Sybil's GitHub issues. Added as a cheap counterfactual sub-study (`zfix`), to be confirmed in the pilot (G2f). Also: padding is −600 HU after normalisation; 22% of series have a reconstruction field above 360 mm (in-plane crop).
- **Series rule (metadata only, IDC 25.0.5; `lung_l2/series_rule.py`, `results/s0_series_rule.json`):** `sharp_thin` (sharper kernel class, then thinnest, then most slices) reproduces the split file's test series in 98.9% / 98.6% of exams (choice half / check half); same kernel class and thickness 99.1%. Gate (90%) passed. Dev: a series for 7,348 of 7,361 studies; 6 duplicate person-years, both studies dropped → 7,336 dev exams. Kernel pairs: dev 3,895, test 3,523.
- **Tools:** no package installed. The IDC parquet files were converted to CSV with the existing `mibg` conda env (pyarrow) and PDFs read with the existing `default` env (pypdf), both with `python -I`. Downloads: IDC index release files (SHA-256 checked against the release), the two papers, Sybil source files.
- **Budget change (approved by the lead):** `ledger.json` gets `project_cap_usd` = 72.0 and task `lung_l2_audit` = 45.0 (with notes); `budget.py` project check uses `project_cap_usd` (falls back to `cap_usd`); monthly check and `cap_usd` = 29 unchanged. Guard dry run: task 0.00 ≤ 45, project 25.39 ≤ 72, month 21.07 ≤ 29.
- **Protocol written:** `docs/LUNG_L2_PROTOCOL.md` (DRAFT; changes C1–C12 from plan v1 in its section 1). Stopped for the lead's OK.
- **Spend:** none.

## 2026-11-13: Lung L2, lead's OK on Part A; step S1 (free) and S2 preparation
- **Lead's answers:** (1) protocol and budget diff OK; (2) the second reviewer is an external person who reads the git repository; a short brief for them will be written; (3) keep `New report .txt` and `ucla_audit/` out of git (now in `.gitignore`); (4) no external dataset request now.
- **S1 dev manifest** (`lung_l2/s1_manifest.py`, `results/manifest_dev.csv`, SHA-256 `0eddcbb1…19425b`, `results/s1_manifest.json`): 7,336 main rows = 99.65% of the 7,362 dev exams in the tables (gate ≥ 95%: **passed**); 0 duplicate pid-year; 2,492 participants. Tiers D1 2,484, D2 2,442, D3 2,410, D4 500 kernel partners (GE 236, Siemens 195, Philips 50, Toshiba 19; drawn from 1,316 available D1 pairs). Pilot = first 300 D1 rows in the fixed participant order (seed 0). Expected zfix rows: 908 (ratio ≤ 0.65); in the pilot 103 rows with ratio < 0.95.
- **Cloud job** `lung_l2/cloud/l2_sybil_modal.py` (from the L1 job): Sybil members called directly with forward hooks; the volume is rebuilt from Sybil's own per-slice loader with the same resample and crop/pad (checked against `Serie.get_volume()` in the smoke step); image measures in the prefetch thread; zfix and pair variants; one `.npz` + `.json` per series and variant. Guard worst case uses the function's hard timeout (60 min).
- **Tests on the PC:** image measures on a synthetic phantom (lung volume and emphysema exact to < 2% and < 1 point, air −1,005 HU, 0.75 s); pilot checks `s2_pilot_checks.py` on fake consistent files (all pass) and with one corrupted logit (detected).
- **Run plan for the executing agent:** `lung_l2/cloud/RUN_PLAN_S2.md`.
- **Spend:** none yet.

## 2026-11-13: S2 smoke attempt 1 (run lung_l2_audit-031): demo passed, two bugs of mine fixed
- **What ran:** the executing agent (Sonnet) launched the smoke step; guard tests passed (task 0.00 + 0.45 ≤ 45; project 25.39 + 0.45 ≤ 72; month 21.08 + 0.45 ≤ 29). The image built without trouble.
- **Result read from the volume** (`l2/run_info/smoke.json`, fetched with `modal volume get`, free): demo case through the L2 path equals the published scores exactly (max difference 0.0); the rebuilt volume equals Sybil's `Serie.get_volume()`; Sybil's own `predict` gives the same six numbers; head weights saved (SHA-256 `ba2d6d85…009bac`); T4, torch 1.13.1+cu117; 1.25 container-minutes.
- **Bug 1:** the returned dict held `torch.__version__` (a torch string type); the local client without torch could not unpickle it, so collect exited 4 and the agent stopped, as the run plan says. Fix: plain `str()`.
- **Bug 2:** the three dev series failed with "COULD NOT LOAD DICOM" inside the verification step, because it re-read the DICOM files after the job had deleted them. Fix: the comparison with `Serie.get_volume()` now runs in `_prepare`, before deletion. Nothing partial was saved (`l2/dev/main` does not exist on the volume).
- **Ledger:** run 031 closed by hand at $0.20 (formula from the measured 1.25 container-minutes: $0.16).
- **Deviation:** a second smoke run (≈ $0.2) inside the S2 allocation ($2.00).

## 2026-11-13: S2 pilot done (runs 032 to 035); two checks failed as written; stopped for the lead
- **Runs (executing agent, Sonnet; all guard tests passed; report checked against ledger, run files and PC counts):** 032 smoke $0.17 (demo exact, 3 of 3 dev volumes equal Sybil's own); 033 pilot D1 0–300 on 4 T4 containers, 297 + 3 smoke series, 0 errors, 52.6 container-min, $1.08; 034 repeat 20 series $0.20; 035 L4 50 series $0.31. Task total $1.96 (with 031). Month usage $22.54; project $27.34 of 72. No open run. PC copy `imgsae_data/lung_l2_vol/l2`: dev/main 300, dev/zfix 111, rep/main 20, l4/main 50 (equal to the volume). The 3 files in dev/errors are stale from run 031; the series are saved.
- **Pilot checks** (`results/s2_pilot_checks.json`): G2a pass (demo 0.0); G2b pass (logits from saved h and head weights within 6.7e-7; hidden_fc within 1.2e-6; ReLU exact); G2c pass (calibrated within 1e-15); G2d pass (repeat run identical, 0.0; L4 vs T4 within 6.9e-7); G2g T4 cheaper ($0.0027 vs $0.0030 per series; 10.6 container-s per series with 37% z-fix variants); G2h pass (0 failures).
- **G2e failed as written:** emphysema/volume plausible in 96% (pass), outside-air median within −1,000 ± 30 HU in only 87% (needed 95%). Diagnosis (`results/s2_diagnose.json`): the inversion is right on GE, Siemens and Philips (median air −998, −994, −999 HU). Toshiba reads about 38 HU low (14 of 18 Toshiba series fail; a scanner offset that also inflates emphysema %). 19 GE series have too little outside air to measure (FOV tight). About 6 GE series: the lung mask leaked into outside air (lung volume < 100 ml), most likely where the lung touches the image edge.
- **G2f failed as written (37 series with stretch ≥ 1.54):** within 10% in 38%. Diagnosis: in all 7 series where the lung is not cut, measured ÷ expected stretch = 0.995 to 1.005; the 30 others are cut by Sybil's 200-slice crop (lung reaches the grid edge in 30 of 30), which the stretch predicts. At stretch 2.0 the lung is cut in 26 of 27 pilot series, at 1.6 in 4 of 10, below 1.6 in 0 of 263. The check did not exclude cut cases; that was my error in writing it.
- **Other pilot facts (dev, outcome-free, descriptive):** hazard units are all off in members 1, 2, 3 for every pilot exam (their logit is the same for all six years); in members 0 and 4 only the units for years 2 and 3 switch on (in 18% and 16% of exams). z-fix changes the 6-year mean member logit by mean |Δ| = 0.46 SD of the between-exam spread at stretch 2.0 (n 27; 70% of exams move ≥ 0.25 SD; mean shift −0.29 logits), 0.42 SD at 1.6 (n 10), 0.27 SD at 1.1–1.33 (n 74).
- **PC pipeline tested on the pilot:** `l2_data.py` (300 exams, all matched to the tables; groups N 28, B 14, D 6, I 7, T 23 variables) and `s4_q1a.py` run end to end. `s4_core` passed its synthetic test (exact contribution identity 1e-14 for all six arms; SAE fit ≈ 400 s on CPU).
- **Stopped:** per the lead's instruction (stop if a gate fails). Proposed: amend G2f to the uncut series and keep z-fix; accept G2e with a QC rule in the analysis (lung volume < 1,500 ml → image measures missing, flag "lung at image edge"), no change to the cloud job. Both would be logged deviations.

## 2026-11-14: lead's decision on the two pilot checks; S3 part 1 (D1) started
- **Lead:** "i accept both proposa". Recorded as protocol amendments A1 and A2 (`docs/LUNG_L2_PROTOCOL.md` section 16a), logged deviations: A1 = G2f judged on the uncut series, z-fix kept; A2 = G2e accepted with the analysis rule "lung volume < 1,500 ml → image measures missing, flag `T_lung_at_edge`" (added to `l2_data.py`). The cloud job is unchanged.
- **S3 part 1:** run plan `lung_l2/cloud/RUN_PLAN_S3_D1.md` (D1 rows 300 to 2,483, zfix for ratio ≤ 0.65, as far as the November month check allows), executed by the agent.

## 2026-11-15: D1 launch A done (run 036); the executing agent hit the assistant's usage limit; unattended driver for the rest
- **Run 036** (launched by the agent on 2026-11-14, D1 rows 300–2,483, 4 T4 containers): 1,597 of 2,184 rows done, 0 errors, 220.4 container-min, collected and closed at $3.61 ($0.0023 per series). Then the agent was stopped by the 5-hour usage limit before launch B. No run open. Task total $5.57; month $26.52 of $29.
- **Lead (2026-11-15):** "Try again but be carefully 5 hours limit, so put a run that keep going if limit end".
- **Change of executor (deviation from the hand-over rule "paid runs by a lower-cost subagent"):** the rest of the run plan is executed by an unattended script, `lung_l2/cloud/drive_runs.py`, started by a one-time Windows scheduled task (`imgsae_l2_d1b`, wrapper `run_d1b.cmd`), so no model limit can stop it. It follows `RUN_PLAN_S3_D1.md` step by step: every launch through the guard, the billing lag rule, nshard 4 → 3 → 2 → 1, stop on collect exit 4, errors > 5%, or 80 minutes without a result; then copies the volume to the PC. Log `lung_l2/logs/driver_d1b.log`, state `driver_d1b.json`. Dry run on 2026-11-15: only nshard 2 or 1 fit the month (26.52 + 2.01 ≤ 29). The result of run 036 is kept as `run_dev_D1_300_2484__lung_l2_audit-036.json`; the driver keeps a copy per run id.

## 2026-11-15: D1 finished (run 037, unattended driver); preemption found; ledger reconciled with Modal's billing
- **Run 037** (driver `d1b`, scheduled task, 2 T4 containers because only that fitted the month: 26.52 + 2.01 ≤ 29): the last D1 rows done, 0 errors; driver copied the volume to the PC and stopped with status `finished`. **D1 complete: 2,484 main series and 430 z-fix variants, 0 failures.**
- **Check (S3 gate for D1):** every saved D1 file passes the recomputation checks (G2b: logits within 6.8e-7, hidden_fc within 1.9e-6, ReLU exact; G2c: calibrated within 1.7e-15). `results/s3_d1_checks.json`.
- **Preemption:** the app log of run 037 shows "Container terminated due to preemption. Your Function will be restarted with the same input." The first attempt of shard 1 had saved 279 series before the restart; the restarted attempt saw 7 left. That is why launch B found 308 rows instead of 587. Data are unaffected (done series are skipped; results are deterministic). Cost is affected: the job only reports the last attempt's minutes.
- **Ledger reconciled** (`lung_l2/cloud/reconcile_billing.py`, Modal hourly billing per app, summed over apps sharing an hour): billed 031–035 $1.37 (measured $1.96, conservative manual estimates), 036 $4.07 (measured $3.61), 037 $1.65 (measured $0.93). The guard counts max(measured, billed): task `lung_l2_audit` $7.67 of $45; project $33.06 of $72; month $28.17 of $29. November is used up.
- **December plan prepared, not scheduled:** `drive_plan.py` + `run_dec.cmd` run D2, D3, D4 in order (each only if the previous finished), copy to the PC, then reconcile billing after 70 minutes. Creating the scheduled task for 2026-12-01 was blocked by the permission system (unattended future spending); left for the lead's decision.

## 2026-11-15: progress report for the lead
- Written: `docs/PROGRESS_REPORT_L2_2026-11-15.md` (steps S0 to S8 and their state, findings so far on dev without outcomes, money, why D2 to D4 wait for 1 December, dated plan, decisions needed, a short message for the external reviewer). Numbers checked against the ledger and the result files. One pilot number from my earlier chat summary (flag change at τ90 of about 4 to 5%) is not in any result file, so it is not in the report.
- Checked: local branch equals GitHub (`174c270`); the December task `imgsae_l2_dec` does not exist yet; no open run; month $28.17 of $29.
- Proposed in the report: free D1 work on the PC before 1 December, outcome-free only (S4 scripts, decomposition fits, validity checks, z-fix change on the 430 D1 variants); all outcome analyses wait for the full dev data.
- **Second account check (user's request, read only):** profile `armanfo`, Modal billing report 1 to 30 Nov: $1.62, all by that account's own other apps (not this project); no app running. With its cap of $29.50, $27.88 is left. Not used for this project (the lead's word is needed). The active profile stays `shforghani2002` (the check used `MODAL_PROFILE` for one command only).
- Report section 12 added: the three data groups (train not run through Sybil; dev used by Sybil's authors to choose when to stop training; test unseen) and the S4 feature step in detail.
- **Decision (user, 15 Nov): no S4 dry run on D1 alone** ("if so forget then"). A result from part of dev would not be trusted and would be replaced. Until D2 to D4 are in, only the remaining S4 scripts are written and tested on synthetic data and the pilot. Report sections 8, 9 and 12 updated.

## 2026-11-15: plan for the rest of L2 written; review by Fable 5.2 next
- **Lead's decisions (quoted):** "i want to use arman fo and not wait" (Modal account `armanfo`, cap $29.50 per month, for the rest of S3 now); the plan is reviewed by Fable 5.2, then executed by a fresh Opus 5.5 session (xhigh).
- **Written:** `docs/PLAN_L2_NEXT_v1.md` (DRAFT): steps P0 to P8 with gates and outputs; proposed amendments A3 (two simple references: R-size, F+I), A4 (second account for S3 D2 to D4, per-account month check, app-list check, identity gate across accounts), A5 (the unattended driver as executor of paid runs). Prompts: `docs/PROMPT_REVIEW_FABLE_L2.md` (review), `docs/HANDOVER_PROMPT_L2_EXEC.md` (execution after the review and the lead's OK).
- Nothing launched; no protocol change yet (A3 to A5 wait for the review and the lead's OK).
- **Plan review done (Fable 5.2, 2026-11-15): approve with edits.** Review in `docs/REVIEW_PLAN_L2_NEXT_v1.md`; 15 edits marked `[Fable edit]` in `docs/PLAN_L2_NEXT_v1.md` (among them: F+I with 5 patient measures and the test "does Sybil add to F+I"; a $17.00 limit for this project on `armanfo`; app check on running containers; account-blind places in the driver; ledger write safety; no cloud volume deletion in P3; S4 scripts committed before the first full-dev run; S6 order and billed-rate projection fixed at S5). Three questions for the lead, each with a default. Execution prompt rewritten step by step: `docs/HANDOVER_PROMPT_L2_EXEC.md` (version 2). The review ran in the same chat as the drafting (not cleared), which the review states. No Modal job, no ledger change, no test data, no dev analysis.

## 2026-11-15: Lung L2 execution (Opus 5.5), Step 0: the lead's OK recorded
- **Lead's OK (execution prompt of 2026-11-15, quoted in short):** plan `docs/PLAN_L2_NEXT_v1.md` approved as reviewed by Fable 5.2, with all `[Fable edit]` changes; amendments A3, A4, A5 approved. Answers to the review's questions: (1) this project may use at most $17.00 on `armanfo` in November, month cap $29.50; (2) keep both cloud volumes, delete nothing on Modal; (3) yes, F+I uses the 5 patient measures as its primary model. The lead keeps the laptop on, plugged in and awake during P3, and wants to be told before P3 starts.
- **Git check:** branch `prostate-mri-plan` equal to `origin/prostate-mri-plan` (`cf0b72b`). Only change in the tree: the known 6-line `checks` entry in `ledger.json` from a read-only status call (15 Nov 14:21); kept, to be committed with the first P1 ledger change (review F8).
- **Protocol:** status line corrected (approved 2026-11-13, not "DRAFT"; review F6); A3, A4, A5 added to section 16a with the date and the three answers. A4 amends section 12 (account, volume deletion), A5 amends section 13 (executor).
- **Spend:** none.

## 2026-11-16: P1 done: the guard knows two accounts (free, code only; no Modal job)
- **Times:** ledger times are UTC. Python's clock on this PC reads UTC because the user variable `TZ=America/New_York` is not understood by the Windows C runtime (scheduled tasks see it too). Modal's billing report hours are UTC as well (checked: `--tz local` gives the same hours with `+00:00`). So the earlier reconciliation was right. The local clock is EST (UTC−5).
- **Ledger** (backup first: `p1b_sanity/cloud/ledger_backup_2026-11-16_before_accounts.json`; change by `ledger_add_accounts.py`): `accounts` = shforghani2002 cap 29.00, armanfo cap 29.50; `armanfo_project_limit_usd` = 17.00; all 37 earlier runs get `profile` = shforghani2002; rule text and notes updated; everything else unchanged (checked by the unit test). The uncommitted `checks` entry of 15 Nov 14:21 is kept and committed with this change (review F8).
- **`budget.py`:** month usage (`modal billing summary --profile P`), open worst cases and the cap per account; task and project tests over all accounts (unchanged); fourth test = this project's runs on the account + worst case ≤ `<P>_project_limit_usd` (armanfo 17.00); unknown profile refused (also a run without profile, and old scripts that call the guard without a profile, e.g. L1, MRI, CT: safe); atomic `save` (temporary file, then replace); `status --no-log` writes nothing; `app_check(P)` for A4.
- **Additions beyond the plan text (all stricter or safety-only):** (1) a lock file serialises ledger writes across processes (a driver and a chat session); (2) the billing lag rule (runs on the account closed in the last 90 min) is now inside the guard's month test, not only in the driver precheck; (3) the $17 test sums all time on armanfo, which equals November because the account had no run of this project before; (4) result files of runs on armanfo get the suffix `__armanfo`, so the main account's `results/runs/smoke.json` is never overwritten; (5) the app check covers every Modal environment of the account (only `main` exists on both accounts).
- **App check field names** (`modal app list --json --profile armanfo` read once on 2026-11-16 ≈ 04:05 UTC: `[]`, no app at all; the main account's list was also empty, so the field names are taken from the client source, modal 1.5.5 `modal/cli/app.py` `list_`): `app_id`, `description`, `state`, `tasks` (= running containers, a string), `created_at`, `stopped_at`. Rule in code: any app whose `description` is not `imgsae-lung-l2` with `tasks` ≠ 0 (or unreadable) blocks a launch; the driver waits 30 min and looks again, and stops after 2 hours.
- **Cloud scripts:** `l2_sybil_modal.py` takes the account from `modal run`'s own `--profile` option (a global Modal option, so no entry-point parameter of the same name), refuses if none is set or if the client profile differs, and passes it to the guard and the run record. `launch.py` runs the app check (armanfo) and the guard per account and stores the profile. `collect.py` takes `--profile`, must agree with the ledger run, sets `MODAL_PROFILE` before importing modal; exit 6 = refused. `drive_runs.py` and `drive_plan.py`: `--profile` required; refuse to start if `MODAL_PROFILE` differs; prechecks = the guard's own tests without logging; per-account copy folder (`imgsae_data\lung_l2_vol_armanfo` for armanfo); every Modal call with `--profile`; keep-awake through `SetThreadExecutionState`. `reconcile_billing.py --profile P` touches only that account's runs. `wait_collect.ps1` needs `-Profile`. `run_dec.cmd` marked superseded (it now fails on purpose).
- **Tests:** `test_budget.py` on a copy of the ledger with fixed month figures: **26 of 26 pass** (per-account caps and status, refusal at the cap, open runs and the billing lag counted on the right account, the $17 refusal by the fourth test only, task test over both accounts, unknown profile and missing profile refused, no-log leaves the file byte-identical, 8 concurrent writers keep all runs, app check on fake output, real ledger untouched). `budget.py status --no-log`: armanfo month $1.62 (metered 9.886 − free storage 8.265), cap $29.50, this project $0.00 of $17.00; shforghani2002 month $28.17, cap $29.00. Ledger hash unchanged by both. Refusals checked: driver without or with a wrong `MODAL_PROFILE`; `drive_plan` likewise; `collect` of run 037 with `--profile armanfo` (exit 6); unknown profile `forghanishayan`. **Driver dry run on armanfo** (D2 0–2442): app check ok; all four tests pass at nshard 4 (task 7.67 + 3.91 ≤ 45; project 33.06 + 3.91 ≤ 72; month 1.62 + 0 + 0 + 3.91 ≤ 29.50; armanfo 0.00 + 3.91 ≤ 17.00). `reconcile_billing.py --dry`: main account total billed $7.09 as before; armanfo has no run.
- **Gate P1: passed.** No Modal job ran. Only read-only Modal calls: profile list, billing summary and report, app list, environment list.
- **Spend:** none.

## 2026-11-16: P2 done: smoke and identity on account armanfo; gate passed
- **Volumes on armanfo before the first run (read only, `modal volume list --json --profile armanfo`):** `ucla-provicnet-vol`, `ct-angio-stage-c-outputs`, `ct-angio-stage-c-inputs`, `ct-angio-totalseg-models`, `kujawa-eval-vol`, `vs-seg-data`, `mibg-dataset-vol`, `mibg-standard-split-data`. None touched. `imgsae-nlst-l2` did not exist; the app created it on the first run.
- **How the runs were launched:** by me, directly (`modal run --detach --profile armanfo ...`, spawn, through the guard), because the driver has no smoke step and both jobs are a few minutes long; a killed client would have lost nothing (detached spawn, one saved unit per series). Collected with `wait_collect.ps1 -Profile armanfo`.
- **The first run on armanfo built the image there** (about 3 minutes). Pinned packages are the same as on the main account (torch 1.13.1+cu117, numpy 1.24.1, pydicom 2.3.0, torchio 0.18.74, opencv 4.5.4.60, Sybil at `d9fc81b9`); some unpinned helper packages are newer (pandas 2.3.3, scipy 1.15.3, idc-index 0.13.5). The identity check below shows no effect on any saved number.
- **Run 038, smoke** (`--step smoke --n-series 3 --zfix-max 0.95`, the same arguments as the main account's smoke run 032): app check ok; guard task 7.67 + 0.45 ≤ 45, project 33.06 + 0.45 ≤ 72, month armanfo 1.63 + lag 0 + open 0 + 0.45 ≤ 29.50, project on armanfo 0.00 + 0.45 ≤ 17.00. T4. Demo case max difference **0.0** (pass mark 0.005); demo volume equal to `Serie.get_volume()`; **3 of 3** dev volumes equal to Sybil's own; 0 errors. Checkpoint SHA-256 of all 16 files equal to the main record; head weights `ba2d6d85…009bac` equal. Closed at $0.17 (1.7 container-min).
- **Run 039, identity** (`--step run --tier D1 --lo 0 --hi 20 --nshard 1 --root xacct --zfix-max 0.65`): guard passed (month armanfo 1.70 + lag 0.17 + 0 + 1.05 ≤ 29.50; project on armanfo 0.17 + 1.05 ≤ 17.00). 20 done, 0 errors, 3.5 container-min, closed at $0.20.
- **Comparison** (`lung_l2/p2_identity.py`, tested first on the main account's repeat run, which passed, and on a copy with one corrupted calibrated value and one corrupted `h`, which failed as it should; result `results/p2_identity.json`): 20 of 20 `xacct` main files and 5 of 5 z-fix files equal the saved D1 files; the 3 smoke series (main + 3 z-fix) in root `dev` equal the saved D1 files. Max difference of the calibrated probabilities **0.0**, of `h` **0.0**, and of every other saved array, the image measures and the DICOM tags 0.0. Only `geo.zfix_needed` differs, in 4 series with spacing/thickness 0.80, because the pilot ran with `--zfix-max 0.95` and the identity run with 0.65 (expected).
- **PC copy:** `D:\Shayan\imgsae_data\lung_l2_vol_armanfo\l2\` (dev main 3 + zfix 3; xacct main 20 + zfix 5; run_info). The main copy is untouched.
- **Gate P2: passed.** D2 to D4 may run on armanfo.
- **Money (ledger, measured; billing not yet reconciled, it will be after P3):** P2 $0.37. Task `lung_l2_audit` $8.04 of $45; project $33.43 of $72; this project on armanfo $0.37 of $17.00; armanfo month by Modal's billing $1.77 of $29.50 (billing lags).

## 2026-11-16: P4a done: S4 scripts written and tested. **S4 analysis code fixed: commit `a536192`** (pushed before any full-dev outcome run)
- **New scripts** (`imgsae/exploratory/lung_l2/`): `s4_common.py` (shared conventions: populations, participant folds seed 0, halves, participant bootstrap 2,000 draws, cross-fitted unpenalised logistic and LR test as lung L1, SMD with a participant-cluster-robust p and BH q per table, primary-arm rule of 9.5, candidate format), `s4_scores.py` (check P1, gating shares, dev AUROC of Sybil and F, C6 note), `s4_q1b_u.py`, `s4_q1c.py`, `s4_q2.py`, `s4_u1a.py`, `s4_u2.py`, `s4_u3.py`, `s4_u4.py`, `s4_refs.py` (A3: R-size; F+I with the 5 measures; "does Sybil add to F+I"; 7-measure and lung-not-cut runs; by maker; U3 row; all-dev fit for S5), `s4_gate.py` (9.8 table; source search that no S4 script reads the L1 test-score file or a test file; exam table all dev), `s4_report.py` (number tables for the results file, read from the result files), `run_s4_dev.ps1` (P4b order). P3 tools: `p3_merge.py` (never overwrites), `s3_checks_all.py`.
- **Changes to existing scripts, before any full-dev run** (no full-dev S4 output exists; logged as fixes):
  1. **Bug:** `s4_q1a.design` (and the new `s4_common.variables`) dropped the text columns `T_maker` and `T_model`: under pandas 3 they are read as `str`, not `object`, so they were turned into empty numbers and removed. Fixed (one-hot for every non-numeric column). Without the fix, maker and model would have been missing from the technical group in Q1a, naming, U1a, Q2 and U2. The pilot Q1a run of 13 Nov had this error (it was a code test only).
  2. `s4_decomp.py`: the V4 association vectors also lost the text columns (now one-hot), and binary variables now use the rank-biserial r = 2·AUROC − 1 as protocol 9.6 says (it used Spearman). Group shares now use the same ddof in covariance and variance (they sum to 1 exactly; before 1.0001).
  3. `s4_q1d.py`: D5 is now the z-fix rows with spacing/thickness ≤ 0.65 only (the old code mixed in the pilot's 0.65–0.95 rows), and the U1b qualification is judged on all D5 exams with SD(ℓ̄_6) of all dev main exams, as written (the old code used only the stretch-2.0 subgroup). Intervals, halves, candidates and group-term changes added.
  4. `s4_q1a.py`: participant-bootstrap intervals and dev-half values of the Shapley shares (point estimates unchanged).
  5. `l2_data.py`: the assemble report lists the non-missing share of every group variable, empty and constant columns, and the `grp` values (review E12).
  6. `s4_decomp.py`, `s4_common.py`: the data folder can be pointed elsewhere (`L2_S4_DATA`), used by the tests only.
- **Specification choices fixed by this commit** (mine, before any full-dev result): candidate statistics and nulls per script (listed in each script's docstring); Q2 candidates only from the τ90 false-alarm tables, misses descriptive (88 one-year cancers); kernel-pair margins carried over from U1b (0.30, 0.10); P1 judged as written on all dev exams, with diagnostics; U2 T-share over the five named groups; U3 target = the radiologists' sensitivity on the analysed exams (tables: 0.909); τ_rad from the protocol's rate 2,573/7,362.
- **Tests:** `test_s4_scripts.py`, a synthetic world with planted effects (900 participants × 3 screens; a maker/kernel factor in `h` with no cancer information; nodule, emphysema and a hidden persistent factor that carry cancer; z-fix and kernel shifts): **50 of 50 checks pass** (among them: PCA arm valid with families named N, T, I, D, B; U adds to F; z-fix qualifies U1b and D5 excludes the 0.8 rows; Sybil-only false alarms have a higher T term; technical removal narrows the false-alarm spread, ratio 0.19; Sybil adds to F+I; the gate judges 8 hand-made cases right; a null candidate does not hold; leak check passes). `test_p3_merge.py`: 5 of 5. `s3_checks_all.py` on the D1-only copy reproduces `s3_d1_checks.json` exactly. **Pilot code test** (300 real dev exams, all 14 steps incl. `l2_data` and all six arms at K = 64 on the GPU): every step runs after three small-sample fixes (a dev half whose fold has no case now gives "no value"; Q1c with too few T0/T1 pairs writes "not computed"; the report handles both). Pilot numbers were not read, not reported and not used; the pilot outputs were deleted. The pilot assemble report has no empty column.
- **Finding about Sybil's published score** (from the calibrator file and the pilot's score values; no outcome): the calibrator is step-like and maps every mean 1-year probability below about 0.04 to the same value 0. In the pilot, s1 takes 32 distinct values in 300 exams and 17% are 0. Consequences: check P1 (a rank correlation) can fail through ties; a quantile threshold can flag more than its nominal share. Handling: P1 stays as written; diagnostics (rank correlation with the uncalibrated mean member probability, tie counts) and the reached specificity at τ90 are reported. If P1 fails in P4b, I stop and ask the lead.
- **Laptop note:** the GPU runs at 210 MHz of 2,100 MHz (software power cap; on mains power, battery 100%). The SAE arm works but about 10× slower (pilot decomposition 70 min). Not changed by me.
- **Spend:** none.

## 2026-11-16: P3 run 1 (driver `arm`): D2 done; stopped in D3 by the 80-minute rule after a Modal preemption; restarted (driver `arm2`)
- **Start:** one-time task `imgsae_l2_s3rest` (wrapper `run_s3rest.cmd`, "do not stop on battery", 14 h limit) at 04:23 UTC. The lead was told before the start.
- **D2:** run 040 (4 T4 containers): 1,629 of 2,442 rows done, 0 errors, measured $3.61; run 041 (4 containers): the remaining 813, 0 errors, $2.03. **D2 complete, 0 failures.**
- **D3, run 042** (4 containers, 05:53): Modal **preempted shard 1** at 06:33 UTC after about 310 series ("Container terminated due to preemption. Your Function will be restarted with the same input."; app log saved in `logs/app_logs_run042.txt`). The restarted attempt did the remaining 293 rows of that shard and finished at about 07:15, two minutes after the driver's 80-minute limit (07:13). The driver stopped with `stopped_collect_timeout`, as its rules say, and copied the armanfo volume to `lung_l2_vol_armanfo` (exit 0). Shards 0, 2, 3 stopped cleanly at their 55-minute soft limit (355, 435, 425 rows). No error in any shard; no data lost (done series are saved one by one).
- **What I did** (no paid step before the reason was known): read the driver log, the state file and the app log (reason above); stopped the old driver process during its idle 70-minute wait (only the billing step was left); collected run 042 by hand (closed at $3.38 measured; the preempted attempt is not in this figure); reconciled the armanfo billing with no driver running (runs 038 to 042 billed $10.95 in total; hour 07 still incomplete, so a final reconcile follows).
- **Restart** (same run plan; done rows are skipped by the job): wrapper `run_s3rest_b.cmd`, one-time task `imgsae_l2_s3rest_b`, `drive_plan.py --profile armanfo --tag arm2 --plan D3:0:2410,D4:0:500`. Preflight and first precheck: task 18.62 + 3.91 ≤ 45; project 44.01 + 3.91 ≤ 72; armanfo month 12.87 + lag 6.31 + 0 + 3.91 ≤ 29.50; this project on armanfo 10.95 + 3.91 ≤ 17.00. Run 043 launched at 07:18 UTC.
- **Deviation (logged):** the restart was made without waiting for the lead. Reason: the hand-over prompt asks to find the reason and report before any restart; the reason is a Modal preemption (no guard refusal, no failed check, no error, no cost overrun), which is not in the stop-and-ask list. The lead was told in the chat before the restart.

## 2026-11-16: P3 done: S3 complete on all dev tiers (D2, D3, D4 on armanfo); merged; S3 gate passed
- **Restart driver `arm2`** (task `imgsae_l2_s3rest_b`, 07:17 UTC): run 043 = the remaining 592 D3 rows (4 containers), 0 errors, measured $1.60; run 044 = D4, 500 of 500 pair series (4 containers; this project on armanfo 12.56 + 3.91 ≤ 17.00), 0 errors, measured $1.38. Copy to `lung_l2_vol_armanfo` exit 0. The driver ended normally and ran `reconcile_billing.py --profile armanfo` after 70 minutes (09:26 UTC). No other app on armanfo had running containers at any check. Both tasks are now `Ready` (one-time; they do not run again).
- **Merge** (`p3_merge.py`, dry run first; `results/p3_merge.json`): 5,920 new series files copied into `lung_l2_vol\l2\dev` (main D2 2,442 and D3 2,410; z-fix D2 304 and D3 264; pair D4 500); 6 existing files (the 3 smoke series of P2 and their z-fix) compared equal and skipped; 0 stops; every copied file's SHA-256 equal to its source; nothing overwritten. The `xacct` and `run_info` folders of armanfo stay apart.
- **S3 gate** (`s3_checks_all.py` on the merged copy, all tiers; `results/s3_checks_all.json`): D1 2,484 / 2,484, D2 2,442 / 2,442, D3 2,410 / 2,410, D4 500 / 500 series done; **0 failures** in every tier (< 5%); file counts = manifest rows; z-fix 998 needed and 998 present (D1 430 incl. the pilot's 111 at ≤ 0.95, D2 304, D3 264), none without its main file. **G2b** on all 8,834 files: ReLU exact, hidden_fc within 1.9e-6, logits within 8.4e-7; **G2c**: calibrated within 5.8e-15. **Gate passed.**
- **Money (Modal billing reconciled; the guard counts max(measured, billed)):** armanfo runs 038 to 044 billed $14.03 (P2 $0.42; P3 $13.61: runs 040 $4.10, 041 $2.30, 042 $3.83, 043 $1.82, 044 $1.56). This project on armanfo **$14.03 of $17.00**; armanfo month (whole workspace) $15.69 of $29.50. shforghani2002 unchanged at $28.17 of $29.00. Task `lung_l2_audit` **$21.70 of $45**; project $47.09 of $72. **S3 total $19.75** of its $22.00 allocation (D1 $5.72 + P2 $0.42 + P3 $13.61). P3 billed rate: $0.0025 per manifest row including z-fix variants.
- **Cloud volumes:** none deleted (lead, 2026-11-15). `imgsae-nlst-l2` exists on both accounts.
- **P4b started** after the gate (free, PC): `l2_data.py` for dev: 7,336 exams, 2,492 participants (2,493 in the split file; one has no usable exam), all `grp` = dev, 998 z-fix and 500 pair variants; no empty column; constant: `T_tilt` only; image measures present for 97.5% (air noise 95.1%); outcome counts as S0 for y1 (88 cancers, 38 at baseline) and y2 at baseline (65); y6 at baseline 135 cancers and 2,045 negatives (S0: 137 and 2,050; 8 baseline exams have no usable series). `s4_scores.py`: **check P1 passed** (Spearman 0.991 at t = 1, 0.997 at t = 6). The rest of S4 runs with `run_s4_dev.ps1 -From s4_q1a`.

## 2026-11-16: P4b: S4 on all dev data done (K = 128 check still running); gate 9.8: something holds → P5
- **Run:** `run_s4_dev.ps1` with the code of commit `a536192`, in the order of the hand-over prompt. Steps and times (UTC): `l2_data` and `s4_scores` 08:2x; `s4_q1a` 08:27 (91 s); `s4_decomp` K = 64, six arms, SAE on the GPU, 08:28 to 10:15 (6,423 s; GPU capped at 210 MHz); then `s4_q1b_u` to `s4_report` 10:16 to 10:41. **Order change (logged):** after K = 64, I stopped the sequential runner and ran the K = 128 check alone in parallel with the later steps, which read only K = 64 outputs (results unchanged; it saves about 3 hours). **No script was changed after its full-dev result was seen.**
- **Results:** `imgsae/exploratory/lung_l2/RESULTS_S4_dev.md` (text + tables generated from `results/s4/*.json` by `s4_report.py`). Main points: check P1 passed (0.991, 0.997); known groups explain 31% (1 year) and 33% (6 years) of Sybil's logit; raw units is the only valid arm at K = 64 (the SAE fails V1 and V3; PCA and ICA fail V3 and V4; NMF and k-means fail V1 and V3) and is the primary arm; z-fix lowers ℓ̄_1 by 0.33 [0.28, 0.37] in 924 stretched exams and moves 67% by ≥ 0.25 SD (U1b qualifies); kernel pairs shift +0.03, flag change 1.8%; U1a and U3 fail gate 9.8 (intervals include 1); U2 R-fixed has the wrong sign and R-learned is near-automatic; F+I is not better than F; dev AUROC of Sybil is optimistic (C6; 0.969 against 0.914 on test in L1).
- **Gate 9.8** (`results/s4/s4_gate_dev.json`, `.md`): 354 candidates, 344 hold (all with the valid raw arm; none partly seen); leak check passed (no S4 script names the L1 test-score file or a test file); data check passed (all rows dev). About 320 of the holding candidates are near-automatic (raw units are Sybil's own risk units; the false-alarm classes are defined by Sybil's score); they are not used as hypotheses. Meaningful holding candidates: z-fix magnitude and direction, kernel mean shift, Q1a group shares at 1 year, the T-family share, U adds to F and Sybil adds to F+I (both doubtful on test because of C6 and the L1 test result). **Decision: go to S5.**
- **Spend:** none (PC only).

## 2026-11-16: P5 done: S5 freeze; stopped for the lead's OK
- **Frozen family** (`imgsae/exploratory/lung_l2/HYPOTHESES_L2.md`; Holm, family-wise α = 0.05, one-sided; participant bootstrap 2,000 draws, seed 0; p from the Wald statistic with the bootstrap SD):
  - H1 z-fix moves the score: share of T5 exams with |Δℓ̄_6| ≥ 0.25 × 0.92957 > 0.30 (dev 0.670 [0.638, 0.701]; 924 exams, 424 participants; chance 0.98);
  - H2 z-fix lowers the score: mean Δℓ̄_1 < −0.10 (dev −0.326 [−0.366, −0.282]; chance 0.97);
  - H3 z-fix changes the τ90 flag: share > 0.05 (dev 0.0747 [0.0558, 0.0971]; chance 0.60);
  - H4 the kernel rarely changes the flag: share of T4 pairs < 0.05 (dev 0.018 [0.008, 0.030]; 500 pairs; chance 0.92);
  - H5 the 6 T-named raw-unit families carry > 0.03 of Var(ℓ̄_1) (dev 0.0505 [0.0501, 0.0509]; 7,336 exams, 2,492 participants; feature-based, valid arm raw units; chance 0.93).
  - None is partly seen. **Disclosed in the file:** the margins of H2 to H5 were set at S5 from dev; H3 and H4 failed the provisional margins of my S4 gate list (0.10, opposite direction for H4).
  - Considered and not frozen, with reasons: U1a and U3 (gate 9.8 failed), "U adds to F" and "Sybil adds to F+I" (doubtful on test given L1; reported at S6 as secondary), Q2 variables (small, confounded), near-automatic candidates.
- **Frozen files** (`results/s5/`, written by `s5_freeze.py`): `frozen_thresholds_L2.json` (τ90 = 0.017993675, SD reference 0.92957453, z-fix ≤ 0.65, hypotheses, Holm, bootstrap, fallbacks, secondary list, SHA-256 of all frozen files and inputs), `frozen_raw_arm_K64.npz` (the primary arm as plain numbers: no pickle needed), `frozen_families_raw_K64.json` (56 families, labels), `frozen_FI_params.json`, `frozen_combinations.json` (secondary only).
- **Frozen analysis** `s6_frozen_analysis.py`: checks the SHA-256 of the frozen files and of Sybil's head weights and calibrator first; refits nothing. **Dev as if test** (`results/s5/s6_dev_as_if_test.json`): all five statistics equal the S4 dev values exactly (difference 0.0); secondary references equal S4 too (Sybil 0.969 / 0.851; U3 table).
- **Two fixes before the final freeze commit:** (1) Python on Windows wrote the frozen JSON files with CRLF while git stores LF, so their SHA-256 would differ on another checkout: the files are now written with LF, and `results/s5/` is `-text` in `.gitattributes` (byte-exact). (2) `.gitignore` ignored `*.npz`, so the frozen dictionary was missing from the first freeze commit (`1b23e45`); an exception was added and it was committed (`c593005`).
- **Hash check:** all 20 files listed in `HYPOTHESES_L2.md` match commit `c593005` (SHA-256 of the committed content and git blob ids; 0 mismatches). SHA-256 of `HYPOTHESES_L2.md` at the freeze: `914a1d1e3156fcdbeab025b1f46c916e126fc53fbecf95988b736b63ec01a6a0`. **Final freeze commit: `c593005`.**
- **S6 run plan and money** (in the S5 file): shforghani2002 in December; order T1 → T2 → T4 → T3, all main runs with `--zfix-max 0.65` (T5 grows with its main tiers); fallbacks fixed; cost projection from the billed S3 rates ≈ $18.9 (≈ $20.8 with a 10% preemption reserve) against $22.30 available (task $23.30 left minus $1.00): below, no extra decision needed, thin margin.
- `docs/REVIEWER_BRIEF_L2.md` updated (file paths, hash check on Windows).
- **Not done (by the rules):** no test manifest, no test activation, no test image measure, no new outcome analysis of the L1 test scores. P6 not started.
- **Still running (dev only):** the K = 128 decomposition check (raw units valid; PCA and ICA not; NMF, k-means, SAE running). Its results will be added to `RESULTS_S4_dev.md`; they do not feed the freeze.
- **Stop:** waiting for the external reviewer's note and the lead's OK.

## 2026-11-16: K = 128 check finished (dev only; does not change the freeze)
- The K = 128 decomposition check finished (exit 0; local GPU, $0; log `imgsae_data/lung_l2/logs/s4_decomp_128.txt`). Code unchanged since `a536192`.
- **Result: raw units is again the only valid arm.** Raw: V1 to V4 pass, 102 families, 76 named (55 N, 26 mixed, 21 T).
- SAE: V1 **failed** (logit correlation 0.833 / 0.855; AUROC change −0.029 at 1 year), V3 passed (35 families, 24 named), V4 **failed** (label agreement between halves 0.25). At K = 64 the SAE failed V1 and V3 and passed V4. So the SAE is not valid at either size.
- PCA (3 families) and ICA (7): V3 and V4 **failed**. NMF (r 0.907; 10 families) and k-means (r 0.983; 0 families): V1, V3 and V4 **failed**.
- `results/s4/RESULTS_S4_dev_tables.md` regenerated; `RESULTS_S4_dev.md` updated (point 4, failed marks, K = 128 table). I also corrected point 4 and the failed-marks list for K = 64: NMF and k-means fail V4 as well (the table already showed it; the text had left it out).
- `HYPOTHESES_L2.md` cites only the raw K = 128 row (21 T families carrying 0.109), which was final before the freeze; it is unchanged, and so are all frozen files.
- Fixed in this log: the dollar amounts in the P5 money line above had been lost when the entry was written.
- **Stop:** still waiting for the external reviewer's note and the lead's OK.

## 2026-11-16: prompt for the S5 review
- At the lead's request: `docs/PROMPT_REVIEW_FABLE_S5.md`, a prompt for Fable 5.2 as the external reviewer. It asks for answers to items 1 to 8 of `docs/REVIEWER_BRIEF_L2.md` on the freeze commit `c593005`, and for a note in `docs/REVIEW_S5_L2.md`. It also lists the weak points I see. It forbids changing frozen files, opening test data, and any cloud command.
- GitHub checked: `origin/prostate-mri-plan` equals the local branch; every file in the brief is committed.

## 2026-11-16: S5 review done (external reviewer, Fable 5.2)
- Review in `docs/REVIEW_S5_L2.md`. **Verdict: approve with changes.** Hashes 22 of 22 match; the dev re-run of the frozen analysis is byte-identical to the committed file; no test data found; H1 to H4 approved; **H5 not approved as frozen** (any 6 of the 56 families pass its test; proposal H5′ = change of the T-family term under z-fix, dev −0.057 [−0.059, −0.054]); four small changes (wording of H3 and H4, `wald()` with SD 0, test-manifest script and its hash, three CRLF input hashes). No frozen file, analysis script, ledger or test data touched; no cloud command. Waiting for the lead's decision.

## 2026-11-16: project guide written (at the lead's request)
- `docs/PROJECT_GUIDE.md`: the whole project in simple words (all stages since 6 Nov, with what was wanted, done, went wrong, found, and what each result shows), the honest score against the lead's goal, the state and money today, the step-by-step plan from here (N0 to N9, each with who, cost, why, what to do, done-when, what can go wrong and its prevention, stop points), the rules for every agent, and how to publish. Writing only; no data, code, frozen file or ledger touched. **Next step: N0, the lead's decisions** (H5; the new freeze; S6 in December).

## 2026-11-16: the lead's decisions (step N0); extra dev feature step (NF, amendment A6) planned; execution prompt
- **Lead (quoted):** "we do allyou ask, put in planpush and give prompt to give opuse xhgih". Recorded as: (1) H5 is replaced by H5′; (2) OK for a new freeze commit with the four small changes of `docs/REVIEW_S5_L2.md`; (3) OK for S6 in December on `shforghani2002` with the thin margin and the frozen fallbacks. Still open with the lead: the request for an outside dataset (needs the lead's name) and the clinical co-author.
- **The lead also asked** whether more can be tested with features ("other method? other layer?"). **Reviewer's check (dev only, 2,500 random exams, no outcomes; exploratory; script outside the repository in the session's temporary folder):** effective dimensions per member: `h` 4.5 to 6.4, `pre` 2.5 to 3.7, `pooled` (1,536) 5.7 to 10.8; principal directions of member 0 that member 1 predicts on held-out exams with R² ≥ 0.5: `h` 6, `pre` 9, `pooled` 14.
- **Planned (not run):** step NF = amendment A6: the six arms and V1 to V4 on `pooled`; SAE sparsity check on `h` (k = 8, 16, 32); shared axes by multiset CCA at both layers; attention location (descriptive). Free, PC only, time limit 2026-11-26, code fixed before the full-dev run. An F result may enter the freeze only under gate 9.8, a random-choice test and no-refit computability on test; at most one, in place of H2. A6 is approved by the lead by pasting the execution prompt; the executor writes it into the protocol.
- **Written:** `docs/HANDOVER_PROMPT_L2_N1.md` (for Opus 5.5, xhigh: Step 0, step F, step N1, then stop). `docs/PROJECT_GUIDE.md` updated (N0 done, step NF, part 6b "why the feature tools failed and what more we can try").
- No frozen file, analysis script, ledger or test data touched; no cloud command.

## 2026-11-16 (night): step R started (rescue scouting of the feature extraction; reviewer session, Fable 5.2)
- The lead asked: before the Opus session, test more methods yourself and see if the extraction can be rescued. Dev only, PC only, no cloud, no money. No frozen file changed.
- Plan fixed before any full-dev run: `imgsae/exploratory/lung_l2/RESULTS_R_dev.md` (R1 shared axes; R2 SAE with k = 8, 16, 32; R3 K = 8 and 16; R4 layer `pooled`; R5 z-fix change only if R1 to R4 give something). Same marks V1 to V4 as S4, from the S4 code (imported, not changed).
- New scripts: `r1_arms.py`, `r2_shared.py`. Code test on 600 and 1,500 dev exams: runs; saved logits reproduced from `h` and from `pooled` within 1e-6.
- Scouting simplification: V2 on fewer members (it was never the failing mark). SAE fits on the GPU (CPU needs about 7 minutes per fit).
- Independence note: the reviewer now also does analysis work; the re-check N2 must say this for anything from step R.

### Step R, note 1 (2026-11-16, night): first result of R1 for `h`, and one method added (R1b)
- R1 on `h` (whitened 30 PCs per member, multiset CCA): shuffle null gives 0 shared axes (largest null r 0.01). Real data: only 1 axis is shared at r >= 0.70 in both halves (2 in one half). That axis is NOT the risk score (r with the 6-year score 0.12). It is technical: "lung cut off in z" (r 0.98 with `lung_cut_z`, 0.85 with the number of real slices, 0.77 with z-stretch), technical variables explain 90% of it, same label in both halves. Held-out agreement between the five members: 0.977.
- Weak point of the R1 method (seen in the result): the whitening gives the small noisy PCs the same weight as the large ones, so the other in-sample axes do not hold on the other half (in-sample MAXVAR values 4.9, 4.75, 4.7; held-out r 0.40, 0.12, 0.82), and the risk axis is not kept (function kept r 0.86 and 0.12).
- **Added after seeing this (logged before it runs): R1b, `r3_joint.py`**: one joint dictionary for the whole ensemble (the five member vectors joined, z-scored, every unit counts by its variance). Arms: joint PCA and joint PCA + ICA rotation ("group ICA"). K = 4, 8, 12, 16, 32. Marks V1' to V4 at the ensemble level, thresholds unchanged (see the script header). Code test on 1,500 dev exams: runs.

### Step R, note 2 (2026-11-17): layer `pooled` gives shared axes; R5 done; R6 added
- R1 on `pooled`: 11 axes shared by all five members in both halves (12 and 11; held-out agreement 0.995 down to 0.71; shuffle null 0, largest 0.014). All 11 are found again when fitted on the other half (r 0.73 to 1.00). Names (same Shapley rule as S4): T 5, I 2, mixed 3, unnamed 1; naming repeats in the halves (median 0.76, label agreement 1.0). Only 1 axis is the risk axis (r -0.85). The 11 axes explain 94% of the variance of the mean logit. Function kept from the shared axes alone: r 0.95 (below the 0.98 mark).
- R5 (`r4_axes_audit.py`): the z-fix moves axis 0 (named "lung cut in z / number of real slices / z-stretch" from correlations only) by -2.74 SD [-2.77, -2.71]; 99.5% of D5 exams move by 0.5 SD or more. The kernel change does not move it (+0.009). So the name of this axis is confirmed by an intervention. Removal test: technical axes (0, 1, 2, 4, 10) set to the dev mean: the mean logit moves by 0.25 SD or more in 51% of exams, flags change in 4.3%, AUROC 0.969 -> 0.960 (1 y), 0.851 -> 0.843 (6 y). Random direction: median 0.6%, 95th percentile 5.6% of exams. Axis 0 alone: AUROC unchanged (0.970, 0.850).
- **Added after seeing this (logged before it runs): R6, `r5_repair.py`**: (1) repair test: with axis 0 (or the technical axes) set to the dev mean, how much of the z-fix effect on the score is left; baseline 200 random directions; (2) random-choice test for "the z-fix moves axis 0 by more than 1 SD" (2,000 random axes).
- R1b (`r3_joint.py`) on `h`: at most 2 to 3 shared features at any K. R3 on `h` (K = 8, 16): raw units valid again but 0 families are not copies of the risk score; PCA, ICA, NMF find 3 to 5 families and miss only V4. So `h` holds about 3 shared directions (risk, lung cut in z, one unnamed).

### Step R, note 3 (2026-11-17): R6 done (repair test); R7 added
- Check: with nothing removed the script reproduces S4 exactly (z-fix share 0.670, mean delta lbar_1 -0.326).
- Repair test, axis 0 ("z-geometry") set to the dev mean in every member: the mean z-fix shift of lbar_1 goes from -0.326 to +0.081 [0.042, 0.125] (200 random directions: -0.43 to -0.21, none near 0). The share of D5 exams that move by 0.25 SD or more goes from 0.670 to 0.550 [0.511, 0.588] (random directions: 0.61 to 0.72). AUROC on dev unchanged (1 y 0.9685 -> 0.9699; 6 y 0.8509 -> 0.8496). So one shared axis carries the whole systematic shift, but only a part of the exam-by-exam change. Removing all five technical axes is not better (0.578) and costs AUROC (0.960).
- Random-choice test for "the z-fix moves axis 0 by more than 1 SD": 6% of 2,000 random axes also move by 1 SD or more (largest 1.79). So a 1 SD margin would be near-automatic. Axis 0 moves by 2.74 SD; no random axis reaches 2 SD.
- SAE on `h`, K = 64, k = 16 (S4: k = 4): V1 0.978 / 0.977 (mark 0.98; AUROC change -0.007, fails), V3 9 families (16 needed, fails), V4 passes. Closer than k = 4, still not valid.
- `pooled`, raw units K = 64: 46 families, V1 fails (AUROC change at 6 y -0.009), V4 fails (0.66). `pooled` PCA K = 64: V1, V2, V4 pass; V3 fails (4 families).
- **Added after seeing this (logged before it runs): R7, `r6_candidate.py`**: gate numbers (9.8) and the random-choice test (2,000 random axes) for two possible hypotheses: C1 "the z-fix moves axis 0" (null -2.0 SD) and C2 "setting axis 0 to the dev mean removes at least 0.20 of the downward shift of lbar_1" (null +0.20).

### Step R, note 4 (2026-11-17): R7 done; results file written
- C1 "the z-fix moves axis 0": -2.740 SD [-2.765, -2.714], halves -2.763 / -2.718; proposed null -2.0; gate 9.8 passes; 0 of 2,000 random axes pass (largest -1.84).
- C2 "axis 0 carries the shift": [mean delta lbar_1 with axis 0 off] - [plain] = +0.408 [0.403, 0.412], halves 0.412 / 0.404; proposed null +0.20; gate 9.8 passes; 1 of 2,000 random axes passes (0.05%; largest 0.226).
- SAE on `h`, K = 64, k = 8: V1 0.826 / 0.824, 8 families: not valid. `pooled` ICA K = 64: 5 families, not valid. Joint dictionary on `pooled`: 3 to 4 shared features, V1' fails. Shared axes with 50 PCs: 16 in one half (the count depends on the number of PCs; 11 is the count at the pre-set 30).
- Results in plain words: `imgsae/exploratory/lung_l2/RESULTS_R_dev.md`. Still running: SAE k = 32 and the small-K and `pooled` SAE runs; remaining `pooled` arms.

### Step R, note 5 (2026-11-17): plan files updated
- `docs/HANDOVER_PROMPT_L2_N1.md` rewritten: STEP F is now "check step R, freeze the axes, H6" (no new discovery by the executor). Default: H6 enters and H2 stays (six hypotheses, Holm over six); the lead can choose five when pasting. This differs from the rule of 2026-11-16 ("in place of H2"); the reason is written at the top of the prompt.
- `docs/PROJECT_GUIDE.md` (part 6b end, part 7, steps NF and N1, open questions) and `STATUS.md` updated.

### Step R, note 6 (2026-11-17): more rows in; one setting added
- SAE on `h`, K = 64, k = 32: V1 0.884 / 0.847, 9 families: not valid. So V1 over k = 4, 8, 16, 32 is 0.72, 0.83, 0.978, 0.88: best at k = 16, never 0.98. (My chat message said "more active features keep more of the score"; that holds up to k = 16 only.)
- `pooled`, K = 16: PCA, ICA and NMF pass V2, V3 and V4 (4, 6, 7 families; naming 0.83 / 1.00, 0.81 / 0.83, 0.79 / 1.00) and fail V1 only on the AUROC change at 6 years (-0.0053, -0.0053, -0.0078; mark 0.005; r 0.993). Raw units K = 16: 15 families, all copies of the risk score, V1 and V4 fail. k-means: not valid. Joint dictionary on `pooled`, K = 16 and 32: 3 to 4 shared features (PCA), 0 to 2 (ICA): not valid.
- **Added after seeing this (logged before it runs): `pooled` with K = 24 and 32, all arms** (SAE with k = K/4). Reason: K = 16 fails V1 by a hair and K = 64 passes V1 but fails V3; a K in between may pass all four marks. This is tuning K after seeing results; any "valid" result from it carries that caveat.

### Step R, note 7 (2026-11-17): NMF valid at `pooled`, with a defect
- NMF on `pooled`, K = 64 (planned in R4 before any run): passes V1 (0.998 / 0.997), V2 (2 members), V3 (16 families; the mark is 16), V4 (0.81 / 0.90): valid. 14 of 16 families are not copies of the risk score. K = 24 and 32 (added, note 6): valid, 8 families each.
- Defect not covered by the four marks: the held-out reconstruction of the layer by NMF is R² -2.8 (PCA 0.81, SAE 0.75), because part 2 of `pooled` is negative in 49% of its values and NMF uses max(x, 0). NMF keeps the function, not the vector. Reported as supporting evidence only (its families show the same themes as the shared axes); no hypothesis from it.
- SAE near misses: `pooled` K = 64, k = 16: V1, V2, V4 pass, V3 12 of 16. `h` K = 16, k = 4 and k = 8: V1, V2, V3 pass, V4 fails (label agreement 0.67).
- Started: V2 on all five members for NMF `pooled` K = 64 (separate output folder `results/r/v2full/`).

### Step R2 (2026-11-17): more candidate hypotheses on dev; plan fixed before any run
- The lead asked: "in dev can we develop more interesting hypotheses? try the things we discussed? the harm? somehow using the form?"
- Plan (scripts `r7_more.py`, `r8_three.py`; headers hold the exact definitions), fixed before running:
  - **A. Real follow-up (natural experiment, outcome-free).** 4,837 pairs of consecutive yearly screens; in 215 the stretch status changes (146 stretched -> not, 69 not -> stretched; 56 on the same scanner model). OLS delta lbar_1 = a + b * delta stretched + c * delta F1 (the form's change). Statistic b; proposed null +0.10 (direction >), the H2 margin. Bootstrap, halves, 2,000 permutations. The same with axis 0 switched off (real-world version of H6). Sensitivity: same scanner model; both screens without cancer.
  - **B. Harm through false alarms, with the form (y1 = 0 only).** Sybil-only false alarms (Sybil flags, the form does not) in stretched against other exams; D5 main against z-fix. Missed cancers: counts and a power note.
  - **C. 3 of 5 members** (`r8_three.py`): shared axes for each set of 3 members; how many are new against the 11 five-member axes; naming of new ones seen in >= 2 sets. Exploratory only.
  - **D. Beyond the radiologist (outcome-free).** Residual of lbar_1 after the form (F1); share explained by the risk axis, the technical axes, the other axes; random-choice test with 2,000 sets of 5 random directions.
- Any candidate must meet the four conditions (gate 9.8, random-choice or permutation test, no refit on test, honest chance >= 0.5). At most the lead decides what enters; all is dev and exploratory.

### Step R2, results A, B, D (2026-11-17)
- A (real follow-up): b = +0.246 [0.134, 0.355], halves 0.222 / 0.272; axis 0 off: -0.094 [-0.208, 0.014]; axis 0 jumps 2.29 SD per stretch change; permutation 2.5% above +0.10. Same-model subset (56 changed pairs) +0.216 [-0.057, 0.471]. Candidate C3 (null +0.10), honest chance about 0.7.
- B (harm, with the form): no difference in false alarms (Sybil 10.9% vs 11.3%; Sybil-only 9.1% vs 7.6%, interval includes 0); z-fix reshuffles Sybil-only false alarms (80 -> 75; 31 lost, 26 new); misses 0 of 18 stretched. No harm hypothesis; harm through misses not testable (about 12 stretched 1-year cancers expected in test).
- D (beyond the form): technical axes explain 14% of Sybil's residual after the form, but 33% of random 5-direction sets do as well: near-automatic, descriptive only.
- C (3 of 5) running.

### Step R2, result C and plan files (2026-11-17)
- C (3 of 5 members): 11 to 13 shared axes per set of 3 (five members: 11); 12 new axis groups, 4 in >= 2 sets, all |r| <= 0.08 with the risk score and weakly named (one is kernel sharpness, in members 0/2/4 and 0/3/4 only). Not proposed.
- `docs/HANDOVER_PROMPT_L2_N1.md`: H7 (candidate C3) added as a default primary hypothesis (F4b), with a one-line opt-out for the lead; Holm over seven with the defaults. `docs/PROJECT_GUIDE.md` N1 item 7 and `STATUS.md` updated.

### Step R3 (2026-11-17): where Sybil looks (descriptive only; never a hypothesis); plan fixed before the run
- The lead asked whether we can show the nodule Sybil sees, and whether a stretched box cuts nodules off. Feasibility (dev): 5,069 recorded nodules with a slice number; 2.4% have a slice number above our series' image count; median relative position upper lobe 0.29, middle 0.53, lower 0.58 (numbering runs from the top: the mapping is usable). Nodules in the cut-off part of Sybil's box: stretched exams 8 of 588 (1.4%), other 0 of 4,359; of nodules >= 8 mm in stretched exams 2 of 112; in exams with cancer within 1 year: 1.
- Plan (`r9_attention.py` header): slice attention near the largest recorded nodule against shuffled nodule bins; in-plane attention on the nodule's side (lobe); orientation chosen on half A, reported on half B.

### Step R3 result and R3b added (2026-11-17)
- R3 (descriptive): slice attention within +-1 bin of the largest recorded nodule (held-out half B; box order 'reversed' and side 'patient right = image left' chosen on half A): cancer within 1 year 72% (38 exams; shuffled 26%, 97.5th 39%); no cancer >= 8 mm 51% (425; shuffled 22%); 4-8 mm 32% (1,033; shuffled 23%). Peak within 1 bin: 74%, 56%, 35%. In-plane attention on the nodule's lung side: 88% (cancer), 77% (>= 8 mm).
- **Added after seeing R3 (logged before it runs): R3b, `r10_att_harm.py`**: does the stretch move attention away from the nodule? (main stretched vs other; D5 main vs z-fix, paired). A harm proxy that needs nodules, not cancers.

### Step R3b result (2026-11-17)
- Code error found and fixed before reporting: `variant_dev_zfix.csv` repeats the main run's `resampled_T`; `r10_att_harm.py` now uses n_images x true spacing / 2.5 for the z-fix box.
- Naive: stretched 27% vs other 40% attention near the nodule; z-fix 27% -> 34% (+0.063 [0.038, 0.088]). Shuffled nodule positions (500 and 300 shuffles): z-fix +0.110; stretched 0.157 vs other 0.237. So the naive effect is geometry (a +-1-bin window covers more of the lung in a shorter box). Corrected excess: main 0.115 -> z-fix 0.068; stretched 0.114 vs other 0.160 (not comparable groups). No harm signal. Descriptive only; nothing proposed.
- `docs/HANDOVER_PROMPT_L2_N1.md`: harm estimates (T5 sensitivity and AUROC, main vs z-fix, with the detectable size stated before the test) and the attention check added as secondary items, on the lead's question.

### 2026-11-17: the lead's money decision (S6 in November)
- Live billing (read-only, 17 Nov): shforghani2002 $28.17 of $29.00 used ($0.83 left); armanfo $15.69 of $29.50 ($13.81 left; project $14.03); forghanishayan $5.02 of $29.50 (metered minus free storage; the lead's own deployed app, idle, 0 tasks).
- Lead: "i dont need any other account for my other works, so we can use them all".
- Ledger (`cloud/ledger.json`): account forghanishayan added (cap $29.50, project limit $20.00); armanfo project limit $17.00 -> $27.00. Project cap $72 and task budget lung_l2_audit ($23.30 left) unchanged. `budget.py status --profile forghanishayan` works (month used $5.02).
- Plan: S6 in November after the new freeze, the re-check and the lead's OK: armanfo smoke + T1 + T4 (about $8.1 with reserve); forghanishayan identity check, then T2 + T3 (about $13.2 with reserve). `docs/PROJECT_GUIDE.md` N4 and `docs/HANDOVER_PROMPT_L2_N1.md` updated.

### 2026-11-17: explanations file, CLAUDE.md, prompt final
- The lead asked for the day's explanations in one simple file so that every new Claude session knows how to talk to the lead: `docs/EXPLAINED_FOR_THE_LEAD.md` (Part A how to talk to the lead; Parts B to L the explanations). `CLAUDE.md` (new, root) points every session to it. Memory: lead-communication-style.
- Last step R runs: NMF `pooled` K = 64 with V2 on all five members stays valid; SAE `pooled` K = 64 not valid (k = 16: V3 12 of 16; k = 4: V1 and V3 fail). The remaining SAE runs (`pooled` K = 16, `h` K = 8) were stopped to free the PC; they cannot change the results.
- `docs/HANDOVER_PROMPT_L2_N1.md` final: H7 in Step 0 and A6; `r7_more.py`, `r9_attention.py` and the explanations file in the reading list; reruns of step R with `L2_S4_DATA` set to a scratch folder so the saved axes are not overwritten.

## 2026-11-17: executor session (Opus 5.5) started with `docs/HANDOVER_PROMPT_L2_N1.md`; the lead's OK recorded (Step 0)
- **Git check:** branch `prostate-mri-plan` at `f2eaaf9`, equal to `origin/prostate-mri-plan`; working tree clean.
- **The lead's OK (given by pasting the prompt, 2026-11-17):**
  1. H5 is replaced by H5′ (`docs/REVIEW_S5_L2.md`, "What I propose instead").
  2. A new freeze commit with the four small changes of the review: wording of H3 and H4 with the flag numbers; `wald()` with bootstrap SD 0; the test-list script and its hash; LF hashes of the three text inputs.
  3. S6 in November (changed 2026-11-17; lead: "i dont need any other account for my other works, so we can use them all"): `armanfo` (smoke, T1, T4) and `forghanishayan` (identity check, then T2, T3), as `docs/PROJECT_GUIDE.md` step N4. Not in this session. The S6 run plan with this split goes into the new hypothesis file.
  4. Amendment A6: the extra feature work on dev (steps R, R2, R3) is done; its results enter the freeze as H6 (candidate C2) and H7 (candidate C3), with C1 and the other axis numbers as secondary items.
- **The lead's choices on H2 and H7:** the prompt was pasted without the opt-out lines ("H6 replaces H2 …" or "H7 goes to the secondary list …"), so the defaults hold: **H6 enters, H2 stays, H7 enters. Seven primary hypotheses (H1, H2, H3, H4, H5′, H6, H7), Holm over seven.**
- Amendment A6 written into `docs/LUNG_L2_PROTOCOL.md` section 16a.
- Next: step F (check step R as an outsider; freeze the axes), then step N1, then stop.

## 2026-11-17: step F done (executor, first independent reader of step R): reruns reproduce; code read; axes frozen; H5′ moved to the secondary list by the lead
- **F1, reruns (dev, PC, free).** `r2_shared.py --layers pooled`, then `r4_axes_audit.py` and `r5_repair.py` in parallel, then `r6_candidate.py` and `r7_more.py` in parallel (4 BLAS threads each), with `L2_S4_DATA` set to a scratch folder so the saved axes were not overwritten (runner and logs in the session's scratch folder; 10:37 to 11:21; all exit 0, empty error logs). Outputs compared with `results/r/` field by field: **0 differences** in `r2_shared_pooled.json`, `r4_axes_audit_pooled.json`, `r5_repair_pooled.json`, `r6_candidate_pooled.json`, `r7_more_pooled.json` (run times ignored); `r2_axes_pooled.csv` and `r4_axes_pooled.csv` identical (max numeric difference 0.0). The scratch pickle equals the saved one (axis activations r = 1.0 for all 11 axes, max difference 0.0; PCA directions, scales and weights identical). The saved pickle is unchanged (SHA-256 `a93cc049…6ebb83bc` before and after).

| Number (dev) | Prompt | Rerun |
|---|---|---|
| shared axes in the two halves; shuffle null | 12, 11; 0 | 12, 11; 0, 0 |
| axis 0 under z-fix (SD) | −2.740 [−2.765, −2.714], halves −2.763 / −2.718 | same |
| axis 0 under kernel change (SD) | +0.009 | +0.009 |
| nothing removed: share ≥ 0.25 SD; mean Δℓ̄_1 | 0.670; −0.326 | 0.670; −0.326 |
| axis 0 removed: mean Δℓ̄_1; share; AUROC 1 y / 6 y | +0.081 [0.042, 0.125]; 0.550; 0.9699 / 0.8496 | same |
| C2 | +0.408 [0.403, 0.412], halves 0.412 / 0.404; random 1 of 2,000 above +0.20 | same (share 0.0005; largest 0.226) |
| C3 (`r7_more.py`) | b +0.246 [0.134, 0.355], halves 0.222 / 0.272; axis 0 off −0.094; 4,837 pairs, 215 changed; permutation 2.5% | same |

- **F2, code read as an outsider (findings).**
  1. `Shared.fit` / `variates` (`r2_shared.py`): the mean, SD, live mask, PCA directions, scales and MAXVAR weights all come from the fit rows; `variates()` only applies them, so the other half is untouched by the fit. Halves are participant folds (no person in both). The shuffle null permutes the exam order inside each member over all rows: a valid null. The held-out shared axes are the first 12 and 11 in eigenvalue order (no gaps), so "final = the first 11 axes of the all-dev fit" takes the same kind of axes; their own held-out agreement cannot be measured (fitted on all dev), but the half fits agree with them (stability r 0.73 to 1.00).
  2. `remove` (`r4_axes_audit.py`): an orthogonal projection in each member's whitened 30-PC space. The change of a member's vector is rank one (one fixed direction per member, scaled per exam); parts outside the 30 PCs are unchanged; after removal the axis variate is exactly 0, which is the dev mean (checked: 4e-15). Other axes move only by their overlap with axis 0 inside that member (MAXVAR member weights are not orthogonal within a member). So "only that one direction of each member's vector changes" is correct.
  3. D5 selection: the same rule (ratio of the main series ≤ 0.65, z-fix row present) and the same 924 exams, 424 participants in `s4_q1d.py`, `r4`, `r5`, `r6` and the new S6 code. The 8 dev exams with a recorded ratio of 0 have no z-fix row (the cloud job needs spacing > 0) and are outside D5.
  4. SD reference: axis SD = SD (ddof 0) of the mean-of-five activation over all 7,336 dev main exams, the same in `r4`, `r6`, `r7`; frozen as `axis_sd_dev`. ℓ̄_6 shares use the S4 reference 0.92957.
  5. The final axes are fitted on the dev **main** arrays only; `r2_shared.py` never loads the z-fix or pair arrays.
  6. **Edge case, not a code error:** `r7_more.py` applies "stretched = spacing/thickness ≤ 0.65" literally, so the 8 ratio-0 exams (every slice position recorded twice) count as stretched. 6 of them are physically stretched in Sybil's box (212 to 502 images at 2.5 mm, lung cut in z); 2 are small partial scans (60 and 68 images). 8 follow-up pairs touch them, 6 of them "changed". b = +0.246 as coded; **+0.227 [0.115, 0.336]** with ratio 0 counted as not stretched; +0.222 [0.118, 0.328] with those pairs removed. Gate 9.8 holds in all three (check script in the scratch folder). Decision: H7 keeps the rule as coded (the dev evidence and the lead's OK refer to it); the frozen file states how ratio 0 is counted, and the other count is a frozen secondary number.
  7. Halves: the repository uses two conventions (S4 draws the two folds on the subset's participants; step R draws them on all dev participants and restricts). Halves are reported, never tested. H5′ halves −0.0565 / −0.0567 use the S4 convention; C2 and C3 halves use the step R convention; the new S6 code reports halves of H5′, H6, H7 with the step R convention.
  8. The random-choice test of C2 uses random unit directions in each member's whitened 30-PC space, where every direction has unit dev variance: a fair comparison. Axis 0 was not chosen by the z-fix (it is the first MAXVAR axis); the hypothesis was chosen after its z-fix result was seen (disclosed in A6).
  - **No real error found in the step R code.** No step R script or `results/r/` file was changed.
- **F3, axes frozen.** New script `s5_axes_freeze.py` writes `results/s5/frozen_axes_pooled.npz` from the saved pickle: per member the dev mean and SD of `pooled`, live mask, the 30 PCA directions, the scales and the weights of the 11 axes; the dev SD and mean of each axis activation. Checks: activations from the file equal the pickle's (variates max difference 0.0, activation 9e-16); ℓ̄_1 from `pooled` through Sybil's `hidden_fc`, ReLU and head equals the saved logits within 2.6e-7; axis 0 is 0 after removal. SHA-256 of the file: `4ff8ade34829535e3d9251ad7e4c2397cb5647c6f4345e38fff1182a3f17da45`. The file, the script and `run_info/heads.npz` (holds `hidden_fc`) go into the hash table of the new freeze. `.gitignore` exception added for the file.
- **F5.** No search for new axes, features or hypotheses. The SAE and the other arms stay "not valid". Exploratory notes for after the test only: (a) under the z-fix the "mixed" raw-unit families move more per family than the T families (−0.0123 against −0.0094; N +0.0002); (b) H7's sensitivity to the ratio-0 exams (item 6).
- **N1 item 1, H5′ dev evidence** (`s5_h5prime_dev.py`, output `results/s5/s5_h5prime_dev.json`, SHA-256 `ed29c357…0804bead`): H5′ = **−0.0566 [−0.0590, −0.0541], halves −0.0565 / −0.0567** (as the review); N +0.005 [−0.013, +0.025]; mixed −0.197 [−0.206, −0.187]; residual −0.101 [−0.107, −0.094]; unreplicated +0.023; T carries 17.4% [16.0%, 19.2%] of the mean shift; the T term falls in 96% of exams. **Random-choice test: 59.7% of 20,000 random sets of 6 of the 56 families have a mean z-fix change below −0.02 (rule: under 5%); 12.6% fall at least as much as the T set; mean of random sets −0.027.** So H5′ is near-automatic, like H5. By the prompt's rule I stopped before freezing H5′ and asked the lead.
- **The lead's choice (2026-11-17, answer to the question in the session):** "Move H5′ to secondary (Recommended)". So the family is **six: H1, H2, H3, H4, H6, H7 (Holm over six)**; H5′ is reported as a secondary number with its failed random-choice test, never called confirmed.
- **Dry run of the new freeze code** (scratch copy of `results/s5/`, dev as if test): H1 to H4 identical to the first freeze (estimates, intervals, p, counts); old H5 share, secondary references, group shares and z-fix descriptives identical; H5′ equal to item 1; H6 = C2 and H7 = C3 to 10 digits, with their halves; C1, b with axis 0 off, axis-0 jump, same-model b, group means, share with axis 0 off and AUROC with axis 0 off all equal to step R. First-freeze frozen files stay byte-identical.
- Next: step N1 (the new freeze), then stop.

## 2026-11-17: step N1 done: second freeze, commit `c3578c3`; stopped for the re-check (N2) and the lead's OK (N3)
- **Family (Holm over six, one-sided, α = 0.05):** H1, H2, H3, H4 (statistics, populations, nulls and thresholds unchanged from `c593005`), **H6** (shared axis 0 of `pooled` carries the z-fix drop; null +0.20; dev +0.408 [0.403, 0.412]) and **H7** (real follow-up jump; null +0.10; dev +0.246 [0.134, 0.355]; **labelled "partly seen"**). H5 (first freeze) and H5′ are secondary numbers.
- **H7 "partly seen" (my decision under protocol 10, flagged for the re-check):** an approximate H7 (logit of the L1 published score instead of the member logits; stretch status from the public IDC metadata) could be computed from the L1 test scores, the form and public metadata. It never was: no L1 script reads spacing, thickness or stretch (checked by search); L1 post hoc saw only the overall T0 vs T1 correlation of the test logits (r = 0.61). It is the only partly-seen hypothesis, which protocol 10 allows, and every report labels it.
- **Changes in the freeze** (as `docs/REVIEW_S5_L2.md` and the lead's prompt): H4 renamed ("the kernel changes the flag in fewer than 5% of exams"); H3 worded with both flag directions; `wald()` returns p = 0 (right side of the null) or 1 when the bootstrap SD is 0; LF hashes of `l2_form_params.json`, `manifest_dev.csv`, `s4_families_dev_raw_K64.csv` in `frozen_thresholds_L2.json`; `tau90_s6` (90th percentile of s6 among dev baseline exams with y6 = 0: 0.12394902) for the harm estimates; new secondary items (flags in both directions; term changes; old H5; H5′; H6 and H7 details incl. the ratio-0 count; harm estimates with the detectable size; attention); the S6 run plan on `armanfo` (smoke → T1 → T4; about $7.4, $8.1 with reserve) and `forghanishayan` (identity check → T2 → T3; about $12.0, $13.2) with fallbacks.
- **New scripts:** `s5_axes_freeze.py` (step F), `s5_h5prime_dev.py` (step F), `s6_manifest_test.py` (test list; **run on dev only**: it reproduces `manifest_dev.csv` byte for byte, SHA-256 `8fe372a6…`, all 500 D4 pairs; `results/s6_manifest_devcheck.json`; it refuses `--root test` without `--lead-ok <freeze commit>`), `s6_attention.py` (step R3 method with the conventions frozen from dev; reproduces `r9_attention_dev.json` on half B, difference 0). Changed: `s5_freeze.py` (keeps unchanged first-freeze files byte-identical: `frozen_raw_arm_K64.npz`, families, FI parameters, combinations have the same hashes as at `c593005`), `s6_frozen_analysis.py`, `s5_hashes.py` (36 files + 3 PC inputs, incl. `heads.npz` for `hidden_fc` and the source pickle of the axes).
- **Dev as if test** (`results/s5/s6_dev_as_if_test.json`): H1 0.6699, H2 −0.3264, H3 0.0747, H4 0.018 — **identical to the first freeze** (estimates, intervals, p, counts); H6 +0.4078 [0.4032, 0.4121], halves 0.412 / 0.404 (= C2); H7 +0.2458 [0.1337, 0.3551], halves 0.222 / 0.272 (= C3); all six confirmed on dev (dev is not evidence for test). Secondary references, group shares and z-fix descriptives identical to the first freeze. H5′ secondary −0.0566 [−0.0590, −0.0541]. H7 "both screens without cancer" sensitivity (separate file, written after the primary output): +0.279 [0.171, 0.380] (= step R2). Harm on dev T5: 1-year cancers 16, main 16 of 16, z-fix 15 of 16; 6-year baseline 27, 16 of 27 in both. Attention on all dev exams: cancer within 1 year 71% near the nodule (shuffled 23%).
- **Checks:** all 39 rows of the hash table match commit `c3578c3` (SHA-256 and blob ids; PC inputs by file hash). SHA-256 of `HYPOTHESES_L2.md` at the freeze: `60b9e34bfd369ecedf957a978e4218cc22dad4f5fde2d89f0a975722865007e8`. The frozen analysis refuses a changed `frozen_axes_pooled.npz` (tested on a scratch copy). The S6 extraction saves `pooled` for the main and the z-fix runs (cloud job: the same saved keys for every variant; on dev `arrays_dev_zfix.npz` holds `pooled`).
- **Files:** `docs/PROMPT_REVIEW_S5b.md` (re-check prompt: it says that the reviewer of the first freeze did step R, so a fresh session must re-check); `docs/REVIEWER_BRIEF_L2.md` (paths; "at most five" now with A6); `docs/LUNG_L2_PROTOCOL.md` A6 (six hypotheses; amends the "at most five" rule of section 10); `docs/PROJECT_GUIDE.md` (N1 done, N2 next); `docs/EXPLAINED_FOR_THE_LEAD.md` (Part I update note).
- **Diff from `c593005`** also holds commits not made by this session: the step R files, the plan documents, and the ledger change of `96d3c12` (the lead's money decision). This session changed no ledger, no step R script and no `results/r/` file.
- **Not done (by the rules):** no test data opened, extracted, listed or analysed; the test-list script not run on test; no cloud command; no package installed. S6 not started.
- **Stop:** waiting for the re-check (N2, `docs/PROMPT_REVIEW_S5b.md`, a fresh session that did not do step R) and the lead's OK (N3).

## 2026-11-17: step N2 done: re-check of the second freeze `c3578c3` (fresh session, Opus 5.5); verdict approve with changes (four run rules; no new freeze needed)
- **Who:** a fresh Opus 5.5 session that did not do steps R to R3, the first review or the second freeze. Prompt: `docs/PROMPT_REVIEW_S5b.md`. Note: `docs/REVIEW_S5_L2.md`, section "Re-check of the second freeze (step N2), 2026-11-17".
- **Verdict: APPROVE WITH CHANGES.** The six hypotheses (H1, H2, H3, H4, H6, H7; Holm over six) can go to the test as frozen. The changes are four run rules for S6, to be written into the log with the lead's OK (N3); none changes a frozen file.
- **Checks (all dev or repository only; my scripts and outputs in the session's temporary folder):** 39 of 39 hash rows match at `c3578c3` and at HEAD (`results/s5/` byte-exact; PC inputs match; LF hashes of the three text inputs done). Dev as if test rerun: byte-identical to `s6_dev_as_if_test.json` and to the H7 sensitivity file; H1 to H4 equal `c593005`; H6 = C2 and H7 = C3 (difference 0.0). Frozen axes equal the pickle (0.0); a fresh `s5_axes_freeze.py` gives the same arrays; axes fitted on the 7,336 dev main exams only; `remove()` is rank one per member. H5′ rerun byte-identical; its random test is fair. Attention rerun byte-identical; half-B check against step R3: difference 0.0. Test-list dev check: byte-identical to `manifest_dev.csv` (`8fe372a6…`), all 500 pairs the same. Diff from `c593005`: only the listed and documented changes; H1 to H4 definitions and thresholds unchanged. `results/runs/` and the ledger hold no test run of L2; no test folder on the PC (names only).
- **Findings:** (1) Latent defect (also in the first freeze): a NaN estimate gives a NaN p, and `holm()` counts it as confirmed (tested on the two functions). The extraction checks G2b and G2c already catch NaN in Sybil's saved numbers; the remaining gap is a missing `ratio`, `F1` or `s1` in the test tables. (2) H6 is outside the six arms of protocol 9.4 and the shared axes fail V1 as a dictionary (r 0.95); V1 does not apply to H6 (it edits the real vector in one direction); A6 allows it; the report must say so. (3) H6 is near-certain if test scans behave like dev (98.5% of dev z-fix exams above the null one by one; every subgroup +0.36 to +0.42). (4) H7: honest chance about 0.6 (stated 0.65; both above 0.5); stable with extra adjustment for scanner, maker, kernel and thickness changes (+0.23 to +0.25); 195 of 215 changed dev pairs involve a GE scanner. (5) "Partly seen" for H7 is right: no L1 script reads spacing, thickness, stretch or kernel. (6) Step R was a wide dev search and H6's statistic was written after its result was seen (disclosed); this cannot make a false confirmation on the untouched test split, only a failure more likely. H7's statistic and null were committed before its result.
- **Run rules proposed for S6 (no new freeze):** (1) NaN guard: before the frozen analysis, G2b and G2c pass and no value is missing in `ratio`, `F1`, `s1` (main) and `v_l1`, `v_l6`, `s1` (z-fix, pair); else stop and ask the lead; a hypothesis with a non-finite estimate or p counts as "not evaluated". (2) `s6_attention.py` runs only after the frozen analysis output is committed. (3) Before N5: `git diff --stat c3578c3 HEAD` touches no hash-table file; `assemble_test.json` shows `form_params_sha256` `b4cba3aa…` (CRLF copy of `02ec7c2d…`); after N5: `check_max_abs_lbar1_from_pooled_minus_saved` ≤ 5e-3 (dev 2.6e-7), else H6 is not evaluated. (4) Wording for the report: H6 outside the 9.4 arms (A6), "at least 0.20 of the drop through axis 0"; H7 observational, mostly GE, partly seen; six hypotheses ≈ three findings.
- **The lead must decide (N3):** OK for the freeze `c3578c3` and for S6, naming the family of six in words; OK for the four run rules (reviewer's advice: as log rules, no new freeze; the other choice is a two-line code fix of `wald()` in a new freeze commit).
- **Not done (by the rules):** no test file opened, listed or analysed; test-list script not run on test; no new analysis of the L1 test scores; no cloud command; no frozen file, analysis script, `results/r/` file or ledger changed; no package installed. Only `docs/REVIEW_S5_L2.md` and this log are committed.
- **Stop:** waiting for the lead's OK (N3).

## 2026-11-17: step N3 done: the lead's OK for the freeze `c3578c3` and for S6; the four run rules of the re-check are now S6 rules (no new freeze)
- **The lead's words (2026-11-17, in the session):** "OK for the freeze c3578c3 and for S6, with the six hypotheses H1, H2, H3, H4, H6, H7 (Holm over six; H7 “partly seen”; H5 and H5′ secondary), and OK for the four run rules as log rules (no new freeze)."
- **How it came:** after a `/clear`, the lead pasted the N2 prompt again. The session (Opus 5.5) found N2 already done (`29096f9`, pushed) and did not repeat it. It explained the state in simple words and proposed the OK line. The lead stopped the repeated N2 request and sent the line unchanged.
- **Recorded as:**
  1. **OK for the freeze `c3578c3`.** Family of six: H1, H2, H3, H4, H6, H7; Holm over six, one-sided, α = 0.05; m stays 6 if a hypothesis is not evaluated. H7 is labelled "partly seen". H5 and H5′ are secondary numbers, never called confirmed.
  2. **OK for S6** (steps N4 to N6 of `docs/PROJECT_GUIDE.md`), by the frozen run plan on `armanfo` (smoke, T1, T4) and `forghanishayan` (identity check, T2, T3). Every launch goes through the guard; usage is checked before every launch; `MODAL_PROFILE` per command.
  3. **The four run rules below bind S6.** No new freeze commit; `wald()` stays as frozen.
- **Run rules for S6** (from `docs/REVIEW_S5_L2.md`, section "Re-check of the second freeze (step N2)", "Changes I propose"):
  1. **NaN guard.** Before `s6_frozen_analysis.py` runs on test: G2b and G2c pass on every file, and there is no missing value in `exams_test.csv` for the main exams (`ratio`, `F1`, `s1`) or in the z-fix and pair tables (`v_l1`, `v_l6`, `s1`). On dev all these counts are 0. If any count is not 0: stop and ask the lead. Reading rule: a hypothesis whose estimate or p is not a finite number counts as "not evaluated" (not confirmed), whatever the Holm column says.
  2. **Order of the analysis scripts.** `s6_frozen_analysis.py` runs first, and its output is committed before anyone reads it (N5). `s6_attention.py` runs only after that (N6).
  3. **Input checks.** Before N5: (a) `git diff --stat c3578c3 HEAD` touches no file of the hash table in `HYPOTHESES_L2.md`; (b) `assemble_test.json` shows `form_params_sha256` = `b4cba3aa14c79a2cc6a45a315348e289ada862fb7fce47cebb4b219af3826806` (the Windows CRLF copy of the frozen LF hash `02ec7c2dda14450ce06a9bc3b127d572ed9c8d6472cf37d550b68ec6283f8034`; the dev assembly `assemble_dev.json` shows the same CRLF value). After N5: `check_max_abs_lbar1_from_pooled_minus_saved` ≤ 5e-3 (the stop rule of `r1_arms.load`; dev 2.6e-7); if not, H6 counts as not evaluated.
  4. **Wording in the S6 report and the paper.** (a) H6 is a feature-level claim on shared axes, allowed by A6, outside the six arms of protocol 9.4; V1 does not apply because H6 edits Sybil's real vector in one direction; the marks that apply hold for axis 0. (b) H6 tests "at least 0.20 logit of the z-fix drop passes through axis 0", not the whole drop. (c) H7 is observational, mostly from GE scanners (195 of 215 changed dev pairs), and partly seen. (d) Six hypotheses are about three findings (z-fix, kernel, real follow-up).
- **Notes for the executor of N4:** the two-account order of the frozen run plan rules (the one-account order T1 → T2 → T4 → T3 in the guide's N4 item 5 is old, as the re-check noted). The `--lead-ok` guard of `s6_manifest_test.py` only checks that a value is given; this entry is the OK it refers to.
- **What this changes:** rule 1 of the guide ("the test split is closed until step N3 is logged") is now met. Step N4 may start.
- **Not done:** no test file opened, listed or analysed; the test-list script not run on test; no cloud command; no money spent; no frozen file, analysis script, `results/r/` file or ledger changed. This commit touches only `docs/EXECUTION_LOG.md`, `STATUS.md` and `docs/PROJECT_GUIDE.md` (none is in the hash table).
- **Next:** N4, the test extraction (about $19 to $21, cloud). The session told the lead it starts N4 only on a separate message from the lead, because it spends money.

## 2026-11-17: step N4 started (test extraction, S6 part 1): the lead's go; test list built; cloud job reads the test list
- **The lead's words (2026-11-17, about 21:05 UTC):** "start N4. i am going to sleep so don't bother me, do your job, fix error and if something bad happen make best decision and continue. Good Night. I expect best clean results with all things happen and how you mange in morning perfectly. give me my high impact result!" Recorded as: go for N4 to N6 (extraction, frozen analysis once, the pre-stated secondary and exploratory looks) without stops for questions; every rule of the guide, the protocol, the frozen run plan and the four N3 run rules still holds; any decision taken without the lead is logged here with its reason.
- **Item 1, usage (21:10 UTC, `budget.py status --no-log`):** `armanfo` month $15.69 of $29.50, this project $14.03 of $27.00; `forghanishayan` month $5.02 of $29.50, this project $0 of $20.00; task `lung_l2_audit` $21.70 of $45; project $47.09 of $72. No open run. App check: no other app with running containers on either account (`forghanishayan`: the lead's deployed app `ucla-nnunet…` has 0 tasks; it is never touched). No volume named `imgsae-nlst-l2` exists on `forghanishayan`; the job creates it (the lead's volumes there are not touched).
- **Item 2, test list:** `s6_manifest_test.py … results --root test --lead-ok c3578c3` → `results/manifest_test.csv` (SHA-256 `677ad5487520baa1e7169e43459a7751dc6e6f87c8e7946f3e10d018caf723c0`) and `results/s6_manifest_test.json`. 6,715 split-file test series, all found in IDC, 0 participant mismatches, 0 duplicate participant-years; T1 2,279, T2 2,243, T3 2,193, T4 500 (pairs available 1,160; GE 215, Siemens 211, Philips 58, Toshiba 16); 2,347 participants; 745 main series with IDC ratio ≤ 0.65 (z-fix expected); 615.9 GB to download. No outcome read (keys of `exams` only).
- **Item 3, code changes for test (no analysis file changed):**
  - `cloud/l2_sybil_modal.py`: root `test` reads `manifest_test.csv`, every other root reads `manifest_dev.csv` as before (both files are in the image); a tier must belong to its root (T* only with root test); `smoke` takes `tier` and `root` (defaults D1 and dev, so the dev smoke is unchanged) and writes `run_info/smoke_<root>.json` for a root other than dev (the dev record `smoke.json` is kept); its result file is `results/runs/smoke_test__<account>.json`. Checked locally: T1 rows 0 to 2, T1 2,279, T2 2,243, T3 2,193, T4 500 (variant pair), D1 300 (dev) and 20 (rep) as before; mixed tier and root refused.
  - `cloud/drive_runs.py` and `cloud/launch.py`: `forghanishayan` added to the PC copy folders (`imgsae_data/lung_l2_vol_forghanishayan`) and to the app check (A4: no other app of the lead may have running containers before a launch). Needed because the driver refused an account without a PC folder.
- **Plan for the runs (decided now, by the frozen run plan and protocol 7 "≤ 4 containers at once across both accounts"):** (1) smoke on both accounts at the same time (1 container each): demo case plus T1 rows 0 to 2 into root test; the identity check compares the two accounts on those 3 series (and the z-fix variant if made) and the checkpoint and head hashes; (2) then one unattended chain, accounts one after the other (4 containers each, never both at once): `armanfo` T1 → T4, then `forghanishayan` T2 → T3; `--zfix-max 0.65`, root test; billing reconciled 70 minutes after the end. If the identity check fails, `forghanishayan` is not used (frozen fallback: H7 not evaluated; the z-fix hypotheses use T1).
