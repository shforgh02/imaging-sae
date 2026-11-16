"""Lung L2, S4, U3 Sybil plus the form (docs/LUNG_L2_PROTOCOL.md 9.7). y1, all screens.
C = cross-fitted (participant folds) plain logistic combination of logit(s1) and F's logit F1 (as lung L1).
Operating point: the radiologists' dev sensitivity for y1 (positive screen among y1 = 1; protocol: 0.909 in the tables; recomputed on
the analysed exams and used as the target). For Sybil, F and C the threshold is the score of the ceil(target x cancers)-th highest
cancer, so each reaches at least the target sensitivity. False alarms per 1,000 screens = exams with y1 = 0 at or above the threshold
per 1,000 exams of the population; the radiologists' call at its own sensitivity likewise.
Dev qualification (as written): C <= 0.80 x the better (smaller) of Sybil and F. Statistic: ratio FA(C) / min(FA(Sybil), FA(F)), with
a participant-bootstrap interval (thresholds recomputed in each draw at the fixed target) and the ratio in each dev half.
For exams where C removes a Sybil false alarm (Sybil flags, C does not; y1 = 0): SMDs of families and group terms against the Sybil
false alarms that C keeps (primary arm).
Candidate for gate 9.8: the ratio < 1 (null 1). "Partly seen": it is computable from the L1 test scores and the form alone (protocol 10).
F+I (amendment A3) is added to this table by s4_refs.py.
usage (venv python): python s4_u3.py <assembled dir> <results dir> [--tag dev] [--K 64]
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s4_common as S  # noqa: E402


def threshold(score, y, target):
    p = np.sort(score[y == 1])[::-1]; k = max(1, math.ceil(target * len(p) - 1e-9)); return p[k - 1]


def fa_per_1000(score, y, target):
    thr = threshold(score, y, target); flag = score >= thr
    return float(((y == 0) & flag).sum() / len(y) * 1000), float(flag[y == 1].mean()), thr


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("assembled"); ap.add_argument("results"); ap.add_argument("--tag", default="dev")
    ap.add_argument("--K", type=int, default=64); a = ap.parse_args(); R = Path(a.results)
    E, _ = S.load(a.assembled, a.tag); m = S.pop(E, "y1"); P = E[m].reset_index(drop=True)
    y = P.y1.to_numpy(int); pid = P.pid.to_numpy(); fold = S.folds(pid); hv = S.halves(pid)
    s, f, rad = P.s1.to_numpy(), P.F1.to_numpy(), P.positive_call.to_numpy()
    c = S.crossfit(y, np.column_stack([S.logit(s), f]), fold)
    target = float(rad[y == 1].mean())
    res = dict(tag=a.tag, counts=S.counts(E, m, "y1"), target_sensitivity=target, protocol_value=0.909)
    tab = {}
    for name, sc in (("sybil", s), ("form_F", f), ("combined_C", c)):
        fa, sens, thr = fa_per_1000(sc, y, target); tab[name] = dict(fa_per_1000=fa, sensitivity=sens, threshold=float(thr))
    tab["radiologists"] = dict(fa_per_1000=float(((y == 0) & (rad == 1)).sum() / len(y) * 1000), sensitivity=target)
    tab["combined_C"]["auroc"] = S.auc(y, c); res["table"] = tab

    def ratio(t):
        yy = y[t]
        if yy.sum() < 2: return None
        fs, ff_, fc = (fa_per_1000(x[t], yy, target)[0] for x in (s, f, c)); b = min(fs, ff_)
        return fc / b if b > 0 else None
    bt = S.Boot(pid); ci = bt.ci(ratio); hh = [ratio(np.flatnonzero(hv == k)) for k in (0, 1)]
    res["ratio_C_over_better"] = dict(ci, halves=hh, qualifies=bool(ci["est"] is not None and ci["est"] <= 0.80))
    res["candidates"] = [S.candidate("U3_FA_ratio_C_over_better", "U3 (9.7)", "false alarms per 1,000 at the radiologists' sensitivity: C / min(Sybil, F)",
                                     "y1, all screens", "<", 1.0, ci, hh, res["counts"], partly_seen=True, qualification="ratio <= 0.80")]
    # SMDs where C removes a Sybil false alarm
    arm, _t = S.primary_arm(R, a.tag, a.K)
    if arm is not None:
        F = S.family_table(R, a.tag, arm, a.K); labels = dict(zip(F.family, F.label)) if len(F) else {}
        X, kind = S.variables(P, S.contrib(a.tag, arm, a.K), labels, t=1); cols = [c_ for c_ in X.columns if kind[c_] in ("G", "family")]
        sflag = s >= tab["sybil"]["threshold"]; cflag = c >= tab["combined_C"]["threshold"]
        removed, kept = (y == 0) & sflag & ~cflag, (y == 0) & sflag & cflag
        rows = S.smd_table(cols, X, removed, kept, pid, half=hv)
        for r in rows: r["kind"] = kind[r["variable"]]
        res["removed_vs_kept_sybil_false_alarms"] = dict(primary_arm=arm, removed=int(removed.sum()), kept=int(kept.sum()), smd=rows)
    S.write(R, f"s4_u3_{a.tag}.json", res)
    print(f"s4_u3: written; target sensitivity {target:.3f}")


if __name__ == "__main__":
    main()
