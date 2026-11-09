"""End-to-end smoke test of the Phase 1 chain on tiny synthetic TotalSegmentator-like scans (CPU, minutes; no real data touched).
usage: .venv\Scripts\python scripts/smoke_phase1.py SCRATCH_DIR     (Mac: nice -n 19 .venv/bin/python ...)
Builds 12 phantom scans (112 x 128 x 128 voxels at 1.5 mm, 22 mask structures), then runs p1_encode (CPU), p1_assemble, p1_probe,
perturbation encodes (3 scans x 3 kinds), p1_fit (1 replicate, 30 steps), p1_decide. Prints SMOKE OK if every step ends with DONE.
"""
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; PY = sys.executable
LEAVES = ["liver", "spleen", "kidney_left", "kidney_right", "stomach", "pancreas", "aorta", "heart", "lung_upper_lobe_left", "lung_lower_lobe_left",
          "lung_upper_lobe_right", "lung_lower_lobe_right", "vertebrae_T12", "vertebrae_L1", "vertebrae_L2", "vertebrae_L3", "colon", "small_bowel",
          "urinary_bladder", "autochthon_left", "autochthon_right", "gallbladder"]


def make(root, n=12, shape=(112, 128, 128)):
    import nibabel as nib
    root.mkdir(parents=True, exist_ok=True); rows = ["image_id;age;gender;institute;study_type;split;manufacturer;scanner_model;kvp;pathology;pathology_location"]
    for i in range(n):
        g = np.random.default_rng(i); sid = f"s9{i:03d}"; d = root / sid / "segmentations"; d.mkdir(parents=True, exist_ok=True)
        x, y, z = np.meshgrid(*[np.arange(s) for s in shape], indexing="ij"); c = np.array(shape) / 2 + g.normal(0, 3, 3)
        hu = np.full(shape, -1000.0); body = ((x - c[0]) / 50) ** 2 + ((y - c[1]) / 58) ** 2 < 1; hu[body] = -80 + g.normal(0, 10)
        taken = np.zeros(shape, bool)  # masks mutually exclusive, as in TotalSegmentator (tokens.label_volume lets a later leaf overwrite)
        for j, leaf in enumerate(LEAVES):
            cc = c + np.array([((j * 37) % 60) - 30, ((j * 53) % 70) - 35, ((j * 11) % 90) - 45]) * 1.2 + g.normal(0, 2, 3); r = 13 + (j % 5) * 2
            m = (((x - cc[0]) / r) ** 2 + ((y - cc[1]) / r) ** 2 + ((z - cc[2]) / (r * 1.5)) ** 2 < 1) & body & ~taken; taken |= m
            hu[m] = {"lung": -820, "vert": 500, "aort": 180}.get(leaf[:4], 40 + 5 * j)
            nib.save(nib.Nifti1Image(m.astype(np.uint8), np.diag([1.5, 1.5, 1.5, 1])), d / f"{leaf}.nii.gz")
        hu += g.normal(0, 12, shape); nib.save(nib.Nifti1Image(hu.astype(np.int16), np.diag([1.5, 1.5, 1.5, 1])), root / sid / "ct.nii.gz")
        rows.append(f"{sid};{50 + i};m;{'I' if i % 2 else 'A'};ct thorax-abdomen;train;{'siemens' if i % 3 else 'ge'};x;{120 if i % 2 else 100};{'tumor' if i % 2 else 'no_pathology'};x")
    (root / "meta.csv").write_text("﻿" + "\n".join(rows) + "\n", encoding="utf-8"); (root / "ids.txt").write_text("\n".join(f"s9{i:03d}" for i in range(n)) + "\n")


def run(args, env, log):
    with open(log, "w") as f: rc = subprocess.call(args, stdout=f, stderr=subprocess.STDOUT, cwd=ROOT, env=env)
    txt = Path(log).read_text(encoding="utf-8", errors="replace"); ok = rc == 0 and "DONE" in txt[-3000:]; print(f"{'ok ' if ok else 'FAIL'} {' '.join(args[1:3])}  {txt.strip().splitlines()[-1][:160] if txt.strip() else ''}", flush=True)
    return ok


def main():
    sc = Path(sys.argv[1]); data = sc / "totalseg"; p1 = sc / "p1"; logs = sc / "logs"; logs.mkdir(parents=True, exist_ok=True); make(data)
    env = {**os.environ, "PYTHONUTF8": "1", "IMGSAE_DATA": str(data), "IMGSAE_P1": str(p1), "IMGSAE_MEMO": str(sc / "MEMO.md"), "IMGSAE_LOGS": str(logs), "IMGSAE_IDS": str(data / "ids.txt"),
           "OMP_NUM_THREADS": "2", "MKL_NUM_THREADS": "2", "VECLIB_MAXIMUM_THREADS": "2"}
    ids = str(data / "ids.txt"); (sc / "pert.txt").write_text("s9000\ns9001\ns9002\n"); ok = True
    ok &= run([PY, "scripts/p1_encode.py", ids, "--device", "cpu", "--win", "96", "--margin", "16"], env, logs / "p1_encode_dev.log")
    ok &= run([PY, "scripts/p1_assemble.py"], env, logs / "assemble.log")
    ok &= run([PY, "scripts/p1_probe.py"], env, logs / "probe.log")
    for k in ("shift", "noise", "huoff"):
        ok &= run([PY, "scripts/p1_encode.py", str(sc / "pert.txt"), "--device", "cpu", "--win", "96", "--margin", "16", "--perturb", k, "--out", str(p1 / "perturb" / k)], env, logs / f"pert_{k}.log")
    ok &= run([PY, "scripts/p1_fit.py", "--reps", "1", "--device", "cpu", "--steps", "30"], env, logs / "fit.log")
    ok &= run([PY, "scripts/p1_decide.py"], env, logs / "decide.log")
    print("SMOKE OK" if ok else "SMOKE FAILED")


if __name__ == "__main__":
    main()
