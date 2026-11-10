"""M1 diagnostics after the gate failed (POST HOC, descriptive; the gate decision is not changed). Laptop only.
D1 alignment (bug check, label-free): ridge regression from each arm's features at cell (z, i, j) to the cell means of T2W / ADC / HBV
   (R columns 16 / 34 / 52) at shifted cells; with a correct mapping the zero shift predicts best. 150 studies, 100 train / 50 test.
D2 probe regularisation: the same probe at C = 0.001, 0.01, 0.1 (C = 1 is the protocol's), every arm incl. R, the same outer folds.
D3 added value: R + MRI-CORE B and R + untrained B (the null for "adding features") vs R alone, at C = 0.01, 0.1, 1.
Writes results/m1_diagnostics.json. usage (OMP/MKL threads 4): python imgsae/mri/m1_diagnostics.py
"""
import json
import time
import warnings

import numpy as np

import m1_analysis as A

ARMS = ["R", "mricore_A", "mricore_B", "sam_A", "sam_B", "profound", "untrained_B"]; CS = [0.001, 0.01, 0.1]; SHIFTS = [(0, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1), (0, 1, 1), (1, 0, 0), (-1, 0, 0)]


def fit_predict_C(X, y, tr, te, tag, C):
    p = A.CACHE / f"{tag}.npy"
    if p.exists(): return np.load(p)
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    t0 = time.time(); Xtr = X[tr].astype(np.float32); sc = StandardScaler().fit(Xtr)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore"); m = LogisticRegression(C=C, class_weight="balanced", max_iter=1000).fit(sc.transform(Xtr), y[tr])
    s = m.decision_function(sc.transform(X[te].astype(np.float32))).astype(np.float32); np.save(p, s)
    A.log(f"  fit {tag}: {X.shape[1]}-d, C {C}, {m.n_iter_[0]} iter, {time.time() - t0:.0f} s"); return s


def cv_C(X, y, T, outer, tag, C):
    s = np.full(len(y), np.nan, np.float32); pf = T.patient.map(outer).to_numpy()
    for f in range(5):
        tr, te = np.flatnonzero(pf != f), np.flatnonzero(pf == f)
        s[te] = (A.fit_predict(X, y, tr, te, f"full_{tag}_f{f}") if C == 1.0 and not tag.startswith("comb") else fit_predict_C(X, y, tr, te, f"diag_{tag}_C{C}_f{f}", C))
    return s


def alignment(keys):
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    rng = np.random.default_rng(0); ks = sorted(rng.choice(keys, 150, replace=False)); data = []
    for k in ks:
        z = np.load(A.FEATS / f"{k}.npz"); data.append(dict(idx=z["idx"].astype(int), R=z["R"][:, [16, 34, 52]], **{a: z[f"f_{a}"] for a in ARMS[1:]}))
    out = {}
    for a in ARMS[1:]:
        res = {}
        for sh in SHIFTS:
            parts = {"tr": ([], []), "te": ([], [])}
            for n, d in enumerate(data):
                pos = {tuple(r): i for i, r in enumerate(d["idx"])}
                src = [i for i, r in enumerate(d["idx"]) if (r[0] + sh[0], r[1] + sh[1], r[2] + sh[2]) in pos]
                dst = [pos[(d["idx"][i][0] + sh[0], d["idx"][i][1] + sh[1], d["idx"][i][2] + sh[2])] for i in src]
                part = parts["tr" if n < 100 else "te"]; part[0].append(d[a][src].astype(np.float32)); part[1].append(d["R"][dst])
            Xtr, Ytr = np.concatenate(parts["tr"][0]), np.concatenate(parts["tr"][1]); Xte, Yte = np.concatenate(parts["te"][0]), np.concatenate(parts["te"][1])
            sc = StandardScaler().fit(Xtr); m = Ridge(alpha=10.0).fit(sc.transform(Xtr), Ytr); P = m.predict(sc.transform(Xte))
            r2 = 1 - ((Yte - P) ** 2).sum(0) / ((Yte - Yte.mean(0)) ** 2).sum(0)
            res[f"dz{sh[0]}_dy{sh[1]}_dx{sh[2]}"] = dict(r2_t2w=float(r2[0]), r2_adc=float(r2[1]), r2_hbv=float(r2[2]), r2_mean=float(r2.mean()), n_test=int(len(Yte)))
        best = max(res, key=lambda s_: res[s_]["r2_mean"]); out[a] = dict(by_shift=res, best_shift=best, aligned=best == "dz0_dy0_dx0")
        A.log(f"D1 {a}: best shift {best}; " + ", ".join(f"{s_} {v['r2_mean']:.3f}" for s_, v in res.items()))
    return out


def main():
    M = A.marksheet(); split = json.load(open(A.HERE / "data" / "split.json")); exc = set(json.load(open(A.RES / "m0_qc_decisions.json"))["excluded"])
    keys = [k for k in sorted(split["dev_studies"]) if k not in exc]; out = dict(note="POST HOC diagnostics after the M1 gate failed; descriptive only")
    out["D1_alignment"] = alignment(keys); json.dump(out, open(A.RES / "m1_diagnostics.json", "w"), indent=1)
    src = {k: v["source"] for k, v in json.load(open(A.RES / "m0_prep_summary.json"))["studies"].items()}
    T, X = A.load_tokens(keys, M, src); y = T.y.to_numpy(); patient = T.patient.to_numpy(); outer = A.folds(A.strata(M, keys)); w = A.pw_weights(patient, y)
    sc = {}; auc = {}
    for a in ARMS:
        for C in CS + [1.0]:
            sc[(a, C)] = cv_C(X[a], y, T, outer, a, C); auc[f"{a}|C{C}"] = A.auc_w(y, sc[(a, C)], w)
        A.log(f"D2 {a}: " + ", ".join(f"C{C} {auc[f'{a}|C{C}']:.4f}" for C in CS + [1.0]))
    best = {a: max(CS + [1.0], key=lambda C: auc[f"{a}|C{C}"]) for a in ARMS}
    out["D2_regularisation"] = dict(auroc=auc, best_C=best, best_vs_R_best={a: A.boot_delta(y, sc[(a, best[a])], sc[("R", best["R"])], patient, B=500) for a in ARMS[1:]})
    json.dump(out, open(A.RES / "m1_diagnostics.json", "w"), indent=1)
    comb = {"R+mricore_B": np.concatenate([X["R"], X["mricore_B"]], 1), "R+untrained_B": np.concatenate([X["R"], X["untrained_B"]], 1)}; d3 = {}
    for C in [0.01, 0.1, 1.0]:
        s = {n: cv_C(Xc, y, T, outer, f"comb_{n}", C) for n, Xc in comb.items()}
        d3[f"C{C}"] = dict(auroc={n: A.auc_w(y, v, w) for n, v in s.items()},
                           mricore_added_vs_R=A.boot_delta(y, s["R+mricore_B"], sc[("R", C)] if C in CS + [1.0] else None, patient, B=500),
                           untrained_added_vs_R=A.boot_delta(y, s["R+untrained_B"], sc[("R", C)], patient, B=500),
                           mricore_added_vs_untrained_added=A.boot_delta(y, s["R+mricore_B"], s["R+untrained_B"], patient, B=500))
        A.log(f"D3 C{C}: {json.dumps(d3[f'C{C}'])}")
    out["D3_added_value"] = d3; json.dump(out, open(A.RES / "m1_diagnostics.json", "w"), indent=1); A.log("M1 DIAGNOSTICS DONE")


if __name__ == "__main__":
    main()
