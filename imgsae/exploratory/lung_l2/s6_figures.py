"""Lung L2, N7: draft figures from the committed result files only (no new analysis): results/s5/s6_dev_as_if_test.json (dev) and
results/s6/s6_test.json (test). Plain SVG (no plotting package is installed in the project environment). Colours: validated two-slot
palette (blue #2a78d6, orange #eb6834; dataviz validator: all checks pass, worst CVD dE 24.7); ink and grid from the reference palette.
  fig1_hypotheses.svg  the six frozen hypotheses: dev and test estimate with 95% CI, the null, the Holm result
  fig2_axis0.svg       the z-geometry axis: z-fix change of lbar_1 as is and with axis 0 off (dev, test); real follow-up group means (test)
  fig3_auroc.svg       AUROC of Sybil, the recorded-findings form F and form + image measures (FI), dev and test, 1 and 6 years
usage (venv python): python s6_figures.py <out dir>
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BLUE, ORANGE = "#2a78d6", "#eb6834"
SURF, INK, INK2, MUTED, GRID, BASE = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
FONT = "system-ui, -apple-system, 'Segoe UI', sans-serif"


class Svg:
    def __init__(self, w, h): self.w, self.h, self.el = w, h, [f'<rect width="{w}" height="{h}" fill="{SURF}"/>']
    def text(self, x, y, s, size=12, fill=INK, anchor="start", weight="normal"):
        s = str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.el.append(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}">{s}</text>')
    def line(self, x1, y1, x2, y2, stroke=GRID, w=1): self.el.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{w}" stroke-linecap="round"/>')
    def dot(self, x, y, fill, r=4.5): self.el.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" stroke="{SURF}" stroke-width="2"/>')
    def save(self, p): Path(p).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}">' + "".join(self.el) + "</svg>\n", encoding="utf-8")


def ticks(lo, hi, n=4):
    import math
    span = hi - lo; step = 10 ** math.floor(math.log10(span / n)); step *= min((m for m in (1, 2, 2.5, 5, 10) if span / (step * m) <= n + 1), default=10)
    t = math.ceil(lo / step) * step; out = []
    while t <= hi + 1e-12: out.append(round(t, 10)); t += step
    return out


def fmt(v): return f"{v:.2f}".rstrip("0").rstrip(".") if abs(v) >= 0.1 or v == 0 else f"{v:.3f}".rstrip("0")


def interval_panel(s, x0, y0, w, title, rows, null=None, sub=None, lo=None, hi=None, null_label="null"):
    """rows: list of (label, est, ci_lo or None, ci_hi or None, colour). Horizontal value axis at the bottom."""
    vals = [v for r in rows for v in r[1:4] if v is not None] + ([null] if null is not None else [])
    a, b = (min(vals) if lo is None else lo), (max(vals) if hi is None else hi); pad = (b - a) * 0.15 or 0.1; a, b = a - pad, b + pad
    lx, rx = x0 + 92, x0 + w - 10; X = lambda v: lx + (v - a) / (b - a) * (rx - lx)   # noqa: E731
    s.text(x0, y0, title, 13, INK, weight="600")
    if sub: s.text(x0, y0 + 16, sub, 11, INK2)
    top = y0 + (42 if sub else 28); rh = 26; bot = top + rh * len(rows) + 6
    for t in ticks(a, b):
        s.line(X(t), top, X(t), bot, GRID); s.text(X(t), bot + 14, fmt(t), 10, MUTED, "middle")
    s.line(lx, bot, rx, bot, BASE)
    if null is not None:
        s.line(X(null), top - 4, X(null), bot, INK2, 1.5); s.text(X(null), top - 7, f"{null_label} {fmt(null)}".strip(), 10, INK2, "middle")
    for i, (lab, est, cl, ch, col) in enumerate(rows):
        y = top + rh * i + rh / 2 + 2; s.text(x0, y + 4, lab, 11, INK2)
        if cl is not None: s.line(X(cl), y, X(ch), y, col, 2)
        s.dot(X(est), y, col)
    return bot + 22


def legend(s, x, y, items):
    for lab, col in items:
        s.dot(x + 5, y - 4, col); s.text(x + 15, y, lab, 11, INK2); x += 22 + 7 * len(lab)


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    dev = json.loads((HERE / "results/s5/s6_dev_as_if_test.json").read_text()); tst = json.loads((HERE / "results/s6/s6_test.json").read_text())
    D, T = {h["id"]: h for h in dev["hypotheses"]}, {h["id"]: h for h in tst["hypotheses"]}
    # ---- figure 1: the six hypotheses
    names = dict(H1="H1  z-fix moves the score (share ≥ ¼ SD)", H2="H2  z-fix lowers the score (mean Δ logit)", H3="H3  z-fix changes the flag (share)",
                 H4="H4  kernel changes the flag (share)", H6="H6  axis 0 carries the z-fix drop (logit)", H7="H7  follow-up jump with stretch change (b)")
    s = Svg(940, 450); s.text(20, 26, "Six frozen hypotheses: dev (discovery) and test (opened once)", 15, INK, weight="600")
    legend(s, 20, 46, [("test, 95% CI", BLUE), ("dev, 95% CI", ORANGE)])
    for k, hid in enumerate(("H1", "H2", "H3", "H4", "H6", "H7")):
        d, t = D[hid], T[hid]; x0, y0 = 20 + (k % 3) * 307, 84 + (k // 3) * 178
        res = "confirmed (Holm)" if t["confirmed_holm"] else "NOT confirmed"
        interval_panel(s, x0, y0, 290, names[hid], [("test", t["est"], *t["ci95"], BLUE), ("dev", d["est"], *d["ci95"], ORANGE)], null=t["null"],
                       sub=f"{'>' if t['direction'] == '>' else '<'} null · test: {res}")
    s.text(20, 438, "Test: 759 z-fix exams (342 participants) for H1–H3 and H6; 500 kernel pairs for H4; 4,353 consecutive-screen pairs (134 changed) for H7.", 10, MUTED)
    s.save(out / "fig1_hypotheses.svg")
    # ---- figure 2: axis 0
    sd, st = dev["secondary_new_freeze"], tst["secondary_new_freeze"]
    s = Svg(940, 360); s.text(20, 26, "One shared direction (axis 0 of Sybil's pooled layer) carries the slice-spacing effect", 15, INK, weight="600")
    legend(s, 20, 46, [("Sybil as is", BLUE), ("axis 0 set to its dev mean", ORANGE)])
    rows = [("dev, as is", sd["H6_detail"]["mean_delta_lbar1_from_pooled"], None, None, BLUE), ("dev, axis 0 off", sd["H6_detail"]["mean_delta_lbar1_axis0_off"], None, None, ORANGE),
            ("test, as is", st["H6_detail"]["mean_delta_lbar1_from_pooled"], None, None, BLUE), ("test, axis 0 off", st["H6_detail"]["mean_delta_lbar1_axis0_off"], None, None, ORANGE)]
    interval_panel(s, 20, 84, 440, "Z-fix: mean change of the 1-year logit", rows, null=0.0, sub="true slice spacing minus Sybil's spacing (T5)", lo=-0.45, hi=0.15, null_label="no change")
    g = st["H7_followup"]["groups"]; lab = dict(stretched_to_not="stretched → not", unchanged="unchanged", not_to_stretched="not → stretched")
    rows = []
    for k in ("stretched_to_not", "unchanged", "not_to_stretched"):
        rows += [(f"{lab[k]} ({g[k]['n']:,})", g[k]["mean_dl"], None, None, BLUE), ("   axis 0 off", g[k]["mean_dl_off"], None, None, ORANGE)]
    interval_panel(s, 480, 84, 440, "Real yearly screening (test): mean change of the 1-year logit", rows, null=0.0, sub="later minus earlier screen, by change of stretch status", lo=-0.25, hi=0.45, null_label="no change")
    s.text(20, 348, "Test H6 = +0.407 [0.401, 0.411] (null +0.20); H7 b = +0.311 [0.185, 0.435], with axis 0 off −0.046 [−0.175, 0.078]; 121 of 134 changed pairs involve a GE scanner.", 10, MUTED)
    s.save(out / "fig2_axis0.svg")
    # ---- figure 3: AUROC
    s = Svg(940, 330); s.text(20, 26, "Discrimination: dev flatters Sybil; on test it does not beat the recorded findings", 15, INK, weight="600")
    legend(s, 20, 46, [("test, 95% CI", BLUE), ("dev, 95% CI", ORANGE)])
    for k, (y, ttl) in enumerate((("y1", "Cancer within 1 year, all screens (AUROC)"), ("y6", "Cancer within 6 years, baseline screens (AUROC)"))):
        rows = []
        for key, nm in (("sybil", "Sybil"), ("F", "form F"), ("FI", "form + image")):
            a, b = tst["secondary"][y][key], dev["secondary"][y][key]
            rows += [(f"{nm}, test", a["est"], a["lo"], a["hi"], BLUE), (f"{nm}, dev", b["est"], b["lo"], b["hi"], ORANGE)]
        c = tst["secondary"][y]["counts"]
        interval_panel(s, 20 + k * 470, 84, 440, ttl, rows, sub=f"test: {c['exams']:,} exams, {c['cancers']} cancers")
    s.save(out / "fig3_auroc.svg")
    print("written:", sorted(p.name for p in out.glob("*.svg")))


if __name__ == "__main__":
    main()
