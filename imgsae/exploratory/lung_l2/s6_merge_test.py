"""Lung L2, step S6 part 1 (N4 item 6): merge one account's PC copy of root test into the main PC copy (imgsae_data/lung_l2_vol/l2/test).
It never overwrites. Same rules as p3_merge.py (dev), for the test tiers that the frozen run plan gave to that account:
- a new file must belong to a manifest row of the given tiers: main/<uid> and zfix/<uid> for T1, T2, T3 main rows, pair/<uid> for T4 rows,
  errors/<uid> for any of them;
- a file that already exists in the main copy (for example the 3 smoke series scored on both accounts) is compared: every array within
  1e-6 and the calibrated scores within 1e-4 (error files: equal content) -> skipped and counted;
- any other case (an unexpected new file, a file that differs, an .npz without its .json, an unknown folder) stops the merge before
  anything is copied.
Copy: .npz first, then .json (the .json marks a finished series), each opened with exclusive create ('xb'); SHA-256 checked after copy.
usage (venv python): python s6_merge_test.py <account l2 dir> <main l2 dir> <manifest_test csv> <tiers, e.g. T1,T4> <out json> [--dry]
"""
import json
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p3_merge import VARIANTS, same, sha  # noqa: E402


def main():
    src, dst, man_p, tiers, out_p = Path(sys.argv[1]) / "test", Path(sys.argv[2]) / "test", sys.argv[3], sys.argv[4].split(","), Path(sys.argv[5])
    dry = "--dry" in sys.argv
    M = pd.read_csv(man_p, dtype={"pid": str}); tier = dict(zip(M.series_uid, M.tier)); M = M[M.tier.isin(tiers)]
    mains = set(M.loc[M.tier.isin(["T1", "T2", "T3"]) & (M.variant == "main"), "series_uid"]); pairs = set(M.loc[M.tier == "T4", "series_uid"])
    allowed = dict(main=mains, zfix=mains, pair=pairs, errors=mains | pairs)
    plan, stops, skipped = [], [], []
    for d in sorted(p for p in src.iterdir()):
        if not d.is_dir() or d.name not in VARIANTS: stops.append(f"unknown entry {d.name}"); continue
        jsons = {p.stem for p in d.glob("*.json")}; npzs = {p.stem for p in d.glob("*.npz")}
        for u in sorted(npzs - jsons): stops.append(f"{d.name}/{u}.npz without .json")
        for o in [p.name for p in d.iterdir() if p.suffix not in (".json", ".npz")]: stops.append(f"{d.name}/{o}: unexpected file type")
        for u in sorted(jsons):
            if d.name != "errors" and u not in npzs: stops.append(f"{d.name}/{u}.json without .npz"); continue
            tj = dst / d.name / f"{u}.json"
            if tj.exists():
                eq, why = same(d / f"{u}.json", tj, d.name)
                if eq: skipped.append(dict(variant=d.name, uid=u, tier=tier.get(u), check=why))
                else: stops.append(f"{d.name}/{u} exists in the main copy and differs ({why})")
            elif (dst / d.name / f"{u}.npz").exists(): stops.append(f"{d.name}/{u}.npz exists in the main copy without its .json")
            elif u in allowed[d.name]: plan.append((d.name, u))
            else: stops.append(f"{d.name}/{u}: new file not of a {'/'.join(tiers)} manifest row (tier {tier.get(u)})")
    rep = dict(source=str(src), destination=str(dst), tiers=tiers, n_to_copy=len(plan), n_skipped_equal=len(skipped), skipped=skipped, stops=stops[:200],
               n_stops=len(stops), to_copy_by_variant_tier=pd.DataFrame(plan, columns=["variant", "uid"]).assign(tier=lambda x: x.uid.map(tier))
               .groupby(["variant", "tier"]).size().rename("n").reset_index().to_dict("records") if plan else [], dry=dry)
    if stops or dry:
        rep["status"] = "STOPPED: nothing copied" if stops else "dry run: nothing copied"
        out_p.write_text(json.dumps(rep, indent=1)); print(json.dumps({k: v for k, v in rep.items() if k != "skipped"}, indent=1)[:4000])
        raise SystemExit(2 if stops else 0)
    bad = []
    for v, u in plan:
        (dst / v).mkdir(parents=True, exist_ok=True)
        for ext in ((".npz", ".json") if v != "errors" else (".json",)):
            s_, t_ = src / v / f"{u}{ext}", dst / v / f"{u}{ext}"
            with open(s_, "rb") as fi, open(t_, "xb") as fo: shutil.copyfileobj(fi, fo)
            if sha(s_) != sha(t_): bad.append(f"{v}/{u}{ext}")
    rep["sha256_mismatch"] = bad; rep["status"] = "merged" if not bad else "MERGED WITH SHA MISMATCH"
    out_p.write_text(json.dumps(rep, indent=1)); print(json.dumps({k: v for k, v in rep.items() if k != "skipped"}, indent=1)[:4000])
    raise SystemExit(3 if bad else 0)


if __name__ == "__main__":
    main()
