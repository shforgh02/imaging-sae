"""Lung L2, plan X1 (docs/EXECUTION_LOG.md, 2026-11-18, committed 0d39e6a before this ran on test): the added value of Sybil beyond the
radiologists' record. EXPLORATORY (protocol 11): not a hypothesis, nothing confirmed; every cell is reported.
Comparators (fitted on Sybil's TRAIN participants only, or not fitted): C1 the frozen form F (F1/F6 columns of the assembly);
C2 findings only (F's items without the radiologist's call res1-res6, iso_pos); C3 the call only; C4 gradient boosting on the findings-only
items (nlst_l0.boost_model); C5 the largest nodule diameter. 1-year family fitted for y1 on all train screens; 6-year family for y6 on
train baseline screens (items needing an earlier scan dropped, as F6).
Endpoints: E1 y1 all screens; E2 y1 baseline; E3 y2 baseline; E4 y6 baseline; E5 late (cancer 1-6 years after a negative baseline);
E6 y1 among negative calls (res 1-3); E7 y1 among positive calls (res 4-6). Sybil: s1 (E1, E2, E6, E7), s2 (E3), s6 (E4, E5).
Methods: M1 AUROC and paired differences; M2 C + Sybil with the combination fitted on dev, applied to test; M3 the same cross-fitted on the
root (10 participant folds, seed 0); M4 likelihood-ratio test of Sybil given C (in-sample); M5 decision curve for E1; M6 scenarios with
thresholds from dev: (a) rule-out among positive calls, (b) rule-in among negative calls. Participant bootstrap 2,000 draws, seed 0.
usage (venv python): python s7_added_value.py <dev assembled dir> <test assembled dir> <nlst tables dir> <split pickle> <out dir> --roots dev[,test]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, r"D:\Shayan\imgsae\exploratory\lung_l0")
import nlst_l0 as L  # noqa: E402
import s4_common as S  # noqa: E402

CALL = ("res1", "res2", "res3", "res4", "res5", "res6", "iso_pos")
FROZEN = json.loads((HERE / "results/s5/frozen_thresholds_L2.json").read_text())["thresholds"]
EP = {"E1": ("y1", "s1", 1, "all"), "E2": ("y1", "s1", 1, "base"), "E3": ("y2", "s2", 6, "base"), "E4": ("y6", "s6", 6, "base"),
      "E5": ("late", "s6", 6, "late"), "E6": ("y1", "s1", 1, "neg"), "E7": ("y1", "s1", 1, "pos")}
NB_T = (0.005, 0.01, 0.02, 0.03, 0.05)


def comparators(b):
    """fit C2, C3, C4 on train for both families; return {fam: {name: (kind, model, features)}}."""
    X = b["X"]; out = {}
    for fam, y, base in ((1, "y1", False), (6, "y6", True)):
        r, d = L.features_for(b["read"], b["demo"], base); full = r + d
        tr = X[(X.grp == "train") & X[y].notna() & ((X.study_yr == 0) | (not base))]
        find = [c for c in full if c not in CALL]; call = [c for c in full if c in CALL]
        out[fam] = dict(C2=("logit", L.logit_model().fit(tr[find], tr[y]), find), C3=("logit", L.logit_model().fit(tr[call], tr[y]), call),
                        C4=("boost", L.boost_model().fit(tr[find], tr[y]), find), n_fit=int(len(tr)), n_pos=int(tr[y].sum()),
                        n_features=dict(C2=len(find), C3=len(call), C4=len(find)))
    return out


def scores(E, CM):
    """comparator logits for every exam of an assembly (columns C1_1 ... C5_6)."""
    for fam in (1, 6):
        E[f"C1_{fam}"] = E[f"F{fam}"]
        for nm in ("C2", "C3", "C4"):
            kind, m, cols = CM[fam][nm]
            E[f"{nm}_{fam}"] = m.decision_function(E[cols]) if kind == "logit" else S.logit(m.predict_proba(E[cols])[:, 1])
        E[f"C5_{fam}"] = E.max_dia.fillna(0).astype(float)
    return E


def population(E, ep):
    y, s, fam, where = EP[ep]; m = E[y].notna()
    if where in ("base",): m &= E.study_yr == 0
    if where == "neg": m &= E.positive_call == 0
    if where == "pos": m &= E.positive_call == 1
    return m.to_numpy()


def folds10(pid):
    u = np.unique(pid); perm = np.random.default_rng(0).permutation(len(u)); f = {p: i % 10 for i, p in zip(range(len(u)), u[perm])}
    return np.array([f[p] for p in pid])


def lr_fit(X, y): return LogisticRegression(C=1e6, max_iter=5000).fit(X, y)


def nb(y, p, t): n = len(y); return float(((p >= t) & (y == 1)).sum() / n - ((p >= t) & (y == 0)).sum() / n * t / (1 - t))


def endpoint(E, ep, Edev=None):
    y_, s_, fam, _ = EP[ep]; m = population(E, ep); Q = E[m].reset_index(drop=True); y = Q[y_].to_numpy(int); pid = Q.pid.to_numpy()
    bt = S.Boot(pid); sy = S.logit(Q[s_]); n_c = int(y.sum())
    o = dict(outcome=y_, sybil_score=s_, counts=dict(exams=int(len(Q)), participants=int(len(np.unique(pid))), cancers=n_c),
             cancers_by_can_scr={str(int(k)) if pd.notna(k) else "na": int(v) for k, v in Q.loc[y == 1, "can_scr"].value_counts(dropna=False).items()},
             note="n < 10 cancers: no claim" if n_c < 10 else "")
    if n_c < 2 or n_c == len(Q): return o
    o["auroc_sybil"] = S.auc_ci(y, sy, bt); fo = folds10(pid)
    for c in ("C1", "C2", "C3", "C4", "C5"):
        cs = Q[f"{c}_{fam}"].to_numpy(float); r = dict(auroc=S.auc_ci(y, cs, bt), sybil_minus_c=S.dauc_ci(y, sy, cs, bt))
        both = np.c_[cs, sy]
        p0, p1 = S.crossfit(y, cs, fo), S.crossfit(y, both, fo)
        r["M3_crossfit_c_plus_sybil_minus_c"] = S.dauc_ci(y, p1, p0, bt); r["M3_auroc_c_plus_sybil"] = S.auc(y, p1)
        r["M4_lr_sybil_given_c"] = S.lr_test(y, cs, both)
        if Edev is not None:
            md = population(Edev, ep); D = Edev[md]; wd = lr_fit(np.c_[D[f"{c}_{fam}"], S.logit(D[s_])], D[y_].astype(int))
            pc = wd.decision_function(both); r["M2_devfit_c_plus_sybil_minus_c"] = S.dauc_ci(y, pc, cs, bt); r["M2_auroc_c_plus_sybil"] = S.auc(y, pc)
            r["M2_dev_weights"] = dict(c=float(wd.coef_[0][0]), sybil=float(wd.coef_[0][1]), intercept=float(wd.intercept_[0]))
        o[c] = r
    return o


def decision_curve(E, Edev):
    m = population(E, "E1"); Q = E[m].reset_index(drop=True); y = Q.y1.to_numpy(int); bt = S.Boot(Q.pid.to_numpy()); md = population(Edev, "E1"); D = Edev[md]
    P = {"sybil": Q.s1.to_numpy(float), "treat_all": np.ones(len(Q))}
    for c in ("C1", "C2"):
        P[c] = 1 / (1 + np.exp(-Q[f"{c}_1"].to_numpy(float)))
        w = lr_fit(np.c_[D[f"{c}_1"], S.logit(D.s1)], D.y1.astype(int)); P[f"{c}_plus_sybil"] = w.predict_proba(np.c_[Q[f"{c}_1"], S.logit(Q.s1)])[:, 1]
    out = {}
    for t in NB_T:
        row = {k: nb(y, p, t) for k, p in P.items()}
        for c in ("C1", "C2"):
            a, b = P[f"{c}_plus_sybil"], P[c]; row[f"{c}_plus_sybil_minus_{c}"] = bt.ci(lambda tk, a=a, b=b: nb(y[tk], a[tk], t) - nb(y[tk], b[tk], t))
        row["sybil_minus_C1"] = bt.ci(lambda tk: nb(y[tk], P["sybil"][tk], t) - nb(y[tk], P["C1"][tk], t))
        out[f"{t:.3f}"] = row
    return dict(counts=S.counts(E, m, "y1"), net_benefit=out, note="net benefit = TP/n - FP/n * t/(1-t); per exam; combinations fitted on dev")


def scenarios(E, Edev):
    out = {}
    # (a) rule-out among positive calls: s1 cut keeping 95% of dev 1-year cancers among positive calls; same rule for C2
    md = population(Edev, "E7"); D = Edev[md]; m = population(E, "E7"); Q = E[m]; yq = Q.y1.to_numpy(int)
    a = {}
    for nm, col in (("sybil", "s1"), ("C2", "C2_1")):
        cut = float(np.quantile(D.loc[D.y1 == 1, col].to_numpy(float), 0.05)); below = (Q[col] < cut).to_numpy()
        fp, ca = int(((yq == 0)).sum()), int((yq == 1).sum())
        a[nm] = dict(cut_from_dev=cut, false_positive_calls=fp, removed=int((below & (yq == 0)).sum()), removed_share=float((below & (yq == 0)).sum() / fp) if fp else None,
                     removed_ci=S.clopper_pearson(int((below & (yq == 0)).sum()), fp) if fp else None, cancers=ca, cancers_lost=int((below & (yq == 1)).sum()))
    out["a_rule_out_positive_calls"] = dict(counts=dict(exams=int(len(Q)), participants=int(Q.pid.nunique()), cancers=int(yq.sum())), **a)
    # (b) rule-in among negative calls: Sybil frozen tau90 vs C2 at its own dev 90th percentile
    b = {}
    for ep, s_, tk in (("E6", "s1", "tau90_s1"), ("E5", "s6", "tau90_s6")):
        fam = EP[ep][2]; y_ = EP[ep][0]; m = population(E, ep); Q = E[m]; yq = Q[y_].to_numpy(int)
        md = population(Edev, ep if ep == "E5" else "E1"); D = Edev[md]; cut_c2 = float(np.quantile(D.loc[D[y_] == 0, f"C2_{fam}"].to_numpy(float), 0.90))
        fs, fc = (Q[s_] >= FROZEN[tk]).to_numpy(), (Q[f"C2_{fam}"] >= cut_c2).to_numpy(); c = yq == 1; n0 = int((~c).sum())
        b[ep] = dict(counts=dict(exams=int(len(Q)), participants=int(Q.pid.nunique()), cancers=int(c.sum())), sybil_cut=FROZEN[tk], c2_cut_from_dev=cut_c2,
                     cancers_flagged_sybil=int((fs & c).sum()), cancers_flagged_c2=int((fc & c).sum()), cancers_flagged_both=int((fs & fc & c).sum()),
                     cancers_flagged_sybil_only=int((fs & ~fc & c).sum()), cancers_flagged_c2_only=int((~fs & fc & c).sum()),
                     sybil_sensitivity_ci=S.clopper_pearson(int((fs & c).sum()), int(c.sum())) if c.sum() else None,
                     c2_sensitivity_ci=S.clopper_pearson(int((fc & c).sum()), int(c.sum())) if c.sum() else None,
                     false_alarms_per_1000_sybil=float((fs & ~c).sum() / n0 * 1000) if n0 else None, false_alarms_per_1000_c2=float((fc & ~c).sum() / n0 * 1000) if n0 else None)
    out["b_rule_in_negative_calls"] = b
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("dev"); ap.add_argument("test"); ap.add_argument("tables"); ap.add_argument("split"); ap.add_argument("out")
    ap.add_argument("--roots", default="dev"); a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    b = L.build(a.tables, a.split); CM = comparators(b)
    prsn = pd.read_csv(next(Path(a.tables).glob("*prsn*.csv")), usecols=["pid", "can_scr"]); cs = dict(zip(prsn.pid.astype(str), prsn.can_scr))
    def load(d, root):
        E = pd.read_csv(Path(d) / f"exams_{root}.csv", dtype={"pid": str}, low_memory=False); E["can_scr"] = E.pid.map(cs); return scores(E, CM)
    Edev = load(a.dev, "dev")
    for root in a.roots.split(","):
        E = Edev if root == "dev" else load(a.test, "test"); ref = None if root == "dev" else Edev
        res = dict(root=root, label="EXPLORATORY (plan X1, committed 0d39e6a before the test run); nothing here is confirmed",
                   comparator_fits={str(f): dict(n_fit=CM[f]["n_fit"], n_pos=CM[f]["n_pos"], n_features=CM[f]["n_features"]) for f in (1, 6)},
                   endpoints={ep: endpoint(E, ep, ref) for ep in EP})
        if ref is not None: res["M5_decision_curve_E1"] = decision_curve(E, ref); res["M6_scenarios"] = scenarios(E, ref)
        p = out / f"s7_added_value_{root}.json"; p.write_bytes((json.dumps(res, indent=1, default=float) + "\n").encode("utf-8")); print("written", p)


if __name__ == "__main__":
    main()
