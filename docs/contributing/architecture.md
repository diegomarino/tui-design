# Architecture

How the repository is laid out, how the skill's scripts fit together, where the tests are, and the recipes for the
usual contributions. Short rules and the pull-request checklist: [CONTRIBUTING.md](../../CONTRIBUTING.md).

## Layout

```
skills/tui-design/   the product: the only folder the skills CLI installs
  SKILL.md           entry point: branches, working rules, reference map
  references/        Markdown read by section, theme JSON, the description schema, prompt and templates
  scripts/           Python 3.11+ (mostly stdlib) and one bash script
  assets/            reference mockups, the Fleet demo, five proto-starters, the test-card reference PNGs
docs/                these pages, docs/img (generated) and docs/showcase (the worked example and its generator)
evals/               trigger and behavior evals, and the ledger of the published run
tests/               unit tests for the scripts, the eval harness and the gallery page
tools/               check_public.sh, check_links.py, gen_toc.py, make_screenshots.py, _browser.py
.github/workflows/   pages.yml: rebuilds the reference gallery and deploys it to GitHub Pages
```

Anything under `skills/tui-design/` reaches every user on their next `npx skills update`, so it must be finished,
tested and self-contained: links stay inside the folder, and scripts compute paths from their own location so a
copy or a symlink works. Material for people (screenshots, the showcase, these docs) lives outside it.

## How the scripts fit together

Four private modules hold everything shared; the commands are thin layers over them.

| Module | Holds | Used by |
|---|---|---|
| `_theme.py` | loading `references/themes/<id>.json` (id or path), token resolution with tier-2 fallbacks, `ansi16` specs, SGR building, OKLab and WCAG math | nearly every script |
| `_ansi.py` | parser for one ANSI frame into a cell grid: SGR 16/256/truecolor, attributes, OSC 8 links, wide and zero-width characters | `ansi_render`, `ansi_grid`, `compare`, `gallery`, `play_mock`, `score_description` |
| `_mock.py` | `.mock` parser and linter: tags, tokens, glyph tiers, box integrity, the `#! caps:` profile | `render_mockup`, `mockkit`, `gallery`, `compare`, the description tools |
| `_craft.py` | craft rules CR1–CR7 as warnings on a parsed mock | `_mock.py` (so `--check` and `mockkit.save()` report them) |

The commands, by stage:

```
mockkit.py ──save()──▶ frame.mock ──render_mockup.py──▶ frame.ansi ──ansi_render.py──▶ SVG / PNG / HTML
                           │                                │
                           ├──gallery.py (imports render_mockup + ansi_render) ──▶ gallery.html
                           └──compare.py ◀── frame.ansi from a starter or capture_tui.sh
                                  ▲
capture_tui.sh ──▶ app.ansi ──ansi_grid.py --describe──▶ description ──description_to_mock.py──▶ recon.mock
screenshot.png ──prep_screenshot.py ▶ describe_prompt.py ▶ (vision) ▶ sample_colors.py ▶ merge_description.py
```

- Renderers: `render_mockup.py` turns a mock into an exact rows × cols ANSI frame at a depth; `ansi_render.py`
  draws any frame as a cell-exact SVG (PNG through `rsvg-convert`).
- `gallery.py` and `compare.py` import those renderers in-process (no subprocess) and write one self-contained HTML
  page each. The gallery renders each layout once with placeholder colors and fills them per theme in JavaScript.
- Host tools (`test_card.py`, `key_probe.py`, `play_mock.py`) and color tools (`preview_theme.py`,
  `contrast_check.py`, `export_theme.py`) stand alone on `_theme.py`.
- One agent-facing line per script, with key flags, is in
  [references/tools.md](../../skills/tui-design/references/tools.md). `--help` is the source of truth for flags.

## Tests

Standard-library `unittest`, no model calls. From the repository root:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
bash tests/test_capture.sh                  # live capture through a private tmux server
```

| Area | Tests |
|---|---|
| parser and renderers | `test_ansi.py`, `test_mockup.py`, `test_caps_clutter.py`, `test_craft.py` (every shipped mockup and the showcase frames are craft-clean) |
| mock builder | `test_mockkit.py`, `test_mockkit_helpers.py`, `test_mockkit_theme.py` |
| gallery and compare | `test_gallery_compare.py`; `test_gallery_browser.py` drives the page in a real browser |
| themes | `test_theme_tools.py` (runs `contrast_check.py --all` over every theme) |
| audit pipeline | `test_description.py`, `test_describe_prompt.py`, `test_screenshot.py` (with the `_fixture.py` ground-truth renderer) |
| host tools | `test_test_card.py`, `test_key_probe.py`, `test_play_mock.py`, `test_capture.sh` |
| reference pins | `test_check_versions.py` |
| eval harness | `test_behavior_evals.py`, `test_eval_harness.py`, `test_export_results.py`, `test_ledger.py` |
| docs | `test_docs_links.py` (no broken relative links; nothing in the skill links outside it), `test_toc.py` (every reference's Sections line ranges are current) |

Some tests skip when an optional tool is missing: Pillow and numpy for the screenshot tests, `rsvg-convert` for PNG
export, a Playwright with a browser for `test_gallery_browser.py` (found by `tools/_browser.py`, never installed).
Fixtures are in `tests/fixtures/` (captured frames of real apps, a deliberately cluttered mock).

## Add a theme

1. Copy `skills/tui-design/references/themes/catppuccin-mocha.json` to `<scheme>-<variant>.json`. Map every tier-1
   token of `themes/_tokens.json` to a value from the scheme's **official** palette (tier-2 tokens fall back when
   unmapped), and fill the terminal colors and `ansi16` from the scheme's official terminal port.
2. Record a `provenance` entry per token (`spec: …` when the style guide names the role, `choice: …` when you
   chose), the `sources` URLs and the upstream `license`. Invented colors are not accepted.
3. Check both depths; fix failures only with same-role colors from the official palette, otherwise keep the
   official mapping and explain the failure in `notes`:

   ```bash
   python3 skills/tui-design/scripts/contrast_check.py <id>
   python3 skills/tui-design/scripts/contrast_check.py <id> --depth 16
   python3 skills/tui-design/scripts/preview_theme.py <id> --depth 16
   ```

4. Add the variant to `references/color-schemes.md` (with its pass counts) and to `references/schemes/<scheme>.md`,
   and credit the upstream project in `CREDITS.md`.
5. Run the unit tests, try `export_theme.py <id> --target textual`, and regenerate `docs/img/themes.png` with
   `uv run tools/make_screenshots.py --only palette`.

## Add a framework

1. Write `references/frameworks/<framework>.md` with the sections of the existing files (when it is right, versions
   and install, mental model, a verified minimal app, layout, components, keys, async and performance, applying the
   theme tokens, color profile and NO_COLOR, testing, one static frame at a forced size, pitfalls as symptom → cause
   → fix → source). Rules carry a source link; mark what you ran as `VERIFIED`.
2. Add `assets/proto-starters/<framework>/` rendering the Fleet demo from a flat `theme.json`, with the frame mode
   (`--frame --cols --rows --theme --depth`), a `capture.sh` and a README listing known differences from the mockup.
3. Add it to `references/frameworks/choosing.md`, `references/vocabulary.md`, `scripts/export_theme.py` (if it has a
   theme format) and `scripts/check_versions.py`.
4. Compare its frame with the mockup: `compare.py assets/demo/fleet--normal--80x24.mock frame.ansi -o cmp.html`.

## Add an eval case

Cases go in `evals/behavior-evals.json` or a new `evals/cases/<topic>.json` (schema in
[evals/README.md](../../evals/README.md#case-schema)).

- Neutral domains only (jobs, backups, deploys, pods, logs, packages); `banned_terms` lists names that must never
  appear. Extend it, never bypass it.
- Prefer program and executed assertions; keep judge questions few, yes/no and crisp. Mark assertions on the skill's
  own formats (`.mock`, `#! caps:`, its scripts) `"neutral": false`.
- Give every new executed check a positive and a negative control in the unit tests. Mark a case `"serial": true`
  if it sends signals or kills processes. Generated fixtures go through `evals/fixtures/gen_fixtures.py`.
- `python3 evals/run_behavior_evals.py --validate-cases`, then a smoke run:
  `--cases <id> --models smoke --arms skill,baseline --max-usd 1`.

Editing a case changes its `case_hash` and separates its results from earlier runs; add a new case when
comparability matters.

## Add a model

Append a `[[models]]` table to `evals/models.toml` (see "Extending" in [evals/README.md](../../evals/README.md#extending)),
check it with `--list-models` and plan a run with `--models <id> --dry-run`. Any agent CLI fits the `command` adapter
(an argv template); try the plumbing offline with `--models example-echo --no-judge --cases sketch-80x24 --arms skill`.
After a campaign, record it with `python3 evals/ledger.py evals/runs/<dir> --label "…"`.

## Checks before a pull request

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
bash tests/test_capture.sh
python3 tools/check_links.py                        # relative links in README, docs/ and the skill
python3 tools/gen_toc.py                            # Sections line ranges of every reference (no-op when current)
bash tools/check_public.sh                          # must print "clean"
python3 skills/tui-design/scripts/render_mockup.py path/to/frame.mock --check     # every .mock you touched: 0 errors
```

`tools/check_public.sh` fails on the owner's name (the GitHub handle is allowed in a few files), local paths, private
hostnames, e-mail addresses, agent session ids, API keys and tokens, and files that must never ship (raw eval runs,
caches, local skill copies in `.claude/` or `.agents/`). It scans PNGs for embedded paths too. Fix the hit, or extend
its patterns; never bypass it. `.gitleaksignore` lists the one fake key the redaction tests need, the same file and
value `check_public.sh` allows.

When a change affects what the docs show, regenerate the images (`uv run tools/make_screenshots.py`, or `--only` a
step) and look at each one before committing.
