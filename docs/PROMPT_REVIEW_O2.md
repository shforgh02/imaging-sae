# Prompt for a re-check of the O2 plan (before any O2 scan is scored)

**How to use it (for the lead):** open a **fresh session** that did not write the plan (working folder `D:\Shayan`; Opus 5.5 or Fable 5.2, effort high), and paste: "Read `docs/PROMPT_REVIEW_O2.md` and do what it says below its line." Free; no cloud.

---

You are re-checking a pre-registered plan before it runs. You did not write it. Repository `D:\Shayan`, branch `prostate-mri-plan`.

**Read:** `docs/O2_PLAN.md` (the plan); `imgsae/exploratory/lung_l2/o2_manifest.py`, `o2_analysis.py`, `o2_form.py`; the diffs of `cloud/l2_sybil_modal.py` and `cloud/drive_runs.py` in the freeze commit; `results/o2_manifest.json`; `results/o2/o2_analysis_dry_dev.json`, `results/o2/o2_form_dry_dev.json`; for the frozen definitions `imgsae/exploratory/lung_l2/HYPOTHESES_L2.md`, `results/s5/frozen_thresholds_L2.json`, `s6_frozen_analysis.py`, `x5_lidc.py`; the log entries of 20 Nov in `docs/EXECUTION_LOG.md`.

**Check and answer:**
1. Do the hashes of section 8 of the plan match the files?
2. Does `o2_analysis.py` compute O2-H1, H2, H3, H6 and H7 exactly as the frozen NLST definitions (`s6_frozen_analysis.py`), apart from the stated changes (ratio > 0; pairs limited to U1 and U2; O2-H7x with null 0)? Any bug?
3. Is `o2_analysis.py` really outcome-free (no outcome column used or written)? Is U3 kept out of O2a/O2b?
4. Is the random sample of `o2_manifest.py` fixed before any outcome is read, and does `o2_form.py` rebuild and check it?
5. Are the cloud changes limited to reading the new list and booking the task? Could they change how dev, test or LIDC were scored?
6. Is the H7 design with only U1 and U2 scored sound? Is the null 0 for O2-H7x reasonable?
7. Anything that should change before the first launch? (A change now means a new freeze commit and a log line.)

**You may:** run the scripts with `--dry-dev` into a temporary folder; write `docs/REVIEW_O2.md` (verdict: approve, approve with changes, or reject, with reasons); add one log entry; commit these two files and push.
**You must not:** read any outcome or image of the never-used participants (no `--add-u3`, no NLST table rows of those participants, no scoring); run any cloud command or change `ledger.json`; change the plan, the scripts or the frozen files; contact anyone outside; put a name, e-mail or project name in any request to an outside service. Keep `New report .txt` and `imgsae/exploratory/ucla_audit/` out of git.
