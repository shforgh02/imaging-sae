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
         .pip_install("torch==2.10.0", "torchvision==0.25.0", "numpy==2.4.6", "scipy==1.17.1", "monai==1.5.0", "timm==1.0.16", "einops==0.8.1",
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


def _mricore(path):
    """MRI-CORE with its own builder (adapters off); checks every image-encoder tensor against the checkpoint (their key renaming)."""
    import torch
    sys.path.insert(0, "/opt/mri_foundation"); import cfg; from models.sam import sam_model_registry as reg
    argv = sys.argv; sys.argv = ["cfg"]; args = cfg.parse_args(); sys.argv = argv
    for k, v in dict(if_encoder_adapter=False, if_mask_decoder_adapter=False, if_encoder_lora_layer=False, if_decoder_lora_layer=False,
                     encoder_adapter_depths=[], finetune_type="vanilla").items(): setattr(args, k, v)
    model = reg["vit_b"](args, checkpoint=path, num_classes=1, image_size=1024, pretrained_sam=False)
    raw = torch.load(path, map_location="cpu", weights_only=False); top = sorted(raw.keys())[:8] if isinstance(raw, dict) else str(type(raw))
    sd = raw
    for key in ("teacher", "model", "state_dict"):
        if isinstance(sd, dict) and key in sd and isinstance(sd[key], dict): sd = sd[key]
    ren = {}
    for k, v in sd.items():
        if "decoder" in k or not hasattr(v, "shape"): continue
        ren[k.replace("fc", "lin").replace("backbone.", "")] = v
    enc = model.image_encoder.state_dict(); missing = [k for k in enc if k not in ren]
    bad = [k for k in enc if k in ren and k != "pos_embed" and (ren[k].shape != enc[k].shape or not torch.equal(ren[k].float(), enc[k].float().cpu()))]
    chk = dict(checkpoint_top_keys=top, n_encoder_tensors=len(enc), missing_in_checkpoint=missing[:20], n_missing=len(missing), n_not_equal=len(bad),
               not_equal=bad[:20], usable=(len(missing) == 0 and len(bad) == 0))
    return model.image_encoder.eval().cuda(), chk


def _sam(path=None, seed=0):
    import torch
    from segment_anything import sam_model_registry
    torch.manual_seed(seed); sam = sam_model_registry["vit_b"](checkpoint=path)  # official loader: strict
    mean, std = sam.pixel_mean.view(1, 3, 1, 1).cuda(), sam.pixel_std.view(1, 3, 1, 1).cuda()
    return sam.image_encoder.eval().cuda(), (mean, std)


def _profound(path):
    import torch
    sys.path.insert(0, "/opt/ProFound")
    ck = torch.load(path, map_location="cpu", weights_only=False); keys = sorted(ck.keys()) if isinstance(ck, dict) else []
    a = ck.get("args"); args = {k: str(v) for k, v in vars(a).items()} if a is not None and hasattr(a, "__dict__") else (str(a) if a is not None else None)
    sd = ck.get("model", ck) if isinstance(ck, dict) else ck
    info = dict(checkpoint_keys=keys, epoch=ck.get("epoch") if isinstance(ck, dict) else None, args=args, n_tensors=len(sd),
                patch_embed=[list(v.shape) for k, v in sd.items() if "patch_embed" in k and k.endswith("weight")][:2])
    is_vit = any(k.startswith("blocks.") for k in sd)
    info["variant"] = "vit" if is_vit else "conv_or_other"
    if not is_vit: info["usable"] = False; info["note"] = "not the ViT variant: the Conv code path is written only after inspecting this checkpoint"; return None, info
    from models import mae
    m = mae.mae_vit_base_patch16(norm_pix_loss=False); msg = m.load_state_dict(sd, strict=False)
    info.update(missing=list(msg.missing_keys)[:20], unexpected=list(msg.unexpected_keys)[:20], n_missing=len(msg.missing_keys), n_unexpected=len(msg.unexpected_keys))
    info["usable"] = len([k for k in msg.missing_keys if not k.startswith("decoder") and k != "mask_token"]) == 0
    return m.eval().cuda(), info


def _slices(z, key_json):
    """protocol 5: scaled (T2W, ADC, HBV) slices in [0, 1], resized 240 -> 1024. Returns (Z, 3, 1024, 1024) float32 on the GPU."""
    import numpy as np
    import torch
    import torch.nn.functional as Fn
    t2lo, t2hi = key_json["t2w_p05_p995"]; hblo, hbhi = key_json["hbv_p05_p995"]
    t2 = np.clip((z["t2w"] - t2lo) / max(t2hi - t2lo, 1e-6), 0, 1); adc = np.clip(z["adc"] / 3000.0, 0, 1); hb = np.clip((z["hbv"] - hblo) / max(hbhi - hblo, 1e-6), 0, 1)
    x = torch.from_numpy(np.stack([t2, adc, hb], 1).astype(np.float32)).cuda()
    return Fn.interpolate(x, size=(1024, 1024), mode="bilinear", align_corners=False)


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


def _pf_input(zp):
    """ProFound input: (1, 3, 64, 256, 256), z-score per channel over non-zero voxels (its dataset.py)."""
    import numpy as np
    import torch
    x = zp["image"].astype(np.float32)
    for c in range(3):
        m = x[c] != 0
        if m.any(): v = x[c][m]; x[c][m] = (v - v.mean()) / max(v.std(), 1e-6)
    return torch.from_numpy(x[None]).cuda()


def _pf_tokens(m, x, seed):
    """ProFound encoder tokens in spatial order: forward_encoder(mask_ratio=0) shuffles tokens; ids_restore puts them back."""
    import torch
    torch.manual_seed(seed)
    with torch.no_grad():
        lat, mask, ids = m.forward_encoder(x, 0.0)
        t = torch.gather(lat[:, 1:], 1, ids.unsqueeze(-1).repeat(1, 1, lat.shape[-1]))
    return t  # (1, 256, 768): (d, h, w) = (4, 8, 8)


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
    diff = []
    for key in keys:
        z = np.load(f"/vol/prep/dev/{key}.npz"); x = _slices(z, summ["studies"][key]); feats = {}
        for arm, (enc, norm) in arms.items():
            for mode in (("B",) if arm == "untrained" else ("A", "B")):
                torch.cuda.synchronize(); t = time.time(); f = _enc2d(enc, x, mode, norm); torch.cuda.synchronize()
                b = bench[f"{arm}_{mode}"]; b["seconds"].append(time.time() - t); b["shape"] = list(f.shape); b["finite"] &= bool(torch.isfinite(f).all())
                b["const_channels"] = max(b["const_channels"], int((f.permute(1, 0, 2, 3).reshape(f.shape[1], -1).std(1) == 0).sum()))
                feats[f"{arm}_{mode}"] = f
        if "mricore_B" in feats and "sam_B" in feats:
            a, s = feats["mricore_B"].flatten(), feats["sam_B"].flatten()
            diff.append(dict(key=key, mean_abs_diff=float((a - s).abs().mean()), corr=float(torch.corrcoef(torch.stack([a, s]))[0, 1])))
        if pf is not None:
            zp = np.load(f"/vol/prep/dev/{key}_pf.npz"); xp = _pf_input(zp); torch.cuda.synchronize(); t = time.time()
            t1 = _pf_tokens(pf, xp, seed=1); torch.cuda.synchronize(); bench["profound"]["seconds"].append(time.time() - t)
            t2 = _pf_tokens(pf, xp, seed=2); bench["profound"]["shape"] = list(t1.shape)
            bench["profound"]["finite"] &= bool(torch.isfinite(t1).all()); bench["profound"].setdefault("order_restored_max_diff", 0.0)
            bench["profound"]["order_restored_max_diff"] = max(bench["profound"]["order_restored_max_diff"], float((t1 - t2).abs().max()))
        del feats; torch.cuda.empty_cache(); print(f"bench {key} done {(time.time() - t0) / 60:.1f} min", flush=True)
    for b in bench.values():
        s = b.pop("seconds"); b["sec_per_study_median"] = float(np.median(s)) if s else None; b["n"] = len(s)
    res.update(bench=bench, mricore_vs_sam=diff, peak_gpu_gb=torch.cuda.max_memory_allocated() / 1e9, container_min=(time.time() - t0) / 60)
    os.makedirs("/vol/enc_check", exist_ok=True); json.dump(res, open("/vol/enc_check/m0_encoders.json", "w"), indent=1, default=str); vol.commit()
    print(json.dumps({k: v for k, v in res.items() if k != "weights"}, indent=1, default=str), flush=True)
    return res


@app.local_entrypoint()
def main():
    root = MRI.parents[1]; sys.path.insert(0, str(root / "imgsae" / "exploratory" / "p1b_sanity" / "cloud")); import budget as B
    worst = B.worst_case(1, TIMEOUT_MIN, GPU, CPU, MEM_GIB) + IMAGE_USD; rate = B.rate_h(GPU, CPU, MEM_GIB)
    ok, rep = B.check(TASK, worst); print(json.dumps(rep, indent=1))
    if not ok: raise SystemExit(f"BUDGET CHECK FAILED - not launching (worst case ${worst:.2f})")
    rid = B.open_run(TASK, worst, dict(app=APP, jobs=["m0_encoder_check"], timeout_min=TIMEOUT_MIN, gpu=GPU, cpu=CPU, mem_gib=MEM_GIB))
    print(f"launch {rid}: worst case ${worst:.2f}"); measured, note = IMAGE_USD, "unfinished"
    try:
        out = check.remote(); measured += (out["container_min"] + B.START_MIN) / 60 * rate
        note = f"mricore usable {out.get('mricore_check', {}).get('usable')}, sam {out.get('sam_check', {}).get('usable')}, profound {out.get('profound_check', {}).get('usable')}"
        json.dump(out, open(MRI / "results" / "m0_encoders.json", "w"), indent=1, default=str)
    except BaseException as e:
        measured += (TIMEOUT_MIN + B.START_MIN) / 60 * rate; note = f"failed or client lost: {e!r}"[:300]; raise
    finally:
        B.close_run(rid, measured, note); print(f"closed {rid}: ${measured:.2f} ({note})")
