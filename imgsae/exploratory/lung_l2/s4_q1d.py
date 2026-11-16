"""Lung L2, S4, Q1d / U1b (docs/LUNG_L2_PROTOCOL.md 9.7): score change inside one exam when only a technical factor changes.
(i) kernel pairs (tier D4, 500 baseline exams): sharp (main) minus soft (pair) reconstruction of the same acquisition;
(ii) z-fix (D5): slices placed at their true spacing minus Sybil as published. D5 = the z-fix rows with spacing/thickness <= 0.65
     (stretch >= 1.54), all screens. The pilot's extra z-fix rows (0.65 < ratio <= 0.95) are reported apart, descriptively.
Statistics per horizon (delta of the mean member logit lbar_t): mean, SD, ICC(3,1), SD(delta) / SD(lbar_t across dev main exams),
share with |delta| >= 0.25 SD, mean |delta| / SD, share whose flag at tau90 differs (tau90 = 90th percentile of the published 1-year
score s1 among dev exams with y1 = 0; the flag is s1 >= tau90). SD reference: t = 1 all dev main exams; t = 6 all dev main exams for D5
(all screens) and baseline dev main exams for D4 (all baseline). z-fix also by stretch class and by lung cut; kernel pairs by maker.
U1b dev qualification (protocol 9.7, as written): |delta lbar_6| >= 0.25 SD(lbar_6) in >= 30% of D5 exams, or a flag change in >= 10%.
Change of each group term G_g (primary arm, frozen dictionaries encoding the variant's h): mean change and share of Var(delta).
AUROC of main and variant in the variant subset: descriptive (few cancers).
Candidates for gate 9.8 (participant bootstrap 95% intervals; halves = 2 participant folds):
  z-fix: share |delta lbar_6| >= 0.25 SD > 0.30; flag change share > 0.10 (the U1b margins); mean delta lbar_1, lbar_6 != 0;
  kernel: the same four statistics; the 0.30 and 0.10 margins are carried over from U1b (my choice, fixed before the full-dev run).
Change log: 2026-11-16, before any full-dev run: D5 restricted to ratio <= 0.65 (the old code mixed in the pilot's 0.65-0.95 rows);
U1b judged on all D5 exams (the old code used only the stretch-2.0 subgroup); intervals, halves, candidates and G_g changes added.
usage (venv python): python s4_q1d.py <assembled dir> <results dir> <heads npz> [--tag dev] [--K 64]
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s4_common as S  # noqa: E402

GROUPS = ("N", "B", "D", "I", "T")


def icc31(a, b):
    x = np.stack([a, b], 1); n = len(x); gm = x.mean()
    msr = 2 * ((x.mean(1) - gm) ** 2).sum() / (n - 1); mse = (((x - x.mean(1, keepdims=True) - x.mean(0) + gm) ** 2).sum()) / (n - 1)
    return float((msr - mse) / (msr + mse))


def stats(d, base, sd, fa, fb):
    return dict(n=int(len(d)), mean=float(d.mean()), sd=float(d.std()), icc=icc31(base, base + d) if len(d) > 2 else None, sd_ratio=float(d.std() / sd),
                share_ge_quarter_sd=float((np.abs(d) >= 0.25 * sd).mean()), mean_abs_over_sd=float(np.abs(d).mean() / sd),
                share_flag_changed=float((fa != fb).mean()))


def variant_frame(A, tag, var):
    p = A / f"variant_{tag}_{var}.csv"
    if not p.exists(): return None, None
    V = pd.read_csv(p); z = np.load(A / f"arrays_{tag}_{var}.npz", allow_pickle=True); pos = {u: i for i, u in enumerate(z["series_uid"])}
    idx = np.array([pos[u] for u in V.series_uid]); lg = z["logit"][idx].astype(np.float64)
    V["v_l1"], V["v_l6"] = lg[:, :, 0].mean(1), lg[:, :, 5].mean(1)
    return V, z["h"][idx].astype(np.float64)


def block(J, d1, d6, sd1, sd6, flag_main, flag_var, prefix, label, cnt, cands, U1b=False):
    """the four candidate statistics with bootstrap intervals and halves."""
    pid = J.pid.to_numpy(); bt = S.Boot(pid); hv = S.halves(pid); out = {}
    fns = {"share_ge_quarter_sd_lbar6": (lambda t: float((np.abs(d6[t]) >= 0.25 * sd6).mean()), ">", 0.30),
           "share_flag_changed": (lambda t: float((flag_main[t] != flag_var[t]).mean()), ">", 0.10),
           "mean_delta_lbar1": (lambda t: float(d1[t].mean()), "!=", 0.0),
           "mean_delta_lbar6": (lambda t: float(d6[t].mean()), "!=", 0.0)}
    for k, (fn, direc, null) in fns.items():
        ci = bt.ci(fn); hh = [fn(np.flatnonzero(hv == j)) for j in (0, 1)]; out[k] = dict(ci, halves=hh)
        q = None
        if U1b and k == "share_ge_quarter_sd_lbar6": q = "U1b: >= 0.30 (or flag change >= 0.10)"
        if U1b and k == "share_flag_changed": q = "U1b: >= 0.10 (or share >= 0.30)"
        cands.append(S.candidate(f"{prefix}_{k}", label, k, cnt["population"], direc, null, ci, hh, cnt, qualification=q,
                                 note="" if U1b or k.startswith("mean") else "margin carried over from U1b (my choice, fixed before the full-dev run)"))
    return out


def group_change(Hv, Hm, arms, fams, lab_of, heads, t, dl):
    """mean change of each term G_g (variant minus main) and its share of Var(delta lbar_t)."""
    gv = S.split_by_label(Hv, arms, fams, lab_of, heads, t); gm = S.split_by_label(Hm, arms, fams, lab_of, heads, t); out = {}
    for k in gv:
        dg = np.asarray(gv[k] - gm[k], float)
        out[k] = dict(mean=float(dg.mean()), sd=float(dg.std()), share_of_var_delta=float(np.cov(dg, dl)[0, 1] / np.var(dl, ddof=1)) if np.var(dl) > 0 else None)
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("assembled"); ap.add_argument("results"); ap.add_argument("heads")
    ap.add_argument("--tag", default="dev"); ap.add_argument("--K", type=int, default=64); a = ap.parse_args()
    A, R = Path(a.assembled), Path(a.results); E, arr = S.load(A, a.tag); cands = []
    tau90 = float(np.quantile(E.loc[E.y1 == 0, "s1"], 0.90))
    sd1, sd6, sd6b = float(E.lbar1.std()), float(E.lbar6.std()), float(E.loc[E.study_yr == 0, "lbar6"].std())
    res = dict(tag=a.tag, tau90=tau90, sd_lbar1_all=sd1, sd_lbar6_all=sd6, sd_lbar6_baseline=sd6b, n_exams=int(len(E)))
    arm, table = S.primary_arm(R, a.tag, a.K); res["primary_arm"] = arm
    if arm is not None:
        arms, fams = S.load_arm(a.tag, arm, a.K); F = S.family_table(R, a.tag, arm, a.K); lab_of = dict(zip(F.family, F.label)) if len(F) else {}
        heads = S.C.load_heads(a.heads)
    rowpos = {u: i for i, u in enumerate(E.series_uid)}
    # ---- (ii) z-fix
    Z, Hz = variant_frame(A, a.tag, "zfix")
    if Z is not None:
        J = E.merge(Z[["series_uid", "v_l1", "v_l6", "s1", "ratio"]].rename(columns={"s1": "v_s1", "ratio": "v_ratio"}), on="series_uid")
        Hz = Hz[[Z.series_uid.tolist().index(u) for u in J.series_uid]]
        J["stretch"] = J.thickness / J.true_spacing; d5 = (J.ratio <= 0.65).to_numpy()
        r = dict(n_zfix_rows=int(len(J)), n_D5=int(d5.sum()), n_extra_pilot_rows=int((~d5).sum()))
        for name, M in (("D5", d5), ("extra_pilot_0.65_0.95", ~d5)):
            P = J[M]; Hm = arr["h"][[rowpos[u] for u in P.series_uid]].astype(np.float64)
            if len(P) < 3: continue
            d1, d6 = (P.v_l1 - P.lbar1).to_numpy(), (P.v_l6 - P.lbar6).to_numpy(); fa, fb = (P.s1 >= tau90).to_numpy(), (P.v_s1 >= tau90).to_numpy()
            q = dict(counts=S.counts(E, E.series_uid.isin(P.series_uid).to_numpy(), "y1"),
                     t1=stats(d1, P.lbar1.to_numpy(), sd1, fa, fb), t6=stats(d6, P.lbar6.to_numpy(), sd6, fa, fb))
            b = (P.study_yr == 0).to_numpy()
            if b.sum() > 2: q["t6_baseline_only"] = stats(d6[b], P.lbar6.to_numpy()[b], sd6b, fa[b], fb[b])
            cls = np.where(P.stretch >= 1.9, "2.0", np.where(P.stretch >= 1.5, "1.6", "<1.5"))
            q["t6_by_stretch"] = {k: stats(d6[cls == k], P.lbar6.to_numpy()[cls == k], sd6, fa[cls == k], fb[cls == k]) for k in np.unique(cls) if (cls == k).sum() > 2}
            cut = (P.T_lung_cut_z.fillna(0) == 1).to_numpy()
            q["t6_by_lung_cut"] = {str(k): stats(d6[cut == k], P.lbar6.to_numpy()[cut == k], sd6, fa[cut == k], fb[cut == k]) for k in (False, True) if (cut == k).sum() > 2}
            if name == "D5":
                cnt = dict(q["counts"], population="D5 z-fix exams (spacing/thickness <= 0.65), all screens")
                q["candidates_stats"] = block(P, d1, d6, sd1, sd6, fa, fb, "ZF", "Q1d (ii) / U1b (9.7)", cnt, cands, U1b=True)
                q["U1b_dev_qualifies"] = bool(q["t6"]["share_ge_quarter_sd"] >= 0.30 or q["t6"]["share_flag_changed"] >= 0.10)
                yy1 = P.y1.to_numpy(float); yy6 = np.where(P.study_yr == 0, P.y6, np.nan).astype(float)
                q["auroc_descriptive"] = dict(y1_pos=int(np.nansum(yy1 == 1)), y1_main=S.auc(yy1, P.lbar1), y1_zfix=S.auc(yy1, P.v_l1),
                                              y6_pos=int(np.nansum(yy6 == 1)), y6_main=S.auc(yy6, P.lbar6), y6_zfix=S.auc(yy6, P.v_l6))
                if arm is not None:
                    q["group_change"] = {f"t{t}": group_change(Hz[d5], Hm, arms, fams, lab_of, heads, t, d1 if t == 1 else d6) for t in (1, 6)}
            r[name] = q
        res["zfix"] = r
    # ---- (i) kernel pairs
    Pp, Hp = variant_frame(A, a.tag, "pair")
    if Pp is not None:
        J = E.merge(Pp[["series_uid", "partner_of", "v_l1", "v_l6", "s1"]].rename(columns={"series_uid": "pair_uid", "s1": "v_s1"}),
                    left_on="series_uid", right_on="partner_of")
        Hp = Hp[[Pp.series_uid.tolist().index(u) for u in J.pair_uid]]; Hm = arr["h"][[rowpos[u] for u in J.series_uid]].astype(np.float64)
        d1, d6 = (J.lbar1 - J.v_l1).to_numpy(), (J.lbar6 - J.v_l6).to_numpy(); fa, fb = (J.s1 >= tau90).to_numpy(), (J.v_s1 >= tau90).to_numpy()
        r = dict(counts=S.counts(E, E.series_uid.isin(J.series_uid).to_numpy(), "y1"), n_baseline=int((J.study_yr == 0).sum()),
                 note="delta = sharp (main) minus soft (pair); SD reference for t = 6: baseline dev main exams",
                 t1=stats(d1, J.v_l1.to_numpy(), sd1, fa, fb), t6=stats(d6, J.v_l6.to_numpy(), sd6b, fa, fb))
        r["by_maker"] = {k: dict(n=int(len(g)), mean_delta_lbar1=float((g.lbar1 - g.v_l1).mean()), mean_delta_lbar6=float((g.lbar6 - g.v_l6).mean()),
                                 sd_delta_lbar6=float((g.lbar6 - g.v_l6).std())) for k, g in J.groupby("T_maker")}
        cnt = dict(r["counts"], population="D4 kernel pairs (baseline D1 exams with a soft-kernel partner)")
        r["candidates_stats"] = block(J, d1, d6, sd1, sd6b, fa, fb, "KP", "Q1d (i) (9.7)", cnt, cands)
        if arm is not None:
            r["group_change"] = {f"t{t}": group_change(Hm, Hp, arms, fams, lab_of, heads, t, d1 if t == 1 else d6) for t in (1, 6)}
        res["kernel_pairs"] = r
    res["candidates"] = cands
    S.write(R, f"s4_q1d_{a.tag}.json", res)
    print(f"s4_q1d: written; {len(cands)} candidates")


if __name__ == "__main__":
    main()
