# Rosé Pine (main, Moon, Dawn): palette → token map

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [At a glance](#at-a-glance) · L15–27 — variant ids, appearance, base/text/accent hex, license and sources.
- [Palette (official hex)](#palette-official-hex) · L29–68 — the exact official hex of a named palette entry.
- [Author's role rules](#authors-role-rules) · L70–80 — the scheme author's own rules for what each colour is for.
- [Token map](#token-map) · L82–144 — the palette entry, hex and contrast behind each semantic token (tier 1 and tier 2).
- [Contrast findings](#contrast-findings) · L146–154 — which tokens fail a floor per variant, in truecolor, 16 and 256 colours.
- [16-color mode](#16-color-mode) · L156–174 — the per-variant `ansi16` overrides and their ratios.
- [Quirks and discrepancy decisions](#quirks-and-discrepancy-decisions) · L176–180 — where sources disagree and which value was kept, light-theme limits.
- [App ports](#app-ports) · L182–190 — whether helix, lazygit, k9s, btop, yazi, gitui or Textual ship a port of this scheme.

Read this when a TUI uses Rosé Pine and you need the exact palette entry, hex and contrast for each semantic token, the author's role rules, and the 16-color caveats. Token meanings: [../color-tokens.md](../color-tokens.md). All schemes: [../color-schemes.md](../color-schemes.md). Machine-readable: [`rose-pine-main.json`](../themes/rose-pine-main.json), [`rose-pine-moon.json`](../themes/rose-pine-moon.json), [`rose-pine-dawn.json`](../themes/rose-pine-dawn.json).

## At a glance

| variant | id | appearance | bg.base | fg.default | accent.primary | license |
|---|---|---|---|---|---|---|
| main | `rose-pine-main` | dark | `#191724` | `#e0def4` 13.39 | iris `#c4a7e7` | MIT |
| Moon | `rose-pine-moon` | dark | `#232136` | `#e0def4` 11.86 | iris `#c4a7e7` | MIT |
| Dawn | `rose-pine-dawn` | light | `#faf4ed` | `#575279` 6.66 | iris `#907aa9` | MIT |

Sources:

- main: palette <https://github.com/rose-pine/palette/blob/main/source/index.ts>; terminal <https://github.com/rose-pine/kitty/blob/main/dist/rose-pine.conf>; role spec <https://github.com/rose-pine/palette#roles>.
- Moon: palette <https://github.com/rose-pine/palette/blob/main/source/index.ts>; terminal <https://github.com/rose-pine/kitty/blob/main/dist/rose-pine-moon.conf>; role spec <https://github.com/rose-pine/palette#roles>.
- Dawn: palette <https://github.com/rose-pine/palette/blob/main/source/index.ts>; terminal <https://github.com/rose-pine/kitty/blob/main/dist/rose-pine-dawn.conf>; role spec <https://github.com/rose-pine/palette#roles>.

## Palette (official hex)

| name | main | Moon | Dawn |
|---|---|---|---|
| base | `#191724` | `#232136` | `#faf4ed` |
| surface | `#1f1d2e` | `#2a273f` | `#fffaf3` |
| overlay | `#26233a` | `#393552` | `#f2e9e1` |
| muted | `#6e6a86` | `#6e6a86` | `#9893a5` |
| subtle | `#908caa` | `#908caa` | `#797593` |
| text | `#e0def4` | `#e0def4` | `#575279` |
| love | `#eb6f92` | `#eb6f92` | `#b4637a` |
| gold | `#f6c177` | `#f6c177` | `#ea9d34` |
| rose | `#ebbcba` | `#ea9a97` | `#d7827e` |
| pine | `#31748f` | `#3e8fb0` | `#286983` |
| foam | `#9ccfd8` | `#9ccfd8` | `#56949f` |
| iris | `#c4a7e7` | `#c4a7e7` | `#907aa9` |
| highlightLow | `#21202e` | `#2a283e` | `#f4ede8` |
| highlightMed | `#403d52` | `#44415a` | `#dfdad9` |
| highlightHigh | `#524f67` | `#56526e` | `#cecacd` |

ANSI 0–15 (terminal slots, in order black … bright white):

| slot | main | Moon | Dawn |
|---|---|---|---|
| 0 black | `#26233a` overlay | `#393552` overlay | `#f2e9e1` overlay |
| 1 red | `#eb6f92` love | `#eb6f92` love | `#b4637a` love |
| 2 green | `#31748f` pine | `#3e8fb0` pine | `#286983` pine |
| 3 yellow | `#f6c177` gold | `#f6c177` gold | `#ea9d34` gold |
| 4 blue | `#9ccfd8` foam | `#9ccfd8` foam | `#56949f` foam |
| 5 magenta | `#c4a7e7` iris | `#c4a7e7` iris | `#907aa9` iris |
| 6 cyan | `#ebbcba` rose | `#ea9a97` rose | `#d7827e` rose |
| 7 white | `#e0def4` text | `#e0def4` text | `#575279` text |
| 8 br.black | `#6e6a86` muted | `#6e6a86` muted | `#9893a5` muted |
| 9 br.red | `#eb6f92` love | `#eb6f92` love | `#b4637a` love |
| 10 br.green | `#31748f` pine | `#3e8fb0` pine | `#286983` pine |
| 11 br.yellow | `#f6c177` gold | `#f6c177` gold | `#ea9d34` gold |
| 12 br.blue | `#9ccfd8` foam | `#9ccfd8` foam | `#56949f` foam |
| 13 br.magenta | `#c4a7e7` iris | `#c4a7e7` iris | `#907aa9` iris |
| 14 br.cyan | `#ebbcba` rose | `#ea9a97` rose | `#d7827e` rose |
| 15 br.white | `#e0def4` text | `#e0def4` text | `#575279` text |

## Author's role rules

Two official sources: the [rose-pine/palette README](https://github.com/rose-pine/palette#roles) and the newer [rosepinetheme.com palette pages](https://github.com/rose-pine/rose-pine-site/tree/main/src/content/palette/en). Rule used here: **site wins, README fills gaps.**

| role | README | site |
|---|---|---|
| Base / Surface / Overlay | primary bg (inactive tabs, sidebars) / inputs, panels / active tabs | bg / popups, inputs, **status and title bars** / active-hovered items, visual selection, tooltips, dialogs |
| Muted / Subtle / Text | comments / non-selected results, inactive tabs / cursor text, selected results | comments, line numbers, disabled / labels, tab titles, placeholder, unfocused pane fg / body, active tab |
| Highlight Low / Med / High | cursor line / selection bg (with Text) / cursor bg, borders | cursor line / text selection, active popup item / borders, cursor bg, search bg |
| Love / Gold | errors, git delete / warnings | errors, deletions / warnings, search match (with Base) |
| Rose / Pine / Foam / Iris | git change / functions, git rename / info, **git add** / links, hints | function calls, **modified** / keywords, **added**, affirmative / info / hints, changed |

## Token map

Cell = palette name, hex, contrast. Contrast is vs `bg.base` (for bg tokens it shows the step from the base), `selection.fg` is vs `selection.bg`, `fg.on-accent` is the lowest ratio over the accent and status fills. FAIL = below the [contrast floor](../formats.md#contrast-floors). *→ token* = unmapped tier-2 token resolved through its fallback; *derived* = computed hex (see Basis).

### Tier 1 (always mapped)

| token | main | Moon | Dawn | basis |
|---|---|---|---|---|
| `bg.base` | base `#191724` 1.00 | base `#232136` 1.00 | base `#faf4ed` 1.00 | spec: Base = primary background |
| `bg.inset` | base `#191724` 1.00 | base `#232136` 1.00 | base `#faf4ed` 1.00 | spec: README 'Base: inactive tabs, sidebars' (no tone below Base; chrome bars go up to Surface) |
| `bg.surface` | surface `#1f1d2e` 1.07 | surface `#2a273f` 1.09 | surface `#fffaf3` 1.05 | spec: Surface = panels, inputs, popups, status bars |
| `bg.raised` | overlay `#26233a` 1.16 | overlay `#393552` 1.34 | overlay `#f2e9e1` 1.10 | spec: Overlay = active/hovered list items, tabs |
| `fg.default` | text `#e0def4` 13.39 | text `#e0def4` 11.86 | text `#575279` 6.66 | spec: Text = high contrast foreground, body text |
| `fg.muted` | subtle `#908caa` 5.48 | subtle `#908caa` 4.86 | subtle `#797593` 4.02 FAIL | spec (site): Subtle = secondary text, labels, tab titles, inactive pane foreground |
| `fg.faint` | muted `#6e6a86` 3.42 | muted `#6e6a86` 3.03 | muted `#9893a5` 2.73 FAIL | spec: Muted = comments, line numbers, disabled labels |
| `fg.on-accent` | base `#191724` 3.38 FAIL | base `#232136` 4.29 FAIL | base `#faf4ed` 2.05 FAIL | spec (site): Gold search highlight 'paired with Base'; cross-scheme N1 on chromatic fills |
| `border.default` | highlightHigh `#524f67` 2.25 | highlightHigh `#56526e` 2.11 | highlightHigh `#cecacd` 1.48 | spec: Highlight High = borders, visual dividers |
| `accent.primary` | iris `#c4a7e7` 8.43 | iris `#c4a7e7` 7.47 | iris `#907aa9` 3.47 FAIL | spec: README Iris = links, hints; consensus accent iris 1/3 |
| `accent.secondary` | pine `#31748f` 3.38 | pine `#3e8fb0` 4.29 | pine `#286983` 5.59 | consensus: accent.secondary pine 1/1 |
| `selection.bg` | highlightMed `#403d52` 1.69 | highlightMed `#44415a` 1.60 | highlightMed `#dfdad9` 1.27 | spec: Highlight Med = selection background (paired with Text) |
| `status.error` | love `#eb6f92` 6.07 | love `#eb6f92` 5.38 | love `#b4637a` 3.84 FAIL | spec: Love = errors |
| `status.warning` | gold `#f6c177` 10.77 | gold `#f6c177` 9.55 | gold `#ea9d34` 2.05 FAIL | spec: Gold = warnings |
| `status.success` | pine `#31748f` 3.38 FAIL | pine `#3e8fb0` 4.29 FAIL | pine `#286983` 5.59 | spec (site): Pine = constructive/affirmative signals, added content |
| `status.info` | foam `#9ccfd8` 10.37 | foam `#9ccfd8` 9.19 | foam `#56949f` 3.14 FAIL | spec: Foam = info |

### Tier 2

| token | main | Moon | Dawn | basis |
|---|---|---|---|---|
| `bg.overlay` | overlay `#26233a` 1.16 | overlay `#393552` 1.34 | overlay `#f2e9e1` 1.10 | spec (site): Overlay = elevated surfaces, e.g. tooltips, dialogs |
| `bg.stripe` | *derived* `#12111b` 1.06 | *derived* `#1e1c2e` 1.06 | *derived* `#f4eee9` 1.05 | derived: bg.base darkened to 1.06:1 (weakest fill; bg.inset is invisible here, 1.00:1 vs inactive … (varies by variant: see JSON) |
| `fg.title` | text `#e0def4` 13.39 | text `#e0def4` 11.86 | text `#575279` 6.66 | spec (site): Text = active tab/item foreground |
| `border.focus` | pine `#31748f` 3.38 | pine `#3e8fb0` 4.29 | pine `#286983` 5.59 | consensus: focused border pine 2/5 ports; port: rose-pine/kitty active_border_color = pine |
| `selection.fg` | text `#e0def4` 7.93 | text `#e0def4` 7.41 | text `#575279` 5.25 | spec: Text = selection foreground (paired with Highlight Med) |
| `selection.inactive.bg` | overlay `#26233a` 1.16 | overlay `#393552` 1.34 | overlay `#f2e9e1` 1.10 | consensus: overlay 1/1 port |
| `text-selection.bg` | highlightMed `#403d52` 1.69 | highlightMed `#44415a` 1.60 | highlightMed `#dfdad9` 1.27 | spec (site): Highlight Med = text selection background |
| `cursor.bg` | highlightHigh `#524f67` 2.25 | highlightHigh `#56526e` 2.11 | highlightHigh `#cecacd` 1.48 | spec: Highlight High = cursor background; port: kitty cursor = highlightHigh |
| `cursor.fg` | text `#e0def4` 13.39 | text `#e0def4` 11.86 | text `#575279` 6.66 | spec: Text = cursor text (paired with Highlight High) |
| `search.match` | gold `#f6c177` 10.77 | gold `#f6c177` 9.55 | gold `#ea9d34` 2.05 | spec (site): Gold = search/match highlights; consensus gold 2/2 |
| `link` | iris `#c4a7e7` 8.43 | iris `#c4a7e7` 7.47 | iris `#907aa9` 3.47 FAIL | spec: README Iris = links |
| `keyhint.key` | foam `#9ccfd8` 10.37 | foam `#9ccfd8` 9.19 | foam `#56949f` 3.14 FAIL | consensus: 2/5 ports |
| `keyhint.desc` | text `#e0def4` 13.39 | text `#e0def4` 11.86 | text `#575279` 6.66 | consensus: 2/4 ports |
| `statusbar.bg` | surface `#1f1d2e` 1.07 | surface `#2a273f` 1.09 | surface `#fffaf3` 1.05 | spec (site): Surface = status bars, title bars |
| `statusbar.fg` | text `#e0def4` 13.39 | text `#e0def4` 11.86 | text `#575279` 6.66 | consensus: 2/3 ports |
| `tab.active.fg` | text `#e0def4` 13.39 | text `#e0def4` 11.86 | text `#575279` 6.66 | spec: README Text = active tabs |
| `tab.active.bg` | overlay `#26233a` 1.16 | overlay `#393552` 1.34 | overlay `#f2e9e1` 1.10 | spec: Overlay = active tabs |
| `tab.inactive.fg` | subtle `#908caa` 5.48 | subtle `#908caa` 4.86 | subtle `#797593` 4.02 | spec: Subtle = inactive tabs, tab titles |
| `table.header` | *→ fg.default* `#e0def4` 13.39 | *→ fg.default* `#e0def4` 11.86 | *→ fg.default* `#575279` 6.66 | fallback |
| `mark` | *→ accent.secondary* `#31748f` 3.38 | *→ accent.secondary* `#3e8fb0` 4.29 | *→ accent.secondary* `#286983` 5.59 | fallback |
| `scrollbar.thumb` | muted `#6e6a86` 3.42 | muted `#6e6a86` 3.03 | muted `#9893a5` 2.73 | spec (site): Muted = scrollbar miscellanea |
| `scrollbar.track` | *→ border.default* `#524f67` 2.25 | *→ border.default* `#56526e` 2.11 | *→ border.default* `#cecacd` 1.48 | fallback |
| `diff.added` | pine `#31748f` 3.38 | pine `#3e8fb0` 4.29 | pine `#286983` 5.59 | spec (site): Pine = added content (README: Foam = git add) |
| `diff.removed` | love `#eb6f92` 6.07 | love `#eb6f92` 5.38 | love `#b4637a` 3.84 | spec: Love = git delete / deletions |
| `diff.changed` | rose `#ebbcba` 10.45 | rose `#ea9a97` 7.13 | rose `#d7827e` 2.60 | spec: README Rose = git change; site Rose = modified content |
| `ramp.low` | pine `#31748f` 3.38 | pine `#3e8fb0` 4.29 | pine `#286983` 5.59 | cross-scheme: severity ramp; = status.success |
| `ramp.mid` | gold `#f6c177` 10.77 | gold `#f6c177` 9.55 | gold `#ea9d34` 2.05 | cross-scheme: severity ramp |
| `ramp.high` | love `#eb6f92` 6.07 | love `#eb6f92` 5.38 | love `#b4637a` 3.84 | cross-scheme: severity ramp |

Derived hex values (computed, not palette entries; `blend(a, b, α)` = a composited over b at opacity α):

- main: `bg.stripe` = `#12111b` = see provenance
- Moon: `bg.stripe` = `#1e1c2e` = see provenance
- Dawn: `bg.stripe` = `#f4eee9` = see provenance

## Contrast findings

| variant | truecolor failures | 16-color failures (after overrides) | 256-color failures (OKLab nearest) |
|---|---|---|---|
| main | status.success 3.38, fg.on-accent 3.38 | status.success 3.38, fg.on-accent 3.38 | fg.faint 2.82, status.success 4.13, fg.on-accent 4.13 |
| Moon | status.success 4.29, fg.on-accent 4.29 | status.success 4.29, fg.on-accent 4.29 | fg.muted 4.41, fg.faint 2.50, status.success 4.01, fg.on-accent 4.01 |
| Dawn | fg.muted 4.02, fg.faint 2.73, status.error 3.84, status.warning 2.05, status.info 3.14, accent.primary 3.47, keyhint.key 3.14, link 3.47, fg.on-accent 2.05 | status.error 3.84, status.warning 2.05, status.info 3.14, accent.primary 3.47, link 3.47, fg.on-accent 2.05 | fg.muted 3.91, fg.faint 2.61, status.error 3.76, status.warning 1.78, status.info 3.41, accent.primary 2.96, keyhint.key 3.41, link 2.96, selection.fg 4.32, fg.on-accent 1.78 |

Rule for failures: the official mapping is kept unless the palette offers a same-role entry that passes (those swaps are listed in Basis). Where a status color fails, never rely on it alone: pair it with a glyph and a word (see [../color-tokens.md](../color-tokens.md#never-color-only)).

## 16-color mode

Per-theme `ansi16` overrides of the `_tokens.json` defaults (spec = `slot [attrs]`; ratio vs the terminal background in that mode):

| token | default | main | Moon | Dawn |
|---|---|---|---|---|
| `fg.muted` | `default dim` | · | · | `7` 6.66 |
| `fg.faint` | `8` | · | · | `7` 6.66 |
| `border.focus` | `4` | `2` 3.38 | `2` 4.29 | `2` 5.59 |
| `accent.primary` | `4` | `5` 8.43 | `5` 7.47 | `5` 3.47 |
| `accent.secondary` | `5` | `2` 3.38 | `2` 4.29 | `2` 5.59 |
| `status.info` | `6` | `4` 10.37 | `4` 9.19 | `4` 3.14 |
| `link` | `4 underline` | `5 underline` 8.43 | `5 underline` 7.47 | `5 underline` 3.47 |
| `keyhint.key` | `4` | · | · | `2` 5.59 |
| `keyhint.desc` | `default dim` | · | · | `7` 6.66 |
| `tab.active.fg` | `4 bold` | `default bold` 13.39 | `default bold` 11.86 | `default bold` 6.66 |
| `tab.inactive.fg` | `default dim` | · | · | `7` 6.66 |
| `mark` | `5` | `2` 3.38 | `2` 4.29 | `2` 5.59 |
| `diff.changed` | `4` | `6` 10.45 | `6` 7.13 | `6` 2.60 |

## Quirks and discrepancy decisions

- Discrepancy (role docs): rose-pine/palette README vs the newer rosepinetheme.com palette pages disagree on Pine/Foam/Rose. Rule used: the site (2025, more specific) wins; the README fills gaps (links = iris, active tabs). So success/added = pine (site), info = foam (both), changed = rose (both).
- ANSI slot names are not hues: green = pine (teal-blue), blue = foam (cyan), cyan = rose (pink), magenta = iris. ansi16 overrides map tokens to the slot holding their palette color. Brights equal normals except bright black = muted.
- bg.inset = base: the spec puts sidebars on Base and status/title bars on Surface (up, not down).

## App ports

O = official (scheme org or scheme repo extras), B = bundled in the app repo, C = community repo, - = none found (checked 2026-10).

| variant | helix | lazygit | k9s | btop | yazi | gitui | textual |
|---|---|---|---|---|---|---|---|
| main | O | O | B | O | O | - | B |
| Moon | O | O | B | O | O | - | B |
| Dawn | O | O | B | O | O | - | B |
