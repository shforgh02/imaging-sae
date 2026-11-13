"""Lung L0 (no images, no compute cost): the public NLST tables joined with Sybil's published split.

Two questions:
  1. Which public NLST participants did Sybil never use, and how many cancers do they have?
  2. On Sybil's own test participants, how well do the trial radiologists' recorded findings
     predict lung cancer? (The comparator that a "beyond the doctor" study needs.)

Usage (from this folder, project venv):
  python nlst_l0.py <dir with the unpacked NLST csv tables> <Sybil split pickle> [out_json]

Inputs (both public, kept out of git under imgsae_data/nlst_public/):
  - NLST clinical package for IDC, `nlst780.idc.delivery.052821.zip` (tables prsn, screen, ctab, ctabc, canc);
  - `files/Shetty_et_al(Google)_data_splits.p`, branch `train` of github.com/reginabarzilaygroup/Sybil.
The pickle is read with a restricted unpickler (only two numpy constructors are allowed).

`build()` is also imported by ../lung_l1/l1_analysis.py, so the comparator is the same code in both steps.
"""
import json
import pathlib
import pickle
import sys
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
N_BOOT = 1000
YEAR = 365.25
PRIOR_PREFIXES = ("gw", "pre", "att", "iso", "res5", "res6")   # need an earlier scan; dropped for baseline scans
GROUPS = ("train", "dev", "test", "unseen")


class SafeUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if (module, name) == ("numpy.core.multiarray", "scalar"):
            return np._core.multiarray.scalar
        if (module, name) == ("numpy", "dtype"):
            return np.dtype
        raise pickle.UnpicklingError(f"blocked {module}.{name}")


def num(s):
    return pd.to_numeric(s, errors="coerce")


def logit_model():
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.3, max_iter=2000))


def boost_model():
    return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=300, l2_regularization=1.0, random_state=0)


def auc_ci(y, s, pid, rng, n_boot=N_BOOT):
    """AUROC with a participant-cluster bootstrap interval."""
    y, s, pid = np.asarray(y), np.asarray(s), np.asarray(pid)
    upid = np.unique(pid)
    rows = {p: np.where(pid == p)[0] for p in upid}
    draws = []
    for _ in range(n_boot):
        take = np.concatenate([rows[p] for p in rng.choice(upid, len(upid))])
        if y[take].min() != y[take].max():
            draws.append(roc_auc_score(y[take], s[take]))
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return [round(float(roc_auc_score(y, s)), 3), round(float(lo), 3), round(float(hi), 3)]


def features_for(read, demo, baseline_only):
    """Feature lists of the recorded-findings model. Baseline scans cannot use comparison with an earlier scan."""
    r = [c for c in read if not (baseline_only and c.startswith(PRIOR_PREFIXES))]
    d = [c for c in demo if not (baseline_only and c == "study_yr")]
    return r, d


def build(tables_dir, split_path):
    """Exam table of the CT arm: labels, Sybil split group and the radiologists' recorded findings per screening exam."""
    tables_dir = pathlib.Path(tables_dir)

    def table(key):
        return pd.read_csv(next(tables_dir.glob(f"*{key}*.csv")), low_memory=False)

    split = SafeUnpickler(open(split_path, "rb")).load()
    pid2split = {int(k): str(v["split"]) for k, v in split.items()}

    prsn, ctab, ctabc = table("prsn"), table("ctab_idc"), table("ctabc")
    ct_pids = set(num(table("screen")["pid"]).dropna().astype(int))      # spiral-CT arm
    prsn["grp"] = prsn["pid"].map(pid2split)
    prsn.loc[prsn.grp.isna() & prsn.pid.isin(ct_pids), "grp"] = "unseen"
    prsn = prsn[prsn.grp.notna()].copy()                                 # drops the chest X-ray arm
    for c in ["candx_days", "canc_free_days", "age"] + [f"{v}{t}" for v in ("scr_days", "scr_res", "scr_iso") for t in range(3)]:
        prsn[c] = num(prsn[c])

    # ---- one row per screening exam ----
    keep = ["pid", "grp", "age", "gender", "cigsmok", "candx_days", "canc_free_days"]
    ex = pd.concat([prsn[keep + [f"scr_res{t}", f"scr_iso{t}", f"scr_days{t}"]]
                    .set_axis(keep + ["scr_res", "scr_iso", "scr_days"], axis=1).assign(study_yr=t) for t in range(3)], ignore_index=True)
    ex = ex[ex.scr_res.isin([1, 2, 3, 4, 5, 6]) & ex.scr_days.notna()].copy()
    ex["dt"] = ex.candx_days - ex.scr_days                               # days from this scan to diagnosis
    ex = ex[~(ex.dt < 0)].copy()
    ex["fu"] = np.where(ex.candx_days.notna(), ex.dt, ex.canc_free_days - ex.scr_days)
    ex["positive_call"] = ex.scr_res.isin([4, 5, 6]).astype(int)
    for y in (1, 2, 6):
        pos = ex.dt.notna() & (ex.dt <= YEAR * y)
        ex[f"y{y}"] = np.where(pos, 1.0, np.where(ex.fu >= YEAR * y, 0.0, np.nan))   # negatives need y cancer-free years

    # ---- the radiologists' recorded findings, per exam ----
    for c in ["sct_ab_desc", "sct_long_dia", "sct_perp_dia", "sct_margins", "sct_pre_att", "sct_epi_loc", "study_yr", "pid"]:
        ctab[c] = num(ctab[c])
    nod = ctab[ctab.sct_ab_desc == 51].copy()                            # non-calcified nodule or mass >= 4 mm
    nod["sct_long_dia"] = nod.sct_long_dia.fillna(4.0)
    nod = nod.sort_values("sct_long_dia", ascending=False)
    big = nod.groupby(["pid", "study_yr"]).first().reset_index()        # the largest nodule of the exam
    f = big[["pid", "study_yr"]].copy()
    f["max_dia"] = big.sct_long_dia
    f["perp_dia"] = big.sct_perp_dia.fillna(big.sct_long_dia)
    f["big_spic"] = (big.sct_margins == 1).astype(int)
    f["big_poor"] = (big.sct_margins == 3).astype(int)
    f["big_soft"] = (big.sct_pre_att == 1).astype(int)
    f["big_gg"] = (big.sct_pre_att == 2).astype(int)
    f["big_mixed"] = (big.sct_pre_att == 3).astype(int)
    f["big_upper"] = big.sct_epi_loc.isin([1, 4]).astype(int)
    agg = nod.groupby(["pid", "study_yr"]).agg(n_nod=("sct_long_dia", "size"), sum_dia=("sct_long_dia", "sum"),
                                                any_spic=("sct_margins", lambda s: int((s == 1).any()))).reset_index()
    other = ctab[ctab.sct_ab_desc.isin([52, 53, 54, 55, 56, 57, 58, 59, 61, 62, 63])]
    fl = pd.crosstab([other.pid, other.study_yr], other.sct_ab_desc).clip(upper=1)
    fl.columns = [f"ab{int(c)}" for c in fl.columns]
    for c in ["sct_ab_gwth", "sct_ab_attn", "sct_ab_preexist", "study_yr", "pid"]:
        ctabc[c] = num(ctabc[c])
    spec = {}
    for var, pre in (("sct_ab_gwth", "gw"), ("sct_ab_preexist", "pre"), ("sct_ab_attn", "att")):
        for k in sorted(ctabc[var].dropna().unique()):
            spec[f"{pre}{int(k)}"] = (var, lambda s, k=k: int((s == k).any()))
    cc = ctabc.groupby(["pid", "study_yr"]).agg(**spec).reset_index()

    X = ex.merge(f.merge(agg, on=["pid", "study_yr"]), on=["pid", "study_yr"], how="left") \
          .merge(fl.reset_index(), on=["pid", "study_yr"], how="left").merge(cc, on=["pid", "study_yr"], how="left")
    X["age_scan"] = X.age + X.study_yr
    X["log_dia"] = np.log1p(X.max_dia.fillna(0))
    for k in range(1, 7):
        X[f"res{k}"] = (X.scr_res == k).astype(int)
    X["iso_pos"] = (X.scr_iso == 4).astype(int)
    read = [c for c in X.columns if c in ("log_dia", "max_dia", "perp_dia", "big_spic", "big_poor", "big_soft", "big_gg", "big_mixed",
                                          "big_upper", "n_nod", "any_spic", "sum_dia", "iso_pos") or c.startswith(("ab", "gw", "pre", "att", "res"))]
    demo = ["age_scan", "gender", "cigsmok", "study_yr"]
    X[read] = X[read].fillna(0)
    X[demo] = X[demo].fillna(X[demo].median())
    return dict(split=split, pid2split=pid2split, ct_pids=ct_pids, prsn=prsn, ex=ex, X=X, read=read, demo=demo)


def main():
    tables, split_path = sys.argv[1], sys.argv[2]
    out = pathlib.Path(sys.argv[3]) if len(sys.argv) > 3 else pathlib.Path(__file__).parent / "results" / "l0_results.json"
    rng = np.random.default_rng(0)
    b = build(tables, split_path)
    split, pid2split, prsn, ex, X, read, demo = b["split"], b["pid2split"], b["prsn"], b["ex"], b["X"], b["read"], b["demo"]
    res = {}

    test_series = sum(len(v["exams"]) for v in split.values() if str(v["split"]) == "test")
    test_c1 = sum(int(e["cancer_in_1"]) for v in split.values() if str(v["split"]) == "test" for e in v["exams"].values())
    res["participants"] = {"ct_arm_in_public_table": len(b["ct_pids"]), "split_file": len(pid2split),
                           "split_pids_missing_from_table": len(set(pid2split) - set(b["ct_pids"])),
                           "by_group": prsn.grp.value_counts().to_dict()}
    res["first_cancer_by_screen_link"] = {g: prsn[prsn.grp == g].can_scr.value_counts().sort_index().to_dict() for g in GROUPS}

    def counts(d):
        return {"participants": int(d.pid.nunique()), "exams": len(d),
                "exams_cancer_within_1y": int((d.dt <= YEAR).sum()),
                "exams_cancer_1_to_2y": int(((d.dt > YEAR) & (d.dt <= 2 * YEAR)).sum()),
                "exams_cancer_2_to_6y": int(((d.dt > 2 * YEAR) & (d.dt <= 6 * YEAR)).sum()),
                "participants_with_later_cancer": int(d.loc[d.dt.notna(), "pid"].nunique())}

    res["counts_all_screens"] = {g: counts(ex[ex.grp == g]) for g in GROUPS}
    res["counts_negative_screens"] = {g: counts(ex[(ex.grp == g) & (ex.positive_call == 0)]) for g in GROUPS}
    res["label_check_vs_split_file"] = {"split_test_series": test_series, "split_test_cancer_in_1": test_c1,
                                        "derived_test_exams": int((ex.grp == "test").sum()),
                                        "derived_test_cancer_within_1y": int(ex.loc[ex.grp == "test", "y1"].sum())}

    # ---- AUROC on Sybil's test participants; every model is fitted on Sybil's train + dev participants only ----
    res["auroc_test"] = {}
    for y, baseline_only in ((1, False), (1, True), (2, True), (6, True)):
        D = X[X[f"y{y}"].notna() & ((X.study_yr == 0) | (not baseline_only))]
        r, d = features_for(read, demo, baseline_only)
        tr, te = D[D.grp.isin(["train", "dev"])], D[D.grp == "test"]
        lab = f"y{y}"
        o = {"n_exams": len(te), "n_positive": int(te[lab].sum()), "n_fit_exams": len(tr), "n_fit_positive": int(tr[lab].sum())}
        for name, cols, make in (("recorded findings + age, sex, smoking (logistic)", r + d, logit_model),
                                 ("recorded findings + age, sex, smoking (boosting)", r + d, boost_model),
                                 ("recorded findings only (logistic)", r, logit_model),
                                 ("age, sex, smoking only (logistic)", d, logit_model)):
            o[name] = auc_ci(te[lab], make().fit(tr[cols], tr[lab]).predict_proba(te[cols])[:, 1], te.pid, rng)
        o["largest nodule diameter alone (no fitting)"] = auc_ci(te[lab], te.max_dia.fillna(0), te.pid, rng)
        o["radiologist call, positive vs negative"] = auc_ci(te[lab], te.positive_call, te.pid, rng)
        res["auroc_test"][f"cancer within {y}y, {'baseline scans, single-scan findings' if baseline_only else 'all screens, with comparison to priors'}"] = o

    # ---- negative baseline screens: cancer 1 to 6 years later ----
    r, _ = features_for(read, demo, True)
    d = ["age_scan", "gender", "cigsmok"]
    D = X[(X.positive_call == 0) & (X.study_yr == 0)].copy()
    D["late"] = np.where(D.dt.notna() & (D.dt > YEAR) & (D.dt <= 6 * YEAR), 1.0, np.where(D.dt.isna() & (D.fu >= 6 * YEAR), 0.0, np.nan))
    D = D[D.late.notna()]
    tr, te = D[D.grp.isin(["train", "dev"])], D[D.grp == "test"]
    res["negative_baseline_screens_cancer_1_to_6y"] = {
        "n_exams": len(te), "n_positive": int(te.late.sum()),
        "recorded findings + age, sex, smoking (logistic)": auc_ci(te.late, logit_model().fit(tr[r + d], tr.late).predict_proba(te[r + d])[:, 1], te.pid, rng),
        "age, sex, smoking only (logistic)": auc_ci(te.late, logit_model().fit(tr[d], tr.late).predict_proba(te[d])[:, 1], te.pid, rng)}

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
