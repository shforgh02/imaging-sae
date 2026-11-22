"""Partner kit v1.0 (plan: docs/EXECUTION_LOG.md, 22 Nov 2026, task 4). Code to data: runs inside the partner's institution, offline,
on CPU; returns ONLY the aggregate file TO_RETURN/aggregate_report.json (and a human-readable copy for review). No patient-level
value, identifier, date, free text or path is written to TO_RETURN. Dependencies: numpy, pandas; pydicom for --geometry only.
Modes
  --selftest                      builds a synthetic dataset (no real data), runs --compare and --geometry, checks the output against the
                                  expected hash shipped in frozen/selftest_expected.sha256
  --compare exams.csv [--nodules nodules.csv]
                                  Sybil vs the frozen 14-item portable form P (and Lung-RADS if recorded); see CODING_SHEET.md
  --geometry <DICOM folder> [--series-manifest csv]
                                  slice thickness vs true spacing of every axial CT series (header only; no pixel is read)
Common: --out <folder> (default ./partner_output), --min-cell N (default 10), --site-label A (no institution name needed)
"""
import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

KIT = Path(__file__).resolve().parent
VERSION = "1.0"
P_SHA256 = "106da9776fa814797317ebae4e88d161a0866a0750343c7b7f1023638c3f22d6"
N_BOOT, SEED, YEAR = 2000, 0, 365.25
MAKERS = {"GE": "GE", "SIEMENS": "SIEMENS", "PHILIPS": "PHILIPS", "TOSHIBA": "CANON/TOSHIBA", "CANON": "CANON/TOSHIBA"}


# ------------------------------------------------------------------ small numerics (no scikit-learn)
def auc(y, s):
    y, s = np.asarray(y, float), np.asarray(s, float); m = np.isfinite(y) & np.isfinite(s); y, s = y[m], s[m]
    n1, n0 = (y == 1).sum(), (y == 0).sum()
    if n1 == 0 or n0 == 0: return None
    r = pd.Series(s).rank().to_numpy(); return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def auc_ipcw(T, E, s, t):
    """cumulative/dynamic AUROC at time t with inverse-probability-of-censoring weights (Blanche et al. 2013); T days, E 1 = cancer."""
    T, E, s = map(lambda x: np.asarray(x, float), (T, E, s)); ok = np.isfinite(T) & np.isfinite(E) & np.isfinite(s); T, E, s = T[ok], E[ok], s[ok]
    order = np.argsort(T); Ts, Cs = T[order], 1 - E[order]; G = np.ones(len(Ts)); surv = 1.0; n = len(Ts)
    for i in range(n):
        if Cs[i] == 1: surv *= 1 - 1 / (n - i)
        G[i] = surv
    def G_at(x): k = np.searchsorted(Ts, x, side="left") - 1; return np.where(k >= 0, G[np.clip(k, 0, n - 1)], 1.0)
    case = (T <= t) & (E == 1); ctrl = T > t
    if case.sum() == 0 or ctrl.sum() == 0: return None
    wi = 1 / np.maximum(G_at(T[case]), 1e-6); wj = 1 / max(float(G_at(np.array([t]))[0]), 1e-6)
    sc, sn = s[case], s[ctrl]; num = 0.0
    for v, w in zip(sc, wi): num += w * wj * ((sn < v).sum() + 0.5 * (sn == v).sum())
    return float(num / (wi.sum() * wj * ctrl.sum()))


def logreg(X, y, offset=None, iters=60):
    """unpenalised logistic regression by Newton-Raphson; returns [intercept, coefficients...]."""
    y = np.asarray(y, float); X = np.column_stack([np.ones(len(y))] + ([np.asarray(X, float).reshape(len(y), -1)] if X is not None else []))
    off = np.zeros(len(y)) if offset is None else np.asarray(offset, float); b = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(X @ b + off))); W = p * (1 - p); g = X.T @ (y - p); H = (X * W[:, None]).T @ X
        step = np.linalg.solve(H + 1e-8 * np.eye(len(b)), g); b = b + step
        if np.max(np.abs(step)) < 1e-10: break
    return b


def logit(p): p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6); return np.log(p / (1 - p))


class Boot:
    def __init__(self, groups):
        g = pd.Series(groups).astype(str).to_numpy(); u, inv = np.unique(g, return_inverse=True); order = np.argsort(inv, kind="stable")
        cnt = np.bincount(inv); start = np.r_[0, np.cumsum(cnt)[:-1]]; self.rows = [order[a:a + c] for a, c in zip(start, cnt)]; self.N = len(g)

    def takes(self):
        rng = np.random.default_rng(SEED); k = len(self.rows)
        for _ in range(N_BOOT): yield np.concatenate([self.rows[i] for i in rng.integers(0, k, k)])

    def stats(self, fn, keys):
        est = fn(np.arange(self.N)); D = np.array([[np.nan if v is None else v for v in fn(t)] for t in self.takes()], float); out = {}
        for i, k in enumerate(keys):
            d = D[:, i]; d = d[np.isfinite(d)]; ok = est[i] is not None and len(d) >= 0.9 * N_BOOT
            out[k] = dict(est=None if est[i] is None else float(est[i]), lo=float(np.percentile(d, 2.5)) if ok else None, hi=float(np.percentile(d, 97.5)) if ok else None,
                          se=float(np.std(d, ddof=1)) if ok else None)
        out["_draws"] = D; return out


# ------------------------------------------------------------------ the frozen portable form P
def load_P():
    raw = (KIT / "frozen" / "x10_portable_form_params.json").read_bytes()
    if hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest() != P_SHA256: raise SystemExit("REFUSED: frozen/x10_portable_form_params.json does not match its hash")
    return json.loads(raw)


def p_logit(params, X):
    Z = (X[params["features"]].to_numpy(float) - np.array(params["mean"])) / np.array(params["scale"]); return Z @ np.array(params["coef"]) + params["intercept"]


YES = {"Y", "YES", "1", "TRUE", "T"}; NO = {"N", "NO", "0", "FALSE", "F"}


def yn(s, name, log):
    v = s.astype(str).str.strip().str.upper(); bad = ~(v.isin(YES | NO) | s.isna())
    if bad.any(): log(f"{name}: {int(bad.sum())} values not Y/N, set missing")
    return pd.Series(np.where(v.isin(YES), 1.0, np.where(v.isin(NO), 0.0, np.nan)), index=s.index)


def nodule_items(N, log):
    """exam-level P items from a nodule table: largest non-calcified nodule >= 4 mm (diameter rule of the NLST form), its type, margin, lobe."""
    N = N.copy()
    if "volume_mm3" in N and "diameter_mm" not in N: N["diameter_mm"] = (6 * pd.to_numeric(N.volume_mm3, errors="coerce") / math.pi) ** (1 / 3)
    N["diameter_mm"] = pd.to_numeric(N.diameter_mm, errors="coerce")
    if "calcified" in N: N = N[yn(N.calcified, "calcified", log) != 1]
    N = N[N.diameter_mm >= 4.0]
    N["type"] = N.get("type", pd.Series("solid", index=N.index)).astype(str).str.lower().str.replace("_", "-")
    N["spic"] = yn(N.spiculated, "spiculated", log) if "spiculated" in N else np.nan
    N["upper"] = N.lobe.astype(str).str.upper().isin({"RUL", "LUL", "RIGHT UPPER", "LEFT UPPER"}).astype(float) if "lobe" in N else np.nan
    N = N.sort_values(["exam_id", "diameter_mm"], ascending=[True, False])
    big = N.drop_duplicates("exam_id")
    out = pd.DataFrame(dict(exam_id=big.exam_id, max_dia=big.diameter_mm, big_gg=(big.type == "ground-glass").astype(float), big_mixed=(big.type == "part-solid").astype(float),
                            big_spic=big.spic, big_upper=big.upper))
    out = out.merge(N.groupby("exam_id").size().rename("n_nod").reset_index(), on="exam_id")
    for k, col in (("gw2", "growth"), ("pre1", "new")):
        if col in N: out = out.merge(N.assign(v=yn(N[col], col, log)).groupby("exam_id").v.max().rename(k).reset_index(), on="exam_id", how="left")
    return out


def build_items(E, N, log):
    X = pd.DataFrame(dict(participant_id=E.participant_id.astype(str), exam_id=E.exam_id.astype(str)))
    X["screen_round"] = pd.to_numeric(E.screen_round, errors="coerce"); X["study_yr"] = X.screen_round.clip(upper=2)   # NLST had rounds 0 to 2
    X["age_scan"] = pd.to_numeric(E.age, errors="coerce")
    sx = E.sex.astype(str).str.strip().str.upper(); X["gender"] = np.where(sx.isin({"M", "MALE"}), 1.0, np.where(sx.isin({"F", "FEMALE"}), 2.0, np.nan))
    X["cigsmok"] = yn(E.current_smoker, "current_smoker", log); X["ab59"] = yn(E.emphysema, "emphysema", log) if "emphysema" in E else np.nan
    if N is not None:
        It = nodule_items(N.assign(exam_id=N.exam_id.astype(str)), log); X = X.merge(It, on="exam_id", how="left")
        nonod = X.max_dia.isna()                                              # no non-calcified nodule >= 4 mm in the exam
        for c in ("max_dia", "big_gg", "big_mixed", "big_spic", "big_upper", "n_nod"): X[c] = X[c].fillna(0.0)
        for k in ("gw2", "pre1"):
            if k in X: X.loc[nonod, k] = 0.0                                  # no nodule: no growth and no new nodule
    else:
        d = pd.to_numeric(E.max_diameter_mm, errors="coerce"); X["max_dia"] = np.where(d >= 4.0, d, 0.0)          # < 4 mm counts as no nodule (NLST form rule)
        t = E.nodule_type.astype(str).str.lower().str.replace("_", "-") if "nodule_type" in E else pd.Series("", index=E.index)
        X["big_gg"] = ((t == "ground-glass") & (X.max_dia > 0)).astype(float); X["big_mixed"] = ((t == "part-solid") & (X.max_dia > 0)).astype(float)
        X["big_spic"] = yn(E.spiculated, "spiculated", log).where(X.max_dia > 0, 0.0) if "spiculated" in E else np.nan
        X["big_upper"] = yn(E.upper_lobe, "upper_lobe", log).where(X.max_dia > 0, 0.0) if "upper_lobe" in E else np.nan
        X["n_nod"] = pd.to_numeric(E.n_nodules_ge4mm, errors="coerce") if "n_nodules_ge4mm" in E else np.where(X.max_dia > 0, 1.0, 0.0)
        for k, col in (("gw2", "growth"), ("pre1", "new_nodule")):
            if col in E: X[k] = yn(E[col], col, log)
    for k in ("gw2", "pre1"):
        if k not in X: X[k] = np.nan
        X.loc[X.screen_round == 0, k] = 0.0                                   # no earlier scan at baseline
    if (X.max_dia[X.max_dia > 0].median() if (X.max_dia > 0).any() else 10) < 2.5: log("WARNING: median nodule diameter < 2.5: are diameters in cm? (mm required)")
    X["log_dia"] = np.log1p(X.max_dia)
    for k in ("sybil_1yr", "sybil_6yr", "days_to_cancer", "days_to_last_followup"): X[k] = pd.to_numeric(E[k], errors="coerce") if k in E else np.nan
    if "lung_rads" in E:
        lr = E.lung_rads.astype(str).str.upper().str.replace(r"[SC]$", "", regex=True).str.strip()
        X["lung_rads"] = lr.map({"0": np.nan, "1": 1, "2": 2, "3": 3, "4A": 4, "4B": 5, "4X": 6}); X["lung_rads_0"] = (lr == "0").astype(int)
    return X


def outcome(X, years, baseline_only):
    """y = 1: cancer within `years` of the exam; 0: no cancer and follow-up >= years; else censored (NaN)."""
    t = years * YEAR; dc, df = X.days_to_cancer, X.days_to_last_followup
    y = np.where(dc.notna() & (dc <= t), 1.0, np.where(df >= t, 0.0, np.nan)); m = (X.screen_round == 0) if baseline_only else pd.Series(True, index=X.index)
    T = np.where(dc.notna(), dc, df); Ev = dc.notna().astype(float)
    return pd.Series(y, index=X.index), m, T, Ev.to_numpy()


# ------------------------------------------------------------------ suppression
class Supp:
    def __init__(self, k): self.k, self.n = k, 0

    def count(self, n):
        if n is None: return None
        if 0 < n < self.k: self.n += 1; return f"<{self.k}"
        return int(n)


def secondary(m_, f, yy, sp, info):
    """secondary suppression: rates from which a small count (TP, FN, FP or TN below min_cell) could be worked back are withheld."""
    tp, fn_ = int((f & (yy == 1)).sum()), int((~f & (yy == 1)).sum()); fp, tn = int((f & (yy == 0)).sum()), int((~f & (yy == 0)).sum())
    small = {k for k, v in (("tp", tp), ("fn", fn_), ("fp", fp), ("tn", tn)) if 0 < v < sp.k}
    if small & {"tp", "fn"}:
        for k in ("sensitivity", "missed_per_1000", "ppv"): m_[k] = dict(est=None, lo=None, hi=None, se=None, note="withheld: small cell"); sp.n += 1
    if small & {"fp", "tn"}:
        for k in ("specificity", "false_alarms_per_1000", "ppv"): m_[k] = dict(est=None, lo=None, hi=None, se=None, note="withheld: small cell"); sp.n += 1
    m_.update(info); return m_


def compare(E, N, out, a, log):
    P = load_P(); X = build_items(E, N, log); sp = Supp(a.min_cell); res = dict(kit_version=VERSION, site=a.site_label, min_cell=a.min_cell, endpoints={})
    miss = {c: float(X[c].isna().mean()) for c in P["P1"]["features"]}; res["missing_share_by_item"] = {k: round(v, 3) for k, v in miss.items()}
    for name, years, base, pk, sk in (("E1_1year_all_screens", 1, False, "P1", "sybil_1yr"), ("E2_1year_baseline", 1, True, "P1", "sybil_1yr"), ("E4_6years_baseline", 6, True, "P6", "sybil_6yr")):
        y, m, T, Ev = outcome(X, years, base); feats = P[pk]["features"]
        Q = X[m & y.notna() & X[sk].notna() & X[feats].notna().all(1)].copy(); Q["y"] = y[Q.index]; yy = Q.y.to_numpy(int); n1, n0 = int(yy.sum()), int((yy == 0).sum())
        o = dict(counts=dict(exams=sp.count(len(Q)), participants=sp.count(int(Q.participant_id.nunique())), cancers=sp.count(n1), controls=sp.count(n0)),
                 dropped_incomplete_items=sp.count(int((m & y.notna() & X[sk].notna()).sum() - len(Q))), censored_share=float(np.isnan(y[m]).mean()) if m.any() else None)
        if n1 < a.min_cell or n0 < a.min_cell: o["status"] = "insufficient cancers or controls"; res["endpoints"][name] = o; continue
        sP = p_logit(P[pk], Q); sS = logit(Q[sk]); pid = Q.participant_id.to_numpy(); bt = Boot(pid)
        demo = np.c_[Q.age_scan, Q.gender, Q.cigsmok]; fold = (pd.util.hash_array(pid.astype(object)) % 5).astype(int)

        def oof(Xm):
            o_ = np.zeros(len(yy))
            for f in range(5):
                tr, te = fold != f, fold == f; b = logreg(Xm[tr], yy[tr]); o_[te] = np.c_[np.ones(te.sum()), Xm[te]] @ b
            return o_
        sPS, sSD = oof(np.c_[sP, sS]), oof(np.c_[sS, demo])
        has_lr = "lung_rads" in Q and Q.lung_rads.notna().mean() > 0.9; sLR = Q.lung_rads.to_numpy(float) if has_lr else None
        names = ["sybil", "P", "sybil_plus_demographics_crossfit", "P_plus_sybil_crossfit"] + (["lung_rads"] if has_lr else [])
        S = dict(sybil=sS, P=sP, sybil_plus_demographics_crossfit=sSD, P_plus_sybil_crossfit=sPS, lung_rads=sLR)
        pairs = [("sybil", "P"), ("sybil_plus_demographics_crossfit", "P"), ("P_plus_sybil_crossfit", "P")] + ([("sybil", "lung_rads"), ("P", "lung_rads")] if has_lr else [])

        def fn(t):
            a_ = {k: auc(yy[t], S[k][t]) for k in names}
            return [a_[k] for k in names] + [None if a_[k] in (None, 0, 1) else math.log(a_[k] / (1 - a_[k])) for k in names] + [None if a_[u] is None or a_[v] is None else a_[u] - a_[v] for u, v in pairs]
        keys = [f"auroc_{k}" for k in names] + [f"logit_auroc_{k}" for k in names] + [f"{u}_minus_{v}" for u, v in pairs]
        st = bt.stats(fn, keys); D = st.pop("_draws")
        o["auroc"] = {k: st[f"auroc_{k}"] for k in names}; o["logit_auroc"] = {k: st[f"logit_auroc_{k}"] for k in names}; o["differences"] = {f"{u}_minus_{v}": st[f"{u}_minus_{v}"] for u, v in pairs}
        i, j = names.index("sybil"), names.index("P"); ok = np.isfinite(D[:, i]) & np.isfinite(D[:, j])
        o["bootstrap_correlation_auroc_sybil_P"] = float(np.corrcoef(D[ok, i], D[ok, j])[0, 1]) if ok.sum() > 10 else None
        if o["censored_share"] and o["censored_share"] > 0.05:
            Tm, Em = T[m.to_numpy()], Ev[m.to_numpy()]; Qm = X[m]; okr = Qm[sk].notna() & Qm[feats].notna().all(1)
            o["auroc_ipcw"] = dict(sybil=auc_ipcw(Tm[okr.to_numpy()], Em[okr.to_numpy()], logit(Qm[sk][okr]), years * YEAR),
                                   P=auc_ipcw(Tm[okr.to_numpy()], Em[okr.to_numpy()], p_logit(P[pk], Qm[okr]), years * YEAR))
        # Sybil's coefficient given P (participant bootstrap interval)
        cb = bt.stats(lambda t: [float(logreg(np.c_[sP[t], sS[t]], yy[t])[2])], ["c"]); cb.pop("_draws"); o["sybil_coefficient_given_P"] = cb["c"]
        # calibration of Sybil (published probabilities) and of P (its logistic probability)
        cal = {}
        for k, lg in (("sybil", sS), ("P", sP)):
            pr = 1 / (1 + np.exp(-lg))

            def cf(t, lg=lg, pr=pr):
                b1 = logreg(lg[t], yy[t]); b0 = logreg(None, yy[t], offset=lg[t])
                return [float(yy[t].sum() / pr[t].sum()), float(b0[0]), float(b1[1]), float(np.mean((pr[t] - yy[t]) ** 2))]
            c_ = bt.stats(cf, ["observed_over_expected", "calibration_intercept", "calibration_slope", "brier"]); c_.pop("_draws"); cal[k] = c_
        o["calibration"] = cal
        # measures at cuts: frozen NLST-dev cuts, and site cuts at 90% / 95% specificity re-estimated in every draw
        cuts = json.loads((KIT / "frozen" / "nlst_dev_cuts.json").read_text())[name]
        def meas(f, yy_):
            tp, fp = int((f & (yy_ == 1)).sum()), int((f & (yy_ == 0)).sum()); fn_, tn = int((~f & (yy_ == 1)).sum()), int((~f & (yy_ == 0)).sum())
            return [tp / max(1, tp + fn_), tn / max(1, tn + fp), (tp / (tp + fp)) if tp + fp else None, fp / len(yy_) * 1000, fn_ / len(yy_) * 1000]
        mk = ["sensitivity", "specificity", "ppv", "false_alarms_per_1000", "missed_per_1000"]; tabs = {}
        for c in cuts:
            sc = S[c["score"]] if c["score"] != "sybil_prob" else Q[sk].to_numpy(float)
            f_all = (sc > c["threshold"]) if c["rule"] == ">" else (sc >= c["threshold"])
            m_ = bt.stats(lambda t, f_all=f_all: meas(f_all[t], yy[t]), mk); m_.pop("_draws"); tabs[c["label"]] = secondary(m_, f_all, yy, sp, dict(threshold=c["threshold"], rule=c["rule"], source=c["source"]))
        for spec in (0.90, 0.95):
            for k in ("sybil", "P"):
                def sc_fn(t, k=k, spec=spec):
                    s_, yy_ = S[k][t], yy[t]; thr = np.quantile(s_[yy_ == 0], spec); return meas(s_ > thr, yy_)
                m_ = bt.stats(sc_fn, mk); m_.pop("_draws"); s_all = S[k]; f0 = s_all > np.quantile(s_all[yy == 0], spec)
                tabs[f"{k}_at_site_specificity_{int(spec * 100)}"] = secondary(m_, f0, yy, sp, dict(note="cut re-estimated on the site's cancer-free exams in every bootstrap draw"))
        o["measures_at_cuts"] = tabs
        if any(o["counts"][k] == f"<{a.min_cell}" for k in ("cancers", "controls")): o["status"] = "suppressed"
        res["endpoints"][name] = o
    # case mix (aggregates only)
    res["case_mix"] = dict(exams=sp.count(len(X)), participants=sp.count(int(X.participant_id.nunique())), age_mean=float(X.age_scan.mean()), age_sd=float(X.age_scan.std()),
                           female_share=float((X.gender == 2).mean()), current_smoker_share=float(X.cigsmok.mean()), baseline_share=float((X.screen_round == 0).mean()),
                           nodule_ge4mm_share=float((X.max_dia > 0).mean()), followup_median_days=float(X.days_to_last_followup.median()),
                           lung_rads_ge3_share=(float((X.lung_rads >= 3).mean()) if "lung_rads" in X else None), lung_rads_0_count=(sp.count(int(X.lung_rads_0.sum())) if "lung_rads_0" in X else None))
    res["cells_suppressed"] = sp.n; return res


# ------------------------------------------------------------------ geometry (header only)
def geometry(root, manifest, a, log):
    import pydicom
    sp = Supp(a.min_cell); series = {}; n_files = n_bad = 0; ts = {}
    for p in Path(root).rglob("*"):
        if not p.is_file(): continue
        n_files += 1
        try: d = pydicom.dcmread(str(p), stop_before_pixels=True, force=True)
        except Exception: n_bad += 1; continue
        if getattr(d, "Modality", None) != "CT": continue
        uid = str(getattr(d, "SeriesInstanceUID", "")); s = series.setdefault(uid, dict(pos=[], iop=None, thick=None, maker=None, itype="", enhanced=False, study=str(getattr(d, "StudyInstanceUID", ""))))
        t_ = str(getattr(getattr(d, "file_meta", None), "TransferSyntaxUID", "unknown")); ts[t_] = ts.get(t_, 0) + 1
        s["maker"] = s["maker"] or str(getattr(d, "Manufacturer", "")); s["itype"] = "\\".join(map(str, getattr(d, "ImageType", []) or []))
        if int(getattr(d, "NumberOfFrames", 1) or 1) > 1 and hasattr(d, "PerFrameFunctionalGroupsSequence"):
            s["enhanced"] = True
            try:
                sh = d.SharedFunctionalGroupsSequence[0]; s["thick"] = float(sh.PixelMeasuresSequence[0].SliceThickness); s["iop"] = [float(v) for v in sh.PlaneOrientationSequence[0].ImageOrientationPatient]
                s["pos"] += [[float(v) for v in fr.PlanePositionSequence[0].ImagePositionPatient] for fr in d.PerFrameFunctionalGroupsSequence]
            except Exception: log("enhanced CT without the expected functional groups (skipped)")
            continue
        try: s["pos"].append([float(v) for v in d.ImagePositionPatient]); s["iop"] = s["iop"] or [float(v) for v in d.ImageOrientationPatient]; s["thick"] = s["thick"] or float(d.SliceThickness)
        except Exception: pass
    att = dict(files=sp.count(n_files), unreadable=sp.count(n_bad), ct_series=sp.count(len(series))); rows = []
    for uid, s in series.items():
        it = s["itype"].upper()
        if any(k in it for k in ("LOCALIZER", "SCOUT", "MIP", "MPR", "SECONDARY", "REFORMAT", "PROJECTION")) or s["iop"] is None or len(s["pos"]) < 30 or not s["thick"]: continue
        r, c = np.array(s["iop"][:3]), np.array(s["iop"][3:]); nrm = np.cross(r, c)
        if abs(nrm[2]) < 0.95: continue
        z = np.sort(np.array(s["pos"]) @ nrm); dz = np.diff(z); step = float(np.median(dz)) if len(dz) else 0.0
        mk = next((v for k, v in MAKERS.items() if k in (s["maker"] or "").upper()), "OTHER/UNKNOWN")
        rows.append(dict(uid=uid, study=s["study"], ratio=round(step / s["thick"], 3) if s["thick"] else None, zero_steps=int((np.abs(dz) < 1e-3).sum()),
                         uniform=bool(len(dz) and (np.abs(dz - step) <= 0.05 * max(step, 1e-6)).mean() > 0.95), maker=mk, enhanced=s["enhanced"], thick=s["thick"]))
    G = pd.DataFrame(rows); att["axial_ct_series_kept"] = sp.count(len(G))
    def classes(Q):
        r = Q.ratio
        return {k: sp.count(int(m.sum())) for k, m in (("ratio_le_0p65", (r > 0) & (r <= 0.65)), ("0p65_0p85", (r > 0.65) & (r <= 0.85)), ("0p85_0p95", (r > 0.85) & (r < 0.95)),
                                                         ("0p95_1p05", (r >= 0.95) & (r <= 1.05)), ("gt_1p05", r > 1.05), ("ratio_0_or_irregular", (r <= 0) | ~Q.uniform))}
    out = dict(attrition=att, transfer_syntax_counts={k: sp.count(v) for k, v in ts.items()}, enhanced_multiframe_series=sp.count(int(G.enhanced.sum())) if len(G) else 0)
    if len(G):
        out["all_axial_series"] = classes(G); out["by_maker"] = {m: classes(G[G.maker == m]) for m in sorted(G.maker.unique())}
        st = G.groupby("study").ratio.agg(lambda r: ((r > 0) & (r <= 0.65)).any() and ((r >= 0.95) & (r <= 1.05)).any())
        out["studies"] = dict(n=sp.count(len(st)), with_both_overlapping_and_contiguous=sp.count(int(st.sum())))
        if manifest is not None:
            M = pd.read_csv(manifest, dtype=str); Gs = G[G.uid.isin(set(M.series_uid))]; out["series_sent_to_sybil"] = classes(Gs)
            if {"participant_id", "screen_round"} <= set(M.columns) and len(Gs):
                J = M.merge(Gs[["uid", "ratio"]], left_on="series_uid", right_on="uid"); J["st"] = ((J.ratio > 0) & (J.ratio <= 0.65)).astype(int); J["screen_round"] = pd.to_numeric(J.screen_round)
                Pp = J.merge(J, on="participant_id", suffixes=("_a", "_b")); Pp = Pp[Pp.screen_round_b == Pp.screen_round_a + 1]
                out["consecutive_screen_pairs"] = dict(n=sp.count(len(Pp)), stretch_status_changes=sp.count(int((Pp.st_a != Pp.st_b).sum())))
    out["cells_suppressed"] = sp.n; return out


# ------------------------------------------------------------------ main
def write(res, out):
    to = Path(out) / "TO_RETURN"; to.mkdir(parents=True, exist_ok=True)
    js = (json.dumps(res, indent=1, sort_keys=True, default=str) + "\n").encode("utf-8"); (to / "aggregate_report.json").write_bytes(js)
    h = hashlib.sha256(js).hexdigest()
    lines = [f"Partner kit v{VERSION}: aggregate report for review before it leaves the site", f"SHA-256 of aggregate_report.json: {h}",
             "The file holds aggregate numbers only: no patient-level value, identifier, date, free text or path.", "", json.dumps(res, indent=1, sort_keys=True, default=str)]
    (to / "SUMMARY_FOR_REVIEW.txt").write_text("\n".join(lines), encoding="utf-8"); return h


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--compare"); ap.add_argument("--nodules"); ap.add_argument("--geometry"); ap.add_argument("--series-manifest")
    ap.add_argument("--selftest", action="store_true"); ap.add_argument("--out", default="partner_output"); ap.add_argument("--min-cell", type=int, default=10); ap.add_argument("--site-label", default="A")
    a = ap.parse_args(); local = Path(a.out) / "LOCAL_DO_NOT_SEND"; local.mkdir(parents=True, exist_ok=True); logf = open(local / "diagnostics.log", "a", encoding="utf-8")
    log = lambda m: logf.write(m + "\n")   # noqa: E731
    if a.selftest:
        sys.path.insert(0, str(KIT / "synthetic")); import make_synthetic as MS
        tmp = Path(a.out) / "LOCAL_DO_NOT_SEND" / "synthetic"; ex, no, dc = MS.make(tmp)
        g_args = argparse.Namespace(**{**vars(a), "min_cell": 1})          # synthetic headers: no suppression, so the classes can be checked
        res = dict(compare=compare(pd.read_csv(ex), pd.read_csv(no), a.out, a, log), geometry=geometry(dc, None, g_args, log), selftest=True)
        h = write(res, a.out); exp = (KIT / "frozen" / "selftest_expected.sha256").read_text().strip()
        keyn = json.loads((KIT / "frozen" / "selftest_expected_key_numbers.json").read_text(encoding="utf-8-sig"))
        got = {f"{e}|{s}": res["compare"]["endpoints"][e]["auroc"][s]["est"] for e in ("E1_1year_all_screens", "E2_1year_baseline", "E4_6years_baseline") for s in ("sybil", "P")}
        same = all(abs(got[k] - v) <= 1e-6 for k, v in keyn.items())
        print(f"selftest: output SHA-256 {h} ({'identical to' if h == exp else 'differs from'} the reference); key numbers {'equal' if same else 'DIFFERENT'} -> {'PASS' if same else 'FAIL'}")
        sys.exit(0 if same else 1)
    res = dict(kit_version=VERSION)
    if a.compare: res["compare"] = compare(pd.read_csv(a.compare), pd.read_csv(a.nodules) if a.nodules else None, a.out, a, log)
    if a.geometry: res["geometry"] = geometry(a.geometry, a.series_manifest, a, log)
    print("written", write(res, a.out))


if __name__ == "__main__":
    main()
