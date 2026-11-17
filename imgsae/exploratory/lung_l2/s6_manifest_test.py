"""Lung L2, step S6 part 1 (N4 item 2): the TEST manifest (docs/LUNG_L2_PROTOCOL.md sections 5, 7 and 11). Metadata and the split file only.
NO OUTCOME IS READ: from the split file only the split name of each participant and, for test participants, the series UIDs (the keys of
"exams") are used; the values (which hold cancer_in_1) are never accessed.

Rows (one per series to score):
  tier T1/T2/T3 = the split file's test series (one per exam; 6,715 in L1) of study year 0 / 1 / 2, variant 'main';
  tier T4       = soft-kernel partner of 500 T1 exams with a same-thickness pair of the other kernel class, variant 'pair'.
T5 (zfix) is not a row: the cloud job adds the 'zfix' variant to every 'main' row whose DICOM spacing/thickness <= 0.65 (--zfix-max 0.65).
The pair rule, the order and the row format are the code of s1_manifest.py (dev), shared here by both roots:
  same study, same thickness, other kernel class, slice count within 2%; one partner per study (lowest series number, then UID); 500 pairs,
  quota by the maker share of the available pairs (rounded; the rest to the largest maker), seed 0, random order inside each maker.
  Order: one fixed random permutation (seed 0) of the root's participants; within a tier rows are sorted by participant rank.
--root dev  : DEV CHECK ONLY. Main rows by the dev series rule (s1_manifest.py), the same pair logic; must reproduce manifest_dev.csv
              (all tiers D1 to D4, every column) exactly. Writes <out>/manifest_devcheck.csv and <out>/s6_manifest_devcheck.json.
--root test : the test list. Allowed only after the lead's OK of the new freeze is logged (step N3); it refuses to run without
              --lead-ok <freeze commit>. Writes <out>/manifest_test.csv and <out>/s6_manifest_test.json.
usage (venv python): python s6_manifest_test.py <nlst_series_meta.csv> <split pickle> <out dir> --root dev [--manifest-dev <csv>]
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, r"D:\Shayan\imgsae\exploratory\lung_l0")
import nlst_l0 as L  # noqa: E402
import series_rule as R  # noqa: E402

N_PILOT, N_PAIRS, SEED = 300, 500, 0
KEEP = ["SeriesInstanceUID", "PatientID", "study_yr", "StudyInstanceUID", "Manufacturer", "ManufacturerModelName", "ConvolutionKernel",
        "kclass", "thick", "vg_slice_spacing_mm", "instanceCount", "series_size_MB", "series_aws_url"]
COLS = ["series_uid", "pid", "study_yr", "tier", "variant", "order", "pos", "pilot", "partner_of", "Manufacturer", "ManufacturerModelName",
        "ConvolutionKernel", "kclass", "thick", "spacing_idc", "ratio_idc", "n_images", "size_mb", "url", "StudyInstanceUID"]


def rank_of(D):
    pids = np.array(sorted(D.PatientID.unique())); perm = np.random.default_rng(SEED).permutation(len(pids))
    return {p: int(r) for p, r in zip(pids[perm], range(len(pids)))}


def rows(df, tier, variant, rank):
    r = df[KEEP].rename(columns={"SeriesInstanceUID": "series_uid", "PatientID": "pid", "vg_slice_spacing_mm": "spacing_idc",
                                 "instanceCount": "n_images", "series_size_MB": "size_mb", "series_aws_url": "url"}).copy()
    r["tier"], r["variant"] = tier, variant
    r["order"] = r.pid.map(rank)
    r["ratio_idc"] = (r.spacing_idc / r.thick).round(3)
    return r


def pairs_of(base, cand):
    """soft-kernel partners of the baseline main series `base` (one row per study), from the candidate series `cand` (series_rule.candidates
    of the root's metadata): the pair rule and the quota of s1_manifest.py, unchanged."""
    j = base[["StudyInstanceUID", "SeriesInstanceUID", "thick", "instanceCount", "kclass", "Manufacturer"]].merge(cand, on="StudyInstanceUID", suffixes=("_sel", ""))
    j = j[(j.SeriesInstanceUID != j.SeriesInstanceUID_sel) & (j.thick == j.thick_sel) & (j.kclass != j.kclass_sel) &
          ((j.instanceCount - j.instanceCount_sel).abs() <= 0.02 * j.instanceCount_sel)]
    j = j.sort_values(["StudyInstanceUID", "SeriesNumber", "SeriesInstanceUID"]).drop_duplicates("StudyInstanceUID")
    rng = np.random.default_rng(SEED)
    share = j.Manufacturer_sel.value_counts(normalize=True)
    quota = (share * N_PAIRS).round().astype(int)
    quota.iloc[0] += N_PAIRS - quota.sum()
    pick = pd.concat([g.iloc[rng.permutation(len(g))[:quota[mf]]] for mf, g in j.groupby("Manufacturer_sel")])
    return pick, j


def build(m, sel, root, rank):
    """manifest frame from the main series `sel` (metadata rows, one per exam) of one root."""
    pre = {"dev": "D", "test": "T"}[root]
    main = rows(sel, pre, "main", rank); main["tier"] = main.study_yr.map({0: f"{pre}1", 1: f"{pre}2", 2: f"{pre}3"})
    D = m[m.grp == root]; pick, j = pairs_of(sel[sel.study_yr == 0], R.candidates(D))
    pairs = rows(pick, f"{pre}4", "pair", rank); pairs["partner_of"] = pick.SeriesInstanceUID_sel.values
    main["partner_of"] = ""
    man = pd.concat([main, pairs], ignore_index=True).sort_values(["tier", "order", "study_yr", "series_uid"]).reset_index(drop=True)
    man["pilot"] = False
    if root == "dev": man.loc[man.index[man.tier == "D1"][:N_PILOT], "pilot"] = True   # the dev pilot of S2 (no pilot on test)
    man["pos"] = man.groupby("tier").cumcount()
    return man[COLS], main, pairs, j


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("meta"); ap.add_argument("split"); ap.add_argument("out"); ap.add_argument("--root", required=True, choices=("dev", "test"))
    ap.add_argument("--manifest-dev", default=str(HERE / "results" / "manifest_dev.csv")); ap.add_argument("--lead-ok", default="")
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    if a.root == "test" and not a.lead_ok:
        raise SystemExit("REFUSED: the test list is built only after the lead's OK of the new freeze is logged (step N3); pass --lead-ok <freeze commit>")
    m = R.load_meta(a.meta); split = L.SafeUnpickler(open(a.split, "rb")).load()
    grp = {str(k): str(v["split"]) for k, v in split.items()}; m["grp"] = m.PatientID.map(grp).fillna("none")
    rank = rank_of(m[m.grp == a.root]); res = dict(root=a.root, script="s6_manifest_test.py")
    if a.root == "dev":
        D = m[m.grp == "dev"].copy(); sel = R.select(D, R.BEST_RULE)
        dup = sel.duplicated(["PatientID", "study_yr"], keep=False); sel = sel[~dup & sel.study_yr.isin([0, 1, 2])].copy()
        man, main_, pairs, j = build(m, sel, "dev", rank); man.to_csv(out / "manifest_devcheck.csv", index=False, lineterminator="\n")
        ref = pd.read_csv(a.manifest_dev, dtype={"pid": str}, keep_default_na=False); new = pd.read_csv(out / "manifest_devcheck.csv", dtype={"pid": str}, keep_default_na=False)
        same_shape = list(ref.columns) == list(new.columns) and len(ref) == len(new)
        neq = {c: int((ref[c].astype(str) != new[c].astype(str)).sum()) for c in ref.columns} if same_shape else None
        d4r, d4n = ref[ref.tier == "D4"], new[new.tier == "D4"]
        res.update(rows_by_tier=new.tier.value_counts().sort_index().to_dict(), same_shape=same_shape, differing_values_by_column=neq,
                   identical_to_manifest_dev=bool(same_shape and not any(neq.values())),
                   D4=dict(n_ref=int(len(d4r)), n_new=int(len(d4n)), same_pairs=bool(set(zip(d4r.series_uid, d4r.partner_of)) == set(zip(d4n.series_uid, d4n.partner_of))),
                           pairs_available=int(len(j)), by_maker=d4n.Manufacturer.value_counts().to_dict()))
        res["manifest_devcheck_sha256"] = hashlib.sha256((out / "manifest_devcheck.csv").read_bytes()).hexdigest()
        (out / "s6_manifest_devcheck.json").write_bytes((json.dumps(res, indent=1) + "\n").encode("utf-8"))
    else:
        series = {str(uid): str(pid) for pid, v in split.items() if str(v["split"]) == "test" for uid in v["exams"].keys()}   # keys only
        T = m[m.SeriesInstanceUID.isin(series)].copy()
        res.update(split_test_series=len(series), found_in_idc=int(T.SeriesInstanceUID.nunique()), pid_mismatch=int((T.PatientID != T.SeriesInstanceUID.map(series)).sum()),
                   duplicate_pid_year=int(T.duplicated(["PatientID", "study_yr"]).sum()), study_years=T.study_yr.value_counts().sort_index().to_dict(), lead_ok=a.lead_ok)
        if res["found_in_idc"] != len(series) or res["pid_mismatch"] or res["duplicate_pid_year"] or not T.study_yr.isin([0, 1, 2]).all():
            (out / "s6_manifest_test.json").write_text(json.dumps(res, indent=1)); raise SystemExit("STOP: the test series do not map one to one onto study years 0 to 2")
        man, main_, pairs, j = build(m, T, "test", rank); man.to_csv(out / "manifest_test.csv", index=False, lineterminator="\n")
        res.update(rows_by_tier=man.tier.value_counts().sort_index().to_dict(), participants=int(main_.pid.nunique()), pairs_available_T1=int(len(j)),
                   pairs_by_maker=pairs.Manufacturer.value_counts().to_dict(), zfix_expected_ratio_le_0p65=int((main_.ratio_idc <= 0.65).sum()),
                   total_size_gb=round(float(man.size_mb.sum() / 1024), 1), manifest_sha256=hashlib.sha256((out / "manifest_test.csv").read_bytes()).hexdigest())
        (out / "s6_manifest_test.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
