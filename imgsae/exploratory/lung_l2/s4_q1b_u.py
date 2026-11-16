"""Lung L2, S4, Q1b (docs/LUNG_L2_PROTOCOL.md 9.7, 9.2): which features carry the composition, and does the unexplained part predict cancer?
(i) Does U add to F? U = lbar_t minus its out-of-fold ridge prediction from all known groups (s4_q1a). Cross-fitted logistic
    y ~ F + U against y ~ F: AUROC difference with a participant-bootstrap interval, likelihood-ratio test; y1 (F1, U of lbar1, all
    screens) and y6 (F6, U of lbar6, baseline). Halves: the same difference refitted within each dev half.
(ii) Group shares of section 9.2 with the primary arm (s4_common.primary_arm): share_g = Cov(G_g, lbar_t) / Var(lbar_t), with
    participant-bootstrap intervals and the shares in each dev half (t = 1 all screens, t = 6 baseline).
(iii) Covariance of each replicated family's contribution with U: share of Var(U) = Cov(G_family, U) / Var(U), Pearson r, cluster-robust
    p, BH q over families; per horizon.
Candidates for gate 9.8: (i) U adds to F (not feature-based); (ii) share of each named group N, B, D, I, T (feature-based);
(iii) families with q < 0.05 (feature-based). If no arm is valid, (ii) and (iii) are not computed (protocol 9.5).
usage (venv python): python s4_q1b_u.py <assembled dir> <results dir> <heads npz> [--tag dev] [--K 64]
"""
import argparse
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s4_common as S  # noqa: E402

GROUPS = ("N", "B", "D", "I", "T")


def share_fn(G, L):
    def fn(t):
        v = np.var(L[t], ddof=1); return float(np.cov(G[t], L[t])[0, 1] / v) if v > 0 else None
    return fn


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("assembled"); ap.add_argument("results"); ap.add_argument("heads")
    ap.add_argument("--tag", default="dev"); ap.add_argument("--K", type=int, default=64); a = ap.parse_args()
    R = Path(a.results); E, arr = S.load(a.assembled, a.tag)
    U = pd.read_csv(R / f"s4_q1a_U_{a.tag}.csv"); E = E.merge(U, on="series_uid", how="left")
    res = dict(tag=a.tag, K=a.K); cands = []
    # (i) U adds to F
    for y, f, u in (("y1", "F1", "U_lbar1"), ("y6", "F6", "U_lbar6")):
        m = S.pop(E, y) & E[u].notna().to_numpy(); P = E[m]
        av = S.added_value(P[y].to_numpy(int), P[[f]].to_numpy(), P[[u]].to_numpy(), P.pid.to_numpy())
        av["counts"] = S.counts(E, m, y); res[f"U_adds_to_F_{y}"] = av
        cands.append(S.candidate(f"Q1b_U_adds_to_F_{y}", "Q1b (9.7)", "dAUROC cross-fitted (F + U) - F", f"{y}, {'all screens' if y == 'y1' else 'baseline'}",
                                 ">", 0.0, av["dauroc"], av["dauroc_halves"], av["counts"], note=f"LR test p = {av['lr']['p']:.3g}"))
    # (ii), (iii): primary arm
    arm, table = S.primary_arm(R, a.tag, a.K); res["arms"] = table; res["primary_arm"] = arm
    if arm is None:
        res["feature_level"] = "no valid arm: group shares and family covariances not computed (protocol 9.5)"
    else:
        Cn = S.contrib(a.tag, arm, a.K); Ej = E.merge(Cn, on="series_uid", how="left")
        hv = S.halves(Ej.pid.to_numpy()); shares = {}
        for t, mask in ((1, np.ones(len(Ej), bool)), (6, (Ej.study_yr == 0).to_numpy())):
            P = Ej[mask].reset_index(drop=True); L = P[f"lbar{t}"].to_numpy(); bt = S.Boot(P.pid.to_numpy()); h = hv[mask]
            keys = [c[len(f"t{t}_"):] for c in Cn.columns if c.startswith(f"t{t}_")]; st = {}
            for k in keys:
                G = P[f"t{t}_{k}"].to_numpy(); ci = bt.ci(share_fn(G, L))
                hh = [share_fn(G[h == j], L[h == j])(np.arange((h == j).sum())) for j in (0, 1)]
                st[k] = dict(ci, halves=hh)
                if k in GROUPS:
                    cands.append(S.candidate(f"Q1b_share_{k}_lbar{t}", "Q1b (9.2, 9.7)", f"share of lbar_{t} carried by group {k} features ({arm})",
                                             f"{'all screens' if t == 1 else 'baseline'}", ">", 0.0, ci, hh, S.counts(Ej, mask), feature_based=True))
            st["sum_of_shares"] = float(sum(v["est"] for v in st.values() if isinstance(v, dict) and v.get("est") is not None))
            shares[f"lbar{t}"] = st
        res["group_shares"] = shares
        # (iii) per-family contributions and U
        pk = S.DATA / "arms" / f"arms_{a.tag}_{arm}_K{a.K}.pkl"; obj = pickle.load(open(pk, "rb")); arms, fams = obj["arms"], obj["families"]
        heads = S.C.load_heads(a.heads); Hh = arr["h"].astype(np.float64)
        As = [arms[m].encode(Hh[:, m]) for m in range(5)]
        F = S.family_table(R, a.tag, arm, a.K); lab = dict(zip(F.family, F.label)) if len(F) else {}
        fam_res = {}
        for t, u in ((1, "U_lbar1"), (6, "U_lbar6")):
            ct = [S.C.contributions(Hh[:, m], As[m], arms[m], heads[m], t)[1] for m in range(5)]
            mask = E[u].notna().to_numpy(); Uv = E.loc[mask, u].to_numpy(); pid = E.pid.to_numpy()[mask]; rows = []
            for k, (fam, sg) in enumerate(fams):
                Gk = np.sum([ct[m][:, f] for m, f in fam.items()], 0)[mask] / 5.0
                cv = float(np.cov(Gk, Uv)[0, 1] / np.var(Uv, ddof=1)); r = float(np.corrcoef(Gk, Uv)[0, 1]) if np.std(Gk) > 0 else None
                rows.append(dict(family=k, label=lab.get(k), share_of_var_U=cv, r=r, p=S.slope_p(Uv, Gk, pid)))   # U on G_k, cluster-robust
            q = S.bh([r_["p"] for r_ in rows])
            for r_, v in zip(rows, q): r_["q"] = None if not np.isfinite(v) else float(v)
            fam_res[f"lbar{t}"] = dict(n_rows=int(mask.sum()), families=rows)
            for r_ in rows:
                if r_["q"] is not None and r_["q"] < 0.05:
                    k = r_["family"]; fam, sg = fams[k]
                    Gk = (np.sum([ct[m][:, f] for m, f in fam.items()], 0) / 5.0)[mask]; bt = S.Boot(pid); hh = S.halves(pid)
                    fn = lambda tk, G=Gk: float(np.cov(G[tk], Uv[tk])[0, 1] / np.var(Uv[tk], ddof=1))
                    ci = bt.ci(fn); halves_est = [fn(np.flatnonzero(hh == j)) for j in (0, 1)]
                    cands.append(S.candidate(f"Q1b_family{k}_carries_U_lbar{t}", "Q1b (9.7)", f"share of Var(U of lbar_{t}) covaried with family {k} ({lab.get(k)}, {arm})",
                                             "all screens" if t == 1 else "baseline", "!=", 0.0, ci, halves_est, dict(exams=int(mask.sum()), participants=int(len(np.unique(pid)))),
                                             feature_based=True))
        res["family_covariance_with_U"] = fam_res
    res["candidates"] = cands
    S.write(R, f"s4_q1b_u_{a.tag}.json", res)
    print(f"s4_q1b_u: written; primary arm {arm}; {len(cands)} candidates")


if __name__ == "__main__":
    main()
