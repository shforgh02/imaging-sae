"""Collect a spawned MRI job (see launch.py): get its result if finished, save it to imgsae/mri/results/<result_name>.json, and close the
ledger run from the measured container minutes (+ the ledger's start-up allowance and image allowance).
usage (miniconda python, which has the modal client): C:\\Users\\Arman\\miniconda3\\python.exe imgsae/mri/cloud/collect.py <rid> [--wait SECONDS]
Exit code 0 = collected and closed; 3 = still running; 4 = the call failed (run left open for a manual close from billing).
"""
import argparse
import json
import sys
from pathlib import Path

import modal

HERE = Path(__file__).resolve().parent; MRI = HERE.parent; sys.path.insert(0, str(HERE))
import launch as LN  # noqa: E402


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("rid"); ap.add_argument("--wait", type=float, default=5.0); a = ap.parse_args()
    rec = json.loads((LN.RUNS / f"{a.rid}.json").read_text()); call = modal.FunctionCall.from_id(rec["call_id"])
    try:
        out = call.get(timeout=a.wait)
    except TimeoutError:
        print(f"{a.rid}: still running"); sys.exit(3)
    except (ConnectionError, OSError) as e:   # laptop network trouble (or a remote OSError): retry; the caller loop is bounded
        print(f"{a.rid}: transient error, will retry: {e!r}"[:800]); sys.exit(5)
    except Exception as e:
        print(f"{a.rid}: CALL FAILED: {e!r}"[:1500]); sys.exit(4)
    name = rec.get("result_name") or rec["job"]; (MRI / "results").mkdir(exist_ok=True)
    (MRI / "results" / f"{name}.json").write_text(json.dumps(out, indent=1, default=str))
    measured = (float(out["container_min"]) + LN.B.START_MIN) / 60 * rec["rate_h"] + LN.IMAGE_USD
    LN.B.close_run(a.rid, measured, f"collected; container {out['container_min']:.1f} min")
    print(f"{a.rid}: collected -> results/{name}.json; closed at ${measured:.2f}")


if __name__ == "__main__":
    main()
