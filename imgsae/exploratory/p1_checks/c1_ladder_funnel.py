"""Exploratory check 1 (post hoc, not part of the pre-written decision): where do features drop out of the validity ladder?
Reads data/p1/fit/<method>_rep<j>_<half>.csv (written by scripts/p1_fit.py) and reports, per method, the funnel
V0 -> non-chimeric -> concept != other -> sel >= .7 -> t >= .7 -> r_pert >= .7 -> v >= .7, plus medians of t, sel, r_pert.
Read-only on the main results. Writes results/c1_ladder_funnel.csv.
usage: ..\..\.venv\Scripts\python c1_ladder_funnel.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]; FIT = ROOT / "data/p1/fit"; OUT = HERE / "results"; OUT.mkdir(exist_ok=True)


def main():
    rows = []
    for f in sorted(FIT.glob("*_rep*_*.csv")):
        meth, rep, half = f.stem.rsplit("_", 2); T = pd.read_csv(f)
        v0 = T["v0"].astype(bool); nc = v0 & ~T["chimeric"].astype(bool); co = nc & (T["concept"] != "other")
        s7 = co & (T["sel"] >= .7); t7 = s7 & (T["t"] >= .7); p7 = t7 & (T["r_pert"].fillna(-1) >= .7)
        rows.append(dict(method=meth, rep=rep, half=half, n=len(T), v0=v0.sum(), nonchim=nc.sum(), concept=co.sum(), sel07=s7.sum(), t07=t7.sum(),
                         rpert07=p7.sum(), v07=(T["v"].fillna(0) >= .7).sum(),
                         med_t_v0=T.loc[v0, "t"].median(), med_sel_co=T.loc[co, "sel"].median(), med_rpert_co=T.loc[co, "r_pert"].median(),
                         share_other_v0=float((T.loc[v0, "concept"] == "other").mean()) if v0.any() else np.nan,
                         share_chim_v0=float(T.loc[v0, "chimeric"].astype(bool).mean()) if v0.any() else np.nan,
                         sel07_any=int(((T["sel"] >= .7) & v0).sum()), t07_any=int(((T["t"] >= .7) & v0).sum()), rpert07_any=int(((T["r_pert"] >= .7) & v0).sum())))
    D = pd.DataFrame(rows); D.to_csv(OUT / "c1_ladder_funnel.csv", index=False)
    agg = D.groupby("method").mean(numeric_only=True).round(3)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30); print(agg.to_string()); print("DONE")


if __name__ == "__main__":
    main()
