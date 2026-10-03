#!/usr/bin/env python3
"""Compare two terminal frames in one self-contained HTML page: side by side, overlay, blink, and (text grids) a cell diff.

LEFT and RIGHT may be `.png` / `.svg` images, `.ansi` frames or `.mock` mockups. Non-images are rendered with --theme (default
catppuccin-mocha; a `.mock` is rendered through render_mockup.py's renderer, then ansi_render.py's SVG). When BOTH sides are text
grids (ansi/mock) the page adds a cell diff, computed on the union of the two grids (missing cells = blank default cells):
  text  the displayed glyph differs
  bg    the painted background differs   (same hex, or sharing a theme token within OKLab 0.01, counts as equal)
  fg    the painted foreground differs   (only cells that show ink on both sides, so a text diff is not double-counted)
Highlights: text = red box, bg = blue fill, fg = yellow bar. The summary table (also printed to stdout) gives counts and %;
the exit status is always 0 unless the inputs cannot be read (2). Typical use: original frame vs `description_to_mock.py`
reconstruction, or two framework implementations of the same screen.

Examples:
  python3 scripts/compare.py a.ansi b.ansi --labels ink,textual -o cmp.html
  python3 scripts/compare.py assets/demo/fleet--normal--80x24.mock recon.mock --theme catppuccin-mocha -o cmp.html
  python3 scripts/compare.py screenshot.png frame.ansi -o cmp.html        # images: no cell diff

Exit: 0 ok, 2 usage/input error (missing file, unknown theme).
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _ansi import parse_ansi  # noqa: E402
from _mock import parse_mock  # noqa: E402
from _theme import load_theme  # noqa: E402
from ansi_grid import Colors, build_grid_json  # noqa: E402
from ansi_render import render_svg  # noqa: E402
from render_mockup import render as render_mock_ansi  # noqa: E402

DEFAULT_THEME = "catppuccin-mocha"
IMAGE_EXT = {".png": "image/png", ".svg": "image/svg+xml", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
MAX_LIST = 60


class Side:
    def __init__(self, path: Path, label: str):
        self.path, self.label = path, label
        self.ansi: str | None = None
        self.html = ""              # <img> or inline <svg>
        self.geo: dict | None = None
        self.grid = None

    @property
    def is_grid(self) -> bool:
        return self.ansi is not None


def load_side(path: str, label: str, theme_id: str) -> Side:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"no such file: {path}")
    s = Side(p, label or p.name)
    ext = p.suffix.lower()
    if ext in IMAGE_EXT:
        b64 = base64.b64encode(p.read_bytes()).decode()
        s.html = f'<img alt="{escape(s.label)}" src="data:{IMAGE_EXT[ext]};base64,{b64}">'
        return s
    text = p.read_text(encoding="utf-8", errors="replace")
    theme = load_theme(theme_id)
    if ext == ".mock":
        mock = parse_mock(text, str(p))
        s.ansi = render_mock_ansi(mock, theme, "truecolor")
    else:
        s.ansi = text
    s.grid = parse_ansi(s.ansi)
    return s


def render_side(s: Side, theme_id: str, cols: int | None, rows: int | None) -> None:
    if not s.is_grid:
        return
    theme = load_theme(theme_id)
    s.grid = parse_ansi(s.ansi, cols, rows)
    svg, s.geo = render_svg(s.grid, theme, title=s.label, chrome=True)
    s.html = svg


# ---------------------------------------------------------------- cell diff

def same_color(a: dict, b: dict) -> bool:
    return a["raw"] == b["raw"] or bool(set(a["tokens"]) & set(b["tokens"]))


def cell_diff(left: Side, right: Side, theme_id: str) -> dict:
    colors = Colors(load_theme(theme_id))
    gl, gr = build_grid_json(left.grid, colors), build_grid_json(right.grid, colors)
    cols, rows = gl["cols"], gl["rows"]
    flags: list[tuple[int, int, str]] = []          # (x, y, kinds) with kinds a subset of "tbf"
    text_list, n_text, n_bg, n_fg, n_ink, n_any = [], 0, 0, 0, 0, 0
    for y in range(rows):
        for x in range(cols):
            a, b = gl["cells"][y][x], gr["cells"][y][x]
            kinds = ""
            if a["ch"] != b["ch"]:
                kinds += "t"
                n_text += 1
                if len(text_list) < MAX_LIST:
                    text_list.append((x, y, a["ch"], b["ch"]))
            if a["w"] and b["w"]:
                if not same_color(a["bg"], b["bg"]):
                    kinds += "b"
                    n_bg += 1
                if a["ch"].strip() and b["ch"].strip():
                    n_ink += 1
                    if not same_color(a["fg"], b["fg"]):
                        kinds += "f"
                        n_fg += 1
            if kinds:
                flags.append((x, y, kinds))
                n_any += 1
    return {"cols": cols, "rows": rows, "cells": cols * rows, "text": n_text, "bg": n_bg, "fg": n_fg, "ink": n_ink,
            "any": n_any, "flags": flags, "text_list": text_list}


def overlay_svg(d: dict, geo: dict) -> str:
    """Highlight rects in the coordinate space of the rendered window (same viewBox as the image)."""
    (cw, ch), (ox, oy) = geo["cell_px"], geo["origin_px"]
    w, h = geo["width_px"], geo["height_px"]
    out = [f'<svg class="ov" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">']
    for kind, style in (("b", 'fill="#2f7bff" fill-opacity=".45"'),
                        ("t", 'fill="#ff2d2d" fill-opacity=".30" stroke="#ff2d2d" stroke-width="1.2"'),
                        ("f", 'fill="#ffd400" fill-opacity=".95"')):
        by_row: dict[int, list[int]] = {}
        for x, y, k in d["flags"]:
            if kind in k:
                by_row.setdefault(y, []).append(x)
        for y, xs in by_row.items():
            run = [xs[0], xs[0]]
            for x in xs[1:] + [None]:
                if x is not None and x == run[1] + 1:
                    run[1] = x
                    continue
                rx, ry = ox + run[0] * cw, oy + y * ch
                rh = ch if kind != "f" else max(2.5, ch * 0.16)
                ry = ry if kind != "f" else ry + ch - rh
                out.append(f'<rect x="{rx:g}" y="{ry:g}" width="{(run[1] - run[0] + 1) * cw:g}" height="{rh:g}" {style}/>')
                run = [x, x]
    out.append("</svg>")
    return "".join(out)


def summary_rows(d: dict) -> list[tuple[str, int, int, float]]:
    def pct(n, tot):
        return 100.0 * n / tot if tot else 0.0
    return [("text", d["text"], d["cells"], pct(d["text"], d["cells"])),
            ("bg", d["bg"], d["cells"], pct(d["bg"], d["cells"])),
            ("fg (cells with ink on both sides)", d["fg"], d["ink"], pct(d["fg"], d["ink"])),
            ("any difference", d["any"], d["cells"], pct(d["any"], d["cells"]))]


def summary_md(left: Side, right: Side, d: dict | None) -> str:
    lines = [f"compare: {left.label} vs {right.label}"]
    if d is None:
        return "\n".join(lines + ["cell diff unavailable (an input is an image)"]) + "\n"
    lines += [f"grid {d['cols']}x{d['rows']} ({d['cells']} cells)", "", "| metric | mismatched | of | % |", "|---|---|---|---|"]
    lines += [f"| {n} | {a} | {b} | {p:.2f}% |" for n, a, b, p in summary_rows(d)]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- page

def build_page(left: Side, right: Side, d: dict | None, theme_id: str) -> str:
    def pane(s: Side, which: str) -> str:
        ov = f'<div class="hl" data-hl hidden>{overlay_svg(d, s.geo)}</div>' if d and s.geo else ""
        return f'<div class="pane" id="p-{which}"><div class="img">{s.html}{ov}</div><div class="lbl">{escape(s.label)}</div></div>'

    table = ""
    if d:
        rows = "".join(f"<tr><td>{escape(n)}</td><td>{a}</td><td>{b}</td><td>{p:.2f}%</td></tr>" for n, a, b, p in summary_rows(d))
        listing = "".join(f"<li>({x},{y}) <code>{escape(a or '∅')}</code> vs <code>{escape(b or '∅')}</code></li>"
                          for x, y, a, b in d["text_list"])
        more = f"<li>… {d['text'] - len(d['text_list'])} more</li>" if d["text"] > len(d["text_list"]) else ""
        table = (f'<section class="sum"><h2>Cell diff <small>{d["cols"]}x{d["rows"]}, theme {escape(theme_id)}</small></h2>'
                 f'<div class="tw"><table><thead><tr><th>metric</th><th>mismatched</th><th>of</th><th>%</th></tr></thead><tbody>{rows}</tbody></table></div>'
                 f'<p class="key"><span class="sw t"></span> text differs <span class="sw b"></span> background differs <span class="sw f"></span> foreground differs</p>'
                 f'<details><summary>text mismatches (left vs right, first {MAX_LIST})</summary><ul>{listing}{more}</ul></details></section>')
    note = "" if d else '<p class="key">Cell diff needs both sides to be .ansi or .mock; an image side disables it.</p>'
    modes = [("side", "Side by side"), ("overlay", "Overlay"), ("blink", "Blink")] + ([("diff", "Cell diff")] if d else [])
    buttons = "".join(f'<button data-mode="{m}" aria-pressed="false">{escape(t)}</button>' for m, t in modes)
    return (PAGE.replace("__TITLE__", escape(f"{left.label} vs {right.label}")).replace("__BUTTONS__", buttons)
            .replace("__LEFT__", pane(left, "l")).replace("__RIGHT__", pane(right, "r"))
            .replace("__TABLE__", table).replace("__NOTE__", note).replace("__HASDIFF__", "true" if d else "false"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Compare two frames (png/svg/ansi/mock) in one HTML page.", epilog=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("left", metavar="LEFT")
    ap.add_argument("right", metavar="RIGHT")
    ap.add_argument("--labels", help="two comma-separated labels, e.g. original,reconstruction (default: file names)")
    ap.add_argument("--theme", default=DEFAULT_THEME, help=f"theme id for ansi/mock sides (default {DEFAULT_THEME})")
    ap.add_argument("-o", "--out", default="compare.html", help="output HTML (default compare.html)")
    a = ap.parse_args(argv)
    labels = (a.labels or "").split(",")
    if a.labels and len(labels) != 2:
        ap.error("--labels needs exactly two comma-separated values")
    labels = labels if a.labels else ["", ""]
    try:
        left, right = load_side(a.left, labels[0], a.theme), load_side(a.right, labels[1], a.theme)
        cols = rows = None
        if left.is_grid and right.is_grid:
            cols, rows = max(left.grid.cols, right.grid.cols), max(left.grid.rows, right.grid.rows)
        render_side(left, a.theme, cols, rows)
        render_side(right, a.theme, cols, rows)
        d = cell_diff(left, right, a.theme) if left.is_grid and right.is_grid else None
    except (OSError, ValueError, KeyError) as e:
        print(f"compare: {e}", file=sys.stderr)
        return 2
    Path(a.out).write_text(build_page(left, right, d, a.theme), encoding="utf-8")
    sys.stdout.write(summary_md(left, right, d))
    print(f"-> {a.out}")
    return 0


PAGE = r"""<meta charset="utf-8">
<title>__TITLE__</title>
<style>
:root{--bg:#f4f4f2;--panel:#fff;--ink:#1d1d1f;--muted:#5e5e66;--line:#d6d6d2;--accent:#2f5fd0;--stage:#e6e6e2;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#17171a;--panel:#212125;--ink:#ececf0;--muted:#a0a0aa;--line:#3a3a40;--accent:#8fb0ff;--stage:#101012;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#17171a;--panel:#212125;--ink:#ececf0;--muted:#a0a0aa;--line:#3a3a40;--accent:#8fb0ff;--stage:#101012;color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.4 system-ui,-apple-system,"Segoe UI",sans-serif;padding-inline:16px}
header{padding-block:12px 8px;border-bottom:1px solid var(--line)}
h1{font-size:16px;margin:0 0 8px}h2{font-size:14px;margin:16px 0 8px}h2 small{color:var(--muted);font-weight:400}
.bar{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center}
button,select,input{font:inherit;font-size:13px;color:var(--ink);background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:5px 10px;min-height:32px}
button{cursor:pointer}button[aria-pressed="true"]{border-color:var(--accent);outline:1px solid var(--accent)}
button:focus-visible,select:focus-visible,input:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
label.inl{display:inline-flex;gap:6px;align-items:center;color:var(--muted);font-size:12px}
input[type=range]{padding:0;min-height:0;width:140px}
main{padding-block:14px 32px}
.panes{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
@media (max-width:760px){.panes{grid-template-columns:1fr}}
.pane{background:var(--stage);border:1px solid var(--line);border-radius:10px;padding:12px;min-width:0}
.img{position:relative}.img>svg,.img>img{display:block;width:100%;height:auto}
.hl{position:absolute;inset:0;pointer-events:none}.hl svg{width:100%;height:100%;display:block}
.lbl{margin-top:8px;font-size:12px;color:var(--muted);word-break:break-word}
.stack .pane{padding:12px}.stack{position:relative}
.stack #p-r{position:absolute;inset:0;background:transparent;border-color:transparent}
.stack #p-r .lbl,.stack #p-l .lbl{display:none}
.stack .lblbar{display:block}
table{border-collapse:collapse;min-width:360px}td,th{border:1px solid var(--line);padding:4px 10px;text-align:right}td:first-child,th:first-child{text-align:left}
.tw{overflow-x:auto}.key{color:var(--muted);font-size:12px}
.sw{display:inline-block;width:12px;height:12px;vertical-align:-2px;margin:0 4px 0 10px;border:1px solid var(--line)}
.sw.t{background:#ff2d2d80}.sw.b{background:#2f7bffa0}.sw.f{background:#ffd400}
code{background:var(--panel);padding:0 4px;border-radius:3px}details{margin-top:8px}ul{columns:3 160px;margin:8px 0;padding-left:18px}
</style>
<header><h1>__TITLE__</h1>
<div class="bar" role="toolbar" aria-label="View mode">__BUTTONS__
<label class="inl" id="op-wrap">opacity <input type="range" id="op" min="0" max="100" value="50" aria-label="Right image opacity"></label>
<label class="inl" id="df-wrap"><input type="checkbox" id="df"> difference blend</label>
<label class="inl" id="bl-wrap">blink <select id="bl"><option value="400">0.4 s</option><option value="800" selected>0.8 s</option><option value="1500">1.5 s</option></select>
<button id="bl-pause" aria-pressed="false">pause</button></label>
<label class="inl" id="hl-wrap"><input type="checkbox" id="hl"> highlight cell diff</label></div>
<p class="key" id="blink-state" aria-live="polite"></p>__NOTE__</header>
<main><div class="panes" id="panes">__LEFT__ __RIGHT__</div>__TABLE__</main>
<script>
(function(){
"use strict";
var HAS=__HASDIFF__,mode=HAS?"diff":"side",panes=document.getElementById("panes"),L=document.getElementById("p-l"),R=document.getElementById("p-r"),
  timer=null,showRight=true,paused=false;
var btns=[].slice.call(document.querySelectorAll("[data-mode]")),hls=[].slice.call(document.querySelectorAll("[data-hl]"));
function $(id){return document.getElementById(id);}
function vis(id,on){$(id).style.display=on?"":"none";}
function apply(){
  clearInterval(timer);timer=null;
  btns.forEach(function(b){b.setAttribute("aria-pressed",b.dataset.mode===mode?"true":"false");});
  panes.className="panes"+(mode==="overlay"||mode==="blink"||mode==="diff"?" stack":"");
  panes.style.gridTemplateColumns=mode==="side"?"":"1fr";
  R.style.display="";L.style.display="";R.style.opacity="1";R.style.mixBlendMode="normal";
  vis("op-wrap",mode==="overlay");vis("df-wrap",mode==="overlay");vis("bl-wrap",mode==="blink");vis("hl-wrap",mode==="side"&&HAS);
  $("blink-state").textContent="";
  if(mode==="overlay"){R.style.opacity=$("op").value/100;R.style.mixBlendMode=$("df").checked?"difference":"normal";R.style.background=$("df").checked?"transparent":"";}
  if(mode==="blink"){tick(true);timer=setInterval(function(){if(!paused)tick(false);},+$("bl").value);}
  if(mode==="diff"){panes.className="panes";panes.style.gridTemplateColumns="repeat(2,minmax(0,1fr))";L.style.opacity=".55";R.style.opacity=".55";}
  var on=mode==="diff"||(mode==="side"&&$("hl").checked);
  hls.forEach(function(h){h.hidden=!on;});
  if(mode!=="diff"){L.style.opacity="1";}
}
function tick(first){if(!first)showRight=!showRight;R.style.visibility=showRight?"visible":"hidden";$("blink-state").textContent="showing "+(showRight?"RIGHT":"LEFT");}
btns.forEach(function(b){b.addEventListener("click",function(){mode=b.dataset.mode;showRight=true;R.style.visibility="visible";apply();});});
["op","df","bl","hl"].forEach(function(id){$(id).addEventListener("input",apply);});
$("bl-pause").addEventListener("click",function(){paused=!paused;this.setAttribute("aria-pressed",paused?"true":"false");});
document.addEventListener("keydown",function(e){if(e.target.tagName==="INPUT"||e.target.tagName==="SELECT")return;
  var order=btns.map(function(b){return b.dataset.mode;}),i=order.indexOf(mode);
  if(e.key==="ArrowRight"||e.key==="ArrowLeft"){mode=order[(i+(e.key==="ArrowRight"?1:order.length-1))%order.length];R.style.visibility="visible";apply();e.preventDefault();}
  else if(e.key===" "&&mode==="blink"){showRight=!showRight;R.style.visibility=showRight?"visible":"hidden";$("blink-state").textContent="showing "+(showRight?"RIGHT":"LEFT");e.preventDefault();}});
apply();
})();
</script>
"""

if __name__ == "__main__":
    sys.exit(main())
