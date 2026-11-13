"""Modal spending guard (user rule, 2026-11-09). Modal's free credit is $30 of compute per month. The whole project stops at $29, and
every task has its own budget (ledger.json 'budgets'). A launch goes ahead only if all three checks pass:
  1. task: the task's committed cost + this launch's worst case <= the task's budget;
  2. project: all committed costs + worst case <= project_cap_usd (ledger.json; falls back to cap_usd if absent; set to 72.00 with the
     lead's approval on 2026-11-13). Committed = measured cost (or billed, if larger) for closed runs; worst case for open runs;
  3. month: this month's workspace usage that the free credit pays for + open worst cases + worst case <= cap. Usage comes from
     `modal billing summary` (metered cost minus free storage) and includes the user's other Modal apps. Billing data lags by up
     to about an hour, which is why open runs count at their worst case.
Worst case = containers x (timeout + START_MIN) x hourly rate (GPU + CPU cores + memory GiB; rates from `modal billing rates`, 2026-11-09).
Modal kills a call at its timeout, so the worst case is a hard bound per launch (plus the image-build allowance).
usage (miniconda python, which has the modal client):  python budget.py status  |  python budget.py worst --n 12 --timeout-min 15
"""
import argparse
import json
import os
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent; LEDGER = HERE / "ledger.json"
MODAL = r"C:\Users\Arman\miniconda3\Scripts\modal.exe"
RATES = dict(cpu_core_h=0.0473, mem_gib_h=0.008,
             gpu_h={"T4": 0.59, "L4": 0.80, "A10G": 1.10, "L40S": 1.95, "A100-40GB": 2.10, "A100-80GB": 2.50, "H100": 3.95})
START_MIN = 3.0  # per-container allowance for start-up and data loading before the function's own clock starts


def rate_h(gpu, cpu, mem_gib):
    return (RATES["gpu_h"][gpu] if gpu else 0.0) + cpu * RATES["cpu_core_h"] + mem_gib * RATES["mem_gib_h"]


def worst_case(n, timeout_min, gpu="L4", cpu=4, mem_gib=16):
    return n * (timeout_min + START_MIN) / 60 * rate_h(gpu, cpu, mem_gib)


def load():
    return json.load(open(LEDGER))


def save(L):
    json.dump(L, open(LEDGER, "w"), indent=1)


def month_used():
    """this month's workspace cost that draws on the free credit (metered cost minus the free-storage allowance)."""
    out = subprocess.run([MODAL, "billing", "summary", "--json"], capture_output=True, text=True, timeout=180, env={**os.environ, "PYTHONUTF8": "1"})
    if out.returncode: raise RuntimeError("modal billing summary failed: " + out.stderr[-500:])
    s = json.loads(out.stdout); return float(s["metered_cost"]) + float(s["adjustments"]["free_storage"])  # free_storage is negative


def run_cost(r):
    return r["worst_usd"] if r.get("closed") is None else max(r.get("measured_usd") or 0.0, r.get("billed_usd") or 0.0)


def status(L=None, log_check=True):
    L = L or load(); m = month_used(); per = {t: 0.0 for t in L["budgets"]}
    for r in L["runs"]: per[r["task"]] = per.get(r["task"], 0.0) + run_cost(r)
    ow = sum(r["worst_usd"] for r in L["runs"] if r.get("closed") is None)
    s = dict(time=time.strftime("%Y-%m-%dT%H:%M:%S"), month_used_usd=round(m, 4), open_worst_usd=round(ow, 4), project_committed_usd=round(sum(per.values()), 4),
             per_task_usd={t: round(v, 4) for t, v in per.items()}, cap_usd=L["cap_usd"], project_cap_usd=L.get("project_cap_usd", L["cap_usd"]))
    if log_check: L["checks"].append({k: s[k] for k in ("time", "month_used_usd", "open_worst_usd", "project_committed_usd")}); save(L)
    return s


def check(task, worst):
    """(ok, report) for launching `worst` dollars of worst-case work under `task`."""
    L = load(); s = status(L); cap = L["cap_usd"]; pcap = L.get("project_cap_usd", cap); b = L["budgets"][task]; t = s["per_task_usd"].get(task, 0.0)
    tests = {f"task {task}: {t:.2f} + {worst:.2f} <= {b:.2f}": t + worst <= b,
             f"project: {s['project_committed_usd']:.2f} + {worst:.2f} <= {pcap:.2f}": s["project_committed_usd"] + worst <= pcap,
             f"month (Modal billing): {s['month_used_usd']:.2f} + open {s['open_worst_usd']:.2f} + {worst:.2f} <= {cap:.2f}":
                 s["month_used_usd"] + s["open_worst_usd"] + worst <= cap}
    return all(tests.values()), dict(status=s, tests=tests)


def open_run(task, worst, info):
    L = load(); rid = f"{task}-{len(L['runs']) + 1:03d}"
    L["runs"].append(dict(id=rid, task=task, opened=time.strftime("%Y-%m-%dT%H:%M:%S"), worst_usd=round(worst, 4), info=info, closed=None)); save(L); return rid


def close_run(rid, measured, note=""):
    L = load()
    for r in L["runs"]:
        if r["id"] == rid: r.update(closed=time.strftime("%Y-%m-%dT%H:%M:%S"), measured_usd=round(measured, 4), note=note)
    save(L)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=("status", "worst")); ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--timeout-min", type=float, default=15); ap.add_argument("--gpu", default="L4"); ap.add_argument("--cpu", type=float, default=4)
    ap.add_argument("--mem-gib", type=float, default=16); a = ap.parse_args()
    if a.cmd == "worst": print(f"worst case ${worst_case(a.n, a.timeout_min, a.gpu, a.cpu, a.mem_gib):.2f}"); return
    L = load(); s = status(L); print(json.dumps(s, indent=1))
    print("budgets:", json.dumps(L["budgets"]), "| sum", sum(L["budgets"].values()), "| month cap", L["cap_usd"],
          "| project cap", L.get("project_cap_usd", L["cap_usd"]))


if __name__ == "__main__":
    main()
