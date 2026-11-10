"""M0.5 (docs/MRI_M0M1_PROTOCOL.md section 5): encoder checks on Modal L4 (task mri_m1_encode). Downloads and checksums the weights
(MRI-CORE, SAM ViT-B, ProFound-alpha), loads each model and checks that its weights really loaded, then runs a 10-study benchmark on
dev studies (time, peak memory, output shapes, finite / non-constant features, MRI-CORE != SAM, ProFound token order restored).
No features are kept; results -> /vol/enc_check/m0_encoders.json and imgsae/mri/results/m0_encoders.json.
usage (from D:\\Shayan): C:\\Users\\Arman\\miniconda3\\Scripts\\modal.exe run --detach imgsae/mri/cloud/m0_encoders_modal.py
"""
import json
import sys
import time
from pathlib import Path

import modal

TASK, APP, VOL = "mri_m1_encode", "imgsae-mri-m0-encoders", "imgsae-picai"
GPU, CPU, MEM_GIB, TIMEOUT_MIN, IMAGE_USD = "L4", 4, 16, 30, 0.10
MRICORE_COMMIT = "0f4f452614013873f8bb58a1fd613dbe36b58aba"
PROFOUND_COMMIT = "6c371406ab86ad53c545444f9adb25014fc1352a"
SAM_COMMIT = "dca509fe793f601edb92606367a655c15ac00fdf"
MRICORE_GDRIVE = "1nPkTI3H0vsujlzwY8jxjKwAbOCTJv4yW"
SAM_URL = "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth"
PF_SHARE = "https://liveuclac-my.sharepoint.com/:f:/g/personal/rmapyhu_ucl_ac_uk/Et-apmeR2JRMsWRPV0VbQ40BZETdEUmWeq40ulwucYoW-A?e=T6y7F0"
PF_SITE = "https://liveuclac-my.sharepoint.com/personal/rmapyhu_ucl_ac_uk"
PF_PATH = "/personal/rmapyhu_ucl_ac_uk/Documents/WORK/ProFound/public_shared/repo_linked/pretrained/alpha/checkpoint-799 1.pth"
N_BENCH = 10
LOCAL = modal.is_local()
MRI = Path(__file__).resolve().parents[1] if LOCAL else Path("/root/mri")

image = (modal.Image.debian_slim(python_version="3.11").apt_install("git")
         # torch 2.6.0 / torchvision 0.21.0: ProFound's documented environment; monai 1.5.0 (ProFound, MRI-CORE) needs torch < 2.7
         .pip_install("torch==2.6.0", "torchvision==0.21.0", "numpy==2.4.6", "scipy==1.17.1", "monai==1.5.0", "timm==1.0.16", "einops==0.8.1",
                      "scikit-image==0.25.2", "requests==2.32.3", "gdown==5.2.0", "nibabel==5.3.2", f"git+https://github.com/facebookresearch/segment-anything.git@{SAM_COMMIT}")
         .run_commands(f"git clone https://github.com/mazurowski-lab/mri_foundation.git /opt/mri_foundation && cd /opt/mri_foundation && git checkout {MRICORE_COMMIT}",
                       f"git clone https://github.com/pipiwang/ProFound.git /opt/ProFound && cd /opt/ProFound && git checkout {PROFOUND_COMMIT}")
         .env({"PYTHONUNBUFFERED": "1"}))
app = modal.App(APP, image=image)
vol = modal.Volume.from_name(VOL)


def _sha256(p):
    import hashlib
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def _weights():
    """download each checkpoint once to /vol/weights (kept), with SHA256."""
    import os

    import requests
    os.makedirs("/vol/weights", exist_ok=True); out = {}
    def stream(sess, url, dst):
        with sess.get(url, stream=True, timeout=600) as r:
            r.raise_for_status()
            with open(dst + ".part", "wb") as f:
                for b in r.iter_content(1 << 22): f.write(b)
        os.replace(dst + ".part", dst)
    jobs = dict(mricore="/vol/weights/MRI_CORE_vitb.pth", sam="/vol/weights/sam_vit_b_01ec64.pth", profound="/vol/weights/profound_alpha_checkpoint-799.pth")
    for name, dst in jobs.items():
        try:
            if not os.path.exists(dst):
                if name == "mricore":
                    import gdown; gdown.download(id=MRICORE_GDRIVE, output=dst + ".part", quiet=True); os.replace(dst + ".part", dst)
                elif name == "sam": stream(requests.Session(), SAM_URL, dst)
                else:
                    s = requests.Session(); s.headers["User-Agent"] = "imgsae-m0"; s.get(PF_SHARE, timeout=120, allow_redirects=True)  # guest cookie
                    stream(s, f"{PF_SITE}/_api/web/GetFileByServerRelativeUrl('{PF_PATH}')/$value", dst)
                vol.commit()
            out[name] = dict(path=dst, bytes=os.path.getsize(dst), sha256=_sha256(dst))
        except Exception as e:
            out[name] = dict(error=f"{type(e).__name__}: {e}"[:400])
        print(name, out[name], flush=True)
    return out


MRICORE_PX = 480          # 480 px on the 120 mm crop -> 30 x 30 patch tokens of exactly 4 mm (protocol 5, revised before M1)
IMNET_MEAN, IMNET_STD = (0.485, 0.456, 0.406), (0.229, 0.224, 0.225)   # DINOv2's default input normalisation


def _safe_load(path):
    """torch's safe loader (weights_only=True); argparse.Namespace allow-listed for ProFound's 'args'."""
    import argparse

    import torch
    torch.serialization.add_safe_globals([argparse.Namespace])
    return torch.load(path, map_location="cpu", weights_only=True)


def _mricore(path):
    """MRI-CORE's trained backbone run AS TRAINED: the checkpoint is a DINOv2 teacher ViT-B/16 (cls token, 14 x 14 pos embed at 224 px,
    final norm, chunked blocks, no layer scale, no SAM neck). Its repo's SAM-shaped loader would add a randomly initialised neck and drop
    the trained position embedding (key-name bug), so we build a standard timm ViT-B/16 (global attention), load the 150 backbone tensors
    (chunk index removed; pos embed resampled bicubically 14x14 -> 30x30) strictly, and check every tensor equals the checkpoint."""
    from functools import partial

    import timm
    import torch
    from timm.layers import resample_abs_pos_embed
    raw = _safe_load(path); sd = raw["teacher"]
    bb = {}
    for k, v in sd.items():
        if not k.startswith("backbone.") or k == "backbone.mask_token": continue
        p = k[len("backbone."):].split(".")
        if p[0] == "blocks" and len(p) > 2 and p[1].isdigit() and p[2].isdigit(): p = [p[0]] + p[2:]   # blocks.<chunk>.<i> -> blocks.<i>
        bb[".".join(p)] = v
    g = MRICORE_PX // 16
    m = timm.models.vision_transformer.VisionTransformer(img_size=MRICORE_PX, patch_size=16, embed_dim=768, depth=12, num_heads=12, mlp_ratio=4,
                                                          qkv_bias=True, class_token=True, global_pool="", num_classes=0, init_values=None,
                                                          norm_layer=partial(torch.nn.LayerNorm, eps=1e-6))
    bb["pos_embed"] = resample_abs_pos_embed(bb["pos_embed"], new_size=(g, g), old_size=(14, 14), num_prefix_tokens=1, interpolation="bicubic")
    msg = m.load_state_dict(bb, strict=True)
    st = m.state_dict(); bad = [k for k in bb if k != "pos_embed" and not torch.equal(st[k], bb[k])]
    chk = dict(checkpoint="DINOv2 teacher ViT-B/16", n_backbone_tensors=len(bb), n_model_tensors=len(st), strict_load=str(msg), n_not_equal=len(bad),
               dropped=sorted(k for k in sd if not k.startswith("backbone.") or k == "backbone.mask_token")[:10],
               input=f"{MRICORE_PX} px, ImageNet mean/std (DINOv2 default)", usable=len(bad) == 0 and len(bb) == len(st))
    return m.eval().cuda(), chk


def _enc_vit(m, x, mode, bs=16):
    """MRI-CORE features: normalised patch tokens (B, 768, 30, 30); mode A joins the 3 single-sequence passes (2304-d)."""
    import torch
    mean = torch.tensor(IMNET_MEAN, device=x.device).view(1, 3, 1, 1); std = torch.tensor(IMNET_STD, device=x.device).view(1, 3, 1, 1); outs = []
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16):
        for xi in ([x[:, c:c + 1].repeat(1, 3, 1, 1) for c in range(3)] if mode == "A" else [x]):
            f = []
            for i in range(0, len(xi), bs):
                t = m.forward_features((xi[i:i + bs] - mean) / std).float()[:, 1:]; g = int(round(t.shape[1] ** 0.5))
                f.append(t.transpose(1, 2).reshape(t.shape[0], t.shape[2], g, g))
            outs.append(torch.cat(f))
    return torch.cat(outs, 1)


def _sam(path=None, seed=0):
    import torch
    from segment_anything import sam_model_registry
    torch.manual_seed(seed); sam = sam_model_registry["vit_b"](checkpoint=path)  # official loader: strict
    mean, std = sam.pixel_mean.view(1, 3, 1, 1).cuda(), sam.pixel_std.view(1, 3, 1, 1).cuda()
    return sam.image_encoder.eval().cuda(), (mean, std)


def _profound(path):
    """ProFound-alpha = FCMAE ConvNeXtV2-tiny 3D encoder (args.model 'convnext', input 64 x 224 x 224, epoch 799, no labels). Built with its
    own convnextv2_tiny and remap_checkpoint_keys (sparse kernels -> dense convs); only the final pooled-output norm may be missing."""
    import copy
    sys.path.insert(0, "/opt/ProFound")
    from models.convnextv2 import convnextv2_tiny, remap_checkpoint_keys
    ck = _safe_load(path); a = ck.get("args")
    info = dict(checkpoint_keys=sorted(ck.keys()), epoch=ck.get("epoch"), model=getattr(a, "model", None), input_size=str(getattr(a, "input_size", None)),
                mask_ratio=getattr(a, "mask_ratio", None))
    m = convnextv2_tiny(in_chans=3); sd = remap_checkpoint_keys(copy.deepcopy(ck)); msg = m.load_state_dict(sd, strict=False)
    info.update(missing=list(msg.missing_keys), unexpected=list(msg.unexpected_keys)[:20], n_unexpected=len(msg.unexpected_keys))
    info["usable"] = set(msg.missing_keys) <= {"norm.weight", "norm.bias"} and not msg.unexpected_keys and info["model"] == "convnext"
    return m.eval().cuda(), info


def _slices(z, key_json, size=1024):
    """protocol 5: scaled (T2W, ADC, HBV) slices in [0, 1] (fixed ADC window, per-study percentiles), resized 240 -> size (bilinear).
    Returns (Z, 3, size, size) float32 on the GPU. size 1024 for SAM / untrained, 480 for MRI-CORE (4 mm tokens)."""
    import numpy as np
    import torch
    import torch.nn.functional as Fn
    t2lo, t2hi = key_json["t2w_p05_p995"]; hblo, hbhi = key_json["hbv_p05_p995"]
    t2 = np.clip((z["t2w"] - t2lo) / max(t2hi - t2lo, 1e-6), 0, 1); adc = np.clip(z["adc"] / 3000.0, 0, 1); hb = np.clip((z["hbv"] - hblo) / max(hbhi - hblo, 1e-6), 0, 1)
    x = torch.from_numpy(np.stack([t2, adc, hb], 1).astype(np.float32)).cuda()
    return Fn.interpolate(x, size=(size, size), mode="bilinear", align_corners=False)


def _enc2d(enc, x, mode, norm=None, bs=8):
    """mode A: each channel alone copied to 3 channels, features joined (3 x 256); mode B: the 3 channels together (256)."""
    import torch
    outs = []
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16):
        inputs = [x[:, c:c + 1].repeat(1, 3, 1, 1) for c in range(3)] if mode == "A" else [x]
        for xi in inputs:
            f = []
            for i in range(0, len(xi), bs):
                b = xi[i:i + bs]; b = (b * 255.0 - norm[0]) / norm[1] if norm is not None else b
                f.append(enc(b).float())
            outs.append(torch.cat(f))
    return torch.cat(outs, 1)  # (Z, 256 or 768, 64, 64)


PF_HW = 224   # ProFound-alpha was pretrained on 64 x 224 x 224 crops: the centre 224 x 224 of our 256 x 256 (1 mm) grid, no resampling


def _pf_input(zp):
    """ProFound input: (1, 3, 64, 224, 224) = centre crop of the 1 mm grid; z-score per channel over non-zero voxels (its dataset.py)."""
    import numpy as np
    import torch
    o = (zp["image"].shape[-1] - PF_HW) // 2
    x = zp["image"][:, :, o:o + PF_HW, o:o + PF_HW].astype(np.float32)
    for c in range(3):
        m = x[c] != 0
        if m.any(): v = x[c][m]; x[c][m] = (v - v.mean()) / max(v.std(), 1e-6)
    return torch.from_numpy(x[None]).cuda()


def _pf_stages(m, x):
    """ProFound ConvNeXtV2 stage feature maps (strides 4, 8, 16, 16 voxels = mm). Deterministic (no masking)."""
    import torch
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16):
        _, hid = m(x, ret_hids=True)
    return [h.float() for h in hid]


@app.function(gpu=GPU, cpu=CPU, memory=MEM_GIB * 1024, timeout=TIMEOUT_MIN * 60, retries=0, volumes={"/vol": vol})
def check():
    import os

    import numpy as np
    import torch
    t0 = time.time(); vol.reload(); res = dict(gpu=torch.cuda.get_device_name(0), torch=str(torch.__version__), commits=dict(mricore=MRICORE_COMMIT, profound=PROFOUND_COMMIT, sam=SAM_COMMIT))
    res["weights"] = W = _weights()
    summ = json.load(open("/vol/prep/dev_summary.json")); keys = sorted(summ["random_qc"])[:N_BENCH]; res["bench_keys"] = keys
    arms = {}
    try:
        if "error" in W["mricore"]: raise RuntimeError("no MRI-CORE weights")
        enc, chk = _mricore(W["mricore"]["path"]); res["mricore_check"] = chk; arms["mricore"] = (enc, None)
    except Exception as e: res["mricore_check"] = dict(error=f"{type(e).__name__}: {e}"[:600], usable=False)
    try:
        if "error" in W["sam"]: raise RuntimeError("no SAM weights")
        enc, norm = _sam(W["sam"]["path"]); arms["sam"] = (enc, norm); res["sam_check"] = dict(loaded="official strict loader", usable=True)
    except Exception as e: res["sam_check"] = dict(error=f"{type(e).__name__}: {e}"[:600], usable=False)
    enc, norm = _sam(None, seed=0); arms["untrained"] = (enc, norm)
    pf = None
    try:
        if "error" in W["profound"]: raise RuntimeError("no ProFound weights")
        pf, info = _profound(W["profound"]["path"]); res["profound_check"] = info
    except Exception as e: res["profound_check"] = dict(error=f"{type(e).__name__}: {e}"[:600], usable=False)
    bench = {a: dict(seconds=[], shape=None, finite=True, const_channels=0) for a in ("mricore_A", "mricore_B", "sam_A", "sam_B", "untrained_B", "profound")}
    def note(name, f, sec):
        b = bench[name]; b["seconds"].append(sec); b["shape"] = list(f.shape); b["finite"] &= bool(torch.isfinite(f).all())
        b["const_channels"] = max(b["const_channels"], int((f.transpose(0, 1).reshape(f.shape[1], -1).std(1) == 0).sum()))
    for key in keys:
        z = np.load(f"/vol/prep/dev/{key}.npz"); x1024 = _slices(z, summ["studies"][key], 1024); x480 = _slices(z, summ["studies"][key], MRICORE_PX)
        for arm, (enc, norm) in arms.items():
            for mode in (("B",) if arm == "untrained" else ("A", "B")):
                torch.cuda.synchronize(); t = time.time()
                f = _enc_vit(enc, x480, mode) if arm == "mricore" else _enc2d(enc, x1024, mode, norm)
                torch.cuda.synchronize(); note(f"{arm}_{mode}", f, time.time() - t); del f
        if pf is not None:
            zp = np.load(f"/vol/prep/dev/{key}_pf.npz"); xp = _pf_input(zp); torch.cuda.synchronize(); t = time.time()
            hs = _pf_stages(pf, xp); torch.cuda.synchronize(); note("profound", hs[0], time.time() - t)
            bench["profound"]["stage_shapes"] = [list(h.shape) for h in hs]
            hs2 = _pf_stages(pf, xp); bench["profound"]["repeat_max_diff"] = max(bench["profound"].get("repeat_max_diff", 0.0), float((hs[0] - hs2[0]).abs().max()))
        torch.cuda.empty_cache(); print(f"bench {key} done {(time.time() - t0) / 60:.1f} min", flush=True)
    diff = []
    for b in bench.values():
        s = b.pop("seconds"); b["sec_per_study_median"] = float(np.median(s)) if s else None; b["n"] = len(s)
    res.update(bench=bench, mricore_vs_sam=diff, peak_gpu_gb=torch.cuda.max_memory_allocated() / 1e9, container_min=(time.time() - t0) / 60)
    os.makedirs("/vol/enc_check", exist_ok=True); json.dump(res, open("/vol/enc_check/m0_encoders.json", "w"), indent=1, default=str); vol.commit()
    print(json.dumps({k: v for k, v in res.items() if k != "weights"}, indent=1, default=str), flush=True)
    return res


@app.local_entrypoint()
def main():
    sys.path.insert(0, str(Path(__file__).resolve().parent)); import launch as LN
    LN.launch(check, TASK, APP, "m0_encoder_check", TIMEOUT_MIN, GPU, CPU, MEM_GIB, result_name="m0_encoders")
