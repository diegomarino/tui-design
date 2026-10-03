#!/usr/bin/env python3
"""Reconstruct a `tui-description` JSON as a `.mock` that renders ONLY what the description asserts.

Drawn: region borders (style -> glyph set, `sides`), region titles (only on a border, or with position `inline`; they stay between the corner-adjacent
border cells so `render_mockup.py --check` box integrity holds: placed at a title element on the border row, else where `screen_text` shows the text, else by
`position`; one padding space per side only where it fits and `screen_text`, when present, shows a space) and border labels, element texts
at their bbox (multi-line text on following rows, `spans` and element `style` as tokens), optional
`screen_text` as an unstyled base layer (only with --use-screen-text). Everything unclaimed stays blank, so
omissions in a description show up as diffs when the reconstruction is compared with the source frame
(`compare.py`) - that is the point.

Colours: canonical tokens are used as is. Non-canonical `ansi.*` / `p:N` / raw-only / token-less colours map to
the nearest canonical token of the right kind (fg or bg) by OKLab distance in the chosen theme (<= 0.08), else
the cell keeps the default style; every lossy mapping is recorded as a `#! note:` header line. `term.fg` and
`term.bg` mean "default" (no tag). Attribute mapping: double/curly underline -> underline;
blink, hidden, overline are dropped (noted); `reverse` + explicit colours: the colours are as painted (ansi_grid convention), so they are written swapped with `inverse` when both map to tokens of the right kind, else as painted without `inverse` (noted). `[?]` in a text becomes `?`, `[?*]` becomes `???`.
Every `#! region` of the description (including children) is emitted as ground truth.

Examples:
  python3 scripts/description_to_mock.py desc.json -o recon.mock
  python3 scripts/description_to_mock.py desc.json --use-screen-text --theme dracula-classic -o recon.mock
  python3 scripts/ansi_grid.py frame.ansi --describe | python3 scripts/description_to_mock.py - | \\
      python3 scripts/render_mockup.py - --check

Exit: 0 ok, 1 the reconstruction has lint ERRORs (should not happen), 2 unreadable input / environment.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _mock import char_width, known_roles, parse_mock  # noqa: E402
from _theme import ANSI_NAMES, load_theme, load_token_defs, nearest256, oklab_distance, palette256  # noqa: E402

DEFAULT_THEME = "catppuccin-mocha"
MAX_DIST = 0.08
GLYPHS = {   # style -> (tl, tr, bl, br, horizontal, vertical)
    "single": "┌┐└┘─│", "rounded": "╭╮╰╯─│", "double": "╔╗╚╝═║", "heavy": "┏┓┗┛━┃",
    "dashed": "┌┐└┘╌╎", "ascii": "++++-|", "block": "▛▜▙▟▀▌", "mixed": "┌┐└┘─│",
}
ATTR_MAP = {"bold": "bold", "dim": "dim", "italic": "italic", "underline": "underline", "strike": "strike",
            "reverse": "inverse", "double_underline": "underline", "curly_underline": "underline"}
NAME_MAP = {"red": ("fg", "status.error"), "green": ("fg", "status.success"), "yellow": ("fg", "status.warning"),
            "orange": ("fg", "status.warning"), "blue": ("fg", "accent.primary"), "gray": ("fg", "fg.muted")}


@dataclass
class Cell:
    ch: str = " "
    w: int = 1                      # 0 = continuation of a wide glyph
    fg: dict | None = None          # schema colour objects (kept raw so scorers can resolve their own way)
    bg: dict | None = None
    attrs: frozenset = frozenset()
    claimed: bool = False           # set by a region/element/span; False = untouched default


# ---------------------------------------------------------------- canvas

def flatten_regions(regions: list, parent_z: int = 0) -> list[dict]:
    out = []
    for r in regions or []:
        out.append(r)
        out += flatten_regions(r.get("children", []), r.get("z", parent_z))
    return out


def new_canvas(cols: int, rows: int) -> list[list[Cell]]:
    return [[Cell() for _ in range(cols)] for _ in range(rows)]


def put_text(cv, x: int, y: int, text: str, fg=None, bg=None, attrs=frozenset(), claimed=True, inherit=False) -> None:
    """Write text starting at cell (x, y); wide glyphs take two cells, combining marks join the previous cell.
    inherit=True: style fields the caller leaves unset keep what is already drawn in the cell (text-only elements)."""
    if not (0 <= y < len(cv)):
        return
    row = cv[y]
    for ch in text:
        w = char_width(ch)
        if w == 0:
            k = x - 1
            while k >= 0 and row[k].w == 0:
                k -= 1
            if 0 <= k < len(row):
                row[k].ch += ch
            continue
        if x < 0:
            x += w
            continue
        if x + w > len(row):
            break
        f, b, at = fg, bg, attrs
        if inherit:
            old = row[x]
            f, b, at = fg or old.fg, bg or old.bg, attrs or old.attrs
        row[x] = Cell(ch, w, f, b, at, claimed)
        if w == 2:
            row[x + 1] = Cell("", 0, f, b, at, claimed)
        x += w


def style_parts(style: dict | None) -> tuple[dict | None, dict | None, frozenset]:
    style = style or {}
    return style.get("fg"), style.get("bg"), frozenset(style.get("attrs", []))


def restyle(cv, x: int, y: int, length: int, style: dict | None) -> None:
    """Overlay a span style on cells x..x+length of row y (span offsets are cell offsets)."""
    fg, bg, attrs = style_parts(style)
    if not (0 <= y < len(cv)):
        return
    for cx in range(max(x, 0), min(x + length, len(cv[y]))):
        c = cv[y][cx]
        c.fg, c.bg = fg or c.fg, bg or c.bg
        c.attrs = c.attrs | attrs
        c.claimed = True


def draw_border(cv, r: dict) -> None:
    b = r.get("border") or {}
    style = b.get("style", "none")
    bb = r["bbox"]
    if style in ("none", None) or bb["w"] < 2 or bb["h"] < 2:
        return
    tl, tr, bl, br, hz, vt = GLYPHS.get(style, GLYPHS["single"])
    sides = set(b.get("sides") or ["top", "right", "bottom", "left"])
    fg, bg, attrs = style_parts(b.get("style_attrs"))
    x0, y0, x1, y1 = bb["x"], bb["y"], bb["x"] + bb["w"] - 1, bb["y"] + bb["h"] - 1
    rows, cols = len(cv), len(cv[0]) if cv else 0

    def put(x, y, ch):
        if ch and 0 <= y < rows and 0 <= x < cols:
            cv[y][x] = Cell(ch, 1, fg, bg, attrs, True)

    def corner(on_a, on_b, glyph, a_glyph, b_glyph):
        return glyph if on_a and on_b else a_glyph if on_a else b_glyph if on_b else ""

    for x in range(x0, x1 + 1):
        top = "top" in sides
        bot = "bottom" in sides
        if x == x0:
            put(x, y0, corner(top, "left" in sides, tl, hz, vt))
            put(x, y1, corner(bot, "left" in sides, bl, hz, vt))
        elif x == x1:
            put(x, y0, corner(top, "right" in sides, tr, hz, vt))
            put(x, y1, corner(bot, "right" in sides, br, hz, vt))
        else:
            put(x, y0, hz if top else "")
            put(x, y1, hz if bot else "")
    for y in range(y0 + 1, y1):
        put(x0, y, vt if "left" in sides else "")
        put(x1, y, vt if "right" in sides else "")


def str_width(s: str) -> int:
    return sum(char_width(c) for c in s)


def cell_text(row: str, x: int) -> str | None:
    """Character drawn at display column x of a screen_text row (None when beyond the row; '' for a wide glyph's 2nd cell)."""
    pos = 0
    for ch in row:
        w = char_width(ch)
        if w == 0:
            continue
        if pos == x:
            return ch
        if w == 2 and pos + 1 == x:
            return ""
        pos += w
    return None


def find_run(row: str, text: str, lo: int, hi: int) -> int | None:
    """Display column of the first occurrence of `text` inside columns [lo, hi) of a screen_text row."""
    w = str_width(text)
    for x in range(lo, hi - w + 1):
        if "".join(cell_text(row, x + k) or "" for k in range(w)) == text:
            return x
    return None


def title_run(r: dict, text: str, pos: str, y: int, elements: list[dict], screen: list[str]) -> tuple[int, str, bool, bool]:
    """-> (x, text, pad_left, pad_right) of a bordered region's title. The run must stay between the corners and the cells next to
    them (x0+2 .. x1-2): those cells hold box glyphs (a title may not touch a corner). Position comes from, in order: a title element
    on the border row, the `screen_text` row, the position keyword. Padding spaces are drawn only where they fit and, when
    `screen_text` is known, only where it shows a space."""
    bb = r["bbox"]
    x0, x1 = bb["x"], bb["x"] + bb["w"] - 1
    lo, hi = x0 + 2, x1 - 1                          # usable cells [lo, hi)
    avail = max(hi - lo, 0)
    row = screen[y] if y < len(screen) else None
    x = None
    for e in elements:
        eb = e.get("bbox") or {}
        if e.get("region") == r.get("id") and eb.get("y") == y and eb.get("h", 1) == 1 and text in (e.get("text") or ""):
            x = eb["x"] + str_width(e["text"][:e["text"].index(text)])
            break
    if x is None and row is not None:
        x = find_run(row, text, x0 + 1, x1)
    w = str_width(text)
    if x is None:                                    # keyword placement, conventional one-space padding
        padded = w + 2 <= avail
        span = w + (2 if padded else 0)
        if pos.endswith("center"):
            start = x0 + max((bb["w"] - span) // 2, 0)
        elif pos.endswith("right"):
            start = hi - span
        else:
            start = lo
        start = min(max(start, lo), max(hi - span, lo))
        x = start + (1 if padded else 0)
    if w > avail:                                    # cannot fit between the corners: cut it (cells, not characters)
        out, used = "", 0
        for c in text:
            cw = char_width(c)
            if used + cw > avail:
                break
            out, used = out + c, used + cw
        text, w = out, used
        x = lo
    x = min(max(x, lo), max(hi - w, lo))
    def pad(px: int) -> bool:
        if not (lo <= px < hi):
            return False
        return cell_text(row, px) == " " if row is not None else True
    return x, text, pad(x - 1), pad(x + w)


def draw_title(cv, r: dict, elements: list[dict] | None = None, screen: list[str] | None = None) -> None:
    t = r.get("title")
    if not t or not t.get("text"):
        return
    bb = r["bbox"]
    bordered = (r.get("border") or {}).get("style", "none") not in ("none", None) and bb["w"] >= 2 and bb["h"] >= 2
    pos = t.get("position") or "top_left"
    if not bordered and pos != "inline":      # a title without a border or an explicit `inline` position is metadata, not screen text
        return
    y = bb["y"] + bb["h"] - 1 if pos.startswith("bottom") else bb["y"]
    fg, bg, attrs = style_parts(t.get("style"))
    if not bordered:
        put_text(cv, bb["x"], y, t["text"], fg, bg, attrs)
        return
    x, text, pad_l, pad_r = title_run(r, t["text"], pos, y, elements or [], screen or [])
    bfg, bbg, battrs = style_parts((r.get("border") or {}).get("style_attrs"))      # padding spaces keep the border colour
    if pad_l:
        put_text(cv, x - 1, y, " ", bfg, bbg, battrs)
    put_text(cv, x, y, text, fg, bg, attrs)
    if pad_r:
        put_text(cv, x + str_width(text), y, " ", bfg, bbg, battrs)


def draw_border_labels(cv, r: dict) -> None:
    bb = r["bbox"]
    for lab in r.get("border_labels", []):
        if not lab.get("text"):
            continue
        lb = lab.get("bbox")
        text = lab["text"]
        if lb:
            x, y = lb["x"], lb["y"]
        else:      # default: bottom-right run, kept between the corner-adjacent border cells
            avail = max(bb["w"] - 4, 0)
            while str_width(text) > avail and text:
                text = text[:-1]
            x, y = bb["x"] + bb["w"] - 2 - str_width(text), bb["y"] + bb["h"] - 1
        fg, bg, attrs = style_parts(lab.get("style"))
        put_text(cv, x, y, text, fg, bg, attrs)


def clean_text(text: str) -> str:
    return text.replace("[?*]", "???").replace("[?]", "?")


def draw_element(cv, e: dict) -> None:
    bb = e["bbox"]
    fg, bg, attrs = style_parts(e.get("style"))
    if bg:                           # an element background fills its bbox (e.g. a selected row)
        for y in range(bb["y"], min(bb["y"] + bb["h"], len(cv))):
            restyle(cv, bb["x"], y, bb["w"], {"bg": bg})
    text = clean_text(e.get("text", ""))
    if e.get("type") == "cursor" and not text.strip():
        text, attrs = " ", attrs | {"reverse"}
    for i, line in enumerate(text.split("\n")):
        put_text(cv, bb["x"], bb["y"] + i, line, fg, bg, attrs, inherit=True)
    for sp in e.get("spans", []):
        restyle(cv, bb["x"] + sp["start"], bb["y"], sp["len"], sp.get("style"))


def build_canvas(desc: dict, use_screen_text: bool = False) -> list[list[Cell]]:
    size = desc["meta"]["size"]
    cv = new_canvas(size["cols"], size["rows"])
    if use_screen_text:
        for y, line in enumerate(desc.get("screen_text") or []):
            put_text(cv, 0, y, line, claimed=False)
    regs = [r for r in flatten_regions(desc.get("regions", [])) if r.get("bbox")]
    regs.sort(key=lambda r: (r.get("z", 0), -r["bbox"]["w"] * r["bbox"]["h"], r.get("order", 0)))
    elements = desc.get("elements", [])
    for r in regs:
        draw_border(cv, r)
        draw_title(cv, r, elements, desc.get("screen_text"))
        draw_border_labels(cv, r)
    for e in sorted(desc.get("elements", []), key=lambda e: e.get("order", 0)):
        draw_element(cv, e)
    return cv


# ---------------------------------------------------------------- colour -> token

class Mapper:
    def __init__(self, theme, defs):
        self.theme, self.defs = theme, defs
        self.notes: list[str] = []
        self._cache: dict = {}

    def note(self, msg: str) -> None:
        if msg not in self.notes:
            self.notes.append(msg)

    def slot_hex(self, slot: str) -> str | None:
        if slot.startswith("ansi.") and slot[5:] in ANSI_NAMES:
            return self.theme.ansi[ANSI_NAMES.index(slot[5:])]
        if slot.startswith("p:") and slot[2:].isdigit() and int(slot[2:]) < 256:
            return palette256(self.theme.ansi)[int(slot[2:])]
        return None

    def nearest(self, hexv: str, kind: str) -> tuple[str | None, float]:
        best = min(((oklab_distance(hexv, h), t) for t, h in self.theme.tokens.items()
                    if self.defs[t]["kind"] == kind), default=(9.0, None))
        return best[1], best[0]

    def token(self, c: dict | None, kind: str) -> str | None:
        """Canonical token of `kind` ('fg'|'bg') for a schema colour object, or None = default style."""
        if not c:
            return None
        key = (kind, json.dumps(c, sort_keys=True))
        if key not in self._cache:
            self._cache[key] = self._token(c, kind)
        return self._cache[key]

    def _token(self, c: dict, kind: str) -> str | None:
        cands = [t for t in [c.get("token"), *c.get("token_candidates", [])] if t]
        for t in cands:
            if t in self.defs and self.defs[t]["kind"] == kind:
                return t
        tok = cands[0] if cands else None
        if tok in ("term.fg", "term.bg"):
            return None
        hexv = c.get("raw") or (self.slot_hex(tok) if tok else None)
        if not hexv and tok in self.defs:
            hexv = self.theme.tokens.get(tok)
        if hexv:
            best, dist = self.nearest(hexv, kind)
            if best and dist <= MAX_DIST:
                if tok not in self.defs:
                    self.note(f"{tok or hexv} mapped to {best} (nearest {kind} token, OKLab {dist:.3f})")
                return best
            self.note(f"{tok or hexv} has no {kind} token within OKLab {MAX_DIST}; left default")
            return None
        name = c.get("name")
        if name in NAME_MAP and NAME_MAP[name][0] == kind:
            self.note(f"colour name {name!r} guessed as {NAME_MAP[name][1]}")
            return NAME_MAP[name][1]
        if tok or name:
            self.note(f"colour {tok or name!r} not mappable; left default")
        return None

    def attrs(self, attrs: frozenset) -> tuple[str, ...]:
        out = []
        for a in ("bold", "dim", "italic", "underline", "reverse", "double_underline", "curly_underline", "strike",
                  "blink", "hidden", "overline"):
            if a in attrs:
                if a in ATTR_MAP:
                    out.append(ATTR_MAP[a])
                else:
                    self.note(f"attribute {a!r} not representable in .mock; dropped")
        return tuple(dict.fromkeys(out))


# ---------------------------------------------------------------- emit

def esc(s: str) -> str:
    return s.replace("{", "{{").replace("}", "}}")


def canvas_to_body(cv, mp: Mapper) -> list[str]:
    lines = []
    for row in cv:
        runs: list[tuple[tuple, str]] = []
        for c in row:
            if c.w == 0:
                continue
            fg = mp.token(c.fg, "fg")
            bg = mp.token(c.bg, "bg")
            attrs = c.attrs
            if "reverse" in attrs and c.fg and c.bg:       # colours are as painted: express them through `inverse` when possible
                sfg, sbg = mp.token(c.bg, "fg"), mp.token(c.fg, "bg")
                if sfg and sbg:
                    fg, bg = sfg, sbg
                else:
                    attrs = attrs - {"reverse"}
                    mp.note("reverse with colours not expressible as fg/bg tokens: emitted as painted, without `inverse`")
            key = (None if fg == "fg.default" else fg, None if bg == "bg.base" else bg, mp.attrs(attrs))
            if runs and runs[-1][0] == key:
                runs[-1] = (key, runs[-1][1] + c.ch)
            else:
                runs.append((key, c.ch))
        while runs and runs[-1][0] == (None, None, ()) and not runs[-1][1].strip():
            runs.pop()
        if runs and runs[-1][0] == (None, None, ()):
            runs[-1] = (runs[-1][0], runs[-1][1].rstrip())
        out = []
        for (fg, bg, attrs), text in runs:
            spec = " ".join(([fg] if fg else []) + list(attrs) + ([f"on:{bg}"] if bg else []))
            out.append(f"{{{spec}}}{esc(text)}{{/}}" if spec else esc(text))
        lines.append("".join(out))
    return lines


def region_lines(desc: dict, cols: int, rows: int, notes: list[str]) -> list[str]:
    roles = known_roles()
    out = []
    for r in flatten_regions(desc.get("regions", [])):
        bb, rid = r.get("bbox"), r.get("id", "")
        if not bb or not rid.startswith("r"):
            continue
        x, y, w, h = bb["x"], bb["y"], bb["w"], bb["h"]
        if x < 0 or y < 0 or x + w > cols or y + h > rows:
            notes.append(f"region {rid} bbox {x},{y},{w},{h} outside {cols}x{rows}; omitted")
            continue
        title = " ".join(((r.get("title") or {}).get("text") or "").split())
        out.append(f"#! region {rid} {r['role'] if r.get('role') in roles else 'other'} {x},{y},{w},{h}"
                   + (f" {title}" if title else ""))
    return out


def description_to_mock(desc: dict, theme_id: str | None = None, use_screen_text: bool = False) -> str:
    size = desc["meta"]["size"]
    cols, rows = size["cols"], size["rows"]
    tg = (desc["meta"].get("theme_guess") or {}).get("name")
    theme = load_theme(theme_id or tg or DEFAULT_THEME)
    mp = Mapper(theme, load_token_defs())
    cv = build_canvas(desc, use_screen_text)
    body = canvas_to_body(cv, mp)
    notes = mp.notes
    regs = region_lines(desc, cols, rows, notes)
    subject = desc["meta"].get("subject")
    head = ["#! tui-mockup 1", f"#! size: {cols}x{rows}",
            f"#! title: Reconstruction of a description{f' ({subject})' if subject else ''}"]
    if theme_id or tg:
        head.append(f"#! theme: {theme.id}")
    head += regs
    head += [f"#! note: {n}" for n in notes[:20]]
    if len(notes) > 20:
        head.append(f"#! note: ... {len(notes) - 20} more notes omitted")
    return "\n".join(head + body) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="tui-description JSON -> .mock reconstruction (asserted content only).",
                                 epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("description", help="tui-description JSON file ('-' = stdin)")
    ap.add_argument("--use-screen-text", action="store_true",
                    help="draw `screen_text` as an unstyled base layer (default: ignore it, assert only regions/elements)")
    ap.add_argument("--theme", help="theme id used to map non-canonical colours (default: meta.theme_guess.name, else "
                                    + DEFAULT_THEME + ")")
    ap.add_argument("-o", "--out", help="write the .mock here instead of stdout")
    a = ap.parse_args(argv)
    try:
        raw = sys.stdin.read() if a.description == "-" else Path(a.description).read_text(encoding="utf-8")
        desc = json.loads(raw)
        desc["meta"]["size"]["cols"], desc["meta"]["size"]["rows"]
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"description_to_mock: cannot read a tui-description from {a.description}: {e}", file=sys.stderr)
        return 2
    try:
        text = description_to_mock(desc, a.theme, a.use_screen_text)
    except (FileNotFoundError, ValueError, KeyError) as e:
        print(f"description_to_mock: {e}", file=sys.stderr)
        return 2
    errors = [f for f in parse_mock(text, a.out or "<recon>").findings if f.level == "ERROR"]
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    for f in errors:
        print(f.fmt(a.out or "<recon>"), file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
