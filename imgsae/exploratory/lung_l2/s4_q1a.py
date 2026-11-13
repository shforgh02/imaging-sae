"""Lung L2, S4, Q1a (docs/LUNG_L2_PROTOCOL.md section 9.7): what share of Sybil's logit is explained by each known variable group.
Target: mean member logit lbar_1 (all screens) and lbar_6 (baseline screens). Groups N, B, D, I, T (section 9.3).
CV R2 (participant-grouped 5 folds, seed 0) of ridge on all groups; Shapley shares over the 5 groups (32 subset fits, ridge);
gradient boosting total R2 as a sensitivity. Also for exams of participants never diagnosed with lung cancer.
Writes the out-of-fold residual U (lbar minus the all-group ridge prediction) for Q1b.
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
        if v.dtype == object:
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


def shapley(E, G, y, fold):
    names = list(G); n = len(names); val = {}
    for k in range(n + 1):
        for S in itertools.combinations(names, k):
            cols = [c for g in S for c in G[g]]
            val[frozenset(S)] = r2(y, cv_pred(design(E, cols), y, fold)) if S else 0.0
    sh = {}
    for g in names:
        rest = [h for h in names if h != g]; s = 0.0
        for k in range(len(rest) + 1):
            for S in itertools.combinations(rest, k):
                wgt = math.factorial(k) * math.factorial(n - k - 1) / math.factorial(n)
                s += wgt * (val[frozenset(S) | {g}] - val[frozenset(S)])
        sh[g] = s
    return sh, val[frozenset(names)], {"+".join(sorted(S)) or "none": v for S, v in val.items() if len(S) == 1}


def main():
    ex_p, arr_p, out_d = sys.argv[1], sys.argv[2], Path(sys.argv[3]); tag = sys.argv[4] if len(sys.argv) > 4 else "dev"
    E = pd.read_csv(ex_p, dtype={"pid": str}, low_memory=False)
    A = np.load(arr_p, allow_pickle=True)
    pos = {u: i for i, u in enumerate(A["series_uid"])}
    lg = A["logit"][[pos[u] for u in E.series_uid]]          # (n, 5, 6)
    E["lbar1"], E["lbar6"] = lg[:, :, 0].mean(1), lg[:, :, 5].mean(1)
    G = D.groups(E); res = {"groups": {k: len(v) for k, v in G.items()}}
    U = pd.DataFrame({"series_uid": E.series_uid})
    for name, ycol, mask in (("lbar1_all", "lbar1", np.ones(len(E), bool)), ("lbar6_baseline", "lbar6", (E.study_yr == 0).to_numpy()),
                             ("lbar1_never_cancer", "lbar1", E.dt.isna().to_numpy()), ("lbar6_baseline_never_cancer", "lbar6", ((E.study_yr == 0) & E.dt.isna()).to_numpy())):
        S = E[mask].reset_index(drop=True); y = S[ycol].to_numpy(float); fold = folds(S.pid.to_numpy())
        sh, tot, single = shapley(S, G, y, fold)
        allc = [c for g in G.values() for c in g]
        Xall = design(S, allc)
        p_r = cv_pred(Xall, y, fold); p_b = cv_pred(Xall, y, fold, "boost")
        res[name] = dict(n_exams=int(len(S)), participants=int(S.pid.nunique()), cv_r2_ridge_all=tot, cv_r2_boost_all=r2(y, p_b),
                         shapley=sh, shapley_share_of_r2={g: (v / tot if tot > 0 else None) for g, v in sh.items()},
                         single_group_r2=single, unexplained=1 - tot)
        if name in ("lbar1_all", "lbar6_baseline"):
            U.loc[np.flatnonzero(mask), f"U_{ycol}"] = y - p_r
    out_d.mkdir(parents=True, exist_ok=True)
    (out_d / f"s4_q1a_{tag}.json").write_text(json.dumps(res, indent=1))
    U.to_csv(out_d / f"s4_q1a_U_{tag}.csv", index=False)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
