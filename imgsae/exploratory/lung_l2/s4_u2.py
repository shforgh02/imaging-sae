"""Lung L2, S4, U2 reliability flag (docs/LUNG_L2_PROTOCOL.md 9.7).
Measure (y1 = 0 exams, all screens): e = [Sybil false alarm at tau90] - [F false alarm at tau90_F]; E(set) = mean of e in the set.
Statistic of a rule: E(flagged) - E(unflagged). Sybil's sensitivity (s1 >= tau90 among y1 = 1) in flagged and unflagged: descriptive.
R-fixed: flag if any of: T-share |G_T| / sum over the named groups N, B, D, I, T of |G_g| (lbar_1, primary arm) above its dev 80th
  percentile; z-stretch >= 1.54; thickness > 2.5 mm; any radiologist image-quality item (ctdxqual limited, breath, motion, artifact,
  graininess); air noise above its dev 90th percentile. Cut-offs are dev percentiles (no outcome), so no cross-validation is needed.
  Without a valid arm the T-share item is left out (protocol 9.5: "U2 (fixed rule) continues").
R-learned: cross-fitted (participant folds) logistic model (nlst_l0.logit_model: standardise + logistic, C = 0.3; medians imputed in
  each training fold) of "Sybil-only false alarm" among y1 = 0 rows, on the family activations (primary arm) and every I and T
  variable; out-of-fold predictions for all rows; flag the top 20% (80th percentile of the out-of-fold predictions among y1 = 0 rows).
The rule with the larger dev statistic is the one that can be frozen; only it becomes a candidate for gate 9.8 (> 0, null 0).
usage (venv python): python s4_u2.py <assembled dir> <results dir> [--tag dev] [--K 64]
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, r"D:\Shayan\imgsae\exploratory\lung_l0")
import nlst_l0 as L0  # noqa: E402
import s4_common as S  # noqa: E402

NAMED = ("N", "B", "D", "I", "T")
Q_ITEMS = ("T_q_limited", "T_q_breath", "T_q_motion", "T_q_artifact", "T_q_graininess")


def stat(flag, e, neg):
    a, b = flag & neg, ~flag & neg
    return float(e[a].mean() - e[b].mean()) if a.sum() and b.sum() else None


def evaluate(name, flag, e, neg, pos, sf, pid, hv):
    bt = S.Boot(pid); ci = bt.ci(lambda t: stat(flag[t], e[t], neg[t]))
    hh = [stat(flag & (hv == k), e, neg & (hv == k)) for k in (0, 1)]
    return dict(rule=name, flagged_share_y1_neg=float(flag[neg].mean()), flagged_exams=int(flag.sum()), statistic=ci, halves=hh,
                E_flagged=float(e[flag & neg].mean()) if (flag & neg).any() else None, E_unflagged=float(e[~flag & neg].mean()),
                sybil_sens_flagged=float(sf[flag & pos].mean()) if (flag & pos).any() else None, n_cancers_flagged=int((flag & pos).sum()),
                sybil_sens_unflagged=float(sf[~flag & pos].mean()) if (~flag & pos).any() else None, n_cancers_unflagged=int((~flag & pos).sum()))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("assembled"); ap.add_argument("results"); ap.add_argument("--tag", default="dev")
    ap.add_argument("--K", type=int, default=64); a = ap.parse_args(); R = Path(a.results)
    E, _ = S.load(a.assembled, a.tag); pid = E.pid.to_numpy(); hv = S.halves(pid); fold = S.folds(pid)
    arm, _t = S.primary_arm(R, a.tag, a.K); Cn = S.contrib(a.tag, arm, a.K) if arm else None
    F = S.family_table(R, a.tag, arm, a.K) if arm else None; labels = dict(zip(F.family, F.label)) if arm and len(F) else {}
    neg, pos = (E.y1 == 0).to_numpy(), (E.y1 == 1).to_numpy(); s1, f1 = E.s1.to_numpy(), E.F1.to_numpy()
    t90, t90f = np.quantile(s1[neg], 0.90), np.quantile(f1[neg], 0.90); sf, ff = s1 >= t90, f1 >= t90f
    e = sf.astype(float) - ff.astype(float); res = dict(tag=a.tag, primary_arm=arm, tau90=float(t90), tau90_F=float(t90f),
                                                        counts=dict(y1_neg=int(neg.sum()), y1_pos=int(pos.sum()), participants=int(E.pid.nunique())))
    # R-fixed
    items = {}
    if arm is not None:
        M = E[["series_uid"]].merge(Cn, on="series_uid", how="left"); cols = [f"t1_{g}" for g in NAMED if f"t1_{g}" in M]
        den = np.sum([np.abs(M[c].to_numpy()) for c in cols], 0) if cols else np.zeros(len(E))
        tsh = np.where(den > 0, np.abs(M["t1_T"].to_numpy()) / np.where(den > 0, den, 1), 0.0) if "t1_T" in M else np.zeros(len(E))
        items["t_share_gt_p80"] = tsh > np.quantile(tsh, 0.80)
    items["zstretch_ge_1.54"] = (E.T_zstretch >= 1.54).to_numpy()
    items["thickness_gt_2.5"] = (E.T_thick_gt_2p5 == 1).to_numpy()
    items["radiologist_quality_item"] = np.any([(E[c] == 1).to_numpy() for c in Q_ITEMS], 0)
    an = E.I_air_noise_sd_hu.to_numpy(float); items["air_noise_gt_p90"] = np.nan_to_num(an, nan=-np.inf) > np.nanquantile(an, 0.90)
    fixed = np.any(list(items.values()), 0)
    res["R_fixed_items_share"] = {k: float(v.mean()) for k, v in items.items()}
    res["R_fixed"] = evaluate("R-fixed", fixed, e, neg, pos, sf, pid, hv)
    # R-learned
    X, kind = S.variables(E, Cn, labels, t=1); X = X[[c for c in X.columns if kind[c] in ("I", "T", "family")]].to_numpy(float)
    target = (sf & ~ff).astype(int); pred = np.zeros(len(E))
    for f in range(5):
        tr, te = (fold != f) & neg, fold == f
        med = np.nanmedian(X[tr], 0); med = np.where(np.isfinite(med), med, 0.0)
        Xtr, Xte = np.where(np.isfinite(X[tr]), X[tr], med), np.where(np.isfinite(X[te]), X[te], med)
        keep = Xtr.std(0) > 0
        pred[te] = L0.logit_model().fit(Xtr[:, keep], target[tr]).predict_proba(Xte[:, keep])[:, 1]
    learned = pred >= np.quantile(pred[neg], 0.80)
    res["R_learned"] = evaluate("R-learned", learned, e, neg, pos, sf, pid, hv); res["R_learned"]["n_inputs"] = int(X.shape[1])
    res["R_learned"]["cv_auroc_of_sybil_only_fa"] = S.auc(target[neg], pred[neg])
    best = max((res["R_fixed"], res["R_learned"]), key=lambda r: -np.inf if r["statistic"]["est"] is None else r["statistic"]["est"])
    res["rule_that_can_be_frozen"] = best["rule"]
    res["candidates"] = [S.candidate(f"U2_{best['rule']}", "U2 (9.7)", f"E(flagged) - E(unflagged), {best['rule']}", "y1 = 0, all screens", ">", 0.0,
                                     best["statistic"], best["halves"], res["counts"], feature_based=arm is not None,   # T-share or families
                                     note="the rule with the larger dev statistic (protocol 9.7)")]
    S.write(R, f"s4_u2_{a.tag}.json", res)
    print(f"s4_u2: written; rule that can be frozen: {best['rule']}")


if __name__ == "__main__":
    main()
