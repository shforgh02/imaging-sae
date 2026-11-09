"""A4: read-out of Stage A. Builds the results section of README.md from results/a1_probe_ladder.json, a2_sae_audit.json, a3_cpu.json,
a3_sae.json (no hand-copied numbers) and applies the reading rules fixed in docs/SANITY_PLAN_v1.md (R-sat, R-fm from A1; R-sae here).
R-sae (simple beats SAE), per sparsity level L0 in {6, 27}: the best CT-FM simple baseline (soft k-means, raw sparse, sparse varimax) has a higher
feature-count-matched area than the best SAE row at that level, in every replicate and under both chimera rules. SAE rows at L0 6: single SAE
with k = 6 (A2 best) and the run-config consensus (its L0 is ~6); at L0 27: the run SAE and the A2 best k = 27 SAE.
Holds = both levels; partial = one level. usage: ..\..\.venv\Scripts\python a4_summarize.py [--quick]
"""
import argparse
import json

import numpy as np

from common import HERE, RES

SIMPLE = {6: ["km_ctfm_L6", "raw_ctfm_L6", "svx_ctfm_L6"], 27: ["km_ctfm_L27", "raw_ctfm_L27", "svx_ctfm_L27"]}
SAE = {6: ["sae_best_k6", "sae_cons_run"], 27: ["sae_run", "sae_best_k27"]}
RULES = ("orig", "neutral")


def f3(x): return "–" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.3f}"


def table(head, rows): return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(map(str, r)) + " |" for r in rows])


def load(name):
    p = RES / name; return json.load(open(p)) if p.exists() else None


def a1_section(a1):
    out = ["## A1 — probe ladder (median one-vs-rest AUROC over scored classes)"]
    sets = ["ctfm", "null", "R0", "R1", "R2", "R3", "R4", "run", "ctfm+R3", "null+R3"]; rows = []
    for k, t in a1["tasks"].items():
        rows.append([k, t["n_tokens"], t["n_patients"], len(t["scored"])] + [f3(t["median"].get(s)) for s in sets] + [t.get("best_ref", "–")])
    out.append(table(["task", "tokens", "patients", "classes"] + sets + ["best label-free ref"], rows))
    out.append("Sets: ctfm = CT-FM; null = same network, random init; R0 HU stats (24) · R1 + texture (28) · R2 + 48 mm context (56) · R3 + body x/y (74) · "
               "R4 + scan-relative z (83) · run = reference as run (z from vertebra masks, label-derived; T3_vert leaks).")
    if a1.get("skipped"): out.append("Skipped (not estimable under the plan's rule): " + ", ".join(f"{k} ({v['reason']}; {v['per_class']})" for k, v in a1["skipped"].items()))
    rows = []
    for k, t in a1["tasks"].items():
        for comp, d in t["comparisons"].items():
            diffs = [v["diff"] for v in d.values()]; pos = sum(v["ci_diff"][0] > 0 for v in d.values()); neg = sum(v["ci_diff"][1] < 0 for v in d.values())
            rows.append([k, comp.replace("|", " − "), f3(float(np.median(diffs))), f"{pos}/{len(d)}", f"{neg}/{len(d)}", sum(v["diff"] >= .05 and v["ci_diff"][0] > 0 for v in d.values())])
    out.append("### Paired differences (patient-cluster bootstrap 95% CI)\n" + table(["task", "difference", "median Δ", "CI > 0", "CI < 0", "Δ ≥ 0.05 & CI > 0"], rows))
    rows = []
    for k, t in a1["tasks"].items():
        for n, f in t.get("few", {}).items():
            rows.append([k, n] + [f3(f["median_per_draw"][s]) for s in ("ctfm", "null", "R3", "R4")] + [f3(f["median"][s]) for s in ("ctfm", "null", "R3", "R4")])
    if rows: out.append("### T4 — few labels (training-fold patients per fold)\n" + table(["task", "n", "ctfm", "null", "R3", "R4", "ctfm (3-draw avg)", "null (avg)", "R3 (avg)", "R4 (avg)"], rows))
    if "T3_side" in a1["tasks"] and "side_by_structure" in a1["tasks"]["T3_side"]:
        sb = a1["tasks"]["T3_side"]["side_by_structure"]
        out.append("### T3_side by structure (AUROC left vs right)\n" + table(["structure", "ctfm", "null", "R2 (no position)", "R3"], [[u, f3(v["ctfm"]), f3(v["null"]), f3(v["R2"]), f3(v["R3"])] for u, v in sb.items()]))
    r = a1["rules"]; out.append(f"**R-sat** holds: **{r['R_sat']['holds']}** — " + ", ".join(f"{k} {f3(v)}" for k, v in r["R_sat"].items() if k != "holds"))
    out.append(f"**R-fm** holds: **{r['R_fm']['holds']}** — share of classes where CT-FM beats both the best label-free reference and the untrained network "
               "by ≥ 0.05 (CI > 0): " + ", ".join(f"{k} {v['share']:.2f}" for k, v in r["R_fm"]["by_task"].items()))
    if "sanity_T1a_max_abs_diff_vs_gates" in a1: out.append(f"Sanity: T1a reproduces gates.json, max |Δ AUROC| = {a1['sanity_T1a_max_abs_diff_vs_gates']:.1e}.")
    return "\n\n".join(out)


def a2_section(a2):
    out = ["## A2 — SAE adequacy and size / sparsity sweep (replicate 0)"]; rows = []
    for n, r in a2.items():
        if n.startswith("_") or n.startswith("seed_check"): continue
        d = r.get("diag", {}); r2 = np.mean([v["r2_other"] for v in d.values()]) if d else None; dead = np.mean([v["dead_share"] for v in d.values()]) if d else None
        rows.append([n, r["M"], r["k"], r["steps"], f"{r['fit_min_two_halves']:.1f}", f3(r2), f3(dead), f"{np.mean(list(r['L0'].values())):.1f}", f3(r["R1"]), f3(r["R1_med"]),
                     f3(r["area_orig"]), f3(r["area_neutral"]), f3(r["area_matched_neutral"]), f3(r["median_sel_v0"]), f3(r["median_t_v0"])])
    out.append(table(["config", "M", "k", "steps", "fit min", "R² held-out", "dead", "L0", "R1", "R1 median r", "area orig", "area neutral", "neutral, 425 feat.", "median sel", "median t"], rows))
    run = a2.get("run_M425_k27_s3000", {}); sc = [f"run config: R1 within half A (2 seeds) {f3(run.get('R1_within_halfA'))} vs between halves {f3(run.get('R1'))}"]
    if "seed_check_best" in a2: b = a2["seed_check_best"]; sc.append(f"best config {b['config']}: within {f3(b['R1_within_halfA'])} vs between {f3(a2[b['config']]['R1'])}")
    out.append("Seed check — " + "; ".join(sc)); out.append(f"Best single config (neutral area): {a2.get('_best_single')}; by k: {a2.get('_best_single_by_k')}")
    if "_sanity" in a2: out.append(f"Sanity vs run / check 1b: {a2['_sanity']}")
    return "\n\n".join(out)


def a3_section(cpu, sae_):
    allr = {**{k: v for k, v in (cpu or {}).items() if not k.startswith("_")}, **{k: v for k, v in (sae_ or {}).items() if not k.startswith("_")}}
    names = sorted({v["method"] for v in allr.values()}); reps = sorted({v["rep"] for v in allr.values()}); out = ["## A3 — fair decomposition comparison"]; rows = []
    for n in names:
        rr = [allr.get(f"{n}_rep{r}") for r in reps]; rr = [x for x in rr if x]
        if not rr: continue
        m = lambda key: float(np.mean([x[key] for x in rr]))  # noqa: E731
        rows.append([n, len(rr), f"{np.mean([np.mean(list(x['L0'].values())) for x in rr]):.1f}", int(np.mean([np.mean(list(x['n_feat'].values())) for x in rr])), f3(m("R1")),
                     f3(m("area_orig")), f3(m("area_neutral")), f3(m("area_matched_orig")), f3(m("area_matched_neutral")), f3(m("median_sel_v0"))])
    out.append(table(["method", "reps", "L0", "features", "R1", "area orig", "area neutral", "orig, 425 feat.", "neutral, 425 feat.", "median sel"], rows))
    out.append("Names: km = soft k-means (M 425), raw = raw sparse channels, svx = sparse varimax; _ctfm / _null / _R3 = input (CT-FM, untrained CT-FM, "
               "label-free reference, no FM); _L6 / _L27 = L0. sae_run = run config (M 425, k 27); sae_best_k* = A2 best; sae_cons_run = 5-fit consensus, run config.")
    res = {}
    for L0 in (6, 27):
        wins, missing, detail = [], 0, []
        for rep in (0, 1, 2):
            for rule in RULES:
                s = [allr[f"{n}_rep{rep}"][f"area_matched_{rule}"] for n in SIMPLE[L0] if f"{n}_rep{rep}" in allr]
                q = [allr[f"{n}_rep{rep}"][f"area_matched_{rule}"] for n in SAE[L0] if f"{n}_rep{rep}" in allr]
                if not s or not q: missing += 1; continue
                wins.append(max(s) > max(q)); detail.append(f"rep{rep}/{rule}: simple {max(s):.3f} vs SAE {max(q):.3f}")
        res[L0] = dict(holds=bool(wins) and all(wins) and not missing, missing=missing, detail=detail)
    levels = [v["holds"] for v in res.values()]; overall = "holds" if all(levels) else ("partial" if any(levels) else "does not hold")
    if any(v["missing"] for v in res.values()): overall += " (incomplete: missing rows)"
    out.append(f"**R-sae: {overall}.** " + " ".join(f"L0 {L0}: {v['holds']} ({'; '.join(v['detail'])})." for L0, v in res.items()))
    for part in (cpu, sae_):
        if part and "_sanity" in part: out.append(f"Sanity: {part['_sanity']}")
    return "\n\n".join(out), overall


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true"); a = ap.parse_args(); q = "_quick" if a.quick else ""
    a1, a2, cpu, sae_ = load(f"a1_probe_ladder{q}.json"), load(f"a2_sae_audit{q}.json"), load(f"a3_cpu{q}.json"), load(f"a3_sae{q}.json")
    parts = ["<!-- generated by a4_summarize.py from results/*.json; do not edit by hand -->", "# Stage A results (exploratory, 150 dev scans)"]
    if a1: parts.append(a1_section(a1))
    if a2: parts.append(a2_section(a2))
    if cpu or sae_: parts.append(a3_section(cpu, sae_)[0])
    path = HERE / f"RESULTS{q}.md"; path.write_text("\n\n".join(parts) + "\n", encoding="utf-8"); print(f"wrote {path}")


if __name__ == "__main__":
    main()
