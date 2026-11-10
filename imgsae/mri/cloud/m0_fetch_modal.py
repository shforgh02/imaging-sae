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
CPU, MEM_GIB, TIMEOUT_MIN, IMAGE_USD = 4, 8, 90, 0.10   # 90 min: relaunch after mri_fetch-010 (cancelled), fits the $0.80 cap
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
        """resumable download: continue a .part file with an HTTP Range request (restart from 0 if the server ignores it); the volume is
        committed about every GB so progress survives a killed container; the MD5 is computed over the whole file at the end."""
        dst = f"{zdir}/{f['key']}"; part = dst + ".part"
        if f["key"] in man and man[f["key"]]["md5"] == f["md5"] and os.path.exists(dst) and os.path.getsize(dst) == f["size"]:
            return f["key"], "skipped"
        for attempt in range(4):
            try:
                start = os.path.getsize(part) if os.path.exists(part) else 0
                if start > f["size"]: os.remove(part); start = 0
                hdr = dict(H, **({"Range": f"bytes={start}-"} if 0 < start < f["size"] else {})); t = time.time(); got = 0; since = 0
                if start < f["size"]:
                    with requests.get(f["url"], headers=hdr, stream=True, timeout=300) as r:
                        r.raise_for_status()
                        if start and r.status_code != 206: start = 0   # server ignored the range: restart
                        with open(part, "ab" if start else "wb") as out:
                            for b in r.iter_content(1 << 22):
                                out.write(b); got += len(b); since += len(b)
                                if since >= 1 << 30:
                                    out.flush(); since = 0
                                    with lock: vol.commit()
                n = os.path.getsize(part)
                if n != f["size"]: raise IOError(f"size {n} != {f['size']} (resumed from {start})")
                md5 = md5_of(part)
                if md5 != f["md5"]: os.remove(part); raise IOError(f"MD5 mismatch {md5} (file removed, restarting from 0)")
                os.replace(part, dst)
                with lock:
                    man[f["key"]] = dict(md5=md5, size=n, resumed_from=start, seconds=round(time.time() - t, 1))
                    json.dump(man, open(mpath, "w"), indent=1); vol.commit()
                print(f"  {f['key']}: {n / 1e9:.2f} GB (resumed from {start / 1e9:.2f}), {got / max(time.time() - t, 1) / 1e6:.1f} MB/s, MD5 ok", flush=True)
                return f["key"], "ok"
            except Exception as e:
                print(f"  {f['key']}: attempt {attempt + 1} failed: {e!r}", flush=True)
                with lock: vol.commit()
        return f["key"], "FAILED"

    with ThreadPoolExecutor(len(files)) as ex: status = dict(ex.map(get, files))
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
    sys.path.insert(0, str(Path(__file__).resolve().parent)); import launch as LN
    LN.launch(fetch, TASK, APP, "fetch", TIMEOUT_MIN, None, CPU, MEM_GIB, result_name="m0_fetch")
