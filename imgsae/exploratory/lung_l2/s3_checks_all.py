"""Lung L2, S3 gate on the merged main PC copy (protocol 7, 8; plan P3 item 7): every dev tier D1 to D4.
Per tier: manifest rows; done series (a .json + .npz in main/ or pair/); logged failures (errors/<uid>.json of a row that is not done);
failures < 5%; file count = manifest rows minus logged failures (no row may be silently missing); z-fix completeness (every main file
whose geo.zfix_needed is true has its zfix file, and no zfix file without its main file).
G2b (ReLU of the pre-ReLU vector equals h exactly; hidden_fc on the pooled vector within 1e-3; logits from h and the head weights
within 1e-4) and G2c (calibrated probabilities from the member logits and the calibrator within 1e-4) on every saved file
(main, zfix, pair), with the code of s2_pilot_checks.py.
usage (venv python): python s3_checks_all.py <main l2 copy> <manifest csv> <out json>
"""
import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s2_pilot_checks as P2  # noqa: E402


def main():
    vol, man_p, out_p = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    M = pd.read_csv(man_p, dtype={"pid": str}); heads = P2.load_heads(vol / "run_info" / "heads.npz")
    cal = json.load(open(vol / "run_info" / "sybil_ensemble_simple_calibrator.json")); dev = vol / "dev"
    done = {v: {Path(j).stem for j in glob.glob(str(dev / v / "*.json")) if Path(j[:-5] + ".npz").exists()} for v in ("main", "zfix", "pair")}
    errs = {Path(j).stem for j in glob.glob(str(dev / "errors" / "*.json"))}
    res = dict(copy=str(vol), tiers={})
    for t, g in M.groupby("tier"):
        v = "pair" if t == "D4" else "main"; rows = set(g.series_uid); d = rows & done[v]; failed = (rows - d) & errs; missing = rows - d - errs
        res["tiers"][t] = dict(variant=v, manifest_rows=len(rows), done=len(d), logged_failures=len(failed), silently_missing=len(missing),
                               failure_share=len(failed) / len(rows), pass_failures=bool(len(failed) / len(rows) < 0.05),
                               pass_counts=bool(len(d) == len(rows) - len(failed) and not missing), missing_examples=sorted(missing)[:5])
    # z-fix completeness
    need, nz = set(), 0
    for u in done["main"]:
        r = json.load(open(dev / "main" / f"{u}.json"))
        if r.get("geo", {}).get("zfix_needed"): need.add(u)
    res["zfix"] = dict(needed=len(need), present=len(done["zfix"]), needed_but_missing=len(need - done["zfix"]), zfix_without_main=len(done["zfix"] - done["main"]),
                       by_tier={t: int(len(set(g.series_uid) & done["zfix"])) for t, g in M.groupby("tier")},
                       pass_=bool(not (need - done["zfix"]) and not (done["zfix"] - done["main"])))
    # G2b / G2c on every saved file
    worst = dict(relu=0.0, hid=0.0, logit=0.0, raw=0.0, mean=0.0, calib=0.0); nfail_b, nfail_c, n, fails = 0, 0, 0, []
    tier = dict(zip(M.series_uid, M.tier)); per_tier = {}
    for v in ("main", "zfix", "pair"):
        for u in sorted(done[v]):
            rec = json.load(open(dev / v / f"{u}.json")); arr = np.load(dev / v / f"{u}.npz")
            a, b, c, d = P2.recompute(arr, heads); mp = (1 / (1 + np.exp(-arr["logit"].astype(np.float64)))).mean(0)
            dm = float(np.abs(mp - np.array(rec["mean_prob"])).max()); dc = float(np.abs(np.array(P2.calibrate(cal, mp)) - np.array(rec["calib"])).max())
            for k, x in zip(worst, (a, b, c, d, dm, dc)): worst[k] = max(worst[k], x)
            okb, okc = (a == 0.0 and b <= 1e-3 and c <= 1e-4), dc <= 1e-4; nfail_b += not okb; nfail_c += not okc; n += 1
            key = f"{tier.get(u, '?')}_{v}"; per_tier[key] = per_tier.get(key, 0) + 1
            if not (okb and okc): fails.append(dict(variant=v, uid=u, relu=a, hidden_fc=b, logits=c, calib=dc))
    res["G2b"] = dict(n_files=n, max_abs=dict(relu_vs_h=worst["relu"], hidden_fc=worst["hid"], logits=worst["logit"], raw_hazards=worst["raw"]), n_fail=nfail_b, pass_=nfail_b == 0)
    res["G2c"] = dict(n_files=n, max_abs_mean_prob=worst["mean"], max_abs_calib=worst["calib"], n_fail=nfail_c, pass_=nfail_c == 0)
    res["files_checked_by_tier_variant"] = per_tier; res["failing_files"] = fails[:50]
    res["gate_S3_pass"] = bool(all(x["pass_failures"] and x["pass_counts"] for x in res["tiers"].values()) and res["zfix"]["pass_"] and res["G2b"]["pass_"] and res["G2c"]["pass_"])
    out_p.write_text(json.dumps(res, indent=1)); print(json.dumps({k: v for k, v in res.items() if k != "failing_files"}, indent=1))


if __name__ == "__main__":
    main()
