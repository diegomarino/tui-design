#!/usr/bin/env python3
"""Terminal preview of a theme: terminal slots, neutral ladder, every token as a labelled swatch, sample UI.

Examples:
  python3 preview_theme.py catppuccin-mocha
  python3 preview_theme.py catppuccin-mocha --depth 256
  python3 preview_theme.py catppuccin-mocha --depth 16     # per-theme ansi16 mapping (your terminal's own palette)
  python3 preview_theme.py path/to/theme.json --depth none | less

fg tokens are drawn as colored text on bg.base; bg tokens as filled blocks with fg.default text.
Exit 0 = ok, 2 = theme not found / invalid.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _theme import RESET, Theme, hex_to_rgb, load_theme, load_token_defs, nearest256, sgr  # noqa: E402

WIDTH = 78
LADDER = ["bg.inset", "bg.base", "bg.surface", "bg.raised", "fg.faint", "fg.muted", "fg.default"]


class Painter:
    def __init__(self, theme: Theme, depth: str):
        self.t, self.depth = theme, depth

    def p(self, text: str, fg: str = "fg.default", bg: str = "bg.base", attrs: tuple[str, ...] = ()) -> str:
        if self.depth == "none":
            return text
        return sgr(self.t, fg, bg, attrs, self.depth) + text + RESET

    def line(self, *segs: tuple, pad_bg: str = "bg.base") -> str:
        """segs = (text, fg, bg, attrs) tuples; pads to WIDTH with pad_bg and ends with a newline."""
        used = sum(len(s[0]) for s in segs)
        out = "".join(self.p(*s) for s in segs)
        pad = WIDTH - used
        return out + (self.p(" " * pad, "fg.default", pad_bg) if pad > 0 else "") + "\n"


def _swatch(h: str, idx: int, depth: str) -> str:
    """3-cell filled block for terminal slot `idx` (truecolor/256 show the theme's hex; 16 shows the slot itself)."""
    if depth == "16":
        return f"\x1b[{40 + idx if idx < 8 else 100 + idx - 8}m   "
    if depth == "256":
        return f"\x1b[48;5;{nearest256(h)}m   "
    return "\x1b[48;2;{};{};{}m   ".format(*hex_to_rgb(h))


def hex_label(t: Theme, tok: str, depth: str) -> str:
    if depth == "16":
        col, attrs = t.ansi16[tok]
        return f"{col}" + ("".join(" " + a for a in attrs))
    return t.hex(tok)


def build(theme: Theme, depth: str) -> str:
    P = Painter(theme, depth)
    defs = load_token_defs()
    out: list[str] = []
    A = out.append
    A(P.line((f" {theme.name} ", "fg.title", "bg.base", ("bold",)), (f"[{theme.id}, {theme.appearance}, depth={depth}]", "fg.muted", "bg.base", ())))
    A(P.line())
    # terminal slots
    A(P.line((" terminal  ", "fg.muted", "bg.base", ()),
             (f"bg {theme.background}  fg {theme.foreground}", "fg.default", "bg.base", ())))
    if depth == "none":
        A(" ansi 0-7   " + " ".join(theme.ansi[:8]) + "\n")
        A(" ansi 8-15  " + " ".join(theme.ansi[8:]) + "\n")
    else:
        strip = "".join(_swatch(h, i, depth) for i, h in enumerate(theme.ansi))
        A(P.p(" ansi 0-15  ", "fg.muted") + strip + RESET + "\n")
    A(P.line())
    # neutral ladder
    A(P.line((" neutral ladder (N0..N6)", "fg.muted", "bg.base", ())))
    cells, labels = [], []
    for tok in LADDER:
        kind = defs[tok]["kind"]
        cells.append(P.p("  " + "▒▒▒▒▒" + "  " if kind == "fg" else " " * 9, tok if kind == "fg" else "fg.default",
                         "bg.base" if kind == "fg" else tok))
        labels.append(f"{tok.split('.')[1]:<9}")
    A(" " + "".join(cells) + "\n")
    A(P.p(" " + "".join(labels), "fg.faint") + "\n")
    A(P.line())
    # token swatches
    A(P.line((" tokens", "fg.muted", "bg.base", ()), ("   (tier  name  value  swatch  role)", "fg.faint", "bg.base", ())))
    ON = {"fg.on-accent": "accent.primary", "cursor.fg": "cursor.bg"}     # fg tokens drawn on their natural fill
    for tok, d in defs.items():
        is_bg = d["kind"] == "bg"
        val = hex_label(theme, tok, depth)
        head = f" {d['tier']}  {tok:<22}{val:<16}"
        if is_bg:
            sw = ("  fill  ", "cursor.fg" if tok == "cursor.bg" else "fg.default", tok, ())
        else:
            sw = (" The quick fox 0123 ", tok, ON.get(tok, "bg.base"), ())
        room = WIDTH - len(head) - len(sw[0]) - 1
        A(P.line((head, "fg.default", "bg.base", ()), sw, (" " + d["role"][:room], "fg.faint", "bg.base", ())))
    A(P.line())
    # sample UI
    A(P.line((" sample UI", "fg.muted", "bg.base", ())))
    sb = "statusbar.bg"
    segs = [(" Fleet ", "accent.primary", sb, ("bold",)), ("│", "border.default", sb, ()),
            (" 1 Services ", "tab.active.fg", "tab.active.bg", ("bold",)), (" 2 Logs ", "tab.inactive.fg", sb, ()),
            (" 3 Config ", "tab.inactive.fg", sb, ())]
    used = sum(len(s[0]) for s in segs)
    right = "prod-eu 12:04 "
    segs += [(" " * (WIDTH - used - len(right)), "statusbar.fg", sb, ()), (right, "statusbar.fg", sb, ())]
    A(P.line(*segs, pad_bg=sb))
    sel = "selection.bg"
    A(P.line((" ", "fg.default", sel, ()), ("❯ ", "accent.primary", sel, ("bold",)), ("● ", "status.success", sel, ()),
              ("api-gateway   ", "selection.fg", sel, ("bold",)), ("running  ", "status.success", sel, ()),
              ("  ", "fg.default", sel, ()), ("3/3 replicas  CPU 31%", "selection.fg", sel, ()), pad_bg=sel))
    A(P.line(("   ▲ ", "status.warning", "bg.base", ()), ("billing       ", "fg.default", "bg.base", ()),
             ("degraded  ", "status.warning", "bg.base", ()), ("  p95 820 ms  ", "fg.muted", "bg.base", ()),
             ("12:01 ", "fg.faint", "bg.base", ()), ("search ", "search.match", "bg.base", ("bold",)), ("match", "link", "bg.base", ("underline",))))
    chips: list[tuple] = []
    for tok, label in (("status.success", " OK "), ("status.warning", " WARN "), ("status.error", " FAIL "), ("status.info", " INFO ")):
        chips += [(label, "fg.on-accent", tok, ("bold",)), (" ", "fg.default", "bg.base", ())]
    A(P.line((" ", "fg.default", "bg.base", ()), *chips, ("CPU ", "fg.muted", "bg.base", ()), ("███", "ramp.low", "bg.base", ()),
             ("███", "ramp.mid", "bg.base", ()), ("███", "ramp.high", "bg.base", ()), ("░░░", "fg.faint", "bg.base", ()),
             ("  ", "fg.default", "bg.base", ()), ("+ added ", "diff.added", "bg.base", ()), ("- removed", "diff.removed", "bg.base", ())))
    hints = [(" ", "fg.default", sb, ())]
    for k, d in (("↑↓", "select"), ("enter", "open"), ("/", "filter"), ("tab", "pane")):
        hints += [(k, "keyhint.key", sb, ("bold",)), (f" {d}  ", "keyhint.desc", sb, ())]
    A(P.line(*hints, pad_bg=sb))
    return "".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Preview a theme's tokens in the terminal.", epilog=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("theme", help="theme id or path to theme .json")
    ap.add_argument("--depth", choices=["truecolor", "256", "16", "nocolor", "none"], default="truecolor")
    ap.add_argument("-o", "--out", help="write here instead of stdout")
    a = ap.parse_args(argv)
    try:
        theme = load_theme(a.theme)
    except (FileNotFoundError, ValueError, KeyError, OSError) as e:
        print(f"preview_theme: {e}", file=sys.stderr)
        return 2
    text = build(theme, a.depth)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
