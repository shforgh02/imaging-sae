"""Phase 1 D2 engineering gate for CT-FM (lean plan v1, gate E). Originally written for the Apple M5 (MPS); ported to any accelerator
(CUDA on the Windows laptop) via imgsae.accel -- the rules below are unchanged.
usage:
  python scripts/p1_d2_engineering.py synthetic [random|ctfm] [--device auto]          phantom volume
  python scripts/p1_d2_engineering.py scans LIST.txt [--n 5] [--spacing 1.5] [--device auto]  first n TotalSegmentator scans with CT-FM
Per volume: full encode on the accelerator in fp16 (time, peak memory); parity = accelerator fp16 vs CPU fp32 on a central 192^3 crop;
seam = two tilings (win 160/margin 48 vs win 224/margin 64) on a central 288^3 crop, interior tokens. Gate E (partial): <= 300 s per scan,
<= 12 GB, parity cosine >= 0.995, seam cosine >= 0.95. Writes logs/p1_d2_engineering_<mode>.json.
Also recorded (informational, not a gate): gpu_capacity_gb and spill = peak > physical VRAM (Windows then pages into shared RAM).
"""
import argparse
import os
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from imgsae import accel, tokens  # noqa: E402
from imgsae.encoders import ctfm  # noqa: E402

DATA = Path(os.environ.get("IMGSAE_DATA", ROOT.parent / "imgsae_data" / "totalseg"))


def phantom(shape=(224, 256, 256), seed=0):
    g = np.random.default_rng(seed); z, y, x = np.meshgrid(*[np.linspace(-1, 1, s) for s in shape], indexing="ij")
    hu = np.full(shape, -1000.0); body = (y / .8) ** 2 + (x / .9) ** 2 < 1; hu[body] = 40
    for sx in (-.4, .4): hu[body & (((x - sx) / .3) ** 2 + (y / .5) ** 2 < 1) & (z > -.2)] = -820
    hu[((x / .08) ** 2 + ((y + .55) / .08) ** 2 < 1)] = 700; hu[body & (((x + .1) / .2) ** 2 + ((y - .2) / .2) ** 2 + ((z + .5) / .3) ** 2 < 1)] = 60
    return (hu + g.normal(0, 15, shape)).astype(np.float32)


def cos_rows(a, b):
    a = a.reshape(a.shape[0], -1).T.astype(np.float64); b = b.reshape(b.shape[0], -1).T.astype(np.float64)
    return float(np.median((a * b).sum(1) / np.maximum(np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1), 1e-12)))


def crop(x, n):
    sl = tuple(slice(max(0, (s - n) // 2 // 16 * 16), max(0, (s - n) // 2 // 16 * 16) + min(n, s)) for s in x.shape); return x[sl]


def check_volume(mm, mc, x01, tag, dev, win=192):
    res = {"tag": tag, "shape": list(x01.shape), "device": dev, "device_name": accel.name(dev), "win": win, "margin": 48}; accel.empty_cache(dev); accel.reset_peak(dev); t0 = time.time()
    F, info = ctfm.encode_tiles(mm, x01, device=dev, win=win, margin=48, half=True)
    res.update(gpu_seconds=time.time() - t0, windows=info["n_windows"], gpu_peak_gb=accel.mem_gb(dev), grid=list(F.shape[1:]))
    c = crop(x01, 192); Fm, _ = ctfm.encode_tiles(mm, c, device=dev, win=win, margin=48, half=True); Fc, _ = ctfm.encode_tiles(mc, c, device="cpu", win=win, margin=48, half=False)
    res["parity_cos_gpu16_vs_cpu32"] = cos_rows(Fm, Fc)
    c = crop(x01, 288); F1, _ = ctfm.encode_tiles(mm, c, device=dev, win=win, margin=48); F2, _ = ctfm.encode_tiles(mm, c, device=dev, win=224, margin=64)
    sl = (slice(None),) + tuple(slice(2, s - 2) for s in F1.shape[1:]); res["seam_cos_tiling_vs_224"] = cos_rows(F1[sl], F2[sl])
    res["gpu_peak_gb_incl_seam"] = accel.mem_gb(dev); res["gpu_capacity_gb"] = accel.capacity_gb(dev); res["spill"] = bool(res["gpu_peak_gb_incl_seam"] > res["gpu_capacity_gb"])
    print(json.dumps(res), flush=True); return res


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("mode"); ap.add_argument("arg", nargs="?", default="random"); ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--spacing", type=float, default=1.5); ap.add_argument("--device", default="auto"); a = ap.parse_args(); out = []; dev = accel.pick(a.device)
    print(f"device {dev} ({accel.name(dev)})", flush=True)
    if a.mode == "synthetic":
        rnd = a.arg == "random"; mm, mc = ctfm.load(dev, random_init=rnd), ctfm.load("cpu", random_init=rnd)
        out.append(check_volume(mm, mc, ctfm.scale(phantom()), f"phantom_{a.arg}", dev))
    else:
        ids = [l.strip() for l in open(a.arg) if l.strip()][:a.n]; mm, mc = ctfm.load(dev), ctfm.load("cpu")
        for s in ids:
            hu, aff, vox = tokens.load_ct(DATA / s / "ct.nii.gz", a.spacing); bm = ctfm.body_mask(hu)
            r = check_volume(mm, mc, ctfm.scale(np.where(bm, hu, -1024.0)), s, dev); r["spacing_native"] = [float(v) for v in vox]; r["spacing"] = a.spacing; out.append(r)
    ok = all(r["gpu_seconds"] <= 300 and r["gpu_peak_gb"] <= 12 and r["parity_cos_gpu16_vs_cpu32"] >= .995 and r["seam_cos_tiling_vs_224"] >= .95 for r in out)
    json.dump(dict(results=out, gate_E_partial=ok, spacing=a.spacing, device=dev, mean_seconds=float(np.mean([r["gpu_seconds"] for r in out]))),
              open(ROOT / "logs" / f"p1_d2_engineering_{a.mode}.json", "w"), indent=1)
    print("GATE_E_PARTIAL", ok, "DONE")


if __name__ == "__main__":
    main()
