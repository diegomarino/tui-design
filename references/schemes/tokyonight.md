# Tokyo Night (Night, Storm, Moon, Day): palette → token map

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [At a glance](#at-a-glance) · L15–29 — variant ids, appearance, base/text/accent hex, license and sources.
- [Palette (official hex)](#palette-official-hex) · L31–109 — the exact official hex of a named palette entry.
- [Author's role rules](#authors-role-rules) · L111–113 — the scheme author's own rules for what each colour is for.
- [Token map](#token-map) · L115–179 — the palette entry, hex and contrast behind each semantic token (tier 1 and tier 2).
- [Contrast findings](#contrast-findings) · L181–190 — which tokens fail a floor per variant, in truecolor, 16 and 256 colours.
- [16-color mode](#16-color-mode) · L192–206 — the per-variant `ansi16` overrides and their ratios.
- [Quirks and discrepancy decisions](#quirks-and-discrepancy-decisions) · L208–213 — where sources disagree and which value was kept, light-theme limits.
- [App ports](#app-ports) · L215–224 — whether helix, lazygit, k9s, btop, yazi, gitui or Textual ship a port of this scheme.

Read this when a TUI uses Tokyo Night and you need the exact palette entry, hex and contrast for each semantic token, the author's role rules, and the 16-color caveats. Token meanings: [../color-tokens.md](../color-tokens.md). All schemes: [../color-schemes.md](../color-schemes.md). Machine-readable: [`tokyonight-night.json`](../themes/tokyonight-night.json), [`tokyonight-storm.json`](../themes/tokyonight-storm.json), [`tokyonight-moon.json`](../themes/tokyonight-moon.json), [`tokyonight-day.json`](../themes/tokyonight-day.json).

## At a glance

| variant | id | appearance | bg.base | fg.default | accent.primary | license |
|---|---|---|---|---|---|---|
| Night | `tokyonight-night` | dark | `#1a1b26` | `#c0caf5` 10.59 | blue `#7aa2f7` | Apache-2.0 |
| Storm | `tokyonight-storm` | dark | `#24283b` | `#c0caf5` 9.02 | blue `#7aa2f7` | Apache-2.0 |
| Moon | `tokyonight-moon` | dark | `#222436` | `#c8d3f5` 10.26 | blue `#82aaff` | Apache-2.0 |
| Day | `tokyonight-day` | light | `#e1e2e7` | `#3760bf` 4.52 | blue `#2e7de9` | Apache-2.0 |

Sources:

- Night: palette <https://github.com/folke/tokyonight.nvim/blob/main/extras/lua/tokyonight_night.lua>; terminal <https://github.com/folke/tokyonight.nvim/blob/main/extras/kitty/tokyonight_night.conf>; role spec none published.
- Storm: palette <https://github.com/folke/tokyonight.nvim/blob/main/extras/lua/tokyonight_storm.lua>; terminal <https://github.com/folke/tokyonight.nvim/blob/main/extras/kitty/tokyonight_storm.conf>; role spec none published.
- Moon: palette <https://github.com/folke/tokyonight.nvim/blob/main/extras/lua/tokyonight_moon.lua>; terminal <https://github.com/folke/tokyonight.nvim/blob/main/extras/kitty/tokyonight_moon.conf>; role spec none published.
- Day: palette <https://github.com/folke/tokyonight.nvim/blob/main/extras/lua/tokyonight_day.lua>; terminal <https://github.com/folke/tokyonight.nvim/blob/main/extras/kitty/tokyonight_day.conf>; role spec none published.

## Palette (official hex)

| name | Night | Storm | Moon | Day |
|---|---|---|---|---|
| bg | `#1a1b26` | `#24283b` | `#222436` | `#e1e2e7` |
| bg_dark | `#16161e` | `#1f2335` | `#1e2030` | `#d0d5e3` |
| bg_dark1 | `#0c0e14` | `#1b1e2d` | `#191b29` | `#c1c9df` |
| bg_float | `#16161e` | `#1f2335` | `#1e2030` | `#d0d5e3` |
| bg_highlight | `#292e42` | `#292e42` | `#2f334d` | `#c4c8da` |
| bg_popup | `#16161e` | `#1f2335` | `#1e2030` | `#d0d5e3` |
| bg_search | `#3d59a1` | `#3d59a1` | `#3e68d7` | `#7890dd` |
| bg_sidebar | `#16161e` | `#1f2335` | `#1e2030` | `#d0d5e3` |
| bg_statusline | `#16161e` | `#1f2335` | `#1e2030` | `#d0d5e3` |
| bg_visual | `#283457` | `#2e3c64` | `#2d3f76` | `#b7c1e3` |
| black | `#15161e` | `#1d202f` | `#1b1d2b` | `#b4b5b9` |
| blue | `#7aa2f7` | `#7aa2f7` | `#82aaff` | `#2e7de9` |
| blue0 | `#3d59a1` | `#3d59a1` | `#3e68d7` | `#7890dd` |
| blue1 | `#2ac3de` | `#2ac3de` | `#65bcff` | `#188092` |
| blue2 | `#0db9d7` | `#0db9d7` | `#0db9d7` | `#07879d` |
| blue5 | `#89ddff` | `#89ddff` | `#89ddff` | `#006a83` |
| blue6 | `#b4f9f8` | `#b4f9f8` | `#b4f9f8` | `#2e5857` |
| blue7 | `#394b70` | `#394b70` | `#394b70` | `#92a6d5` |
| border | `#15161e` | `#1d202f` | `#1b1d2b` | `#b4b5b9` |
| border_highlight | `#27a1b9` | `#29a4bd` | `#589ed7` | `#4094a3` |
| comment | `#565f89` | `#565f89` | `#636da6` | `#848cb5` |
| cyan | `#7dcfff` | `#7dcfff` | `#86e1fc` | `#007197` |
| dark3 | `#545c7e` | `#545c7e` | `#545c7e` | `#8990b3` |
| dark5 | `#737aa2` | `#737aa2` | `#737aa2` | `#68709a` |
| diff.add | `#243e4a` | `#2b485a` | `#2a4556` | `#b7ced5` |
| diff.change | `#1f2231` | `#272d43` | `#252a3f` | `#d5d9e4` |
| diff.delete | `#4a272f` | `#52313f` | `#4b2a3d` | `#dababe` |
| diff.text | `#394b70` | `#394b70` | `#394b70` | `#92a6d5` |
| error | `#db4b4b` | `#db4b4b` | `#c53b53` | `#c64343` |
| fg | `#c0caf5` | `#c0caf5` | `#c8d3f5` | `#3760bf` |
| fg_dark | `#a9b1d6` | `#a9b1d6` | `#828bb8` | `#6172b0` |
| fg_float | `#c0caf5` | `#c0caf5` | `#c8d3f5` | `#3760bf` |
| fg_gutter | `#3b4261` | `#3b4261` | `#3b4261` | `#a8aecb` |
| fg_sidebar | `#a9b1d6` | `#a9b1d6` | `#828bb8` | `#6172b0` |
| git.add | `#449dab` | `#449dab` | `#b8db87` | `#4197a4` |
| git.change | `#6183bb` | `#6183bb` | `#7ca1f2` | `#506d9c` |
| git.delete | `#914c54` | `#914c54` | `#e26a75` | `#c47981` |
| git.ignore | `#545c7e` | `#545c7e` | `#545c7e` | `#8990b3` |
| green | `#9ece6a` | `#9ece6a` | `#c3e88d` | `#587539` |
| green1 | `#73daca` | `#73daca` | `#4fd6be` | `#387068` |
| green2 | `#41a6b5` | `#41a6b5` | `#41a6b5` | `#38919f` |
| hint | `#1abc9c` | `#1abc9c` | `#4fd6be` | `#118c74` |
| info | `#0db9d7` | `#0db9d7` | `#0db9d7` | `#07879d` |
| magenta | `#bb9af7` | `#bb9af7` | `#c099ff` | `#9854f1` |
| magenta2 | `#ff007c` | `#ff007c` | `#ff007c` | `#d20065` |
| orange | `#ff9e64` | `#ff9e64` | `#ff966c` | `#b15c00` |
| purple | `#9d7cd8` | `#9d7cd8` | `#fca7ea` | `#7847bd` |
| red | `#f7768e` | `#f7768e` | `#ff757f` | `#f52a65` |
| red1 | `#db4b4b` | `#db4b4b` | `#c53b53` | `#c64343` |
| teal | `#1abc9c` | `#1abc9c` | `#4fd6be` | `#118c74` |
| terminal_black | `#414868` | `#414868` | `#444a73` | `#a1a6c5` |
| todo | `#7aa2f7` | `#7aa2f7` | `#82aaff` | `#2e7de9` |
| warning | `#e0af68` | `#e0af68` | `#ffc777` | `#8c6c3e` |
| yellow | `#e0af68` | `#e0af68` | `#ffc777` | `#8c6c3e` |

ANSI 0–15 (terminal slots, in order black … bright white):

| slot | Night | Storm | Moon | Day |
|---|---|---|---|---|
| 0 black | `#15161e` black | `#1d202f` black | `#1b1d2b` black | `#b4b5b9` black |
| 1 red | `#f7768e` red | `#f7768e` red | `#ff757f` red | `#f52a65` red |
| 2 green | `#9ece6a` green | `#9ece6a` green | `#c3e88d` green | `#587539` green |
| 3 yellow | `#e0af68` warning | `#e0af68` warning | `#ffc777` warning | `#8c6c3e` warning |
| 4 blue | `#7aa2f7` blue | `#7aa2f7` blue | `#82aaff` blue | `#2e7de9` blue |
| 5 magenta | `#bb9af7` magenta | `#bb9af7` magenta | `#c099ff` magenta | `#9854f1` magenta |
| 6 cyan | `#7dcfff` cyan | `#7dcfff` cyan | `#86e1fc` cyan | `#007197` cyan |
| 7 white | `#a9b1d6` fg_dark | `#a9b1d6` fg_dark | `#828bb8` fg_dark | `#6172b0` fg_dark |
| 8 br.black | `#414868` terminal_black | `#414868` terminal_black | `#444a73` terminal_black | `#a1a6c5` terminal_black |
| 9 br.red | `#ff899d` | `#ff899d` | `#ff8d94` | `#ff4774` |
| 10 br.green | `#9fe044` | `#9fe044` | `#c7fb6d` | `#5c8524` |
| 11 br.yellow | `#faba4a` | `#faba4a` | `#ffd8ab` | `#a27629` |
| 12 br.blue | `#8db0ff` | `#8db0ff` | `#9ab8ff` | `#358aff` |
| 13 br.magenta | `#c7a9ff` | `#c7a9ff` | `#caabff` | `#a463ff` |
| 14 br.cyan | `#a4daff` | `#a4daff` | `#b2ebff` | `#007ea8` |
| 15 br.white | `#c0caf5` fg | `#c0caf5` fg | `#c8d3f5` fg | `#3760bf` fg |

## Author's role rules

No prose style guide; roles come from [colors/init.lua](https://github.com/folke/tokyonight.nvim/blob/main/lua/tokyonight/colors/init.lua) and [groups/base.lua](https://github.com/folke/tokyonight.nvim/blob/main/lua/tokyonight/groups/base.lua): `bg_sidebar = bg_statusline = bg_popup = bg_float = bg_dark` (floats sit *below* bg); CursorLine = bg_highlight; PmenuSel = blend(fg_gutter, 0.8); Visual = bg_visual; FloatBorder = border_highlight; WinSeparator = border (near-invisible); StatusLine = fg_sidebar on bg_statusline; TabLineSel = black on blue; Title = blue bold; LineNr = fg_gutter; dark5 = Conceal, inactive tab labels; `error = red1, warning = yellow, info = blue2, hint = teal`. Day is generated at runtime from Night (`Util.invert`).

## Token map

Cell = palette name, hex, contrast. Contrast is vs `bg.base` (for bg tokens it shows the step from the base), `selection.fg` is vs `selection.bg`, `fg.on-accent` is the lowest ratio over the accent and status fills. FAIL = below the [contrast floor](../formats.md#contrast-floors). *→ token* = unmapped tier-2 token resolved through its fallback; *derived* = computed hex (see Basis).

### Tier 1 (always mapped)

| token | Night | Storm | Moon | Day | basis |
|---|---|---|---|---|---|
| `bg.base` | bg `#1a1b26` 1.00 | bg `#24283b` 1.00 | bg `#222436` 1.00 | bg `#e1e2e7` 1.00 | spec: colors/init.lua bg |
| `bg.inset` | bg_dark `#16161e` 1.05 | bg_dark `#1f2335` 1.07 | bg_dark `#1e2030` 1.05 | bg_dark `#d0d5e3` 1.13 | spec: bg_sidebar = bg_statusline = bg_dark (default 'dark' sidebars) |
| `bg.surface` | bg_highlight `#292e42` 1.27 | bg_highlight `#292e42` 1.08 | bg_highlight `#2f334d` 1.24 | bg_highlight `#c4c8da` 1.29 | spec: CursorLine = bg_highlight; port: Textual surface ~ bg_highlight |
| `bg.raised` | *derived* `#343a55` 1.53 | *derived* `#363d59` 1.37 | *derived* `#363c58` 1.42 | *derived* `#b3b8d1` 1.52 | spec: PmenuSel bg = blend(fg_gutter, 0.8) over bg (also helix extras ui.menu.selected) |
| `fg.default` | fg `#c0caf5` 10.59 | fg `#c0caf5` 9.02 | fg `#c8d3f5` 10.26 | fg `#3760bf` 4.52 | spec: Normal fg |
| `fg.muted` | fg_dark `#a9b1d6` 8.10 | fg_dark `#a9b1d6` 6.90 | fg_dark `#828bb8` 4.61 | fg_dark `#6172b0` 3.57 FAIL | spec: fg_sidebar = fg_dark; StatusLine, MsgArea, ModeMsg use fg_dark |
| `fg.faint` | dark5 `#737aa2` 4.10 | dark5 `#737aa2` 3.49 | dark5 `#737aa2` 3.67 | dark5 `#68709a` 3.71 | spec: dark5 = Conceal, qfLineNr, inactive/hidden buffer and tab labels; comment (consensus 2/3) fails 3:1 … |
| `fg.on-accent` | black `#15161e` 6.81 | black `#1d202f` 6.11 | black `#1b1d2b` 6.45 | bg `#e1e2e7` 3.11 FAIL | spec: TabLineSel = black on blue (varies by variant: see JSON) |
| `border.default` | dark3 `#545c7e` 2.61 | dark3 `#545c7e` 2.23 | dark3 `#545c7e` 2.34 | dark3 `#8990b3` 2.42 | choice: single focus indicator (audit-checklist FS-09) — the ports use border_highlight (consensus 3/5), a … |
| `accent.primary` | blue `#7aa2f7` 6.79 | blue `#7aa2f7` 5.78 | blue `#82aaff` 6.66 | blue `#2e7de9` 3.11 FAIL | consensus: 2/3 ports (helix statusline.normal, yazi mode.normal); Directory/MoreMsg = blue |
| `accent.secondary` | magenta `#bb9af7` 7.39 | magenta `#bb9af7` 6.30 | magenta `#c099ff` 6.73 | magenta `#9854f1` 3.33 | port: Textual primary = magenta; choice |
| `selection.bg` | *derived* `#343a55` 1.53 | *derived* `#363d59` 1.37 | *derived* `#363c58` 1.42 | bg_highlight `#c4c8da` 1.29 | spec: PmenuSel bg = blend(fg_gutter, 0.8); ports btop/yazi/gitui use bg_highlight (3/6) (varies by variant: see JSON) |
| `status.error` | red `#f7768e` 6.46 | red `#f7768e` 5.51 | red `#ff757f` 5.90 | red1 `#c64343` 3.79 FAIL | spec: error = red1, but red1 fails 4.5:1 here; red (ANSI red; error in Textual/gitui ports 2/5) passes (varies by variant: see JSON) |
| `status.warning` | yellow `#e0af68` 8.55 | yellow `#e0af68` 7.28 | yellow `#ffc777` 9.96 | yellow `#8c6c3e` 3.75 FAIL | spec: warning = yellow |
| `status.success` | green `#9ece6a` 9.35 | green `#9ece6a` 7.97 | green `#c3e88d` 11.10 | green `#587539` 4.04 FAIL | port: Textual success = green; ANSI green |
| `status.info` | blue2 `#0db9d7` 7.27 | blue2 `#0db9d7` 6.20 | blue2 `#0db9d7` 6.51 | blue2 `#07879d` 3.27 FAIL | spec: info = blue2 |

### Tier 2

| token | Night | Storm | Moon | Day | basis |
|---|---|---|---|---|---|
| `bg.overlay` | bg_popup `#16161e` 1.05 | bg_popup `#1f2335` 1.07 | bg_popup `#1e2030` 1.05 | bg_popup `#d0d5e3` 1.13 | spec: Pmenu/NormalFloat bg = bg_popup/bg_float = bg_dark (floats sit below bg) |
| `bg.stripe` | *→ bg.inset* `#16161e` 1.05 | *derived* `#212536` 1.04 | *→ bg.inset* `#1e2030` 1.05 | *→ bg.inset* `#d0d5e3` 1.13 | derived: bg.base darkened to 1.04:1 (weakest fill; bg.inset is too strong here, 1.07:1 vs inactive … |
| `fg.title` | blue `#7aa2f7` 6.79 | blue `#7aa2f7` 5.78 | blue `#82aaff` 6.66 | blue `#2e7de9` 3.11 | spec: Title = blue bold |
| `border.focus` | orange `#ff9e64` 8.40 | orange `#ff9e64` 7.16 | orange `#ff966c` 7.16 | orange `#b15c00` 3.69 | port: official extras/lazygit activeBorderColor = orange, paired with border_highlight inactive (no … |
| `selection.fg` | fg `#c0caf5` 6.91 | fg `#c0caf5` 6.61 | fg `#c8d3f5` 7.25 | fg `#3760bf` 3.52 FAIL | spec: PmenuSel sets bg only (fg passes through) |
| `selection.inactive.bg` | *→ bg.surface* `#292e42` 1.27 | *→ bg.surface* `#292e42` 1.08 | *→ bg.surface* `#2f334d` 1.24 | *→ bg.surface* `#c4c8da` 1.29 | fallback |
| `text-selection.bg` | bg_visual `#283457` 1.40 | bg_visual `#2e3c64` 1.35 | bg_visual `#2d3f76` 1.52 | bg_visual `#b7c1e3` 1.38 | spec: Visual = bg_visual |
| `cursor.bg` | fg `#c0caf5` 10.59 | fg `#c0caf5` 9.02 | fg `#c8d3f5` 10.26 | fg `#3760bf` 4.52 | port: extras/kitty cursor = fg |
| `cursor.fg` | bg `#1a1b26` 1.00 | bg `#24283b` 1.00 | bg `#222436` 1.00 | bg `#e1e2e7` 1.00 | port: extras/kitty cursor_text_color = bg |
| `search.match` | *→ status.warning* `#e0af68` 8.55 | *→ status.warning* `#e0af68` 7.28 | *→ status.warning* `#ffc777` 9.96 | *→ status.warning* `#8c6c3e` 3.75 | fallback |
| `link` | green1 `#73daca` 10.26 | green1 `#73daca` 8.75 | green1 `#4fd6be` 8.51 | green1 `#387068` 4.40 FAIL | port: extras/kitty url_color = green1 |
| `keyhint.key` | orange `#ff9e64` 8.40 | orange `#ff9e64` 7.16 | orange `#ff966c` 7.16 | orange `#b15c00` 3.69 FAIL | consensus: 2/4 ports (Textual footer key = $accent, btop hi_fg) |
| `keyhint.desc` | *→ fg.muted* `#a9b1d6` 8.10 | *→ fg.muted* `#a9b1d6` 6.90 | *→ fg.muted* `#828bb8` 4.61 | *→ fg.muted* `#6172b0` 3.57 | fallback |
| `statusbar.bg` | bg_statusline `#16161e` 1.05 | bg_statusline `#1f2335` 1.07 | bg_statusline `#1e2030` 1.05 | bg_statusline `#d0d5e3` 1.13 | spec: StatusLine bg = bg_statusline |
| `statusbar.fg` | fg_sidebar `#a9b1d6` 8.10 | fg_sidebar `#a9b1d6` 6.90 | fg_sidebar `#828bb8` 4.61 | fg_sidebar `#6172b0` 3.57 | spec: StatusLine fg = fg_sidebar |
| `tab.active.fg` | black `#15161e` 1.05 | black `#1d202f` 1.11 | black `#1b1d2b` 1.09 | bg `#e1e2e7` 1.00 | spec: TabLineSel = black on blue (varies by variant: see JSON) |
| `tab.active.bg` | blue `#7aa2f7` 6.79 | blue `#7aa2f7` 5.78 | blue `#82aaff` 6.66 | blue `#2e7de9` 3.11 | spec: TabLineSel = black on blue |
| `tab.inactive.fg` | *→ fg.muted* `#a9b1d6` 8.10 | *→ fg.muted* `#a9b1d6` 6.90 | *→ fg.muted* `#828bb8` 4.61 | *→ fg.muted* `#6172b0` 3.57 | fallback |
| `table.header` | *→ fg.default* `#c0caf5` 10.59 | *→ fg.default* `#c0caf5` 9.02 | *→ fg.default* `#c8d3f5` 10.26 | *→ fg.default* `#3760bf` 4.52 | fallback |
| `mark` | *→ accent.secondary* `#bb9af7` 7.39 | *→ accent.secondary* `#bb9af7` 6.30 | *→ accent.secondary* `#c099ff` 6.73 | *→ accent.secondary* `#9854f1` 3.33 | fallback |
| `scrollbar.thumb` | fg_gutter `#3b4261` 1.74 | fg_gutter `#3b4261` 1.48 | fg_gutter `#3b4261` 1.56 | fg_gutter `#a8aecb` 1.69 | spec: PmenuThumb = fg_gutter |
| `scrollbar.track` | *→ border.default* `#545c7e` 2.61 | *→ border.default* `#545c7e` 2.23 | *→ border.default* `#545c7e` 2.34 | *→ border.default* `#8990b3` 2.42 | fallback |
| `diff.added` | green `#9ece6a` 9.35 | green `#9ece6a` 7.97 | green `#c3e88d` 11.10 | green `#587539` 4.04 | consensus: 2/3 ports (yazi marker_copied, gitui diff_line_add) |
| `diff.removed` | red `#f7768e` 6.46 | red `#f7768e` 5.51 | red `#ff757f` 5.90 | red `#f52a65` 3.01 | consensus: 2/3 ports (yazi marker_cut, gitui diff_line_delete) |
| `diff.changed` | yellow `#e0af68` 8.55 | yellow `#e0af68` 7.28 | yellow `#ffc777` 9.96 | yellow `#8c6c3e` 3.75 | port: extras/gitui diff_file_modified = yellow |
| `ramp.low` | green `#9ece6a` 9.35 | green `#9ece6a` 7.97 | green `#c3e88d` 11.10 | green `#587539` 4.04 | port: extras/btop cpu/temp gradients green->yellow->red |
| `ramp.mid` | yellow `#e0af68` 8.55 | yellow `#e0af68` 7.28 | yellow `#ffc777` 9.96 | yellow `#8c6c3e` 3.75 | port: extras/btop gradients |
| `ramp.high` | red `#f7768e` 6.46 | red `#f7768e` 5.51 | red `#ff757f` 5.90 | red1 `#c64343` 3.79 | port: extras/btop gradients (varies by variant: see JSON) |

Derived hex values (computed, not palette entries; `blend(a, b, α)` = a composited over b at opacity α):

- Night: `bg.raised`, `selection.bg` = `#343a55` = blend(fg_gutter, bg, 0.8)
- Storm: `bg.raised`, `selection.bg` = `#363d59` = blend(fg_gutter, bg, 0.8)
- Storm: `bg.stripe` = `#212536` = see provenance
- Moon: `bg.raised`, `selection.bg` = `#363c58` = blend(fg_gutter, bg, 0.8)
- Day: `bg.raised` = `#b3b8d1` = blend(fg_gutter, bg, 0.8)

## Contrast findings

| variant | truecolor failures | 16-color failures (after overrides) | 256-color failures (OKLab nearest) |
|---|---|---|---|
| Night | none | none | none |
| Storm | none | none | none |
| Moon | none | none | fg.muted 4.41 |
| Day | fg.muted 3.57, status.error 3.79, status.warning 3.75, status.success 4.04, status.info 3.27, accent.primary 3.11, keyhint.key 3.69, link 4.40, selection.fg 3.52, fg.on-accent 3.11 | status.error 3.01, status.warning 3.75, status.success 4.04, status.info 4.26, accent.primary 3.11, keyhint.key 3.15, link 3.11, fg.on-accent 3.01 | fg.muted 4.41, status.error 4.25, status.success 3.23, status.info 3.25, accent.primary 2.79, keyhint.key 3.70, selection.fg 3.78, fg.on-accent 2.79 |

Rule for failures: the official mapping is kept unless the palette offers a same-role entry that passes (those swaps are listed in Basis). Where a status color fails, never rely on it alone: pair it with a glyph and a word (see [../color-tokens.md](../color-tokens.md#never-color-only)).

## 16-color mode

Per-theme `ansi16` overrides of the `_tokens.json` defaults (spec = `slot [attrs]`; ratio vs the terminal background in that mode):

| token | default | Night | Storm | Moon | Day |
|---|---|---|---|---|---|
| `fg.muted` | `default dim` | `7` 8.10 | `7` 6.90 | `7` 4.61 | `15` 4.52 |
| `fg.faint` | `8` | `default dim` 4.10 | `default dim` 3.80 | `default dim` 4.13 | `7` 3.57 |
| `border.focus` | `4` | `3` 8.55 | `3` 7.28 | · | `11` 3.15 |
| `keyhint.key` | `4` | `3` 8.55 | `3` 7.28 | · | `11` 3.15 |
| `keyhint.desc` | `default dim` | · | · | · | `7` 3.57 |
| `tab.active.fg` | `4 bold` | `bg bold` 10.59 | `bg bold` 9.02 | `bg bold` 10.26 | `bg bold` 4.52 |
| `tab.active.bg` | `default` | `4` 6.79 | `4` 5.78 | `4` 6.66 | `4` 3.11 |
| `tab.inactive.fg` | `default dim` | · | · | · | `7` 3.57 |
| `diff.changed` | `4` | `3` 8.55 | `3` 7.28 | `3` 9.96 | `3` 3.75 |

## Quirks and discrepancy decisions

- Bright ANSI 9-14 are generated (Util.brighten), not palette names. (Night, Storm, Moon)
- status.error uses `red`: the spec's error color red1 fails 4.5:1 on this background (night 4.17, storm 3.55, moon 3.00). (Night, Storm, Moon)
- Day is computed at runtime (Util.invert of night); extras/lua/tokyonight_day.lua is the only static source. (Day)
- Light-theme limit: fg_dark, red1, yellow, green and blue2 all sit between 3.0:1 and 4.5:1 on bg #e1e2e7; no same-role entry passes. (Day)

## App ports

O = official (scheme org or scheme repo extras), B = bundled in the app repo, C = community repo, - = none found (checked 2026-10).

| variant | helix | lazygit | k9s | btop | yazi | gitui | textual |
|---|---|---|---|---|---|---|---|
| Night | O | O | - | O | O | O | B |
| Storm | O | O | - | O | O | O | - |
| Moon | O | O | - | O | O | O | - |
| Day | O | O | - | O | O | O | - |
