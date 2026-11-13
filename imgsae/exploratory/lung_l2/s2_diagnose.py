"""Lung L2, S2: diagnosis of the two pilot checks that failed as written (G2e air inversion, G2f z-stretch). Exploratory, no outcome.
usage: python s2_diagnose.py <volume copy dir (…/l2)> <out_json>
"""
import glob
import json
import sys

import numpy as np
import pandas as pd

vol_d, out_p = sys.argv[1], sys.argv[2]
rows = []
for j in glob.glob(f"{vol_d}/dev/main/*.json"):
    r = json.load(open(j)); m, g, t = r["measures"], r["geo"], r["tags"]
    rows.append(dict(uid=r["series_uid"], maker=t.get("Manufacturer"), model=t.get("ManufacturerModelName"), kernel=t.get("ConvolutionKernel"),
                     fov=pd.to_numeric(t.get("ReconstructionDiameter"), errors="coerce"), ratio=g.get("ratio"), resT=(g.get("resampled_shape_main") or [0] * 4)[3],
                     **{k: m.get(k) for k in ("air_median_hu", "air_noise_sd_hu", "air_n_vox", "lung_vol_ml", "laa950_pct", "lung_cut_z", "lung_cut_xy",
                                              "lung_z_extent_app_mm", "lung_z_first", "lung_z_last", "body_touches_edge", "n_real_slices")}))
M = pd.DataFrame(rows)
res = {}
bad = M[(M.air_median_hu.isna()) | ((M.air_median_hu + 1000).abs() > 30)]
res["G2e_air"] = dict(n=len(M), n_fail=len(bad), fail_by_maker=bad.maker.value_counts().to_dict(), all_by_maker=M.maker.value_counts().to_dict(),
                      fail_air_median_q=np.nanpercentile(bad.air_median_hu, [0, 25, 50, 75, 100]).round(1).tolist() if bad.air_median_hu.notna().any() else None,
                      air_median_by_maker={k: np.nanpercentile(v.air_median_hu, [5, 50, 95]).round(1).tolist() for k, v in M.groupby("maker")},
                      fail_examples=bad.head(12).astype(str).to_dict("records"))
# G2f: stretch with and without the z-crop cutting the lung
Z = {}
for j in glob.glob(f"{vol_d}/dev/zfix/*.json"):
    r = json.load(open(j)); Z[r["series_uid"]] = r["measures"]
P = []
for _, r in M.iterrows():
    z = Z.get(r.uid)
    if z is None or r.ratio is None or r.ratio > 0.65 or not z.get("lung_z_extent_app_mm"): continue
    P.append(dict(expected=1 / r.ratio, measured=r.lung_z_extent_app_mm / z["lung_z_extent_app_mm"], cut=bool(r.lung_cut_z), resT=r.resT,
                  lung_first=r.lung_z_first, lung_last=r.lung_z_last, zfix_cut=bool(z.get("lung_cut_z"))))
P = pd.DataFrame(P)
P["within10"] = (P.measured / P.expected - 1).abs() <= 0.10
res["G2f_stretch"] = dict(n=len(P), within10_all=float(P.within10.mean()), n_cut=int(P.cut.sum()),
                          within10_not_cut=float(P[~P.cut].within10.mean()) if (~P.cut).any() else None, n_not_cut=int((~P.cut).sum()),
                          measured_over_expected_not_cut=np.percentile(P[~P.cut].measured / P[~P.cut].expected, [0, 50, 100]).round(3).tolist() if (~P.cut).any() else None,
                          cut_cases_lung_at_grid_edge=float(((P[P.cut].lung_first == 0) | (P[P.cut].lung_last == 199)).mean()) if P.cut.any() else None,
                          cut_cases_resampled_T=P[P.cut].resT.describe().round(0).to_dict() if P.cut.any() else None,
                          cut_by_ratio=P.groupby(P.expected.round(2)).cut.agg(["sum", "count"]).to_dict("index"))
# lung cut by the default crop, all pilot series, by stretch
M["stretch"] = 1 / M.ratio
res["lung_cut_z_by_stretch"] = M.groupby(M.stretch.round(2)).lung_cut_z.agg(["sum", "count"]).to_dict("index")
json.dump(res, open(out_p, "w"), indent=1, default=str)
print(json.dumps(res, indent=1, default=str))
