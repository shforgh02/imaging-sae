# Prompt for the plan review (Fable 5.2)

Paste everything below the line into a fresh session (model Fable 5.2, working folder `D:\Shayan`).

---

You are an independent reviewer for a research project. Repository: `D:\Shayan`, git branch `prostate-mri-plan` (pushed to GitHub). The project is a feature-level audit of the lung cancer screening model Sybil on public NLST data ("Lung L2"). The aim is the highest-impact paper the data can honestly support.

**Your task: review the plan `docs/PLAN_L2_NEXT_v1.md`. Approve it, edit it, or reject it.** A later session (Opus 5.5) will execute the plan as you leave it, after the lead's OK.

Read, in this order:
1. `docs/PLAN_L2_NEXT_v1.md`: the plan to review.
2. `docs/LUNG_L2_PROTOCOL.md`: the approved rule book. Section 16a has the amendments A1 and A2.
3. `docs/PROGRESS_REPORT_L2_2026-11-15.md`: the state and the findings so far.
4. `STATUS.md` (top part) and `docs/EXECUTION_LOG.md` (entries from 2026-11-13 on).
5. `docs/REVIEWER_BRIEF_L2.md`: what the external reviewer checks at S5.
6. Code as needed:
   - `imgsae/exploratory/p1b_sanity/cloud/budget.py` and `ledger.json`;
   - `imgsae/exploratory/lung_l2/cloud/` (`launch.py`, `drive_runs.py`, `drive_plan.py`, `l2_sybil_modal.py`, `reconcile_billing.py`);
   - `imgsae/exploratory/lung_l2/` (`l2_data.py`, `l2_form.py`, `s4_*.py`).

Check, and answer each point:
1. **Facts:** does the plan agree with the protocol and with the files (numbers, file names, what is done and what is missing)? List every error.
2. **Amendments:**
   - **A3:** two simple references, R-size and F+I. Are they well defined? Are they fair to Sybil? Are they free of leakage? Is anything better, or missing?
   - **A4:** the second Modal account. Is there any way the design could overspend, use the wrong account, or touch the lead's other work on that account? Is the identity gate enough?
   - **A5:** the unattended driver as the executor of paid runs.
   - For each one: approve, edit or reject, with the reason.
3. **Science:**
   - Will this plan give the strongest honest paper?
   - Is any step wasteful, missing or in the wrong order?
   - Are the gates and stop points right?
   - Do the S4 scripts still to be written match the protocol's definitions?
4. **Honesty rules:**
   - Is the test split protected until the S5 approval?
   - Can anything leak test information into the choices?
5. **Risks:** anything not covered in section 9 of the plan.

What you may do:
- Edit `docs/PLAN_L2_NEXT_v1.md` directly. Mark each change with `[Fable edit]` and give its reason.
- Set the plan's status line to "REVIEWED by Fable 5.2 on <date>: <verdict>".
- Write `docs/REVIEW_PLAN_L2_NEXT_v1.md`:
  - the verdict: approve / approve with edits / reject;
  - your answers to points 1 to 5;
  - the list of your edits;
  - open questions for the lead.
- Commit both files with a clear message and push to `origin prostate-mri-plan`.
- Add one line to `docs/EXECUTION_LOG.md` saying that the review was done and where it is.

What you must not do:
- **Do not run any Modal or cloud command,** paid or not, and do not change `ledger.json`.
- **Do not open, extract or analyse test-split data.**
- **Do not run analyses on the dev data,** and do not change code, the protocol's pass marks or its gates. Your changes go into the plan as proposals for the lead.
- **Do not install packages.**
- **Privacy:** do not put the user's name, email or project name into any request to an outside service. A literature search, if you need one, uses neutral terms only.
- **Git:** keep `New report .txt` and `imgsae/exploratory/ucla_audit/` out of git.

Environment:
- Windows, PowerShell (not Bash).
- Python for scripts: `D:\Shayan\imgsae\.venv\Scripts\python.exe`.

How to write: the lead's first language is not English. Use short, plain sentences. Start with the verdict, then the main reasons, then what the lead must decide. End your answer in the chat with the verdict and the paths of the files you changed.
