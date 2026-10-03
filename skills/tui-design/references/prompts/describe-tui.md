# describe-tui — prompt for the vision describer subagent

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [1. Assembling one call](#1-assembling-one-call) · L17–45 — building one describer prompt with `describe_prompt.py` (never by hand).
- [2. Preamble (every call)](#2-preamble-every-call) · L47–141 — the rules every describer call gets, or why a describer output broke one.
- [3. Pass 1 block (layout; input: full screen)](#3-pass-1-block-layout-input-full-screen) · L143–172 — the pass-1 (layout, full screen) prompt block.
- [4. Pass 2 block (one leaf region; input: crop with absolute margin ruler)](#4-pass-2-block-one-leaf-region-input-crop-with-absolute-margin-ruler) · L174–211 — the pass-2 (one leaf region, cropped) prompt block.
- [5. Live-capture addendum (exact text is known)](#5-live-capture-addendum-exact-text-is-known) · L213–225 — the addendum for a live capture, where the exact text is known.
- [6. Uncertainty conventions](#6-uncertainty-conventions) · L227–244 — how the describer marks what it cannot read or measure.
- [7. Worked example: Fleet demo, 80×24 (screenshot path, crisp 1× image)](#7-worked-example-fleet-demo-8024-screenshot-path-crisp-1-image) · L246–334 — a full pass-1/pass-2 output for the Fleet demo, to compare a describer output against.
- [8. Why the rules look like this (evidence)](#8-why-the-rules-look-like-this-evidence) · L336–351 — the evidence behind the describer rules, before changing one.

Read this when you dispatch a describer subagent for an audit ([../audit-protocol.md](../audit-protocol.md) §4.1; live capture step 4 in §3, screenshot steps 2 and 5 in §4) or when a describer output fails validation. This file holds the prompt blocks: a preamble, a pass-1 or pass-2 block, and, for a live capture, an addendum. The output contract is [../schemas/tui-description.schema.json](../schemas/tui-description.schema.json): pass 1 must validate against `$defs/describer_pass1`, pass 2 against `$defs/describer_pass2`.

The describer is a **perception instrument**. It reports what is drawn and never says whether it is good. It also never learns what the app is or what the user dislikes about it. Judging happens later in a separate step ([../audit-checklist.md](../audit-checklist.md)).

## 1. Assembling one call

Never fill the blocks by hand. `describe_prompt.py` builds the exact prompt for one dispatch: **Preamble + (Pass 1 | Pass 2) [+ live-capture addendum] + OUTPUT CONTRACT**. The contract is generated from the schema (`$defs/describer_pass1` / `describer_pass2` and every enum they reach), so it lists every allowed key and value.

```bash
# pass 1 (full screen)
python3 SKILL_DIR/scripts/describe_prompt.py --pass 1 --grid prep/grid.json -o prompt.pass1.txt
# pass 2 (one leaf region; its crop from crops.json, its record from the reconciled pass 1)
python3 SKILL_DIR/scripts/describe_prompt.py --pass 2 --grid prep/grid.json --crops prep/crops.json \
    --pass1 pass1.json --region r3 -o prompt.pass2.r3.txt
# Live capture: add the exact text from ansi_grid.py --describe
python3 SKILL_DIR/scripts/describe_prompt.py --pass 1 --grid prep/grid.json --path capture --text 120x30.skeleton.json -o p.txt
```

The script fills the placeholders below from the facts of **the image the describer actually sees** (the downscaled pass-1 image or the upscaled crop), not from the original screenshot:

| Placeholder | Filled from | Example |
|---|---|---|
| `{{cols}}`, `{{rows}}` | `grid.json` (`--cols/--rows` given to `prep_screenshot.py` win) | `80`, `24` |
| `{{grid_confidence}}` | `grid.json` `grid_confidence` and `advice` | `0.99 (advice: ok)` |
| `{{image_list}}` | absolute paths with a one-phrase label each; the ruler image is added for crops, for `advice: check-ruler`, or with `--ruler` | `/…/prep/pass1.png  (plain full screen)` |
| `{{geometry}}` | `pass1.{cell_px, origin_px}` or the crop's `{cell_px, origin_px}`, in that image's pixels | `cell (0,0) top-left at (0.3,0.7) px; cells 16.8 x 36.0 px` |
| `{{region_id}}`, `{{n}}`, `{{region_record}}` | pass 2: the region id, its number, its pass-1 object without `children` | `r2`, `2`, `{"id":"r2","role":"list",…}` |
| `{{crop_note}}` | pass 2: which cells the image shows | `The image shows cells x=0..32, y=0..22: region r2 plus a 1-cell margin.` |
| `{{screen_text_numbered}}` | Live capture: `screen_text`, one row per line, prefixed `NN|` | `05|│   ✗ search …` |

`grid.json` `advice` decides whether to dispatch at all: `ok` → dispatch; `check-ruler` → the script adds `pass1-ruler.png`, and you first open it yourself to confirm the labels sit on the cells; `give-size` → the script refuses (exit 3): get the terminal size from the user and re-run `prep_screenshot.py --cols C --rows R` (audit-protocol §4 step 1).

**Never include:** the app's name or command line; the user's complaint or design goals; the audit checklist; earlier findings; theme names; any hex value. Each of these pushes the describer toward completing text from its priors instead of reading it.

## 2. Preamble (every call)

```text
ROLE
You are a perception instrument. You describe what is visible in images of a terminal user
interface so that another agent can evaluate it later. You do not evaluate, recommend, or guess
the application's identity, purpose or behaviour.

TOOLS
Open each image listed below with the image tool of the host you are running in:
Claude Code: Read. Codex CLI: view_image. Cursor: Read. Gemini CLI: read_file.
GitHub Copilot CLI: view. OpenCode: read. Pi: read.
Read nothing else. Your final message must be exactly one JSON object: no prose, no code fence, no comments.

FACTS FROM THE MEASUREMENT SCRIPT (authoritative: do not recount or override)
- Grid: {{cols}} columns x {{rows}} rows of character cells. 0-based: x = column, y = row.
  Grid confidence: {{grid_confidence}}.
- Images:
{{image_list}}
- Plain image geometry: {{geometry}}.
- A ruler image is the same picture with a white margin added: column numbers above and below
  every 10 columns (short ticks every 5), row numbers on the left and right. Labels are ABSOLUTE
  screen coordinates. Rulers are NOT part of the UI: never transcribe them.
If the image clearly contradicts the grid (text runs past the last column, rows are cut), add an
uncertainty with kind "count" and keep using the given numbers.

RULES
1. Verbatim. Copy characters exactly as drawn: punctuation, box-drawing glyphs, arrows, bullets,
   and every run of spaces inside a line. Do not fix spelling, casing or spacing.
2. Never complete text. If a word is cut by a border, an ellipsis or the image edge, copy only the
   visible part and set "truncated" to "start", "end" or "both". Do not use knowledge of any real
   application, language or font to fill gaps. A shape drawn across several cells (a font ligature,
   such as one arrow or one double bar spanning 2 cells) is not expanded into the characters you
   think produced it: write [?] for each cell it spans and add an "ambiguous_glyph" uncertainty
   whose alternatives list the drawn shape and the candidate characters (for example "→", "->").
3. Unreadable cells: write [?] for each cell you cannot read and [?*] for a run of unknown length.
   A [?] is always better than a plausible guess. Add one uncertainty per [?] group with your
   best "alternatives". Look-alikes: transcribe the one that is drawn and, when two are hard to
   tell apart, add an "ambiguous_glyph" uncertainty listing both:
   │ ┃ ▏ ▐ | l I 1    ─ ━ — - ‐    ╭ ┌ +    · • ∙ ●    O 0 ○ ◯    … ⋯ ...    ❯ > ›
   ✓ ✔    ✗ ✕ × x    ▲ △ ^    ▸ ▶ ►
   A thicker or offset vertical bar on a border column is often a scrollbar (▐ ▕ █), not │.
4. Positions come from the grid. Read x/y from ruler labels or by counting cells from a labelled
   neighbour. Never estimate from pixels. A bbox includes the border. Wide characters (CJK,
   emoji) occupy 2 cells. A band without a border that runs across the screen (header, menubar,
   tabbar, statusbar, footer, keybar) spans the full width: bbox x = 0 and w = {{cols}}, even
   when its text is shorter.
5. Colours: give only a coarse name in color.name (black, red, green, yellow, blue, magenta, cyan,
   white, gray, orange, purple, pink, default) with "source": "vision". Never output hex values or
   theme names; a script measures colours from pixels. If two hues are hard to separate, add an
   uncertainty of kind "colour" listing both.
6. Attributes (bold, dim, italic, underline, reverse, strike): report one only when it is clearly
   visible, and set attrs_confidence ("high", "medium" or "low"). A solid colour bar behind text
   (a selection bar, a header band, a chip) is a background colour: describe it as style.bg, never
   as "reverse". The colour sampler and the scorer record such bars as background too. Text that
   looks like a fainter copy of a nearby hue gets an uncertainty of kind "attribute" with
   alternatives ["dim", "gray fg"].
7. Neutral language. These words are forbidden in every field: good, bad, clean, cluttered, nice,
   ugly, clear, unclear, confusing, consistent, inconsistent, should, could, too, better, worse,
   well, poorly, intuitive, readable, cramped, busy, polished, broken, wrong, missing, issue,
   problem. State what is there, where, and how it looks.
   NOT "the footer is cramped". YES "row 23 holds 7 key hints; text ends at x=78".
8. Do not invent. Every element must have visible ink or a visible coloured background inside its
   bbox. Blank space is not an element. Do not describe behaviour you cannot see (what a key does).
9. States need evidence. Whenever you set focused/selected/checked/expanded/current/disabled/busy,
   write the visible difference in state.evidence ("gray bg across x=1..30 that sibling rows lack;
   ❯ marker at x=2"). No visible difference: leave the field out.
10. Charts, sparklines, gauges, braille or block graphs: the area is a region of role "chart" (or
   an element of type chart, sparkline, gauge or progress_bar inside another region). Its "name"
   says what kind of plot it is in a few words ("braille line graph", "block bar per core"). Copy
   labels, axis text and printed numbers verbatim. Do not transcribe the plot glyphs cell by cell:
   in "rows" write one [?*] for each run of braille or block plot glyphs, and never read a value
   off the drawn shape.
11. Overlays. A modal, popup_menu, toast or tooltip drawn over other content gets "z": 1 (or
   higher when stacked) and "occludes": the ids of the regions it covers. Regions under it keep
   their full bbox and "z": 0; describe only their visible cells.
12. Output shape. Use only the keys and values listed in the OUTPUT CONTRACT at the end of this
   prompt. When a value is unknown or absent, leave the key out instead of writing null, unless
   the contract lists null.

VOCABULARY (use these ids only)
Region roles: screen header menubar tabbar toolbar sidebar list table tree detail editor log chart
  form input statusbar footer keybar modal toast popup_menu tooltip panel other
Element types: text heading label value button link key_hint tab list_item table_header table_row
  table_cell tree_item checkbox radio toggle input_field placeholder cursor prompt progress_bar
  gauge sparkline chart separator scrollbar badge icon spinner status_indicator breadcrumb message
  other
Border styles: none single rounded double heavy dashed ascii block mixed
Key names (key_hints[].key, lower case): enter esc space tab shift+tab backspace delete up down
  left right home end pgup pgdn f1..f12, ctrl+x / alt+x / shift+x, or the literal character
  ("q", "?", "/"). Several keys for one action: join with "/" ("up/down", "j/k"). Keep the drawn
  form in key_raw ("↑↓", "^O", "<enter>", "⏎").
Key concepts (optional): quit help confirm cancel save search filter refresh navigate select
  toggle edit delete copy open close new
```

## 3. Pass 1 block (layout; input: full screen)

```text
PASS 1 — LAYOUT
Describe the regions of the screen. Do not list elements yet.
A region is a visually delimited area: a border, a background block, a separator line, or a
block of consistently aligned text. r0 is the whole screen (role "screen", bbox 0,0,{{cols}},{{rows}}).
Number the others r1, r2, … in reading order (top-to-bottom, then left-to-right) and set "order".
Nest them: r0 "children" holds the full region objects of the top-level regions (never id
strings); a bordered panel that contains other panels holds them in its own "children".
Overlays (modal, popup_menu, toast, tooltip) are children of r0 listed last, with z >= 1 and
"occludes" (rule 11). An empty bordered box is still a region.
Only leaf regions (no children) are described again in pass 2. The border and title of a parent
region come from this pass alone, so copy a parent's title text verbatim into title.text and give
its border.style.

Return exactly:
{
  "regions": [ the r0 region object, with the others nested in "children" ],
  "anchor_lines": [ 1 to 3 objects {y, x_start, text}: the longest single-row runs of plain text
               (at least 8 characters, letters and digits preferred, no box glyphs) that you
               read with full confidence, copied verbatim ],
  "focus_summary": "<region id> plus the visible evidence, or 'none visible'",
  "uncertainties": [ {ref, field, kind, note, alternatives, source: "vision"} ]
}
Region title text excludes the border glyphs and the padding spaces around it.
Before answering, check: every bbox lies inside 0..{{cols}}-1 x 0..{{rows}}-1; full-width bands
have x = 0 and w = {{cols}}; sibling regions at the same z do not overlap; every focused/selected
flag has evidence; every key and value appears in the OUTPUT CONTRACT.
```

## 4. Pass 2 block (one leaf region; input: crop with absolute margin ruler)

```text
PASS 2 — DETAIL OF REGION {{region_id}}
{{crop_note}} Ruler labels are ABSOLUTE screen coordinates, so use them directly.
The pass-1 record of this region is:
{{region_record}}

Return exactly:
{
  "region": "{{region_id}}",
  "rows": [ {y, x, text} for every row y of the region's bbox, border and title cells included;
            x = bbox.x; text padded with spaces to exactly bbox.w cells ],
  "elements": [ element objects: id ("e{{n}}01", "e{{n}}02", …), region "{{region_id}}", type,
            name (generic, e.g. "service row"), bbox, text (verbatim, = the cells of the bbox),
            truncated, spans[{start, len, style}], style{fg, bg, attrs, attrs_confidence},
            state{…, evidence}, interactive, key_hints[{key, key_raw, action, concept, bbox}],
            order, source: "vision", confidence ],
  "uncertainties": [ {ref, field, kind, note, alternatives, source: "vision"} ]
}

Element guidance:
- One element per list row, table row, tree row, key-hint group, label/value line, tab, button,
  message line. Split a row into table_cell elements only when columns are visibly aligned
  across rows.
- spans: style runs inside the element; start is the cell offset from bbox.x. Add a span wherever
  the colour or attribute changes (status glyph, coloured status word, highlighted key).
- Key hints: parse every "key action", "action: key", "<key> action", "[k]ey", "^X Action" pattern
  into key_hints. Record the hints in the order drawn and do not reorder them.
- Selection/focus: if one row has a background, leading marker (❯ ▶ > * ●) or bold that its
  siblings lack, set state.selected (or current) and put the difference in evidence.
- Scrollbars and "N more" / "1 of 5" counters: their own elements (scrollbar / text), verbatim.
- Charts: rule 10. Cells hidden under an overlay: leave them as spaces and add one uncertainty of
  kind "occluded" with ref = this region.
Before answering, check: len(rows) == bbox.h; each row is exactly bbox.w cells ([?] = one cell);
each element's text equals the matching slice of rows; each element bbox lies inside the region
bbox; every key and value appears in the OUTPUT CONTRACT.
```

## 5. Live-capture addendum (exact text is known)

`describe_prompt.py --path capture --text SKELETON.json` appends this block to pass 1 and pass 2 when the screen was captured live. The image is then `ansi_render.py` output of the capture. Text and colours come from the capture. The describer contributes **structure, roles, element segmentation and states** only.

```text
GIVEN TEXT (exact, from the terminal capture; authoritative)
Each line is "row|text". Copy text from here instead of reading it from the image; if the image
seems to differ, the text below wins.
{{screen_text_numbered}}
Colours and attributes are measured from the capture. Leave style.fg/bg/attrs out, except where
a style difference is your evidence for a state (then name the colour coarsely in evidence).
In pass 2, "rows" may be an empty list.
```

## 6. Uncertainty conventions

| Situation | In the text | In `uncertainties[]` |
|---|---|---|
| One unreadable cell | `[?]` (counts as 1 cell) | `kind: unreadable`, `alternatives` = best guesses |
| Unreadable run of unknown length | `[?*]` | `kind: unreadable`, `note` with the approximate x-range |
| Look-alike glyph (`│`/`▐`, `✗`/`✕`/`×`) | the glyph that is drawn | `kind: ambiguous_glyph`, all candidates in `alternatives` |
| Ligature across cells | `[?]` per cell | `kind: ambiguous_glyph`, drawn shape + candidate characters |
| Braille or block plot | `[?*]` per plot run, labels verbatim | none (rule 10; the scorer excludes chart cells from CER) |
| Position or width unsure | best bbox | `kind: position`, `field: "bbox.w"` |
| Hue on a boundary (yellow vs green) | coarse name | `kind: colour`, both names |
| Attribute unsure | omit, or set it with `attrs_confidence: "low"` | `kind: attribute` |
| State unsure (selected or just coloured?) | omit the flag | `kind: state`, note the visible cue |
| Text cut by border or edge | visible part only, `truncated` set | `kind: truncated` only when the cut point itself is unclear |
| Region covered by an overlay | describe the visible part | `kind: occluded`, `ref` = covered region |
| Grid facts look wrong | keep the given numbers | `kind: count` |

Every uncertainty has exactly the keys `ref` (a region or element id), `field`, `kind`, `note` (required), `alternatives`, `source`. The merge step adds two more kinds: `ink_mismatch` (pixels contradict the transcription) and `disagreement` (two passes, or script vs model, differ); a describer never uses them. Confidence fields are hints only, because verbalized model confidence is miscalibrated ([arXiv 2505.20236](https://arxiv.org/abs/2505.20236)). Accuracy comes from cross-checks.

## 7. Worked example: Fleet demo, 80×24 (screenshot path, crisp 1× image)

Source: `assets/demo/fleet--normal--80x24.mock` rendered with `catppuccin-mocha`. Every coordinate below was checked against the mock text, and each object validates with `python3 SKILL_DIR/scripts/merge_description.py --validate FILE --part describer_pass1|describer_pass2`.

**Pass 1 output:**

```json
{"regions":[
 {"id":"r0","role":"screen","bbox":{"x":0,"y":0,"w":80,"h":24},"z":0,"children":[
  {"id":"r1","role":"header","bbox":{"x":0,"y":0,"w":80,"h":1},"border":{"style":"none"},"order":0,"z":0},
  {"id":"r2","role":"list","bbox":{"x":0,"y":1,"w":32,"h":21},"border":{"style":"rounded"},
   "title":{"text":"Services (6)","position":"top_left"},
   "state":{"focused":true,"evidence":"border drawn in blue; r3 border drawn in gray; ❯ marker at x=2 y=2"},"order":1,"z":0},
  {"id":"r3","role":"detail","bbox":{"x":32,"y":1,"w":48,"h":21},"border":{"style":"rounded"},
   "title":{"text":"api-gateway","position":"top_left"},"state":{"focused":false,"evidence":"border drawn in gray"},"order":2,"z":0},
  {"id":"r4","role":"statusbar","bbox":{"x":0,"y":22,"w":80,"h":1},"border":{"style":"none"},"order":3,"z":0},
  {"id":"r5","role":"keybar","bbox":{"x":0,"y":23,"w":80,"h":1},"border":{"style":"none"},"order":4,"z":0}]}],
 "anchor_lines":[{"y":22,"x_start":3,"text":"deployed api-gateway v2.4.1"},
                 {"y":23,"x_start":24,"text":"/ filter  r restart  tab pane"}],
 "focus_summary":"r2: its border is blue while r3's is gray, and it contains the ❯ marker",
 "uncertainties":[{"ref":"r1","field":"role","kind":"other","source":"vision",
   "note":"row 0 holds an app label, three numbered labels and a right-aligned context",
   "alternatives":["header","tabbar"]}]}
```

**Pass 2 output for `r5` (key bar):**

```json
{"region":"r5",
 "rows":[{"y":23,"x":0,"text":" ↑↓ select  enter open  / filter  r restart  tab pane            ? help  q quit "}],
 "elements":[
  {"id":"e501","region":"r5","type":"key_hint","name":"left key-hint group","bbox":{"x":1,"y":23,"w":52,"h":1},
   "text":"↑↓ select  enter open  / filter  r restart  tab pane",
   "style":{"bg":{"name":"gray","source":"vision","confidence":"medium"}},
   "key_hints":[
    {"key":"up/down","key_raw":"↑↓","action":"select","concept":"navigate","bbox":{"x":1,"y":23,"w":9,"h":1}},
    {"key":"enter","key_raw":"enter","action":"open","concept":"confirm","bbox":{"x":12,"y":23,"w":10,"h":1}},
    {"key":"/","key_raw":"/","action":"filter","concept":"filter","bbox":{"x":24,"y":23,"w":8,"h":1}},
    {"key":"r","key_raw":"r","action":"restart","concept":null,"bbox":{"x":34,"y":23,"w":9,"h":1}},
    {"key":"tab","key_raw":"tab","action":"pane","concept":"navigate","bbox":{"x":45,"y":23,"w":8,"h":1}}],
   "order":0,"source":"vision","confidence":"high"},
  {"id":"e502","region":"r5","type":"key_hint","name":"right key-hint group","bbox":{"x":65,"y":23,"w":14,"h":1},
   "text":"? help  q quit",
   "key_hints":[
    {"key":"?","key_raw":"?","action":"help","concept":"help","bbox":{"x":65,"y":23,"w":6,"h":1}},
    {"key":"q","key_raw":"q","action":"quit","concept":"quit","bbox":{"x":73,"y":23,"w":6,"h":1}}],
   "order":1,"source":"vision","confidence":"high"}],
 "uncertainties":[{"ref":"e501","field":"style.attrs","kind":"attribute","source":"vision",
   "note":"key glyphs look heavier than the action words; bold not certain"}]}
```

**Pass 2 for `r2` (excerpt: 3 of the 21 rows and 2 of the 6 elements):**

```json
{"region":"r2",
 "rows":[{"y":1,"x":0,"text":"╭─ Services (6) ───────────────╮"},
         {"y":2,"x":0,"text":"│ ❯ ● api-gateway   running    │"},
         {"y":5,"x":0,"text":"│   ✗ search        failed     │"}],
 "elements":[
  {"id":"e201","region":"r2","type":"list_item","name":"service row","bbox":{"x":1,"y":2,"w":30,"h":1},
   "text":" ❯ ● api-gateway   running    ",
   "spans":[{"start":1,"len":1,"style":{"fg":{"name":"blue","source":"vision"}}},
            {"start":3,"len":1,"style":{"fg":{"name":"green","source":"vision"}}},
            {"start":5,"len":11},
            {"start":19,"len":7,"style":{"fg":{"name":"green","source":"vision"}}}],
   "style":{"bg":{"name":"gray","source":"vision","confidence":"medium"}},
   "state":{"selected":true,"evidence":"gray background across x=1..30 that sibling rows lack; ❯ marker at x=2"},
   "order":0,"source":"vision","confidence":"high"},
  {"id":"e204","region":"r2","type":"list_item","name":"service row","bbox":{"x":1,"y":5,"w":30,"h":1},
   "text":"   ✗ search        failed     ",
   "spans":[{"start":3,"len":1,"style":{"fg":{"name":"red","source":"vision"}}},
            {"start":19,"len":6,"style":{"fg":{"name":"red","source":"vision"}}}],
   "order":3,"source":"vision","confidence":"high"}],
 "uncertainties":[]}
```

After the merge, `sample_colors.py` replaces each `name` with measured values. For example, e201 `style.bg` becomes `{"token":"selection.bg","raw":"#3b3d4f","source":"pixel","confidence":"high"}`.

**Common invalid shapes** (fix these when a describer output fails validation):

| Written | Allowed |
|---|---|
| `"children": ["r1","r2"]` | `"children": [{"id":"r1",…}, …]` |
| `"position": "top-left"` | `"position": "top_left"` |
| `"confidence": 0.9`, `"attrs_confidence": 0.8` | `"high"`, `"medium"`, `"low"` |
| `"truncated": true` / `false` | `"start"`, `"end"`, `"both"`, or leave the key out |
| uncertainty `{"target":…, "where":…, "detail":…}` | `{"ref", "field", "kind", "note", "alternatives", "source"}` |
| uncertainty `"kind": "glyph"` | `"ambiguous_glyph"` |
| `"bg": null` | leave `bg` out |

## 8. Why the rules look like this (evidence)

| Rule | Evidence |
|---|---|
| Script gives cols×rows; the model never counts | BlindTest grid counting: Claude 3.5 Sonnet 59.8% on empty grids ([arXiv 2407.06581](https://arxiv.org/abs/2407.06581)). `measured:` text-filled panels were counted right in 5/5 runs |
| `[?]` instead of guessing; no completion | Claude completed a truncated "C CONU" into "Coconut Milk" ([arXiv 2502.06445](https://arxiv.org/html/2502.06445v1)). `measured:` 5 of 5 `[?]` marks fell on the truly ambiguous `▐` |
| Ligatures are not expanded | `measured:` on a helix screenshot the describer turned 2-cell ligature arrows back into `->`, `=>`, `==` from prior knowledge of the font |
| Look-alike list | `measured:` the only text errors in 5 runs were `▐`→`│`, `─`↔`-`, and one dropped or added space; also `✗` vs `✕`/`×` |
| Full-width bands | `measured:` borderless header bands got text-extent boxes (`x=1, w=118` on 120 cols), which cost region IoU |
| Charts as one element, plot runs as `[?*]` | `measured:` a braille dashboard at 120×30 gave 417 `[?]` and 12% CER when plots were transcribed per cell |
| Generated output contract | `measured:` 100% of first describer outputs failed schema validation on shapes the prose did not pin down (§7 table) |
| Coarse colour names only | ColorBench exact-value extraction is 56.2% for the best model ([arXiv 2504.10514](https://arxiv.org/html/2504.10514)). `measured:` pixel unmixing reached 98.4% token accuracy at 0.37× scale |
| Positions from rulers or labels | Set-of-Mark: RefCOCOg 25.7 → 86.4 when the model refers to marks instead of raw coordinates ([arXiv 2310.11441](https://arxiv.org/abs/2310.11441)) |
| Plain image for pass 1; ruler only on small or upscaled images | `measured:` ruler on a crisp 1× image gave 3/8 exact rows vs 7/8 plain; on a 0.37× image upscaled 1.95× it gave 8/8 vs 3/8 |
| Neutral word ban | keeps the judge's evidence free of conclusions; the calibration neutrality score (evaluative tokens) must be 0 |
| No app name | `measured:` describers never named lazygit when it was not given; naming it invites priors |
