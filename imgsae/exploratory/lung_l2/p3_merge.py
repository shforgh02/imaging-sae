"""Lung L2, plan step P3 item 6: merge the armanfo PC copy (root dev) into the main PC copy. It never overwrites.
Rules (plan P3 item 3, review F1/E10):
- a new file must belong to a D2, D3 or D4 row of the manifest: main/<uid> and zfix/<uid> for D2 and D3 main rows, pair/<uid> for D4
  rows, errors/<uid> for any of them;
- a file that already exists in the main copy (the 3 smoke series of P2) is compared: every array within 1e-6 and the calibrated
  scores within 1e-4 (error files: equal content) -> skipped and counted;
- any other case (an unexpected new file, a file that differs, an .npz without its .json, an unknown folder) stops the merge before
  anything is copied.
Copy: .npz first, then .json (the .json marks a finished series), each opened with exclusive create ('xb'); SHA-256 checked after copy.
usage (venv python): python p3_merge.py <armanfo l2 dir> <main l2 dir> <manifest csv> <out json> [--dry]
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

VARIANTS = ("main", "zfix", "pair", "errors")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def same(src_json, dst_json, variant):
    a, b = json.load(open(src_json)), json.load(open(dst_json))
    if variant == "errors": return a == b, "error file content"
    za, zb = np.load(str(src_json)[:-5] + ".npz"), np.load(str(dst_json)[:-5] + ".npz")
    if sorted(za.files) != sorted(zb.files): return False, "array keys differ"
    d = max(float(np.abs(za[k].astype(np.float64) - zb[k].astype(np.float64)).max()) for k in za.files)
    dc = float(np.abs(np.array(a["calib"]) - np.array(b["calib"])).max())
    return (d <= 1e-6 and dc <= 1e-4), f"arrays {d:.2e}, calib {dc:.2e}"


def main():
    src, dst, man_p, out_p = Path(sys.argv[1]) / "dev", Path(sys.argv[2]) / "dev", sys.argv[3], Path(sys.argv[4]); dry = "--dry" in sys.argv
    M = pd.read_csv(man_p, dtype={"pid": str}); tier = dict(zip(M.series_uid, M.tier))
    d23 = set(M.loc[M.tier.isin(["D2", "D3"]) & (M.variant == "main"), "series_uid"]); d4 = set(M.loc[M.tier == "D4", "series_uid"])
    allowed = dict(main=d23, zfix=d23, pair=d4, errors=d23 | d4)
    plan, stops, skipped = [], [], []
    for d in sorted(p for p in src.iterdir()):
        if not d.is_dir() or d.name not in VARIANTS: stops.append(f"unknown entry {d.name}"); continue
        jsons = {p.stem for p in d.glob("*.json")}; npzs = {p.stem for p in d.glob("*.npz")}
        for u in sorted(npzs - jsons): stops.append(f"{d.name}/{u}.npz without .json")
        others = [p.name for p in d.iterdir() if p.suffix not in (".json", ".npz")]
        for o in others: stops.append(f"{d.name}/{o}: unexpected file type")
        for u in sorted(jsons):
            if d.name != "errors" and u not in npzs: stops.append(f"{d.name}/{u}.json without .npz"); continue
            tj = dst / d.name / f"{u}.json"
            if tj.exists():
                eq, why = same(d / f"{u}.json", tj, d.name)
                if eq: skipped.append(dict(variant=d.name, uid=u, tier=tier.get(u), check=why))
                else: stops.append(f"{d.name}/{u} exists in the main copy and differs ({why})")
            elif (dst / d.name / f"{u}.npz").exists(): stops.append(f"{d.name}/{u}.npz exists in the main copy without its .json")
            elif u in allowed[d.name]: plan.append((d.name, u))
            else: stops.append(f"{d.name}/{u}: new file not of a D2/D3/D4 manifest row (tier {tier.get(u)})")
    rep = dict(source=str(src), destination=str(dst), n_to_copy=len(plan), n_skipped_equal=len(skipped), skipped=skipped, stops=stops[:200], n_stops=len(stops),
               to_copy_by_variant_tier=pd.DataFrame(plan, columns=["variant", "uid"]).assign(tier=lambda x: x.uid.map(tier)).groupby(["variant", "tier"]).size()
               .rename("n").reset_index().to_dict("records") if plan else [], dry=dry)
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
