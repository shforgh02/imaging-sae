# imgsae: Phase 1 runbook (lean plan v1) — Windows laptop (RTX 3050 4 GB, CUDA)

Plan: `D:\Shayan\docs\IMAGING_SAE_LEAN_v1.md`. Deviation log: `D:\Shayan\docs\EXECUTION_LOG.md`.
Status / handover: `D:\Shayan\STATUS.md`.

## Layout
```
D:\Shayan\
  docs\            plan, protocol draft, EXECUTION_LOG.md, DECISION_MEMO_P1.md (written at the end)
  imgsae\          code (this folder): imgsae\ package, scripts\, tests\, data\ (locked subject lists + results in data\p1\), logs\
  imgsae_data\totalseg\   TotalSegmentator scans (downloaded; not code)
  sae-groundtruth\ frozen reference package for the equivalence test (must be copied here)
```

## Start Phase 1 (one command, when the GPU is free)
Plug the laptop into power. From PowerShell:
```
cd D:\Shayan\imgsae
powershell -File scripts\run_phase1.ps1
```
- The launcher refuses to start if another program runs compute on the GPU (one GPU job at a time). `-Force` overrides.
- **Progress:** `Get-Content logs\phase1.log -Tail 20` (one line per step; each step also has its own log in `logs\`).
- **Status:** `powershell -File scripts\run_phase1.ps1 -Status`
- **Finished when** `logs\phase1.log` ends with `PHASE1 DONE`, or with a `STOP ...` line naming the gate that failed.
- **Resume:** run the same command again. Finished steps are skipped (markers in `data\p1\steps\`); encodes and fetches skip existing files.
- The driver blocks Windows sleep while it runs. Closing the lid may still suspend the laptop depending on power settings.

## Steps and what they decide
1. **fetch** (`scripts/fetch_subset.py`): the 150 development scans by HTTP range from the Hugging Face mirror, CRC32-verified against the zip index (3.84 GB).
2. **tests:** bitwise equivalence with saegt (needs `D:\Shayan\sae-groundtruth`), plus the planted-truth unit gates.
3. **engineering gate E** (`scripts/p1_d2_engineering.py`): CT-FM timing and memory on the GPU in fp16, CPU fp32 parity ≥ 0.995, seam ≥ 0.95.
   Spacing rule: 1.0 mm if the projected encode is ≤ 16 h, otherwise 1.5 mm. Rule and ETA logged in `data/p1/spacing.json`.
4. **encode** (`scripts/p1_encode.py`): per-scan token table plus CT-FM and random-init CT-FM features → `data/p1/scans/`. Watchdog 12 GB; `SPILL` warning above VRAM.
5. **assemble** (`scripts/p1_assemble.py`): rows, the 43-group atlas, eligibility, adjacency, s\*, n_eff, M\* and k → `data/p1/{rows.npz, concepts.json}`.
6. **probe**, gate S (`scripts/p1_probe.py`): dense vs reference probes → `data/p1/gates.json`.
7. **perturb** (×3): 20 scans re-encoded with half-token shift, +50% noise and +20 HU → `data/p1/perturb/`.
8. **fit** (`scripts/p1_fit.py`): 10 methods × J = 3 patient-grouped half replicates → `data/p1/fit/*.csv`, `summary.json`.
9. **decide** (`scripts/p1_decide.py`): the pre-written decision table → `D:\Shayan\docs\DECISION_MEMO_P1.md` and `data/p1/decision.json`.

## Environment
`.venv` = uv, CPython 3.11.15, torch 2.10 + CUDA 12.6, monai 1.6.1, nibabel, SimpleITK, scikit-learn, pandas, safetensors, huggingface_hub.
Recreate:
```
uv venv .venv --python 3.11
uv pip install --python .venv\Scripts\python.exe "torch==2.10.*" --index-url https://download.pytorch.org/whl/cu126
uv pip install --python .venv\Scripts\python.exe numpy scipy scikit-learn pandas nibabel SimpleITK monai==1.6.1 safetensors huggingface_hub psutil
```
Manual runs of single scripts: `.venv\Scripts\python scripts\<name>.py ...` with `$env:PYTHONUTF8='1'`.

## Expected time
Known after gate E (the driver prints the projected encode time). Mac-era estimate: 150 scans × 2 encoders at 1–3 min each (5–15 h);
SAE fits 3–5 h; probes and baselines about 1 h CPU.
