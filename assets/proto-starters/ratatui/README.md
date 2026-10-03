# Fleet — Ratatui starter

The canonical "Fleet" demo screen (`../../demo/fleet--normal--80x24.mock`) in Ratatui 0.30: header band with tabs,
focused list, detail panel with severity gauges, message line, key-hint bar. Adapts to any size >= 80x24 (list 32 cols
fixed, detail flexible); below that it shows a centered "Terminal too small — need 80×24, have C×R".

Verified against the mock (`../../demo/fleet--normal--80x24.mock`): at 80x24 truecolor the frame is cell-for-cell identical (characters, fg/bg, bold)
across 7 themes, and `--depth 16` matches `render_mockup.py --depth 16` (0 differing cells for catppuccin-mocha and everforest-dark).
There is no 120x30 mock: at 120x30 Bubble Tea and Ratatui render identical frames to each other (0 differing cells); Ink and Textual widen the
gauges with the detail pane. `--depth 256` uses this framework's own quantizer, so it differs from the mock's 256-color rounding.

Pinned (verified 2026-10-01): Rust >= 1.88 (edition 2024; tested 1.98.1), `ratatui` 0.30.2 (re-exports crossterm 0.29),
`serde` 1.0 + `serde_json` 1.0 (theme JSON). `Cargo.lock` is not shipped; cargo generates it.

## Copy it into your project
```sh
export SKILL_DIR=/path/to/tui-design            # the skill directory (SKILL.md lives there)
cp -R "$SKILL_DIR/assets/proto-starters/ratatui" ./fleet-ui && cd ./fleet-ui
python3 "$SKILL_DIR/scripts/export_theme.py" catppuccin-mocha --target json -o theme.json   # any theme ID
cargo run -q -- --frame --cols 80 --rows 24 --theme theme.json --depth truecolor > fleet.ansi
./capture.sh catppuccin-mocha out/              # frames at 80x24 and 120x30; or ./capture.sh theme.json out/
```
`capture.sh` finds the skill through `SKILL_DIR` first, then through `../../..` (the starter still inside the skill), and stops with an
error naming `SKILL_DIR` if neither works. It only needs the skill to turn a theme ID into JSON: with a JSON path (`./capture.sh theme.json out/`), no `SKILL_DIR` is needed.
`theme.json` here is a flat theme JSON (`{id, tokens, ansi16, ...}`); keep the frame mode (`--frame --cols --rows --theme --depth`) in the copy, it is how the design is audited.

## Run
```sh
cargo run                         # interactive (alt screen): up/down or j/k select, tab switches pane focus, r restart message, q quits
cargo run -- --theme theme.json   # a flat theme JSON path (the binary does not take theme IDs; capture.sh does)
cargo build --release && target/release/fleet
```
`enter`, `/`, `?` and the tabs 2/3 are drawn (part of the demo screen) but not wired.

## One static frame (for gallery / compare / audit)
```sh
cargo run -q -- --frame --cols 120 --rows 30 --theme theme.json --depth truecolor > fleet.ansi   # exactly --rows lines
./capture.sh catppuccin-mocha out/    # builds in a temp dir; writes out/ratatui--normal--80x24.ansi and ...120x30.ansi
DEPTH=16 ./capture.sh catppuccin-latte out/
```
Frame recipe: `Terminal::new(TestBackend::new(cols, rows))`, `terminal.draw(ui::render)`, then
`ansi::buffer_to_ansi(buffer, depth)`: one SGR run per style change, wide glyphs skip their continuation cells
(width from `Span::width`). Ratatui keeps `Color::Rgb` in cells, so color depth is applied by our serializer:
truecolor as-is, 256 = nearest of the xterm 16..255 cube/greys, 16 = the theme's `ansi16` specs (see below).
`--selected N` and `--focus-detail` pick another state.

## Theme tokens -> Ratatui
`theme.json` = `python3 "$SKILL_DIR/scripts/export_theme.py" ID --target json -o theme.json` (embedded default: catppuccin-mocha;
`export_theme.py --target ratatui` emits a ready-made const `Theme` if you prefer compile-time colors).
`src/theme.rs`: `Theme::new(&ThemeFile, ansi16)` returns a struct of `Style`s, one per UI role (the
`examples/apps/demo2/src/theme.rs` pattern); `ui.rs` only uses those fields.

| UI role | token(s) |
|---|---|
| header band / app name / tabs | `statusbar.bg`+`statusbar.fg`, `accent.primary` bold, `tab.active.fg` on `tab.active.bg`, `tab.inactive.fg`, `border.default` |
| focused / unfocused pane border | `border.focus` / `border.default`; titles `fg.title` bold |
| selected row, cursor | `selection.bg` (`selection.inactive.bg` when unfocused) as `List::highlight_style`, `selection.fg`, `accent.primary` |
| status glyphs and words | `status.success/warning/error`, `fg.faint` (stopped), `fg.muted` (running, unselected) |
| gauges | `ramp.low` (< 50 %), `ramp.mid` (< 80 %), `ramp.high`, empty `fg.faint` |
| footer | `statusbar.*`, `keyhint.key` bold, `keyhint.desc` |

The whole area is painted with `bg.base` once (`Block::new().style(base)`); widgets patch on top. 16-color mode builds the
`Style`s from the per-token `ansi16` specs (`"4 bold"`, `"default dim"`, `"reverse"`) with `Color::Indexed(0..15)`/`Reset`, so the
terminal's own palette is used. With `selection.bg = reverse` the `List` highlight adds REVERSED to every cell of the row, so each segment is
inverted keeping its own fg spec and bold (same as `render_mockup.py --depth 16`); the unfocused row follows `selection.inactive.bg`.
A `bg` fg spec (e.g. `tab.active.fg` in everforest-dark) is drawn as the fill token's slot as fg + REVERSED (`Resolver::fg_on`), so the
text takes the terminal background color on the fill.

## Caveats
- Immediate mode: `ui::render` rebuilds every widget each frame; `ListState` is created per frame from `App.sel`.
- `List::highlight_style` is applied over the whole row after the spans, so it only sets the background (spans keep their fg).
- Block titles start right after the corner, so the title line is `"─"` + `" Title "`; title spans inherit the border style, so `fg.title` sets its fg explicitly (also `Reset` in 16-color mode) or the title would take the border color.
- Gauges are hand-built spans (`█`/`░`) to match the mock exactly; `Gauge`/`LineGauge` widgets draw their own fill glyphs.
- `Terminal::new(TestBackend)` frames never run the event loop: no timers, no input.
