"""Lung L1 analysis, frozen before any Sybil score existed (docs/LUNG_L1_PROTOCOL.md section 6).

Sybil against the NLST radiologists' recorded findings, on Sybil's own test participants, paired on the same exams.
The comparator is the L0 code (../lung_l0/nlst_l0.py, `build`, `features_for`, `logit_model`), fitted on Sybil's train + dev
participants only. Sybil's scores are used as published (ensemble, calibrated); nothing about Sybil is fitted here except the
two-variable combination, which is cross-fitted on the test participants.

Usage (project venv, from this folder):
  python l1_analysis.py <NLST tables dir> <Sybil split pickle> <scores.csv> [out_json]

scores.csv columns (one row per scored series):
  series_uid, pid, study_yr (0, 1 or 2), y1, y2, y3, y4, y5, y6   (Sybil's cumulative risks for years 1 to 6)
"""
import json
import pathlib
import sys

import numpy as np
import pandas as pd
from scipy.stats import chi2
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lung_l0"))
import nlst_l0 as L0  # noqa: E402

N_BOOT = 2000
SEED = 0
MARGIN_BEATS = 0.03      # Sybil minus recorded findings
MARGIN_ADDS = 0.02       # (recorded findings + Sybil) minus recorded findings
PRIMARY_ALPHA = 0.025    # two primary analyses -> 97.5% intervals
SANITY = {"A1": (0.88, 0.97), "A3": (0.86, 0.96)}   # Sybil's own AUROC must land near its published 0.93 / 0.92


def logit(p):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def boot(pid, fn, rng, alpha):
    """Participant-cluster bootstrap of fn(index array) -> float."""
    pid = np.asarray(pid)
    upid = np.unique(pid)
    rows = {p: np.where(pid == p)[0] for p in upid}
    draws = []
    for _ in range(N_BOOT):
        take = np.concatenate([rows[p] for p in rng.choice(upid, len(upid))])
        v = fn(take)
        if v is not None:
            draws.append(v)
    lo, hi = np.percentile(draws, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return round(float(lo), 4), round(float(hi), 4)


def crossfit(y, cols, pid):
    """Cross-fitted probability of a plain logistic regression on the given columns (5 folds; one participant stays in one fold)."""
    y = np.asarray(y)
    Z = np.column_stack(cols)
    upid = np.unique(pid)
    ypid = np.array([y[pid == p].max() for p in upid])
    out = np.zeros(len(y))
    for tr, te in StratifiedKFold(5, shuffle=True, random_state=SEED).split(upid, ypid):
        mtr, mte = np.isin(pid, upid[tr]), np.isin(pid, upid[te])
        out[mte] = LogisticRegression(C=1e6, max_iter=5000).fit(Z[mtr], y[mtr]).predict_proba(Z[mte])[:, 1]
    return out


def loglik(y, cols):
    Z = np.column_stack(cols)
    p = np.clip(LogisticRegression(C=1e6, max_iter=5000).fit(Z, y).predict_proba(Z)[:, 1], 1e-12, 1 - 1e-12)
    return float(np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))


def compare(D, lab, sybil_col, read_p, rng, alpha):
    """Paired comparison on the rows of D (all have a Sybil score and a known label)."""
    y, pid = D[lab].to_numpy().astype(int), D.pid.to_numpy()
    s, r = D[sybil_col].to_numpy(float), np.asarray(read_p, float)
    ls, lr = logit(s), logit(r)
    both_cf, read_cf, syb_cf = crossfit(y, [lr, ls], pid), crossfit(y, [lr], pid), crossfit(y, [ls], pid)

    def auc(v):
        return lambda take: roc_auc_score(y[take], v[take]) if y[take].min() != y[take].max() else None

    def dauc(a, b_):
        def fn(take):
            if y[take].min() == y[take].max():
                return None
            return roc_auc_score(y[take], a[take]) - roc_auc_score(y[take], b_[take])
        return fn

    def est(a, b_=None):
        point = roc_auc_score(y, a) - (roc_auc_score(y, b_) if b_ is not None else 0.0)
        lo, hi = boot(pid, dauc(a, b_) if b_ is not None else auc(a), rng, alpha)
        return [round(float(point), 4), lo, hi]

    lr_stat = 2 * (loglik(y, [lr, ls]) - loglik(y, [lr]))
    lr_rev = 2 * (loglik(y, [lr, ls]) - loglik(y, [ls]))
    return {
        "n_exams": int(len(y)), "n_positive": int(y.sum()), "n_participants": int(len(np.unique(pid))), "interval": f"{100 * (1 - alpha):.1f}%",
        "auroc_sybil": est(s), "auroc_recorded_findings": est(r),
        "delta_sybil_minus_recorded": est(s, r),
        "auroc_combined_crossfit": est(both_cf),
        "delta_combined_minus_recorded": est(both_cf, read_cf),
        "delta_combined_minus_sybil": est(both_cf, syb_cf),
        "lr_test_sybil_given_recorded": {"chi2_1df": round(lr_stat, 2), "p": float(chi2.sf(max(lr_stat, 0), 1))},
        "lr_test_recorded_given_sybil": {"chi2_1df": round(lr_rev, 2), "p": float(chi2.sf(max(lr_rev, 0), 1))},
    }


def main():
    tables, split_path, scores_path = sys.argv[1], sys.argv[2], sys.argv[3]
    out = pathlib.Path(sys.argv[4]) if len(sys.argv) > 4 else pathlib.Path(__file__).parent / "results" / "l1_results.json"
    rng = np.random.default_rng(SEED)
    b = L0.build(tables, split_path)
    X, read, demo, split = b["X"], b["read"], b["demo"], b["split"]
    res = {"scores_file": str(scores_path)}

    sc = pd.read_csv(scores_path).rename(columns={f"y{k}": f"sybil_y{k}" for k in range(1, 7)})   # keep apart from the label columns y1, y2, y6
    sc["pid"] = sc.pid.astype(int)
    sc["study_yr"] = sc.study_yr.astype(int)
    res["scores"] = {"rows": len(sc), "participants": int(sc.pid.nunique()), "by_study_yr": sc.study_yr.value_counts().sort_index().to_dict(),
                     "duplicate_pid_year_rows": int(sc.duplicated(["pid", "study_yr"]).sum())}
    if sc.duplicated(["pid", "study_yr"]).any():
        raise SystemExit("STOP: more than one scored series for a participant and study year; fix the manifest first.")

    # ---- checks of the mapping series -> (participant, study year) ----
    c1 = {uid: int(e["cancer_in_1"]) for v in split.values() if str(v["split"]) == "test" for uid, e in v["exams"].items()}
    not_test = int((~sc.pid.map(b["pid2split"]).eq("test")).sum())
    T = X[X.grp == "test"].merge(sc, on=["pid", "study_yr"], how="inner")
    chk = T[T.y1.notna()].copy()
    chk["split_c1"] = chk.series_uid.map(c1)
    agree = float((chk.split_c1 == chk.y1).mean()) if len(chk) else float("nan")   # split file's cancer_in_1 against the table-derived label
    res["mapping_checks"] = {"scored_rows_not_in_test_split": not_test, "test_exams_in_table": int((X.grp == "test").sum()),
                             "test_exams_with_score": len(T), "scored_rows_without_table_exam": len(sc) - len(T),
                             "label_agreement_with_split_file": round(agree, 4)}
    if not (agree >= 0.99) or not_test > 0:
        res["verdict"] = "STOP: series-to-exam mapping failed its check; scores not interpreted."
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1)); raise SystemExit(2)

    def read_scores(lab, baseline_only, rows):
        """Recorded-findings model fitted on Sybil's train + dev participants, scored on the given test rows."""
        D = X[X[lab].notna() & ((X.study_yr == 0) | (not baseline_only))]
        r, d = L0.features_for(read, demo, baseline_only)
        tr = D[D.grp.isin(["train", "dev"])]
        return L0.logit_model().fit(tr[r + d], tr[lab]).predict_proba(rows[r + d])[:, 1]

    analyses = {}
    for key, lab, sybil_col, baseline_only, primary, title in (
            ("A1", "y1", "sybil_y1", True, True, "cancer within 1 year, baseline scans"),
            ("A2", "y6", "sybil_y6", True, True, "cancer within 6 years, baseline scans"),
            ("A3", "y1", "sybil_y1", False, False, "cancer within 1 year, all screens (recorded findings may use earlier scans)"),
            ("A4", "y2", "sybil_y2", True, False, "cancer within 2 years, baseline scans")):
        D = T[T[lab].notna() & ((T.study_yr == 0) | (not baseline_only))].copy()
        if D[lab].sum() < 10:
            analyses[key] = {"title": title, "skipped": "fewer than 10 positives with a score"}
            continue
        a = compare(D, lab, sybil_col, read_scores(lab, baseline_only, D), rng, PRIMARY_ALPHA if primary else 0.05)
        a.update(title=title, primary=primary)
        analyses[key] = a

    # A5: negative baseline screens, cancer 1 to 6 years later
    D = T[(T.positive_call == 0) & (T.study_yr == 0)].copy()
    D["late"] = np.where(D.dt.notna() & (D.dt > L0.YEAR) & (D.dt <= 6 * L0.YEAR), 1.0, np.where(D.dt.isna() & (D.fu >= 6 * L0.YEAR), 0.0, np.nan))
    D = D[D.late.notna()]
    F = X[(X.positive_call == 0) & (X.study_yr == 0) & X.grp.isin(["train", "dev"])].copy()
    F["late"] = np.where(F.dt.notna() & (F.dt > L0.YEAR) & (F.dt <= 6 * L0.YEAR), 1.0, np.where(F.dt.isna() & (F.fu >= 6 * L0.YEAR), 0.0, np.nan))
    F = F[F.late.notna()]
    r, _ = L0.features_for(read, demo, True)
    cols = r + ["age_scan", "gender", "cigsmok"]
    if D.late.sum() >= 10:
        a = compare(D, "late", "sybil_y6", L0.logit_model().fit(F[cols], F.late).predict_proba(D[cols])[:, 1], rng, 0.05)
        a.update(title="negative baseline screen, cancer 1 to 6 years later", primary=False)
        analyses["A5"] = a
    res["analyses"] = analyses

    # ---- verdict, by the rules fixed in the protocol ----
    sanity = {k: (SANITY[k][0] <= analyses[k]["auroc_sybil"][0] <= SANITY[k][1]) for k in SANITY if "auroc_sybil" in analyses.get(k, {})}
    res["sanity_sybil_reproduces_published"] = sanity
    if not sanity or not all(sanity.values()):
        res["verdict"] = "PIPELINE SUSPECT: Sybil's own AUROC is outside the range around its published value; do not interpret."
    else:
        prim = [analyses[k] for k in ("A1", "A2") if "delta_sybil_minus_recorded" in analyses.get(k, {})]
        beats = any(a["delta_sybil_minus_recorded"][0] >= MARGIN_BEATS and a["delta_sybil_minus_recorded"][1] > 0 for a in prim)
        adds = any(a["delta_combined_minus_recorded"][0] >= MARGIN_ADDS and a["delta_combined_minus_recorded"][1] > 0 for a in prim)
        res["verdict"] = ("Sybil BEATS the recorded findings (a gap over the doctor exists)." if beats else
                          "Sybil ADDS to the recorded findings (complementary information), without beating them alone." if adds else
                          "No evidence that Sybil carries information beyond the recorded findings, at the precision of this test set.")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
