"""imgsae vs sae-groundtruth (saegt) with every new flag off: outputs must be bitwise identical (CPU).
usage: .venv\Scripts\python   (Mac: .venv/bin/python) tests/test_equivalence.py
"""
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT.parent / "sae-groundtruth"))
from imgsae import sae as new, ladder  # noqa: E402
from saegt import sae as old, synth  # noqa: E402

OK = []


def check(name, ok, detail=""):
    OK.append(bool(ok)); print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}", flush=True)


def same(a, b):
    if isinstance(a, dict): return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, (tuple, list)): return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    if isinstance(a, np.ndarray): return a.shape == b.shape and np.array_equal(a, b, equal_nan=a.dtype.kind in "fc")
    return a == b


def main():
    g = np.random.default_rng(0)
    X = (np.abs(g.normal(size=(3000, 12))) @ g.normal(size=(12, 24)) + .3 * g.normal(size=(3000, 24))).astype(np.float32); X = synth.prep(X)
    for mat in (True, False):
        cfg = dict(M=48, k=4, steps=60, device="cpu", seed=3, matryoshka=mat)
        torch.manual_seed(0); mo, ho = old.fit(X, cfg); torch.manual_seed(0); mn, hn = new.fit(X, cfg)
        check(f"fit + encode (matryoshka={mat})", same(old.encode(mo, X), new.encode(mn, X)) and same(ho, hn))
    cfg = dict(steps=40, device="cpu", matryoshka=False)  # M, k from the legacy defaults (k = round(.06 M))
    torch.manual_seed(0); mo, _ = old.fit(X, cfg); torch.manual_seed(0); mn, _ = new.fit(X, cfg)
    check("fit legacy default M/k", same(old.encode(mo, X), new.encode(mn, X)) and mo.k == mn.k)
    cfg = dict(M=48, k=4, steps=40, device="cpu", matryoshka=False)
    torch.manual_seed(0); Zo = old.fits_codes(X[:2000], X, cfg); torch.manual_seed(0); Zn = new.fits_codes(X[:2000], X, cfg)
    check("fits_codes / consensus_codes_cl / anchor", same(Zo, Zn) and same(old.consensus_codes_cl(Zo), new.consensus_codes_cl(Zn)) and same(old.consensus_codes_anchor(Zo), new.consensus_codes_anchor(Zn)))
    from imgsae import consensus
    check("consensus_groups_cl + encode_groups == consensus_codes_cl", same(consensus.encode_groups(Zn, consensus.consensus_groups_cl(Zn)), new.consensus_codes_cl(Zn)[0]))
    for kind in ("pca", "varimax", "ica"):
        check(f"control_codes({kind}) + split_signed", same(old.split_signed(old.control_codes(kind, X, 0, seed=1, Xfit=X[:2000])), new.split_signed(new.control_codes(kind, X, 0, seed=1, Xfit=X[:2000]))))
    Z = np.maximum(X @ g.normal(size=(24, 40)).astype(np.float32), 0); Z2 = np.maximum(X @ g.normal(size=(24, 40)).astype(np.float32), 0)
    check("topk_rows / alive / act_match", same(old.topk_rows(Z, 5), new.topk_rows(Z, 5)) and same(old.alive(Z), new.alive(Z)) and same(old.act_match(Z, Z2), new.act_match(Z, Z2)))
    labs = ["A", "B", "C", "D", "E", "F", "G"]; lab = np.array(labs)[g.integers(0, 7, len(Z))]
    check("ladder.selectivity == saegt lineage_selectivity at K = 7", same(old.lineage_selectivity(Z, lab, labs), ladder.selectivity(Z, lab, labs)))
    print(f"{sum(OK)}/{len(OK)} passed" + (" DONE" if all(OK) else "")); return all(OK)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
