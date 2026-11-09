"""Exploratory check 2 (post hoc, not part of the pre-written decision): does gate S depend on the label-derived position in the reference?
The reference in the run = HU/texture features (+ 3x3x3 context) + position, where the z position is the vertebral level computed from the
ground-truth vertebra masks (imgsae/tokens.position_features). CT-FM sees only the image. Variants of the reference:
  ref_pos     : as in the run (sanity check: must reproduce data/p1/gates.json)
  ref_pos_xy  : z / vertebral-level columns removed (x, y are body-relative, computed from the HU body mask, label-free)
  ref_only    : no position at all
Same probe code (scripts/p1_probe.oof_proba, boot_auc), same token subsample, same CT-FM out-of-fold probabilities, same gate thresholds.
Raw ref/pos are re-read from data/p1/scans/<id>.npz in the assemble order and preprocessed with the assemble prep().
Writes results/c2_probe_position.json. usage: ..\..\.venv\Scripts\python c2_probe_position.py
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import p1_assemble as A  # noqa: E402
import p1_probe as PR  # noqa: E402

OUT = HERE / "results"; OUT.mkdir(exist_ok=True); P1 = PR.P1
Z_COLS = [0] + [3 + 3 * j for j in range(8)]  # pos = [z, y, x] + sin/cos(2^k pi c) blocks of 3 for k < 4; z is column 0 of each block


def main():
    R = np.load(P1 / "rows.npz"); C = json.load(open(P1 / "concepts.json")); G = C["groups"]; elig = C["eligible"]; Gt = json.load(open(P1 / "gates.json"))
    lab, scan = R["lab"], R["scan"]; ref, pos = [], []
    for s in C["scans"]:
        z = np.load(P1 / "scans" / f"{s['id']}.npz"); ref.append(z["ref"]); pos.append(z["pos"])
    ref, pos = np.concatenate(ref).astype(np.float32), np.concatenate(pos).astype(np.float32); assert len(ref) == len(lab), (len(ref), len(lab))
    assert pos.shape[1] == 27, pos.shape
    X0 = A.prep(np.concatenate([ref, pos], 1))[0]; print("max |X_ref(run) - rebuilt|:", float(np.abs(X0[:50000] - R["X_ref"][:50000].astype(np.float32)).max()), flush=True)
    xy = np.delete(pos, Z_COLS, axis=1)
    variants = dict(ref_pos=X0, ref_pos_xy=A.prep(np.concatenate([ref, xy], 1))[0], ref_only=A.prep(ref)[0])
    rng = np.random.default_rng(0); keep = np.flatnonzero((lab == -1) | np.isin(lab, [G.index(g) for g in elig]))  # same subsample as p1_probe
    if len(keep) > 60000: keep = np.sort(rng.choice(keep, 60000, replace=False))
    y = lab[keep].copy(); classes = sorted(set(y.tolist())); y = np.searchsorted(classes, y)
    print("CT-FM probe ...", flush=True); Pd = PR.oof_proba(R["X_ctfm"][keep], y, scan[keep]); res = {}
    for name, X in variants.items():
        print(f"reference {name} ({X.shape[1]} features) ...", flush=True); Pr = PR.oof_proba(X[keep], y, scan[keep]); tok = {}
        for ci, c in enumerate(classes):
            if c < 0: continue
            r = PR.boot_auc(Pd[:, ci], Pr[:, ci], y == ci, scan[keep]); r["gated"] = r["ci"][0] >= .70
            r["beyond_hu"] = bool(r["gated"] and r["diff"] >= .05 and r["ci_diff"][0] > 0); tok[G[c]] = r
        ng = sum(v["gated"] for v in tok.values()); nb = sum(v["beyond_hu"] for v in tok.values())
        res[name] = dict(n_features=int(X.shape[1]), n_gated=ng, n_beyond_hu=nb, gate_S=bool(ng >= 15 and nb >= 3), token=tok,
                         beyond=[g for g, v in tok.items() if v["beyond_hu"]], median_auc_ref=float(np.median([v["auc_ref"] for v in tok.values()])))
        print(f"  gated {ng} beyond-HU {nb} gate_S {res[name]['gate_S']} median ref AUROC {res[name]['median_auc_ref']:.3f} beyond: {res[name]['beyond']}", flush=True)
        json.dump(res, open(OUT / "c2_probe_position.json", "w"), indent=1, default=float)
    same = all(abs(res["ref_pos"]["token"][g]["auc_ref"] - Gt["token"][g]["auc_ref"]) < 1e-9 for g in Gt["token"])
    print("sanity: ref_pos reproduces gates.json:", same, flush=True); res["sanity_reproduces_run"] = same
    json.dump(res, open(OUT / "c2_probe_position.json", "w"), indent=1, default=float); print("DONE", flush=True)


if __name__ == "__main__":
    main()
