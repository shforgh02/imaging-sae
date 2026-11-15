"""Run several tiers in sequence with the unattended driver (drive_runs.Driver). A tier starts only if the previous one finished
cleanly (status 'finished' with no rows left); any stop ends the plan. The volume is copied to the PC once, at the end.
usage (miniconda python): python drive_plan.py --tag dec --plan D2:0:2442,D3:0:2410,D4:0:500 --zfix-max 0.65 --root dev
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import drive_runs as DR  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--tag", required=True); ap.add_argument("--plan", required=True); ap.add_argument("--zfix-max", type=float, default=0.65)
ap.add_argument("--root", default="dev"); ap.add_argument("--nshards", default="4,3,2,1"); ap.add_argument("--max-launches", type=int, default=4)
a = ap.parse_args()
steps = [s.split(":") for s in a.plan.split(",")]
for i, (tier, lo, hi) in enumerate(steps):
    ns = argparse.Namespace(tag=f"{a.tag}_{tier}", tier=tier, lo=int(lo), hi=int(hi), zfix_max=a.zfix_max, root=a.root, nshards=a.nshards,
                            max_launches=a.max_launches, copy=(i == len(steps) - 1), dry=False)
    d = DR.Driver(ns)
    try: d.run()
    except Exception as e: d.stop("crashed", repr(e)[:500])
    last = d.state["launches"][-1] if d.state["launches"] else {}
    left = last.get("n_todo", 0) - last.get("n_done", 0) - last.get("n_err", 0)
    if d.state["status"] != "finished" or left > 0:
        d.log(f"PLAN STOP after {tier}: status {d.state['status']}, rows left {left}")
        if not ns.copy:   # still copy what was done, so nothing waits on the cloud
            DR.subprocess.run([DR.MODAL, "volume", "get", "imgsae-nlst-l2", "l2", r"D:\Shayan\imgsae_data\lung_l2_vol", "--force"], cwd=DR.ROOT,
                              env=DR.ENV, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=7200)
        break
# Modal bills a restarted (preempted) attempt too; write the billed cost into the ledger once the last hour is complete
DR.time.sleep(70 * 60)
p = DR.subprocess.run([DR.PY, str(Path(__file__).resolve().parent / "reconcile_billing.py")], cwd=DR.ROOT, env=DR.ENV, capture_output=True,
                      text=True, encoding="utf-8", errors="replace", timeout=900)
DR.Driver(argparse.Namespace(tag=f"{a.tag}_end", tier="-", lo=0, hi=0, zfix_max=0, root=a.root, nshards="", max_launches=0, copy=False, dry=False)).log(
    "reconcile_billing: exit %d %s" % (p.returncode, (p.stdout or p.stderr or "").strip()[-300:]))
