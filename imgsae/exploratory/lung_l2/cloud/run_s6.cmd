@echo off
rem S6 part 1 (step N4, 17 Nov 2026): the frozen run plan of HYPOTHESES_L2.md on two accounts, one after the other
rem (protocol 7: at most 4 containers at once across both accounts). armanfo: T1 then T4; forghanishayan: T2 then T3.
rem Smoke and identity check were done before (results/s6_identity_accounts.json, gate passed). Every launch goes through the guard
rem (drive_runs.py); done rows are skipped by the job. Started by the one-time scheduled task "imgsae_l2_s6". The account is set here
rem because a scheduled task does not inherit MODAL_PROFILE. Billing is reconciled 70 minutes after the end.
cd /d D:\Shayan
set PYTHONUTF8=1
set LOG=imgsae\exploratory\lung_l2\logs\driver_s6.stdout.txt
echo %DATE% %TIME% run_s6 start >> %LOG%
set MODAL_PROFILE=armanfo
C:\Users\Arman\miniconda3\python.exe imgsae\exploratory\lung_l2\cloud\drive_plan.py --profile armanfo --tag s6arm --plan T1:0:2279,T4:0:500 --zfix-max 0.65 --root test --max-launches 6 --no-reconcile >> %LOG% 2>&1
C:\Users\Arman\miniconda3\python.exe imgsae\exploratory\lung_l2\cloud\wait_idle.py --profile armanfo --max-min 90 >> %LOG% 2>&1
set MODAL_PROFILE=forghanishayan
C:\Users\Arman\miniconda3\python.exe imgsae\exploratory\lung_l2\cloud\drive_plan.py --profile forghanishayan --tag s6fgs --plan T2:0:2243,T3:0:2193 --zfix-max 0.65 --root test --max-launches 6 --no-reconcile >> %LOG% 2>&1
echo %DATE% %TIME% run_s6 drivers done; reconcile in 70 min >> %LOG%
powershell -NoProfile -Command "Start-Sleep -Seconds 4200"
set MODAL_PROFILE=armanfo
C:\Users\Arman\miniconda3\python.exe imgsae\exploratory\lung_l2\cloud\reconcile_billing.py --profile armanfo >> %LOG% 2>&1
set MODAL_PROFILE=forghanishayan
C:\Users\Arman\miniconda3\python.exe imgsae\exploratory\lung_l2\cloud\reconcile_billing.py --profile forghanishayan >> %LOG% 2>&1
echo %DATE% %TIME% run_s6 end >> %LOG%
