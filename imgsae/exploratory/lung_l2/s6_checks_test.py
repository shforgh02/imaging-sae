"""Lung L2, step S6 part 1 (N4, "checks before any analysis"; protocol 11): the extraction gate on the merged main PC copy, root test.
The code of s3_checks_all.py (dev) for tiers T1 to T4 (T4 = variant pair), plus the identity check with lung L1:
- per tier: manifest rows; done series (a .json + .npz in main/ or pair/); logged failures; failures < 5%; file count = manifest rows minus
  logged failures (no row silently missing);
- z-fix completeness: every main file whose geo.zfix_needed is true has its zfix file, and no zfix file without its main file;
- G2b (ReLU of the pre-ReLU vector equals h exactly; hidden_fc on the pooled vector within 1e-3; logits from h and the head weights within
  1e-4) and G2c (calibrated probabilities from the member logits and the calibrator within 1e-4) on every saved file (main, zfix, pair);
- identity: the calibrated probabilities (6 years) of the re-extracted main series equal the L1 scores (lung_l1/results/scores.csv,
  5,412 test series) within 1e-4 for >= 99% of the L1 series (a series missing in L2 counts as not equal).
No outcome is read (the L1 file holds scores only).
usage (venv python): python s6_checks_test.py <main l2 copy> <manifest_test csv> <L1 scores csv> <out json>
"""
import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s2_pilot_checks as P2  # noqa: E402

TOL_ID = 1e-4


def main():
    vol, man_p, l1_p, out_p = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4])
    M = pd.read_csv(man_p, dtype={"pid": str}); heads = P2.load_heads(vol / "run_info" / "heads.npz")
    cal = json.load(open(vol / "run_info" / "sybil_ensemble_simple_calibrator.json")); root = vol / "test"
    done = {v: {Path(j).stem for j in glob.glob(str(root / v / "*.json")) if Path(j[:-5] + ".npz").exists()} for v in ("main", "zfix", "pair")}
    errs = {Path(j).stem for j in glob.glob(str(root / "errors" / "*.json"))}
    res = dict(copy=str(vol), root="test", tiers={})
    for t, g in M.groupby("tier"):
        v = "pair" if t == "T4" else "main"; rows = set(g.series_uid); d = rows & done[v]; failed = (rows - d) & errs; missing = rows - d - errs
        res["tiers"][t] = dict(variant=v, manifest_rows=len(rows), done=len(d), logged_failures=len(failed), silently_missing=len(missing),
                               failure_share=len(failed) / len(rows), pass_failures=bool(len(failed) / len(rows) < 0.05),
                               pass_counts=bool(len(d) == len(rows) - len(failed) and not missing), missing_examples=sorted(missing)[:5],
                               failure_messages=sorted({json.load(open(root / "errors" / f"{u}.json")).get("error", "")[:120] for u in failed})[:10])
    extra = {v: sorted(done[v] - set(M.series_uid)) for v in done}
    res["files_not_in_manifest"] = {v: len(x) for v, x in extra.items()}
    need = set()
    for u in done["main"]:
        if json.load(open(root / "main" / f"{u}.json")).get("geo", {}).get("zfix_needed"): need.add(u)
    res["zfix"] = dict(needed=len(need), present=len(done["zfix"]), needed_but_missing=len(need - done["zfix"]), zfix_without_main=len(done["zfix"] - done["main"]),
                       by_tier={t: int(len(set(g.series_uid) & done["zfix"])) for t, g in M.groupby("tier")},
                       pass_=bool(not (need - done["zfix"]) and not (done["zfix"] - done["main"])))
    worst = dict(relu=0.0, hid=0.0, logit=0.0, raw=0.0, mean=0.0, calib=0.0); nfail_b, nfail_c, n, fails = 0, 0, 0, []
    tier = dict(zip(M.series_uid, M.tier)); per_tier = {}; calib_main = {}
    for v in ("main", "zfix", "pair"):
        for u in sorted(done[v]):
            rec = json.load(open(root / v / f"{u}.json")); arr = np.load(root / v / f"{u}.npz")
            a, b, c, d = P2.recompute(arr, heads); mp = (1 / (1 + np.exp(-arr["logit"].astype(np.float64)))).mean(0)
            dm = float(np.abs(mp - np.array(rec["mean_prob"])).max()); dc = float(np.abs(np.array(P2.calibrate(cal, mp)) - np.array(rec["calib"])).max())
            for k, x in zip(worst, (a, b, c, d, dm, dc)): worst[k] = max(worst[k], x)
            okb, okc = (a == 0.0 and b <= 1e-3 and c <= 1e-4), dc <= 1e-4; nfail_b += not okb; nfail_c += not okc; n += 1
            key = f"{tier.get(u, '?')}_{v}"; per_tier[key] = per_tier.get(key, 0) + 1
            if not (okb and okc): fails.append(dict(variant=v, uid=u, relu=a, hidden_fc=b, logits=c, calib=dc))
            if v == "main": calib_main[u] = np.array(rec["calib"], float)
    res["G2b"] = dict(n_files=n, max_abs=dict(relu_vs_h=worst["relu"], hidden_fc=worst["hid"], logits=worst["logit"], raw_hazards=worst["raw"]), n_fail=nfail_b, pass_=nfail_b == 0)
    res["G2c"] = dict(n_files=n, max_abs_mean_prob=worst["mean"], max_abs_calib=worst["calib"], n_fail=nfail_c, pass_=nfail_c == 0)
    res["files_checked_by_tier_variant"] = per_tier; res["failing_files"] = fails[:50]
    S = pd.read_csv(l1_p, dtype={"pid": str}); ycols = [f"y{t}" for t in range(1, 7)]; diffs = []
    for u, y in zip(S.series_uid, S[ycols].to_numpy(float)):
        diffs.append(float(np.abs(calib_main[u] - y).max()) if u in calib_main else np.inf)
    diffs = np.array(diffs); fin = diffs[np.isfinite(diffs)]
    res["identity_L1"] = dict(n_l1=int(len(S)), n_found=int(np.isfinite(diffs).sum()), n_within_1e4=int((diffs <= TOL_ID).sum()), share_within_1e4=float((diffs <= TOL_ID).mean()),
                              max_abs=float(fin.max()) if len(fin) else None, median_abs=float(np.median(fin)) if len(fin) else None,
                              n_exact_0=int((fin == 0).sum()), by_year={int(yr): dict(n=int((S.study_yr == yr).sum()), within=int(((S.study_yr == yr).to_numpy() & (diffs <= TOL_ID)).sum()))
                                                                       for yr in sorted(S.study_yr.unique())},
                              pass_=bool((diffs <= TOL_ID).mean() >= 0.99))
    res["gate_S6_extraction_pass"] = bool(all(x["pass_failures"] and x["pass_counts"] for x in res["tiers"].values()) and res["zfix"]["pass_"] and res["G2b"]["pass_"]
                                          and res["G2c"]["pass_"] and res["identity_L1"]["pass_"])
    out_p.write_text(json.dumps(res, indent=1)); print(json.dumps({k: v for k, v in res.items() if k != "failing_files"}, indent=1))


if __name__ == "__main__":
    main()
