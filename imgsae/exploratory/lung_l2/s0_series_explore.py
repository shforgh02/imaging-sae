"""Lung L2, step S0 (free, exploratory description, metadata only): how do the split file's test series differ from the other CT series
of the same study? No outcome is read (the split file's cancer_in_1 field is ignored).
usage: python s0_series_explore.py <nlst_series_meta.csv> <split pickle> <out_txt>
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"D:\Shayan\imgsae\exploratory\lung_l0")
import nlst_l0 as L  # noqa: E402

meta_p, split_p, out_p = sys.argv[1:4]
COLS = ["PatientID", "StudyInstanceUID", "SeriesInstanceUID", "StudyDate", "Modality", "Manufacturer", "ManufacturerModelName",
        "SeriesDescription", "SeriesNumber", "instanceCount", "ImageType", "SliceThickness", "ConvolutionKernel", "KVP",
        "XRayTubeCurrent_max", "Exposure_max", "ReconstructionDiameter", "PixelSpacing_row_mm", "GantryDetectorTilt",
        "vg_regularly_spaced_3d_volume", "vg_slice_spacing_mm"]
m = pd.read_csv(meta_p, usecols=COLS, dtype={"PatientID": str}, low_memory=False)
m = m[m.Modality == "CT"].copy()
split = L.SafeUnpickler(open(split_p, "rb")).load()
grp = {str(k): str(v["split"]) for k, v in split.items()}
test_uids = {u for k, v in split.items() if str(v["split"]) == "test" for u in v["exams"]}
m["grp"] = m.PatientID.map(grp).fillna("none")
m["chosen"] = m.SeriesInstanceUID.isin(test_uids)
m["yr"] = pd.to_datetime(m.StudyDate, errors="coerce").dt.year - 1999
lines = []
P = lines.append
P(f"CT series in NLST (IDC 25.0.5): {len(m)}; by split group: {m.grp.value_counts().to_dict()}")
P(f"test series in split file: {len(test_uids)}; found among CT series: {int(m.chosen.sum())}")
T = m[m.grp == "test"]
st = T.groupby("StudyInstanceUID").agg(n=("SeriesInstanceUID", "size"), nchosen=("chosen", "sum"))
P(f"test studies: {len(st)}; with a chosen series: {int((st.nchosen > 0).sum())}; with >1 chosen: {int((st.nchosen > 1).sum())}")
P(f"CT series per test study: {st.n.describe().round(2).to_dict()}")
P(f"series per study (test, distribution): {st.n.value_counts().sort_index().to_dict()}")
ts = T[T.StudyInstanceUID.isin(st.index[st.nchosen > 0])].copy()
ts["loc"] = ts.ImageType.astype(str).str.contains("LOCALIZER")
P("")
P("== chosen vs not chosen, test studies with a chosen series ==")
for c in ["loc"]:
    P(f"localizer share: chosen {ts[ts.chosen][c].mean():.4f}, other {ts[~ts.chosen][c].mean():.4f}")
P("slice thickness, chosen: " + str(ts[ts.chosen].SliceThickness.round(2).value_counts().head(12).to_dict()))
P("slice thickness, other non-localizer: " + str(ts[~ts.chosen & ~ts["loc"]].SliceThickness.round(2).value_counts().head(12).to_dict()))
P("kernel, chosen (top 25): " + str(ts[ts.chosen].ConvolutionKernel.value_counts().head(25).to_dict()))
P("kernel, other non-localizer (top 25): " + str(ts[~ts.chosen & ~ts["loc"]].ConvolutionKernel.value_counts().head(25).to_dict()))
P("manufacturer, chosen: " + str(ts[ts.chosen].Manufacturer.value_counts().to_dict()))
P("thickness > 2.5 mm among chosen: " + str(int((ts[ts.chosen].SliceThickness > 2.5).sum())))
# rank of the chosen series within its study by instanceCount, among non-localizers
nl = ts[~ts["loc"]].copy()
nl["rank_count"] = nl.groupby("StudyInstanceUID").instanceCount.rank(ascending=False, method="min")
nl["rank_thick"] = nl.groupby("StudyInstanceUID").SliceThickness.rank(ascending=True, method="min")
P("rank of chosen by instanceCount (1 = most slices): " + str(nl[nl.chosen].rank_count.value_counts().sort_index().head(8).to_dict()))
P("rank of chosen by thickness (1 = thinnest): " + str(nl[nl.chosen].rank_thick.value_counts().sort_index().head(8).to_dict()))
# per manufacturer: chosen kernel vs alternatives in multi-series studies
multi = nl.groupby("StudyInstanceUID").filter(lambda d: len(d) > 1)
P(f"test studies with >1 non-localizer CT series: {multi.StudyInstanceUID.nunique()}")
for mf, d in multi.groupby("Manufacturer"):
    P(f"-- {mf}: studies {d.StudyInstanceUID.nunique()}")
    P("   chosen kernels: " + str(d[d.chosen].ConvolutionKernel.value_counts().head(12).to_dict()))
    P("   not chosen kernels: " + str(d[~d.chosen].ConvolutionKernel.value_counts().head(12).to_dict()))
    P("   chosen thickness: " + str(d[d.chosen].SliceThickness.round(2).value_counts().head(6).to_dict()) +
      " | not chosen: " + str(d[~d.chosen].SliceThickness.round(2).value_counts().head(6).to_dict()))
P("")
D = m[m.grp == "dev"]
sd = D.groupby("StudyInstanceUID").size()
P(f"dev: CT series {len(D)}, studies {len(sd)}, participants {D.PatientID.nunique()}; study years {D.groupby('StudyInstanceUID').yr.first().value_counts().sort_index().to_dict()}")
P("example description strings: " + str(ts.SeriesDescription.head(6).tolist()))
open(out_p, "w").write("\n".join(lines))
print("\n".join(lines))
