"""Exploratory check 1b (post hoc, not part of the pre-written decision): is the chimera rule rejecting features because of the 'other' class?
In scripts/p1_fit.py the chimera rule counts 'other' tokens (<= 20% labelled structure; ~45% of scored tokens: fat, unlabelled tissue) as a
foreign concept for every organ feature. This script refits replicate 0 with the unchanged p1_fit code (same seeds, same halves) and scores
each feature twice: chimera as in the run ("orig") and with 'other' treated as adjacent to every concept ("neutral"). Everything else
(V0, selectivity, twin score, perturbation r, gates) is identical. Also records which class triggered each original chimera flag.
Writes results/c1b_chimera_rep0.json and results/c1b_<method>_rep0_<half>.csv. Main results are not touched.
usage: ..\..\.venv\Scripts\python c1b_chimera_other.py [--methods ...]
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import p1_fit as F  # noqa: E402  (unchanged production code)
from imgsae import accel, ladder, sae  # noqa: E402

OUT = HERE / "results"; OUT.mkdir(exist_ok=True); STASH = {}
_orig_chimera = ladder.chimera


def chimera_both(Z, lab, labs, own, adj, top_frac=.01, share=.2):
    """original result + triggering class (stashed); returns the 'neutral' variant (other adjacent to every concept)."""
    ch = _orig_chimera(Z, lab, labs, own, adj, top_frac, share); trig = []
    for f in np.flatnonzero(ch):
        z = Z[:, f]; nz = np.flatnonzero(z > 0); top = nz[np.argsort(-z[nz])[:max(1, int(np.ceil(top_frac * len(z))))]]; w = z[top]; tot = w.sum()
        hit = [l for l in labs if l != own[f] and l not in adj.get(own[f], ()) and w[lab[top] == l].sum() >= share * tot]; trig.append(hit[0] if hit else "?")
    STASH["orig"] = ch; STASH["trig"] = trig
    adj2 = {k: set(v) | {"other"} for k, v in adj.items()}
    return _orig_chimera(Z, lab, labs, own, adj2, top_frac, share)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--methods", default="sae_cons,sae_single,hu_sae_cons,null_enc_cons,pca,varimax,sparse_varimax,soft_kmeans,raw_sparse")
    ap.add_argument("--rep", type=int, default=0); a = ap.parse_args(); dev = accel.pick("auto"); print(f"device {dev}", flush=True)
    F.ladder.chimera = chimera_both  # p1_fit.feature_table calls ladder.chimera through the module
    P1 = F.P1; R = dict(np.load(P1 / "rows.npz")); C = json.load(open(P1 / "concepts.json")); Gt = json.load(open(P1 / "gates.json")); G, elig = C["groups"], C["eligible"]
    gates = Gt["token"]; cls_of = {g: ("path" if g == "kidney_cyst" else "anat") for g in G}; lab, scan = R["lab"], R["scan"]; S = C["scans"]
    scan_labels = dict(manufacturer_siemens=np.array([s["manufacturer"].strip().lower() == "siemens" for s in S], float),
                       institute_I=np.array([s["institute"] == "I" for s in S], float), kvp_ge120=np.array([float(s["kvp"] or 0) >= 120 for s in S], float),
                       contrast=np.array([s["contrast"] for s in S], float))
    pert_in = F.load_perturb(C, R); summ = json.load(open(P1 / "fit" / "summary.json")); rep = a.rep
    hA = F.halves(S, rep); Ea, Eb = F.eval_rows(scan, hA, seed=rep), F.eval_rows(scan, ~hA, seed=rep + 50); rowsA, rowsB = np.flatnonzero(hA[scan]), np.flatnonzero(~hA[scan])
    gated_set = [g for g in elig if gates.get(g, {}).get("gated")]; res_path = OUT / f"c1b_chimera_rep{rep}.json"
    res = json.load(open(res_path)) if res_path.exists() else {}
    for meth in a.methods.split(","):
        if meth in res: continue
        inp = F.SAE_METHODS[meth][0] if meth in F.SAE_METHODS else "X_ctfm"; X = R[inp]; d = X.shape[1]
        M, k = (C["M"], C["k"]) if inp != "X_ref" else sae.size_rule(d, C["n_eff"])
        cfg = dict(M=M, k=k, matryoshka=False, steps=3000, device=dev, rows_per_latent=None); L0 = summ[f"sae_cons_rep{rep}"]["L0_cons"]
        mods = {h: F.Model(meth, cfg, L0=L0, seed=rep * 7 + hi).fit(X[rows]) for hi, (h, rows) in enumerate((("A", rowsA), ("B", rowsB)))}
        Z = {h: {e: mods[h].encode(X[E]) for e, E in (("A", Ea), ("B", Eb))} for h in "AB"}; out = dict(area_orig=[], area_neutral=[], C07_orig=[], C07_neutral=[])
        trig_all = Counter(); n_v0 = n_ch_orig = n_ch_neu = 0
        for h, o, Eo in (("A", "B", Eb), ("B", "A", Ea)):
            pert = {}
            for kind, P in pert_in.items():
                keep = np.isin(P["rows"], Eo) | np.isin(scan[P["rows"]], np.flatnonzero(hA if o == "A" else ~hA))
                if keep.sum() >= 50: pert[kind] = dict(Z_orig=mods[h].encode(X[P["rows"][keep]]), Z_pert=mods[h].encode(P[inp][keep]))
            T = F.feature_table(Z[h][h], Z[o][h], Z[h][o], lab[Eo], scan[Eo], G, elig, C["adjacency"], gates, pert, scan_labels, list(scan_labels), cls_of)
            ch_o = STASH["orig"]; trig_all.update(STASH["trig"]); v0 = T["v0"]; n_v0 += int(v0.sum()); n_ch_orig += int((ch_o & v0).sum()); n_ch_neu += int((T["chimeric"] & v0).sum())
            base_o = v0 & ~ch_o & (T["concept"] != "other"); v_o = np.where(base_o, np.fmin(np.fmin(T["t"], T["sel"]), T["r_pert"]), 0.0)
            for tag, v in (("orig", v_o), ("neutral", T["v"])):
                vv = np.nan_to_num(v, nan=0.0); _, ar = ladder.coverage_curve(vv, T["concept"], gated_set); out[f"area_{tag}"].append(ar)
                out[f"C07_{tag}"].append(len({c for c, x in zip(T["concept"], vv) if x >= .7 and c in gated_set}))
            pd.DataFrame({**{k_: v_ for k_, v_ in T.items()}, "chimeric_orig": ch_o}).to_csv(OUT / f"c1b_{meth}_rep{rep}_{h}.csv", index=False)
        res[meth] = dict(area_orig=float(np.mean(out["area_orig"])), area_neutral=float(np.mean(out["area_neutral"])), area_run=summ[f"{meth}_rep{rep}"]["area"],
                         C07_orig=out["C07_orig"], C07_neutral=out["C07_neutral"], n_v0=n_v0, chim_share_orig=n_ch_orig / max(n_v0, 1), chim_share_neutral=n_ch_neu / max(n_v0, 1),
                         trigger_top=trig_all.most_common(6), trigger_other_share=trig_all.get("other", 0) / max(sum(trig_all.values()), 1))
        json.dump(res, open(res_path, "w"), indent=1, default=float); r = res[meth]
        print(f"{meth}: area run {r['area_run']:.3f} orig {r['area_orig']:.3f} neutral {r['area_neutral']:.3f} | chimeric {r['chim_share_orig']:.2f} -> {r['chim_share_neutral']:.2f}"
              f" | trigger 'other' {r['trigger_other_share']:.2f} | C07 {r['C07_orig']} -> {r['C07_neutral']}", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
