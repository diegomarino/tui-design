"""Test fixture: render an ANSI frame to a PNG with exact, known cell geometry (ground truth).

Used by test_screenshot.py to calibrate prep_screenshot.py and sample_colors.py. Stand-alone on
purpose (does not need ansi_render.py): Pillow + numpy + the shared _theme.py only.
Needs a monospace font; macOS system fonts are tried in order, else the test is skipped.
"""
from __future__ import annotations

import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "tui-design" / "scripts"))
import _theme  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

FONTS = {
    "menlo": ("/System/Library/Fonts/Menlo.ttc", [0, 1, 2, 3]),      # regular, bold, italic, bold italic
    "monaco": ("/System/Library/Fonts/Monaco.ttf", None),
    "andale": ("/System/Library/Supplemental/Andale Mono.ttf", None),
    "courier": ("/System/Library/Supplemental/Courier New.ttf", None),
}
TOKEN = re.compile(r"\x1b\[([0-9;:]*)m|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|(.)", re.S)


def cwidth(ch: str) -> int:
    if unicodedata.combining(ch):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


@dataclass
class Cell:
    ch: str = " "
    fg: str = "#000000"       # resolved colors (after inverse/dim)
    bg: str = "#000000"
    attrs: tuple = ()


@dataclass
class Frame:
    cols: int
    rows: int
    cells: list = field(default_factory=list)   # rows x cols of Cell


def parse_ansi(text: str, cols: int, rows: int, theme: _theme.Theme) -> Frame:
    pal = _theme.palette256(theme.ansi)
    st = {"fg": None, "bg": None, "attrs": set()}

    def color(c, default):
        if c is None:
            return default
        return pal[c] if isinstance(c, int) else c

    def apply(params: str):
        parts = (params or "0").replace(":", ";").split(";")
        i = 0
        while i < len(parts):
            n = int(parts[i] or 0)
            if n == 0:
                st.update(fg=None, bg=None, attrs=set())
            elif n in (1, 2, 3, 4, 7, 9):
                st["attrs"].add({1: "bold", 2: "dim", 3: "italic", 4: "underline", 7: "inverse", 9: "strike"}[n])
            elif n == 22:
                st["attrs"] -= {"bold", "dim"}
            elif n == 23:
                st["attrs"].discard("italic")
            elif n == 24:
                st["attrs"].discard("underline")
            elif n == 27:
                st["attrs"].discard("inverse")
            elif n == 29:
                st["attrs"].discard("strike")
            elif 30 <= n <= 37:
                st["fg"] = n - 30
            elif 90 <= n <= 97:
                st["fg"] = n - 90 + 8
            elif 40 <= n <= 47:
                st["bg"] = n - 40
            elif 100 <= n <= 107:
                st["bg"] = n - 100 + 8
            elif n == 39:
                st["fg"] = None
            elif n == 49:
                st["bg"] = None
            elif n in (38, 48):
                key = "fg" if n == 38 else "bg"
                if parts[i + 1] == "5":
                    st[key] = int(parts[i + 2]); i += 2
                elif parts[i + 1] == "2":
                    st[key] = "#%02x%02x%02x" % tuple(int(x) for x in parts[i + 2:i + 5]); i += 4
            i += 1

    frame = Frame(cols, rows)
    lines = text.split("\n")
    for y in range(rows):
        row = []
        for m in TOKEN.finditer(lines[y] if y < len(lines) else ""):
            if m.group(1) is not None:
                apply(m.group(1)); continue
            ch = m.group(2)
            if ch is None:
                continue
            w = cwidth(ch)
            if w == 0:
                continue
            fg = color(st["fg"], theme.foreground)
            bg = color(st["bg"], theme.background)
            attrs = tuple(sorted(st["attrs"]))
            if "inverse" in attrs:
                fg, bg = bg, fg
            if "dim" in attrs:
                fg = _theme.blend(fg, bg, 0.55)
            row.append(Cell(ch, fg, bg, attrs))
            if w == 2:
                row.append(Cell("", fg, bg, attrs))
        while len(row) < cols:
            row.append(Cell(" ", theme.foreground, theme.background, ()))
        frame.cells.append(row[:cols])
    return frame


def load_font(name: str, size: int):
    path, idx = FONTS[name]
    if not Path(path).exists():
        return None
    if idx:
        return [ImageFont.truetype(path, size, index=i) for i in idx]
    f = ImageFont.truetype(path, size)
    return [f, f, f, f]


def render(frame: Frame, theme: _theme.Theme, font: str = "menlo", size: int = 28, pad: int = 20,
           chrome: bool = False):
    """-> (PIL image, truth dict). Truth geometry is exact at scale 1."""
    fonts = load_font(font, size)
    if fonts is None:
        raise RuntimeError(f"font {font} missing")
    asc, desc = fonts[0].getmetrics()
    cw, ch = int(round(fonts[0].getlength("M"))), asc + desc
    top = 64 if chrome else 0                    # title bar height
    margin = 40 if chrome else 0                 # outer desktop margin
    W, H = frame.cols * cw + 2 * pad + 2 * margin, frame.rows * ch + 2 * pad + top + 2 * margin
    img = Image.new("RGB", (W, H), _theme.hex_to_rgb(theme.background))
    d = ImageDraw.Draw(img)
    if chrome:
        d.rectangle([0, 0, W, H], fill=(236, 236, 240))
        wx0, wy0, wx1, wy1 = margin, margin, W - margin, H - margin
        d.rectangle([wx0, wy0, wx1 - 1, wy0 + top - 1], fill=(48, 49, 66))
        for i, c in enumerate(((255, 95, 87), (254, 188, 46), (40, 200, 64))):
            cx, cy = wx0 + 28 + i * 36, wy0 + top // 2
            d.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=c)
        d.rectangle([wx0, wy0 + top, wx1 - 1, wy1 - 1], fill=_theme.hex_to_rgb(theme.background))
    ox, oy = margin + pad, margin + top + pad
    for y, row in enumerate(frame.cells):
        for x, c in enumerate(row):
            px, py = ox + x * cw, oy + y * ch
            d.rectangle([px, py, px + cw - 1, py + ch - 1], fill=_theme.hex_to_rgb(c.bg))
            if c.ch and c.ch != " ":
                fi = (1 if "bold" in c.attrs else 0) + (2 if "italic" in c.attrs else 0)
                if 0x2500 <= ord(c.ch[0]) <= 0x259F:
                    fi = 0
                d.text((px, py), c.ch, font=fonts[fi], fill=_theme.hex_to_rgb(c.fg))
            if "underline" in c.attrs:
                d.line([px, py + asc + 3, px + cw - 1, py + asc + 3], fill=_theme.hex_to_rgb(c.fg), width=2)
    truth = {"cell_px": [cw, ch], "origin_px": [ox, oy], "cols": frame.cols, "rows": frame.rows,
             "font": font, "chrome": chrome, "size": [W, H]}
    return img, truth


def scale_image(img: Image.Image, truth: dict, s: float):
    if s == 1.0:
        return img, truth
    out = img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)
    t = dict(truth)
    t["cell_px"] = [truth["cell_px"][0] * s, truth["cell_px"][1] * s]
    t["origin_px"] = [truth["origin_px"][0] * s, truth["origin_px"][1] * s]
    t["size"] = list(out.size)
    t["scale"] = s
    return out, t
