# Gruvbox (Dark, Light; medium contrast): palette → token map

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [At a glance](#at-a-glance) · L15–25 — variant ids, appearance, base/text/accent hex, license and sources.
- [Palette (official hex)](#palette-official-hex) · L27–87 — the exact official hex of a named palette entry.
- [Author's role rules](#authors-role-rules) · L89–91 — the scheme author's own rules for what each colour is for.
- [Token map](#token-map) · L93–149 — the palette entry, hex and contrast behind each semantic token (tier 1 and tier 2).
- [Contrast findings](#contrast-findings) · L151–158 — which tokens fail a floor per variant, in truecolor, 16 and 256 colours.
- [16-color mode](#16-color-mode) · L160–187 — the per-variant `ansi16` overrides and their ratios.
- [Quirks and discrepancy decisions](#quirks-and-discrepancy-decisions) · L189–194 — where sources disagree and which value was kept, light-theme limits.
- [App ports](#app-ports) · L196–203 — whether helix, lazygit, k9s, btop, yazi, gitui or Textual ship a port of this scheme.

Read this when a TUI uses Gruvbox and you need the exact palette entry, hex and contrast for each semantic token, the author's role rules, and the 16-color caveats. Token meanings: [../color-tokens.md](../color-tokens.md). All schemes: [../color-schemes.md](../color-schemes.md). Machine-readable: [`gruvbox-dark.json`](../themes/gruvbox-dark.json), [`gruvbox-light.json`](../themes/gruvbox-light.json).

## At a glance

| variant | id | appearance | bg.base | fg.default | accent.primary | license |
|---|---|---|---|---|---|---|
| Dark | `gruvbox-dark` | dark | `#282828` | `#ebdbb2` 10.75 | bright_blue `#83a598` | MIT |
| Light | `gruvbox-light` | light | `#fbf1c7` | `#3c3836` 10.22 | faded_blue `#076678` | MIT |

Sources:

- Dark: palette <https://github.com/morhetz/gruvbox/blob/master/colors/gruvbox.vim>; terminal <https://github.com/morhetz/gruvbox-contrib/blob/master/xresources/gruvbox-dark.xresources>; role spec none published.
- Light: palette <https://github.com/morhetz/gruvbox/blob/master/colors/gruvbox.vim>; terminal <https://github.com/morhetz/gruvbox-contrib/blob/master/xresources/gruvbox-light.xresources>; role spec none published.

## Palette (official hex)

| name | Dark | Light |
|---|---|---|
| dark0_hard | `#1d2021` | `#1d2021` |
| dark0 | `#282828` | `#282828` |
| dark0_soft | `#32302f` | `#32302f` |
| dark1 | `#3c3836` | `#3c3836` |
| dark2 | `#504945` | `#504945` |
| dark3 | `#665c54` | `#665c54` |
| dark4 | `#7c6f64` | `#7c6f64` |
| light0_hard | `#f9f5d7` | `#f9f5d7` |
| light0 | `#fbf1c7` | `#fbf1c7` |
| light0_soft | `#f2e5bc` | `#f2e5bc` |
| light1 | `#ebdbb2` | `#ebdbb2` |
| light2 | `#d5c4a1` | `#d5c4a1` |
| light3 | `#bdae93` | `#bdae93` |
| light4 | `#a89984` | `#a89984` |
| bright_red | `#fb4934` | `#fb4934` |
| bright_green | `#b8bb26` | `#b8bb26` |
| bright_yellow | `#fabd2f` | `#fabd2f` |
| bright_blue | `#83a598` | `#83a598` |
| bright_purple | `#d3869b` | `#d3869b` |
| bright_aqua | `#8ec07c` | `#8ec07c` |
| bright_orange | `#fe8019` | `#fe8019` |
| neutral_red | `#cc241d` | `#cc241d` |
| neutral_green | `#98971a` | `#98971a` |
| neutral_yellow | `#d79921` | `#d79921` |
| neutral_blue | `#458588` | `#458588` |
| neutral_purple | `#b16286` | `#b16286` |
| neutral_aqua | `#689d6a` | `#689d6a` |
| neutral_orange | `#d65d0e` | `#d65d0e` |
| faded_red | `#9d0006` | `#9d0006` |
| faded_green | `#79740e` | `#79740e` |
| faded_yellow | `#b57614` | `#b57614` |
| faded_blue | `#076678` | `#076678` |
| faded_purple | `#8f3f71` | `#8f3f71` |
| faded_aqua | `#427b58` | `#427b58` |
| faded_orange | `#af3a03` | `#af3a03` |
| gray | `#928374` | `#928374` |

ANSI 0–15 (terminal slots, in order black … bright white):

| slot | Dark | Light |
|---|---|---|
| 0 black | `#282828` dark0 | `#fdf4c1` |
| 1 red | `#cc241d` neutral_red | `#cc241d` neutral_red |
| 2 green | `#98971a` neutral_green | `#98971a` neutral_green |
| 3 yellow | `#d79921` neutral_yellow | `#d79921` neutral_yellow |
| 4 blue | `#458588` neutral_blue | `#458588` neutral_blue |
| 5 magenta | `#b16286` neutral_purple | `#b16286` neutral_purple |
| 6 cyan | `#689d6a` neutral_aqua | `#689d6a` neutral_aqua |
| 7 white | `#a89984` light4 | `#7c6f64` dark4 |
| 8 br.black | `#928374` gray | `#928374` gray |
| 9 br.red | `#fb4934` bright_red | `#9d0006` faded_red |
| 10 br.green | `#b8bb26` bright_green | `#79740e` faded_green |
| 11 br.yellow | `#fabd2f` bright_yellow | `#b57614` faded_yellow |
| 12 br.blue | `#83a598` bright_blue | `#076678` faded_blue |
| 13 br.magenta | `#d3869b` bright_purple | `#8f3f71` faded_purple |
| 14 br.cyan | `#8ec07c` bright_aqua | `#427b58` faded_aqua |
| 15 br.white | `#ebdbb2` light1 | `#3c3836` dark1 |

## Author's role rules

No prose style guide is published. Roles come from the author's highlight groups in [colors/gruvbox.vim](https://github.com/morhetz/gruvbox/blob/master/colors/gruvbox.vim): bg0 = dark0/light0, bg1 CursorLine, bg2 Pmenu/StatusLine, bg3 Visual/VertSplit, bg4 LineNr; fg1 Normal, fg4 StatusLineNC; Comment = gray; Title = green bold; Search = yellow (inverse); IncSearch = orange; PmenuSel = bg2 on blue; Underlined = blue; DiffAdd/Change/Delete = green/aqua/red. **Dark uses the `bright_*` accents, Light the `faded_*` accents.** Hard/soft contrast change bg0 only.

## Token map

Cell = palette name, hex, contrast. Contrast is vs `bg.base` (for bg tokens it shows the step from the base), `selection.fg` is vs `selection.bg`, `fg.on-accent` is the lowest ratio over the accent and status fills. FAIL = below the [contrast floor](../formats.md#contrast-floors). *→ token* = unmapped tier-2 token resolved through its fallback; *derived* = computed hex (see Basis).

### Tier 1 (always mapped)

| token | Dark | Light | basis |
|---|---|---|---|
| `bg.base` | dark0 `#282828` 1.00 | light0 `#fbf1c7` 1.00 | spec: gruvbox.vim bg0 = dark0 (Normal bg, medium contrast) (varies by variant: see JSON) |
| `bg.inset` | dark0_hard `#1d2021` 1.11 | light0_hard `#f9f5d7` 1.03 | choice: gruvbox's own 'hard' background, one step below bg0 (varies by variant: see JSON) |
| `bg.surface` | dark1 `#3c3836` 1.27 | light1 `#ebdbb2` 1.21 | spec: bg1 = CursorLine, SignColumn |
| `bg.raised` | dark2 `#504945` 1.67 | light2 `#d5c4a1` 1.51 | spec: bg2 = Pmenu, StatusLine background |
| `fg.default` | light1 `#ebdbb2` 10.75 | dark1 `#3c3836` 10.22 | spec: fg1 = Normal fg |
| `fg.muted` | light4 `#a89984` 5.30 | dark3 `#665c54` 5.74 | spec: fg4 = StatusLineNC / secondary UI text (varies by variant: see JSON) |
| `fg.faint` | gray `#928374` 4.02 | gray `#928374` 3.24 | spec: Comment = gray |
| `fg.on-accent` | dark0 `#282828` 4.29 FAIL | light0 `#fbf1c7` 4.29 FAIL | spec: Search/IncSearch draw bg0 on yellow/orange (inverse) |
| `border.default` | dark3 `#665c54` 2.26 | light3 `#bdae93` 1.92 | spec: VertSplit fg = bg3 |
| `accent.primary` | bright_blue `#83a598` 5.48 | faded_blue `#076678` 5.82 | spec: PmenuSel = bg2 on blue, Underlined/links blue; consensus accent bright_blue 1/3 (varies by variant: see JSON) |
| `accent.secondary` | bright_purple `#d3869b` 5.37 | faded_purple `#8f3f71` 5.94 | choice: categorical contrast with blue; dark accent set bright_* (varies by variant: see JSON) |
| `selection.bg` | dark3 `#665c54` 2.26 | light3 `#bdae93` 1.92 | spec: Visual bg = bg3 (gruvbox default is inverse video) (varies by variant: see JSON) |
| `status.error` | bright_red `#fb4934` 4.29 FAIL | faded_red `#9d0006` 7.60 | spec: ErrorMsg red; dark accent set bright_* (varies by variant: see JSON) |
| `status.warning` | bright_yellow `#fabd2f` 8.69 | faded_orange `#af3a03` 5.40 | cross-scheme: warning = yellow 17/22 (gruvbox ports tie bright_orange/bright_yellow 1/3) (varies by variant: see JSON) |
| `status.success` | bright_green `#b8bb26` 7.14 | faded_green `#79740e` 4.29 FAIL | consensus: success bright_green 1/2; dark accent set (varies by variant: see JSON) |
| `status.info` | bright_aqua `#8ec07c` 7.01 | faded_aqua `#427b58` 4.40 FAIL | consensus: info bright_aqua 2/2 (varies by variant: see JSON) |

### Tier 2

| token | Dark | Light | basis |
|---|---|---|---|
| `bg.overlay` | dark2 `#504945` 1.67 | light2 `#d5c4a1` 1.51 | spec: Pmenu = fg1 on bg2 |
| `bg.stripe` | *→ bg.inset* `#1d2021` 1.11 | *→ bg.inset* `#f9f5d7` 1.03 | fallback |
| `fg.title` | bright_green `#b8bb26` 7.14 | faded_green `#79740e` 4.29 | spec: Title = green bold (ports use light1 2/3; swap if titles should stay neutral) (varies by variant: see JSON) |
| `border.focus` | light1 `#ebdbb2` 10.75 | dark1 `#3c3836` 10.22 | consensus: focused border light1 2/4 ports (varies by variant: see JSON) |
| `selection.fg` | *→ fg.default* `#ebdbb2` 4.75 | *→ fg.default* `#3c3836` 5.32 | fallback |
| `selection.inactive.bg` | *→ bg.surface* `#3c3836` 1.27 | *→ bg.surface* `#ebdbb2` 1.21 | fallback |
| `text-selection.bg` | dark3 `#665c54` 2.26 | light3 `#bdae93` 1.92 | spec: Visual bg = bg3 |
| `cursor.bg` | *→ fg.default* `#ebdbb2` 10.75 | *→ fg.default* `#3c3836` 10.22 | fallback |
| `cursor.fg` | *→ bg.base* `#282828` 1.00 | *→ bg.base* `#fbf1c7` 1.00 | fallback |
| `search.match` | bright_yellow `#fabd2f` 8.69 | faded_yellow `#b57614` 3.33 | spec: Search = yellow (inverse) |
| `link` | bright_blue `#83a598` 5.48 | faded_blue `#076678` 5.82 | spec: Underlined = blue underline |
| `keyhint.key` | *→ accent.primary* `#83a598` 5.48 | *→ accent.primary* `#076678` 5.82 | fallback |
| `keyhint.desc` | *→ fg.muted* `#a89984` 5.30 | *→ fg.muted* `#665c54` 5.74 | fallback |
| `statusbar.bg` | dark2 `#504945` 1.67 | light2 `#d5c4a1` 1.51 | spec: StatusLine = fg1 on bg2; consensus dark2 2/3 (varies by variant: see JSON) |
| `statusbar.fg` | light1 `#ebdbb2` 10.75 | dark1 `#3c3836` 10.22 | spec: StatusLine fg1; consensus light1 2/3 (varies by variant: see JSON) |
| `tab.active.fg` | *→ accent.primary* `#83a598` 5.48 | *→ accent.primary* `#076678` 5.82 | fallback |
| `tab.active.bg` | *→ bg.raised* `#504945` 1.67 | *→ bg.raised* `#d5c4a1` 1.51 | fallback |
| `tab.inactive.fg` | *→ fg.muted* `#a89984` 5.30 | *→ fg.muted* `#665c54` 5.74 | fallback |
| `table.header` | *→ fg.default* `#ebdbb2` 10.75 | *→ fg.default* `#3c3836` 10.22 | fallback |
| `mark` | *→ accent.secondary* `#d3869b` 5.37 | *→ accent.secondary* `#8f3f71` 5.94 | fallback |
| `scrollbar.thumb` | *→ fg.faint* `#928374` 4.02 | *→ fg.faint* `#928374` 3.24 | fallback |
| `scrollbar.track` | *→ border.default* `#665c54` 2.26 | *→ border.default* `#bdae93` 1.92 | fallback |
| `diff.added` | bright_green `#b8bb26` 7.14 | faded_green `#79740e` 4.29 | spec: DiffAdd = green |
| `diff.removed` | bright_red `#fb4934` 4.29 | faded_red `#9d0006` 7.60 | spec: DiffDelete = red |
| `diff.changed` | bright_aqua `#8ec07c` 7.01 | faded_aqua `#427b58` 4.40 | spec: DiffChange = aqua |
| `ramp.low` | bright_green `#b8bb26` 7.14 | faded_green `#79740e` 4.29 | cross-scheme: severity ramp |
| `ramp.mid` | bright_yellow `#fabd2f` 8.69 | faded_orange `#af3a03` 5.40 | cross-scheme: severity ramp (varies by variant: see JSON) |
| `ramp.high` | bright_red `#fb4934` 4.29 | faded_red `#9d0006` 7.60 | cross-scheme: severity ramp |

## Contrast findings

| variant | truecolor failures | 16-color failures (after overrides) | 256-color failures (OKLab nearest) |
|---|---|---|---|
| Dark | status.error 4.29, fg.on-accent 4.29 | status.error 4.29, fg.on-accent 4.29 | none |
| Light | status.success 4.29, status.info 4.40, fg.on-accent 4.29 | status.warning 3.33, status.success 4.29, status.info 4.40, fg.on-accent 3.39 | status.info 4.43, fg.on-accent 4.43 |

Rule for failures: the official mapping is kept unless the palette offers a same-role entry that passes (those swaps are listed in Basis). Where a status color fails, never rely on it alone: pair it with a glyph and a word (see [../color-tokens.md](../color-tokens.md#never-color-only)).

## 16-color mode

Per-theme `ansi16` overrides of the `_tokens.json` defaults (spec = `slot [attrs]`; ratio vs the terminal background in that mode):

| token | default | Dark | Light |
|---|---|---|---|
| `fg.muted` | `default dim` | `7` 5.30 | `15` 10.22 |
| `fg.on-accent` | `bg` | · | `0` 3.39 |
| `border.focus` | `4` | `11` 8.69 | `7` 4.29 |
| `accent.primary` | `4` | `12` 5.48 | `12` 5.82 |
| `accent.secondary` | `5` | `13` 5.37 | `13` 5.94 |
| `status.error` | `1` | `9` 4.29 | `9` 7.60 |
| `status.warning` | `3` | `11` 8.69 | `11` 3.33 |
| `status.success` | `2` | `10` 7.14 | `10` 4.29 |
| `status.info` | `6` | `14` 7.01 | `14` 4.40 |
| `search.match` | `3 bold` | `11 bold` 8.69 | `11 bold` 3.33 |
| `link` | `4 underline` | `12 underline` 5.48 | `12 underline` 5.82 |
| `keyhint.key` | `4` | `12` 5.48 | `12` 5.82 |
| `keyhint.desc` | `default dim` | · | `7` 4.29 |
| `tab.active.fg` | `4 bold` | `12 bold` 5.48 | `12 bold` 5.82 |
| `tab.inactive.fg` | `default dim` | · | `7` 4.29 |
| `mark` | `5` | `13` 5.37 | `13` 5.94 |
| `diff.added` | `2` | `10` 7.14 | `10` 4.29 |
| `diff.removed` | `1` | `9` 4.29 | `9` 7.60 |
| `diff.changed` | `4` | `14` 7.01 | · |
| `ramp.low` | `2` | `10` 7.14 | `10` 4.29 |
| `ramp.mid` | `3` | `11` 8.69 | `11` 3.33 |
| `ramp.high` | `1` | `9` 4.29 | `9` 7.60 |

## Quirks and discrepancy decisions

- Terminal slots: morhetz/gruvbox-contrib xresources (2014, the author's only terminal definition); cursor/selection undefined (null). (Dark)
- Hard/soft contrast only change bg0 (dark0_hard #1d2021, dark0_soft #32302f); bg.inset uses dark0_hard. (Dark)
- Discrepancy (ANSI 0): gruvbox-contrib light xresources sets color0 = #fdf4c1, which is not a palette color (light0 = #fbf1c7). Kept the port value (it is what that terminal config shows; the two differ by 1.02:1); no token references it. (Light)
- Light accents are the faded_* set; faded_yellow (3.33:1) fails as text so status.warning uses faded_orange (5.40:1). Note faded_orange and faded_red are close in hue: always pair warning/error with distinct glyphs. (Light)

## App ports

O = official (scheme org or scheme repo extras), B = bundled in the app repo, C = community repo, - = none found (checked 2026-10).

| variant | helix | lazygit | k9s | btop | yazi | gitui | textual |
|---|---|---|---|---|---|---|---|
| Dark | B | - | B | B | C | - | B |
| Light | B | - | B | B | - | - | - |
