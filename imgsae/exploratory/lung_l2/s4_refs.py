"""Lung L2, S4, simple references of amendment A3 (docs/LUNG_L2_PROTOCOL.md 16a; plan docs/PLAN_L2_NEXT_v1.md section 3, A3).
R-size: the largest nodule's long diameter (max_dia, 0 if no nodule), no fitting. AUROC for y1 (all screens) and y6 (baseline).
  It was computed on test in L0, so it is "partly seen": a reference only, never a hypothesis.
F+I: inputs = F's logit (F1 for y1, F6 for y6; frozen, fitted on train) + the 5 patient measures of l2_data.MEASURES (lung volume,
  emphysema % LAA-950, lung 15th-percentile HU, lung mean HU, body area; rule A2 already applied in l2_data) + one indicator "any
  measure missing"; medians imputed inside each training fold. Model nlst_l0.logit_model() (standardise + logistic, C = 0.3).
  Dev: participant-grouped 5-fold CV (seed 0); AUROC with a participant bootstrap (2,000 draws).
  The test that gives F+I its meaning: does Sybil add to F+I? Cross-fitted logistic y ~ (F+I logit, out of fold) + logit(s_t) against
  y ~ (F+I logit): dAUROC with interval, likelihood-ratio test, and the difference refitted within each dev half.
  Sensitivity runs next to the primary: (i) all 7 measures (adds air noise and lung z-extent); (ii) only exams with lung_cut_z = 0.
  Known limit: emphysema % depends on the scanner (Toshiba air reads about 38 HU low); F+I is also reported by maker (descriptive).
  U3 table: false alarms per 1,000 screens of F+I at the radiologists' sensitivity (y1), added next to s4_u3's table.
  S6: one fit on all dev (primary model) whose parameters are written here and frozen at S5 (hash), then applied to test unchanged.
Candidates for gate 9.8: "Sybil adds to F+I" for y1 and y6 (> 0, null 0); not feature-based, not partly seen (needs image measures).
usage (venv python): python s4_refs.py <assembled dir> <results dir> [--tag dev]
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, r"D:\Shayan\imgsae\exploratory\lung_l0")
import nlst_l0 as L0  # noqa: E402
import s4_common as S  # noqa: E402
import s4_u3 as U3  # noqa: E402

MEAS5 = ["I_lung_vol_ml", "I_laa950_pct", "I_lung_p15_hu", "I_lung_mean_hu", "I_body_area_cm2"]
MEAS7 = MEAS5 + ["I_air_noise_sd_hu", "I_lung_z_extent_mm"]
FCOL = {"y1": "F1", "y6": "F6"}


def design(P, fcol, meas, med=None):
    M = P[meas].to_numpy(float); miss = (~np.isfinite(M)).any(1).astype(float)
    med = np.nanmedian(M, 0) if med is None else med; M = np.where(np.isfinite(M), M, med)
    return np.column_stack([P[fcol].to_numpy(float), M, miss]), med


def fi_oof(P, y, fcol, meas, fold):
    lg = np.zeros(len(P))
    for f in range(5):
        tr, te = fold != f, fold == f
        Xtr, med = design(P[tr], fcol, meas); Xte, _ = design(P[te], fcol, meas, med)
        lg[te] = L0.logit_model().fit(Xtr, y[tr]).decision_function(Xte)
    return lg


def run(E, meas, mask_extra, y):
    m = S.pop(E, y) & mask_extra; P = E[m].reset_index(drop=True); yy = P[y].to_numpy(int); pid = P.pid.to_numpy()
    fold = S.folds(pid); bt = S.Boot(pid); fi = fi_oof(P, yy, FCOL[y], meas, fold); s = P[S.HORIZONS[y][0]].to_numpy()
    out = dict(counts=S.counts(E, m, y), any_missing_share=float(np.mean(~np.isfinite(P[meas].to_numpy(float))).round(4)),
               auroc_FI=S.auc_ci(yy, fi, bt), auroc_F=S.auc_ci(yy, P[FCOL[y]].to_numpy(), bt), auroc_sybil=S.auc_ci(yy, s, bt),
               FI_minus_F=S.dauc_ci(yy, fi, P[FCOL[y]].to_numpy(), bt), sybil_minus_FI=S.dauc_ci(yy, s, fi, bt),
               sybil_adds_to_FI=S.added_value(yy, fi[:, None], S.logit(s)[:, None], pid, bt))
    return out, P, yy, fi


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("assembled"); ap.add_argument("results"); ap.add_argument("--tag", default="dev"); a = ap.parse_args()
    R = Path(a.results); E, _ = S.load(a.assembled, a.tag); res = dict(tag=a.tag); cands = []
    # R-size
    rs = {}
    for y in ("y1", "y6"):
        m = S.pop(E, y); P = E[m]; bt = S.Boot(P.pid.to_numpy())
        rs[y] = dict(counts=S.counts(E, m, y), auroc=S.auc_ci(P[y].to_numpy(float), P.max_dia.fillna(0).to_numpy(float), bt))
    res["R_size"] = dict(rs, note="partly seen (computed on test in L0): a reference only, never a hypothesis")
    # F+I
    allrows = np.ones(len(E), bool); notcut = (E.T_lung_cut_z == 0).to_numpy()
    fi = {}
    for name, meas, extra in (("primary_5_measures", MEAS5, allrows), ("sensitivity_7_measures", MEAS7, allrows), ("sensitivity_lung_not_cut", MEAS5, notcut)):
        fi[name] = {}
        for y in ("y1", "y6"):
            out, P, yy, lg = run(E, meas, extra, y); fi[name][y] = out
            if name == "primary_5_measures":
                av = out["sybil_adds_to_FI"]
                cands.append(S.candidate(f"A3_sybil_adds_to_FI_{y}", "A3 (16a), form of Q1b", "dAUROC cross-fitted (F+I + logit s) - (F+I)",
                                         f"{y}, {'all screens' if y == 'y1' else 'baseline'}", ">", 0.0, av["dauroc"], av["dauroc_halves"], out["counts"],
                                         note=f"LR test p = {av['lr']['p']:.3g}"))
                bym = {}
                for mk, g in P.groupby(P.T_maker.fillna("NA")):
                    ix = P.index.get_indexer(g.index); yk = yy[ix]
                    bym[mk] = dict(exams=int(len(ix)), cancers=int(yk.sum()), auroc_FI=S.auc(yk, lg[ix]), auroc_F=S.auc(yk, g[FCOL[y]].to_numpy()),
                                   auroc_sybil=S.auc(yk, g[S.HORIZONS[y][0]].to_numpy()), median_laa950=float(g.I_laa950_pct.median()))
                fi[name][f"{y}_by_maker"] = bym
                if y == "y1":
                    target = float(P.positive_call.to_numpy()[yy == 1].mean()); fa, sens, thr = U3.fa_per_1000(1 / (1 + np.exp(-lg)), yy, target)
                    u3 = dict(target_sensitivity=target, FI=dict(fa_per_1000=fa, sensitivity=sens))
                    p3 = R / f"s4_u3_{a.tag}.json"
                    if p3.exists(): u3["s4_u3_table"] = json.loads(p3.read_text())["table"]
                    res["U3_table_with_FI"] = u3
    res["F_plus_I"] = fi
    res["limit"] = "emphysema % depends on the scanner (Toshiba air about 38 HU low); F+I by maker is descriptive"
    # all-dev fit of the primary model, for freezing at S5
    params = {}
    for y in ("y1", "y6"):
        m = S.pop(E, y); P = E[m]; X, med = design(P, FCOL[y], MEAS5); mdl = L0.logit_model().fit(X, P[y].to_numpy(int))
        sc, lr = mdl.named_steps["standardscaler"], mdl.named_steps["logisticregression"]
        params[y] = dict(inputs=[FCOL[y]] + MEAS5 + ["any_measure_missing"], medians=med.tolist(), mean=sc.mean_.tolist(), scale=sc.scale_.tolist(),
                         coef=lr.coef_[0].tolist(), intercept=float(lr.intercept_[0]), n_fit=int(len(P)), n_fit_pos=int(P[y].sum()), C=0.3)
    pp = R / f"s4_refs_FI_params_{a.tag}.json"; pp.write_text(json.dumps(params, indent=1))
    res["FI_params_file"] = dict(path=pp.name, sha256=hashlib.sha256(pp.read_bytes()).hexdigest())
    res["candidates"] = cands
    S.write(R, f"s4_refs_{a.tag}.json", res)
    print(f"s4_refs: written; F+I params {pp.name}")


if __name__ == "__main__":
    main()
