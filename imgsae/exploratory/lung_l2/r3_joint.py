"""Lung L2, step R1b (rescue scouting; dev only, exploratory; ADDED after R1 was seen, logged before it ran): one joint dictionary for
the whole ensemble. The five member vectors of an exam are joined (z-scored per unit) and decomposed together, so a feature is a feature
of the ensemble (the model that is really used), and every unit counts by its variance (R1 whitened 30 PCs per member, which gave the
small noisy PCs the same weight as the large ones).
Arms: joint PCA ("pca") and joint PCA followed by an ICA rotation ("ica", the "group ICA" used for brain imaging).
usage: python r3_joint.py <assembled dir> <heads npz> <out dir> [--layers h,pooled] [--K 4,8,12,16,32] [--rows N (test only)]
Marks (the S4 marks, moved to the ensemble level; thresholds unchanged):
 V1' function kept: each member's vector is rebuilt from the K joint features, Sybil's head gives the logits; fitted on one half,
     judged on the other, both directions (r >= 0.98 for year 1 and 6, AUROC change <= 0.005).
 V2' stability: features fitted on half A against features fitted on half B (activation correlation on all exams, Hungarian); pass if
     at least half of the K features match at |r| >= 0.70.
 V3' shared: a feature is the sum of five member parts. It is SHARED if the mean pairwise correlation of the five parts on the other
     half is >= 0.70. Pass if at least K/4 features are shared (in both directions; the smaller count is used).
 V4  naming repeats in the two halves, as S4 (same Shapley rule).
Writes <out>/r3_joint_<layer>_<arm>_K<K>.json and the feature table (.csv); the all-dev fit goes to <L2_S4_DATA>/r/ (outside git).
"""
import argparse
import json
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, r"D:\Shayan\imgsae")
import l2_data as D  # noqa: E402
import r1_arms as R1  # noqa: E402
import r2_shared as R2  # noqa: E402
import s4_decomp as DC  # noqa: E402
import s4_q1a as Q  # noqa: E402


class Joint:
    """joint z-scored vector Zc (n, sum of live units); feature activations A = Zc @ Enc; rebuilt Zc = A @ Dec."""

    def prep(self, X):
        self.T = []
        for m in range(X.shape[1]):
            x = X[:, m]; mu, sd = x.mean(0), x.std(0); live = sd >= 1e-6; self.T.append(dict(mu=mu, sd=sd, live=live))
        self.cut = np.r_[0, np.cumsum([t["live"].sum() for t in self.T])]; Zc = self.z(X)
        _, S, Vt = np.linalg.svd(Zc, full_matrices=False); self.S, self.Vt, self.n = S, Vt, len(Zc); self.var_share = S ** 2 / (S ** 2).sum(); return self, Zc

    def z(self, X):
        return np.hstack([(X[:, m][:, t["live"]] - t["mu"][t["live"]]) / t["sd"][t["live"]] for m, t in enumerate(self.T)])

    def set(self, K, arm, Zc):
        V = self.Vt[:K]; sc = self.S[:K] / np.sqrt(self.n); self.K = K
        if arm == "pca": self.Enc, self.Dec = V.T, V
        else:
            from sklearn.decomposition import FastICA
            W0 = Zc @ V.T / sc; ic = FastICA(random_state=0, max_iter=3000, whiten=False).fit(W0); U = ic.components_     # comp = W0 @ U.T
            sk = np.sign((((W0 @ U.T) - (W0 @ U.T).mean(0)) ** 3).mean(0)); sk[sk == 0] = 1; U = U * sk[:, None]
            self.Enc = (V.T / sc) @ U.T; self.Dec = np.linalg.pinv(U.T) * sc @ V
        return self

    def encode(self, X): return self.z(X) @ self.Enc

    def parts(self, X):
        Zc = self.z(X); return np.stack([Zc[:, self.cut[m]:self.cut[m + 1]] @ self.Enc[self.cut[m]:self.cut[m + 1]] for m in range(X.shape[1])], 1)   # (n, 5, K)

    def rebuild(self, X, m):
        t = self.T[m]; Zh = (self.encode(X) @ self.Dec)[:, self.cut[m]:self.cut[m + 1]]
        out = np.tile(t["mu"], (len(X), 1)); out[:, t["live"]] += Zh * t["sd"][t["live"]]; return out


def one(E, X, LG, logits, layer, Ks, arms, out, tag=""):
    n = len(E); half = Q.folds(E.pid.to_numpy(), k=2, seed=0); fold = Q.folds(E.pid.to_numpy())
    lbar = {t: LG[:, :, t - 1].mean(1) for t in (1, 6)}; y1, y6 = E.y1.to_numpy(float), np.where(E.study_yr == 0, E.y6, np.nan).astype(float)
    G = D.groups(E); allv = [c for g in G.values() for c in g]; AF = DC.assoc_frame(E, allv); cols = list(AF.columns)
    L0 = np.stack([logits(X[:, m], m)[0] for m in range(5)], 1)
    base = {hh: Joint().prep(X[half == hh]) for hh in (0, 1)}; full = Joint().prep(X)
    print(f"{layer}: joint PCA, share of variance of the first 12 components: {np.round(full[0].var_share[:12], 3).tolist()}", flush=True)
    for K in Ks:
        for arm in arms:
            name = f"{layer}_{arm}_K{K}{tag}"
            if (out / f"r3_joint_{name}.json").exists() and not tag: print("done before:", name, flush=True); continue
            t0 = time.time(); res = dict(layer=layer, arm=arm, K=K, n_exams=n); Ah, sh, sh5, L1 = {}, [], [], np.zeros_like(L0)
            for hh in (0, 1):
                J = base[hh][0].set(K, arm, base[hh][1]); judge = half != hh; Ah[hh] = J.encode(X); r = R2.pair_r(J.parts(X[judge])); sh.append(int((r >= 0.70).sum())); sh5.append(int((r >= 0.50).sum()))
                for m in range(5): L1[judge, m] = logits(J.rebuild(X[judge], m), m)[0]
            rr = {t: float(np.mean([np.corrcoef(L0[:, m, t - 1], L1[:, m, t - 1])[0, 1] for m in range(5)])) for t in (1, 6)}
            dA1 = DC.auc(y1, L1[:, :, 0].mean(1)) - DC.auc(y1, L0[:, :, 0].mean(1)); dA6 = DC.auc(y6, L1[:, :, 5].mean(1)) - DC.auc(y6, L0[:, :, 5].mean(1))
            res["V1"] = dict(r_y1=rr[1], r_y6=rr[6], dAUROC_y1=dA1, dAUROC_y6=dA6, r_lbar1=float(np.corrcoef(L0[:, :, 0].mean(1), L1[:, :, 0].mean(1))[0, 1]),
                             pass_=bool(rr[1] >= 0.98 and rr[6] >= 0.98 and abs(dA1) <= 0.005 and abs(dA6) <= 0.005))
            mt = R2.match(Ah[0], Ah[1]); res["V2"] = dict(n_matched=int((mt >= 0.7).sum()), median_r=float(np.median(mt)), pass_=bool((mt >= 0.7).sum() >= 0.5 * K))
            res["V3"] = dict(n_shared=min(sh), per_direction=sh, n_shared_at_0p5=min(sh5), pass_=bool(min(sh) >= max(1, round(0.25 * K))))
            J = full[0].set(K, arm, full[1]); A = J.encode(X); pr = R2.pair_r(J.parts(X)); rows = []
            for j in range(K):
                act = A[:, j]; st = [float(np.abs(np.corrcoef(act, Ah[hh].T)[0, 1:]).max()) for hh in (0, 1)]
                lab, tot, shp = DC.shapley_label(E, G, act, fold); hl, av = [], []
                for hh in (0, 1):
                    Sx = E[half == hh].reset_index(drop=True); ah = act[half == hh]
                    hl.append(DC.shapley_label(Sx, G, ah, Q.folds(Sx.pid.to_numpy()))[0]); av.append(DC.assoc_vector(AF[half == hh].reset_index(drop=True), ah))
                ok = np.isfinite(av[0]) & np.isfinite(av[1]); assoc = DC.assoc_vector(AF, act); top = np.argsort(-np.nan_to_num(np.abs(assoc)))[:6]
                T0 = pd.Series(act[(E.study_yr == 0).to_numpy()], index=E.pid[E.study_yr == 0]); T1 = pd.Series(act[(E.study_yr == 1).to_numpy()], index=E.pid[E.study_yr == 1])
                jn = T0.to_frame("a").join(T1.to_frame("b"), how="inner")
                rows.append(dict(feature=j, pair_r_in_sample=float(pr[j]), shared=bool(pr[j] >= 0.70), stable=bool(min(st) >= 0.7), r_lbar1=float(np.corrcoef(act, lbar[1])[0, 1]), r_lbar6=float(np.corrcoef(act, lbar[6])[0, 1]),
                                 label=lab, cv_r2=tot, **{f"sh_{g}": v for g, v in shp.items()}, label_half_a=hl[0], label_half_b=hl[1],
                                 assoc_half_corr=float(np.corrcoef(av[0][ok], av[1][ok])[0, 1]) if ok.sum() > 3 else np.nan, auc_y1=DC.auc(y1, act), auc_y6=DC.auc(y6, act),
                                 r_T0_T1=float(np.corrcoef(jn.a, jn.b)[0, 1]) if len(jn) > 20 else None, top_assoc="; ".join(f"{cols[i]} {assoc[i]:+.2f}" for i in top)))
            F = pd.DataFrame(rows); F.to_csv(out / f"r3_joint_{name}_features.csv", index=False); named = F[F.label.isin(list(G))]
            agree = float((named.label_half_a == named.label_half_b).mean()) if len(named) else 0.0
            res["V4"] = dict(median_assoc_half_corr=float(F.assoc_half_corr.median()), label_agreement_named=agree, n_named=int(len(named)), pass_=bool(F.assoc_half_corr.median() >= 0.70 and agree >= 0.70))
            res["valid"] = bool(res["V1"]["pass_"] and res["V2"]["pass_"] and res["V3"]["pass_"] and res["V4"]["pass_"]); res["labels"] = F.label.value_counts().to_dict()
            good = F[F.shared & F.stable & F.label.isin(list(G)) & (F.label_half_a == F.label) & (F.label_half_b == F.label)]
            res["good_features"] = dict(n_shared_stable_named=int(len(good)), of_these_non_risk=int((np.abs(good.r_lbar6) < 0.5).sum()), labels=good.label.value_counts().to_dict())
            res["minutes"] = round((time.time() - t0) / 60, 1); (out / f"r3_joint_{name}.json").write_text(json.dumps(res, indent=1, default=str))
            if not tag: pickle.dump(dict(T=J.T, cut=J.cut, Enc=J.Enc, Dec=J.Dec, series_uid=E.series_uid.to_numpy(), A=A), open(R2.DATA / "r" / f"r3_joint_{name}.pkl", "wb"))
            v1, v4 = res["V1"], res["V4"]
            print(f"{name:20s} V1 r1 {v1['r_y1']:.3f} r6 {v1['r_y6']:.3f} dA {dA1:+.4f}/{dA6:+.4f} {'P' if v1['pass_'] else 'F'} | V2 {res['V2']['n_matched']}/{K} {'P' if res['V2']['pass_'] else 'F'}"
                  f" | V3 shared {sh} (at 0.5: {sh5}) {'P' if res['V3']['pass_'] else 'F'} | V4 corr {v4['median_assoc_half_corr']:.2f} agree {agree:.2f} {'P' if v4['pass_'] else 'F'}"
                  f" | valid {res['valid']} | {res['labels']} | good {res['good_features']} | {res['minutes']} min", flush=True)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("assembled"); ap.add_argument("heads"); ap.add_argument("out")
    ap.add_argument("--layers", default="h,pooled"); ap.add_argument("--K", default="4,8,12,16,32"); ap.add_argument("--arms", default="pca,ica"); ap.add_argument("--rows", type=int, default=0)
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True); (R2.DATA / "r").mkdir(parents=True, exist_ok=True)
    for layer in a.layers.split(","):
        E, X, LG, logits, _, _ = R1.load(a.assembled, a.heads, layer)
        if a.rows: E, X, LG = E.iloc[:a.rows].reset_index(drop=True), X[:a.rows], LG[:a.rows]
        one(E, X, LG, logits, layer, [int(k) for k in a.K.split(",")], a.arms.split(","), out, tag="_test" if a.rows else "")


if __name__ == "__main__":
    main()
