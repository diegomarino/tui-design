# Solarized (Dark, Light): palette → token map

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [At a glance](#at-a-glance) · L15–25 — variant ids, appearance, base/text/accent hex, license and sources.
- [Palette (official hex)](#palette-official-hex) · L27–67 — the exact official hex of a named palette entry.
- [Author's role rules](#authors-role-rules) · L69–71 — the scheme author's own rules for what each colour is for.
- [Token map](#token-map) · L73–134 — the palette entry, hex and contrast behind each semantic token (tier 1 and tier 2).
- [Contrast findings](#contrast-findings) · L136–143 — which tokens fail a floor per variant, in truecolor, 16 and 256 colours.
- [16-color mode](#16-color-mode) · L145–160 — the per-variant `ansi16` overrides and their ratios.
- [Quirks and discrepancy decisions](#quirks-and-discrepancy-decisions) · L162–168 — where sources disagree and which value was kept, light-theme limits.
- [App ports](#app-ports) · L170–177 — whether helix, lazygit, k9s, btop, yazi, gitui or Textual ship a port of this scheme.

Read this when a TUI uses Solarized and you need the exact palette entry, hex and contrast for each semantic token, the author's role rules, and the 16-color caveats. Token meanings: [../color-tokens.md](../color-tokens.md). All schemes: [../color-schemes.md](../color-schemes.md). Machine-readable: [`solarized-dark.json`](../themes/solarized-dark.json), [`solarized-light.json`](../themes/solarized-light.json).

## At a glance

| variant | id | appearance | bg.base | fg.default | accent.primary | license |
|---|---|---|---|---|---|---|
| Dark | `solarized-dark` | dark | `#002b36` | `#839496` 4.75 | blue `#268bd2` | MIT |
| Light | `solarized-light` | light | `#fdf6e3` | `#657b83` 4.13 | blue `#268bd2` | MIT |

Sources:

- Dark: palette <https://github.com/altercation/solarized/blob/master/README.md#the-values>; terminal <https://github.com/solarized/xresources/blob/master/Xresources.dark>; role spec <https://github.com/altercation/solarized/blob/master/README.md#usage--development>.
- Light: palette <https://github.com/altercation/solarized/blob/master/README.md#the-values>; terminal <https://github.com/solarized/xresources/blob/master/Xresources.light>; role spec <https://github.com/altercation/solarized/blob/master/README.md#usage--development>.

## Palette (official hex)

| name | Dark | Light |
|---|---|---|
| base03 | `#002b36` | `#002b36` |
| base02 | `#073642` | `#073642` |
| base01 | `#586e75` | `#586e75` |
| base00 | `#657b83` | `#657b83` |
| base0 | `#839496` | `#839496` |
| base1 | `#93a1a1` | `#93a1a1` |
| base2 | `#eee8d5` | `#eee8d5` |
| base3 | `#fdf6e3` | `#fdf6e3` |
| yellow | `#b58900` | `#b58900` |
| orange | `#cb4b16` | `#cb4b16` |
| red | `#dc322f` | `#dc322f` |
| magenta | `#d33682` | `#d33682` |
| violet | `#6c71c4` | `#6c71c4` |
| blue | `#268bd2` | `#268bd2` |
| cyan | `#2aa198` | `#2aa198` |
| green | `#859900` | `#859900` |

ANSI 0–15 (terminal slots, in order black … bright white):

| slot | Dark | Light |
|---|---|---|
| 0 black | `#073642` base02 | `#073642` base02 |
| 1 red | `#dc322f` red | `#dc322f` red |
| 2 green | `#859900` green | `#859900` green |
| 3 yellow | `#b58900` yellow | `#b58900` yellow |
| 4 blue | `#268bd2` blue | `#268bd2` blue |
| 5 magenta | `#d33682` magenta | `#d33682` magenta |
| 6 cyan | `#2aa198` cyan | `#2aa198` cyan |
| 7 white | `#eee8d5` base2 | `#eee8d5` base2 |
| 8 br.black | `#002b36` base03 | `#002b36` base03 |
| 9 br.red | `#cb4b16` orange | `#cb4b16` orange |
| 10 br.green | `#586e75` base01 | `#586e75` base01 |
| 11 br.yellow | `#657b83` base00 | `#657b83` base00 |
| 12 br.blue | `#839496` base0 | `#839496` base0 |
| 13 br.magenta | `#6c71c4` violet | `#6c71c4` violet |
| 14 br.cyan | `#93a1a1` base1 | `#93a1a1` base1 |
| 15 br.white | `#fdf6e3` base3 | `#fdf6e3` base3 |

## Author's role rules

Source: [README "Usage & Development"](https://github.com/altercation/solarized/blob/master/README.md#usage--development): "four monotones form the core values (with an optional fifth for emphasized content)"; dark: "the normal relationship for background and body text is `base03:base0` (please note that body text is **not** `base00`)... text can be highlighted using a combination of `base02:base1`... simply inverted in the case of a light background." base01 = comments/secondary content (dark), base1 = emphasis. The eight accents are identical in both modes and defined with equal lightness, so none reaches 4.5:1 on base3.

## Token map

Cell = palette name, hex, contrast. Contrast is vs `bg.base` (for bg tokens it shows the step from the base), `selection.fg` is vs `selection.bg`, `fg.on-accent` is the lowest ratio over the accent and status fills. FAIL = below the [contrast floor](../formats.md#contrast-floors). *→ token* = unmapped tier-2 token resolved through its fallback; *derived* = computed hex (see Basis).

### Tier 1 (always mapped)

| token | Dark | Light | basis |
|---|---|---|---|
| `bg.base` | base03 `#002b36` 1.00 | base3 `#fdf6e3` 1.00 | spec: dark background = base03 (varies by variant: see JSON) |
| `bg.inset` | base03 `#002b36` 1.00 | base3 `#fdf6e3` 1.00 | choice: no tone below base03 (varies by variant: see JSON) |
| `bg.surface` | base02 `#073642` 1.15 | base2 `#eee8d5` 1.14 | spec: base02 = background highlights (varies by variant: see JSON) |
| `bg.raised` | base02 `#073642` 1.15 | base2 `#eee8d5` 1.14 | spec: base02 = background highlights (only raised tone) (varies by variant: see JSON) |
| `fg.default` | base0 `#839496` 4.75 | base00 `#657b83` 4.13 FAIL | spec: 'body text is base0 on base03 (not base00)' (varies by variant: see JSON) |
| `fg.muted` | base01 `#586e75` 2.79 FAIL | base1 `#93a1a1` 2.48 FAIL | spec: base01 = comments / secondary content (varies by variant: see JSON) |
| `fg.faint` | base01 `#586e75` 2.79 FAIL | base1 `#93a1a1` 2.48 FAIL | spec: base01 = comments (only tone dimmer than body) (varies by variant: see JSON) |
| `fg.on-accent` | base03 `#002b36` 3.25 FAIL | base03 `#002b36` 3.25 FAIL | choice: Solarized accents are mid-luminance; base03 gives the highest ratio on them in both modes |
| `border.default` | base01 `#586e75` 2.79 | base1 `#93a1a1` 2.48 | choice: dimmest visible monotone (base02 is 1.15:1) (varies by variant: see JSON) |
| `accent.primary` | blue `#268bd2` 4.08 FAIL | blue `#268bd2` 3.41 FAIL | choice: Solarized identity hue; no accent reaches 4.5:1 in light mode |
| `accent.secondary` | violet `#6c71c4` 3.43 | violet `#6c71c4` 4.06 | choice: distinct from blue and from info cyan |
| `selection.bg` | base02 `#073642` 1.15 | base2 `#eee8d5` 1.14 | spec: highlighted pair base02:base1 (varies by variant: see JSON) |
| `status.error` | red `#dc322f` 3.25 FAIL | red `#dc322f` 4.29 FAIL | choice: accent red (README defines no UI roles) |
| `status.warning` | yellow `#b58900` 4.68 | yellow `#b58900` 2.98 FAIL | choice: accent yellow |
| `status.success` | green `#859900` 4.69 | green `#859900` 2.97 FAIL | choice: accent green |
| `status.info` | cyan `#2aa198` 4.75 | cyan `#2aa198` 2.93 FAIL | choice: accent cyan |

### Tier 2

| token | Dark | Light | basis |
|---|---|---|---|
| `bg.overlay` | base02 `#073642` 1.15 | base2 `#eee8d5` 1.14 | spec: background highlights |
| `bg.stripe` | *derived* `#00262f` 1.06 | *derived* `#f5efde` 1.06 | derived: bg.base darkened to 1.06:1 (weakest fill; bg.inset is invisible here, 1.00:1 vs inactive … (varies by variant: see JSON) |
| `fg.title` | base1 `#93a1a1` 5.61 | base01 `#586e75` 4.99 | spec: base1 = optional emphasized content (varies by variant: see JSON) |
| `border.focus` | *→ accent.primary* `#268bd2` 4.08 | *→ accent.primary* `#268bd2` 3.41 | fallback |
| `selection.fg` | base1 `#93a1a1` 4.86 | base01 `#586e75` 4.39 FAIL | spec: highlighted pair base02:base1 (varies by variant: see JSON) |
| `selection.inactive.bg` | *→ bg.surface* `#073642` 1.15 | *→ bg.surface* `#eee8d5` 1.14 | fallback |
| `text-selection.bg` | base02 `#073642` 1.15 | base2 `#eee8d5` 1.14 | spec: background highlights |
| `cursor.bg` | base1 `#93a1a1` 5.61 | base01 `#586e75` 4.99 | port: solarized/xresources cursorColor = base1 (varies by variant: see JSON) |
| `cursor.fg` | base03 `#002b36` 1.00 | base3 `#fdf6e3` 1.00 | choice: background tone |
| `search.match` | *→ status.warning* `#b58900` 4.68 | *→ status.warning* `#b58900` 2.98 | fallback |
| `link` | *→ accent.primary* `#268bd2` 4.08 FAIL | *→ accent.primary* `#268bd2` 3.41 FAIL | fallback |
| `keyhint.key` | *→ accent.primary* `#268bd2` 4.08 FAIL | *→ accent.primary* `#268bd2` 3.41 FAIL | fallback |
| `keyhint.desc` | *→ fg.muted* `#586e75` 2.79 | *→ fg.muted* `#93a1a1` 2.48 | fallback |
| `statusbar.bg` | base02 `#073642` 1.15 | base2 `#eee8d5` 1.14 | choice: background highlight band |
| `statusbar.fg` | base1 `#93a1a1` 5.61 | base01 `#586e75` 4.99 | spec: highlighted pair base02:base1 (varies by variant: see JSON) |
| `tab.active.fg` | *→ accent.primary* `#268bd2` 4.08 | *→ accent.primary* `#268bd2` 3.41 | fallback |
| `tab.active.bg` | *→ bg.raised* `#073642` 1.15 | *→ bg.raised* `#eee8d5` 1.14 | fallback |
| `tab.inactive.fg` | *→ fg.muted* `#586e75` 2.79 | *→ fg.muted* `#93a1a1` 2.48 | fallback |
| `table.header` | *→ fg.default* `#839496` 4.75 | *→ fg.default* `#657b83` 4.13 | fallback |
| `mark` | *→ accent.secondary* `#6c71c4` 3.43 | *→ accent.secondary* `#6c71c4` 4.06 | fallback |
| `scrollbar.thumb` | *→ fg.faint* `#586e75` 2.79 | *→ fg.faint* `#93a1a1` 2.48 | fallback |
| `scrollbar.track` | *→ border.default* `#586e75` 2.79 | *→ border.default* `#93a1a1` 2.48 | fallback |
| `diff.added` | *→ status.success* `#859900` 4.69 | *→ status.success* `#859900` 2.97 | fallback |
| `diff.removed` | *→ status.error* `#dc322f` 3.25 | *→ status.error* `#dc322f` 4.29 | fallback |
| `diff.changed` | *→ status.info* `#2aa198` 4.75 | *→ status.info* `#2aa198` 2.93 | fallback |
| `ramp.low` | green `#859900` 4.69 | green `#859900` 2.97 | cross-scheme: severity ramp |
| `ramp.mid` | yellow `#b58900` 4.68 | yellow `#b58900` 2.98 | cross-scheme: severity ramp |
| `ramp.high` | red `#dc322f` 3.25 | red `#dc322f` 4.29 | cross-scheme: severity ramp |

Derived hex values (computed, not palette entries; `blend(a, b, α)` = a composited over b at opacity α):

- Dark: `bg.stripe` = `#00262f` = see provenance
- Light: `bg.stripe` = `#f5efde` = see provenance

## Contrast findings

| variant | truecolor failures | 16-color failures (after overrides) | 256-color failures (OKLab nearest) |
|---|---|---|---|
| Dark | fg.muted 2.79, fg.faint 2.79, status.error 3.25, accent.primary 4.08, keyhint.key 4.08, link 4.08, fg.on-accent 3.25 | status.error 3.25, accent.primary 4.08, keyhint.key 4.08, link 4.08, fg.on-accent 3.25 | fg.muted 2.88, fg.faint 2.88, status.error 2.80, status.success 3.96, accent.primary 3.93, keyhint.key 3.93, link 3.93, fg.on-accent 2.80 |
| Light | fg.default 4.13, fg.muted 2.48, fg.faint 2.48, status.error 4.29, status.warning 2.98, status.success 2.97, status.info 2.93, accent.primary 3.41, keyhint.key 3.41, link 3.41, selection.fg 4.39, fg.on-accent 3.25 | fg.default 4.13, fg.muted 4.13, status.error 4.29, status.warning 2.98, status.success 2.97, status.info 2.93, accent.primary 3.41, keyhint.key 3.41, link 3.41, selection.fg 4.13, fg.on-accent 3.25 | fg.default 4.44, fg.muted 2.62, fg.faint 2.62, status.warning 3.27, status.success 3.74, status.info 2.65, accent.primary 3.77, keyhint.key 3.77, link 3.77, selection.fg 4.13, fg.on-accent 2.80 |

Rule for failures: the official mapping is kept unless the palette offers a same-role entry that passes (those swaps are listed in Basis). Where a status color fails, never rely on it alone: pair it with a glyph and a word (see [../color-tokens.md](../color-tokens.md#never-color-only)).

## 16-color mode

Per-theme `ansi16` overrides of the `_tokens.json` defaults (spec = `slot [attrs]`; ratio vs the terminal background in that mode):

| token | default | Dark | Light |
|---|---|---|---|
| `fg.muted` | `default dim` | `7 dim` 4.66 | `default` 4.13 |
| `fg.faint` | `8` | `7 dim` 4.66 | · |
| `fg.on-accent` | `bg` | · | `8` 3.25 |
| `border.default` | `8` | `default dim` 2.39 | · |
| `accent.secondary` | `5` | `13` 3.43 | `13` 4.06 |
| `keyhint.desc` | `default dim` | `7 dim` 4.66 | `8 dim` 3.57 |
| `tab.inactive.fg` | `default dim` | `7 dim` 4.66 | `8 dim` 3.57 |
| `mark` | `5` | `13` 3.43 | `13` 4.06 |
| `scrollbar.track` | `8` | `default dim` 2.39 | · |
| `diff.changed` | `4` | `6` 4.75 | · |

## Quirks and discrepancy decisions

- Terminal slots: solarized/xresources (same ANSI assignment in dark and light): 8 = base03 (= background, invisible), 9 = orange, 10-12/14 = monotones base01/base00/base0/base1, 13 = violet, 15 = base3. ansi16 overrides route faint text and borders to slot 10 (base01). (Dark)
- Discrepancy: altercation iterm2 files use color-managed values (bg #001e27); kept the canonical README/xresources hex. (Dark)
- Solarized has two text tones per mode: body base0 (4.75:1) and secondary base01 (2.79:1). fg.muted and fg.faint are both base01 and fail their floors; use fg.title (base1) for emphasis to keep hierarchy. (Dark)
- Terminal slots: solarized/xresources (identical ANSI assignment to dark): 8 = base03 (darkest, not faint), 10-12/14 = monotones. (Light)
- Body text base00 on base3 is 4.13:1 (spec pairing) and fails 4.5:1; no same-role tone passes. No accent reaches 4.5:1 on base3. (Light)

## App ports

O = official (scheme org or scheme repo extras), B = bundled in the app repo, C = community repo, - = none found (checked 2026-10).

| variant | helix | lazygit | k9s | btop | yazi | gitui | textual |
|---|---|---|---|---|---|---|---|
| Dark | B | - | B | B | - | - | B |
| Light | B | - | B | B | - | - | B |
