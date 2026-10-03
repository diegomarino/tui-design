#!/usr/bin/env python3
"""(Re)generate the **Sections** list at the top of every reference, with exact line ranges. Stdlib only.

    python3 tools/gen_toc.py              rewrite every stale list; prints what changed
    python3 tools/gen_toc.py --check      exit 1 if any list is stale or has a placeholder (writes nothing)
    python3 tools/gen_toc.py --init FILE… insert a list into references that have none, then fill its placeholders

A managed file is any Markdown file under skills/tui-design/references/ (templates/ excluded: they are copied into
the user's documents) that has a `**Sections**` line. Its list gets one entry per `## ` heading, in order:

    - [Title](#anchor) · L<start>–<end> — <when to read it>

<start> is the heading's line and <end> the section's last non-blank line, in the final file, so an agent reads
exactly that range (`sed -n 'START,ENDp' FILE`). The list's own length moves every line number, so generation
repeats until the file stops changing (a fixed point); a second run is a no-op. Titles and "when to read it" texts
are kept from the existing list (matched by anchor, then by position for a renamed heading); a new heading gets a
placeholder that --check, and tests/test_toc.py, reject until someone writes its text.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_links import FENCE, HEADING, slug  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "skills" / "tui-design" / "references"
EXCLUDED = ("templates",)
HEADER = ("**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, "
          "or Read with offset/limit):")
PLACEHOLDER = "TODO: say when to read this section."
ENTRY = re.compile(r"^- \[(?P<title>.+?)\]\(#(?P<anchor>[^)\s]+)\)(?: · L\d+–\d+)? — (?P<desc>.*)$")


def headings(lines: list[str]) -> list[tuple[int, int, str, str]]:
    """(index, level, text, anchor) of every heading outside fenced code; anchors deduplicated as GitHub does."""
    out, seen, fenced = [], {}, False
    for i, line in enumerate(lines):
        if FENCE.match(line):
            fenced = not fenced
            continue
        m = None if fenced else HEADING.match(line)
        if m:
            s = slug(m.group(2))
            k = seen.get(s, 0)
            seen[s] = k + 1
            out.append((i, len(m.group(1)), m.group(2), s if k == 0 else f"{s}-{k}"))
    return out


def find_block(lines: list[str]) -> tuple[int, int] | None:
    """(index of the **Sections** line, index after its last entry), or None."""
    for i, line in enumerate(lines[:20]):
        if line.startswith("**Sections**"):
            j = i + 1
            while j < len(lines) and lines[j].startswith("- "):
                j += 1
            return i, j
    return None


def sections(lines: list[str]) -> list[tuple[str, str, int, int]]:
    """(heading text, anchor, start line, end line) of every `## ` section, 1-based inclusive, trailing blanks cut."""
    hs = headings(lines)
    out = []
    for n, (i, level, text, anchor) in enumerate(hs):
        if level != 2:
            continue
        nxt = next((j for j, lv, _, _ in hs[n + 1:] if lv <= 2), len(lines))
        end = nxt - 1
        while end > i and not lines[end].strip():
            end -= 1
        out.append((text, anchor, i + 1, end + 1))
    return out


def render(lines: list[str]) -> list[str]:
    """One pass: rebuild the block of `lines` from its current headings and line numbers."""
    start, stop = find_block(lines)
    old = [m.groupdict() for m in (ENTRY.match(e) for e in lines[start + 1:stop]) if m]
    by_anchor = {e["anchor"]: e for e in old}
    secs = sections(lines)
    anchors = {a for _, a, _, _ in secs}
    entries = []
    for k, (text, anchor, a, b) in enumerate(secs):
        e = by_anchor.get(anchor)
        if e is None and k < len(old) and old[k]["anchor"] not in anchors:     # renamed heading, same slot
            e = {"title": text, "desc": old[k]["desc"]}
        title = e["title"] if e else text
        desc = e["desc"] if e and e["desc"].strip() else PLACEHOLDER
        entries.append(f"- [{title}](#{anchor}) · L{a}–{b} — {desc}")
    return lines[:start] + [HEADER] + entries + lines[stop:]


def generate(text: str) -> str:
    """The file with an up-to-date block, iterated to a fixed point (the block's length shifts line numbers)."""
    lines = text.split("\n")
    for _ in range(20):
        new = render(lines)
        if new == lines:
            return "\n".join(lines)
        lines = new
    raise RuntimeError("gen_toc: no fixed point after 20 passes")


def managed() -> list[Path]:
    files = []
    for p in sorted(REFS.rglob("*.md")):
        if p.relative_to(REFS).parts[0] in EXCLUDED:
            continue
        if find_block(p.read_text(encoding="utf-8").split("\n")):
            files.append(p)
    return files


def init(path: Path) -> bool:
    """Insert an empty block after the H1 (and its blank line); False when the file already has one."""
    lines = path.read_text(encoding="utf-8").split("\n")
    if find_block(lines):
        return False
    h1 = next((i for i, line in enumerate(lines) if line.startswith("# ")), -1)
    at = h1 + 1
    if at < len(lines) and not lines[at].strip():
        at += 1
    lines[at:at] = [HEADER, ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    return True


def problems(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    rel = path.relative_to(ROOT)
    out = []
    if generate(text) != text:
        out.append(f"{rel}: Sections list is stale (run python3 tools/gen_toc.py)")
    if PLACEHOLDER in text:
        out.append(f"{rel}: a Sections entry still says {PLACEHOLDER!r}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="report stale lists and placeholders; write nothing")
    ap.add_argument("--init", nargs="+", metavar="FILE", help="insert a Sections list into these references")
    a = ap.parse_args()
    for f in a.init or ():
        if init(Path(f)):
            print(f"gen_toc: inserted a Sections list into {f}")
    files = managed()
    if a.check:
        found = [msg for p in files for msg in problems(p)]
        for msg in found:
            print(msg)
        print(f"gen_toc: {len(found)} problem(s) in {len(files)} files")
        return 1 if found else 0
    changed = []
    for p in files:
        text = p.read_text(encoding="utf-8")
        new = generate(text)
        if new != text:
            p.write_text(new, encoding="utf-8")
            changed.append(p.relative_to(ROOT))
    for c in changed:
        print(f"gen_toc: updated {c}")
    todo = [p.relative_to(ROOT) for p in files if PLACEHOLDER in p.read_text(encoding="utf-8")]
    for t in todo:
        print(f"gen_toc: {t} has placeholder entries: write when to read each section")
    print(f"gen_toc: {len(changed)} updated, {len(files) - len(changed)} unchanged")
    return 1 if todo else 0


if __name__ == "__main__":
    sys.exit(main())
