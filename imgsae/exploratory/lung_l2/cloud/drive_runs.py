"""Unattended driver for L2 cloud runs: executes a run plan (launch -> wait -> collect -> relaunch while rows remain -> copy to PC)
without a model in the loop, so a usage limit of the assistant cannot stop it. Every launch still goes through the guard in launch.py.
Started by a Windows scheduled task (independent of any Claude session). Logs to lung_l2/logs/driver_<tag>.log, state to driver_<tag>.json.

Stop rules (docs/LUNG_L2_PROTOCOL.md 7, 12; RUN_PLAN_S2.md "Never" list): guard refusal at every allowed nshard -> stop (month used up);
collect exit 4 (a call failed) -> stop; errors > 5% of rows attempted in a launch -> stop; a call not finished 80 min after launch -> stop
(the ledger run stays open at its worst case for a manual close). The billing lag rule is applied: measured costs of runs closed in the last
90 minutes are added to Modal's month figure before each launch.
usage (miniconda python):  python drive_runs.py --tag d1b --tier D1 --lo 300 --hi 2484 --zfix-max 0.65 --root dev --nshards 4,3,2,1 --max-launches 3 --copy
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent; L2 = HERE.parent; ROOT = Path(r"D:\Shayan")
sys.path.insert(0, str(ROOT / "imgsae" / "exploratory" / "p1b_sanity" / "cloud"))
import budget as B  # noqa: E402

PY = r"C:\Users\Arman\miniconda3\python.exe"; MODAL = r"C:\Users\Arman\miniconda3\Scripts\modal.exe"
ENV = {**os.environ, "PYTHONUTF8": "1"}
TASK = "lung_l2_audit"


class Driver:
    def __init__(self, a):
        self.a = a; self.log_p = L2 / "logs" / f"driver_{a.tag}.log"; self.state_p = L2 / "logs" / f"driver_{a.tag}.json"
        self.state = dict(tag=a.tag, args=vars(a), started=now(), launches=[], status="running")

    def log(self, msg):
        line = f"{now()} {msg}"; print(line, flush=True)
        with open(self.log_p, "a", encoding="utf-8") as f: f.write(line + "\n")

    def save(self):
        self.state_p.write_text(json.dumps(self.state, indent=1, default=str))

    def stop(self, status, msg):
        self.state["status"] = status; self.state["ended"] = now(); self.log(f"STOP {status}: {msg}"); self.save()

    def lag_extra(self):
        L = B.load(); cut = datetime.now() - timedelta(minutes=90); extra = 0.0
        for r in L["runs"]:
            if r.get("closed") and datetime.fromisoformat(r["closed"]) > cut: extra += max(r.get("measured_usd") or 0, r.get("billed_usd") or 0)
        return extra

    def precheck(self, ns):
        """the guard's month test plus the billing lag rule; the guard itself runs again inside launch.py."""
        s = B.status(log_check=False); worst = B.worst_case(ns, 60, "T4", 4, 16) + 0.10; extra = self.lag_extra()
        ok = s["month_used_usd"] + extra + s["open_worst_usd"] + worst <= B.load()["cap_usd"]
        self.log(f"precheck nshard {ns}: month {s['month_used_usd']:.2f} + lag {extra:.2f} + open {s['open_worst_usd']:.2f} + worst {worst:.2f} -> {'ok' if ok else 'no'}")
        return ok

    def launch(self, ns):
        a = self.a
        cmd = [MODAL, "run", "--detach", "imgsae/exploratory/lung_l2/cloud/l2_sybil_modal.py", "--step", "run", "--tier", a.tier, "--lo", str(a.lo),
               "--hi", str(a.hi), "--nshard", str(ns), "--timeout-min", "60", "--zfix-max", str(a.zfix_max), "--root", a.root]
        self.log("launch: " + " ".join(cmd[2:]))
        p = subprocess.run(cmd, cwd=ROOT, env=ENV, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
        out = (p.stdout or "") + (p.stderr or "")
        for ln in out.splitlines():
            if "<=" in ln or "SPAWNED" in ln or "FAILED" in ln: self.log("  " + ln.strip()[:300])
        if "BUDGET CHECK FAILED" in out: return None, "refused"
        rid = next((w for ln in out.splitlines() if ln.startswith("SPAWNED") for w in ln.split() if w.startswith(TASK + "-")), None)
        if rid: rid = rid.rstrip(":")
        return (rid, "spawned") if rid else (None, "error: " + out[-500:])

    def wait_collect(self, rid):
        t0 = time.time()
        while time.time() - t0 < 80 * 60:
            p = subprocess.run([PY, str(HERE / "collect.py"), rid, "--wait", "30"], cwd=ROOT, env=ENV, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
            code = p.returncode; self.log(f"collect {rid}: exit {code} {(p.stdout or '').strip()[-200:]}")
            if code == 0: return "ok"
            if code == 4: return "failed"
            time.sleep(120)
        return "timeout"

    def run(self):
        a = self.a; self.save()
        for k in range(a.max_launches):
            rid = None
            for ns in [int(x) for x in a.nshards.split(",")]:
                if not self.precheck(ns): continue
                rid, msg = self.launch(ns)
                if rid: break
                self.log(f"launch nshard {ns}: {msg[:300]}")
                if not msg.startswith("refused"): return self.stop("stopped_launch_error", msg[:300])
            if not rid: return self.stop("month_used_up", "no launch fits the month check at any allowed nshard")
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
            dst = r"D:\Shayan\imgsae_data\lung_l2_vol"
            p = subprocess.run([MODAL, "volume", "get", "imgsae-nlst-l2", "l2", dst, "--force"], cwd=ROOT, env=ENV, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=7200)
            self.log(f"copy to PC: exit {p.returncode} {(p.stdout or p.stderr or '').strip()[-200:]}")
            for sub in ("main", "zfix", "pair", "errors"):
                d = Path(dst) / "l2" / a.root / sub
                self.state.setdefault("pc_counts", {})[sub] = len(list(d.glob("*.json"))) if d.exists() else 0
        s = B.status(log_check=True); self.state["budget_after"] = {k: s[k] for k in ("month_used_usd", "open_worst_usd", "project_committed_usd")}
        self.state["task_usd"] = s["per_task_usd"].get(TASK)
        self.stop("finished", f"budget after: {self.state['budget_after']}, task {self.state['task_usd']}")


def now(): return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True); ap.add_argument("--tier", required=True); ap.add_argument("--lo", type=int, required=True)
    ap.add_argument("--hi", type=int, required=True); ap.add_argument("--zfix-max", type=float, default=0.65); ap.add_argument("--root", default="dev")
    ap.add_argument("--nshards", default="4,3,2,1"); ap.add_argument("--max-launches", type=int, default=3); ap.add_argument("--copy", action="store_true")
    ap.add_argument("--dry", action="store_true", help="only the prechecks, no launch")
    a = ap.parse_args(); d = Driver(a)
    if a.dry:
        for ns in [int(x) for x in a.nshards.split(",")]: d.precheck(ns)
    else:
        try: d.run()
        except Exception as e: d.stop("crashed", repr(e)[:500])
