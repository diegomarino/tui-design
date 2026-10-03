# Nord: palette → token map

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [At a glance](#at-a-glance) · L15–21 — variant ids, appearance, base/text/accent hex, license and sources.
- [Palette (official hex)](#palette-official-hex) · L23–63 — the exact official hex of a named palette entry.
- [Author's role rules](#authors-role-rules) · L65–80 — the scheme author's own rules for what each colour is for.
- [Token map](#token-map) · L82–143 — the palette entry, hex and contrast behind each semantic token (tier 1 and tier 2).
- [Contrast findings](#contrast-findings) · L145–151 — which tokens fail a floor per variant, in truecolor, 16 and 256 colours.
- [16-color mode](#16-color-mode) · L153–168 — the per-variant `ansi16` overrides and their ratios.
- [Quirks and discrepancy decisions](#quirks-and-discrepancy-decisions) · L170–174 — where sources disagree and which value was kept, light-theme limits.
- [App ports](#app-ports) · L176–182 — whether helix, lazygit, k9s, btop, yazi, gitui or Textual ship a port of this scheme.

Read this when a TUI uses Nord and you need the exact palette entry, hex and contrast for each semantic token, the author's role rules, and the 16-color caveats. Token meanings: [../color-tokens.md](../color-tokens.md). All schemes: [../color-schemes.md](../color-schemes.md). Machine-readable: [`nord-dark.json`](../themes/nord-dark.json).

## At a glance

| variant | id | appearance | bg.base | fg.default | accent.primary | license |
|---|---|---|---|---|---|---|
| Dark | `nord-dark` | dark | `#2e3440` | `#d8dee9` 9.25 | nord8 `#88c0d0` | MIT |

Sources (first variant; others use the same files per variant): palette <https://github.com/nordtheme/nord/blob/develop/src/nord.css>; terminal <https://github.com/nordtheme/alacritty/blob/main/src/nord.yaml>; role spec <https://github.com/nordtheme/web/blob/main/content/docs/colors-and-palettes/index.mdx>.

## Palette (official hex)

| name | Dark |
|---|---|
| nord0 | `#2e3440` |
| nord1 | `#3b4252` |
| nord2 | `#434c5e` |
| nord3 | `#4c566a` |
| nord4 | `#d8dee9` |
| nord5 | `#e5e9f0` |
| nord6 | `#eceff4` |
| nord7 | `#8fbcbb` |
| nord8 | `#88c0d0` |
| nord9 | `#81a1c1` |
| nord10 | `#5e81ac` |
| nord11 | `#bf616a` |
| nord12 | `#d08770` |
| nord13 | `#ebcb8b` |
| nord14 | `#a3be8c` |
| nord15 | `#b48ead` |

ANSI 0–15 (terminal slots, in order black … bright white):

| slot | Dark |
|---|---|
| 0 black | `#3b4252` nord1 |
| 1 red | `#bf616a` nord11 |
| 2 green | `#a3be8c` nord14 |
| 3 yellow | `#ebcb8b` nord13 |
| 4 blue | `#81a1c1` nord9 |
| 5 magenta | `#b48ead` nord15 |
| 6 cyan | `#88c0d0` nord8 |
| 7 white | `#e5e9f0` nord5 |
| 8 br.black | `#4c566a` nord3 |
| 9 br.red | `#bf616a` nord11 |
| 10 br.green | `#a3be8c` nord14 |
| 11 br.yellow | `#ebcb8b` nord13 |
| 12 br.blue | `#81a1c1` nord9 |
| 13 br.magenta | `#b48ead` nord15 |
| 14 br.cyan | `#8fbcbb` nord7 |
| 15 br.white | `#eceff4` nord6 |

## Author's role rules

Source: [nordtheme/web colors-and-palettes](https://github.com/nordtheme/web/blob/main/content/docs/colors-and-palettes/index.mdx) ("soft recommendations", work in progress).

| entry | role (quoted/condensed) |
|---|---|
| nord0 | "background and area coloring" |
| nord1 | elevated UI: status bars, gutters, panels, modals, floating popups, form components |
| nord2 | "currently active text editor line as well as selection- and text highlighting color" |
| nord3 | comments, invisibles, indent/wrap guides, disabled UI |
| nord4 / nord5 / nord6 | text and caret / subtle UI text / "elevated UI text elements that require more visual attention" |
| nord8 | "bright and shiny primary accent color": primary UI, functions, link URLs |
| nord9 / nord10 / nord7 | secondary UI / tertiary UI / classes, types |
| nord11 / nord12 / nord13 / nord14 / nord15 | errors, deletions / "advanced or dangerous functionality" / warnings, modifications / success, additions / numbers |

Nord's lighter snow tones (nord5, nord6) are *more* emphasis, not less: there is no official grey between nord3 and nord4.

## Token map

Cell = palette name, hex, contrast. Contrast is vs `bg.base` (for bg tokens it shows the step from the base), `selection.fg` is vs `selection.bg`, `fg.on-accent` is the lowest ratio over the accent and status fills. FAIL = below the [contrast floor](../formats.md#contrast-floors). *→ token* = unmapped tier-2 token resolved through its fallback; *derived* = computed hex (see Basis).

### Tier 1 (always mapped)

| token | Dark | basis |
|---|---|---|
| `bg.base` | nord0 `#2e3440` 1.00 | spec: nord0 = background and area coloring |
| `bg.inset` | nord0 `#2e3440` 1.00 | choice: Nord has no tone below nord0; chrome bands use statusbar.bg = nord1 (spec) |
| `bg.surface` | nord1 `#3b4252` 1.24 | spec: nord1 = panels, modals, floating popups, form components |
| `bg.raised` | nord2 `#434c5e` 1.45 | spec: nord2 = active line, selection and text highlighting |
| `fg.default` | nord4 `#d8dee9` 9.25 | spec: nord4 = text |
| `fg.muted` | *derived* `#9ca2ae` 4.87 | choice: no Nord grey between nord3 (1.69:1) and nord4; derived: nord4 @alpha over nord0 (Textual … |
| `fg.faint` | nord3 `#4c566a` 1.69 FAIL | spec: nord3 = comments, guides, disabled UI |
| `fg.on-accent` | nord0 `#2e3440` 3.05 FAIL | consensus: selection.fg on nord8 = nord0 (1/3); cross-scheme N1 on chromatic fills |
| `border.default` | nord3 `#4c566a` 1.69 | spec: nord3 = indent/wrap guides; choice over nord1 (spec 'borders') because nord1 is 1.24:1 on nord0 |
| `accent.primary` | nord8 `#88c0d0` 6.24 | spec: nord8 = 'bright and shiny primary accent color' |
| `accent.secondary` | nord9 `#81a1c1` 4.64 | spec: nord9 = secondary UI elements |
| `selection.bg` | nord2 `#434c5e` 1.45 | spec: nord2 = selection and text highlighting |
| `status.error` | nord11 `#bf616a` 3.05 FAIL | spec: nord11 = errors |
| `status.warning` | nord13 `#ebcb8b` 8.00 | spec: nord13 = warnings |
| `status.success` | nord14 `#a3be8c` 6.13 | spec: nord14 = success |
| `status.info` | nord8 `#88c0d0` 6.24 | consensus: info = nord8 (1/1); cross-scheme info = cyan |

### Tier 2

| token | Dark | basis |
|---|---|---|
| `bg.overlay` | nord1 `#3b4252` 1.24 | spec: nord1 = modals and floating popups |
| `bg.stripe` | *derived* `#2a303b` 1.06 | derived: bg.base darkened to 1.06:1 (weakest fill; bg.inset is invisible here, 1.00:1 vs inactive … |
| `fg.title` | nord6 `#eceff4` 10.84 | spec: nord6 = 'elevated UI text elements that require more visual attention' |
| `border.focus` | nord8 `#88c0d0` 6.24 | spec: nord8 = primary UI accent; consensus focused border nord8 1/3 |
| `selection.fg` | *→ fg.default* `#d8dee9` 6.39 | fallback |
| `selection.inactive.bg` | *→ bg.surface* `#3b4252` 1.24 | fallback |
| `text-selection.bg` | nord2 `#434c5e` 1.45 | spec: nord2 = selection and text highlighting |
| `cursor.bg` | nord4 `#d8dee9` 9.25 | spec: nord4 = UI text editor caret |
| `cursor.fg` | nord0 `#2e3440` 1.00 | port: nordtheme/alacritty cursor text = nord0 |
| `search.match` | *→ status.warning* `#ebcb8b` 8.00 | fallback |
| `link` | nord8 `#88c0d0` 6.24 | spec: nord8 = markup link URLs |
| `keyhint.key` | *→ accent.primary* `#88c0d0` 6.24 | fallback |
| `keyhint.desc` | nord4 `#d8dee9` 9.25 | consensus: 2/2 ports |
| `statusbar.bg` | nord1 `#3b4252` 1.24 | spec: nord1 = status bars |
| `statusbar.fg` | nord4 `#d8dee9` 9.25 | consensus: 2/2 ports |
| `tab.active.fg` | *→ accent.primary* `#88c0d0` 6.24 | fallback |
| `tab.active.bg` | *→ bg.raised* `#434c5e` 1.45 | fallback |
| `tab.inactive.fg` | *→ fg.muted* `#9ca2ae` 4.87 | fallback |
| `table.header` | *→ fg.default* `#d8dee9` 9.25 | fallback |
| `mark` | *→ accent.secondary* `#81a1c1` 4.64 | fallback |
| `scrollbar.thumb` | *→ fg.faint* `#4c566a` 1.69 | fallback |
| `scrollbar.track` | *→ border.default* `#4c566a` 1.69 | fallback |
| `diff.added` | nord14 `#a3be8c` 6.13 | spec: nord14 = git diff additions |
| `diff.removed` | nord11 `#bf616a` 3.05 | spec: nord11 = git diff deletions |
| `diff.changed` | nord13 `#ebcb8b` 8.00 | spec: nord13 = git diff modifications |
| `ramp.low` | nord14 `#a3be8c` 6.13 | cross-scheme: severity ramp |
| `ramp.mid` | nord13 `#ebcb8b` 8.00 | cross-scheme: severity ramp |
| `ramp.high` | nord11 `#bf616a` 3.05 | cross-scheme: severity ramp |

Derived hex values (computed, not palette entries; `blend(a, b, α)` = a composited over b at opacity α):

- Dark: `bg.stripe` = `#2a303b` = see provenance
- Dark: `fg.muted` = `#9ca2ae` = blend(nord4, nord0, 0.65)

## Contrast findings

| variant | truecolor failures | 16-color failures (after overrides) | 256-color failures (OKLab nearest) |
|---|---|---|---|
| Dark | fg.faint 1.69, status.error 3.05, fg.on-accent 3.05 | status.error 3.05, fg.on-accent 3.05 | fg.faint 1.86, status.error 2.91, fg.on-accent 2.91 |

Rule for failures: the official mapping is kept unless the palette offers a same-role entry that passes (those swaps are listed in Basis). Where a status color fails, never rely on it alone: pair it with a glyph and a word (see [../color-tokens.md](../color-tokens.md#never-color-only)).

## 16-color mode

Per-theme `ansi16` overrides of the `_tokens.json` defaults (spec = `slot [attrs]`; ratio vs the terminal background in that mode):

| token | default | Dark |
|---|---|---|
| `fg.muted` | `default dim` | `default` 9.25 |
| `fg.faint` | `8` | `default dim` 3.99 |
| `border.focus` | `4` | `6` 6.24 |
| `accent.primary` | `4` | `6` 6.24 |
| `accent.secondary` | `5` | `4` 4.64 |
| `link` | `4 underline` | `6 underline` 6.24 |
| `keyhint.key` | `4` | `6` 6.24 |
| `tab.active.fg` | `4 bold` | `6 bold` 6.24 |
| `mark` | `5` | `4` 4.64 |
| `diff.changed` | `4` | `3` 8.00 |

## Quirks and discrepancy decisions

- No official kitty port; terminal from nordtheme/alacritty. selection_foreground is dynamic (CellForeground) -> null. Bright cyan is nord7, normal cyan nord8.
- nord3 (comments, disabled UI) is 1.69:1 on nord0: fg.faint fails 3:1 and the palette has no compliant grey with that role. Use fg.muted for anything the user must read.
- nord11 (errors) is 3.05:1 on nord0 and nord12 is 4.39:1: status.error fails 4.5:1 with no compliant same-role alternative. Pair errors with a glyph and bold.

## App ports

O = official (scheme org or scheme repo extras), B = bundled in the app repo, C = community repo, - = none found (checked 2026-10).

| variant | helix | lazygit | k9s | btop | yazi | gitui | textual |
|---|---|---|---|---|---|---|---|
| Dark | B | - | B | B | - | - | B |
