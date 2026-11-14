# Run plan S3, part 1 (tier D1, November 2026) for the executing agent

Protocol: `docs/LUNG_L2_PROTOCOL.md` (sections 7, 12, 14, 16a). Same fixed facts, "Never" list and billing lag rule as in `RUN_PLAN_S2.md` (read its sections "Fixed facts", "Never" and "Billing lag rule" first; they apply unchanged). You do not change code, thresholds, manifests or the order of steps.

## Goal
Score D1 rows 300 to 2,483 (2,184 baseline dev series; rows 0 to 299 are done) into root `dev`, as far as the November month check allows. Rows already done are skipped by the job, so relaunching the same range is safe.

## Steps
0. **Preflight (free).** `budget.py status` (record month, project, open = must be 0). `modal volume list`, `modal app list`.
1. **Launch A (guard worst case about $3.91).**
   `modal run --detach imgsae/exploratory/lung_l2/cloud/l2_sybil_modal.py --step run --tier D1 --lo 300 --hi 2484 --nshard 4 --timeout-min 60 --zfix-max 0.65 --root dev`
   Wait: `powershell -File imgsae\exploratory\lung_l2\cloud\wait_collect.ps1 -Rid <rid> -MaxMinutes 80`. Expected: about 1,500 series done in 55 minutes, the rest not reached.
   Stop and report if errors in the four calls sum to more than 5% of the rows attempted (`n_done` + errors), or collect exits 4.
2. **Launch B, only if rows remain.** Apply the billing lag rule (add the measured cost of launch A by hand if it closed less than 90 minutes ago). Then try the same command with `--nshard 4`; if the guard refuses, try `--nshard 3`, then `--nshard 2`, then `--nshard 1` (same other arguments). If even `--nshard 1` is refused, stop: November is used up; report how many rows remain.
   Wait and check as in step 1. Repeat step 2 at most twice more while rows remain and the guard allows.
3. **Copy to the PC (free).** `modal volume get imgsae-nlst-l2 l2 D:\Shayan\imgsae_data\lung_l2_vol --force`. Compare counts (`modal volume ls imgsae-nlst-l2 l2/dev/main`, `l2/dev/zfix`, `l2/dev/errors`) with the local folders.
4. **Final status (free).** `budget.py status`; `modal volume list`; `modal app list`.

## Report
Same format as S2: each run id, command, guard tests, wall time, collect result, measured cost; per-call `n_todo`, `n_done`, errors (first messages); rows of D1 still not done; file counts on the volume and on the PC; budget before and after; volume and app lists; anything unexpected or not done.
