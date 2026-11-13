"""Free counts for the Sybil audit plan: cancers and false positives per split."""
import sys, json
import numpy as np, pandas as pd
sys.path.insert(0, r"D:\Shayan\imgsae\exploratory\lung_l0")
import nlst_l0 as L

T = r"D:\Shayan\imgsae_data\nlst_public\tables"
S = r"D:\Shayan\imgsae_data\nlst_public\Shetty_et_al(Google)_data_splits.p"
b = L.build(T, S)
ex, prsn = b["ex"], b["prsn"]
print("groups:", ex.grp.value_counts().to_dict())
out = {}
for g, d in ex.groupby("grp"):
    r = {"participants": int(d.pid.nunique()), "exams": int(len(d))}
    r["participants_with_cancer_after_a_scan"] = int(d[d.candx_days.notna()].pid.nunique())
    for y in (1, 2, 6):
        r[f"exams_y{y}_pos"] = int((d[f"y{y}"] == 1).sum())
        base = d[d.study_yr == 0]
        r[f"baseline_y{y}_pos"] = int((base[f"y{y}"] == 1).sum())
    # false positives: positive screen call, no cancer within 1 year (known)
    r["positive_calls"] = int(d.positive_call.sum())
    r["positive_calls_no_cancer_1y"] = int(((d.positive_call == 1) & (d.y1 == 0)).sum())
    r["negative_calls_cancer_1y"] = int(((d.positive_call == 0) & (d.y1 == 1)).sum())
    r["negative_baseline_cancer_1to6y"] = int(((d.study_yr == 0) & (d.positive_call == 0) & (d.y6 == 1) & ~(d.y1 == 1)).sum())
    out[g] = r
print(json.dumps(out, indent=1))

# Sybil's own errors on the scored test exams
sc = pd.read_csv(r"D:\Shayan\imgsae\exploratory\lung_l1\results\scores.csv")
sc["pid"] = sc.pid.astype(ex.pid.dtype)
m = ex.merge(sc, on=["pid", "study_yr"], how="inner", suffixes=("", "_s"))
print("scored exams merged:", len(m))
ycol = [c for c in m.columns if c in ("y1_s",)]
print("cols:", [c for c in m.columns if c.startswith("y")])
s1 = m["y1_s"]
k = m.y1.notna()
thr = np.quantile(s1[k & (m.y1 == 0)], 0.90)   # 90% specificity threshold
pos = k & (m.y1 == 1)
print("1y cancers scored:", int(pos.sum()), "| missed by Sybil at 90% spec:", int((pos & (s1 < thr)).sum()),
      "| missed by radiologist call:", int((pos & (m.positive_call == 0)).sum()),
      "| missed by both:", int((pos & (s1 < thr) & (m.positive_call == 0)).sum()))
neg = k & (m.y1 == 0)
print("1y negatives scored:", int(neg.sum()), "| Sybil FP at 90% spec:", int((neg & (s1 >= thr)).sum()),
      "| radiologist positive calls (FP):", int((neg & (m.positive_call == 1)).sum()),
      "| radiologist FP that Sybil scores below thr:", int((neg & (m.positive_call == 1) & (s1 < thr)).sum()))
# among radiologist-positive screens: can Sybil separate cancer from benign?
from sklearn.metrics import roc_auc_score
pc = k & (m.positive_call == 1)
print("within positive calls: n", int(pc.sum()), "cancers", int((pc & (m.y1 == 1)).sum()),
      "Sybil AUROC", round(roc_auc_score(m.y1[pc], s1[pc]), 3))
nc = k & (m.positive_call == 0)
print("within negative calls: n", int(nc.sum()), "cancers", int((nc & (m.y1 == 1)).sum()),
      "Sybil AUROC", round(roc_auc_score(m.y1[nc], s1[nc]), 3) if (nc & (m.y1 == 1)).sum() > 0 else None)
# histology/stage availability
canc = pd.read_csv([__import__("glob").glob(T + r"\*canc*.csv")][0][0], low_memory=False)
print("canc rows", len(canc), "| de_type filled", int(canc.de_type.notna().sum()), "| lc_topog filled", int(canc.lc_topog.notna().sum()),
      "| stage filled", int(canc.de_stag.notna().sum()))
print("lc_morph top:", canc.lc_morph.value_counts().head(6).to_dict())
