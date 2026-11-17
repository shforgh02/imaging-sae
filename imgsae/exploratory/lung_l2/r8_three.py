"""Lung L2, step R2-C (dev only, exploratory; the lead asked "why 5 of 5, why not 3 of 5, to have more axes?"). Plan logged before this ran.
Shared axes of layer `pooled` for every set of 3 of the 5 members (10 sets), with the method and thresholds of r2_shared.py (30 PCs per member,
fit on one participant half, shared if the mean pairwise correlation of the 3 member variates on the other half is >= 0.70; both directions,
the smaller count). Then: the axes of each set fitted on all dev; an axis is NEW if its activation correlates below 0.70 (|r|) with every one
of the 11 five-member axes. New axes that come up in at least 2 of the 10 sets are named (S4 Shapley rule, both halves).
usage: python r8_three.py <assembled dir> <heads npz> <out dir>
"""
import itertools
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, r"D:\Shayan\imgsae")
import l2_data as D  # noqa: E402
import r1_arms as R1  # noqa: E402
import r2_shared as R2  # noqa: E402
import s4_decomp as DC  # noqa: E402
import s4_q1a as Q  # noqa: E402


def main():
    A, heads, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]); sys.modules["__main__"].Shared = R2.Shared
    E, X, LG, _, _, _ = R1.load(A, heads, "pooled"); P = pickle.load(open(R2.DATA / "r" / "r2_shared_pooled.pkl", "rb")); S5 = P["S"]
    half = Q.folds(E.pid.to_numpy(), k=2, seed=0); l6 = LG[:, :, 5].mean(1); res, new = dict(sets={}), []
    for sub in itertools.combinations(range(5), 3):
        Xs = X[:, list(sub)]; cnt = []
        for hh in (0, 1):
            r = R2.pair_r(R2.Shared().fit(Xs[half == hh]).variates(Xs[half != hh])); cnt.append(int((r >= R2.R_SHARED).sum()))
        kk = min(cnt); Sa = R2.Shared().fit(Xs).variates(Xs)[:, :, :kk].mean(1) if kk else np.zeros((len(E), 0))
        best = [float(np.abs(np.corrcoef(Sa[:, j], S5.T)[0, 1:]).max()) for j in range(kk)]
        nj = [j for j in range(kk) if best[j] < 0.70]; new += [(sub, j, Sa[:, j]) for j in nj]
        res["sets"]["".join(map(str, sub))] = dict(n_shared=cnt, n_final=kk, n_new=len(nj), best_r_with_5member_axes=np.round(best, 2).tolist())
        print(sub, res["sets"]["".join(map(str, sub))], flush=True)
    # group the new axes across sets (|r| >= 0.70), keep groups seen in >= 2 sets, name them
    grp = []
    for s, j, a in new:
        for g in grp:
            if abs(np.corrcoef(a, g["act"])[0, 1]) >= 0.70: g["sets"].append("".join(map(str, s))); break
        else: grp.append(dict(act=a, sets=["".join(map(str, s))]))
    fold = Q.folds(E.pid.to_numpy()); G = D.groups(E); AF = DC.assoc_frame(E, [c for g in G.values() for c in g]); cols = list(AF.columns); rows = []
    for i, g in enumerate(grp):
        row = dict(group=i, n_sets=len(g["sets"]), sets=" ".join(g["sets"]), r_lbar6=float(np.corrcoef(g["act"], l6)[0, 1]))
        if len(g["sets"]) >= 2:
            lab, tot, _ = DC.shapley_label(E, G, g["act"], fold); hl = [DC.shapley_label(E[half == h].reset_index(drop=True), G, g["act"][half == h], Q.folds(E.pid[half == h].to_numpy()))[0] for h in (0, 1)]
            assoc = DC.assoc_vector(AF, g["act"]); top = np.argsort(-np.nan_to_num(np.abs(assoc)))[:5]
            row.update(label=lab, cv_r2=tot, label_half_a=hl[0], label_half_b=hl[1], top_assoc="; ".join(f"{cols[t]} {assoc[t]:+.2f}" for t in top))
        rows.append(row)
    F = pd.DataFrame(rows); F.to_csv(out / "r8_three_new_axes.csv", index=False); res["new_axis_groups"] = int(len(F)); res["new_axis_groups_in_2plus_sets"] = int((F.n_sets >= 2).sum()) if len(F) else 0
    (out / "r8_three_pooled.json").write_text(json.dumps(res, indent=1)); print(json.dumps({k: v for k, v in res.items() if k != "sets"})); print(F.round(2).to_string() if len(F) else "no new axes")


if __name__ == "__main__":
    main()
