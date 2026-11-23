"""Lung L2, task 5: paper figures from committed result files only (no new analysis; plan docs/FIGURE_PLAN.md). Plain SVG with the helpers and
the validated two-slot palette of s6_figures.py (blue #2a78d6, orange #eb6834; ink and grey from the reference palette).
  fig1_mechanism.svg   (a) schematic of overlapping slices placed at the slice thickness; (b) one public NLST dev exam, coronal, as Sybil sees
                       it and at the true spacing (PNG from fig1_coronal.py, embedded; written OUTSIDE git because it holds CT pixels)
  fig2_flow.svg        study flow from committed counts
  fig3_hypotheses.svg  the six pre-registered hypotheses (test, dev) and the LIDC-IDRI replication
  fig4_mechanism_inside.svg  (a) test: the z-fix change and the follow-up jump with and without shared axis 0 (results/figures/fig4a_intervals_test.json,
                       results/s6); (b, c) X11 (dev, exploratory; results/x11/x11_analysis_dev.json): arm B stretch dose, arm A padding variants
  figS1_padding_curve.svg  supplement: axis 0 against the padded slices of all dev main runs (results/x11/x11_padcurve_fine_dev.json, post hoc bins)
  fig5_exposure.svg    how often a chest CT study holds an overlapping series (results/x12), in non-overlapping parts
  fig6_clinical.svg    operating points and threshold transfer on NLST test (results/x9, results/x7, results/s4/s4_u3_dev.json)
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
    """blue = Sybil's reading (SliceThickness), orange = the true spacing (ImagePositionPatient), in both panels. Panel (b) is drawn at TRUE
    physical proportions: Sybil resizes every slice to 256 columns, so one column = resampled pixel x DICOM columns / 256 (1.41 mm here, not the
    0.70 mm in Sybil's volume header; Neon's review), one row = 2.5 mm (Sybil's z voxel; true for the z-fix, 1.25 mm of anatomy for main)."""
    info = json.loads((ct_dir / "fig1_coronal.json").read_text()); s = Svg(1130, 660)
    s.text(20, 28, "Figure 1. Sybil places overlapping slices at the slice thickness, so the chest is stretched along the body axis", 15, weight="bold")
    # (a) schematic: orange = true positions, blue = Sybil
    s.text(20, 62, "a", 14, weight="bold"); s.text(40, 62, "Slices 2.5 mm thick, reconstructed every 1.25 mm (50% overlap)", 12, INK2)
    x0, y0, mm = 60, 92, 9.0                                                   # 9 px per mm
    for xc, step, lab, col in ((x0, 1.25, "True positions (ImagePositionPatient)", ORANGE), (x0 + 200, 2.5, "Where Sybil places them (SliceThickness)", BLUE)):
        s.text(xc - 20, y0 - 10, lab, 11, INK2)
        for k in range(8): rect(s, xc + (k % 2) * 14, y0 + k * step * mm, 110, 2.5 * mm, col, op=0.25, stroke=col, sw=1)
        c0, c1 = y0 + 1.25 * mm, y0 + (7 * step + 1.25) * mm                  # first and last slice centres
        s.line(xc - 10, c0, xc - 10, c1, col, 2); s.text(xc - 14, c1 + 18, f"centre to centre: {7 * step:g} mm", 11, INK)
    s.text(x0 - 20, 322, "The slice step doubles (1.25 -> 2.5 mm), so the anatomy is", 11, INK); s.text(x0 - 20, 338, "stretched 2-fold along the body axis for this protocol.", 11, INK)
    # (b) true physical proportions
    vs = info["sybil_voxel_spacing_after_resample_mm"]; colmm = vs[0] * info["dicom_columns"] / 256; W = 230.0; H = W * (200 * vs[2]) / (256 * colmm)
    s.text(450, 62, "b", 14, weight="bold")
    s.text(470, 62, f"One NLST exam, coronal, Sybil's 200-slice input box ({200 * vs[2]:.0f} mm), drawn at true proportions", 12, INK2)
    yb, flip = 96, info["positions_increase_with_index"]                       # volume index 0 = feet -> flip so the head is up
    ry = lambda r_: (yb + H - (r_ + 0.5) * H / 200) if flip else (yb + (r_ + 0.5) * H / 200)   # noqa: E731
    panels = [(470, "fig1_coronal_main.png", "As Sybil reads it", BLUE, None, info["lung_rows_main"]), (770, "fig1_coronal_zfix.png", "At the true spacing (z-fix)", ORANGE, info["padded_rows_zfix"], info["lung_rows_zfix"])]
    for x, png, title, col, pad, lung in panels:
        b64 = base64.b64encode((ct_dir / png).read_bytes()).decode("ascii")
        tr = f' transform="translate(0,{2 * yb + H:.1f}) scale(1,-1)"' if flip else ""
        s.el.append(f'<image x="{x}" y="{yb}" width="{W:.1f}" height="{H:.1f}" preserveAspectRatio="none" href="data:image/png;base64,{b64}"{tr}/>')
        rect(s, x, yb, W, H, "none", col, 2); s.text(x, yb + H + 20, title, 12, INK, weight="bold")
        if lung: s.line(x - 8, ry(lung[0]), x + W + 8, ry(lung[0]), col, 1.5); s.text(x - 10, ry(lung[0]) + 4, "lung base", 9, INK2, "end")
        if pad:
            rows = sorted(pad); bands, start = [], rows[0]
            for a_, b_ in zip(rows, rows[1:] + [None]):
                if b_ != a_ + 1: bands.append((start, a_)); start = b_
            for r0, r1 in bands:
                ya, yb2 = min(ry(r0), ry(r1)) - H / 400, max(ry(r0), ry(r1)) + H / 400
                s.line(x + W + 8, ya, x + W + 8, yb2, ORANGE, 4); s.text(x + W + 14, (ya + yb2) / 2 + 4, f"{r1 - r0 + 1} padded", 10, INK2)
    tm, tz, nl = info["T_resampled_main"], info["T_resampled_zfix"], info["lung_rows_zfix"]
    s.text(470, yb + H + 36, f"Chest spread over {tm} slices = {tm * vs[2]:.0f} mm as Sybil", 11, INK2)
    s.text(470, yb + H + 51, f"reads it; the box holds {200 * vs[2]:.0f} mm, so {tm - 200} slices", 11, INK2); s.text(470, yb + H + 66, "are cut off (here the lung apex).", 11, INK2)
    s.text(770, yb + H + 36, f"Chest = {tz} slices = {tz * vs[2]:.0f} mm; lungs about {(nl[1] - nl[0] + 1) * vs[2]:.0f} mm;", 11, INK2)
    s.text(770, yb + H + 51, f"{len(info['padded_rows_zfix'])} slices of Sybil's mid-grey padding.", 11, INK2)
    # L-shaped 100 mm x 100 mm scale bar
    sx, sy = 1110, yb + H; s.line(sx, sy, sx - 100 / colmm * W / 256, sy, INK, 2); s.line(sx, sy, sx, sy - 100 / vs[2] * H / 200, INK, 2); s.text(sx - 4, sy - 100 / vs[2] * H / 200 - 6, "100 mm", 10, INK, "end")
    s.text(470, yb + H + 92, f"DICOM: SliceThickness {info['thickness_mm']:g} mm  ·  spacing of ImagePositionPatient {info['true_spacing_mm']:g} mm  ·  ratio {info['ratio']:.2f}  ·  "
                             f"{info['maker']} {info['model']}  ·  {info['n_images']} images", 10, INK)
    for i, t in enumerate(("Cropping is typical (627 of 759 stretched test exams), but the score drop is as large without it (-0.42 uncropped vs -0.36 cropped);",
                           "GE, Philips and Siemens show the same distortion (supplement). The exam is the first of the dev list, chosen without reading any outcome or model output.",
                           "Public NLST series (Imaging Data Commons, CC BY 4.0); coronal plane through the posterior lungs, Sybil's own intensity scale; no model output is shown.")):
        s.text(20, 610 + i * 14, t, 9.5, MUTED)
    s.save(out / "fig1_mechanism.svg")


def ci(s, x1, y1, x2, y2, col, w=1.0, op=0.65):
    s.el.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col}" stroke-width="{w}" stroke-opacity="{op}"/>')


NAMES = {"lidc_idri": "LIDC-IDRI", "cptac_lscc": "CPTAC-LSCC", "cptac_luad": "CPTAC-LUAD", "covid_19_ny_sbu": "COVID-19-NY-SBU", "cmb_lca": "CMB-LCA"}


def fig5(out):
    """exposure in non-overlapping parts (Neon's assessments): strong overlap without a contiguous alternative, strong overlap with a contiguous
    series in the same study (the series choice decides), moderate overlap only (0.65-0.85; hatched; not in the pre-registered tests); interval of
    the strong total; per-collection series shares on the SAME 0-40% axis (stacked dots)."""
    import csv
    d = json.loads((HERE / "results" / "x12" / "x12_overlap_prevalence.json").read_text())["sets"]
    rows = [("NLST (2002-2004 scanners)", "nlst"), ("Modern scanner models (2013 or later)", "modern_scanner_models"), ("Public chest CT collections (2015 or later)", "modern_collections_2015_on")]
    s = Svg(960, 640); s.text(20, 28, "Figure 5. How often a chest CT study holds an overlapping series (public data, DICOM headers only)", 15, weight="bold")
    s.el.append(f'<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="{SURF}"/>'
                f'<line x1="0" y1="0" x2="0" y2="6" stroke="{MUTED}" stroke-width="2"/></pattern></defs>')
    px, pw, xmax, top, rh = 330, 520, 0.40, 76, 74
    X = lambda v: px + v / xmax * pw   # noqa: E731
    for tt in ticks(0, xmax, 4):
        s.line(X(tt), top - 14, X(tt), top + 3 * rh - 10, GRID); s.text(X(tt), top + 3 * rh + 4, f"{tt * 100:.0f}%", 10, MUTED, "middle")
    s.text(px, top + 3 * rh + 20, "share of studies", 10, MUTED)
    for ri, (lab, key) in enumerate(rows):
        v = d[key]; y = top + ri * rh; h = 22
        s.text(20, y + 14, lab, 11, INK); s.text(20, y + 29, f"{v['studies']:,} studies, {v['patients']:,} people", 10, MUTED)
        strong, both, mod = v["studies_any_le_0p65"]["share"], v["studies_both_le_0p65_and_contiguous"]["share"], v["studies_any_le_0p85"]["share"] - v["studies_any_le_0p65"]["share"]
        x = px
        for w, fill, stroke in ((strong - both, BLUE, SURF), (both, "#86b6ef", SURF), (mod, "url(#hatch)", MUTED)):
            ww = w / xmax * pw
            if ww > 0: rect(s, x, y, ww, h, fill, stroke, 1)
            x += ww
        lo, hi = v["studies_any_le_0p65"]["lo"], v["studies_any_le_0p65"]["hi"]; yi = y + h + 7
        s.line(X(lo), yi, X(hi), yi, INK, 1.5); s.line(X(lo), yi - 3, X(lo), yi + 3, INK, 1.5); s.line(X(hi), yi - 3, X(hi), yi + 3, INK, 1.5)
        s.text(X(strong) + 4, y - 5, f"strong {strong * 100:.1f}% ({(strong - both) * 100:.1f}% + {both * 100:.1f}%)", 10, INK2)
        s.text(X(strong + mod) + 6, y + 15, f"+ moderate only {mod * 100:.1f}%", 10, MUTED)
    ly = top + 3 * rh + 42
    for i_, (lab, fill, stroke) in enumerate((("strong overlap (spacing / thickness <= 0.65), no contiguous series in the study", BLUE, None),
                                              ("strong overlap, a contiguous series also present (which series is sent to Sybil decides)", "#86b6ef", None),
                                              ("moderate overlap only (0.65 to 0.85): not part of the pre-registered tests (exploratory check only)", "url(#hatch)", MUTED))):
        rect(s, 20, ly + i_ * 18 - 9, 14, 10, fill, stroke or "none", 1 if stroke else 0); s.text(40, ly + i_ * 18, lab, 10, INK2)
    s.text(660, ly, "black line: 95% interval of the strong total", 10, MUTED)
    # per-collection strip on the same axis, stacked dots
    cols = [r_ for r_ in csv.DictReader(open(HERE / "results" / "x12" / "x12_per_collection.csv", encoding="utf-8")) if int(r_["patients"]) >= 20 and r_["collection_id"] != "nlst"]
    sy = ly + 150; s.text(20, sy - 96, f"Each public chest CT collection with 20 or more people ({len(cols)}; NLST excluded): share of its series with strong overlap (all acquisition years)", 10, INK2)
    s.line(px, sy + 4, px + pw, sy + 4, BASE, 1)
    for tt in ticks(0, xmax, 4): s.text(X(tt), sy + 20, f"{tt * 100:.0f}%", 10, MUTED, "middle")
    stack = {}
    for r_ in sorted(cols, key=lambda q: float(q["le_0p65"])):
        v = float(r_["le_0p65"]); b = round(v / 0.005); n = stack.get(b, 0); stack[b] = n + 1
        s.dot(X(min(v, xmax)), sy - 2 - n * 5.5, BLUE, 2.8)
    n0 = sum(1 for r_ in cols if float(r_["le_0p65"]) == 0); s.text(X(0) - 6, sy - 2, f"{n0} at 0%", 9, INK2, "end")
    for j_, r_ in enumerate(sorted(cols, key=lambda q: -float(q["le_0p65"]))[:3]):
        v = float(r_["le_0p65"]); yl = sy - 14 - j_ * 13; s.line(X(v), sy - 6, X(v), yl + 3, BASE, 1)
        s.text(X(v) + 3, yl, f"{NAMES.get(r_['collection_id'], r_['collection_id'])} {v * 100:.0f}%", 9, INK2)
    s.text(20, 620, "Header-only audit of Imaging Data Commons (mostly diagnostic and oncology CT, not screening). Top: study-level shares; strip: series-level shares.", 9, MUTED)
    s.text(20, 633, "Intervals by bootstrap over patients do not capture clustering by site; collections differ widely (strip). Filters and set definitions: Methods and supplement.", 9, MUTED)
    s.save(out / "fig5_exposure.svg")


def mark(s, shape, x, y, fill, r=5, hollow=False):
    f, st = (SURF, fill) if hollow else (fill, SURF)
    if shape == "circle": s.el.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{f}" stroke="{st}" stroke-width="{2 if hollow else 1.5}"/>')
    elif shape == "square": s.el.append(f'<rect x="{x - r:.1f}" y="{y - r:.1f}" width="{2 * r}" height="{2 * r}" fill="{f}" stroke="{st}" stroke-width="{2 if hollow else 1.5}"/>')
    elif shape == "diamond": s.el.append(f'<path d="M{x:.1f},{y - r - 1:.1f} L{x + r + 1:.1f},{y:.1f} L{x:.1f},{y + r + 1:.1f} L{x - r - 1:.1f},{y:.1f} Z" fill="{f}" stroke="{st}" stroke-width="{2 if hollow else 1.5}"/>')
    else: s.el.append(f'<path d="M{x:.1f},{y - r - 1:.1f} L{x + r + 1:.1f},{y + r:.1f} L{x - r - 1:.1f},{y + r:.1f} Z" fill="{f}" stroke="{st}" stroke-width="{2 if hollow else 1.5}"/>')


SCORES = [("sybil", "Sybil", BLUE, "circle"), ("form", "Form (radiologists' findings + age, sex, smoking; fitted on NLST train)", ORANGE, "square"),
          ("brock", "Brock (published; no family history in the public data)", MUTED, "triangle"), ("rule", "Fixed rule: Lung-RADS >= 4A (L4), >= 3 (L3), radiologists' call (R)", INK, "diamond")]
SHORT = {"sybil": "Sybil", "form": "Form", "brock": "Brock"}
RULE = {"L4": "lung_rads_4A", "L3": "lung_rads_3", "R": "radiologists_call"}
RULE_NAME = {"L4": "Lung-RADS >= 4A", "L3": "Lung-RADS >= 3", "R": "call"}


def fig6(out):
    """clinical context (exploratory, all NLST test exams): operating points at dev-matched false-alarm levels (broken x axis so L4 and L3 do not
    collide), 1 year all screens and 6 years baseline, with cancers caught at every level; threshold transfer dev -> test with the dev false
    alarms of the dev-cancer cuts (results/s4/s4_u3_dev.json). Caption facts from the same files (step offsets, 1-year baseline summary)."""
    X9 = {sp: json.loads((HERE / "results" / "x9" / f"x9_rules_thresholds_{sp}.json").read_text())["thresholds"] for sp in ("dev", "test")}
    P5 = json.loads((HERE / "results" / "x7" / "x7_sensitivity_test.json").read_text())["P5_harm_at_dev_cuts"]
    U3 = json.loads((HERE / "results" / "s4" / "s4_u3_dev.json").read_text())["table"]
    s = Svg(1060, 880); s.text(20, 28, "Figure 6. Clinical context on the NLST test split (exploratory): the same false-alarm levels, and cuts set on development data", 14, weight="bold")

    def get(T, key): return T["table"][key]

    def key_of(k, lvl): return RULE[lvl] if k == "rule" else f"{k}@OP_{lvl}"
    for pi, (E, lab, ylo, yhi) in enumerate((("E1", "1 year, all screens", 0.6, 1.0), ("E4", "6 years, baseline screens", 0.2, 0.9))):
        T = X9["test"][E]; c = T["counts"]; px, py, pw, ph = 90 + pi * 510, 96, 400, 290
        if pi == 0: s.text(20, py - 36, "a", 14, weight="bold")
        s.text(px, py - 36, f"{lab}: {c['exams']:,} exams, {c['cancers']} cancers ({c['prevalence'] * 100:.1f}%)", 12, INK)

        def X(v):   # broken axis: 0-175 | 310-420 (the gap is compressed)
            if v <= 175: return px + v / 175 * 0.58 * pw
            if v < 310: return px + (0.58 + (v - 175) / 135 * 0.06) * pw
            return px + (0.64 + (min(v, 420) - 310) / 110 * 0.36) * pw
        Y = lambda v: py + ph - (min(max(v, ylo), yhi) - ylo) / (yhi - ylo) * ph   # noqa: E731
        for tt in (0, 50, 100, 150, 325, 350, 375, 400): s.line(X(tt), py, X(tt), py + ph, GRID); s.text(X(tt), py + ph + 14, str(tt), 10, MUTED, "middle")
        gx = X(242); s.line(gx - 6, py + ph + 4, gx - 2, py + ph - 4, INK2, 1.5); s.line(gx + 2, py + ph + 4, gx + 6, py + ph - 4, INK2, 1.5)
        for tt in ticks(ylo, yhi, 4): s.line(px, Y(tt), px + pw, Y(tt), GRID); s.text(px - 6, Y(tt) + 4, f"{tt * 100:.0f}%", 10, MUTED, "end")
        s.text(px + pw / 2, py + ph + 30, "false alarms per 1,000 exams (axis broken between 175 and 310)", 10, INK2, "middle"); s.text(px - 58, py - 12, "sensitivity", 10, INK2)
        for lvl in ("L4", "L3", "R"):
            xs = []
            for key, name, col, shp in SCORES:
                r_ = get(T, key_of(key, lvl)); se, fa = r_["sensitivity"], r_["fa_per_1000_exams"]
                ci(s, X(fa["lo"]), Y(se["est"]), X(fa["hi"]), Y(se["est"]), col); ci(s, X(fa["est"]), Y(se["lo"]), X(fa["est"]), Y(se["hi"]), col)
                mark(s, shp, X(fa["est"]), Y(se["est"]), col); xs.append(fa["est"])
            s.text(X(sum(xs) / len(xs)), py - 10, lvl, 11, INK2, "middle", "bold")
        for li, lvl in enumerate(("L4", "L3", "R")):
            parts = [f"{SHORT[k]} {get(T, key_of(k, lvl))['counts']['tp']}" for k in ("sybil", "form", "brock")] + [f"{RULE_NAME[lvl]} {get(T, RULE[lvl])['counts']['tp']}"]
            s.text(px, py + ph + 50 + li * 14, f"{lvl}, cancers caught of {c['cancers']}: " + ", ".join(parts), 10, INK2)
    for i_, (key, name, col, shp) in enumerate(SCORES): mark(s, shp, 40 + (i_ % 2) * 510, 508 + (i_ // 2) * 18, col); s.text(52 + (i_ % 2) * 510, 512 + (i_ // 2) * 18, name, 10, INK2)

    def step(E):   # Sybil's achieved dev false-alarm share at R vs the target (its score has steps)
        r_ = get(X9["dev"][E], "sybil@OP_R")["counts"]; return 100 * r_["fp"] / (r_["fp"] + r_["tn"]), 100 * X9["dev"][E]["operating_points"]["OP_R"]["dev_false_alarm_share"]
    (a1, t1), (a4, t4) = step("E1"), step("E4"); E2 = X9["test"]["E2"]; c2 = E2["counts"]["cancers"]
    tp2 = lambda k: get(E2, k)["counts"]["tp"]; fa2 = lambda k: get(E2, k)["fa_per_1000_exams"]["est"]   # noqa: E731
    notes = ["Levels: cuts set on cancer-free DEV exams to the dev false-alarm share of Lung-RADS >= 4A (L4), >= 3 (L3) and the radiologists' call (R). Lines: 95% participant-bootstrap intervals.",
             f"Sybil's score has steps: at R its dev false-alarm share was {a1:.1f}% (target {t1:.1f}%) at 1 year and {a4:.1f}% (target {t4:.1f}%) at 6 years, part of its lower false alarms there.",
             "1 year: the form and the fixed rules use the radiologists' reads, which also triggered the work-up (not blind to the outcome). 6 years at baseline avoids the prior-scan advantage and",
             "reduces 1-year work-up bias, but Lung-RADS and Brock score nodules only: 55 of the 131 six-year cancers (7 of 86 one-year) had no nodule >= 4 mm on the scan.",
             "Lung-RADS and Brock were reconstructed from the NLST forms (part-solid size assumed; Brock without family history).",
             f"1 year, baseline screens only ({c2} cancers): at L3 Sybil {tp2('sybil@OP_L3')}, form {tp2('form@OP_L3')}, Lung-RADS >= 3 {tp2('lung_rads_3')}; at R Sybil {tp2('sybil@OP_R')} "
             f"({fa2('sybil@OP_R'):.0f} false alarms per 1,000), form {tp2('form@OP_R')} ({fa2('form@OP_R'):.0f}), call {tp2('radiologists_call')} ({fa2('radiologists_call'):.0f})."]
    for i_, n_ in enumerate(notes): s.text(20, 556 + i_ * 13, n_, 9, MUTED)
    # (b) threshold transfer, 1 year all screens
    s.text(20, 660, "b", 14, weight="bold"); s.text(40, 660, "Threshold transfer, 1 year, all screens: development (hollow) -> test (filled)", 12, INK)
    g1 = "cut set on cancer-free dev exams (L3): false alarms transfer; dev sensitivity was inflated for Sybil"
    g2 = "cut matched on dev CANCERS (to the radiologists' dev sensitivity): false alarms not matched; Sybil's sensitivity collapses"
    rows = []
    for key, nm, col, shp in (("sybil", "Sybil", BLUE, "circle"), ("form", "Form", ORANGE, "square"), ("rule", "Lung-RADS >= 3", INK, "diamond")):
        d_, t_ = get(X9["dev"]["E1"], key_of(key, "L3")), get(X9["test"]["E1"], key_of(key, "L3"))
        rows.append((g1, nm, col, shp, d_["sensitivity"]["est"], t_["sensitivity"]["est"], d_["fa_per_1000_exams"]["est"], t_["fa_per_1000_exams"]["est"], t_["counts"]["tp"]))
    for nm, col, shp, tk, uk in (("Sybil", BLUE, "circle", "sybil", "sybil"), ("Form", ORANGE, "square", "C1_form", "form_F")):
        r_ = P5["rad"]["table"][tk]; rows.append((g2, nm, col, shp, U3[uk]["sensitivity"], r_["sensitivity"], U3[uk]["fa_per_1000"], r_["fa_per_1000_exams"], r_["cancers_caught"]))
    rows.append((g2, "Radiologists' call", INK, "diamond", U3["radiologists"]["sensitivity"], P5["radiologists_test_sensitivity"], U3["radiologists"]["fa_per_1000"], P5["radiologists_fa_per_1000_exams"],
                 round(P5["radiologists_test_sensitivity"] * 86)))
    bx, bw, by = 330, 300, 676; Xb = lambda v: bx + (v - 0.5) / 0.5 * bw   # noqa: E731
    ys, grp, y = [], None, by
    for g, *_ in rows:
        if g != grp: y += 18; grp = g
        ys.append(y); y += 19
    bottom = ys[-1] + 10
    for tt in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0): s.line(Xb(tt), by + 8, Xb(tt), bottom, GRID); s.text(Xb(tt), bottom + 13, f"{tt * 100:.0f}%", 10, MUTED, "middle")
    s.text(bx + bw / 2, bottom + 26, "sensitivity", 10, INK2, "middle"); s.text(bx + bw + 24, by + 10, "false alarms per 1,000, dev -> test; cancers caught on test", 10, INK2)
    grp = None
    for i_, (g, nm, col, shp, sd, st, fd, ft, tp) in enumerate(rows):
        y = ys[i_]
        if g != grp: s.text(20, y - 15, g, 10, INK2, weight="bold"); grp = g
        s.text(200, y + 4, nm, 10, INK); s.line(Xb(sd), y, Xb(st), y, col, 2); mark(s, shp, Xb(sd), y, col, 5, hollow=True); mark(s, shp, Xb(st), y, col, 5)
        s.text(bx + bw + 24, y + 4, f"{fd:.0f} -> {ft:.0f};  sensitivity {sd * 100:.0f}% -> {st * 100:.0f}%  ({tp}/86)", 10, INK2)
    s.text(20, 872, "Dev results flatter Sybil: Sybil's developers selected the model on this split, so its dev sensitivity is optimistic and a cut tuned to dev cancers sits too high on new data.", 9, MUTED)
    s.save(out / "fig6_clinical.svg")


def fig3(out):
    """the six pre-registered hypotheses (test = confirmatory, blue; dev = discovery, grey) with the exploratory external LIDC-IDRI replication
    (orange) on H1, H2, H6; H3 drawn as not confirmed; H7 tagged partly seen. Sources: results/s6/s6_test.json, results/s5/s6_dev_as_if_test.json,
    results/x5/x5_lidc.json."""
    from s6_figures import fmt
    T = {h["id"]: h for h in json.loads((HERE / "results" / "s6" / "s6_test.json").read_text())["hypotheses"]}
    D = {h["id"]: h for h in json.loads((HERE / "results" / "s5" / "s6_dev_as_if_test.json").read_text())["hypotheses"]}
    L = {h["id"]: h for h in json.loads((HERE / "results" / "x5" / "x5_lidc.json").read_text())["replication"]["hypotheses"]}
    S6 = json.loads((HERE / "results" / "s6" / "s6_test.json").read_text()); zf, kf = S6["secondary_new_freeze"]["zfix_flags"], S6["secondary_new_freeze"]["kernel_flags"]
    TH = json.loads((HERE / "results" / "s5" / "frozen_thresholds_L2.json").read_text())["thresholds"]
    # titles state each frozen hypothesis and its direction (HYPOTHESES_L2.md; "rarely" for H4 was removed at the S5 review as too strong)
    names = dict(H1=("H1  the z-fix moves the score", "share of exams whose 6-year logit moves", ">= 1/4 dev SD (test: > 30%)"),
                 H2=("H2  the z-fix lowers the score", "mean change of the 1-year logit,", "z-fix minus as read (test: < -0.10)"),
                 H3=("H3  the z-fix changes the alarm", "share of exams whose alarm changes", "(test: > 5%)"),
                 H4=("H4  a kernel change alters the alarm in < 5%", "share of sharp/soft kernel pairs whose", "alarm differs (test: < 5%)"),
                 H6=("H6  shared axis 0 carries the drop", "1-year logit change removed by switching", "axis 0 off (test: > 0.20)"),
                 H7=("H7  jump at a stretch change (partly seen)", "b: 1-year logit change per change of stretch,", "consecutive yearly screens, form-adjusted (test: > 0.10)"))
    pct = {"H1", "H3", "H4"}
    def lab_v(hid, v): return (f"{100 * v:.1f}%" if hid in pct else f"{v:+.3f}" if hid != "H6" else f"{v:.3f}")   # noqa: E306
    def tick_v(hid, v): return (f"{100 * v:.0f}%" if hid in pct else fmt(v))   # noqa: E306
    s = Svg(1000, 632); s.text(20, 28, "Figure 3. The six pre-registered hypotheses (Holm over six, one-sided) and the external replication on LIDC-IDRI", 15, weight="bold")
    s.dot(30, 52, BLUE); s.text(40, 56, "NLST test (confirmatory)", 11, INK2)
    mark(s, "circle", 230, 52, MUTED, r=3.5, hollow=True); s.text(240, 56, "NLST dev (discovery; Sybil's model selection split)", 11, INK2)
    mark(s, "diamond", 560, 52, ORANGE, r=4); s.text(570, 56, "LIDC-IDRI, 7 centres, clinical CT (exploratory replication)", 11, INK2)
    for k, hid in enumerate(("H1", "H2", "H3", "H4", "H6", "H7")):
        t, d = T[hid], D[hid]; x0, y0, w = 20 + (k % 3) * 325, 90 + (k // 3) * 250, 305
        rows = [("test", t["est"], *t["ci95"], BLUE, "test"), ("dev", d["est"], *d["ci95"], MUTED, "dev")] + ([("LIDC-IDRI", L[hid]["est"], *L[hid]["ci95"], ORANGE, "lidc")] if hid in L else [])
        ok = t["confirmed_holm"]
        if not ok:
            s.el.append(f'<rect x="{x0 - 8}" y="{y0 - 18}" width="{w + 6}" height="232" fill="none" stroke="{INK2}" stroke-width="1.5" stroke-dasharray="5,4" rx="6"/>')
        s.text(x0, y0, names[hid][0], 12, INK if ok else INK2, weight="bold"); s.text(x0, y0 + 15, names[hid][1], 9.5, INK2); s.text(x0, y0 + 28, names[hid][2], 9.5, INK2)
        vals = [v for r_ in rows for v in r_[1:4]] + [t["null"]]; a, b = min(vals), max(vals); pad = (b - a) * 0.15 or 0.1; a, b = a - pad, b + pad
        lx, rx = x0 + 62, x0 + 188; Xh = lambda v: lx + (v - a) / (b - a) * (rx - lx)   # noqa: E731
        top = y0 + 50; rh = 26; bot = top + rh * len(rows) + 6
        for tt in ticks(a, b, 3): s.line(Xh(tt), top, Xh(tt), bot, GRID); s.text(Xh(tt), bot + 14, tick_v(hid, tt), 9.5, MUTED, "middle")
        s.line(Xh(t["null"]), top - 4, Xh(t["null"]), bot, INK2, 1.5); s.text(Xh(t["null"]), top - 7, f"null {tick_v(hid, t['null'])}", 9.5, INK2, "middle")
        for i_, (lab, est, cl, ch, col, kind) in enumerate(rows):
            y = top + rh * i_ + rh / 2 + 2
            if kind == "lidc": s.el.append(f'<line x1="{x0}" y1="{y - rh / 2:.1f}" x2="{x0 + w - 4}" y2="{y - rh / 2:.1f}" stroke="{GRID}" stroke-width="1" stroke-dasharray="3,3"/>')
            s.text(x0, y + 4, lab, 10.5 if kind != "dev" else 10, INK2 if kind != "dev" else MUTED)
            if kind == "test": s.line(Xh(cl), y, Xh(ch), y, col, 2); s.dot(Xh(est), y, col)
            elif kind == "dev": s.line(Xh(cl), y, Xh(ch), y, col, 1.2); mark(s, "circle", Xh(est), y, col, r=3.5, hollow=True)
            else: s.line(Xh(cl), y, Xh(ch), y, col, 2); mark(s, "diamond", Xh(est), y, col, r=4)
            s.text(x0 + 196, y + 4, f"{lab_v(hid, est)} [{lab_v(hid, cl)}, {lab_v(hid, ch)}]", 9, INK2 if kind != "dev" else MUTED)
        pv = t["p_one_sided"]; ptxt = "p < 0.001" if pv < 1e-3 else (f"p = {pv:.4f}" if pv < 0.01 else f"p = {pv:.2f}")
        res = (f"NLST test: confirmed (Holm), one-sided {ptxt}" if ok else f"NLST test: NOT CONFIRMED (one-sided p = {pv:.2f})")
        s.text(x0, bot + 32, res, 10, INK if ok else INK2, weight="bold" if not ok else "normal")
        if hid in L:
            lp = L[hid]["p_one_sided"]; s.text(x0, bot + 46, "LIDC-IDRI (exploratory): one-sided " + ("p < 0.001" if lp < 1e-3 else f"p = {lp:.3f}"), 9.5, INK2)
        if hid == "H3": s.text(x0, bot + 46, f"alarms lost {zf['lost']}, gained {zf['gained']} of {T['H3']['counts']['exams']} exams: the z-fix loses more than it adds", 9, MUTED)
        if hid == "H4": s.text(x0, bot + 46, f"test and dev both had {kf['changed']} of {T['H4']['counts']['pairs']} pairs with a changed alarm", 9, MUTED)
        if hid == "H7": s.text(x0, bot + 46, f"partly seen before the freeze; 121 of the {T['H7']['counts']['changed']} changed pairs involve GE", 9, MUTED)
    tc, dc = T["H7"]["counts"], D["H7"]["counts"]
    foot = [f"Counts, test (dev): z-fix exams {T['H1']['counts']['exams']} ({D['H1']['counts']['exams']}), participants {T['H1']['counts']['participants']} ({D['H1']['counts']['participants']}) for H1-H3 and H6; "
            f"kernel pairs {T['H4']['counts']['pairs']} ({D['H4']['counts']['pairs']}) for H4; consecutive yearly pairs {tc['pairs']:,} ({dc['pairs']:,}), changed {tc['changed']} ({dc['changed']}) for H7.",
            "z-fix: the same images given to Sybil at their true slice spacing (from the slice positions) instead of at the slice thickness. Alarm: Sybil's 1-year risk at or above",
            f"the frozen dev cut tau90 = {TH['tau90_s1']:.3f}. Axis 0: one direction shared by Sybil's five members in its pooled layer (frozen name \"z-geometry\"; an exploratory dev experiment",
            "with no outcome read showed that it reads whether a thick slab of Sybil's own padding is in its 200-slice box; Figure 4). H5 and H5' were moved to the secondary list before the test split was opened.",
            f"LIDC-IDRI: 197 scans with strongly overlapping slices (one per patient; GE 134, Philips 46, Siemens 17), no cancer outcome, the frozen NLST dev SD ({TH['sd_ref_lbar6_all_dev_main']:.2f}) and axis 0, Holm over its",
            "three tests; a different population (clinical CT), so it is a marker of replication, not part of the confirmatory family. Intervals: 95% participant bootstrap."]
    for i_, t_ in enumerate(foot): s.text(20, 548 + 14 * i_, t_, 9, MUTED)
    s.save(out / "fig3_hypotheses.svg")


def fig4(out):
    """where the effect sits inside Sybil. (a) NLST test (pre-registered H2, H6, H7): mean change of Sybil's logit as Sybil gives it (blue,
    filled) and with shared axis 0 of `pooled` set to its dev mean in every member (grey, hollow), with 95% participant-bootstrap intervals.
    Sources: results/figures/fig4a_intervals_test.json (plan 23 Nov), results/s6/s6_test.json (H7, its axis-0-off b, axis-0 shifts).
    (b, c) X11 (dev, exploratory; results/x11/x11_analysis_dev.json; Neon's corrections of 23 Nov: matched z-fix values for the every-second-
    slice row, pad-matched logits not drawn as effects, the exam-level scatter shown; after Neon's check of the write-up: f = 2.5 on the axis-0
    plot only, A0 as triangles, controls grouped below the main rows, the padding curve moved to Supplementary Figure S1)."""
    from s6_figures import fmt
    A4 = json.loads((HERE / "results" / "figures" / "fig4a_intervals_test.json").read_text())
    S6 = json.loads((HERE / "results" / "s6" / "s6_test.json").read_text()); H7 = [h for h in S6["hypotheses"] if h["id"] == "H7"][0]
    F7 = S6["secondary_new_freeze"]["H7_followup"]; C1 = S6["secondary_new_freeze"]["C1_zfix_moves_axis0_dev_sd"]
    s = Svg(1060, 600); s.text(20, 28, "Figure 4. Where the slice-spacing effect sits inside Sybil: a signal from Sybil's own padding", 15, weight="bold")
    # ---- panel (a)
    s.text(20, 58, "a", 13, weight="bold"); s.text(36, 58, "NLST test, pre-registered (H2, H6, H7): mean change of Sybil's logit", 12, INK, weight="bold")
    s.text(36, 74, "as Sybil gives it, and with shared axis 0 switched off (set to its dev mean in all five members; nothing refitted)", 10, INK2)
    rows = [("z-fix, 1-year logit", f"{A4['counts']['exams']} stretched exams, {A4['counts']['participants']} people", A4["delta_lbar1_as_sybil"], A4["delta_lbar1_axis0_off"]),
            ("z-fix, 6-year logit", "same exams", A4["delta_lbar6_as_sybil"], A4["delta_lbar6_axis0_off"]),
            ("follow-up jump b, 1-year", f"{H7['counts']['pairs']:,} yearly pairs, {H7['counts']['changed']} changed stretch",
             dict(est=H7["est"], lo=H7["ci95"][0], hi=H7["ci95"][1]), F7["b_axis0_off"])]
    a, b = -0.5, 0.5; lx, rx = 250, 470; Xh = lambda v: lx + (v - a) / (b - a) * (rx - lx)   # noqa: E731
    top, gh = 100, 74; bot = top + gh * len(rows)
    for tt in (-0.4, -0.2, 0.0, 0.2, 0.4): s.line(Xh(tt), top - 6, Xh(tt), bot, GRID); s.text(Xh(tt), bot + 14, fmt(tt), 10, MUTED, "middle")
    s.line(Xh(0), top - 6, Xh(0), bot, INK2, 1.5); s.text(Xh(0), top - 10, "no change", 9.5, INK2, "middle")
    s.text((lx + rx) / 2, bot + 30, "mean change of the logit (z-fix minus as read; later minus earlier screen per stretch change)", 9.5, MUTED, "middle")
    for i, (lab, sub, on, off) in enumerate(rows):
        y0 = top + gh * i; s.text(20, y0 + 18, lab, 11, INK, weight="bold"); s.text(20, y0 + 32, sub, 9.5, MUTED)
        for j, (v, col, hollow, name) in enumerate(((on, BLUE, False, "as Sybil gives it"), (off, MUTED, True, "axis 0 off"))):
            y = y0 + 16 + j * 22; s.line(Xh(v["lo"]), y, Xh(v["hi"]), y, col, 2); mark(s, "circle", Xh(v["est"]), y, col, r=4.5, hollow=hollow)
            s.text(rx + 12, y + 4, f"{name}: {v['est']:+.3f} [{v['lo']:+.3f}, {v['hi']:+.3f}]", 9.5, INK2 if not hollow else MUTED)
    sh = A4["share_exams_abs_delta_lbar6_ge_quarter_sd"]; au = S6["secondary_new_freeze"]["H6_auroc_axis0_off"]["y1"]["diff_off_minus_plain"]
    notes = [f"Switching axis 0 off removes the mean shift, not the exam-by-exam scatter: z-fix exams whose 6-year logit moves >= 1/4 SD (as in H1):",
             f"{100 * sh['as_sybil']:.1f}% as Sybil gives it, {100 * sh['axis0_off']:.1f}% with axis 0 off. 1-year AUROC with axis 0 off minus as given: "
             f"{au['est']:+.4f} [{au['lo']:+.3f}, {au['hi']:+.3f}] (no change detected; secondary).",
             f"The z-fix moves axis 0 by {C1['est']:.2f} dev SD [{C1['lo']:.2f}, {C1['hi']:.2f}]; a change of stretch between yearly screens moves it by",
             f"{F7['axis0_jump_per_stretch_change_dev_sd']['est']:.2f} dev SD [{F7['axis0_jump_per_stretch_change_dev_sd']['lo']:.2f}, {F7['axis0_jump_per_stretch_change_dev_sd']['hi']:.2f}]. "
             f"H7 is partly seen before the freeze; {121} of its {H7['counts']['changed']} changed pairs involve GE."]
    for k, t in enumerate(notes): s.text(20, bot + 54 + 14 * k, t, 9.5, MUTED)
    # ---- panels (b, c): X11 (dev, exploratory)
    xf = HERE / "results" / "x11" / "x11_analysis_dev.json"
    if not xf.exists():
        for k, (lab, t) in enumerate((("b", "X11 arm B: synthetic stretch on non-overlapping dev scans (axis 0 and the logit against the stretch factor)"),
                                      ("c", "X11 arm A: the z-fix shift split into padding value, box filling, constant slab and every-second-slice decimation"))):
            y = 470 + k * 50; s.text(20, y, lab, 13, weight="bold"); s.text(36, y, t, 11, INK2); s.text(36, y + 16, "dev, exploratory; drawn when the X11 analysis is committed", 10, MUTED)
        s.save(out / "fig4_mechanism_inside.svg"); return
    X = json.loads(xf.read_text(encoding="utf-8")); EB, EA = X["estimates"]["B"], X["estimates"]["A"]; C = X["criteria"]
    # ---- panel (b): arm B, synthetic z-stretch of contiguous scans (pooled over 4 makers, 12 each)
    yb = 448; s.text(20, yb, "b", 13, weight="bold")
    s.text(36, yb, "Synthetic z-stretch of 48 contiguous dev scans, 12 per maker (exploratory; no outcome read)", 12, INK, weight="bold")
    s.text(36, yb + 16, "Stretch factor f = how much longer Sybil sees the scan (f = 1: the scan as it is; f = 2: what Sybil does to a 50%-overlapping scan read with the wrong spacing)", 10, INK2)
    P = lambda c, m: EB[c][m]["pooled"]   # noqa: E731
    zero = dict(est=0.0, lo=0.0, hi=0.0)
    seq = [(1.0, zero, zero, zero)] + [(f, P(c, "d_ax0"), P(c, "d_l1"), P(c, "A0")) for f, c in ((1.25, "f125"), (1.5, "f15"), (2.0, "f20"))]
    f25 = (2.5, P("f25", "d_ax0"), P("f25", "d_l1"), P("f25", "A0"))
    pm = (2.0, P("f20_padmatch", "d_ax0"), P("f20_padmatch", "d_l1"), P("f20_padmatch", "A0"))
    air = (1.0, P("main_air", "d_ax0"), P("main_air", "d_l1"), P("main_air", "A0"))
    b4 = C["B4"]["f25_minus_f20_axis0"]
    top, ph = yb + 50, 190
    for x0, w, idx, ylo, yhi, ytk, ttl, fmax in ((70, 400, 1, -0.4, 3.3, (0, 1, 2, 3), "change of shared axis 0 (dev SD)", 2.65),
                                                (600, 400, 2, -0.15, 0.65, (0, 0.2, 0.4, 0.6), "change of the 1-year logit", 2.2)):
        Xf = lambda f, x0=x0, w=w, fmax=fmax: x0 + (f - 0.85) / (fmax - 0.85) * w   # noqa: E731
        Yv = lambda v, ylo=ylo, yhi=yhi: top + ph - (v - ylo) / (yhi - ylo) * ph   # noqa: E731
        s.text(x0, top - 12, ttl, 10.5, INK, weight="bold")
        for t in ytk: s.line(x0, Yv(t), x0 + w, Yv(t), GRID); s.text(x0 - 6, Yv(t) + 3.5, fmt(t), 9.5, MUTED, "end")
        s.line(x0, Yv(0), x0 + w, Yv(0), INK2, 1.2)
        for f in ((1.0, 1.25, 1.5, 2.0, 2.5) if idx == 1 else (1.0, 1.25, 1.5, 2.0)): s.text(Xf(f), top + ph + 14, fmt(f), 9.5, MUTED, "middle")
        s.text(x0 + w / 2, top + ph + 28, "stretch factor f", 9.5, MUTED, "middle")
        series = [(idx, BLUE, 0.0, "circle")] + ([(3, MUTED, 0.03, "triangle")] if idx == 2 else [])
        for j, col, dx, shp in series:
            pts = [(Xf(r[0] + dx), Yv(r[j]["est"])) for r in seq]
            s.el.append('<polyline points="' + " ".join(f"{a:.1f},{b:.1f}" for a, b in pts) + f'" fill="none" stroke="{col}" stroke-width="1.6" stroke-opacity="0.8"/>')
            for r in seq + ([f25] if idx == 1 else []):
                v = r[j]; x = Xf(r[0] + dx); s.line(x, Yv(v["lo"]), x, Yv(v["hi"]), col, 2); mark(s, shp, x, Yv(v["est"]), col, r=4, hollow=r is f25)
        if idx == 1:
            s.text(Xf(2.5), Yv(f25[1]["hi"]) - 20, "f = 2.5: 20 scans;", 9, MUTED, "middle")
            s.text(Xf(2.5), Yv(f25[1]["hi"]) - 9, f"{b4['est']:+.2f} vs f = 2 on them", 9, MUTED, "middle")
            v = pm[1]; x = Xf(2.0) + 14; s.line(x, Yv(v["lo"]), x, Yv(v["hi"]), INK2, 2); mark(s, "square", x, Yv(v["est"]), INK2, r=4.5, hollow=True)
            mark(s, "diamond", x0 + 14, top + 2, ORANGE, r=4); s.text(x0 + 24, top + 6, "f = 1 with air instead of Sybil's padding", 9.5, INK2)
            mark(s, "square", x0 + 14, top + 18, INK2, r=4, hollow=True); s.text(x0 + 24, top + 22, "f = 2 at the same filling as the true scan", 9.5, INK2)
        else:
            mark(s, "circle", x0 + w - 200, top + 2, BLUE, r=4); s.text(x0 + w - 192, top + 6, "1-year logit", 9.5, INK2)
            mark(s, "triangle", x0 + w - 200, top + 18, MUTED, r=4); s.text(x0 + w - 192, top + 22, "A0: its axis-0 part", 9.5, INK2)
            mark(s, "diamond", x0 + w - 200, top + 34, ORANGE, r=4); s.text(x0 + w - 192, top + 38, "f = 1 with air (1-year logit)", 9.5, INK2)
        v = air[idx]; x = Xf(1.0); s.line(x, Yv(v["lo"]), x, Yv(v["hi"]), ORANGE, 2); mark(s, "diamond", x, Yv(v["est"]), ORANGE, r=4.5)
    phil = C["B2"]["by_maker"]["PHILIPS"]["lbar1"]; k3 = C["B3"]["kept_share_axis0"]
    nb = [f"Axis 0 rises with f and stops once Sybil's 200-slice box is full. Axis 0 and A0 rise in all four makers; the total 1-year logit at f = 2 does not in every maker "
          f"(Philips {phil['est']:+.2f} [{phil['lo']:+.2f}, {phil['hi']:+.2f}]).",
          f"Square: f = 2 cut back to the true scan's slice count and padded like it keeps {100 * k3['est']:.1f}% [{100 * k3['lo']:.1f}, {100 * k3['hi']:.1f}] of the axis-0 shift "
          f"(its logit is not read: the cut removes about half of the lung).",
          f"Diamond: no stretch, only air instead of Sybil's padding: axis 0 {air[1]['est']:+.2f} SD, 1-year logit {air[2]['est']:+.3f} [{air[2]['lo']:+.3f}, {air[2]['hi']:+.3f}]. "
          f"The stretch is a resampling of the images, not a real overlapping reconstruction."]
    for k, t in enumerate(nb): s.text(20, top + ph + 48 + 14 * k, t, 9.5, MUTED)
    # ---- panel (c): arm A, real overlapping scans: main comparisons, then controls (axis 0 only)
    yc = top + ph + 112; s.text(20, yc, "c", 13, weight="bold")
    s.text(36, yc, "Real overlapping dev scans: 63 scans (GE 24, Philips 27, Siemens 12; weighted to the dev maker mix; exploratory; no outcome read)", 12, INK, weight="bold")
    s.text(36, yc + 16, "Change within the same scans; each row names what is compared. \"Sybil's run\" = the scan as Sybil reads it (wrong spacing, Sybil's padding)", 10, INK2)
    W = lambda c, m: EA[c][m]["dev_weighted"]   # noqa: E731
    a4 = C["A4"]; zm = W("zfix", "d_ax0_maxpool"); za = W("zfix", "d_ax0_attn1")["est"] + W("zfix", "d_ax0_attn2")["est"]
    zsame = (a4["ratio_decim_over_zfix_axis0"]["denominator"]["est"], a4["ratio_decim_over_zfix_lbar1"]["denominator"]["est"])
    att_r = W("zfix_reflect", "pad1_var")["est"]
    rowsc = [("z-fix, Sybil's padding (as published)", f"true spacing minus Sybil's run; max-pool {zm['est']:+.2f}, attention {za:+.2f}",
              W("zfix", "d_ax0"), W("zfix", "d_l1"), W("zfix", "big6"), BLUE, False, None),
             ("every second slice, unmodified Sybil", f"that series minus Sybil's run; {a4['ratio_decim_over_zfix_axis0']['n']} GE + Siemens scans",
              EA["decim0"]["d_ax0"]["dev_weighted"], EA["decim0"]["d_l1"]["dev_weighted"], EA["decim0"]["big6"]["dev_weighted"], BLUE, False, zsame),
             ("z-fix, air padding", "both runs padded with air (-1,000 HU): z-fix minus that run",
              W("zfix_air_vs_main_air", "d_ax0"), W("zfix_air_vs_main_air", "d_l1"), W("zfix_air_vs_main_air", "big6"), ORANGE, False, None),
             ("z-fix, mirrored box ends", f"minus Sybil's run ({100 * att_r:.0f}% of slice attention on the mirror)", W("zfix_reflect", "d_ax0"), None, None, MUTED, True, None),
             ("box filling only", "stretched scan cut to the z-fix's length, padded; minus Sybil's run", W("padmatch", "d_ax0"), None, None, MUTED, True, None),
             ("stretch only, same filling", "z-fix minus the cut-back stretched scan", W("zfix_vs_padmatch", "d_ax0"), None, None, MUTED, True, None)]
    lx, rx = 340, 600; xa, xb = -3.2, 0.4; Xc = lambda v: lx + (v - xa) / (xb - xa) * (rx - lx)   # noqa: E731
    t0, rh, gap = yc + 46, 38, 18; ys = [t0 + rh * i + 14 + (gap if i >= 3 else 0) for i in range(len(rowsc))]; b0 = ys[-1] + 24
    for tt in (-3, -2, -1, 0): s.line(Xc(tt), t0 - 4, Xc(tt), b0, GRID); s.text(Xc(tt), b0 + 14, fmt(tt), 9.5, MUTED, "middle")
    s.line(Xc(0), t0 - 4, Xc(0), b0, INK2, 1.5); s.text((lx + rx) / 2, b0 + 28, "change of shared axis 0 (dev SD)", 9.5, MUTED, "middle")
    s.text(620, t0 - 10, "change of the 1-year logit", 9.5, MUTED); s.text(880, t0 - 10, "6-year logit moves >= 1/4 SD", 9.5, MUTED)
    yd_ = (ys[2] + ys[3]) / 2 - 2
    s.el.append(f'<line x1="20" y1="{yd_:.1f}" x2="1040" y2="{yd_:.1f}" stroke="{GRID}" stroke-width="1" stroke-dasharray="4,3"/>')
    s.text(620, ys[3] + 4, "controls: only the axis-0 change is read (the mirror adds", 9, MUTED); s.text(620, ys[3] + 16, "image content; the cut-back scan loses about half of the lung)", 9, MUTED)
    for i, (lab, sub, v, l1, bg, col, hol, same) in enumerate(rowsc):
        y = ys[i]; s.text(20, y - 2, lab, 10.5, INK, weight="bold"); s.text(20, y + 11, sub, 9, MUTED)
        s.line(Xc(v["lo"]), y, Xc(v["hi"]), y, col, 2); mark(s, "circle", Xc(v["est"]), y, col, r=4.5, hollow=hol)
        s.text(Xc(v["est"]) + (10 if v["est"] < -1 else -10), y - 7, f"{v['est']:+.2f}" + (f" (z-fix on the same scans {same[0]:+.2f})" if same else ""), 9.5, INK2, "start" if v["est"] < -1 else "end")
        if l1 is not None:
            s.text(620, y + 4, f"{l1['est']:+.3f} [{l1['lo']:+.3f}, {l1['hi']:+.3f}]" + (f"  (z-fix on them {same[1]:+.3f})" if same else ""), 9.5, INK2)
            s.text(880, y + 4, f"{100 * bg['est']:.0f}% [{100 * bg['lo']:.0f}, {100 * bg['hi']:.0f}]", 9.5, INK2)
    k1, r3, g2, rd = C["A1"]["kept_share_axis0"], C["A3"]["share_removed_axis0"], C["A2"]["share_geometry_part"], a4["ratio_decim_over_zfix_axis0"]
    nc = [f"Air padding keeps {100 * k1['est']:.1f}% [{100 * k1['lo']:.1f}, {100 * k1['hi']:.1f}] of the axis-0 shift; mirrored box ends remove {100 * r3['est']:.1f}%; "
          f"at the same filling the stretch alone gives {100 * g2['est']:.1f}% [{100 * g2['lo']:.1f}, {100 * g2['hi']:.1f}]. Every second slice gives {rd['est']:.3f} "
          f"[{rd['lo']:.3f}, {rd['hi']:.3f}] times the z-fix shift.",
          "With air padding the mean logit change is near 0, but the exam-by-exam scatter stays (right column): air padding does not fix Sybil, and it moves ordinary scans",
          "out of their usual range of axis 0. Every-second-slice row: GE and Siemens only (the one Philips scan with ratio 0.5 is left out by the rule of >= 5 per maker).",
          "How axis 0 depends on the padding left in the box across all 7,336 dev scans: Supplementary Figure S1."]
    for k, t in enumerate(nc): s.text(20, b0 + 48 + 14 * k, t, 9.5, MUTED)
    s.h = int(b0 + 48 + 14 * len(nc) + 16); s.el[0] = f'<rect width="{s.w}" height="{s.h}" fill="{SURF}"/>'
    s.save(out / "fig4_mechanism_inside.svg")


def figS1(out):
    """Supplementary Figure S1: absolute shared axis 0 of all dev main runs against the padded slices in Sybil's 200-slice box, by ratio group.
    Source: results/x11/x11_padcurve_fine_dev.json (POST HOC 8-slice bins, added after Neon's review; the planned 16-slice bins are in
    x11_padcurve_dev.json). Bins with fewer than 5 scans are not drawn."""
    from s6_figures import fmt
    pf = HERE / "results" / "x11" / "x11_padcurve_fine_dev.json"
    if not pf.exists(): return
    PF = json.loads(pf.read_text(encoding="utf-8")); PC = json.loads((HERE / "results" / "x11" / "x11_padcurve_dev.json").read_text(encoding="utf-8"))
    s = Svg(1060, 420)
    s.text(20, 28, "Supplementary Figure S1. Shared axis 0 against the padding left in Sybil's 200-slice box", 15, weight="bold")
    s.text(20, 48, "All 7,336 NLST dev scans as Sybil read them (no new run; exploratory; no outcome read). Padded slices: slices holding only padding, both ends together; 0 = box full", 10, INK2)
    def xb(k): return 0.0 if k == "0" else (100.0 if k == ">96" else (int(k.split("-")[0]) + int(k.split("-")[1])) / 2)   # noqa: E306
    x0, w, ylo, yhi = 80, 560, -1.0, 2.7; top, ph = 86, 230
    Xp = lambda p: x0 + (p + 3) / 107 * w; Yp = lambda v: top + ph - (v - ylo) / (yhi - ylo) * ph   # noqa: E731
    q = PC["summary"]["contiguous"]["p_quantiles"]
    rect(s, Xp(q["0.05"]), top, Xp(q["0.95"]) - Xp(q["0.05"]), ph, ORANGE, op=0.08)
    s.text((Xp(q["0.05"]) + Xp(q["0.95"])) / 2, top + 12, "contiguous scans,", 9, ORANGE, "middle")
    s.text((Xp(q["0.05"]) + Xp(q["0.95"])) / 2, top + 24, "5th to 95th percentile", 9, ORANGE, "middle")
    for t in (-1, 0, 1, 2): s.line(x0, Yp(t), x0 + w, Yp(t), GRID); s.text(x0 - 6, Yp(t) + 3.5, fmt(t), 9.5, MUTED, "end")
    for p in (0, 16, 32, 48, 64, 80, 96): s.text(Xp(p), top + ph + 14, str(p), 9.5, MUTED, "middle")
    s.text(x0 + w / 2, top + ph + 28, "padded slices in Sybil's 200-slice box (8-slice bins; > 96 drawn at 100)", 9.5, MUTED, "middle")
    s.text(x0 - 40, top - 12, "shared axis 0 (dev SD), absolute", 10, INK, weight="bold")
    groups = (("overlapping_0_0p65", "overlapping (ratio <= 0.65)", BLUE, "circle", -0.9), ("moderate_0p65_0p95", "moderate overlap (0.65-0.95)", MUTED, "square", 0.0),
              ("contiguous_0p95_1p05", "contiguous (0.95-1.05)", ORANGE, "diamond", 0.9))
    for g, lab, col, shp, dx in groups:
        pts = [(Xp(xb(k) + dx), Yp(v["mean"]), v) for k, v in PF["bins"][g].items() if v["n"] >= 5]
        s.el.append('<polyline points="' + " ".join(f"{a:.1f},{b:.1f}" for a, b, _ in pts) + f'" fill="none" stroke="{col}" stroke-width="1.2" stroke-opacity="0.6"/>')
        for a, b, v in pts:
            if v["lo"] is not None: s.line(a, Yp(v["lo"]), a, Yp(v["hi"]), col, 1.6)
            mark(s, shp, a, b, col, r=3.5, hollow=(shp == "square"))
    lgx = 680
    for k, (g, lab, col, shp, dx) in enumerate(groups):
        mark(s, shp, lgx, top + 2 + 18 * k, col, r=4, hollow=(shp == "square")); s.text(lgx + 12, top + 6 + 18 * k, f"{lab}: {PF['counts']['by_group'][g]:,} scans", 10, INK2)
    B = PF["bins"]; cg = B["contiguous_0p95_1p05"]; nc = PF["counts"]["by_group"]["contiguous_0p95_1p05"]; nm = PF["counts"]["by_group"]["moderate_0p65_0p95"]
    c64 = sum(v["n"] for k, v in cg.items() if xb(k) > 64); c48 = sum(v["n"] for k, v in cg.items() if xb(k) <= 48)
    m32 = sum(v["n"] for k, v in B["moderate_0p65_0p95"].items() if xb(k) <= 32)
    n_other = PF["counts"]["by_group"]["gaps_gt_1p05"] + PF["counts"]["by_group"]["ratio_0_or_missing"]
    side = [f"Where groups share a bin they agree within about 0.1 SD (49-56: {cg['49-56']['mean']:+.2f}, {B['moderate_0p65_0p95']['49-56']['mean']:+.2f}, "
            f"{B['overlapping_0_0p65']['49-56']['mean']:+.2f}):",
            "axis 0 depends on how much padding is left, not on why it is thin.",
            f"Contiguous scans: {100 * c64 / nc:.0f}% have more than 64 padded slices (flat part);",
            f"{100 * c48 / nc:.1f}% have 48 or fewer.",
            f"Moderate overlap: {m32} of {nm:,} ({100 * m32 / nm:.0f}%) have 32 or fewer (steep part).",
            f"Not drawn: {n_other} scans with gaps (ratio > 1.05) or ratio 0;",
            "bins with fewer than 5 scans.",
            "Observational: scans with thin padding may differ in other ways too;",
            "the experiments of Figure 4 (b, c) point the same way."]
    for k, t in enumerate(side): s.text(lgx - 8, top + 76 + 15 * k, t, 9.5, MUTED)
    s.text(20, top + ph + 52, "Each point: mean axis 0 with its 95% participant-bootstrap interval; points of a bin are spread sideways. The 8-slice bins were added after an outside review "
           "(post hoc);", 9.5, MUTED)
    s.text(20, top + ph + 66, "the planned 16-slice bins (results/x11/x11_padcurve_dev.json) give the same picture except that the wide 33-48 bin mixes the steep part.", 9.5, MUTED)
    s.save(out / "figS1_padding_curve.svg")


def box(s, x, y, w, lines, edge=BASE, head=None, h=None, dash=False):
    hh = h or 16 * len(lines) + 14; rect(s, x, y, w, hh, SURF, edge, 1.5, rx=6)
    if dash: s.el[-1] = s.el[-1].replace("/>", ' stroke-dasharray="6,4"/>')
    for i, (t, size, col, wt) in enumerate(lines): s.text(x + 10, y + 20 + i * 16, t, size, col, weight=wt)
    return hh


def arrow(s, x1, y1, x2, y2):
    s.line(x1, y1, x2, y2, INK2, 1.5); s.el.append(f'<path d="M{x2:.1f},{y2:.1f} l-4,-8 l8,0 Z" fill="{INK2}"/>' if x1 == x2 else "")


def fig2(out):
    """study flow from committed counts: lung_l0/results/l0_results.json, results/s6/assemble_test.json, the dev assemble record (logged),
    results/manifest_unseen.csv tiers, results/manifest_lidc.csv (X5)."""
    R = HERE / "results"; ld = lambda p: json.loads(p.read_text(encoding="utf-8"))   # noqa: E731
    L0 = ld(HERE.parent / "lung_l0" / "results" / "l0_results.json"); P = L0["participants"]; C = L0["counts_all_screens"]
    AT = ld(R / "s6" / "assemble_test.json"); S0 = ld(R / "s0_series_rule.json")["dev"]; S1 = ld(R / "s1_manifest.json"); MT = ld(R / "s6_manifest_test.json")
    FP = ld(R / "l2_form_params.json"); O2 = ld(R / "o2_manifest.json"); X5 = ld(R / "x5_lidc_manifest.json"); X12 = ld(R / "x12" / "x12_overlap_prevalence.json")
    S6 = ld(R / "s6" / "s6_test.json"); P2 = ld(R / "x7" / "x7_sensitivity_test.json")["P2_censoring_E4"]["description"]
    y1, y6 = S6["secondary"]["y1"]["counts"], S6["secondary"]["y6"]["counts"]; att = dict(X12["attrition"]); ac = X12["sets"]["all_chest"]
    assert S0["studies_with_selected_series"] - S1["dev_main_rows"] == 2 * S0["dup_pid_year"] and O2["exams_selected"] - O2["not_selected_exams"] == O2["U1"]["rows"] + O2["U2"]["rows"]
    s = Svg(1060, 500); s.text(20, 28, "Figure 2. Study flow", 15, weight="bold")
    B, I, M = (INK, "bold"), (INK2, "normal"), (MUTED, "normal")
    # internal NLST frame
    s.el.append(f'<rect x="10" y="40" width="1040" height="282" fill="none" stroke="{GRID}" stroke-width="1.5" rx="8"/>')
    s.text(20, 58, "INTERNAL TESTING: NLST, one trial (33 US centres, enrolment 2002-2004). Every split, including the participants Sybil never used, is internal.", 10.5, INK2, weight="bold")
    box(s, 302, 68, 460, [(f"NLST CT arm (public tables): {P['ct_arm_in_public_table']:,} participants", 12, *B),
                          (f"Sybil's published split file: {P['split_file']:,}; not in it: {P['by_group']['unseen']:,}", 10, *I)])
    arrow(s, 532, 114, 532, 132); s.line(142, 132, 922, 132, INK2, 1.5)
    tr, dv, ts, un = (P["by_group"][k] for k in ("train", "dev", "test", "unseen"))
    cols = [(20, "Sybil's train split", [f"{tr:,} participants, {C['train']['exams']:,} exams", "Sybil was trained here (by its developers)", "we fit only the radiologists' forms here:",
                                         f"1-year: {FP['F1']['n_fit']:,} exams ({C['train']['exams'] - FP['F1']['n_fit']} without a", f"  1-year outcome), {FP['F1']['n_fit_pos']} cancers",
                                         f"6-year: {FP['F6']['n_fit']:,} baseline exams, {FP['F6']['n_fit_pos']} cancers"], BASE, False),
            (280, "Sybil's dev split (discovery)", [f"{dv:,} participants, {C['dev']['exams']:,} exams in tables", f"{S0['ct_studies']:,} CT studies on IDC; {S0['ct_studies'] - S0['studies_with_selected_series']} without",
                                                   f"  an eligible series, {2 * S0['dup_pid_year']} duplicate person-years", f"{S1['dev_main_rows']:,} scored ({S1['participants']:,} participants; 0 failed)",
                                                   "Sybil's model selection split: in-sample", "used for our discovery work"], BASE, False),
            (540, "Sybil's test split (held out)", [f"{ts:,} participants, {C['test']['exams']:,} exams in tables", f"split file: {MT['split_test_series']:,} series, all scored (0 failed)",
                                                    f"+ {AT['n_zfix']} z-fix runs, {AT['n_pair']} kernel pairs", f"1-year: {y1['exams']:,} exams ({AT['n_main'] - y1['exams']} unknown), {y1['cancers']} cancers",
                                                    f"6-year, baseline: {P2['observed']:,} of {P2['baseline_exams']:,} ({P2['censored']} censored),", f"  {P2['cancers']} cancers. Six pre-registered tests"], BLUE, False),
            (800, "Never used by Sybil", [f"{un:,} participants ({C['unseen']['participants']:,} with {C['unseen']['exams']:,} exams)", f"{O2['unseen_participants_with_ct']:,} with CT on IDC; {O2['participants_selected']:,} kept",
                                          f"  ({O2['exams_selected']:,} exams); {O2['not_selected_exams']:,} not", f"  overlapping and not a partner scan", f"{O2['U1']['rows']:,} overlapping scans ({O2['U1']['participants']:,} people)",
                                          f"+ {O2['U2']['rows']} partner scans; pre-registered, from 1 Dec"], MUTED, True)]
    for x, title, lines, edge, dash in cols:
        arrow(s, x + 122, 132, x + 122, 148)
        box(s, x, 148, 245, [(title, 11, *B)] + [(t, 10, *I) for t in lines], edge=edge, dash=dash)
    s.text(20, 290, f"Only {C['unseen']['participants_with_later_cancer']} of the never-used participants have a later lung cancer, so this group tests the mechanism, not cancer detection.", 10, INK2)
    s.text(20, 306, "Exams with an unknown outcome are left out only of the analyses that need that outcome. Sybil's developers do not state why participants are outside the split file.", 10, MUTED)
    # outside NLST
    s.text(20, 350, "EXTERNAL REPLICATION OF THE MECHANISM", 10.5, INK2, weight="bold"); s.text(540, 350, "HOW COMMON THE GEOMETRY IS TODAY (HEADERS ONLY)", 10.5, INK2, weight="bold")
    mk = X5["by_maker"]
    box(s, 20, 360, 500, [("LIDC-IDRI (7 US academic centres; clinical CT, not screening)", 11, *B),
                          (f"{X5['lidc_patients']:,} patients ({X5['lidc_ct_series']:,} CT series) → {X5['patients']} with a strongly overlapping series", 10, *I),
                          (f"(one per patient; GE {mk['GE MEDICAL SYSTEMS']}, Philips {mk['Philips']}, Siemens {mk['SIEMENS']}); no cancer outcome", 10, *I)], edge=ORANGE)
    box(s, 540, 360, 500, [("Imaging Data Commons, all CT collections (no model run)", 11, *B),
                           (f"{att['CT series']:,} CT series → {att['chest']:,} axial chest series → {ac['series']:,} at ≤ 3 mm", 10, *I),
                           (f"({ac['studies']:,} studies, {ac['patients']:,} patients, {ac['collections']} collections)", 10, *I)])
    s.text(20, 464, "Edges: blue = confirmatory (pre-registered, test split); orange = exploratory external replication; dashed grey = pre-registered, not yet run.", 10, MUTED)
    s.text(20, 480, "Image data: NLST on Imaging Data Commons (CC BY 4.0), LIDC-IDRI (CC BY 3.0); outcomes from the NLST tables. Selection rules and cut-offs: Methods and Supplement.", 10, MUTED)
    s.save(out / "fig2_flow.svg")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--ct-dir"); a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    fig2(out); fig3(out); fig4(out); fig5(out); fig6(out); figS1(out)
    if a.ct_dir: fig1(Path(a.ct_dir), Path(a.ct_dir))                          # Figure 1 holds CT pixels: written next to the PNGs, outside git
    print("figures written")


if __name__ == "__main__":
    main()
