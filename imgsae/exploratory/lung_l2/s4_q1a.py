"""Lung L2, S4, Q1a (docs/LUNG_L2_PROTOCOL.md section 9.7): what share of Sybil's logit is explained by each known variable group.
Target: mean member logit lbar_1 (all screens) and lbar_6 (baseline screens). Groups N, B, D, I, T (section 9.3).
CV R2 (participant-grouped 5 folds, seed 0) of ridge on all groups; Shapley shares over the 5 groups (32 subset fits, ridge);
gradient boosting total R2 as a sensitivity. Also for exams of participants never diagnosed with lung cancer.
Writes the out-of-fold residual U (lbar minus the all-group ridge prediction) for Q1b.
Gate 9.8 (added 2026-11-16, before any full-dev run): for lbar1_all and lbar6_baseline, a participant-bootstrap 95% interval of each
group's Shapley value (2,000 draws over the fixed out-of-fold predictions) and the Shapley values refitted in each dev half; every
group gives a candidate (> 0, null 0; H-C1 is the T row).
usage: python s4_q1a.py <exams csv> <arrays npz (main)> <out_dir> [tag]
"""
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
import l2_data as D  # noqa: E402

ALPHAS = np.logspace(-2, 4, 13)


def design(E, cols):
    """numeric matrix: object columns one-hot (dev categories), numeric NaN -> dev median."""
    parts = []
    for c in cols:
        v = E[c]
        if not pd.api.types.is_numeric_dtype(v):   # fixed 2026-11-16: pandas 3 reads text as 'str', not object (maker/model were dropped)
            parts.append(pd.get_dummies(v.fillna("NA"), prefix=c, dtype=float))
        else:
            v = pd.to_numeric(v, errors="coerce"); parts.append(v.fillna(v.median()).to_frame(c))
    X = pd.concat(parts, axis=1) if parts else pd.DataFrame(index=E.index)
    return X.loc[:, X.std() > 0].to_numpy(float)


def folds(pid, k=5, seed=0):
    u = np.unique(pid); rng = np.random.default_rng(seed); g = dict(zip(u, rng.permutation(len(u)) % k))
    return np.array([g[p] for p in pid])


def cv_pred(X, y, fold, model="ridge"):
    pred = np.zeros(len(y))
    for f in np.unique(fold):
        tr, te = fold != f, fold == f
        if X.shape[1] == 0: pred[te] = y[tr].mean(); continue
        m = make_pipeline(StandardScaler(), RidgeCV(alphas=ALPHAS)) if model == "ridge" else \
            HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, random_state=0)
        pred[te] = m.fit(X[tr], y[tr]).predict(X[te])
    return pred


def r2(y, p): return float(1 - ((y - p) ** 2).sum() / ((y - y.mean()) ** 2).sum())


def shap_from(val, names):
    n = len(names); sh = {}
    for g in names:
        rest = [h for h in names if h != g]; s = 0.0
        for k in range(len(rest) + 1):
            for S in itertools.combinations(rest, k):
                wgt = math.factorial(k) * math.factorial(n - k - 1) / math.factorial(n)
                s += wgt * (val[frozenset(S) | {g}] - val[frozenset(S)])
        sh[g] = s
    return sh


def shapley(E, G, y, fold, keep_preds=False):
    names = list(G); n = len(names); val = {}; preds = {}
    for k in range(n + 1):
        for S in itertools.combinations(names, k):
            cols = [c for g in S for c in G[g]]
            if S: preds[frozenset(S)] = cv_pred(design(E, cols), y, fold)
            val[frozenset(S)] = r2(y, preds[frozenset(S)]) if S else 0.0
    sh = shap_from(val, names)
    out = (sh, val[frozenset(names)], {"+".join(sorted(S)) or "none": v for S, v in val.items() if len(S) == 1})
    return out + (preds,) if keep_preds else out


def shapley_ci(y, preds, names, pid, n_boot=2000, seed=0):
    """participant-bootstrap 95% interval of each group's Shapley value, from the fixed out-of-fold predictions (no refit per draw)."""
    pid = np.asarray(pid); u, inv = np.unique(pid, return_inverse=True); order = np.argsort(inv, kind="stable"); cnt = np.bincount(inv)
    rows = [order[s:s + c] for s, c in zip(np.r_[0, np.cumsum(cnt)[:-1]], cnt)]; rng = np.random.default_rng(seed); draws = {g: [] for g in names}
    for _ in range(n_boot):
        t = np.concatenate([rows[i] for i in rng.integers(0, len(rows), len(rows))])
        val = {S: r2(y[t], p[t]) for S, p in preds.items()}; val[frozenset()] = 0.0
        for g, v in shap_from(val, names).items(): draws[g].append(v)
    return {g: [float(x) for x in np.percentile(d, [2.5, 97.5])] for g, d in draws.items()}


def main():
    ex_p, arr_p, out_d = sys.argv[1], sys.argv[2], Path(sys.argv[3]); tag = sys.argv[4] if len(sys.argv) > 4 else "dev"
    E = pd.read_csv(ex_p, dtype={"pid": str}, low_memory=False)
    A = np.load(arr_p, allow_pickle=True)
    pos = {u: i for i, u in enumerate(A["series_uid"])}
    lg = A["logit"][[pos[u] for u in E.series_uid]]          # (n, 5, 6)
    E["lbar1"], E["lbar6"] = lg[:, :, 0].mean(1), lg[:, :, 5].mean(1)
    G = D.groups(E); res = {"groups": {k: len(v) for k, v in G.items()}}
    U = pd.DataFrame({"series_uid": E.series_uid}); cands = []; half = folds(E.pid.to_numpy(), k=2, seed=0)
    for name, ycol, mask in (("lbar1_all", "lbar1", np.ones(len(E), bool)), ("lbar6_baseline", "lbar6", (E.study_yr == 0).to_numpy()),
                             ("lbar1_never_cancer", "lbar1", E.dt.isna().to_numpy()), ("lbar6_baseline_never_cancer", "lbar6", ((E.study_yr == 0) & E.dt.isna()).to_numpy())):
        S = E[mask].reset_index(drop=True); y = S[ycol].to_numpy(float); fold = folds(S.pid.to_numpy())
        sh, tot, single, preds = shapley(S, G, y, fold, keep_preds=True)
        allc = [c for g in G.values() for c in g]
        Xall = design(S, allc)
        p_r = cv_pred(Xall, y, fold); p_b = cv_pred(Xall, y, fold, "boost")
        res[name] = dict(n_exams=int(len(S)), participants=int(S.pid.nunique()), cv_r2_ridge_all=tot, cv_r2_boost_all=r2(y, p_b),
                         shapley=sh, shapley_share_of_r2={g: (v / tot if tot > 0 else None) for g, v in sh.items()},
                         single_group_r2=single, unexplained=1 - tot)
        if name in ("lbar1_all", "lbar6_baseline"):
            U.loc[np.flatnonzero(mask), f"U_{ycol}"] = y - p_r
            # intervals and dev halves for gate 9.8 (added 2026-11-16, before any full-dev run; point estimates unchanged)
            ci = shapley_ci(y, preds, list(G), S.pid.to_numpy()); hv = half[mask]; hh = {}
            for k in (0, 1):
                Sk = S[hv == k].reset_index(drop=True); hh[k] = shapley(Sk, G, Sk[ycol].to_numpy(float), folds(Sk.pid.to_numpy()))[0]
            res[name]["shapley_ci95"] = ci; res[name]["shapley_halves"] = [hh[0], hh[1]]
            cnt = dict(exams=int(len(S)), participants=int(S.pid.nunique()))
            for g in G:
                cands.append(dict(id=f"Q1a_shapley_{g}_{name}", source="Q1a (9.7)", statistic=f"Shapley CV R2 of group {g} for {ycol}",
                                  population="all screens" if ycol == "lbar1" else "baseline", direction=">", null=0.0, est=sh[g], lo=ci[g][0], hi=ci[g][1],
                                  half_a=hh[0][g], half_b=hh[1][g], counts=cnt, feature_based=False, partly_seen=False, qualification=None,
                                  note="H-C1 template (technical share) for T; interval from fixed out-of-fold predictions"))
    res["candidates"] = cands
    out_d.mkdir(parents=True, exist_ok=True)
    (out_d / f"s4_q1a_{tag}.json").write_text(json.dumps(res, indent=1))
    U.to_csv(out_d / f"s4_q1a_U_{tag}.csv", index=False)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
