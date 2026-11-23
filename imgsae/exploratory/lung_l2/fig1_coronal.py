"""Lung L2, task 5, Figure 1(b): one NLST dev exam (public IDC series) as Sybil sees it and at the true slice spacing. No model is run and no
outcome is read: the two 200-slice input volumes are built with the frozen job's own functions (cloud/l2_sybil_modal.py, imported, not
edited): main = Sybil as published (z voxel = SliceThickness), z-fix = the true spacing from ImagePositionPatient. One coronal slice of each
is saved as an 8-bit PNG in Sybil's own intensity scale (value x 87.1849 + 128.1722; Sybil's padding is mid-grey 128, air 59), with the
padding rows, the orientation and the voxel sizes in a json, for the SVG figure (paper_figures.py).
usage (sybil env python, -I): python -I fig1_coronal.py <x11_list.csv> <order> <download dir> <out dir>
"""
import glob
import json
import os
import shutil
import subprocess
import sys

import numpy as np
import pandas as pd
import torch
from PIL import Image

sys.path.insert(0, r"D:\Shayan\imgsae\exploratory\lung_l2\cloud")
import l2_sybil_modal as J  # noqa: E402
from sybil import Serie  # noqa: E402
from sybil.datasets.utils import VOXEL_SPACING  # noqa: E402

S5 = r"D:\sybil_env\Scripts\s5cmd.exe"; MEAN, SD = 128.1722, 87.1849


def coronal(v, row):
    x = v[0, 0, :, row, :].numpy() * SD + MEAN; return np.clip(np.rint(x), 0, 255).astype(np.uint8)   # (200, 256): z by x


def main():
    L = pd.read_csv(sys.argv[1]); r = L[L.order == int(sys.argv[2])].iloc[0]; dl, out = sys.argv[3], sys.argv[4]; os.makedirs(out, exist_ok=True)
    d = os.path.join(dl, r.series_uid); os.makedirs(d, exist_ok=True)
    res = subprocess.run([S5, "--no-sign-request", "--endpoint-url", "https://s3.amazonaws.com", "cp", r.url, d + "/"], capture_output=True, text=True, timeout=600)
    if res.returncode: raise SystemExit(f"download failed: {res.stderr[-300:]}")
    paths = sorted(p for p in glob.glob(os.path.join(d, "**", "*"), recursive=True) if os.path.isfile(p))
    s = Serie(paths, file_type="dicom"); x2d = J._slices(s); pos = np.array(s._meta.slice_positions, float)
    spacing, thick = float(np.median(np.abs(np.diff(pos)))), float(s._meta.thickness)
    vm, shp_m = J._volume(s, x2d); vz, shp_z = J._volume(s, x2d, z_spacing=spacing)
    # the coronal row through the lungs: the row (of the central 96) with the most lung-dark pixels in the true-geometry volume
    zc = vz[0, 0].numpy() * SD + MEAN; rows = range(80, 176); row = max(rows, key=lambda k: int(((zc[:, k, 64:192] > 62) & (zc[:, k, 64:192] < 100)).sum()))
    cm, cz = coronal(vm, row), coronal(vz, row)
    pad_m = [int(i) for i in np.where((vm[0, 0] == 0).flatten(1).all(1).numpy())[0]]; pad_z = [int(i) for i in np.where((vz[0, 0] == 0).flatten(1).all(1).numpy())[0]]
    inc = bool(pos[-1] > pos[0])   # slice order of the volume follows the sorted positions
    import pydicom
    cols = int(pydicom.dcmread(paths[0], stop_before_pixels=True).Columns)   # Sybil resizes each slice to 256 columns: true column size = pixel x cols / 256 x resample
    def lung_rows(img):   # rows (volume order) with lung-dark pixels in the central columns: first and last = lung ends inside the box
        r_ = np.where(((img[:, 40:216] > 62) & (img[:, 40:216] < 100)).sum(1) > 12)[0]; return [int(r_.min()), int(r_.max())] if len(r_) else None
    Image.fromarray(cm).save(os.path.join(out, "fig1_coronal_main.png")); Image.fromarray(cz).save(os.path.join(out, "fig1_coronal_zfix.png"))
    vs = [float(v) for v in s._meta.voxel_spacing]
    info = dict(series_uid=r.series_uid, maker=r.maker, model=r.tag_model, thickness_mm=thick, true_spacing_mm=spacing, ratio=round(spacing / thick, 3), n_images=int(len(pos)),
                T_resampled_main=int(shp_m[3]), T_resampled_zfix=int(shp_z[3]), coronal_row=int(row), padded_rows_main=pad_m, padded_rows_zfix=pad_z,
                positions_increase_with_index=inc, dicom_columns=cols, lung_rows_main=lung_rows(cm), lung_rows_zfix=lung_rows(cz), sybil_voxel_spacing_after_resample_mm=[float(v) for v in VOXEL_SPACING], meta_voxel_spacing=vs,
                note="Sybil's volume: 200 slices of 2.5 mm (its belief) by 256 x 256; main crops a stretched chest at the box ends, z-fix pads a true-length chest")
    json.dump(info, open(os.path.join(out, "fig1_coronal.json"), "w"), indent=1); shutil.rmtree(d, ignore_errors=True)
    print(json.dumps({k: v for k, v in info.items() if not k.startswith("padded")}, indent=None), "| padded rows main", len(pad_m), "zfix", len(pad_z))


if __name__ == "__main__":
    main()
