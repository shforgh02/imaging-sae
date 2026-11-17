"""Robust Modal launch for the lung L2 jobs (same pattern as lung_l1/cloud/launch.py).
Pattern: [app check on armanfo] -> budget check -> open ledger run -> fn.spawn() -> write lung_l2/logs/runs/<rid>.json -> return at once.
The local client never waits on the call, so a client error cannot cancel the cloud job (with `modal run --detach`, spawned calls keep
running). Collect later with `collect.py <rid>` (reads the call's result, saves it, closes the ledger run from the measured container
minutes).
Accounts (amendment A4): `profile` is the Modal profile the calling `modal run` process uses (its own --profile option, which sets
MODAL_PROFILE). It is checked against Modal's active profile in this process, passed to the guard (per-account month test), stored in
the ledger run and in the run record, and used again by collect.py. Never `modal profile activate`.
"""
import json
import os
import sys
import time
from pathlib import Path

L2 = Path(__file__).resolve().parents[1]; ROOT = Path(r"D:\Shayan"); RUNS = L2 / "logs" / "runs"
sys.path.insert(0, str(ROOT / "imgsae" / "exploratory" / "p1b_sanity" / "cloud"))
import budget as B  # noqa: E402

IMAGE_USD = 0.10
APP_CHECK_PROFILES = ("armanfo", "forghanishayan")   # A4: the lead's other work on these accounts must not be running (forghanishayan: S6, 17 Nov)


def client_profile():
    """the profile this process's Modal client uses; must be set explicitly (MODAL_PROFILE, set by `modal run --profile P`)."""
    import modal.config as MC
    env = os.environ.get("MODAL_PROFILE", "")
    if not env: raise SystemExit("REFUSED: no Modal profile given (use `modal run --profile <account> ...`)")
    if MC._profile != env: raise SystemExit(f"REFUSED: Modal client profile {MC._profile!r} differs from MODAL_PROFILE {env!r}")
    return env


def _pre(task, worst, profile):
    if profile in APP_CHECK_PROFILES:
        ok, busy = B.app_check(profile)
        print(f"app check {profile}: {'ok' if ok else 'BUSY'} {json.dumps(busy)}")
        if not ok: raise SystemExit(f"APP CHECK FAILED on {profile} - not launching: {json.dumps(busy)[:300]}")
    ok, rep = B.check(task, worst, profile); print(json.dumps(rep, indent=1))
    if not ok: raise SystemExit(f"BUDGET CHECK FAILED - not launching (worst case ${worst:.2f}, account {profile})")


def launch_many(fn, args_list, task, app, job, timeout_min, gpu, cpu, mem_gib, result_name=None, profile=None):
    """several spawned calls (containers in parallel) under ONE ledger run; worst case = n x (timeout + start) x rate + image."""
    n = len(args_list); worst = B.worst_case(n, timeout_min, gpu, cpu, mem_gib) + IMAGE_USD; rate = B.rate_h(gpu, cpu, mem_gib)
    _pre(task, worst, profile)
    rid = B.open_run(task, worst, dict(app=app, jobs=[f"{job}{a}" for a in args_list], timeout_min=timeout_min, gpu=gpu, cpu=cpu, mem_gib=mem_gib, launch="spawn"), profile=profile)
    calls = [fn.spawn(*a) for a in args_list]
    rec = dict(rid=rid, task=task, profile=profile, app=app, job=job, call_ids=[c.object_id for c in calls], rate_h=rate, timeout_min=timeout_min,
               worst_usd=worst, launched=time.strftime("%Y-%m-%dT%H:%M:%S"), result_name=result_name)
    RUNS.mkdir(parents=True, exist_ok=True); (RUNS / f"{rid}.json").write_text(json.dumps(rec, indent=1))
    print(f"SPAWNED {rid}: {n} calls on {profile}, worst case ${worst:.2f}. Collect with: python imgsae/exploratory/lung_l2/cloud/collect.py {rid} --profile {profile}")
    return rid


def launch(fn, task, app, job, timeout_min, gpu, cpu, mem_gib, args=(), result_name=None, profile=None):
    worst = B.worst_case(1, timeout_min, gpu, cpu, mem_gib) + IMAGE_USD; rate = B.rate_h(gpu, cpu, mem_gib)
    _pre(task, worst, profile)
    rid = B.open_run(task, worst, dict(app=app, jobs=[job], timeout_min=timeout_min, gpu=gpu, cpu=cpu, mem_gib=mem_gib, launch="spawn"), profile=profile)
    call = fn.spawn(*args)
    rec = dict(rid=rid, task=task, profile=profile, app=app, job=job, call_id=call.object_id, rate_h=rate, timeout_min=timeout_min, worst_usd=worst,
               launched=time.strftime("%Y-%m-%dT%H:%M:%S"), result_name=result_name)
    RUNS.mkdir(parents=True, exist_ok=True); (RUNS / f"{rid}.json").write_text(json.dumps(rec, indent=1))
    print(f"SPAWNED {rid}: call {call.object_id} on {profile}, worst case ${worst:.2f}. Collect with: python imgsae/exploratory/lung_l2/cloud/collect.py {rid} --profile {profile}")
    return rid
