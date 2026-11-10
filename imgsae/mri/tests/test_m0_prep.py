"""Unit tests for imgsae/mri/m0_prep_lib.py on synthetic data with known answers (run before any cloud job).
usage: D:\\Shayan\\imgsae\\.venv\\Scripts\\python.exe -m pytest -q imgsae/mri/tests  (or run this file directly)
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import m0_prep_lib as L  # noqa: E402


def test_cells_exact():
    m = np.zeros((2, 240, 240), bool); m[0, 0:8, 0:16] = True  # half of the first 16 x 16 cell
    c = L.cells(m, 16); assert c.shape == (2, 15, 15); assert abs(c[0, 0, 0] - 0.5) < 1e-9 and c[0, 0, 1] == 0 and c[1].sum() == 0


def test_capture_rule():
    lab = np.zeros((1, 240, 240), int)
    lab[0, 0:8, 0:8] = 1            # 8 x 8 px lesion: fills a whole 4 mm cell (block 8) but only 25% of an 8 mm cell (block 16)
    lab[0, 100:104, 100:104] = 2    # 4 x 4 px lesion: 25% of a 4 mm cell
    les = lab > 0
    for block, want in ((16, [False, False]), (8, [True, False])):
        occ = L.cells(les, block); assert list(L.captured(lab, 2, occ, block)) == want, (block, list(L.captured(lab, 2, occ, block)))


def test_components_volume():
    les = np.zeros((3, 20, 20), bool); les[0, :2, :2] = True; les[1, 1, 1] = True; les[2, 10, 10] = True  # two 26-connected parts? (0,1) and (2)
    lab, vol = L.components(les, voxel_ml=0.001)
    assert len(vol) == 2 and abs(sorted(vol)[-1] - 0.005) < 1e-12 and abs(sorted(vol)[0] - 0.001) < 1e-12


def test_dice():
    a = np.zeros((1, 4, 4), bool); b = a.copy(); a[0, :2] = True; b[0, 1:3] = True
    assert abs(L.dice(a, b) - 0.5) < 1e-12 and np.isnan(L.dice(np.zeros(3, bool), np.zeros(3, bool)))
    z1 = np.zeros((1, 4, 4), int); z2 = z1.copy(); z1[0, 0] = 1; z2[0, 0] = 1; z1[0, 1] = 2; z2[0, 2] = 2
    assert abs(L.zone_dice(z1, z2) - 0.5) < 1e-12  # PZ Dice 1, TZ Dice 0


def test_crop_centre_and_padding():
    g = np.zeros((10, 300, 300), bool); g[3:6, 140:160, 40:60] = True     # centroid (149.5 -> 150, 49.5 -> 50), near the left edge
    box = L.crop_box(g); assert box[:2] == (2, 7) and box[2] == 150 - 120 and box[3] == 50 - 120
    c, v = L.crop(g.astype(np.uint8), box); assert c.shape == (5, 240, 240) and c.sum() == g.sum() and not v[:, :, :70].any() and v[:, :, 70:].all()


def test_resampling_preserves_box():
    import SimpleITK as sitk
    a = np.zeros((4, 100, 80), np.uint8); a[:, 20:60, 10:50] = 1                  # 40 x 40 px at 0.6 mm = 24 x 24 mm
    img = sitk.GetImageFromArray(a); img.SetSpacing((0.6, 0.6, 3.0)); img.SetOrigin((10.0, -5.0, 2.0))
    ref = L.inplane_grid(img); out = sitk.GetArrayFromImage(L.to_grid(img, ref, nearest=True))
    assert ref.GetSpacing()[:2] == (0.5, 0.5) and out.shape == (4, 120, 96)
    assert abs(out[0].sum() * 0.25 - 24 * 24) / (24 * 24) < 0.06                    # area kept within 6% (pixel rounding at the edges)
    assert L.same_grid(img, img) and not L.same_grid(img, ref)


def test_study_metrics_smoke():
    rng = np.random.default_rng(0); Z = 6
    t2, adc, hb = rng.random((Z, 240, 240)), 1000 + 500 * rng.random((Z, 240, 240)), rng.random((Z, 240, 240))
    valid = np.ones((Z, 240, 240), bool); gl = np.zeros_like(valid); gl[1:5, 80:160, 80:160] = True
    les = np.zeros_like(valid); les[2:4, 100:120, 100:120] = True
    zh = np.where(gl, 2, 0); zh[:, 80:100] = np.where(gl[:, 80:100], 1, 0); zy = zh.copy()
    m = L.study_metrics(t2, adc, hb, valid, les, gl, gl, zh, zy, dz_mm=3.0)
    assert m["dice_gland"] == 1.0 and m["dice_zone"] == 1.0 and len(m["components_ml"]) == 1
    assert abs(m["lesion_ml_total"] - 2 * 400 * 0.25 * 3.0 / 1000) < 1e-9 and m["recall"]["4"]["n_captured"] == 1


if __name__ == "__main__":
    fs = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for f in fs: f(); print("ok", f.__name__)
    print(f"ALL {len(fs)} TESTS PASSED")
