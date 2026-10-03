#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""ansi_render.py - render one ANSI frame as a themed terminal-window SVG / PNG / HTML.

Parser: stdlib (_ansi.py, shared with ansi_grid.py). Theme: references/themes/<id>.json
(ANSI 0-15, default fg/bg, cursor); indexes 16-255 are the xterm cube/greys; truecolor passes through.
Layout is cell-exact: every narrow glyph gets its own x, wide (CJK/emoji) glyphs are centred
over 2 cells, backgrounds are rects drawn first, so the grid never drifts with font metrics.

Examples:
  python3 scripts/ansi_render.py frame.ansi --theme catppuccin-mocha --title myapp -o frame.svg
  uv run scripts/ansi_render.py frame.ansi --cols 120 --format png --scale 2 -o frame.png
  uv run scripts/ansi_render.py frame.ansi --format png --quantize --geometry frame.geo.json -o frame.png
  tmux -L NAME capture-pane -t PANE -p -e | python3 scripts/ansi_render.py - --no-chrome --format html -o frame.html

Input must be ONE frame (capture-pane / capture_tui.sh / render_mockup.py output). Cursor movement and
erase sequences are NOT emulated (skipped); a raw pty log of an interactive app is not a frame.

Attribute fidelity: bold=font-weight 700; dim=fill-opacity .55; italic=font-style; reverse swaps painted
fg/bg (default colours come from the theme); hidden=not drawn; blink=drawn static; underline / strike /
overline are drawn as lines (underline colour from SGR 58 if set); double underline = two lines; CURLY
underline is approximated by a small zigzag line; dotted/dashed (4:4, 4:5) render as a plain underline.
Colour emoji are NOT supported by rsvg (monochrome silhouette or tofu); cursor is only drawn with --cursor.
PNG needs the `rsvg-convert` binary. The package depends on the OS (macOS: `brew install librsvg`;
Debian/Ubuntu: `apt install librsvg2-bin`; Fedora/RHEL: `dnf install librsvg2-tools`; Arch: `pacman -S librsvg`;
Alpine: `apk add rsvg-convert`). The missing-binary error names the command for this machine. --quantize needs
`pngquant`. Fonts: JetBrains Mono NL,
falling back to Menlo, monospace (the grid stays exact either way).

Exit: 0 ok, 2 usage/environment error (missing file, theme, binary).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ansi import Resolver, parse_ansi  # noqa: E402
from _theme import load_theme  # noqa: E402

FONT = "'JetBrains Mono NL',Menlo,monospace"
CHROME_FONT = "'SF Pro Text',Helvetica,sans-serif"
DIM_OPACITY = 0.55


class Layout:
    def __init__(self, size: float, chrome: bool):
        self.size = size
        self.cw = size * 0.6
        self.lh = round(size * 1.3)
        self.base = round(size * 0.93)
        self.px, self.pt, self.pb = 14, 8, 12
        self.tb = 34 if chrome else 0       # title-bar height

    def x(self, col: float) -> float:
        return self.px + col * self.cw

    def top(self, row: int) -> float:
        return self.tb + self.pt + row * self.lh


def runs(row, keyfn):
    """Merge horizontally adjacent cells with an equal non-None key -> (start_col, end_col_excl, key, cells)."""
    out, col, cur = [], 0, None
    for c in row:
        if not c.w:
            continue
        k = keyfn(c)
        if cur and k is not None and k == cur[2] and cur[1] == col:
            cur[1] = col + c.w
            cur[3].append((col, c))
        else:
            cur = [col, col + c.w, k, [(col, c)]] if k is not None else None
            if cur:
                out.append(cur)
        col += c.w
    return out


def n(v: float) -> str:
    return f"{v:.1f}".rstrip("0").rstrip(".")


# Block elements drawn as exact rectangles (x, y, w, h as fractions of the cell): fonts leave seams between
# adjacent glyphs (visible in browsers), rectangles tile perfectly. Shades (░▒▓) stay glyphs.
BLOCKS = {"█": (0, 0, 1, 1), "▀": (0, 0, 1, .5), "▄": (0, .5, 1, .5), "▌": (0, 0, .5, 1), "▐": (.5, 0, .5, 1),
          "▔": (0, 0, 1, 1 / 8), "▕": (7 / 8, 0, 1 / 8, 1)}
BLOCKS.update({ch: (0, 1 - k / 8, 1, k / 8) for k, ch in enumerate("▁▂▃▄▅▆▇", 1)})
BLOCKS.update({ch: (0, 0, k / 8, 1) for k, ch in enumerate("▏▎▍▌▋▊▉", 1)})


def render_svg(grid, theme, *, title="", chrome=True, size=14.0, font=FONT, cursor=None):
    """Return (svg_text, geometry_dict at scale 1)."""
    res, L = Resolver(theme), Layout(size, chrome)
    painted = {}                                   # Style -> (fg, bg)

    def paint(c):
        s = c.style
        if s not in painted:
            painted[s] = res.painted(s)
        return painted[s]

    W = round(L.px * 2 + grid.cols * L.cw)
    H = L.tb + L.pt + grid.rows * L.lh + L.pb
    chrome_fg = theme.hex("border.default")
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<rect width="{W}" height="{H}" rx="{10 if chrome else 0}" fill="{res.bg}"/>']
    if chrome:
        o += [f'<circle cx="{cx}" cy="17" r="6" fill="{chrome_fg}"/>' for cx in (22, 42, 62)]
        if title:
            o.append(f'<text x="{n(W / 2)}" y="21" fill="{chrome_fg}" font-family="{CHROME_FONT}" font-size="12" '
                     f'text-anchor="middle">{escape(title, quote=False)}</text>')
    o.append(f'<g font-family="{font}" font-size="{n(size)}" xml:space="preserve">')

    lw = max(1, round(size / 14))
    for y, row in enumerate(grid.cells):
        top = L.top(y)
        # 1. backgrounds (merged runs)
        for a, b, bg, _ in runs(row, lambda c: paint(c)[1]):
            o.append(f'<rect x="{n(L.x(a))}" y="{n(top)}" width="{n((b - a) * L.cw)}" height="{L.lh}" fill="{bg}"/>')
        # 2. text: narrow glyphs per-glyph x in runs of contiguous columns; wide / multi-codepoint glyphs alone
        def bkey(c):
            if c.w != 1 or c.ch not in BLOCKS or "hidden" in c.style.attrs:
                return None
            return (c.ch, paint(c)[0], "dim" in c.style.attrs)

        for a, b, (ch, fg, dim), _ in runs(row, bkey):       # merged per glyph kind: no seams between cells
            fx, fy, fw, fh = BLOCKS[ch]
            op = ' fill-opacity="0.55"' if dim else ""
            if (fx, fw) == (0, 1):
                o.append(f'<rect x="{n(L.x(a))}" y="{n(top + fy * L.lh)}" width="{n((b - a) * L.cw)}" '
                         f'height="{n(fh * L.lh)}" fill="{fg}"{op}/>')
            else:
                for col in range(a, b):
                    o.append(f'<rect x="{n(L.x(col) + fx * L.cw)}" y="{n(top + fy * L.lh)}" width="{n(fw * L.cw)}" '
                             f'height="{n(fh * L.lh)}" fill="{fg}"{op}/>')

        def tkey(c):
            s = c.style
            if c.w != 1 or len(c.ch) != 1 or "hidden" in s.attrs or c.ch == " " or c.ch in BLOCKS:
                return None                                  # spaces end a run: browsers collapse them in SVG text
            return (paint(c)[0], "bold" in s.attrs, "italic" in s.attrs, "dim" in s.attrs)

        for a, b, key, cells in runs(row, tkey):
            if cells:
                xs = " ".join(n(L.x(col)) for col, _ in cells)
                o.append(f'<text x="{xs}" y="{n(top + L.base)}"{_tattrs(key)}>'
                         f'{escape("".join(c.ch for _, c in cells), quote=False)}</text>')
        col = 0
        for c in row:
            if c.w and (c.w == 2 or len(c.ch) > 1) and c.ch.strip() and "hidden" not in c.style.attrs:
                fg, s = paint(c)[0], c.style.attrs
                key = (fg, "bold" in s, "italic" in s, "dim" in s)
                cx = L.x(col) + c.w * L.cw / 2
                o.append(f'<text x="{n(cx)}" y="{n(top + L.base)}" text-anchor="middle"{_tattrs(key)}>'
                         f'{escape(c.ch, quote=False)}</text>')
            col += c.w
        # 3. line decorations
        def dkey(kind):
            def f(c):
                if kind not in c.style.attrs:
                    return None
                return (res.hex(c.style.ul) or paint(c)[0], "dim" in c.style.attrs)
            return f

        for kind in ("underline", "double_underline", "curly_underline", "strike", "overline"):
            for a, b, (color, dim), _ in runs(row, dkey(kind)):
                o.append(_deco(kind, L.x(a), L.x(b), top, L, color, dim, lw))
    if cursor:
        cx, cy = cursor
        if 0 <= cx < grid.cols and 0 <= cy < grid.rows:
            o.append(f'<rect x="{n(L.x(cx))}" y="{n(L.top(cy))}" width="{n(L.cw)}" height="{L.lh}" '
                     f'fill="{res.cursor}" fill-opacity="0.6"/>')
    o.append("</g></svg>")
    geo = {"cols": grid.cols, "rows": grid.rows, "cell_px": [L.cw, L.lh], "origin_px": [L.px, L.tb + L.pt],
           "width_px": W, "height_px": H, "scale": 1, "font_size": size, "theme": theme.id, "chrome": chrome}
    return "\n".join(o) + "\n", geo


def _tattrs(key) -> str:
    fg, bold, italic, dim = key
    a = f' fill="{fg}"'
    if bold:
        a += ' font-weight="700"'
    if italic:
        a += ' font-style="italic"'
    if dim:
        a += f' fill-opacity="{DIM_OPACITY}"'
    return a


def _deco(kind, x0, x1, top, L, color, dim, lw) -> str:
    op = f' stroke-opacity="{DIM_OPACITY}"' if dim else ""
    st = f'stroke="{color}" stroke-width="{lw}"{op} fill="none"'
    uy = top + L.base + 2
    if kind == "underline":
        return f'<line x1="{n(x0)}" y1="{n(uy)}" x2="{n(x1)}" y2="{n(uy)}" {st}/>'
    if kind == "double_underline":
        return (f'<path d="M{n(x0)} {n(uy - 1.5)}H{n(x1)}M{n(x0)} {n(uy + 1)}H{n(x1)}" {st}/>')
    if kind == "strike":
        y = top + L.base - L.size * 0.3
        return f'<line x1="{n(x0)}" y1="{n(y)}" x2="{n(x1)}" y2="{n(y)}" {st}/>'
    if kind == "overline":
        return f'<line x1="{n(x0)}" y1="{n(top + 1)}" x2="{n(x1)}" y2="{n(top + 1)}" {st}/>'
    pts, x, up = [], x0, True                       # curly: zigzag, half a cell per segment
    step = L.cw / 2
    while x < x1 - 0.01:
        pts.append(f"{n(x)},{n(uy + (0.5 if up else 2.5))}")
        x, up = x + step, not up
    pts.append(f"{n(x1)},{n(uy + (0.5 if up else 2.5))}")
    return f'<polyline points="{" ".join(pts)}" {st}/>'


# ---------------------------------------------------------------- output formats

def to_html(svg: str, theme, title: str) -> str:
    return (f'<!doctype html>\n<html><head><meta charset="utf-8"><title>{escape(title or "ANSI frame")}</title>'
            f'<style>html,body{{margin:0;background:{theme.background}}}body{{padding:16px}}'
            f'svg{{display:block;max-width:100%;height:auto;margin:0 auto}}</style></head>\n<body>\n{svg}</body></html>\n')


def need(binary: str, hint: str) -> str:
    path = shutil.which(binary)
    if not path:
        sys.exit(f"{binary} not found: {hint}")
    return path


def _os_release_ids(text: str) -> set[str]:
    ids: set[str] = set()
    for line in text.splitlines():
        if line.startswith(("ID=", "ID_LIKE=")):
            value = line.split("=", 1)[1].strip().strip("\"'")
            ids.update(part.lower() for part in value.replace(",", " ").split())
    return ids


# The binary is always rsvg-convert. These are the packages that provide it.
_RSVG_PACKAGES = (
    (frozenset({"debian", "ubuntu", "linuxmint", "pop", "raspbian", "kali"}), "apt install librsvg2-bin"),
    (frozenset({"fedora", "rhel", "centos", "rocky", "almalinux"}), "dnf install librsvg2-tools"),
    (frozenset({"arch", "manjaro", "endeavouros"}), "pacman -S librsvg"),
    (frozenset({"alpine"}), "apk add rsvg-convert"),
)
_RSVG_ANY = (
    "macOS: brew install librsvg; Debian/Ubuntu: apt install librsvg2-bin; "
    "Fedora/RHEL: dnf install librsvg2-tools; Arch: pacman -S librsvg; Alpine: apk add rsvg-convert"
)


def rsvg_install_hint(platform: str | None = None, release_text: str | None = None) -> str:
    """Install command for the rsvg-convert binary on this OS. The binary name does not change."""
    platform = sys.platform if platform is None else platform
    if platform == "darwin":
        return "brew install librsvg"
    if platform.startswith("linux"):
        if release_text is None:
            try:
                release_text = Path("/etc/os-release").read_text(encoding="utf-8")
            except OSError:
                release_text = ""
        ids = _os_release_ids(release_text)
        for keys, cmd in _RSVG_PACKAGES:
            if ids & keys:
                return cmd
    return _RSVG_ANY


def to_png(svg: str, scale: float, quantize: bool) -> bytes:
    rsvg = need("rsvg-convert", rsvg_install_hint())
    fc = shutil.which("fc-match")
    if fc:
        fam = subprocess.run([fc, "JetBrains Mono NL", "-f", "%{family}"], capture_output=True, text=True).stdout
        if "JetBrains" not in fam:
            print("warning: font 'JetBrains Mono NL' not installed; PNG falls back to Menlo/monospace "
                  "(grid stays cell-exact, glyph shapes differ)", file=sys.stderr)
    r = subprocess.run([rsvg, "-z", str(scale), "-f", "png"], input=svg.encode(), capture_output=True)
    if r.returncode:
        sys.exit(f"rsvg-convert failed: {r.stderr.decode(errors='replace').strip()}")
    png = r.stdout
    if quantize:
        pq = need("pngquant", "brew install pngquant")
        q = subprocess.run([pq, "--quality", "90-100", "--speed", "1", "-"], input=png, capture_output=True)
        if q.returncode == 0:
            png = q.stdout
        else:
            print("warning: pngquant could not reach quality 90-100; keeping unquantized PNG", file=sys.stderr)
    return png


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Render one ANSI frame as a themed terminal-window SVG/PNG/HTML.",
                                 epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="ANSI file, or - for stdin")
    ap.add_argument("--theme", default="catppuccin-mocha", help="theme id or path (default catppuccin-mocha)")
    ap.add_argument("--cols", type=int, help="force grid width (pad/crop); default = longest line")
    ap.add_argument("--rows", type=int, help="force grid height (pad/crop); default = line count")
    ap.add_argument("--title", help="window title in the chrome (default: input file stem)")
    ap.add_argument("--no-chrome", action="store_true", help="no title bar / dots (tight image)")
    ap.add_argument("--format", choices=("svg", "png", "html"), help="default: from -o extension, else svg")
    ap.add_argument("--scale", type=float, default=2, help="PNG zoom factor (default 2)")
    ap.add_argument("--quantize", action="store_true", help="PNG: pngquant --quality 90-100")
    ap.add_argument("--size", type=float, default=14, help="font size in px (default 14; cell = 0.6em x 1.3em)")
    ap.add_argument("--font", default=FONT, help=f"SVG font-family (default {FONT})")
    ap.add_argument("--cursor", metavar="COL,ROW", help="draw a cursor block at this 0-based cell")
    ap.add_argument("--geometry", metavar="OUT.json", help="write cell geometry sidecar (cell_px, origin_px, cols, rows)")
    ap.add_argument("-o", "--out", help="output file (default stdout)")
    a = ap.parse_args(argv)

    try:
        theme = load_theme(a.theme)
        text = sys.stdin.read() if a.input == "-" else Path(a.input).read_text(encoding="utf-8", errors="replace")
    except (OSError, FileNotFoundError, ValueError, KeyError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    fmt = a.format or (Path(a.out).suffix.lstrip(".").lower() if a.out else "svg")
    if fmt not in ("svg", "png", "html"):
        print(f"error: unknown format {fmt!r} (svg|png|html)", file=sys.stderr)
        return 2
    cursor = tuple(int(v) for v in a.cursor.split(",")) if a.cursor else None
    title = a.title if a.title is not None else (Path(a.input).stem if a.input != "-" else "")

    grid = parse_ansi(text, a.cols, a.rows)
    svg, geo = render_svg(grid, theme, title=title, chrome=not a.no_chrome, size=a.size, font=a.font, cursor=cursor)
    try:
        if fmt == "png":
            data = to_png(svg, a.scale, a.quantize)
            geo.update(scale=a.scale, cell_px=[geo["cell_px"][0] * a.scale, geo["cell_px"][1] * a.scale],
                       origin_px=[v * a.scale for v in geo["origin_px"]],
                       width_px=round(geo["width_px"] * a.scale), height_px=round(geo["height_px"] * a.scale))
        else:
            data = (to_html(svg, theme, title) if fmt == "html" else svg).encode()
    except SystemExit as e:
        print(f"error: {e.code}", file=sys.stderr)
        return 2
    if a.out:
        Path(a.out).write_bytes(data)
    else:
        sys.stdout.buffer.write(data)
    if a.geometry:
        Path(a.geometry).write_text(json.dumps(geo, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
