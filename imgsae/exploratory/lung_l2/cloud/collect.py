"""Collect a spawned L2 job (see launch.py): get its result if finished, save it to lung_l2/results/runs/<result_name>.json, and close the
ledger run from the measured container minutes (+ the ledger's start-up allowance and image allowance).
usage (miniconda python, which has the modal client):
  C:\\Users\\Arman\\miniconda3\\python.exe imgsae/exploratory/lung_l2/cloud/collect.py <rid> --profile <account> [--wait SECONDS]
The account (amendment A4) is the run's ledger profile; --profile, if given, must equal it. MODAL_PROFILE is set for this process before
modal is imported, so the call is read on the account that ran it. Never `modal profile activate`.
Exit code 0 = collected and closed; 3 = still running; 4 = a call failed (run left open for a manual close from billing); 5 = transient
error; 6 = refused (profile mismatch or unknown).
"""
import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent; L2 = HERE.parent; sys.path.insert(0, str(HERE))
import launch as LN  # noqa: E402  (does not import modal)


def run_profile(rid):
    """the profile stored in the ledger run (truth) and in the run record (must agree)."""
    L = LN.B.load(); hit = [r for r in L["runs"] if r["id"] == rid]
    if not hit: raise SystemExit(f"{rid}: not in the ledger")
    p = LN.B.need_profile(L, LN.B.run_profile(hit[0]))
    rec = json.loads((LN.RUNS / f"{rid}.json").read_text())
    if rec.get("profile", "shforghani2002") != p: raise SystemExit(f"{rid}: run record profile {rec.get('profile')!r} != ledger {p!r}")
    return p, rec


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("rid"); ap.add_argument("--wait", type=float, default=5.0); ap.add_argument("--profile")
    a = ap.parse_args()
    try: p, rec = run_profile(a.rid)
    except (SystemExit, ValueError) as e: print(f"{a.rid}: REFUSED: {e}"); sys.exit(6)
    if a.profile and a.profile != p: print(f"{a.rid}: REFUSED: --profile {a.profile} but the run is on {p}"); sys.exit(6)
    if os.environ.get("MODAL_PROFILE") not in (None, "", p): print(f"{a.rid}: REFUSED: MODAL_PROFILE {os.environ['MODAL_PROFILE']} but the run is on {p}"); sys.exit(6)
    os.environ["MODAL_PROFILE"] = p
    import modal  # after MODAL_PROFILE is set: modal reads the profile at import
    import modal.config as MC
    if MC._profile != p: print(f"{a.rid}: REFUSED: modal client profile {MC._profile} != {p}"); sys.exit(6)
    ids = rec.get("call_ids") or [rec["call_id"]]; outs = []
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
    print(f"{a.rid}: collected on {p} -> results/runs/{name}.json; closed at ${measured:.2f}")


if __name__ == "__main__":
    main()
