# Imaging SAE: sparse autoencoders on medical imaging foundation models

Do sparse autoencoder (SAE) features on a 3D CT foundation model capture valid concepts? We ask for features that go beyond intensity and position, that beat simple baselines, and we ask whether reproducibility predicts validity. Validity is checked against dense segmentation masks (TotalSegmentator), perturbation robustness, and null encoders.

## Status (2026-11-09)
- **Phase 1** (pre-registered feasibility, 150 development scans): **NO-GO**. See `docs/DECISION_MEMO_P1.md`.
- **Post hoc checks** (`imgsae/exploratory/p1_checks/`) and **Phase 1b Stage A diagnostics** (`imgsae/exploratory/p1b_sanity/`) found that the failures were design problems:
  - organ-level concepts are saturated;
  - the SAE size rule was too dense and too short;
  - the chimera rule treated 'other' tissue as a foreign concept.
- **Plan v2**, which restarts the SAE paper, is **out for review**: **`docs/SAE_v2_REVIEW_PACKET.md`**. That one file has all results so far, the detailed tables, the full v2 plan, and questions for reviewers. No v2 work starts before approval.

## Where to look
| What | File |
|---|---|
| **Review packet: results + plan v2** | `docs/SAE_v2_REVIEW_PACKET.md` |
| Original plan (v1) and decision rules | `docs/IMAGING_SAE_LEAN_v1.md` |
| Phase 1 verdict | `docs/DECISION_MEMO_P1.md`, `imgsae/data/p1/decision.json`, `imgsae/data/p1/fit/summary.json` |
| Every decision and deviation, in order | `docs/EXECUTION_LOG.md` |
| Post hoc checks 1–3 | `imgsae/exploratory/p1_checks/README.md` |
| Stage A plan, results and code | `docs/SANITY_PLAN_v1.md`, `imgsae/exploratory/p1b_sanity/RESULTS.md`, `imgsae/exploratory/p1b_sanity/README.md` |
| Cloud runs and the Modal budget ledger | `imgsae/exploratory/p1b_sanity/cloud/README.md`, `cloud/ledger.json` |
| Current state of the work | `STATUS.md` |

## Layout
```
docs/                     plans, decision memo, execution log, review packet
imgsae/imgsae/            package: SAE, consensus, validity ladder, atlas, tokens, stats, CT-FM encoder
imgsae/scripts/           Phase 1 pipeline (select, fetch, encode, assemble, probe, fit, decide)
imgsae/tests/             unit tests (planted-truth checks)
imgsae/data/              subject lists and small result files (big arrays stay local: DATA.md)
imgsae/exploratory/       post hoc checks (p1_checks) and Stage A diagnostics (p1b_sanity), with logs and results
```

## Reproduce
- **Environment and Phase 1 pipeline:** `imgsae/RUNBOOK.md`, using Python 3.11 and `imgsae/requirements-lock.txt`.
- **Stage A:** run `powershell -File imgsae/exploratory/p1b_sanity/run_stageA.ps1`. Every script first reproduces an official Phase 1 number as a sanity row.
- **Large inputs** are not in git. `DATA.md` lists them and how to rebuild them from public TotalSegmentator data.
