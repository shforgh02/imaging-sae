"""Stage 1a runner, local CPU part (exploratory, dev data; protocol docs/STAGE1A_PROTOCOL.md). SAE rows run on Modal: cloud/s1a_sae_modal.py.
Steps (each resumable):
  --step tasks    T6 token sets = Stage A's A1 T1b / T3_vert / T3_lobe (same builder and seeds) -> results/s1a_tasks.npz; sanity: sizes = A1
  --step cpu      CPU methods (s1a_lib.methods(), not gpu) on --reps; default names: all candidates on rep 0, or with --selected the
                  rep-0 representatives of each family (results/s1a_selection.json) -> results/s1a_cpu.json + results/tables/*.csv.gz
                  Sanity: every row with a Stage A counterpart (km M425 / raw / sparse varimax at L0 6 and 27) must equal a3_cpu.json exactly.
  --step select   selection rule on rep 0 (protocol section 3) -> results/s1a_selection.json
  --step refs     T6 dense references (CT-FM, label-free R4, untrained CT-FM) per rep -> results/s1a_refs.json
usage (from v2_ct/): ..\\..\\.venv\\Scripts\\python s1a_run.py --step cpu [--reps 0] [--names a,b] [--selected]
"""
import argparse
import json
import sys

import numpy as np

import s1a_lib as L
from s1a_lib import RES, SAN, cm, log

A3_OF = {f"km_M425_L{l}": f"km_ctfm_L{l}" for l in (6, 27)} | {f"raw_L{l}": f"raw_ctfm_L{l}" for l in (6, 27)} | {f"svx_L{l}": f"svx_ctfm_L{l}" for l in (6, 27)}
SANITY_KEYS = ("R1", "area_orig", "area_neutral", "area_matched_orig", "area_matched_neutral")
PRIMARY = "area_matched_neutral"


def step_tasks():
    import a1_probe_ladder as a1
    C = cm.concepts(); R = cm.load_rows(["lab", "scan", "occ", "occg"]); T, _ = a1.build_tasks(R, C, quick=False)
    a1res = json.load(open(SAN / "results" / "a1_probe_ladder.json"))["tasks"]; meta, arrs = {}, {}
    for t in L.TASKS:
        d = T[t]; assert d["n_tokens"] == a1res[t]["n_tokens"] and d["scored"] == a1res[t]["scored"], t  # same token sets as A1
        meta[t] = dict(classes=d["classes"], scored=d["scored"], n_tokens=d["n_tokens"], n_patients=d["n_patients"]); arrs[f"{t}_rows"] = d["rows"]; arrs[f"{t}_y"] = d["y"]
        log(f"task {t}: {d['n_tokens']} tokens, {d['n_patients']} patients, {len(d['scored'])} scored classes (= A1)")
    np.savez(RES / "s1a_tasks.npz", meta=json.dumps(meta), **arrs); log("tasks written")


def step_cpu(a):
    allm = L.methods(); cpu = {n: s for n, s in allm.items() if not s.get("gpu")}
    if a.names: names = a.names.split(",")
    elif a.selected: sel = json.load(open(RES / "s1a_selection.json")); names = [sel["representative"][f] for f in sel["representative"] if f in ("kmeans", "ica", "dl", "raw", "svx")] + ["oracle"]
    else: names = list(cpu)
    reps = [int(r) for r in a.reps.split(",")]; path = RES / "s1a_cpu.json"; res = json.load(open(path)) if path.exists() else {}
    a3 = json.load(open(SAN / "results" / "a3_cpu.json")); R = cm.load_rows(L.ROWS_KEYS); C = cm.concepts(); Gt = cm.gates(); tasks = L.load_tasks()
    X, pert_in = L.load_input("X_ctfm", R, C); log(f"input X_ctfm {X.shape}; jobs {names} x reps {reps}")
    for rep in reps:
        cache = {}
        for n in names:
            key = f"{n}_rep{rep}"
            if key in res: continue
            r, tables = L.run_job(n, cpu[n], rep, R, C, Gt, X, pert_in, tasks, "cpu", cache)
            if n in A3_OF:
                ref = a3[f"{A3_OF[n]}_rep{rep}"]; diff = {k: abs(r[k] - ref[k]) for k in SANITY_KEYS}; r["sanity_vs_a3"] = diff
                if max(diff.values()) > 1e-12: log(f"SANITY FAIL {key}: {diff}"); dump_and_exit(res, path, 2)
            L.save_tables(n, rep, tables); res[key] = r; L.dump(res, path); f = r["feat"]
            log(f"{key}: R1 {r['R1']:.2f} L0 {np.mean(list(r['L0'].values())):.1f} nfeat {r['n_feat']} | area orig {r['area_orig']:.3f} neutral {r['area_neutral']:.3f}"
                f" | matched {r['area_matched_orig']:.3f} / {r[PRIMARY]:.3f} | C07 {r['C07_neutral']} | prec {f['neutral']['precision07']:.3f}"
                f" | k1 vert {r['k1']['T3_vert']['median']:.3f} lobe {r['k1']['T3_lobe']['median']:.3f} | fit {r['fit_min']:.1f} eval {r['eval_min']:.1f} k1 {r['k1_min']:.1f} min"
                + (" | sanity vs A3 exact" if n in A3_OF else ""))
    log("STEP CPU DONE")


def dump_and_exit(res, path, code):
    L.dump(res, path); sys.exit(code)


def step_select():
    """per family, the rep-0 config with the highest area at 425 features ('neutral'); ties -> higher R1. SAE family from A2 (rep 0)."""
    res = json.load(open(RES / "s1a_cpu.json")); a2 = json.load(open(SAN / "results" / "a2_sae_audit.json")); allm = L.methods(); cand = {}
    for n, s in allm.items():
        if s.get("gpu") or s["family"] in ("oracle", "null"): continue
        if f"{n}_rep0" not in res: raise SystemExit(f"missing rep-0 row {n}")
        cand.setdefault(s["family"], []).append((n, res[f"{n}_rep0"][PRIMARY], res[f"{n}_rep0"]["R1"]))
    cand["sae"] = [(("cons_" + n.replace("cons_", "")) if n.startswith("cons_") else ("sae_" + n), v[PRIMARY], v["R1"]) for n, v in a2.items() if isinstance(v, dict) and PRIMARY in v]
    rep_ = {f: max(c, key=lambda t: (t[1], t[2]))[0] for f, c in cand.items()}
    out = dict(rule="per family: max rep-0 area_matched_neutral, ties -> R1", candidates=cand, representative=rep_); L.dump(out, RES / "s1a_selection.json")
    for f, c in cand.items(): log(f"family {f}: " + ", ".join(f"{n} {v:.3f}" for n, v, _ in sorted(c, key=lambda t: -t[1])) + f" -> {rep_[f]}")


def step_refs(a):
    from sklearn.utils import parallel_backend  # noqa: F401  (threads only)
    reps = [int(r) for r in a.reps.split(",")]; path = RES / "s1a_refs.json"; res = json.load(open(path)) if path.exists() else {}
    R = cm.load_rows(L.ROWS_KEYS); C = cm.concepts(); Gt = cm.gates(); tasks = L.load_tasks(); rows = np.unique(np.concatenate([t["rows"] for t in tasks.values()]))
    ref, pos = cm.refpos(C); R4 = A_prep_rows(cm.raw_ref_sets(ref, pos, cm.zrel(R["gidx"], R["scan"]))["R4"], rows); del ref, pos
    Xs = dict(ctfm=L.load_array("X_ctfm"), R4=R4, null=L.load_array("X_null"))
    for rep in reps:
        ctx = cm.Ctx(rep, R, C, Gt, {})
        for s, X in Xs.items():
            k = f"{s}_rep{rep}"
            if k in res: continue
            res[k] = L.dense_probe(X, ctx, tasks); L.dump(res, path); log(f"refs {k}: " + ", ".join(f"{t} {v['median']:.3f}" for t, v in res[k].items()))
    log("STEP REFS DONE")


def A_prep_rows(raw, rows):
    """R4 prepared exactly as Stage A (A.prep on all rows); only the task rows are kept to save memory."""
    X = L.A.prep(raw)[0]; out = np.zeros_like(X); out[rows] = X[rows]; return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--step", required=True, choices=("tasks", "cpu", "select", "refs")); ap.add_argument("--reps", default="0")
    ap.add_argument("--names", default=""); ap.add_argument("--selected", action="store_true"); a = ap.parse_args(); log(f"Stage 1a step {a.step}")
    dict(tasks=step_tasks, cpu=lambda: step_cpu(a), select=step_select, refs=lambda: step_refs(a))[a.step]()


if __name__ == "__main__":
    main()
