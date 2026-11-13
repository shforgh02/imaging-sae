"""Lung L1 (docs/LUNG_L1_PROTOCOL.md): Sybil on the 6,715 test series of its own NLST split. Task lung_l1_sybil, app imgsae-lung-l1, volume imgsae-nlst-l1.
usage (from D:\\Shayan, miniconda python, PYTHONUTF8=1):
  modal run --detach imgsae/exploratory/lung_l1/cloud/l1_sybil_modal.py --step s1       (CPU: manifest + IDC join)
  ... --step smoke                                                                       (GPU: demo case + 20 series)
  ... --step run --tier P1 --lo 0 --hi 1700 --nshard 4                                   (GPU: shard of a tier)
  ... --step export                                                                      (CPU: gather scores)
Every finished series is one JSON file on the volume (/vol/scores/<uid>.json); the volume is committed every 25 series; no DICOM is kept.
"""
import json
import sys
import time
from pathlib import Path

import modal

TASK, APP, VOL = "lung_l1_sybil", "imgsae-lung-l1", "imgsae-nlst-l1"
GPU, CPU, MEM_GIB = "T4", 4, 16
SYBIL_COMMIT = "d9fc81b93c1c6239a570c1c570c1f2a2e6266a4a"
DEMO_URL = "https://www.dropbox.com/scl/fi/covbvo6f547kak4em3cjd/sybil_example.zip?rlkey=7a13nhlc9uwga9x7pmtk1cf1c&dl=1"
DEMO_REF = [0.021628819563619374, 0.03857256315036462, 0.07191945816622261, 0.07926975188037134, 0.09584583525781108, 0.13568094038444453]
LOCAL = modal.is_local()
L1 = Path(__file__).resolve().parents[1] if LOCAL else Path("/root/l1")
REMOTE = "/root/l1"

image = (modal.Image.debian_slim(python_version="3.10")
         .apt_install("git", "unzip", "wget", "libgl1", "libglib2.0-0")
         .pip_install("torch==1.13.1", "torchvision==0.14.1", "numpy==1.24.1", "imageio==2.34.1", "opencv-python==4.5.4.60", "opencv-python-headless==4.5.4.60",
                      "pillow>=10.2.0", "pydicom==2.3.0", "pylibjpeg[all]==2.0.0", "torchio==0.18.74", "tqdm==4.62.3", "idc-index", "pandas", "importlib-metadata")
         .pip_install(f"git+https://github.com/reginabarzilaygroup/Sybil.git@{SYBIL_COMMIT}", extra_options="--no-deps")   # setup.cfg pins torch==1.13.1+cu117, absent from the mirror; PyPI 1.13.1 wheel bundles CUDA 11.7
         .run_commands("python -c \"from sybil import Sybil; Sybil('sybil_ensemble')\"")   # checkpoints into /root/.sybil at build time
         .env({"PYTHONUNBUFFERED": "1"})
         .add_local_file(L1 / "results" / "manifest_series.csv", f"{REMOTE}/manifest_series.csv"))
app = modal.App(APP, image=image)
vol = modal.Volume.from_name(VOL, create_if_missing=True)


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


@app.function(cpu=2, memory=8 * 1024, timeout=15 * 60, retries=0, volumes={"/vol": vol})
def s1_index():
    """S1: join the manifest with the IDC index; write /vol/manifest.csv (series_uid,pid,cancer_in_1,study_yr,tier,order,size_mb)."""
    import random

    import pandas as pd
    from idc_index import IDCClient
    t0 = time.time(); vol.reload(); c = IDCClient(); ix = c.index; cols = list(ix.columns)
    m = pd.read_csv(f"{REMOTE}/manifest_series.csv", dtype={"pid": str})
    sub = ix[ix.SeriesInstanceUID.isin(set(m.series_uid))]
    j = m.merge(sub, left_on="series_uid", right_on="SeriesInstanceUID", how="left")
    found = j.SeriesInstanceUID.notna()
    j["yr"] = pd.to_datetime(j.StudyDate, errors="coerce").dt.year
    j["study_yr"] = j.yr - 1999
    res = dict(n_manifest=len(m), n_found=int(found.sum()), frac_found=float(found.mean()), index_columns=cols,
               collections_found=j.collection_id.value_counts(dropna=False).to_dict() if "collection_id" in j else None,
               study_yr_counts={str(k): int(v) for k, v in j.study_yr.value_counts(dropna=False).items()},
               pid_match=int((j.PatientID.astype(str) == j.pid.astype(str)).sum()),
               dup_pid_year=int(j[found].duplicated(["pid", "study_yr"]).sum()),
               size_mb_total=float(j.series_size_MB.sum()) if "series_size_MB" in j else None,
               size_mb_mean=float(j.series_size_MB.mean()) if "series_size_MB" in j else None)
    ok = j[found & j.study_yr.isin([0, 1, 2])].copy(); ok["study_yr"] = ok.study_yr.astype(int)
    res["n_usable"] = len(ok)
    P2 = sorted(ok[ok.study_yr > 0].pid.unique()); random.Random(0).shuffle(P2); rank = {p: i for i, p in enumerate(P2)}
    ok["tier"] = ok.study_yr.map(lambda y: "P1" if y == 0 else "P2")
    ok["order"] = [rank.get(p, -1) if t == "P2" else 0 for p, t in zip(ok.pid, ok.tier)]
    ok = ok.sort_values(["tier", "order", "study_yr", "series_uid"]).reset_index(drop=True)
    ok[["series_uid", "pid", "cancer_in_1", "study_yr", "tier", "order"] + (["series_size_MB"] if "series_size_MB" in ok else [])].to_csv("/vol/manifest.csv", index=False)
    res["tier_counts"] = ok.tier.value_counts().to_dict(); res["n_p2_participants"] = len(P2)
    res["sample_row"] = {k: str(v) for k, v in j[found].iloc[0].to_dict().items()}
    res["container_min"] = (time.time() - t0) / 60
    json.dump(res, open("/vol/s1_result.json", "w"), indent=1, default=str); vol.commit()
    return res


_S5 = {}


def _init_idc(uids):
    """once per process, in the main thread: series address map from the IDC index + the s5cmd binary path.
    (idc-index's own download_from_selection hangs when two calls run in threads, shown by dl_test on 2026-11-12, so s5cmd is called directly.)"""
    import shutil

    from idc_index import IDCClient
    c = IDCClient(); ix = c.index; sub = ix[ix.SeriesInstanceUID.isin(set(uids))]
    _S5["urls"] = dict(zip(sub.SeriesInstanceUID, sub.series_aws_url)); _S5["bin"] = getattr(c, "s5cmdPath", None) or shutil.which("s5cmd")
    print(f"s5cmd={_S5['bin']} urls={len(_S5['urls'])}", flush=True)


def _download(uid, d):
    """download one series (IDC public bucket, no credentials) into d with s5cmd; returns the list of file paths."""
    import glob
    import os
    import subprocess
    r = subprocess.run([_S5["bin"], "--no-sign-request", "--endpoint-url", "https://s3.amazonaws.com", "cp", _S5["urls"][uid], d + "/"],
                       capture_output=True, text=True, timeout=300)
    if r.returncode: raise RuntimeError(f"s5cmd rc={r.returncode}: {r.stderr[-300:]}")
    return sorted(p for p in glob.glob(os.path.join(d, "**", "*"), recursive=True) if os.path.isfile(p))


def _score_list(rows, model, tag, t0, limit_s):
    """rows: list of (uid,pid,study_yr). Saves /vol/scores/<uid>.json per series; prefetches the next downloads in threads."""
    import os
    import shutil
    import tempfile
    from concurrent.futures import ThreadPoolExecutor

    from sybil import Serie
    os.makedirs("/vol/scores", exist_ok=True); os.makedirs("/vol/errors", exist_ok=True)
    todo = [r for r in rows if not os.path.exists(f"/vol/scores/{r[0]}.json")]
    _init_idc([r[0] for r in todo])   # always rebuild: a reused container must not keep the previous call's address map (KeyError seen on 2026-11-12)
    done, errs, T = 0, {}, dict(download=[], load=[], infer=[])
    base = tempfile.mkdtemp(prefix="l1_")

    def fetch(r):
        d = os.path.join(base, r[0]); os.makedirs(d, exist_ok=True); ts = time.time()
        try:
            paths = _download(r[0], d); tdl = time.time() - ts; t1 = time.time()
            s = Serie(paths, file_type="dicom"); s.get_volume()   # loading (CPU) runs here, in the prefetch thread, while the GPU scores the previous series
            return r, paths, tdl, None, s, time.time() - t1
        except Exception as e: return r, None, time.time() - ts, f"{type(e).__name__}: {e}"[:500], None, 0.0
    ex = ThreadPoolExecutor(2); fut = [ex.submit(fetch, r) for r in todo[:3]]; nxt = 3
    for n in range(len(todo)):
        r, paths, tdl, err, s, tload = fut[n].result(); fut[n] = None   # drop the reference so the loaded volume can be freed
        if nxt < len(todo): fut.append(ex.submit(fetch, todo[nxt])); nxt += 1
        uid, pid, yr = r; d = os.path.join(base, uid)
        try:
            if err: raise RuntimeError(err)
            t2 = time.time(); sc = model.predict([s]).scores[0]; t3 = time.time()
            rec = dict(series_uid=uid, pid=pid, study_yr=yr, **{f"y{k + 1}": float(sc[k]) for k in range(6)}, n_slices=len(paths),
                       sec_download=tdl, sec_load=tload, sec_infer=t3 - t2)
            json.dump(rec, open(f"/vol/scores/{uid}.json", "w")); done += 1
            T["download"].append(tdl); T["load"].append(tload); T["infer"].append(t3 - t2)
        except Exception as e:
            errs[uid] = f"{type(e).__name__}: {e}"[:500]; json.dump(dict(series_uid=uid, error=errs[uid]), open(f"/vol/errors/{uid}.json", "w"))
        shutil.rmtree(d, ignore_errors=True)
        if (n + 1) % 25 == 0: vol.commit(); print(f"{tag}: {n + 1}/{len(todo)} errs={len(errs)} {(time.time() - t0) / 60:.1f} min", flush=True)
        if time.time() - t0 > limit_s: print("time limit reached, stopping cleanly", flush=True); break
    vol.commit(); ex.shutdown(wait=False, cancel_futures=True); shutil.rmtree(base, ignore_errors=True)
    mean = {k: (sum(v) / len(v) if v else None) for k, v in T.items()}
    return dict(n_todo=len(todo), n_done=done, errors=errs, mean_sec=mean, n_attempted=done + len(errs))


def _model():
    import torch
    from sybil import Sybil
    return Sybil("sybil_ensemble", device="cuda" if torch.cuda.is_available() else "cpu")


@app.function(gpu=GPU, cpu=CPU, memory=MEM_GIB * 1024, timeout=12 * 60, retries=0, volumes={"/vol": vol})
def smoke(n_series: int = 0):
    """S2: (a) the published demo case, (b) n_series test series (seeded random pick from the manifest); the scored series stay on the volume."""
    import glob
    import os
    import subprocess

    import numpy as np
    import pandas as pd
    import torch
    t0 = time.time(); vol.reload(); out = dict(gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)
    def P(m):
        import resource
        print(f"[smoke {time.time() - t0:.0f}s rss={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6:.2f}GB] {m}", flush=True)
    P("start"); model = _model(); P("model loaded"); out["ckpt_sha256"] = _ckpt_hashes(); P("hashes done")
    os.makedirs("/tmp/demo", exist_ok=True)
    subprocess.run(["wget", "-q", "-T", "60", "-t", "2", "-O", "/tmp/demo/d.zip", DEMO_URL], check=True, timeout=180); P("zip downloaded")
    subprocess.run(["unzip", "-q", "-o", "/tmp/demo/d.zip", "-d", "/tmp/demo/x"], check=True, timeout=120); P("unzipped")
    from sybil import Serie
    allf = sorted(p for p in glob.glob("/tmp/demo/x/**/*", recursive=True) if os.path.isfile(p)); out["demo_all_files_head"] = allf[:5]; out["demo_all_files_n"] = len(allf)
    import pydicom
    paths = []
    for p in allf:
        try: pydicom.dcmread(p, stop_before_pixels=True); paths.append(p)
        except Exception: pass
    P(f"{len(paths)} dicom files of {len(allf)}"); out["demo_n_files"] = len(paths); sc = model.predict([Serie(paths, file_type="dicom")]).scores[0]
    P("predicted"); out["demo_scores"] = [float(x) for x in sc]; out["demo_ref"] = DEMO_REF; out["demo_maxdiff"] = float(max(abs(a - b) for a, b in zip(sc, DEMO_REF)))
    out["demo_pass"] = out["demo_maxdiff"] <= 0.005
    if out["demo_pass"] and n_series:
        m = pd.read_csv("/vol/manifest.csv", dtype={"pid": str}); m = m[m.tier == "P1"]
        pick = m.sample(n_series, random_state=0)
        out["bench"] = _score_list(list(zip(pick.series_uid, pick.pid, pick.study_yr)), model, "smoke", t0, 20 * 60)
    out["container_min"] = (time.time() - t0) / 60
    return out


@app.function(cpu=2, memory=8 * 1024, timeout=8 * 60, retries=0, volumes={"/vol": vol})
def dl_test():
    """diagnosis: time IDC downloads (one, then two at once in threads)."""
    import os
    import shutil
    from concurrent.futures import ThreadPoolExecutor

    import pandas as pd
    t0 = time.time(); vol.reload(); m = pd.read_csv("/vol/manifest.csv", dtype={"pid": str}); m = m[m.tier == "P1"].sample(3, random_state=1); u = list(m.series_uid)
    out = {}; _init_idc(u); out["s5"] = _S5["bin"]

    def one(i):
        d = f"/tmp/dl{i}"; os.makedirs(d, exist_ok=True); ts = time.time(); print(f"dl {i} start {ts - t0:.0f}s", flush=True)
        fs = _download(u[i], d); n = sum(os.path.getsize(p) for p in fs); out[f"dl{i}"] = dict(sec=time.time() - ts, n_files=len(fs), mb=n / 1e6)
        print(f"dl {i} done {out[f'dl{i}']}", flush=True); shutil.rmtree(d, ignore_errors=True)
    one(0)
    with ThreadPoolExecutor(2) as ex: list(ex.map(one, [1, 2]))
    out["container_min"] = (time.time() - t0) / 60
    return out


@app.function(gpu=GPU, cpu=CPU, memory=MEM_GIB * 1024, timeout=60 * 60, retries=0, volumes={"/vol": vol})
def run_shard(tier: str, lo: int, hi: int, shard: int, nshard: int, limit_min: float = 55.0):
    import pandas as pd
    t0 = time.time(); vol.reload()
    m = pd.read_csv("/vol/manifest.csv", dtype={"pid": str}); m = m[m.tier == tier].reset_index(drop=True).iloc[lo:hi]
    m = m.iloc[shard::nshard]
    model = _model()
    out = _score_list(list(zip(m.series_uid, m.pid, m.study_yr)), model, f"{tier}[{lo}:{hi}] s{shard}", t0, limit_min * 60)
    out.update(tier=tier, lo=lo, hi=hi, shard=shard, nshard=nshard, container_min=(time.time() - t0) / 60)
    return out


@app.function(cpu=1, memory=2048, timeout=10 * 60, retries=0, volumes={"/vol": vol})
def export():
    """S4: gather every score file into scores.csv text (+ counts)."""
    import glob

    import pandas as pd
    t0 = time.time(); vol.reload()
    rows = [json.load(open(f)) for f in sorted(glob.glob("/vol/scores/*.json"))]
    errs = {json.load(open(f))["series_uid"]: json.load(open(f))["error"] for f in glob.glob("/vol/errors/*.json")}
    df = pd.DataFrame(rows)
    csv = df[["series_uid", "pid", "study_yr"] + [f"y{k}" for k in range(1, 7)]].to_csv(index=False)
    tim = {k: float(df[k].mean()) for k in ("sec_download", "sec_load", "sec_infer", "n_slices")}
    return dict(n=len(df), csv=csv, errors=errs, mean=tim, by_yr={str(k): int(v) for k, v in df.study_yr.value_counts().items()}, container_min=(time.time() - t0) / 60)


@app.local_entrypoint()
def main(step: str = "s1", tier: str = "P1", lo: int = 0, hi: int = 100000, nshard: int = 4, timeout_min: int = 60, n_series: int = 0):
    sys.path.insert(0, str(Path(__file__).resolve().parent)); import launch as LN
    if step == "s1": LN.launch(s1_index, TASK, APP, "s1_index", 15, None, 2, 8, result_name="s1_index")
    elif step == "smoke": LN.launch(smoke, TASK, APP, "smoke", 12, GPU, CPU, MEM_GIB, args=(n_series,), result_name="smoke")
    elif step == "run":
        name = f"run_{tier}_{lo}_{hi}"
        LN.launch_many(run_shard, [(tier, lo, hi, s, nshard, timeout_min - 5.0) for s in range(nshard)], TASK, APP, name, timeout_min, GPU, CPU, MEM_GIB, result_name=name)
    elif step == "dl_test": LN.launch(dl_test, TASK, APP, "dl_test", 8, None, 2, 8, result_name="dl_test")
    elif step == "export": LN.launch(export, TASK, APP, "export", 10, None, 1, 2, result_name="export")





