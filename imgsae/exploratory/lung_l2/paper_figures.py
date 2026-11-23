"""Lung L2, task 5: paper figures from committed result files only (no new analysis; plan docs/FIGURE_PLAN.md). Plain SVG with the helpers and
the validated two-slot palette of s6_figures.py (blue #2a78d6, orange #eb6834; ink and grey from the reference palette).
  fig1_mechanism.svg   (a) schematic of overlapping slices placed at the slice thickness; (b) one public NLST dev exam, coronal, as Sybil sees
                       it and at the true spacing (PNG from fig1_coronal.py, embedded; written OUTSIDE git because it holds CT pixels)
  fig6_exposure.svg    share of studies with a strongly (<= 0.65) or moderately (<= 0.85) overlapping series, and with both an overlapping and
                       a contiguous series (results/x12/x12_overlap_prevalence.json)
usage (venv python): python paper_figures.py <out dir for figures without CT pixels> [--ct-dir <dir with fig1_coronal_*.png and json>]
"""
import argparse
import base64
import json
from pathlib import Path

from s6_figures import BASE, BLUE, GRID, INK, INK2, MUTED, ORANGE, SURF, Svg, ticks

HERE = Path(__file__).resolve().parent


def rect(s, x, y, w, h, fill, stroke="none", sw=0, op=1.0, rx=0):
    s.el.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}" fill-opacity="{op}" stroke="{stroke}" stroke-width="{sw}" rx="{rx}"/>')


def fig1(ct_dir, out):
    info = json.loads((ct_dir / "fig1_coronal.json").read_text()); s = Svg(1010, 740)
    s.text(20, 28, "Figure 1. Sybil places overlapping slices at the slice thickness, so the chest is stretched along the body axis", 15, weight="bold")
    # (a) schematic
    s.text(20, 62, "a", 14, weight="bold"); s.text(40, 62, "Slices 2.5 mm thick, reconstructed every 1.25 mm (overlap 50%)", 12, INK2)
    x0, y0, mm = 70, 90, 9.0                                                   # 9 px per mm
    for col, (xc, step, lab) in enumerate(((x0, 1.25, "True positions (ImagePositionPatient)"), (x0 + 210, 2.5, "Where Sybil places them (SliceThickness)"))):
        s.text(xc - 20, y0 - 8, lab, 11, INK2)
        for k in range(8):
            top = y0 + k * step * mm; rect(s, xc + (k % 2) * 14, top, 110, 2.5 * mm, BLUE if col == 0 else ORANGE, op=0.28, stroke=BLUE if col == 0 else ORANGE, sw=1)
        h = (7 * step + 2.5) * mm; s.line(xc - 10, y0, xc - 10, y0 + h, INK2, 1.5); s.text(xc - 14, y0 + h + 16, f"{7 * step + 2.5:g} mm", 11, INK, "start")
    s.text(x0, 330, "Eight slices cover 11.25 mm of chest, but Sybil spreads them over 20 mm:", 11, INK); s.text(x0, 346, "the anatomy is stretched 2-fold in z for this protocol.", 11, INK)
    # (b) the two coronal images, same scale in Sybil's frame (columns 0.703 mm, rows 2.5 mm as Sybil assumes), head up
    vs = info["sybil_voxel_spacing_after_resample_mm"]; W = 190.0; H = 200 * vs[2] / vs[0] * (W / 256)
    s.text(470, 62, "b", 14, weight="bold"); s.text(490, 62, f"One NLST exam ({info['maker']}, {info['thickness_mm']:g} mm every {info['true_spacing_mm']:g} mm), coronal, Sybil's 200-slice input", 12, INK2)
    bx = [(490, "fig1_coronal_main.png", "As Sybil reads it", f"{info['T_resampled_main']} slices of chest for a 200-slice box:", "lung apex and base cut off", info["padded_rows_main"]),
          (720, "fig1_coronal_zfix.png", "At the true spacing (z-fix)", f"{info['T_resampled_zfix']} slices of chest; {len(info['padded_rows_zfix'])} padded slices", "(Sybil's mid-grey padding)", info["padded_rows_zfix"])]
    yb = 110; flip = info["positions_increase_with_index"]                       # index 0 = feet end -> flip so the head is up
    for x, png, t1, t2, t3, pad in bx:
        b64 = base64.b64encode((ct_dir / png).read_bytes()).decode("ascii")
        tr = f' transform="translate(0,{2 * yb + H:.1f}) scale(1,-1)"' if flip else ""
        s.el.append(f'<image x="{x}" y="{yb}" width="{W:.1f}" height="{H:.1f}" preserveAspectRatio="none" href="data:image/png;base64,{b64}"{tr}/>')
        rect(s, x, yb, W, H, "none", INK2, 1)
        s.text(x, yb + H + 18, t1, 12, INK, weight="bold"); s.text(x, yb + H + 34, t2, 11, INK2); s.text(x, yb + H + 48, t3, 11, INK2)
        if pad:                                                                # bracket the padding bands
            rows = sorted(pad); bands, start = [], rows[0]
            for a_, b_ in zip(rows, rows[1:] + [None]):
                if b_ != a_ + 1: bands.append((start, a_)); start = b_
            for r0, r1 in bands:
                y_a, y_b = (yb + H - (r1 + 1) * H / 200, yb + H - r0 * H / 200) if flip else (yb + r0 * H / 200, yb + (r1 + 1) * H / 200)
                s.line(x + W + 6, y_a, x + W + 6, y_b, ORANGE, 3)
        else:
            for yy in (yb, yb + H): s.line(x - 6, yy, x + W + 6, yy, BLUE, 3)  # the box edges cut the stretched chest
    sb = 100 / vs[2] * H / 200; s.line(950, yb + H, 950, yb + H - sb, INK, 2); s.text(958, yb + H - sb / 2 - 4, "100 mm", 10, INK); s.text(958, yb + H - sb / 2 + 9, "(as Sybil", 9, MUTED)
    s.text(958, yb + H - sb / 2 + 20, "assumes)", 9, MUTED)
    s.text(470, 730, "Orange bars: padded slices. Blue lines: box edges cutting the chest. Public NLST series (IDC); no model output is shown.", 10, MUTED)
    s.save(out / "fig1_mechanism.svg")


def fig6(out):
    d = json.loads((HERE / "results" / "x12" / "x12_overlap_prevalence.json").read_text())["sets"]
    rows = [("NLST (2002-2004 scanners)", "nlst"), ("Modern scanner models (2013 or later)", "modern_scanner_models"), ("Public chest CT collections from 2015", "modern_collections_2015_on")]
    s = Svg(920, 420); s.text(20, 28, "Figure 6. How often a chest CT study holds an overlapping series (public data, header only)", 15, weight="bold")
    panels = [(["Studies with a series of", "slice spacing / thickness"], [("<= 0.65 (strong overlap)", "studies_any_le_0p65", BLUE), ("<= 0.85 (moderate or strong)", "studies_any_le_0p85", ORANGE)], 0.40),
              (["Studies with BOTH a strongly overlapping", "and a contiguous series (series choice decides)"], [("both present", "studies_both_le_0p65_and_contiguous", BLUE)], 0.12)]
    x_lab, top = 20, 80
    for pi, (title, series, xmax) in enumerate(panels):
        px, pw = (300, 270) if pi == 0 else (620, 250)
        s.text(px, top - 24, title[0], 11, INK2); s.text(px, top - 10, title[1], 11, INK2)
        for t in ticks(0, xmax, 3):
            xx = px + t / xmax * pw; s.line(xx, top, xx, top + 3 * 80, GRID); s.text(xx, top + 3 * 80 + 14, f"{t * 100:.0f}%", 10, MUTED, "middle")
        for ri, (lab, key) in enumerate(rows):
            yc = top + 30 + ri * 80
            if pi == 0: s.text(x_lab, yc + 4, lab, 11, INK); s.text(x_lab, yc + 19, f"{d[key]['studies']:,} studies, {d[key]['patients']:,} people", 10, MUTED)
            for si, (slab, k, col) in enumerate(series):
                v = d[key][k]; y = yc - 8 + si * 18 if len(series) == 2 else yc
                s.line(px + v["lo"] / xmax * pw, y, px + min(v["hi"], xmax) / xmax * pw, y, col, 2); s.dot(px + v["share"] / xmax * pw, y, col)
                s.text(px + min(v["hi"], xmax) / xmax * pw + 8, y + 4, f"{v['share'] * 100:.1f}%", 10, INK2)
    for si, (slab, k, col) in enumerate(panels[0][1]): s.dot(310 + si * 200, top + 3 * 80 + 42, col); s.text(320 + si * 200, top + 3 * 80 + 46, slab, 10, INK2)
    s.text(20, 405, "Dots: share of studies; lines: 95% intervals (bootstrap over patients). Series selection, filters and sets as in RESULTS_L2.md 3i.", 10, MUTED)
    s.save(out / "fig6_exposure.svg")


def fig5(out):
    """exposure in non-overlapping parts (Neon's assessment): strong overlap without a contiguous alternative, strong overlap with a contiguous
    series in the same study (the series choice decides), moderate overlap only (0.65-0.85; hatched; tested in X11 only); interval on the strong
    total; a strip of per-collection series shares."""
    import csv
    d = json.loads((HERE / "results" / "x12" / "x12_overlap_prevalence.json").read_text())["sets"]
    rows = [("NLST (2002-2004 scanners)", "nlst"), ("Modern scanner models (2013 or later)", "modern_scanner_models"), ("Public chest CT collections from 2015", "modern_collections_2015_on")]
    s = Svg(940, 470); s.text(20, 28, "Figure 5. How often a chest CT study holds an overlapping series (public data, DICOM headers only)", 15, weight="bold")
    s.el.append(f'<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="{SURF}"/>'
                f'<line x1="0" y1="0" x2="0" y2="6" stroke="{MUTED}" stroke-width="2"/></pattern></defs>')
    px, pw, xmax, top, rh = 330, 520, 0.40, 70, 70
    for t in ticks(0, xmax, 4):
        xx = px + t / xmax * pw; s.line(xx, top - 6, xx, top + 3 * rh - 10, GRID); s.text(xx, top + 3 * rh + 4, f"{t * 100:.0f}%", 10, MUTED, "middle")
    s.text(px, top + 3 * rh + 20, "share of studies", 10, MUTED)
    for ri, (lab, key) in enumerate(rows):
        v = d[key]; y = top + ri * rh; h = 22
        s.text(20, y + 14, lab, 11, INK); s.text(20, y + 29, f"{v['studies']:,} studies, {v['patients']:,} people", 10, MUTED)
        strong, both, mod = v["studies_any_le_0p65"]["share"], v["studies_both_le_0p65_and_contiguous"]["share"], v["studies_any_le_0p85"]["share"] - v["studies_any_le_0p65"]["share"]
        parts = [(strong - both, BLUE, None), (both, "#86b6ef", None), (mod, "url(#hatch)", MUTED)]; x = px
        for w, fill, stroke in parts:
            ww = w / xmax * pw
            if ww > 0: rect(s, x, y, max(ww - 2, 0.5), h, fill, stroke or "none", 1 if stroke else 0)
            x += ww
        lo, hi = v["studies_any_le_0p65"]["lo"], v["studies_any_le_0p65"]["hi"]; yi = y + h + 7
        s.line(px + lo / xmax * pw, yi, px + hi / xmax * pw, yi, INK2, 1.5)
        s.text(px + strong / xmax * pw + 4, y - 4, f"strong {strong * 100:.1f}%", 10, INK2)
        s.text(px + (strong + mod) / xmax * pw + 6, y + 15, f"+ moderate {mod * 100:.1f}%", 10, MUTED)
    ly = top + 3 * rh + 40
    for i, (lab, fill, stroke) in enumerate((("strong overlap (ratio <= 0.65), no contiguous series in the study", BLUE, None),
                                             ("strong overlap, a contiguous series also present (the series sent to Sybil decides)", "#86b6ef", None),
                                             ("moderate overlap only (0.65 to 0.85): effect tested in X11 only", "url(#hatch)", MUTED))):
        rect(s, 20, ly + i * 18 - 9, 14, 10, fill, stroke or "none", 1 if stroke else 0); s.text(40, ly + i * 18, lab, 10, INK2)
    s.text(560, ly - 2, "black line: 95% interval of the strong total", 10, MUTED)
    # per-collection strip (collections with >= 20 patients; series level)
    cols = [r_ for r_ in csv.DictReader(open(HERE / "results" / "x12" / "x12_per_collection.csv", encoding="utf-8")) if int(r_["patients"]) >= 20 and r_["collection_id"] != "nlst"]
    sy = ly + 78; s.text(20, sy, f"Per collection ({len(cols)} public chest CT collections with >= 20 people, NLST excluded): share of series with strong overlap", 10, INK2)
    for t in (0, 0.25, 0.5):
        xx = px + t / 0.5 * pw; s.text(xx, sy + 34, f"{t * 100:.0f}%", 10, MUTED, "middle")
    s.line(px, sy + 18, px + pw, sy + 18, BASE, 1)
    for r_ in cols: s.dot(px + min(float(r_["le_0p65"]), 0.5) / 0.5 * pw, sy + 18, BLUE, 3.5)
    s.text(20, 462, "Header-only audit of IDC (mostly diagnostic and oncology CT, not screening); study-level shares; intervals by bootstrap over patients. Filters and sets: RESULTS_L2.md 3i.", 9, MUTED)
    s.save(out / "fig5_exposure.svg")


def mark(s, shape, x, y, fill, r=5, hollow=False):
    f, st = (SURF, fill) if hollow else (fill, SURF)
    if shape == "circle": s.el.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{f}" stroke="{st}" stroke-width="{2 if hollow else 1.5}"/>')
    elif shape == "square": s.el.append(f'<rect x="{x - r:.1f}" y="{y - r:.1f}" width="{2 * r}" height="{2 * r}" fill="{f}" stroke="{st}" stroke-width="{2 if hollow else 1.5}"/>')
    elif shape == "diamond": s.el.append(f'<path d="M{x:.1f},{y - r - 1:.1f} L{x + r + 1:.1f},{y:.1f} L{x:.1f},{y + r + 1:.1f} L{x - r - 1:.1f},{y:.1f} Z" fill="{f}" stroke="{st}" stroke-width="{2 if hollow else 1.5}"/>')
    else: s.el.append(f'<path d="M{x:.1f},{y - r - 1:.1f} L{x + r + 1:.1f},{y + r:.1f} L{x - r - 1:.1f},{y + r:.1f} Z" fill="{f}" stroke="{st}" stroke-width="{2 if hollow else 1.5}"/>')


SCORES = [("sybil", "Sybil", BLUE, "circle"), ("form", "Form (radiologists' findings + age, sex, smoking; fitted on NLST train)", ORANGE, "square"),
          ("brock", "Brock (published, not fitted)", MUTED, "triangle"), ("rule", "Fixed rule: Lung-RADS >= 4A (L4), >= 3 (L3), radiologists' call (R)", INK, "diamond")]
RULE = {"L4": "lung_rads_4A", "L3": "lung_rads_3", "R": "radiologists_call"}


def fig6(out):
    """clinical context (exploratory, all NLST test exams): operating points at dev-matched false-alarm levels, 1 year all screens and 6 years
    baseline; threshold transfer dev -> test (cancer-free cuts keep their false-alarm level; cuts matched on dev cancers lose Sybil's sensitivity)."""
    X9 = {sp: json.loads((HERE / "results" / "x9" / f"x9_rules_thresholds_{sp}.json").read_text())["thresholds"] for sp in ("dev", "test")}
    P5 = json.loads((HERE / "results" / "x7" / "x7_sensitivity_test.json").read_text())["P5_harm_at_dev_cuts"]
    s = Svg(1040, 830); s.text(20, 28, "Figure 6. Clinical context on the NLST test split (exploratory): the same false-alarm levels, and what happens to cuts set on development data", 14, weight="bold")

    def get(T, key): return T["table"][key]
    # (a) operating points
    for pi, (E, lab, ylo, yhi) in enumerate((("E1", "1 year, all screens", 0.6, 1.0), ("E4", "6 years, baseline screens", 0.3, 0.85))):
        T = X9["test"][E]; c = T["counts"]; px, py, pw, ph = 90 + pi * 500, 90, 400, 290
        s.text(px - 70, py - 30, "a" if pi == 0 else "", 14, weight="bold")
        s.text(px, py - 30, f"{lab}: {c['exams']:,} exams, {c['cancers']} cancers ({c['prevalence'] * 100:.1f}%)", 12, INK)
        X = lambda v: px + v / 420 * pw; Y = lambda v: py + ph - (v - ylo) / (yhi - ylo) * ph   # noqa: E731
        for t in range(0, 421, 100): s.line(X(t), py, X(t), py + ph, GRID); s.text(X(t), py + ph + 14, str(t), 10, MUTED, "middle")
        for t in ticks(ylo, yhi, 4): s.line(px, Y(t), px + pw, Y(t), GRID); s.text(px - 6, Y(t) + 4, f"{t * 100:.0f}%", 10, MUTED, "end")
        s.text(px + pw / 2, py + ph + 30, "false alarms per 1,000 exams", 10, INK2, "middle")
        s.text(px - 55, py - 10, "sensitivity", 10, INK2)
        for lvl in ("L4", "L3", "R"):
            pts = []
            for key, name, col, shp in SCORES:
                r_ = get(T, RULE[lvl] if key == "rule" else f"{key}@OP_{lvl}"); se, fa = r_["sensitivity"], r_["fa_per_1000_exams"]
                s.line(X(fa["lo"]), Y(se["est"]), X(fa["hi"]), Y(se["est"]), col, 1); s.line(X(fa["est"]), Y(se["lo"]), X(fa["est"]), Y(se["hi"]), col, 1)
                mark(s, shp, X(fa["est"]), Y(se["est"]), col); pts.append((fa["est"], se["est"], r_["counts"]["tp"], col))
            fx = sum(p[0] for p in pts) / len(pts); s.text(X(fx), py - 8, lvl, 11, INK2, "middle", "bold")
        lab_pts = {k: get(T, RULE["L3"] if k == "rule" else f"{k}@OP_L3") for k, _, _, _ in SCORES}
        yy = py + ph + 48
        s.text(px, yy, "At L3, cancers caught: " + ", ".join(f"{nm.split(' (')[0].split(':')[0]} {lab_pts[k]['counts']['tp']}/{c['cancers']}" for k, nm, _, _ in SCORES), 10, INK2)
    for i, (key, name, col, shp) in enumerate(SCORES): mark(s, shp, 40 + (i % 2) * 500, 490 + (i // 2) * 18, col); s.text(52 + (i % 2) * 500, 494 + (i // 2) * 18, name, 10, INK2)
    s.text(20, 540, "Levels: cuts set on cancer-free DEV exams to the dev false-alarm share of Lung-RADS >= 4A (L4), >= 3 (L3) and the radiologists' call (R). Lines: 95% participant-bootstrap intervals.", 9, MUTED)
    s.text(20, 553, "1 year: the form and the fixed rules use the radiologists' reads, which also triggered the work-up (not blind to the outcome); 6 years at baseline avoids most of this and the prior-scan advantage.", 9, MUTED)
    # (b) threshold transfer, 1 year all screens: dev -> test
    s.text(20, 590, "b", 14, weight="bold"); s.text(40, 590, "Threshold transfer, 1 year, all screens: development (hollow) -> test (filled)", 12, INK)
    rows = []
    for key, nm, col, shp in SCORES[:2] + SCORES[3:]:
        k = RULE["L3"] if key == "rule" else f"{key}@OP_L3"; d_, t_ = get(X9["dev"]["E1"], k), get(X9["test"]["E1"], k)
        rows.append(("cut set on cancer-free dev exams (L3)", nm.split(" (")[0].split(":")[0], col, shp, d_["sensitivity"]["est"], t_["sensitivity"]["est"], d_["fa_per_1000_exams"]["est"], t_["fa_per_1000_exams"]["est"]))
    tgt = P5["dev_target_sensitivity"]
    for key, nm, col, shp, tk in (("sybil", "Sybil", BLUE, "circle", "sybil"), ("form", "Form", ORANGE, "square", "C1_form")):
        r_ = P5["rad"]["table"][tk]; rows.append(("cut matched on dev CANCERS (radiologists' dev sensitivity)", nm, col, shp, tgt, r_["sensitivity"], None, r_["fa_per_1000_exams"]))
    rows.append(("cut matched on dev CANCERS (radiologists' dev sensitivity)", "Radiologists' call", INK, "diamond", tgt, P5["radiologists_test_sensitivity"], None, P5["radiologists_fa_per_1000_exams"]))
    bx, bw, by = 330, 300, 606; X = lambda v: bx + (v - 0.5) / 0.5 * bw   # noqa: E731
    ys, grp, y = [], None, by
    for g, *_ in rows:
        if g != grp: y += 18; grp = g
        ys.append(y); y += 20
    bottom = ys[-1] + 10
    for t in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0): s.line(X(t), by, X(t), bottom, GRID); s.text(X(t), bottom + 14, f"{t * 100:.0f}%", 10, MUTED, "middle")
    s.text(bx + bw / 2, bottom + 28, "sensitivity", 10, INK2, "middle"); s.text(bx + bw + 30, by + 4, "false alarms per 1,000 (dev -> test)", 10, INK2)
    grp = None
    for i, (g, nm, col, shp, sd, st, fd, ft) in enumerate(rows):
        y = ys[i]
        if g != grp: s.text(20, y - 16, g, 10, INK2, weight="bold"); grp = g
        s.text(220, y + 4, nm, 10, INK); s.line(X(sd), y, X(st), y, col, 2); mark(s, shp, X(sd), y, col, 5, hollow=True); mark(s, shp, X(st), y, col, 5)
        s.text(bx + bw + 30, y + 4, (f"{fd:.0f} -> {ft:.0f}" if fd is not None else f"(dev not matched) -> {ft:.0f}") + f";  sensitivity {sd * 100:.0f}% -> {st * 100:.0f}%", 10, INK2)
    s.text(20, 822, "Dev results flatter Sybil (Sybil's developers selected the model on this split). Sources: results/x9 (dev, test), results/x7/x7_sensitivity_test.json P5; RESULTS_L2.md 3e-3g.", 9, MUTED)
    s.save(out / "fig6_clinical.svg")


def box(s, x, y, w, lines, edge=BASE, head=None, h=None):
    hh = h or 16 * len(lines) + 14; rect(s, x, y, w, hh, SURF, edge, 1.5, rx=6)
    for i, (t, size, col, wt) in enumerate(lines): s.text(x + 10, y + 20 + i * 16, t, size, col, weight=wt)
    return hh


def arrow(s, x1, y1, x2, y2):
    s.line(x1, y1, x2, y2, INK2, 1.5); s.el.append(f'<path d="M{x2:.1f},{y2:.1f} l-4,-8 l8,0 Z" fill="{INK2}"/>' if x1 == x2 else "")


def fig2(out):
    """study flow from committed counts: lung_l0/results/l0_results.json, results/s6/assemble_test.json, the dev assemble record (logged),
    results/manifest_unseen.csv tiers, results/manifest_lidc.csv (X5)."""
    L0 = json.loads((HERE.parent / "lung_l0" / "results" / "l0_results.json").read_text()); P = L0["participants"]; C = L0["counts_all_screens"]
    AT = json.loads((HERE / "results" / "s6" / "assemble_test.json").read_text())
    import csv
    U = list(csv.DictReader(open(HERE / "results" / "manifest_unseen.csv", encoding="utf-8")))
    u1 = [r_ for r_ in U if r_["tier"] == "U1"]; u2 = [r_ for r_ in U if r_["tier"] == "U2"]
    nl = sum(1 for _ in csv.DictReader(open(HERE / "results" / "manifest_lidc.csv", encoding="utf-8")))
    s = Svg(1060, 560); s.text(20, 28, "Figure 2. Study flow", 15, weight="bold")
    B, I, M = (INK, "bold"), (INK2, "normal"), (MUTED, "normal")
    box(s, 300, 50, 420, [(f"NLST, CT arm (public tables, IDC): {P['ct_arm_in_public_table']:,} participants", 12, *B),
                          ("CT images and DICOM headers from IDC; outcomes from the NLST tables", 10, *I)])
    arrow(s, 510, 98, 510, 128); s.line(130, 128, 930, 128, INK2, 1.5)
    cols = [(20, "Sybil's train split", [f"{P['by_group']['train']:,} participants, {C['train']['exams']:,} exams", "Sybil was trained here (by its developers)", "we fit only the radiologists' forms (F, P) here"], BASE),
            (280, "Sybil's dev split", [f"{P['by_group']['dev']:,} participants; 7,336 series scored", "Sybil's model selection split: in-sample", "our discovery work; X11 (mechanism, no outcome)"], BASE),
            (540, "Sybil's test split (held out)", [f"{P['by_group']['test']:,} participants; {AT['n_main']:,} series scored", f"+ {AT['n_zfix']} z-fix runs, {AT['n_pair']} kernel pairs", f"1-year outcome: {AT['outcomes']['y1']['pos'] + AT['outcomes']['y1']['neg']:,} exams, {AT['outcomes']['y1']['pos']} cancers",
                                                   "six pre-registered tests; exploratory X1-X10"], BLUE),
            (800, "Never used by Sybil (O2)", [f"{P['by_group']['unseen']:,} participants, {C['unseen']['exams']:,} exams", f"lists: U1 {len(u1):,} series, U2 {len(u2):,} series", "pre-registered; scoring from 1 Dec 2026", f"(cancer-poor: {C['unseen']['participants_with_later_cancer']} with a later cancer)"], ORANGE)]
    for x, title, lines, edge in cols:
        arrow(s, x + 120, 128, x + 120, 150)
        box(s, x, 150, 240, [(title, 11, *B)] + [(t, 10, *I) for t in lines], edge=edge)
    s.text(20, 290, "All NLST groups are the same trial (33 US centres, 2002-2004 enrolment): every NLST result is internal testing, including O2.", 10, INK2)
    box(s, 20, 320, 480, [("LIDC-IDRI (7 US academic centres; clinical CT, not screening)", 11, *B),
                          (f"{nl} scans with overlapping slices (one per patient; GE 134, Philips 46, Siemens 17)", 10, *I),
                          ("external replication of the mechanism only (no cancer outcome)", 10, *I)], edge=BLUE)
    box(s, 540, 320, 480, [("Imaging Data Commons, all chest CT (DICOM headers only)", 11, *B),
                           ("how common overlapping series are today (X12); no model run", 10, *I),
                           ("NLST collection licence CC BY 4.0; LIDC-IDRI CC BY 3.0", 10, *M)])
    s.text(20, 430, "Selection rules, exclusions at each step and the cut-offs are in the protocol (section 5), O2_PLAN.md and RESULTS_L2.md 3d, 3i.", 10, MUTED)
    s.text(20, 446, "Blue edge: confirmatory results (test) and the external mechanism replication; orange edge: pre-registered, not yet run.", 10, MUTED)
    s.save(out / "fig2_flow.svg")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--ct-dir"); a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    fig2(out); fig5(out); fig6(out)
    if a.ct_dir: fig1(Path(a.ct_dir), Path(a.ct_dir))                          # Figure 1 holds CT pixels: written next to the PNGs, outside git
    print("figures written")


if __name__ == "__main__":
    main()
