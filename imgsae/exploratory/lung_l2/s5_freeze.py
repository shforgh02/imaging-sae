"""Lung L2, step S5 (docs/LUNG_L2_PROTOCOL.md section 10; plan P5) and its second freeze (step N1, 2026-11-17): write the frozen files the
S6 analysis reads. Dev only.
Writes into <out dir> (results/s5/):
- frozen_raw_arm_K64.npz: the primary arm (raw units, K = 64) as plain numbers per member: dev mean and SD of h, live units, the 64
  selected units (so the S6 code rebuilds the arm without a pickle); kept byte-identical if its content is unchanged;
- frozen_families_raw_K64.json: the 56 replicated families (member -> unit, sign) with their dev labels (N, T, mixed);
- frozen_FI_params.json: the F+I model fitted on all dev (copy of s4_refs_FI_params_dev.json; amendment A3);
- frozen_combinations.json: secondary references only (not hypotheses): plain logistic fits on all dev of y1 ~ logit(s1) + F1 (U3's C)
  and of y ~ (F+I logit) + logit(s_t) (A3), coefficients on the raw scale;
- frozen_thresholds_L2.json: thresholds, SD references, populations, the hypotheses (statistic, population, direction, null, test),
  Holm, bootstrap, fallbacks, the S6 run plan, and the SHA-256 of every frozen file and input.
- frozen_axes_pooled.npz is written by s5_axes_freeze.py (step F3) and must exist before this runs; its hash enters the list here.
Second freeze (N1): H5 -> H5prime (or secondary, by the lead's choice), H6 and H7 from step R (amendment A6), H4 renamed, H3 worded with
both flag directions, new secondary items (flags lost and gained, term changes, old H5, H6 and H7 details, harm estimates, attention),
tau90_s6 for the harm estimates, the S6 run plan on two accounts, and the three text inputs hashed on their LF bytes.
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

# The lead's choice on H5prime (2026-11-17), set before the freeze runs: True = H5prime in the Holm family; False = secondary only.
# H5prime failed its random-choice test on dev (59.7% of random sets of 6 families pass; s5_h5prime_dev.json); the lead chose
# "Move H5' to secondary (Recommended)" on 2026-11-17 (docs/EXECUTION_LOG.md). Family: H1, H2, H3, H4, H6, H7.
H5PRIME_IN_FAMILY = False


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sha_lf(p):
    """SHA-256 of a text file's LF bytes (as git stores it), so the value is the same on every checkout (review change 5)."""
    return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def write_json(p, obj):
    """LF line endings on every system, so the SHA-256 is the same on any checkout (results/s5 is '-text' in .gitattributes)."""
    Path(p).write_bytes((json.dumps(obj, indent=1) + "\n").encode("utf-8"))


def write_npz_keep(p, arrs):
    """write an npz, but keep an existing file byte-identical if it holds exactly the same arrays (zip timestamps would change the hash)."""
    p = Path(p)
    if p.exists():
        z = np.load(p)
        if set(z.files) == set(arrs) and all(np.array_equal(z[k], np.asarray(v)) and z[k].dtype == np.asarray(v).dtype for k, v in arrs.items()): return "kept"
    np.savez(p, **arrs); return "written"


def plain_logit(y, X):
    m = LogisticRegression(C=1e6, max_iter=5000).fit(X, y); return dict(coef=m.coef_[0].tolist(), intercept=float(m.intercept_[0]), n=int(len(y)), n_pos=int(y.sum()))


def hypotheses():
    T5 = "T5: test z-fix variants of T1 to T3 main series with spacing/thickness <= 0.65 (all screens); exams with a recorded ratio of 0 have no z-fix row and are not in T5"
    wald = "one-sided Wald, participant-bootstrap SE (2,000 draws, seed 0); p = 0 (right side of the null) or 1 if the bootstrap SD is 0"
    H = [
        dict(id="H1", name="z-fix moves Sybil's score materially", statistic="share of T5 exams with |lbar6(zfix) - lbar6(main)| >= 0.25 x sd_ref_lbar6_all_dev_main",
             population=T5, direction=">", null=0.30, margin=0.30, test=wald, source="U1b (protocol 9.7), Q1d (ii)", dev=dict(est=0.670, ci=[0.638, 0.701], halves=[0.669, 0.671])),
        dict(id="H2", name="z-fix lowers Sybil's score", statistic="mean of lbar1(zfix) - lbar1(main)", population="T5", direction="<", null=-0.10, margin=-0.10,
             test=wald, source="Q1d (ii)", dev=dict(est=-0.326, ci=[-0.366, -0.282], halves=[-0.320, -0.332])),
        dict(id="H3", name="z-fix changes the tau90 flag (in both directions: flags are lost and gained)",
             statistic="share of T5 exams with [s1(main) >= tau90_s1] != [s1(zfix) >= tau90_s1]", population="T5", direction=">", null=0.05, margin=0.05,
             test=wald, source="Q1d (ii) / U1b", dev=dict(est=0.0747, ci=[0.0558, 0.0971], halves=[0.0741, 0.0753], flags_main=112, flags_zfix=105, lost=38, gained=31,
                                                          discordant_share_of_flagged_in_either=0.48)),
        dict(id="H4", name="the kernel changes the tau90 flag in fewer than 5% of exams", statistic="share of T4 pairs with [s1(sharp) >= tau90_s1] != [s1(soft) >= tau90_s1]",
             population="T4: the 500 soft-kernel partners of T1 exams (and their main series)", direction="<", null=0.05, margin=0.05,
             test=wald, source="Q1d (i)", dev=dict(est=0.018, ci=[0.008, 0.030], halves=[0.028, 0.008], flags_sharp=64, flags_soft=61, changed=9, discordant_share_of_flagged_in_either=0.13))]
    H5p = dict(id="H5prime", name="z-fix moves the term of the technical-named features (H5', replaces H5 of the first freeze)",
               statistic="mean over T5 exams of G_T(zfix) - G_T(main) for lbar1; G_T = exact contribution of the 6 T-named raw-unit families (frozen dictionary and labels of the first freeze)",
               population="T5", direction="<", null=-0.02, margin=-0.02, test=wald, source="docs/REVIEW_S5_L2.md (H5'); s5_h5prime_dev.py", feature_based=True,
               dev=dict(est=-0.0566, ci=[-0.0590, -0.0541], halves=[-0.0565, -0.0567], random_choice_share_below_null=0.597))
    H6 = dict(id="H6", name="shared axis 0 of `pooled` (z-geometry) carries the z-fix drop of Sybil's score",
              statistic=("mean over T5 exams of [delta lbar1 with shared axis 0 set to the dev mean in every member] - [delta lbar1 as Sybil gives it]; delta = z-fix minus main; "
                         "lbar1 = mean of the five member logits computed from the saved `pooled` through Sybil's own hidden_fc, ReLU and head; frozen dev axis "
                         "(frozen_axes_pooled.npz), no refit, no outcome"),
              population="T5", direction=">", null=0.20, margin=0.20, test=wald, source="step R, candidate C2 (RESULTS_R_dev.md section 6; r6_candidate.py); amendment A6", feature_based=True,
              dev=dict(est=0.408, ci=[0.403, 0.412], halves=[0.412, 0.404], random_choice_share_passing=0.0005, random_choice_max=0.226))
    H7 = dict(id="H7", name="in real follow-up, Sybil's 1-year score jumps when a yearly screen changes between stretched and not stretched, beyond the form",
              statistic=("b in the OLS fit delta lbar1 = a + b x delta stretched + c x delta F1 over pairs of consecutive yearly screens of one participant (T0->T1, T1->T2; main runs); "
                         "delta = later minus earlier; lbar1 = mean member logit of the main run (saved logits); stretched = 1 if spacing/thickness <= 0.65 as recorded in the "
                         "series geometry (a recorded ratio of 0, i.e. duplicated slice positions, counts as stretched, as on dev), else 0; F1 = the frozen form model's "
                         "1-year logit (results/l2_form_params.json); no outcome, no refit"),
              population="test participants with two consecutive yearly screens among the T1, T2, T3 main runs", direction=">", null=0.10, margin=0.10,
              test=wald + "; bootstrap unit = participant (a participant can give two pairs)", source="step R2, candidate C3 (RESULTS_R_dev.md section 9A; r7_more.py); amendment A6",
              partly_seen=True,
              partly_seen_note=("protocol 10: an approximate version (logit of the L1 published score instead of lbar1, the stretch status from the public IDC metadata) "
                                "is computable from the L1 test scores, the form and public metadata, so H7 is labelled 'partly seen' (the only one in the family). "
                                "It was never computed: no L1 script reads spacing, thickness or stretch, and the L1 test scores have not been analysed since L1; "
                                "L1 post hoc saw only the overall correlation of the test logits between T0 and T1 of the same participant (r = 0.61; "
                                "lung_l1/posthoc/posthoc_sybil_vs_form.py), not split by stretch."),
              dev=dict(est=0.246, ci=[0.134, 0.355], halves=[0.222, 0.272], pairs=4837, changed=215, permutation_share_above_null=0.025))
    fam = H + ([H5p] if H5PRIME_IN_FAMILY else []) + [H6, H7]
    return fam, (None if H5PRIME_IN_FAMILY else H5p)


def main():
    if H5PRIME_IN_FAMILY is None: raise SystemExit("STOP: set H5PRIME_IN_FAMILY from the lead's choice before the freeze")
    A, R4, RI, OUT = (Path(x) for x in sys.argv[1:5]); OUT.mkdir(parents=True, exist_ok=True)
    if not (OUT / "frozen_axes_pooled.npz").exists(): raise SystemExit("STOP: run s5_axes_freeze.py first (frozen_axes_pooled.npz missing)")
    pk = S.DATA / "arms" / "arms_dev_raw_K64.pkl"; obj = pickle.load(open(pk, "rb")); arms, fams = obj["arms"], obj["families"]
    npz_state = write_npz_keep(OUT / "frozen_raw_arm_K64.npz", {f"m{m}_{k}": np.asarray(getattr(arms[m], k)) for m in range(5) for k in ("mu", "sd", "live", "sel")})
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
    # thresholds and references, from the committed S4 result files (+ tau90_s6 for the harm estimates, the S4 Q2 miss rule at 6 years)
    q1d = json.loads((R4 / "s4_q1d_dev.json").read_text()); q2 = json.loads((R4 / "s4_q2_dev.json").read_text())
    neg6 = S.pop(E, "y6") & (E.y6 == 0).to_numpy()
    th = dict(tau90_s1=q2["thresholds"]["tau90"], tau90_F1=q2["thresholds"]["tau90_F"], sd_ref_lbar6_all_dev_main=q1d["sd_lbar6_all"],
              sd_ref_lbar1_all_dev_main=q1d["sd_lbar1_all"], zfix_ratio_max=0.65, quarter_sd=0.25,
              tau90_s6=float(np.quantile(E.loc[neg6, "s6"], 0.90)), tau90_s6_rule="90th percentile of s6 among dev baseline exams with y6 = 0 (S4 Q2 miss rule at 6 years)")
    assert abs(th["tau90_s1"] - q1d["tau90"]) < 1e-15
    hyp, h5p_secondary = hypotheses()
    files = {p.name: sha(p) for p in sorted(OUT.glob("frozen_*")) if p.name != "frozen_thresholds_L2.json"}
    inputs = {"heads.npz": sha(RI / "heads.npz"), "sybil_ensemble_simple_calibrator.json": sha(RI / "sybil_ensemble_simple_calibrator.json"),
              "arms_dev_raw_K64.pkl (source of the frozen arm)": sha(pk), "s4_families_dev_raw_K64.csv": sha_lf(R4 / "s4_families_dev_raw_K64.csv"),
              "l2_form_params.json (F)": sha_lf(HERE / "results" / "l2_form_params.json"), "manifest_dev.csv": sha_lf(HERE / "results" / "manifest_dev.csv"),
              "r2_shared_pooled.pkl (source of the frozen axes; L2_S4_DATA/r)": sha(S.DATA / "r" / "r2_shared_pooled.pkl")}
    secondary = ["AUROC (participant bootstrap) of Sybil s1 (y1, all screens), s6 (y6, baseline), F1, F6, R-size, F+I (frozen parameters)",
                 "frozen A3 combination: (F+I + Sybil) minus F+I, y1 and y6", "frozen U3 table: false alarms per 1,000 at the radiologists' test sensitivity for the call, Sybil, F, C, F+I",
                 "descriptive: z-fix and kernel statistics by stretch class, lung cut and maker; group shares of all terms",
                 "flags in both directions (z-fix in T5 and kernel in T4): flagged in each run, flags lost, flags gained, share of discordant flags among exams flagged in either run",
                 "z-fix change of every term of lbar1 (N, T, mixed, unreplicated, intercept, residual) and the part of the mean shift carried by each",
                 "old H5 of the first freeze: Cov(G_T, lbar1) / Var(lbar1) on all main exams (near-automatic; review)",
                 "H6 details: C1 = mean z-fix change of axis 0 in dev SD units (dev -2.740; null -2.0 stated, not tested); for each of the 11 frozen axes the agreement of the five members "
                 "(mean pairwise r; how many reach 0.70), the z-fix change and the kernel change in dev SD units; share of T5 exams moving >= 0.25 SD (lbar6) with axis 0 off (dev 0.550); "
                 "AUROC with axis 0 off, y1 and y6 (caution C6: dev flatters Sybil)",
                 "H7 details: b with axis 0 switched off (dev -0.094); the jump of axis 0 per stretch change in dev SD units (dev 2.29); same scanner model subset; group means "
                 "(stretched to not, unchanged, not to stretched); flag flips by group; b with recorded ratio 0 counted as not stretched (dev +0.227); "
                 "'both screens without cancer within 1 year' sensitivity (uses outcomes; computed after the primary result is saved)",
                 "harm estimates in T5 (pre-stated, never a hypothesis): sensitivity at tau90_s1 (y1, all screens) and at tau90_s6 (y6, baseline screens) for the main and the z-fix "
                 "run, exact (Clopper-Pearson) intervals, the paired counts and the bootstrap interval of the paired difference; AUROC of s_t for main and z-fix and their paired "
                 "difference (participant bootstrap)",
                 "where Sybil looks (s6_attention.py; descriptive): slice attention within +-1 bin of the largest recorded nodule against shuffled nodule bins, peak within 1 bin, "
                 "in-plane attention on the nodule's lung side; conventions frozen from dev (box order reversed; patient right = image left)"]
    if h5p_secondary: secondary.append("H5prime (moved to the secondary list by the lead): " + h5p_secondary["statistic"] + "; dev " + json.dumps(h5p_secondary["dev"]))
    fallbacks = ["if T3 is not scored: H1, H2, H3, H5prime and H6 use the T5 rows of T1 and T2; H7 uses the T0->T1 pairs only (stated before the run)",
                 "if T4 is not scored, H4 is 'not evaluated' and counts as not confirmed",
                 "if no T5 row is scored, H1, H2, H3, H5prime and H6 are 'not evaluated' and count as not confirmed",
                 "if T2 is not scored (for example, the identity check on forghanishayan fails), H7 has no consecutive pair and is 'not evaluated' (counts as not confirmed); "
                 "the z-fix hypotheses use the T5 rows of T1 (and T3 if scored)",
                 "a hypothesis that is not evaluated keeps its place in the Holm family (m stays the family size)"]
    run_plan = dict(accounts={
        "armanfo": dict(order=["smoke (demo case + 3 test series)", "T1 baseline (2,279 main rows, with their z-fix variants)", "T4 (500 soft-kernel partners of T1 exams)"],
                        cost_usd=7.4, cost_with_10pct_reserve_usd=8.1, limits="project limit on armanfo $27.00 (used $14.03 on 2026-11-17); month cap $29.50 (used $15.69 on 2026-11-17)"),
        "forghanishayan": dict(order=["identity check (a few series already scored on armanfo must give equal numbers to the last digit, as in S3)",
                                      "T2 year 1 (2,243 main rows, with their z-fix variants)", "T3 year 2 (2,193 main rows, with their z-fix variants)"],
                               cost_usd=12.0, cost_with_10pct_reserve_usd=13.2, limits="project limit on forghanishayan $20.00; month cap $29.50 (used $5.02 on 2026-11-17); the lead's deployed app there is never touched")},
        total_usd=19.4, total_with_reserve_usd=21.3, task_budget_left_usd=23.30, allowed_usd=22.30, when="November 2026, after the re-check (N2) and the lead's OK (N3)",
        rates="billed S3 rates: main rows with z-fix variants $0.0026 per row, pair rows $0.0023; smoke and image rebuild about $0.30 per account",
        rule="every launch through the guard (budget.py) with MODAL_PROFILE set per command; all main runs with --zfix-max 0.65; unattended driver (A5)")
    out = dict(created="2026-11-16", second_freeze="2026-11-17 (step N1; first freeze c593005)", protocol="docs/LUNG_L2_PROTOCOL.md section 10; amendment A6", s4_code_commit="a536192",
               thresholds=th, primary_arm=dict(arm="raw", K=64, n_families=len(fam_json), labels={k: int(sum(f["label"] == k for f in fam_json)) for k in sorted({f["label"] for f in fam_json})}),
               shared_axes=dict(file="frozen_axes_pooled.npz", layer="pooled", n_axes=11, npc=30, axis_used_by_H6_H7=0, axis_0_name="z-geometry (lung cut in z, real slices, z-stretch)",
                                source="r2_shared.py fitted on all 7,336 dev main exams (never on z-fix or test data); s5_axes_freeze.py"),
               hypotheses=hyp, holm=dict(alpha=0.05, one_sided=True, family=[h["id"] for h in hyp]),
               bootstrap=dict(unit="participant", draws=2000, seed=0, interval="95% percentile; p from the Wald statistic (est - null) / SD of the draws; SD 0 -> p = 0 on the stated side, else 1"),
               fallbacks=fallbacks, secondary=secondary, s6_run_plan=run_plan, frozen_files_sha256=files, inputs_sha256=inputs)
    write_json(OUT / "frozen_thresholds_L2.json", out)
    print(json.dumps(dict(frozen_raw_arm_K64=npz_state, files=files, thresholds=th, family=out["holm"]["family"]), indent=1))


if __name__ == "__main__":
    main()
