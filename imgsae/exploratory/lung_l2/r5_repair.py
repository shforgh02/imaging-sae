"""Lung L2, step R6 (rescue scouting; dev only, exploratory; ADDED after R5 was seen, logged before it ran): two checks on the shared
axes of layer `pooled`.
 1. Repair test. R5 showed that the z-fix moves shared axis 0 ("z-geometry") by 2.7 SD. If this axis is set to its dev mean in every
    member (for the main run and for the z-fix run), how much of the z-fix effect on the score is left? Same for the kernel change.
    Reported for: nothing removed (must reproduce S4: share 0.670, mean delta lbar_1 -0.326), axis 0, the technical axes, and 200 random
    directions of the same space (the baseline). Flag: lbar_1 at or above its 90th percentile among dev exams without cancer at 1 year
    (recomputed after each removal; an approximation of the S4 flag, which uses the calibrated score).
 2. Random-choice test for the claim "the z-fix moves axis 0 by more than 1 SD": 2,000 random axes (one random direction per member,
    mean of the five), their mean z-fix change in SD units.
usage: python r5_repair.py <assembled dir> <heads npz> <out dir>
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, r"D:\Shayan\imgsae")
import r1_arms as R1  # noqa: E402
import r2_shared as R2  # noqa: E402
import s4_common as S4  # noqa: E402
import s4_decomp as DC  # noqa: E402
from r4_axes_audit import remove  # noqa: E402


def main():
    A, heads, out, L = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), "pooled"; sys.modules["__main__"].Shared = R2.Shared
    E, X, LG, logits, _, _ = R1.load(A, heads, L); P = pickle.load(open(R2.DATA / "r" / f"r2_shared_{L}.pkl", "rb")); sh, k = P["shared"], P["k"]
    T = pd.read_csv(out / f"r2_axes_{L}.csv"); C = T[T.rotation == "cca"].set_index("axis"); tech = [j for j in range(k) if C.label[j] == "T"]
    lb1, lb6 = LG[:, :, 0].mean(1), LG[:, :, 5].mean(1); sd1, sd6 = lb1.std(ddof=1), lb6.std(ddof=1); y1 = E.y1.to_numpy(float); y6 = np.where(E.study_yr == 0, E.y6, np.nan).astype(float)
    rowpos = {u: i for i, u in enumerate(E.series_uid)}; V = {}
    for var, short in (("zfix", "zfix"), ("pair", "kernel")):
        Vf = pd.read_csv(A / f"variant_dev_{var}.csv", low_memory=False); Z = np.load(A / f"arrays_dev_{var}.npz", allow_pickle=True); pos = {u: i for i, u in enumerate(Z["series_uid"])}
        Vf["main_uid"] = Vf.series_uid if var == "zfix" else Vf.partner_of; Vf = Vf[Vf.main_uid.isin(rowpos)].reset_index(drop=True); mi = np.array([rowpos[u] for u in Vf.main_uid])
        if var == "zfix": keep = (E.ratio.to_numpy()[mi] <= 0.65); Vf, mi = Vf[keep].reset_index(drop=True), mi[keep]
        V[short] = (mi, Z[L][np.array([pos[u] for u in Vf.series_uid])].astype(np.float64))

    def lbar(Xs, dirs):
        Lg = np.stack([logits(Xs[:, m] if dirs is None else remove(sh, Xs[:, m], m, dirs[m]), m)[0] for m in range(5)], 1); return Lg[:, :, 0].mean(1), Lg[:, :, 5].mean(1)

    def test(dirs, full=True):
        a1, a6 = lbar(X, dirs); tau = np.quantile(a1[y1 == 0], 0.90); o = {}
        if full: o.update(auroc_y1=DC.auc(y1, a1), auroc_y6=DC.auc(y6, a6), r_with_original_lbar6=float(np.corrcoef(a6, lb6)[0, 1]))
        for short, (mi, Xv) in V.items():
            v1, v6 = lbar(Xv, dirs); d1 = v1 - a1[mi]; d6 = (v6 - a6[mi]) / sd6
            o[short] = dict(n=int(len(mi)), share_ge_quarter_sd_lbar6=float((np.abs(d6) >= 0.25).mean()), mean_delta_lbar1=float(d1.mean()), mean_abs_delta_lbar6_sd=float(np.abs(d6).mean()),
                            share_flag_changed=float(((v1 >= tau) != (a1[mi] >= tau)).mean()), flags_main=int((a1[mi] >= tau).sum()), flags_variant=int((v1 >= tau).sum()))
            if full:
                bt = S4.Boot(E.pid.to_numpy()[mi]); hv = S4.halves(E.pid.to_numpy())[mi]; ok = np.abs(d6) >= 0.25
                o[short]["share_ci"] = bt.ci(lambda t: float(ok[t].mean())); o[short]["share_halves"] = [float(ok[hv == h].mean()) for h in (0, 1)]
                o[short]["mean_delta_lbar1_ci"] = bt.ci(lambda t: float(d1[t].mean())); o[short]["mean_delta_lbar1_halves"] = [float(d1[hv == h].mean()) for h in (0, 1)]
        return o
    res = dict(layer=L, sd_lbar6=float(sd6), technical_axes=tech)
    res["nothing_removed"] = test(None); res["axis_0_removed"] = test([sh.Wt[m][:, [0]] for m in range(5)]); res["technical_axes_removed"] = test([sh.Wt[m][:, tech] for m in range(5)])
    for j in range(1, k): res[f"axis_{j}_removed"] = test([sh.Wt[m][:, [j]] for m in range(5)], full=False)
    rng = np.random.default_rng(0); rnd = []
    for _ in range(200):
        o = test([(lambda v: v / np.linalg.norm(v))(rng.normal(size=(sh.npc, 1))) for m in range(5)], full=False); rnd.append(dict(zfix_share=o["zfix"]["share_ge_quarter_sd_lbar6"], zfix_mean_d1=o["zfix"]["mean_delta_lbar1"], zfix_flag=o["zfix"]["share_flag_changed"]))
    Rn = pd.DataFrame(rnd); res["random_direction_removed"] = {c: dict(median=float(Rn[c].median()), p2_5=float(Rn[c].quantile(0.025)), p97_5=float(Rn[c].quantile(0.975)), min=float(Rn[c].min()), max=float(Rn[c].max())) for c in Rn}
    # ---- random-choice test: mean z-fix change of 2,000 random axes, in SD units
    mi, Xv = V["zfix"]; Wm = [sh.white(X[:, m], m) for m in range(5)]; Wv = [sh.white(Xv[:, m], m) for m in range(5)]; rng = np.random.default_rng(1); n_r = 2000
    Am = [(lambda a: a / np.linalg.norm(a, axis=0))(rng.normal(size=(sh.npc, n_r))) for m in range(5)]
    act_m = np.mean([Wm[m] @ Am[m] for m in range(5)], 0); act_v = np.mean([Wv[m] @ Am[m] for m in range(5)], 0); shift = (act_v - act_m[mi]).mean(0) / act_m.std(0)
    real = np.mean([Wv[m] @ sh.Wt[m][:, :k] for m in range(5)], 0) - np.mean([Wm[m] @ sh.Wt[m][:, :k] for m in range(5)], 0)[mi]; real = real.mean(0) / np.mean([Wm[m] @ sh.Wt[m][:, :k] for m in range(5)], 0).std(0)
    res["random_choice_zfix_axis_shift"] = dict(n_random=n_r, share_abs_ge_1sd=float((np.abs(shift) >= 1).mean()), share_abs_ge_half_sd=float((np.abs(shift) >= 0.5).mean()), max_abs=float(np.abs(shift).max()),
                                                p97_5_abs=float(np.quantile(np.abs(shift), 0.975)), real_axes_shift_sd=np.round(real, 3).tolist())
    (out / f"r5_repair_{L}.json").write_text(json.dumps(res, indent=1, default=str))
    for name in ("nothing_removed", "axis_0_removed", "technical_axes_removed"):
        o = res[name]; print(name, {q: round(o[q], 4) for q in ("auroc_y1", "auroc_y6", "r_with_original_lbar6")})
        for s in ("zfix", "kernel"): print("   ", s, {q: (round(v, 4) if isinstance(v, float) else v) for q, v in o[s].items() if not isinstance(v, (dict, list))}, "share CI", [round(o[s]["share_ci"][q], 3) for q in ("lo", "hi")], "halves", np.round(o[s]["share_halves"], 3).tolist(), "d1 CI", [round(o[s]["mean_delta_lbar1_ci"][q], 3) for q in ("lo", "hi")])
    for j in range(1, k): print(f"axis {j} removed: zfix", {q: round(v, 3) for q, v in res[f"axis_{j}_removed"]["zfix"].items() if isinstance(v, float)})
    print("random direction removed:", json.dumps(res["random_direction_removed"])); print("random-choice:", json.dumps(res["random_choice_zfix_axis_shift"]))


if __name__ == "__main__":
    main()
