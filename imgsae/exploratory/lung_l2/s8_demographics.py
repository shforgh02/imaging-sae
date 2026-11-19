"""Lung L2, plan X3 (docs/EXECUTION_LOG.md, 2026-11-19, committed dcfba8f before this ran on test): do age, sex and smoking change
Sybil's added value? EXPLORATORY (protocol 11): nothing here is confirmed; every cell is reported.
Models fitted on Sybil's TRAIN participants only (as the frozen form F; 1-year family on all train screens, 6-year family on train
baseline screens): D = demographics (age_scan, gender, cigsmok, + study_yr in the 1-year family); FN = the radiologists' findings without
the screening call and without demographics. C2 = findings + demographics (no call) and C1 = the frozen form, as in s7_added_value.py.
Combinations with Sybil (Sybil + D, FN + D is C2 itself): weights fitted on dev and applied to test (M2), and cross-fitted on the root
(10 participant folds, seed 0; M3).
Endpoints: E1 y1 all screens, E2 y1 baseline, E4 y6 baseline, E5 cancer 1-6 years after a negative baseline. Participant bootstrap 2,000.
usage (venv python): python s8_demographics.py <dev assembled dir> <test assembled dir> <nlst tables dir> <split pickle> <out dir> --roots dev[,test]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, r"D:\Shayan\imgsae\exploratory\lung_l0")
import nlst_l0 as L  # noqa: E402
import s4_common as S  # noqa: E402
import s7_added_value as A  # noqa: E402

EPS = ("E1", "E2", "E4", "E5")


def fit_models(b):
    X = b["X"]; out = {}
    for fam, y, base in ((1, "y1", False), (6, "y6", True)):
        r, d = L.features_for(b["read"], b["demo"], base)
        tr = X[(X.grp == "train") & X[y].notna() & ((X.study_yr == 0) | (not base))]
        fn = [c for c in r if c not in A.CALL]
        out[fam] = dict(D=(L.logit_model().fit(tr[d], tr[y]), d), FN=(L.logit_model().fit(tr[fn], tr[y]), fn), n_fit=int(len(tr)), n_pos=int(tr[y].sum()),
                        items=dict(D=d, n_FN=len(fn)))
    return out


def add_scores(E, M, CM):
    E = A.scores(E, CM)
    for fam in (1, 6):
        for nm in ("D", "FN"):
            m, cols = M[fam][nm]; E[f"{nm}_{fam}"] = m.decision_function(E[cols])
    return E


def dci(y, a, b, bt):
    return S.dauc_ci(y, a, b, bt)


def endpoint(E, ep, Edev):
    y_, s_, fam, _ = A.EP[ep]; m = A.population(E, ep); Q = E[m].reset_index(drop=True); y = Q[y_].to_numpy(int); pid = Q.pid.to_numpy()
    bt = S.Boot(pid); sy = S.logit(Q[s_]).astype(float); fo = A.folds10(pid)
    D_, FN, C2, C1 = (Q[f"{k}_{fam}"].to_numpy(float) for k in ("D", "FN", "C2", "C1"))
    o = dict(outcome=y_, sybil_score=s_, counts=dict(exams=int(len(Q)), participants=int(len(np.unique(pid))), cancers=int(y.sum())))
    o["auroc"] = {k: S.auc_ci(y, v, bt) for k, v in (("D_demographics", D_), ("sybil", sy), ("FN_findings_no_demo_no_call", FN), ("C2_findings_plus_demo", C2), ("C1_frozen_form", C1))}
    # Sybil + D: cross-fitted on this root (M3) and, on test, weights from dev (M2)
    sd_x = S.crossfit(y, np.c_[sy, D_], fo); o["M3_auroc_sybil_plus_D"] = S.auc(y, sd_x)
    o["M3_sybil_plus_D_minus_sybil"] = dci(y, sd_x, S.crossfit(y, sy, fo), bt)
    o["M3_sybil_plus_D_minus_C2"] = dci(y, sd_x, C2, bt)
    if Edev is not None:
        md = A.population(Edev, ep); Dv = Edev[md]; w = A.lr_fit(np.c_[S.logit(Dv[s_]), Dv[f"D_{fam}"]], Dv[y_].astype(int))
        sd = w.decision_function(np.c_[sy, D_]); o["M2_auroc_sybil_plus_D"] = S.auc(y, sd)
        o["M2_sybil_plus_D_minus_sybil"] = dci(y, sd, sy, bt); o["M2_sybil_plus_D_minus_C2"] = dci(y, sd, C2, bt)
        o["M2_dev_weights"] = dict(sybil=float(w.coef_[0][0]), demographics=float(w.coef_[0][1]), intercept=float(w.intercept_[0]))
        o["spearman_sybil_vs_sybil_plus_D_M2"] = float(spearmanr(sy, sd).correlation)
    o["sybil_minus_FN"] = dci(y, sy, FN, bt); o["C2_minus_FN"] = dci(y, C2, FN, bt); o["C1_minus_C2"] = dci(y, C1, C2, bt)
    o["spearman_sybil_vs_age"] = float(spearmanr(sy, Q.age_scan.astype(float)).correlation)
    o["spearman_sybil_vs_sybil_plus_D_M3"] = float(spearmanr(sy, sd_x).correlation)
    o["note"] = "n < 10 cancers: no claim" if y.sum() < 10 else ""
    return o


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("dev"); ap.add_argument("test"); ap.add_argument("tables"); ap.add_argument("split"); ap.add_argument("out")
    ap.add_argument("--roots", default="dev"); a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    b = L.build(a.tables, a.split); CM = A.comparators(b); M = fit_models(b)
    prsn = pd.read_csv(next(Path(a.tables).glob("*prsn*.csv")), usecols=["pid", "can_scr"]); cs = dict(zip(prsn.pid.astype(str), prsn.can_scr))
    def load(d, root):
        E = pd.read_csv(Path(d) / f"exams_{root}.csv", dtype={"pid": str}, low_memory=False); E["can_scr"] = E.pid.map(cs); return add_scores(E, M, CM)
    Edev = load(a.dev, "dev")
    for root in a.roots.split(","):
        E = Edev if root == "dev" else load(a.test, "test"); ref = None if root == "dev" else Edev
        res = dict(root=root, label="EXPLORATORY (plan X3, committed dcfba8f before the test run); nothing here is confirmed",
                   fits={str(f): dict(n_fit=M[f]["n_fit"], n_pos=M[f]["n_pos"], D_items=M[f]["items"]["D"], n_FN_items=M[f]["items"]["n_FN"]) for f in (1, 6)},
                   endpoints={ep: endpoint(E, ep, ref) for ep in EPS})
        p = out / f"s8_demographics_{root}.json"; p.write_bytes((json.dumps(res, indent=1, default=float) + "\n").encode("utf-8")); print("written", p)


if __name__ == "__main__":
    main()
