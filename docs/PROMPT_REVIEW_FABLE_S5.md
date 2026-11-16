# Prompt for the S5 review (Fable 5.2, external reviewer)

Paste everything below the line into a fresh session (model Fable 5.2, working folder `D:\Shayan`), or give the short prompt: "Read `docs/PROMPT_REVIEW_FABLE_S5.md` and do what it says below its line."

---

You are the external (second) reviewer named in section 10 of the protocol of a research project. Repository: `D:\Shayan`, git branch `prostate-mri-plan`, also on GitHub (`github.com/shforgh02/imaging-sae`, same commit). The project is a feature-level audit of the lung cancer screening model Sybil on public NLST data ("Lung L2"). Discovery was done on Sybil's dev split. The test split is still closed. It will be opened once, under hypotheses frozen in advance.

**Your task: review the S5 freeze before any test data are extracted. Answer items 1 to 8 of `docs/REVIEWER_BRIEF_L2.md`, and give a verdict: approve the freeze / approve with changes / reject.** The lead decides after reading your note. Only after the lead's OK does an executor session (Opus 5.5) build the test list and run the frozen analysis once.

## Key commits
- `a536192`: the S4 analysis code, fixed before any full-dev run.
- `1b23e45` and `c593005`: the freeze (part 1, and part 2 that adds the frozen dictionary). **`c593005` is the freeze commit to review.**
- After the freeze: `b26ff0e` (log and STATUS) and `b85be4c` (K = 128 check results on dev, log, STATUS). Check with `git diff --stat c593005 HEAD` that they touch no frozen or analysis file.

## Read, in this order
1. `docs/REVIEWER_BRIEF_L2.md`: your checklist (items 1 to 8) and how to reply.
2. `imgsae/exploratory/lung_l2/HYPOTHESES_L2.md`: the five hypotheses (H1 to H5), chance estimates, what was considered and not frozen, the S6 run plan, the SHA-256 list.
3. `docs/LUNG_L2_PROTOCOL.md`: the rules. Most relevant: sections 9 (analyses; 9.5 validity marks; 9.8 the gate), 10 (S5 freeze), 11 (S6 test), 12 and 13 (budget), 16a (amendments A1 to A5), and rule C10 (what was already seen on test).
4. `imgsae/exploratory/lung_l2/RESULTS_S4_dev.md` and the evidence it cites in `imgsae/exploratory/lung_l2/results/s4/` (including `s4_gate_dev.md`).
5. The frozen files in `imgsae/exploratory/lung_l2/results/s5/`, the frozen analysis `imgsae/exploratory/lung_l2/s6_frozen_analysis.py`, the script that wrote the frozen files `s5_freeze.py`, and the S4 modules the analysis imports (`s4_common.py`, `s4_core.py`, `s4_q1d.py`, `s4_refs.py`, `s4_u3.py`).
6. `docs/EXECUTION_LOG.md`, entries from 2026-11-13 on (especially P4a, P4b, P5 and the K = 128 entry of 2026-11-16).
7. What was already seen on test: `imgsae/exploratory/lung_l1/RESULTS_L1.md` and `imgsae/exploratory/lung_l1/posthoc/`.
8. Paid runs: `imgsae/exploratory/p1b_sanity/cloud/ledger.json` and the run records in `imgsae/exploratory/lung_l2/results/runs/` (each has a `root` value; no L2 run should have `root` = `test`).

## Points the executor flagged (judge them yourself, and look for others)
- The margins (null values) of H2 to H5 were chosen at S5, after the dev values were known. H3 and H4 did not meet the provisional margins written at S4. This is disclosed in the file. Is it acceptable, and are the chosen margins reasonable?
- H3 (z-fix flag change > 0.05; dev 0.0747) has an estimated chance of only 0.60 on test.
- All five hypotheses are about Sybil's technical behaviour and its internal features. None is about cancer prediction. The use candidates U1a and U3 failed gate 9.8 on dev, and are not frozen.
- H5 uses the frozen raw-unit dictionary and its family labels. Raw units were the only valid arm at K = 64 and at K = 128. The sparse autoencoder was not valid at either size.
- About 320 of the 344 gate candidates that "hold" are near-automatic (they hold by construction). They were excluded from the family.
- Two inputs are on the PC only (Sybil's head weights and calibrator, under `D:\Shayan\imgsae_data\lung_l2_vol\l2\run_info\`). Their SHA-256 values are in the S5 file.
- The S6 cost projection (about $18.9, or $20.8 with a preemption reserve) leaves a thin margin against $22.30 available.

## How to check (all local and free)
- **Hashes (item 5):**
  - `results/s5/` is stored byte-exact, so `Get-FileHash -Algorithm SHA256 <file>` on the checkout gives the listed values.
  - For the other text files, do **not** pipe `git show` into a hash in PowerShell, because PowerShell re-encodes the bytes. Instead, compare git blob ids with `git ls-tree c593005 -- <path>`, or hash the bytes of `git show c593005:<path>` from a small Python script.
  - For the two PC-only inputs, use `Get-FileHash`.
- **Dev as if test (item 5, optional):** you may re-run the frozen analysis on dev. It reads dev data only and is free. Write the output to a temporary folder outside the repository, never over the committed file:
  `cd D:\Shayan\imgsae\exploratory\lung_l2; D:\Shayan\imgsae\.venv\Scripts\python.exe s6_frozen_analysis.py D:\Shayan\imgsae_data\lung_l2\dev dev results\s5 D:\Shayan\imgsae_data\lung_l2_vol\l2\run_info <temp folder>\s6_dev_check.json`
  Then compare the output with `results/s5/s6_dev_as_if_test.json` and with the S4 dev values. It may take several minutes.
- **Dev only (item 2):** use `git log`, file lists and the committed run records. You may read file names on the PC, but do not open any test-split file there.

## What you may do
- Write `docs/REVIEW_S5_L2.md`, containing:
  - the verdict;
  - one line per item 1 to 8 (yes / no / comment; if an item fails, say which hypothesis and why);
  - other comments;
  - any change you propose;
  - what the lead must decide.
- Add one line to `docs/EXECUTION_LOG.md` saying that the S5 review was done and where it is.
- Commit only these two files with a clear message, and push to `origin prostate-mri-plan`.

## What you must not do
- **Do not change `HYPOTHESES_L2.md`, any file in `results/s5/`, or any analysis script.** The freeze must stay byte-exact. If a hypothesis or margin should change, propose it in your note. After the lead's OK, the executor makes a new freeze commit.
- **Do not run `s5_freeze.py`, `s5_hashes.py` or `run_s4_dev.ps1`.** They rewrite the frozen or result files.
- **Do not open, extract or analyse test-split data,** and do not build a test manifest.
- **Do not run any Modal or cloud command,** paid or not, and do not change `ledger.json`.
- **Do not install packages.**
- **Privacy:** do not put the user's name, email or project name into any request to an outside service. A literature search, if you need one, uses neutral terms only.
- **Git:** keep `New report .txt` and `imgsae/exploratory/ucla_audit/` out of git.

## Environment
- Windows, PowerShell (not Bash).
- Python for scripts: `D:\Shayan\imgsae\.venv\Scripts\python.exe`.

## How to write
The lead's first language is not English. Use short, plain sentences. Start with the verdict, then the main reasons, then what the lead must decide. End your answer in the chat with the verdict and the paths of the files you changed.
