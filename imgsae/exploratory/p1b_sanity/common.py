"""Shared helpers for Phase 1b Stage A (exploratory, dev data only; plan docs/SANITY_PLAN_v1.md).
Reuses the production code unchanged: scripts/p1_probe (probe, cluster bootstrap), scripts/p1_assemble.prep (input transform),
scripts/p1_fit (halves, eval rows, Model, feature_table, load_perturb) and p1_checks/c1b_chimera_other.chimera_both (both chimera rules).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
for _p in (ROOT, ROOT / "scripts", ROOT / "exploratory" / "p1_checks"): sys.path.insert(0, str(_p))
import p1_assemble as A  # noqa: E402
import p1_fit as F  # noqa: E402
import p1_probe as PR  # noqa: E402
import c1b_chimera_other as CB  # noqa: E402
from imgsae import atlas, ladder, sae  # noqa: E402

P1 = PR.P1; RES = HERE / "results"; LOGS = HERE / "logs"; RES.mkdir(exist_ok=True); LOGS.mkdir(exist_ok=True)
Z_COLS = [0] + [3 + 3 * j for j in range(8)]  # z column of each [z, y, x] block in pos (as in c2_probe_position.py)
XY_COLS = [c for c in range(27) if c not in Z_COLS]
T0 = time.time()


def log(*a):
    print(f"[{(time.time() - T0) / 60:6.1f} min]", *a, flush=True)


def concepts():
    return json.load(open(P1 / "concepts.json"))


def gates():
    return json.load(open(P1 / "gates.json"))


def load_rows(keys):
    """only the requested arrays of data/p1/rows.npz (the file is 4.9 GB)."""
    z = np.load(P1 / "rows.npz"); return {k: z[k] for k in keys}


def refpos(C):
    """raw reference (n x 56: 28 local + 28 context) and position (n x 27) in rows.npz order; cached as float16 (the stored dtype)."""
    cache = RES / "cache_refpos.npz"
    if cache.exists():
        z = np.load(cache); return z["ref"].astype(np.float32), z["pos"].astype(np.float32)
    ref, pos = [], []
    for s in C["scans"]:
        z = np.load(P1 / "scans" / f"{s['id']}.npz"); ref.append(z["ref"]); pos.append(z["pos"])
    ref, pos = np.concatenate(ref), np.concatenate(pos); np.savez(cache, ref=ref, pos=pos)
    return ref.astype(np.float32), pos.astype(np.float32)


def zrel(gidx, scan, nfreq=4):
    """label-free scan-relative z: token z index scaled to [-1, 1] over the scan's valid-token z range, + sin/cos(2^k pi z), k < nfreq (9 cols)."""
    z = gidx[:, 0].astype(np.float32); out = np.zeros(len(z), np.float32)
    for s in np.unique(scan):
        ii = scan == s; lo, hi = z[ii].min(), z[ii].max(); out[ii] = 2 * (z[ii] - lo) / max(hi - lo, 1) - 1
    c = out[:, None]; return np.concatenate([c] + [f(2 ** k * np.pi * c) for k in range(nfreq) for f in (np.sin, np.cos)], 1).astype(np.float32)


def raw_ref_sets(ref, pos, zr):
    """reference ladder (raw, before prep). R0 HU stats (hist 22 + mean + sd), R1 + texture, R2 + 48 mm context, R3 + body x/y,
    R4 + scan-relative z; 'run' = as in the run (z = vertebral level from the masks, label-derived)."""
    xy = pos[:, XY_COLS]
    return dict(R0=ref[:, :24], R1=ref[:, :28], R2=ref, R3=np.hstack([ref, xy]), R4=np.hstack([ref, xy, zr]), run=np.hstack([ref, pos]))


def prep_apply(X, mu, sc):
    """the assemble transform with stored parameters (centre, row unit-norm, global scale) - same maths as p1_fit.load_perturb."""
    X = X.astype(np.float32) - mu; X /= np.maximum(np.linalg.norm(X, axis=1, keepdims=True), 1e-9); return X / sc


def scan_labels(C):
    S = C["scans"]
    return dict(manufacturer_siemens=np.array([s["manufacturer"].strip().lower() == "siemens" for s in S], float),
                institute_I=np.array([s["institute"] == "I" for s in S], float), kvp_ge120=np.array([float(s["kvp"] or 0) >= 120 for s in S], float),
                contrast=np.array([s["contrast"] for s in S], float))


def load_perturb_all(C, R, r3_params=None):
    """production perturbation inputs (X_ctfm, X_null, X_ref) + the label-free R3 reference for the same rows (if r3_params given)."""
    P = F.load_perturb(C, R)
    if r3_params is None: return P
    ids = [s["id"] for s in C["scans"]]
    for kind, d in P.items():
        rows, X3 = [], []
        for f in sorted((P1 / "perturb" / kind).glob("*.npz")):
            if f.stem not in ids: continue
            si = ids.index(f.stem); z = np.load(f); orig = np.flatnonzero(R["scan"] == si)
            if len(orig) != len(z["occ"]): continue
            rows.append(orig)
            X3.append(np.hstack([z["ref"].astype(np.float32), z["pos"].astype(np.float32)[:, XY_COLS]]))
        rows = np.concatenate(rows); assert np.array_equal(rows, d["rows"]), kind
        d["R3"] = prep_apply(np.concatenate(X3), *r3_params)
    return P


class Ctx:
    """everything the ladder needs for one replicate (same halves, eval rows and rules as scripts/p1_fit.py)."""

    def __init__(self, rep, R, C, Gt, pert_in):
        self.rep, self.R, self.C, self.pert_in = rep, R, C, pert_in; S = C["scans"]; scan = R["scan"]
        self.hA = F.halves(S, rep); self.E = dict(A=F.eval_rows(scan, self.hA, seed=rep), B=F.eval_rows(scan, ~self.hA, seed=rep + 50))
        self.rows = dict(A=np.flatnonzero(self.hA[scan]), B=np.flatnonzero(~self.hA[scan]))
        self.G, self.elig, self.gates = C["groups"], C["eligible"], Gt["token"]; self.cls_of = {g: ("path" if g == "kidney_cyst" else "anat") for g in self.G}
        self.gated_set = [g for g in self.elig if self.gates.get(g, {}).get("gated")]; self.scan_labels = scan_labels(C)

    def fit(self, meth, cfg, X, L0=None, seed_offset=0):
        """two half models with the production seeds (seed = rep * 7 + half index)."""
        return {h: F.Model(meth, cfg, L0=L0, seed=self.rep * 7 + hi + seed_offset).fit(X[self.rows[h]]) for hi, h in enumerate("AB")}


class LazyPert:
    """perturbation codes for feature_table, encoded on access and not cached, so only one perturbation kind is in memory at a time
    (feature_table only reads P['Z_orig'] and P['Z_pert'] inside its loop over kinds; values are identical to precomputed codes)."""

    def __init__(self, model, X, P, keep, pkey):
        self.model, self.X, self.P, self.keep, self.pkey = model, X, P, keep, pkey

    def __getitem__(self, k):
        if k == "Z_orig": return self.model.encode(self.X[self.P["rows"][self.keep]])
        if k == "Z_pert": return self.model.encode(self.P[self.pkey][self.keep])
        raise KeyError(k)


def evaluate(mods, X, pkey, ctx, n_match=425, n_draw=20, keep_tables=False):
    """ladder for two half models: R1, and per chimera rule ('orig' = as run, 'neutral' = 'other' adjacent to all) the C(tau) area,
    the area with features subsampled to n_match (n_draw draws; feature-count matched), C(0.7), and medians of t / sel / r_pert over V0 features."""
    F.ladder.chimera = CB.chimera_both  # feature_table calls ladder.chimera through the module; returns 'neutral', stashes 'orig'
    R, C, scan, lab, E = ctx.R, ctx.C, ctx.R["scan"], ctx.R["lab"], ctx.E
    Z = {h: {e: mods[h].encode(X[E[e]]) for e in "AB"} for h in "AB"}
    r1, r1med = sae.act_match(np.vstack([Z["A"]["A"], Z["A"]["B"]]), np.vstack([Z["B"]["A"], Z["B"]["B"]]))
    out = dict(R1=r1, R1_med=r1med, n_feat={h: int(Z[h]["A"].shape[1]) for h in "AB"}, L0={h: float((Z[h][h] > 0).sum(1).mean()) for h in "AB"})
    acc = {f"{k}_{t}": [] for k in ("area", "area_matched", "C07") for t in ("orig", "neutral")}; stats = {k: [] for k in ("n_v0", "chim_orig", "chim_neutral")}
    med = {k: [] for k in ("t", "sel", "r_pert")}; tables = {}; rng = np.random.default_rng(ctx.rep)
    for h, o in (("A", "B"), ("B", "A")):
        Eo = E[o]; pert = {}
        for kind, P in ctx.pert_in.items():
            keep = np.isin(P["rows"], Eo) | np.isin(scan[P["rows"]], np.flatnonzero(ctx.hA if o == "A" else ~ctx.hA))
            if keep.sum() >= 50: pert[kind] = LazyPert(mods[h], X, P, keep, pkey)
        T = F.feature_table(Z[h][h], Z[o][h], Z[h][o], lab[Eo], scan[Eo], ctx.G, ctx.elig, C["adjacency"], ctx.gates, pert, ctx.scan_labels,
                            list(ctx.scan_labels), ctx.cls_of)
        ch_o = CB.STASH["orig"]; v0 = T["v0"]; base_o = v0 & ~ch_o & (T["concept"] != "other")
        v_o = np.where(base_o, np.fmin(np.fmin(T["t"], T["sel"]), T["r_pert"]), 0.0); v_o = np.where(base_o & np.isnan(T["r_pert"]), np.nan, v_o)  # as p1_fit
        Fn = len(v0)
        for tag, v in (("orig", v_o), ("neutral", T["v"])):
            vv = np.nan_to_num(v, nan=0.0); acc[f"area_{tag}"].append(ladder.coverage_curve(vv, T["concept"], ctx.gated_set)[1])
            acc[f"C07_{tag}"].append(len({c for c, x in zip(T["concept"], vv) if x >= .7 and c in ctx.gated_set}))
            if Fn > n_match:
                ar = [ladder.coverage_curve(vv[ii], T["concept"][ii], ctx.gated_set)[1] for ii in (np.sort(rng.choice(Fn, n_match, replace=False)) for _ in range(n_draw))]
                acc[f"area_matched_{tag}"].append(float(np.mean(ar)))
            else: acc[f"area_matched_{tag}"].append(acc[f"area_{tag}"][-1])
        stats["n_v0"].append(int(v0.sum())); stats["chim_orig"].append(int((ch_o & v0).sum())); stats["chim_neutral"].append(int((T["chimeric"] & v0).sum()))
        for k in med: med[k].append(T[k][v0])
        if keep_tables: tables[h] = {**T, "chimeric_orig": ch_o, "v_orig": v_o}
    for k, v in acc.items(): out[k] = float(np.mean(v)) if not k.startswith("C07") else v
    nv0 = max(sum(stats["n_v0"]), 1); out.update(n_v0=stats["n_v0"], chim_share_orig=sum(stats["chim_orig"]) / nv0, chim_share_neutral=sum(stats["chim_neutral"]) / nv0)
    for k, v in med.items(): out[f"median_{k}_v0"] = float(np.nanmedian(np.concatenate(v))) if sum(len(x) for x in v) else float("nan")
    return (out, tables) if keep_tables else out


def dump(obj, path):
    json.dump(obj, open(path, "w"), indent=1, default=lambda o: o.tolist() if isinstance(o, np.ndarray) else float(o))
