#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow>=10.1", "numpy>=1.26"]
# ///
"""prep_screenshot.py - Screenshot preprocessing: turn a terminal screenshot into a measured cell grid
plus model-ready images (plain, margin-ruler, per-region crops). Pixels only; nothing is sharpened,
quantized, JPEG-encoded or generatively upscaled (Lanczos resampling only).

Pipeline:
  1 normalize   RGB, strip alpha, crop window chrome when detectable (outer margin, traffic-light title bar)
  2 detect      bg = modal color; row pitch = Fourier comb over the row-gradient profile (6-80 px);
                column pitch = anchor line (--anchor-line) | exact count (--cols) | aspect-window comb (provisional);
                origin = phase of the ink-mass profile (cell edge, not ink bbox)
  3 budget      pass1 scaled to >= 8 px/cell width within the long-edge budget (1568); tiled into
                overlapping column halves (2-cell overlap) when it cannot fit
  4 outputs     grid.json, pass1[-N].png, pass1-ruler[-N].png, region-<id>.png / region-<id>-ruler.png

All pixel coordinates in grid.json refer to the ORIGINAL input image; cell coordinates are 0-based.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
except ImportError as e:  # pragma: no cover
    print(f"missing dependency ({e.name}); run with: uv run prep_screenshot.py ...", file=sys.stderr)
    sys.exit(2)

EPILOG = """\
examples:
  uv run prep_screenshot.py shot.png -o out/                       # detect grid, write pass1 + ruler
  uv run prep_screenshot.py shot.png --cols 120 --rows 30 -o out/  # known terminal size: exact counts
  uv run prep_screenshot.py shot.png --anchor-line '3:│ Services (6) ────────│' -o out/
  uv run prep_screenshot.py shot.png --cols 120 --rows 30 --regions regions.json -o out/

regions.json: a bare list [{"id": "r1", "bbox": {"x": 0, "y": 1, "w": 32, "h": 21}}, ...] (cells, 0-based) or
the describer pass-1 object {"regions": [{"id", "bbox", "children": [...]}]}; crops are cut per leaf region.
--anchor-line ROW:TEXT  ROW = 0-based row index on the grid printed in pass1-ruler.png, TEXT = a verbatim run
of that row (any part of it, >= 4 cells, spaces count). Matched as a template (ink where TEXT has glyphs,
none where it has spaces) to get the column pitch, then refined on the whole image.
Exit: 0 ok, 1 grid not detectable, 2 usage/environment error.
"""

ASPECT_LO, ASPECT_HI = 0.40, 0.68      # cell width / height of monospace fonts (derived: Menlo 0.515)
INK_THRESH = 60                         # L1 distance from bg that counts as ink for the profiles
MARGIN_FONT_PX = 11


# ----------------------------------------------------------------------------- helpers
def modal_color(a: np.ndarray) -> np.ndarray:
    packed = (a[..., 0].astype(np.int64) << 16) | (a[..., 1].astype(np.int64) << 8) | a[..., 2]
    vals, counts = np.unique(packed, return_counts=True)
    v = int(vals[counts.argmax()])
    return np.array([(v >> 16) & 255, (v >> 8) & 255, v & 255], dtype=np.int64)


def hexc(c) -> str:
    return "#%02x%02x%02x" % tuple(int(x) for x in c)


def load_rgb(path: str) -> np.ndarray:
    im = Image.open(path)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        opaque = np.asarray(im)[..., 3] > 250
        base = modal_color(np.asarray(im.convert("RGB"))[opaque]) if opaque.any() else np.array([0, 0, 0])
        bg = Image.new("RGBA", im.size, tuple(int(x) for x in base) + (255,))
        im = Image.alpha_composite(bg, im)
    return np.asarray(im.convert("RGB")).astype(np.uint8)


def display_width(s: str) -> int:
    import unicodedata
    n = 0
    for ch in s:
        if unicodedata.combining(ch):
            continue
        n += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return n


# ----------------------------------------------------------------------------- 1 normalize
def crop_chrome(a: np.ndarray, bg: np.ndarray) -> tuple[tuple[int, int, int, int], list[str]]:
    """-> (x0, y0, x1, y1) of the terminal body, notes. Conservative: only strips an outer uniform
    margin whose color differs from the terminal bg, and a macOS-style traffic-light title bar."""
    H, W, _ = a.shape
    notes: list[str] = []
    x0, y0, x1, y1 = 0, 0, W, H
    corner = a[0, 0].astype(np.int64)
    if np.abs(corner - bg).sum() > 30:
        def margin_like(line):
            return (np.abs(line.astype(np.int64) - corner).sum(1) < 40).mean() > 0.97
        lim_y, lim_x = H // 4, W // 4
        while y0 < lim_y and margin_like(a[y0, x0:x1]):
            y0 += 1
        while H - y1 < lim_y and margin_like(a[y1 - 1, x0:x1]):
            y1 -= 1
        while x0 < lim_x and margin_like(a[y0:y1, x0]):
            x0 += 1
        while W - x1 < lim_x and margin_like(a[y0:y1, x1 - 1]):
            x1 -= 1
        if (x0, y0, x1, y1) != (0, 0, W, H):
            notes.append("outer margin stripped")
    # traffic-light title bar: red, yellow, green dots in one row in the top 20% of what is left
    sub = a[y0:y0 + max(40, (y1 - y0) // 5), x0:x1].astype(np.int64)
    blobs = []
    for rgb in ((255, 95, 87), (254, 188, 46), (40, 200, 64)):
        m = np.abs(sub - np.array(rgb)).sum(2) < 60
        if m.sum() < 5:
            break
        yy, xx = np.nonzero(m)
        blobs.append((xx.mean(), yy.mean(), yy.max()))
    if len(blobs) == 3 and max(b[1] for b in blobs) - min(b[1] for b in blobs) < 4 \
            and blobs[0][0] < blobs[1][0] < blobs[2][0] \
            and abs((blobs[1][0] - blobs[0][0]) - (blobs[2][0] - blobs[1][0])) < 0.3 * (blobs[2][0] - blobs[0][0]):
        row = y0 + int(max(b[2] for b in blobs)) + 1
        while row < y1 and (np.abs(a[row, x0:x1].astype(np.int64) - bg).sum(1) < 12).mean() < 0.5:
            row += 1
        if row < y1 and row - y0 < (y1 - y0) // 4:
            y0 = row
            notes.append("title bar stripped (traffic lights)")
    # blurred/anti-aliased rim of a stripped edge must not count as ink: inset 2 px on stripped sides
    if (x0, y0, x1, y1) != (0, 0, W, H):
        x0, y0 = x0 + (2 if x0 else 0), y0 + (2 if y0 else 0)
        x1, y1 = x1 - (2 if x1 < W else 0), y1 - (2 if y1 < H else 0)
    return (x0, y0, x1, y1), notes


def mask_corners(I: np.ndarray, body: np.ndarray, bg: np.ndarray) -> np.ndarray:
    """Rounded window corners show whatever is behind the window (black, white, desktop): not terminal ink."""
    H, W = I.shape
    k = max(16, int(0.03 * min(H, W)))
    for (yy, xx, sy, sx) in ((0, 0, slice(0, k), slice(0, k)), (0, W - 1, slice(0, k), slice(W - k, W)),
                             (H - 1, 0, slice(H - k, H), slice(0, k)), (H - 1, W - 1, slice(H - k, H), slice(W - k, W))):
        if np.abs(body[yy, xx].astype(np.int64) - bg).sum() > 30:
            I[sy, sx] = False
    return I


def isolated_title_band(body: np.ndarray, grid: dict) -> int | None:
    """Title bars that share the terminal bg (modern terminals) cannot be told apart by color. Heuristic:
    the first ink block starts near the top, is thinner than one cell, and is followed by a gap of nearly a
    cell or more before the next ink. Returns the first row to keep, or None."""
    H = body.shape[0]
    bg = modal_color(body)
    I = mask_corners(ink_mask(body, bg), body, bg)
    rows = np.nonzero(I.any(1))[0]
    py = grid["cell_px"][1]
    if rows.size < 2:
        return None
    f = int(rows[0])
    gaps = np.nonzero(np.diff(rows) > 0.25 * py)[0]
    if gaps.size == 0:
        return None
    e = int(rows[gaps[0]])
    n = int(rows[gaps[0] + 1])
    if f < 0.1 * H and f < 1.5 * py and (e - f + 1) < 0.95 * py and (n - e - 1) >= 0.8 * py:
        return e + 1
    return None


def title_band_candidate(body: np.ndarray) -> int | None:
    """Pitch-free variant of isolated_title_band: the first ink block starts in the top 10%, is at most
    6% of the height, and is followed by a gap at least as tall as the block. Returns the first row to keep."""
    H = body.shape[0]
    bg = modal_color(body)
    I = mask_corners(ink_mask(body, bg), body, bg)
    rows = np.nonzero(I.any(1))[0]
    if rows.size < 2:
        return None
    gaps = np.nonzero(np.diff(rows) > 1)[0]
    if gaps.size == 0:
        return None
    f, e, n = int(rows[0]), int(rows[gaps[0]]), int(rows[gaps[0] + 1])
    if f < 0.1 * H and (e - f + 1) <= 0.06 * H and (n - e - 1) >= (e - f + 1):
        return e + 1
    return None


# ----------------------------------------------------------------------------- 2 grid detection
def ink_mask(a: np.ndarray, bg: np.ndarray) -> np.ndarray:
    return (np.abs(a.astype(np.int64) - bg).sum(2) > INK_THRESH)


def spectrum(prof: np.ndarray, periods: np.ndarray) -> np.ndarray:
    """Complex Fourier coefficients of prof at the given periods (chunked)."""
    k = np.arange(len(prof), dtype=np.float64)
    out = np.empty(len(periods), dtype=np.complex128)
    step = max(1, 4_000_000 // max(1, len(prof)))
    for i in range(0, len(periods), step):
        p = periods[i:i + step]
        out[i:i + step] = np.exp(-2j * np.pi * np.outer(1.0 / p, k)) @ prof
    return out


def refine_peak(prof: np.ndarray, p0: float, span: float, step: float) -> tuple[float, complex]:
    ps = np.arange(p0 - span, p0 + span + step / 2, step)
    z = spectrum(prof, ps)
    i = int(np.abs(z).argmax())
    return float(ps[i]), z[i]


def comb_period(prof: np.ndarray, lo: float, hi: float) -> tuple[float, complex, float]:
    """Dominant fundamental period of a periodic profile with harmonic-sum scoring.
    Returns (period, complex coefficient, prominence = peak / median magnitude)."""
    prof = prof - prof.mean()
    ps = np.arange(lo / 3.0, hi + 0.01, 0.02)
    z = np.abs(spectrum(prof, ps))

    def zat(q):
        return np.interp(q, ps, z)

    cand = ps[(ps >= lo) & (ps <= hi)]
    score = zat(cand) + 0.5 * zat(cand / 2) + 0.25 * zat(cand / 3)
    p = float(cand[int(score.argmax())])
    # octave check: the harmonic sum also credits p's subharmonic (2p gets 0.5*z(p)); when p/2 or p/3 is
    # itself at least as strong as p, the true period is the shorter one
    for d in (3, 2):
        if p / d >= lo and zat(p / d) >= zat(p):
            p = p / d
            break
    p, c = refine_peak(prof, p, 0.06, 0.002)
    med = float(np.median(z[(ps >= lo) & (ps <= hi)])) or 1e-9
    return p, c, float(abs(c)) / med


def phase_origin(prof: np.ndarray, p: float) -> float:
    """Position of the cell edge: ink mass of text is centered in a cell, so the periodic maximum of
    the ink-mass profile sits at the cell center; the edge is half a period before it."""
    z = spectrum(prof - prof.mean(), np.array([p]))[0]
    center = (-np.angle(z) / (2 * np.pi) * p) % p
    return (center - p / 2) % p


def column_pitch_comb(col_ink: np.ndarray, py: float) -> tuple[float, float]:
    """Provisional column pitch: strongest periodic component of the column ink-mass profile inside the
    monospace aspect window (width/height 0.40-0.68). Returns (pitch, prominence)."""
    lo, hi = max(3.0, ASPECT_LO * py), ASPECT_HI * py
    prof = col_ink - col_ink.mean()
    ps = np.arange(lo, hi, 0.01)
    z = np.abs(spectrum(prof, ps))
    i = int(z.argmax())
    p, c = refine_peak(prof, float(ps[i]), 0.02, 0.0005)
    return p, float(abs(c) / (np.median(z) + 1e-9))


def column_peak_mag(col_ink: np.ndarray, py: float) -> float:
    """Absolute strength (not normalised by the window's median) of the strongest column periodicity inside the aspect
    window of row pitch `py`; comparable across windows, which the prominence is not."""
    lo, hi = max(3.0, ASPECT_LO * py), ASPECT_HI * py
    prof = col_ink - col_ink.mean()
    return float(np.abs(spectrum(prof, np.arange(lo, hi, 0.01))).max()) / max(1.0, len(prof))


def anchor_pitch(I: np.ndarray, oy: float, py: float, row: int, text: str, pc: float) -> tuple[float, float]:
    """Column pitch from one transcribed run of text (verbatim, anywhere in the row). Template match:
    for each candidate pitch (within +-4% of the comb estimate `pc`) and start offset, score the cells
    of TEXT: a non-space char should have ink in its cell box, a space should not. The best
    (pitch, start) gives the pitch hint, which the caller refines on the whole image. Returns (pitch, match score), the
    score = (ink hits - 1.5 * false hits) / expected ink cells: ~1 for a real match, low when the row geometry is wrong."""
    text = text.strip("\n")
    chars = []                                    # one entry per cell: True = expects ink
    import unicodedata
    for ch in text:
        if unicodedata.combining(ch):
            continue
        w = 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        chars += [ch != " "] * w
    n = len(chars)
    if n < 4 or not any(chars):
        raise ValueError("--anchor-line text is too short to measure a pitch")
    y0, y1 = int(round(oy + row * py)), int(round(oy + (row + 1) * py))
    band = I[max(0, y0):max(1, y1)]
    if not band.any():
        raise ValueError(f"anchor row {row} has no ink")
    colink = band.any(0).astype(np.int64)
    csum = np.concatenate([[0], np.cumsum(colink)])
    W = len(colink)
    want = np.array(chars)
    best = (-1e9, pc, 0.0)
    for px in np.arange(pc * 0.96, pc * 1.04, pc * 0.002):
        inner = 0.2 * px                           # look at the middle 60% of each cell box
        starts = np.arange(0.0, W - n * px, 0.5)
        if starts.size == 0:
            continue
        idx = np.arange(n)
        lo = np.clip((starts[:, None] + idx * px + inner).astype(int), 0, W)
        hi = np.clip((starts[:, None] + (idx + 1) * px - inner).astype(int) + 1, 0, W)
        has = (csum[np.maximum(hi, lo)] - csum[lo]) > 0
        score = (has & want).sum(1) - 1.5 * (has & ~want).sum(1)
        i = int(score.argmax())
        if score[i] > best[0]:
            best = (float(score[i]), float(px), float(starts[i]))
    sc, px, start = best
    if sc <= -1e8:
        raise ValueError(f"anchor text ({n} cells) is wider than the image at the estimated pitch")
    match = sc / max(1, int(want.sum()))
    # snap the run's two ends to the real ink and derive the pitch from the extent
    ns = np.nonzero(want)[0]
    fi, li = int(ns[0]), int(ns[-1])
    glyphs = [ch for ch in text if not unicodedata.combining(ch)]
    wid = np.cumsum([2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in glyphs]) - 1
    first_ch = next(ch for ch in glyphs if ch != " ")
    last_ch = next(ch for ch in reversed(glyphs) if ch != " ")

    def inkw(ch):          # ink width of an end glyph in cell units (derived: Menlo-like fonts)
        if ch in "│┃║|▐▌":
            return 0.12
        if "\u2500" <= ch <= "\u259f":
            return 1.0
        return 0.7
    xa, xb = start + fi * px, start + (li + 1) * px
    lo_a, hi_a = int(max(0, xa - 0.6 * px)), int(min(W, xa + 0.6 * px))
    lo_b, hi_b = int(max(0, xb - 0.6 * px)), int(min(W, xb + 0.6 * px))
    ia, ib = np.nonzero(colink[lo_a:hi_a])[0], np.nonzero(colink[lo_b:hi_b])[0]
    if ia.size and ib.size:
        extent = (lo_b + ib.max() + 1) - (lo_a + ia.min())
        cells = li - fi + 1
        adj = 1.0 - 0.5 * (inkw(first_ch) + inkw(last_ch))
        return float(extent / max(1.0, cells - adj)), match
    return px, match


def comb_pair(row_ink: np.ndarray, gy: np.ndarray, lo: float, hi: float):
    pm, _, prom_m = comb_period(row_ink, lo, hi)
    pg, _, prom_g = comb_period(gy, lo, hi)
    return pm, prom_m, pg, prom_g


def octave_related(a: float, b: float, tol: float = 0.12) -> bool:
    r = max(a, b) / min(a, b)
    return abs(r - 2.0) < 2.0 * tol


def pick_row_pitch(row_ink: np.ndarray, col_ink: np.ndarray, pm: float, prom_m: float, pg: float, prom_g: float,
                   notes: list[str]) -> tuple[float, float, bool]:
    """Choose between the ink-mass and gradient row pitch. When they are an octave apart (the abs-gradient of a text
    block has a strong second harmonic: pitch/2 can win and then halves the column window too), the column profile
    arbitrates: the pitch whose aspect window holds the stronger column periodicity (absolute spectral magnitude) wins, the
    longer one unless the shorter is > 1.25x stronger.
    Returns (pitch, prominence, octave_resolved)."""
    if not octave_related(pm, pg) or abs(max(pm, pg) / min(pm, pg) - 1) < 0.01:
        return (pm, prom_m, False) if prom_m >= prom_g else (pg, prom_g, False)
    hi_p, lo_p = max(pm, pg), min(pm, pg)
    cands = []
    for p in (hi_p, lo_p):
        prom = prom_m if p == pm else prom_g
        cands.append((p, prom, column_peak_mag(col_ink, p)))
    (ph, prh, ch_), (pl, prl, cl_) = cands
    if ch_ >= 0.8 * cl_:
        pick = (ph, prh)
    else:
        pick = (pl, prl)
    if pick[0] != (pm if prom_m >= prom_g else pg):      # the arbitration overruled the more prominent profile: say so
        notes.append(f"row pitch: ink-mass {pm:.2f}px and gradient {pg:.2f}px are an octave apart; kept {pick[0]:.2f}px "
                     f"(column comb strength {ch_:.3g} at the longer pitch vs {cl_:.3g} at the shorter)")
    return pick[0], pick[1], True


ANCHOR_OK = 0.6          # normalised template score above which an anchor match is trusted
ANCHOR_MIN = 0.35


def anchored_pitch(I: np.ndarray, col_ink: np.ndarray, row_ink: np.ndarray, oy_of, py: float, row: int, text: str,
                   pc: float, notes: list[str]):
    """--anchor-line with octave recovery. The row index is read off the ruler of the FIRST grid estimate; when that
    estimate is wrong (row pitch locked at half or double), the same text sits on another row index of the corrected
    grid. Tries the estimate, then 2x and 0.5x of the row pitch (row index re-derived from the same y position), and
    keeps the best template match. -> (px_hint, py, oy, pc)."""
    tried, best = [], None
    for f in (1.0, 2.0, 0.5):
        p2 = py * f
        if not 6.0 <= p2 <= 80.0:
            continue
        oy2 = oy_of(p2)
        row2 = row if f == 1.0 else int(((row + 0.5) * py - 0.0) / p2)
        pc2 = pc if f == 1.0 else column_pitch_comb(col_ink, p2)[0]
        try:
            px, match = anchor_pitch(I, oy2, p2, row2, text, pc2)
        except ValueError as e:
            tried.append(f"row pitch {p2:.2f}px (row {row2}): {e}")
            continue
        tried.append(f"row pitch {p2:.2f}px (row {row2}): match {match:.2f}")
        # a half-height / half-width grid also matches text fairly well, so every octave is scored and the best wins;
        # the first estimate keeps the job unless an alternative is clearly better
        if best is None or match > best[0] + (0.08 if best[2] == py else 0.0):
            best = (match, px, p2, oy2, pc2, row2)
    if best is None or best[0] < ANCHOR_MIN:
        raise ValueError("--anchor-line did not match the image at the estimated row pitch or its octaves ("
                         + "; ".join(tried) + "). Check ROW against the ruler and that TEXT is verbatim, "
                         "or rerun with --cols/--rows (exact terminal size) instead")
    match, px, p2, oy2, pc2, row2 = best
    if p2 != py:
        p2, _ = refine_peak(row_ink - row_ink.mean(), p2, 0.04 * p2, 0.002)       # 2x / 0.5x of an estimate is only approximate
        oy2 = oy_of(p2)
        notes.append(f"--anchor-line did not fit the first row-pitch estimate ({py:.2f}px); retried at {p2:.2f}px "
                     f"(octave) where it matches (score {match:.2f}, row {row2}); the ruler grid of that estimate was wrong")
    return px, p2, oy2, pc2, match


def advice(conf: float, size_given: bool) -> str:
    """ok >= 0.7; check-ruler 0.4-0.7 (read the printed ruler against the image before trusting cell coordinates);
    give-size < 0.4 (rerun with --cols/--rows or --anchor-line). With both counts already given, give-size is not offered."""
    if conf >= 0.7:
        return "ok"
    return "check-ruler" if conf >= 0.4 or size_given else "give-size"


def detect_grid(body: np.ndarray, args, notes: list[str]) -> dict:
    bg = modal_color(body)
    I = mask_corners(ink_mask(body, bg), body, bg)
    H, W = I.shape
    ys, xs = np.nonzero(I)
    if ys.size < 50:
        raise RuntimeError("no ink found: image looks blank")
    ix0, ix1, iy0, iy1 = int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1

    # rows
    row_ink = I.sum(1).astype(float)
    col_ink = I.sum(0).astype(float)
    gy = np.abs(np.diff(row_ink))
    # two views of the same periodicity: ink mass (clean on dense UIs) and its gradient; keep the
    # more prominent peak, unless they are an octave apart: then the column profile arbitrates
    pm, prom_m, pg, prom_g = comb_pair(row_ink, gy, 6.0, 80.0)
    py, prom_y, octave = pick_row_pitch(row_ink, col_ink, pm, prom_m, pg, prom_g, notes)
    method = {"row_pitch": "fourier-comb(ink mass | gradient, harmonic-scored)"}
    if octave:
        method["row_pitch"] += "; octave resolved with the column comb"
    if args.rows:
        # a known row count bounds the pitch: rows*pitch fits in the body and covers most of the ink extent
        lo_y, hi_y = 0.8 * (iy1 - iy0) / args.rows, 1.02 * H / args.rows
        if lo_y < hi_y and not (lo_y <= py <= hi_y):
            pm, prom_m, pg, prom_g = comb_pair(row_ink, gy, lo_y, hi_y)
            py, prom_y, octave = pick_row_pitch(row_ink, col_ink, pm, prom_m, pg, prom_g, notes)
            method["row_pitch"] += f"; constrained by --rows to {lo_y:.1f}-{hi_y:.1f} px"

    def place(o, pitch, first_ink, extent, count, label):
        """Pick the cell-aligned origin (phase o + k*pitch). With a known count assume symmetric window
        padding (padding = (extent - count*pitch)/2); otherwise the cell holding the first ink is cell 0."""
        if count:
            pad = (extent - count * pitch) / 2.0
            k = round((pad - o) / pitch)
            if abs(o + k * pitch - pad) <= 0.3 * pitch:
                method["origin"] = "ink-mass phase; symmetric-padding rule (cols/rows given)"
                return o + k * pitch
            notes.append(f"{label}: symmetric padding assumption failed; origin = first-ink rule")
        return o + math.floor((first_ink - o) / pitch + 0.25) * pitch

    method["origin"] = "ink-mass phase; first-ink rule"

    def oy_of(pitch):
        return place(phase_origin(row_ink, pitch), pitch, iy0, H, args.rows, "rows")

    oy = oy_of(py)

    # columns: comb estimate inside the aspect window first (always available), then let an anchor
    # line / known column count correct or confirm it
    pc, prom_x = column_pitch_comb(col_ink, py)
    px_hint, anchor_match = None, None
    if args.anchor_line:
        row_s, _, text = args.anchor_line.partition(":")
        if not text:
            raise ValueError("--anchor-line wants ROW:TEXT")
        py0 = py
        px_hint, py, oy, pc, anchor_match = anchored_pitch(I, col_ink, row_ink, oy_of, py, int(row_s), text, pc, notes)
        if py != py0:
            octave = True
            method["row_pitch"] += f"; octave corrected by --anchor-line ({py0:.2f} -> {py:.2f} px)"
            pc, prom_x = column_pitch_comb(col_ink, py)
            prom_y = min(prom_y, 2.5)             # the row evidence belonged to the discarded pitch: confidence drops
        method["col_pitch"] = f"anchor-line(row {int(row_s)}) + local comb refine"
    elif args.cols:
        px_hint = (ix1 - ix0) / max(1.0, args.cols - 0.6)      # ink extent / cols: a lower bound on pitch
        method["col_pitch"] = "cols-given + local comb refine"
    provisional = px_hint is None
    if provisional:
        px = pc
        method["col_pitch"] = "aspect-window comb on column ink mass (provisional; pass --cols or --anchor-line)"
    else:
        # refine near the hint; for --cols the hint is only a lower bound (blank right-hand cells), so
        # prefer the comb value when it is feasible (comb * cols >= ink extent) and within the aspect window
        base = px_hint
        if args.cols and not args.anchor_line and pc * args.cols >= (ix1 - ix0) * 0.98 and pc >= px_hint * 0.97 \
                and pc * args.cols <= W * 1.02:
            base = pc
        px, _ = refine_peak(col_ink - col_ink.mean(), base, 0.03 * base, 0.0005 * base)
        if abs(px - base) / base > 0.035:        # refinement wandered off the hint: keep the hint
            px = base
    ox = place(phase_origin(col_ink, px), px, ix0, W, args.cols, "cols")
    if args.origin:    # given in original-image coordinates; detection runs on the cropped body
        ox, oy = args.origin[0] - args.crop_off[0], args.origin[1] - args.crop_off[1]
        method["origin"] = "explicit --origin"

    cols = args.cols or int(math.ceil((ix1 - ox) / px - 0.1))
    rows = args.rows or int(math.ceil((iy1 - oy) / py - 0.1))
    ratio = max(pm, pg) / min(pm, pg)           # the two profiles agree (or differ by an exact harmonic)
    agree = 1.0 if min(abs(ratio - 1), abs(ratio - 2)) < 0.01 else 0.5 if octave else 0.0
    conf_y = 0.5 * agree + 0.5 * max(0.0, min(1.0, (prom_y - 2.5) / 4))
    conf_x = max(0.0, min(1.0, (prom_x - 2.5) / 4))
    if not provisional:
        conf_x = max(conf_x, 0.8 if anchor_match is None or anchor_match >= ANCHOR_OK else 0.5)
    conf = round(0.5 * conf_y + 0.5 * conf_x, 2)
    if not (args.cols and args.rows):
        notes.append("cols/rows derived from the ink extent (lower bound if the right/bottom cells are blank); "
                     "pass --cols/--rows when the terminal size is known")
    return {
        "cell_px": [round(px, 3), round(py, 3)], "origin_px": [round(float(ox), 2), round(float(oy), 2)],
        "cols": int(cols), "rows": int(rows), "cols_given": bool(args.cols), "rows_given": bool(args.rows),
        "col_pitch_provisional": provisional, "grid_confidence": conf, "advice": advice(conf, bool(args.cols and args.rows)),
        "method": method,
        "diagnostics": {"row_prominence": round(prom_y, 2), "col_prominence": round(prom_x, 2),
                        "row_pitch_mass": round(pm, 3), "row_pitch_gradient": round(pg, 3), "col_pitch_comb": round(pc, 3)},
        "bg": hexc(bg), "ink_bbox_px": [ix0, iy0, ix1, iy1],
    }


# ----------------------------------------------------------------------------- 3/4 images + rulers
def font(size: int):
    for p in ("/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Monaco.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    try:
        return ImageFont.load_default(size)
    except TypeError:  # old Pillow
        return ImageFont.load_default()


def lanczos(im: Image.Image, scale: float) -> Image.Image:
    if abs(scale - 1.0) < 1e-6:
        return im
    return im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS)


def add_ruler(im: Image.Image, cell: tuple[float, float], origin: tuple[float, float],
              first_col: int, first_row: int, ncols: int, nrows: int) -> Image.Image:
    """Margin-only ruler. `origin` = pixel position of cell (first_col, first_row)'s top-left inside `im`.
    Column labels every 10 + ticks every 5 (above and below), row labels left and right (every row when
    the pitch allows, else every 5). Nothing is drawn over the image area. Labels are ABSOLUTE indexes."""
    cw, ch = cell
    f = font(MARGIN_FONT_PX)
    my, mx = MARGIN_FONT_PX + 12, 4 * MARGIN_FONT_PX
    out = Image.new("RGB", (im.width + 2 * mx, im.height + 2 * my), (255, 255, 255))
    out.paste(im, (mx, my))
    d = ImageDraw.Draw(out)
    ink, tick = (0, 0, 0), (90, 90, 90)
    for i in range(ncols):
        c = first_col + i
        x = mx + origin[0] + (i + 0.5) * cw
        if c % 10 == 0:
            for y_text, y_tick in ((1, my - 5), (my + im.height + 6, my + im.height + 1)):
                d.line([x, y_tick, x, y_tick + 4], fill=ink, width=1)
                d.text((x, y_text if y_text == 1 else y_text), str(c), font=f, fill=ink, anchor="ma")
        elif c % 5 == 0:
            d.line([x, my - 4, x, my - 1], fill=tick, width=1)
            d.line([x, my + im.height, x, my + im.height + 3], fill=tick, width=1)
    every = 1 if ch >= MARGIN_FONT_PX + 2 else 5
    for j in range(nrows):
        r = first_row + j
        if r % every:
            continue
        y = my + origin[1] + (j + 0.5) * ch
        d.text((mx - 4, y), str(r), font=f, fill=ink, anchor="rm")
        d.text((mx + im.width + 4, y), str(r), font=f, fill=ink, anchor="lm")
    return out


def plan_pass1(grid: dict, budget: int, min_cw: float) -> dict:
    cw, ch = grid["cell_px"]
    cols, rows = grid["cols"], grid["rows"]
    s = 1.0
    if cw * s < min_cw:
        s = min_cw / cw
    long_edge = max(cols * cw, rows * ch) * s
    tiles = 1
    if long_edge > budget:
        s_fit = budget / max(cols * cw, rows * ch)
        if cw * s_fit >= min_cw:
            s = s_fit
        else:
            s = min_cw / cw
            while True:
                tiles += 1
                tw = (math.ceil(cols / tiles) + 2) * cw * s
                if tw <= budget and rows * ch * s <= budget:
                    break
                if tiles > 8:
                    break
    return {"scale": s, "tiles": tiles}


def tile_ranges(cols: int, tiles: int) -> list[tuple[int, int]]:
    if tiles == 1:
        return [(0, cols)]
    base = math.ceil(cols / tiles)
    return [(max(0, t * base - 1), min(cols, (t + 1) * base + 1)) for t in range(tiles)]   # 2-cell overlap


def cell_crop(img: Image.Image, grid: dict, c0: int, c1: int, r0: int, r1: int):
    """Crop cells [c0,c1) x [r0,r1) (clamped; may extend into the image padding by float edges)."""
    cw, ch = grid["cell_px"]
    ox, oy = grid["origin_px"]
    fx0, fy0 = ox + c0 * cw, oy + r0 * ch
    x0, y0 = int(math.floor(fx0)), int(math.floor(fy0))
    x1, y1 = int(math.ceil(ox + c1 * cw)) + 1, int(math.ceil(oy + r1 * ch)) + 1
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(img.width, x1), min(img.height, y1)
    sub = img.crop((x0, y0, x1, y1))
    return sub, (fx0 - x0, fy0 - y0)


def leaf_regions(doc) -> list[dict]:
    """Accepts a bare list, {"regions": [...]} or a describer pass-1 object (regions with nested
    `children`). Returns the leaf regions (those without children) as [{id, bbox}]."""
    items = doc.get("regions", []) if isinstance(doc, dict) else doc
    out: list[dict] = []

    def walk(r):
        kids = r.get("children") or r.get("regions") or []
        if kids:
            for k in kids:
                walk(k)
        elif "bbox" in r and "id" in r:
            out.append({"id": r["id"], "bbox": r["bbox"]})
    for r in items:
        walk(r)
    return out


def write_outputs(src_rgb: np.ndarray, crop: tuple, grid: dict, args, out: Path) -> None:
    full = Image.fromarray(src_rgb)
    cx0, cy0, cx1, cy1 = crop
    body = full.crop(crop)
    g_body = dict(grid)                      # grid in body coordinates for image slicing
    g_body["origin_px"] = [grid["origin_px"][0] - cx0, grid["origin_px"][1] - cy0]
    cw, ch = grid["cell_px"]
    plan = plan_pass1(grid, args.max_edge, args.min_cell_w)
    s = plan["scale"]
    files, tiles_meta = [], []
    for ti, (c0, c1) in enumerate(tile_ranges(grid["cols"], plan["tiles"])):
        sub, off = cell_crop(body, g_body, c0, c1, 0, grid["rows"])
        im = lanczos(sub, s)
        suf = "" if plan["tiles"] == 1 else f"-{ti + 1}"
        im.save(out / f"pass1{suf}.png", format="PNG")
        ruler = add_ruler(im, (cw * s, ch * s), (off[0] * s, off[1] * s), c0, 0, c1 - c0, grid["rows"])
        ruler.save(out / f"pass1-ruler{suf}.png", format="PNG")
        files.append(f"pass1{suf}.png")
        tiles_meta.append({"file": f"pass1{suf}.png", "ruler": f"pass1-ruler{suf}.png", "cols": [c0, c1],
                           "size_px": list(im.size), "ruler_size_px": list(ruler.size),
                           "origin_px": [round(off[0] * s, 2), round(off[1] * s, 2)]})
    # facts about the image the describer actually sees (not the original): file, cell size and the position of the first cell
    # (column cols[0] of the first tile; every tile lists its own origin_px) inside it, scale vs the original pixels
    grid["pass1"] = {"file": tiles_meta[0]["file"], "cell_px": [round(cw * s, 3), round(ch * s, 3)],
                     "origin_px": tiles_meta[0]["origin_px"], "scale": round(s, 4),
                     "cell_px_scaled": [round(cw * s, 2), round(ch * s, 2)],
                     "tiles": tiles_meta, "long_edge_budget": args.max_edge,
                     "tiled": plan["tiles"] > 1, "note": "ruler images add a margin; labels are absolute cell indexes"}
    if args.regions:
        regs = leaf_regions(json.loads(Path(args.regions).read_text()))
        meta, crops = [], []
        for r in regs:
            b = r["bbox"]
            c0, r0 = max(0, b["x"] - 1), max(0, b["y"] - 1)
            c1, r1 = min(grid["cols"], b["x"] + b["w"] + 1), min(grid["rows"], b["y"] + b["h"] + 1)
            sub, off = cell_crop(body, g_body, c0, c1, r0, r1)
            rs = max(args.region_min_cell_w / cw, 1.0)
            note = None
            long_e = max(sub.width, sub.height) * rs
            if long_e > args.max_edge:
                rs2 = args.max_edge / max(sub.width, sub.height)
                note = (f"region exceeds the {args.max_edge}px budget at {args.region_min_cell_w}px/cell; "
                        f"scaled to {cw * rs2:.1f}px/cell (raise --max-edge on a high-res tier or split the region)")
                rs = rs2
            im = lanczos(sub, rs)
            rid = str(r["id"])
            im.save(out / f"region-{rid}.png", format="PNG")
            ruler = add_ruler(im, (cw * rs, ch * rs), (off[0] * rs, off[1] * rs), c0, r0, c1 - c0, r1 - r0)
            ruler.save(out / f"region-{rid}-ruler.png", format="PNG")
            crop_cells = {"x": c0, "y": r0, "w": c1 - c0, "h": r1 - r0}
            meta.append({"id": rid, "bbox": b, "crop_cells": crop_cells,
                         "file": f"region-{rid}.png", "ruler": f"region-{rid}-ruler.png",
                         "scale": round(rs, 3), "cell_px_scaled": [round(cw * rs, 2), round(ch * rs, 2)],
                         **({"note": note} if note else {})})
            crops.append({"id": rid, "file": f"region-{rid}.png", "bbox": crop_cells, "scale": round(rs, 4),
                          "cell_px": [round(cw * rs, 3), round(ch * rs, 3)],
                          "origin_px": [round(off[0] * rs, 2), round(off[1] * rs, 2)], "ruler": f"region-{rid}-ruler.png",
                          **({"note": note} if note else {})})
        grid["regions"] = meta
        (out / "crops.json").write_text(json.dumps(crops, indent=2) + "\n")


# ----------------------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], epilog=EPILOG,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--cols", type=int, help="terminal columns (exact when known)")
    ap.add_argument("--rows", type=int, help="terminal rows (exact when known)")
    ap.add_argument("--anchor-line", metavar="ROW:TEXT", help="refine the column pitch from one transcribed line")
    ap.add_argument("--regions", metavar="regions.json",
                    help="bare list of {id, bbox:{x,y,w,h}} or a describer pass-1 JSON (regions[] with nested "
                         "children); one crop per leaf region")
    ap.add_argument("--origin", metavar="X,Y", type=lambda v: tuple(float(t) for t in v.split(",")),
                    help="pixel position of cell (0,0) top-left in the ORIGINAL image (overrides detection)")
    ap.add_argument("--crop", metavar="X,Y,W,H", help="explicit body rectangle in pixels (skips chrome detection)")
    ap.add_argument("--no-crop", action="store_true", help="never crop window chrome")
    ap.add_argument("--max-edge", type=int, default=1568, help="long-edge budget in px (default 1568; 2576 high-res tier)")
    ap.add_argument("--min-cell-w", type=float, default=8.0, help="pass-1 minimum px per cell width (default 8)")
    ap.add_argument("--region-min-cell-w", type=float, default=12.0, help="region crop minimum px per cell width (default 12)")
    ap.add_argument("-o", "--out", required=True, help="output directory")
    args = ap.parse_args(argv)

    try:
        rgb = load_rgb(args.image)
    except (OSError, ValueError) as e:
        print(f"cannot read {args.image}: {e}", file=sys.stderr)
        return 2
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    H, W, _ = rgb.shape
    notes: list[str] = []
    bg_all = modal_color(rgb)
    if args.crop:
        x, y, w, h = (int(v) for v in args.crop.split(","))
        crop = (x, y, x + w, y + h)
        notes.append("explicit --crop")
    elif args.no_crop:
        crop = (0, 0, W, H)
    else:
        crop, n2 = crop_chrome(rgb, bg_all)
        notes += n2
    body = rgb[crop[1]:crop[3], crop[0]:crop[2]]
    args.crop_off = (crop[0], crop[1])
    anchor, args.anchor_line = args.anchor_line, None      # chrome / title-band decisions use the unanchored estimate
    if anchor and ":" not in anchor:
        print("--anchor-line wants ROW:TEXT", file=sys.stderr)
        return 2
    try:
        g = detect_grid(body, args, notes)
        if not (args.crop or args.no_crop) and not any("title bar" in n for n in notes):
            y0 = isolated_title_band(body, g)
            if y0:
                crop = (crop[0], crop[1] + y0, crop[2], crop[3])
                body = rgb[crop[1]:crop[3], crop[0]:crop[2]]
                args.crop_off = (crop[0], crop[1])
                notes.append("title bar stripped (isolated thin ink band at the top; use --no-crop if row 0 was lost)")
                g = detect_grid(body, args, notes)
            else:
                # the title band itself can corrupt the first pitch estimate, which then fails the band test:
                # try a pitch-free band (thin top block followed by a gap at least as tall) and keep it only
                # when the grid detected without it is clearly more confident
                y1 = title_band_candidate(body)
                if y1:
                    body2 = rgb[crop[1] + y1:crop[3], crop[0]:crop[2]]
                    args.crop_off = (crop[0], crop[1] + y1)
                    notes2: list[str] = []
                    g2 = detect_grid(body2, args, notes2)
                    if g2["grid_confidence"] >= g["grid_confidence"] + 0.1:
                        crop, body, g = (crop[0], crop[1] + y1, crop[2], crop[3]), body2, g2
                        notes += notes2 + ["title bar stripped (thin top band; grid confidence rose; use --no-crop "
                                           "if row 0 was lost)"]
                    else:
                        args.crop_off = (crop[0], crop[1])
        if anchor:                                           # final pass on the settled crop, with the anchor line
            args.anchor_line = anchor
            notes3: list[str] = []
            g = detect_grid(body, args, notes3)
            notes[:] = [n for n in notes if not n.startswith("cols/rows derived")] + notes3
    except (RuntimeError, ValueError) as e:
        print(f"grid detection failed: {e}", file=sys.stderr)
        return 1
    notes[:] = list(dict.fromkeys(notes))
    # report in ORIGINAL image coordinates
    g["origin_px"] = [round(g["origin_px"][0] + crop[0], 2), round(g["origin_px"][1] + crop[1], 2)]
    ib = g["ink_bbox_px"]
    g["ink_bbox_px"] = [ib[0] + crop[0], ib[1] + crop[1], ib[2] + crop[0], ib[3] + crop[1]]
    g.update({"image": str(args.image), "image_size_px": [W, H], "crop_px": list(crop),
              "coords": "cells are 0-based; pixels refer to the original image", "notes": notes})
    write_outputs(rgb, crop, g, args, out)
    (out / "grid.json").write_text(json.dumps(g, indent=2) + "\n")
    print(f"grid {g['cols']}x{g['rows']} cell {g['cell_px'][0]}x{g['cell_px'][1]}px origin {g['origin_px']} "
          f"confidence {g['grid_confidence']} ({g['advice']}) -> {out}/grid.json")
    if g["advice"] != "ok":
        print("advice: " + ("read the ruler against the image before trusting cell coordinates; pass --cols/--rows or "
                            "--anchor-line when the size is known" if g["advice"] == "check-ruler" else
                            "grid is a guess; rerun with --cols/--rows (terminal size) or --anchor-line ROW:TEXT"), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
