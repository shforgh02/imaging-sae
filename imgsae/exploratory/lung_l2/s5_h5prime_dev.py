"""Lung L2, step N1 item 1 (new freeze; dev only): the dev evidence for H5' (docs/REVIEW_S5_L2.md, "What I propose instead").
H5': on the z-fix exams (D5 on dev, T5 on test: spacing/thickness <= 0.65), the mean of G_T(zfix) - G_T(main) for lbar_1, where G_T is the
exact contribution of the 6 T-named raw-unit families (frozen dictionary and labels of the first freeze, results/s5/). Direction <, null -0.02.
Also: the same change for the N, mixed, unreplicated, intercept and residual terms and for lbar_1 itself; the part of the mean shift of
lbar_1 carried by each term; the share of exams whose T term falls; and the RANDOM-CHOICE TEST asked by the lead's prompt: random sets of 6
of the 56 families (20,000 draws, seed 0, without replacement): how often is their mean z-fix change below -0.02? (If 5% or more pass, the
executor stops and tells the lead before freezing H5'.) Participant bootstrap, 2,000 draws, seed 0 (s4_common.Boot). Halves: two
participant folds, seed 0, reported both ways (folds drawn on the D5 participants, as s4_q1d.block; and on all dev participants, then
restricted, as the step R scripts). Nothing is fitted. No outcome is read.
usage (venv python): python s5_h5prime_dev.py <assembled dev dir> <frozen dir (results/s5)> <heads npz> <out json>
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import s4_common as S  # noqa: E402
import s4_q1d as QD  # noqa: E402

NULL, N_SETS = -0.02, 20000


def frozen_raw(FZ):
    """the frozen raw-unit arm (K = 64) and its 56 labelled families, rebuilt from results/s5/ exactly as s6_frozen_analysis.py does."""
    z = np.load(FZ / "frozen_raw_arm_K64.npz"); arms = []
    for m in range(5):
        a = S.C.Arm("raw", 64, 0); a.mu, a.sd, a.live, a.sel = (z[f"m{m}_{k}"] for k in ("mu", "sd", "live", "sel"))
        a.live = a.live.astype(bool); n_live = int(a.live.sum()); a.off, a.c, a.D = a.mu, np.zeros(n_live), np.eye(n_live)[a.sel]; arms.append(a)
    fj = json.loads((FZ / "frozen_families_raw_K64.json").read_text())
    fams = [({int(m): int(f) for m, f in d["members"].items()}, {int(m): float(s) for m, s in d["signs"].items()}) for d in fj]
    return arms, fams, {d["family"]: d["label"] for d in fj}


def family_terms(Hh, arms, fams, heads, t):
    """per-family exact contributions (n, n_families) to lbar_t, and the other terms (unreplicated, intercept, residual); same mapping as
    s4_common.split_by_label (so the sum over the T families equals its 'T' term)."""
    fam_of = [dict() for _ in range(5)]
    for k, (fam, _) in enumerate(fams):
        for m, f in fam.items(): fam_of[m][f] = k
    G = np.zeros((len(Hh), len(fams))); other = dict(unreplicated=np.zeros(len(Hh)), intercept=np.zeros(len(Hh)), residual=np.zeros(len(Hh)))
    for m in range(5):
        A = arms[m].encode(Hh[:, m]); ic, ct, rs = S.C.contributions(Hh[:, m], A, arms[m], heads[m], t)
        other["intercept"] += ic / 5; other["residual"] += rs / 5
        for i in range(ct.shape[1]):
            if i in fam_of[m]: G[:, fam_of[m][i]] += ct[:, i] / 5
            else: other["unreplicated"] += ct[:, i] / 5
    return G, other


def main():
    A, FZ, heads_p, out_p = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])
    E, arr = S.load(A, "dev"); heads = S.C.load_heads(heads_p); arms, fams, lab_of = frozen_raw(FZ)
    Z, Hz = QD.variant_frame(A, "dev", "zfix")
    J = E.merge(Z[["series_uid", "v_l1"]], on="series_uid"); Hz = Hz[[Z.series_uid.tolist().index(u) for u in J.series_uid]]
    d5 = (J.ratio <= 0.65).to_numpy(); J, Hz = J[d5].reset_index(drop=True), Hz[d5]
    rowpos = {u: i for i, u in enumerate(E.series_uid)}; Hm = arr["h"][[rowpos[u] for u in J.series_uid]].astype(np.float64)
    pid = J.pid.to_numpy(); bt = S.Boot(pid)
    hv_sub = S.halves(pid); hv_all = dict(zip(E.pid, S.halves(E.pid.to_numpy()))); hv_all = np.array([hv_all[p] for p in pid])
    Gz, Oz = family_terms(Hz, arms, fams, heads, 1); Gm, Om = family_terms(Hm, arms, fams, heads, 1)
    dG = Gz - Gm; lab = np.array([lab_of[k] for k in range(len(fams))])
    terms = {g: dG[:, lab == g].sum(1) for g in sorted(set(lab))}
    terms.update({k: Oz[k] - Om[k] for k in Oz})
    # exactness: the terms add up to the change of lbar_1 (saved logits), and the T term equals split_by_label's
    dl = (J.v_l1 - J.lbar1).to_numpy(); tot = sum(terms.values()); chk = float(np.abs(tot - dl).max())
    sl = S.split_by_label(Hz, arms, fams, lab_of, heads, 1)["T"] - S.split_by_label(Hm, arms, fams, lab_of, heads, 1)["T"]
    assert chk < 1e-3 and np.abs(sl - terms["T"]).max() < 1e-9, (chk, np.abs(sl - terms["T"]).max())
    mean_ci = lambda v: dict(bt.ci(lambda t: float(v[t].mean())), halves_d5_folds=[float(v[hv_sub == h].mean()) for h in (0, 1)],
                             halves_all_dev_folds=[float(v[hv_all == h].mean()) for h in (0, 1)])   # noqa: E731
    res = dict(script="s5_h5prime_dev.py", population="D5: dev z-fix exams with spacing/thickness <= 0.65 (main ratio), all screens",
               counts=dict(exams=int(len(J)), participants=int(J.pid.nunique()), cancers_y1=int((J.y1 == 1).sum())),
               max_abs_error_terms_vs_saved_delta_lbar1=chk, null=NULL, direction="<",
               H5prime=dict(statistic="mean of G_T(zfix) - G_T(main), lbar_1, frozen raw-unit dictionary and labels (6 T families)", **mean_ci(terms["T"]),
                            share_exams_T_term_falls=float((terms["T"] < 0).mean())),
               delta_lbar1=mean_ci(dl), terms={k: mean_ci(v) for k, v in terms.items()},
               part_of_mean_shift={k: bt.ci(lambda t, v=v: float(v[t].mean() / dl[t].mean())) for k, v in terms.items()})
    gate = res["H5prime"]; res["H5prime"]["gate_9_8"] = bool(gate["est"] < NULL and gate["hi"] < NULL and all(h < NULL for h in gate["halves_d5_folds"] + gate["halves_all_dev_folds"]))
    # ---- random-choice test: random sets of 6 of the 56 families
    c = dG.mean(0); rng = np.random.default_rng(0); n_t = int((lab == "T").sum())
    sets = np.array([rng.choice(len(fams), n_t, replace=False) for _ in range(N_SETS)]); r = c[sets].sum(1)
    res["random_choice"] = dict(n_sets=N_SETS, set_size=n_t, n_families=len(fams), seed=0,
                                share_below_null=float((r < NULL).mean()), share_at_or_below_T_value=float((r <= gate["est"]).mean()),
                                mean=float(r.mean()), median=float(np.median(r)), p2_5=float(np.quantile(r, 0.025)), p97_5=float(np.quantile(r, 0.975)),
                                min=float(r.min()), max=float(r.max()), rule="if share_below_null >= 0.05, H5' is near-automatic: stop and tell the lead",
                                passes_rule=bool((r < NULL).mean() < 0.05))
    res["per_family_mean_change"] = [dict(family=k, label=str(lab[k]), mean_change=float(c[k])) for k in range(len(fams))]
    res["mean_change_per_family_by_label"] = {g: float(c[lab == g].mean()) for g in sorted(set(lab))}
    out_p.parent.mkdir(parents=True, exist_ok=True); out_p.write_bytes((json.dumps(res, indent=1) + "\n").encode("utf-8"))
    print(json.dumps({k: v for k, v in res.items() if k != "per_family_mean_change"}, indent=1))


if __name__ == "__main__":
    main()
