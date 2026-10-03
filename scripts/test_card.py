#!/usr/bin/env python3
"""Terminal test card: one 80x24 screen that shows what a terminal, or a host such as a multiplexer plugin popup,
can really draw. Run it inside the target, take one screenshot, and read the capability profile off it
(`#! caps: attrs=… colors=… glyphs=…`, references/formats.md#capability-profile).

Two modes, because the drawing library caps what the host can show:
  raw (default)  writes SGR / OSC escapes directly, like Ink, Bubble Tea, Ratatui or Textual do: attributes incl.
                 strike, curly / colored underline, overline, OSC 8 links, 16 / 256 / 24-bit color.
  --curses       draws through Python curses, like a curses plugin: no strike, no extended underline, no links,
                 at most 256 colors (truecolor needs a direct-color terminfo). Use it when the app is curses.

Reading the card:
  attrs   a word that looks like `normal` is an attribute the host drops.
  16      the swatches are the terminal's own palette (what `ansi16` tokens become), not the theme's.
  256     smooth cube and grey ramp = 256 colors work.  24-bit: a smooth hue sweep = truecolor; visible bands = the
          host quantizes to 256; wrong or missing colors = no truecolor.
  widths  every row's `|` bars must line up with the `ref` row; a bar that drifts right marks a glyph the host draws
          wider than one cell (unsafe in layout). The `wide` row shows what a real 2-cell glyph looks like.
  nerd    boxes or blanks = no Nerd Font (glyphs=unicode at most).

Usage:
  python3 SKILL_DIR/scripts/test_card.py            # raw escapes; waits for a key when on a TTY
  python3 SKILL_DIR/scripts/test_card.py --curses   # through curses; q quits
  python3 SKILL_DIR/scripts/test_card.py > card.ansi   # not a TTY: prints the card once (render it with ansi_render.py)
  python3 SKILL_DIR/scripts/test_card.py --print [--curses]   # print once, with a neutral info line (references)
Compare the screenshot with assets/test-card/{raw,curses}--reference.png: anything missing on the screenshot
(an overline, the red underline, the 24-bit sweep) is something the host drops.
"""

from __future__ import annotations

import argparse
import colorsys
import os
import sys

CORE = "✓ ✗ ▲ ● ○ ◇ ❯ › … · │ ─ ╭ ╮ ╰ ╯ ▏ ▌ █ ⣿ ▁ ▇".split()      # the safe set (visual-vocabulary.md)
RISKY = "✔ ★ ⚠ ⏵ ⏸ ↻ ⚡ ❤ ☐ ☑".split()                             # Emoji=Yes or ambiguous width
NERD = ["\ue0a0", "\uf07b", "\uf113", "\ue5ff", "\uf00c", "\uf489"]  # branch folder github folder check terminal
WIDE = ["日", "本", "🙂"]

RAW_ATTR = {"bold": "1", "dim": "2", "italic": "3", "underline": "4", "inverse": "7", "strike": "9",
            "double": "4:2", "curly": "4:3", "ucolor": "4;58;2;255;64;64", "overline": "53"}


def seg(text: str, fg=None, bg=None, attrs=(), link: str | None = None):
    return (text, {"fg": fg, "bg": bg, "attrs": tuple(attrs), "link": link})


def label(name: str):
    return seg(f"{name:<8}", attrs=("bold",))


def card(mode: str, info: str, colors: int = 256) -> list[list[tuple]]:
    """The card as rows of (text, style) segments; the same layout feeds both renderers."""
    note = lambda t: seg(t, attrs=("dim",))
    rows: list[list[tuple]] = [
        [seg(f"TEST CARD · {'raw escapes' if mode == 'raw' else 'curses'} · q quits", attrs=("bold",))],
        [note(info)],
        [],
    ]
    row = [label("attrs")]
    names = ["normal", "bold", "dim", "italic", "underline", "inverse"] + (["strike"] if mode == "raw" else [])
    for n in names:
        row += [seg(n, attrs=() if n == "normal" else (n,)), seg(" ")]
    if mode == "curses":
        row.append(note("strike: n/a"))
    rows.append(row)
    if mode == "raw":
        rows.append([label("extra"), seg("double", attrs=("double",)), seg(" "), seg("curly", attrs=("curly",)),
                     seg(" "), seg("colored", attrs=("ucolor",)), seg(" "), seg("overline", attrs=("overline",)),
                     seg(" "), seg("link", link="https://example.com"),
                     note("  (click it: opens = OSC 8 links work)")])
    else:
        rows.append([label("extra"), note("curly/colored underline, overline, links: n/a in curses")])
    rows.append([])
    rows.append([label("16")] + [seg("   ", bg=i) for i in range(16)])
    rows.append([seg(" " * 8)] + [note(f"{i:<3}") for i in range(16)])
    if colors >= 256:
        rows.append([label("256")] + [seg(" ", bg=c) for c in range(16, 232, 4)])
        rows.append([seg(" " * 8)] + [seg("  ", bg=c) for c in range(232, 256)])
    else:
        rows.append([label("256"), note(f"curses reports {colors} colors: design at 16 (colors=16)")])
        rows.append([])
    if mode == "raw":
        sweep = []
        for i in range(64):
            r, g, b = colorsys.hsv_to_rgb(i / 64, 0.65, 0.95)
            sweep.append(seg(" ", bg=f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"))
        rows.append([label("24-bit")] + sweep)
    else:
        rows.append([label("24-bit"), note("n/a in curses: at most 256 colors (truecolor needs raw escapes)")])
    rows.append([label("fill"), seg("  surface fill · bold text on it  ", bg=236 if colors >= 256 else 8,
                                    attrs=("bold",))])
    rows.append([])
    rows.append([label("widths"), note("bars in each row must line up with the ref row")])
    rows.append([label("ref"), seg("|" + "a|" * len(CORE))])
    rows.append([label("core"), seg("|" + "|".join(CORE) + "|")])
    rows.append([label("emoji?"), seg("|" + "|".join(RISKY) + "|")])
    rows.append([label("nerd"), seg("|" + "|".join(NERD) + "|"), note("  boxes/blanks = no Nerd Font")])
    rows.append([label("2-cell"), seg("|aa" * len(WIDE) + "|"), note("  ref for wide glyphs")])
    rows.append([label("wide"), seg("|" + "|".join(WIDE) + "|"), note("  must line up with 2-cell")])
    rows.append([])
    rows.append([note("→ #! caps: attrs=… colors=16|256|truecolor glyphs=ascii|unicode|nerd")])
    return rows


# ── raw renderer ──────────────────────────────────────────────────────────────────────────────────────────────────

def _color(c, base: int) -> str | None:
    """base 30 = foreground, 40 = background."""
    if c is None:
        return None
    if isinstance(c, str):
        return f"{base + 8};2;{int(c[1:3], 16)};{int(c[3:5], 16)};{int(c[5:7], 16)}"
    if c < 8:
        return str(base + c)
    if c < 16:
        return str(base + 60 + c - 8)
    return f"{base + 8};5;{c}"


def render_raw(rows) -> str:
    out = []
    for row in rows:
        line = []
        for text, st in row:
            codes = [RAW_ATTR[a] for a in st["attrs"]]
            codes += [c for c in (_color(st["fg"], 30), _color(st["bg"], 40)) if c]
            if st["link"]:
                text = f"\x1b]8;;{st['link']}\x1b\\{text}\x1b]8;;\x1b\\"
            line.append(f"\x1b[0;{';'.join(codes)}m{text}\x1b[0m" if codes else text)
        out.append("".join(line))
    return "\n".join(out) + "\n"


def run_raw() -> int:
    tty = sys.stdout.isatty()
    try:
        cols, lines = os.get_terminal_size()
    except OSError:
        cols, lines = 80, 24
    info = (f"TERM={os.environ.get('TERM', '?')} COLORTERM={os.environ.get('COLORTERM', '-')} "
            f"TERM_PROGRAM={os.environ.get('TERM_PROGRAM', '-')}{' tmux' if os.environ.get('TMUX') else ''}"
            f" · {cols}x{lines}")
    body = render_raw(card("raw", info))
    if not tty:
        sys.stdout.write(body)
        return 0
    sys.stdout.write("\x1b[2J\x1b[H\x1b[?25l" + body)
    sys.stdout.flush()
    try:
        if sys.stdin.isatty():
            import termios
            import tty as ttymod
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                ttymod.setcbreak(fd)
                sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
    finally:
        sys.stdout.write("\x1b[?25h")
        sys.stdout.flush()
    return 0


# ── curses renderer ───────────────────────────────────────────────────────────────────────────────────────────────

def run_curses() -> int:
    import curses

    attr_map = {"bold": curses.A_BOLD, "dim": curses.A_DIM, "italic": getattr(curses, "A_ITALIC", 0),
                "underline": curses.A_UNDERLINE, "inverse": curses.A_REVERSE}

    def main(stdscr) -> None:
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        pairs: dict[tuple[int, int], int] = {}

        def pair(fg, bg) -> int:
            fg = fg if isinstance(fg, int) and fg < curses.COLORS else -1
            bg = bg if isinstance(bg, int) and bg < curses.COLORS else -1
            if (fg, bg) == (-1, -1):
                return 0
            if (fg, bg) not in pairs and len(pairs) < curses.COLOR_PAIRS - 1:
                pairs[(fg, bg)] = len(pairs) + 1
                curses.init_pair(pairs[(fg, bg)], fg, bg)
            return pairs.get((fg, bg), 0)

        while True:
            stdscr.erase()
            h, w = stdscr.getmaxyx()
            info = (f"TERM={os.environ.get('TERM', '?')} COLORTERM={os.environ.get('COLORTERM', '-')} "
                    f"· curses COLORS={curses.COLORS} PAIRS={curses.COLOR_PAIRS} · {w}x{h}")
            for y, row in enumerate(card("curses", info, curses.COLORS)):
                if y >= h - 1:
                    break
                x = 0
                for text, st in row:
                    if x >= w - 1:
                        break
                    a = curses.color_pair(pair(st["fg"], st["bg"]))
                    for name in st["attrs"]:
                        a |= attr_map.get(name, 0)
                    try:
                        stdscr.addnstr(y, x, text, w - 1 - x, a)
                    except curses.error:
                        pass
                    x = stdscr.getyx()[1] if stdscr.getyx()[0] == y else w
            stdscr.refresh()
            if stdscr.getch() in (ord("q"), 27):
                return

    curses.wrapper(main)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--curses", action="store_true", help="draw through curses (what a curses app can show)")
    ap.add_argument("--print", action="store_true", help="print the card once as escapes (curses layout too) and exit")
    a = ap.parse_args(argv)
    if a.print:
        mode = "curses" if a.curses else "raw"
        sys.stdout.write(render_raw(card(mode, f"reference · how the {mode} card looks on a host that draws everything")))
        return 0
    return run_curses() if a.curses else run_raw()


if __name__ == "__main__":
    sys.exit(main())
