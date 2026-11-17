"""Wait until this project's app (imgsae-lung-l2) has no running container on one account (S6, 17 Nov). Used between the two accounts of
run_s6.cmd, so the protocol rule "<= 4 containers at once across both accounts" also holds if a call of the first account ran late (for
example after a Modal preemption restart). Read-only: `modal app list --json` in every environment. Polls every 2 minutes; gives up
after --max-min minutes (exit 1; the chain then goes on, because the late call is bounded by its own 60-minute timeout).
usage (miniconda python): python wait_idle.py --profile armanfo [--max-min 90]
"""
import argparse
import json
import os
import subprocess
import time
from datetime import datetime

MODAL = r"C:\Users\Arman\miniconda3\Scripts\modal.exe"; OWN = "imgsae-lung-l2"


def own_tasks(profile):
    env = {**os.environ, "PYTHONUTF8": "1", "MODAL_PROFILE": profile}
    p = subprocess.run([MODAL, "environment", "list", "--json", "--profile", profile], capture_output=True, text=True, timeout=120, env=env)
    envs = [e["name"] for e in json.loads(p.stdout[p.stdout.find("["):])]; n = 0
    for e in envs:
        q = subprocess.run([MODAL, "app", "list", "--json", "--env", e, "--profile", profile], capture_output=True, text=True, timeout=120, env=env)
        for a in json.loads(q.stdout[q.stdout.find("["):]):
            if a.get("description") == OWN: n += int(str(a.get("tasks", "0")).strip() or 0)
    return n


ap = argparse.ArgumentParser(); ap.add_argument("--profile", required=True); ap.add_argument("--max-min", type=float, default=90); a = ap.parse_args()
t0 = time.time()
while True:
    try: n = own_tasks(a.profile)
    except Exception as e: n = -1; print(f"{datetime.now():%Y-%m-%dT%H:%M:%S} read error {e!r}"[:300], flush=True)
    print(f"{datetime.now():%Y-%m-%dT%H:%M:%S} {a.profile}: {OWN} running containers {n}", flush=True)
    if n == 0: raise SystemExit(0)
    if time.time() - t0 > a.max_min * 60: raise SystemExit(1)
    time.sleep(120)
