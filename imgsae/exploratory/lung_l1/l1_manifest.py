import sys, json, csv, random
sys.path.insert(0, r"D:\Shayan\imgsae\exploratory\lung_l0")
import nlst_l0
p = r"D:\Shayan\imgsae_data\nlst_public\Shetty_et_al(Google)_data_splits.p"
split = nlst_l0.SafeUnpickler(open(p, "rb")).load()
rows = []
for pid, v in split.items():
    if str(v["split"]) != "test": continue
    for uid, e in v["exams"].items():
        rows.append((uid, pid, int(e["cancer_in_1"])))
rows.sort()
print(len(rows), len({r[1] for r in rows}))
out = r"D:\Shayan\imgsae\exploratory\lung_l1\results\manifest_series.csv"
with open(out, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["series_uid", "pid", "cancer_in_1"]); w.writerows(rows)
