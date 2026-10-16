#!/usr/bin/env python3
"""The animated isometric ML pipeline on the profile README.

Ten stages, in the order the work actually happens, with data packets travelling
between them, each stage lighting as a packet arrives, and a small chart growing
inside the stages that have a real number behind them.

Why SVG + SMIL rather than a video
----------------------------------
GitHub strips <script> from README SVGs but runs <animate> and <animateMotion>,
so SMIL is the only way to get motion that is also crisp at any zoom, tiny on the
wire, and themeable. The whole thing is about 30 KB per theme — two orders of
magnitude under the 3 MB budget, which leaves that budget for the 3D scenes.

Isometric projection
--------------------
A true isometric axonometric: the two ground axes sit at +/-30 degrees from
horizontal and z rises vertically.

    sx = (x - y) * cos(30)
    sy = (x + y) * sin(30) - z

Every face is drawn from that one transform, so the slabs cannot drift out of a
consistent projection the way hand-placed parallelograms do.

Every number printed is verified in _portfolio-work/FACTS.md. Stages that have no
verified number carry no number.

    python scripts/make_pipeline_iso.py
"""

from __future__ import annotations

import math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets"

W = 1480          # height is derived from the content; see build()
CYCLE = 14.0          # seconds for one full pass of the pipeline

COS30, SIN30 = math.cos(math.radians(30)), math.sin(math.radians(30))

THEMES = {
    "light": dict(
        bg="#FBFAF7", ink="#14181D", muted="#5A6472", hair="#E2DFD8",
        top="#FFFFFF", left="#EFEDE8", right="#E4E1DA", rail="#C9CFD6",
        glow="#00897B",
    ),
    "dark": dict(
        bg="#0E1116", ink="#E8EDF2", muted="#8B97A6", hair="#263040",
        top="#1A2029", left="#141A22", right="#10151C", rail="#2C3847",
        glow="#2DD4BF",
    ),
}

TEAL, PURPLE, ORANGE, MAGENTA = "#00897B", "#6D28D9", "#C2410C", "#BE185D"

# (label, sublabel, accent, stat, stat_label)
# A stat is printed only where FACTS.md verifies one for that step.
STAGES = [
    ("Sources",      "simulation · OSM · PDF", TEAL,   "",          ""),
    ("Ingestion",    "batch + stream",        TEAL,    "",          ""),
    ("Validation",   "schema · ranges",       TEAL,    "14",        "gates"),
    ("Features",     "5 link features",       PURPLE,  "",          ""),
    ("Graph build",  "line graph",            PURPLE,  "31,635",    "nodes"),
    ("Training",     "graph network",         PURPLE,  "1.4M",      "params"),
    ("Evaluation",   "held-out split",        ORANGE,  "3,163,500", "predictions"),
    ("Uncertainty",  "calibration",           ORANGE,  "−82%",      "cal. error"),
    ("Serving",      "FastAPI · Docker · CI", MAGENTA, "1e-9",      "CI tolerance"),
    ("Monitoring",   "drift watch",           MAGENTA, "0.679",     "drift caught"),
]

# Little bar charts that grow inside a stage. Heights are relative only — they
# are decoration showing "a chart lives here", not a plotted quantity, so they
# carry no axis and no number.
SPARK = {2: [3, 5, 4, 6], 6: [2, 4, 5, 6], 7: [6, 4, 3, 2], 9: [2, 3, 6, 4]}


def iso(x, y, z=0.0):
    return ((x - y) * COS30, (x + y) * SIN30 - z)


def slab(ox, oy, w, d, h, t):
    """One isometric box: top face, left face, right face."""
    p = {}
    for name, (x, y, z) in {
        "a": (0, 0, h), "b": (w, 0, h), "c": (w, d, h), "d": (0, d, h),
        "e": (0, 0, 0), "f": (w, 0, 0), "g": (w, d, 0), "h2": (0, d, 0),
    }.items():
        sx, sy = iso(x, y, z)
        p[name] = (ox + sx, oy + sy)

    def poly(pts, fill, extra=""):
        s = " ".join(f"{p[k][0]:.1f},{p[k][1]:.1f}" for k in pts)
        return f'<polygon points="{s}" fill="{fill}"{extra}/>'

    return (
        poly(["e", "f", "g", "h2"], t["right"], ' opacity="0"'),   # hidden base
        poly(["a", "b", "f", "e"], t["left"]),                     # front-left
        poly(["b", "c", "g", "f"], t["right"]),                    # front-right
        poly(["a", "b", "c", "d"], t["top"]),                      # top
        p,
    )


def build(theme: str) -> str:
    t = THEMES[theme]
    uid = f"iso{theme}"

    # Two rows of five, snaking — not one row of ten.
    #
    # Two things drive this. First, the projection: sy = (x + y) * sin30, so
    # stepping along +x alone moves the chain right AND down, and ten of those
    # staircase off the bottom of a banner. Walking the (+1, -1) diagonal cancels
    # the two terms and keeps the run level while every slab stays true isometric.
    #
    # Second, and the reason for two rows rather than one long level one: GitHub
    # renders a README image at roughly 860 px wide. Ten stages across that is 86
    # px each, which is narrower than most of the labels — they collided, and at
    # display size they would have been illegible anyway. Five per row doubles the
    # width each stage gets.
    #
    # The second row runs right-to-left so stage 6 sits directly beneath stage 5
    # and the connector between rows is a short vertical drop. Adding the same
    # amount to x and y moves straight down on screen, since sx = (x - y) is
    # unchanged by it.
    step, drop = 0.92, 1.55
    coords = []
    for i in range(len(STAGES)):
        row, j = divmod(i, 5)
        d = j if row == 0 else (4 - j)       # snake back along the second row
        wave = 0.16 * math.sin(i * 1.1)
        gx = d * step + row * drop + wave
        gy = -d * step + row * drop + wave
        coords.append((gx, gy))

    # Fit the drawing to the canvas, counting the type as part of it.
    #
    # Bounding only the slab corners is what left a band of dead space below and
    # pushed the stats onto the slab edges: a label sits ~58 px above its slab and
    # a stat ~56 px below, and neither is in the geometry. Measure the grid, add
    # those bands in pixels, then solve for the scale that fits both axes.
    corners = []
    for gx, gy in coords:
        for cx, cy, cz in ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
                           (0, 0, bh_u := 0.30), (1, 0, bh_u), (1, 1, bh_u),
                           (0, 1, bh_u)):
            sx, sy = iso(gx + cx, gy + cy, cz)
            corners.append((sx, sy))
    x0, x1 = min(c[0] for c in corners), max(c[0] for c in corners)
    y0, y1 = min(c[1] for c in corners), max(c[1] for c in corners)

    # Width is the binding constraint — GitHub scales a README image to the
    # column — so fix the scale from the width and let the height follow. Fixing
    # both left a quarter of the canvas empty underneath, because the content is
    # wider than it is tall and the width always won the min().
    #
    # PAD_X has to clear the *labels*, not the slabs: a centred label on the last
    # stage overhangs its slab by roughly half its own width, which is what put
    # the right-hand slab against the edge.
    PAD_X, PAD_TOP, PAD_BOT = 125, 86, 84
    sc = (W - 2 * PAD_X) / (x1 - x0)
    ox = W / 2 - (x0 + x1) / 2 * sc
    oy = PAD_TOP - y0 * sc
    height = int(round((y1 - y0) * sc)) + PAD_TOP + PAD_BOT

    def place(gx, gy):
        sx, sy = iso(gx, gy)
        return ox + sx * sc, oy + sy * sc

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" '
        f'viewBox="0 0 {W} {height}" role="img" '
        f'aria-label="An animated isometric diagram of a machine learning '
        f'pipeline: sources, ingestion, validation, features, graph build, '
        f'training, evaluation, uncertainty, serving and monitoring, with data '
        f'packets flowing between the stages.">',
        f'<rect width="{W}" height="{height}" fill="{t["bg"]}"/>',
        "<defs>",
        f'<linearGradient id="{uid}sheen" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{t["glow"]}" stop-opacity="0"/>'
        f'<stop offset=".5" stop-color="{t["glow"]}" stop-opacity=".55"/>'
        f'<stop offset="1" stop-color="{t["glow"]}" stop-opacity="0"/>'
        "</linearGradient>",
        f'<filter id="{uid}soft" x="-60%" y="-60%" width="220%" height="220%">'
        '<feGaussianBlur stdDeviation="7"/></filter>',
        "</defs>",
    ]

    bw, bd, bh = 1.0, 1.0, 0.30
    per = CYCLE / len(STAGES)

    # ---- rails first, so the slabs sit on top of them --------------------
    for i in range(len(STAGES) - 1):
        x0, y0 = place(*coords[i])
        x1, y1 = place(*coords[i + 1])
        # Enter and leave at the centre of each slab's top face.
        cx0, cy0 = iso(bw / 2, bd / 2, bh)
        cx1, cy1 = iso(bw / 2, bd / 2, bh)
        ax, ay = x0 + cx0 * sc, y0 + cy0 * sc
        bx, by = x1 + cx1 * sc, y1 + cy1 * sc
        out.append(
            f'<path id="{uid}r{i}" d="M {ax:.1f} {ay:.1f} L {bx:.1f} {by:.1f}" '
            f'fill="none" stroke="{t["rail"]}" stroke-width="2.4" '
            f'stroke-linecap="round"/>')
        # A sheen that sweeps the rail just before the packet crosses it.
        out.append(
            f'<path d="M {ax:.1f} {ay:.1f} L {bx:.1f} {by:.1f}" fill="none" '
            f'stroke="url(#{uid}sheen)" stroke-width="5" stroke-linecap="round" '
            f'opacity="0">'
            f'<animate attributeName="opacity" values="0;1;0" dur="{CYCLE}s" '
            f'keyTimes="0;{(i*per+per*.45)/CYCLE:.4f};{(i*per+per*1.0)/CYCLE:.4f}" '
            f'begin="0s" repeatCount="indefinite"/></path>')

    # ---- stages ----------------------------------------------------------
    for i, (label, sub, accent, stat, stat_label) in enumerate(STAGES):
        x, y = place(*coords[i])
        base, left, right, top, p = slab(x, y, bw * sc, bd * sc, bh * sc, t)
        lit_at = (i * per + per * 0.92) / CYCLE

        out.append(f'<g id="{uid}s{i}">')
        out.append(base)
        out.append(left)
        out.append(right)
        out.append(top)

        # Accent edge along the top-front of the slab.
        out.append(
            f'<path d="M {p["a"][0]:.1f},{p["a"][1]:.1f} '
            f'L {p["b"][0]:.1f},{p["b"][1]:.1f} '
            f'L {p["c"][0]:.1f},{p["c"][1]:.1f}" fill="none" '
            f'stroke="{accent}" stroke-width="2.2" opacity=".30">'
            f'<animate attributeName="opacity" values=".30;1;.30" '
            f'dur="{CYCLE}s" keyTimes="0;{lit_at:.4f};{min(lit_at+0.075,1):.4f}" '
            f'repeatCount="indefinite"/></path>')

        # The glow that fires as the packet lands.
        gx, gy = p["a"][0] + (p["c"][0] - p["a"][0]) / 2, \
                 p["a"][1] + (p["c"][1] - p["a"][1]) / 2
        out.append(
            f'<ellipse cx="{gx:.1f}" cy="{gy:.1f}" rx="46" ry="26" '
            f'fill="{accent}" filter="url(#{uid}soft)" opacity="0">'
            f'<animate attributeName="opacity" values="0;.45;0" dur="{CYCLE}s" '
            f'keyTimes="0;{lit_at:.4f};{min(lit_at+0.075,1):.4f}" '
            f'repeatCount="indefinite"/></ellipse>')

        # A small chart growing on the top face, where one belongs.
        if i in SPARK:
            vals = SPARK[i]
            bx0, by0 = iso(0.22, 0.78, bh)
            for j, v in enumerate(vals):
                hx, hy = iso(0.22 + j * 0.16, 0.78, bh)
                px, py = x + hx * sc, y + hy * sc
                full = 6 + v * 4.6
                out.append(
                    f'<rect x="{px:.1f}" y="{py - full:.1f}" width="7" '
                    f'height="{full:.1f}" rx="1.6" fill="{accent}" opacity=".85">'
                    f'<animate attributeName="height" values="0;{full:.1f}" '
                    f'dur="0.7s" begin="{i*per + 0.18*j:.2f}s" fill="freeze"/>'
                    f'<animate attributeName="y" values="{py:.1f};{py - full:.1f}" '
                    f'dur="0.7s" begin="{i*per + 0.18*j:.2f}s" fill="freeze"/>'
                    f'<animate attributeName="height" values="{full:.1f};0" '
                    f'dur="0.3s" begin="{CYCLE - 0.4:.2f}s" fill="freeze"/>'
                    "</rect>")

        out.append("</g>")

        # Labels float above the slab, upright — isometric type is unreadable.
        tx, ty = p["a"][0] + (p["c"][0] - p["a"][0]) / 2, p["a"][1] - 34
        out.append(
            f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="middle" '
            f'font-family="Segoe UI, Helvetica, Arial, sans-serif" '
            f'font-size="27" font-weight="700" fill="{t["ink"]}">{label}</text>')
        out.append(
            f'<text x="{tx:.1f}" y="{ty + 25:.1f}" text-anchor="middle" '
            f'font-family="Segoe UI, Helvetica, Arial, sans-serif" '
            f'font-size="18" fill="{t["muted"]}">{sub}</text>')
        if stat:
            sy2 = p["h2"][1] + 50
            out.append(
                f'<text x="{tx:.1f}" y="{sy2:.1f}" text-anchor="middle" '
                f'font-family="Cascadia Mono, Consolas, monospace" '
                f'font-size="23" font-weight="700" fill="{accent}" opacity=".35">'
                f'{stat}'
                f'<animate attributeName="opacity" values=".35;1;.35" '
                f'dur="{CYCLE}s" keyTimes="0;{lit_at:.4f};'
                f'{min(lit_at+0.10,1):.4f}" repeatCount="indefinite"/></text>')
            out.append(
                f'<text x="{tx:.1f}" y="{sy2 + 21:.1f}" text-anchor="middle" '
                f'font-family="Segoe UI, Helvetica, Arial, sans-serif" '
                f'font-size="16" fill="{t["muted"]}">{stat_label}</text>')

    # ---- packets ---------------------------------------------------------
    # Three packets, offset so the line is never empty.
    for k, delay in enumerate((0.0, CYCLE / 3, 2 * CYCLE / 3)):
        for i in range(len(STAGES) - 1):
            begin = (i * per + delay) % CYCLE
            out.append(
                f'<g opacity="0">'
                f'<animate attributeName="opacity" values="0;1;1;0" '
                f'dur="{per:.3f}s" keyTimes="0;0.12;0.88;1" '
                f'begin="{begin:.3f}s" repeatCount="indefinite"/>'
                f'<polygon points="0,-6 6,0 0,6 -6,0" fill="{t["glow"]}">'
                f'<animateMotion dur="{per:.3f}s" begin="{begin:.3f}s" '
                f'repeatCount="indefinite" '
                f'keyPoints="0;1" keyTimes="0;1" calcMode="spline" '
                f'keySplines="0.45 0 0.55 1">'
                f'<mpath href="#{uid}r{i}"/></animateMotion></polygon></g>')

    out.append("</svg>")
    return "\n".join(out)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for theme in THEMES:
        p = OUT / f"pipeline-iso-{theme}.svg"
        p.write_text(build(theme), encoding="utf-8")
        print(f"  wrote {p.name}  {p.stat().st_size/1024:.1f} KB")
    print(f"\n  {len(STAGES)} stages, {CYCLE:.0f}s loop")


if __name__ == "__main__":
    main()
