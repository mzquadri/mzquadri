#!/usr/bin/env bash
# Rasterise the social preview cards.
#
# GitHub's social preview upload takes PNG, JPG or GIF and will not take SVG,
# so the cards written by make_social_cards.py have to be rendered before they
# can be used. Any Chromium will do it; there is no need for a toolchain.
#
#   bash scripts/render_social_cards.sh
#
# Then, per repository: Settings -> General -> Social preview -> Edit -> Upload,
# and pick the matching PNG in assets/social/. That page has no API, so this is
# the one step that stays manual.

set -euo pipefail

cd "$(dirname "$0")/.."
out="assets/social"

if [ ! -d "$out" ]; then
  echo "no $out — run: python scripts/make_social_cards.py" >&2
  exit 1
fi

browser=""
for candidate in \
  "${CHROME:-}" \
  "$(command -v chromium 2>/dev/null || true)" \
  "$(command -v chromium-browser 2>/dev/null || true)" \
  "$(command -v google-chrome 2>/dev/null || true)" \
  "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" \
  "/c/Program Files/Google/Chrome/Application/chrome.exe" \
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
do
  if [ -n "$candidate" ] && [ -x "$candidate" ]; then browser="$candidate"; break; fi
done

if [ -z "$browser" ]; then
  echo "no Chromium found; set CHROME=/path/to/chrome and retry" >&2
  exit 1
fi

# Git Bash hands Windows binaries Windows paths; cygpath is absent elsewhere.
topath() { if command -v cygpath >/dev/null 2>&1; then cygpath -w "$1"; else echo "$1"; fi; }

count=0
for svg in "$out"/*.svg; do
  png="${svg%.svg}.png"
  "$browser" --headless --disable-gpu --hide-scrollbars \
    --force-device-scale-factor=1 --window-size=1280,640 \
    --screenshot="$(topath "$PWD/$png")" "$(topath "$PWD/$svg")" 2>/dev/null
  printf '  %-56s %s bytes\n' "$(basename "$png")" "$(wc -c < "$png")"
  count=$((count + 1))
done

echo "$count card(s) rendered into $out"
