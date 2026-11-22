"""Lung L2, plan X10 (docs/EXECUTION_LOG.md, 2026-11-22, plan committed 39f3f7a before anything was computed). EXPLORATORY: nothing is
confirmed; every cell is reported; no claim for a group with fewer than 10 cancers.
A reduced "portable" form (items most screening sites record; a strict subset of the form F), fitted like F on Sybil's TRAIN participants
only (nlst_l0.logit_model: standardise + logistic, C = 0.3), never refit; parameters written to results/x10/x10_portable_form_params.json
(the frozen form for partners). Primary P without the radiologist's call; secondary P + call. Evaluated on dev and test.
Imports frozen modules, x9_rules_thresholds.py and l2_form.py; edits none.
usage (venv python): python x10_portable_form.py <dev assembled dir> <test assembled dir> <nlst tables dir> <split pickle> <out dir> --roots dev[,test]
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, r"D:\Shayan\imgsae\exploratory\lung_l0")
import nlst_l0 as L  # noqa: E402
import s4_common as S  # noqa: E402
import s7_added_value as X1  # noqa: E402
import x7_sensitivity as X7  # noqa: E402
import x9_rules_thresholds as X9  # noqa: E402
import l2_form  # noqa: E402

LABEL = "EXPLORATORY (plan X10, committed 39f3f7a before anything was computed); nothing here is confirmed"
ITEMS6 = ["max_dia", "log_dia", "big_gg", "big_mixed", "big_spic", "big_upper", "n_nod", "ab59", "age_scan", "gender", "cigsmok"]
ITEMS1 = ITEMS6 + ["gw2", "pre1", "study_yr"]
CALL = "positive_call"
MODELS = (("P1", "y1", False, ITEMS1), ("P6", "y6", True, ITEMS6), ("P1_call", "y1", False, ITEMS1 + [CALL]), ("P6_call", "y6", True, ITEMS6 + [CALL]))


# ------------------------------------------------------------------ fit on train (no dev or test row is used)
def fit(b):
    X = b["X"]; out = {}
    for name, y, base, items in MODELS:
        tr = X[(X.grp == "train") & X[y].notna() & ((X.study_yr == 0) | (not base))]
        mdl = L.logit_model().fit(tr[items], tr[y])
        sc, lr = mdl.named_steps["standardscaler"], mdl.named_steps["logisticregression"]
        out[name] = dict(outcome=y, baseline_only=base, features=list(items), mean=sc.mean_.tolist(), scale=sc.scale_.tolist(),
                         coef=lr.coef_[0].tolist(), intercept=float(lr.intercept_[0]), n_fit=int(len(tr)), n_fit_pos=int(tr[y].sum()))
        out[name]["_check_rows"] = mdl   # removed before writing
    return out


# ------------------------------------------------------------------ analyses
def auroc_block(Q, y_col, P, pairs, note):
    y = Q[y_col].to_numpy(int); bt = S.Boot(Q.pid.to_numpy()); n_c = int(y.sum()); names = list(P)
    o = dict(counts=dict(exams=int(len(Q)), participants=int(Q.pid.nunique()), cancers=n_c, prevalence=float(y.mean())),
             note=note + ("; n < 10 cancers: no claim" if n_c < 10 else ""))
    if n_c < 2: return o

    def fn(t):
        yy = y[t]; a = {k: S.auc(yy, P[k][t]) for k in names}
        ap = {k: (float(average_precision_score(yy, P[k][t])) if yy.sum() > 0 else None) for k in names}
        v = [a[k] for k in names] + [ap[k] for k in names]
        for u, w in pairs:
            v += [None if a[u] is None or a[w] is None else a[u] - a[w], None if ap[u] is None or ap[w] is None else ap[u] - ap[w]]
        return v
    keys = [f"auroc|{k}" for k in names] + [f"auprc|{k}" for k in names] + [f"{m}|{u}_minus_{w}" for u, w in pairs for m in ("auroc", "auprc")]
    ci = X7.multi_ci(bt, fn, keys)
    o["auroc"] = {k: ci[f"auroc|{k}"] for k in names}; o["auprc"] = {k: ci[f"auprc|{k}"] for k in names}
    o["auroc_differences"] = {f"{u}_minus_{w}": ci[f"auroc|{u}_minus_{w}"] for u, w in pairs}
    o["auprc_differences"] = {f"{u}_minus_{w}": ci[f"auprc|{u}_minus_{w}"] for u, w in pairs}
    return o


def cut(s0, fa):
    thr = float(np.quantile(s0, 1 - fa)); strict = abs(float((s0 > thr).mean()) - fa) < abs(float((s0 >= thr).mean()) - fa)
    return thr, strict


def thresholds(Q, D, y_col, cont):
    y = Q[y_col].to_numpy(int); yd = D[y_col].to_numpy(int); bt = S.Boot(Q.pid.to_numpy())
    fixed = dict(lung_rads_3=lambda Z: Z.lr_up.to_numpy() >= 3, radiologists_call=lambda Z: Z.positive_call.to_numpy() == 1)
    ops = {"OP_L3": ("lung_rads_3", float(fixed["lung_rads_3"](D)[yd == 0].mean())), "OP_R": ("radiologists_call", float(fixed["radiologists_call"](D)[yd == 0].mean()))}
    F, cuts = {k: f(Q) for k, f in fixed.items()}, {}
    for op, (ref, fa) in ops.items():
        for nm, col in cont.items():
            s0 = D[col].to_numpy(float)[yd == 0]; thr, strict = cut(s0, fa); s = Q[col].to_numpy(float)
            F[f"{nm}@{op}"] = (s > thr) if strict else (s >= thr)
            cuts[f"{nm}@{op}"] = dict(threshold=thr, flag_rule=">" if strict else ">=", target_dev_false_alarm_share=fa,
                                      achieved_dev_false_alarm_share=float(((s0 > thr) if strict else (s0 >= thr)).mean()),
                                      test_false_alarm_share=float(F[f"{nm}@{op}"][y == 0].mean()))
    pairs = []
    for op, (ref, _) in ops.items():
        pairs += [(f"sybil@{op}", f"P@{op}"), (f"sybil@{op}", f"P_call@{op}")]
    pairs += [("P@OP_L3", "lung_rads_3")]
    names = list(F)

    def fn(t):
        yy = y[t]; M = {k: X9.measures(F[k][t], yy)[0] for k in names}; v = [M[k][m] for k in names for m in X9.MEAS]
        for a, b in pairs: v += [None if M[a][m] is None or M[b][m] is None else M[a][m] - M[b][m] for m in X9.DIFF]
        return v
    keys = [f"{k}|{m}" for k in names for m in X9.MEAS] + [f"{a}_minus_{b}|{m}" for a, b in pairs for m in X9.DIFF]
    ci = X7.multi_ci(bt, fn, keys)
    table = {k: dict(counts=X9.measures(F[k], y)[1], **{m: ci[f"{k}|{m}"] for m in X9.MEAS}) for k in names}
    for k, c in cuts.items(): table[k]["cut"] = c
    return dict(counts=dict(exams=int(len(Q)), cancers=int(y.sum())), operating_points={op: dict(matched_to=r, dev_false_alarm_share=fa) for op, (r, fa) in ops.items()},
                note="cuts set on cancer-free dev exams only (X9 tie rule)", table=table,
                differences={f"{a}_minus_{b}": {m: ci[f"{a}_minus_{b}|{m}"] for m in X9.DIFF} for a, b in pairs})


def added_value(Q, D, y_col, s_col, pcols):
    y = Q[y_col].to_numpy(int); yd = D[y_col].to_numpy(int); bt = S.Boot(Q.pid.to_numpy()); fo = X1.folds10(Q.pid.to_numpy())
    sy, syd = S.logit(Q[s_col]), S.logit(D[s_col]); out = {}
    for nm, col in pcols.items():
        p, pd_ = Q[col].to_numpy(float), D[col].to_numpy(float)
        b1 = X7.logreg(np.c_[pd_, syd], yd); comb = np.column_stack([np.ones(len(y)), p, sy]) @ b1
        c0, c1 = S.crossfit(y, p[:, None], fo), S.crossfit(y, np.c_[p, sy], fo)
        out[nm] = dict(dev_fitted_gain=S.dauc_ci(y, comb, p, bt), crossfit_gain=S.dauc_ci(y, c1, c0, bt), auroc_alone=S.auc(y, p),
                       auroc_plus_sybil_dev_fitted=S.auc(y, comb), auroc_alone_crossfit=S.auc(y, c0), auroc_plus_sybil_crossfit=S.auc(y, c1),
                       dev_weights=dict(intercept=float(b1[0]), form=float(b1[1]), sybil_logit=float(b1[2])))
    return out


# ------------------------------------------------------------------ main
EPS = {"E1_1_year_all_screens": ("E1", 1), "E2_1_year_baseline": ("E2", 1), "E4_6_years_baseline": ("E4", 6)}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("dev"); ap.add_argument("test"); ap.add_argument("tables"); ap.add_argument("split"); ap.add_argument("out")
    ap.add_argument("--roots", default="dev"); a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    b = L.build(a.tables, a.split); CM = X1.comparators(b); X = b["X"]
    P = fit(b)
    dev_rows = X[X.grp == "dev"]
    checks = {k: float(np.abs(P[k].pop("_check_rows").decision_function(dev_rows[P[k]["features"]]) - l2_form.predict_logit(P[k], dev_rows)).max()) for k in P}
    pp = out / "x10_portable_form_params.json"
    if "dev" in a.roots.split(","):
        pp.write_bytes((json.dumps(P, indent=1) + "\n").encode("utf-8"))
    else:   # test run: the committed parameter file must be identical to a fresh fit (never refit silently)
        old = json.loads(pp.read_text())
        if any(np.abs(np.array(old[k]["coef"]) - np.array(P[k]["coef"])).max() > 1e-12 for k in P): raise SystemExit("REFUSED: parameters differ from the committed file")
        P = old
    p_sha = hashlib.sha256(pp.read_bytes()).hexdigest()
    S_ = X[["pid", "study_yr"]].copy(); S_["pid"] = S_.pid.astype(int).astype(str); S_["study_yr"] = S_.study_yr.astype(int)
    for k in P: S_[k] = l2_form.predict_logit(P[k], X)
    fparams = json.loads((HERE / "results/l2_form_params.json").read_text()); S_["F1_rebuilt"] = l2_form.predict_logit(fparams["F1"], X)

    R, _ = X9.rules(a.tables); R["pid"] = R.pid.astype(int).astype(str); R["study_yr"] = R.study_yr.astype(int); R = R[["pid", "study_yr", "lr_up", "brock"]]
    prsn = pd.read_csv(next(Path(a.tables).glob("*prsn*.csv")), usecols=["pid", "can_scr"]); cs = dict(zip(prsn.pid.astype(str), prsn.can_scr))

    def load(d, root):
        E = pd.read_csv(Path(d) / f"exams_{root}.csv", dtype={"pid": str}, low_memory=False); E["can_scr"] = E.pid.map(cs); E = X1.scores(E, CM)
        n = len(E); E = E.merge(R, on=["pid", "study_yr"], how="left").merge(S_, on=["pid", "study_yr"], how="left")
        if len(E) != n: raise SystemExit("REFUSED: a merge duplicated exam rows")
        if E[[k for k in P]].isna().any().any(): raise SystemExit("REFUSED: portable form missing for some exams")
        E["lr_up"] = E.lr_up.fillna(1).astype(int); E["brock"] = E.brock.fillna(-99.0)
        return E
    Edev = load(a.dev, "dev")
    for root in a.roots.split(","):
        E = Edev if root == "dev" else load(a.test, "test")
        res = dict(root=root, label=LABEL, params_file=pp.name, params_sha256=p_sha, items=dict(P1=ITEMS1, P6=ITEMS6, call=CALL),
                   n_fit={k: dict(exams=P[k]["n_fit"], cancers=P[k]["n_fit_pos"]) for k in P}, coefficients_standardised={k: dict(zip(P[k]["features"], P[k]["coef"])) for k in P},
                   check_vs_sklearn_on_dev_rows=checks, check_form_F1_rebuilt_vs_assembly=float(np.abs(E.F1_rebuilt - E.F1).max()))
        res["auroc_auprc"], res["thresholds"], res["added_value"] = {}, {}, {}
        b4 = (E.study_yr == 0) & E.y6.notna()
        pops = {k: (E[X1.population(E, ep)].reset_index(drop=True), Edev[X1.population(Edev, ep)].reset_index(drop=True), ep, fam) for k, (ep, fam) in EPS.items()}
        pops["W2_E4_without_cancers_after_a_positive_screen"] = (E[b4 & ~((E.y6 == 1) & (E.can_scr == 1))].reset_index(drop=True), None, "E4", 6)
        for k, (Q, D, ep, fam) in pops.items():
            y_col, s_col = X1.EP[ep][0], X1.EP[ep][1]; pk = f"P{fam}"
            sc = dict(sybil=Q[s_col].to_numpy(float), form_F=Q[f"C1_{fam}"].to_numpy(float), findings_only_C2=Q[f"C2_{fam}"].to_numpy(float),
                      P=Q[pk].to_numpy(float), P_call=Q[f"{pk}_call"].to_numpy(float), lung_rads=Q.lr_up.to_numpy(float), brock=Q.brock.to_numpy(float))
            pairs = [("sybil", "P"), ("sybil", "P_call"), ("form_F", "P"), ("form_F", "P_call")]
            res["auroc_auprc"][k] = auroc_block(Q, y_col, sc, pairs, "W2: cases = 6-year cancers with can_scr 2, 3 or 4 (as X7)" if D is None else "")
            if D is not None:
                cont = dict(sybil=s_col, form_F=f"C1_{fam}", P=pk, P_call=f"{pk}_call")
                res["thresholds"][k] = thresholds(Q, D, y_col, cont)
                if ep in ("E1", "E4"): res["added_value"][k] = added_value(Q, D, y_col, s_col, dict(P=pk, P_call=f"{pk}_call"))
        p = out / f"x10_portable_form_{root}.json"; p.write_bytes((json.dumps(res, indent=1, default=float) + "\n").encode("utf-8")); print("written", p)


if __name__ == "__main__":
    main()
