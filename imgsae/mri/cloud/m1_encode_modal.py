"""M1 encodes (docs/MRI_M0M1_PROTOCOL.md sections 5-6) on Modal L4 (task mri_m1_encode): every dev study (QC exclusions removed) through
MRI-CORE A/B, SAM A/B, untrained B, ProFound stage 0, mapped onto the 4 mm common grid; plus per-cell labels and the intensity reference R
(66). Kept cells: gland occupancy > 0 or lesion occupancy > 0. Sensitivity arms (MRI-CORE B with per-slice min-max input; MRI-CORE B
without ImageNet normalisation) only for the probe-sample cells. One file per study (/vol/m1/feats/<key>.npz), saved at once; resumable.
usage (from D:\\Shayan):  modal run --detach imgsae/mri/cloud/m1_encode_modal.py --smoke     (2 studies)
                          modal run --detach imgsae/mri/cloud/m1_encode_modal.py             (4 shards in parallel)
"""
import json
import sys
import time
from pathlib import Path

import modal

TASK, APP, VOL = "mri_m1_encode", "imgsae-mri-m1-encode", "imgsae-picai"
GPU, CPU, MEM_GIB = "L4", 4, 16
NSHARD, TIMEOUT_MIN, SMOKE_N, SMOKE_TIMEOUT_MIN = 4, 54, 2, 10
MRICORE_COMMIT = "0f4f452614013873f8bb58a1fd613dbe36b58aba"; PROFOUND_COMMIT = "6c371406ab86ad53c545444f9adb25014fc1352a"
SAM_COMMIT = "dca509fe793f601edb92606367a655c15ac00fdf"
SHA = dict(mricore="0ca90aeba09568f2e10a2e9851d2f2e22b21796067f5dfc7d65548e1a3078276", sam="ec2df62732614e57411cdcf32a23ffdf28910380d03139ee0f4fcbe91eb8c912",
           profound="c4ff630d052fdae1d8a549ea319a3c9b9a26501a376f79f3b0f8fa6f02612d01")
WPATH = dict(mricore="/vol/weights/MRI_CORE_vitb.pth", sam="/vol/weights/sam_vit_b_01ec64.pth", profound="/vol/weights/profound_alpha_checkpoint-799.pth")
LOCAL = modal.is_local()
MRI = Path(__file__).resolve().parents[1] if LOCAL else Path("/root/mri"); REMOTE = "/root/mri"

image = (modal.Image.debian_slim(python_version="3.11").apt_install("git")
         .pip_install("torch==2.6.0", "torchvision==0.21.0", "numpy==2.4.6", "scipy==1.17.1", "monai==1.5.0", "timm==1.0.16", "einops==0.8.1",
                      "scikit-image==0.25.2", f"git+https://github.com/facebookresearch/segment-anything.git@{SAM_COMMIT}")
         .run_commands(f"git clone https://github.com/pipiwang/ProFound.git /opt/ProFound && cd /opt/ProFound && git checkout {PROFOUND_COMMIT}")
         .env({"PYTHONUNBUFFERED": "1"})
         .add_local_file(MRI / "encoders_lib.py", f"{REMOTE}/encoders_lib.py").add_local_file(MRI / "m1_lib.py", f"{REMOTE}/m1_lib.py")
         .add_local_file(MRI / "data" / "split.json", f"{REMOTE}/split.json")
         .add_local_file(MRI / "results" / "m0_qc_decisions.json", f"{REMOTE}/m0_qc_decisions.json"))
app = modal.App(APP, image=image)
vol = modal.Volume.from_name(VOL)


def _sha256(p):
    import hashlib
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def _keys():
    split = json.load(open(f"{REMOTE}/split.json")); exc = set(json.load(open(f"{REMOTE}/m0_qc_decisions.json"))["excluded"])
    return [k for k in sorted(split["dev_studies"]) if k not in exc]


def _run(shard, nshard, limit=0):
    import os

    import numpy as np
    import torch
    sys.path.insert(0, REMOTE); import encoders_lib as E; import m1_lib as L
    t0 = time.time(); vol.reload()
    for k, p in WPATH.items():
        if _sha256(p) != SHA[k]: raise RuntimeError(f"weights {k}: SHA256 mismatch")
    mc = E.mricore(WPATH["mricore"]); sm, snorm = E.sam(WPATH["sam"]); un, unorm = E.sam(None, seed=0); pf = E.profound(WPATH["profound"])
    Wt = torch.tensor(L.overlap_weights(64, 1.875), dtype=torch.float32, device="cuda")
    def to_grid(f): return torch.einsum("ij,zcjk,lk->zcil", Wt, f, Wt)          # (Z, C, 64, 64) -> (Z, C, 30, 30), exact area weights
    keys = _keys()[shard::nshard]; keys = keys[:limit] if limit else keys
    os.makedirs("/vol/m1/feats", exist_ok=True); done, errors, secs, outside = 0, {}, [], []
    for n, key in enumerate(keys):
        dst = f"/vol/m1/feats/{key}.npz"
        if os.path.exists(dst): done += 1; continue
        try:
            ts = time.time(); z = np.load(f"/vol/prep/dev/{key}.npz"); js = json.load(open(f"/vol/prep/dev/{key}.json")); zp = np.load(f"/vol/prep/dev/{key}_pf.npz")
            lab = L.labels(z); keep, idx, sample, les, nor = L.keep_and_sample(lab, key.split("_")[1]); zone = L.zone_label(lab)[keep]
            R = np.concatenate([L.ref_features(z["t2w"], z["adc"], z["hbv"], z["valid"], lab["gland"], keep, js["t2w_p05_p995"], js["hbv_p05_p995"]),
                                np.eye(3, dtype=np.float32)[zone]], 1)
            kt = torch.from_numpy(keep).cuda(); st = torch.from_numpy(np.argwhere(keep)[sample]).cuda()
            def gather(f): return f.permute(0, 2, 3, 1)[kt].half().cpu().numpy()                      # (n_keep, C)
            def gather_s(f): g = f.permute(0, 2, 3, 1); return g[st[:, 0], st[:, 1], st[:, 2]].half().cpu().numpy()
            x = E.scaled(z, js); x480 = E.resize(x, E.MRICORE_PX); x1024 = E.resize(x, 1024); A = {}
            A["mricore_A"] = gather(E.enc_vit(mc, x480, "A")); A["mricore_B"] = gather(E.enc_vit(mc, x480, "B"))
            S = {"mricore_B_minmax": gather_s(E.enc_vit(mc, E.resize(E.scaled_minmax(z), E.MRICORE_PX), "B")),
                 "mricore_B_noimagenet": gather_s(E.enc_vit(mc, x480, "B", imagenet=False))}
            A["sam_A"] = gather(to_grid(E.enc_sam(sm, x1024, "A", snorm))); A["sam_B"] = gather(to_grid(E.enc_sam(sm, x1024, "B", snorm)))
            A["untrained_B"] = gather(to_grid(E.enc_sam(un, x1024, "B", unorm)))
            xp, off = E.pf_input(zp); g, out = E.pf_to_grid(E.pf_stage0(pf, xp), js, x.shape[0], off); outside.append(out)
            A["profound"] = gather(g.permute(1, 0, 2, 3))
            np.savez_compressed(dst, idx=idx.astype(np.int16), sample=sample, zone=zone.astype(np.int8), R=R,
                                **{f"lab_{k}": v[keep].astype(np.float16) for k, v in lab.items()},
                                **{f"f_{k}": v for k, v in A.items()}, **{f"s_{k}": v for k, v in S.items()},
                                meta=json.dumps(dict(key=key, n_slices=int(x.shape[0]), profound_outside_share=out)))
            done += 1; secs.append(time.time() - ts)
        except Exception as e:
            errors[key] = f"{type(e).__name__}: {e}"[:400]
            if len(errors) >= 3 and done == 0: vol.commit(); raise RuntimeError(f"fail-fast: first studies all failed: {errors}")
        if n % 5 == 4: vol.commit()
        torch.cuda.empty_cache()
        if n % 10 == 0: print(f"shard {shard}: {n + 1}/{len(keys)} {(time.time() - t0) / 60:.1f} min", flush=True)
    vol.commit()
    return dict(shard=shard, n_keys=len(keys), n_done=done, errors=errors, sec_per_study_median=float(np.median(secs)) if secs else None,
                profound_outside_median=float(np.median(outside)) if outside else None, container_min=(time.time() - t0) / 60)


@app.function(gpu=GPU, cpu=CPU, memory=MEM_GIB * 1024, timeout=SMOKE_TIMEOUT_MIN * 60, retries=0, volumes={"/vol": vol})
def encode_smoke():
    return _run(0, NSHARD, limit=SMOKE_N)


@app.function(gpu=GPU, cpu=CPU, memory=MEM_GIB * 1024, timeout=TIMEOUT_MIN * 60, retries=0, volumes={"/vol": vol})
def encode_shard(shard: int):
    return _run(shard, NSHARD)


@app.local_entrypoint()
def main(smoke: bool = False):
    sys.path.insert(0, str(Path(__file__).resolve().parent)); import launch as LN
    if smoke: LN.launch(encode_smoke, TASK, APP, "m1_encode_smoke", SMOKE_TIMEOUT_MIN, GPU, CPU, MEM_GIB, result_name="m1_encode_smoke")
    else: LN.launch_many(encode_shard, [(s,) for s in range(NSHARD)], TASK, APP, "m1_encode", TIMEOUT_MIN, GPU, CPU, MEM_GIB, result_name="m1_encode")
