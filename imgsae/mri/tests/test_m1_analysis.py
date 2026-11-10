"""Unit tests for the statistics in imgsae/mri/m1_analysis.py (synthetic data, known answers). usage: python imgsae/mri/tests/test_m1_analysis.py"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import m1_analysis as A  # noqa: E402


def test_pw_weights_equalise_patients():
    p = np.array(["a"] * 10 + ["b"] * 2 + ["a"] * 1 + ["b"] * 3); y = np.array([0] * 12 + [1] * 4)
    w = A.pw_weights(p, y)
    assert np.isclose(w[:10].sum(), 1) and np.isclose(w[10:12].sum(), 1) and np.isclose(w[12], 1) and np.isclose(w[13:].sum(), 1)


def test_auc_weighted_equals_patient_level_mean():
    # patient a: all its lesion tokens score above its normals; patient b: below -> patient-weighted AUROC reflects both equally
    y = np.array([1, 1, 1, 1, 0, 1, 0, 0, 0, 0]); s = np.array([9, 9, 9, 9, 5, 0, 5, 5, 5, 5], float); p = np.array(list("aaaaabbbbb"))
    w = A.pw_weights(p, y); auc = A.auc_w(y, s, w)
    # weighted: pos a (weight 0.25 each, 4 tokens) and pos b (weight 1); negatives a (1) and b (0.25 each x4): pos-a beat all, pos-b beats none
    assert np.isclose(auc, 0.5), auc


def test_boot_delta_identical_scores_is_zero():
    rng = np.random.default_rng(0); y = rng.integers(0, 2, 400); s = rng.random(400) + y; p = np.repeat(np.arange(40), 10).astype(str)
    d, lo, hi = A.boot_delta(y, s, s, p, B=200); assert d == 0 and lo == 0 and hi == 0


def test_boot_delta_detects_better_score():
    rng = np.random.default_rng(1); n = 3000; y = rng.integers(0, 2, n); p = np.repeat(np.arange(150), 20).astype(str)
    good = y + rng.normal(0, 0.7, n); bad = y + rng.normal(0, 2.0, n)
    d, lo, hi = A.boot_delta(y, good, bad, p, B=300); assert d > 0.1 and lo > 0, (d, lo, hi)


def test_rule_s():
    rng = np.random.default_rng(2); n = 4000; y = rng.integers(0, 2, n); p = np.repeat(np.arange(200), 20).astype(str); m = np.ones(n, bool)
    mk = lambda sd: y + rng.normal(0, sd, n)  # noqa: E731
    sc = dict(R=mk(3.0), mricore_A=mk(1.5), mricore_B=mk(1.6), sam_A=mk(2.5), sam_B=mk(2.6), profound=mk(1.45))
    r = A.rule_s(sc, y, p, m); assert r["U"] == "mricore_A" and r["chosen"] == "mricore_A", r      # ProFound only slightly better -> U kept
    sc["profound"] = mk(0.5); r = A.rule_s(sc, y, p, m); assert r["chosen"] == "profound", r       # clearly better -> ProFound


def test_folds_patient_level_and_stratified():
    Pt = pd.DataFrame(dict(patient=[f"p{i}" for i in range(100)], stratum=["a"] * 50 + ["b"] * 50)); f = A.folds(Pt)
    s = pd.Series(f); assert set(s) == set(range(5)) and all(s.value_counts() == 20)
    assert all(pd.Series([f[f"p{i}"] for i in range(50)]).value_counts() == 10)


if __name__ == "__main__":
    fs = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for f in fs: f(); print("ok", f.__name__)
    print(f"ALL {len(fs)} TESTS PASSED")
