"""Lung L2, step R7 (rescue scouting; dev only, exploratory; ADDED after R6 was seen, logged before it ran): gate numbers (protocol 9.8)
and the random-choice test for two possible feature-level hypotheses about shared axis 0 of layer `pooled` ("z-geometry").
 C1 "the z-fix moves axis 0": mean change of axis 0 (z-fix minus main) in SD units, D5 exams. Proposed null -2.0, direction <.
 C2 "axis 0 carries the downward shift of the score": statistic = mean over D5 exams of
        [delta lbar_1 with axis 0 set to the dev mean in every member]  -  [delta lbar_1 as Sybil gives it]     (delta = z-fix minus main).
    Proposed null +0.20, direction >. (H2 says the plain delta is below -0.10; dev -0.326.)
For each: estimate, participant bootstrap interval (2,000 draws, seed 0), the two halves, and the same statistic for 2,000 random axes
(one random direction of the 30-PC space per member). If 5% or more of the random axes pass the null, the candidate is near-automatic.
usage: python r6_candidate.py <assembled dir> <heads npz> <out dir>
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, r"D:\Shayan\imgsae")
import r1_arms as R1  # noqa: E402
import r2_shared as R2  # noqa: E402
import s4_common as S4  # noqa: E402
from r4_axes_audit import remove  # noqa: E402


def main():
    A, heads, out, L = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), "pooled"; sys.modules["__main__"].Shared = R2.Shared
    import pandas as pd
    E, X, LG, logits, _, _ = R1.load(A, heads, L); P = pickle.load(open(R2.DATA / "r" / f"r2_shared_{L}.pkl", "rb")); sh = P["shared"]
    Vf = pd.read_csv(A / "variant_dev_zfix.csv", low_memory=False); Z = np.load(A / "arrays_dev_zfix.npz", allow_pickle=True); pos = {u: i for i, u in enumerate(Z["series_uid"])}
    rowpos = {u: i for i, u in enumerate(E.series_uid)}; Vf = Vf[Vf.series_uid.isin(rowpos)].reset_index(drop=True); mi = np.array([rowpos[u] for u in Vf.series_uid]); keep = E.ratio.to_numpy()[mi] <= 0.65
    Vf, mi = Vf[keep].reset_index(drop=True), mi[keep]; Xm = X[mi]; Xv = Z[L][np.array([pos[u] for u in Vf.series_uid])].astype(np.float64); pid = E.pid.to_numpy()[mi]; bt = S4.Boot(pid); hv = S4.halves(E.pid.to_numpy())[mi]
    l1 = lambda Xs, dirs: np.stack([logits(Xs[:, m] if dirs is None else remove(sh, Xs[:, m], m, dirs[m]), m)[0][:, 0] for m in range(5)], 1).mean(1)   # noqa: E731
    d0 = l1(Xv, None) - l1(Xm, None)
    Wall = [sh.white(X[:, m], m) for m in range(5)]; Wm = [w[mi] for w in Wall]; Wv = [sh.white(Xv[:, m], m) for m in range(5)]

    def c1(dirs):   # per-exam change of the axis in SD units (SD over all dev main exams)
        return (np.mean([Wv[m] @ dirs[m][:, 0] for m in range(5)], 0) - np.mean([Wm[m] @ dirs[m][:, 0] for m in range(5)], 0)) / np.mean([Wall[m] @ dirs[m][:, 0] for m in range(5)], 0).std()

    def c2(dirs): return (l1(Xv, dirs) - l1(Xm, dirs)) - d0
    ax0 = [sh.Wt[m][:, [0]] for m in range(5)]; res = dict(n_D5=int(len(mi)), participants=int(len(set(pid))), mean_delta_lbar1_plain=float(d0.mean()))
    rng = np.random.default_rng(2); rnd = [[(lambda v: v / np.linalg.norm(v))(rng.normal(size=(sh.npc, 1))) for m in range(5)] for _ in range(2000)]
    for name, fn, null, direc in (("C1_zfix_moves_axis0_sd", c1, -2.0, "<"), ("C2_axis0_carries_shift_of_lbar1", c2, 0.20, ">")):
        v = fn(ax0); ci = bt.ci(lambda t: float(v[t].mean())); hh = [float(v[hv == h].mean()) for h in (0, 1)]; r = np.array([fn(d).mean() for d in rnd])
        ok = (lambda x: x < null) if direc == "<" else (lambda x: x > null)
        res[name] = dict(est=ci["est"], lo=ci["lo"], hi=ci["hi"], halves=hh, null=null, direction=direc, gate_9_8=bool(ok(ci["est"]) and ok(ci["lo"]) and ok(ci["hi"]) and all(ok(h) for h in hh)),
                         random=dict(n=len(r), share_passing_null=float(ok(r).mean()), share_passing_null_either_sign=float((np.abs(r) > abs(null)).mean()), min=float(r.min()), max=float(r.max()),
                                     p2_5=float(np.quantile(r, 0.025)), p97_5=float(np.quantile(r, 0.975))))
    (out / "r6_candidate_pooled.json").write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
