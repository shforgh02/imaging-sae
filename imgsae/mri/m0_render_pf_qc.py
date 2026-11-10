"""Label-blind QC render of one study's ProFound-grid volume (T2W + Bosma22b gland outline only; NO lesion mask is read).
Writes a PNG with a minimal encoder (no matplotlib/PIL in the project venv). usage: python render_pf_qc.py <pf.npz> <out.png>"""
import struct
import sys
import zlib

import numpy as np
from scipy import ndimage as ndi


def png(path, rgb):
    h, w, _ = rgb.shape; raw = b"".join(b"\x00" + rgb[i].astype(np.uint8).tobytes() for i in range(h))
    def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def panel(img, mask, lo, hi, scale=2):
    g = np.clip((img - lo) / max(hi - lo, 1e-6), 0, 1) * 255; rgb = np.stack([g] * 3, -1)
    edge = mask & ~ndi.binary_erosion(mask); rgb[edge] = (0, 255, 0)
    return np.kron(rgb, np.ones((scale, scale, 1)))


z = np.load(sys.argv[1]); t2 = z["image"][0].astype(np.float32); gl = z["gland"] > 0      # (64, 256, 256) z, y, x
lo, hi = np.percentile(t2[t2 > 0], [0.5, 99.5]); zs = np.flatnonzero(gl.any((1, 2)))
print("gland slices (z index on the 64-slice 1 mm grid):", zs.min() if len(zs) else None, "-", zs.max() if len(zs) else None, "| gland voxels", int(gl.sum()))
zc = int(np.round(np.median(zs))) if len(zs) else 32; yc = int(np.round(np.nonzero(gl)[1].mean())) if gl.any() else 128; xc = int(np.round(np.nonzero(gl)[2].mean())) if gl.any() else 128
ax = [panel(t2[k], gl[k], lo, hi) for k in (max(zc - 12, 0), zc, min(zc + 12, 63))]
sag = panel(np.repeat(t2[:, :, xc], 1, 0), gl[:, :, xc], lo, hi); cor = panel(t2[:, yc, :], gl[:, yc, :], lo, hi)
row1 = np.concatenate(ax, 1); pad = np.zeros((sag.shape[0], row1.shape[1] - sag.shape[1] - cor.shape[1], 3))
row2 = np.concatenate([sag, cor, pad], 1); png(sys.argv[2], np.concatenate([row1, np.full((8, row1.shape[1], 3), 255), row2], 0))
print("written", sys.argv[2], "| axial slices", (max(zc - 12, 0), zc, min(zc + 12, 63)), "| sagittal x", xc, "| coronal y", yc)
