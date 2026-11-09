"""merge cloud results saved on the volume (fetched by s1a_collect.ps1) into results/s1a_sae.json + results/tables/, skipping rows already there.
usage: ..\\..\\.venv\\Scripts\\python cloud\\s1a_merge.py <folder with <name>_rep<r>.json files>"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import s1a_lib as L  # noqa: E402

path = L.RES / "s1a_sae.json"; res = json.load(open(path)) if path.exists() else {}; n = 0
for f in sorted(Path(sys.argv[1]).rglob("*_rep*.json")):
    d = json.load(open(f)); r = d["result"]; key = f"{r['method']}_rep{r['rep']}"
    if key in res: continue
    L.save_tables(r["method"], r["rep"], {h: {k: np.asarray(v) for k, v in T.items()} for h, T in d["tables"].items()})
    r["where"]["collected_from_volume"] = True; res[key] = r; n += 1; print(f"merged {key}: matched neutral {r['area_matched_neutral']:.3f}")
json.dump(res, open(path, "w"), indent=1); print(f"{n} merged; {len(res)} rows in {path.name}")
