"""Local test of image_measures on a synthetic chest phantom with known truth (no real data).
Phantom: air -1000 HU around a body ellipse (+40 HU) holding two lung ellipsoids (-860 HU) with an emphysema block (-980 HU);
padded slices at both ends (exact 0 in normalised units)."""
import time

import numpy as np

import image_measures as M


def hu_to_x(hu):
    v = np.floor((((hu + 600.5) / 1499.0) + 0.5) * 256.0).clip(0, 255)
    return ((v - M.MEAN) / M.STD).astype(np.float32)


T, H, W = 200, 256, 256
z, y, x = np.mgrid[0:T, 0:H, 0:W].astype(np.float32)
hu = np.full((T, H, W), -1000.0, np.float32)
hu += np.random.default_rng(0).normal(0, 20, hu.shape).astype(np.float32)   # noise SD 20 HU
body = ((y - 128) / 100) ** 2 + ((x - 128) / 118) ** 2 <= 1
hu[:, body[0]] = 40.0
lungL = ((z - 100) / 60) ** 2 + ((y - 128) / 60) ** 2 + ((x - 85) / 32) ** 2 <= 1
lungR = ((z - 100) / 60) ** 2 + ((y - 128) / 60) ** 2 + ((x - 171) / 32) ** 2 <= 1
hu[lungL | lungR] = -860.0
emph = lungL & (z < 70)
hu[emph] = -980.0
vol = hu_to_x(hu)
vol[:20] = 0.0
vol[-20:] = 0.0                                                       # padding
t0 = time.time()
r = M.measures(vol, stretch=1.0)
dt = time.time() - t0
lung = (lungL | lungR)
lung[:20] = False
lung[-20:] = False
true_ml = lung.sum() * M.VOX_ML
print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()})
print("true lung ml", round(true_ml, 1), "| true emphysema %", round(100 * (emph & lung).sum() / lung.sum(), 2), "| seconds", round(dt, 2))
assert abs(r["lung_vol_app_ml"] / true_ml - 1) < 0.02
assert abs(r["laa950_pct"] - 100 * (emph & lung).sum() / lung.sum()) < 1.0
assert r["n_real_slices"] == 160 and abs(r["air_median_hu"] + 1000) < 10 and 15 < r["air_noise_sd_hu"] < 25
r2 = M.measures(vol, stretch=2.0)
assert abs(r2["lung_vol_ml"] * 2 - r["lung_vol_app_ml"]) < 1e-3
print("PASS")
