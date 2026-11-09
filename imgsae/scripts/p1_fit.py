"""Phase 1 D4-D6: methods x J=3 patient-grouped half replicates -> per-feature validity ladder and method summaries.
usage: python scripts/p1_fit.py [--reps 3] [--device auto] [--steps 3000] [--methods all] [--smoke]
Reads data/p1/{rows.npz, concepts.json, gates.json} and data/p1/perturb/<kind>/<id>.npz (kinds shift, noise, huoff).
Writes data/p1/fit/<method>_rep<j>_<half>.csv (per feature) and data/p1/fit/summary.json. Resumable per (method, rep).
Rules (lean plan v1, fixed before running): halves stratified by study type; model of half h scored on the other half's patients (V2, V3,
shortcut), twin score t_f on h's own evaluation tokens; v_f = min(t_f, sel_f, r_pert) for V0-passing non-chimeric features (else 0, NE = nan).
"""
import argparse
import os
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from imgsae import accel, consensus, ladder, sae  # noqa: E402

P1 = Path(os.environ.get("IMGSAE_P1", ROOT / "data/p1")); OUT = P1 / "fit"; KINDS = ("shift", "noise", "huoff")
SAE_METHODS = {"sae_cons": ("X_ctfm", "cons"), "sae_single": ("X_ctfm", "single"), "hu_sae_cons": ("X_ref", "cons"), "null_enc_cons": ("X_null", "cons"),
               "frozen_dec": ("X_ctfm", "frozen")}
CPU_METHODS = ("pca", "varimax", "sparse_varimax", "soft_kmeans", "raw_sparse")


def halves(scans, rep):
    """patient halves stratified by study type (seed = rep)."""
    rng = np.random.default_rng(1000 + rep); st = np.array([s["study_type"] for s in scans]); h = np.zeros(len(scans), bool)
    for t in np.unique(st):
        ii = rng.permutation(np.flatnonzero(st == t)); h[ii[: (len(ii) + rng.integers(0, 2)) // 2]] = True
    return h


def eval_rows(scan, mask_pat, per=300, seed=0):
    rng = np.random.default_rng(seed); out = []
    for s in np.flatnonzero(mask_pat):
        ii = np.flatnonzero(scan == s); out.append(ii if len(ii) <= per else rng.choice(ii, per, replace=False))
    return np.sort(np.concatenate(out)) if out else np.zeros(0, int)


def load_perturb(C, R):
    """perturbed token inputs per kind, preprocessed with the stored parameters; aligned with the original rows of that scan."""
    ids = [s["id"] for s in C["scans"]]; out = {}
    for kind in KINDS:
        d = P1 / "perturb" / kind
        if not d.exists(): continue
        rows, Xs = [], {"X_ctfm": [], "X_null": [], "X_ref": []}
        for f in sorted(d.glob("*.npz")):
            if f.stem not in ids: continue
            si = ids.index(f.stem); z = np.load(f); orig = np.flatnonzero(R["scan"] == si)
            if len(orig) != len(z["occ"]): continue
            rows.append(orig)
            for key, src, p in (("X_ctfm", "feat_ctfm", "ctfm"), ("X_null", "feat_null", "null"), ("X_ref", None, "ref")):
                raw = z[src] if src else np.concatenate([z["ref"], z["pos"]], 1)
                X = raw.astype(np.float32) - R[f"prep_{p}_mu"]; X /= np.maximum(np.linalg.norm(X, axis=1, keepdims=True), 1e-9); Xs[key].append(X / R[f"prep_{p}_sc"])
        if rows: out[kind] = dict(rows=np.concatenate(rows), **{k: np.concatenate(v) for k, v in Xs.items()})
    return out


class Model:
    """uniform fit/encode wrapper for SAE (single, consensus, frozen) and CPU baselines."""

    def __init__(self, method, cfg, L0=None, seed=0):
        self.method, self.cfg, self.L0, self.seed = method, cfg, L0, seed

    def fit(self, X):
        m, s = self.method, self.seed
        if m in SAE_METHODS:
            kind = SAE_METHODS[m][1]
            if kind == "cons":  # 5 fits; consensus groups fixed on (up to 30k of) the model's own fit rows
                self.models = [sae.fit(X, {**self.cfg, "seed": 10 * s + i})[0] for i in range(5)]
                sub = X[np.random.default_rng(s).choice(len(X), min(len(X), 30000), replace=False)]
                self.groups = consensus.consensus_groups_cl([sae.encode(mm, sub) for mm in self.models])
            elif kind == "single": self.models = [sae.fit(X, {**self.cfg, "seed": 10 * s})[0]]
            else: self.models = [sae.fit(X, {**self.cfg, "seed": 10 * s, "freeze_D": True})[0]]
            accel.empty_cache(self.cfg.get("device", "cpu"))
        else:
            from sklearn.decomposition import PCA
            self.pca = PCA(min(X.shape[1], len(X) - 1), random_state=s).fit(X)
            if m in ("varimax", "sparse_varimax"):
                L = self.pca.components_.T * np.sqrt(self.pca.explained_variance_); self.R = sae.varimax(L)
            if m == "soft_kmeans":
                from sklearn.cluster import MiniBatchKMeans
                self.km = MiniBatchKMeans(self.cfg["M"], random_state=s, n_init=3, batch_size=8192).fit(X)
                d = self.km.transform(X[np.random.default_rng(s).choice(len(X), min(len(X), 20000), replace=False)]); self.tau = float(np.median(d ** 2))
            if m == "raw_sparse": self.mu, self.sd = X.mean(0), X.std(0) + 1e-9
        return self

    def encode(self, X):
        m = self.method
        if m in SAE_METHODS:
            Zs = [sae.encode(mm, X) for mm in self.models]
            if SAE_METHODS[m][1] == "cons": return consensus.encode_groups(Zs, self.groups)
            return Zs[0]
        if m == "pca": return sae.split_signed(self.pca.transform(X))
        if m in ("varimax", "sparse_varimax"):
            Z = sae.split_signed(self.pca.transform(X) @ self.R); return Z if m == "varimax" else sae.topk_rows(Z, self.L0)
        if m == "soft_kmeans":
            d = self.km.transform(X); W = np.exp(-(d ** 2) / self.tau).astype(np.float32); return sae.topk_rows(W, self.L0)
        if m == "raw_sparse": return sae.topk_rows(sae.split_signed((X - self.mu) / self.sd), self.L0)

def feature_table(Z_own_e, Z_twin_e, Z_other, lab_o, scan_o, G, elig, adj, gates, pert, scan_labels, acq_names, cls_of):
    """per-feature ladder for one model: Z_own_e/Z_twin_e = own and twin model codes on own-half eval tokens; Z_other = own codes on other-half eval tokens."""
    F = Z_other.shape[1]; t = ladder.twin_scores(Z_own_e, Z_twin_e) if F else np.zeros(0)
    act = Z_other > 0; freq = act.mean(0); npat = np.array([len(np.unique(scan_o[act[:, f]])) for f in range(F)]); mag = np.where(act.any(0), np.abs(Z_other).sum(0) / np.maximum(act.sum(0), 1), 0)
    v0 = (freq >= 1e-3) & (npat >= 10)
    if F > 1:
        A = Z_other - Z_other.mean(0); A /= np.maximum(np.linalg.norm(A, axis=0), 1e-12); Cm = A.T @ A; np.fill_diagonal(Cm, 0)
        dup = np.array([bool(((Cm[f] >= .9) & (freq > freq[f])).any()) for f in range(F)]); v0 &= ~dup
    sc = lab_o >= -1; labs = [-1] + [G.index(g) for g in elig]; sc &= np.isin(lab_o, labs)
    sel, arg = ladder.selectivity(Z_other[sc], lab_o[sc], labs, groups=scan_o[sc])
    concept = np.array(["other" if a_ == -1 else G[a_] for a_ in arg])
    ch = ladder.chimera(Z_other[sc], np.array(["other" if l_ == -1 else G[l_] for l_ in lab_o[sc]]), ["other"] + elig, own=concept,
                        adj={**{k: set(v) for k, v in adj.items()}, "other": set(G)})
    r = {}
    for kind, P in pert.items():
        Zo, Zp = P["Z_orig"], P["Z_pert"]; Zo_ = Zo - Zo.mean(0); Zp_ = Zp - Zp.mean(0); den = np.linalg.norm(Zo_, axis=0) * np.linalg.norm(Zp_, axis=0)
        r[kind] = np.where(den > 0, (Zo_ * Zp_).sum(0) / np.maximum(den, 1e-12), np.nan)
    rs = r.get("shift", np.full(F, np.nan)); rn = r.get("noise", np.full(F, np.nan)); rh = r.get("huoff", np.full(F, np.nan))
    is_anat = np.array([cls_of.get(c) == "anat" for c in concept]); r_pert = np.where(is_anat, np.fmin(np.fmin(rs, rn), rh), np.fmin(rs, rn))
    r_pert = np.where(np.isnan(rs) | np.isnan(rn), np.nan, r_pert)
    gated = np.array([bool(gates.get(c, {}).get("gated", False)) for c in concept]); beyond = np.array([bool(gates.get(c, {}).get("beyond_hu", False)) for c in concept])
    valid_base = v0 & ~ch & (concept != "other")
    v = np.where(valid_base, np.fmin(np.fmin(t, sel), r_pert), 0.0); v = np.where(valid_base & np.isnan(r_pert), np.nan, v)
    ns = len(next(iter(scan_labels.values()))); means = np.zeros((ns, F))
    for s in range(ns):
        ii = scan_o == s
        if ii.any(): means[s] = Z_other[ii].mean(0)
    present = np.array([(scan_o == s).any() for s in range(ns)]); acq_auc = np.zeros(F)
    for nm in acq_names:
        y = scan_labels[nm]; ok = present & np.isfinite(y)
        if ok.sum() < 10 or y[ok].min() == y[ok].max(): continue
        for f in range(F):
            a_ = ladder.auroc(means[ok, f], y[ok] > 0); acq_auc[f] = max(acq_auc[f], abs(a_ - .5) + .5) if np.isfinite(a_) else acq_auc[f]
    return dict(t=t, sel=sel, concept=concept, chimeric=ch, v0=v0, r_shift=rs, r_noise=rn, r_huoff=rh, r_pert=r_pert, v=v, gated=gated, beyond=beyond,
                freq=freq, mag=mag, npat=npat, acq_auc=acq_auc)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--reps", type=int, default=3); ap.add_argument("--device", default="auto"); ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--methods", default="all"); ap.add_argument("--smoke", action="store_true"); a = ap.parse_args(); a.device = accel.pick(a.device); OUT.mkdir(parents=True, exist_ok=True); print(f"device {a.device}", flush=True)
    R = dict(np.load(P1 / "rows.npz")); C = json.load(open(P1 / "concepts.json")); Gt = json.load(open(P1 / "gates.json")); G, elig = C["groups"], C["eligible"]
    gates = Gt["token"]; cls_of = {g: ("path" if g == "kidney_cyst" else "anat") for g in G}; lab, scan = R["lab"], R["scan"]; ns = len(C["scans"])
    S = C["scans"]; scan_labels = dict(manufacturer_siemens=np.array([s["manufacturer"].strip().lower() == "siemens" for s in S], float),
                                       institute_I=np.array([s["institute"] == "I" for s in S], float), kvp_ge120=np.array([float(s["kvp"] or 0) >= 120 for s in S], float),
                                       contrast=np.array([s["contrast"] for s in S], float))
    pert_in = load_perturb(C, R); methods = list(SAE_METHODS) + list(CPU_METHODS) if a.methods == "all" else a.methods.split(",")
    summ_path = OUT / "summary.json"; summary = json.load(open(summ_path)) if summ_path.exists() else {}
    for rep in range(a.reps):
        hA = halves(S, rep); Ea, Eb = eval_rows(scan, hA, seed=rep), eval_rows(scan, ~hA, seed=rep + 50); rowsA, rowsB = np.flatnonzero(hA[scan]), np.flatnonzero(~hA[scan])
        L0_cons = None
        for meth in methods:
            key = f"{meth}_rep{rep}"
            if key in summary and not a.smoke: L0_cons = summary[key].get("L0_cons", L0_cons) if meth == "sae_cons" else L0_cons; continue
            inp = SAE_METHODS[meth][0] if meth in SAE_METHODS else "X_ctfm"; X = R[inp]; d = X.shape[1]
            M, k = (C["M"], C["k"]) if inp != "X_ref" else sae.size_rule(d, C["n_eff"])
            cfg = dict(M=M, k=k, matryoshka=False, steps=a.steps, device=a.device, rows_per_latent=None)
            if meth in CPU_METHODS and L0_cons is None: L0_cons = summary.get(f"sae_cons_rep{rep}", {}).get("L0_cons", k)
            mods = {h: Model(meth, cfg, L0=L0_cons, seed=rep * 7 + hi).fit(X[rows]) for hi, (h, rows) in enumerate((("A", rowsA), ("B", rowsB)))}
            Z = {h: {e: mods[h].encode(X[E]) for e, E in (("A", Ea), ("B", Eb))} for h in "AB"}
            if meth == "sae_cons": L0_cons = int(round(np.mean([(Z[h][h] > 0).sum(1).mean() for h in "AB"])))
            r1, r1med = sae.act_match(np.vstack([Z["A"]["A"], Z["A"]["B"]]), np.vstack([Z["B"]["A"], Z["B"]["B"]]))
            res = dict(method=meth, rep=rep, R1=r1, R1_med=r1med, n_feat={h: int(Z[h]["A"].shape[1]) for h in "AB"}, L0={h: float((Z[h][h] > 0).sum(1).mean()) for h in "AB"})
            if meth == "sae_cons": res["L0_cons"] = L0_cons
            areas, areas_b, tabs = [], [], {}
            for h, o, Eo in (("A", "B", Eb), ("B", "A", Ea)):
                pert = {}
                for kind, P in pert_in.items():
                    keep = np.isin(P["rows"], Eo) | np.isin(scan[P["rows"]], np.flatnonzero(hA if o == "A" else ~hA))
                    if keep.sum() < 50: continue
                    pert[kind] = dict(Z_orig=mods[h].encode(X[P["rows"][keep]]), Z_pert=mods[h].encode(P[inp][keep]))
                T = feature_table(Z[h][h], Z[o][h], Z[h][o], lab[Eo], scan[Eo], G, elig, C["adjacency"], gates, pert, scan_labels, list(scan_labels), cls_of)
                tabs[h] = T; gated_set = [g for g in elig if gates.get(g, {}).get("gated")]; beyond_set = [g for g in gated_set if gates[g].get("beyond_hu")]
                vv = np.nan_to_num(T["v"], nan=0.0); _, ar = ladder.coverage_curve(vv, T["concept"], gated_set); _, arb = ladder.coverage_curve(vv, T["concept"], beyond_set)
                areas.append(ar); areas_b.append(arb)
                import pandas as pd
                pd.DataFrame({k_: v_ for k_, v_ in T.items()}).to_csv(OUT / f"{meth}_rep{rep}_{h}.csv", index=False)
            Tall = {k_: np.concatenate([tabs["A"][k_], tabs["B"][k_]]) for k_ in tabs["A"]}
            y = (Tall["sel"] >= .7) & ~Tall["chimeric"] & Tall["gated"] & (np.nan_to_num(Tall["r_pert"], nan=-1) >= .7) & Tall["v0"]
            res.update(area=float(np.mean(areas)), area_beyond=float(np.mean(areas_b)),
                       theta=ladder.theta(np.where(Tall["v0"], Tall["t"], np.nan), y, freq=np.maximum(Tall["freq"], 1e-6), mag=np.maximum(Tall["mag"], 1e-6)),
                       n_valid07=int((np.nan_to_num(Tall["v"]) >= .7).sum()), C07=int(len({c for c, x in zip(Tall["concept"], np.nan_to_num(Tall["v"])) if x >= .7})),
                       share_ne=float(np.mean(np.isnan(Tall["v"]))))
            rep_ = Tall["v0"] & (Tall["t"] >= .7); res["n_reproducible"] = int(rep_.sum())
            res["shortcut_share"] = float(np.mean((Tall["acq_auc"][rep_] >= .8) | (np.nan_to_num(Tall["r_shift"][rep_], nan=1) < .5))) if rep_.any() else np.nan
            summary[key] = res; json.dump(summary, open(summ_path, "w"), indent=1, default=float)
            print(f"{key} R1 {r1:.2f} area {res['area']:.3f} beyondHU {res['area_beyond']:.3f} theta {res['theta'].get('theta')} shortcut {res['shortcut_share']}", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
