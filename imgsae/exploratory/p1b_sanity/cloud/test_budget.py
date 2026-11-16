"""Unit test of budget.py with two accounts (plan docs/PLAN_L2_NEXT_v1.md P1 item 5). Runs on a COPY of ledger.json in a temporary folder;
Modal's month figure is replaced by fixed numbers, so no Modal call is made and the real ledger is not touched.
usage (miniconda python): python test_budget.py
"""
import json
import shutil
import tempfile
import threading
import time
from pathlib import Path

import budget as B

REAL = B.LEDGER; BACKUP = B.HERE / "ledger_backup_2026-11-16_before_accounts.json"
MONTH = {"shforghani2002": 28.17, "armanfo": 1.62}
TASK = "lung_l2_audit"; W4 = B.worst_case(4, 60, "T4", 4, 16) + 0.10; W3 = B.worst_case(3, 60, "T4", 4, 16) + 0.10
results = []


def ok(name, cond, info=""):
    results.append((name, bool(cond))); print(f"{'PASS' if cond else 'FAIL'}  {name}  {info}")


def raises(fn, exc=ValueError):
    try: fn()
    except exc: return True
    return False


def ago(minutes): return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - 60 * minutes))


def add_closed(profile, usd, minutes_ago, task=TASK):
    with B.locked():
        L = B.load(); rid = f"{task}-{len(L['runs']) + 1:03d}"
        L["runs"].append(dict(id=rid, task=task, profile=profile, opened=ago(minutes_ago + 30), worst_usd=4.0, info={}, closed=ago(minutes_ago), measured_usd=usd))
        B.save(L)
    return rid


def main():
    real_bytes = REAL.read_bytes()
    tmp = Path(tempfile.mkdtemp(prefix="budget_test_")); B.LEDGER = tmp / "ledger.json"; shutil.copy(REAL, B.LEDGER)
    B.month_used = lambda profile: MONTH[profile]
    try:
        # 0. the migration kept everything else
        old, new = json.loads(BACKUP.read_text()), B.load()
        same_runs = all({k: v for k, v in rn.items() if k != "profile"} == ro for rn, ro in zip(new["runs"], old["runs"])) and len(new["runs"]) == len(old["runs"])
        ok("migration: runs unchanged except profile", same_runs and all(r["profile"] == "shforghani2002" for r in new["runs"]))
        ok("migration: checks, budgets, caps unchanged", new["checks"] == old["checks"] and new["budgets"] == old["budgets"]
           and new["cap_usd"] == old["cap_usd"] == 29.0 and new["project_cap_usd"] == 72.0)
        ok("migration: accounts and armanfo limit", new["accounts"] == {"shforghani2002": {"cap_usd": 29.0}, "armanfo": {"cap_usd": 29.5}}
           and new["armanfo_project_limit_usd"] == 17.0)

        # 1. per-account status
        sa, sm = B.status(log_check=False, profile="armanfo"), B.status(log_check=False, profile="shforghani2002")
        ok("status armanfo: month 1.62, cap 29.50, limit 17.00, nothing of this project there",
           sa["month_used_usd"] == 1.62 and sa["cap_usd"] == 29.5 and sa["project_on_account_limit_usd"] == 17.0 and sa["project_on_account_usd"] == 0.0, json.dumps({k: sa[k] for k in ("month_used_usd", "cap_usd", "project_on_account_usd")}))
        ok("status shforghani2002: month 28.17, cap 29.00, no account limit", sm["month_used_usd"] == 28.17 and sm["cap_usd"] == 29.0 and sm["project_on_account_limit_usd"] is None)
        ok("task and project totals are the same seen from both accounts", sa["per_task_usd"] == sm["per_task_usd"] and sa["project_committed_usd"] == sm["project_committed_usd"],
           f"task {sa['per_task_usd'][TASK]}, project {sa['project_committed_usd']}")

        # 2. unknown profiles are refused
        ok("unknown profile refused (status, check, open_run)", raises(lambda: B.status(log_check=False, profile="forghanishayan"))
           and raises(lambda: B.check(TASK, 0.1, "forghanishayan")) and raises(lambda: B.check(TASK, 0.1)) and raises(lambda: B.open_run(TASK, 0.1, {}, profile=None)))

        # 3. no-log mode writes nothing; log mode appends one check with the profile
        b0 = B.LEDGER.read_bytes(); B.status(log_check=False, profile="armanfo")
        ok("status no-log: ledger bytes unchanged", B.LEDGER.read_bytes() == b0)
        n0 = len(B.load()["checks"]); B.status(log_check=True, profile="armanfo"); c = B.load()["checks"]
        ok("status log: one check added, with profile", len(c) == n0 + 1 and c[-1]["profile"] == "armanfo")

        # 4. month test per account, and a refusal at the cap
        okA, repA = B.check(TASK, W4, "armanfo"); okM, repM = B.check(TASK, 1.0, "shforghani2002")
        ok("4 containers on armanfo allowed", okA, f"worst {W4:.2f}")
        ok("1.00 on shforghani2002 refused by its month test only (28.17 + 1.00 > 29.00)", not okM and [k for k, v in repM["tests"].items() if not v][0].startswith("month shforghani2002"))
        MONTH["armanfo"] = 26.0
        okA2, repA2 = B.check(TASK, W4, "armanfo"); okA3, _ = B.check(TASK, W3, "armanfo")
        ok("armanfo at 26.00: 4 containers refused (26 + 3.91 > 29.50), 3 containers allowed (26 + 2.96 <= 29.50)",
           not okA2 and okA3 and [k for k, v in repA2["tests"].items() if not v][0].startswith("month armanfo"))
        MONTH["armanfo"] = 1.62

        # 5. open runs are counted on the right account
        t_before = sm["per_task_usd"][TASK]; p_before = sm["project_committed_usd"]
        rid = B.open_run(TASK, W4, {"test": 1}, profile="armanfo")
        sa, sm = B.status(log_check=False, profile="armanfo"), B.status(log_check=False, profile="shforghani2002")
        ok("open run counted on armanfo only", abs(sa["open_worst_usd"] - round(W4, 4)) < 1e-9 and sm["open_worst_usd"] == 0 and abs(sm["open_worst_all_accounts_usd"] - round(W4, 4)) < 1e-9)
        ok("open run counts in the task and project totals (all accounts)", abs(sm["per_task_usd"][TASK] - t_before - round(W4, 4)) < 1e-3
           and abs(sm["project_committed_usd"] - p_before - round(W4, 4)) < 1e-3 and sa["project_on_account_usd"] == round(W4, 4))
        B.close_run(rid, 3.0, "test close"); L = B.load(); r = [x for x in L["runs"] if x["id"] == rid][0]
        ok("close_run keeps the profile", r["profile"] == "armanfo" and r["measured_usd"] == 3.0)

        # 6. billing lag on the right account (that run closed just now)
        sa, sm = B.status(log_check=False, profile="armanfo"), B.status(log_check=False, profile="shforghani2002")
        ok("lag: a run closed just now adds to armanfo's month test only", sa["lag_usd"] == 3.0 and sm["lag_usd"] == 0.0)

        # 7. the $17.00 limit for this project on armanfo (old closed runs, so no lag)
        add_closed("armanfo", 10.5, 600)     # armanfo total now 3.00 + 10.50 = 13.50
        okL4, repL4 = B.check(TASK, W4, "armanfo"); okL3, _ = B.check(TASK, W3, "armanfo")
        failed = [k for k, v in repL4["tests"].items() if not v]
        ok("armanfo limit: 13.50 + 3.91 > 17.00 refused by the 4th test only; 13.50 + 2.96 allowed", not okL4 and okL3 and len(failed) == 1 and failed[0].startswith("project on armanfo"), failed[0] if failed else "")
        okS, repS = B.check(TASK, W4, "shforghani2002")
        ok("the armanfo limit does not apply to shforghani2002 (refused there only by its month)", not okS and all(not k.startswith("project on") for k in repS["tests"])
           and [k for k, v in repS["tests"].items() if not v][0].startswith("month shforghani2002"))

        # 8. task and project tests still sum over all accounts
        L = B.load(); t = sum(B.run_cost(r) for r in L["runs"] if r["task"] == TASK)
        okT, repT = B.check(TASK, 45.0 - t + 0.01, "armanfo")
        ok("task test sums both accounts", [k for k, v in repT["tests"].items() if not v and k.startswith("task")] != [], f"task total {t:.2f}")

        # 9. a run without profile is refused
        L = B.load(); L["runs"].append(dict(id="x-999", task=TASK, opened=ago(5), worst_usd=1.0, info={}, closed=None)); B.save(L)
        ok("a ledger run without profile makes the guard refuse", raises(lambda: B.status(log_check=False, profile="armanfo")))
        L = B.load(); L["runs"] = L["runs"][:-1]; B.save(L)

        # 10. concurrent writers: 8 threads open runs at once; the lock keeps every one
        n0 = len(B.load()["runs"]); ids = []
        th = [threading.Thread(target=lambda: ids.append(B.open_run("a3_sae", 0.01, {}, profile="armanfo"))) for _ in range(8)]
        [x.start() for x in th]; [x.join() for x in th]
        L = B.load()
        ok("8 concurrent open_run: 8 new runs, ids unique, file valid JSON", len(L["runs"]) == n0 + 8 and len(set(ids)) == 8)
        ok("no lock or temp file left", not (tmp / "ledger.json.lock").exists() and not list(tmp.glob("ledger.json.tmp*")))

        # 11. app check (A4) on fake `modal` output: field names app_id, description, state, tasks
        import subprocess as SP
        real_run = SP.run

        class R:
            def __init__(self, out, code=0): self.stdout, self.stderr, self.returncode = out, "", code

        def fake(apps, code=0):
            def run(cmd, **k):
                if cmd[1:3] == ["environment", "list"]: return R(json.dumps([{"name": "main", "web_suffix": "", "active": "True"}]))
                return R(json.dumps(apps), code)
            return run
        own = {"app_id": "ap-1", "description": "imgsae-lung-l2", "state": "ephemeral (detached)", "tasks": "4", "created_at": "x", "stopped_at": None}
        idle = {"app_id": "ap-2", "description": "lead-app", "state": "deployed", "tasks": "0", "created_at": "x", "stopped_at": None}
        busy = {"app_id": "ap-3", "description": "lead-job", "state": "ephemeral", "tasks": "2", "created_at": "x", "stopped_at": None}
        try:
            SP.run = fake([]); a0 = B.app_check("armanfo")
            SP.run = fake([own, idle]); a1 = B.app_check("armanfo")
            SP.run = fake([own, idle, busy]); a2 = B.app_check("armanfo")
            SP.run = fake([dict(idle, tasks="?")]); a3 = B.app_check("armanfo")
            SP.run = fake([], code=1); a4 = B.app_check("armanfo")
        finally:
            SP.run = real_run
        ok("app check: empty list ok; own busy app and idle deployed app ok", a0[0] and a1[0] and a1[1] == [])
        ok("app check: another app with 2 running tasks -> busy", not a2[0] and a2[1][0]["app_id"] == "ap-3")
        ok("app check: unreadable task count -> busy; failed command -> not ok", not a3[0] and not a4[0])
    finally:
        B.LEDGER = REAL; shutil.rmtree(tmp, ignore_errors=True)
    ok("the real ledger was not touched", REAL.read_bytes() == real_bytes)
    n_fail = sum(not c for _, c in results); print(f"\n{len(results) - n_fail} of {len(results)} passed")
    raise SystemExit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
