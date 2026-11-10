"""M0.3 (docs/MRI_M0M1_PROTOCOL.md section 3): preprocess the DEV half of PI-CAI on Modal (CPU), one study at a time, each saved at once
to the volume imgsae-picai (/prep/dev/<key>.npz + .json; QC PNGs in /prep/qc/). Only dev studies (imgsae/mri/data/split.json) are opened.
Resumable: a study with a saved .json is skipped. Budget: task mri_prep (checked by budget.py before launch).
usage (from D:\\Shayan): C:\\Users\\Arman\\miniconda3\\Scripts\\modal.exe run --detach imgsae/mri/cloud/m0_prep_modal.py
"""
import json
import sys
import time
from pathlib import Path

import modal

TASK, APP, VOL = "mri_prep", "imgsae-mri-m0-prep", "imgsae-picai"
CPU, MEM_GIB, TIMEOUT_MIN, IMAGE_USD, WORKERS = 8, 16, 60, 0.10, 7
SMOKE_N, SMOKE_TIMEOUT_MIN = 5, 15      # smoke run first (5 studies), then the full run; both fit the $0.80 task cap
GLAND_DICE_MIN, ZONE_DICE_MIN, N_RANDOM_QC = 0.8, 0.7, 20
LOCAL = modal.is_local()
MRI = Path(__file__).resolve().parents[1] if LOCAL else Path("/root/mri")
REMOTE = "/root/mri"

image = (modal.Image.debian_slim(python_version="3.11")
         .pip_install("numpy==2.4.6", "scipy==1.17.1", "SimpleITK==2.5.7", "matplotlib==3.9.2")
         .env({"OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "PYTHONUNBUFFERED": "1"})
         .add_local_file(MRI / "m0_prep_lib.py", f"{REMOTE}/m0_prep_lib.py")
         .add_local_file(MRI / "data" / "split.json", f"{REMOTE}/split.json"))
app = modal.App(APP, image=image)
vol = modal.Volume.from_name(VOL)


def _process(key, idx_entry, lroot, qc_kind):
    """one dev study -> npz + json on the volume; returns (key, info or None, error or None)."""
    import os
    import tempfile
    import zipfile

    import numpy as np
    import SimpleITK as sitk
    sys.path.insert(0, REMOTE); import m0_prep_lib as L
    try:
        imgs = {}
        for seq in ("t2w", "adc", "hbv"):
            zname, member = idx_entry[seq]
            with zipfile.ZipFile(f"/vol/raw/zenodo/{zname}") as z, tempfile.TemporaryDirectory() as td:
                imgs[seq] = sitk.ReadImage(z.extract(member, td))
        t2 = imgs["t2w"]; geo = {s: dict(size=list(im.GetSize()), spacing=list(im.GetSpacing()), origin=list(im.GetOrigin()),
                                         direction=list(im.GetDirection())) for s, im in imgs.items()}
        D = f"{lroot}/csPCa_lesion_delineations/human_expert"; A = f"{lroot}/anatomical_delineations"
        les_p = f"{D}/resampled/{key}.nii.gz"; src = "resampled"
        if not os.path.exists(les_p): les_p, src = f"{D}/Pooch25/{key}.nii.gz", "Pooch25"
        paths = dict(lesion=les_p, gland_b=f"{A}/whole_gland/AI/Bosma22b/{key}.nii.gz", gland_g=f"{A}/whole_gland/AI/Guerbet23/{key}.nii.gz",
                     zone_h=f"{A}/zonal_pz_tz/AI/HeviAI23/{key}.nii.gz", zone_y=f"{A}/zonal_pz_tz/AI/Yuan23/{key}.nii.gz")
        masks, minfo = {}, {}
        for k, p in paths.items():
            if not os.path.exists(p): raise FileNotFoundError(f"{k}: {p}")
            m = sitk.ReadImage(p)
            minfo[k] = dict(values=sorted(int(v) for v in np.unique(sitk.GetArrayFromImage(m))), on_t2w_grid=bool(L.same_grid(m, t2)))
            masks[k] = m
        # final grid = the T2W slices at 0.5 x 0.5 mm in-plane; every image and mask is resampled onto it in ONE step (physical
        # coordinates), so ADC/HBV are interpolated once (not first onto T2W, then again in-plane)
        ref = L.inplane_grid(t2)
        arr = {s: sitk.GetArrayFromImage(L.to_grid(im, ref)).astype(np.float32) for s, im in imgs.items()}
        marr = {k: sitk.GetArrayFromImage(L.to_grid(m, ref, nearest=True)).astype(np.uint8) for k, m in masks.items()}
        gb, gg = marr["gland_b"] > 0, marr["gland_g"] > 0
        crop_from = "Bosma22b" if gb.any() else ("Guerbet23" if gg.any() else None)
        if crop_from is None: return key, None, "both gland masks empty"
        box = L.crop_box(gb if gb.any() else gg)
        C = {s: L.crop(a, box)[0] for s, a in arr.items()}; valid = L.crop(arr["t2w"], box)[1]
        M = {k: L.crop(a, box)[0] for k, a in marr.items()}
        dz = float(t2.GetSpacing()[2])
        met = L.study_metrics(C["t2w"], C["adc"], C["hbv"], valid, M["lesion"] >= 1, M["gland_b"] > 0, M["gland_g"] > 0, M["zone_h"], M["zone_y"], dz)
        info = dict(key=key, source=src, crop_from=crop_from, box=list(map(int, box)), geometry=geo, masks=minfo, **met)
        os.makedirs("/vol/prep/dev", exist_ok=True)
        np.savez_compressed(f"/vol/prep/dev/{key}.npz", t2w=C["t2w"], adc=C["adc"], hbv=C["hbv"], valid=valid,
                            lesion=M["lesion"], gland_b=M["gland_b"], gland_g=M["gland_g"], zone_h=M["zone_h"], zone_y=M["zone_y"])
        flagged = (np.isfinite(met["dice_gland"]) and met["dice_gland"] < GLAND_DICE_MIN) or (np.isfinite(met["dice_zone"]) and met["dice_zone"] < ZONE_DICE_MIN) \
            or not np.isfinite(met["dice_gland"])
        info["flagged"] = bool(flagged)
        if qc_kind == "random": _qc_png(key, C, M, met, with_lesion=True)
        if flagged: _qc_png(key, C, M, met, with_lesion=False)
        json.dump(info, open(f"/vol/prep/dev/{key}.json", "w"), default=float)
        return key, info, None
    except Exception as e:
        return key, None, f"{type(e).__name__}: {e}"[:400]


def _qc_png(key, C, M, met, with_lesion):
    """(a) random QC (with lesion outlines) or (b) label-blind gland/zone QC (no lesion outlines)."""
    import os

    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    g = M["gland_b"] > 0; area = g.sum((1, 2)); zs = np.flatnonzero(area)
    if not len(zs): zs = np.array([C["t2w"].shape[0] // 2])
    mid = int(zs[np.argmax(area[zs])])
    def win(x, lo, hi): return np.clip((x - lo) / max(hi - lo, 1e-6), 0, 1)
    t2lo, t2hi = met["t2w_p05_p995"]; hblo, hbhi = met["hbv_p05_p995"]
    os.makedirs("/vol/prep/qc", exist_ok=True)
    if with_lesion:
        fig, ax = plt.subplots(1, 3, figsize=(12, 4.2))
        for a, (name, img) in zip(ax, (("T2W", win(C["t2w"][mid], t2lo, t2hi)), ("ADC 0-3000", win(C["adc"][mid], 0, 3000)), ("HBV", win(C["hbv"][mid], hblo, hbhi)))):
            a.imshow(img, cmap="gray"); a.set_title(name, fontsize=9); a.axis("off")
            a.contour(M["gland_b"][mid] > 0, [0.5], colors="lime", linewidths=0.8); a.contour(M["gland_g"][mid] > 0, [0.5], colors="cyan", linewidths=0.6, linestyles="dashed")
            a.contour(M["zone_h"][mid] == 1, [0.5], colors="yellow", linewidths=0.5)
            if (M["lesion"][mid] >= 1).any(): a.contour(M["lesion"][mid] >= 1, [0.5], colors="red", linewidths=1.0)
        fig.suptitle(f"{key} slice {mid}  gland Dice {met['dice_gland']:.2f}  zone Dice {met['dice_zone']:.2f}  lesion {met['lesion_ml_total']:.2f} ml "
                     "(green Bosma22b, cyan Guerbet23, yellow PZ HeviAI23, red lesion)", fontsize=8)
        fig.savefig(f"/vol/prep/qc/random_{key}.png", dpi=110, bbox_inches="tight")
    else:  # label-blind: no lesion outlines; three slices (base, mid, apex) of the union gland
        sl = sorted(set([int(zs[0]), mid, int(zs[-1])]))
        fig, ax = plt.subplots(2, len(sl), figsize=(4 * len(sl), 8.2), squeeze=False)
        for j, z in enumerate(sl):
            for i, (zm, zname) in enumerate(((M["zone_h"], "HeviAI23"), (M["zone_y"], "Yuan23"))):
                a = ax[i, j]; a.imshow(win(C["t2w"][z], t2lo, t2hi), cmap="gray"); a.axis("off")
                a.contour(M["gland_b"][z] > 0, [0.5], colors="lime", linewidths=0.9); a.contour(M["gland_g"][z] > 0, [0.5], colors="cyan", linewidths=0.9, linestyles="dashed")
                a.contour(zm[z] == 1, [0.5], colors="yellow", linewidths=0.6); a.contour(zm[z] == 2, [0.5], colors="orange", linewidths=0.6)
                a.set_title(f"slice {z}, zones {zname}", fontsize=8)
        fig.suptitle(f"{key}  LABEL-BLIND gland/zone QC  gland Dice {met['dice_gland']:.2f}  zone Dice {met['dice_zone']:.2f} "
                     "(green Bosma22b, cyan dashed Guerbet23, yellow PZ, orange TZ)", fontsize=8)
        fig.savefig(f"/vol/prep/qc/glandqc_{key}.png", dpi=110, bbox_inches="tight")
    plt.close("all")


@app.function(cpu=CPU, memory=MEM_GIB * 1024, timeout=SMOKE_TIMEOUT_MIN * 60, retries=0, volumes={"/vol": vol})
def prep_smoke():
    return _run(SMOKE_N)


@app.function(cpu=CPU, memory=MEM_GIB * 1024, timeout=TIMEOUT_MIN * 60, retries=0, volumes={"/vol": vol})
def prep_full():
    return _run(0)


def _run(limit):
    import os
    from concurrent.futures import ProcessPoolExecutor, as_completed

    import numpy as np
    t0 = time.time(); vol.reload()
    split = json.load(open(f"{REMOTE}/split.json")); keys = sorted(split["dev_studies"]); idx = json.load(open("/vol/raw/zenodo/index.json"))
    fs = json.load(open("/vol/raw/fetch_summary.json")); lroot = fs["labels_root"]
    rnd = set(np.array(keys)[np.random.default_rng(0).permutation(len(keys))[:N_RANDOM_QC]].tolist())
    todo = [k for k in keys if not os.path.exists(f"/vol/prep/dev/{k}.json")]
    if limit: todo = todo[:limit]
    missing = [k for k in todo if k not in idx or not all(s in idx[k] for s in ("t2w", "adc", "hbv"))]
    print(f"dev studies {len(keys)}; to do {len(todo)}; missing in index {len(missing)}", flush=True)
    errors, n = {k: "not in image index (t2w/adc/hbv)" for k in missing}, 0
    with ProcessPoolExecutor(WORKERS) as ex:
        futs = [ex.submit(_process, k, idx[k], lroot, "random" if k in rnd else "") for k in todo if k not in missing]
        for f in as_completed(futs):
            k, info, err = f.result(); n += 1
            if err: errors[k] = err
            if n % 5 == 0 or err: vol.commit(); print(f"{n}/{len(futs)} {k} {'ERROR ' + err if err else 'ok'}  {(time.time() - t0) / 60:.1f} min", flush=True)
    vol.commit()
    summ = {}
    for k in keys:
        p = f"/vol/prep/dev/{k}.json"
        if os.path.exists(p): summ[k] = json.load(open(p))
    out = dict(n_dev=len(keys), n_done=len(summ), errors=errors, random_qc=sorted(rnd), container_min=(time.time() - t0) / 60)
    json.dump(dict(**out, studies=summ), open("/vol/prep/dev_summary.json", "w"), default=float); vol.commit()
    print(json.dumps({k: v for k, v in out.items() if k != "studies"}, indent=1, default=float), flush=True)
    return dict(**out, studies=summ)


@app.local_entrypoint()
def main(smoke: bool = False):
    root = MRI.parents[1]; sys.path.insert(0, str(root / "imgsae" / "exploratory" / "p1b_sanity" / "cloud")); import budget as B
    tmin = SMOKE_TIMEOUT_MIN if smoke else TIMEOUT_MIN
    worst = B.worst_case(1, tmin, None, CPU, MEM_GIB) + IMAGE_USD; rate = B.rate_h(None, CPU, MEM_GIB)
    ok, rep = B.check(TASK, worst); print(json.dumps(rep, indent=1))
    if not ok: raise SystemExit(f"BUDGET CHECK FAILED - not launching (worst case ${worst:.2f})")
    rid = B.open_run(TASK, worst, dict(app=APP, jobs=["prep_smoke" if smoke else "prep_full"], timeout_min=tmin, gpu=None, cpu=CPU, mem_gib=MEM_GIB))
    print(f"launch {rid}: worst case ${worst:.2f}"); measured, note = IMAGE_USD, "unfinished"
    try:
        out = (prep_smoke if smoke else prep_full).remote(); measured += (out["container_min"] + B.START_MIN) / 60 * rate
        note = f"done {out['n_done']}/{out['n_dev']}, errors {len(out['errors'])}"
        (MRI / "results").mkdir(exist_ok=True); json.dump(out, open(MRI / "results" / "m0_prep_summary.json", "w"), indent=1, default=float)
    except BaseException as e:
        measured += (tmin + B.START_MIN) / 60 * rate; note = f"failed or client lost: {e!r}"[:300]; raise
    finally:
        B.close_run(rid, measured, note); print(f"closed {rid}: ${measured:.2f} ({note})")
