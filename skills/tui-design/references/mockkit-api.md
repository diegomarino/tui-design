# mockkit API reference

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [Canvas: constructor, properties, caps](#canvas-constructor-properties-caps) · L22–33 — the `Canvas(...)` constructor, `.rect`, `.size_class`, `.is_ascii`, `g`, `status`, `adapt`, `ascii`, and how caps change what helpers draw.
- [Canvas: writing cells](#canvas-writing-cells) · L35–45 — `text`, `runs`, `rtext`, `rruns`, `fill`, `clear`, `hline`, `vline`, `box`.
- [Canvas: header records](#canvas-header-records) · L47–53 — `region`, `focus`, `selected`, `selected_at`, `note` (the `#! …` lines audits read).
- [Canvas: panes, bars and fields](#canvas-panes-bars-and-fields) · L55–66 — `panel`, `band`, `tabs`, `message`, `chip`, `kv`, `lines`, `gauge`, `scrollbar`, `keybar`.
- [Canvas: table, listing, tree](#canvas-table-listing-tree) · L68–74 — `table`, `listing`, `tree`, and the table semantics (offset, selection, zebra, stale, skeleton).
- [Canvas: overlays and the too-small screen](#canvas-overlays-and-the-too-small-screen) · L76–81 — `fade`, `overlay`, `center`, `toosmall`.
- [Canvas: output and lint](#canvas-output-and-lint) · L83–88 — `to_mock`, `plain`, `lint`, `save`.
- [Rect and layout](#rect-and-layout) · L90–103 — `Rect` and its `inset`, `inner`, `split_h`, `split_v`, `take`, `center`, `row`; `layout()`, `size_class()`.
- [Col, Node, CanvasError](#col-node-canvaserror) · L105–109 — table columns, tree nodes, the error every bad write raises.
- [Text and number helpers](#text-and-number-helpers) · L111–121 — `width`, `fit`, `truncate`, `bar`, `spark`, `fold_runs`, `times`, `scroll_range`, `scroll_pos`.
- [Run builders](#run-builders) · L123–128 — `chip`, `hint_runs`, `tab_runs`, `tree_rows`: runs for `runs()` and `band()`.
- [matrix and frame_name](#matrix-and-frame_name) · L130–133 — every state × size in one call; the frame file name.
- [STATUS and GLYPHS](#status-and-glyphs) · L135–138 — the status roles and chrome glyph roles `status()` and `g()` accept.

Read this when you need the exact signature of a `mockkit.py` class, method or helper; do not read `mockkit.py` itself. What mockkit is, the helper map, recipes and `matrix()` are in [mockkit.md](mockkit.md). `help(mockkit.Canvas.table)`, run from `SKILL_DIR/scripts`, prints one full docstring.

Signatures as in `scripts/mockkit.py` (its `__all__`), one line of purpose each. A name with a leading dot is a method of the class its section is about (`c.` for a Canvas, `r.` for a Rect). A `*where` argument is a `Rect`, an `(x, y, w, h)` tuple or four ints; runs are `[(text, spec), …]`; a spec is `"token attr… on:bg-token"`.

## Canvas: constructor, properties, caps

- `Canvas(cols, rows, title=None, state=None, theme=None, caps=None, fallback=False)` — The frame: a cols × rows grid of cells with a strict writer and the `#! …` header lines; every helper is a method.
- `.rect` (property) — The whole canvas as a Rect, the root of split_h / split_v layouts.
- `.size_class` (property) — Size class of the canvas width (see `size_class()`).
- `.is_ascii` (property) — True under caps glyphs=ascii (helpers then draw V9 ASCII glyphs).
- `.g(role) -> str` — The glyph for a chrome or status role under the caps profile: g("cursor") -> ❯ or >, g("ok") -> ✓ or [ok].
- `.status(role) -> tuple` — (glyph, token) of a V5 status role under the caps profile: status("warn") -> ("▲", "status.warning").
- `.adapt(spec) -> str | None` — Drop the attributes of `spec` that the caps profile does not allow (what helpers do to their defaults).
- `.ascii(s) -> str` — Replace glyphs by their V9 ASCII fallback and accented letters by base letters.

**Caps.** `Canvas(caps="attrs=bold,dim glyphs=ascii")` writes `#! caps:`. Helpers drop the attributes they add by default (title bold, key bold, cursor bold) and draw their own glyphs from V9 ASCII (`>`, `...`, `|--`, `#`, `+-+` borders). An attribute or glyph you pass yourself still raises, so violations stay visible. `fallback=True` degrades everything instead (glyphs to V9, accents to base letters, boxes to ascii, forbidden attributes dropped). Use it to derive a host-limited variant of a finished design, not while designing for that host.

## Canvas: writing cells

- `.text(x, y, s, spec=None, force=False, clip=False) -> int` — Write one line of text starting at (x, y); returns the x after the last cell written.
- `.runs(x, y, parts, force=False) -> int` — Write [(text, spec), ...] one after another; returns the end x.
- `.rtext(x_end, y, s, spec=None, force=False) -> int` — Right-aligned: the text ends just before column x_end (exclusive). Returns its start x.
- `.rruns(x_end, y, parts, force=False) -> int` — Right-aligned runs ending just before x_end (exclusive). Returns their start x.
- `.fill(x, y, w, h, spec) -> None` — Set the background of a rectangle ('on:statusbar.bg' or a bare bg token); glyphs are kept.
- `.clear(x, y, w, h, bg=None) -> None` — Reset a rectangle to blank cells (optionally on a fill) and drop its border protection.
- `.hline(x, y, w, spec='border.default', ch='─', ends=None, force=False) -> None` — Horizontal rule of w cells; ends=("├", "┤") replaces the first/last glyph (joins to a box side).
- `.vline(x, y, h, spec='border.default', ch='│', ends=None, force=False) -> None` — Vertical rule of h cells; ends=("┬", "┴") replaces the first/last glyph.
- `.box(x, y, w, h, title=None, border='rounded', spec='border.default', title_spec='fg.title bold', region=None, title_right=None, bottom=None, bottom_right=None, fill=None, clear=False, force=False) -> None` — Bordered box (w × h includes the border); titles sit between ─ segments. Prefer `panel()`, which also records the region.

## Canvas: header records

- `.region(rid, role, x, y, w, h, title=None) -> None` — Record `#! region rid role x,y,w,h [title]` (ground truth for audits).
- `.focus(rid) -> None` — Record the focused pane (`#! focus <rid>`), the ground truth audits score state against.
- `.selected(rid, row) -> None` — Record the selected row (`#! selected <rid> <row>`), 0-based inside the region's interior.
- `.selected_at(rid, y) -> None` — Record the selected row from its canvas row y (interior of a box region starts below its border).
- `.note(text) -> None` — Add a `#! note:` header line (free text, one line).

## Canvas: panes, bars and fields

- `.panel(*where, title=None, role='panel', focus=False, rid=None, border='rounded', spec=None, **box_kw) -> Rect` — Titled box that records `#! region` (and `#! focus`); returns the interior Rect (with `.rid`). Call as `panel(rect, "Title", …)`; other `box()` keywords pass through.
- `.band(y, left=(), right=(), *, bg='statusbar.bg', x=0, w=None, pad=1, region=None, min_gap=1) -> tuple[int, int]` — 1-row header or status line: `left` runs from x+pad, `right` runs ending at x+w−pad, on `bg` (None = no fill); raises when they collide. Returns (end of left, start of right).
- `.tabs(x, y, items, active=0, numbered=True) -> int` — Tab bar ` 1 Services ` at (x, y); items are labels or (label, badge[, badge_spec]). Returns the end x.
- `.message(y, status, text, meta=None, x=1, w=None, spec='fg.default') -> int` — Message line `✓ deployed v2.4.1 · 2m ago`: V5 status role (or None) + text + faint meta. Returns the end x.
- `.chip(x, y, text, token='status.warning') -> int` — ' WARN ' in fg.on-accent on the `token` fill (16 colors: slot + reverse). Returns the end x.
- `.kv(x, y, pairs, key_w=None, w=None, key_spec='fg.muted', val_spec='fg.default') -> int` — Field list: keys in a fixed-width column, values after it; None = blank row. Returns the next y.
- `.lines(x, y, items, spec='fg.default', w=None) -> int` — One item per row from (x, y), each clipped with ⋯ to w cells (default: up to the next border); "" or None = blank row. Returns the next y.
- `.gauge(x, y, w, value, label='pct', label_w=5, ramp=None, thresholds=(0.5, 0.8), track='fg.faint', label_spec='fg.default', style='block', smooth=False) -> int` — Bar + right-aligned number in w cells; fill = floor(value × bar width), colour from the ramp by thresholds; style block|line|meter. Returns the end x.
- `.scrollbar(x, y, h, offset, visible, total, always=False) -> bool` — Vertical scrollbar (thumb █ on a │ track); returns False and draws nothing when everything fits, unless always=True. On a box side only the thumb replaces the border.
- `.keybar(y, left, right=(('?', 'help'), ('q', 'quit')), bg='statusbar.bg', x=0, w=None, region=None, overflow='raise') -> None` — Footer hints: context `left`, global `right`; (key, verb, "off") = disabled; x/w (bg=None) put it inside a panel; overflow="drop" drops hints from the end instead of raising.

## Canvas: table, listing, tree

- `.table(*where, columns, rows, header=True, selected=None, offset=0, total=None, cursor=None, zebra=False, zebra_phase=1, row_spec=None, gap=1, pad=1, inactive=False, stale=False, header_spec='table.header bold', stripe='bg.stripe', skeleton=0, region=None)` — Columns of cells in `where` (usually a panel interior), widths from `Col`, each cell truncated and aligned; semantics in "Table semantics" below. Returns info with `.cols .y .shown .rows_y .range`.
- `.listing(*where, items, selected=None, cursor='❯', spec='fg.default', sel='selection.fg bold', truncate='end', **kw)` — One-column list with the cursor and selection band; other keywords as `table()`.
- `.tree(*where, nodes, selected=None, indent=4, folds=False, guide_spec='fg.faint', cursor=None, **kw)` — Tree as a listing with guides `├── └── │` and optional ▾/▸ folds; nodes are labels, (label, [children][, open]) or `Node`; selected indexes the flattened rows.

**Table semantics.** `rows` is the data list, of which `rows[offset:]` is shown; `total` (default `len(rows)`) feeds `info.range`. A cell is `str`, `(str, spec)` or a list of runs. Neutral styles (`fg.default/muted/faint`) come from `Col.spec`. On the selected row a full-width `selection.bg` band is drawn, neutral text switches to `Col.sel` (default `selection.fg`), and semantic colors (`status.*`) stay. `inactive=True` (focus is elsewhere) uses `selection.inactive.bg` with no cursor and no `#! selected`. `zebra=True` stripes by data index, `zebra="newest-first"` counts from the oldest record so new rows never flip stripes, and a function `fn(i, row)` decides itself. Stripes appear where `key % 2 == zebra_phase`, use `bg.stripe` and lose to the selection (rules Z1–Z8 in layout-archetypes §2.4). `row_spec=fn(i, row)` restyles a whole row (e.g. `fg.faint` for stopped). `stale=True` makes every value faint (degraded). `skeleton=N` draws N `░` placeholder rows (busy). `Col(hide_below=100)` drops a column when the table is narrower than 100 cells.

## Canvas: overlays and the too-small screen

- `.fade(keep=None) -> None` — Dim everything (the app behind an overlay): glyphs fg.faint, fills and attributes removed.
- `.overlay(w, h, title=None, *, x=None, y=None, fade=True, fill='bg.overlay', border='rounded', spec='border.focus', role='modal', hints=None, title_right=None) -> Rect` — Modal: fades the base, clears its area, draws a focused box, records region and focus; centred unless x/y; `hints` go on its last row. Returns the interior above the hints.
- `.center(*where, lines, spec='fg.default') -> int` — Write lines (str | (str, spec) | runs | "" for a gap) centered horizontally and vertically in `where`; too-wide lines are truncated. Returns the y of the first line.
- `.toosmall(need, app=None, keys=(('q', 'quit'),), hint=None) -> None` — The too-small screen (layout-archetypes §2.2): current vs needed size, how to fix it, the keys that still work.

## Canvas: output and lint

- `.to_mock() -> str` — The `.mock` text (header lines + body) that `save()` writes.
- `.plain() -> str` — The canvas as plain text rows (for a quick look in a terminal).
- `.lint(path='<canvas>') -> list[str]` — Lint errors, each naming its cell; empty list = clean.
- `.save(path, check=True, verbose=None, report=True) -> Path` — Write the .mock (parent directories are created). With check=True a lint ERROR raises CanvasError. Prints `mockkit: saved NAME · 0 errors · 1 warning → DIR` plus one line per warning; `verbose=True` (or env `MOCKKIT_VERBOSE=1`) lists every finding, INFO included; `report=False` prints nothing.

## Rect and layout

- `Rect(x, y, w, h, rid=None)` — A cell rectangle (x, y, w, h); unpacks like a tuple. `rid` is the region id when a panel() made it.
- `.right` (property) — First column after the rect (exclusive).
- `.bottom` (property) — First row after the rect (exclusive).
- `.inset(left=1, top=None, right=None, bottom=None) -> Rect` — Shrink: inset(1) all sides, inset(2, 0) left/right 2, top/bottom 0, inset(l, t, r, b) each side.
- `.inner` (property) — The interior of a box drawn on this rect (1 cell of border on each side).
- `.split_h(sizes, gap=0) -> list` — Side by side (columns, like `tmux -L <name> split-window -h`): split_h([32, "*"]) -> [list rect, detail rect].
- `.split_v(sizes, gap=0) -> list` — Stacked (rows): split_v([1, "*", 1, 1]) -> header, body, message line, keybar.
- `.take(n, side='top') -> tuple` — (taken, rest): n rows from top/bottom or n columns from left/right.
- `.center(w, h) -> Rect` — A w x h rect centered in this one (clamped to it).
- `.row(i) -> Rect` — The i-th row as a 1-high rect (negative counts from the bottom).
- `layout(total, sizes, gap=0, what='layout') -> list` — Split `total` cells into [(offset, size)]: int = cells, float < 1 = share, `"*"`/`"N*"` = flex weight. Raises when fixed parts do not fit.
- `size_class(cols) -> str` — layout-archetypes.md §2.1 by width: tiny <60, narrow 60-79, compact 80-99, regular 100-159, wide >=160.

## Col, Node, CanvasError

- `Col(name=None, width=None, align='l', truncate='end', spec='fg.default', sel=None, flex=1, min=1, hide_below=None, header_align=None, ascii_width=None)` — Table column: width None = flex (by `flex` weight, at least `min`); truncate end|start|middle (paths start, ids middle); `sel` = neutral text on the selected row; `hide_below` drops it under that table width; `ascii_width` under glyphs=ascii.
- `Node(label, children=(), open=True)` — A tree node: label (str or runs), children, open (False = folded, children hidden).
- `CanvasError` — A write that would produce a broken mockup (off canvas, border overwrite, bad token...).

## Text and number helpers

- `width(s) -> int` — Display width in cells (EAW W/F = 2, combining = 0).
- `fit(s, w, align='l', ellipsis='⋯', side='end') -> str` — Truncate to w cells at `side` and pad; align l|r|c.
- `truncate(s, w, side='end', ellipsis='⋯') -> str` — Cut to at most w cells: side end (`abc⋯`), start (`⋯xyz`, paths) or middle (`ab⋯yz`, ids); never pads.
- `bar(frac, w) -> tuple[str, str]` — (filled, empty) strings of '█' and '░' totalling w cells; frac is clamped to 0..1.
- `spark(values, lo=None, hi=None, ascii=False) -> str` — Sparkline of one cell per value (▁..█, or `_.,-~=+#` with ascii=True); ▁ is the floor.
- `fold_runs(seq, key=None) -> list` — Collapse consecutive equal items: [a, a, b] -> [(a, 2), (b, 1)]; `key` picks what "equal" compares.
- `times(label, n) -> str` — 'Source read failed ×8' for n > 1, the bare label otherwise (× becomes x under glyphs=ascii).
- `scroll_range(offset, visible, total) -> str` — Visible window as '1-6/21' (1-based, inclusive); '0/0' when empty.
- `scroll_pos(index, total) -> str` — Cursor position as '12/90' (index is 0-based).

## Run builders

- `chip(text, token='status.warning') -> tuple` — A run for runs()/band(): ' WARN ' in fg.on-accent on the status/accent fill `token`.
- `hint_runs(items, sep='  ', key_spec='keyhint.key bold', desc_spec='keyhint.desc') -> list` — Footer hint runs: `key verb` pairs `sep` apart; an item (key, verb, "off") is disabled (fg.faint).
- `tab_runs(items, active=0, numbered=True, active_spec='tab.active.fg bold on:tab.active.bg', inactive_spec='tab.inactive.fg') -> list` — Tab bar runs for a band: ` 1 Services ` (active on its fill), ` 2 Logs `; items as in `tabs()`.
- `tree_rows(nodes, indent=4, ascii=False, folds=False) -> list` — Flatten a tree to [(prefix, label, node, depth)] with V4 guides (ASCII with ascii=True); folded nodes hide their children.

## matrix and frame_name

- `matrix(build, variant, out_dir, states=('normal',), sizes=((80, 24), (120, 30)), extra=(), *, theme=None, caps=None, title=None, fallback=False, skip=None, check=True, render=False, png=False, gallery=None, verbose=None) -> list` — Call `build(c, state)` on a fresh Canvas for every state × size and save each linted frame as `out_dir/<variant>--<state>--<cols>x<rows>.mock`; `extra` adds combos, `skip(state, cols, rows)` drops them; `render`/`png` also write .ansi/.png, `gallery=path` builds a gallery. Failures are reported together. Prints one summary line (`mockkit: saved 12 frames · 0 errors · 3 warnings → DIR`) plus one line per distinct warning; `verbose=True` or `MOCKKIT_VERBOSE=1` lists every frame and finding. Returns the .mock paths.
- `frame_name(variant, state, cols, rows, ext='mock') -> str` — `<variant>--<state>--<cols>x<rows>.<ext>` (formats.md "Frame naming"); slugs are lowercase a-z0-9 and '-'.

## STATUS and GLYPHS

- `STATUS` — dict: ok, fail, warn, info, running, working, pending, marked, success, done, error, failed, warning, degraded, busy, stopped, idle.
- `GLYPHS` — dict: cursor, ellipsis, sep, crumb, times, bar_full, bar_empty, thumb, track, fold_open, fold_closed, skeleton, check_on, check_off, radio_on, radio_off.
