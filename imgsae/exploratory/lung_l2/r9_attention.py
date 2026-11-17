"""Lung L2, step R3 (dev only, descriptive; never a hypothesis; the lead asked "can we show the nodule Sybil sees? map the cancer?").
Plan logged before this ran. Does Sybil's saved attention point at the nodule the radiologist recorded?
- Nodule: per exam the largest recorded nodule (NLST CT abnormality table, sct_ab_desc 51) with a slice number (sct_slice_num) not above
  the image count of our series. Its place in Sybil's 200-slice box: r = (slice_num - 1) * thickness / 2.5 (Sybil puts slices at the
  thickness and resamples to 2.5 mm), box index b = r - (resampled_T - 200) / 2 (centre crop or pad), z-bin = floor(b / 8) of 25.
- Slice attention: att_vol1 and att_vol2 (log-scores), softmax over the 25 bins per member, mean of the 5 members.
  Measure: attention share within +-1 bin of the nodule bin; peak within +-1 bin. Baseline: the nodule bins shuffled between exams of the
  same group (2,000 times). The box order (same as the slice numbers or reversed) is chosen on participant half A, reported on half B.
- In-plane: att_img1 (16 x 16 per bin) at the nodule bin; attention share in the image half on the nodule's side (lobe: right 1-3,
  left 4-6). Side convention chosen on half A, reported on half B.
- Groups: cancer within 1 year; no cancer with nodule >= 8 mm; no cancer with nodule 4 to < 8 mm.
usage: python r9_attention.py <assembled dir> <per-series dir> <nlst tables dir> <out dir>
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s4_common as S4  # noqa: E402


def sm(x, ax=-1):
    x = x - x.max(ax, keepdims=True); e = np.exp(x); return e / e.sum(ax, keepdims=True)


def main():
    A, V, T, out = map(Path, sys.argv[1:5])
    E = pd.read_csv(A / "exams_dev.csv", dtype={"pid": str}, low_memory=False)
    if not (E.grp == "dev").all(): raise SystemExit("REFUSED: non-dev rows")
    Z = np.load(A / "arrays_dev_main.npz", allow_pickle=True); pos = {u: i for i, u in enumerate(Z["series_uid"])}; idx = np.array([pos[u] for u in E.series_uid])
    att = {k: sm(Z[k][idx].astype(np.float64)).mean(1) for k in ("att_vol1", "att_vol2")}
    N = pd.read_csv(T / "nlst_780_ctab_idc_20210527.csv", dtype={"pid": str}); N = N[(N.sct_ab_desc == 51) & N.sct_slice_num.notna()]
    N = N.sort_values("sct_long_dia", ascending=False).drop_duplicates(["pid", "study_yr"])
    J = E.reset_index().merge(N[["pid", "study_yr", "sct_slice_num", "sct_long_dia", "sct_epi_loc"]], on=["pid", "study_yr"])
    J = J[J.sct_slice_num <= J.n_images].copy()
    b = (J.sct_slice_num - 1) * J.thickness / 2.5 - (J.resampled_T - 200) / 2; J = J[(b >= 0) & (b < 200)].copy(); J["bin"] = (((J.sct_slice_num - 1) * J.thickness / 2.5 - (J.resampled_T - 200) / 2) // 8).astype(int)
    J["grp"] = np.where(J.y1 == 1, "cancer_1y", np.where(J.sct_long_dia >= 8, "no_cancer_ge8mm", np.where(J.sct_long_dia >= 4, "no_cancer_4to8mm", "small")))
    J = J[J.grp != "small"].reset_index(drop=True); half = dict(zip(E.pid, S4.halves(E.pid.to_numpy()))); J["half"] = J.pid.map(half)
    res = dict(n_exams=int(len(J)), groups=J.grp.value_counts().to_dict())

    def near(a, bins):
        return np.array([a[i, max(0, k - 1):k + 2].sum() for i, k in enumerate(bins)]), np.array([abs(int(np.argmax(a[i])) - k) <= 1 for i, k in enumerate(bins)])
    for key in ("att_vol1", "att_vol2"):
        a = att[key][J["index"].to_numpy()]
        sA = {o: near(a[J.half == 0], (J.bin if o == "same" else 24 - J.bin)[J.half == 0].to_numpy())[0].mean() for o in ("same", "reversed")}
        o = max(sA, key=sA.get); bins = (J.bin if o == "same" else 24 - J.bin).to_numpy(); r = dict(order_chosen_on_half_A=o, half_A_share=sA)
        for g in res["groups"]:
            m = ((J.grp == g) & (J.half == 1)).to_numpy(); sh, pk = near(a[m], bins[m]); rng = np.random.default_rng(0)
            base = np.array([near(a[m], rng.permutation(bins[m]))[0].mean() for _ in range(2000)])
            r[g] = dict(n_half_B=int(m.sum()), share_near_nodule=float(sh.mean()), peak_within_1_bin=float(pk.mean()), shuffled_share_median=float(np.median(base)),
                        shuffled_share_p97_5=float(np.quantile(base, 0.975)), uniform_share=3 / 25)
        res[key] = r
    # in-plane side, at the nodule bin (cancer and >= 8 mm groups)
    S = J[J.grp.isin(["cancer_1y", "no_cancer_ge8mm"]) & J.sct_epi_loc.isin([1, 2, 3, 4, 5, 6])].reset_index(drop=True); side = np.where(S.sct_epi_loc <= 3, "R", "L")
    k = (S.bin if res["att_vol1"]["order_chosen_on_half_A"] == "same" else 24 - S.bin).to_numpy(); left = []
    for i, u in enumerate(S.series_uid):
        m = sm(np.load(V / f"{u}.npz")["att_img1"].astype(np.float64)[:, k[i]]).mean(0).reshape(16, 16); left.append(m[:, :8].sum())
    left = np.array(left); hA = (S.half == 0).to_numpy()
    conv = "R_is_image_left" if (left[hA & (side == "R")].mean() - left[hA & (side == "L")].mean()) > 0 else "R_is_image_right"
    on_side = np.where((side == "R") == (conv == "R_is_image_left"), left, 1 - left)
    res["in_plane"] = dict(convention_chosen_on_half_A=conv, **{g: dict(n_half_B=int(((S.grp == g) & ~hA).sum()), share_on_nodule_side=float(on_side[(S.grp == g).to_numpy() & ~hA].mean()),
                                                                 share_nodule_side_gt_0p6=float((on_side[(S.grp == g).to_numpy() & ~hA] > 0.6).mean())) for g in ("cancer_1y", "no_cancer_ge8mm")})
    (out / "r9_attention_dev.json").write_text(json.dumps(res, indent=1, default=str)); print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
