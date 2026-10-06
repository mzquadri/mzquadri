#!/usr/bin/env python3
"""Check that every third-party image in README.md still serves.

Two of the widgets this profile was first built with went dead at the same time
— github-profile-trophy and github-readme-activity-graph both started answering
402 DEPLOYMENT_DISABLED when their hosting lapsed. Nothing about the README
changed, so the only way to notice was to look. This looks.

Prints a report and exits non-zero if anything is broken, which the workflow
turns into an issue.

    python scripts/check_widgets.py
"""

from __future__ import annotations

import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
TIMEOUT = 30

# Hosts we do not control. Local assets/ paths are covered by the repo itself.
SKIP_HOSTS = {"raw.githubusercontent.com", "github.com"}


def urls() -> list[str]:
    text = README.read_text(encoding="utf-8")
    found = re.findall(r'(?:src|srcset)="(https://[^"]+)"', text)
    out, seen = [], set()
    for u in found:
        host = urlsplit(u).netloc
        if host in SKIP_HOSTS or u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def probe(url: str) -> tuple[bool, str]:
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", "mzquadri-profile-widget-healthcheck")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read(4096)
            if resp.status != 200:
                return False, f"HTTP {resp.status}"
            if not body.strip():
                return False, "empty response"
            return True, f"HTTP 200, {len(body)}+ bytes"
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read(200).decode("utf-8", errors="replace").strip().replace("\n", " ")
        except Exception:  # noqa: BLE001
            pass
        return False, f"HTTP {exc.code}{f' — {detail}' if detail else ''}"
    except urllib.error.URLError as exc:
        return False, f"unreachable: {exc.reason}"
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


def main() -> int:
    targets = urls()
    if not targets:
        print("no third-party images found in README.md")
        return 0

    broken = []
    for url in targets:
        ok, detail = probe(url)
        host = urlsplit(url).netloc
        print(f"  {'ok  ' if ok else 'FAIL'}  {host:38s} {detail}")
        if not ok:
            broken.append((url, detail))

    print(f"\n{len(targets) - len(broken)}/{len(targets)} third-party images are serving.")

    if broken:
        lines = [
            "The following images embedded in the profile README are not serving.",
            "Visitors are seeing broken images until these are swapped or removed.",
            "",
        ]
        for url, detail in broken:
            lines.append(f"- **{urlsplit(url).netloc}** — {detail}")
            lines.append(f"  <br><sub>`{url}`</sub>")
        Path("widget-report.md").write_text("\n".join(lines), encoding="utf-8")
        print("\nwrote widget-report.md", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
