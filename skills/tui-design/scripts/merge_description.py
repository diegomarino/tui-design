#!/usr/bin/env python3
"""Merge describer pass 1 + pass 2 outputs (+ measured colours) into one validated `tui-description` (audit-protocol.md section 5).

Inputs
  --pass1 P1.json      describer_pass1: regions (no elements), anchor_lines, focus_summary, uncertainties
  --pass2 DIR|FILE...  describer_pass2 objects (one per region): rows (verbatim text of the region bbox), elements, uncertainties.
                       Optional: with none, a pass-1-only description is written (regions, borders, titles, anchor lines; warning)
  --crops crops.json   prep_screenshot.py region crops (default: crops.json next to --grid); recorded in meta.image.preprocessing
  --cells cells.json   sample_colors.py output (screenshot): per-cell bg/fg raw + token candidates + ink; supplies colours, ink checks,
                       coverage check and `theme_guess`
  --grid grid.json     EITHER prep_screenshot.py grid.json (size, cell_px, origin_px, confidence, pass-1 image facts -> meta.image) OR an
                       ansi_grid.py grid (live capture: exact text, colours and attributes from SGR; source "sgr")
  --capture-meta F     capture_tui.sh meta.json (live capture; default: <stem>.meta.json next to an NAME.grid.json) -> meta.capture
Rules implemented (numbers = audit-protocol.md 5.1/5.2)
  1 regions from pass 1, elements concatenated in region order, colliding ids renumbered e<region><seq>
  2 screen_text: live capture from the capture grid; screenshot painted from pass-2 rows (identical overlap fine, a differing overlap -> `[?]` +
    `disagreement`); `[?]` / `[?*]` take one cell, so such rows may be shorter than cols
  3 coverage: inked cells (cells.json) that no pass-2 region painted -> new leaf region role `other` + uncertainty (run pass 2 on it)
  4 element text := its slice of screen_text (screenshot: the element's own version goes to a `disagreement` uncertainty)
  5 bounds: element bbox clipped into its region, child region into its parent (uncertainty `position`)
  7 colours: per element and span, modal RGB class over non-space fg cells / all bg cells; >= 80% -> token, raw, token_candidates, source
    (`sgr` | `pixel`), name null; else keep the vision name + `colour` uncertainty
  8 ink check (screenshot): space transcribed over inked cell / glyph over blank cell -> `ink_mismatch` (source pixel); cells of role `chart`
    regions (plots are written as `[?*]` runs) are never flagged
  9 attributes from SGR in a live capture (>= 80% of ink cells); screenshot keeps vision attrs and confidence
  11 meta from --grid/--crops/--cells/--capture-meta/options (meta.image: cell_px, origin_px, size, confidence, preprocessing; meta.capture); focus_summary "rN ..." sets that region's state.focused with the text as evidence
  13 parent regions (with children) get no pass 2: their borders and titles are painted from pass 1 into blank cells (border glyphs from
    border.style/sides; title position fitted to the cell ink, else the one-space-padded convention; title fg measured); pass-1
    `anchor_lines` fill blanks too
  14 z-order: a cell covered by a region with a higher effective z (a parent's z counts for its children) that painted it takes that
    region's text; the lower region's own transcription there is dropped (no `[?]`) and counted in an `occluded` uncertainty, `occludes`
    is set on the higher region; elements wholly under it are dropped, partly covered ones are clipped to their visible side
Output is validated against references/schemas/tui-description.schema.json (in-process `jsonschema` when importable, else
`uv run --with jsonschema`); inputs are validated against $defs/describer_pass1|2 first. Exit 1 on schema errors.

Examples:
  python3 scripts/merge_description.py --pass1 p1.json --pass2 pass2/ --cells cells.json --grid prep/grid.json \\
      --subject shot.png --model claude-fable -o description.json
  python3 scripts/merge_description.py --pass1 p1.json --pass2 pass2/r*.json --grid 120x30.grid.json --theme catppuccin-mocha -o d.json
  python3 scripts/merge_description.py --validate description.json            # or: --validate pass2.r3.json --part describer_pass2

Exit: 0 ok, 1 schema errors, 2 usage/input/environment error.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import description_to_mock as d2m  # noqa: E402
from _mock import char_width  # noqa: E402
from _theme import ANSI_NAMES, SKILL_ROOT, load_token_defs  # noqa: E402

SCHEMA = SKILL_ROOT / "references" / "schemas" / "tui-description.schema.json"
COVERAGE = 0.8
INK_MIN = 0.05           # cell ink fraction above which a blank cell counts as inked
GLYPH_INK_MIN = 0.005    # a transcribed glyph needs at least this ink
MAX_INK_NOTES = 40
DEFS = None


# ---------------------------------------------------------------- validation

VALIDATOR_SRC = r'''
import json, sys
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
s = json.load(open(sys.argv[1])); jobs = json.load(sys.stdin)
reg = Registry().with_resource(s["$id"], Resource.from_contents(s))
out = []
for doc, part in jobs:
    v = Draft202012Validator({"$ref": s["$id"] + ("#/$defs/" + part if part else "")}, registry=reg)
    out.append(["/".join(map(str, e.path)) + " : " + e.message[:200] for e in v.iter_errors(doc)])
json.dump(out, sys.stdout)
'''


def validate(jobs: list[tuple[dict, str | None]]) -> list[list[str]]:
    """Validate (document, part) pairs; returns one list of error lines per job. Raises RuntimeError without a validator."""
    try:
        import jsonschema  # noqa: F401
        out = subprocess.run([sys.executable, "-c", VALIDATOR_SRC, str(SCHEMA)], input=json.dumps(jobs), capture_output=True, text=True)
    except ImportError:
        if not shutil.which("uv"):
            raise RuntimeError("no jsonschema and no uv: install uv (brew install uv) or `pip install jsonschema` in a venv")
        out = subprocess.run(["uv", "run", "--quiet", "--with", "jsonschema", "python", "-c", VALIDATOR_SRC, str(SCHEMA)],
                             input=json.dumps(jobs), capture_output=True, text=True)
    if out.returncode:
        raise RuntimeError("schema validator failed: " + out.stderr.strip()[-400:])
    return json.loads(out.stdout)


# ---------------------------------------------------------------- helpers

def tokenize(text: str) -> list[str]:
    """One entry per display cell; `[?]` and `[?*]` are single entries; the continuation cell of a wide glyph is ''."""
    cells, i = [], 0
    while i < len(text):
        m = re.match(r"\[\?\*?\]", text[i:])
        if m:
            cells.append(m.group(0))
            i += m.end()
            continue
        ch = text[i]
        i += 1
        w = char_width(ch)
        if w == 0 and cells:
            cells[-1] += ch
        else:
            cells.append(ch)
            if w == 2:
                cells.append("")
    return cells


def walk(regions: list[dict], parent: dict | None = None):
    for r in regions:
        yield r, parent
        yield from walk(r.get("children", []), r)


def clip(bb: dict, outer: dict) -> tuple[dict, bool]:
    x0, y0 = max(bb["x"], outer["x"]), max(bb["y"], outer["y"])
    x1, y1 = min(bb["x"] + bb["w"], outer["x"] + outer["w"]), min(bb["y"] + bb["h"], outer["y"] + outer["h"])
    if x1 <= x0 or y1 <= y0:
        return bb, False
    new = {"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0}
    return (new, new != bb)


def unc(kind: str, note: str, source: str = "derived", ref: str | None = None, field: str | None = None, alts: list | None = None) -> dict:
    u = {"kind": kind, "note": note, "source": source}
    if ref:
        u["ref"] = ref
    if field:
        u["field"] = field
    if alts:
        u["alternatives"] = alts
    return u


class Cells:
    """Uniform per-cell colour/ink access over an ansi_grid grid (live capture, sgr) or sample_colors cells.json (screenshot, pixel)."""

    def __init__(self, grid: dict | None, cells: dict | None):
        self.sgr = bool(grid and isinstance(grid.get("cells"), list) and grid["cells"] and isinstance(grid["cells"][0], list))
        self.grid, self.by_xy = grid if self.sgr else None, {}
        if cells:
            self.by_xy = {(c["x"], c["y"]): c for c in cells.get("cells", [])}
        self.have = self.sgr or bool(self.by_xy)
        self.source = "sgr" if self.sgr else "pixel"

    def get(self, x: int, y: int) -> dict | None:
        if self.sgr:
            try:
                c = self.grid["cells"][y][x]
            except IndexError:
                return None
            return {"ch": c["ch"], "fg": c.get("fg"), "bg": c.get("bg"), "attrs": c.get("attrs", [])} if c["w"] else None
        c = self.by_xy.get((x, y))
        return {"fg": c.get("fg"), "bg": c.get("bg"), "ink": c.get("ink", 0.0), "attrs": []} if c else None


def canonical_tokens(c: dict) -> list[str]:
    global DEFS
    DEFS = DEFS or load_token_defs()
    return [t for t in c.get("tokens", []) if t in DEFS]


def color_object(c: dict, source: str) -> dict:
    slot = c.get("slot")
    toks = canonical_tokens(c)
    token = None
    if slot and (slot.startswith("ansi.") or slot.startswith("p:")):
        token = slot
    elif toks:
        token = toks[0]
    else:
        for t in c.get("tokens", []):
            m = re.fullmatch(r"ansi\.(\d+)", t)
            if m and int(m[1]) < 16:
                token = f"ansi.{ANSI_NAMES[int(m[1])]}"
                break
            if t == "terminal.foreground":
                token = "term.fg"
            elif t == "terminal.background":
                token = "term.bg"
        token = token or (slot if slot in ("term.fg", "term.bg") else None)
    out = {"token": token, "raw": c["raw"].lower(), "name": None, "source": source}
    if len(toks) > 1:
        out["token_candidates"] = toks
    return out


def class_of(cells: list[dict | None], which: str, source: str, need_ink: bool, chars: list[str] | None):
    """Modal RGB class over the selected cells -> (colour object, fraction) or (None, 0)."""
    raws = []
    for i, c in enumerate(cells):
        if not c or not c.get(which):
            continue
        if need_ink and chars is not None and (chars[i] or " ").strip() == "":
            continue
        raws.append(c[which])
    if not raws:
        return None, 0.0
    modal, n = Counter(r["raw"].lower() for r in raws).most_common(1)[0]
    rep = next(r for r in raws if r["raw"].lower() == modal)
    return color_object(rep, source), n / len(raws)


# ---------------------------------------------------------------- merge

class Merger:
    def __init__(self, a: argparse.Namespace, p1: dict, p2s: list[dict], grid: dict | None, cells: dict | None,
                 crops: list | None = None, capture: dict | None = None):
        self.a, self.p1, self.p2s, self.gridjson, self.cellsjson = a, p1, p2s, grid, cells
        self.crops, self.capture = crops, capture
        self.occ_cells: dict[str, set] = {}          # region id -> cells whose own transcription lost to a higher-z region
        self.occ_by: dict[tuple[str, str], int] = {}  # (covered id, covering id) -> cell count
        self.title_runs: dict[str, tuple[int, int, int]] = {}   # parent region id -> (x, y, width) of its painted title
        self.cd = Cells(grid, cells)
        self.path = norm_path(a.path) or ("capture" if self.cd.sgr else "screenshot")
        self.unc: list[dict] = []
        self.palette: dict[str, str] = {}

    # -- size
    def size(self) -> tuple[int, int, str]:
        g, c = self.gridjson or {}, (self.cellsjson or {}).get("meta", {}).get("grid", {})
        for src, d, how in (("user", {"cols": self.a.cols, "rows": self.a.rows}, "user"), ("sgr" if self.cd.sgr else "derived", g, ""),
                            ("derived", c, "")):
            if d.get("cols") and d.get("rows"):
                return d["cols"], d["rows"], how or src
        ext = [(r["bbox"]["x"] + r["bbox"]["w"], r["bbox"]["y"] + r["bbox"]["h"]) for r, _ in walk(self.p1["regions"])]
        if not ext:
            raise ValueError("cannot determine the grid size: give --cols/--rows or --grid")
        return max(e[0] for e in ext), max(e[1] for e in ext), "derived"

    def run(self) -> dict:
        cols, rows, size_src = self.size()
        regions = copy.deepcopy(self.p1["regions"])
        for r, parent in walk(regions):                                        # rule 5, regions
            outer = parent["bbox"] if parent else {"x": 0, "y": 0, "w": cols, "h": rows}
            r["bbox"], changed = clip(r["bbox"], outer)
            if changed:
                self.unc.append(unc("position", f"bbox of {r['id']} clipped into {'parent ' + parent['id'] if parent else 'the screen'}", ref=r["id"], field="bbox"))
        self.unc += [dict(u, source=u.get("source", "vision")) for u in self.p1.get("uncertainties", [])]
        by_id = {r["id"]: r for r, _ in walk(regions)}
        order = {rid: i for i, rid in enumerate(by_id)}
        elements, used = [], set()
        for p2 in sorted(self.p2s, key=lambda p: order.get(p["region"], 10**6)):          # rule 1
            rid = p2["region"]
            if rid not in by_id:
                self.unc.append(unc("other", f"pass-2 output for unknown region {rid}; its elements were kept", ref=rid))
            idmap = {}
            for e in p2["elements"]:
                e = copy.deepcopy(e)
                old = e["id"]
                if old in used:
                    n = 1
                    num = re.sub(r"\D", "", rid) or "0"
                    while f"e{num}{n:02d}" in used:
                        n += 1
                    e["id"] = f"e{num}{n:02d}"
                    idmap[old] = e["id"]
                used.add(e["id"])
                e.setdefault("region", rid)
                elements.append(e)
            for u in p2.get("uncertainties", []):
                u = dict(u, source=u.get("source", "vision"))
                if u.get("ref") in idmap:
                    u["ref"] = idmap[u["ref"]]
                self.unc.append(u)
        self.effz = {}
        for r, parent in walk(regions):
            self.effz[r["id"]] = max(r.get("z", 0) or 0, self.effz.get(parent["id"], 0) if parent else 0)
        text = self.screen_text(cols, rows, p2s=self.p2s, by_id=by_id, regions=regions)
        elements = self.occlude_elements(elements, by_id)
        cells_txt = [tokenize(t) for t in text]
        if self.p2s:
            self.coverage(cols, rows, regions, cells_txt)
        else:
            self.unc.append(unc("other", "pass 2 was not run: no elements, and screen_text holds only borders, titles and anchor lines of pass 1; "
                                "run pass 2 on the leaf regions", "derived"))
        self.ink_check(cols, rows, cells_txt, regions)
        for e in elements:
            self.fix_element(e, by_id, cells_txt, cols, rows)
        self.parent_title_style(regions, cells_txt)
        self.borders(regions, cells_txt, cols, rows)
        self.focus(regions, by_id)
        meta = self.meta(cols, rows, size_src)
        desc = {"schema_version": "1.0", "meta": meta}
        if self.palette:
            desc["palette"] = dict(sorted(self.palette.items()))
        desc.update({"regions": regions, "elements": elements, "screen_text": text, "uncertainties": self.dedupe(self.unc)})
        return desc

    # -- rule 2 (+ rules 13 parent borders/titles, 14 z-order)
    def screen_text(self, cols: int, rows: int, p2s: list[dict], by_id: dict, regions: list[dict] | None = None) -> list[str]:
        if self.cd.sgr:
            return ["".join(c["ch"] for c in row if c["w"]) for row in self.cd.grid["cells"]][:rows] + [" " * cols] * max(0, rows - len(self.cd.grid["cells"]))
        canvas = [[" "] * cols for _ in range(rows)]
        self.painted = set()
        top: dict[tuple[int, int], tuple[int, str]] = {}          # cell -> (highest effective z that transcribed it, region)
        for p2 in p2s:
            z = self.effz.get(p2["region"], 0)
            for row in p2["rows"]:
                for i, _ in enumerate(tokenize(row["text"])):
                    c = (row["x"] + i, row["y"])
                    if c not in top or z > top[c][0]:
                        top[c] = (z, p2["region"])
        for p2 in p2s:
            rid, z = p2["region"], self.effz.get(p2["region"], 0)
            for row in p2["rows"]:
                y = row["y"]
                if not 0 <= y < rows:
                    continue
                for i, t in enumerate(tokenize(row["text"])):
                    x = row["x"] + i
                    if not 0 <= x < cols:
                        continue
                    if top[(x, y)][0] > z:                       # rule 14: a higher-z region (modal, popup, toast) owns this cell
                        self.occ_cells.setdefault(rid, set()).add((x, y))
                        k = (rid, top[(x, y)][1])
                        self.occ_by[k] = self.occ_by.get(k, 0) + 1
                        continue
                    self.painted.add((x, y))
                    old = canvas[y][x]
                    if t.strip() == "" and t != "":
                        continue
                    if old.strip() == "" or old == t:
                        canvas[y][x] = t
                    else:
                        canvas[y][x] = "[?]"
                        self.unc.append(unc("disagreement", f"two regions paint different characters at x={x} y={y}", ref=p2["region"], alts=[old, t]))
        self.paint_parents(canvas, cols, rows, regions or [])
        for (low, high), n in sorted(self.occ_by.items()):
            self.unc.append(unc("occluded", f"rule 14: {n} cells of {low} are covered by {high} (z {self.effz.get(high, 0)} > {self.effz.get(low, 0)}); "
                                f"screen_text there is {high}'s transcription, {low}'s own reading of them was dropped", "derived", ref=low))
            hi = by_id.get(high)
            if hi is not None and low not in hi.setdefault("occludes", []):
                hi["occludes"].append(low)
        for a in self.p1.get("anchor_lines", []):               # verbatim pass-1 runs fill what nothing else painted
            for i, t in enumerate(tokenize(a["text"])):
                x, y = a["x_start"] + i, a["y"]
                if 0 <= x < cols and 0 <= y < rows and canvas[y][x] == " " and t.strip() and (x, y) not in self.painted:
                    canvas[y][x] = t
                    self.painted.add((x, y))
        return ["".join(c) for c in canvas]

    def covered_by_higher(self, x: int, y: int, z: int, regions: list[dict]) -> bool:
        return any(self.effz.get(r["id"], 0) > z and r["bbox"]["x"] <= x < r["bbox"]["x"] + r["bbox"]["w"]
                   and r["bbox"]["y"] <= y < r["bbox"]["y"] + r["bbox"]["h"] for r, _ in walk(regions))

    def paint_parents(self, canvas: list[list[str]], cols: int, rows: int, regions: list[dict]) -> None:
        """Rule 13: borders and titles of non-leaf regions. Pass 2 only sees leaf crops, so these cells come from pass 1."""
        for r, _ in walk(regions):
            bb, b = r["bbox"], r.get("border") or {}
            if not r.get("children") or b.get("style") in (None, "none") or bb["w"] < 2 or bb["h"] < 2:
                continue
            z = self.effz.get(r["id"], 0)
            cv = d2m.new_canvas(cols, rows)
            d2m.draw_border(cv, r)
            for y in range(max(bb["y"], 0), min(bb["y"] + bb["h"], rows)):
                for x in range(max(bb["x"], 0), min(bb["x"] + bb["w"], cols)):
                    c = cv[y][x]
                    if c.claimed and canvas[y][x] == " " and not self.covered_by_higher(x, y, z, regions):
                        canvas[y][x] = c.ch
                        self.painted.add((x, y))
            t = r.get("title") or {}
            if t.get("text") and bb["w"] >= 6:
                x, text, pad_l, pad_r = self.fit_title(r, t["text"], t.get("position") or "top_left")
                y = bb["y"] + bb["h"] - 1 if (t.get("position") or "").startswith("bottom") else bb["y"]
                run = ([" "] if pad_l else []) + list(text) + ([" "] if pad_r else [])
                x0 = x - (1 if pad_l else 0)
                for i, ch in enumerate(run):
                    if 0 <= x0 + i < cols and 0 <= y < rows and not self.covered_by_higher(x0 + i, y, z, regions):
                        canvas[y][x0 + i] = ch
                        self.painted.add((x0 + i, y))
                self.title_runs[r["id"]] = (x, y, d2m.str_width(text))

    def fit_title(self, r: dict, text: str, pos: str) -> tuple[int, str, bool, bool]:
        """Where a parent's title sits on its border row: the candidate (start, padding) whose expected ink pattern (text and
        border glyphs inked, padding spaces blank) agrees best with the measured cell ink; ties go to the conventional
        `─ Title ─` placement. Without cells.json the convention is used (recorded as a `position` uncertainty)."""
        bb = r["bbox"]
        x0, x1 = bb["x"], bb["x"] + bb["w"] - 1
        y = bb["y"] + bb["h"] - 1 if pos.startswith("bottom") else bb["y"]
        w = d2m.str_width(text)
        avail = bb["w"] - 3
        if w > avail:                                   # cut to what fits between the corners
            out, used = "", 0
            for ch in text:
                cw = char_width(ch)
                if used + cw > avail:
                    break
                out, used = out + ch, used + cw
            text, w = out, used
        conv_pad = w + 4 <= bb["w"] - 2
        if pos.endswith("center"):
            want = x0 + (bb["w"] - w) // 2
        elif pos.endswith("right"):
            want = x1 - 2 - w
        else:
            want = x0 + 2 + (1 if conv_pad else 0)
        cands = []
        for pad in ((1, 0) if conv_pad else (0,)):
            for start in range(x0 + 1, x1 - (w + 2 * pad) + 1 + 1):
                cands.append((start + pad, pad))
        if not cands:
            return x0 + 1, text, False, False
        if not self.cd.by_xy:
            self.unc.append(unc("position", f"rule 13: title of {r['id']} placed by convention (no cell ink to fit it)", "derived", ref=r["id"], field="title"))
            best = min(cands, key=lambda c: (abs(c[0] - want), -c[1]))
            return best[0], text, bool(best[1]), bool(best[1])

        def agree(c):
            tx, pad = c
            n = 0
            for x in range(x0 + 1, x1):
                cell = self.cd.by_xy.get((x, y))
                if not cell:
                    continue
                has = cell.get("ink", 0.0) >= 0.02
                blank = (pad and x in (tx - 1, tx + w)) or (tx <= x < tx + w and text[x - tx:x - tx + 1] == " ")
                n += (not has) if blank else has
            return n
        best = max(cands, key=lambda c: (agree(c), -abs(c[0] - want), c[1]))
        if len({agree(c) for c in cands}) == 1:
            self.unc.append(unc("position", f"rule 13: title of {r['id']}: cell ink does not tell where it sits; conventional placement used", "derived",
                                ref=r["id"], field="title"))
        return best[0], text, bool(best[1]), bool(best[1])

    def parent_title_style(self, regions: list[dict], cells_txt: list[list[str]]) -> None:
        """Measured fg of a parent's title text (the leaf regions' own titles are measured through their heading elements)."""
        if not self.cd.have:
            return
        for r, _ in walk(regions):
            run = self.title_runs.get(r["id"])
            if not run or not r.get("title"):
                continue
            x, y, w = run
            col, frac = class_of([self.cd.get(x + i, y) for i in range(w)], "fg", self.cd.source, True, [(cells_txt[y][x + i] if x + i < len(cells_txt[y]) else " ") for i in range(w)])
            if col and frac >= COVERAGE and not (r["title"].get("style") or {}).get("fg"):
                col["confidence"] = "high" if frac >= 0.95 else "medium"
                r["title"].setdefault("style", {})["fg"] = col
                if col["token"] and not col["token"].startswith(("ansi.", "p:", "term.")):
                    self.palette.setdefault(col["token"], col["raw"])

    # -- rule 14 for elements: drop what lies wholly under a higher-z region, clip what is partly covered
    def occlude_elements(self, elements: list[dict], by_id: dict) -> list[dict]:
        out = []
        for e in elements:
            occ = self.occ_cells.get(e["region"])
            bb = e["bbox"]
            if not occ:
                out.append(e)
                continue
            cells = [(x, y) for y in range(bb["y"], bb["y"] + bb["h"]) for x in range(bb["x"], bb["x"] + bb["w"])]
            hit = [c for c in cells if c in occ]
            if not hit:
                out.append(e)
            elif len(hit) == len(cells):
                self.unc.append(unc("occluded", f"rule 14: element {e['id']} lies wholly under a higher-z region; dropped", "derived", ref=e["id"]))
            else:
                self.unc.append(unc("occluded", f"rule 14: element {e['id']} is partly covered by a higher-z region ({len(hit)} of {len(cells)} cells)", "derived",
                                    ref=e["id"], field="bbox"))
                if bb["h"] == 1:
                    vis = [x for x in range(bb["x"], bb["x"] + bb["w"]) if (x, bb["y"]) not in occ]
                    runs, cur = [], [vis[0]]
                    for x in vis[1:]:
                        if x == cur[-1] + 1:
                            cur.append(x)
                        else:
                            runs.append(cur)
                            cur = [x]
                    runs.append(cur)
                    run = max(runs, key=len)                  # the widest visible stretch stays the element
                    shift = run[0] - bb["x"]
                    cells_e = tokenize(e["text"])
                    e["text"] = "".join(cells_e[shift:shift + len(run)]).rstrip()
                    e["bbox"] = {"x": run[0], "y": bb["y"], "w": len(run), "h": 1}
                    spans = []
                    for sp in e.get("spans", []):
                        s0, s1 = max(sp["start"], shift), min(sp["start"] + sp["len"], shift + len(run))
                        if s1 > s0:
                            spans.append(dict(sp, start=s0 - shift, len=s1 - s0))
                    e["spans"] = spans
                    e["truncated"] = e.get("truncated") or ("end" if run[0] == bb["x"] else "start")
                out.append(e)
        return out

    # -- rule 3 + 8
    def coverage(self, cols: int, rows: int, regions: list[dict], cells_txt: list[list[str]]) -> None:
        if self.cd.sgr or not self.cd.have:
            return
        todo = {(x, y) for (x, y), c in self.cd.by_xy.items() if c.get("ink", 0) >= INK_MIN and (x, y) not in self.painted}
        seen = set()
        n = max([int(r["id"][1:]) for r, _ in walk(regions) if r["id"][1:].isdigit()] + [0])
        for start in sorted(todo, key=lambda p: (p[1], p[0])):
            if start in seen:
                continue
            comp, stack = [], [start]
            seen.add(start)
            while stack:                                                       # components with a 1-cell gap tolerance
                x, y = stack.pop()
                comp.append((x, y))
                for dx in (-2, -1, 0, 1, 2):
                    for dy in (-1, 0, 1):
                        q = (x + dx, y + dy)
                        if q in todo and q not in seen:
                            seen.add(q)
                            stack.append(q)
            x0, x1, y0, y1 = min(p[0] for p in comp), max(p[0] for p in comp), min(p[1] for p in comp), max(p[1] for p in comp)
            n += 1
            rid = f"r{n}"
            regions.append({"id": rid, "role": "other", "bbox": {"x": x0, "y": y0, "w": x1 - x0 + 1, "h": y1 - y0 + 1}, "z": 0})
            self.unc.append(unc("other", f"{len(comp)} inked cells outside every pass-2 region; leaf region {rid} added, run pass 2 on it",
                                "pixel", ref=rid, field="bbox"))

    def ink_check(self, cols: int, rows: int, cells_txt: list[list[str]], regions: list[dict]) -> None:
        if self.cd.sgr or not self.cd.by_xy:
            return
        chart = {(x, y) for r, _ in walk(regions) if r["role"] == "chart"          # plots are `[?*]` runs, not transcribable text
                 for y in range(r["bbox"]["y"], r["bbox"]["y"] + r["bbox"]["h"]) for x in range(r["bbox"]["x"], r["bbox"]["x"] + r["bbox"]["w"])}
        notes = 0
        for y in range(rows):
            runs, cur = [], None
            for x in range(min(cols, len(cells_txt[y]))):
                c = self.cd.by_xy.get((x, y))
                if not c or (x, y) not in self.painted or (x, y) in chart:
                    cur = None
                    continue
                t, ink = cells_txt[y][x], c.get("ink", 0.0)
                bad = "ink" if (t.strip() == "" and t != "" and ink >= INK_MIN) else "blank" if (t.strip() and not t.startswith("[?") and ink < GLYPH_INK_MIN and not 0x2580 <= ord(t[0]) <= 0x259F) else ""
                if bad and cur and cur[0] == bad and cur[2] == x - 1:
                    cur[2] = x
                elif bad:
                    cur = [bad, x, x]
                    runs.append(cur)
                else:
                    cur = None
            for bad, xa, xb in runs:
                if notes < MAX_INK_NOTES:
                    what = "claimed blank but has ink" if bad == "ink" else "claimed glyph but has no ink"
                    self.unc.append(unc("ink_mismatch", f"row {y} x={xa}..{xb}: {what}", "pixel", field="screen_text"))
                notes += 1
        if notes > MAX_INK_NOTES:
            self.unc.append(unc("ink_mismatch", f"{notes - MAX_INK_NOTES} more ink mismatch runs not listed", "pixel"))

    # -- rules 4, 5, 7, 9
    def fix_element(self, e: dict, by_id: dict, cells_txt: list[list[str]], cols: int, rows: int) -> None:
        bb = e["bbox"]
        reg = by_id.get(e["region"])
        if reg:
            bb2, changed = clip(bb, reg["bbox"])
            if changed:
                e["bbox"] = bb = bb2
                self.unc.append(unc("position", f"bbox of {e['id']} clipped into region {reg['id']}", ref=e["id"], field="bbox"))
        if "[?*]" not in e["text"] and bb["h"] == 1 and bb["y"] < len(cells_txt):
            sl = "".join(cells_txt[bb["y"]][bb["x"]:bb["x"] + bb["w"]]).rstrip()
            if sl != e["text"].rstrip() and sl:
                if self.path == "screenshot":
                    self.unc.append(unc("disagreement", "element text differs from its screen_text slice; screen_text kept", ref=e["id"], field="text",
                                        alts=[e["text"], sl]))
                e["text"] = sl
        if self.path == "capture":
            e["source"] = "sgr"
        if not self.cd.have:
            return
        flat = [self.cd.get(x, y) for y in range(bb["y"], bb["y"] + bb["h"]) for x in range(bb["x"], bb["x"] + bb["w"])]
        flat_chars = [(cells_txt[y][x] if y < len(cells_txt) and x < len(cells_txt[y]) else " ")
                      for y in range(bb["y"], bb["y"] + bb["h"]) for x in range(bb["x"], bb["x"] + bb["w"])]
        e["style"] = e.get("style") or {}
        self.apply_style(e["style"], flat, flat_chars, e["id"], "style")
        if not e["style"]:
            del e["style"]
        for i, sp in enumerate(e.get("spans", [])):
            x0 = bb["x"] + sp["start"]
            scells = [self.cd.get(x, bb["y"]) for x in range(x0, x0 + sp["len"])]
            schars = [(cells_txt[bb["y"]][x] if bb["y"] < len(cells_txt) and x < len(cells_txt[bb["y"]]) else " ") for x in range(x0, x0 + sp["len"])]
            sp["style"] = sp.get("style") or {}
            self.apply_style(sp["style"], scells, schars, e["id"], f"spans/{i}/style")
            if not sp["style"]:
                del sp["style"]

    def apply_style(self, style: dict, cells: list, chars: list, ref: str, field: str) -> None:
        if not self.cd.sgr:       # screenshot: a solid block (█) is one flat colour in the pixels: that colour is its fg, and it says nothing about the bg
            cells = [dict(c, fg=c["bg"], bg=None) if c and c.get("bg") and chars[i] == "\u2588" else c for i, c in enumerate(cells)]
        for which in ("fg", "bg"):
            col, frac = class_of(cells, which, self.cd.source, which == "fg", chars)
            if col and frac >= COVERAGE:
                col["confidence"] = "high" if frac >= 0.95 else "medium"
                style[which] = col
                if col["token"] and not col["token"].startswith(("ansi.", "p:", "term.")):
                    self.palette.setdefault(col["token"], col["raw"])
            elif col:
                self.unc.append(unc("colour", f"{which} covers only {frac:.0%} of the cells (one RGB class needed: {COVERAGE:.0%}); vision name kept",
                                    self.cd.source, ref=ref, field=f"{field}/{which}"))
            elif which in style and style[which].get("name") is None and not style[which].get("token"):
                style.pop(which)
        if self.cd.sgr:
            ink = [c for c, ch in zip(cells, chars) if c and ch.strip()]
            if ink:
                cnt = Counter(a for c in ink for a in c["attrs"])
                attrs = sorted(a for a, n in cnt.items() if n / len(ink) >= COVERAGE)
                if attrs or "attrs" in style:
                    style["attrs"], style["attrs_source"] = attrs, "sgr"

    # -- rule 7 for region borders: the border glyph colour is measured like an element's fg
    def borders(self, regions: list[dict], cells_txt: list[list[str]], cols: int, rows: int) -> None:
        if not self.cd.have:
            return
        for r, _ in walk(regions):
            b = r.get("border") or {}
            if b.get("style") in (None, "none") or (b.get("style_attrs") or {}).get("fg"):
                continue
            bb = r["bbox"]
            x0, y0, x1, y1 = bb["x"], bb["y"], bb["x"] + bb["w"] - 1, bb["y"] + bb["h"] - 1
            ring = {(x, y) for x in range(x0, x1 + 1) for y in (y0, y1)} | {(x, y) for y in range(y0, y1 + 1) for x in (x0, x1)}
            pts = [(x, y) for x, y in sorted(ring) if 0 <= y < min(rows, len(cells_txt)) and 0 <= x < len(cells_txt[y])
                   and cells_txt[y][x][:1] and 0x2500 <= ord(cells_txt[y][x][0]) <= 0x257F]
            col, frac = class_of([self.cd.get(x, y) for x, y in pts], "fg", self.cd.source, False, None)
            if col and frac >= COVERAGE:
                col["confidence"] = "high" if frac >= 0.95 else "medium"
                b.setdefault("style_attrs", {})["fg"] = col
                r["border"] = b
                if col["token"] and not col["token"].startswith(("ansi.", "p:", "term.")):
                    self.palette.setdefault(col["token"], col["raw"])

    # -- rule 11
    def focus(self, regions: list[dict], by_id: dict) -> None:
        m = re.match(r"\s*(r\d+)\b[\s:,;-]*(.*)", self.p1.get("focus_summary", ""))
        if m and m[1] in by_id:
            st = by_id[m[1]].setdefault("state", {})
            if st.get("focused") is None:
                st["focused"], st["evidence"] = True, (m[2].strip() or "reported by pass 1")

    def meta(self, cols: int, rows: int, size_src: str) -> dict:
        meta = {"source_path": self.path, "size": {"cols": cols, "rows": rows, "source": size_src}}
        if self.a.subject:
            meta["subject"] = self.a.subject
        g = self.gridjson or {}
        if not self.cd.sgr and g:
            img = {k: g[k] for k in ("cell_px", "origin_px") if k in g}
            if g.get("image_size_px"):
                img["width_px"], img["height_px"] = g["image_size_px"]
            gc = g.get("grid_confidence")
            if isinstance(gc, (int, float)) and not isinstance(gc, bool):      # prep_screenshot.py writes 0..1
                gc = "high" if gc >= 0.8 else "medium" if gc >= 0.5 else "low"
            if gc in ("high", "medium", "low"):
                img["grid_confidence"] = gc
            pre = self.preprocessing(g)
            if pre:
                img["preprocessing"] = pre
            if self.a.model:
                img["describer_model"] = self.a.model
            if img:
                meta["image"] = img
            if g.get("image"):
                meta["capture"] = {"tool": f"screenshot {Path(g['image']).name} (prep_screenshot.py)"}
        elif self.a.model:
            meta["image"] = {"describer_model": self.a.model}
        if self.cd.sgr and self.capture:
            cap = self.capture_block(self.capture)
            if cap:
                meta["capture"] = cap
        tg = (self.cellsjson or {}).get("theme_guess") or {}
        name = self.a.theme or tg.get("id")
        if name:
            guess = {"name": name}
            if tg.get("residual") is not None and not self.a.theme:
                guess["residual"] = tg["residual"]
            meta["theme_guess"] = guess
        return meta

    def preprocessing(self, g: dict) -> list[str]:
        """What was done to the image before the describer saw it (prep_screenshot.py grid.json + crops.json)."""
        out = [n for n in g.get("notes", []) if not n.startswith("cols/rows derived")]
        if g.get("method"):
            out.append("grid: " + "; ".join(f"{k} = {v}" for k, v in g["method"].items()))
        if g.get("crop_px") and g.get("image_size_px") and list(g["crop_px"]) != [0, 0, *g["image_size_px"]]:
            out.append("body crop (px of the original) = " + ",".join(str(v) for v in g["crop_px"]))
        if g.get("advice") and g["advice"] != "ok":
            out.append(f"grid advice: {g['advice']}")
        p1 = g.get("pass1") or {}
        if p1.get("file"):
            out.append(f"pass-1 image {p1['file']}: scale {p1.get('scale')}, cell {p1.get('cell_px')} px, first cell at {p1.get('origin_px')} px"
                       + (" (tiled)" if p1.get("tiled") else ""))
        if self.crops:
            scales = sorted({c.get("scale") for c in self.crops if c.get("scale")})
            out.append(f"{len(self.crops)} region crops (crops.json), scale {'/'.join(str(x) for x in scales)}")
        return out

    @staticmethod
    def capture_block(m: dict) -> dict:
        cap: dict = {}
        tool = " / ".join(x for x in ("capture_tui.sh" if m.get("tmux") or m.get("command") else "", m.get("tmux", "")) if x)
        if tool:
            cap["tool"] = tool
        if m.get("env"):
            cap["env"] = {k: str(v) for k, v in m["env"].items()}
        if m.get("keys"):
            cap["keys_sent"] = [str(k) for k in m["keys"]]
        for src, dst in (("stable", "stable"), ("quiet_ms", "quiet_ms"), ("alternate_on", "alternate_screen")):
            if m.get(src) is not None:
                cap[dst] = m[src]
        cur = m.get("cursor")
        if isinstance(cur, dict) and {"x", "y"} <= set(cur):
            cap["cursor"] = {k: cur[k] for k in ("x", "y", "visible") if k in cur}
        return cap

    @staticmethod
    def dedupe(items: list[dict]) -> list[dict]:
        seen, out = set(), []
        for u in items:
            k = json.dumps(u, sort_keys=True)
            if k not in seen:
                seen.add(k)
                out.append(u)
        return out


def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


LEGACY_PATHS = {"A": "capture", "B": "screenshot"}


def norm_path(v):
    """meta.source_path -> 'capture' | 'screenshot'; legacy 'A' / 'B' (old descriptions) are accepted."""
    return LEGACY_PATHS.get(v, v)


def norm_path_arg(v: str) -> str:
    v = norm_path(v)
    if v not in ("capture", "screenshot"):
        raise argparse.ArgumentTypeError(f"invalid choice: {v!r} (choose from 'capture', 'screenshot')")
    return v


def expand(paths: list[str]) -> list[Path]:
    out = []
    for p in paths:
        pp = Path(p)
        out += sorted(pp.glob("*.json")) if pp.is_dir() else [pp]
    return out


def lint(desc: dict) -> list[str]:
    msgs = []
    for obj, label in [(r, r["id"]) for r, _ in walk(desc["regions"])] + [(e, e["id"]) for e in desc["elements"]]:
        st = obj.get("state") or {}
        if any(st.get(k) is True for k in ("focused", "selected", "expanded", "disabled", "current", "busy")) and not st.get("evidence"):
            msgs.append(f"{label}: state flag set without state.evidence")
    return msgs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Merge describer pass 1/pass 2 (+ cells) into a validated tui-description.", epilog=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pass1", metavar="P1.json")
    ap.add_argument("--pass2", nargs="*", metavar="DIR_OR_FILE", help="pass-2 JSON files or directories of them")
    ap.add_argument("--cells", metavar="cells.json", help="sample_colors.py output (screenshot colours, ink, theme guess)")
    ap.add_argument("--grid", metavar="grid.json", help="prep_screenshot.py grid.json (screenshot) or ansi_grid.py grid JSON (live capture)")
    ap.add_argument("--crops", metavar="crops.json", help="prep_screenshot.py crops.json (default: next to --grid, when present)")
    ap.add_argument("--capture-meta", metavar="meta.json", help="capture_tui.sh meta.json for meta.capture (default: NAME.meta.json next to NAME.grid.json)")
    ap.add_argument("--path", type=norm_path_arg, metavar="{capture,screenshot}",
                    help="override the detected source path (capture when --grid is an ansi_grid grid, else screenshot)")
    ap.add_argument("--subject", help="command line (A) or image file name (B)")
    ap.add_argument("--model", help="describer model name for meta.image.describer_model")
    ap.add_argument("--theme", help="theme id for meta.theme_guess.name (live capture; overrides cells.json)")
    ap.add_argument("--cols", type=int)
    ap.add_argument("--rows", type=int)
    ap.add_argument("--validate", metavar="FILE", help="only validate FILE against the schema and exit")
    ap.add_argument("--part", choices=["describer_pass1", "describer_pass2"], help="with --validate: validate a pass fragment")
    ap.add_argument("-o", "--out", help="write the description here (default stdout)")
    a = ap.parse_args(argv)
    try:
        if a.validate:
            errs = validate([(load_json(a.validate), a.part)])[0]
            for e in errs:
                print(f"{a.validate}: {e}", file=sys.stderr)
            print(f"{a.validate}: {'INVALID' if errs else 'valid'}")
            return 1 if errs else 0
        if not a.pass1:
            ap.error("--pass1 is required (or use --validate FILE)")
        p1 = load_json(a.pass1)
        p2s = [load_json(str(p)) for p in expand(a.pass2 or [])]
        if not p2s:
            print("merge_description: warning: no pass-2 files; writing a pass-1-only description (regions, borders, titles, anchor lines; "
                  "no elements)", file=sys.stderr)
        grid = load_json(a.grid) if a.grid else None
        cells = load_json(a.cells) if a.cells else None
        gdir = Path(a.grid).resolve().parent if a.grid else None
        crops_path = Path(a.crops) if a.crops else (gdir / "crops.json" if gdir and (gdir / "crops.json").exists() else None)
        crops = load_json(str(crops_path)) if crops_path else None
        cap_path = Path(a.capture_meta) if a.capture_meta else None
        if cap_path is None and a.grid and Path(a.grid).name.endswith(".grid.json"):
            cand = Path(a.grid).with_name(Path(a.grid).name[:-len(".grid.json")] + ".meta.json")
            cap_path = cand if cand.exists() else None
        capture = load_json(str(cap_path)) if cap_path else None
        jobs = [(p1, "describer_pass1")] + [(p, "describer_pass2") for p in p2s]
        bad = False
        for (doc, part), errs in zip(jobs, validate(jobs)):
            for e in errs:
                print(f"input {part} {doc.get('region', '')}: {e}", file=sys.stderr)
                bad = True
        if bad:
            return 1
        desc = Merger(a, p1, p2s, grid, cells, crops, capture).run()
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"merge_description: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    except RuntimeError as e:
        print(f"merge_description: {e}", file=sys.stderr)
        return 2
    text = json.dumps(desc, ensure_ascii=False, indent=2) + "\n"
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    for m in lint(desc):
        print(f"merge_description: lint: {m}", file=sys.stderr)
    errs = validate([(desc, None)])[0]
    for e in errs:
        print(f"schema: {e}", file=sys.stderr)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
