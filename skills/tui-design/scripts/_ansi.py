"""Shared ANSI/SGR parser for the tui-design scripts (stdlib only).

Turns ONE frame of terminal output (a `tmux -L <name> capture-pane -p -e` dump, a rendered
`.ansi` mockup, a program's one-shot output) into a grid of cells. Used by
ansi_render.py (SVG/PNG/HTML) and ansi_grid.py (JSON + description skeleton).

Supported: SGR 16 / 256 / truecolor (`;` and `:` forms), bold dim italic underline
(+ styles 4:0-4:5 and SGR 21 double) blink reverse hidden strike overline, underline
colour (58/59), tmux's `5:3` overline quirk, OSC 8 hyperlinks, wide (EAW W/F) and
zero-width (combining, VS16, ZWJ) characters, tabs (8-col stops).

NOT supported (by design): cursor movement, erase sequences, scroll regions, alternate
screen. Every other escape sequence is skipped, never emulated. Feed it a single frame
(`tmux -L <name> capture-pane -p -e`, `capture_tui.sh` output, `render_mockup.py` output) - a raw
pty log of an interactive app is NOT a frame.

Colours are None (terminal default), "p:N" (palette index 0-255) or "#rrggbb".
"""

from __future__ import annotations

import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _theme import ANSI_NAMES, Theme, palette256  # noqa: E402

# Attribute vocabulary = schemas/tui-description.schema.json style.attrs enum.
UL_STYLES = {2: "double_underline", 3: "curly_underline"}       # 4:1/4:4/4:5 (single, dotted, dashed) -> "underline"
SIMPLE_ATTRS = {1: "bold", 2: "dim", 3: "italic", 4: "underline", 5: "blink", 6: "blink", 7: "reverse", 8: "hidden",
                9: "strike", 53: "overline"}
ATTR_OFF = {22: ("bold", "dim"), 23: ("italic",), 25: ("blink",), 27: ("reverse",), 28: ("hidden",),
            29: ("strike",), 55: ("overline",)}
UL_ATTRS = ("underline", "double_underline", "curly_underline")

_TOKEN = re.compile(
    r"\x1b\[([0-9;:]*)m"                       # SGR
    r"|\x1b\]8;[^;\x07\x1b]*;([^\x07\x1b]*)(?:\x07|\x1b\\)"   # OSC 8 hyperlink (group 2 = URI, may be empty)
    r"|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"      # any other OSC: skip
    r"|\x1b\[[0-?]*[ -/]*[@-~]"               # any other CSI: skip (no cursor emulation)
    r"|\x1b[()*+][0-9A-Za-z]"                  # charset designation
    r"|\x1b[@-Z\\-_a-z=>]"                     # other 2-byte escapes
    r"|(.)",                                   # a character
    re.S,
)


@dataclass(frozen=True)
class Style:
    fg: str | None = None
    bg: str | None = None
    ul: str | None = None               # underline colour (SGR 58)
    attrs: frozenset = frozenset()
    link: str | None = None


@dataclass
class Cell:
    ch: str = " "                       # "" for the continuation cell of a wide char
    w: int = 1                          # 1, 2, or 0 (continuation)
    style: Style = Style()


BLANK = Cell()


def char_width(ch: str) -> int:
    """Terminal cell width: 0 combining/format (incl. VS15/16, ZWJ), 2 for East Asian W/F, else 1."""
    if ch < "\x7f":
        return 1 if ch >= " " else 0
    if unicodedata.category(ch) in ("Mn", "Me", "Cf", "Cc"):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in "WF" else 1


def str_width(s: str) -> int:
    return sum(char_width(c) for c in s)


# ---------------------------------------------------------------- SGR

def _color(kind: str, a: list[str]) -> str | None:
    """Colour from the params after 38/48/58 (already split): ['5','N'] | ['2','r','g','b'] | ['2','','r','g','b']."""
    try:
        if a and a[0] == "5":
            n = int(a[1])
            return f"p:{n}" if 0 <= n <= 255 else None
        if a and a[0] == "2":
            r, g, b = (int(x or 0) for x in a[-3:])
            if all(0 <= v <= 255 for v in (r, g, b)):
                return f"#{r:02x}{g:02x}{b:02x}"
    except (ValueError, IndexError):
        pass
    return None


def apply_sgr(params: str, st: dict) -> None:
    """Apply one SGR parameter string to the mutable state dict (fg bg ul attrs link)."""
    parts = (params or "0").split(";")
    i = 0
    while i < len(parts):
        p = parts[i]
        if ":" in p:
            head, *rest = p.split(":")
            if head == "4":                                     # 4:N underline style
                st["attrs"] -= set(UL_ATTRS)
                n = int(rest[0]) if rest and rest[0].isdigit() else 1
                if n:
                    st["attrs"].add(UL_STYLES.get(n) or "underline")
            elif head == "5" and rest == ["3"]:                 # tmux writes overline (53) as "5:3"
                st["attrs"].add("overline")
            elif head in ("38", "48", "58"):                    # 38:2::r:g:b / 38:2:r:g:b / 38:5:n
                st[{"38": "fg", "48": "bg", "58": "ul"}[head]] = _color(head, rest)
            i += 1
            continue
        try:
            n = int(p) if p else 0
        except ValueError:
            i += 1
            continue
        if n == 0:
            st.update(fg=None, bg=None, ul=None, attrs=set())
        elif n == 4:
            st["attrs"] -= set(UL_ATTRS)
            st["attrs"].add("underline")
        elif n == 21:
            st["attrs"] -= set(UL_ATTRS)
            st["attrs"].add("double_underline")
        elif n == 24:
            st["attrs"] -= set(UL_ATTRS)
        elif n in SIMPLE_ATTRS:
            st["attrs"].add(SIMPLE_ATTRS[n])
        elif n in ATTR_OFF:
            st["attrs"] -= set(ATTR_OFF[n])
        elif 30 <= n <= 37:
            st["fg"] = f"p:{n - 30}"
        elif 90 <= n <= 97:
            st["fg"] = f"p:{n - 90 + 8}"
        elif 40 <= n <= 47:
            st["bg"] = f"p:{n - 40}"
        elif 100 <= n <= 107:
            st["bg"] = f"p:{n - 100 + 8}"
        elif n == 39:
            st["fg"] = None
        elif n == 49:
            st["bg"] = None
        elif n == 59:
            st["ul"] = None
        elif n in (38, 48, 58):
            key = {38: "fg", 48: "bg", 58: "ul"}[n]
            mode = parts[i + 1] if i + 1 < len(parts) else ""
            take = 2 if mode == "5" else 4 if mode == "2" else 0
            st[key] = _color(str(n), parts[i + 1:i + 1 + take]) if take else None
            i += take
        i += 1


# ---------------------------------------------------------------- parsing

class Grid:
    """rows x cols cells. `cells[y][x]`; wide chars occupy two entries (second: ch="", w=0)."""

    def __init__(self, cells: list[list[Cell]]):
        self.cells = cells
        self.rows = len(cells)
        self.cols = max((len(r) for r in cells), default=0)

    def text_rows(self) -> list[str]:
        """Verbatim row text; continuation cells omitted (display width == cols)."""
        return ["".join(c.ch for c in row if c.w) for row in self.cells]

    def resize(self, cols: int | None, rows: int | None) -> "Grid":
        cols = self.cols if cols is None else cols
        rows = self.rows if rows is None else rows
        out = []
        for y in range(rows):
            row = list(self.cells[y]) if y < self.rows else []
            row = row[:cols] + [BLANK] * (cols - len(row))
            if cols and row[cols - 1].w == 2:                   # cropped wide char -> blank
                row[cols - 1] = Cell(" ", 1, row[cols - 1].style)
            out.append(row)
        return Grid(out)


def parse_ansi(text: str, cols: int | None = None, rows: int | None = None) -> Grid:
    """Parse one frame. Style state carries across lines (tmux does not reset at EOL).

    Default size = longest line (display cells) x line count (one trailing newline ignored);
    `cols`/`rows` pad with blank cells or crop.
    """
    text = text.replace("\r\n", "\n").replace("\r", "")
    if text.endswith("\n"):
        text = text[:-1]
    st = {"fg": None, "bg": None, "ul": None, "attrs": set(), "link": None}
    cache: dict = {}

    def style() -> Style:
        key = (st["fg"], st["bg"], st["ul"], frozenset(st["attrs"]), st["link"])
        s = cache.get(key)
        if s is None:
            s = cache[key] = Style(*key)
        return s

    grid: list[list[Cell]] = []
    for line in text.split("\n"):
        row: list[Cell] = []
        for m in _TOKEN.finditer(line):
            ch = m.group(3)
            if m.group(1) is not None:
                apply_sgr(m.group(1), st)
            elif m.group(2) is not None:
                st["link"] = m.group(2) or None
            elif ch is not None:
                if ch == "\t":
                    for _ in range(8 - len(row) % 8):
                        row.append(Cell(" ", 1, style()))
                    continue
                w = char_width(ch)
                if w == 0:
                    if row and ord(ch) >= 0x7f:                  # combining / VS16 / ZWJ -> previous glyph
                        k = len(row) - 1
                        if not row[k].w and k:
                            k -= 1
                        row[k].ch += ch
                    continue
                row.append(Cell(ch, w, style()))
                if w == 2:
                    row.append(Cell("", 0, row[-1].style))
        grid.append(row)
    return Grid(grid).resize(cols or None, rows or None)       # also pads every row to the same width


# ---------------------------------------------------------------- colour resolution

SLOT_NAMES = {i: f"ansi.{n}" for i, n in enumerate(ANSI_NAMES)}


class Resolver:
    """Resolve parsed colours against a theme: 0-15 + default fg/bg from the theme, 16-255 xterm, truecolor as is."""

    def __init__(self, theme: Theme):
        self.theme = theme
        self.pal = palette256(theme.ansi)
        self.fg = theme.foreground
        self.bg = theme.background
        self.cursor = theme.cursor or theme.foreground

    def hex(self, color: str | None, default: str | None = None) -> str | None:
        if color is None:
            return default
        return self.pal[int(color[2:])] if color[0] == "p" else color

    @staticmethod
    def slot(color: str | None, default: str) -> str | None:
        """'ansi.red' | 'p:208' | 'term.fg'|'term.bg' (default) | None (off-palette truecolor)."""
        if color is None:
            return default
        if color[0] == "p":
            n = int(color[2:])
            return SLOT_NAMES[n] if n < 16 else color
        return None

    def painted(self, s: Style) -> tuple[str, str | None]:
        """(fg, bg) as painted. bg None = terminal default background (no fill). reverse and hidden applied."""
        fg, bg = self.hex(s.fg, self.fg), self.hex(s.bg)
        if "reverse" in s.attrs:
            fg, bg = bg or self.bg, fg
        if "hidden" in s.attrs:
            fg = bg or self.bg
        return fg, bg
