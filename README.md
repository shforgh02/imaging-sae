# Imaging SAE: clinically meaningful sparse-autoencoder features from imaging foundation models

**Goal:** find sparse autoencoder (SAE) features of an imaging foundation model that mark disease, are stable and not shortcuts, add information beyond standard clinical data, and are recognised by radiologists. The first clinical target is prostate cancer on MRI (PI-CAI).

**Reviewers: start with [`docs/BRIEFING_FOR_REVIEWERS.md`](docs/BRIEFING_FOR_REVIEWERS.md).**

## Status (2026-11-10)
- **CT work (method test bench; TotalSegmentator, CT-FM, 150 dev scans): done and stopped before confirmation.**
  - Phase 1 was NO-GO, because of design faults.
  - Stage 1a then passed its gate: the SAE beats equally tuned baselines by +0.10 in coverage area.
  - Normal organs are not a clinical question, and the dataset has no tumour outlines. So the 555 sealed scans stay unused.
- **Next: prostate MRI (PI-CAI).** The plan [`docs/PLAN_PROSTATE_MRI_v1.md`](docs/PLAN_PROSTATE_MRI_v1.md) is out for review. Nothing has been run or downloaded for it yet.

## Where to look
| What | File |
|---|---|
| **Briefing for reviewers** (what happened, why CT stops, what we ask) | `docs/BRIEFING_FOR_REVIEWERS.md` |
| **Prostate MRI plan** | `docs/PLAN_PROSTATE_MRI_v1.md` |
| Current state of the work | `STATUS.md` |
| Every decision and deviation, in order | `docs/EXECUTION_LOG.md` |
| Original plan (v1) and Phase 1 verdict | `docs/IMAGING_SAE_LEAN_v1.md`, `docs/DECISION_MEMO_P1.md` |
| Stage A and plan v2 | `docs/SANITY_PLAN_v1.md`, `docs/SAE_v2_REVIEW_PACKET.md`, `imgsae/exploratory/p1b_sanity/RESULTS.md` |
| Stage 1a protocol and results | `docs/REVIEW_AND_PROPOSAL_v2.md`, `docs/STAGE1A_PROTOCOL.md`, `imgsae/exploratory/v2_ct/RESULTS_S1A.md` |
| CT confirmation protocol (archived, not registered), its review and our reply | `docs/SAE_PROTOCOL_v2.md`, `docs/REVIEW_PROTOCOL_v2.md`, `docs/RESPONSE_REVIEW_PROTOCOL_v2.md` |
| Cloud runs and the Modal budget ledger | `imgsae/exploratory/p1b_sanity/cloud/README.md`, `cloud/ledger.json` |

## Layout
```
docs/                     plans, protocols, reviews, decision memo, execution log
imgsae/imgsae/            package: SAE, consensus, validity ladder, atlas, tokens, stats, CT-FM encoder
imgsae/scripts/           Phase 1 pipeline (select, fetch, encode, assemble, probe, fit, decide)
imgsae/tests/             unit tests (planted-truth checks)
imgsae/data/              subject lists and small result files (big arrays stay local: DATA.md)
imgsae/exploratory/       post hoc checks (p1_checks), Stage A (p1b_sanity), Stage 1a (v2_ct), with logs and results
```

## Reproduce
- **Environment and Phase 1 pipeline:** `imgsae/RUNBOOK.md`, using Python 3.11 and `imgsae/requirements-lock.txt`.
- **Stage A:** `powershell -File imgsae/exploratory/p1b_sanity/run_stageA.ps1`. **Stage 1a:** `imgsae/exploratory/v2_ct/README.md`. Every script first reproduces an official number as a sanity row.
- **Large inputs** are not in git. `DATA.md` lists them and how to rebuild them from public data.
