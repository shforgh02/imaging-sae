"""Pre-registered subject selection (lean plan v1). Writes data/eligible.csv, data/p1_dev_ids.txt (150), data/p2_conf_ids.txt, data/SHA256SUMS.
Eligible = study types covering thorax and/or abdomen (fixed list below), institute known. Phase 1 development = 150 drawn at random (seed 0)
stratified by study_type x institute group (I vs other); everything else eligible is Phase 2 confirmation. Post-download QC (>= 20 non-empty
structures) is applied later by p1_tokens and logged, never by looking at results.
"""
import csv
import hashlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; META = ROOT.parent / "imgsae_data" / "totalseg" / "meta.csv"; OUT = ROOT / "data"
TYPES = ["ct thorax-abdomen-pelvis", "ct neck-thorax-abdomen-pelvis", "ct thorax-abdomen", "ct polytrauma", "ct angiography thorax-abdomen-pelvis",
         "ct angiography neck-thx-abd-pelvis-leg", "ct abdomen-pelvis", "ct abdomen", "ct thorax-chest", "ct thorax", "ct thorax-neck"]
N_DEV = 150


def main():
    rows = list(csv.DictReader(open(META, encoding="utf-8-sig"), delimiter=";"))
    el = [r for r in rows if r["study_type"].strip() in TYPES and r["institute"].strip()]
    strata = {}
    for r in el: strata.setdefault((r["study_type"].strip(), "I" if r["institute"] == "I" else "other"), []).append(r["image_id"])
    rng = np.random.default_rng(0); dev = []
    keys = sorted(strata); quota = {k: len(strata[k]) * N_DEV / len(el) for k in keys}
    base = {k: int(np.floor(q)) for k, q in quota.items()}; rem = N_DEV - sum(base.values())
    for k in sorted(keys, key=lambda k: -(quota[k] - base[k]))[:rem]: base[k] += 1
    for k in keys: dev += list(rng.choice(sorted(strata[k]), base[k], replace=False))
    dev = sorted(dev); conf = sorted(r["image_id"] for r in el if r["image_id"] not in set(dev))
    OUT.mkdir(exist_ok=True)
    with open(OUT / "eligible.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(el[0].keys()) + ["role"]); w.writeheader()
        for r in el: w.writerow({**r, "role": "p1_dev" if r["image_id"] in set(dev) else "p2_conf"})
    (OUT / "p1_dev_ids.txt").write_text("\n".join(dev) + "\n"); (OUT / "p2_conf_ids.txt").write_text("\n".join(conf) + "\n")
    with open(OUT / "SHA256SUMS", "w") as f:
        for p in ("eligible.csv", "p1_dev_ids.txt", "p2_conf_ids.txt"): f.write(f"{hashlib.sha256((OUT / p).read_bytes()).hexdigest()}  {p}\n")
    print(f"eligible {len(el)}  dev {len(dev)}  conf {len(conf)}  strata {len(keys)}  DONE")


if __name__ == "__main__":
    main()
