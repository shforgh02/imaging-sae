"""Lung L2, plan X7 (docs/EXECUTION_LOG.md, 2026-11-20, plan committed 413dc07 before anything was computed): free checks after the
outside review (docs/REVIEW_PLAN_CHOICE.md, docs/INDEPENDENT_AUDIT_R2.md). EXPLORATORY and POST HOC (protocol 11): nothing is confirmed;
every cell is reported; no claim for a group with fewer than 10 cancers.
P1 work-up bias (W1 E4 without 1-year cancers; W2 E4 without cancers after a positive screen; W3 E5 without them; W4 E1 counts).
P2 6-year censoring of E4 (IPCW with the censoring model refitted in each draw; bound with censored counted as cancer-free).
P3 calibration of Sybil, C1, C2 (E1, E2, E4) and decision curves (E1, E2) with every score recalibrated on dev.
P4 repeated screens: Sybil's coefficient given C1 / C2 with participant-bootstrap intervals (E1, E7); X1's rule-out scenario with
   participant-bootstrap intervals.
P5 harm at cuts fixed on dev: the dev radiologist-matched cuts (s4_u3_dev.json) and the frozen tau90, against the radiologists' call (E1).
P6 z-fix alarm changes at tau90 and tau_rad (T5; outcome-free).
P8 data notes.
Comparators exactly as X1 (s7_added_value.comparators: fitted on Sybil's train participants only). Imports frozen modules, edits none.
usage (venv python): python x7_sensitivity.py <dev assembled dir> <test assembled dir> <nlst tables dir> <split pickle> <out dir> --roots dev[,test]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.special import expit
from scipy.stats import norm
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, r"D:\Shayan\imgsae\exploratory\lung_l0")
import nlst_l0 as L  # noqa: E402
import s4_common as S  # noqa: E402
import s7_added_value as X1  # noqa: E402
from s4_u3 import threshold as u3_threshold  # noqa: E402

FROZEN = X1.FROZEN
U3DEV = json.loads((HERE / "results/s4/s4_u3_dev.json").read_text())
LABEL = "EXPLORATORY, post hoc (plan X7, committed 413dc07 before anything was computed); nothing here is confirmed"


# ------------------------------------------------------------------ helpers
def multi_ci(bt, fn, keys):
    """point estimates and 95% percentile intervals of several statistics computed together in each participant-bootstrap draw."""
    est = fn(np.arange(bt.N)); D = []
    for t in bt.takes(): D.append([np.nan if v is None else v for v in fn(t)])
    D = np.asarray(D, float); out = {}
    for i, k in enumerate(keys):
        d = D[:, i]; d = d[np.isfinite(d)]
        lo, hi = (np.percentile(d, [2.5, 97.5]) if len(d) >= 0.9 * bt.n else (np.nan, np.nan))
        out[k] = dict(est=None if est[i] is None else float(est[i]), lo=float(lo), hi=float(hi), n_draws=int(len(d)),
                      sd=float(d.std(ddof=1)) if len(d) > 1 else None)
    return out


def logreg(X, y, offset=None, iters=60):
    """unpenalised logistic regression by Newton-Raphson; returns [intercept, coefficients...]."""
    y = np.asarray(y, float); X = np.column_stack([np.ones(len(y))] + ([np.asarray(X, float).reshape(len(y), -1)] if X is not None else []))
    off = np.zeros(len(y)) if offset is None else np.asarray(offset, float); b = np.zeros(X.shape[1])
    for _ in range(iters):
        p = expit(X @ b + off); W = p * (1 - p); g = X.T @ (y - p); H = (X * W[:, None]).T @ X
        step = np.linalg.solve(H + 1e-10 * np.eye(len(b)), g); b = b + step
        if np.max(np.abs(step)) < 1e-10: break
    return b


def wauc(y, s, w=None):
    y, s = np.asarray(y, float), np.asarray(s, float)
    if len(np.unique(y)) < 2: return None
    return float(roc_auc_score(y, s, sample_weight=w))


def frame(Q, cols): return {c: Q[c].to_numpy(float) for c in cols}


# ------------------------------------------------------------------ P1 work-up bias
def p1_endpoint(Q, y_col, s_col, fam, note):
    y = Q[y_col].to_numpy(int); pid = Q.pid.to_numpy(); bt = S.Boot(pid); sy = S.logit(Q[s_col]); n_c = int(y.sum())
    o = dict(counts=dict(exams=int(len(Q)), participants=int(len(np.unique(pid))), cancers=n_c), note=note + ("; n < 10 cancers: no claim" if n_c < 10 else ""),
             cancers_by_can_scr={str(int(k)) if pd.notna(k) else "na": int(v) for k, v in Q.loc[y == 1, "can_scr"].value_counts(dropna=False).items()})
    if n_c < 2: return o
    c1, c2 = Q[f"C1_{fam}"].to_numpy(float), Q[f"C2_{fam}"].to_numpy(float)
    o["auroc"] = multi_ci(bt, lambda t: [S.auc(y[t], sy[t]), S.auc(y[t], c1[t]), S.auc(y[t], c2[t])], ["sybil", "C1_form", "C2_findings_only"])
    d = multi_ci(bt, lambda t: [None if S.auc(y[t], sy[t]) is None else S.auc(y[t], sy[t]) - S.auc(y[t], c1[t]),
                                None if S.auc(y[t], sy[t]) is None else S.auc(y[t], sy[t]) - S.auc(y[t], c2[t])], ["sybil_minus_C1", "sybil_minus_C2"])
    fo = X1.folds10(pid); p0, p1 = S.crossfit(y, c2, fo), S.crossfit(y, np.c_[c2, sy], fo)
    d["M3_crossfit_C2_plus_sybil_minus_C2"] = S.dauc_ci(y, p1, p0, bt); o["differences"] = d
    return o


def p1(E):
    out = {}
    b4 = (E.study_yr == 0) & E.y6.notna()
    Q = E[b4 & ~((E.y6 == 1) & (E.y1 == 1))].reset_index(drop=True)
    out["W1_E4_without_cancers_within_1_year"] = p1_endpoint(Q, "y6", "s6", 6, "cases: cancer 1 to 6 years after the baseline scan; controls: baseline exams without cancer within 6 years")
    Q = E[b4 & ~((E.y6 == 1) & (E.can_scr == 1))].reset_index(drop=True)
    out["W2_E4_without_cancers_after_a_positive_screen"] = p1_endpoint(Q, "y6", "s6", 6, "cases: 6-year cancers with can_scr 2, 3 or 4 (not after a positive screen)")
    m5 = X1.population(E, "E5")
    Q = E[m5 & ~((E.late == 1) & (E.can_scr == 1)).to_numpy()].reset_index(drop=True)
    out["W3_E5_without_cancers_after_a_positive_screen"] = p1_endpoint(Q, "late", "s6", 6, "cases: cancer 1 to 6 years after a negative baseline, can_scr 2, 3 or 4")
    m1 = X1.population(E, "E1"); Q = E[m1]
    out["W4_E1_cancers_by_can_scr"] = dict(cancers=int((Q.y1 == 1).sum()), by_can_scr={str(int(k)) if pd.notna(k) else "na": int(v) for k, v in Q.loc[Q.y1 == 1, "can_scr"].value_counts(dropna=False).items()},
                                          note="counts only; cancers not after a positive screen are too few for any claim")
    out["can_scr_codes"] = "NLST prsn can_scr: 1 positive screen, 2 negative screen, 3 missed screen, 4 post-screening, 0 no cancer"
    return out


# ------------------------------------------------------------------ P2 censoring at 6 years (E4)
def p2(E):
    B = E[E.study_yr == 0].reset_index(drop=True); cens = B.y6.isna().to_numpy(); case = (B.y6 == 1).to_numpy(); ctrl = (B.y6 == 0).to_numpy()
    sy = S.logit(B.s6); c1, c2 = B.C1_6.to_numpy(float), B.C2_6.to_numpy(float)
    Z = np.column_stack([B.age_scan.astype(float), B.gender.astype(float), B.cigsmok.astype(float), c1, c2, sy]); Zs = (Z - Z.mean(0)) / Z.std(0)
    bt = S.Boot(B.pid.to_numpy())

    def stats(t):
        nc = ~case[t]; b = logreg(Zs[t][nc], cens[t][nc].astype(float)); pc = expit(b[0] + Zs[t] @ b[1:])
        obs = ~cens[t]; w = np.where(case[t], 1.0, 1.0 / np.clip(1 - pc, 1e-6, None))[obs]; yy = case[t][obs].astype(float)
        a = [wauc(yy, v[t][obs], w) for v in (sy, c1, c2)]
        return a + ([None, None] if a[0] is None else [a[0] - a[1], a[0] - a[2]])
    keys = ["sybil", "C1_form", "C2_findings_only", "sybil_minus_C1", "sybil_minus_C2"]
    ipcw = multi_ci(bt, stats, keys)
    yb = case.astype(float)

    def bound(t):
        a = [S.auc(yb[t], v[t]) for v in (sy, c1, c2)]; return a + ([None, None] if a[0] is None else [a[0] - a[1], a[0] - a[2]])
    bnd = multi_ci(bt, bound, keys)
    fu = B.fu.to_numpy(float)
    desc = dict(baseline_exams=int(len(B)), observed=int((~cens).sum()), censored=int(cens.sum()), censored_share=float(cens.mean()), cancers=int(case.sum()),
                censored_follow_up_years_median=float(np.nanmedian(fu[cens]) / 365.25) if cens.any() else None,
                censored_follow_up_missing=int(np.isnan(fu[cens]).sum()),
                mean_logit_s6=dict(censored=float(sy[cens].mean()), other_controls=float(sy[ctrl].mean())),
                mean_F6=dict(censored=float(c1[cens].mean()), other_controls=float(c1[ctrl].mean())),
                mean_age=dict(censored=float(B.age_scan[cens].mean()), other_controls=float(B.age_scan[ctrl].mean())))
    return dict(description=desc, ipcw=ipcw, bound_censored_as_cancer_free=bnd,
                note="IPCW: logistic model of censoring (age, sex, current smoking, F6, C2, logit s6; standardised) among baseline exams without a 6-year cancer, refitted in every draw; controls weighted 1/(1-p), cases 1")


# ------------------------------------------------------------------ P3 calibration and calibrated decision curves
def calib(y, p):
    y = np.asarray(y, float); p = np.clip(np.asarray(p, float), 1e-8, 1 - 1e-8); lp = np.log(p / (1 - p))
    try: a = brentq(lambda a: expit(a + lp).sum() - y.sum(), -20, 20)
    except ValueError: a = None
    sl = logreg(lp, y)[1]; idx = np.array_split(np.argsort(p, kind="stable"), 10)
    ece = float(sum(abs(p[i].mean() - y[i].mean()) * len(i) for i in idx) / len(y))
    return dict(observed=int(y.sum()), expected=float(p.sum()), o_over_e=float(y.sum() / p.sum()), calibration_intercept=None if a is None else float(a),
                calibration_slope=float(sl), brier=float(np.mean((p - y) ** 2)), ece_10_bins=ece)


def p3(E, Edev):
    out = {}; EPS = {"E1": ("y1", "s1", 1), "E2": ("y1", "s1", 1), "E4": ("y6", "s6", 6)}
    for ep, (y_, s_, fam) in EPS.items():
        m = X1.population(E, ep); Q = E[m].reset_index(drop=True); y = Q[y_].to_numpy(float); bt = S.Boot(Q.pid.to_numpy())
        md = X1.population(Edev, ep); D = Edev[md].reset_index(drop=True); yd = D[y_].to_numpy(float)
        P = {"sybil": Q[s_].to_numpy(float), "C1_form": expit(Q[f"C1_{fam}"].to_numpy(float)), "C2_findings_only": expit(Q[f"C2_{fam}"].to_numpy(float))}
        Pd = {"sybil": D[s_].to_numpy(float), "C1_form": expit(D[f"C1_{fam}"].to_numpy(float)), "C2_findings_only": expit(D[f"C2_{fam}"].to_numpy(float))}
        r = dict(counts=dict(exams=int(len(Q)), participants=int(Q.pid.nunique()), cancers=int(y.sum())), as_given={}, recalibrated_on_dev={})
        for k, p in P.items():
            c = calib(y, p)
            lp = S.logit(p)
            ci = multi_ci(bt, lambda t, p=p, lp=lp: [float(y[t].sum() / p[t].sum()), float(logreg(lp[t], y[t])[1])], ["o_over_e", "calibration_slope"])
            r["as_given"][k] = dict(c, o_over_e_ci=[ci["o_over_e"]["lo"], ci["o_over_e"]["hi"]], calibration_slope_ci=[ci["calibration_slope"]["lo"], ci["calibration_slope"]["hi"]])
            ab = logreg(S.logit(Pd[k]), yd); prc = expit(ab[0] + ab[1] * lp)
            r["recalibrated_on_dev"][k] = dict(calib(y, prc), dev_recalibration=dict(intercept=float(ab[0]), slope=float(ab[1])))
        out[ep] = r
    dca = {}
    for ep in ("E1", "E2"):
        y_, s_, fam = EPS[ep]; m = X1.population(E, ep); Q = E[m].reset_index(drop=True); y = Q[y_].to_numpy(int); bt = S.Boot(Q.pid.to_numpy())
        md = X1.population(Edev, ep); D = Edev[md].reset_index(drop=True); yd = D[y_].to_numpy(int)
        R = {}
        for k, col, f in (("sybil", s_, None), ("C1_form", f"C1_{fam}", expit), ("C2_findings_only", f"C2_{fam}", expit)):
            pt = Q[col].to_numpy(float) if f is None else f(Q[col].to_numpy(float)); pdv = D[col].to_numpy(float) if f is None else f(D[col].to_numpy(float))
            ab = logreg(S.logit(pdv), yd); R[k] = expit(ab[0] + ab[1] * S.logit(pt))
        for c in ("C1", "C2"):
            w = X1.lr_fit(np.c_[D[f"{c}_{fam}"], S.logit(D[s_])], yd); nm = "C1_form" if c == "C1" else "C2_findings_only"
            R[f"{nm}_plus_sybil"] = w.predict_proba(np.c_[Q[f"{c}_{fam}"], S.logit(Q[s_])])[:, 1]
        R["treat_all"] = np.ones(len(Q))
        rows = {}
        for t in X1.NB_T:
            row = {k: X1.nb(y, p, t) for k, p in R.items()}
            pairs = [("C1_form_plus_sybil", "C1_form"), ("C2_findings_only_plus_sybil", "C2_findings_only"), ("sybil", "C1_form"), ("sybil", "C2_findings_only")]
            ci = multi_ci(bt, lambda tk, t=t: [X1.nb(y[tk], R[a][tk], t) - X1.nb(y[tk], R[b][tk], t) for a, b in pairs], [f"{a}_minus_{b}" for a, b in pairs])
            row.update(ci); rows[f"{t:.3f}"] = row
        dca[ep] = dict(counts=dict(exams=int(len(Q)), cancers=int(y.sum())), net_benefit=rows,
                       note="net benefit per exam (TP/n - FP/n * t/(1-t)); single scores recalibrated on dev (logistic on their logit); combinations fitted on dev (X1 M2)")
    out["decision_curves_recalibrated"] = dca
    return out


# ------------------------------------------------------------------ P4 repeated screens
def p4(E, Edev):
    out = {"a_sybil_coefficient_given_comparator": {}}
    for ep in ("E1", "E7"):
        m = X1.population(E, ep); Q = E[m].reset_index(drop=True); y = Q.y1.to_numpy(float); bt = S.Boot(Q.pid.to_numpy()); sy = S.logit(Q.s1); r = {}
        for c in ("C1", "C2"):
            cs = Q[f"{c}_1"].to_numpy(float); X = np.c_[cs, sy]
            ci = multi_ci(bt, lambda t, X=X: [float(logreg(X[t], y[t])[2])], ["sybil_coef"])["sybil_coef"]
            ci["wald_p_two_sided_bootstrap_sd"] = float(2 * norm.sf(abs(ci["est"] / ci["sd"]))) if ci["sd"] else None
            r[c] = ci
        out["a_sybil_coefficient_given_comparator"][ep] = dict(counts=dict(exams=int(len(Q)), participants=int(Q.pid.nunique()), cancers=int(y.sum())), **r,
                                                              note="logistic y1 ~ C + logit(s1); Sybil's coefficient per logit unit; participant-bootstrap interval; replaces X1's in-sample LR test")
    md = X1.population(Edev, "E7"); D = Edev[md]; m = X1.population(E, "E7"); Q = E[m].reset_index(drop=True); yq = Q.y1.to_numpy(int); bt = S.Boot(Q.pid.to_numpy())
    cuts = {nm: float(np.quantile(D.loc[D.y1 == 1, col].to_numpy(float), 0.05)) for nm, col in (("sybil", "s1"), ("C2_findings_only", "C2_1"))}
    below = {nm: (Q[col] < cuts[nm]).to_numpy() for nm, col in (("sybil", "s1"), ("C2_findings_only", "C2_1"))}

    def st(t):
        yy = yq[t]; fp = (yy == 0).sum(); ca = (yy == 1).sum(); v = []
        for nm in ("sybil", "C2_findings_only"):
            b = below[nm][t]; v += [float((b & (yy == 0)).sum() / fp), float((b & (yy == 1)).sum() / ca)]
        return v + [v[2] - v[0], v[3] - v[1]]
    ci = multi_ci(bt, st, ["sybil_removed_share", "sybil_cancers_lost_share", "C2_removed_share", "C2_cancers_lost_share", "C2_minus_sybil_removed_share", "C2_minus_sybil_cancers_lost_share"])
    out["b_rule_out_positive_calls"] = dict(counts=dict(exams=int(len(Q)), participants=int(Q.pid.nunique()), cancers=int(yq.sum()), false_positive_calls=int((yq == 0).sum())),
                                            cuts_from_dev=cuts, cancers_lost=dict(sybil=int((below["sybil"] & (yq == 1)).sum()), C2_findings_only=int((below["C2_findings_only"] & (yq == 1)).sum())),
                                            participant_bootstrap=ci)
    return out


# ------------------------------------------------------------------ P5 harm at cuts fixed on dev
def p5(E, Edev):
    m = X1.population(E, "E1"); Q = E[m].reset_index(drop=True); y = Q.y1.to_numpy(int); bt = S.Boot(Q.pid.to_numpy()); n0 = int((y == 0).sum())
    md = X1.population(Edev, "E1"); D = Edev[md]; target = float(U3DEV["target_sensitivity"])
    c2_rad = float(u3_threshold(D.C2_1.to_numpy(float), D.y1.to_numpy(int), target)); c2_90 = float(np.quantile(D.loc[D.y1 == 0, "C2_1"].to_numpy(float), 0.90))
    cut = dict(rad=dict(sybil=("s1", float(U3DEV["table"]["sybil"]["threshold"])), C1_form=("C1_1", float(U3DEV["table"]["form_F"]["threshold"])), C2_findings_only=("C2_1", c2_rad)),
               tau90=dict(sybil=("s1", float(FROZEN["tau90_s1"])), C1_form=("C1_1", float(FROZEN["tau90_F1"])), C2_findings_only=("C2_1", c2_90)))
    rad = Q.positive_call.to_numpy(int) == 1; out = dict(counts=dict(exams=int(len(Q)), participants=int(Q.pid.nunique()), cancers=int(y.sum()), cancer_free=n0),
                                                         dev_target_sensitivity=target, radiologists_test_sensitivity=float(rad[y == 1].mean()), radiologists_fa_per_1000_exams=float((rad & (y == 0)).sum() / len(y) * 1000))
    for op, cc in cut.items():
        F = {k: (Q[col].to_numpy(float) >= thr) for k, (col, thr) in cc.items()}; F["radiologists"] = rad
        tab = {k: dict(threshold=None if k == "radiologists" else cc[k][1], flagged=int(f.sum()), sensitivity=float(f[y == 1].mean()), cancers_caught=int(f[y == 1].sum()),
                       fa_per_1000_exams=float((f & (y == 0)).sum() / len(y) * 1000), fa_per_1000_cancer_free=float((f & (y == 0)).sum() / n0 * 1000)) for k, f in F.items()}
        pairs = [("sybil", "radiologists"), ("sybil", "C1_form"), ("sybil", "C2_findings_only"), ("C2_findings_only", "radiologists")]

        def st(t, F=F, pairs=pairs):
            yy = y[t]; v = []
            for a, b in pairs:
                fa, fb = F[a][t], F[b][t]; v += [float(fa[yy == 1].mean() - fb[yy == 1].mean()), float(((fa & (yy == 0)).sum() - (fb & (yy == 0)).sum()) / len(yy) * 1000)]
            return v
        keys = [f"{a}_minus_{b}_{w}" for a, b in pairs for w in ("sensitivity", "fa_per_1000_exams")]
        out[op] = dict(table=tab, differences=multi_ci(bt, st, keys))
    out["note"] = "rad: cuts matched on dev to the dev radiologists' sensitivity (s4_u3_dev.json; C2 by the same rule here); tau90: the frozen 90th percentiles (C2: dev 90th percentile among y1 = 0)"
    return out


# ------------------------------------------------------------------ P6 z-fix alarm changes (outcome-free)
def p6(E, A, root):
    V = pd.read_csv(Path(A) / f"variant_{root}_zfix.csv", usecols=["series_uid", "s1"], low_memory=False).rename(columns={"s1": "v_s1"})
    J = E.merge(V, on="series_uid"); J = J[J.ratio <= FROZEN["zfix_ratio_max"]].reset_index(drop=True); bt = S.Boot(J.pid.to_numpy())
    out = dict(counts=dict(exams=int(len(J)), participants=int(J.pid.nunique()), ratio_zero=int((J.ratio == 0).sum())))
    for nm, thr in (("tau90", float(FROZEN["tau90_s1"])), ("tau_rad", float(U3DEV["table"]["sybil"]["threshold"]))):
        a, b = (J.s1 >= thr).to_numpy(), (J.v_s1 >= thr).to_numpy()
        ci = multi_ci(bt, lambda t, a=a, b=b: [float((a[t] != b[t]).mean()), float(((~a[t] & b[t]).sum() - (a[t] & ~b[t]).sum()) / len(t) * 1000)], ["discordant_share", "net_change_per_1000"])
        out[nm] = dict(threshold=thr, flagged_main=int(a.sum()), flagged_zfix=int(b.sum()), lost=int((a & ~b).sum()), gained=int((~a & b).sum()), **ci,
                       discordant_share_of_flagged_in_either=float((a != b).sum() / max(1, (a | b).sum())))
    return out


# ------------------------------------------------------------------ P8 data notes
def p8(E):
    m = X1.population(E, "E1"); Q = E[m]
    return dict(missing=dict(age=int(E.age.isna().sum()), gender=int(E.gender.isna().sum()), cigsmok=int(E.cigsmok.isna().sum()), age_scan=int(E.age_scan.isna().sum())),
                s1_distinct_values=int(E.s1.nunique()), s1_lowest=float(E.s1.min()), s1_ties_at_lowest=int((E.s1 == E.s1.min()).sum()), exams=int(len(E)),
                share_of_cancer_free_E1_exams_flagged_at_tau90=float((Q.loc[Q.y1 == 0, "s1"] >= FROZEN["tau90_s1"]).mean()),
                note="median imputation of reading items (nlst_l0.py, frozen) is not visible in the assembled table; only the demographics are counted")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("dev"); ap.add_argument("test"); ap.add_argument("tables"); ap.add_argument("split"); ap.add_argument("out")
    ap.add_argument("--roots", default="dev"); a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    b = L.build(a.tables, a.split); CM = X1.comparators(b)
    prsn = pd.read_csv(next(Path(a.tables).glob("*prsn*.csv")), usecols=["pid", "can_scr"]); cs = dict(zip(prsn.pid.astype(str), prsn.can_scr))

    def load(d, root):
        E = pd.read_csv(Path(d) / f"exams_{root}.csv", dtype={"pid": str}, low_memory=False); E["can_scr"] = E.pid.map(cs); return X1.scores(E, CM)
    Edev = load(a.dev, "dev")
    for root in a.roots.split(","):
        E, A = (Edev, a.dev) if root == "dev" else (load(a.test, "test"), a.test)
        res = dict(root=root, label=LABEL, P1_work_up_bias=p1(E), P2_censoring_E4=p2(E), P3_calibration=p3(E, Edev), P4_repeated_screens=p4(E, Edev),
                   P5_harm_at_dev_cuts=p5(E, Edev), P6_zfix_alarm_changes=p6(E, A, root), P8_data_notes=p8(E))
        p = out / f"x7_sensitivity_{root}.json"; p.write_bytes((json.dumps(res, indent=1, default=float) + "\n").encode("utf-8")); print("written", p)


if __name__ == "__main__":
    main()
