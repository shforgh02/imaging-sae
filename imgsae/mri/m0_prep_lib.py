"""M0.3 preprocessing functions (docs/MRI_M0M1_PROTOCOL.md section 3). Pure functions, unit-tested in imgsae/mri/tests/test_m0_prep.py.
Arrays are (z, y, x) in the T2W index order. In-plane grid after resampling: 0.5 x 0.5 mm; crop 240 x 240 pixels (120 x 120 mm).
"""
from __future__ import annotations

import numpy as np

INPLANE_MM = 0.5
CROP_PX = 240                     # 120 mm at 0.5 mm
CELL_MM = (8, 6, 4)               # candidate token sizes (in-plane), one T2W slice deep
MIN_LESION_ML = 0.02              # components below this are reported, not used for recall
CAPTURE_OCC = 0.5


# ------------------------------------------------------------------ geometry (SimpleITK)
def same_grid(a, b, tol=1e-3):
    """True if two SimpleITK images share size, spacing, origin and direction (within tol)."""
    return (a.GetSize() == b.GetSize() and np.allclose(a.GetSpacing(), b.GetSpacing(), atol=tol)
            and np.allclose(a.GetOrigin(), b.GetOrigin(), atol=tol) and np.allclose(a.GetDirection(), b.GetDirection(), atol=tol))


def to_grid(moving, reference, nearest=False):
    """resample `moving` onto `reference`'s grid (identity transform, physical coordinates); outside -> 0."""
    import SimpleITK as sitk
    interp = sitk.sitkNearestNeighbor if nearest else sitk.sitkLinear
    out_type = moving.GetPixelID() if nearest else sitk.sitkFloat32
    return sitk.Resample(moving, reference, sitk.Transform(), interp, 0.0, out_type)


def inplane_grid(img, mm=INPLANE_MM):
    """a reference grid with in-plane spacing `mm` x `mm`, same z spacing, origin and direction, covering the same extent."""
    import SimpleITK as sitk
    sp = img.GetSpacing(); sz = img.GetSize()
    new_sp = (mm, mm, sp[2]); new_sz = [int(round(sz[0] * sp[0] / mm)), int(round(sz[1] * sp[1] / mm)), sz[2]]
    ref = sitk.Image(new_sz, sitk.sitkUInt8); ref.SetSpacing(new_sp); ref.SetOrigin(img.GetOrigin()); ref.SetDirection(img.GetDirection())
    return ref


# ------------------------------------------------------------------ crop
def crop_box(gland, size=CROP_PX):
    """in-plane box of `size` pixels centred on the in-plane centroid of the gland (all slices); z from the first to the last gland
    slice +- 1 (clipped). Returns (z0, z1, y0, x0) with z1 exclusive; y0/x0 may be negative or exceed the image (padding)."""
    zz, yy, xx = np.nonzero(gland)
    if len(zz) == 0: raise ValueError("empty gland mask")
    cy, cx = int(round(yy.mean())), int(round(xx.mean()))
    z0, z1 = max(int(zz.min()) - 1, 0), min(int(zz.max()) + 2, gland.shape[0])
    return z0, z1, cy - size // 2, cx - size // 2


def crop(arr, box, size=CROP_PX):
    """crop (z0:z1, y0:y0+size, x0:x0+size) with zero padding; returns (crop, valid mask)."""
    z0, z1, y0, x0 = box; Z = z1 - z0
    out = np.zeros((Z, size, size), arr.dtype); valid = np.zeros((Z, size, size), bool)
    ys, xs = max(y0, 0), max(x0, 0); ye, xe = min(y0 + size, arr.shape[1]), min(x0 + size, arr.shape[2])
    if ye > ys and xe > xs:
        out[:, ys - y0:ye - y0, xs - x0:xe - x0] = arr[z0:z1, ys:ye, xs:xe]; valid[:, ys - y0:ye - y0, xs - x0:xe - x0] = True
    return out, valid


# ------------------------------------------------------------------ cells, lesions, QC
def cells(mask, block):
    """per-cell mean of a (z, H, W) array over block x block in-plane cells (H, W divisible by block)."""
    Z, H, W = mask.shape; m = np.asarray(mask, np.float32)
    return m.reshape(Z, H // block, block, W // block, block).mean((2, 4))


def components(lesion, voxel_ml):
    """3D connected components (26-connectivity) of a boolean mask; returns (labels, volumes_ml per component 1..n)."""
    from scipy import ndimage as ndi
    lab, n = ndi.label(lesion, structure=np.ones((3, 3, 3), bool))
    vol = np.bincount(lab.ravel(), minlength=n + 1)[1:] * voxel_ml if n else np.zeros(0)
    return lab, vol


def captured(lab, n, occ, block, thr=CAPTURE_OCC):
    """for each component 1..n: True if at least one cell with lesion occupancy >= thr overlaps the component."""
    hit = occ >= thr; out = np.zeros(n, bool)
    for k in range(1, n + 1):
        comp_cells = cells(lab == k, block) > 0; out[k - 1] = bool((hit & comp_cells).any())
    return out


def dice(a, b):
    a = np.asarray(a, bool); b = np.asarray(b, bool); s = a.sum() + b.sum()
    return float(2 * (a & b).sum() / s) if s else float("nan")


def zone_dice(z1, z2):
    """mean of PZ (label 1) and TZ (label 2) Dice between two zone maps; nan-mean if a zone is empty in both."""
    d = [dice(z1 == 1, z2 == 1), dice(z1 == 2, z2 == 2)]; d = [x for x in d if np.isfinite(x)]
    return float(np.mean(d)) if d else float("nan")


def pct(x, mask, qs):
    v = np.asarray(x, np.float64)[np.asarray(mask, bool)]
    return [float(np.percentile(v, q)) for q in qs] if v.size else [float("nan")] * len(qs)


# ------------------------------------------------------------------ one study (arrays already on the cropped 0.5 mm grid)
def study_metrics(t2w, adc, hbv, valid, lesion, gland_b, gland_g, zone_h, zone_y, dz_mm):
    """all M0 per-study numbers from cropped arrays. lesion: bool; zone maps: 0/1 (PZ)/2 (TZ)."""
    voxel_ml = INPLANE_MM * INPLANE_MM * dz_mm / 1000.0
    lab, vols = components(lesion, voxel_ml); n = len(vols)
    out = dict(n_slices=int(t2w.shape[0]), dz_mm=float(dz_mm), valid_share=float(valid.mean()),
               lesion_ml_total=float(lesion.sum() * voxel_ml), components_ml=[round(float(v), 5) for v in vols],
               gland_ml_bosma=float(gland_b.sum() * voxel_ml), gland_ml_guerbet=float(gland_g.sum() * voxel_ml),
               dice_gland=dice(gland_b, gland_g), dice_zone=zone_dice(zone_h, zone_y),
               adc_p1_p50_p99_gland=pct(adc, gland_b & valid, (1, 50, 99)), t2w_p05_p995=pct(t2w, valid, (0.5, 99.5)),
               hbv_p05_p995=pct(hbv, valid, (0.5, 99.5)), recall={})
    big = np.array([v >= MIN_LESION_ML for v in vols], bool)
    for mm in CELL_MM:
        block = int(round(mm / INPLANE_MM)); occ = cells(lesion, block); cap = captured(lab, n, occ, block) if n else np.zeros(0, bool)
        out["recall"][str(mm)] = dict(n_lesions=int(big.sum()), n_captured=int(cap[big].sum()), n_small=int((~big).sum()),
                                      n_lesion_cells=int((occ >= CAPTURE_OCC).sum()), n_partial_cells=int(((occ > 0) & (occ < CAPTURE_OCC)).sum()))
    return out
