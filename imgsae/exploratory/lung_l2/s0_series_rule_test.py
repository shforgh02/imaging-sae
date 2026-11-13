"""Lung L2, step S0: test the series rule against the split file's test choices (metadata only; no outcome is read).
Choose the rule on half A of the test participants (seeded split), report agreement on half B and on all; then report coverage on dev.
Gate (plan section 4): on all test exams, the rule picks the split file's series, or one with the same kernel class and slice
thickness, for >= 90%.
usage: python s0_series_rule_test.py <nlst_series_meta.csv> <split pickle> <out_json>
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, r"D:\Shayan\imgsae\exploratory\lung_l0")
import nlst_l0 as L  # noqa: E402
import series_rule as R  # noqa: E402

meta_p, split_p, out_p = sys.argv[1:4]
m = R.load_meta(meta_p)
split = L.SafeUnpickler(open(split_p, "rb")).load()
grp = {str(k): str(v["split"]) for k, v in split.items()}
chosen = {u for k, v in split.items() if str(v["split"]) == "test" for u in v["exams"]}
m["grp"] = m.PatientID.map(grp).fillna("none")
T = m[m.grp == "test"]
ref = T[T.SeriesInstanceUID.isin(chosen)].set_index("StudyInstanceUID")
T = T[T.StudyInstanceUID.isin(ref.index)]
pids = np.array(sorted(T.PatientID.unique()))
rng = np.random.default_rng(0)
half_a = set(rng.choice(pids, len(pids) // 2, replace=False))


def agree(sel, studies):
    s = sel.set_index("StudyInstanceUID").reindex(studies)
    r = ref.reindex(studies)
    exact = (s.SeriesInstanceUID == r.SeriesInstanceUID)
    equiv = exact | ((s.kclass == r.kclass) & (s.thick == r.thick))
    covered = s.SeriesInstanceUID.notna()
    return dict(n=len(studies), covered=float(covered.mean()), exact=float(exact.mean()), equivalent=float(equiv.mean()))


res = {"n_test_studies_with_choice": int(len(ref)), "min_slices": R.MIN_SLICES, "rules": {}}
studies_a = ref.index[ref.PatientID.isin(half_a)]
studies_b = ref.index[~ref.PatientID.isin(half_a)]
for name in R.RULES:
    sel = R.select(T, name)
    res["rules"][name] = {"half_A": agree(sel, studies_a), "half_B": agree(sel, studies_b), "all": agree(sel, ref.index)}
best = max(R.RULES, key=lambda k: res["rules"][k]["half_A"]["exact"])
res["chosen_rule_on_half_A"] = best
res["gate_all_equivalent_ge_0.90"] = res["rules"][best]["all"]["equivalent"] >= 0.90
# where the chosen rule disagrees: what was picked instead
sel = R.select(T, best).set_index("StudyInstanceUID").reindex(ref.index)
bad = sel.SeriesInstanceUID != ref.SeriesInstanceUID
cmp = sel[bad][["Manufacturer", "ConvolutionKernel", "thick", "instanceCount"]].join(
    ref[bad][["ConvolutionKernel", "thick", "instanceCount"]], rsuffix="_ref")
res["disagreements"] = {"n": int(bad.sum()),
                        "by_manufacturer": cmp.Manufacturer.value_counts().to_dict(),
                        "top_patterns": cmp.astype(str).agg(" | ".join, axis=1).value_counts().head(15).to_dict()}
# selected test series thicker than 2.5 mm (outside Sybil's own training filter)
res["test_ref_thicker_than_2.5mm"] = int((ref.thick > 2.5).sum())
res["test_ref_by_kclass"] = ref.kclass.value_counts().to_dict()
# coverage on dev (exam = pid x study year): S1 gate is >= 95%
D = m[m.grp == "dev"]
ds = R.select(D, best)
n_dev_studies = D.StudyInstanceUID.nunique()
res["dev"] = {"ct_studies": int(n_dev_studies), "studies_with_selected_series": int(len(ds)),
              "coverage": float(len(ds) / n_dev_studies), "participants": int(ds.PatientID.nunique()),
              "study_yr": ds.study_yr.value_counts().sort_index().to_dict(),
              "dup_pid_year": int(ds.duplicated(["PatientID", "study_yr"]).sum()),
              "thicker_than_2.5mm": int((ds.thick > 2.5).sum()), "by_kclass": ds.kclass.value_counts().to_dict(),
              "by_manufacturer": ds.Manufacturer.value_counts().to_dict()}
# same check for the test reference for comparison of the two distributions
res["test_ref"] = {"by_manufacturer": ref.Manufacturer.value_counts().to_dict(),
                   "study_yr": ref.study_yr.value_counts().sort_index().to_dict()}
Path(out_p).write_text(json.dumps(res, indent=1, default=str))
print(json.dumps(res, indent=1, default=str))
