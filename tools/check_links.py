#!/usr/bin/env python3
"""Check relative links and images in the repository's Markdown. Stdlib only.

    python3 tools/check_links.py            exit 0 = no problems, 1 = problems (printed as file:line: message)

Checks every Markdown file at the root, in docs/, evals/ and skills/tui-design/:
  - a relative link or image (Markdown, or an HTML <a href> / <img src>) points at a file or directory that exists;
  - a `#anchor` (same file or another Markdown file) matches a heading, using GitHub's slug rules;
  - nothing under skills/tui-design/ points outside that folder (an installed copy has nothing else).
External links (http, https, mailto) are not fetched. Links inside code spans and fenced code blocks are ignored.
"""
from __future__ import annotations

import re
import sys
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "tui-design"
LINK = re.compile(r"!?\[(?:[^\[\]]|\[[^\]]*\])*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
HTML_REF = re.compile(r"""<(?:a|img)\b[^>]*?\b(?:href|src)=["']([^"']+)["']""", re.I)
FENCE = re.compile(r"^\s*(```|~~~)")
CODE_SPAN = re.compile(r"(`+)(?:(?!\1).)+?\1")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def markdown_files() -> list[Path]:
    files = sorted(ROOT.glob("*.md"))
    for d in ("docs", "evals", "skills/tui-design"):
        files += sorted((ROOT / d).rglob("*.md"))
    return [f for f in files if "node_modules" not in f.parts]


def lines_outside_code(text: str):
    fenced = False
    for n, line in enumerate(text.splitlines(), 1):
        if FENCE.match(line):
            fenced = not fenced
            continue
        if not fenced:
            yield n, line


def slug(heading: str) -> str:
    """GitHub's heading anchor: strip markup, lowercase, drop punctuation, spaces to hyphens."""
    h = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", heading)       # links -> their text
    h = h.replace("`", "").strip().lower()
    h = re.sub(r"[^\w\- ]", "", h, flags=re.UNICODE)
    return h.replace(" ", "-")


@lru_cache(maxsize=None)
def anchors(path: Path) -> frozenset[str]:
    seen: dict[str, int] = {}
    out = set()
    for _, line in lines_outside_code(path.read_text(encoding="utf-8")):
        m = HEADING.match(line)
        if not m:
            continue
        s = slug(m.group(2))
        k = seen.get(s, 0)
        out.add(s if k == 0 else f"{s}-{k}")
        seen[s] = k + 1
    return frozenset(out)


def check(path: Path) -> list[str]:
    problems = []
    in_skill = SKILL in path.parents
    for n, line in lines_outside_code(path.read_text(encoding="utf-8")):
        text = CODE_SPAN.sub("", line)
        for target in [m.group(1) for m in LINK.finditer(text)] + HTML_REF.findall(text):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):          # http:, https:, mailto:
                continue
            where = f"{path.relative_to(ROOT)}:{n}"
            file_part, _, anchor = target.partition("#")
            dest = (path.parent / unquote(file_part)).resolve() if file_part else path
            if in_skill and SKILL != dest and SKILL not in dest.parents:
                problems.append(f"{where}: link leaves skills/tui-design/: {target}")
                continue
            if not dest.exists():
                problems.append(f"{where}: missing target: {target}")
                continue
            if anchor and dest.suffix == ".md" and anchor not in anchors(dest):
                problems.append(f"{where}: no heading for #{anchor} in {dest.relative_to(ROOT)}")
    return problems


def main() -> int:
    files = markdown_files()
    problems = [p for f in files for p in check(f)]
    for p in problems:
        print(p)
    print(f"check_links: {len(problems)} problem(s) in {len(files)} files", file=sys.stderr if problems else sys.stdout)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
