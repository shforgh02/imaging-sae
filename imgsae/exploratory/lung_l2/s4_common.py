"""Lung L2, S4: shared helpers of the analysis scripts (docs/LUNG_L2_PROTOCOL.md section 9; plan docs/PLAN_L2_NEXT_v1.md P4).
Conventions (fixed before any full-dev outcome analysis):
- Populations: y1 on all screens; y2 and y6 on baseline screens (study_yr 0). A row enters a horizon only if its outcome is known.
- Folds: participant-grouped 5 folds, seed 0 (s4_q1a.folds, the same folds in every S4 script); halves: 2 participant folds, seed 0.
- Intervals: participant-cluster bootstrap, 2,000 draws, seed 0, percentile 95% interval. The same draws are reused within a script.
- Cross-fitted logistic: plain (unpenalised, C = 1e6, as lung L1) logistic regression on standardised columns, fitted on 4 folds and
  predicted on the 5th. Likelihood-ratio test: the same model on all rows, nested, chi-square with df = added columns.
- SMD: (mean of the class - mean of the reference) / pooled SD. Its p-value: difference of means with a participant-cluster-robust
  (CR1) standard error, normal approximation. Benjamini-Hochberg q within each table.
- Candidates for gate 9.8: every script writes them in one format (candidate()); s4_gate.py judges them.
Test data: load() refuses any exam table that is not all dev participants.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import beta as Beta
from scipy.stats import chi2, norm
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, r"D:\Shayan\imgsae")
import l2_data as D  # noqa: E402,F401
import s4_core as C  # noqa: E402
import s4_q1a as Q  # noqa: E402

N_BOOT, SEED = 2000, 0
DATA = Path(os.environ.get("L2_S4_DATA", r"D:\Shayan\imgsae_data\lung_l2"))   # arms, contributions (outside git); tests point it elsewhere
HORIZONS = {"y1": ("s1", "lbar1", False), "y2": ("s2", "lbar2", True), "y6": ("s6", "lbar6", True)}   # score, analysed score, baseline only


# ------------------------------------------------------------------ data
def load(assembled, tag="dev"):
    """exam table (+ lbar_t, the mean member logits) and the main arrays aligned to it."""
    A = Path(assembled)
    E = pd.read_csv(A / f"exams_{tag}.csv", dtype={"pid": str}, low_memory=False)
    if tag == "dev" and not (E.grp == "dev").all(): raise SystemExit("REFUSED: the exam table holds non-dev participants")
    Z = np.load(A / f"arrays_{tag}_main.npz", allow_pickle=True); pos = {u: i for i, u in enumerate(Z["series_uid"])}
    idx = np.array([pos[u] for u in E.series_uid])
    arr = {k: Z[k][idx] for k in ("h", "logit", "raw_haz", "base_haz")}
    for t in range(1, 7): E[f"lbar{t}"] = arr["logit"][:, :, t - 1].astype(np.float64).mean(1)
    return E, arr


def pop(E, y):
    """boolean mask of the rows that enter horizon y."""
    m = E[y].notna()
    if HORIZONS[y][2]: m &= E.study_yr == 0
    return m.to_numpy()


def counts(E, mask=None, y=None):
    S = E if mask is None else E[mask]
    out = dict(exams=int(len(S)), participants=int(S.pid.nunique()))
    if y is not None: out["cancers"] = int((S[y] == 1).sum())
    return out


def folds(pid): return Q.folds(np.asarray(pid))


def halves(pid): return Q.folds(np.asarray(pid), k=2, seed=0)


def logit(p):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6); return np.log(p / (1 - p))


# ------------------------------------------------------------------ bootstrap and AUROC
class Boot:
    """participant-cluster bootstrap over the rows of one population; .takes() yields the same index arrays every time."""

    def __init__(self, pid, n=N_BOOT, seed=SEED):
        pid = np.asarray(pid); u, inv = np.unique(pid, return_inverse=True); order = np.argsort(inv, kind="stable")
        cnt = np.bincount(inv); start = np.r_[0, np.cumsum(cnt)[:-1]]
        self.rows = [order[s:s + c] for s, c in zip(start, cnt)]; self.n, self.seed, self.N = n, seed, len(pid)

    def takes(self):
        rng = np.random.default_rng(self.seed); k = len(self.rows)
        for _ in range(self.n): yield np.concatenate([self.rows[i] for i in rng.integers(0, k, k)])

    def ci(self, fn):
        """point estimate on all rows and the 95% percentile interval of fn(take); fn returns a float or None."""
        est = fn(np.arange(self.N)); d = []
        for t in self.takes():
            v = fn(t)
            if v is not None and np.isfinite(v): d.append(v)
        lo, hi = (np.percentile(d, [2.5, 97.5]) if len(d) >= 0.9 * self.n else (np.nan, np.nan))
        return dict(est=None if est is None else float(est), lo=float(lo), hi=float(hi), n_draws=len(d))


def auc(y, s):
    y, s = np.asarray(y, float), np.asarray(s, float); m = np.isfinite(y) & np.isfinite(s)
    return float(roc_auc_score(y[m], s[m])) if m.sum() > 1 and len(np.unique(y[m])) == 2 else None


def auc_ci(y, s, boot):
    y, s = np.asarray(y, float), np.asarray(s, float); return boot.ci(lambda t: auc(y[t], s[t]))


def dauc_ci(y, a, b, boot):
    y, a, b = np.asarray(y, float), np.asarray(a, float), np.asarray(b, float)

    def fn(t):
        u, v = auc(y[t], a[t]), auc(y[t], b[t]); return None if u is None or v is None else u - v
    return boot.ci(fn)


# ------------------------------------------------------------------ logistic models
def _lr(): return make_pipeline(StandardScaler(), LogisticRegression(C=1e6, max_iter=5000))


def crossfit(y, X, fold, model=_lr):
    """out-of-fold probabilities (n,) of model() on columns X (n, p); y must be 0/1 on all rows."""
    X = np.asarray(X, float).reshape(len(y), -1); y = np.asarray(y, int); out = np.zeros(len(y))
    for f in np.unique(fold):
        tr, te = fold != f, fold == f
        out[te] = model().fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
    return out


def loglik(y, X):
    X = np.asarray(X, float).reshape(len(y), -1); y = np.asarray(y, int)
    p = np.clip(_lr().fit(X, y).predict_proba(X)[:, 1], 1e-12, 1 - 1e-12)
    return float(np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))


def lr_test(y, X_small, X_big):
    Xs, Xb = np.asarray(X_small, float).reshape(len(y), -1), np.asarray(X_big, float).reshape(len(y), -1)
    stat = 2 * (loglik(y, Xb) - loglik(y, Xs)); df = Xb.shape[1] - Xs.shape[1]
    return dict(chi2=float(stat), df=int(df), p=float(chi2.sf(max(stat, 0.0), df)))


def added_value(y, base, extra, pid, boot=None):
    """does `extra` add to `base`? cross-fitted logistic y ~ base + extra against y ~ base: AUROC of both (out of fold), their
    difference with a participant-bootstrap interval, the likelihood-ratio test, and the difference refitted within each dev half."""
    y = np.asarray(y, int); base = np.asarray(base, float).reshape(len(y), -1); extra = np.asarray(extra, float).reshape(len(y), -1)
    full = np.hstack([base, extra]); fold = folds(pid); boot = boot or Boot(pid)
    p0, p1 = crossfit(y, base, fold), crossfit(y, full, fold)
    out = dict(auroc_base=auc_ci(y, p0, boot), auroc_full=auc_ci(y, p1, boot), dauroc=dauc_ci(y, p1, p0, boot), lr=lr_test(y, base, full))
    hv = halves(pid); hh = []
    for k in (0, 1):
        m = hv == k; fk = folds(np.asarray(pid)[m])
        try: a1, a0 = auc(y[m], crossfit(y[m], full[m], fk)), auc(y[m], crossfit(y[m], base[m], fk))
        except ValueError: a1 = a0 = None   # a training fold without cases (small data): no value, so gate 9.8 cannot pass it
        hh.append(None if a1 is None or a0 is None else a1 - a0)
    out["dauroc_halves"] = hh
    return out


# ------------------------------------------------------------------ group comparisons
def smd(x, g, ref):
    x = np.asarray(x, float); a, b = x[g & np.isfinite(x)], x[ref & np.isfinite(x)]
    if len(a) < 2 or len(b) < 2: return None
    sp = np.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2))
    return float((a.mean() - b.mean()) / sp) if sp > 0 else None


def cluster_p(x, g, ref, pid):
    """two-sided p of the mean difference (g minus ref) with a participant-cluster-robust (CR1) standard error."""
    x = np.asarray(x, float); m = (g | ref) & np.isfinite(x)
    if (g & m).sum() < 2 or (ref & m).sum() < 2: return None
    xv, d, cl = x[m], g[m].astype(float), np.asarray(pid)[m]
    X = np.column_stack([np.ones(len(xv)), d]); XtXi = np.linalg.inv(X.T @ X); b = XtXi @ X.T @ xv; e = xv - X @ b
    S = pd.DataFrame(X * e[:, None]).groupby(cl).sum().to_numpy(); G, N = len(S), len(xv)
    V = XtXi @ (S.T @ S) @ XtXi * (G / (G - 1)) * ((N - 1) / (N - 2))
    se = np.sqrt(V[1, 1]); return float(2 * norm.sf(abs(b[1] / se))) if se > 0 else None


def slope_p(yv, xv, pid):
    """two-sided p of the slope of yv on xv (OLS with intercept), participant-cluster-robust (CR1) standard error."""
    yv, xv = np.asarray(yv, float), np.asarray(xv, float); m = np.isfinite(yv) & np.isfinite(xv)
    if m.sum() < 3 or np.std(xv[m]) == 0: return None
    X = np.column_stack([np.ones(m.sum()), xv[m]]); XtXi = np.linalg.inv(X.T @ X); b = XtXi @ X.T @ yv[m]; e = yv[m] - X @ b
    S = pd.DataFrame(X * e[:, None]).groupby(np.asarray(pid)[m]).sum().to_numpy(); G, N = len(S), int(m.sum())
    V = XtXi @ (S.T @ S) @ XtXi * (G / (G - 1)) * ((N - 1) / (N - 2)); se = np.sqrt(max(V[1, 1], 0.0))
    return float(2 * norm.sf(abs(b[1] / se))) if se > 0 else None


def bh(p):
    p = np.asarray([np.nan if v is None else v for v in p], float); q = np.full(len(p), np.nan); ok = np.isfinite(p)
    if ok.any():
        v = p[ok]; o = np.argsort(v); r = v[o] * ok.sum() / np.arange(1, ok.sum() + 1)
        r = np.minimum.accumulate(r[::-1])[::-1]; qq = np.empty_like(v); qq[o] = np.minimum(r, 1.0); q[ok] = qq
    return q


def clopper_pearson(k, n, a=0.05):
    if n == 0: return (None, None)
    return (float(Beta.ppf(a / 2, k, n - k + 1)) if k > 0 else 0.0, float(Beta.ppf(1 - a / 2, k + 1, n - k)) if k < n else 1.0)


def smd_table(cols, X, g, ref, pid, boot_rows=None, half=None):
    """one SMD table (class g vs reference ref) over columns of the frame X: SMD, cluster p, BH q, and the SMD in each dev half."""
    rows = []
    for c in cols:
        x = pd.to_numeric(X[c], errors="coerce").to_numpy(float)
        r = dict(variable=c, n_class=int(g.sum()), n_ref=int(ref.sum()), smd=smd(x, g, ref), p=cluster_p(x, g, ref, pid))
        if half is not None: r["smd_halves"] = [smd(x, g & (half == k), ref & (half == k)) for k in (0, 1)]
        rows.append(r)
    q = bh([r["p"] for r in rows])
    for r, v in zip(rows, q): r["q"] = None if not np.isfinite(v) else float(v)
    return rows


# ------------------------------------------------------------------ decomposition outputs
def primary_arm(res_dir, tag="dev", K=64):
    """protocol 9.5: the valid arm with the most named, replicated families; tie -> simpler arm (raw, pca, ica, nmf, kmeans, sae)."""
    rows = []
    for arm in C.ARMS:
        p = Path(res_dir) / f"s4_decomp_{tag}_{arm}_K{K}.json"
        if p.exists():
            r = json.loads(p.read_text()); rows.append(dict(arm=arm, valid=bool(r.get("valid")), named_replicated=int(r.get("audit_yield_named_replicated", 0)),
                                                         V1=r["V1"]["pass_"], V2=r["V2"]["pass_"], V3=r["V3"]["pass_"], V4=r["V4"]["pass_"]))
    valid = [r for r in rows if r["valid"]]
    best = max(valid, key=lambda r: (r["named_replicated"], -C.SIMPLE_ORDER[r["arm"]]))["arm"] if valid else None
    return best, rows


def contrib(tag, arm, K=64):
    """group contributions G_g (t1_*, t6_*) and family activations (family_k) of an arm, keyed by series_uid; plus the family table."""
    z = np.load(DATA / f"s4_contrib_{tag}_{arm}_K{K}.npz", allow_pickle=True)
    df = pd.DataFrame({k: z[k] for k in z.files if k != "series_uid"}); df.insert(0, "series_uid", z["series_uid"])
    return df


def family_table(res_dir, tag, arm, K=64):
    p = Path(res_dir) / f"s4_families_{tag}_{arm}_K{K}.csv"
    return pd.read_csv(p) if p.exists() and p.stat().st_size > 2 else pd.DataFrame(columns=["family", "label"])


def load_arm(tag, arm, K=64):
    """the seed-0 arms (one per member) and the families saved by s4_decomp.py."""
    import pickle
    obj = pickle.load(open(DATA / "arms" / f"arms_{tag}_{arm}_K{K}.pkl", "rb")); return obj["arms"], obj["families"]


def split_by_label(Hh, arms, fams, lab_of, heads, t):
    """exact split of lbar_t for rows with hidden vectors Hh (n, 5, 512), encoded with the given (frozen) arms: dict term -> (n,),
    terms = family labels (N, B, D, I, T, mixed, unnamed), 'unreplicated', 'intercept', 'residual'; the terms sum to lbar_t.
    Same mapping as s4_decomp.py."""
    fam_of = [dict() for _ in range(5)]
    for k, (fam, sg) in enumerate(fams):
        for m, f in fam.items(): fam_of[m][f] = k
    comp = {}
    for m in range(5):
        A = arms[m].encode(Hh[:, m]); ic, ct, rs = C.contributions(Hh[:, m], A, arms[m], heads[m], t)
        comp["intercept"] = comp.get("intercept", 0) + ic / 5; comp["residual"] = comp.get("residual", 0) + rs / 5
        for i in range(ct.shape[1]):
            key = lab_of.get(fam_of[m][i], "unreplicated") if i in fam_of[m] else "unreplicated"
            comp[key] = comp.get(key, 0) + ct[:, i] / 5
    return comp


def variables(E, Cn=None, labels=None, t=1):
    """the variables compared between classes (Q2, U2, U3): every I and T variable (object columns one-hot), and, with an arm,
    every group term G_g of lbar_t and every family activation. Returns (frame aligned to E, dict column -> kind I/T/G/family)."""
    G = D.groups(E); cols, kind = {}, {}
    for g in ("I", "T"):
        for c in G[g]:
            v = E[c]
            if not pd.api.types.is_numeric_dtype(v):   # text columns (pandas 3 'str' dtype) -> one-hot
                for lev, d in pd.get_dummies(v.fillna("NA"), prefix=c, dtype=float).items(): cols[lev] = d.to_numpy(); kind[lev] = g
            else: cols[c] = pd.to_numeric(v, errors="coerce").to_numpy(float); kind[c] = g
    if Cn is not None:
        M = E[["series_uid"]].merge(Cn, on="series_uid", how="left")
        for c in Cn.columns:
            if c.startswith(f"t{t}_"): cols[f"G_{c[len(f't{t}_'):]}"] = M[c].to_numpy(float); kind[f"G_{c[len(f't{t}_'):]}"] = "G"
            elif c.startswith("family_"):
                k = int(c.split("_")[1]); nm = f"fam{k}_{(labels or {}).get(k, '?')}"; cols[nm] = M[c].to_numpy(float); kind[nm] = "family"
    return pd.DataFrame(cols, index=E.index), kind


# ------------------------------------------------------------------ Sybil's calibrator (numpy copy, as s2_pilot_checks.calibrate)
def calibrate(cal, mean_prob):
    """mean_prob (n, 6) -> calibrated (n, 6): per year, mean over sub-calibrators of interp(clip(x * coef + b))."""
    mp = np.asarray(mean_prob, float); out = np.zeros_like(mp)
    for t in range(6):
        vals = []
        for c in cal[f"Year{t + 1}"]:
            T = mp[:, [t]] @ np.array(c["coef"]) + np.array(c["intercept"])
            T = np.clip(T, c["x_min"] if c["x_min"] is not None else -np.inf, c["x_max"] if c["x_max"] is not None else np.inf)
            vals.append(np.interp(T.ravel(), np.array(c["x0"]), np.array(c["y0"])))
        out[:, t] = np.mean(vals, 0)
    return out


# ------------------------------------------------------------------ candidates for gate 9.8
def candidate(cid, source, statistic, population, direction, null, ci, halves_est, cnt, feature_based=False, partly_seen=False,
              qualification=None, note=""):
    """direction: '>' or '<' (stated), or '!=' (two-sided: the dev sign is the direction). ci: dict(est, lo, hi)."""
    return dict(id=cid, source=source, statistic=statistic, population=population, direction=direction, null=null,
                est=ci.get("est"), lo=ci.get("lo"), hi=ci.get("hi"), half_a=halves_est[0], half_b=halves_est[1], counts=cnt,
                feature_based=feature_based, partly_seen=partly_seen, qualification=qualification, note=note)


def write(out_dir, name, res):
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / name).write_text(json.dumps(res, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
