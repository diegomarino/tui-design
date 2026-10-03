# Audit protocol: perceive → describe → prove → judge

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [1. Who sees what](#1-who-sees-what) · L33–40 — who gets the image, the description and the judgment.
- [2. Choose the path](#2-choose-the-path) · L42–53 — live capture vs screenshot vs your own mock.
- [3. Live capture](#3-live-capture) · L55–94 — the app runs: capture commands and multiplexer gotchas.
- [4. Screenshot: image only](#4-screenshot-image-only) · L96–167 — only an image: preparation, describer prompts, subagents.
- [5. Merge and validate](#5-merge-and-validate) · L169–207 — merging describer output into a valid description.
- [6. Fidelity loop: prove the description before judging it](#6-fidelity-loop-prove-the-description-before-judging-it) · L209–223 — checking the description against the source.
- [7. Judge step](#7-judge-step) · L225–241 — applying the checklist and writing the report.
- [8. Calibration: measure the screenshot path before trusting it](#8-calibration-measure-the-screenshot-path-before-trusting-it) · L243–259 — measuring the screenshot path's accuracy.
- [9. Quick troubleshooting](#9-quick-troubleshooting) · L261–272 — a step fails.
- [Host tools](#host-tools) · L274–297 — opening a PNG, starting a describer, or continuing one.

Read this when you audit an existing TUI (a running app, or only a screenshot) or review a rendered prototype frame. It describes how to turn the screen into a schema-valid `tui-description`, how to prove the description is faithful, and how to judge it with [audit-checklist.md](audit-checklist.md). The describer prompt is in [prompts/describe-tui.md](prompts/describe-tui.md) and the report shape in [templates/audit-report.md](templates/audit-report.md). Self-review of your own `.mock` frames (design step A8) needs none of the audit procedure: use the §0 quick-review core in [audit-quick.md](audit-quick.md). Opening a PNG still uses [Host tools](#host-tools).

**Core rule: perception and judgment are separate steps.** A neutral describer produces a schema-validated description of what is on screen. A separate judge applies the checklist to that description and cites element and region ids as evidence. A reconstruction step proves the description is faithful before anyone judges it.

```
app runs? ─yes─► live capture: capture_tui.sh ─► ansi_grid.py --describe ─► ansi_render.py ─► describer (roles, states) ──┐
    │                                                                                                          │
    no ────────► screenshot: prep_screenshot.py ─► describer pass 1 ×2 ─► crops ─► pass 2 per leaf ─► sample_colors.py ─┤
                                                                                                               ▼
                                                                merge_description.py (merge + validate) ─► description.json
                                                                                              │
                         fidelity: description_to_mock.py ─► render_mockup.py ─► compare.py (≤2 loops)
                                                                                              │
                                                       judge: audit-checklist.md ─► templates/audit-report.md
```

Every command below runs a script as `SKILL_DIR/scripts/<name>`; `--help` on each script is the source of truth for flags.

## 1. Who sees what

| Step | Done by | Sees | Must not see |
|---|---|---|---|
| Capture / preprocessing | scripts | the app or the image | — |
| Describe | fresh subagent per call, or this session when [Host tools](#host-tools) has a dash under Start ([prompts/describe-tui.md](prompts/describe-tui.md)) | images plus grid facts (live capture: also the exact text) | app name, user's complaint, design goals, checklist, hex values |
| Merge, validate, prove | orchestrating agent | everything produced so far | — |
| Judge | orchestrating agent, or a separate subagent for long audits | the description, script outputs, checklist, design brief | the raw image while judging (see §7) |

## 2. Choose the path

| Situation | Input path | Why |
|---|---|---|
| You can launch the app, even a demo build or a prototype | **Live capture** | `measured:` lossless (a re-emitted, recaptured lazygit screen differed in 0/3600 cells) |
| Only a screenshot exists (README, issue, user upload) | **Screenshot** | the only option. Layout is reliable; exact glyphs, spaces and colours need scripts |
| Screenshot provided but the app is installable | **Live capture** for the audit; keep the image as context | one live capture beats any number of screenshot passes |
| Our own `.mock` prototype, self-review | none: §0 quick-review core in [audit-quick.md](audit-quick.md) | the mock *is* the truth; checks run on the file, its PNG and `contrast_check.py` |
| Our own `.mock` prototype, full audit | render it (`render_mockup.py`) and use **live capture** on the `.ansi` | no perception needed for text and colour |
| Calibrating the screenshot path | both: live capture for truth, screenshot on the rendered PNG | §8 |

Work in one directory per screen state, named like rendered frames: `audit/<variant>--<state>--<cols>x<rows>/` (for example `audit/main--normal--120x30/`).

## 3. Live capture

```bash
# 1. Capture at the standard sizes and the too-small sizes (layout-archetypes.md §2.2: 60x18, 40x10);
#    keys are tmux send-keys names, sent in order before capturing
SKILL_DIR/scripts/capture_tui.sh -s 120x30 -s 80x24 -s 60x18 -s 40x10 -w 2 -o audit/main/ -- /abs/path/to/app --flag
SKILL_DIR/scripts/capture_tui.sh -s 120x30 -k Tab -k j -w 2 -o audit/second-pane/ -- /abs/path/to/app
# colour profiles: same capture with env overrides (-e VAR=VAL)
SKILL_DIR/scripts/capture_tui.sh -s 80x24 -e NO_COLOR=1 -o audit/nocolor/ -- /abs/path/to/app
SKILL_DIR/scripts/capture_tui.sh -s 80x24 -e TERM=xterm -e COLORTERM= -o audit/16color/ -- /abs/path/to/app

# 2. Exact skeleton (meta, screen_text, boxes from box-drawing, palette) and the cell grid for the merge
uv run SKILL_DIR/scripts/ansi_grid.py audit/main/120x30.ansi --theme catppuccin-mocha --describe -o audit/main/120x30.skeleton.json
uv run SKILL_DIR/scripts/ansi_grid.py audit/main/120x30.ansi --theme catppuccin-mocha -o audit/main/120x30.grid.json

# 3. Image for the describer (roles, segmentation, states)
uv run SKILL_DIR/scripts/ansi_render.py audit/main/120x30.ansi --theme catppuccin-mocha --format png --scale 2 \
    --geometry audit/main/120x30.geom.json -o audit/main/120x30.png
uv run SKILL_DIR/scripts/prep_screenshot.py audit/main/120x30.png --cols 120 --rows 30 -o audit/main/prep/
```

4. Run describer pass 1 (§4.1) with the given text: `python3 SKILL_DIR/scripts/describe_prompt.py --pass 1 --grid audit/main/prep/grid.json --path capture --text audit/main/120x30.skeleton.json`. Then re-run `uv run SKILL_DIR/scripts/prep_screenshot.py audit/main/120x30.png --cols 120 --rows 30 --regions audit/main/pass1.json -o audit/main/prep/` to get crops, and run pass 2 per leaf region with `--crops prep/crops.json --pass1 pass1.json --region rN --path capture --text …`. Because the text is given, a screen of 120×30 or smaller with five or fewer regions may skip crops: without `--crops`, pass 2 uses `pass1.png` and names the region's cells.
5. Merge (§5) with `--grid audit/main/120x30.grid.json`: text and styles come from the capture (`source: "sgr"`); roles, element boundaries, states and key hints come from the describer.
6. Copy `<size>.meta.json` facts into `meta.capture`: cursor, `alternate_screen`, `stable`, `env`, `keys_sent`. Copy volatile cells into `volatile_cells` and set `volatile: true` on every region that contains one.

**The `--theme` choice for a live capture.** A third-party app emits ANSI indexes 0–15 whose hex values belong to the *user's* terminal theme. Map them with a theme only for rendering. In the description, record them as terminal slots (`ansi.red`, `term.fg`) and run colour checks against at least one dark and one light theme (CA-09). Truecolor and 256-colour SGR values are exact.

### tmux gotchas (`capture_tui.sh` handles them; check them first when a capture looks wrong)

| Symptom | Cause | Fix |
|---|---|---|
| Blank pane | relative command path; the tmux server's cwd differs | absolute paths, or `-C DIR` |
| Overlined text reads as blinking | tmux prints SGR 53 as `5:3` | parser maps `5:3` → overline |
| Grid shifted, SGR leaks across rows | `capture-pane -J` joins wrapped lines | never use `-J` for grids |
| Short rows, lost right-aligned backgrounds | capture trims trailing default cells; `-N` pads only to the used width | pad every row to `pane_width` in the parser |
| Live app never "settles" (btop changed 796/3600 cells over 3 s) | continuous redraw | `-p` ≥ 2× the refresh interval marks changed cells `volatile`; describe structure from any one frame |
| Size changes mid-audit | a client attached under `window-size latest` | never attach to the audit server; resize with `resize-window` |
| Wrong colours or depth | apps branch on `TERM`/`COLORTERM`/`NO_COLOR`; inside tmux `TERM=tmux-256color` | set env per profile explicitly (`-e`) |
| Your own tmux sessions touched | default server used | private socket `tmux -L <unique>`; never `kill-server` on the default server |
| Wide char misplaces later cells | tmux emits a wide char once and skips its padding cell | the parser advances 2 cells by `wcwidth` |

## 4. Screenshot: image only

1. **Grid and pass-1 image.** Pass `--cols/--rows` whenever the user knows the terminal size: then the grid is exact.
   ```bash
   uv run SKILL_DIR/scripts/prep_screenshot.py shot.png -o audit/x/prep/
   #  → grid.json (cols, rows, cell_px, origin_px, grid_confidence, advice, pass1{file, cell_px, origin_px, scale}),
   #    pass1.png, pass1-ruler.png
   ```
   Act on `grid.json` `advice` before any dispatch:

   | `advice` | Meaning | Do |
   |---|---|---|
   | `ok` | `grid_confidence` ≥ 0.7 | go on; pass 1 gets the plain image only |
   | `check-ruler` | `grid_confidence` 0.4–0.7, or lower with `--cols/--rows` given | open `pass1-ruler.png` yourself: the last column label must sit on the last inked column and row labels on text rows. If they do, go on (`describe_prompt.py` adds the ruler image to pass 1). If not, re-run with `--cols/--rows` or `--anchor-line` |
   | `give-size` | `grid_confidence` < 0.4 and no size given: the grid cannot be trusted | stop. Ask the user for the terminal size (or read it from the image: window title, a `120x30` label) and re-run with `--cols C --rows R`. `describe_prompt.py` refuses this grid (exit 3) |

2. **Pass 1, twice.** Build the prompt with `python3 SKILL_DIR/scripts/describe_prompt.py --pass 1 --grid prep/grid.json -o prompt.pass1.txt` and dispatch two independent describer subagents on it (§4.1). Validate each output: `python3 SKILL_DIR/scripts/merge_description.py --validate pass1.runN.json --part describer_pass1`.
3. **Reconcile pass 1.** Compare the two outputs region by region: same ids/roles, bbox equal, anchor lines equal. When they agree, keep run 1. For each disagreeing region, keep the box both runs share (or run 1's), add `uncertainties[{kind: "disagreement", source: "derived", alternatives: [both]}]`, and make sure pass 2 covers that region. Check by hand that borderless full-width bands (header, statusbar, keybar) have `x = 0, w = cols` and that overlays carry `z ≥ 1` and `occludes`. Save the result as `pass1.json`. Never ask a describer "are you sure?": self-verification does not re-look at the image, while majority voting works ([arXiv 2506.17417](https://arxiv.org/abs/2506.17417)).
4. **Refine the grid and cut crops:**
   ```bash
   uv run SKILL_DIR/scripts/prep_screenshot.py shot.png --anchor-line 22:"deployed api-gateway v2.4.1" \
       --regions audit/x/pass1.json -o audit/x/prep/
   #  → crops.json [{id, file, bbox, scale, cell_px, origin_px}] (pixels of each crop), region-rN.png, region-rN-ruler.png
   ```
   Use the longest anchor line from pass 1. If the refined `cols×rows` differs from the grid that pass 1 was given, re-run pass 1 (it is cheap) before cutting crops.
5. **Pass 2:** one describer per *leaf* region, all in parallel: `python3 SKILL_DIR/scripts/describe_prompt.py --pass 2 --grid prep/grid.json --crops prep/crops.json --pass1 pass1.json --region rN -o prompt.pass2.rN.txt`. The crop is upscaled with an absolute margin ruler. Validate each output with `--part describer_pass2`. Parent regions get no pass 2: their border and title come from pass 1 (§5).
6. **Colours from pixels:**
   ```bash
   uv run SKILL_DIR/scripts/sample_colors.py shot.png --grid audit/x/prep/grid.json --themes all -o audit/x/prep/cells.json
   ```
   This gives per-cell bg/fg hex, token candidates, and a best theme with its residual. **A theme fits** when `theme_guess.bg_match` is 1.0 and the residual is low (calibration fits were 0.35–0.7; the next-best theme was ≥ 3.7). Then re-run with `--theme <id>` for stable token names. **No theme fits** (bg_match < 1, or residual several times the fitting range: the helix screenshot gave 13.6 with bg_match 0): re-run with `--no-tokens`. Colours then stay raw (`token: null`, `raw` set), and the judge must not apply token-based checks (§7).
7. **Merge and validate** (§5) → `description.json` → **fidelity loop** (§6).

### 4.1 Dispatching the describer subagent

One describer call = one fresh start, on the same model family the audit runs on. Which tool opens the image, which tool starts the describer, and which tool continues it: [Host tools](#host-tools).

```bash
python3 SKILL_DIR/scripts/describe_prompt.py --pass 1 --grid audit/x/prep/grid.json -o audit/x/prompt.pass1.txt
python3 SKILL_DIR/scripts/describe_prompt.py --pass 2 --grid audit/x/prep/grid.json --crops audit/x/prep/crops.json \
    --pass1 audit/x/pass1.json --region r3 -o audit/x/prompt.pass2.r3.txt
# Live capture: add --path capture --text <size>.skeleton.json ; print only the output contract: --contract 1|2
```

- The prompt file is the subagent prompt, verbatim: Preamble + Pass 1 or Pass 2 block [+ live-capture addendum] + an OUTPUT CONTRACT generated from the schema that lists every allowed key and enum value. Never write or edit the facts by hand: they are the facts of the image the describer sees (the downscaled pass-1 image or the upscaled crop), not of the original screenshot.
- The image paths are absolute. The subagent opens them with the image tool named in the preamble, and the preamble forbids reading anything else.
- The subagent's final message is the JSON object only. Save it verbatim to `pass1.run1.json`, `pass2/r3.json`, and so on.
- Validate at once: `python3 SKILL_DIR/scripts/merge_description.py --validate pass2/r3.json --part describer_pass2`. When it fails, continue that same describer ([Host tools](#host-tools)) with the validator's error lines and "Return the corrected JSON object only". Allow at most 2 continuations; after that, run a fresh describer.
- Image budget: keep each image ≤1568 px on the long edge (≤2576 px on the high-res tier). Claude silently downscales larger images ([vision docs](https://platform.claude.com/docs/en/build-with-claude/vision)). If the full screen falls below 8 px per cell at that size, `prep_screenshot.py` tiles pass 1; build one prompt per tile with `--tile N` and merge the halves. To tile by hand, pass a `regions.json` with two synthetic regions (`{"regions":[{"id":"r1","bbox":…},{"id":"r2","bbox":…}]}`) with a 2-cell overlap to `prep_screenshot.py --regions` and describe each crop.

### 4.2 What the screenshot path gets right and wrong

`measured:` on lazygit 120×30, 5 runs:

| Reliable (5/5 runs) | Unreliable: the fix comes from scripts or crops |
|---|---|
| grid size when given; all 7 panel boxes exact; focused panel; reverse/selection bars; bold headers on letters; underline; key-hint pairs (6/6); no invented elements; app never named | `▐` scrollbar read as `│`; `─`↔`-` in titles; runs of spaces collapsed (a 16-space gap became 1: footer CER 12.5% at 0.37×); bold on box glyphs (not drawn by the font); hue boundaries (yellow-green called "yellow"); exact colours (never trust model colours); counts on empty grids (never trust model counts) |

Measured preprocessing effects: plain 1× gave row CER 0.002. A 0.37× image gave 0.023, upscaled 1.95× gave 0.016, and upscaled with a ruler gave 0.000. Adding the ruler to the crisp 1× image made results worse (0.020, 5 `[?]`). Use rulers only on small or upscaled images, and only as margin labels.

**What to expect** (`measured:` this skill's mocks rendered to PNG, run through the screenshot path and scored with `score_description.py`):

| Screen kind | Result | What it means for an audit |
|---|---|---|
| Clean bordered 80×24 renders, dark theme, scale 2 (list+detail, inbox, pods) | region IoU 100%, exact boxes 100%; row CER 0.05–0.16%; key-hint F1 1.0 | trust layout, text and hints after the usual merge checks |
| Form with borderless bands, 80×24 | IoU 62%, exact boxes 40%; CER 1.5% | bands got text-extent boxes; check rule 4 (`x = 0, w = cols`) when reconciling pass 1 |
| Dense dashboard with braille graphs, 120×30 | 417 `[?]`, CER 12.3% (hallucination CER only 0.37%); fg tokens 64% | expect `[?]`-heavy plots; judge charts from labels and printed numbers only (rule 10) |
| Light theme at scale 1 | fg tokens 67.5%; text and layout fine | grey tokens (`fg.muted`/`fg.faint`/`border.default`) collapse into one: no token-level claims about greys; use scale ≥ 2 or a live capture |
| Colours from pixels, dark themes, scale 2 | fg tokens 94.6–99.9%; bg 95–97% of cells | colour checks are sound; a single cell is not evidence |
| Focus / selection | scored once the mock truth carries `#! focus` / `#! selected` (§8) | before that, state was unscored |

Still untested: JPEG screenshots, CJK-heavy screens. Calibrate (§8) before trusting the screenshot path on those.

## 5. Merge and validate

```bash
# Screenshot
python3 SKILL_DIR/scripts/merge_description.py --pass1 audit/x/pass1.json --pass2 audit/x/pass2/ \
    --cells audit/x/prep/cells.json --grid audit/x/prep/grid.json --subject shot.png --model <describer model> \
    -o audit/x/description.json
# Live capture: the grid is the ansi_grid.py grid of the capture (exact text, colours, attributes)
python3 SKILL_DIR/scripts/merge_description.py --pass1 pass1.json --pass2 pass2/ --grid 120x30.grid.json \
    --theme catppuccin-mocha -o description.json
# Validate any file on its own (full description, or a describer fragment)
python3 SKILL_DIR/scripts/merge_description.py --validate FILE [--part describer_pass1|describer_pass2]
```

The merge validates its inputs and its output against the schema and exits 1 on errors. Below: what the script does (rule numbers as in `merge_description.py --help`), and what to check by hand afterwards.

### 5.1 Structure and text

| # | The script does | Check by hand |
|---|---|---|
| 1 | Regions from reconciled pass 1; elements = all pass-2 `elements` in region order; colliding element ids renumbered `e<region><seq>` with `refs` updated | — |
| 2 | `screen_text` — live capture: from the capture, always. Screenshot: `rows` lines of `cols` spaces, each pass-2 `rows[]` painted at `(x, y)`. A cell painted by two leaf regions (a shared border) may hold the same character; differing characters become `[?]` + `disagreement` | — |
| 3 | **Coverage**: a cell no region painted but that has ink in `cells.json` → a new leaf region with role `other` + an uncertainty | run pass 2 on each such region |
| 4 | **Element text** := its slice of `screen_text`. Live capture: silently. Screenshot: the element's own version goes into a `disagreement` | — |
| 5 | **Bounds**: element bbox clipped into its region, child region into its parent (`kind: position`) | — |
| 6 | **`[?]` survives the merge.** Never resolved by guessing; only a live capture, a re-crop, or the user resolves it. In `screen_text`, `[?]` and `[?*]` stand for one cell and an unknown run, so such rows are not exactly `cols` characters long. **Chart regions** (role `chart`, or chart/sparkline elements) carry plot runs as `[?*]`; the scorer excludes chart cells from CER | — |
| 13 | **Parent regions** (with children) get no pass 2: their border and title cells are painted from pass 1 (`border.style`, `title.text`, `title.position`) | a parent's title in `screen_text` matches the image; if not, fix `pass1.json` (re-run pass 1 if unsure) and re-merge |
| 14 | **Overlays**: z-order applies. A higher `z` wins every cell it covers; the covered cells of lower regions are marked occluded (`kind: occluded`, `ref` = the covered region) | every modal/popup has `z ≥ 1` and `occludes`; if the describer missed it, fix pass 1 and re-merge |

### 5.2 Colours, attributes, counts

| # | The script does | Check by hand |
|---|---|---|
| 7 | **Colours only from SGR (live capture) or pixels (screenshot).** Per element and span: fg over non-space cells, bg over all cells. One RGB class covering ≥ 80% → `token`, `raw`, `token_candidates` (several tokens share the RGB), `source` `sgr`/`pixel`, `name: null`. Otherwise the vision `name` stays and a `colour` uncertainty is added. Pixels beat the model on hue with no further note | when no theme fits (§4 step 6), every `token` is null: colour checks use `raw` |
| 8 | **Ink check (screenshot)**: a space over an inked cell, or a glyph over a blank cell → `kind: ink_mismatch`, `source: "pixel"` (runs, not single cells) | many mismatches on spaces = collapsed space runs: re-crop with the ruler |
| 9 | **Attributes**: live capture from SGR (`attrs_source: "sgr"`); screenshot keeps the vision attrs and their `attrs_confidence`, never upgraded. A solid bar is background: reverse video on spaces and full blocks (`█`) count as bg, the same rule the describer follows (prompt rule 6) and the scorer applies | — |
| 10 | — | **Counts** are never copied from model prose. Any count the judge needs (rows in a list, hints in a bar) is computed from `elements[]` and `screen_text` |
| 11 | **Meta**: `source_path`; `subject` (live capture: the command line; screenshot: the image file name, never a guessed app name); `size` with `source`; `image{…, grid_confidence, preprocessing[], describer_model}`; `theme_guess{name, dark, default_fg, default_bg, residual, confidence}`; `focus_summary` "rN …" sets that region's `state.focused` with the text as evidence | — |
| 12 | — | **Lint what the schema cannot check**: every state flag set to `true` has `evidence`; `observations` (optional, neutral, script-derived, e.g. "row 23 text ends at x=78; x=79 blank") contain none of the banned words of prompt rule 7 |

## 6. Fidelity loop: prove the description before judging it

```bash
python3 SKILL_DIR/scripts/description_to_mock.py audit/x/description.json -o audit/x/recon.mock
python3 SKILL_DIR/scripts/render_mockup.py audit/x/recon.mock --theme <theme_guess.name> -o audit/x/recon.ansi
# Live capture: cell diff against the capture
python3 SKILL_DIR/scripts/compare.py audit/x/120x30.ansi audit/x/recon.ansi --labels capture,description --theme <id> -o audit/x/fidelity.html
# Screenshot: side by side against the screenshot
python3 SKILL_DIR/scripts/compare.py shot.png audit/x/recon.ansi --labels screenshot,description --theme <id> -o audit/x/fidelity.html
```

- The reconstruction renders **only what the description asserts**, so omissions show up as blank cells.
- **Pass bars:** text matches in ≥98% of cells and bg tokens match in ≥98% (live-capture cell diff). For the screenshot path, check visually that every inked area in the screenshot is present in the reconstruction, and that borders, the selection bar and the focus cue match.
- A failing region gets one more pass-2 crop, plus a second sample if its text disagrees. Stop after **2 iterations**. Anything still unresolved stays in `uncertainties`, and the judge treats it as unverified.
- Open `fidelity.html` (or render both sides to PNG with `ansi_render.py` and open them with this host's image tool, [Host tools](#host-tools)) before you move on. Do not judge an unproven description.

## 7. Judge step

Inputs: the validated, fidelity-checked `description.json` (one per size and state), the outputs of the script checks below, [audit-checklist.md](audit-checklist.md), and the design brief (target sizes, framework, the screen's main question). The judge may know the app; only the describer may not.

```bash
python3 SKILL_DIR/scripts/contrast_check.py <theme_guess.name> --format md                 # floors: formats.md#contrast-floors
python3 SKILL_DIR/scripts/render_mockup.py audit/x/recon.mock --check --strict-ambiguous   # glyph/width lint on the screen text
```

1. Walk every checklist area. For each check, record **pass**, **fail**, **n/a** or **unverifiable** (definitions in the checklist's "How to use").
2. **A finding cites ids and quotes.** For example: `FS-03 fail — e201 state.evidence "gray bg … ❯ marker" (pass); r3 has no selected row` or `CA-06 fail — e207 span 19..25 fg.faint #7f849c on selection.bg #3b3d4f = 2.89:1 (floor 3.0)`. Floors are those of [formats.md](formats.md#contrast-floors). A finding without an id or a measured value is not admissible.
3. **No eyeballing.** If a check needs a fact the description lacks, mark it *unverifiable* and request **one** targeted re-description: a pass-2 crop of that region with the specific question added as a neutral "also report" line. Live-capture alternatives: re-capture with `-k` keys, or another size or env. A check still unverifiable after that goes to the report's "Not verifiable" section.
4. **Uncertain fields** (`[?]`, an `uncertainties[]` entry, `confidence: low`) can only support *tentative* findings. Confirm them via §6 or a live capture before calling them blockers.
5. **Volatile cells** (`volatile_cells`, `volatile: true`) never support findings about changing values or inconsistent numbers.
6. **No theme fit → no token checks.** When `theme_guess` did not fit (§4 step 6; tokens are null), checks that compare tokens (CT-01, CT-02, CT-05, CT-09, FS-06, the token rows of CA-01..05) are `n/a (no theme fit)`; contrast is judged from `raw` pairs with `ratio` (CA-06, CA-07, CA-08). Light-theme screenshots at scale 1 collapse the grey tokens (§4.2): no finding may rest on which grey token a span uses.
7. **Classify each finding.** A *rendering bug* is output that differs from what the code intended: corruption, wrap, misalignment from width miscount, ghost lines. A *style issue* is an intended output that breaks a design rule. Bugs get a "likely mechanism" and "reproduce before declaring fixed".
8. Write the report from [templates/audit-report.md](templates/audit-report.md), with fixes mapped to the target framework's vocabulary ([vocabulary.md](vocabulary.md), [frameworks/](frameworks/)).

## 8. Calibration: measure the screenshot path before trusting it

Run calibration when the screenshot path meets a new kind of screen (borderless, dense charts, light theme, JPEG, very small cells) or a new describer model. The truth comes from the source mock: its `#! region` lines give regions and roles, `#! focus <region-id>` the focused region and `#! selected <region-id> <row>` the selected row, so focus and selection are scored too. Add those two lines to any mock you calibrate on.

```bash
python3 SKILL_DIR/scripts/render_mockup.py SKILL_DIR/assets/demo/fleet--normal--80x24.mock --theme catppuccin-mocha -o cal/fleet.ansi
uv run SKILL_DIR/scripts/ansi_render.py cal/fleet.ansi --theme catppuccin-mocha --format png --scale 2 -o cal/fleet.png
#  → run the screenshot path (§4) on the PNG (and on scaled variants) → cal/fleet.desc.json
python3 SKILL_DIR/scripts/score_description.py cal/fleet.desc.json \
    --truth-from-mock SKILL_DIR/assets/demo/fleet--normal--80x24.mock --theme catppuccin-mocha \
    --save-truth cal/fleet.truth.json --format md
```

- **Corpus.** Use our own mockups (`assets/demo/`, `assets/mockups/<archetype>/`) × one dark and one light theme × scales 2×, 1× and 0.5×. Add real live captures (lazygit, btop) when available. Cover borderless layouts, tables, braille charts, modals and CJK.
- **Perceivable truth** (the scorer applies it). Attributes the renderer does not draw (bold on box-drawing glyphs, blink, hidden) are dropped, tokens that share an RGB value are one class, reverse video on spaces and full blocks count as bg, and chart cells are excluded from CER. Otherwise the describer is penalised for being right.
- **Pass bars:** grid exact · region mean IoU ≥0.9 and exact boxes ≥80% · roles ≥85% · row CER ≤2% and hallucination CER (substitutions excluding `[?]`, plus insertions) ≤0.5% · colour tokens ≥95% (pixel path) · focused region, selected elements and checked/expanded exact · key-hint F1 ≥0.9 · neutrality 0 evaluative tokens · reconstruction text and bg ≥98% of cells. Report attributes (gate only reverse and underline) and `[?]` precision.
- **Failing a bar** changes the protocol for that screen kind. Examples: CER too high → force crops with rulers; regions miss → tile pass 1; colours miss → check `sample_colors.py` theme residual. Record the result and its date in the audit report's meta. Current results: §4.2 "What to expect".

## 9. Quick troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| Describer output fails validation | shape outside the contract (id strings as `children`, `top-left`, numeric confidence, boolean `truncated`, `target` instead of `ref`) | send the validator lines back to the same describer ([Host tools](#host-tools)); check the prompt was built by `describe_prompt.py` |
| Pass 1 runs disagree on many boxes | grid wrong, or image below 8 px/cell | re-run `prep_screenshot.py` with the user's cols×rows or an anchor line; upscale; tile |
| Header/statusbar boxes narrower than the screen | text-extent boxes for borderless bands | set `x = 0, w = cols` when reconciling pass 1 |
| Rows shifted by one column after merge | column pitch drift (≤0.6 col over 120 is normal) | anchor on the longest line; re-cut crops |
| Many `ink_mismatch` on spaces | collapsed space runs | re-crop with the ruler; use a live capture if possible |
| Parent panel title blank or wrong in `screen_text` | parents get no pass 2; pass 1 title missing or misread | fix `title.text` in `pass1.json` (re-run pass 1 if unsure) and re-merge |
| All colours `token: null` | `sample_colors.py` found no fitting theme | expected for unknown themes: use `raw` hex for contrast, skip token checks (§7 step 6); use a live capture when possible |
| Description valid but the judge keeps saying "unverifiable" | regions too coarse, elements missing | pass 2 on those regions with an "also report …" line |

## Host tools

Match the harness you are running in. Use that row whenever you open an image, start a describer, or send a correction back to it. Checked 2026-10-04.

| Host | Open an image | Start a describer | Continue that describer |
|---|---|---|---|
| Claude Code | `Read` | `Agent` (`general-purpose`) | `SendMessage` |
| Codex CLI | `view_image` | `spawn_agent` | `send_input` |
| Cursor | `Read` | `Task` | resume that agent id |
| Gemini CLI | `read_file` | `invoke_agent` (`generalist`) | — |
| GitHub Copilot CLI | `view` | `task` (`general-purpose`) | `write_agent` |
| OpenCode v2 | `read` | `subagent` (`general`) | `subagent` with the `sessionID` it returned |
| OpenCode v1 | `read` | `task` (General) | — |
| Pi | `read` | — | — |
| Pi with `pi-subagents` | `read` | `subagent` | `subagent` on that same child |

The word in parentheses is the agent you pass to the tool. A dash under **Start a describer** means this host has no subagent tool: run the describer prompt in this session. That work sees the prompt and the images. Save the JSON, then judge. A dash under **Continue that describer** means the child returns one result: put the validator lines and "Return the corrected JSON object only" into a new prompt and start a fresh describer. Two continuations, then one fresh describer.

- **Cursor.** The published docs describe image reading as a tool call and leave the tool's string unnamed. Use `Read`, the name in the editor's tool list and in failure reports. Continuing is by the agent id the host returned.
- **Gemini CLI.** Call `invoke_agent` and name `generalist`. The docs also describe each built-in agent as a tool of its own name.
- **OpenCode.** v2 is the current docs: `read` passes PNG, JPEG, GIF, WebP and PDF (up to 20 MiB). `subagent` takes an agent id; `general` is the built-in for multi-step work and `explore` is the read-only one. Pass the returned `sessionID` to continue that child. v1 docs are still published: there `read` is file contents and line ranges, and the agents page calls the launcher the Task tool (permission `task`; built-ins General, Explore, Scout). A tool list that contains `subagent` is the v2 row. A tool list that contains `task` and not `subagent` is the v1 row.
- **Pi.** The built-in tools are `read`, `bash`, `edit` and `write`, and `read` takes images. The package `pi-subagents` adds `subagent`. On some models the first request only shows `subagents_enable`: call it, then call `subagent` on the next request. Other subagent packages use other tool names.

The describer preamble lists these same image tools, so the child opens the files without this table.
