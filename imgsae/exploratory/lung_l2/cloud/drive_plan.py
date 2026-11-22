"""Run several tiers in sequence with the unattended driver (drive_runs.Driver). A tier starts only if the previous one finished
cleanly (status 'finished' with no rows left); any stop ends the plan. The account's volume is copied to that account's own PC folder
(drive_runs.PC_COPY) once, at the end, or at a stop. 70 minutes after the plan ends, the account's billing is reconciled.
Accounts (amendment A4): --profile is required; the plan refuses to start if MODAL_PROFILE in its environment differs from it (the .cmd
wrapper sets it). Never `modal profile activate`.
usage (miniconda python):
  set MODAL_PROFILE=armanfo & python drive_plan.py --profile armanfo --tag arm --plan D2:0:2442,D3:0:2410,D4:0:500 --zfix-max 0.65 --root dev
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import drive_runs as DR  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--profile", required=True); ap.add_argument("--tag", required=True); ap.add_argument("--plan", required=True)
ap.add_argument("--zfix-max", type=float, default=0.65); ap.add_argument("--root", default="dev"); ap.add_argument("--nshards", default="4,3,2,1")
ap.add_argument("--max-launches", type=int, default=4); ap.add_argument("--no-reconcile", action="store_true")
a = ap.parse_args()
DR.require_profile(a.profile)
steps = [s.split(":") for s in a.plan.split(",")]
end = DR.Driver(argparse.Namespace(profile=a.profile, tag=f"{a.tag}_end", tier="-", lo=0, hi=0, zfix_max=0, root=a.root, nshards="", max_launches=0, copy=False, dry=False))
end.log(f"PLAN START on {a.profile}: {a.plan}, zfix-max {a.zfix_max}, root {a.root}, copy folder {DR.PC_COPY[a.profile]}")
DR.keep_awake(True)
try:
    for i, (tier, lo, hi) in enumerate(steps):
        ns = argparse.Namespace(profile=a.profile, tag=f"{a.tag}_{tier}", tier=tier, lo=int(lo), hi=int(hi), zfix_max=a.zfix_max, root=a.root,
                                nshards=a.nshards, max_launches=a.max_launches, copy=(i == len(steps) - 1), dry=False)
        d = DR.Driver(ns)
        try: d.run()
        except Exception as e: d.stop("crashed", repr(e)[:500])
        last = d.state["launches"][-1] if d.state["launches"] else {}
        left = last.get("n_todo", 0) - last.get("n_done", 0) - last.get("n_err", 0)
        if d.state["status"] != "finished" or left > 0:
            d.log(f"PLAN STOP after {tier}: status {d.state['status']}, rows left {left}")
            if not ns.copy: DR.copy_to_pc(a.profile, d.log)   # still copy what was done, so nothing waits on the cloud
            break
        end.log(f"plan step {tier} finished")
    end.log("PLAN END (all steps tried); reconcile after 70 min" if not a.no_reconcile else "PLAN END; no reconcile")
    # Modal bills a restarted (preempted) attempt too; write the billed cost into the ledger once the last hour is complete
    if not a.no_reconcile:
        DR.time.sleep(70 * 60)
        p = DR.subprocess.run([DR.PY, str(Path(__file__).resolve().parent / "reconcile_billing.py"), "--profile", a.profile, "--task", DR.task_of(a.root)], cwd=DR.ROOT,
                              env=DR.env_for(a.profile), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
        end.log("reconcile_billing %s: exit %d %s" % (a.profile, p.returncode, (p.stdout or p.stderr or "").strip()[-300:]))
finally:
    DR.keep_awake(False)
