"""Stage 1a SAE rows on Modal (one L4 per job), with the same code as the CPU rows: s1a_lib.run_job (fit -> production ladder with both
chimera rules -> T4/T5/T8 -> T6 k = 1 probing). Jobs: tuned single SAE, its 5-fit consensus (T7), and the nulls at the tuned config (T9:
untrained CT-FM, physics R3), reps 0-2. Results -> results/s1a_sae.json and results/tables/ on this PC.
Budget: p1b_sanity/cloud/budget.py checks task, project and month before launch (user rule: $29 per Modal account per month; this task's
budget is in the ledger). Each job's Modal timeout is the hard bound for the worst case.
usage (from v2_ct/, miniconda modal client):
  $env:S1A_TIMEOUT_MIN = "15"; $env:S1A_MAXC = "1"; C:\\Users\\Arman\\miniconda3\\Scripts\\modal.exe run --detach cloud/s1a_sae_modal.py --jobs sae_M1024_k6_s12000:0
  ... --jobs singles | cons      (singles = single SAE + both nulls, reps 0-2; cons = consensus, reps 0-2)
Each job also writes its result to the volume (/s1a_out/<name>_rep<r>.json). With --detach the cloud jobs keep running if the local client
dies; then cloud/s1a_collect.ps1 fetches and merges the results, and the ledger run is closed by hand from Modal billing.
"""
import json
import os
import sys
import time
from pathlib import Path

import modal

TASK, APP, VOL = "v2s1a_sae", "imgsae-v2-s1a", "imgsae-p1b"
GPU, CPU, MEM_GIB = "L4", 4, 16
TIMEOUT_MIN = int(os.environ.get("S1A_TIMEOUT_MIN", "15")); MAXC = int(os.environ.get("S1A_MAXC", "3"))
IMAGE_USD = 0.10
REMOTE = "/root/imgsae"
LOCAL = modal.is_local()
HERE = Path(__file__).resolve().parent; V2 = HERE.parent if LOCAL else Path("/x/x/x"); ROOT = V2.parents[1]; SAN = ROOT / "exploratory" / "p1b_sanity"

image = (modal.Image.debian_slim(python_version="3.11")
         .pip_install("torch==2.10.0", "numpy==2.4.6", "scipy==1.17.1", "scikit-learn==1.9.1", "pandas==3.1.1", "joblib==1.6.0", "threadpoolctl==3.8.0")
         .env({"IMGSAE_P1": "/vol/p1", "PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1", "OMP_NUM_THREADS": str(CPU), "MKL_NUM_THREADS": str(CPU), "S1A_JOBS": str(CPU)})
         .add_local_dir(ROOT / "imgsae", f"{REMOTE}/imgsae", ignore=["**/__pycache__/**"])
         .add_local_file(ROOT / "scripts" / "p1_fit.py", f"{REMOTE}/scripts/p1_fit.py")
         .add_local_file(ROOT / "scripts" / "p1_probe.py", f"{REMOTE}/scripts/p1_probe.py")
         .add_local_file(ROOT / "scripts" / "p1_assemble.py", f"{REMOTE}/scripts/p1_assemble.py")
         .add_local_file(ROOT / "exploratory" / "p1_checks" / "c1b_chimera_other.py", f"{REMOTE}/exploratory/p1_checks/c1b_chimera_other.py")
         .add_local_file(SAN / "common.py", f"{REMOTE}/exploratory/p1b_sanity/common.py")
         .add_local_file(SAN / "results" / "cache_refpos.npz", f"{REMOTE}/exploratory/p1b_sanity/results/cache_refpos.npz")
         .add_local_file(V2 / "s1a_lib.py", f"{REMOTE}/exploratory/v2_ct/s1a_lib.py")
         .add_local_file(V2 / "results" / "s1a_tasks.npz", f"{REMOTE}/exploratory/v2_ct/results/s1a_tasks.npz"))
app = modal.App(APP, image=image)
vol = modal.Volume.from_name(VOL)


@app.function(gpu=GPU, cpu=CPU, memory=MEM_GIB * 1024, timeout=TIMEOUT_MIN * 60, retries=0, max_containers=MAXC, scaledown_window=10, volumes={"/vol": vol})
def run_one(name, rep):
    t_start = time.time(); sys.path.insert(0, f"{REMOTE}/exploratory/v2_ct")
    import torch
    import s1a_lib as L
    from imgsae import accel
    spec = L.methods()[name]; dev = accel.pick("auto")
    print(f"{name} rep {rep}: device {dev} {torch.cuda.get_device_name(0)}", flush=True)
    R = L.cm.load_rows(L.ROWS_KEYS); C = L.cm.concepts(); Gt = L.cm.gates(); tasks = L.load_tasks()
    X, pert_in = L.load_input(spec["inp"], R, C); t_load = (time.time() - t_start) / 60
    r, tables = L.run_job(name, spec, rep, R, C, Gt, X, pert_in, tasks, dev)
    r["where"] = dict(host="modal", gpu=str(torch.cuda.get_device_name(0)), torch=str(torch.__version__), load_min=t_load, container_min=(time.time() - t_start) / 60)
    print(f"{name} rep {rep}: R1 {r['R1']:.3f} matched neutral {r['area_matched_neutral']:.3f} | fit {r['fit_min']:.1f} min, total {r['where']['container_min']:.1f} min", flush=True)
    tab = {h: {k: (v.tolist() if hasattr(v, "tolist") else list(v)) for k, v in T.items()} for h, T in tables.items()}
    out = (r, json.loads(json.dumps(tab, default=lambda o: bool(o) if type(o).__name__ == "bool_" else float(o))))
    # also keep the result on the volume, so it survives a lost local client (collect with s1a_collect.ps1)
    try:
        os.makedirs("/vol/s1a_out", exist_ok=True)
        with open(f"/vol/s1a_out/{name}_rep{rep}.json", "w") as f: json.dump(dict(result=out[0], tables=out[1]), f)
        vol.commit(); print(f"{name} rep {rep}: saved to volume /s1a_out", flush=True)
    except Exception as e:  # never lose the returned result because of the backup copy
        print(f"{name} rep {rep}: volume save FAILED {e!r}", flush=True)
    return out


def gpu_methods():
    """the GPU method specs from s1a_lib.methods(), run in the project venv (the modal client's python has no numpy)."""
    import subprocess
    code = "import json, s1a_lib as L; print('@@' + json.dumps({n: s for n, s in L.methods().items() if s.get('gpu')}))"
    out = subprocess.run([str(ROOT / ".venv" / "Scripts" / "python.exe"), "-c", code], cwd=V2, capture_output=True, text=True, check=True)
    return json.loads(out.stdout.split("@@")[-1])


def save_tables_csv(name, rep, tab):
    """per-feature tables as results/tables/<name>_rep<rep>_<half>.csv.gz, the format of s1a_lib.save_tables (stdlib only)."""
    import csv
    import gzip
    import math
    fmt = lambda x: x if isinstance(x, (str, bool)) else ("" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.5g}")  # noqa: E731
    for h, T in tab.items():
        keys = list(T)
        with gzip.open(V2 / "results" / "tables" / f"{name}_rep{rep}_{h}.csv.gz", "wt", newline="") as f:
            w = csv.writer(f); w.writerow(keys)
            for i in range(len(T[keys[0]])): w.writerow([fmt(T[k][i]) for k in keys])


@app.local_entrypoint()
def main(jobs: str = "singles"):
    sys.path.insert(0, str(SAN / "cloud")); import budget as B
    allm = gpu_methods(); path = V2 / "results" / "s1a_sae.json"; res = json.load(open(path)) if path.exists() else {}
    if jobs == "singles": want = [(n, r) for n in allm if allm[n]["meth"] == "sae_single" for r in (0, 1, 2)]
    elif jobs == "cons": want = [(n, r) for n in allm if allm[n]["meth"] == "sae_cons" for r in (0, 1, 2)]
    else: want = [(j.split(":")[0], int(j.split(":")[1])) for j in jobs.split(",")]
    todo = [(n, r) for n, r in want if f"{n}_rep{r}" not in res]
    print(f"to run {todo}; timeout {TIMEOUT_MIN} min, max containers {MAXC}, {GPU}")
    if not todo: print("nothing to run"); return
    rate = B.rate_h(GPU, CPU, MEM_GIB); worst = B.worst_case(len(todo), TIMEOUT_MIN, GPU, CPU, MEM_GIB) + IMAGE_USD
    ok, rep_ = B.check(TASK, worst); print(json.dumps(rep_, indent=1))
    if not ok: raise SystemExit(f"BUDGET CHECK FAILED - not launching (worst case ${worst:.2f})")
    rid = B.open_run(TASK, worst, dict(app=APP, jobs=[f"{n}:{r}" for n, r in todo], timeout_min=TIMEOUT_MIN, gpu=GPU, cpu=CPU, mem_gib=MEM_GIB))
    print(f"launch {rid}: {len(todo)} jobs, worst case ${worst:.2f}")
    measured, n_ok, n_fail = IMAGE_USD, 0, 0
    try:
        for out in run_one.starmap(todo, order_outputs=False, return_exceptions=True):
            if isinstance(out, BaseException): n_fail += 1; measured += (TIMEOUT_MIN + B.START_MIN) / 60 * rate; print("JOB FAILED:", repr(out)[:800]); continue
            r, tab = out; key = f"{r['method']}_rep{r['rep']}"
            save_tables_csv(r["method"], r["rep"], tab)
            res = json.load(open(path)) if path.exists() else {}; res[key] = r; json.dump(res, open(path, "w"), indent=1)
            n_ok += 1; measured += (r["where"]["container_min"] + B.START_MIN) / 60 * rate
            print(f"saved {key} ({n_ok + n_fail}/{len(todo)}): matched neutral {r['area_matched_neutral']:.3f}; measured so far ${measured:.2f}")
    finally:
        left = len(todo) - n_ok - n_fail; measured += left * (TIMEOUT_MIN + B.START_MIN) / 60 * rate
        B.close_run(rid, measured, f"ok {n_ok}, failed {n_fail}, unfinished {left}"); print(f"closed {rid}: ok {n_ok} failed {n_fail} unfinished {left}, cost estimate ${measured:.2f}")
