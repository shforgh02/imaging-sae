"""Lung L2, S4, U1a technical removal (docs/LUNG_L2_PROTOCOL.md 9.7).
Per participant fold (5, seed 0) and member: ridge (standardised, RidgeCV over the alphas of s4_q1a, one alpha for all 512 outputs) of
h_m on the technical group T (s4_q1a.design: one-hot categoricals, numeric NaN -> dev median), fitted on the training folds;
held-out h'_m = h_m - (T-fit - its dev mean) (the fold model's mean prediction over all dev rows). Logits recomputed with Sybil's
head (gating recomputed), member probabilities averaged, then Sybil's calibrator (numpy copy) -> s'_t.
Reported: dAUROC (s'_t - s_t) for y1 (all screens) and y6 (baseline); false-alarm-rate spread = SD (ddof 1) across maker x kernel-class
groups with >= 100 exams with y1 = 0 of the false-alarm rate at the overall 90%-specificity threshold (tau90 of that score), after /
before; the same spread for F (F1) as a case-mix reference. Participant-bootstrap intervals; values in each dev half.
Dev qualification for a hypothesis (as written): dAUROC >= -0.01 at both horizons, spread ratio <= 0.80, and Sybil's spread before
removal larger than F's.
Candidates for gate 9.8: spread ratio < 1 (null 1); dAUROC y1 and y6 > -0.01 (non-inferiority null -0.01). Not feature-based.
usage (venv python): python s4_u1a.py <assembled dir> <results dir> <heads npz> <calibrator json> [--tag dev]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s4_common as S  # noqa: E402


def ensemble(Hx, heads, cal):
    lg = np.stack([S.C.head_logits(Hx[:, m], heads[m])[0] for m in range(5)], 1)          # (n, 5, 6)
    return S.calibrate(cal, (1 / (1 + np.exp(-lg))).mean(1))


def spread(score, neg, grp, groups):
    tau = np.quantile(score[neg], 0.90); r = [float((score[neg & (grp == g)] >= tau).mean()) for g in groups]
    return float(np.std(r, ddof=1)) if len(r) > 1 else None, r


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("assembled"); ap.add_argument("results"); ap.add_argument("heads"); ap.add_argument("calibrator")
    ap.add_argument("--tag", default="dev"); a = ap.parse_args(); R = Path(a.results)
    E, arr = S.load(a.assembled, a.tag); H = arr["h"].astype(np.float64); heads = S.C.load_heads(a.heads); cal = json.load(open(a.calibrator))
    XT = S.Q.design(E, S.D.groups(E)["T"]); pid = E.pid.to_numpy(); fold = S.folds(pid); Hp = np.zeros_like(H); r2 = np.zeros((5, 5))
    for f in range(5):
        tr, te = fold != f, fold == f
        for m in range(5):
            mdl = make_pipeline(StandardScaler(), RidgeCV(alphas=S.Q.ALPHAS)).fit(XT[tr], H[tr, m]); fit = mdl.predict(XT)
            Hp[te, m] = H[te, m] - (fit[te] - fit.mean(0))
            r2[f, m] = 1 - ((H[te, m] - fit[te]) ** 2).sum() / ((H[te, m] - H[tr, m].mean(0)) ** 2).sum()
    s_old, s_new = ensemble(H, heads, cal), ensemble(Hp, heads, cal)
    res = dict(tag=a.tag, n_T_columns=int(XT.shape[1]), heldout_r2_of_h_on_T_by_member=r2.mean(0).round(4).tolist(),
               check_recomputed_s_vs_saved_max_abs=float(np.abs(s_old - E[[f"s{t}" for t in range(1, 7)]].to_numpy()).max()))
    cands = []; hv = S.halves(pid)
    for y, t in (("y1", 1), ("y6", 6)):
        m = S.pop(E, y); yy = E[y].to_numpy(float)[m]; bt = S.Boot(pid[m]); a_new, a_old = s_new[m, t - 1], s_old[m, t - 1]
        d = S.dauc_ci(yy, a_new, a_old, bt); hh = []
        for k in (0, 1):
            mk = hv[m] == k; u, v = S.auc(yy[mk], a_new[mk]), S.auc(yy[mk], a_old[mk]); hh.append(None if u is None or v is None else u - v)
        res[f"auroc_{y}"] = dict(counts=S.counts(E, m, y), before=S.auc(yy, a_old), after=S.auc(yy, a_new), dauroc=d, dauroc_halves=hh)
        cands.append(S.candidate(f"U1a_dAUROC_{y}", "U1a (9.7)", f"dAUROC after technical removal, {y}", f"{y}, {'all screens' if y == 'y1' else 'baseline'}",
                                 ">", -0.01, d, hh, res[f"auroc_{y}"]["counts"], qualification="dAUROC >= -0.01 at both horizons"))
    neg = (E.y1 == 0).to_numpy(); grp = (E.T_maker.fillna("NA").astype(str) + "|" + np.where(E.T_kclass_sharp == 1, "sharp", "soft")).to_numpy()
    groups = sorted(g for g in np.unique(grp) if (neg & (grp == g)).sum() >= 100)
    sb, rb = spread(s_old[:, 0], neg, grp, groups); sa, ra = spread(s_new[:, 0], neg, grp, groups); sf, rf = spread(E.F1.to_numpy(), neg, grp, groups)
    res["spread"] = dict(groups=groups, n_neg_by_group=[int((neg & (grp == g)).sum()) for g in groups], fa_rate_before=rb, fa_rate_after=ra, fa_rate_F=rf,
                         sd_before=sb, sd_after=sa, sd_F=sf, ratio=(sa / sb if sb else None),
                         specificity_at_tau90=dict(before=float((s_old[neg, 0] < np.quantile(s_old[neg, 0], .9)).mean()),
                                                   after=float((s_new[neg, 0] < np.quantile(s_new[neg, 0], .9)).mean())))

    def ratio_fn(t):
        nt, gt = neg[t], grp[t]; b, _ = spread(s_old[t, 0], nt, gt, groups); c, _ = spread(s_new[t, 0], nt, gt, groups)
        return None if not b or c is None else c / b
    bt = S.Boot(pid); ci = bt.ci(ratio_fn); hh = [ratio_fn(np.flatnonzero(hv == k)) for k in (0, 1)]
    res["spread"]["ratio_ci"] = ci; res["spread"]["ratio_halves"] = hh
    q = dict(dauroc_y1_ok=bool(res["auroc_y1"]["dauroc"]["est"] >= -0.01), dauroc_y6_ok=bool(res["auroc_y6"]["dauroc"]["est"] >= -0.01),
             ratio_ok=bool(res["spread"]["ratio"] is not None and res["spread"]["ratio"] <= 0.80), sybil_spread_gt_F=bool(sb is not None and sf is not None and sb > sf))
    q["qualifies"] = bool(all(q.values())); res["qualification"] = q
    cands.append(S.candidate("U1a_spread_ratio", "U1a (9.7)", "false-alarm-rate spread across maker x kernel class, after / before", "y1 = 0, all screens",
                             "<", 1.0, ci, hh, dict(exams=int(neg.sum()), participants=int(len(np.unique(pid[neg]))), groups=len(groups)),
                             qualification=f"ratio <= 0.80, dAUROC >= -0.01 both, Sybil spread > F spread: {q['qualifies']}"))
    res["candidates"] = cands
    S.write(R, f"s4_u1a_{a.tag}.json", res)
    print(f"s4_u1a: written; recomputed-s check {res['check_recomputed_s_vs_saved_max_abs']:.2e}; {len(groups)} maker x kernel groups")


if __name__ == "__main__":
    main()
