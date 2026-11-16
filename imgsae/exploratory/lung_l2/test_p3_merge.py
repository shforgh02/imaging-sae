"""Rule test of p3_merge.py on fake folders (no real data written): allowed new files are copied and hash-checked; a rerun copies
nothing (no overwrite); an unexpected new file, a differing existing file and an .npz without .json each stop the merge with nothing
copied. usage (venv python): python test_p3_merge.py
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent; PY = sys.executable; res = []


def ok(n, c): res.append(c); print(("PASS " if c else "FAIL ") + n)


def series(d, uid, val=0.0):
    d.mkdir(parents=True, exist_ok=True); np.savez(d / f"{uid}.npz", h=np.full((5, 4), val, np.float32), logit=np.zeros((5, 6), np.float32))
    (d / f"{uid}.json").write_text(json.dumps(dict(series_uid=uid, calib=[val] * 6)))


def merge(T, man):
    p = subprocess.run([PY, str(HERE / "p3_merge.py"), str(T / "src"), str(T / "dst"), str(man), str(T / "rep.json")], capture_output=True, text=True)
    return p.returncode, json.loads((T / "rep.json").read_text())


def main():
    T = Path(tempfile.mkdtemp(prefix="mergetest_"))
    try:
        man = T / "m.csv"; pd.DataFrame(dict(series_uid=["d1a", "d2a", "d3a", "d4a"], tier=["D1", "D2", "D3", "D4"], variant=["main", "main", "main", "pair"],
                                             pid=["1", "2", "3", "4"])).to_csv(man, index=False)
        series(T / "dst" / "dev" / "main", "d1a", 1.0); series(T / "src" / "dev" / "main", "d1a", 1.0)          # existing, equal
        series(T / "src" / "dev" / "main", "d2a", 2.0); series(T / "src" / "dev" / "zfix", "d3a", 3.0); series(T / "src" / "dev" / "pair", "d4a", 4.0)
        code, r = merge(T, man)
        ok("allowed files copied, existing equal file skipped", code == 0 and r["n_to_copy"] == 3 and r["n_skipped_equal"] == 1 and not r["sha256_mismatch"]
           and (T / "dst" / "dev" / "pair" / "d4a.json").exists())
        code, r = merge(T, man); ok("rerun copies nothing (no overwrite)", code == 0 and r["n_to_copy"] == 0 and r["n_skipped_equal"] == 4)
        series(T / "src" / "dev" / "main", "d9x", 9.0); code, r = merge(T, man)
        ok("unexpected new file stops, nothing copied", code == 2 and "d9x" in " ".join(r["stops"]) and not (T / "dst" / "dev" / "main" / "d9x.json").exists())
        for f in (T / "src" / "dev" / "main").glob("d9x.*"): f.unlink()
        series(T / "src" / "dev" / "main", "d1a", 1.5); code, r = merge(T, man); ok("differing existing file stops", code == 2 and "differs" in " ".join(r["stops"]))
        series(T / "src" / "dev" / "main", "d1a", 1.0); (T / "src" / "dev" / "zfix" / "d2a.npz").write_bytes(b"x"); code, r = merge(T, man)
        ok(".npz without .json stops", code == 2 and "without .json" in " ".join(r["stops"]))
    finally:
        shutil.rmtree(T, ignore_errors=True)
    print(f"{sum(res)} of {len(res)} passed"); raise SystemExit(0 if all(res) else 1)


if __name__ == "__main__":
    main()
