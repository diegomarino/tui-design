# Tools: what each script does

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [Frames](#frames) · L12–19 — build, lint, render, compare.
- [Gallery](#gallery) · L21–23 — the HTML page: keys, export, opening it.
- [Host](#host) · L25–31 — what the host draws, which keys reach the app.
- [Audit](#audit) · L33–44 — live capture, screenshot pipeline.
- [Color](#color) · L46–51 — themes, contrast, export.

Run as `python3 SKILL_DIR/scripts/<name>`; `--help` is the source of truth. `_*.py` are shared modules.

## Frames

Every frame is built, linted and looked at before anyone sees it.

- `mockkit.py` — Python library that builds every `.mock` frame: helpers, recipes, `matrix()` in [mockkit.md](mockkit.md); exact signatures in [mockkit-api.md](mockkit-api.md).
- `render_mockup.py FILE.mock` — lint (every frame) or render. `--check` (lint, caps, craft CR1–CR7), `--depth 256|16|none`, `--theme ID`, `-o f.ansi`.
- `ansi_render.py f.ansi` — frame → PNG to look at before showing. `--format png`, `--theme ID`, `-o`.
- `compare.py LEFT RIGHT` — mock vs build, or source vs reconstruction: side by side, overlay, cell diff. `--labels a,b`, `-o cmp.html`.

## Gallery

`gallery.py DIR… --themes a,b -o gallery.html` — one self-contained page of every frame, to show a design (`--themes all`). Selectors for design, variant, state, size, theme, scale; keys `←→` variant, `↑↓` state, `t` theme, `z` size, `s` side by side, `f` fit / 1x. Each frame exports TXT, ANSI, SVG, PNG or copies its text. Open the file locally; if the browser blocks file actions, run `python3 -m http.server` in its folder and open `localhost:8000/gallery.html`. Sandboxed hosts (published pages) block downloads: use Copy, or `--export DIR [--formats txt,png]`. Themes: ids or JSON paths.

## Host

For a plugin or popup: ask the user to run these inside the host and send screenshots.

- `test_card.py` — attributes, colors, glyph widths → the `#! caps:` line; compare with `assets/test-card/*--reference.png`. `--curses`.
- `key_probe.py KEY…` — which keys reach the app inside the host (`f2 ctrl+s alt+s`).
- `play_mock.py FRAME.mock` — draws a frame with curses in the host. `--depth 256|16`.

## Audit

Live capture: the first two. Screenshot: `prep_screenshot.py` to `merge_description.py`, in order. Both paths then prove the description with `description_to_mock.py` + `compare.py` (`audit-protocol.md`).

- `capture_tui.sh -s 80x24 -o OUT -- CMD` — frames of a running app (private tmux). `-s` repeats, `-k KEYS`, `-p SECS`.
- `ansi_grid.py f.ansi|f.mock` — cell grid. `--describe` (skeleton), `--clutter` (counts).
- `prep_screenshot.py IMG -o DIR` — screenshot → grid + images (`uv run`). `--cols --rows`.
- `describe_prompt.py --pass 1|2 --grid grid.json` — one describer prompt.
- `sample_colors.py IMG --grid grid.json` — colors from pixels (`uv run`). `--themes all`.
- `merge_description.py` — passes + colors → one description. `--validate FILE`.
- `description_to_mock.py desc.json -o recon.mock` — draws only what a description asserts.
- `score_description.py HYP.json [TRUTH.json]` — scores it. `--truth-from-mock F.mock`.

## Color

- `preview_theme.py ID` — token swatches. `--depth 16`.
- `contrast_check.py ID` — contrast floors, exit 1 on failure. `--depth 16`, `--all`.
- `export_theme.py ID --target T -o FILE` — `textual ink lipgloss ratatui gum css json`.
- `check_versions.py` — pinned framework versions. `--online`.
