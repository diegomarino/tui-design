#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""ansi_grid.py - ANSI frame -> cell-grid JSON, and (--describe) a live-capture tui-description skeleton.

Grid JSON:  {"cols","rows","cells":[[{"ch","w","fg","bg","attrs":[...],"link"?}, ...], ...]}
  - fg/bg = {"raw":"#rrggbb", "slot":"ansi.red|p:208|term.fg|term.bg|null", "tokens":[theme tokens whose
    resolved colour is within OKLab distance 0.01 of raw]}. Colours are AS PAINTED: reverse/hidden already
    applied, "reverse" stays in attrs as evidence. dim is not applied to the colour (it is in attrs).
  - w = 1 | 2; the continuation cell of a wide char is {"ch":"","w":0}.
  - attrs use the schema vocabulary: bold dim italic underline double_underline curly_underline blink
    reverse hidden strike overline.

--describe emits a `tui-description` (schemas/tui-description.schema.json, schema_version 1.0) SKELETON
(meta.source_path "capture", size, screen_text, palette, regions, elements, uncertainties). Heuristics - simple on
purpose; the describer/judge refines it:
  1. Boxes: a top-left corner (U+250C/256D/250F/2554 family: only DOWN+RIGHT connections) is closed into a
     rectangle when the nearest top-right corner on its row, the left/right edges and the bottom edge all
     validate (edges may contain text). Role "panel"; border style single|rounded|double|heavy|mixed; text in
     the top edge -> title (box-drawing runs collapsed to one space; position top_left|top_center|top_right);
     text in the bottom edge -> border_labels; border colour -> border.style_attrs.fg.
  2. Bands: first / last non-blank row that is not a box edge and has a non-default bg on >= 90% of
     the width -> header / statusbar. 3. Key hints: in the last non-blank row, segments separated by 2+ spaces,
     ' | ', ' . ' or similar that read "<key> <action>" (key = single char, named key, ^X, <x>, a/b, f1..);
     needs >= 2 segments; the row becomes a keybar region and each hint an element of type key_hint.
     Verb-first hints ("Stage: <space>") are matched too.
  Regions are a flat list (no nesting); region r0 is the whole screen. Nothing evaluative is asserted.

--clutter [--format md|json] prints countable clutter metrics instead (input: an .ansi frame, or a `.mock` path, which is
rendered with render_mockup first). Each metric gets a one-line verdict. Thresholds are calibrated on 34 curated good
frames (assets/demo, the 28 assets/mockups and captures of real dashboards and of lazygit); "notable" means above what
9 of 10 of them reach, so it is a prompt to look, not a law.
  chrome share        % of non-space cells that are box-drawing / separator / rule glyphs (U+2500-257F, ¦, runs of
                      3+ of - = _ , | and + that line up with other border cells). Good set: p50 24.5, p90 47.6,
                      max 58.1. > 50 % = notable. (The Fleet demo scores 30.8, lazygit 58.1, the cluttered fixture 72.3.)
  border nesting      max number of nested boxes (corner-closed rectangles, detected as --describe does) around any
                      content cell. Good set: max 1. > 1 = notable (ASCII +--+ boxes are not detected).
  repeated markers    per region (box interior; the rest of the screen is region "screen"; needs >= 4 non-blank rows),
                      the same symbol glyph in the same column on >= 90 % of the rows = notable (a marker that marks
                      nothing). Letters, digits, ASCII punctuation, box-drawing, block, braille and truncation (… ⋯)
                      glyphs are not markers. Good set: 0 of 34 files.
  duplicate signals   per region row, status encodings from a small vocabulary: glyph (✓✗▲●○◌, and · ? ! at the start
                      of the row), bracket tag ([X] [!] [i] [OK] [*]), word (ok error fail warn blocked done idle).
                      glyph + word is the required baseline and is NEVER flagged. Flagged (notable): a tag next to a glyph
                      ([OK] ✓), all three encodings at once, or a repeated type word on a status row ("Source Source
                      error"). Good set: 0 of 34 files.
  blank share         % of cells without content per region; > 90 % on a region of >= 20 cells = "sparse" (info
                      only). Good set: p50 62, p90 85, p95 94.

Examples:
  python3 scripts/ansi_grid.py frame.ansi --clutter
  python3 scripts/ansi_grid.py ../assets/demo/fleet--normal--80x24.mock --clutter --format json
  python3 scripts/ansi_grid.py frame.ansi --theme catppuccin-mocha -o grid.json
  python3 scripts/ansi_grid.py frame.ansi --cols 120 --rows 30 --describe -o desc.json
  python3 scripts/render_mockup.py demo.mock | python3 scripts/ansi_grid.py - --describe

Exit: 0 ok, 2 usage/environment error. Cursor movement is not emulated (feed one-frame output).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ansi import Resolver, parse_ansi  # noqa: E402
from _theme import load_theme, oklab_distance  # noqa: E402

CAND_MAX_DIST = 0.01


# ---------------------------------------------------------------- box-drawing table (from Unicode names)

def _box_table() -> dict[str, tuple[frozenset, str]]:
    t = {}
    for cp in range(0x2500, 0x2580):
        ch = chr(cp)
        name = unicodedata.name(ch, "")
        words = set(name.replace("-", " ").split())
        dirs = {d for d, w in (("U", "UP"), ("D", "DOWN"), ("L", "LEFT"), ("R", "RIGHT")) if w in words}
        if "VERTICAL" in words:
            dirs |= {"U", "D"}
        if "HORIZONTAL" in words:
            dirs |= {"L", "R"}
        style = "rounded" if "ARC" in words else "double" if "DOUBLE" in words else "heavy" if "HEAVY" in words else "single"
        t[ch] = (frozenset(dirs), style)
    return t


BOX = _box_table()


def dirs(ch: str) -> frozenset:
    return BOX[ch][0] if ch in BOX else frozenset()


SCROLLBAR = "▐▌█▓▒░▕▏"        # may replace a vertical edge cell (scrollbar thumb/track)


def is_h(ch: str) -> bool:
    """horizontal-ish edge cell: line/junction with L+R, or non-box text."""
    return ch not in BOX or {"L", "R"} <= dirs(ch)


def is_v(ch: str) -> bool:
    return ch in BOX and {"U", "D"} <= dirs(ch)


# ---------------------------------------------------------------- colours

class Colors:
    def __init__(self, theme):
        self.theme, self.res = theme, Resolver(theme)
        self._cand: dict[str, list[str]] = {}

    def candidates(self, raw: str) -> list[str]:
        if raw not in self._cand:
            scored = sorted((oklab_distance(raw, h), tok) for tok, h in self.theme.tokens.items())
            self._cand[raw] = [tok for d, tok in scored if d < CAND_MAX_DIST]
        return self._cand[raw]

    def obj(self, raw: str, slot: str | None) -> dict:
        return {"raw": raw, "slot": slot, "tokens": self.candidates(raw)}

    def cell_colors(self, st) -> tuple[dict, dict]:
        """fg/bg objects as painted (reverse/hidden applied)."""
        fg, bg = self.res.painted(st)
        fslot, bslot = self.res.slot(st.fg, "term.fg"), self.res.slot(st.bg, "term.bg")
        if "reverse" in st.attrs:
            fslot, bslot = bslot if st.bg else "term.bg", fslot if st.fg else "term.fg"
        if "hidden" in st.attrs and "reverse" not in st.attrs:
            fslot = bslot
        return self.obj(fg, fslot), self.obj(bg or self.res.bg, bslot if bg else "term.bg")

    def schema_color(self, o: dict) -> dict:
        """grid colour object -> schema `color` (source sgr)."""
        c = {"raw": o["raw"], "source": "sgr"}
        slot = o["slot"]
        c["token"] = slot if slot and slot.startswith(("ansi.", "p:")) else (o["tokens"][0] if o["tokens"] else slot)
        if o["tokens"]:
            c["token_candidates"] = o["tokens"]
        return c


def build_grid_json(grid, colors: Colors) -> dict:
    rows = []
    for row in grid.cells:
        out = []
        for c in row:
            if not c.w:
                out.append({"ch": "", "w": 0})
                continue
            fg, bg = colors.cell_colors(c.style)
            d = {"ch": c.ch, "w": c.w, "fg": fg, "bg": bg, "attrs": sorted(c.style.attrs)}
            if c.style.link:
                d["link"] = c.style.link
            out.append(d)
        rows.append(out)
    return {"cols": grid.cols, "rows": grid.rows, "cells": rows}


# ---------------------------------------------------------------- describe

KEY_ATOM = (r"(?:\^[A-Za-z]|<[^\s>]+>|ctrl|alt|shift|esc|enter|return|tab|space|bksp|backspace|del|delete|home|end|"
            r"pgup|pgdn|up|down|left|right|f\d{1,2}|[←→↑↓]+|[⏎↵⇥⎋⌫⌃⌥⇧]|[A-Za-z0-9?!@#$%&*=~.;:'\"\\\[\]{}|<>_])")
KEY_RE = re.compile(rf"{KEY_ATOM}(?:[/·+,-]{KEY_ATOM})*|/", re.I)
SEP_RE = re.compile(r"\s{2,}|\s[·│|•]\s")
KEY_NORM = {"⏎": "enter", "↵": "enter", "⇥": "tab", "⎋": "esc", "⌫": "backspace", "↑": "up", "↓": "down",
            "←": "left", "→": "right"}


def norm_key(k: str) -> str:
    if len(k) == 2 and k[0] == "^":
        return "ctrl+" + k[1].lower()
    if k.startswith("<") and k.endswith(">") and len(k) > 2:
        k = k[1:-1]
    return KEY_NORM.get(k, k.lower() if len(k) > 1 else k)


class Describer:
    def __init__(self, grid, theme, colors: Colors, subject: str | None):
        self.g, self.theme, self.colors, self.subject = grid, theme, colors, subject
        self.rows = grid.text_rows()
        # per row: start column of every character of the row text
        self.pos = [[x for x, c in enumerate(row) if c.w for _ in c.ch] for row in grid.cells]
        self.regions: list[dict] = []
        self.elements: list[dict] = []

    # -- helpers
    def cell(self, x, y):
        return self.g.cells[y][x]

    def ch(self, x, y) -> str:
        c = self.cell(x, y)
        return c.ch[:1] if c.w else " "

    def style_of(self, x, y) -> dict:
        st = self.cell(x, y).style
        fg, bg = self.colors.cell_colors(st)
        out = {"fg": self.colors.schema_color(fg)}
        if st.bg or "reverse" in st.attrs:
            out["bg"] = self.colors.schema_color(bg)
        if st.attrs:
            out["attrs"] = sorted(st.attrs)
            out["attrs_source"] = "sgr"
        return out

    def text_between(self, y, x0, x1) -> str:
        return "".join(self.cell(x, y).ch for x in range(x0, x1) if self.cell(x, y).w)

    # -- 1. boxes
    def find_boxes(self) -> list[tuple[int, int, int, int]]:
        W, H = self.g.cols, self.g.rows
        found = []
        for y in range(H):
            for x1 in range(W):
                if dirs(self.ch(x1, y)) != {"D", "R"}:
                    continue
                for x2 in range(x1 + 1, W):
                    c = self.ch(x2, y)
                    if dirs(c) == {"D", "L"}:
                        y2 = self.close_box(x1, y, x2)
                        if y2:
                            found.append((x1, y, x2 - x1 + 1, y2 - y + 1))
                        break
                    if not is_h(c):
                        break
        return sorted(set(found), key=lambda b: (b[1], b[0], -b[2]))

    def close_box(self, x1, y, x2) -> int | None:
        for y2 in range(y + 1, self.g.rows):
            l, r = self.ch(x1, y2), self.ch(x2, y2)
            if dirs(l) == {"U", "R"} and dirs(r) == {"U", "L"}:
                if all(is_h(self.ch(x, y2)) for x in range(x1 + 1, x2)):
                    return y2
                return None
            if not (is_v(l) and (is_v(r) or r in SCROLLBAR)):
                return None
        return None

    def box_region(self, rid, b) -> dict:
        x, y, w, h = b
        corners = [self.ch(x, y), self.ch(x + w - 1, y), self.ch(x, y + h - 1), self.ch(x + w - 1, y + h - 1)]
        styles = {BOX[c][1] for c in corners}
        style = styles.pop() if len(styles) == 1 else "mixed"
        reg = {"id": rid, "role": "panel", "bbox": {"x": x, "y": y, "w": w, "h": h}, "z": 0,
               "border": {"style": style, "sides": ["top", "right", "bottom", "left"],
                          "style_attrs": {"fg": self.colors.schema_color(self.colors.cell_colors(self.cell(x, y).style)[0])}}}
        title = self.edge_text(y, x, w)
        if title:
            text, tx0, tx1 = title
            pos = "top_left" if tx0 - (x + 1) <= 3 else "top_right" if (x + w - 2) - tx1 <= 3 else "top_center"
            reg["title"] = {"text": text, "position": pos, "style": self.style_of(tx0, y)}
        bl = self.edge_text(y + h - 1, x, w)
        if bl:
            reg["border_labels"] = [{"text": bl[0], "bbox": {"x": bl[1], "y": y + h - 1, "w": bl[2] - bl[1] + 1, "h": 1}}]
        return reg

    def edge_text(self, y, x, w):
        """(text, first_col, last_col) of non-box text inside a top/bottom edge, or None."""
        parts, first, last = [], None, None
        for xx in range(x + 1, x + w - 1):
            c = self.cell(xx, y)
            if c.w and c.ch[:1] in BOX:
                parts.append(" ")
            elif c.w:
                parts.append(c.ch)
                first = xx if first is None else first
                last = xx + c.w - 1
        text = re.sub(r"\s+", " ", "".join(parts)).strip()
        return (text, first, last) if text else None

    # -- 2/3. bands and key hints
    def band(self, y) -> bool:
        return sum(self.colors.res.painted(c.style)[1] is not None for c in self.g.cells[y]) >= 0.9 * self.g.cols

    def hints(self, y) -> list[dict]:
        row, pos = self.rows[y], self.pos[y]
        segs, start = [], 0
        for m in list(SEP_RE.finditer(row)) + [None]:
            end = m.start() if m else len(row)
            seg = row[start:end]
            if seg.strip():
                lead = len(seg) - len(seg.lstrip())
                segs.append((start + lead, seg.strip()))
            start = m.end() if m else end
        out = []
        for s0, seg in segs:
            parts = seg.split(None, 1)
            verb_first = re.fullmatch(rf"(\w[\w ]*?):\s+({KEY_ATOM}(?:[/·+,-]{KEY_ATOM})*)", seg, re.I)
            if verb_first:
                parts = [verb_first.group(2), verb_first.group(1)]
            if len(parts) == 2 and KEY_RE.fullmatch(parts[0]) and re.search(r"[^\W\d_]", parts[1]):
                x0 = pos[s0]
                x1 = pos[s0 + len(seg) - 1] + 1
                out.append({"key": norm_key(parts[0]), "key_raw": parts[0], "action": parts[1],
                            "bbox": {"x": x0, "y": y, "w": x1 - x0, "h": 1}, "text": seg})
        return out if len(out) >= 2 else []

    def non_blank_rows(self) -> list[int]:
        return [y for y, r in enumerate(self.rows) if r.strip()]

    def is_edge_row(self, y) -> bool:
        s = self.rows[y].strip()
        return bool(s) and sum(c in BOX for c in s) >= 0.6 * len(s)

    def run(self) -> dict:
        W, H = self.g.cols, self.g.rows
        self.regions.append({"id": "r0", "role": "screen", "bbox": {"x": 0, "y": 0, "w": W, "h": H}, "z": 0, "order": 0})
        for b in self.find_boxes():
            self.regions.append(self.box_region(f"r{len(self.regions)}", b))
        nb = self.non_blank_rows()
        inside_box = lambda y: any(r["bbox"]["y"] <= y < r["bbox"]["y"] + r["bbox"]["h"] for r in self.regions[1:])
        if nb:
            top, bot = nb[0], nb[-1]
            if top <= 1 and not self.is_edge_row(top) and not inside_box(top) and self.band(top):
                self.add_band("header", top)
            if bot >= H - 2 and bot != top and not self.is_edge_row(bot) and not inside_box(bot):
                hints = self.hints(bot)
                if hints or self.band(bot):
                    r = self.add_band("keybar" if hints else "statusbar", bot)
                    for h in hints:
                        self.elements.append({"id": f"e{len(self.elements)}", "region": r["id"], "type": "key_hint",
                                              "bbox": h["bbox"], "text": h["text"], "interactive": True, "source": "derived",
                                              "key_hints": [{k: h[k] for k in ("key", "key_raw", "action", "bbox")}]})
        body = sorted(self.regions[1:], key=lambda r: (r["bbox"]["y"], r["bbox"]["x"], -r["bbox"]["w"]))
        remap = {r["id"]: f"r{i}" for i, r in enumerate(body, 1)}
        for r in body:
            r["id"] = remap[r["id"]]
        for e in self.elements:
            e["region"] = remap[e["region"]]
        self.regions = self.regions[:1] + body
        for i, r in enumerate(self.regions):
            r["order"] = i
        palette = self.palette()
        meta = {"source_path": "capture", "size": {"cols": W, "rows": H, "source": "derived"},
                "theme_guess": {"name": self.theme.id, "dark": self.theme.appearance == "dark",
                                "default_fg": self.theme.foreground, "default_bg": self.theme.background}}
        if self.subject:
            meta["subject"] = self.subject
        return {"schema_version": "1.0", "meta": meta, "palette": palette, "regions": self.regions,
                "elements": self.elements, "screen_text": self.rows,
                "uncertainties": [{"kind": "other", "note": "Live-capture skeleton: regions come only from box-drawing "
                                   "rectangles, uniform-background first/last rows and 'key action' hints; roles beyond "
                                   "panel/header/statusbar/keybar are not assigned and elements other than key hints are not listed."}]}

    def add_band(self, role, y) -> dict:
        r = {"id": f"r{len(self.regions)}", "role": role, "bbox": {"x": 0, "y": y, "w": self.g.cols, "h": 1}, "z": 0}
        self.regions.append(r)
        return r

    def palette(self) -> dict:
        """Every token whose colour is painted on screen (aliases of one hex all listed); colours with no
        token are keyed by their SGR slot (ansi.red, p:208, term.fg) or rgb:#hex for off-palette truecolor."""
        pal, seen = {}, set()
        for row in self.g.cells:
            for c in row:
                if c.w and c.style not in seen:
                    seen.add(c.style)
                    for o in self.colors.cell_colors(c.style):
                        for tok in o["tokens"] or [o["slot"] or f"rgb:{o['raw']}"]:
                            pal.setdefault(tok, o["raw"])
        return dict(sorted(pal.items()))

# ---------------------------------------------------------------- clutter metrics (--clutter)

CHROME_SHARE_MAX = 50.0      # % of non-space cells (calibrated: see --help)
NESTING_MAX = 1
MARKER_ROW_SHARE = 0.90
MIN_REGION_ROWS = 4
SPARSE_BLANK = 90.0
SPARSE_MIN_CELLS = 20
STATUS_GLYPHS = "✓✗▲●○◌"
STATUS_LEAD = "·?!"           # only count as a status glyph as the first token of a row
TAG_RE = re.compile(r"\[(?:x|!|i|ok|\*)\]", re.I)
WORD_RE = re.compile(r"\b(?:ok|errors?|fail(?:ed|ure|s)?|warn(?:ing|ings)?|blocked|done|idle)\b", re.I)


def _is_marker(ch: str) -> bool:
    """A symbol glyph that can mark a row: non-ASCII S* / Po, not box-drawing, block elements or braille."""
    cp = ord(ch[0])
    if cp < 128 or 0x2500 <= cp <= 0x259F or 0x2800 <= cp <= 0x28FF:
        return False
    if ch[0] in "…⋯":                                  # truncation marks, not row markers
        return False
    cat = unicodedata.category(ch[0])
    return cat.startswith("S") or cat == "Po"


def chrome_cells(grid) -> set[tuple[int, int]]:
    """Cells holding border / separator / rule glyphs (box-drawing, plus ASCII rules and aligned | +)."""
    def at(x, y):
        return grid.cells[y][x].ch[:1] if 0 <= y < grid.rows and 0 <= x < len(grid.cells[y]) and grid.cells[y][x].w else " "
    out = set()
    for y in range(grid.rows):
        for x in range(len(grid.cells[y])):
            c = at(x, y)
            if c == " ":
                continue
            if 0x2500 <= ord(c) <= 0x257F or c in "¦":
                out.add((x, y))
            elif c in "-=_":
                run = 1 + sum(1 for d in (-1, 1) for k in range(1, 3) if all(at(x + d * j, y) in "-=_+" for j in range(1, k + 1)))
                if run >= 3:
                    out.add((x, y))
            elif c == "|" and (at(x, y - 1) in "|+" or at(x, y + 1) in "|+"):
                out.add((x, y))
            elif c == "+" and (at(x - 1, y) in "-=" or at(x + 1, y) in "-=" or at(x, y - 1) in "|" or at(x, y + 1) in "|"):
                out.add((x, y))
    return out


def clutter_metrics(grid, theme, name: str = "") -> dict:
    W, H = grid.cols, grid.rows
    desc = Describer(grid, theme, Colors(theme), None)
    chrome = chrome_cells(grid)
    boxes = desc.find_boxes()                       # (x, y, w, h), border included

    def ch_at(x, y):
        return grid.cells[y][x].ch if grid.cells[y][x].w else ""
    nonspace = {(x, y) for y in range(H) for x in range(len(grid.cells[y])) if ch_at(x, y).strip()}
    content = nonspace - chrome

    def inside(b, x, y, strict):
        bx, by, bw, bh = b
        return (bx < x < bx + bw - 1 and by < y < by + bh - 1) if strict else (bx <= x < bx + bw and by <= y < by + bh)

    # ownership: the smallest box containing the cell (border included); -1 = the bare screen
    order = sorted(range(len(boxes)), key=lambda i: boxes[i][2] * boxes[i][3])
    owner = [[-1] * len(grid.cells[y]) for y in range(H)]
    for y in range(H):
        for x in range(len(grid.cells[y])):
            for i in order:
                if inside(boxes[i], x, y, False):
                    owner[y][x] = i
                    break

    def label(i):
        if i < 0:
            return "screen"
        bx, by, bw, bh = boxes[i]
        t = desc.edge_text(by, bx, bw)
        return f"box {bx},{by} {bw}x{bh}" + (f" '{t[0]}'" if t else "")

    # 1. chrome share
    n_chrome, n_content = len(nonspace & chrome), len(content)
    share = 100.0 * n_chrome / max(1, n_chrome + n_content)
    m_chrome = {"share_pct": round(share, 1), "chrome_cells": n_chrome, "content_cells": n_content,
                "threshold_pct": CHROME_SHARE_MAX, "notable": share > CHROME_SHARE_MAX}

    # 2. border nesting depth
    depth, deepest = 0, None
    for (x, y) in content:
        d = sum(1 for b in boxes if inside(b, x, y, True))
        if d > depth:
            depth, deepest = d, (x, y)
    m_nest = {"max_depth": depth, "boxes": len(boxes), "deepest_content_cell": list(deepest) if deepest else None,
              "threshold": NESTING_MAX, "notable": depth > NESTING_MAX}

    # regions: interior cells owned by the box (screen = cells owned by nothing)
    region_cells: dict[int, list[tuple[int, int]]] = {}
    for y in range(H):
        for x in range(len(grid.cells[y])):
            i = owner[y][x]
            if i >= 0 and not (x in (boxes[i][0], boxes[i][0] + boxes[i][2] - 1) or y in (boxes[i][1], boxes[i][1] + boxes[i][3] - 1)):
                region_cells.setdefault(i, []).append((x, y))
            elif i < 0:
                region_cells.setdefault(-1, []).append((x, y))

    # 3. repeated markers, 5. blank share
    markers, blanks = [], []
    for i, cells in sorted(region_cells.items()):
        rows_with = sorted({y for (x, y) in cells if (x, y) in content})
        if len(rows_with) >= MIN_REGION_ROWS:
            hits: dict[tuple[int, str], int] = {}
            for (x, y) in cells:
                c = ch_at(x, y)
                if (x, y) in content and c and _is_marker(c):
                    hits[(x, c[0])] = hits.get((x, c[0]), 0) + 1
            for (x, c), n in sorted(hits.items()):
                if n >= MARKER_ROW_SHARE * len(rows_with):
                    markers.append({"region": label(i), "glyph": c, "codepoint": f"U+{ord(c):04X}", "col": x,
                                    "rows_hit": n, "rows": len(rows_with), "share_pct": round(100.0 * n / len(rows_with), 1)})
        blank = sum(1 for c in cells if c not in content and c not in chrome)
        pct = 100.0 * blank / max(1, len(cells))
        blanks.append({"region": label(i), "cells": len(cells), "blank_pct": round(pct, 1),
                       "sparse": pct > SPARSE_BLANK and len(cells) >= SPARSE_MIN_CELLS})
    m_mark = {"threshold_row_share": MARKER_ROW_SHARE, "items": markers, "notable": bool(markers)}

    # 4. duplicate status signals: per (region, row) text
    by_row: dict[tuple[int, int], list[tuple[int, str]]] = {}
    for i, cells in region_cells.items():
        for (x, y) in cells:
            by_row.setdefault((i, y), []).append((x, ch_at(x, y)))
    combos: dict[str, int] = {}
    examples = []
    for (i, y), items in sorted(by_row.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        text = "".join(c for _, c in sorted(items)).strip()
        if not text:
            continue
        first = text.split()[0]
        kinds = []
        if any(g in text for g in STATUS_GLYPHS) or (first in tuple(STATUS_LEAD) and len(text.split()) > 1):
            kinds.append("glyph")
        if TAG_RE.search(text):
            kinds.append("tag")
        if WORD_RE.search(TAG_RE.sub(" ", text)):
            kinds.append("word")
        toks = [t.lower() for t in text.split()]
        repeated = bool(kinds) and any(a == b and len(a) >= 3 and a.isalpha() for a, b in zip(toks, toks[1:]))
        # glyph + word is the required baseline (glyph + color + word) and is never flagged; a bracket tag next to a
        # glyph, all three at once, or a repeated type word is redundancy.
        if ("tag" in kinds and "glyph" in kinds) or len(kinds) >= 3 or repeated:
            key = ("+".join(kinds) if len(kinds) > 1 and ("tag" in kinds) else "") + ("+" if kinds and repeated and "tag" in kinds else "") + ("repeated-word" if repeated else "")
            key = key or "+".join(kinds)
            combos[key] = combos.get(key, 0) + 1
            if len(examples) < 6:
                examples.append({"row": y, "region": label(i), "encodings": kinds + (["repeated-word"] if repeated else []),
                                 "text": re.sub(r"\s{2,}", "  ", text)[:70]})
    m_dup = {"rows_flagged": sum(combos.values()), "by_encoding": combos, "examples": examples,
             "threshold": "glyph + tag, glyph + tag + word, or a repeated type word on one row", "notable": bool(combos)}

    verdicts = {
        "chrome_share": (f"{share:.1f} % of {n_chrome + n_content} non-space cells are chrome: "
                         + ("notable (> 50 %: drop rules/boxes, let alignment and spacing group)" if m_chrome["notable"] else "ok (<= 50 %)")),
        "border_nesting": (f"max {depth} nested box(es) around content: "
                           + ("notable (> 1: flatten, one border level per region)" if m_nest["notable"] else "ok (<= 1)")),
        "repeated_markers": ("none: ok" if not markers else
                             f"{len(markers)} marker column(s) on >= 90 % of rows: notable (a marker on every row marks nothing)"),
        "duplicate_signals": ("none: ok" if not combos else
                              f"{m_dup['rows_flagged']} row(s) encode status redundantly ({', '.join(f'{k} x{v}' for k, v in combos.items())}): "
                              "notable (glyph + word is the baseline; keep one of tag/glyph, say the type once)"),
        "blank_share": ("no sparse region: ok" if not any(b["sparse"] for b in blanks) else
                        "sparse (> 90 % blank): " + ", ".join(b["region"] for b in blanks if b["sparse"])),
    }
    return {"source": name, "size": {"cols": W, "rows": H}, "chrome_share": m_chrome, "border_nesting": m_nest,
            "repeated_markers": m_mark, "duplicate_signals": m_dup, "blank_share": {"regions": blanks},
            "verdicts": verdicts}


def clutter_md(r: dict) -> str:
    v = r["verdicts"]
    c, n = r["chrome_share"], r["border_nesting"]
    out = [f"# Clutter metrics: {r['source'] or 'frame'} ({r['size']['cols']}x{r['size']['rows']})", "",
           "| Metric | Value | Verdict |", "|---|---|---|",
           f"| chrome share | {c['share_pct']} % ({c['chrome_cells']} chrome / {c['content_cells']} content cells) | {v['chrome_share'].split(': ', 1)[1]} |",
           f"| border nesting depth | {n['max_depth']} ({n['boxes']} boxes) | {v['border_nesting'].split(': ', 1)[1]} |",
           f"| repeated markers | {len(r['repeated_markers']['items'])} | {v['repeated_markers'].split(': ', 1)[1] if ': ' in v['repeated_markers'] else v['repeated_markers']} |",
           f"| duplicate status signals | {r['duplicate_signals']['rows_flagged']} row(s) | {v['duplicate_signals'].split(': ', 1)[-1]} |",
           f"| blank share | {max((b['blank_pct'] for b in r['blank_share']['regions']), default=0)} % max | {v['blank_share']} |", ""]
    if r["repeated_markers"]["items"]:
        out += ["## Repeated markers", ""] + [
            f"- {m['region']}: `{m['glyph']}` {m['codepoint']} at column {m['col']} on {m['rows_hit']}/{m['rows']} rows" for m in r["repeated_markers"]["items"]] + [""]
    if r["duplicate_signals"]["examples"]:
        out += ["## Duplicate status signals (examples)", ""] + [
            f"- row {e['row']} [{e['region']}] {'+'.join(e['encodings'])}: `{e['text']}`" for e in r["duplicate_signals"]["examples"]] + [""]
    out += ["## Blank share per region", ""] + [
        f"- {b['region']}: {b['blank_pct']} % blank of {b['cells']} cells" + (" (sparse)" if b["sparse"] else "") for b in r["blank_share"]["regions"]]
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="ANSI frame -> cell-grid JSON (+ --describe live-capture skeleton).",
                                 epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="ANSI file, or - for stdin")
    ap.add_argument("--theme", default=None, help="theme id or path (default: a .mock's header theme, else catppuccin-mocha)")
    ap.add_argument("--clutter", action="store_true", help="print clutter metrics (thresholds below); input may be a .mock")
    ap.add_argument("--format", choices=["md", "json"], default="md", help="with --clutter: output format (default md)")
    ap.add_argument("--cols", type=int, help="force grid width (pad/crop)")
    ap.add_argument("--rows", type=int, help="force grid height (pad/crop)")
    ap.add_argument("--describe", action="store_true", help="emit a tui-description skeleton instead of the grid")
    ap.add_argument("--pretty", action="store_true", help="indent the JSON (grid output is large)")
    ap.add_argument("-o", "--out", help="output file (default stdout)")
    a = ap.parse_args(argv)
    try:
        text = sys.stdin.read() if a.input == "-" else Path(a.input).read_text(encoding="utf-8", errors="replace")
        theme_id = a.theme
        if a.clutter and a.input.endswith(".mock"):      # render the mockup first (no color needed for the metrics)
            from _mock import parse_mock
            from render_mockup import DEFAULT_THEME, render
            mock = parse_mock(text, a.input)
            theme_id = theme_id or mock.theme or DEFAULT_THEME
            theme = load_theme(theme_id)
            text = render(mock, theme, "truecolor")
        else:
            theme = load_theme(theme_id or "catppuccin-mocha")
    except (OSError, ValueError, KeyError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    grid = parse_ansi(text, a.cols, a.rows)
    colors = Colors(theme)
    if a.clutter:
        r = clutter_metrics(grid, theme, "" if a.input == "-" else Path(a.input).name)
        out = json.dumps(r, ensure_ascii=False, indent=2) + "\n" if a.format == "json" else clutter_md(r)
        if a.out:
            Path(a.out).write_text(out, encoding="utf-8")
        else:
            sys.stdout.write(out)
        return 0
    if a.describe:
        doc = Describer(grid, theme, colors, None if a.input == "-" else Path(a.input).name).run()
    else:
        doc = build_grid_json(grid, colors)
    s = json.dumps(doc, ensure_ascii=False, indent=2 if a.pretty else None, separators=None if a.pretty else (",", ":")) + "\n"
    if a.out:
        Path(a.out).write_text(s, encoding="utf-8")
    else:
        sys.stdout.write(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
