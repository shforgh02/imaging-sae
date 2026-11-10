"""M0.2 (docs/MRI_M0M1_PROTOCOL.md section 2): fetch PI-CAI images (Zenodo 6624726, MD5-checked) and labels (picai_labels at the pinned
commit, SHA256 recorded) into the Modal volume imgsae-picai. No image is opened: zip central directories are read only to index names.
Each finished file is committed to the volume at once; a file already present with the right checksum is skipped (resumable).
Budget: task mri_fetch (ledger p1b_sanity/cloud/ledger.json); budget.py checks task, project and month before launch.
usage (miniconda modal client, from D:\\Shayan):
  C:\\Users\\Arman\\miniconda3\\Scripts\\modal.exe run --detach imgsae/mri/cloud/m0_fetch_modal.py
"""
import json
import sys
import time
from pathlib import Path

import modal

TASK, APP, VOL = "mri_fetch", "imgsae-mri-m0-fetch", "imgsae-picai"
CPU, MEM_GIB, TIMEOUT_MIN, IMAGE_USD = 4, 8, 120, 0.10
RECORD = "6624726"
COMMIT = "ce4a4723d7c46d882a6cbaacb40ed6c4be86282f"
MARKSHEET_SHA = "23eab23790886258440b4af2842733332003f2c59f0a007b1e7b6b44572cf0ae"
LOCAL = modal.is_local()
ROOT = Path(__file__).resolve().parents[3] if LOCAL else Path("/x")

image = modal.Image.debian_slim(python_version="3.11").pip_install("requests==2.32.3")
app = modal.App(APP, image=image)
vol = modal.Volume.from_name(VOL, create_if_missing=True)


@app.function(cpu=CPU, memory=MEM_GIB * 1024, timeout=TIMEOUT_MIN * 60, retries=0, volumes={"/vol": vol})
def fetch():
    import hashlib
    import os
    import re
    import threading
    import zipfile
    from concurrent.futures import ThreadPoolExecutor

    import requests
    t0 = time.time(); lock = threading.Lock(); H = {"User-Agent": "imgsae-m0-fetch"}
    zdir = "/vol/raw/zenodo"; os.makedirs(zdir, exist_ok=True); mpath = f"{zdir}/manifest.json"
    rec = requests.get(f"https://zenodo.org/api/records/{RECORD}", headers=H, timeout=120).json()
    files = [dict(key=f["key"], size=int(f["size"]), md5=f["checksum"].split(":", 1)[1], url=f["links"]["self"]) for f in rec["files"]]
    meta = dict(record=RECORD, title=rec["metadata"].get("title"), version=rec["metadata"].get("version"),
                license=rec["metadata"].get("license"), doi=rec.get("doi"), files=[{k: f[k] for k in ("key", "size", "md5")} for f in files])
    man = json.load(open(mpath)) if os.path.exists(mpath) else {}
    print(f"record {RECORD} v{meta['version']}: {len(files)} files, {sum(f['size'] for f in files) / 1e9:.2f} GB; already done: {sorted(man)}", flush=True)

    def md5_of(path):
        h = hashlib.md5()
        with open(path, "rb") as fh:
            for b in iter(lambda: fh.read(1 << 24), b""): h.update(b)
        return h.hexdigest()

    def get(f):
        dst = f"{zdir}/{f['key']}"
        if f["key"] in man and man[f["key"]]["md5"] == f["md5"] and os.path.exists(dst) and os.path.getsize(dst) == f["size"]:
            return f["key"], "skipped"
        for attempt in range(3):
            try:
                h = hashlib.md5(); n = 0; t = time.time()
                with requests.get(f["url"], headers=H, stream=True, timeout=300) as r, open(dst + ".part", "wb") as out:
                    r.raise_for_status()
                    for b in r.iter_content(1 << 22):
                        out.write(b); h.update(b); n += len(b)
                if h.hexdigest() != f["md5"] or n != f["size"]: raise IOError(f"checksum/size mismatch {h.hexdigest()} {n}")
                os.replace(dst + ".part", dst)
                with lock:
                    man[f["key"]] = dict(md5=f["md5"], size=n, seconds=round(time.time() - t, 1))
                    json.dump(man, open(mpath, "w"), indent=1); vol.commit()
                print(f"  {f['key']}: {n / 1e9:.2f} GB in {time.time() - t:.0f} s, MD5 ok", flush=True); return f["key"], "ok"
            except Exception as e:  # retry from scratch; the .part file is overwritten
                print(f"  {f['key']}: attempt {attempt + 1} failed: {e!r}", flush=True)
        return f["key"], "FAILED"

    with ThreadPoolExecutor(3) as ex: status = dict(ex.map(get, files))
    json.dump(meta, open(f"{zdir}/record.json", "w"), indent=1)

    # labels at the pinned commit
    lzip = f"/vol/raw/picai_labels_{COMMIT[:7]}.zip"
    if not os.path.exists(lzip):
        r = requests.get(f"https://codeload.github.com/DIAGNijmegen/picai_labels/zip/{COMMIT}", headers=H, timeout=600); r.raise_for_status()
        open(lzip, "wb").write(r.content)
    lsha = hashlib.sha256(open(lzip, "rb").read()).hexdigest()
    ldir = "/vol/raw/labels"
    if not os.path.exists(f"{ldir}/.extracted"):
        with zipfile.ZipFile(lzip) as z: z.extractall(ldir)
        open(f"{ldir}/.extracted", "w").write(lsha)
    roots = [d for d in os.listdir(ldir) if d.startswith("picai_labels")]; lroot = f"{ldir}/{roots[0]}" if roots else ldir
    msha = hashlib.sha256(open(f"{lroot}/clinical_information/marksheet.csv", "rb").read()).hexdigest()
    vol.commit()

    # index (names only) of image members
    idx = {}; pat = re.compile(r"(\d{5})_(\d{7})_(t2w|adc|hbv|sag|cor)\.mha$")
    for f in files:
        if not f["key"].endswith(".zip") or status.get(f["key"]) == "FAILED": continue
        with zipfile.ZipFile(f"{zdir}/{f['key']}") as z:
            for name in z.namelist():
                m = pat.search(name)
                if m: idx.setdefault(f"{m.group(1)}_{m.group(2)}", {})[m.group(3)] = [f["key"], name]
    json.dump(idx, open(f"{zdir}/index.json", "w")); vol.commit()
    complete = sum(all(s in v for s in ("t2w", "adc", "hbv")) for v in idx.values())
    out = dict(status=status, n_studies_indexed=len(idx), n_complete_t2w_adc_hbv=complete, labels_zip_sha256=lsha, labels_root=lroot,
               marksheet_sha256_ok=(msha == MARKSHEET_SHA), record=meta, container_min=(time.time() - t0) / 60)
    json.dump(out, open("/vol/raw/fetch_summary.json", "w"), indent=1); vol.commit()
    print(json.dumps({k: v for k, v in out.items() if k != "record"}, indent=1), flush=True)
    return out


@app.local_entrypoint()
def main():
    sys.path.insert(0, str(ROOT / "imgsae" / "exploratory" / "p1b_sanity" / "cloud")); import budget as B
    worst = B.worst_case(1, TIMEOUT_MIN, None, CPU, MEM_GIB) + IMAGE_USD; rate = B.rate_h(None, CPU, MEM_GIB)
    ok, rep = B.check(TASK, worst); print(json.dumps(rep, indent=1))
    if not ok: raise SystemExit(f"BUDGET CHECK FAILED - not launching (worst case ${worst:.2f})")
    rid = B.open_run(TASK, worst, dict(app=APP, jobs=["fetch"], timeout_min=TIMEOUT_MIN, gpu=None, cpu=CPU, mem_gib=MEM_GIB))
    print(f"launch {rid}: worst case ${worst:.2f}"); measured, note = IMAGE_USD, "unfinished"
    try:
        out = fetch.remote(); measured += (out["container_min"] + B.START_MIN) / 60 * rate
        note = f"status {out['status']}; indexed {out['n_studies_indexed']}, complete {out['n_complete_t2w_adc_hbv']}; marksheet ok {out['marksheet_sha256_ok']}"
        (ROOT / "imgsae" / "mri" / "results").mkdir(parents=True, exist_ok=True)
        json.dump(out, open(ROOT / "imgsae" / "mri" / "results" / "m0_fetch.json", "w"), indent=1)
    except BaseException as e:
        measured += (TIMEOUT_MIN + B.START_MIN) / 60 * rate; note = f"failed or client lost: {e!r}"[:300]; raise
    finally:
        B.close_run(rid, measured, note); print(f"closed {rid}: ${measured:.2f} ({note})")
