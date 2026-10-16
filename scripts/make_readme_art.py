#!/usr/bin/env python3
"""Generate the animated pipeline and the six project cards for the profile.

Two kinds of art come out of here:

  assets/pipeline-{light,dark}.svg      data -> model -> uncertainty -> service
  assets/cards/<slug>-{light,dark}.svg  one card per pinned repository

Both are SMIL only. GitHub serves README images through its camo proxy, which
strips <script> but leaves <animate> and <animateTransform> alone, so the motion
has to be declarative. Nothing here is fetched from a third-party widget service:
two of those went dead on this profile once already, and an asset that lives in
the repository cannot.

Light and dark come out of one source so they cannot drift apart. The README
picks between them with <picture> and prefers-color-scheme.

    python scripts/make_readme_art.py
"""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
CARDS_DIR = ASSETS / "cards"

FONT = "Segoe UI, Helvetica, Arial, sans-serif"
MONO = "Cascadia Mono, SFMono-Regular, Consolas, monospace"

THEMES = {
    "light": {
        "bg": "#f8fafc", "bg2": "#eef2f7", "panel": "#ffffff", "border": "#dde3ea",
        "ink": "#0f172a", "muted": "#64748b", "dim": "#94a3b8",
        "accent": "#0d9488", "accent_soft": "#ccfbf1", "violet": "#7c3aed",
        "grid": "#e2e8f0", "glow": "#2dd4bf",
    },
    "dark": {
        "bg": "#0b1220", "bg2": "#111a2b", "panel": "#131c2e", "border": "#263349",
        "ink": "#e8eef7", "muted": "#9aa8bd", "dim": "#64748b",
        "accent": "#5eead4", "accent_soft": "#10342f", "violet": "#c4b5fd",
        "grid": "#1d293d", "glow": "#5eead4",
    },
}

# --------------------------------------------------------------------- pipeline

STAGES = [
    ("Data", "scenarios, graphs,\ndocuments"),
    ("Model", "train, compare,\npick one"),
    ("Uncertainty", "calibrate, cover,\nabstain"),
    ("Service", "ship it, watch it,\nretrain it"),
]

PIPE_W, PIPE_H = 980, 240
CYCLE = 8.0  # seconds for one full pass


def defs(t: dict, uid: str, line_x0: float = 0, line_x1: float = 100) -> str:
    """Shared gradient, glow filter and dot grid.

    line-* is userSpaceOnUse on purpose. A gradient defaults to
    objectBoundingBox, and the two things it paints here - the pipeline rail and
    the card's top hairline - are both perfectly horizontal, so their bounding
    box has zero height and the gradient degenerates to nothing. It rendered as
    flat grey until this was pinned to user space with explicit endpoints.
    """
    return f"""<defs>
  <linearGradient id="bg-{uid}" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{t['bg']}"/><stop offset="1" stop-color="{t['bg2']}"/>
  </linearGradient>
  <linearGradient id="line-{uid}" gradientUnits="userSpaceOnUse"
                  x1="{line_x0}" y1="0" x2="{line_x1}" y2="0">
    <stop offset="0" stop-color="{t['accent']}"/><stop offset="1" stop-color="{t['violet']}"/>
  </linearGradient>
  <filter id="glow-{uid}" x="-60%" y="-60%" width="220%" height="220%">
    <feGaussianBlur stdDeviation="5" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <pattern id="dots-{uid}" width="22" height="22" patternUnits="userSpaceOnUse">
    <circle cx="1.5" cy="1.5" r="1.1" fill="{t['grid']}"/>
  </pattern>
</defs>"""


def pipeline(theme: str) -> str:
    t = THEMES[theme]
    uid = theme
    y = 104
    xs = [128, 364, 606, 848]

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{PIPE_W}" height="{PIPE_H}" '
        f'viewBox="0 0 {PIPE_W} {PIPE_H}" font-family="{FONT}" role="img" '
        f'aria-label="How the work is shaped: data, model, uncertainty, service.">',
        defs(t, uid, xs[0], xs[-1]),
        f'<rect width="{PIPE_W}" height="{PIPE_H}" rx="18" fill="url(#bg-{uid})"/>',
        f'<rect width="{PIPE_W}" height="{PIPE_H}" rx="18" fill="url(#dots-{uid})" opacity="0.55"/>',
        f'<rect x="0.5" y="0.5" width="{PIPE_W-1}" height="{PIPE_H-1}" rx="18" '
        f'fill="none" stroke="{t["border"]}"/>',
    ]

    # The rail, drawn once on load.
    rail = f"M{xs[0]} {y} H{xs[-1]}"
    out.append(
        f'<path d="{rail}" fill="none" stroke="{t["border"]}" stroke-width="3" stroke-linecap="round"/>'
    )
    out.append(
        f'<path d="{rail}" fill="none" stroke="url(#line-{uid})" stroke-width="3" '
        f'stroke-linecap="round" stroke-dasharray="{xs[-1]-xs[0]}" '
        f'stroke-dashoffset="{xs[-1]-xs[0]}">'
        f'<animate attributeName="stroke-dashoffset" from="{xs[-1]-xs[0]}" to="0" '
        f'dur="1.6s" fill="freeze"/></path>'
    )

    # A packet running the rail, once per cycle.
    out.append(
        f'<circle r="7" fill="{t["glow"]}" filter="url(#glow-{uid})" opacity="0">'
        f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.06;0.94;1" '
        f'dur="{CYCLE}s" begin="1.6s" repeatCount="indefinite"/>'
        f'<animate attributeName="cx" values="{xs[0]};{xs[-1]}" dur="{CYCLE}s" '
        f'begin="1.6s" repeatCount="indefinite" calcMode="spline" '
        f'keySplines="0.45 0 0.55 1"/>'
        f'<animate attributeName="cy" values="{y};{y}" dur="{CYCLE}s" begin="1.6s" '
        f'repeatCount="indefinite"/></circle>'
    )

    # Stage nodes. Each lights as the packet reaches it.
    for i, ((label, sub), x) in enumerate(zip(STAGES, xs)):
        at = 1.6 + CYCLE * (i / (len(STAGES) - 1)) * 0.94
        out.append(
            f'<circle cx="{x}" cy="{y}" r="30" fill="{t["panel"]}" stroke="{t["border"]}" stroke-width="2"/>'
            f'<circle cx="{x}" cy="{y}" r="30" fill="none" stroke="{t["accent"]}" stroke-width="2.5" opacity="0">'
            f'<animate attributeName="opacity" values="0;1;1;0.25" keyTimes="0;0.04;0.3;1" '
            f'dur="{CYCLE}s" begin="{at:.2f}s" repeatCount="indefinite"/>'
            f'<animate attributeName="r" values="30;36;30" keyTimes="0;0.06;0.2" '
            f'dur="{CYCLE}s" begin="{at:.2f}s" repeatCount="indefinite"/>'
            f'</circle>'
        )
        out.append(
            f'<text x="{x}" y="{y+6}" fill="{t["accent"]}" font-size="17" font-weight="700" '
            f'text-anchor="middle" font-family="{MONO}">{i+1:02d}</text>'
        )
        out.append(
            f'<text x="{x}" y="{y+62}" fill="{t["ink"]}" font-size="19" font-weight="600" '
            f'text-anchor="middle">{escape(label)}</text>'
        )
        for j, line in enumerate(sub.split("\n")):
            out.append(
                f'<text x="{x}" y="{y+86+j*19}" fill="{t["muted"]}" font-size="14.5" '
                f'text-anchor="middle">{escape(line)}</text>'
            )

    out.append(
        f'<text x="{PIPE_W//2}" y="34" fill="{t["dim"]}" font-size="14" text-anchor="middle" '
        f'letter-spacing="2.4">HOW THE WORK IS SHAPED</text>'
    )
    out.append("</svg>")
    return "\n".join(out)


# ------------------------------------------------------------------ repo cards

CARD_W, CARD_H = 560, 188

CARDS = [
    {
        "slug": "ml_surrogates_for_agent_based_transport_models",
        "name": "ml_surrogates",
        "line": "Uncertainty for a GNN traffic surrogate",
        "stat": "−82%",
        "stat_label": "calibration error, on the protocol that replays",
    },
    {
        "slug": "mcp-policy-gateway",
        "name": "mcp-policy-gateway",
        "line": "Policy enforcement for MCP tool calls",
        "stat": "96.2%",
        "stat_label": "of an adversarial corpus caught, 9.5% false positives",
    },
    {
        "slug": "insureassist-rag-mlops",
        "name": "insureassist-rag-mlops",
        "line": "Retrieval that cites exact character offsets",
        "stat": "0.420",
        "stat_label": "MRR, up from 0.365 for dense alone",
    },
    {
        "slug": "drift-aware-ml-platform",
        "name": "drift-aware-ml-platform",
        "line": "Forecasting that notices its own staleness",
        "stat": "0.679",
        "stat_label": "target drift while 9% of features move",
    },
    {
        "slug": "ai-engineering-portfolio",
        "name": "ai-engineering-portfolio",
        "line": "Architecture case studies, authorship per component",
        "stat": "22",
        "stat_label": "diagrams, each with what it does not claim",
    },
    {
        "slug": "munich-accident-forecasting",
        "name": "munich-accident-forecasting",
        "line": "Forecasts that argue against their own headline",
        "stat": "1e-9",
        "stat_label": "tolerance CI reproduces the run to, or fails",
    },
]


def wrap(text: str, width: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if len(trial) <= width:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def card(spec: dict, theme: str, index: int) -> str:
    t = THEMES[theme]
    uid = f"{theme}{index}"
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{CARD_H}" '
        f'viewBox="0 0 {CARD_W} {CARD_H}" font-family="{FONT}" role="img" '
        f'aria-label="{escape(spec["name"])}: {escape(spec["line"])}. '
        f'{escape(spec["stat"])} {escape(spec["stat_label"])}.">',
        defs(t, uid, 16, CARD_W - 16),
        f'<rect width="{CARD_W}" height="{CARD_H}" rx="16" fill="url(#bg-{uid})"/>',
        f'<rect width="{CARD_W}" height="{CARD_H}" rx="16" fill="url(#dots-{uid})" opacity="0.5"/>',
        f'<rect x="0.5" y="0.5" width="{CARD_W-1}" height="{CARD_H-1}" rx="16" '
        f'fill="none" stroke="{t["border"]}"/>',
    ]

    # A hairline that draws itself along the top edge, tinted accent to violet.
    out.append(
        f'<path d="M16 2 H{CARD_W-16}" stroke="url(#line-{uid})" stroke-width="3" '
        f'stroke-linecap="round" fill="none" stroke-dasharray="{CARD_W-32}" '
        f'stroke-dashoffset="{CARD_W-32}">'
        f'<animate attributeName="stroke-dashoffset" from="{CARD_W-32}" to="0" dur="1.1s" '
        f'begin="{0.12*index:.2f}s" fill="freeze"/></path>'
    )

    out.append(
        f'<text x="28" y="48" fill="{t["ink"]}" font-size="21" font-weight="700" '
        f'font-family="{MONO}" opacity="0">{escape(spec["name"])}'
        f'<animate attributeName="opacity" from="0" to="1" dur="0.5s" '
        f'begin="{0.12*index+0.25:.2f}s" fill="freeze"/></text>'
    )
    out.append(
        f'<text x="28" y="76" fill="{t["muted"]}" font-size="16" opacity="0">'
        f'{escape(spec["line"])}'
        f'<animate attributeName="opacity" from="0" to="1" dur="0.5s" '
        f'begin="{0.12*index+0.35:.2f}s" fill="freeze"/></text>'
    )

    # The number rises into place rather than just appearing.
    out.append(
        f'<g opacity="0" transform="translate(0,10)">'
        f'<animate attributeName="opacity" from="0" to="1" dur="0.55s" '
        f'begin="{0.12*index+0.5:.2f}s" fill="freeze"/>'
        f'<animateTransform attributeName="transform" type="translate" from="0 10" to="0 0" '
        f'dur="0.55s" begin="{0.12*index+0.5:.2f}s" fill="freeze"/>'
        f'<text x="28" y="136" fill="{t["accent"]}" font-size="46" font-weight="700" '
        f'font-family="{MONO}">{escape(spec["stat"])}</text>'
        f"</g>"
    )
    for j, line in enumerate(wrap(spec["stat_label"], 40)):
        out.append(
            f'<text x="28" y="{158+j*18}" fill="{t["dim"]}" font-size="13.5" opacity="0">'
            f"{escape(line)}"
            f'<animate attributeName="opacity" from="0" to="1" dur="0.5s" '
            f'begin="{0.12*index+0.6:.2f}s" fill="freeze"/></text>'
        )

    # A slow breathing dot, so a still card still reads as live.
    out.append(
        f'<circle cx="{CARD_W-34}" cy="44" r="6" fill="{t["glow"]}" filter="url(#glow-{uid})">'
        f'<animate attributeName="opacity" values="0.35;1;0.35" dur="3.2s" '
        f'begin="{0.3*index:.2f}s" repeatCount="indefinite"/></circle>'
    )

    out.append("</svg>")
    return "\n".join(out)


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    CARDS_DIR.mkdir(exist_ok=True)
    written = []

    for theme in THEMES:
        p = ASSETS / f"pipeline-{theme}.svg"
        p.write_text(pipeline(theme), encoding="utf-8")
        written.append(p)

    for i, spec in enumerate(CARDS):
        for theme in THEMES:
            p = CARDS_DIR / f"{spec['slug']}-{theme}.svg"
            p.write_text(card(spec, theme, i), encoding="utf-8")
            written.append(p)

    for p in written:
        print(f"  {p.relative_to(ROOT)}  {p.stat().st_size:,} bytes")
    print(f"\n  {len(written)} files")


if __name__ == "__main__":
    main()
