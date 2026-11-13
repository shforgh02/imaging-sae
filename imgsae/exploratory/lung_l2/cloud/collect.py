"""Collect a spawned L2 job (see launch.py): get its result if finished, save it to lung_l2/results/runs/<result_name>.json, and close the
ledger run from the measured container minutes (+ the ledger's start-up allowance and image allowance).
usage (miniconda python, which has the modal client): C:\\Users\\Arman\\miniconda3\\python.exe imgsae/exploratory/lung_l2/cloud/collect.py <rid> [--wait SECONDS]
Exit code 0 = collected and closed; 3 = still running; 4 = a call failed (run left open for a manual close from billing); 5 = transient error.
"""
import argparse
import json
import sys
from pathlib import Path

import modal

HERE = Path(__file__).resolve().parent; L2 = HERE.parent; sys.path.insert(0, str(HERE))
import launch as LN  # noqa: E402


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("rid"); ap.add_argument("--wait", type=float, default=5.0); a = ap.parse_args()
    rec = json.loads((LN.RUNS / f"{a.rid}.json").read_text()); ids = rec.get("call_ids") or [rec["call_id"]]; outs = []
    for cid in ids:
        try:
            outs.append(modal.FunctionCall.from_id(cid).get(timeout=a.wait))
        except TimeoutError:
            print(f"{a.rid}: call {cid} still running"); sys.exit(3)
        except (ConnectionError, OSError) as e:
            print(f"{a.rid}: transient error, will retry: {e!r}"[:800]); sys.exit(5)
        except Exception as e:
            print(f"{a.rid}: CALL {cid} FAILED: {e!r}"[:1500]); sys.exit(4)
    out = outs[0] if len(outs) == 1 else dict(calls=outs, container_min=sum(float(o["container_min"]) for o in outs))
    name = rec.get("result_name") or rec["job"]; (L2 / "results" / "runs").mkdir(parents=True, exist_ok=True)
    (L2 / "results" / "runs" / f"{name}.json").write_text(json.dumps(out, indent=1, default=str))
    measured = (float(out["container_min"]) + LN.B.START_MIN * len(ids)) / 60 * rec["rate_h"] + LN.IMAGE_USD
    LN.B.close_run(a.rid, measured, f"collected; {len(ids)} call(s), container {out['container_min']:.1f} min")
    print(f"{a.rid}: collected -> results/runs/{name}.json; closed at ${measured:.2f}")


if __name__ == "__main__":
    main()
