"""X11 descriptive follow-up (plan: docs/EXECUTION_LOG.md, 23 Nov, "Plan of one free follow-up check"; committed before this ran).
Does shared axis 0 already rise in ordinary scans when the natural padding slab in Sybil's 200-slice box gets thin?
All dev main runs (already scored on the cloud; no new Sybil run); axis 0 with the frozen axes in dev SD units, the same code as
x11_analysis.py; padded slices p = 200 - m_n_real_slices (slices of Sybil's tensor with any non-zero voxel; cloud/image_measures.py).
Only outcome-free columns are read. Participant bootstrap of each mean (2,000 draws, seed 0).
usage (venv python, from this folder): python x11_padcurve.py <assembled dev dir> <out json> [--frozen results/s5] [--run-info <dir>] [--fine]
--fine (POST HOC, added after Neon's review of the write-up; plan in the log 23 Nov, committed before it ran): 8-slice bins and five ratio
groups (overlapping, moderate, contiguous, gaps, ratio 0 or missing). Without --fine the output is the planned one.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "lung_l0"))
import s5_axes_freeze as AXF  # noqa: E402
import s6_frozen_analysis as FA  # noqa: E402

COLS = ["series_uid", "pid", "grp", "ratio", "tag_maker", "m_n_real_slices", "n_images", "true_spacing"]
BINS = [("0", 0, 0), ("1-8", 1, 8), ("9-16", 9, 16), ("17-24", 17, 24), ("25-32", 25, 32), ("33-48", 33, 48), ("49-64", 49, 64), ("65-80", 65, 80), (">80", 81, 200)]
BINS_FINE = [("0", 0, 0)] + [(f"{a}-{a + 7}", a, a + 7) for a in range(1, 96, 8)] + [(">96", 97, 200)]
N_BOOT, SEED = 2000, 0


def boot_mean(x, pid):
    codes, inv = np.unique(pid, return_inverse=True); n = len(codes)
    s = np.bincount(inv, weights=x, minlength=n); c = np.bincount(inv, minlength=n).astype(float)
    rng = np.random.default_rng(SEED); d = np.empty(N_BOOT)
    for b in range(N_BOOT):
        i = rng.integers(0, n, n); d[b] = s[i].sum() / c[i].sum()
    return float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5)), int(n)


def summ(x, pid):
    if len(x) == 0: return dict(n=0)
    lo, hi, npid = boot_mean(x, pid) if len(set(pid)) >= 2 else (None, None, len(set(pid)))
    return dict(n=int(len(x)), participants=npid, mean=float(x.mean()), lo=lo, hi=hi, median=float(np.median(x)), p05=float(np.quantile(x, 0.05)), p95=float(np.quantile(x, 0.95)))


def spearman(a, b):
    ra, rb = pd.Series(a).rank().to_numpy(), pd.Series(b).rank().to_numpy(); return float(np.corrcoef(ra, rb)[0, 1])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("assembled"); ap.add_argument("out")
    ap.add_argument("--frozen", default=str(HERE / "results" / "s5")); ap.add_argument("--run-info", default=r"D:\Shayan\imgsae_data\lung_l2_vol\l2\run_info")
    ap.add_argument("--fine", action="store_true"); a = ap.parse_args()
    A = Path(a.assembled); _, _, _, _, _, _, AX = FA.load_frozen(Path(a.frozen), Path(a.run_info))
    sd0, mu0 = float(AX["axis_sd_dev"][0]), float(AX["axis_mean_dev"][0])
    Ed = pd.read_csv(A / "exams_dev.csv", usecols=COLS, dtype={"pid": str}, low_memory=False)
    if not (Ed.grp == "dev").all(): raise SystemExit("REFUSED: non-dev rows")
    z = np.load(A / "arrays_dev_main.npz", allow_pickle=True); uid = z["series_uid"]; P = z["pooled"]
    if not set(uid) <= set(Ed.series_uid): raise SystemExit("REFUSED: dev arrays hold an exam outside the dev table")
    a0 = np.empty(len(uid))
    for s in range(0, len(uid), 500): a0[s:s + 500] = (AXF.activation(AX, P[s:s + 500].astype(np.float64))[:, 0] - mu0) / sd0
    D = pd.DataFrame(dict(series_uid=uid, axis0=a0)).merge(Ed, on="series_uid", how="left", validate="one_to_one")
    D["ratio"] = pd.to_numeric(D.ratio, errors="coerce"); D["nreal"] = pd.to_numeric(D.m_n_real_slices, errors="coerce")
    D["p"] = 200 - D.nreal; D["scan_length_mm"] = pd.to_numeric(D.n_images, errors="coerce") * pd.to_numeric(D.true_spacing, errors="coerce")
    cont, strt = D.ratio.between(0.95, 1.05), (D.ratio > 0) & (D.ratio <= 0.65)
    D["group"] = np.where(cont, "contiguous_0p95_1p05", np.where(strt, "stretched_0_0p65", "other"))
    ok = D.p.notna() & (D.p >= 0)
    if a.fine:
        mod, gap = (D.ratio > 0.65) & (D.ratio < 0.95), D.ratio > 1.05
        D["group"] = np.where(strt, "overlapping_0_0p65", np.where(mod, "moderate_0p65_0p95", np.where(cont, "contiguous_0p95_1p05", np.where(gap, "gaps_gt_1p05", "ratio_0_or_missing"))))
        res = dict(label="X11 POST HOC finer bins (after Neon's review of the write-up): axis 0 against the padded slices in Sybil's box (dev main runs; outcome-free)",
                   plan="docs/EXECUTION_LOG.md, 2026-11-23, Neon's check of the X11 write-up: post hoc finer bins",
                   counts=dict(exams=int(len(D)), with_padded_slices=int(ok.sum()), by_group={g: int((D.group == g).sum()) for g in sorted(D.group.unique())}), bins={})
        for g in sorted(D.group.unique()) + ["all"]:
            Dg = D[ok] if g == "all" else D[ok & (D.group == g)]; res["bins"][g] = {}
            for name, lo, hi in BINS_FINE:
                m = Dg.p.between(lo, hi); res["bins"][g][name] = summ(Dg.axis0[m].to_numpy(), Dg.pid[m].to_numpy())
        Path(a.out).write_text(json.dumps(res, indent=1, allow_nan=False) + "\n", encoding="utf-8", newline="\n"); print("written", a.out); return
    res = dict(label="X11 descriptive follow-up: axis 0 against the padded slices in Sybil's box (dev main runs; outcome-free; exploratory)",
               plan="docs/EXECUTION_LOG.md, 2026-11-23, plan of one free follow-up check",
               axis0_check_mean_contiguous=float(D.loc[cont, "axis0"].mean()),
               counts=dict(exams=int(len(D)), with_padded_slices=int(ok.sum()), missing_measure=int((~ok).sum()), by_group={g: int((D.group == g).sum()) for g in D.group.unique()}),
               bins={}, summary={})
    for g in ("contiguous_0p95_1p05", "stretched_0_0p65", "other", "all"):
        Dg = D[ok] if g == "all" else D[ok & (D.group == g)]; res["bins"][g] = {}
        for name, lo, hi in BINS:
            m = Dg.p.between(lo, hi); res["bins"][g][name] = summ(Dg.axis0[m].to_numpy(), Dg.pid[m].to_numpy())
    C = D[ok & cont]
    res["summary"]["contiguous"] = dict(n=int(len(C)), share_p_le_16=float((C.p <= 16).mean()), share_p_le_32=float((C.p <= 32).mean()),
                                        spearman_p_axis0=spearman(C.p, C.axis0), p_quantiles={str(q): float(C.p.quantile(q)) for q in (0.05, 0.25, 0.5, 0.75, 0.95)},
                                        scan_length_mm_quantiles={str(q): float(C.scan_length_mm.quantile(q)) for q in (0.05, 0.5, 0.95)})
    Path(a.out).write_text(json.dumps(res, indent=1, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    print("written", a.out)


if __name__ == "__main__":
    main()
