"""Partner kit v1.0 (plan: docs/EXECUTION_LOG.md, 22 Nov 2026, task 4; revised after Neon's review of the built kit). Code to data: runs
inside the partner's institution, offline, on CPU; returns ONLY the aggregate file TO_RETURN/aggregate_report.json (and a human-readable
copy for review). No patient-level value, identifier, date, free text or path is written to TO_RETURN. Dependencies: numpy, pandas;
pydicom for --geometry only.
Modes
  --selftest                      synthetic data built by the kit (no real data): --compare with a nodule table, --compare with an exam
                                  table only and awkward codings, and --geometry; checks key numbers against frozen/selftest_expected*
  --compare exams.csv [--nodules nodules.csv]     Sybil vs the frozen 14-item portable form P (and Lung-RADS if recorded)
  --geometry <DICOM folder> [--series-manifest csv]   slice thickness vs true spacing of every axial CT series (header only)
Common: --out <folder> (default ./partner_output), --min-cell N (default 10), --site-label A (no institution name is needed)
Disclosure control: counts below --min-cell are shown as "<N"; counts at or above it are exact in --compare and rounded to a multiple of 5
in --geometry; shares are given only when both the count and its complement are at least --min-cell (else "withheld"); rates that would
reveal a small cell are withheld; an endpoint whose cancers or controls are below --min-cell reports no count at all.
"""
import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

KIT = Path(__file__).resolve().parent
VERSION = "1.0"
FROZEN_SHA = {"x10_portable_form_params.json": "106da9776fa814797317ebae4e88d161a0866a0750343c7b7f1023638c3f22d6",
              "nlst_dev_cuts.json": "ae2f5c6518c7e514b95924cd63e9d1381ac8189f66a6cb274303d1cc556b015e"}
N_BOOT, SEED, YEAR = 2000, 0, 365.25
MAKERS = {"GE": "GE", "SIEMENS": "SIEMENS", "PHILIPS": "PHILIPS", "TOSHIBA": "CANON/TOSHIBA", "CANON": "CANON/TOSHIBA"}
STD_TS = {"1.2.840.10008.1.2": "implicit_le", "1.2.840.10008.1.2.1": "explicit_le", "1.2.840.10008.1.2.2": "explicit_be", "1.2.840.10008.1.2.4.70": "jpeg_lossless",
          "1.2.840.10008.1.2.4.57": "jpeg_lossless", "1.2.840.10008.1.2.4.90": "jpeg2000_lossless", "1.2.840.10008.1.2.4.91": "jpeg2000", "1.2.840.10008.1.2.4.80": "jpeg_ls",
          "1.2.840.10008.1.2.4.81": "jpeg_ls", "1.2.840.10008.1.2.5": "rle", "1.2.840.10008.1.2.1.99": "deflate"}


# ------------------------------------------------------------------ numerics (no scikit-learn)
def auc(y, s):
    y, s = np.asarray(y, float), np.asarray(s, float); m = np.isfinite(y) & np.isfinite(s); y, s = y[m], s[m]
    n1, n0 = int((y == 1).sum()), int((y == 0).sum())
    if n1 == 0 or n0 == 0: return None
    r = pd.Series(s).rank().to_numpy(); return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (float(n1) * float(n0)))


def km_censoring(T, E):
    """Kaplan-Meier of the censoring distribution on unique times (events before censorings at a tie); returns (times, G after each time)."""
    u = np.unique(T); G, out = 1.0, []
    for t in u:
        c = ((T == t) & (E == 0)).sum(); at_risk = ((T > t) | ((T == t) & (E == 0))).sum()   # events at t leave the risk set first
        G *= (1 - c / at_risk) if at_risk else 1.0; out.append(G)
    return u, np.array(out)


def auc_ipcw(T, E, s, t):
    """cumulative/dynamic AUROC at time t with inverse-probability-of-censoring weights (Blanche et al. 2013)."""
    T, E, s = (np.asarray(x, float) for x in (T, E, s)); ok = np.isfinite(T) & np.isfinite(E) & np.isfinite(s); T, E, s = T[ok], E[ok], s[ok]
    if len(T) == 0: return None
    u, G = km_censoring(T, E)

    def G_left(x):   # G(x-): product over censoring times strictly before x
        k = np.searchsorted(u, x, side="left") - 1; return np.where(k >= 0, G[np.clip(k, 0, len(G) - 1)], 1.0)

    def G_at(x): k = int(np.searchsorted(u, x, side="right") - 1); return float(G[k]) if k >= 0 else 1.0
    case, ctrl = (T <= t) & (E == 1), T > t
    if case.sum() == 0 or ctrl.sum() == 0: return None
    wi, wj = 1 / np.maximum(G_left(T[case]), 1e-6), 1 / max(G_at(t), 1e-6); sn = np.sort(s[ctrl])
    lo, hi = np.searchsorted(sn, s[case], "left"), np.searchsorted(sn, s[case], "right")
    return float(np.sum(wi * wj * (lo + 0.5 * (hi - lo))) / (wi.sum() * wj * ctrl.sum()))


def logreg(X, y, offset=None, ridge=0.0, iters=100):
    """logistic regression by Newton-Raphson with step halving on the (penalised) log-likelihood; ridge on slopes only.
    Returns None if the outcome has one class, or the fit does not converge (separation, a flat likelihood) or gives |b| >= 50."""
    y = np.asarray(y, float)
    if len(np.unique(y)) < 2: return None
    X = np.column_stack([np.ones(len(y))] + ([np.asarray(X, float).reshape(len(y), -1)] if X is not None else []))
    off = np.zeros(len(y)) if offset is None else np.asarray(offset, float); b = np.zeros(X.shape[1]); R = ridge * np.eye(len(b)); R[0, 0] = 0

    def ll(b_):
        eta = X @ b_ + off; return float(np.sum(y * eta - np.logaddexp(0, eta)) - 0.5 * b_ @ R @ b_)
    cur = ll(b)
    for _ in range(iters):
        eta = np.clip(X @ b + off, -30, 30); p = 1 / (1 + np.exp(-eta)); W = p * (1 - p); g = X.T @ (y - p) - R @ b
        H = (X * W[:, None]).T @ X + R
        try: step = np.linalg.solve(H + 1e-10 * np.eye(len(b)), g)
        except np.linalg.LinAlgError: return None
        if np.max(np.abs(step)) < 1e-8: return b if np.max(np.abs(b)) < 50 else None   # converged (under separation the step stays large)
        t = 1.0
        while t > 1e-8:
            new = ll(b + t * step)
            if np.isfinite(new) and new >= cur - 1e-11 * max(1.0, abs(cur)): break   # relative tolerance (summation noise on large cohorts)
            t /= 2
        else: return None
        b, cur = b + t * step, new
        if not np.all(np.isfinite(b)) or np.max(np.abs(b)) >= 50: return None
    return None                                                                 # not converged within iters


def logit(p): p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6); return np.log(p / (1 - p))


def fold_of(ids, k=5): return np.array([int(hashlib.sha256(str(i).encode()).hexdigest()[:8], 16) % k for i in ids])


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
            d = D[:, i]; d = d[np.isfinite(d)]; ok = est[i] is not None and np.isfinite(est[i]) and len(d) >= 0.9 * N_BOOT
            out[k] = dict(est=None if est[i] is None or not np.isfinite(est[i]) else float(est[i]), lo=float(np.percentile(d, 2.5)) if ok else None,
                          hi=float(np.percentile(d, 97.5)) if ok else None, se=float(np.std(d, ddof=1)) if ok else None)
        out["_draws"] = D; return out


# ------------------------------------------------------------------ disclosure control
class Supp:
    def __init__(self, k): self.k, self.n = k, 0

    def count(self, n, round5=False):
        """counts 1 .. k-1 -> "<k"; with round5, other counts are rounded to a multiple of 5 (a positive count never becomes 0)."""
        if n is None: return None
        n = int(n)
        if 0 < n < self.k: self.n += 1; return f"<{self.k}"
        if not round5 or n == 0: return n
        return max(5 * ((self.k + 4) // 5), 5, int(5 * round(n / 5)))   # never below min_cell (e.g. 11 -> 15 with --min-cell 11)

    def share(self, num, den, digits=3):
        """a share only when the count and its complement are 0 or >= k; a positive share that rounds to 0 is shown as "<0.001" (digits 3)."""
        num, den = int(num), int(den)
        if den == 0: return None
        if (0 < num < self.k) or (0 < den - num < self.k): self.n += 1; return "withheld"
        v = round(num / den, digits)
        if v == 0 and num > 0: return f"<{10 ** -digits:g}"
        if v == 1 and num < den: return f">{1 - 10 ** -digits:g}"
        return v


def clean(o):
    """JSON-safe: NaN / inf -> None, numpy scalars -> Python."""
    if isinstance(o, dict): return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [clean(v) for v in o]
    if isinstance(o, np.bool_): return bool(o)
    if isinstance(o, np.integer): return int(o)
    if isinstance(o, (np.floating, float)): return None if not np.isfinite(o) else float(o)
    return o


# ------------------------------------------------------------------ frozen files
def frozen(name):
    raw = (KIT / "frozen" / name).read_bytes()
    if hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest() != FROZEN_SHA[name]: raise SystemExit(f"REFUSED: frozen/{name} does not match its hash")
    return json.loads(raw.decode("utf-8-sig"))


def p_logit(params, X):
    Z = (X[params["features"]].to_numpy(float) - np.array(params["mean"])) / np.array(params["scale"]); return Z @ np.array(params["coef"]) + params["intercept"]


# ------------------------------------------------------------------ input coding
YES = {"Y", "YES", "1", "TRUE", "T"}; NO = {"N", "NO", "0", "FALSE", "F"}


def norm_str(s):
    v = s.astype(str).str.strip().str.upper().str.replace(r"\.0$", "", regex=True)
    return v.where(~v.isin({"NAN", "", "NONE", "NA", "<NA>"}), np.nan)


def yn(s, name, log):
    v = norm_str(s); bad = v.notna() & ~v.isin(YES | NO)
    if bad.any(): log(f"{name}: {int(bad.sum())} values not Y/N/1/0, set missing")
    return pd.Series(np.where(v.isin(YES), 1.0, np.where(v.isin(NO), 0.0, np.nan)), index=s.index)


def ntype(s):
    v = norm_str(s).str.replace(r"[\s_]+", "-", regex=True)
    gg, ps = {"GROUND-GLASS", "GGN", "GGO", "NON-SOLID", "NONSOLID", "PURE-GROUND-GLASS"}, {"PART-SOLID", "PARTSOLID", "MIXED", "SEMI-SOLID", "SUBSOLID"}
    return v.map(lambda x: np.nan if not isinstance(x, str) else ("GG" if x in gg else ("PS" if x in ps else ("SOLID" if x == "SOLID" else np.nan))))


def upper_lobe(s):
    v = norm_str(s).str.replace(r"[\s_]+", " ", regex=True)
    ok = {"RUL", "LUL", "RIGHT UPPER", "LEFT UPPER", "RIGHT UPPER LOBE", "LEFT UPPER LOBE", "RML", "RLL", "LLL", "LINGULA", "RIGHT MIDDLE", "RIGHT LOWER", "LEFT LOWER",
          "RIGHT MIDDLE LOBE", "RIGHT LOWER LOBE", "LEFT LOWER LOBE"}
    return v.map(lambda x: np.nan if not isinstance(x, str) or x not in ok else (1.0 if x in {"RUL", "LUL", "RIGHT UPPER", "LEFT UPPER", "RIGHT UPPER LOBE", "LEFT UPPER LOBE"} else 0.0))


def nodule_items(N, log):
    """exam-level items from a nodule table: largest non-calcified nodule >= 4 mm (the NLST form rule), its type, margin and lobe."""
    N = N.copy(); N.columns = [c.strip() for c in N.columns]; N["exam_id"] = N.exam_id.astype(str).str.strip()
    d = pd.to_numeric(N["diameter_mm"], errors="coerce") if "diameter_mm" in N else pd.Series(np.nan, index=N.index)
    if "volume_mm3" in N: d = d.fillna((6 * pd.to_numeric(N.volume_mm3, errors="coerce") / math.pi) ** (1 / 3))
    if d.notna().sum() == 0: raise SystemExit("REFUSED: nodules.csv needs diameter_mm or volume_mm3")
    if d.dropna().median() < 2.5: log("WARNING: median nodule diameter < 2.5: are diameters in cm? (mm required)")
    N["d"] = d
    if "calcified" in N: N = N[yn(N.calcified, "calcified", log) != 1]
    N = N[N.d >= 4.0].copy()
    N["t"] = ntype(N["type"]) if "type" in N else np.nan
    N["spic"] = yn(N.spiculated, "spiculated", log) if "spiculated" in N else np.nan
    N["upper"] = upper_lobe(N.lobe) if "lobe" in N else np.nan
    N = N.sort_values(["exam_id", "d"], ascending=[True, False], kind="mergesort")   # stable: equal diameters keep file order
    big = N.drop_duplicates("exam_id")
    out = pd.DataFrame(dict(exam_id=big.exam_id.to_numpy(), max_dia=big.d.to_numpy(), big_gg=np.where(big.t.isna(), np.nan, (big.t == "GG").astype(float)),
                            big_mixed=np.where(big.t.isna(), np.nan, (big.t == "PS").astype(float)), big_spic=big.spic.to_numpy(), big_upper=big.upper.to_numpy()))
    out = out.merge(N.groupby("exam_id").size().rename("n_nod").reset_index(), on="exam_id")
    for k, col in (("gw2", "growth"), ("pre1", "new")):
        if col in N: out = out.merge(N.assign(v=yn(N[col], col, log)).groupby("exam_id").v.max().rename(k).reset_index(), on="exam_id", how="left")
    return out


def build_items(E, N, log):
    E = E.copy(); E.columns = [c.strip() for c in E.columns]
    X = pd.DataFrame(dict(participant_id=E.participant_id.astype(str).str.strip(), exam_id=E.exam_id.astype(str).str.strip()))
    if X.exam_id.duplicated().any(): raise SystemExit(f"REFUSED: {int(X.exam_id.duplicated().sum())} duplicate exam_id values")
    X["screen_round"] = pd.to_numeric(E.screen_round, errors="coerce")
    if X.screen_round.min() != 0: raise SystemExit("REFUSED: screen_round must start at 0 for the baseline screen")
    X["study_yr"] = X.screen_round.clip(upper=2)
    X["age_scan"] = pd.to_numeric(E.age, errors="coerce")
    sx = norm_str(E.sex); X["gender"] = np.where(sx.isin({"M", "MALE", "1"}), 1.0, np.where(sx.isin({"F", "FEMALE", "2"}), 2.0, np.nan))
    X["cigsmok"] = yn(E.current_smoker, "current_smoker", log) if "current_smoker" in E else np.nan
    X["ab59"] = yn(E.emphysema, "emphysema", log) if "emphysema" in E else np.nan
    items = ["max_dia", "big_gg", "big_mixed", "big_spic", "big_upper", "n_nod", "gw2", "pre1"]
    if N is not None:
        It = nodule_items(N, log); X = X.merge(It, on="exam_id", how="left"); nonod = X.max_dia.isna()
        for c in items:
            if c not in X: X[c] = np.nan
            X.loc[nonod, c] = 0.0                                              # no nodule >= 4 mm: no type, margin, lobe, growth or new nodule
    else:
        d = pd.to_numeric(E.max_diameter_mm, errors="coerce") if "max_diameter_mm" in E else pd.Series(np.nan, index=E.index)
        if (d > 0).any() and d[d > 0].median() < 2.5: log("WARNING: median nodule diameter < 2.5: are diameters in cm? (mm required)")
        X["max_dia"] = np.where(d.isna(), np.nan, np.where(d >= 4.0, d, 0.0)); has = (X.max_dia > 0).to_numpy()
        t = ntype(E.nodule_type) if "nodule_type" in E else pd.Series(np.nan, index=E.index)
        X["big_gg"] = np.where(~has, 0.0, np.where(t.isna(), np.nan, (t == "GG").astype(float)))
        X["big_mixed"] = np.where(~has, 0.0, np.where(t.isna(), np.nan, (t == "PS").astype(float)))
        X["big_spic"] = np.where(~has, 0.0, yn(E.spiculated, "spiculated", log)) if "spiculated" in E else np.where(~has, 0.0, np.nan)
        X["big_upper"] = np.where(~has, 0.0, yn(E.upper_lobe, "upper_lobe", log)) if "upper_lobe" in E else np.where(~has, 0.0, np.nan)
        nn = pd.to_numeric(E.n_nodules_ge4mm, errors="coerce") if "n_nodules_ge4mm" in E else pd.Series(np.nan, index=E.index)
        X["n_nod"] = np.where(~has, 0.0, nn)
        for k, col in (("gw2", "growth"), ("pre1", "new_nodule")):
            X[k] = np.where(~has, 0.0, yn(E[col], col, log)) if col in E else np.where(~has, 0.0, np.nan)
        X.loc[X.max_dia.isna(), items] = np.nan                               # nodule size unknown: every nodule item unknown
    X.loc[X.screen_round == 0, ["gw2", "pre1"]] = 0.0                        # no earlier scan at baseline
    X["log_dia"] = np.log1p(X.max_dia)
    for k in ("sybil_1yr", "sybil_6yr", "days_to_cancer", "days_to_last_followup"): X[k] = pd.to_numeric(E[k], errors="coerce") if k in E else np.nan
    for k in ("sybil_1yr", "sybil_6yr"):
        if ((X[k] < 0) | (X[k] > 1)).any(): raise SystemExit(f"REFUSED: {k} must be a probability between 0 and 1")
    if "lung_rads" in E:
        lr = norm_str(E.lung_rads).str.replace(r"\s+", "", regex=True).str.replace(r"[SC]+$", "", regex=True)
        X["lung_rads"] = lr.map({"1": 1, "2": 2, "3": 3, "4A": 4, "4B": 5, "4X": 6}); X["lung_rads_0"] = (lr == "0").astype(int)
        un = lr.notna() & X.lung_rads.isna() & (lr != "0")
        if un.any(): log(f"lung_rads: {int(un.sum())} values not in 0, 1, 2, 3, 4A, 4B, 4X (S/C allowed), set missing")
    neg = X.days_to_cancer < 0
    if neg.any(): log(f"{int(neg.sum())} exams after a lung cancer diagnosis (negative days_to_cancer) left out"); X = X[~neg].copy()
    fix = X.days_to_cancer.notna() & (X.days_to_last_followup.isna() | (X.days_to_last_followup < X.days_to_cancer))
    X.loc[fix, "days_to_last_followup"] = X.loc[fix, "days_to_cancer"]
    if X.max_dia.isna().mean() > 0.2: log(f"WARNING: nodule size missing in {X.max_dia.isna().mean():.0%} of exams (give 0 when there is no nodule >= 4 mm)")
    return X


NODULE_ITEMS = {"big_gg", "big_mixed", "big_spic", "big_upper", "n_nod"}; REPEAT_ITEMS = {"gw2", "pre1"}; P_MIN_COMPLETE = 0.8


def p_check(X, feats):
    """is the form usable at this site? Each item is checked where it applies (nodule items on exams with a nodule >= 4 mm; growth and new
    nodule on repeat screens with one; the rest on all exams). The form is evaluated only if every item is >= 80% complete there; otherwise it
    is not evaluated anywhere (no exam is dropped because one column is missing). Returns (usable, {item: (n missing, n applicable)})."""
    has = X.max_dia > 0; rep = X.screen_round > 0; out = {}
    for c in feats:
        st = has if c in NODULE_ITEMS else ((has & rep) if c in REPEAT_ITEMS else pd.Series(True, index=X.index))
        out[c] = (int(X.loc[st, c].isna().sum()), int(st.sum()))
    ok = all(n == 0 or (1 - m / n) >= P_MIN_COMPLETE for m, n in out.values())
    return ok, out


def outcome(X, years, baseline_only):
    t = years * YEAR; dc, df = X.days_to_cancer, X.days_to_last_followup
    y = np.where(dc.notna() & (dc <= t), 1.0, np.where(df > t, 0.0, np.nan)); m = (X.screen_round == 0) if baseline_only else pd.Series(True, index=X.index)
    T = np.where(dc.notna(), dc, df); Ev = dc.notna().astype(float).to_numpy()
    return pd.Series(y, index=X.index), m, T, Ev


# ------------------------------------------------------------------ --compare
def secondary(m_, f, yy, sp, info):
    """rates from which a small cell (TP, FN, FP or TN below min_cell) could be worked back are withheld."""
    tp, fn_ = int((f & (yy == 1)).sum()), int((~f & (yy == 1)).sum()); fp, tn = int((f & (yy == 0)).sum()), int((~f & (yy == 0)).sum())
    small = {k for k, v in (("tp", tp), ("fn", fn_), ("fp", fp), ("tn", tn)) if 0 < v < sp.k}; withheld = set()
    if small & {"tp", "fn"}: withheld |= {"sensitivity", "missed_per_1000", "ppv"}
    if small & {"fp", "tn"}: withheld |= {"specificity", "false_alarms_per_1000", "ppv"}
    for k in withheld: m_[k] = dict(est=None, lo=None, hi=None, se=None, note="withheld: small cell")
    sp.n += len(withheld); m_.update(info); return m_


def meas(f, yy_):
    tp, fp = int((f & (yy_ == 1)).sum()), int((f & (yy_ == 0)).sum()); fn_, tn = int((~f & (yy_ == 1)).sum()), int((~f & (yy_ == 0)).sum())
    return [tp / (tp + fn_) if tp + fn_ else None, tn / (tn + fp) if tn + fp else None, (tp / (tp + fp)) if tp + fp else None, fp / len(yy_) * 1000, fn_ / len(yy_) * 1000]


MK = ["sensitivity", "specificity", "ppv", "false_alarms_per_1000", "missed_per_1000"]


def site_cut(s0, spec):
    """cut on cancer-free scores for a target specificity; flag with > or >= as closer to the target (stepped scores)."""
    thr = float(np.quantile(s0, spec)); strict = abs(float((s0 <= thr).mean()) - spec) < abs(float((s0 < thr).mean()) - spec)
    return thr, strict


def coef_given_P(sP, sS, yy):
    def f(t):
        b = logreg(np.c_[sP[t], sS[t]], yy[t]); return [None if b is None else float(b[2])]
    return f


def endpoint(X, P, name, years, base, pk, sk, sp, cuts_all, use_P):
    y, m, T, Ev = outcome(X, years, base); feats = P[pk]["features"]
    elig = m & y.notna() & X[sk].notna(); Pok = X[feats].notna().all(1)
    Q = X[elig & Pok].copy() if use_P else X[elig].copy(); Q["y"] = y[Q.index]; yy = Q.y.to_numpy(int); n1, n0 = int(yy.sum()), int((yy == 0).sum())
    o = dict(P_evaluated=use_P)
    if n1 < sp.k or n0 < sp.k:
        o["status"] = "not analysed: fewer cancers or controls than min_cell (no count reported)"; return o, None
    o["counts"] = dict(exams=sp.count(len(Q)), participants=sp.count(int(Q.participant_id.nunique())), cancers=sp.count(n1), controls=sp.count(n0))
    o["dropped_incomplete_P_items"] = sp.count(int((elig & ~Pok).sum())) if use_P else None
    o["censored_share"] = sp.share(int((m & y.isna()).sum()), int(m.sum()), 2)
    pid = Q.participant_id.to_numpy(); bt = Boot(pid); sS = logit(Q[sk]); demo = Q[["age_scan", "gender", "cigsmok"]].to_numpy(float)
    sd = np.nanstd(demo, 0); dz = (demo - np.nanmean(demo, 0)) / np.where(sd > 0, sd, 1); dok = np.isfinite(dz).all(1); fold = fold_of(pid)

    def oof(Xm, ok_rows):
        out = np.full(len(yy), np.nan)
        for f in range(5):
            tr, te = (fold != f) & ok_rows, (fold == f) & ok_rows
            b = logreg(Xm[tr], yy[tr], ridge=1e-3) if tr.any() else None
            if b is not None and te.any(): out[te] = np.c_[np.ones(te.sum()), Xm[te]] @ b
        return out
    S = dict(sybil=sS)
    if dok.mean() > 0.9: S["sybil_plus_demographics_crossfit"] = oof(np.c_[sS, np.nan_to_num(dz)], dok)
    if use_P:
        sP = p_logit(P[pk], Q); S["P"] = sP; S["P_plus_sybil_crossfit"] = oof(np.c_[sP, sS], np.ones(len(yy), bool))
    lr_rows = Q.lung_rads.notna().to_numpy() if "lung_rads" in Q else None
    has_lr = lr_rows is not None and lr_rows.sum() >= 0.5 * len(Q) and int(yy[lr_rows].sum()) >= sp.k and int((yy[lr_rows] == 0).sum()) >= sp.k
    if has_lr: S["lung_rads"] = Q.lung_rads.to_numpy(float)
    names = list(S)
    pairs = [(u, v) for u, v in (("sybil", "P"), ("sybil_plus_demographics_crossfit", "P"), ("P_plus_sybil_crossfit", "P"), ("sybil", "lung_rads"), ("P", "lung_rads")) if u in S and v in S]

    def fn(t):
        a_ = {k: auc(yy[t], S[k][t]) for k in names}; d_ = []
        for u, v in pairs:   # comparisons with Lung-RADS use only the exams that have Lung-RADS (paired)
            if v == "lung_rads": r = t[lr_rows[t]]; au, av = auc(yy[r], S[u][r]), auc(yy[r], S[v][r])
            else: au, av = a_[u], a_[v]
            d_.append(None if au is None or av is None else au - av)
        return [a_[k] for k in names] + [None if a_[k] is None or a_[k] in (0, 1) else math.log(a_[k] / (1 - a_[k])) for k in names] + d_
    st = bt.stats(fn, [f"a|{k}" for k in names] + [f"l|{k}" for k in names] + [f"d|{u}_minus_{v}" for u, v in pairs]); D = st.pop("_draws")
    o["auroc"] = {k: st[f"a|{k}"] for k in names}; o["logit_auroc"] = {k: st[f"l|{k}"] for k in names}
    o["differences"] = {f"{u}_minus_{v}": st[f"d|{u}_minus_{v}"] for u, v in pairs}
    if "P" in names:
        i, j = names.index("sybil"), names.index("P"); ok = np.isfinite(D[:, i]) & np.isfinite(D[:, j])
        o["bootstrap_correlation_auroc_sybil_P"] = float(np.corrcoef(D[ok, i], D[ok, j])[0, 1]) if ok.sum() > 10 and np.std(D[ok, i]) > 0 and np.std(D[ok, j]) > 0 else None
        cb = bt.stats(coef_given_P(sP, sS, yy), ["c"]); cb.pop("_draws"); o["sybil_coefficient_given_P"] = cb["c"]
    cen = (m & y.isna()).sum() / max(1, m.sum())
    if cen > 0.05:
        mm = (m & X[sk].notna() & (Pok if use_P else True)).to_numpy(); Qm = X[mm]
        o["auroc_ipcw"] = dict(sybil=auc_ipcw(T[mm], Ev[mm], logit(Qm[sk]), years * YEAR), P=(auc_ipcw(T[mm], Ev[mm], p_logit(P[pk], Qm), years * YEAR) if use_P else None))
    cal = {}
    for k in [k for k in ("sybil", "P") if k in S]:
        lg = S[k]; pr = 1 / (1 + np.exp(-lg))

        def cf(t, lg=lg, pr=pr):
            b1, b0 = logreg(lg[t], yy[t]), logreg(None, yy[t], offset=lg[t]); oe = yy[t].sum() / pr[t].sum()
            return [float(oe), (math.log(oe) if oe > 0 else None), None if b0 is None else float(b0[0]), None if b1 is None else float(b1[1]), float(np.mean((pr[t] - yy[t]) ** 2))]
        c_ = bt.stats(cf, ["observed_over_expected", "log_observed_over_expected", "calibration_intercept", "calibration_slope", "brier"]); c_.pop("_draws"); cal[k] = c_
    o["calibration"] = cal
    tabs = {}
    for c in cuts_all[name]:
        if c["score"] == "P" and "P" not in S: continue
        sc = S["P"] if c["score"] == "P" else Q[sk].to_numpy(float); f_all = (sc > c["threshold"]) if c["rule"] == ">" else (sc >= c["threshold"])
        m_ = bt.stats(lambda t, f_all=f_all: meas(f_all[t], yy[t]), MK); m_.pop("_draws")
        tabs[c["label"]] = secondary(m_, f_all, yy, sp, dict(threshold=c["threshold"], rule=c["rule"], source=c["source"]))
    for spec in (0.90, 0.95):
        for k in [k for k in ("sybil", "P") if k in S]:
            def sc_fn(t, k=k, spec=spec):
                s_, yy_ = S[k][t], yy[t]
                if (yy_ == 0).sum() == 0 or (yy_ == 1).sum() == 0: return [None] * 5
                thr, strict = site_cut(s_[yy_ == 0], spec); return meas((s_ > thr) if strict else (s_ >= thr), yy_)
            m_ = bt.stats(sc_fn, MK); m_.pop("_draws"); thr, strict = site_cut(S[k][yy == 0], spec); f0 = (S[k] > thr) if strict else (S[k] >= thr)
            tabs[f"{k}_at_site_specificity_{int(spec * 100)}"] = secondary(m_, f0, yy, sp, dict(note="cut set on the site's cancer-free exams, re-estimated in every bootstrap draw (> or >= as closer to the target)"))
    o["measures_at_cuts"] = tabs
    return o, dict(exams=len(Q), participants=int(Q.participant_id.nunique()), cancers=n1, controls=n0)


EPS = (("E1_1year_all_screens", 1, False, "P1", "sybil_1yr"), ("E2_1year_baseline", 1, True, "P1", "sybil_1yr"), ("E4_6years_baseline", 6, True, "P6", "sybil_6yr"))


def cross_suppress(sizes, k):
    """complementary suppression across endpoints: for every pair of endpoints that still show counts, if exams, participants, cancers or
    controls differ by 1 .. k-1, the endpoint other than the primary E1 (E2 before E4 when E1 is not in the pair) loses its count-revealing
    numbers; repeated until no pair can reveal a small count (a baseline-only site, where E1 = E2, is covered). Returns {withheld: other}."""
    shown = [n for n, _, _, _, _ in EPS if sizes.get(n)]; out = {}; changed = True
    while changed:
        changed = False
        for i in range(len(shown)):
            for j in range(i + 1, len(shown)):
                u, v = shown[i], shown[j]
                if any(0 < abs(sizes[u][q] - sizes[v][q]) < k for q in sizes[u]):
                    drop = v if u == "E1_1year_all_screens" else (u if u == "E2_1year_baseline" else v)
                    out[drop] = v if drop == u else u; shown.remove(drop); changed = True; break
            if changed: break
    return out


def round_tree(o, d):
    if isinstance(o, dict): return {k: round_tree(v, d) for k, v in o.items()}
    if isinstance(o, (float, np.floating)) and np.isfinite(o): return round(float(o), d)
    return o


def compare(E, N, a, log):
    P = frozen("x10_portable_form_params.json"); cuts_all = frozen("nlst_dev_cuts.json"); X = build_items(E, N, log); sp = Supp(a.min_cell)
    res = dict(kit_version=VERSION, site=a.site_label, min_cell=a.min_cell, endpoints={},
               site_metadata=dict(lung_rads_version=a.lung_rads_version, nodule_diameter_type=a.diameter_type, cancer_ascertainment=a.cancer_ascertainment,
                                  input="nodule table" if N is not None else "exam table only"))
    use = {}
    for pk in ("P1", "P6"):
        ok, ms = p_check(X[X.screen_round == 0] if P[pk].get("baseline_only") else X, P[pk]["features"]); use[pk] = ok   # P6 is used on baseline screens only
        res[f"form_{pk}_items_missing_where_applicable"] = {c: ("none" if m == 0 else sp.share(m, n, 2)) for c, (m, n) in ms.items()}
        res[f"form_{pk}_evaluated"] = ok
    sizes = {}
    for name, years, base, pk, sk in EPS:
        o, sz = endpoint(X, P, name, years, base, pk, sk, sp, cuts_all, use[pk]); res["endpoints"][name] = o; sizes[name] = sz
    for name, other in cross_suppress(sizes, a.min_cell).items():
        e = res["endpoints"][name]
        for k in ("counts", "dropped_incomplete_P_items", "censored_share", "measures_at_cuts"):
            if e.get(k) is not None: e[k] = dict(note=f"withheld: a small count could be worked out by subtraction from {other}"); sp.n += 1
        for k in ("auroc", "logit_auroc", "differences", "calibration", "sybil_coefficient_given_P", "auroc_ipcw"):
            if k in e: e[k] = round_tree(e[k], 3)                           # rounded so that n1 x n0 cannot be recovered from a full-precision AUROC
    n = len(X); cm = dict(exams=sp.count(n, True), participants=sp.count(int(X.participant_id.nunique()), True), note_counts="rounded to a multiple of 5")
    if n >= a.min_cell:
        if X.age_scan.notna().sum() >= a.min_cell: cm.update(age_mean=round(float(X.age_scan.mean()), 1), age_sd=round(float(X.age_scan.std()), 1))
        if X.days_to_last_followup.notna().sum() >= a.min_cell:
            cm.update(followup_median_days=round(float(X.days_to_last_followup.median())), followup_iqr_days=[round(float(X.days_to_last_followup.quantile(q))) for q in (0.25, 0.75)])
        cm.update(female_share=sp.share(int((X.gender == 2).sum()), int(X.gender.notna().sum())), current_smoker_share=sp.share(int((X.cigsmok == 1).sum()), int(X.cigsmok.notna().sum())),
                  baseline_share=sp.share(int((X.screen_round == 0).sum()), n), nodule_ge4mm_share=sp.share(int((X.max_dia > 0).sum()), int(X.max_dia.notna().sum())))
        if "lung_rads" in X:
            cm["lung_rads_ge3_share"] = sp.share(int((X.lung_rads >= 3).sum()), int(X.lung_rads.notna().sum())); cm["lung_rads_0_share"] = sp.share(int(X.lung_rads_0.sum()), n)
    res["case_mix"] = cm; res["cells_suppressed"] = sp.n; return res


# ------------------------------------------------------------------ --geometry (header only)
BAD_IT = re.compile(r"LOCALIZER|SCOUT|MIP|MPR|SECONDARY|REFORMAT|PROJECTION", re.I)


def geometry(root, manifest, a, log):
    import pydicom
    sp = Supp(a.min_cell); series = {}; n_files = n_bad = 0; ts = {}; no_uid = 0; R5 = not getattr(a, "no_round", False)
    for p in sorted(Path(root).rglob("*")):
        if not p.is_file(): continue
        n_files += 1
        try: d = pydicom.dcmread(str(p), stop_before_pixels=True, force=True)
        except Exception: n_bad += 1; continue
        if getattr(d, "Modality", None) != "CT": continue
        uid = str(getattr(d, "SeriesInstanceUID", "") or "")
        if not uid: no_uid += 1; continue
        s = series.setdefault(uid, dict(pos=[], iop=None, thick=None, maker=None, bad_type=False, enhanced=False, study=str(getattr(d, "StudyInstanceUID", ""))))
        t_ = STD_TS.get(str(getattr(getattr(d, "file_meta", None), "TransferSyntaxUID", "")), "other"); ts[t_] = ts.get(t_, 0) + 1
        s["maker"] = s["maker"] or str(getattr(d, "Manufacturer", "") or "")
        it = getattr(d, "ImageType", None) or []; s["bad_type"] |= bool(BAD_IT.search(it if isinstance(it, str) else "\\".join(map(str, it))))
        try: nfr = int(str(getattr(d, "NumberOfFrames", 1) or 1).strip() or 1)
        except ValueError: nfr = 1
        try:
            if nfr > 1 and getattr(d, "PerFrameFunctionalGroupsSequence", None):
                s["enhanced"] = True; shs = getattr(d, "SharedFunctionalGroupsSequence", None); sh = shs[0] if shs else None

                def tag(fr, seq, attr, n=None):
                    """the attribute from the per-frame group, else from the shared group; None if absent or of the wrong length."""
                    for grp in (fr, sh):
                        q = getattr(grp, seq, None) if grp is not None else None
                        v = getattr(q[0], attr, None) if q else None
                        if v not in (None, ""):
                            try: v = [float(x) for x in v] if n else float(v)
                            except (TypeError, ValueError): continue
                            if n is None or len(v) == n: return v
                    return None
                for fr in d.PerFrameFunctionalGroupsSequence:
                    if s["thick"] is None: s["thick"] = tag(fr, "PixelMeasuresSequence", "SliceThickness")
                    if s["iop"] is None: s["iop"] = tag(fr, "PlaneOrientationSequence", "ImageOrientationPatient", 6)
                    pp = tag(fr, "PlanePositionSequence", "ImagePositionPatient", 3)
                    if pp is not None: s["pos"].append(pp)
            else:
                ipp, iop = list(getattr(d, "ImagePositionPatient", []) or []), list(getattr(d, "ImageOrientationPatient", []) or [])
                if len(ipp) == 3: s["pos"].append([float(v) for v in ipp])
                if len(iop) == 6 and s["iop"] is None: s["iop"] = [float(v) for v in iop]
                if s["thick"] is None and getattr(d, "SliceThickness", None) not in (None, ""): s["thick"] = float(d.SliceThickness)
        except Exception: log("a CT header could not be parsed (skipped)")
    rows = []; ex = dict(scout_or_reformat=0, fewer_than_30_slices=0, no_orientation_or_thickness=0, not_axial=0)
    for uid, s in series.items():
        if s["bad_type"]: ex["scout_or_reformat"] += 1; continue
        if s["iop"] is None or not s["thick"]: ex["no_orientation_or_thickness"] += 1; continue
        if len(s["pos"]) < 30: ex["fewer_than_30_slices"] += 1; continue
        r, c = np.array(s["iop"][:3]), np.array(s["iop"][3:]); nrm = np.cross(r, c); nn = float(np.linalg.norm(nrm))
        if nn == 0 or abs(nrm[2] / nn) < 0.95: ex["not_axial"] += 1; continue
        z = np.sort(np.array(s["pos"]) @ (nrm / nn)); dz = np.diff(z); step = float(np.median(dz)) if len(dz) else 0.0
        mk = next((v for k, v in MAKERS.items() if k in (s["maker"] or "").upper()), "OTHER/UNKNOWN")
        uni = bool(len(dz) and step > 0 and (np.abs(dz - step) <= 0.05 * step).mean() > 0.95)
        rows.append(dict(uid=uid, study=s["study"], ratio=round(step / s["thick"], 3), uniform=uni, maker=mk, enhanced=s["enhanced"]))
    G = pd.DataFrame(rows, columns=["uid", "study", "ratio", "uniform", "maker", "enhanced"])
    out = dict(attrition=dict(files=sp.count(n_files, R5), unreadable=sp.count(n_bad, R5), ct_series=sp.count(len(series), R5), axial_ct_series_kept=sp.count(len(G), R5),
                              ct_files_without_series_uid=sp.count(no_uid, R5), **{f"excluded_{k}": sp.count(v, R5) for k, v in ex.items()}),
               transfer_syntax_counts={k: sp.count(v, R5) for k, v in ts.items()}, enhanced_multiframe_series=sp.count(int(G.enhanced.sum()), R5) if len(G) else 0)

    def classes(Q):
        r, u = Q.ratio, Q.uniform.astype(bool)
        return {k: sp.count(int(m.sum()), R5) for k, m in (("ratio_le_0p65", u & (r > 0) & (r <= 0.65)), ("0p65_0p85", u & (r > 0.65) & (r <= 0.85)),
                                                               ("0p85_0p95", u & (r > 0.85) & (r < 0.95)), ("0p95_1p05", u & (r >= 0.95) & (r <= 1.05)), ("gt_1p05", u & (r > 1.05)),
                                                               ("ratio_0_or_irregular", ~u | (r <= 0)))}
    if len(G):
        out["all_axial_series"] = classes(G)
        vc = G.maker.value_counts(); keep = set(vc[vc >= a.min_cell].index); G["mk2"] = np.where(G.maker.isin(keep), G.maker, "OTHER/UNKNOWN")
        out["by_maker"] = {m: classes(G[G.mk2 == m]) for m in sorted(G.mk2.unique()) if (G.mk2 == m).sum() >= a.min_cell}
        both = {st_: bool((q.uniform & (q.ratio > 0) & (q.ratio <= 0.65)).any() and (q.uniform & (q.ratio >= 0.95) & (q.ratio <= 1.05)).any()) for st_, q in G.groupby("study")}
        out["studies"] = dict(n=sp.count(len(both), R5), with_both_overlapping_and_contiguous=sp.count(int(sum(both.values())), R5))
        if manifest is not None:
            M = pd.read_csv(manifest, dtype=str, encoding="utf-8-sig"); M.columns = [c.strip() for c in M.columns]; M["series_uid"] = M.series_uid.str.strip()
            Gs = G[G.uid.isin(set(M.series_uid))]; out["series_sent_to_sybil"] = classes(Gs)
            if {"participant_id", "screen_round"} <= set(M.columns) and len(Gs):
                J = M.merge(Gs[["uid", "ratio", "uniform"]], left_on="series_uid", right_on="uid")
                J["st"] = (J.uniform.astype(bool) & (J.ratio > 0) & (J.ratio <= 0.65)).astype(int); J["screen_round"] = pd.to_numeric(J.screen_round, errors="coerce")
                Pp = J.merge(J, on="participant_id", suffixes=("_a", "_b")); Pp = Pp[Pp.screen_round_b == Pp.screen_round_a + 1]
                out["consecutive_screen_pairs"] = dict(n=sp.count(len(Pp), R5), stretch_status_changes=sp.count(int((Pp.st_a != Pp.st_b).sum()), R5))
    out["cells_suppressed"] = sp.n
    out["note"] = ("counts rounded to a multiple of 5 (a positive count is never shown as 0); " if R5 else "counts NOT rounded (self-test only); ") + \
        "counts below min_cell shown as <min_cell; makers with fewer series than min_cell merged into OTHER/UNKNOWN; the counts are of CT series and studies, not of people"
    return out


# ------------------------------------------------------------------ main
def read_csv(p): return pd.read_csv(p, dtype=str, encoding="utf-8-sig")


def write(res, out):
    to = Path(out) / "TO_RETURN"; to.mkdir(parents=True, exist_ok=True)
    js = (json.dumps(clean(res), indent=1, sort_keys=True, allow_nan=False) + "\n").encode("utf-8"); (to / "aggregate_report.json").write_bytes(js); h = hashlib.sha256(js).hexdigest()
    lines = [f"Partner kit v{VERSION}: aggregate report for review before it leaves the site", f"SHA-256 of aggregate_report.json: {h}",
             "The file holds aggregate numbers only: no patient-level value, identifier, date, free text or path.", "", js.decode("utf-8")]
    (to / "SUMMARY_FOR_REVIEW.txt").write_text("\n".join(lines), encoding="utf-8"); return h


KEY_BLOCKS = ("compare", "compare_exam_table_only", "compare_no_margin_column"); KEY_EPS = ("E1_1year_all_screens", "E2_1year_baseline", "E4_6years_baseline")


def unit_checks():
    """small known-answer checks of the input coding and the numerics (synthetic values; no data)."""
    log = lambda m: None   # noqa: E731
    out = {}
    v = yn(pd.Series(["1.0", "0.0", "", "Y", " no ", "x"]), "t", log).tolist(); out["yn_1.0_0.0_blank"] = v[:2] == [1.0, 0.0] and np.isnan(v[2]) and v[3:5] == [1.0, 0.0] and np.isnan(v[5])
    N = pd.DataFrame(dict(exam_id=["e1", "e1", "e2", "e3"], diameter_mm=["12", "8", "", "3"], volume_mm3=["", "", "523.6", ""], calcified=["Y", "n", "", "N"],
                          type=["solid", "Part Solid", "ground glass", "solid"], lobe=["RUL", " Right  Upper Lobe", "lingula", "LLL"], spiculated=["", "1", "0", ""]))
    It = nodule_items(N, log).set_index("exam_id")
    out["calcified_largest_left_out"] = bool(abs(It.loc["e1", "max_dia"] - 8) < 1e-9 and It.loc["e1", "big_mixed"] == 1 and It.loc["e1", "big_upper"] == 1 and It.loc["e1", "big_spic"] == 1)
    out["volume_to_diameter_and_lingula"] = bool(abs(It.loc["e2", "max_dia"] - 10.0) < 1e-3 and It.loc["e2", "big_gg"] == 1 and It.loc["e2", "big_upper"] == 0)
    out["nodule_below_4mm_left_out"] = "e3" not in It.index
    lr = norm_str(pd.Series(["4AS ", "4B C", "4x", "0", "3", "2S", ""])).str.replace(r"\s+", "", regex=True).str.replace(r"[SC]+$", "", regex=True)
    out["lung_rads_parsing"] = lr.map({"1": 1, "2": 2, "3": 3, "4A": 4, "4B": 5, "4X": 6}).fillna(-1).tolist() == [4, 5, 6, -1, 3, 2, -1]
    u, G = km_censoring(np.array([1.0, 1.0, 2.0]), np.array([1, 0, 0])); out["km_events_before_censorings"] = bool(np.allclose(G, [0.5, 0.0]))
    out["logreg_separation_gives_None"] = logreg(np.array([0.0, 0.0, 1.0, 1.0]), np.array([0, 0, 1, 1])) is None
    rng = np.random.default_rng(3); xx = rng.normal(size=400); yy = (rng.random(400) < 1 / (1 + np.exp(-(0.5 + 1.2 * xx)))).astype(int); b = logreg(xx, yy)
    out["logreg_converges"] = b is not None and abs(b[1] - 1.2) < 0.4
    s4, s1 = Supp(4), Supp(1)
    out["suppression_rules"] = s4.count(2, True) == "<4" and s1.count(2, True) == 5 and s1.count(0, True) == 0 and Supp(10).share(3, 1000) == "withheld" and Supp(10).share(10, 100000) == "<0.001"
    out["min_cell_11_never_shows_10"] = Supp(11).count(11, True) >= 11 and Supp(11).count(12, True) >= 11 and Supp(11).count(10, True) == "<11"
    base = dict(exams=1000, participants=1000, cancers=20, controls=980)
    out["cross_endpoint_suppression"] = (cross_suppress({"E1_1year_all_screens": base, "E2_1year_baseline": dict(base), "E4_6years_baseline": dict(exams=900, participants=900, cancers=25, controls=875)}, 10)
                                         == {"E4_6years_baseline": "E1_1year_all_screens"} and
                                         set(cross_suppress({"E1_1year_all_screens": dict(exams=3000, participants=1500, cancers=60, controls=2940), "E2_1year_baseline": base,
                                                             "E4_6years_baseline": dict(exams=995, participants=995, cancers=40, controls=955)}, 10)) == {"E2_1year_baseline"})
    Xc = pd.DataFrame(dict(max_dia=[0, 6, 8, 0], screen_round=[0, 1, 1, 0], big_spic=[0, np.nan, np.nan, 0], gw2=[0, 1, 0, 0]))
    out["form_off_when_an_item_is_missing_where_it_applies"] = p_check(Xc, ["max_dia", "big_spic", "gw2"])[0] is False and p_check(Xc, ["max_dia", "gw2"])[0] is True
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--compare"); ap.add_argument("--nodules"); ap.add_argument("--geometry"); ap.add_argument("--series-manifest")
    ap.add_argument("--selftest", action="store_true"); ap.add_argument("--write-reference", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--out", default="partner_output"); ap.add_argument("--min-cell", type=int, default=10); ap.add_argument("--site-label", default="A")
    ap.add_argument("--lung-rads-version", default="not stated", help="e.g. 1.1, 2022, none"); ap.add_argument("--diameter-type", default="not stated", help="longest, mean or volume")
    ap.add_argument("--cancer-ascertainment", default="not stated", help="registry, records or mixed")
    a = ap.parse_args()
    if not (a.selftest or a.compare or a.geometry): ap.print_help(); return
    local = Path(a.out) / "LOCAL_DO_NOT_SEND"; local.mkdir(parents=True, exist_ok=True)
    with open(local / "diagnostics.log", "a", encoding="utf-8") as logf:
        def log(msg): logf.write(msg + "\n")
        if a.selftest:
            sys.path.insert(0, str(KIT / "synthetic")); import make_synthetic as MS
            ex, no, ex2, dc, man = MS.make(local / "synthetic")
            g_args = argparse.Namespace(**{**vars(a), "min_cell": 1, "no_round": True})   # synthetic headers: no suppression or rounding, so the classes can be checked
            res = dict(kit_version=VERSION, selftest=True, unit_checks=unit_checks(), compare=compare(read_csv(ex), read_csv(no), a, log),
                       compare_exam_table_only=compare(read_csv(ex2), None, a, log), compare_no_margin_column=compare(read_csv(ex2).drop(columns=["spiculated"]), None, a, log),
                       geometry=geometry(dc, man, g_args, log))
            h = write(res, a.out); g = res["geometry"]; nm = res["compare_no_margin_column"]
            structure = dict(no_margin_column_form_off=nm["form_P1_evaluated"] is False and all("P" not in e.get("auroc", {}) and "sybil" in e.get("auroc", {}) for e in nm["endpoints"].values()),
                             geometry_classes=g["all_axial_series"] == {"ratio_le_0p65": 2, "0p65_0p85": 1, "0p85_0p95": 0, "0p95_1p05": 2, "gt_1p05": 0, "ratio_0_or_irregular": 0},
                             geometry_scout_excluded=g["attrition"]["excluded_scout_or_reformat"] == 1, geometry_enhanced_shared_and_per_frame=g["enhanced_multiframe_series"] == 2,
                             geometry_study_with_both=g["studies"]["with_both_overlapping_and_contiguous"] == 1,
                             geometry_manifest_pairs=g.get("consecutive_screen_pairs") == {"n": 1, "stretch_status_changes": 1})
            got = {f"{b}|{e}|{s}": res[b]["endpoints"][e]["auroc"][s]["est"] for b in KEY_BLOCKS for e in KEY_EPS for s in ("sybil", "P")
                   if "auroc" in res[b]["endpoints"][e] and s in res[b]["endpoints"][e]["auroc"]}
            ref = KIT / "frozen" / "selftest_expected_key_numbers.json"
            checks_ok = all(res["unit_checks"].values()) and all(structure.values())
            if not checks_ok: print("FAILED checks:", [k for k, v in {**res["unit_checks"], **structure}.items() if not v])
            if a.write_reference:
                if not checks_ok: sys.exit(1)
                ref.write_text(json.dumps(got, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n"); print("reference written", h); return
            keyn = json.loads(ref.read_text(encoding="utf-8-sig"))
            same = set(got) == set(keyn) and all(got[k] is not None and abs(got[k] - v) <= 1e-6 for k, v in keyn.items())
            ok = same and checks_ok
            print(f"selftest: output SHA-256 {h}; {len(res['unit_checks'])} unit checks and {len(structure)} structure checks {'pass' if checks_ok else 'FAIL'}; "
                  f"key numbers {'equal to the reference' if same else 'DIFFERENT from the reference'} -> {'PASS' if ok else 'FAIL'}")
            sys.exit(0 if ok else 1)
        res = dict(kit_version=VERSION)
        if a.compare: res["compare"] = compare(read_csv(a.compare), read_csv(a.nodules) if a.nodules else None, a, log)
        if a.geometry: res["geometry"] = geometry(a.geometry, a.series_manifest, a, log)
        print("written; SHA-256", write(res, a.out))


if __name__ == "__main__":
    main()
