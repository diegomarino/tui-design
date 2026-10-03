#!/usr/bin/env python3
"""Score a hypothesis `tui-description` against ground truth (the audit's perception calibration rubric).

Metrics (pass bar -> exit 1 when any GATED metric fails):
  grid        exact cols x rows                                              must match
  regions     greedy one-to-one match on cell IoU: mean IoU >= 0.9, exact-box rate >= 80%; P/R @ IoU>=0.5 reported
  roles       region role + element type accuracy over matched (IoU>=0.5)    >= 85%
  text        micro CER over right-trimmed rows, `[?]` = 1 substitution      <= 2%
              hallucination CER (substitutions excluding `[?]`, plus insertions)   <= 0.5%
  colour      fg token accuracy over truth non-space cells, RGB-equivalence classes (same hex = one class)   >= 95%
              (bg accuracy over all cells and per-class detail are reported)
  attributes  per-attribute P/R over perceivable cells; gated: reverse, underline (P and R >= 0.9, my bar)
  state       focused / selected / checked / expanded exact match            must match (n/a if neither side asserts any; info
              when only the hypothesis does: a truth without `#! focus` / `#! selected` headers has no state to gate on)
  key hints   F1 over normalised (key, action) pairs                         >= 0.9
  neutrality  evaluative words in `observations` (LEXICON below)      0
  recon       description rendered with ONLY asserted content (see description_to_mock.py): text cells >= 98%, bg >= 98%
Rows without a signal in the truth show `n/a` and are not gated. Unclaimed cells are default fg/bg in both sides.

Hypothesis text = `screen_text` if present, else the asserted-only reconstruction. TRUTH may be any tui-description
(e.g. `ansi_grid.py --describe` output). To build a complete truth from a source mock use
`--truth-from-mock FILE.mock --theme ID`: the mock is rendered, `ansi_grid --describe` runs on it, the mock's
`#! region` lines replace the detected regions, and one `__truth_run` element per same-style row run carries every cell's
colours/attributes (these are ignored by element matching). The mock's `#! focus <region-id>` sets `state.focused` on that
region and `#! selected <region-id> <row>` (row = 0-based inside the region interior) sets `state.selected` on the element at
that row (a synthetic `list_item`/`table_row`/`tree_item` element when the skeleton has none). `--save-truth OUT.json` keeps it;
HYP `-` = score the truth against itself.
Perceivable truth: a space or full block (█) with reverse video is a background, not a reverse attribute (bg scored, reverse
not gated on it); a █ cell counts as a background of its fg colour (not in fg accuracy; bg accuracy / recon bg compare what is seen). Cells of truth regions with role `chart` (braille / sparkline content) are excluded from the row CER, which is
reported separately as `chart CER` (info).

Examples:
  python3 scripts/score_description.py hyp.json truth.json
  python3 scripts/score_description.py hyp.json --truth-from-mock assets/demo/fleet--normal--80x24.mock --theme catppuccin-mocha
  python3 scripts/score_description.py hyp.json truth.json --format json -o scores.json

Exit: 0 all gated metrics pass, 1 some fail, 2 usage/input error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _ansi import parse_ansi  # noqa: E402
from _mock import char_width  # noqa: E402
from _theme import ANSI_NAMES, load_theme, palette256  # noqa: E402
from description_to_mock import build_canvas, flatten_regions  # noqa: E402

DEFAULT_THEME = "catppuccin-mocha"
LEXICON = ("good bad clean cluttered should poor nice ugly confusing inconsistent too better worse "
           "messy cramped awkward great beautiful intuitive").split()
LEX_RE = re.compile(r"\b(" + "|".join(LEXICON) + r")\b|\b(well-)", re.I)
SCORED_ATTRS = ("bold", "italic", "underline", "reverse", "dim", "strike")
GATED_ATTRS = ("reverse", "underline")
STATE_KEYS = ("focused", "selected", "checked", "expanded", "disabled", "current", "busy")
RUN = "__truth_run"
UNK = "\uffff"


# ---------------------------------------------------------------- truth from a mock

def build_truth_from_mock(mock_path: str, theme_id: str | None) -> dict:
    import render_mockup
    from _mock import parse_mock
    from ansi_grid import Colors, Describer

    text = Path(mock_path).read_text(encoding="utf-8")
    mock = parse_mock(text, mock_path)
    theme = load_theme(theme_id or mock.theme or DEFAULT_THEME)
    grid = parse_ansi(render_mockup.render(mock, theme, "truecolor"), mock.cols, mock.rows)
    colors = Colors(theme)
    desc = Describer(grid, theme, colors, Path(mock_path).name).run()
    desc["meta"]["theme_guess"]["name"] = theme.id
    skel = desc["regions"]
    if mock.regions:
        regs = [r for r in skel if r["role"] == "screen"][:1]
        for i, mr in enumerate(mock.regions, 1):
            bb = {"x": mr.x, "y": mr.y, "w": mr.w, "h": mr.h}
            reg = {"id": mr.id, "role": mr.role, "bbox": bb, "z": 0, "order": i}
            twin = next((s for s in skel if s["bbox"] == bb and s["role"] != "screen"), None)
            if twin and "border" in twin:
                reg["border"] = twin["border"]
            if mr.title:
                reg["title"] = {"text": mr.title, **({k: v for k, v in twin["title"].items() if k != "text"}
                                                     if twin and "title" in twin else {})}
            regs.append(reg)
        desc["regions"] = regs

    def home(x: int, y: int) -> str:
        inside = [r for r in desc["regions"] if r["role"] != "screen" and r["bbox"]["x"] <= x < r["bbox"]["x"] + r["bbox"]["w"]
                  and r["bbox"]["y"] <= y < r["bbox"]["y"] + r["bbox"]["h"]]
        return min(inside, key=lambda r: r["bbox"]["w"] * r["bbox"]["h"])["id"] if inside else "r0"

    for e in desc["elements"]:
        e["region"] = home(e["bbox"]["x"], e["bbox"]["y"])
    base_bgs = {theme.background, theme.hex("bg.base")}
    n = 1000
    for y, row in enumerate(grid.cells):
        x, runs = 0, []
        for c in row:
            if not c.w:
                continue
            fg, bg = colors.cell_colors(c.style)
            key = (fg["raw"], bg["raw"], tuple(sorted(c.style.attrs)))
            if runs and runs[-1]["key"] == key:
                runs[-1]["text"] += c.ch
                runs[-1]["w"] += c.w
            else:
                runs.append({"key": key, "x": x, "w": c.w, "text": c.ch, "fg": fg, "bg": bg})
            x += c.w
        for r in runs:
            fg_raw, bg_raw, attrs = r["key"]
            if not r["text"].strip() and bg_raw in base_bgs and not {"underline", "reverse", "strike"} & set(attrs):
                continue
            el = {"id": f"e{n}", "region": home(r["x"], y), "type": "text", "name": RUN,
                  "bbox": {"x": r["x"], "y": y, "w": r["w"], "h": 1}, "text": r["text"],
                  "style": {"fg": colors.schema_color(r["fg"]), "bg": colors.schema_color(r["bg"]), "attrs": list(attrs)},
                  "source": "derived"}
            desc["elements"].append(el)
            n += 1
    inject_state(desc, mock, grid)
    return desc


def inject_state(desc: dict, mock, grid) -> None:
    """Apply the mock's `#! focus` / `#! selected` headers to the truth description."""
    by_id = {r["id"]: r for r in desc["regions"]}
    if mock.focus in by_id:
        by_id[mock.focus]["state"] = {"focused": True, "evidence": "#! focus header of the source mock"}
    corners = set("┌╭┏╔╒╓┍┎+")
    for rid, row in mock.selected:
        reg = by_id.get(rid)
        if not reg:
            continue
        bb = reg["bbox"]
        tl = grid.cells[bb["y"]][bb["x"]].ch if bb["y"] < len(grid.cells) and bb["x"] < len(grid.cells[bb["y"]]) else " "
        edge = 1 if tl in corners else 0                # a box-drawn region: the interior starts inside the border
        x0, x1 = bb["x"] + edge, bb["x"] + bb["w"] - edge
        y = bb["y"] + edge + row
        if x1 <= x0 or y >= bb["y"] + bb["h"] - edge:
            continue
        ev = {"selected": True, "evidence": f"#! selected {rid} {row} header of the source mock"}
        hit = next((e for e in desc["elements"] if e.get("name") != RUN and e["region"] == rid
                    and e["bbox"]["y"] <= y < e["bbox"]["y"] + e["bbox"]["h"]
                    and e["bbox"]["x"] < x1 and e["bbox"]["x"] + e["bbox"]["w"] > x0), None)
        if hit:
            hit["state"] = {**(hit.get("state") or {}), **ev}
            continue
        kind = {"tree": "tree_item", "table": "table_row"}.get(reg["role"], "list_item")
        desc["elements"].append({"id": f"e{len(desc['elements']) + 2000}", "region": rid, "type": kind, "name": "selected row",
                                 "bbox": {"x": x0, "y": y, "w": x1 - x0, "h": 1}, "text": "",       # state anchor only: draws nothing
                                 "state": ev, "source": "derived"})


# ---------------------------------------------------------------- helpers

class Resolver:
    """Schema colour object -> hex (raw wins; then canonical token / terminal slot in the theme)."""

    def __init__(self, theme):
        self.theme, self.pal = theme, palette256(theme.ansi)

    def hex(self, c: dict | None, default: str) -> str:
        if not c:
            return default
        if c.get("raw"):
            return c["raw"].lower()
        tok = c.get("token")
        if tok in self.theme.tokens:
            return self.theme.tokens[tok]
        if tok == "term.fg":
            return self.theme.foreground
        if tok == "term.bg":
            return self.theme.background
        if tok and tok.startswith("ansi.") and tok[5:] in ANSI_NAMES:
            return self.theme.ansi[ANSI_NAMES.index(tok[5:])]
        if tok and tok.startswith("p:") and tok[2:].isdigit() and int(tok[2:]) < 256:
            return self.pal[int(tok[2:])]
        return default


def iou(a: dict, b: dict) -> float:
    ix = max(0, min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"]))
    iy = max(0, min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"]))
    inter = ix * iy
    union = a["w"] * a["h"] + b["w"] * b["h"] - inter
    return inter / union if union else 0.0


def greedy_match(truth: list[dict], hyp: list[dict]) -> dict[int, tuple[int, float]]:
    """One-to-one greedy matching on bbox IoU (descending). Returns truth index -> (hyp index, IoU)."""
    pairs = sorted(((iou(t["bbox"], h["bbox"]), i, j) for i, t in enumerate(truth) for j, h in enumerate(hyp)),
                   key=lambda p: (-p[0], p[1], p[2]))
    used_t, used_h, out = set(), set(), {}
    for v, i, j in pairs:
        if v <= 0:
            break
        if i not in used_t and j not in used_h:
            used_t.add(i), used_h.add(j)
            out[i] = (j, v)
    return out


def edit_ops(ref: str, hyp: str) -> tuple[int, int, int, int]:
    """Levenshtein alignment -> (real substitutions, `[?]` substitutions, insertions, deletions)."""
    n, m = len(ref), len(hyp)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            same = ref[i - 1] == hyp[j - 1]
            d[i][j] = min(d[i - 1][j - 1] + (0 if same else 1), d[i - 1][j] + 1, d[i][j - 1] + 1)
    i, j, sub, unk, ins, dele = n, m, 0, 0, 0, 0
    while i or j:
        if i and j and d[i][j] == d[i - 1][j - 1] + (0 if ref[i - 1] == hyp[j - 1] else 1):
            if ref[i - 1] != hyp[j - 1]:
                if hyp[j - 1] == UNK:
                    unk += 1
                else:
                    sub += 1
            i, j = i - 1, j - 1
        elif i and d[i][j] == d[i - 1][j] + 1:
            dele += 1
            i -= 1
        else:
            ins += 1
            j -= 1
    return sub, unk, ins, dele


def cell_tokens(row: str) -> list[str]:
    """One entry per display cell of a screen_text row; `[?]` / `[?*]` count as one cell, the second cell of a wide glyph is ''."""
    out, i = [], 0
    while i < len(row):
        m = re.match(r"\[\?\*?\]", row[i:])
        if m:
            out.append(m.group(0))
            i += m.end()
            continue
        ch = row[i]
        i += 1
        w = char_width(ch)
        if w == 0 and out:
            out[-1] += ch
        else:
            out.append(ch)
            if w == 2:
                out.append("")
    return out


def canvas_rows(cv) -> list[str]:
    return ["".join(c.ch for c in row if c.w).rstrip() for row in cv]


def norm_key(k: str) -> str:
    k = k.strip().lower().strip("<>[]")
    arrows = {"↑": "up", "↓": "down", "←": "left", "→": "right"}
    if len(k) > 1 and all(c in arrows for c in k):          # "↑↓" is the drawn form of the vocabulary key "up/down"
        return "/".join(arrows[c] for c in k)
    k = re.sub(r"^(\^|⌃|ctrl[-+ ]?)", "ctrl+", k)
    k = re.sub(r"^(⌥|alt[-+ ]?|meta[-+ ]?)", "alt+", k)
    k = re.sub(r"^(⇧|shift[-+ ]?)", "shift+", k)
    for a, b in (("⏎", "enter"), ("↵", "enter"), ("return", "enter"), ("⎋", "esc"), ("escape", "esc"), ("⇥", "tab"),
                 ("↑", "up"), ("↓", "down"), ("←", "left"), ("→", "right"), ("⌫", "backspace")):
        k = k.replace(a, b)
    return k


def norm_action(a: str) -> str:
    return " ".join(a.lower().strip().rstrip(":").split())


def key_hint_set(desc: dict) -> list[tuple[str, str]]:
    return sorted((norm_key(h["key"]), norm_action(h["action"])) for e in desc.get("elements", [])
                  for h in e.get("key_hints", []))


def f1(truth: list, hyp: list) -> tuple[float, float, float]:
    left = list(hyp)
    tp = 0
    for t in truth:
        if t in left:
            left.remove(t)
            tp += 1
    p = tp / len(hyp) if hyp else 0.0
    r = tp / len(truth) if truth else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def flag_overlap(a: dict, b: dict) -> float:
    """Overlap score of two flag boxes (0 = no pairing): IoU when >= 0.5, else the contained fraction of the smaller box when it is
    >= 0.5 and the areas are within 4x."""
    v = iou(a, b)
    if v >= 0.5:
        return v
    ix = max(0, min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"]))
    iy = max(0, min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"]))
    small, big = sorted((a["w"] * a["h"], b["w"] * b["h"]))
    if small and ix * iy / small >= 0.5 and big <= 4 * small:
        return 0.5 * ix * iy / small
    return 0.0


def inside(bb: dict, boxes: list[dict]) -> bool:
    cx, cy = bb["x"] + (bb["w"] - 1) / 2, bb["y"] + (bb["h"] - 1) / 2
    return any(b["x"] <= cx < b["x"] + b["w"] and b["y"] <= cy < b["y"] + b["h"] for b in boxes)


def flags(obj: dict) -> frozenset:
    st = obj.get("state") or {}
    return frozenset(k for k in STATE_KEYS if st.get(k) in (True, "mixed"))


def perceivable(attrs: frozenset, ch: str) -> frozenset:
    """Drop attributes the renderer cannot draw (bold/italic/dim on box glyphs and blanks, blink, hidden)."""
    keep = {a for a in attrs if a in SCORED_ATTRS}
    cp = ord(ch[0]) if ch else 32
    if ch.strip() == "" or 0x2500 <= cp <= 0x259F or unicodedata.category(ch[0]) == "Zs":
        keep -= {"bold", "italic", "dim"}
    if ch.strip() == "" or ch[0] == "\u2588":      # reversed blank / full block is perceived as a background fill (scored as bg)
        keep -= {"reverse"}
    return frozenset(keep)


# ---------------------------------------------------------------- metrics

class Report:
    def __init__(self):
        self.rows: list[dict] = []

    def add(self, group: str, name: str, value, bar: str, ok: bool | None, gated: bool = True, detail: str = "") -> None:
        status = "n/a" if ok is None and value is None else "info" if not gated else "pass" if ok else "fail"
        self.rows.append({"group": group, "metric": name, "value": value, "bar": bar, "status": status, "detail": detail})

    @property
    def failed(self) -> list[dict]:
        return [r for r in self.rows if r["status"] == "fail"]


def pct(v: float | None) -> str:
    return "n/a" if v is None else f"{v * 100:.2f}%"


def score(hyp: dict, truth: dict, theme) -> Report:
    rep = Report()
    res = Resolver(theme)
    ts, hs = truth["meta"]["size"], hyp["meta"]["size"]

    # -- grid
    same = (ts["cols"], ts["rows"]) == (hs["cols"], hs["rows"])
    rep.add("grid", "size", f"{hs['cols']}x{hs['rows']} vs {ts['cols']}x{ts['rows']}", "exact", same)
    if not same:      # cell metrics need a common grid: crop/pad the hypothesis to the truth size
        hyp = json.loads(json.dumps(hyp))
        hyp["meta"]["size"] = {"cols": ts["cols"], "rows": ts["rows"]}

    # -- regions
    treg = [r for r in flatten_regions(truth.get("regions", [])) if r.get("role") != "screen"]
    hreg = [r for r in flatten_regions(hyp.get("regions", [])) if r.get("role") != "screen"]
    rmatch = greedy_match(treg, hreg)
    if treg:
        mean_iou = sum(v for _, v in rmatch.values()) / len(treg)
        m50 = sum(1 for _, v in rmatch.values() if v >= 0.5)
        exact = sum(1 for _, v in rmatch.values() if v == 1.0) / len(treg)
        rep.add("regions", "mean IoU", mean_iou, ">= 0.90", mean_iou >= 0.9, detail=f"{len(treg)} truth, {len(hreg)} hyp")
        rep.add("regions", "exact-box rate", exact, ">= 80%", exact >= 0.8)
        rep.add("regions", "precision @IoU>=0.5", m50 / len(hreg) if hreg else 0.0, "report", True, gated=False)
        rep.add("regions", "recall @IoU>=0.5", m50 / len(treg), "report", True, gated=False)
    else:
        for name in ("mean IoU", "exact-box rate"):
            rep.add("regions", name, None, "-", None, detail="truth has no regions")

    # -- roles (regions + elements, matched @IoU>=0.5)
    tel = [e for e in truth.get("elements", []) if e.get("name") != RUN]
    hel = [e for e in hyp.get("elements", []) if e.get("name") != RUN]
    ematch = greedy_match(tel, hel)
    pairs = [(treg[i]["role"], hreg[j]["role"]) for i, (j, v) in rmatch.items() if v >= 0.5]
    epairs = [(tel[i]["type"], hel[j]["type"]) for i, (j, v) in ematch.items() if v >= 0.5]
    allp = pairs + epairs
    if treg or tel:
        acc = sum(a == b for a, b in allp) / len(allp) if allp else 0.0
        rep.add("roles", "role/type accuracy", acc, ">= 85%", acc >= 0.85,
                detail=f"{sum(a == b for a, b in pairs)}/{len(pairs)} regions, {sum(a == b for a, b in epairs)}/{len(epairs)} elements")
    else:
        rep.add("roles", "role/type accuracy", None, ">= 85%", None)

    # -- text (chart regions are scored apart: braille / sparkline cells are not transcribable text)
    tcv = build_canvas(truth, use_screen_text=True)
    hcv_text = build_canvas(hyp, use_screen_text=True)
    trows = [r.rstrip() for r in (truth.get("screen_text") or canvas_rows(tcv))]
    hrows = [r.rstrip() for r in (hyp.get("screen_text") or canvas_rows(hcv_text))]
    chart_cells = {(x, y) for r in treg if r.get("role") == "chart"
                   for y in range(r["bbox"]["y"], r["bbox"]["y"] + r["bbox"]["h"])
                   for x in range(r["bbox"]["x"], r["bbox"]["x"] + r["bbox"]["w"])}
    n_ref = edits = real = unk_total = 0
    c_ref = c_edits = 0
    for y in range(max(len(trows), len(hrows))):
        tt = cell_tokens(trows[y] if y < len(trows) else "")
        ht = [UNK if t in ("[?]", "[?*]") else t for t in cell_tokens(hrows[y] if y < len(hrows) else "")]
        if chart_cells:
            tt_out = "".join(t for x, t in enumerate(tt) if (x, y) not in chart_cells).rstrip()
            ht_out = "".join(t for x, t in enumerate(ht) if (x, y) not in chart_cells).rstrip()
            tt_in = "".join(t for x, t in enumerate(tt) if (x, y) in chart_cells)
            ht_in = "".join(t for x, t in enumerate(ht) if (x, y) in chart_cells)
            if tt_in.strip() or ht_in.strip():
                sub, unk, ins, dele = edit_ops(tt_in.rstrip(), ht_in.rstrip())
                c_ref += len(tt_in.rstrip())
                c_edits += sub + unk + ins + dele
            ref, h = tt_out, ht_out
        else:
            ref, h = "".join(tt).rstrip(), "".join(ht).rstrip()
        sub, unk, ins, dele = edit_ops(ref, h)
        n_ref += len(ref)
        edits += sub + unk + ins + dele
        real += sub + ins
        unk_total += unk
    if n_ref:
        rep.add("text", "CER (`[?]` = 1 sub)", edits / n_ref, "<= 2%", edits / n_ref <= 0.02,
                detail=f"{edits} edits / {n_ref} chars" + (f"; {len(chart_cells)} chart cells excluded" if chart_cells else ""))
        rep.add("text", "hallucination CER", real / n_ref, "<= 0.5%", real / n_ref <= 0.005,
                detail=f"{real} subs+ins excl. `[?]`; {unk_total} `[?]`")
    else:
        rep.add("text", "CER", None, "<= 2%", None, detail="truth has no text")
    if chart_cells:
        rep.add("text", "chart CER (chart regions)", c_edits / c_ref if c_ref else None, "report", True, gated=False,
                detail=f"{c_edits} edits / {c_ref} chars in role=chart regions")

    # -- recon (asserted only) cells shared by colour/attribute metrics
    hcv = build_canvas(hyp, use_screen_text=False)
    cols, rows = ts["cols"], ts["rows"]
    # perceivable colours: a full block (█) is a solid fill, i.e. a background drawn with the glyph's fg; so its fg is not scored as
    # text colour, and the background a viewer sees there is the fg (a space with that bg is the same picture)
    tcells = [(x, y) for y in range(rows) for x in range(cols) if tcv[y][x].w and tcv[y][x].ch.strip() and tcv[y][x].ch != "\u2588"]
    seen_bg = lambda cv, x, y: res.hex(cv[y][x].fg, dfg) if cv[y][x].ch == "\u2588" else res.hex(cv[y][x].bg, dbg)
    dfg, dbg = theme.foreground, theme.background

    # -- colour tokens
    if tcells:
        fg_ok = sum(res.hex(hcv[y][x].fg, dfg) == res.hex(tcv[y][x].fg, dfg) for x, y in tcells)
        rep.add("colour", "fg token accuracy", fg_ok / len(tcells), ">= 95%", fg_ok / len(tcells) >= 0.95,
                detail=f"{fg_ok}/{len(tcells)} non-space truth cells")
    else:
        rep.add("colour", "fg token accuracy", None, ">= 95%", None)
    all_cells = [(x, y) for y in range(rows) for x in range(cols)]
    bg_ok = sum(seen_bg(hcv, x, y) == seen_bg(tcv, x, y) for x, y in all_cells)
    rep.add("colour", "bg accuracy (all cells)", bg_ok / len(all_cells), "report", True, gated=False)

    # -- attributes
    for a in SCORED_ATTRS:
        tp = fp = fn = 0
        for y in range(rows):
            for x in range(cols):
                tc, hc = tcv[y][x], hcv[y][x]
                if not tc.w:
                    continue
                t = a in perceivable(tc.attrs, tc.ch)
                h = a in perceivable(hc.attrs, tc.ch)
                tp, fp, fn = tp + (t and h), fp + (h and not t), fn + (t and not h)
        if tp + fp + fn == 0:
            rep.add("attributes", f"{a} P/R", None, "report", None, gated=a in GATED_ATTRS)
            continue
        p, r = tp / (tp + fp) if tp + fp else 0.0, tp / (tp + fn) if tp + fn else 0.0
        gated = a in GATED_ATTRS
        rep.add("attributes", f"{a} P/R", f"{p:.2f}/{r:.2f}", ">= 0.9 / 0.9" if gated else "report", p >= 0.9 and r >= 0.9, gated)

    # -- state, compared as flag items (kind, bbox) so it does not depend on how regions/elements were cut. A hypothesis flag pairs
    # with a truth flag of the same kind when the boxes overlap (IoU >= 0.5, or >= 50% of the smaller box inside the other while the
    # areas are within 4x: the describer may flag the interior table of a focused pane). Scope: only kinds the truth asserts; element
    # flags only inside regions where the truth asserts state (an active tab is not a hallucinated selection); `focused` on an element
    # inside a region the hypothesis already marks focused is redundant; a flag overlapping an already paired hypothesis flag is a duplicate.
    kinds = {k for o in treg + tel for k in flags(o)}
    t_ids = {r["id"]: r for r in treg}
    scope = [r["bbox"] for r in treg if flags(r) & kinds] + [t_ids[e["region"]]["bbox"] for e in tel if flags(e) & kinds and e.get("region") in t_ids]
    hfoc = [r["bbox"] for r in hreg if "focused" in flags(r)]
    titems = [(k, o["bbox"]) for o in treg + tel for k in flags(o) & kinds]
    hitems = [(k, o["bbox"], i >= len(hreg)) for i, o in enumerate(hreg + hel) for k in flags(o) & kinds]
    hitems = [(k, b) for k, b, el in hitems if not (el and k == "focused" and inside(b, hfoc))
              and (not el or inside(b, scope))]
    pairs = sorted(((flag_overlap(tb, hb), i, j) for i, (tk, tb) in enumerate(titems) for j, (hk, hb) in enumerate(hitems) if tk == hk),
                   key=lambda p: (-p[0], p[1], p[2]))
    used_t, used_h = set(), set()
    for v, i, j in pairs:
        if v > 0 and i not in used_t and j not in used_h:
            used_t.add(i), used_h.add(j)
    dup = sum(1 for j, (k, b) in enumerate(hitems) if j not in used_h
              and any(hitems[m][0] == k and flag_overlap(b, hitems[m][1]) > 0 for m in used_h))
    fn, fp = len(titems) - len(used_t), len(hitems) - len(used_h) - dup
    if not kinds:
        extra = len([1 for o in hreg + hel for _ in flags(o)])
        rep.add("state", "focus/selected exact", f"{extra} flags asserted by hyp only" if extra else None, "exact", None if not extra else extra == 0,
                gated=False, detail="truth asserts no state (add `#! focus` / `#! selected` to the source mock to gate it)" if extra
                else "neither side asserts state")
    else:
        rep.add("state", "focus/selected exact", f"{fn + fp} mismatching flags", "exact", fn + fp == 0,
                detail=f"kinds compared: {', '.join(sorted(kinds))}; {len(used_t)}/{len(titems)} truth flags found" + (f", {fp} extra" if fp else ""))

    # -- key hints
    tk, hk = key_hint_set(truth), key_hint_set(hyp)
    if tk or hk:
        p, r, f = f1(tk, hk)
        rep.add("key hints", "F1 (key, action)", f, ">= 0.90", f >= 0.9, detail=f"P {p:.2f} R {r:.2f}; {len(tk)} truth, {len(hk)} hyp")
    else:
        rep.add("key hints", "F1 (key, action)", None, ">= 0.90", None)

    # -- neutrality
    words = [m.group(0).lower() for o in hyp.get("observations", []) for m in LEX_RE.finditer(o.get("text", ""))]
    rep.add("neutrality", "evaluative words", len(words), "0", not words, detail=", ".join(sorted(set(words))))

    # -- reconstruction fidelity (asserted content only)
    text_ok = sum(hcv[y][x].ch == tcv[y][x].ch for x, y in all_cells)
    rep.add("recon", "text cells match", text_ok / len(all_cells), ">= 98%", text_ok / len(all_cells) >= 0.98,
            detail="asserted content only (no screen_text)")
    rep.add("recon", "bg cells match", bg_ok / len(all_cells), ">= 98%", bg_ok / len(all_cells) >= 0.98)
    return rep


def fmt_value(v) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, float):
        return pct(v) if v <= 1.0 else f"{v:.3f}"
    return str(v)


def to_markdown(rep: Report, hyp_name: str, truth_name: str) -> str:
    lines = [f"Scores for `{hyp_name}` against `{truth_name}`", "", "| group | metric | value | bar | status | detail |",
             "|---|---|---|---|---|---|"]
    for r in rep.rows:
        lines.append(f"| {r['group']} | {r['metric']} | {fmt_value(r['value'])} | {r['bar']} | {r['status'].upper()} | {r['detail']} |")
    f = rep.failed
    lines += ["", f"**{'FAIL' if f else 'PASS'}**" + (f": {', '.join(r['group'] + '/' + r['metric'] for r in f)}" if f else "")]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Score a tui-description against ground truth.",
                                 epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("hyp", metavar="HYP.json", help="hypothesis description ('-' = the truth itself, self-test)")
    ap.add_argument("truth", metavar="TRUTH.json", nargs="?", help="ground-truth description")
    ap.add_argument("--truth-from-mock", metavar="FILE.mock", help="build the truth from a source mock (see above)")
    ap.add_argument("--theme", help="theme id used to render the mock / resolve tokens (default: truth theme_guess, else "
                                    + DEFAULT_THEME + ")")
    ap.add_argument("--save-truth", metavar="OUT.json", help="write the (built) truth description here")
    ap.add_argument("--format", choices=["md", "json"], default="md")
    ap.add_argument("-o", "--out", help="write the report here instead of stdout")
    a = ap.parse_args(argv)
    if bool(a.truth) == bool(a.truth_from_mock):
        ap.error("give exactly one of TRUTH.json or --truth-from-mock FILE.mock")
    try:
        truth = build_truth_from_mock(a.truth_from_mock, a.theme) if a.truth_from_mock else json.loads(Path(a.truth).read_text("utf-8"))
        hyp = truth if a.hyp == "-" else json.loads(Path(a.hyp).read_text("utf-8"))
        for d in (hyp, truth):
            d["meta"]["size"]["cols"], d["meta"]["size"]["rows"]
        theme = load_theme(a.theme or (truth["meta"].get("theme_guess") or {}).get("name") or DEFAULT_THEME)
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"score_description: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    if a.save_truth:
        Path(a.save_truth).write_text(json.dumps(truth, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    rep = score(hyp, truth, theme)
    out = (json.dumps({"pass": not rep.failed, "metrics": rep.rows}, ensure_ascii=False, indent=2) + "\n"
           if a.format == "json" else to_markdown(rep, a.hyp, a.truth or a.truth_from_mock))
    if a.out:
        Path(a.out).write_text(out, encoding="utf-8")
    else:
        sys.stdout.write(out)
    return 1 if rep.failed else 0


if __name__ == "__main__":
    sys.exit(main())
