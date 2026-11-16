"""One-time ledger change for lung L2 amendment A4 (lead's OK, 2026-11-15; plan docs/PLAN_L2_NEXT_v1.md P1 item 1).
Backs up ledger.json first, then: adds 'accounts' (per-account monthly caps) and 'armanfo_project_limit_usd'; gives every run a
'profile' (all earlier runs were on shforghani2002); updates the rule text and the notes. Refuses to run twice.
usage (miniconda python): python ledger_add_accounts.py
"""
import json
import shutil
import time
from pathlib import Path

import budget as B

BACKUP = B.HERE / "ledger_backup_2026-11-16_before_accounts.json"


def main():
    L = B.load()
    if "accounts" in L or any("profile" in r for r in L["runs"]): raise SystemExit("ledger already has accounts or run profiles: nothing done")
    if BACKUP.exists(): raise SystemExit(f"{BACKUP} exists: nothing done")
    shutil.copy2(B.LEDGER, BACKUP); print("backup:", BACKUP)
    with B.locked():
        L = B.load(); n = len(L["runs"])
        for r in L["runs"]: r["profile"] = "shforghani2002"
        notes = dict(L["budget_notes"])
        notes["accounts"] = ("Per-account monthly caps (lead's OK 2026-11-15, lung L2 amendment A4): shforghani2002 29.00, armanfo 29.50. "
                             "cap_usd stays as shforghani2002's cap for old scripts; budget.py uses 'accounts'. Every run records its profile.")
        notes["armanfo_project_limit_usd"] = ("This project may use at most $17.00 on account armanfo (lead's answer to review question 1, "
                                              "2026-11-15). budget.py test 4: this project's runs on armanfo (all time = November 2026), "
                                              "worst case for open runs, + launch worst case <= 17.00.")
        notes["lung_l2_audit"] += (" Amended 2026-11-15 (A4, A5, lead's OK): account armanfo for S3 D2, D3, D4 and the P2 smoke and identity "
                                   "runs; paid runs by the unattended driver (drive_runs.py, drive_plan.py).")
        new = {}
        for k in ("cap_usd", "project_cap_usd"): new[k] = L[k]
        new["accounts"] = {"shforghani2002": {"cap_usd": 29.0}, "armanfo": {"cap_usd": 29.5}}
        new["armanfo_project_limit_usd"] = 17.0
        new["rule"] = L["rule"] + (" Updated 2026-11-15 (lead, lung L2 amendment A4): the ledger tracks two accounts; per-account monthly "
                                   "caps in 'accounts' (shforghani2002 29.00, armanfo 29.50); this project at most $17.00 on armanfo; "
                                   "profile forghanishayan and the reserve are not used.")
        for k in L:
            if k not in new: new[k] = notes if k == "budget_notes" else L[k]
        B.save(new)
    print(f"ledger updated {time.strftime('%Y-%m-%dT%H:%M:%S')}: accounts added, {n} runs given profile shforghani2002")


if __name__ == "__main__":
    main()
