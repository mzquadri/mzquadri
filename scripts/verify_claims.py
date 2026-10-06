#!/usr/bin/env python3
"""Check every number in README.md against the file that produced it.

For each entry in claims.yml this fetches the cited file from the cited
repository and checks two separate things:

  1. the source still reports the value the claim was built from, and
  2. README.md still renders the text that corresponds to it.

Both have to hold. Checking only the source would let the README drift; checking
only the README would let it keep a number its repository has since revised,
which is the failure this exists to catch.

Exits non-zero if any claim fails, so CI blocks on it.

    python scripts/verify_claims.py            # check
    python scripts/verify_claims.py --report   # check and write the status table
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
CLAIMS = ROOT / "claims.yml"
README = ROOT / "README.md"
OWNER = os.environ.get("PROFILE_OWNER", "mzquadri")
API = "https://api.github.com"

MARK_START = "<!-- AUTO:claims:start -->"
MARK_END = "<!-- AUTO:claims:end -->"


class ClaimError(Exception):
    pass


def fetch(repo: str, path: str, branch: str) -> str:
    """Read a file from another repository at a branch tip."""
    url = f"{API}/repos/{OWNER}/{repo}/contents/{path}?ref={branch}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.raw")
    req.add_header("User-Agent", "mzquadri-profile-claim-verifier")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise ClaimError(f"{repo}/{path} returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ClaimError(f"{repo}/{path} unreachable: {exc.reason}") from exc


def dig(obj: Any, key: str) -> Any:
    """Walk a dotted key path, e.g. retrieval.metrics.top_document_accuracy."""
    cur = obj
    for part in key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise ClaimError(f"key path '{key}' stops at '{part}'")
        cur = cur[part]
    return cur


def check_json(claim: dict, text: str) -> tuple[Any, str]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ClaimError(f"source is not valid JSON: {exc}") from exc
    value = dig(data, claim["key"])
    if claim.get("length"):
        if not isinstance(value, (list, dict)):
            raise ClaimError(f"'{claim['key']}' is {type(value).__name__}, cannot take a length")
        value = len(value)
    if not isinstance(value, (int, float)):
        raise ClaimError(f"'{claim['key']}' is {type(value).__name__}, not a number")
    expect, tol = float(claim["expect"]), float(claim.get("tol", 0))
    if abs(float(value) - expect) > tol:
        raise ClaimError(f"source says {value}, claim says {expect} (tolerance {tol})")
    return value, f"{value}"


def check_regex(claim: dict, text: str) -> tuple[Any, str]:
    pattern = claim["pattern"]
    if not re.search(pattern, text):
        raise ClaimError(f"pattern /{pattern}/ no longer matches the source")
    return pattern, "matched"


_BIN_OPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
}


def arithmetic(expression: str, names: dict[str, float]) -> float:
    """Evaluate arithmetic over the extracted names.

    A deliberately small AST walker rather than eval(): claims.yml is data, and
    an expression field that reaches eval() would turn a data file into an
    execution path. Only numbers, the four operators, parentheses, unary minus
    and the names bound by `extract` are reachable.
    """

    def walk(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
                raise ClaimError(f"{node.value!r} is not a number")
            return float(node.value)
        if isinstance(node, ast.Name):
            if node.id not in names:
                raise ClaimError(f"'{node.id}' is not one of the extracted names")
            return float(names[node.id])
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            v = walk(node.operand)
            return -v if isinstance(node.op, ast.USub) else v
        if isinstance(node, ast.BinOp):
            op = _BIN_OPS.get(type(node.op))
            if op is None:
                raise ClaimError(f"operator {type(node.op).__name__} is not allowed")
            right = walk(node.right)
            if isinstance(node.op, ast.Div) and right == 0:
                raise ClaimError("division by zero")
            return op(walk(node.left), right)
        raise ClaimError(f"{type(node).__name__} is not allowed in an expression")

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ClaimError(f"expression {expression!r} does not parse: {exc}") from exc
    return walk(tree)


def check_derived(claim: dict, text: str) -> tuple[Any, str]:
    values: dict[str, float] = {}
    for name, pattern in claim["extract"].items():
        m = re.search(pattern, text)
        if not m:
            raise ClaimError(f"could not extract '{name}' with /{pattern}/")
        try:
            values[name] = float(m.group("v"))
        except (IndexError, ValueError) as exc:
            raise ClaimError(f"'{name}' did not capture a number") from exc

    expression = claim["expression"]
    try:
        got = arithmetic(expression, values)
    except ClaimError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ClaimError(f"expression {expression!r} failed: {exc}") from exc

    expect, tol = float(claim["expect"]), float(claim.get("tol", 0))
    if abs(float(got) - expect) > tol:
        detail = ", ".join(f"{k}={v}" for k, v in values.items())
        raise ClaimError(f"{expression} = {got:.6g} ({detail}), claim says {expect}")
    return got, f"{got:.4g}"


CHECKERS = {"json": check_json, "regex": check_regex, "derived": check_derived}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="write the table into README.md")
    args = ap.parse_args()

    spec = yaml.safe_load(CLAIMS.read_text(encoding="utf-8"))
    default_branch = spec.get("defaults", {}).get("branch", "main")
    claims = spec["claims"]
    readme = README.read_text(encoding="utf-8")

    cache: dict[tuple[str, str], str] = {}
    rows, failures = [], []

    for claim in claims:
        cid, repo = claim["id"], claim["repo"]
        source = claim["source"]
        branch = claim.get("branch", default_branch)
        kind = claim["kind"]
        shown = claim["shown"]

        try:
            key = (repo, source)
            if key not in cache:
                cache[key] = fetch(repo, source, branch)
            checker = CHECKERS.get(kind)
            if checker is None:
                raise ClaimError(f"unknown kind '{kind}'")
            _, rendered = checker(claim, cache[key])

            # The README has to actually show it.
            if shown not in readme:
                raise ClaimError(f"README.md does not contain {shown!r}")

            rows.append((cid, repo, source, rendered, True, ""))
            print(f"  ok    {cid:22s} {repo}/{source}")
        except ClaimError as exc:
            rows.append((cid, repo, source, "—", False, str(exc)))
            failures.append((cid, str(exc)))
            print(f"  FAIL  {cid:22s} {repo}/{source}\n          {exc}")

    print()
    print(f"{len(claims) - len(failures)}/{len(claims)} claims verified against source.")

    if args.report:
        write_report(rows, len(failures))

    if failures:
        print("\nClaims that no longer match their source:", file=sys.stderr)
        for cid, msg in failures:
            print(f"  - {cid}: {msg}", file=sys.stderr)
        return 1
    return 0


def write_report(rows: list[tuple], failures: int) -> None:
    """Replace the claims block in README.md with the current status."""
    total = len(rows)
    ok = total - failures
    lines = [
        MARK_START,
        f"`{ok}/{total}` figures on this page were re-checked against the file "
        "that produced them, by the workflow that built this line.",
        "",
        "<details>",
        "<summary>Which number comes from which file</summary>",
        "",
        "| | Claim | Source of record | Value |",
        "|---|---|---|---|",
    ]
    for cid, repo, source, rendered, passed, err in rows:
        mark = "✅" if passed else "❌"
        link = f"https://github.com/{OWNER}/{repo}/blob/main/{source}"
        detail = rendered if passed else f"**{err}**"
        lines.append(f"| {mark} | `{cid}` | [`{repo}/{source}`]({link}) | {detail} |")
    lines += ["", "</details>", MARK_END]

    readme = README.read_text(encoding="utf-8")
    block = "\n".join(lines)
    if MARK_START in readme and MARK_END in readme:
        readme = re.sub(
            re.escape(MARK_START) + r".*?" + re.escape(MARK_END),
            lambda _: block,
            readme,
            flags=re.DOTALL,
        )
        README.write_text(readme, encoding="utf-8")
        print(f"updated claims block in README.md ({ok}/{total})")
    else:
        print("claims markers not found in README.md; left unchanged", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
