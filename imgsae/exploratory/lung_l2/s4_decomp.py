"""Lung L2, S4: decomposition arms, validity V1-V4, families, naming, group shares (docs/LUNG_L2_PROTOCOL.md 9.2, 9.4-9.6, 9.7 Q1b).
usage: python s4_decomp.py <exams csv> <arrays npz (main)> <heads npz> <out_dir> [--K 64] [--arms raw,pca,ica,nmf,kmeans,sae] [--device cpu]
       [--v2-members 0,1,2,3,4] [--tag dev]
Writes <out_dir>/s4_decomp_<tag>_<arm>_K<K>.json, s4_families_<tag>_<arm>_K<K>.csv, s4_contrib_<tag>_<arm>_K<K>.npz, and the fitted
seed-0 arms (pickle, for freezing at S5) under <out_dir>/../../../imgsae_data/lung_l2/arms/.
"""
import argparse
import hashlib
import itertools
import json
import math
import os
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, r"D:\Shayan\imgsae")
import l2_data as D  # noqa: E402
import s4_core as C  # noqa: E402
import s4_q1a as Q  # noqa: E402
from imgsae import sae as SAE  # noqa: E402

DATA = Path(os.environ.get("L2_S4_DATA", r"D:\Shayan\imgsae_data\lung_l2"))   # same folder as s4_common.DATA (tests point it elsewhere)
SEEDED = ("ica", "nmf", "kmeans", "sae")
DENSE = ("raw", "pca", "ica")          # signed codes: matching across members uses |r| and aligns signs


def auc(y, s):
    m = np.isfinite(y) & np.isfinite(s)
    return float(roc_auc_score(y[m], s[m])) if m.sum() and len(np.unique(y[m])) == 2 else None


def families_signed(As, absval):
    """families across members. Dense arms (signed codes): every member's features are first sign-aligned to member 0 by the sign of
    their best |r| match, then the signed routine runs; the signs are returned so family activations use the aligned signs."""
    if not absval:
        fams = C.families(As); return [(f, {m: 1.0 for m in f}) for f in fams]
    ref = C.zscore(As[0]); out = [As[0]]; signs = [np.ones(As[0].shape[1])]
    for A in As[1:]:
        Z = C.zscore(A); Cm = Z.T @ ref / len(Z)                       # (K_m, K_0)
        j = np.abs(Cm).argmax(1); s = np.sign(Cm[np.arange(len(j)), j]); s[s == 0] = 1
        out.append(A * s); signs.append(s)
    fams = C.families(out)
    return [(f, {m: float(signs[m][i]) for m, i in f.items()}) for f in fams]


def fam_act(As, fam, sg):
    return np.mean([sg[m] * C.zscore(As[m][:, [f]])[:, 0] for m, f in fam.items()], 0)


def shapley_label(E, G, a, fold):
    """group label of one family activation (protocol 9.6): CV R2 (ridge) on all groups, Shapley shares over the 5 groups."""
    names = list(G); n = len(names); val = {}
    X = {g: Q.design(E, G[g]) for g in names}
    for k in range(n + 1):
        for S in itertools.combinations(names, k):
            val[frozenset(S)] = Q.r2(a, Q.cv_pred(np.hstack([X[g] for g in S]), a, fold)) if S else 0.0
    tot = val[frozenset(names)]; sh = {}
    for g in names:
        rest = [h for h in names if h != g]; s = 0.0
        for k in range(len(rest) + 1):
            for S in itertools.combinations(rest, k):
                s += math.factorial(k) * math.factorial(n - k - 1) / math.factorial(n) * (val[frozenset(S) | {g}] - val[frozenset(S)])
        sh[g] = s
    if tot < 0.10: lab = "unnamed"
    else:
        g = max(sh, key=sh.get); lab = g if sh[g] >= 0.5 * tot else "mixed"
    return lab, tot, sh


def assoc_frame(E, cols):
    """numeric frame of the naming variables: text columns (maker, model) one-hot, as s4_q1a.design (fixed 2026-11-16, before any
    full-dev run: under pandas 3 text columns are 'str', and pd.to_numeric turned them into missing values)."""
    parts = {}
    for c in cols:
        v = E[c]
        if not pd.api.types.is_numeric_dtype(v):
            for lev, d in pd.get_dummies(v.fillna("NA"), prefix=c, dtype=float).items(): parts[lev] = d.to_numpy()
        else: parts[c] = pd.to_numeric(v, errors="coerce").to_numpy(float)
    return pd.DataFrame(parts)


def assoc_vector(X, a):
    """protocol 9.6: Spearman rho; binary variables as rank-biserial r = 2 AUROC - 1 (fixed 2026-11-16; Spearman before)."""
    v = []
    for c in X.columns:
        x = X[c].to_numpy(float); m = np.isfinite(x); u = np.unique(x[m])
        if m.sum() <= 20 or len(u) < 2: v.append(np.nan)
        elif len(u) == 2: v.append(2 * roc_auc_score(x[m] == u[1], a[m]) - 1)
        else: v.append(spearmanr(x[m], a[m])[0])
    return np.array(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exams"); ap.add_argument("arrays"); ap.add_argument("heads"); ap.add_argument("out")
    ap.add_argument("--K", type=int, default=64); ap.add_argument("--arms", default=",".join(C.ARMS)); ap.add_argument("--device", default="cpu")
    ap.add_argument("--v2-members", default="0,1,2,3,4"); ap.add_argument("--tag", default="dev"); ap.add_argument("--skip-v2", action="store_true")
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    arm_dir = DATA / "arms"; arm_dir.mkdir(parents=True, exist_ok=True)
    E = pd.read_csv(a.exams, dtype={"pid": str}, low_memory=False)
    Z = np.load(a.arrays, allow_pickle=True); pos = {u: i for i, u in enumerate(Z["series_uid"])}
    idx = np.array([pos[u] for u in E.series_uid]); Hh = Z["h"][idx].astype(np.float64); LG = Z["logit"][idx].astype(np.float64)
    heads = C.load_heads(a.heads); n = len(E)
    lbar = {t: LG[:, :, t - 1].mean(1) for t in (1, 6)}
    y1, y6 = E.y1.to_numpy(float), np.where(E.study_yr == 0, E.y6, np.nan).astype(float)
    fold = Q.folds(E.pid.to_numpy()); half = Q.folds(E.pid.to_numpy(), k=2, seed=0)
    G = D.groups(E); allv = [c for g in G.values() for c in g]; AF = assoc_frame(E, allv); allv_num = list(AF.columns)
    for t in (1, 6):   # identity check: saved logits equal Sybil's head on saved h
        rec = np.stack([C.head_logits(Hh[:, m], heads[m])[0][:, t - 1] for m in range(5)], 1)
        assert np.abs(rec - LG[:, :, t - 1]).max() < 1e-3
    for arm in a.arms.split(","):
        res = dict(arm=arm, K=a.K, n_exams=n, participants=int(E.pid.nunique()))
        w6 = [C.eff_weights(C.head_logits(Hh[:, m], heads[m])[1], heads[m], 6)[0].mean(0) for m in range(5)]
        # ---- V1 function kept (held-out folds)
        L0 = {t: np.zeros((n, 5)) for t in (1, 6)}; L1 = {t: np.zeros((n, 5)) for t in (1, 6)}
        for f in range(5):
            tr, te = fold != f, fold == f
            for m in range(5):
                l0, l1 = C.v1_fold(Hh[tr, m], Hh[te, m], heads[m], arm, a.K, 0, w_ref=w6[m], device=a.device)
                for t in (1, 6): L0[t][te, m] = l0[:, t - 1]; L1[t][te, m] = l1[:, t - 1]
        r = {t: float(np.mean([np.corrcoef(L0[t][:, m], L1[t][:, m])[0, 1] for m in range(5)])) for t in (1, 6)}
        dA1 = auc(y1, L1[1].mean(1)) - auc(y1, L0[1].mean(1)); dA6 = auc(y6, L1[6].mean(1)) - auc(y6, L0[6].mean(1))
        res["V1"] = dict(r_y1=r[1], r_y6=r[6], dAUROC_y1=dA1, dAUROC_y6=dA6,
                         pass_=bool(r[1] >= 0.98 and r[6] >= 0.98 and abs(dA1) <= 0.005 and abs(dA6) <= 0.005))
        # ---- seed-0 fits on all dev, per member
        arms = [C.Arm(arm, a.K, 0, a.device).fit(Hh[:, m], w_ref=w6[m]) for m in range(5)]
        As = [ar.encode(Hh[:, m]) for m, ar in enumerate(arms)]
        # ---- V2 seed stability (consensus 0-4 vs 10-14) and anchored stability of seed-0 features
        stable = [np.ones(a.K, bool) for _ in range(5)]
        if arm in SEEDED and not a.skip_v2:
            v2 = []
            for m in map(int, a.v2_members.split(",")):
                Za = [As[m]] + [C.Arm(arm, a.K, s, a.device).fit(Hh[:, m]).encode(Hh[:, m]) for s in (1, 2, 3, 4)]
                Zb = [C.Arm(arm, a.K, s, a.device).fit(Hh[:, m]).encode(Hh[:, m]) for s in (10, 11, 12, 13, 14)]
                if arm == "ica":
                    Za = [np.abs(x) for x in Za]; Zb = [np.abs(x) for x in Zb]      # sign-free comparison for ICA
                ca, _ = SAE.consensus_codes_cl(Za); cb, _ = SAE.consensus_codes_cl(Zb)
                share, med = C.act_match(ca, cb) if ca.shape[1] and cb.shape[1] else (0.0, 0.0)
                votes = np.ones(a.K)
                for Zs_ in Za[1:]:
                    i, j, v = C.match(Za[0], Zs_); votes[i[v >= 0.7]] += 1
                stable[m] = votes >= 3
                v2.append(dict(member=m, n_cons_a=int(ca.shape[1]), n_cons_b=int(cb.shape[1]), share=share, median_r=med, n_stable_seed0=int(stable[m].sum())))
            res["V2"] = dict(per_member=v2, share=float(np.mean([x["share"] for x in v2])), median_r=float(np.mean([x["median_r"] for x in v2])))
            res["V2"]["pass_"] = bool(res["V2"]["median_r"] >= 0.70 and res["V2"]["share"] >= 0.50)
        else:
            res["V2"] = dict(pass_=True, note="deterministic arm" if arm not in SEEDED else "skipped")
        # ---- V3 families across members
        fams = families_signed(As, arm in DENSE)
        res["V3"] = dict(n_families=len(fams), pass_=bool(len(fams) >= max(1, round(0.25 * a.K))))
        # ---- naming, V4 split halves, per-family stats
        rows, labs_h = [], []
        for k, (fam, sg) in enumerate(fams):
            act = fam_act(As, fam, sg)
            lab, tot, sh = shapley_label(E, G, act, fold)
            hl, av = [], []
            for hh in (0, 1):
                S = E[half == hh].reset_index(drop=True); ah = act[half == hh]; fh = Q.folds(S.pid.to_numpy())
                hl.append(shapley_label(S, G, ah, fh)[0]); av.append(assoc_vector(AF[half == hh].reset_index(drop=True), ah))
            ok = np.isfinite(av[0]) & np.isfinite(av[1])
            rho = float(np.corrcoef(av[0][ok], av[1][ok])[0, 1]) if ok.sum() > 3 else np.nan
            assoc = assoc_vector(AF, act); top = np.argsort(-np.nan_to_num(np.abs(assoc)))[:5]
            T0 = pd.Series(act[(E.study_yr == 0).to_numpy()], index=E.pid[E.study_yr == 0]); T1 = pd.Series(act[(E.study_yr == 1).to_numpy()], index=E.pid[E.study_yr == 1])
            j = T0.to_frame("a").join(T1.to_frame("b"), how="inner")
            rows.append(dict(family=k, members=json.dumps({str(m): int(f) for m, f in fam.items()}), n_members=len(fam), label=lab, cv_r2=tot,
                             **{f"sh_{g}": v for g, v in sh.items()}, label_half_a=hl[0], label_half_b=hl[1], assoc_half_corr=rho,
                             top_assoc="; ".join(f"{allv_num[i]} {assoc[i]:+.2f}" for i in top),
                             auc_y1=auc(y1, act), auc_y6=auc(y6, act), auc_y2=auc(np.where(E.study_yr == 0, E.y2, np.nan).astype(float), act),
                             r_T0_T1=float(np.corrcoef(j.a, j.b)[0, 1]) if len(j) > 20 else None, active_share=float(np.mean(np.abs(act - np.median(act)) > 1e-9))))
        F = pd.DataFrame(rows)
        named = F[F.label.isin(list(G))] if len(F) else F
        agree = float((named.label_half_a == named.label_half_b).mean()) if len(named) else 0.0
        res["V4"] = dict(median_assoc_half_corr=float(F.assoc_half_corr.median()) if len(F) else None, label_agreement_named=agree,
                         pass_=bool(len(F) and F.assoc_half_corr.median() >= 0.70 and agree >= 0.70))
        res["valid"] = bool(res["V1"]["pass_"] and res["V2"]["pass_"] and res["V3"]["pass_"] and res["V4"]["pass_"])
        res["audit_yield_named_replicated"] = int(len(named))
        res["labels"] = F.label.value_counts().to_dict() if len(F) else {}
        # ---- exact contributions -> group shares of lbar_t (Q1b)
        fam_of = [dict() for _ in range(5)]
        for k, (fam, sg) in enumerate(fams):
            for m, f in fam.items(): fam_of[m][f] = k
        lab_of = dict(zip(F.family, F.label)) if len(F) else {}
        shares, store = {}, {}
        for t in (1, 6):
            comp = {}
            for m in range(5):
                ic, ct, rs = C.contributions(Hh[:, m], As[m], arms[m], heads[m], t)
                comp["intercept"] = comp.get("intercept", 0) + ic / 5; comp["residual"] = comp.get("residual", 0) + rs / 5
                for i in range(ct.shape[1]):
                    key = lab_of.get(fam_of[m].get(i), "unreplicated") if i in fam_of[m] else "unreplicated"
                    comp[key] = comp.get(key, 0) + ct[:, i] / 5
            tot_l = sum(comp.values())
            assert np.abs(tot_l - lbar[t]).max() < 1e-3
            v = np.var(lbar[t], ddof=1); shares[f"lbar{t}"] = {k: float(np.cov(x, lbar[t])[0, 1] / v) for k, x in comp.items()}   # ddof 1 both (fixed 2026-11-16)
            for k, x in comp.items(): store[f"t{t}_{k}"] = x
        res["group_shares"] = shares
        tag = f"{a.tag}_{arm}_K{a.K}"
        (out / f"s4_decomp_{tag}.json").write_text(json.dumps(res, indent=1, default=str))
        F.to_csv(out / f"s4_families_{tag}.csv", index=False)
        np.savez(DATA / f"s4_contrib_{tag}.npz", series_uid=E.series_uid.to_numpy(), **store,
                 **{f"family_{k}": fam_act(As, fam, sg) for k, (fam, sg) in enumerate(fams)})
        pk = arm_dir / f"arms_{tag}.pkl"; pickle.dump(dict(arms=arms, families=fams), open(pk, "wb"))
        res["arms_pickle_sha256"] = hashlib.sha256(pk.read_bytes()).hexdigest()
        (out / f"s4_decomp_{tag}.json").write_text(json.dumps(res, indent=1, default=str))
        print(json.dumps({k: res[k] for k in ("arm", "V1", "V3", "V4", "valid", "audit_yield_named_replicated", "labels")}, indent=1, default=str), flush=True)


if __name__ == "__main__":
    main()
