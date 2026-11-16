"""Lung L2, plan step P2 (docs/PLAN_L2_NEXT_v1.md; protocol 16a, amendment A4): gate "identity across accounts".
Compares the armanfo copy of the volume with the main account's PC copy (D1 files saved in S2/S3, all G2b/G2c-checked).
Pass marks (all must hold):
  smoke on armanfo: demo case within 0.005 of the published scores (expected 0.0), the demo volume equal to Serie.get_volume(), 3 of 3
  dev volumes equal to Sybil's own, no error, 3 done; checkpoint SHA-256 (all files) and head-weight SHA-256 equal to the main account's
  record (results/runs/smoke.json; heads ba2d6d85...009bac);
  identity: every one of the 20 armanfo files of root xacct (D1 rows 0-20) and the 3 smoke series armanfo wrote into root dev has its
  counterpart in the main copy, with calibrated probabilities within 1e-4 and h within 1e-4 (max abs); z-fix files that exist on both
  sides are compared the same way. Other arrays, the image measures and the DICOM tags are reported (not marks).
usage (venv python): python p2_identity.py <armanfo l2 copy> <main l2 copy> <armanfo smoke json> <main smoke json> <armanfo run json> <out json>
"""
import glob
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HEADS_MAIN = "ba2d6d85d330cc6c99360c557647460ba4fa7ab738abba9be79c1d26b8009bac"
TOL_CALIB, TOL_H = 1e-4, 1e-4


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def num_diff(a, b):
    """max abs difference over the numeric fields shared by two flat dicts; names of fields that differ in kind or presence."""
    worst, odd = 0.0, []
    for k in sorted(set(a) | set(b)):
        x, y = a.get(k), b.get(k)
        if isinstance(x, bool) or isinstance(y, bool) or not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            if x != y: odd.append(k)
        elif np.isfinite(x) and np.isfinite(y): worst = max(worst, abs(float(x) - float(y)))
        elif not (np.isnan(x) and np.isnan(y)) and x != y: odd.append(k)
    return worst, odd


def compare(a_dir, m_dir, variant):
    rows = []
    for j in sorted(glob.glob(str(a_dir / variant / "*.json"))):
        uid = Path(j).stem; mj = m_dir / variant / f"{uid}.json"
        if not mj.exists(): rows.append(dict(uid=uid, variant=variant, counterpart=False)); continue
        ra, rm = json.load(open(j)), json.load(open(mj)); za, zm = np.load(j[:-5] + ".npz"), np.load(str(mj)[:-5] + ".npz")
        arr = {k: float(np.abs(za[k].astype(np.float64) - zm[k].astype(np.float64)).max()) for k in za.files if k in zm.files}
        dc = float(np.abs(np.array(ra["calib"]) - np.array(rm["calib"])).max())
        dmeas, odd_meas = num_diff(ra["measures"], rm["measures"])
        rows.append(dict(uid=uid, variant=variant, counterpart=True, calib=dc, h=arr.get("h"), arrays=arr, keys_equal=sorted(za.files) == sorted(zm.files),
                         measures_max_abs=dmeas, measures_odd=odd_meas, tags_equal=ra["tags"] == rm["tags"], geo_equal=ra["geo"] == rm["geo"],
                         ok=bool(dc <= TOL_CALIB and arr.get("h") is not None and arr["h"] <= TOL_H)))
    return rows


def summary(rows):
    have = [r for r in rows if r["counterpart"]]
    return dict(n=len(rows), n_with_counterpart=len(have), n_ok=sum(r["ok"] for r in have),
                max_calib=max((r["calib"] for r in have), default=None), max_h=max((r["h"] for r in have), default=None),
                max_by_array={k: max(r["arrays"][k] for r in have if k in r["arrays"]) for k in sorted({k for r in have for k in r["arrays"]})} if have else {},
                max_measures=max((r["measures_max_abs"] for r in have), default=None), measures_odd=sorted({k for r in have for k in r["measures_odd"]}),
                tags_equal=all(r["tags_equal"] for r in have), geo_equal=all(r["geo_equal"] for r in have), keys_equal=all(r["keys_equal"] for r in have))


def main():
    A, M, sa_p, sm_p, run_p, out_p = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5]), Path(sys.argv[6])
    sa, sm = json.load(open(sa_p)), json.load(open(sm_p)); b = sa.get("bench", {})
    res = dict(files=dict(armanfo_copy=str(A), main_copy=str(M), armanfo_smoke=str(sa_p), main_smoke=str(sm_p), armanfo_run=str(run_p)))
    smoke = dict(gpu=sa.get("gpu"), torch=sa.get("torch"), demo_maxdiff=sa["demo_maxdiff"], demo_pass=sa["demo_pass"], demo_volume_equal_serie=sa["demo_volume_equal_serie"],
                 demo_official_vs_l2=max(abs(x - y) for x, y in zip(sa["demo_official_predict"], sa["demo_scores"])),
                 demo_vs_main_smoke=max(abs(x - y) for x, y in zip(sa["demo_scores"], sm["demo_scores"])),
                 dev_volumes_equal=[v["equal"] for v in b.get("verify", [])], bench_n_done=b.get("n_done"), bench_errors=b.get("errors"))
    smoke["pass"] = bool(sa["demo_maxdiff"] <= 0.005 and sa["demo_pass"] and sa["demo_volume_equal_serie"] and smoke["dev_volumes_equal"] == [True] * 3
                         and b.get("n_done") == 3 and not b.get("errors"))
    hashes = dict(ckpt_equal=sa["ckpt_sha256"] == sm["ckpt_sha256"], n_ckpt_files=len(sa["ckpt_sha256"]), heads_armanfo=sa["heads_sha256"], heads_main=sm["heads_sha256"],
                  heads_equal=sa["heads_sha256"] == sm["heads_sha256"] == HEADS_MAIN, sybil_commit_equal=sa["sybil_commit"] == sm["sybil_commit"],
                  heads_file_pc_equal=sha(A / "run_info" / "heads.npz") == sha(M / "run_info" / "heads.npz") == HEADS_MAIN,
                  calibrator_file_pc_equal=sha(A / "run_info" / "sybil_ensemble_simple_calibrator.json") == sha(M / "run_info" / "sybil_ensemble_simple_calibrator.json"))
    hashes["pass"] = bool(hashes["ckpt_equal"] and hashes["heads_equal"] and hashes["sybil_commit_equal"] and hashes["heads_file_pc_equal"] and hashes["calibrator_file_pc_equal"])
    run = json.load(open(run_p)); calls = run.get("calls", [run])
    run_info = dict(n_rows=sum(c["n_rows"] for c in calls), n_done=sum(c["n_done"] for c in calls), n_err=sum(len(c["errors"]) for c in calls),
                    gpu=calls[0].get("gpu"), container_min=run["container_min"])
    x_main, x_zfix = compare(A / "xacct", M / "dev", "main"), compare(A / "xacct", M / "dev", "zfix")
    s_main, s_zfix = compare(A / "dev", M / "dev", "main"), compare(A / "dev", M / "dev", "zfix")
    ident = dict(xacct_main=summary(x_main), xacct_zfix=summary(x_zfix), smoke_main=summary(s_main), smoke_zfix=summary(s_zfix),
                 xacct_run=run_info, armanfo_dev_uids=sorted(r["uid"] for r in s_main))
    allrows = x_main + x_zfix + s_main + s_zfix
    ident["pass"] = bool(len(x_main) == 20 and len(s_main) == 3 and run_info["n_done"] == 20 and run_info["n_err"] == 0
                         and all(r["counterpart"] for r in x_main + s_main) and all(r["ok"] for r in allrows if r["counterpart"]))
    res.update(smoke=smoke, hashes=hashes, identity=ident, gate_pass=bool(smoke["pass"] and hashes["pass"] and ident["pass"]),
               rows=[{k: v for k, v in r.items() if k != "arrays"} for r in allrows])
    out_p.write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=1, default=str))


if __name__ == "__main__":
    main()
