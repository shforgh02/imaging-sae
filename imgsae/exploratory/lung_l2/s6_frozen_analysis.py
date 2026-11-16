"""Lung L2, step S6: the frozen analysis (docs/LUNG_L2_PROTOCOL.md sections 10 and 11). Runs once on test after the lead's OK.
It reads only the frozen files of S5 (results/s5/, SHA-256 checked against frozen_thresholds_L2.json before anything else) and the
assembled exam table and arrays of one root (l2_data.py output). Nothing is fitted: the dictionary, the family labels, the
thresholds, the SD references, the F+I parameters and the secondary combinations are the frozen dev values.
Hypotheses H1 to H5 (one-sided, Holm, family-wise alpha 0.05; participant bootstrap, 2,000 draws, seed 0; p from the Wald statistic
(est - null) / SD of the draws). Secondary references are reported outside the Holm family and labelled secondary.
Tested end to end on dev ("dev as if test", root dev): it must reproduce the S4 dev numbers.
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
    return T, arms, fams, lab_of, json.loads((FZ / "frozen_FI_params.json").read_text()), json.loads((FZ / "frozen_combinations.json").read_text())


def load_root(A, root):
    E = pd.read_csv(A / f"exams_{root}.csv", dtype={"pid": str}, low_memory=False)
    if not (E.grp == root).all(): raise SystemExit(f"REFUSED: the exam table holds rows outside '{root}'")
    Z = np.load(A / f"arrays_{root}_main.npz", allow_pickle=True); pos = {u: i for i, u in enumerate(Z["series_uid"])}; idx = np.array([pos[u] for u in E.series_uid])
    H = Z["h"][idx].astype(np.float64); lg = Z["logit"][idx].astype(np.float64)
    for t in (1, 6): E[f"lbar{t}"] = lg[:, :, t - 1].mean(1)
    return E, H


def wald(ci_draws_sd, est, null, direction):
    if est is None or not ci_draws_sd: return None
    z = (est - null) / ci_draws_sd; return float(norm.sf(z) if direction == ">" else norm.cdf(z))


def boot_stat(fn, pid):
    bt = S.Boot(pid); est = fn(np.arange(len(pid))); d = [v for v in (fn(t) for t in bt.takes()) if v is not None and np.isfinite(v)]
    lo, hi = np.percentile(d, [2.5, 97.5]); return dict(est=float(est), lo=float(lo), hi=float(hi), sd=float(np.std(d, ddof=1)), n_draws=len(d))


def holm(ps, alpha):
    order = sorted(range(len(ps)), key=lambda i: (np.inf if ps[i] is None else ps[i])); rej = [False] * len(ps); m = len(ps)
    for r, i in enumerate(order):
        if ps[i] is None or ps[i] > alpha / (m - r): break
        rej[i] = True
    return rej


def main():
    A, root, FZ, RI, out_p = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5])
    T, arms, fams, lab_of, FI, COMB = load_frozen(FZ, RI); th = T["thresholds"]; tau = th["tau90_s1"]
    E, H = load_root(A, root); heads = S.C.load_heads(RI / "heads.npz"); res = dict(root=root, frozen=str(FZ), n_exams=int(len(E)), participants=int(E.pid.nunique()))
    rowpos = {u: i for i, u in enumerate(E.series_uid)}; HY = {h["id"]: h for h in T["hypotheses"]}; st = {}
    # ---- H1 to H3: z-fix (T5)
    Z, _ = QD.variant_frame(A, root, "zfix")
    if Z is not None:
        J = E.merge(Z[["series_uid", "v_l1", "v_l6", "s1"]].rename(columns={"s1": "v_s1"}), on="series_uid"); J = J[J.ratio <= th["zfix_ratio_max"]].reset_index(drop=True)
        d1, d6 = (J.v_l1 - J.lbar1).to_numpy(), (J.v_l6 - J.lbar6).to_numpy(); fa, fb = (J.s1 >= tau).to_numpy(), (J.v_s1 >= tau).to_numpy(); pid = J.pid.to_numpy()
        cnt = dict(exams=int(len(J)), participants=int(J.pid.nunique()), cancers_y1=int((J.y1 == 1).sum()))
        st["H1"] = dict(boot_stat(lambda t: float((np.abs(d6[t]) >= th["quarter_sd"] * th["sd_ref_lbar6_all_dev_main"]).mean()), pid), counts=cnt)
        st["H2"] = dict(boot_stat(lambda t: float(d1[t].mean()), pid), counts=cnt)
        st["H3"] = dict(boot_stat(lambda t: float((fa[t] != fb[t]).mean()), pid), counts=cnt)
        cls = np.where(J.thickness / J.true_spacing >= 1.9, "2.0", "1.6")
        res["zfix_descriptive"] = {k: dict(n=int((cls == k).sum()), mean_d1=float(d1[cls == k].mean()), share_quarter_sd=float((np.abs(d6[cls == k]) >= 0.25 * th["sd_ref_lbar6_all_dev_main"]).mean()),
                                           flag_change=float((fa != fb)[cls == k].mean())) for k in ("1.6", "2.0") if (cls == k).any()}
    # ---- H4: kernel pairs (T4)
    P, _ = QD.variant_frame(A, root, "pair")
    if P is not None:
        J = E.merge(P[["partner_of", "s1", "v_l1"]].rename(columns={"s1": "v_s1"}), left_on="series_uid", right_on="partner_of")
        fa, fb = (J.s1 >= tau).to_numpy(), (J.v_s1 >= tau).to_numpy(); pid = J.pid.to_numpy()
        st["H4"] = dict(boot_stat(lambda t: float((fa[t] != fb[t]).mean()), pid), counts=dict(pairs=int(len(J)), participants=int(J.pid.nunique())),
                        mean_delta_lbar1_sharp_minus_soft=float((J.lbar1 - J.v_l1).mean()))
    # ---- H5: share of Var(lbar1) carried by the T-named families (frozen raw-unit dictionary)
    comp = S.split_by_label(H, arms, fams, lab_of, heads, 1); L = E.lbar1.to_numpy(); G = np.asarray(comp.get("T", np.zeros(len(E))), float)
    assert np.abs(sum(np.asarray(v, float) for v in comp.values()) - L).max() < 1e-3
    fn = lambda t: float(np.cov(G[t], L[t])[0, 1] / np.var(L[t], ddof=1))
    st["H5"] = dict(boot_stat(fn, E.pid.to_numpy()), counts=S.counts(E))
    res["group_shares_lbar1_all_terms"] = {k: float(np.cov(np.asarray(v, float), L)[0, 1] / np.var(L, ddof=1)) for k, v in comp.items()}
    # ---- tests, Holm
    ps, rows = [], []
    for hid in T["holm"]["family"]:
        h = HY[hid]; s = st.get(hid)
        p = wald(s["sd"], s["est"], h["null"], h["direction"]) if s else None; ps.append(p)
        rows.append(dict(id=hid, name=h["name"], direction=h["direction"], null=h["null"], est=s["est"] if s else None, ci95=[s["lo"], s["hi"]] if s else None,
                         p_one_sided=p, counts=s["counts"] if s else None, evaluated=s is not None))
    rej = holm(ps, T["holm"]["alpha"])
    for r, x in zip(rows, rej): r["confirmed_holm"] = bool(x)
    res["hypotheses"] = rows; res["n_confirmed"] = int(sum(rej))
    # ---- secondary references (outside the Holm family)
    sec = {}
    for y, s, fcol in (("y1", "s1", "F1"), ("y6", "s6", "F6")):
        m = S.pop(E, y); Q = E[m].reset_index(drop=True); yy = Q[y].to_numpy(float); bt = S.Boot(Q.pid.to_numpy()); prm = FI[y]
        X, _ = RF.design(Q, fcol, RF.MEAS5, np.array(prm["medians"])); fi = ((X - np.array(prm["mean"])) / np.array(prm["scale"])) @ np.array(prm["coef"]) + prm["intercept"]
        cb = COMB[f"A3_FI_plus_sybil_{y}"]; comb = np.column_stack([fi, S.logit(Q[s])]) @ np.array(cb["coef"]) + cb["intercept"]
        sec[y] = dict(counts=S.counts(E, m, y), sybil=S.auc_ci(yy, Q[s].to_numpy(), bt), F=S.auc_ci(yy, Q[fcol].to_numpy(), bt), R_size=S.auc_ci(yy, Q.max_dia.fillna(0).to_numpy(float), bt),
                      FI=S.auc_ci(yy, fi, bt), FI_plus_sybil_minus_FI=S.dauc_ci(yy, comb, fi, bt))
        if y == "y1":
            target = float(Q.positive_call.to_numpy()[yy == 1].mean()); c = COMB["U3_C_y1"]; cs = np.column_stack([S.logit(Q.s1), Q.F1]) @ np.array(c["coef"]) + c["intercept"]
            sec["U3_table"] = dict(target_sensitivity=target, radiologists=float(((yy == 0) & (Q.positive_call == 1)).sum() / len(yy) * 1000),
                                   **{k: U3.fa_per_1000(v, yy.astype(int), target)[0] for k, v in (("sybil", Q.s1.to_numpy()), ("F", Q.F1.to_numpy()), ("C_frozen", cs), ("FI", fi))})
    res["secondary"] = sec; res["note"] = "secondary references are outside the Holm family; anything else is exploratory (protocol 11)"
    out_p.parent.mkdir(parents=True, exist_ok=True); out_p.write_bytes((json.dumps(res, indent=1, default=float) + "\n").encode("utf-8"))   # LF everywhere
    print(json.dumps(dict(root=root, hypotheses=rows, n_confirmed=res["n_confirmed"]), indent=1, default=float))


if __name__ == "__main__":
    main()
