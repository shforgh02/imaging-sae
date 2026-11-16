"""Lung L2, S4, scores (docs/LUNG_L2_PROTOCOL.md 9.1; plan P4 item 3, review F4).
(i) Check P1: Spearman(lbar_t, s_t) >= 0.98 on dev for t = 1 and 6 (all dev main exams, as written; also on the primary populations:
    t = 1 all screens, t = 6 baseline). If it fails, the decomposition is reported per member only.
(ii) Hazard gating: unit j is "on" for member m and exam x if its raw hazard > 0; shares by member, by unit, and by member x unit.
(iii) Dev AUROC (participant bootstrap, 2,000 draws) of Sybil's published score s_t and of F: y1 all screens (s1, F1), y6 baseline (s6, F6),
    secondary y2 baseline (s2); the analysed score lbar_t alongside. The radiologists' call (positive screen) for y1, descriptive.
    Note (protocol C6): dev was used for Sybil's model selection, so Sybil's dev accuracy is mildly optimistic. Test is clean.
No candidate for gate 9.8 comes from this script (these are references).
usage (venv python): python s4_scores.py <assembled dir> <out dir> [tag]
"""
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s4_common as S  # noqa: E402


def main():
    A, out = Path(sys.argv[1]), Path(sys.argv[2]); tag = sys.argv[3] if len(sys.argv) > 3 else "dev"
    E, arr = S.load(A, tag); res = dict(tag=tag, counts=S.counts(E),
                                        participants_note="2,493 dev participants in Sybil's split file; 2,492 have a usable exam (S1 manifest)")
    # (i) check P1
    p1 = {}
    for t in (1, 6):
        p1[f"t{t}_all"] = float(spearmanr(E[f"lbar{t}"], E[f"s{t}"])[0])
    b = (E.study_yr == 0).to_numpy(); p1["t6_baseline"] = float(spearmanr(E.lbar6[b], E.s6[b])[0])
    p1["pass_"] = bool(p1["t1_all"] >= 0.98 and p1["t6_all"] >= 0.98)
    p1["primary_populations_pass"] = bool(p1["t1_all"] >= 0.98 and p1["t6_baseline"] >= 0.98)
    p1["consequence_if_fail"] = "decomposition reported per member only (protocol 9.1)"
    # diagnostics (not marks; added 2026-11-16 before any full-dev run): Sybil's calibrator is step-like and clips low risks, so s_t
    # has ties; the rank correlation with the uncalibrated mean member probability shows whether lbar_t ranks like the model itself
    lg = arr["logit"].astype(np.float64); mp = (1 / (1 + np.exp(-lg))).mean(1)
    p1["diagnostics"] = {f"t{t}": dict(spearman_lbar_vs_mean_member_prob=float(spearmanr(E[f"lbar{t}"], mp[:, t - 1])[0]),
                                        n_unique_s=int(E[f"s{t}"].nunique()), share_at_min_s=float((E[f"s{t}"] == E[f"s{t}"].min()).mean()),
                                        min_s=float(E[f"s{t}"].min())) for t in (1, 6)}
    res["check_P1"] = p1
    # (ii) gating shares
    g = arr["raw_haz"] > 0                                   # (n, 5 members, 6 units)
    res["gating_on_share"] = dict(overall=float(g.mean()), by_member=g.mean((0, 2)).round(5).tolist(), by_unit=g.mean((0, 1)).round(5).tolist(),
                                  by_member_unit=g.mean(0).round(5).tolist(), exams_any_unit_on=float(g.any((1, 2)).mean()), n_exams=int(len(g)))
    # (iii) AUROC
    au = {}
    for y, (s, lb, base) in S.HORIZONS.items():
        m = S.pop(E, y); P = E[m]; bt = S.Boot(P.pid.to_numpy()); yy = P[y].to_numpy(float)
        r = dict(counts=S.counts(E, m, y), sybil_s=S.auc_ci(yy, P[s].to_numpy(), bt), sybil_lbar=S.auc_ci(yy, P[lb].to_numpy(), bt))
        fcol = {"y1": "F1", "y6": "F6"}.get(y)
        if fcol:
            r["form_F"] = S.auc_ci(yy, P[fcol].to_numpy(), bt); r["sybil_minus_F"] = S.dauc_ci(yy, P[s].to_numpy(), P[fcol].to_numpy(), bt)
        au[y] = r
    m = S.pop(E, "y1"); P = E[m]; yy = P.y1.to_numpy(float); pc = P.positive_call.to_numpy(float)
    au["radiologists_y1"] = dict(sensitivity=float(pc[yy == 1].mean()), specificity=float(1 - pc[yy == 0].mean()), positive_rate=float(pc.mean()),
                                 counts=S.counts(E, m, "y1"), positive_calls=int(pc.sum()))
    res["auroc"] = au
    res["note_C6"] = "Sybil's dev numbers are mildly optimistic: dev was used for Sybil's model selection (protocol C6). Test is clean."
    S.write(out, f"s4_scores_{tag}.json", res)
    print(f"s4_scores: written {out / f's4_scores_{tag}.json'}; check P1 pass {p1['pass_']}")


if __name__ == "__main__":
    main()
