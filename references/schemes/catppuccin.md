# Catppuccin (Latte, Frappé, Macchiato, Mocha): palette → token map

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [At a glance](#at-a-glance) · L15–29 — variant ids, appearance, base/text/accent hex, license and sources.
- [Palette (official hex)](#palette-official-hex) · L31–81 — the exact official hex of a named palette entry.
- [Author's role rules](#authors-role-rules) · L83–98 — the scheme author's own rules for what each colour is for.
- [Token map](#token-map) · L100–163 — the palette entry, hex and contrast behind each semantic token (tier 1 and tier 2).
- [Contrast findings](#contrast-findings) · L165–174 — which tokens fail a floor per variant, in truecolor, 16 and 256 colours.
- [16-color mode](#16-color-mode) · L176–185 — the per-variant `ansi16` overrides and their ratios.
- [Quirks and discrepancy decisions](#quirks-and-discrepancy-decisions) · L187–196 — where sources disagree and which value was kept, light-theme limits.
- [App ports](#app-ports) · L198–207 — whether helix, lazygit, k9s, btop, yazi, gitui or Textual ship a port of this scheme.

Read this when a TUI uses Catppuccin and you need the exact palette entry, hex and contrast for each semantic token, the author's role rules, and the 16-color caveats. Token meanings: [../color-tokens.md](../color-tokens.md). All schemes: [../color-schemes.md](../color-schemes.md). Machine-readable: [`catppuccin-latte.json`](../themes/catppuccin-latte.json), [`catppuccin-frappe.json`](../themes/catppuccin-frappe.json), [`catppuccin-macchiato.json`](../themes/catppuccin-macchiato.json), [`catppuccin-mocha.json`](../themes/catppuccin-mocha.json).

## At a glance

| variant | id | appearance | bg.base | fg.default | accent.primary | license |
|---|---|---|---|---|---|---|
| Latte | `catppuccin-latte` | light | `#eff1f5` | `#4c4f69` 7.06 | blue `#1e66f5` | MIT |
| Frappé | `catppuccin-frappe` | dark | `#303446` | `#c6d0f5` 8.06 | blue `#8caaee` | MIT |
| Macchiato | `catppuccin-macchiato` | dark | `#24273a` | `#cad3f5` 9.92 | blue `#8aadf4` | MIT |
| Mocha | `catppuccin-mocha` | dark | `#1e1e2e` | `#cdd6f4` 11.34 | blue `#89b4fa` | MIT |

Sources:

- Latte: palette <https://github.com/catppuccin/palette/blob/main/palette.json>; terminal <https://github.com/catppuccin/kitty/blob/main/themes/latte.conf>; role spec <https://github.com/catppuccin/catppuccin/blob/main/docs/style-guide.md>.
- Frappé: palette <https://github.com/catppuccin/palette/blob/main/palette.json>; terminal <https://github.com/catppuccin/kitty/blob/main/themes/frappe.conf>; role spec <https://github.com/catppuccin/catppuccin/blob/main/docs/style-guide.md>.
- Macchiato: palette <https://github.com/catppuccin/palette/blob/main/palette.json>; terminal <https://github.com/catppuccin/kitty/blob/main/themes/macchiato.conf>; role spec <https://github.com/catppuccin/catppuccin/blob/main/docs/style-guide.md>.
- Mocha: palette <https://github.com/catppuccin/palette/blob/main/palette.json>; terminal <https://github.com/catppuccin/kitty/blob/main/themes/mocha.conf>; role spec <https://github.com/catppuccin/catppuccin/blob/main/docs/style-guide.md>.

## Palette (official hex)

| name | Latte | Frappé | Macchiato | Mocha |
|---|---|---|---|---|
| rosewater | `#dc8a78` | `#f2d5cf` | `#f4dbd6` | `#f5e0dc` |
| flamingo | `#dd7878` | `#eebebe` | `#f0c6c6` | `#f2cdcd` |
| pink | `#ea76cb` | `#f4b8e4` | `#f5bde6` | `#f5c2e7` |
| mauve | `#8839ef` | `#ca9ee6` | `#c6a0f6` | `#cba6f7` |
| red | `#d20f39` | `#e78284` | `#ed8796` | `#f38ba8` |
| maroon | `#e64553` | `#ea999c` | `#ee99a0` | `#eba0ac` |
| peach | `#fe640b` | `#ef9f76` | `#f5a97f` | `#fab387` |
| yellow | `#df8e1d` | `#e5c890` | `#eed49f` | `#f9e2af` |
| green | `#40a02b` | `#a6d189` | `#a6da95` | `#a6e3a1` |
| teal | `#179299` | `#81c8be` | `#8bd5ca` | `#94e2d5` |
| sky | `#04a5e5` | `#99d1db` | `#91d7e3` | `#89dceb` |
| sapphire | `#209fb5` | `#85c1dc` | `#7dc4e4` | `#74c7ec` |
| blue | `#1e66f5` | `#8caaee` | `#8aadf4` | `#89b4fa` |
| lavender | `#7287fd` | `#babbf1` | `#b7bdf8` | `#b4befe` |
| text | `#4c4f69` | `#c6d0f5` | `#cad3f5` | `#cdd6f4` |
| subtext1 | `#5c5f77` | `#b5bfe2` | `#b8c0e0` | `#bac2de` |
| subtext0 | `#6c6f85` | `#a5adce` | `#a5adcb` | `#a6adc8` |
| overlay2 | `#7c7f93` | `#949cbb` | `#939ab7` | `#9399b2` |
| overlay1 | `#8c8fa1` | `#838ba7` | `#8087a2` | `#7f849c` |
| overlay0 | `#9ca0b0` | `#737994` | `#6e738d` | `#6c7086` |
| surface2 | `#acb0be` | `#626880` | `#5b6078` | `#585b70` |
| surface1 | `#bcc0cc` | `#51576d` | `#494d64` | `#45475a` |
| surface0 | `#ccd0da` | `#414559` | `#363a4f` | `#313244` |
| base | `#eff1f5` | `#303446` | `#24273a` | `#1e1e2e` |
| mantle | `#e6e9ef` | `#292c3c` | `#1e2030` | `#181825` |
| crust | `#dce0e8` | `#232634` | `#181926` | `#11111b` |

ANSI 0–15 (terminal slots, in order black … bright white):

| slot | Latte | Frappé | Macchiato | Mocha |
|---|---|---|---|---|
| 0 black | `#5c5f77` subtext1 | `#51576d` surface1 | `#494d64` surface1 | `#45475a` surface1 |
| 1 red | `#d20f39` red | `#e78284` red | `#ed8796` red | `#f38ba8` red |
| 2 green | `#40a02b` green | `#a6d189` green | `#a6da95` green | `#a6e3a1` green |
| 3 yellow | `#df8e1d` yellow | `#e5c890` yellow | `#eed49f` yellow | `#f9e2af` yellow |
| 4 blue | `#1e66f5` blue | `#8caaee` blue | `#8aadf4` blue | `#89b4fa` blue |
| 5 magenta | `#ea76cb` pink | `#f4b8e4` pink | `#f5bde6` pink | `#f5c2e7` pink |
| 6 cyan | `#179299` teal | `#81c8be` teal | `#8bd5ca` teal | `#94e2d5` teal |
| 7 white | `#acb0be` surface2 | `#b5bfe2` subtext1 | `#b8c0e0` subtext1 | `#bac2de` subtext1 |
| 8 br.black | `#6c6f85` subtext0 | `#626880` surface2 | `#5b6078` surface2 | `#585b70` surface2 |
| 9 br.red | `#d20f39` red | `#e78284` red | `#ed8796` red | `#f38ba8` red |
| 10 br.green | `#40a02b` green | `#a6d189` green | `#a6da95` green | `#a6e3a1` green |
| 11 br.yellow | `#df8e1d` yellow | `#e5c890` yellow | `#eed49f` yellow | `#f9e2af` yellow |
| 12 br.blue | `#1e66f5` blue | `#8caaee` blue | `#8aadf4` blue | `#89b4fa` blue |
| 13 br.magenta | `#ea76cb` pink | `#f4b8e4` pink | `#f5bde6` pink | `#f5c2e7` pink |
| 14 br.cyan | `#179299` teal | `#81c8be` teal | `#8bd5ca` teal | `#94e2d5` teal |
| 15 br.white | `#bcc0cc` surface1 | `#a5adce` subtext0 | `#a5adcb` subtext0 | `#a6adc8` subtext0 |

## Author's role rules

Source: [docs/style-guide.md](https://github.com/catppuccin/catppuccin/blob/main/docs/style-guide.md) ("General Usage", same for all flavors). Quote: "Legibility always comes first, so please use your own judgement."

| function | color | | function | color |
|---|---|---|---|---|
| Background pane | Base | | Links, URLs | Blue |
| Secondary panes | Crust, Mantle | | Success / Warnings / Errors | Green / Yellow / Red |
| Surface elements | Surface 0/1/2 | | Tags, pills | Blue |
| Overlays | Overlay 0/1/2 | | Selection background | Overlay 2 at 20-30% opacity |
| Body copy, main headline | Text | | Cursor | Rosewater |
| Sub-headlines, labels | Subtext 0/1 | | Terminal active / inactive / bell border | Lavender / Overlay 0 / Yellow |
| Subtle | Overlay 1 | | Terminal cursor text | Crust (Latte: Base) |
| On accent | Base | | Diff added / removed / changed | Green / Red / Blue |

Editors: comments Overlay 2, line numbers Overlay 1, active line number Lavender, keyword Mauve, information Teal. App ports make the accent a user choice (`{accent}` in catppuccin/lazygit and catppuccin/yazi: 14 files per flavor), so `accent.primary` is a choice (blue).

## Token map

Cell = palette name, hex, contrast. Contrast is vs `bg.base` (for bg tokens it shows the step from the base), `selection.fg` is vs `selection.bg`, `fg.on-accent` is the lowest ratio over the accent and status fills. FAIL = below the [contrast floor](../formats.md#contrast-floors). *→ token* = unmapped tier-2 token resolved through its fallback; *derived* = computed hex (see Basis).

### Tier 1 (always mapped)

| token | Latte | Frappé | Macchiato | Mocha | basis |
|---|---|---|---|---|---|
| `bg.base` | base `#eff1f5` 1.00 | base `#303446` 1.00 | base `#24273a` 1.00 | base `#1e1e2e` 1.00 | spec: style guide 'Background Pane = Base' |
| `bg.inset` | mantle `#e6e9ef` 1.08 | mantle `#292c3c` 1.12 | mantle `#1e2030` 1.09 | mantle `#181825` 1.07 | spec: 'Secondary Panes = Crust, Mantle'; consensus: statusline bg mantle 2/4 ports |
| `bg.surface` | surface0 `#ccd0da` 1.37 | surface0 `#414559` 1.30 | surface0 `#363a4f` 1.31 | surface0 `#313244` 1.30 | spec: 'Surface Elements = Surface 0/1/2'; port: catppuccin/helix ui.popup = surface0 |
| `bg.raised` | surface1 `#bcc0cc` 1.61 | surface1 `#51576d` 1.72 | surface1 `#494d64` 1.77 | surface1 `#45475a` 1.80 | consensus: 3/7 ports use surface1 for the list cursor (helix ui.menu.selected, k9s cursorBg, btop selected_bg) |
| `fg.default` | text `#4c4f69` 7.06 | text `#c6d0f5` 8.06 | text `#cad3f5` 9.92 | text `#cdd6f4` 11.34 | spec: 'Body Copy, Main Headline = Text' |
| `fg.muted` | subtext1 `#5c5f77` 5.53 | subtext0 `#a5adce` 5.55 | subtext0 `#a5adcb` 6.62 | subtext0 `#a6adc8` 7.37 | spec: 'Sub-Headlines, Labels = Subtext 0/1'; subtext0 is 4.37:1 on Latte base, subtext1 (same role) 5.53:1 (varies by variant: see JSON) |
| `fg.faint` | overlay2 `#7c7f93` 3.49 | overlay1 `#838ba7` 3.65 | overlay1 `#8087a2` 4.14 | overlay1 `#7f849c` 4.44 | spec: 'Overlays = Overlay 0/1/2', editor comments = Overlay 2; overlay1 is 2.83:1 on Latte base, overlay2 … (varies by variant: see JSON) |
| `fg.on-accent` | base `#eff1f5` 2.31 FAIL | base `#303446` 4.65 | base `#24273a` 5.96 | base `#1e1e2e` 7.08 | spec: 'On Accent = Base' |
| `border.default` | overlay0 `#9ca0b0` 2.30 | overlay0 `#737994` 2.87 | overlay0 `#6e738d` 3.15 | overlay0 `#6c7086` 3.36 | spec: terminal 'Inactive Border = Overlay 0' |
| `accent.primary` | blue `#1e66f5` 4.34 FAIL | blue `#8caaee` 5.34 | blue `#8aadf4` 6.57 | blue `#89b4fa` 7.79 | choice: ports make the accent user-selectable ({accent} in lazygit/yazi); blue = style-guide links/tags … |
| `accent.secondary` | mauve `#8839ef` 4.79 | mauve `#ca9ee6` 5.60 | mauve `#c6a0f6` 6.84 | mauve `#cba6f7` 8.07 | port: Textual secondary = mauve; style guide editor keyword hue |
| `selection.bg` | *derived* `#d2d4dc` 1.31 | *derived* `#494e63` 1.50 | *derived* `#404459` 1.53 | *derived* `#3b3d4f` 1.54 | spec: 'Selection Background = Overlay 2 at 20-30% opacity' -> derived: overlay2 @25% over base … |
| `status.error` | red `#d20f39` 4.80 | red `#e78284` 4.65 | red `#ed8796` 5.96 | red `#f38ba8` 7.08 | spec: 'Errors = Red' |
| `status.warning` | yellow `#df8e1d` 2.31 FAIL | yellow `#e5c890` 7.62 | yellow `#eed49f` 10.20 | yellow `#f9e2af` 12.91 | spec: 'Warnings = Yellow' |
| `status.success` | green `#40a02b` 2.96 FAIL | green `#a6d189` 7.10 | green `#a6da95` 9.17 | green `#a6e3a1` 11.03 | spec: 'Success = Green' |
| `status.info` | teal `#179299` 3.31 FAIL | teal `#81c8be` 6.41 | teal `#8bd5ca` 8.74 | teal `#94e2d5` 11.01 | spec: editor 'Information = Teal' |

### Tier 2

| token | Latte | Frappé | Macchiato | Mocha | basis |
|---|---|---|---|---|---|
| `bg.overlay` | surface0 `#ccd0da` 1.37 | surface0 `#414559` 1.30 | surface0 `#363a4f` 1.31 | surface0 `#313244` 1.30 | port: catppuccin/helix ui.popup and ui.menu bg = surface0 |
| `bg.stripe` | *→ bg.inset* `#e6e9ef` 1.08 | *→ bg.inset* `#292c3c` 1.12 | *→ bg.inset* `#1e2030` 1.09 | *→ bg.inset* `#181825` 1.07 | fallback |
| `fg.title` | text `#4c4f69` 7.06 | text `#c6d0f5` 8.06 | text `#cad3f5` 9.92 | text `#cdd6f4` 11.34 | spec: 'Main Headline = Text' |
| `border.focus` | lavender `#7287fd` 2.81 FAIL | lavender `#babbf1` 6.72 | lavender `#b7bdf8` 8.17 | lavender `#b4befe` 9.17 | spec: terminal 'Active Border = Lavender'; port: Textual $border, k9s frame.border.focusColor |
| `selection.fg` | text `#4c4f69` 5.40 | text `#c6d0f5` 5.38 | text `#cad3f5` 6.46 | text `#cdd6f4` 7.38 | spec: body text = Text; port: helix ui.menu.selected fg = text |
| `selection.inactive.bg` | surface0 `#ccd0da` 1.37 | surface0 `#414559` 1.30 | surface0 `#363a4f` 1.31 | surface0 `#313244` 1.30 | choice: one step below the active selection fill (lazygit's only value, overlay0, is brighter than the … |
| `text-selection.bg` | *derived* `#d2d4dc` 1.31 | *derived* `#494e63` 1.50 | *derived* `#404459` 1.53 | *derived* `#3b3d4f` 1.54 | spec: 'Selection Background = Overlay 2 at 20-30% opacity' |
| `cursor.bg` | rosewater `#dc8a78` 2.34 | rosewater `#f2d5cf` 8.91 | rosewater `#f4dbd6` 11.18 | rosewater `#f5e0dc` 12.95 | spec: 'Cursor = Rosewater' |
| `cursor.fg` | base `#eff1f5` 1.00 | crust `#232634` 1.22 | crust `#181926` 1.18 | crust `#11111b` 1.14 | spec: terminal cursor text = Base (Latte) (varies by variant: see JSON) |
| `search.match` | *→ status.warning* `#df8e1d` 2.31 | *→ status.warning* `#e5c890` 7.62 | *→ status.warning* `#eed49f` 10.20 | *→ status.warning* `#f9e2af` 12.91 | fallback |
| `link` | blue `#1e66f5` 4.34 FAIL | blue `#8caaee` 5.34 | blue `#8aadf4` 6.57 | blue `#89b4fa` 7.79 | spec: 'Links, URLs = Blue' |
| `keyhint.key` | blue `#1e66f5` 4.34 FAIL | blue `#8caaee` 5.34 | blue `#8aadf4` 6.57 | blue `#89b4fa` 7.79 | consensus: 3/5 ports (lazygit optionsTextColor, k9s frame.menu.keyColor, btop hi_fg) |
| `keyhint.desc` | text `#4c4f69` 7.06 | text `#c6d0f5` 8.06 | text `#cad3f5` 9.92 | text `#cdd6f4` 11.34 | consensus: 2/3 ports (k9s frame.menu.fgColor, Textual footer description) |
| `statusbar.bg` | mantle `#e6e9ef` 1.08 | mantle `#292c3c` 1.12 | mantle `#1e2030` 1.09 | mantle `#181825` 1.07 | consensus: 2/4 ports (helix ui.statusline, gitui cmdbar_bg); spec secondary panes |
| `statusbar.fg` | subtext1 `#5c5f77` 5.53 | subtext1 `#b5bfe2` 6.75 | subtext1 `#b8c0e0` 8.17 | subtext1 `#bac2de` 9.26 | port: catppuccin/helix ui.statusline fg = subtext1; spec labels = Subtext 0/1 |
| `tab.active.fg` | *→ accent.primary* `#1e66f5` 4.34 | *→ accent.primary* `#8caaee` 5.34 | *→ accent.primary* `#8aadf4` 6.57 | *→ accent.primary* `#89b4fa` 7.79 | fallback |
| `tab.active.bg` | *→ bg.raised* `#bcc0cc` 1.61 | *→ bg.raised* `#51576d` 1.72 | *→ bg.raised* `#494d64` 1.77 | *→ bg.raised* `#45475a` 1.80 | fallback |
| `tab.inactive.fg` | *→ fg.muted* `#5c5f77` 5.53 | *→ fg.muted* `#a5adce` 5.55 | *→ fg.muted* `#a5adcb` 6.62 | *→ fg.muted* `#a6adc8` 7.37 | fallback |
| `table.header` | *→ fg.default* `#4c4f69` 7.06 | *→ fg.default* `#c6d0f5` 8.06 | *→ fg.default* `#cad3f5` 9.92 | *→ fg.default* `#cdd6f4` 11.34 | fallback |
| `mark` | *→ accent.secondary* `#8839ef` 4.79 | *→ accent.secondary* `#ca9ee6` 5.60 | *→ accent.secondary* `#c6a0f6` 6.84 | *→ accent.secondary* `#cba6f7` 8.07 | fallback |
| `scrollbar.thumb` | overlay2 `#7c7f93` 3.49 | overlay2 `#949cbb` 4.53 | overlay2 `#939ab7` 5.29 | overlay2 `#9399b2` 5.81 | port: catppuccin/kitty scrollbar_handle_color = overlay2 |
| `scrollbar.track` | surface1 `#bcc0cc` 1.61 | surface1 `#51576d` 1.72 | surface1 `#494d64` 1.77 | surface1 `#45475a` 1.80 | port: catppuccin/kitty scrollbar_track_color = surface1 |
| `diff.added` | green `#40a02b` 2.96 | green `#a6d189` 7.10 | green `#a6da95` 9.17 | green `#a6e3a1` 11.03 | spec: diff added = Green |
| `diff.removed` | red `#d20f39` 4.80 | red `#e78284` 4.65 | red `#ed8796` 5.96 | red `#f38ba8` 7.08 | spec: diff removed = Red |
| `diff.changed` | blue `#1e66f5` 4.34 | blue `#8caaee` 5.34 | blue `#8aadf4` 6.57 | blue `#89b4fa` 7.79 | spec: diff changed = Blue |
| `ramp.low` | green `#40a02b` 2.96 | green `#a6d189` 7.10 | green `#a6da95` 9.17 | green `#a6e3a1` 11.03 | port: catppuccin/btop temp_start = green; cross-scheme: severity ramp green->yellow->red |
| `ramp.mid` | yellow `#df8e1d` 2.31 | yellow `#e5c890` 7.62 | yellow `#eed49f` 10.20 | yellow `#f9e2af` 12.91 | port: catppuccin/btop temp_mid = yellow |
| `ramp.high` | red `#d20f39` 4.80 | red `#e78284` 4.65 | red `#ed8796` 5.96 | red `#f38ba8` 7.08 | port: catppuccin/btop temp_end = red |

Derived hex values (computed, not palette entries; `blend(a, b, α)` = a composited over b at opacity α):

- Latte: `selection.bg`, `text-selection.bg` = `#d2d4dc` = blend(overlay2, base, 0.25)
- Frappé: `selection.bg`, `text-selection.bg` = `#494e63` = blend(overlay2, base, 0.25)
- Macchiato: `selection.bg`, `text-selection.bg` = `#404459` = blend(overlay2, base, 0.25)
- Mocha: `selection.bg`, `text-selection.bg` = `#3b3d4f` = blend(overlay2, base, 0.25)

## Contrast findings

| variant | truecolor failures | 16-color failures (after overrides) | 256-color failures (OKLab nearest) |
|---|---|---|---|
| Latte | status.warning 2.31, status.success 2.96, status.info 3.31, accent.primary 4.34, keyhint.key 4.34, link 4.34, border.focus 2.81, fg.on-accent 2.31 | status.warning 2.31, status.success 2.96, status.info 3.31, accent.primary 4.34, keyhint.key 4.34, link 4.34, fg.on-accent 2.31 | status.warning 2.46, status.success 2.54, status.info 3.76, accent.primary 4.44, keyhint.key 4.44, link 4.44, border.focus 2.83, fg.on-accent 2.46 |
| Frappé | none | none | status.error 4.17, fg.on-accent 4.17 |
| Macchiato | none | none | none |
| Mocha | none | none | none |

Rule for failures: the official mapping is kept unless the palette offers a same-role entry that passes (those swaps are listed in Basis). Where a status color fails, never rely on it alone: pair it with a glyph and a word (see [../color-tokens.md](../color-tokens.md#never-color-only)).

## 16-color mode

Per-theme `ansi16` overrides of the `_tokens.json` defaults (spec = `slot [attrs]`; ratio vs the terminal background in that mode):

| token | default | Latte | Frappé | Macchiato | Mocha |
|---|---|---|---|---|---|
| `fg.muted` | `default dim` | `0` 5.53 | `15` 5.55 | `15` 6.62 | `15` 7.37 |
| `fg.faint` | `8` | · | `default dim` 3.60 | `default dim` 4.09 | `default dim` 4.38 |
| `keyhint.desc` | `default dim` | `default` 7.06 | · | · | · |
| `tab.inactive.fg` | `default dim` | `0` 5.53 | · | · | · |

## Quirks and discrepancy decisions

- Discrepancy (Latte terminal): catppuccin/alacritty latte inverts black/white and the brights vs catppuccin/kitty and the style guide; kept kitty (matches the style guide: black = subtext1, white = surface2, bright black = subtext0, bright white = surface1). (Latte)
- Discrepancy (brights): ports set ANSI 9-14 identical to 1-6; palette.json defines generated variants. Kept the port values. (Latte)
- Catppuccin does not invert the chrome ladder in Latte: mantle/crust (secondary panes) are darker than base, as in the dark flavors (spec). (Latte)
- Light-theme limit: yellow (2.31:1), green (2.96:1) and teal (3.31:1) on base fail 4.5:1 and no same-role palette entry passes; keep them for glyphs/badges and pair with a word or icon. (Latte)
- Discrepancy (ANSI 7/15): the style guide and palette.json say white = subtext0, bright white = subtext1; both official ports (kitty, alacritty) ship the swap (7 = subtext1, 15 = subtext0). Kept the port values: they are what users' terminals actually show. (Frappé, Macchiato, Mocha)
- Discrepancy (brights): ports set ANSI 9-14 identical to 1-6; palette.json defines generated brighter variants. Kept the port values, so bold-as-bright cannot change hue. (Frappé, Macchiato, Mocha)
- Terminal selection is opaque rosewater/base in kitty; tokens use the style-guide rule (overlay2 at 25% over base) for UI selection instead. (Frappé, Macchiato, Mocha)
- Reviewed the orchestrator's worked example: kept every mapping; added tier-2 tokens with evidence (fg.title, keyhint.desc, scrollbar.*, ramp.*, cursor.fg) and per-theme ansi16 overrides. (Mocha)

## App ports

O = official (scheme org or scheme repo extras), B = bundled in the app repo, C = community repo, - = none found (checked 2026-10).

| variant | helix | lazygit | k9s | btop | yazi | gitui | textual |
|---|---|---|---|---|---|---|---|
| Latte | O | O | O | O | O | O | B |
| Frappé | O | O | O | O | O | O | B |
| Macchiato | O | O | O | O | O | O | B |
| Mocha | O | O | O | O | O | O | B |
