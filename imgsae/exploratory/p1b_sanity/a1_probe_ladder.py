"""A1 (exploratory, dev data): probe ladder. How much of what a linear probe reads from CT-FM tokens is already in label-free physical features,
in an untrained CT-FM, and on tasks harder than clean-token organ identity? Plan docs/SANITY_PLAN_v1.md, section A1.

Probe and bootstrap are the production ones (scripts/p1_probe.oof_proba / boot_auc: multinomial logistic, C = 1, balanced, patient-grouped
5-fold CV; patient-cluster bootstrap). Feature sets: ctfm, null (random-init CT-FM), R0-R4 (label-free reference ladder, see common.raw_ref_sets),
run (reference as run, z from vertebra masks; label-derived), ctfm+R3, null+R3.
Tasks (fixed in the plan before running):
  T1a  group concepts, clean tokens, the run's uniform 60k sample (sanity: ctfm / run must reproduce data/p1/gates.json)
  T1b  group concepts, clean tokens, concept-stratified (<= 2,000 per concept, 20,000 'other')
  T2   boundary tokens (label -2) with max group occupancy >= 0.5, labelled by that group (<= 2,000 per group)
  T3_* fine-grained leaf tasks on tokens whose dominant leaf occupancy >= 0.5: vertebra level, rib index (sides merged), lung lobe,
       body side of paired structures (<= 500 per leaf). Classes need >= 10 patients.
  T4   few labels: T1b and T3_* probes trained on 3 / 10 / 30 training-fold patients (3 draws), tested on the held-out fold.
Writes results/a1_probe_ladder.json (+ prediction cache results/a1_cache/). usage: ..\..\.venv\Scripts\python a1_probe_ladder.py [--quick] [--jobs 4]
"""
import argparse
import warnings

import numpy as np
from joblib import Parallel, delayed
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

from common import A, PR, RES, atlas, concepts, dump, gates, ladder, load_rows, log, raw_ref_sets, refpos, zrel

SETS_ALL = ["ctfm", "null", "R0", "R1", "R2", "R3", "R4", "run", "ctfm+R3", "null+R3"]
SETS_T1A = ["ctfm", "run", "null"]
SETS_T4 = ["ctfm", "null", "R3", "R4"]
LABEL_FREE = ["R0", "R1", "R2", "R3", "R4"]
N_FEW = [3, 10, 30]


def capped(idx, cap, rng):
    return idx if len(idx) <= cap else np.sort(rng.choice(idx, cap, replace=False))


def make_task(rows, cls, names, scan, min_pat=10, binary_score_first=True):
    """rows + class labels (strings) -> dict; drops classes with < min_pat patients; y = class index."""
    keep_cls = [c for c in names if len(np.unique(scan[rows[cls == c]])) >= min_pat or c == "other"]
    m = np.isin(cls, keep_cls); rows, cls = rows[m], cls[m]; y = np.array([keep_cls.index(c) for c in cls])
    scored = [c for c in keep_cls if c != "other"]
    if len(keep_cls) == 2 and binary_score_first: scored = scored[:1]  # binary: both one-vs-rest AUROCs are identical
    return dict(rows=rows, y=y, classes=keep_cls, scored=scored, n_tokens=int(len(rows)), n_patients=int(len(np.unique(scan[rows]))),
                per_class={c: dict(tokens=int((cls == c).sum()), patients=int(len(np.unique(scan[rows[cls == c]])))) for c in keep_cls})


def build_tasks(R, C, quick):
    lab, scan, occ, occg = R["lab"], R["scan"], R["occ"], R["occg"]; G, elig = C["groups"], C["eligible"]; gi = [G.index(g) for g in elig]
    cap, cap_other, cap_leaf = (100, 1000, 40) if quick else (2000, 20000, 500); T = {}
    # T1a: exactly the p1_probe sample
    keep = np.flatnonzero((lab == -1) | np.isin(lab, gi)); rng = np.random.default_rng(0)
    if len(keep) > 60000: keep = np.sort(rng.choice(keep, 60000, replace=False))
    if quick: keep = np.sort(np.random.default_rng(5).choice(keep, 5000, replace=False))
    cls = np.array(["other" if l_ < 0 else G[l_] for l_ in lab[keep]]); order = ["other"] + sorted(set(cls) - {"other"}, key=G.index)
    t = make_task(keep, cls, order, scan, min_pat=0); T["T1a"] = t
    # T1b: concept-stratified
    rng = np.random.default_rng(1); parts = [capped(np.flatnonzero(lab == -1), cap_other, rng)] + [capped(np.flatnonzero(lab == g), cap, rng) for g in gi]
    rows = np.sort(np.concatenate(parts)); cls = np.array(["other" if l_ < 0 else G[l_] for l_ in lab[rows]])
    T["T1b"] = make_task(rows, cls, ["other"] + elig, scan, min_pat=0)
    # T2: boundary tokens
    occg32 = occg.astype(np.float32); mx, arg = occg32.max(1), occg32.argmax(1); cand = (lab == -2) & (mx >= .5) & np.isin(arg, gi)
    rng = np.random.default_rng(2); rows = np.sort(np.concatenate([capped(np.flatnonzero(cand & (arg == g)), cap, rng) for g in gi]))
    T["T2"] = make_task(rows, np.array([G[a_] for a_ in arg[rows]]), elig, scan)
    # T3: fine-grained leaf tasks
    occ32 = occ.astype(np.float32); dom, share = occ32.argmax(1), occ32.max(1); L = atlas.LEAVES; ok = share >= .5
    def leaf_rows(leaf_idx, c, rng): return capped(np.flatnonzero(ok & (dom == leaf_idx)), c, rng)
    rng = np.random.default_rng(3); vert = [i for i, l_ in enumerate(L) if l_.startswith("vertebrae_")]
    rows = np.sort(np.concatenate([leaf_rows(i, cap, rng) for i in vert])); T["T3_vert"] = make_task(rows, np.array([L[d] for d in dom[rows]]), [L[i] for i in vert], scan)
    rib = [i for i, l_ in enumerate(L) if l_.startswith("rib_")]; idx_of = {i: f"rib{int(L[i].rsplit('_', 1)[1]):02d}" for i in rib}
    rows = np.sort(np.concatenate([capped(np.flatnonzero(ok & np.isin(dom, [i for i in rib if idx_of[i] == n])), cap, rng) for n in sorted(set(idx_of.values()))]))
    T["T3_rib"] = make_task(rows, np.array([idx_of[d] for d in dom[rows]]), sorted(set(idx_of.values())), scan)
    lobes = [L.index(n) for n in ("lung_upper_lobe_left", "lung_lower_lobe_left", "lung_upper_lobe_right", "lung_middle_lobe_right", "lung_lower_lobe_right")]
    rows = np.sort(np.concatenate([leaf_rows(i, cap, rng) for i in lobes])); T["T3_lobe"] = make_task(rows, np.array([L[d] for d in dom[rows]]), [L[i] for i in lobes], scan)
    mirror = lambda l_: l_[:-5] + "_right" if l_.endswith("_left") else l_[:-6] + "_left"  # noqa: E731
    paired = [i for i, l_ in enumerate(L) if (l_.endswith("_left") or l_.endswith("_right")) and mirror(l_) in L and not l_.startswith("kidney_cyst")]
    paired = [i for i in paired if len(np.unique(scan[ok & (dom == i)])) >= 10]
    rows = np.sort(np.concatenate([leaf_rows(i, cap_leaf, rng) for i in paired])); side = np.array(["left" if L[d].endswith("_left") else "right" for d in dom[rows]])
    t = make_task(rows, side, ["left", "right"], scan); t["struct"] = np.array([L[d].rsplit("_", 1)[0] for d in dom[t["rows"]]]); T["T3_side"] = t
    skipped = {k: dict(reason="< 2 classes with >= 10 patients", per_class=t["per_class"]) for k, t in T.items() if len([c for c in t["classes"] if c != "other"]) < 2 and k != "T3_side"}
    return {k: t for k, t in T.items() if k not in skipped}, skipped


def oof_few(X, y, g, n, draw, C=1.0):
    """as p1_probe.oof_proba, but each fold's training set is reduced to n random training-fold patients (seeded by n, draw, fold)."""
    P = np.zeros((len(y), int(y.max()) + 1))
    for k, (tr, te) in enumerate(GroupKFold(5).split(X, y, g)):
        pats = np.unique(g[tr]); pick = np.random.default_rng(1000 * n + 10 * draw + k).choice(pats, min(n, len(pats)), replace=False); tr = tr[np.isin(g[tr], pick)]
        if len(np.unique(y[tr])) < 2: continue
        sc = StandardScaler().fit(X[tr]); m = LogisticRegression(C=C, max_iter=300, class_weight="balanced").fit(sc.transform(X[tr]), y[tr])
        P[np.ix_(te, m.classes_)] = m.predict_proba(sc.transform(X[te]))
    return P


def run_probe(path, X, y, g, few=None):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always", ConvergenceWarning)
        P = PR.oof_proba(X, y, g) if few is None else oof_few(X, y, g, *few)
    np.save(path, P.astype(np.float32)); return path.name, sum(issubclass(x.category, ConvergenceWarning) for x in w)


def boot(key, s1, s2, y, g, B):
    r = PR.boot_auc(s1, s2, y, g, B=B); return key, r


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true"); ap.add_argument("--jobs", type=int, default=4); ap.add_argument("--B", type=int, default=500)
    a = ap.parse_args(); tag = "quick" if a.quick else "full"; cache = RES / f"a1_cache_{tag}"; cache.mkdir(exist_ok=True); B = 20 if a.quick else a.B
    C = concepts(); Gt = gates(); log(f"A1 {tag}: loading rows")
    R = load_rows(["lab", "scan", "occ", "occg", "gidx"]); scan = R["scan"]; Xs = {}  # feature matrices (~5.5 GB) only loaded if probes are left to run
    def feats(name, rows):
        if name == "ctfm": return R["X_ctfm"][rows]
        if name == "null": return R["X_null"][rows]
        if "+" in name: b, r = name.split("+"); return np.hstack([feats(b, rows), Xs[r][rows]])
        return Xs[name][rows]
    T, skipped = build_tasks(R, C, a.quick); del R["occ"], R["occg"]
    for k, t in T.items(): log(f"task {k}: {t['n_tokens']} tokens, {t['n_patients']} patients, {len(t['classes'])} classes")
    for k, s in skipped.items(): log(f"task {k} SKIPPED ({s['reason']}): {s['per_class']}")
    jobs = []
    for k, t in T.items():
        for s in (SETS_T1A if k == "T1a" else SETS_ALL): jobs.append((cache / f"{k}__{s}.npy", k, s, None))
        if k in ("T1b",) or k.startswith("T3_"):
            for s in SETS_T4:
                for n in (N_FEW[:1] if a.quick else N_FEW):
                    for dr in range(1 if a.quick else 3): jobs.append((cache / f"T4_{k}__{s}__n{n}__d{dr}.npy", k, s, (n, dr)))
    todo = [j for j in jobs if not j[0].exists()]; log(f"probes: {len(jobs)} total, {len(todo)} to run, {a.jobs} workers")
    if todo:
        R.update(load_rows(["X_ctfm", "X_null", "X_ref"])); ref, pos = refpos(C); raw = raw_ref_sets(ref, pos, zrel(R["gidx"], scan)); del ref, pos
        Xs.update({k: A.prep(v)[0] for k, v in raw.items()}); del raw
        d = float(np.abs(Xs["run"][:50000] - R["X_ref"][:50000]).max()); log(f"max |rebuilt run reference - X_ref| = {d:.2e}"); assert d < 1e-2, d
        del R["X_ref"]
        gen = (delayed(run_probe)(p, feats(s, T[k]["rows"]), T[k]["y"], scan[T[k]["rows"]], few) for p, k, s, few in todo)
        for i, (nm, nw) in enumerate(Parallel(n_jobs=a.jobs, return_as="generator", pre_dispatch="n_jobs", max_nbytes=None)(gen)):  # no memmap spill to C:
            log(f"  probe {i + 1}/{len(todo)} {nm}" + (f" ({nw} convergence warnings)" if nw else ""))
        for k in ("X_ctfm", "X_null"): R.pop(k, None)
        Xs.clear()
    # ---- analysis
    out = dict(tag=tag, B=B, tasks={}, skipped=skipped); bjobs = []
    for k, t in T.items():
        y, g = t["y"], scan[t["rows"]]; sets = SETS_T1A if k == "T1a" else SETS_ALL; P = {s: np.load(cache / f"{k}__{s}.npy") for s in sets}
        auc = {s: {c: ladder.auroc(P[s][:, t["classes"].index(c)], y == t["classes"].index(c)) for c in t["scored"]} for s in sets}
        med = {s: float(np.nanmedian(list(v.values()))) for s, v in auc.items()}
        res = dict(n_tokens=t["n_tokens"], n_patients=t["n_patients"], per_class=t["per_class"], scored=t["scored"], auc=auc, median=med)
        if k == "T1a": comps = [("ctfm", "run")]
        else:
            best = max(LABEL_FREE, key=lambda s: med[s]); res["best_ref"] = best
            comps = [("ctfm", best), ("ctfm", "null"), ("ctfm+R3", "R3"), ("null+R3", "R3")]
        res["comparisons"] = {f"{a_}|{b_}": {} for a_, b_ in comps}
        for a_, b_ in comps:
            for c in t["scored"]:
                ci = t["classes"].index(c); bjobs.append(((k, f"{a_}|{b_}", c), P[a_][:, ci], P[b_][:, ci], y == ci, g, B))
        if k == "T3_side":
            st = t["struct"]; res["side_by_structure"] = {u: {s: ladder.auroc(P[s][st == u, 0], y[st == u] == 0) for s in sets} for u in sorted(set(st))}
        out["tasks"][k] = res
        if k == "T1b" or k.startswith("T3_"):
            few = {}
            for n in (N_FEW[:1] if a.quick else N_FEW):
                Pn = {s: [np.load(cache / f"T4_{k}__{s}__n{n}__d{dr}.npy") for dr in range(1 if a.quick else 3)] for s in SETS_T4}
                Pm = {s: np.mean(v, 0) for s, v in Pn.items()}
                aucm = {s: {c: ladder.auroc(Pm[s][:, t["classes"].index(c)], y == t["classes"].index(c)) for c in t["scored"]} for s in SETS_T4}
                aucd = {s: {c: float(np.mean([ladder.auroc(p[:, t["classes"].index(c)], y == t["classes"].index(c)) for p in Pn[s]])) for c in t["scored"]} for s in SETS_T4}
                medm = {s: float(np.nanmedian(list(v.values()))) for s, v in aucm.items()}; best = max(["R3", "R4"], key=lambda s: medm[s])
                few[f"n{n}"] = dict(auc_drawavg=aucm, auc_per_draw_mean=aucd, median=medm, median_per_draw={s: float(np.nanmedian(list(v.values()))) for s, v in aucd.items()},
                                    best_ref=best, comparisons={f"ctfm|{best}": {}, "ctfm|null": {}})
                for a_, b_ in (("ctfm", best), ("ctfm", "null")):
                    for c in t["scored"]:
                        ci = t["classes"].index(c); bjobs.append(((f"T4:{k}:n{n}", f"{a_}|{b_}", c), Pm[a_][:, ci], Pm[b_][:, ci], y == ci, g, min(B, 200)))
            out["tasks"][k]["few"] = few
    log(f"bootstrap: {len(bjobs)} comparisons")
    for key, r in Parallel(n_jobs=a.jobs, max_nbytes=None)(delayed(boot)(*j) for j in bjobs):
        tk, comp, c = key
        if tk.startswith("T4:"): _, k, n = tk.split(":"); out["tasks"][k]["few"][n]["comparisons"][comp][c] = r
        else: out["tasks"][tk]["comparisons"][comp][c] = r
    # ---- sanity + reading rules (plan A4)
    t1a = out["tasks"]["T1a"]; g_tok = Gt["token"]
    if not a.quick:
        dd = [abs(t1a["auc"]["ctfm"][c] - g_tok[c]["auc"]) for c in t1a["scored"]] + [abs(t1a["auc"]["run"][c] - g_tok[c]["auc_ref"]) for c in t1a["scored"]]
        out["sanity_T1a_max_abs_diff_vs_gates"] = float(max(dd)); log(f"sanity T1a vs gates.json: max |diff| = {max(dd):.2e}")
    rules = {}; t1b = out["tasks"]["T1b"]
    d3 =[t1b["auc"]["ctfm"][c] - t1b["auc"]["R3"][c] for c in t1b["scored"]]
    rules["R_sat"] = dict(median_ctfm=t1b["median"]["ctfm"], median_null=t1b["median"]["null"], median_R3=t1b["median"]["R3"], median_diff_ctfm_R3=float(np.median(d3)),
                          holds=bool(min(t1b["median"]["ctfm"], t1b["median"]["null"], t1b["median"]["R3"]) >= .97 and abs(np.median(d3)) <= .01))
    def wins(comp_best, comp_null, scored):
        w = [c for c in scored if comp_best[c]["diff"] >= .05 and comp_best[c]["ci_diff"][0] > 0 and comp_null[c]["diff"] >= .05 and comp_null[c]["ci_diff"][0] > 0]
        return w, len(w) / max(len(scored), 1)
    fm = {}
    for k, t in out["tasks"].items():
        if k in ("T2",) or k.startswith("T3_"):
            w, sh = wins(t["comparisons"][f"ctfm|{t['best_ref']}"], t["comparisons"]["ctfm|null"], t["scored"]); fm[k] = dict(best_ref=t["best_ref"], wins=w, share=sh)
        for n, f in t.get("few", {}).items():
            w, sh = wins(f["comparisons"][f"ctfm|{f['best_ref']}"], f["comparisons"]["ctfm|null"], t["scored"]); fm[f"T4:{k}:{n}"] = dict(best_ref=f["best_ref"], wins=w, share=sh)
    rules["R_fm"] = dict(by_task=fm, holds=bool(any(v["share"] >= 1 / 3 for v in fm.values())))
    out["rules"] = rules; dump(out, RES / f"a1_probe_ladder{'_quick' if a.quick else ''}.json")
    log(f"R_sat {rules['R_sat']}"); log(f"R_fm holds {rules['R_fm']['holds']}: " + ", ".join(f"{k} {v['share']:.2f}" for k, v in fm.items())); log("DONE")


if __name__ == "__main__":
    main()
