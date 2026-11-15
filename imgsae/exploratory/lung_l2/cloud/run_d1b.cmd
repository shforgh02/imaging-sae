@echo off
rem Unattended finish of tier D1 (rows 300-2483; done rows are skipped), started by the scheduled task "imgsae_l2_d1b".
rem See drive_runs.py for the stop rules. Output also goes to lung_l2\logs\driver_d1b.log.
cd /d D:\Shayan
set PYTHONUTF8=1
C:\Users\Arman\miniconda3\python.exe imgsae\exploratory\lung_l2\cloud\drive_runs.py --tag d1b --tier D1 --lo 300 --hi 2484 --zfix-max 0.65 --root dev --nshards 4,3,2,1 --max-launches 3 --copy >> imgsae\exploratory\lung_l2\logs\driver_d1b.stdout.txt 2>&1
