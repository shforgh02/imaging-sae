"""Lung L2, step S6 (N6): extra looks at one root, labelled EXPLORATORY (protocol 11; docs/PROJECT_GUIDE.md N6). Runs on test only after
the frozen analysis output (results/s6/s6_test.json) is committed. Nothing here is a hypothesis, nothing is confirmed, nothing is fitted:
the thresholds are the frozen dev values (frozen_thresholds_L2.json), the axes and heads are the frozen files (loaded and hash-checked by
s6_frozen_analysis.load_frozen). Every number carries its counts of exams, participants and cancers. Written and committed before the
frozen analysis ran on test (17 Nov 2026); tested on dev.
A. Misses at the frozen tau90 (s1 for 1-year cancers, all screens; s6 for 6-year cancers, baseline screens): Sybil's misses, and for the
   1-year cancers also the radiologists' (positive_call = 0) and the form's (F1 < tau90_F1); by histology, central location, stage,
   stretch status (ratio <= 0.65), scanner maker, and (6 years) time to diagnosis. Exact 95% intervals. Subgroups with fewer than 10
   cancers are marked "n < 10: no claim".
B. The z-fix (T5 exams): mean change of lbar_1, share with |change of lbar_6| >= 0.25 dev SD, share of flag changes at tau90, and the H6
   statistic per exam (axis 0 off minus plain), by stretch class (1.6 / 2.0), scanner maker, study year and lung cut in z.
C. H7 (consecutive yearly screens, main runs): b by scanner-maker group of the pair (both GE, neither GE, one GE) and without GE pairs.
usage (venv python): python s6_explore_test.py <assembled dir> <root> <frozen dir (results/s5)> <run_info dir> <out json>
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import s4_common as S  # noqa: E402
import s4_q1d as QD  # noqa: E402
import s5_axes_freeze as AXF  # noqa: E402
import s6_frozen_analysis as FA  # noqa: E402

YEAR = 365.25


def cp(k, n): return S.clopper_pearson(int(k), int(n)) if n else None


def miss_table(Q, cancer, missed, by):
    out = {}
    for name, col in by.items():
        g = {}
        for v in sorted(Q.loc[cancer, col].dropna().astype(str).unique()):
            c = cancer & (Q[col].astype(str) == v).to_numpy(); n = int(c.sum()); k = int((missed & c).sum())
            g[v] = dict(cancers=n, missed=k, share=k / n if n else None, ci_exact=cp(k, n), note="n < 10: no claim" if n < 10 else "")
        out[name] = g
    return out


def mean_ci(v, pid):
    if len(v) < 3: return dict(n=int(len(v)), est=float(v.mean()) if len(v) else None)
    b = S.Boot(pid).ci(lambda t: float(v[t].mean())); return dict(n=int(len(v)), participants=int(len(np.unique(pid))), **b)


def main():
    A, root, FZ, RI, out_p = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5])
    T, arms, fams, lab_of, FI, COMB, AX = FA.load_frozen(FZ, RI); th = T["thresholds"]
    E, H, X = FA.load_root(A, root); heads = S.C.load_heads(RI / "heads.npz"); fc = AXF.load_fc(RI / "heads.npz")
    res = dict(root=root, label="EXPLORATORY (protocol 11): not a hypothesis, never confirmed", thresholds=dict(tau90_s1=th["tau90_s1"], tau90_s6=th["tau90_s6"], tau90_F1=th["tau90_F1"]))
    E["stretched"] = np.where(E.ratio <= th["zfix_ratio_max"], "stretched", "not_stretched"); E["central"] = E.c_loc_central.map({1.0: "central", 0.0: "not_central"})
    E["maker"] = E.T_maker.fillna("unknown")
    # ---- A. misses
    A_ = {}
    m = S.pop(E, "y1"); Q = E[m].reset_index(drop=True); c = (Q.y1 == 1).to_numpy()
    sy, rad, form = (Q.s1 < th["tau90_s1"]).to_numpy(), (Q.positive_call == 0).to_numpy(), (Q.F1 < th["tau90_F1"]).to_numpy()
    A_["y1_all_screens"] = dict(counts=S.counts(E, m, "y1"), sybil_missed=dict(k=int((sy & c).sum()), n=int(c.sum()), ci_exact=cp((sy & c).sum(), c.sum())),
                                radiologists_missed=dict(k=int((rad & c).sum()), n=int(c.sum()), ci_exact=cp((rad & c).sum(), c.sum())),
                                form_missed=dict(k=int((form & c).sum()), n=int(c.sum()), ci_exact=cp((form & c).sum(), c.sum())),
                                sybil_and_radiologists_missed=int((sy & rad & c).sum()),
                                by_sybil=miss_table(Q, c, sy, dict(histology="c_histology", location="central", stage="c_stage", stretch="stretched", maker="maker")))
    m = S.pop(E, "y6"); Q = E[m].reset_index(drop=True); c = (Q.y6 == 1).to_numpy(); sy = (Q.s6 < th["tau90_s6"]).to_numpy()
    Q["dx"] = pd.cut(Q.dt / YEAR, [0, 1, 2, 4, 6], labels=["0-1y", "1-2y", "2-4y", "4-6y"]).astype(str)
    A_["y6_baseline"] = dict(counts=S.counts(E, m, "y6"), sybil_missed=dict(k=int((sy & c).sum()), n=int(c.sum()), ci_exact=cp((sy & c).sum(), c.sum())),
                             by_sybil=miss_table(Q, c, sy, dict(histology="c_histology", location="central", stage="c_stage", time_to_diagnosis="dx", stretch="stretched", maker="maker")))
    res["A_misses_at_frozen_tau90"] = A_
    # ---- B. z-fix by subgroup (T5), with the H6 statistic per exam
    Z, _ = QD.variant_frame(A, root, "zfix")
    if Z is not None:
        rowpos = {u: i for i, u in enumerate(E.series_uid)}
        J = E.merge(Z[["series_uid", "v_l1", "v_l6", "s1"]].rename(columns={"s1": "v_s1"}), on="series_uid"); J = J[J.ratio <= th["zfix_ratio_max"]].reset_index(drop=True)
        d1 = (J.v_l1 - J.lbar1).to_numpy(); d6 = (J.v_l6 - J.lbar6).to_numpy(); fl = ((J.s1 >= th["tau90_s1"]) != (J.v_s1 >= th["tau90_s1"])).to_numpy()
        mi = np.array([rowpos[u] for u in J.series_uid]); _, Xz = FA.variant_arrays(A, root, "zfix", J.series_uid)
        Lz, Lm = FA.logits_pooled(Xz, fc, heads), FA.logits_pooled(X[mi], fc, heads); Lz_off, Lm_off = FA.logits_pooled(Xz, fc, heads, AX, [0]), FA.logits_pooled(X[mi], fc, heads, AX, [0])
        h6 = (Lz_off[:, :, 0].mean(1) - Lm_off[:, :, 0].mean(1)) - (Lz[:, :, 0].mean(1) - Lm[:, :, 0].mean(1))
        J["cls"] = np.where(J.thickness / J.true_spacing >= 1.9, "2.0", "1.6"); J["cut"] = J.T_lung_cut_z.map({1.0: "lung_cut_z", 0.0: "no_lung_cut_z"}).fillna("unknown")
        pid = J.pid.to_numpy(); B = dict(counts=dict(exams=int(len(J)), participants=int(J.pid.nunique()), cancers_y1=int((J.y1 == 1).sum())))
        for name, col in (("stretch_class", "cls"), ("maker", "maker"), ("study_yr", "study_yr"), ("lung_cut", "cut")):
            g = {}
            for v in sorted(J[col].astype(str).unique()):
                k = (J[col].astype(str) == v).to_numpy()
                g[v] = dict(n=int(k.sum()), participants=int(J.pid[k].nunique()), mean_delta_lbar1=mean_ci(d1[k], pid[k]), h6=mean_ci(h6[k], pid[k]),
                            share_abs_delta_lbar6_ge_quarter_sd=float((np.abs(d6[k]) >= th["quarter_sd"] * th["sd_ref_lbar6_all_dev_main"]).mean()), share_flag_changed=float(fl[k].mean()))
            B[name] = g
        B["h6_share_exams_above_null_0p20"] = float((h6 >= 0.20).mean())
        res["B_zfix_by_subgroup"] = B
    # ---- C. H7 by scanner-maker group of the pair
    E2 = E.copy(); E2["st"] = (E2.ratio <= th["zfix_ratio_max"]).astype(int); E2["ge"] = E2.maker.str.upper().str.startswith("GE").astype(int)
    cols = ["pid", "study_yr", "st", "lbar1", "F1", "ge"]; P = E2[cols].merge(E2[cols], on="pid", suffixes=("_a", "_b")); P = P[P.study_yr_b == P.study_yr_a + 1].reset_index(drop=True)
    dl, dst, dF, ppid = (P.lbar1_b - P.lbar1_a).to_numpy(), (P.st_b - P.st_a).to_numpy(float), (P.F1_b - P.F1_a).to_numpy(), P.pid.to_numpy()
    grp = np.select([(P.ge_a == 1) & (P.ge_b == 1), (P.ge_a == 0) & (P.ge_b == 0)], ["both_GE", "neither_GE"], "one_GE")
    C = {}
    for v in ("both_GE", "one_GE", "neither_GE"):
        k = np.flatnonzero(grp == v); ch = int((dst[k] != 0).sum())
        C[v] = dict(pairs=int(len(k)), participants=int(len(np.unique(ppid[k]))), changed=ch,
                    b=S.Boot(ppid[k]).ci(lambda t, k=k: FA.ols_b(dl[k][t], dst[k][t], dF[k][t]) if (dst[k][t] != 0).sum() >= 3 else None) if ch >= 5 else None,
                    note="fewer than 20 changed pairs: no claim" if ch < 20 else "")
    k = np.flatnonzero(grp != "both_GE"); C["without_both_GE"] = dict(pairs=int(len(k)), changed=int((dst[k] != 0).sum()),
                                                                      b=S.Boot(ppid[k]).ci(lambda t: FA.ols_b(dl[k][t], dst[k][t], dF[k][t]) if (dst[k][t] != 0).sum() >= 3 else None))
    C["changed_pairs_involving_GE"] = int(((dst != 0) & (grp != "neither_GE")).sum()); C["changed_pairs"] = int((dst != 0).sum())
    res["C_H7_by_maker"] = C
    out_p.parent.mkdir(parents=True, exist_ok=True); out_p.write_bytes((json.dumps(res, indent=1, default=float) + "\n").encode("utf-8"))
    print(json.dumps(res, indent=1, default=float)[:6000])


if __name__ == "__main__":
    main()
