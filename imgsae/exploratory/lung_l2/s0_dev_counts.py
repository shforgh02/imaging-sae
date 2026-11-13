"""Lung L2, step S0 (free): dev-split counts for the power statements (NLST tables only; no Sybil score, no test data).
usage: python s0_dev_counts.py <tables dir> <split pickle> <out_json>
"""
import json
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"D:\Shayan\imgsae\exploratory\lung_l0")
import nlst_l0 as L  # noqa: E402

tables, split_p, out_p = sys.argv[1:4]
b = L.build(tables, split_p)
p = b["prsn"]
d = p[(p.grp == "dev") & p.candx_days.notna()].copy()
res = {"dev_participants_with_cancer": int(len(d))}
CEN = ["loclhil", "locrhil", "loclmsb", "locrmsb", "loccar", "locmed"]
UP, LOW, MID = ["loclup", "locrup"], ["locllow", "locrlow"], ["locrmid", "loclin"]
for c in CEN + UP + LOW + MID + ["locunk", "locoth"]:
    d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0)
res["location_flags_participants"] = {"central (hilum, main bronchus, carina, mediastinum)": int((d[CEN].sum(1) > 0).sum()),
                                      "upper lobe": int((d[UP].sum(1) > 0).sum()), "middle lobe or lingula": int((d[MID].sum(1) > 0).sum()),
                                      "lower lobe": int((d[LOW].sum(1) > 0).sum()), "unknown": int((d.locunk > 0).sum())}
canc = pd.read_csv(next(__import__("pathlib").Path(tables).glob("*canc*.csv")), low_memory=False)
c = canc[canc.pid.isin(d.pid)]
if "lc_order" in c:
    c = c[pd.to_numeric(c.lc_order, errors="coerce") == 1]
mor = pd.to_numeric(c.lc_morph, errors="coerce")
grp = np.select([mor.isin([8140, 8250, 8251, 8252, 8253, 8254, 8255, 8260, 8310, 8323, 8480, 8481, 8490, 8550]),
                 mor.isin([8052, 8070, 8071, 8072, 8073, 8074]), mor.isin([8041, 8042, 8043, 8044, 8045])],
                ["adenocarcinoma", "squamous", "small cell"], "other or not specified")
res["first_cancer_rows"] = int(len(c))
res["histology"] = pd.Series(grp).value_counts().to_dict()
st = pd.to_numeric(c.de_stag_7thed, errors="coerce")
res["stage_7th_codes"] = {str(int(k)): int(v) for k, v in st.value_counts().sort_index().items()}
ls = pd.to_numeric(c.lesionsize, errors="coerce")
res["lesionsize_mm"] = {"filled": int(ls.notna().sum()), "q25_50_75": np.nanpercentile(ls, [25, 50, 75]).round(0).tolist()}
e = b["ex"]
e = e[e.grp == "dev"]
res["exams"] = {}
for y in (1, 2, 6):
    res["exams"][f"y{y}"] = {"all_pos": int((e[f"y{y}"] == 1).sum()), "all_neg": int((e[f"y{y}"] == 0).sum()),
                             "baseline_pos": int(((e[f"y{y}"] == 1) & (e.study_yr == 0)).sum()),
                             "baseline_neg": int(((e[f"y{y}"] == 0) & (e.study_yr == 0)).sum())}
res["positive_call_no_cancer_1y"] = int(((e.positive_call == 1) & (e.y1 == 0)).sum())
res["positive_call_sensitivity_1y"] = float(((e.positive_call == 1) & (e.y1 == 1)).sum() / (e.y1 == 1).sum())
open(out_p, "w").write(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
