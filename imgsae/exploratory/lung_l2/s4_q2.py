"""Lung L2, S4, Q2 (docs/LUNG_L2_PROTOCOL.md 9.7, 9.9): why is Sybil wrong? False-alarm classes and misses.
Thresholds (dev): tau90 = 90th percentile of s1 among exams with y1 = 0 (all screens); tau_rad = the s1 threshold that flags the
radiologists' dev positive-call rate (2,573 of 7,362 exams in the tables, protocol 9.7); F's thresholds likewise on F1.
False alarms (y1 = 0, all screens): Sybil only (s1 >= tau, F1 < tauF), shared, form only, against true negatives (both below).
  SMD of every family activation, every group term G_g of lbar_1 (primary arm), every I and T variable; cluster-robust p; BH q per table.
  Primary operating point tau90 (well powered, protocol 9.9); tau_rad reported as a secondary table.
Misses at 1 year (all screens), 2 and 6 years (baseline): missed (s_t < tau90_t, the 90th percentile of s_t among y_t = 0 of that
  population) against caught; SMDs as above (descriptive); counts by location, histology, stage (I, II-III, IV), lesion size tertile,
  time to diagnosis, lung_cut_z, z-stretch >= 1.54, with exact binomial intervals. No claim for a subgroup with fewer than 10 cancers.
Candidates for gate 9.8: rows of the tau90 false-alarm tables with q < 0.05 (all three classes); statistic SMD, two-sided, null 0,
  participant-bootstrap interval, SMD in each dev half. Families and G_g are feature-based. Misses: descriptive only (my choice:
  88 one-year cancers; protocol 9.9 calls the 1-year misses descriptive), fixed before the full-dev run.
usage (venv python): python s4_q2.py <assembled dir> <results dir> [--tag dev] [--K 64]
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s4_common as S  # noqa: E402

RAD_RATE = 2573 / 7362


def boot_smd(x, g, ref, bt, hv):
    fn = lambda t: S.smd(x[t], g[t], ref[t])
    return bt.ci(fn), [S.smd(x, g & (hv == k), ref & (hv == k)) for k in (0, 1)]


def subgroup_counts(P, missed):
    """miss counts by subgroup among the cancers of one horizon (P = cancer rows)."""
    out = {}
    def add(name, mask):
        n, k = int(mask.sum()), int((mask & missed).sum()); lo, hi = S.clopper_pearson(k, n)
        out[name] = dict(cancers=n, missed=k, miss_rate=(k / n if n else None), ci95=[lo, hi], claim_allowed=bool(n >= 10))
    for k in ("central", "upper", "middle", "lower"): add(f"location_{k}", (P[f"c_loc_{k}"] == 1).to_numpy())
    for k in ("adeno", "squamous", "small_cell", "other"): add(f"histology_{k}", (P.c_histology == k).to_numpy())
    for k in ("I", "II_III", "IV", "unknown"): add(f"stage_{k}", (P.c_stage == k).to_numpy())
    sz = P.c_lesion_mm.to_numpy(float)
    if np.isfinite(sz).sum() >= 3:
        q1, q2 = np.nanquantile(sz, [1 / 3, 2 / 3])
        add("size_tertile_1", sz <= q1); add("size_tertile_2", (sz > q1) & (sz <= q2)); add("size_tertile_3", sz > q2)
        out["size_tertile_cuts_mm"] = [float(q1), float(q2)]
    add("size_missing", ~np.isfinite(sz))
    dt = P.dt.to_numpy(float) / 365.25
    for lo_, hi_ in ((0, 1), (1, 2), (2, 4), (4, 6)): add(f"time_to_dx_{lo_}_{hi_}y", (dt > lo_) & (dt <= hi_) if lo_ else (dt <= hi_))
    add("lung_cut_z", (P.T_lung_cut_z.fillna(0) == 1).to_numpy()); add("zstretch_ge_1.54", (P.T_zstretch >= 1.54).to_numpy())
    add("all", np.ones(len(P), bool))
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("assembled"); ap.add_argument("results"); ap.add_argument("--tag", default="dev")
    ap.add_argument("--K", type=int, default=64); a = ap.parse_args(); R = Path(a.results)
    E, _ = S.load(a.assembled, a.tag)
    arm, table = S.primary_arm(R, a.tag, a.K); res = dict(tag=a.tag, primary_arm=arm); cands = []
    Cn = S.contrib(a.tag, arm, a.K) if arm else None
    F = S.family_table(R, a.tag, arm, a.K) if arm else None; labels = dict(zip(F.family, F.label)) if arm and len(F) else {}
    X, kind = S.variables(E, Cn, labels, t=1)
    neg = (E.y1 == 0).to_numpy(); s1, f1 = E.s1.to_numpy(), E.F1.to_numpy(); pid = E.pid.to_numpy(); hv = S.halves(pid)
    th = dict(tau90=float(np.quantile(s1[neg], 0.90)), tau90_F=float(np.quantile(f1[neg], 0.90)),
              tau_rad=float(np.quantile(s1, 1 - RAD_RATE)), tau_rad_F=float(np.quantile(f1, 1 - RAD_RATE)), rad_rate=RAD_RATE,
              rad_rate_in_analysed_exams=float(E.positive_call.mean()))
    # Sybil's calibrated score has ties (step-like calibrator), so the share flagged at a quantile can differ from its target
    th["specificity_at_tau90"] = float((s1[neg] < th["tau90"]).mean()); th["specificity_at_tau90_F"] = float((f1[neg] < th["tau90_F"]).mean())
    th["flagged_share_at_tau_rad"] = float((s1 >= th["tau_rad"]).mean())
    res["thresholds"] = th
    # ---- false alarms
    fa = {}
    for op, ts, tf in (("tau90", th["tau90"], th["tau90_F"]), ("tau_rad", th["tau_rad"], th["tau_rad_F"])):
        Sf, Ff = s1 >= ts, f1 >= tf
        cls = dict(sybil_only=neg & Sf & ~Ff, shared=neg & Sf & Ff, form_only=neg & ~Sf & Ff); tn = neg & ~Sf & ~Ff
        o = dict(counts={k: dict(exams=int(v.sum()), participants=int(len(np.unique(pid[v])))) for k, v in dict(cls, true_negative=tn).items()},
                 y1_negatives=int(neg.sum()))
        for c, g in cls.items():
            rows = S.smd_table(list(X.columns), X, g, tn, pid, half=hv)
            for r in rows: r["kind"] = kind[r["variable"]]
            o[c] = rows
            if op == "tau90":
                for r in rows:
                    if r["q"] is not None and r["q"] < 0.05 and r["smd"] is not None:
                        x = X[r["variable"]].to_numpy(float); sub = g | tn; idx = np.flatnonzero(sub)
                        btt = S.Boot(pid[idx]); ci, hh = boot_smd(x[idx], g[idx], tn[idx], btt, hv[idx])
                        cands.append(S.candidate(f"Q2_FA_{c}_{r['variable']}", "Q2 (9.7)", f"SMD of {r['variable']} ({r['kind']}), {c} false alarms vs true negatives at tau90",
                                                 "y1 = 0, all screens", "!=", 0.0, ci, hh, dict(exams=int(sub.sum()), class_exams=int(g.sum()),
                                                 participants=int(len(np.unique(pid[idx])))), feature_based=r["kind"] in ("G", "family"),
                                                 note=f"BH q = {r['q']:.3g} in its table"))
        fa[op] = o
    res["false_alarms"] = fa
    # ---- misses
    ms = {}
    for y, (s, lb, base) in S.HORIZONS.items():
        m = S.pop(E, y); sv = E[s].to_numpy(); tau_t = float(np.quantile(sv[m & (E[y] == 0).to_numpy()], 0.90))
        canc = m & (E[y] == 1).to_numpy(); missed = canc & (sv < tau_t); caught = canc & ~missed
        rows = S.smd_table(list(X.columns), X, missed, caught, pid, half=hv)
        for r in rows: r["kind"] = kind[r["variable"]]
        P = E[canc]; ms[y] = dict(tau90_t=tau_t, population="all screens" if y == "y1" else "baseline", counts=S.counts(E, m, y),
                                  missed=int(missed.sum()), caught=int(caught.sum()), subgroups=subgroup_counts(P, missed[canc]),
                                  smd_missed_vs_caught=rows, note="descriptive only")
    res["misses"] = ms
    res["candidates"] = cands
    S.write(R, f"s4_q2_{a.tag}.json", res)
    print(f"s4_q2: written; primary arm {arm}; {len(cands)} candidates")


if __name__ == "__main__":
    main()
