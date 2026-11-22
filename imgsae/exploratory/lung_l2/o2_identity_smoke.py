"""Lung L2, plan O2 amendment A1 (22 Nov; review R4c, Neon's A1 reviews): the gate between the three smoke runs and the main O2 runs.
Each account's smoke scored the demo case and U1 rows 0-2 into root `unseen` on its own volume (`modal volume get imgsae-nlst-l2 l2 <PC copy>
--force --profile <P>` copies the whole l2 folder, including run_info/smoke_unseen.json). This checks, for exactly three distinct PC copies:
  every smoke record: demo case within 0.005 of the published scores, demo volume equal to Sybil's own, 3 of 3 U1 volumes equal to
  Sybil's own (bench.verify), no error (bench.errors), head weights SHA-256 = the frozen ba2d6d85..., root unseen, tier U1;
  the same 3 main series on every account; every main series whose geometry needs a z-fix has its z-fix file on every account;
  across every pair of accounts calibrated probabilities within 1e-4, logits within 1e-5, pooled within 1e-4, all finite.
Outcome-free (no table is read). The main runs start only if this prints PASS; any missing file is a FAIL (written to the json).
usage (venv python): python o2_identity_smoke.py <l2 copy 1>,<l2 copy 2>,<l2 copy 3> <out json>
"""
import glob
import itertools
import json
import sys
from pathlib import Path

import numpy as np

HEADS_SHA256 = "ba2d6d85d330cc6c99360c557647460ba4fa7ab738abba9be79c1d26b8009bac"


def fin(x): return bool(np.all(np.isfinite(np.asarray(x, dtype=np.float64))))


def main():
    copies, out = sys.argv[1].split(","), Path(sys.argv[2]); res = dict(copies=copies, smoke={}, series={}, problems=[])
    if len(copies) != 3 or len({str(Path(c).resolve()).lower() for c in copies}) != 3: res["problems"].append("need exactly 3 distinct copies")
    for c in copies:
        p = Path(c) / "run_info" / "smoke_unseen.json"
        if not p.exists(): res["smoke"][c] = "missing"; res["problems"].append(f"smoke record missing: {p}"); continue
        s = json.load(open(p)); b = s.get("bench", {}); ver = b.get("verify") or []
        m = dict(demo_maxdiff=s.get("demo_maxdiff"), demo_volume_equal_serie=s.get("demo_volume_equal_serie"), heads_sha256=s.get("heads_sha256"),
                 verify=[v.get("equal") for v in ver], errors=b.get("errors"), root=s.get("root"), tier=s.get("tier"))
        m["pass"] = bool(m["demo_maxdiff"] is not None and np.isfinite(m["demo_maxdiff"]) and m["demo_maxdiff"] <= 0.005 and m["demo_volume_equal_serie"]
                         and len(ver) == 3 and all(v is True for v in m["verify"]) and not m["errors"] and m["heads_sha256"] == HEADS_SHA256
                         and m["root"] == "unseen" and m["tier"] == "U1")
        if not m["pass"]: res["problems"].append(f"smoke record fails its marks: {c}")
        res["smoke"][c] = m
    main_sets = [{Path(j).stem for j in glob.glob(str(Path(c) / "unseen" / "main" / "*.json"))} for c in copies]
    zfix_sets = [{Path(j).stem for j in glob.glob(str(Path(c) / "unseen" / "zfix" / "*.json"))} for c in copies]
    if any(s_ != main_sets[0] for s_ in main_sets) or len(main_sets[0]) != 3: res["problems"].append(f"main: not the same 3 series on every account ({[len(s_) for s_ in main_sets]})")
    if any(s_ != zfix_sets[0] for s_ in zfix_sets): res["problems"].append("zfix: different series on the accounts")
    need = set()
    for u in sorted(set.intersection(*main_sets)) if main_sets else []:
        for c in copies:
            try:
                if json.load(open(Path(c) / "unseen" / "main" / f"{u}.json")).get("geo", {}).get("zfix_needed"): need.add(u)
            except (OSError, ValueError): res["problems"].append(f"main/{u}: unreadable record on {c}")
    for u in sorted(need):
        if not all(u in s_ for s_ in zfix_sets): res["problems"].append(f"zfix/{u}: needed but missing on an account")
    for var, sets in (("main", main_sets), ("zfix", zfix_sets)):
        for u in sorted(set.intersection(*sets)) if sets else []:
            try:
                recs = [json.load(open(Path(c) / "unseen" / var / f"{u}.json")) for c in copies]
                npz = [np.load(Path(c) / "unseen" / var / f"{u}.npz") for c in copies]
            except (OSError, ValueError) as e:
                res["problems"].append(f"{var}/{u}: missing or unreadable file ({type(e).__name__})"); continue
            vals = dict(calib=[np.array(r["calib"], float) for r in recs], logit=[z["logit"].astype(np.float64) for z in npz], pooled=[z["pooled"].astype(np.float64) for z in npz])
            d = {k: (float("inf") if not all(fin(x) for x in xs) else float(max(np.abs(x - y).max() for x, y in itertools.combinations(xs, 2)))) for k, xs in vals.items()}
            ok = d["calib"] <= 1e-4 and d["logit"] <= 1e-5 and d["pooled"] <= 1e-4
            res["series"][f"{var}/{u}"] = dict(max_abs_any_pair=d, pass_=bool(ok))
            if not ok: res["problems"].append(f"{var}/{u}: accounts differ {d}")
    res["zfix_needed"] = sorted(need); res["PASS"] = not res["problems"]
    out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes((json.dumps(res, indent=1, default=float) + "\n").encode("utf-8"))
    print("PASS" if res["PASS"] else "FAIL: " + "; ".join(res["problems"])); sys.exit(0 if res["PASS"] else 1)


if __name__ == "__main__":
    main()
