@echo off
rem O2 main runs (docs/O2_PLAN.md with amendment A1; from 1 December 2026). NOT started by any scheduled task: the lead or the session
rem starts it by hand, AFTER (1) usage on all three accounts shows the December month near $0 (budget.py status --profile P --no-log),
rem (2) the smoke on each account (section 2 of the plan) and (3) the identity gate printed PASS:
rem   python imgsae\exploratory\lung_l2\o2_identity_smoke.py D:\Shayan\imgsae_data\lung_l2_vol\l2,D:\Shayan\imgsae_data\lung_l2_vol_armanfo\l2,D:\Shayan\imgsae_data\lung_l2_vol_forghanishayan\l2 imgsae\exploratory\lung_l2\results\o2\o2_identity_smoke.json
rem Accounts one after the other (protocol 7: at most 4 containers at once). Rows are half-open (--lo/--hi of the job): U1 0-2149 and 2149-4298, U2 0-811.
rem Every launch goes through the guard (drive_plan.py -> drive_runs.py); done rows are skipped by the job. Billing reconciled 70 min after the end, task o2_unseen.
cd /d D:\Shayan
set PYTHONUTF8=1
set LOG=imgsae\exploratory\lung_l2\logs\driver_o2.stdout.txt
echo %DATE% %TIME% run_o2 start >> %LOG%
set MODAL_PROFILE=armanfo
C:\Users\Arman\miniconda3\python.exe imgsae\exploratory\lung_l2\cloud\drive_plan.py --profile armanfo --tag o2arm --plan U1:0:2149 --zfix-max 0.65 --root unseen --max-launches 6 --no-reconcile >> %LOG% 2>&1
C:\Users\Arman\miniconda3\python.exe imgsae\exploratory\lung_l2\cloud\wait_idle.py --profile armanfo --max-min 90 >> %LOG% 2>&1
set MODAL_PROFILE=forghanishayan
C:\Users\Arman\miniconda3\python.exe imgsae\exploratory\lung_l2\cloud\drive_plan.py --profile forghanishayan --tag o2fgs --plan U1:2149:4298 --zfix-max 0.65 --root unseen --max-launches 6 --no-reconcile >> %LOG% 2>&1
C:\Users\Arman\miniconda3\python.exe imgsae\exploratory\lung_l2\cloud\wait_idle.py --profile forghanishayan --max-min 90 >> %LOG% 2>&1
set MODAL_PROFILE=shforghani2002
C:\Users\Arman\miniconda3\python.exe imgsae\exploratory\lung_l2\cloud\drive_plan.py --profile shforghani2002 --tag o2shf --plan U2:0:811 --zfix-max 0.65 --root unseen --max-launches 6 --no-reconcile >> %LOG% 2>&1
echo %DATE% %TIME% run_o2 drivers done; reconcile in 70 min >> %LOG%
powershell -NoProfile -Command "Start-Sleep -Seconds 4200"
set MODAL_PROFILE=armanfo
C:\Users\Arman\miniconda3\python.exe imgsae\exploratory\lung_l2\cloud\reconcile_billing.py --profile armanfo --task o2_unseen >> %LOG% 2>&1
set MODAL_PROFILE=forghanishayan
C:\Users\Arman\miniconda3\python.exe imgsae\exploratory\lung_l2\cloud\reconcile_billing.py --profile forghanishayan --task o2_unseen >> %LOG% 2>&1
set MODAL_PROFILE=shforghani2002
C:\Users\Arman\miniconda3\python.exe imgsae\exploratory\lung_l2\cloud\reconcile_billing.py --profile shforghani2002 --task o2_unseen >> %LOG% 2>&1
echo %DATE% %TIME% run_o2 end >> %LOG%
