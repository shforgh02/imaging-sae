"""Synthetic test of s4_core: exact contribution identity for every arm; families recover a feature planted in 5 'members'."""
import sys
import time

import numpy as np

sys.path.insert(0, r"D:\Shayan\imgsae\exploratory\lung_l2")
import s4_core as C  # noqa: E402

rng = np.random.default_rng(0)
n, d, K = 3000, 512, 16
heads = [dict(hazard_fc_W=rng.normal(0, .05, (6, d)), hazard_fc_b=rng.normal(0, .2, 6), base_hazard_fc_W=rng.normal(0, .05, (1, d)),
              base_hazard_fc_b=np.array([-4.0])) for _ in range(5)]
latent = np.abs(rng.normal(0, 1, (n, 8))) * (rng.random((n, 8)) < .3)          # 8 sparse shared factors
Hs = []
for m in range(5):
    D = np.abs(rng.normal(0, 1, (8, d)))
    h = np.maximum(latent @ D + rng.normal(0, .3, (n, d)), 0); h[:, :5] = 0      # 5 dead units
    Hs.append(h)
ok = True
for kind in C.ARMS:
    t0 = time.time()
    w6 = C.eff_weights(C.head_logits(Hs[0], heads[0])[1], heads[0], 6)[0].mean(0)
    arm = C.Arm(kind, K, 0).fit(Hs[0], w_ref=w6)
    A = arm.encode(Hs[0])
    lg, _ = C.head_logits(Hs[0], heads[0])
    for t in (1, 6):
        ic, ct, rs = C.contributions(Hs[0], A, arm, heads[0], t)
        err = np.abs(ic + ct.sum(1) + rs - lg[:, t - 1]).max()
        ok &= err < 1e-8
    l0, l1 = C.v1_fold(Hs[0][:2000], Hs[0][2000:], heads[0], kind, K, 0, w_ref=w6)
    r = np.corrcoef(l0[:, 5], l1[:, 5])[0, 1]
    print(f"{kind:7s} identity err {err:.1e}  V1 r(6y) {r:.3f}  {time.time() - t0:.1f}s")
As = [C.Arm("pca", K, 0).fit(h).encode(h) for h in Hs]
fam = C.families([np.abs(a) for a in As], r_thr=0.7, min_members=3)
print("families (pca, abs):", len(fam))
As = [C.Arm("sae", K, 0).fit(h).encode(h) for h in Hs]
fam = C.families(As, r_thr=0.7, min_members=3)
best = max(abs(np.corrcoef(C.family_activation(As, f), latent[:, j])[0, 1]) for f in fam for j in range(8)) if fam else 0
print("families (sae):", len(fam), "| best |r| with a planted factor:", round(best, 3))
print("PASS" if ok and len(fam) >= 4 and best > .8 else "FAIL")
