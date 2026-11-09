"""Planted-truth unit gates for the imaging ladder and statistics (lean plan v1, Phase 1 D1).
usage: .venv\Scripts\python   (Mac: .venv/bin/python) tests/test_units.py
"""
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from imgsae import accel, ladder, stats, sae  # noqa: E402

OK = []


def check(name, ok, detail=""):
    OK.append(bool(ok)); print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}", flush=True)


def main():
    g = np.random.default_rng(1)
    # R1: identical codes -> 1; independent random sparse codes -> ~0
    Z = (g.random((20000, 64)) < .05) * g.random((20000, 64)); Zr = (g.random((20000, 64)) < .05) * g.random((20000, 64))
    r_id, _ = sae.act_match(Z, Z); r_rnd, _ = sae.act_match(Z, Zr)
    check("R1 identical codes = 1", r_id == 1.0, f"{r_id:.3f}"); check("R1 random codes <= 0.05", r_rnd <= .05, f"{r_rnd:.3f}")
    # K-robust selectivity: pure spleen feature with 0.02 background in 59 others -> 0.89; feature equal on 5 of 60 -> 0.2
    labs = [f"c{i}" for i in range(60)]; lab = np.repeat(labs, 50); Zs = np.full((len(lab), 2), 0.0)
    Zs[:, 0] = np.where(lab == "c0", 1.0, .02); Zs[:, 1] = np.where(np.isin(lab, labs[:5]), 1.0, 0.0)
    s, a = ladder.selectivity(Zs, lab, labs)
    check("selectivity pure feature, K=60", abs(s[0] - 1 / 1.12) < 1e-9 and a[0] == "c0", f"{s[0]:.3f}")
    check("selectivity 5-organ feature, K=60", abs(s[1] - .2) < 1e-9, f"{s[1]:.3f}")
    grp = np.tile(np.arange(10), len(lab) // 10); s2, _ = ladder.selectivity(Zs, lab, labs, groups=grp)
    check("selectivity with patient averaging (balanced)", np.allclose(s, s2), f"{s2[0]:.3f}")
    # coverage curve
    C, area = ladder.coverage_curve(np.array([.95, .6, .8, .4]), ["a", "b", "a", "c"], ["a", "b", "c", "d"], taus=np.array([.5, .7, .9]))
    check("coverage_curve", list(C) == [2, 1, 1] and abs(area - (4 / 3) / 4) < 1e-12, f"{list(C)} {area:.3f}")
    # chimera: own c0, adjacent c1; 30% of top mass in non-adjacent c5 -> chimeric; in adjacent c1 -> not
    labc = np.array(["c0"] * 70 + ["c1"] * 30 + ["c5"] * 30 + ["c9"] * 9870); zc = np.zeros((len(labc), 2))
    zc[:70, :] = 1.0; zc[70:100, 0] = 1.0; zc[100:130, 1] = 1.0
    ch = ladder.chimera(zc, labc, ["c0", "c1", "c5", "c9"], own=["c0", "c0"], adj={"c0": {"c1"}})
    check("chimera adjacency rule", (not ch[0]) and ch[1], str(ch))
    # theta: binormal planted AUROC
    n = 4000; y = g.random(n) < .4; dlt = 1.0; true = float(__import__("scipy.stats", fromlist=["norm"]).norm.cdf(dlt / np.sqrt(2)))
    t = np.where(y, g.normal(dlt, 1, n), g.normal(0, 1, n)); th = ladder.theta(t, y, freq=g.lognormal(0, 1, n))
    check("theta recovers planted AUROC +-0.03", abs(th["theta"] - true) <= .03 and th["estimable"], f"{th['theta']:.3f} vs {true:.3f}")
    # twin scores: identical -> 1 for alive features
    tw = ladder.twin_scores(Z, Z); check("twin scores identical = 1", np.allclose(tw[sae.alive(Z)], 1.0))
    # cluster bootstrap coverage (ICC ~ .5, 100 patients x 20 tokens), 1000 simulations
    cov = 0; mu = 0.0
    for s_ in range(1000):
        r = np.random.default_rng(100 + s_); u = r.normal(0, 1, 100); v = np.repeat(u, 20) + r.normal(0, 1, 2000)
        _, lo, hi = stats.cluster_bootstrap(v, np.repeat(np.arange(100), 20), B=1000, seed=s_); cov += lo <= mu <= hi
    check("cluster bootstrap 95% coverage in [0.93, 0.97]", .93 <= cov / 1000 <= .97, f"{cov / 1000:.3f}")
    # corrected t formula and Holm
    ct = stats.corrected_t(np.array([.1, .2, .15, .05, .12])); se = np.sqrt((1 / 5 + 1) * np.var([.1, .2, .15, .05, .12], ddof=1))
    check("corrected t variance (1/J + 1)", abs(ct["se"] - se) < 1e-12, f"t={ct['t']:.2f}")
    check("holm", np.allclose(stats.holm([.01, .04, .03, .2]), [.04, .09, .09, .2]))
    # size rule + init fallback + sampled threshold path
    check("size_rule", sae.size_rule(512, 30000) == (600, 38) and sae.size_rule(64, 10 ** 7) == (256, 16))
    Xs = g.normal(size=(300, 16)).astype(np.float32); m, _ = sae.fit(Xs, dict(M=400, k=8, steps=20, matryoshka=False, init_fallback=True))
    check("init_fallback M > rows", m.D.shape == (400, 16))
    Xb = g.normal(size=(30000, 16)).astype(np.float32); Xb /= np.sqrt((Xb ** 2).mean())
    m1, _ = sae.fit(Xb, dict(M=64, k=4, steps=200, matryoshka=False, exact_limit=0, thr_sample=20000)); L1 = (sae.encode(m1, Xb) > 0).sum(1).mean()
    check("sampled-threshold path L0 within 2% of k", abs(L1 / 4 - 1) <= .02, f"L0={L1:.3f}")
    dev = accel.pick("auto")  # the M5 ran this on MPS; on the Windows laptop it runs on CUDA
    if dev != "cpu":
        cfg = dict(M=64, k=4, steps=300, matryoshka=False, seed=0)
        mc, _ = sae.fit(Xb, {**cfg, "device": "cpu"}); mm, _ = sae.fit(Xb, {**cfg, "device": dev})
        Lc = (sae.encode(mc, Xb) > 0).sum(1).mean(); Lm = (sae.encode(mm, Xb) > 0).sum(1).mean()
        check(f"{dev.upper()} vs CPU L0 within 1%", abs(Lm / Lc - 1) <= .01, f"cpu {Lc:.3f} {dev} {Lm:.3f}")
    print(f"{sum(OK)}/{len(OK)} passed" + (" DONE" if all(OK) else "")); return all(OK)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
