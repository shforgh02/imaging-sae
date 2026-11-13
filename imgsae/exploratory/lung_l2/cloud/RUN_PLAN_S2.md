# Run plan S2 (pilot) for the executing agent

Protocol: `docs/LUNG_L2_PROTOCOL.md` (sections 7, 8, 12, 14). You run commands; you do not change code, thresholds, manifests or the order of steps. If anything is unclear or fails, stop and report.

## Fixed facts
- Working directory `D:\Shayan`. Shell: PowerShell. Set `$env:PYTHONUTF8 = "1"` in every command that calls `modal` or the miniconda python.
- Modal client: `C:\Users\Arman\miniconda3\Scripts\modal.exe` (call it as `modal`; if not on PATH use the full path). Python for collect and budget: `C:\Users\Arman\miniconda3\python.exe`.
- App `imgsae-lung-l2`, volume `imgsae-nlst-l2`, ledger task `lung_l2_audit`, account `shforghani2002` (the current Modal profile; do not switch profiles).
- Every launch goes through the guard inside `launch.py` (it prints three tests; if it prints `BUDGET CHECK FAILED`, nothing was launched: stop and report).

## Never
- Touch any other volume or app (`vs-workspace-data`, `vs-radiomics-vol`, `picai-dataset-vol`, `lupi-data`, `imgsae-nlst-l1` or anything else). No `modal volume rm`, `modal volume delete`, `modal app stop` on anything except, if a run hangs past its hard timeout plus 15 minutes, the app `imgsae-lung-l2` itself (report it).
- Switch Modal profile or use the second account. Use the `reserve` budget. Edit `ledger.json` by hand.
- Edit any `.py`, `.csv` or protocol file. Delete the volume `imgsae-nlst-l2` (it is reused in S3).
- Commit or push to git (the main session does that).

## Billing lag rule
Modal's billing lags up to about an hour. Before each launch, if a run was closed less than 90 minutes ago, add its measured cost (from the collect output) to the guard's printed month figure by hand. If that sum plus the new worst case exceeds 29.00, wait and re-check; report if it still does not fit.

## Steps
0. **Preflight (free).**
   - `& C:\Users\Arman\miniconda3\python.exe imgsae\exploratory\p1b_sanity\cloud\budget.py status` → record `month_used_usd`, `project_committed_usd`, `open_worst_usd` (must be 0).
   - `modal volume list` and `modal app list` → record the names. `imgsae-nlst-l2` should not exist yet (it is created by the first run).
1. **Smoke (≈ $0.2).**
   - `modal run --detach imgsae/exploratory/lung_l2/cloud/l2_sybil_modal.py --step smoke --n-series 3 --zfix-max 0.95`
   - Note the run id printed (`lung_l2_audit-NNN`). Wait: `powershell -File imgsae\exploratory\lung_l2\cloud\wait_collect.ps1 -Rid <rid> -MaxMinutes 40`
   - Open `imgsae/exploratory/lung_l2/results/runs/smoke.json`. Continue only if: `demo_pass` true, `demo_maxdiff` ≤ 0.005, `demo_volume_equal_serie` true, every `bench.verify[*].equal` true, `bench.errors` empty, `bench.n_done` = 3. Otherwise stop and report the file.
   - The first launch builds the image (several minutes); that is expected.
2. **Pilot main run (≈ $0.7; guard worst case ≈ $3.91).**
   - `modal run --detach imgsae/exploratory/lung_l2/cloud/l2_sybil_modal.py --step run --tier D1 --lo 0 --hi 300 --nshard 4 --timeout-min 30 --zfix-max 0.95 --root dev`
   - Wait with `wait_collect.ps1 -Rid <rid> -MaxMinutes 70`. Result file `results/runs/run_dev_D1_0_300.json`.
   - Count errors over the four calls (`calls[*].errors`). If more than 15 (5% of 300): stop and report.
   - If some rows were not reached (sum of `n_done` + errors < `n_todo`), relaunch the same command once (done series are skipped); report it.
3. **Repeat and L4 runs (≈ $0.3; launch both, one after the other, then wait for both).**
   - `modal run --detach imgsae/exploratory/lung_l2/cloud/l2_sybil_modal.py --step run --tier D1 --lo 0 --hi 20 --nshard 1 --timeout-min 15 --zfix-max 0.95 --root rep`
   - `modal run --detach imgsae/exploratory/lung_l2/cloud/l2_sybil_modal.py --step run_l4 --tier D1 --lo 0 --hi 50 --nshard 1 --timeout-min 25 --zfix-max 0.95 --root l4`
   - Wait for each with `wait_collect.ps1` (MaxMinutes 40).
4. **Copy to the PC (free).**
   - `modal volume get imgsae-nlst-l2 l2 D:\Shayan\imgsae_data\lung_l2_vol` (creates `D:\Shayan\imgsae_data\lung_l2_vol\l2\...`). If the command needs `--force` because the folder exists, use it.
   - `modal volume ls imgsae-nlst-l2 l2/dev/main`, `.../l2/dev/zfix`, `.../l2/rep/main`, `.../l2/l4/main`, `.../l2/dev/errors` and compare the counts with the local folders (`(Get-ChildItem <dir> -Filter *.json).Count`).
5. **Final status (free).** `budget.py status` again; `modal volume list`.

## Report (short, to the main session)
- Each run id, command, wall time, collect result, measured cost from collect; the guard's three tests at each launch.
- Smoke: `demo_maxdiff`, verify results.
- Pilot: n_done, errors (with the first few messages), mean seconds from the result files.
- File counts on the volume and on the PC, per folder.
- Budget status before and after; volume and app lists before and after.
- Anything unexpected, and anything you did not do.
