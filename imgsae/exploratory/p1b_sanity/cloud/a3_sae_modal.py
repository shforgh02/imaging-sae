"""A3 --part sae on Modal (one L4 GPU per job), with the same code as the local run: a3_decomp_fair.load_input + fit_eval, common.Ctx and
common.evaluate. One container per (method, replicate). Results are merged into results/a3_sae.json on this PC, which keeps the local
--part sae resumable (it then only adds the sanity block). Method specs come from a3_decomp_fair.sae_methods(), run in the project venv.
Budget: cloud/budget.py checks task, project and month before launch (user rule: stop at $29 total). The timeout per job is the hard bound.
usage (from p1b_sanity/, miniconda modal client):
  $env:P1B_TIMEOUT_MIN = "15"; $env:P1B_MAXC = "1"; C:\\Users\\Arman\\miniconda3\\Scripts\\modal.exe run cloud/a3_sae_modal.py --jobs sae_run:0
  ... --jobs all   (every method x replicates 0-2 not yet in results/a3_sae.json)
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import modal

TASK, APP, VOL = "a3_sae", "imgsae-p1b-a3sae", "imgsae-p1b"
GPU, CPU, MEM_GIB = "L4", 4, 16
TIMEOUT_MIN = int(os.environ.get("P1B_TIMEOUT_MIN", "15")); MAXC = int(os.environ.get("P1B_MAXC", "1"))
IMAGE_USD = 0.10  # allowance for the image build and app start
REMOTE = "/root/imgsae"
LOCAL = modal.is_local()
HERE = Path(__file__).resolve().parent; SAN = HERE.parent if LOCAL else Path("/x/x/x"); ROOT = SAN.parents[1]

image = (modal.Image.debian_slim(python_version="3.11")
         .pip_install("torch==2.10.0", "numpy==2.4.6", "scipy==1.17.1", "scikit-learn==1.9.1", "pandas==3.1.1", "joblib==1.6.0", "threadpoolctl==3.8.0")
         .env({"IMGSAE_P1": "/vol/p1", "PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1", "OMP_NUM_THREADS": str(CPU), "MKL_NUM_THREADS": str(CPU)})
         .add_local_dir(ROOT / "imgsae", f"{REMOTE}/imgsae", ignore=["**/__pycache__/**"])
         .add_local_file(ROOT / "scripts" / "p1_fit.py", f"{REMOTE}/scripts/p1_fit.py")
         .add_local_file(ROOT / "scripts" / "p1_probe.py", f"{REMOTE}/scripts/p1_probe.py")
         .add_local_file(ROOT / "scripts" / "p1_assemble.py", f"{REMOTE}/scripts/p1_assemble.py")
         .add_local_file(ROOT / "exploratory" / "p1_checks" / "c1b_chimera_other.py", f"{REMOTE}/exploratory/p1_checks/c1b_chimera_other.py")
         .add_local_file(SAN / "common.py", f"{REMOTE}/exploratory/p1b_sanity/common.py")
         .add_local_file(SAN / "a3_decomp_fair.py", f"{REMOTE}/exploratory/p1b_sanity/a3_decomp_fair.py"))
app = modal.App(APP, image=image)
vol = modal.Volume.from_name(VOL)


@app.function(gpu=GPU, cpu=CPU, memory=MEM_GIB * 1024, timeout=TIMEOUT_MIN * 60, retries=0, max_containers=MAXC, scaledown_window=10, volumes={"/vol": vol})
def run_one(name, spec, rep):
    t_start = time.time(); sys.path.insert(0, f"{REMOTE}/exploratory/p1b_sanity")
    import numpy as np
    import torch
    import a3_decomp_fair as a3
    import common as cm
    dev = a3.accel.pick("auto"); print(f"{name} rep {rep}: device {dev} {torch.cuda.get_device_name(0)}", flush=True)
    R = cm.load_rows(a3.ROWS_KEYS); C = cm.concepts(); Gt = cm.gates()
    X, pert_in = a3.load_input(spec["inp"], R, C); ctx = cm.Ctx(rep, R, C, Gt, pert_in); t_load = (time.time() - t_start) / 60
    r = a3.fit_eval(name, spec, ctx, X, dev)
    r["where"] = dict(host="modal", gpu=torch.cuda.get_device_name(0), torch=torch.__version__, load_min=t_load, container_min=(time.time() - t_start) / 60)
    print(f"{name} rep {rep}: R1 {r['R1']:.3f} area orig {r['area_orig']:.3f} neutral {r['area_neutral']:.3f} | fit {r['fit_min']:.1f} min, total {r['where']['container_min']:.1f} min", flush=True)
    return json.loads(json.dumps(r, default=lambda o: o.tolist() if isinstance(o, np.ndarray) else float(o)))


def sae_methods():
    """the method specs, from a3_decomp_fair.sae_methods() in the project venv (reads results/a2_sae_audit.json)."""
    code = "import json, a3_decomp_fair as a; print('@@' + json.dumps(a.sae_methods()))"
    out = subprocess.run([str(ROOT / ".venv" / "Scripts" / "python.exe"), "-c", code], cwd=SAN, capture_output=True, text=True, check=True)
    return json.loads(out.stdout.split("@@")[-1])


@app.local_entrypoint()
def main(jobs: str = "all"):
    sys.path.insert(0, str(HERE)); import budget as B
    specs = sae_methods(); path = SAN / "results" / "a3_sae.json"; res = json.load(open(path)) if path.exists() else {}
    want = [(n, r) for n in specs for r in (0, 1, 2)] if jobs == "all" else [(j.split(":")[0], int(j.split(":")[1])) for j in jobs.split(",")]
    todo = [(n, r) for n, r in want if f"{n}_rep{r}" not in res]
    print(f"methods {list(specs)}; to run {todo}; timeout {TIMEOUT_MIN} min, max containers {MAXC}, {GPU}")
    if not todo: print("nothing to run"); return
    rate = B.rate_h(GPU, CPU, MEM_GIB); worst = B.worst_case(len(todo), TIMEOUT_MIN, GPU, CPU, MEM_GIB) + IMAGE_USD
    ok, rep = B.check(TASK, worst); print(json.dumps(rep, indent=1))
    if not ok: raise SystemExit(f"BUDGET CHECK FAILED - not launching (worst case ${worst:.2f})")
    rid = B.open_run(TASK, worst, dict(app=APP, jobs=[f"{n}:{r}" for n, r in todo], timeout_min=TIMEOUT_MIN, gpu=GPU, cpu=CPU, mem_gib=MEM_GIB))
    print(f"launch {rid}: {len(todo)} jobs, worst case ${worst:.2f}")
    measured, n_ok, n_fail = IMAGE_USD, 0, 0
    try:
        for out in run_one.starmap([(n, specs[n], r) for n, r in todo], order_outputs=False, return_exceptions=True):
            if isinstance(out, BaseException): n_fail += 1; measured += (TIMEOUT_MIN + B.START_MIN) / 60 * rate; print("JOB FAILED:", repr(out)[:800]); continue
            res = json.load(open(path)) if path.exists() else {}; res[f"{out['method']}_rep{out['rep']}"] = out; res["_methods"] = specs
            json.dump(res, open(path, "w"), indent=1); n_ok += 1; measured += (out["where"]["container_min"] + B.START_MIN) / 60 * rate
            print(f"saved {out['method']}_rep{out['rep']} ({n_ok + n_fail}/{len(todo)}); measured so far ${measured:.2f}")
    finally:
        left = len(todo) - n_ok - n_fail; measured += left * (TIMEOUT_MIN + B.START_MIN) / 60 * rate  # interrupted: count unfinished at worst case
        B.close_run(rid, measured, f"ok {n_ok}, failed {n_fail}, unfinished {left}"); print(f"closed {rid}: ok {n_ok} failed {n_fail} unfinished {left}, cost estimate ${measured:.2f}")
