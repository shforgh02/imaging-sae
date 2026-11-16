@echo off
rem P3 of docs/PLAN_L2_NEXT_v1.md: S3 tiers D2, D3, D4 on Modal account armanfo (amendment A4), unattended (amendment A5).
rem Started by the one-time scheduled task "imgsae_l2_s3rest". Run plan: RUN_PLAN_S3_REST.md. Stop rules: drive_runs.py / drive_plan.py.
rem The account is set here because a scheduled task does not inherit MODAL_PROFILE; the driver refuses to start if it differs.
cd /d D:\Shayan
set PYTHONUTF8=1
set MODAL_PROFILE=armanfo
C:\Users\Arman\miniconda3\python.exe imgsae\exploratory\lung_l2\cloud\drive_plan.py --profile armanfo --tag arm --plan D2:0:2442,D3:0:2410,D4:0:500 --zfix-max 0.65 --root dev >> imgsae\exploratory\lung_l2\logs\driver_arm.stdout.txt 2>&1
