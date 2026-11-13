"""Lung L2, step S0 (free, metadata only): how many exams have a second reconstruction of the same acquisition with the other kernel class,
same slice thickness and (almost) the same slice count? Also: the dev exams with two CT studies in one study year.
usage: python s0_pairs_count.py <nlst_series_meta.csv> <split pickle> <out_json>
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, r"D:\Shayan\imgsae\exploratory\lung_l0")
import nlst_l0 as L  # noqa: E402
import series_rule as R  # noqa: E402

meta_p, split_p, out_p = sys.argv[1:4]
m = R.load_meta(meta_p)
split = L.SafeUnpickler(open(split_p, "rb")).load()
grp = {str(k): str(v["split"]) for k, v in split.items()}
m["grp"] = m.PatientID.map(grp).fillna("none")
res = {}
for g in ("dev", "test"):
    G = m[m.grp == g]
    sel = R.select(G, R.BEST_RULE)
    cand = R.candidates(G)
    j = sel[["StudyInstanceUID", "SeriesInstanceUID", "thick", "instanceCount", "kclass", "ConvolutionKernel", "Manufacturer"]].merge(
        cand[["StudyInstanceUID", "SeriesInstanceUID", "thick", "instanceCount", "kclass", "ConvolutionKernel", "KVP", "Exposure_max"]],
        on="StudyInstanceUID", suffixes=("", "_p"))
    j = j[(j.SeriesInstanceUID != j.SeriesInstanceUID_p) & (j.thick == j.thick_p) & (j.kclass != j.kclass_p) &
          ((j.instanceCount - j.instanceCount_p).abs() <= 0.02 * j.instanceCount)]
    j = j.drop_duplicates("StudyInstanceUID")
    res[g] = {"selected": int(len(sel)), "studies_with_kernel_pair": int(len(j)),
              "pairs_by_manufacturer": j.Manufacturer.value_counts().to_dict(),
              "pair_kernels_top": (j.ConvolutionKernel + " vs " + j.ConvolutionKernel_p).value_counts().head(10).to_dict(),
              "pairs_by_thickness": j.thick.value_counts().to_dict()}
    if g == "dev":
        d = sel[sel.duplicated(["PatientID", "study_yr"], keep=False)]
        res[g]["dup_pid_year_rows"] = d[["PatientID", "study_yr", "StudyDate", "StudyInstanceUID", "instanceCount"]].astype(str).to_dict("records")
Path(out_p).write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
