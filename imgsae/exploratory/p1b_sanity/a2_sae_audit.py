"""A2 (exploratory, dev data): is the Phase 1 SAE adequately trained, and does a larger / sparser SAE change the SAE-vs-baseline picture?
Plan docs/SANITY_PLAN_v1.md, section A2. Replicate 0 halves, production fit code (scripts/p1_fit.Model -> imgsae.sae.fit), production ladder
(p1_fit.feature_table) scored under both chimera rules (common.evaluate).
Per config: reconstruction R^2 on own-half and other-half evaluation tokens, dead-latent share, L0, R1 between halves, and the ladder areas.
Seed check (run config and best config): a second fit on half A with another seed -> R1 within the same data (seed noise vs data noise).
Configs: run (M 425, k 27, 3,000 steps; sanity: must reproduce fit/summary.json sae_single_rep0 and c1b), M in {425, 1024, 2048} x k in {6, 27}
at 3,000 steps, M 1024 at 12,000 steps; then a 5-fit consensus at the best single config (highest 'neutral' area; ties -> R1).
Writes results/a2_sae_audit.json (resumable per config). usage: ..\..\.venv\Scripts\python a2_sae_audit.py [--quick]
"""
import argparse
import json
import time

import numpy as np

from common import P1, RES, Ctx, F, concepts, dump, evaluate, gates, load_perturb_all, load_rows, log, sae
from imgsae import accel

CONFIGS = [("run_M425_k27_s3000", 425, 27, 3000), ("M425_k6_s3000", 425, 6, 3000), ("M1024_k27_s3000", 1024, 27, 3000), ("M1024_k6_s3000", 1024, 6, 3000),
           ("M2048_k27_s3000", 2048, 27, 3000), ("M2048_k6_s3000", 2048, 6, 3000), ("M1024_k27_s12000", 1024, 27, 12000), ("M1024_k6_s12000", 1024, 6, 12000)]


def diagnostics(mods, X, ctx):
    out = {}
    for h, o in (("A", "B"), ("B", "A")):
        m = mods[h].models[0]; Zo = sae.encode(m, X[ctx.E[o]])
        out[h] = dict(r2_own=sae.recon_r2(m, X[ctx.E[h]]), r2_other=sae.recon_r2(m, X[ctx.E[o]]), dead_share=float(1 - sae.alive(Zo).mean()), L0_other=float((Zo > 0).sum(1).mean()))
    return out


def seed_check(cfg, X, ctx, mA=None):
    """second fit on half A with a different seed (production seed model refitted if not given); R1 on the same evaluation rows."""
    mA = mA or F.Model("sae_single", cfg, seed=ctx.rep * 7).fit(X[ctx.rows["A"]])
    m2 = F.Model("sae_single", cfg, seed=ctx.rep * 7 + 50).fit(X[ctx.rows["A"]]); E = np.concatenate([ctx.E["A"], ctx.E["B"]])
    r1, r1med = sae.act_match(mA.encode(X[E]), m2.encode(X[E])); return dict(R1_within_halfA=r1, R1_med_within_halfA=r1med)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true"); a = ap.parse_args(); dev = accel.pick("auto"); log(f"A2 device {dev}")
    R = load_rows(["X_ctfm", "lab", "scan"] + [f"prep_{p}_{q}" for p in ("ctfm", "null", "ref") for q in ("mu", "sc")]); C = concepts(); Gt = gates(); X = R["X_ctfm"]
    pert_in = load_perturb_all(C, R)
    for d in pert_in.values(): d.pop("X_null", None); d.pop("X_ref", None)  # only CT-FM inputs are needed here (saves ~1.3 GB)
    ctx = Ctx(0, R, C, Gt, pert_in); log(f"loaded; perturbation kinds {list(pert_in)}")
    path = RES / f"a2_sae_audit{'_quick' if a.quick else ''}.json"; res = json.load(open(path)) if path.exists() else {}
    configs = [(n, M, k, 200) for n, M, k, _ in CONFIGS[:2]] if a.quick else CONFIGS
    for name, M, k, steps in configs:
        if name in res: continue
        cfg = dict(M=M, k=k, matryoshka=False, steps=steps, device=dev, rows_per_latent=None); t0 = time.time()
        mods = ctx.fit("sae_single", cfg, X); fit_min = (time.time() - t0) / 60; accel.empty_cache(dev)
        r = dict(M=M, k=k, steps=steps, fit_min_two_halves=fit_min, **evaluate(mods, X, "X_ctfm", ctx), diag=diagnostics(mods, X, ctx))
        if name.startswith("run"): r.update(seed_check(cfg, X, ctx, mods["A"]))
        res[name] = r; dump(res, path)
        log(f"{name}: fit {fit_min:.1f} min | R1 {r['R1']:.2f} | r2_other {np.mean([d['r2_other'] for d in r['diag'].values()]):.3f} | dead {np.mean([d['dead_share'] for d in r['diag'].values()]):.2f}"
            f" | area orig {r['area_orig']:.3f} neutral {r['area_neutral']:.3f} matched {r['area_matched_neutral']:.3f} | C07 {r['C07_neutral']} | med sel {r['median_sel_v0']:.2f}")
    singles = [n for n, *_ in configs]; best = max(singles, key=lambda n: (res[n]["area_neutral"], res[n]["R1"])); res["_best_single"] = best
    res["_best_single_by_k"] = {str(k): max([n for n in singles if res[n]["k"] == k], key=lambda n: (res[n]["area_neutral"], res[n]["R1"])) for k in sorted({res[n]["k"] for n in singles})}
    b = res[best]; cfg = dict(M=b["M"], k=b["k"], matryoshka=False, steps=b["steps"], device=dev, rows_per_latent=None)
    if "seed_check_best" not in res and not best.startswith("run"):
        res["seed_check_best"] = dict(config=best, **seed_check(cfg, X, ctx)); dump(res, path); log(f"seed check {best}: {res['seed_check_best']}")
    cname = f"cons_{best}"
    if cname not in res:
        t0 = time.time(); mods = ctx.fit("sae_cons", cfg, X); fit_min = (time.time() - t0) / 60; accel.empty_cache(dev)
        res[cname] = dict(M=b["M"], k=b["k"], steps=b["steps"], fit_min_two_halves=fit_min, **evaluate(mods, X, "X_ctfm", ctx)); dump(res, path)
        r = res[cname]; log(f"{cname}: fit {fit_min:.1f} min | R1 {r['R1']:.2f} | n_feat {r['n_feat']} | area orig {r['area_orig']:.3f} neutral {r['area_neutral']:.3f}")
    # sanity vs the run (fit/summary.json) and check 1b (rep 0)
    if not a.quick:
        S = json.load(open(P1 / "fit" / "summary.json"))["sae_single_rep0"]; cb = json.load(open(RES.parents[1] / "p1_checks" / "results" / "c1b_chimera_rep0.json"))["sae_single"]
        r = res["run_M425_k27_s3000"]; res["_sanity"] = dict(R1_run=S["R1"], R1_here=r["R1"], area_run=S["area"], area_orig_here=r["area_orig"],
                                                            area_neutral_c1b=cb["area_neutral"], area_neutral_here=r["area_neutral"])
        log(f"sanity: {res['_sanity']}")
    dump(res, path); log(f"best single {best}; by k {res['_best_single_by_k']}"); log("DONE")


if __name__ == "__main__":
    main()
