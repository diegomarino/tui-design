# Everforest (Dark, Light; medium contrast): palette → token map

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [At a glance](#at-a-glance) · L15–22 — variant ids, appearance, base/text/accent hex, license and sources.
- [Palette (official hex)](#palette-official-hex) · L24–75 — the exact official hex of a named palette entry.
- [Author's role rules](#authors-role-rules) · L77–88 — the scheme author's own rules for what each colour is for.
- [Token map](#token-map) · L90–151 — the palette entry, hex and contrast behind each semantic token (tier 1 and tier 2).
- [Contrast findings](#contrast-findings) · L153–160 — which tokens fail a floor per variant, in truecolor, 16 and 256 colours.
- [16-color mode](#16-color-mode) · L162–179 — the per-variant `ansi16` overrides and their ratios.
- [Quirks and discrepancy decisions](#quirks-and-discrepancy-decisions) · L181–185 — where sources disagree and which value was kept, light-theme limits.
- [App ports](#app-ports) · L187–194 — whether helix, lazygit, k9s, btop, yazi, gitui or Textual ship a port of this scheme.

Read this when a TUI uses Everforest and you need the exact palette entry, hex and contrast for each semantic token, the author's role rules, and the 16-color caveats. Token meanings: [../color-tokens.md](../color-tokens.md). All schemes: [../color-schemes.md](../color-schemes.md). Machine-readable: [`everforest-dark.json`](../themes/everforest-dark.json), [`everforest-light.json`](../themes/everforest-light.json).

## At a glance

| variant | id | appearance | bg.base | fg.default | accent.primary | license |
|---|---|---|---|---|---|---|
| Dark | `everforest-dark` | dark | `#2d353b` | `#d3c6aa` 7.38 | green `#a7c080` | MIT |
| Light | `everforest-light` | light | `#fdf6e3` | `#5c6a72` 5.18 | green `#8da101` | MIT |

Sources (first variant; others use the same files per variant): palette <https://github.com/sainnhe/everforest/blob/master/autoload/everforest.vim>; terminal <https://github.com/sainnhe/everforest/blob/master/colors/everforest.vim>; role spec <https://github.com/sainnhe/everforest/blob/master/palette.md#highlights>.

## Palette (official hex)

| name | Dark | Light |
|---|---|---|
| bg_dim | `#232a2e` | `#efebd4` |
| bg0 | `#2d353b` | `#fdf6e3` |
| bg1 | `#343f44` | `#f4f0d9` |
| bg2 | `#3d484d` | `#efebd4` |
| bg3 | `#475258` | `#e6e2cc` |
| bg4 | `#4f585e` | `#e0dcc7` |
| bg5 | `#56635f` | `#bdc3af` |
| bg_visual | `#543a48` | `#eaedc8` |
| bg_red | `#514045` | `#fde3da` |
| bg_yellow | `#4d4c43` | `#faedcd` |
| bg_green | `#425047` | `#f0f1d2` |
| bg_blue | `#3a515d` | `#e9f0e9` |
| bg_purple | `#4a444e` | `#fae8e2` |
| fg | `#d3c6aa` | `#5c6a72` |
| red | `#e67e80` | `#f85552` |
| orange | `#e69875` | `#f57d26` |
| yellow | `#dbbc7f` | `#dfa000` |
| green | `#a7c080` | `#8da101` |
| aqua | `#83c092` | `#35a77c` |
| blue | `#7fbbb3` | `#3a94c5` |
| purple | `#d699b6` | `#df69ba` |
| grey0 | `#7a8478` | `#a6b0a0` |
| grey1 | `#859289` | `#939f91` |
| grey2 | `#9da9a0` | `#829181` |
| statusline1 | `#a7c080` | `#93b259` |
| statusline2 | `#d3c6aa` | `#708089` |
| statusline3 | `#e67e80` | `#e66868` |

ANSI 0–15 (terminal slots, in order black … bright white):

| slot | Dark | Light |
|---|---|---|
| 0 black | `#475258` bg3 | `#5c6a72` fg |
| 1 red | `#e67e80` red | `#f85552` red |
| 2 green | `#a7c080` green | `#8da101` green |
| 3 yellow | `#dbbc7f` yellow | `#dfa000` yellow |
| 4 blue | `#7fbbb3` blue | `#3a94c5` blue |
| 5 magenta | `#d699b6` purple | `#df69ba` purple |
| 6 cyan | `#83c092` aqua | `#35a77c` aqua |
| 7 white | `#d3c6aa` fg | `#e6e2cc` bg3 |
| 8 br.black | `#475258` bg3 | `#5c6a72` fg |
| 9 br.red | `#e67e80` red | `#f85552` red |
| 10 br.green | `#a7c080` green | `#8da101` green |
| 11 br.yellow | `#dbbc7f` yellow | `#dfa000` yellow |
| 12 br.blue | `#7fbbb3` blue | `#3a94c5` blue |
| 13 br.magenta | `#d699b6` purple | `#df69ba` purple |
| 14 br.cyan | `#83c092` aqua | `#35a77c` aqua |
| 15 br.white | `#d3c6aa` fg | `#e6e2cc` bg3 |

## Author's role rules

Source: [palette.md "Highlights"](https://github.com/sainnhe/everforest/blob/master/palette.md#highlights): "The semantics of color identifiers ... apply uniformly to all Palette Variants and contrast settings."

| entry | role | | entry | role |
|---|---|---|---|---|
| bg_dim | dimmed background | | grey0 | line numbers, foreground UI elements |
| bg0 | default bg, inactive status line, active tab label text | | grey1 | comments, UI borders, status line text |
| bg1 | cursor line, active status line, tab line bg | | grey2 | cursor line number, inactive tab label |
| bg2 | popup menu, floating window | | statusline1 | menu selection bg, active tab label bg |
| bg3 / bg4 | list chars, inactive tab bg / window split separators | | red / yellow / green / blue | errors / warnings / hints, search / info |
| bg_visual | visual selection | | orange | operators, tags, **Title** |

## Token map

Cell = palette name, hex, contrast. Contrast is vs `bg.base` (for bg tokens it shows the step from the base), `selection.fg` is vs `selection.bg`, `fg.on-accent` is the lowest ratio over the accent and status fills. FAIL = below the [contrast floor](../formats.md#contrast-floors). *→ token* = unmapped tier-2 token resolved through its fallback; *derived* = computed hex (see Basis).

### Tier 1 (always mapped)

| token | Dark | Light | basis |
|---|---|---|---|
| `bg.base` | bg0 `#2d353b` 1.00 | bg0 `#fdf6e3` 1.00 | spec: bg0 = Default Background |
| `bg.inset` | bg_dim `#232a2e` 1.17 | bg_dim `#efebd4` 1.11 | spec: bg_dim = Dimmed Background |
| `bg.surface` | bg1 `#343f44` 1.15 | bg1 `#f4f0d9` 1.06 | spec: bg1 = Cursor Line, Status Line (active), Tab Line background |
| `bg.raised` | bg3 `#475258` 1.55 | bg3 `#e6e2cc` 1.21 | choice: next neutral step above the popup fill bg2 (spec bg3 = inactive tab label background) |
| `fg.default` | fg `#d3c6aa` 7.38 | fg `#5c6a72` 5.18 | spec: fg = Default Foreground |
| `fg.muted` | grey2 `#9da9a0` 5.12 | grey2 `#829181` 3.08 FAIL | spec: grey2 = Cursor Line Number, Tab Line Label (inactive) |
| `fg.faint` | grey0 `#7a8478` 3.21 | grey0 `#a6b0a0` 2.08 FAIL | spec: grey0 = Line Numbers, Foreground UI Elements |
| `fg.on-accent` | bg0 `#2d353b` 4.55 | bg0 `#fdf6e3` 2.12 FAIL | spec: bg0 = Tab Line Label (active), drawn on statusline1 |
| `border.default` | bg4 `#4f585e` 1.72 | bg4 `#e0dcc7` 1.28 | spec: bg4 = Window Splits Separators; consensus inactive border bg4 2/4 |
| `accent.primary` | green `#a7c080` 6.23 | green `#8da101` 2.69 FAIL | consensus: accent green/statusline1 2/2 ports |
| `accent.secondary` | purple `#d699b6` 5.40 | purple `#df69ba` 2.83 | choice: categorical contrast with green (aqua/blue sit next to green) |
| `selection.bg` | statusline1 `#a7c080` 6.23 | bg_visual `#eaedc8` 1.12 | spec: statusline1 = Menu Selection Background (varies by variant: see JSON) |
| `status.error` | red `#e67e80` 4.55 | red `#f85552` 3.04 FAIL | spec: red = Error Messages |
| `status.warning` | yellow `#dbbc7f` 6.84 | yellow `#dfa000` 2.12 FAIL | spec: yellow = Warning Messages |
| `status.success` | green `#a7c080` 6.23 | green `#8da101` 2.69 FAIL | spec: green = Hint Messages; cross-scheme success = green |
| `status.info` | blue `#7fbbb3` 5.74 | blue `#3a94c5` 3.13 FAIL | spec: blue = Info Messages |

### Tier 2

| token | Dark | Light | basis |
|---|---|---|---|
| `bg.overlay` | bg2 `#3d484d` 1.33 | bg2 `#efebd4` 1.11 | spec: bg2 = Popup Menu, Floating Window background |
| `bg.stripe` | *derived* `#293136` 1.06 | *derived* `#f9f2e0` 1.04 | derived: bg.base darkened to 1.06:1 (weakest fill; bg.inset is too strong here, 1.17:1 vs inactive … (varies by variant: see JSON) |
| `fg.title` | orange `#e69875` 5.41 | orange `#f57d26` 2.48 | spec: orange = Title (vim Title group; ports use fg 2/2) |
| `border.focus` | *→ accent.primary* `#a7c080` 6.23 | *→ accent.primary* `#8da101` 2.69 FAIL | fallback |
| `selection.fg` | bg0 `#2d353b` 6.23 | fg `#5c6a72` 4.64 | consensus: selection fg bg0 1/2; spec bg0 = label on statusline1 (varies by variant: see JSON) |
| `selection.inactive.bg` | *→ bg.surface* `#343f44` 1.15 | *→ bg.surface* `#f4f0d9` 1.06 | fallback |
| `text-selection.bg` | bg_visual `#543a48` 1.23 | bg_visual `#eaedc8` 1.12 | spec: bg_visual = Visual Selection |
| `cursor.bg` | *→ fg.default* `#d3c6aa` 7.38 | *→ fg.default* `#5c6a72` 5.18 | fallback |
| `cursor.fg` | *→ bg.base* `#2d353b` 1.00 | *→ bg.base* `#fdf6e3` 1.00 | fallback |
| `search.match` | green `#a7c080` 6.23 | green `#8da101` 2.69 | spec: green = Search Highlights |
| `link` | *→ accent.primary* `#a7c080` 6.23 | *→ accent.primary* `#8da101` 2.69 FAIL | fallback |
| `keyhint.key` | *→ accent.primary* `#a7c080` 6.23 | *→ accent.primary* `#8da101` 2.69 FAIL | fallback |
| `keyhint.desc` | *→ fg.muted* `#9da9a0` 5.12 | *→ fg.muted* `#829181` 3.08 | fallback |
| `statusbar.bg` | bg1 `#343f44` 1.15 | bg1 `#f4f0d9` 1.06 | spec: bg1 = Status Line Background (active) |
| `statusbar.fg` | grey1 `#859289` 3.84 | grey1 `#939f91` 2.56 | spec: grey1 = Status Line Text |
| `tab.active.fg` | bg0 `#2d353b` 1.00 | bg0 `#fdf6e3` 1.00 | spec: bg0 = Tab Line Label (active) |
| `tab.active.bg` | statusline1 `#a7c080` 6.23 | statusline1 `#93b259` 2.22 | spec: statusline1 = Tab Line Label Background (active) |
| `tab.inactive.fg` | grey2 `#9da9a0` 5.12 | grey2 `#829181` 3.08 | spec: grey2 = Tab Line Label (inactive) |
| `table.header` | *→ fg.default* `#d3c6aa` 7.38 | *→ fg.default* `#5c6a72` 5.18 | fallback |
| `mark` | *→ accent.secondary* `#d699b6` 5.40 | *→ accent.secondary* `#df69ba` 2.83 | fallback |
| `scrollbar.thumb` | *→ fg.faint* `#7a8478` 3.21 | *→ fg.faint* `#a6b0a0` 2.08 | fallback |
| `scrollbar.track` | *→ border.default* `#4f585e` 1.72 | *→ border.default* `#e0dcc7` 1.28 | fallback |
| `diff.added` | green `#a7c080` 6.23 | green `#8da101` 2.69 | consensus: 2/2 ports |
| `diff.removed` | red `#e67e80` 4.55 | red `#f85552` 3.04 | spec: red = Diff Deleted Signs; consensus 2/2 |
| `diff.changed` | blue `#7fbbb3` 5.74 | blue `#3a94c5` 3.13 | spec: blue = Diff Changed Text background; consensus 1/2 |
| `ramp.low` | green `#a7c080` 6.23 | green `#8da101` 2.69 | cross-scheme: severity ramp |
| `ramp.mid` | yellow `#dbbc7f` 6.84 | yellow `#dfa000` 2.12 | cross-scheme: severity ramp |
| `ramp.high` | red `#e67e80` 4.55 | red `#f85552` 3.04 | cross-scheme: severity ramp |

Derived hex values (computed, not palette entries; `blend(a, b, α)` = a composited over b at opacity α):

- Dark: `bg.stripe` = `#293136` = see provenance
- Light: `bg.stripe` = `#f9f2e0` = see provenance

## Contrast findings

| variant | truecolor failures | 16-color failures (after overrides) | 256-color failures (OKLab nearest) |
|---|---|---|---|
| Dark | none | none | none |
| Light | fg.muted 3.08, fg.faint 2.08, status.error 3.04, status.warning 2.12, status.success 2.69, status.info 3.13, accent.primary 2.69, keyhint.key 2.69, link 2.69, border.focus 2.69, fg.on-accent 2.12 | status.error 3.04, status.warning 2.12, status.success 2.69, status.info 3.13, accent.primary 2.69, keyhint.key 2.69, link 2.69, border.focus 2.69, fg.on-accent 2.12 | fg.muted 3.38, fg.faint 2.15, status.error 2.91, status.warning 2.05, status.success 2.52, status.info 3.69, accent.primary 2.52, keyhint.key 2.52, link 2.52, border.focus 2.52, fg.on-accent 2.05 |

Rule for failures: the official mapping is kept unless the palette offers a same-role entry that passes (those swaps are listed in Basis). Where a status color fails, never rely on it alone: pair it with a glyph and a word (see [../color-tokens.md](../color-tokens.md#never-color-only)).

## 16-color mode

Per-theme `ansi16` overrides of the `_tokens.json` defaults (spec = `slot [attrs]`; ratio vs the terminal background in that mode):

| token | default | Dark | Light |
|---|---|---|---|
| `fg.muted` | `default dim` | `7` 7.38 | `8` 5.18 |
| `fg.faint` | `8` | `default dim` 3.37 | · |
| `border.focus` | `4` | `2` 6.23 | `2` 2.69 |
| `accent.primary` | `4` | `2` 6.23 | `2` 2.69 |
| `status.info` | `6` | · | `4` 3.13 |
| `search.match` | `3 bold` | · | `2 bold` 2.69 |
| `link` | `4 underline` | `2 underline` 6.23 | `2 underline` 2.69 |
| `keyhint.key` | `4` | `2` 6.23 | `2` 2.69 |
| `keyhint.desc` | `default dim` | · | `8` 5.18 |
| `tab.active.fg` | `4 bold` | `bg bold` 7.38 | `bg bold` 5.18 |
| `tab.active.bg` | `default` | `2` 6.23 | `2` 2.69 |
| `tab.inactive.fg` | `default dim` | · | `8` 5.18 |

## Quirks and discrepancy decisions

- No terminal-emulator port is published; ANSI slots come from colors/everforest.vim terminal colors (black = bg3, white = fg, brights = normals). cursor/selection null. (Dark)
- No terminal-emulator port is published; ANSI slots come from colors/everforest.vim (black = fg, white = bg3, brights = normals). (Light)
- Light-theme limit: every Everforest Light accent and grey except fg is below 4.5:1 on bg0 (red 3.04, blue 3.13, green 2.69, yellow 2.12, grey2 3.08). Hard contrast (bg0 #fffbef) helps only marginally. (Light)

## App ports

O = official (scheme org or scheme repo extras), B = bundled in the app repo, C = community repo, - = none found (checked 2026-10).

| variant | helix | lazygit | k9s | btop | yazi | gitui | textual |
|---|---|---|---|---|---|---|---|
| Dark | B | - | B | B | C | - | - |
| Light | B | - | B | B | - | - | - |
