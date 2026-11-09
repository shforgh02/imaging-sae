"""Tile-size benchmark for the CT-FM tiled encode on this GPU (engineering only; analysis unchanged).
usage: .venv\Scripts\python scripts\tile_bench.py SCAN_ID [--spacing 1.0] [--wins 160,192,208]
For each window size (margin fixed at 48, the gate's value): full-scan encode time, peak GPU memory, spill flag, and median cosine of the
token features vs the 160/48 tiling (same quantity as gate E's seam check). Writes logs/tile_bench_<scan>.json.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import torch  # noqa: E402
from imgsae import accel, tokens  # noqa: E402
from imgsae.encoders import ctfm  # noqa: E402

DATA = ROOT.parent / "imgsae_data" / "totalseg"


def cos(a, b):
    a = a.reshape(a.shape[0], -1).T.astype(np.float64); b = b.reshape(b.shape[0], -1).T.astype(np.float64)
    return float(np.median((a * b).sum(1) / np.maximum(np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1), 1e-12)))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("scan"); ap.add_argument("--spacing", type=float, default=1.0); ap.add_argument("--wins", default="160,192,208")
    a = ap.parse_args(); dev = accel.pick("auto")
    hu, _, _ = tokens.load_ct(DATA / a.scan / "ct.nii.gz", a.spacing); x = ctfm.scale(np.where(ctfm.body_mask(hu), hu, -1024.0)); m = ctfm.load(dev)
    print(f"{a.scan} shape {x.shape} at {a.spacing} mm on {accel.name(dev)}", flush=True); ref = None; res = []
    for w in [int(v) for v in a.wins.split(",")]:
        accel.empty_cache(dev); accel.reset_peak(dev)
        try:
            torch.cuda.synchronize(); t0 = time.time(); F, info = ctfm.encode_tiles(m, x, device=dev, win=w, margin=48); sec = time.time() - t0
        except torch.OutOfMemoryError:
            print(f"win {w}: out of memory", flush=True); res.append(dict(win=w, oom=True)); continue
        gb = accel.mem_gb(dev); r = dict(win=w, margin=48, seconds=sec, windows=info["n_windows"], peak_gb=gb, spill=gb > accel.capacity_gb(dev))
        if ref is None: ref = F
        else: r["cos_vs_160"] = cos(ref, F)
        res.append(r); print(json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}), flush=True)
    json.dump(res, open(ROOT / "logs" / f"tile_bench_{a.scan}.json", "w"), indent=1); print("DONE")


if __name__ == "__main__":
    main()
