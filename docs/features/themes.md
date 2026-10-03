# Themes

The skill ships 25 theme variants of 10 color schemes, each a JSON file that maps the 44 semantic tokens to the
scheme's official palette ([tokens, not colors](../concepts.md#tokens-not-colors)). Three scripts preview, check and
export them.

![The Fleet demo frame rendered in all 25 themes, five per row, each labelled with its theme id](../img/themes.png)

*One frame, 25 themes: Catppuccin (frappe, latte, macchiato, mocha), Dracula (alucard, classic), Everforest (dark,
light), Gruvbox (dark, light), Kanagawa (dragon, lotus, wave), Nord (dark), One Dark (dark, light), Rosé Pine (dawn,
main, moon), Solarized (dark, light), Tokyo Night (day, moon, night, storm).*

Theme ids are `<scheme>-<variant>` (`catppuccin-mocha`, `gruvbox-light`); every script also takes a path to a theme
JSON. Which variant passes which contrast floor, and which to pick for what, is in the skill's
[color-schemes.md](../../skills/tui-design/references/color-schemes.md#how-to-choose) (short version: `catppuccin-mocha`
is the safe dark default; `dracula-alucard` is the only light variant that passes every floor).

## What a theme holds

`references/themes/<id>.json`: the terminal colors (background, foreground, cursor, selection and the 16 ANSI
slots from the scheme's official terminal port), a value per token (a palette name or hex), optional `ansi16`
overrides that say what each token becomes in a 16-color terminal, a `provenance` entry per token (`spec: …` when
the scheme's style guide names the role, `choice: …` otherwise), the `sources` and the upstream `license`. Format:
[formats.md](../../skills/tui-design/references/formats.md#theme-json).

## Preview: `preview_theme.py`

```bash
python3 skills/tui-design/scripts/preview_theme.py catppuccin-mocha              # truecolor
python3 skills/tui-design/scripts/preview_theme.py catppuccin-mocha --depth 16   # through your terminal's own palette
python3 skills/tui-design/scripts/preview_theme.py gruvbox-light --depth none | less
```

Prints, in your terminal, the terminal slots, the neutral ladder, every token as a labelled swatch (foreground
tokens as text on `bg.base`, background tokens as filled blocks) and a sample UI. `--depth 16` resolves tokens
through `ansi16`, so it shows what users with that scheme in their terminal will see.

## Contrast: `contrast_check.py`

```bash
python3 skills/tui-design/scripts/contrast_check.py catppuccin-mocha
python3 skills/tui-design/scripts/contrast_check.py catppuccin-mocha --depth 16
python3 skills/tui-design/scripts/contrast_check.py --all --format json
```

WCAG 2.x ratios for each token pair that matters, against `bg.base` unless noted: `fg.default`, `fg.muted`, the four
`status.*`, `accent.primary`, `keyhint.key` and `link` need 4.5:1; `fg.faint` and `border.focus` need 3:1;
`selection.fg` on `selection.bg` and `fg.on-accent` on each fill need 4.5:1. Advisory rows (text on the selected
row, the focus border against the normal one) never change the exit status. Exit 1 when a required floor fails.

`--depth 16` checks the theme as a 16-color terminal draws it: each token becomes one of the scheme's 16 terminal
colors or the terminal default, `dim` is modelled as a blend, `reverse` swaps the pair. A theme that passes at
truecolor can fail here, which is why the skill checks both. The floor values live in
[formats.md](../../skills/tui-design/references/formats.md#contrast-floors).

## Export: `export_theme.py`

```bash
python3 skills/tui-design/scripts/export_theme.py catppuccin-mocha --target textual -o theme.py
python3 skills/tui-design/scripts/export_theme.py catppuccin-mocha --target json -o theme.json
```

| Target | Output |
|---|---|
| `textual` | a Python module with a Textual `Theme` |
| `ink` | a JS module (valid in TypeScript): the token map and an `@inkjs/ui` theme |
| `lipgloss` | a Go `package theme` for Lip Gloss v2 (Bubble Tea) |
| `ratatui` | a Rust module |
| `gum` | `GUM_*` environment variables: `source` the file, then run gum |
| `css` | CSS custom properties |
| `json` | the flat resolved theme the [proto-starters](starters.md) read |

Values are truecolor hex from the resolved tokens; the frameworks downsample to 256 or 16 colors themselves. Each
file starts with a header naming the theme and its sources.

## Adding a theme

Start from `catppuccin-mocha.json`, use only the scheme's official palette and terminal port, record provenance
for every token, and check both depths. The steps are in [architecture.md](../contributing/architecture.md#add-a-theme).
