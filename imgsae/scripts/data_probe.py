"""Data-source probes for TotalSegmentator v2 (lean plan Phase 1 D1).
usage: python scripts/data_probe.py hf REPO | zenodo_cd | speed URL
  hf REPO     list files/sizes of a Hugging Face dataset mirror
  zenodo_cd   read the central directory of the Zenodo zip through HTTP ranges -> data/totalseg_zip_index.csv (name, size, crc32, offset)
  speed URL   time a 20 MB range read
"""
import csv
import io
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ZEN = "https://zenodo.org/api/records/10047292/files/Totalsegmentator_dataset_v201.zip/content"
ROOT = Path(__file__).resolve().parents[1]


class HTTPRangeFile(io.RawIOBase):
    """seekable read-only file over HTTP range requests (for zipfile)."""

    def __init__(self, url):
        self.url = url; self.pos = 0
        req = urllib.request.Request(url, method="HEAD"); r = urllib.request.urlopen(req); self.url = r.geturl(); self.size = int(r.headers["Content-Length"])

    def seekable(self): return True

    def readable(self): return True

    def tell(self): return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else (self.pos + off if whence == 1 else self.size + off); return self.pos

    def read(self, n=-1):
        if n is None or n < 0: n = self.size - self.pos
        if n == 0 or self.pos >= self.size: return b""
        end = min(self.size, self.pos + n) - 1; req = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{end}"})
        for attempt in range(8):
            try:
                data = urllib.request.urlopen(req, timeout=120).read(); break
            except Exception:
                time.sleep(5 * (attempt + 1))
        else: raise IOError("range read failed")
        self.pos += len(data); return data

    def readinto(self, b):
        d = self.read(len(b)); b[:len(d)] = d; return len(d)


def hf(repo):
    from huggingface_hub import HfApi
    info = HfApi().dataset_info(repo, files_metadata=True); fs = info.siblings
    print(len(fs), "files", round(sum((f.size or 0) for f in fs) / 1e9, 2), "GB")
    for f in fs[:15]: print(f.rfilename, f.size)


def zenodo_cd():
    f = HTTPRangeFile(ZEN); print("zip size GB", round(f.size / 1e9, 2), "url", f.url[:80])
    z = zipfile.ZipFile(io.BufferedReader(f, buffer_size=1 << 20)); out = ROOT / "data" / "totalseg_zip_index.csv"; out.parent.mkdir(exist_ok=True)
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["name", "file_size", "compress_size", "crc32", "header_offset"])
        for i in z.infolist(): w.writerow([i.filename, i.file_size, i.compress_size, f"{i.CRC:08x}", i.header_offset])
    print("members", len(z.infolist()), "->", out)


def speed(url):
    t = time.time(); req = urllib.request.Request(url, headers={"Range": "bytes=0-20971519"}); n = len(urllib.request.urlopen(req, timeout=300).read())
    dt = time.time() - t; print(f"{n / 1e6:.1f} MB in {dt:.1f} s = {n / 1e6 / dt:.2f} MB/s")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "hf": hf(sys.argv[2])
    elif cmd == "zenodo_cd": zenodo_cd()
    elif cmd == "speed": speed(sys.argv[2])
