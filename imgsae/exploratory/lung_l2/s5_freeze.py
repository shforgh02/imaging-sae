"""Lung L2, step S5 (docs/LUNG_L2_PROTOCOL.md section 10; plan P5): write the frozen files the S6 analysis reads. Dev only.
Writes into <out dir> (results/s5/):
- frozen_raw_arm_K64.npz: the primary arm (raw units, K = 64) as plain numbers per member: dev mean and SD of h, live units, the 64
  selected units (so the S6 code rebuilds the arm without a pickle);
- frozen_families_raw_K64.json: the 56 replicated families (member -> unit, sign) with their dev labels (N, T, mixed);
- frozen_FI_params.json: the F+I model fitted on all dev (copy of s4_refs_FI_params_dev.json; amendment A3);
- frozen_combinations.json: secondary references only (not hypotheses): plain logistic fits on all dev of y1 ~ logit(s1) + F1 (U3's C)
  and of y ~ (F+I logit) + logit(s_t) (A3), coefficients on the raw scale;
- frozen_thresholds_L2.json: thresholds, SD references, populations, the hypotheses (statistic, population, direction, null, test),
  Holm, bootstrap, fallbacks, the S6 run plan, and the SHA-256 of every frozen file and input.
usage (venv python): python s5_freeze.py <assembled dev dir> <results s4 dir> <run_info dir> <out dir>
"""
import hashlib
import json
import pickle
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import s4_common as S  # noqa: E402
import s4_refs as RF  # noqa: E402


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write_json(p, obj):
    """LF line endings on every system, so the SHA-256 is the same on any checkout (results/s5 is '-text' in .gitattributes)."""
    Path(p).write_bytes((json.dumps(obj, indent=1) + "\n").encode("utf-8"))


def plain_logit(y, X):
    m = LogisticRegression(C=1e6, max_iter=5000).fit(X, y); return dict(coef=m.coef_[0].tolist(), intercept=float(m.intercept_[0]), n=int(len(y)), n_pos=int(y.sum()))


def main():
    A, R4, RI, OUT = (Path(x) for x in sys.argv[1:5]); OUT.mkdir(parents=True, exist_ok=True)
    pk = S.DATA / "arms" / "arms_dev_raw_K64.pkl"; obj = pickle.load(open(pk, "rb")); arms, fams = obj["arms"], obj["families"]
    np.savez(OUT / "frozen_raw_arm_K64.npz", **{f"m{m}_{k}": np.asarray(getattr(arms[m], k)) for m in range(5) for k in ("mu", "sd", "live", "sel")})
    F = S.family_table(R4, "dev", "raw", 64); lab = dict(zip(F.family.astype(int), F.label))
    fam_json = [dict(family=k, label=lab[k], members={str(m): int(f) for m, f in fam.items()}, signs={str(m): float(s) for m, s in sg.items()}) for k, (fam, sg) in enumerate(fams)]
    write_json(OUT / "frozen_families_raw_K64.json", fam_json)
    write_json(OUT / "frozen_FI_params.json", json.loads((R4 / "s4_refs_FI_params_dev.json").read_text()))   # same content, LF
    # secondary references: frozen combinations fitted on all dev
    E, _ = S.load(A, "dev"); FI = json.loads((OUT / "frozen_FI_params.json").read_text()); comb = {}
    m1 = S.pop(E, "y1"); P = E[m1]; comb["U3_C_y1"] = dict(inputs=["logit(s1)", "F1"], **plain_logit(P.y1.to_numpy(int), np.column_stack([S.logit(P.s1), P.F1])))
    for y, s, fcol in (("y1", "s1", "F1"), ("y6", "s6", "F6")):
        m = S.pop(E, y); P = E[m]; prm = FI[y]; X, _ = RF.design(P, fcol, RF.MEAS5, np.array(prm["medians"]))
        fi = ((X - np.array(prm["mean"])) / np.array(prm["scale"])) @ np.array(prm["coef"]) + prm["intercept"]
        comb[f"A3_FI_plus_sybil_{y}"] = dict(inputs=["F+I logit", f"logit({s})"], **plain_logit(P[y].to_numpy(int), np.column_stack([fi, S.logit(P[s])])))
    write_json(OUT / "frozen_combinations.json", comb)
    # thresholds and references, from the committed S4 result files
    q1d = json.loads((R4 / "s4_q1d_dev.json").read_text()); q2 = json.loads((R4 / "s4_q2_dev.json").read_text())
    th = dict(tau90_s1=q2["thresholds"]["tau90"], tau90_F1=q2["thresholds"]["tau90_F"], sd_ref_lbar6_all_dev_main=q1d["sd_lbar6_all"],
              sd_ref_lbar1_all_dev_main=q1d["sd_lbar1_all"], zfix_ratio_max=0.65, quarter_sd=0.25)
    assert abs(th["tau90_s1"] - q1d["tau90"]) < 1e-15
    hyp = [
        dict(id="H1", name="z-fix moves Sybil's score materially", statistic="share of T5 exams with |lbar6(zfix) - lbar6(main)| >= 0.25 x sd_ref_lbar6_all_dev_main",
             population="T5: test z-fix variants with spacing/thickness <= 0.65 (all screens)", direction=">", null=0.30, margin=0.30,
             test="one-sided Wald, participant-bootstrap SE (2,000 draws, seed 0)", source="U1b (protocol 9.7), Q1d (ii)"),
        dict(id="H2", name="z-fix lowers Sybil's score", statistic="mean of lbar1(zfix) - lbar1(main)", population="T5", direction="<", null=-0.10, margin=-0.10,
             test="one-sided Wald, participant-bootstrap SE", source="Q1d (ii)"),
        dict(id="H3", name="z-fix changes the tau90 flag", statistic="share of T5 exams with [s1(main) >= tau90_s1] != [s1(zfix) >= tau90_s1]", population="T5",
             direction=">", null=0.05, margin=0.05, test="one-sided Wald, participant-bootstrap SE", source="Q1d (ii) / U1b"),
        dict(id="H4", name="kernel change rarely changes the tau90 flag", statistic="share of T4 pairs with [s1(sharp) >= tau90_s1] != [s1(soft) >= tau90_s1]",
             population="T4: the 500 soft-kernel partners of T1 exams (and their main series)", direction="<", null=0.05, margin=0.05,
             test="one-sided Wald, participant-bootstrap SE", source="Q1d (i)"),
        dict(id="H5", name="technical-named features carry a part of Sybil's score",
             statistic="Cov(G_T, lbar1) / Var(lbar1): share of the variance of lbar1 carried by the 6 T-named raw-unit families (frozen dictionary, frozen labels)",
             population="all scored test main exams (T1, T2, T3)", direction=">", null=0.03, margin=0.03, test="one-sided Wald, participant-bootstrap SE",
             source="Q1b group shares (protocol 9.2, 9.7); feature-based (valid arm: raw units)", feature_based=True)]
    files = {p.name: sha(p) for p in sorted(OUT.glob("frozen_*")) if p.name != "frozen_thresholds_L2.json"}
    inputs = {"heads.npz": sha(RI / "heads.npz"), "sybil_ensemble_simple_calibrator.json": sha(RI / "sybil_ensemble_simple_calibrator.json"),
              "arms_dev_raw_K64.pkl (source of the frozen arm)": sha(pk), "s4_families_dev_raw_K64.csv": sha(R4 / "s4_families_dev_raw_K64.csv"),
              "l2_form_params.json (F)": sha(HERE / "results" / "l2_form_params.json"), "manifest_dev.csv": sha(HERE / "results" / "manifest_dev.csv")}
    out = dict(created="2026-11-16", protocol="docs/LUNG_L2_PROTOCOL.md section 10", s4_code_commit="a536192", thresholds=th,
               primary_arm=dict(arm="raw", K=64, n_families=len(fam_json), labels={k: int(sum(f["label"] == k for f in fam_json)) for k in sorted({f["label"] for f in fam_json})}),
               hypotheses=hyp, holm=dict(alpha=0.05, one_sided=True, family=[h["id"] for h in hyp]),
               bootstrap=dict(unit="participant", draws=2000, seed=0, interval="95% percentile; p from the Wald statistic (est - null) / SD of the draws"),
               fallbacks=["if T3 is not scored, H1 to H3 use the T5 rows of T1 and T2, and H5 uses T1 and T2 exams (stated before the run)",
                          "if T4 is not scored, H4 is 'not evaluated' and counts as not confirmed", "if T5 is not scored, H1 to H3 are 'not evaluated' and count as not confirmed"],
               secondary=["AUROC (participant bootstrap) of Sybil s1 (y1, all screens), s6 (y6, baseline), F1, F6, R-size, F+I (frozen parameters)",
                          "frozen A3 combination: (F+I + Sybil) minus F+I, y1 and y6", "frozen U3 table: false alarms per 1,000 at the radiologists' test sensitivity for the call, Sybil, F, C, F+I",
                          "descriptive: z-fix and kernel statistics by stretch class, lung cut and maker; group shares of all terms"],
               frozen_files_sha256=files, inputs_sha256=inputs)
    write_json(OUT / "frozen_thresholds_L2.json", out)
    print(json.dumps(dict(files=files, thresholds=th), indent=1))


if __name__ == "__main__":
    main()
