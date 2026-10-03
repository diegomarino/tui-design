#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow>=10.1", "numpy>=1.26"]
# ///
"""sample_colors.py - per-cell colors from screenshot pixels, never from vision.

For every cell of the grid (grid.json from prep_screenshot.py):
  bg   = modal pixel color of the cell (exact at 1.0/0.5/0.37x in the calibration fixtures)
  ink  = fraction of pixels that differ from bg
  fg   = antialias UNMIXING: among candidate colors, the one whose bg->candidate segment best explains the
         ink pixels (token accuracy 98.4% at 0.37x scale, vs 62.8% for nearest-palette-to-extreme-pixel)
Candidates come from a theme's resolved tokens + terminal ANSI slots (+ terminal fg/bg, named palette).
Colors that share an RGB are merged into one candidate with a list of token names.
--themes all tries every theme in references/themes/ and reports the best fit (lowest residual).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import numpy as np
    from PIL import Image
    import _theme
except ImportError as e:  # pragma: no cover
    print(f"missing dependency ({e.name}); run with: uv run sample_colors.py ...", file=sys.stderr)
    sys.exit(2)

EPILOG = """\
examples:
  uv run sample_colors.py shot.png --grid out/grid.json --theme catppuccin-mocha -o cells.json
  uv run sample_colors.py shot.png --grid out/grid.json --themes all -o cells.json   # also guesses the theme
  uv run sample_colors.py shot.png --grid out/grid.json --no-tokens                   # raw colors only

Output cells.json: {"meta", "theme_guess", "cells": [{x, y, bg:{raw,tokens,dist}, fg:{raw,tokens,confidence,residual,alternatives?}|null, ink}]}
ink = fraction (0..1) of the cell's inner pixels (12% inset per edge) that differ from the cell bg. Ink-consistency
rule of thumb (measured at 1.0/0.5/0.37x on Menlo/Monaco fixtures): ink > 0.05 means a glyph is present; space
cells stay <= 0.03 (p99.5), glyph cells are >= 0.074 (p1). Expect ~0.5% of spaces above and ~1% of glyphs
(. , ' `) below that line: report mismatch *runs*, not single cells.
fg is null for cells without ink. tokens = every token/ANSI slot/palette name with that exact RGB (sorted:
tokens, ansi.N, terminal.*, palette.*). Known limits: dim text lands on the nearest un-dimmed color on the same
hue line; full-block glyphs (U+2580-259F) look like a background; below ~10 px per cell width, collinear
candidates (the neutral ladder fg.default / fg.muted / fg.faint) cannot be separated: the pick is the terminal
default fg and the rest are listed in fg.alternatives with low confidence (measured top-1 51% on a muted-heavy
UI at 0.5x, 96-99% when the truth is among top-6). Cells of 10+ px resolve them from pixels that reach full color.
Exit: 0 ok, 2 usage/environment error.
"""
INK_L1 = 30            # |pixel - bg| L1 above which a pixel counts as ink for fg estimation
MIN_INK_PX = 4
BG_TOKEN_TOL = 12      # max L1 distance for a bg to be named by a token
FG_RES_MAX = 45.0      # RMS residual above which no candidate is accepted for fg


def hexc(c) -> str:
    return "#%02x%02x%02x" % tuple(int(round(float(x))) for x in c)


def candidates(theme: "_theme.Theme") -> dict[str, list[str]]:
    """hex -> names. Order: canonical tokens, ansi.N, terminal.*, palette.*"""
    groups: dict[str, dict[str, list[str]]] = {}

    def add(h: str, kind: str, name: str):
        groups.setdefault(h.lower(), {"tok": [], "ansi": [], "term": [], "pal": []})[kind].append(name)

    for t, h in theme.tokens.items():
        add(h, "tok", t)
    for i, h in enumerate(theme.ansi):
        add(h, "ansi", f"ansi.{i}")
    add(theme.foreground, "term", "terminal.foreground")
    add(theme.background, "term", "terminal.background")
    for k in ("cursor", "selection_background"):
        v = getattr(theme, k)
        if v and v.startswith("#"):
            add(v, "term", f"terminal.{k}")
    for n, h in theme.palette.items():
        add(h, "pal", f"palette.{n}")
    return {h: sorted(g["tok"]) + sorted(g["ansi"], key=lambda s: int(s.split(".")[1])) + sorted(g["term"])
            + sorted(g["pal"]) for h, g in groups.items()}


class CellData:
    __slots__ = ("x", "y", "bg", "ink", "pix", "px", "inner")


def _ink_of(c: CellData):
    px = c.px if c.inner is None else c.inner
    d = np.abs(px - c.bg).sum(1)
    m = d > INK_L1
    c.ink = float(m.mean()) if len(m) else 0.0
    c.pix = px[m].astype(np.float64)


def collect(img: np.ndarray, grid: dict) -> list[CellData]:
    cw, ch = grid["cell_px"]
    ox, oy = grid["origin_px"]
    H, W, _ = img.shape
    out = []
    for y in range(grid["rows"]):
        ya, yb = int(round(oy + y * ch)), int(round(oy + (y + 1) * ch))
        for x in range(grid["cols"]):
            xa, xb = int(round(ox + x * cw)), int(round(ox + (x + 1) * cw))
            xa, xb, ya_, yb_ = max(0, xa), min(W, max(xb, xa + 1)), max(0, ya), min(H, max(yb, ya + 1))
            c = CellData()
            c.x, c.y = x, y
            if xb <= xa or yb_ <= ya_:
                c.px, c.inner, c.bg, c.ink, c.pix = np.zeros((0, 3), dtype=np.int64), None, np.zeros(3), 0.0, np.zeros((0, 3))
                out.append(c)
                continue
            blk = img[ya_:yb_, xa:xb].astype(np.int64)
            px = blk.reshape(-1, 3)
            ix, iy = int(round(INSET * (xb - xa))), int(round(INSET * (yb_ - ya_)))
            inner = blk[iy:blk.shape[0] - iy, ix:blk.shape[1] - ix] if (blk.shape[0] > 2 * iy + 1 and blk.shape[1] > 2 * ix + 1) else blk
            c.inner = inner.reshape(-1, 3)
            packed = (px[:, 0] << 16) | (px[:, 1] << 8) | px[:, 2]
            vals, counts = np.unique(packed, return_counts=True)
            v = int(vals[counts.argmax()])
            c.px = px
            c.bg = np.array([(v >> 16) & 255, (v >> 8) & 255, v & 255], dtype=np.float64)
            _ink_of(c)
            out.append(c)
    # Resampling ringing: a thin bright stroke can leave no exact-bg pixel in a small cell, so the mode is a
    # halo color. Snap such cells to a bg color that occurs cleanly (low ink) in >= 2 cells elsewhere.
    clean = {}
    for c in out:
        if c.ink < 0.15 and len(c.px):
            k = tuple(int(v) for v in c.bg)
            clean[k] = clean.get(k, 0) + 1
    glob = np.array([k for k, n in clean.items() if n >= 2], dtype=np.float64)
    if len(glob):
        for c in out:
            if c.ink >= 0.2 and len(c.px):
                d = np.abs(glob - c.bg).sum(1)
                i = int(d.argmin())
                if 0 < d[i] <= 40:
                    c.bg = glob[i]
                    _ink_of(c)
    return out


PURE_OK = True         # set from the grid: False when cells are narrower than PURE_MIN_CELL_W px
PURE_MIN_CELL_W = 10.0
INSET = 0.12            # fraction of the cell ignored at each edge when measuring ink / fg (neighbor bleed)
TIE = "default"        # fg tie-break among near-equal candidates: "none" | "extreme" | "default"


def unmix(cell: CellData, cand_rgb: np.ndarray, default_idx: int | None = None):
    """-> (best_idx, rms_residual, second_rms, near_tie_indexes) or None."""
    ink, bg = cell.pix, cell.bg
    if len(ink) < MIN_INK_PX:
        return None
    V = cand_rgb - bg                                      # (K,3)
    vv = (V * V).sum(1)
    ok = vv > 400                                          # candidate must differ from bg
    if not ok.any():
        return None
    D = ink - bg                                           # (n,3)
    DV = D @ V.T
    t = DV / np.where(ok, vv, 1.0)                         # (n,K)
    tc = np.clip(t, 0, 1)
    dd = (D * D).sum(1)[:, None]
    res = (dd - tc * (2 * DV - tc * vv)).mean(0)           # mean |D - tc V|^2
    pen = 2000.0 * np.maximum(0.0, t.max(0) - 1.08)        # pixel more extreme than the candidate
    score = np.where(ok, res + pen, np.inf)
    order = np.argsort(score)
    best = int(order[0])
    sb = max(float(score[best]), 0.0)
    ties = [int(k) for k in order if np.isfinite(score[k]) and score[k] <= sb * 1.15 + 4.0]
    info = None
    if len(ties) > 1 and TIE != "none":
        hi = np.percentile(t, 95, axis=0)
        # pixels reaching a candidate's color is only evidence when strokes are not diluted by downscaling
        pure = [k for k in ties if 0.85 <= hi[k] <= 1.08] if PURE_OK else []
        if pure:
            best = min(pure, key=lambda k: abs(hi[k] - 1.0))
        else:                                       # diluted strokes: decided later by describe_cells
            ref = max(ties, key=lambda k: vv[k])    # most extreme collinear candidate (TIE="extreme")
            info = {"ties": ties, "ref": ref}
            if TIE == "default" and default_idx in ties:
                best = default_idx
            else:
                best = ref
    others = [k for k in order if k != best and np.isfinite(score[k])]
    second = float(score[others[0]]) if others else float("inf")
    return (best, float(np.sqrt(max(score[best], 0.0))),
            float(np.sqrt(max(second, 0.0))) if np.isfinite(second) else float("inf"),
            [k for k in ties if k != best], info)


def fit_theme(cells: list[CellData], theme, sample_stride: int = 1):
    cand = candidates(theme)
    hexes = sorted(cand)
    rgb = np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in hexes], dtype=np.float64)
    tot, n = 0.0, 0
    for c in cells[::sample_stride]:
        r = unmix(c, rgb, None)
        if r is not None:
            tot += min(r[1], 60.0)
            n += 1
    bgd = np.array([np.sqrt(((rgb - c.bg) ** 2).sum(1)).min() for c in cells[::max(1, sample_stride)]])
    bg_match = float((bgd <= 6).mean()) if len(bgd) else 0.0
    resid = tot / n if n else 60.0
    return {"id": theme.id, "residual": round(resid, 2), "bg_match": round(bg_match, 3),
            "score": round(resid + 40.0 * (1 - bg_match), 2), "cells_fitted": n}, cand, hexes, rgb


def describe_cells(cells, cand, hexes, rgb, with_tokens=True, default_hex=None):
    default_idx = hexes.index(default_hex) if default_hex in hexes else None
    raw = []                                        # first pass: unmix every inked cell
    for c in cells:
        r = unmix(c, rgb, default_idx) if (len(c.pix) >= MIN_INK_PX and len(rgb)) else None
        raw.append(r)
    # Diluted strokes (small cells) never reach their fg color, so collinear candidates (the neutral
    # ladder fg.default / fg.muted / fg.faint) cannot be told apart per cell. Calibrate the coverage
    # ceiling kappa from the whole image (90th percentile of how far strokes reach along the line, in
    # units of the most extreme candidate) and pick the candidate whose magnitude matches u / kappa.
    # Diluted strokes (small cells) never reach their fg color, so collinear candidates (the neutral ladder
    # fg.default / fg.muted / fg.faint) cannot be told apart per cell. Prior: the terminal's default fg;
    # the other candidates are reported as `alternatives` and confidence drops. (A coverage-ceiling
    # calibration from colored cells is noisier than this prior.)
    out = []
    for c, r in zip(cells, raw):
        bgh = hexc(c.bg)
        d = float(np.abs(rgb - c.bg).sum(1).min()) if len(rgb) else 999.0
        bg_t = []
        if with_tokens and len(rgb) and d <= BG_TOKEN_TOL:
            bg_t = cand[hexes[int(np.abs(rgb - c.bg).sum(1).argmin())]]
        rec = {"x": c.x, "y": c.y, "bg": {"raw": bgh, "tokens": bg_t, "dist": round(d, 1)},
               "ink": round(c.ink, 3)}
        fg = None
        if len(c.pix) >= MIN_INK_PX:
            if r is not None and r[1] <= FG_RES_MAX:
                best, res, second, ties, _info = r
                conf = 0.0 if second == float("inf") else max(0.0, min(1.0, 1.0 - res / max(second, 1e-6)))
                conf *= min(1.0, len(c.pix) / 12.0)
                fg = {"raw": hexes[best], "tokens": cand[hexes[best]] if with_tokens else [],
                      "confidence": round(conf, 2), "residual": round(res, 1)}
                if ties:    # collinear candidates the pixels cannot separate (AA-diluted strokes)
                    fg["alternatives"] = [hexes[k] for k in sorted(ties, key=lambda k: abs(rgb[k] - rgb[best]).sum())[:5]]
            else:   # no candidate explains the ink: report the most bg-distant pixel, unnamed
                dist = np.abs(c.pix - c.bg).sum(1)
                fg = {"raw": hexc(c.pix[int(dist.argmax())]), "tokens": [], "confidence": 0.0,
                      "residual": None if r is None else round(r[1], 1)}
        rec["fg"] = fg
        out.append(rec)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], epilog=EPILOG,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--grid", required=True, help="grid.json from prep_screenshot.py")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--theme", help="theme id or path (references/themes/<id>.json)")
    g.add_argument("--themes", choices=["all"], help="try every theme and report the best fit (default)")
    g.add_argument("--no-tokens", action="store_true", help="raw colors only (no theme)")
    ap.add_argument("-o", "--out", help="output cells.json (default: stdout)")
    args = ap.parse_args(argv)

    try:
        grid = json.loads(Path(args.grid).read_text())
        img = np.asarray(Image.open(args.image).convert("RGB"))
    except (OSError, ValueError) as e:
        print(f"cannot read input: {e}", file=sys.stderr)
        return 2
    global PURE_OK
    PURE_OK = grid["cell_px"][0] >= PURE_MIN_CELL_W
    cells = collect(img, grid)

    guess, cand, hexes, rgb = None, {}, [], np.zeros((0, 3))
    if args.no_tokens:
        guess = {"id": None, "method": "none"}
    else:
        ids = [args.theme] if args.theme else _theme.list_themes()
        if not ids:
            print("no themes found", file=sys.stderr)
            return 2
        try:
            themes = [_theme.load_theme(i) for i in ids]
        except (FileNotFoundError, ValueError, KeyError) as e:
            print(f"theme error: {e}", file=sys.stderr)
            return 2
        stride = max(1, len(cells) // 900) if len(themes) > 1 else 1
        fits = [fit_theme(cells, t, stride) for t in themes]
        best = min(range(len(themes)), key=lambda i: fits[i][0]["score"])
        stats, cand, hexes, rgb = fits[best]
        guess = dict(stats, method="given" if args.theme else "lowest-unmixing-residual",
                     ranked=sorted((f[0] for f in fits), key=lambda s: s["score"]))
        if len(fits) == 1:
            guess["ranked"] = [stats]
    rec = describe_cells(cells, cand, hexes, rgb, with_tokens=not args.no_tokens,
                         default_hex=(themes[best].foreground if not args.no_tokens else None))
    meta = {"image": str(args.image), "grid": {k: grid[k] for k in ("cell_px", "origin_px", "cols", "rows")},
            "ink_threshold_l1": INK_L1, "fg_residual_max_rms": FG_RES_MAX}
    text = ('{"meta":' + json.dumps(meta) + ',\n"theme_guess":' + json.dumps(guess) + ',\n"cells":[\n'
            + ",\n".join(json.dumps(r, separators=(",", ":")) for r in rec) + "\n]}\n")
    if args.out:
        Path(args.out).write_text(text)
        if guess.get("id"):
            print(f"theme {guess['id']} residual {guess['residual']} bg_match {guess['bg_match']} "
                  f"-> {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
