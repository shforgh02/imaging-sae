"""Lung L2, step S6: the frozen analysis (docs/LUNG_L2_PROTOCOL.md sections 10 and 11; second freeze, step N1). Runs once on test after the lead's OK.
It reads only the frozen files of S5 (results/s5/, SHA-256 checked against frozen_thresholds_L2.json before anything else), Sybil's head
weights and calibrator (hash-checked), and the assembled exam table and arrays of one root (l2_data.py output). Nothing is fitted: the
dictionary, the family labels, the shared axes of `pooled`, the thresholds, the SD references, the F+I parameters, the form model and the
secondary combinations are the frozen dev values.
Primary hypotheses: the ids in frozen_thresholds_L2.json -> holm.family (one-sided, Holm, family-wise alpha 0.05; participant bootstrap,
2,000 draws, seed 0; p from the Wald statistic (est - null) / SD of the draws; if that SD is 0, p = 0 when the estimate is on the stated
side of the null, else p = 1). Statistics computed here:
  H1, H2, H3 (z-fix, T5), H4 (kernel pairs, T4)           - unchanged from the first freeze (c593005);
  H5prime: mean of G_T(zfix) - G_T(main), lbar_1, frozen raw-unit dictionary and labels (T5);
  H6: mean over T5 exams of [delta lbar_1 with shared axis 0 of `pooled` set to the dev mean in every member] - [delta lbar_1 as Sybil
      gives it]; delta = z-fix minus main; lbar_1 from the saved `pooled` through Sybil's own hidden_fc, ReLU and head;
  H7: b in the OLS fit  delta lbar_1 = a + b * delta stretched + c * delta F1  over pairs of consecutive yearly screens of one participant
      (main runs; delta = later minus earlier; stretched = spacing/thickness <= 0.65 as recorded; F1 = the frozen form model's 1-year logit).
A statistic whose id is not in holm.family is reported under 'secondary' (never called confirmed). Secondary references are outside the
Holm family and labelled secondary; anything else is exploratory (protocol 11).
Tested end to end on dev ("dev as if test", root dev): it must reproduce the S4 and step R dev numbers.
usage (venv python): python s6_frozen_analysis.py <assembled dir> <root: dev|test> <frozen dir (results/s5)> <run_info dir> <out json>
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import s4_common as S  # noqa: E402
import s4_q1d as QD  # noqa: E402
import s4_refs as RF  # noqa: E402
import s4_u3 as U3  # noqa: E402
import s5_axes_freeze as AXF  # noqa: E402


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_frozen(FZ, RI):
    T = json.loads((FZ / "frozen_thresholds_L2.json").read_text())
    bad = [n for n, h in T["frozen_files_sha256"].items() if sha(FZ / n) != h]
    for n, p in (("heads.npz", RI / "heads.npz"), ("sybil_ensemble_simple_calibrator.json", RI / "sybil_ensemble_simple_calibrator.json")):
        if sha(p) != T["inputs_sha256"][n]: bad.append(n)
    if bad: raise SystemExit(f"REFUSED: frozen files changed: {bad}")
    z = np.load(FZ / "frozen_raw_arm_K64.npz"); arms = []
    for m in range(5):
        a = S.C.Arm("raw", 64, 0); a.mu, a.sd, a.live, a.sel = (z[f"m{m}_{k}"] for k in ("mu", "sd", "live", "sel"))
        a.live = a.live.astype(bool); n_live = int(a.live.sum()); a.off, a.c, a.D = a.mu, np.zeros(n_live), np.eye(n_live)[a.sel]; arms.append(a)
    fj = json.loads((FZ / "frozen_families_raw_K64.json").read_text())
    fams = [({int(m): int(f) for m, f in d["members"].items()}, {int(m): float(s) for m, s in d["signs"].items()}) for d in fj]
    lab_of = {d["family"]: d["label"] for d in fj}
    AX = AXF.load_axes(FZ / "frozen_axes_pooled.npz")
    return T, arms, fams, lab_of, json.loads((FZ / "frozen_FI_params.json").read_text()), json.loads((FZ / "frozen_combinations.json").read_text()), AX


def load_root(A, root):
    E = pd.read_csv(A / f"exams_{root}.csv", dtype={"pid": str}, low_memory=False)
    if not (E.grp == root).all(): raise SystemExit(f"REFUSED: the exam table holds rows outside '{root}'")
    Z = np.load(A / f"arrays_{root}_main.npz", allow_pickle=True); pos = {u: i for i, u in enumerate(Z["series_uid"])}; idx = np.array([pos[u] for u in E.series_uid])
    H = Z["h"][idx].astype(np.float64); lg = Z["logit"][idx].astype(np.float64); X = Z["pooled"][idx].astype(np.float64)
    for t in (1, 6): E[f"lbar{t}"] = lg[:, :, t - 1].mean(1)
    return E, H, X


def variant_arrays(A, root, var, uids):
    """`h` and `pooled` of a variant (zfix or pair), rows in the order of uids (the variant's own series UIDs)."""
    z = np.load(A / f"arrays_{root}_{var}.npz", allow_pickle=True); pos = {u: i for i, u in enumerate(z["series_uid"])}; i = np.array([pos[u] for u in uids])
    return z["h"][i].astype(np.float64), z["pooled"][i].astype(np.float64)


def wald(sd, est, null, direction):
    """one-sided p of the Wald statistic; review change 3: with a bootstrap SD of 0, p = 0 on the stated side of the null, else 1."""
    if est is None or sd is None or not np.isfinite(sd): return None
    right = (est > null) if direction == ">" else (est < null)
    if sd == 0: return 0.0 if right else 1.0
    z = (est - null) / sd; return float(norm.sf(z) if direction == ">" else norm.cdf(z))


def boot_stat(fn, pid):
    bt = S.Boot(pid); est = fn(np.arange(len(pid))); d = [v for v in (fn(t) for t in bt.takes()) if v is not None and np.isfinite(v)]
    lo, hi = np.percentile(d, [2.5, 97.5]); return dict(est=float(est), lo=float(lo), hi=float(hi), sd=float(np.std(d, ddof=1)), n_draws=len(d))


def holm(ps, alpha):
    order = sorted(range(len(ps)), key=lambda i: (np.inf if ps[i] is None else ps[i])); rej = [False] * len(ps); m = len(ps)
    for r, i in enumerate(order):
        if ps[i] is None or ps[i] > alpha / (m - r): break
        rej[i] = True
    return rej


def logits_pooled(X, fc, heads, AX=None, off=None):
    """(n, 5, 6) member logits from `pooled` X (n, 5, 1536) through Sybil's hidden_fc, ReLU and head; off = shared axes set to the dev mean."""
    return np.stack([AXF.member_logits(AXF.remove(AX, X[:, m], m, list(off)) if off else X[:, m], m, fc, heads) for m in range(5)], 1)


def halves_mean(v, rows_pid, half_of):
    h = np.array([half_of[p] for p in rows_pid]); return [float(v[h == k].mean()) for k in (0, 1)]


def flags(fa, fb):
    """two-direction flag numbers (review change 2): flagged in each run, lost, gained, discordant share among exams flagged in either."""
    either = int((fa | fb).sum())
    return dict(flagged_main=int(fa.sum()), flagged_variant=int(fb.sum()), lost=int((fa & ~fb).sum()), gained=int((~fa & fb).sum()), changed=int((fa != fb).sum()),
                flagged_in_either=either, discordant_share_of_flagged_in_either=float((fa != fb).sum() / either) if either else None)


def ols_b(y, x, f):
    X = np.c_[np.ones(len(y)), x, f]; return float(np.linalg.lstsq(X, y, rcond=None)[0][1])


def main():
    A, root, FZ, RI, out_p = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5])
    T, arms, fams, lab_of, FI, COMB, AX = load_frozen(FZ, RI); th = T["thresholds"]; tau = th["tau90_s1"]
    E, H, X = load_root(A, root); heads = S.C.load_heads(RI / "heads.npz"); fc = AXF.load_fc(RI / "heads.npz")
    res = dict(root=root, frozen=str(FZ), n_exams=int(len(E)), participants=int(E.pid.nunique()))
    rowpos = {u: i for i, u in enumerate(E.series_uid)}; HY = {h["id"]: h for h in T["hypotheses"]}; st = {}; sec2 = {}
    half_of = dict(zip(E.pid, S.halves(E.pid.to_numpy())))     # participant halves of the whole root (as step R)
    sd0 = float(AX["axis_sd_dev"][0]); k_ax = AX["k"]; act_main = AXF.activation(AX, X)
    # ---- main-run logits from `pooled`, with and without shared axis 0 (H6, H7 secondary, AUROC with axis 0 off)
    LP = logits_pooled(X, fc, heads); LP_off = logits_pooled(X, fc, heads, AX, [0])
    res["check_max_abs_lbar1_from_pooled_minus_saved"] = float(np.abs(LP[:, :, 0].mean(1) - E.lbar1.to_numpy()).max())
    # ---- per-axis agreement of the five members on this root (secondary for H6)
    V = AXF.variates(AX, X); Zs = (V - V.mean(0)) / np.maximum(V.std(0), 1e-12); Cc = np.einsum("nia,nja->ija", Zs, Zs) / len(V); iu = np.triu_indices(5, 1)
    agree = Cc[iu].mean(0); sec2["H6_axes_member_agreement"] = dict(mean_pairwise_r=np.round(agree, 4).tolist(), n_axes_ge_0p70=int((agree >= 0.70).sum()), n_axes=int(k_ax))
    # ---- H1 to H3, H5prime, H6: z-fix (T5)
    Z, _ = QD.variant_frame(A, root, "zfix")
    if Z is not None:
        J = E.merge(Z[["series_uid", "v_l1", "v_l6", "s1", "s6"]].rename(columns={"s1": "v_s1", "s6": "v_s6"}), on="series_uid"); J = J[J.ratio <= th["zfix_ratio_max"]].reset_index(drop=True)
        d1, d6 = (J.v_l1 - J.lbar1).to_numpy(), (J.v_l6 - J.lbar6).to_numpy(); fa, fb = (J.s1 >= tau).to_numpy(), (J.v_s1 >= tau).to_numpy(); pid = J.pid.to_numpy()
        cnt = dict(exams=int(len(J)), participants=int(J.pid.nunique()), cancers_y1=int((J.y1 == 1).sum()))
        st["H1"] = dict(boot_stat(lambda t: float((np.abs(d6[t]) >= th["quarter_sd"] * th["sd_ref_lbar6_all_dev_main"]).mean()), pid), counts=cnt)
        st["H2"] = dict(boot_stat(lambda t: float(d1[t].mean()), pid), counts=cnt)
        st["H3"] = dict(boot_stat(lambda t: float((fa[t] != fb[t]).mean()), pid), counts=cnt)
        cls = np.where(J.thickness / J.true_spacing >= 1.9, "2.0", "1.6")
        res["zfix_descriptive"] = {k: dict(n=int((cls == k).sum()), mean_d1=float(d1[cls == k].mean()), share_quarter_sd=float((np.abs(d6[cls == k]) >= 0.25 * th["sd_ref_lbar6_all_dev_main"]).mean()),
                                           flag_change=float((fa != fb)[cls == k].mean())) for k in ("1.6", "2.0") if (cls == k).any()}
        sec2["zfix_flags"] = flags(fa, fb)
        mi = np.array([rowpos[u] for u in J.series_uid]); Hz, Xz = variant_arrays(A, root, "zfix", J.series_uid); Hm, Xm = H[mi], X[mi]
        # H5prime: change of the T term (frozen raw-unit dictionary and labels); the other terms are secondary
        gz, gm = S.split_by_label(Hz, arms, fams, lab_of, heads, 1), S.split_by_label(Hm, arms, fams, lab_of, heads, 1)
        terms = {k: np.asarray(gz[k] - gm[k], float) for k in gz}; dT = terms.get("T", np.zeros(len(J)))
        st["H5prime"] = dict(boot_stat(lambda t: float(dT[t].mean()), pid), counts=cnt, halves=halves_mean(dT, pid, half_of), share_exams_T_term_falls=float((dT < 0).mean()))
        sec2["zfix_term_changes_lbar1"] = {k: dict(boot_stat(lambda t, v=v: float(v[t].mean()), pid), part_of_mean_shift=float(v.mean() / d1.mean())) for k, v in terms.items()}
        sec2["zfix_terms_check_max_abs_sum_minus_delta_lbar1"] = float(np.abs(sum(terms.values()) - d1).max())
        # H6: axis 0 of `pooled` set to the dev mean in every member (main and z-fix runs)
        Lz, Lm = logits_pooled(Xz, fc, heads), LP[mi]; Lz_off, Lm_off = logits_pooled(Xz, fc, heads, AX, [0]), LP_off[mi]
        dp1 = Lz[:, :, 0].mean(1) - Lm[:, :, 0].mean(1); doff1 = Lz_off[:, :, 0].mean(1) - Lm_off[:, :, 0].mean(1); h6 = doff1 - dp1
        st["H6"] = dict(boot_stat(lambda t: float(h6[t].mean()), pid), counts=cnt, halves=halves_mean(h6, pid, half_of),
                        mean_delta_lbar1_from_pooled=float(dp1.mean()), mean_delta_lbar1_axis0_off=float(doff1.mean()))
        az = AXF.activation(AX, Xz); dax = (az - act_main[mi]) / AX["axis_sd_dev"]
        sec2["C1_zfix_moves_axis0_dev_sd"] = dict(boot_stat(lambda t: float(dax[t, 0].mean()), pid), halves=halves_mean(dax[:, 0], pid, half_of), null=-2.0, direction="<", note="secondary; dev -2.740")
        sec2["H6_axes_zfix_change_dev_sd"] = np.round(dax.mean(0), 4).tolist()
        e6 = (Lz_off[:, :, 5].mean(1) - Lm_off[:, :, 5].mean(1)) / th["sd_ref_lbar6_all_dev_main"]; e6p = (Lz[:, :, 5].mean(1) - Lm[:, :, 5].mean(1)) / th["sd_ref_lbar6_all_dev_main"]
        sec2["H6_share_ge_quarter_sd_lbar6"] = dict(axis0_off=boot_stat(lambda t: float((np.abs(e6[t]) >= 0.25).mean()), pid), plain_from_pooled=float((np.abs(e6p) >= 0.25).mean()), note="dev: 0.550 off, 0.670 plain")
        # harm estimates (pre-stated secondary; not hypotheses): sensitivity at tau90 and AUROC, main against z-fix, in T5
        hz = {}
        for y, s, vs, tk in (("y1", "s1", "v_s1", "tau90_s1"), ("y6", "s6", "v_s6", "tau90_s6")):
            m = J[y].notna().to_numpy() & ((J.study_yr == 0).to_numpy() if y == "y6" else True); Q = J[m].reset_index(drop=True); yy = Q[y].to_numpy(float); c = yy == 1
            ca, cb = (Q[s] >= th[tk]).to_numpy(), (Q[vs] >= th[tk]).to_numpy(); n_c = int(c.sum()); bt = S.Boot(Q.pid.to_numpy())
            o = dict(population=f"T5 exams with known {y}" + (" (baseline screens)" if y == "y6" else " (all screens)"), counts=dict(exams=int(len(Q)), participants=int(Q.pid.nunique()), cancers=n_c), threshold=th[tk])
            if n_c:
                o.update(sens_main=dict(k=int(ca[c].sum()), n=n_c, est=float(ca[c].mean()), ci_exact=S.clopper_pearson(int(ca[c].sum()), n_c)),
                         sens_zfix=dict(k=int(cb[c].sum()), n=n_c, est=float(cb[c].mean()), ci_exact=S.clopper_pearson(int(cb[c].sum()), n_c)),
                         paired=dict(caught_main_only=int((ca & ~cb & c).sum()), caught_zfix_only=int((~ca & cb & c).sum()),
                                     diff_zfix_minus_main=bt.ci(lambda t: (lambda cc: float(cb[t][cc].mean() - ca[t][cc].mean()) if cc.any() else None)(c[t]))))
            if n_c and n_c < len(Q):
                o.update(auroc_main=S.auc_ci(yy, Q[s].to_numpy(), bt), auroc_zfix=S.auc_ci(yy, Q[vs].to_numpy(), bt), dauroc_zfix_minus_main=S.dauc_ci(yy, Q[vs].to_numpy(), Q[s].to_numpy(), bt))
            hz[y] = o
        sec2["harm_T5"] = hz
    # ---- H4: kernel pairs (T4)
    P, _ = QD.variant_frame(A, root, "pair")
    if P is not None:
        J = E.merge(P[["partner_of", "s1", "v_l1", "series_uid"]].rename(columns={"s1": "v_s1", "series_uid": "pair_uid"}), left_on="series_uid", right_on="partner_of")
        fa, fb = (J.s1 >= tau).to_numpy(), (J.v_s1 >= tau).to_numpy(); pid = J.pid.to_numpy()
        st["H4"] = dict(boot_stat(lambda t: float((fa[t] != fb[t]).mean()), pid), counts=dict(pairs=int(len(J)), participants=int(J.pid.nunique())),
                        mean_delta_lbar1_sharp_minus_soft=float((J.lbar1 - J.v_l1).mean()))
        sec2["kernel_flags"] = flags(fa, fb)
        _, Xp = variant_arrays(A, root, "pair", J.pair_uid); mk = np.array([rowpos[u] for u in J.series_uid])
        sec2["H6_axes_kernel_change_dev_sd"] = np.round(((AXF.activation(AX, Xp) - act_main[mk]) / AX["axis_sd_dev"]).mean(0), 4).tolist()
        sec2["H6_axes_kernel_change_note"] = "pair (soft) minus main (sharp), in dev SD units of each axis; dev axis 0: +0.009"
    # ---- H7: real follow-up pairs of consecutive yearly screens (main runs; outcome-free)
    E2 = E.copy(); E2["st"] = (E2.ratio <= th["zfix_ratio_max"]).astype(int); E2["st_pos"] = ((E2.ratio > 0) & (E2.ratio <= th["zfix_ratio_max"])).astype(int)
    E2["l1"], E2["l1_off"], E2["ax0"] = E2.lbar1, LP_off[:, :, 0].mean(1), act_main[:, 0] / sd0
    c = ["pid", "study_yr", "st", "st_pos", "l1", "l1_off", "ax0", "F1", "s1", "tag_model", "y1"]; Pp = E2[c].merge(E2[c], on="pid", suffixes=("_a", "_b"))   # y1 is used only after the save (last block)
    Pp = Pp[Pp.study_yr_b == Pp.study_yr_a + 1].reset_index(drop=True)
    if len(Pp) and (Pp.st_b != Pp.st_a).any():
        dd = dict(dst=(Pp.st_b - Pp.st_a).to_numpy(float), dst_pos=(Pp.st_pos_b - Pp.st_pos_a).to_numpy(float), dl=(Pp.l1_b - Pp.l1_a).to_numpy(),
                  dl_off=(Pp.l1_off_b - Pp.l1_off_a).to_numpy(), dax0=(Pp.ax0_b - Pp.ax0_a).to_numpy(), dF=(Pp.F1_b - Pp.F1_a).to_numpy())
        ppid = Pp.pid.to_numpy(); flip = ((Pp.s1_a >= tau) != (Pp.s1_b >= tau)).to_numpy()
        pcnt = dict(pairs=int(len(Pp)), participants=int(Pp.pid.nunique()), changed=int((dd["dst"] != 0).sum()), stretched_to_not=int((dd["dst"] == -1).sum()), not_to_stretched=int((dd["dst"] == 1).sum()))
        bfn = lambda key, rows, dk="dst": (lambda t: ols_b(dd[key][rows][t], dd[dk][rows][t], dd["dF"][rows][t]))   # noqa: E731
        allr = np.flatnonzero(np.ones(len(Pp), bool))
        st["H7"] = dict(boot_stat(bfn("dl", allr), ppid), counts=pcnt, halves=[ols_b(*(dd[k][[half_of[p] == h for p in ppid]] for k in ("dl", "dst", "dF"))) for h in (0, 1)])
        f7 = dict(b_axis0_off=boot_stat(bfn("dl_off", allr), ppid), axis0_jump_per_stretch_change_dev_sd=boot_stat(bfn("dax0", allr), ppid),
                  b_ratio0_not_stretched=dict(boot_stat(bfn("dl", allr, "dst_pos"), ppid), note="stretched = 0 < ratio <= 0.65 (exams with a recorded ratio of 0, i.e. duplicated slice positions, counted as not stretched); dev +0.227"))
        same = np.flatnonzero((Pp.tag_model_a == Pp.tag_model_b).to_numpy())
        if len(same) > 3 and (dd["dst"][same] != 0).any():
            f7["same_scanner_model"] = dict(boot_stat(bfn("dl", same), ppid[same]), pairs=int(len(same)), changed=int((dd["dst"][same] != 0).sum()))
        f7["groups"] = {nm: dict(n=int((dd["dst"] == v).sum()), mean_dl=float(dd["dl"][dd["dst"] == v].mean()), mean_dl_off=float(dd["dl_off"][dd["dst"] == v].mean()),
                                 mean_dax0=float(dd["dax0"][dd["dst"] == v].mean()), flag_flip=float(flip[dd["dst"] == v].mean()))
                        for nm, v in (("stretched_to_not", -1), ("unchanged", 0), ("not_to_stretched", 1)) if (dd["dst"] == v).any()}
        sec2["H7_followup"] = f7
    # ---- old H5 (first freeze), now secondary: share of Var(lbar1) carried by the T-named families
    comp = S.split_by_label(H, arms, fams, lab_of, heads, 1); L = E.lbar1.to_numpy(); G = np.asarray(comp.get("T", np.zeros(len(E))), float)
    assert np.abs(sum(np.asarray(v, float) for v in comp.values()) - L).max() < 1e-3
    sec2["old_H5_share_T_lbar1"] = dict(boot_stat(lambda t: float(np.cov(G[t], L[t])[0, 1] / np.var(L[t], ddof=1)), E.pid.to_numpy()), counts=S.counts(E), note="H5 of the first freeze; near-automatic (review): secondary")
    res["group_shares_lbar1_all_terms"] = {k: float(np.cov(np.asarray(v, float), L)[0, 1] / np.var(L, ddof=1)) for k, v in comp.items()}
    # ---- AUROC with axis 0 off (secondary for H6; dev flatters Sybil: caution C6)
    au = {}
    for y, t_ in (("y1", 0), ("y6", 5)):
        m = S.pop(E, y); yy = E.loc[m, y].to_numpy(float); bt = S.Boot(E.pid.to_numpy()[m]); a_, b_ = LP[m][:, :, t_].mean(1), LP_off[m][:, :, t_].mean(1)
        au[y] = dict(counts=S.counts(E, m, y), plain=S.auc(yy, a_), axis0_off=S.auc(yy, b_), diff_off_minus_plain=S.dauc_ci(yy, b_, a_, bt))
    sec2["H6_auroc_axis0_off"] = au
    # ---- tests, Holm
    ps, rows = [], []
    for hid in T["holm"]["family"]:
        h = HY[hid]; s = st.get(hid)
        p = wald(s["sd"], s["est"], h["null"], h["direction"]) if s else None; ps.append(p)
        rows.append(dict(id=hid, name=h["name"], direction=h["direction"], null=h["null"], est=s["est"] if s else None, ci95=[s["lo"], s["hi"]] if s else None,
                         p_one_sided=p, counts=s["counts"] if s else None, halves=s.get("halves") if s else None, evaluated=s is not None,
                         partly_seen=bool(h.get("partly_seen", False))))
    rej = holm(ps, T["holm"]["alpha"])
    for r, x in zip(rows, rej): r["confirmed_holm"] = bool(x)
    res["hypotheses"] = rows; res["n_confirmed"] = int(sum(rej)); res["n_family"] = len(rows)
    for hid, s in st.items():   # computed statistics that are not in the family (e.g. H5prime if the lead moved it): secondary, never confirmed
        if hid not in T["holm"]["family"]: sec2[f"{hid}_not_in_family"] = s
    if "H5prime" in st: sec2["H5prime_detail"] = {k: v for k, v in st["H5prime"].items() if k in ("halves", "share_exams_T_term_falls")}
    if "H6" in st: sec2["H6_detail"] = {k: v for k, v in st["H6"].items() if k.startswith("mean_delta")}
    # ---- secondary references (outside the Holm family; first freeze, unchanged)
    sec = {}
    for y, s, fcol in (("y1", "s1", "F1"), ("y6", "s6", "F6")):
        m = S.pop(E, y); Q = E[m].reset_index(drop=True); yy = Q[y].to_numpy(float); bt = S.Boot(Q.pid.to_numpy()); prm = FI[y]
        Xd, _ = RF.design(Q, fcol, RF.MEAS5, np.array(prm["medians"])); fi = ((Xd - np.array(prm["mean"])) / np.array(prm["scale"])) @ np.array(prm["coef"]) + prm["intercept"]
        cb = COMB[f"A3_FI_plus_sybil_{y}"]; comb = np.column_stack([fi, S.logit(Q[s])]) @ np.array(cb["coef"]) + cb["intercept"]
        sec[y] = dict(counts=S.counts(E, m, y), sybil=S.auc_ci(yy, Q[s].to_numpy(), bt), F=S.auc_ci(yy, Q[fcol].to_numpy(), bt), R_size=S.auc_ci(yy, Q.max_dia.fillna(0).to_numpy(float), bt),
                      FI=S.auc_ci(yy, fi, bt), FI_plus_sybil_minus_FI=S.dauc_ci(yy, comb, fi, bt))
        if y == "y1":
            target = float(Q.positive_call.to_numpy()[yy == 1].mean()); c_ = COMB["U3_C_y1"]; cs = np.column_stack([S.logit(Q.s1), Q.F1]) @ np.array(c_["coef"]) + c_["intercept"]
            sec["U3_table"] = dict(target_sensitivity=target, radiologists=float(((yy == 0) & (Q.positive_call == 1)).sum() / len(yy) * 1000),
                                   **{k: U3.fa_per_1000(v, yy.astype(int), target)[0] for k, v in (("sybil", Q.s1.to_numpy()), ("F", Q.F1.to_numpy()), ("C_frozen", cs), ("FI", fi))})
    res["secondary"] = sec; res["secondary_new_freeze"] = sec2
    res["note"] = "secondary references and secondary_new_freeze are outside the Holm family (never called confirmed); anything else is exploratory (protocol 11)"
    out_p.parent.mkdir(parents=True, exist_ok=True); out_p.write_bytes((json.dumps(res, indent=1, default=float) + "\n").encode("utf-8"))   # LF everywhere
    print(json.dumps(dict(root=root, hypotheses=rows, n_confirmed=res["n_confirmed"]), indent=1, default=float))
    # ---- after the primary result is saved: the H7 sensitivity that uses outcomes (both screens without cancer within 1 year)
    if "H7" in st:
        nc = np.flatnonzero(((Pp.y1_a == 0) & (Pp.y1_b == 0)).to_numpy())
        o = dict(note="secondary sensitivity; uses outcomes; computed after the primary result was saved", pairs=int(len(nc)), changed=int((dd["dst"][nc] != 0).sum()),
                 b=boot_stat(bfn("dl", nc), ppid[nc]), b_axis0_off=boot_stat(bfn("dl_off", nc), ppid[nc]))
        p2 = out_p.with_name(out_p.stem + "_h7_no_cancer_sensitivity.json"); p2.write_bytes((json.dumps(o, indent=1, default=float) + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
