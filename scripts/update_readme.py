#!/usr/bin/env python3
"""Rewrite the generated blocks of README.md from the GitHub API.

Two blocks, each delimited by markers so the hand-written prose around them is
never touched:

  AUTO:now    the few repositories last pushed to, with how long ago
  AUTO:index  every public repository, language and one-line description

The "currently working on" line is the section of a profile most likely to go
stale, so this derives it from push timestamps instead of asking anyone to
remember to edit it.

    python scripts/update_readme.py            # rewrite the blocks
    python scripts/update_readme.py --check    # non-zero if they are out of date
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
OWNER = os.environ.get("PROFILE_OWNER", "mzquadri")
API = "https://api.github.com"

NOW_COUNT = 3
# Teaching exercises stay in the index but should not be presented as current work.
NOW_EXCLUDE = {OWNER, "git-python-basics", "complete-python-warmup", "snake-water-gun"}


def api(path: str) -> list | dict:
    url = f"{API}{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "mzquadri-profile-readme-updater")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def repos() -> list[dict]:
    out: list[dict] = []
    page = 1
    while True:
        batch = api(f"/users/{OWNER}/repos?per_page=100&page={page}&sort=pushed")
        if not isinstance(batch, list) or not batch:
            break
        out.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return [r for r in out if not r.get("private")]


def ago(stamp: str, now: datetime) -> str:
    when = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    days = (now - when).days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 14:
        return f"{days} days ago"
    if days < 60:
        return f"{days // 7} weeks ago"
    if days < 365:
        return f"{days // 30} months ago"
    years = days // 365
    return "a year ago" if years == 1 else f"{years} years ago"


def block_now(rs: list[dict], now: datetime) -> str:
    live = [r for r in rs if not r["fork"] and not r["archived"] and r["name"] not in NOW_EXCLUDE]
    live.sort(key=lambda r: r["pushed_at"], reverse=True)
    picks = live[:NOW_COUNT]
    if not picks:
        return "_Nothing pushed recently._"

    lines = []
    for r in picks:
        desc = (r.get("description") or "").strip()
        # One clause is enough here; the index below carries the full sentence.
        short = desc.split(". ")[0].rstrip(".")
        if len(short) > 104:
            short = short[:101].rsplit(" ", 1)[0] + "…"
        lang = r.get("language")
        tail = f" · {lang}" if lang else ""
        lines.append(
            f"- **[{r['name']}](https://github.com/{OWNER}/{r['name']})** "
            f"— {short} <sub>`{ago(r['pushed_at'], now)}`{tail}</sub>"
        )
    return "\n".join(lines)


def block_index(rs: list[dict], now: datetime) -> str:
    live = [r for r in rs if r["name"] != OWNER]
    live.sort(key=lambda r: r["pushed_at"], reverse=True)

    lines = [
        "| Repository | Language | Last pushed | |",
        "|---|---|---|---|",
    ]
    for r in live:
        desc = (r.get("description") or "—").strip().replace("|", "\\|")
        if len(desc) > 150:
            desc = desc[:147].rsplit(" ", 1)[0] + "…"
        lang = r.get("language") or "—"
        tags = []
        if r["fork"]:
            tags.append("fork")
        if r["archived"]:
            tags.append("archived")
        name = f"[`{r['name']}`](https://github.com/{OWNER}/{r['name']})"
        if tags:
            name += f" <sub>{' · '.join(tags)}</sub>"
        lines.append(f"| {name} | {lang} | {ago(r['pushed_at'], now)} | {desc} |")

    lines.append("")
    lines.append(
        f"<sub>{len(live)} public repositories, including the learning exercises. "
        "A list that dropped them would be saying something else.</sub>"
    )
    return "\n".join(lines)


def splice(text: str, name: str, body: str) -> str:
    start, end = f"<!-- AUTO:{name}:start -->", f"<!-- AUTO:{name}:end -->"
    if start not in text or end not in text:
        raise SystemExit(f"markers for '{name}' not found in README.md")
    return re.sub(
        re.escape(start) + r".*?" + re.escape(end),
        lambda _: f"{start}\n{body}\n{end}",
        text,
        flags=re.DOTALL,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit non-zero if out of date")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    try:
        rs = repos()
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        print(f"could not reach the GitHub API: {exc}", file=sys.stderr)
        return 2

    before = README.read_text(encoding="utf-8")
    after = splice(before, "now", block_now(rs, now))
    after = splice(after, "index", block_index(rs, now))

    if args.check:
        if before != after:
            print("README.md generated blocks are out of date", file=sys.stderr)
            return 1
        print("README.md generated blocks are current")
        return 0

    if before == after:
        print("no change")
        return 0

    README.write_text(after, encoding="utf-8")
    print(f"updated README.md from {len(rs)} repositories")
    return 0


if __name__ == "__main__":
    sys.exit(main())
