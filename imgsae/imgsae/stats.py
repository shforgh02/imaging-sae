"""Inference helpers (lean plan v1): Nadeau-Bengio corrected resampled t, patient-cluster bootstrap, Holm."""
from __future__ import annotations

import numpy as np
from scipy import stats


def corrected_t(d, test_over_train=1.0, alpha=.05):
    """paired differences d over J random splits; variance inflated by (1/J + n_test/n_train) (half splits: 1).
    Returns dict(mean, se, t, df, p_two, lo, hi) with a (1 - alpha) CI."""
    d = np.asarray(d, float); J = len(d); m = d.mean(); s2 = d.var(ddof=1) if J > 1 else np.nan
    se = np.sqrt((1 / J + test_over_train) * s2); t = m / se if se > 0 else np.inf * np.sign(m); df = J - 1
    q = stats.t.ppf(1 - alpha / 2, df); return dict(mean=m, se=se, t=t, df=df, p_two=float(2 * stats.t.sf(abs(t), df)), lo=m - q * se, hi=m + q * se)


def cluster_bootstrap(values, groups, stat=np.mean, B=2000, alpha=.05, seed=0):
    """percentile CI of stat over per-row values, resampling whole clusters (patients) with replacement."""
    values = np.asarray(values, float); g, inv = np.unique(groups, return_inverse=True); rng = np.random.default_rng(seed)
    S = np.zeros(len(g)); N = np.bincount(inv); np.add.at(S, inv, values)
    if stat is np.mean:
        W = rng.multinomial(len(g), np.full(len(g), 1 / len(g)), size=B); bs = (W @ S) / (W @ N)
    else:
        bs = np.array([stat(np.concatenate([values[inv == j] for j in rng.integers(0, len(g), len(g))])) for _ in range(B)])
    return float(stat(values)), float(np.quantile(bs, alpha / 2)), float(np.quantile(bs, 1 - alpha / 2))


def holm(p):
    """Holm step-down adjusted p-values (same order as input)."""
    p = np.asarray(p, float); o = np.argsort(p); m = len(p); adj = np.empty(m); run = 0.0
    for i, j in enumerate(o): run = max(run, min(1.0, (m - i) * p[j])); adj[j] = run
    return adj
