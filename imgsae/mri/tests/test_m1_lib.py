"""Unit tests for imgsae/mri/m1_lib.py (synthetic data, known answers). usage: python imgsae/mri/tests/test_m1_lib.py"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import m1_lib as L  # noqa: E402


def test_overlap_weights():
    W = L.overlap_weights(64, 1.875)
    assert W.shape == (30, 64) and np.allclose(W.sum(1), 1.0)                 # every 4 mm cell fully covered
    assert np.allclose(W @ np.ones(64), 1.0) and abs(W[0, 0] - 1.875 / 4) < 1e-12 and abs(W[0, 2] - 0.25 / 4) < 1e-12
    F = np.random.default_rng(0).random(64)                                    # piecewise-constant source field
    x = (np.arange(120000) + 0.5) / 1000.0; fine = F[np.minimum((x / 1.875).astype(int), 63)]
    direct = fine.reshape(30, 4000).mean(1)                                     # numerical mean over each 4 mm cell
    assert np.allclose(W @ F, direct, atol=1e-6)
    assert np.allclose(L.overlap_weights(30, 4.0), np.eye(30))                 # identity when the grids coincide


def test_keep_and_sample():
    Z = 3; lab = {k: np.zeros((Z, 30, 30)) for k in ("lesion", "gland", "valid", "h_pz", "h_tz", "y_pz", "y_tz")}
    lab["gland"][:, 5:25, 5:25] = 1.0; lab["lesion"][1, 10:12, 10:12] = 1.0; lab["lesion"][1, 12, 10] = 0.3
    keep, idx, sample, les, nor = L.keep_and_sample(lab, "1000123")
    assert keep.sum() == 3 * 400 and les.sum() == 4 and sample[les].all() and (sample & nor).sum() == 200
    assert not sample[(lab["lesion"][keep] > 0) & (lab["lesion"][keep] < 0.5)].any()
    k2 = L.keep_and_sample(lab, "1000123"); assert (k2[2] == sample).all()   # deterministic per study


def test_zone_label():
    z = {k: np.zeros((1, 1, 4)) for k in ("h_pz", "h_tz", "y_pz", "y_tz")}
    z["h_pz"][0, 0, 0] = z["y_pz"][0, 0, 0] = 1; z["h_tz"][0, 0, 1] = z["y_tz"][0, 0, 1] = 1; z["h_pz"][0, 0, 2] = z["y_tz"][0, 0, 2] = 1
    assert list(L.zone_label(z)[0, 0]) == [0, 1, 2, 2]


def test_ref_features():
    Z = 2; t2 = np.zeros((Z, 240, 240)); adc = np.full((Z, 240, 240), 1500.0); hb = np.zeros((Z, 240, 240)); valid = np.ones((Z, 240, 240), bool)
    t2[:, :8, :8] = 1.0   # first cell bright on T2W
    gl = np.zeros((Z, 30, 30)); gl[:, 2:5, 3:6] = 1; keep = np.zeros((Z, 30, 30), bool); keep[0, 0, 0] = keep[0, 3, 4] = True
    R = L.ref_features(t2, adc, hb, valid, gl, keep, (0.0, 1.0), (0.0, 1.0))
    assert R.shape == (2, 63)
    assert R[0, 15] == 1.0 and R[0, 16] == 1.0 and R[0, 17] == 0.0          # T2W cell (0,0): all pixels in the top bin, mean 1, SD 0
    assert R[1, 18 + 8] == 1.0 and abs(R[1, 18 + 16] - 0.5) < 1e-6           # ADC 1500 -> 0.5 -> bin 8; mean 0.5
    assert abs(R[1, 54] - 0.0) < 1e-6 and abs(R[0, 54] - 0.0) < 1e-6         # context mean T2W of neighbours (cell (0,0): neighbours dark)
    assert abs(R[1, 60] - 0.5) < 1e-9 and abs(R[1, 61] - 0.5) < 1e-9          # position x, y of cell (3,4) in bbox x 3..5, y 2..4


if __name__ == "__main__":
    fs = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for f in fs: f(); print("ok", f.__name__)
    print(f"ALL {len(fs)} TESTS PASSED")
