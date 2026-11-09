# Data kept out of git

Git holds all code, docs, logs and result tables (JSON / CSV / MD). The items below are too large for git, or are raw imaging data. They stay on the project PC (`D:\Shayan`); `.gitignore` lists them. Everything here can be rebuilt from public data with the scripts named.

| Path | Size | What | Rebuild with |
|---|---|---|---|
| `imgsae_data/totalseg/` | 4.9 GB | Raw TotalSegmentator v2 CTs and masks for the 150 development scans (public, Zenodo, CC-BY) | `imgsae/scripts/fetch_subset.py` (ids in `imgsae/data/p1_dev_ids.txt`) |
| `imgsae/data/p1/scans/` | 1.9 GB, 150 files | Per-scan token tables: CT-FM and untrained CT-FM features, reference features, occupancy | `imgsae/scripts/p1_encode.py` (see `imgsae/RUNBOOK.md`) |
| `imgsae/data/p1/perturb/` | 0.8 GB, 60 files | Re-encodes of 20 scans under shift / noise / HU-offset perturbations | `imgsae/scripts/p1_encode.py` (perturbation step) |
| `imgsae/data/p1/rows.npz` | 4.6 GB | All 1,021,303 tokens assembled, plus preprocessing parameters | `imgsae/scripts/p1_assemble.py` |
| `imgsae/exploratory/p1b_sanity/results/a1_cache_full/` | 0.5 GB | Cached out-of-fold probe predictions (A1) | `imgsae/exploratory/p1b_sanity/a1_probe_ladder.py` |
| `imgsae/exploratory/p1b_sanity/results/cache_refpos.npz` | 0.16 GB | Reference and position features in row order | `common.refpos()` (built on first use) |
| `imgsae/exploratory/p1b_sanity/cloud/stage/` | 2.0 GB | Copy of `rows.npz` cut down for upload to the Modal volume `imgsae-p1b` | `imgsae/exploratory/p1b_sanity/cloud/upload_p1.ps1` |
| `imgsae/.venv/` | 4.3 GB | Python environment | `imgsae/RUNBOOK.md` (Environment) and `imgsae/requirements-lock.txt` |

**Kept in git** (small and needed to read the results):
- `imgsae/data/p1/{concepts,gates,decision,spacing}.json`;
- `imgsae/data/p1/fit/` (per-feature tables and `summary.json`);
- the subject lists and SHA-256 sums in `imgsae/data/`.

**Sealed data.** The 555 confirmation scans (`imgsae/data/p2_conf_ids.txt`) have never been downloaded or used. They stay sealed until the v2 protocol is registered.

**Cloud copy.** The Modal volume `imgsae-p1b` holds the same `X_ctfm` rows, the perturbation files, `concepts.json` and `gates.json`. Spending is tracked in `imgsae/exploratory/p1b_sanity/cloud/ledger.json`.

**Local clinical data** (breast RT CT, CTA with MACE, vestibular schwannoma) are not part of this repository.
