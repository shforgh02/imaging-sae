"""Phase 1 driver (lean plan v1): runs every step in order, skipping steps already done (markers in data/p1/steps/).
Launch on the Windows laptop (checks the GPU is free, sets 4 threads, runs detached, logs to logs/phase1.log):
  powershell -File scripts/run_phase1.ps1          (status: scripts/run_phase1.ps1 -Status)
Original Mac launch: ~/.claude/tools/prun imgsae_p1 ... ".venv/bin/python scripts/run_phase1.py".
Every step runs with this interpreter (sys.executable) and auto device (cuda > mps > cpu); see docs/EXECUTION_LOG.md for the port.
Steps: fetch (resume, CRC-verified) -> tests -> engineering gate (spacing rule) -> encode 150 dev scans (CT-FM + random-init null) -> assemble ->
probes (gate S) -> perturbation re-encodes (20 scans x shift/noise/huoff) -> fits + ladder (J = 3) -> decision memo.
Spacing rule (fixed now): engineering on 2 scans at 1.0 mm; use 1.0 mm (16 mm tokens) if 150 x 2 encoders x mean seconds x 1.3 <= 16 h and the
partial gate passes; otherwise 1.5 mm native (24 mm tokens), with the gate re-run on 5 scans at 1.5 mm. Stops with 'STOP gate E' if both fail.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; PY = sys.executable; ST = ROOT / "data/p1/steps"; LOG = ROOT / "logs"
ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1", **{k: os.environ.get(k, "4") for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")}}


def keep_awake():
    """Windows laptop: block system sleep while this driver runs (released automatically when the process exits)."""
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)  # ES_CONTINUOUS | ES_SYSTEM_REQUIRED


def sh(name, args, log):
    if (ST / f"{name}.done").exists(): print(f"skip {name}", flush=True); return True
    t0 = time.time(); print(f"start {name}: {' '.join(args)}", flush=True)
    with open(LOG / log, "a") as f: rc = subprocess.call(args, stdout=f, stderr=subprocess.STDOUT, cwd=ROOT, env=ENV)
    ok = rc == 0 and "DONE" in (LOG / log).read_text(encoding="utf-8", errors="replace")[-4000:]
    print(f"{'done' if ok else 'FAILED'} {name} rc={rc} {(time.time() - t0) / 60:.1f} min", flush=True)
    if ok: (ST / f"{name}.done").write_text(time.ctime())
    return ok


def main():
    ST.mkdir(parents=True, exist_ok=True); LOG.mkdir(exist_ok=True); dev = str(ROOT / "data/p1_dev_ids.txt"); keep_awake()
    print(f"python {PY}  threads {ENV['OMP_NUM_THREADS']}  {time.ctime()}", flush=True)
    if not sh("fetch", [PY, "scripts/fetch_subset.py", "get", dev, "hf", "6"], "fetch_p1_dev.log"): sys.exit("STOP fetch")
    if not (ROOT.parent / "sae-groundtruth" / "saegt").exists() and not (ST / "tests.done").exists():
        sys.exit(f"STOP tests: frozen reference package not found at {ROOT.parent / 'sae-groundtruth'} (needed by tests/test_equivalence.py)")
    if not sh("tests", [PY, "tests/test_equivalence.py"], "test_equivalence.log") or not sh("units", [PY, "tests/test_units.py"], "test_units.log"): sys.exit("STOP tests")
    sp_file = ROOT / "data/p1/spacing.json"
    if not sp_file.exists():
        sh("eng10", [PY, "scripts/p1_d2_engineering.py", "scans", dev, "--n", "2", "--spacing", "1.0"], "p1_d2_eng10.log")
        e = json.load(open(LOG / "p1_d2_engineering_scans.json")) if (LOG / "p1_d2_engineering_scans.json").exists() else {}
        proj_h = 150 * 2 * e.get("mean_seconds", 1e9) * 1.3 / 3600; spacing = 1.0 if (e.get("gate_E_partial") and proj_h <= 16) else 1.5
        if spacing == 1.5:
            (ST / "eng15.done").unlink(missing_ok=True); sh("eng15", [PY, "scripts/p1_d2_engineering.py", "scans", dev, "--n", "5", "--spacing", "1.5"], "p1_d2_eng15.log")
            e = json.load(open(LOG / "p1_d2_engineering_scans.json")); proj_h = 150 * 2 * e.get("mean_seconds", 1e9) * 1.3 / 3600
            if not e.get("gate_E_partial") or proj_h > 24: sys.exit(f"STOP gate E (projected {proj_h:.1f} h); fallback: DINOv3 2D encoder")
        sp_file.parent.mkdir(parents=True, exist_ok=True); json.dump(dict(spacing=spacing, projected_hours=proj_h), open(sp_file, "w")); print(f"spacing {spacing} mm, projected encode {proj_h:.1f} h", flush=True)
    sp = str(json.load(open(sp_file))["spacing"])
    if not sh("encode", [PY, "scripts/p1_encode.py", dev, "--spacing", sp], "p1_encode_dev.log"): sys.exit("STOP encode")
    if not sh("assemble", [PY, "scripts/p1_assemble.py"], "p1_assemble.log"): sys.exit("STOP assemble")
    if not sh("probe", [PY, "scripts/p1_probe.py"], "p1_probe.log"): sys.exit("STOP probe")
    pl = ROOT / "data/p1/perturb_ids.txt"
    if not pl.exists():
        import numpy as np
        C = json.load(open(ROOT / "data/p1/concepts.json")); ids = [s["id"] for s in C["scans"]]; pl.write_text("\n".join(sorted(np.random.default_rng(7).choice(ids, min(20, len(ids)), replace=False))) + "\n")
    for kind in ("shift", "noise", "huoff"):
        if not sh(f"perturb_{kind}", [PY, "scripts/p1_encode.py", str(pl), "--spacing", sp, "--perturb", kind, "--out", str(ROOT / f"data/p1/perturb/{kind}")], f"p1_perturb_{kind}.log"): sys.exit("STOP perturb")
    if not sh("fit", [PY, "scripts/p1_fit.py"], "p1_fit.log"): sys.exit("STOP fit")
    sh("decide", [PY, "scripts/p1_decide.py"], "p1_decide.log"); print("PHASE1 DONE", flush=True)


if __name__ == "__main__":
    main()
