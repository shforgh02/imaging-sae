"""Validity-ladder metrics for imaging (lean plan v1): K-robust selectivity, chimera, weakest-link validity, C(tau), theta.

All functions take codes Z (n x F, non-negative) on scored tokens plus token labels; no model code here.
"""
from __future__ import annotations

import numpy as np

from .sae import alive, lineage_selectivity


def concept_means(Z, lab, labs, groups=None):
    """F x K matrix of mean |z| per concept; groups (patient ids) given -> mean over patients of the patient mean (patients with >= 1 token)."""
    A = np.abs(Z)
    if groups is None: return np.stack([A[lab == l].mean(0) if (lab == l).any() else np.zeros(Z.shape[1]) for l in labs], 1)
    out = []
    for l in labs:
        ii = np.flatnonzero(lab == l)
        if not len(ii): out.append(np.zeros(Z.shape[1])); continue
        g, inv = np.unique(groups[ii], return_inverse=True); S = np.zeros((len(g), Z.shape[1])); np.add.at(S, inv, A[ii])
        out.append((S / np.bincount(inv)[:, None]).mean(0))
    return np.stack(out, 1)


def selectivity(Z, lab, labs, groups=None, top_other=6):
    """K-robust selectivity: mu* / (mu* + sum of the top_other largest other concept means).
    K <= top_other + 1 and groups None -> exactly saegt lineage_selectivity (bitwise). Returns (sel, argmax concept)."""
    if groups is None and len(labs) <= top_other + 1: return lineage_selectivity(Z, lab, labs)
    M = concept_means(Z, lab, labs, groups); o = np.sort(M, 1)[:, ::-1]; top = o[:, 0]; rest = o[:, 1:1 + top_other].sum(1)
    return top / np.maximum(top + rest, 1e-12), np.array(labs)[M.argmax(1)]


def chimera(Z, lab, labs, own, adj, top_frac=.01, share=.2):
    """feature chimeric if >= share of its top-1% activation mass lies in a class that is neither its own nor adjacent to it.
    adj: dict concept -> set of adjacent concepts. own: assigned concept per feature."""
    out = np.zeros(Z.shape[1], bool); li = {l: i for i, l in enumerate(labs)}
    for f in range(Z.shape[1]):
        z = Z[:, f]; nz = np.flatnonzero(z > 0)
        if not len(nz): continue
        top = nz[np.argsort(-z[nz])[:max(1, int(np.ceil(top_frac * len(z))))]]; w = z[top]; tot = w.sum()
        for l in labs:
            if l == own[f] or l in adj.get(own[f], ()): continue
            if w[lab[top] == l].sum() >= share * tot: out[f] = True; break
    return out


def weakest_link(*scores):
    """per-feature validity v_f = min over the ladder scores (each in [0, 1]; nan -> not evaluable, propagated)."""
    return np.min(np.vstack(scores), 0)


def coverage_curve(v, concept, gated, taus=np.linspace(.5, .9, 9)):
    """C(tau) = number of gated concepts with >= 1 feature of validity >= tau; returns (C array, normalised area = mean C / |gated|)."""
    gated = list(gated); C = np.array([len({c for c, x in zip(concept, v) if np.isfinite(x) and x >= t and c in set(gated)}) for t in taus])
    return C, float(C.mean() / max(len(gated), 1))


def auroc(score, y):
    """Mann-Whitney AUROC (ties = 1/2)."""
    from scipy.stats import rankdata
    y = np.asarray(y, bool); s = np.asarray(score, float); n1, n0 = y.sum(), (~y).sum()
    if n1 == 0 or n0 == 0: return np.nan
    r = rankdata(s); return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def theta(t, y, freq=None, mag=None):
    """H1 estimand: AUROC of twin score t for validity y, plus the frequency/magnitude-adjusted logistic coefficient of t (standardised).
    Returns dict(theta, n_pos, n_neg, estimable (>= 20 per class), beta_t)."""
    t = np.asarray(t, float); y = np.asarray(y, bool); ok = np.isfinite(t); t, y = t[ok], y[ok]
    res = dict(theta=auroc(t, y), n_pos=int(y.sum()), n_neg=int((~y).sum())); res["estimable"] = res["n_pos"] >= 20 and res["n_neg"] >= 20
    if freq is not None and res["estimable"]:
        from sklearn.linear_model import LogisticRegression
        cols = [t] + [np.log(np.maximum(np.asarray(a, float)[ok], 1e-12)) for a in (freq, mag) if a is not None]
        Xd = np.column_stack(cols); Xd = (Xd - Xd.mean(0)) / np.maximum(Xd.std(0), 1e-12)
        res["beta_t"] = float(LogisticRegression(C=1e6, max_iter=2000).fit(Xd, y).coef_[0, 0])
    return res


def twin_scores(Za, Zb, n_max=60000, seed=0):
    """per-feature twin score: Hungarian-matched activation r of each alive feature of Za in Zb (unmatched -> 0). Same rows."""
    from scipy.optimize import linear_sum_assignment
    ia, ib = np.flatnonzero(alive(Za)), np.flatnonzero(alive(Zb)); t = np.full(Za.shape[1], np.nan)
    if not len(ia) or not len(ib): return t
    rows = np.random.default_rng(seed).choice(len(Za), min(len(Za), n_max), replace=False)
    A = Za[rows][:, ia].astype(np.float64); B = Zb[rows][:, ib].astype(np.float64)
    A = (A - A.mean(0)) / np.maximum(A.std(0), 1e-12); B = (B - B.mean(0)) / np.maximum(B.std(0), 1e-12); C = A.T @ B / len(A)
    r, c = linear_sum_assignment(-C); t[ia] = 0.0; t[ia[r]] = np.maximum(C[r, c], 0); return t
