@echo off
rem P3 restart (2026-11-16) after the first driver stopped by its 80-minute rule: a Modal preemption made shard 1 of run 042 (D3)
rem restart and finish late. Same run plan (RUN_PLAN_S3_REST.md); done rows are skipped by the job. Started by the one-time scheduled
rem task "imgsae_l2_s3rest_b". The account is set here because a scheduled task does not inherit MODAL_PROFILE.
cd /d D:\Shayan
set PYTHONUTF8=1
set MODAL_PROFILE=armanfo
C:\Users\Arman\miniconda3\python.exe imgsae\exploratory\lung_l2\cloud\drive_plan.py --profile armanfo --tag arm2 --plan D3:0:2410,D4:0:500 --zfix-max 0.65 --root dev >> imgsae\exploratory\lung_l2\logs\driver_arm2.stdout.txt 2>&1
