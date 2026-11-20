"""Lung L2, plan X5 (docs/EXECUTION_LOG.md, 2026-11-20, committed 41ca595): the LIDC-IDRI scoring list, from the public IDC index only.
Rows: CT series of collection lidc_idri with at least 60 images and IDC metadata spacing/thickness <= 0.70 (candidates; the cloud job's own
DICOM geometry decides the z-fix at <= 0.65, as frozen); one series per patient (most images, then lowest UID); fixed random order of the
patients (seed 0); tier L1, variant main. No outcome and no annotation is read.
Writes <out>/manifest_lidc.csv (the row format of manifest_dev.csv), <out>/manifest_lidc.csv.gz (gzip level 9, mtime 0, LF bytes) and
<out>/x5_lidc_manifest.json.
usage (a python with pyarrow, e.g. the existing conda env 'mibg', run with -I): python x5_lidc_manifest.py <idc index dir> <out dir>
"""
import gzip
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

COLS = ["series_uid", "pid", "study_yr", "tier", "variant", "order", "pos", "pilot", "partner_of", "Manufacturer", "ManufacturerModelName",
        "ConvolutionKernel", "kclass", "thick", "spacing_idc", "ratio_idc", "n_images", "size_mb", "url", "StudyInstanceUID"]


def main():
    d, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    I = pq.read_table(d / "idc_index.parquet", columns=["collection_id", "PatientID", "SeriesInstanceUID", "StudyInstanceUID", "Modality", "Manufacturer",
                                                        "ManufacturerModelName", "instanceCount", "series_size_MB", "series_aws_url", "license_short_name"]).to_pandas()
    I = I[(I.collection_id == "lidc_idri") & (I.Modality == "CT")]
    C = pq.read_table(d / "ct_index.parquet", columns=["SeriesInstanceUID", "SliceThickness", "ConvolutionKernel"]).to_pandas()
    V = pq.read_table(d / "volume_geometry_index.parquet", columns=["SeriesInstanceUID", "slice_spacing_mm"]).to_pandas()
    X = I.merge(C, on="SeriesInstanceUID", how="left").merge(V, on="SeriesInstanceUID", how="left")
    X["thick"] = pd.to_numeric(X.SliceThickness, errors="coerce"); X["spacing_idc"] = pd.to_numeric(X.slice_spacing_mm, errors="coerce")
    X["ratio_idc"] = (X.spacing_idc / X.thick).round(3)
    info = dict(lidc_ct_series=int(len(X)), lidc_patients=int(X.PatientID.nunique()), licence=sorted(set(X.license_short_name.astype(str))))
    X = X[(X.instanceCount >= 60) & (X.ratio_idc <= 0.70)]
    X = X.sort_values(["PatientID", "instanceCount", "SeriesInstanceUID"], ascending=[True, False, True]).drop_duplicates("PatientID")
    pids = np.array(sorted(X.PatientID.unique())); perm = np.random.default_rng(0).permutation(len(pids)); rank = {p: int(r) for p, r in zip(pids[perm], range(len(pids)))}
    M = pd.DataFrame(dict(series_uid=X.SeriesInstanceUID, pid=X.PatientID, study_yr=0, tier="L1", variant="main", order=X.PatientID.map(rank), pilot=False, partner_of="",
                          Manufacturer=X.Manufacturer, ManufacturerModelName=X.ManufacturerModelName, ConvolutionKernel=X.ConvolutionKernel, kclass="", thick=X.thick,
                          spacing_idc=X.spacing_idc, ratio_idc=X.ratio_idc, n_images=X.instanceCount, size_mb=X.series_size_MB, url=X.series_aws_url,
                          StudyInstanceUID=X.StudyInstanceUID))
    M = M.sort_values("order").reset_index(drop=True); M["pos"] = np.arange(len(M)); M = M[COLS]
    M.to_csv(out / "manifest_lidc.csv", index=False, lineterminator="\n")
    raw = (out / "manifest_lidc.csv").read_bytes(); (out / "manifest_lidc.csv.gz").write_bytes(gzip.compress(raw, 9, mtime=0))
    info.update(rows=int(len(M)), patients=int(M.pid.nunique()), ratio_le_0p65=int((M.ratio_idc <= 0.65).sum()), by_maker=M.Manufacturer.value_counts().to_dict(),
                thickness_counts=M.thick.value_counts().sort_index().to_dict(), total_gb=round(float(M.size_mb.sum()) / 1024, 2),
                manifest_sha256=hashlib.sha256(raw).hexdigest())
    (out / "x5_lidc_manifest.json").write_text(json.dumps(info, indent=1, default=str)); print(json.dumps(info, indent=1, default=str))


if __name__ == "__main__":
    main()
