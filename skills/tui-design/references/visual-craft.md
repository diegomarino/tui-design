# Visual craft: from correct to good

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [Ambition: reframe before restyling](#ambition-reframe-before-restyling) · L15–80 — design step 2: three genuinely different concepts before restyling, with a worked example.
- [Principles](#principles) · L82–255 — 13 principles that make a correct frame good (composition, hierarchy, color budget, surfaces, selection, signature…).
- [Aesthetic rubric](#aesthetic-rubric) · L257–292 — design step 6: scoring frames C1–C8 (0–2 each), with calibration.
- [README test](#readme-test) · L294–316 — would the frame sell the tool in a README; the failure patterns.
- [Exemplar corpus](#exemplar-corpus) · L318–346 — public screenshots to compare against; rarely needed.

The other references make a frame **correct**: tokens, glyph widths, states, contrast, clutter. A frame can pass
every lint and still look poor or unambitious. This file sets the bar above correct. The worked example (a deploy
console: one job, three concepts, each frame rendered at 256 and 16 colors and scored) is described at the end of
[Ambition](#ambition-reframe-before-restyling).

## Ambition: reframe before restyling

**Rule.** Before you mock states and sizes, produce **three genuinely different concepts**, one normal frame each
at the main size. Then pick one, or merge two.

**Why.** Starting from the current screen produces "the same table, improved": a redesign that keeps the
inventory table and tunes its columns never asks whether a table is the right shape.

**How to generate the three:**

1. Write the job as verbs, objects and frequency. For example: "see what is rolling out (often, at a glance);
   spot what is unhealthy (any time); approve or reject what waits for a human (several times a day)".
2. Pick three different **anchors**. The anchor is the object that owns most of the screen. Concepts that differ
   only in column order or colors count as one concept.

   | Anchor (shape) | The screen is… | Good when | Exemplar |
   |---|---|---|---|
   | Queue / inbox | the items that need action, one in focus, with progress | a backlog gets processed, then the queue empties | gh-dash, mail clients, `git add -p` |
   | Map / topology | a spatial overview, with items placed inside their containers | where things are matters; IDs belong to a hierarchy | btop boxes, k9s xray, yazi columns |
   | Spotlight / palette | a query whose results resolve as you type | the user arrives with a key (an ID, a name) | atuin, fzf, the helix picker |
   | Dashboard + drilldown | counts, meters and trends, then one level of detail | "is everything OK?" comes before "fix this one" | btop, dolphie, bottom |
   | Feed / timeline | events in order, newest at the edge | change over time is the content | toolong, the lazygit command log |
   | Document / editor | one object, edited in place | a single rich object | helix, posting |

3. For each concept, record: the anchor, the **signature element** (principle 8), what it makes fast, what it
   makes slow, and which host limits it hits. A feature that needs an API the host lacks is labelled "needs
   <host> support" in the frame notes, not drawn as if it worked.
4. **Choose** with a short table: fit to the primary verb (keys needed to do it), fit to the data (does real data
   at the expected counts fill the screen?), fit to the host, signature. Merging is allowed: give the primary
   verb the anchor and put the secondary verb behind one key.

**Worked example: a deploy console.** Job: see what is rolling out (often), spot what is unhealthy (any time),
approve or reject what waits for a human (several times a day, one at a time). Data: 7 services in staging and
prod, 4 requests waiting, 12 events today (invented, and every frame says so in a `#! note:`). Each concept was
built with `mockkit.py` at 120×30 and 80×24 and scored on the rubric below at 256 and 16 colors.

| Concept | Anchor | Signature | Makes fast | Makes slow | Rubric 120×30, 256 / 16 |
|---|---|---|---|---|---|
| A. Feed | events, newest first; the selected event opens in place with its cause | live rollouts pinned above the timeline as meters (`━━━━━━──── 3/5 pods`) | "what changed, and when" | comparing services; a backlog | 15 / 15 |
| B. Board | services × environments, prod health first; the selected service drills down | a staging/prod strip (one glyph per service) plus error and latency sparklines | "is everything OK?" | the history behind a change | 15 / 14 |
| C. Approvals | requests waiting for a human, as cards; the selected card joins a surface with its evidence | the joined card, approval pips `●○ 1/2`, diff bars | approving with checks, diff and staging data on one screen | seeing system health | 16 / 15 |

Chosen: **C** as the home screen, with B behind `tab` for health and A's expanded event as the detail view of a
failure. C wins because approving is the only verb that needs a person; health and history support it. Excerpt of
C at 80×24 (left: the queue, oldest first; right: the selected request's evidence; no boxes):

```
  Waiting  4 ───────── oldest first
 ▌ ◇ payments  v1.9.3         prod    payments › prod › v1.9.2 → v1.9.3
 ▌   fix currency rounding on par⋯    fix currency rounding on partial refunds
                                      sam · 42m ago · on staging since 14:05
   ◇ api  v2.5.0              prod
     paginate /v2/orders, drop th⋯    Approvals  1 of 2 ──────────────────────
                                      ✓ priya    approved 20m ago
   ◇ web  v3.18.1             prod    ◇ you      your call
```

The frames leave open decisions and say so: whether a note is required to reject, what "degraded" means (an
error-rate alert line), whether `r` retries a failed rollout or files a new request.

**Check.** Three frames exist, their anchors differ, and the choice is written down with its reason.

**Ambitious in presentation, honest in function.** A plugin host such as tmux or Neovim limits behavior: which
APIs exist, what can be focused, which events arrive. It rarely limits looks, because the pane is a full
terminal. Take the color depth from what the **host** supports, verified with `tput colors` and `$COLORTERM`
inside it (or the test card), not from what the current code happens to use.

## Principles

Each principle gives the rule, why it matters, an example (`[exemplar]` from the corpus, or the deploy-console worked example), and how
to check it on a rendered PNG.

### 1. Composition: fill the screen with purpose

- **Rule.** Size each region to the data at its expected count, and give the leftover space to the region that
  benefits: detail, preview, roster, summary. A dead band (space no state of the screen uses) is never acceptable.
  Empty space goes in three places only: gutters (1–2 cells at the sides), gaps between groups (1 row), and above
  content anchored to the bottom (an input, an action preview). Never as a hole after the last table row.
- **Why.** A half-empty screen reads as unfinished, whatever the quality of the rows.
- **Example.** [btop] fills every box, and the CPU graph spans the full box width. [superfile] fills 4 panels plus
  a bottom strip. [yazi] splits its columns about 1:4:3, giving the narrow parent column less space. Counter-
  example: an 11-row table in a 27-row body with the detail 25 rows below the selection; [gitui] shows two empty
  panes in its own README. Showcase B at 80x24 moved the environment strips above the drill-down so the detail
  surface has no hole.
- **Check.** On the PNG, a contiguous empty block of more than ~20% of the body with no role fails. A list
  viewport with room to grow is allowed only when the leftover cannot serve another region.

### 2. Hierarchy in four layers

- **Rule.** Assign every cell to one layer:
  - **L1 focus / primary:** bold, plus the accent or the brightest fg. At most ~5% of cells.
  - **L2 content:** `fg.default`.
  - **L3 meta:** `fg.muted` / `fg.faint` for IDs, paths, ages, units, counts' nouns.
  - **L4 chrome:** borders, rules and separators in `border.default`.

  The brightest thing on screen must be the thing the job is about.
- **Why.** Readers scan by contrast. If the container names are the boldest column, the eye lands on containers,
  not on the items that need action; if a placeholder and real values share one weight, nothing stands out.
- **Example.** [dolphie] draws values bright and units dim (`13.85GB/32GB`). [soft-serve] puts bright author names
  inside a dim connector line. [posting] makes the focused panel title bold and the unfocused one dim.
- **Check.** The squint test: view the PNG at about 25% size. What remains visible should be L1 and the job's
  objects.

### 3. Color budget: one accent plus semantics

- **Rule.** One accent hue for "you can act here": focus, keys, the selection bar, the call to action. Semantic
  hues only for states (success, info, warning, error). Everything else on the neutral ladder. Saturated cells
  cover at most ~10% of the screen. Warning and error colors **never** mark normal work: a to-do is not an alarm.
- **Why.** Color that means nothing teaches the reader to ignore color. Five yellow `▲ needs approval` rows read
  as five problems, when they are five tasks.
- **Example.** [lazygit] colors only the focused border. [gh-dash] colors only check results and diff counts.
  [k9s] colors whole rows by pod state. [btop] gives each box border a low-saturation hue and keeps saturated
  color for data. Showcase: a request waiting for approval is `◇` in the accent; healthy, degraded, failed and
  rolling stay semantic.
- **Check.** List every hue on the PNG with its meaning. A hue with two meanings fails; so does an alarm hue on
  something that is not a problem, and saturated text in a column that is not about state.

### 4. Surfaces before boxes

- **Rule.** Group with whitespace, section rules (`Waiting  4 ─────`) and background surfaces (`bg.surface`,
  `bg.raised`). Draw boxes only around panes that take focus independently. Never draw a box inside a host's
  frame; share borders between neighbors.
- **Why.** Boxes cost 2 rows and 2 columns each, and nested frames read as bureaucracy. An app box inside a host
  popup's frame makes a double frame and can push chrome past 30%.
- **Example.** [helix] draws its documentation popup as a darker surface with no border. [gh-dash] puts its
  preview header on a surface block. [harlequin] and [posting] put the panel title inside the border. Deploy
  console C: the selected card's surface continues into the detail surface, so "this request, its evidence" reads
  as one shape; no box anywhere in the three concepts.
- **Fallback.** At 16 colors every `bg.*` token falls back to the terminal default, so surfaces vanish. Give each
  surface a structural backup that survives: a title line, a section rule, an underline (on inputs), indentation.
- **Check.** No box inside a host frame, nesting at most 1, `ansi_grid.py --clutter` chrome ≤ 20% as the craft
  target. Render at 16 colors and confirm the groups still read.

### 5. Selection that survives 16 colors

- **Rule.** In truecolor or 256 colors: a band (`selection.bg`) and the label in bold, optionally an accent bar `▌`
  in the first cell. In 16 colors `selection.bg` becomes **reverse video**, and every colored cell on the row
  turns into a colored block. Two fixes:
  - **Neutralize the row.** Draw the selected row's glyphs and meta in `selection.fg`, so reverse gives one even
    band; the glyph's shape still carries the state. Showcase A and B.
  - **Select with a surface.** Surface plus accent bar plus bold; at 16 colors it degrades to bar plus bold.
    Showcase C.
- **Why.** At the caps depth a selected row with `▲` and `✓` in their hues renders as a yellow and a green block,
  faithfully to curses; it is the most common reason a correct frame "looks poor".
- **Watch.** In a `.mock`, blank cells after a run take that run's fg. An accent `▌` followed by spaces on a band
  shows as an accent block in reverse video: on bands, drop the bar or start content in the next cell.
- **Example.** [yazi] and [lazygit] use one full band with uniform text. [soft-serve] uses no band: a left bar `│`
  and the item in the accent. [gum] uses `>` plus the accent.
- **Check.** Render with `--depth 16` and read the selected row: one even band, or a bar plus bold, and no colored
  blocks.

### 6. Data in cells

- **Rule.** Show quantities as meters, sparklines or braille plots, with the number printed next to them. Draw
  stacked horizontal meters with a glyph that leaves a gap between rows (`▆` lower 3/4 block, `■` squares, `━`),
  not `█`: full blocks in adjacent rows merge into one blob. One hue per series, the same in the legend and the
  plot. At 16 colors, switch the shape rather than lose the data.
- **Why.** `█` meters on consecutive rows fuse into staircase shapes (per-core CPU bars, memory boxes, share
  columns); with `▆` or `■` every row reads alone, as in the reference `sysmon` and `diskusage` mockups.
- **Example.** [btop] draws discrete `■` meters with a gradient ramp and braille graphs, and its tty mode swaps
  braille for colored blocks. [gping] and [dolphie] color each series with the same hue in the header and plot.
  Showcase B: an error-rate sparkline per service with the percentage printed, in the warning hue only on the
  degraded service.
- **Check.** Bars in adjacent rows stay separate on the PNG, the value is printed, and legend hues match the plot.

### 7. State at a glance

- **Rule.** Summarize before the rows: counts as glyph plus number (bold number, muted noun), a progress meter
  when there is a backlog, a chip for an exceptional state (`STALE 42s`, `200 OK`, `TAIL`), and freshness
  (`updated 12s ago`).
- **Why.** The first question is "how many, how bad, how far along". A table makes the reader count.
- **Example.** [gh-dash] puts counts in its tabs and freshness in the footer. [posting] shows a `200 OK` chip.
  [toolong] has a `TAIL` chip. [k9s] puts cluster, user and CPU in its header. Showcase header:
  `● 2 rolling  ◇ 4 to approve  ✗ 1 failed · updated 12s ago`.
- **Check.** Cover everything below the header. Can the reader still answer how many, how bad and how far along?

### 8. Signature element

- **Rule.** Give the screen one element that makes the screenshot identifiable and that is about the job.
- **Why.** A frame that could belong to any app is forgotten; memorable is part of ambitious.
- **Example.** [btop]: braille graphs plus gradient meters. [yazi]: the preview column. [lazygit]: stacked,
  numbered side panels. [posting]: the URL bar with its `Send` button. [soft-serve] and [glow]: a status bar of
  colored chips. [k9s]: the header with its ASCII logo. Showcase: rollout meters pinned over the timeline (A), the
  staging/prod strip of one glyph per service (B), the card joined to its evidence with approval pips `●○` (C).
- **Check.** Name the screen in one noun phrase that no other app shares.

### 9. Header and footer craft

- **Header.** Left: identity (app name in accent bold) and context (muted). Right: the state summary
  (principle 7). One row.
- **Footer.** Key hints: key in `keyhint.key` bold, verb muted, context keys left, global keys right. One row. No
  brackets (`[ Apply: F2 ]`), no `Key: verb` colons, never every hint in the accent. The Charm chip bar is an
  alternative ([soft-serve], [glow]).
- **Why.** These two rows appear in every frame. Separate `Search:` and `Filter:` rows plus a two-row footer spend
  4 rows on chrome; an all-accent footer reads as a rainbow.
- **Example.** [lazydocker]: blue keys in the footer, the right edge used. [posting]: `^c Quit ^j Send` with an
  accent key and a plain verb. [gitui] boxes each hint as `Scroll [↑↓]`, heavier than needed.
- **Check.** At most 1 header row and 1 footer row, keys distinguishable from verbs, no bracket noise.

### 10. Density matched to the count

- **Rule.** Choose density from the expected item count against the rows available; aim for items ×
  rows-per-item at 60–90% of the region.
  - **Compact:** 1 row per item, no gaps. Logs, process tables, more than ~30 items ([k9s], [btop] proc).
  - **Cozy:** 1 row per item plus gaps between sections. 10–30 items.
  - **Comfortable:** 2–3 rows per item with a meta line. Fewer than ~15 items ([gh-dash], [soft-serve],
    [circumflex]).
- **Why.** A compact table of 11 rows in a 27-row body leaves a dead band; comfortable cards for 4 items fill the
  same body with useful context.
- **Example.** Showcase C: 4 waiting requests as 3-row cards, the 5 decided ones as a compact roster below. Showcase
  B: 7 services at 2 rows each at 120x30, 1 row each at 80x24.
- **Check.** Compute the fill ratio for the expected count, and for the count in the frame.

### 11. Typography with bold and dim only

- **Rule.** A terminal has one font size. Hierarchy comes from bold, the fg ladder, dim, underline (inputs, the
  active tab) and reverse (small chips only).
  - Bold at most once per line group: titles, the selected label, the numbers in a summary.
  - Numbers right-aligned, units dim after the value.
  - Truncate paths at the start and titles at the end. Never truncate the useful column while a less useful one
    wastes width (a task title cut short next to a column of repeated long paths).
  - No `Label:` prefixes when position already says what a value is. No brackets around tabs (`[ Services ]`):
    mark the active tab with accent and bold, or an underline ([soft-serve], [posting], [harlequin]).
  - No slash-joined detail lines (`payments / prod / v1.9.2 / degraded`): use aligned key–value rows or a
    breadcrumb `›`.
- **Check.** Every column is aligned to one grid, and every bold run has a reason.

### 12. Glyph accents within the caps

- **Rule.** One glyph per meaning, used everywhere: in the deploy console `◇` waiting for a human, `●` rolling, `✓`
  healthy, `▲` degraded, `✗` failed. Section rules use `─` in `border.default`, breadcrumbs `›`, tree guides `└─`,
  meters `▆`, `■` or `━`. Stay inside the `#! caps:` glyph level. Nerd Font icons are a signature in [yazi] and
  [superfile], but only with `glyphs=nerd`.
- **Check.** `render_mockup.py --glyphs` lists every non-ASCII glyph; each maps to exactly one meaning.

### 13. Depth honesty

- **Rule.** Design for the verified host depth, then look at the 256-color and 16-color renders. In 256 colors
  theme backgrounds are quantized: [harlequin]'s Nord background turns teal, and Catppuccin's base turns neutral
  grey in this skill's renders. In 16 colors fills vanish and `selection.bg` becomes reverse video.
- **Check.** Two PNGs per key frame (`render_mockup.py --depth 256` and `--depth 16`), and both pass the rubric.

## Aesthetic rubric

Score each key frame, at each depth, 0–2 on every criterion, from the rendered PNG (never the `.mock` text).
**Pass bar: 12/16 or more, and no criterion at 0.** In the craft pass (branch A, step 6), fix every criterion
below 2 that a cheap change can lift, and fix every 0 before showing the frames.

| # | Criterion | 0 | 1 | 2 |
|---|---|---|---|---|
| C1 | Composition (P1, P10) | a dead band of ≥ 1/3 of the body, or huge gutters between columns | one minor band, or a list viewport with room that nothing else could use | every region earns its area; empty space is only gutters, group gaps or anchored |
| C2 | Hierarchy (P2) | everything the same weight, or the wrong thing brightest | layers present but muddy | 4 layers clear; the squint test leaves the job's objects |
| C3 | Color budget (P3) | an alarm color on normal work, or a hue with two meanings | one stray saturated element | one accent plus semantics, ≤ ~10% saturated |
| C4 | Structure economy (P4, P9) | a double frame, a box inside the host frame, or chrome > 30% | boxes where a surface or rule would do; an extra chrome row; groups that need a surface to read | grouping by space, rules and surfaces; titles in borders; 1 header row, 1 footer row |
| C5 | Selection and focus (P5) | colored blocks under reverse at 16 colors, or selection unclear | clear in one depth only | unmistakable at both depths; focus visible |
| C6 | State at a glance (P6, P7) | only rows; the reader must count | a count in plain text | counts, meters or chips answer how many, how bad and how far; meters do not blob |
| C7 | Typography and rhythm (P11, P12) | bracket noise, `Label:` lines, misaligned columns | minor alignment or truncation slips | one grid, right-aligned numbers, purposeful bold and dim, consistent glyphs |
| C8 | Signature (P8) | generic: could be any app | a nice detail that is not tied to the job | one identifiable element that expresses the job |

**Calibration.** Scores read off the PNGs; use them to anchor your own.

| Frame | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | Total |
|---|---|---|---|---|---|---|---|---|---|
| [btop] normal | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 16 |
| [posting] | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 16 |
| [lazygit] (commit demo) | 2 | 2 | 2 | 1 | 2 | 1 | 2 | 2 | 14 |
| [k9s] pods (README) | 1 | 2 | 2 | 2 | 2 | 2 | 1 | 2 | 14 |
| [gitui] diff (README) | 0 | 1 | 2 | 1 | 2 | 1 | 1 | 1 | 9 (fails on C1) |
| table-only redesign: half-empty body, yellow `▲` on to-dos, colored blocks on the selected row at 16 colors | 0 | 1 | 0 | 2 | 0 | 1 | 1 | 0 | 5 |
| boxed redesign inside a host frame: double frame, 4 chrome rows, all-accent footer, bracket tabs | 1 | 0 | 1 | 0 | 1 | 1 | 0 | 0 | 4 |
| deploy console C (approvals), 120×30, 256 / 16 | 2 | 2 | 2 | 2 / 1 | 2 | 2 | 2 | 2 | 16 / 15 |
| deploy console B (board), 120×30, 256 / 16 | 1 | 2 | 2 | 2 / 1 | 2 | 2 | 2 | 2 | 15 / 14 |
| deploy console A (feed), 120×30, 256 and 16 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 1 | 15 |
| ref `sysmon--normal--120x30` | 2 | 2 | 2 | 2 | 2 | 2 | 1 | 2 | 15 |
| ref `diskusage--normal--120x30` | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 1 | 15 |

The reference mockups in `assets/mockups/` score 12–15; the lowest are the `pods--*` table frames (12–13: a list
viewport with room, and no state summary above the table). A frame that sums to 12 with a 0 still fails.

## README test

**Would this screenshot sit next to [lazygit] or [btop] in a README without embarrassment?**

Put the PNG at README width (~1000 px) next to one exemplar of the same archetype from the corpus, and list every
difference you see. Each pattern below fails the test on its own:

| Failure pattern | Seen as | Fix (principle) |
|---|---|---|
| Half-empty screen | rows 15–25 blank under an 11-row table; the detail 25 rows below the selection | size to the data; give the rest to the detail or a roster (P1, P10) |
| Table-only | one uniform table, no summary, no signature | reframe (§Ambition); summary first (P7); signature (P8) |
| Alarm colors for to-dos | five yellow `▲ needs approval` rows | accent `◇` for to-dos; warning only for problems (P3) |
| Reverse-video blocks | `▲` and `✓` turned into colored blocks on the selected row at 16 colors | neutralize the row, or select with surface + bar + bold (P5) |
| Double frame | the app's box inside a host popup's frame | draw no outer box inside a host (P4) |
| Bracket and label noise | `[ Services ]`, `Filter: [ All ]`, `Search: /`, `payments / prod / v1.9.2 / degraded`, `[ Apply: F2 ]` | accent + bold or underline for active; aligned key–value; footer keys (P9, P11) |
| Placeholder repeated at full weight | `(none)` ×6 as bright as the real values | a glyph plus a dim or accent word, once per row (P2) |
| Gaps that split a row | ~25 empty cells between two columns | flex one column; keep the others tight (P1, P11) |
| Wrong truncation | the title cut to `fix currency rou…` while a path column repeats long paths | truncate the less useful column, and paths at the start (P11) |
| Footer as a rainbow | every hint in the accent across 2 rows | key bold accent, verb muted, 1 row (P9) |

Pass = none of these patterns, plus the rubric bar, at both depths. `render_mockup.py FILE --check` reports the
countable ones as `craft CR1`–`CR7` warnings ([formats.md](formats.md)); the rest (alarm colors, reverse-video
blocks, hierarchy) need your eyes on the PNG.

## Exemplar corpus

README, docs and demo images of well-regarded TUIs (GIF stills are mid-animation). The observation per image is
in the principles above. The `lazygit-hero`, `lazydocker-hero` and `k9s-xray` URLs in `exemplars.md` are logos,
not screenshots; use these.

| ID | Image | Shows |
|---|---|---|
| [btop] | `raw.githubusercontent.com/aristocratos/btop/main/Img/normal.png` (also `tty.png`, `alt.png`) | four boxes, braille + `■` meters; 16-color tty variant |
| [lazygit] | `raw.githubusercontent.com/jesseduffield/lazygit/assets/demo/commit_and_push-compressed.gif` | stacked titled panels, commit popup with counter |
| [lazydocker] | `raw.githubusercontent.com/jesseduffield/lazydocker/master/docs/resources/demo3.gif` | status words, focused panel, footer |
| [gitui] | `raw.githubusercontent.com/gitui-org/gitui/master/assets/screenshots/s00-diff.png` | tabs, diff; empty panes; bracket key chips |
| [k9s] | `raw.githubusercontent.com/derailed/k9s/master/assets/screen_po.png` | dense header, title in border, state-colored rows |
| [yazi] | `raw.githubusercontent.com/yazi-rs/yazi-rs.github.io/main/static/images/full-border.png` | 1:4:3 columns, image preview, chip status line |
| [helix] | `raw.githubusercontent.com/helix-editor/helix/master/screenshot.png` | borderless doc popup on a surface |
| [posting] | `github.com/user-attachments/assets/78359ab0-5e0c-4c0b-a60b-dce06b11bbf5` | URL bar, surfaces, `200 OK` chip, footer keys |
| [superfile] | `raw.githubusercontent.com/yorukot/superfile/main/website/src/assets/demo.png` | full-screen panels, gradient progress |
| [harlequin] | `raw.githubusercontent.com/tconbeer/harlequin-web/main/src/lib/assets/docs/nord.png` (and `nord-256.png`) | Textual panels; the 256-color quantization shift |
| [dolphie] | `github.com/user-attachments/assets/b23426ad-060e-4a3a-bb10-66cf0ac95bd0` | stat panels, values vs units, metric graph |
| [soft-serve] | `stuff.charm.sh/soft-serve/soft-serve-demo-commit.png` | margins, 2-line items, bar selection, chip status bar |
| [glow] | README GIF of `charmbracelet/glow` | reading column, chip status bar |
| [gh-dash] | `raw.githubusercontent.com/dlvhdr/gh-dash/main/docs/src/assets/overview.gif` | counts in tabs, 2-line rows, surface preview header |
| [atuin] | `raw.githubusercontent.com/atuinsh/atuin/main/demo.gif` | inline bottom-up list, numbered quick-select |
| [circumflex] | `raw.githubusercontent.com/bensadeh/circumflex/main/screenshots/main-view.png` | comfortable 2-line items, empty-state message |
| [toolong] | README GIF of `Textualize/toolong` | line numbers, `TAIL` chip, key chips |
| [bottom] | `raw.githubusercontent.com/ClementTsang/bottom/main/demos/demo.gif` | braille CPU plot, legend hues |
| [gping] | `raw.githubusercontent.com/orf/gping/master/images/readme-example.gif` | series hues shared by header and plot |
| [gum] | `vhs.charm.sh/vhs-1qY57RrQlXCuydsEgDp68G.gif` | minimal choose: `>` + accent |
| [textual] | README of `Textualize/textual` | devtools console colors |
