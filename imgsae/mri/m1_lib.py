"""M1 cell-level helpers (docs/MRI_M0M1_PROTOCOL.md section 6): the 4 mm common grid on the 120 mm crop (30 x 30 cells per slice,
8 x 8 pixels at 0.5 mm), labels, the intensity reference R (66 features), the probe sample, and feature mapping onto the grid.
Pure numpy; unit-tested in tests/test_m1_lib.py."""
from __future__ import annotations

import numpy as np

BLOCK = 8            # 4 mm at 0.5 mm
NCELL = 30           # 120 mm / 4 mm
N_NORMAL = 200       # normal tokens sampled per study
NBINS = 16


def cells(a, block=BLOCK):
    Z, H, W = a.shape; return np.asarray(a, np.float32).reshape(Z, H // block, block, W // block, block).mean((2, 4))


def labels(prep):
    """per-cell occupancies on the 4 mm grid from a prep npz (dict-like)."""
    return dict(lesion=cells(prep["lesion"] >= 1), gland=cells(prep["gland_b"] > 0), valid=cells(prep["valid"]),
                h_pz=cells(prep["zone_h"] == 1), h_tz=cells(prep["zone_h"] == 2), y_pz=cells(prep["zone_y"] == 1), y_tz=cells(prep["zone_y"] == 2))


def keep_and_sample(lab, study_id):
    """kept cells = gland occupancy > 0 or lesion occupancy > 0; probe sample = all lesion cells (occ >= 0.5) + up to 200 normal cells
    (gland occ >= 0.5, lesion occ = 0), default_rng(int(study_id)). Cells with 0 < lesion occ < 0.5 are never sampled."""
    keep = (lab["gland"] > 0) | (lab["lesion"] > 0); idx = np.argwhere(keep)
    les = lab["lesion"][keep] >= 0.5; nor = (lab["gland"][keep] >= 0.5) & (lab["lesion"][keep] == 0)
    rng = np.random.default_rng(int(study_id)); nidx = np.flatnonzero(nor)
    pick = rng.choice(nidx, min(N_NORMAL, len(nidx)), replace=False) if len(nidx) else np.zeros(0, int)
    sample = les.copy(); sample[pick] = True
    return keep, idx, sample, les, nor


def zone_label(lab):
    """per cell: 0 = PZ, 1 = TZ, 2 = uncertain. PZ / TZ only if both zone models give that zone the larger occupancy."""
    def maj(pz, tz): return np.where((pz == 0) & (tz == 0), -1, np.where(pz >= tz, 0, 1))
    a, b = maj(lab["h_pz"], lab["h_tz"]), maj(lab["y_pz"], lab["y_tz"])
    return np.where((a == b) & (a >= 0), a, 2)


def ref_features(t2w, adc, hbv, valid, gland_cells, keep, t2p, hbp):
    """R (66 per kept cell): per channel a 16-bin normalised histogram + mean + SD (T2W, HBV scaled by the study's [p0.5, p99.5]; ADC by
    the fixed 0-3,000 window), 3 x 3 in-plane context (mean and SD of the 8 neighbours' channel means), position (x, y relative to the
    gland's in-plane bounding box; slice relative to the gland's extent) and zone one-hot (filled by the caller)."""
    sc = [np.clip((t2w - t2p[0]) / max(t2p[1] - t2p[0], 1e-6), 0, 1), np.clip(adc / 3000.0, 0, 1), np.clip((hbv - hbp[0]) / max(hbp[1] - hbp[0], 1e-6), 0, 1)]
    Z = t2w.shape[0]; feats, means = [], []
    for x in sc:
        b = x.reshape(Z, NCELL, BLOCK, NCELL, BLOCK).transpose(0, 1, 3, 2, 4).reshape(Z, NCELL, NCELL, BLOCK * BLOCK)
        v = valid.reshape(Z, NCELL, BLOCK, NCELL, BLOCK).transpose(0, 1, 3, 2, 4).reshape(Z, NCELL, NCELL, BLOCK * BLOCK)
        n = np.maximum(v.sum(-1), 1); m = (b * v).sum(-1) / n; sd = np.sqrt(np.maximum(((b - m[..., None]) ** 2 * v).sum(-1) / n, 0))
        bins = np.minimum((b * NBINS).astype(int), NBINS - 1); h = np.stack([((bins == k) & v).sum(-1) for k in range(NBINS)], -1) / n[..., None]
        feats.append(np.concatenate([h, m[..., None], sd[..., None]], -1)); means.append(m)
    ctx = []
    for m in means:   # 8-neighbour context on the full grid (edge cells: available neighbours only)
        P = np.pad(m, ((0, 0), (1, 1), (1, 1)), constant_values=np.nan)
        nb = np.stack([P[:, 1 + dy:1 + dy + NCELL, 1 + dx:1 + dx + NCELL] for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy, dx) != (0, 0)], -1)
        ctx += [np.nanmean(nb, -1), np.nanstd(nb, -1)]
    zz, yy, xx = np.nonzero(gland_cells > 0)
    if len(zz): y0, y1, x0, x1, z0, z1 = yy.min(), yy.max(), xx.min(), xx.max(), zz.min(), zz.max()
    else: y0, y1, x0, x1, z0, z1 = 0, NCELL - 1, 0, NCELL - 1, 0, Z - 1
    Zi, Yi, Xi = np.meshgrid(np.arange(Z), np.arange(NCELL), np.arange(NCELL), indexing="ij")
    pos = [(Xi - x0) / max(x1 - x0, 1), (Yi - y0) / max(y1 - y0, 1), (Zi - z0) / max(z1 - z0, 1)]
    allf = np.concatenate(feats + [c[..., None] for c in ctx] + [p[..., None] for p in pos], -1)   # Z x 30 x 30 x 63
    return np.nan_to_num(allf[keep], nan=0.0).astype(np.float32)


def overlap_weights(n_src, src_mm, n_dst=NCELL, dst_mm=4.0):
    """W (n_dst x n_src): share of each destination cell covered by each source cell (1D, both grids start at 0 mm)."""
    W = np.zeros((n_dst, n_src))
    for i in range(n_dst):
        a, b = i * dst_mm, (i + 1) * dst_mm
        for k in range(n_src):
            lo, hi = max(a, k * src_mm), min(b, (k + 1) * src_mm)
            if hi > lo: W[i, k] = (hi - lo) / dst_mm
    return W
