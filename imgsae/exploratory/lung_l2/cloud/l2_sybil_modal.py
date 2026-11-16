"""Lung L2 (docs/LUNG_L2_PROTOCOL.md): Sybil activations, image measures and variants for dev (S2, S3) and later test (S6).
Task lung_l2_audit, app imgsae-lung-l2, volume imgsae-nlst-l2. Built on the L1 job (lung_l1/cloud/l1_sybil_modal.py).
usage (from D:\\Shayan, miniconda python, PYTHONUTF8=1, always with --detach and always with the account as --profile; never
`modal profile activate`):
  modal run --detach --profile <shforghani2002|armanfo> imgsae/exploratory/lung_l2/cloud/l2_sybil_modal.py --step smoke --n-series 3
  ... --step run --tier D1 --lo 0 --hi 300 --nshard 4 --timeout-min 30 --zfix-max 0.95 --root dev     (T4)
  ... --step run_l4 --tier D1 --lo 0 --hi 50 --nshard 1 --timeout-min 20 --zfix-max 0.95 --root l4    (L4, timing)
  ... --step run --tier D1 --lo 0 --hi 20 --nshard 1 --timeout-min 15 --zfix-max 0.95 --root rep      (repeat, determinism)
  ... --step count --root dev                                                                          (CPU: files on the volume)
Per series and variant: /vol/l2/<root>/<variant>/<uid>.npz (+ .json, written last = done). Errors: /vol/l2/<root>/errors/<uid>.json.
Variants: 'main' (Sybil as published), 'zfix' (same images, z voxel size = true slice spacing; added to 'main' rows whose
DICOM spacing/thickness <= zfix_max), 'pair' (manifest rows of tier D4). No DICOM is kept. The volume is committed every 25 series.
"""
import json
import sys
import time
from pathlib import Path

import modal

TASK, APP, VOL = "lung_l2_audit", "imgsae-lung-l2", "imgsae-nlst-l2"
CPU, MEM_GIB = 4, 16
SYBIL_COMMIT = "d9fc81b93c1c6239a570c1c570c1f2a2e6266a4a"
DEMO_URL = "https://www.dropbox.com/scl/fi/covbvo6f547kak4em3cjd/sybil_example.zip?rlkey=7a13nhlc9uwga9x7pmtk1cf1c&dl=1"
DEMO_REF = [0.021628819563619374, 0.03857256315036462, 0.07191945816622261, 0.07926975188037134, 0.09584583525781108, 0.13568094038444453]
LOCAL = modal.is_local()
HERE = Path(__file__).resolve().parent if LOCAL else Path("/root/l2")
L2 = HERE.parent if LOCAL else Path("/root/l2")
REMOTE = "/root/l2"
MANIFEST = "manifest_dev.csv"

image = (modal.Image.debian_slim(python_version="3.10")
         .apt_install("git", "unzip", "wget", "libgl1", "libglib2.0-0")
         .pip_install("torch==1.13.1", "torchvision==0.14.1", "numpy==1.24.1", "imageio==2.34.1", "opencv-python==4.5.4.60", "opencv-python-headless==4.5.4.60",
                      "pillow>=10.2.0", "pydicom==2.3.0", "pylibjpeg[all]==2.0.0", "torchio==0.18.74", "tqdm==4.62.3", "idc-index", "pandas", "importlib-metadata", "scipy")
         .pip_install(f"git+https://github.com/reginabarzilaygroup/Sybil.git@{SYBIL_COMMIT}", extra_options="--no-deps")   # as L1 (torch==1.13.1+cu117 is not on the mirror)
         .run_commands("python -c \"from sybil import Sybil; Sybil('sybil_ensemble')\"")   # checkpoints into /root/.sybil at build time
         .env({"PYTHONUNBUFFERED": "1"})
         .add_local_file(HERE / "image_measures.py", f"{REMOTE}/image_measures.py")
         .add_local_file(L2 / "results" / MANIFEST, f"{REMOTE}/{MANIFEST}"))
app = modal.App(APP, image=image)
vol = modal.Volume.from_name(VOL, create_if_missing=True)


# ------------------------------------------------------------------ helpers (container side)
def _sha256(p):
    import hashlib
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def _ckpt_hashes():
    import os
    root = os.path.expanduser("~/.sybil"); out = {}
    for dp, _, fs in os.walk(root):
        for f in sorted(fs):
            if f.endswith((".ckpt", ".p", ".json", ".pt", ".pth")): out[os.path.relpath(os.path.join(dp, f), root)] = _sha256(os.path.join(dp, f))
    return out


_CAP = {}


def _model():
    """Sybil ensemble on the GPU, with forward hooks that copy the pooled vector, the pre-ReLU hidden vector, raw hazards and base hazard."""
    import torch
    from sybil import Sybil
    model = Sybil("sybil_ensemble", device="cuda" if torch.cuda.is_available() else "cpu")
    for i, net in enumerate(model.ensemble):
        net.eval()
        net.pool.hidden_fc.register_forward_hook(lambda m, inp, out, i=i: _CAP.setdefault(i, {}).update(pooled=inp[0].detach().clone(), pre=out.detach().clone()))
        net.prob_of_failure_layer.hazard_fc.register_forward_hook(lambda m, inp, out, i=i: _CAP.setdefault(i, {}).update(raw=out.detach().clone()))   # clone: ReLU after it is in place
        net.prob_of_failure_layer.base_hazard_fc.register_forward_hook(lambda m, inp, out, i=i: _CAP.setdefault(i, {}).update(base=out.detach().clone()))
    return model


def _save_heads(model, path):
    import numpy as np
    d = {}
    for i, net in enumerate(model.ensemble):
        for name, lin in (("hidden_fc", net.pool.hidden_fc), ("hazard_fc", net.prob_of_failure_layer.hazard_fc), ("base_hazard_fc", net.prob_of_failure_layer.base_hazard_fc)):
            d[f"m{i}_{name}_W"] = lin.weight.detach().cpu().numpy().astype(np.float32)
            d[f"m{i}_{name}_b"] = lin.bias.detach().cpu().numpy().astype(np.float32)
    np.savez(path, **d)


def _slices(s):
    """Sybil's own per-slice loading (window, 8-bit, resize to 256, normalise), as in Serie.get_volume; returns (C, T, H, W)."""
    import torch
    dicts = [s._loader.get_image(p) for p in s._meta.paths]
    return torch.cat([d["input"].unsqueeze(0) for d in dicts], dim=0).permute(1, 0, 2, 3)


def _volume(s, x2d, z_spacing=None):
    """Serie.get_volume from the loaded slices; z_spacing replaces the z voxel size (Sybil uses SliceThickness). Returns (volume, resampled shape)."""
    import torch
    import torchio as tio
    vs = s._meta.voxel_spacing.clone()
    if z_spacing is not None: vs[2] = float(z_spacing)
    img = tio.ScalarImage(affine=torch.diag(vs), tensor=x2d.permute(0, 2, 3, 1))
    img = s.resample_transform(img)
    shp = [int(v) for v in img.shape]          # (C, H, W, T) before crop/pad
    img = s.padding_transform(img)
    return img.data.permute(0, 3, 1, 2).unsqueeze(0), shp


def _tags(path):
    import pydicom
    d = pydicom.dcmread(path, stop_before_pixels=True); out = {}
    for k in ("Manufacturer", "ManufacturerModelName", "ConvolutionKernel", "SliceThickness", "PixelSpacing", "KVP", "Exposure", "XRayTubeCurrent",
              "ExposureTime", "ReconstructionDiameter", "GantryDetectorTilt", "SpiralPitchFactor", "CTDIvol", "ImageType", "SeriesDescription",
              "Rows", "Columns", "PatientPosition", "BodyPartExamined"):
        v = getattr(d, k, None)
        out[k] = None if v is None else (list(map(str, v)) if isinstance(v, (list, tuple)) or type(v).__name__ == "MultiValue" else str(v))
    return out


def _forward(model, vol_t, dev):
    """five members; returns dict of numpy arrays (member axis first) and the published calibrated probabilities."""
    import numpy as np
    import torch
    keys = ("h", "pre", "pooled", "raw_haz", "base_haz", "logit", "att_img1", "att_vol1", "att_vol2")
    acc = {k: [] for k in keys}
    with torch.no_grad():
        v = vol_t.to(dev)
        for i, net in enumerate(model.ensemble):
            out = net(v); c = _CAP[i]
            acc["h"].append(out["hidden"][0].float().cpu().numpy()); acc["pre"].append(c["pre"][0].float().cpu().numpy())
            acc["pooled"].append(c["pooled"][0].float().cpu().numpy()); acc["raw_haz"].append(c["raw"][0].float().cpu().numpy())
            acc["base_haz"].append(c["base"][0].float().cpu().numpy()); acc["logit"].append(out["logit"][0].float().cpu().numpy())
            acc["att_img1"].append(out["image_attention_1"][0].cpu().numpy().astype(np.float16))
            acc["att_vol1"].append(out["volume_attention_1"][0].cpu().numpy().astype(np.float16))
            acc["att_vol2"].append(out["volume_attention_2"][0].cpu().numpy().astype(np.float16))
    arr = {k: np.stack(v) for k, v in acc.items()}
    probs = 1.0 / (1.0 + np.exp(-arr["logit"].astype(np.float64)))      # (5, 6), as Sybil: sigmoid per member
    mean = probs.mean(0)
    calib = np.asarray(model._calibrate(mean[None, :]))[0]
    return arr, [float(x) for x in mean], [float(x) for x in calib]


def _save(root, variant, uid, arr, rec):
    import os

    import numpy as np
    d = f"/vol/l2/{root}/{variant}"; os.makedirs(d, exist_ok=True)
    np.savez(f"{d}/{uid}.npz", **arr)
    json.dump(rec, open(f"{d}/{uid}.json", "w"))           # written last: its presence means the series is done


def _download(s5, url, d):
    import glob
    import os
    import subprocess
    r = subprocess.run([s5, "--no-sign-request", "--endpoint-url", "https://s3.amazonaws.com", "cp", url, d + "/"], capture_output=True, text=True, timeout=300)
    if r.returncode: raise RuntimeError(f"s5cmd rc={r.returncode}: {r.stderr[-300:]}")
    return sorted(p for p in glob.glob(os.path.join(d, "**", "*"), recursive=True) if os.path.isfile(p))


def _s5():
    import shutil
    p = shutil.which("s5cmd")
    if p: return p
    from idc_index import IDCClient
    return IDCClient().s5cmdPath


def _prepare(row, d, s5, zfix_max, verify=False):
    """download + load + build volumes + image measures (CPU; runs in the prefetch thread). verify: compare the rebuilt main volume with
    Sybil's own Serie.get_volume() while the DICOM files still exist (they are deleted right after this function)."""
    import numpy as np
    import pydicom
    import torch
    from sybil import Serie

    import image_measures as IM
    t0 = time.time(); allf = _download(s5, row["url"], d); t1 = time.time()
    paths = []
    for p in allf:
        try: pydicom.dcmread(p, stop_before_pixels=True); paths.append(p)
        except Exception: pass
    s = Serie(paths, file_type="dicom")
    pos = np.array(s._meta.slice_positions, float); dz = np.abs(np.diff(pos))
    thick = float(s._meta.thickness); spacing = float(np.median(dz)) if len(dz) else float("nan")
    geo = dict(n_files=len(allf), n_images=len(paths), thickness=thick, true_spacing=spacing, ratio=spacing / thick if thick else None,
               n_zero_steps=int((dz < 1e-3).sum()), spacing_min=float(dz.min()) if len(dz) else None, spacing_max=float(dz.max()) if len(dz) else None,
               pixel_spacing=[float(v) for v in s._meta.pixel_spacing], z_first=float(pos[0]), z_last=float(pos[-1]))
    x2d = _slices(s); t2 = time.time()
    out = {}
    v, shp = _volume(s, x2d); geo["resampled_shape_main"] = shp
    out["main"] = (v, IM.measures(v[0, 0].numpy(), stretch=thick / spacing if spacing > 0 else 1.0, z_cropped=shp[3] > 200))
    want_zfix = row["variant"] == "main" and geo["ratio"] is not None and geo["ratio"] <= zfix_max and spacing > 0
    if want_zfix:
        vz, shpz = _volume(s, x2d, z_spacing=spacing); geo["resampled_shape_zfix"] = shpz
        out["zfix"] = (vz, IM.measures(vz[0, 0].numpy(), stretch=1.0, z_cropped=shpz[3] > 200))
    geo["zfix_needed"] = bool(want_zfix)
    tags = _tags(s._meta.paths[len(s._meta.paths) // 2])
    sec = dict(download=t1 - t0, load=t2 - t1, volumes_measures=time.time() - t2)
    ver = bool(torch.equal(out["main"][0], s.get_volume())) if verify else None
    return dict(vols=out, geo=geo, tags=tags, sec=sec, verify_equal=ver)


def _done(root, row):
    import os
    j = f"/vol/l2/{root}/{row['variant']}/{row['series_uid']}.json"
    if not os.path.exists(j): return False
    try: rec = json.load(open(j))
    except Exception: return False
    return (not rec.get("geo", {}).get("zfix_needed")) or os.path.exists(f"/vol/l2/{root}/zfix/{row['series_uid']}.json")


def _rows(tier, lo, hi, shard, nshard):
    import pandas as pd
    m = pd.read_csv(f"{REMOTE}/{MANIFEST}", dtype={"pid": str})
    m = m[(m.tier == tier) & (m.pos >= lo) & (m.pos < hi)].sort_values("pos").iloc[shard::nshard]
    return m.to_dict("records")


def _score_rows(rows, root, zfix_max, tag, t0, limit_s, verify=False, model=None):
    import os
    import shutil
    import tempfile
    from concurrent.futures import ThreadPoolExecutor

    import torch
    sys.path.insert(0, REMOTE)
    model = model or _model(); dev = "cuda" if torch.cuda.is_available() else "cpu"
    gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    os.makedirs(f"/vol/l2/{root}/errors", exist_ok=True)
    todo = [r for r in rows if not _done(root, r)]
    s5 = _s5(); base = tempfile.mkdtemp(prefix="l2_")
    done, errs, T, ver = 0, {}, [], []

    def fetch(r):
        d = os.path.join(base, r["series_uid"]); os.makedirs(d, exist_ok=True)
        try: return r, _prepare(r, d, s5, zfix_max, verify), None
        except Exception as e: return r, None, f"{type(e).__name__}: {e}"[:500]
        finally: shutil.rmtree(d, ignore_errors=True)
    ex = ThreadPoolExecutor(2); fut = [ex.submit(fetch, r) for r in todo[:3]]; nxt = 3
    for n in range(len(todo)):
        r, P, err = fut[n].result(); fut[n] = None
        if nxt < len(todo): fut.append(ex.submit(fetch, todo[nxt])); nxt += 1
        uid = r["series_uid"]
        try:
            if err: raise RuntimeError(err)
            if verify:   # the rebuilt volume must equal Sybil's own Serie.get_volume() (checked in _prepare)
                ver.append(dict(series_uid=uid, equal=P["verify_equal"]))
            sec = dict(P["sec"])
            for var, (v, meas) in P["vols"].items():
                ti = time.time(); arr, mean, calib = _forward(model, v, dev); sec[f"infer_{var}"] = time.time() - ti
                variant = r["variant"] if var == "main" else var
                rec = dict(series_uid=uid, pid=str(r["pid"]), study_yr=int(r["study_yr"]), tier=r["tier"], variant=variant, pos=int(r["pos"]),
                           pilot=bool(r.get("pilot", False)), partner_of=r.get("partner_of") if isinstance(r.get("partner_of"), str) else "",
                           calib=calib, mean_prob=mean, geo=P["geo"], tags=P["tags"], measures=meas, sec=sec, gpu=gpu)
                _save(root, variant, uid, arr, rec)
            done += 1; T.append(sec)
        except Exception as e:
            errs[uid] = f"{type(e).__name__}: {e}"[:500]
            json.dump(dict(series_uid=uid, error=errs[uid]), open(f"/vol/l2/{root}/errors/{uid}.json", "w"))
        P = None
        if (n + 1) % 25 == 0: vol.commit(); print(f"{tag}: {n + 1}/{len(todo)} errs={len(errs)} {(time.time() - t0) / 60:.1f} min", flush=True)
        if time.time() - t0 > limit_s: print("time limit reached, stopping cleanly", flush=True); break
    vol.commit(); ex.shutdown(wait=False, cancel_futures=True); shutil.rmtree(base, ignore_errors=True)
    keys = sorted({k for s in T for k in s})
    mean = {k: (sum(s.get(k, 0.0) for s in T) / max(1, sum(k in s for s in T))) for k in keys}
    return dict(n_rows=len(rows), n_todo=len(todo), n_done=done, errors=errs, mean_sec=mean, gpu=gpu, verify=ver,
                torch=str(torch.__version__), cuda=str(torch.version.cuda))   # plain str: torch.__version__ needs torch to unpickle locally


# ------------------------------------------------------------------ cloud functions
@app.function(gpu="T4", cpu=CPU, memory=MEM_GIB * 1024, timeout=20 * 60, retries=0, volumes={"/vol": vol})
def smoke(n_series: int = 3, zfix_max: float = 0.95):
    """S2 step 0: demo case through the L2 path (must match the published scores within 0.005) and through Serie.get_volume;
    head weights, calibrator, checkpoint hashes saved once; then the first n_series pilot rows scored (root 'dev') with volume verification."""
    import glob
    import os
    import shutil
    import subprocess

    import pydicom
    import torch
    from sybil import Serie
    t0 = time.time(); vol.reload(); sys.path.insert(0, REMOTE)
    out = dict(gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None, torch=str(torch.__version__))
    model = _model(); dev = "cuda" if torch.cuda.is_available() else "cpu"
    os.makedirs("/vol/l2/run_info", exist_ok=True)
    _save_heads(model, "/vol/l2/run_info/heads.npz")
    cal = os.path.expanduser("~/.sybil/sybil_ensemble_simple_calibrator.json")
    shutil.copy(cal, "/vol/l2/run_info/sybil_ensemble_simple_calibrator.json")
    out["ckpt_sha256"] = _ckpt_hashes(); out["heads_sha256"] = _sha256("/vol/l2/run_info/heads.npz"); out["sybil_commit"] = SYBIL_COMMIT
    os.makedirs("/tmp/demo", exist_ok=True)
    subprocess.run(["wget", "-q", "-T", "60", "-t", "2", "-O", "/tmp/demo/d.zip", DEMO_URL], check=True, timeout=180)
    subprocess.run(["unzip", "-q", "-o", "/tmp/demo/d.zip", "-d", "/tmp/demo/x"], check=True, timeout=120)
    paths = []
    for p in sorted(p for p in glob.glob("/tmp/demo/x/**/*", recursive=True) if os.path.isfile(p)):
        try: pydicom.dcmread(p, stop_before_pixels=True); paths.append(p)
        except Exception: pass
    s = Serie(paths, file_type="dicom"); x2d = _slices(s); v, shp = _volume(s, x2d)
    out["demo_volume_equal_serie"] = bool(torch.equal(v, s.get_volume()))
    arr, mean, calib = _forward(model, v, dev)
    out["demo_scores"] = calib; out["demo_ref"] = DEMO_REF; out["demo_maxdiff"] = max(abs(a - b) for a, b in zip(calib, DEMO_REF))
    out["demo_official_predict"] = [float(x) for x in model.predict([Serie(paths, file_type="dicom")]).scores[0]]
    out["demo_pass"] = out["demo_maxdiff"] <= 0.005
    json.dump(out, open("/vol/l2/run_info/smoke.json", "w"), indent=1, default=str); vol.commit()
    if out["demo_pass"] and n_series:
        out["bench"] = _score_rows(_rows("D1", 0, n_series, 0, 1), "dev", zfix_max, "smoke", t0, 12 * 60, verify=True, model=model)
    out["container_min"] = (time.time() - t0) / 60
    json.dump(out, open("/vol/l2/run_info/smoke.json", "w"), indent=1, default=str); vol.commit()
    return out


def _run(tier, lo, hi, shard, nshard, limit_min, zfix_max, root, verify):
    t0 = time.time(); vol.reload()
    out = _score_rows(_rows(tier, lo, hi, shard, nshard), root, zfix_max, f"{root}:{tier}[{lo}:{hi}] s{shard}", t0, limit_min * 60, verify=verify)
    out.update(tier=tier, lo=lo, hi=hi, shard=shard, nshard=nshard, root=root, zfix_max=zfix_max, container_min=(time.time() - t0) / 60)
    return out


@app.function(gpu="T4", cpu=CPU, memory=MEM_GIB * 1024, timeout=60 * 60, retries=0, volumes={"/vol": vol})
def run_shard(tier: str, lo: int, hi: int, shard: int, nshard: int, limit_min: float, zfix_max: float, root: str, verify: bool = False):
    return _run(tier, lo, hi, shard, nshard, limit_min, zfix_max, root, verify)


@app.function(gpu="L4", cpu=CPU, memory=MEM_GIB * 1024, timeout=60 * 60, retries=0, volumes={"/vol": vol})
def run_shard_l4(tier: str, lo: int, hi: int, shard: int, nshard: int, limit_min: float, zfix_max: float, root: str, verify: bool = False):
    return _run(tier, lo, hi, shard, nshard, limit_min, zfix_max, root, verify)


@app.function(cpu=1, memory=2048, timeout=10 * 60, retries=0, volumes={"/vol": vol})
def count(root: str = "dev"):
    """files on the volume per variant (json = done), errors."""
    import glob
    t0 = time.time(); vol.reload(); out = {}
    for d in sorted(glob.glob(f"/vol/l2/{root}/*")):
        out[d.split("/")[-1]] = dict(json=len(glob.glob(d + "/*.json")), npz=len(glob.glob(d + "/*.npz")))
    out["container_min"] = (time.time() - t0) / 60
    return out


@app.local_entrypoint()
def main(step: str = "smoke", tier: str = "D1", lo: int = 0, hi: int = 100000, nshard: int = 4, timeout_min: int = 60,
         zfix_max: float = 0.65, root: str = "dev", n_series: int = 3, verify: bool = False):
    """the account is modal run's own --profile option (amendment A4); it is required, checked, sent to the guard and stored per run.
    On accounts other than shforghani2002 the result file gets the suffix __<profile>, so it never overwrites the main account's record."""
    sys.path.insert(0, str(Path(__file__).resolve().parent)); import launch as LN
    profile = LN.client_profile(); sfx = "" if profile == "shforghani2002" else f"__{profile}"
    assert timeout_min <= 60 and nshard <= 4, "protocol: timeout <= 60 min, <= 4 containers"
    if step == "smoke": LN.launch(smoke, TASK, APP, "smoke", 20, "T4", CPU, MEM_GIB, args=(n_series, zfix_max), result_name="smoke" + sfx, profile=profile)
    elif step in ("run", "run_l4"):
        fn, gpu = (run_shard, "T4") if step == "run" else (run_shard_l4, "L4")
        name = f"{step}_{root}_{tier}_{lo}_{hi}"
        # the soft stop is timeout_min - 5; the guard's worst case uses the function's hard timeout (60 min), so it is a true bound
        LN.launch_many(fn, [(tier, lo, hi, s, nshard, timeout_min - 5.0, zfix_max, root, verify) for s in range(nshard)], TASK, APP, name,
                       60, gpu, CPU, MEM_GIB, result_name=name + sfx, profile=profile)
    elif step == "count": LN.launch(count, TASK, APP, f"count_{root}", 10, None, 1, 2, args=(root,), result_name=f"count_{root}" + sfx, profile=profile)
