#!/usr/bin/env python3
"""Draw a .mock frame with curses inside the real host (herdr popup, tmux popup, a plain terminal…) to verify
that the host can render the design — colors, background fills, attributes and size — before building it.

The frame is drawn the way a curses app would draw it: one color pair per fg/bg combination, 256-color indexes when
the terminal offers >= 256 colors (nearest xterm color by OKLab, like render_mockup.py --depth 256), otherwise the
theme's 16-color `ansi16` mapping. Attributes: bold, dim, italic (A_ITALIC), underline, reverse. A status line shows
what the host reported (TERM, COLORTERM, curses COLORS / COLOR_PAIRS, size) so a screenshot of it is evidence.

Usage (run it inside the host, then take a screenshot):
  python3 SKILL_DIR/scripts/play_mock.py --probe              # = test_card.py --curses (capability test card)
  python3 SKILL_DIR/scripts/play_mock.py FRAME.mock [--theme ID] [--depth auto|256|16]
Keys: q quit · d toggle depth (256 ↔ 16) · i toggle the info line.
Exit codes: 0 ok, 2 usage error (bad file, frame larger than the terminal is shown with a message instead).
"""

from __future__ import annotations

import argparse
import curses
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _mock import parse_mock  # noqa: E402
from _theme import load_theme, nearest256  # noqa: E402
from render_mockup import render  # noqa: E402
from _ansi import parse_ansi  # noqa: E402

ATTR = {"bold": curses.A_BOLD, "dim": curses.A_DIM, "underline": curses.A_UNDERLINE,
        "reverse": curses.A_REVERSE, "inverse": curses.A_REVERSE,
        "italic": getattr(curses, "A_ITALIC", 0), "strike": 0}


def grid_for(mock, theme, depth: str):
    """Render the mock to ANSI at the given depth and parse it back into cells (ch, style)."""
    ansi = render(mock, theme, "256" if depth == "256" else "16")
    return parse_ansi(ansi, mock.cols, mock.rows)


def color_number(spec: str | None, depth: str) -> int:
    """Map a parsed SGR color from _ansi ('p:N' palette index or '#rrggbb') to a curses color number; -1 = default."""
    if not spec:
        return -1
    if spec.startswith("p:"):
        return int(spec[2:])
    if spec.startswith("#"):
        return nearest256(spec) if depth == "256" else -1
    return -1


def draw(stdscr, mock, theme, depth: str, show_info: bool) -> None:
    stdscr.erase()
    h, w = stdscr.getmaxyx()
    show_info = show_info and h > mock.rows          # a frame the exact size of the host drops the info line
    if w < mock.cols or h < mock.rows:
        msg = f"frame {mock.cols}x{mock.rows} does not fit: terminal is {w}x{h}"
        stdscr.addnstr(0, 0, msg, max(1, w - 1))
        stdscr.refresh()
        return
    grid = grid_for(mock, theme, depth)
    pairs: dict[tuple[int, int], int] = {}
    max_pairs = getattr(curses, "COLOR_PAIRS", 64) - 1
    for y, row in enumerate(grid.cells):
        x = 0
        for cell in row:
            if not cell.w:
                continue
            st = cell.style
            fg = color_number(st.fg, depth)
            bg = color_number(st.bg, depth)
            if depth == "16":
                fg = fg if 0 <= fg < 16 else -1
                bg = bg if 0 <= bg < 16 else -1
            key = (fg, bg)
            if key not in pairs:
                if len(pairs) >= max_pairs:
                    key = (-1, -1)
                else:
                    n = len(pairs) + 1
                    try:
                        curses.init_pair(n, fg, bg)
                        pairs[key] = n
                    except curses.error:
                        key = (-1, -1)
            attr = curses.color_pair(pairs.get(key, 0))
            for a in st.attrs:
                attr |= ATTR.get(a, 0)
            try:
                stdscr.addstr(y, x, cell.ch or " ", attr)
            except curses.error:
                pass                                    # writing the bottom-right cell raises; harmless
            x += cell.w
    if show_info:
        info = (f" {Path(mock.source).name} · depth {depth} · TERM={os.environ.get('TERM', '?')} "
                f"COLORTERM={os.environ.get('COLORTERM', '-')} · curses COLORS={curses.COLORS} "
                f"PAIRS={curses.COLOR_PAIRS} used={len(pairs)} · {w}x{h} · q quit · d depth · i info ")
        try:
            stdscr.addnstr(min(h - 1, mock.rows), 0, info, w - 1, curses.A_REVERSE)
        except curses.error:
            pass
    stdscr.refresh()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mock", nargs="?", help=".mock frame to draw (omit with --probe)")
    ap.add_argument("--probe", action="store_true", help="draw the curses test card (test_card.py --curses) instead of a frame")
    ap.add_argument("--theme", help="theme id (default: the mock's theme, else catppuccin-mocha)")
    ap.add_argument("--depth", choices=["auto", "256", "16"], default="auto")
    a = ap.parse_args(argv)
    if a.probe:
        import test_card
        return test_card.main(["--curses"])
    if not a.mock:
        ap.error("give a .mock file or --probe")
    path = Path(a.mock)
    try:
        mock = parse_mock(path.read_text(encoding="utf-8"), str(path))
        mock.source = str(path)
        theme = load_theme(a.theme or mock.theme or "catppuccin-mocha")
    except (OSError, ValueError, KeyError, FileNotFoundError) as e:
        print(f"play_mock: {e}", file=sys.stderr)
        return 2

    def run(stdscr) -> None:
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        depth = a.depth if a.depth != "auto" else ("256" if curses.COLORS >= 256 else "16")
        show_info = True
        while True:
            draw(stdscr, mock, theme, depth, show_info)
            k = stdscr.getch()
            if k in (ord("q"), 27):
                return
            if k == ord("d"):
                depth = "16" if depth == "256" else "256"
            if k == ord("i"):
                show_info = not show_info
            if k == curses.KEY_RESIZE:
                continue

    curses.wrapper(run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
