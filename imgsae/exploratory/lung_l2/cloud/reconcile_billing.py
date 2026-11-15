"""Write Modal's billed cost into the ledger (field billed_usd) for lung_l2_audit runs, so the guard's task and project checks use real cost.
Why: Modal may preempt a GPU container and restart the input; the restarted attempt's container minutes are all the job reports, so the
measured cost undercounts (seen on 2026-11-15, run 037). Modal's hourly billing report (per app, UTC) is the source of truth.
Rule: runs are grouped into clusters whose UTC hours overlap; a cluster's billed cost (app imgsae-lung-l2, those hours) is split over its
runs in proportion to their measured cost. Only full hours are reported by Modal: run this at least one hour after the last run closed.
usage (miniconda python): python reconcile_billing.py [--dry]
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, r"D:\Shayan\imgsae\exploratory\p1b_sanity\cloud")
import budget as B  # noqa: E402

MODAL = r"C:\Users\Arman\miniconda3\Scripts\modal.exe"; APP = "imgsae-lung-l2"; TASK = "lung_l2_audit"


def hours(a, b):
    h = a.replace(minute=0, second=0); out = set()
    while h <= b: out.add(h.strftime("%Y-%m-%dT%H:00:00")); h += timedelta(hours=1)
    return out


def billing(day0, day1):
    p = subprocess.run([MODAL, "billing", "report", "--start", day0, "--end", day1, "--resolution", "h", "--json"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env={**os.environ, "PYTHONUTF8": "1"}, timeout=300)
    t = p.stdout; rows = json.loads(t[t.find("["):]); out = {}
    for r in rows:   # one row per app and hour; several apps (one per `modal run`) can share an hour: add them up
        if r.get("description") == APP: out[r["interval_start"][:19]] = out.get(r["interval_start"][:19], 0.0) + float(r["cost"])
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true"); a = ap.parse_args()
    L = B.load(); runs = [r for r in L["runs"] if r["task"] == TASK and r.get("closed")]
    for r in runs: r["_h"] = hours(datetime.fromisoformat(r["opened"]), datetime.fromisoformat(r["closed"]))
    d0 = min(datetime.fromisoformat(r["opened"]) for r in runs).strftime("%Y-%m-%d")
    d1 = (max(datetime.fromisoformat(r["closed"]) for r in runs) + timedelta(days=1)).strftime("%Y-%m-%d")
    bill = billing(d0, d1)
    clusters = []
    for r in sorted(runs, key=lambda r: r["opened"]):
        if clusters and clusters[-1]["h"] & r["_h"]: clusters[-1]["runs"].append(r); clusters[-1]["h"] |= r["_h"]
        else: clusters.append(dict(runs=[r], h=set(r["_h"])))
    report = []
    for c in clusters:
        billed = sum(bill.get(h, 0.0) for h in c["h"]); meas = sum(r.get("measured_usd") or 0 for r in c["runs"])
        for r in c["runs"]:
            share = billed * (r.get("measured_usd") or 0) / meas if meas else billed / len(c["runs"])
            report.append(dict(id=r["id"], measured=r.get("measured_usd"), billed=round(share, 4)))
    print(json.dumps(dict(billing_hours=bill, runs=report, total_billed=round(sum(x["billed"] for x in report), 4),
                          total_measured=round(sum(x["measured"] or 0 for x in report), 4)), indent=1))
    if a.dry: return
    L = B.load(); by = {x["id"]: x for x in report}
    for r in L["runs"]:
        if r["id"] in by:
            r["billed_usd"] = by[r["id"]]["billed"]; r["billed_note"] = f"from modal billing report (hourly, app {APP}), {datetime.now():%Y-%m-%dT%H:%M}"
    B.save(L); print("ledger updated")


if __name__ == "__main__":
    main()
