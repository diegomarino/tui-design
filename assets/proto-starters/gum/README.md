# Fleet — gum starter (and what gum cannot do)

gum (Charm, v2.0.1 verified 2026-10-01) is a set of shell-callable styling and prompt commands. It **cannot build a
persistent multi-pane app**: there is no event loop, no focus, no layout engine, no screen that stays up between
commands. Every `gum` call is a separate process that prints once (`style`, `join`, `format`, `table`) or runs one
modal prompt and exits (`choose`, `filter`, `input`, `confirm`, `spin`, `pager`). So the lesson of this starter is
the split below, not a clone of the Ratatui/Bubble Tea apps.

| gum can | gum cannot |
|---|---|
| Style text: fg/bg, bold/faint/italic/underline/strike, borders (4 styles), padding, margin, fixed width/height, align | Pane focus, a selection that survives between calls, `tab` between panes, live updates |
| Compose static layouts: `gum join --horizontal/--vertical` (what `fleet-static.sh` does) | Border titles, per-side borders, reverse video (`style` has no flag), vertical centering |
| One interaction at a time: `choose` / `filter` / `confirm` / `input` / `write` / `spin` / `pager` / `table` (select a row) | Redraw on resize or keep key hints on screen; any "?" help overlay or modal |
| Theme prompts through `GUM_*` env vars (`lib.sh` `gum_env`) | Theme `style` output through env: each `style` call takes explicit `--foreground/--background` |

Use gum for a script's prompts and a one-shot summary. If the user wants "a screen that stays up" (lists, tabs, panes,
live data), pick Bubble Tea (`../bubbletea`) or Ratatui (`../ratatui`) (gum itself is a thin CLI over
those libraries).

## Files
- `fleet-static.sh`: ONE static Fleet frame from `gum style` + `gum join` (header band, two bordered boxes side by side,
  message line, footer hints); ~100 `gum` spawns, about 4 s at 80x24 (each styled span is a process).
- `fleet-flow.sh`: the idiomatic gum flow for the same domain: `gum choose` a service -> `gum confirm` the restart ->
  `gum spin` -> a styled result line.
- `lib.sh`: loads the flat theme JSON with `jq` into `T_<token>`/`A_<token>` variables; `S "fg=TOKEN bg=TOKEN bold" text`
  is one styled span; `gum_env` exports `GUM_CHOOSE_*`, `GUM_CONFIRM_*`, `GUM_SPIN_*` from the tokens.
- `theme.json` (default catppuccin-mocha), `capture.sh`. Needs `gum` and `jq`; bash 3.2 (macOS /bin/bash) is enough.

Pinned (verified): gum 2.0.1, jq 1.8.2, tmux >= 3.2 for the interactive capture. No Go/Rust needed; no manifest.

## Copy it into your project
```sh
export SKILL_DIR=/path/to/tui-design            # the skill directory (SKILL.md lives there)
cp -R "$SKILL_DIR/assets/proto-starters/gum" ./fleet-ui && cd ./fleet-ui
python3 "$SKILL_DIR/scripts/export_theme.py" catppuccin-mocha --target json -o theme.json   # any theme ID
./fleet-static.sh --cols 80 --rows 24 --theme theme.json --depth truecolor > fleet.ansi
./capture.sh catppuccin-mocha out/              # frames at 80x24 and 120x30 (+ the tmux flow); or ./capture.sh theme.json out/
```
`capture.sh` finds the skill through `SKILL_DIR` first, then through `../../..` (the starter still inside the skill), and stops with an error
naming `SKILL_DIR` if neither works; it only needs the skill to turn a theme ID into JSON (with a JSON path no `SKILL_DIR` is needed).
`fleet-static.sh`, `fleet-flow.sh` and `lib.sh` read only the JSON file.

## Run
```sh
./fleet-flow.sh                       # interactive: choose -> confirm -> spin (themed from theme.json)
./fleet-static.sh                     # the static Fleet screen at 80x24 on stdout
./fleet-static.sh --cols 120 --rows 30 --theme theme.json --depth 256 > fleet.ansi   # a frame (exactly --rows lines)
./capture.sh catppuccin-mocha out/    # out/gum--normal--80x24.ansi, gum--normal--120x30.ansi, gum-flow--choose--80x24.ansi
DEPTH=16 ./capture.sh catppuccin-latte out/
```
Static output frame capture: `CLICOLOR_FORCE=1 COLORTERM=truecolor` (set by `load_theme`): gum's colorprofile writer would
strip color when piped otherwise (`NO_COLOR` is ignored when `CLICOLOR_FORCE` is set and the output is piped).
Interactive capture (`capture.sh`): a private `tmux -L gumcap$$` server runs `fleet-flow.sh`, sends `Down`, and writes
`capture-pane -p -e`; only that socket is killed. Render it with `ansi_render.py ... --cols 80 --rows 24` (tmux trims trailing blanks).

## Theme tokens -> gum
`theme.json` = `python3 "$SKILL_DIR/scripts/export_theme.py" ID --target json -o theme.json`.
- Spans: `gum style --foreground '#hex' --background '#hex' [--bold|--faint]`; every span carries `bg.base` so the frame is self-painted.
- Prompts: `GUM_CHOOSE_CURSOR_FOREGROUND=accent.primary`, `..._SELECTED_FOREGROUND=status.success`, `GUM_CONFIRM_SELECTED_BACKGROUND=accent.primary`
  on `fg.on-accent`, `GUM_SPIN_SPINNER_FOREGROUND=accent.primary` (same as `export_theme.py --target gum`).
- Boxes: `--border rounded --border-foreground border.focus|border.default`; `gum join` glues them; `fg.title bold` titles, gauges
  `ramp.low/mid/high`.
- `--depth 256` is gum's own downsampling (no `COLORTERM`); `--depth 16` uses the theme's per-token `ansi16` specs as numeric colors.
  `gum style` has no reverse flag, so `S` (`lib.sh`) wraps the span in SGR 7 ... SGR 0: that gives `reverse` fills (per segment, keeping the fg spec)
  and the `bg` fg spec (the fill's slot as foreground + reverse, i.e. text in the terminal background color on the fill, e.g. the active tab in
  everforest-dark).

## Fidelity vs the mock (80x24, catppuccin-mocha: 170 of 1920 cells differ, all from the limits above)
- Pane titles are content lines inside the boxes ("Services (6)", "api-gateway"), because gum borders carry no title.
  The list rows therefore start one row lower than in the mock.
- Detail pane is fixed to api-gateway (no `--selected`); there is no selected state, focus or tab handling.
- Selected row uses the background token; at `--depth 16` "reverse" is real SGR 7 per segment (see above), so this row's colors match the mock;
  the differing cells at 16 colors are the same layout cells as at truecolor (170 for catppuccin-mocha and everforest-dark).
- `gum style --width/--height` are outer sizes including the border (verified); `--height` pads but never clips, so `fleet-static.sh`
  pipes through `head -n $rows`.
