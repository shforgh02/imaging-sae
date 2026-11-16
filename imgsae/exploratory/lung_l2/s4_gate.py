"""Lung L2, S4 gate (docs/LUNG_L2_PROTOCOL.md 9.8): one table of all candidate hypotheses found on dev.
A candidate holds if: the effect is in the stated direction, the dev 95% interval excludes the null value, and the sign (relative to
the null) is the same in both dev halves. Direction '>' or '<' is stated in advance; '!=' (two-sided) takes the full-dev sign.
A feature-based candidate also needs at least one valid arm (protocol 9.5). Where protocol 9.7 gives a dev qualification (U1a, U1b,
U3), it is reported next to the 9.8 result and a hypothesis needs both. If no candidate holds: stop before any test spending (9.8).
Also checked (plan P4, review): no S4 script reads the lung L1 test-score file or any test file (source search for the patterns
below), and the assembled exam table holds dev participants only.
usage (venv python): python s4_gate.py <results dir> [--tag dev] [--K 64] [--assembled <dir>]
"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s4_common as S  # noqa: E402

SOURCES = ("q1a", "q1b_u", "q1c", "q1d", "q2", "u1a", "u2", "u3", "refs")
# built from pieces so that this file does not match its own patterns
PATTERNS = ["lung_" + "l1", "scores" + r"\.csv", "manifest_" + "test", r"[/\\]" + "test" + r"[/\\]", "exams_" + "test", "arrays_" + "test",
            r"grp\s*==\s*['\"]" + "test", r"root\s*=\s*['\"]" + "test"]


def judge(c, any_valid):
    est, lo, hi, a, b, nl, d = c.get("est"), c.get("lo"), c.get("hi"), c.get("half_a"), c.get("half_b"), c["null"], c["direction"]
    vals = [est, lo, hi, a, b]
    if any(v is None or (isinstance(v, float) and not np.isfinite(v)) for v in vals): return False, "missing value"
    if d == "!=": d = ">" if est > nl else "<"
    if d == ">": ok = est > nl and lo > nl and a > nl and b > nl
    else: ok = est < nl and hi < nl and a < nl and b < nl
    if not ok:
        why = []
        if not ((est > nl) if d == ">" else (est < nl)): why.append("direction")
        if not ((lo > nl) if d == ">" else (hi < nl)): why.append("interval includes null")
        if not (((a > nl) and (b > nl)) if d == ">" else ((a < nl) and (b < nl))): why.append("halves disagree")
        return False, "; ".join(why)
    if c.get("feature_based") and not any_valid: return False, "feature-based but no valid arm"
    return True, f"holds ({d})"


def qualification(R, tag, cid):
    try:
        if cid.startswith("U1a_"): return json.loads((R / f"s4_u1a_{tag}.json").read_text())["qualification"]["qualifies"]
        if cid.startswith("ZF_share") or cid.startswith("ZF_flag"): return json.loads((R / f"s4_q1d_{tag}.json").read_text())["zfix"]["D5"]["U1b_dev_qualifies"]
        if cid.startswith("U3_"): return json.loads((R / f"s4_u3_{tag}.json").read_text())["ratio_C_over_better"]["qualifies"]
    except (FileNotFoundError, KeyError): return None
    return None


def leak_check():
    files = sorted(set(HERE.glob("s4_*.py")) | {HERE / "l2_data.py", HERE / "s4_core.py"}); hits = []
    for f in files:
        for i, ln in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            for p in PATTERNS:
                if re.search(p, ln): hits.append(dict(file=f.name, line=i, pattern=p, text=ln.strip()[:160]))
    return dict(files_searched=[f.name for f in files], patterns=PATTERNS, hits=hits, pass_=not hits)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("results"); ap.add_argument("--tag", default="dev"); ap.add_argument("--K", type=int, default=64)
    ap.add_argument("--assembled"); a = ap.parse_args(); R = Path(a.results)
    arm, arms = S.primary_arm(R, a.tag, a.K); any_valid = any(r["valid"] for r in arms)
    rows, missing = [], []
    for s in SOURCES:
        p = R / f"s4_{s}_{a.tag}.json"
        if not p.exists(): missing.append(p.name); continue
        for c in json.loads(p.read_text()).get("candidates", []):
            ok, why = judge(c, any_valid); q = qualification(R, a.tag, c["id"])
            rows.append(dict(c, holds_9_8=ok, reason=why, dev_qualification=q, eligible=bool(ok and (q is None or q))))
    res = dict(tag=a.tag, K=a.K, sources_missing=missing, arms=arms, primary_arm=arm, any_valid_arm=any_valid, n_candidates=len(rows),
               n_hold=int(sum(r["holds_9_8"] for r in rows)), n_eligible=int(sum(r["eligible"] for r in rows)),
               n_eligible_not_partly_seen=int(sum(r["eligible"] and not r["partly_seen"] for r in rows)), leak_check=leak_check())
    if a.assembled:
        E = pd.read_csv(Path(a.assembled) / f"exams_{a.tag}.csv", dtype={"pid": str}, usecols=["pid", "grp"])
        info = json.loads((Path(a.assembled) / f"assemble_{a.tag}.json").read_text())
        res["data_check"] = dict(all_rows_dev=bool((E.grp == "dev").all()), root=info.get("root"), n_exams=int(len(E)), pass_=bool((E.grp == "dev").all() and info.get("root") == "dev"))
    res["gate_9_8"] = dict(something_holds=bool(res["n_eligible"] > 0),
                           decision="go to S5" if res["n_eligible"] > 0 else "STOP: no candidate holds; report plainly; fallback paper (protocol 9.8)")
    res["table"] = rows
    S.write(R, f"s4_gate_{a.tag}.json", res)
    md = ["| id | statistic | dir | null | est | 95% CI | halves | n | 9.8 | qual. | feature | partly seen | reason |", "|" + "---|" * 13]
    for r in rows:
        f = lambda v: "—" if v is None else (f"{v:.3g}" if isinstance(v, (int, float)) else str(v))
        n = r["counts"].get("exams", r["counts"].get("participants", "")) if isinstance(r["counts"], dict) else ""
        md.append(f"| {r['id']} | {r['statistic']} | {r['direction']} | {f(r['null'])} | {f(r['est'])} | [{f(r['lo'])}, {f(r['hi'])}] | {f(r['half_a'])} / {f(r['half_b'])} | {n} | "
                  f"{'yes' if r['holds_9_8'] else 'no'} | {f(r['dev_qualification'])} | {'yes' if r['feature_based'] else ''} | {'yes' if r['partly_seen'] else ''} | {r['reason']} |")
    (R / f"s4_gate_{a.tag}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"s4_gate: {res['n_candidates']} candidates, {res['n_hold']} hold 9.8, {res['n_eligible']} eligible; leak check pass {res['leak_check']['pass_']}; "
          f"missing sources {missing}")


if __name__ == "__main__":
    main()
