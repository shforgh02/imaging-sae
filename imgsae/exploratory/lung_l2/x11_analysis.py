"""Lung L2, plan X11 (docs/EXECUTION_LOG.md, 22 Nov, commit 2a624b5; scripts bb7d258; scoring amendment A1 98a09d5): the analysis of the
padding / synthetic-stretch runs. Exploratory, dev exams only, outcome-free (the dev exam table is read with four columns only: series_uid,
grp, ratio, tag_maker). Written and committed BEFORE any X11 estimate is looked at (first version f11c610; this revision R1 after Neon's
review, still before any estimate); its output is committed before it is read.
Inputs: the X11 list, the X11 run folder (one json + npz per exam, x11_score.py), the cloud dev arrays (main / zfix per exam, the reference
where the exam has no local main_sp / zfix_sp run; gate G1: local CPU = cloud within 1e-4), the assembled dev arrays (axis-0 distribution of
all dev main and z-fix runs), the frozen shared axes and Sybil's heads (results/s5, hash-checked by s6_frozen_analysis).
Measures per comparison (variant minus reference, paired within exam):
  d_l1, d_l6     change of the mean member logit of year 1 / year 6 (saved logits); big6 = 1 if |d_l6| >= 0.25 x 0.92957 (the O2-H1 rule);
  d_ax0          change of shared axis 0 of `pooled` (frozen axes), in dev SD units; split exactly into the three blocks of `pooled`
                 (0:512 volume attention pool 1, 512:1024 volume attention pool 2, 1024:1536 global max pool; Sybil's pooling_layer.py);
  A0             axis-0-carried part: d_l1 from `pooled` minus d_l1 from `pooled` with axis 0 set to its dev mean in every member (both runs);
  d_l1_off       the rest: d_l1 from `pooled` with axis 0 removed in both runs;
  pad mass       slice-attention mass (softmax of the stored float16 log-softmax att_vol1 / att_vol2, renormalised; 25 bins of 8 input slices,
                 input order, checked in Sybil's pooling code) on padded input slices (reflect: mirrored slices), weighted by the padded share of
                 each bin; also the mass on fully padded bins and on boundary bins (att_vol1). att_vol2 passes a Conv1d (kernel 11) first.
Padded slices: computed from the real slice count with torchio's placement (extra slice at the start; torchio 0.18.74) for every variant with
a known count; stored profile otherwise (f125, f15, f25, decim); computed must lie within the stored profile with at most 2 extra (empty
resampled edge) slices, for value-0 AND air padding (stop otherwise).
Statistics: means with 95% bootstrap intervals over exams (2,000 draws, seed 0), paired within exam (one exam per participant). Arm A: pooled
(plain bootstrap), per maker, and dev-weighted (bootstrap stratified by maker). Weights from the dev table (outcome-free): the maker counts of
stretched dev exams (0 < ratio <= 0.65; the plan's 503 : 343 : 77 is checked) and, for the ratio-0.5 subset (A4: decim0 / decim1), the maker
counts of dev exams with |ratio - 0.5| < 0.02. A maker with fewer than 5 exams in a subset is left out of the weighted estimate (shown per
maker). Arm B: pooled with a bootstrap stratified by maker (12 per maker). Ratios ("keeps x%") are ratios of means on the same exams with the
interval of the ratio; each ratio also reports its denominator and where its interval lies against the decision boundary.
Rules decided before any estimate is seen (R1 tightened after Neon's review; the plan's wording is in CRITERIA):
  A1  air keeps >= 50% of the z-fix axis-0 shift AND of d_l1 (point estimates; ratio intervals reported) -> not a primary driver.
  A2  shares of the z-fix axis-0 shift: geometry part >= 50% -> geometry drives; box part >= 70% and geometry part < 25% -> box filling drives.
  A3  judged on axis 0 (d_l1 and A0 reported): reflect removes >= 70% -> the constant slab drives it.
  A4  reproduced: (decim0 - main) / (z-fix - main) in axis 0 within 0.75 to 1.25 (weights of the ratio-0.5 subset); overlap does not matter:
      the signed mean (z-fix - decim0) has its 95% interval inside (-0.5, +0.5) AND the mean absolute difference < 0.5 dev SD.
  B1  met only if, for axis 0 AND A0: the 4-point slope over f = 1 (0), 1.25, 1.5, 2.0 has its interval > 0; the stretched-only 3-point slope
      (1.25, 1.5, 2.0) has its interval > 0; f = 1.25 has its interval > 0; f2.0 - f1.25 (paired) has its interval > 0; and axis 0 at
      f = 2.0 >= +2 dev SD, A0 at f = 2.0 >= +0.20 (point estimates).
  B2  axis 0 AND A0 at f = 2.0 have their interval > 0 in each of the four makers.
  B3  f20_padmatch keeps >= 50% of the f = 2.0 axis-0 shift -> geometry matters; < 25% -> box filling dominates.
  B4  on the f = 2.5 exams (all fill the box at f = 2.0; checked): |f2.5 - f2.0| < 0.3 dev SD -> saturation; <= -0.3 -> reversal; >= +0.3 ->
      no plateau; A0 reported; makers counted.
  B5  (new with scoring amendment A1, before any arm B exam was scored) f = 2.0 against the AIR-padded true geometry keeps >= 50% of the
      axis-0 shift against the Sybil-padded true geometry -> the stretch effect does not come from the reference's padding value; < 25% -> it
      does; between -> partly.
Secondary (descriptive): the three-block split of every axis-0 shift; arm A cropped (T_main > 200) vs uncropped (T_main <= 200); A1 to A3
on the 60 exams drawn by the plan (order < 60); arm B by f = 1.5 already filling the box or not and by slice thickness; d_l1_off and big6;
attention on fully padded and boundary bins; the share of exams whose axis 0 lies inside the 5th to 95th percentile of dev contiguous
main runs; skipped-twin counts.
usage (venv python): python x11_analysis.py <x11_list.csv> <x11 run dir> <cloud dev dir> <assembled dev dir> <out dir>
       [--frozen results/s5] [--run-info <l2 run_info dir>] [--code-check]
--code-check: runs on the exams done so far, writes x11_code_check.json to <out dir>, prints only structure and checks (no estimate).
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
N_BOOT, SEED, MIN_STRATUM, SD6 = 2000, 0, 5, 0.92957
PLAN_DEV_W = {"GE": 503, "PHILIPS": 343, "SIEMENS": 77}
TWIN = {"main_air": "main_sp", "f20_air": "f20_sp", "zfix_air": "zfix_sp"}
BLOCKS = {"attn1": slice(0, 512), "attn2": slice(512, 1024), "maxpool": slice(1024, 1536)}
CMP_A = [("zfix", "zfix_sp", "main_sp"), ("main_air", "main_air", "main_sp"), ("zfix_air_vs_main_air", "zfix_air", "main_air"), ("zfix_air_vs_main", "zfix_air", "main_sp"),
         ("padmatch", "padmatch_sp", "main_sp"), ("zfix_vs_padmatch", "zfix_sp", "padmatch_sp"), ("padmatch_air_vs_main_air", "padmatch_air", "main_air"),
         ("zfix_air_vs_padmatch_air", "zfix_air", "padmatch_air"), ("zfix_reflect", "zfix_reflect", "main_sp"), ("zfix_reflect_vs_zfix", "zfix_reflect", "zfix_sp"),
         ("decim0", "decim0", "main_sp"), ("decim1", "decim1", "main_sp"), ("zfix_vs_decim0", "zfix_sp", "decim0"), ("decim1_vs_decim0", "decim1", "decim0")]
CMP_B = [("f125", "f125_sp", "main_sp"), ("f15", "f15_sp", "main_sp"), ("f20", "f20_sp", "main_sp"), ("f20_air", "f20_air", "main_sp"), ("f20_air_vs_f20", "f20_air", "f20_sp"),
         ("f20_padmatch", "f20_padmatch", "main_sp"), ("f25", "f25_sp", "main_sp"), ("f25_vs_f20", "f25_sp", "f20_sp"), ("main_air", "main_air", "main_sp"),
         ("f20_vs_main_air", "f20_sp", "main_air")]
DECIM = {"decim0", "decim1", "zfix_vs_decim0", "decim1_vs_decim0"}
MEAS = ("d_l1", "d_l6", "big6", "d_ax0", "d_ax0_attn1", "d_ax0_attn2", "d_ax0_maxpool", "A0", "d_l1_off", "pad1_var", "pad1_ref", "d_pad1", "pad2_var", "pad2_ref", "d_pad2",
        "padfull1_var", "padfull1_ref", "padbound1_var")
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
    "B4": "plateau: among exams already filling the box at f = 2.0, f = 2.5 - f = 2.0 < 0.3 dev SD = saturation (box filling)",
    "B5": "(amendment A1) f = 2.0 vs the air-padded true geometry keeps >= 50% of the axis-0 shift vs the Sybil-padded true geometry = the stretch effect does not come "
          "from the reference's padding value; < 25% = it does"}


def sha_lf(p): return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def maker_of(tag):
    t = str(tag).upper()
    for k, v in (("PHILIPS", "PHILIPS"), ("SIEMENS", "SIEMENS"), ("TOSHIBA", "TOSHIBA"), ("CANON", "TOSHIBA"), ("GE", "GE")):
        if k in t: return v
    return "OTHER"


def prof_T(T):
    """(200,) True on the slices torchio's CropOrPad pads when a volume of T real slices is brought to 200 (extra slice at the start)."""
    p = np.zeros(200, bool); T = int(T)
    if T < 200: s = math.ceil((200 - T) / 2); p[:s] = True; p[s + T:] = True
    return p


def padfrac(p): return np.asarray(p, float).reshape(25, 8).mean(1)


def att_w(att):
    a = np.asarray(att, np.float64); w = np.exp(a - a.max(1, keepdims=True)); return w / w.sum(1, keepdims=True)


def att_masses(att, p):
    w = att_w(att); f = padfrac(p); return float((w @ f).mean()), float(w[:, f == 1].sum(1).mean()), float(w[:, (f > 0) & (f < 1)].sum(1).mean())


def ax0_blocks(AX, dX):
    """exact split of the axis-0 change (dev SD units) of `pooled` difference dX (5, 1536) into the three blocks of `pooled`."""
    out = {}
    for b, sl in BLOCKS.items():
        v = []
        for m in range(5):
            t = AX["members"][m]; d = np.zeros(dX.shape[1]); d[sl] = dX[m, sl]
            v.append((d[t["live"]] / t["sd"][t["live"]]) @ t["P"].T / t["sc"] @ t["W"][:, 0])
        out[b] = float(np.mean(v)) / float(AX["axis_sd_dev"][0])
    return out


# ------------------------------------------------------------------ loading
def load_exams(L, run_dir, partial):
    recs, missing = [], []
    for r in L.itertuples():
        j = run_dir / f"{r.series_uid}.json"
        if not j.exists(): missing.append(r.series_uid); continue
        rec = json.loads(j.read_text()); rec["order"] = int(r.order); rec["pid"] = str(r.pid); recs.append(rec)
    if missing and not partial: raise SystemExit(f"REFUSED: {len(missing)} of {len(L)} exams not scored yet (use --code-check for a partial code check)")
    return recs, missing


def exam_arrays(rec, run_dir, cloud_dev):
    """{variant: dict(logit, pooled, att_vol1, att_vol2, prof, src)} for one exam; references from the cloud arrays when not run locally."""
    u = rec["series_uid"]; z = np.load(run_dir / f"{u}.npz"); out = {}; T = dict(main_sp=rec["T_main"], main_air=rec["T_main"])
    if rec["arm"] == "A":
        Tz = rec["T_zfix"]; pm = min(min(Tz, 200), rec["T_main"]); T.update(zfix_sp=Tz, zfix_air=Tz, zfix_reflect=Tz, padmatch_sp=pm, padmatch_air=pm)
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
                chk.append(("air" if k.endswith("_air") else "value0", k, bool((v["prof"] <= s_).all() and extra <= 2), extra))
        elif k in stored: v["prof"] = stored[k].astype(bool)
        else: raise SystemExit(f"REFUSED: no padding profile for {u} {k}")
    return out, chk


# ------------------------------------------------------------------ bootstrap (vectorised; the same draws for every measure of a subset)
class Draws:
    def __init__(self, rows, strata=None):
        rows = np.asarray(rows); rng = np.random.default_rng(SEED)
        lab = np.array(["all"] * len(rows)) if strata is None else np.asarray(strata)
        self.blocks = []; cols = []; start = 0
        for g in sorted(set(lab)):
            r = rows[lab == g]; self.blocks.append((g, slice(start, start + len(r)))); cols.append(r); start += len(r)
        self.rows = np.concatenate(cols) if cols else rows
        self.D = np.empty((N_BOOT, len(self.rows)), int)
        for g, sl in self.blocks:
            r = self.rows[sl]; self.D[:, sl] = r[rng.integers(0, len(r), (N_BOOT, len(r)))]

    def mean(self, v, weights=None):
        """(estimate, draws) of the mean of v, or of the weighted mean of the stratum means (weights: {stratum: w})."""
        if weights is None: return float(np.mean(v[self.rows])), v[self.D].mean(1)
        num_e = den = 0.0; num_d = np.zeros(N_BOOT)
        for g, sl in self.blocks:
            w = weights.get(g, 0.0)
            if w: num_e += w * float(v[self.rows[sl]].mean()); num_d += w * v[self.D[:, sl]].mean(1); den += w
        return (num_e / den, num_d / den) if den else (np.nan, np.full(N_BOOT, np.nan))


def summ(est, d):
    d = np.asarray(d, float); d = d[np.isfinite(d)]; ok = est is not None and np.isfinite(est) and len(d) >= 0.9 * N_BOOT
    return dict(est=None if est is None or not np.isfinite(est) else float(est), lo=float(np.percentile(d, 2.5)) if ok else None, hi=float(np.percentile(d, 97.5)) if ok else None,
                se=float(np.std(d, ddof=1)) if ok else None, n_valid_draws=int(len(d)))


def side(s, b):
    if not s or s.get("lo") is None: return None
    return "above" if s["lo"] >= b else ("below" if s["hi"] < b else "straddles")


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("list"); ap.add_argument("run_dir"); ap.add_argument("cloud_dev"); ap.add_argument("assembled"); ap.add_argument("out")
    ap.add_argument("--frozen", default=str(HERE / "results" / "s5")); ap.add_argument("--run-info", default=r"D:\Shayan\imgsae_data\lung_l2_vol\l2\run_info")
    ap.add_argument("--code-check", action="store_true"); a = ap.parse_args()
    run_dir, cloud_dev, A, OUT = Path(a.run_dir), Path(a.cloud_dev), Path(a.assembled), Path(a.out); OUT.mkdir(parents=True, exist_ok=True)
    res = dict(label=("CODE CHECK on the exams done so far (not a result)" if a.code_check else "X11 analysis (plan 2a624b5, scoring amendment A1, analysis R1; exploratory, dev only, outcome-free)"),
               criteria_from_plan=CRITERIA)
    # ---- O2 hash table (docs/O2_PLAN.md section 10): no O2 file may change
    plan = (HERE.parents[2] / "docs" / "O2_PLAN.md").read_text(encoding="utf-8"); sec = plan[plan.index("## 10."):]
    rows = re.findall(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \|", sec, flags=re.M); bad = [p for p, h in rows if sha_lf(HERE.parents[2] / p) != h]
    res["o2_hash_table"] = dict(n_files=len(rows), changed=bad, pass_=len(rows) > 0 and not bad)
    if not res["o2_hash_table"]["pass_"]: raise SystemExit(f"STOP: O2 hash table check failed: {bad}")
    # ---- frozen axes and heads (hash-checked); dev table (four columns, no outcome) for weights and the distribution
    RI = Path(a.run_info); _, _, _, _, _, _, AX = FA.load_frozen(Path(a.frozen), RI)
    heads = S.C.load_heads(RI / "heads.npz"); fc = AXF.load_fc(RI / "heads.npz"); sd0, mu0 = float(AX["axis_sd_dev"][0]), float(AX["axis_mean_dev"][0])
    Ed = pd.read_csv(A / "exams_dev.csv", usecols=["series_uid", "grp", "ratio", "tag_maker"], low_memory=False)
    if not (Ed.grp == "dev").all(): raise SystemExit("REFUSED: non-dev rows")
    Ed["ratio"] = pd.to_numeric(Ed.ratio, errors="coerce"); Ed["mk"] = Ed.tag_maker.map(maker_of)
    st = Ed[(Ed.ratio > 0) & (Ed.ratio <= 0.65)]; W_ST = {k: float(v) for k, v in st.mk.value_counts().items() if k in PLAN_DEV_W}
    W05 = {k: float(v) for k, v in Ed[(Ed.ratio - 0.5).abs() < 0.02].mk.value_counts().items() if k in PLAN_DEV_W}
    res["weights"] = dict(stretched_dev_counts=W_ST, plan_counts=PLAN_DEV_W, equal_to_plan=all(int(W_ST.get(k, 0)) == v for k, v in PLAN_DEV_W.items()), ratio_0p5_dev_counts=W05,
                          min_exams_per_maker_in_weighted_estimates=MIN_STRATUM)
    WA = {k: float(v) for k, v in PLAN_DEV_W.items()}                        # the plan's weights (equality with the dev table is reported)
    L = pd.read_csv(a.list, dtype={"pid": str}); recs, missing = load_exams(L, run_dir, a.code_check)
    if not set(L.series_uid) <= set(Ed.series_uid): raise SystemExit("REFUSED: an X11 exam is not in the dev table")
    res["counts"] = dict(list=int(len(L)), scored=len(recs), not_scored=len(missing), by_arm_maker={})
    for r in recs: res["counts"]["by_arm_maker"][f"{r['arm']}|{r['maker']}"] = res["counts"]["by_arm_maker"].get(f"{r['arm']}|{r['maker']}", 0) + 1
    # ---- gates from the records
    g1 = [(v.get("max_abs_logit"), v.get("max_abs_pooled")) for r in recs for v in r.get("gate_G1", {}).values()]
    n_ident = sum(1 for r in recs if r.get("gate_G1"))
    res["gates"] = dict(G2_all=all(r.get("gate_G2") is True for r in recs), G1_n=len(g1), G1_exams=n_ident,
                        G1_max_abs_logit=max((x for x, _ in g1), default=None), G1_max_abs_pooled=max((y for _, y in g1), default=None))
    fin = all(x is not None and y is not None and np.isfinite(x) and np.isfinite(y) for x, y in g1)
    if not res["gates"]["G2_all"] or not fin or (g1 and (max(x for x, _ in g1) > 1e-4 or max(y for _, y in g1) > 1e-3)): raise SystemExit("STOP: a gate of x11_score.py failed")
    if not a.code_check and len(g1) != 18: raise SystemExit(f"STOP: {len(g1)} G1 values (18 expected: 6 arm A exams x 2 runs + 6 arm B exams)")
    # ---- per exam: arrays, padding profiles, measures
    var_rows, pchk, exam_rows = [], [], []
    for r in recs:
        V, chk = exam_arrays(r, run_dir, cloud_dev); pchk += chk
        exam_rows.append(dict(series_uid=r["series_uid"], pid=r["pid"], order=r["order"], arm=r["arm"], maker=r["maker"], ratio=r["ratio_list"], thickness=r["thickness"], spacing=r["spacing"],
                              T_main=r["T_main"], T_zfix=r.get("T_zfix"), T_f20=r.get("T_f20"), n_pad_f15=r.get("n_padded", {}).get("f15_sp"), ref_src=V["main_sp"]["src"],
                              skipped=";".join(sorted(r.get("skipped", {}))), seconds=r.get("seconds")))
        for k, v in V.items(): var_rows.append((r["series_uid"], k, v))
    Ex = pd.DataFrame(exam_rows)
    if not (Ex.series_uid.is_unique and Ex.pid.is_unique): raise SystemExit("STOP: an exam or participant appears twice")
    badp = [c for c in pchk if not c[2]]
    res["checks"] = dict(padprof_value0_ok=f"{sum(c[2] for c in pchk if c[0] == 'value0')} of {sum(c[0] == 'value0' for c in pchk)}",
                         padprof_air_ok=f"{sum(c[2] for c in pchk if c[0] == 'air')} of {sum(c[0] == 'air' for c in pchk)}",
                         padprof_runs_with_extra_empty_edge_slices=int(sum(c[3] > 0 for c in pchk)))
    if badp: raise SystemExit(f"STOP: computed padding profile not within the stored one: {badp[:3]}")
    X = np.stack([v["pooled"] for _, _, v in var_rows]); LG = np.stack([v["logit"] for _, _, v in var_rows])
    if not (np.isfinite(X).all() and np.isfinite(LG).all()): raise SystemExit("STOP: a non-finite array")
    LP, LP0 = FA.logits_pooled(X, fc, heads), FA.logits_pooled(X, fc, heads, AX, [0]); act = AXF.activation(AX, X)
    res["checks"]["max_abs_lbar1_from_pooled_minus_saved"] = float(np.abs(LP[:, :, 0].mean(1) - LG[:, :, 0].mean(1)).max())
    if not res["checks"]["max_abs_lbar1_from_pooled_minus_saved"] <= 5e-3: raise SystemExit("STOP: lbar_1 rebuilt from pooled differs from the saved one")
    # identity exams: local vs cloud attention and axis 0 (descriptive check)
    F = {}
    for i, (u, k, v) in enumerate(var_rows):
        m1 = att_masses(v["att_vol1"], v["prof"]); m2 = att_masses(v["att_vol2"], v["prof"])
        F[(u, k)] = dict(l1=LG[i, :, 0].mean(), l6=LG[i, :, 5].mean(), p1=LP[i, :, 0].mean(), p1off=LP0[i, :, 0].mean(), ax=act[i] / AX["axis_sd_dev"], X=X[i],
                         ax0abs=(act[i, 0] - mu0) / sd0, pad1=m1[0], padfull1=m1[1], padbound1=m1[2], pad2=m2[0], src=v["src"], att1=v["att_vol1"])
    par = []
    for r in recs:
        if not r.get("gate_G1"): continue
        u = r["series_uid"]
        for k, sub in (("main_sp", "main"), ("zfix_sp", "zfix")):
            if (u, k) in F and F[(u, k)]["src"] == "local":
                c = np.load(cloud_dev / sub / f"{u}.npz"); par.append(float(np.abs(att_w(c["att_vol1"]) - att_w(F[(u, k)]["att1"])).max()))
    res["checks"]["identity_max_abs_att_vol1_weight_local_minus_cloud"] = max(par) if par else None
    long = []
    for arm, cmps in (("A", CMP_A), ("B", CMP_B)):
        for name, kv, kr in cmps:
            for e in Ex[Ex.arm == arm].itertuples():
                fv, fr = F.get((e.series_uid, kv)), F.get((e.series_uid, kr))
                if fv is None or fr is None: continue
                d_ax = fv["ax"] - fr["ax"]; bl = ax0_blocks(AX, fv["X"] - fr["X"]); dl6 = fv["l6"] - fr["l6"]
                long.append(dict(series_uid=e.series_uid, arm=arm, maker=e.maker, order=e.order, T_main=e.T_main, thickness=e.thickness, n_pad_f15=e.n_pad_f15, cmp=name, variant=kv, reference=kr,
                                 d_l1=fv["l1"] - fr["l1"], d_l6=dl6, big6=float(abs(dl6) >= 0.25 * SD6), d_ax0=d_ax[0], **{f"d_ax0_{b}": x for b, x in bl.items()},
                                 A0=(fv["p1"] - fr["p1"]) - (fv["p1off"] - fr["p1off"]), d_l1_off=fv["p1off"] - fr["p1off"],
                                 pad1_var=fv["pad1"], pad1_ref=fr["pad1"], d_pad1=fv["pad1"] - fr["pad1"], pad2_var=fv["pad2"], pad2_ref=fr["pad2"], d_pad2=fv["pad2"] - fr["pad2"],
                                 padfull1_var=fv["padfull1"], padfull1_ref=fr["padfull1"], padbound1_var=fv["padbound1"], ax0_var_abs=fv["ax0abs"], ax0_ref_abs=fr["ax0abs"],
                                 src_var=fv["src"], src_ref=fr["src"], **{f"d_ax{j}": d_ax[j] for j in range(1, AX["k"])}))
    Lg = pd.DataFrame(long)
    split_err = float((Lg[[f"d_ax0_{b}" for b in BLOCKS]].sum(1) - Lg.d_ax0).abs().max()) if len(Lg) else None
    res["checks"]["max_abs_axis0_block_split_minus_total"] = split_err
    if split_err is not None and not split_err <= 1e-6: raise SystemExit("STOP: the three-block split of axis 0 does not add up")
    tag = "x11_code_check" if a.code_check else "x11"
    Lg.drop(columns=[]).to_csv(OUT / f"{tag}_per_exam.csv", index=False, lineterminator="\n"); Ex.to_csv(OUT / f"{tag}_exams.csv", index=False, lineterminator="\n")

    # ---- helpers on the long table
    def col(arm, name, meas, keep=None):
        sub = Lg[(Lg.arm == arm) & (Lg.cmp == name)]
        if keep is not None: sub = sub[keep(sub)]
        return sub.set_index("series_uid")[meas]

    def weights_for(arm, name): return None if arm == "B" else (W05w if name in DECIM else WA)

    def draws_for(arm, idx_uids, weighted, name=""):
        """Draws over the exams idx_uids; arm A weighted: stratified, makers with >= MIN_STRATUM exams only; arm B: stratified by maker."""
        mk = Ex.set_index("series_uid").loc[list(idx_uids), "maker"].to_numpy(); rows = np.arange(len(idx_uids))
        if arm == "A" and not weighted: return Draws(rows), mk
        keep = np.ones(len(rows), bool)
        if arm == "A":
            vc = pd.Series(mk).value_counts(); keep = np.isin(mk, [g for g, n in vc.items() if n >= MIN_STRATUM])
        return Draws(rows[keep], mk[keep]), mk
    W05w = {k: float(v) for k, v in W05.items()}

    def mean_of(arm, name, meas, keep=None, weighted=False):
        s = col(arm, name, meas, keep).dropna()
        if len(s) == 0: return None
        dr, _ = draws_for(arm, s.index, weighted, name); v = s.to_numpy(float)
        e, d = dr.mean(v, weights_for(arm, name) if (weighted and arm == "A") else None); out = summ(e, d); out["n"] = int(len(dr.rows)); return out

    def ratio(arm, num, den, meas, weighted, keep=None, one_minus=False, boundary=None):
        a_, b_ = col(arm, num, meas, keep), col(arm, den, meas, keep); j = a_.dropna().index.intersection(b_.dropna().index)
        if len(j) == 0: return None
        dr, _ = draws_for(arm, j, weighted, num); w = weights_for(arm, num if num in DECIM else den) if (weighted and arm == "A") else None
        en, dn = dr.mean(a_.loc[j].to_numpy(float), w); ed, dd = dr.mean(b_.loc[j].to_numpy(float), w)
        with np.errstate(divide="ignore", invalid="ignore"):
            rr = dn / np.where(np.abs(dd) > 1e-12, dd, np.nan); est = en / ed if abs(ed) > 1e-12 else np.nan
        if one_minus: rr, est = 1 - rr, 1 - est
        out = summ(est, rr); dsum = summ(ed, dd); out.update(n=int(len(dr.rows)), denominator=dsum, denominator_interval_excludes_0=None if dsum["lo"] is None else not (dsum["lo"] <= 0 <= dsum["hi"]))
        if boundary is not None: out["interval_vs_boundary"] = {str(b): side(out, b) for b in (boundary if isinstance(boundary, (list, tuple)) else [boundary])}
        return out

    # ---- estimates per comparison and measure
    est = {}
    for arm, cmps in (("A", CMP_A), ("B", CMP_B)):
        est[arm] = {}
        for name, _, _ in cmps:
            if not ((Lg.arm == arm) & (Lg.cmp == name)).any(): continue
            blk = {}
            for ms in MEAS:
                b = dict(pooled=mean_of(arm, name, ms))
                if arm == "A": b["dev_weighted"] = mean_of(arm, name, ms, weighted=True)
                b["by_maker"] = {g: mean_of(arm, name, ms, keep=lambda s, g=g: s.maker == g) for g in sorted(Lg[(Lg.arm == arm) & (Lg.cmp == name)].maker.unique())}
                blk[ms] = b
            sub = Lg[(Lg.arm == arm) & (Lg.cmp == name)]
            blk["other_axes_mean_shift_dev_sd"] = {f"axis{j}": float(sub[f"d_ax{j}"].mean()) for j in range(1, AX["k"])}
            blk["n_exams_by_maker"] = sub.maker.value_counts().to_dict()
            est[arm][name] = blk
    res["estimates"] = est

    def pe(arm, name, meas, kind="pooled"):
        s = est.get(arm, {}).get(name, {}).get(meas, {}).get(kind); return None if not s else s.get("est")

    # ---- criteria
    C = {}; wA = True
    k_ax, k_l1 = ratio("A", "zfix_air_vs_main_air", "zfix", "d_ax0", wA, boundary=0.5), ratio("A", "zfix_air_vs_main_air", "zfix", "d_l1", wA, boundary=0.5)
    ok1 = None if k_ax is None or k_l1 is None or k_ax["est"] is None or k_l1["est"] is None else (k_ax["est"] >= 0.5 and k_l1["est"] >= 0.5)
    C["A1"] = dict(kept_share_axis0=k_ax, kept_share_lbar1=k_l1, kept_share_A0=ratio("A", "zfix_air_vs_main_air", "zfix", "A0", wA),
                   pooled_unweighted=dict(axis0=ratio("A", "zfix_air_vs_main_air", "zfix", "d_ax0", False), lbar1=ratio("A", "zfix_air_vs_main_air", "zfix", "d_l1", False)),
                   plan_60_exams=dict(axis0=ratio("A", "zfix_air_vs_main_air", "zfix", "d_ax0", wA, keep=lambda s: s.order < 60)),
                   verdict=None if ok1 is None else ("padding value is not a primary driver (air keeps >= 50%, same sign)" if ok1 else "the padding value is a primary driver"))
    s1, s2 = ratio("A", "padmatch", "zfix", "d_ax0", wA, boundary=[0.7, 0.25]), ratio("A", "zfix_vs_padmatch", "zfix", "d_ax0", wA, boundary=[0.5, 0.25])
    v2 = None if not (s1 and s2 and s1["est"] is not None and s2["est"] is not None) else \
        ("geometry drives" if s2["est"] >= 0.5 else ("box filling drives" if (s1["est"] >= 0.7 and s2["est"] < 0.25) else "neither rule met (mixed)"))
    C["A2"] = dict(share_box_filling_part=s1, share_geometry_part=s2, share_geometry_part_lbar1=ratio("A", "zfix_vs_padmatch", "zfix", "d_l1", wA),
                   share_geometry_part_A0=ratio("A", "zfix_vs_padmatch", "zfix", "A0", wA),
                   with_air_padding=dict(share_box_filling_part=ratio("A", "padmatch_air_vs_main_air", "zfix_air_vs_main_air", "d_ax0", wA),
                                         share_geometry_part=ratio("A", "zfix_air_vs_padmatch_air", "zfix_air_vs_main_air", "d_ax0", wA)),
                   plan_60_exams=dict(share_geometry_part=ratio("A", "zfix_vs_padmatch", "zfix", "d_ax0", wA, keep=lambda s: s.order < 60)), verdict=v2)
    rm = ratio("A", "zfix_reflect", "zfix", "d_ax0", wA, one_minus=True, boundary=0.7)
    C["A3"] = dict(metric="axis 0 (decided before reading; delta lbar_1 and A0 reported)", share_removed_axis0=rm,
                   share_removed_lbar1=ratio("A", "zfix_reflect", "zfix", "d_l1", wA, one_minus=True), share_removed_A0=ratio("A", "zfix_reflect", "zfix", "A0", wA, one_minus=True),
                   plan_60_exams=dict(share_removed_axis0=ratio("A", "zfix_reflect", "zfix", "d_ax0", wA, one_minus=True, keep=lambda s: s.order < 60)),
                   verdict=None if rm is None or rm["est"] is None else ("the constant slab drives the z-fix shift" if rm["est"] >= 0.7 else "the constant slab does not drive it (reflect removes < 70%)"))
    dec = lambda s: s.series_uid.isin(set(Lg[(Lg.arm == "A") & (Lg.cmp == "decim0")].series_uid))   # noqa: E731
    r4 = ratio("A", "decim0", "zfix", "d_ax0", wA, keep=dec, boundary=[0.75, 1.25])
    sg = mean_of("A", "zfix_vs_decim0", "d_ax0", weighted=True)
    s_abs = Lg[(Lg.arm == "A") & (Lg.cmp == "zfix_vs_decim0")].assign(absd=lambda q: q.d_ax0.abs())
    if len(s_abs):
        dr4, _ = draws_for("A", s_abs.series_uid.to_numpy(), True); e4, d4 = dr4.mean(s_abs.absd.to_numpy(float), W05w); mabs = summ(e4, d4)
    else: mabs = None
    rep = None if r4 is None or r4["est"] is None else (0.75 <= r4["est"] <= 1.25)
    ovl = None if sg is None or sg["lo"] is None or mabs is None or mabs["est"] is None else (-0.5 < sg["lo"] and sg["hi"] < 0.5 and mabs["est"] < 0.5)
    C["A4"] = dict(weights="dev maker counts of exams with |ratio - 0.5| < 0.02; makers with < 5 exams in the subset left out", ratio_decim_over_zfix_axis0=r4,
                   ratio_decim_over_zfix_lbar1=ratio("A", "decim0", "zfix", "d_l1", wA, keep=dec), signed_mean_zfix_minus_decim0_axis0=sg, mean_abs_zfix_minus_decim0_axis0=mabs,
                   phase_noise_floor_decim1_minus_decim0_axis0=mean_of("A", "decim1_vs_decim0", "d_ax0"),
                   by_maker_n=Lg[(Lg.arm == "A") & (Lg.cmp == "decim0")].maker.value_counts().to_dict(),
                   verdict_reproduced=None if rep is None else ("the bug is reproduced with unmodified Sybil" if rep else "not reproduced (outside +-25%)"),
                   verdict_overlap=None if ovl is None else ("slice overlap itself does not matter" if ovl else "not shown that overlap does not matter (interval or mean absolute difference reaches 0.5 dev SD)"))

    def slope(meas, fs):
        W = pd.concat({n: col("B", n, meas) for n in ("f125", "f15", "f20")}, axis=1).dropna()
        if len(W) == 0: return None
        fx = np.array([1.0, 1.25, 1.5, 2.0]); Y = np.c_[np.zeros(len(W)), W[["f125", "f15", "f20"]].to_numpy(float)]
        sel = [i for i, f in enumerate(fx) if f in fs]; fx, Y = fx[sel], Y[:, sel]
        sl = ((fx - fx.mean()) * (Y - Y.mean(1, keepdims=True))).sum(1) / ((fx - fx.mean()) ** 2).sum()
        dr, _ = draws_for("B", W.index, False); e, d = dr.mean(sl); out = summ(e, d); out["n"] = int(len(W)); return out

    def paired_diff(meas, n1, n0):
        a_, b_ = col("B", n1, meas), col("B", n0, meas); j = a_.dropna().index.intersection(b_.dropna().index)
        if len(j) == 0: return None
        dr, _ = draws_for("B", j, False); e, d = dr.mean((a_.loc[j] - b_.loc[j]).to_numpy(float)); return summ(e, d)
    B1 = {}
    for ms, thr in (("d_ax0", 2.0), ("A0", 0.20)):
        s4p, s3p, f125, dlt = slope(ms, (1.0, 1.25, 1.5, 2.0)), slope(ms, (1.25, 1.5, 2.0)), est.get("B", {}).get("f125", {}).get(ms, {}).get("pooled"), paired_diff(ms, "f20", "f125")
        parts = dict(slope_4pt_interval_above_0=None if not s4p or s4p["lo"] is None else s4p["lo"] > 0, slope_3pt_stretched_only_interval_above_0=None if not s3p or s3p["lo"] is None else s3p["lo"] > 0,
                     f125_interval_above_0=None if not f125 or f125["lo"] is None else f125["lo"] > 0, f20_minus_f125_interval_above_0=None if not dlt or dlt["lo"] is None else dlt["lo"] > 0,
                     f20_at_least_threshold=None if pe("B", "f20", ms) is None else pe("B", "f20", ms) >= thr)
        B1[ms] = dict(threshold_at_f20=thr, slope_4pt=s4p, slope_3pt_stretched_only=s3p, f20_minus_f125=dlt, parts=parts)
    allp = {f"{ms}|{k}": v for ms in B1 for k, v in B1[ms]["parts"].items()}
    C["B1"] = dict(**B1, slope_lbar1_4pt=slope("d_l1", (1.0, 1.25, 1.5, 2.0)),
                   verdict=None if any(v is None for v in allp.values()) else ("met" if all(allp.values()) else "not met: " + ", ".join(k for k, v in allp.items() if not v)))
    bm = {m: dict(axis0=est.get("B", {}).get("f20", {}).get("d_ax0", {}).get("by_maker", {}).get(m), A0=est.get("B", {}).get("f20", {}).get("A0", {}).get("by_maker", {}).get(m),
                  lbar1=est.get("B", {}).get("f20", {}).get("d_l1", {}).get("by_maker", {}).get(m)) for m in ("GE", "PHILIPS", "SIEMENS", "TOSHIBA")}
    pos = {m: (None if not v["axis0"] or not v["A0"] or v["axis0"]["lo"] is None or v["A0"]["lo"] is None else (v["axis0"]["lo"] > 0 and v["A0"]["lo"] > 0)) for m, v in bm.items()}
    C["B2"] = dict(rule="interval > 0 for axis 0 and A0 in each maker", by_maker=bm, positive_by_maker=pos,
                   verdict=None if any(v is None for v in pos.values()) else ("met in all four makers" if all(pos.values()) else "not met in: " + ", ".join(m for m, v in pos.items() if not v)))
    k3 = ratio("B", "f20_padmatch", "f20", "d_ax0", False, boundary=[0.5, 0.25])
    C["B3"] = dict(kept_share_axis0=k3, kept_share_lbar1=ratio("B", "f20_padmatch", "f20", "d_l1", False), kept_share_A0=ratio("B", "f20_padmatch", "f20", "A0", False),
                   verdict=None if k3 is None or k3["est"] is None else ("geometry matters" if k3["est"] >= 0.5 else ("box filling dominates" if k3["est"] < 0.25 else "between 25% and 50% (neither)")))
    f25 = Lg[(Lg.arm == "B") & (Lg.cmp == "f25_vs_f20")]
    if len(f25) and not (Ex.set_index("series_uid").loc[f25.series_uid, "T_f20"] >= 200).all(): raise SystemExit("STOP: an f = 2.5 exam does not fill the box at f = 2.0")
    p4 = est.get("B", {}).get("f25_vs_f20", {}).get("d_ax0", {}).get("pooled")
    C["B4"] = dict(f25_minus_f20_axis0=p4, f25_minus_f20_A0=est.get("B", {}).get("f25_vs_f20", {}).get("A0", {}).get("pooled"),
                   f25_minus_f20_lbar1=est.get("B", {}).get("f25_vs_f20", {}).get("d_l1", {}).get("pooled"), n_by_maker=f25.maker.value_counts().to_dict(),
                   verdict=None if p4 is None or p4["est"] is None else ("saturation (box filling)" if abs(p4["est"]) < 0.3 else ("reversal (drop of >= 0.3 dev SD)" if p4["est"] <= -0.3 else "no plateau (>= +0.3 dev SD)")))
    k5 = ratio("B", "f20_vs_main_air", "f20", "d_ax0", False, boundary=[0.5, 0.25])
    C["B5"] = dict(kept_share_axis0=k5, kept_share_A0=ratio("B", "f20_vs_main_air", "f20", "A0", False), kept_share_lbar1=ratio("B", "f20_vs_main_air", "f20", "d_l1", False),
                   true_geometry_air_minus_sybil_padding=dict(axis0=pe("B", "main_air", "d_ax0"), A0=pe("B", "main_air", "A0"), lbar1=pe("B", "main_air", "d_l1")),
                   verdict=None if k5 is None or k5["est"] is None else ("the stretch effect does not come from the reference's padding value" if k5["est"] >= 0.5 else
                                                                         ("the reference's padding value drives the stretch effect" if k5["est"] < 0.25 else "partly (25% to 50%)")))
    res["criteria"] = C

    # ---- secondary strata (descriptive)
    keyA = ("zfix", "main_air", "zfix_air_vs_main_air", "padmatch", "zfix_vs_padmatch", "zfix_reflect")
    sec = dict(armA_cropped_vs_uncropped={nm: {lab: {ms: mean_of("A", nm, ms, keep=f) for ms in ("d_l1", "d_ax0", "A0")} for lab, f in
                                               (("cropped_T_main_gt_200", lambda s: s.T_main > 200), ("uncropped_T_main_le_200", lambda s: s.T_main <= 200))} for nm in keyA},
               armB_f15_full_vs_padded={nm: {lab: {ms: mean_of("B", nm, ms, keep=f) for ms in ("d_l1", "d_ax0", "A0")} for lab, f in
                                             (("f15_fills_box", lambda s: s.n_pad_f15.fillna(999) <= 2), ("f15_padded", lambda s: s.n_pad_f15.fillna(999) > 2))} for nm in ("f15", "f20")},
               armB_by_thickness={nm: {str(t): {ms: mean_of("B", nm, ms, keep=lambda s, t=t: s.thickness == t) for ms in ("d_ax0", "A0")}
                                       for t in sorted(Ex[Ex.arm == "B"].thickness.unique())} for nm in ("f20", "f20_padmatch")},
               skipped_twin_counts={f"{r_.arm}|{k}": int(sum(1 for q in recs if q["arm"] == r_.arm and k in q.get("skipped", {}))) for r_ in Ex.drop_duplicates("arm").itertuples()
                                    for k in TWIN})
    res["secondary"] = sec

    # ---- axis 0 of all dev main and z-fix runs ("back in distribution")
    rat = dict(zip(Ed.series_uid, Ed.ratio)); dist = {}; edges = np.arange(-4, 10.01, 0.25); ref_q = None
    for var in ("main", "zfix"):
        z = np.load(A / f"arrays_dev_{var}.npz", allow_pickle=True); uid = z["series_uid"]; P = z["pooled"]
        if not set(uid) <= set(Ed.series_uid): raise SystemExit("REFUSED: dev arrays hold an exam outside the dev table")
        a0 = np.empty(len(uid))
        for s in range(0, len(uid), 500): a0[s:s + 500] = (AXF.activation(AX, P[s:s + 500].astype(np.float64))[:, 0] - mu0) / sd0
        r_ = np.array([rat.get(u, np.nan) for u in uid]); cont, strt = (r_ >= 0.95) & (r_ <= 1.05), (r_ > 0) & (r_ <= 0.65)
        groups = {"main": {"contiguous_0p95_1p05": cont, "stretched_0_0p65": strt, "other": ~(cont | strt)}, "zfix": {"stretched_0_0p65": strt, "other": ~strt}}[var]
        for gname, m in groups.items():
            x = a0[m]
            if len(x) == 0: continue
            dist[f"{var}|{gname}"] = dict(n=int(len(x)), mean=float(x.mean()), sd=float(x.std()), quantiles={str(q): float(np.quantile(x, q)) for q in (0.05, 0.25, 0.5, 0.75, 0.95)},
                                         hist_edges=edges.tolist(), hist_counts=np.histogram(x, edges)[0].tolist(), n_below_range=int((x < edges[0]).sum()), n_above_range=int((x > edges[-1]).sum()))
            if var == "main" and gname == "contiguous_0p95_1p05": ref_sorted = np.sort(x); ref_q = (float(np.quantile(x, 0.05)), float(np.quantile(x, 0.95)))
    place = {}; arm_of = dict(zip(Ex.series_uid, Ex.arm)); mk_of = dict(zip(Ex.series_uid, Ex.maker))
    for arm in ("A", "B"):
        for k in sorted({k for (u, k) in F if arm_of[u] == arm}):
            uu = [u for (u, kk) in F if kk == k and arm_of[u] == arm]; x = np.array([F[(u, k)]["ax0abs"] for u in uu]); mk = np.array([mk_of[u] for u in uu])
            wmean = None
            if arm == "A":
                ok = [g for g in WA if (mk == g).sum() >= MIN_STRATUM]; wmean = float(sum(WA[g] * x[mk == g].mean() for g in ok) / sum(WA[g] for g in ok)) if ok else None
            place[f"{arm}|{k}"] = dict(n=int(len(x)), mean_axis0_dev_sd=float(x.mean()), dev_weighted_mean=wmean, median=float(np.median(x)),
                                       percentile_of_mean_in_dev_contiguous_main=float(np.searchsorted(ref_sorted, x.mean()) / len(ref_sorted) * 100) if ref_q else None,
                                       share_of_exams_inside_dev_contiguous_5_to_95=float(((x >= ref_q[0]) & (x <= ref_q[1])).mean()) if ref_q else None)
    res["axis0_distribution"] = dict(note="axis 0 = (activation - dev mean) / dev SD of the frozen shared axis 0; dev arrays assembled from the cloud runs", dev=dist, x11_variants=place)
    res["exam_descriptives"] = dict(arm_A_T_main_le_200=int(((Ex.arm == "A") & (Ex.T_main <= 200)).sum()), arm_A_plan_60=int(((Ex.arm == "A") & (Ex.order < 60)).sum()),
                                    arm_B_thickness_by_maker={m: [[float(k), int(v)] for k, v in Ex[(Ex.arm == "B") & (Ex.maker == m)].thickness.value_counts().sort_index().items()]
                                                              for m in sorted(Ex[Ex.arm == "B"].maker.unique())},
                                    ref_source=Ex.ref_src.value_counts().to_dict(), cpu_seconds_total=float(Ex.seconds.fillna(0).sum()))
    js = json.dumps(clean(res), indent=1, sort_keys=False, allow_nan=False) + "\n"; (OUT / f"{tag}_analysis_dev.json").write_text(js, encoding="utf-8", newline="\n")
    if a.code_check:
        nn = sum(1 for _ in walk_none(res["estimates"]))
        print(f"CODE CHECK written to {OUT}; exams {len(recs)} (missing {len(missing)}); comparisons A {len(est.get('A', {}))}, B {len(est.get('B', {}))}; None estimates {nn}; "
              f"verdicts {[k for k, v in C.items() if any(kk.startswith('verdict') for kk in v)]}; weights equal to plan {res['weights']['equal_to_plan']}; checks {res['checks']}; gates {res['gates']}")
    else: print("written", OUT / f"{tag}_analysis_dev.json", hashlib.sha256(js.encode()).hexdigest())


def walk_none(o):
    if isinstance(o, dict):
        if "est" in o and o["est"] is None: yield o
        for v in o.values(): yield from walk_none(v)


def clean(o):
    if isinstance(o, dict): return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [clean(v) for v in o]
    if isinstance(o, np.ndarray): return [clean(v) for v in o.tolist()]
    if isinstance(o, np.bool_): return bool(o)
    if isinstance(o, np.integer): return int(o)
    if isinstance(o, (np.floating, float)): return None if not np.isfinite(o) else float(o)
    return o


if __name__ == "__main__":
    main()
