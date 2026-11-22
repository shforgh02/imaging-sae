"""Lung L2, plan X12 (docs/EXECUTION_LOG.md, 22 Nov, commit 2b88e20; task 3): how common are overlapping CT reconstructions in modern chest
CT? Metadata only (local IDC index v25.0.5); no image, no outcome. EXPLORATORY.
usage (sybil env python, -I; needs pyarrow): python -I x12_overlap_prevalence.py <idc index dir> <out dir>
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PHANTOM = {"phantom_fda", "ct4harmonization_multicentric", "ct_phantom4radiomics", "cc_radiomics_phantom", "cc_radiomics_phantom_2", "cc_radiomics_phantom_3",
           "qiba_ct_liver_phantom", "qiba_ct_1c", "rider_phantom_pet_ct", "dro_toolkit", "uw_cirp_mouse_pet_ct_nsclc"}
CHEST_COLL = {"nlst", "lidc_idri", "covid_19_ny_sbu", "midrc_ricord_1a", "midrc_ricord_1b", "covid_19_ar", "cmb_lca", "varepop_apollo", "lung_pet_ct_dx",
              "anti_pd_1_lung", "cptac_luad", "cptac_lscc", "tcga_luad", "tcga_lusc", "nsclc_radiomics", "nsclc_radiogenomics", "nsclc_radiomics_genomics",
              "rider_lung_ct", "lungct_diagnosis", "qin_lung_ct", "lung_fused_ct_pathology", "spie_aapm_lung_ct_challenge"}
CHEST_WORD = re.compile(r"CHEST|THORAX|THORAC|LUNG|THX|PULM", re.I)
DEF_EDGE = re.compile(r"SOMATOM\s*DEFINITION\s*EDGE", re.I)   # launched 2012: sensitivity only (Neon review of X12)
MODERN_COLL = {"covid_19_ny_sbu", "midrc_ricord_1a", "midrc_ricord_1b", "covid_19_ar"}          # plus every cmb_* collection
MODERN_MODEL = re.compile(r"REVOLUTION\s*(?:CT|EVO|FRONTIER|APEX|MAXIMA|ACT)|SOMATOM\s*(?:FORCE|DRIVE|EDGE\s*PLUS|CONFIDENCE|GO\.|X\.CITE|X\.CEED)|NAEOTOM|"
                          r"IQON|INCISIVE|CT\s*5300|SPECTRAL\s*CT\s*7500|AQUILION\s*ONE\s*(?:GENESIS|PRISM)|AQUILION\s*PRIME\s*SP|AQUILION\s*LIGHTNING|"
                          r"AQUILION\s*PRECISION|AQUILION\s*EXCEED|AQUILION\s*SERVE", re.I)
BAD_TYPE = re.compile(r"LOCALIZER|SCOUT|\bMIP\b|MINIP|\bAIP\b|\bMPR\b|REFORMATTED|PROJECTION|SCREEN SAVE|DOSE|SECONDARY", re.I)
BAD_MAKER = re.compile(r"RIVERAIN|ADAC|CMS, INC|VARIAN|ELEKTA|BRAINLAB|ACCURAY|TOMOTHERAPY", re.I)   # post-processing / radiotherapy systems
BAD_DESC = re.compile(r"\bMIP\b|MINIP|\bAIP\b|\bMPR\b|\bCOR\b|CORON|\bSAG\b|SAGIT|SCOUT|TOPO|LOCALI|SURVIEW|BOLUS|SMARTPREP|DOSE\s*(?:REPORT|INFO)|PATIENT\s*PROTOCOL|\b3D\b|\bVR\b", re.I)
CLASSES = [("le_0p65", 0, 0.65), ("0p65_0p85", 0.65, 0.85), ("0p85_0p95", 0.85, 0.95), ("0p95_1p05", 0.95, 1.05), ("gt_1p05", 1.05, 99)]


def cls(r):
    for nm, lo, hi in CLASSES:
        if (r > lo if lo > 0 else r > 0) and r <= hi: return nm
    return "none"


def boot_share(flag, groups, n=2000, seed=0):
    """share of True among units, 95% interval by resampling the groups (patients)."""
    flag = np.asarray(flag, bool); g = pd.Series(groups).astype(str).to_numpy(); u, inv = np.unique(g, return_inverse=True)
    s = np.bincount(inv, weights=flag.astype(float)); c = np.bincount(inv); rng = np.random.default_rng(seed); d = []
    for _ in range(n):
        k = rng.integers(0, len(u), len(u)); d.append(s[k].sum() / c[k].sum())
    return dict(share=float(flag.mean()) if len(flag) else None, lo=float(np.percentile(d, 2.5)) if len(flag) else None, hi=float(np.percentile(d, 97.5)) if len(flag) else None,
                units=int(len(flag)), patients=int(len(u)))


def main():
    D, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    ix = pd.read_parquet(D / "idc_index.parquet", columns=["collection_id", "analysis_result_id", "PatientID", "SeriesInstanceUID", "StudyInstanceUID", "StudyDate", "StudyDescription",
                                                           "BodyPartExamined", "Modality", "SOPClassUID", "Manufacturer", "ManufacturerModelName", "SeriesDescription", "instanceCount", "license_short_name"])
    ct = pd.read_parquet(D / "ct_index.parquet", columns=["SeriesInstanceUID", "ImageType", "Rows", "Columns", "SliceThickness", "ConvolutionKernel"])
    vg = pd.read_parquet(D / "volume_geometry_index.parquet")
    att = []; X = ix[ix.Modality == "CT"]; att.append(("CT series", len(X)))
    X = X[X.analysis_result_id.isna()]; att.append(("not an analysis result", len(X)))
    X = X[X.SOPClassUID == "1.2.840.10008.5.1.4.1.1.2"]; att.append(("CT Image Storage", len(X)))
    X = X[~X.collection_id.isin(PHANTOM) & ~X.collection_id.str.contains("phantom")]; att.append(("not phantom or animal", len(X)))
    X = X.merge(ct, on="SeriesInstanceUID", how="inner").merge(vg, on="SeriesInstanceUID", how="left"); att.append(("with a CT header record", len(X)))
    flags = ["single_orientation", "orthogonal_orientation", "unique_slice_positions", "consistent_in_plane_row", "consistent_in_plane_col", "consistent_pixel_spacing",
             "consistent_image_dimensions", "uniform_slice_spacing"]
    geo_fail = {f: int((X[f].astype("boolean").fillna(False) != True).sum()) for f in flags if f in X.columns}   # noqa: E712
    geo_fail["no_geometry_record"] = int(X.regularly_spaced_3d_volume.isna().sum())
    X = X[X.regularly_spaced_3d_volume.astype("boolean").fillna(False)]; att.append(("regularly spaced 3D volume", len(X)))
    X["SliceThickness"] = pd.to_numeric(X.SliceThickness, errors="coerce"); X = X[(X.SliceThickness >= 0.2) & (X.SliceThickness <= 15)]; att.append(("SliceThickness 0.2 to 15 mm", len(X)))
    iop = np.stack(X.ImageOrientationPatient.to_numpy()).astype(float); nz = np.abs(np.cross(iop[:, :3], iop[:, 3:])[:, 2])
    X = X[nz >= 0.95]; att.append(("axial (|n_z| >= 0.95)", len(X)))
    it = X.ImageType.apply(lambda a: "\\".join(str(t) for t in (a if a is not None else [])))
    X = X[~it.str.contains(BAD_TYPE)]; att.append(("ImageType not scout / MIP / AIP / reformat / secondary / dose", len(X)))
    X = X[~X.Manufacturer.fillna("").str.contains(BAD_MAKER)]; att.append(("not a post-processing or radiotherapy system", len(X)))
    X = X[~X.SeriesDescription.fillna("").str.contains(BAD_DESC)]; att.append(("description not MIP / reformat / scout / dose", len(X)))
    X = X[(X.Rows >= 256) & (X.Columns >= 256) & (X.instanceCount >= 30)]; att.append(("matrix >= 256, >= 30 images", len(X)))
    zc = (X.instanceCount - 1) * X.slice_spacing_mm; X = X[(zc >= 150) & (zc <= 450)]; att.append(("z coverage 150 to 450 mm (chest, not chest-abdomen-pelvis)", len(X)))
    chest = X.collection_id.isin(CHEST_COLL) | X.BodyPartExamined.fillna("").str.contains(CHEST_WORD) | X.StudyDescription.fillna("").str.contains(CHEST_WORD) | X.SeriesDescription.fillna("").str.contains(CHEST_WORD)
    X = X[chest].copy(); att.append(("chest", len(X)))
    X["ratio"] = (X.slice_spacing_mm / X.SliceThickness).round(3); X["cls"] = X.ratio.apply(cls)
    X["band"] = np.where(X.SliceThickness <= 1.25, "le_1p25", np.where(X.SliceThickness <= 3.0, "1p25_3p0", "gt_3p0")); X["sybil_range"] = X.SliceThickness <= 3.0
    X["original"] = X.ImageType.apply(lambda a: "ORIGINAL" in {str(t).upper() for t in (a if a is not None else [])})
    X["modern_model"] = X.ManufacturerModelName.fillna("").str.contains(MODERN_MODEL); X["modern_or_def_edge"] = X.modern_model | X.ManufacturerModelName.fillna("").str.contains(DEF_EDGE)
    X["maker"] = X.Manufacturer.fillna("?").str.upper().str.replace(r"SIEMENS.*", "SIEMENS", regex=True).str.replace(r"^(TOSHIBA|CANON).*", "TOSHIBA/CANON", regex=True).str.replace(r"^GE .*", "GE", regex=True).str.replace(r"^PHILIPS.*", "PHILIPS", regex=True)
    X["modern_coll"] = X.collection_id.isin(MODERN_COLL) | X.collection_id.str.startswith("cmb_")
    X["pkey"] = X.collection_id + "|" + X.PatientID.astype(str); X["ov65"] = X.cls == "le_0p65"; X["ov85"] = X.ratio <= 0.85
    res = dict(label="X12 (plan 2b88e20; exploratory; metadata only)", attrition=att, geometry_flags_failed_among_ct_header_rows=geo_fail,
               ratio_classes={nm: [lo, hi] for nm, lo, hi in CLASSES})
    # per collection (series level, Sybil thickness range)
    S = X[X.sybil_range]
    per = S.groupby("collection_id").agg(series=("SeriesInstanceUID", "size"), patients=("pkey", "nunique"), le_0p65=("ov65", "mean"), le_0p85=("ov85", "mean"),
                                         modern_model_share=("modern_model", "mean"), license=("license_short_name", "first")).reset_index().sort_values("series", ascending=False)
    per.to_csv(out / "x12_per_collection.csv", index=False)
    res["per_collection_summary"] = dict(n_collections=int(len(per)), collections_ge_20_patients=int((per.patients >= 20).sum()),
                                         le_0p65_median_range=[float(per[per.patients >= 20].le_0p65.median()), float(per[per.patients >= 20].le_0p65.min()), float(per[per.patients >= 20].le_0p65.max())],
                                         le_0p85_median_range=[float(per[per.patients >= 20].le_0p85.median()), float(per[per.patients >= 20].le_0p85.min()), float(per[per.patients >= 20].le_0p85.max())])

    def study_level(Q):
        g = Q.groupby(["pkey", "StudyInstanceUID"]); a = g.ov65.agg(["any", "all"]); a85 = g.ov85.agg(["any", "all"]); cont = g.cls.apply(lambda c: (c == "0p95_1p05").any())
        T = pd.DataFrame(dict(pkey=[k[0] for k in a.index], any65=a["any"].to_numpy(), only65=a["all"].to_numpy(), any85=a85["any"].to_numpy(), only85=a85["all"].to_numpy(), cont=cont.to_numpy()))
        T["both65"] = T.any65 & T.cont
        return T

    def summary(Q, name):
        Q = Q[Q.sybil_range]
        if len(Q) == 0: return dict(note="no series")
        T = study_level(Q); P = Q.groupby("pkey").agg(any65=("ov65", "any"), any85=("ov85", "any"))
        return dict(series=int(len(Q)), studies=int(len(T)), patients=int(Q.pkey.nunique()), collections=int(Q.collection_id.nunique()),
                    series_le_0p65=boot_share(Q.ov65, Q.pkey), series_le_0p85=boot_share(Q.ov85, Q.pkey),
                    studies_any_le_0p65=boot_share(T.any65, T.pkey), studies_only_le_0p65=boot_share(T.only65, T.pkey), studies_both_le_0p65_and_contiguous=boot_share(T.both65, T.pkey),
                    studies_any_le_0p85=boot_share(T.any85, T.pkey), patients_any_le_0p65=boot_share(P.any65, P.index), patients_any_le_0p85=boot_share(P.any85, P.index),
                    by_band={b: dict(series=int((Q.band == b).sum()), le_0p65=float(Q.ov65[Q.band == b].mean()) if (Q.band == b).any() else None,
                                     le_0p85=float(Q.ov85[Q.band == b].mean()) if (Q.band == b).any() else None) for b in ("le_1p25", "1p25_3p0")},
                    by_maker={m: dict(series=int((Q.maker == m).sum()), le_0p65=float(Q.ov65[Q.maker == m].mean()), le_0p85=float(Q.ov85[Q.maker == m].mean()))
                              for m in Q.maker.value_counts().index[:8]},
                    studies_only_le_0p85=boot_share(T.only85, T.pkey), studies_both_le_0p85_and_contiguous=boot_share(T.any85 & T.cont, T.pkey),
                    collections_table={c: dict(patients=int(Q.pkey[Q.collection_id == c].nunique()), le_0p65=float(Q.ov65[Q.collection_id == c].mean()), le_0p85=float(Q.ov85[Q.collection_id == c].mean())) for c in Q.collection_id.unique()},
                    classes={c: int((Q.cls == c).sum()) for c, _, _ in CLASSES})
    sets = {"all_chest": X, "nlst": X[X.collection_id == "nlst"], "non_nlst_chest": X[X.collection_id != "nlst"],
            "modern_scanner_models": X[X.modern_model], "modern_collections_2015_on": X[X.modern_coll],
            "modern_scanner_models_original_only": X[X.modern_model & X.original], "modern_models_incl_definition_edge_2012": X[X.modern_or_def_edge],
            "modern_collections_2015_on_original_only": X[X.modern_coll & X.original]}
    res["sets"] = {k: summary(v, k) for k, v in sets.items()}
    # deduplicated sensitivity: one series per study and identical geometry
    X["sp2"] = X.slice_spacing_mm.round(2); Mx = X[X.modern_model & X.sybil_range]
    res["dedup_modern_scanner_models"] = summary(Mx.drop_duplicates(["pkey", "StudyInstanceUID", "SliceThickness", "sp2", "instanceCount"]), "dedup")
    M = X[X.modern_model & X.sybil_range]
    res["modern_model_strings"] = M.ManufacturerModelName.value_counts().to_dict()
    res["modern_top_protocols"] = M.assign(p=M.SliceThickness.round(3).astype(str) + "/" + M.slice_spacing_mm.round(3).astype(str)).p.value_counts().head(15).to_dict()
    yr = pd.to_numeric(X.StudyDate.astype(str).str[:4], errors="coerce"); res["studydate_year_diagnostic"] = yr.value_counts(bins=[1900, 1990, 2005, 2010, 2015, 2020, 2027]).sort_index().astype(int).to_dict()
    res["studydate_year_diagnostic"] = {str(k): int(v) for k, v in res["studydate_year_diagnostic"].items()}
    qc = X[X.modern_model & X.ov65 & X.sybil_range].sample(n=min(50, int((X.modern_model & X.ov65 & X.sybil_range).sum())), random_state=0)
    qc[["collection_id", "SeriesDescription", "ImageType", "SliceThickness", "slice_spacing_mm", "instanceCount", "ManufacturerModelName"]].assign(ImageType=lambda q: q.ImageType.apply(lambda a: "\\".join(a) if a is not None else "")).to_csv(out / "x12_qc_sample.csv", index=False)
    X[X.sybil_range][["collection_id", "Manufacturer", "modern_model", "SliceThickness", "slice_spacing_mm"]].round(3).groupby(["Manufacturer", "modern_model", "SliceThickness", "slice_spacing_mm"]).size().rename("series").reset_index().to_csv(out / "x12_scatter_counts.csv", index=False)
    (out / "x12_overlap_prevalence.json").write_bytes((json.dumps(res, indent=1, default=str) + "\n").encode("utf-8")); print("written", out)


if __name__ == "__main__":
    main()
