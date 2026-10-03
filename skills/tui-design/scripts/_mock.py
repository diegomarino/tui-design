"""Parser + linter for the `.mock` v1 mockup markup (private to render_mockup.py; stdlib only).

Format: references/formats.md "Mockup format". Glyph policy: references/visual-vocabulary.md
"Linter policy". Only the pieces needed by render_mockup.py live here.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from _craft import craft_findings
from _theme import ATTRS, SKILL_ROOT, load_token_defs

VISUAL_VOCAB = SKILL_ROOT / "references" / "visual-vocabulary.md"

SCHEMA_FILE = SKILL_ROOT / "references" / "schemas" / "tui-description.schema.json"
FALLBACK_ROLES = (
    "screen header menubar tabbar toolbar sidebar list table tree detail editor log chart form input "
    "statusbar footer keybar modal toast popup_menu tooltip panel other"
).split()

# Text-default emoji: EAW N/A but widen to 2 with VS16 and may render as colour emoji (WARN).
TEXT_EMOJI = set(
    "✔✖⚠⚙❤ℹ⏺⏸▶◀♥✳↔↕↩↪⏏⏭⏮⏯⏹☀☁☂☎☑☠☢☣☮☯☸☹☺♀♂♠♣♦♨♻⚒⚔⚖⚗⚛⚜⚧⚰⚱✂✈✉✏✒✝✡✴❄❇❣➡⬅⬆⬇"
    "⤴⤵▪▫◻◼©®™‼⁉⌨⛈⛏⛑⛓⛩⛰⛱⛴⛷⛸⛹✌✍☄☘☝☪☭☦"
)
# Replacement hints (the SAFE list of references/visual-vocabulary.md).
HINTS = {
    "✔": "use ✓ U+2713", "✖": "use ✗ U+2717 or ✕ U+2715", "⚠": "use ▲ U+25B2 (status glyph table: references/visual-vocabulary.md V5)",
    "ℹ": "use 'i'", "⚙": "use a text label or ⋮ U+22EE", "▶": "use ▸ U+25B8 or ► U+25BA",
    "◀": "use ◂ U+25C2 or ◄ U+25C4", "❤": "use a word or ◉", "♥": "use a word or ◉",
    "✳": "use ✱ U+2731", "⏺": "use ◉ U+25C9 or ⬤ U+2B24", "⏸": "use '||'", "…": "use ⋯ U+22EF (N) or '...'",
    "—": "use '-' or '─'", "–": "use '-'", "√": "use ✓ U+2713", "×": "use ✕ U+2715 or 'x'",
}
# A-class chrome allow-list (INFO; ERROR under --strict-ambiguous): r5 2.2 list + arrows used by key hints.
ALLOW_A = set("●○◆■▲▼★…·•→×√←↑↓")
# Dashes are EAW=A but ubiquitous in copy and single-width in monospace fonts: INFO like the chrome set.
DASHES = set("—–")
SAFE_HINT = "pick an N/Na/H glyph (r5 2.2 SAFE list) or accept ambiguity with the default profile"


@dataclass
class Finding:
    line: int
    col: int
    level: str   # ERROR | WARN | INFO
    msg: str
    hint: str = ""
    tag: str = ""   # "caps" = capability-profile finding (never collapsed into the glyph INFO summary)

    def fmt(self, path: str) -> str:
        h = f" ({self.hint})" if self.hint else ""
        return f"{path}:{self.line}:{self.col}: {self.level}: {self.msg}{h}"


@dataclass
class Region:
    id: str
    role: str
    x: int
    y: int
    w: int
    h: int
    title: str = ""
    line: int = 0


@dataclass
class Style:
    fg: str | None = None
    bg: str | None = None
    attrs: tuple[str, ...] = ()


@dataclass
class Cell:
    text: str          # base char plus any combining marks
    width: int         # 1 or 2
    style: Style
    col: int = 0       # 1-based source column of the cell's first code point (0 = synthetic)


@dataclass
class Mock:
    path: str = "<stdin>"
    cols: int = 80
    rows: int = 24
    title: str = ""
    state: str = ""
    theme: str = ""
    notes: list[str] = field(default_factory=list)          # `#! note:` lines (free text, repeatable)
    body_line: int = 1                                       # 1-based source line of body row 0
    regions: list[Region] = field(default_factory=list)
    focus: str = ""                                          # `#! focus <region-id>`: audit truth, ignored by rendering
    selected: list[tuple[str, int]] = field(default_factory=list)   # `#! selected <region-id> <row>`; row = 0-based offset inside the region interior
    caps: "Caps" = field(default_factory=lambda: Caps())     # `#! caps:` header (+ --caps override); default = everything allowed
    grid: list[list[Cell]] = field(default_factory=list)   # one list of cells per source row
    findings: list[Finding] = field(default_factory=list)


# ------------------------------------------------------------------ widths and glyph classes

def char_width(ch: str) -> int:
    cat = unicodedata.category(ch)
    if cat in ("Mn", "Me", "Cf"):
        return 0
    if cat in ("Cc", "Cs"):
        return 0 if ch not in "\t" else 1
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def str_width(s: str) -> int:
    return sum(char_width(c) for c in s)


def known_roles() -> list[str]:
    try:
        schema = json.loads(SCHEMA_FILE.read_text())
        return list(schema["$defs"]["region"]["properties"]["role"]["enum"])
    except (OSError, KeyError, ValueError):
        return FALLBACK_ROLES


# ------------------------------------------------------------------ capability profile

CAP_COLORS = {"truecolor": "truecolor", "256": "256", "16": "16", "none": "nocolor"}   # caps colors= -> render depth
CAP_GLYPHS = ("ascii", "unicode", "nerd")
CAP_KEYS = ("attrs", "colors", "glyphs", "widgets", "source")
CAP_SOURCES = ("test-card", "docs", "code", "assumed")   # where the profile comes from; only test-card/docs are evidence


class Caps:
    """Capability profile of the target host: `attrs=bold,dim colors=16 glyphs=unicode widgets=tabs,list`.

    `given` holds only the keys that were written explicitly (key -> tuple of values); every property falls
    back to the default (all attrs, truecolor, unicode, no widget list)."""

    def __init__(self, given: dict | None = None):
        self.given: dict[str, tuple[str, ...]] = dict(given or {})

    @property
    def attrs(self) -> tuple[str, ...]:
        return tuple(self.given["attrs"]) if "attrs" in self.given else tuple(ATTRS)

    @property
    def colors(self) -> str:
        return self.given["colors"][0] if "colors" in self.given else "truecolor"

    @property
    def glyphs(self) -> str:
        return self.given["glyphs"][0] if "glyphs" in self.given else "unicode"

    @property
    def source(self) -> str:
        return self.given["source"][0] if "source" in self.given else ""

    @property
    def widgets(self) -> tuple[str, ...]:
        return tuple(self.given.get("widgets", ()))

    @property
    def depth(self) -> str:
        """The render depth this profile implies (colors=none -> nocolor: no color, attributes kept)."""
        return CAP_COLORS[self.colors]

    def merged(self, other: "Caps") -> "Caps":
        return Caps({**self.given, **other.given})

    def spec(self) -> str:
        return " ".join(f"{k}={','.join(self.given[k])}" for k in CAP_KEYS if k in self.given)

    def __bool__(self) -> bool:
        return bool(self.given)


def parse_caps(text: str) -> tuple[Caps, list[str]]:
    """Parse `key=v,v key=v` into (Caps, error messages). Unknown keys and values are errors."""
    given: dict[str, tuple[str, ...]] = {}
    errs: list[str] = []
    for item in text.split():
        key, sep, val = item.partition("=")
        if not sep or key not in CAP_KEYS:
            errs.append(f"bad caps item {item!r}; expected key=v,v with key in {' '.join(CAP_KEYS)}")
            continue
        vals = tuple(v for v in val.split(",") if v)
        if key in given:
            errs.append(f"duplicate caps key {key!r}")
        if key == "attrs":
            if vals == ("none",):
                vals = ()
            bad = [v for v in vals if v not in ATTRS]
            if bad:
                errs.append(f"unknown attrs {','.join(bad)} (valid: {' '.join(ATTRS)} or none)")
                continue
        elif key == "colors":
            if len(vals) != 1 or vals[0] not in CAP_COLORS:
                errs.append(f"bad colors {val!r} (valid: {' '.join(CAP_COLORS)})")
                continue
        elif key == "glyphs":
            if len(vals) != 1 or vals[0] not in CAP_GLYPHS:
                errs.append(f"bad glyphs {val!r} (valid: {' '.join(CAP_GLYPHS)})")
                continue
        elif key == "source":
            if len(vals) != 1 or vals[0] not in CAP_SOURCES:
                errs.append(f"bad source {val!r} (valid: {' '.join(CAP_SOURCES)})")
                continue
        given[key] = vals
    return Caps(given), errs


# ------------------------------------------------------------------ ASCII fallbacks (visual-vocabulary.md V9)

# Built-in extras for glyphs V9 does not list (copy punctuation); V9 entries win.
FALLBACK_EXTRA = {"—": "-", "–": "-", "…": "...", "→": "->", "←": "<-", "↑": "^", "↓": "v", "×": "x", "•": "-"}
# Sharp corners and heavy/double rules: V9 only maps them in a comment or not at all.
FALLBACK_FORCE = {"┌": "+", "┐": "+", "└": "+", "┘": "+", "━": "-", "┃": "|", "═": "=", "║": "|"}
_V9: dict[str, str] | None = None
_V9_LINE = re.compile(r'([\w/]+):\s*\[\s*"([^"]*)"\s*,\s*"([^"]*)"\s*\]')


def v9_fallbacks(path: Path | None = None) -> dict[str, str]:
    """glyph -> ASCII fallback parsed from the V9 map in visual-vocabulary.md ({} when absent or unparsable)."""
    global _V9
    if path is None and _V9 is not None:
        return _V9
    out: dict[str, str] = {}
    try:
        text = (path or VISUAL_VOCAB).read_text(encoding="utf-8")
        m = re.search(r"^##\s+V9\b.*?$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
        for _role, glyphs, ascii_ in _V9_LINE.findall(m.group(1) if m else ""):
            g_, a_ = glyphs.strip(), ascii_.strip()
            if " " in g_:                       # "╭ ╮ ╰ ╯": space-separated glyphs share the one ASCII
                chars, per_char = [c for c in g_ if not c.isspace()], False
            else:                               # "▁▂▃▄", "├──": same length -> glyph i maps to ASCII char i
                chars, per_char = list(g_), len(a_) == len(g_) > 1
            for i, c in enumerate(chars):
                out.setdefault(c, a_[i] if per_char else (a_ or ascii_))
    except OSError:
        out = {}
    if path is None:
        _V9 = out
    return out


def ascii_fallback(ch: str) -> str:
    """ASCII replacement for a glyph: V9 first, then the built-in extras; "" when unknown."""
    return FALLBACK_FORCE.get(ch) or v9_fallbacks().get(ch) or FALLBACK_EXTRA.get(ch, "")


def classify_glyph(ch: str, strict: bool, nerd: bool, caps: Caps | None = None) -> tuple[str, str, str] | None:
    """Return (level, message, hint) for a body code point, or None when it is fine."""
    cp = ord(ch)
    cat = unicodedata.category(ch)
    eaw = unicodedata.east_asian_width(ch)
    u = f"U+{cp:04X}"
    if cp in (0xFE0F, 0xFE0E):
        return "ERROR", f"variation selector {u} in layout text", "never emit VS15/VS16; width is terminal-dependent"
    if cp == 0x200D:
        return "ERROR", f"zero-width joiner {u} in layout text", "ZWJ sequences have no stable cell width"
    if 0x1F1E6 <= cp <= 0x1F1FF or 0x1F3FB <= cp <= 0x1F3FF:
        return "ERROR", f"regional indicator / skin-tone modifier {u}", "remove it; use plain text"
    if cp == 0xFFFD:
        return "ERROR", "replacement character U+FFFD (encoding damage)", "re-save the file as UTF-8"
    if cat == "Cc" and ch != "\t":
        return "ERROR", f"control character {u}", "control codes cannot appear in a mockup"
    if ch == "\t":
        return "WARN", "tab character (rendered as 1 space)", "use spaces; tabs have no fixed width"
    if caps is not None and caps.glyphs == "ascii" and cp > 127:
        fb = ascii_fallback(ch)
        return ("ERROR", f"non-ASCII glyph {u} {ch} under caps glyphs=ascii",
                f"ASCII fallback (V9): {fb!r}" if fb else "no V9 fallback; use a plain ASCII character")
    if caps is not None and caps.glyphs == "nerd":
        nerd = True
    if cat == "Co" or 0xF0000 <= cp <= 0x10FFFF:
        if caps is not None and "glyphs" in caps.given and caps.glyphs == "unicode":
            return "ERROR", f"private-use glyph {u} (Nerd Font / Powerline) under caps glyphs=unicode", "use a SAFE Unicode glyph, or declare glyphs=nerd"
        if nerd:
            return None
        return "ERROR", f"private-use glyph {u} (Nerd Font / Powerline)", "use a SAFE Unicode glyph or pass --allow-nerd-font"
    if eaw in ("W", "F"):
        return "ERROR", f"wide glyph {u} {unicodedata.name(ch, '?')} (EAW={eaw}, 2 cells)", HINTS.get(ch, "use a 1-cell glyph; emoji/CJK break column alignment")
    if cat in ("Mn", "Me"):
        return "WARN", f"combining mark {u} (0 cells, font-dependent)", "precompose the character or avoid it"
    if ch in TEXT_EMOJI:
        return "WARN", f"text-default emoji {u} {ch} (2 cells with VS16, may render as colour emoji)", HINTS.get(ch, SAFE_HINT)
    if cp == 0x2800:
        return "WARN", "braille blank U+2800 (some fonts draw nothing)", "use a plain space outside graphs"
    if eaw == "A" and ch in DASHES:
        return ("ERROR" if strict else "INFO"), f"ambiguous-width (EAW=A) dash {u} {ch}", "single-width in monospace fonts; use '-' or '─' to be strict"
    if eaw == "A":
        chrome = 0x2500 <= cp <= 0x259F or 0x25A0 <= cp <= 0x25FF or ch in ALLOW_A
        if chrome:
            eaw_n = (0x254C <= cp <= 0x254F or 0x2574 <= cp <= 0x257F or cp in (0x2590, 0x2591)
                     or 0x2596 <= cp <= 0x259F)
            if eaw_n:
                return None
            return ("ERROR" if strict else "INFO"), f"ambiguous-width (EAW=A) chrome glyph {u} {ch}", "1 cell normally, 2 in CJK-ambiguous-wide terminals"
        return "WARN", f"ambiguous-width (EAW=A) glyph {u} {ch} outside the chrome allow-list", HINTS.get(ch, SAFE_HINT)
    return None


# ------------------------------------------------------------------ box integrity

# Corner glyphs per position (light/rounded/heavy/double/mixed) plus ASCII '+'.
_CORNERS = {
    "tl": set("┌╭┏╔╒╓┍┎+"), "tr": set("┐╮┓╗╕╖┑┒+"),
    "bl": set("└╰┗╚╘╙┕┖+"), "br": set("┘╯┛╝╛╜┙┚+"),
}
_ASCII_EDGE = set("-=+|")
_SCROLL = set("▀▐▌█▓▒░▕▏▎▍▋▊▉")      # scrollbar thumb/track glyphs may replace a vertical edge cell


def _is_box(ch: str) -> bool:
    return 0x2500 <= ord(ch[0]) <= 0x257F or ch in _ASCII_EDGE


def _row_cells(row: list[Cell]) -> dict[int, Cell]:
    """Display column -> cell (a wide glyph occupies its first column only)."""
    out: dict[int, Cell] = {}
    x = 0
    for c in row:
        out[x] = c
        x += c.width
    return out


def check_box_integrity(m: Mock) -> None:
    """ERROR when text overwrites the border of a `#! region` whose bbox corners are box-drawing corners.

    Top/bottom edges may carry title runs (any text between box glyphs, never touching a corner);
    the vertical sides must hold box glyphs (scrollbar block glyphs are tolerated) all the way down.
    """
    rows = [_row_cells(r) for r in m.grid]

    def cell(x: int, y: int) -> tuple[str, int, int]:
        """(char, source line, source col) at display position; blank beyond the row."""
        line = m.body_line + y
        r = rows[y] if y < len(rows) else {}
        c = r.get(x)
        if c is None:
            used = max((k + r[k].width for k in r), default=0)
            return " ", line, (max((r[k].col for k in r), default=0) + 1 if x >= used else 1)
        return c.text, line, c.col or 1

    for reg in m.regions:
        x0, y0, x1, y1 = reg.x, reg.y, reg.x + reg.w - 1, reg.y + reg.h - 1
        if reg.w < 2 or reg.h < 2 or x0 < 0 or y0 < 0 or x1 >= m.cols or y1 >= m.rows:
            continue
        corners = (("tl", x0, y0), ("tr", x1, y0), ("bl", x0, y1), ("br", x1, y1))
        missing = [(x, y) for k, x, y in corners if cell(x, y)[0][0] not in _CORNERS[k]]
        if len(missing) > 1:                   # not a box (>=3 intact corners = a box with one overwritten corner)
            continue
        bad: list[tuple[int, int]] = list(missing)
        for y in (y0, y1):                     # horizontal edges: a title run may sit between box glyphs
            for x in {x0 + 1, x1 - 1} if reg.w > 2 else ():
                if not _is_box(cell(x, y)[0][0]):
                    bad.append((x, y))
        for y in range(y0 + 1, y1):            # vertical sides: no text at all
            for x in (x0, x1):
                ch = cell(x, y)[0][0]
                if not (_is_box(ch) or ch in _SCROLL):
                    bad.append((x, y))
        for x, y in sorted(set(bad), key=lambda p: (p[1], p[0])):
            ch, line, col = cell(x, y)
            m.findings.append(Finding(line, col, "ERROR",
                                      f"region {reg.id} border overwritten at ({x},{y}) by {ch!r}",
                                      "keep text inside the box; titles sit between ─ segments"))


# ------------------------------------------------------------------ parsing

REGION_RE = re.compile(r"^region\s+(\S+)\s+(\S+)\s+(-?\d+),(-?\d+),(-?\d+),(-?\d+)(?:\s+(.*))?$")
SIZE_RE = re.compile(r"^(\d+)\s*x\s*(\d+)$")
HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")


def _parse_spec(spec: str, defs: dict, line: int, col: int, out: list[Finding]) -> Style:
    st = Style()
    attrs: list[str] = []
    if not spec.strip():
        out.append(Finding(line, col, "ERROR", "empty style tag {}", "use {/} to close or give a token/attribute"))
        return st
    for item in spec.split():
        if HEX_RE.fullmatch(item) or HEX_RE.fullmatch(item.removeprefix("on:")):
            out.append(Finding(line, col, "ERROR", f"raw hex color {item!r} not allowed", "use a token from themes/_tokens.json"))
        elif item.startswith("on:"):
            tok = item[3:]
            if tok not in defs:
                out.append(Finding(line, col, "ERROR", f"unknown token {tok!r} in {item!r}", "see themes/_tokens.json"))
            elif tok == "fg.on-accent":
                out.append(Finding(line, col, "ERROR", "'fg.on-accent' is text drawn on a fill, not a fill",
                                   "write {fg.on-accent on:status.warning} (chip text on a status/accent fill)"))
            else:   # any other token is a color; "kind" only names its usual role (chips: on:status.warning)
                st.bg = tok
        elif item in ATTRS:
            attrs.append(item)
        elif item in defs:
            if defs[item]["kind"] != "fg":
                out.append(Finding(line, col, "ERROR", f"{item!r} is a bg token; write on:{item}"))
            else:
                st.fg = item
        elif "." in item:
            out.append(Finding(line, col, "ERROR", f"unknown token {item!r}", "see themes/_tokens.json"))
        else:
            out.append(Finding(line, col, "ERROR", f"unknown attribute {item!r}", "valid: " + " ".join(ATTRS)))
    st.attrs = tuple(dict.fromkeys(attrs))
    return st


def _merge(stack: list[tuple[Style, int, int]]) -> Style:
    fg = bg = None
    attrs: list[str] = []
    for st, _, _ in stack:
        fg = st.fg or fg
        bg = st.bg or bg
        attrs += st.attrs
    return Style(fg, bg, tuple(dict.fromkeys(attrs)))


def parse_mock(text: str, path: str = "<stdin>", strict: bool = False, nerd: bool = False,
               caps: str | None = None) -> Mock:
    """Parse and lint. `caps` (a `key=v,v …` string) overrides/defines the capability profile (CLI --caps)."""
    defs = load_token_defs()
    m = Mock(path=path)
    f = m.findings
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    # ---- header
    i = 0
    seen_magic = seen_size = False
    focus_line, selected_lines = 0, []
    caps_line = 0
    roles = known_roles()
    while i < len(lines) and lines[i].startswith("#!"):
        n = i + 1
        body = lines[i][2:].strip()
        i += 1
        if not seen_magic:
            seen_magic = True
            if body != "tui-mockup 1":
                f.append(Finding(n, 1, "ERROR", f"first line must be '#! tui-mockup 1', got {body!r}"))
            continue
        if body.startswith("region"):
            mt = REGION_RE.match(body)
            if not mt:
                f.append(Finding(n, 1, "ERROR", "malformed region", "#! region <id> <role> x,y,w,h [title]"))
                continue
            rid, role, x, y, w, h, title = mt.groups()
            reg = Region(rid, role, int(x), int(y), int(w), int(h), title or "", n)
            if not re.fullmatch(r"r[0-9]+", rid):
                f.append(Finding(n, 1, "ERROR", f"region id {rid!r} must match r<N>"))
            if any(r.id == rid for r in m.regions):
                f.append(Finding(n, 1, "ERROR", f"duplicate region id {rid!r}"))
            if role not in roles:
                f.append(Finding(n, 1, "ERROR", f"unknown region role {role!r}", "valid: " + " ".join(roles)))
            m.regions.append(reg)
            continue
        words = body.split()
        if words and words[0] == "focus":
            if len(words) != 2 or not re.fullmatch(r"r[0-9]+", words[1]):
                f.append(Finding(n, 1, "ERROR", "malformed focus", "#! focus <region-id>"))
            elif m.focus:
                f.append(Finding(n, 1, "ERROR", "duplicate '#! focus' header", "one focused region per mockup"))
            else:
                m.focus = words[1]
                focus_line = n
            continue
        if words and words[0] == "selected":
            if len(words) != 3 or not re.fullmatch(r"r[0-9]+", words[1]) or not words[2].isdigit():
                f.append(Finding(n, 1, "ERROR", "malformed selected", "#! selected <region-id> <row>  (row = 0-based offset inside the region interior)"))
            else:
                m.selected.append((words[1], int(words[2])))
                selected_lines.append(n)
            continue
        key, sep, val = body.partition(":")
        key, val = key.strip(), val.strip()
        if not sep:
            f.append(Finding(n, 1, "WARN", f"header line without 'key:' ({body!r})"))
        elif key == "size":
            ms = SIZE_RE.match(val)
            if not ms or int(ms.group(1)) < 1 or int(ms.group(2)) < 1:
                f.append(Finding(n, 1, "ERROR", f"bad size {val!r}", "expected COLSxROWS, e.g. 80x24"))
            else:
                m.cols, m.rows, seen_size = int(ms.group(1)), int(ms.group(2)), True
        elif key == "caps":
            parsed, errs = parse_caps(val)
            for e in errs:
                f.append(Finding(n, 1, "ERROR", f"#! caps: {e}"))
            if caps_line:
                f.append(Finding(n, 1, "ERROR", "duplicate '#! caps:' header", "one capability profile per mockup"))
            else:
                m.caps, caps_line = parsed, n
        elif key in ("title", "state", "theme"):
            setattr(m, key, val)
        elif key == "note":
            m.notes.append(val)
        else:
            f.append(Finding(n, 1, "WARN", f"unknown header key {key!r}"))
    if caps:
        over, errs = parse_caps(caps)
        for e in errs:
            f.append(Finding(1, 1, "ERROR", f"--caps: {e}"))
        m.caps = m.caps.merged(over)
        caps_line = caps_line or 1
    if m.caps.colors in ("16", "none"):
        depth = m.caps.depth
        f.append(Finding(caps_line or 1, 1, "INFO", f"caps colors={m.caps.colors}: render and check with --depth {depth}",
                         "render_mockup.py defaults to this depth; run contrast_check.py ID --depth 16", tag="caps"))
    if m.caps and m.caps.source in ("", "code", "assumed"):
        why = {"": "says nowhere where it comes from", "code": "comes from what the current code uses",
               "assumed": "is assumed"}[m.caps.source]
        f.append(Finding(caps_line or 1, 1, "WARN", f"caps profile {why}, not from the host",
                         "ask the user to run `python3 SKILL_DIR/scripts/test_card.py` (`--curses` for a curses app) inside "
                         "the host and send a screenshot, then write source=test-card; source=docs if the host documents it",
                         tag="caps"))
    if not seen_magic:
        f.append(Finding(1, 1, "ERROR", "missing '#! tui-mockup 1' header"))
    if not seen_size:
        f.append(Finding(1, 1, "ERROR", "missing '#! size: COLSxROWS' (assuming 80x24)"))
    for r in m.regions:
        if r.w < 1 or r.h < 1 or r.x < 0 or r.y < 0 or r.x + r.w > m.cols or r.y + r.h > m.rows:
            f.append(Finding(r.line, 1, "ERROR", f"region {r.id} bbox {r.x},{r.y},{r.w},{r.h} outside size {m.cols}x{m.rows}"))

    ids = {r.id: r for r in m.regions}
    if m.focus and m.focus not in ids:
        f.append(Finding(focus_line, 1, "ERROR", f"'#! focus' names unknown region {m.focus!r}", "declare it with '#! region' first"))
    for (rid, row), n in zip(m.selected, selected_lines):
        if rid not in ids:
            f.append(Finding(n, 1, "ERROR", f"'#! selected' names unknown region {rid!r}", "declare it with '#! region' first"))
        elif row >= ids[rid].h:
            f.append(Finding(n, 1, "ERROR", f"'#! selected {rid} {row}': row outside the region (h={ids[rid].h})"))

    # ---- body
    m.body_line = i + 1
    stack: list[tuple[Style, int, int]] = []
    glyphs: dict[tuple[str, str], dict] = {}
    base = Style()
    for ri, raw in enumerate(lines[i:]):
        n = i + ri + 1
        if raw.startswith("#! "):
            f.append(Finding(n, 1, "ERROR", "header line after body started", "all '#!' lines must precede the first body row"))
        cells: list[Cell] = []
        width = 0
        overflow_at = 0
        cur = _merge(stack) if stack else base
        j = 0
        while j < len(raw):
            ch = raw[j]
            col = j + 1
            if ch == "{":
                if raw.startswith("{{", j):
                    ch = "{"
                    j += 1
                else:
                    end = raw.find("}", j)
                    if end < 0:
                        f.append(Finding(n, col, "ERROR", "unterminated tag '{'", "literal brace is '{{'"))
                        j += 1
                        continue
                    spec = raw[j + 1:end]
                    if spec == "/":
                        if not stack:
                            f.append(Finding(n, col, "ERROR", "unbalanced {/}: no open tag"))
                        else:
                            stack.pop()
                    else:
                        st = _parse_spec(spec, defs, n, col, f)
                        for a in st.attrs:
                            if a not in m.caps.attrs:
                                f.append(Finding(n, col, "ERROR",
                                                 f"attribute {a!r} not in caps attrs={','.join(m.caps.attrs) or 'none'} (cell x={width},y={ri})",
                                                 "drop it, or carry the emphasis with an allowed attribute or a glyph"))
                        stack.append((st, n, col))
                    cur = _merge(stack) if stack else base
                    j = end + 1
                    continue
            elif ch == "}":
                if raw.startswith("}}", j):
                    j += 1
                else:
                    f.append(Finding(n, col, "ERROR", "stray '}'", "literal brace is '}}'"))
                    j += 1
                    continue
            j += 1
            g = classify_glyph(ch, strict, nerd, m.caps)
            if g:
                key = (g[0], ch)
                d = glyphs.setdefault(key, {"first": (n, col), "lines": [], "msg": g[1], "hint": g[2], "count": 0})
                d["count"] += 1
                if n not in d["lines"]:
                    d["lines"].append(n)
            w = char_width(ch)
            if w == 0:
                if cells:
                    cells[-1].text += ch
                continue
            if ch == "\t":
                ch = " "
            if width + w > m.cols and not overflow_at:
                overflow_at = col
            cells.append(Cell(ch, w, cur, col))
            width += w
        if overflow_at:
            f.append(Finding(n, overflow_at, "ERROR", f"row is {width} cells wide, exceeds cols={m.cols}",
                             "trim the line or raise #! size"))
        m.grid.append(cells)
    for st, n, col in stack:
        f.append(Finding(n, col, "ERROR", "unbalanced tag: never closed with {/}"))
    if len(m.grid) > m.rows:
        f.append(Finding(i + m.rows + 1, 1, "ERROR", f"{len(m.grid)} body rows exceed rows={m.rows}",
                         "drop rows or raise #! size"))
    for (level, ch), d in sorted(glyphs.items(), key=lambda kv: (kv[1]["first"], kv[0])):
        n, col = d["first"]
        where = ",".join(map(str, d["lines"][:8])) + ("…" if len(d["lines"]) > 8 else "")
        msg = d["msg"] + (f" [{d['count']}x, lines {where}]" if d["count"] > 1 else "")
        f.append(Finding(n, col, level, msg, d["hint"]))
    check_box_integrity(m)
    for y, x, msg, hint in craft_findings(m):
        f.append(Finding(m.body_line + y, x + 1, "WARN", msg, hint, tag="craft"))
    f.sort(key=lambda x: (x.line, x.col, x.level))
    return m
