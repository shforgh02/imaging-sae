"""Lung L2: the recorded-findings comparator F (docs/LUNG_L2_PROTOCOL.md section 4).
F = nlst_l0.logit_model() (standardise + logistic, C = 0.3) on the recorded findings plus age, sex and smoking (nlst_l0.features_for),
fitted on Sybil's TRAIN participants only: F1 for y1 on all screens, F6 for y6 on baseline screens. Used unchanged on dev (S4) and
test (S6). The fitted parameters are written to results/l2_form_params.json (hashed) so S6 uses exactly this model.
usage: python l2_form.py <tables dir> <split pickle> <out_dir>      (writes params + dev predictions; never predicts test here)
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, r"D:\Shayan\imgsae\exploratory\lung_l0")
import nlst_l0 as L  # noqa: E402


def fit(b):
    X, read, demo = b["X"], b["read"], b["demo"]
    out = {}
    for name, y, base in (("F1", "y1", False), ("F6", "y6", True)):
        r, d = L.features_for(read, demo, base)
        tr = X[(X.grp == "train") & X[y].notna() & ((X.study_yr == 0) | (not base))]
        mdl = L.logit_model().fit(tr[r + d], tr[y])
        sc, lr = mdl.named_steps["standardscaler"], mdl.named_steps["logisticregression"]
        out[name] = dict(outcome=y, baseline_only=base, features=r + d, mean=sc.mean_.tolist(), scale=sc.scale_.tolist(),
                         coef=lr.coef_[0].tolist(), intercept=float(lr.intercept_[0]), n_fit=int(len(tr)), n_fit_pos=int(tr[y].sum()))
    return out


def predict_logit(params, X):
    """F logits for the rows of X (exam table from nlst_l0.build); identical to the sklearn pipeline's decision_function."""
    cols = params["features"]
    Z = (X[cols].to_numpy(float) - np.array(params["mean"])) / np.array(params["scale"])
    return Z @ np.array(params["coef"]) + params["intercept"]


def main():
    tables, split_p, out_d = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    b = L.build(tables, split_p)
    P = fit(b)
    p = out_d / "l2_form_params.json"
    p.write_text(json.dumps(P, indent=1))
    X = b["X"]
    dev = X[X.grp == "dev"][["pid", "study_yr"]].copy()
    D = X[X.grp == "dev"]
    dev["F1"] = predict_logit(P["F1"], D)
    dev["F6"] = predict_logit(P["F6"], D)
    # self-check against sklearn on the training rows (same pipeline)
    tr = X[(X.grp == "train") & X.y1.notna()]
    mdl = L.logit_model().fit(tr[P["F1"]["features"]], tr.y1)
    chk = float(np.abs(mdl.decision_function(D[P["F1"]["features"]]) - dev.F1.to_numpy()).max())
    dev.to_csv(out_d / "l2_form_dev.csv", index=False)
    info = dict(params_sha256=hashlib.sha256(p.read_bytes()).hexdigest(), n_dev=int(len(dev)), max_abs_vs_sklearn=chk,
                n_fit=dict(F1=P["F1"]["n_fit"], F6=P["F6"]["n_fit"]), n_fit_pos=dict(F1=P["F1"]["n_fit_pos"], F6=P["F6"]["n_fit_pos"]),
                n_features=dict(F1=len(P["F1"]["features"]), F6=len(P["F6"]["features"])))
    (out_d / "l2_form_info.json").write_text(json.dumps(info, indent=1))
    print(json.dumps(info, indent=1))


if __name__ == "__main__":
    main()
