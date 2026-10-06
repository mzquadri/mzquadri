#!/usr/bin/env python3
"""Generate the social preview cards for the repositories worth sharing.

GitHub shows a repository's social preview whenever its link is posted to
LinkedIn, Slack or X. Unset, it falls back to a grey placeholder with an
octocat, which is the same card every unconfigured repository on the platform
gets. These put the repository's name and the one number it earned on it
instead.

Output is 1280x640, the size GitHub asks for. The cards are SVG here and
rasterised by scripts/render_social_cards.sh, because the upload form takes
PNG, JPG or GIF and will not take SVG.

The headline on each card is the same figure claims.yml verifies, so a card
cannot quietly disagree with the profile.

    python scripts/make_social_cards.py
"""

from __future__ import annotations

import math
from pathlib import Path

WIDTH, HEIGHT = 1280, 640
OUT = Path(__file__).resolve().parent.parent / "assets" / "social"

BG = "#1e293b"
PANEL = "#172033"
BORDER = "#334155"
NAME = "#f1f5f9"
MUTED = "#94a3b8"
DIM = "#64748b"
ACCENT = "#5eead4"
VIOLET = "#c4b5fd"

CARDS = [
    {
        "slug": "ml_surrogates_for_agent_based_transport_models",
        "title": "ml_surrogates",
        "subtitle": "Uncertainty quantification for a GNN transport surrogate",
        "stat": "−90.5%",
        "stat_label": "calibration error, after temperature scaling",
        "foot": "M.Sc. thesis · six UQ methods · TUM",
    },
    {
        "slug": "mcp-policy-gateway",
        "title": "mcp-policy-gateway",
        "subtitle": "Runtime policy enforcement for MCP tool calls",
        "stat": "96.2%",
        "stat_label": "of an adversarial corpus caught, at 9.5% false positives",
        "foot": "keyword baseline 38.5% · three scored misses kept in the corpus",
    },
    {
        "slug": "insureassist-rag-mlops",
        "title": "insureassist-rag-mlops",
        "subtitle": "Retrieval over policy documents, with citations that resolve",
        "stat": "0.556",
        "stat_label": "top-document accuracy, 3.3× the 0.167 starting point",
        "foot": "hybrid BM25 + dense · hit rate@5 did not improve, and it says so",
    },
    {
        "slug": "drift-aware-ml-platform",
        "title": "drift-aware-ml-platform",
        "subtitle": "Forecasting that watches its own target for drift",
        "stat": "0.679",
        "stat_label": "target drift while only 9% of input features move",
        "foot": "a feature-only monitor would miss a 63% rise in demand",
    },
    {
        "slug": "munich-accident-forecasting",
        "title": "munich-accident-forecasting",
        "subtitle": "Munich road accident forecasting behind a FastAPI service",
        "stat": "1e-9",
        "stat_label": "tolerance CI reproduces the reference run to, or fails",
        "foot": "temporal split · baseline comparison · open data",
    },
    {
        "slug": "UQ-Hydrology-Seminar-TUM",
        "title": "UQ-Hydrology-Seminar-TUM",
        "subtitle": "Where a calibrated rainfall-runoff model's skill actually goes",
        "stat": "0.148",
        "stat_label": "NSE lost to observation error, not to rainfall noise",
        "foot": "recalibration recovers 5.76% of it",
    },
]


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def curve() -> tuple[str, str]:
    """The same motif as the profile hero, as a quiet background mark."""
    x0, x1, y0, y1 = 700, 1240, 300, 560
    n = 64
    pts = []
    for i in range(n + 1):
        t = i / n
        v = 0.55 - 0.32 * t + 0.16 * math.sin(t * math.pi * 2.2 + 0.5)
        pts.append((x0 + t * (x1 - x0), y0 + v * (y1 - y0)))
    line = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)

    up, lo = [], []
    for i, (x, y) in enumerate(pts):
        s = 6 + 26 * ((i / n) ** 1.7)
        up.append((x, y - s))
        lo.append((x, y + s))
    band = (
        "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in up)
        + " L " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in reversed(lo)) + " Z"
    )
    return line, band


def title_size(title: str) -> float:
    if len(title) <= 18:
        return 58
    if len(title) <= 26:
        return 48
    return 40


def render(card: dict) -> str:
    line, band = curve()
    ts = title_size(card["title"])
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{esc(card['title'])} — {esc(card['subtitle'])}">
  <rect width="{WIDTH}" height="{HEIGHT}" fill="{BG}"/>
  <rect x="24" y="24" width="{WIDTH - 48}" height="{HEIGHT - 48}" rx="18" fill="{PANEL}" stroke="{BORDER}" stroke-width="1.5"/>

  <!-- Identity motif -->
  <g opacity="0.5">
    <path d="{band}" fill="{ACCENT}" opacity="0.13"/>
    <path d="{line}" fill="none" stroke="{ACCENT}" stroke-width="2.4" stroke-linecap="round" opacity="0.6"/>
  </g>

  <g font-family="Segoe UI, Helvetica, Arial, sans-serif">
    <text x="76" y="118" font-size="17" letter-spacing="2.6" fill="{DIM}">GITHUB.COM / MZQUADRI</text>

    <text x="76" y="{118 + 76}" font-size="{ts}" font-weight="700" fill="{NAME}">{esc(card['title'])}</text>
    <text x="76" y="{118 + 76 + 42}" font-size="21" fill="{MUTED}">{esc(card['subtitle'])}</text>

    <rect x="76" y="{118 + 76 + 70}" width="72" height="4" rx="2" fill="{ACCENT}"/>

    <text x="76" y="{118 + 76 + 70 + 108}" font-size="96" font-weight="700" fill="{ACCENT}">{esc(card['stat'])}</text>
    <text x="76" y="{118 + 76 + 70 + 150}" font-size="21" fill="{NAME}">{esc(card['stat_label'])}</text>

    <text x="76" y="{HEIGHT - 76}" font-size="18" fill="{DIM}">{esc(card['foot'])}</text>
    <text x="{WIDTH - 76}" y="{HEIGHT - 76}" font-size="18" fill="{VIOLET}" text-anchor="end">mzquadri.de</text>
  </g>
</svg>
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for card in CARDS:
        p = OUT / f"{card['slug']}.svg"
        p.write_text(render(card), encoding="utf-8")
        print(f"wrote {p.relative_to(OUT.parent.parent)}")
    print(f"\n{len(CARDS)} cards. Rasterise with scripts/render_social_cards.sh")


if __name__ == "__main__":
    main()
