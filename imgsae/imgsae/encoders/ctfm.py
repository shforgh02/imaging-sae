"""CT-FM encoder adapter (project-lighter/ct_fm_feature_extractor, Apache-2.0) without the lighter-zoo dependency chain.

lighter_zoo.SegResEncoder == monai.networks.nets.segresnet_ds.SegResEncoder(spatial_dims=3, init_filters=32, in_channels=1,
blocks_down=(1,2,2,4,4)) with defaults act='relu', norm='batch' (BatchNorm: in eval mode per-token outputs do not depend on global
volume statistics, so tiling is allowed). Preprocessing as in the model card: orientation SPL, HU clipped to [-1024, 2048] -> [0, 1].
The last stage is 512-d at stride 16 voxels.
"""
from __future__ import annotations

import json
import time

import numpy as np
import torch

from .. import accel

REPO = "project-lighter/ct_fm_feature_extractor"
HU_MIN, HU_MAX, STRIDE, D = -1024.0, 2048.0, 16, 512


def load(device="cpu", random_init=False, seed=0):
    """CT-FM encoder in eval mode; random_init=True gives the same architecture with fresh weights (null encoder)."""
    from huggingface_hub import hf_hub_download
    from monai.networks.nets.segresnet_ds import SegResEncoder
    cfg = json.load(open(hf_hub_download(REPO, "config.json"))); torch.manual_seed(seed)
    m = SegResEncoder(spatial_dims=cfg["spatial_dims"], init_filters=cfg["init_filters"], in_channels=cfg["in_channels"], blocks_down=tuple(cfg["blocks_down"]))
    if not random_init:
        from safetensors.torch import load_file
        sd = load_file(hf_hub_download(REPO, "model.safetensors")); missing, unexpected = m.load_state_dict(sd, strict=True), None
    return m.eval().to(device)


def to_spl(vol_ras, affine):
    """nibabel RAS-ordered array + affine -> SPL-ordered array + affine (MONAI Orientation('SPL') equivalent for axis-aligned scans)."""
    import nibabel as nib
    ornt_src = nib.orientations.io_orientation(affine); ornt_dst = nib.orientations.axcodes2ornt(("S", "P", "L"))
    tr = nib.orientations.ornt_transform(ornt_src, ornt_dst); out = nib.orientations.apply_orientation(vol_ras, tr)
    aff = affine @ nib.orientations.inv_ornt_aff(tr, vol_ras.shape); return np.ascontiguousarray(out), aff


def body_mask(hu, thr=-500):
    """largest connected component above thr, hole-filled slice-wise (removes air and most of the table)."""
    from scipy import ndimage as ndi
    m = hu > thr; lab, n = ndi.label(m)
    if n == 0: return m
    keep = lab == (np.argmax(np.bincount(lab.ravel())[1:]) + 1)
    return np.stack([ndi.binary_fill_holes(s) for s in keep])


def scale(hu): return np.clip((hu - HU_MIN) / (HU_MAX - HU_MIN), 0, 1).astype(np.float32)


@torch.no_grad()
def encode_tiles(model, x01, device="auto", win=160, margin=48, half=True):
    """sliding-window encode of a scaled SPL volume (Z, Y, X) -> token grid (D, z, y, x) at stride 16.
    Windows of `win` voxels (multiple of 16) advance by win - 2*margin; each token is taken from a window where it lies >= margin
    voxels from that window's border (or at the volume border). Returns float16 numpy array and timing."""
    assert win % STRIDE == 0 and margin % STRIDE == 0
    device = accel.pick(device); Z = x01.shape; pad = [(-s) % STRIDE for s in Z]
    x = np.pad(x01, [(0, p) for p in pad], constant_values=0.0); S = x.shape; G = [s // STRIDE for s in S]
    out = np.zeros((D, *G), np.float16); filled = np.zeros(G, bool); step = win - 2 * margin; t0 = time.time()
    starts = [sorted(set(list(range(0, max(s - win, 0) + 1, step)) + [max(s - win, 0)])) for s in S]
    dt = torch.float16 if (half and device != "cpu") else torch.float32; model = model.to(device=device, dtype=dt)
    for a in starts[0]:
        for b in starts[1]:
            for c in starts[2]:
                w = x[a:a + win, b:b + win, c:c + win]; t = torch.from_numpy(np.ascontiguousarray(w))[None, None].to(device=device, dtype=dt)
                f = model(t)[-1][0].float().cpu().numpy(); g0 = (a // STRIDE, b // STRIDE, c // STRIDE); gs = f.shape[1:]
                lo = [0 if o == 0 else margin // STRIDE for o in (a, b, c)]
                hi = [gs[i] if (o + win) >= S[i] else gs[i] - margin // STRIDE for i, o in enumerate((a, b, c))]
                sl_t = tuple(slice(g0[i] + lo[i], g0[i] + hi[i]) for i in range(3)); sl_f = tuple(slice(lo[i], hi[i]) for i in range(3))
                sel = ~filled[sl_t]; blk = out[(slice(None),) + sl_t]; blk[:, sel] = f[(slice(None),) + sl_f][:, sel].astype(np.float16)
                out[(slice(None),) + sl_t] = blk; filled[sl_t] |= True
    accel.empty_cache(device)
    return out, dict(seconds=time.time() - t0, grid=G, filled=float(filled.mean()), n_windows=int(np.prod([len(s) for s in starts])))


def token_centres(grid, affine_spl, offset=0.0):
    """world (mm) centre of each token: voxel index = 16 * i + offset (offset calibrated by impulse response at D2)."""
    idx = np.stack(np.meshgrid(*[np.arange(g) for g in grid], indexing="ij"), -1).reshape(-1, 3) * STRIDE + offset
    return (np.c_[idx, np.ones(len(idx))] @ affine_spl.T)[:, :3]
