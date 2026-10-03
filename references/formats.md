# Formats: themes, mockups, frames, vocabulary ids

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [Theme JSON](#theme-json) · L14–35 — writing or editing a theme file.
- [Contrast floors](#contrast-floors) · L37–51 — the contrast numbers per token (the only place they live).
- [Mockup format](#mockup-format) · L53–78 — writing or reading a `.mock` file: header lines, markup, regions.
- [Capability profile](#capability-profile) · L80–100 — the `#! caps:` line: host attributes, colour depth, glyph level, `source=`.
- [Frame naming](#frame-naming) · L102–120 — file names and the required states × sizes.
- [Vocabulary ids](#vocabulary-ids) · L122–127 — region roles and element types shared by designs and audits.
- [Canonical demo](#canonical-demo) · L129–131 — what the Fleet demo frame contains.

Read this when you write or edit a `.mock` file, a theme JSON, or a frame file name, or when another reference points at a format defined here. Scripts and references depend on these exact shapes.

## Theme JSON

`references/themes/<scheme>-<variant>.json` (template: `catppuccin-mocha.json`). Token definitions (names, tier, role, fallback, default 16-color spec) live in `themes/_tokens.json`; tier-1 tokens must be mapped, tier-2 tokens fall back when unmapped.

```json
{
  "id": "catppuccin-mocha", "name": "Catppuccin Mocha", "scheme": "catppuccin", "variant": "mocha",
  "appearance": "dark|light", "license": "…", "sources": {…},
  "palette": {"base": "#1e1e2e", …},                 // official named palette, exact hexes
  "terminal": {"background": "#…", "foreground": "#…", "cursor": "#…|null", "cursor_text": "#…|null",
               "selection_background": "#…|null", "selection_foreground": "#…|null",
               "ansi": ["#…" × 16]},                 // ANSI 0..15, black..bright_white
  "tokens": {"bg.base": "base", "selection.bg": "#3b3d4f", …},   // palette name or #rrggbb
  "provenance": {"bg.base": "spec: …", "selection.bg": "consensus: 3/7 ports", …},
  "ansi16": {"fg.faint": "default dim"},            // per-token overrides of _tokens.json
  "notes": []
}
```

- **Mapping precedence:** (1) the scheme author's published role spec → (2) consensus of the scheme's official app ports → (3) cross-scheme role consensus → (4) explicit choice. Record the basis in `provenance` (`spec:`, `port:`, `consensus: n/m`, `cross-scheme:`, `choice:` + reason, `derived:`). An ANSI slot name is not its hue (Dracula's blue slot is purple; Rosé Pine's cyan slot is pink).
- **Neutral ladder** (dark): `bg.inset (N0) < bg.base (N1) < bg.surface (N2) < bg.raised (N3) < fg.faint (N4) < fg.muted (N5) < fg.default (N6)`; light themes invert lightness, keep roles.
- **16-color specs** (`ansi16`): `"<color> [attrs…]"` with color `0..15 | default | reverse | bg` and attrs `bold dim italic underline inverse strike`. `default` = terminal default fg/bg; `reverse` = swap the cell's fg/bg; `bg` (fg tokens only) = text in the terminal background color on the fill, drawn as the fill's slot + SGR 7 (how chips stay readable in 16 colors).

## Contrast floors

WCAG ratio against `bg.base` unless noted; checked by `scripts/contrast_check.py` in truecolor and with `--depth 16`.

| Pair | Floor |
|---|---|
| `fg.default` | ≥ 4.5 required, ≥ 7 preferred (advisory) |
| `fg.muted` | ≥ 4.5 |
| `fg.faint` | ≥ 3.0 |
| `status.*`, `accent.primary`, `keyhint.key`, `link` | ≥ 4.5 |
| `border.focus` | ≥ 3.0 |
| `selection.fg` on `selection.bg` | ≥ 4.5 |
| `fg.on-accent` on `accent.primary` and on each `status.*` | ≥ 4.5 |

Dim text (SGR 2) is modelled as `blend(fg, bg, 0.55)` (55 % of the foreground over the background), the constant used by `contrast_check.py` and the theme build. Policy: report failures; fix only when the official palette has a same-role color that passes, otherwise keep the official mapping and note it in the theme. Per-theme results are in `color-schemes.md`.

## Mockup format

Low-fi prototypes are UTF-8 `.mock` files rendered by `scripts/render_mockup.py` (`--check` lints, `--depth truecolor|256|16|none` renders ANSI).

```
#! tui-mockup 1
#! size: 80x24
#! title: Fleet — list + detail demo
#! state: normal
#! caps: attrs=bold,dim,inverse colors=16 glyphs=unicode
#! region r2 list 0,1,32,21 Services (6)
{border.focus}╭─{/}{fg.title bold} Services (6) {/}{border.focus}───╮{/}
│ {accent.primary bold on:selection.bg}❯{/} …
```

- **Header:** `#! ` lines before the first body line. `tui-mockup 1` (first line) and `size: COLSxROWS` are required; optional `title:`, `state:`, `theme:` (default theme id), `caps:` (capability profile, below), `region <id> <role> x,y,w,h [title…]` (ground truth for audits; roles from the schema list below), `focus <region-id>` (the focused pane), `selected <region-id> <row>` (selected row, 0-based inside the region's interior), `note:` (repeatable). Region, focus and selected lines are what `score_description.py --truth-from-mock` scores against.
- **Body:** one line per terminal row; display width ≤ cols (short lines are padded on `bg.base`); line count ≤ rows.
- **Tags:** `{spec}` opens a style, `{/}` closes the innermost; styles nest and may span lines. `spec` = space-separated: one fg token (`fg.muted`), `on:<token>` for the background (`on:selection.bg`; any token is allowed except `fg.on-accent`), attributes `bold dim italic underline inverse strike`. Inner tags inherit outer fg/bg/attrs. Literal braces: `{{` `}}`. Unknown tokens or attributes, unbalanced tags and raw hex are errors.
- **Chips:** `{fg.on-accent on:status.warning} WARN {/}` — text on a status or accent fill. In 16 colors it renders as the fill's slot + reverse (the `bg` spec), so it stays readable.
- **Box integrity:** for every `#! region` drawn as a box (≥ 3 box corners), the perimeter must stay box glyphs; only a title run on the top or bottom edge may interrupt it. Text over a border is an error.
- **Generator:** `scripts/mockkit.py` builds `.mock` files from a cell canvas (`Canvas.box/text/fill/keybar/save`); `save()` lints and refuses border overwrites and wide glyphs; `hline`/`vline` with `ends=("├","┤")` / `("┬","┴")` may join a box side without `force`; `Canvas(…, caps="…")` writes the `#! caps:` header and raises on writes that violate it. Widget helpers (panel, table, listing, tree, keybar, overlay, toosmall) and `matrix()` build every state × size in one call; see [mockkit.md](mockkit.md) (signatures: [mockkit-api.md](mockkit-api.md)). Prefer it over hand-written tags beyond a few frames.
- **Width:** per code point by Unicode East Asian Width (W/F = 2, combining = 0, else 1). Glyph tiers (error / warn / info) are listed in `visual-vocabulary.md`; the em dash `—` and en dash `–` (EAW=A, single-width in practice, common in copy) are INFO like the chrome glyphs.
- **Capability profile:** the optional `#! caps: attrs=bold,dim,inverse colors=16 glyphs=unicode widgets=tabs,list` header declares what the host supports; `render_mockup.py --check` enforces it, see the next section. `--caps "…"` (same syntax) defines or overrides it for files without the header.
- **Craft warnings:** `--check` also reports the countable README-test failures of [visual-craft.md](visual-craft.md#readme-test) as `WARN: craft CRn`: CR1 bracket chips with words (`[ Items ]`), CR2 two `Label:` prefixes on a row or `a / b / c` detail lines, CR3 a table column with one value on all 6+ rows, CR4 a placeholder such as `(none)` ×3+ at full weight, CR5 16+ empty columns between columns on every row of a table, CR6 blank rows ≥ 1/5 of the frame (not in `empty`/`busy`/`toosmall` frames), CR7 key hints over 2+ footer rows. The shipped mockups produce 0 warnings; a cluttered design typically produces dozens. Fix them, or waive one on purpose with `#! note: craft-ok CRn <reason>`.
- **Glyph inventory:** `render_mockup.py --glyphs FILE… [--format md|json]` prints one table of every non-ASCII glyph used across the files (code point, name, EAW, emoji status, PUA flag, lint tier, V9 ASCII fallback, count, first file); exit 1 on any ERROR-tier glyph. Use it to decide the icon level and the fallback list.
- **Clutter metrics:** `ansi_grid.py FILE.ansi|FILE.mock --clutter [--format md|json]` counts chrome share, border nesting depth, repeated markers, redundant status encodings and blank share per region, with one verdict line each. Thresholds are calibrated on the 34 curated references (chrome share notable above 50 %, nesting above 1, a marker on at least 90 % of rows, a glyph next to a bracket tag or a repeated type word on a status row; glyph + word is the baseline and never flagged); the full definitions are in the script's `--help`.

## Capability profile

A **capability profile** states what the host (a terminal, or the application a plugin runs inside) can actually draw, so a design is checked against the real target instead of an ideal one. Fill it during framing (design-system §0 Brief) whenever the TUI runs inside a host such as a multiplexer plugin, an editor pane or an embedded widget host, or in a limited terminal; leave it out for a free-standing app in a modern terminal (the defaults apply).

Header `#! caps: <key>=<v,v> …` (space-separated, each key at most once):

| Key | Values | Default | `--check` enforces |
|---|---|---|---|
| `attrs` | subset of `bold dim italic underline inverse strike` (`none` = no attributes) | all six | an attribute outside the list is an ERROR naming the cell (`x=…,y=…`) |
| `colors` | `truecolor` `256` `16` `none` | `truecolor` | INFO reminder to render with `--depth 16` / `nocolor`; the frame renders at that depth unless `--depth` is given (`none` = `nocolor`: no color, attributes kept) |
| `glyphs` | `ascii` `unicode` `nerd` | `unicode` | `ascii`: any non-ASCII glyph is an ERROR with the V9 fallback (`visual-vocabulary.md`) as hint; `unicode`: private-use / Nerd Font glyphs are ERROR even with `--allow-nerd-font`; `nerd`: private-use glyphs allowed |
| `widgets` | free list (`tabs,list,modal`…) | none | informational only, kept for the design system |
| `source` | `test-card` `docs` `code` `assumed` | none | WARN unless `test-card` or `docs`: a profile copied from the current code (`code`) or guessed (`assumed`) is not evidence of what the host draws; the hint asks for the test card |

```
#! caps: attrs=bold,dim,inverse colors=16 glyphs=unicode widgets=list,tabs source=test-card
```

Italic and strike are the usual casualties in hosts and 16-color terminals: with the profile above, `{fg.muted italic}` is an ERROR and the fix is to carry the emphasis with `dim`, `bold` or a glyph. `render_mockup.py FILE --check --caps "attrs=bold glyphs=ascii"` tries a profile on a file without editing it; `--caps` overrides the header key by key.

**Measure, then declare.** Inside the host, run the **test card**: `python3 scripts/test_card.py` writes escapes directly, as Ink, Bubble Tea, Ratatui and Textual do; `--curses` draws through curses, which caps the result (no strike, no extended underline or links, at most 256 colors). It shows TERM, COLORTERM, the pane size, each attribute (one that looks like `normal` is unsupported), the host's own 16-color palette, the 256 cube, a 24-bit sweep (bands = quantized to 256), a background fill, and glyph rows whose `|` bars must line up with a reference row (a drifting bar = a glyph drawn wider than one cell; boxes in the nerd row = no Nerd Font). Put the screenshot next to `assets/test-card/raw--reference.png` (or `curses--reference.png`): whatever the reference shows and the screenshot lacks (an overline, the red underline color, a smooth sweep) the host drops. One screenshot fills every key above. Nerd glyphs depend on the user's font, not the host: a plugin others install keeps `glyphs=unicode`. After designing, `play_mock.py FRAME.mock` draws the frame itself with curses in the host (one color pair per fg/bg, 256-color indexes or the theme's `ansi16`), which proves the host renders it before any code is written.

## Frame naming

`<design-dir>/<variant>--<state>--<cols>x<rows>.<ext>` with ext `mock`, `ansi`, `svg` or `png`. `gallery.py` and `compare.py` rely on this naming.

**Required states and sizes** (the single list every other file defers to):

| State | Required when | Shows |
|---|---|---|
| `normal` | always | representative real data, one focused pane, one selected row |
| `empty` | the screen lists or searches anything; for a detail or log screen, the item exists but has no data yet (queued run, step not started) | why it is empty and the key that fills it |
| `busy` | data loads or an action runs longer than ~300 ms | spinner/progress in place of the content being loaded; the rest stays usable |
| `error` | anything can fail (I/O, network, auth) | what failed, what still works, the key to retry; `degraded` (stale data kept) is a variant of `error` |
| `toosmall` | once per app, on its main screen, one frame below the minimum size | current vs needed size in words, keys that still work (quit) |

Sizes: `80x24` and `120x30` for every required state except `toosmall`; add `170x40` when the layout changes at wide widths.

**60-column check** (`60x24`): the floor for a narrow tmux split. **Required** when the layout has more than one column or pane (list + detail, sidebar, Miller columns, side-by-side logs): the `normal` state must be shown at `60x24` as its single-pane fallback (which pane stays, which are dropped or stacked, and the key that switches), as a frame `<variant>--normal--60x24.mock` or, when the layout simply collapses to what the `toosmall` or 80-column design already shows, as a written statement of that behavior in the design system. **Not required** for single-column screens, and for multi-column layouts it is needed for `normal` only, not for every state. If the app's minimum width is above 60, the 60-column frame is the `toosmall` frame.

Overlays (help, confirm, filter, command palette, toast) are extra states of the screen they cover, named after the overlay: `runs--help--80x24.mock`, `run--confirm--80x24.mock`. One frame per overlay at 80x24 is enough unless it changes with size.

## Vocabulary ids

One vocabulary across designs, framework translation (`vocabulary.md`) and audits (`schemas/tui-description.schema.json`).

- **Region roles:** screen header menubar tabbar toolbar sidebar list table tree detail editor log chart form input statusbar footer keybar modal toast popup_menu tooltip panel other
- **Element types:** text heading label value button link key_hint tab list_item table_header table_row table_cell tree_item checkbox radio toggle input_field placeholder cursor prompt progress_bar gauge sparkline chart separator scrollbar badge icon spinner status_indicator breadcrumb message other

## Canonical demo

`assets/demo/fleet--normal--80x24.mock` — "Fleet", a list + detail service monitor: header band (app name, 3 tabs, right-aligned context), focused list "Services (6)" with a selected row and status glyphs, detail panel with fields, three severity gauges and "Recent events", a message line and a footer key-hint bar. Every proto-starter in `assets/proto-starters/` renders this screen from a theme, so frameworks can be compared cell by cell.
