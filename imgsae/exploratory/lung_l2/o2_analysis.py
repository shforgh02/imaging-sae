"""Lung L2, plan O2 (docs/O2_PLAN.md; frozen before any O2 scan is scored): the slice-spacing tests on the NLST participants Sybil never used.
O2a + O2b, OUTCOME-FREE: no outcome column is read or written (the NLST tables give only the radiologists' findings and age, sex,
smoking for the frozen form F1, and the nodule slice for the attention check). Frozen NLST definitions, nulls, SD reference, shared
axes and heads (results/s5/, hash-checked by s6_frozen_analysis.load_frozen); nothing is fitted except the H7 regressions.
Rows: tiers U1 and U2 of manifest_unseen.csv (U3 is selected with outcomes and is never used here), merged from the PC copies of the
accounts. Stretched = the job's DICOM ratio, 0 < ratio <= 0.65 ("ratio > 0 rule"; review Q8.5).
Family (Holm over six, one-sided, alpha 0.05; participant bootstrap 2,000, seed 0; Wald p from the bootstrap SD, as frozen):
  O2-H1 share with |delta lbar_6| >= 0.25 x 0.92957 (> 0.30)   O2-H2 mean delta lbar_1 (< -0.10)   O2-H3 tau90 flag change share (> 0.05)
  O2-H6 axis-0 carries the drop (> +0.20)   O2-H7 follow-up jump b (> +0.10)   O2-H7x the same b on pairs that are not both GE (> 0)
Secondary (never confirmed): alarm changes at tau90 and tau_rad; by maker and stretch class; C1; member agreement; H7 details;
the z-fix change by crop; attention under the z-fix (outcome-free version of r10_att_harm.py); G2b/G2c integrity.
--dry-dev: the same code on the dev copy (rows of manifest_dev.csv; U1 emulated as IDC ratio <= 0.70, U2 as their year neighbours) as a
check before the freeze; its output is a code check, not a result.
usage (venv python): python o2_analysis.py <manifest csv> <out json> --copies <l2 dir>[,<l2 dir>] --root unseen|dev [--dry-dev]
       [--frozen results/s5] [--run-info <l2 run_info dir>] [--tables <nlst tables>] [--split <split pickle>]
"""
import argparse
import glob
import json
import sys
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
from r10_att_harm import bins, near  # noqa: E402
from r9_attention import sm  # noqa: E402

TAU_RAD = 0.03388673708469479   # results/s4/s4_u3_dev.json, Sybil's dev cut matched to the dev radiologists' sensitivity
OUTCOME_COLS = ("candx_days", "canc_free_days", "dt", "fu", "y1", "y2", "y6", "late", "can_scr", "de_stag", "de_type")


def load_files(copies, root, variant):
    out = {}
    for c in copies:
        for j in sorted(glob.glob(str(Path(c) / root / variant / "*.json"))):
            u = Path(j).stem; npz = j[:-5] + ".npz"
            if u not in out and Path(npz).exists(): out[u] = (json.load(open(j)), npz)
    return out


def arr(npz, key): return np.load(npz)[key]


def manifest_rows(man_p, dry):
    M = pd.read_csv(man_p, dtype={"pid": str}, low_memory=False); M = M[M.variant == "main"]
    if not dry: return M[M.tier.isin(["U1", "U2"])].copy()
    M = M[M.tier.isin(["D1", "D2", "D3"])].copy()   # dev: main rows; U1/U2 emulated from the IDC ratio as o2_manifest.py does
    k1 = set(zip(M.pid[M.ratio_idc <= 0.70], M.study_yr[M.ratio_idc <= 0.70])); nb = {(p, y + d) for p, y in k1 for d in (-1, 1)}
    M["tier"] = ["U1" if (p, y) in k1 else ("U2" if (p, y) in nb else "-") for p, y in zip(M.pid, M.study_yr)]
    return M[M.tier.isin(["U1", "U2"])].copy()


def form_f1(tables, split, keys):
    b = L.build(tables, split); X = b["X"].drop(columns=[c for c in OUTCOME_COLS if c in b["X"].columns]); X["pid"] = X.pid.astype(str)
    P = json.loads((HERE / "results/l2_form_params.json").read_text()); X["F1"] = l2_form.predict_logit(P["F1"], X)
    return dict(zip(zip(X.pid, X.study_yr.astype(int)), X.F1)), b["read"] if "read" in b else None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("manifest"); ap.add_argument("out"); ap.add_argument("--copies", required=True); ap.add_argument("--root", default="unseen")
    ap.add_argument("--dry-dev", action="store_true"); ap.add_argument("--frozen", default=str(HERE / "results/s5"))
    ap.add_argument("--run-info", default=r"D:\Shayan\imgsae_data\lung_l2_vol\l2\run_info"); ap.add_argument("--tables", default=r"D:\Shayan\imgsae_data\nlst_public\tables")
    ap.add_argument("--split", default=r"D:\Shayan\imgsae_data\nlst_public\Shetty_et_al(Google)_data_splits.p"); a = ap.parse_args()
    FZ, RI, copies = Path(a.frozen), Path(a.run_info), a.copies.split(",")
    T, arms, fams, lab_of, FI, COMB, AX = FA.load_frozen(FZ, RI); th = T["thresholds"]; HY = {h["id"]: h for h in T["hypotheses"]}; tau = th["tau90_s1"]
    heads = S.C.load_heads(RI / "heads.npz"); fc = AXF.load_fc(RI / "heads.npz"); cal = json.load(open(RI / "sybil_ensemble_simple_calibrator.json")); hchk = P2.load_heads(RI / "heads.npz")
    Mn = manifest_rows(a.manifest, a.dry_dev); tier_of = dict(zip(Mn.series_uid, Mn.tier))
    Fm, Fz = load_files(copies, a.root, "main"), load_files(copies, a.root, "zfix"); Fm = {u: v for u, v in Fm.items() if u in tier_of}; Fz = {u: v for u, v in Fz.items() if u in Fm}
    res = dict(label=("DRY CHECK on dev (code check before the O2 freeze; not a result)" if a.dry_dev else "O2a + O2b (plan docs/O2_PLAN.md, frozen before scoring); outcome-free"),
               files=dict(list_rows=int(len(Mn)), list_U1=int((Mn.tier == "U1").sum()), list_U2=int((Mn.tier == "U2").sum()), main=len(Fm), zfix=len(Fz),
                          errors=len({Path(p).stem for c in copies for p in glob.glob(str(Path(c) / a.root / "errors" / "*.json"))} & set(tier_of))))
    # ---- integrity (G2b / G2c, as x5_lidc.py) on every file used
    nb = nc = 0
    for rec, npz in list(Fm.values()) + list(Fz.values()):
        z = np.load(npz); x1, x2, x3, _ = P2.recompute(z, hchk); mp = (1 / (1 + np.exp(-z["logit"].astype(np.float64)))).mean(0)
        nb += not (x1 == 0.0 and x2 <= 1e-3 and x3 <= 1e-4); nc += not float(np.abs(np.array(P2.calibrate(cal, mp)) - np.array(rec["calib"])).max()) <= 1e-4
    res["G2b_G2c"] = dict(n_files=len(Fm) + len(Fz), G2b_fail=nb, G2c_fail=nc, pass_=nb == 0 and nc == 0)
    # ---- exam table from the job's records (no outcome)
    rows = []
    for u, (rec, npz) in Fm.items():
        g = rec["geo"]; ms = rec.get("measures", {})
        rows.append(dict(series_uid=u, pid=str(rec["pid"]), study_yr=int(rec["study_yr"]), tier=tier_of[u], ratio=g.get("ratio"), thickness=g.get("thickness"), true_spacing=g.get("true_spacing"),
                         n_images=g.get("n_images"), resT=(g.get("resampled_shape_main") or [None] * 4)[3], maker=str(rec["tags"].get("Manufacturer")), model=str(rec["tags"].get("ManufacturerModelName")),
                         s1=rec["calib"][0], zfix=u in Fz, lung_cut_z=bool(ms.get("lung_cut_z"))))
    E = pd.DataFrame(rows); E["ratio"] = pd.to_numeric(E.ratio, errors="coerce"); E["ge"] = E.maker.str.upper().str.contains("GE").astype(int)
    E["st"] = ((E.ratio > 0) & (E.ratio <= th["zfix_ratio_max"])).astype(int); E["st_incl0"] = (E.ratio <= th["zfix_ratio_max"]).astype(int)
    Xm = np.stack([arr(Fm[u][1], "pooled").astype(np.float64) for u in E.series_uid]); lg = np.stack([arr(Fm[u][1], "logit").astype(np.float64) for u in E.series_uid])
    E["l1"] = lg[:, :, 0].mean(1); LP = FA.logits_pooled(Xm, fc, heads); LP0 = FA.logits_pooled(Xm, fc, heads, AX, [0]); E["l1_off"] = LP0[:, :, 0].mean(1)
    act = AXF.activation(AX, Xm); E["ax0"] = act[:, 0] / float(AX["axis_sd_dev"][0])
    res["check_max_abs_lbar1_from_pooled_minus_saved"] = float(np.abs(LP[:, :, 0].mean(1) - E.l1.to_numpy()).max())
    V = AXF.variates(AX, Xm); Zs = (V - V.mean(0)) / np.maximum(V.std(0), 1e-12); Cc = np.einsum("nia,nja->ija", Zs, Zs) / len(V); iu = np.triu_indices(5, 1)
    sec = dict(axes_member_agreement_main=np.round(Cc[iu].mean(0), 4).tolist())
    res["geometry"] = dict(main=int(len(E)), stretched_ratio_gt0=int(E.st.sum()), ratio_zero=int((E.ratio == 0).sum()), ratio_missing=int(E.ratio.isna().sum()),
                           stretched_by_tier={t: int(E.st[E.tier == t].sum()) for t in ("U1", "U2")}, zfix_files=int(E.zfix.sum()),
                           stretched_without_zfix=int((E.st == 1).sum() - (E.st.astype(bool) & E.zfix).sum()))
    st = {}
    # ---- O2a: H1, H2, H3, H6 on stretched exams (ratio > 0) with a z-fix file
    J = E[(E.st == 1) & E.zfix].reset_index(drop=True); pid = J.pid.to_numpy()
    lgz = np.stack([arr(Fz[u][1], "logit").astype(np.float64) for u in J.series_uid]); Xz = np.stack([arr(Fz[u][1], "pooled").astype(np.float64) for u in J.series_uid])
    mi = E.index[(E.st == 1) & E.zfix].to_numpy(); lgm = lg[mi]
    d1, d6 = lgz[:, :, 0].mean(1) - lgm[:, :, 0].mean(1), lgz[:, :, 5].mean(1) - lgm[:, :, 5].mean(1)
    s1z = np.array([Fz[u][0]["calib"][0] for u in J.series_uid]); s1m = J.s1.to_numpy()
    Lz, Lz0 = FA.logits_pooled(Xz, fc, heads), FA.logits_pooled(Xz, fc, heads, AX, [0]); dp1 = Lz[:, :, 0].mean(1) - LP[mi][:, :, 0].mean(1); doff = Lz0[:, :, 0].mean(1) - LP0[mi][:, :, 0].mean(1); h6 = doff - dp1
    cnt = dict(exams=int(len(J)), participants=int(len(np.unique(pid))))
    st["O2-H1"] = dict(FA.boot_stat(lambda t: float((np.abs(d6[t]) >= th["quarter_sd"] * th["sd_ref_lbar6_all_dev_main"]).mean()), pid), counts=cnt)
    st["O2-H2"] = dict(FA.boot_stat(lambda t: float(d1[t].mean()), pid), counts=cnt)
    fa, fb = s1m >= tau, s1z >= tau
    st["O2-H3"] = dict(FA.boot_stat(lambda t: float((fa[t] != fb[t]).mean()), pid), counts=cnt)
    st["O2-H6"] = dict(FA.boot_stat(lambda t: float(h6[t].mean()), pid), counts=cnt, mean_delta_lbar1_from_pooled=float(dp1.mean()), mean_delta_lbar1_axis0_off=float(doff.mean()))
    al = {}
    for nm, thr in (("tau90", tau), ("tau_rad", TAU_RAD)):
        xa, xb = s1m >= thr, s1z >= thr; bt = S.Boot(pid)
        al[nm] = dict(FA.flags(xa, xb), threshold=thr, discordant_share=bt.ci(lambda t: float((xa[t] != xb[t]).mean())),
                      net_change_per_1000=bt.ci(lambda t: float(((~xa[t] & xb[t]).sum() - (xa[t] & ~xb[t]).sum()) / len(t) * 1000)))
    sec["alarm_changes"] = al
    dax = (AXF.activation(AX, Xz) - act[mi]) / AX["axis_sd_dev"]; sec["C1_axis0_shift_dev_sd"] = FA.boot_stat(lambda t: float(dax[t, 0].mean()), pid)
    mk = J.maker.to_numpy(); cls = np.where(J.thickness / J.true_spacing >= 1.9, "2.0", "1.6")
    sec["by_maker"] = {k: dict(n=int((mk == k).sum()), mean_d1=float(d1[mk == k].mean()), mean_h6=float(h6[mk == k].mean()), flag_change_tau90=float((fa != fb)[mk == k].mean()),
                               share_quarter_sd=float((np.abs(d6[mk == k]) >= 0.25 * th["sd_ref_lbar6_all_dev_main"]).mean())) for k in sorted(set(mk))}
    sec["by_stretch_class"] = {k: dict(n=int((cls == k).sum()), mean_d1=float(d1[cls == k].mean())) for k in ("1.6", "2.0") if (cls == k).any()}
    crop = (J.resT.astype(float) > 200).to_numpy(); zT = np.round(J.n_images.astype(float) * J.true_spacing.astype(float) / 2.5).to_numpy(); pad = zT < 200
    sec["crop_pad"] = {nm: dict(n=int(m_.sum()), mean_d1=(S.Boot(pid[m_]).ci(lambda t, v=d1[m_]: float(v[t].mean())) if m_.sum() >= 10 else None))
                       for nm, m_ in (("main_cropped", crop), ("main_not_cropped", ~crop), ("zfix_padded", pad), ("zfix_not_padded", ~pad))}
    # ---- O2b: H7 on consecutive pairs with both exams scored (U1 and U2)
    c = ["pid", "study_yr", "st", "st_incl0", "l1", "l1_off", "ax0", "F1", "s1", "model", "ge"]
    f1, _ = form_f1(a.tables, a.split, None); E["F1"] = [f1.get((p, y), np.nan) for p, y in zip(E.pid, E.study_yr)]
    res["F1_missing"] = int(E.F1.isna().sum())
    Pp = E[c].merge(E[c], on="pid", suffixes=("_a", "_b")); Pp = Pp[(Pp.study_yr_b == Pp.study_yr_a + 1) & Pp.F1_a.notna() & Pp.F1_b.notna()].reset_index(drop=True)
    dd = dict(dst=(Pp.st_b - Pp.st_a).to_numpy(float), dst0=(Pp.st_incl0_b - Pp.st_incl0_a).to_numpy(float), dl=(Pp.l1_b - Pp.l1_a).to_numpy(), dl_off=(Pp.l1_off_b - Pp.l1_off_a).to_numpy(),
              dax0=(Pp.ax0_b - Pp.ax0_a).to_numpy(), dF=(Pp.F1_b - Pp.F1_a).to_numpy())
    ppid = Pp.pid.to_numpy(); nge = (Pp.ge_a + Pp.ge_b).to_numpy(); flip = ((Pp.s1_a >= tau) != (Pp.s1_b >= tau)).to_numpy()
    bfn = lambda key, rows_, dk="dst": (lambda t: FA.ols_b(dd[key][rows_][t], dd[dk][rows_][t], dd["dF"][rows_][t]))   # noqa: E731

    def pc(r_): return dict(pairs=int(len(r_)), participants=int(len(np.unique(ppid[r_]))), changed=int((dd["dst"][r_] != 0).sum()),
                            stretched_to_not=int((dd["dst"][r_] == -1).sum()), not_to_stretched=int((dd["dst"][r_] == 1).sum()))
    allr = np.arange(len(Pp)); notboth = np.flatnonzero(nge < 2); neither = np.flatnonzero(nge == 0); chg = np.flatnonzero(dd["dst"] != 0)
    st["O2-H7"] = dict(FA.boot_stat(bfn("dl", allr), ppid), counts=pc(allr))
    st["O2-H7x"] = dict(FA.boot_stat(bfn("dl", notboth), ppid[notboth]), counts=pc(notboth))
    f7 = dict(b_axis0_off=FA.boot_stat(bfn("dl_off", allr), ppid), axis0_jump_dev_sd=FA.boot_stat(bfn("dax0", allr), ppid),
              b_ratio0_counted_stretched=FA.boot_stat(bfn("dl", allr, "dst0"), ppid), b_changed_pairs_only=FA.boot_stat(bfn("dl", chg), ppid[chg]),
              by_ge=dict(both_ge=dict(FA.boot_stat(bfn("dl", np.flatnonzero(nge == 2)), ppid[nge == 2]), counts=pc(np.flatnonzero(nge == 2))),
                         one_ge=dict(FA.boot_stat(bfn("dl", np.flatnonzero(nge == 1)), ppid[nge == 1]), counts=pc(np.flatnonzero(nge == 1))) if ((nge == 1) & (dd["dst"] != 0)).sum() >= 5 else None,
                         neither_ge=dict(FA.boot_stat(bfn("dl", neither), ppid[neither]), counts=pc(neither)) if (dd["dst"][neither] != 0).sum() >= 5 else None),
              axis0_off_not_both_ge=FA.boot_stat(bfn("dl_off", notboth), ppid[notboth]))
    same = np.flatnonzero((Pp.model_a == Pp.model_b).to_numpy())
    if (dd["dst"][same] != 0).sum() >= 5: f7["same_scanner_model"] = dict(FA.boot_stat(bfn("dl", same), ppid[same]), counts=pc(same))
    f7["groups"] = {nm: dict(n=int((dd["dst"] == v).sum()), mean_dl=float(dd["dl"][dd["dst"] == v].mean()), mean_dl_off=float(dd["dl_off"][dd["dst"] == v].mean()),
                             flag_flip_tau90=float(flip[dd["dst"] == v].mean())) for nm, v in (("stretched_to_not", -1), ("unchanged", 0), ("not_to_stretched", 1)) if (dd["dst"] == v).any()}
    sec["H7_details"] = f7
    # ---- attention under the z-fix (outcome-free r10 logic; the largest recorded nodule >= 4 mm from ctab)
    N = pd.read_csv(Path(a.tables) / "nlst_780_ctab_idc_20210527.csv", dtype={"pid": str}); N = N[(N.sct_ab_desc == 51) & N.sct_slice_num.notna() & (N.sct_long_dia >= 4)]
    N = N.sort_values("sct_long_dia", ascending=False).drop_duplicates(["pid", "study_yr"])
    Q = J.merge(N[["pid", "study_yr", "sct_slice_num", "sct_long_dia"]], on=["pid", "study_yr"]); Q = Q[Q.sct_slice_num <= Q.n_images].reset_index(drop=True)
    att = {}
    if len(Q) >= 10:
        a1 = sm(np.stack([arr(Fm[u][1], "att_vol1").astype(np.float64) for u in Q.series_uid])).mean(1); a2 = sm(np.stack([arr(Fz[u][1], "att_vol1").astype(np.float64) for u in Q.series_uid])).mean(1)
        zq = np.round(Q.n_images.astype(float) * Q.true_spacing.astype(float) / 2.5).to_numpy()
        ok1, k1 = bins(Q.sct_slice_num.to_numpy(), Q.thickness.astype(float).to_numpy(), Q.resT.astype(float).to_numpy()); ok2, k2 = bins(Q.sct_slice_num.to_numpy(), Q.true_spacing.astype(float).to_numpy(), zq)
        v1, v2 = near(a1, k1), near(a2, k2); both = ok1 & ok2; dq = (v2 - v1)[both]; qp = Q.pid.to_numpy()[both]
        att = dict(n=int(both.sum()), participants=int(len(set(qp))), nodule_outside_box_main=int((~ok1).sum()), nodule_outside_box_zfix=int((~ok2).sum()),
                   share_near_main=float(v1[both].mean()), share_near_zfix=float(v2[both].mean()), diff_zfix_minus_main=S.Boot(qp).ci(lambda t: float(dq[t].mean())),
                   note="att_vol1; nodule bins as r10_att_harm.py (box order reversed); mechanistic displacement, never patient harm")
    sec["attention_zfix"] = att
    # ---- tests, Holm over the O2 family
    fam = [("O2-H1", "H1", None), ("O2-H2", "H2", None), ("O2-H3", "H3", None), ("O2-H6", "H6", None), ("O2-H7", "H7", None), ("O2-H7x", "H7", 0.0)]
    ps, out_rows = [], []
    for oid, hid, null_over in fam:
        h = HY[hid]; s = st[oid]; null = h["null"] if null_over is None else null_over
        p = FA.wald(s["sd"], s["est"], null, h["direction"]); ps.append(p)
        out_rows.append(dict(id=oid, frozen_source=hid, direction=h["direction"], null=null, est=s["est"], ci95=[s["lo"], s["hi"]], p_one_sided=p, counts=s["counts"]))
    for r, x in zip(out_rows, FA.holm(ps, 0.05)): r["null_rejected_holm_over_6"] = bool(x)
    res["hypotheses"] = out_rows; res["n_rejected"] = int(sum(r["null_rejected_holm_over_6"] for r in out_rows)); res["secondary"] = sec
    res["O2-H6_detail"] = {k: v for k, v in st["O2-H6"].items() if k.startswith("mean_delta")}
    out_p = Path(a.out); out_p.parent.mkdir(parents=True, exist_ok=True); out_p.write_bytes((json.dumps(res, indent=1, default=float) + "\n").encode("utf-8"))
    print(json.dumps(dict(files=res["files"], G2=res["G2b_G2c"]["pass_"], n=cnt, pairs=st["O2-H7"]["counts"]), default=float))


if __name__ == "__main__":
    main()
