# One Dark / One Light: palette → token map

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [At a glance](#at-a-glance) · L15–25 — variant ids, appearance, base/text/accent hex, license and sources.
- [Palette (official hex)](#palette-official-hex) · L27–51 — the exact official hex of a named palette entry.
- [Author's role rules](#authors-role-rules) · L53–55 — the scheme author's own rules for what each colour is for.
- [Token map](#token-map) · L57–121 — the palette entry, hex and contrast behind each semantic token (tier 1 and tier 2).
- [Contrast findings](#contrast-findings) · L123–130 — which tokens fail a floor per variant, in truecolor, 16 and 256 colours.
- [16-color mode](#16-color-mode) · L132–146 — the per-variant `ansi16` overrides and their ratios.
- [Quirks and discrepancy decisions](#quirks-and-discrepancy-decisions) · L148–154 — where sources disagree and which value was kept, light-theme limits.
- [App ports](#app-ports) · L156–163 — whether helix, lazygit, k9s, btop, yazi, gitui or Textual ship a port of this scheme.

Read this when a TUI uses One Dark / One Light and you need the exact palette entry, hex and contrast for each semantic token, the author's role rules, and the 16-color caveats. Token meanings: [../color-tokens.md](../color-tokens.md). All schemes: [../color-schemes.md](../color-schemes.md). Machine-readable: [`onedark-dark.json`](../themes/onedark-dark.json), [`onedark-light.json`](../themes/onedark-light.json).

## At a glance

| variant | id | appearance | bg.base | fg.default | accent.primary | license |
|---|---|---|---|---|---|---|
| Dark | `onedark-dark` | dark | `#282c34` | `#abb2bf` 6.57 | blue `#61afef` | MIT |
| Light | `onedark-light` | light | `#fafafa` | `#383a42` 10.86 | syntax_accent `#526fff` | MIT |

Sources:

- Dark: palette <https://github.com/joshdick/onedark.vim/blob/main/autoload/onedark.vim>; terminal <https://github.com/joshdick/onedark.vim/blob/main/term/One%20Dark.kitty>; role spec none published.
- Light: palette <https://github.com/atom/one-light-syntax/blob/master/styles/colors.less>; terminal none official; role spec <https://github.com/atom/one-light-syntax/blob/master/styles/syntax-variables.less>.

## Palette (official hex)

- **Dark:** red `#e06c75`, dark_red `#be5046`, green `#98c379`, yellow `#e5c07b`, dark_yellow `#d19a66`, blue `#61afef`, purple `#c678dd`, cyan `#56b6c2`, white `#abb2bf`, black `#282c34`, foreground `#abb2bf`, background `#282c34`, comment_grey `#5c6370`, gutter_fg_grey `#4b5263`, cursor_grey `#2c323c`, visual_grey `#3e4452`, menu_grey `#3e4452`, special_grey `#3b4048`, vertsplit `#3e4452`
- **Light:** mono_1 `#383a42`, mono_2 `#696c77`, mono_3 `#a0a1a7`, hue_1_cyan `#0184bc`, hue_2_blue `#4078f2`, hue_3_purple `#a626a4`, hue_4_green `#50a14f`, hue_5_red1 `#e45649`, hue_5_2_red2 `#ca1243`, hue_6_orange1 `#986801`, hue_6_2_orange2 `#c18401`, syntax_bg `#fafafa`, syntax_gutter `#9d9d9f`, syntax_accent `#526fff`, selection `#e5e5e6`, git_renamed `#52aeff`, git_added `#2db448`, git_modified `#f2a60d`, git_removed `#ff1414`

ANSI 0–15 (terminal slots, in order black … bright white):

| slot | Dark | Light |
|---|---|---|
| 0 black | `#2c323c` cursor_grey | `#383a42` mono_1 |
| 1 red | `#e06c75` red | `#e45649` hue_5_red1 |
| 2 green | `#98c379` green | `#50a14f` hue_4_green |
| 3 yellow | `#e5c07b` yellow | `#c18401` hue_6_2_orange2 |
| 4 blue | `#61afef` blue | `#4078f2` hue_2_blue |
| 5 magenta | `#c678dd` purple | `#a626a4` hue_3_purple |
| 6 cyan | `#56b6c2` cyan | `#0184bc` hue_1_cyan |
| 7 white | `#5c6370` comment_grey | `#a0a1a7` mono_3 |
| 8 br.black | `#3e4452` visual_grey | `#696c77` mono_2 |
| 9 br.red | `#e06c75` red | `#ca1243` hue_5_2_red2 |
| 10 br.green | `#98c379` green | `#50a14f` hue_4_green |
| 11 br.yellow | `#e5c07b` yellow | `#986801` hue_6_orange1 |
| 12 br.blue | `#61afef` blue | `#526fff` syntax_accent |
| 13 br.magenta | `#c678dd` purple | `#a626a4` hue_3_purple |
| 14 br.cyan | `#56b6c2` cyan | `#0184bc` hue_1_cyan |
| 15 br.white | `#abb2bf` white | `#e5e5e6` selection |

## Author's role rules

No prose style guide. One Dark roles come from [colors/onedark.vim](https://github.com/joshdick/onedark.vim/blob/main/colors/onedark.vim) highlight groups: CursorLine cursor_grey, Visual visual_grey, Pmenu white on menu_grey, PmenuSel cursor_grey on blue, StatusLine white on cursor_grey, VertSplit vertsplit, Comment comment_grey, LineNr gutter_fg_grey, Search black on yellow, Diff green/red/yellow. One Light comes from Atom [one-light-syntax](https://github.com/atom/one-light-syntax/blob/master/styles/syntax-variables.less) (archived 2018, HSL only): mono-1/2/3 text ladder, `@syntax-cursor-line = fade(fg, 5%)`, `@syntax-selection-color = darken(bg, 8%)`, `@syntax-guide = fade(fg, 20%)`, `@syntax-accent` = cursor.

## Token map

Cell = palette name, hex, contrast. Contrast is vs `bg.base` (for bg tokens it shows the step from the base), `selection.fg` is vs `selection.bg`, `fg.on-accent` is the lowest ratio over the accent and status fills. FAIL = below the [contrast floor](../formats.md#contrast-floors). *→ token* = unmapped tier-2 token resolved through its fallback; *derived* = computed hex (see Basis).

### Tier 1 (always mapped)

| token | Dark | Light | basis |
|---|---|---|---|
| `bg.base` | background `#282c34` 1.00 | syntax_bg `#fafafa` 1.00 | spec: Normal bg = background (varies by variant: see JSON) |
| `bg.inset` | background `#282c34` 1.00 | syntax_bg `#fafafa` 1.00 | choice: no tone below background (ANSI black = background) (varies by variant: see JSON) |
| `bg.surface` | cursor_grey `#2c323c` 1.09 | *derived* `#f0f0f1` 1.09 | spec: CursorLine/ColorColumn = cursor_grey (varies by variant: see JSON) |
| `bg.raised` | visual_grey `#3e4452` 1.44 | selection `#e5e5e6` 1.21 | spec: Visual = visual_grey (varies by variant: see JSON) |
| `fg.default` | foreground `#abb2bf` 6.57 | mono_1 `#383a42` 10.86 | spec: Normal fg = foreground (varies by variant: see JSON) |
| `fg.muted` | *derived* `#9197a3` 4.77 | mono_2 `#696c77` 5.01 | choice: no grey between comment_grey (2.32:1) and foreground; derived: foreground @alpha over background … (varies by variant: see JSON) |
| `fg.faint` | comment_grey `#5c6370` 2.32 FAIL | mono_3 `#a0a1a7` 2.47 FAIL | spec: Comment = comment_grey (varies by variant: see JSON) |
| `fg.on-accent` | black `#282c34` 4.38 FAIL | syntax_bg `#fafafa` 3.07 FAIL | spec: DiffAdd/DiffDelete/Search draw black on the accent (varies by variant: see JSON) |
| `border.default` | vertsplit `#3e4452` 1.44 | *derived* `#d3d4d5` 1.42 | spec: VertSplit = vertsplit (varies by variant: see JSON) |
| `accent.primary` | blue `#61afef` 5.92 | syntax_accent `#526fff` 3.96 FAIL | spec: Function/Directory = blue; PmenuSel fill = blue (varies by variant: see JSON) |
| `accent.secondary` | purple `#c678dd` 4.75 | hue_3_purple `#a626a4` 5.86 | spec: Keyword = purple (varies by variant: see JSON) |
| `selection.bg` | blue `#61afef` 5.92 | selection `#e5e5e6` 1.21 | spec: PmenuSel = cursor_grey on blue (accent-fill selection) (varies by variant: see JSON) |
| `status.error` | red `#e06c75` 4.38 FAIL | hue_5_2_red2 `#ca1243` 5.47 | spec: ErrorMsg = red (varies by variant: see JSON) |
| `status.warning` | yellow `#e5c07b` 8.10 | hue_6_orange1 `#986801` 4.66 | spec: WarningMsg = yellow (varies by variant: see JSON) |
| `status.success` | green `#98c379` 6.94 | hue_4_green `#50a14f` 3.07 FAIL | choice: String/DiffAdd green (varies by variant: see JSON) |
| `status.info` | cyan `#56b6c2` 5.91 | hue_1_cyan `#0184bc` 4.00 FAIL | choice: cyan (cross-scheme info = cyan) (varies by variant: see JSON) |

### Tier 2

| token | Dark | Light | basis |
|---|---|---|---|
| `bg.overlay` | menu_grey `#3e4452` 1.44 | *derived* `#f0f0f1` 1.09 | spec: Pmenu = white on menu_grey (varies by variant: see JSON) |
| `bg.stripe` | *derived* `#24272f` 1.07 | *derived* `#f4f4f4` 1.05 | derived: bg.base darkened to 1.07:1 (weakest fill; bg.inset is invisible here, 1.00:1 vs inactive … (varies by variant: see JSON) |
| `fg.title` | *→ fg.default* `#abb2bf` 6.57 | *→ fg.default* `#383a42` 10.86 | fallback |
| `border.focus` | *→ accent.primary* `#61afef` 5.92 | *→ accent.primary* `#526fff` 3.96 | fallback |
| `selection.fg` | cursor_grey `#2c323c` 5.46 | *→ fg.default* `#383a42` 9.01 | spec: PmenuSel = cursor_grey on blue |
| `selection.inactive.bg` | visual_grey `#3e4452` 1.44 | *→ bg.surface* `#f0f0f1` 1.09 | choice: neutral Visual tone when the pane loses focus |
| `text-selection.bg` | visual_grey `#3e4452` 1.44 | selection `#e5e5e6` 1.21 | spec: Visual = visual_grey (varies by variant: see JSON) |
| `cursor.bg` | foreground `#abb2bf` 6.57 | syntax_accent `#526fff` 3.96 | port: term/One Dark.Xresources (canonical) cursorColor = #abb2bf (varies by variant: see JSON) |
| `cursor.fg` | cursor_grey `#2c323c` 1.09 | *→ bg.base* `#fafafa` 1.00 | port: kitty/alacritty cursor text = cursor_grey |
| `search.match` | yellow `#e5c07b` 8.10 | *→ status.warning* `#986801` 4.66 | spec: Search = black on yellow |
| `link` | *→ accent.primary* `#61afef` 5.92 | hue_2_blue `#4078f2` 3.88 FAIL | choice: function blue |
| `keyhint.key` | *→ accent.primary* `#61afef` 5.92 | *→ accent.primary* `#526fff` 3.96 FAIL | fallback |
| `keyhint.desc` | *→ fg.muted* `#9197a3` 4.77 | *→ fg.muted* `#696c77` 5.01 | fallback |
| `statusbar.bg` | cursor_grey `#2c323c` 1.09 | *→ bg.inset* `#fafafa` 1.00 | spec: StatusLine = white on cursor_grey |
| `statusbar.fg` | white `#abb2bf` 6.57 | *→ fg.muted* `#696c77` 5.01 | spec: StatusLine = white on cursor_grey |
| `tab.active.fg` | *→ accent.primary* `#61afef` 5.92 | *→ accent.primary* `#526fff` 3.96 | fallback |
| `tab.active.bg` | *→ bg.raised* `#3e4452` 1.44 | *→ bg.raised* `#e5e5e6` 1.21 | fallback |
| `tab.inactive.fg` | *→ fg.muted* `#9197a3` 4.77 | *→ fg.muted* `#696c77` 5.01 | fallback |
| `table.header` | *→ fg.default* `#abb2bf` 6.57 | *→ fg.default* `#383a42` 10.86 | fallback |
| `mark` | *→ accent.secondary* `#c678dd` 4.75 | *→ accent.secondary* `#a626a4` 5.86 | fallback |
| `scrollbar.thumb` | *→ fg.faint* `#5c6370` 2.32 | *→ fg.faint* `#a0a1a7` 2.47 | fallback |
| `scrollbar.track` | *→ border.default* `#3e4452` 1.44 | *→ border.default* `#d3d4d5` 1.42 | fallback |
| `diff.added` | green `#98c379` 6.94 | git_added `#2db448` 2.60 | spec: DiffAdd = green (varies by variant: see JSON) |
| `diff.removed` | red `#e06c75` 4.38 | git_removed `#ff1414` 3.75 | spec: DiffDelete = red (varies by variant: see JSON) |
| `diff.changed` | yellow `#e5c07b` 8.10 | git_modified `#f2a60d` 1.97 | spec: DiffChange = yellow underline (varies by variant: see JSON) |
| `ramp.low` | green `#98c379` 6.94 | hue_4_green `#50a14f` 3.07 | cross-scheme: severity ramp |
| `ramp.mid` | yellow `#e5c07b` 8.10 | hue_6_orange1 `#986801` 4.66 | cross-scheme: severity ramp |
| `ramp.high` | red `#e06c75` 4.38 | hue_5_2_red2 `#ca1243` 5.47 | cross-scheme: severity ramp |

Derived hex values (computed, not palette entries; `blend(a, b, α)` = a composited over b at opacity α):

- Dark: `bg.stripe` = `#24272f` = see provenance
- Dark: `fg.muted` = `#9197a3` = blend(foreground, background, 0.8)
- Light: `bg.surface`, `bg.overlay` = `#f0f0f1` = blend(mono_1, syntax_bg, 0.05)
- Light: `bg.stripe` = `#f4f4f4` = see provenance
- Light: `border.default` = `#d3d4d5` = blend(mono_1, syntax_bg, 0.2)

## Contrast findings

| variant | truecolor failures | 16-color failures (after overrides) | 256-color failures (OKLab nearest) |
|---|---|---|---|
| Dark | fg.faint 2.32, status.error 4.38, fg.on-accent 4.38 | status.error 4.38, fg.on-accent 4.38 | fg.muted 4.35, fg.faint 2.16, status.error 3.58, fg.on-accent 3.58 |
| Light | fg.faint 2.47, status.success 3.07, status.info 4.00, accent.primary 3.96, keyhint.key 3.96, link 3.88, fg.on-accent 3.07 | status.success 3.07, status.info 4.00, accent.primary 3.88, keyhint.key 3.88, link 3.88, fg.on-accent 3.07 | fg.faint 2.68, status.success 2.88, status.info 4.13, link 3.55, fg.on-accent 2.88 |

Rule for failures: the official mapping is kept unless the palette offers a same-role entry that passes (those swaps are listed in Basis). Where a status color fails, never rely on it alone: pair it with a glyph and a word (see [../color-tokens.md](../color-tokens.md#never-color-only)).

## 16-color mode

Per-theme `ansi16` overrides of the `_tokens.json` defaults (spec = `slot [attrs]`; ratio vs the terminal background in that mode):

| token | default | Dark | Light |
|---|---|---|---|
| `fg.muted` | `default dim` | `15` 6.57 | `8` 5.01 |
| `fg.faint` | `8` | `default dim` 3.06 | · |
| `border.default` | `8` | `7 dim` 1.58 | · |
| `status.error` | `1` | · | `9` 5.47 |
| `status.warning` | `3` | · | `11` 4.66 |
| `search.match` | `3 bold` | · | `11 bold` 4.66 |
| `diff.changed` | `4` | `3` 8.10 | `3` 3.06 |
| `ramp.mid` | `3` | · | `11` 4.66 |
| `ramp.high` | `1` | · | `9` 5.47 |

## Quirks and discrepancy decisions

- Discrepancy (cursor): kitty/alacritty #5c6370 vs term/One Dark.Xresources (README: canonical) #abb2bf. Used #abb2bf: canonical, and #5c6370 is only 2.32:1 on the background. (Dark)
- Discrepancy (selection): kitty selection #5c6370 with fg #2c323c (2.1:1) vs alacritty #3e4452 with cell foreground. Used alacritty's #3e4452 (= onedark.vim Visual) and null foreground. (Dark)
- ANSI quirks: 0 = cursor_grey #2c323c (not the background), 7 = comment_grey (dim), 8 = visual_grey #3e4452 (1.44:1), brights 9-14 = normals. (Dark)
- No official One Light terminal port exists and the Atom source is HSL-only (archived 2018): every hex is derived from atom/one-light-syntax [colors.less](https://github.com/atom/one-light-syntax/blob/master/styles/colors.less). (Light)
- derived: terminal.ansi is NOT official. It is a hue mapping of the syntax palette so the theme loads and 16-color previews work: 0 mono_1, 1 hue-5 red, 2 hue-4 green, 3 hue-6-2 orange, 4 hue-2 blue, 5 hue-3 purple, 6 hue-1 cyan, 7 mono_3, 8 mono_2, 9 hue-5-2 red, 10 hue-4 green, 11 hue-6 orange, 12 syntax_accent, 13 hue-3 purple, 14 hue-1 cyan, 15 selection. (Light)

## App ports

O = official (scheme org or scheme repo extras), B = bundled in the app repo, C = community repo, - = none found (checked 2026-10).

| variant | helix | lazygit | k9s | btop | yazi | gitui | textual |
|---|---|---|---|---|---|---|---|
| Dark | B | - | B | B | - | - | B |
| Light | B | - | B | - | - | - | B |
