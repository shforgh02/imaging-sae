"""Lung L2, plan O2, part O2c (docs/O2_PLAN.md; frozen before any O2 scan is scored): the small "form" check on the NLST participants
Sybil never used. DESCRIPTIVE SECONDARY (no hypothesis; about 29 one-year cancers, so the interval of Sybil minus the form is about
+-0.10). Runs only after the O2a + O2b output (o2_analysis.py) is committed.
Case-control design (AUROC does not depend on the sampling fraction): cases = scored exams with a lung cancer within 1 year (y1 = 1;
all exams, years 0-2, of the unseen participants with a cancer are in the list); controls = exams of the random sample (800 exams, seed
1, drawn by o2_manifest.py before any outcome was read) with y1 = 0. Also 6 years on baseline screens (cases y6 = 1 at baseline;
controls: baseline exams of the random sample with y6 = 0), reported only with >= 10 cancers.
Scores: Sybil s1 / s6 as published (main run); C1 the frozen form F1 / F6 (results/l2_form_params.json); C2 findings only (X1's model,
fitted on Sybil's train participants only: s7_added_value.comparators). Participant bootstrap 2,000, seed 0.
--dry-dev: the same code on dev (random 800 dev exams, seed 1; dev cancers) as a code check before the freeze; not a result.
usage (venv python): python o2_form.py <manifest csv> <out json> --copies <l2 dir>[,...] --root unseen|dev [--dry-dev] [--tables ...] [--split ...]
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
import s4_common as S  # noqa: E402
import s7_added_value as X1  # noqa: E402

N_RANDOM, SEED_RANDOM = 800, 1


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("manifest"); ap.add_argument("out"); ap.add_argument("--copies", required=True); ap.add_argument("--root", default="unseen")
    ap.add_argument("--dry-dev", action="store_true"); ap.add_argument("--tables", default=r"D:\Shayan\imgsae_data\nlst_public\tables")
    ap.add_argument("--split", default=r"D:\Shayan\imgsae_data\nlst_public\Shetty_et_al(Google)_data_splits.p"); a = ap.parse_args()
    M = pd.read_csv(a.manifest, dtype={"pid": str}, low_memory=False); M = M[M.variant == "main"]
    if a.dry_dev:
        M = M[M.tier.isin(["D1", "D2", "D3"])]; rnd = set(M.sample(n=N_RANDOM, random_state=SEED_RANDOM).series_uid)
    else:
        info = json.loads((HERE / "results/o2_manifest.json").read_text()); rnd = None   # the random sample is rebuilt below and checked against its hash
    rec = {}
    for c in a.copies.split(","):
        for j in glob.glob(str(Path(c) / a.root / "main" / "*.json")):
            u = Path(j).stem
            if u not in rec: rec[u] = json.load(open(j))
    b = L.build(a.tables, a.split); CM = X1.comparators(b); X = b["X"].copy(); X["pid"] = X.pid.astype(str)
    P = json.loads((HERE / "results/l2_form_params.json").read_text()); X["F1"] = l2_form.predict_logit(P["F1"], X); X["F6"] = l2_form.predict_logit(P["F6"], X)
    X = X1.scores(X, CM)
    E = pd.DataFrame([dict(series_uid=u, pid=str(r["pid"]), study_yr=int(r["study_yr"]), s1=r["calib"][0], s6=r["calib"][5]) for u, r in rec.items() if u in set(M.series_uid)])
    E = E.merge(X[["pid", "study_yr", "y1", "y6", "F1", "F6", "C2_1", "C2_6"]], on=["pid", "study_yr"], how="left")
    if rnd is None:   # the same draw as the list (o2_manifest.py: seed 1 over the whole selection), checked against the committed hash
        import hashlib
        from o2_manifest import N_RANDOM as NR, selection
        _, sel = selection(r"D:\Shayan\imgsae_data\idc_index_25.0.5\nlst_series_meta.csv", a.split); rnd = set(sel.sample(n=NR, random_state=1).SeriesInstanceUID)
        if hashlib.sha256("\n".join(sorted(rnd)).encode()).hexdigest() != info["random_sample_for_U3"]["sha256_of_uids"]: raise SystemExit("REFUSED: random sample differs from the list")
    E["random"] = E.series_uid.isin(rnd)
    res = dict(label=("DRY CHECK on dev (code check before the O2 freeze; not a result)" if a.dry_dev else "O2c form check (descriptive secondary; plan docs/O2_PLAN.md)"),
               scored_exams=int(len(E)), random_sample_scored=int(E.random.sum()), random_sample_size=len(rnd))
    for ep, y, s, c1, c2, base in (("E1_1year_all_screens", "y1", "s1", "F1", "C2_1", False), ("E4_6years_baseline", "y6", "s6", "F6", "C2_6", True)):
        Q = E[E[y].notna() & ((E.study_yr == 0) if base else True)]
        Q = Q[(Q[y] == 1) | (Q.random & (Q[y] == 0))].reset_index(drop=True); yy = Q[y].to_numpy(int); n_c = int(yy.sum())
        o = dict(counts=dict(exams=int(len(Q)), participants=int(Q.pid.nunique()), cancers=n_c, controls=int((yy == 0).sum())))
        if n_c >= 10 and (yy == 0).sum() >= 10:
            bt = S.Boot(Q.pid.to_numpy()); sy = S.logit(Q[s]); f1, f2 = Q[c1].to_numpy(float), Q[c2].to_numpy(float)
            o.update(auroc_sybil=S.auc_ci(yy, sy, bt), auroc_form_C1=S.auc_ci(yy, f1, bt), auroc_findings_C2=S.auc_ci(yy, f2, bt),
                     sybil_minus_form=S.dauc_ci(yy, sy, f1, bt), sybil_minus_findings=S.dauc_ci(yy, sy, f2, bt))
        else: o["note"] = "fewer than 10 cancers or controls: no AUROC"
        res[ep] = o
    out_p = Path(a.out); out_p.parent.mkdir(parents=True, exist_ok=True); out_p.write_bytes((json.dumps(res, indent=1, default=float) + "\n").encode("utf-8"))
    print(json.dumps({k: (v["counts"] if isinstance(v, dict) and "counts" in v else v) for k, v in res.items()}, default=float))


if __name__ == "__main__":
    main()
