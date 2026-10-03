"""mockkit - build `.mock` v1 files from a cell canvas instead of hand-writing tag markup (stdlib only).

Guide with recipes per archetype: references/mockkit.md; signatures: references/mockkit-api.md. You place text, fills, boxes and lines at (x, y) cells, or
use the widget helpers (panel, table, listing, tree, tabs, band, keybar, gauge, overlay, toosmall...) on Rects that
you split from the canvas, so one screen function adapts to 80x24, 120x30 and 60x24. mockkit validates every token,
measures width per code point (East Asian Width W/F = 2, combining = 0, else 1), refuses writes that fall off the
canvas or overwrite a border cell (force=True overrides), merges same-style cells into one tag, escapes braces and
writes the `#!` header including `#! region` lines. `save()` re-lints with the linter of `render_mockup.py --check`.
Output is quiet: save() and matrix() print one summary line (`mockkit: saved 12 frames · 0 errors · 3 warnings → DIR`)
plus one line per warning; verbose=True or MOCKKIT_VERBOSE=1 lists every finding of every frame, INFO included.

Example (run from SKILL_DIR/scripts, or sys.path.insert(0, "SKILL_DIR/scripts")):

    from mockkit import Canvas, Col
    c = Canvas(40, 8, title="Hello", state="normal", theme="catppuccin-mocha")
    c.band(0, [("Hello", "accent.primary bold")], [("prod · 12:04", "statusbar.fg")], region="header")
    body = c.rect.inset(0, 1, 0, 1)                              # rows 1..6: between header and keybar
    inner = c.panel(body, "Services (2)", role="list", focus=True)
    c.table(inner, columns=[Col("", 1), Col("NAME"), Col("STATE", 8)], selected=0, cursor="❯",
            rows=[[("●", "status.success"), "api-gateway", "running"],
                  [("▲", "status.warning"), "billing", ("degraded", "status.warning")]])
    c.chip(inner.right - 7, inner.y + 3, "WARN", "status.warning")
    c.keybar(7, [("↑↓", "select"), ("enter", "open")], region="keybar")
    c.save("hello--normal--40x8.mock")                           # raises CanvasError on lint errors
    # then: python3 render_mockup.py hello--normal--40x8.mock --check ; -o f.ansi ; ansi_render.py f.ansi -o f.png

API (coordinates are 0-based cells, x = column, y = row; sizes w x h; "where" = a Rect, an (x, y, w, h) tuple or
four ints). Low level (unchanged, strict):
    Canvas(cols, rows, title=None, state=None, theme=None, caps=None, fallback=False)
        caps="attrs=bold,dim colors=16 glyphs=ascii" writes `#! caps:`; a write that violates it raises. Helpers
        drop the attributes they add by default and use V9 ASCII glyphs when caps forbid them. fallback=True
        degrades instead of raising everywhere: glyphs -> V9 ASCII, boxes -> ascii, forbidden attributes dropped
        (use it to derive a host-limited variant of a finished design; keep it off while designing for the host).
    .text(x, y, s, spec=None, force=False, clip=False) -> end x    clip=True truncates (with ⋯) before the next
        border or the canvas edge; clip=N to N cells.   .runs(x, y, [(s, spec)...])   .rtext(x_end, y, s, spec)
    .fill(x, y, w, h, spec)   .clear(x, y, w, h, bg=None)   .hline/.vline(..., ends=("├", "┤"))
    .box(x, y, w, h, title=None, border="rounded", spec="border.default", title_spec="fg.title bold", region=None,
         title_right=None, bottom=None, bottom_right=None, fill=None, clear=False, force=False)
    .region(id, role, x, y, w, h, title)   .note(text)   .focus(rid)   .selected(rid, row)   .selected_at(rid, y)
    .to_mock()   .plain()   .save(path, check=True, verbose=None, report=True)
Layout:   c.rect -> Rect(0, 0, cols, rows);  Rect.inset(l, t, r, b) / .inner / .split_h([30, "*"], gap) (side by
    side) / .split_v([1, "*", 1]) (stacked) / .take(n, "top|bottom|left|right") / .center(w, h) / .row(i);
    sizes: int = cells, float < 1 = share, "*" / "2*" = flex weight.  layout(total, sizes, gap).  size_class(cols).
Widgets (Canvas methods; each returns what you need next):
    panel(where, title, role="panel", focus=False, **box) -> inner Rect     band(y, left, right, bg=...) header/status
    tabs(x, y, items, active) -> end x     keybar(y, left, right, x=0, w=None, bg=..., overflow="raise|drop")
    message(y, status, text, meta)   chip(x, y, text, token)   kv(x, y, pairs, key_w=None, w=None)   lines(x, y, items)
    table(where, columns=[Col(...)], rows=..., header=True, selected=None, offset=0, total=None, cursor=None,
          zebra=False|True|"newest-first"|fn, zebra_phase=1, row_spec=None, inactive=False, stale=False,
          skeleton=0) -> info(cols, y, shown, range)
    listing(where, items, selected=None, cursor="❯", ...)    tree(where, nodes, indent=4, folds=False, ...)
    gauge(x, y, w, value, label="pct", label_w=5, ramp=..., smooth=False) -> end x
    scrollbar(x, y, h, offset, visible, total)  (on a box side: only the thumb replaces the border)
    overlay(w, h, title, fade=True, hints=None) -> inner Rect    fade()    center(where, lines)
    toosmall(need=(80, 24), app=None, keys=(("q", "quit"),))     g(role) -> glyph per caps   adapt(spec)
Pure helpers: width, fit(s, w, align="l|r|c", side="end|start|middle"), truncate(s, w, side), bar, spark,
    fold_runs(seq, key) -> [(item, n)], times(label, n) -> "label ×n", scroll_range(off, vis, total) -> "1-6/21",
    scroll_pos(i, total) -> "12/90", chip(text, token) -> run, hint_runs(items), tab_runs(items, active), tree_rows.
Matrix: matrix(build, variant, out_dir, states=..., sizes=..., extra=..., theme=..., caps=..., render=, png=,
    gallery=, verbose=None) (theme = a bundled id or a path to a theme .json, as in render_mockup.py --theme) builds build(c, state) for every state x size, saves `<variant>--<state>--<cols>x<rows>.mock`
    (linted), optionally .ansi/.png and a gallery; frame_name() validates names.
Border cells (box edges, hline/vline) are protected: text onto them raises with the free span of that row.
Chips: `fg.on-accent` is text, so put it on an accent/status fill (`fg.on-accent on:status.warning`).
"""

from __future__ import annotations

import difflib
import os
import re
import subprocess
import sys
import types
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _mock import (Caps, ascii_fallback, char_width, classify_glyph, known_roles, parse_caps,  # noqa: E402
                   parse_mock, str_width)
from _theme import ATTRS, THEMES_DIR, load_token_defs  # noqa: E402

__all__ = ["Canvas", "CanvasError", "Col", "Node", "Rect", "width", "fit", "truncate", "bar", "spark", "layout",
           "size_class", "fold_runs", "times", "scroll_range", "scroll_pos", "chip", "hint_runs", "tab_runs",
           "tree_rows", "matrix", "frame_name", "STATUS", "GLYPHS"]

SCRIPTS = Path(__file__).resolve().parent
BORDERS = {
    "rounded": ("╭╮╰╯", "─", "│"),
    "light": ("┌┐└┘", "─", "│"),
    "heavy": ("┏┓┗┛", "━", "┃"),
    "double": ("╔╗╚╝", "═", "║"),
    "ascii": ("++++", "-", "|"),
}
VISIBLE_ON_SPACE = ("inverse", "underline", "strike")
# Foreground tokens that carry no meaning of their own: a selected row may restyle them (semantic ones stay).
NEUTRAL_FG = {None, "fg.default", "fg.muted", "fg.faint", "fg.title", "table.header", "statusbar.fg", "keyhint.desc"}
# role -> (unicode glyph, ASCII fallback, token); visual-vocabulary.md V5 (status) and V9 (ASCII).
STATUS = {
    "ok": ("✓", "[ok]", "status.success"), "fail": ("✗", "[x]", "status.error"),
    "warn": ("▲", "[!]", "status.warning"), "info": ("i", "[i]", "status.info"),
    "running": ("●", "[*]", "status.success"), "working": ("⋯", "...", "accent.primary"),
    "pending": ("·", ".", "fg.faint"), "marked": ("●", "*", "mark"),
}
STATUS.update({"success": STATUS["ok"], "done": STATUS["ok"], "error": STATUS["fail"], "failed": STATUS["fail"],
               "warning": STATUS["warn"], "degraded": STATUS["warn"], "busy": STATUS["working"],
               "stopped": STATUS["pending"], "idle": STATUS["pending"]})
# Chrome glyphs the helpers draw: role -> (unicode, ASCII).
GLYPHS = {
    "cursor": ("❯", ">"), "ellipsis": ("⋯", "..."), "sep": ("·", "|"), "crumb": ("›", ">"), "times": ("×", "x"),
    "bar_full": ("█", "#"), "bar_empty": ("░", "-"), "thumb": ("█", "#"), "track": ("│", "|"),
    "fold_open": ("▾", "-"), "fold_closed": ("▸", "+"), "skeleton": ("░", "."), "check_on": ("☒", "[x]"),
    "check_off": ("☐", "[ ]"), "radio_on": ("◉", "(*)"), "radio_off": ("◌", "( )"),
}
GAUGE_STYLES = {"block": ("█", "░"), "line": ("━", "─"), "meter": ("▰", "▱")}
EIGHTHS = "▏▎▍▌▋▊▉"
SPARK = "▁▂▃▄▅▆▇█"
SPARK_ASCII = "_.,-~=+#"
TREE_GUIDES = {   # indent -> (mid, last, pipe, blank) unicode, then ASCII
    4: (("├── ", "└── ", "│   ", "    "), ("|-- ", "`-- ", "|   ", "    ")),
    3: (("├─ ", "└─ ", "│  ", "   "), ("|- ", "`- ", "|  ", "   ")),
    2: (("├ ", "└ ", "│ ", "  "), ("| ", "` ", "| ", "  ")),
}
SIZE_CLASSES = ((60, "tiny"), (80, "narrow"), (100, "compact"), (160, "regular"))
REQUIRED_STATES = ("normal", "empty", "busy", "error", "toosmall")
_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_DEFS: dict | None = None


class CanvasError(ValueError):
    """A write that would produce a broken mockup (off canvas, border overwrite, bad token...)."""


# ====================================================================== text measuring and truncation

def width(s: str) -> int:
    """Display width in cells (EAW W/F = 2, combining = 0)."""
    return str_width(s)


def _trunc_chars(chars: list, w: int, side: str, ell) -> list:
    """Truncate a list of (ch, spec) to at most w cells; `ell` = (ellipsis text, spec or None = adjacent spec)."""
    if side not in ("end", "start", "middle"):
        raise CanvasError(f"truncate side must be end|start|middle, got {side!r}")
    total = sum(char_width(c) for c, _ in chars)
    if total <= w:
        return chars
    e_text = ell[0]
    ew = width(e_text)
    if w < ew or w <= 0:                       # no room for the ellipsis: hard cut
        e_text, ew = "", 0

    def head(budget: int) -> list:
        out, used = [], 0
        for c, sp in chars:
            cw = char_width(c)
            if used + cw > budget:
                break
            out.append((c, sp))
            used += cw
        return out

    def tail(budget: int) -> list:
        out, used = [], 0
        for c, sp in reversed(chars):
            cw = char_width(c)
            if used + cw > budget:
                break
            out.insert(0, (c, sp))
            used += cw
        return out

    budget = max(0, w - ew)
    if side == "end":
        h, t = head(budget), []
    elif side == "start":
        h, t = [], tail(budget)
    else:
        h = head(budget - budget // 2)
        t = tail(budget // 2)
    ref = (h[-1] if h else t[0] if t else chars[0])[1]
    mid = [(c, ell[1] if ell[1] is not None else ref) for c in e_text]
    return h + mid + t


def truncate(s: str, w: int, side: str = "end", ellipsis: str = "⋯") -> str:
    """Cut `s` to at most w cells, marking the cut with `ellipsis`: side end ("abc⋯"), start ("⋯xyz", paths) or
    middle ("ab⋯yz", ids). Never pads; see fit()."""
    if w <= 0:
        return ""
    return "".join(c for c, _ in _trunc_chars([(c, None) for c in s], w, side, (ellipsis, None)))


def _pad(chars: list, w: int, align: str) -> list:
    if align not in ("l", "r", "c"):
        raise CanvasError(f"align must be l|r|c, got {align!r}")
    gap = w - sum(char_width(c) for c, _ in chars)
    if gap <= 0:
        return chars
    left = gap if align == "r" else gap // 2 if align == "c" else 0
    return [(" ", None)] * left + chars + [(" ", None)] * (gap - left)


def fit(s: str, w: int, align: str = "l", ellipsis: str = "⋯", side: str = "end") -> str:
    """Truncate `s` to w cells (marked with `ellipsis`, cut at `side`) and pad with spaces; align = l | r | c."""
    if w <= 0:
        return ""
    return "".join(c for c, _ in _pad(_trunc_chars([(c, None) for c in s], w, side, (ellipsis, None)), w, align))


def _as_runs(v, spec=None) -> list:
    """str | (str, spec) | [runs...] | number | None -> [(str, spec)] with `spec` as the default."""
    if v is None:
        return []
    if isinstance(v, (int, float)):
        v = str(v)
    if isinstance(v, str):
        return [(v, spec)]
    if isinstance(v, tuple) and len(v) == 2 and isinstance(v[0], str) and (v[1] is None or isinstance(v[1], str)):
        return [(v[0], v[1] if v[1] is not None else spec)]
    out: list = []
    for item in v:
        out += _as_runs(item, spec)
    return out


def _merge_runs(chars: list) -> list:
    out: list = []
    for c, sp in chars:
        if out and out[-1][1] == sp:
            out[-1] = (out[-1][0] + c, sp)
        else:
            out.append((c, sp))
    return out


def _fit_runs(runs: list, w: int, align: str = "l", side: str = "end", ellipsis: str = "⋯", pad: bool = True) -> list:
    """Like fit() for styled runs: the ellipsis takes the style of the text next to the cut."""
    if w <= 0:
        return []
    chars = [(c, sp) for s, sp in runs for c in s]
    chars = _trunc_chars(chars, w, side, (ellipsis, None))
    return _merge_runs(_pad(chars, w, align) if pad else chars)


def runs_width(runs) -> int:
    return sum(width(s) for s, _ in _as_runs(runs))


def bar(frac: float, w: int) -> tuple[str, str]:
    """(filled, empty) strings of '█' and '░' totalling w cells; frac is clamped to 0..1."""
    n = max(0, min(w, round(frac * w)))
    return "█" * n, "░" * (w - n)


def spark(values, lo: float | None = None, hi: float | None = None, ascii: bool = False) -> str:
    """Sparkline of one cell per value (▁..█, or `_.,-~=+#` with ascii=True); ▁ is the floor."""
    vals = list(values)
    if not vals:
        return ""
    lo = min(vals) if lo is None else lo
    hi = max(vals) if hi is None else hi
    ramp = SPARK_ASCII if ascii else SPARK
    span = (hi - lo) or 1
    return "".join(ramp[max(0, min(7, round((v - lo) / span * 7)))] for v in vals)


def fold_runs(seq, key=None) -> list:
    """Collapse consecutive equal items: [a, a, b] -> [(a, 2), (b, 1)]; `key` picks what "equal" compares."""
    out: list = []
    k = key or (lambda v: v)
    for item in seq:
        if out and k(out[-1][0]) == k(item):
            out[-1] = (out[-1][0], out[-1][1] + 1)
        else:
            out.append((item, 1))
    return out


def times(label: str, n: int) -> str:
    """'Source read failed ×8' for n > 1, the bare label otherwise (× becomes x under glyphs=ascii)."""
    return f"{label} ×{n}" if n > 1 else label


def scroll_range(offset: int, visible: int, total: int) -> str:
    """Visible window as '1-6/21' (1-based, inclusive); '0/0' when empty."""
    if total <= 0:
        return "0/0"
    return f"{offset + 1}-{min(offset + visible, total)}/{total}"


def scroll_pos(index: int, total: int) -> str:
    """Cursor position as '12/90' (index is 0-based)."""
    return f"{index + 1}/{total}" if total > 0 else "0/0"


def chip(text: str, token: str = "status.warning") -> tuple:
    """A run for runs()/band(): ' WARN ' in fg.on-accent on the status/accent fill `token`."""
    return (f" {text} ", f"fg.on-accent on:{token}")


def hint_runs(items, sep: str = "  ", key_spec: str = "keyhint.key bold", desc_spec: str = "keyhint.desc") -> list:
    """Footer hint runs: `key verb` pairs `sep` apart; an item (key, verb, "off") is disabled (fg.faint)."""
    out: list = []
    for i, it in enumerate(items):
        off = len(it) > 2 and it[2] not in (True, None)
        if i:
            out.append((sep, None))
        out.append((it[0], "fg.faint" if off else key_spec))
        out.append((" " + it[1], "fg.faint" if off else desc_spec))
    return out


def tab_runs(items, active: int = 0, numbered: bool = True, active_spec: str = "tab.active.fg bold on:tab.active.bg",
             inactive_spec: str = "tab.inactive.fg") -> list:
    """Tab bar runs: ' 1 Services ' (active on its fill) then ' 2 Logs '. An item is a label or
    (label, badge[, badge_spec]); badges render after the label (counts, `✗ 3`)."""
    out: list = []
    for i, it in enumerate(items):
        label, badge, bspec = (it, None, None) if isinstance(it, str) else (tuple(it) + (None, None))[:3]
        text = f" {i + 1} {label}" if numbered else f" {label}"
        sp = active_spec if i == active else inactive_spec
        out.append((text, sp))
        if badge is not None:
            out.append((f" {badge}", bspec or sp))
        out.append((" ", sp))
    return out


# ====================================================================== geometry

def _parse_size(s, total: int):
    if s is None or s == "*":
        return ("flex", 1)
    if isinstance(s, bool):
        raise CanvasError(f"bad size {s!r}")
    if isinstance(s, int):
        if s < 0:
            raise CanvasError(f"negative size {s}")
        return ("fixed", s)
    if isinstance(s, float):
        if not 0 < s < 1:
            raise CanvasError(f"a float size is a share of the total and must be in (0, 1), got {s}")
        return ("fixed", int(total * s))
    if isinstance(s, str):
        m = re.fullmatch(r"(\d+(?:\.\d+)?)(?:\*|fr)", s.strip())
        if m:
            return ("flex", float(m.group(1)))
    raise CanvasError(f"bad size {s!r}: use an int (cells), a float < 1 (share), '*' or '2*' (flex weight)")


def layout(total: int, sizes, gap: int = 0, what: str = "layout") -> list:
    """Split `total` cells into [(offset, size)]: int = fixed cells, float < 1 = share of total, '*' / 'N*' = flex
    weight sharing what is left (leftover cells go to the first flex items). Raises when fixed parts do not fit."""
    parsed = [_parse_size(s, total) for s in sizes]
    n = len(parsed)
    fixed = sum(v for k, v in parsed if k == "fixed")
    need = fixed + gap * max(0, n - 1)
    rest = total - need
    if rest < 0:
        raise CanvasError(f"{what}: sizes {list(sizes)} with gap {gap} need {need} cells but only {total} are "
                          f"available; shrink a fixed size, make one flexible ('*'), or switch layout below this "
                          f"width (size_class(), layout-archetypes.md §2.1)")
    weights = [v if k == "flex" else 0 for k, v in parsed]
    wt = sum(weights)
    out_sizes = [v if k == "fixed" else 0 for k, v in parsed]
    if wt:
        shares = [int(rest * w_ / wt) if w_ else 0 for w_ in weights]
        left = rest - sum(shares)
        for i, w_ in enumerate(weights):
            if w_ and left > 0:
                shares[i] += 1
                left -= 1
        out_sizes = [s if k == "fixed" else shares[i] for i, (s, (k, _)) in enumerate(zip(out_sizes, parsed))]
    out, off = [], 0
    for s in out_sizes:
        out.append((off, s))
        off += s + gap
    return out


def size_class(cols: int) -> str:
    """layout-archetypes.md §2.1 by width: tiny <60, narrow 60-79, compact 80-99, regular 100-159, wide >=160."""
    for limit, name in SIZE_CLASSES:
        if cols < limit:
            return name
    return "wide"


class Rect:
    """A cell rectangle (x, y, w, h); unpacks like a tuple. `rid` is the region id when a panel() made it."""
    __slots__ = ("x", "y", "w", "h", "rid")

    def __init__(self, x: int, y: int, w: int, h: int, rid: str | None = None):
        self.x, self.y, self.w, self.h, self.rid = int(x), int(y), int(w), int(h), rid

    def __iter__(self):
        return iter((self.x, self.y, self.w, self.h))

    def __eq__(self, other) -> bool:
        try:
            return tuple(self) == tuple(other)
        except TypeError:
            return NotImplemented

    def __hash__(self) -> int:
        return hash(tuple(self))

    def __repr__(self) -> str:
        return f"Rect({self.x}, {self.y}, {self.w}, {self.h}" + (f", rid={self.rid!r})" if self.rid else ")")

    @property
    def right(self) -> int:
        """First column after the rect (exclusive)."""
        return self.x + self.w

    @property
    def bottom(self) -> int:
        """First row after the rect (exclusive)."""
        return self.y + self.h

    def inset(self, left: int = 1, top: int | None = None, right: int | None = None, bottom: int | None = None) -> "Rect":
        """Shrink: inset(1) all sides, inset(2, 0) left/right 2, top/bottom 0, inset(l, t, r, b) each side."""
        top = left if top is None else top
        right = left if right is None else right
        bottom = top if bottom is None else bottom
        return Rect(self.x + left, self.y + top, max(0, self.w - left - right), max(0, self.h - top - bottom), self.rid)

    @property
    def inner(self) -> "Rect":
        """The interior of a box drawn on this rect (1 cell of border on each side)."""
        return self.inset(1)

    def split_h(self, sizes, gap: int = 0) -> list:
        """Side by side (columns, like `tmux -L <name> split-window -h`): split_h([32, "*"]) -> [list rect, detail rect]."""
        return [Rect(self.x + o, self.y, s, self.h) for o, s in layout(self.w, sizes, gap, f"split_h of {self!r}")]

    def split_v(self, sizes, gap: int = 0) -> list:
        """Stacked (rows): split_v([1, "*", 1, 1]) -> header, body, message line, keybar."""
        return [Rect(self.x, self.y + o, self.w, s) for o, s in layout(self.h, sizes, gap, f"split_v of {self!r}")]

    def take(self, n: int, side: str = "top") -> tuple:
        """(taken, rest): n rows from top/bottom or n columns from left/right."""
        if side == "top":
            return Rect(self.x, self.y, self.w, n), Rect(self.x, self.y + n, self.w, self.h - n)
        if side == "bottom":
            return Rect(self.x, self.bottom - n, self.w, n), Rect(self.x, self.y, self.w, self.h - n)
        if side == "left":
            return Rect(self.x, self.y, n, self.h), Rect(self.x + n, self.y, self.w - n, self.h)
        if side == "right":
            return Rect(self.right - n, self.y, n, self.h), Rect(self.x, self.y, self.w - n, self.h)
        raise CanvasError(f"take side must be top|bottom|left|right, got {side!r}")

    def center(self, w: int, h: int) -> "Rect":
        """A w x h rect centered in this one (clamped to it)."""
        w, h = min(w, self.w), min(h, self.h)
        return Rect(self.x + (self.w - w) // 2, self.y + (self.h - h) // 2, w, h)

    def row(self, i: int) -> "Rect":
        """The i-th row as a 1-high rect (negative counts from the bottom)."""
        return Rect(self.x, (self.y + i) if i >= 0 else (self.bottom + i), self.w, 1)


def _where(args, need_h: bool = True) -> Rect:
    """Rect | (x, y, w, h) | x, y, w, h [| x, y, w with need_h=False] -> Rect (h may be -1 = unknown)."""
    if len(args) == 1:
        a = args[0]
        if isinstance(a, Rect):
            return a
        args = tuple(a)
    if len(args) == 4:
        return Rect(*args)
    if len(args) == 3 and not need_h:
        return Rect(args[0], args[1], args[2], -1)
    raise CanvasError(f"expected a Rect, an (x, y, w, h) tuple or x, y, w, h; got {args!r}")


# ====================================================================== columns, tree nodes

class Col:
    """A table column. width = cells (None = flexible, sharing the rest by `flex` weight); align l|r|c;
    truncate end|start|middle (paths: start; ids: middle); spec = default style of its cells; sel = style of
    neutral text on the selected row (default 'selection.fg'); min = smallest flexible width before the table
    raises; hide_below = drop the column when the table is narrower than this (responsive tables);
    ascii_width = width under caps glyphs=ascii (status glyphs become [ok] [x] [!]: give them 4 cells, V9)."""

    def __init__(self, name: str | None = None, width: int | None = None, align: str = "l", truncate: str = "end",
                 spec: str | None = "fg.default", sel: str | None = None, flex: float = 1, min: int = 1,
                 hide_below: int | None = None, header_align: str | None = None, ascii_width: int | None = None):
        if align not in ("l", "r", "c"):
            raise CanvasError(f"Col {name!r}: align must be l|r|c, got {align!r}")
        if truncate not in ("end", "start", "middle"):
            raise CanvasError(f"Col {name!r}: truncate must be end|start|middle, got {truncate!r}")
        self.name, self.width, self.align, self.truncate = name, width, align, truncate
        self.spec, self.sel, self.flex, self.min = spec, sel, flex, min
        self.hide_below, self.header_align, self.ascii_width = hide_below, header_align, ascii_width

    def __repr__(self) -> str:
        return f"Col({self.name!r}, {self.width!r})"


class Node:
    """A tree node: label (str or runs), children, open (False = folded, children hidden)."""

    def __init__(self, label, children=(), open: bool = True):
        self.label, self.children, self.open = label, [_node(c) for c in children], open


def _node(n) -> Node:
    """Node | (label, [children]) | (label, [children], open) | label (str or runs) -> Node."""
    if isinstance(n, Node):
        return n
    if isinstance(n, tuple) and len(n) in (2, 3) and isinstance(n[1], list):
        return Node(n[0], n[1], n[2] if len(n) > 2 else True)
    return Node(n)


def tree_rows(nodes, indent: int = 4, ascii: bool = False, folds: bool = False) -> list:
    """Flatten a tree to [(prefix, label, node, depth)] with guides ├── └── │ (V4; indent 4, 3 or 2 cells per
    level; ascii=True: |-- `-- |). Top-level nodes carry no guide. folds=True prefixes ▾/▸ (open/folded) and
    two spaces on leaves; folded nodes hide their children."""
    if indent not in TREE_GUIDES:
        raise CanvasError(f"tree indent must be one of {sorted(TREE_GUIDES)}, got {indent}")
    mid, last, pipe, blank = TREE_GUIDES[indent][1 if ascii else 0]
    fo, fc = (GLYPHS["fold_open"][1], GLYPHS["fold_closed"][1]) if ascii else (GLYPHS["fold_open"][0], GLYPHS["fold_closed"][0])
    out: list = []

    def walk(items, prefix: str, depth: int) -> None:
        items = [_node(n) for n in items]
        for i, n in enumerate(items):
            is_last = i == len(items) - 1
            pre = "" if depth == 0 else prefix + (last if is_last else mid)
            if folds:
                pre += (fo if n.open else fc) + " " if n.children else "  "
            out.append((pre, n.label, n, depth))
            if n.children and n.open:
                walk(n.children, "" if depth == 0 else prefix + (blank if is_last else pipe), depth + 1)

    walk(nodes, "", 0)
    return out


# ====================================================================== specs

def _defs() -> dict:
    global _DEFS
    if _DEFS is None:
        _DEFS = load_token_defs()
    return _DEFS


def _suggest(tok: str) -> str:
    near = difflib.get_close_matches(tok, list(_defs()) + list(ATTRS), n=2, cutoff=0.6)
    return f"; did you mean {' or '.join(map(repr, near))}?" if near else "; tokens are listed in references/themes/_tokens.json"


# A cell style is (fg, bg, attrs) with attrs a tuple in ATTRS order.
Style = tuple


def parse_spec(spec: str | None) -> Style:
    """'fg.muted bold on:selection.bg' -> (fg, bg, attrs); raises CanvasError on anything the linter rejects."""
    fg = bg = None
    attrs: list[str] = []
    defs = _defs()
    for item in (spec or "").split():
        if item.startswith("#") or item.startswith("on:#"):
            raise CanvasError(f"raw hex color {item!r} not allowed; use a token from themes/_tokens.json")
        if item.startswith("on:"):
            tok = item[3:]
            if tok not in defs:
                raise CanvasError(f"unknown token {tok!r} in {item!r}{_suggest(tok)}")
            if tok == "fg.on-accent":
                raise CanvasError("'fg.on-accent' is chip text, not a fill: use 'fg.on-accent on:status.warning'")
            bg = tok
        elif item in ATTRS:
            attrs.append(item)
        elif item in defs:
            if defs[item]["kind"] != "fg":
                raise CanvasError(f"{item!r} is a bg token; write on:{item}")
            fg = item
        else:
            raise CanvasError(f"unknown token or attribute {item!r}{_suggest(item)}")
    return fg, bg, tuple(a for a in ATTRS if a in attrs)


def _spec_str(st: Style) -> str:
    fg, bg, attrs = st
    return " ".join(([fg] if fg else []) + list(attrs) + ([f"on:{bg}"] if bg else []))


def _restyle(spec: str | None, over: str | None) -> str | None:
    """`over`'s fg replaces spec's fg, attributes are united, bg from over else spec."""
    if not over:
        return spec
    f1, b1, a1 = parse_spec(spec)
    f2, b2, a2 = parse_spec(over)
    return _spec_str((f2 or f1, b2 or b1, tuple(a for a in ATTRS if a in a1 or a in a2))) or None


def _fg(spec: str | None):
    return parse_spec(spec)[0]


class _Cell:
    __slots__ = ("ch", "fg", "bg", "attrs", "cont")

    def __init__(self) -> None:
        self.ch, self.fg, self.bg, self.attrs, self.cont = " ", None, None, (), False

    def reset(self, bg: str | None = None) -> None:
        self.ch, self.fg, self.bg, self.attrs, self.cont = " ", None, bg, (), False


def is_junction(ch: str) -> bool:
    """A box-drawing tee or cross (3+ directions), any weight: ├ ┤ ┬ ┴ ┼ ┝ ╟ ╦ ..."""
    if not ch or not 0x2500 <= ord(ch[0]) <= 0x257F:
        return False
    words = set(unicodedata.name(ch[0], "").replace("-", " ").split())
    dirs = {d for d, w in (("U", "UP"), ("D", "DOWN"), ("L", "LEFT"), ("R", "RIGHT")) if w in words}
    if "VERTICAL" in words:
        dirs |= {"U", "D"}
    if "HORIZONTAL" in words:
        dirs |= {"L", "R"}
    return len(dirs) >= 3


# ====================================================================== canvas

class Canvas:
    def __init__(self, cols: int, rows: int, title: str | None = None, state: str | None = None,
                 theme: str | None = None, caps: str | None = None, fallback: bool = False):
        if cols < 1 or rows < 1:
            raise CanvasError(f"bad canvas size {cols}x{rows}")
        self.cols, self.rows = cols, rows
        self.title, self.state, self.theme = title, state, theme
        self.caps: Caps = Caps()
        if caps:
            self.caps, errs = parse_caps(caps)
            if errs:
                raise CanvasError("bad caps: " + "; ".join(errs))
        self.fallback = fallback
        self.cells = [[_Cell() for _ in range(cols)] for _ in range(rows)]
        self.notes: list[str] = []
        self._regions: list[tuple[str, str, int, int, int, int, str]] = []
        self._prot: set[tuple[int, int]] = set()   # border cells: text onto them raises
        self._owner: dict[tuple[int, int], str] = {}

    # ------------------------------------------------------------------ caps-aware basics
    @property
    def rect(self) -> Rect:
        """The whole canvas as a Rect, the root of split_h / split_v layouts."""
        return Rect(0, 0, self.cols, self.rows)

    @property
    def size_class(self) -> str:
        return size_class(self.cols)

    @property
    def is_ascii(self) -> bool:
        """True under caps glyphs=ascii (helpers then draw V9 ASCII glyphs)."""
        return self.caps.glyphs == "ascii"

    def g(self, role: str) -> str:
        """The glyph for a chrome or status role under the caps profile: g("cursor") -> ❯ or >, g("ok") -> ✓ or [ok]."""
        if role in STATUS:
            return STATUS[role][1 if self.is_ascii else 0]
        if role in GLYPHS:
            return GLYPHS[role][1 if self.is_ascii else 0]
        raise CanvasError(f"unknown glyph role {role!r}; known: {' '.join(sorted(set(STATUS) | set(GLYPHS)))}")

    def status(self, role: str) -> tuple:
        """(glyph, token) of a V5 status role under the caps profile: status("warn") -> ("▲", "status.warning")."""
        if role not in STATUS:
            raise CanvasError(f"unknown status role {role!r}; known: {' '.join(STATUS)}")
        return self.g(role), STATUS[role][2]

    def adapt(self, spec: str | None) -> str | None:
        """Drop the attributes of `spec` that the caps profile does not allow (what helpers do to their defaults)."""
        if not spec:
            return spec
        fg, bg, attrs = parse_spec(spec)
        return _spec_str((fg, bg, tuple(a for a in attrs if a in self.caps.attrs))) or None

    def ascii(self, s: str) -> str:
        """Replace non-ASCII glyphs by their V9 fallback, accented letters by their base letter (É -> E); unknown
        glyphs are kept, so the caps check names them."""
        def one(ch: str) -> str:
            if ord(ch) < 128:
                return ch
            fb = ascii_fallback(ch)
            if fb:
                return fb
            base = unicodedata.normalize("NFKD", ch).encode("ascii", "ignore").decode()
            return base or ch
        return "".join(one(ch) for ch in s)

    def _content(self, s: str) -> str:
        return self.ascii(s) if self.is_ascii else s

    def _runs_content(self, runs: list) -> list:
        return [(self._content(s), sp) for s, sp in runs] if self.is_ascii else runs

    # ------------------------------------------------------------------ writing
    def _check_cell(self, x: int, y: int, what: str) -> None:
        if not (0 <= x < self.cols and 0 <= y < self.rows):
            raise CanvasError(f"{what} at ({x},{y}) is outside the {self.cols}x{self.rows} canvas "
                              f"(x 0..{self.cols - 1}, y 0..{self.rows - 1})")

    def _free_span(self, x: int, y: int) -> tuple[int, int]:
        """The contiguous unprotected cells of row y at or after x (start, end inclusive); (x, x-1) if none."""
        a = x
        while a < self.cols and (a, y) in self._prot:
            a += 1
        b = a
        while b + 1 < self.cols and (b + 1, y) not in self._prot:
            b += 1
        return (a, b) if a < self.cols else (x, x - 1)

    def _clip_limit(self, x: int, y: int) -> int:
        """Cells available from x before the next border cell or the canvas edge."""
        xx = x
        while xx < self.cols and (xx, y) not in self._prot:
            xx += 1
        return xx - x

    def text(self, x: int, y: int, s: str, spec: str | None = None, force: bool = False, clip=False) -> int:
        """Write one line of text starting at (x, y); returns the x after the last cell written.

        clip=True truncates s (with ⋯) to fit before the next border cell or the canvas edge; clip=N to N cells."""
        fg, bg, attrs = parse_spec(spec)
        if self.fallback:
            attrs = tuple(a for a in attrs if a in self.caps.attrs)
        if "\n" in s or any(ord(c) < 32 or ord(c) == 127 for c in s):
            raise CanvasError(f"control character in text {s!r}; text() writes one row, call it once per line")
        if self.fallback and self.is_ascii:
            s = self.ascii(s)
        if clip is not False and clip is not None:
            if not (0 <= y < self.rows) or not 0 <= x < self.cols:
                self._check_cell(x, y, f"text {s!r}")
            limit = self._clip_limit(x, y) if clip is True else min(int(clip), self.cols - x)
            s = truncate(s, limit, ellipsis=self.g("ellipsis"))
        self._check_caps(x, y, s, attrs)
        w = width(s)
        if w == 0:
            return x
        if not (0 <= y < self.rows):
            raise CanvasError(f"text {s!r} at row y={y} is outside the canvas rows 0..{self.rows - 1}")
        if x < 0 or x + w > self.cols:
            avail = self.cols - x
            raise CanvasError(f"text {s!r} is {w} cells but only {max(0, avail)} fit at x={x}, y={y} on the "
                              f"{self.cols}x{self.rows} canvas; shorten it with fit(s, {max(0, avail)}) or "
                              f"text(..., clip=True)")
        if not force:
            for xx in range(x, x + w):
                if (xx, y) in self._prot:
                    a, b = self._free_span(x, y) if (x, y) not in self._prot else self._free_span(xx + 1, y)
                    owner = self._owner.get((xx, y), "a border")
                    free = f"the free cells there are x={a}..{b} ({b - a + 1} cells)" if b >= a else "no free cells follow"
                    raise CanvasError(f"text {s!r} (x={x}..{x + w - 1}, y={y}) overwrites {owner} at ({xx},{y}); "
                                      f"{free}: start inside them or shorten with fit()/clip=True; "
                                      f"force=True overrides")
        xx = x
        for ch in s:
            cw = char_width(ch)
            if cw == 0:
                prev = xx - 1
                while prev > 0 and self.cells[y][prev].cont:
                    prev -= 1
                self.cells[y][max(prev, 0)].ch += ch
                continue
            self._put(xx, y, ch, cw, fg, bg, attrs)
            xx += cw
        return xx

    def _check_caps(self, x: int, y: int, s: str, attrs: tuple) -> None:
        """Raise when a write violates the capability profile (`caps=`)."""
        caps = self.caps
        for a in attrs:
            if a not in caps.attrs:
                raise CanvasError(f"attribute {a!r} at ({x},{y}) is not in caps attrs={','.join(caps.attrs) or 'none'}; "
                                  f"drop it or carry the emphasis with an allowed attribute or a glyph "
                                  f"(c.adapt(spec) strips it)")
        if caps.glyphs == "ascii":
            for ch in s:
                if ord(ch) > 127:
                    fb = ascii_fallback(ch)
                    raise CanvasError(f"glyph {ch!r} (U+{ord(ch):04X}) in {s!r} at ({x},{y}) violates caps glyphs=ascii"
                                      + (f"; V9 ASCII fallback: {fb!r}" if fb else "")
                                      + ("; use border='ascii' for boxes" if ch in "╭╮╰╯┌┐└┘─│" else "")
                                      + "; Canvas(..., fallback=True) substitutes fallbacks automatically")
        elif "glyphs" in caps.given and caps.glyphs == "unicode":
            for ch in s:
                if unicodedata.category(ch) == "Co" or ord(ch) >= 0xF0000:
                    raise CanvasError(f"private-use glyph U+{ord(ch):04X} in {s!r} at ({x},{y}) violates caps glyphs=unicode; "
                                      "declare glyphs=nerd to allow it")

    def _put(self, x: int, y: int, ch: str, cw: int, fg, bg, attrs) -> None:
        row = self.cells[y]
        if row[x].cont and x > 0:                # cutting a wide glyph's right half: blank its left half
            row[x - 1].ch, row[x - 1].cont = " ", False
        end = x + cw - 1
        if end + 1 < self.cols and row[end + 1].cont:   # cutting its left half: blank the orphaned right half
            row[end + 1].ch, row[end + 1].cont = " ", False
        cell = row[x]
        cell.ch, cell.fg, cell.attrs, cell.cont = ch, fg, attrs, False
        if bg:
            cell.bg = bg
        if cw == 2:
            nxt = row[x + 1]
            nxt.ch, nxt.fg, nxt.attrs, nxt.cont = "", fg, attrs, True
            if bg:
                nxt.bg = bg

    def runs(self, x: int, y: int, parts, force: bool = False) -> int:
        """Write [(text, spec), ...] one after another; returns the end x."""
        for s, spec in parts:
            x = self.text(x, y, s, spec, force=force)
        return x

    def rtext(self, x_end: int, y: int, s: str, spec: str | None = None, force: bool = False) -> int:
        """Right-aligned: the text ends just before column x_end (exclusive). Returns its start x."""
        if self.fallback and self.is_ascii:
            s = self.ascii(s)
        start = x_end - width(s)
        self.text(start, y, s, spec, force=force)
        return start

    def rruns(self, x_end: int, y: int, parts, force: bool = False) -> int:
        """Right-aligned runs ending just before x_end (exclusive). Returns their start x."""
        parts = self._runs_content(list(parts)) if (self.fallback and self.is_ascii) else list(parts)
        start = x_end - sum(width(s) for s, _ in parts)
        self.runs(start, y, parts, force=force)
        return start

    def fill(self, x: int, y: int, w: int, h: int, spec: str) -> None:
        """Set the background of a rectangle ('on:statusbar.bg' or a bare bg token); glyphs are kept."""
        spec = spec.strip()
        if spec and " " not in spec and spec in _defs() and _defs()[spec]["kind"] == "bg":
            spec = "on:" + spec
        fg, bg, attrs = parse_spec(spec)
        if bg is None or fg or attrs:
            raise CanvasError(f"fill needs a background spec like 'on:selection.bg', got {spec!r}")
        if w < 0 or h < 0 or x < 0 or y < 0 or x + w > self.cols or y + h > self.rows:
            raise CanvasError(f"fill {x},{y},{w},{h} exceeds the {self.cols}x{self.rows} canvas")
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.cells[yy][xx].bg = bg

    def clear(self, x: int, y: int, w: int, h: int, bg: str | None = None) -> None:
        """Reset a rectangle to blank cells (optionally on a fill) and drop its border protection."""
        if bg and not (bg in _defs() or bg.startswith("on:")):
            raise CanvasError(f"unknown token {bg!r}{_suggest(bg)}")
        bg = bg[3:] if bg and bg.startswith("on:") else bg
        if w < 0 or h < 0 or x < 0 or y < 0 or x + w > self.cols or y + h > self.rows:
            raise CanvasError(f"clear {x},{y},{w},{h} exceeds the {self.cols}x{self.rows} canvas")
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.cells[yy][xx].reset(bg)
                self._prot.discard((xx, yy))
                self._owner.pop((xx, yy), None)

    # ------------------------------------------------------------------ lines and boxes
    def _line(self, cells: list[tuple[int, int]], ch: str, spec: str, force: bool, what: str,
              joins: frozenset = frozenset()) -> None:
        if width(ch) != 1:
            raise CanvasError(f"{what}: ch must be one single-width glyph, got {ch!r}")
        for xx, yy in cells:
            self._check_cell(xx, yy, what)
            if not force and (xx, yy) in self._prot and (xx, yy) not in joins:
                raise CanvasError(f"{what} overwrites {self._owner.get((xx, yy), 'a border')} at ({xx},{yy}); "
                                  f"stop one cell short, or join it with ends=('├', '┤') / ('┬', '┴') when it "
                                  f"meets a box side; force=True overrides")
        for xx, yy in cells:
            self.text(xx, yy, ch, spec, force=True)
            self._prot.add((xx, yy))
            self._owner.setdefault((xx, yy), f"the {what} at {cells[0][0]},{cells[0][1]}")

    @staticmethod
    def _joins(cells: list[tuple[int, int]], ends) -> frozenset:
        """End cells of a line that may sit on a border because their `ends` glyph is a tee/cross junction."""
        if not ends or len(cells) < 2:
            return frozenset()
        return frozenset(c for c, g in ((cells[0], ends[0]), (cells[-1], ends[1])) if is_junction(g))

    def hline(self, x: int, y: int, w: int, spec: str = "border.default", ch: str = "─", ends=None,
              force: bool = False) -> None:
        """Horizontal rule of w cells; ends=("├", "┤") replaces the first/last glyph (joins to a box side)."""
        if self.is_ascii and self.fallback:
            ch = self.ascii(ch)
            ends = tuple(self.ascii(e) for e in ends) if ends else ends
        cells = [(x + i, y) for i in range(w)]
        joins = self._joins(cells, ends)
        if ends and self.is_ascii and all(e == "+" for e in ends):
            joins = frozenset((cells[0], cells[-1])) if len(cells) >= 2 else joins
        self._line(cells, ch, spec, force, "hline", joins)
        if ends and w >= 2:
            self.text(x, y, ends[0], spec, force=True)
            self.text(x + w - 1, y, ends[1], spec, force=True)

    def vline(self, x: int, y: int, h: int, spec: str = "border.default", ch: str = "│", ends=None,
              force: bool = False) -> None:
        """Vertical rule of h cells; ends=("┬", "┴") replaces the first/last glyph."""
        if self.is_ascii and self.fallback:
            ch = self.ascii(ch)
            ends = tuple(self.ascii(e) for e in ends) if ends else ends
        cells = [(x, y + i) for i in range(h)]
        joins = self._joins(cells, ends)
        if ends and self.is_ascii and all(e == "+" for e in ends):
            joins = frozenset((cells[0], cells[-1])) if len(cells) >= 2 else joins
        self._line(cells, ch, spec, force, "vline", joins)
        if ends and h >= 2:
            self.text(x, y, ends[0], spec, force=True)
            self.text(x, y + h - 1, ends[1], spec, force=True)

    def box(self, x: int, y: int, w: int, h: int, title: str | None = None, border: str = "rounded",
            spec: str = "border.default", title_spec: str = "fg.title bold", region=None,
            title_right: str | None = None, bottom: str | None = None, bottom_right: str | None = None,
            fill: str | None = None, clear: bool = False, force: bool = False) -> None:
        """Draw a bordered box (w x h includes the border). Titles sit between ─ segments, never at a corner.

        region=(id, role) records `#! region id role x,y,w,h <title>` (a bare role picks the next free id).
        fill = bg token for the whole box; clear=True first blanks the area (a modal over existing content).
        Edge texts use title_spec (title) or fg.muted (title_right, bottom, bottom_right).
        """
        if border not in BORDERS:
            raise CanvasError(f"unknown border {border!r}; valid: {' '.join(BORDERS)}")
        if self.fallback:
            spec, title_spec = self.adapt(spec) or "", self.adapt(title_spec) or ""
        if self.fallback and self.is_ascii:
            border = "ascii"
            title, title_right, bottom, bottom_right = (self.ascii(t) if t else t for t in
                                                        (title, title_right, bottom, bottom_right))
        corners, hz, vt = BORDERS[border]
        if w < 2 or h < 2 or x < 0 or y < 0 or x + w > self.cols or y + h > self.rows:
            raise CanvasError(f"box {x},{y},{w},{h} does not fit the {self.cols}x{self.rows} canvas "
                              f"(needs x+w <= {self.cols}, y+h <= {self.rows}, w and h >= 2)")
        perim = [(xx, yy) for yy in range(y, y + h) for xx in range(x, x + w)
                 if yy in (y, y + h - 1) or xx in (x, x + w - 1)]
        if not force and not clear:
            for p in perim:
                if p in self._prot:
                    raise CanvasError(f"box {x},{y},{w},{h} overwrites {self._owner.get(p, 'another border')} at {p}; "
                                      f"boxes may touch but not share cells (place it at the next column/row), "
                                      f"clear=True draws it over (modals), force=True overrides")
        edge_texts = [(title, y, "l", title_spec), (title_right, y, "r", "fg.muted"),
                      (bottom, y + h - 1, "l", "fg.muted"), (bottom_right, y + h - 1, "r", "fg.muted")]
        for row_y in (y, y + h - 1):             # fail before drawing anything
            used = [width(f" {t.strip()} ") for t, yy, _, _ in edge_texts if t is not None and yy == row_y]
            if used and sum(used) + (len(used) - 1) > w - 4:
                raise CanvasError(f"edge text on row {row_y} is too long for a box of width {w} "
                                  f"(titles need {sum(used) + len(used) - 1} of {w - 4} cells); shorten it, "
                                  f"e.g. truncate(title, {max(0, w - 6 - sum(used[1:]) - len(used) + 1)})")
        parse_spec(spec)
        parse_spec(title_spec)
        self._check_caps(x, y, corners + hz + vt, parse_spec(spec)[2])     # caps violations fail before drawing too
        for t, yy, _, sp in edge_texts:
            if t is not None:
                self._check_caps(x, yy, t, parse_spec(sp)[2])
        if clear:
            self.clear(x, y, w, h, fill)
        elif fill:
            self.fill(x, y, w, h, fill)
        for xx in range(x, x + w):
            self.text(xx, y, corners[0] if xx == x else corners[1] if xx == x + w - 1 else hz, spec, force=True)
            self.text(xx, y + h - 1, corners[2] if xx == x else corners[3] if xx == x + w - 1 else hz, spec, force=True)
        for yy in range(y + 1, y + h - 1):
            self.text(x, yy, vt, spec, force=True)
            self.text(x + w - 1, yy, vt, spec, force=True)
        self._prot.update(perim)
        label = f"the border of box {title.strip()!r} ({x},{y},{w},{h})" if title else f"the border of box {x},{y},{w},{h}"
        for p in perim:
            self._owner[p] = label
        for t, yy, side, sp in edge_texts:
            if t is None:
                continue
            s_ = f" {t.strip()} "
            self.text(x + 2 if side == "l" else x + w - 2 - width(s_), yy, s_, sp, force=True)
        if region:
            self._add_region(region, x, y, w, h, (title or "").strip())

    # ------------------------------------------------------------------ regions, notes
    def _add_region(self, region, x: int, y: int, w: int, h: int, title: str = "") -> str | None:
        """region = (id, role) | role (next free id) | None. Returns the id."""
        if not region:
            return None
        rid, role = region if isinstance(region, (tuple, list)) else (self._next_id(), region)
        self.region(rid, role, x, y, w, h, title)
        return rid

    def region(self, rid: str, role: str, x: int, y: int, w: int, h: int, title: str | None = None) -> None:
        """Record `#! region rid role x,y,w,h [title]` (ground truth for audits)."""
        if not re.fullmatch(r"r[0-9]+", rid):
            raise CanvasError(f"region id {rid!r} must match r<N> (e.g. 'r{len(self._regions) + 1}')")
        if role not in known_roles():
            near = difflib.get_close_matches(role, known_roles(), n=2)
            raise CanvasError(f"unknown region role {role!r}" + (f"; did you mean {' or '.join(near)}?" if near else "")
                              + f"; valid: {' '.join(known_roles())}")
        if any(r[0] == rid for r in self._regions):
            raise CanvasError(f"duplicate region id {rid!r}; pass a bare role (region='list') to get the next free id")
        if w < 1 or h < 1 or x < 0 or y < 0 or x + w > self.cols or y + h > self.rows:
            raise CanvasError(f"region {rid} bbox {x},{y},{w},{h} outside the {self.cols}x{self.rows} canvas")
        self._regions.append((rid, role, x, y, w, h, title or ""))

    def _next_id(self) -> str:
        used = {r[0] for r in self._regions}
        n = 1
        while f"r{n}" in used:
            n += 1
        return f"r{n}"

    def focus(self, rid: str) -> None:
        """Record the focused pane (`#! focus <rid>`), the ground truth audits score state against."""
        self._focus = rid

    def selected(self, rid: str, row: int) -> None:
        """Record the selected row (`#! selected <rid> <row>`), 0-based inside the region's interior."""
        self._selected = (rid, int(row))

    def selected_at(self, rid: str, y: int) -> None:
        """Record the selected row from its canvas row y (interior of a box region starts below its border)."""
        reg = next((r for r in self._regions if r[0] == rid), None)
        if reg is None:
            raise CanvasError(f"selected_at: no region {rid!r} yet; draw the panel (or region) first")
        _, _, rx, ry, _, _, _ = reg
        self.selected(rid, y - ry - (1 if (rx, ry) in self._prot else 0))

    def note(self, text: str) -> None:
        """Add a `#! note:` header line (free text, one line)."""
        if "\n" in text:
            raise CanvasError("a note is a single line; call note() once per line")
        self.notes.append(text.strip())

    # ------------------------------------------------------------------ widgets
    def panel(self, *where, title: str | None = None, role: str = "panel", focus: bool = False, rid: str | None = None,
              border: str = "rounded", spec: str | None = None, **box_kw) -> Rect:
        """A titled box that records its `#! region` (and `#! focus` when focus=True); returns the interior Rect
        (with .rid) to draw into. spec defaults to border.focus / border.default by focus. Other box() keywords
        (title_right, bottom, bottom_right, fill, clear) pass through. Usage: panel(rect, "Title", ...)."""
        if len(where) >= 2 and isinstance(where[-1], str) and title is None:
            where, title = where[:-1], where[-1]
        r = _where(where)
        if self.is_ascii:
            border = "ascii"
            title = self._content(title) if title else title
            box_kw = {k: (self._content(v) if isinstance(v, str) and k in ("title_right", "bottom", "bottom_right") else v)
                      for k, v in box_kw.items()}
        box_kw.setdefault("title_spec", self.adapt("fg.title bold"))
        region = (rid, role) if rid else role
        n0 = len(self._regions)
        self.box(r.x, r.y, r.w, r.h, title, border=border, spec=spec or ("border.focus" if focus else "border.default"),
                 region=region, **box_kw)
        got = self._regions[n0][0]
        if focus:
            self.focus(got)
        return Rect(r.x + 1, r.y + 1, r.w - 2, r.h - 2, got)

    def band(self, y: int, left=(), right=(), *, bg: str | None = "statusbar.bg", x: int = 0, w: int | None = None,
             pad: int = 1, region=None, min_gap: int = 1) -> tuple[int, int]:
        """A 1-row band (header, status line): runs `left` from x+pad, runs `right` ending at x+w-pad, on `bg`
        (None = no fill). left/right: str | (str, spec) | [runs]. Returns (end of left, start of right)."""
        w = self.cols - x if w is None else w
        if bg:
            self.fill(x, y, w, 1, bg)
        lr = self._runs_content(_as_runs(left))
        rr = self._runs_content(_as_runs(right))
        lw, rw = runs_width(lr), runs_width(rr)
        if lw + rw + min_gap > w - 2 * pad:
            raise CanvasError(f"band row {y}: left ({lw} cells) + right ({rw} cells) + gap {min_gap} exceed the "
                              f"{w - 2 * pad} usable cells; shorten a run (fit/truncate) or drop the right part "
                              f"below this width (size_class())")
        end = self.runs(x + pad, y, lr)
        start = x + w - pad - rw
        self.runs(start, y, rr)
        self._add_region(region, x, y, w, 1)
        return end, start

    def tabs(self, x: int, y: int, items, active: int = 0, numbered: bool = True) -> int:
        """Tab bar at (x, y): ' 1 Services ' active on tab.active.bg, others in tab.inactive.fg; items are labels or
        (label, badge[, badge_spec]). Returns the end x."""
        runs = tab_runs(items, active, numbered, self.adapt("tab.active.fg bold on:tab.active.bg"))
        return self.runs(x, y, self._runs_content(runs))

    def message(self, y: int, status: str | None, text: str, meta: str | None = None, x: int = 1,
                w: int | None = None, spec: str = "fg.default") -> int:
        """Message line: `✓ deployed v2.4.1 · 2m ago` = status glyph + text + faint meta (age, source). status is
        a V5 role (ok, warn, fail, info, working...) or None. Returns the end x."""
        runs = []
        if status:
            g, tok = self.status(status)
            runs.append((g, tok))
        runs.append(((" " if status else "") + text, spec))
        if meta:
            runs.append((f" {self.g('sep')} {meta}", "fg.faint"))
        runs = self._runs_content(runs)
        w = self.cols - x - 1 if w is None else w
        return self.runs(x, y, _fit_runs(runs, w, ellipsis=self.g("ellipsis"), pad=False))

    def chip(self, x: int, y: int, text: str, token: str = "status.warning") -> int:
        """' WARN ' in fg.on-accent on the `token` fill (16 colors: slot + reverse). Returns the end x."""
        s, sp = chip(self._content(text), token)
        return self.text(x, y, s, sp)

    def kv(self, x: int, y: int, pairs, key_w: int | None = None, w: int | None = None, key_spec: str = "fg.muted",
           val_spec: str = "fg.default") -> int:
        """Field list: keys in a fixed-width column, values (str | (str, spec) | runs) after it; None = blank row.
        w clips values to x+w. Returns the y after the last row."""
        keys = [p[0] for p in pairs if p]
        key_w = max((width(k) for k in keys), default=0) + 2 if key_w is None else key_w
        w = self.cols - x if w is None else w
        for p in pairs:
            if p:
                k, v = p
                self.text(x, y, fit(self._content(k), key_w, ellipsis=self.g("ellipsis")), key_spec)
                vr = self._runs_content(_as_runs(v, val_spec))
                self.runs(x + key_w, y, _fit_runs(vr, w - key_w, ellipsis=self.g("ellipsis"), pad=False))
            y += 1
        return y

    def lines(self, x: int, y: int, items, spec: str = "fg.default", w: int | None = None) -> int:
        """Several rows of text from (x, y), one item per row (str | (str, spec) | runs; "" or None = blank row),
        each clipped with ⋯ to w cells (default: up to the next border). Returns the y after the last row."""
        for it in items:
            runs = self._runs_content(_as_runs(it, spec))
            if runs:
                lim = self._clip_limit(x, y) if w is None else w
                self.runs(x, y, _fit_runs(runs, lim, ellipsis=self.g("ellipsis"), pad=False))
            y += 1
        return y

    def gauge(self, x: int, y: int, w: int, value: float, label="pct", label_w: int = 5, ramp=None,
              thresholds=(0.5, 0.8), track: str = "fg.faint", label_spec: str = "fg.default", style: str = "block",
              smooth: bool = False) -> int:
        """Bar + number in w cells: the bar takes w - label_w, the label (default the percentage) is right-aligned
        in label_w. Fill = floor(value * bar width) (never overstates); color from ramp tokens by thresholds
        (default ramp.low < 0.5 <= ramp.mid < 0.8 <= ramp.high) or a single token. style block|line|meter;
        smooth=True adds a partial eighth cell. ASCII caps: # and -. Returns the end x."""
        v = max(0.0, min(1.0, float(value)))
        lab = f"{round(v * 100)}%" if label == "pct" else (label or "")
        lw = label_w if label else 0
        bw = w - lw
        if bw < 1:
            raise CanvasError(f"gauge at ({x},{y}): width {w} leaves no room for the bar after a {lw}-cell label; "
                              f"widen it or pass label_w smaller / label=None")
        ramp = ramp or ("ramp.low", "ramp.mid", "ramp.high")
        if isinstance(ramp, str):
            tok = ramp
        else:
            tok = ramp[0] if v < thresholds[0] else ramp[1] if v < thresholds[1] or len(ramp) < 3 else ramp[2]
        if style not in GAUGE_STYLES:
            raise CanvasError(f"gauge style must be one of {' '.join(GAUGE_STYLES)}, got {style!r}")
        full_g, empty_g = ("#", "-") if self.is_ascii else GAUGE_STYLES[style]
        eighths = int(v * bw * 8 + 1e-9)
        n = eighths // 8
        part = ""
        if smooth and not self.is_ascii and eighths % 8 and n < bw:
            part = EIGHTHS[eighths % 8 - 1]
        filled = full_g * n + part
        empty = empty_g * (bw - n - (1 if part else 0))
        xx = self.text(x, y, filled, tok) if filled else x
        if empty:
            self.text(xx, y, empty, track)
        if lw:
            self.text(x + bw, y, fit(self._content(lab), lw, "r", self.g("ellipsis")), label_spec)
        return x + w

    def scrollbar(self, x: int, y: int, h: int, offset: int, visible: int, total: int, always: bool = False) -> bool:
        """Vertical scrollbar of h cells: thumb █ (scrollbar.thumb) on a │ track (scrollbar.track), thumb >= 1 cell.
        Hidden (returns False) when everything fits, unless always=True. On a box side (protected cells) only the
        thumb replaces the border, which the linter allows."""
        if total <= visible and not always:
            return False
        size = max(1, min(h, round(h * visible / max(1, total))))
        pos = round((h - size) * offset / max(1, total - visible)) if total > visible else 0
        on_border = any((x, y + i) in self._prot for i in range(h))
        if on_border and self.is_ascii:
            raise CanvasError(f"scrollbar at x={x}: under glyphs=ascii '#' cannot replace a box border; draw it "
                              f"in the interior column x={x - 1}")
        for i in range(h):
            yy = y + i
            if pos <= i < pos + size:
                self.text(x, yy, self.g("thumb"), "scrollbar.thumb", force=on_border)
            elif (x, yy) not in self._prot:
                self.text(x, yy, self.g("track"), "scrollbar.track")
        return True

    def table(self, *where, columns, rows, header: bool = True, selected: int | None = None, offset: int = 0,
              total: int | None = None, cursor: str | None = None, zebra=False, zebra_phase: int = 1,
              row_spec=None, gap: int = 1, pad: int = 1, inactive: bool = False, stale: bool = False,
              header_spec: str = "table.header bold", stripe: str = "bg.stripe", skeleton: int = 0,
              region: str | None = None):
        """Columns of cells in `where` (usually a panel interior): widths from Col (fixed or flex), each cell
        truncated with ⋯ at its Col.truncate side and aligned, `gap` cells between columns, `pad` cells inside
        the left and right edge, a 2-cell cursor gutter when cursor is set.

        rows: the data list (sequences or dicts keyed by Col.name) of which rows[offset:] are shown; total = full
        count for the range label (default len(rows)). A cell is str | (str, spec) | [runs]; neutral styles come
        from Col.spec. selected = data index: full-width selection.bg band (selection.inactive.bg and no cursor
        when inactive=True), neutral text in Col.sel, semantic colors (status.*) kept; recorded as `#! selected`
        for region (default: the panel's rid). zebra: True = parity of the data index, "newest-first" = counted from
        the oldest (needs total; new rows never flip stripes), or fn(index, row) -> bool; stripe when key % 2 ==
        zebra_phase (layout-archetypes §2.4: data-anchored, weakest fill, the selection replaces it). row_spec =
        fn(index, row) -> spec restyling neutral cells of that row (e.g. fg.faint for stopped). stale=True draws
        every value faint (degraded state). skeleton=N adds N placeholder rows (busy state).
        Returns info: .cols [(Col, x, w)], .y (first data row), .shown, .range ('1-15/175'), .rows_y."""
        r = _where(where, need_h=False)
        vis_cols = [(i, c) for i, c in enumerate(columns) if c.hide_below is None or r.w >= c.hide_below]
        cur_g = (self.g("cursor") if cursor == "❯" else self._content(cursor)) if cursor else ""
        gutter = width(cur_g) + 1 if cursor else 0
        avail = r.w - 2 * pad - gutter
        sizes = [(c.ascii_width if self.is_ascii and c.ascii_width is not None else c.width) if c.width is not None
                 else f"{c.flex}*" for _, c in vis_cols]
        try:
            lay = layout(avail, sizes, gap, "table")
        except CanvasError as e:
            raise CanvasError(f"table at {r!r}: columns {[c.name for _, c in vis_cols]} with widths {sizes} need "
                              f"more than the {avail} interior cells; give a column hide_below=<width> or shrink "
                              f"fixed widths ({e})") from None
        for (_, c), (_, cw) in zip(vis_cols, lay):
            if c.width is None and cw < c.min:
                raise CanvasError(f"table at {r!r}: flexible column {c.name!r} gets {cw} cells (< min {c.min}); "
                                  f"shrink fixed columns or hide one below this width with Col(hide_below=...)")
        x0 = r.x + pad + gutter
        cols_info = [(c, x0 + off, cw) for (_, c), (off, cw) in zip(vis_cols, lay)]
        ell = self.g("ellipsis")
        total = len(rows) if total is None else total
        y = r.y
        h = r.h if r.h >= 0 else (1 if header else 0) + len(rows) - offset + skeleton
        bottom = r.y + h
        if header:
            if y >= bottom:
                raise CanvasError(f"table at {r!r} has no room for its header row")
            hs = self.adapt(header_spec)
            for c, cx, cw in cols_info:
                self.runs(cx, y, _fit_runs(self._runs_content(_as_runs(c.name or "", hs)), cw,
                                           c.header_align or c.align, c.truncate, ell))
            y += 1
        first_y = y
        cap = max(0, bottom - y)
        shown = rows[offset:offset + cap]
        rows_y = []
        rid = region or r.rid
        for i, row in enumerate(shown):
            idx = offset + i
            yy = first_y + i
            rows_y.append(yy)
            is_sel = selected is not None and idx == selected
            if is_sel:
                self.fill(r.x, yy, r.w, 1, "selection.inactive.bg" if inactive else "selection.bg")
                if rid and not inactive:            # an inactive selection is not the focused pane's state
                    self.selected_at(rid, yy)
            elif zebra:
                if callable(zebra):
                    striped = bool(zebra(idx, row))
                else:
                    key = (total - 1 - idx) if zebra == "newest-first" else idx
                    striped = key % 2 == zebra_phase
                if striped:
                    self.fill(r.x, yy, r.w, 1, stripe)
            if is_sel and cursor and not inactive:
                self.text(r.x + pad, yy, cur_g, self.adapt("accent.primary bold"))
            rs = row_spec(idx, row) if row_spec else None
            for ci, (c, cx, cw) in zip([i_ for i_, _ in vis_cols], cols_info):
                if isinstance(row, dict):
                    val = row.get(c.name)
                else:
                    val = row[ci] if ci < len(row) else None
                runs = _as_runs(val, c.spec)
                out = []
                for s, sp in runs:
                    if rs and _fg(sp) in NEUTRAL_FG:
                        sp = rs
                    if stale:
                        sp = _restyle(sp, "fg.muted" if is_sel else "fg.faint")
                    elif is_sel and not inactive and _fg(sp) in NEUTRAL_FG:
                        sp = _restyle(sp, self.adapt(c.sel or "selection.fg"))
                    out.append((s, sp))
                self.runs(cx, yy, _fit_runs(self._runs_content(out), cw, c.align, c.truncate, ell))
        y = first_y + len(shown)
        sk = self.g("skeleton")
        for j in range(min(skeleton, max(0, bottom - y))):
            for k, (c, cx, cw) in enumerate(cols_info):
                n = max(1, cw - ((j * 3 + k * 5) % max(1, cw // 2 + 1)))
                self.text(cx + (cw - n if c.align == "r" else 0), y, sk * n, "fg.faint")
            y += 1
        return types.SimpleNamespace(cols=cols_info, y=first_y, shown=len(shown), rows_y=rows_y,
                                     range=scroll_range(offset, len(shown), total), total=total)

    def listing(self, *where, items, selected: int | None = None, cursor: str | None = "❯", spec: str = "fg.default",
                sel: str = "selection.fg bold", truncate: str = "end", **kw):
        """A one-column list: items are str | (str, spec) | runs; cursor glyph + full-width selection band on the
        selected item. Other keywords as table() (offset, total, zebra, inactive, stale, region...)."""
        return self.table(*where, columns=[Col(None, spec=spec, sel=sel, truncate=truncate)],
                          rows=[[it] for it in items], header=False, selected=selected, cursor=cursor, **kw)

    def tree(self, *where, nodes, selected: int | None = None, indent: int = 4, folds: bool = False,
             guide_spec: str = "fg.faint", cursor: str | None = None, **kw):
        """A tree as a listing: guides ├── └── │ (indent 4, 3 or 2), optional ▾/▸ folds; nodes are labels,
        (label, [children]) / (label, [children], open) tuples or Node objects. selected = index in the flattened
        rows. Returns the table info with .items = tree_rows(...)."""
        flat = tree_rows(nodes, indent, self.is_ascii, folds)
        items = [[(pre, guide_spec)] + _as_runs(label, kw.get("spec", "fg.default")) for pre, label, _, _ in flat]
        info = self.listing(*where, items=items, selected=selected, cursor=cursor, **kw)
        info.items = flat
        return info

    def keybar(self, y: int, left, right=(("?", "help"), ("q", "quit")), bg: str | None = "statusbar.bg",
               x: int = 0, w: int | None = None, region=None, overflow: str = "raise") -> None:
        """Footer key hints on a band: `key verb` pairs 2 cells apart, context left (from x+1), global right
        (ending at x+w-1). An item is (key, verb) or (key, verb, "off") for a disabled hint (fg.faint).
        x/w place it inside a panel (bg=None: no band); region="keybar" records it; overflow="drop" drops left hints
        from the end (then right ones) until they fit, instead of raising."""
        w = self.cols - x if w is None else w
        left, right = list(left), list(right or ())
        ks, ds = self.adapt("keyhint.key bold"), self.adapt("keyhint.desc")

        def parts(items):
            return self._runs_content(hint_runs(items, key_spec=ks, desc_spec=ds))

        def widths():
            return runs_width(parts(left)), runs_width(parts(right))

        lw, rw = widths()
        while overflow == "drop" and lw + rw + 2 > w - 2 and (left or right):
            (left if left else right).pop()
            lw, rw = widths()
        if lw + rw + (2 if right else 0) > w - 2:
            need = lw + rw + (2 if right else 0) - (w - 2)
            names = ", ".join(f"'{k} {v}'" for k, v, *_ in reversed(left))
            raise CanvasError(f"keybar row {y}: left hints need {lw} cells and right hints {rw} (+2 gap) but the band "
                              f"has {w - 2}; {need} cell(s) too many. Drop hints from the end ({names}), shorten "
                              f"verbs, or pass overflow='drop' (footer verbs beyond ~6 go first at 80 columns)")
        if bg:
            self.clear(x, y, w, 1, bg)
        self.runs(x + 1, y, parts(left))
        if right:
            self.runs(x + w - 1 - rw, y, parts(right))
        self._add_region(region, x, y, w, 1)

    def fade(self, keep: Rect | None = None) -> None:
        """Dim everything (the app behind an overlay): glyphs fg.faint, fills and attributes removed."""
        for yy, row in enumerate(self.cells):
            for xx, c in enumerate(row):
                if keep and keep.x <= xx < keep.right and keep.y <= yy < keep.bottom:
                    continue
                c.fg = "fg.faint" if c.ch.strip() else None
                c.bg, c.attrs = None, ()

    def overlay(self, w: int, h: int, title: str | None = None, *, x: int | None = None, y: int | None = None,
                fade: bool = True, fill: str = "bg.overlay", border: str = "rounded", spec: str = "border.focus",
                role: str = "modal", hints=None, title_right: str | None = None) -> Rect:
        """A modal over the current screen: fades the base (fade=True), clears its area, draws a focused box on
        `fill`, records the region and focus. Centered unless x/y are given. hints=[(key, verb)...] go on the last
        interior row (the modal's own hints). Returns the interior Rect (above the hint row)."""
        if w > self.cols or h > self.rows or w < 4 or h < 3:
            raise CanvasError(f"overlay {w}x{h} does not fit the {self.cols}x{self.rows} canvas; size it from the "
                              f"canvas, e.g. min({w}, c.cols - 4) x min({h}, c.rows - 2)")
        x = (self.cols - w) // 2 if x is None else x
        y = (self.rows - h) // 2 if y is None else y
        if fade:
            self.fade()
        if self.is_ascii:
            border = "ascii"
        self.clear(x, y, w, h, fill)
        inner = self.panel(Rect(x, y, w, h), title, role=role, focus=True, border=border, spec=spec,
                           fill=fill, clear=True, title_right=title_right)
        if hints:
            self.keybar(inner.bottom - 1, hints, right=(), bg=None, x=inner.x, w=inner.w)
            inner = Rect(inner.x, inner.y, inner.w, inner.h - 2, inner.rid)
        return inner

    def center(self, *where, lines, spec: str = "fg.default") -> int:
        """Write lines (str | (str, spec) | runs | "" for a gap) centered horizontally and vertically in `where`;
        too-wide lines are truncated. Returns the y of the first line."""
        r = _where(where)
        y0 = r.y + max(0, (r.h - len(lines)) // 2)
        for i, ln in enumerate(lines[:r.h]):
            runs = _fit_runs(self._runs_content(_as_runs(ln, spec)), r.w, ellipsis=self.g("ellipsis"), pad=False)
            lw = runs_width(runs)
            if lw:
                self.runs(r.x + (r.w - lw) // 2, y0 + i, runs)
        return y0

    def toosmall(self, need: tuple, app: str | None = None, keys=(("q", "quit"),), hint: str | None = None) -> None:
        """The too-small screen (layout-archetypes §2.2): what is short, current vs needed size in words and color
        (✗ / ✓), how to fix it, and the keys that still work on the bottom row."""
        nc, nr = need
        fail_g, ok_g = self.g("fail"), self.g("ok")

        def line(word, cur, req):
            short = cur < req
            return [(f"{word:<7}", "fg.muted"), (f"{cur:>4}", self.adapt("status.error bold") if short else "status.success"),
                    ("   needs ", "fg.muted"), (f"{req:<4}", "fg.default"),
                    (fail_g if short else ok_g, "status.error" if short else "status.success")]

        lines = ([(app, self.adapt("accent.primary bold")), ""] if app else []) + [
            ("Terminal too small", self.adapt("fg.title bold")), "",
            line("Width", self.cols, nc), line("Height", self.rows, nr), "",
            (hint or "Enlarge the window to continue.", "fg.muted")]
        self.center(Rect(0, 0, self.cols, max(1, self.rows - 1)), lines=lines)
        if keys:
            self.keybar(self.rows - 1, [], right=keys, overflow="drop")

    # ------------------------------------------------------------------ output
    def _norm(self, c: _Cell) -> Style:
        fg, attrs = c.fg, c.attrs
        if c.ch == " " and not any(a in attrs for a in VISIBLE_ON_SPACE):
            fg = None                            # the foreground of a blank is invisible
            attrs = tuple(a for a in attrs if a in VISIBLE_ON_SPACE)
        return fg, c.bg, attrs

    def _row_markup(self, row: list[_Cell]) -> str:
        items = [(c.ch, self._norm(c)) for c in row if not c.cont]
        while items and items[-1][0] == " " and items[-1][1] == (None, None, ()):
            items.pop()                           # the renderer pads short rows on bg.base

        def flexible(ch: str, st: Style) -> bool:  # a blank: its fg/attrs are invisible, only its bg matters
            return ch == " " and not any(a in st[2] for a in VISIBLE_ON_SPACE)

        styles: list[Style] = [st for _, st in items]
        for i, (ch, st) in enumerate(items):      # let blanks join a neighbouring run with the same bg
            if not flexible(ch, st):
                continue
            left = styles[i - 1] if i else None
            right = next((s for c, s in items[i + 1:] if not flexible(c, s)), None)
            for nb in (left, right):
                if nb is not None and nb[1] == st[1] and not any(a in nb[2] for a in VISIBLE_ON_SPACE):
                    styles[i] = nb
                    break
        out: list[str] = []
        cur: Style | None = None
        buf = ""

        def flush() -> None:
            nonlocal buf
            if buf:
                esc = buf.replace("{", "{{").replace("}", "}}")
                spec = _spec_str(cur) if cur else ""
                out.append("{" + spec + "}" + esc + "{/}" if spec else esc)
            buf = ""

        for (ch, _), st in zip(items, styles):
            if st != cur:
                flush()
                cur = st
            buf += ch
        flush()
        return "".join(out)

    def to_mock(self) -> str:
        head = ["#! tui-mockup 1", f"#! size: {self.cols}x{self.rows}"]
        if self.caps:
            head.append(f"#! caps: {self.caps.spec()}")
        if self.title:
            head.append(f"#! title: {self.title}")
        if self.state:
            head.append(f"#! state: {self.state}")
        if self.theme:
            head.append(f"#! theme: {self.theme}")
        head += [f"#! note: {n}" for n in self.notes]
        for rid, role, x, y, w, h, t in sorted(self._regions, key=lambda r: int(r[0][1:])):
            head.append(f"#! region {rid} {role} {x},{y},{w},{h}" + (f" {t}" if t else ""))
        if getattr(self, "_focus", None):
            head.append(f"#! focus {self._focus}")
        if getattr(self, "_selected", None):
            head.append(f"#! selected {self._selected[0]} {self._selected[1]}")
        return "\n".join(head + [self._row_markup(r) for r in self.cells]) + "\n"

    def plain(self) -> str:
        """The canvas as plain text rows (for a quick look in a terminal)."""
        return "\n".join("".join(c.ch for c in row if not c.cont).rstrip() for row in self.cells) + "\n"

    def lint(self, path: str = "<canvas>") -> list[str]:
        """Lint ERRORs as messages that name the cell: glyph errors with (x,y) and the fix, body errors with
        their canvas row y. Empty list = clean."""
        msgs: list[str] = []
        seen: set = set()
        for y, row in enumerate(self.cells):
            x = 0
            for c in row:
                if not c.cont:
                    for ch in c.ch:
                        g = classify_glyph(ch, False, False, self.caps)
                        if g and g[0] == "ERROR" and (ch, y) not in seen:
                            seen.add((ch, y))
                            msgs.append(f"{path}: ERROR at (x={x},y={y}): {g[1]} ({g[2]})")
                x += 1
        if msgs:
            return msgs
        text = self.to_mock()
        m = parse_mock(text, path)
        for f in m.findings:
            if f.level != "ERROR":
                continue
            where = f" [canvas row y={f.line - m.body_line}]" if f.line >= m.body_line else " [header]"
            msgs.append(f.fmt(path) + where)
        return msgs

    def save(self, path, check: bool = True, verbose: bool | None = None, report: bool = True) -> Path:
        """Write the .mock (parent directories are created). With check=True a lint ERROR raises CanvasError.
        Prints one summary line (`mockkit: saved NAME · 0 errors · 1 warning → DIR`) plus one line per warning;
        verbose=True (or env MOCKKIT_VERBOSE=1) lists every finding, INFO included; report=False prints nothing."""
        errs = self.lint(str(path)) if check or report else []
        if check and errs:
            raise CanvasError("mockup has lint errors:\n" + "\n".join(errs))
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        text = self.to_mock()
        p.write_text(text, encoding="utf-8")
        if report:
            _report([_frame_result(p, text, errs)], p.parent, verbose, single=True)
        return p


# ====================================================================== save / matrix reporting

def _verbose(verbose: bool | None) -> bool:
    """verbose=True/False wins; None follows env MOCKKIT_VERBOSE (1, true, yes, on)."""
    if verbose is not None:
        return bool(verbose)
    return os.environ.get("MOCKKIT_VERBOSE", "").strip().lower() in ("1", "true", "yes", "on")


def _frame_result(path: Path, text: str, errors: list) -> types.SimpleNamespace:
    """One saved (or failed) frame: its name, lint errors in full, and the parsed WARN/INFO findings."""
    findings = [f for f in parse_mock(text, path.name).findings if f.level != "ERROR"] if text else []
    return types.SimpleNamespace(name=path.name, errors=list(errors), findings=findings)


def _n(count: int, word: str) -> str:
    return f"{count} {word}" + ("" if count == 1 else "s")


def _report(results: list, where, verbose: bool | None, attempted: int | None = None, single: bool = False,
            suffix: str = "", show_errors: bool = True) -> None:
    """Print the summary line, errors in full, one line per distinct warning (frames that share it are counted);
    verbose: every frame and every finding."""
    ok = [r for r in results if not r.errors]
    n_err = sum(len(r.errors) for r in results)
    warns = [(r, f) for r in results for f in r.findings if f.level == "WARN"]
    total = attempted if attempted is not None else len(results)
    if single:
        what = results[0].name
    else:
        what = _n(len(ok), "frame") if len(ok) == total else f"{len(ok)} of {total} frames"
    out = [f"mockkit: saved {what} · {_n(n_err, 'error')} · {_n(len(warns), 'warning')} → {where}{suffix}"]
    if _verbose(verbose):
        for r in results:
            infos = sum(1 for f in r.findings if f.level == "INFO")
            if not single:
                out.append(f"  {r.name} · {_n(len(r.errors), 'error')} · "
                           f"{_n(len(r.findings) - infos, 'warning')} · {infos} info")
            out += [f"    {e}" for e in r.errors] + [f"    {f.fmt(r.name)}" for f in r.findings]
    else:
        if show_errors:
            out += [f"  {e}" for r in results for e in r.errors]
        groups: dict = {}
        for r, f in warns:
            groups.setdefault((f.msg, f.hint), []).append((r, f))
        for (msg, hint), hits in groups.items():
            if len(hits) == 1:
                out.append(f"  {hits[0][1].fmt(hits[0][0].name)}")
            else:
                names = [r.name for r, _ in hits]
                shown = ", ".join(names[:3]) + (f" +{len(names) - 3} more" if len(names) > 3 else "")
                out.append(f"  WARN: {msg}{f' ({hint})' if hint else ''} — {len(hits)} frames: {shown}")
    print("\n".join(out), flush=True)


# ====================================================================== states x sizes matrix

def theme_arg(theme: str) -> str:
    """A theme id or a path to a theme .json, in the form the sub-tools (ansi_render.py, gallery.py) resolve with
    the same _theme.load_theme as render_mockup.py --theme. A path is made absolute (the sub-process gets the same
    cwd today, but the .mock header may be read from elsewhere); a bundled id is passed through unchanged. Do not
    pass Theme.id for a custom theme: an id is looked up in references/themes/ only, so it is not found there."""
    from _theme import find_theme_file
    path = find_theme_file(theme)            # FileNotFoundError names the bundled ids, as load_theme does
    return theme if path.parent == THEMES_DIR else str(path.resolve())


def frame_name(variant: str, state: str, cols: int, rows: int, ext: str = "mock") -> str:
    """`<variant>--<state>--<cols>x<rows>.<ext>` (formats.md "Frame naming"); slugs are lowercase a-z0-9 and '-'."""
    for what, v in (("variant", variant), ("state", state)):
        if not _SLUG.fullmatch(v or ""):
            fix = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", (v or "").lower())).strip("-") or "screen"
            raise CanvasError(f"{what} {v!r} is not a lowercase slug (a-z, 0-9, single '-'); e.g. {fix!r}")
    return f"{variant}--{state}--{int(cols)}x{int(rows)}.{ext}"


def matrix(build, variant: str, out_dir, states=("normal",), sizes=((80, 24), (120, 30)), extra=(), *,
           theme: str | None = None, caps: str | None = None, title=None, fallback: bool = False, skip=None,
           check: bool = True, render: bool = False, png: bool = False, gallery=None, verbose: bool | None = None) -> list:
    """Build one screen in every (state, size): for each, Canvas(cols, rows, title, state, theme, caps) is made,
    build(c, state) draws it, and it is saved (linted) as out_dir/<variant>--<state>--<cols>x<rows>.mock.
    extra = [(state, (cols, rows)), ...] adds odd combos (toosmall, 60x24, overlays); skip(state, cols, rows) -> True
    leaves a combo out. title = str or fn(state, cols, rows). Every frame is attempted; failures are reported
    together, each with its frame name. render=True also writes .ansi (theme, caps depth); png=True also .png
    (needs rsvg-convert); gallery=path builds gallery.py over out_dir. Prints one summary line
    (`mockkit: saved 12 frames · 0 errors · 3 warnings → DIR`) plus one line per distinct warning; verbose=True (or
    env MOCKKIT_VERBOSE=1) lists every frame and finding. Returns the .mock paths."""
    out = Path(out_dir)
    combos = [(s, tuple(z)) for s in states for z in sizes] + [(s, tuple(z)) for s, z in extra]
    done, errors, results = [], [], []
    for state, (cols, rows) in combos:
        if skip and skip(state, cols, rows):
            continue
        name = frame_name(variant, state, cols, rows)
        t = title(state, cols, rows) if callable(title) else (title or f"{variant} — {state}")
        try:
            c = Canvas(cols, rows, title=t, state=state, theme=theme, caps=caps, fallback=fallback)
            build(c, state)
            p = c.save(out / name, check=check, report=False)
            done.append(p)
            results.append(_frame_result(p, p.read_text(encoding="utf-8"), [] if check else c.lint(name)))
        except CanvasError as e:
            errors.append(f"{name}: {e}")
            lines = str(e).splitlines()
            results.append(types.SimpleNamespace(name=name, errors=lines[1:] if len(lines) > 1 else lines,
                                                 findings=[]))
    if errors:
        _report(results, out, verbose, show_errors=False)        # the exception carries the errors in full
        raise CanvasError(f"{len(errors)} of {len(combos)} frame(s) failed:\n" + "\n".join(errors))
    if render or png:
        import render_mockup as rm
        from _theme import load_theme
        for p in done:
            m = parse_mock(p.read_text(encoding="utf-8"), str(p))
            th_arg = theme_arg(theme or m.theme or rm.DEFAULT_THEME)
            th = load_theme(th_arg)
            ansi = p.with_suffix(".ansi")
            ansi.write_text(rm.render(m, th, m.caps.depth), encoding="utf-8")
            if png:
                r = subprocess.run([sys.executable, str(SCRIPTS / "ansi_render.py"), str(ansi), "--theme", th_arg,
                                    "--format", "png", "-o", str(p.with_suffix(".png"))],
                                   capture_output=True, text=True)
                if r.returncode:
                    detail = (r.stderr or r.stdout).strip()
                    raise CanvasError(f"PNG for {p.name} failed: {detail}")
    if gallery:
        cmd = [sys.executable, str(SCRIPTS / "gallery.py"), str(out), "-o", str(gallery)]
        if theme:
            cmd += ["--themes", theme_arg(theme)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            raise CanvasError(f"gallery failed: {r.stderr.strip() or r.stdout.strip()}")
    made = ("+.ansi+.png" if png else "+.ansi") if render or png else ""
    _report(results, out, verbose, suffix=(f" ({made})" if made else "") + (f" · gallery {gallery}" if gallery else ""))
    return done
