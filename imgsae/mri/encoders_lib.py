"""Encoder loading and feature extraction for the MRI leg (verified in M0: imgsae/mri/RESULTS_M0.md, mri_m1_encode-015).
Runs inside the Modal image of the encode jobs (repos cloned at pinned commits in /opt). Same functions as cloud/m0_encoders_modal.py.
"""
from __future__ import annotations

import sys

MRICORE_PX = 480
IMNET_MEAN, IMNET_STD = (0.485, 0.456, 0.406), (0.229, 0.224, 0.225)
PF_HW = 224


def safe_load(path):
    import argparse

    import torch
    torch.serialization.add_safe_globals([argparse.Namespace])
    return torch.load(path, map_location="cpu", weights_only=True)


def mricore(path):
    """MRI-CORE trained backbone (DINOv2 teacher ViT-B/16) in a timm ViT; strict load + equality check (see m0_encoders_modal._mricore)."""
    from functools import partial

    import timm
    import torch
    from timm.layers import resample_abs_pos_embed
    sd = safe_load(path)["teacher"]; bb = {}
    for k, v in sd.items():
        if not k.startswith("backbone.") or k == "backbone.mask_token": continue
        p = k[len("backbone."):].split(".")
        if p[0] == "blocks" and len(p) > 2 and p[1].isdigit() and p[2].isdigit(): p = [p[0]] + p[2:]
        bb[".".join(p)] = v
    g = MRICORE_PX // 16
    m = timm.models.vision_transformer.VisionTransformer(img_size=MRICORE_PX, patch_size=16, embed_dim=768, depth=12, num_heads=12, mlp_ratio=4,
                                                          qkv_bias=True, class_token=True, global_pool="", num_classes=0, init_values=None,
                                                          norm_layer=partial(torch.nn.LayerNorm, eps=1e-6))
    bb["pos_embed"] = resample_abs_pos_embed(bb["pos_embed"], new_size=(g, g), old_size=(14, 14), num_prefix_tokens=1, interpolation="bicubic")
    m.load_state_dict(bb, strict=True); st = m.state_dict()
    bad = [k for k in bb if k != "pos_embed" and not torch.equal(st[k], bb[k])]
    if bad or len(bb) != len(st): raise RuntimeError(f"MRI-CORE load check failed: {bad[:5]}")
    return m.eval().cuda()


def sam(path=None, seed=0):
    import torch
    from segment_anything import sam_model_registry
    torch.manual_seed(seed); s = sam_model_registry["vit_b"](checkpoint=path)
    return s.image_encoder.eval().cuda(), (s.pixel_mean.view(1, 3, 1, 1).cuda(), s.pixel_std.view(1, 3, 1, 1).cuda())


def profound(path):
    import copy
    sys.path.insert(0, "/opt/ProFound")
    from models.convnextv2 import convnextv2_tiny, remap_checkpoint_keys
    ck = safe_load(path); m = convnextv2_tiny(in_chans=3); msg = m.load_state_dict(remap_checkpoint_keys(copy.deepcopy(ck)), strict=False)
    if not set(msg.missing_keys) <= {"norm.weight", "norm.bias"} or msg.unexpected_keys: raise RuntimeError(f"ProFound load check failed: {msg}")
    return m.eval().cuda()


def scaled(z, js):
    """fixed ADC window and per-study percentiles (protocol): (Z, 3, 240, 240) numpy in [0, 1]."""
    import numpy as np
    t2lo, t2hi = js["t2w_p05_p995"]; hblo, hbhi = js["hbv_p05_p995"]
    return np.stack([np.clip((z["t2w"] - t2lo) / max(t2hi - t2lo, 1e-6), 0, 1), np.clip(z["adc"] / 3000.0, 0, 1),
                     np.clip((z["hbv"] - hblo) / max(hbhi - hblo, 1e-6), 0, 1)], 1).astype(np.float32)


def scaled_minmax(z):
    """sensitivity input: per-slice, per-channel min-max over the crop's valid pixels (how MRI-CORE was pretrained)."""
    import numpy as np
    out = []
    for name in ("t2w", "adc", "hbv"):
        a = z[name].astype(np.float32); v = z["valid"]; r = np.zeros_like(a)
        for s in range(a.shape[0]):
            vals = a[s][v[s]] if v[s].any() else a[s].ravel(); lo, hi = float(vals.min()), float(vals.max())
            r[s] = np.clip((a[s] - lo) / max(hi - lo, 1e-6), 0, 1)
        out.append(r)
    return np.stack(out, 1)


def resize(x, size):
    import torch
    import torch.nn.functional as Fn
    return Fn.interpolate(torch.from_numpy(x).cuda(), size=(size, size), mode="bilinear", align_corners=False)


def enc_vit(m, x, mode, imagenet=True, bs=16):
    """MRI-CORE patch tokens (Z, 768 or 2304, 30, 30)."""
    import torch
    mean = torch.tensor(IMNET_MEAN, device=x.device).view(1, 3, 1, 1); std = torch.tensor(IMNET_STD, device=x.device).view(1, 3, 1, 1); outs = []
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16):
        for xi in ([x[:, c:c + 1].repeat(1, 3, 1, 1) for c in range(3)] if mode == "A" else [x]):
            f = []
            for i in range(0, len(xi), bs):
                b = xi[i:i + bs]; b = (b - mean) / std if imagenet else b
                t = m.forward_features(b).float()[:, 1:]; g = int(round(t.shape[1] ** 0.5))
                f.append(t.transpose(1, 2).reshape(t.shape[0], t.shape[2], g, g))
            outs.append(torch.cat(f))
    return torch.cat(outs, 1)


def enc_sam(enc, x, mode, norm, bs=8):
    """SAM / untrained features (Z, 256 or 768, 64, 64)."""
    import torch
    outs = []
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16):
        for xi in ([x[:, c:c + 1].repeat(1, 3, 1, 1) for c in range(3)] if mode == "A" else [x]):
            outs.append(torch.cat([enc((xi[i:i + bs] * 255.0 - norm[0]) / norm[1]).float() for i in range(0, len(xi), bs)]))
    return torch.cat(outs, 1)


def pf_input(zp):
    import numpy as np
    import torch
    o = (zp["image"].shape[-1] - PF_HW) // 2; x = zp["image"][:, :, o:o + PF_HW, o:o + PF_HW].astype(np.float32)
    for c in range(3):
        m = x[c] != 0
        if m.any(): v = x[c][m]; x[c][m] = (v - v.mean()) / max(v.std(), 1e-6)
    return torch.from_numpy(x[None]).cuda(), o


def pf_stage0(m, x):
    import torch
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16):
        _, hid = m(x, ret_hids=True)
    return hid[0].float()[0]          # (96, 16, 56, 56) = (C, z, y, x); cell k covers voxels [4k, 4k + 4)


def pf_to_grid(f0, js, Z, offset, ncell=30, block=8):
    """ProFound stage-0 features sampled (trilinear, physical coordinates) at the centres of the 4 mm common-grid cells.
    Returns (C, Z, 30, 30) and the share of cell centres outside the ProFound field of view (zeros there)."""
    import numpy as np
    import torch
    import torch.nn.functional as Fn
    cg, pg = js["crop_grid"], js["profound_grid"]
    D = np.array(cg["direction"]).reshape(3, 3); sp = np.array(cg["spacing"]); o_c = np.array(cg["origin_phys"]); o_p = np.array(pg["origin_phys"])
    zz, ii, jj = np.meshgrid(np.arange(Z), np.arange(ncell), np.arange(ncell), indexing="ij")
    idx = np.stack([jj * block + (block - 1) / 2, ii * block + (block - 1) / 2, zz], -1).reshape(-1, 3)      # crop index (x, y, z)
    phys = o_c + (D @ (idx * sp).T).T
    q = (D.T @ (phys - o_p).T).T                                                                            # profound voxel index (x, y, z), 1 mm
    q[:, 0] -= offset; q[:, 1] -= offset
    u = (q - 1.5) / 4.0                                                                                      # stage-0 cell index (x, y, z)
    C, Dz, Hy, Wx = f0.shape; size = np.array([Wx, Hy, Dz], float)
    g = torch.tensor(2 * u / (size - 1) - 1, dtype=torch.float32, device=f0.device).view(1, Z, ncell, ncell, 3)
    out = Fn.grid_sample(f0[None], g, mode="bilinear", padding_mode="zeros", align_corners=True)[0]          # (C, Z, 30, 30)
    outside = float(((u < 0) | (u > size - 1)).any(1).mean())
    return out, outside
