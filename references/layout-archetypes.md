# Layout archetypes

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [Product shapes](#product-shapes) · L14–39 — first, for any design or review: full-screen, inline picker, one-shot CLI or plugin in a host (P1–P4), and what each host decides.
- [1. Choose an archetype](#1-choose-an-archetype) · L41–65 — picking the screen structure from the operator's main question; combining two archetypes.
- [2. General layout rules (all archetypes)](#2-general-layout-rules-all-archetypes) · L67–173 — rules L1–L14 for every screen; §2.1 size classes, §2.2 too-small screen, §2.3 states (empty, busy, error), §2.4 zebra striping.
- [3. Archetypes](#3-archetypes) · L175–191 — one file per archetype (A–K) in `archetypes/`: open only the one you chose.
- [4. Mockup index](#4-mockup-index) · L193–211 — which shipped `.mock` to start from.

Labels: `[live]` = seen in a tmux capture of the real app; `[src]` = read in its source or default config; `derived:` = our inference. Mockups are `.mock` files ([formats.md](formats.md#mockup-format)) under `../assets/mockups/<archetype>/`; lint them with `python3 SKILL_DIR/scripts/render_mockup.py FILE --check`.

---

## Product shapes

Classify the product **before** choosing an archetype: the shape decides who owns the screen, where output goes and what "exit" means. Layout cannot fix a wrong shape (a pane layout for a one-line choice, a full-screen app where a host gives you a popup).

| Shape | Screen | Streams and exit | Design with | Exemplars |
|---|---|---|---|---|
| **Full-screen session** | alt screen, whole terminal, stable spatial model (panes never move on their own) | the app owns the TTY; diagnostics to a file; terminal restored on every exit path ([lifecycle.md](lifecycle.md)) | archetypes A-I; every state × size ([formats.md](formats.md#frame-naming)) | lazygit, k9s, btop, helix |
| **Summon–choose–exit (inline picker)** | inline, a bounded viewport under the prompt; scrollback above stays visible | chrome on `/dev/tty` or stderr, **only the result on stdout**; exit code = chosen / nothing / cancelled; erase or leave a one-line receipt; contract: [cli-contract.md](cli-contract.md) §1, §3, §7 | archetype **J**; frames at the viewport height | fzf `--height`, gum `choose`/`filter` |
| **One-shot CLI** | no live UI; at most a spinner or progress line on stderr | stdout = results (plain or `--json` when piped), stderr = diagnostics, meaningful exit codes, works without a TTY; contract: [cli-contract.md](cli-contract.md) (exit codes, signals, `app \| head`, progress, NDJSON, errors) | output samples, not screens; [clig.dev](https://clig.dev/) | `gh`, `git`, `rg` |
| **Plugin or popup inside a host** | the region the host gives you (panel, popup, float), often with a host-drawn border and title | the host owns the screen, the keys, the styling and the lifecycle; it decides how a result returns (stdout, callback, exit status) | the host's **capability profile**, then the closest archetype at the host's region size | tmux popup, herdr pane, Neovim float, k9s plugin, lazygit custom command |

| # | Rule | When | Concrete example |
|---|---|---|---|
| P1 | **Name the shape first** and write it into the design-system brief; escalate only on evidence (one-shot → inline picker → full-screen) | every new design or review | "pick a branch to switch to" is an inline picker, not a list + detail app |
| P2 | **Keep stdout for the result** whenever the tool can run inside `$(…)` or a pipe: every UI byte goes to `/dev/tty` or stderr, the answer to stdout without ANSI | inline pickers, one-shot CLIs | `git switch "$(pick-branch)"` works only if the picker draws on `/dev/tty` (fzf does; gum draws on stderr) |
| P3 | **Host first: ask for its capability profile before designing.** Widgets/components offered, SGR attributes (italic? dim?), color depth and whether colors come from the host theme, glyph level (ascii / unicode / nerd), region size, who draws border and title, reserved keys, how results return. Record it as the `#! caps:` header ([formats.md](formats.md#capability-profile)) so the linter rejects what the host cannot draw, and tag each recommendation with what it needs ("needs italic") | plugins, popups, floats, custom commands | proposing italic, inline inputs and breadcrumbs for a plugin before asking what its API allows |
| P4 | **The shell boundary is part of the design** for every shape that can run in a pipe, a script or `$(…)`: exit codes (0 / 1 / 2 / 130 / 143), Ctrl-C and SIGPIPE behavior, which stream gets what, `--json`, cd on exit. Write them into the brief next to the shape; review them with SH-01…SH-15 | one-shot CLIs, inline pickers, full-screen apps with a scripted mode | `logq list \| head -1` ends silently with status 0 or 141; `pickf` cancelled by Esc exits 130; contract in [cli-contract.md](cli-contract.md) |

Host notes (what each host decides for you):
- **tmux popup** — `display-popup -E -w 80% -h 60% CMD` (to try it yourself: `tmux -L <name> display-popup …` on a private server) runs your program in a PTY of the popup's size inside a tmux-drawn border (`-B` drops it); `-E` closes the popup when the program exits. Design a full-screen app at the popup size, not the terminal size.
- **Neovim float** — `nvim_open_win(buf, enter, {relative = "editor", width = …, height = …, border = …})`; colors come from highlight groups (link to `NormalFloat`, `FloatBorder`… instead of hex), keys are buffer-local maps that must not shadow the user's.
- **k9s plugin** — a `plugins.yaml` entry (`shortCut`, `scopes`, `command`, `args`, `background`); a foreground command gets the terminal while k9s waits, then k9s redraws. Your UI is a full-screen app or a one-shot inside k9s's lifecycle.
- **lazygit custom command** — `customCommands` (`key`, `context`, `command`, `prompts`, `output`); the prompts are lazygit's own menus and inputs (you style nothing); only a command that `output`s to the terminal gets the screen.
- **Other multiplexers and app hosts** (herdr, zellij, an editor's plugin API) — the host's API defines the components, keys and focus you get; ask for it before designing.

---

## 1. Choose an archetype

Start from the operator's most frequent question, not from the data model. Most real apps combine two archetypes (lazygit = A + B, k9s = I + E + G); pick the primary for the most frequent task and add the second as a view or overlay.

| Task shape (operator question) | Archetype | Why it fits | Exemplar | Mockups |
|---|---|---|---|---|
| "Is everything healthy right now?" several live sources at a glance | **[A. Multi-pane dashboard](archetypes/a-dashboard.md)** | every source visible at once, no navigation needed to notice a spike | btop, lazydocker | `dashboard/sysmon--*` |
| "Which item needs me, and what is in it?" | **[B. List + detail](archetypes/b-list-detail.md)** | list stays scannable, selection carries depth | lazygit, gitui, k9s describe | `list-detail/prs--*` |
| "Where is it in this hierarchy?" browse a deep tree of containers | **[C. Miller columns](archetypes/c-miller-columns.md)** | parent / current / preview keeps context while drilling | yazi, ranger | `miller-columns/files--*` |
| "Change this text/document" with many commands | **[D. Editor + statusline + which-key](archetypes/d-editor.md)** | maximal content area; modes and commands discovered on demand | helix | `editor/code--*` |
| "What just happened?" append-only events | **[E. Log / stream viewer](archetypes/e-log-viewer.md)** | time-ordered rows, follow vs paused is the core state | k9s logs, lnav | `log-viewer/stream--*` |
| "Give the app N inputs once" | **[F. Form / wizard](archetypes/f-form-wizard.md)** | linear focus, validation where the input is | huh forms, posting | `form-wizard/setup--*` |
| "Run any command without remembering its key" | **[G. Command palette overlay](archetypes/g-command-palette.md)** | one fuzzy input over everything; doubles as help | helix `Space ?`, yazi help | `command-palette/palette--*` |
| "What is big / where is it nested?" sizes or ownership in a tree | **[H. Tree browser](archetypes/h-tree-browser.md)** | indentation + guides show containment; expand on demand | ncdu, gdu, k9s xray | `tree-browser/diskusage--*` |
| "Find rows by attribute across hundreds of records" | **[I. Table / grid explorer](archetypes/i-table-explorer.md)** | sortable columns, filter, one row per record | k9s, htop | `table-explorer/pods--*` |
| "Pick one (or a few) and get back to my shell" | **[J. Inline picker](archetypes/j-inline-picker.md)** | bounded viewport, type-to-filter, result on stdout | fzf `--height`, gum `filter` | none shipped (build with `mockkit.py`) |
| "What is it doing, and what do I say next?" converse with a responder that streams and acts | **[K. Chat / agent session](archetypes/k-chat-session.md)** | append-only turns above, one input below; the live tail is the only moving part | Claude Code, Codex CLI, Gemini CLI | `chat/session--*` |

Combination rules (`derived:` from the catalog in [exemplars.md](exemplars.md) §8):
- A + B when the "detail" is itself a live feed (lazydocker: lists left, tabbed Logs/Stats right).
- I + E / I + B when rows drill into a log or a description (k9s `Enter`, `l`, `d`).
- G belongs on top of any archetype with more than ~15 actions; it is an overlay, never a screen.
- K + G: slash commands and `@` mentions open a palette anchored above the input. K + B at ≥ 110 cols: a sidebar with the session's changes, plan and context use.

---

## 2. General layout rules (all archetypes)

| # | Rule | When | Concrete example |
|---|---|---|---|
| L1 | **Fixed chrome bands**: 1-row header band, body, 1-row message line, 1-row key-hint footer | every full-screen app | canonical demo: row 0 header, rows 1-21 panes, row 22 message, row 23 keybar (`../assets/demo/fleet--normal--80x24.mock`) |
| L2 | **Rows are cells.** Lay out each row as columns with their own width and truncation, never one hand-padded string | any list, table, tree, log | `❯ │ ✓ │ #482 │ Retry webhook deli… │ 2h` = cursor 2, glyph 2, id 5, title flex, age 3 right |
| L3 | **Fixed vs flexible columns**: ids, glyphs, status, numbers, ages are fixed; exactly one text column (name/title/message) is flexible and absorbs width changes | tables and lists | `pods--normal--80x24`: NAME flex (35), READY 6, STATUS 13, RS 4, CPU 6, MEM 7, AGE 5 |
| L4 | **Truncate per cell with `…`** (1 cell, budget it), never per row and never by wrapping chrome. **Direction by content:** paths and URLs at the start, so the file name survives; names, titles, prose and IDs at the end | any overflow | `✗ CrashLoop…` (STATUS cell), `…/tests/retry_test.go` (path cell), `Retry webhook deli…` (title cell) |
| L5 | **Numbers right-aligned, same unit per column**, label left | numeric columns | `  9.8G`, ` 21.4G`; `212Mi` / ` 32Mi`; age `6d`, `47m` right-aligned |
| L6 | **Hanging indent** for wrapped content: continuation lines start at the message column, not column 0 | logs, descriptions, errors | log row wraps under `MESSAGE` at col 23, timestamps column stays clean (`stream--normal--80x24`) |
| L7 | **Detail text max ~72 cells per line**, even in wide panes | detail panes, descriptions, help text | description wrapped at `min(pane-4, 64)` in `prs--normal--120x30`; cards at `min(columns-4, 72)` |
| L8 | **One focus indicator**: focused pane = `border.focus`; focused row = `selection.bg` + `❯`; nothing else uses those tokens | every screen with >1 pane | Services list blue border + `❯` row; detail pane `border.default` |
| L9 | **Contrast layering**: (1) act-now = chip/bold/status color, (2) content = `fg.default`, (3) metadata = `fg.muted`/`fg.faint`. Primary content on a failing row is never faint | every screen | `✗ CrashLoop…` bold `status.error`; names `fg.default`; ages `fg.faint` |
| L10 | **Border vs whitespace**: border a region when it has its own focus, scroll or title; use whitespace or a single `│` rule otherwise. Never nest borders more than one level | all | Miller columns use only `│` rules (yazi); dashboard boxes are bordered because each has a title and toggle key (btop) |
| L11 | **Titles carry state**: `Name (count)`, position `3 of 7`, sort, filter, freshness live in the border, not in the body | bordered panes | `╭─ Inbox (7) ─…─ 1 of 7 ─╯`, `─ sort cpu ─`, `─ /api ─`; lazygit `1 of 5`, k9s `Pods(ns)[12]`, btop `┤filter├` |
| L12 | **Key hints only in the footer** (plus transient which-key/overlay hints); no hint text in pane bodies, except the next action inside an empty/error state. Format: [interaction.md](interaction.md) §3 | all | footer `↑↓ select  enter open … ? help  q quit` |
| L13 | **Stable geometry across states**: loading, empty, error and normal use the same regions and widths | all | `diskusage--busy` keeps columns; `prs--empty` keeps both panes |
| L14 | **Header right = context, message line = last event** (with age), both 1 row | all | `prod-eu · 12:04:31`; `✓ merged #473 into main · 4m ago` |

### 2.1 Size classes and what to show

Standard sizes are 80x24 (de-facto minimum), 120x30 (Windows Terminal default), 170x40 (wide laptop / external monitor); layouts with side-by-side panes also get the 60-column floor test below. Breakpoints are `derived:` from those sizes plus measured exemplar thresholds.

| Class | Size | Show | Hide / compress | Evidence |
|---|---|---|---|---|
| too small | below the computed minimum | only the too-small screen (§2.2) | everything | btop 80x24 floor with 4 boxes; lazygit `<9` rows [src] |
| narrow | 60-79 cols (a tmux or editor split) | the focused pane only, full width; drill-down (`enter` opens, `esc` returns) instead of side-by-side; breadcrumb instead of a parent column | second and third panes, previews, secondary columns | `derived:`; lazygit `screenMode: full` is the manual version [src] |
| compact | 80-99 cols or 24-29 rows | primary pane + one secondary; 1-row bands; abbreviated labels (`3.2 GHz`, `6d`) | extra columns (IP, NODE, FILES), histograms, third panes, footer verbs beyond ~6 | btop at 80x24 abbreviates `U/A/C/F` [live]; lazygit collapses unfocused side windows to 1-row title bars on short terminals [live] |
| regular | 100-159 cols, 30-39 rows | add secondary columns, side previews, histograms, 8-10 footer verbs | — | lazygit side panel = 1/3 of width (`sidePanelWidth: 0.3333`) [src] |
| wide | ≥160 cols, ≥40 rows | third pane (e.g. list + detail + preview), split diffs, per-core/per-item graphs | nothing; cap text measure at L7 | lazygit splits the main view side-by-side when width ≥ 200 or height ≤ 30 (`mainPanelSplitMode: flexible`) [src] |
| portrait | ≤84 cols and ≥46 rows | stack panes vertically (list on top, detail below) | side-by-side layout | lazygit `portraitModeAutoMaxWidth: 84`, `portraitModeAutoMinHeight: 46`; lazydocker `width <= 84 && height > 45` [src] |

**Floor test (60-column split).** Every layout with two or more side-by-side panes is checked at 60 columns: `tmux -L <name> split-window -h` leaves 59 columns per pane on a 120-column window and 39 on an 80-column one. State, in the design system or the review: which pane wins (the focused one), what hides (preview, parent column, secondary columns), what becomes drill-down, and where the too-small screen starts (below the single-pane minimum, not at 80). A multi-column layout with no single-pane fallback fails. Example: B list + detail at 60x24 = list only, `enter` shows the detail full-width, footer `enter open  esc back`. Mock it as a `--60x24` frame when the layout changes there.

Degrade in this order: (1) drop optional columns right-to-left by priority, (2) shorten labels and units, (3) collapse unfocused panes to 1-row title bars, (4) hide secondary panes (toggle keys keep them reachable), (5) show the too-small screen. Never let a row wrap, never clip silently.

### 2.2 The too-small screen

Compute `MIN_COLS x MIN_ROWS` from the panes currently enabled (btop sums its boxes: Cpu 60x8, Mem 36x10, Net 36x6, Proc 44x16 → 80x24 [src]). Below it, replace the whole UI with: a title, current vs needed in **words and color** (never color alone), and the keys that fix it in place (toggle panes, quit). Keep handling resize and quit (signals: [terminal-capabilities.md](terminal-capabilities.md) D10). In mockups this is the `toosmall` frame, drawn one size below the minimum ([formats.md](formats.md#frame-naming)); `../assets/mockups/dashboard/sysmon--toosmall--60x18.mock`. For accessibility checks resize to e.g. 60x18 and 40x10 ([accessibility.md](accessibility.md) A5).

```text
            Terminal too small
        Width  60   needs 80  ✗        <- 60 status.error bold, ✗ = word-free cue
        Height 18   needs 24  ✗
   Enlarge the window, or hide a box to fit:
      1 cpu  2 mem  3 net  4 proc
                 q quit
```

Exemplar behavior:
- **btop** `[src]`: clears and centers `Terminal size too small:` / `Width = <w> Height = <h>` (red if below minimum, green if OK) / `Needed for current config:` / `Width = <minW> Height = <minH>`; polls every 100 ms; `q` quits and `1`-`4` toggle boxes so the user can fix it in place. Effective minimum is computed from the enabled boxes (Gpu 41x8 also exists).
- **lazygit / lazydocker** `[src]`: responsive instead of refusing. lazygit `gui.portraitMode: auto` stacks panels when width ≤ `portraitModeAutoMaxWidth` (**84**) and height ≥ `portraitModeAutoMinHeight` (**46**); `screenMode: normal|half|full`. Hard floor: height < max(9, side windows + 4) or width < 10 shows the box `Not enough space to render panels` (acceptable, but it omits the needed size; prefer btop's form). lazydocker has the same floor and portrait at width ≤ 84 and height > 45. The lazygit footer hint line truncates with `...` at 70 cols.
- **gitui, yazi, helix** degrade silently `[live]`: gitui's tab bar is cut mid-word (`Stashing [4]  |`) at 60x15 and its command bar elides to `Stage All [a] Stage [⏎]  more [.]`; yazi shrinks by ratio, elides names with `…` and its status bar overlaps itself at 30x8; helix drops right-hand statusline items at 40x8. Graceful but unannounced: do not copy.
- **Claude Code screen-reader mode** sidesteps size by printing scrolling text.

### 2.3 States every archetype must design

**The required list** (which states, when, sizes) lives only in [formats.md](formats.md#frame-naming): `normal`, `empty`, `busy`, `error`, `toosmall`. `degraded` (stale data kept, partial failure) is a **variant of `error`**, not a sixth state; name its frame `error`. This section says what each state shows. Glyphs per state: [visual-vocabulary.md](visual-vocabulary.md) V5/V8.

| State | Shows | Never | Mockup example |
|---|---|---|---|
| `empty` | what will appear here + why it is empty + the key/command that makes it appear; keep the frame | "No items" before the first load finished | `prs--empty`, `stream--empty`, `palette--empty` |
| `busy` (loading/scanning) | spinner + verb + progress counts in the message line; elapsed time once the wait passes ~1 s ([interaction.md](interaction.md) §8.1); finished parts final, unfinished parts faint; unsafe verbs disabled; a cancel affordance | reordering rows under the cursor; fake totals | `diskusage--busy` |
| `error` (total) | `✗` + what failed + why (human terms) + next action; keep last good data visibly marked stale | blank screen; raw exception | `files--error` (local to one column), `code--error` |
| `error` / degraded (partial) | `STALE 42s` chip in the header, values in `fg.faint`, sample time, retry countdown; read-only verbs still work; the missing source stays in the saved config ([interaction.md](interaction.md) §8.1) | showing stale numbers in normal colors; dropping the missing source from the user's config | `sysmon--error`, `pods--error` |
| `toosmall` | §2.2 | silent clipping | `sysmon--toosmall--60x18` |

**Patterns from real TUIs:**

| App | Pattern |
|---|---|
| **k9s** | three distinct states in a flash line: loading `Synchronizing <gvr> in "<ns>" namespace...` (info), error `Unable to sync <gvr>: <err>` (warn), empty `No resources found for <gvr> in "<ns>" namespace` (warn) shown only after the informer cache has synced; code comment: "While the informer cache hasn't synced yet, show a neutral status instead of a misleading 'no resources found' warning" (`internal/view/browser.go`) |
| **lazygit** | panel-level empty text: `No changed files`, `No commits for this branch`, `No branches for this repo`, `No stash entries`, `No matches for '%s' %s`; loading `Loading commits`, `Loading file suggestions` with the `●∙∙` spinner (180 ms); fatal `An error occurred! Please create an issue...` + `Press enter to return to lazygit`; too-small floor `Not enough space to render panels` (`pkg/i18n/english.go`) |
| **btop** | too-small screen replaces everything (§2.2) |
| **GitHub CLI, huh, Claude Code** | static `Working...` (or action-specific text) instead of an animated spinner in accessible mode |
| **Textual** | `Widget.loading = True` temporarily replaces the widget with a `LoadingIndicator` and disables interaction (`widget.py`) |
| **Skeleton screens** | no first-party TUI exemplar found (`UNVERIFIED` as prior art). `derived:` pattern: paint the final layout immediately with dim `░` (N) or `···` placeholders at final widths, swap in place, no animation under reduced motion |

Rules (`derived:` from the table):

| Rule | Example |
|---|---|
| **loading != empty != error**: never show "No X found" before the first load completes (k9s encodes this) | `⋯ Loading services` -> `No services in "prod". Press n to create one.` |
| every state gets a text label, a reason, and a next action | `✗ Unable to reach api (timeout 5s). Press r to retry.` |
| errors in human terms, the most important information last (clig.dev) | `could not save config: permission denied: /etc/myapp.toml` |
| show a loading state only after a short delay (~100-300 ms; the number is `UNVERIFIED`) to avoid flashes | |
| keep geometry stable across loading -> loaded (same width/height) | skeleton `░░░░░░░░ ░░░░` rows in the final columns |
| a retry/cancel affordance is visible during long loads; Ctrl-C exits promptly | footer `esc cancel` |

### 2.4 Zebra striping (tables, logs, long lists)

Alternate-record fills keep the eye on one record across a wide row. They are decoration, never data. Token and contrast order: [color-tokens.md](color-tokens.md#zebra-stripes-the-weakest-fill).

| # | Rule | When | Concrete example |
|---|---|---|---|
| Z1 | **Stripe where the eye travels** | wide tables or logs with whitespace gaps between columns (≳ 20 cells), ≥ ~8 visible rows, or records that span 2+ lines | an event table with a ~25-column gap between EVENT and AGE: striped |
| Z2 | **Skip it** on short or narrow content | lists of ≤ ~6 rows, single-column lists, trees (guides already lead the eye), tables with row rules | the 5-6-row side lists next to that event table: not striped |
| Z3 | **Weakest fill on screen**: stripe < inactive selection < selection (contrast vs `bg.base`); the cursor row's selection replaces the stripe, never blends with it | always | Tokyo Night: `bg.stripe` 1.05, `selection.inactive.bg` 1.27, `selection.bg` 1.53 |
| Z4 | **Darker, not lighter, in dark themes**: `bg.stripe` (→ `bg.inset`) sits below base, so `bg.surface`/`bg.raised` stay free for selection, hover, popups | dark themes | a stripe lighter than base left selection only 1.10:1 against it |
| Z5 | **Parity anchored to the data, never to the viewport** | anything that scrolls; live "following" feeds | parity = arrival sequence counted from the **oldest** event (`seq % 2`), or a stable id's position in the sorted, filtered result; scrolling and new rows at the top never flip existing stripes. A viewport-index parity (Textual `zebra_stripes` uses the row index) flips on every new event |
| Z6 | **Stripe whole records**, full pane width | multi-line records | a wrapped log entry (hanging indent, L6) gets one stripe on both lines, gaps included |
| Z7 | **Never meaning-bearing**: no striping by group or status (use a heading or a glyph); the screen must read the same without stripes | always | stripes vanish in 16 colors (`ansi16 default`), under `NO_COLOR` and in themes where `bg.inset` = `bg.base` |
| Z8 | **Keep existing stripes in a redesign**, or say why you drop them | redesigns, reviews | dropping an app's striping silently removes a decision that worked |

Mockups: `table(..., zebra="newest-first")` in `mockkit.py` (parity anchored to the data; see [mockkit-api.md](mockkit-api.md#canvas-table-listing-tree)), or `{on:bg.stripe}` over the whole record row / `Canvas.fill(x, y, w, h, "bg.stripe")` before writing the row's text.

---

## 3. Archetypes

One file per archetype in [archetypes/](archetypes/); open only the one you chose in §1.

- **A. Multi-pane dashboard** — [archetypes/a-dashboard.md](archetypes/a-dashboard.md): monitoring several live sources at a glance (gauges, graphs, one interactive table).
- **B. List + detail** — [archetypes/b-list-detail.md](archetypes/b-list-detail.md): the operator picks one item from tens to hundreds and reads or acts on it.
- **C. Miller columns** — [archetypes/c-miller-columns.md](archetypes/c-miller-columns.md): browsing a deep hierarchy where parent and sibling context matter.
- **D. Editor + statusline + which-key** — [archetypes/d-editor.md](archetypes/d-editor.md): a long text edited with many commands: modes, statusline, which-key.
- **E. Log / stream viewer** — [archetypes/e-log-viewer.md](archetypes/e-log-viewer.md): append-only, time-ordered events: follow vs paused, wrapping, filters.
- **F. Form / wizard** — [archetypes/f-form-wizard.md](archetypes/f-form-wizard.md): forms, wizards and settings screens: validation timing, required and conditional fields, persistence, dirty state (F1–F7).
- **G. Command palette overlay** — [archetypes/g-command-palette.md](archetypes/g-command-palette.md): more actions than a footer can list: a fuzzy palette overlay that doubles as help.
- **H. Tree browser** — [archetypes/h-tree-browser.md](archetypes/h-tree-browser.md): containment is the point: disk usage, dependency or ownership trees.
- **I. Table / grid explorer** — [archetypes/i-table-explorer.md](archetypes/i-table-explorer.md): many records with comparable attributes: columns, sort, filter, striping.
- **J. Inline picker (summon–choose–exit)** — [archetypes/j-inline-picker.md](archetypes/j-inline-picker.md): summon–choose–exit from a shell or host key: bounded viewport, result on stdout.
- **K. Chat / agent session** — [archetypes/k-chat-session.md](archetypes/k-chat-session.md): chat and agent sessions: follow and scrollback, streaming, input, busy, approvals, screen-reader mode (K1–K8).

---

## 4. Mockup index

All under `../assets/mockups/`; each archetype has `normal` at 80x24 and 120x30 plus the most instructive non-normal state at 80x24. Regions (`#! region`) are ground truth for audits ([audit-protocol.md](audit-protocol.md)).

| Archetype | Files |
|---|---|
| A dashboard | `dashboard/sysmon--normal--80x24.mock`, `--normal--120x30`, `--error--80x24` (stale source), `--toosmall--60x18` |
| B list + detail | `list-detail/prs--normal--80x24.mock`, `--normal--120x30`, `--empty--80x24` |
| C Miller columns | `miller-columns/files--normal--80x24.mock`, `--normal--120x30`, `--error--80x24` |
| D editor | `editor/code--normal--80x24.mock` (Goto which-key), `--normal--120x30` (Space which-key), `--error--80x24` |
| E log viewer | `log-viewer/stream--normal--80x24.mock` (following), `--normal--120x30` (paused), `--empty--80x24` |
| F form/wizard | `form-wizard/setup--normal--80x24.mock`, `--normal--120x30`, `--error--80x24` |
| G command palette | `command-palette/palette--normal--80x24.mock` (over the Fleet demo), `--normal--120x30`, `--empty--80x24` |
| H tree browser | `tree-browser/diskusage--normal--80x24.mock`, `--normal--120x30`, `--busy--80x24` |
| I table explorer | `table-explorer/pods--normal--80x24.mock`, `--normal--120x30`, `--error--80x24` |
| J inline picker | none shipped; generate with `mockkit.py` (see [J](archetypes/j-inline-picker.md)) |
| K chat / agent session | `chat/session--normal--80x24.mock`, `--busy--80x24` (streaming), `--empty--80x24`, `--normal--120x30` (sidebar) |

Preview all of them in one page: `python3 SKILL_DIR/scripts/gallery.py SKILL_DIR/assets/mockups -o gallery.html`.
