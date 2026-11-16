"""Synthetic end-to-end test of the S4 analysis scripts (plan docs/PLAN_L2_NEXT_v1.md P4a item 2): a fake dev world with planted
effects, every script run in the protocol order on it, known answers checked. No real data is read except Sybil's calibrator (a model
file). Writes only into a temporary folder (L2_S4_DATA points there).
Planted world (900 participants x 3 screens): 8 latent factors with distinct sizes enter every member's h (h = 3 + L W_m + noise);
Sybil's head reads a_N (nodules, also on the form), a_T (scanner maker and kernel; no cancer information), a_I (emphysema), a_D (age)
and a_U (hidden, persistent within a participant). Cancer depends on a_N, a_U and a_I, not on a_T. F knows a_N only.
z-fix variants (stretch 2) lower a_T by 1.0; soft-kernel partners lower a_T by 0.7.
Known answers: check P1 passes; Shapley T > 0 and B ~ 0 for lbar6; the PCA arm is valid with families named N and T; U adds to F;
z-fix moves >= 30% of D5 exams by >= 0.25 SD and qualifies U1b; sharp minus soft > 0; Sybil-only false alarms have a higher T term;
technical removal narrows the false-alarm spread (ratio < 0.8) without AUROC loss; the reliability statistic > 0; Sybil adds to F+I;
F+I beats F; the gate finds holding candidates; the leak check passes; gate judging rules work on hand-made candidates.
usage (venv python): python test_s4_scripts.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent; PY = sys.executable
CAL = Path(r"D:\Shayan\imgsae_data\lung_l2_vol\l2\run_info\sybil_ensemble_simple_calibrator.json")
sys.path.insert(0, str(HERE))
results = []


def ok(name, cond, info=""):
    results.append((name, bool(cond))); print(f"{'PASS' if cond else 'FAIL'}  {name}  {info}", flush=True)


def std(x): return (x - x.mean()) / x.std()


def world(T):
    import s4_common as S
    rng = np.random.default_rng(1); P = 900; n = 3 * P
    E = pd.DataFrame(dict(pid=np.repeat([str(200000 + p) for p in range(P)], 3), study_yr=np.tile([0, 1, 2], P)))
    pidx = np.repeat(np.arange(P), 3); E["series_uid"] = [f"9.9.{i}" for i in range(n)]; E["grp"] = "dev"
    uN, uU = rng.normal(size=P), rng.normal(size=P)
    aN = 0.8 * uN[pidx] + 0.6 * rng.normal(size=n); aU = 0.8 * uU[pidx] + 0.6 * rng.normal(size=n)
    maker = rng.choice(["GE MEDICAL SYSTEMS", "SIEMENS", "Philips", "TOSHIBA"], n, p=[.45, .3, .15, .10]); sharp = (rng.random(n) < .5).astype(int)
    eff = {"GE MEDICAL SYSTEMS": 0.0, "SIEMENS": 0.8, "Philips": -0.6, "TOSHIBA": 1.5}
    aT_raw = np.array([eff[m] for m in maker]) + 0.7 * sharp + 0.2 * rng.normal(size=n); mT, sT = aT_raw.mean(), aT_raw.std(); aT = (aT_raw - mT) / sT
    age = rng.normal(62, 5, n) + E.study_yr.to_numpy(); aD = std(age); laa = rng.gamma(2, 3, n); aI = std(laa)
    male, smoker, ab60 = ((rng.random(n) < q).astype(int) for q in (.6, .5, .2))
    Z3 = np.column_stack([std(male + 0.3 * rng.normal(size=n)), std(smoker + 0.3 * rng.normal(size=n)), std(ab60 + 0.3 * rng.normal(size=n))])
    SC = np.array([3.0, 2.5, 2.0, 1.6, 1.3, 1.0, 0.8, 0.6])
    def latents(aT_):
        return np.column_stack([aN, aT_, aI, aD, aU, Z3]) * SC
    coef = np.array([0.9, 0.6, 0.3, 0.3, 0.7, 0, 0, 0]); beta = coef / SC
    Ws = []; heads = {}; noise = rng.normal(0, 0.02, (5, n, 512))
    for m in range(5):
        W = rng.normal(size=(8, 512)); W /= np.linalg.norm(W, axis=1, keepdims=True); Ws.append(W)
        w = W.T @ np.linalg.solve(W @ W.T, beta) + rng.normal(0, 1e-4, 512); w[:5] = 0
        Wh = rng.normal(0, 0.002, (6, 512)); Wh[:, :5] = 0; off = np.array([-5, -5, 0, 0, -5, -5.0])
        heads[f"m{m}_base_hazard_fc_W"] = w[None, :].astype(np.float32); heads[f"m{m}_base_hazard_fc_b"] = np.array([-2.2 - 3 * w.sum()], np.float32)
        heads[f"m{m}_hazard_fc_W"] = Wh.astype(np.float32); heads[f"m{m}_hazard_fc_b"] = (off - 3 * Wh.sum(1)).astype(np.float32)
    np.savez(T / "heads.npz", **heads); Hd = S.C.load_heads(T / "heads.npz"); cal = json.load(open(CAL))

    def arrays(aT_):
        L = latents(aT_); H = np.stack([np.maximum(3 + L @ Ws[m] + noise[m], 0) for m in range(5)], 1); H[:, :, :5] = 0
        lg, raw = zip(*[S.C.head_logits(H[:, m], Hd[m]) for m in range(5)]); lg = np.stack(lg, 1)
        rawv = np.stack([H[:, m] @ Hd[m]["hazard_fc_W"].T + Hd[m]["hazard_fc_b"] for m in range(5)], 1)
        basev = np.stack([H[:, m] @ Hd[m]["base_hazard_fc_W"].T + Hd[m]["base_hazard_fc_b"] for m in range(5)], 1)
        s = S.calibrate(cal, (1 / (1 + np.exp(-lg))).mean(1))
        return dict(h=H.astype(np.float32), logit=lg.astype(np.float32), raw_haz=rawv.astype(np.float32), base_haz=basev.astype(np.float32)), s
    arr, s = arrays(aT)
    for t in range(6): E[f"s{t + 1}"] = s[:, t]
    p6 = 1 / (1 + np.exp(-(-2.0 + 0.9 * aN + 0.7 * aU + 0.4 * aI))); canc = rng.random(n) < p6
    dt = np.where(canc, 6 * 365.25 * rng.random(n) ** 2, np.nan); E["dt"] = dt
    for y, d in (("y1", 1), ("y2", 2), ("y6", 6)): E[y] = np.where(canc & (dt <= d * 365.25), 1.0, 0.0)
    E["F1"] = -4 + 1.2 * aN + 0.2 * rng.normal(size=n); E["F6"] = -2.5 + 1.0 * aN + 0.2 * rng.normal(size=n)
    E["positive_call"] = ((aN > 0.3) | (rng.random(n) < 0.05)).astype(int)
    E["N_log_dia"] = aN; E["N_max_dia"] = np.exp(1.6 + 0.4 * aN); E["max_dia"] = E.N_max_dia; E["N_n_nod"] = rng.poisson(1, n)
    E["B_ab60"] = ab60; E["B_ab64"] = (rng.random(n) < .1).astype(int)
    E["D_age"] = age; E["D_male"] = male; E["D_current_smoker"] = smoker
    E["D_race_black"] = (rng.random(n) < .1).astype(int); E["D_race_other"] = (rng.random(n) < .05).astype(int); E["D_study_yr"] = E.study_yr
    meas = dict(I_lung_vol_ml=rng.normal(5000, 800, n), I_laa950_pct=laa, I_lung_p15_hu=-900 - 5 * laa + rng.normal(0, 5, n),
                I_lung_mean_hu=-850 - 3 * laa + rng.normal(0, 5, n), I_body_area_cm2=rng.normal(650, 90, n), I_air_noise_sd_hu=rng.gamma(4, 5, n),
                I_lung_z_extent_mm=rng.normal(260, 25, n))
    for k, v in meas.items(): v = v.copy(); v[rng.random(n) < .04] = np.nan; E[k] = v
    ratio = np.select([rng.random(n) < .2, rng.random(n) < .25], [0.5, 0.8], 1.0); thick = rng.choice([1.0, 1.25, 2.5, 3.0], n, p=[.3, .3, .3, .1])
    E["thickness"], E["true_spacing"], E["ratio"] = thick, thick * ratio, ratio
    E["T_maker"] = maker; E["T_model"] = np.char.add(maker.astype(str), "_m1"); E["T_kclass_sharp"] = sharp; E["T_sharp_rank"] = rng.random(n)
    E["T_thickness"] = thick; E["T_zstretch"] = 1 / ratio; E["T_thick_gt_2p5"] = (thick > 2.5).astype(int); E["T_kvp"] = rng.choice([120, 140], n)
    for k in ("T_exposure", "T_tube_current", "T_recon_diameter", "T_n_images", "T_scan_length_mm", "T_n_real_slices"): E[k] = rng.normal(100, 10, n)
    E["T_tilt"] = 0; E["T_regular_3d"] = 1.0; E["T_lung_cut_z"] = ((ratio == 0.5) & (rng.random(n) < .8)).astype(float); E["T_lung_cut_xy"] = 0.0
    for k in ("T_q_limited", "T_q_breath", "T_q_motion", "T_q_artifact", "T_q_graininess"): E[k] = (rng.random(n) < .03).astype(int)
    E["T_lung_at_edge"] = 0
    E["c_histology"] = np.where(canc, rng.choice(["adeno", "squamous", "small_cell", "other"], n), None)
    E["c_stage"] = np.where(canc, rng.choice(["I", "II_III", "IV"], n), None); E["c_lesion_mm"] = np.where(canc, rng.gamma(3, 6, n), np.nan)
    for k in ("central", "upper", "middle", "lower"): E[f"c_loc_{k}"] = np.where(canc, (rng.random(n) < .3).astype(float), np.nan)
    A = T / "assembled"; A.mkdir(); E.to_csv(A / "exams_dev.csv", index=False); np.savez(A / "arrays_dev_main.npz", series_uid=E.series_uid.to_numpy(), **arr)
    (A / "assemble_dev.json").write_text(json.dumps(dict(root="dev")))
    # z-fix variants (stretch 2 rows, plus 30 rows of ratio 0.8 as the pilot's extra rows) and kernel partners
    zr = np.flatnonzero(ratio == 0.5); zx = np.flatnonzero(ratio == 0.8)[:30]; zi = np.r_[zr, zx]
    az, sz = arrays(np.where(np.isin(np.arange(n), zi), aT - 1.0, aT))
    Zv = E.loc[zi, ["series_uid", "pid", "study_yr", "ratio", "thickness", "true_spacing"]].copy(); Zv["variant"] = "zfix"; Zv["partner_of"] = ""
    for t in range(6): Zv[f"s{t + 1}"] = sz[zi, t]
    Zv.to_csv(A / "variant_dev_zfix.csv", index=False); np.savez(A / "arrays_dev_zfix.npz", series_uid=Zv.series_uid.to_numpy(), **{k: v[zi] for k, v in az.items()})
    pi = np.flatnonzero((E.study_yr == 0).to_numpy() & (sharp == 1))[:150]
    ap_, sp = arrays(np.where(np.isin(np.arange(n), pi), aT - 0.7 / sT, aT))
    Pv = E.loc[pi, ["pid", "study_yr", "ratio", "thickness", "true_spacing"]].copy(); Pv["series_uid"] = [f"8.8.{i}" for i in pi]
    Pv["partner_of"] = E.series_uid.to_numpy()[pi]; Pv["variant"] = "pair"
    for t in range(6): Pv[f"s{t + 1}"] = sp[pi, t]
    Pv.to_csv(A / "variant_dev_pair.csv", index=False); np.savez(A / "arrays_dev_pair.npz", series_uid=Pv.series_uid.to_numpy(), **{k: v[pi] for k, v in ap_.items()})
    return A, E


def run(args, T, name):
    t0 = time.time(); env = {**os.environ, "L2_S4_DATA": str(T / "data"), "PYTHONUTF8": "1"}
    p = subprocess.run([PY, str(HERE / args[0])] + [str(x) for x in args[1:]], capture_output=True, text=True, env=env, cwd=str(HERE))
    (T / "logs").mkdir(exist_ok=True); (T / "logs" / f"{name}.txt").write_text((p.stdout or "") + (p.stderr or ""))
    ok(f"{name} runs", p.returncode == 0, f"{time.time() - t0:.0f}s" + ("" if p.returncode == 0 else " | " + (p.stderr or "")[-600:]))
    return p.returncode == 0


def gate_rules():
    import s4_gate as G
    base = dict(null=0.0, feature_based=False)
    cases = [(dict(base, direction=">", est=.2, lo=.1, hi=.3, half_a=.1, half_b=.3), True, True),
             (dict(base, direction=">", est=.2, lo=-.1, hi=.3, half_a=.1, half_b=.3), True, False),
             (dict(base, direction=">", est=.2, lo=.1, hi=.3, half_a=-.1, half_b=.3), True, False),
             (dict(base, direction="<", null=1.0, est=.6, lo=.4, hi=.9, half_a=.7, half_b=.5), True, True),
             (dict(base, direction="!=", est=-.3, lo=-.5, hi=-.1, half_a=-.2, half_b=-.4), True, True),
             (dict(base, direction="!=", est=-.3, lo=-.5, hi=-.1, half_a=.2, half_b=-.4), True, False),
             (dict(base, direction=">", est=.2, lo=.1, hi=.3, half_a=.1, half_b=.3, feature_based=True), False, False),
             (dict(base, direction=">", est=None, lo=.1, hi=.3, half_a=.1, half_b=.3), True, False)]
    ok("gate judge rules (8 hand-made cases)", all(G.judge(c, v)[0] == want for c, v, want in cases))
    import re
    ok("leak patterns match forbidden strings", all(any(re.search(p, s) for p in G.PATTERNS) for s in
                                                     ["lung_l1/results/scores.csv", "manifest_test.csv", r"D:\x\l2\test\main", "exams_test.csv", "grp == 'test'"]))
    ok("leak patterns ignore the dev strings", not any(re.search(p, s) for p in G.PATTERNS for s in ["exams_dev.csv", "root dev", "later test (S6)", "tag == 'dev'"]))


def main():
    T = Path(tempfile.mkdtemp(prefix="s4test_")); (T / "data").mkdir(); R = T / "results"; t0 = time.time()
    try:
        A, E = world(T); H = T / "heads.npz"; K = "16"
        print(f"world: {len(E)} exams, y1 {int(E.y1.sum())}, y6 baseline {int(E[E.study_yr == 0].y6.sum())}", flush=True)
        gate_rules()
        run(["s4_scores.py", A, R], T, "s4_scores")
        run(["s4_q1a.py", A / "exams_dev.csv", A / "arrays_dev_main.npz", R, "dev"], T, "s4_q1a")
        run(["s4_decomp.py", A / "exams_dev.csv", A / "arrays_dev_main.npz", H, R, "--K", K, "--arms", "raw,pca"], T, "s4_decomp")
        for s, extra in (("s4_q1b_u.py", [H]), ("s4_q1c.py", []), ("s4_q1d.py", [H]), ("s4_q2.py", []), ("s4_u1a.py", [H, CAL]),
                         ("s4_u2.py", []), ("s4_u3.py", []), ("s4_u4.py", []), ("s4_refs.py", [])):
            run([s, A, R] + extra + ([] if s in ("s4_u1a.py", "s4_refs.py") else ["--K", K]), T, s[:-3])
        run(["s4_gate.py", R, "--K", K, "--assembled", A], T, "s4_gate")
        run(["s4_report.py", R, T / "report.md"], T, "s4_report")
        J = lambda n: json.loads((R / f"{n}_dev.json").read_text())
        sc = J("s4_scores"); from scipy.stats import spearmanr
        ok("scores: check P1 equals a direct computation", abs(sc["check_P1"]["t1_all"] - spearmanr(E.s1, np.load(A / "arrays_dev_main.npz")["logit"][:, :, 0].astype(float).mean(1))[0]) < 1e-9,
           f"{sc['check_P1']['t1_all']:.4f}")
        ok("scores: lbar ranks like the mean member probability (diagnostic >= 0.98)", sc["check_P1"]["diagnostics"]["t1"]["spearman_lbar_vs_mean_member_prob"] >= 0.98)
        g = np.load(A / "arrays_dev_main.npz")["raw_haz"] > 0; ok("scores: gating share equals raw > 0", abs(sc["gating_on_share"]["overall"] - g.mean()) < 1e-9)
        a1 = sc["auroc"]["y1"]["sybil_s"]; ok("scores: AUROC interval brackets the estimate", a1["lo"] <= a1["est"] <= a1["hi"])
        q = J("s4_q1a"); c = {x["id"]: x for x in q["candidates"]}
        ok("q1a: Shapley T of lbar6 > 0 with interval above 0", c["Q1a_shapley_T_lbar6_baseline"]["lo"] > 0)
        ok("q1a: Shapley B of lbar6 ~ 0 (interval includes 0 or tiny)", c["Q1a_shapley_B_lbar6_baseline"]["est"] < 0.01)
        dp = json.loads((R / "s4_decomp_dev_pca_K16.json").read_text()); ok("decomp: pca arm valid", dp["valid"], json.dumps({k: dp[k]["pass_"] for k in ("V1", "V2", "V3", "V4")}))
        ok("decomp: families named N and T present", {"N", "T"} <= set(dp["labels"]), json.dumps(dp["labels"]))
        qb = J("s4_q1b_u"); ok("q1b: primary arm pca", qb["primary_arm"] == "pca")
        ok("q1b: U adds to F (y1) with interval above 0", qb["U_adds_to_F_y1"]["dauroc"]["lo"] > 0, f"{qb['U_adds_to_F_y1']['dauroc']}")
        ok("q1b: group share T of lbar1 > 0", qb["group_shares"]["lbar1"]["T"]["lo"] > 0)
        ok("q1b: shares sum to 1", abs(qb["group_shares"]["lbar1"]["sum_of_shares"] - 1) < 1e-6)
        qc = J("s4_q1c"); ok("q1c: stable shares sum to 1", abs(qc["all"]["lbar6"]["stable_shares"]["sum_of_shares"] - 1) < 1e-6)
        qd = J("s4_q1d"); z = qd["zfix"]["D5"]
        ok("q1d: D5 excludes the ratio-0.8 rows", qd["zfix"]["n_D5"] == int((E.ratio == 0.5).sum()) and qd["zfix"]["n_extra_pilot_rows"] == 30)
        ok("q1d: z-fix moves >= 30% by 0.25 SD; U1b qualifies", z["t6"]["share_ge_quarter_sd"] >= 0.30 and z["U1b_dev_qualifies"])
        ok("q1d: z-fix mean delta < 0 (a_T lowered)", z["t6"]["mean"] < 0)
        ok("q1d: kernel sharp minus soft > 0", qd["kernel_pairs"]["t1"]["mean"] > 0)
        ok("q1d: kernel change carried by the T term (largest mean change)", max(qd["kernel_pairs"]["group_change"]["t1"].items(), key=lambda kv: abs(kv[1]["mean"]))[0] == "T")
        q2 = J("s4_q2"); so = {r["variable"]: r for r in q2["false_alarms"]["tau90"]["sybil_only"]}
        ok("q2: Sybil-only false alarms have a higher T term (SMD > 0, q < 0.05)", so["G_T"]["smd"] > 0 and so["G_T"]["q"] < 0.05, f"SMD {so['G_T']['smd']:.2f}")
        u1 = J("s4_u1a"); ok("u1a: recomputed s equals saved s (float32 h)", u1["check_recomputed_s_vs_saved_max_abs"] < 1e-5)
        ok("u1a: maker dummies enter the T design (pandas 3 text fix)", u1["n_T_columns"] >= 18 + 6, f"{u1['n_T_columns']} columns")
        ok("u1a: spread ratio < 0.8 and qualifies", u1["spread"]["ratio"] < 0.8 and u1["qualification"]["qualifies"], f"ratio {u1['spread']['ratio']:.2f}")
        u2 = J("s4_u2"); ok("u2: frozen-rule statistic > 0", u2["candidates"][0]["est"] > 0, u2["rule_that_can_be_frozen"])
        u3 = J("s4_u3"); ok("u3: sensitivities reach the target", all(u3["table"][k]["sensitivity"] >= u3["target_sensitivity"] - 1e-9 for k in ("sybil", "form_F", "combined_C")))
        u4 = J("s4_u4"); ok("u4: probe AUROC > 0.6", u4["y1"]["probe_h_2560"]["est"] > 0.6)
        rf = J("s4_refs"); fi = rf["F_plus_I"]["primary_5_measures"]
        ok("refs: F+I beats F (y6)", fi["y6"]["auroc_FI"]["est"] > fi["y6"]["auroc_F"]["est"])
        ok("refs: Sybil adds to F+I (y1), interval above 0", fi["y1"]["sybil_adds_to_FI"]["dauroc"]["lo"] > 0)
        ok("refs: F+I parameters written", (R / "s4_refs_FI_params_dev.json").exists())
        gt = J("s4_gate"); ok("gate: candidates found and some hold", gt["n_candidates"] > 20 and gt["n_eligible"] > 0, f"{gt['n_candidates']} candidates, {gt['n_eligible']} eligible")
        ok("gate: leak check passes on the real S4 code", gt["leak_check"]["pass_"], json.dumps(gt["leak_check"]["hits"])[:300])
        ok("gate: data check passes", gt["data_check"]["pass_"])
        ok("gate: technical-only candidate holds (U1a spread)", any(r["id"] == "U1a_spread_ratio" and r["eligible"] for r in gt["table"]))
        ok("gate: a null candidate does not hold (Shapley B)", not any(r["id"] == "Q1a_shapley_B_lbar6_baseline" and r["holds_9_8"] for r in gt["table"]))
    finally:
        keep = os.environ.get("KEEP_S4TEST")
        if not keep: shutil.rmtree(T, ignore_errors=True)
        else: print("kept", T)
    n_fail = sum(not c for _, c in results); print(f"\n{len(results) - n_fail} of {len(results)} passed ({time.time() - t0:.0f}s)")
    raise SystemExit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
