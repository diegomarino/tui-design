# mockkit: building mockups in Python

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [Quick start](#quick-start) · L14–32 — your first frame end to end: canvas, layout, panel, table, footer, save, render.
- [Which helper](#which-helper) · L34–62 — which helper for which need, one row each.
- [Recipes](#recipes) · L64–161 — a screen function per archetype (B, A, I, F, J, G) to start from.
- [States × sizes in one call](#states--sizes-in-one-call) · L163–183 — `matrix()` for every state × size, with render and gallery.
- [Pitfalls (from real runs)](#pitfalls-from-real-runs) · L185–194 — before the first save, or when lint fails.

Read this when you build `.mock` frames with `SKILL_DIR/scripts/mockkit.py`. The `.mock` format itself is in [formats.md](formats.md#mockup-format). Do not read `mockkit.py`: every public name and its exact signature is in [mockkit-api.md](mockkit-api.md) (one section per group of names; table semantics and caps behaviour are there too).

The canvas is strict: off-canvas writes, text over a border, unknown tokens, raw hex, wide glyphs and caps violations raise `CanvasError`. The message names the cell, the box that owns it and a fix. `save()` lints with the same linter as `render_mockup.py --check`.

## Quick start

```python
import sys; sys.path.insert(0, "SKILL_DIR/scripts")
from mockkit import Canvas, Col
c = Canvas(80, 24, title="Fleet — services", state="normal", theme="catppuccin-mocha", caps="attrs=bold,dim colors=16 source=test-card")
_, body, msg, keys = c.rect.split_v([1, "*", 1, 1])            # header, body, message line, keybar
c.band(0, [(" Fleet ", "accent.primary bold")], [("prod-eu · 12:04 ", "statusbar.fg")], pad=0, region="header")
lst = c.panel(body, "Services (2)", role="list", focus=True)  # box + region + focus -> interior Rect
c.table(lst, columns=[Col("", 1), Col("NAME"), Col("AGE", 4, "r", spec="fg.muted")], selected=0, cursor="❯",
        rows=[[c.status("running"), "api-gateway", "6d"], [c.status("warn"), "billing", "2h"]])
c.message(msg.y, "ok", "deployed api-gateway v2.4.1", "2m ago")
c.keybar(keys.y, [("↑↓", "select"), ("enter", "open")], region="keybar")
c.save("out/fleet--normal--80x24.mock")                        # raises CanvasError with the cell on lint errors
```

`save()` prints `mockkit: saved fleet--normal--80x24.mock · 0 errors · 0 warnings → out` plus one line per warning (`verbose=True` or `MOCKKIT_VERBOSE=1`: every finding). Do not print `c.plain()` or each path from your generator: the summary is the check, the PNG is the look.

Then render it and look at it: `render_mockup.py F.mock -o f.ansi`, then `uv run ansi_render.py f.ansi --format png -o f.png`, then Read the PNG. `matrix(..., png=True)` does this for every frame.

## Which helper

Signatures: [mockkit-api.md](mockkit-api.md). The helpers draw through the low-level API (`text runs rtext rruns fill clear box hline vline region note focus selected save`).

| Need | Call | Notes |
|---|---|---|
| Layout that adapts to size | `c.rect.split_v([1, "*", 1, 1])`, `r.split_h([32, "*"], gap=1)`, `r.inset(l, t, r, b)`, `r.inner`, `r.take(n, "top")`, `r.center(w, h)`, `r.row(i)` | sizes: int = cells, float < 1 = share, `"*"` / `"2*"` = flex weight. `split_h` = side by side. `size_class(cols)` gives tiny/narrow/compact/regular/wide (layout-archetypes §2.1). |
| Titled pane | `inner = c.panel(rect, "Title", role="list", focus=True, title_right=…, bottom_right=…)` | records `#! region` (and `#! focus`); returns the interior with `.rid` |
| Header / status line | `c.band(y, left_runs, right_runs, bg="statusbar.bg", pad=1, region="header")` | `bg=None` for a plain line; raises when left and right collide |
| Tabs | `c.tabs(x, y, ["Services", ("Logs", 3)], active=0)` or `tab_runs(...)` inside a band | numbered ` 1 Services `; badges after the label |
| Footer hints | `c.keybar(y, [(k, verb), (k, verb, "off")], right=[("?", "help"), ("q", "quit")], region="keybar")` | `x=, w=, bg=None` puts it inside a panel or modal; `overflow="drop"` drops hints from the end |
| Message line | `c.message(y, "ok", "deployed v2", "2m ago")` | V5 status glyph + text + faint meta |
| Table | `c.table(where, columns=[Col(name, width, align, truncate, spec, sel, hide_below, ascii_width)], rows=…, selected=i, cursor="❯")` | [table semantics](mockkit-api.md#canvas-table-listing-tree); returns `.cols .y .shown .rows_y .range` |
| List | `c.listing(where, items=[...], selected=i)` | one-column table with the `❯` cursor |
| Tree | `c.tree(where, nodes=[("src", ["a.py", ("lib", [...])])], indent=4, folds=True)` | guides `├── └── │`; `tree_rows()` gives the flat rows |
| Field list | `c.kv(x, y, [("Status", runs), None, ("Version", "v2")], key_w=10)` | `None` = blank row; returns the next y |
| Lines of text | `c.lines(x, y, ["text", ("muted", "fg.muted")])` | each line clipped with `⋯` before the next border |
| Status | `c.status("warn")` gives `("▲", "status.warning")`; `c.g("cursor")` gives `❯` | V5 glyphs; V9 ASCII under `glyphs=ascii` |
| Chip | `c.chip(x, y, "STALE 42s", "status.warning")` or `chip(text, token)` as a run | `fg.on-accent` on the fill |
| Gauge | `c.gauge(x, y, w, 0.68, label_w=5, ramp=("ramp.low", "ramp.mid", "ramp.high"), smooth=True)` | fill = floor(value × bar), number always printed |
| Sparkline | `spark(values)` | `▁▂▃▄▅▆▇█`, `ascii=True` for `_.,-~=+#` |
| Scroll position | `scroll_range(off, visible, total)` gives `1-15/175`; `scroll_pos(i, total)` gives `12/90`; `c.scrollbar(x, y, h, off, visible, total)` | on a box side only the thumb replaces the border |
| Truncate | `truncate(s, w, "end/start/middle")`, `fit(s, w, align="l/r/c", side=…)`, `c.text(..., clip=True)` | ellipsis `⋯` (`...` in ASCII); paths `start`, ids `middle` |
| Folding repeats | `fold_runs(events, key=…)` gives `[(item, n)]`; `times(label, n)` gives `label ×n` | |
| Modal | `inner = c.overlay(48, 9, "Delete run?", hints=[("y", "delete"), ("esc", "cancel")])` | fades the base, clears, focuses; `c.center(inner, lines=[...])` |
| Too-small screen | `c.toosmall((80, 24), app="Fleet")` | layout-archetypes §2.2 wording, `q quit` |
| States × sizes | `matrix(build, "fleet", out_dir, states=…, sizes=…, extra=[("toosmall", (60, 18))])` | see the matrix section |

**Caps.** Under `Canvas(caps=…)` helpers drop the attributes and glyphs the profile forbids; what you pass yourself still raises; `fallback=True` degrades everything instead ([details](mockkit-api.md#canvas-constructor-properties-caps)).

## Recipes

Each recipe is a screen function `screen(c, state)` that works at 80x24 and 120x30. Pass it to `matrix()`.

**List + detail (B)**: list fixed, detail flex; at 60 columns only the focused list.

```python
def screen(c, state):
    _, body, msg, keys = c.rect.split_v([1, "*", 1, 1])
    c.band(0, [(" Fleet ", "accent.primary bold")], [("prod-eu ", "statusbar.fg")], pad=0, region="header")
    panes = body.split_h([32, "*"]) if c.cols >= 80 else [body]
    lst = c.panel(panes[0], "Services (3)", role="list", focus=True)
    data = [] if state == "empty" else [("running", "api-gateway"), ("warn", "billing"), ("fail", "search")]
    c.table(lst, header=False, selected=0 if data else None, cursor="❯", columns=[Col("", 1), Col("")],
            rows=[[c.status(s), n] for s, n in data])
    if not data:
        c.lines(lst.x + 1, lst.y + 1, ["No services in prod-eu.", ("Press n to create one.", "fg.muted")])
    if len(panes) > 1:
        det = c.panel(panes[1], "api-gateway", role="detail").inset(1, 1, 1, 0)
        c.kv(det.x, det.y, [("Status", [c.status("running"), (" running", "status.success")]), ("Version", "v2.4.1")])
    c.message(msg.y, "ok", "deployed api-gateway", "2m ago")
    c.keybar(keys.y, [("↑↓", "select"), ("enter", "open")] + ([] if len(panes) > 1 else [("esc", "back")]),
             region="keybar", overflow="drop")
```

**Dashboard (A)**: grid of read-only boxes plus one focusable table; gauges always print the number.

```python
def screen(c, state):
    top, procs, msg, keys = c.rect.split_v([7, "*", 1, 1])
    cpu, mem = top.split_h(["*", "*"])
    for r, title, v in ((cpu, "1 cpu", .64), (mem, "2 mem", .31)):
        inner = c.panel(r, title, role="chart", title_right=spark([3, 5, 2, 8, 13, 9, 21]))
        c.gauge(inner.x + 1, inner.y + 1, inner.w - 2, v, ramp=("ramp.low", "ramp.mid", "ramp.high"))
    t = c.panel(procs, "4 proc", role="table", focus=True, bottom_right=scroll_pos(0, 412))
    c.table(t, selected=0, stale=state == "error", columns=[Col("PID", 6, "r"), Col("NAME"), Col("CPU%", 5, "r"),
            Col("USER", 8, hide_below=90)], rows=[[412, "postgres", "12.0", "pg"], [77, "nginx", "3.1", "www"]])
    if state == "error":                         # degraded: stale chip + reason, values faint, unsafe verb off
        c.text(c.chip(1, msg.y, "STALE 42s"), msg.y, " sampler unreachable · retry in 5s", "fg.muted")
    c.keybar(keys.y, [("↑↓", "select"), ("/", "filter"), ("k", "kill", "off" if state == "error" else None)],
             region="keybar")
```

**Table explorer (I)**: header row, right-aligned numbers, zebra on wide tables, a scrollbar, responsive columns.

```python
def screen(c, state):
    body, keys = c.rect.split_v(["*", 1])
    rows = [[f"evt-{i:03}", "deploy" if i % 3 else "scale", f"{i * 7 % 90}s"] for i in range(90)]
    t = c.panel(body, "Events", role="table", focus=True, title_right="by ID ↑")
    info = c.table(t.inset(0, 0, 1, 0), columns=[Col("ID", 8, truncate="middle"), Col("KIND"),
                   Col("AGE", 5, "r", spec="fg.muted")], rows=rows, offset=10, selected=12, cursor="❯", zebra=True)
    c.scrollbar(t.right, t.y, t.h, 10, info.shown, len(rows))     # on the box's right side
    c.keybar(keys.y, [("↑↓", "move"), ("s", "sort"), ("/", "filter")], region="keybar")
```

**Form (F)**: labels in a fixed column, inputs on `bg.raised`, the focused field with a cursor cell.

```python
def screen(c, state):
    body, keys = c.rect.split_v(["*", 1])
    f = c.panel(body.center(60, 10), "New service", role="form", focus=True).inset(1, 1)
    for i, (label, value, focused) in enumerate((("Name", "billing", True), ("Port", "8080", False))):
        c.text(f.x, f.y + i * 2, label, "fg.muted")
        c.fill(f.x + 8, f.y + i * 2, 30, 1, "bg.raised")
        end = c.text(f.x + 9, f.y + i * 2, value, "fg.default")
        if focused:
            c.text(end, f.y + i * 2, " ", "on:cursor.bg")
    c.runs(f.x + 8, f.y + 4, [(c.g("check_on"), "accent.primary"), (" start after create", "fg.default")])
    if state == "error":
        c.message(f.y + 5, "fail", "port 8080 is already in use", x=f.x, w=f.w)
    c.keybar(keys.y, [("tab", "next field"), ("enter", "create"), ("esc", "cancel")], region="keybar")
```

**Inline picker (J)**: a short canvas (the drawn area only), prompt row and a bounded list; matches highlighted.

```python
def screen(c, state):                       # use with sizes=((80, 8),)
    prompt, lst, hint = c.rect.split_v([1, "*", 1])
    c.runs(0, prompt.y, [("> ", "accent.primary bold"), ("fea", "fg.default"), (" ", "on:cursor.bg"),
                         ("  3/41", "fg.faint")])
    items = [[("fea", "search.match bold"), "ture/login"], [("fea", "search.match bold"), "t/cache"],
             ["release/", ("fea", "search.match bold"), "ture-x"]]
    c.listing(lst, items=items, selected=0, region=None)
    c.keybar(hint.y, [("enter", "checkout"), ("esc", "cancel")], right=(), bg=None)
```

**Modal (G)**: draw the base screen, then the overlay; it fades the base and carries its own hints.

```python
def screen(c, state):
    body, keys = c.rect.split_v(["*", 1])
    lst = c.panel(body, "Runs", role="list", focus=True)
    c.listing(lst, items=["#1842 api", "#1841 web"], selected=0)
    c.keybar(keys.y, [("enter", "open"), ("d", "delete")])
    m = c.overlay(min(46, c.cols - 4), 8, "Delete run #1842?", hints=[("y", "delete"), ("esc", "cancel")])
    c.center(m, lines=["Logs and artifacts are removed.", ("This cannot be undone.", "status.warning")])
```

## States × sizes in one call

```python
from mockkit import matrix
def build(c, state):
    if state == "toosmall":
        return c.toosmall((80, 24), app="Fleet")
    screen(c, state)                              # one function, every state and size
paths = matrix(build, "fleet", "design/frames", states=("normal", "empty", "busy", "error"),
               sizes=((80, 24), (120, 30)), extra=[("toosmall", (60, 18)), ("normal", (60, 24))],
               theme="catppuccin-mocha", caps="attrs=bold,dim", png=True, gallery="design/gallery.html")
```

Each combo gets a fresh `Canvas(cols, rows, title, state, theme, caps)` and is saved linted as `<variant>--<state>--<cols>x<rows>.mock`. `frame_name()` rejects names that `gallery.py` and `compare.py` would not parse. Every frame is attempted, and failures are reported together, each prefixed with its frame name. `skip=lambda state, cols, rows: …` leaves out combos, and `title=` takes a string or `fn(state, cols, rows)`. `render=True` writes `.ansi` and `png=True` writes `.png` (needs `rsvg-convert`). Read the PNGs afterwards.

Output: one line for the set, then one line per distinct warning (shared ones once, with the count); errors raise with every failing frame in full:

```text
mockkit: saved 10 frames · 0 errors · 4 warnings → design/frames (+.ansi+.png) · gallery design/gallery.html
  WARN: craft CR1: bracket chip '[ api ]' (…) — 4 frames: fleet--normal--80x24.mock, fleet--normal--120x30.mock +2 more
```

## Pitfalls (from real runs)

- **Coordinate arithmetic.** Derive every pane from `c.rect` with `split_v` / `split_h` / `inset` and read `inner.x`, `.right`, `.bottom`. Hard-coded `x0 + w - 10` breaks at the next size.
- **Text over a border.** Draw content inside `panel()`'s interior. Join a separator to a box side with `hline(..., ends=("├", "┤"))` instead of `force=True`, which also bypasses the checks that matter.
- **Overflow.** Fit table cells by their `Col` width. Use `clip=True` or `lines()` for free text. Paths truncate at the start, ids in the middle.
- **Zebra.** Anchor parity to the data, not to the screen row: use `zebra="newest-first"` for live feeds. Keep stripes that the app already has (Z8), and skip them on short lists (Z2).
- **Selection state.** One `#! selected` per frame. An inactive selection in an unfocused pane is drawn but not recorded.
- **ASCII caps.** `[ok]` takes 4 cells, so give status columns `Col(..., 1, ascii_width=4)`.
- **Dashes.** Em dash `—` and `×` are INFO-level ambiguous glyphs; fine in copy. Wide glyphs (CJK, emoji) are errors, and the lint message gives their cell.
- **Commentary.** Assumptions go in `c.note(...)`, never in UI text.
