#!/usr/bin/env python3
"""Render directories of terminal frames into ONE self-contained HTML gallery (inline SVG, no external requests).

Input: directories holding `<variant>--<state>--<cols>x<rows>.mock|.ansi` (references/formats.md "Frame naming"); the design is the
directory name. Sub-directories are scanned too (each directory with frames is one design). A `.mock` wins over an `.ansi`
with the same name. Every frame is rendered per theme: `.mock` via render_mockup.py's renderer, then ansi_render.py's SVG
(terminal-window chrome, title `design / variant / state / size`). Both are imported from this folder; no subprocess.

The page has selectors for design / variant / state / size / theme, keyboard navigation (left/right = variant, up/down = state,
t = theme, z = size, s = side by side, f = fit/1x), a side-by-side mode that shows two variants (or states) of the same design,
and a caption per frame (`#! title:`, lint summary from the same linter as `render_mockup.py --check`, source file).
A selector value that exists for the design but not with the other current choices stays selectable (marked with a dot);
choosing it snaps the other selectors to the closest combination that exists, so every selection shows a real frame.
Page chrome is neutral and follows light/dark; the frames keep their own theme. Frames are stored once per layout: colours are placeholders (rendered once with a synthetic theme) filled from a per-theme colour string, so N themes cost
little more than one.

Export: every frame has TXT / ANSI / SVG / PNG buttons and "copy text" / "copy ANSI" in the page (downloads work when the
HTML is opened as a local file; inside a published artifact the sandbox blocks downloads, so use the copy buttons there).
`--export DIR` writes the same files for every frame x theme from the command line:
`DIR/<design>/<variant>--<state>--<cols>x<rows>--<theme>.{txt,ansi,svg,png}` (`--formats` picks a subset; PNG needs rsvg-convert).

Examples:
  python3 scripts/gallery.py assets/demo assets/mockups --themes catppuccin-mocha,dracula-classic -o gallery.html
  python3 scripts/gallery.py assets/mockups --themes catppuccin-mocha --export out/ --formats txt,png
  python3 scripts/gallery.py proto/ink proto/textual --title "Fleet in 2 frameworks" -o fleet.html
  python3 scripts/gallery.py frames/ --themes all -o all-themes.html

Themes: `--themes a,b,c` or `all` (every theme in references/themes/). Default: each `.mock`'s `#! theme:` else
catppuccin-mocha (`.ansi` frames: catppuccin-mocha). Exit: 0 ok, 2 usage/input error (no frames, unknown theme).
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _ansi import parse_ansi  # noqa: E402
from _mock import parse_mock  # noqa: E402
from _theme import list_themes, load_theme  # noqa: E402
from ansi_render import render_svg, to_png  # noqa: E402
from render_mockup import render as render_mock_ansi  # noqa: E402

DEFAULT_THEME = "catppuccin-mocha"
FRAME_RE = re.compile(r"^(?P<variant>.+?)--(?P<state>.+?)--(?P<cols>\d+)x(?P<rows>\d+)$")
SIZE_RE = re.compile(r"^(?P<cols>\d+)x(?P<rows>\d+)$")
STATE_ORDER = ["empty", "normal", "busy", "error"]
EXTS = (".mock", ".ansi")


@dataclass
class Frame:
    design: str
    variant: str
    state: str
    size: str
    path: Path
    mock: object = None
    ansi: str = ""
    title: str = ""
    lint: dict = field(default_factory=dict)


def discover(dirs: list[Path]) -> list[Frame]:
    """Find frames under each directory; a `.mock` replaces an `.ansi` of the same stem."""
    by_dir: dict[Path, dict[str, Path]] = {}
    for root in dirs:
        for p in sorted(root.rglob("*")):
            if p.suffix in EXTS and p.is_file():
                files = by_dir.setdefault(p.parent.resolve(), {})
                if p.stem not in files or p.suffix == ".mock":
                    files[p.stem] = p
    names: dict[str, int] = {}
    for d in by_dir:
        names[d.name] = names.get(d.name, 0) + 1
    frames = []
    for d, files in by_dir.items():
        design = d.name if names[d.name] == 1 else f"{d.parent.name}/{d.name}"
        for stem, p in sorted(files.items()):
            m, s = FRAME_RE.match(stem), SIZE_RE.match(stem)
            variant, state = (m["variant"], m["state"]) if m else ("default", "normal") if s else (stem, "normal")
            size = f"{(m or s)['cols']}x{(m or s)['rows']}" if (m or s) else ""
            frames.append(Frame(design, variant, state, size, p))
    return frames


def load_frame(f: Frame) -> None:
    text = f.path.read_text(encoding="utf-8", errors="replace")
    if f.path.suffix == ".mock":
        f.mock = parse_mock(text, str(f.path))
        f.title = f.mock.title
        f.size = f.size or f"{f.mock.cols}x{f.mock.rows}"
        n = {lv: sum(1 for x in f.mock.findings if x.level == lv) for lv in ("ERROR", "WARN", "INFO")}
        f.lint = {"errors": n["ERROR"], "warnings": n["WARN"], "info": n["INFO"]}
        if not f.state or f.state == "normal":
            f.state = f.mock.state or f.state
    else:
        f.ansi = text
        cols, rows = (int(v) for v in f.size.split("x")) if f.size else (None, None)
        g = parse_ansi(text, cols, rows)
        f.size = f.size or f"{g.cols}x{g.rows}"


def synthetic_theme(base):
    """A theme whose every token / ANSI slot / default colour is a unique placeholder hex, so a frame rendered once with it has a
    theme-independent structure; `resolve` maps its placeholders to a real theme's colours."""
    n = [0]

    def nxt() -> str:
        n[0] += 1
        return "#%02x%02x%02x" % (1, n[0] >> 8, n[0] & 255)

    slots: dict[str, tuple] = {}

    def make(key: tuple) -> str:
        h = nxt()
        slots[h] = key
        return h

    tokens = {t: make(("tok", t)) for t in base.tokens}
    ansi = [make(("ansi", i)) for i in range(16)]
    syn = dataclasses.replace(base, tokens=tokens, ansi=ansi, foreground=make(("fg",)), background=make(("bg",)),
                              cursor=make(("cursor",)), selection_background=make(("sel",)))

    def resolve(h: str, theme) -> str:
        key = slots.get(h)
        if key is None:
            return h                                    # literal colour (truecolor / 256-cube): same in every theme
        kind = key[0]
        if kind == "tok":
            return theme.tokens[key[1]]
        if kind == "ansi":
            return theme.ansi[key[1]]
        return {"fg": theme.foreground, "bg": theme.background, "cursor": theme.cursor or theme.foreground,
                "sel": theme.selection_background or theme.background}[kind]

    return syn, resolve


def render_frame(f: Frame, theme) -> str:
    cols, rows = (int(v) for v in f.size.split("x"))
    ansi = render_mock_ansi(f.mock, theme, "truecolor") if f.mock else f.ansi
    grid = parse_ansi(ansi, cols, rows)
    title = f"{f.design} / {f.variant} / {f.state} / {f.size}"
    svg, _ = render_svg(grid, theme, title=title, chrome=True)
    return svg


def frame_themes(f: Frame, requested: list[str] | None) -> list[str]:
    if requested:
        return requested
    return [(f.mock.theme if f.mock and f.mock.theme else DEFAULT_THEME)]


COLOR_ATTR = re.compile(r'="(#[0-9a-fA-F]{6})"')


def skeletonize(svg: str) -> tuple[str, list[str]]:
    """Replace every attribute colour by `="@N"` (N = index in the frame's colour list, first-occurrence order)."""
    colors: list[str] = []

    def sub(m: re.Match) -> str:
        c = m.group(1).lower()
        if c not in colors:
            colors.append(c)
        return f'="@{colors.index(c)}"'

    return COLOR_ATTR.sub(sub, svg), colors


SGR_RGB = re.compile(r"(38|48|58);2;(\d+);(\d+);(\d+)")
ANSI_STRIP = re.compile(r"\x1b\[[0-9;:?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")


def ansi_skeleton(ansi: str, colors: list[str]) -> str:
    """Replace truecolor SGR colours by `\\x01N\\x01` (index in the frame's colour list; new colours are appended)."""
    def sub(m: re.Match) -> str:
        c = "#%02x%02x%02x" % tuple(int(v) for v in m.group(2, 3, 4))
        if c not in colors:
            colors.append(c)
        return f"{m.group(1)};2;\x01{colors.index(c)}\x01"
    return SGR_RGB.sub(sub, ansi)


def plain_text(ansi: str) -> str:
    return "\n".join(line.rstrip() for line in ANSI_STRIP.sub("", ansi).split("\n")).rstrip("\n") + "\n"


def fill_colors(skel: str, colors_hex: list[str], ansi: bool) -> str:
    if ansi:
        return re.sub(r"\x01(\d+)\x01", lambda m: "%d;%d;%d" % tuple(int(colors_hex[int(m.group(1))][i:i + 2], 16) for i in (1, 3, 5)), skel)
    return re.sub(r'="@(\d+)"', lambda m: f'="{colors_hex[int(m.group(1))]}"', skel)


def ordered(values: list[str], key=None) -> list[str]:
    return sorted(dict.fromkeys(values), key=key)


def build(frames: list[Frame], themes: list[str] | None, title: str) -> tuple[str, dict, list[dict]]:
    pool: dict[str, int] = {}
    svgs: list[str] = []
    ansis: list[str] = []
    texts: list[str] = []
    recs = []
    exports = []
    syn, resolve = synthetic_theme(load_theme(DEFAULT_THEME))
    loaded: dict[str, object] = {}
    for f in frames:
        skel, colors = skeletonize(render_frame(f, syn))
        raw_ansi = render_mock_ansi(f.mock, syn, "truecolor") if f.mock else f.ansi
        askel = ansi_skeleton(raw_ansi, colors)
        h = hashlib.sha1((skel + "\0" + askel).encode()).hexdigest()
        if h not in pool:
            pool[h] = len(svgs)
            svgs.append(skel)
            ansis.append(askel)
            texts.append(plain_text(raw_ansi))
        for t in frame_themes(f, themes):
            theme = loaded.setdefault(t, load_theme(t))
            real = [resolve(c, theme).lower() for c in colors]
            recs.append({"d": f.design, "v": f.variant, "s": f.state, "z": f.size, "t": theme.id, "svg": pool[h],
                         "c": "".join(c[1:] for c in real), "cap": {"title": f.title, "lint": f.lint, "src": f.path.name}})
            exports.append({"rec": recs[-1], "svg": fill_colors(skel, real, False), "ansi": fill_colors(askel, real, True),
                            "txt": texts[pool[h]]})
    designs = ordered([f.design for f in frames], key=None)
    design_order = list(dict.fromkeys(f.design for f in frames))
    order = {
        "d": design_order,
        "v": ordered([r["v"] for r in recs]),
        "s": ordered([r["s"] for r in recs], key=lambda s: (STATE_ORDER.index(s) if s in STATE_ORDER else 99, s)),
        "z": ordered([r["z"] for r in recs], key=lambda z: tuple(int(v) for v in z.split("x"))),
        "t": list(dict.fromkeys(r["t"] for r in recs)),
    }
    data = {"title": title, "frames": recs, "order": order, "ansi": ansis, "text": texts}
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    tpl = "".join(f'<template id="s{i}">{svg}</template>\n' for i, svg in enumerate(svgs))
    page = (PAGE.replace("__TITLE__", escape(title)).replace("__DATA__", payload).replace("__TEMPLATES__", tpl))
    return page, {"frames": len(frames), "renders": len(recs), "unique_svgs": len(svgs), "designs": len(designs)}, exports


def export_files(exports: list[dict], out: Path, formats: list[str]) -> int:
    """Write every frame x theme as <design>/<variant>--<state>--<size>--<theme>.<ext>. Returns the number of files."""
    n = 0
    png_ok = True
    for e in exports:
        r = e["rec"]
        d = out / re.sub(r"[^\w.-]+", "_", r["d"])
        d.mkdir(parents=True, exist_ok=True)
        base = d / f'{r["v"]}--{r["s"]}--{r["z"]}--{r["t"]}'
        for fmt in formats:
            if fmt == "txt":
                base.with_suffix(".txt").write_text(e["txt"], encoding="utf-8")
            elif fmt == "ansi":
                base.with_suffix(".ansi").write_text(e["ansi"], encoding="utf-8")
            elif fmt == "svg":
                base.with_suffix(".svg").write_text(e["svg"], encoding="utf-8")
            elif fmt == "png":
                if not png_ok:
                    continue
                try:
                    base.with_suffix(".png").write_bytes(to_png(e["svg"], 2.0, False))
                except SystemExit as err:                # rsvg-convert missing: skip PNGs, keep the rest
                    print(f"gallery: PNG export skipped ({err})", file=sys.stderr)
                    png_ok = False
                    continue
            n += 1
    return n


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Directories of terminal frames -> one self-contained HTML gallery.",
                                 epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dirs", nargs="+", metavar="DIR", help="directory of <variant>--<state>--<cols>x<rows>.mock|.ansi frames")
    ap.add_argument("--themes", help="comma-separated theme ids, or 'all' (default: each mock's own theme / catppuccin-mocha)")
    ap.add_argument("--title", default="Terminal UI gallery", help="page title")
    ap.add_argument("-o", "--out", help="output HTML file (default gallery.html unless only --export is given)")
    ap.add_argument("--export", metavar="DIR", help="also write every frame x theme as files under DIR")
    ap.add_argument("--formats", default="txt,ansi,svg,png", help="formats for --export (default txt,ansi,svg,png)")
    a = ap.parse_args(argv)
    dirs = [Path(d) for d in a.dirs]
    for d in dirs:
        if not d.is_dir():
            print(f"gallery: not a directory: {d}", file=sys.stderr)
            return 2
    themes = None
    if a.themes:
        themes = list_themes() if a.themes == "all" else [t.strip() for t in a.themes.split(",") if t.strip()]
        for t in themes:
            try:
                load_theme(t)
            except (FileNotFoundError, ValueError, KeyError) as e:
                print(f"gallery: {e}", file=sys.stderr)
                return 2
    frames = discover(dirs)
    if not frames:
        print(f"gallery: no .mock/.ansi frames under {', '.join(map(str, dirs))}", file=sys.stderr)
        return 2
    for f in frames:
        load_frame(f)
    try:
        page, stats, exports = build(frames, themes, a.title)
    except (FileNotFoundError, ValueError, KeyError) as e:
        print(f"gallery: {e}", file=sys.stderr)
        return 2
    out = a.out or (None if a.export else "gallery.html")
    if out:
        Path(out).write_text(page, encoding="utf-8")
        print(f"gallery: {stats['frames']} frames in {stats['designs']} design(s), {stats['renders']} renders, "
              f"{stats['unique_svgs']} unique SVGs, {len(page.encode()) // 1024} KiB -> {out}")
    if a.export:
        formats = [x.strip() for x in a.formats.split(",") if x.strip()]
        bad = sorted(set(formats) - {"txt", "ansi", "svg", "png"})
        if bad:
            print(f"gallery: unknown export format(s): {', '.join(bad)} (use txt,ansi,svg,png)", file=sys.stderr)
            return 2
        n = export_files(exports, Path(a.export), formats)
        print(f"gallery: exported {n} file(s) ({','.join(formats)}) -> {a.export}")
    return 0


PAGE = r"""<meta charset="utf-8">
<title>__TITLE__</title>
<meta name="description" content="Self-contained gallery of rendered terminal UI frames">
<style>
:root{--bg:#f4f4f2;--panel:#ffffff;--ink:#1d1d1f;--muted:#5e5e66;--line:#d6d6d2;--accent:#2f5fd0;--stage:#e6e6e2;--chip:#ececE8;
  --err:#b3261e;--warn:#8a5a00;--ok:#1f6b3a;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#17171a;--panel:#212125;--ink:#ececf0;--muted:#a0a0aa;
  --line:#3a3a40;--accent:#8fb0ff;--stage:#101012;--chip:#2c2c32;--err:#ff8a80;--warn:#f0c060;--ok:#7fd49a;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#17171a;--panel:#212125;--ink:#ececf0;--muted:#a0a0aa;--line:#3a3a40;--accent:#8fb0ff;--stage:#101012;
  --chip:#2c2c32;--err:#ff8a80;--warn:#f0c060;--ok:#7fd49a;color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.4 system-ui,-apple-system,"Segoe UI",sans-serif;padding-inline:16px}
header{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:var(--bg);padding-block:12px 8px;border-bottom:1px solid var(--line)}
.heading{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;margin-bottom:8px}
h1{font-size:16px;margin:0;font-weight:650}
.bar{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:flex-end}
label{display:flex;flex-direction:column;font-size:11px;color:var(--muted);gap:2px;text-transform:uppercase;letter-spacing:.04em}
select,button{font:inherit;font-size:13px;color:var(--ink);background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:5px 8px;min-height:32px}
button{cursor:pointer}button[aria-pressed="true"]{border-color:var(--accent);outline:1px solid var(--accent)}
select:focus-visible,button:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
.hint{font-size:12px;color:var(--muted);margin:8px 0 0}.hint kbd{border:1px solid var(--line);border-bottom-width:2px;border-radius:4px;padding:0 4px;font:11px ui-monospace,Menlo,monospace;background:var(--panel)}
main{padding-block:14px 32px}
.panes{display:grid;gap:16px;grid-template-columns:1fr}
.panes.split{grid-template-columns:repeat(2,minmax(0,1fr))}
@media (max-width:760px){.panes.split{grid-template-columns:1fr}}
.pane{min-width:0}
.pane .sub{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px;align-items:flex-end}
.stage{background:var(--stage);border:1px solid var(--line);border-radius:10px;padding:14px;overflow:auto;display:flex;justify-content:center}
.stage svg{display:block;height:auto;flex:none}
.cap{margin-top:8px;font-size:13px}.cap .t{font-weight:600}.cap .m{color:var(--muted);font-size:12px;margin-top:2px;word-break:break-word}
.chip{display:inline-block;border-radius:999px;padding:0 8px;background:var(--chip);font-size:12px;margin-right:4px}
.chip.err{color:var(--err)}.chip.warn{color:var(--warn)}.chip.ok{color:var(--ok)}
.opt-off{color:var(--muted)}
.count{font-size:12px;color:var(--muted);align-self:center}
.ex{display:flex;flex-wrap:wrap;gap:6px;margin-left:auto;align-items:center;justify-content:flex-end}
.ex button{min-height:26px;font-size:12px;padding:2px 8px}
.ex .lbl{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
</style>
<header>
  <div class="heading"><h1 id="ttl"></h1><div class="ex" id="exports-a" role="group" aria-label="Export left frame"></div></div>
  <div class="bar" role="toolbar" aria-label="Frame selectors">
    <label>Design<select id="sel-d"></select></label>
    <label>Variant<select id="sel-v"></select></label>
    <label>State<select id="sel-s"></select></label>
    <label>Size<select id="sel-z"></select></label>
    <label>Theme<select id="sel-t"></select></label>
    <label>Scale<select id="sel-scale"><option value="fit">Fit</option><option value="1">1x</option><option value="1.5">1.5x</option><option value="2">2x</option></select></label>
    <button id="btn-split" aria-pressed="false" title="Show two variants side by side (s)">Side by side</button>
    <span class="count" id="count" aria-live="polite"></span>
    <span class="count" id="note" aria-live="polite"></span>
  </div>
  <p class="hint"><kbd>&larr;</kbd><kbd>&rarr;</kbd> variant &nbsp; <kbd>&uarr;</kbd><kbd>&darr;</kbd> state &nbsp; <kbd>t</kbd> theme &nbsp; <kbd>z</kbd> size &nbsp; <kbd>s</kbd> side by side &nbsp; <kbd>f</kbd> fit / 1x. Each frame exports as TXT, ANSI, SVG or PNG (downloads need this file opened locally; inside a published page use Copy). Options with a dot exist for this design but change another selector when chosen.</p>
</header>
<main><div class="panes" id="panes">
  <section class="pane" id="pane-a"><div class="stage" id="stage-a"></div><div class="cap" id="cap-a"></div></section>
  <section class="pane" id="pane-b" hidden>
    <div class="sub"><label>Variant<select id="sel-v2"></select></label><label>State<select id="sel-s2"></select></label><div class="ex" id="exports-b" role="group" aria-label="Export right frame"></div></div>
    <div class="stage" id="stage-b"></div><div class="cap" id="cap-b"></div></section>
</div></main>
<script type="application/json" id="data">__DATA__</script>
__TEMPLATES__
<script>
(function(){
"use strict";
var DATA=JSON.parse(document.getElementById("data").textContent), F=DATA.frames, ORD=DATA.order, ANSI=DATA.ansi||[], TEXT=DATA.text||[];
function hx(f,i){return f.c.substr(6*(+i),6);}
function svgOf(f){return document.getElementById("s"+f.svg).innerHTML.replace(/="@(\d+)"/g,function(m,i){return '="#'+hx(f,i)+'"';});}
function ansiOf(f){return (ANSI[f.svg]||"").replace(/\x01(\d+)\x01/g,function(m,i){var h=hx(f,i);return parseInt(h.substr(0,2),16)+";"+parseInt(h.substr(2,2),16)+";"+parseInt(h.substr(4,2),16);});}
function baseName(f){return (f.d+"--"+f.v+"--"+f.s+"--"+f.z+"--"+f.t).replace(/[^\w.-]+/g,"_");}
function note(t){document.getElementById("note").textContent=t;}
function dlBlob(name,blob){
  // application/octet-stream makes browsers save the file instead of opening the blob: URL in a tab
  // (Safari displays text/plain and image/svg blobs even with a download attribute); revoke late so slow saves finish.
  var b=blob.type==="application/octet-stream"?blob:new Blob([blob],{type:"application/octet-stream"});
  var u=URL.createObjectURL(b),a=document.createElement("a");a.href=u;a.download=name;a.rel="noopener";a.style.display="none";
  document.body.appendChild(a);a.click();setTimeout(function(){URL.revokeObjectURL(u);a.remove();},60000);
  note("Saved "+name+" (if nothing downloaded, this page is sandboxed: use Copy)");}
function dl(name,data,type){dlBlob(name,new Blob([data],{type:type}));}
function png(f){var img=new Image();img.onload=function(){var s=2,c=document.createElement("canvas");c.width=img.naturalWidth*s;c.height=img.naturalHeight*s;
  var x=c.getContext("2d");x.scale(s,s);x.drawImage(img,0,0);c.toBlob(function(b){if(b)dlBlob(baseName(f)+".png",b);else note("PNG export failed");},"image/png");};
  img.onerror=function(){note("PNG export failed");};img.src="data:image/svg+xml;charset=utf-8,"+encodeURIComponent(svgOf(f));}
function copy(text,label){var fallback=function(){var t=document.createElement("textarea");t.value=text;document.body.appendChild(t);t.select();var ok=false;
  try{ok=document.execCommand("copy");}catch(e){}t.remove();note(ok?label+" copied":"Copy is blocked here");};
  if(navigator.clipboard&&navigator.clipboard.writeText)navigator.clipboard.writeText(text).then(function(){note(label+" copied");},fallback);else fallback();}
function exportFrame(f,kind){if(kind==="txt")dl(baseName(f)+".txt",TEXT[f.svg]||"","text/plain;charset=utf-8");
  else if(kind==="ansi")dl(baseName(f)+".ansi",ansiOf(f),"text/plain;charset=utf-8");
  else if(kind==="svg")dl(baseName(f)+".svg",svgOf(f),"image/svg+xml");
  else if(kind==="png")png(f);
  else if(kind==="copy-txt")copy(TEXT[f.svg]||"","Text");
  else if(kind==="copy-ansi")copy(ansiOf(f),"ANSI");}
var DIMS=["d","v","s","z","t"], LABEL={d:"Design",v:"Variant",s:"State",z:"Size",t:"Theme"};
var KEEP={d:16,t:8,z:4,s:2,v:1};           // when snapping, which selections matter most
var cur=pick(F[0]), split=false, right={v:null,s:null}, scale="fit";
var preferredSize=cur.z;                   // only an explicit size choice replaces this
document.getElementById("ttl").textContent=DATA.title;
function pick(f){return {d:f.d,v:f.v,s:f.s,z:f.z,t:f.t};}
function matches(f,sel,skip){for(var i=0;i<DIMS.length;i++){var k=DIMS[i];if(k!==skip&&sel[k]!==undefined&&sel[k]!==null&&f[k]!==sel[k])return false;}return true;}
function exact(sel){for(var i=0;i<F.length;i++)if(matches(F[i],sel))return F[i];return null;}
function snap(sel,dim,val){                 // closest existing frame with sel[dim]=val
  var best=null,bs=-1;
  for(var i=0;i<F.length;i++){var f=F[i];if(f[dim]!==val)continue;if(dim!=="d"&&f.d!==sel.d)continue;
    if(dim!=="d"&&dim!=="v"&&f.v!==sel.v)continue;
    var sc=0;for(var j=0;j<DIMS.length;j++){var k=DIMS[j];if(k!==dim&&f[k]===sel[k])sc+=KEEP[k];}
    if(sc>bs){bs=sc;best=f;}}
  return best?pick(best):sel;}
function values(dim,sel){                   // states, sizes and themes stay within the current variant
  var seen={};F.forEach(function(f){if((f.d===sel.d||dim==="d")&&
    (dim==="d"||dim==="v"||f.v===sel.v))seen[f[dim]]=1;});
  return ORD[dim].filter(function(v){return seen[v];});}
function choose(dim,val){
  var want=Object.assign({},cur,{z:preferredSize}),next=snap(want,dim,val);
  if(exact(next)){cur=next;if(dim==="z")preferredSize=val;}
  render();}
function fill(el,dim,sel){
  var vals=values(dim,sel),probe=Object.assign({},sel);
  el.innerHTML="";
  vals.forEach(function(v){probe[dim]=v;var ok=dim==="d"||!!exact(probe),o=document.createElement("option");
    o.value=v;o.textContent=ok?v:v+" ·";if(!ok)o.className="opt-off";o.selected=v===sel[dim];el.appendChild(o);});
  el.disabled=vals.length<2;}
function chip(cls,txt){return '<span class="chip '+cls+'">'+txt+'</span>';}
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}
function show(f,stage,cap,note){
  var tpl=document.getElementById("s"+f.svg),box=document.createElement("div");
  box.innerHTML=tpl.innerHTML.replace(/="@(\d+)"/g,function(m,i){return '="#'+f.c.substr(6*(+i),6)+'"';});
  var svg=box.firstElementChild;
  var w=parseFloat(svg.getAttribute("width"))||800;
  svg.removeAttribute("height");
  svg.style.width=scale==="fit"?"100%":(w*parseFloat(scale))+"px";
  svg.style.maxWidth=scale==="fit"?(w*1.5)+"px":"none";
  stage.innerHTML="";stage.appendChild(svg);
  var c=f.cap,l=c.lint||{},h="";
  h+='<div class="t">'+esc(c.title||f.v+" / "+f.s)+'</div><div class="m">';
  h+=esc(f.d+" / "+f.v+" / "+f.s+" / "+f.z+" · "+f.t+" · "+c.src)+(note?" · "+esc(note):"")+'</div><div class="m">';
  if("errors" in l){h+=chip(l.errors?"err":"ok",l.errors+" error"+(l.errors===1?"":"s"))+chip(l.warnings?"warn":"ok",l.warnings+" warning"+(l.warnings===1?"":"s"))+chip("",l.info+" info")+" lint (render_mockup --check)";}
  else h+=chip("","ANSI frame")+" no lint";
  h+='</div>';cap.innerHTML=h;
  var ex=document.getElementById(stage.id==="stage-a"?"exports-a":"exports-b");
  ex.innerHTML='<span class="lbl">Export</span><button type="button" data-x="txt">TXT</button><button type="button" data-x="ansi">ANSI</button>'
    +'<button type="button" data-x="svg">SVG</button><button type="button" data-x="png">PNG</button>'
    +'<button type="button" data-x="copy-txt">Copy text</button><button type="button" data-x="copy-ansi">Copy ANSI</button>';
  ex.__frame=f;}
function render(){
  var a=exact(cur)||F[0];cur=pick(a);
  ["d","v","s","z","t"].forEach(function(k){fill(document.getElementById("sel-"+k),k,cur);});
  show(a,document.getElementById("stage-a"),document.getElementById("cap-a"),"");
  document.getElementById("pane-b").hidden=!split;
  document.getElementById("panes").className="panes"+(split?" split":"");
  document.getElementById("btn-split").setAttribute("aria-pressed",split?"true":"false");
  if(split){
    var vs=values("v",cur);
    if(!right.v||vs.indexOf(right.v)<0)right.v=vs[(vs.indexOf(cur.v)+1)%vs.length];
    var ss=values("s",Object.assign({},cur,{v:right.v}));
    if(!right.s||ss.indexOf(right.s)<0)right.s=ss.indexOf(cur.s)>=0?cur.s:ss[0];
    var want={d:cur.d,v:right.v,s:right.s,z:cur.z,t:cur.t},b=exact(want),note="";
    if(!b){var p=snap(want,"v",right.v);b=exact(p)||a;note="closest match: "+DIMS.filter(function(k){return p[k]!==want[k];}).map(function(k){return LABEL[k].toLowerCase()+" "+p[k];}).join(", ");}
    var s2=document.getElementById("sel-s2"),v2=document.getElementById("sel-v2");
    v2.innerHTML="";vs.forEach(function(v){var o=document.createElement("option");o.value=v;o.textContent=v;o.selected=v===right.v;v2.appendChild(o);});
    s2.innerHTML="";ss.forEach(function(v){var o=document.createElement("option");o.value=v;o.textContent=v;o.selected=v===right.s;s2.appendChild(o);});
    show(b,document.getElementById("stage-b"),document.getElementById("cap-b"),note);}
  document.getElementById("count").textContent=F.filter(function(f){return f.d===cur.d&&f.t===cur.t;}).length+" frames in "+cur.d;}
DIMS.forEach(function(k){document.getElementById("sel-"+k).addEventListener("change",function(e){
  choose(k,e.target.value);e.target.blur();});});
document.getElementById("sel-scale").addEventListener("change",function(e){scale=e.target.value;render();});
document.getElementById("sel-v2").addEventListener("change",function(e){right.v=e.target.value;render();});
document.getElementById("sel-s2").addEventListener("change",function(e){right.s=e.target.value;render();});
document.getElementById("btn-split").addEventListener("click",function(){split=!split;render();});
document.addEventListener("click",function(e){var b=e.target.closest&&e.target.closest("button[data-x]");if(!b)return;
  var ex=b.closest(".ex");if(ex&&ex.__frame)exportFrame(ex.__frame,b.getAttribute("data-x"));});
function step(dim,delta){var vs=values(dim,cur),i=vs.indexOf(cur[dim]);if(vs.length<2)return;
  choose(dim,vs[(i+delta+vs.length)%vs.length]);}
document.addEventListener("keydown",function(e){
  if(e.altKey||e.ctrlKey||e.metaKey)return;var tg=e.target&&e.target.tagName;if(tg==="INPUT"||tg==="TEXTAREA")return;
  var k=e.key,used=true;
  if(k==="ArrowRight")step("v",1);else if(k==="ArrowLeft")step("v",-1);
  else if(k==="ArrowDown")step("s",1);else if(k==="ArrowUp")step("s",-1);
  else if(k==="t")step("t",e.shiftKey?-1:1);else if(k==="T")step("t",-1);
  else if(k==="z")step("z",1);else if(k==="s"){split=!split;render();}
  else if(k==="f"){scale=scale==="fit"?"1":"fit";document.getElementById("sel-scale").value=scale;render();}
  else used=false;
  if(used){e.preventDefault();if(tg==="SELECT")e.target.blur();}});
render();
})();
</script>
"""

if __name__ == "__main__":
    sys.exit(main())
