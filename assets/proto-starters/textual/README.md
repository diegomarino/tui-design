# Fleet — Textual starter

The canonical "Fleet" demo screen (`../../demo/fleet--normal--80x24.mock`) in Textual: header band with tabs,
focused list, detail panel with severity gauges, message line, key-hint bar. Adapts to any size >= 80x24; below that it
shows a centered "Terminal too small — need 80×24, have C×R".

Verified against the mock: at 80x24 truecolor the frame is cell-for-cell identical (characters, fg/bg, bold) across 7 themes, and
`--depth 16` matches `render_mockup.py --depth 16` (0 differing cells for catppuccin-mocha and everforest-dark). There is no 120x30 mock:
at 120x30 the Textual gauges widen with the detail pane (up to 60 cells), so Textual differs from Bubble Tea/Ratatui (40-cell gauges) in 92
cells and matches Ink. `--depth 256` uses Rich's quantizer, so it differs from the mock's 256-color rounding.

Pinned (verified 2026-10-01): Python >= 3.11, `textual==8.2.8` (exact: `--frame` uses a private API; Rich 15.0.0 comes with it).

## Copy it into your project
```sh
export SKILL_DIR=/path/to/tui-design            # the skill directory (SKILL.md lives there)
cp -R "$SKILL_DIR/assets/proto-starters/textual" ./fleet-ui && cd ./fleet-ui
uv sync                                         # project-local .venv; no global installs
python3 "$SKILL_DIR/scripts/export_theme.py" catppuccin-mocha --target json -o theme.json   # any theme ID
uv run python -m fleet --frame --cols 80 --rows 24 --theme theme.json --depth truecolor > fleet.ansi
./capture.sh catppuccin-mocha out/              # frames at 80x24 and 120x30; or ./capture.sh theme.json out/
```
`--theme` takes a flat theme JSON path or a theme ID (an ID is exported through `$SKILL_DIR/scripts/export_theme.py`, so it needs
`SKILL_DIR`, or the starter still inside the skill). `capture.sh` resolves the skill the same way (`SKILL_DIR` first, then `../../..`) and stops
with an error naming `SKILL_DIR` if neither works; with a JSON path no skill is needed. Keep the frame mode in the copy.

## Install and run
```sh
uv sync                          # project-local .venv; no global installs
uv run python -m fleet           # interactive: up/down (or j/k) select, tab switches pane focus, q quits
uv run python -m fleet --theme theme.json --depth 256     # --theme: JSON path or theme ID
```

## One static frame (for gallery / compare / audit)
```sh
uv run python -m fleet --frame --cols 120 --rows 30 --theme theme.json --depth truecolor > fleet.ansi
./capture.sh catppuccin-mocha out/    # writes out/textual--normal--80x24.ansi and out/textual--normal--120x30.ansi
DEPTH=16 ./capture.sh catppuccin-latte out/
```
Frame recipe: `App.run_test(size=(cols, rows))` + `pilot.pause()`, then render the compositor strips
(`app.screen._compositor.render_update(full=True, ...)`) through a Rich `Console(color_system=...)` — exactly
`rows` lines, no cursor-move codes. This is a **private API** (`fleet/__main__.py:frame_to_ansi`); re-verify when
bumping Textual. `App.export_screenshot()` is the public alternative but only yields SVG.

## Theme tokens -> Textual
`theme.json` = `python3 "$SKILL_DIR/scripts/export_theme.py" ID --target json -o theme.json` (default is catppuccin-mocha).
`fleet/theme.py` registers a `Theme` and TCSS (`fleet/app.tcss`) uses only variables:
- Textual slots: primary/accent <- `accent.primary`, secondary <- `accent.secondary`, success/warning/error <- `status.*`,
  foreground <- `fg.default`, background <- `bg.base`, surface <- `bg.surface`, panel <- `bg.raised`, `dark` <- appearance.
- Every token also becomes a theme variable `$tok-<token-with-dashes>` (`border.focus` -> `$tok-border-focus`),
  e.g. `#services:focus { border: round $tok-border-focus; }`. Textual's built-ins do not cover keyhint/ramp/statusbar/tab tokens.
- Widget text is markup built from tokens: `self.m("running", "status.success", on="selection.bg", bold=True)`.
- depth `16`: tokens resolve to `ansi_<name>` colors from the theme's `ansi16` map and the app runs with
  `ansi_color=True` (native ANSI codes, terminal palette); `256` uses Rich's down-sampling. A `reverse` fill (`selection.bg`) inverts each
  segment keeping its own fg spec; a `bg` fg spec (e.g. `tab.active.fg` in everforest-dark) becomes the fill token's `ansi_<name>` + `reverse`,
  so the text takes the terminal background color on the fill (`Tokens.sty`).

## Caveats
- Private compositor API for `--frame` (see above); the pin is the mitigation.
- Border titles come with built-in padding, so titles are passed without spaces (`border_title = "Services (6)"`).
- Textual paints `bg.base` on the screen, so a translucent terminal background is lost (unlike Ink); at depth 16 it is `ansi_default`.
- Focus border uses `:focus` on the pane widget, so `tab` (built-in `focus_next`) moves `border.focus`; hints in the key bar are static.
- Frame mode renders without notifications/tooltips (run_test defaults).
