"""Lung L2, step S1 (free): the dev manifest (docs/LUNG_L2_PROTOCOL.md sections 5 and 7). Metadata only; no outcome is read.

Rows (one per series to score):
  tier D1/D2/D3 = selected series of dev baseline / year-1 / year-2 exams (rule series_rule.BEST_RULE), variant 'main';
  tier D4       = soft-kernel partner of 500 D1 exams with a same-thickness pair (seed 0, stratified by maker), variant 'pair'.
D5 (zfix) is not a row: the cloud job adds the 'zfix' variant to every 'main' row whose DICOM spacing/thickness <= the threshold.
Order: one fixed random permutation of dev participants (seed 0); within a tier rows are sorted by participant rank.
Pilot = the first 300 D1 rows. Duplicate person-years (two CT studies in one study year) are dropped entirely.
Gate S1: >= 95% of dev exams in the NLST tables (pid x study year) get a series; 0 duplicate pid-year.
usage: python s1_manifest.py <nlst_series_meta.csv> <tables dir> <split pickle> <out_dir>
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, r"D:\Shayan\imgsae\exploratory\lung_l0")
import nlst_l0 as L  # noqa: E402
import series_rule as R  # noqa: E402

meta_p, tables, split_p, out_d = sys.argv[1:5]
out_d = Path(out_d)
N_PILOT, N_PAIRS, SEED = 300, 500, 0
m = R.load_meta(meta_p)
split = L.SafeUnpickler(open(split_p, "rb")).load()
grp = {str(k): str(v["split"]) for k, v in split.items()}
m["grp"] = m.PatientID.map(grp).fillna("none")
D = m[m.grp == "dev"].copy()
sel = R.select(D, R.BEST_RULE)
dup = sel.duplicated(["PatientID", "study_yr"], keep=False)
dropped = sel[dup][["PatientID", "study_yr", "StudyInstanceUID"]]
sel = sel[~dup & sel.study_yr.isin([0, 1, 2])].copy()

pids = np.array(sorted(D.PatientID.unique()))
perm = np.random.default_rng(SEED).permutation(len(pids))
rank = {p: int(r) for p, r in zip(pids[perm], range(len(pids)))}

KEEP = ["SeriesInstanceUID", "PatientID", "study_yr", "StudyInstanceUID", "Manufacturer", "ManufacturerModelName", "ConvolutionKernel",
        "kclass", "thick", "vg_slice_spacing_mm", "instanceCount", "series_size_MB", "series_aws_url"]


def rows(df, tier, variant):
    r = df[KEEP].rename(columns={"SeriesInstanceUID": "series_uid", "PatientID": "pid", "vg_slice_spacing_mm": "spacing_idc",
                                 "instanceCount": "n_images", "series_size_MB": "size_mb", "series_aws_url": "url"}).copy()
    r["tier"], r["variant"] = tier, variant
    r["order"] = r.pid.map(rank)
    r["ratio_idc"] = (r.spacing_idc / r.thick).round(3)
    return r


main = rows(sel, "D", "main")
main["tier"] = main.study_yr.map({0: "D1", 1: "D2", 2: "D3"})
# D4: soft partners of D1 exams that have a same-thickness pair of the other kernel class (as in s0_pairs_count.py)
cand = R.candidates(D)
b = sel[sel.study_yr == 0]
j = b[["StudyInstanceUID", "SeriesInstanceUID", "thick", "instanceCount", "kclass", "Manufacturer"]].merge(
    cand, on="StudyInstanceUID", suffixes=("_sel", ""))
j = j[(j.SeriesInstanceUID != j.SeriesInstanceUID_sel) & (j.thick == j.thick_sel) & (j.kclass != j.kclass_sel) &
      ((j.instanceCount - j.instanceCount_sel).abs() <= 0.02 * j.instanceCount_sel)]
j = j.sort_values(["StudyInstanceUID", "SeriesNumber", "SeriesInstanceUID"]).drop_duplicates("StudyInstanceUID")
rng = np.random.default_rng(SEED)
share = j.Manufacturer_sel.value_counts(normalize=True)
quota = (share * N_PAIRS).round().astype(int)
quota.iloc[0] += N_PAIRS - quota.sum()
pick = pd.concat([g.iloc[rng.permutation(len(g))[:quota[mf]]] for mf, g in j.groupby("Manufacturer_sel")])
pairs = rows(pick, "D4", "pair")
pairs["partner_of"] = pick.SeriesInstanceUID_sel.values
main["partner_of"] = ""
man = pd.concat([main, pairs], ignore_index=True).sort_values(["tier", "order", "study_yr", "series_uid"]).reset_index(drop=True)
man["pilot"] = False
d1 = man.index[man.tier == "D1"]
man.loc[d1[:N_PILOT], "pilot"] = True
man["pos"] = man.groupby("tier").cumcount()          # position within the tier (shards use tier + [lo, hi) of pos)
out_d.mkdir(parents=True, exist_ok=True)
cols = ["series_uid", "pid", "study_yr", "tier", "variant", "order", "pos", "pilot", "partner_of", "Manufacturer", "ManufacturerModelName",
        "ConvolutionKernel", "kclass", "thick", "spacing_idc", "ratio_idc", "n_images", "size_mb", "url", "StudyInstanceUID"]
man[cols].to_csv(out_d / "manifest_dev.csv", index=False)

# ---- gate: coverage of the dev exams in the NLST tables (exam = pid x study year with a screen result)
ex = L.build(tables, split_p)["ex"]
dev_ex = ex[ex.grp == "dev"][["pid", "study_yr"]].astype({"pid": str})
have = set(zip(main.pid, main.study_yr.astype(int)))
cov = np.mean([(p, int(y)) in have for p, y in zip(dev_ex.pid, dev_ex.study_yr)])
in_idc_not_table = len(have - set(zip(dev_ex.pid, dev_ex.study_yr.astype(int))))
res = {"dev_table_exams": int(len(dev_ex)), "dev_main_rows": int(len(main)), "coverage_of_table_exams": round(float(cov), 4),
       "gate_coverage_ge_0.95": bool(cov >= 0.95), "dup_pid_year_after_drop": int(main.duplicated(["pid", "study_yr"]).sum()),
       "dropped_duplicate_studies": dropped.astype(str).to_dict("records"), "main_rows_not_in_tables": int(in_idc_not_table),
       "rows_by_tier": man.tier.value_counts().sort_index().to_dict(), "pilot_rows": int(man.pilot.sum()),
       "zfix_expected_ratio_le_0.65": int(((main.ratio_idc <= 0.65)).sum()),
       "zfix_expected_pilot_ratio_lt_0.95": int(((man.pilot) & (man.ratio_idc < 0.95)).sum()),
       "ratio_idc_missing_main": int(main.ratio_idc.isna().sum()),
       "pairs_by_maker": pairs.Manufacturer.value_counts().to_dict(), "pairs_available_D1": int(len(j)),
       "total_size_gb": round(float(man.size_mb.sum() / 1024), 1), "participants": int(main.pid.nunique())}
res["manifest_sha256"] = hashlib.sha256((out_d / "manifest_dev.csv").read_bytes()).hexdigest()
(out_d / "s1_manifest.json").write_text(json.dumps(res, indent=1))
print(json.dumps({k: v for k, v in res.items() if k != "dropped_duplicate_studies"}, indent=1))
