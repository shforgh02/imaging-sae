"""Stage 1a, deviation M7 diagnostic (label-free; after G1): is the DL instability in the dictionary or in the per-token coding?
Uses the saved nonnegative DL dictionaries of rep 0 (half A = seed 0, half B = seed 1; results/dl_dicts/) and 20,000 random CT-FM tokens.
No labels, no ladder. Compares two encoders on the same dictionaries:
  omp        nonnegative OMP with k non-zeros (what the DL rows use)
  threshold  top-k of ReLU(D (x - b)), no refit (the tied linear encoder of a TopK SAE)
Measures: atom match between halves (max cosine), code match between halves (max Pearson r per active feature, as the twin score),
code stability under small input noise (0.1 SD per dimension), reconstruction R2. -> results/s1a_dl_diag.json
usage (from v2_ct/): ..\\..\\.venv\\Scripts\\python s1a_dl_diag.py [--cfg dl_nn_A1024_k6]
"""
import argparse
import json

import numpy as np

import s1a_lib as L


def codes(X, D, b, k, how):
    Xc = X - b
    if how == "omp":
        idx, coef = L.omp(Xc, D, k, nonneg=True); Z = np.zeros((len(X), len(D)), np.float32); np.put_along_axis(Z, idx, coef, 1); return Z
    A = np.maximum(Xc @ D.T, 0); idx = np.argpartition(-A, k, 1)[:, :k]; Z = np.zeros_like(A); np.put_along_axis(Z, idx, np.take_along_axis(A, idx, 1), 1); return Z


def corr_cols(Za, Zb):
    a = Za - Za.mean(0); b = Zb - Zb.mean(0); return (a.T @ b) / np.outer(np.linalg.norm(a, axis=0), np.linalg.norm(b, axis=0)).clip(1e-12)


def r2(X, Z, D, b): return float(1 - ((X - b - Z @ D) ** 2).sum() / ((X - b) ** 2).sum())


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--cfg", default="dl_nn_A1024_k6"); ap.add_argument("--n", type=int, default=20000); a = ap.parse_args()
    k = int(a.cfg.split("_k")[-1]); dd = L.RES / "dl_dicts"; DA, DB = (np.load(dd / f"{a.cfg}_seed{s}.npz") for s in (0, 1))
    X = L.load_array("X_ctfm"); rng = np.random.default_rng(0); X = np.asarray(X[np.sort(rng.choice(len(X), a.n, replace=False))], np.float32)
    Xn = X + 0.1 * X.std(0) * rng.standard_normal(X.shape).astype(np.float32)
    cos = DA["D"] @ DB["D"].T; am = cos.max(1); out = dict(cfg=a.cfg, n_tokens=a.n, atom_match=dict(median=float(np.median(am)), share_ge_09=float((am >= .9).mean()), share_ge_07=float((am >= .7).mean())))
    for how in ("omp", "threshold"):
        ZA, ZB, ZAn = codes(X, DA["D"], DA["b"], k, how), codes(X, DB["D"], DB["b"], k, how), codes(Xn, DA["D"], DA["b"], k, how)
        act = (ZA > 0).sum(0) >= 20; actB = (ZB > 0).sum(0) >= 20
        tw = corr_cols(ZA[:, act], ZB[:, actB]).max(1); st = np.array([np.corrcoef(ZA[:, j], ZAn[:, j])[0, 1] for j in np.flatnonzero(act)])
        out[how] = dict(r2_A=r2(X, ZA, DA["D"], DA["b"]), n_active_A=int(act.sum()), twin_median=float(np.median(tw)), twin_share_ge_07=float((tw >= .7).mean()),
                        noise_stability_median=float(np.nanmedian(st)))
        L.log(f"{a.cfg} {how}: R2 {out[how]['r2_A']:.3f} | twin median {out[how]['twin_median']:.3f}, share >= 0.7 {out[how]['twin_share_ge_07']:.3f} | noise stability median {out[how]['noise_stability_median']:.3f} | active {out[how]['n_active_A']}")
    L.log(f"{a.cfg} atom match A->B: median max cosine {out['atom_match']['median']:.3f}, share >= 0.9 {out['atom_match']['share_ge_09']:.3f}, >= 0.7 {out['atom_match']['share_ge_07']:.3f}")
    p = L.RES / "s1a_dl_diag.json"; res = json.load(open(p)) if p.exists() else {}; res[a.cfg] = out; L.dump(res, p)


if __name__ == "__main__":
    main()
