"""Lung L2, step S6 (N5): run rules 1 and 3 of the lead's OK (docs/EXECUTION_LOG.md, entry "step N3 done", 2026-11-17).
--pre <assembled dir> <s6_checks_test.json> <out json>   (before s6_frozen_analysis.py runs on test)
  rule 1, NaN guard: G2b and G2c passed on every file (s6_checks_test.json); no missing or non-finite value in exams_test.csv for the main
          exams (ratio, F1, s1) and in the z-fix and pair tables as the frozen analysis loads them (s4_q1d.variant_frame: v_l1, v_l6, s1).
          Also reported (not marks): non-finite values in the main logits and `pooled`, and in the variant `pooled`.
  rule 3a: no file of the hash table in HYPOTHESES_L2.md changed since the freeze c3578c3 (git diff c3578c3 HEAD, and no uncommitted change);
  rule 3b: assemble_test.json shows form_params_sha256 = b4cba3aa... (the CRLF working copy of the frozen LF hash 02ec7c2d...).
--post <s6_test.json> <out json>   (after N5)
  rule 3c: check_max_abs_lbar1_from_pooled_minus_saved <= 5e-3 (the stop rule of r1_arms.load), else H6 counts as not evaluated;
  reading rule of rule 1: a family hypothesis whose estimate or p is not a finite number counts as "not evaluated" (not confirmed).
No outcome is read: exams_test.csv is read with the four columns above only.
usage (venv python): python s6_input_checks.py --pre <A> <checks json> <out json> | --post <s6_test.json> <out json>
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import s4_q1d as QD  # noqa: E402

FREEZE = "c3578c3"; FORM_CRLF = "b4cba3aa14c79a2cc6a45a315348e289ada862fb7fce47cebb4b219af3826806"; TOL_LBAR = 5e-3


def bad(x): return int((~np.isfinite(pd.to_numeric(pd.Series(np.asarray(x).ravel()), errors="coerce").to_numpy(float))).sum())


def hash_table_files():
    txt = (HERE / "HYPOTHESES_L2.md").read_text(encoding="utf-8"); part = txt[txt.index("## SHA-256 of the frozen and analysis files"):]
    out = []
    for m in re.finditer(r"^\| `([^`]+)`", part, flags=re.M):
        p = m.group(1)
        if p.startswith("lung_l2_vol/") or p.startswith("lung_l2/r/"): continue   # PC-only inputs (hash-checked by the frozen analysis or below)
        out.append((HERE / p).resolve().relative_to(Path(r"D:\Shayan")).as_posix())
    return out


def pre(A, checks_p, out_p):
    C = json.loads(Path(checks_p).read_text()); res = dict(mode="pre", assembled=str(A))
    E = pd.read_csv(A / "exams_test.csv", usecols=["series_uid", "ratio", "F1", "s1"])
    r1 = dict(G2b_pass=bool(C["G2b"]["pass_"]), G2c_pass=bool(C["G2c"]["pass_"]), main_exams=int(len(E)), main_missing={c: bad(E[c]) for c in ("ratio", "F1", "s1")})
    Z = np.load(A / "arrays_test_main.npz", allow_pickle=True); r1["main_arrays_nonfinite"] = dict(logit=bad(Z["logit"]), pooled=bad(Z["pooled"]), h=bad(Z["h"]))
    for var in ("zfix", "pair"):
        V, Hv = QD.variant_frame(A, "test", var)
        if V is None: r1[var] = dict(rows=0, note="no table"); continue
        zz = np.load(A / f"arrays_test_{var}.npz", allow_pickle=True)
        r1[var] = dict(rows=int(len(V)), missing={c: bad(V[c]) for c in ("v_l1", "v_l6", "s1")}, pooled_nonfinite=bad(zz["pooled"]), h_nonfinite=bad(Hv))
    marks = [r1["main_missing"][c] for c in r1["main_missing"]] + [n for v in ("zfix", "pair") if "missing" in r1[v] for n in r1[v]["missing"].values()]
    r1["pass"] = bool(r1["G2b_pass"] and r1["G2c_pass"] and not any(marks)); res["rule1_nan_guard"] = r1
    files = hash_table_files()
    changed = subprocess.run(["git", "diff", "--name-only", FREEZE, "HEAD"], cwd=r"D:\Shayan", capture_output=True, text=True).stdout.split()
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=r"D:\Shayan", capture_output=True, text=True).stdout.splitlines()
    dirty = [ln[3:].strip() for ln in dirty]
    res["rule3a_hash_table_untouched"] = dict(n_files=len(files), changed_since_freeze=sorted(set(files) & set(changed)), uncommitted=sorted(set(files) & set(dirty)),
                                             pass_=not (set(files) & set(changed)) and not (set(files) & set(dirty)))
    asm = json.loads((A / "assemble_test.json").read_text())
    res["rule3b_form_hash"] = dict(form_params_sha256=asm.get("form_params_sha256"), expected=FORM_CRLF, pass_=asm.get("form_params_sha256") == FORM_CRLF)
    res["pass"] = bool(r1["pass"] and res["rule3a_hash_table_untouched"]["pass_"] and res["rule3b_form_hash"]["pass_"])
    Path(out_p).write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))
    raise SystemExit(0 if res["pass"] else 2)


def post(s6_p, out_p):
    R = json.loads(Path(s6_p).read_text()); c = R["check_max_abs_lbar1_from_pooled_minus_saved"]
    rows = [dict(id=h["id"], est_finite=h["est"] is not None and bool(np.isfinite(h["est"])), p_finite=h["p_one_sided"] is not None and bool(np.isfinite(h["p_one_sided"])),
                 confirmed_holm=h["confirmed_holm"], evaluated=h["evaluated"]) for h in R["hypotheses"]]
    for r in rows: r["counts_as"] = "not evaluated" if not (r["evaluated"] and r["est_finite"] and r["p_finite"]) else ("confirmed" if r["confirmed_holm"] else "not confirmed")
    res = dict(mode="post", s6=str(s6_p), rule3c=dict(check_max_abs_lbar1_from_pooled_minus_saved=c, tol=TOL_LBAR, pass_=bool(c <= TOL_LBAR),
                                                      consequence=None if c <= TOL_LBAR else "H6 counts as not evaluated"), reading_rule=rows)
    if c > TOL_LBAR:
        for r in rows:
            if r["id"] == "H6": r["counts_as"] = "not evaluated"
    Path(out_p).write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "--pre": pre(Path(sys.argv[2]), sys.argv[3], sys.argv[4])
    elif sys.argv[1] == "--post": post(sys.argv[2], sys.argv[3])
    else: raise SystemExit(__doc__)
