"""Phase 1 D3: assemble token rows from per-scan npz files -> data/p1/rows.npz + data/p1/concepts.json.
Rows = valid tokens of scans passing QC (>= 20 non-empty structures). Inputs preprocessed as in saegt (centre, row unit-norm, global scale).
Also: group occupancy, partition labels, concept eligibility (>= 10 patients with a core token), data-driven adjacency, scan-level labels
(acq: manufacturer, institute, kVp, contrast; path: pathology tumour vs none, kidney cyst present; HU-derived: liver HU, L1 HU, LAA-950),
neighbour-token correlation per axis on scan-centred CT-FM tokens -> s*, n_eff, M*, k (size rule).
usage: python scripts/p1_assemble.py [--scans data/p1/scans] [--ids data/p1_dev_ids.txt]
"""
import argparse
import os
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from imgsae import atlas, sae  # noqa: E402

META = Path(os.environ.get("IMGSAE_DATA", ROOT.parent / "imgsae_data" / "totalseg")) / "meta.csv"; P1 = Path(os.environ.get("IMGSAE_P1", ROOT / "data/p1"))


def prep(X, params=None):
    """saegt preprocessing (centre, row unit-norm, global scale); returns (X, mu, scale) so perturbed tokens get the same transform."""
    X = X.astype(np.float32); mu = X.mean(0) if params is None else params[0]; X = X - mu; X = X / np.maximum(np.linalg.norm(X, axis=1, keepdims=True), 1e-9)
    sc = np.sqrt((X ** 2).mean()) if params is None else params[1]; return X / sc, mu, sc


def neighbour_corr(feat, gidx, scan, axis, lag):
    """median over feature dims of corr(token, token + lag along axis) on scan-centred features."""
    Xc = feat.astype(np.float32).copy()
    for s in np.unique(scan): Xc[scan == s] -= Xc[scan == s].mean(0)
    key = {(int(s), *map(int, g)): i for i, (s, g) in enumerate(zip(scan, gidx))}; a, b = [], []
    for i, (s, g) in enumerate(zip(scan, gidx)):
        h = list(map(int, g)); h[axis] += lag; j = key.get((int(s), *h))
        if j is not None: a.append(i); b.append(j)
    if len(a) < 100: return np.nan
    A, B = Xc[a], Xc[b]; A = (A - A.mean(0)) / np.maximum(A.std(0), 1e-9); B = (B - B.mean(0)) / np.maximum(B.std(0), 1e-9)
    return float(np.median((A * B).mean(0)))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--scans", default=str(P1 / "scans")); ap.add_argument("--ids", default=os.environ.get("IMGSAE_IDS", str(ROOT / "data/p1_dev_ids.txt")))
    ap.add_argument("--out", default=str(P1)); a = ap.parse_args(); out = Path(a.out)
    meta = {r["image_id"]: r for r in csv.DictReader(open(META, encoding="utf-8-sig"), delimiter=";")}
    ids = [l.strip() for l in open(a.ids) if l.strip()]; parts, qc = {k: [] for k in ("ctfm", "null", "ref", "pos", "occ", "gidx", "coords", "scan")}, []
    scan_rows = []
    for si, s in enumerate(ids):
        p = Path(a.scans) / f"{s}.npz"
        if not p.exists(): qc.append((s, "missing")); continue
        z = np.load(p, allow_pickle=False); sc = json.loads(str(z["scan"]))
        if sc["n_struct"] < 20: qc.append((s, f"n_struct {sc['n_struct']}")); continue
        n = len(z["occ"]); k = len(scan_rows)
        for key, src in (("ctfm", "feat_ctfm"), ("null", "feat_null"), ("ref", "ref"), ("pos", "pos"), ("occ", "occ"), ("gidx", "gidx"), ("coords", "coords")):
            parts[key].append(z[src] if src in z.files else np.zeros((n, 1), np.float16))
        parts["scan"].append(np.full(n, k)); m = meta.get(s, {})
        scan_rows.append(dict(id=s, study_type=m.get("study_type", "").strip(), institute=m.get("institute", ""), manufacturer=m.get("manufacturer", ""),
                              kvp=m.get("kvp", ""), pathology=m.get("pathology", ""), age=m.get("age", ""), sex=m.get("gender", ""), **sc,
                              cyst=float(z["occ"][:, [atlas.LEAVES.index("kidney_cyst_left"), atlas.LEAVES.index("kidney_cyst_right")]].max() > 0)))
    R = {k: np.concatenate(v) for k, v in parts.items()}; occg = atlas.group_occupancy(R["occ"].astype(np.float32)); lab = atlas.partition(occg)
    core_pat = {g: len(np.unique(R["scan"][lab == i])) for i, g in enumerate(atlas.GROUPS)}; eligible = [g for g, n in core_pat.items() if n >= 10]
    adj = atlas.adjacency(occg)
    sstar = {}
    for ax, nm in enumerate("zyx"):
        sstar[nm] = None
        for lag in range(1, 7):
            if neighbour_corr(R["ctfm"], R["gidx"], R["scan"], ax, lag) < .5: sstar[nm] = lag; break
    eff = np.prod([1.0 / (sstar[a_] or 6) for a_ in "zyx"]); n_eff = int(len(R["occ"]) * eff); M, k = sae.size_rule(R["ctfm"].shape[1], n_eff)
    out.mkdir(parents=True, exist_ok=True)
    Xc, mc, sc_c = prep(R["ctfm"]); Xn, mn, sc_n = prep(R["null"]); Xr, mr, sc_r = prep(np.concatenate([R["ref"], R["pos"]], 1))
    np.savez(out / "rows.npz", X_ctfm=Xc, X_null=Xn, X_ref=Xr, occ=R["occ"], occg=occg.astype(np.float16), lab=lab, scan=R["scan"], gidx=R["gidx"], coords=R["coords"],
             prep_ctfm_mu=mc, prep_ctfm_sc=sc_c, prep_null_mu=mn, prep_null_sc=sc_n, prep_ref_mu=mr, prep_ref_sc=sc_r)
    json.dump(dict(groups=atlas.GROUPS, eligible=eligible, core_patients=core_pat, adjacency={k_: sorted(v) for k_, v in adj.items()}, s_star=sstar, n_rows=int(len(R["occ"])),
                   n_eff=n_eff, M=M, k=k, scans=scan_rows, qc_excluded=qc), open(out / "concepts.json", "w"), indent=1, default=float)
    print(f"rows {len(R['occ'])} scans {len(scan_rows)} excluded {len(qc)} eligible groups {len(eligible)} s* {sstar} n_eff {n_eff} M {M} k {k} DONE")


if __name__ == "__main__":
    main()
