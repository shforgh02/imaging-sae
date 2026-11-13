"""Lung L2, step S4 core (docs/LUNG_L2_PROTOCOL.md sections 9.1, 9.2, 9.4, 9.5): Sybil's head, exact contributions, decomposition arms,
families across members, validity marks. Pure numpy / sklearn / torch (the SAE from imgsae/imgsae/sae.py).

Conventions: H is (n, 5, 512) post-ReLU hidden vectors; heads[m] has the member's hazard_fc / base_hazard_fc weights.
A decomposition of member m works in a space h = off + sd * (c + A @ D) (off = dev mean for centred arms, 0 for NMF), so every arm
gives an exact split  logit_{m,t} = intercept + sum_i contrib_i + residual  with the exam's own hazard gating.
Specification detail (logged): contributions and V1 use the seed-0 fit of a seeded arm; V2 uses the consensus of seeds 0-4 against 10-14.
"""
import sys

import numpy as np
from scipy.optimize import linear_sum_assignment

sys.path.insert(0, r"D:\Shayan\imgsae")
K_DEFAULT = 64
ARMS = ("raw", "pca", "ica", "nmf", "kmeans", "sae")
SIMPLE_ORDER = {a: i for i, a in enumerate(ARMS)}      # tie-break order of protocol 9.5 (simpler first)


# ------------------------------------------------------------------ head
def load_heads(path):
    z = np.load(path)
    return [{k: z[f"m{i}_{k}"].astype(np.float64) for k in ("hazard_fc_W", "hazard_fc_b", "base_hazard_fc_W", "base_hazard_fc_b")} for i in range(5)]


def head_logits(h, H):
    """h (n, 512) of one member -> (logits (n, 6), gate (n, 6))."""
    h = np.asarray(h, np.float64)
    raw = h @ H["hazard_fc_W"].T + H["hazard_fc_b"]
    base = h @ H["base_hazard_fc_W"].T + H["base_hazard_fc_b"]
    return base + np.cumsum(np.maximum(raw, 0), 1), raw > 0


def eff_weights(gate, H, t):
    """effective weight (n, 512) and bias (n,) of year t (1..6) given the gating (n, 6)."""
    g = gate[:, :t].astype(np.float64)
    w = H["base_hazard_fc_W"][0][None, :] + g @ H["hazard_fc_W"][:t]
    b = H["base_hazard_fc_b"][0] + g @ H["hazard_fc_b"][:t]
    return w, b


# ------------------------------------------------------------------ arms
class Arm:
    """fit on (n, d) h of one member; .encode(h) -> A (n, K); .recon(A) -> h_hat; decoder directions in h space: .dirs (K, d)."""

    def __init__(self, kind, K=K_DEFAULT, seed=0, device="cpu"):
        self.kind, self.K, self.seed, self.device = kind, K, seed, device

    def fit(self, h, w_ref=None):
        h = np.asarray(h, np.float64); self.mu = h.mean(0); sd = h.std(0)
        self.live = sd >= 1e-6; self.sd = np.where(self.live, sd, 1.0)
        Z = ((h - self.mu) / self.sd)[:, self.live]
        d, K = Z.shape[1], self.K
        if self.kind == "raw":   # the K units with the largest variance of contribution to the 6-year logit (label-free)
            score = np.abs(w_ref[self.live]) * self.sd[self.live]
            self.sel = np.argsort(-score)[:K]; self.off, self.c = self.mu, np.zeros(d)
            self.D = np.eye(d)[self.sel]
        elif self.kind == "pca":
            from sklearn.decomposition import PCA
            p = PCA(K, random_state=self.seed).fit(Z); self.p = p; self.D = p.components_; self.c = p.mean_; self.off = self.mu
        elif self.kind == "ica":
            from sklearn.decomposition import FastICA
            ic = FastICA(K, random_state=self.seed, max_iter=1000, whiten="unit-variance").fit(Z)
            S = ic.transform(Z); sk = np.sign(((S - S.mean(0)) ** 3).mean(0)); sk[sk == 0] = 1   # sign convention: positive skew
            self.ic, self.flip = ic, sk; self.D = (ic.mixing_ * sk).T; self.c = ic.mean_; self.off = self.mu
        elif self.kind == "nmf":
            from sklearn.decomposition import NMF
            Zn = np.maximum(h[:, self.live] / self.sd[self.live], 0)
            nm = NMF(K, init="nndsvda", random_state=self.seed, max_iter=800).fit(Zn); self.nm = nm
            self.D = nm.components_; self.c = np.zeros(d); self.off = np.zeros_like(self.mu)
        elif self.kind == "kmeans":
            from sklearn.cluster import KMeans
            km = KMeans(K, random_state=self.seed, n_init=3).fit(Z); self.km = km; self.D = km.cluster_centers_; self.c = np.zeros(d); self.off = self.mu
        elif self.kind == "sae":
            from imgsae import sae
            m, _ = sae.fit(Z.astype(np.float32), dict(M=K, k=max(1, K // 16), seed=self.seed, device=self.device, matryoshka=True))
            self.m = m; self.D = m.D.detach().numpy().astype(np.float64); self.c = m.b_dec.detach().numpy().astype(np.float64); self.off = self.mu
        else:
            raise ValueError(self.kind)
        return self

    def _z(self, h):
        return ((np.asarray(h, np.float64) - self.mu) / self.sd)[:, self.live]

    def encode(self, h):
        if self.kind == "raw": return self._z(h)[:, self.sel]
        if self.kind == "pca": return self.p.transform(self._z(h))
        if self.kind == "ica": return self.ic.transform(self._z(h)) * self.flip
        if self.kind == "nmf": return self.nm.transform(np.maximum(np.asarray(h, np.float64)[:, self.live] / self.sd[self.live], 0))
        if self.kind == "kmeans":
            lab = self.km.predict(self._z(h)); A = np.zeros((len(lab), self.K)); A[np.arange(len(lab)), lab] = 1; return A
        if self.kind == "sae":
            from imgsae import sae
            return sae.encode(self.m, self._z(h).astype(np.float32)).astype(np.float64)

    def _full(self, M):   # (., d_live) -> (., 512) in h units (scaled), zeros on dead dims
        out = np.zeros((M.shape[0], len(self.mu))); out[:, self.live] = M * self.sd[self.live]; return out

    @property
    def dirs(self):
        return self._full(self.D)

    def recon(self, A):
        return self.off + self._full(self.c[None, :] + A @ self.D)


def contributions(h, A, arm, H, t):
    """exact split of member logits at year t: intercept (n,), contrib (n, K), residual (n,); sums to the logit."""
    _, gate = head_logits(h, H)
    w, b = eff_weights(gate, H, t)
    wd = w @ arm.dirs.T                                     # (n, K): w_eff . d_i
    contrib = A * wd
    intercept = b + (w * (arm.off + arm._full(arm.c[None, :])[0])).sum(1)
    resid = (w * (np.asarray(h, np.float64) - arm.recon(A))).sum(1)
    return intercept, contrib, resid


# ------------------------------------------------------------------ matching
def zscore(A):
    A = np.asarray(A, np.float64); return (A - A.mean(0)) / np.maximum(A.std(0), 1e-12)


def alive(A, thr=1e-3):
    return (np.asarray(A) != 0).mean(0) >= thr


def match(Aa, Ab):
    """Hungarian match by activation correlation; returns (rows, cols, r) over alive features."""
    ia, ib = np.flatnonzero(alive(Aa)), np.flatnonzero(alive(Ab))
    C = zscore(Aa[:, ia]).T @ zscore(Ab[:, ib]) / len(Aa)
    r, c = linear_sum_assignment(-C); return ia[r], ib[c], C[r, c]


def act_match(Aa, Ab, r_thr=0.7):
    """share of matched features at r >= r_thr (of the smaller alive set) and median matched r."""
    _, _, v = match(Aa, Ab)
    n = min(alive(Aa).sum(), alive(Ab).sum())
    return (float((v >= r_thr).sum() / n) if n else 0.0), (float(np.median(v)) if len(v) else 0.0)


def families(As, r_thr=0.7, min_members=3):
    """symmetric merge across members (as imgsae.sae.consensus_codes_cl, but returning membership): list of {member: feature index}."""
    S = len(As); Zs = [zscore(A) for A in As]; idx = [np.flatnonzero(alive(A)) for A in As]
    C, E = {}, []
    for i in range(S):
        for j in range(i + 1, S):
            C[i, j] = Zs[i][:, idx[i]].T @ Zs[j][:, idx[j]] / len(Zs[i]); r, c = linear_sum_assignment(-C[i, j])
            E += [(float(v), (i, int(idx[i][a])), (j, int(idx[j][b]))) for a, b, v in zip(r, c, C[i, j][r, c]) if v >= r_thr]
    pos = {(m, int(f)): k for m in range(S) for k, f in enumerate(idx[m])}

    def corr(u, v):
        (mu, fu), (mv, fv) = u, v
        return C[mu, mv][pos[u], pos[v]] if mu < mv else C[mv, mu][pos[v], pos[u]]
    gid = {n: n for n in pos}; grp = {n: [n] for n in pos}
    for v, a, b in sorted(E, key=lambda e: -e[0]):
        ga, gb = gid[a], gid[b]
        if ga == gb: continue
        Ga, Gb = grp[ga], grp[gb]
        if {m for m, _ in Ga} & {m for m, _ in Gb} or np.mean([corr(u, w) for u in Ga for w in Gb]) < r_thr: continue
        grp[ga] = Ga + Gb
        for n in Gb: gid[n] = ga
        del grp[gb]
    return [dict(G) for G in grp.values() if len(G) >= min_members]


def family_activation(As, fam):
    return np.mean([zscore(As[m][:, [f]])[:, 0] for m, f in fam.items()], 0)


# ------------------------------------------------------------------ validity V1 (function kept)
def v1_fold(h_tr, h_te, H, kind, K, seed, w_ref=None, device="cpu"):
    """fit on training rows of one member, reconstruct held-out rows; returns held-out logits from h and from h_hat (n_te, 6)."""
    arm = Arm(kind, K, seed, device).fit(h_tr, w_ref=w_ref)
    hh = arm.recon(arm.encode(h_te))
    return head_logits(h_te, H)[0], head_logits(hh, H)[0]
