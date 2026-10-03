#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow>=10.1", "numpy>=1.26"]
# ///
"""Calibration tests for prep_screenshot.py and sample_colors.py against ground-truth fixtures.

Fixtures (tests/fixtures/*.ansi) are rendered to PNG here with exactly known cell geometry
(tests/_fixture.py, Menlo/Monaco; skipped when the font is missing) and, when ansi_render.py works,
also with the skill's own renderer (fleet demo, with window chrome). Each image is re-run at scale
1.0 / 0.5 / 0.37 (Lanczos downscale) and the detected grid and sampled colors are scored against truth.

Run:  uv run scripts/tests/test_screenshot.py        exit 0 = all thresholds met, 1 = a check failed
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "skills" / "tui-design" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import _fixture as F  # noqa: E402
import _theme  # noqa: E402
import prep_screenshot as P  # noqa: E402
import sample_colors as SC  # noqa: E402

FRAMES = {"lazygit": ("lazygit-120x30.ansi", 120, 30), "monitor": ("release-monitor-120x31.ansi", 120, 31)}
SCALES = (1.0, 0.5, 0.37)
FAILS: list[str] = []
INK_STATS: list[tuple] = []
ROWS: list[str] = []


def check(ok: bool, msg: str):
    if not ok:
        FAILS.append(msg)
        print("FAIL", msg)


def block_glyph(ch: str) -> bool:        # U+2580-259F: indistinguishable from a bg (documented limit)
    return bool(ch) and 0x2580 <= ord(ch[0]) <= 0x259F


def detect(a: np.ndarray, cols, rows):
    ns = types.SimpleNamespace(origin=None, crop_off=(0, 0), cols=cols, rows=rows, anchor_line=None)
    return P.detect_grid(a, ns, [])


def score_colors(a: np.ndarray, grid: dict, truth_cell, theme):
    """truth_cell(x, y) -> (ch, fg_hex, bg_hex, dim) ; returns dict of accuracies."""
    cells = SC.collect(a, grid)
    SC.PURE_OK = grid["cell_px"][0] >= SC.PURE_MIN_CELL_W
    fit, cand, hexes, rgb = SC.fit_theme(cells, theme)
    recs = SC.describe_cells(cells, cand, hexes, rgb, default_hex=theme.foreground)
    bg_ok = bg_n = fg_ok = fg_n = top3 = 0
    sp_ink, gl_ink = [], []
    for r in recs:
        ch, fg, bg, dim = truth_cell(r["x"], r["y"])
        if block_glyph(ch):
            continue
        if ch == " ":
            sp_ink.append(r["ink"])
        elif ch and ch.strip() and ch not in "·.,'`":
            gl_ink.append(r["ink"])
        bg_n += 1
        bg_ok += r["bg"]["raw"] == bg
        if ch.strip() and r["fg"] and fg != bg and r["ink"] >= 0.03 and not dim and fg in cand:
            fg_n += 1
            ok = r["fg"]["raw"] == fg
            fg_ok += ok
            top3 += ok or fg in r["fg"].get("alternatives", [])
    INK_STATS.append((np.percentile(sp_ink, 99.5), max(sp_ink), np.percentile(gl_ink, 1), min(gl_ink)))
    return {"bg": bg_ok / bg_n, "fg": fg_ok / max(1, fg_n), "fg_top4": top3 / max(1, fg_n), "fg_n": fg_n,
            "residual": fit["residual"]}


def grid_check(tag, grid, truth, cols, rows, known):
    tw, th = truth["cell_px"]
    cw, ch = grid["cell_px"]
    ex, ey = abs(cw - tw) / tw, abs(ch - th) / th
    oxe, oye = abs(grid["origin_px"][0] - truth["origin_px"][0]) / tw, abs(grid["origin_px"][1] - truth["origin_px"][1]) / th
    check(ex < 0.01 and ey < 0.01, f"{tag}: cell pitch off ({cw:.3f},{ch:.3f}) vs ({tw:.3f},{th:.3f})")
    if known:
        check((grid["cols"], grid["rows"]) == (cols, rows), f"{tag}: grid {grid['cols']}x{grid['rows']} != {cols}x{rows}")
        check(oxe < 0.3 and oye < 0.3, f"{tag}: origin off by ({oxe:.2f},{oye:.2f}) cells")
    else:   # blank edge cells make the ink-derived count a lower bound; origin may sit whole cells in
        check(cols - 3 <= grid["cols"] <= cols and rows - 2 <= grid["rows"] <= rows,
              f"{tag}: ink-derived grid {grid['cols']}x{grid['rows']} not within a few cells of {cols}x{rows}")
    return ex, ey, oxe, oye


def test_self_rendered(theme):
    for font in ("menlo", "monaco"):
        if F.load_font(font, 28) is None:
            print(f"skip font {font}")
            continue
        for name, (fn, cols, rows) in FRAMES.items():
            fr = F.parse_ansi((HERE / "fixtures" / fn).read_text(), cols, rows, theme)
            img0, t0 = F.render(fr, theme, font=font)
            for s in SCALES:
                img, t = F.scale_image(img0, t0, s)
                a = np.asarray(img)
                for known in (True, False):
                    g = detect(a, cols if known else None, rows if known else None)
                    e = grid_check(f"{font}/{name}@{s}/{'cols' if known else 'auto'}", g, t, cols, rows, known)
                    if known:
                        grid = dict(g)
                        acc = score_colors(a, grid, lambda x, y: (fr.cells[y][x].ch, fr.cells[y][x].fg, fr.cells[y][x].bg,
                                                                   "dim" in fr.cells[y][x].attrs), theme)
                        ROWS.append(f"| {font}/{name} | {s} | cell {g['cell_px'][0]:.2f}x{g['cell_px'][1]:.2f} (truth "
                                    f"{t['cell_px'][0]:.2f}x{t['cell_px'][1]:.2f}) | origin err {e[2]:.2f}/{e[3]:.2f} cells | "
                                    f"bg {acc['bg']*100:.1f}% | fg {acc['fg']*100:.1f}% (top-6 {acc['fg_top4']*100:.1f}%, n={acc['fg_n']}) |")
                        floor = 0.995 if s >= 1 else 0.99
                        check(acc["bg"] >= floor, f"{font}/{name}@{s}: bg accuracy {acc['bg']:.3f}")
                        check(acc["fg"] >= (0.985 if s >= 1 else 0.94), f"{font}/{name}@{s}: fg accuracy {acc['fg']:.3f}")


def test_chrome_and_ansi_render(theme):
    """Skill renderer: window chrome, same-color title bar, fractional pitch (16.8 x 36), tokens from ansi_grid."""
    src = HERE / "fixtures" / "fleet-80x24.ansi"
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        png, geom = td / "fleet.png", td / "geom.json"
        r = subprocess.run([sys.executable, str(SCRIPTS / "ansi_render.py"), str(src), "--format", "png", "--scale", "2",
                            "--geometry", str(geom), "-o", str(png)], capture_output=True, text=True)
        if r.returncode != 0 or not png.exists():
            print("skip ansi_render fixture:", (r.stderr or r.stdout).strip()[:120])
            return
        gj = subprocess.run([sys.executable, str(SCRIPTS / "ansi_grid.py"), str(src), "--cols", "80", "--rows", "24"],
                            capture_output=True, text=True)
        truth_grid = json.loads(gj.stdout)["cells"]
        geo = json.loads(geom.read_text())
        base = Image.open(png).convert("RGB")
        for s in (1.0, 0.5, 0.37):          # relative to the 2x PNG: 16.8 / 8.4 / 6.2 px cells
            img = base if s == 1.0 else base.resize((round(base.width * s), round(base.height * s)), Image.LANCZOS)
            t = {"cell_px": [geo["cell_px"][0] * s, geo["cell_px"][1] * s],
                 "origin_px": [geo["origin_px"][0] * s, geo["origin_px"][1] * s]}
            ip = td / f"fleet-{s}.png"
            img.save(ip)
            rc = P.main([str(ip), "--cols", "80", "--rows", "24", "-o", str(td / f"o{s}")])
            check(rc == 0, f"fleet@{s}: prep_screenshot exit {rc}")
            g = json.loads((td / f"o{s}" / "grid.json").read_text())
            e = grid_check(f"fleet(ansi_render,chrome)@{s}", g, t, 80, 24, True)
            a = np.asarray(img)
            truth = lambda x, y: (truth_grid[y][x]["ch"], truth_grid[y][x]["fg"]["raw"], truth_grid[y][x]["bg"]["raw"],
                                  "dim" in truth_grid[y][x]["attrs"])
            acc = score_colors(a, g, truth, theme)
            ROWS.append(f"| fleet (ansi_render, chrome) | {s} | cell {g['cell_px'][0]:.2f}x{g['cell_px'][1]:.2f} (truth "
                        f"{t['cell_px'][0]:.2f}x{t['cell_px'][1]:.2f}) | origin err {e[2]:.2f}/{e[3]:.2f} cells | "
                        f"bg {acc['bg']*100:.1f}% | fg {acc['fg']*100:.1f}% (top-6 {acc['fg_top4']*100:.1f}%, n={acc['fg_n']}) |")
            check(acc["bg"] >= 0.98, f"fleet@{s}: bg accuracy {acc['bg']:.3f}")
            # fleet is mostly neutral-ladder text (fg.default/muted/faint): collinear, so below ~10 px/cell the
            # top-1 pick is a prior (default fg) and the truth is expected among `alternatives` (top-6)
            check(acc["fg"] >= (0.99 if s >= 1 else 0.45), f"fleet@{s}: fg accuracy {acc['fg']:.3f}")
            check(acc["fg_top4"] >= (0.99 if s >= 1 else 0.80), f"fleet@{s}: fg top-6 accuracy {acc['fg_top4']:.3f}")
        # CLI end to end on the chrome image: title bar must be detected, outputs written
        out = td / "out"
        regions = td / "regions.json"
        regions.write_text(json.dumps([{"id": "list", "bbox": {"x": 0, "y": 2, "w": 32, "h": 20}}]))
        rc = P.main([str(png), "--cols", "80", "--rows", "24", "--regions", str(regions), "-o", str(out)])
        check(rc == 0, "CLI returned nonzero on the chrome image")
        gjson = json.loads((out / "grid.json").read_text())
        check(any("title bar" in n for n in gjson["notes"]), "title bar not detected on the chrome image")
        check((gjson["grid_confidence"] or 0) > 0.3, f"confidence too low: {gjson['grid_confidence']}")
        for f in ("pass1.png", "pass1-ruler.png", "region-list.png", "region-list-ruler.png", "grid.json"):
            check((out / f).exists(), f"missing output {f}")
        # ruler is margin-only: the image area inside the ruler equals the plain image exactly
        plain, ruler = Image.open(out / "pass1.png").convert("RGB"), Image.open(out / "pass1-ruler.png").convert("RGB")
        mx, my = (ruler.width - plain.width) // 2, (ruler.height - plain.height) // 2
        check(np.array_equal(np.asarray(ruler.crop((mx, my, mx + plain.width, my + plain.height))), np.asarray(plain)),
              "ruler drew over the image area")
        reg = gjson["regions"][0]
        check(reg["cell_px_scaled"][0] >= 12 - 0.01, f"region crop below 12 px/cell: {reg['cell_px_scaled']}")
        check(Image.open(out / "pass1.png").format == "PNG", "pass1 is not PNG")
        # anchor-line: derive the pitch from one verbatim row
        row = "".join(c["ch"] for c in truth_grid[3]).rstrip()
        for sc in (1.0, 0.37):
            ip = td / f"fleet-{sc}.png"
            for k, (spec, tag) in enumerate(((f"3:{row.strip()}", "full row"), ("22:deployed api-gateway v2.4.1", "substring"))):
                rc = P.main([str(ip), "--anchor-line", spec, "-o", str(td / f"anc{sc}{k}")])
                g2 = json.loads((td / f"anc{sc}{k}" / "grid.json").read_text())
                want = geo["cell_px"][0] * sc
                check(abs(g2["cell_px"][0] - want) / want < 0.01,
                      f"anchor ({tag}) @{sc}: pitch {g2['cell_px'][0]:.3f} vs {want:.3f}")
                check((g2["cols"], g2["rows"]) == (80, 24), f"anchor ({tag}) @{sc}: grid {g2['cols']}x{g2['rows']}")
        # describer pass-1 JSON with nested children: crops per leaf region only
        p1 = td / "pass1.json"
        p1.write_text(json.dumps({"regions": [{"id": "r1", "bbox": {"x": 0, "y": 0, "w": 80, "h": 24}, "children": [
            {"id": "r2", "bbox": {"x": 0, "y": 2, "w": 32, "h": 20}},
            {"id": "r3", "bbox": {"x": 33, "y": 2, "w": 47, "h": 20}, "children": [{"id": "r4", "bbox": {"x": 34, "y": 4, "w": 20, "h": 5}}]}]}]}))
        P.main([str(png), "--cols", "80", "--rows", "24", "--regions", str(p1), "-o", str(td / "leaf")])
        ids = sorted(r["id"] for r in json.loads((td / "leaf" / "grid.json").read_text())["regions"])
        check(ids == ["r2", "r4"], f"leaf regions wrong: {ids}")
        check((td / "leaf" / "region-r4-ruler.png").exists(), "leaf crop missing")


def test_tiling_and_errors(theme):
    fr = F.parse_ansi((HERE / "fixtures" / "lazygit-120x30.ansi").read_text(), 120, 30, theme)
    wide = F.Frame(240, 30, [row + row for row in fr.cells])           # 240 columns: cannot fit 8 px/cell in 1568
    img, t = F.render(wide, theme, font="menlo" if F.load_font("menlo", 28) else "monaco")
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        png = td / "wide.png"
        img.save(png)
        rc = P.main([str(png), "--cols", "240", "--rows", "30", "-o", str(td / "o")])
        g = json.loads((td / "o" / "grid.json").read_text())
        check(rc == 0 and g["pass1"]["tiled"] and len(g["pass1"]["tiles"]) == 2, "wide screen was not tiled into 2 halves")
        t0, t1 = g["pass1"]["tiles"]
        check(t0["cols"][1] - t1["cols"][0] == 2, f"tile overlap != 2 cells: {t0['cols']} {t1['cols']}")
        for tile in g["pass1"]["tiles"]:
            check(max(tile["size_px"]) <= 1568, f"tile exceeds the long-edge budget: {tile['size_px']}")
            check(g["pass1"]["cell_px_scaled"][0] >= 8 - 0.01, "tile below 8 px/cell")
        blank = td / "blank.png"
        Image.new("RGB", (300, 200), (10, 10, 10)).save(blank)
        check(P.main([str(blank), "-o", str(td / "b")]) == 1, "blank image should exit 1")
        check(P.main([str(td / "nope.png"), "-o", str(td / "c")]) == 2, "missing image should exit 2")


def test_octaves_crops_and_advice(theme):
    """Row/column octave lock, --anchor-line recovery, crops.json / pass1 facts / advice."""
    # 1. pick_row_pitch: ink-mass 16 px vs gradient 7.85 px (k9s screenshot: the gradient's 2nd harmonic won and halved the grid).
    #    The column profile has period 8: only the longer pitch has an aspect window containing it.
    cols = np.tile(np.array([1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0]), 140)
    notes: list[str] = []
    p, _, resolved = P.pick_row_pitch(np.zeros(10), cols, 15.99, 2.3, 7.854, 3.3, notes)
    check(abs(p - 15.99) < 1e-6 and resolved and notes, f"octave pick: kept {p} (notes {notes})")
    p, _, resolved = P.pick_row_pitch(np.zeros(10), cols, 15.99, 5.0, 16.1, 4.0, [])
    check(not resolved and abs(p - 15.99) < 1e-6, "agreeing profiles must not trigger the octave path")
    # 2. an anchor line read off a wrong (half-pitch) grid is recovered through the octave alternatives
    src = HERE / "fixtures" / "fleet-80x24.ansi"
    font = "menlo" if F.load_font("menlo", 28) else "monaco" if F.load_font("monaco", 28) else None
    if font:
        fr = F.parse_ansi(src.read_text(), 80, 24, theme)
        img, t = F.render(fr, theme, font=font)
        a = np.asarray(img)
        real = P.pick_row_pitch
        P.pick_row_pitch = lambda *x, **k: (t["cell_px"][1] / 2, 3.0, False)      # force the half-pitch lock
        try:
            row = "".join(c.ch for c in fr.cells[3]).strip()
            ns = types.SimpleNamespace(origin=None, crop_off=(0, 0), cols=None, rows=None, anchor_line=f"6:{row}")
            notes = []
            g = P.detect_grid(a, ns, notes)
        finally:
            P.pick_row_pitch = real
        check(abs(g["cell_px"][1] - t["cell_px"][1]) / t["cell_px"][1] < 0.02 and abs(g["cell_px"][0] - t["cell_px"][0]) / t["cell_px"][0] < 0.02,
              f"anchor octave retry: cell {g['cell_px']} vs {t['cell_px']}")
        check(any("retried" in n for n in notes), f"no retry note: {notes}")
        check(g["advice"] in ("ok", "check-ruler"), f"advice {g['advice']}")
        ns = types.SimpleNamespace(origin=None, crop_off=(0, 0), cols=None, rows=None, anchor_line="900:nothing to see here")
        try:
            P.detect_grid(a, ns, [])
            check(False, "anchor row beyond the image must fail")
        except ValueError as e:
            check("octave" in str(e) and "--cols/--rows" in str(e), f"unclear anchor failure message: {e}")
        # 3. crops.json, pass-1 image facts, advice
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            png = td / "f.png"
            img.save(png)
            regs = td / "regions.json"
            regs.write_text(json.dumps([{"id": "r2", "bbox": {"x": 0, "y": 1, "w": 32, "h": 21}}]))
            check(P.main([str(png), "--cols", "80", "--rows", "24", "--regions", str(regs), "-o", str(td / "o")]) == 0, "prep failed")
            g = json.loads((td / "o" / "grid.json").read_text())
            check(g["advice"] in ("ok", "check-ruler", "give-size"), "grid.json lacks advice")
            p1 = g["pass1"]
            check({"file", "cell_px", "origin_px", "scale"} <= set(p1) and p1["file"] == "pass1.png", f"pass1 facts {p1}")
            im = Image.open(td / "o" / p1["file"])
            check(abs(p1["cell_px"][0] * 80 - im.width) <= p1["cell_px"][0] + 2, "pass1 cell_px does not match the image the describer sees")
            crops = json.loads((td / "o" / "crops.json").read_text())
            c = crops[0]
            check(isinstance(crops, list) and {"id", "file", "bbox", "scale", "cell_px", "origin_px"} <= set(c), f"crops.json entry {c}")
            check(c["id"] == "r2" and c["bbox"] == {"x": 0, "y": 0, "w": 33, "h": 23}, f"crop bbox (1-cell margin, clamped) {c['bbox']}")
            ci = Image.open(td / "o" / c["file"])
            check(abs(c["cell_px"][0] * c["bbox"]["w"] - ci.width) <= c["cell_px"][0] + 2, "crop cell_px does not match its image")
            check(c["origin_px"][0] < c["cell_px"][0] and c["origin_px"][1] < c["cell_px"][1], "crop origin outside the first cell")
    check(P.advice(0.9, False) == "ok" and P.advice(0.5, False) == "check-ruler" and P.advice(0.2, False) == "give-size"
          and P.advice(0.2, True) == "check-ruler", "advice thresholds")


def test_theme_guess(theme):
    """A different palette must fit worse than the true theme."""
    raw = json.loads(Path(_theme.find_theme_file(theme.id)).read_text())
    with tempfile.TemporaryDirectory() as td:
        alt = dict(raw, id="alt-test")
        alt["palette"] = {k: "#%02x%02x%02x" % tuple((255 - v) // 1 for v in _theme.hex_to_rgb(h)) for k, h in raw["palette"].items()}
        alt["terminal"] = dict(raw["terminal"], background="#101010", foreground="#e0e0e0",
                               ansi=["#%02x%02x%02x" % tuple(255 - v for v in _theme.hex_to_rgb(h)) for h in raw["terminal"]["ansi"]])
        alt["tokens"] = {k: ("#%02x%02x%02x" % tuple(255 - v for v in _theme.hex_to_rgb(theme.tokens[k]))) for k in raw["tokens"]}
        p = Path(td) / "alt-test.json"
        p.write_text(json.dumps(alt))
        th2 = _theme.load_theme(str(p))
        fr = F.parse_ansi((HERE / "fixtures" / "lazygit-120x30.ansi").read_text(), 120, 30, theme)
        font = "menlo" if F.load_font("menlo", 28) else "monaco"
        img, t = F.render(fr, theme, font=font)
        cells = SC.collect(np.asarray(img), dict(cell_px=t["cell_px"], origin_px=t["origin_px"], cols=120, rows=30))
        f_true = SC.fit_theme(cells, theme, 4)[0]
        f_alt = SC.fit_theme(cells, th2, 4)[0]
        ROWS.append(f"| theme guess | 1.0 | true theme score {f_true['score']} vs inverted palette {f_alt['score']} | | | |")
        check(f_true["score"] < f_alt["score"] / 3, f"theme guess not decisive: {f_true['score']} vs {f_alt['score']}")


def main() -> int:
    theme = _theme.load_theme("catppuccin-mocha")
    test_self_rendered(theme)
    test_chrome_and_ansi_render(theme)
    test_tiling_and_errors(theme)
    test_octaves_crops_and_advice(theme)
    test_theme_guess(theme)
    print("\n| fixture | scale | cell px | origin | bg acc | fg acc |\n|---|---|---|---|---|---|")
    print("\n".join(ROWS))
    sp99, spmax, gl1, glmin = (max(x[0] for x in INK_STATS), max(x[1] for x in INK_STATS),
                               min(x[2] for x in INK_STATS), min(x[3] for x in INK_STATS))
    print(f"\nink fraction (all fixtures/scales): space cells p99.5 <= {sp99:.3f} (max {spmax:.3f}); "
          f"glyph cells p1 >= {gl1:.3f} (min {glmin:.3f})")
    check(sp99 < 0.05 < gl1, f"ink threshold 0.05 does not separate spaces ({sp99:.3f}) from glyphs ({gl1:.3f})")
    print(f"\n{'FAILED: ' + str(len(FAILS)) + ' check(s)' if FAILS else 'all checks passed'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
