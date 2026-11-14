"""Lung L2: assemble one exam table + activation arrays from the PC copy of the volume (docs/LUNG_L2_PROTOCOL.md sections 6 and 9.3).
Same code for dev (S4) and, after the freeze, test (S6).
usage: python l2_data.py <volume copy dir (…/l2)> <root: dev|test> <manifest csv> <nlst_series_meta.csv> <tables dir> <split pickle> <form params json> <out_dir>
Writes <out_dir>/exams_<root>.csv, <out_dir>/arrays_<root>_<variant>.npz (variant main, zfix, pair) and <out_dir>/assemble_<root>.json.
"""
import glob
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, r"D:\Shayan\imgsae\exploratory\lung_l0")
import l2_form  # noqa: E402
import nlst_l0 as L  # noqa: E402
import series_rule as R  # noqa: E402

YEAR = 365.25
ARR_KEYS = ("h", "pre", "pooled", "raw_haz", "base_haz", "logit", "att_vol1", "att_vol2")
CEN = ["loclhil", "locrhil", "loclmsb", "locrmsb", "loccar", "locmed"]
MEASURES = ["lung_vol_ml", "laa950_pct", "lung_p15_hu", "lung_mean_hu", "body_area_cm2", "air_noise_sd_hu", "lung_z_extent_mm"]


def histology(m):
    m = pd.to_numeric(m, errors="coerce")
    return np.select([m.isin([8140, 8250, 8251, 8252, 8253, 8254, 8255, 8260, 8310, 8323, 8480, 8481, 8490, 8550]),
                      m.isin([8052, 8070, 8071, 8072, 8073, 8074]), m.isin([8041, 8042, 8043, 8044, 8045])],
                     ["adeno", "squamous", "small_cell"], "other")


def stage_group(s):
    s = pd.to_numeric(s, errors="coerce")
    return np.select([s.isin([110, 120]), s.isin([210, 220, 310, 320]), s == 400], ["I", "II_III", "IV"], "unknown")


def read_variant(vdir):
    recs, arrs = [], {k: [] for k in ARR_KEYS}
    for j in sorted(glob.glob(str(vdir / "*.json"))):
        recs.append(json.load(open(j))); z = np.load(j[:-5] + ".npz")
        for k in ARR_KEYS: arrs[k].append(z[k])
    return recs, {k: (np.stack(v) if v else np.zeros((0,))) for k, v in arrs.items()}


def flat(recs):
    rows = []
    for r in recs:
        g, t, me = r.get("geo", {}), r.get("tags", {}), r.get("measures", {})
        d = dict(series_uid=r["series_uid"], pid=str(r["pid"]), study_yr=int(r["study_yr"]), tier=r.get("tier"), variant=r["variant"],
                 partner_of=r.get("partner_of", ""))
        d.update({f"s{t_ + 1}": r["calib"][t_] for t_ in range(6)}); d.update({f"mp{t_ + 1}": r["mean_prob"][t_] for t_ in range(6)})
        for k in ("n_images", "thickness", "true_spacing", "ratio", "n_zero_steps"): d[k] = g.get(k)
        sh = g.get("resampled_shape_main") or [None] * 4
        d["resampled_T"], d["resampled_H"] = sh[3], sh[1]
        for k in ("KVP", "Exposure", "XRayTubeCurrent", "ExposureTime", "ReconstructionDiameter", "GantryDetectorTilt", "SpiralPitchFactor", "CTDIvol"):
            d[f"tag_{k}"] = pd.to_numeric(t.get(k), errors="coerce") if t.get(k) is not None else np.nan
        d["tag_kernel"], d["tag_model"], d["tag_maker"] = t.get("ConvolutionKernel"), t.get("ManufacturerModelName"), t.get("Manufacturer")
        for k, v in me.items():
            if not isinstance(v, (list, dict)): d[f"m_{k}"] = v
        d.update({f"sec_{k}": v for k, v in r.get("sec", {}).items()})
        rows.append(d)
    return pd.DataFrame(rows)


def groups(df):
    """variable groups of protocol section 9.3 (column lists present in df)."""
    N = [c for c in df.columns if c.startswith("N_")]
    B = [c for c in df.columns if c.startswith("B_")]
    D = ["D_age", "D_male", "D_current_smoker", "D_race_black", "D_race_other", "D_study_yr"]
    I = [f"I_{k}" for k in MEASURES]
    T = [c for c in df.columns if c.startswith("T_")]
    return {"N": N, "B": B, "D": [c for c in D if c in df], "I": [c for c in I if c in df], "T": T}


def build_exams(main, b, meta, man, form):
    X, ex, prsn, read = b["X"], b["ex"], b["prsn"], b["read"]
    X = X.assign(pid=X.pid.astype(int).astype(str))
    E = main.merge(X, on=["pid", "study_yr"], how="left", suffixes=("", "_x"))
    E["late"] = np.where(E.dt.notna() & (E.dt > YEAR) & (E.dt <= 6 * YEAR), 1.0, np.where(E.dt.isna() & (E.fu >= 6 * YEAR), 0.0, np.nan))
    E.loc[E.positive_call != 0, "late"] = np.nan
    E.loc[E.study_yr != 0, "late"] = np.nan
    E["F1"] = l2_form.predict_logit(form["F1"], E)
    E["F6"] = l2_form.predict_logit(form["F6"], E)
    # N, B (recorded findings); B adds ab60 / ab64 / ab65 from ctab
    for c in read:
        if not c.startswith("ab"): E[f"N_{c}"] = E[c]
    ctab = pd.read_csv(next(Path(b["tables"]).glob("*ctab_idc*.csv")), low_memory=False)
    for c in ("sct_ab_desc", "study_yr", "pid"): ctab[c] = pd.to_numeric(ctab[c], errors="coerce")
    o = ctab[ctab.sct_ab_desc.between(52, 65)]
    fl = pd.crosstab([o.pid.astype(int).astype(str), o.study_yr.astype(int)], o.sct_ab_desc.astype(int)).clip(upper=1)
    fl.columns = [f"B_ab{c}" for c in fl.columns]; fl = fl.reset_index().rename(columns={"study_yr": "study_yr"})
    fl.columns = ["pid", "study_yr"] + list(fl.columns[2:])
    E = E.merge(fl, on=["pid", "study_yr"], how="left")
    for c in [c for c in E.columns if c.startswith("B_ab")]: E[c] = E[c].fillna(0)
    # D
    E["D_age"], E["D_male"] = E.age_scan, (E.gender == 1).astype(int)
    E["D_current_smoker"], E["D_study_yr"] = (E.cigsmok == 1).astype(int), E.study_yr
    race = pd.to_numeric(prsn.set_index(prsn.pid.astype(int).astype(str)).race, errors="coerce")
    E["race"] = E.pid.map(race)
    E["D_race_black"], E["D_race_other"] = (E.race == 2).astype(int), (~E.race.isin([1, 2])).astype(int)
    # I (protocol amendment A2: lung volume < 1,500 ml = segmentation leaked; measures missing, flag the lung at the image edge)
    seg_bad = pd.to_numeric(E.get("m_lung_vol_ml"), errors="coerce").fillna(0) < 1500
    for k in MEASURES: E[f"I_{k}"] = np.where(seg_bad, np.nan, pd.to_numeric(E.get(f"m_{k}"), errors="coerce"))
    E["T_lung_at_edge"] = seg_bad.astype(int)
    # T: IDC metadata + DICOM tags + geometry + the radiologist's quality items
    mm = meta.set_index("SeriesInstanceUID")
    E["T_maker"] = E.series_uid.map(mm.Manufacturer)
    mod = E.series_uid.map(mm.ManufacturerModelName)
    vc = mod.value_counts()
    E["T_model"] = np.where(mod.map(vc).fillna(0) >= 50, mod, "other")
    E["T_kclass_sharp"] = (E.series_uid.map(mm.kclass) == "sharp").astype(int)
    E["T_sharp_rank"] = E.series_uid.map(mm.sharp)
    E["T_sharp_rank"] = E.groupby("T_maker").T_sharp_rank.rank(pct=True)
    E["T_thickness"], E["T_zstretch"] = E.thickness, E.thickness / E.true_spacing
    E["T_thick_gt_2p5"] = (E.thickness > 2.5).astype(int)
    E["T_kvp"], E["T_exposure"], E["T_tube_current"] = E.tag_KVP, E.tag_Exposure, E.tag_XRayTubeCurrent
    E["T_recon_diameter"], E["T_n_images"] = E.tag_ReconstructionDiameter, E.n_images
    E["T_scan_length_mm"] = E.n_images * E.true_spacing
    E["T_tilt"] = (E.tag_GantryDetectorTilt.fillna(0).abs() > 0).astype(int)
    E["T_regular_3d"] = E.series_uid.map(mm.vg_regularly_spaced_3d_volume).astype(float)
    E["T_n_real_slices"] = E.get("m_n_real_slices")
    E["T_lung_cut_z"], E["T_lung_cut_xy"] = E.get("m_lung_cut_z").astype(float), E.get("m_lung_cut_xy").astype(float)
    scr = pd.read_csv(next(Path(b["tables"]).glob("*screen*.csv")), low_memory=False)
    scr["pid"] = pd.to_numeric(scr.pid, errors="coerce").astype("Int64").astype(str); scr["study_yr"] = pd.to_numeric(scr.study_yr, errors="coerce")
    q = scr[["pid", "study_yr", "ctdxqual", "ctdxqual_breath", "ctdxqual_motion", "ctdxqual_artifact", "ctdxqual_graininess"]].drop_duplicates(["pid", "study_yr"])
    E = E.merge(q, on=["pid", "study_yr"], how="left")
    E["T_q_limited"] = (E.ctdxqual >= 2).astype(int)
    for k in ("breath", "motion", "artifact", "graininess"): E[f"T_q_{k}"] = E[f"ctdxqual_{k}"].fillna(0).astype(int)
    # cancer descriptors (participant level; for exams of participants with a later cancer)
    canc = pd.read_csv(next(Path(b["tables"]).glob("*canc*.csv")), low_memory=False)
    canc["pid"] = pd.to_numeric(canc.pid, errors="coerce").astype("Int64").astype(str)
    c1 = canc[pd.to_numeric(canc.lc_order, errors="coerce") == 1].drop_duplicates("pid").set_index("pid")
    E["c_histology"] = E.pid.map(pd.Series(histology(c1.lc_morph), index=c1.index))
    E["c_stage"] = E.pid.map(pd.Series(stage_group(c1.de_stag_7thed), index=c1.index))
    E["c_lesion_mm"] = E.pid.map(pd.to_numeric(c1.lesionsize, errors="coerce"))
    P = prsn.assign(pid=prsn.pid.astype(int).astype(str)).set_index("pid")
    loc = {"central": CEN, "upper": ["loclup", "locrup"], "middle": ["locrmid", "loclin"], "lower": ["locllow", "locrlow"]}
    for k, cols in loc.items():
        E[f"c_loc_{k}"] = E.pid.map((P[cols].apply(pd.to_numeric, errors="coerce").fillna(0).sum(1) > 0).astype(int))
    for c in [c for c in E.columns if c.startswith("c_")]:
        E.loc[E.dt.isna(), c] = np.nan
    return E


def main():
    vol_d, root, man_p, meta_p, tables, split_p, form_p, out_d = sys.argv[1:9]
    vol_d, out_d = Path(vol_d), Path(out_d); out_d.mkdir(parents=True, exist_ok=True)
    b = L.build(tables, split_p); b["tables"] = tables
    meta = R.load_meta(meta_p)
    man = pd.read_csv(man_p, dtype={"pid": str})
    form = json.load(open(form_p))
    info = dict(root=root, form_params_sha256=hashlib.sha256(Path(form_p).read_bytes()).hexdigest())
    frames = {}
    for var in ("main", "zfix", "pair"):
        recs, arr = read_variant(vol_d / root / var)
        if not recs: continue
        f = flat(recs); frames[var] = f
        np.savez(out_d / f"arrays_{root}_{var}.npz", series_uid=f.series_uid.to_numpy(), **arr)
        info[f"n_{var}"] = len(f)
    E = build_exams(frames["main"], b, meta, man, form)
    assert E.series_uid.is_unique and not E.duplicated(["pid", "study_yr"]).any()
    E.to_csv(out_d / f"exams_{root}.csv", index=False)
    for var in ("zfix", "pair"):
        if var in frames: frames[var].to_csv(out_d / f"variant_{root}_{var}.csv", index=False)
    g = groups(E)
    info.update(n_exams=len(E), participants=int(E.pid.nunique()), groups={k: len(v) for k, v in g.items()},
                outcomes={y: dict(pos=int((E[y] == 1).sum()), neg=int((E[y] == 0).sum())) for y in ("y1", "y2", "y6", "late")},
                missing_I=int(E.I_lung_vol_ml.isna().sum()), unmatched_table=int(E.age.isna().sum()))
    (out_d / f"assemble_{root}.json").write_text(json.dumps(info, indent=1, default=str))
    print(json.dumps(info, indent=1, default=str))


if __name__ == "__main__":
    main()
