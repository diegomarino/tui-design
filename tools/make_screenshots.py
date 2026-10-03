#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow>=10.1"]
# ///
"""Regenerate every image in docs/img/ with the skill's own tools. Deterministic on one machine.

    uv run tools/make_screenshots.py            # all images
    uv run tools/make_screenshots.py --only palette,gallery
    uv run tools/make_screenshots.py --list

Needs: rsvg-convert (librsvg) for PNG renders; pngquant (optional) to shrink the PNGs; Pillow (declared above for
`uv run`, nothing is installed globally). The page screenshots (gallery, compare) need a Playwright that is already
installed with a browser (tools/_browser.py looks for one); without it they are skipped with a message and the
existing images are kept. Run from anywhere; paths are computed from this file.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "tui-design"
SCRIPTS = SKILL / "scripts"
SHOWCASE = ROOT / "docs" / "showcase" / "deploy-console"
OUT = ROOT / "docs" / "img"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _browser  # noqa: E402

BG = (22, 22, 26)          # composite background: neutral dark, reads on light and dark READMEs
INK = (230, 230, 236)
MUTED = (150, 150, 160)
GALLERY_THEMES = "catppuccin-mocha,tokyonight-night,gruvbox-dark,rose-pine-dawn"


def py(script: str, *args) -> None:
    subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def frame_png(mock: Path, out: Path, *, theme: str | None = None, depth: str | None = None, title: str | None = None,
              scale: int = 2) -> Path:
    """`.mock` -> ANSI (render_mockup.py) -> PNG (ansi_render.py), the pipeline the skill uses to look at frames."""
    ansi = out.with_suffix(".ansi")
    args = [mock, "-o", ansi] + (["--theme", theme] if theme else []) + (["--depth", depth] if depth else [])
    py("render_mockup.py", *args)
    py("ansi_render.py", ansi, "--format", "png", "--scale", scale, "--title", title or mock.stem,
       "--theme", theme or "catppuccin-mocha", "-o", out)
    ansi.unlink()
    return out


def font(size: int):
    return ImageFont.load_default(size=size)


def labelled(img: Image.Image, label: str, width: int, sub: str = "") -> Image.Image:
    """Scale `img` to `width` and put a caption under it."""
    img = img.convert("RGBA")                       # window chrome has transparent rounded corners
    h = round(img.height * width / img.width)
    img = img.resize((width, h), Image.LANCZOS)
    cap = 34 if sub else 26
    tile = Image.new("RGB", (width, h + cap), BG)
    tile.paste(img, (0, 0), img)
    d = ImageDraw.Draw(tile)
    d.text((4, h + 6), label, fill=INK, font=font(15))
    if sub:
        d.text((4 + d.textlength(label, font=font(15)) + 10, h + 8), sub, fill=MUTED, font=font(13))
    return tile


def grid(tiles: list[Image.Image], cols: int, gap: int = 18, pad: int = 18) -> Image.Image:
    rows = (len(tiles) + cols - 1) // cols
    tw = max(t.width for t in tiles)
    th = max(t.height for t in tiles)
    sheet = Image.new("RGB", (pad * 2 + cols * tw + (cols - 1) * gap, pad * 2 + rows * th + (rows - 1) * gap), BG)
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols)
        sheet.paste(t, (pad + c * (tw + gap), pad + r * (th + gap)))
    return sheet


def save(img: Image.Image, name: str) -> Path:
    out = OUT / name
    img.save(out, optimize=True)
    return out


# ---- images ----------------------------------------------------------------------------------------------------

def hero(tmp: Path) -> list[Path]:
    """Concept C of the worked example at 120x30, 256 colors (its caps depth)."""
    out = OUT / "hero.png"
    frame_png(SHOWCASE / "approvals--normal--120x30.mock", out, depth="256", title="deploy console · approvals")
    return [out]


def concepts(tmp: Path) -> list[Path]:
    """The three concepts of the worked example at 80x24, side by side."""
    names = [("feed", "A. Feed"), ("board", "B. Board"), ("approvals", "C. Approvals (chosen)")]
    tiles = []
    for stem, label in names:
        p = frame_png(SHOWCASE / f"{stem}--normal--80x24.mock", tmp / f"{stem}.png", depth="256", title=stem)
        tiles.append(labelled(Image.open(p), label, 760, "80x24 · 256 colors"))
    return [save(grid(tiles, 3), "concepts.png")]


def depth(tmp: Path) -> list[Path]:
    """One frame at 256 colors and at 16 colors: what survives the terminal's own palette."""
    mock = SHOWCASE / "approvals--normal--80x24.mock"
    tiles = [labelled(Image.open(frame_png(mock, tmp / f"d{d}.png", depth=d, title=f"approvals · {d} colors")),
                      f"--depth {d}", 900) for d in ("256", "16")]
    return [save(grid(tiles, 2), "depth-256-vs-16.png")]


def fleet(tmp: Path) -> list[Path]:
    """The Fleet demo, the screen every proto-starter renders."""
    out = OUT / "fleet-demo.png"
    frame_png(SKILL / "assets" / "demo" / "fleet--normal--80x24.mock", out, title="fleet · normal · 80x24")
    return [out]


def palette(tmp: Path) -> list[Path]:
    """The Fleet demo in every theme: 25 variants of 10 schemes."""
    sys.path.insert(0, str(SCRIPTS))
    from _theme import list_themes
    mock = SKILL / "assets" / "demo" / "fleet--normal--80x24.mock"
    tiles = []
    for t in list_themes():
        p = frame_png(mock, tmp / f"{t}.png", theme=t, title=t, scale=1)
        tiles.append(labelled(Image.open(p), t, 460))
    return [save(grid(tiles, 5, gap=14), "themes.png")]


def test_card(tmp: Path) -> list[Path]:
    """The two test-card references the skill ships: raw escapes and through curses."""
    card = SKILL / "assets" / "test-card"
    tiles = [labelled(Image.open(card / "raw--reference.png"), "test_card.py", 900, "raw escapes (Ink, Bubble Tea, Ratatui, Textual)"),
             labelled(Image.open(card / "curses--reference.png"), "test_card.py --curses", 900, "through curses")]
    return [save(grid(tiles, 2), "test-card.png")]


def perturbed_fleet(tmp: Path) -> tuple[Path, Path]:
    """The Fleet demo, and a copy that drifts the way a build does: a text, a color and a background change."""
    src = SKILL / "assets" / "demo" / "fleet--normal--80x24.mock"
    text = src.read_text(encoding="utf-8")
    for a, b in [("{status.error}failed    {/}", "{status.error}error     {/}"),          # text
                 ("{status.warning}degraded  {/}", "{fg.muted}degraded  {/}"),          # foreground
                 ("{accent.primary bold on:statusbar.bg} Fleet {/}", "{accent.primary bold} Fleet {/}")]:  # background
        assert a in text, a
        text = text.replace(a, b)
    design = tmp / "design" / "fleet--normal--80x24.mock"
    build = tmp / "build" / "fleet--normal--80x24.mock"
    design.parent.mkdir(exist_ok=True)
    build.parent.mkdir(exist_ok=True)
    design.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    build.write_text(text, encoding="utf-8")
    return design, build


def pages(tmp: Path) -> list[Path]:
    """Page screenshots: the gallery (single and side by side) and a compare page."""
    pw = _browser.find()
    if pw is None:
        print("  skipped: no Playwright with a browser found (tools/_browser.py); keeping the existing page images")
        return []
    print(f"  browser: {pw.describe()}")
    gal = tmp / "gallery.html"
    py("gallery.py", SHOWCASE, SKILL / "assets" / "mockups", "--themes", GALLERY_THEMES,
       "--title", "tui-design gallery: deploy console and reference mockups", "-o", gal)
    design, build = perturbed_fleet(tmp)
    cmp = tmp / "compare.html"
    py("compare.py", design, build, "--labels", "design,build", "-o", cmp)
    jobs = [
        {"url": gal.as_uri(), "out": str(OUT / "gallery.png"), "width": 1360, "height": 1045, "dark": True,
         "select": [["#sel-v", "approvals"], ["#sel-z", "120x30"]]},
        {"url": gal.as_uri(), "out": str(OUT / "gallery-side-by-side.png"), "width": 1600, "height": 840, "dark": True,
         "select": [["#sel-v", "approvals"], ["#sel-z", "80x24"]], "keys": ["s"]},
        {"url": cmp.as_uri(), "out": str(OUT / "compare.png"), "width": 1360, "height": 850, "dark": False,
         "full_page": False},
    ]
    _browser.screenshots(pw, jobs)
    return [Path(j["out"]) for j in jobs]


STEPS = {"hero": hero, "concepts": concepts, "depth": depth, "fleet": fleet, "palette": palette,
         "test-card": test_card, "pages": pages}


def quantize(paths: list[Path]) -> None:
    if not shutil.which("pngquant"):
        print("pngquant not found: PNGs left unquantized")
        return
    for p in paths:
        subprocess.run(["pngquant", "--force", "--skip-if-larger", "--quality", "80-100", "--speed", "1",
                        "--strip", "--output", str(p), str(p)], check=False)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", help="comma-separated steps: " + ",".join(STEPS))
    ap.add_argument("--list", action="store_true", help="list the steps and exit")
    a = ap.parse_args()
    if a.list:
        for k, f in STEPS.items():
            print(f"{k:10} {f.__doc__}")
        return 0
    if not shutil.which("rsvg-convert"):
        sys.path.insert(0, str(SCRIPTS))
        import ansi_render
        print(f"rsvg-convert not found: {ansi_render.rsvg_install_hint()}", file=sys.stderr)
        return 2
    steps = [s.strip() for s in a.only.split(",")] if a.only else list(STEPS)
    OUT.mkdir(parents=True, exist_ok=True)
    made: list[Path] = []
    with tempfile.TemporaryDirectory() as t:
        for s in steps:
            print(f"{s}:")
            out = STEPS[s](Path(t))
            for p in out:
                print(f"  {p.relative_to(ROOT)}")
            made += out
    quantize(made)
    return 0


if __name__ == "__main__":
    sys.exit(main())
