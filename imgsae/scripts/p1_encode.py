"""Phase 1 D2-D3: per-scan token table + CT-FM and random-init CT-FM features (resumable; one GPU job).
usage: python scripts/p1_encode.py LIST.txt [--spacing 1.5] [--device auto] [--out data/p1/scans] [--perturb none|shift|noise|huoff]
Writes <out>/<id>.npz with: feat_ctfm, feat_null (n_valid x 512 fp16), occ (n_valid x 117), ref, pos, coords (token centres, mm), gidx,
grid, valid mask, scan json. Footprint watchdog: aborts if accelerator memory (CUDA peak reserved / MPS driver memory) > 12 GB; on CUDA a
'SPILL' warning is printed if the peak exceeds physical VRAM. --device auto = cuda > mps > cpu. Completion line 'DONE <n>' at the end.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from imgsae import accel, tokens  # noqa: E402
from imgsae.encoders import ctfm  # noqa: E402

DATA = Path(os.environ.get("IMGSAE_DATA", ROOT.parent / "imgsae_data" / "totalseg")); P1 = Path(os.environ.get("IMGSAE_P1", ROOT / "data/p1")); CAP_GB = 12.0


def perturb(hu, body, kind, scan, seed):
    """V3-lite perturbations on the HU volume (padded, SPL): half-token shift (+8 voxels in z and x), +50% noise, +20 HU offset in body."""
    if kind == "shift":
        out = np.full_like(hu, -1024.0); out[8:, :, 8:] = hu[:-8, :, :-8]; return out
    if kind == "noise":
        sd0 = scan.get("noise_sd") if np.isfinite(scan.get("noise_sd", np.nan)) else 15.0
        return np.where(body, hu + np.random.default_rng(seed).normal(0, np.sqrt(1.5 ** 2 - 1) * sd0, hu.shape).astype(np.float32), hu)
    if kind == "huoff": return np.where(body, hu + 20.0, hu)
    return hu


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("ids"); ap.add_argument("--spacing", type=float, default=1.5); ap.add_argument("--device", default="auto")
    ap.add_argument("--out", default=str(P1 / "scans")); ap.add_argument("--perturb", default="none"); ap.add_argument("--no-null", action="store_true")
    # win 192 on the 4 GB laptop GPU (was 160 on the Mac); see docs/EXECUTION_LOG.md
    ap.add_argument("--win", type=int, default=192); ap.add_argument("--margin", type=int, default=48); a = ap.parse_args(); a.device = accel.pick(a.device)
    print(f"device {a.device} ({accel.name(a.device)})", flush=True); vram = accel.capacity_gb(a.device)
    ids = [l.strip() for l in open(a.ids) if l.strip()]; out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    enc = {"ctfm": ctfm.load(a.device)}
    if not a.no_null: enc["null"] = ctfm.load(a.device, random_init=True, seed=0)
    n_done = 0
    for k, s in enumerate(ids):
        dst = out / f"{s}.npz"
        if dst.exists(): n_done += 1; continue
        if not (DATA / s / "ct.nii.gz").exists(): print(f"MISSING {s}", flush=True); continue
        t0 = time.time(); T = tokens.scan_table(DATA / s / "ct.nii.gz", DATA / s / "segmentations", a.spacing); t1 = time.time()
        hu = perturb(T["hu"], T["bodymask"], a.perturb, T["scan"], k); x01 = ctfm.scale(hu); v = T["valid"]; feats = {}
        if a.perturb != "none":  # reference features of the perturbed volume (for the HU-histogram SAE arm), aligned like the encoder features
            body_p = T["bodymask"] if a.perturb != "shift" else np.pad(T["bodymask"], ((8, 0), (0, 0), (8, 0)))[:T["bodymask"].shape[0], :, :T["bodymask"].shape[2]]
            R2 = tokens.ref_features(hu, body_p)[0]
            if a.perturb == "shift": R2[:-1] = .5 * (R2[:-1] + R2[1:]); R2[:, :, :-1] = .5 * (R2[:, :, :-1] + R2[:, :, 1:])
            T["ref"] = R2.astype(np.float16)
        for name, m in enc.items():
            accel.reset_peak(a.device); F, info = ctfm.encode_tiles(m, x01, device=a.device, win=a.win, margin=a.margin)
            if a.perturb == "shift":  # content moved +8 voxels (half token) in z and x: sample the perturbed grid at i + 0.5 (mean of i, i+1)
                F = F.astype(np.float32); F[:, :-1] = .5 * (F[:, :-1] + F[:, 1:]); F[:, :, :, :-1] = .5 * (F[:, :, :, :-1] + F[:, :, :, 1:])
            feats[f"feat_{name}"] = np.moveaxis(F, 0, -1)[v].astype(np.float16)
            gb = accel.mem_gb(a.device)
            if gb > vram: print(f"SPILL {s} {name}: peak {gb:.2f} GB > VRAM {vram:.2f} GB (shared-RAM paging, slow)", flush=True)
            if gb > CAP_GB: print(f"ABORT footprint {gb:.1f} GB > {CAP_GB}", flush=True); sys.exit(3)
        gidx = np.argwhere(v); coords = ctfm.token_centres(T["grid"], T["affine"])[np.ravel_multi_index(gidx.T, T["grid"])]
        np.savez_compressed(dst, occ=T["occ"][v], ref=T["ref"][v], pos=T["pos"][v], body=T["body"][v], gidx=gidx, grid=T["grid"], coords=coords.astype(np.float32),
                            ref_names=T["ref_names"], scan=json.dumps(T["scan"]), **feats)
        n_done += 1; print(f"{k + 1}/{len(ids)} {s} tokens {int(v.sum())} table {t1 - t0:.0f}s encode {time.time() - t1:.0f}s", flush=True)
    print(f"DONE {n_done}/{len(ids)}", flush=True)


if __name__ == "__main__":
    main()
