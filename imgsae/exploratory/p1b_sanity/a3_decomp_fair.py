"""A3 (exploratory, dev data): fair comparison of SAEs and simple decompositions on the Phase 1 validity ladder.
Plan docs/SANITY_PLAN_v1.md, section A3. Replicates 0-2 (production halves), both chimera rules, matched sparsity (L0 6 = the run's consensus
L0, and 27 = the run's single-SAE k), areas raw and feature-count matched (425 features, 20 draws; common.evaluate).
Inputs: CT-FM (X_ctfm), untrained CT-FM (X_null), and the label-free reference R3 (HU + texture + 48 mm context + body x/y; no FM at all).
  --part cpu : soft k-means (M 425), raw sparse channels, sparse varimax (CT-FM only) at L0 6 and 27, on each input
  --part sae : single SAE at the run config and at A2's best config per k; 5-fit consensus at the run config (reads results/a2_sae_audit.json)
Sanity: CT-FM rows at L0 6 are the run's rows -> 'orig' areas must equal fit/summary.json; rep 0 'neutral' must equal check 1b.
Writes results/a3_<part>.json (resumable per method x rep). usage: ..\..\.venv\Scripts\python a3_decomp_fair.py --part cpu|sae [--quick]
"""
import argparse
import json
import time

import numpy as np

from common import A, P1, RES, Ctx, concepts, dump, evaluate, gates, load_perturb_all, load_rows, log, raw_ref_sets, refpos, zrel
from imgsae import accel


def cpu_methods():
    out = {}
    for inp, tag in (("X_ctfm", "ctfm"), ("X_null", "null"), ("R3", "R3")):
        for meth, short in (("soft_kmeans", "km"), ("raw_sparse", "raw")) + ((("sparse_varimax", "svx"),) if tag == "ctfm" else ()):
            for L0 in (6, 27): out[f"{short}_{tag}_L{L0}"] = dict(meth=meth, inp=inp, L0=L0, cfg=dict(M=425))
    return out


def sae_methods():
    out = dict(sae_run=dict(meth="sae_single", inp="X_ctfm", cfg=dict(M=425, k=27, steps=3000)), sae_cons_run=dict(meth="sae_cons", inp="X_ctfm", cfg=dict(M=425, k=27, steps=3000)))
    p = RES / "a2_sae_audit.json"
    if not p.exists() or "_best_single_by_k" not in json.load(open(p)): log("A2 results missing: run-config SAE rows only"); return out
    a2 = json.load(open(p))
    for k, name in a2["_best_single_by_k"].items():
        b = a2[name]
        if name.startswith("run"): continue  # identical to sae_run
        out[f"sae_best_k{k}"] = dict(meth="sae_single", inp="X_ctfm", cfg=dict(M=b["M"], k=b["k"], steps=b["steps"]), a2_config=name)
    return out


ROWS_KEYS = ["lab", "scan", "gidx"] + [f"prep_{p}_{q}" for p in ("ctfm", "null", "ref") for q in ("mu", "sc")]


def load_input(inp, R, C):
    """one input matrix and its perturbation inputs; only 'rows' and this input are kept (one input in memory at a time)."""
    r3p = None
    if inp == "R3":
        ref, pos = refpos(C); X, mu, sc = A.prep(raw_ref_sets(ref, pos, zrel(R["gidx"], R["scan"]))["R3"]); r3p = (mu, sc); del ref, pos
    else: X = load_rows([inp])[inp]
    pert_in = load_perturb_all(C, R, r3p)
    for d in pert_in.values():
        for k in [k for k in d if k not in ("rows", inp)]: d.pop(k)
    return X, pert_in


def fit_eval(name, spec, ctx, X, dev, quick=False):
    """fit one method on the replicate's two halves and score it (common.evaluate). Also used by modal/a3_sae_modal.py."""
    cfg = dict(matryoshka=False, device=dev, rows_per_latent=None, **spec["cfg"])
    if quick and "steps" in cfg: cfg["steps"] = 200
    t0 = time.time(); mods = ctx.fit(spec["meth"], cfg, X, L0=spec.get("L0")); fit_min = (time.time() - t0) / 60
    if dev != "cpu": accel.empty_cache(dev)
    return dict(method=name, rep=ctx.rep, fit_min=fit_min, **evaluate(mods, X, spec["inp"], ctx))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--part", required=True, choices=("cpu", "sae")); ap.add_argument("--quick", action="store_true")
    ap.add_argument("--reps", default="0,1,2"); a = ap.parse_args(); dev = accel.pick("auto") if a.part == "sae" else "cpu"; log(f"A3 part {a.part} device {dev}")
    R = load_rows(ROWS_KEYS); C = concepts(); Gt = gates(); methods = cpu_methods() if a.part == "cpu" else sae_methods()
    if a.quick: methods = dict(list(methods.items())[:2])
    path = RES / f"a3_{a.part}{'_quick' if a.quick else ''}.json"; res = json.load(open(path)) if path.exists() else {}; res["_methods"] = methods
    reps = [0] if a.quick else [int(r) for r in a.reps.split(",")]
    for inp in dict.fromkeys(s["inp"] for s in methods.values()):  # one input matrix in memory at a time
        todo = [(n, s) for n, s in methods.items() if s["inp"] == inp and any(f"{n}_rep{r}" not in res for r in reps)]
        if not todo: continue
        X, pert_in = load_input(inp, R, C); log(f"input {inp} loaded: {X.shape}")
        for rep in reps:
            ctx = Ctx(rep, R, C, Gt, pert_in)
            for name, spec in todo:
                key = f"{name}_rep{rep}"
                if key in res: continue
                r = fit_eval(name, spec, ctx, X, dev, a.quick); res[key] = r; dump(res, path)
                log(f"{key}: R1 {r['R1']:.2f} L0 {r['L0']} nfeat {r['n_feat']} | area orig {r['area_orig']:.3f} neutral {r['area_neutral']:.3f}"
                    f" | matched orig {r['area_matched_orig']:.3f} neutral {r['area_matched_neutral']:.3f} | C07 n {r['C07_neutral']} | {r['fit_min']:.1f} min")
        del X, pert_in
    if a.part == "cpu" and not a.quick:
        S = json.load(open(P1 / "fit" / "summary.json")); cb = json.load(open(RES.parents[1] / "p1_checks" / "results" / "c1b_chimera_rep0.json")); san = {}
        for short, meth in (("km", "soft_kmeans"), ("raw", "raw_sparse"), ("svx", "sparse_varimax")):
            for rep in reps:
                k = f"{short}_ctfm_L6_rep{rep}"
                if k in res: san[k] = dict(area_run=S[f"{meth}_rep{rep}"]["area"], area_orig_here=res[k]["area_orig"], R1_run=S[f"{meth}_rep{rep}"]["R1"], R1_here=res[k]["R1"])
                if k in res and rep == 0: san[k].update(area_neutral_c1b=cb[meth]["area_neutral"], area_neutral_here=res[k]["area_neutral"])
        res["_sanity"] = san; log(f"sanity: {san}")
    if a.part == "sae" and not a.quick:
        S = json.load(open(P1 / "fit" / "summary.json")); san = {}
        for name, meth in (("sae_run", "sae_single"), ("sae_cons_run", "sae_cons")):
            for rep in reps:
                k = f"{name}_rep{rep}"
                if k in res: san[k] = dict(area_run=S[f"{meth}_rep{rep}"]["area"], area_orig_here=res[k]["area_orig"], R1_run=S[f"{meth}_rep{rep}"]["R1"], R1_here=res[k]["R1"])
        res["_sanity"] = san; log(f"sanity: {san}")
    dump(res, path); log("DONE")


if __name__ == "__main__":
    main()
