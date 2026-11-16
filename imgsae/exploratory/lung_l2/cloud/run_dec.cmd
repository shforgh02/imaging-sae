@echo off
rem SUPERSEDED on 2026-11-15 by run_s3rest.cmd (amendment A4: D2, D3, D4 on account armanfo in November). Kept for the record only.
rem It now fails on purpose: drive_plan.py requires --profile and a matching MODAL_PROFILE. Do not schedule it.
rem Unattended December run of S3: tiers D2 (year-1), D3 (year-2), D4 (500 kernel partners), in that order; started by the
rem scheduled task "imgsae_l2_dec" (2026-12-01 01:00 local, or as soon as the PC is on after that). See drive_runs.py / drive_plan.py.
cd /d D:\Shayan
set PYTHONUTF8=1
C:\Users\Arman\miniconda3\python.exe imgsae\exploratory\lung_l2\cloud\drive_plan.py --tag dec --plan D2:0:2442,D3:0:2410,D4:0:500 --zfix-max 0.65 --root dev >> imgsae\exploratory\lung_l2\logs\driver_dec.stdout.txt 2>&1
