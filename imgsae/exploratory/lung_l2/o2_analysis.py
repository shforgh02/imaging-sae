"""Lung L2, plan O2 (docs/O2_PLAN.md; frozen before any O2 scan is scored; amendment A1 of 22 Nov, also before any O2 scan is scored):
the slice-spacing tests on the NLST participants Sybil never used.
O2a + O2b, OUTCOME-FREE: no outcome value is read or written. The radiologists' findings and age, sex, smoking for the frozen form F1 come from
nlst_l0.build run on a copy of the NLST tables whose prsn holds only the columns the build needs (the two outcome columns empty), so no
exam is dropped because of an outcome (amendment A1); the nodule slice and the Lung-RADS category (x9_rules_thresholds.rules) come from the
CT tables. Frozen NLST definitions, nulls, SD reference, shared axes and heads (results/s5/, hash-checked by s6_frozen_analysis.load_frozen);
the form parameters and the X9 cut file are hash-checked here (LF content); nothing is fitted except the H7 regressions.
Rows: tiers U1 and U2 of manifest_unseen.csv (U3 is selected with outcomes and is never used here), merged from the PC copies of the
accounts (rows scored on more than one account must agree: identity rule). Stretched = the job's DICOM ratio, 0 < ratio <= 0.65.
Family (Holm over six, one-sided, alpha 0.05; participant bootstrap 2,000, seed 0; Wald p from the bootstrap SD, as frozen):
  O2-H1 share with |delta lbar_6| >= 0.25 x 0.92957 (> 0.30)   O2-H2 mean delta lbar_1 (< -0.10)   O2-H3 tau90 flag change share (> 0.05)
  O2-H6 axis-0 carries the drop (> +0.20)   O2-H7 follow-up jump b (> +0.10)
  O2-H7x the same b on pairs where NEITHER scan is GE (> 0)   [amendment A1, review R1; before: "not both GE", now a secondary]
Stop rules (amendment A1): an input hash, G2b/G2c, a non-finite array, lbar1 rebuilt from pooled > 5e-3, an account-to-account logit
difference > 1e-5, or an outcome value in the form table -> no family is computed (the output file says why). A non-finite estimate or p,
or fewer than 90% valid bootstrap draws -> "not evaluated" (counts as not rejected). Fewer than 30 stretched exams with a z-fix file ->
O2-H1 to H6 not evaluated; fewer than 30 changed pairs in a population -> O2-H7 / O2-H7x not evaluated. Regressions whose stretch change
takes a single value are not computed (no unique b); such strata report directional means.
Secondary (never confirmed): docs/O2_PLAN.md section 9.8 (reporting order in 9.12).
--dry-dev: the same code on the dev copy (rows of manifest_dev.csv; U1 emulated as IDC ratio <= 0.70, U2 as their year neighbours) as a
code check; its output is a code check, not a result.
usage (venv python): python o2_analysis.py <manifest csv> <out json> --copies <l2 dir>[,<l2 dir>] --root unseen|dev [--dry-dev]
       [--frozen results/s5] [--run-info <l2 run_info dir>] [--tables <nlst tables>] [--split <split pickle>]
"""
import argparse
import glob
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "lung_l0"))
import l2_form  # noqa: E402
import nlst_l0 as L  # noqa: E402
import s2_pilot_checks as P2  # noqa: E402
import s4_common as S  # noqa: E402
import s5_axes_freeze as AXF  # noqa: E402
import s6_frozen_analysis as FA  # noqa: E402
import x9_rules_thresholds as X9  # noqa: E402
from r10_att_harm import bins, near  # noqa: E402
from r9_attention import sm  # noqa: E402

TAU_RAD = 0.03388673708469479   # results/s4/s4_u3_dev.json, Sybil's dev cut matched to the dev radiologists' sensitivity
OUTCOME_COLS = ("candx_days", "canc_free_days", "dt", "fu", "y1", "y2", "y6", "late", "can_scr", "de_stag", "de_type")
FORM_SHA256 = "02ec7c2dda14450ce06a9bc3b127d572ed9c8d6472cf37d550b68ec6283f8034"   # results/l2_form_params.json, hash table of HYPOTHESES_L2.md
X9_DEV = HERE / "results/x9/x9_rules_thresholds_dev.json"
X9_DEV_SHA256 = "3fc2f78180c472cdee22cffa5303687f84412efab36b5be47e2a9803804cc6ef"  # LF content, committed in 3bde287 (plan X9 dev check)
MIN_CHANGED = 30
BUILD_TABLES = ("ctab_idc", "ctabc", "screen")   # the CT tables nlst_l0.build reads besides prsn
PRSN_NEED = ["pid", "age", "gender", "cigsmok"] + [f"{v}{t}" for v in ("scr_days", "scr_res", "scr_iso") for t in range(3)]


def sha(p):
    """SHA-256 of the LF content (the hash tables give committed content with LF line ends; a Windows checkout may hold CRLF)."""
    return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def finite(x): return bool(np.all(np.isfinite(np.asarray(x, dtype=np.float64))))


def ols_safe(y, x, f):
    """the frozen H7 OLS b, or None when the stretch change takes a single value (b not identified; review of A1)."""
    return None if len(np.unique(x)) < 2 else FA.ols_b(y, x, f)


def sboot(fn, pid, min_frac=0.9):
    """FA.boot_stat with guards: None (not evaluated) if the point estimate is undefined, the sample is small, or < 90% of draws are valid."""
    pid = np.asarray(pid)
    if len(pid) < 10: return dict(est=None, lo=None, hi=None, sd=None, n_draws=0, note="fewer than 10 rows")
    est = fn(np.arange(len(pid)))
    if est is None or not np.isfinite(est): return dict(est=None, lo=None, hi=None, sd=None, n_draws=0, note="estimate not defined")
    bt = S.Boot(pid); d = [v for v in (fn(t) for t in bt.takes()) if v is not None and np.isfinite(v)]
    if len(d) < min_frac * bt.n: return dict(est=float(est), lo=None, hi=None, sd=None, n_draws=len(d), note="fewer than 90% valid draws: not evaluated")
    lo, hi = np.percentile(d, [2.5, 97.5]); return dict(est=float(est), lo=float(lo), hi=float(hi), sd=float(np.std(d, ddof=1)), n_draws=len(d))


def load_files(copies, root, variant):
    """first copy of every file, plus every duplicate across copies for the identity rule."""
    out, dup = {}, {}
    for c in copies:
        for j in sorted(glob.glob(str(Path(c) / root / variant / "*.json"))):
            u = Path(j).stem; npz = j[:-5] + ".npz"
            if not Path(npz).exists(): continue
            if u not in out: out[u] = (json.load(open(j)), npz)
            elif Path(npz).resolve() != Path(out[u][1]).resolve(): dup.setdefault(u, []).append(npz)
    return out, dup


def identity(files, dup):
    """largest logit difference between copies of the same series (S6 rule: arrays equal across accounts); non-finite -> inf."""
    worst = 0.0
    for u, others in dup.items():
        a = np.load(files[u][1])["logit"].astype(np.float64)
        for o in others:
            b = np.load(o)["logit"].astype(np.float64)
            worst = max(worst, float(np.abs(b - a).max()) if finite(a) and finite(b) else float("inf"))
    return dict(series_on_more_than_one_account=len(dup), max_abs_logit_difference=worst)


def arr(npz, key): return np.load(npz)[key]


def manifest_rows(man_p, dry):
    M = pd.read_csv(man_p, dtype={"pid": str}, low_memory=False); M = M[M.variant == "main"]
    if not dry: return M[M.tier.isin(["U1", "U2"])].copy()
    M = M[M.tier.isin(["D1", "D2", "D3"])].copy()   # dev: main rows; U1/U2 emulated from the IDC ratio as o2_manifest.py does
    k1 = set(zip(M.pid[M.ratio_idc <= 0.70], M.study_yr[M.ratio_idc <= 0.70])); nb = {(p, y + d) for p, y in k1 for d in (-1, 1)}
    M["tier"] = ["U1" if (p, y) in k1 else ("U2" if (p, y) in nb else "-") for p, y in zip(M.pid, M.study_yr)]
    return M[M.tier.isin(["U1", "U2"])].copy()


def form_table(tables, split):
    """nlst_l0.build on a copy of the tables: prsn holds only the columns the build needs, with the two outcome columns empty; only the CT
    tables the build reads are linked. No outcome value is read and no exam is dropped because of an outcome (amendment A1)."""
    T = Path(tables); tmp = Path(tempfile.mkdtemp(prefix="o2_noout_", dir=str(T.parent)))
    try:
        for p in T.glob("*.csv"):
            if "prsn" in p.name:
                P = pd.read_csv(p, usecols=PRSN_NEED, low_memory=False); P["candx_days"] = np.nan; P["canc_free_days"] = np.nan
                P.to_csv(tmp / p.name, index=False)
            elif any(k in p.name for k in BUILD_TABLES):
                try: os.link(p, tmp / p.name)
                except OSError: shutil.copy2(p, tmp / p.name)
        b = L.build(str(tmp), split)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    X = b["X"]
    present = [c for c in OUTCOME_COLS if c in X.columns]
    if X[present].notna().any().any(): raise ValueError("an outcome value reached the form table")
    X = X.drop(columns=present); X["pid"] = X.pid.astype(str); X["study_yr"] = X.study_yr.astype(int)
    P = json.loads((HERE / "results/l2_form_params.json").read_text()); X["F1"] = l2_form.predict_logit(P["F1"], X)
    return X


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("manifest"); ap.add_argument("out"); ap.add_argument("--copies", required=True); ap.add_argument("--root", default="unseen")
    ap.add_argument("--dry-dev", action="store_true"); ap.add_argument("--frozen", default=str(HERE / "results/s5"))
    ap.add_argument("--run-info", default=r"D:\Shayan\imgsae_data\lung_l2_vol\l2\run_info"); ap.add_argument("--tables", default=r"D:\Shayan\imgsae_data\nlst_public\tables")
    ap.add_argument("--split", default=r"D:\Shayan\imgsae_data\nlst_public\Shetty_et_al(Google)_data_splits.p"); a = ap.parse_args()
    FZ, RI, copies = Path(a.frozen), Path(a.run_info), a.copies.split(",")
    T, arms, fams, lab_of, FI, COMB, AX = FA.load_frozen(FZ, RI); th = T["thresholds"]; HY = {h["id"]: h for h in T["hypotheses"]}; tau = th["tau90_s1"]
    out_p = Path(a.out); out_p.parent.mkdir(parents=True, exist_ok=True)

    def write(res): out_p.write_bytes((json.dumps(res, indent=1, default=float) + "\n").encode("utf-8"))

    def stop(res, why): res["STOPPED"] = why; write(res); raise SystemExit(f"STOPPED: {why}")
    res = dict(label=("DRY CHECK on dev (code check of amendment A1; not a result)" if a.dry_dev else "O2a + O2b (plan docs/O2_PLAN.md with amendment A1, frozen before scoring); outcome-free"))
    res["input_hashes"] = dict(l2_form_params_json=sha(HERE / "results/l2_form_params.json"), x9_rules_thresholds_dev_json=sha(X9_DEV))
    if res["input_hashes"]["l2_form_params_json"] != FORM_SHA256: stop(res, "results/l2_form_params.json does not match the frozen hash")
    if res["input_hashes"]["x9_rules_thresholds_dev_json"] != X9_DEV_SHA256: stop(res, "results/x9/x9_rules_thresholds_dev.json does not match its committed hash")
    heads = S.C.load_heads(RI / "heads.npz"); fc = AXF.load_fc(RI / "heads.npz"); cal = json.load(open(RI / "sybil_ensemble_simple_calibrator.json")); hchk = P2.load_heads(RI / "heads.npz")
    Mn = manifest_rows(a.manifest, a.dry_dev); tier_of = dict(zip(Mn.series_uid, Mn.tier))
    (Fm, dm), (Fz, dz) = load_files(copies, a.root, "main"), load_files(copies, a.root, "zfix")
    Fm = {u: v for u, v in Fm.items() if u in tier_of}; Fz = {u: v for u, v in Fz.items() if u in Fm}
    res["files"] = dict(list_rows=int(len(Mn)), list_U1=int((Mn.tier == "U1").sum()), list_U2=int((Mn.tier == "U2").sum()), main=len(Fm), zfix=len(Fz),
                        errors=len({Path(p).stem for c in copies for p in glob.glob(str(Path(c) / a.root / "errors" / "*.json"))} & set(tier_of)))
    if not Fm: stop(res, "no scored main file")
    # ---- identity across accounts (S6 rule), finiteness and integrity (G2b / G2c, as x5_lidc.py) on every file used
    res["identity_across_accounts"] = dict(main=identity(Fm, {u: v for u, v in dm.items() if u in Fm}), zfix=identity(Fz, {u: v for u, v in dz.items() if u in Fz}))
    if not max(v["max_abs_logit_difference"] for v in res["identity_across_accounts"].values()) <= 1e-5: stop(res, "identity across accounts failed (> 1e-5 or non-finite)")
    nb = nc = nf = 0
    for rec, npz in list(Fm.values()) + list(Fz.values()):
        z = np.load(npz)
        if not all(finite(z[k]) for k in ("logit", "pooled", "h", "pre", "att_vol1") if k in z.files) or not finite(rec["calib"]): nf += 1; continue
        x1, x2, x3, _ = P2.recompute(z, hchk); mp = (1 / (1 + np.exp(-z["logit"].astype(np.float64)))).mean(0)
        nb += not (x1 == 0.0 and x2 <= 1e-3 and x3 <= 1e-4); nc += not float(np.abs(np.array(P2.calibrate(cal, mp)) - np.array(rec["calib"])).max()) <= 1e-4
    res["G2b_G2c"] = dict(n_files=len(Fm) + len(Fz), non_finite=nf, G2b_fail=nb, G2c_fail=nc, pass_=nb == 0 and nc == 0 and nf == 0)
    if not res["G2b_G2c"]["pass_"]: stop(res, "G2b/G2c failed or a non-finite array")
    # ---- exam table from the job's records (no outcome)
    rows = []
    for u, (rec, npz) in Fm.items():
        g = rec["geo"]; ms = rec.get("measures", {}); mdl = rec["tags"].get("ManufacturerModelName")
        rows.append(dict(series_uid=u, pid=str(rec["pid"]), study_yr=int(rec["study_yr"]), tier=tier_of[u], ratio=g.get("ratio"), thickness=g.get("thickness"), true_spacing=g.get("true_spacing"),
                         n_images=g.get("n_images"), resT=(g.get("resampled_shape_main") or [None] * 4)[3], maker=str(rec["tags"].get("Manufacturer")), model=(None if mdl in (None, "") else str(mdl)),
                         s1=rec["calib"][0], s6=rec["calib"][5], zfix=u in Fz, lung_cut_z=bool(ms.get("lung_cut_z"))))
    E = pd.DataFrame(rows); E["ratio"] = pd.to_numeric(E.ratio, errors="coerce"); E["ge"] = E.maker.str.upper().str.contains("GE").astype(int)
    E["st"] = ((E.ratio > 0) & (E.ratio <= th["zfix_ratio_max"])).astype(int); E["st_incl0"] = (E.ratio <= th["zfix_ratio_max"]).astype(int)
    Xm = np.stack([arr(Fm[u][1], "pooled").astype(np.float64) for u in E.series_uid]); lg = np.stack([arr(Fm[u][1], "logit").astype(np.float64) for u in E.series_uid])
    E["l1"] = lg[:, :, 0].mean(1); LP = FA.logits_pooled(Xm, fc, heads); LP0 = FA.logits_pooled(Xm, fc, heads, AX, [0]); E["l1_off"] = LP0[:, :, 0].mean(1)
    act = AXF.activation(AX, Xm); E["ax0"] = act[:, 0] / float(AX["axis_sd_dev"][0])
    chk = float(np.abs(LP[:, :, 0].mean(1) - E.l1.to_numpy()).max()); res["check_max_abs_lbar1_from_pooled_minus_saved"] = chk
    if not (np.isfinite(chk) and chk <= 5e-3): stop(res, "lbar1 rebuilt from pooled differs by > 5e-3 (or is not finite)")
    V = AXF.variates(AX, Xm); Zs = (V - V.mean(0)) / np.maximum(V.std(0), 1e-12); Cc = np.einsum("nia,nja->ija", Zs, Zs) / len(V); iu = np.triu_indices(5, 1)
    sec = dict(axes_member_agreement_main=np.round(Cc[iu].mean(0), 4).tolist(),
               reporting_rule=("headline descriptive alarm cuts: tau90 and x9_OP_L3; key H7 secondary: same_scanner_model; every other cut and stratum "
                               "is reported in full tables (docs/O2_PLAN.md 9.12); x9_OP_L4 equals tau_rad; never 'confirmed'"))
    res["geometry"] = dict(main=int(len(E)), stretched_ratio_gt0=int(E.st.sum()), ratio_zero=int((E.ratio == 0).sum()), ratio_missing=int(E.ratio.isna().sum()),
                           stretched_by_tier={t: int(E.st[E.tier == t].sum()) for t in ("U1", "U2")}, zfix_files=int(E.zfix.sum()),
                           stretched_without_zfix=int((E.st == 1).sum() - (E.st.astype(bool) & E.zfix).sum()))
    # ---- outcome-free form table (F1, largest nodule) and Lung-RADS category (X9 corrected rules)
    try: XF = form_table(a.tables, a.split)
    except ValueError as e: stop(res, str(e))
    n0, uids0 = len(E), E.series_uid.to_numpy().copy()
    E = E.merge(XF[["pid", "study_yr", "F1", "max_dia"]], on=["pid", "study_yr"], how="left")
    R9, _ = X9.rules(a.tables); R9["pid"] = R9.pid.astype(int).astype(str); R9["study_yr"] = R9.study_yr.astype(int)
    E = E.merge(R9[["pid", "study_yr", "lr_up"]], on=["pid", "study_yr"], how="left"); E["lr_up"] = E.lr_up.fillna(1).astype(int)
    if len(E) != n0 or not (E.series_uid.to_numpy() == uids0).all(): stop(res, "a merge changed the exam rows (row order of the arrays would break)")
    res["F1_missing"] = int(E.F1.isna().sum())
    res["F1_note"] = "exams without F1 are exams the form cannot score (no adequate screen result); no outcome is used"
    st = {}
    # ---- O2a: H1, H2, H3, H6 on stretched exams (ratio > 0) with a z-fix file
    jm = ((E.st == 1) & E.zfix).to_numpy(); J = E[jm].reset_index(drop=True); pid = J.pid.to_numpy(); mi = np.flatnonzero(jm)
    cnt = dict(exams=int(len(J)), participants=int(len(np.unique(pid)))); E["l1fix"] = E.l1.copy()
    qsd = th["quarter_sd"] * th["sd_ref_lbar6_all_dev_main"]
    if len(J) < MIN_CHANGED:
        for k in ("O2-H1", "O2-H2", "O2-H3", "O2-H6"): st[k] = dict(est=None, sd=None, lo=None, hi=None, counts=cnt, note="fewer than 30 stretched exams with a z-fix file: not evaluated")
        sec["O2a_secondaries"] = "not computed: fewer than 30 stretched exams with a z-fix file"
    else:
        lgz = np.stack([arr(Fz[u][1], "logit").astype(np.float64) for u in J.series_uid]); Xz = np.stack([arr(Fz[u][1], "pooled").astype(np.float64) for u in J.series_uid]); lgm = lg[mi]
        d1, d6 = lgz[:, :, 0].mean(1) - lgm[:, :, 0].mean(1), lgz[:, :, 5].mean(1) - lgm[:, :, 5].mean(1)
        s1z = np.array([Fz[u][0]["calib"][0] for u in J.series_uid]); s1m = J.s1.to_numpy(); s6z = np.array([Fz[u][0]["calib"][5] for u in J.series_uid]); s6m = J.s6.to_numpy()
        Lz, Lz0 = FA.logits_pooled(Xz, fc, heads), FA.logits_pooled(Xz, fc, heads, AX, [0]); dp1 = Lz[:, :, 0].mean(1) - LP[mi][:, :, 0].mean(1); doff = Lz0[:, :, 0].mean(1) - LP0[mi][:, :, 0].mean(1); h6 = doff - dp1
        E.loc[jm, "l1fix"] = lgz[:, :, 0].mean(1)        # review A3: stretched exams with their z-fix score
        fa, fb = s1m >= tau, s1z >= tau
        st["O2-H1"] = dict(sboot(lambda t: float((np.abs(d6[t]) >= qsd).mean()), pid), counts=cnt)
        st["O2-H2"] = dict(sboot(lambda t: float(d1[t].mean()), pid), counts=cnt)
        st["O2-H3"] = dict(sboot(lambda t: float((fa[t] != fb[t]).mean()), pid), counts=cnt)
        st["O2-H6"] = dict(sboot(lambda t: float(h6[t].mean()), pid), counts=cnt, mean_delta_lbar1_from_pooled=float(dp1.mean()), mean_delta_lbar1_axis0_off=float(doff.mean()))
        # ---- secondary: alarm changes at the frozen cuts and at the X9 cuts set on cancer-free dev exams (outcome-free here)
        x9 = json.loads(X9_DEV.read_text())["thresholds"]

        def cutf(s, c): return (s > c["threshold"]) if c["flag_rule"] == ">" else (s >= c["threshold"])
        cuts = {"tau90": dict(threshold=tau, flag_rule=">="), "tau_rad": dict(threshold=TAU_RAD, flag_rule=">="),
                "x9_OP_L3_lung_rads3_level": x9["E1"]["table"]["sybil@OP_L3"]["cut"], "x9_OP_L4_lung_rads4A_level": x9["E1"]["table"]["sybil@OP_L4"]["cut"],
                "x9_OP_R_radiologists_level": x9["E1"]["table"]["sybil@OP_R"]["cut"]}
        al = {}; bt = S.Boot(pid)
        for nm, c in cuts.items():
            xa, xb = cutf(s1m, c), cutf(s1z, c)
            al[nm] = dict(FA.flags(xa, xb), threshold=c["threshold"], flag_rule=c["flag_rule"], discordant_share=bt.ci(lambda t: float((xa[t] != xb[t]).mean())),
                          net_change_per_1000=bt.ci(lambda t: float(((~xa[t] & xb[t]).sum() - (xa[t] & ~xb[t]).sum()) / len(t) * 1000)))
        c6 = x9["E4"]["table"]["sybil@OP_90"]["cut"]; b0 = (J.study_yr == 0).to_numpy()
        if b0.sum() >= 10:
            xa, xb = cutf(s6m[b0], c6), cutf(s6z[b0], c6); bt0 = S.Boot(pid[b0])
            al["x9_6year_OP_90_baseline"] = dict(FA.flags(xa, xb), threshold=c6["threshold"], flag_rule=c6["flag_rule"], exams=int(b0.sum()),
                                                  discordant_share=bt0.ci(lambda t: float((xa[t] != xb[t]).mean())),
                                                  net_change_per_1000=bt0.ci(lambda t: float(((~xa[t] & xb[t]).sum() - (xa[t] & ~xb[t]).sum()) / len(t) * 1000)))
        sec["alarm_changes"] = al
        # ---- secondary: alarm changes by Lung-RADS category (1-2, 3, 4A, 4B-4X) and largest-nodule size (none, 4-<8, >=8 mm) at tau90 and x9_OP_L3
        lrg = np.select([J.lr_up.to_numpy() <= 2, J.lr_up.to_numpy() == 3, J.lr_up.to_numpy() == 4], ["1-2", "3", "4A"], "4B-4X")
        md = J.max_dia.fillna(0).to_numpy(); szg = np.where(md == 0, "none", np.where(md < 8, "4-<8 mm", ">=8 mm"))
        by = {}
        for gname, g in (("lung_rads", lrg), ("nodule_size", szg)):
            by[gname] = {}
            for k in sorted(set(g)):
                m_ = g == k; o = dict(n=int(m_.sum()), mean_d1=float(d1[m_].mean()))
                for nm in ("tau90", "x9_OP_L3_lung_rads3_level"):
                    xa, xb = cutf(s1m[m_], cuts[nm]), cutf(s1z[m_], cuts[nm]); o[nm] = dict(FA.flags(xa, xb), net_change_per_1000=float(((~xa & xb).sum() - (xa & ~xb).sum()) / max(1, m_.sum()) * 1000))
                by[gname][k] = o
        sec["alarm_changes_by_group"] = by
        dax = (AXF.activation(AX, Xz) - act[mi]) / AX["axis_sd_dev"]; sec["C1_axis0_shift_dev_sd"] = sboot(lambda t: float(dax[t, 0].mean()), pid)
        # ---- secondary: by maker, by stretch class, by maker x class, with intervals (reviews A1, Neon 8.4)
        mk = J.maker.to_numpy(); cls = np.where(J.thickness / J.true_spacing >= 1.9, "2.0", "1.6"); fl = (fa != fb)

        def grp(m_):
            p_ = pid[m_]; v1, vh, va, vf, vq = d1[m_], h6[m_], dax[m_, 0], fl[m_], (np.abs(d6[m_]) >= qsd)
            return dict(n=int(m_.sum()), mean_d1=sboot(lambda t: float(v1[t].mean()), p_), h6=sboot(lambda t: float(vh[t].mean()), p_),
                        axis0_shift_dev_sd=sboot(lambda t: float(va[t].mean()), p_), flag_change_tau90=sboot(lambda t: float(vf[t].mean()), p_),
                        share_quarter_sd=sboot(lambda t: float(vq[t].mean()), p_))
        sec["by_maker"] = {k: grp(mk == k) for k in sorted(set(mk))}
        sec["by_stretch_class"] = {k: grp(cls == k) for k in ("1.6", "2.0") if (cls == k).any()}
        sec["by_maker_and_class"] = {f"{m} {c}": dict(n=int(((mk == m) & (cls == c)).sum()), mean_d1=float(d1[(mk == m) & (cls == c)].mean())) for m in sorted(set(mk)) for c in ("1.6", "2.0") if ((mk == m) & (cls == c)).any()}
        crop = (J.resT.astype(float) > 200).to_numpy(); zT = np.round(J.n_images.astype(float) * J.true_spacing.astype(float) / 2.5).to_numpy(); pad = zT < 200
        sec["crop_pad"] = {nm: dict(n=int(m_.sum()), mean_d1=(S.Boot(pid[m_]).ci(lambda t, v=d1[m_]: float(v[t].mean())) if m_.sum() >= 10 else None))
                           for nm, m_ in (("main_cropped", crop), ("main_not_cropped", ~crop), ("zfix_padded", pad), ("zfix_not_padded", ~pad))}
        # ---- attention under the z-fix (outcome-free r10 logic) with the shuffled-position geometry control (Neon; dev check of 17 Nov)
        N = pd.read_csv(Path(a.tables) / "nlst_780_ctab_idc_20210527.csv", dtype={"pid": str}); N = N[(N.sct_ab_desc == 51) & N.sct_slice_num.notna() & (N.sct_long_dia >= 4)]
        N = N.sort_values("sct_long_dia", ascending=False).drop_duplicates(["pid", "study_yr"])
        Q = J.assign(row=np.arange(len(J))).merge(N[["pid", "study_yr", "sct_slice_num", "sct_long_dia"]], on=["pid", "study_yr"]); Q = Q[Q.sct_slice_num <= Q.n_images].reset_index(drop=True)
        att = dict(n=int(len(Q)), note="fewer than 10 exams with a nodule slice: not computed")
        if len(Q) >= 10:
            a1 = sm(np.stack([arr(Fm[u][1], "att_vol1").astype(np.float64) for u in Q.series_uid])).mean(1); a2 = sm(np.stack([arr(Fz[u][1], "att_vol1").astype(np.float64) for u in Q.series_uid])).mean(1)
            zq = np.round(Q.n_images.astype(float) * Q.true_spacing.astype(float) / 2.5).to_numpy(); sl = Q.sct_slice_num.to_numpy(float); nim = Q.n_images.to_numpy(float)
            th1, rT = Q.thickness.astype(float).to_numpy(), Q.resT.astype(float).to_numpy(); sp_ = Q.true_spacing.astype(float).to_numpy()
            ok1, k1 = bins(sl, th1, rT); ok2, k2 = bins(sl, sp_, zq)
            v1, v2 = near(a1, k1), near(a2, k2); both = ok1 & ok2
            rng = np.random.default_rng(0); sh1, sh2, nsh = np.zeros(len(Q)), np.zeros(len(Q)), np.zeros(len(Q))
            frac = sl / nim
            for _ in range(500):   # shuffled nodule positions (as a fraction of the series) across exams: the attention a nodule-free bin would get
                fs = np.clip(np.round(rng.permutation(frac) * nim), 1, nim)
                o1, q1 = bins(fs, th1, rT); o2, q2 = bins(fs, sp_, zq); okb = o1 & o2
                sh1[okb] += near(a1, q1)[okb]; sh2[okb] += near(a2, q2)[okb]; nsh[okb] += 1
            okn = both & (nsh > 0); e1, e2 = v1 - sh1 / np.maximum(nsh, 1), v2 - sh2 / np.maximum(nsh, 1); dq = (e2 - e1)[okn]; dn_ = (v2 - v1)[okn]; qp = Q.pid.to_numpy()[okn]
            moved = (~ok1) & ok2; mrow = Q.row.to_numpy()[moved]
            att = dict(n=int(okn.sum()), participants=int(len(set(qp))), nodule_outside_box_main=int((~ok1).sum()), nodule_outside_box_zfix=int((~ok2).sum()),
                       share_near_main=(float(v1[okn].mean()) if okn.any() else None), share_near_zfix=(float(v2[okn].mean()) if okn.any() else None),
                       naive_diff_zfix_minus_main=(S.Boot(qp).ci(lambda t: float(dn_[t].mean())) if okn.sum() >= 10 else None),
                       excess_over_shuffled_main=(float(e1[okn].mean()) if okn.any() else None), excess_over_shuffled_zfix=(float(e2[okn].mean()) if okn.any() else None),
                       excess_diff_zfix_minus_main=(S.Boot(qp).ci(lambda t: float(dq[t].mean())) if okn.sum() >= 10 else None),
                       nodule_back_in_box=dict(n=int(moved.sum()), large_ge_8mm=int((moved & (Q.sct_long_dia.to_numpy() >= 8)).sum()),
                                               mean_d1=(float(d1[mrow].mean()) if len(mrow) else None), tau90_flags=(FA.flags(fa[mrow], fb[mrow]) if len(mrow) else None)),
                       note="att_vol1; nodule bins as r10_att_harm.py; the excess over 500 shuffled positions removes the box-size geometry; mechanistic displacement, never patient harm")
        sec["attention_zfix"] = att
    # ---- O2b: H7 on consecutive pairs with both exams scored (U1 and U2)
    c = ["pid", "study_yr", "st", "st_incl0", "l1", "l1_off", "l1fix", "ax0", "F1", "s1", "model", "ge"]
    Pp = E[c].merge(E[c], on="pid", suffixes=("_a", "_b")); Pp = Pp[(Pp.study_yr_b == Pp.study_yr_a + 1) & Pp.F1_a.notna() & Pp.F1_b.notna()].reset_index(drop=True)
    dd = dict(dst=(Pp.st_b - Pp.st_a).to_numpy(float), dst0=(Pp.st_incl0_b - Pp.st_incl0_a).to_numpy(float), dl=(Pp.l1_b - Pp.l1_a).to_numpy(), dl_off=(Pp.l1_off_b - Pp.l1_off_a).to_numpy(),
              dlfix=(Pp.l1fix_b - Pp.l1fix_a).to_numpy(), dax0=(Pp.ax0_b - Pp.ax0_a).to_numpy(), dF=(Pp.F1_b - Pp.F1_a).to_numpy())
    ppid = Pp.pid.to_numpy(); nge = (Pp.ge_a + Pp.ge_b).to_numpy(); flip = ((Pp.s1_a >= tau) != (Pp.s1_b >= tau)).to_numpy()
    fa_p, fb_p = (Pp.s1_a >= tau).to_numpy(), (Pp.s1_b >= tau).to_numpy()
    bfn = lambda key, rows_, dk="dst": (lambda t: ols_safe(dd[key][rows_][t], dd[dk][rows_][t], dd["dF"][rows_][t]))   # noqa: E731

    def pc(r_): return dict(pairs=int(len(r_)), participants=int(len(np.unique(ppid[r_]))), changed=int((dd["dst"][r_] != 0).sum()),
                            stretched_to_not=int((dd["dst"][r_] == -1).sum()), not_to_stretched=int((dd["dst"][r_] == 1).sum()))
    allr = np.arange(len(Pp)); notboth = np.flatnonzero(nge < 2); neither = np.flatnonzero(nge == 0); onege = np.flatnonzero(nge == 1); chg = np.flatnonzero(dd["dst"] != 0)

    def h7(rows_):
        n_ch = int((dd["dst"][rows_] != 0).sum())
        if n_ch < MIN_CHANGED: return dict(est=None, sd=None, lo=None, hi=None, counts=pc(rows_), note=f"fewer than {MIN_CHANGED} changed pairs: not evaluated")
        return dict(sboot(bfn("dl", rows_), ppid[rows_]), counts=pc(rows_))
    st["O2-H7"] = h7(allr); st["O2-H7x"] = h7(neither)

    def directional(r_):
        g = dd["dst"][r_]
        return {nm: dict(n=int((g == v).sum()), mean_dl=float(dd["dl"][r_][g == v].mean()), mean_dl_off=float(dd["dl_off"][r_][g == v].mean()), mean_dax0=float(dd["dax0"][r_][g == v].mean()))
                for nm, v in (("stretched_to_not", -1), ("unchanged", 0), ("not_to_stretched", 1)) if (g == v).any()}

    def stratum(r_):
        r_ = np.asarray(r_, int)
        if (dd["dst"][r_] != 0).sum() < 5: return dict(counts=pc(r_), note="fewer than 5 changed pairs")
        if len(np.unique(dd["dst"][r_])) < 2: return dict(counts=pc(r_), directional_means=directional(r_), note="one value of the stretch change only: b not identified; directional means")
        g = dd["dst"][r_]; up, dn = r_[g == 1], r_[g == -1]
        return dict(counts=pc(r_), b=sboot(bfn("dl", r_), ppid[r_]), b_axis0_off=sboot(bfn("dl_off", r_), ppid[r_]),
                    b_minus_b_axis0_off=sboot(lambda t: (None if bfn("dl", r_)(t) is None else bfn("dl", r_)(t) - bfn("dl_off", r_)(t)), ppid[r_]),
                    axis0_jump_dev_sd=sboot(bfn("dax0", r_), ppid[r_]), directional_means=directional(r_),
                    symmetric_contrast=(float(0.5 * (dd["dl"][up].mean() - dd["dl"][dn].mean())) if len(up) and len(dn) else None))
    f7 = dict(b_ratio0_counted_stretched=sboot(bfn("dl", allr, "dst0"), ppid), b_changed_pairs_only=sboot(bfn("dl", chg), ppid[chg]),
              b_with_zfix_scores_two_sided=(sboot(bfn("dlfix", allr), ppid) if len(J) >= MIN_CHANGED else dict(est=None, lo=None, hi=None, sd=None, n_draws=0, note="fewer than 30 stretched exams with a z-fix file: not computed")),
              strata=dict(all=stratum(allr), both_ge=stratum(np.flatnonzero(nge == 2)), not_both_ge_old_H7x=stratum(notboth), one_ge=stratum(onege), neither_ge=stratum(neither)))
    # one-GE changed pairs split by the maker of the stretched scan; each part keeps all unchanged one-GE pairs (both stretched) for the intercept
    stretched_ge = np.where(Pp.st_a.to_numpy() == 1, Pp.ge_a.to_numpy(), Pp.ge_b.to_numpy()); unch1 = onege[dd["dst"][onege] == 0]; ch1 = onege[dd["dst"][onege] != 0]
    f7["strata"]["one_ge_stretched_scan_GE"] = stratum(np.r_[unch1, ch1[stretched_ge[ch1] == 1]]); f7["strata"]["one_ge_stretched_scan_not_GE"] = stratum(np.r_[unch1, ch1[stretched_ge[ch1] == 0]])
    same = np.flatnonzero((Pp.model_a.notna() & Pp.model_b.notna() & (Pp.model_a == Pp.model_b)).to_numpy())
    f7["strata"]["same_scanner_model"] = stratum(same); f7["strata"]["same_scanner_model_neither_ge"] = stratum(np.intersect1d(same, neither))
    f7["groups"] = {nm: dict(n=int((dd["dst"] == v).sum()), mean_dl=float(dd["dl"][dd["dst"] == v].mean()), mean_dl_off=float(dd["dl_off"][dd["dst"] == v].mean()),
                             flag_flip_tau90=float(flip[dd["dst"] == v].mean()),
                             alarms_b_minus_a_per_1000=float((fb_p[dd["dst"] == v].sum() - fa_p[dd["dst"] == v].sum()) / (dd["dst"] == v).sum() * 1000))
                    for nm, v in (("stretched_to_not", -1), ("unchanged", 0), ("not_to_stretched", 1)) if (dd["dst"] == v).any()}
    f7["note"] = "same_scanner_model is the key secondary: 'on pairs with the same scanner model, b = x [interval]'; alarms_b_minus_a_per_1000 is descriptive (no interval)"
    sec["H7_details"] = f7
    # ---- tests, Holm over the O2 family (not evaluated -> p None -> not rejected; the family size stays 6)
    fam = [("O2-H1", "H1", None), ("O2-H2", "H2", None), ("O2-H3", "H3", None), ("O2-H6", "H6", None), ("O2-H7", "H7", None), ("O2-H7x", "H7", 0.0)]
    ps, out_rows = [], []
    for oid, hid, null_over in fam:
        h = HY[hid]; s = st[oid]; null = h["null"] if null_over is None else null_over
        ok = s.get("est") is not None and s.get("sd") is not None and np.isfinite(s["est"]) and np.isfinite(s["sd"])
        p = FA.wald(s["sd"], s["est"], null, h["direction"]) if ok else None
        if p is not None and not np.isfinite(p): p = None
        ps.append(p)
        out_rows.append(dict(id=oid, frozen_source=hid, direction=h["direction"], null=null, est=(s["est"] if ok else None), ci95=([s.get("lo"), s.get("hi")] if ok else [None, None]),
                             p_one_sided=p, evaluated=p is not None, counts=s["counts"], note=s.get("note"),
                             population=("pairs where neither scan is GE (amendment A1)" if oid == "O2-H7x" else None)))
    for r, x in zip(out_rows, FA.holm(ps, 0.05)): r["null_rejected_holm_over_6"] = bool(x)
    res["hypotheses"] = out_rows; res["n_rejected"] = int(sum(r["null_rejected_holm_over_6"] for r in out_rows)); res["secondary"] = sec
    res["O2-H6_detail"] = {k: v for k, v in st["O2-H6"].items() if k.startswith("mean_delta")}
    write(res)
    print(json.dumps(dict(files=res["files"], G2=res["G2b_G2c"]["pass_"], n=cnt, pairs=st["O2-H7"]["counts"], H7x=st["O2-H7x"]["counts"]), default=float))


if __name__ == "__main__":
    main()
