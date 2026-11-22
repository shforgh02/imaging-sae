"""Lung L2, plan X11 (docs/EXECUTION_LOG.md, 22 Nov, commit 2a624b5; scripts bb7d258): the analysis of the padding / synthetic-stretch runs.
Exploratory, dev exams only, outcome-free (no label is read: the dev exam table is read with four columns only, series_uid, grp, ratio,
tag_maker). Written and committed BEFORE any X11 estimate is looked at; its output is committed before it is read.
Inputs: the X11 list, the X11 run folder (one json + npz per exam, x11_score.py), the cloud dev arrays (main / zfix per exam, used as the
reference where the exam has no local main_sp / zfix_sp run; gate G1 showed local CPU = cloud within 1e-4), the assembled dev arrays (axis-0
distribution of all dev main and z-fix runs), the frozen shared axes and Sybil's heads (results/s5, hash-checked by s6_frozen_analysis).
Measures per comparison (variant minus reference, paired within exam):
  d_l1, d_l6     change of the mean member logit of year 1 / year 6 (saved logits);
  d_ax0          change of shared axis 0 of `pooled` (frozen axes), in dev SD units (all 11 axes also kept);
  A0             axis-0-carried part: d_l1 from `pooled` minus d_l1 from `pooled` with axis 0 set to its dev mean in every member (both runs);
  pad mass       slice-attention mass (exp of the stored log-softmax att_vol1 / att_vol2, 25 bins of 8 input slices, input order: checked
                 in Sybil's pooling code) on padded input slices (reflect: on mirrored slices), weighted by the padded share of each bin.
Padded slices: the stored padding profile for value-0 (Sybil's) padding; computed from the real slice count for air padding, reflect and
cloud references, with torchio's placement (extra slice at the start; checked with torchio 0.18.74); computed = stored is checked
wherever both exist for value-0 padding (stop if not) and reported for air padding.
Statistics (plan): means with 95% bootstrap intervals over exams (2,000 draws, seed 0), paired within exam (one exam per participant).
Arm A is reported pooled (plain bootstrap), per maker and dev-weighted (GE : Philips : Siemens = 503 : 343 : 77; bootstrap stratified by
maker; makers absent from a subset are left out and the weights renormalised). Decided here, before any estimate is seen:
  - the arm A predictions are judged on the dev-weighted estimates (pooled and per maker shown beside them);
  - ratios ("keeps x%") are ratios of means over the same exams, with bootstrap intervals of the ratio;
  - A4 "|z-fix - every-second-slice| < 0.5 dev SD" uses the absolute value of the mean paired difference (the mean of per-exam absolute
    differences is reported beside it);
  - B1 slope: per exam, the least-squares slope of the shift on f over f = 1 (shift 0), 1.25, 1.5, 2.0, then the mean over exams;
    "f = 2.0 > f = 1.25 > 0" on the mean shifts; B2 "positive" = mean > 0 in each maker (interval shown);
  - main_air / f20_air / zfix_air runs skipped by x11_score.py because their volume equals the Sybil-padded twin take the twin's arrays.
Predictions and failure criteria: copied from the plan into CRITERIA below; each verdict is a string from the plan.
Also: the gates of x11_score.py (G1, G2) from the exam records; the O2 hash table (docs/O2_PLAN.md section 10) re-checked; the axis-0
distribution of dev main runs (contiguous 0.95-1.05, stretched 0-0.65, other) and z-fix runs, with the X11 variants placed on it.
usage (venv python): python x11_analysis.py <x11_list.csv> <x11 run dir> <cloud dev dir> <assembled dev dir> <out dir>
       [--frozen results/s5] [--run-info <l2 run_info dir>] [--code-check]
--code-check: runs on the exams done so far, writes to <out dir>, prints only structure and checks (no estimate).
"""
import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "lung_l0"))
import s4_common as S  # noqa: E402
import s5_axes_freeze as AXF  # noqa: E402
import s6_frozen_analysis as FA  # noqa: E402

KEYS = ("logit", "pooled", "att_vol1", "att_vol2")
N_BOOT, SEED = 2000, 0
DEV_W = {"GE": 503.0, "PHILIPS": 343.0, "SIEMENS": 77.0}
TWIN = {"main_air": "main_sp", "f20_air": "f20_sp", "zfix_air": "zfix_sp"}
CMP_A = [("zfix", "zfix_sp", "main_sp"), ("main_air", "main_air", "main_sp"), ("zfix_air_vs_main_air", "zfix_air", "main_air"), ("zfix_air_vs_main", "zfix_air", "main_sp"),
         ("padmatch", "padmatch_sp", "main_sp"), ("zfix_vs_padmatch", "zfix_sp", "padmatch_sp"), ("padmatch_air_vs_main_air", "padmatch_air", "main_air"),
         ("zfix_air_vs_padmatch_air", "zfix_air", "padmatch_air"), ("zfix_reflect", "zfix_reflect", "main_sp"), ("zfix_reflect_vs_zfix", "zfix_reflect", "zfix_sp"),
         ("decim0", "decim0", "main_sp"), ("decim1", "decim1", "main_sp"), ("zfix_vs_decim0", "zfix_sp", "decim0"), ("decim1_vs_decim0", "decim1", "decim0")]
CMP_B = [("f125", "f125_sp", "main_sp"), ("f15", "f15_sp", "main_sp"), ("f20", "f20_sp", "main_sp"), ("f20_air", "f20_air", "main_sp"), ("f20_air_vs_f20", "f20_air", "f20_sp"),
         ("f20_padmatch", "f20_padmatch", "main_sp"), ("f25", "f25_sp", "main_sp"), ("f25_vs_f20", "f25_sp", "f20_sp")]
MEAS = ("d_l1", "d_l6", "d_ax0", "A0", "pad1_var", "pad1_ref", "d_pad1", "pad2_var", "pad2_ref", "d_pad2")
CRITERIA = {
    "A1": "padding value: with air padding the z-fix change keeps >= 50% of its axis-0 shift and of delta lbar_1, same sign; otherwise the padding value is a primary driver",
    "A2": "padding amount: total z-fix axis-0 shift = [pad-matched - main] (box filling and cropping at stretched geometry) + [z-fix - pad-matched] (geometry at the same "
          "filling); 'geometry drives' if the second part is >= 50% of the total; 'box filling drives' if the first part is >= 70% and the second < 25%",
    "A3": "reflect: if reflect padding removes >= 70% of the z-fix shift, the constant slab drives it",
    "A4": "decimation: (every-second-slice - main) within +-25% of (z-fix - main) in axis 0 = the bug reproduced with unmodified Sybil; |z-fix - every-second-slice| < "
          "0.5 dev SD = slice overlap itself does not matter",
    "B1": "with Sybil's padding, axis 0 and A0 rise with f (slope interval > 0), axis 0 at f = 2.0 >= +2 dev SD, A0 >= +0.20, f = 2.0 > f = 1.25 > 0",
    "B2": "axis 0 and A0 positive at f = 2.0 in each of the four makers (delta lbar_1 by maker descriptive)",
    "B3": "f = 2.0 pad-matched - true keeps >= 50% of the f = 2.0 axis-0 shift = geometry matters; < 25% = box filling dominates",
    "B4": "plateau: among exams already filling the box at f = 2.0, f = 2.5 - f = 2.0 < 0.3 dev SD = saturation (box filling)"}


def sha_lf(p): return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def prof_T(T):
    """(200,) True on the slices torchio's CropOrPad pads when a volume of T real slices is brought to 200 (extra slice at the start)."""
    p = np.zeros(200, bool); T = int(T)
    if T < 200: s = math.ceil((200 - T) / 2); p[:s] = True; p[s + T:] = True
    return p


def padfrac(p): return np.asarray(p, float).reshape(25, 8).mean(1)


def pad_mass(att, p): return float((np.exp(np.asarray(att, np.float64)) @ padfrac(p)).mean())


# ------------------------------------------------------------------ loading
def load_exams(L, run_dir, cloud_dev, partial):
    recs, missing = [], []
    for r in L.itertuples():
        j = run_dir / f"{r.series_uid}.json"
        if not j.exists(): missing.append(r.series_uid); continue
        rec = json.loads(j.read_text()); rec["order"] = int(r.order); rec["pid"] = str(r.pid); recs.append(rec)
    if missing and not partial: raise SystemExit(f"REFUSED: {len(missing)} of {len(L)} exams not scored yet (use --code-check for a partial code check)")
    return recs, missing


def exam_arrays(rec, run_dir, cloud_dev):
    """{variant: dict(logit, pooled, att_vol1, att_vol2, prof, src)} for one exam; references from the cloud arrays when not run locally."""
    u = rec["series_uid"]; z = np.load(run_dir / f"{u}.npz"); out = {}; T = {}
    T["main_sp"] = rec["T_main"]
    if rec["arm"] == "A":
        Tz = rec["T_zfix"]; T.update(zfix_sp=Tz, zfix_air=Tz, zfix_reflect=Tz, main_air=rec["T_main"], padmatch_sp=min(min(Tz, 200), rec["T_main"]), padmatch_air=min(min(Tz, 200), rec["T_main"]))
    else:
        T.update(f20_sp=rec["T_f20"], f20_air=rec["T_f20"], f20_padmatch=min(min(rec["T_main"], 200), rec["T_f20"]))
    stored = {k.split("__")[0]: z[k] for k in z.files if k.endswith("__padprof")}
    for k in rec["variants"]:
        out[k] = {q: z[f"{k}__{q}"].astype(np.float64) for q in KEYS}; out[k]["src"] = "local"
    for k, sub in (("main_sp", "main"), ("zfix_sp", "zfix")):
        if k not in out and (k == "main_sp" or rec["arm"] == "A"):
            c = np.load(cloud_dev / sub / f"{u}.npz"); out[k] = {q: c[q].astype(np.float64) for q in KEYS}; out[k]["src"] = "cloud"
    for k, why in rec.get("skipped", {}).items():
        out[k] = dict(out[TWIN[k]]); out[k]["src"] = f"twin of {TWIN[k]} ({why})"
    chk = []
    for k, v in out.items():
        if k in T:
            v["prof"] = prof_T(T[k])
            if k in stored and k != "zfix_reflect":
                s_ = stored[k].astype(bool); extra = int((s_ & ~v["prof"]).sum())
                if k.endswith("_air"): chk.append(("air", k, bool(np.array_equal(v["prof"], s_)), extra))
                else: chk.append(("value0", k, bool((v["prof"] <= s_).all() and extra <= 2), extra))
        elif k in stored: v["prof"] = stored[k].astype(bool)
        else: raise SystemExit(f"REFUSED: no padding profile for {u} {k}")
    return out, chk


# ------------------------------------------------------------------ bootstrap
class Draws:
    """index draws over a subset of rows; stratified by maker when strata is given. Same draws for every measure of the subset (paired)."""
    def __init__(self, rows, strata=None):
        rng = np.random.default_rng(SEED); rows = np.asarray(rows); self.rows = rows; self.D = []
        if strata is None:
            for _ in range(N_BOOT): self.D.append(rows[rng.integers(0, len(rows), len(rows))])
        else:
            st = np.asarray(strata); groups = [rows[st == g] for g in sorted(set(st))]
            for _ in range(N_BOOT): self.D.append(np.concatenate([g[rng.integers(0, len(g), len(g))] for g in groups]))


def summary(fn, dr):
    est = fn(dr.rows); d = np.array([fn(t) for t in dr.D], float); d = d[np.isfinite(d)]
    ok = est is not None and np.isfinite(est) and len(d) >= 0.9 * N_BOOT
    return dict(est=None if est is None or not np.isfinite(est) else float(est), lo=float(np.percentile(d, 2.5)) if ok else None, hi=float(np.percentile(d, 97.5)) if ok else None,
                se=float(np.std(d, ddof=1)) if ok else None, n=int(len(dr.rows)), n_valid_draws=int(len(d)))


def wmean(v, mk, rows, weighted):
    x, m = v[rows], mk[rows]; ok = np.isfinite(x); x, m = x[ok], m[ok]
    if len(x) == 0: return np.nan
    if not weighted: return float(x.mean())
    num = den = 0.0
    for g, w in DEV_W.items():
        s = m == g
        if s.any(): num += w * x[s].mean(); den += w
    return num / den if den else np.nan


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("list"); ap.add_argument("run_dir"); ap.add_argument("cloud_dev"); ap.add_argument("assembled"); ap.add_argument("out")
    ap.add_argument("--frozen", default=str(HERE / "results" / "s5")); ap.add_argument("--run-info", default=r"D:\Shayan\imgsae_data\lung_l2_vol\l2\run_info")
    ap.add_argument("--code-check", action="store_true"); a = ap.parse_args()
    run_dir, cloud_dev, A, OUT = Path(a.run_dir), Path(a.cloud_dev), Path(a.assembled), Path(a.out); OUT.mkdir(parents=True, exist_ok=True)
    res = dict(label=("CODE CHECK on the exams done so far (not a result)" if a.code_check else "X11 analysis (plan 2a624b5; exploratory, dev only, outcome-free)"),
               criteria_from_plan=CRITERIA)
    # ---- O2 hash table (docs/O2_PLAN.md section 10): no O2 file may change
    plan = (HERE.parents[2] / "docs" / "O2_PLAN.md").read_text(encoding="utf-8"); sec = plan[plan.index("## 10."):]
    rows = re.findall(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \|", sec, flags=re.M); bad = [p for p, h in rows if sha_lf(HERE.parents[2] / p) != h]
    res["o2_hash_table"] = dict(n_files=len(rows), changed=bad, pass_=len(rows) > 0 and not bad)
    if not res["o2_hash_table"]["pass_"]: raise SystemExit(f"STOP: O2 hash table check failed: {bad}")
    # ---- frozen axes and heads (hash-checked)
    RI = Path(a.run_info); _, _, _, _, _, _, AX = FA.load_frozen(Path(a.frozen), RI)
    heads = S.C.load_heads(RI / "heads.npz"); fc = AXF.load_fc(RI / "heads.npz"); sd0, mu0 = float(AX["axis_sd_dev"][0]), float(AX["axis_mean_dev"][0])
    L = pd.read_csv(a.list, dtype={"pid": str}); recs, missing = load_exams(L, run_dir, cloud_dev, a.code_check)
    res["counts"] = dict(list=int(len(L)), scored=len(recs), not_scored=len(missing), by_arm_maker={f"{r['arm']}|{r['maker']}": 0 for r in recs})
    for r in recs: res["counts"]["by_arm_maker"][f"{r['arm']}|{r['maker']}"] += 1
    # ---- gates from the records
    g1 = [v["max_abs_logit"] for r in recs for v in r.get("gate_G1", {}).values()]
    res["gates"] = dict(G2_all=all(r.get("gate_G2") is True for r in recs), G1_n=len(g1), G1_max_abs_logit=max(g1) if g1 else None)
    if not res["gates"]["G2_all"] or (g1 and max(g1) > 1e-4): raise SystemExit("STOP: a gate of x11_score.py failed")
    # ---- per exam: arrays, padding profiles, measures
    var_rows, pchk, exam_rows = [], [], []
    for r in recs:
        V, chk = exam_arrays(r, run_dir, cloud_dev); pchk += chk
        exam_rows.append(dict(series_uid=r["series_uid"], pid=r["pid"], order=r["order"], arm=r["arm"], maker=r["maker"], ratio=r["ratio_list"], thickness=r["thickness"], spacing=r["spacing"],
                              T_main=r["T_main"], T_zfix=r.get("T_zfix"), T_f20=r.get("T_f20"), ref_src=V["main_sp"]["src"], seconds=r.get("seconds")))
        for k, v in V.items(): var_rows.append((r["series_uid"], k, v))
    bad0 = [c for c in pchk if c[0] == "value0" and not c[2]]
    res["checks"] = dict(padprof_value0_computed_within_stored_le2_extra=f"{sum(c[2] for c in pchk if c[0] == 'value0')} of {sum(c[0] == 'value0' for c in pchk)}",
                         padprof_value0_runs_with_extra_empty_edge_slices=int(sum(c[3] > 0 for c in pchk if c[0] == "value0")),
                         padprof_air_computed_equals_stored=f"{sum(c[2] for c in pchk if c[0] == 'air')} of {sum(c[0] == 'air' for c in pchk)}",
                         padprof_note="padded = slices added by torchio's CropOrPad (computed from the real slice count); a stored value-0 profile may also hold up to "
                                      "2 real edge slices that Sybil's resampling leaves empty (all 0); variants without a known slice count (f125, f15, f25, decim) use "
                                      "the stored profile")
    if bad0: raise SystemExit(f"STOP: computed padding profile differs from the stored one (value 0): {bad0[:3]}")
    X = np.stack([v["pooled"] for _, _, v in var_rows]); LG = np.stack([v["logit"] for _, _, v in var_rows])
    LP, LP0 = FA.logits_pooled(X, fc, heads), FA.logits_pooled(X, fc, heads, AX, [0]); act = AXF.activation(AX, X)
    res["checks"]["max_abs_lbar1_from_pooled_minus_saved"] = float(np.abs(LP[:, :, 0].mean(1) - LG[:, :, 0].mean(1)).max())
    if not res["checks"]["max_abs_lbar1_from_pooled_minus_saved"] <= 5e-3: raise SystemExit("STOP: lbar_1 rebuilt from pooled differs from the saved one")
    if not (np.isfinite(X).all() and np.isfinite(LG).all()): raise SystemExit("STOP: a non-finite array")
    F = {}
    for i, (u, k, v) in enumerate(var_rows):
        F[(u, k)] = dict(l1=LG[i, :, 0].mean(), l6=LG[i, :, 5].mean(), p1=LP[i, :, 0].mean(), p1off=LP0[i, :, 0].mean(), ax=act[i] / AX["axis_sd_dev"],
                         ax0abs=(act[i, 0] - mu0) / sd0, pad1=pad_mass(v["att_vol1"], v["prof"]), pad2=pad_mass(v["att_vol2"], v["prof"]), src=v["src"])
    Ex = pd.DataFrame(exam_rows); long = []
    for arm, cmps in (("A", CMP_A), ("B", CMP_B)):
        for name, kv, kr in cmps:
            for e in Ex[Ex.arm == arm].itertuples():
                fv, fr = F.get((e.series_uid, kv)), F.get((e.series_uid, kr))
                if fv is None or fr is None: continue
                d_ax = fv["ax"] - fr["ax"]
                long.append(dict(series_uid=e.series_uid, arm=arm, maker=e.maker, cmp=name, variant=kv, reference=kr, d_l1=fv["l1"] - fr["l1"], d_l6=fv["l6"] - fr["l6"], d_ax0=d_ax[0],
                                 A0=(fv["p1"] - fr["p1"]) - (fv["p1off"] - fr["p1off"]), pad1_var=fv["pad1"], pad1_ref=fr["pad1"], d_pad1=fv["pad1"] - fr["pad1"], pad2_var=fv["pad2"],
                                 pad2_ref=fr["pad2"], d_pad2=fv["pad2"] - fr["pad2"], ax0_var_abs=fv["ax0abs"], ax0_ref_abs=fr["ax0abs"], src_var=fv["src"], src_ref=fr["src"],
                                 **{f"d_ax{j}": d_ax[j] for j in range(1, len(d_ax))}))
    Lg = pd.DataFrame(long); Lg.to_csv(OUT / "x11_per_exam.csv", index=False, lineterminator="\n"); Ex.to_csv(OUT / "x11_exams.csv", index=False, lineterminator="\n")

    # ---- estimates per comparison
    def wide(arm, names, meas):
        """exam x comparison table of one measure for the given comparisons (NaN where missing)."""
        W = Lg[(Lg.arm == arm) & Lg.cmp.isin(names)].pivot(index="series_uid", columns="cmp", values=meas)
        E_ = Ex[Ex.arm == arm].set_index("series_uid"); return W.reindex(E_.index), E_.maker.to_numpy()
    est = {}
    for arm, cmps in (("A", CMP_A), ("B", CMP_B)):
        names = [c[0] for c in cmps]; est[arm] = {}
        for name in names:
            blk = {}
            for ms in MEAS:
                W, mk = wide(arm, [name], ms)
                if name not in W: continue
                v = W[name].to_numpy(float); rows_ = np.where(np.isfinite(v))[0]
                if len(rows_) == 0: continue
                b = dict(pooled=summary(lambda t, v=v: wmean(v, mk, t, False), Draws(rows_)))
                if arm == "A": b["dev_weighted"] = summary(lambda t, v=v: wmean(v, mk, t, True), Draws(rows_, mk[rows_]))
                b["by_maker"] = {g: summary(lambda t, v=v: wmean(v, mk, t, False), Draws(rows_[mk[rows_] == g])) for g in sorted(set(mk[rows_]))}
                blk[ms] = b
            if blk: est[arm][name] = blk
            sub = Lg[(Lg.arm == arm) & (Lg.cmp == name)]
            if len(sub): est[arm][name]["other_axes_mean_shift_dev_sd"] = {f"axis{j}": float(sub[f"d_ax{j}"].mean()) for j in range(1, 11)}
    res["estimates"] = est

    # ---- criteria
    def ratio(arm, num, den, meas, weighted, rows_filter=None, one_minus=False):
        W, mk = wide(arm, [num, den], meas)
        if num not in W or den not in W: return None
        a_, b_ = W[num].to_numpy(float), W[den].to_numpy(float); rows_ = np.where(np.isfinite(a_) & np.isfinite(b_))[0]
        if rows_filter is not None: rows_ = rows_[rows_filter(W.index.to_numpy()[rows_])]
        if len(rows_) == 0: return None

        def f(t):
            n_, d_ = wmean(a_, mk, t, weighted), wmean(b_, mk, t, weighted)
            if not np.isfinite(d_) or d_ == 0: return np.nan
            return 1 - n_ / d_ if one_minus else n_ / d_
        return summary(f, Draws(rows_, mk[rows_] if weighted else None))
    C = {}
    wA = True
    # A1
    k_ax, k_l1 = ratio("A", "zfix_air_vs_main_air", "zfix", "d_ax0", wA), ratio("A", "zfix_air_vs_main_air", "zfix", "d_l1", wA)
    kA0 = ratio("A", "zfix_air_vs_main_air", "zfix", "A0", wA)
    ok1 = None if k_ax is None or k_l1 is None or k_ax["est"] is None or k_l1["est"] is None else (k_ax["est"] >= 0.5 and k_l1["est"] >= 0.5)
    C["A1"] = dict(kept_share_axis0=k_ax, kept_share_lbar1=k_l1, kept_share_A0=kA0,
                   verdict=None if ok1 is None else ("padding value is not a primary driver (air keeps >= 50%, same sign)" if ok1 else "the padding value is a primary driver"))
    # A2
    s1, s2 = ratio("A", "padmatch", "zfix", "d_ax0", wA), ratio("A", "zfix_vs_padmatch", "zfix", "d_ax0", wA)
    if s1 and s2 and s1["est"] is not None and s2["est"] is not None:
        v2 = "geometry drives" if s2["est"] >= 0.5 else ("box filling drives" if (s1["est"] >= 0.7 and s2["est"] < 0.25) else "neither rule met (mixed)")
    else: v2 = None
    C["A2"] = dict(share_box_filling_part=s1, share_geometry_part=s2, share_box_filling_part_lbar1=ratio("A", "padmatch", "zfix", "d_l1", wA),
                   share_geometry_part_lbar1=ratio("A", "zfix_vs_padmatch", "zfix", "d_l1", wA), share_geometry_part_A0=ratio("A", "zfix_vs_padmatch", "zfix", "A0", wA),
                   with_air_padding=dict(share_box_filling_part=ratio("A", "padmatch_air_vs_main_air", "zfix_air_vs_main_air", "d_ax0", wA),
                                         share_geometry_part=ratio("A", "zfix_air_vs_padmatch_air", "zfix_air_vs_main_air", "d_ax0", wA)), verdict=v2)
    # A3
    rm = ratio("A", "zfix_reflect", "zfix", "d_ax0", wA, one_minus=True)
    C["A3"] = dict(share_removed_axis0=rm, share_removed_lbar1=ratio("A", "zfix_reflect", "zfix", "d_l1", wA, one_minus=True),
                   share_removed_A0=ratio("A", "zfix_reflect", "zfix", "A0", wA, one_minus=True),
                   verdict=None if rm is None or rm["est"] is None else ("the constant slab drives the z-fix shift" if rm["est"] >= 0.7 else "the constant slab does not drive it (reflect removes < 70%)"))
    # A4 (exams with ratio 0.5 and a decim0 run)
    r4 = ratio("A", "decim0", "zfix", "d_ax0", wA); W4, mk4 = wide("A", ["zfix_vs_decim0"], "d_ax0")
    if "zfix_vs_decim0" in W4:
        v4 = W4["zfix_vs_decim0"].to_numpy(float); rows4 = np.where(np.isfinite(v4))[0]
        dabs = summary(lambda t: abs(wmean(v4, mk4, t, wA)), Draws(rows4, mk4[rows4])) if len(rows4) else None
        mabs = summary(lambda t: wmean(np.abs(v4), mk4, t, wA), Draws(rows4, mk4[rows4])) if len(rows4) else None
    else: dabs = mabs = None
    rep = None if r4 is None or r4["est"] is None else (0.75 <= r4["est"] <= 1.25)
    ovl = None if dabs is None or dabs["est"] is None else (dabs["est"] < 0.5)
    C["A4"] = dict(ratio_decim_over_zfix_axis0=r4, ratio_decim_over_zfix_lbar1=ratio("A", "decim0", "zfix", "d_l1", wA), abs_mean_zfix_minus_decim0_axis0=dabs,
                   mean_abs_zfix_minus_decim0_axis0=mabs, verdict_reproduced=None if rep is None else ("the bug is reproduced with unmodified Sybil" if rep else "not reproduced (outside +-25%)"),
                   verdict_overlap=None if ovl is None else ("slice overlap itself does not matter" if ovl else "slice overlap itself matters (>= 0.5 dev SD)"))
    # B1
    def slope(meas):
        W, mk = wide("B", ["f125", "f15", "f20"], meas)
        if not {"f125", "f15", "f20"} <= set(W.columns): return None
        Y = W[["f125", "f15", "f20"]].to_numpy(float); ok = np.isfinite(Y).all(1); fx = np.array([1.0, 1.25, 1.5, 2.0])
        Yf = np.c_[np.zeros(len(Y)), Y]; sl = ((fx - fx.mean()) * (Yf - Yf.mean(1, keepdims=True))).sum(1) / ((fx - fx.mean()) ** 2).sum()
        rows_ = np.where(ok)[0]; return summary(lambda t: float(np.nanmean(sl[t])), Draws(rows_)) if len(rows_) else None
    eB = est.get("B", {}); g = lambda n, m: (eB.get(n, {}).get(m, {}).get("pooled", {}) or {}).get("est")   # noqa: E731
    sl_ax, sl_a0 = slope("d_ax0"), slope("A0")
    parts = dict(slope_axis0_interval_above_0=None if sl_ax is None or sl_ax["lo"] is None else sl_ax["lo"] > 0, slope_A0_interval_above_0=None if sl_a0 is None or sl_a0["lo"] is None else sl_a0["lo"] > 0,
                 axis0_f20_ge_2=None if g("f20", "d_ax0") is None else g("f20", "d_ax0") >= 2, A0_f20_ge_0p20=None if g("f20", "A0") is None else g("f20", "A0") >= 0.20,
                 axis0_f20_gt_f125_gt_0=None if g("f20", "d_ax0") is None or g("f125", "d_ax0") is None else g("f20", "d_ax0") > g("f125", "d_ax0") > 0,
                 A0_f20_gt_f125_gt_0=None if g("f20", "A0") is None or g("f125", "A0") is None else g("f20", "A0") > g("f125", "A0") > 0)
    C["B1"] = dict(slope_axis0_per_unit_f=sl_ax, slope_A0_per_unit_f=sl_a0, slope_lbar1_per_unit_f=slope("d_l1"), parts=parts,
                   verdict=None if any(v is None for v in parts.values()) else ("met" if all(parts.values()) else "not met: " + ", ".join(k for k, v in parts.items() if not v)))
    # B2
    bm = {m: dict(axis0=eB.get("f20", {}).get("d_ax0", {}).get("by_maker", {}).get(m), A0=eB.get("f20", {}).get("A0", {}).get("by_maker", {}).get(m),
                  lbar1=eB.get("f20", {}).get("d_l1", {}).get("by_maker", {}).get(m)) for m in ("GE", "PHILIPS", "SIEMENS", "TOSHIBA")}
    pos = {m: (None if not v["axis0"] or not v["A0"] or v["axis0"]["est"] is None or v["A0"]["est"] is None else (v["axis0"]["est"] > 0 and v["A0"]["est"] > 0)) for m, v in bm.items()}
    C["B2"] = dict(by_maker=bm, positive_by_maker=pos, verdict=None if any(v is None for v in pos.values()) else ("met in all four makers" if all(pos.values()) else
                                                                                                                 "not met in: " + ", ".join(m for m, v in pos.items() if not v)))
    # B3
    k3 = ratio("B", "f20_padmatch", "f20", "d_ax0", False)
    C["B3"] = dict(kept_share_axis0=k3, kept_share_lbar1=ratio("B", "f20_padmatch", "f20", "d_l1", False), kept_share_A0=ratio("B", "f20_padmatch", "f20", "A0", False),
                   verdict=None if k3 is None or k3["est"] is None else ("geometry matters" if k3["est"] >= 0.5 else ("box filling dominates" if k3["est"] < 0.25 else "between 25% and 50% (neither)")))
    # B4
    p4 = eB.get("f25_vs_f20", {}).get("d_ax0", {}).get("pooled")
    C["B4"] = dict(f25_minus_f20_axis0=p4, f25_minus_f20_lbar1=eB.get("f25_vs_f20", {}).get("d_l1", {}).get("pooled"),
                   verdict=None if p4 is None or p4["est"] is None else ("saturation (box filling)" if p4["est"] < 0.3 else "no plateau (>= 0.3 dev SD)"))
    res["criteria"] = C

    # ---- axis 0 of all dev main and z-fix runs ("back in distribution"); four columns of the dev table only (no outcome)
    Ed = pd.read_csv(A / "exams_dev.csv", usecols=["series_uid", "grp", "ratio", "tag_maker"], low_memory=False)
    if not (Ed.grp == "dev").all(): raise SystemExit("REFUSED: non-dev rows")
    rat = dict(zip(Ed.series_uid, pd.to_numeric(Ed.ratio, errors="coerce"))); dist = {}; edges = np.arange(-4, 10.01, 0.25)
    for var in ("main", "zfix"):
        z = np.load(A / f"arrays_dev_{var}.npz", allow_pickle=True); uid = z["series_uid"]; P = z["pooled"]; a0 = np.empty(len(uid))
        for s in range(0, len(uid), 500): a0[s:s + 500] = (AXF.activation(AX, P[s:s + 500].astype(np.float64))[:, 0] - mu0) / sd0
        r_ = np.array([rat.get(u, np.nan) for u in uid])
        groups = {"main": {"contiguous_0p95_1p05": (r_ >= 0.95) & (r_ <= 1.05), "stretched_0_0p65": (r_ > 0) & (r_ <= 0.65), "other": ~(((r_ >= 0.95) & (r_ <= 1.05)) | ((r_ > 0) & (r_ <= 0.65)))},
                  "zfix": {"stretched_0_0p65": (r_ > 0) & (r_ <= 0.65), "other": ~((r_ > 0) & (r_ <= 0.65))}}[var]
        for gname, m in groups.items():
            x = a0[m]
            if len(x) == 0: continue
            dist[f"{var}|{gname}"] = dict(n=int(len(x)), mean=float(x.mean()), sd=float(x.std()), quantiles={str(q): float(np.quantile(x, q)) for q in (0.05, 0.25, 0.5, 0.75, 0.95)},
                                         hist_edges=edges.tolist(), hist_counts=np.histogram(np.clip(x, edges[0], edges[-1]), edges)[0].tolist())
            if var == "main" and gname == "contiguous_0p95_1p05": ref_sorted = np.sort(x)
    place = {}; arm_of = dict(zip(Ex.series_uid, Ex.arm))
    for arm in ("A", "B"):
        for k in sorted({k for (u, k) in F if arm_of[u] == arm}):
            x = np.array([F[(u, kk)]["ax0abs"] for (u, kk) in F if kk == k and arm_of[u] == arm])
            place[f"{arm}|{k}"] = dict(n=int(len(x)), mean_axis0_dev_sd=float(x.mean()), median=float(np.median(x)),
                                       percentile_of_mean_in_dev_contiguous_main=float(np.searchsorted(ref_sorted, x.mean()) / len(ref_sorted) * 100))
    res["axis0_distribution"] = dict(note="axis 0 = (activation - dev mean) / dev SD of the frozen shared axis 0; dev arrays assembled from the cloud runs", dev=dist, x11_variants=place)
    res["exam_descriptives"] = dict(arm_A_T_main_le_200=int(((Ex.arm == "A") & (Ex.T_main <= 200)).sum()), arm_B_thickness_by_maker={m: sorted(Counter_(Ex[(Ex.arm == "B") & (Ex.maker == m)].thickness))
                                                                                                                                     for m in sorted(Ex[Ex.arm == "B"].maker.unique())},
                                    ref_source=Ex.ref_src.value_counts().to_dict(), cpu_seconds_total=float(Ex.seconds.fillna(0).sum()))
    js = json.dumps(clean(res), indent=1, sort_keys=False, allow_nan=False) + "\n"; (OUT / "x11_analysis_dev.json").write_text(js, encoding="utf-8", newline="\n")
    if a.code_check:
        nn = sum(1 for _ in walk_none(res["estimates"])); print(f"CODE CHECK written to {OUT}; exams {len(recs)} (missing {len(missing)}); comparisons A {len(est.get('A', {}))}, B {len(est.get('B', {}))}; "
                                                               f"None estimates {nn}; criteria {sorted(C)}; checks {res['checks']}; gates {res['gates']}; O2 hash {res['o2_hash_table']['pass_']}")
    else: print("written", OUT / "x11_analysis_dev.json", hashlib.sha256(js.encode()).hexdigest())


def Counter_(s): return [[float(k), int(v)] for k, v in pd.Series(s).value_counts().sort_index().items()]


def walk_none(o):
    if isinstance(o, dict):
        if "est" in o and o["est"] is None: yield o
        for v in o.values(): yield from walk_none(v)


def clean(o):
    if isinstance(o, dict): return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [clean(v) for v in o]
    if isinstance(o, np.bool_): return bool(o)
    if isinstance(o, np.integer): return int(o)
    if isinstance(o, (np.floating, float)): return None if not np.isfinite(o) else float(o)
    return o


if __name__ == "__main__":
    main()
