# Color schemes: the 25 most-used variants mapped to tokens

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [How to choose](#how-to-choose) · L12–21 — picking a scheme for a need (max contrast, light, the user's terminal scheme, what to avoid).
- [All variants](#all-variants) · L23–53 — every variant id with bg, fg, accent, floors passed, license, ports and what it suits.
- [Key tokens at a glance (truecolor hex)](#key-tokens-at-a-glance-truecolor-hex) · L55–85 — a key token's hex in any variant, side by side.
- [Cross-scheme patterns](#cross-scheme-patterns) · L87–93 — what fails across schemes (light status hues, faint greys, ANSI slot names) and what to do.
- [Using a theme](#using-a-theme) · L95–100 — loading, checking, previewing, exporting a theme or naming it in a `.mock`.

Read this when you pick a color scheme for a TUI, need the hex for a semantic token in a named scheme, or must know which schemes survive contrast checks. Token meanings and design rules: [color-tokens.md](color-tokens.md). Per-scheme detail (full palette, author rules, every token, 16-color overrides, quirks): the `schemes/` pages linked below. Machine-readable themes: `themes/<id>.json` (load with `SKILL_DIR/scripts/_theme.py`).

## How to choose

| need | pick | why |
|---|---|---|
| one safe dark default | `catppuccin-mocha` | complete author spec, official ports for helix/lazygit/k9s/btop/yazi/gitui, every floor passes |
| dark + light pair that both pass most floors | `gruvbox-dark` + `gruvbox-light` | only error (dark 4.29) and success/info (light 4.29/4.40) are short |
| maximum contrast dark | `dracula-classic`, `catppuccin-mocha`, `kanagawa-wave` | body text 13.4 / 11.3 / 11.3:1, every truecolor floor passes |
| light theme with readable status colors | `dracula-alucard` | the only light variant where every floor passes |
| user already runs scheme X in the terminal | X's variant with `ansi16` overrides, or render in 16-color mode | the terminal palette is the user's; see [color-tokens.md](color-tokens.md#16-color-and-256-color) |
| avoid for dense text | `solarized-light` (body 4.13), `tokyonight-day` (4.52), `everforest-light`, `rose-pine-dawn`, `kanagawa-lotus` | accents below 4.5:1, greys below 3:1 |

## All variants

Ports: helix · lazygit · k9s · btop · yazi · gitui · Textual (O official, B bundled in the app, C community, - none). Pass = [contrast floors](formats.md#contrast-floors) met, as `truecolor · 16-color /18` checks (e.g. `7 · 8 /18` = 7 pass in truecolor, 8 in 16-color mode).

| scheme | variant (id) | mode | bg | fg | accent.primary | pass (TC · 16 /18) | license | ports | good for |
|---|---|---|---|---|---|---|---|---|---|
| [Catppuccin](schemes/catppuccin.md) | Latte (`catppuccin-latte`) | light | `#eff1f5` | `#4c4f69` 7.1 | blue `#1e66f5` | 7 · 8 /18 | MIT | `OOOOOOB` | light companion to Mocha; pastel accents are weak as text, fine as fills/glyphs |
| [Catppuccin](schemes/catppuccin.md) | Frappé (`catppuccin-frappe`) | dark | `#303446` | `#c6d0f5` 8.1 | blue `#8caaee` | 18 · 18 /18 | MIT | `OOOOOOB` | mid-dark, softer than Mocha; every floor passes |
| [Catppuccin](schemes/catppuccin.md) | Macchiato (`catppuccin-macchiato`) | dark | `#24273a` | `#cad3f5` 9.9 | blue `#8aadf4` | 18 · 18 /18 | MIT | `OOOOOOB` | mid-dark between Frappé and Mocha; every floor passes |
| [Catppuccin](schemes/catppuccin.md) | Mocha (`catppuccin-mocha`) | dark | `#1e1e2e` | `#cdd6f4` 11.3 | blue `#89b4fa` | 18 · 18 /18 | MIT | `OOOOOOB` | default dark pick: full spec, 7 official app ports, every floor passes |
| [Dracula](schemes/dracula.md) | Dracula (`dracula-classic`) | dark | `#282a36` | `#f8f8f2` 13.4 | purple `#bd93f9` | 18 · 18 /18 | MIT | `BOBBO-B` | high-saturation dark; every floor passes (muted is a derived blend) |
| [Dracula](schemes/dracula.md) | Alucard (`dracula-alucard`) | light | `#fffbeb` | `#1f1f1f` 15.9 | purple `#644ac9` | 18 · 18 /18 | MIT | `-------` | warm light; every floor passes, but no app ports exist |
| [Nord](schemes/nord.md) | Dark (`nord-dark`) | dark | `#2e3440` | `#d8dee9` 9.2 | nord8 `#88c0d0` | 15 · 16 /18 | MIT | `B-BB--B` | calm low-saturation dark; weak greys (nord3) and error red |
| [Gruvbox](schemes/gruvbox.md) | Dark (`gruvbox-dark`) | dark | `#282828` | `#ebdbb2` 10.7 | bright_blue `#83a598` | 16 · 16 /18 | MIT | `B-BBC-B` | warm retro dark with a solid light twin; only error red is short |
| [Gruvbox](schemes/gruvbox.md) | Light (`gruvbox-light`) | light | `#fbf1c7` | `#3c3836` 10.2 | faded_blue `#076678` | 14 · 12 /18 | MIT | `B-BB---` | warm light with good body contrast; success/info near-miss |
| [Tokyo Night](schemes/tokyonight.md) | Night (`tokyonight-night`) | dark | `#1a1b26` | `#c0caf5` 10.6 | blue `#7aa2f7` | 18 · 18 /18 | Apache-2.0 | `OO-OOOB` | cool deep dark; complete official extras; every floor passes |
| [Tokyo Night](schemes/tokyonight.md) | Storm (`tokyonight-storm`) | dark | `#24283b` | `#c0caf5` 9.0 | blue `#7aa2f7` | 18 · 18 /18 | Apache-2.0 | `OO-OOO-` | lighter navy Tokyo Night; every floor passes |
| [Tokyo Night](schemes/tokyonight.md) | Moon (`tokyonight-moon`) | dark | `#222436` | `#c8d3f5` 10.3 | blue `#82aaff` | 18 · 18 /18 | Apache-2.0 | `OO-OOO-` | brighter, more saturated Tokyo Night; every floor passes |
| [Tokyo Night](schemes/tokyonight.md) | Day (`tokyonight-day`) | light | `#e1e2e7` | `#3760bf` 4.5 | blue `#2e7de9` | 4 · 6 /18 | Apache-2.0 | `OO-OOO-` | light Tokyo Night; low contrast (body text 4.52:1), avoid for dense text |
| [Rosé Pine](schemes/rose-pine.md) | main (`rose-pine-main`) | dark | `#191724` | `#e0def4` 13.4 | iris `#c4a7e7` | 16 · 16 /18 | MIT | `OOBOO-B` | muted elegant dark; success (pine) is 3.38:1, use glyphs |
| [Rosé Pine](schemes/rose-pine.md) | Moon (`rose-pine-moon`) | dark | `#232136` | `#e0def4` 11.9 | iris `#c4a7e7` | 16 · 16 /18 | MIT | `OOBOO-B` | lighter Rosé Pine dark; success (pine) 4.29:1 |
| [Rosé Pine](schemes/rose-pine.md) | Dawn (`rose-pine-dawn`) | light | `#faf4ed` | `#575279` 6.7 | iris `#907aa9` | 6 · 9 /18 | MIT | `OOBOO-B` | soft light; most accents below 4.5:1, decorative use only |
| [Kanagawa](schemes/kanagawa.md) | Wave (`kanagawa-wave`) | dark | `#1f1f28` | `#dcd7ba` 11.3 | crystalBlue `#7e9cd8` | 18 · 16 /18 | MIT | `B-BBC--` | ink-and-paper dark with an explicit elevation ladder; floors pass after fixes |
| [Kanagawa](schemes/kanagawa.md) | Dragon (`kanagawa-dragon`) | dark | `#181616` | `#c5c9c5` 10.8 | dragonBlue2 `#8ba4b0` | 18 · 18 /18 | MIT | `B--B---` | darker, desaturated Kanagawa; floors pass after fixes |
| [Kanagawa](schemes/kanagawa.md) | Lotus (`kanagawa-lotus`) | light | `#f2ecbc` | `#545464` 6.2 | lotusBlue4 `#4d699b` | 8 · 12 /18 | MIT | `B--B---` | parchment light; accents and status colors below 4.5:1 |
| [Everforest](schemes/everforest.md) | Dark (`everforest-dark`) | dark | `#2d353b` | `#d3c6aa` 7.4 | green `#a7c080` | 18 · 18 /18 | MIT | `B-BBC--` | soft green-grey dark; every floor passes |
| [Everforest](schemes/everforest.md) | Light (`everforest-light`) | light | `#fdf6e3` | `#5c6a72` 5.2 | green `#8da101` | 3 · 5 /18 | MIT | `B-BB---` | soft light; nearly every accent fails 4.5:1, chrome-only |
| [Solarized](schemes/solarized.md) | Dark (`solarized-dark`) | dark | `#002b36` | `#839496` 4.7 | blue `#268bd2` | 10 · 12 /18 | MIT | `B-BB--B` | classic low-contrast dark; body 4.75:1, secondary text 2.79:1 |
| [Solarized](schemes/solarized.md) | Light (`solarized-light`) | light | `#fdf6e3` | `#657b83` 4.1 | blue `#268bd2` | 5 · 6 /18 | MIT | `B-BB--B` | classic light; body text 4.13:1 fails AA, avoid for dense text |
| [One Dark / One Light](schemes/onedark.md) | Dark (`onedark-dark`) | dark | `#282c34` | `#abb2bf` 6.6 | blue `#61afef` | 15 · 16 /18 | MIT | `B-BB--B` | familiar Atom/VS Code dark; faint grey and red short |
| [One Dark / One Light](schemes/onedark.md) | Light (`onedark-light`) | light | `#fafafa` | `#383a42` 10.9 | syntax_accent `#526fff` | 9 · 10 /18 | MIT | `B-B---B` | Atom One Light; derived hexes, no official terminal palette |

## Key tokens at a glance (truecolor hex)

| id | `bg.inset` | `bg.base` | `bg.surface` | `bg.raised` | `selection.bg` | `border.default` | `fg.faint` | `fg.muted` | `fg.default` | `accent.primary` | `status.error` | `status.warning` | `status.success` | `status.info` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `catppuccin-latte` | `#e6e9ef` | `#eff1f5` | `#ccd0da` | `#bcc0cc` | `#d2d4dc` | `#9ca0b0` | `#7c7f93` | `#5c5f77` | `#4c4f69` | `#1e66f5` | `#d20f39` | `#df8e1d` | `#40a02b` | `#179299` |
| `catppuccin-frappe` | `#292c3c` | `#303446` | `#414559` | `#51576d` | `#494e63` | `#737994` | `#838ba7` | `#a5adce` | `#c6d0f5` | `#8caaee` | `#e78284` | `#e5c890` | `#a6d189` | `#81c8be` |
| `catppuccin-macchiato` | `#1e2030` | `#24273a` | `#363a4f` | `#494d64` | `#404459` | `#6e738d` | `#8087a2` | `#a5adcb` | `#cad3f5` | `#8aadf4` | `#ed8796` | `#eed49f` | `#a6da95` | `#8bd5ca` |
| `catppuccin-mocha` | `#181825` | `#1e1e2e` | `#313244` | `#45475a` | `#3b3d4f` | `#6c7086` | `#7f849c` | `#a6adc8` | `#cdd6f4` | `#89b4fa` | `#f38ba8` | `#f9e2af` | `#a6e3a1` | `#94e2d5` |
| `dracula-classic` | `#21222c` | `#282a36` | `#343746` | `#424450` | `#44475a` | `#6272a4` | `#6272a4` | `#a5a6a7` | `#f8f8f2` | `#bd93f9` | `#ff5555` | `#ffb86c` | `#50fa7b` | `#8be9fd` |
| `dracula-alucard` | `#ceccc0` | `#fffbeb` | `#dedccf` | `#ece9df` | `#cfcfde` | `#bcbab3` | `#6c664b` | `#6c664b` | `#1f1f1f` | `#644ac9` | `#cb3a2a` | `#a34d14` | `#14710a` | `#036a96` |
| `nord-dark` | `#2e3440` | `#2e3440` | `#3b4252` | `#434c5e` | `#434c5e` | `#4c566a` | `#4c566a` | `#9ca2ae` | `#d8dee9` | `#88c0d0` | `#bf616a` | `#ebcb8b` | `#a3be8c` | `#88c0d0` |
| `gruvbox-dark` | `#1d2021` | `#282828` | `#3c3836` | `#504945` | `#665c54` | `#665c54` | `#928374` | `#a89984` | `#ebdbb2` | `#83a598` | `#fb4934` | `#fabd2f` | `#b8bb26` | `#8ec07c` |
| `gruvbox-light` | `#f9f5d7` | `#fbf1c7` | `#ebdbb2` | `#d5c4a1` | `#bdae93` | `#bdae93` | `#928374` | `#665c54` | `#3c3836` | `#076678` | `#9d0006` | `#af3a03` | `#79740e` | `#427b58` |
| `tokyonight-night` | `#16161e` | `#1a1b26` | `#292e42` | `#343a55` | `#343a55` | `#545c7e` | `#737aa2` | `#a9b1d6` | `#c0caf5` | `#7aa2f7` | `#f7768e` | `#e0af68` | `#9ece6a` | `#0db9d7` |
| `tokyonight-storm` | `#1f2335` | `#24283b` | `#292e42` | `#363d59` | `#363d59` | `#545c7e` | `#737aa2` | `#a9b1d6` | `#c0caf5` | `#7aa2f7` | `#f7768e` | `#e0af68` | `#9ece6a` | `#0db9d7` |
| `tokyonight-moon` | `#1e2030` | `#222436` | `#2f334d` | `#363c58` | `#363c58` | `#545c7e` | `#737aa2` | `#828bb8` | `#c8d3f5` | `#82aaff` | `#ff757f` | `#ffc777` | `#c3e88d` | `#0db9d7` |
| `tokyonight-day` | `#d0d5e3` | `#e1e2e7` | `#c4c8da` | `#b3b8d1` | `#c4c8da` | `#8990b3` | `#68709a` | `#6172b0` | `#3760bf` | `#2e7de9` | `#c64343` | `#8c6c3e` | `#587539` | `#07879d` |
| `rose-pine-main` | `#191724` | `#191724` | `#1f1d2e` | `#26233a` | `#403d52` | `#524f67` | `#6e6a86` | `#908caa` | `#e0def4` | `#c4a7e7` | `#eb6f92` | `#f6c177` | `#31748f` | `#9ccfd8` |
| `rose-pine-moon` | `#232136` | `#232136` | `#2a273f` | `#393552` | `#44415a` | `#56526e` | `#6e6a86` | `#908caa` | `#e0def4` | `#c4a7e7` | `#eb6f92` | `#f6c177` | `#3e8fb0` | `#9ccfd8` |
| `rose-pine-dawn` | `#faf4ed` | `#faf4ed` | `#fffaf3` | `#f2e9e1` | `#dfdad9` | `#cecacd` | `#9893a5` | `#797593` | `#575279` | `#907aa9` | `#b4637a` | `#ea9d34` | `#286983` | `#56949f` |
| `kanagawa-wave` | `#16161d` | `#1f1f28` | `#2a2a37` | `#363646` | `#2d4f67` | `#54546d` | `#727169` | `#c8c093` | `#dcd7ba` | `#7e9cd8` | `#ff5d62` | `#ff9e3b` | `#98bb6c` | `#6a9589` |
| `kanagawa-dragon` | `#0d0c0c` | `#181616` | `#282727` | `#393836` | `#2d4f67` | `#54546d` | `#737c73` | `#c8c093` | `#c5c9c5` | `#8ba4b0` | `#c4746e` | `#ff9e3b` | `#98bb6c` | `#658594` |
| `kanagawa-lotus` | `#d5cea3` | `#f2ecbc` | `#e7dba0` | `#e4d794` | `#c9cbd1` | `#8a8980` | `#8a8980` | `#43436c` | `#545464` | `#4d699b` | `#e82424` | `#e98a00` | `#6f894e` | `#5a7785` |
| `everforest-dark` | `#232a2e` | `#2d353b` | `#343f44` | `#475258` | `#a7c080` | `#4f585e` | `#7a8478` | `#9da9a0` | `#d3c6aa` | `#a7c080` | `#e67e80` | `#dbbc7f` | `#a7c080` | `#7fbbb3` |
| `everforest-light` | `#efebd4` | `#fdf6e3` | `#f4f0d9` | `#e6e2cc` | `#eaedc8` | `#e0dcc7` | `#a6b0a0` | `#829181` | `#5c6a72` | `#8da101` | `#f85552` | `#dfa000` | `#8da101` | `#3a94c5` |
| `solarized-dark` | `#002b36` | `#002b36` | `#073642` | `#073642` | `#073642` | `#586e75` | `#586e75` | `#586e75` | `#839496` | `#268bd2` | `#dc322f` | `#b58900` | `#859900` | `#2aa198` |
| `solarized-light` | `#fdf6e3` | `#fdf6e3` | `#eee8d5` | `#eee8d5` | `#eee8d5` | `#93a1a1` | `#93a1a1` | `#93a1a1` | `#657b83` | `#268bd2` | `#dc322f` | `#b58900` | `#859900` | `#2aa198` |
| `onedark-dark` | `#282c34` | `#282c34` | `#2c323c` | `#3e4452` | `#61afef` | `#3e4452` | `#5c6370` | `#9197a3` | `#abb2bf` | `#61afef` | `#e06c75` | `#e5c07b` | `#98c379` | `#56b6c2` |
| `onedark-light` | `#fafafa` | `#fafafa` | `#f0f0f1` | `#e5e5e6` | `#e5e5e6` | `#d3d4d5` | `#a0a1a7` | `#696c77` | `#383a42` | `#526fff` | `#ca1243` | `#986801` | `#50a14f` | `#0184bc` |

Palette names, contrast ratios and the remaining 29 tokens are in each scheme page.

## Cross-scheme patterns

| pattern | evidence | consequence for designs |
|---|---|---|
| Light variants fail status floors | Latte, Day, Dawn, Lotus, Everforest Light, Solarized Light, One Light: yellow/green/cyan at 2.0-3.5:1 | in light themes treat status hues as glyph/fill colors; carry meaning with words and icons; prefer `dracula-alucard` or `gruvbox-light` when status text matters |
| Secondary greys are the weakest link | Nord nord3 1.69, One Dark comment 2.32, Solarized base01 2.79, Tokyo Night comment 2.76 | use `fg.muted` for anything readable; reserve `fg.faint` for decoration, disabled items, line numbers |
| ANSI slot name != hue | Dracula blue = purple; Rosé Pine green = pine, blue = foam, cyan = rose; Solarized 8-15 = monotones | in 16-color mode use the theme's `ansi16` overrides, never `blue` by name |

## Using a theme

- Load: `from _theme import load_theme; t = load_theme('rose-pine-moon'); t.hex('status.info')` (tier-2 fallbacks resolved).
- Check: `python3 SKILL_DIR/scripts/contrast_check.py rose-pine-moon --depth 16`. Preview: `python3 SKILL_DIR/scripts/preview_theme.py rose-pine-moon`.
- Export: `python3 SKILL_DIR/scripts/export_theme.py rose-pine-moon --target textual|ink|lipgloss|ratatui|gum|css|json`.
- Mockups: `#! theme: rose-pine-moon` in a `.mock` header, or `python3 SKILL_DIR/scripts/render_mockup.py FILE --theme rose-pine-moon`.
