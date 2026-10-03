# Kanagawa (Wave, Dragon, Lotus): palette → token map

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [At a glance](#at-a-glance) · L15–27 — variant ids, appearance, base/text/accent hex, license and sources.
- [Palette (official hex)](#palette-official-hex) · L29–54 — the exact official hex of a named palette entry.
- [Author's role rules](#authors-role-rules) · L56–58 — the scheme author's own rules for what each colour is for.
- [Token map](#token-map) · L60–120 — the palette entry, hex and contrast behind each semantic token (tier 1 and tier 2).
- [Contrast findings](#contrast-findings) · L122–130 — which tokens fail a floor per variant, in truecolor, 16 and 256 colours.
- [16-color mode](#16-color-mode) · L132–150 — the per-variant `ansi16` overrides and their ratios.
- [Quirks and discrepancy decisions](#quirks-and-discrepancy-decisions) · L152–157 — where sources disagree and which value was kept, light-theme limits.
- [App ports](#app-ports) · L159–167 — whether helix, lazygit, k9s, btop, yazi, gitui or Textual ship a port of this scheme.

Read this when a TUI uses Kanagawa and you need the exact palette entry, hex and contrast for each semantic token, the author's role rules, and the 16-color caveats. Token meanings: [../color-tokens.md](../color-tokens.md). All schemes: [../color-schemes.md](../color-schemes.md). Machine-readable: [`kanagawa-wave.json`](../themes/kanagawa-wave.json), [`kanagawa-dragon.json`](../themes/kanagawa-dragon.json), [`kanagawa-lotus.json`](../themes/kanagawa-lotus.json).

## At a glance

| variant | id | appearance | bg.base | fg.default | accent.primary | license |
|---|---|---|---|---|---|---|
| Wave | `kanagawa-wave` | dark | `#1f1f28` | `#dcd7ba` 11.26 | crystalBlue `#7e9cd8` | MIT |
| Dragon | `kanagawa-dragon` | dark | `#181616` | `#c5c9c5` 10.76 | dragonBlue2 `#8ba4b0` | MIT |
| Lotus | `kanagawa-lotus` | light | `#f2ecbc` | `#545464` 6.19 | lotusBlue4 `#4d699b` | MIT |

Sources:

- Wave: palette <https://github.com/rebelot/kanagawa.nvim/blob/master/lua/kanagawa/colors.lua>; terminal <https://github.com/rebelot/kanagawa.nvim/blob/master/extras/kitty/kanagawa.conf>; role spec <https://github.com/rebelot/kanagawa.nvim/blob/master/lua/kanagawa/themes.lua>.
- Dragon: palette <https://github.com/rebelot/kanagawa.nvim/blob/master/lua/kanagawa/colors.lua>; terminal <https://github.com/rebelot/kanagawa.nvim/blob/master/extras/kitty/kanagawa_dragon.conf>; role spec <https://github.com/rebelot/kanagawa.nvim/blob/master/lua/kanagawa/themes.lua>.
- Lotus: palette <https://github.com/rebelot/kanagawa.nvim/blob/master/lua/kanagawa/colors.lua>; terminal <https://github.com/rebelot/kanagawa.nvim/blob/master/extras/kitty/kanagawa_light.conf>; role spec <https://github.com/rebelot/kanagawa.nvim/blob/master/lua/kanagawa/themes.lua>.

## Palette (official hex)

- **Wave:** sumiInk0 `#16161d`, sumiInk1 `#181820`, sumiInk2 `#1a1a22`, sumiInk3 `#1f1f28`, sumiInk4 `#2a2a37`, sumiInk5 `#363646`, sumiInk6 `#54546d`, waveBlue1 `#223249`, waveBlue2 `#2d4f67`, winterGreen `#2b3328`, winterYellow `#49443c`, winterRed `#43242b`, winterBlue `#252535`, autumnGreen `#76946a`, autumnRed `#c34043`, autumnYellow `#dca561`, samuraiRed `#e82424`, roninYellow `#ff9e3b`, waveAqua1 `#6a9589`, dragonBlue `#658594`, oldWhite `#c8c093`, fujiWhite `#dcd7ba`, fujiGray `#727169`, oniViolet `#957fb8`, oniViolet2 `#b8b4d0`, crystalBlue `#7e9cd8`, springViolet1 `#938aa9`, springViolet2 `#9cabca`, springBlue `#7fb4ca`, waveAqua2 `#7aa89f`, springGreen `#98bb6c`, boatYellow2 `#c0a36e`, carpYellow `#e6c384`, sakuraPink `#d27e99`, waveRed `#e46876`, peachRed `#ff5d62`, surimiOrange `#ffa066`, katanaGray `#717c7c`
- **Dragon:** sumiInk6 `#54546d`, waveBlue1 `#223249`, waveBlue2 `#2d4f67`, winterGreen `#2b3328`, winterYellow `#49443c`, winterRed `#43242b`, winterBlue `#252535`, autumnGreen `#76946a`, autumnRed `#c34043`, autumnYellow `#dca561`, samuraiRed `#e82424`, roninYellow `#ff9e3b`, waveAqua1 `#6a9589`, dragonBlue `#658594`, oldWhite `#c8c093`, fujiWhite `#dcd7ba`, springViolet1 `#938aa9`, springBlue `#7fb4ca`, waveAqua2 `#7aa89f`, springGreen `#98bb6c`, carpYellow `#e6c384`, waveRed `#e46876`, katanaGray `#717c7c`, dragonBlack0 `#0d0c0c`, dragonBlack1 `#12120f`, dragonBlack2 `#1d1c19`, dragonBlack3 `#181616`, dragonBlack4 `#282727`, dragonBlack5 `#393836`, dragonBlack6 `#625e5a`, dragonWhite `#c5c9c5`, dragonGreen `#87a987`, dragonGreen2 `#8a9a7b`, dragonPink `#a292a3`, dragonOrange `#b6927b`, dragonOrange2 `#b98d7b`, dragonGray `#a6a69c`, dragonGray2 `#9e9b93`, dragonGray3 `#7a8382`, dragonBlue2 `#8ba4b0`, dragonViolet `#8992a7`, dragonRed `#c4746e`, dragonAqua `#8ea4a2`, dragonAsh `#737c73`, dragonTeal `#949fb5`, dragonYellow `#c4b28a`
- **Lotus:** sumiInk3 `#1f1f28`, lotusInk1 `#545464`, lotusInk2 `#43436c`, lotusGray `#dcd7ba`, lotusGray2 `#716e61`, lotusGray3 `#8a8980`, lotusWhite0 `#d5cea3`, lotusWhite1 `#dcd5ac`, lotusWhite2 `#e5ddb0`, lotusWhite3 `#f2ecbc`, lotusWhite4 `#e7dba0`, lotusWhite5 `#e4d794`, lotusViolet1 `#a09cac`, lotusViolet2 `#766b90`, lotusViolet3 `#c9cbd1`, lotusViolet4 `#624c83`, lotusBlue1 `#c7d7e0`, lotusBlue2 `#b5cbd2`, lotusBlue3 `#9fb5c9`, lotusBlue4 `#4d699b`, lotusBlue5 `#5d57a3`, lotusGreen `#6f894e`, lotusGreen2 `#6e915f`, lotusGreen3 `#b7d0ae`, lotusPink `#b35b79`, lotusOrange `#cc6d00`, lotusOrange2 `#e98a00`, lotusYellow `#77713f`, lotusYellow2 `#836f4a`, lotusYellow3 `#de9800`, lotusYellow4 `#f9d791`, lotusRed `#c84053`, lotusRed2 `#d7474b`, lotusRed3 `#e82424`, lotusRed4 `#d9a594`, lotusAqua `#597b75`, lotusAqua2 `#5e857a`, lotusTeal1 `#4e8ca2`, lotusTeal2 `#6693bf`, lotusTeal3 `#5a7785`, lotusCyan `#d7e3d8`

ANSI 0–15 (terminal slots, in order black … bright white):

| slot | Wave | Dragon | Lotus |
|---|---|---|---|
| 0 black | `#16161d` sumiInk0 | `#0d0c0c` dragonBlack0 | `#1f1f28` sumiInk3 |
| 1 red | `#c34043` autumnRed | `#c4746e` dragonRed | `#c84053` lotusRed |
| 2 green | `#76946a` autumnGreen | `#8a9a7b` dragonGreen2 | `#6f894e` lotusGreen |
| 3 yellow | `#c0a36e` boatYellow2 | `#c4b28a` dragonYellow | `#77713f` lotusYellow |
| 4 blue | `#7e9cd8` crystalBlue | `#8ba4b0` dragonBlue2 | `#4d699b` lotusBlue4 |
| 5 magenta | `#957fb8` oniViolet | `#a292a3` dragonPink | `#b35b79` lotusPink |
| 6 cyan | `#6a9589` waveAqua1 | `#8ea4a2` dragonAqua | `#597b75` lotusAqua |
| 7 white | `#c8c093` oldWhite | `#c8c093` oldWhite | `#545464` lotusInk1 |
| 8 br.black | `#727169` fujiGray | `#a6a69c` dragonGray | `#8a8980` lotusGray3 |
| 9 br.red | `#e82424` samuraiRed | `#e46876` waveRed | `#d7474b` lotusRed2 |
| 10 br.green | `#98bb6c` springGreen | `#87a987` dragonGreen | `#6e915f` lotusGreen2 |
| 11 br.yellow | `#e6c384` carpYellow | `#e6c384` carpYellow | `#836f4a` lotusYellow2 |
| 12 br.blue | `#7fb4ca` springBlue | `#7fb4ca` springBlue | `#6693bf` lotusTeal2 |
| 13 br.magenta | `#938aa9` springViolet1 | `#938aa9` springViolet1 | `#624c83` lotusViolet4 |
| 14 br.cyan | `#7aa89f` waveAqua2 | `#7aa89f` waveAqua2 | `#5e857a` lotusAqua2 |
| 15 br.white | `#dcd7ba` fujiWhite | `#c5c9c5` dragonWhite | `#43436c` lotusInk2 |

## Author's role rules

No prose style guide; the semantic table in [themes.lua](https://github.com/rebelot/kanagawa.nvim/blob/master/lua/kanagawa/themes.lua) acts as the spec: `ui.{fg, fg_dim, fg_reverse, bg_m3, bg_m2, bg_m1, bg, bg_p1, bg_p2, bg_gutter, nontext, bg_visual, bg_search}`, `ui.pmenu.{fg, bg, bg_sel, bg_sbar, bg_thumb}`, `ui.float.{fg, bg, fg_border}`, `diag.{error, warning, info, hint, ok}`, `vcs.{added, removed, changed}`, `syn.*`. The numbered **`bg_m3 … bg_p2` ladder is an explicit elevation scale** (m = below, p = above); floats sit at `bg_m3`. Each variant uses different palette names for the same roles (Wave sumiInk*, Dragon dragonBlack*, Lotus lotusWhite*).

## Token map

Cell = palette name, hex, contrast. Contrast is vs `bg.base` (for bg tokens it shows the step from the base), `selection.fg` is vs `selection.bg`, `fg.on-accent` is the lowest ratio over the accent and status fills. FAIL = below the [contrast floor](../formats.md#contrast-floors). *→ token* = unmapped tier-2 token resolved through its fallback; *derived* = computed hex (see Basis).

### Tier 1 (always mapped)

| token | Wave | Dragon | Lotus | basis |
|---|---|---|---|---|
| `bg.base` | sumiInk3 `#1f1f28` 1.00 | dragonBlack3 `#181616` 1.00 | lotusWhite3 `#f2ecbc` 1.00 | spec: themes.lua ui.bg |
| `bg.inset` | sumiInk0 `#16161d` 1.10 | dragonBlack0 `#0d0c0c` 1.08 | lotusWhite0 `#d5cea3` 1.33 | spec: ui.bg_m3 (lowest step of the bg_m3..bg_p2 ladder); consensus statusline bg sumiInk0 2/3 |
| `bg.surface` | sumiInk4 `#2a2a37` 1.16 | dragonBlack4 `#282727` 1.21 | lotusWhite4 `#e7dba0` 1.16 | spec: ui.bg_p1 (first raised step; also bg_gutter) |
| `bg.raised` | sumiInk5 `#363646` 1.38 | dragonBlack5 `#393836` 1.54 | lotusWhite5 `#e4d794` 1.21 | spec: ui.bg_p2 (second raised step; CursorLine) |
| `fg.default` | fujiWhite `#dcd7ba` 11.26 | dragonWhite `#c5c9c5` 10.76 | lotusInk1 `#545464` 6.19 | spec: ui.fg |
| `fg.muted` | oldWhite `#c8c093` 8.89 | oldWhite `#c8c093` 9.80 | lotusInk2 `#43436c` 7.75 | spec: ui.fg_dim |
| `fg.faint` | fujiGray `#727169` 3.33 | dragonAsh `#737c73` 4.17 | lotusGray3 `#8a8980` 2.93 FAIL | spec: syn.comment; consensus inactive/disabled fujiGray 3/3 (wave) |
| `fg.on-accent` | sumiInk0 `#16161d` 5.38 | dragonBlack0 `#0d0c0c` 4.96 | lotusGray `#dcd7ba` 1.79 FAIL | choice: ui.bg_m3 (darkest ladder step); spec ui.fg_reverse (waveBlue1) is below 4.5:1 on the error/info hues (varies by variant: see JSON) |
| `border.default` | sumiInk6 `#54546d` 2.23 | sumiInk6 `#54546d` 2.46 | lotusGray3 `#8a8980` 2.93 | spec: ui.float.fg_border (varies by variant: see JSON) |
| `accent.primary` | crystalBlue `#7e9cd8` 5.94 | dragonBlue2 `#8ba4b0` 6.90 | lotusBlue4 `#4d699b` 4.59 | consensus: accent crystalBlue 2/2 (wave); spec syn.fun |
| `accent.secondary` | oniViolet `#957fb8` 4.67 | dragonViolet `#8992a7` 5.78 | lotusViolet4 `#624c83` 6.07 | choice: syn.keyword violet (categorical contrast with the blue accent) |
| `selection.bg` | waveBlue2 `#2d4f67` 1.89 | waveBlue2 `#2d4f67` 2.08 | lotusViolet3 `#c9cbd1` 1.35 | spec: ui.pmenu.bg_sel (menu selection) (varies by variant: see JSON) |
| `status.error` | peachRed `#ff5d62` 5.44 | dragonRed `#c4746e` 5.21 | lotusRed3 `#e82424` 3.72 FAIL | spec: diag.error = samuraiRed (3.66:1, fails); peachRed (used for errors by 1/3 wave ports) passes (varies by variant: see JSON) |
| `status.warning` | roninYellow `#ff9e3b` 7.94 | roninYellow `#ff9e3b` 8.76 | lotusOrange2 `#e98a00` 2.16 FAIL | spec: diag.warning |
| `status.success` | springGreen `#98bb6c` 7.52 | springGreen `#98bb6c` 8.29 | lotusGreen `#6f894e` 3.26 FAIL | spec: diag.ok |
| `status.info` | waveAqua1 `#6a9589` 4.88 | dragonBlue `#658594` 4.58 | lotusTeal3 `#5a7785` 3.97 FAIL | spec: diag.info = dragonBlue (4.15:1, fails); waveAqua1 = diag.hint and wave's ANSI cyan, passes (varies by variant: see JSON) |

### Tier 2

| token | Wave | Dragon | Lotus | basis |
|---|---|---|---|---|
| `bg.overlay` | sumiInk0 `#16161d` 1.10 | dragonBlack0 `#0d0c0c` 1.08 | lotusWhite0 `#d5cea3` 1.33 | spec: ui.float.bg (floating windows sit at bg_m3) |
| `bg.stripe` | *→ bg.inset* `#16161d` 1.10 | *→ bg.inset* `#0d0c0c` 1.08 | *derived* `#ebe5b8` 1.06 | derived: bg.base darkened to 1.06:1 (weakest fill; bg.inset is too strong here, 1.33:1 vs inactive … |
| `fg.title` | *→ fg.default* `#dcd7ba` 11.26 | *→ fg.default* `#c5c9c5` 10.76 | *→ fg.default* `#545464` 6.19 | fallback |
| `border.focus` | *→ accent.primary* `#7e9cd8` 5.94 | *→ accent.primary* `#8ba4b0` 6.90 | *→ accent.primary* `#4d699b` 4.59 | fallback |
| `selection.fg` | *→ fg.default* `#dcd7ba` 5.97 | *→ fg.default* `#c5c9c5` 5.17 | *→ fg.default* `#545464` 4.58 | fallback |
| `selection.inactive.bg` | *→ bg.surface* `#2a2a37` 1.16 | *→ bg.surface* `#282727` 1.21 | *→ bg.surface* `#e7dba0` 1.16 | fallback |
| `text-selection.bg` | waveBlue1 `#223249` 1.26 | waveBlue1 `#223249` 1.39 | lotusViolet3 `#c9cbd1` 1.35 | spec: ui.bg_visual |
| `cursor.bg` | oldWhite `#c8c093` 8.89 | oldWhite `#c8c093` 9.80 | lotusInk2 `#43436c` 7.75 | port: extras/kitty cursor = oldWhite (varies by variant: see JSON) |
| `cursor.fg` | *→ bg.base* `#1f1f28` 1.00 | *→ bg.base* `#181616` 1.00 | lotusWhite3 `#f2ecbc` 1.00 | port: extras/kitty cursor_text_color = lotusWhite3 |
| `search.match` | *→ status.warning* `#ff9e3b` 7.94 | *→ status.warning* `#ff9e3b` 8.76 | *→ status.warning* `#e98a00` 2.16 | fallback |
| `link` | *→ accent.primary* `#7e9cd8` 5.94 | *→ accent.primary* `#8ba4b0` 6.90 | *→ accent.primary* `#4d699b` 4.59 | fallback |
| `keyhint.key` | *→ accent.primary* `#7e9cd8` 5.94 | *→ accent.primary* `#8ba4b0` 6.90 | *→ accent.primary* `#4d699b` 4.59 | fallback |
| `keyhint.desc` | *→ fg.muted* `#c8c093` 8.89 | *→ fg.muted* `#c8c093` 9.80 | *→ fg.muted* `#43436c` 7.75 | fallback |
| `statusbar.bg` | sumiInk0 `#16161d` 1.10 | dragonBlack0 `#0d0c0c` 1.08 | lotusWhite0 `#d5cea3` 1.33 | consensus: statusline bg sumiInk0 (= ui.bg_m3) 2/3 ports (wave) |
| `statusbar.fg` | *→ fg.muted* `#c8c093` 8.89 | *→ fg.muted* `#c8c093` 9.80 | *→ fg.muted* `#43436c` 7.75 | fallback |
| `tab.active.fg` | *→ accent.primary* `#7e9cd8` 5.94 | *→ accent.primary* `#8ba4b0` 6.90 | *→ accent.primary* `#4d699b` 4.59 | fallback |
| `tab.active.bg` | *→ bg.raised* `#363646` 1.38 | *→ bg.raised* `#393836` 1.54 | *→ bg.raised* `#e4d794` 1.21 | fallback |
| `tab.inactive.fg` | *→ fg.muted* `#c8c093` 8.89 | *→ fg.muted* `#c8c093` 9.80 | *→ fg.muted* `#43436c` 7.75 | fallback |
| `table.header` | *→ fg.default* `#dcd7ba` 11.26 | *→ fg.default* `#c5c9c5` 10.76 | *→ fg.default* `#545464` 6.19 | fallback |
| `mark` | *→ accent.secondary* `#957fb8` 4.67 | *→ accent.secondary* `#8992a7` 5.78 | *→ accent.secondary* `#624c83` 6.07 | fallback |
| `scrollbar.thumb` | waveBlue2 `#2d4f67` 1.89 | waveBlue2 `#2d4f67` 2.08 | lotusBlue2 `#b5cbd2` 1.41 | spec: ui.pmenu.bg_thumb |
| `scrollbar.track` | waveBlue1 `#223249` 1.26 | waveBlue1 `#223249` 1.39 | lotusBlue1 `#c7d7e0` 1.23 | spec: ui.pmenu.bg_sbar |
| `diff.added` | autumnGreen `#76946a` 4.84 | autumnGreen `#76946a` 5.33 | lotusGreen2 `#6e915f` 2.98 | spec: vcs.added |
| `diff.removed` | autumnRed `#c34043` 3.22 | autumnRed `#c34043` 3.55 | lotusRed2 `#d7474b` 3.58 | spec: vcs.removed |
| `diff.changed` | autumnYellow `#dca561` 7.47 | autumnYellow `#dca561` 8.24 | lotusYellow3 `#de9800` 2.04 | spec: vcs.changed |
| `ramp.low` | springGreen `#98bb6c` 7.52 | springGreen `#98bb6c` 8.29 | lotusGreen `#6f894e` 3.26 | cross-scheme: severity ramp |
| `ramp.mid` | roninYellow `#ff9e3b` 7.94 | roninYellow `#ff9e3b` 8.76 | lotusOrange2 `#e98a00` 2.16 | cross-scheme: severity ramp |
| `ramp.high` | peachRed `#ff5d62` 5.44 | dragonRed `#c4746e` 5.21 | lotusRed3 `#e82424` 3.72 | = status.error |

Derived hex values (computed, not palette entries; `blend(a, b, α)` = a composited over b at opacity α):

- Lotus: `bg.stripe` = `#ebe5b8` = see provenance

## Contrast findings

| variant | truecolor failures | 16-color failures (after overrides) | 256-color failures (OKLab nearest) |
|---|---|---|---|
| Wave | none | status.error 3.22, fg.on-accent 3.54 | status.info 4.30 |
| Dragon | none | none | none |
| Lotus | fg.faint 2.93, status.error 3.72, status.warning 2.16, status.success 3.26, status.info 3.97, fg.on-accent 1.79 | status.error 4.06, status.warning 4.15, status.success 3.26, fg.on-accent 3.26 | fg.faint 2.67, status.error 2.97, status.warning 2.12, status.success 3.05, status.info 3.37, accent.primary 4.49, keyhint.key 4.49, link 4.49, fg.on-accent 1.93 |

Rule for failures: the official mapping is kept unless the palette offers a same-role entry that passes (those swaps are listed in Basis). Where a status color fails, never rely on it alone: pair it with a glyph and a word (see [../color-tokens.md](../color-tokens.md#never-color-only)).

## 16-color mode

Per-theme `ansi16` overrides of the `_tokens.json` defaults (spec = `slot [attrs]`; ratio vs the terminal background in that mode):

| token | default | Wave | Dragon | Lotus |
|---|---|---|---|---|
| `fg.muted` | `default dim` | `7` 8.89 | `7` 9.80 | `7` 6.19 |
| `fg.faint` | `8` | · | · | `7` 6.19 |
| `fg.on-accent` | `bg` | `0` 3.54 | · | · |
| `accent.secondary` | `5` | · | · | `13` 6.07 |
| `status.success` | `2` | `10` 7.52 | · | · |
| `status.info` | `6` | · | · | `0` 13.62 |
| `keyhint.desc` | `default dim` | · | · | `7` 6.19 |
| `tab.active.fg` | `4 bold` | · | · | `bg bold` 6.19 |
| `tab.active.bg` | `default` | · | · | `10` 2.98 |
| `tab.inactive.fg` | `default dim` | · | · | `7` 6.19 |
| `mark` | `5` | · | · | `13` 6.07 |
| `diff.changed` | `4` | `3` 6.78 | `11` 10.73 | · |
| `ramp.low` | `2` | `10` 7.52 | · | · |

## Quirks and discrepancy decisions

- Discrepancy (ANSI 0): extras/alacritty wave sets black = #090618; extras/kitty and themes.lua term table set #16161d (sumiInk0). Kept #16161d (two sources agree). (Wave)
- cursor_text is undefined in the kitty port (null). (Wave, Dragon)
- Discrepancy (selection_foreground): extras/alacritty lotus uses #dcd7ba, extras/kitty #43436c. Kept kitty: #dcd7ba on the #c9cbd1 selection would be ~1.1:1. (Lotus)
- In Lotus ui.fg_dim (lotusInk2) is darker, i.e. higher contrast, than ui.fg: fg.muted follows the spec and is distinguished from fg.default by hue, not by lightness. (Lotus)

## App ports

O = official (scheme org or scheme repo extras), B = bundled in the app repo, C = community repo, - = none found (checked 2026-10).

| variant | helix | lazygit | k9s | btop | yazi | gitui | textual |
|---|---|---|---|---|---|---|---|
| Wave | B | - | B | B | C | - | - |
| Dragon | B | - | - | B | - | - | - |
| Lotus | B | - | - | B | - | - | - |
