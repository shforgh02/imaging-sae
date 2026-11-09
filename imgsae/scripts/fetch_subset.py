"""Selective, verified fetch of TotalSegmentator v2 members from the remote zip (HTTP ranges; no full 23.6 GB download).
usage:
  python scripts/fetch_subset.py index [SRC]          central directory -> data/totalseg_zip_index.csv (+ meta.csv extracted)
  python scripts/fetch_subset.py get LIST.txt [SRC] [N_PAR]   fetch all members of the subjects in LIST (one id per line), CRC32-verified
SRC: zenodo | hf (identical zip, 23,581,218,285 bytes; md5 fe250e5718e0a3b5df4c4ea9d58a62fe on Zenodo). Members are written to
imgsae_data/totalseg/<subject>/...; a member is skipped if it exists with the right CRC. Progress + a DONE line go to stdout.
"""
import csv
import struct
import sys
import time
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data_probe import HTTPRangeFile  # noqa: E402

URLS = {"zenodo": "https://zenodo.org/api/records/10047292/files/Totalsegmentator_dataset_v201.zip/content",
        "hf": "https://huggingface.co/datasets/HajihajihaJimmy/TotalSegmentator_v2/resolve/main/Totalsegmentator_dataset_v201.zip"}
ROOT = Path(__file__).resolve().parents[1]; DATA = ROOT.parent / "imgsae_data" / "totalseg"; IDX = ROOT / "data" / "totalseg_zip_index.csv"


def rng_read(url, start, end, tries=10):
    req = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}"})
    for a in range(tries):
        try: return urllib.request.urlopen(req, timeout=300).read()
        except Exception: time.sleep(5 * (a + 1))
    raise IOError(f"range {start}-{end} failed")


def index(src="hf"):
    import io
    import zipfile
    f = HTTPRangeFile(URLS[src]); z = zipfile.ZipFile(io.BufferedReader(f, buffer_size=1 << 22)); IDX.parent.mkdir(exist_ok=True)
    with open(IDX, "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["name", "file_size", "compress_size", "crc32", "header_offset", "method"])
        for i in z.infolist(): w.writerow([i.filename, i.file_size, i.compress_size, f"{i.CRC:08x}", i.header_offset, i.compress_type])
    meta = [i for i in z.infolist() if i.filename.endswith("meta.csv")]
    for m in meta: (DATA / Path(m.filename).name).parent.mkdir(parents=True, exist_ok=True); (DATA / Path(m.filename).name).write_bytes(z.read(m))
    print("members", len(z.infolist()), "meta", [m.filename for m in meta], "-> DONE", flush=True)


def fetch_member(url, row):
    out = DATA / row["name"]
    if out.exists() and f"{zlib.crc32(out.read_bytes()) & 0xffffffff:08x}" == row["crc32"]: return 0
    off = int(row["header_offset"]); h = rng_read(url, off, off + 29)
    n, e = struct.unpack("<HH", h[26:30]); start = off + 30 + n + e; raw = rng_read(url, start, start + int(row["compress_size"]) - 1)
    data = raw if row["method"] == "0" else zlib.decompress(raw, -15)
    if f"{zlib.crc32(data) & 0xffffffff:08x}" != row["crc32"]: raise IOError(f"CRC mismatch {row['name']}")
    out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(data); return int(row["compress_size"])


def get(list_file, src="hf", n_par=6):
    ids = {l.strip() for l in open(list_file) if l.strip()}; rows = [r for r in csv.DictReader(open(IDX)) if not r["name"].endswith("/")]
    rows = [r for r in rows if len(Path(r["name"]).parts) > 1 and Path(r["name"]).parts[0] in ids]
    tot = sum(int(r["compress_size"]) for r in rows); print(f"{len(ids)} subjects, {len(rows)} members, {tot / 1e9:.2f} GB", flush=True)
    t0 = time.time(); done = 0
    with ThreadPoolExecutor(int(n_par)) as ex:
        for i, b in enumerate(ex.map(lambda r: fetch_member(URLS[src], r), rows)):
            done += b
            if i % 500 == 0: print(f"{i}/{len(rows)} {done / 1e9:.2f} GB {done / 1e6 / max(time.time() - t0, 1):.2f} MB/s", flush=True)
    print(f"DONE {len(rows)} members {done / 1e9:.2f} GB in {(time.time() - t0) / 60:.1f} min", flush=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "index": index(*(a[1:2] or ["hf"]))
    elif a[0] == "get": get(a[1], *(a[2:4]))
