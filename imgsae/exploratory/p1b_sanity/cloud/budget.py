"""Modal spending guard (user rule, 2026-11-09; two accounts since 2026-11-15, lung L2 amendment A4). Every task has its own budget
(ledger.json 'budgets'); every Modal account has its own monthly cap (ledger.json 'accounts'). A launch on account (Modal profile) P goes
ahead only if all tests pass:
  1. task: the task's committed cost (all accounts) + this launch's worst case <= the task's budget;
  2. project: all committed costs (all accounts) + worst case <= project_cap_usd (72.00, lead, 2026-11-13). Committed = measured cost
     (or billed, if larger) for closed runs; worst case for open runs;
  3. month, per account: P's workspace usage this month that the free credit pays for (`modal billing summary --profile P`: metered
     cost minus free storage; it includes the user's other apps on P) + the cost of this project's runs on P closed in the last
     90 minutes (billing lag rule; billing lags by up to about an hour) + open worst cases on P + worst case <= P's cap;
  4. project limit on an account, if the ledger has '<P>_project_limit_usd' (now only armanfo, 17.00, lead 2026-11-15): this project's
     runs on P (all time, worst case for open runs; equals November 2026 for armanfo) + worst case <= that limit.
A profile that is not in 'accounts' is refused. Worst case = containers x (timeout + START_MIN) x hourly rate (GPU + CPU cores + memory
GiB; rates from `modal billing rates`, 2026-11-09). Modal kills a call at its timeout, so the worst case is a hard bound per launch.
Ledger writes are atomic (temporary file, then replace) and serialised by a lock file, because a driver and a chat session may both
write. `status` has a no-log mode (--no-log) that writes nothing.
Ledger times are UTC: Python's clock on this PC reads UTC (the user variable TZ=America/New_York is not understood by the Windows C
runtime; scheduled tasks see it too), and Modal's billing report hours are UTC too.
usage (miniconda python, which has the modal client):
  python budget.py status --profile armanfo --no-log  |  python budget.py worst --n 12 --timeout-min 15
"""
import argparse
import contextlib
import json
import os
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent; LEDGER = HERE / "ledger.json"
MODAL = r"C:\Users\Arman\miniconda3\Scripts\modal.exe"
RATES = dict(cpu_core_h=0.0473, mem_gib_h=0.008,
             gpu_h={"T4": 0.59, "L4": 0.80, "A10G": 1.10, "L40S": 1.95, "A100-40GB": 2.10, "A100-80GB": 2.50, "H100": 3.95})
START_MIN = 3.0  # per-container allowance for start-up and data loading before the function's own clock starts
LAG_MIN = 90     # billing lag rule: runs closed within this many minutes are added to Modal's month figure
OWN_APPS = ("imgsae-lung-l2",)   # this project's app; app_check ignores it


def rate_h(gpu, cpu, mem_gib):
    return (RATES["gpu_h"][gpu] if gpu else 0.0) + cpu * RATES["cpu_core_h"] + mem_gib * RATES["mem_gib_h"]


def worst_case(n, timeout_min, gpu="L4", cpu=4, mem_gib=16):
    return n * (timeout_min + START_MIN) / 60 * rate_h(gpu, cpu, mem_gib)


# ------------------------------------------------------------------ ledger file
def load():
    with open(LEDGER, encoding="utf-8") as f: return json.load(f)


def save(L):
    """atomic: write a temporary file next to the ledger, then replace it (a crash or a second writer never leaves half a file)."""
    tmp = LEDGER.with_name(f"{LEDGER.name}.tmp{os.getpid()}")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(L, f, indent=1); f.flush(); os.fsync(f.fileno())
    for _ in range(100):
        try: os.replace(tmp, LEDGER); return
        except PermissionError: time.sleep(0.1)   # Windows: a reader may hold the file open for a moment
    raise RuntimeError(f"could not replace {LEDGER}; new content left in {tmp}")


@contextlib.contextmanager
def locked(wait_s=120, stale_s=300):
    """serialise read-modify-write of the ledger across processes (lock file created with O_EXCL; a lock older than stale_s is from a
    killed writer and is removed)."""
    lk = LEDGER.with_name(LEDGER.name + ".lock"); t0 = time.time()
    while True:
        try:
            fd = os.open(lk, os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.write(fd, str(os.getpid()).encode()); os.close(fd); break
        except FileExistsError:
            try:
                if time.time() - lk.stat().st_mtime > stale_s: lk.unlink(missing_ok=True); continue
            except FileNotFoundError: continue
            if time.time() - t0 > wait_s: raise RuntimeError(f"ledger lock {lk} busy for {wait_s} s")
            time.sleep(0.2)
    try: yield
    finally: lk.unlink(missing_ok=True)


# ------------------------------------------------------------------ accounts
def need_profile(L, profile):
    acc = L.get("accounts") or {}
    if not profile or profile not in acc:
        raise ValueError(f"Modal profile {profile!r} is not in the ledger's accounts {sorted(acc)}: refused")
    return profile


def account_cap(L, profile):
    return float(L["accounts"][need_profile(L, profile)]["cap_usd"])


def account_project_limit(L, profile):
    v = L.get(f"{profile}_project_limit_usd"); return None if v is None else float(v)


def run_profile(r):
    if not r.get("profile"): raise ValueError(f"ledger run {r.get('id')} has no profile")
    return r["profile"]


def month_used(profile):
    """this month's workspace cost on that account that draws on the free credit (metered cost minus the free-storage allowance)."""
    out = subprocess.run([MODAL, "billing", "summary", "--json", "--profile", profile], capture_output=True, text=True, timeout=180,
                         env={**os.environ, "PYTHONUTF8": "1", "MODAL_PROFILE": profile})
    if out.returncode: raise RuntimeError(f"modal billing summary ({profile}) failed: " + out.stderr[-500:])
    s = json.loads(out.stdout); return float(s["metered_cost"]) + float(s["adjustments"]["free_storage"])  # free_storage is negative


def app_check(profile):
    """A4: (ok, busy) where busy lists the OTHER apps on that account that have running containers, in every environment.
    `modal app list --json` fields (modal 1.5.5, modal/cli/app.py list_): app_id, description, state, tasks (= n_running_tasks, a string),
    created_at, stopped_at. Rule: no app other than this project's (description in OWN_APPS) may have tasks > 0. Any read error -> not ok."""
    env = {**os.environ, "PYTHONUTF8": "1", "MODAL_PROFILE": profile}; busy = []
    try:
        p = subprocess.run([MODAL, "environment", "list", "--json", "--profile", profile], capture_output=True, text=True, timeout=120, env=env)
        envs = [e["name"] for e in json.loads(p.stdout[p.stdout.find("["):])] if p.returncode == 0 else None
        if not envs: return False, [f"environment list failed: {(p.stderr or p.stdout)[-300:]}"]
        for e in envs:
            p = subprocess.run([MODAL, "app", "list", "--json", "--env", e, "--profile", profile], capture_output=True, text=True, timeout=120, env=env)
            if p.returncode: return False, [f"app list ({e}) failed: {p.stderr[-300:]}"]
            for a in json.loads(p.stdout[p.stdout.find("["):]):
                if a.get("description") in OWN_APPS: continue
                try: n = int(str(a.get("tasks", "")).strip())
                except ValueError: n = -1   # unreadable -> counted as busy
                if n != 0: busy.append(dict(env=e, app_id=a.get("app_id"), description=a.get("description"), state=a.get("state"), tasks=a.get("tasks")))
    except Exception as ex:
        return False, [f"app check error: {ex!r}"[:300]]
    return not busy, busy


# ------------------------------------------------------------------ costs and tests
def run_cost(r):
    return r["worst_usd"] if r.get("closed") is None else max(r.get("measured_usd") or 0.0, r.get("billed_usd") or 0.0)


def lag_extra(L, profile, now=None):
    """billing lag rule: cost of this project's runs on that account closed in the last LAG_MIN minutes (same clock as the ledger's
    time.strftime stamps)."""
    cut = (now or datetime.now()) - timedelta(minutes=LAG_MIN)
    return sum(run_cost(r) for r in L["runs"] if r.get("closed") and run_profile(r) == profile and datetime.fromisoformat(r["closed"]) > cut)


def status(L=None, log_check=True, profile=None):
    L = L or load(); profile = need_profile(L, profile); m = month_used(profile); per = {t: 0.0 for t in L["budgets"]}
    for r in L["runs"]: per[r["task"]] = per.get(r["task"], 0.0) + run_cost(r)
    opn = [r for r in L["runs"] if r.get("closed") is None]
    ow = sum(r["worst_usd"] for r in opn if run_profile(r) == profile); ow_all = sum(r["worst_usd"] for r in opn)
    on_acct = sum(run_cost(r) for r in L["runs"] if run_profile(r) == profile)
    s = dict(time=time.strftime("%Y-%m-%dT%H:%M:%S"), profile=profile, month_used_usd=round(m, 4), open_worst_usd=round(ow, 4),
             lag_usd=round(lag_extra(L, profile), 4), open_worst_all_accounts_usd=round(ow_all, 4), project_committed_usd=round(sum(per.values()), 4),
             per_task_usd={t: round(v, 4) for t, v in per.items()}, cap_usd=account_cap(L, profile),
             project_cap_usd=L.get("project_cap_usd", L["cap_usd"]), project_on_account_usd=round(on_acct, 4),
             project_on_account_limit_usd=account_project_limit(L, profile))
    if log_check:
        with locked():
            L2 = load(); L2["checks"].append({k: s[k] for k in ("time", "profile", "month_used_usd", "open_worst_usd", "lag_usd", "project_committed_usd")}); save(L2)
    return s


def evaluate(task, worst, profile, log_check=False):
    """(ok, report) for launching `worst` dollars of worst-case work under `task` on account `profile`."""
    L = load(); s = status(L, log_check=log_check, profile=profile); cap = s["cap_usd"]; pcap = s["project_cap_usd"]
    b = L["budgets"][task]; t = s["per_task_usd"].get(task, 0.0)
    tests = {f"task {task}: {t:.2f} + {worst:.2f} <= {b:.2f}": t + worst <= b,
             f"project: {s['project_committed_usd']:.2f} + {worst:.2f} <= {pcap:.2f}": s["project_committed_usd"] + worst <= pcap,
             f"month {profile} (Modal billing): {s['month_used_usd']:.2f} + lag {s['lag_usd']:.2f} + open {s['open_worst_usd']:.2f} + {worst:.2f} <= {cap:.2f}":
                 s["month_used_usd"] + s["lag_usd"] + s["open_worst_usd"] + worst <= cap}
    lim = s["project_on_account_limit_usd"]
    if lim is not None:
        tests[f"project on {profile}: {s['project_on_account_usd']:.2f} + {worst:.2f} <= {lim:.2f}"] = s["project_on_account_usd"] + worst <= lim
    return all(tests.values()), dict(status=s, tests=tests)


def check(task, worst, profile=None):
    """the guard before a launch (logs a 'checks' entry)."""
    return evaluate(task, worst, profile, log_check=True)


def open_run(task, worst, info, profile=None):
    with locked():
        L = load(); need_profile(L, profile); rid = f"{task}-{len(L['runs']) + 1:03d}"
        L["runs"].append(dict(id=rid, task=task, profile=profile, opened=time.strftime("%Y-%m-%dT%H:%M:%S"), worst_usd=round(worst, 4), info=info, closed=None))
        save(L)
    return rid


def close_run(rid, measured, note=""):
    with locked():
        L = load(); hit = [r for r in L["runs"] if r["id"] == rid]
        if not hit: raise KeyError(f"no ledger run {rid}")
        for r in hit: r.update(closed=time.strftime("%Y-%m-%dT%H:%M:%S"), measured_usd=round(measured, 4), note=note)
        save(L)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=("status", "worst")); ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--timeout-min", type=float, default=15); ap.add_argument("--gpu", default="L4"); ap.add_argument("--cpu", type=float, default=4)
    ap.add_argument("--mem-gib", type=float, default=16); ap.add_argument("--profile", help="Modal profile (account); required for status")
    ap.add_argument("--no-log", action="store_true", help="status only: write nothing into the ledger"); a = ap.parse_args()
    if a.cmd == "worst": print(f"worst case ${worst_case(a.n, a.timeout_min, a.gpu, a.cpu, a.mem_gib):.2f}"); return
    L = load(); s = status(L, log_check=not a.no_log, profile=a.profile); print(json.dumps(s, indent=1))
    print("budgets:", json.dumps(L["budgets"]), "| sum", sum(L["budgets"].values()), "| account caps",
          {k: v["cap_usd"] for k, v in L["accounts"].items()}, "| project cap", L.get("project_cap_usd", L["cap_usd"]))


if __name__ == "__main__":
    main()
