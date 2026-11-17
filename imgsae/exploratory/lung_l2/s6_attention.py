"""Lung L2, new freeze: where Sybil looks, on one root (descriptive secondary only; never a hypothesis; protocol 11: reported, not confirmed).
Method of step R3 (r9_attention.py), with the two conventions FROZEN from dev (chosen there on participant half A; no choice on test):
  slice box order 'reversed' for att_vol1 and att_vol2; in-plane side 'R_is_image_left' (patient right = image left).
- Nodule: per exam the largest recorded nodule (NLST CT abnormality table, sct_ab_desc 51) with a slice number not above the image count of
  the main series. Place in Sybil's 200-slice box: r = (slice_num - 1) * thickness / 2.5; b = r - (resampled_T - 200) / 2; z-bin = floor(b / 8)
  of 25 (exams with b outside [0, 200) are dropped). With the frozen order the bin is 24 - z-bin.
- Slice attention: att_vol1 and att_vol2 (log-scores), softmax over the 25 bins per member, mean of the 5 members. Share of attention within
  +-1 bin of the nodule bin; peak within +-1 bin. Baseline: nodule bins shuffled between exams of the same group (2,000 times, seed 0).
- In-plane: att_img1 (16 x 16 per bin) at the nodule bin; share of attention in the image half on the nodule's lung side (lobe codes 1-3
  right, 4-6 left).
- Groups: cancer within 1 year (y1 = 1); no cancer with nodule >= 8 mm; no cancer with nodule 4 to < 8 mm.
--dev-check: on dev, restrict to participant half B (s4_common.halves) and compare with results/r/r9_attention_dev.json (must be equal).
usage (venv python): python s6_attention.py <assembled dir> <per-series main dir> <nlst tables dir> <root: dev|test> <out json> [--dev-check <r9 json>]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import s4_common as S4  # noqa: E402

ORDER = {"att_vol1": "reversed", "att_vol2": "reversed"}   # frozen from dev (r9_attention_dev.json, chosen on half A)
SIDE = "R_is_image_left"                                    # frozen from dev (r9_attention_dev.json, chosen on half A)
GROUPS = ("cancer_1y", "no_cancer_ge8mm", "no_cancer_4to8mm")


def sm(x, ax=-1):
    x = x - x.max(ax, keepdims=True); e = np.exp(x); return e / e.sum(ax, keepdims=True)


def near(a, bins):
    return np.array([a[i, max(0, k - 1):k + 2].sum() for i, k in enumerate(bins)]), np.array([abs(int(np.argmax(a[i])) - k) <= 1 for i, k in enumerate(bins)])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("assembled"); ap.add_argument("series_dir"); ap.add_argument("tables"); ap.add_argument("root", choices=("dev", "test")); ap.add_argument("out")
    ap.add_argument("--dev-check", default=""); a = ap.parse_args(); A, V, T = Path(a.assembled), Path(a.series_dir), Path(a.tables)
    E = pd.read_csv(A / f"exams_{a.root}.csv", dtype={"pid": str}, low_memory=False)
    if not (E.grp == a.root).all(): raise SystemExit(f"REFUSED: the exam table holds rows outside '{a.root}'")
    if a.dev_check and a.root != "dev": raise SystemExit("REFUSED: --dev-check is for dev only")
    Z = np.load(A / f"arrays_{a.root}_main.npz", allow_pickle=True); pos = {u: i for i, u in enumerate(Z["series_uid"])}; idx = np.array([pos[u] for u in E.series_uid])
    att = {k: sm(Z[k][idx].astype(np.float64)).mean(1) for k in ORDER}
    N = pd.read_csv(T / "nlst_780_ctab_idc_20210527.csv", dtype={"pid": str}); N = N[(N.sct_ab_desc == 51) & N.sct_slice_num.notna()]
    N = N.sort_values("sct_long_dia", ascending=False).drop_duplicates(["pid", "study_yr"])
    J = E.reset_index().merge(N[["pid", "study_yr", "sct_slice_num", "sct_long_dia", "sct_epi_loc"]], on=["pid", "study_yr"])
    J = J[J.sct_slice_num <= J.n_images].copy()
    b = (J.sct_slice_num - 1) * J.thickness / 2.5 - (J.resampled_T - 200) / 2; J = J[(b >= 0) & (b < 200)].copy()
    J["bin"] = (((J.sct_slice_num - 1) * J.thickness / 2.5 - (J.resampled_T - 200) / 2) // 8).astype(int)
    J["grp"] = np.where(J.y1 == 1, "cancer_1y", np.where(J.sct_long_dia >= 8, "no_cancer_ge8mm", np.where(J.sct_long_dia >= 4, "no_cancer_4to8mm", "small")))
    J = J[J.grp != "small"].reset_index(drop=True)
    if a.dev_check:   # as r9: report on participant half B
        half = dict(zip(E.pid, S4.halves(E.pid.to_numpy()))); J = J[J.pid.map(half) == 1].reset_index(drop=True)
    res = dict(root=a.root, frozen_conventions=dict(order=ORDER, side=SIDE), dev_check_half_B=bool(a.dev_check), n_exams=int(len(J)),
               participants=int(J.pid.nunique()), groups={g: int((J.grp == g).sum()) for g in GROUPS})
    for key in ORDER:
        a_ = att[key][J["index"].to_numpy()]; bins = (J.bin if ORDER[key] == "same" else 24 - J.bin).to_numpy(); r = {}
        for g in GROUPS:
            m = (J.grp == g).to_numpy()
            if m.sum() < 2: r[g] = dict(n=int(m.sum())); continue
            sh, pk = near(a_[m], bins[m]); rng = np.random.default_rng(0)
            base = np.array([near(a_[m], rng.permutation(bins[m]))[0].mean() for _ in range(2000)])
            r[g] = dict(n=int(m.sum()), share_near_nodule=float(sh.mean()), peak_within_1_bin=float(pk.mean()), shuffled_share_median=float(np.median(base)),
                        shuffled_share_p97_5=float(np.quantile(base, 0.975)), uniform_share=3 / 25)
        res[key] = r
    Sx = J[J.grp.isin(["cancer_1y", "no_cancer_ge8mm"]) & J.sct_epi_loc.isin([1, 2, 3, 4, 5, 6])].reset_index(drop=True); side = np.where(Sx.sct_epi_loc <= 3, "R", "L")
    k = (Sx.bin if ORDER["att_vol1"] == "same" else 24 - Sx.bin).to_numpy(); left = []
    for i, u in enumerate(Sx.series_uid):
        mm = sm(np.load(V / f"{u}.npz")["att_img1"].astype(np.float64)[:, k[i]]).mean(0).reshape(16, 16); left.append(mm[:, :8].sum())
    left = np.array(left); on_side = np.where((side == "R") == (SIDE == "R_is_image_left"), left, 1 - left)
    res["in_plane"] = {g: dict(n=int((Sx.grp == g).sum()), share_on_nodule_side=float(on_side[(Sx.grp == g).to_numpy()].mean()) if (Sx.grp == g).any() else None,
                               share_nodule_side_gt_0p6=float((on_side[(Sx.grp == g).to_numpy()] > 0.6).mean()) if (Sx.grp == g).any() else None) for g in ("cancer_1y", "no_cancer_ge8mm")}
    if a.dev_check:
        ref = json.loads(Path(a.dev_check).read_text()); d = []
        for key in ORDER:
            for g in GROUPS:
                for q in ("share_near_nodule", "peak_within_1_bin", "shuffled_share_median", "shuffled_share_p97_5"):
                    d.append(abs(res[key][g][q] - ref[key][g][q]))
                d.append(abs(res[key][g]["n"] - ref[key][g]["n_half_B"]))
        for g in ("cancer_1y", "no_cancer_ge8mm"):
            d += [abs(res["in_plane"][g][q] - ref["in_plane"][g][q]) for q in ("share_on_nodule_side", "share_nodule_side_gt_0p6")]
            d.append(abs(res["in_plane"][g]["n"] - ref["in_plane"][g]["n_half_B"]))
        res["dev_check_max_abs_difference_vs_r9"] = float(max(d))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True); Path(a.out).write_bytes((json.dumps(res, indent=1) + "\n").encode("utf-8"))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
