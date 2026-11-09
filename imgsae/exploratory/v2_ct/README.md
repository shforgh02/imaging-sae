# v2_ct: Stage 1a (exploratory, 150 development scans)

**Protocol:** `docs/STAGE1A_PROTOCOL.md`, fixed and committed before running. It is the colleague review `docs/REVIEW_AND_PROPOSAL_v2.md`, adopted with amendments.

**Question.** On fixed CT-FM tokens, does the tuned SAE (its 5-fit consensus) beat equally tuned k-means, FastICA, k-sparse dictionary learning, raw channels and sparse varimax on the production validity ladder? The ladder is calibrated with a supervised reference on the same embedding (gate G1). Also reported:
- precision;
- θ;
- k = 1 sparse probing on organ groups, vertebral level and lung lobe;
- the shortcut share;
- null SAEs (untrained CT-FM, physics R3).

| File | What |
|---|---|
| `s1a_lib.py` | Method registry, new models (ICA, OMP + MOD dictionary learning, supervised reference), per-feature metrics, k = 1 probing, dense references |
| `s1a_run.py` | CPU steps: `tasks`, `cpu`, `select`, `refs` |
| `run_s1a_cpu.ps1` | Runs the CPU steps in order (resumable; logs in `logs/s1a_cpu.log`) |
| `cloud/s1a_sae_modal.py` | SAE rows on a Modal L4, same code path; budget guard `../p1b_sanity/cloud/budget.py`, task `v2s1a_sae` |
| `cloud/upload_s1a.ps1` | Puts `X_null` on the Modal volume (`/p1/rows_extra.npz`) |
| `s1a_summary.py` | Read-out: `RESULTS_S1A.md`, `results/s1a_g1.json` |
| `results/` | `s1a_cpu.json`, `s1a_sae.json`, `s1a_refs.json`, `s1a_selection.json`; per-feature tables in `tables/*.csv.gz` |

**Sanity.** Every CPU row with a Stage A counterpart must equal `a3_cpu.json` exactly; otherwise the runner stops. The SAE rows are compared with the A3 L4 rows.
