"""Stage 1a (exploratory, 150 development scans): shared code. Protocol docs/STAGE1A_PROTOCOL.md (fixed before running).
Reuses Stage A code unchanged:
  p1b_sanity/common   Ctx (production halves, eval rows, seeds), evaluate (production ladder, both chimera rules, area at 425 features)
  p1b_sanity/a1_probe_ladder.build_tasks   the T1b / T3 token sets (k = 1 probing, T6)
  scripts/p1_fit      Model (SAE, soft k-means, raw channels, sparse varimax), feature_table; theta and shortcut rules copied 1:1
New here: FastICA and dictionary-learning models, the supervised reference ('oracle'), per-feature metrics (T4 precision, T5 theta,
T8 shortcut share), k = 1 sparse probing (T6), dense reference probes for T6.
"""
from __future__ import annotations

import copy
import json
import os
import sys
import time
import warnings
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent; SAN = HERE.parent / "p1b_sanity"; sys.path.insert(0, str(SAN))
import common as cm  # noqa: E402  (also puts the package, scripts/ and p1_checks/ on sys.path)
from common import A, F, P1, ladder, sae  # noqa: E402

RES = HERE / "results"; LOGS = HERE / "logs"; TAB = RES / "tables"
for _d in (RES, LOGS, TAB): _d.mkdir(exist_ok=True)
TASKS = ("T1b", "T3_vert", "T3_lobe")
ROWS_KEYS = ["lab", "scan", "gidx"] + [f"prep_{p}_{q}" for p in ("ctfm", "null", "ref") for q in ("mu", "sc")]
log, dump = cm.log, cm.dump


# ------------------------------------------------------------------ method registry (fixed in the protocol)
def methods():
    """every Stage 1a method. family = the tuning family; within a family the config is chosen on rep 0 (protocol section 3)."""
    M = {}
    for Mk in (425, 1024, 2048):
        for L0 in (1, 6, 27): M[f"km_M{Mk}_L{L0}"] = dict(meth="soft_kmeans", inp="X_ctfm", L0=L0, cfg=dict(M=Mk), family="kmeans")
    for L0 in (6, 27):
        M[f"ica_L{L0}"] = dict(meth="ica", inp="X_ctfm", L0=L0, cfg=dict(n_fit=100000), family="ica")
        M[f"raw_L{L0}"] = dict(meth="raw_sparse", inp="X_ctfm", L0=L0, cfg=dict(M=425), family="raw")
        M[f"svx_L{L0}"] = dict(meth="sparse_varimax", inp="X_ctfm", L0=L0, cfg=dict(M=425), family="svx")
    for atoms, k in DL_CONFIGS: M[f"dl_A{atoms}_k{k}"] = dict(meth="dl", inp="X_ctfm", L0=k, cfg=dict(atoms=atoms, k=k, n_fit=100000), family="dl")
    M["oracle"] = dict(meth="oracle", inp="X_ctfm", family="oracle")
    sae_cfg = dict(M=1024, k=6, steps=12000)  # A2's best single config
    M["sae_M1024_k6_s12000"] = dict(meth="sae_single", inp="X_ctfm", cfg=sae_cfg, family="sae", gpu=True)
    M["cons_M1024_k6_s12000"] = dict(meth="sae_cons", inp="X_ctfm", cfg=sae_cfg, family="sae", gpu=True)
    M["nullsae_M1024_k6_s12000"] = dict(meth="sae_single", inp="X_null", cfg=sae_cfg, family="null", gpu=True)
    M["physsae_M1024_k6_s12000"] = dict(meth="sae_single", inp="R3", cfg=sae_cfg, family="null", gpu=True)
    return M


DL_CONFIGS = [(1024, 6), (2048, 6), (1024, 27)]
SHARE = ("soft_kmeans", "raw_sparse", "sparse_varimax", "ica")  # fits that do not depend on L0 are shared across L0 values


# ------------------------------------------------------------------ data
def load_array(key):
    """one array of data/p1/rows.npz, or of rows_extra.npz (the cloud volume keeps X_null there)."""
    z = np.load(P1 / "rows.npz")
    if key in z.files: return z[key]
    return np.load(P1 / "rows_extra.npz")[key]


def load_input(inp, R, C):
    """input matrix + its perturbation inputs (same as p1b_sanity/a3_decomp_fair.load_input, with the rows_extra fallback)."""
    r3p = None
    if inp == "R3":
        ref, pos = cm.refpos(C); X, mu, sc = A.prep(cm.raw_ref_sets(ref, pos, cm.zrel(R["gidx"], R["scan"]))["R3"]); r3p = (mu, sc); del ref, pos
    else: X = load_array(inp)
    pert_in = cm.load_perturb_all(C, R, r3p)
    for d in pert_in.values():
        for k in [k for k in d if k not in ("rows", inp)]: d.pop(k)
    return X, pert_in


def load_tasks(path=None):
    """T6 token sets written by s1a_run.py --step tasks (rows, y, classes, scored per task)."""
    z = np.load(path or RES / "s1a_tasks.npz", allow_pickle=False); meta = json.loads(str(z["meta"]))
    return {t: dict(rows=z[f"{t}_rows"], y=z[f"{t}_y"], classes=meta[t]["classes"], scored=meta[t]["scored"]) for t in meta}


# ------------------------------------------------------------------ new models (fit(X) -> self, encode(X) -> non-negative float32 codes)
class ICA:
    """FastICA with d components (whitened, unit-variance sources, fitted on n_fit random rows); codes = top-L0 of the split-signed sources."""

    def __init__(self, cfg, L0, seed): self.cfg, self.L0, self.seed = cfg, L0, seed

    def fit(self, X):
        from sklearn.decomposition import FastICA
        rng = np.random.default_rng(self.seed); sub = X[rng.choice(len(X), min(len(X), self.cfg["n_fit"]), replace=False)].astype(np.float64)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            self.ica = FastICA(n_components=X.shape[1], whiten="unit-variance", random_state=self.seed, max_iter=self.cfg.get("max_iter", 400), tol=1e-4).fit(sub)
        self.info = dict(n_iter=int(self.ica.n_iter_), converged=not any("converge" in str(x.message) for x in w)); return self

    def encode(self, X): return sae.topk_rows(sae.split_signed(self.ica.transform(np.asarray(X, np.float64))), self.L0)


def omp(Xc, D, k, chunk=8192):
    """batched orthogonal matching pursuit: for each row of Xc (centred, n x d) the k atoms of D (M x d, unit rows) chosen greedily by
    |correlation with the residual|, with least-squares coefficients on the chosen atoms. Returns (idx n x k, coef n x k)."""
    import torch
    Xc = torch.as_tensor(np.asarray(Xc, np.float32)); D = torch.as_tensor(np.asarray(D, np.float32)); G = D @ D.T; I_out, C_out = [], []
    for i in range(0, len(Xc), chunk):
        x = Xc[i:i + chunk]; m = len(x); DX = x @ D.T; idx = torch.zeros(m, k, dtype=torch.long); r = x; coef = None
        for s in range(k):
            c = (r @ D.T).abs()
            if s: c.scatter_(1, idx[:, :s], -1.0)
            idx[:, s] = c.argmax(1); I = idx[:, :s + 1]
            Gs = G[I[:, :, None], I[:, None, :]] + 1e-6 * torch.eye(s + 1)
            coef = torch.linalg.solve(Gs, DX.gather(1, I).unsqueeze(-1)).squeeze(-1)
            r = x - torch.einsum("ms,msd->md", coef, D[I])
        I_out.append(idx); C_out.append(coef)
    return torch.cat(I_out).numpy(), torch.cat(C_out).numpy()


class DL:
    """k-sparse dictionary learning: OMP coding with k non-zeros + MOD dictionary update (Engan et al. 1999), on rows centred by the fit
    mean, from the SAE's own initialisation (sae._init: k-means++ seeds of the centred rows, unit atoms). Atoms no row uses are re-seeded on
    high-residual rows. Codes = OMP with k non-zeros on the learned dictionary, split-signed (2 x atoms features, L0 = k).
    This is the L0-constrained objective of the TopK SAE solved per token, without the amortised encoder (protocol, amendment M5)."""

    def __init__(self, cfg, seed): self.cfg, self.seed, self.L0 = cfg, seed, cfg["k"]

    def fit(self, X):
        import torch
        rng = np.random.default_rng(self.seed); sub = np.asarray(X[rng.choice(len(X), min(len(X), self.cfg["n_fit"]), replace=False)], np.float32)
        M, k = self.cfg["atoms"], self.cfg["k"]; b, D = sae._init(sub, M, self.seed); self.b = b.astype(np.float32); Xc = sub - self.b
        Xt = torch.as_tensor(Xc); D = torch.as_tensor(D.astype(np.float32)); var = float((Xt ** 2).sum()); hist = []
        for it in range(self.cfg.get("iters", DL_ITERS)):
            idx, coef = omp(Xc, D.numpy(), k); idx, coef = torch.as_tensor(idx), torch.as_tensor(coef)
            A_ = torch.zeros(M, M); B_ = torch.zeros(M, Xt.shape[1])
            for s in range(k):
                B_.index_add_(0, idx[:, s], coef[:, s:s + 1] * Xt)
                for t in range(k): A_.index_put_((idx[:, s], idx[:, t]), coef[:, s] * coef[:, t], accumulate=True)
            rec = torch.zeros_like(Xt)
            for s in range(k): rec += coef[:, s:s + 1] * D[idx[:, s]]
            res = Xt - rec; r2 = 1 - float((res ** 2).sum()) / var; used = torch.bincount(idx.flatten(), minlength=M) > 0
            Dn = torch.linalg.solve(A_ + 1e-4 * torch.eye(M), B_)
            dead = (~used) | (Dn.norm(dim=1) < 1e-8); nd = int(dead.sum())
            if nd and it < self.cfg.get("iters", DL_ITERS) - 1:
                w = (res ** 2).sum(1); pick = torch.multinomial(w / w.sum(), nd, replacement=False, generator=torch.Generator().manual_seed(self.seed * 1000 + it))
                Dn[dead] = res[pick]
            D = Dn / Dn.norm(dim=1, keepdim=True).clamp_min(1e-9); hist.append(dict(it=it, r2=round(r2, 5), reseeded=nd))
        self.D = D.numpy(); self.info = dict(history=hist, r2_fit=hist[-1]["r2"]); return self

    def encode(self, X):
        idx, coef = omp(np.asarray(X, np.float32) - self.b, self.D, self.L0); Z = np.zeros((len(idx), len(self.D)), np.float32)
        np.put_along_axis(Z, idx, coef, 1); return sae.split_signed(Z)


DL_ITERS = 30


class Oracle:
    """supervised reference on the same embedding: multinomial logistic regression (C = 1, balanced; as p1_probe) trained on the fit half's
    labels, T1b caps (<= 2,000 core tokens per eligible concept, 20,000 'other'); features = class probabilities of the eligible concepts."""

    def __init__(self, ctx, seed): self.ctx, self.seed, self.L0 = ctx, seed, None

    def fit_rows(self, X, rows):
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        lab = self.ctx.R["lab"]; G, elig = self.ctx.G, self.ctx.elig; gi = [G.index(g) for g in elig]; rng = np.random.default_rng(self.seed)
        cap = lambda ii, c: ii if len(ii) <= c else np.sort(rng.choice(ii, c, replace=False))  # noqa: E731
        lr = lab[rows]; tr = np.sort(np.concatenate([cap(rows[lr == -1], 20000)] + [cap(rows[lr == g], 2000) for g in gi]))
        y = np.where(lab[tr] < 0, -1, lab[tr]); self.sc = StandardScaler().fit(X[tr])
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always"); self.m = LogisticRegression(C=1.0, max_iter=300, class_weight="balanced").fit(self.sc.transform(X[tr]), y)
        self.keep = [j for j, c in enumerate(self.m.classes_) if c >= 0]; self.info = dict(n_train=int(len(tr)), n_classes=len(self.m.classes_), warnings=len(w))
        return self

    def encode(self, X): return self.m.predict_proba(self.sc.transform(X))[:, self.keep].astype(np.float32)


def fit_pair(spec, ctx, X, dev="cpu", cache=None):
    """the replicate's two half models with the production seeds (rep * 7 + half index), as common.Ctx.fit."""
    meth, cfg, L0 = spec["meth"], spec.get("cfg", {}), spec.get("L0"); mods = {}
    for hi, h in enumerate("AB"):
        seed = ctx.rep * 7 + hi; rows = ctx.rows[h]; key = (meth, json.dumps(cfg, sort_keys=True), spec["inp"], ctx.rep, h)
        if cache is not None and key in cache: m = copy.copy(cache[key]); m.L0 = L0
        else:
            if meth in ("sae_single", "sae_cons"): m = F.Model(meth, dict(matryoshka=False, device=dev, rows_per_latent=None, **cfg), seed=seed).fit(X[rows])
            elif meth == "ica": m = ICA(cfg, L0, seed).fit(X[rows])
            elif meth == "dl": m = DL(cfg, seed).fit(X[rows])
            elif meth == "oracle": m = Oracle(ctx, seed).fit_rows(X, rows)
            else: m = F.Model(meth, cfg, L0=L0, seed=seed).fit(X[rows])
            if cache is not None and meth in SHARE: cache[key] = m
        mods[h] = m
    return mods


# ------------------------------------------------------------------ per-feature metrics (T4, T5, T8)
def table_metrics(tables):
    """pooled over the two half models. T4 precision = share of V0 features with v >= 0.7; T5 theta exactly as scripts/p1_fit.py
    (valid = sel >= .7, not chimeric, gated, r_pert >= .7, V0; predictor = twin score); T8 shortcut share as p1_fit (reproducible = V0 and t >= .7)."""
    T = {k: np.concatenate([tables["A"][k], tables["B"][k]]) for k in tables["A"]}; v0 = T["v0"]; out = {}
    for rule, vk, chk in (("neutral", "v", "chimeric"), ("orig", "v_orig", "chimeric_orig")):
        v = np.nan_to_num(T[vk], nan=0.0)
        y = (T["sel"] >= .7) & ~T[chk] & T["gated"] & (np.nan_to_num(T["r_pert"], nan=-1) >= .7) & v0
        th = ladder.theta(np.where(v0, T["t"], np.nan), y, freq=np.maximum(T["freq"], 1e-6), mag=np.maximum(T["mag"], 1e-6))
        out[rule] = dict(precision07=float((v[v0] >= .7).mean()) if v0.any() else float("nan"), n_valid07=int((v >= .7).sum()), theta=th)
    out.update(n_feat=int(len(v0)), n_v0=int(v0.sum()), share_other_v0=float((T["concept"][v0] == "other").mean()) if v0.any() else float("nan"))
    rep_ = v0 & (T["t"] >= .7)
    out["shortcut"] = dict(n_reproducible=int(rep_.sum()), share=float(np.mean((T["acq_auc"][rep_] >= .8) | (np.nan_to_num(T["r_shift"][rep_], nan=1) < .5))) if rep_.any() else float("nan"))
    return out


def save_tables(name, rep, tables):
    import pandas as pd
    for h, T in tables.items():
        pd.DataFrame({k: np.asarray(v) for k, v in T.items()}).to_csv(TAB / f"{name}_rep{rep}_{h}.csv.gz", index=False, float_format="%.5g")


# ------------------------------------------------------------------ T6: k = 1 sparse probing
def _auc_cols(Rk, y):
    """one-vs-rest AUROC of every column from column ranks Rk (ties averaged) and a boolean label."""
    n1 = int(y.sum()); n0 = len(y) - n1
    if n1 == 0 or n0 == 0: return np.full(Rk.shape[1], np.nan)
    return (Rk[y].sum(0, dtype=np.float64) - n1 * (n1 + 1) / 2) / (n1 * n0)


def _ranks(Z, chunk=256):
    """column ranks (ties averaged) as float32, computed in column chunks to limit memory; ranks are multiples of 0.5 below 2**24,
    so float32 holds them exactly and the AUROCs equal the float64 ones."""
    from scipy.stats import rankdata
    R = np.empty(Z.shape, np.float32)
    for j in range(0, Z.shape[1], chunk): R[:, j:j + chunk] = rankdata(Z[:, j:j + chunk], axis=0)
    return R


def k1_probe(mods, X, ctx, tasks, n_match=425, n_draw=20):
    """per task and class: the single feature with the highest AUROC (positive direction) on the fit half's task tokens, tested on the other
    half's task tokens with the same model; averaged over the two directions (A->B, B->A). 'matched': the same, choosing among n_match
    random features (n_draw draws), so dictionaries of different size compete with the same number of candidates."""
    scan = ctx.R["scan"]; rng = np.random.default_rng(100 + ctx.rep); out = {}
    for tn, t in tasks.items():
        rows, y, classes, scored = t["rows"], t["y"], t["classes"], t["scored"]; inA = ctx.hA[scan[rows]]
        per = {c: [] for c in scored}; per_m = {c: [] for c in scored}; feat = {c: [] for c in scored}
        for h in "AB":
            fm = inA if h == "A" else ~inA
            Zs = mods[h].encode(X[rows[fm]]); Rs = _ranks(Zs); del Zs
            Zt = mods[h].encode(X[rows[~fm]]); Rt = _ranks(Zt); del Zt
            Fn = Rs.shape[1]; draws = [rng.choice(Fn, n_match, replace=False) for _ in range(n_draw)] if Fn > n_match else None
            for c in scored:
                ci = classes.index(c); a_s, a_t = _auc_cols(Rs, y[fm] == ci), _auc_cols(Rt, y[~fm] == ci)
                if not np.isfinite(a_s).any() or not np.isfinite(a_t).any(): continue
                f = int(np.nanargmax(a_s)); per[c].append(float(a_t[f])); feat[c].append(f)
                per_m[c].append(float(np.mean([a_t[d[np.nanargmax(a_s[d])]] for d in draws])) if draws else float(a_t[f]))
            del Rs, Rt
        auc = {c: float(np.mean(v)) if v else float("nan") for c, v in per.items()}; aum = {c: float(np.mean(v)) if v else float("nan") for c, v in per_m.items()}
        out[tn] = dict(auc=auc, auc_matched=aum, feature=feat, median=float(np.nanmedian(list(auc.values()))), median_matched=float(np.nanmedian(list(aum.values()))))
    return out


def dense_probe(Xs, ctx, tasks):
    """T6 references: dense multinomial probe (as p1_probe: standardised, C = 1, balanced) trained on the fit half's task tokens and tested on
    the other half's, per class AUROC averaged over the two directions."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    scan = ctx.R["scan"]; out = {}
    for tn, t in tasks.items():
        rows, y, classes, scored = t["rows"], t["y"], t["classes"], t["scored"]; inA = ctx.hA[scan[rows]]; per = {c: [] for c in scored}
        for h in "AB":
            fm = inA if h == "A" else ~inA; Xtr, Xte = Xs[rows[fm]], Xs[rows[~fm]]; sc = StandardScaler().fit(Xtr)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore"); m = LogisticRegression(C=1.0, max_iter=300, class_weight="balanced").fit(sc.transform(Xtr), y[fm])
            P = m.predict_proba(sc.transform(Xte)); cl = list(m.classes_)
            for c in scored:
                ci = classes.index(c)
                if ci in cl: per[c].append(ladder.auroc(P[:, cl.index(ci)], y[~fm] == ci))
        auc = {c: float(np.nanmean(v)) if v else float("nan") for c, v in per.items()}; out[tn] = dict(auc=auc, median=float(np.nanmedian(list(auc.values()))))
    return out


# ------------------------------------------------------------------ one (method, rep) job
def run_job(name, spec, rep, R, C, Gt, X, pert_in, tasks, dev="cpu", cache=None):
    """fit -> production ladder (both rules, tables kept) -> T4/T5/T8 -> T6. Returns a JSON-safe dict and the per-feature tables."""
    ctx = cm.Ctx(rep, R, C, Gt, pert_in); t0 = time.time(); mods = fit_pair(spec, ctx, X, dev, cache); fit_min = (time.time() - t0) / 60
    t1 = time.time(); ev, tables = cm.evaluate(mods, X, spec["inp"], ctx, keep_tables=True); ev_min = (time.time() - t1) / 60
    t2 = time.time(); k1 = k1_probe(mods, X, ctx, tasks); k1_min = (time.time() - t2) / 60
    info = {h: getattr(m, "info", None) for h, m in mods.items()}
    r = dict(method=name, rep=rep, spec=spec, fit_min=fit_min, eval_min=ev_min, k1_min=k1_min, fit_info=info, **ev, feat=table_metrics(tables), k1=k1)
    return json.loads(json.dumps(r, default=lambda o: o.tolist() if isinstance(o, np.ndarray) else (bool(o) if isinstance(o, np.bool_) else float(o)))), tables
