"""Lung L2: simple image measures on the exact tensor Sybil feeds its network (docs/LUNG_L2_PROTOCOL.md section 6).

Input: x, Sybil's volume (1, C, T=200, H=256, W=256), normalised: x = (v - 128.1722) / 87.1849 with v the 8-bit lung-window value.
HU ~ -600.5 + (v / 256 - 0.5) * 1499 (Sybil's window: centre -600, width 1500; one 8-bit step = 5.9 HU).
Padded voxels (CropOrPad pads with exactly 0 in normalised units) are found as exact zeros and excluded.
Voxel: 1.40625 x 1.40625 mm in plane (each slice resized to 256 px first, then resampled; Sybil issue #74), 2.5 mm in z as Sybil
assumes; `stretch` = thickness / true spacing converts apparent z sizes to true ones.
Pure numpy + scipy; no outcome is used.
"""
import numpy as np
from scipy import ndimage

MEAN, STD = 128.1722, 87.1849
VOX_MM = (2.5, 1.40625, 1.40625)          # z, y, x
VOX_ML = VOX_MM[0] * VOX_MM[1] * VOX_MM[2] / 1000.0
INPLANE = np.zeros((3, 3, 3), bool)
INPLANE[1] = ndimage.generate_binary_structure(2, 1)


def to_hu(x):
    v = x * STD + MEAN
    return (-600.5 + (v / 256.0 - 0.5) * 1499.0).astype(np.float32)


def measures(x, stretch=1.0, z_cropped=False):
    """x: numpy (T, H, W) one channel of Sybil's volume. stretch: thickness / true spacing (1 for a zfix volume).
    z_cropped: True if the resampled volume had more than 200 slices (Sybil cut its ends)."""
    x = np.asarray(x, np.float32)
    real = x != 0.0
    hu = to_hu(x)
    out = {"n_real_slices": int(real.any(axis=(1, 2)).sum())}
    low = (hu < -400) & real
    # in-plane border of the real region (array edge or next to padding), 1 voxel wide
    edge = real & ~ndimage.binary_erosion(real, structure=INPLANE, border_value=0)
    lab, n = ndimage.label(low)
    if n == 0:
        out["error"] = "no low-density voxels"
        return out
    touch = np.unique(lab[edge & low])
    outside = np.isin(lab, touch[touch > 0])
    inner = low & ~outside
    lab2, n2 = ndimage.label(inner)
    if n2 == 0:
        out["error"] = "no lung component"
        return out
    sizes = ndimage.sum_labels(np.ones_like(lab2, np.float32), lab2, index=np.arange(1, n2 + 1))
    keep = np.argsort(sizes)[::-1][:2]
    keep = [k for k in keep if sizes[k] >= 0.2 * sizes[keep[0]]]
    lung = np.isin(lab2, [k + 1 for k in keep])
    lhu = hu[lung]
    zs = np.where(lung.any(axis=(1, 2)))[0]
    out.update(
        lung_vol_app_ml=float(lung.sum() * VOX_ML), lung_vol_ml=float(lung.sum() * VOX_ML / stretch),
        n_lung_components_kept=len(keep), lung_largest_two_ratio=float(sizes[keep[-1]] / sizes[keep[0]]) if len(keep) > 1 else 0.0,
        laa950_pct=float((lhu < -950).mean() * 100), lung_p15_hu=float(np.percentile(lhu, 15)), lung_mean_hu=float(lhu.mean()),
        lung_z_extent_app_mm=float(len(zs) * VOX_MM[0]), lung_z_extent_mm=float(len(zs) * VOX_MM[0] / stretch),
        lung_z_first=int(zs[0]), lung_z_last=int(zs[-1]),
        lung_cut_z=bool(z_cropped and (lung[0].any() or lung[-1].any())))
    band = real & ~ndimage.binary_erosion(real, structure=INPLANE, iterations=3, border_value=0)
    out["lung_cut_xy"] = bool((lung & band).any())
    zmid = int(np.median(zs))
    body = real[zmid] & ~outside[zmid]
    out["body_area_cm2"] = float(body.sum() * VOX_MM[1] * VOX_MM[2] / 100.0)
    out["body_touches_edge"] = bool((body & edge[zmid]).any())
    rz = np.where(real.any(axis=(1, 2)))[0]
    mid = rz[max(0, len(rz) // 2 - 25): len(rz) // 2 + 25]
    air = outside[mid] & ~(hu[mid] < -1340)                       # drop voxels clipped at the window floor
    air = ndimage.binary_erosion(air, structure=INPLANE, iterations=10, border_value=0)
    a = hu[mid][air]
    out["air_n_vox"] = int(a.size)
    out["air_median_hu"] = float(np.median(a)) if a.size >= 500 else None
    out["air_noise_sd_hu"] = float(a.std()) if a.size >= 500 else None
    return out
