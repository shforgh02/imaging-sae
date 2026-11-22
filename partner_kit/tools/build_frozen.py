"""Partner kit v1.0: build frozen/ from the committed NLST files (run once in the repository; partners do not run it).
Copies the portable form parameters (X10) and extracts the NLST-dev cuts (cancer-free dev exams; X9 for Sybil, X10 for P) per endpoint,
with their source; writes frozen/MANIFEST.sha256. usage: python tools/build_frozen.py <repository lung_l2 folder>
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]


def main():
    L2 = Path(sys.argv[1]); F = KIT / "frozen"; F.mkdir(exist_ok=True)
    shutil.copyfile(L2 / "results/x10/x10_portable_form_params.json", F / "x10_portable_form_params.json")
    x9 = json.loads((L2 / "results/x9/x9_rules_thresholds_dev.json").read_text())["thresholds"]
    x10 = json.loads((L2 / "results/x10/x10_portable_form_dev.json").read_text())["thresholds"]
    out = {}
    for ep, e9, e10 in (("E1_1year_all_screens", "E1", "E1_1_year_all_screens"), ("E2_1year_baseline", "E2", "E2_1_year_baseline"), ("E4_6years_baseline", "E4", "E4_6_years_baseline")):
        rows = []
        for op, lab in (("OP_L3", "Lung-RADS>=3 false-alarm level"), ("OP_R", "radiologists' false-alarm level")):
            c = x9[e9]["table"][f"sybil@{op}"]["cut"]
            rows.append(dict(label=f"sybil_at_nlst_dev_{op}", score="sybil_prob", threshold=c["threshold"], rule=c["flag_rule"], source=f"X9 dev, {e9} sybil@{op} ({lab}); transportability without local recalibration"))
            c = x10[e10]["table"][f"P@{op}"]["cut"]
            rows.append(dict(label=f"P_at_nlst_dev_{op}", score="P", threshold=c["threshold"], rule=c["flag_rule"], source=f"X10 dev, {e10} P@{op} ({lab}); transportability without local recalibration"))
        out[ep] = rows
    (F / "nlst_dev_cuts.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8", newline="\n")
    def lf_sha(p): return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    lines = [lf_sha(p) + "  " + p.name for p in sorted(F.glob("*.json"))]
    (F / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n"); print("\n".join(lines))


if __name__ == "__main__":
    main()
