"""Lung L2, plan X11 (docs/EXECUTION_LOG.md, 22 Nov, commit 2a624b5): the fixed exam list for the padding / synthetic-stretch test.
Dev exams only (already used for discovery); reads no outcome column (only geometry, maker and participant ids).
Arm A: 0 < ratio <= 0.65, one exam per participant, seed 0, GE 24, Philips 24, Siemens 12; if fewer than 12 have a main volume of <= 200 slices,
uncropped exams are added in the same seed order until 12. Arm B: 0.95 <= ratio <= 1.05, one per participant, seed 0, 12 per maker.
usage (venv python): python x11_list.py <dev exams csv> <manifest_dev.csv> <out csv>
"""
import sys

import numpy as np
import pandas as pd

COLS = ["series_uid", "pid", "study_yr", "ratio", "thickness", "true_spacing", "n_images", "resampled_T", "tag_maker", "tag_model"]


def maker(s): return s.fillna("?").str.upper().str.extract(r"(GE|PHILIPS|SIEMENS|TOSHIBA)", expand=False).fillna("OTHER")


def one_per_participant(D, seed):
    D = D.sample(frac=1.0, random_state=seed); return D.drop_duplicates("pid", keep="first")


def main():
    E = pd.read_csv(sys.argv[1], usecols=COLS, low_memory=False); M = pd.read_csv(sys.argv[2], usecols=["series_uid", "url"])
    E["maker"] = maker(E.tag_maker); out = []
    A = one_per_participant(E[(E.ratio > 0) & (E.ratio <= 0.65)], 0)
    pick = pd.concat([A[A.maker == m].head(n) for m, n in (("GE", 24), ("PHILIPS", 24), ("SIEMENS", 12))])
    unc = int((pick.resampled_T <= 200).sum())
    if unc < 12:
        extra = A[~A.series_uid.isin(pick.series_uid) & (A.resampled_T <= 200) & A.maker.isin(["GE", "PHILIPS", "SIEMENS"])].head(12 - unc)
        pick = pd.concat([pick, extra])
    out.append(pick.assign(arm="A"))
    B = one_per_participant(E[(E.ratio >= 0.95) & (E.ratio <= 1.05) & ~E.pid.isin(pick.pid)], 0)
    out.append(pd.concat([B[B.maker == m].head(12) for m in ("GE", "PHILIPS", "SIEMENS", "TOSHIBA")]).assign(arm="B"))
    L = pd.concat(out).merge(M, on="series_uid", how="left")
    if L.url.isna().any(): raise SystemExit("REFUSED: url missing")
    L["order"] = np.arange(len(L)); L.to_csv(sys.argv[3], index=False)
    print(L.groupby(["arm", "maker"]).size().to_dict(), "| arm A uncropped:", int(((L.arm == "A") & (L.resampled_T <= 200)).sum()),
          "| arm A ratio 0.5:", int(((L.arm == "A") & ((L.ratio - 0.5).abs() < 0.02)).sum()))
    print("arm B thickness by maker:", L[L.arm == "B"].groupby("maker").thickness.median().to_dict())


if __name__ == "__main__":
    main()
