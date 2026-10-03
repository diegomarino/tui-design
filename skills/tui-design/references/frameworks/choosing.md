# Choosing a TUI framework

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [1. Identity table](#1-identity-table) · L13–25 — what each framework is (language, licence, maturity).
- [2. Behavior table (what matters for our design / audit loop)](#2-behavior-table-what-matters-for-our-design--audit-loop) · L27–40 — focus, mouse, testing, one-frame capture, color depth.
- [3. Pick X when…](#3-pick-x-when) · L42–59 — picking a framework from the project's situation.
- [4. Constraint lookup](#4-constraint-lookup) · L61–72 — a hard constraint (inline mode, startup time, language) decides.

Read this when the user has not fixed a framework, or when you must justify one. Decide in this order: (1) the language/runtime of the existing code, (2) one-shot script vs persistent app, (3) the widget set you need (section 3), (4) how you will test and capture frames (section 2). The runtime contract (cleanup on every exit path, `$EDITOR` handoff, resize, logs, non-blocking I/O) and the test pyramid are framework-independent: [../lifecycle.md](../lifecycle.md).

Versions as of 2026-10-01; re-check with `SKILL_DIR/scripts/check_versions.py --online`. `VERIFIED` = run or read in the release source; `UNVERIFIED` = not confirmed; `derived:` = inference.

## 1. Identity table

| | Language / runtime | Model | Layout system | Widget richness | Version (date) · maturity | Notable apps |
|---|---|---|---|---|---|---|
| **Ink** | TypeScript/JS, Node >=22, React >=19.2 | Retained React tree; whole-frame string re-render each commit; inline by default | Yoga flexbox via `<Box>` props (`flexDirection`, `flexGrow`, `width="40%"`, `gap`, `borderStyle`) | Low in core (`Box`, `Text`, `Static`, `Spacer`, `Transform`); @inkjs/ui adds 13 small components; no table, tree, tabs, modal, scroll view | **7.1.1** (2026-07-16); very active, 40k stars. @inkjs/ui 2.0.0 and ink-testing-library 4.0.0 are dormant (2024) but work | Claude Code, Gemini CLI, GitHub Copilot CLI, Cloudflare Wrangler, Shopify CLI, Prisma |
| **Textual** | Python >=3.9, asyncio, Rich | Retained widget DOM; async message pump; reactive attributes; alt screen by default, `inline=True` available | TCSS: `layout: vertical/horizontal/grid`, `dock`, `fr`/`%`/`auto` units, layers, breakpoints | **Highest**: 40+ built-ins incl. `DataTable`, `Tree`, `TextArea`, `Tabs`, `Select` overlay, `Markdown`, command palette, toasts, `ModalScreen` | **8.2.8** (2026-06-30); very active, 37k stars | Posting, Harlequin, Memray (live mode), Toad, mistral-vibe, Dolphie |
| **Bubble Tea** (+Bubbles, Lip Gloss, Huh) | Go (`go 1.26.0`) | Elm architecture: `Init/Update/View`; messages and Cmds; string `View`; cell-diff renderer; inline by default | **No layout engine**: Lip Gloss string composition (`JoinHorizontal/Vertical`, `Place`, `Width`), v2 compositor layers for overlays | Medium: Bubbles `list`, `table`, `textinput`, `textarea`, `viewport`, `spinner`, `progress`, `help`, `filepicker`, `tree`…; Huh forms. No tabs/modal/grid | **v2.0.10** (2026-09-24), Bubbles v2.2.1, Lip Gloss v2.0.6, Huh v2.0.3; module path `charm.land/…/v2`; 45k stars, "18,000+" dependents | chezmoi, gh-dash, Glow, Mods, Superfile, MinIO mc, AWS eks-node-viewer |
| **Ratatui** | Rust (MSRV 1.88, edition 2024) + crossterm | Immediate mode: redraw every widget each frame into a `Buffer`, diff, flush; no event system; app owns state | Cassowary constraints: `Layout::vertical/horizontal` + `Constraint::{Length,Min,Max,Percentage,Ratio,Fill}`, `Flex`, `Rect` helpers | Medium: ~12 built-ins (`Block`, `Paragraph`, `List`, `Table`, `Tabs`, `Gauge`, `Sparkline`, `BarChart`, `Chart`, `Canvas`, `Scrollbar`, `Calendar`); text input, tree, popup, markdown via crates | **0.30.2** (2026-06-19); **pre-1.0, breaking minors**; 22.8k stars | gitui, yazi, atuin, bottom, television, openai/codex (`codex-rs`), trippy, csvlens |
| **gum** | Go binary (CLI) | One-shot shell components; UI on stderr, result on stdout; exit codes 0/1/130/124 | None: `style`, `join` compose blocks | 13 commands: `choose confirm file filter format input join pager spin style table write log` | **v2.0.2** (2026-09-24); 24k stars | Shell scripts, commit wizards, README one-liners |
| **tview** | Go on `tcell` | Retained primitives; `Application`; callbacks; `QueueUpdateDraw` from goroutines | `Flex`, `Grid`, `Pages`, `Frame` | High out of the box: `TextView`, `TextArea`, `InputField`, `DropDown`, `Checkbox`, `Button`, `List`, `Table`, `TreeView`, `Form`, `Modal`, `Image` | v0.42.0 (first semver tag 2025-08-27); last push 2026-08-11; MIT | K9s (uses a `derailed/tview` fork), docui |
| **urwid** | Python >=3.9 | Retained widget tree; `MainLoop`; signals; event loops: Select, asyncio, Trio, Tornado, Twisted, GLib, ZMQ | `Pile`, `Columns`, `GridFlow`, `Padding`, `Filler`, `Overlay`, `Frame`; flow/box/fixed sizing | Medium: `Text`, `Edit`, `Button`, `CheckBox`, `RadioButton`, `ListBox`, `TreeListBox`, `ProgressBar`, `BarGraph`, `BigText`, `Scrollable`, `LineBox`, `PopUpLauncher`, `Terminal` | **4.2.4** (2026-10-01); very active; **LGPL-2.1** | pudb, mitmproxy, toot, alot |
| **blessed (Python)** | Python >=3.8 | Imperative terminal toolkit (`Terminal`): styling, cursor, input, width math; **no widgets** | Manual (`move_xy`) | None (`LineEditor` for input) | **1.50.0** (2026-09-14); active | Utilities and examples |
| **blessed (Node)** | Node | Retained DOM-like widget tree | Absolute/percent per element | Many widgets (+`blessed-contrib` charts) | **Abandoned**: chjj/blessed last commit 2016-01-04, npm 0.1.81 (2015). Forks: `neo-blessed` 0.2.0 (2018), `reblessed` 0.2.1 (2023), `@unblessed/node` 1.0.0-alpha.23 (2025-12) | Legacy dashboards (UNVERIFIED specifics) |

## 2. Behavior table (what matters for our design / audit loop)

| | Focus and mouse | Testing | **One frame at a forced size as ANSI** (difficulty: recipe) | Color depth / NO_COLOR |
|---|---|---|---|---|
| **Ink** | `useFocus` + Tab cycling; **no mouse** in core (parse SGR yourself) | `ink-testing-library` (`lastFrame()`, `stdin.write`; fixed 100 cols), `node:test` | **Easy**: `renderToString(tree, {columns})` sync; root `Box height` explicit; set `TERM=dumb FORCE_COLOR=3`. Fake-stdout `render()` when hooks matter | chalk 5 levels; `FORCE_COLOR` is a minimum; **NO_COLOR not honored** (VERIFIED) |
| **Textual** | Full focus system; mouse on by default; kitty keyboard | Pilot (`run_test`), `pytest-textual-snapshot` (SVG) | **Medium**: built-ins export SVG only; ANSI needs the private compositor recipe (VERIFIED, pin the version) | Rich `color_system`; **NO_COLOR honored**; converts ANSI to truecolor unless `ansi_color=True` |
| **Bubble Tea** | No focus manager (app-owned); mouse via `View.MouseMode` + `MouseClickMsg…`; hit-test with Lip Gloss `Compositor` | pure `Update(WindowSizeMsg)` + `View().Content` + `x/exp/golden`; `teatest/v2` (untagged) for flows | **Easy**: `m.Update(tea.WindowSizeMsg{…})`, `m.View().Content` is truecolor ANSI, downsample with `colorprofile.Writer`; `Init` Cmds are not run (VERIFIED) | `colorprofile` detection; `NO_COLOR` on a TTY → ASCII profile; `CLICOLOR_FORCE` wins when piped |
| **Ratatui** | App-owned focus enum; mouse via crossterm `EnableMouseCapture` + `Rect::contains` | `TestBackend` + `assert_buffer_lines`; `insta` snapshots | **Easy-medium**: render to `TestBackend`, then ~40 lines of `buffer_to_ansi` (no built-in exporter; VERIFIED) | **No detection, no NO_COLOR**: you emit what you set |
| **gum** | Single widget at a time; mouse n/a | shell scripts; tmux | **Static commands easy** (`CLICOLOR_FORCE=1 COLORTERM=truecolor gum style …`); **interactive need tmux** `capture-pane -p -e` (VERIFIED) | `colorprofile`; `CLICOLOR_FORCE` beats `NO_COLOR` when piped (observed) |
| **tview** | `Application.SetFocus`, `SetInputCapture`; mouse `Application.EnableMouse(true)` (source read) | none in repo; `tcell.NewSimulationScreen` + `GetContents()` | **Medium**: simulation screen then serialize cells yourself (derived; UNVERIFIED) | via `tcell` (UNVERIFIED) |
| **urwid** | `focus_position`; mouse `MainLoop(handle_mouse=True)` default (source read) | `widget.render((cols, rows)).text`; HTML `screenshot_init/collect` | **Easy for text**; attributes need `canvas.content()` (UNVERIFIED) | 16/88/256/24-bit palette entries |
| **blessed (py)** | none (no widgets); `inkey()` returns keys and `MOUSE_*` | `Terminal(stream=StringIO(), force_styling=True)` | **Easy** (VERIFIED: force styling into a `StringIO`) | Honors `NO_COLOR`/`FORCE_COLOR`; `number_of_colors` settable |

Universal fallback for **any** binary, including ones in this table: `SKILL_DIR/scripts/capture_tui.sh -s 80x24 -s 120x30 -- CMD` (private tmux server, `capture-pane -p -e`).

## 3. Pick X when…

| Pick | When (decisive factors) | Watch out for | Startup (first frame) |
|---|---|---|---|
| **Textual** | Python; you want tables, trees, text areas, tabs, modals, command palette, mouse and theming **without building them**; also want to serve the app in a browser (`textual serve`); you need the best snapshot and Pilot testing | ANSI frame capture relies on a private API (pin the version); macOS Terminal.app is poor (Cmd/Option keys never arrive) | **~89 ms** alt screen, ~90 ms inline (8.2.8, Python 3.14; measured) |
| **Ink** | The team writes TypeScript/React; agent/chat-style CLIs with streaming text and a few widgets; you want to reuse React patterns (hooks, Suspense); inline apps | No mouse, no scroll view, no table/tree/modal in core: compose them; keep the live region shorter than `rows`; @inkjs/ui is dormant | **~119 ms** (7.1.1, React 19.3, Node 26; measured) |
| **Bubble Tea** | Go; single static binary; composable models; forms (Huh); you accept building layout by string composition | **v1 vs v2**: most online code is v1 (`github.com/charmbracelet/...`, `View() string`); target `charm.land/…/v2`. No focus manager; bubbles do not adapt to dark/light automatically in v2 | **~24 ms** (v2.0.10; measured) |
| **Ratatui** | Rust; maximum control and performance; large data views; you are fine owning the event loop, focus and state architecture | Pre-1.0 (API drift: use the release tag, not `main` examples); no NO_COLOR handling; no help/keymap widget; hyperlinks need a workaround | **~5 ms** (0.30.2, release build; measured) |
| **gum** | **Shell-script UIs, not persistent apps**: pick one, confirm, input, filter, spinner, styled output in a script or alias; output must pipe | Each call is a separate mini-program: no multi-pane layout, no shared state, no custom keys | **~41 ms** per command (`gum choose`, 2.0.1; measured); a script pays it per call |
| **Bubble Tea + Huh only** | A multi-step prompt wizard in Go | `form.(*huh.Form)` type assertion when embedding in Bubble Tea | ≈ Bubble Tea (`derived:`, not measured) |
| **tview** | Go; admin/ops tools with forms, tables, trees and modals out of the box; callback style preferred over Elm | No tests in the repo; styling via the global `tview.Styles`; one global theme object, not per-widget tokens | not measured; `derived:` Go binary, same class as Bubble Tea |
| **urwid** | Python; you need many event-loop integrations (Twisted, Trio, GLib, ZMQ), long-standing API stability, or LGPL is acceptable; flow/box sizing model | LGPL-2.1; no OSC 8 hyperlink support found; fewer ready-made widgets than Textual (derived) | not measured; pays Python start-up plus its imports (`derived:`) |
| **blessed (Python)** | Python scripts needing precise cursor/input control, width math, OSC 8 links, kitty keyboard; no widget layer wanted | You write every widget; for dashboards use Textual | not measured |
| **blessed (Node)** | **Never for new work** (abandoned 2016). If you meet it, migrate to Ink, or to the alpha fork `@unblessed/node` at your own risk || n/a |

**Startup column**: `exec` to the first frame's text on a pseudo-terminal (80x24, cursor-position and device-attribute queries answered), hello-world app, warm cache, median of 10 runs, Apple M5 Max, macOS 26, 2026-10-02. Same harness: `printf` 4 ms, fzf 0.74.4 `--height 10` 25 ms. Your imports, config and first data load add to these; a cold cache or a slower machine is slower. Why it matters: a summon–choose–exit tool has ≤ 100 ms to first frame ([archetype J](../archetypes/j-inline-picker.md)); Go, Rust and gum fit, Ink and Textual spend most of it before your code runs, so give `--version`, `completion` and `init` a path that does not import the UI. Measure your own build: `hyperfine --warmup 3 'APP --version'` for the import cost; first-frame timing needs a PTY.

Defaults when nothing else decides (derived: language fit and widget richness): Python → **Textual**; TypeScript → **Ink**; Go app → **Bubble Tea**; Go admin tool with many ready widgets → **tview**; Rust → **Ratatui**; shell script → **gum**.

## 4. Constraint lookup

| Constraint | Answer |
|---|---|
| Need mouse support from day one | Textual (default on), Bubble Tea (mouse msgs + Lip Gloss `Compositor.Hit`), tview, urwid. Not Ink (none), Ratatui (DIY via crossterm) |
| Need a dropdown overlay or text area built in | Textual (`Select`, `TextArea`); tview (`DropDown`, `TextArea`). Bubble Tea has `textarea` but no dropdown overlay |
| Need golden-frame tests with colors | Bubble Tea (`x/exp/golden`, ANSI preserved), Ratatui (`insta` on the buffer), Ink (`renderToString` + `TERM=dumb FORCE_COLOR`), Textual (ANSI helper or SVG snapshots) |
| Need to prototype a static mock at an exact size for the gallery | Any ("one frame" column); starters in `assets/proto-starters/<framework>/` |
| Must honor `NO_COLOR` automatically | Textual, blessed (py), Bubble Tea (TTY case). Ink and Ratatui: add it yourself |
| Windows support matters | Ratatui works through crossterm (filter `KeyEventKind::Press`); Textual `inline=True` is **not** supported on Windows; Bubble Tea, tview, urwid, Ink: UNVERIFIED here |
| Inline (non-fullscreen) apps | Ink (default), Bubble Tea (default), gum, Textual (`run(inline=True)`), Ratatui (`Viewport::Inline`) |
| LLM-generated code is likely to be stale | Bubble Tea (v1 vs v2), Ink (`create-ink-app` scaffolds Ink 4/React 18; master readme documents unreleased features), Ratatui (`main` examples vs crates.io release) |
