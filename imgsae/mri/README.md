# imgsae/mri: prostate MRI (PI-CAI) leg

**Plan:** `docs/PLAN_PROSTATE_MRI_v1.md` (revision 4). **Current stage protocol:** `docs/MRI_M0M1_PROTOCOL.md`, fixed before running.

| File | What | Where it runs |
|---|---|---|
| `m0_split.py` | M0.1: patient-level dev / sealed split from the clinical sheet only → `data/split.json` | laptop |
| `cloud/m0_fetch_modal.py` | M0.2: PI-CAI images (Zenodo, MD5) and labels (pinned commit) → Modal volume `imgsae-picai` | Modal CPU |
| `m0_prep_lib.py` | M0.3 preprocessing functions: grid, crop, cells, lesions, QC metrics | used by the prep job |
| `cloud/m0_prep_modal.py` | M0.3: dev-half preprocessing, one study at a time, saved at once; QC images | Modal CPU |
| `tests/test_m0_prep.py` | Unit tests on synthetic data with known answers | laptop |

**Rules:**
- Only dev studies are opened before registration. The sealed half stays closed.
- Every Modal launch passes `exploratory/p1b_sanity/cloud/budget.py` and runs detached.
- Every finished unit is saved to the volume.
- QC images and arrays stay out of git (`.gitignore`).
