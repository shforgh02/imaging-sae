"""Symmetric cannot-link consensus that also returns its member groups, so a fitted consensus can encode new tokens.
consensus_groups_cl(Zs) uses exactly the grouping of saegt consensus_codes_cl (tests/test_units.py checks the codes are identical).
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import linear_sum_assignment

from .sae import alive


def consensus_groups_cl(Zs, r_thr=.7, min_votes=3, n_rows=30000):
    """returns list of groups [(fit, feature index in that fit), ...] with >= min_votes members (same order as consensus_codes_cl)."""
    rows = np.random.default_rng(0).choice(len(Zs[0]), min(len(Zs[0]), n_rows), replace=False)
    idx = [np.flatnonzero(alive(Z)) for Z in Zs]; off = np.cumsum([0] + [len(i) for i in idx]); N = int(off[-1]); S = len(Zs)
    A = []
    for Z, ii in zip(Zs, idx):
        B = Z[rows][:, ii].astype(np.float64); A.append(((B - B.mean(0)) / np.maximum(B.std(0), 1e-12)).astype(np.float32))
    C, E = {}, []
    for i in range(S):
        for j in range(i + 1, S):
            if not len(idx[i]) or not len(idx[j]): continue
            C[i, j] = A[i].T @ A[j] / len(rows); r, c = linear_sum_assignment(-C[i, j])
            E += [(float(v), off[i] + a, off[j] + b) for a, b, v in zip(r, c, C[i, j][r, c]) if v >= r_thr]
    fit_of = np.repeat(np.arange(S), np.diff(off)); loc = np.arange(N) - off[fit_of]

    def corr(u, v):
        fu, fv = fit_of[u], fit_of[v]
        return C[fu, fv][loc[u], loc[v]] if fu < fv else C[fv, fu][loc[v], loc[u]]
    grp = {a: [a] for a in range(N)}; gid = np.arange(N)
    for v, a, b in sorted(E, key=lambda e: -e[0]):
        ga, gb = gid[a], gid[b]
        if ga == gb: continue
        Ga, Gb = grp[ga], grp[gb]
        if set(fit_of[Ga]) & set(fit_of[Gb]) or np.mean([corr(u, w) for u in Ga for w in Gb]) < r_thr: continue
        grp[ga] = Ga + Gb; gid[Gb] = ga; del grp[gb]
    return [[(int(fit_of[u]), int(idx[fit_of[u]][loc[u]])) for u in G] for G in grp.values() if len(G) >= min_votes]


def encode_groups(Zs, groups):
    """consensus activation = mean of the members' activations (as consensus_codes_cl)."""
    if not groups: return np.zeros((len(Zs[0]), 0), np.float32)
    return np.stack([np.mean([Zs[f][:, j] for f, j in G], 0) for G in groups], 1).astype(np.float32)
