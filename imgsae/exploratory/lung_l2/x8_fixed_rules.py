"""Lung L2, plan X8 (docs/EXECUTION_LOG.md, 2026-11-21, plan committed 06a8eef before anything was computed): Sybil against
published rules that we did not fit, built from the NLST records. EXPLORATORY and POST HOC (protocol 11): nothing is confirmed;
every cell is reported; no claim for a group with fewer than 10 cancers.
R1 Lung-RADS (v1.1 rules; primary: part-solid with the upper assumption, solid part = whole nodule; secondary: lower assumption);
   "Lung-RADS + size" (category, then the mean diameter of the highest nodule).
R2 Brock (PanCan full model with spiculation; family history 0 for everyone, not in the public tables).
Endpoints E1 (main), E2, E4, E6 and W2 (E4 without cancers after a positive screen); added value of Sybil given each rule;
harm at cuts fixed on dev (E1); the dev code check against Pinsky et al. 2015.
Comparators C1 and C2 exactly as X1 (s7_added_value.comparators). Imports frozen modules, edits none.
usage (venv python): python x8_fixed_rules.py <dev assembled dir> <test assembled dir> <nlst tables dir> <split pickle> <out dir> --roots dev[,test]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, r"D:\Shayan\imgsae\exploratory\lung_l0")
import nlst_l0 as L  # noqa: E402
import s4_common as S  # noqa: E402
import s7_added_value as X1  # noqa: E402
from s4_u3 import threshold as u3_threshold  # noqa: E402
import x7_sensitivity as X7  # noqa: E402

LABEL = "EXPLORATORY, post hoc (plan X8, committed 06a8eef before anything was computed); nothing here is confirmed"
CAT_NAME = {1: "1", 2: "2", 3: "3", 4: "4A", 5: "4B", 6: "4X"}
PINSKY = dict(source="Pinsky et al., Ann Intern Med 2015;162:485-91 (whole NLST CT arm, Lung-RADS v1.0 applied retrospectively)",
              baseline=dict(false_positive_rate=dict(lung_rads=0.128, nlst=0.266), sensitivity=dict(lung_rads=0.849, nlst=0.935)),
              after_baseline=dict(false_positive_rate=dict(lung_rads=0.053, nlst=0.218), sensitivity=dict(lung_rads=0.786, nlst=0.938)))


def num(s): return pd.to_numeric(s, errors="coerce")


# ------------------------------------------------------------------ R1 and R2 per exam (no outcome is used here)
def cat_solid(d, st):
    if st == "stable": return 2
    if st == "grow": return 5 if d >= 8 else 4
    if st == "new": return 2 if d < 4 else 3 if d < 6 else 4 if d < 8 else 5
    return 2 if d < 6 else 3 if d < 8 else 4 if d < 15 else 5


def cat_part(d, st, upper):
    if st == "stable": return 2
    if upper:
        if st == "grow": return 5
        if st == "new": return 3 if d < 6 else 5
        return 2 if d < 6 else 4 if d < 8 else 5
    if st == "grow": return 4
    if st == "new": return 3 if d < 6 else 4
    return 2 if d < 6 else 3


def cat_ggn(d, st):
    if st in ("stable", "grow"): return 2
    return 2 if d < 30 else 3


def nodule_cat(r, upper):
    if r.type == "fat": return 1
    if r.type == "ggn": return cat_ggn(r.d, r.status)
    if r.type == "part": return cat_part(r.d, r.status, upper)
    return cat_solid(r.d, r.status)


def rules(tables):
    """exam table (pid, study_yr) with Lung-RADS (primary, lower), Lung-RADS + size, Brock, and the parts they are built from."""
    T = Path(tables)
    ctab = pd.read_csv(next(T.glob("*ctab_idc*.csv")), low_memory=False); ctabc = pd.read_csv(next(T.glob("*ctabc*.csv")), low_memory=False)
    prsn = pd.read_csv(next(T.glob("*prsn*.csv")), usecols=["pid", "age", "gender"], low_memory=False)
    for c in ["pid", "study_yr", "sct_ab_desc", "sct_ab_num", "sct_long_dia", "sct_perp_dia", "sct_margins", "sct_pre_att", "sct_epi_loc"]: ctab[c] = num(ctab[c])
    for c in ["pid", "study_yr", "sct_ab_num", "sct_ab_preexist", "sct_ab_gwth"]: ctabc[c] = num(ctabc[c])
    for c in ["pid", "age", "gender"]: prsn[c] = num(prsn[c])
    key = ["pid", "study_yr"]
    flags = ctab.assign(v=1).pivot_table(index=key, columns="sct_ab_desc", values="v", aggfunc="max").fillna(0)
    flags = flags.reindex(columns=[51, 52, 53, 56, 59, 62], fill_value=0)
    flags.columns = [f"ab{int(c)}" for c in flags.columns]; flags = flags.reset_index()

    nod = ctab[ctab.sct_ab_desc == 51].copy()
    nod["long"] = nod.sct_long_dia.fillna(4.0); nod["perp"] = nod.sct_perp_dia.fillna(nod["long"]); nod["d"] = (nod["long"] + nod["perp"]) / 2
    att = nod.sct_pre_att
    nod["type"] = np.where(att == 2, "ggn", np.where(att == 3, "part", np.where(att == 6, "fat", "solid")))
    cc = ctabc[["pid", "study_yr", "sct_ab_num", "sct_ab_preexist", "sct_ab_gwth"]].drop_duplicates(["pid", "study_yr", "sct_ab_num"])
    nod = nod.merge(cc, on=["pid", "study_yr", "sct_ab_num"], how="left")
    later = nod.study_yr > 0
    nod["status"] = np.select([later & (nod.sct_ab_gwth == 2), later & (nod.sct_ab_preexist == 1), later & (nod.sct_ab_preexist == 2)],
                              ["grow", "new", "stable"], "base")
    nod["cat_up"] = [nodule_cat(r, True) for r in nod.itertuples()]
    nod["cat_lo"] = [nodule_cat(r, False) for r in nod.itertuples()]
    nod["spic"] = (nod.sct_margins == 1).astype(int)

    # Brock per nodule
    nod = nod.merge(prsn, on="pid", how="left").merge(flags[key + ["ab59", "ab62"]], on=key, how="left")
    cnt = nod.groupby(key).sct_ab_num.transform("size").astype(float)
    cnt = np.where(nod.ab62 == 1, np.maximum(cnt, 6), cnt)
    size = nod["long"].clip(lower=1.0)
    nod["brock"] = (-6.7892 + 0.0287 * (nod.age + nod.study_yr - 62) + 0.6011 * (nod.gender == 2) + 0.2961 * 0 + 0.2953 * (nod.ab59 == 1)
                    - 5.3854 * ((size / 10) ** -0.5 - 1.58113883) + np.where(nod.type == "ggn", -0.1276, np.where(nod.type == "part", 0.377, 0.0))
                    + 0.6581 * nod.sct_epi_loc.isin([1, 4]) - 0.0824 * (cnt - 4) + 0.7729 * nod.spic)

    ex = flags[key + ["ab56"]].copy()
    ex["base_cat"] = np.where((flags.ab52 == 1) | (flags.ab62 == 1), 2, 1)
    for tag, col in (("up", "cat_up"), ("lo", "cat_lo")):
        top = nod.groupby(key)[col].max().rename(f"top_{tag}")
        n2 = nod.merge(top.reset_index(), on=key)
        hi = n2[n2[col] == n2[f"top_{tag}"]]
        agg = hi.groupby(key).agg(**{f"spic_{tag}": ("spic", "max"), f"d_{tag}": ("d", "max")}).reset_index()
        ex = ex.merge(top.reset_index(), on=key, how="left").merge(agg, on=key, how="left")
        c = np.maximum(ex.base_cat, ex[f"top_{tag}"].fillna(0)).astype(int)
        x4 = np.isin(c, [3, 4, 5]) & ((ex[f"spic_{tag}"].fillna(0).to_numpy() == 1) | (ex.ab56.to_numpy() == 1))
        ex[f"lr_{tag}"] = np.where(x4, 6, c)
        ex[f"d_{tag}"] = np.where(ex[f"top_{tag}"].fillna(0) >= c, ex[f"d_{tag}"].fillna(0), 0.0)
    ex["lr_size"] = ex.lr_up + ex.d_up / 1000.0
    ex = ex.merge(nod.groupby(key).brock.max().rename("brock").reset_index(), on=key, how="left")
    ex["brock"] = ex.brock.fillna(-99.0)
    status = nod.groupby(key).status.agg(lambda s: ",".join(sorted(set(s)))).rename("statuses").reset_index()
    return ex.merge(status, on=key, how="left"), nod


# ------------------------------------------------------------------ analyses
SCORES = ("sybil", "lr_up", "lr_lo", "lr_size", "brock", "size_alone", "C1_form", "C2_findings_only", "radiologists_call")


def score_cols(Q, s_col, fam):
    return dict(sybil=Q[s_col].to_numpy(float), lr_up=Q.lr_up.to_numpy(float), lr_lo=Q.lr_lo.to_numpy(float), lr_size=Q.lr_size.to_numpy(float),
                brock=Q.brock.to_numpy(float), size_alone=Q.max_dia.fillna(0).to_numpy(float), C1_form=Q[f"C1_{fam}"].to_numpy(float),
                C2_findings_only=Q[f"C2_{fam}"].to_numpy(float), radiologists_call=Q.positive_call.to_numpy(float))


def auroc_block(Q, y_col, s_col, fam, note):
    y = Q[y_col].to_numpy(int); pid = Q.pid.to_numpy(); bt = S.Boot(pid); n_c = int(y.sum())
    o = dict(counts=dict(exams=int(len(Q)), participants=int(len(np.unique(pid))), cancers=n_c), note=note + ("; n < 10 cancers: no claim" if n_c < 10 else ""))
    if n_c < 2: return o
    P = score_cols(Q, s_col, fam); others = [k for k in SCORES if k != "sybil"]

    def fn(t):
        a = {k: S.auc(y[t], P[k][t]) for k in SCORES}
        return [a[k] for k in SCORES] + [None if a["sybil"] is None or a[k] is None else a["sybil"] - a[k] for k in others]
    ci = X7.multi_ci(bt, fn, [f"auroc_{k}" for k in SCORES] + [f"sybil_minus_{k}" for k in others])
    o["auroc"] = {k[6:]: ci[k] for k in ci if k.startswith("auroc_")}; o["differences"] = {k: ci[k] for k in ci if k.startswith("sybil_minus_")}
    o["lung_rads_distribution"] = {CAT_NAME[int(c)]: dict(exams=int((Q.lr_up == c).sum()), cancers=int(((Q.lr_up == c) & (y == 1)).sum())) for c in range(1, 7)}
    return o


def dummies(cat):
    cat = np.asarray(cat, int); return np.column_stack([(cat == c).astype(float) for c in (3, 4, 5, 6)])   # 1 and 2 pooled as reference


def added_value(E, Edev, ep):
    y_col, s_col, fam, _ = X1.EP[ep]; m = X1.population(E, ep); Q = E[m].reset_index(drop=True); y = Q[y_col].to_numpy(int)
    md = X1.population(Edev, ep); D = Edev[md].reset_index(drop=True); yd = D[y_col].to_numpy(int)
    bt = S.Boot(Q.pid.to_numpy()); sy, syd = S.logit(Q[s_col]), S.logit(Edev.loc[md, s_col]); fo = X1.folds10(Q.pid.to_numpy()); out = {}
    for rule, Xq, Xd in (("lung_rads", dummies(Q.lr_up), dummies(D.lr_up)), ("brock", Q.brock.to_numpy(float)[:, None], D.brock.to_numpy(float)[:, None])):
        Xs = np.c_[Xq, sy]
        coef = X7.multi_ci(bt, lambda t, Xs=Xs: [float(X7.logreg(Xs[t], y[t])[-1])], ["sybil_coef"])["sybil_coef"]
        coef["wald_p_two_sided_bootstrap_sd"] = float(2 * norm.sf(abs(coef["est"] / coef["sd"]))) if coef["sd"] else None
        b0, b1 = X7.logreg(Xd, yd), X7.logreg(np.c_[Xd, syd], yd)
        p0 = np.column_stack([np.ones(len(y)), Xq]) @ b0; p1 = np.column_stack([np.ones(len(y)), Xs]) @ b1
        c0, c1 = S.crossfit(y, Xq, fo), S.crossfit(y, Xs, fo)
        out[rule] = dict(sybil_coefficient_given_rule=coef, dev_fitted_gain=S.dauc_ci(y, p1, p0, bt), crossfit_gain=S.dauc_ci(y, c1, c0, bt),
                         auroc_rule_alone_dev_fitted=S.auc(y, p0), auroc_rule_plus_sybil_dev_fitted=S.auc(y, p1))
    out["counts"] = dict(exams=int(len(Q)), participants=int(Q.pid.nunique()), cancers=int(y.sum()))
    out["note"] = "logistic y ~ rule + logit(Sybil); Lung-RADS as indicators of 3, 4A, 4B, 4X (1 and 2 pooled); Brock as its logit"
    return out


def harm(E, Edev):
    m = X1.population(E, "E1"); Q = E[m].reset_index(drop=True); y = Q.y1.to_numpy(int); bt = S.Boot(Q.pid.to_numpy())
    md = X1.population(Edev, "E1"); D = Edev[md].reset_index(drop=True); yd = D.y1.to_numpy(int); sd = D.s1.to_numpy(float)
    F = {"lung_rads_3_or_higher": Q.lr_up.to_numpy() >= 3, "lung_rads_4A_or_higher": Q.lr_up.to_numpy() >= 4, "radiologists_call": Q.positive_call.to_numpy() == 1}
    cuts = {}
    for nm, k in (("3", 3), ("4A", 4)):
        sens = float((D.lr_up.to_numpy()[yd == 1] >= k).mean()); cuts[f"sybil_at_dev_sensitivity_of_lung_rads_{nm}"] = (float(u3_threshold(sd, yd, sens)), dict(dev_sensitivity=sens))
    fa = float(((D.lr_up.to_numpy() >= 3) & (yd == 0)).sum() / (yd == 0).sum())
    cuts["sybil_at_dev_false_alarm_rate_of_lung_rads_3"] = (float(np.quantile(sd[yd == 0], 1 - fa)), dict(dev_false_alarm_share_of_cancer_free=fa))
    for nm, (thr, info) in cuts.items(): F[nm] = Q.s1.to_numpy(float) >= thr
    n0 = int((y == 0).sum())
    tab = {k: dict(flagged=int(f.sum()), cancers_caught=int(f[y == 1].sum()), sensitivity=float(f[y == 1].mean()),
                   fa_per_1000_exams=float((f & (y == 0)).sum() / len(y) * 1000), fa_per_1000_cancer_free=float((f & (y == 0)).sum() / n0 * 1000)) for k, f in F.items()}
    for nm, (thr, info) in cuts.items(): tab[nm].update(threshold=thr, **info)
    pairs = [("sybil_at_dev_sensitivity_of_lung_rads_3", "lung_rads_3_or_higher"), ("sybil_at_dev_sensitivity_of_lung_rads_4A", "lung_rads_4A_or_higher"),
             ("sybil_at_dev_false_alarm_rate_of_lung_rads_3", "lung_rads_3_or_higher"), ("lung_rads_3_or_higher", "radiologists_call")]

    def st(t):
        yy = y[t]; v = []
        for a, b in pairs:
            fa_, fb = F[a][t], F[b][t]; v += [float(fa_[yy == 1].mean() - fb[yy == 1].mean()), float(((fa_ & (yy == 0)).sum() - (fb & (yy == 0)).sum()) / len(yy) * 1000)]
        return v
    keys = [f"{a}_minus_{b}_{w}" for a, b in pairs for w in ("sensitivity", "fa_per_1000_exams")]
    return dict(counts=dict(exams=int(len(Q)), participants=int(Q.pid.nunique()), cancers=int(y.sum()), cancer_free=n0), table=tab, differences=X7.multi_ci(bt, st, keys))


def pinsky_check(E):
    """share of cancer-free exams called positive and 1-year sensitivity, baseline and after baseline: Lung-RADS >= 3 and the NLST call."""
    out = {}
    for nm, mask in (("baseline", E.study_yr == 0), ("after_baseline", E.study_yr > 0)):
        Q = E[mask & E.y1.notna()]; y = Q.y1.to_numpy(int)
        r = {}
        for k, f in (("lung_rads", Q.lr_up.to_numpy() >= 3), ("nlst", Q.positive_call.to_numpy() == 1)):
            r[k] = dict(false_positive_rate=float(f[y == 0].mean()), sensitivity=float(f[y == 1].mean()) if (y == 1).any() else None)
        out[nm] = dict(exams=int(len(Q)), cancers=int(y.sum()), **r)
    out["reference"] = PINSKY
    return out


def describe(E, nod_root):
    return dict(lung_rads_primary={CAT_NAME[c]: int((E.lr_up == c).sum()) for c in range(1, 7)}, lung_rads_lower={CAT_NAME[c]: int((E.lr_lo == c).sum()) for c in range(1, 7)},
                exams_changed_by_part_solid_assumption=int((E.lr_up != E.lr_lo).sum()), exams_without_nodule_ge_4mm=int((E.brock <= -98).sum()),
                nodule_status_counts=nod_root.status.value_counts().to_dict(), nodule_type_counts=nod_root.type.value_counts().to_dict(), exams=int(len(E)))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("dev"); ap.add_argument("test"); ap.add_argument("tables"); ap.add_argument("split"); ap.add_argument("out")
    ap.add_argument("--roots", default="dev"); a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    b = L.build(a.tables, a.split); CM = X1.comparators(b)
    R, nod = rules(a.tables); R["pid"] = R.pid.astype(int).astype(str); R["study_yr"] = R.study_yr.astype(int)
    R = R[["pid", "study_yr", "lr_up", "lr_lo", "lr_size", "brock", "d_up"]]
    prsn = pd.read_csv(next(Path(a.tables).glob("*prsn*.csv")), usecols=["pid", "can_scr"]); cs = dict(zip(prsn.pid.astype(str), prsn.can_scr))

    def load(d, root):
        E = pd.read_csv(Path(d) / f"exams_{root}.csv", dtype={"pid": str}, low_memory=False); E["can_scr"] = E.pid.map(cs); E = X1.scores(E, CM)
        n = len(E); E = E.merge(R, on=["pid", "study_yr"], how="left")
        if len(E) != n: raise SystemExit("REFUSED: the rule table duplicated exam rows")
        for c in ("lr_up", "lr_lo"): E[c] = E[c].fillna(1).astype(int)          # no CT abnormality recorded: category 1
        E["lr_size"] = E.lr_size.fillna(1.0); E["brock"] = E.brock.fillna(-99.0)
        return E
    Edev = load(a.dev, "dev")
    for root in a.roots.split(","):
        E = Edev if root == "dev" else load(a.test, "test")
        pids = set(E.pid.astype(int)); nod_root = nod[nod.pid.isin(pids)]
        res = dict(root=root, label=LABEL, description=describe(E, nod_root), pinsky_check=pinsky_check(E))
        b4 = (E.study_yr == 0) & E.y6.notna()
        res["auroc"] = {
            "E1_1_year_all_screens": auroc_block(E[X1.population(E, "E1")].reset_index(drop=True), "y1", "s1", 1, "main endpoint"),
            "E2_1_year_baseline": auroc_block(E[X1.population(E, "E2")].reset_index(drop=True), "y1", "s1", 1, ""),
            "E4_6_years_baseline": auroc_block(E[X1.population(E, "E4")].reset_index(drop=True), "y6", "s6", 6, ""),
            "E6_1_year_negative_calls": auroc_block(E[X1.population(E, "E6")].reset_index(drop=True), "y1", "s1", 1, "exams the radiologists called negative"),
            "W2_E4_without_cancers_after_a_positive_screen": auroc_block(E[b4 & ~((E.y6 == 1) & (E.can_scr == 1))].reset_index(drop=True), "y6", "s6", 6,
                                                                         "cases: 6-year cancers with can_scr 2, 3 or 4 (as X7 W2)")}
        res["added_value"] = {ep: added_value(E, Edev, ep) for ep in ("E1", "E4")}
        res["harm_at_dev_fixed_cuts_E1"] = harm(E, Edev)
        p = out / f"x8_fixed_rules_{root}.json"; p.write_bytes((json.dumps(res, indent=1, default=float) + "\n").encode("utf-8")); print("written", p)


if __name__ == "__main__":
    main()
