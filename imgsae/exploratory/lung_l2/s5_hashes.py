"""Lung L2, S5: (re)write the SHA-256 section of HYPOTHESES_L2.md. Text files are hashed on their committed content (LF line endings,
as git stores them), so the values hold on any checkout; results/s5 is stored byte-exact ('-text' in .gitattributes). Git blob ids are
given as a second, line-ending-free check. usage (venv python, from lung_l2): python s5_hashes.py
"""
import hashlib
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = ["results/s5/frozen_thresholds_L2.json", "results/s5/frozen_raw_arm_K64.npz", "results/s5/frozen_families_raw_K64.json", "results/s5/frozen_FI_params.json",
         "results/s5/frozen_combinations.json", "results/s5/frozen_axes_pooled.npz", "results/s5/s6_dev_as_if_test.json",
         "results/s5/s6_dev_as_if_test_h7_no_cancer_sensitivity.json", "results/s5/s6_attention_dev_as_if_test.json",
         "results/s5/s5_h5prime_dev.json", "s6_frozen_analysis.py", "s6_attention.py", "s6_manifest_test.py", "s5_freeze.py", "s5_axes_freeze.py", "s5_h5prime_dev.py",
         "s5_hashes.py", "s4_common.py", "s4_core.py", "s4_q1a.py", "s4_q1d.py", "s4_refs.py", "s4_u3.py", "l2_data.py", "l2_form.py", "series_rule.py",
         "../lung_l0/nlst_l0.py", "results/l2_form_params.json", "results/manifest_dev.csv",
         # provenance of the frozen axes and of the step R dev evidence for H6 and H7 (amendment A6); not run at S6
         "r1_arms.py", "r2_shared.py", "r4_axes_audit.py", "r5_repair.py", "r6_candidate.py", "r7_more.py", "r9_attention.py"]
PC = [r"D:\Shayan\imgsae_data\lung_l2_vol\l2\run_info\heads.npz", r"D:\Shayan\imgsae_data\lung_l2_vol\l2\run_info\sybil_ensemble_simple_calibrator.json",
      r"D:\Shayan\imgsae_data\lung_l2\r\r2_shared_pooled.pkl"]
HEAD = "## SHA-256 of the frozen and analysis files"


def content(p):
    b = (HERE / p).read_bytes()
    return b if p.endswith(".npz") or p.startswith("results/s5/") else b.replace(b"\r\n", b"\n")


def main():
    rows = ["| File (path from `imgsae/exploratory/lung_l2/`) | SHA-256 (committed content) | git blob id |", "|---|---|---|"]
    for p in FILES:
        blob = subprocess.run(["git", "hash-object", p], cwd=HERE, capture_output=True, text=True).stdout.strip()
        rows.append(f"| `{p}` | `{hashlib.sha256(content(p)).hexdigest()}` | `{blob}` |")
    for p in PC:
        what = ("PC only: source of the frozen axes, fitted by r2_shared.py on dev" if p.endswith(".pkl") else
                "PC only: Sybil's head weights (incl. hidden_fc) or calibrator, saved by the cloud job")
        rows.append(f"| `{p.split('imgsae_data')[1].replace(chr(92), '/').lstrip('/')}` under `imgsae_data/` ({what}) | "
                    f"`{hashlib.sha256(Path(p).read_bytes()).hexdigest()}` | — |")
    note = ("\nText files are hashed on their committed content (LF line endings). The frozen folder `results/s5/` is stored byte-exact "
            "(`-text` in `.gitattributes`), so `Get-FileHash` or `sha256sum` on a checkout gives these values. For the other text files on Windows "
            "with `core.autocrlf`, use `git show HEAD:<path> | sha256sum` or compare the git blob ids (`git ls-tree HEAD <path>`). The commit that "
            "freezes this file is logged in `docs/EXECUTION_LOG.md`. In S6 (step N4) the cloud job `cloud/l2_sybil_modal.py` changes only to read "
            "the test manifest written by `s6_manifest_test.py` (protocol 11); that change is logged and touches no analysis file. The step R "
            "scripts (`r*.py`) are listed for provenance only: they made the dev evidence and the frozen axes, and are not run at S6.\n")
    t = (HERE / "HYPOTHESES_L2.md").read_text(encoding="utf-8"); t = t[:t.index(HEAD) + len(HEAD)] + "\n\n" + "\n".join(rows) + "\n" + note
    (HERE / "HYPOTHESES_L2.md").write_bytes(t.replace("\r\n", "\n").encode("utf-8")); print("\n".join(rows))


if __name__ == "__main__":
    main()
