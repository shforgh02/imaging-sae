# Run plan S3, rest (tiers D2, D3, D4 on account `armanfo`, November 2026)

Plan step P3 of `docs/PLAN_L2_NEXT_v1.md`. Protocol `docs/LUNG_L2_PROTOCOL.md` sections 7, 12, 14 and 16a (amendments A4: second account; A5: the unattended driver runs the paid jobs). Same fixed facts and "Never" list as `RUN_PLAN_S2.md`; the billing lag rule is now inside the guard (`budget.py`, 2026-11-16). Nobody changes code, thresholds, manifests or the order of steps while it runs.

## Goal
Score into root `dev` on account `armanfo`:
- D2 (year-1 screens) rows 0 to 2,441 (2,442 series), with z-fix variants for spacing/thickness ≤ 0.65;
- D3 (year-2 screens) rows 0 to 2,409 (2,410 series), with z-fix variants likewise;
- D4 (500 soft-kernel partners of D1 exams) rows 0 to 499 (variant `pair`; no z-fix).

## Gate before the start (done)
- P1 passed (guard per account; unit test 26 of 26; dry run on armanfo).
- P2 passed (smoke and identity on armanfo equal to the main account, max difference 0.0; `results/p2_identity.json`).

## How it runs
- Wrapper `cloud/run_s3rest.cmd`, started as a one-time Windows scheduled task `imgsae_l2_s3rest` that starts at once. The wrapper sets `MODAL_PROFILE=armanfo` itself (a scheduled task does not inherit it from a chat session) and runs:
  `drive_plan.py --profile armanfo --tag arm --plan D2:0:2442,D3:0:2410,D4:0:500 --zfix-max 0.65 --root dev`
- For each tier, `drive_runs.Driver` (at most 4 launches per tier):
  1. app check on armanfo: no other app may have running containers; else wait 30 min and look again; stop after 2 hours;
  2. prechecks = the guard's four tests without logging, at nshard 4, then 3, 2, 1 (task ≤ $45; project ≤ $72; armanfo month: Modal billing + lag (this project's runs on armanfo closed in the last 90 min) + open worst cases + worst case ≤ $29.50; this project on armanfo + worst case ≤ $17.00);
  3. `modal run --detach --profile armanfo ... --step run --tier <T> --lo <lo> --hi <hi> --nshard <n> --timeout-min 60 --zfix-max 0.65 --root dev` (T4, 4 CPU, 16 GiB; hard timeout 60 min, soft stop 55 min; the guard runs again inside, logged);
  4. collect every 2 minutes, for at most 80 minutes after the launch;
  5. relaunch the same range while rows remain (done rows are skipped by the job).
- A tier starts only if the previous one finished cleanly (status `finished`, no rows left).
- At the end (or at any stop) the armanfo volume is copied to `D:\Shayan\imgsae_data\lung_l2_vol_armanfo\l2\` (that account's own PC folder; never into the main copy).
- 70 minutes after the plan ends, `reconcile_billing.py --profile armanfo` writes Modal's billed cost into the ledger (runs 038 onward on armanfo).

## Stop rules (the driver stops itself; nothing is retried by hand before the reason is known)
- the guard refuses at every nshard; the app check fails for 2 hours;
- a call fails (collect exit 4) or collect refuses (exit 6);
- errors > 5% of the rows attempted in a launch;
- a call is not finished 80 minutes after its launch (the ledger run stays open at its worst case);
- any crash of the driver.

## Expected
- Rows: 5,352 main/pair series plus about 600 z-fix variants.
- Cost: about $14 (billed D1 rate $0.0026 per row incl. z-fix: D1 rows 300 to 2,483 billed $5.72). About 6 hours.
- The $17 limit will likely make the last launch (D4) use 3 containers instead of 4.
- After P3: this project on armanfo about $14.4 of $17; task about $22 of $45; S3 total about $20 of its $22.00 allocation (stop rule +10%: $24.20).

## While it runs (the chat session)
- Only `budget.py status --profile armanfo --no-log`; no `reconcile_billing.py`; no other Modal launch on either account (≤ 4 containers at once over both accounts).
- Logs: `lung_l2/logs/driver_arm_D2.log`, `driver_arm_D3.log`, `driver_arm_D4.log`, `driver_arm_end.log`; state files `driver_arm_<tier>.json`; stdout `driver_arm.stdout.txt`.

## After it ends (P3 items 5 to 10)
- Read the logs and state files; if it stopped early, find the reason and report before any restart.
- Merge `lung_l2_vol_armanfo\l2\dev` into `lung_l2_vol\l2\dev` with `p3_merge.py` (never overwrites; new files must be D2, D3, D4 rows of the manifest or their z-fix files; existing files are compared and skipped if equal; anything else stops the merge).
- Checks: failures < 5% per tier; G2b and G2c on every new file; file counts = manifest rows minus logged failures → `results/s3_checks_all.json`.
- Reconcile armanfo billing (if the driver's own reconcile did not run). Delete no cloud volume (lead, 2026-11-15).
