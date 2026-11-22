"""Lung L2, plan X9 (docs/EXECUTION_LOG.md, 2026-11-22, plan committed 96453cc before anything was computed). EXPLORATORY and POST HOC
(protocol 11): nothing is confirmed; every cell is reported; no claim for a group with fewer than 10 cancers.
Part A: X8 with the corrections found by two independent reviews (Brock and Lung-RADS coding in fitted models; 4X on any nodule;
         growth "unable to determine" = baseline rules; attenuation change = growing; growing part-solid < 4 mm = 4A; Brock without fat
         nodules and with the lingula as upper lobe; cross-fitted rule-alone AUROCs written out; Brock with a dev-fitted no-nodule level).
Part B: threshold measures (sensitivity, specificity, PPV, NPV, LR+, LR-, per 1,000 exams) at operating points set on cancer-free dev exams
         only, and AUPRC (average precision).
Imports frozen modules and x8_fixed_rules.py, edits none.
usage (venv python): python x9_rules_thresholds.py <dev assembled dir> <test assembled dir> <nlst tables dir> <split pickle> <out dir> --roots dev[,test]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.metrics import average_precision_score

HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, r"D:\Shayan\imgsae\exploratory\lung_l0")
import nlst_l0 as L  # noqa: E402
import s4_common as S  # noqa: E402
import s7_added_value as X1  # noqa: E402
import x7_sensitivity as X7  # noqa: E402
import x8_fixed_rules as X8  # noqa: E402

LABEL = "EXPLORATORY, post hoc (plan X9, committed 96453cc before anything was computed); nothing here is confirmed"
CAT_NAME = X8.CAT_NAME


def num(s): return pd.to_numeric(s, errors="coerce")


# ------------------------------------------------------------------ part A: corrected rules (no outcome is used here)
def cat_solid(d, st): return X8.cat_solid(d, st)


def cat_part(d, st, upper):
    if upper and st == "grow": return 5 if d >= 4 else 4          # correction 5: new or growing solid part < 4 mm = 4A
    return X8.cat_part(d, st, upper)


def cat_ggn(d, st): return X8.cat_ggn(d, st)


def nodule_cat(r, upper):
    if r.type == "fat": return 1
    if r.type == "ggn": return cat_ggn(r.d, r.status)
    if r.type == "part": return cat_part(r.d, r.status, upper)
    return cat_solid(r.d, r.status)


def rules(tables):
    """exam table (pid, study_yr): corrected Lung-RADS (upper, lower), Lung-RADS + size, Brock (NaN = no scored nodule)."""
    T = Path(tables)
    ctab = pd.read_csv(next(T.glob("*ctab_idc*.csv")), low_memory=False); ctabc = pd.read_csv(next(T.glob("*ctabc*.csv")), low_memory=False)
    prsn = pd.read_csv(next(T.glob("*prsn*.csv")), usecols=["pid", "age", "gender"], low_memory=False)
    for c in ["pid", "study_yr", "sct_ab_desc", "sct_ab_num", "sct_long_dia", "sct_perp_dia", "sct_margins", "sct_pre_att", "sct_epi_loc"]: ctab[c] = num(ctab[c])
    for c in ["pid", "study_yr", "sct_ab_num", "sct_ab_preexist", "sct_ab_gwth", "sct_ab_attn"]: ctabc[c] = num(ctabc[c])
    for c in ["pid", "age", "gender"]: prsn[c] = num(prsn[c])
    key = ["pid", "study_yr"]
    flags = ctab.assign(v=1).pivot_table(index=key, columns="sct_ab_desc", values="v", aggfunc="max").fillna(0)
    flags = flags.reindex(columns=[51, 52, 53, 56, 59, 62], fill_value=0)
    flags.columns = [f"ab{int(c)}" for c in flags.columns]; flags = flags.reset_index()

    nod = ctab[ctab.sct_ab_desc == 51].copy()
    nod["long"] = nod.sct_long_dia.fillna(4.0); nod["perp"] = nod.sct_perp_dia.fillna(nod["long"]); nod["d"] = (nod["long"] + nod["perp"]) / 2
    att = nod.sct_pre_att
    nod["type"] = np.where(att == 2, "ggn", np.where(att == 3, "part", np.where(att == 6, "fat", "solid")))
    cc = ctabc[["pid", "study_yr", "sct_ab_num", "sct_ab_preexist", "sct_ab_gwth", "sct_ab_attn"]].drop_duplicates(["pid", "study_yr", "sct_ab_num"])
    nod = nod.merge(cc, on=["pid", "study_yr", "sct_ab_num"], how="left")
    later = nod.study_yr > 0
    grow = later & ((nod.sct_ab_gwth == 2) | (nod.sct_ab_attn == 2))                  # correction 4: attenuation change = growing
    stable = later & (nod.sct_ab_preexist == 2) & (nod.sct_ab_gwth == 1)               # correction 4: stable only if growth = "No"
    nod["status"] = np.select([grow, later & (nod.sct_ab_preexist == 1), stable], ["grow", "new", "stable"], "base")
    nod["cat_up"] = [nodule_cat(r, True) for r in nod.itertuples()]
    nod["cat_lo"] = [nodule_cat(r, False) for r in nod.itertuples()]
    nod["spic"] = (nod.sct_margins == 1).astype(int)

    # Brock per nodule (correction 6: fat-containing nodules not scored; lingula = upper lobe)
    nod = nod.merge(prsn, on="pid", how="left").merge(flags[key + ["ab59", "ab62"]], on=key, how="left")
    cnt = nod.groupby(key).sct_ab_num.transform("size").astype(float)
    cnt = np.where(nod.ab62 == 1, np.maximum(cnt, 6), cnt)
    size = nod["long"].clip(lower=1.0)
    br = (-6.7892 + 0.0287 * (nod.age + nod.study_yr - 62) + 0.6011 * (nod.gender == 2) + 0.2961 * 0 + 0.2953 * (nod.ab59 == 1)
          - 5.3854 * ((size / 10) ** -0.5 - 1.58113883) + np.where(nod.type == "ggn", -0.1276, np.where(nod.type == "part", 0.377, 0.0))
          + 0.6581 * nod.sct_epi_loc.isin([1, 4, 5]) - 0.0824 * (cnt - 4) + 0.7729 * nod.spic)
    nod["brock"] = np.where(nod.type == "fat", np.nan, br)

    ex = flags[key + ["ab56"]].copy()
    ex["base_cat"] = np.where((flags.ab52 == 1) | (flags.ab62 == 1), 2, 1)
    for tag, col in (("up", "cat_up"), ("lo", "cat_lo")):
        nod[f"x4_{tag}"] = (np.isin(nod[col], [3, 4, 5]) & (nod.spic == 1)).astype(int)       # correction 3: 4X on any nodule
        top = nod.groupby(key)[col].max().rename(f"top_{tag}")
        n2 = nod.merge(top.reset_index(), on=key)
        hi = n2[n2[col] == n2[f"top_{tag}"]]
        agg = hi.groupby(key).agg(**{f"d_{tag}": ("d", "max")}).reset_index()
        anyx = nod.groupby(key)[f"x4_{tag}"].max().rename(f"anyx_{tag}").reset_index()
        ex = ex.merge(top.reset_index(), on=key, how="left").merge(agg, on=key, how="left").merge(anyx, on=key, how="left")
        c = np.maximum(ex.base_cat, ex[f"top_{tag}"].fillna(0)).astype(int)
        x4 = np.isin(c, [3, 4, 5]) & ((ex[f"anyx_{tag}"].fillna(0).to_numpy() == 1) | (ex.ab56.to_numpy() == 1))
        ex[f"lr_{tag}"] = np.where(x4, 6, c)
        ex[f"d_{tag}"] = np.where(ex[f"top_{tag}"].fillna(0) >= c, ex[f"d_{tag}"].fillna(0), 0.0)
    ex["lr_size"] = ex.lr_up + ex.d_up / 1000.0
    ex = ex.merge(nod.groupby(key).brock.max().rename("brock").reset_index(), on=key, how="left")   # NaN: no scored nodule
    return ex, nod


# ------------------------------------------------------------------ part A: analyses
SCORES = ("sybil", "lr_up", "lr_lo", "lr_size", "brock", "brock_dev_level", "size_alone", "C1_form", "C2_findings_only", "radiologists_call")


def brock_design(B):
    B = np.asarray(B, float); nn = ~np.isfinite(B); return np.column_stack([nn.astype(float), np.where(nn, 0.0, B)])


def lr_design(cat):
    cat = np.asarray(cat, int); return np.column_stack([(cat == c).astype(float) for c in (2, 3, 4, 5, 6)])   # 1 = reference


def brock_level_coef(Edev, ep):
    y_col = X1.EP[ep][0]; D = Edev[X1.population(Edev, ep)]; return X7.logreg(brock_design(D.brock_raw), D[y_col].to_numpy(int))


def score_cols(Q, s_col, fam, bcoef):
    return dict(sybil=Q[s_col].to_numpy(float), lr_up=Q.lr_up.to_numpy(float), lr_lo=Q.lr_lo.to_numpy(float), lr_size=Q.lr_size.to_numpy(float),
                brock=Q.brock.to_numpy(float), brock_dev_level=np.column_stack([np.ones(len(Q)), brock_design(Q.brock_raw)]) @ bcoef,
                size_alone=Q.max_dia.fillna(0).to_numpy(float), C1_form=Q[f"C1_{fam}"].to_numpy(float),
                C2_findings_only=Q[f"C2_{fam}"].to_numpy(float), radiologists_call=Q.positive_call.to_numpy(float))


def auroc_block(Q, y_col, s_col, fam, bcoef, note):
    y = Q[y_col].to_numpy(int); pid = Q.pid.to_numpy(); bt = S.Boot(pid); n_c = int(y.sum())
    o = dict(counts=dict(exams=int(len(Q)), participants=int(len(np.unique(pid))), cancers=n_c,
                         cancers_in_exams_without_scored_nodule=int(((~np.isfinite(Q.brock_raw.to_numpy(float))) & (y == 1)).sum())),
             note=note + ("; n < 10 cancers: no claim" if n_c < 10 else ""), brock_dev_level_coef=[float(v) for v in bcoef])
    if n_c < 2: return o
    P = score_cols(Q, s_col, fam, bcoef); others = [k for k in SCORES if k != "sybil"]

    def fn(t):
        a = {k: S.auc(y[t], P[k][t]) for k in SCORES}
        return [a[k] for k in SCORES] + [None if a["sybil"] is None or a[k] is None else a["sybil"] - a[k] for k in others]
    ci = X7.multi_ci(bt, fn, [f"auroc_{k}" for k in SCORES] + [f"sybil_minus_{k}" for k in others])
    o["auroc"] = {k[6:]: ci[k] for k in ci if k.startswith("auroc_")}; o["differences"] = {k: ci[k] for k in ci if k.startswith("sybil_minus_")}
    o["lung_rads_distribution"] = {CAT_NAME[int(c)]: dict(exams=int((Q.lr_up == c).sum()), cancers=int(((Q.lr_up == c) & (y == 1)).sum())) for c in range(1, 7)}
    return o


def added_value(E, Edev, ep):
    y_col, s_col, fam, _ = X1.EP[ep]; m = X1.population(E, ep); Q = E[m].reset_index(drop=True); y = Q[y_col].to_numpy(int)
    md = X1.population(Edev, ep); D = Edev[md].reset_index(drop=True); yd = D[y_col].to_numpy(int)
    bt = S.Boot(Q.pid.to_numpy()); sy, syd = S.logit(Q[s_col]), S.logit(D[s_col]); fo = X1.folds10(Q.pid.to_numpy()); out = {}
    for rule, Xq, Xd, raw in (("lung_rads", lr_design(Q.lr_up), lr_design(D.lr_up), Q.lr_up.to_numpy(float)),
                              ("brock", brock_design(Q.brock_raw), brock_design(D.brock_raw), Q.brock.to_numpy(float))):
        Xs = np.c_[Xq, sy]
        coef = X7.multi_ci(bt, lambda t, Xs=Xs: [float(X7.logreg(Xs[t], y[t])[-1])], ["sybil_coef"])["sybil_coef"]
        coef["wald_p_two_sided_bootstrap_sd"] = float(2 * norm.sf(abs(coef["est"] / coef["sd"]))) if coef.get("sd") else None
        b0, b1 = X7.logreg(Xd, yd), X7.logreg(np.c_[Xd, syd], yd)
        p0 = np.column_stack([np.ones(len(y)), Xq]) @ b0; p1 = np.column_stack([np.ones(len(y)), Xs]) @ b1
        c0, c1 = S.crossfit(y, Xq, fo), S.crossfit(y, Xs, fo)
        out[rule] = dict(sybil_coefficient_given_rule=coef,
                         dev_fitted_gain=S.dauc_ci(y, p1, p0, bt), gain_over_unfitted_rule=S.dauc_ci(y, p1, raw, bt), crossfit_gain=S.dauc_ci(y, c1, c0, bt),
                         auroc_unfitted_rule=S.auc(y, raw), auroc_rule_alone_dev_fitted=S.auc(y, p0), auroc_rule_alone_crossfit=S.auc(y, c0),
                         auroc_rule_plus_sybil_dev_fitted=S.auc(y, p1), auroc_rule_plus_sybil_crossfit=S.auc(y, c1))
    out["counts"] = dict(exams=int(len(Q)), participants=int(Q.pid.nunique()), cancers=int(y.sum()))
    out["note"] = ("logistic y ~ rule + logit(Sybil); Lung-RADS as indicators of 2, 3, 4A, 4B, 4X (1 = reference); "
                   "Brock as indicator 'no scored nodule' + Brock logit (0 when no nodule)")
    return out


# ------------------------------------------------------------------ part B: threshold measures and AUPRC
MEAS = ("sensitivity", "specificity", "ppv", "npv", "lr_pos", "lr_neg", "fa_per_1000_exams", "missed_per_1000_exams", "flagged_per_1000_exams")
DIFF = ("sensitivity", "specificity", "ppv", "npv", "fa_per_1000_exams", "missed_per_1000_exams")


def measures(f, yy):
    pos = yy == 1; n = len(yy); tp = int((f & pos).sum()); fp = int((f & ~pos).sum()); fn_ = int((~f & pos).sum()); tn = int((~f & ~pos).sum())
    sens = tp / (tp + fn_) if tp + fn_ else None; spec = tn / (tn + fp) if tn + fp else None
    ppv = tp / (tp + fp) if tp + fp else None; npv = tn / (tn + fn_) if tn + fn_ else None
    lrp = sens / (1 - spec) if sens is not None and spec is not None and spec < 1 else None
    lrn = (1 - sens) / spec if sens is not None and spec else None
    return dict(sensitivity=sens, specificity=spec, ppv=ppv, npv=npv, lr_pos=lrp, lr_neg=lrn, fa_per_1000_exams=fp / n * 1000,
                missed_per_1000_exams=fn_ / n * 1000, flagged_per_1000_exams=(tp + fp) / n * 1000), dict(tp=tp, fp=fp, fn=fn_, tn=tn)


def thresholds(E, Edev, ep):
    y_col, s_col, fam, _ = X1.EP[ep]
    Q = E[X1.population(E, ep)].reset_index(drop=True); D = Edev[X1.population(Edev, ep)].reset_index(drop=True)
    y = Q[y_col].to_numpy(int); yd = D[y_col].to_numpy(int); bt = S.Boot(Q.pid.to_numpy()); n_c = int(y.sum())
    cont = dict(sybil=s_col, form=f"C1_{fam}", findings_only=f"C2_{fam}", brock="brock")
    fixed = dict(lung_rads_3=lambda Z: Z.lr_up.to_numpy() >= 3, lung_rads_4A=lambda Z: Z.lr_up.to_numpy() >= 4, radiologists_call=lambda Z: Z.positive_call.to_numpy() == 1)
    ops = {"OP_L3": ("lung_rads_3", float(fixed["lung_rads_3"](D)[yd == 0].mean())), "OP_L4": ("lung_rads_4A", float(fixed["lung_rads_4A"](D)[yd == 0].mean())),
           "OP_R": ("radiologists_call", float(fixed["radiologists_call"](D)[yd == 0].mean())), "OP_90": (None, 0.10)}
    F, cuts = {k: fn(Q) for k, fn in fixed.items()}, {}
    for op, (ref, fa) in ops.items():
        for nm, col in cont.items():
            s0 = D[col].to_numpy(float)[yd == 0]; thr = float(np.quantile(s0, 1 - fa))
            # ties at the cut (Sybil's calibrated score has steps; Brock has one block without a nodule): flag with >= or >,
            # whichever gives the dev false-alarm share closer to the target (dev-check fix, logged before the test run)
            strict = abs(float((s0 > thr).mean()) - fa) < abs(float((s0 >= thr).mean()) - fa)
            F[f"{nm}@{op}"] = (Q[col].to_numpy(float) > thr) if strict else (Q[col].to_numpy(float) >= thr)
            cuts[f"{nm}@{op}"] = dict(threshold=thr, flag_rule=">" if strict else ">=", target_dev_false_alarm_share=fa,
                                      achieved_dev_false_alarm_share=float(((s0 > thr) if strict else (s0 >= thr)).mean()),
                                      test_false_alarm_share=float((F[f"{nm}@{op}"][y == 0]).mean()))
    pairs = []
    for op, (ref, _) in ops.items():
        pairs += [(f"sybil@{op}", f"form@{op}"), (f"sybil@{op}", f"findings_only@{op}")]
        if ref: pairs += [(f"sybil@{op}", ref), (f"form@{op}", ref)]
    names = list(F)

    def fn(t):
        yy = y[t]; M = {k: measures(F[k][t], yy)[0] for k in names}; v = [M[k][m] for k in names for m in MEAS]
        for a, b in pairs:
            v += [None if M[a][m] is None or M[b][m] is None else M[a][m] - M[b][m] for m in DIFF]
        return v
    keys = [f"{k}|{m}" for k in names for m in MEAS] + [f"{a}_minus_{b}|{m}" for a, b in pairs for m in DIFF]
    ci = X7.multi_ci(bt, fn, keys)
    table = {k: dict(counts=measures(F[k], y)[1], **{m: ci[f"{k}|{m}"] for m in MEAS}) for k in names}
    for k, c in cuts.items(): table[k]["cut"] = c
    diffs = {f"{a}_minus_{b}": {m: ci[f"{a}_minus_{b}|{m}"] for m in DIFF} for a, b in pairs}

    P = dict(sybil=Q[s_col].to_numpy(float), form=Q[f"C1_{fam}"].to_numpy(float), findings_only=Q[f"C2_{fam}"].to_numpy(float), brock=Q.brock.to_numpy(float),
             lung_rads=Q.lr_up.to_numpy(float), lung_rads_plus_size=Q.lr_size.to_numpy(float), size_alone=Q.max_dia.fillna(0).to_numpy(float),
             radiologists_call=Q.positive_call.to_numpy(float))
    others = ("form", "findings_only", "lung_rads", "brock")

    def ap(t):
        yy = y[t]
        if yy.sum() == 0: return [None] * (len(P) + len(others))
        a = {k: float(average_precision_score(yy, P[k][t])) for k in P}
        return [a[k] for k in P] + [a["sybil"] - a[k] for k in others]
    aci = X7.multi_ci(bt, ap, [f"auprc_{k}" for k in P] + [f"sybil_minus_{k}" for k in others])
    return dict(counts=dict(exams=int(len(Q)), participants=int(Q.pid.nunique()), cancers=n_c, prevalence=float(y.mean())),
                note="cuts set on cancer-free dev exams only" + ("; n < 10 cancers: no claim" if n_c < 10 else ""),
                operating_points={op: dict(matched_to=ref, dev_false_alarm_share=fa) for op, (ref, fa) in ops.items()},
                table=table, differences=diffs,
                auprc=dict(values={k[6:]: aci[k] for k in aci if k.startswith("auprc_")},
                           differences={k: aci[k] for k in aci if k.startswith("sybil_minus_")},
                           note="average precision; a score with no skill has AUPRC = prevalence"))


# ------------------------------------------------------------------ main
def describe(E, R8):
    M = E[["pid", "study_yr", "lr_up"]].merge(R8, on=["pid", "study_yr"], how="left"); x8 = M.lr_up_x8.fillna(1).astype(int)
    moved = pd.crosstab(x8.map(CAT_NAME), M.lr_up.map(CAT_NAME))
    return dict(lung_rads_primary={CAT_NAME[c]: int((E.lr_up == c).sum()) for c in range(1, 7)}, lung_rads_lower={CAT_NAME[c]: int((E.lr_lo == c).sum()) for c in range(1, 7)},
                exams_changed_by_part_solid_assumption=int((E.lr_up != E.lr_lo).sum()), exams_without_scored_nodule=int((~np.isfinite(E.brock_raw)).sum()),
                exams_whose_primary_category_changed_from_x8=int((x8.to_numpy() != M.lr_up.to_numpy()).sum()),
                x8_to_x9_category_table={str(i): {str(j): int(moved.loc[i, j]) for j in moved.columns} for i in moved.index}, exams=int(len(E)))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("dev"); ap.add_argument("test"); ap.add_argument("tables"); ap.add_argument("split"); ap.add_argument("out")
    ap.add_argument("--roots", default="dev"); a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    b = L.build(a.tables, a.split); CM = X1.comparators(b)
    R, nod = rules(a.tables); R["pid"] = R.pid.astype(int).astype(str); R["study_yr"] = R.study_yr.astype(int)
    R = R[["pid", "study_yr", "lr_up", "lr_lo", "lr_size", "brock", "d_up"]]
    R8, _ = X8.rules(a.tables); R8["pid"] = R8.pid.astype(int).astype(str); R8["study_yr"] = R8.study_yr.astype(int)
    R8 = R8[["pid", "study_yr", "lr_up"]].rename(columns={"lr_up": "lr_up_x8"})
    prsn = pd.read_csv(next(Path(a.tables).glob("*prsn*.csv")), usecols=["pid", "can_scr"]); cs = dict(zip(prsn.pid.astype(str), prsn.can_scr))

    def load(d, root):
        E = pd.read_csv(Path(d) / f"exams_{root}.csv", dtype={"pid": str}, low_memory=False); E["can_scr"] = E.pid.map(cs); E = X1.scores(E, CM)
        n = len(E); E = E.merge(R, on=["pid", "study_yr"], how="left")
        if len(E) != n: raise SystemExit("REFUSED: the rule table duplicated exam rows")
        for c in ("lr_up", "lr_lo"): E[c] = E[c].fillna(1).astype(int)          # no CT abnormality recorded: category 1
        E["lr_size"] = E.lr_size.fillna(1.0); E["brock_raw"] = E.brock; E["brock"] = E.brock.fillna(-99.0)   # rank: no scored nodule lowest
        return E
    Edev = load(a.dev, "dev")
    bc = {ep: brock_level_coef(Edev, ep) for ep in ("E1", "E2", "E4")}
    for root in a.roots.split(","):
        E = Edev if root == "dev" else load(a.test, "test")
        res = dict(root=root, label=LABEL, description=describe(E, R8), pinsky_check=X8.pinsky_check(E))
        b4 = (E.study_yr == 0) & E.y6.notna()
        res["auroc"] = {
            "E1_1_year_all_screens": auroc_block(E[X1.population(E, "E1")].reset_index(drop=True), "y1", "s1", 1, bc["E1"], "main endpoint"),
            "E2_1_year_baseline": auroc_block(E[X1.population(E, "E2")].reset_index(drop=True), "y1", "s1", 1, bc["E2"], ""),
            "E4_6_years_baseline": auroc_block(E[X1.population(E, "E4")].reset_index(drop=True), "y6", "s6", 6, bc["E4"], ""),
            "W2_E4_without_cancers_after_a_positive_screen": auroc_block(E[b4 & ~((E.y6 == 1) & (E.can_scr == 1))].reset_index(drop=True), "y6", "s6", 6, bc["E4"],
                                                                         "cases: 6-year cancers with can_scr 2, 3 or 4 (as X7 W2)")}
        res["added_value"] = {ep: added_value(E, Edev, ep) for ep in ("E1", "E4")}
        res["thresholds"] = {ep: thresholds(E, Edev, ep) for ep in ("E1", "E2", "E4")}
        p = out / f"x9_rules_thresholds_{root}.json"; p.write_bytes((json.dumps(res, indent=1, default=float) + "\n").encode("utf-8")); print("written", p)


if __name__ == "__main__":
    main()
