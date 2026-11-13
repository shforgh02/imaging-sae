"""Lung L2, step S2: pilot checks G2a-G2h (docs/LUNG_L2_PROTOCOL.md section 8), on the PC copy of the volume.
usage: python s2_pilot_checks.py <local copy of /l2 on the volume> <lung_l2/results/runs dir> <out_json>
The local copy holds run_info/ (heads.npz, calibrator json, smoke.json), dev/{main,zfix,errors}/, rep/main/, l4/main/.
"""
import glob
import json
import os
import sys
from pathlib import Path

import numpy as np

T4_RATE, L4_RATE = 0.59 + 4 * 0.0473 + 16 * 0.008, 0.80 + 4 * 0.0473 + 16 * 0.008
L1_SEC_PER_SERIES = 7.6


def load_heads(p):
    z = np.load(p)
    return [{k: z[f"m{i}_{k}"] for k in ("hidden_fc_W", "hidden_fc_b", "hazard_fc_W", "hazard_fc_b", "base_hazard_fc_W", "base_hazard_fc_b")} for i in range(5)]


def calibrate(cal, mean_prob):
    """numpy copy of sybil.models.calibrator.SimpleClassifierGroup for one exam: mean over sub-calibrators of interp(clip(x @ coef + b))."""
    out = []
    for t in range(6):
        vals = []
        for c in cal[f"Year{t + 1}"]:
            T = np.array([[mean_prob[t]]]) @ np.array(c["coef"]) + np.array(c["intercept"])
            T = np.clip(T, c["x_min"] if c["x_min"] is not None else -np.inf, c["x_max"] if c["x_max"] is not None else np.inf)
            vals.append(np.interp(T, np.array(c["x0"]), np.array(c["y0"])))
        out.append(float(np.mean(vals)))
    return out


def recompute(arr, heads):
    """max abs differences of the three recomputations (G2b) for one series."""
    d_relu, d_hid, d_logit, d_raw = 0.0, 0.0, 0.0, 0.0
    for i, H in enumerate(heads):
        h, pre, pooled = arr["h"][i].astype(np.float64), arr["pre"][i].astype(np.float64), arr["pooled"][i].astype(np.float64)
        d_relu = max(d_relu, float(np.abs(np.maximum(pre, 0) - h).max()))
        d_hid = max(d_hid, float(np.abs(pooled @ H["hidden_fc_W"].T.astype(np.float64) + H["hidden_fc_b"] - pre).max()))
        raw = h @ H["hazard_fc_W"].T.astype(np.float64) + H["hazard_fc_b"]
        base = h @ H["base_hazard_fc_W"].T.astype(np.float64) + H["base_hazard_fc_b"]
        logit = base + np.cumsum(np.maximum(raw, 0))
        d_logit = max(d_logit, float(np.abs(logit - arr["logit"][i]).max()))
        d_raw = max(d_raw, float(np.abs(raw - arr["raw_haz"][i]).max()))
    return d_relu, d_hid, d_logit, d_raw


def main():
    vol_d, runs_d, out_p = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    res = {}
    smoke = json.load(open(vol_d / "run_info" / "smoke.json"))
    ver = smoke.get("bench", {}).get("verify", [])
    res["G2a"] = dict(demo_maxdiff=smoke["demo_maxdiff"], demo_volume_equal_serie=smoke["demo_volume_equal_serie"],
                      official_vs_l2_maxdiff=max(abs(a - b) for a, b in zip(smoke["demo_official_predict"], smoke["demo_scores"])),
                      dev_volume_equal_serie=[v["equal"] for v in ver])
    res["G2a"]["pass"] = bool(smoke["demo_maxdiff"] <= 0.005 and smoke["demo_volume_equal_serie"] and all(v["equal"] for v in ver))
    heads = load_heads(vol_d / "run_info" / "heads.npz")
    cal = json.load(open(vol_d / "run_info" / "sybil_ensemble_simple_calibrator.json"))
    rows, worst = [], dict(relu=0.0, hid=0.0, logit=0.0, raw=0.0, mean=0.0, calib=0.0)
    gating = []
    for var in ("main", "zfix"):
        for j in sorted(glob.glob(str(vol_d / "dev" / var / "*.json"))):
            rec = json.load(open(j)); arr = np.load(j[:-5] + ".npz")
            a, b, c, d = recompute(arr, heads)
            mp = (1 / (1 + np.exp(-arr["logit"].astype(np.float64)))).mean(0)
            dm = float(np.abs(mp - np.array(rec["mean_prob"])).max())
            dc = float(np.abs(np.array(calibrate(cal, mp)) - np.array(rec["calib"])).max())
            for k, v in zip(worst, (a, b, c, d, dm, dc)): worst[k] = max(worst[k], v)
            gating.append(arr["raw_haz"] > 0)                       # (5 members, 6 units)
            rows.append(dict(uid=rec["series_uid"], variant=var, pilot=rec["pilot"], ok_b=(a == 0.0 and b <= 1e-3 and c <= 1e-4), ok_c=(dc <= 1e-4),
                             geo=rec["geo"], meas=rec["measures"], sec=rec["sec"], calib=rec["calib"]))
    main_rows = [r for r in rows if r["variant"] == "main" and r["pilot"]]
    res["n_saved"] = dict(main=len([r for r in rows if r["variant"] == "main"]), zfix=len([r for r in rows if r["variant"] == "zfix"]), pilot_main=len(main_rows))
    res["G2b"] = dict(max_abs=dict(relu_vs_h=worst["relu"], hidden_fc=worst["hid"], logits=worst["logit"], raw_hazards=worst["raw"]),
                      n_fail=int(sum(not r["ok_b"] for r in rows)), pass_=bool(all(r["ok_b"] for r in rows)))
    res["G2c"] = dict(max_abs_mean_prob=worst["mean"], max_abs_calib=worst["calib"], n_fail=int(sum(not r["ok_c"] for r in rows)), pass_=bool(all(r["ok_c"] for r in rows)))
    g = np.array(gating)
    res["hazard_units_on_share"] = dict(by_member=g.mean((0, 2)).round(4).tolist(), by_unit=g.mean((0, 1)).round(4).tolist()) if len(g) else None
    # G2d: repeat run in another container
    diffs = []
    for j in glob.glob(str(vol_d / "rep" / "main" / "*.json")):
        a = json.load(open(j)); p = vol_d / "dev" / "main" / os.path.basename(j)
        if p.exists(): diffs.append(float(np.abs(np.array(a["calib"]) - np.array(json.load(open(p))["calib"])).max()))
    res["G2d"] = dict(n=len(diffs), max_abs=max(diffs) if diffs else None, pass_=bool(len(diffs) >= 20 and max(diffs) <= 1e-4))
    # L4 vs T4 values (same series) for information
    d4 = []
    for j in glob.glob(str(vol_d / "l4" / "main" / "*.json")):
        p = vol_d / "dev" / "main" / os.path.basename(j)
        if p.exists(): d4.append(float(np.abs(np.array(json.load(open(j))["calib"]) - np.array(json.load(open(p))["calib"])).max()))
    res["l4_vs_t4_max_abs_calib"] = max(d4) if d4 else None
    # G2e: image measures
    M = [r["meas"] for r in main_rows]
    have = [m for m in M if "lung_vol_ml" in m]
    plaus = [m for m in have if 2000 <= m["lung_vol_ml"] <= 9000 and 0 <= m["laa950_pct"] <= 60]
    air = [m for m in have if m.get("air_median_hu") is not None and abs(m["air_median_hu"] + 1000) <= 30]
    res["G2e"] = dict(n=len(M), computed=len(have) / max(1, len(M)), plausible=len(plaus) / max(1, len(have)), air_ok=len(air) / max(1, len(have)),
                      lung_vol_ml_q=np.percentile([m["lung_vol_ml"] for m in have], [5, 50, 95]).round(0).tolist() if have else None,
                      laa950_q=np.percentile([m["laa950_pct"] for m in have], [5, 50, 95]).round(2).tolist() if have else None,
                      air_median_q=np.percentile([m["air_median_hu"] for m in air], [5, 50, 95]).round(1).tolist() if air else None,
                      noise_q=np.percentile([m["air_noise_sd_hu"] for m in have if m.get("air_noise_sd_hu") is not None], [5, 50, 95]).round(1).tolist() if have else None,
                      lung_cut_z=int(sum(m.get("lung_cut_z", False) for m in have)), lung_cut_xy=int(sum(m.get("lung_cut_xy", False) for m in have)),
                      mean_sec_volumes_measures=float(np.mean([r["sec"]["volumes_measures"] for r in main_rows])) if main_rows else None)
    # G2f: z-stretch is real
    zf = {r["uid"]: r for r in rows if r["variant"] == "zfix"}
    pairs = []
    for r in main_rows:
        z = zf.get(r["uid"])
        if z is None or r["geo"]["ratio"] is None or r["geo"]["ratio"] > 0.65: continue
        if "lung_z_extent_app_mm" not in r["meas"] or "lung_z_extent_app_mm" not in z["meas"]: continue
        meas_ratio = r["meas"]["lung_z_extent_app_mm"] / z["meas"]["lung_z_extent_app_mm"]
        pairs.append(dict(expected=1 / r["geo"]["ratio"], measured=meas_ratio, cut=r["meas"].get("lung_cut_z", False)))
    ok = [abs(p["measured"] / p["expected"] - 1) <= 0.10 for p in pairs]
    res["G2f"] = dict(n=len(pairs), share_within_10pct=float(np.mean(ok)) if ok else None, pass_=bool(len(ok) >= 10 and np.mean(ok) >= 0.90),
                      examples=pairs[:8])
    # zfix score change in the pilot (information for the dev analysis; not a gate)
    dz = [(zf[r["uid"]]["calib"][5] - r["calib"][5], r["geo"]["ratio"]) for r in main_rows if r["uid"] in zf]
    res["zfix_change_calib_y6"] = dict(n=len(dz), mean_abs=float(np.mean([abs(a) for a, _ in dz])) if dz else None,
                                       by_ratio={str(round(k, 2)): float(np.mean([abs(a) for a, rr in dz if round(rr, 2) == round(k, 2)])) for k in sorted({round(rr, 2) for _, rr in dz})} if dz else None)
    # G2g + G2h from the collected run files
    runs = {}
    for p in glob.glob(str(runs_d / "*.json")):
        o = json.load(open(p)); calls = o.get("calls", [o])
        runs[Path(p).stem] = dict(container_min=float(o["container_min"]), n_done=sum(c.get("n_done", 0) for c in calls),
                                  n_err=sum(len(c.get("errors", {})) for c in calls), gpu=calls[0].get("gpu"),
                                  mean_sec={k: float(np.mean([c["mean_sec"].get(k, 0) for c in calls if c.get("mean_sec")])) for k in ("download", "load", "volumes_measures", "infer_main", "infer_zfix")})
    res["runs"] = runs
    pil = [v for k, v in runs.items() if k.startswith("run_dev_D1_0_300")]
    l4 = [v for k, v in runs.items() if k.startswith("run_l4_l4_D1")]
    if pil:
        p = pil[0]; sec = p["container_min"] * 60 / max(1, p["n_done"])
        res["G2g"] = dict(t4_container_sec_per_series=sec, t4_usd_per_series=sec / 3600 * T4_RATE)
        if l4:
            q = l4[0]; s4 = q["container_min"] * 60 / max(1, q["n_done"])
            res["G2g"].update(l4_container_sec_per_series=s4, l4_usd_per_series=s4 / 3600 * L4_RATE)
            res["G2g"]["cheaper"] = "L4" if s4 / 3600 * L4_RATE < sec / 3600 * T4_RATE else "T4"
        res["G2h"] = dict(n_rows=300, n_err=p["n_err"], share=p["n_err"] / 300, pass_=p["n_err"] / 300 < 0.05)
    err_files = glob.glob(str(vol_d / "dev" / "errors" / "*.json"))
    res["error_files"] = [json.load(open(e)) for e in err_files][:20]
    Path(out_p).write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: v for k, v in res.items() if k not in ("error_files",)}, indent=1, default=str))


if __name__ == "__main__":
    main()
