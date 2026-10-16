#!/usr/bin/env python3
"""Three animated result charts for the profile README.

SMIL again, for the same reason as the pipeline: GitHub runs <animate> but not
<script>, and a 6 KB SVG beats a 2 MB video for something this simple.

Every number here is verified. Where a result is mixed, the chart says so on its
face rather than showing only the half that flatters — see the retrieval chart,
where fusion wins on MRR and loses on hit rate.

    python scripts/make_result_charts.py
"""

from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets"

W, H = 880, 300
PAD_L, PAD_R, PAD_T, PAD_B = 210, 92, 62, 46

THEMES = {
    "light": dict(bg="#FBFAF7", ink="#14181D", muted="#5A6472",
                  track="#EFEDE8", hair="#E2DFD8"),
    "dark":  dict(bg="#0E1116", ink="#E8EDF2", muted="#8B97A6",
                  track="#1B2430", hair="#263040"),
}
TEAL, ORANGE, PURPLE, MAGENTA = "#00897B", "#C2410C", "#6D28D9", "#BE185D"

CHARTS = {
    "chart-calibration": dict(
        title="Calibration error, before and after one scalar",
        sub="MC Dropout sigma scaling, protocol graph20_80_v1. Lower is better.",
        unit="expected calibration error",
        note="verify_headline_results.py replays this: 0.26874 → 0.04783",
        rows=[("before scaling", 0.26874, ORANGE, "0.269"),
              ("after sigma × 2.70", 0.04783, TEAL, "0.048")],
        vmax=0.30,
    ),
    "chart-retrieval": dict(
        title="Hybrid retrieval beats either half — on MRR",
        sub="NFIP policy benchmark, 18 answerable test questions.",
        unit="mean reciprocal rank",
        note="hit rate@5 did not improve: BM25 alone reaches 0.611 against 0.556",
        rows=[("BM25 + dense, fused", 0.420, TEAL, "0.420"),
              ("BM25 only", 0.3657, ORANGE, "0.366"),
              ("dense only", 0.3646, PURPLE, "0.365")],
        vmax=0.50,
    ),
    "chart-gateway": dict(
        title="Adversarial tool calls caught",
        sub="47-case corpus: 26 attacks, 21 benign, 10 attack classes.",
        unit="share of attacks caught",
        note="at 9.5% false positives; three scored misses are kept in the corpus",
        rows=[("policy gateway", 0.962, TEAL, "96.2%"),
              ("keyword baseline", 0.385, ORANGE, "38.5%")],
        vmax=1.0,
    ),
}


def build(key: str, spec: dict, theme: str) -> str:
    t = THEMES[theme]
    uid = f"{key}{theme}"
    rows = spec["rows"]
    n = len(rows)

    plot_w = W - PAD_L - PAD_R
    gap = 20
    bar_h = min(38, (H - PAD_T - PAD_B - gap * (n - 1)) / n)
    total = bar_h * n + gap * (n - 1)
    y0 = PAD_T + (H - PAD_T - PAD_B - total) / 2

    o = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" aria-label="{spec["title"]}">',
        f'<rect width="{W}" height="{H}" fill="{t["bg"]}"/>',
        f'<text x="{PAD_L - 150}" y="34" font-family="Segoe UI, Helvetica, Arial, '
        f'sans-serif" font-size="21" font-weight="700" fill="{t["ink"]}">'
        f'{spec["title"]}</text>',
        f'<text x="{PAD_L - 150}" y="56" font-family="Segoe UI, Helvetica, Arial, '
        f'sans-serif" font-size="13.5" fill="{t["muted"]}">{spec["sub"]}</text>',
    ]

    for i, (lab, val, col, shown) in enumerate(rows):
        y = y0 + i * (bar_h + gap)
        w = plot_w * (val / spec["vmax"])
        begin = 0.25 + i * 0.22

        o.append(
            f'<text x="{PAD_L - 16}" y="{y + bar_h/2 + 5:.1f}" text-anchor="end" '
            f'font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="15" '
            f'fill="{t["ink"]}">{lab}</text>')
        o.append(
            f'<rect x="{PAD_L}" y="{y:.1f}" width="{plot_w}" height="{bar_h:.1f}" '
            f'rx="4" fill="{t["track"]}"/>')
        # The bar grows once, then holds. A looping grow/shrink would read as
        # the value changing, which it does not.
        o.append(
            f'<rect x="{PAD_L}" y="{y:.1f}" width="0" height="{bar_h:.1f}" rx="4" '
            f'fill="{col}">'
            f'<animate attributeName="width" from="0" to="{w:.1f}" dur="1.05s" '
            f'begin="{begin:.2f}s" fill="freeze" '
            f'calcMode="spline" keyTimes="0;1" keySplines="0.22 0.61 0.36 1"/>'
            f'</rect>')
        o.append(
            f'<text x="{PAD_L + w + 12:.1f}" y="{y + bar_h/2 + 6:.1f}" '
            f'font-family="Cascadia Mono, Consolas, monospace" font-size="17" '
            f'font-weight="700" fill="{col}" opacity="0">{shown}'
            f'<animate attributeName="opacity" from="0" to="1" dur="0.4s" '
            f'begin="{begin + 0.95:.2f}s" fill="freeze"/></text>')

    o.append(
        f'<line x1="{PAD_L}" y1="{H - PAD_B + 6}" x2="{W - PAD_R}" '
        f'y2="{H - PAD_B + 6}" stroke="{t["hair"]}" stroke-width="1"/>')
    o.append(
        f'<text x="{PAD_L}" y="{H - PAD_B + 26}" font-family="Segoe UI, Helvetica, '
        f'Arial, sans-serif" font-size="12.5" fill="{t["muted"]}">'
        f'{spec["unit"]} →</text>')
    o.append(
        f'<text x="{W - PAD_R}" y="{H - PAD_B + 26}" text-anchor="end" '
        f'font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="12.5" '
        f'fill="{t["muted"]}">{spec["note"]}</text>')
    o.append("</svg>")
    return "\n".join(o)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for key, spec in CHARTS.items():
        for theme in THEMES:
            p = OUT / f"{key}-{theme}.svg"
            p.write_text(build(key, spec, theme), encoding="utf-8")
            print(f"  wrote {p.name:<30} {p.stat().st_size/1024:.1f} KB")


if __name__ == "__main__":
    main()
