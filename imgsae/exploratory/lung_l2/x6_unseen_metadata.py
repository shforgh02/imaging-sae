"""Lung L2, for the plan-choice review (2026-11-20): counts for the NLST CT-arm participants that are in none of Sybil's splits ("unseen" in
L0: never used by Sybil). PUBLIC METADATA ONLY (IDC series metadata + Sybil's split file): no image, no outcome, no NLST table is read.
Same selection as the count in docs/EXECUTION_LOG.md (2026-11-20, "idea: NLST participants Sybil never used"): the dev series rule
(lung_l0/series_rule.py, BEST_RULE), one series per participant and screen year, years 0 to 2, stretched = IDC spacing / thickness <= 0.65.
Adds: stretched exams by maker and thickness; consecutive-screen pairs that change stretch status, by maker of the pair (the GE question
of H7); series sizes (for the cost estimate).
usage (venv python): python x6_unseen_metadata.py <nlst_series_meta.csv> <Sybil split pickle> <out json>
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE.parent / "lung_l0"))
import nlst_l0 as L  # noqa: E402
import series_rule as R  # noqa: E402


def main():
    meta, split_p, out_p = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    m = R.load_meta(meta)
    split = L.SafeUnpickler(open(split_p, "rb")).load()
    grp = {str(k): str(v["split"]) for k, v in split.items()}; m["grp"] = m.PatientID.map(grp).fillna("unseen")
    U = m[m.grp == "unseen"].copy(); sel = R.select(U, R.BEST_RULE)
    dup = sel.duplicated(["PatientID", "study_yr"], keep=False); sel = sel[~dup & sel.study_yr.isin([0, 1, 2])].copy()
    sel["ratio"] = sel.vg_slice_spacing_mm / sel.thick; sel["st"] = (sel.ratio <= 0.65).astype(int)
    sel["ge"] = sel.Manufacturer.astype(str).str.upper().str.contains("GE").astype(int)
    S = sel[sel.st == 1]
    cols = ["PatientID", "study_yr", "st", "ge", "series_size_MB"]
    p = sel[cols].merge(sel[cols], on="PatientID", suffixes=("_a", "_b")); p = p[p.study_yr_b == p.study_yr_a + 1]
    ch = p[p.st_a != p.st_b]; nge = ch.ge_a + ch.ge_b
    partner_mb = (ch.series_size_MB_a * (ch.st_a == 0) + ch.series_size_MB_b * (ch.st_b == 0))
    partners = set(zip(ch.PatientID[ch.st_a == 0], ch.study_yr_a[ch.st_a == 0])) | set(zip(ch.PatientID[ch.st_b == 0], ch.study_yr_b[ch.st_b == 0]))
    res = dict(
        label="public metadata only (no image, no outcome); for the plan-choice review",
        unseen_participants_with_ct=int(U.PatientID.nunique()), exams_selected=int(len(sel)), participants_selected=int(sel.PatientID.nunique()),
        stretched=dict(exams=int(len(S)), share=round(float(sel.st.mean()), 4), participants=int(S.PatientID.nunique()),
                       by_maker={str(k): int(v) for k, v in S.Manufacturer.value_counts().items()},
                       by_thickness={str(k): int(v) for k, v in S.thick.value_counts().sort_index().items()},
                       by_year={str(k): int(v) for k, v in S.study_yr.value_counts().sort_index().items()},
                       size_gb=round(float(S.series_size_MB.sum()) / 1024, 1), mean_mb=round(float(S.series_size_MB.mean()), 1)),
        pairs=dict(consecutive=int(len(p)), change_status=int(len(ch)),
                   change_stretched_to_not=int(((ch.st_a == 1) & (ch.st_b == 0)).sum()), change_not_to_stretched=int(((ch.st_a == 0) & (ch.st_b == 1)).sum()),
                   change_by_ge=dict(both_ge=int((nge == 2).sum()), one_ge=int((nge == 1).sum()), neither_ge=int((nge == 0).sum())),
                   unchanged_by_ge=dict(both_ge=int(((p.st_a == p.st_b) & (p.ge_a + p.ge_b == 2)).sum()), neither_ge=int(((p.st_a == p.st_b) & (p.ge_a + p.ge_b == 0)).sum())),
                   not_stretched_partner_exams=len(partners), partner_size_gb=round(float(partner_mb.sum()) / 1024, 1)),
        all_selected_size_gb=round(float(sel.series_size_MB.sum()) / 1024, 1),
        note_test_for_comparison="NLST test (H7): 134 changed pairs; both GE 88, one GE 33, neither GE 13")
    out_p.parent.mkdir(parents=True, exist_ok=True); out_p.write_bytes((json.dumps(res, indent=1) + "\n").encode("utf-8"))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
