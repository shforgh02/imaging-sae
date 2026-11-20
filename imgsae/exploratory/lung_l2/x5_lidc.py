"""Lung L2, plan X5 (docs/EXECUTION_LOG.md, 2026-11-20, committed 41ca595): the slice-spacing replication on LIDC-IDRI. EXPLORATORY external
replication: the statistics, nulls, SD reference, shared axes and heads are the frozen NLST ones (results/s5/, hash-checked by
s6_frozen_analysis.load_frozen); nothing is fitted; no outcome or annotation is read. Written and committed before the LIDC output existed.
Per series (one per patient), from the PC copy of root lidc: the main run and the z-fix run (made by the job when its DICOM ratio <= 0.65).
  H1: share of exams with |delta lbar_6| >= 0.25 x 0.92957 (null 0.30, >); H2: mean delta lbar_1 (null -0.10, <);
  H6: mean of [delta lbar_1 with shared axis 0 of pooled set to its dev mean] - [delta lbar_1 from pooled as is] (null +0.20, >);
  C1: mean axis-0 shift in dev SD units (secondary); patient bootstrap 2,000, seed 0; one-sided Wald p; Holm over H1, H2, H6.
Also: G2b/G2c rebuild checks on every file; counts by maker and thickness; flags at the frozen tau90 (descriptive); agreement of the five
members on the 11 frozen axes in the LIDC main runs.
usage (venv python): python x5_lidc.py <account l2 copy> <frozen dir results/s5> <run_info dir (main copy)> <out json>
"""
import glob
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import s2_pilot_checks as P2  # noqa: E402
import s4_common as S  # noqa: E402
import s5_axes_freeze as AXF  # noqa: E402
import s6_frozen_analysis as FA  # noqa: E402


def load(root_dir, variant):
    out = {}
    for j in sorted(glob.glob(str(root_dir / variant / "*.json"))):
        npz = j[:-5] + ".npz"
        if Path(npz).exists(): out[Path(j).stem] = (json.load(open(j)), np.load(npz))
    return out


def main():
    A, FZ, RI, out_p = Path(sys.argv[1]) / "lidc", Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
    T, arms, fams, lab_of, FI, COMB, AX = FA.load_frozen(FZ, RI); th = T["thresholds"]; HY = {h["id"]: h for h in T["hypotheses"]}
    heads = S.C.load_heads(RI / "heads.npz"); fc = AXF.load_fc(RI / "heads.npz"); cal = json.load(open(RI / "sybil_ensemble_simple_calibrator.json"))
    heads_chk = P2.load_heads(RI / "heads.npz")   # the format of the S3 rebuild checks (s3_checks_all.py)
    M, Z = load(A, "main"), load(A, "zfix"); errs = sorted(Path(p).stem for p in glob.glob(str(A / "errors" / "*.json")))
    res = dict(label="EXPLORATORY external replication on LIDC-IDRI (plan X5, committed 41ca595); frozen NLST definitions; nothing confirmed",
               files=dict(main=len(M), zfix=len(Z), errors=len(errs), errors_not_done=len(set(errs) - set(M))))
    # integrity: G2b / G2c on every file (the code of s3_checks_all.py)
    nb = nc = 0; worst = dict(hid=0.0, logit=0.0, calib=0.0)
    for rec, arr in list(M.values()) + list(Z.values()):
        a, b, c, d = P2.recompute(arr, heads_chk); mp = (1 / (1 + np.exp(-arr["logit"].astype(np.float64)))).mean(0)
        dc = float(np.abs(np.array(P2.calibrate(cal, mp)) - np.array(rec["calib"])).max())
        nb += not (a == 0.0 and b <= 1e-3 and c <= 1e-4); nc += not dc <= 1e-4
        worst.update(hid=max(worst["hid"], b), logit=max(worst["logit"], c), calib=max(worst["calib"], dc))
    res["G2b_G2c"] = dict(n_files=len(M) + len(Z), G2b_fail=nb, G2c_fail=nc, max_abs=worst, pass_=nb == 0 and nc == 0)
    ver = [r["geo"].get("ratio") for r, _ in M.values()]
    res["geometry"] = dict(n_main=len(M), ratio_le_0p65=int(sum(1 for v in ver if v is not None and v <= th["zfix_ratio_max"])),
                           zfix_needed=int(sum(1 for r, _ in M.values() if r["geo"].get("zfix_needed"))), zfix_present=len(Z),
                           lung_cut_z=int(sum(1 for r, _ in M.values() if r.get("measures", {}).get("lung_cut_z"))))
    # agreement of the five members on the 11 frozen axes, LIDC main runs
    Xm = np.stack([arr["pooled"].astype(np.float64) for _, arr in M.values()])
    V = AXF.variates(AX, Xm); Zs = (V - V.mean(0)) / np.maximum(V.std(0), 1e-12); Cc = np.einsum("nia,nja->ija", Zs, Zs) / len(V); iu = np.triu_indices(5, 1)
    res["axes_member_agreement_lidc_main"] = np.round(Cc[iu].mean(0), 4).tolist()
    # the z-fix population: main files with ratio <= 0.65 and a z-fix file
    uids = [u for u, (r, _) in M.items() if r["geo"].get("ratio") is not None and r["geo"]["ratio"] <= th["zfix_ratio_max"] and u in Z]
    pid = np.array([M[u][0]["pid"] for u in uids])
    lg_m = np.stack([M[u][1]["logit"].astype(np.float64) for u in uids]); lg_z = np.stack([Z[u][1]["logit"].astype(np.float64) for u in uids])
    d1, d6 = lg_z[:, :, 0].mean(1) - lg_m[:, :, 0].mean(1), lg_z[:, :, 5].mean(1) - lg_m[:, :, 5].mean(1)
    Xa, Xz = np.stack([M[u][1]["pooled"].astype(np.float64) for u in uids]), np.stack([Z[u][1]["pooled"].astype(np.float64) for u in uids])
    Lm, Lz = FA.logits_pooled(Xa, fc, heads), FA.logits_pooled(Xz, fc, heads); Lm0, Lz0 = FA.logits_pooled(Xa, fc, heads, AX, [0]), FA.logits_pooled(Xz, fc, heads, AX, [0])
    dp1 = Lz[:, :, 0].mean(1) - Lm[:, :, 0].mean(1); h6 = (Lz0[:, :, 0].mean(1) - Lm0[:, :, 0].mean(1)) - dp1
    res["check_max_abs_lbar1_from_pooled_minus_saved"] = float(max(np.abs(Lm[:, :, 0].mean(1) - lg_m[:, :, 0].mean(1)).max(), np.abs(Lz[:, :, 0].mean(1) - lg_z[:, :, 0].mean(1)).max()))
    sd6 = th["sd_ref_lbar6_all_dev_main"]; st = {}
    st["H1"] = FA.boot_stat(lambda t: float((np.abs(d6[t]) >= th["quarter_sd"] * sd6).mean()), pid)
    st["H2"] = FA.boot_stat(lambda t: float(d1[t].mean()), pid)
    st["H6"] = FA.boot_stat(lambda t: float(h6[t].mean()), pid)
    rows, ps = [], []
    for hid in ("H1", "H2", "H6"):
        h, s = HY[hid], st[hid]; p = FA.wald(s["sd"], s["est"], h["null"], h["direction"]); ps.append(p)
        rows.append(dict(id=hid, name=h["name"], direction=h["direction"], null=h["null"], est=s["est"], ci95=[s["lo"], s["hi"]], p_one_sided=p))
    for r, x in zip(rows, FA.holm(ps, 0.05)): r["null_rejected_holm_over_3"] = bool(x)
    res["replication"] = dict(counts=dict(exams=len(uids), patients=int(len(np.unique(pid)))), hypotheses=rows,
                              mean_delta_lbar1_axis0_off=float((Lz0[:, :, 0].mean(1) - Lm0[:, :, 0].mean(1)).mean()), mean_delta_lbar1_from_pooled=float(dp1.mean()),
                              share_exams_h6_above_0p20=float((h6 >= 0.20).mean()))
    az, am = AXF.activation(AX, Xz), AXF.activation(AX, Xa); dax = (az - am) / AX["axis_sd_dev"]
    res["C1_axis0_shift_dev_sd"] = dict(FA.boot_stat(lambda t: float(dax[t, 0].mean()), pid), note="secondary; NLST dev -2.740, test -2.729")
    tau = th["tau90_s1"]; fa = np.array([M[u][0]["calib"][0] >= tau for u in uids]); fb = np.array([Z[u][0]["calib"][0] >= tau for u in uids])
    res["flags_tau90_descriptive"] = FA.flags(fa, fb)
    mk = np.array([str(M[u][0]["tags"].get("Manufacturer")) for u in uids]); thk = np.array([M[u][0]["geo"].get("thickness") for u in uids])
    res["by_maker"] = {k: dict(n=int((mk == k).sum()), mean_d1=float(d1[mk == k].mean()), mean_h6=float(h6[mk == k].mean())) for k in sorted(set(mk))}
    res["by_thickness"] = {str(k): dict(n=int((thk == k).sum()), mean_d1=float(d1[thk == k].mean())) for k in sorted(set(thk))}
    out_p.parent.mkdir(parents=True, exist_ok=True); out_p.write_bytes((json.dumps(res, indent=1, default=float) + "\n").encode("utf-8"))
    print(json.dumps(dict(files=res["files"], G2=res["G2b_G2c"]["pass_"], n=res["replication"]["counts"]), default=float))


if __name__ == "__main__":
    main()
