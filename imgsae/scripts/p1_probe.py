"""Phase 1 gate S: decodability of concepts from the dense CT-FM embedding vs the reference (HU histogram + texture + 3x3x3 context + position).
Token concepts: eligible groups (one-vs-rest on scored tokens = core or 'other'), multinomial logistic, patient-grouped 5-fold CV.
Scan concepts (scan-mean embedding): manufacturer, institute I, kVp >= 120, contrast, pathology tumour vs none, kidney cyst; HU-derived (liver HU < 40,
L1 HU < 110, LAA-950 > 5 %). AUROC with patient-cluster bootstrap CI; gated if lower bound >= 0.70; beyond-HU if dense - ref dAUROC >= 0.05 with
lower bound > 0 (token concepts). Writes data/p1/gates.json. usage: python scripts/p1_probe.py [--max-tokens 60000]
"""
import argparse
import os
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from imgsae import ladder  # noqa: E402

P1 = Path(os.environ.get("IMGSAE_P1", ROOT / "data/p1"))


def oof_proba(X, y, groups, C=1.0, seed=0):
    P = np.zeros((len(y), int(y.max()) + 1))
    for tr, te in GroupKFold(5).split(X, y, groups):
        sc = StandardScaler().fit(X[tr]); m = LogisticRegression(C=C, max_iter=300, class_weight="balanced").fit(sc.transform(X[tr]), y[tr])
        P[np.ix_(te, m.classes_)] = m.predict_proba(sc.transform(X[te]))
    return P


def boot_auc(s1, s2, y, g, B=500, seed=0):
    """AUROC of s1, s2 and their difference with patient-cluster bootstrap 95% CIs."""
    rng = np.random.default_rng(seed); ug, inv = np.unique(g, return_inverse=True); idx = [np.flatnonzero(inv == j) for j in range(len(ug))]
    a1, a2 = ladder.auroc(s1, y), ladder.auroc(s2, y) if s2 is not None else np.nan; bs = []
    for _ in range(B):
        ii = np.concatenate([idx[j] for j in rng.integers(0, len(ug), len(ug))])
        if y[ii].all() or not y[ii].any(): continue
        b1 = ladder.auroc(s1[ii], y[ii]); b2 = ladder.auroc(s2[ii], y[ii]) if s2 is not None else np.nan; bs.append((b1, b2, b1 - b2))
    bs = np.array(bs); q = lambda c: (float(np.nanquantile(bs[:, c], .025)), float(np.nanquantile(bs[:, c], .975)))  # noqa: E731
    return dict(auc=a1, ci=q(0), auc_ref=a2, ci_ref=q(1), diff=a1 - a2, ci_diff=q(2))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--max-tokens", type=int, default=60000); a = ap.parse_args()
    R = np.load(P1 / "rows.npz"); C = json.load(open(P1 / "concepts.json")); G = C["groups"]; elig = C["eligible"]
    lab, scan = R["lab"], R["scan"]; rng = np.random.default_rng(0)
    keep = np.flatnonzero((lab == -1) | np.isin(lab, [G.index(g) for g in elig]))
    if len(keep) > a.max_tokens: keep = np.sort(rng.choice(keep, a.max_tokens, replace=False))
    y = lab[keep].copy(); classes = sorted(set(y.tolist())); y = np.searchsorted(classes, y)
    Pd = oof_proba(R["X_ctfm"][keep], y, scan[keep]); Pr = oof_proba(R["X_ref"][keep], y, scan[keep]); tok = {}
    for ci, c in enumerate(classes):
        if c < 0: continue
        r = boot_auc(Pd[:, ci], Pr[:, ci], y == ci, scan[keep]); r["gated"] = r["ci"][0] >= .70
        r["beyond_hu"] = bool(r["gated"] and r["diff"] >= .05 and r["ci_diff"][0] > 0); r["cls"] = "path" if G[c] == "kidney_cyst" else "anat"; tok[G[c]] = r
    S = C["scans"]; ns = len(S); Xs = {k: np.stack([R[k][scan == i].astype(np.float32).mean(0) for i in range(ns)]) for k in ("X_ctfm", "X_ref", "X_null")}
    f = lambda key, fn: np.array([fn(s) for s in S], float)  # noqa: E731
    labels = dict(manufacturer_siemens=f("m", lambda s: s["manufacturer"].strip().lower() == "siemens"), institute_I=f("i", lambda s: s["institute"] == "I"),
                  kvp_ge120=f("k", lambda s: float(s["kvp"] or 0) >= 120), contrast=f("c", lambda s: s["contrast"]),
                  tumour=f("t", lambda s: 1.0 if s["pathology"] == "tumor" else (0.0 if s["pathology"] == "no_pathology" else np.nan)), kidney_cyst=f("y", lambda s: s["cyst"]),
                  steatosis=f("l", lambda s: s["liver_hu"] < 40 if np.isfinite(s["liver_hu"]) else np.nan), osteopenia=f("o", lambda s: s["l1_hu"] < 110 if np.isfinite(s["l1_hu"]) else np.nan),
                  emphysema=f("e", lambda s: s["laa950"] > .05 if np.isfinite(s["laa950"]) else np.nan))
    cls = dict(manufacturer_siemens="acq", institute_I="acq", kvp_ge120="acq", contrast="acq", tumour="path", kidney_cyst="path", steatosis="path_hu", osteopenia="path_hu", emphysema="path_hu")
    scn = {}
    for name, yy in labels.items():
        ok = np.isfinite(yy)
        if ok.sum() < 20 or yy[ok].min() == yy[ok].max() or min(yy[ok].sum(), (1 - yy[ok]).sum()) < 8: scn[name] = dict(skipped=True, n=int(ok.sum())); continue
        res = {}
        for k in ("X_ctfm", "X_ref", "X_null"):
            from sklearn.model_selection import cross_val_predict, StratifiedKFold
            from sklearn.pipeline import make_pipeline
            pr = cross_val_predict(make_pipeline(StandardScaler(), LogisticRegression(C=.1, max_iter=500, class_weight="balanced")), Xs[k][ok], yy[ok].astype(int),
                                   cv=StratifiedKFold(5, shuffle=True, random_state=0), method="predict_proba")[:, 1]
            res[k] = ladder.auroc(pr, yy[ok] > 0)
        scn[name] = dict(auc=res["X_ctfm"], auc_ref=res["X_ref"], auc_null=res["X_null"], n=int(ok.sum()), n_pos=int(yy[ok].sum()), cls=cls[name])
    n_gated = sum(v["gated"] for v in tok.values()); n_beyond = sum(v["beyond_hu"] for v in tok.values())
    gate_S = n_gated >= 15 and n_beyond >= 3
    json.dump(dict(token=tok, scan=scn, n_gated=n_gated, n_beyond_hu=n_beyond, gate_S=gate_S, n_tokens=int(len(keep))), open(P1 / "gates.json", "w"), indent=1, default=float)
    print(f"gated {n_gated} beyond-HU {n_beyond} gate_S {gate_S} DONE")


if __name__ == "__main__":
    main()
