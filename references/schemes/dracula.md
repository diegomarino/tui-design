# Dracula (Dracula, Alucard): palette → token map

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [At a glance](#at-a-glance) · L15–25 — variant ids, appearance, base/text/accent hex, license and sources.
- [Palette (official hex)](#palette-official-hex) · L27–73 — the exact official hex of a named palette entry.
- [Author's role rules](#authors-role-rules) · L75–83 — the scheme author's own rules for what each colour is for.
- [Token map](#token-map) · L85–146 — the palette entry, hex and contrast behind each semantic token (tier 1 and tier 2).
- [Contrast findings](#contrast-findings) · L148–155 — which tokens fail a floor per variant, in truecolor, 16 and 256 colours.
- [16-color mode](#16-color-mode) · L157–166 — the per-variant `ansi16` overrides and their ratios.
- [Quirks and discrepancy decisions](#quirks-and-discrepancy-decisions) · L168–175 — where sources disagree and which value was kept, light-theme limits.
- [App ports](#app-ports) · L177–184 — whether helix, lazygit, k9s, btop, yazi, gitui or Textual ship a port of this scheme.

Read this when a TUI uses Dracula and you need the exact palette entry, hex and contrast for each semantic token, the author's role rules, and the 16-color caveats. Token meanings: [../color-tokens.md](../color-tokens.md). All schemes: [../color-schemes.md](../color-schemes.md). Machine-readable: [`dracula-classic.json`](../themes/dracula-classic.json), [`dracula-alucard.json`](../themes/dracula-alucard.json).

## At a glance

| variant | id | appearance | bg.base | fg.default | accent.primary | license |
|---|---|---|---|---|---|---|
| Dracula | `dracula-classic` | dark | `#282a36` | `#f8f8f2` 13.36 | purple `#bd93f9` | MIT |
| Alucard | `dracula-alucard` | light | `#fffbeb` | `#1f1f1f` 15.89 | purple `#644ac9` | MIT |

Sources:

- Dracula: palette <https://github.com/dracula/dracula-theme/blob/main/README.md>; terminal <https://github.com/dracula/kitty/blob/master/dracula.conf>; role spec <https://github.com/dracula/draculatheme.com/blob/main/content/spec.mdx>.
- Alucard: palette <https://github.com/dracula/draculatheme.com/blob/main/content/spec.mdx>; terminal <https://github.com/dracula/draculatheme.com/blob/main/content/spec.mdx>; role spec <https://github.com/dracula/draculatheme.com/blob/main/content/spec.mdx>.

## Palette (official hex)

| name | Dracula | Alucard |
|---|---|---|
| background | `#282a36` | `#fffbeb` |
| current_line | `#6272a4` | `#6c664b` |
| selection | `#44475a` | `#cfcfde` |
| foreground | `#f8f8f2` | `#1f1f1f` |
| comment | `#6272a4` | `#6c664b` |
| red | `#ff5555` | `#cb3a2a` |
| orange | `#ffb86c` | `#a34d14` |
| yellow | `#f1fa8c` | `#846e15` |
| green | `#50fa7b` | `#14710a` |
| cyan | `#8be9fd` | `#036a96` |
| purple | `#bd93f9` | `#644ac9` |
| pink | `#ff79c6` | `#a3144d` |
| ui_floating_interactive_elements | `#343746` | `#efeddc` |
| ui_background_lighter | `#424450` | `#ece9df` |
| ui_background_light | `#343746` | `#dedccf` |
| ui_background_dark | `#21222c` | `#ceccc0` |
| ui_background_darker | `#191a21` | `#bcbab3` |
| functional_red | `#de5735` | `#de5735` |
| functional_orange | `#a39514` | `#a39514` |
| functional_green | `#089108` | `#089108` |
| functional_cyan | `#0081d6` | `#0081d6` |
| functional_purple | `#815cd6` | `#815cd6` |

ANSI 0–15 (terminal slots, in order black … bright white):

| slot | Dracula | Alucard |
|---|---|---|
| 0 black | `#21222c` ui_background_dark | `#fffbeb` background |
| 1 red | `#ff5555` red | `#cb3a2a` red |
| 2 green | `#50fa7b` green | `#14710a` green |
| 3 yellow | `#f1fa8c` yellow | `#846e15` yellow |
| 4 blue | `#bd93f9` purple | `#644ac9` purple |
| 5 magenta | `#ff79c6` pink | `#a3144d` pink |
| 6 cyan | `#8be9fd` cyan | `#036a96` cyan |
| 7 white | `#f8f8f2` foreground | `#1f1f1f` foreground |
| 8 br.black | `#6272a4` current_line | `#6c664b` current_line |
| 9 br.red | `#ff6e6e` | `#d74c3d` |
| 10 br.green | `#69ff94` | `#198d0c` |
| 11 br.yellow | `#ffffa5` | `#9e841a` |
| 12 br.blue | `#d6acff` | `#7862d0` |
| 13 br.magenta | `#ff92df` | `#bf185a` |
| 14 br.cyan | `#a4ffff` | `#047fb4` |
| 15 br.white | `#ffffff` | `#2c2b31` |

## Author's role rules

Source: [spec.mdx](https://github.com/dracula/draculatheme.com/blob/main/content/spec.mdx) (2026) + [dracula-theme README](https://github.com/dracula/dracula-theme/blob/main/README.md).

- Syntax roles: Comment = "comments, disabled code"; Selection = text selection; Red = "errors, warnings, deletion"; Orange = numbers/constants; Yellow = strings; Green = functions; Cyan = classes/types; Purple = instance reserved words; Pink = keywords.
- UI: "Subtle borders: Use `Current Line` color; Interactive borders: Use functional colors; Focus rings: `Functional Purple`". States: "Success: Functional Green; Warning: Functional Orange; Error: Functional Red; Info: Functional Cyan".
- Functional colors are "UI-specific... **Do not use in editor or terminal applications.**" A TUI is a terminal application, so the tokens use the same-named regular colors (green, orange, red, cyan, purple).
- Accessibility: "Maintain **4.5:1 minimum contrast ratio** (WCAG 2.1 Level AA); Ensure color is not the sole means of conveying information".
- UI background ladder: Darker < Dark < Background < Light (= floating interactive elements) < Lighter.

## Token map

Cell = palette name, hex, contrast. Contrast is vs `bg.base` (for bg tokens it shows the step from the base), `selection.fg` is vs `selection.bg`, `fg.on-accent` is the lowest ratio over the accent and status fills. FAIL = below the [contrast floor](../formats.md#contrast-floors). *→ token* = unmapped tier-2 token resolved through its fallback; *derived* = computed hex (see Basis).

### Tier 1 (always mapped)

| token | Dracula | Alucard | basis |
|---|---|---|---|
| `bg.base` | background `#282a36` 1.00 | background `#fffbeb` 1.00 | spec: Background = main background |
| `bg.inset` | ui_background_dark `#21222c` 1.11 | ui_background_dark `#ceccc0` 1.56 | spec: UI 'Background Dark' (secondary panes; = ANSI black) |
| `bg.surface` | ui_background_light `#343746` 1.21 | ui_background_light `#dedccf` 1.33 | spec: UI 'Background Light' / floating interactive elements |
| `bg.raised` | ui_background_lighter `#424450` 1.47 | ui_background_lighter `#ece9df` 1.17 | spec: UI 'Background Lighter' (highest neutral UI fill) |
| `fg.default` | foreground `#f8f8f2` 13.36 | foreground `#1f1f1f` 15.89 | spec: Foreground = default text |
| `fg.muted` | *derived* `#a5a6a7` 5.84 | comment `#6c664b` 5.56 | consensus: tie 1/3 each (Textual $foreground-muted = foreground @60%, k9s comment, btop selection); … (varies by variant: see JSON) |
| `fg.faint` | comment `#6272a4` 3.03 | comment `#6c664b` 5.56 | spec: 'Comment: comments, disabled code' |
| `fg.on-accent` | background `#282a36` 4.53 | background `#fffbeb` 4.85 | cross-scheme: text on chromatic fills = N1 background |
| `border.default` | current_line `#6272a4` 3.03 | ui_background_darker `#bcbab3` 1.87 | spec: 'Subtle borders: use Current Line' (varies by variant: see JSON) |
| `accent.primary` | purple `#bd93f9` 5.90 | purple `#644ac9` 6.02 | consensus: 2/2 ports (Textual primary, helix ui.statusline.normal) |
| `accent.secondary` | pink `#ff79c6` 5.97 | pink `#a3144d` 7.33 | port: Textual accent = pink; spec keyword hue |
| `selection.bg` | selection `#44475a` 1.56 | selection `#cfcfde` 1.49 | spec: Selection = text selection |
| `status.error` | red `#ff5555` 4.53 | red `#cb3a2a` 4.85 | spec: UI state Error = Functional Red -> Red (functional colors are not for terminal apps) |
| `status.warning` | orange `#ffb86c` 8.36 | orange `#a34d14` 5.58 | spec: UI state Warning = Functional Orange -> Orange |
| `status.success` | green `#50fa7b` 10.38 | green `#14710a` 5.96 | spec: UI state Success = Functional Green -> Green |
| `status.info` | cyan `#8be9fd` 10.29 | cyan `#036a96` 5.78 | spec: UI state Info = Functional Cyan -> Cyan |

### Tier 2

| token | Dracula | Alucard | basis |
|---|---|---|---|
| `bg.overlay` | ui_floating_interactive_elements `#343746` 1.21 | ui_floating_interactive_elements `#efeddc` 1.14 | spec: 'Floating interactive elements' |
| `bg.stripe` | *→ bg.inset* `#21222c` 1.11 | *derived* `#f8f4e5` 1.06 | derived: bg.base darkened to 1.06:1 (weakest fill; bg.inset is too strong here, 1.56:1 vs inactive … |
| `fg.title` | foreground `#f8f8f2` 13.36 | foreground `#1f1f1f` 15.89 | consensus: 2/2 ports (k9s frame.title, btop title) |
| `border.focus` | purple `#bd93f9` 5.90 | purple `#644ac9` 6.02 | spec: focus rings = Functional Purple 'or appropriate accent'; Functional colors are UI-only ('Do not use … |
| `selection.fg` | foreground `#f8f8f2` 8.59 | foreground `#1f1f1f` 10.70 | spec: Foreground = default text (kitty selection_foreground is #ffffff) |
| `selection.inactive.bg` | *→ bg.surface* `#343746` 1.21 | *→ bg.surface* `#dedccf` 1.33 | fallback |
| `text-selection.bg` | selection `#44475a` 1.56 | selection `#cfcfde` 1.49 | spec: Selection |
| `cursor.bg` | foreground `#f8f8f2` 13.36 | foreground `#1f1f1f` 15.89 | port: dracula/kitty cursor = foreground |
| `cursor.fg` | background `#282a36` 1.00 | background `#fffbeb` 1.00 | port: dracula/kitty cursor_text_color = background |
| `search.match` | *→ status.warning* `#ffb86c` 8.36 | *→ status.warning* `#a34d14` 5.58 | fallback |
| `link` | cyan `#8be9fd` 10.29 | cyan `#036a96` 5.78 | spec: Functional Cyan = info, links -> Cyan |
| `keyhint.key` | pink `#ff79c6` 5.97 | pink `#a3144d` 7.33 | consensus: 2/4 ports (Textual footer key = $accent, k9s frame.menu.keyColor) |
| `keyhint.desc` | foreground `#f8f8f2` 13.36 | foreground `#1f1f1f` 15.89 | consensus: 2/2 ports (Textual footer description, k9s frame.menu.fgColor) |
| `statusbar.bg` | *→ bg.inset* `#21222c` 1.11 | *→ bg.inset* `#ceccc0` 1.56 | fallback |
| `statusbar.fg` | foreground `#f8f8f2` 13.36 | foreground `#1f1f1f` 15.89 | consensus: 3/3 ports |
| `tab.active.fg` | *→ accent.primary* `#bd93f9` 5.90 | *→ accent.primary* `#644ac9` 6.02 | fallback |
| `tab.active.bg` | *→ bg.raised* `#424450` 1.47 | *→ bg.raised* `#ece9df` 1.17 | fallback |
| `tab.inactive.fg` | *→ fg.muted* `#a5a6a7` 5.84 | *→ fg.muted* `#6c664b` 5.56 | fallback |
| `table.header` | *→ fg.default* `#f8f8f2` 13.36 | *→ fg.default* `#1f1f1f` 15.89 | fallback |
| `mark` | *→ accent.secondary* `#ff79c6` 5.97 | *→ accent.secondary* `#a3144d` 7.33 | fallback |
| `scrollbar.thumb` | *→ fg.faint* `#6272a4` 3.03 | *→ fg.faint* `#6c664b` 5.56 | fallback |
| `scrollbar.track` | *→ border.default* `#6272a4` 3.03 | *→ border.default* `#bcbab3` 1.87 | fallback |
| `diff.added` | green `#50fa7b` 10.38 | green `#14710a` 5.96 | port: helix diff.plus = green |
| `diff.removed` | red `#ff5555` 4.53 | red `#cb3a2a` 4.85 | spec: Red = deletion |
| `diff.changed` | *→ status.info* `#8be9fd` 10.29 | *→ status.info* `#036a96` 5.78 | fallback |
| `ramp.low` | green `#50fa7b` 10.38 | green `#14710a` 5.96 | cross-scheme: severity ramp green->yellow/orange->red |
| `ramp.mid` | orange `#ffb86c` 8.36 | orange `#a34d14` 5.58 | cross-scheme: severity ramp; = status.warning |
| `ramp.high` | red `#ff5555` 4.53 | red `#cb3a2a` 4.85 | cross-scheme: severity ramp; = status.error |

Derived hex values (computed, not palette entries; `blend(a, b, α)` = a composited over b at opacity α):

- Dracula: `fg.muted` = `#a5a6a7` = blend(foreground, background, 0.6)
- Alucard: `bg.stripe` = `#f8f4e5` = see provenance

## Contrast findings

| variant | truecolor failures | 16-color failures (after overrides) | 256-color failures (OKLab nearest) |
|---|---|---|---|
| Dracula | none | none | none |
| Alucard | none | none | none |

Rule for failures: the official mapping is kept unless the palette offers a same-role entry that passes (those swaps are listed in Basis). Where a status color fails, never rely on it alone: pair it with a glyph and a word (see [../color-tokens.md](../color-tokens.md#never-color-only)).

## 16-color mode

Per-theme `ansi16` overrides of the `_tokens.json` defaults (spec = `slot [attrs]`; ratio vs the terminal background in that mode):

| token | default | Dracula | Alucard |
|---|---|---|---|
| `fg.muted` | `default dim` | · | `8` 5.56 |
| `link` | `4 underline` | `6 underline` 10.29 | `6 underline` 5.78 |
| `keyhint.key` | `4` | `5` 5.97 | `5` 7.33 |
| `diff.changed` | `4` | `6` 10.29 | `6` 5.78 |

## Quirks and discrepancy decisions

- Discrepancy (Current Line): dracula-theme README says #44475a (= Selection), the 2026 spec says Current Line = Comment #6272a4 used as a translucent overlay (opaque fallback #353747). Followed the spec: border.default = current_line #6272a4. k9s skins/dracula.yaml still uses #44475a. (Dracula)
- The spec's Functional colors (functional_*) are UI-only: 'Do not use in editor or terminal applications'. They stay in the palette for reference but no token uses them. (Dracula)
- ANSI blue (slot 4) is purple #bd93f9; ANSI black (slot 0) = ui_background_dark. (Dracula)
- No terminal port exists for Alucard; terminal slots come from the spec's ANSI table. ANSI black (0) = background #fffbeb and ANSI white (7) = foreground #1f1f1f (inverted for a light theme): text in slot 0 is invisible, so no ansi16 token resolves to slot 0 as foreground on the background. (Alucard)
- cursor, cursor_text and selection_foreground are not defined by the spec (null). (Alucard)
- Alucard has a single secondary grey (comment = current_line #6c664b): fg.muted and fg.faint are the same color. (Alucard)

## App ports

O = official (scheme org or scheme repo extras), B = bundled in the app repo, C = community repo, - = none found (checked 2026-10).

| variant | helix | lazygit | k9s | btop | yazi | gitui | textual |
|---|---|---|---|---|---|---|---|
| Dracula | B | O | B | B | O | - | B |
| Alucard | - | - | - | - | - | - | - |
