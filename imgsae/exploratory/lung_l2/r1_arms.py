"""Lung L2, step R (rescue scouting; dev only, exploratory; the lead's instruction of 2026-11-16): the six arms of S4 with the same
validity marks V1 to V4, but on another layer (--layer pooled), with another K, or with another SAE sparsity (--sae-k).
Nothing of S4 or S5 is changed or overwritten: the arm code, the family rule and the naming are imported from s4_core / s4_decomp.
usage: python r1_arms.py <assembled dir> <heads npz> <out dir> --layer h|pooled --K 16 --arms pca,ica [--sae-k 8] [--v2-members 0,1]
Writes <out>/r1_<layer>_<arm>_K<K>[_k<k>].json and the family table (.csv).
Scouting simplification (logged): V2 on members 0 and 1 only by default (S4: all five). V1, V3, V4 exactly as S4.
New descriptive numbers (not marks): how many families are not copies of the risk score (|r| with lbar6 below 0.5), and the effective
number of dimensions of the family activations.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, r"D:\Shayan\imgsae")
import l2_data as D  # noqa: E402
import s4_core as C  # noqa: E402
import s4_decomp as DC  # noqa: E402
import s4_q1a as Q  # noqa: E402
from imgsae import sae as SAE  # noqa: E402


class Arm(C.Arm):
    """s4_core.Arm; only the SAE sparsity k can be set (S4 rule: k = K/16)."""

    def __init__(self, kind, K, seed=0, device="cpu", sae_k=0):
        super().__init__(kind, K, seed, device); self.sae_k = sae_k

    def fit(self, h, w_ref=None):
        if self.kind != "sae" or not self.sae_k: return super().fit(h, w_ref)
        h = np.asarray(h, np.float64); self.mu = h.mean(0); sd = h.std(0)
        self.live = sd >= 1e-6; self.sd = np.where(self.live, sd, 1.0)
        Z = ((h - self.mu) / self.sd)[:, self.live]
        cfg = dict(M=self.K, k=self.sae_k, seed=self.seed, device=self.device, matryoshka=True)
        if os.environ.get("R1_TEST_STEPS"): cfg["steps"] = int(os.environ["R1_TEST_STEPS"])       # code test only; never set in a real run
        m, _ = SAE.fit(Z.astype(np.float32), cfg)
        self.m = m; self.D = m.D.detach().cpu().numpy().astype(np.float64); self.c = m.b_dec.detach().cpu().numpy().astype(np.float64); self.off = self.mu
        return self


def load(assembled, heads_path, layer):
    A = Path(assembled); E = pd.read_csv(A / "exams_dev.csv", dtype={"pid": str}, low_memory=False)
    if not (E.grp == "dev").all(): raise SystemExit("REFUSED: the exam table holds non-dev participants")
    Z = np.load(A / "arrays_dev_main.npz", allow_pickle=True); pos = {u: i for i, u in enumerate(Z["series_uid"])}
    idx = np.array([pos[u] for u in E.series_uid]); X = Z[layer][idx].astype(np.float64); LG = Z["logit"][idx].astype(np.float64)
    heads = C.load_heads(heads_path); hz = np.load(heads_path)
    fc = [(hz[f"m{m}_hidden_fc_W"].astype(np.float64), hz[f"m{m}_hidden_fc_b"].astype(np.float64)) for m in range(5)]

    def logits(x, m):   # layer vector of member m -> (logits (n, 6), gate, pre)
        pre = x @ fc[m][0].T + fc[m][1] if layer == "pooled" else None
        lg, gate = C.head_logits(np.maximum(pre, 0) if layer == "pooled" else x, heads[m]); return lg, gate, pre
    wref, dev_max = [], 0.0
    for m in range(5):
        lg, gate, pre = logits(X[:, m], m); dev_max = max(dev_max, float(np.abs(lg - LG[:, m]).max()))
        w = C.eff_weights(gate, heads[m], 6)[0]
        wref.append(w.mean(0) if layer == "h" else ((w * (pre > 0)).mean(0)) @ fc[m][0])     # mean effective weight of the 6-year logit
    if dev_max > 5e-3: raise SystemExit(f"STOP: the saved {layer} does not give the saved logits (max difference {dev_max})")
    return E, X, LG, logits, wref, dev_max


def run(E, X, LG, logits, wref, arm, K, sae_k, v2_members, device, out, layer, naming=True):
    t0 = time.time(); n = len(E); mk = lambda s=0: Arm(arm, K, s, device, sae_k)   # noqa: E731
    lbar = {t: LG[:, :, t - 1].mean(1) for t in (1, 6)}
    y1, y6 = E.y1.to_numpy(float), np.where(E.study_yr == 0, E.y6, np.nan).astype(float)
    fold = Q.folds(E.pid.to_numpy()); half = Q.folds(E.pid.to_numpy(), k=2, seed=0)
    G = D.groups(E); allv = [c for g in G.values() for c in g]; AF = DC.assoc_frame(E, allv); allv_num = list(AF.columns)
    res = dict(layer=layer, arm=arm, K=K, sae_k=(sae_k or max(1, K // 16)) if arm == "sae" else None, n_exams=n, participants=int(E.pid.nunique()))
    # ---- V1 function kept (held-out folds), as S4
    L0 = {t: np.zeros((n, 5)) for t in (1, 6)}; L1 = {t: np.zeros((n, 5)) for t in (1, 6)}; ev = []
    for f in range(5):
        tr, te = fold != f, fold == f
        for m in range(5):
            a = mk().fit(X[tr, m], w_ref=wref[m]); rec = a.recon(a.encode(X[te, m])); l0 = logits(X[te, m], m)[0]; l1 = logits(rec, m)[0]
            zt = a._z(X[te, m]); zr = a._z(rec); ev.append(1 - ((zt - zr) ** 2).sum() / (zt ** 2).sum())
            for t in (1, 6): L0[t][te, m] = l0[:, t - 1]; L1[t][te, m] = l1[:, t - 1]
    r = {t: float(np.mean([np.corrcoef(L0[t][:, m], L1[t][:, m])[0, 1] for m in range(5)])) for t in (1, 6)}
    dA1 = DC.auc(y1, L1[1].mean(1)) - DC.auc(y1, L0[1].mean(1)); dA6 = DC.auc(y6, L1[6].mean(1)) - DC.auc(y6, L0[6].mean(1))
    res["V1"] = dict(r_y1=r[1], r_y6=r[6], dAUROC_y1=dA1, dAUROC_y6=dA6, recon_r2_heldout=float(np.mean(ev)),
                     pass_=bool(r[1] >= 0.98 and r[6] >= 0.98 and abs(dA1) <= 0.005 and abs(dA6) <= 0.005))
    arms = [mk().fit(X[:, m], w_ref=wref[m]) for m in range(5)]; As = [a.encode(X[:, m]) for m, a in enumerate(arms)]
    # ---- V2 seed stability, as S4 (scouting: fewer members)
    if arm in DC.SEEDED and v2_members:
        v2 = []
        for m in v2_members:
            Za = [As[m]] + [mk(s).fit(X[:, m]).encode(X[:, m]) for s in (1, 2, 3, 4)]; Zb = [mk(s).fit(X[:, m]).encode(X[:, m]) for s in (10, 11, 12, 13, 14)]
            if arm == "ica": Za = [np.abs(x) for x in Za]; Zb = [np.abs(x) for x in Zb]
            ca, _ = SAE.consensus_codes_cl(Za); cb, _ = SAE.consensus_codes_cl(Zb)
            share, med = C.act_match(ca, cb) if ca.shape[1] and cb.shape[1] else (0.0, 0.0); v2.append(dict(member=m, share=share, median_r=med))
        res["V2"] = dict(per_member=v2, share=float(np.mean([x["share"] for x in v2])), median_r=float(np.mean([x["median_r"] for x in v2])))
        res["V2"]["pass_"] = bool(res["V2"]["median_r"] >= 0.70 and res["V2"]["share"] >= 0.50)
    else:
        res["V2"] = dict(pass_=True, note="deterministic arm" if arm not in DC.SEEDED else "skipped")
    # ---- V3 families across members, as S4
    fams = DC.families_signed(As, arm in DC.DENSE)
    res["V3"] = dict(n_families=len(fams), pass_=bool(len(fams) >= max(1, round(0.25 * K))))
    # ---- naming and V4, as S4
    rows, FA = [], []
    for k, (fam, sg) in enumerate(fams):
        act = DC.fam_act(As, fam, sg); FA.append(act); row = dict(family=k, n_members=len(fam), r_lbar1=float(np.corrcoef(act, lbar[1])[0, 1]), r_lbar6=float(np.corrcoef(act, lbar[6])[0, 1]),
                                                                 auc_y1=DC.auc(y1, act), auc_y6=DC.auc(y6, act))
        if naming:
            lab, tot, sh = DC.shapley_label(E, G, act, fold); hl, av = [], []
            for hh in (0, 1):
                S = E[half == hh].reset_index(drop=True); ah = act[half == hh]
                hl.append(DC.shapley_label(S, G, ah, Q.folds(S.pid.to_numpy()))[0]); av.append(DC.assoc_vector(AF[half == hh].reset_index(drop=True), ah))
            ok = np.isfinite(av[0]) & np.isfinite(av[1]); assoc = DC.assoc_vector(AF, act); top = np.argsort(-np.nan_to_num(np.abs(assoc)))[:5]
            row.update(label=lab, cv_r2=tot, **{f"sh_{g}": v for g, v in sh.items()}, label_half_a=hl[0], label_half_b=hl[1],
                       assoc_half_corr=float(np.corrcoef(av[0][ok], av[1][ok])[0, 1]) if ok.sum() > 3 else np.nan,
                       top_assoc="; ".join(f"{allv_num[i]} {assoc[i]:+.2f}" for i in top))
        rows.append(row)
    F = pd.DataFrame(rows)
    if naming and len(F):
        named = F[F.label.isin(list(G))]; agree = float((named.label_half_a == named.label_half_b).mean()) if len(named) else 0.0
        res["V4"] = dict(median_assoc_half_corr=float(F.assoc_half_corr.median()), label_agreement_named=agree, n_named=int(len(named)),
                         pass_=bool(F.assoc_half_corr.median() >= 0.70 and agree >= 0.70))
        res["labels"] = F.label.value_counts().to_dict()
    else:
        res["V4"] = dict(pass_=False, note="no family" if naming else "naming skipped"); res["labels"] = {}
    res["valid"] = bool(res["V1"]["pass_"] and res["V2"]["pass_"] and res["V3"]["pass_"] and res["V4"]["pass_"])
    # ---- descriptive: are the families more than copies of the risk score?
    if len(F):
        ev_ = np.linalg.eigvalsh(np.corrcoef(np.array(FA))) if len(FA) > 1 else np.array([1.0]); ev_ = np.maximum(ev_, 0) / max(ev_.sum(), 1e-12)
        nr = F[np.abs(F.r_lbar6) < 0.5]
        res["distinct"] = dict(family_effective_dims=float(1 / (ev_ ** 2).sum()), median_abs_r_lbar6=float(np.abs(F.r_lbar6).median()), n_non_risk=int(len(nr)),
                               n_non_risk_named=int(nr.label.isin(list(G)).sum()) if naming else None,
                               n_non_risk_named_stable=int((nr.label.isin(list(G)) & (nr.label_half_a == nr.label) & (nr.label_half_b == nr.label)).sum()) if naming else None)
    res["minutes"] = round((time.time() - t0) / 60, 1)
    tag = f"{layer}_{arm}_K{K}" + (f"_k{sae_k}" if arm == "sae" and sae_k else "")
    (out / f"r1_{tag}.json").write_text(json.dumps(res, indent=1, default=str)); F.to_csv(out / f"r1_{tag}_families.csv", index=False)
    v1, v4 = res["V1"], res["V4"]
    print(f"{tag:22s} V1 r1 {v1['r_y1']:.3f} r6 {v1['r_y6']:.3f} dA {v1['dAUROC_y1']:+.4f}/{v1['dAUROC_y6']:+.4f} {'P' if v1['pass_'] else 'F'} | V2 {'P' if res['V2']['pass_'] else 'F'}"
          f" | V3 fam {len(fams)} {'P' if res['V3']['pass_'] else 'F'} | V4 corr {v4.get('median_assoc_half_corr', float('nan')):.2f} agree {v4.get('label_agreement_named', float('nan')):.2f}"
          f" {'P' if v4['pass_'] else 'F'} | valid {res['valid']} | {res['labels']} | {res.get('distinct')} | {res['minutes']} min", flush=True)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("assembled"); ap.add_argument("heads"); ap.add_argument("out")
    ap.add_argument("--layer", default="h", choices=("h", "pooled")); ap.add_argument("--K", default="64"); ap.add_argument("--arms", default=",".join(C.ARMS))
    ap.add_argument("--sae-k", default="0"); ap.add_argument("--v2-members", default="0,1"); ap.add_argument("--device", default="cpu")
    ap.add_argument("--rows", type=int, default=0, help="test only: use the first N exams"); ap.add_argument("--no-naming", action="store_true")
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    E, X, LG, logits, wref, dmax = load(a.assembled, a.heads, a.layer); print(f"layer {a.layer}: {X.shape}, saved logits reproduced within {dmax:.2e}", flush=True)
    if a.rows: E, X, LG = E.iloc[:a.rows].reset_index(drop=True), X[:a.rows], LG[:a.rows]
    v2m = [int(x) for x in a.v2_members.split(",") if x != ""]
    for K in map(int, a.K.split(",")):
        for arm in a.arms.split(","):
            for sk in (map(int, a.sae_k.split(",")) if arm == "sae" else [0]):
                tag = f"{a.layer}_{arm}_K{K}" + (f"_k{sk}" if arm == "sae" and sk else "")
                if (out / f"r1_{tag}.json").exists() and not a.rows: print("done before:", tag, flush=True); continue
                run(E, X, LG, logits, wref, arm, K, sk, v2m, a.device, out, a.layer, naming=not a.no_naming)


if __name__ == "__main__":
    main()
