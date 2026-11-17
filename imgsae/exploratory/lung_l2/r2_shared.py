"""Lung L2, step R (rescue scouting; dev only, exploratory): shared axes of the five Sybil members ("group" approach).
Idea: Sybil's vectors are small and dense, and each member uses its own directions. So first find the directions that all five
members share (multiset CCA, MAXVAR), then name them. A sparse dictionary is not needed for this.
usage: python r2_shared.py <assembled dir> <heads npz> <out dir> [--layers h,pooled] [--npc 30] [--rows N (test only)]
Per layer:
 1. halves (participants, as S4). Fit on one half: per member z-score, PCA to npc, whiten; MAXVAR on the five blocks.
    An axis is SHARED if on the OTHER half the mean pairwise correlation of its five member variates is >= 0.70. Both directions.
 2. null: the same with the exam order shuffled inside each member. Must give no shared axis.
 3. function kept: each member's vector is rebuilt from its shared axes only, then Sybil's own head gives the logits (other half).
    Compared with the same number of the member's own top PCs.
 4. stability: axes fitted on half A against axes fitted on half B (activation correlation on all exams, Hungarian), with and
    without an ICA rotation of the shared axes.
 5. final axes: fitted on all dev; named as S4 families (same Shapley rule, same split-half checks); correlation with the risk score.
Writes <out>/r2_shared_<layer>.json, r2_axes_<layer>.csv; the fitted transforms go to <L2_S4_DATA>/r/ (outside git).
"""
import argparse
import json
import os
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, r"D:\Shayan\imgsae")
import l2_data as D  # noqa: E402
import r1_arms as R1  # noqa: E402
import s4_decomp as DC  # noqa: E402
import s4_q1a as Q  # noqa: E402

DATA = Path(os.environ.get("L2_S4_DATA", r"D:\Shayan\imgsae_data\lung_l2"))
R_SHARED = 0.70


class Shared:
    """per member: z-score, PCA to npc, whiten (fit rows); MAXVAR across members. .variates(X) -> (n, 5, npc) member variates."""

    def fit(self, X, npc=30):
        self.npc, self.T, W = npc, [], []
        for m in range(X.shape[1]):
            x = X[:, m]; mu, sd = x.mean(0), x.std(0); live = sd >= 1e-6; Z = (x[:, live] - mu[live]) / sd[live]
            _, S, Vt = np.linalg.svd(Z, full_matrices=False); P = Vt[:npc]; sc = S[:npc] / np.sqrt(len(Z))
            self.T.append(dict(mu=mu, sd=sd, live=live, P=P, sc=sc)); W.append(Z @ P.T / sc)
        _, S, Vt = np.linalg.svd(np.hstack(W) / np.sqrt(len(X)), full_matrices=False)
        self.ev = S[:npc] ** 2                                              # 5 = the same axis in all five members, 1 = nothing shared
        self.Wt = [Vt[:npc, m * npc:(m + 1) * npc].T / np.linalg.norm(Vt[:npc, m * npc:(m + 1) * npc].T, axis=0) for m in range(X.shape[1])]
        return self

    def white(self, x, m):
        t = self.T[m]; return (x[:, t["live"]] - t["mu"][t["live"]]) / t["sd"][t["live"]] @ t["P"].T / t["sc"]

    def variates(self, X):
        return np.stack([self.white(X[:, m], m) @ self.Wt[m] for m in range(X.shape[1])], 1)

    def rebuild(self, x, m, keep, own_pcs=False):
        """member vector from `keep` shared axes only (or from its own top PCs: the baseline)."""
        t = self.T[m]; W = self.white(x, m)
        if own_pcs: Wh = np.zeros_like(W); Wh[:, :len(keep)] = W[:, :len(keep)]
        else: A = self.Wt[m][:, keep]; Wh = W @ A @ np.linalg.pinv(A.T @ A) @ A.T
        out = np.tile(t["mu"], (len(x), 1)); out[:, t["live"]] += (Wh * t["sc"]) @ t["P"] * t["sd"][t["live"]]; return out


def pair_r(V):
    """V (n, 5, a) -> mean pairwise correlation of the five member variates, per axis."""
    Zs = (V - V.mean(0)) / np.maximum(V.std(0), 1e-12); C = np.einsum("nia,nja->ija", Zs, Zs) / len(V); iu = np.triu_indices(V.shape[1], 1)
    return C[iu].mean(0)


def match(A, B):
    if not A.shape[1] or not B.shape[1]: return np.array([])
    C = np.abs(np.corrcoef(A.T, B.T)[:A.shape[1], A.shape[1]:]); r, c = linear_sum_assignment(-C); return C[r, c]


def ica_rot(S_fit, S_all):
    from sklearn.decomposition import FastICA
    if S_fit.shape[1] < 2: return S_all
    ic = FastICA(S_fit.shape[1], random_state=0, max_iter=2000, whiten="unit-variance").fit(S_fit); A = ic.transform(S_all)
    sk = np.sign(((A - A.mean(0)) ** 3).mean(0)); sk[sk == 0] = 1; return A * sk


def one_layer(E, X, LG, logits, layer, npc, out, tag=""):
    t0 = time.time(); n = len(E); half = Q.folds(E.pid.to_numpy(), k=2, seed=0); res = dict(layer=layer, npc=npc, n_exams=n)
    lbar = {t: LG[:, :, t - 1].mean(1) for t in (1, 6)}; y1, y6 = E.y1.to_numpy(float), np.where(E.study_yr == 0, E.y6, np.nan).astype(float)
    rng = np.random.default_rng(0); Xs = np.stack([X[rng.permutation(n), m] for m in range(5)], 1)          # null: exam order shuffled inside each member
    fits, S_all, dirs = {}, {}, {}
    for hh in (0, 1):
        fit, judge = half == hh, half != hh; sh = Shared().fit(X[fit], npc); r = pair_r(sh.variates(X[judge])); keep = np.flatnonzero(r >= R_SHARED)
        r0 = pair_r(Shared().fit(Xs[fit], npc).variates(Xs[judge]))
        fk = {}
        for name, own in (("shared_axes", False), ("own_top_pcs", True)):
            L0 = np.stack([logits(X[judge, m], m)[0] for m in range(5)], 1); L1 = np.stack([logits(sh.rebuild(X[judge, m], m, keep, own), m)[0] for m in range(5)], 1)
            fk[name] = dict(r_y1=float(np.mean([np.corrcoef(L0[:, m, 0], L1[:, m, 0])[0, 1] for m in range(5)])), r_y6=float(np.mean([np.corrcoef(L0[:, m, 5], L1[:, m, 5])[0, 1] for m in range(5)])),
                            dAUROC_y1=DC.auc(y1[judge], L1[:, :, 0].mean(1)) - DC.auc(y1[judge], L0[:, :, 0].mean(1)),
                            dAUROC_y6=DC.auc(y6[judge], L1[:, :, 5].mean(1)) - DC.auc(y6[judge], L0[:, :, 5].mean(1))) if len(keep) else None
        dirs[hh] = dict(n_shared=int(len(keep)), heldout_pair_r=np.round(r[:20], 3).tolist(), maxvar_eig=np.round(sh.ev[:20], 2).tolist(),
                        null_n_shared=int((r0 >= R_SHARED).sum()), null_max_pair_r=float(r0.max()), function_kept=fk)
        fits[hh] = (sh, keep); S_all[hh] = sh.variates(X)[:, :, keep].mean(1)
    res["halves"] = dirs
    mA, mB = match(S_all[0], S_all[1]), match(ica_rot(S_all[0][half == 0], S_all[0]), ica_rot(S_all[1][half == 1], S_all[1]))
    res["stability_A_vs_B"] = dict(cca=dict(n_ge_0p7=int((mA >= 0.7).sum()), r=np.round(np.sort(mA)[::-1], 2).tolist()), ica=dict(n_ge_0p7=int((mB >= 0.7).sum()), r=np.round(np.sort(mB)[::-1], 2).tolist()))
    # ---- final axes on all dev: the number of shared axes is the smaller of the two half counts
    k = min(dirs[0]["n_shared"], dirs[1]["n_shared"]); res["n_axes_final"] = k
    if k:
        sh = Shared().fit(X, npc); V = sh.variates(X)[:, :, :k]; res["final_pair_r_in_sample"] = np.round(pair_r(V), 3).tolist(); S = V.mean(1); Si = ica_rot(S, S)
        fold = Q.folds(E.pid.to_numpy()); G = D.groups(E); allv = [c for g in G.values() for c in g]; AF = DC.assoc_frame(E, allv); cols = list(AF.columns); rows = []
        for rot, M in (("cca", S), ("ica", Si)):
            ha = S_all[0] if rot == "cca" else ica_rot(S_all[0][half == 0], S_all[0]); hb = S_all[1] if rot == "cca" else ica_rot(S_all[1][half == 1], S_all[1])
            for j in range(k):
                act = M[:, j]; st = [float(np.abs(np.corrcoef(act, hx.T)[0, 1:]).max()) if hx.shape[1] else 0.0 for hx in (ha, hb)]
                lab, tot, shp = DC.shapley_label(E, G, act, fold); hl, av = [], []
                for hh in (0, 1):
                    Sx = E[half == hh].reset_index(drop=True); ah = act[half == hh]
                    hl.append(DC.shapley_label(Sx, G, ah, Q.folds(Sx.pid.to_numpy()))[0]); av.append(DC.assoc_vector(AF[half == hh].reset_index(drop=True), ah))
                ok = np.isfinite(av[0]) & np.isfinite(av[1]); assoc = DC.assoc_vector(AF, act); top = np.argsort(-np.nan_to_num(np.abs(assoc)))[:6]
                T0 = pd.Series(act[(E.study_yr == 0).to_numpy()], index=E.pid[E.study_yr == 0]); T1 = pd.Series(act[(E.study_yr == 1).to_numpy()], index=E.pid[E.study_yr == 1])
                jn = T0.to_frame("a").join(T1.to_frame("b"), how="inner")
                rows.append(dict(rotation=rot, axis=j, r_lbar1=float(np.corrcoef(act, lbar[1])[0, 1]), r_lbar6=float(np.corrcoef(act, lbar[6])[0, 1]), best_r_half_a_fit=st[0], best_r_half_b_fit=st[1],
                                 stable=bool(min(st) >= 0.7), label=lab, cv_r2=tot, **{f"sh_{g}": v for g, v in shp.items()}, label_half_a=hl[0], label_half_b=hl[1],
                                 assoc_half_corr=float(np.corrcoef(av[0][ok], av[1][ok])[0, 1]) if ok.sum() > 3 else np.nan, auc_y1=DC.auc(y1, act), auc_y6=DC.auc(y6, act),
                                 r_T0_T1=float(np.corrcoef(jn.a, jn.b)[0, 1]) if len(jn) > 20 else None, top_assoc="; ".join(f"{cols[i]} {assoc[i]:+.2f}" for i in top)))
        F = pd.DataFrame(rows); F.to_csv(out / f"r2_axes_{layer}{tag}.csv", index=False); summ = {}
        for rot, g in F.groupby("rotation"):
            named = g[g.label.isin(list(G))]; nr = g[np.abs(g.r_lbar6) < 0.5]
            summ[rot] = dict(n=int(len(g)), n_stable=int(g.stable.sum()), labels=g.label.value_counts().to_dict(), median_assoc_half_corr=float(g.assoc_half_corr.median()),
                             label_agreement_named=float((named.label_half_a == named.label_half_b).mean()) if len(named) else None, n_non_risk=int(len(nr)),
                             n_non_risk_stable_named=int((nr.stable & nr.label.isin(list(G)) & (nr.label_half_a == nr.label) & (nr.label_half_b == nr.label)).sum()))
            Mx = S if rot == "cca" else Si; b = np.linalg.lstsq(np.c_[np.ones(n), Mx], np.c_[lbar[1], lbar[6]], rcond=None)[0]; p = np.c_[np.ones(n), Mx] @ b
            summ[rot]["r2_of_lbar1_from_axes"] = float(1 - ((lbar[1] - p[:, 0]) ** 2).sum() / ((lbar[1] - lbar[1].mean()) ** 2).sum()); summ[rot]["r2_of_lbar6_from_axes"] = float(1 - ((lbar[6] - p[:, 1]) ** 2).sum() / ((lbar[6] - lbar[6].mean()) ** 2).sum())
        res["final"] = summ
        if not tag:
            (DATA / "r").mkdir(parents=True, exist_ok=True); pickle.dump(dict(shared=sh, k=k, series_uid=E.series_uid.to_numpy(), S=S, S_ica=Si), open(DATA / "r" / f"r2_shared_{layer}.pkl", "wb"))
    res["minutes"] = round((time.time() - t0) / 60, 1); (out / f"r2_shared_{layer}{tag}.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k_: v for k_, v in res.items() if k_ != "halves"}, indent=1, default=str)); print(json.dumps(res["halves"], default=str), flush=True)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("assembled"); ap.add_argument("heads"); ap.add_argument("out")
    ap.add_argument("--layers", default="h,pooled"); ap.add_argument("--npc", type=int, default=30); ap.add_argument("--rows", type=int, default=0)
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    for layer in a.layers.split(","):
        E, X, LG, logits, _, _ = R1.load(a.assembled, a.heads, layer)
        if a.rows: E, X, LG = E.iloc[:a.rows].reset_index(drop=True), X[:a.rows], LG[:a.rows]
        one_layer(E, X, LG, logits, layer, a.npc, out, tag="_test" if a.rows else ("" if a.npc == 30 else f"_npc{a.npc}"))


if __name__ == "__main__":
    main()
