# Fleet — Bubble Tea v2 starter

The canonical "Fleet" demo screen (`../../demo/fleet--normal--80x24.mock`) in Bubble Tea v2 + Lip Gloss v2: header
band with tabs, focused list, detail panel with severity gauges, message line, key-hint bar. Adapts to any size >= 80x24
(list 32 cols fixed, detail flexible); below that it shows a centered "Terminal too small — need 80×24, have C×R".

Verified against the mock (`../../demo/fleet--normal--80x24.mock`): at 80x24 truecolor the frame is cell-for-cell identical (characters, fg/bg, bold)
across 7 themes, and `--depth 16` matches `render_mockup.py --depth 16` (0 differing cells for catppuccin-mocha and everforest-dark).
There is no 120x30 mock: at 120x30 Bubble Tea and Ratatui render identical frames to each other (0 differing cells); Ink and Textual widen the
gauges with the detail pane. `--depth 256` uses this framework's own quantizer, so it differs from the mock's 256-color rounding.

Pinned (verified 2026-10-01): Go >= 1.26 (tested 1.27.1), `charm.land/bubbletea/v2` v2.0.10,
`charm.land/lipgloss/v2` v2.0.6, `github.com/charmbracelet/colorprofile` v0.4.3. `go.sum` is included (pins the tree).
Import paths are the v2 vanity domain; most online Bubble Tea code is v1 (`github.com/charmbracelet/...`, `View() string`).

## Copy it into your project
```sh
export SKILL_DIR=/path/to/tui-design            # the skill directory (SKILL.md lives there)
cp -R "$SKILL_DIR/assets/proto-starters/bubbletea" ./fleet-ui && cd ./fleet-ui
python3 "$SKILL_DIR/scripts/export_theme.py" catppuccin-mocha --target json -o theme.json   # any theme ID
go run . --frame --cols 80 --rows 24 --theme theme.json --depth truecolor > fleet.ansi
./capture.sh catppuccin-mocha out/              # frames at 80x24 and 120x30; or ./capture.sh theme.json out/
```
`capture.sh` finds the skill through `SKILL_DIR` first, then through `../../..` (the starter still inside the skill), and stops with an
error naming `SKILL_DIR` if neither works. It only needs the skill to turn a theme ID into JSON: with a JSON path (`./capture.sh theme.json out/`), no `SKILL_DIR` is needed.
`theme.json` here is a flat theme JSON (`{id, tokens, ansi16, ...}`); keep the frame mode (`--frame --cols --rows --theme --depth`) in the copy, it is how the design is audited.

## Run
```sh
go run .                      # interactive (alt screen): up/down or j/k select, tab switches pane focus, r restart message, q quits
go run . --theme theme.json   # a flat theme JSON path (the binary does not take theme IDs; capture.sh does)
go build -o fleet . && ./fleet
```
`enter`, `/`, `?` and the tabs 2/3 are drawn (they are part of the demo screen) but not wired.

## One static frame (for gallery / compare / audit)
```sh
go run . --frame --cols 120 --rows 30 --theme theme.json --depth truecolor > fleet.ansi     # exactly --rows lines
./capture.sh catppuccin-mocha out/    # builds in a temp dir; writes out/bubbletea--normal--80x24.ansi and ...120x30.ansi
DEPTH=16 ./capture.sh catppuccin-latte out/
```
Frame recipe: `m.Update(tea.WindowSizeMsg{...})`, take `m.View().Content` (Lip Gloss v2 `Render()`
always emits truecolor), write it through a `colorprofile.Writer{Profile: TrueColor|ANSI256|ANSI}`. `Init()` Cmds are
not run, so the frame is the time-zero state. `--selected N` and `--focus-detail` pick another state.

## Theme tokens -> Lip Gloss
`theme.json` = `python3 "$SKILL_DIR/scripts/export_theme.py" ID --target json -o theme.json` (embedded default: catppuccin-mocha;
`export_theme.py --target lipgloss` emits a ready-made `theme` package of colors if you prefer compile-time constants).
`theme.go`: `LoadTheme` (go:embed or file) -> `NewStyles(theme, ansi16)` returns a `Styles` struct, one lipgloss style
per UI role (the Bubble Tea convention: there is no theme object in Lip Gloss). View code only touches `Styles`.

| UI role | token(s) |
|---|---|
| header band / app name / tabs | `statusbar.bg`+`statusbar.fg`, `accent.primary` bold, `tab.active.fg` on `tab.active.bg`, `tab.inactive.fg`, `border.default` |
| focused / unfocused pane border | `border.focus` / `border.default`; titles `fg.title` bold |
| selected row, cursor | `selection.bg` (`selection.inactive.bg` when the list is unfocused), `selection.fg`, `accent.primary` |
| status glyphs and words | `status.success/warning/error`, `fg.faint` (stopped), `fg.muted` (running, unselected) |
| gauges | `ramp.low` (< 50 %), `ramp.mid` (< 80 %), `ramp.high`, empty `fg.faint` |
| footer | `statusbar.*`, `keyhint.key` bold, `keyhint.desc` |

Every style paints `bg.base` explicitly, so the frame does not depend on the terminal background.
16-color mode (`--depth 16`): `NewStyles(.., true)` builds styles from the theme's per-token `ansi16` specs
(`"4 bold"`, `"default dim"`, `"reverse"`), i.e. the terminal's own palette, not `colorprofile`'s nearest-color guess.
When `selection.bg` is `reverse`, the selected row is inverted per segment (each segment keeps its own fg spec and bold, like
`render_mockup.py --depth 16`); the unfocused row follows `selection.inactive.bg` (no fill in those themes, only the name is bold).
A `bg` fg spec (e.g. `tab.active.fg` in everforest-dark) is drawn as the fill token's slot as foreground + reverse, so the text takes the
terminal background color on the fill (`resolver.fgOn`).

## Caveats
- Lip Gloss v2 sizing: `Width` is the outer width (border and padding included); `Height` is a minimum (wrapping
  content grows the block). Rows are therefore padded by hand and the root is clipped with `MaxWidth/MaxHeight`.
- Lip Gloss has no border titles: the top edge is drawn by hand and the pane uses `BorderTop(false)`.
- Gauges are plain `█`/`░` runs (a `progress` Bubble would add animation, not fidelity).
- `View.BackgroundColor` is set so the terminal default background matches `bg.base` while the app runs.
- `go mod tidy` needs network only if you change dependencies; first build downloads the modules.
