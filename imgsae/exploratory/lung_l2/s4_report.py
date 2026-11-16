"""Lung L2, S4: number tables for RESULTS_S4_dev.md, read straight from the result files (no number is typed by hand).
Every row gives its exams, participants and cancers where the result file has them. Failed marks are written as FAILED.
usage (venv python): python s4_report.py <results dir> <out md> [--tag dev]
"""
import argparse
import json
from pathlib import Path


def f(v, d=3):
    if v is None: return "—"
    if isinstance(v, bool): return "yes" if v else "no"
    if isinstance(v, (int,)) and not isinstance(v, bool): return f"{v:,}"
    try: return f"{float(v):.{d}f}"
    except (TypeError, ValueError): return str(v)


def ci(x, d=3):
    if not isinstance(x, dict): return f(x, d)
    return f"{f(x.get('est'), d)} [{f(x.get('lo'), d)}, {f(x.get('hi'), d)}]"


def cnt(c):
    if not isinstance(c, dict): return ""
    parts = [f"{c[k]:,} {k}" for k in ("exams", "participants", "cancers") if k in c]
    return ", ".join(parts)


def mark(p): return "pass" if p else "**FAILED**"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("results"); ap.add_argument("out"); ap.add_argument("--tag", default="dev"); a = ap.parse_args()
    R = Path(a.results); L = []
    J = lambda n: json.loads((R / f"{n}_{a.tag}.json").read_text()) if (R / f"{n}_{a.tag}.json").exists() else None
    sc = J("s4_scores")
    if sc:
        p = sc["check_P1"]; L += ["## Scores (9.1)", f"- Exams {cnt(sc['counts'])}. {sc['participants_note']}.",
                                  f"- Check P1 (Spearman of lbar_t with s_t >= 0.98, all dev exams): t1 {f(p['t1_all'], 4)}, t6 {f(p['t6_all'], 4)} -> {mark(p['pass_'])}; "
                                  f"t6 on baseline {f(p['t6_baseline'], 4)}.",
                                  "- Diagnostics: " + "; ".join(f"{t}: Spearman with the mean member probability {f(v['spearman_lbar_vs_mean_member_prob'], 4)}, "
                                                                f"{v['n_unique_s']:,} distinct values of s, {f(100 * v['share_at_min_s'], 1)}% at the minimum {f(v['min_s'], 4)}"
                                                                for t, v in p["diagnostics"].items()),
                                  f"- Hazard units on: overall {f(sc['gating_on_share']['overall'], 4)}; by member {sc['gating_on_share']['by_member']}; by unit {sc['gating_on_share']['by_unit']}.",
                                  "", "| horizon | population | Sybil s_t | Sybil lbar_t | F | Sybil − F |", "|---|---|---|---|---|---|"]
        for y, r in sc["auroc"].items():
            if y == "radiologists_y1": continue
            L.append(f"| {y} | {cnt(r['counts'])} | {ci(r['sybil_s'])} | {ci(r['sybil_lbar'])} | {ci(r.get('form_F'))} | {ci(r.get('sybil_minus_F'))} |")
        rr = sc["auroc"]["radiologists_y1"]
        L += ["", f"- Radiologists' call, y1 ({cnt(rr['counts'])}): sensitivity {f(rr['sensitivity'])}, specificity {f(rr['specificity'])}, positive {f(rr['positive_rate'])}.",
              f"- {sc['note_C6']}", ""]
    q = J("s4_q1a")
    if q:
        L += ["## Q1a: composition by known groups (9.7)", "", "| target | exams, participants | CV R² ridge | CV R² boosting | N | B | D | I | T | unexplained |", "|---|---|---|---|---|---|---|---|---|---|"]
        for k in ("lbar1_all", "lbar6_baseline", "lbar1_never_cancer", "lbar6_baseline_never_cancer"):
            r = q[k]; sh = r["shapley"]; c95 = r.get("shapley_ci95", {})
            L.append(f"| {k} | {r['n_exams']:,}, {r['participants']:,} | {f(r['cv_r2_ridge_all'])} | {f(r['cv_r2_boost_all'])} | "
                     + " | ".join(f"{f(sh[g])}" + (f" [{f(c95[g][0])}, {f(c95[g][1])}]" if g in c95 else "") for g in ("N", "B", "D", "I", "T")) + f" | {f(r['unexplained'])} |")
        L.append("")
    for K in (64, 128):
        rows = []
        for arm in ("raw", "pca", "ica", "nmf", "kmeans", "sae"):
            p_ = R / f"s4_decomp_{a.tag}_{arm}_K{K}.json"
            if not p_.exists(): continue
            d = json.loads(p_.read_text())
            rows.append(f"| {arm} | {f(d['V1']['r_y1'])} / {f(d['V1']['r_y6'])} | {f(d['V1']['dAUROC_y1'], 4)} / {f(d['V1']['dAUROC_y6'], 4)} | {mark(d['V1']['pass_'])} | "
                        f"{mark(d['V2']['pass_'])} {f(d['V2'].get('median_r'))} / {f(d['V2'].get('share'))} | {mark(d['V3']['pass_'])} {d['V3']['n_families']} | "
                        f"{mark(d['V4']['pass_'])} {f(d['V4']['median_assoc_half_corr'])} / {f(d['V4']['label_agreement_named'])} | {'**valid**' if d['valid'] else 'not valid'} | "
                        f"{d['audit_yield_named_replicated']} | {json.dumps(d['labels'])} |")
        if rows:
            L += [f"## Decomposition arms, K = {K} (9.4, 9.5)", "", "| arm | V1 r (y1/y6) | V1 dAUROC (y1/y6) | V1 | V2 (median r / share) | V3 families | V4 (half corr / label agree) | valid | named replicated | labels |",
                  "|---|---|---|---|---|---|---|---|---|---|"] + rows + [""]
    qb = J("s4_q1b_u")
    if qb:
        L += ["## Q1b (9.7)", f"- Primary arm: **{qb['primary_arm']}**."]
        for y in ("y1", "y6"):
            r = qb[f"U_adds_to_F_{y}"]
            L.append(f"- U adds to F, {y} ({cnt(r['counts'])}): AUROC F {ci(r['auroc_base'])}, F + U {ci(r['auroc_full'])}, difference {ci(r['dauroc'])}, "
                     f"halves {f(r['dauroc_halves'][0])} / {f(r['dauroc_halves'][1])}, LR test chi² {f(r['lr']['chi2'], 2)}, p {f(r['lr']['p'], 4)}.")
        if "group_shares" in qb:
            for t, st in qb["group_shares"].items():
                L.append(f"- Group shares of {t} ({qb['primary_arm']}): " + "; ".join(f"{k} {ci(v)}" for k, v in st.items() if isinstance(v, dict)) + f" (sum {f(st['sum_of_shares'], 4)}).")
        L.append("")
    qc = J("s4_q1c")
    if qc:
        L += ["## Q1c: stable part, T0 and T1 (9.7)"] + ([f"- {qc['note']}"] if "note" in qc else [])
        for sub in [s for s in ("all", "no_cancer_within_2y_of_T0") if s in qc]:
            r = qc[sub]; L.append(f"- {sub}: {r['participants']:,} participants; r(lbar1) {ci(r['lbar1']['pearson_r_T0_T1'])}, r(lbar6) {ci(r['lbar6']['pearson_r_T0_T1'])}.")
            for t in ("lbar1", "lbar6"):
                if "stable_shares" in r[t]:
                    L.append(f"  - stable shares of {t}: " + "; ".join(f"{k} {ci(v)}" for k, v in r[t]["stable_shares"].items() if isinstance(v, dict)))
        L.append("")
    qd = J("s4_q1d")
    if qd:
        L += ["## Q1d / U1b: technical changes inside one exam (9.7)", f"- tau90 = {f(qd['tau90'], 4)}; SD lbar1 {f(qd['sd_lbar1_all'])}, SD lbar6 all {f(qd['sd_lbar6_all'])}, baseline {f(qd['sd_lbar6_baseline'])}."]
        if "zfix" in qd and "D5" in qd["zfix"]:
            z = qd["zfix"]["D5"]
            L.append(f"- z-fix, D5 ({cnt(z['counts'])}): t6 mean {f(z['t6']['mean'])}, SD {f(z['t6']['sd'])}, ICC {f(z['t6']['icc'])}, share |Δ| ≥ 0.25 SD {f(z['t6']['share_ge_quarter_sd'])}, "
                     f"flag change {f(z['t6']['share_flag_changed'])}; U1b qualifies: {f(z['U1b_dev_qualifies'])}. Intervals: " +
                     "; ".join(f"{k} {ci(v)} (halves {f(v['halves'][0])} / {f(v['halves'][1])})" for k, v in z["candidates_stats"].items()))
        if "kernel_pairs" in qd:
            k_ = qd["kernel_pairs"]
            L.append(f"- Kernel pairs ({cnt(k_['counts'])}): t1 mean {f(k_['t1']['mean'])}, t6 mean {f(k_['t6']['mean'])}, SD ratio t6 {f(k_['t6']['sd_ratio'])}, ICC t6 {f(k_['t6']['icc'])}, "
                     f"flag change {f(k_['t6']['share_flag_changed'])}. Intervals: " + "; ".join(f"{kk} {ci(v)}" for kk, v in k_["candidates_stats"].items()))
        L.append("")
    q2 = J("s4_q2")
    if q2:
        th = q2["thresholds"]; L += ["## Q2: false alarms and misses (9.7)", f"- tau90 {f(th['tau90'], 4)} (specificity reached {f(th['specificity_at_tau90'])}), tau90_F {f(th['tau90_F'], 3)}, tau_rad {f(th['tau_rad'], 4)}."]
        fa = q2["false_alarms"]["tau90"]
        L.append("- Classes at tau90: " + "; ".join(f"{k} {v['exams']:,} exams ({v['participants']:,} participants)" for k, v in fa["counts"].items()))
        for c in ("sybil_only", "shared", "form_only"):
            top = sorted([r for r in fa[c] if r["q"] is not None and r["q"] < 0.05 and r["smd"] is not None], key=lambda r: -abs(r["smd"]))[:8]
            L.append(f"  - {c}: {sum(r['q'] is not None and r['q'] < 0.05 for r in fa[c])} variables with q < 0.05; largest: " + "; ".join(f"{r['variable']} {f(r['smd'], 2)}" for r in top))
        for y, m in q2["misses"].items():
            L.append(f"- Misses {y} ({m['population']}, {cnt(m['counts'])}): missed {m['missed']}, caught {m['caught']} (descriptive).")
        L.append("")
    u1 = J("s4_u1a")
    if u1:
        s = u1["spread"]; L += ["## U1a: technical removal (9.7)", f"- dAUROC y1 {ci(u1['auroc_y1']['dauroc'], 4)} ({cnt(u1['auroc_y1']['counts'])}); y6 {ci(u1['auroc_y6']['dauroc'], 4)} ({cnt(u1['auroc_y6']['counts'])}).",
                                f"- False-alarm spread over {len(s['groups'])} maker × kernel groups: before {f(s['sd_before'], 4)}, after {f(s['sd_after'], 4)}, ratio {ci(s['ratio_ci'])}; F {f(s['sd_F'], 4)}.",
                                f"- Qualification: {json.dumps(u1['qualification'])}.", ""]
    u2 = J("s4_u2")
    if u2:
        L += ["## U2: reliability flag (9.7)"] + [f"- {r['rule']}: flagged {f(r['flagged_share_y1_neg'])} of y1 = 0; statistic {ci(r['statistic'])} (halves {f(r['halves'][0])} / {f(r['halves'][1])}); "
                                                    f"Sybil sensitivity flagged {f(r['sybil_sens_flagged'])} (n {r['n_cancers_flagged']}) vs unflagged {f(r['sybil_sens_unflagged'])} (n {r['n_cancers_unflagged']})."
                                                    for r in (u2["R_fixed"], u2["R_learned"])] + [f"- Rule that can be frozen: {u2['rule_that_can_be_frozen']}.", ""]
    u3 = J("s4_u3")
    if u3:
        t = u3["table"]; L += ["## U3: Sybil plus the form at the radiologists' sensitivity (9.7; partly seen)", f"- {cnt(u3['counts'])}; target sensitivity {f(u3['target_sensitivity'])} (tables 0.909).",
                               "- False alarms per 1,000 screens: " + "; ".join(f"{k} {f(v['fa_per_1000'], 1)} (sens {f(v['sensitivity'])})" for k, v in t.items()),
                               f"- Ratio C / better of Sybil and F: {ci(u3['ratio_C_over_better'])}; qualifies (≤ 0.80): {f(u3['ratio_C_over_better']['qualifies'])}.", ""]
    u4 = J("s4_u4")
    if u4:
        L += ["## U4: references (9.7)"]
        for y in ("y1", "y6"):
            r = u4[y]; L.append(f"- {y} ({cnt(r['counts'])}): Sybil {ci(r['sybil'])}; probe on h {ci(r['probe_h_2560'])}; family models: " +
                                "; ".join(f"{k} {ci(v)} ({v.get('n_families')} fam.)" for k, v in r["family_activation_models"].items() if "est" in v))
        L.append("")
    rf = J("s4_refs")
    if rf:
        L += ["## Simple references (amendment A3)"] + [f"- R-size, {y} ({cnt(v['counts'])}): {ci(v['auroc'])} (partly seen; reference only)." for y, v in rf["R_size"].items() if isinstance(v, dict) and "auroc" in v]
        for name, d in rf["F_plus_I"].items():
            for y in ("y1", "y6"):
                r = d[y]; av = r["sybil_adds_to_FI"]
                L.append(f"- F+I {name}, {y} ({cnt(r['counts'])}): F+I {ci(r['auroc_FI'])}, F {ci(r['auroc_F'])}, Sybil {ci(r['auroc_sybil'])}; F+I − F {ci(r['FI_minus_F'])}; "
                         f"Sybil adds to F+I {ci(av['dauroc'])} (halves {f(av['dauroc_halves'][0])} / {f(av['dauroc_halves'][1])}), LR p {f(av['lr']['p'], 4)}.")
        if "U3_table_with_FI" in rf: L.append(f"- U3 table, F+I: {f(rf['U3_table_with_FI']['FI']['fa_per_1000'], 1)} false alarms per 1,000 at sensitivity {f(rf['U3_table_with_FI']['FI']['sensitivity'])}.")
        L += [f"- {rf['limit']}.", ""]
    g = J("s4_gate")
    if g:
        L += ["## Gate 9.8", f"- {g['n_candidates']} candidates; {g['n_hold']} hold 9.8; {g['n_eligible']} eligible (with valid arm and qualification); "
                             f"{g['n_eligible_not_partly_seen']} not partly seen. Any valid arm: {f(g['any_valid_arm'])}; primary arm {g['primary_arm']}.",
              f"- Leak check: {mark(g['leak_check']['pass_'])}; data check: {mark(g.get('data_check', {}).get('pass_'))}. Decision: **{g['gate_9_8']['decision']}**.",
              f"- Full table: `results/s4/s4_gate_{a.tag}.md`.", ""]
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8"); print(f"s4_report: {len(L)} lines -> {a.out}")


if __name__ == "__main__":
    main()
