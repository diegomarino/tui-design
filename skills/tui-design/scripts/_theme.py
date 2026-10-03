"""Shared theme + color utilities for the tui-design scripts (stdlib only).

Contract (see references/color-tokens.md):
- Token definitions live in references/themes/_tokens.json.
- A theme lives in references/themes/<id>.json and contains `terminal`
  (background, foreground, cursor, selection, 16-entry `ansi` list) and
  `tokens` (token -> palette name or "#rrggbb"), plus optional `ansi16`
  per-token overrides. Missing tier-2 tokens resolve through `fallback`.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
THEMES_DIR = SKILL_ROOT / "references" / "themes"
TOKENS_FILE = THEMES_DIR / "_tokens.json"

HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
ANSI_NAMES = [
    "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white",
    "bright_black", "bright_red", "bright_green", "bright_yellow",
    "bright_blue", "bright_magenta", "bright_cyan", "bright_white",
]
ATTRS = ("bold", "dim", "italic", "underline", "inverse", "strike")
SGR_ATTR = {"bold": 1, "dim": 2, "italic": 3, "underline": 4, "inverse": 7, "strike": 9}

# xterm defaults for indexes 0-15 when no theme is given.
XTERM16 = [
    "#000000", "#cd0000", "#00cd00", "#cdcd00", "#0000ee", "#cd00cd", "#00cdcd", "#e5e5e5",
    "#7f7f7f", "#ff0000", "#00ff00", "#ffff00", "#5c5cff", "#ff00ff", "#00ffff", "#ffffff",
]


# ---------------------------------------------------------------- hex / rgb

def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def palette256(ansi16: list[str] | None = None) -> list[str]:
    """xterm 256-color palette; 0-15 from the theme (or xterm defaults)."""
    pal = list(ansi16 or XTERM16)
    levels = [0, 95, 135, 175, 215, 255]
    for r in levels:
        for g in levels:
            for b in levels:
                pal.append(rgb_to_hex((r, g, b)))
    for i in range(24):
        v = 8 + 10 * i
        pal.append(rgb_to_hex((v, v, v)))
    return pal


# ---------------------------------------------------------------- OKLab

def _srgb_to_lin(c: float) -> float:
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def oklab(h: str) -> tuple[float, float, float]:
    r, g, b = (_srgb_to_lin(c) for c in hex_to_rgb(h))
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (math.copysign(abs(x) ** (1 / 3), x) for x in (l, m, s))
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def oklab_distance(a: str, b: str) -> float:
    return math.dist(oklab(a), oklab(b))


_CUBE_LAB: list[tuple[int, tuple[float, float, float]]] | None = None


def nearest256(h: str) -> int:
    """Nearest xterm index in 16..255 by OKLab distance (0-15 are theme-defined, never used)."""
    global _CUBE_LAB
    if _CUBE_LAB is None:
        pal = palette256()
        _CUBE_LAB = [(i, oklab(pal[i])) for i in range(16, 256)]
    t = oklab(h)
    return min(_CUBE_LAB, key=lambda item: math.dist(t, item[1]))[0]


# ---------------------------------------------------------------- contrast

def relative_luminance(h: str) -> float:
    r, g, b = (_srgb_to_lin(c) for c in hex_to_rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: str, bg: str) -> float:
    a, b = relative_luminance(fg), relative_luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def blend(fg: str, bg: str, alpha: float) -> str:
    """Alpha-composite fg over bg (used to model dim text: alpha ~0.55)."""
    f, b = hex_to_rgb(fg), hex_to_rgb(bg)
    return rgb_to_hex(tuple(round(alpha * x + (1 - alpha) * y) for x, y in zip(f, b)))


# ---------------------------------------------------------------- tokens

def load_token_defs(path: Path = TOKENS_FILE) -> dict[str, dict]:
    return json.loads(Path(path).read_text())["tokens"]


def parse_ansi16(spec: str) -> tuple[str | int, tuple[str, ...]]:
    """'4 bold' -> (4, ('bold',)); 'default dim' -> ('default', ('dim',)); 'reverse' -> ('reverse', ()).

    'bg' (fg tokens only) = "terminal background as text": the cell is drawn as the fill's slot with
    SGR 7, so text takes the terminal's default background. Used for chips in 16-color mode.
    """
    parts = spec.split()
    head, attrs = parts[0], tuple(parts[1:])
    for a in attrs:
        if a not in ATTRS:
            raise ValueError(f"unknown attribute {a!r} in ansi16 spec {spec!r}")
    if head in ("default", "reverse", "bg"):
        return head, attrs
    if head in ANSI_NAMES:
        return ANSI_NAMES.index(head), attrs
    idx = int(head)
    if not 0 <= idx <= 15:
        raise ValueError(f"ansi16 color index out of range in {spec!r}")
    return idx, attrs


@dataclass
class Theme:
    id: str
    name: str
    appearance: str
    background: str
    foreground: str
    cursor: str | None
    selection_background: str | None
    ansi: list[str]
    palette: dict[str, str]
    tokens: dict[str, str] = field(default_factory=dict)          # token -> resolved hex
    ansi16: dict[str, tuple] = field(default_factory=dict)        # token -> (color, attrs)
    raw: dict = field(default_factory=dict)

    def hex(self, token: str) -> str:
        try:
            return self.tokens[token]
        except KeyError:
            raise KeyError(f"unknown token {token!r} (see references/themes/_tokens.json)") from None


def _resolve_value(value: str, palette: dict[str, str], where: str) -> str:
    if HEX_RE.match(value):
        return value.lower()
    if value in palette:
        return palette[value].lower()
    raise ValueError(f"{where}: {value!r} is neither #rrggbb nor a palette name")


def find_theme_file(name_or_path: str) -> Path:
    p = Path(name_or_path)
    if p.suffix == ".json" and p.exists():
        return p
    cand = THEMES_DIR / f"{name_or_path}.json"
    if cand.exists():
        return cand
    available = ", ".join(list_themes())
    raise FileNotFoundError(f"theme {name_or_path!r} not found. Available: {available}")


def list_themes() -> list[str]:
    return sorted(p.stem for p in THEMES_DIR.glob("*.json") if not p.name.startswith("_"))


def load_theme(name_or_path: str, token_defs: dict[str, dict] | None = None) -> Theme:
    path = find_theme_file(name_or_path)
    data = json.loads(path.read_text())
    defs = token_defs or load_token_defs()
    term = data["terminal"]
    palette = {k: v for k, v in data.get("palette", {}).items() if isinstance(v, str) and HEX_RE.match(v)}
    ansi = [c.lower() for c in term["ansi"]]
    if len(ansi) != 16:
        raise ValueError(f"{path}: terminal.ansi must have 16 entries")

    raw_tokens: dict[str, str] = data.get("tokens", {})
    unknown = set(raw_tokens) - set(defs)
    if unknown:
        raise ValueError(f"{path}: unknown tokens {sorted(unknown)}")

    resolved: dict[str, str] = {}

    def resolve(tok: str, seen: tuple = ()) -> str:
        if tok in resolved:
            return resolved[tok]
        if tok in seen:
            raise ValueError(f"{path}: fallback cycle {' -> '.join(seen + (tok,))}")
        if tok in raw_tokens:
            val = _resolve_value(raw_tokens[tok], palette, f"{path}: tokens.{tok}")
        else:
            fb = defs[tok].get("fallback")
            if not fb:
                raise ValueError(f"{path}: tier-1 token {tok!r} is missing")
            val = resolve(fb, seen + (tok,))
        resolved[tok] = val
        return val

    for tok in defs:
        resolve(tok)

    overrides = data.get("ansi16", {})
    ansi16 = {tok: parse_ansi16(overrides.get(tok, d["ansi16"])) for tok, d in defs.items()}

    return Theme(
        id=data.get("id", path.stem),
        name=data.get("name", path.stem),
        appearance=data.get("appearance", "dark"),
        background=term["background"].lower(),
        foreground=term["foreground"].lower(),
        cursor=(term.get("cursor") or None),
        selection_background=(term.get("selection_background") or None),
        ansi=ansi,
        palette=palette,
        tokens=resolved,
        ansi16=ansi16,
        raw=data,
    )


# ---------------------------------------------------------------- SGR

def sgr(theme: Theme, fg: str | None, bg: str | None, attrs: tuple[str, ...] = (), depth: str = "truecolor") -> str:
    """Escape sequence for a cell style given token names. depth: truecolor | 256 | 16 | nocolor | none."""
    if depth == "none":
        return ""
    if depth == "nocolor":
        # NO_COLOR emulation: keep attributes, drop every color; selection-style `reverse`
        # specs (16-color mode) survive as inverse so the cursor row stays visible.
        keep = list(attrs)
        for tok in (fg, bg):
            if tok and theme.ansi16[tok][0] == "reverse":
                keep.append("inverse")
            if tok:
                keep += [a for a in theme.ansi16[tok][1] if a in ("bold", "underline", "inverse", "italic", "strike")]
        return "\x1b[" + ";".join(["0"] + [str(SGR_ATTR[a]) for a in dict.fromkeys(keep)]) + "m"
    codes: list[str] = ["0"]
    extra_attrs: list[str] = list(attrs)
    reverse = False
    if depth == "16":
        if fg and theme.ansi16[fg][0] == "bg":
            # Text in the terminal background color on the fill: paint the fill as fg and reverse.
            extra_attrs += theme.ansi16[fg][1]
            fill = theme.ansi16[bg][0] if bg else "default"
            if isinstance(fill, int):
                codes.append(str(30 + fill if fill < 8 else 90 + fill - 8))
            reverse = True
            fg = bg = None
        if fg:
            color, a = theme.ansi16[fg]
            extra_attrs += a
            if color == "reverse":
                reverse = True
            elif color != "default":
                codes.append(str(30 + color if color < 8 else 90 + color - 8))
        if bg:
            color, a = theme.ansi16[bg]
            if color == "reverse":
                reverse = True
            elif color != "default":
                codes.append(str(40 + color if color < 8 else 100 + color - 8))
    else:
        for tok, base in ((fg, 38), (bg, 48)):
            if not tok:
                continue
            h = theme.hex(tok)
            if depth == "256":
                codes.append(f"{base};5;{nearest256(h)}")
            else:
                r, g, b = hex_to_rgb(h)
                codes.append(f"{base};2;{r};{g};{b}")
    if reverse:
        extra_attrs.append("inverse")
    for a in dict.fromkeys(extra_attrs):
        codes.append(str(SGR_ATTR[a]))
    return "\x1b[" + ";".join(codes) + "m"


RESET = "\x1b[0m"
