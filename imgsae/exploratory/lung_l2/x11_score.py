"""Lung L2, plan X11 (docs/EXECUTION_LOG.md, 22 Nov, commit 2a624b5): score the padding / synthetic-stretch variants of the X11 dev list on this
PC's CPU with the frozen job's own functions (cloud/l2_sybil_modal.py is imported, never edited). Outcome-free (no label is read).
Each finished exam is written at once (npz of the variant arrays, then a json written last as the done marker); a rerun skips done exams.
usage (sybil env python, -I): python -I x11_score.py <x11_list.csv> <out dir> <download dir> <cloud dev dir> [--only N] [--smoke]
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time

import numpy as np
import pandas as pd
import torch
import torchio as tio

sys.path.insert(0, r"D:\Shayan\imgsae\exploratory\lung_l2\cloud")
import l2_sybil_modal as J  # noqa: E402
from sybil import Serie  # noqa: E402

AIR = (59.0 - 128.1722) / 87.1849          # -1,000 HU after Sybil's window (-600 / 1,500), 8-bit floor division and normalisation
S5 = r"D:\sybil_env\Scripts\s5cmd.exe"
KEYS = ("logit", "pooled", "att_vol1", "att_vol2")


def vol(s, x2d, z_spacing=None, z_pad=0, match_T=None):
    """Sybil's resample, then crop/pad x-y exactly as Sybil (value 0), then z only: optional centre crop to match_T slices, then pad to 200 with z_pad."""
    vs = s._meta.voxel_spacing.clone()
    if z_spacing is not None: vs[2] = float(z_spacing)
    img = tio.ScalarImage(affine=torch.diag(vs), tensor=x2d.permute(0, 2, 3, 1))
    img = s.resample_transform(img); shp = [int(v) for v in img.shape]
    img = tio.transforms.CropOrPad((256, 256, shp[3]), padding_mode=0)(img)
    if match_T is not None and int(match_T) < shp[3]:
        img = tio.transforms.CropOrPad((256, 256, int(match_T)), padding_mode=0)(img)
    img = tio.transforms.CropOrPad((256, 256, 200), padding_mode=z_pad)(img)
    return img.data.permute(0, 3, 1, 2).unsqueeze(0), shp


def pad_profile(v, value):
    """(200,) True where the whole slice equals the constant padding value (None for reflect)."""
    if value is None: return np.zeros(200, bool)
    x = v[0, 0]; return (x == float(value)).flatten(1).all(1).numpy()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("list"); ap.add_argument("out"); ap.add_argument("dl"); ap.add_argument("cloud_dev")
    ap.add_argument("--only", type=int, default=0); ap.add_argument("--smoke", action="store_true"); a = ap.parse_args()
    L = pd.read_csv(a.list); os.makedirs(a.out, exist_ok=True)
    model = J._model()
    for net in model.ensemble: net.to("cpu")
    nA = nB = 0; n_decim1 = 0; n_f25 = 0
    for r in L.itertuples():
        if a.only and (nA + nB) >= a.only: break
        done = os.path.join(a.out, r.series_uid + ".json")
        ident = (r.arm == "A" and nA < 6) or (r.arm == "B" and nB < 6)
        if r.arm == "A": nA += 1
        else: nB += 1
        if os.path.exists(done):
            rec = json.load(open(done)); n_decim1 += int("decim1" in rec["variants"]); n_f25 += int("f25_sp" in rec["variants"]); continue
        t0 = time.time(); d = os.path.join(a.dl, r.series_uid); os.makedirs(d, exist_ok=True)
        res = subprocess.run([S5, "--no-sign-request", "--endpoint-url", "https://s3.amazonaws.com", "cp", r.url, d + "/"], capture_output=True, text=True, timeout=600)
        if res.returncode: raise SystemExit(f"download failed {r.series_uid}: {res.stderr[-300:]}")
        paths = sorted(p for p in glob.glob(os.path.join(d, "**", "*"), recursive=True) if os.path.isfile(p))
        s = Serie(paths, file_type="dicom"); x2d = J._slices(s)
        pos = np.array(s._meta.slice_positions, float); spacing = float(np.median(np.abs(np.diff(pos)))); thick = float(s._meta.thickness)
        # gate G2: the split crop/pad with Sybil's padding equals Sybil's own volume (main and z-fix)
        vm_ref, _ = J._volume(s, x2d); vm, shp_m = vol(s, x2d)
        if not torch.equal(vm, vm_ref): raise SystemExit(f"GATE G2 failed (main) {r.series_uid}")
        V = {}; info = dict(series_uid=r.series_uid, arm=r.arm, maker=r.maker, ratio_list=float(r.ratio), spacing=spacing, thickness=thick, T_main=shp_m[3], gate_G2=True)
        if r.arm == "A":
            vz_ref, _ = J._volume(s, x2d, z_spacing=spacing); vz, shp_z = vol(s, x2d, z_spacing=spacing)
            if not torch.equal(vz, vz_ref): raise SystemExit(f"GATE G2 failed (zfix) {r.series_uid}")
            Tz = min(shp_z[3], 200); info["T_zfix"] = shp_z[3]
            if ident: V["main_sp"] = (vm, 0); V["zfix_sp"] = (vz, 0)
            V["main_air"] = (vol(s, x2d, z_pad=AIR)[0], AIR); V["zfix_air"] = (vol(s, x2d, z_spacing=spacing, z_pad=AIR)[0], AIR)
            V["padmatch_sp"] = (vol(s, x2d, match_T=Tz)[0], 0); V["padmatch_air"] = (vol(s, x2d, z_pad=AIR, match_T=Tz)[0], AIR)
            V["zfix_reflect"] = (vol(s, x2d, z_spacing=spacing, z_pad="reflect")[0], None)
            if abs(spacing / thick - 0.5) < 0.02:
                V["decim0"] = (vol(s, x2d[:, ::2])[0], 0)
                if n_decim1 < 10: V["decim1"] = (vol(s, x2d[:, 1::2])[0], 0); n_decim1 += 1
        else:
            if ident: V["main_sp"] = (vm, 0)
            for f, k in ((1.25, "f125_sp"), (1.5, "f15_sp"), (2.0, "f20_sp")): V[k] = (vol(s, x2d, z_spacing=thick * f)[0], 0)
            _, shp20 = vol(s, x2d, z_spacing=thick * 2.0); info["T_f20"] = shp20[3]
            V["f20_air"] = (vol(s, x2d, z_spacing=thick * 2.0, z_pad=AIR)[0], AIR)
            V["f20_padmatch"] = (vol(s, x2d, z_spacing=thick * 2.0, match_T=min(shp_m[3], 200))[0], 0)
            if shp20[3] >= 200 and n_f25 < 20: V["f25_sp"] = (vol(s, x2d, z_spacing=thick * 2.5)[0], 0); n_f25 += 1
        out, skipped, prof = {}, {}, {}
        for k, (v, padv) in V.items():
            prof[k] = pad_profile(v, padv)
            # an air-padded volume without any z padding is identical to its Sybil-padded twin: no forward pass, reuse the twin
            if k == "main_air" and torch.equal(v, vm): skipped[k] = "identical to main (no z padding)"; continue
            if k == "f20_air" and torch.equal(v, V["f20_sp"][0]): skipped[k] = "identical to f20_sp (no z padding)"; continue
            if k == "zfix_air" and "zfix_sp" in V and torch.equal(v, V["zfix_sp"][0]): skipped[k] = "identical to zfix_sp"; continue
            arr, mean, calib = J._forward(model, v, "cpu")
            out[k] = ({q: np.asarray(arr[q], np.float32) for q in KEYS}, v)
        np.savez_compressed(os.path.join(a.out, r.series_uid + ".npz"), **{f"{k}__{q}": out[k][0][q] for k in out for q in KEYS},
                            **{f"{k}__padprof": prof[k] for k in prof})
        if ident:   # gate G1: local vs cloud logits
            G = {}
            for k, sub in (("main_sp", "main"), ("zfix_sp", "zfix")):
                if k in out:
                    ref = np.load(os.path.join(a.cloud_dev, sub, r.series_uid + ".npz"))
                    G[k] = dict(max_abs_logit=float(np.abs(out[k][0]["logit"] - ref["logit"]).max()), max_abs_pooled=float(np.abs(out[k][0]["pooled"] - ref["pooled"]).max()))
                    if G[k]["max_abs_logit"] > 1e-4: raise SystemExit(f"GATE G1 failed {r.series_uid} {k}: {G[k]}")
            info["gate_G1"] = G
        info.update(variants=sorted(out), skipped=skipped, seconds=round(time.time() - t0, 1), n_padded={k: int(prof[k].sum()) for k in prof})
        json.dump(info, open(done, "w")); shutil.rmtree(d, ignore_errors=True)
        print(f"{r.order:3d} {r.arm} {r.maker:8s} {len(out)} runs {info['seconds']:.0f}s", flush=True)
        if a.smoke: pass


if __name__ == "__main__":
    main()
