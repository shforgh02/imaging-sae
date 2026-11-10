"""M0.1: patient-level dev / sealed split of PI-CAI from the clinical sheet only (docs/MRI_M0M1_PROTOCOL.md section 1).
Downloads marksheet.csv at the pinned picai_labels commit, checks its SHA256, builds the patient table
(outcome group: csPCa / verified negative / unverified negative; centre), and splits each centre x outcome stratum with the
p1_fit.halves rule (rng = default_rng(0); per stratum in sorted order: permutation of sorted ids, first (n + rng.integers(0, 2)) // 2 -> dev).
Writes imgsae/mri/data/split.json and SHA256SUMS. No image is touched.
usage: D:\\Shayan\\imgsae\\.venv\\Scripts\\python.exe imgsae\\mri\\m0_split.py
"""
import hashlib
import io
import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

COMMIT = "ce4a4723d7c46d882a6cbaacb40ed6c4be86282f"
SHA = "23EAB23790886258440B4AF2842733332003F2C59F0A007B1E7B6B44572CF0AE"
URL = f"https://raw.githubusercontent.com/DIAGNijmegen/picai_labels/{COMMIT}/clinical_information/marksheet.csv"
OUT = Path(__file__).resolve().parent / "data"


def patient_table(M):
    """one row per patient: centre (must be unique) and outcome group."""
    rows = []
    for pid, g in M.groupby("patient_id"):
        centres = sorted(g.center.unique())
        if len(centres) != 1: sys.exit(f"STOP: patient {pid} has studies at several centres {centres}")
        if g.case_csPCa.eq("YES").any(): grp = "csPCa"
        elif g.histopath_type.notna().any(): grp = "verified_negative"
        else: grp = "unverified_negative"
        rows.append(dict(patient_id=pid, center=centres[0], group=grp, studies=sorted(g.study_id)))
    return pd.DataFrame(rows)


def split(P, seed=0):
    """the p1_fit.halves rule on centre x outcome strata."""
    rng = np.random.default_rng(seed); dev = set()
    for (c, g), s in sorted(P.groupby(["center", "group"]), key=lambda t: t[0]):
        ids = np.array(sorted(s.patient_id)); ii = rng.permutation(len(ids)); k = (len(ids) + rng.integers(0, 2)) // 2
        dev.update(ids[ii[:k]].tolist())
    return dev


def main():
    raw = urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "imgsae-m0"}), timeout=120).read()
    h = hashlib.sha256(raw).hexdigest().upper()
    if h != SHA: sys.exit(f"STOP: marksheet SHA256 {h} != pinned {SHA}")
    M = pd.read_csv(io.BytesIO(raw), dtype=str)
    if len(M) != 1500 or M.patient_id.nunique() != 1476: sys.exit(f"STOP: unexpected size {len(M)} / {M.patient_id.nunique()}")
    P = patient_table(M); dev = split(P)
    P["half"] = np.where(P.patient_id.isin(dev), "dev", "sealed")
    counts = P.groupby(["center", "group", "half"]).size().unstack(fill_value=0)
    if (counts["dev"] - counts["sealed"]).abs().max() > 1: sys.exit(f"STOP: unbalanced strata\n{counts}")
    key = lambda r: f"{r.patient_id}_{r.study_id}"  # noqa: E731  (file key used by PI-CAI: <patient>_<study>)
    M["half"] = M.patient_id.map(dict(zip(P.patient_id, P.half)))
    out = dict(
        rule="docs/MRI_M0M1_PROTOCOL.md section 1: patient-level, centre x outcome group, p1_fit.halves rule, seed 0",
        source=dict(repo="DIAGNijmegen/picai_labels", commit=COMMIT, file="clinical_information/marksheet.csv", sha256=SHA),
        counts={f"{c}|{g}": {"dev": int(r.dev), "sealed": int(r.sealed)} for (c, g), r in counts.iterrows()},
        totals=dict(dev_patients=int((P.half == "dev").sum()), sealed_patients=int((P.half == "sealed").sum()),
                    dev_studies=int((M.half == "dev").sum()), sealed_studies=int((M.half == "sealed").sum()),
                    dev_biopsy_cohort=int(((M.half == "dev") & M.histopath_type.notna() & (M.lesion_PIRADS.fillna("").map(
                        lambda s: max([int(x) for x in s.split(",") if x.strip().isdigit()] or [0])) >= 3)).sum())),
        dev_patients=sorted(P.patient_id[P.half == "dev"]), sealed_patients=sorted(P.patient_id[P.half == "sealed"]),
        dev_studies=sorted(key(r) for r in M[M.half == "dev"].itertuples()), sealed_studies=sorted(key(r) for r in M[M.half == "sealed"].itertuples()))
    OUT.mkdir(parents=True, exist_ok=True); p = OUT / "split.json"; p.write_text(json.dumps(out, indent=1))
    (OUT / "SHA256SUMS").write_text(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  split.json\n{SHA.lower()}  marksheet.csv (picai_labels {COMMIT[:7]}, not stored)\n")
    print(counts.to_string()); print(json.dumps(out["totals"], indent=1)); print("SPLIT DONE")


if __name__ == "__main__":
    main()
