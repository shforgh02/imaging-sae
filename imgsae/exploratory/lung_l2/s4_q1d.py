"""Lung L2, S4, Q1d / U1b (docs/LUNG_L2_PROTOCOL.md 9.7): score change inside one exam when only a technical factor changes.
(i) kernel pairs (tier D4): sharp (main) vs soft (pair) reconstruction of the same acquisition;
(ii) z-fix (D5): slices placed at their true spacing vs Sybil as published.
Statistics per horizon t = 1 (all screens) and 6 (baseline): mean / SD of delta = lbar_t(variant) - lbar_t(main) [or main - pair],
intraclass correlation ICC(3,1), SD(delta) / SD(lbar_t across dev exams), share with |delta| >= 0.25 SD, share whose flag at tau90 differs
(tau90 = 90th percentile of the published 1-year score among dev exams with y1 = 0). z-fix also by stretch class and by lung cut.
AUROC in the variant subset (descriptive). U1b dev qualification: |delta_6| >= 0.25 SD in >= 30% of D5 exams, or a flag change in >= 10%.
usage: python s4_q1d.py <assembled dir> <out_dir> [tag]
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score


def lbar(arr_p):
    z = np.load(arr_p, allow_pickle=True); lg = z["logit"]
    return pd.DataFrame({"series_uid": z["series_uid"], "l1": lg[:, :, 0].mean(1), "l6": lg[:, :, 5].mean(1)})


def icc31(a, b):
    x = np.stack([a, b], 1); n = len(x); gm = x.mean()
    msr = 2 * ((x.mean(1) - gm) ** 2).sum() / (n - 1); mse = (((x - x.mean(1, keepdims=True) - x.mean(0) + gm) ** 2).sum()) / (n - 1)
    return float((msr - mse) / (msr + mse))


def auc(y, s):
    m = np.isfinite(y)
    return float(roc_auc_score(y[m], s[m])) if m.sum() and len(np.unique(y[m])) == 2 else None


def stats(d, base, sd, flag_a, flag_b):
    return dict(n=int(len(d)), mean=float(d.mean()), sd=float(d.std()), icc=icc31(base, base + d), sd_ratio=float(d.std() / sd),
                share_ge_quarter_sd=float((np.abs(d) >= 0.25 * sd).mean()), share_flag_changed=float((flag_a != flag_b).mean()),
                mean_abs_over_sd=float(np.abs(d).mean() / sd))


def main():
    A, out = Path(sys.argv[1]), Path(sys.argv[2]); tag = sys.argv[3] if len(sys.argv) > 3 else "dev"
    E = pd.read_csv(A / f"exams_{tag}.csv", dtype={"pid": str}, low_memory=False).merge(lbar(A / f"arrays_{tag}_main.npz"), on="series_uid")
    tau90 = float(np.quantile(E.loc[E.y1 == 0, "s1"], 0.90))
    sd = {t: float(E[f"l{t}"].std()) for t in (1, 6)}
    sd6b = float(E.loc[E.study_yr == 0, "l6"].std())
    res = dict(tau90=tau90, sd_lbar1_all=sd[1], sd_lbar6_all=sd[6], sd_lbar6_baseline=sd6b, n_exams=int(len(E)))
    # (ii) z-fix
    zp = A / f"variant_{tag}_zfix.csv"
    if zp.exists():
        Z = pd.read_csv(zp).merge(lbar(A / f"arrays_{tag}_zfix.npz"), on="series_uid")
        J = E.merge(Z[["series_uid", "l1", "l6", "s1"]], on="series_uid", suffixes=("", "_z"))
        J["stretch"] = (J.thickness / J.true_spacing).round(2)
        r = {}
        for t in (1, 6):
            S = J if t == 1 else J[J.study_yr == 0]
            d = (S[f"l{t}_z"] - S[f"l{t}"]).to_numpy(); s_ = sd[1] if t == 1 else sd6b
            r[f"t{t}"] = stats(d, S[f"l{t}"].to_numpy(), s_, S.s1 >= tau90, S.s1_z >= tau90)
            r[f"t{t}"]["by_stretch"] = {str(k): stats((g[f"l{t}_z"] - g[f"l{t}"]).to_numpy(), g[f"l{t}"].to_numpy(), s_, g.s1 >= tau90, g.s1_z >= tau90)
                                        for k, g in S.groupby(np.where(S.stretch >= 1.9, "2.0", np.where(S.stretch >= 1.5, "1.6", "<1.5"))) if len(g) > 2}
            cut = S.T_lung_cut_z.fillna(0) == 1
            r[f"t{t}"]["by_lung_cut"] = {str(bool(k)): stats((g[f"l{t}_z"] - g[f"l{t}"]).to_numpy(), g[f"l{t}"].to_numpy(), s_, g.s1 >= tau90, g.s1_z >= tau90)
                                         for k, g in S.groupby(cut) if len(g) > 2}
        D5 = J[J.stretch >= 1.54]
        r["auroc_D5"] = dict(n=int(len(D5)), y1_pos=int((D5.y1 == 1).sum()), y1_main=auc(D5.y1.to_numpy(float), D5.l1.to_numpy()),
                             y1_zfix=auc(D5.y1.to_numpy(float), D5.l1_z.to_numpy()),
                             y6_pos=int(((D5.y6 == 1) & (D5.study_yr == 0)).sum()),
                             y6_main=auc(np.where(D5.study_yr == 0, D5.y6, np.nan).astype(float), D5.l6.to_numpy()),
                             y6_zfix=auc(np.where(D5.study_yr == 0, D5.y6, np.nan).astype(float), D5.l6_z.to_numpy()))
        q = r["t6"]["by_stretch"].get("2.0") or r["t6"]
        r["U1b_dev_qualifies"] = bool(q["share_ge_quarter_sd"] >= 0.30 or q["share_flag_changed"] >= 0.10)
        res["zfix"] = r
    # (i) kernel pairs
    pp = A / f"variant_{tag}_pair.csv"
    if pp.exists():
        P = pd.read_csv(pp).merge(lbar(A / f"arrays_{tag}_pair.npz"), on="series_uid")
        J = E.merge(P[["partner_of", "l1", "l6", "s1"]], left_on="series_uid", right_on="partner_of", suffixes=("", "_p"))
        r = {}
        for t in (1, 6):
            d = (J[f"l{t}"] - J[f"l{t}_p"]).to_numpy(); s_ = sd[1] if t == 1 else sd6b
            r[f"t{t}"] = stats(-d, J[f"l{t}"].to_numpy(), s_, J.s1 >= tau90, J.s1_p >= tau90)
            r[f"t{t}"]["sharp_minus_soft_mean"] = float(d.mean())
            r[f"t{t}"]["by_maker"] = {k: dict(n=int(len(g)), sharp_minus_soft_mean=float((g[f"l{t}"] - g[f"l{t}_p"]).mean()),
                                             sd=float((g[f"l{t}"] - g[f"l{t}_p"]).std())) for k, g in J.groupby("T_maker")}
        res["kernel_pairs"] = r
    out.mkdir(parents=True, exist_ok=True)
    (out / f"s4_q1d_{tag}.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
