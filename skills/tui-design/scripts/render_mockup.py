#!/usr/bin/env python3
"""Render (or lint) a `.mock` v1 terminal mockup as an exact rows x cols ANSI frame.

Examples:
  python3 render_mockup.py ../assets/demo/fleet--normal--80x24.mock
  python3 render_mockup.py FILE.mock --theme dracula-classic --depth 256 -o FILE.ansi
  python3 render_mockup.py FILE.mock --depth none            # plain text grid
  python3 render_mockup.py FILE.mock --check [--strict-ambiguous] [--allow-nerd-font] [--verbose]
  python3 render_mockup.py FILE.mock --check --regions-json regions.json
  python3 render_mockup.py FILE.mock --check --caps "attrs=bold,dim,inverse colors=16 glyphs=ascii"
  python3 render_mockup.py --glyphs a.mock b.mock [--format md|json]   # inventory of every non-ASCII glyph used

Capability profile: an optional `#! caps: attrs=bold,dim colors=16 glyphs=unicode widgets=tabs,list` header (or --caps
with the same syntax, which overrides it key by key) declares what the host supports. --check then reports an attribute
outside `attrs` (ERROR, names the cell), any non-ASCII glyph under glyphs=ascii (ERROR, with the V9 ASCII fallback as
hint), PUA/Nerd glyphs under glyphs=unicode (ERROR; allowed under glyphs=nerd), and a reminder for colors=16|none (INFO).
Without an explicit --depth the frame is rendered at the profile's depth (colors=none -> nocolor: no color, attributes kept).

--glyphs FILE... prints one table of every non-ASCII glyph across the files: glyph, U+code, Unicode name, EAW class, emoji
status (Emoji_Presentation is approximated: wide glyphs in the emoji planes + regional indicators; text-default emoji use
the linter's list), PUA/Nerd flag, lint tier, ASCII fallback from V9 (blank when V9 has none), count, first file.
Exit 1 when any glyph is ERROR-tier. --format md (default) | json.

Markup: see references/formats.md "Mockup format". Build mockups with mockkit.py (cell canvas) instead of
hand-writing tags. Beyond tokens/glyph widths/balance, --check errors when text overwrites the border of a
`#! region` whose bbox corners are box-drawing corners (titles may sit between ─ segments, not at corners or
on the vertical sides). Findings: `file:line:col: ERROR|WARN|INFO: msg (hint)`.
--check lists ERROR/WARN individually and collapses INFO to one summary line (--verbose lists them).
In render mode ERROR and WARN findings go to stderr, the frame is still written, and the exit
status is 1 if any ERROR was found (INFO is shown only with --check). Exit 2 = usage/environment.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _mock import Cell, Mock, Style, TEXT_EMOJI, ascii_fallback, classify_glyph, parse_mock  # noqa: E402
import unicodedata  # noqa: E402
from _theme import RESET, load_theme, sgr  # noqa: E402

DEFAULT_THEME = "catppuccin-mocha"
BASE = Style("fg.default", "bg.base", ())


def fit_row(cells: list[Cell], cols: int) -> list[Cell]:
    """Truncate to exactly `cols` cells (a wide glyph straddling the edge becomes a space), pad with base."""
    out: list[Cell] = []
    used = 0
    for c in cells:
        if used + c.width > cols:
            break
        out.append(c)
        used += c.width
    out += [Cell(" ", 1, Style())] * (cols - used)
    return out


def render(mock: Mock, theme, depth: str) -> str:
    lines: list[str] = []
    blank = [Cell(" ", 1, Style())] * mock.cols
    for y in range(mock.rows):
        cells = fit_row(mock.grid[y], mock.cols) if y < len(mock.grid) else blank
        if depth == "none":
            lines.append("".join(c.text for c in cells) + "\n")
            continue
        parts: list[str] = []
        prev = None
        for c in cells:
            key = (c.style.fg or BASE.fg, c.style.bg or BASE.bg, c.style.attrs)
            if key != prev:
                parts.append(sgr(theme, key[0], key[1], key[2], depth))
                prev = key
            parts.append(c.text)
        parts.append(RESET + "\n")
        lines.append("".join(parts))
    return "".join(lines)

TIER_RANK = {"ERROR": 3, "WARN": 2, "INFO": 1, "OK": 0}


def is_emoji_presentation(ch: str) -> bool:
    """Approximation of Emoji_Presentation=Yes (the stdlib has no emoji data): wide glyphs in the emoji planes,
    regional indicators, and the BMP emoji-presentation set."""
    cp = ord(ch)
    if 0x1F1E6 <= cp <= 0x1F1FF:
        return True
    if cp >= 0x1F000:
        return unicodedata.east_asian_width(ch) == "W"
    return ch in "⌚⌛⏩⏪⏫⏬⏰⏳◽◾☔☕♈♉♊♋♌♍♎♏♐♑♒♓♿⚓⚡⚪⚫⚽⚾⛄⛅⛎⛔⛪⛲⛳⛵⛺⛽✅✊✋✨❌❎❓❔❕❗➕➖➗➰➿⬛⬜⭐⭕"


def glyph_inventory(paths: list[str], strict: bool, nerd: bool, caps: str | None) -> tuple[list[dict], int]:
    """Every non-ASCII glyph used in the body of the given mockups, worst tier first. Returns (rows, exit status)."""
    inv: dict[str, dict] = {}
    bad_files = 0
    for path in paths:
        try:
            text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            print(f"render_mockup: cannot read {path}: {e}", file=sys.stderr)
            bad_files += 1
            continue
        label = "<stdin>" if path == "-" else path
        mock = parse_mock(text, label, strict=strict, nerd=nerd, caps=caps)
        for row in mock.grid:
            for cell in row:
                for ch in cell.text:
                    if ord(ch) < 128:
                        continue
                    d = inv.setdefault(ch, {"count": 0, "first_file": label, "files": [], "tier": "OK"})
                    d["count"] += 1
                    if label not in d["files"]:
                        d["files"].append(label)
                    g = classify_glyph(ch, strict, nerd, mock.caps)
                    tier = g[0] if g else "OK"
                    if TIER_RANK[tier] > TIER_RANK[d["tier"]]:
                        d["tier"] = tier
    rows = []
    for ch, d in inv.items():
        cp = ord(ch)
        rows.append({
            "glyph": ch, "codepoint": f"U+{cp:04X}", "name": unicodedata.name(ch, "<unnamed>").lower(),
            "eaw": unicodedata.east_asian_width(ch),
            "emoji": "emoji_presentation" if is_emoji_presentation(ch) else "text_default" if ch in TEXT_EMOJI else "",
            "pua": unicodedata.category(ch) == "Co" or cp >= 0xF0000,
            "tier": d["tier"], "ascii_fallback": ascii_fallback(ch) or None,
            "count": d["count"], "first_file": d["first_file"], "files": d["files"],
        })
    rows.sort(key=lambda r: (-TIER_RANK[r["tier"]], -r["count"], r["codepoint"]))
    return rows, (2 if bad_files and not rows else 1 if any(r["tier"] == "ERROR" for r in rows) else 0)


def glyph_table_md(rows: list[dict]) -> str:
    head = "| Glyph | Code | Name | EAW | Emoji | PUA/Nerd | Tier | ASCII fallback | Count | First file |"
    out = [head, "|" + "---|" * 10]
    for r in rows:
        fb = "`" + r["ascii_fallback"].replace("|", "\\|") + "`" if r["ascii_fallback"] else "-"
        out.append(f"| {r['glyph']} | {r['codepoint']} | {r['name']} | {r['eaw']} | {r['emoji'] or '-'} | "
                   f"{'PUA' if r['pua'] else '-'} | {r['tier']} | {fb} | {r['count']} | {r['first_file']} |")
    errs = sum(r["tier"] == "ERROR" for r in rows)
    out.append("")
    out.append(f"{len(rows)} distinct non-ASCII glyph(s), {errs} at ERROR tier.")
    return "\n".join(out) + "\n"


def regions_payload(mock: Mock) -> dict:
    return {
        "source": Path(mock.path).name,
        "title": mock.title,
        "state": mock.state,
        "size": {"cols": mock.cols, "rows": mock.rows},
        "regions": [
            {"id": r.id, "role": r.role, "bbox": {"x": r.x, "y": r.y, "w": r.w, "h": r.h}, "title": r.title}
            for r in mock.regions
        ],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render or lint a .mock v1 terminal mockup.", epilog=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="*", help="input .mock file ('-' = stdin); several only with --glyphs")
    ap.add_argument("--theme", help=f"theme id or path (default: header 'theme:' else {DEFAULT_THEME})")
    ap.add_argument("--depth", choices=["truecolor", "256", "16", "nocolor", "none"], default=None,
                    help="render depth (default: the caps profile's colors, else truecolor)")
    ap.add_argument("--caps", metavar="SPEC", help="capability profile 'attrs=bold,dim colors=16 glyphs=ascii widgets=…' "
                    "(overrides/defines the '#! caps:' header key by key)")
    ap.add_argument("--glyphs", action="store_true", help="print the inventory of every non-ASCII glyph across FILE... (exit 1 on ERROR-tier glyphs)")
    ap.add_argument("--format", choices=["md", "json"], default="md", help="with --glyphs: output format (default md)")
    ap.add_argument("--check", action="store_true", help="lint only: print findings, no frame")
    ap.add_argument("--strict-ambiguous", action="store_true", help="promote INFO (EAW=A chrome glyphs) to ERROR")
    ap.add_argument("--allow-nerd-font", action="store_true", help="do not flag private-use glyphs")
    ap.add_argument("--regions-json", metavar="OUT", help="export '#! region' lines as JSON (calibration ground truth)")
    ap.add_argument("--verbose", action="store_true", help="with --check: list every INFO finding (default: one summary line)")
    ap.add_argument("-o", "--out", help="write the frame here instead of stdout")
    a = ap.parse_args(argv)
    if not a.file:
        ap.error("no input file")
    if a.glyphs:
        rows, rc = glyph_inventory(a.file, a.strict_ambiguous, a.allow_nerd_font, a.caps)
        out = (json.dumps({"files": a.file, "glyphs": rows, "errors": sum(r["tier"] == "ERROR" for r in rows)},
                          indent=2, ensure_ascii=False) + "\n") if a.format == "json" else glyph_table_md(rows)
        if a.out:
            Path(a.out).write_text(out, encoding="utf-8")
        else:
            sys.stdout.write(out)
        return rc
    if len(a.file) != 1:
        ap.error("exactly one input file (several only with --glyphs)")
    a.file = a.file[0]

    try:
        text = sys.stdin.read() if a.file == "-" else Path(a.file).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"render_mockup: cannot read {a.file}: {e}", file=sys.stderr)
        return 2
    path = "<stdin>" if a.file == "-" else a.file
    mock = parse_mock(text, path, strict=a.strict_ambiguous, nerd=a.allow_nerd_font, caps=a.caps)
    errors = [f for f in mock.findings if f.level == "ERROR"]

    if a.regions_json:
        Path(a.regions_json).write_text(json.dumps(regions_payload(mock), indent=2, ensure_ascii=False) + "\n")

    if a.check:
        infos = [f for f in mock.findings if f.level == "INFO" and not f.tag]
        for f in mock.findings:
            if f.level != "INFO" or a.verbose or f.tag:
                print(f.fmt(path))
        if infos and not a.verbose:
            glyphs = " ".join(dict.fromkeys(chr(int(m.group(1), 16)) for f in infos if (m := re.search(r"U\+([0-9A-F]+)", f.msg))))
            print(f"{path}: INFO: {len(infos)} info (ambiguous-width glyphs: {glyphs}) - use --verbose to list")
        n = {lv: sum(1 for f in mock.findings if f.level == lv) for lv in ("ERROR", "WARN", "INFO")}
        print(f"{path}: {n['ERROR']} error(s), {n['WARN']} warning(s), {n['INFO']} info", file=sys.stderr)
        return 1 if errors else 0

    try:
        theme = load_theme(a.theme or mock.theme or DEFAULT_THEME)
    except (FileNotFoundError, ValueError, KeyError) as e:
        print(f"render_mockup: {e}", file=sys.stderr)
        return 2
    for f in mock.findings:
        if f.level != "INFO":
            print(f.fmt(path), file=sys.stderr)
    frame = render(mock, theme, a.depth or mock.caps.depth)
    if a.out:
        Path(a.out).write_text(frame, encoding="utf-8")
    else:
        sys.stdout.write(frame)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
