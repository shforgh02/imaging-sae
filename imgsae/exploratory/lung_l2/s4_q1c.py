"""Lung L2, S4, Q1c (docs/LUNG_L2_PROTOCOL.md 9.7): which groups carry the within-person stable part of Sybil's score.
Participants with a T0 (baseline) and a T1 (year-1) exam. For t = 1 and 6 and every term g of the primary arm's exact split
(groups N, B, D, I, T, mixed, unnamed, unreplicated, intercept, residual; they sum to lbar_t):
  stable share of g = Cov(G_g(T0), lbar_t(T1)) / Cov(lbar_t(T0), lbar_t(T1));   the stable shares of all terms sum to 1.
For all such participants and for those without cancer within 2 years of T0 (y2 = 0 at T0). Participant bootstrap (one row per
participant), 2,000 draws; the shares in each dev half. Also reported, label-free: Pearson r of lbar_t between T0 and T1.
Candidates for gate 9.8: stable share of each named group N, B, D, I, T, t = 1 and 6, all participants (feature-based).
If no arm is valid, the group shares are not computed (protocol 9.5); r is still reported.
usage (venv python): python s4_q1c.py <assembled dir> <results dir> [--tag dev] [--K 64]
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s4_common as S  # noqa: E402

GROUPS = ("N", "B", "D", "I", "T")


def stable_fn(G0, L0, L1):
    def fn(t):
        c = np.cov(L0[t], L1[t])[0, 1]; return float(np.cov(G0[t], L1[t])[0, 1] / c) if abs(c) > 1e-12 else None
    return fn


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("assembled"); ap.add_argument("results"); ap.add_argument("--tag", default="dev")
    ap.add_argument("--K", type=int, default=64); a = ap.parse_args(); R = Path(a.results)
    E, _ = S.load(a.assembled, a.tag)
    arm, table = S.primary_arm(R, a.tag, a.K); res = dict(tag=a.tag, K=a.K, primary_arm=arm, arms=table); cands = []
    if arm is not None: E = E.merge(S.contrib(a.tag, arm, a.K), on="series_uid", how="left")
    T0 = E[E.study_yr == 0].set_index("pid"); T1 = E[E.study_yr == 1].set_index("pid"); both = T0.index.intersection(T1.index)
    T0, T1 = T0.loc[both], T1.loc[both]
    if len(both) < 20:
        res.update(note=f"only {len(both)} participants with T0 and T1 exams: not computed", candidates=[])
        S.write(R, f"s4_q1c_{a.tag}.json", res); print(f"s4_q1c: {len(both)} participants with T0 and T1; not computed"); return
    for sub, keep in (("all", np.ones(len(both), bool)), ("no_cancer_within_2y_of_T0", (T0.y2 == 0).to_numpy())):
        A0, A1 = T0[keep], T1[keep]; pid = A0.index.to_numpy(); bt = S.Boot(pid); hv = S.halves(pid); out = dict(participants=int(len(pid)))
        out["cancers_y1_at_T0"] = int((A0.y1 == 1).sum()); out["cancers_y6_at_T0"] = int((A0.y6 == 1).sum())
        for t in (1, 6):
            L0, L1 = A0[f"lbar{t}"].to_numpy(), A1[f"lbar{t}"].to_numpy(); r = dict()
            r["pearson_r_T0_T1"] = bt.ci(lambda tk: float(np.corrcoef(L0[tk], L1[tk])[0, 1]))
            if arm is not None:
                terms = [c[len(f"t{t}_"):] for c in E.columns if c.startswith(f"t{t}_")]; sh = {}
                for g in terms:
                    G0 = A0[f"t{t}_{g}"].to_numpy(); fn = stable_fn(G0, L0, L1); ci = bt.ci(fn)
                    hh = [fn(np.flatnonzero(hv == k)) for k in (0, 1)]; sh[g] = dict(ci, halves=hh)
                    if sub == "all" and g in GROUPS:
                        cands.append(S.candidate(f"Q1c_stable_share_{g}_lbar{t}", "Q1c (9.7)", f"stable share of lbar_{t} carried by group {g} ({arm})",
                                                 "participants with T0 and T1 exams", ">", 0.0, ci, hh, dict(participants=int(len(pid)), exams=int(2 * len(pid))),
                                                 feature_based=True))
                sh["sum_of_shares"] = float(sum(v["est"] for v in sh.values() if v.get("est") is not None)); r["stable_shares"] = sh
            out[f"lbar{t}"] = r
        res[sub] = out
    if arm is None: res["feature_level"] = "no valid arm: stable group shares not computed (protocol 9.5)"
    res["candidates"] = cands
    S.write(R, f"s4_q1c_{a.tag}.json", res)
    print(f"s4_q1c: written; primary arm {arm}; {len(both)} participants with T0 and T1; {len(cands)} candidates")


if __name__ == "__main__":
    main()
