"""Unattended driver for L2 cloud runs: executes a run plan (launch -> wait -> collect -> relaunch while rows remain -> copy to PC)
without a model in the loop, so a usage limit of the assistant cannot stop it (amendment A5). Every launch still goes through the guard
in launch.py. Started by a Windows scheduled task (independent of any Claude session). Logs to lung_l2/logs/driver_<tag>.log, state to
driver_<tag>.json.

Accounts (amendment A4): --profile is the Modal account. The driver refuses to start if MODAL_PROFILE in its environment differs from
--profile (the .cmd wrapper sets it, because a scheduled task does not inherit it from a chat session). Every Modal subprocess gets the
CLI's own --profile option and MODAL_PROFILE. Never `modal profile activate`.

Stop rules (docs/LUNG_L2_PROTOCOL.md 7, 12, 16a; RUN_PLAN_S2.md "Never" list): guard refusal at every allowed nshard -> stop (month or a
limit used up); collect exit 4 (a call failed) or 6 (refused) -> stop; errors > 5% of rows attempted in a launch -> stop; a call not
finished 80 min after launch -> stop (the ledger run stays open at its worst case for a manual close). On armanfo, before each launch:
no other app may have running containers (budget.app_check); if one has, wait 30 min and look again; after 2 hours stop. The prechecks
are the guard's own tests without logging (budget.evaluate: task, project, month per account with the billing lag rule, and the
project limit on the account).
usage (miniconda python):
  set MODAL_PROFILE=armanfo & python drive_runs.py --profile armanfo --tag x --tier D2 --lo 0 --hi 2442 --zfix-max 0.65 --root dev --copy
  ... --dry   (prechecks and app check only, no launch)
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent; L2 = HERE.parent; ROOT = Path(r"D:\Shayan")
sys.path.insert(0, str(ROOT / "imgsae" / "exploratory" / "p1b_sanity" / "cloud"))
import budget as B  # noqa: E402

PY = r"C:\Users\Arman\miniconda3\python.exe"; MODAL = r"C:\Users\Arman\miniconda3\Scripts\modal.exe"
TASK = "lung_l2_audit"; VOL = "imgsae-nlst-l2"
PC_COPY = {"shforghani2002": r"D:\Shayan\imgsae_data\lung_l2_vol", "armanfo": r"D:\Shayan\imgsae_data\lung_l2_vol_armanfo",
           "forghanishayan": r"D:\Shayan\imgsae_data\lung_l2_vol_forghanishayan"}   # S6 (lead's money decision, 17 Nov)
APP_CHECK = ("armanfo", "forghanishayan")   # A4: the lead's other apps on these accounts must not be running (forghanishayan: S6, 17 Nov)
APP_WAIT_S, APP_MAX_S = 30 * 60, 120 * 60


def env_for(profile):
    return {**os.environ, "PYTHONUTF8": "1", "MODAL_PROFILE": profile}


def require_profile(profile):
    """refuse unless the account is known to the ledger and this process's MODAL_PROFILE equals it."""
    B.need_profile(B.load(), profile)
    if os.environ.get("MODAL_PROFILE") != profile:
        raise SystemExit(f"REFUSED: MODAL_PROFILE in this environment is {os.environ.get('MODAL_PROFILE')!r}, not --profile {profile!r}")
    if profile not in PC_COPY: raise SystemExit(f"REFUSED: no PC copy folder for profile {profile}")


def keep_awake(on=True):
    """ask Windows not to sleep while the driver runs (SetThreadExecutionState; no install). Lid close or power button still win."""
    try:
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | (0x00000001 if on else 0))   # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
    except Exception: pass


def copy_to_pc(profile, log):
    """copy the account's volume folder l2 into that account's own PC folder (never into another account's copy)."""
    dst = PC_COPY[profile]
    p = subprocess.run([MODAL, "volume", "get", VOL, "l2", dst, "--force", "--profile", profile], cwd=ROOT, env=env_for(profile),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=7200)
    log(f"copy to PC ({profile} -> {dst}): exit {p.returncode} {(p.stdout or p.stderr or '').strip()[-200:]}")
    return dst, p.returncode


class Driver:
    def __init__(self, a):
        self.a = a; self.log_p = L2 / "logs" / f"driver_{a.tag}.log"; self.state_p = L2 / "logs" / f"driver_{a.tag}.json"
        self.state = dict(tag=a.tag, profile=a.profile, args=vars(a), started=now(), launches=[], status="running")

    def log(self, msg):
        line = f"{now()} {msg}"; print(line, flush=True)
        with open(self.log_p, "a", encoding="utf-8") as f: f.write(line + "\n")

    def save(self):
        tmp = self.state_p.with_name(self.state_p.name + ".tmp"); tmp.write_text(json.dumps(self.state, indent=1, default=str)); os.replace(tmp, self.state_p)

    def stop(self, status, msg):
        self.state["status"] = status; self.state["ended"] = now(); self.log(f"STOP {status}: {msg}"); self.save()

    def precheck(self, ns):
        """the guard's tests for this account without logging (the guard runs again, logged, inside launch.py)."""
        worst = B.worst_case(ns, 60, "T4", 4, 16) + 0.10
        ok, rep = B.evaluate(TASK, worst, self.a.profile, log_check=False)
        self.log(f"precheck nshard {ns} on {self.a.profile}: " + " | ".join(f"{k} {'ok' if v else 'NO'}" for k, v in rep["tests"].items()))
        return ok

    def wait_apps(self):
        """A4: on armanfo, no other app with running containers; wait 30 min and look again; give up after 2 hours."""
        if self.a.profile not in APP_CHECK: return True
        t0 = time.time()
        while True:
            ok, busy = B.app_check(self.a.profile); self.log(f"app check {self.a.profile}: {'ok' if ok else 'BUSY'} {json.dumps(busy)[:300]}")
            if ok: return True
            if time.time() - t0 >= APP_MAX_S: return False
            time.sleep(APP_WAIT_S)

    def launch(self, ns):
        a = self.a
        cmd = [MODAL, "run", "--detach", "--profile", a.profile, "imgsae/exploratory/lung_l2/cloud/l2_sybil_modal.py", "--step", "run", "--tier", a.tier,
               "--lo", str(a.lo), "--hi", str(a.hi), "--nshard", str(ns), "--timeout-min", "60", "--zfix-max", str(a.zfix_max), "--root", a.root]
        self.log("launch: " + " ".join(cmd[2:]))
        p = subprocess.run(cmd, cwd=ROOT, env=env_for(a.profile), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
        out = (p.stdout or "") + (p.stderr or "")
        for ln in out.splitlines():
            if "<=" in ln or "SPAWNED" in ln or "FAILED" in ln or "REFUSED" in ln or "app check" in ln: self.log("  " + ln.strip()[:300])
        if "APP CHECK FAILED" in out: return None, "app_busy"
        if "BUDGET CHECK FAILED" in out: return None, "refused"
        rid = next((w for ln in out.splitlines() if ln.startswith("SPAWNED") for w in ln.split() if w.startswith(TASK + "-")), None)
        if rid: rid = rid.rstrip(":")
        return (rid, "spawned") if rid else (None, "error: " + out[-500:])

    def wait_collect(self, rid):
        t0 = time.time()
        while time.time() - t0 < 80 * 60:
            p = subprocess.run([PY, str(HERE / "collect.py"), rid, "--profile", self.a.profile, "--wait", "30"], cwd=ROOT, env=env_for(self.a.profile),
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
            code = p.returncode; self.log(f"collect {rid}: exit {code} {(p.stdout or '').strip()[-200:]}")
            if code == 0: return "ok"
            if code == 4: return "failed"
            if code == 6: return "refused"
            time.sleep(120)
        return "timeout"

    def run(self):
        a = self.a; self.save(); keep_awake(True)
        for k in range(a.max_launches):
            rid, msg = None, "refused"
            for _attempt in range(5):   # repeated only if the app check inside launch.py found another app busy
                if not self.wait_apps(): return self.stop("stopped_other_app_busy", f"another app on {a.profile} had running containers for 2 hours")
                msg = "refused"
                for ns in [int(x) for x in a.nshards.split(",")]:
                    if not self.precheck(ns): continue
                    rid, msg = self.launch(ns)
                    if rid: break
                    self.log(f"launch nshard {ns}: {msg[:300]}")
                    if msg == "app_busy": break
                    if not msg.startswith("refused"): return self.stop("stopped_launch_error", msg[:300])
                if rid or msg != "app_busy": break
                self.log(f"app check failed inside the launch; waiting {APP_WAIT_S // 60} min"); time.sleep(APP_WAIT_S)
            if not rid:
                if msg == "app_busy": return self.stop("stopped_other_app_busy", "the app check inside launch.py kept failing")
                return self.stop("stopped_guard_refused", "no launch fits the guard at any allowed nshard (month, task, project or account limit)")
            rec = dict(rid=rid, launched=now()); self.state["launches"].append(rec); self.save()
            w = self.wait_collect(rid); rec["collect"] = w
            if w != "ok": return self.stop(f"stopped_collect_{w}", f"{rid}: collect {w}; ledger run may be open")
            name = json.loads((L2 / "logs" / "runs" / f"{rid}.json").read_text())["result_name"]
            src = L2 / "results" / "runs" / f"{name}.json"; shutil.copy(src, src.with_name(f"{name}__{rid}.json"))
            o = json.loads(src.read_text()); calls = o.get("calls", [o])
            todo = sum(c["n_todo"] for c in calls); done = sum(c["n_done"] for c in calls); err = sum(len(c["errors"]) for c in calls)
            rec.update(n_todo=todo, n_done=done, n_err=err, container_min=o["container_min"]); self.save()
            self.log(f"{rid}: todo {todo}, done {done}, errors {err}, remaining {todo - done - err}")
            if done + err and err / (done + err) > 0.05: return self.stop("stopped_errors", f"{rid}: {err} errors of {done + err}")
            if todo - done - err <= 0: break
        else:
            self.log("max launches reached")
        if a.copy:
            dst, _ = copy_to_pc(a.profile, self.log)
            for sub in ("main", "zfix", "pair", "errors"):
                d = Path(dst) / "l2" / a.root / sub
                self.state.setdefault("pc_counts", {})[sub] = len(list(d.glob("*.json"))) if d.exists() else 0
        s = B.status(log_check=True, profile=a.profile)
        self.state["budget_after"] = {k: s[k] for k in ("profile", "month_used_usd", "open_worst_usd", "project_committed_usd", "project_on_account_usd")}
        self.state["task_usd"] = s["per_task_usd"].get(TASK)
        self.stop("finished", f"budget after: {self.state['budget_after']}, task {self.state['task_usd']}")


def now(): return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True); ap.add_argument("--tag", required=True); ap.add_argument("--tier", required=True)
    ap.add_argument("--lo", type=int, required=True); ap.add_argument("--hi", type=int, required=True); ap.add_argument("--zfix-max", type=float, default=0.65)
    ap.add_argument("--root", default="dev"); ap.add_argument("--nshards", default="4,3,2,1"); ap.add_argument("--max-launches", type=int, default=3)
    ap.add_argument("--copy", action="store_true"); ap.add_argument("--dry", action="store_true", help="only the prechecks and the app check, no launch")
    a = ap.parse_args(); require_profile(a.profile); d = Driver(a)
    if a.dry:
        d.log(f"DRY RUN on {a.profile}: tier {a.tier} rows {a.lo}-{a.hi}, copy folder {PC_COPY[a.profile]}")
        ok, busy = B.app_check(a.profile) if a.profile in APP_CHECK else (True, [])
        d.log(f"app check {a.profile}: {'ok' if ok else 'BUSY'} {json.dumps(busy)[:300]}")
        for ns in [int(x) for x in a.nshards.split(",")]: d.precheck(ns)
    else:
        try: d.run()
        except Exception as e: d.stop("crashed", repr(e)[:500])
        finally: keep_awake(False)
