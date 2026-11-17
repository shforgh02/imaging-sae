"""Lung L2, step R2 (dev only, exploratory; the lead's question of 2026-11-17: "can we develop more interesting hypotheses on dev? the harm?
using the form?"). Plan fixed and logged before this ran (docs/EXECUTION_LOG.md, step R2).
usage: python r7_more.py <assembled dir> <heads npz> <out dir>
A. Real follow-up (natural experiment, outcome-free). Pairs of consecutive yearly screens of one person (dev). d_st = stretched(later) -
   stretched(earlier), stretched = spacing/thickness <= 0.65. OLS  delta lbar_1 = a + b * d_st + c * delta F1  (F1 = the form model's 1-year
   logit: the radiologist's view of change). Statistic b (proposed null +0.10, direction >). Participant bootstrap, halves, permutation of
   d_st (2,000). The same with shared axis 0 of `pooled` switched off in every member (b_off) and the share (b - b_off) / b. Sensitivity:
   same scanner model in both years; both screens without cancer within 1 year (uses outcomes; sensitivity only). Descriptive: flag flips.
B. Harm through false alarms, with the form (uses outcomes: y1 = 0 only). Sybil-only false alarm = Sybil flag (s1 >= tau90) while the form is
   below its own tau90 (F1, 90th percentile among dev exams with y1 = 0). Rates in stretched against other exams; D5 main against z-fix.
   Missed cancers: counts only, and the expected number of stretched test cancers (power note).
D. Beyond the radiologist (outcome-free). R1 = lbar_1 minus its linear fit on F1 (all dev exams). Share of Var(R1) explained by the shared
   axes of `pooled`: the risk axis (3), the technical axes (labels T: 0, 1, 2, 4, 10), the other axes, all 11. Random-choice test for the
   technical set: 2,000 sets of 5 random directions (one random direction of the 30-PC space per member, mean of the five).
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, r"D:\Shayan\imgsae")
import r1_arms as R1  # noqa: E402
import r2_shared as R2  # noqa: E402
import s4_common as S4  # noqa: E402
from r4_axes_audit import remove  # noqa: E402


def ols(y, *xs):
    X = np.c_[np.ones(len(y)), np.column_stack(xs)]; return np.linalg.lstsq(X, y, rcond=None)[0]


def r2(y, X):
    X = np.c_[np.ones(len(y)), X]; p = X @ np.linalg.lstsq(X, y, rcond=None)[0]; return float(1 - ((y - p) ** 2).sum() / ((y - y.mean()) ** 2).sum())


def main():
    A, heads, out, L = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), "pooled"; sys.modules["__main__"].Shared = R2.Shared
    E, X, LG, logits, _, _ = R1.load(A, heads, L); E = E.copy(); n = len(E)
    P = pickle.load(open(R2.DATA / "r" / f"r2_shared_{L}.pkl", "rb")); sh, k = P["shared"], P["k"]; assert (P["series_uid"] == E.series_uid.to_numpy()).all()
    T = pd.read_csv(out / f"r2_axes_{L}.csv"); C = T[T.rotation == "cca"].set_index("axis")
    tech = [j for j in range(k) if C.label[j] == "T"]; risk = [j for j in range(k) if abs(C.r_lbar6[j]) >= 0.5]; other = [j for j in range(k) if j not in tech + risk]
    l1 = LG[:, :, 0].mean(1); l1_off = np.stack([logits(remove(sh, X[:, m], m, sh.Wt[m][:, [0]]), m)[0][:, 0] for m in range(5)], 1).mean(1)
    S = P["S"]; E["l1"], E["l1_off"], E["ax0"] = l1, l1_off, S[:, 0] / S[:, 0].std()
    E["st"] = (E.ratio <= 0.65).astype(int); half_of = dict(zip(E.pid, S4.halves(E.pid.to_numpy()))); res = dict(tech_axes=tech, risk_axes=risk, other_axes=other)
    # ---------------- A. real follow-up
    c = ["pid", "study_yr", "st", "l1", "l1_off", "ax0", "F1", "s1", "y1", "tag_model"]; Pp = E[c].merge(E[c], on="pid", suffixes=("_a", "_b"))
    Pp = Pp[Pp.study_yr_b == Pp.study_yr_a + 1].reset_index(drop=True)
    d = dict(dst=(Pp.st_b - Pp.st_a).to_numpy(float), dl=(Pp.l1_b - Pp.l1_a).to_numpy(), dl_off=(Pp.l1_off_b - Pp.l1_off_a).to_numpy(), dax0=(Pp.ax0_b - Pp.ax0_a).to_numpy(), dF=(Pp.F1_b - Pp.F1_a).to_numpy())
    pid = Pp.pid.to_numpy(); hv = np.array([half_of[p] for p in pid]); tau = float(np.quantile(E.loc[E.y1 == 0, "s1"], 0.90)); flip = ((Pp.s1_a >= tau) != (Pp.s1_b >= tau)).to_numpy()

    def block(rows, name):
        rows = np.flatnonzero(rows); bt = S4.Boot(pid[rows]); o = dict(n_pairs=int(len(rows)), participants=int(len(set(pid[rows]))), n_changed=int((d["dst"][rows] != 0).sum()),
                                                                        n_stretched_to_not=int((d["dst"][rows] == -1).sum()), n_not_to_stretched=int((d["dst"][rows] == 1).sum()))
        fb = lambda key: (lambda t: float(ols(d[key][rows][t], d["dst"][rows][t], d["dF"][rows][t])[1]))   # noqa: E731
        for key in ("dl", "dl_off", "dax0"):
            ci = bt.ci(fb(key)); o[f"b_{key}"] = dict(ci, halves=[fb(key)(np.flatnonzero(hv[rows] == h)) for h in (0, 1)])
        o["share_carried_by_axis0"] = float(1 - o["b_dl_off"]["est"] / o["b_dl"]["est"]) if o["b_dl"]["est"] else None
        g = {"stretched_to_not": -1, "unchanged": 0, "not_to_stretched": 1}
        o["groups"] = {nm: dict(n=int((d["dst"][rows] == v).sum()), mean_dl=float(d["dl"][rows][d["dst"][rows] == v].mean()), mean_dl_off=float(d["dl_off"][rows][d["dst"][rows] == v].mean()),
                                mean_dax0=float(d["dax0"][rows][d["dst"][rows] == v].mean()), flag_flip=float(flip[rows][d["dst"][rows] == v].mean())) for nm, v in g.items() if (d["dst"][rows] == v).sum()}
        if name == "all":
            rng = np.random.default_rng(0); perm = np.array([ols(d["dl"][rows], rng.permutation(d["dst"][rows]), d["dF"][rows])[1] for _ in range(2000)])
            o["permutation"] = dict(n=2000, share_above_null=float((perm > 0.10).mean()), max=float(perm.max()), p97_5=float(np.quantile(perm, 0.975)))
        return o
    res["A_followup"] = dict(tau90=tau, null=0.10, direction=">", all=block(np.ones(len(Pp), bool), "all"),
                             same_scanner_model=block((Pp.tag_model_a == Pp.tag_model_b).to_numpy(), "same"),
                             both_no_cancer_1y_sensitivity=block(((Pp.y1_a == 0) & (Pp.y1_b == 0)).to_numpy(), "nc"))
    # ---------------- B. harm through false alarms, with the form
    tF = float(np.quantile(E.loc[E.y1 == 0, "F1"], 0.90)); nc = (E.y1 == 0).to_numpy(); st = E.st.to_numpy() == 1; fs = E.s1.to_numpy() >= tau; ff = E.F1.to_numpy() >= tF
    so = fs & ~ff; bt = S4.Boot(E.pid.to_numpy()[nc]); i_st = st[nc]
    diff = lambda v: (lambda t: float(v[t][i_st[t]].mean() - v[t][~i_st[t]].mean()))   # noqa: E731
    res["B_false_alarms"] = dict(tau90_form=tF, n_no_cancer=int(nc.sum()), n_no_cancer_stretched=int((nc & st).sum()),
                                 sybil_fa_rate=dict(stretched=float(fs[nc & st].mean()), other=float(fs[nc & ~st].mean()), diff=bt.ci(diff(fs[nc].astype(float)))),
                                 sybil_only_fa_rate=dict(stretched=float(so[nc & st].mean()), other=float(so[nc & ~st].mean()), diff=bt.ci(diff(so[nc].astype(float)))),
                                 form_fa_rate=dict(stretched=float(ff[nc & st].mean()), other=float(ff[nc & ~st].mean())))
    V = pd.read_csv(A / "variant_dev_zfix.csv", low_memory=False)[["series_uid", "s1"]].rename(columns={"s1": "v_s1"}); J = E.merge(V, on="series_uid"); J = J[(J.ratio <= 0.65) & (J.y1 == 0)]
    a, b = (J.s1 >= tau) & (J.F1 < tF), (J.v_s1 >= tau) & (J.F1 < tF)
    res["B_false_alarms"]["D5_zfix_no_cancer"] = dict(n=int(len(J)), sybil_only_fa_main=int(a.sum()), sybil_only_fa_zfix=int(b.sum()), lost=int((a & ~b).sum()), gained=int((~a & b).sum()))
    cy = (E.y1 == 1).to_numpy(); res["B_missed"] = dict(cancers_1y_stretched=int((cy & st).sum()), missed_1y_stretched=int((cy & st & ~fs).sum()), cancers_1y_other=int((cy & ~st).sum()),
                                                      missed_1y_other=int((cy & ~st & ~fs).sum()), expected_stretched_test_cancers_1y=round(float((cy & st).sum()) * 400 / 578, 1),
                                                      note="test scale from the series counts at ratio 0.5 (400 test, 578 dev; protocol C2); no test file read")
    # ---------------- D. beyond the radiologist
    bF = ols(l1, E.F1.to_numpy()); R = l1 - (bF[0] + bF[1] * E.F1.to_numpy()); res["D_beyond_form"] = dict(r2_lbar1_from_F1=r2(l1, E.F1.to_numpy()[:, None]))
    for nm, js in (("risk_axis", risk), ("technical_axes", tech), ("other_axes", other), ("all_11", list(range(k)))): res["D_beyond_form"][f"share_of_residual_{nm}"] = r2(R, S[:, js])
    W = [sh.white(X[:, m], m) for m in range(5)]; rng = np.random.default_rng(3); rr = []
    for _ in range(2000):
        Ar = [(lambda q: q / np.linalg.norm(q, axis=0))(rng.normal(size=(sh.npc, len(tech)))) for m in range(5)]; rr.append(r2(R, np.mean([W[m] @ Ar[m] for m in range(5)], 0)))
    rr = np.array(rr); res["D_beyond_form"]["random_5_directions"] = dict(n=2000, median=float(np.median(rr)), p97_5=float(np.quantile(rr, 0.975)), max=float(rr.max()),
                                                                          share_ge_technical=float((rr >= res["D_beyond_form"]["share_of_residual_technical_axes"]).mean()))
    (out / "r7_more_pooled.json").write_text(json.dumps(res, indent=1, default=str)); print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
