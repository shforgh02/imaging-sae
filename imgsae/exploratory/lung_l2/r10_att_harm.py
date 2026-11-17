"""Lung L2, step R3b (dev only, exploratory; ADDED after R3 was seen, logged before it ran): does the stretch move Sybil's attention away
from the recorded nodule? A harm proxy that needs nodules, not cancers.
Same nodule, bin and attention rules as r9_attention.py (largest recorded nodule >= 4 mm; box order "reversed", chosen on half A in R3).
 1. Main runs: attention share within +-1 bin of the nodule, stretched (spacing/thickness <= 0.65) against other exams.
 2. D5, paired: main run (slices at the thickness, as Sybil does) against z-fix run (slices at the true spacing; the nodule bin is computed
    with the true spacing and the z-fix resampled_T). Mean paired difference (z-fix minus main), participant bootstrap, halves.
 Both for att_vol1; att_vol2 reported too. Cancer exams are included and also reported alone (counts only; few).
usage: python r10_att_harm.py <assembled dir> <nlst tables dir> <out dir>
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s4_common as S4  # noqa: E402
from r9_attention import sm  # noqa: E402


def bins(slice_num, step, resT):
    b = (slice_num - 1) * step / 2.5 - (resT - 200) / 2; ok = (b >= 0) & (b < 200); return ok, np.where(ok, 24 - (b // 8), -1).astype(int)   # "reversed" order


def near(a, k): return np.array([a[i, max(0, j - 1):j + 2].sum() if j >= 0 else np.nan for i, j in enumerate(k)])


def main():
    A, T, out = map(Path, sys.argv[1:4])
    E = pd.read_csv(A / "exams_dev.csv", dtype={"pid": str}, low_memory=False)
    if not (E.grp == "dev").all(): raise SystemExit("REFUSED: non-dev rows")
    N = pd.read_csv(T / "nlst_780_ctab_idc_20210527.csv", dtype={"pid": str}); N = N[(N.sct_ab_desc == 51) & N.sct_slice_num.notna() & (N.sct_long_dia >= 4)]
    N = N.sort_values("sct_long_dia", ascending=False).drop_duplicates(["pid", "study_yr"])
    J = E.merge(N[["pid", "study_yr", "sct_slice_num", "sct_long_dia"]], on=["pid", "study_yr"]); J = J[J.sct_slice_num <= J.n_images].reset_index(drop=True)
    Zm = np.load(A / "arrays_dev_main.npz", allow_pickle=True); pm = {u: i for i, u in enumerate(Zm["series_uid"])}; im = np.array([pm[u] for u in J.series_uid])
    half = S4.halves(E.pid.to_numpy()); hof = dict(zip(E.pid, half)); res = {}
    # fix (2026-11-17, before any result was reported): the variant table repeats the main run's resampled_T; the z-fix slice count before
    # crop or pad is n_images * true_spacing / 2.5 (it equals m_n_real_slices of the z-fix run when no crop happens)
    V = pd.read_csv(A / "variant_dev_zfix.csv", low_memory=False)[["series_uid", "n_images", "true_spacing"]].rename(columns={"true_spacing": "zsp"})
    V["zT"] = np.round(V.n_images * V.zsp / 2.5); V = V.drop(columns="n_images")
    Zz = np.load(A / "arrays_dev_zfix.npz", allow_pickle=True); pz = {u: i for i, u in enumerate(Zz["series_uid"])}
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
        r["D5_paired"] = dict(n=int(both.sum()), participants=int(len(set(pid))), nodule_outside_box_main=int((~ok1).sum()), nodule_outside_box_zfix=int((~ok2).sum()),
                              share_near_main=float(s1[both].mean()), share_near_zfix=float(s2[both].mean()), diff=dict(bt2.ci(lambda t: float(dd[t].mean())), halves=[float(dd[hv == h].mean()) for h in (0, 1)]),
                              peak_hit_main=float(pk1.mean()), peak_hit_zfix=float(pk2.mean()), cancer_1y_exams=int((P.y1.to_numpy()[both] == 1).sum()),
                              ge8mm=dict(n=int((P.sct_long_dia.to_numpy()[both] >= 8).sum()), share_near_main=float(s1[both][P.sct_long_dia.to_numpy()[both] >= 8].mean()), share_near_zfix=float(s2[both][P.sct_long_dia.to_numpy()[both] >= 8].mean())))
        res[key] = r
    (out / "r10_att_harm_dev.json").write_text(json.dumps(res, indent=1, default=str)); print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
