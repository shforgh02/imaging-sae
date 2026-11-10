"""M1 analysis on the laptop (docs/MRI_M0M1_PROTOCOL.md section 6): token probes, patient-weighted AUROC, patient-cluster bootstrap,
rule S, nested 5-fold cross-validation, the gate, and the descriptive outputs. Inputs: per-study feature files from the M1 encode
(imgsae/mri/results/prep_cache/m1_feats/<key>.npz, downloaded from the volume), split.json, QC exclusions, prep summary, marksheet.
Every fitted probe's held-out scores are cached (results/m1_cache/), so a killed run resumes. Writes results/m1_results.json, RESULTS_M1.md.
usage (OMP/MKL threads 4): D:\\Shayan\\imgsae\\.venv\\Scripts\\python.exe imgsae\\mri\\m1_analysis.py
"""
import hashlib
import io
import json
import os
import urllib.request
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent; RES = HERE / "results"; FEATS = RES / "prep_cache" / "m1_feats"; CACHE = RES / "m1_cache"
COMMIT = "ce4a4723d7c46d882a6cbaacb40ed6c4be86282f"; MARKSHEET_SHA = "23EAB23790886258440B4AF2842733332003F2C59F0A007B1E7B6B44572CF0AE"
CAND = ["mricore_A", "mricore_B", "sam_A", "sam_B", "profound"]; UNEXPOSED = ["mricore_A", "mricore_B", "sam_A", "sam_B"]
NULL = "untrained_B"; SENS = ["mricore_B_minmax", "mricore_B_noimagenet"]; B_BOOT = 2000
GATE_R, GATE_NULL, TIE_PF = 0.03, 0.05, 0.02


def log(*a): print(*a, flush=True)


# ------------------------------------------------------------------ data
def marksheet():
    url = f"https://raw.githubusercontent.com/DIAGNijmegen/picai_labels/{COMMIT}/clinical_information/marksheet.csv"
    raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "imgsae-m1"}), timeout=120).read()
    if hashlib.sha256(raw).hexdigest().upper() != MARKSHEET_SHA: raise SystemExit("STOP: marksheet SHA256 differs from the pinned one")
    M = pd.read_csv(io.BytesIO(raw), dtype=str)
    M["key"] = M.patient_id + "_" + M.study_id; return M.set_index("key")


def load_tokens(keys, M, src):
    """probe-sample tokens of every study: features per arm (float16), R, labels, study/patient ids, zone, flags."""
    arms = {a: [] for a in CAND + [NULL] + SENS + ["R"]}; rows = []
    for k in keys:
        z = np.load(FEATS / f"{k}.npz"); s = z["sample"]; les = z["lab_lesion"].astype(np.float32)[s] >= 0.5
        for a in CAND + [NULL]: arms[a].append(z[f"f_{a}"][s])
        for a in SENS: arms[a].append(z[f"s_{a}"])
        arms["R"].append(z["R"][s].astype(np.float16))
        pr = M.loc[k, "lesion_PIRADS"]; prmax = max([int(x) for x in str(pr).split(",") if x.strip().isdigit()] or [0])
        isup1 = "1" in [x.strip() for x in str(M.loc[k, "lesion_ISUP"]).split(",")]
        rows.append(pd.DataFrame(dict(key=k, patient=M.loc[k, "patient_id"], y=les.astype(int), zone=z["zone"][s], centre=M.loc[k, "center"],
                                      verified=pd.notna(M.loc[k, "histopath_type"]), clean=(not isup1) and prmax <= 2, source=src.get(k, ""))))
    T = pd.concat(rows, ignore_index=True)
    return T, {a: np.concatenate(v) for a, v in arms.items()}


def strata(M, keys):
    P = {}
    for k in keys:
        p = M.loc[k, "patient_id"]; c = M.loc[k, "center"]
        g = "csPCa" if M.loc[k, "case_csPCa"] == "YES" else ("verified_negative" if pd.notna(M.loc[k, "histopath_type"]) else "unverified_negative")
        old = P.get(p, (c, "unverified_negative"))[1]; rank = ["unverified_negative", "verified_negative", "csPCa"]
        P[p] = (c, g if rank.index(g) > rank.index(old) else old)
    return pd.DataFrame([dict(patient=p, stratum=f"{c}|{g}") for p, (c, g) in sorted(P.items())])


def folds(Pt, n=5, seed=0):
    from sklearn.model_selection import StratifiedKFold
    f = np.zeros(len(Pt), int)
    for i, (_, te) in enumerate(StratifiedKFold(n, shuffle=True, random_state=seed).split(Pt.patient, Pt.stratum)): f[te] = i
    return dict(zip(Pt.patient, f))


# ------------------------------------------------------------------ probe and AUROC
def fit_predict(X, y, tr, te, tag):
    """StandardScaler + LogisticRegression(C 1, balanced, max_iter 1000) on tr; scores on te. Cached by tag."""
    p = CACHE / f"{tag}.npy"
    if p.exists(): return np.load(p)
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    import time
    t0 = time.time(); Xtr = X[tr].astype(np.float32); sc = StandardScaler().fit(Xtr)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore"); m = LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000).fit(sc.transform(Xtr), y[tr])
    s = m.decision_function(sc.transform(X[te].astype(np.float32))).astype(np.float32); CACHE.mkdir(parents=True, exist_ok=True); np.save(p, s)
    log(f"  fit {tag}: {X.shape[1]}-d, {len(tr)} train, {m.n_iter_[0]} iter, {time.time() - t0:.0f} s"); return s


def fit_model(X, y, tr, tag):
    """the same probe as fit_predict, returning its parameters (scaler mean/scale, coef, intercept) for scoring all gland cells. Cached."""
    p = CACHE / f"model_{tag}.npz"
    if p.exists(): z = np.load(p); return z["mu"], z["sd"], z["coef"], float(z["b"])
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    Xtr = X[tr].astype(np.float32); sc = StandardScaler().fit(Xtr)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore"); m = LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000).fit(sc.transform(Xtr), y[tr])
    CACHE.mkdir(parents=True, exist_ok=True); np.savez(p, mu=sc.mean_, sd=sc.scale_, coef=m.coef_[0], b=m.intercept_[0])
    return sc.mean_, sc.scale_, m.coef_[0], float(m.intercept_[0])


def patient_level(arms, X, y, T, outer, M, keys):
    """descriptive: per study, the highest probe score over ALL its gland cells (gland occupancy >= 0.5), from the probe fitted on the
    other folds' sample tokens; AUROC vs csPCa in the biopsy cohort (verified, PI-RADS >= 3) and in all studies; arm vs R."""
    from sklearn.metrics import roc_auc_score
    pf = T.patient.map(outer).to_numpy(); score = {a: {} for a in arms}
    for f in range(5):
        tr = np.flatnonzero(pf != f); test_keys = sorted(set(T.key[pf == f]))
        par = {a: fit_model(X[a], y, tr, f"pl_f{f}_{a}") for a in arms}
        for k in test_keys:
            z = np.load(FEATS / f"{k}.npz"); g = z["lab_gland"].astype(np.float32) >= 0.5
            for a in arms:
                mu, sd, coef, b = par[a]; F = (z["R"] if a == "R" else z[f"f_{a}"])[g].astype(np.float32)
                score[a][k] = float(((F - mu) / sd @ coef + b).max()) if len(F) else float("nan")
    out = {}
    for name, sel in (("biopsy_cohort", lambda k: pd.notna(M.loc[k, "histopath_type"]) and max([int(x) for x in str(M.loc[k, "lesion_PIRADS"]).split(",") if x.strip().isdigit()] or [0]) >= 3),
                      ("all_studies", lambda k: True)):
        ks = [k for k in keys if sel(k) and all(np.isfinite(score[a].get(k, np.nan)) for a in arms)]
        yy = np.array([M.loc[k, "case_csPCa"] == "YES" for k in ks], int); pats = np.array([M.loc[k, "patient_id"] for k in ks])
        aucs = {a: float(roc_auc_score(yy, [score[a][k] for k in ks])) for a in arms}
        rng = np.random.default_rng(0); up, inv = np.unique(pats, return_inverse=True); ds = []
        for _ in range(B_BOOT):
            cnt = np.bincount(rng.integers(0, len(up), len(up)), minlength=len(up))[inv]; idx = np.repeat(np.arange(len(ks)), cnt)
            if len(np.unique(yy[idx])) < 2: continue
            ds.append(roc_auc_score(yy[idx], [score[arms[0]][ks[i]] for i in idx]) - roc_auc_score(yy[idx], [score[arms[1]][ks[i]] for i in idx]))
        out[name] = dict(n=len(ks), n_pos=int(yy.sum()), auroc=aucs, delta=aucs[arms[0]] - aucs[arms[1]], ci=[float(np.quantile(ds, .025)), float(np.quantile(ds, .975))])
    return out


def pw_weights(patient, y):
    """each patient counts equally within each class: weight = 1 / (tokens of that class for that patient)."""
    d = pd.DataFrame(dict(p=patient, y=y)); n = d.groupby(["p", "y"]).y.transform("size").to_numpy(); return 1.0 / n


def auc_w(y, s, w):
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(y, s, sample_weight=w))


class FastAUC:
    """weighted AUROC of a FIXED score vector under changing weights (the bootstrap only changes weights): scores ranked once,
    ties count one half (same definition as sklearn's roc_auc_score with sample_weight; checked in the tests)."""
    def __init__(self, y, s):
        u, inv = np.unique(s, return_inverse=True); y = np.asarray(y).astype(bool); self.n = len(u); self.ip, self.ineg, self.y = inv[y], inv[~y], y

    def __call__(self, w):
        wp = np.bincount(self.ip, weights=w[self.y], minlength=self.n); wn = np.bincount(self.ineg, weights=w[~self.y], minlength=self.n)
        return float((wp * (np.cumsum(wn) - 0.5 * wn)).sum() / (wp.sum() * wn.sum()))


def boot_delta(y, sa, sb, patient, B=B_BOOT, seed=0):
    """patient-cluster bootstrap of AUROC(a) - AUROC(b) with patient weights; returns (delta, lo, hi)."""
    if not (np.isfinite(sa).all() and np.isfinite(sb).all()): raise ValueError("boot_delta: scores contain nan")
    w = pw_weights(patient, y); d0 = auc_w(y, sa, w) - auc_w(y, sb, w); fa, fb = FastAUC(y, sa), FastAUC(y, sb); yb = np.asarray(y).astype(bool)
    pats, inv = np.unique(patient, return_inverse=True); rng = np.random.default_rng(seed); ds = []
    for _ in range(B):
        ww = w * np.bincount(rng.integers(0, len(pats), len(pats)), minlength=len(pats))[inv]
        if ww[yb].sum() == 0 or ww[~yb].sum() == 0: continue
        ds.append(fa(ww) - fb(ww))
    return d0, float(np.quantile(ds, .025)), float(np.quantile(ds, .975))


def cv_scores(X, y, T, fold_of, pats, tagp):
    """pooled held-out scores over the folds defined on `pats` (patients); tokens of other patients are ignored (nan)."""
    s = np.full(len(y), np.nan, np.float32); pf = T.patient.map(fold_of)
    for f in sorted(set(fold_of.values())):
        te = np.flatnonzero(T.patient.isin(pats) & (pf == f)); tr = np.flatnonzero(T.patient.isin(pats) & (pf != f))
        s[te] = fit_predict(X, y, tr, te, f"{tagp}_f{f}")
    return s


def rule_s(scores, y, patient, m):
    """rule S on held-out scores (mask m): U = best unexposed by delta vs R; ProFound only if delta(PF) - delta(U) >= 0.02 with lower CI > 0."""
    w = pw_weights(patient[m], y[m]); aR = auc_w(y[m], scores["R"][m], w)
    delta = {a: auc_w(y[m], scores[a][m], w) - aR for a in CAND if a in scores}; U = max(UNEXPOSED, key=lambda a: delta[a])
    out = dict(delta=delta, U=U, chosen=U)
    if "profound" in delta:
        d, lo, hi = boot_delta(y[m], scores["profound"][m], scores[U][m], patient[m])
        out["profound_vs_U"] = dict(delta=d, lo=lo, hi=hi)
        if d >= TIE_PF and lo > 0: out["chosen"] = "profound"
    return out


# ------------------------------------------------------------------ main
def main():
    M = marksheet(); split = json.load(open(HERE / "data" / "split.json")); exc = set(json.load(open(RES / "m0_qc_decisions.json"))["excluded"])
    keys = [k for k in sorted(split["dev_studies"]) if k not in exc]; missing = [k for k in keys if not (FEATS / f"{k}.npz").exists()]
    if missing: raise SystemExit(f"STOP: {len(missing)} feature files missing, e.g. {missing[:3]}")
    src = {k: v["source"] for k, v in json.load(open(RES / "m0_prep_summary.json"))["studies"].items()}
    T, X = load_tokens(keys, M, src); y = T.y.to_numpy(); patient = T.patient.to_numpy()
    log(f"tokens {len(T)} (lesion {int(y.sum())}, normal {int((y == 0).sum())}); studies {T.key.nunique()}; patients {T.patient.nunique()}")
    Pt = strata(M, keys); outer = folds(Pt); res = dict(n_tokens=len(T), n_lesion=int(y.sum()), n_studies=int(T.key.nunique()), n_patients=int(T.patient.nunique()))
    allp = set(Pt.patient)
    # ---- nested CV for the gate
    nested = dict(chosen=np.full(len(y), np.nan, np.float32), R=np.full(len(y), np.nan, np.float32), null=np.full(len(y), np.nan, np.float32))
    per_fold = []
    for f in range(5):
        trp = set(Pt.patient[[outer[p] != f for p in Pt.patient]]); tep = allp - trp
        Pin = Pt[Pt.patient.isin(trp)].reset_index(drop=True); inner = folds(Pin, seed=0)   # same rule as the outer folds (protocol 6)
        sc = {a: cv_scores(X[a], y, T, inner, trp, f"nest{f}_{a}") for a in CAND + ["R"]}
        m = T.patient.isin(trp).to_numpy(); rs = rule_s(sc, y, patient, m); per_fold.append(dict(fold=f, **rs)); log(f"outer fold {f}: rule S -> {rs['chosen']} {rs['delta']}")
        tr = np.flatnonzero(T.patient.isin(trp)); te = np.flatnonzero(T.patient.isin(tep))
        # outer fold f trains on exactly the tokens of full-CV fold f (same patients, same order): the fits are shared by tag
        nested["chosen"][te] = fit_predict(X[rs["chosen"]], y, tr, te, f"full_{rs['chosen']}_f{f}")
        nested["R"][te] = fit_predict(X["R"], y, tr, te, f"full_R_f{f}"); nested["null"][te] = fit_predict(X[NULL], y, tr, te, f"full_{NULL}_f{f}")
    res["nested_folds"] = per_fold; gate = {}
    for name, m in (("all", np.ones(len(y), bool)), ("verified", (y == 1) | T.verified.to_numpy())):
        dR = boot_delta(y[m], nested["chosen"][m], nested["R"][m], patient[m]); dN = boot_delta(y[m], nested["chosen"][m], nested["null"][m], patient[m])
        gate[name] = dict(delta_R=dR, delta_null=dN, pass_=bool(dR[0] >= GATE_R and dR[1] > 0 and dN[0] >= GATE_NULL))
    gate["PASS"] = bool(gate["all"]["pass_"] and gate["verified"]["pass_"]); res["gate"] = gate; log("GATE", json.dumps(gate))
    # ---- full dev 5-fold CV: every arm (descriptive) and the final selection for M2
    full = {a: cv_scores(X[a], y, T, outer, allp, f"full_{a}") for a in CAND + [NULL, "R"] + SENS}
    w = pw_weights(patient, y); res["auroc_all_arms"] = {a: auc_w(y, s, w) for a, s in full.items()}
    res["selection_for_M2"] = rule_s(full, y, patient, np.ones(len(y), bool))
    res["mricore_vs_sam"] = dict(A=boot_delta(y, full["mricore_A"], full["sam_A"], patient), B=boot_delta(y, full["mricore_B"], full["sam_B"], patient))
    res["mricore_input_sensitivity"] = {a: boot_delta(y, full[a], full["mricore_B"], patient, B=500) for a in SENS}   # side arm minus mricore_B
    pos = T[T.y == 1].drop_duplicates("key"); res["lesion_outline_source_by_centre"] = {c: g.source.value_counts().to_dict() for c, g in pos.groupby("centre")}
    arm = res["selection_for_M2"]["chosen"]; desc = {}
    for name, m in (("zone_PZ", (T.zone == 0).to_numpy()), ("zone_TZ", (T.zone == 1).to_numpy()),
                    ("clean_normal", (y == 1) | T.clean.to_numpy()), ("verified", (y == 1) | T.verified.to_numpy()),
                    *[(f"centre_{c}", (T.centre == c).to_numpy()) for c in ("PCNN", "RUMC", "ZGT")],
                    *[(f"RUMC_{s_}", ((T.centre == "RUMC") & ((T.source == s_) | (y == 0))).to_numpy()) for s_ in ("Pooch25", "resampled")]):
        if len(np.unique(y[m])) < 2: continue
        desc[name] = dict(n=int(m.sum()), delta_chosen_vs_R=boot_delta(y[m], full[arm][m], full["R"][m], patient[m], B=500))
    res["descriptive"] = desc
    # ---- leave-one-centre-out (chosen arm and R)
    loco = {}
    for c in ("PCNN", "RUMC", "ZGT"):
        tr = np.flatnonzero((T.centre != c).to_numpy()); te = np.flatnonzero((T.centre == c).to_numpy())
        sa = fit_predict(X[arm], y, tr, te, f"loco_{c}_{arm}"); sr = fit_predict(X["R"], y, tr, te, f"loco_{c}_R")
        loco[c] = dict(delta_chosen_vs_R=boot_delta(y[te], sa, sr, patient[te], B=500), lesion_outline_sources=res["lesion_outline_source_by_centre"].get(c, {}))
    res["loco"] = loco
    json.dump(res, open(RES / "m1_results.json", "w"), indent=1, default=float)          # saved before the slower patient-level step
    res["patient_level"] = patient_level([arm, "R"], X, y, T, outer, M, keys)
    json.dump(res, open(RES / "m1_results.json", "w"), indent=1, default=float); log(json.dumps(res["gate"], indent=1)); log("M1 ANALYSIS DONE")


if __name__ == "__main__":
    main()
