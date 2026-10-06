#!/usr/bin/env python3
"""Generate the animated profile hero banner in a light and a dark variant.

The two files differ only by palette, so they are emitted from one source to
keep them from drifting apart. The drawing is a calibrated prediction band:
a point forecast with an uncertainty envelope that tightens and relaxes, which
is the subject the rest of the profile is about.

Animation is declarative SMIL only. GitHub serves these through its image
proxy, where <script> is stripped but <animate> still runs.

    python scripts/make_hero.py
"""

from __future__ import annotations

import math
from pathlib import Path

WIDTH, HEIGHT = 1200, 280
ASSETS = Path(__file__).resolve().parent.parent / "assets"

# Plot area on the right-hand side of the banner.
PLOT_X0, PLOT_X1 = 596, 1152
PLOT_Y0, PLOT_Y1 = 60, 232

NAME = "MOHD ZAMIN QUADRI"
ROLE = "AI / ML Engineer"
LINE2 = "Uncertainty quantification · Retrieval · MLOps"
LINE3 = "M.Sc. Mathematics in Science and Engineering, TUM · Munich"

THEMES = {
    "light": {
        "bg": "#f8fafc",
        "panel": "#f1f5f9",
        "border": "#e2e8f0",
        "grid": "#e2e8f0",
        "name": "#0f172a",
        "role": "#334155",
        "muted": "#64748b",
        "curve": "#0f6b5c",
        "band": "#0f6b5c",
        "band_opacity": "0.16",
        "accent": "#5b4b9e",
        "truth": "#9d1f41",
    },
    "dark": {
        "bg": "#1e293b",
        "panel": "#172033",
        "border": "#334155",
        "grid": "#334155",
        "name": "#f1f5f9",
        "role": "#e2e8f0",
        "muted": "#94a3b8",
        "curve": "#5eead4",
        "band": "#5eead4",
        "band_opacity": "0.17",
        "accent": "#c4b5fd",
        "truth": "#fda4af",
    },
}

SAMPLES = 72


def _curve() -> list[tuple[float, float]]:
    """A deterministic, plausible-looking forecast curve."""
    pts = []
    for i in range(SAMPLES + 1):
        t = i / SAMPLES
        x = PLOT_X0 + t * (PLOT_X1 - PLOT_X0)
        # Gentle upward trend with two seasonal components.
        v = (
            0.52
            - 0.30 * t
            + 0.17 * math.sin(t * math.pi * 2.3 + 0.4)
            + 0.06 * math.sin(t * math.pi * 6.1 + 1.1)
        )
        y = PLOT_Y0 + v * (PLOT_Y1 - PLOT_Y0)
        pts.append((x, y))
    return pts


def _sigma(t: float) -> float:
    """Half-width of the interval, widening toward the forecast horizon."""
    return 7.0 + 30.0 * (t**1.7)


def _path(pts: list[tuple[float, float]]) -> str:
    head = f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"
    rest = " ".join(f"L {x:.1f} {y:.1f}" for x, y in pts[1:])
    return f"{head} {rest}"


def _band(pts: list[tuple[float, float]], k: float = 1.0) -> str:
    """Envelope at k times the nominal interval width.

    Two of these at different k animate into each other to show the interval
    tightening, which keeps the envelope wrapped around the curve. Scaling a
    single path instead would scale about the SVG origin and slide it off-plot.
    """
    upper, lower = [], []
    for i, (x, y) in enumerate(pts):
        s = _sigma(i / SAMPLES) * k
        upper.append((x, y - s))
        lower.append((x, y + s))
    d = _path(upper)
    d += " " + " ".join(f"L {x:.1f} {y:.1f}" for x, y in reversed(lower))
    return d + " Z"


def _observed(pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Scattered observations that mostly sit inside the band."""
    out = []
    for i in range(4, SAMPLES - 6, 6):
        x, y = pts[i]
        t = i / SAMPLES
        # Deterministic pseudo-jitter, scaled to the local interval width.
        j = math.sin(i * 12.9898) * 43758.5453
        j = (j - math.floor(j)) * 2 - 1
        out.append((x, y + j * _sigma(t) * 0.78))
    return out


def render(theme_name: str) -> str:
    c = THEMES[theme_name]
    pts = _curve()
    band_wide = _band(pts, 1.0)
    band_tight = _band(pts, 0.40)
    curve_d = _path(pts)

    grid = []
    for k in range(1, 4):
        y = PLOT_Y0 + k * (PLOT_Y1 - PLOT_Y0) / 4
        grid.append(
            f'<line x1="{PLOT_X0}" y1="{y:.1f}" x2="{PLOT_X1}" y2="{y:.1f}" '
            f'stroke="{c["grid"]}" stroke-width="1" stroke-dasharray="2 6"/>'
        )
    for k in range(1, 6):
        x = PLOT_X0 + k * (PLOT_X1 - PLOT_X0) / 6
        grid.append(
            f'<line x1="{x:.1f}" y1="{PLOT_Y0}" x2="{x:.1f}" y2="{PLOT_Y1}" '
            f'stroke="{c["grid"]}" stroke-width="1" stroke-dasharray="2 6"/>'
        )

    # Static attributes carry the *final* state everywhere below, so the banner
    # still reads correctly if SMIL never runs (reduced-motion contexts, feed
    # readers, static rasterisers). The animation only supplies the way in.
    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="{c["truth"]}" opacity="0.85">'
        f'<animate attributeName="opacity" from="0" to="0.85" dur="0.4s" '
        f'begin="{0.7 + i * 0.07:.2f}s" fill="freeze"/></circle>'
        for i, (x, y) in enumerate(_observed(pts))
    )

    curve_len = 2200  # generous over-estimate; dash just needs to exceed length

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{NAME} — {ROLE}. {LINE2}. {LINE3}">
  <title>{NAME} — {ROLE}</title>
  <defs>
    <clipPath id="plot">
      <rect x="{PLOT_X0}" y="{PLOT_Y0}" width="{PLOT_X1 - PLOT_X0}" height="{PLOT_Y1 - PLOT_Y0}"/>
    </clipPath>
    <linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{c["accent"]}" stop-opacity="0"/>
      <stop offset="50%" stop-color="{c["accent"]}" stop-opacity="0.55"/>
      <stop offset="100%" stop-color="{c["accent"]}" stop-opacity="0"/>
    </linearGradient>
  </defs>

  <rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="14"
        fill="{c["bg"]}" stroke="{c["border"]}" stroke-width="1"/>

  <!-- Identity -->
  <g font-family="Segoe UI, Helvetica, Arial, sans-serif" opacity="1">
    <animate attributeName="opacity" from="0" to="1" dur="0.7s" begin="0.1s" fill="freeze"/>
    <text x="52" y="104" font-size="34" font-weight="700" letter-spacing="2.0"
          fill="{c["name"]}">{NAME}</text>
    <text x="52" y="140" font-size="18" font-weight="600" letter-spacing="0.4"
          fill="{c["role"]}">{ROLE}</text>
    <text x="52" y="172" font-size="14.5" fill="{c["muted"]}">{LINE2}</text>
    <text x="52" y="196" font-size="13" fill="{c["muted"]}">{LINE3}</text>
    <rect x="52" y="214" width="58" height="3" rx="1.5" fill="{c["curve"]}"/>
  </g>

  <!-- Prediction panel -->
  <g>
    <rect x="{PLOT_X0 - 16}" y="{PLOT_Y0 - 26}" width="{PLOT_X1 - PLOT_X0 + 32}"
          height="{PLOT_Y1 - PLOT_Y0 + 48}" rx="10" fill="{c["panel"]}"
          stroke="{c["border"]}" stroke-width="1"/>
    <text x="{PLOT_X0 - 2}" y="{PLOT_Y0 - 9}" font-size="11.5" letter-spacing="1.3"
          font-family="Segoe UI, Helvetica, Arial, sans-serif" fill="{c["muted"]}">
      PREDICTION WITH CALIBRATED INTERVAL
    </text>
    {"".join(grid)}

    <g clip-path="url(#plot)">
      <!-- Interval, tightening and relaxing around the mean path -->
      <path d="{band_wide}" fill="{c["band"]}" opacity="{c["band_opacity"]}">
        <animate attributeName="opacity" from="0" to="{c["band_opacity"]}"
                 dur="0.9s" begin="0.35s" fill="freeze"/>
        <animate attributeName="d" dur="7s" begin="1.4s" repeatCount="indefinite"
                 calcMode="spline" keyTimes="0;0.5;1"
                 keySplines="0.4 0 0.2 1;0.4 0 0.2 1"
                 values="{band_wide};{band_tight};{band_wide}"/>
      </path>

      <path d="{curve_d}" fill="none" stroke="{c["curve"]}" stroke-width="2.4"
            stroke-linecap="round" stroke-dasharray="{curve_len}" stroke-dashoffset="0">
        <animate attributeName="stroke-dashoffset" from="{curve_len}" to="0"
                 dur="1.8s" begin="0.25s" fill="freeze"/>
      </path>

      {dots}

      <!-- Travelling evaluation marker -->
      <circle r="4.4" fill="{c["curve"]}" opacity="1" cx="{pts[0][0]:.1f}" cy="{pts[0][1]:.1f}">
        <animate attributeName="opacity" from="0" to="1" dur="0.3s" begin="2.0s" fill="freeze"/>
        <animateMotion dur="7s" begin="2.0s" repeatCount="indefinite" path="{curve_d}"/>
      </circle>

      <!-- Sweep. Purely decorative motion, so it stays hidden unless the
           animation actually runs; otherwise it parks as a static smear. -->
      <rect x="{PLOT_X0}" y="{PLOT_Y0}" width="90" height="{PLOT_Y1 - PLOT_Y0}"
            fill="url(#sweep)" opacity="0">
        <animate attributeName="opacity" from="0" to="1" dur="0.01s"
                 begin="2.0s" fill="freeze"/>
        <animateTransform attributeName="transform" type="translate"
          values="-110 0; {PLOT_X1 - PLOT_X0 + 20} 0" dur="7s" begin="2.0s"
          repeatCount="indefinite"/>
      </rect>
    </g>

    <line x1="{PLOT_X0}" y1="{PLOT_Y1}" x2="{PLOT_X1}" y2="{PLOT_Y1}"
          stroke="{c["border"]}" stroke-width="1.5"/>
  </g>
</svg>
"""


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    for name in THEMES:
        out = ASSETS / f"hero-{name}.svg"
        out.write_text(render(name), encoding="utf-8")
        print(f"wrote {out.relative_to(ASSETS.parent)} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
