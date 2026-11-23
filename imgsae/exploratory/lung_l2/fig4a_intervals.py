"""Figure 4 panel (a): intervals of the mean z-fix change of Sybil's 1-year and 6-year logit, as Sybil gives it (from `pooled`) and with
shared axis 0 of `pooled` set to its dev mean in every member. Descriptive (plan: docs/EXECUTION_LOG.md, 23 Nov, committed before this ran).
Uses the frozen S6 functions unchanged (s6_frozen_analysis.py; its hash check of the frozen files runs first); same T5 exams, same
participant bootstrap (2,000 draws, seed 0). Nothing is fitted.
usage (venv python, from this folder): python fig4a_intervals.py <assembled dir> <root: dev|test> <frozen dir (results/s5)> <run_info dir> <out json>
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import s6_frozen_analysis as F  # noqa: E402


def main():
    A, root, FZ, RI, out_p = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5])
    T, arms, fams, lab_of, FI, COMB, AX = F.load_frozen(FZ, RI); th = T["thresholds"]
    E, H, X = F.load_root(A, root); heads = F.S.C.load_heads(RI / "heads.npz"); fc = F.AXF.load_fc(RI / "heads.npz")
    rowpos = {u: i for i, u in enumerate(E.series_uid)}
    LP = F.logits_pooled(X, fc, heads); LP_off = F.logits_pooled(X, fc, heads, AX, [0])
    # the T5 exams exactly as in s6_frozen_analysis.main
    Z, _ = F.QD.variant_frame(A, root, "zfix")
    J = E.merge(Z[["series_uid", "v_l1", "v_l6", "s1", "s6"]].rename(columns={"s1": "v_s1", "s6": "v_s6"}), on="series_uid")
    J = J[J.ratio <= th["zfix_ratio_max"]].reset_index(drop=True); pid = J.pid.to_numpy()
    mi = np.array([rowpos[u] for u in J.series_uid]); Hz, Xz = F.variant_arrays(A, root, "zfix", J.series_uid)
    Lz, Lm = F.logits_pooled(Xz, fc, heads), LP[mi]; Lz_off, Lm_off = F.logits_pooled(Xz, fc, heads, AX, [0]), LP_off[mi]
    res = dict(root=root, plan="docs/EXECUTION_LOG.md, 2026-11-23, Figure 4 panel (a)", counts=dict(exams=int(len(J)), participants=int(J.pid.nunique())),
               bootstrap="S6 boot_stat: participant bootstrap, 2,000 draws, seed 0, 2.5/97.5 percentiles")
    for t, k in ((0, "lbar1"), (5, "lbar6")):
        d_plain = Lz[:, :, t].mean(1) - Lm[:, :, t].mean(1); d_off = Lz_off[:, :, t].mean(1) - Lm_off[:, :, t].mean(1)
        res[f"delta_{k}_as_sybil"] = F.boot_stat(lambda s, v=d_plain: float(v[s].mean()), pid)
        res[f"delta_{k}_axis0_off"] = F.boot_stat(lambda s, v=d_off: float(v[s].mean()), pid)
        res[f"delta_{k}_axis0_carried"] = F.boot_stat(lambda s, v=d_off - d_plain: float(v[s].mean()), pid)
        res[f"share_exams_abs_delta_{k}_ge_quarter_sd"] = dict(
            as_sybil=float((np.abs(d_plain) >= 0.25 * th[f"sd_ref_{k}_all_dev_main"]).mean()) if f"sd_ref_{k}_all_dev_main" in th else None,
            axis0_off=float((np.abs(d_off) >= 0.25 * th[f"sd_ref_{k}_all_dev_main"]).mean()) if f"sd_ref_{k}_all_dev_main" in th else None)
    out_p.parent.mkdir(parents=True, exist_ok=True); out_p.write_text(json.dumps(res, indent=1))
    print(json.dumps({k: (v["est"] if isinstance(v, dict) and "est" in v else v) for k, v in res.items() if k.startswith("delta")}, indent=1))


if __name__ == "__main__":
    main()
