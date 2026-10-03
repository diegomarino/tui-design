# Audit checklist: the judge's rubric

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [How to use](#how-to-use) · L19–30 — before a full audit: statuses, severity, kind, notation of the Verify column.
- [1. Layout & hierarchy (LH)](#1-layout--hierarchy-lh) · L32–49 — region order, emphasis, clutter budget (LH-*).
- [2. Density & alignment (DA)](#2-density--alignment-da) · L51–63 — columns, truncation, padding, wide screens (DA-*).
- [3. Responsive & minimum size (RS)](#3-responsive--minimum-size-rs) · L65–76 — 80×24, the 60-column split, too-small screens, resize (RS-*).
- [4. Focus & selection (FS)](#4-focus--selection-fs) · L78–92 — one focus, cursor and selection cues, FS-09 border ratios (FS-*).
- [5. Interaction & discoverability (ID)](#5-interaction--discoverability-id) · L94–110 — footer grammar, help, keys, quit paths (ID-*).
- [6. Feedback & states (ST)](#6-feedback--states-st) · L112–125 — empty, busy, error and status semantics (ST-*).
- [7. Color & tokens (CT)](#7-color--tokens-ct) · L127–142 — token use, colour budget, NO_COLOR (CT-*).
- [8. Contrast & accessibility (CA)](#8-contrast--accessibility-ca) · L144–159 — contrast floors, CVD, dim text, charts (CA-*).
- [9. Glyphs & width (GW)](#9-glyphs--width-gw) · L161–172 — wide and ambiguous glyphs, border sets, ellipses (GW-*).
- [10. Terminal compatibility (TC)](#10-terminal-compatibility-tc) · L174–209 — cleanup, colour depth, capability profile; §10.1 shell contract SH-* (TC-*, SH-*).
- [11. Framework-specific rendering bugs (FR)](#11-framework-specific-rendering-bugs-fr) · L211–231 — flicker, blocking, redraw and width bugs per framework (FR-*).

The full check list for judging a validated `tui-description` in a full audit ([audit-protocol.md](audit-protocol.md) §7). A quick review of a screenshot or a mock needs only [audit-quick.md](audit-quick.md) (§0 and the MR checks); a full audit applies §1–§11 here. Each check has a pass/fail criterion you can test against description fields or a script. Write findings in the order of ["Order findings by user harm"](audit-quick.md#order-findings-by-user-harm); the report uses [templates/audit-report.md](templates/audit-report.md).

## How to use

- **Statuses:** every check ends as exactly one of `pass` | `fail` | `n/a` | `unverifiable`. `n/a` = the screen has no such element, or the check needs evidence this audit cannot produce (behaviour on a screenshot, token checks with no theme fit); give the reason. `unverifiable` = the description lacks the fact: it triggers **one** targeted re-description ([audit-protocol.md](audit-protocol.md) §7 step 3), then the check is judged again; if still unverifiable it goes to the report's "Not verifiable" section. In a full audit, never eyeball: a fail must cite region/element ids and a quoted value (text, bbox, token, ratio). In a [§0 quick review](audit-quick.md#0-quick-review-core-screenshots-mocks-your-own-frames) there is no description, so `unverifiable` is not used: a fact the image or mock cannot settle is `n/a` with what would settle it.
- **Severity:** **B** blocker = corrupts the frame, loses data or the terminal state, makes a core task impossible, or text is effectively unreadable (< 3:1). **M** major = breaks a required contrast floor ([formats.md](formats.md#contrast-floors)), a standard size (80×24) or a core task's discoverability, or misleads about state. **m** minor = consistency and polish. A check may name two severities ("M/B"); the condition in the rule decides which applies.
- **Kind:** **bug** = the output differs from what the code meant to draw (corruption, overflow wrap, width miscount, ghost lines). Report the mechanism and "reproduce before declaring fixed". **style** = drawn as intended, but breaks a design rule.
- **Verify column notation.**
  - `R` = `regions[]`, `E` = `elements[]`, `E[key_hint]` = elements of that type, `ST` = `screen_text`, `U` = `uncertainties[]`, `M` = `meta`.
  - `cap@80x24` = a live capture at that size (`SKILL_DIR/scripts/capture_tui.sh -s 80x24 …`); `cap+k X` = capture after `-k X`; `cap env=VAR=VAL` = capture with `capture_tui.sh -e VAR=VAL`.
  - `cc` = `SKILL_DIR/scripts/contrast_check.py`; `lint` = `SKILL_DIR/scripts/render_mockup.py recon.mock --check [--strict-ambiguous]`; `ratio` = `contrast_ratio()` from `SKILL_DIR/scripts/_theme.py` on the span's `raw` fg/bg.
  - `floor` = the token's contrast floor in [formats.md](formats.md#contrast-floors), the only place the numbers live.
  - `clutter` = `python3 SKILL_DIR/scripts/ansi_grid.py FILE --clutter` (`.mock` or `.ansi`); `glyphs` = `python3 SKILL_DIR/scripts/render_mockup.py --glyphs FILE…`; `caps` = the `#! caps:` line of a mock, or the host's capability profile ([formats.md](formats.md#capability-profile)).
- **Thresholds and standards.** A numeric threshold with no cited standard is this skill's calibrated default. Standards named in rules: WCAG 2.2 success criteria (https://www.w3.org/TR/WCAG22/), UAX #11 East Asian Width (https://www.unicode.org/reports/tr11/), https://no-color.org/, https://clig.dev/.

## 1. Layout & hierarchy (LH)

| ID | Rule → fail when | Sev | Kind | Verify |
|---|---|---|---|---|
| LH-01 | The answer to the screen's main question (design brief) comes first. Fail when the region or element holding it has `order` > 1, or sits below a list taller than half the screen. | M | style | brief + `R.order`, `bbox.y` |
| LH-02 | Chrome sits at the edges: header/tabbar at y=0, keybar/footer/statusbar on the last 1–2 rows. Fail when a keybar or statusbar has `bbox.y` outside {0, 1, rows-2, rows-1}. | m | style | `R[role∈header,tabbar,keybar,footer,statusbar].bbox` |
| LH-03 | Every bordered panel that shares the screen with another panel has a title. Fail when `border.style ≠ none` and `title` is missing. | m | style | `R.border`, `R.title` |
| LH-04 | A count in a title matches what is reachable. Fail when "(N)" > the visible list_item/table_row/tree_item count and no scroll cue exists (`R.scroll`, or "N more" / "1 of N" text). If N > visible and the list has no scroll, treat it as a possible eaten row: check DA-02 and FR-01. | M | bug | title text vs `count(E[list_item] in R)` |
| LH-05 | Repeated prefixes become structure. Fail when ≥3 consecutive rows share the same leading token (e.g. `host.`, `proj.`) and no section heading groups them. | m | style | `E[list_item].text` |
| LH-06 | Identical rows are folded. Fail when ≥4 consecutive rows have identical text after the id column and there is neither a fold line ("+ N more …") nor one row with a count (`Source error ×8`). | m | style | `E.text`; `clutter` |
| LH-07 | The emphasis budget holds. Fail when bold covers > 25% of non-space body cells, or when every row of a status list has the same style (no level stands out). | m | style | `E.style.attrs`, spans over `ST` |
| LH-08 | Primary content on warning/error rows is never dim or faint. Fail when an element containing a `status.warning`/`status.error` span has its main text in `fg.faint` or with `dim`. | M | style | `E.spans[].style` |
| LH-09 | Space goes where content is. Fail when one region's interior is > 60% blank while another region's elements are `truncated`. | m | style | `ST` blank ratio per `R`, `E.truncated` |
| LH-10 | Overlays are whole and on top. Fail when a z ≥ 1 region's bbox exceeds the screen, it has no border or distinct bg, or `occludes` is empty while it covers another region. | M | bug | `R[z≥1]` |
| LH-11 | No screen is blank. Fail when a non-empty state shows < 3 inked rows, or any state lacks a status message plus a way out (a quit/back key hint). | M | style | `ST`, `E[key_hint]` |
| LH-12 | One encoding per fact. Fail when one fact (a status, a type, an error, a note) is stated twice: two glyphs or two words for it on one row (`[X] ◌ error`, `[!] ▲`), a doubled word (`Source Source`), or the same fact or note in two regions. A status's one glyph + one word + one colour is a single encoding (CT-11) and passes. | m | style | `E.text` per row, `ST`; `clutter` |
| LH-13 | UI text is product text. Fail when a frame or the app shows design notes or meta-commentary (`DESIGN SAMPLE`, `illustrative`, `Exact reason is not visible in the screenshot`). Assumptions go in `#! note:` lines or the design doc. m in a mock; M in a built app (it misleads the user). | m/M | style | `ST`, mock body |
| LH-14 | The clutter budget holds (the countable clutter audit of [§0.1](audit-quick.md#01-review-reflexes-apply-unprompted-in-every-review)). Fail when, in a content region: a content cell sits inside more than 1 box; the same marker is drawn on ≥ 90% of the rows; chrome (border, separator and rule cells) exceeds the `ansi_grid.py --clutter` threshold (calibrated on this skill's reference frames; see its `--help`); or a field has the same value on ≥ 90% of rows instead of sitting in the title or header. The finding names each element to remove, merge or move. | m | style | `clutter`; `R.border` nesting, `E.text` per column |

## 2. Density & alignment (DA)

| ID | Rule → fail when | Sev | Kind | Verify |
|---|---|---|---|---|
| DA-01 | Columns align. Fail when the same field (status word, age, id) starts at different x in sibling rows of a list or table (span `start` differs by ≥1). | M | bug | `E.spans[].start` across rows |
| DA-02 | No row is wider than the terminal. Fail when any `ST` row's display width ≠ cols, or a bordered panel's row continues at x=0 on the next row (wrap). | B | bug | `ST`, `lint` |
| DA-03 | Truncation is marked. Fail when `truncated ≠ null` and the visible text does not end (or start) with `…`/`⋯`/`...`. | m | style | `E.truncated`, `E.text` |
| DA-04 | Truncation keeps identity and status. Fail when a truncated row lost its leading id or its status word while optional prose survived. | m | style | `E.text` vs sibling rows |
| DA-05 | Trailing numeric/age columns are right-aligned. Fail when such a column's right edge differs across rows. | m | style | span `start+len` across rows |
| DA-06 | Label/value pairs use one label width per panel. Fail when values in one panel start at more than one x. | m | style | `E[label,value].bbox.x` |
| DA-07 | Content does not touch borders. Fail when the text of a bordered region starts at border x+1 with no padding, except for selection bars and scrollbars. | m | style | `ST` vs `R.bbox` |
| DA-08 | The cursor gutter is reserved. Fail when a selected row's text starts at a different x than unselected rows (the marker pushes text). | M | bug | `E[list_item].spans` selected vs not |
| DA-09 | Large terminals are used. At 170×40, fail when content regions keep their 80-col widths and > 30% of the columns stay blank. | m | style | `cap@170x40`, `ST` |

## 3. Responsive & minimum size (RS)

| ID | Rule → fail when | Sev | Kind | Verify |
|---|---|---|---|---|
| RS-01 | Standard sizes render. Fail when the 120×30 or 80×24 capture fails DA-02, or loses a primary region. | M/B | bug | `cap@120x30`, `cap@80x24` |
| RS-02 | Below the minimum, say so. At 60x18 and 40x10 (the sizes of [layout-archetypes.md §2.2](layout-archetypes.md#22-the-too-small-screen), the canonical rule), fail on silent clipping, garbage or a crash. Pass on a message that gives the current and needed size in words and still accepts quit. Mocks: the `toosmall` frame. | M | style | `cap@60x18`, `cap@40x10`, then `cap+k q` |
| RS-03 | Secondary regions collapse first. Fail when, at a narrower size, a primary region truncates while a secondary region keeps its width. | M | style | `cap@80x24` vs `@120x30` |
| RS-04 | Key hints never wrap. Fail when the keybar takes 2 rows at a narrow size. Pass when it elides with `…` or `more`. | M | bug | `cap@60x18`, `E[key_hint]` |
| RS-05 | Resize reflows cleanly. Fail when a capture after resizing 120×30→80×24→120×30 differs from a fresh launch at 120×30 (ghost lines, stale cells). | M | bug | `cmp` of two caps |
| RS-06 | The live frame fits the viewport (inline renderers). Fail when frame height > rows, which causes flicker and wiped scrollback. | B | bug | `cap@80x24` with long content |
| RS-07 | Selection survives shrink and filter. Fail when the selected item is off-screen after a resize or a filter. | M | bug | `cap+k /…`, resize caps |
| RS-08 | The floor is designed: the five answers of the floor test ([audit-quick.md §0.1](audit-quick.md#01-review-reflexes-apply-unprompted-in-every-review): which pane wins, what hides first, what truncates, the single-pane fallback, the too-small message) exist for 80×24 and for a 60-column split (60x24). Fail when one is undefined, on silent clipping, or on a lost primary region. Mocks: the 80x24 frame plus a 60x24 or `toosmall` frame, or a written rule in design-system §8. | M | style | `cap@80x24`, `cap@60x24`; mock frames |

## 4. Focus & selection (FS)

| ID | Rule → fail when | Sev | Kind | Verify |
|---|---|---|---|---|
| FS-01 | Exactly one region has focus at the top z. Fail when 0 or ≥2 regions have `state.focused = true` among those with max z. | M | style | `R.state.focused`, `R.z` |
| FS-02 | Focus is visible without hue. Fail when the focused region's `evidence` names only a colour, and the `NO_COLOR=1` capture shows no difference (attribute, glyph, border style). | M | style | `R.state.evidence`, `cap env=NO_COLOR=1` |
| FS-03 | Selection is visible without hue. Fail when the selected element's `evidence` is a bg colour only, with no marker glyph, bold or reverse. | M | style | `E.state.evidence` |
| FS-04 | Selection contrast. Fail when `selection.fg` on `selection.bg` is below its floor, or when `selection.bg` vs `bg.base` < 3.0 (WCAG non-text contrast) and FS-03 fails too. (Mocha: 1.54:1, which passes only because of the `❯` marker.) | M | style | `cc`, `ratio` |
| FS-05 | One apparent cursor. Fail when a list shows a marker on one row and a highlight on another, or two lists show active-styled selections at once. | M | bug | `E.state.selected` per `R` |
| FS-06 | An unfocused pane's selection is quieter. Fail when the selected rows of focused and unfocused panes use the same bg token. | m | style | `E.style.bg.token` vs `selection.inactive.bg` |
| FS-07 | Current tab ≠ focus ≠ selection. Fail when the active tab uses the exact style of the selected list row. | m | style | `E[tab].state.current` style |
| FS-08 | The hardware cursor is parked on focus. Fail when `M.capture.cursor.visible` is true and the cursor is not on the focused input or row. | m | style | `M.capture.cursor` |
| FS-09 | One focus indicator: unfocused borders are visibly weaker than `border.focus`. Fail when `border.default` is a saturated hue (OKLab chroma ≥ 0.07) whose contrast vs `bg.base` is ≥ 0.6 × that of `border.focus`, or when any `border.default` reaches ≥ 0.85 × it. Fix: override `border.default` with a neutral of the theme's ladder (N3–N4, e.g. the scheme's comment or gutter grey) and record it in the theme's `provenance` as `choice:`. | M | style | the command below the table; `PNG`; screenshot: border `raw` of focused vs unfocused `R` |

FS-09 numbers for a theme (prints the default/focus contrast ratio, then the OKLab chroma of `border.default`): `python3 -c "import sys,math; sys.path.insert(0,'SKILL_DIR/scripts'); import _theme as t; th=t.load_theme('ID'); b=th.hex('bg.base'); d,f=th.hex('border.default'),th.hex('border.focus'); L=t.oklab(d); print(round(t.contrast_ratio(d,b)/t.contrast_ratio(f,b),2), round(math.hypot(L[1],L[2]),3))"`. Shipped themes that fail: `tokyonight-*` (0.67–0.74, chroma 0.08–0.11), `dracula-alucard` (0.92), `kanagawa-lotus` (0.93); `catppuccin-mocha` passes (0.37, 0.03).

## 5. Interaction & discoverability (ID)

| ID | Rule → fail when | Sev | Kind | Verify |
|---|---|---|---|---|
| ID-01 | Persistent hints exist. Fail when the normal state has fewer than 3 `key_hints` on screen, or lacks one with concept `help` or `quit`. | M | style | `E[key_hint].key_hints[].concept` |
| ID-02 | Help is one key away. Fail when there is no `?`/F1 hint, or when `cap+k ?` shows no overlay listing the current context's bindings. | M | style | `cap+k ?` |
| ID-03 | One hint grammar app-wide. Fail when key_hints in one app mix forms (`[a]pprove`, `f/enter fix`, `Label: key`, `<k> Label`). | m | style | `key_raw`/`action` order across screens |
| ID-04 | Context hints left, global right. Fail when global keys (help, quit) sit between context keys, or their side changes across screens. | m | style | `key_hints[].bbox.x` |
| ID-05 | Hints only offer valid actions. Fail when sending a hinted key changes nothing and shows no message (compare frames). | M | bug | `cap+k <key>` vs before |
| ID-06 | The lingua franca holds. Fail when Enter does not open/confirm, Esc does not back/cancel, arrows do not move, or `/` (if bound) does not search/filter, or when any of these is destructive. | M | style | key_hints + caps |
| ID-07 | Esc leaves every transient state (modal, filter, menu, prompt). Fail when `cap+k Escape` still shows the overlay. | M | bug | `cap+k Escape` |
| ID-08 | Inputs own printable keys. Fail when, with an `input_field` focused, `cap+k q` quits or moves instead of typing `q`. | B | bug | `cap+k q` |
| ID-09 | Destructive actions confirm in proportion. Fail when delete/kill/discard runs on one key with no confirm and no undo, or when the confirm lacks the verb and object (`Delete pod x?`) or ignores Esc. | M | style | `cap+k d` |
| ID-10 | Number keys are labelled. Fail when digits switch panes/tabs but no `[1]`/`1 Services` label is visible. | m | style | `E[tab].text`, `R.title` |
| ID-11 | A modal steals input. Fail when a modal is open and the background still reacts to keys, or the modal shows no own hints (`[y]es · [n]o`, Esc). | M | bug | `cap+k` inside the modal |
| ID-12 | Mouse is optional. Fail when any action is reachable only by mouse. | M | style | key_hints vs clickable chrome |
| ID-13 | Reserved chords are respected. Fail when ctrl+c does not quit or cancel, or when ctrl+z or ctrl+\ is bound to another app action. Ctrl+z either suspends (implemented by the app: raw mode does not do it for you, LC3) or does nothing. | M | style | keymap, `cap+k C-c` |

## 6. Feedback & states (ST)

| ID | Rule → fail when | Sev | Kind | Verify |
|---|---|---|---|---|
| ST-01 | Loading ≠ empty ≠ error. Fail when an empty-text ("No X found") appears before the first load completes, or when two of the three states share one text. | M | style | caps across states |
| ST-02 | Empty states teach. Fail when an empty region shows nothing, or shows no hint at what will appear and which key or command fills it. | m | style | `E` in empty `R` |
| ST-03 | Errors say what, why and what next (a key or command). Fail when an error `message` lacks a next action, or shows only a raw code (`ECONNREFUSED`). | M | style | `E[message]` text |
| ST-04 | Disabled is shown with a reason, not hidden. Fail when a footnote says items are hidden, or `disabled` items carry no reason text. | m | style | `E.state.disabled`, `E.text` |
| ST-05 | Busy is labelled. Fail when a spinner has no text label, or a long operation (> 1 s) shows no busy state. | m | style | `E[spinner]`, `state.busy` |
| ST-06 | Actions report an outcome. Fail when an action changes data but no message, toast or log line states the result. | m | style | `cap+k <action>` |
| ST-07 | Freshness is honest. Fail when live data shows no age/updated time, or stale data is not labelled stale. | m | style | `E.text` |
| ST-08 | Layout is stable across states. Fail when region bboxes move between loading, loaded and empty at the same size. | m | bug | `R.bbox` diff across caps |
| ST-09 | Counts are labelled. Fail when filtered views do not say "N of M", or when counts of overlapping groups are summed. | m | style | `E.text` |
| ST-10 | Status markers agree with the payload. Fail when a status tag, glyph or colour contradicts the result it labels: `[OK]` or `✓` or `status.success` on a FAIL, BLOCK or error result (`[OK] Independent review BLOCK`), or a neutral "recorded" marker styled as success. Separate "recorded/delivered" from the verdict (PASS/FAIL/BLOCK) and give each its own column or word. | M | style | `E[status_indicator]` vs the row's text |

## 7. Color & tokens (CT)

| ID | Rule → fail when | Sev | Kind | Verify |
|---|---|---|---|---|
| CT-01 | Every colour is a token. Fail when an element colour has `token: null` with a `raw` hex that is off-palette (our own app), or when one meaning uses several tokens. | m | style | `E.style.*.token` |
| CT-02 | One token per meaning. Fail when the same status word appears in two tokens, or a `status.*` token decorates non-status content. | M | style | spans grouped by text |
| CT-03 | Colour is never the only carrier. Fail when two status states differ only in fg colour (same glyph, no word). | M | style | `E[status_indicator]` glyph/text per state |
| CT-04 | Hue budget. Fail when > 2 chromatic non-status tokens decorate (besides `accent.primary`/`accent.secondary`), e.g. rainbow borders. | m | style | distinct tokens on non-status spans |
| CT-05 | Interaction states do not borrow status hues. Fail when selection, focus or current uses `status.success`/`status.error`. | m | style | `selection.*`/`border.focus` vs `status.*` raw |
| CT-06 | Dim/faint is for secondary text only (ages, ids, hints, disabled). Fail when headings, values or the selected row text are faint. | m | style | `fg.faint`/`dim` spans by element type |
| CT-07 | It survives NO_COLOR. Fail when the `NO_COLOR=1` capture loses the selection, focus or status distinctions (no inverse, bold or glyph left). | M | style | `cap env=NO_COLOR=1` |
| CT-08 | RGB fg comes with RGB bg. Fail when an app emits a truecolor fg on the terminal's default bg for body text (the user's bg is unknown). | M | style | live capture SGR: fg `raw` with bg `term.bg` |
| CT-09 | No bright-black text. Fail when `ansi.bright_black` (ANSI 8) is used as muted text: it is invisible on Solarized Dark (`color8` = background). | M | style | `E.style.fg.token == ansi.bright_black` |
| CT-10 | Bold is not a colour. Fail when an ANSI 0–7 colour plus bold is the only emphasis; bold-as-bright terminals shift its hue. | m | style | spans: bold + ansi 0–7 |
| CT-11 | Every status carries glyph + word + colour. Fail when a status column or word is drawn as plain text with no glyph and no `status.*` colour (`idle`, `done` in `fg.default`), so states do not stand out. Exception: a table's deliberate plain "normal" state ([archetypes/i-table-explorer.md](archetypes/i-table-explorer.md): only non-normal statuses get glyph + colour). With the host's glyph level at ascii, the glyph is its V9 ASCII fallback. | m | style | `E[status_indicator]`, spans per state |
| CT-12 | One role, one emphasis across rows. Fail when the same role (a column, a tag like `Editable`, a status word) is styled on some rows and plain on others with no state difference. On the selected row the colour may give way to `selection.fg` only when the role keeps a non-colour cue (glyph, word, bold). | m | style | spans of the same column across rows, selected row included |

## 8. Contrast & accessibility (CA)

| ID | Rule → fail when | Sev | Kind | Verify |
|---|---|---|---|---|
| CA-01 | Body text (`fg.default`) meets its floor on `bg.base`. Fail below the floor (M); below 3:1, the blocker line of the severity scale (B). | M/B | style | `cc` |
| CA-02 | `fg.muted` and `fg.faint` meet their floors; `fg.faint` never carries essential text. Fail below the floor. | M | style | `cc`, CT-06 |
| CA-03 | `status.*`, `accent.primary`, `keyhint.key`, `link` meet their floors on `bg.base`. Fail below. | M | style | `cc` |
| CA-04 | `border.focus` meets its floor vs `bg.base` (non-text contrast). Fail below. | M | style | `cc` |
| CA-05 | `selection.fg` on `selection.bg`, and `fg.on-accent` on `accent.primary` and on each `status.*`, meet their floors. Fail below. | M | style | `cc` |
| CA-06 | Every drawn text span passes on its **actual** bg, not just on `bg.base`. Fail when a text span's `ratio` is below the floor of its fg token (`fg.default`'s floor when the token is unknown). Example: `fg.faint` on a selection bar, Mocha 2.89:1. Mocks: the `cc` advisory selection-row rows. | M | style | `ratio` per span; `cc` advisory rows |
| CA-07 | Dim text still passes. Fail when a `dim` span, modelled as `blend(fg, bg, 0.55)` ([formats.md](formats.md#contrast-floors)), falls below its token's floor (Mocha `fg.muted` dim on base = 3.21:1). | M | style | `blend()` + `ratio` |
| CA-08 | CVD-safe status. Fail when error and success differ only in hue (red/green, same glyph), or have < 1.5:1 luminance contrast with each other and no glyph or word difference. | M | style | `ratio(status.error, status.success)` + glyphs |
| CA-09 | Works on a light background. For 16-colour apps, fail when CA-01..05 fail on a light theme (e.g. `catppuccin-latte`). Yellow/cyan/green on white are the classic failures. | M | style | `cc catppuccin-latte --depth 16` |
| CA-10 | Motion can stop. Fail on SGR blink, or animation that lasts > 5 s with no off switch, or animation when stdout is not a TTY. | M | style | `E[spinner]`, `cap` piped |
| CA-11 | A linear mode exists for tools used by screen-reader users or pipelines (`--plain`/`--json`/screen-reader flag). Fail when it is absent and the tool's output is consumed by other programs. | m | style | `--help` |
| CA-12 | Charts carry numbers. Fail when a chart, sparkline or gauge has no numeric label or summary. | m | style | `E[chart,sparkline,gauge].text` |

## 9. Glyphs & width (GW)

| ID | Rule → fail when | Sev | Kind | Verify |
|---|---|---|---|---|
| GW-01 | No double-width or unstable glyphs in layout text: W/F, emoji presentation, VS15/VS16, ZWJ, regional indicators, PUA (unless Nerd Font opt-in). Fail on any `lint` ERROR. B when it shifts columns (DA-01). | M/B | bug | `lint` |
| GW-02 | No text-default emoji (`✔ ✖ ⚠ ⚙ ℹ ▶ ⏸`). Fail on a `lint` WARN, which proposes a SAFE replacement (`✓ ✗ ! i ▸`). | m | style | `lint` |
| GW-03 | Ambiguous-width glyphs (`● ▲ … · → •`) outside chrome are a known risk. Fail when `lint --strict-ambiguous` errors and the app claims CJK-locale support. | m | style | `lint --strict-ambiguous` |
| GW-04 | One glyph per concept app-wide. Fail when two glyphs mean the same thing (`✓` and `✔`, `▲` and `!`). | m | style | glyph inventory over `ST` |
| GW-05 | ASCII fallback works. Fail when `cap env=TERM=linux` (or `cap env=LANG=C`) still draws Unicode chrome with no ASCII mode, or draws tofu. | m | style | `cap env=TERM=linux` |
| GW-06 | Width is measured in cells, not string length. Fail when injecting CJK/emoji data (`名前`, `👤`) shifts later columns or overflows the row. | M | bug | `cap` with wide test data, DA-01/02 |
| GW-07 | Border sets are consistent per level. Fail when sibling panels mix rounded, single and heavy without a role reason (`border.style` differs or is `mixed`). | m | style | `R.border.style` |
| GW-08 | One ellipsis. Fail when `…`, `⋯` and `...` are mixed. | m | style | `E.text` |

## 10. Terminal compatibility (TC)

| ID | Rule → fail when | Sev | Kind | Verify |
|---|---|---|---|---|
| TC-01 | The terminal is restored on every exit path (q, ctrl+c, error). Fail when after exit `#{alternate_on}`≠0, the cursor is hidden, echo is off, mouse reporting is on, or SGR leaks. | B | bug | `cap+k q`, then `tmux -L <name> display -p` |
| TC-02 | NO_COLOR is honoured: non-empty `NO_COLOR` removes colour SGR and keeps bold/underline/inverse. Fail when the capture still has 30–38/40–48/90–107 codes. | M | bug | `cap env=NO_COLOR=1` (live capture grid) |
| TC-03 | Non-TTY and `TERM=dumb` output is clean: no animation, no cursor addressing. Fail when `app … \| cat` prints escape sequences or spinner frames. | M | bug | run piped |
| TC-04 | Colour depth is respected. Fail when, with `COLORTERM` unset and `TERM=xterm-256color`, the app emits `38;2` truecolor SGR without a fallback, or `TERM=xterm` gets 256-colour codes. | m | bug | `cap env=COLORTERM=` (empty) and `cap env=TERM=xterm`: SGR forms |
| TC-05 | Untrusted strings are sanitised. Fail when data containing ESC/CSI/OSC (`\x1b[2J`, `\x1b]8;;…`) changes the frame instead of showing escaped text. | B | bug | `cap` with hostile data |
| TC-06 | Screen mode fits the app. Fail when a fullscreen app does not use the alt screen and leaves its frame in scrollback, or an inline/picker app enters the alt screen and loses the shell context. | m | style | `M.capture.alternate_screen` |
| TC-07 | Paste is text. Fail when a pasted newline submits a form or a pasted `q` quits (no bracketed paste). | M | bug | `tmux -L <name> paste-buffer -p` in cap |
| TC-08 | Ctrl+C acts within 1 s from any state, including busy. Fail when the app hangs or ignores it. | M | bug | `cap+k C-c` timing |
| TC-09 | Under tmux, rich features degrade quietly. Fail when OSC 8 links, kitty keyboard or graphics leave visible garbage under tmux without passthrough. | m | bug | live capture is inside tmux |
| TC-10 | The host's capability profile is respected. Fail when a mock or the app uses an attribute, colour depth, glyph level or widget outside the profile (`#! caps:` line, or the host's documented limits): italic in a host without italic, Nerd Font glyphs at glyph level unicode, an inline text input in a host whose plugins only get lists. Also fail when a recommendation does not name what it requires. | M | style | `lint` with `#! caps:`; `glyphs`; live capture SGR vs the profile |

### 10.1 Shell contract (SH)

Where the TUI meets the shell: exit codes, signals, pipes, streams, `--json`, cd on exit. Apply to one-shot CLIs, inline pickers, and full-screen apps that can also run in a pipe or a script ([layout-archetypes.md](layout-archetypes.md#product-shapes) P4). Rules and per-language fixes: [cli-contract.md](cli-contract.md); the `CC rule` column names its rules. Notation as in "How to use"; `pipestatus[1]` is zsh (bash: `PIPESTATUS[0]`); with `cap+k X`, run the command as `sh -c 'APP; echo $? > rc'` and read `rc`. On a screenshot or a mock these are `n/a` except where [§0.2](audit-quick.md#02-core-items) "Shell contract" says otherwise.

| ID | Rule → fail when | Sev | Kind | Verify | CC rule |
|---|---|---|---|---|---|
| SH-01 | `app list \| head -1` ends silently. Fail when stderr has a traceback, panic or `EPIPE`, or the app's status is not 0 or 141 (1 accepted for Python's documented recipe). | M | bug | `app list 2>err \| head -1; echo ${pipestatus[1]}; [ ! -s err ]` | CC7 |
| SH-02 | Ctrl-C in the picker or TUI exits 130. Fail when `echo $?` gives 0 or 1. | M | bug | `cap+k C-c`, read `rc` | CC1, CC2 |
| SH-03 | Esc (cancel) in a picker exits non-zero (130, or a documented 1). Fail when 0. | M | bug | `cap+k Escape`, read `rc` | CC1 |
| SH-04 | A chosen value reaches stdout alone. Fail when `out.txt` holds chrome, a receipt or any ESC byte. | B | bug | `app > out.txt` + `cap+k Enter`; `grep -c $'\e' out.txt` = 0 | CC9, P2 |
| SH-05 | Output to a file is plain. Fail when `app > out.txt` contains ESC bytes, `\r` spinner frames or `?1049h`. | M | bug | `app > out.txt; grep -c $'[\e\r]' out.txt` = 0 | CC11, CC13; extends TC-03 |
| SH-06 | SIGTERM restores the terminal and exits 143. Fail (B) when raw mode, the alt screen or a hidden cursor survive; (m) when the status is 0. | B/m | bug | LC1 restore check with `kill -TERM` from another pane; `#{alternate_on}` | CC5 |
| SH-07 | Piped data does not break the UI: `printf 'a\nb\n' \| pickf` still takes keys; `echo x \| app` never prompts on stdin. | M | bug | `cap` of `printf … \| pickf` + `-k Down Enter` | CC9, cli-contract §3 table |
| SH-08 | No terminal: fail when the app hangs or prompts; pass when it exits non-zero within 1 s naming the non-interactive flag. | M | bug | Linux: `setsid -w app </dev/null >out 2>err; echo $?` | CC10, LC8 |
| SH-09 | A command that expects stdin, run with stdin on a TTY, prints usage and exits 2. Fail when it waits. | m | bug | `cap@80x24`, no keys, check `rc` after 1 s | CC8 |
| SH-10 | Exit codes match the class: usage 2, runtime 1, cancel 130; stdout empty on failure. Fail when a usage error exits 1 without a usage hint, or any failure exits 0. | M | bug | `app --bogus; echo $?`; force a runtime error | CC19, cli-contract §1 |
| SH-11 | Errors say what, why, next. Fail when stderr shows a bare `Error: ENOENT`, or a stack trace without `--debug`. | m | style | read stderr of a forced error | CC18, CC20 |
| SH-12 | `--json` is parseable and plain. Fail when `app list --json \| jq -c . >/dev/null` fails, the output has SGR, or a list is neither NDJSON nor one documented array. | M | bug | the command above; `grep -c $'\e'` | CC15-CC17 |
| SH-13 | Pager and progress only on a TTY. Fail when `app log \| cat` waits for `q`, or `app sync 2>err` leaves spinner frames in `err`. | M | bug | run piped / redirected | CC11, CC12 |
| SH-14 | cd on exit works both ways. Fail when the wrapper does not change dir after a choice, or does after cancel / the no-cd quit key. | M | bug | `pcd`, choose, `pwd`; again with Esc | CC21 |
| SH-15 | rc files untouched without consent. Fail when `~/.zshrc` / `~/.bashrc` checksums change after first run or `init` without a prompt that named the change. | B | bug | `shasum ~/.zshrc` before / after | CC24 |

## 11. Framework-specific rendering bugs (FR)

Use these when the framework is known (brief or source code). Each is a **bug** with a known mechanism. The pitfalls section (§13) of `frameworks/<x>.md` ([frameworks/](frameworks/)) is the source of truth and holds the fixes; these rows index it.

| ID | Symptom on screen → mechanism | Sev | Verify |
|---|---|---|---|
| FR-01 | Any: merged rows, doubled suffix (`6h agos · 6h ago`), missing row next to long rows → over-width row wrapped by the terminal; the renderer's line accounting drifts. Fix: per-cell truncation (every cell has a width and truncates). | B | DA-02, `ST` |
| FR-02 | Ink: flicker and scrollback wiped every frame → output taller than `stdout.rows` triggers `clearTerminal` (incl. `ESC[3J`). Fix: keep the live region < rows (`useWindowSize`), move history to `<Static>` ([ink#935](https://github.com/vadimdemedes/ink/issues/935), [ink#990](https://github.com/vadimdemedes/ink/issues/990)). | B | RS-06 |
| FR-03 | Ink: ghost lines after the terminal narrows → stale lines on resize. Fix: full redraw on resize; test RS-05. | M | RS-05 |
| FR-04 | Ink: fixed id/age columns squeezed at narrow widths → `flexShrink` defaults to 1. Fix: `flexShrink={0}` on fixed cells, `flexGrow={1}` on the flex cell. | M | DA-01 at 80×24 |
| FR-05 | Ink: feed rows never update or appear in the wrong order → `<Static>` is write-once. Fix: window a normal list by slicing. | M | `cap` over time |
| FR-06 | Lip Gloss v2: panes 2–4 cells off, footer pushed below the screen → `Width` includes border+padding; `Height` is a minimum and grows with wrapped text. Fix: inner = `w - style.GetHorizontalFrameSize()`; clip with `MaxHeight`. | M | DA-02, LH-02 |
| FR-07 | Bubble Tea: stray text lines tearing the frame → `fmt.Println` to stdout. Fix: `tea.LogToFile`; `tea.Println` (inline only; dropped in alt screen). | B | `ST` |
| FR-08 | Bubble Tea: frozen spinner/cursor, list ignores keys → messages not forwarded to the child, or its return value not reassigned. | M | `cap` twice |
| FR-09 | Ratatui: underlying text shows through a popup → no `Clear` widget rendered before the popup. | M | LH-10 |
| FR-10 | Ratatui: columns shift after styled text → ANSI escapes inside `Span` content (#902). Fix: use `Style`; convert with `ansi-to-tui`. | M | DA-01 |
| FR-11 | Ratatui: selection resets every frame → `ListState`/`TableState` created inside render. | M | FS-01, `cap+k j` |
| FR-12 | Ratatui/crossterm on Windows: every key acts twice → key-release events handled as presses. Fix: filter `KeyEventKind::Press`. | M | interaction test |
| FR-13 | Textual: a panel collapses to 0 rows or stretches to fill → `Horizontal`/`Vertical` (`1fr`) inside `VerticalScroll`. Fix: `HorizontalGroup`/`VerticalGroup`. | M | `R.bbox.h` |
| FR-14 | Textual: colours ignore the user's terminal theme → Textual overrides ANSI colours unless `ansi_color=True`. | m | CT, CA-09 |
| FR-15 | Textual / any async UI: no repaint or input during work → blocking I/O in a handler. Fix: `@work` (Textual), `tea.Cmd` (Bubble Tea), async tasks. | M | `cap` during work |

