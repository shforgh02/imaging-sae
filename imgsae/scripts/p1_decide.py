"""Phase 1 D7: apply the pre-written decision table -> data/p1/decision.json + DECISION_MEMO_P1.md (project folder).
Gates: E engineering, S signal, D1 SAE advantage, D2 reproducibility-validity dissociation, D3 shortcut share, degeneracy check.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from imgsae import ladder  # noqa: E402

P1 = Path(os.environ.get("IMGSAE_P1", ROOT / "data/p1")); MEMO = Path(os.environ.get("IMGSAE_MEMO", ROOT.parent / "docs" / "DECISION_MEMO_P1.md")); LOGS = Path(os.environ.get("IMGSAE_LOGS", ROOT / "logs"))
BASE = ("sparse_varimax", "soft_kmeans", "raw_sparse", "hu_sae_cons")


def theta_pooled(B=2000):
    fs = sorted((P1 / "fit").glob("sae_single_rep*_*.csv"))
    if not fs: return dict(theta=np.nan, estimable=False)
    T = pd.concat([pd.read_csv(f) for f in fs]); T = T[T["v0"]]
    y = (T["sel"] >= .7) & ~T["chimeric"] & T["gated"] & (T["r_pert"].fillna(-1) >= .7); t = T["t"].values; y = y.values
    th = ladder.theta(t, y); rng = np.random.default_rng(0); bs = []
    for _ in range(B):
        ii = rng.integers(0, len(t), len(t)); bs.append(ladder.auroc(t[ii], y[ii]))
    th["ci"] = (float(np.nanquantile(bs, .025)), float(np.nanquantile(bs, .975)))
    if not th["estimable"]:
        from scipy.stats import spearmanr
        w = np.fmin(T["sel"].values, T["r_pert"].fillna(0).values); th["spearman_t_vs_validity"] = float(spearmanr(t, w)[0])
    return th


def main():
    E = {}
    for f in ("p1_d2_engineering_scans.json",):
        p = LOGS / f
        if p.exists(): E = json.load(open(p))
    enc_log = LOGS / "p1_encode_dev.log"; enc_hours = np.nan
    if enc_log.exists():
        secs = [float(l.split("encode ")[1].split("s")[0]) + float(l.split("table ")[1].split("s")[0]) for l in open(enc_log) if " tokens " in l]
        enc_hours = sum(secs) / 3600
    gate_E = bool(E.get("gate_E_partial")) and (np.isnan(enc_hours) or enc_hours <= 24)
    # Time waiver (user decision 2026-11-07, docs/EXECUTION_LOG.md): GPU hardware power-sensor fault on the Windows laptop; precision (1.0 mm) chosen
    # over speed. E is then judged on memory, GPU/CPU parity and seam only; the timings are still reported in the memo.
    sp = json.load(open(P1 / "spacing.json")) if (P1 / "spacing.json").exists() else {}; waived = bool(sp.get("gate_E_time_waived"))
    if waived:
        gate_E = bool(E.get("results")) and all(r["gpu_peak_gb"] <= 12 and r["parity_cos_gpu16_vs_cpu32"] >= .995 and r["seam_cos_tiling_vs_224"] >= .95 for r in E["results"])
    Gt = json.load(open(P1 / "gates.json")); gate_S = bool(Gt["gate_S"])
    S = json.load(open(P1 / "fit" / "summary.json")); reps = sorted({v["rep"] for v in S.values()})
    area = lambda m: np.array([S.get(f"{m}_rep{r}", {}).get("area", np.nan) for r in reps])  # noqa: E731
    base_means = {b: float(np.nanmean(area(b))) for b in BASE}; strongest = max(base_means, key=lambda b: base_means[b]); best = {}
    for m in ("sae_cons", "sae_single"):
        diff = area(m) - area(strongest); best[m] = dict(all_reps_above=bool(np.all(diff > 0)), mean_gain=float(np.nanmean(diff)))
    D1 = any(v["all_reps_above"] and v["mean_gain"] >= .05 for v in best.values())
    r1_cons = float(np.nanmean([S.get(f"sae_cons_rep{r}", {}).get("R1", np.nan) for r in reps])); th = theta_pooled()
    D2 = r1_cons >= .60 and ((th.get("estimable") and th["ci"][1] < .75) or (not th.get("estimable") and th.get("spearman_t_vs_validity", 1) < .3))
    sc = float(np.nanmean([S.get(f"sae_cons_rep{r}", {}).get("shortcut_share", np.nan) for r in reps])); D3 = sc >= .20
    c07 = {m: float(np.nanmean([S.get(f"{m}_rep{r}", {}).get("C07", 0) for r in reps])) for m in {v["method"] for v in S.values()}}
    degenerate = sum(v > 0 for v in c07.values()) < 2 or not th.get("estimable", False)
    verdict = "GO-positive" if (gate_E and gate_S and D1 and not degenerate) else ("GO-cautionary" if (gate_E and gate_S and (D2 or D3) and not degenerate) else "NO-GO")
    out = dict(verdict=verdict, gate_E=gate_E, gate_E_time_waived=waived, spacing=sp.get("spacing"), encode_hours=enc_hours, gate_S=gate_S, n_gated=Gt["n_gated"], n_beyond_hu=Gt["n_beyond_hu"], strongest_baseline=strongest,
               baseline_area=base_means, sae_vs_strongest=best, D1=D1, R1_consensus=r1_cons, theta=th, D2=bool(D2), shortcut_share=sc, D3=bool(D3), C07=c07, degenerate=bool(degenerate),
               areas={m: float(np.nanmean(area(m))) for m in sorted(c07)}, R1={m: float(np.nanmean([S.get(f"{m}_rep{r}", {}).get("R1", np.nan) for r in reps])) for m in sorted(c07)})
    json.dump(out, open(P1 / "decision.json", "w"), indent=1, default=float)
    L = [f"# Phase 1 decision memo (pre-written table, lean plan v1)", "", f"**Verdict: {verdict}**", "",
         f"- E engineering: {'pass' if gate_E else 'FAIL'} (encode {enc_hours:.1f} h for the dev set"
         + (f"; TIME CRITERION WAIVED: {sp.get('waiver_reason', '')})" if waived else ")"),
         f"- S signal: {'pass' if gate_S else 'FAIL'} ({Gt['n_gated']} gated concepts, {Gt['n_beyond_hu']} beyond-HU)",
         f"- D1 SAE advantage: {'yes' if D1 else 'no'} (strongest baseline {strongest}, area {base_means[strongest]:.3f}; "
         + ", ".join(f"{m} gain {v['mean_gain']:+.3f}" for m, v in best.items()) + ")",
         f"- D2 dissociation: {'yes' if D2 else 'no'} (consensus R1 {r1_cons:.2f}; theta {th.get('theta', np.nan):.2f}, CI {th.get('ci')})",
         f"- D3 shortcut share of reproducible consensus features: {sc:.2f} ({'yes' if D3 else 'no'})",
         f"- Degeneracy: {'DEGENERATE' if degenerate else 'ok'} (C(0.7) by method: " + ", ".join(f"{m} {v:.1f}" for m, v in sorted(c07.items())) + ")", "",
         "Validated-coverage area (normalised) by method: " + ", ".join(f"{m} {v:.3f}" for m, v in out["areas"].items()),
         "", "R1 by method: " + ", ".join(f"{m} {v:.2f}" for m, v in out["R1"].items())]
    MEMO.write_text("\n".join(L) + "\n"); print(verdict, "DONE")


if __name__ == "__main__":
    main()
