"""Robust Modal launch for the lung L2 jobs (same pattern as lung_l1/cloud/launch.py).
Pattern: budget check -> open ledger run -> fn.spawn() -> write lung_l2/logs/runs/<rid>.json -> return at once. The local client never
waits on the call, so a client error cannot cancel the cloud job (with `modal run --detach`, spawned calls keep running).
Collect later with `collect.py <rid>` (reads the call's result, saves it, closes the ledger run from the measured container minutes).
"""
import json
import sys
import time
from pathlib import Path

L2 = Path(__file__).resolve().parents[1]; ROOT = Path(r"D:\Shayan"); RUNS = L2 / "logs" / "runs"
sys.path.insert(0, str(ROOT / "imgsae" / "exploratory" / "p1b_sanity" / "cloud"))
import budget as B  # noqa: E402

IMAGE_USD = 0.10


def launch_many(fn, args_list, task, app, job, timeout_min, gpu, cpu, mem_gib, result_name=None):
    """several spawned calls (containers in parallel) under ONE ledger run; worst case = n x (timeout + start) x rate + image."""
    n = len(args_list); worst = B.worst_case(n, timeout_min, gpu, cpu, mem_gib) + IMAGE_USD; rate = B.rate_h(gpu, cpu, mem_gib)
    ok, rep = B.check(task, worst); print(json.dumps(rep, indent=1))
    if not ok: raise SystemExit(f"BUDGET CHECK FAILED - not launching (worst case ${worst:.2f})")
    rid = B.open_run(task, worst, dict(app=app, jobs=[f"{job}{a}" for a in args_list], timeout_min=timeout_min, gpu=gpu, cpu=cpu, mem_gib=mem_gib, launch="spawn"))
    calls = [fn.spawn(*a) for a in args_list]
    rec = dict(rid=rid, task=task, app=app, job=job, call_ids=[c.object_id for c in calls], rate_h=rate, timeout_min=timeout_min, worst_usd=worst,
               launched=time.strftime("%Y-%m-%dT%H:%M:%S"), result_name=result_name)
    RUNS.mkdir(parents=True, exist_ok=True); (RUNS / f"{rid}.json").write_text(json.dumps(rec, indent=1))
    print(f"SPAWNED {rid}: {n} calls, worst case ${worst:.2f}. Collect with: python imgsae/exploratory/lung_l2/cloud/collect.py {rid}")
    return rid


def launch(fn, task, app, job, timeout_min, gpu, cpu, mem_gib, args=(), result_name=None):
    worst = B.worst_case(1, timeout_min, gpu, cpu, mem_gib) + IMAGE_USD; rate = B.rate_h(gpu, cpu, mem_gib)
    ok, rep = B.check(task, worst); print(json.dumps(rep, indent=1))
    if not ok: raise SystemExit(f"BUDGET CHECK FAILED - not launching (worst case ${worst:.2f})")
    rid = B.open_run(task, worst, dict(app=app, jobs=[job], timeout_min=timeout_min, gpu=gpu, cpu=cpu, mem_gib=mem_gib, launch="spawn"))
    call = fn.spawn(*args)
    rec = dict(rid=rid, task=task, app=app, job=job, call_id=call.object_id, rate_h=rate, timeout_min=timeout_min, worst_usd=worst,
               launched=time.strftime("%Y-%m-%dT%H:%M:%S"), result_name=result_name)
    RUNS.mkdir(parents=True, exist_ok=True); (RUNS / f"{rid}.json").write_text(json.dumps(rec, indent=1))
    print(f"SPAWNED {rid}: call {call.object_id}, worst case ${worst:.2f}. Collect with: python imgsae/exploratory/lung_l2/cloud/collect.py {rid}")
    return rid
