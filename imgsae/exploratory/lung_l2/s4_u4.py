"""Lung L2, S4, U4 references (docs/LUNG_L2_PROTOCOL.md 9.7; C7: the probe is a reference, not a strict ceiling).
Cross-validated AUROC (participant folds, 5, seed 0; participant-bootstrap intervals) for y1 (all screens) and y6 (baseline) of:
- the probe: L2-logistic regression on the five members' h joined (2,560 numbers), standardised; C chosen by inner participant-grouped
  5-fold CV on each training part (Cs 1e-4 to 1e1, scoring AUROC);
- for every arm with saved families: nlst_l0.logit_model (standardise + logistic, C = 0.3) on the arm's family activations;
- Sybil's own published score s_t.
References only: no candidate for gate 9.8.
usage (venv python): python s4_u4.py <assembled dir> <results dir> [--tag dev] [--K 64]
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegressionCV
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, r"D:\Shayan\imgsae\exploratory\lung_l0")
import nlst_l0 as L0  # noqa: E402
import s4_common as S  # noqa: E402

CS = np.logspace(-4, 1, 6)


def probe_oof(X, y, pid, fold):
    out = np.zeros(len(y)); chosen = []
    for f in range(5):
        tr, te = fold != f, fold == f
        inner = list(GroupKFold(5).split(X[tr], y[tr], groups=pid[tr]))
        m = make_pipeline(StandardScaler(), LogisticRegressionCV(Cs=CS, cv=inner, scoring="roc_auc", max_iter=3000)).fit(X[tr], y[tr])
        out[te] = m.predict_proba(X[te])[:, 1]; chosen.append(float(m[-1].C_[0]))
    return out, chosen


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("assembled"); ap.add_argument("results"); ap.add_argument("--tag", default="dev")
    ap.add_argument("--K", type=int, default=64); a = ap.parse_args(); R = Path(a.results)
    E, arr = S.load(a.assembled, a.tag); Hall = arr["h"].reshape(len(E), -1).astype(np.float64); res = dict(tag=a.tag)
    for y, (s, lb, base) in (("y1", S.HORIZONS["y1"]), ("y6", S.HORIZONS["y6"])):
        m = S.pop(E, y); P = E[m]; yy = P[y].to_numpy(int); pid = P.pid.to_numpy(); fold = S.folds(pid); bt = S.Boot(pid)
        r = dict(counts=S.counts(E, m, y), sybil=S.auc_ci(yy, P[s].to_numpy(), bt))
        pr, ch = probe_oof(Hall[m], yy, pid, fold); r["probe_h_2560"] = dict(S.auc_ci(yy, pr, bt), C_by_fold=ch)
        fams = {}
        for arm in S.C.ARMS:
            try: Cn = S.contrib(a.tag, arm, a.K)
            except FileNotFoundError: continue
            M = P[["series_uid"]].merge(Cn, on="series_uid", how="left"); cols = [c for c in Cn.columns if c.startswith("family_")]
            if not cols: fams[arm] = dict(n_families=0); continue
            X = M[cols].to_numpy(float); oof = np.zeros(len(yy))
            for f in range(5):
                tr, te = fold != f, fold == f; oof[te] = L0.logit_model().fit(X[tr], yy[tr]).predict_proba(X[te])[:, 1]
            fams[arm] = dict(S.auc_ci(yy, oof, bt), n_families=len(cols))
        r["family_activation_models"] = fams; res[y] = r
    res["note"] = "references only (protocol 9.7 U4, C7); Sybil's dev AUROC is mildly optimistic (C6)"
    S.write(R, f"s4_u4_{a.tag}.json", res)
    print("s4_u4: written")


if __name__ == "__main__":
    main()
