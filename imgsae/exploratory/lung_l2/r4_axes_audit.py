"""Lung L2, step R5 (rescue scouting; dev only, exploratory): what the shared axes of layer `pooled` do (the axes of r2_shared.py).
usage: python r4_axes_audit.py <assembled dir> <heads npz> <out dir> [--layer pooled] [--n-random 200]
 A. paired change of each axis under z-fix (D5: spacing/thickness <= 0.65) and under the kernel change (D4), in SD units of the axis
    (SD over all dev main exams); participant bootstrap (2,000 draws, seed 0) and the two halves. Both rotations (CCA order, ICA).
 B. removal test: in every member the axis is set to its dev mean (only that direction of the member's vector changes), then Sybil's own
    hidden layer and head give the logits. Reported: the change of the mean member logit in SD units, the share of exams that move by
    >= 0.25 SD, the share whose flag changes (flag here: lbar_1 at or above its 90th percentile among dev exams without cancer at 1 year;
    an approximation of the S4 flag, which uses the calibrated score), AUROC before and after (dev flatters Sybil: caution C6).
    Baseline: the same removal for random directions of the same 30-PC space of each member.
    Also sets: all technical axes together, all non-risk axes together, the risk axis.
Writes <out>/r4_axes_audit_<layer>.json and r4_axes_<layer>.csv.
"""
import argparse
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


def remove(sh, x, m, Amat):
    """member vector with the span of the columns of Amat (whitened-PC directions) set to the dev mean."""
    t = sh.T[m]; W = sh.white(x, m); Pj = Amat @ np.linalg.pinv(Amat.T @ Amat) @ Amat.T
    out = x.copy(); out[:, t["live"]] -= ((W @ Pj) * t["sc"]) @ t["P"] * t["sd"][t["live"]]; return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("assembled"); ap.add_argument("heads"); ap.add_argument("out"); ap.add_argument("--layer", default="pooled"); ap.add_argument("--n-random", type=int, default=200)
    a = ap.parse_args(); A, out, L = Path(a.assembled), Path(a.out), a.layer
    sys.modules["__main__"].Shared = R2.Shared            # the pickle was written by r2_shared.py run as a script
    E, X, LG, logits, _, _ = R1.load(A, a.heads, L); n = len(E); P = pickle.load(open(R2.DATA / "r" / f"r2_shared_{L}.pkl", "rb")); sh, k = P["shared"], P["k"]
    assert (P["series_uid"] == E.series_uid.to_numpy()).all()
    from sklearn.decomposition import FastICA
    S = sh.variates(X)[:, :, :k].mean(1); assert np.allclose(S, P["S"]); ic = FastICA(k, random_state=0, max_iter=2000, whiten="unit-variance").fit(S)
    Si = ic.transform(S); sk = np.sign(((Si - Si.mean(0)) ** 3).mean(0)); sk[sk == 0] = 1; Si = Si * sk; assert np.allclose(Si, P["S_ica"], atol=1e-6)
    acts = lambda Xv: (lambda Sv: {"cca": Sv, "ica": ic.transform(Sv) * sk})(sh.variates(Xv)[:, :, :k].mean(1))   # noqa: E731
    main_act = {"cca": S, "ica": Si}; sdA = {r: v.std(0) for r, v in main_act.items()}
    T = pd.read_csv(out / f"r2_axes_{L}.csv"); lb1, lb6 = LG[:, :, 0].mean(1), LG[:, :, 5].mean(1); sd1, sd6 = lb1.std(ddof=1), lb6.std(ddof=1)
    y1, y6 = E.y1.to_numpy(float), np.where(E.study_yr == 0, E.y6, np.nan).astype(float); rowpos = {u: i for i, u in enumerate(E.series_uid)}; hv_all = S4.halves(E.pid.to_numpy())
    res = dict(layer=L, n_axes=int(k), n_exams=n, sd_lbar1=float(sd1), sd_lbar6=float(sd6)); rows = {(r, j): dict(rotation=r, axis=j) for r in ("cca", "ica") for j in range(k)}
    # ---- A. paired change under z-fix and under the kernel change
    for var, short in (("zfix", "zfix"), ("pair", "kernel")):
        Vf = pd.read_csv(A / f"variant_dev_{var}.csv", low_memory=False); Z = np.load(A / f"arrays_dev_{var}.npz", allow_pickle=True); pos = {u: i for i, u in enumerate(Z["series_uid"])}
        Vf["main_uid"] = Vf.series_uid if var == "zfix" else Vf.partner_of; Vf = Vf[Vf.main_uid.isin(rowpos)].reset_index(drop=True); mi = np.array([rowpos[u] for u in Vf.main_uid])
        if var == "zfix": keep = (E.ratio.to_numpy()[mi] <= 0.65); Vf, mi = Vf[keep].reset_index(drop=True), mi[keep]
        vi = np.array([pos[u] for u in Vf.series_uid]); Av = acts(Z[L][vi].astype(np.float64)); lv = Z["logit"][vi].astype(np.float64)
        d6 = (lv[:, :, 5].mean(1) - lb6[mi]) / sd6; pid = E.pid.to_numpy()[mi]; bt = S4.Boot(pid); hv = hv_all[mi]
        res[short] = dict(n=int(len(mi)), participants=int(len(set(pid))), mean_delta_lbar6_sd=float(d6.mean()), share_lbar6_ge_quarter_sd=float((np.abs(d6) >= 0.25).mean()))
        for r in ("cca", "ica"):
            Dm = (Av[r] - main_act[r][mi]) / sdA[r]
            for j in range(k):
                d = Dm[:, j]; ci = bt.ci(lambda t: float(d[t].mean()))
                rows[r, j].update({f"{short}_mean_sd": ci["est"], f"{short}_lo": ci["lo"], f"{short}_hi": ci["hi"], f"{short}_half_a": float(d[hv == 0].mean()), f"{short}_half_b": float(d[hv == 1].mean()),
                                   f"{short}_share_abs_ge_half_sd": float((np.abs(d) >= 0.5).mean()), f"{short}_r_with_delta_lbar6": float(np.corrcoef(d, d6)[0, 1])})
    # ---- B. removal test (CCA axes: each has one direction per member)
    tau = np.quantile(lb1[y1 == 0], 0.90); flag0 = lb1 >= tau

    def effect(dirs):   # dirs: list over members of (30, q) matrices
        L1 = np.stack([logits(remove(sh, X[:, m], m, dirs[m]), m)[0] for m in range(5)], 1); n1, n6 = L1[:, :, 0].mean(1), L1[:, :, 5].mean(1); e1, e6 = (n1 - lb1) / sd1, (n6 - lb6) / sd6
        return dict(mean_delta_lbar1_sd=float(e1.mean()), mean_delta_lbar6_sd=float(e6.mean()), sd_delta_lbar1=float(e1.std()), sd_delta_lbar6=float(e6.std()), share_ge_quarter_sd_lbar6=float((np.abs(e6) >= 0.25).mean()),
                    share_flag_changed=float(((n1 >= tau) != flag0).mean()), r_new_old_lbar6=float(np.corrcoef(n6, lb6)[0, 1]), auroc_y1_before=DC.auc(y1, lb1), auroc_y1_after=DC.auc(y1, n1),
                    auroc_y6_before=DC.auc(y6, lb6), auroc_y6_after=DC.auc(y6, n6))
    for j in range(k):
        ef = effect([sh.Wt[m][:, [j]] for m in range(5)]); rows["cca", j].update({f"rm_{q}": v for q, v in ef.items()})
    C = T[T.rotation == "cca"].set_index("axis"); tech = [j for j in range(k) if C.label[j] == "T"]; nonrisk = [j for j in range(k) if abs(C.r_lbar6[j]) < 0.5]; risk = [j for j in range(k) if abs(C.r_lbar6[j]) >= 0.5]
    res["removal_sets"] = {name: dict(axes=js, **effect([sh.Wt[m][:, js] for m in range(5)])) for name, js in (("technical_axes", tech), ("non_risk_axes", nonrisk), ("risk_axes", risk), ("all_shared_axes", list(range(k)))) if js}
    rng = np.random.default_rng(0); rnd = []
    for _ in range(a.n_random):
        d = [(lambda v: v / np.linalg.norm(v))(rng.normal(size=(sh.npc, 1))) for m in range(5)]; rnd.append(effect(d))
    Rn = pd.DataFrame(rnd); res["removal_random_direction"] = dict(n=a.n_random, **{q: dict(median=float(Rn[q].median()), p95=float(Rn[q].quantile(0.95)), max=float(Rn[q].max())) for q in ("sd_delta_lbar6", "share_ge_quarter_sd_lbar6", "share_flag_changed")})
    F = T.merge(pd.DataFrame(list(rows.values())), on=["rotation", "axis"]); F.to_csv(out / f"r4_axes_{L}.csv", index=False)
    (out / f"r4_axes_audit_{L}.json").write_text(json.dumps(res, indent=1, default=str)); print(json.dumps(res, indent=1, default=str))
    pd.set_option("display.width", 250); c = ["rotation", "axis", "label", "r_lbar6", "zfix_mean_sd", "zfix_lo", "zfix_hi", "zfix_share_abs_ge_half_sd", "kernel_mean_sd", "kernel_lo", "kernel_hi", "rm_sd_delta_lbar6", "rm_share_ge_quarter_sd_lbar6", "rm_share_flag_changed", "rm_auroc_y1_after", "rm_auroc_y6_after"]
    print(F[c].round(3).to_string())


if __name__ == "__main__":
    main()
