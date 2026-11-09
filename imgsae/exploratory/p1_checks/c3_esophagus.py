"""Exploratory check 3 (post hoc): why is the CT-FM probe AUROC for esophagus 0.30 (below chance) in data/p1/gates.json?
Same token subsample and probe as scripts/p1_probe.py. Reports: esophagus core tokens and patients (all rows, subsample, per CV fold);
whether the class is present in each fold's training set; per-fold AUROC of the pooled out-of-fold probability; what CT-FM predicts for
esophagus tokens; and a direct one-vs-rest logistic probe (CT-FM and reference) as a cross-check.
Writes results/c3_esophagus.json. usage: ..\..\.venv\Scripts\python c3_esophagus.py [--concept esophagus]
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import p1_probe as PR  # noqa: E402
from imgsae import ladder  # noqa: E402

OUT = HERE / "results"; OUT.mkdir(exist_ok=True); P1 = PR.P1


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--concept", default="esophagus"); a = ap.parse_args()
    R = np.load(P1 / "rows.npz"); C = json.load(open(P1 / "concepts.json")); G = C["groups"]; elig = C["eligible"]; lab, scan = R["lab"], R["scan"]
    gi = G.index(a.concept); res = dict(concept=a.concept, all_rows_tokens=int((lab == gi).sum()), all_rows_patients=int(len(np.unique(scan[lab == gi]))))
    rng = np.random.default_rng(0); keep = np.flatnonzero((lab == -1) | np.isin(lab, [G.index(g) for g in elig]))
    if len(keep) > 60000: keep = np.sort(rng.choice(keep, 60000, replace=False))
    y = lab[keep].copy(); classes = sorted(set(y.tolist())); y = np.searchsorted(classes, y); ci = classes.index(gi); pos = y == ci; g = scan[keep]
    res.update(sub_tokens=int(pos.sum()), sub_patients=int(len(np.unique(g[pos]))), sub_tokens_per_patient=sorted(Counter(g[pos].tolist()).values(), reverse=True))
    folds = []
    for k, (tr, te) in enumerate(GroupKFold(5).split(y, y, g)):
        folds.append(dict(fold=k, train_pos=int(pos[tr].sum()), test_pos=int(pos[te].sum()), test_patients=int(len(np.unique(g[te][pos[te]])))))
    res["folds"] = folds; print(json.dumps({k: v for k, v in res.items()}, default=int), flush=True)
    for name, key in (("ctfm", "X_ctfm"), ("ref", "X_ref")):
        X = R[key][keep]; P = PR.oof_proba(X, y, g); s = P[:, ci]; out = dict(auc_pooled=ladder.auroc(s, pos))
        per = []
        for k, (tr, te) in enumerate(GroupKFold(5).split(X, y, g)):
            per.append(dict(fold=k, auc_within_fold=ladder.auroc(s[te], pos[te]) if pos[te].any() else None, mean_p_pos=float(s[te][pos[te]].mean()) if pos[te].any() else None,
                            mean_p_neg=float(s[te][~pos[te]].mean())))
        out["per_fold"] = per; pred = np.array(classes)[P.argmax(1)][pos]
        out["argmax_for_pos"] = [("other" if c_ == -1 else G[c_], n) for c_, n in Counter(pred.tolist()).most_common(5)]
        bin_s = np.zeros(len(y))  # direct one-vs-rest logistic, same CV and scaling
        for tr, te in GroupKFold(5).split(X, y, g):
            sc = StandardScaler().fit(X[tr]); m = LogisticRegression(C=1.0, max_iter=300, class_weight="balanced").fit(sc.transform(X[tr]), pos[tr]); bin_s[te] = m.decision_function(sc.transform(X[te]))
        out["auc_binary_ovr"] = ladder.auroc(bin_s, pos); res[name] = out
        print(name, json.dumps(out, default=float), flush=True)
    json.dump(res, open(OUT / f"c3_{a.concept}.json", "w"), indent=1, default=float); print("DONE", flush=True)


if __name__ == "__main__":
    main()
