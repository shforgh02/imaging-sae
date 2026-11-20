"""Lung L2, plan O2 (docs/O2_PLAN.md): the scoring list of the NLST participants Sybil never used ("unseen": CT-arm participants in IDC that
are in none of Sybil's splits). Tiers U1 and U2 come from PUBLIC METADATA ONLY (IDC series metadata + Sybil's split file; no image, no
outcome, no NLST table). Tier U3 (the form sample) is added only after the O2 freeze, with --add-u3, and is the only step that reads an
outcome (to find the exams of participants with a lung cancer).
Selection (as x6_unseen_metadata.py): the dev series rule (series_rule.BEST_RULE), one series per participant and screen year, years 0-2,
studies with two chosen series for one year dropped. IDC ratio = vg_slice_spacing_mm / SliceThickness.
  U1: stretched candidates, IDC ratio <= 0.70 (the job's own DICOM geometry decides the z-fix at <= 0.65, as frozen); fixed random order of
      the participants (seed 0), so any first part of the list is a random subset.
  U2: the not-U1 exams that are the consecutive-year neighbour (same participant, year +-1) of a U1 exam (the partners of the pairs that
      change stretch status); same participant order.
  U3 (--add-u3, after the freeze): every exam (years 0-2) of an unseen participant with a lung cancer diagnosis (NLST prsn candx_days), plus a
      random sample of 800 unseen exams (seed 1, drawn from the list before any outcome is read); rows already in U1 or U2 are not repeated.
Writes <out>/manifest_unseen.csv (the row format of manifest_dev.csv), its gzip copy (level 9, mtime 0, LF bytes) and <out>/o2_manifest.json.
usage (venv python): python o2_manifest.py <nlst_series_meta.csv> <split pickle> <out dir> [--add-u3 <nlst tables dir>]
"""
import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "lung_l0"))
import nlst_l0 as L  # noqa: E402
import series_rule as R  # noqa: E402

COLS = ["series_uid", "pid", "study_yr", "tier", "variant", "order", "pos", "pilot", "partner_of", "Manufacturer", "ManufacturerModelName",
        "ConvolutionKernel", "kclass", "thick", "spacing_idc", "ratio_idc", "n_images", "size_mb", "url", "StudyInstanceUID"]
U1_MAX, N_RANDOM = 0.70, 800


def selection(meta, split_p):
    m = R.load_meta(meta); split = L.SafeUnpickler(open(split_p, "rb")).load()
    grp = {str(k): str(v["split"]) for k, v in split.items()}; m["grp"] = m.PatientID.map(grp).fillna("unseen")
    U = m[m.grp == "unseen"].copy(); sel = R.select(U, R.BEST_RULE)
    dup = sel.duplicated(["PatientID", "study_yr"], keep=False); sel = sel[~dup & sel.study_yr.isin([0, 1, 2])].copy()
    sel["ratio_idc"] = (sel.vg_slice_spacing_mm / sel.thick).round(4)
    pids = np.array(sorted(sel.PatientID.unique())); perm = np.random.default_rng(0).permutation(len(pids))
    sel["order"] = sel.PatientID.map({p: int(r) for p, r in zip(pids[perm], range(len(pids)))})
    return U, sel.reset_index(drop=True)


def rows(X, tier):
    M = pd.DataFrame(dict(series_uid=X.SeriesInstanceUID, pid=X.PatientID, study_yr=X.study_yr.astype(int), tier=tier, variant="main", order=X.order, pilot=False,
                          partner_of="", Manufacturer=X.Manufacturer, ManufacturerModelName=X.ManufacturerModelName, ConvolutionKernel=X.ConvolutionKernel,
                          kclass=X.kclass, thick=X.thick, spacing_idc=X.vg_slice_spacing_mm, ratio_idc=X.ratio_idc, n_images=X.instanceCount,
                          size_mb=X.series_size_MB, url=X.series_aws_url, StudyInstanceUID=X.StudyInstanceUID))
    M = M.sort_values(["order", "study_yr"]).reset_index(drop=True); M["pos"] = np.arange(len(M)); return M[COLS]


def write(M, out, info):
    M.to_csv(out / "manifest_unseen.csv", index=False, lineterminator="\n")
    raw = (out / "manifest_unseen.csv").read_bytes(); (out / "manifest_unseen.csv.gz").write_bytes(gzip.compress(raw, 9, mtime=0))
    info["manifest_sha256"] = hashlib.sha256(raw).hexdigest()
    (out / "o2_manifest.json").write_bytes((json.dumps(info, indent=1, default=str) + "\n").encode("utf-8")); print(json.dumps(info, indent=1, default=str))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("meta"); ap.add_argument("split"); ap.add_argument("out"); ap.add_argument("--add-u3", default=None)
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    U, sel = selection(a.meta, a.split)
    u1 = sel[sel.ratio_idc <= U1_MAX]; k1 = set(zip(u1.PatientID, u1.study_yr))
    nb = {(p, y + d) for p, y in k1 for d in (-1, 1)}
    u2 = sel[[(p, y) in nb and (p, y) not in k1 for p, y in zip(sel.PatientID, sel.study_yr)]]
    M = pd.concat([rows(u1, "U1"), rows(u2, "U2")], ignore_index=True)
    rest = sel[~sel.SeriesInstanceUID.isin(M.series_uid)]
    rnd = sel.sample(n=N_RANDOM, random_state=1).SeriesInstanceUID.tolist()   # drawn from the whole list before any outcome is read
    def gb(X): return round(float(X.series_size_MB.sum()) / 1024, 1)
    k2 = set(zip(u2.PatientID, u2.study_yr))
    pairs = [(p, y) for p, y in k1 if (p, y + 1) in k1 or (p, y + 1) in k2] + [(p, y) for p, y in k2 if (p, y + 1) in k1]
    info = dict(label="O2 scoring list; U1 and U2 from public metadata only (no image, no outcome)", unseen_participants_with_ct=int(U.PatientID.nunique()),
                exams_selected=int(len(sel)), participants_selected=int(sel.PatientID.nunique()),
                idc_ratio=dict(le_0p65=int((sel.ratio_idc <= 0.65).sum()), between_0p65_and_0p70=int(((sel.ratio_idc > 0.65) & (sel.ratio_idc <= 0.70)).sum()),
                               blank=int(sel.ratio_idc.isna().sum()), zero=int((sel.ratio_idc == 0).sum())),
                U1=dict(rows=int(len(u1)), participants=int(u1.PatientID.nunique()), gb=gb(u1), by_maker=u1.Manufacturer.value_counts().to_dict()),
                U2=dict(rows=int(len(u2)), participants=int(u2.PatientID.nunique()), gb=gb(u2), by_maker=u2.Manufacturer.value_counts().to_dict()),
                pairs_with_both_scored_starting_at_a_U1_exam=len(pairs),
                random_sample_for_U3=dict(n=N_RANDOM, seed=1, already_in_U1_or_U2=int(pd.Series(rnd).isin(M.series_uid).sum()),
                                          sha256_of_uids=hashlib.sha256("\n".join(sorted(rnd)).encode()).hexdigest()),
                cost_estimate_usd=dict(U1=[round(gb(u1) * 0.0325, 2), round(gb(u1) * 0.0366, 2)], U2=[round(gb(u2) * 0.023, 2), round(gb(u2) * 0.035, 2)],
                                       basis="cost per GB of S6 and X5 (x6 estimate: z-fix part $16-18 for 492 GB, pairs $2-3 for 86 GB); measured, billing about 5-10% more"),
                not_selected_exams=int(len(rest)))
    if a.add_u3:
        # the only outcome read for the lists: which unseen participants have a lung cancer diagnosis (NLST prsn candx_days)
        P = pd.read_csv(next(Path(a.add_u3).glob("*prsn*.csv")), usecols=["pid", "candx_days"], dtype={"pid": str})
        ca = set(P.loc[P.candx_days.notna(), "pid"]) & set(sel.PatientID)
        u3 = sel[(sel.PatientID.isin(ca) | sel.SeriesInstanceUID.isin(rnd)) & ~sel.SeriesInstanceUID.isin(M.series_uid)]
        M = pd.concat([M, rows(u3, "U3")], ignore_index=True)
        info["U3"] = dict(rows=int(len(u3)), participants_with_cancer=len(ca), exams_of_cancer_participants=int(sel.PatientID.isin(ca).sum()),
                          gb=gb(u3), cost_estimate_usd=[round(gb(u3) * 0.0325, 2), round(gb(u3) * 0.0366, 2)])
    write(M, out, info)


if __name__ == "__main__":
    main()
