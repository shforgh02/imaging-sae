"""Per-scan token table for TotalSegmentator scans (lean plan v1, Phase 1 D3): world grid of token boxes (16 voxels at the chosen spacing),
leaf occupancy, intensity/texture/context reference features, anatomy-normalised position, valid-token flags, scan-level HU-derived values.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from . import atlas
from .encoders import ctfm

S = ctfm.STRIDE
EDGES = np.array([-1024, -900, -700, -500, -300, -150, -100, -60, -30, 0, 20, 40, 60, 80, 100, 150, 200, 300, 500, 800, 1200, 2000, 1e9])


def load_ct(path, spacing=None):
    """CT -> SPL-ordered HU array and affine; optional isotropic resampling (linear) to `spacing` mm."""
    import nibabel as nib
    im = nib.load(str(path)); hu, aff = ctfm.to_spl(np.asarray(im.dataobj, np.float32), im.affine); vox = np.sqrt((aff[:3, :3] ** 2).sum(0))
    if spacing and np.any(np.abs(vox - spacing) > 1e-3):
        z = vox / spacing; hu = ndi.zoom(hu, z, order=1, prefilter=False); aff = aff.copy(); aff[:3, :3] = aff[:3, :3] / z
    return hu.astype(np.float32), aff, vox


def load_mask(path, shape, spacing=None):
    import nibabel as nib
    im = nib.load(str(path)); m, aff = ctfm.to_spl(np.asarray(im.dataobj) > 0, im.affine); vox = np.sqrt((aff[:3, :3] ** 2).sum(0))
    if spacing and np.any(np.abs(vox - spacing) > 1e-3): m = ndi.zoom(m.astype(np.uint8), vox / spacing, order=0)
    out = np.zeros(shape, bool); sl = tuple(slice(0, min(a, b)) for a, b in zip(shape, m.shape)); out[sl] = m[sl] > 0; return out


def label_volume(seg_dir, shape, spacing=None):
    """all leaf masks -> one uint8 label volume (leaf index + 1; 0 = none) in SPL order at the CT grid; one nearest-neighbour resample per scan.
    TotalSegmentator structures are mutually exclusive; on rare overlaps the later leaf wins."""
    import nibabel as nib
    lv, vox = None, None
    for i, leaf in enumerate(atlas.LEAVES):
        p = seg_dir / f"{leaf}.nii.gz"
        if not p.exists(): continue
        im = nib.load(str(p)); m, aff = ctfm.to_spl(np.asarray(im.dataobj) > 0, im.affine)
        if lv is None: lv = np.zeros(m.shape, np.uint8); vox = np.sqrt((aff[:3, :3] ** 2).sum(0))
        lv[m] = i + 1
    if lv is None: return np.zeros(shape, np.uint8)
    if spacing and np.any(np.abs(vox - spacing) > 1e-3): lv = ndi.zoom(lv, vox / spacing, order=0)
    out = np.zeros(shape, np.uint8); sl = tuple(slice(0, min(a, b)) for a, b in zip(shape, lv.shape)); out[sl] = lv[sl]; return out


def pad16(v, fill):
    return np.pad(v, [(0, (-s) % S) for s in v.shape], constant_values=fill)


def blocks(v):
    """(Z, Y, X) padded to multiples of 16 -> view (gz, gy, gx, 16**3)."""
    gz, gy, gx = [s // S for s in v.shape]
    return v.reshape(gz, S, gy, S, gx, S).transpose(0, 2, 4, 1, 3, 5).reshape(gz, gy, gx, S ** 3)


def block_mean(v): return blocks(v.astype(np.float32)).mean(-1)


def ref_features(hu, body):
    """per-token reference features: HU histogram (22 bins), mean, sd, texture (|grad|, LoG sd 1.5 and 3 vox, local sd), the same averaged
    over the 3x3x3 token neighbourhood (context). Returns (gz, gy, gx, F) float32 and feature names."""
    h = np.clip(hu, -1024, 3000); B = blocks(h); idx = np.digitize(B, EDGES[1:-1])
    hist = np.stack([(idx == i).mean(-1) for i in range(len(EDGES) - 1)], -1); mu = B.mean(-1, keepdims=True) / 1000; sd = B.std(-1, keepdims=True) / 1000
    g = np.sqrt(sum(ndi.sobel(h, a) ** 2 for a in range(3))) / 1000
    tex = [block_mean(g), block_mean(np.abs(ndi.gaussian_laplace(h, 1.5))) / 1000, block_mean(np.abs(ndi.gaussian_laplace(h, 3.0))) / 1000]
    m1 = ndi.uniform_filter(h, 5); lsd = np.sqrt(np.maximum(ndi.uniform_filter(h * h, 5) - m1 * m1, 0)) / 1000; tex.append(block_mean(lsd))
    F = np.concatenate([hist, mu, sd, np.stack(tex, -1)], -1).astype(np.float32)
    ctx = ndi.uniform_filter(F, size=(3, 3, 3, 1), mode="nearest")
    names = [f"hist{i}" for i in range(hist.shape[-1])] + ["mean", "sd", "grad", "log15", "log3", "lsd"]
    return np.concatenate([F, ctx], -1), names + [f"ctx_{n}" for n in names]


def position_features(grid, occ_leaf_grid, body_grid, nfreq=4):
    """anatomy-normalised coordinates: x, y relative to body centroid / half-extent per axial token slice; z as continuous vertebral level
    (interpolated from vertebra centroids; extrapolated linearly). Fourier features sin/cos(2^k pi c), k < nfreq. Returns (gz, gy, gx, 3 + 6 nfreq)."""
    gz, gy, gx = grid; Zc, Yc, Xc = np.meshgrid(np.arange(gz), np.arange(gy), np.arange(gx), indexing="ij"); coords = np.zeros((gz, gy, gx, 3), np.float32)
    for z in range(gz):
        b = body_grid[z] > .5
        if b.sum() < 4: continue
        yy, xx = np.nonzero(b); cy, cx = yy.mean(), xx.mean(); hy, hx = max(np.ptp(yy) / 2, 1), max(np.ptp(xx) / 2, 1)
        coords[z, ..., 1] = (Yc[z] - cy) / hy; coords[z, ..., 2] = (Xc[z] - cx) / hx
    vert = [i for i, l in enumerate(atlas.LEAVES) if l.startswith("vertebrae_") or l == "sacrum"]; order = {l: k for k, l in enumerate(
        ["vertebrae_C1", "vertebrae_C2", "vertebrae_C3", "vertebrae_C4", "vertebrae_C5", "vertebrae_C6", "vertebrae_C7"] + [f"vertebrae_T{i}" for i in range(1, 13)]
        + [f"vertebrae_L{i}" for i in range(1, 6)] + ["vertebrae_S1", "sacrum"])}
    zs, lv = [], []
    for i in vert:
        w = occ_leaf_grid[..., i].sum((1, 2))
        if w.sum() > .5: zs.append((np.arange(gz) * w).sum() / w.sum()); lv.append(order[atlas.LEAVES[i]])
    if len(zs) >= 2:
        o = np.argsort(zs); zs, lv = np.array(zs)[o], np.array(lv)[o]; p = np.polyfit(zs, lv, 1)
        lev = np.interp(np.arange(gz), zs, lv, left=np.nan, right=np.nan); lev = np.where(np.isnan(lev), np.polyval(p, np.arange(gz)), lev)
    else: lev = np.arange(gz, dtype=float) - gz / 2
    coords[..., 0] = (lev[:, None, None] / 26.0).astype(np.float32)
    ff = [coords] + [f(2 ** k * np.pi * coords) for k in range(nfreq) for f in (np.sin, np.cos)]
    return np.concatenate(ff, -1).astype(np.float32)


def scan_table(ct_path, seg_dir, spacing=None, edge=2):
    """everything except encoder features for one scan. Returns dict of arrays on the token grid and scan-level values."""
    hu, aff, vox = load_ct(ct_path, spacing); body = ctfm.body_mask(hu); hu_b = np.where(body, hu, -1024.0)
    hp, bp = pad16(hu_b, -1024.0), pad16(body, False); grid = tuple(s // S for s in hp.shape)
    lv_map = label_volume(seg_dir, hu.shape, spacing); hu_vals = {}
    lp = pad16(lv_map, 0); nb = int(np.prod(grid)); flat = blocks(lp).reshape(nb, S ** 3).astype(np.int32)
    cnt = np.bincount((np.arange(nb, dtype=np.int64)[:, None] * (len(atlas.LEAVES) + 1) + flat).ravel(), minlength=nb * (len(atlas.LEAVES) + 1))
    occ = (cnt.reshape(nb, -1)[:, 1:] / S ** 3).reshape(grid + (len(atlas.LEAVES),)).astype(np.float16)
    for leaf in ("liver", "vertebrae_L1", "aorta", "spleen"):
        m = lv_map == atlas.LEAVES.index(leaf) + 1
        if m.sum() > 50:
            core = ndi.binary_erosion(m, iterations=2); v = hu[core] if core.sum() > 50 else hu[m]
            hu_vals[leaf] = dict(mean=float(np.mean(v)), sd=float(np.std(v)), p95=float(np.percentile(v, 95)), n=int(v.size))
    lung = np.isin(lv_map, [atlas.LEAVES.index(l) + 1 for l in atlas.LEAVES if l.startswith("lung_")])
    if lung.any(): hu_vals["lung_vals"] = [hu[lung][::7]]
    lv = hu_vals.pop("lung_vals", None); lv = np.concatenate(lv) if lv else None
    ref, ref_names = ref_features(hp, bp); bocc = block_mean(bp); pos = position_features(grid, occ.astype(np.float32), bocc)
    valid = bocc >= .5; valid[:edge] = valid[-edge:] = False; valid[:, :edge] = valid[:, -edge:] = False; valid[:, :, :edge] = valid[:, :, -edge:] = False
    aorta = hu_vals.get("aorta", {}); liver = hu_vals.get("liver", {})
    scan = dict(liver_hu=liver.get("mean", np.nan), l1_hu=hu_vals.get("vertebrae_L1", {}).get("mean", np.nan),
                laa950=float((lv < -950).mean()) if lv is not None and lv.size else np.nan, aorta_hu=aorta.get("mean", np.nan),
                contrast=float(aorta.get("mean", np.nan) > 150) if aorta else np.nan, aorta_ca=float(aorta.get("p95", np.nan) > 600) if aorta else np.nan,
                noise_sd=hu_vals.get("liver", hu_vals.get("spleen", {})).get("sd", np.nan), n_struct=int((occ.reshape(-1, occ.shape[-1]).max(0) > 0).sum()),
                spacing_native=[float(v) for v in vox], spacing=float(spacing or vox[0]))
    return dict(occ=occ, ref=ref.astype(np.float16), pos=pos.astype(np.float16), body=bocc.astype(np.float16), valid=valid, affine=aff, grid=np.array(grid),
                ref_names=np.array(ref_names), scan=scan, hu=hp, bodymask=bp)
