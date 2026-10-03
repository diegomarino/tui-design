# Audit quick review: the §0 core

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [0. Quick-review core (screenshots, mocks, your own frames)](#0-quick-review-core-screenshots-mocks-your-own-frames) · L9–72 — every quick review or self-review: frame of reference, tools, §0.1 clutter audit and floor test, §0.2 core items, §0.3 mock-review checks (MR).
- [Order findings by user harm](#order-findings-by-user-harm) · L74–99 — writing the answer or report: harm tiers and the recommendation-first rule.

Read this when you review a TUI quickly: a screenshot, someone's mock, or your own `.mock` frames (SKILL.md C0, and the self-review of design step A8). It holds §0 of the audit checklist and the order to report findings in. Check ids (LH-14, TC-10, RS-08…) are defined in the full list, [audit-checklist.md](audit-checklist.md); open the one section of it you need only when an id's rule is unclear. A full audit of a validated description uses that full list with [audit-protocol.md](audit-protocol.md) §7.

## 0. Quick-review core (screenshots, mocks, your own frames)

Use §0 whenever the evidence is an image or a `.mock`, and there is no capture and no description: a quick review of a screenshot (SKILL.md C0), a review of someone's mock, or the self-review of your own frames (design step A8). It is **required and self-sufficient**: every item of §0.1 and §0.2 ends as `pass`, `fail` or `n/a`, and each item says what to look at, when it fails, and how to verify it by eye or with a script. Checks that need behaviour (key presses, resize, terminal restore) or a running app are `n/a` here: every ID not named in §0.

- **Before judging, fix the frame of reference.** The **product shape** (full-screen session · inline picker · one-shot CLI · plugin inside a host, [layout-archetypes.md](layout-archetypes.md#product-shapes)) and, for a host or an unknown stack, its **capability profile** (attributes, colour depth, glyph level, widgets, reserved keys; the `#! caps:` line of [formats.md](formats.md#capability-profile)). Ask when unknown. Every recommendation names what it requires ("needs italic", "needs a text-input widget", "needs a second pane") so the user can drop what the host cannot do (TC-10).
- **Evidence.** Mock: `file:row:col` (`sysmon--normal--80x24.mock:23:61`) or a `#! region` id. Screenshot: the quoted text plus where it is (`row ~7 from the top, right panel`). Looking at the image is the evidence in §0, unlike the full audit ([How to use](audit-checklist.md#how-to-use): never eyeball). By eye you may judge layout, text, glyphs, alignment, visible row counts and repetition. You may **not** judge exact colours, contrast ratios, which grey token a span uses, or behaviour: those items are `n/a` with what would settle them (`sample_colors.py`, `contrast_check.py`, a live capture).
- **Output.** Recommendation first, then the failures in the order of "Order findings by user harm", then what to keep (items that pass and matter), then open questions. Offer a mock redesign (branch A) when the failures are structural.

Tools: `lint` = `python3 SKILL_DIR/scripts/render_mockup.py FILE --check` (also enforces the `#! caps:` line); `glyphs` = `python3 SKILL_DIR/scripts/render_mockup.py --glyphs FILE…` (every non-ASCII glyph with width class, emoji/PUA flag, lint tier and ASCII fallback); `PNG` = render and Read it (`python3 SKILL_DIR/scripts/render_mockup.py FILE --theme ID -o f.ansi`, then `uv run SKILL_DIR/scripts/ansi_render.py f.ansi --theme ID --format png -o f.png`); `plain` = the same with `--depth none` (no colour and no attributes: stricter than NO_COLOR); `cc` = `python3 SKILL_DIR/scripts/contrast_check.py ID` and `--depth 16`; `clutter` = `python3 SKILL_DIR/scripts/ansi_grid.py FILE --clutter` on a `.mock` (rendered for you) or a live capture `.ansi` (prints the §0.1 counts, each with a verdict).

### 0.1 Review reflexes (apply unprompted, in every review)

Run both even when the user only asked "how would you improve it?". They are the two items reviewers skip when nobody asks.

**Clutter audit: count, do not feel** (LH-14, LH-12, LH-06). For each content region, record the counts below and name every element to remove, merge or move, with its location: `rows 7–14 "Source error …" → one row "Source error ×8"`, `drop the [X] before ◌`, `ENV column (all "prod") → header`.

| Count | What to look at (by eye) | Fails when |
|---|---|---|
| Border nesting | boxes around a content cell, counted from the screen edge inwards | more than 1 box around any content cell (a panel box inside a screen frame, a box inside a panel); `clutter` "border nesting" > 1 |
| Signals per fact | for one fact (a status, a type, an error), every glyph, word, tag and region that states it | more than one glyph, tag or word for it on a row (`[X] ◌ error`, `Source Source`; `clutter` "duplicate signals"), or the same fact or note in two regions. One glyph + one word + one colour for a status is **one** encoding (CT-11), not three |
| Every-row markers | a glyph, tag or word drawn on every row of a list with the same value | the same marker on ≥ 90% of a region's rows (≥ 3 rows): it marks nothing (`clutter` "repeated markers"; the selection cursor and a status column whose values differ are exempt) |
| Chrome share | cells of borders, separators and rules vs all inked cells; by eye also labels, headings and repeated boilerplate | border/separator/rule cells > 25% of the non-space cells (`clutter` "chrome share"); name the labels and boilerplate that could go too |
| Near-constant fields | a column or per-row field whose value barely varies | the same value on ≥ 90% of rows, or only 2 values with no meaning to the main job: move it to the title or header and show only the exceptions |
| Repeated rows | consecutive rows identical after the id column | ≥ 4 such rows not folded to one row with `×N` or a `+ N more` line (LH-06) |

On a screenshot, count by eye and quote the rows.

**Floor test: 80×24 and a 60-column split** (RS-08, with RS-01…RS-04). Answer five questions for 80×24 and for a 60-column tmux split (60x24): **which pane wins** (the primary region stays whole), **what hides first**, **what truncates** (ids and status survive, DA-04), the **single-pane fallback** (e.g. list only, Enter opens the detail full-screen), and the **too-small message** below the minimum (current vs needed size, quit key). Fails when an answer is undefined (no frame and no written rule in design-system §8), a primary region is lost, or anything clips silently. Mock: compare the 80x24 frame with a 60x24 frame or the `toosmall` frame. Screenshot of a wider screen: `n/a` for the app's real behaviour, but always state the predicted floor from the visible fixed widths (sum of fixed panes and columns vs 80 and 60) and recommend the rule as an open decision.

### 0.2 Core items

| Item | Checks | Look at → fails when | By eye (screenshot or mock) | Script (mock or capture) |
|---|---|---|---|---|
| Frames present (mocks) | MR-01 | the design dir → MR-01 fails (§0.3) | list the files against the formats table | `ls DIR`; screenshot: `n/a` |
| Sketches are frames | MR-02 | every box drawing or aligned text table you show the user, inline ones included → MR-02 fails (§0.3) | count the columns of each row of the sketch | `lint` on the `.mock`; `mockkit.py` frames |
| Capability profile | TC-10 | attributes, colour depth, glyph level and widgets used vs the host profile → italic/strike/underline, 256/truecolor, Nerd Font glyphs or a widget outside the profile; a recommendation that does not name its requirement | read the attributes in the image (italic slant, underline) and the widget kinds | `lint` with the `#! caps:` line; `glyphs` for the glyph level |
| Lint and glyph widths | GW-01, GW-02, GW-03, GW-08, DA-02 | glyphs and row widths → wide or emoji glyphs, text over borders, over-width rows, WARN glyphs kept, mixed ellipses | ragged right borders, a shifted column after an icon, `…` and `...` both present | `lint` (`--strict-ambiguous` when CJK locales are targeted); `glyphs` |
| Layout and hierarchy | LH-01, LH-02, LH-03, LH-05…LH-09, LH-11, GW-07 | region order and chrome → the main answer is not first, chrome off the edge rows, an untitled bordered panel, the emphasis budget blown, faint primary text on warning/error rows, a blank screen, mixed border sets | the screen top-down: what you read first, where the bars sit | `#! region` lines + `PNG` |
| Clutter (§0.1) | LH-06, LH-12, LH-14 | the counts of §0.1 → any threshold crossed | count by eye | `clutter` |
| Counts | LH-04 | titles with `(N)` → N ≠ the rows drawn and no scroll cue (`1 of N`, `N more`) | count the rows | count rows in the mock body |
| Alignment | DA-01, DA-03…DA-08 | sibling rows → the same field starts at different columns, truncation without `…`, no padding inside borders, the cursor pushes the selected row's text | follow each column down the rows | mock body columns |
| Floor and sizes (§0.1) | RS-01, RS-03, RS-04, RS-08, DA-09 | the size frames → 80x24 loses a primary region, secondary regions do not shrink first, the keybar wraps, no 60-column answer, 170x40 wastes the width | §0.1 floor test | compare the 80x24, 60x24, 120x30 (and 170x40) frames |
| Too small | RS-02 | the `toosmall` frame → below the minimum, it does not say current vs needed size in words plus the quit key ([layout-archetypes.md §2.2](layout-archetypes.md#22-the-too-small-screen)) | read the frame | `PNG` of the `toosmall` frame |
| Focus and selection | FS-01, FS-09, FS-02, FS-03, FS-05, FS-06, FS-07 | focus and cursor cues → not exactly one focused region, unfocused borders as strong as `border.focus` (FS-09), focus or selection only by hue, two apparent cursors | find the focused pane and the cursor; squint test: is one border clearly stronger | `#! focus` / `#! selected` lines, `PNG`, `plain`, FS-09 ratios |
| Footer grammar | ID-01, ID-03, ID-04, ID-10, ID-11 | footer rows → mixed hint grammars, global keys (`? help`, `q quit`) not on the right or in the middle of context keys, a modal without its own hints, unlabelled number keys | read every footer | footer rows of every frame |
| States | ST-01…ST-05, ST-07, ST-08, ST-09 | empty/busy/error frames → what [layout-archetypes.md §2.3](layout-archetypes.md#23-states-every-archetype-must-design) requires is missing (why empty + the key; spinner + verb; what failed + retry key); region boxes move between state frames of one size | state frames side by side | `#! region` lines diffed |
| Status semantics | ST-10, CT-11, CT-03 | every status marker, word and colour vs the result it labels → a success tag or colour on a FAIL/BLOCK/error result (`[OK] review FAIL`), a status shown as a plain word with no glyph and no status colour, two states told apart by hue only | read each status cell together with its payload text | `{token}` tags in the mock; `glyphs` |
| Consistent emphasis | CT-12 | one role (a column, a tag like `Editable`, a status word) across rows, the selected row included → styled on some rows and plain on others with no reason | compare the selected row with its neighbours | `{token}` tags per row |
| UI text is product text | LH-13 | every string inside the frame → design notes or meta-commentary in UI text (`DESIGN SAMPLE`, `illustrative`, `not visible in the screenshot`) | read all text | grep the mock body; notes belong in `#! note:` or the design doc |
| Kept affordances (redesigns) | MR-03 | the current UI (screenshot or code) vs the redesign → MR-03 fails (§0.3) | list the current UI's affordances first, then tick each in the redesign | diff the old and new frames; zebra rules: [layout-archetypes.md §2.4](layout-archetypes.md#24-zebra-striping-tables-logs-long-lists) |
| Colour tokens | CT-01…CT-06 | the `{token}` tags → several tokens for one meaning, `status.*` on non-status content, > 2 decorative hues, selection/focus in status hues, `fg.faint` on primary text | screenshot: hues only, never token names (`n/a` for token identity) | the `{token}` tags in the mock |
| Contrast | CA-01…CA-09, CA-12 | the floors of [formats.md](formats.md#contrast-floors) in both depths, the advisory selection-row rows (CA-06), dim text, error vs success beyond hue, light theme for 16-colour designs, charts with numbers → any floor missed | never by eye: `n/a` on a screenshot unless sampled (`sample_colors.py` + `ratio`); CA-08 and CA-12 can be judged by eye (glyph/word difference, printed numbers) | `cc` (advisory rows never change its exit code) |
| No colour | CT-03, CT-07, FS-02 | the frame without colour → selection, focus or status distinctions vanish | imagine the screen in grey: does a glyph, word, bold or reverse remain | `plain`; if it fails only because attributes are gone, check that the mock carries bold/reverse/glyph cues (NO_COLOR keeps attributes) |
| Shell contract (pickers, one-shot CLIs, scripted modes) | SH-02, SH-03, SH-04, SH-10, SH-14 | the receipt frame, the design brief and the footer → no stated exit code for chosen / nothing / cancelled (Esc and Ctrl-C = 130), chrome or the receipt on stdout, no cd-on-exit wrapper for a directory picker, a footer that offers `q` in a query field | read the brief and the receipt frame | `n/a` on a mock; on a running app the SH Verify commands ([cli-contract.md](cli-contract.md) §8) |

### 0.3 Mock-review checks (MR)

These exist only in §0: they judge the design work, not a running app.

| ID | Rule → fail when | Sev | Kind | Verify |
|---|---|---|---|---|
| MR-01 | Every required frame exists. Fail when a required state × size of [formats.md](formats.md#frame-naming) is missing, an overlay has no frame, or the main screen has no `toosmall` frame. | M | style | the design dir vs the formats table |
| MR-02 | Any sketch shown to the user is a linted frame of a declared size. Fail when a box drawing or aligned text table shown to the user was not built with `mockkit.py` or linted with `render_mockup.py --check`, has no declared `#! size:`, has rows of different widths or panels whose right edges differ, or claims a size it is not (`~140 cols` drawn at 92). | M | bug | `lint`; count row widths |
| MR-03 | A redesign keeps what already works. Fail when an affordance of the current UI (zebra striping, a column, sort order, a filter, a key, a count, a freshness cue) is absent from the redesign and its removal is not listed with a reason in the design doc. M when an action, key or piece of information is lost; m for a visual aid (striping). | M/m | style | inventory of the current UI vs the new frames |

## Order findings by user harm

Write each finding as one line: `- **<change>** — <evidence>. Needs: <capability, or "nothing new">`. The `Needs:` field is mandatory: it lets the user drop what their host cannot do.

Example, a quick review of a backup-job list:

```markdown
- **Mark the selected row with `❯` and a reverse band** — rows 3–14 differ only by an italic name, and this pane drops italic. Needs: reverse video
- **Show the selected job's log beside the list at 120 columns** — `enter` replaces the whole screen, so the list position is lost. Needs: a second pane
- **Fold the 8 "retry failed" rows into one "retry failed ×8"** — rows 7–14 are identical and push the queue off screen. Needs: nothing new
```

Report findings in this order, in quick reviews and full reports alike. Blockers (B) come first whatever their tier; inside a tier, M before m. A check not listed goes to the tier of the harm it causes.

| # | Tier | Typical checks |
|---|---|---|
| 1 | **Product shape**: the wrong kind of program, or a design the host cannot draw | TC-06, TC-10; [layout-archetypes.md](layout-archetypes.md#product-shapes) |
| 2 | **Lifecycle and cleanup**: the terminal left broken, the app cannot be left | TC-01, TC-08, TC-07, ID-13, SH-06, SH-08, SH-15; [lifecycle.md](lifecycle.md) |
| 3 | **Blocking, redraw and width**: frozen input, flicker, corrupt or wrapped rows | FR-*, DA-02, RS-05, RS-06, GW-01, GW-06, TC-05 |
| 4 | **Discoverability and truth**: the user cannot find the action, the focus, or the real state | ID-01…ID-12, FS-*, ST-01…ST-10, LH-01, LH-04, LH-13, CT-03 |
| 5 | **Clutter**: the answer drowns in chrome and repetition | LH-05…LH-07, LH-12, LH-14, CT-04, CT-11, CT-12, DA-* |
| 6 | **Floor**: 80×24, the 60-column split, too-small | RS-01…RS-04, RS-07, RS-08 |
| 7 | **Streams, NO_COLOR and plain mode**: pipes, exit codes, colour depth, contrast, screen readers | SH-01…SH-05, SH-07, SH-09…SH-14, TC-02, TC-03, TC-04, TC-09, CT-07…CT-10, CA-*, GW-05 |
| 8 | **Tests**: golden frames at pinned sizes (80×24, 60 cols, the minimum), state unit tests, one or two PTY end-to-end runs | (recommendations, no check id) |

**Make the recommendation before explaining it.** Each finding opens with the change to make, in the imperative, then its evidence (check id + quote) and why it matters, then what it requires: `Fold the 8 "Source error" rows into one "Source error ×8" (LH-06: rows 7–14 identical; needs nothing).` Redesign-process checks (MR-02, MR-03) go with the tier of what they would break.
