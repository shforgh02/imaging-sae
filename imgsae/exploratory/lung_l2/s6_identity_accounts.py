"""Lung L2, step S6 part 1 (N4; frozen run plan "identity check" on forghanishayan; protocol 16a, amendment A4): the two S6 accounts give the
same numbers. Both smoke runs scored rows 0-2 of T1 into root test on their own volumes; this compares them file by file.
Pass marks (all must hold), as in p2_identity.py:
  each smoke: demo case within 0.005 of the published scores, demo volume equal to Serie.get_volume(), 3 of 3 test volumes equal to
  Sybil's own, 3 done, no error; checkpoint SHA-256 (all files) equal to the main account's record (results/runs/smoke.json); head
  weights SHA-256 = ba2d6d85...009bac on both; heads and calibrator files on the PC equal to the frozen input hashes;
  identity: every main (and z-fix, if any) file of root test on one account has its counterpart on the other, with calibrated
  probabilities within 1e-4 and h within 1e-4 (max abs). Other arrays, the image measures, tags and geometry are reported.
usage (venv python): python s6_identity_accounts.py <armanfo l2 copy> <forghanishayan l2 copy> <armanfo smoke json> <forghanishayan smoke json>
                     <main smoke json> <out json>
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p2_identity as P  # noqa: E402

CAL_FROZEN = "74cedae39715fa1ca29ebad881790432639d39fd0a3cf811529ebce9a767393a"


def smoke_marks(s, main):
    b = s.get("bench", {})
    d = dict(gpu=s.get("gpu"), tier=s.get("tier"), root=s.get("root"), demo_maxdiff=s["demo_maxdiff"], demo_volume_equal_serie=s["demo_volume_equal_serie"],
             demo_official_vs_l2=max(abs(x - y) for x, y in zip(s["demo_official_predict"], s["demo_scores"])),
             test_volumes_equal=[v["equal"] for v in b.get("verify", [])], n_done=b.get("n_done"), errors=b.get("errors"),
             ckpt_equal_main=s["ckpt_sha256"] == main["ckpt_sha256"], heads_sha256=s["heads_sha256"], sybil_commit_equal=s["sybil_commit"] == main["sybil_commit"])
    d["pass"] = bool(s["demo_maxdiff"] <= 0.005 and s["demo_pass"] and s["demo_volume_equal_serie"] and d["test_volumes_equal"] == [True] * 3 and b.get("n_done") == 3
                     and not b.get("errors") and d["ckpt_equal_main"] and s["heads_sha256"] == P.HEADS_MAIN and d["sybil_commit_equal"] and s.get("root") == "test")
    return d


def main():
    A, F, sa_p, sf_p, sm_p, out_p = (Path(x) for x in sys.argv[1:7])
    sa, sf, sm = (json.load(open(p)) for p in (sa_p, sf_p, sm_p))
    res = dict(files=dict(armanfo_copy=str(A), forghanishayan_copy=str(F), armanfo_smoke=str(sa_p), forghanishayan_smoke=str(sf_p), main_smoke=str(sm_p)))
    res["smoke"] = dict(armanfo=smoke_marks(sa, sm), forghanishayan=smoke_marks(sf, sm),
                        demo_armanfo_vs_forghanishayan=max(abs(x - y) for x, y in zip(sa["demo_scores"], sf["demo_scores"])))
    files = {}
    for acc, C in (("armanfo", A), ("forghanishayan", F)):
        files[acc] = dict(heads=P.sha(C / "run_info" / "heads.npz"), calibrator=P.sha(C / "run_info" / "sybil_ensemble_simple_calibrator.json"))
    files["pass"] = bool(all(v["heads"] == P.HEADS_MAIN and v["calibrator"] == CAL_FROZEN for k, v in files.items() if k != "pass"))
    res["pc_files"] = files
    rows = []
    for v in ("main", "zfix"):
        rows += P.compare(A / "test", F / "test", v)
    back = [r for v in ("main", "zfix") for r in P.compare(F / "test", A / "test", v)]   # nothing on one side only
    res["identity"] = dict(main=P.summary([r for r in rows if r["variant"] == "main"]), zfix=P.summary([r for r in rows if r["variant"] == "zfix"]),
                           uids=sorted(r["uid"] for r in rows if r["variant"] == "main"), n_reverse=len(back), reverse_all_have_counterpart=all(r["counterpart"] for r in back))
    res["identity"]["pass"] = bool(res["identity"]["main"]["n"] == 3 and all(r["counterpart"] and r["ok"] for r in rows) and res["identity"]["reverse_all_have_counterpart"]
                                   and len(back) == len(rows))
    res["gate_pass"] = bool(res["smoke"]["armanfo"]["pass"] and res["smoke"]["forghanishayan"]["pass"] and files["pass"] and res["identity"]["pass"])
    res["rows"] = [{k: v for k, v in r.items() if k != "arrays"} | dict(arrays=r.get("arrays")) for r in rows]
    out_p.write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=1, default=str))


if __name__ == "__main__":
    main()
