"""Lung L2, step S0 (free): NLST series metadata from the public IDC index (idc-index-data release 25.0.5), parquet -> CSV.

Joins three IDC tables on SeriesInstanceUID, keeps the NLST collection only, and writes one CSV row per series.
No image is read and no outcome is used.
usage (any python with pandas + pyarrow; run with -I):  python -I s0_idc_meta.py <dir with the three parquet files> <out_csv>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

d, out = Path(sys.argv[1]), Path(sys.argv[2])
ix = pd.read_parquet(d / "idc_index.parquet",
                     columns=["collection_id", "PatientID", "StudyInstanceUID", "SeriesInstanceUID", "StudyDate", "Modality",
                              "Manufacturer", "ManufacturerModelName", "SeriesDescription", "SeriesNumber", "instanceCount",
                              "series_size_MB", "series_aws_url"])
ix = ix[ix.collection_id == "nlst"].copy()
ct = pd.read_parquet(d / "ct_index.parquet")
ct = ct[ct.SeriesInstanceUID.isin(set(ix.SeriesInstanceUID))].copy()
for c in ct.columns:
    if ct[c].map(lambda v: isinstance(v, (list, np.ndarray))).any():
        ct[c] = ct[c].map(lambda v: "\\".join(map(str, v)) if isinstance(v, (list, np.ndarray)) else v)
vg = pd.read_parquet(d / "volume_geometry_index.parquet")
vg = vg[vg.SeriesInstanceUID.isin(set(ix.SeriesInstanceUID))].copy()
for c in vg.columns:
    if vg[c].map(lambda v: isinstance(v, (list, np.ndarray))).any():
        vg[c] = vg[c].map(lambda v: "\\".join(map(str, v)) if isinstance(v, (list, np.ndarray)) else v)
vg = vg.rename(columns={c: f"vg_{c}" for c in vg.columns if c != "SeriesInstanceUID"})
m = ix.merge(ct, on="SeriesInstanceUID", how="left").merge(vg, on="SeriesInstanceUID", how="left")
m.to_csv(out, index=False)
print("nlst series:", len(ix), "| with ct_index row:", int(m.SeriesInstanceUID.isin(set(ct.SeriesInstanceUID)).sum()),
      "| with geometry row:", int(m.SeriesInstanceUID.isin(set(vg.SeriesInstanceUID)).sum()))
print("modalities:", ix.Modality.value_counts().to_dict())
print("ct_index columns:", list(ct.columns))
print("geometry columns:", list(vg.columns))
