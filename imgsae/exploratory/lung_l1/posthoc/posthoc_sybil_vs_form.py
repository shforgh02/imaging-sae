"""Exploratory, post hoc (not part of the frozen L1 analysis): how much of Sybil is on the radiologist's form, and where do the two disagree."""
import sys
import numpy as np, pandas as pd
from scipy.special import logit
from sklearn.metrics import roc_auc_score
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GroupKFold, cross_val_predict
sys.path.insert(0, r"D:\Shayan\imgsae\exploratory\lung_l0")
import nlst_l0 as L

T = r"D:\Shayan\imgsae_data\nlst_public\tables"
S = r"D:\Shayan\imgsae_data\nlst_public\Shetty_et_al(Google)_data_splits.p"
b = L.build(T, S)
X, read, demo = b["X"], b["read"], b["demo"]
sc = pd.read_csv(r"D:\Shayan\imgsae\exploratory\lung_l1\results\scores.csv").rename(columns={f"y{k}": f"sybil_y{k}" for k in range(1, 7)})
sc["pid"] = sc.pid.astype(int)
M = X[X.grp == "test"].merge(sc, on=["pid", "study_yr"], how="inner")
r, d = L.features_for(read, demo, False)
tr = X[X.grp.isin(["train", "dev"]) & X.y1.notna()]
mdl = L.logit_model().fit(tr[r + d], tr.y1)
M["rf"] = mdl.predict_proba(M[r + d])[:, 1]
M["ls"] = logit(M.sybil_y1.clip(1e-6, 1 - 1e-6))

# 1. how much of Sybil's 1-year score is predictable from the recorded findings (cross-validated R2, grouped by participant)
for name, cols in (("recorded findings + age/sex/smoking", r + d), ("age/sex/smoking only", d)):
    pred = cross_val_predict(make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 12))), M[cols], M.ls, groups=M.pid, cv=GroupKFold(5))
    print(f"R2 of Sybil logit from {name}: {1 - ((M.ls - pred) ** 2).sum() / ((M.ls - M.ls.mean()) ** 2).sum():.3f}")
print("Spearman Sybil vs recorded-findings model:", round(M[["sybil_y1", "rf"]].corr(method="spearman").iloc[0, 1], 3))

K = M[M.y1.notna()].copy()
K["pc"] = K.positive_call
def auc(D, c): return round(roc_auc_score(D.y1, D[c]), 3) if D.y1.nunique() == 2 else None
for nm, D in (("all scored screens", K), ("radiologist-positive screens", K[K.pc == 1]), ("radiologist-negative screens", K[K.pc == 0]),
              ("baseline, radiologist-positive", K[(K.pc == 1) & (K.study_yr == 0)])):
    print(f"{nm}: n {len(D)}, cancers {int(D.y1.sum())}, Sybil {auc(D, 'sybil_y1')}, recorded findings {auc(D, 'rf')}")

# 2. errors at matched 90% specificity (threshold on the scored negatives)
for c in ("sybil_y1", "rf"):
    K[c + "_hi"] = K[c] >= np.quantile(K.loc[K.y1 == 0, c], 0.90)
pos, neg = K[K.y1 == 1], K[K.y1 == 0]
print("cancers within 1y:", len(pos), "| caught by both", int((pos.sybil_y1_hi & pos.rf_hi).sum()), "| Sybil only", int((pos.sybil_y1_hi & ~pos.rf_hi).sum()),
      "| findings only", int((~pos.sybil_y1_hi & pos.rf_hi).sum()), "| neither", int((~pos.sybil_y1_hi & ~pos.rf_hi).sum()))
print("non-cancers:", len(neg), "| flagged by both", int((neg.sybil_y1_hi & neg.rf_hi).sum()), "| Sybil only", int((neg.sybil_y1_hi & ~neg.rf_hi).sum()),
      "| findings only", int((~neg.sybil_y1_hi & neg.rf_hi).sum()))
# 3. 6-year, baseline: same error table
B = M[(M.study_yr == 0) & M.y6.notna()].copy()
rb, db = L.features_for(read, demo, True)
trb = X[X.grp.isin(["train", "dev"]) & X.y6.notna() & (X.study_yr == 0)]
B["rf6"] = L.logit_model().fit(trb[rb + db], trb.y6).predict_proba(B[rb + db])[:, 1]
for c in ("sybil_y6", "rf6"):
    B[c + "_hi"] = B[c] >= np.quantile(B.loc[B.y6 == 0, c], 0.90)
p6 = B[B.y6 == 1]
print("6y cancers (baseline):", len(p6), "| both", int((p6.sybil_y6_hi & p6.rf6_hi).sum()), "| Sybil only", int((p6.sybil_y6_hi & ~p6.rf6_hi).sum()),
      "| findings only", int((~p6.sybil_y6_hi & p6.rf6_hi).sum()), "| neither", int((~p6.sybil_y6_hi & ~p6.rf6_hi).sum()))

# 4. nonlinear fit, and stability of the score in the same participant one year apart
from sklearn.ensemble import HistGradientBoostingRegressor
pred = cross_val_predict(HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05), M[r + d], M.ls, groups=M.pid, cv=GroupKFold(5))
print("nonlinear R2 (boosting) of Sybil logit from recorded findings:", round(1 - ((M.ls - pred) ** 2).sum() / ((M.ls - M.ls.mean()) ** 2).sum(), 3))
W = M.pivot_table(index="pid", columns="study_yr", values="ls")
print("Sybil logit, same participant T0 vs T1: r =", round(W[[0, 1]].dropna().corr().iloc[0, 1], 3), "n", len(W[[0, 1]].dropna()))
R = M.assign(lr=np.log(M.rf / (1 - M.rf))).pivot_table(index="pid", columns="study_yr", values="lr")
print("recorded-findings logit, same participant T0 vs T1: r =", round(R[[0, 1]].dropna().corr().iloc[0, 1], 3))
