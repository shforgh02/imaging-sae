"""Lung L2, step F3 (new freeze; dev only): freeze the 11 shared axes of layer `pooled` (step R, r2_shared.py) as plain numbers, so the S6
analysis needs no pickle and no refit. Also the axis code used by s6_frozen_analysis.py (whiten, variates, removal, logits from `pooled`).
Source: <L2_S4_DATA>/r/r2_shared_pooled.pkl (fitted by r2_shared.py on all 7,336 dev main exams; never saw z-fix or test data).
Writes <out dir>/frozen_axes_pooled.npz with, per member m (5 members):
  m{m}_mu, m{m}_sd (1,536: dev mean and SD of `pooled`), m{m}_live (units with SD >= 1e-6), m{m}_P (30 x n_live: the 30 PCA directions),
  m{m}_sc (30: the scales, SD of each PC on dev), m{m}_W (30 x 11: the weight vectors of the 11 shared axes in the whitened PC space);
  and axis_sd_dev, axis_mean_dev (11: SD (ddof 0) and mean over the 7,336 dev main exams of each axis activation = mean of the five
  member variates), n_axes, npc, n_dev_exams.
Check (stops if it fails): the activations computed from the written file equal the pickle's (each member's variates and their mean)
within 1e-9 on all dev main exams; the saved dev logits are rebuilt from `pooled` through Sybil's hidden_fc, ReLU and head.
usage (venv python): python s5_axes_freeze.py <assembled dev dir> <heads npz> <out dir (results/s5)>
"""
import os
import pickle
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, r"D:\Shayan\imgsae")
import s4_core as C  # noqa: E402

PKL = Path(os.environ.get("L2_S4_DATA", r"D:\Shayan\imgsae_data\lung_l2")) / "r" / "r2_shared_pooled.pkl"


# ------------------------------------------------------------------ axis code (used by s6_frozen_analysis.py; same algebra as r2_shared.Shared and r4_axes_audit.remove)
def load_axes(path):
    z = np.load(path); k = int(z["n_axes"])
    mem = [dict(mu=z[f"m{m}_mu"], sd=z[f"m{m}_sd"], live=z[f"m{m}_live"].astype(bool), P=z[f"m{m}_P"], sc=z[f"m{m}_sc"], W=z[f"m{m}_W"]) for m in range(5)]
    return dict(members=mem, k=k, npc=int(z["npc"]), axis_sd_dev=z["axis_sd_dev"], axis_mean_dev=z["axis_mean_dev"])


def white(ax, x, m):
    """whitened PC scores (n, 30) of member m's `pooled` rows x (n, 1536)."""
    t = ax["members"][m]; return (x[:, t["live"]] - t["mu"][t["live"]]) / t["sd"][t["live"]] @ t["P"].T / t["sc"]


def variates(ax, X):
    """(n, 5, k): the member variates of the k shared axes; X is (n, 5, 1536)."""
    return np.stack([white(ax, X[:, m], m) @ ax["members"][m]["W"] for m in range(5)], 1)


def activation(ax, X):
    """(n, k): axis activation = mean of the five member variates (as step R)."""
    return variates(ax, X).mean(1)


def remove(ax, x, m, axes):
    """member m's `pooled` rows with the span of the given shared axes set to the dev mean (0 in the whitened space); only that span of the
    member's vector changes (r4_axes_audit.remove with the frozen numbers)."""
    t = ax["members"][m]; A = t["W"][:, axes]; W = white(ax, x, m); Pj = A @ np.linalg.pinv(A.T @ A) @ A.T
    out = x.copy(); out[:, t["live"]] -= ((W @ Pj) * t["sc"]) @ t["P"] * t["sd"][t["live"]]; return out


def load_fc(heads_path):
    hz = np.load(heads_path); return [(hz[f"m{m}_hidden_fc_W"].astype(np.float64), hz[f"m{m}_hidden_fc_b"].astype(np.float64)) for m in range(5)]


def member_logits(x, m, fc, heads):
    """member m's logits (n, 6) from its `pooled` rows: Sybil's own hidden_fc, ReLU and head (r1_arms.load)."""
    return C.head_logits(np.maximum(x @ fc[m][0].T + fc[m][1], 0), heads[m])[0]


def lbar_t(X, fc, heads, t=1, ax=None, off=None):
    """mean member logit of year t from `pooled` X (n, 5, 1536); off = list of shared axes of `ax` switched off (set to the dev mean) in
    every member (none if off is empty)."""
    return np.stack([member_logits(remove(ax, X[:, m], m, list(off)) if off else X[:, m], m, fc, heads)[:, t - 1] for m in range(5)], 1).mean(1)


# ------------------------------------------------------------------ freeze
def main():
    A, heads_p, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]); OUT.mkdir(parents=True, exist_ok=True)
    import r1_arms as R1   # noqa: E402  (loads the dev main arrays and checks the saved logits from `pooled`)
    import r2_shared as R2  # noqa: E402
    sys.modules["__main__"].Shared = R2.Shared   # the pickle was written by r2_shared.py run as a script
    E, X, LG, _, _, dmax = R1.load(A, heads_p, "pooled"); P = pickle.load(open(PKL, "rb")); sh, k = P["shared"], int(P["k"])
    assert (P["series_uid"] == E.series_uid.to_numpy()).all() and k == 11 and sh.npc == 30
    arrs = dict(n_axes=np.int64(k), npc=np.int64(sh.npc), n_dev_exams=np.int64(len(E)))
    for m in range(5):
        t = sh.T[m]
        arrs.update({f"m{m}_mu": np.asarray(t["mu"], np.float64), f"m{m}_sd": np.asarray(t["sd"], np.float64), f"m{m}_live": np.asarray(t["live"], bool),
                     f"m{m}_P": np.asarray(t["P"], np.float64), f"m{m}_sc": np.asarray(t["sc"], np.float64), f"m{m}_W": np.asarray(sh.Wt[m][:, :k], np.float64)})
    Sp = np.asarray(P["S"], np.float64); arrs["axis_sd_dev"] = Sp.std(0); arrs["axis_mean_dev"] = Sp.mean(0)
    np.savez(OUT / "frozen_axes_pooled.npz", **arrs)
    # ---- checks
    ax = load_axes(OUT / "frozen_axes_pooled.npz"); V = variates(ax, X); V0 = sh.variates(X)[:, :, :k]
    e_var, e_act = float(np.abs(V - V0).max()), float(np.abs(V.mean(1) - Sp).max())
    fc = load_fc(heads_p); heads = C.load_heads(heads_p)
    e_log = float(np.abs(lbar_t(X, fc, heads, 1) - LG[:, :, 0].mean(1)).max())
    x0 = remove(ax, X[:200, 0], 0, [0]); e_rm = float(np.abs(white(ax, x0, 0) @ ax["members"][0]["W"][:, 0]).max())   # axis 0 is 0 after removal
    print(f"frozen_axes_pooled.npz written: {k} axes, 30 PCs, {len(E)} dev exams; max |variates - pickle| {e_var:.2e}; max |activation - pickle S| {e_act:.2e}; "
          f"max |lbar1 from pooled - saved| {e_log:.2e} (R1.load check {dmax:.2e}); axis 0 after removal max |variate| {e_rm:.2e}")
    print("axis SD (dev):", np.round(arrs["axis_sd_dev"], 6).tolist()); print("axis mean (dev):", np.round(arrs["axis_mean_dev"], 12).tolist())
    if not (e_var < 1e-9 and e_act < 1e-9 and e_log < 1e-4 and e_rm < 1e-9): raise SystemExit("STOP: the frozen axes do not reproduce the pickle")


if __name__ == "__main__":
    main()
