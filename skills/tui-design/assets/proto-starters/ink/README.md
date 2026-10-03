# Fleet — Ink starter

The canonical "Fleet" demo screen (`../../demo/fleet--normal--80x24.mock`) in Ink: header band with tabs,
focused list, detail panel with severity gauges, message line, key-hint bar. Adapts to any size >= 80x24; below that it
shows a centered "Terminal too small — need 80×24, have C×R".

Verified against the mock: at 80x24 truecolor the frame is cell-for-cell identical (characters, fg/bg, bold) across 7 themes, and
`--depth 16` matches `render_mockup.py --depth 16` (0 differing cells for catppuccin-mocha and everforest-dark). There is no 120x30 mock:
at 120x30 the Ink gauges widen with the detail pane (up to 60 cells), so Ink differs from Bubble Tea/Ratatui (40-cell gauges) in 92 cells and
matches Textual. `--depth 256` uses chalk's quantizer, so it differs from the mock's 256-color rounding.

Pinned (verified 2026-10-01): Node >= 22 (tested 26.9), `ink` 7.1.1, `react` 19.3.0, `chalk` 5.6.2, `tsx` 4.23.15.

## Copy it into your project
```sh
export SKILL_DIR=/path/to/tui-design            # the skill directory (SKILL.md lives there)
cp -R "$SKILL_DIR/assets/proto-starters/ink" ./fleet-ui && cd ./fleet-ui
npm install                                     # local only; no global installs
python3 "$SKILL_DIR/scripts/export_theme.py" catppuccin-mocha --target json -o theme.json   # any theme ID
npx tsx src/cli.tsx --frame --cols 80 --rows 24 --theme theme.json --depth truecolor > fleet.ansi
./capture.sh catppuccin-mocha out/              # frames at 80x24 and 120x30; or ./capture.sh theme.json out/
```
`--theme` takes a flat theme JSON path or a theme ID (an ID is exported through `$SKILL_DIR/scripts/export_theme.py`, so it needs
`SKILL_DIR`, or the starter still inside the skill). `capture.sh` resolves the skill the same way (`SKILL_DIR` first, then `../../..`) and stops
with an error naming `SKILL_DIR` if neither works; with a JSON path no skill is needed. Keep the frame mode in the copy.

## Install and run
```sh
npm install                      # local only; no global installs
npm start                        # interactive: up/down (or j/k) select, tab switches pane focus, q quits
npx tsx src/cli.tsx --theme theme.json --depth 256     # --theme (JSON path or theme ID)/--depth work in interactive mode too
```

## One static frame (for gallery / compare / audit)
```sh
npx tsx src/cli.tsx --frame --cols 120 --rows 30 --theme theme.json --depth truecolor > fleet.ansi
./capture.sh catppuccin-mocha out/    # writes out/ink--normal--80x24.ansi and out/ink--normal--120x30.ansi
DEPTH=16 ./capture.sh catppuccin-latte out/
```
Frame recipe: `render()` into a fake non-TTY stdout that reports `columns`/`rows`
(so `useWindowSize()` works), with a fake stdin claiming raw-mode support, `debug: true`; read the last
frame before unmount, pad to exactly `rows` lines. `renderToString` is not used because `useWindowSize`
does not see its `columns`.

## Theme tokens -> Ink
`theme.json` = `python3 "$SKILL_DIR/scripts/export_theme.py" ID --target json -o theme.json` (default is catppuccin-mocha).
`src/theme.ts` `createTheme(json, depth)` returns `{color(token), text(token, {on, bold, dim})}`:
- `<Text {...t.text('fg.muted')}>`, `<Text {...t.text('keyhint.key', {on: 'statusbar.bg', bold: true})}>`
- `<Box borderColor={t.color('border.focus')} backgroundColor={t.color('statusbar.bg')}>`
- depth `truecolor`/`256`: hex strings; `chalk.level` (3/2) does the down-sampling.
- depth `16`: the theme's `ansi16` map (`"4 bold"`, `"default dim"`, `"reverse"`) becomes named colors/`dimColor`/`inverse`
  (chalk level 1), so the terminal's own palette is used. Matches `render_mockup.py --depth 16`; a `bg` fg spec (e.g. `tab.active.fg` in
  everforest-dark) becomes the fill token's slot as `color` + `inverse`, so the text takes the terminal background color on the fill.

## Caveats
- Ink has no border titles: `Pane` draws the top edge as a `<Text>` line and the box below sets `borderTop={false}`.
- Ink has no theme system; tokens are plain props, so changing theme means re-creating the theme object.
- `bg.base` is not painted: the terminal's own background shows through (correct on a themed terminal; a PNG
  renderer needs `--theme` to paint it). Textual paints it.
- Gauge bars scale with width (`detailW - 28`, max 60); 20 cells at 80 columns like the mock.
- Frame mode is non-interactive (`isTTY=false`): no effects/timers/input are exercised.
- Selected-row `reverse` at depth 16 comes out as inverse video per segment, same as the mock renderer.
