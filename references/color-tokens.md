# Color tokens: the semantic layer between palettes and widgets

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [The 44 tokens](#the-44-tokens) · L15–62 — the token list and what each means.
- [The neutral ladder](#the-neutral-ladder) · L64–78 — the fg/bg greys and their order.
- [Design rules](#design-rules) · L80–162 — selection, focus, elevation, stripes, chips, adaptive light/dark.
- [Token → theme-system keys](#token--theme-system-keys) · L164–223 — mapping tokens onto an app's or library's theme keys.
- [16-color and 256-color](#16-color-and-256-color) · L225–237 — how tokens degrade to 16 and 256 colours.
- [Contrast floors](#contrast-floors) · L239–241 — pointer to the floor values.
- [Adding a theme](#adding-a-theme) · L243–245 — writing a new theme.

Read this when you choose colors for a TUI, write or review a theme, map a color scheme onto widgets, or audit color use in a screen.
Never put a raw hex in a widget: name the role (token), then resolve it through a theme in `themes/<id>.json`. Scheme-by-scheme values: [color-schemes.md](color-schemes.md) and `schemes/<scheme>.md`.

## The 44 tokens

Source of truth: [`themes/_tokens.json`](themes/_tokens.json). Tier 1 is mapped explicitly in every theme; tier 2 falls back to the listed token when a theme has no evidence for it. Ladder = position on the neutral ladder below (N0-N6) or the hue family. Example = `catppuccin-mocha`.

| token | tier | role | fallback | ladder / family | Mocha example |
|---|---|---|---|---|---|
| `bg.base` | 1 | app background; most panes sit on it | - | N1 | base `#1e1e2e` |
| `bg.inset` | 1 | below-base chrome: header/status bands, sidebars | - | N0 | mantle `#181825` |
| `bg.surface` | 1 | raised fill: filled panels, inputs, popups, cursor line | - | N2 | surface0 `#313244` |
| `bg.raised` | 1 | highest neutral fill: neutral selection, hover, active tab bg | - | N3 | surface1 `#45475a` |
| `bg.overlay` | 2 | floating layers (modal, dropdown, toast) when they differ from surface | `bg.surface` | N2 (or N0 in schemes whose floats sit below base) | surface0 `#313244` |
| `bg.stripe` | 2 | zebra-stripe fill on alternate records; the weakest fill, never meaning-bearing ([rule](#zebra-stripes-the-weakest-fill)) | `bg.inset` | N0 (dark: below base) | mantle `#181825` |
| `fg.default` | 1 | body text | - | N6 | text `#cdd6f4` |
| `fg.muted` | 1 | secondary text: labels, descriptions, timestamps, unfocused pane text | - | N5 | subtext0 `#a6adc8` |
| `fg.faint` | 1 | tertiary: disabled, placeholders, guides, line numbers | - | N4 | overlay1 `#7f849c` |
| `fg.on-accent` | 1 | text on chromatic fills: chips, badges, accent selection, mode pills | - | N1 (bg tone) | base `#1e1e2e` |
| `fg.title` | 2 | panel and section titles (with bold) | `fg.default` | N6 | text `#cdd6f4` |
| `border.default` | 1 | inactive borders, rules, dividers | - | N3-N4 | overlay0 `#6c7086` |
| `border.focus` | 2 | border of the focused pane | `accent.primary` | cool hue | lavender `#b4befe` |
| `accent.primary` | 1 | identity accent: active tab, cursor glyph, spinner, primary button | - | scheme identity hue | blue `#89b4fa` |
| `accent.secondary` | 1 | second identity hue, categorical contrast with primary | - | second hue | mauve `#cba6f7` |
| `selection.bg` | 1 | focused list/table cursor row | - | N2-N3 (neutral) | overlay2 @25% `#3b3d4f` |
| `selection.fg` | 2 | text on `selection.bg` | `fg.default` | N6 | text `#cdd6f4` |
| `selection.inactive.bg` | 2 | cursor row in an unfocused pane | `bg.surface` | N2 | surface0 `#313244` |
| `text-selection.bg` | 2 | selected text range in inputs/editors | `selection.bg` | N2-N3 | `#3b3d4f` |
| `cursor.bg` | 2 | text-input cursor block | `fg.default` | N6 or warm accent | rosewater `#f5e0dc` |
| `cursor.fg` | 2 | glyph under the cursor | `bg.base` | N0-N1 | crust `#11111b` |
| `status.error` | 1 | errors, failures, destructive actions | - | red | red `#f38ba8` |
| `status.warning` | 1 | warnings, degraded, needs attention | - | yellow (orange) | yellow `#f9e2af` |
| `status.success` | 1 | success, healthy, done | - | green | green `#a6e3a1` |
| `status.info` | 1 | neutral information, hints | - | cyan/teal | teal `#94e2d5` |
| `search.match` | 2 | search/filter match highlight | `status.warning` | yellow/orange | `#f9e2af` |
| `link` | 2 | hyperlinks (OSC 8), URLs | `accent.primary` | blue | blue `#89b4fa` |
| `keyhint.key` | 2 | the key in `q quit` | `accent.primary` | blue/cyan | blue `#89b4fa` |
| `keyhint.desc` | 2 | the action label in `q quit` | `fg.muted` | N5-N6 | text `#cdd6f4` |
| `statusbar.bg` | 2 | status/footer/header bar fill | `bg.inset` | N0 or N2 | mantle `#181825` |
| `statusbar.fg` | 2 | status bar text | `fg.muted` | N5-N6 | subtext1 `#bac2de` |
| `tab.active.fg` | 2 | active tab label | `accent.primary` | accent or N6 | `#89b4fa` |
| `tab.active.bg` | 2 | active tab fill | `bg.raised` | N3 (or accent fill) | surface1 `#45475a` |
| `tab.inactive.fg` | 2 | inactive tab labels | `fg.muted` | N5 | `#a6adc8` |
| `table.header` | 2 | column headers | `fg.title` | N6 | `#cdd6f4` |
| `mark` | 2 | marked / multi-selected indicator | `accent.secondary` | second hue | `#cba6f7` |
| `scrollbar.thumb` | 2 | scrollbar thumb | `fg.faint` | N4-N5 | overlay2 `#9399b2` |
| `scrollbar.track` | 2 | scrollbar track | `border.default` | N3 | surface1 `#45475a` |
| `diff.added` / `diff.removed` / `diff.changed` | 2 | added / removed / changed lines | success / error / info | green / red / blue-yellow | green / red / blue |
| `ramp.low` / `ramp.mid` / `ramp.high` | 2 | severity gauge stops (good to bad) | success / warning / error | green / yellow / red | green / yellow / red |

Resolve in code: `load_theme('catppuccin-mocha').hex('keyhint.key')` returns `#89b4fa` with fallbacks applied ([`scripts/_theme.py`](../scripts/_theme.py)).

## The neutral ladder

Every scheme with a published spec defines 5-8 neutral steps (Catppuccin crust→text, Rosé Pine base/surface/overlay/muted/subtle/text, Kanagawa `bg_m3…bg_p2`, Dracula Darker→Lighter). Tokens name the steps, not the hex:

```
 N0 bg.inset    ▓▓▓▓  chrome bands, sidebars            Mocha mantle   #181825  1.07:1 vs base
 N1 bg.base     ▓▓▓▓  app background                    Mocha base     #1e1e2e  1.00
 N2 bg.surface  ▓▓▓▓  panels, inputs, popups            Mocha surface0 #313244  1.30
 N3 bg.raised   ▓▓▓▓  selection, hover, active tab      Mocha surface1 #45475a  1.80
 N4 fg.faint    ····  disabled, guides, line numbers    Mocha overlay1 #7f849c  4.44  (floor 3.0)
 N5 fg.muted    ····  labels, descriptions              Mocha subtext0 #a6adc8  7.37  (floor 4.5)
 N6 fg.default  ····  body text                         Mocha text     #cdd6f4 11.34  (floor 4.5, prefer 7)
```

Light themes keep the roles and invert lightness (N1 lightest body bg, N6 darkest text). Scheme authors do not all agree on direction: Catppuccin Latte keeps mantle/crust *darker* than base; Rosé Pine puts status bars on Surface (above base) and has no step below Base; Tokyo Night and Kanagawa put floating windows *below* base. Always read `bg.inset`/`bg.overlay` from the theme instead of assuming "lighter = higher".

## Design rules

Each rule: what to do → when → example → evidence.

### Elevation: overlays up, chrome down

- **Rule:** popups, menus, dialogs use `bg.surface`/`bg.overlay` (1-2 steps above base); status bars, headers and side panes use `bg.inset`/`statusbar.bg` (at or below base). Body panes stay on `bg.base`.
- **When:** any screen with a status bar, sidebar or floating layer.
- **Example (Mocha):** header and footer bands `mantle #181825`, list and detail panes `base #1e1e2e`, command palette `surface0 #313244` with a `lavender` border.
- **Evidence:** helix popup = surface0 (Catppuccin), Rosé Pine Surface = popups, Dracula "floating" `#343746`; status bars below: Catppuccin mantle/crust, Tokyo Night `bg_statusline = bg_dark`, Kanagawa `bg_m3`. Exceptions above.

### Three selection styles

| style | tokens | use when | example (Mocha) |
|---|---|---|---|
| **neutral fill** (default) | `selection.bg` + `selection.fg` + marker glyph in `accent.primary` | lists, tables, trees: the everyday cursor row | `❯` blue on `#3b3d4f`, text `#cdd6f4` (7.38:1) |
| **accent fill** | `accent.primary` fill + `fg.on-accent` text | one strong cursor in a menu, a mode pill, a selected button | `base #1e1e2e` on `blue #89b4fa` (7.79:1) |
| **tinted badge** | accent text on a 10-20% tint of the same accent | tags/labels that must stay readable inside a selected row | `red #f38ba8` on blend(red, base, 0.15) `#3e2e40` (5.43:1) |

- **Rule:** default to the neutral fill; the author specs say so (Catppuccin "Selection Background = Overlay 2 at 20-30% opacity", Rosé Pine Highlight Med + Text, Nord nord2, Dracula Selection). Accent fills come from ports that reuse `$primary` (Textual) or the user accent (yazi); across 33 official ports, 18 select with a neutral-ish fill and 15 with a chromatic one. Tinted badge precedent: Rosé Pine helix `rose_10`, `foam_10`.
- **Always** add a non-color cue: a neutral fill is only 1.3-1.9:1 against the base (Mocha 1.54:1; WCAG 1.4.11 wants 3:1 for state), so draw `❯`/`▌` or bold. Some schemes use the accent fill as their own spec (Everforest Dark `statusline1`, One Dark PmenuSel = blue): their `selection.bg` is chromatic and `selection.fg` is a bg tone.
- **Unfocused pane:** keep the row visible with `selection.inactive.bg` (one step lower) and drop the marker color to `fg.muted`.

### Zebra stripes: the weakest fill

- **Rule:** stripe alternate records with `bg.stripe` (falls back to `bg.inset`). Keep the background order, measured as contrast against `bg.base`: **stripe < `selection.inactive.bg` < `selection.bg`**. On the cursor row the selection fill replaces the stripe (never blend them).
- **Direction:** in dark themes the stripe goes **darker** than base (toward `bg.inset`), so the lighter steps (`bg.surface`, `bg.raised`) stay reserved for meaning: selection, hover, popups.
- **When / where:** layout rules (which tables, parity, whole records) live in [layout-archetypes.md §2.4](layout-archetypes.md#24-zebra-striping-tables-logs-long-lists).
- **Example (Tokyo Night Night):** stripe `bg.inset` 1.05:1, inactive selection `bg.surface` 1.27, selection `bg.raised` 1.53. Mocha: 1.07 / 1.30 / 1.54.
- **Never meaning-bearing:** `ansi16` is `default`, so stripes vanish in 16 colors and under `NO_COLOR`; that is fine because nothing may depend on them.
- **When the fallback breaks the order** (`bg.inset` equal to `bg.base`, or stronger than `selection.inactive.bg`), map `bg.stripe` explicitly as `bg.base` darkened to ~1.06:1 with a `derived:` provenance. The shipped themes already do this where needed (Nord, One Dark, Rosé Pine, Solarized, dracula-alucard, kanagawa-lotus, Everforest, tokyonight-storm); check a new theme with `_theme.contrast_ratio`. gruvbox-light's inset is lighter than base (1.03).
- **Keep existing stripes** in a redesign, and anchor parity to the data (e.g. the oldest event), not the screen row.
- **Evidence:** Textual `DataTable(zebra_stripes=True)` with component classes `datatable--even-row`/`datatable--odd-row` (`_data_table.py`, read); Lip Gloss `table.StyleFunc(func(row, col int) lipgloss.Style)`. Both index rows by position, so a list that prepends rows flips every stripe unless you pass a data-anchored parity.

### Three ways to encode focus

| method | tokens | precedent | when |
|---|---|---|---|
| accent border | `border.focus` on the focused pane, `border.default` elsewhere | lazygit `activeBorderColor`, k9s `frame.border.focusColor`, Textual `$border` | bordered multi-pane layouts (default) |
| visible vs hidden border | border only on the focused element | huh `Focused.Base` thick left border, `Blurred` = `HiddenBorder()` | forms, stacked fields |
| normal vs dimmed chrome | unfocused panes switch title/text to `fg.muted` | gitui (no focus-border key) | borderless layouts, narrow terminals |

- **Rule:** use one primary method plus the title cue (bold `fg.title` on the focused pane). `border.focus` must reach 3:1 against `bg.base` ([contrast floor](formats.md#contrast-floors)); `border.default` should be visibly weaker (Mocha 3.36 vs 9.17).

### Tabs

- **Rule:** active tab = `tab.active.fg` (bold) on `tab.active.bg`, which falls back to `bg.raised` (the raised neutral); inactive tabs = `tab.inactive.fg` on the bar background, no fill. Add an underline or `▔`/brackets so the active tab survives without color.
- **Evidence:** Rosé Pine "active tab = Text on Overlay" (Overlay is its `bg.raised`); Tokyo Night `TabLineSel = black on blue` and Everforest `statusline1` label background are filled-accent variants, so their themes map `tab.active.bg` to the accent and `tab.active.fg` to a bg tone.

### Key hints: key vs description

- **Rule:** the key is chromatic (`keyhint.key`), the description neutral (`keyhint.desc`), if a separator is used: `·` in `fg.faint` (default: two spaces). Never color both the same.
- **Example (Mocha):** `q` in blue `#89b4fa`, ` quit` in `#cdd6f4`, optional `·` separators in overlay1 (`fg.faint`).
- **Evidence:** key = blue/cyan in 15/31 ports, description = N6 fg in 12/21; Textual `$footer-key-foreground` ← accent; bubbles help uses greys only (key brighter than desc).

### Severity ramps vs categorical ramps

- **Severity ramp** (`ramp.low → ramp.mid → ramp.high` = green → yellow → red): CPU/memory/latency gauges where "higher = worse". Evidence: btop default temp, Tokyo Night extras all ramps, Catppuccin btop temp, k9s `defaultChartColors` green→red.
- **Categorical ramp:** one identity hue per metric (btop `cpu_box mauve`, `mem_box green`, `net_box maroon`); no good/bad meaning, so never reuse status hues for them. Use `accent.primary`, `accent.secondary`, `mark` and scheme-specific extras.
- **Rule:** a gauge colored by severity also prints the value (`87%`) and changes glyph or label at thresholds; see "Never color-only".

### Chips and badges

- **Rule:** chip = `fg.on-accent` text on a `status.*` or `accent.primary` fill, padded with one space on each side (` FAIL `).
- **Floor:** `fg.on-accent` on every fill ≥ 4.5:1 ([contrast floors](formats.md#contrast-floors)). Mocha passes on all five fills (7.08-12.91). Many schemes do not (Rosé Pine main `base` on pine 3.38, Tokyo Night Day 1.96-3.11): check `contrast_check.py ID` and prefer a tinted badge there.
- **Evidence:** Catppuccin "On Accent = Base"; helix mode badges base on rosewater/green/lavender; huh FocusedButton base on pink.

### Never color-only

- **Rule:** every state carries at least two of {glyph, word, color, position}. Status: `✓ passed` green, `✗ failed` red, `▲ warn` yellow, `· idle` faint. Selection: marker + fill. Focus: border color + bold title.
- **When:** always; doubly so in light themes, where status hues often fall below 4.5:1 ([color-schemes.md](color-schemes.md#cross-scheme-patterns)).
- **Evidence:** WCAG 2.2 SC 1.4.1; Dracula spec "Ensure color is not the sole means of conveying information"; red/green collapse for deuteranopes (ΔE 19.6). Test with `NO_COLOR=1` and a grayscale render.

### Transparency (`bg = terminal default`)

- **Rule:** support a transparent mode where `bg.base` is the terminal's default background (SGR 49) and only raised fills are painted. When you set an RGB fg, also set the bg of that cell, except in transparent mode where you trust the user's bg.
- **Example:** k9s Catppuccin `-transparent` skins swap every bg to `default`; btop empty `main_bg`; Textual `ansi=True` themes. Theme JSON keeps the hex; the renderer decides.

### Adaptive light/dark

- **Rule:** detect the terminal background at startup and pick the dark or light variant of the same scheme; let the user override.
- **How:** detection order and sentinels in [terminal-capabilities.md](terminal-capabilities.md) D5. Library hooks: lipgloss `LightDark(isDark)` with `tea.BackgroundColorMsg`, lazygit `gui.colorScheme: auto` + `darkTheme/lightTheme`, yazi `theme-dark/light`, helix `[theme] dark/light`.
- **Pairs:** catppuccin-mocha/latte, gruvbox-dark/light, tokyonight-night/day, rose-pine-main/dawn, kanagawa-wave/lotus, everforest-dark/light, solarized-dark/light, onedark-dark/light, dracula-classic/alucard.

## Token → theme-system keys

Use this to port a design to an existing app theme, or to name your own config keys. Key names were read from each project's theme source or docs (2026-10); verify against the installed version. `—` = the system has no such key.

### Apps

| token | Textual | helix | lazygit | k9s skin | btop | yazi | gitui |
|---|---|---|---|---|---|---|---|
| `bg.base` | `$background` | `ui.background` | — (terminal) | `body.bgColor` | `main_bg` | `app.overall` | — |
| `bg.surface` | `$surface`, `$panel` | `ui.gutter`, `ui.cursorline.primary` | — | `prompt.bgColor`, `views.*.bgColor` | — | `status.overall` | `cmdbar_bg` |
| `bg.overlay` | `$panel` (+`$boost`) | `ui.popup`, `ui.menu`, `ui.help` | — | `dialog.bgColor`, `help.bgColor` | — | `which.mask` | — |
| `fg.default` | `$foreground`, `$text` | `ui.text` | `defaultFgColor` | `body.fgColor` | `main_fg` | (terminal) | `command_fg` |
| `fg.muted` | `$text-muted`, `$foreground-muted` | `ui.text.inactive` | — | `status.completedColor` | `inactive_fg`, `graph_text` | `which.rest`, `help.action` | `disabled_fg` |
| `fg.faint` | `$text-disabled` | `ui.linenr`, `ui.virtual.*` | — | — | `div_line`, `meter_bg` | `status.perm_sep` | `disabled_fg` |
| `fg.title` | (`$markdown-h*`) | — | — | `frame.title.fgColor` | `title` | `confirm.title`, `input.title` | `block_title_focused` |
| `border.default` | `$border-blurred` | `ui.window` | `inactiveBorderColor` | `frame.border.fgColor` | `div_line` | `mgr.border_style` | `disabled_fg` |
| `border.focus` | `$border` | — | `activeBorderColor` | `frame.border.focusColor` | — | `{input,confirm,pick,…}.border` | — |
| `accent.primary` | `$primary` | `ui.statusline.normal` | — | `body.logoColor` | `hi_fg` | `mode.normal_main` | — |
| `accent.secondary` | `$secondary` | — | — | — | — | — | — |
| `selection.bg` / `bg.raised` | `$block-cursor-background` | `ui.menu.selected` | `selectedLineBgColor` | `views.table.cursorBgColor` | `selected_bg` | `indicator.current` | `selection_bg` |
| `selection.fg` | `$block-cursor-foreground` | `ui.menu.selected` fg | `selectedLineFgColor` | `views.table.cursorFgColor` | `selected_fg` | `indicator.current` fg | `selection_fg` |
| `selection.inactive.bg` | `$block-cursor-blurred-background` | `ui.cursorline.secondary` | `inactiveViewSelectedLineBgColor` | — | — | `indicator.parent` | — |
| `text-selection.bg` | `$input-selection-background` | `ui.selection` | — | — | — | `input.selected` | — |
| `cursor.bg` / `cursor.fg` | `$input-cursor-background/-foreground` | `ui.cursor.primary` | — | — | — | — | — |
| `status.error` | `$error` | `error`, `diagnostic.error` | `unstagedChangesColor` | `status.errorColor` | — | `notify.title_error` | `danger_fg` |
| `status.warning` | `$warning` | `warning` | — | `status.pendingColor` | — | `notify.title_warn` | — |
| `status.success` | `$success` | — | — | `status.addColor` | — | — | — |
| `status.info` | — | `info`, `hint` | — | `logoColorInfo` | — | `notify.title_info` | — |
| `search.match` | — | — | `searchingActiveBorderColor` | `frame.title.filterColor`, `highlightColor` | — | `mgr.find_keyword` | — |
| `link` | `$link-color`, `$link-style` | (`markup.link.*`) | — | — | — | — | — |
| `keyhint.key` | `$footer-key-foreground` | `ui.text.info` | `optionsTextColor` | `frame.menu.keyColor`, `help.keyColor` | `hi_fg` | `which.cand`, `help.chord` | — |
| `keyhint.desc` | `$footer-description-foreground` | `ui.popup.info` | (same key) | `frame.menu.fgColor`, `help.fgColor` | — | `which.desc`, `help.action` | `command_fg` |
| `statusbar.bg/fg` (and `bg.inset`) | `$footer-background/-foreground` | `ui.statusline` | — | `frame.crumbs.bgColor/fgColor` | — | `status.overall` | `cmdbar_bg` |
| `tab.active.*` / `tab.inactive.fg` | (Tabs underline `$block-cursor-background`) | `ui.bufferline.active` / `ui.bufferline` | — | `frame.crumbs.activeColor` | — | `tabs.active` / `tabs.inactive` | `selected_tab` |
| `table.header` | (DataTable `$panel`) | `ui.picker.header` | — | `views.table.header.*` | — | `spot.tbl_col` | — |
| `mark` | — | — | `cherryPicked*`, `markedBase*` | `views.table.markColor` | — | `mgr.marker_*` | — |
| `scrollbar.thumb/track` | `$scrollbar`, `$scrollbar-background` | `ui.menu.scroll` (fg/bg) | — | — | — | — | `selection_bg` |
| `diff.*` | — | `diff.plus/minus/delta` | — | — | — | — | `diff_line_add/delete`, `diff_file_*` |
| `ramp.*` | — | — | — | `views.charts.default{Chart,Dial}Colors` | `*_start/_mid/_end` | `status.progress_*` | `push_gauge_bg/fg` |

### Libraries

| token | lipgloss / bubbles / huh (Go) | Ink / @inkjs/ui (Node) | Ratatui (Rust): demo2 `Theme` field · opaline token |
|---|---|---|---|
| `bg.base` | root `Style.Background` (usually unset) · huh `Form.Base` | `<Box backgroundColor>` (unset = terminal) | `root` · `bg.base` |
| `bg.surface` / `bg.overlay` | `Style.Background` on panes · huh `Card` | `<Box backgroundColor>` | `content` · `bg.panel` / `bg.elevated` |
| `fg.default` | list `NormalTitle`, huh `Option`, textinput `Text` | `<Text>` default | `content` · `text.primary` |
| `fg.muted` | list `NormalDesc`, huh `Description`, help `ShortDesc` | `dimColor` | `description` · `text.muted` |
| `fg.faint` | textinput `Placeholder`, help `ShortSeparator`, list `DimmedTitle` | `dimColor` (list markers) | · `text.dim` |
| `fg.title` | huh `Title`, `Group.Title`, list `Title` | Alert `title` (bold) | `app_title`, `description_title` |
| `border.default` / `border.focus` | huh `Blurred.Base` (hidden) / `Focused.Base` `BorderForeground` | `borderColor`, `borderDimColor` | `borders` · `border.unfocused` / `border.focused` |
| `accent.primary` | huh `Title`, `FocusedButton` bg | Spinner `frame`, ProgressBar `completed` | `tabs_selected` · `accent.primary` |
| `selection.*` | list `SelectedTitle` (left border + fg, no bg), table `Selected`, huh `SelectSelector` | Select `focusIndicator`, `label` | `Style::new().bg(..)` on the highlighted row · `bg.selection` |
| `status.*` | huh `ErrorIndicator`, `ErrorMessage`; `SelectedOption` | Alert / StatusMessage variants (error red, warning yellow, success green, info blue) | · `error warning success info` |
| `keyhint.key/desc` | help `ShortKey`/`ShortDesc`, `FullKey`/`FullDesc` | — | `key_binding.key` / `key_binding.description` |
| `cursor.*` / `text-selection.bg` | textinput `Cursor.Color`, huh `TextInput.Cursor`; textarea `Selection` | — | — |
| `mark` | huh `SelectedPrefix` / `UnselectedPrefix` | MultiSelect `selectedIndicator` | — |
| `ramp.*` | `lipgloss.Blend1D(steps, stops...)` | ProgressBar `completed` / `remaining` (dim) | `Gauge::gauge_style` |

gum takes the same roles as flags: `--cursor.foreground`, `--selected.foreground`, `--header.foreground`, `--placeholder.foreground` (env `GUM_<CMD>_<PREFIX>_FOREGROUND`). Ratatui has no theme system; the closest precedent for this token set is [opaline](https://github.com/hyperb1iss/opaline/tree/c9edc3df25) (palette → tokens → styles, ~20 built-in TOML themes). Generate ready-to-paste code with `SKILL_DIR/scripts/export_theme.py ID --target textual|ink|lipgloss|ratatui|gum|css|json`.

## 16-color and 256-color

| depth | what to emit | how tokens resolve | caveat |
|---|---|---|---|
| truecolor | `38;2;r;g;b` / `48;2;…` | theme hex | set fg *and* bg on any cell you color |
| 256 | `38;5;N` | `nearest256(hex)` = OKLab nearest over indexes 16-255 (never 0-15) | method and measurements: [terminal-capabilities.md](terminal-capabilities.md) D3; re-check contrast after quantizing: e.g. Rosé Pine main `fg.faint` 3.42 → 2.82 |
| 16 | `30-37/90-97` (fg), `40-47` (bg) | per-token `ansi16` spec: `_tokens.json` default, overridden per theme | slots belong to the user's terminal palette; slot name ≠ hue |
| none | attributes only | bold, dim, reverse, underline carry the hierarchy | honor `NO_COLOR` ([terminal-capabilities.md](terminal-capabilities.md) D1) |

- **Spec grammar:** `"<color> [attrs…]"`; full definition (`0..15|default|reverse|bg`, attrs) in [formats.md](formats.md#theme-json). Examples: `"8"`, `"default dim"`, `"4 underline"`, `"reverse"` (selection: swap terminal fg/bg).
- **Hand-author 16, compute 256** (nearest-color to 16 slots is unreliable: Catppuccin pink lands on bright red or bright magenta depending on the metric). Each theme JSON carries `ansi16` overrides chosen by a fixed rule: keep the `_tokens.json` default when it clears the floor and has the token's hue; otherwise use the slot holding the same palette color (Rosé Pine `status.info` → slot 4, which is foam), else the nearest same-hue slot that passes; neutral text tokens may move to `7`, `15`, `8` or `default dim`.
- **Known 16-color traps fixed by overrides:** Solarized slot 8 = background (`fg.faint` → `7 dim`); Rosé Pine green/blue/cyan slots hold pine/foam/rose; Dracula and Rosé Pine accents live in slot 5; `default dim` drops below 4.5:1 in most dark themes (Mocha 4.38), so `fg.muted` moves to a grey slot (Mocha `15` = subtext0).
- **Residual 16-color limit:** chips (`fg.on-accent` on an accent slot) often fail because no slot equals the background (Mocha slot 0 = surface1: 4.33:1 on blue). `fg.on-accent` therefore defaults to `bg` in 16-color mode: the accent slot + SGR 7, which shows the terminal background color as the text (Mocha 7.79:1). Bold does not help and can turn slot 0 into slot 8 on bold-as-bright terminals.

## Contrast floors

Values, the dim model (blend 0.55) and the failure policy live in [formats.md](formats.md#contrast-floors); check with `python3 SKILL_DIR/scripts/contrast_check.py ID` and `--depth 16`. Failures are listed per variant in the scheme pages and in each JSON's `notes`; real terminals vary on dim (Ghostty `faint-opacity`).

## Adding a theme

To add a theme: copy a JSON from `themes/`, keep the official palette hexes, map every tier-1 token, write a `provenance` entry per token (`spec:`, `port:`, `consensus: n/m`, `cross-scheme:`, `choice:`, `derived:`), then run `contrast_check.py` in both depths and add `ansi16` overrides where the 16-color result is invisible or below the floor.
