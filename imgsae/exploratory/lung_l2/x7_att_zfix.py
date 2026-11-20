"""Lung L2, plan X7 part P7 (docs/EXECUTION_LOG.md, 2026-11-20, plan committed 413dc07): does the stretch move Sybil's attention away
from the recorded nodule, on TEST? EXPLORATORY and post hoc (audit R2 section 6.4). The dev analysis R3b (r10_att_harm.py) applied to
any root: the same nodule, bin and attention rules (imports bins and near from r10_att_harm.py and sm from r9_attention.py; edits none).
 1. Main runs: attention share within +-1 bin of the largest recorded nodule >= 4 mm, stretched (ratio <= 0.65) against other exams.
 2. Paired (z-fix rows): main run against z-fix run (the nodule bin computed with the true spacing for the z-fix run).
On dev the output must equal results/r/r10_att_harm_dev.json (check). Outcomes: only a count of 1-year cancer exams (as R3b).
usage (venv python): python x7_att_zfix.py <assembled dir> <nlst tables dir> <out dir> --root dev|test
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s4_common as S4  # noqa: E402
from r10_att_harm import bins, near  # noqa: E402
from r9_attention import sm  # noqa: E402


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("assembled"); ap.add_argument("tables"); ap.add_argument("out"); ap.add_argument("--root", default="dev")
    a = ap.parse_args(); A, T, out, root = Path(a.assembled), Path(a.tables), Path(a.out), a.root; out.mkdir(parents=True, exist_ok=True)
    E = pd.read_csv(A / f"exams_{root}.csv", dtype={"pid": str}, low_memory=False)
    if not (E.grp == root).all(): raise SystemExit(f"REFUSED: rows outside root {root}")
    N = pd.read_csv(T / "nlst_780_ctab_idc_20210527.csv", dtype={"pid": str}); N = N[(N.sct_ab_desc == 51) & N.sct_slice_num.notna() & (N.sct_long_dia >= 4)]
    N = N.sort_values("sct_long_dia", ascending=False).drop_duplicates(["pid", "study_yr"])
    J = E.merge(N[["pid", "study_yr", "sct_slice_num", "sct_long_dia"]], on=["pid", "study_yr"]); J = J[J.sct_slice_num <= J.n_images].reset_index(drop=True)
    Zm = np.load(A / f"arrays_{root}_main.npz", allow_pickle=True); pm = {u: i for i, u in enumerate(Zm["series_uid"])}; im = np.array([pm[u] for u in J.series_uid])
    half = S4.halves(E.pid.to_numpy()); hof = dict(zip(E.pid, half)); res = {}
    V = pd.read_csv(A / f"variant_{root}_zfix.csv", low_memory=False)[["series_uid", "n_images", "true_spacing"]].rename(columns={"true_spacing": "zsp"})
    V["zT"] = np.round(V.n_images * V.zsp / 2.5); V = V.drop(columns="n_images")
    Zz = np.load(A / f"arrays_{root}_zfix.npz", allow_pickle=True); pz = {u: i for i, u in enumerate(Zz["series_uid"])}
    for key in ("att_vol1", "att_vol2"):
        am = sm(Zm[key][im].astype(np.float64)).mean(1); ok, k = bins(J.sct_slice_num.to_numpy(), J.thickness.to_numpy(), J.resampled_T.to_numpy()); s = near(am, k)
        st = (J.ratio <= 0.65).to_numpy(); m = ok
        bt = S4.Boot(J.pid.to_numpy()[m]); sv, sm_ = s[m], st[m]
        d = bt.ci(lambda t: float(np.nanmean(sv[t][sm_[t]]) - np.nanmean(sv[t][~sm_[t]])))
        r = dict(main_stretched=dict(n=int((m & st).sum()), share_near=float(np.nanmean(s[m & st]))), main_other=dict(n=int((m & ~st).sum()), share_near=float(np.nanmean(s[m & ~st]))), diff_stretched_minus_other=d)
        P = J[st].merge(V, on="series_uid").reset_index(drop=True); P = P[P.ratio <= 0.65].reset_index(drop=True)
        a1 = sm(Zm[key][np.array([pm[u] for u in P.series_uid])].astype(np.float64)).mean(1); a2 = sm(Zz[key][np.array([pz[u] for u in P.series_uid])].astype(np.float64)).mean(1)
        ok1, k1 = bins(P.sct_slice_num.to_numpy(), P.thickness.to_numpy(), P.resampled_T.to_numpy()); ok2, k2 = bins(P.sct_slice_num.to_numpy(), P.zsp.to_numpy(), P.zT.to_numpy())
        s1, s2 = near(a1, k1), near(a2, k2); both = ok1 & ok2; dd = (s2 - s1)[both]; pid = P.pid.to_numpy()[both]; hv = np.array([hof[p] for p in pid]); bt2 = S4.Boot(pid)
        pk1 = np.array([abs(int(np.argmax(a1[i])) - k1[i]) <= 1 for i in range(len(P))])[both]; pk2 = np.array([abs(int(np.argmax(a2[i])) - k2[i]) <= 1 for i in range(len(P))])[both]
        g8 = P.sct_long_dia.to_numpy()[both] >= 8
        r["D5_paired"] = dict(n=int(both.sum()), participants=int(len(set(pid))), nodule_outside_box_main=int((~ok1).sum()), nodule_outside_box_zfix=int((~ok2).sum()),
                              share_near_main=float(s1[both].mean()), share_near_zfix=float(s2[both].mean()), diff=dict(bt2.ci(lambda t: float(dd[t].mean())), halves=[float(dd[hv == h].mean()) for h in (0, 1)]),
                              peak_hit_main=float(pk1.mean()), peak_hit_zfix=float(pk2.mean()), cancer_1y_exams=int((P.y1.to_numpy()[both] == 1).sum()),
                              ge8mm=dict(n=int(g8.sum()), share_near_main=float(s1[both][g8].mean()), share_near_zfix=float(s2[both][g8].mean())))
        r["D5_paired"]["rows_with_zfix_variant"] = int(len(P))
        res[key] = r
    # P9 (plan amendment, logged before the test run): the z-fix change of lbar_1 split by crop and pad (outcome-free; all z-fix rows)
    Q = E[E.ratio <= 0.65].merge(V, on="series_uid").reset_index(drop=True)
    lm = Zm["logit"][np.array([pm[u] for u in Q.series_uid])].astype(np.float64)[:, :, 0].mean(1)
    lz = Zz["logit"][np.array([pz[u] for u in Q.series_uid])].astype(np.float64)[:, :, 0].mean(1); d1 = lz - lm
    crop = (Q.resampled_T > 200).to_numpy(); pad = (Q.zT < 200).to_numpy(); pid = Q.pid.to_numpy(); p9 = dict(all=dict(n=int(len(Q)), mean_d1=float(d1.mean())))
    for nm, mk in (("main_cropped_zfix_padded", crop & pad), ("main_cropped_zfix_not_padded", crop & ~pad), ("main_not_cropped_zfix_padded", ~crop & pad),
                   ("main_not_cropped_zfix_not_padded", ~crop & ~pad)):
        p9[nm] = dict(n=int(mk.sum()), participants=int(len(set(pid[mk]))))
        if mk.sum() >= 10: p9[nm]["mean_d1"] = S4.Boot(pid[mk]).ci(lambda t, v=d1[mk]: float(v[t].mean()))
    ns = E[E.ratio > 0.65]
    p9["not_stretched_main_exams"] = dict(n=int(len(ns)), padded=int((ns.resampled_T < 200).sum()), share_padded=float((ns.resampled_T < 200).mean()),
                                          cropped=int((ns.resampled_T > 200).sum()), note="Sybil pads every scan shorter than 200 resampled slices; ordinary scans are padded too")
    p9["note"] = "cropped: main resampled slices > 200 (Sybil crops to 200); padded: z-fix slices n_images x true spacing / 2.5 < 200 (Sybil pads to 200 with its padding value)"
    res["P9_zfix_change_by_crop_and_pad"] = p9
    res["label"] = "EXPLORATORY, post hoc (plan X7 part P7, committed 413dc07); the R3b analysis (r10_att_harm.py) on root " + root
    (out / f"x7_att_zfix_{root}.json").write_text(json.dumps(res, indent=1, default=str)); print("written", out / f"x7_att_zfix_{root}.json")


if __name__ == "__main__":
    main()
