# Ratatui (Rust, immediate-mode) — getting-started and design reference

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [1. Versions and install (as of 2026-10-01)](#1-versions-and-install-as-of-2026-10-01) · L23–42 — pinning versions and installing.
- [2. Mental model](#2-mental-model) · L44–50 — first contact: how the framework thinks.
- [3. Minimal app](#3-minimal-app-verified-built-and-driven-in-tmux) · L52–110 — a verified minimal app to copy.
- [4. Project layout](#4-project-layout) · L112–126 — file layout of a real app.
- [5. Layout system](#5-layout-system) · L128–169 — sizing panes, flex and grid, breakpoints.
- [6. Widgets (built in `ratatui::widgets` vs ecosystem)](#6-widgets-built-in-ratatuiwidgets-vs-ecosystem) · L171–186 — which built-in or ecosystem widget to use.
- [7. Focus, keys, mouse](#7-focus-keys-mouse) · L188–193 — key bindings, focus order, mouse.
- [8. Async, timers, performance](#8-async-timers-performance) · L195–211 — background work, streaming, frame rate, flicker.
- [9. Applying our theme tokens](#9-applying-our-theme-tokens) · L213–255 — wiring `export_theme.py` output into styles.
- [10. Color profiles, NO_COLOR, wide characters, inline vs alt screen](#10-color-profiles-no_color-wide-characters-inline-vs-alt-screen) · L257–263 — colour depth, NO_COLOR, wide characters, alt screen vs inline.
- [11. Testing](#11-testing) · L265–276 — unit, snapshot and PTY tests.
- [12. One static frame at a forced size, as ANSI](#12-one-static-frame-at-a-forced-size-as-ansi-what-the-proto-starters-use) · L278–330 — frame mode: one ANSI frame at a forced size (for `compare.py`).
- [13. Pitfalls and anti-patterns](#13-pitfalls-and-anti-patterns-symptom--cause--fix--source) · L332–349 — something renders or behaves wrong (symptom → fix).
- [14. Showcase apps and official examples worth reading](#14-showcase-apps-and-official-examples-worth-reading) · L351–355 — real code worth reading.

Read this when you design, build, theme, test or capture a terminal UI with **Ratatui 0.30** (Rust, crossterm backend). Ratatui is a rendering library, not a framework: no event system, no focus manager, no theme system, no color-profile detection. You own state, input routing and theming.

Source keys: `RT:` https://github.com/ratatui/ratatui/blob/ratatui-v0.30.2/ (tag; `main` examples may use unreleased code) · `TPL:` https://github.com/ratatui/templates/blob/main/. **VERIFIED** = built and run on 2026-10-01 with Rust/Cargo 1.98.1, ratatui 0.30.2, ratatui-core 0.1.2, ratatui-widgets 0.3.2, crossterm 0.29.0, insta 1.48.0: a Fleet demo (list + detail + header/footer bands + modal) whose static frame matches `assets/demo/fleet--normal--80x24.mock` **cell for cell** (char, fg, bg), plus insta tests and a tmux-driven interactive run. `UNVERIFIED` = not confirmed; `derived:` = inference.

## 1. Versions and install (as of 2026-10-01)

**0.30 crate split** (`RT:ARCHITECTURE.md`): apps depend on `ratatui` only; widget-library authors depend on `ratatui-core` (most stable API).

| Crate | Version | Role |
|---|---|---|
| `ratatui` | **0.30.2** (2026-06-19; 0.30.0 was 2025-12-26) | umbrella; re-exports everything; edition 2024, MSRV 1.88.0; MIT |
| `ratatui-core` | 0.1.2 | `Widget`/`StatefulWidget`, `Text/Line/Span`, `Buffer`, layout, style, symbols |
| `ratatui-widgets` | 0.3.2 | built-in widgets |
| `ratatui-crossterm` | 0.1.2 | default backend (crossterm 0.29; feature `crossterm_0_28` exists); `ratatui-termion`, `ratatui-termwiz` 0.1.2, `ratatui-termina` 0.1.0 |
| `ratatui-macros` | 0.7.2 | `constraint!`, `vertical!`, `horizontal!`, `line!`, `span!`, `row!`, `text!` |

Default features: `all-widgets` (includes `widget-calendar` → `time`), `crossterm`, `layout-cache`, `macros`, `underline-color`; optional `serde`, `palette`, `scrolling-regions`, `termion`, `termwiz`, `termina`. Active (main pushed 2026-09-28, 22.8k stars). Source: `RT:Cargo.toml`.

```sh
cargo new app && cd app && cargo add ratatui            # use ratatui::crossterm, do not add crossterm yourself (version skew)
cargo add --dev insta                                   # snapshot tests
cargo generate ratatui/templates                        # optional scaffold (needs user-installed cargo-generate)
```
Examples on `main` "might use unreleased code": read the tag `ratatui-v0.30.2` or branch `latest` (`ratatui-widgets/examples/README.md`).

## 2. Mental model

- **Immediate mode:** each loop iteration `terminal.draw(|frame| …)` re-renders **every** widget into a fresh `Buffer`; Ratatui diffs against the previous buffer and writes only changed cells. Widgets are short-lived values consumed by `render`.
- **Traits:** `Widget::render(self, area: Rect, buf: &mut Buffer)`; `StatefulWidget::render(self, area, buf, &mut State)`. Persistent UI state (`ListState`, `TableState`, `ScrollbarState`: selection, offset) lives **in your app** and is passed in each frame. `&str`, `String`, `Line`, `Text` are widgets themselves.
- **You own the loop and the input:** `event::read()` / `poll(timeout)` from crossterm, your own `App` struct, your own message/action enum. Official state patterns: `RT:examples/concepts/state/README.md`.
- **Coordinates are cells:** `Rect {x, y, width, height}` (`u16`); layout = splitting rects; a style is `fg/bg/modifiers` on cells; `Frame` gives `area()`, `render_widget`, `render_stateful_widget`, `set_cursor_position`.
- **Rendering order = painting order:** later widgets overwrite earlier cells (this is how modals work: `Clear` then draw on top).

## 3. Minimal app (VERIFIED: built and driven in tmux)

```rust
use ratatui::crossterm::event::{self, Event, KeyCode, KeyEventKind};
use ratatui::layout::{Constraint, Layout};
use ratatui::style::Stylize;
use ratatui::text::Line;
use ratatui::widgets::{Block, Paragraph};
use ratatui::{DefaultTerminal, Frame};

#[derive(Default)]
struct App { count: u32, quit: bool }

impl App {
    fn run(&mut self, terminal: &mut DefaultTerminal) -> std::io::Result<()> {
        while !self.quit {
            terminal.draw(|frame| self.render(frame))?;   // immediate mode: redraw everything
            self.handle_events()?;                        // blocks; use event::poll(timeout) to animate
        }
        Ok(())
    }
    fn render(&self, frame: &mut Frame) {
        let [body, footer] = Layout::vertical([Constraint::Fill(1), Constraint::Length(1)]).areas(frame.area());
        frame.render_widget(Paragraph::new(format!("Count: {}", self.count)).centered().block(Block::bordered().title(" Counter ")), body);
        frame.render_widget(Line::from("space +1 • q quit").dim(), footer);
    }
    fn handle_events(&mut self) -> std::io::Result<()> {
        if let Event::Key(key) = event::read()? {
            if key.kind != KeyEventKind::Press { return Ok(()); }   // Windows also reports releases
            match key.code {
                KeyCode::Char(' ') => self.count += 1,
                KeyCode::Char('q') | KeyCode::Esc => self.quit = true,
                _ => {}
            }
        }
        Ok(())
    }
}

fn main() -> std::io::Result<()> {
    ratatui::run(|terminal| App::default().run(terminal))   // raw mode + alt screen + panic hook; restores on exit
}
```
Init API (`RT:ratatui/src/init.rs`): `ratatui::run(f)` (alt screen); `run_with_options(TerminalOptions { viewport }, f)` (**no** alt screen); `init()/try_init()/restore()`. `init*` installs a panic hook that restores the terminal: install `color_eyre` **before** it.

### Lifecycle, signals and exit status

Read in `ratatui-0.30.2/src/init.rs` and `ratatui-core-0.1.2/src/terminal.rs` (`Drop for Terminal`); "Since" from `RT:CHANGELOG.md`. **VERIFIED** = run 2026-10-02 in an isolated `tmux -L` (bash job control for Ctrl+Z), crossterm 0.29.0, signal-hook 0.3.18; `#{alternate_on}` and `stty -a` read after exit. The rules behind it: `../lifecycle.md` LC1, LC3, LC9-LC11.

| Path | Ratatui 0.30.2 | What you add | Since |
|---|---|---|---|
| quit / `Err` | `ratatui::run(f)` = `init()`, `f(&mut terminal)`, `restore()`, return `f`'s result. By hand: keep the loop's result, `restore()`, then return it (a `?` before `restore()` skips it) | `main` returning `Ok(())` → 0, `Err` → 1; any other status: `std::process::ExitCode` after `run` returns | `run` 0.30.0; `init`, `restore`, `try_init`, `try_restore` 0.28.1 |
| panic | `try_init()` first installs a hook that calls `restore()`, then the previous hook → restored, status 101 (VERIFIED) | install `color_eyre` (or your hook) **before** `init`; do not wrap a second restoring hook around `run`/`init` | |
| Ctrl+C | `Event::Key` with `Char('c')` + `CONTROL`; nothing quits by itself (VERIFIED) | handle it; exit 130 after `run` returns | |
| SIGTERM | **no handler** in Ratatui or crossterm: the default action kills the process, no destructor or `restore()` runs → 143 with **raw mode, alt screen and hidden cursor left** (VERIFIED) | `signal_hook::flag::register(SIGTERM, Arc::clone(&flag))`; loop on `event::poll(timeout)` and return when the flag is set; after `run`: `std::process::exit(143)` (VERIFIED: 143, restored) | |
| fallible setup / teardown | **not transactional.** `try_init`: `set_panic_hook()`, `enable_raw_mode()?`, `EnterAlternateScreen?`: an error in the second step leaves raw mode on. `try_restore`: `disable_raw_mode()?` then `LeaveAlternateScreen?`: stops at the first error. `restore()` prints the error to stderr and ignores it. `Terminal`'s `Drop` shows a hidden cursor | after an `Err`, run each teardown step on its own, ignoring individual errors: raw mode off, leave the alt screen, mouse and paste off, show the cursor | |
| `$EDITOR` handoff | nothing built in. Official recipe (https://ratatui.rs/recipes/apps/spawn-vim/): `LeaveAlternateScreen`, `disable_raw_mode`, `Command::new(…).status()`, `EnterAlternateScreen`, `enable_raw_mode`, `terminal.clear()` | stop any input-reader thread or `EventStream` task first (it would read the child's keys); keep the child's result and re-enter before returning it (the recipe's `?` on `status()` skips re-entry: `derived:`); reload data | |
| Ctrl+Z | `Char('z')` + `CONTROL`; no suspend | Unix only (`#[cfg(unix)]`): `ratatui::restore(); signal_hook::low_level::raise(SIGTSTP)?; enable_raw_mode()?; execute!(stdout(), EnterAlternateScreen)?; terminal.clear()?;` (`raise` returns after SIGCONT; VERIFIED: alt screen off while stopped, back and redrawn after `fg`) | |
| Windows | no SIGTSTP or job control; key releases are reported too (§13 #1) | a shell-out key using the handoff sequence | |

## 4. Project layout

Templates (`TPL:cargo-generate.toml`): `hello-world`, `simple` (one `main.rs`, `App { running }`), `simple-async`, `event-driven` (`app.rs event.rs ui.rs main.rs`, event thread), `event-driven-async`, `component` (`action.rs app.rs cli.rs config.rs errors.rs logging.rs tui.rs components/*`, action/component architecture, keybindings in a config file). Generated `Cargo.toml` pins `crossterm 0.29.0`, `ratatui 0.30.2`, `color-eyre 0.6.5`. Recommended for design-system work (derived):

```
app/
├── Cargo.toml                 # ratatui = "0.30.2"; serde_json only if you load themes at runtime
├── src/main.rs                # terminal setup, loop, flags (--static W H for headless frames)
├── src/app.rs                 # App { list: ListState, tab, modal, quit } + on_key()
├── src/ui.rs                  # render(frame, &mut app, &Theme) and one fn per region
├── src/theme_gen.rs           # GENERATED: SKILL_DIR/scripts/export_theme.py ID --target ratatui -o src/theme_gen.rs
├── src/theme.rs               # hand-written Theme { Style per role } built from theme_gen::palette
├── src/snapshots/*.snap       # insta
└── tests/ or #[cfg(test)]     # TestBackend frames
```

## 5. Layout system

Source: `RT:ratatui-core/src/layout/*`, `ratatui-widgets/src/block.rs`.

| Need | API |
|---|---|
| split | `Layout::vertical([c…])` / `horizontal([c…])` / `Layout::new(Direction, c)`; `.margin(n)`, `.spacing(n)` (negative overlaps borders), `.flex(Flex)`; `let [a, b] = layout.areas(rect);` (destructure), `split`, `try_areas`, `rect.layout(&layout)` |
| constraints | `Min(u16)`, `Max(u16)`, `Length(u16)`, `Percentage(u16)`, `Ratio(u32,u32)`, `Fill(u16)` (proportional weight); solved by Cassowary (`kasuari`), cached (`layout-cache`) |
| flex | `Flex::{Legacy, Start (default), End, Center, SpaceBetween, SpaceEvenly, SpaceAround}` |
| rect helpers | `inner(Margin)`, `centered(h_constraint, v_constraint)`, `centered_horizontally/vertically`, `contains(Position)`, `intersection`, `rows()`, `columns()` |
| panel | `Block::bordered()`, `.border_type(Rounded\|Plain\|Double\|Thick\|…)`, `.border_style(s)`, `.style(s)` (fills the inner cells), `.title(Line)`, `.title_bottom`, `.title_alignment`, `.padding(Padding::uniform(n))`, `.merge_borders(MergeStrategy)`, `block.inner(area)` |
| overlay | `Clear` widget, then draw over it (Ratatui has no z-order; later render wins) |
| inline region | `Viewport::Inline(h)` / `Fixed(Rect)` via `TerminalOptions`; `terminal.insert_before(n, …)` writes permanent lines above |

**Archetype recipes** (VERIFIED in the Fleet demo; `th` is the `Theme` of §9):

```rust
fn render(frame: &mut Frame, app: &mut App, th: &Theme) {
    let area = frame.area();
    frame.render_widget(Block::new().style(th.base), area);       // paint bg.base under everything (0 default-bg cells afterwards)
    if area.width < 40 || area.height < 10 {                       // small-terminal guard
        frame.render_widget(Paragraph::new("terminal too small (need 40x10)").alignment(Alignment::Center),
                            area.centered(Constraint::Fill(1), Constraint::Length(1)));
        return;
    }
    let [header, body, message, keybar] = Layout::vertical(
        [Constraint::Length(1), Constraint::Fill(1), Constraint::Length(1), Constraint::Length(1)]).areas(area);
    let [list_area, detail_area] =
        Layout::horizontal([Constraint::Length(32.min(area.width * 2 / 5)), Constraint::Fill(1)]).areas(body);
    render_header(frame, header, app, th);  render_list(frame, list_area, app, th);
    render_detail(frame, detail_area, app, th);  render_keybar(frame, keybar, th);
    if app.modal { render_modal(frame, area, th); }                // last = on top
}
```

| Archetype | Recipe |
|---|---|
| **header + body + footer bands** | `Layout::vertical([Length(1), Fill(1), Length(1)…])` as above. A band = `frame.render_widget(Block::new().style(th.bar), area)` (fills the whole row incl. gaps), then `Line`s on top; right-aligned part = `Layout::horizontal([Fill(1), Length(right.width() as u16)])`, dropped when `l.width` is too small. |
| **list + detail** | the two-way `horizontal` split above; list = `List::new(items).block(titled(..)).highlight_symbol(Line::from(Span::styled(" ❯ ", th.cursor_glyph))).highlight_style(th.row_selected)` rendered with `render_stateful_widget(list, area, &mut app.list)`; detail = `Paragraph::new(lines).block(..)`. Focused pane border `th.border_focus`, other `th.border`. |
| **dashboard grid** | `Layout::vertical([Fill(1); 2])` rows, each `Layout::horizontal([Fill(1); 3])`; `Rect::columns()/rows()` for uniform cells; bars = spans of `"█".repeat(n)` in `ramp[i]` + `"░"` in `th.faint` (or `Gauge`/`LineGauge`/`Sparkline`/`BarChart` widgets); `spacing(-1)` + `merge_borders` to share borders (UNVERIFIED). |
| **modal overlay** | `let r = area.centered(Constraint::Length(40), Constraint::Length(6)); frame.render_widget(Clear, r);` then `Block::bordered().border_style(th.border_focus).style(th.overlay)` and a `Paragraph` in `block.inner(r)`. While `app.modal` is set, `on_key` handles only y/n/enter/esc (focus trap). |
| **titled panel** | Ratatui puts a title right after the corner (`╭Services`): prefix a `─` span to get our `╭─ Services (6) ───╮`: `.title(Line::from(vec![Span::styled("─", border), Span::styled(format!(" {t} "), th.title)]))`. |

## 6. Widgets (built in `ratatui::widgets` vs ecosystem)

| Concept | Built in (0.30.2) | Notes |
|---|---|---|
| panel / title / border | `Block` | `.block(b)` on most widgets |
| text, rich text | `Paragraph` (`wrap(Wrap{trim})`, `scroll((y,x))`, `centered()`), `Text > Line > Span` | no markdown |
| selectable list | `List` + `ListItem` + `ListState` | `highlight_symbol(Line)`, `highlight_style`, `HighlightSpacing`, `ListDirection` |
| table | `Table` + `Row` + `Cell` + `TableState` | `widths(constraints)`, header/footer, row/column/cell selection |
| tabs | `Tabs` | `.select(i)`, `.highlight_style`, `.divider` |
| progress / gauge | `Gauge`, `LineGauge` | `.ratio(f64)` / `.percent(u16)` |
| sparkline / charts | `Sparkline`, `BarChart`, `Chart`, `canvas::Canvas` (`Marker::Braille/Block/HalfBlock/…`) | |
| scroll | `Scrollbar` + `ScrollbarState` | pair with `Paragraph::scroll` or `ListState` |
| overlay helper / fill | `Clear`, `Fill` | render `Clear` before a popup |
| calendar | `calendar::Monthly` | feature `widget-calendar` |

Ecosystem (crates.io, versions as of 2026-10-01): **text input/area** `ratatui-textarea` 0.9.2 (the maintained fork of rhysd/tui-textarea; the original `tui-textarea` 0.7.0 has been inactive since 2024; `tui-textarea-2` 0.13.2 exists), `tui-input` 0.15.5, `tui-prompts` 0.6.8, `edtui` 0.11.7 (vim-like) · **tree** `tui-tree-widget` 0.24.1 · **scroll view** `tui-scrollview` 0.6.8 · **`tui-widgets` 0.7.12** (org umbrella: `tui-popup`, `tui-big-text`, `tui-bar-graph`, `tui-qrcode`, …) · **images** `ratatui-image` 11.1.0 · **log view** `tui-logger` 0.18.3 · **markdown** `tui-markdown` 0.3.10 · **spinner** `throbber-widgets-tui` 0.11.1 · **ANSI → Text** `ansi-to-tui` 8.0.1 · **embedded terminal** `tui-term` 0.3.4 · **effects** `tachyonfx` 0.25.2 · **toasts** `ratatui-toaster` 0.1.4, `tui-overlay` 0.1.2 · **menus** `tui-menu` 0.3.1 · **focus helper** `ratatui-interact` 0.5.3 · **web/WASM** `ratzilla` 0.3.1. Gaps to compose yourself: modal/dialog (`Clear` + `Rect::centered`; or `tui-popup`), toast (timed popup), button, key-hint bar (`Line` of styled `Span`s), command palette (input + `List` in a popup), header/footer bar (`Length(1)` rows).

## 7. Focus, keys, mouse

- **Focus is yours.** An enum (`Focus { List, Detail, Input }`) with `next()` on Tab; route keys to the focused region; set the text cursor with `frame.set_cursor_position(area.origin + offset)`. Pattern: `RT:examples/apps/input-form`. Modal open ⇒ handle only its keys first (VERIFIED in the demo's `on_key`).
- **Events (crossterm 0.29):** `event::read()` blocks, `event::poll(Duration)` waits with timeout; `Event::{Key, Mouse, Resize(w,h), Paste(String), FocusGained, FocusLost}`; `KeyEvent { code, modifiers, kind, … }`. **Always filter `KeyEventKind::Press`** (Windows sends releases; `TPL:simple` comment). 0.30 helpers: `event.is_key_press()`, `as_key_press_event()`.
- **Keybindings and help:** no keymap type or help widget. Keep a `const HINTS: [(&str, &str); N]` (key, label) or an `Action` enum + config (the `component` template) and render hints as `Span`s: key in `th.key` (bold), label in `th.key_desc`, both on `th.bar`; add hints in priority order only while they fit (VERIFIED: `while n > 0 && width(hints[..n]) + 2 > l.width { n -= 1 }`).
- **Mouse:** `execute!(stdout(), EnableMouseCapture)` / `DisableMouseCapture`, `Event::Mouse(MouseEvent { kind, column, row, .. })`; hit-test with `rect.contains(Position { x: column, y: row })` (`RT:examples/apps/mouse-drawing`).

## 8. Async, timers, performance

- **Sync:** `event::poll(tick)` in the loop plus a tick counter, or a thread feeding `std::sync::mpsc` with `AppEvent`s (the `event-driven` template).
- **Async** (`RT:examples/apps/async-github`): `tokio` (macros, rt-multi-thread) + `crossterm` feature **`event-stream`** + `tokio-stream`; `tokio::select! { _ = interval.tick() => terminal.draw(..)?, Some(Ok(ev)) = events.next() => handle(ev) }`; background work via `tokio::spawn` writing to `Arc<RwLock<State>>`.
- **Perf:** only the diff is flushed; `render` runs every frame so keep it allocation-light and I/O-free; `layout-cache` memoizes splits (`Layout::init_cache(NonZeroUsize)`); `scrolling-regions` feature reduces flicker for `insert_before`.

### Debugging and profiling

stdout belongs to the alternate screen, and a `println!` or `dbg!` writes into the frame. Checked 2026-10-02: **docs** = read in the cited page, not run here (no `perf`, no compile of the logging snippet); `derived:` = inference.

| Need | Tool | Command / setting | Notes and gotchas | Source |
|---|---|---|---|---|
| Log to a file | `tracing` + `tracing-subscriber` | `cargo add tracing tracing-subscriber --features tracing-subscriber/env-filter`; `tracing_subscriber::fmt().with_writer(Mutex::new(File::create("app.log")?)).with_ansi(false).with_env_filter(EnvFilter::from_default_env()).init();` then `RUST_LOG=debug cargo run` and `tail -f app.log` | **docs.** `Mutex<File>` as `MakeWriter` is the documented file example; `with_ansi(false)` keeps escape codes out of the log. Initialise it **before** `ratatui::init()`. The official recipe adds XDG paths and a `trace_dbg!` macro | https://ratatui.rs/recipes/apps/log-with-tracing/ ; https://docs.rs/tracing-subscriber/latest/tracing_subscriber/fmt/trait.MakeWriter.html |
| Logs inside the UI | `tui-logger` | `tui_logger::init_logger(log::LevelFilter::Trace)`, `tui_logger::set_default_level(…)`, render `TuiLoggerWidget` in a pane; feature `tracing-support` adds `TuiTracingSubscriberLayer` | **docs.** ratatui-only since v0.10; also logs to a file | https://github.com/gin66/tui-logger |
| Profile a slow draw or event loop | `cargo flamegraph` | `cargo install flamegraph`; `cargo flamegraph --bin app -o flame.svg` (release profile by default; add `[profile.release] debug = true` or `CARGO_PROFILE_RELEASE_DEBUG=true` for symbols); `--root` runs under `sudo` | **docs.** Linux needs `perf` (and `perf_event_paranoid` lowered, or `--root`); with lld / mold add `-Clink-arg=-Wl,--no-rosegment`; macOS uses `xctrace`; `--no-inline` if the post-processing is slow. Open the SVG in a browser | https://github.com/flamegraph-rs/flamegraph#readme |
| **Ctrl-C gotcha** | raw mode | the recording ends when the app exits, so **quit with the app's own quit key** | derived, UNVERIFIED (no `perf` here): in raw mode Ctrl+C is a key event (§3), not SIGINT, so the wrapper never sees it and the recording does not stop. If you must kill it, send `kill -INT` to the `perf` / `flamegraph` process from another pane; `--ignore-status` ("Ignores perf's exit code") lets the SVG still be written | flamegraph README `--ignore-status` |
| Where the cost usually is | read the flame graph for | `render` allocating (`format!`, `Vec`, `String` per row), layout rebuilt each frame, big `Paragraph` / `Table` re-wrapped, work done in the draw closure | derived: §8: `render` runs every frame, keep it allocation-light and I/O-free; `layout-cache` memoizes splits; move work to a thread or task and read state in `render` |  §8 |

## 9. Applying our theme tokens

Ratatui has **no theme system**; the idiom is a struct of `Style`s per UI role (`RT:examples/apps/demo2/src/theme.rs`, gitui's `Theme`). `python3 SKILL_DIR/scripts/export_theme.py ID --target ratatui -o src/theme_gen.rs` generates (VERIFIED: compiles; the `const THEME` evaluates in const context):

```rust
use ratatui::style::{Color, Modifier, Style};
pub mod palette {           // one const per token: bg.base → BG_BASE, fg.on-accent → FG_ON_ACCENT, selection.inactive.bg → SELECTION_INACTIVE_BG
    pub const BG_BASE: Color = Color::Rgb(30, 30, 46);   pub const FG_DEFAULT: Color = Color::Rgb(205, 214, 244);
    pub const BORDER_FOCUS: Color = Color::Rgb(180, 190, 254);   pub const SELECTION_BG: Color = Color::Rgb(59, 61, 79);  // … every token
}
pub struct Theme { pub root: Style, pub content: Style, pub title: Style, pub muted: Style, pub faint: Style, pub borders: Style,
    pub borders_focused: Style, pub selected: Style, pub selected_inactive: Style, pub tabs: Style, pub tabs_selected: Style,
    pub statusbar: Style, pub link: Style, pub success: Style, pub warning: Style, pub error: Style, pub info: Style,
    pub chip_success: Style, /* chip_warning, chip_error, chip_info */ pub key_binding: KeyBinding /* {key, description} */ }
pub const THEME: Theme = Theme { root: Style::new().fg(palette::FG_DEFAULT).bg(palette::BG_BASE), /* … */ };
```
The generated `Theme` covers common roles; for the rest (bar band, brand, ramp, overlay, buttons, cursor glyph, bg-only selection) build your own `Theme` from `theme_gen::palette::*` (VERIFIED, 0 cells differ from the mock):

```rust
pub struct Theme { pub base: Style, pub text: Style, pub muted: Style, pub faint: Style, pub title: Style,
    pub border: Style, pub border_focus: Style, pub row_selected: Style, pub cursor_glyph: Style,
    pub ok: Style, pub warn: Style, pub err: Style, pub bar: Style, pub brand: Style, pub tab_active: Style, pub tab_inactive: Style,
    pub key: Style, pub key_desc: Style, pub overlay: Style, pub button_primary: Style, pub button: Style, pub ramp: [Style; 3] }
impl Theme {
    pub fn from_palette() -> Self {
        use crate::theme_gen::palette as p;
        let fg = |c: Color| Style::new().fg(c);
        Self {
            base: Style::new().fg(p::FG_DEFAULT).bg(p::BG_BASE),
            title: fg(p::FG_TITLE).add_modifier(Modifier::BOLD),
            border: fg(p::BORDER_DEFAULT), border_focus: fg(p::BORDER_FOCUS),
            row_selected: Style::new().bg(p::SELECTION_BG).add_modifier(Modifier::BOLD),   // bg only: see pitfall 10
            bar: Style::new().fg(p::STATUSBAR_FG).bg(p::STATUSBAR_BG),
            key: fg(p::KEYHINT_KEY).bg(p::STATUSBAR_BG).add_modifier(Modifier::BOLD), key_desc: fg(p::KEYHINT_DESC).bg(p::STATUSBAR_BG),
            overlay: Style::new().fg(p::FG_DEFAULT).bg(p::BG_OVERLAY),
            button_primary: Style::new().fg(p::FG_ON_ACCENT).bg(p::ACCENT_PRIMARY).add_modifier(Modifier::BOLD),
            ramp: [fg(p::RAMP_LOW), fg(p::RAMP_MID), fg(p::RAMP_HIGH)],
            // … abridged: every field must be set (text/muted/faint/ok/warn/err/brand/tabs/cursor_glyph/button follow the same pattern)
        }
    }
}
```
**Runtime alternative** (VERIFIED, ~35 lines, `serde_json::Value` only, no derive): read `<dir>/<id>.json` and `_tokens.json`; for each token in `_tokens.json["tokens"]` follow `theme["tokens"][tok]` (a `#hex`, else a `palette` name) else the tier-2 `fallback` chain; build `HashMap<String, Color>`; `Theme::new(&tokens)`. Output was byte-identical to the generated-consts build. Use it for theme switching at startup. **Remember to paint:** `Block::new().style(th.base)` over the whole frame, or cells you do not write show the terminal's own background. Optional: `ratatui` feature `serde` serializes `Style`/`Color` if you want themes as files (`ratatui/Cargo.toml`). Closest community precedent: `opaline` (https://github.com/hyperb1iss/opaline; palette → tokens → styles in TOML).

## 10. Color profiles, NO_COLOR, wide characters, inline vs alt screen

- **No profile detection and no downgrading** (grep of 0.30.2 sources: no `NO_COLOR`, no `COLORTERM`). `Color::Rgb` is written as `38;2;r;g;b` even on a 256-color terminal. Choose per terminal yourself: truecolor `Color::Rgb`, 256 `Color::Indexed(n)`, 16 named colors or `Reset`; the theme's `ansi16` map (`../color-tokens.md`) gives the 16-color choice. Community: `termprofile` (detection + downsampling). Inside tmux, truecolor passes through (VERIFIED: `38;2;…` in `capture-pane -e` without any env tweak), unlike Charm apps.
- **NO_COLOR is honored by crossterm, not by Ratatui:** `crossterm::style::Colored`'s `Display` returns an empty string when `NO_COLOR` is set and non-empty (`crossterm-0.29.0/src/style/types/colored.rs`). VERIFIED in tmux: `NO_COLOR=1` removed **all** SGR (216 color SGR → 0; bold/reverse also vanished, derived cause: the emptied color SGR becomes a bare `ESC[m` reset). Consequence: selection and focus must survive without color (`highlight_symbol(" ❯ ")`, glyph + word for severity). To keep modifiers under NO_COLOR take over the policy: `if env NO_COLOR non-empty { ratatui::crossterm::style::force_color_output(true); /* then strip fg/bg from your Styles, keep modifiers */ }` (the function compiles and is exported; the strip step is UNVERIFIED).
- **Wide chars:** `unicode-width`; the Buffer stores the glyph in the first cell and a hidden blank after it (VERIFIED CJK/emoji; skip the trailing cells when serializing, §12). Known open issue #1271 (unicode width). Prefer single-cell glyphs (`../visual-vocabulary.md` V1).
- **Hyperlinks:** no API; OSC 8 in cell symbols breaks width math (issue #902); `RT:examples/apps/hyperlink` writes 2-char chunks as a workaround.
- **Viewport:** `ratatui::run` = alt screen (`Viewport::Fullscreen`); `Viewport::Inline(h)` renders below the prompt without alt screen; `insert_before` prints permanent lines above it (`RT:examples/apps/inline`).

## 11. Testing

`TestBackend::new(w, h)` + `Terminal::new(backend)` + `terminal.draw(..)`; then `terminal.backend()` (Display = plain-text rows), `.buffer()`, `assert_buffer_lines([...])`, `assert_cursor_position`; `Buffer::with_lines`, `buf[(x, y)]` → `Cell` (`.symbol()`, `.fg`, `.bg`, `.modifier`). Widget unit test: `widget.render(area, &mut Buffer::empty(area))`.

```rust
#[test] fn frame_80x24_plain() { insta::assert_snapshot!(render_static(80, 24, false, &theme()).backend()); }   // plain text grid
#[test] fn selected_row_has_selection_bg() {
    let t = render_static(80, 24, false, &theme());
    assert_eq!(t.backend().buffer()[(5, 2)].bg, Color::Rgb(0x3b, 0x3d, 0x4f));          // selection.bg of catppuccin-mocha
}
```
**insta (VERIFIED):** first run of a new/changed snapshot **fails** and writes `src/snapshots/<crate>__tests__<name>.snap.new`; accept with `INSTA_UPDATE=always cargo test` (verified: "updated snapshot", next run green) or `cargo insta review` (needs the user-installed `cargo-insta`, UNVERIFIED). Plain-text snapshots do not capture style: assert key cells' `fg/bg/modifier`, or snapshot `buffer_to_ansi` output.

## 12. One static frame at a forced size, as ANSI (what the proto-starters use)

No crate exports a Buffer to ANSI (crates.io search; `ansi-to-tui` goes the other way). Render into a `TestBackend` and serialize cells (VERIFIED: `cargo run -- --static 80 24 [--modal] > frame.ansi`; sizes 30x8, 40x12, 60x16, 80x24, 120x30, 170x40 give exactly w×h cells and 0 default-bg cells; the 80x24 output has **0 differing cells** against `render_mockup.py fleet--normal--80x24.mock`):

```rust
pub fn render_static(w: u16, h: u16, modal: bool, th: &Theme) -> Terminal<TestBackend> {
    let mut app = App::new(); app.modal = modal;                 // pre-set state for empty/busy/error/modal variants
    let mut terminal = Terminal::new(TestBackend::new(w, h)).unwrap();
    terminal.draw(|f| render(f, &mut app, th)).unwrap();
    terminal
}
pub fn buffer_to_ansi(buf: &Buffer) -> String {
    let mut out = String::new();
    let a = buf.area;
    for y in a.top()..a.bottom() {
        let mut last: Option<(Color, Color, Modifier)> = None;
        let mut skip = 0usize;
        for x in a.left()..a.right() {
            let cell = &buf[(x, y)];
            if skip > 0 { skip -= 1; continue; }                           // trailing cells of a wide glyph
            let key = (cell.fg, cell.bg, cell.modifier);
            if last != Some(key) {
                out.push_str("\x1b[0");
                sgr_color(&mut out, cell.fg, true);
                sgr_color(&mut out, cell.bg, false);
                for (f, c) in [(Modifier::BOLD,1),(Modifier::DIM,2),(Modifier::ITALIC,3),(Modifier::UNDERLINED,4),(Modifier::SLOW_BLINK,5),
                               (Modifier::RAPID_BLINK,6),(Modifier::REVERSED,7),(Modifier::HIDDEN,8),(Modifier::CROSSED_OUT,9)] {
                    if cell.modifier.contains(f) { let _ = write!(out, ";{c}"); }
                }
                out.push('m'); last = Some(key);
            }
            out.push_str(cell.symbol());
            let w = Span::raw(cell.symbol()).width();                      // unicode-width, the rule Ratatui uses
            if w > 1 { skip = w - 1; }
        }
        out.push_str("\x1b[0m\n");
    }
    out
}
fn sgr_color(out: &mut String, c: Color, fg: bool) {      // Gray → 37, White → 97 (matches crossterm); DarkGray → 90
    let b = if fg { 30 } else { 40 };
    let code = match c {
        Color::Reset => return,
        Color::Black => 0, Color::Red => 1, Color::Green => 2, Color::Yellow => 3, Color::Blue => 4, Color::Magenta => 5, Color::Cyan => 6, Color::Gray => 7,
        Color::DarkGray => 60, Color::LightRed => 61, Color::LightGreen => 62, Color::LightYellow => 63, Color::LightBlue => 64,
        Color::LightMagenta => 65, Color::LightCyan => 66, Color::White => 67,
        Color::Indexed(i) => { let _ = write!(out, ";{};5;{}", b + 8, i); return; }
        Color::Rgb(r, g, bl) => { let _ = write!(out, ";{};2;{};{};{}", b + 8, r, g, bl); return; }
    };
    let _ = write!(out, ";{}", b + code);
}
```
Notes: `underline_color` is ignored (add `58;2;r;g;b`); OSC 8 inside symbols passes through; the output is truecolor (for 256/16-color variants map `Color::Rgb` in `sgr_color` or build the theme with `Indexed`/named colors; not implemented here); plain text: `format!("{}", terminal.backend())` or iterate `symbol()`. Verify with `uv run SKILL_DIR/scripts/ansi_grid.py frame.ansi --cols 80 --rows 24`. **Real-runtime capture** (resize, keys): `SKILL_DIR/scripts/capture_tui.sh -s 80x24 -s 120x30 -k j -k r -o out -- ./target/release/app` (no TERM trick needed for Ratatui). Alternative, UNVERIFIED: `Terminal::with_options(CrosstermBackend::new(Vec<u8>), TerminalOptions { viewport: Viewport::Fixed(rect) })` (real escape stream, cursor-movement based).

## 13. Pitfalls and anti-patterns (symptom → cause → fix → source)

| # | Symptom | Cause | Fix | Source |
|---|---|---|---|---|
| 1 | Every key fires twice / acts on release (Windows) | crossterm reports `Press` and `Release` | `if key.kind != KeyEventKind::Press { return }` | `TPL:simple` |
| 2 | Shell left in raw mode / garbled after a panic | `init()` called before another panic hook was installed, or `restore()` skipped | use `ratatui::run`; install `color_eyre` before `init` | `RT:ratatui/src/init.rs` |
| 3 | List selection/scroll resets every frame | `ListState`/`TableState` created inside `render` | keep state in `App`, pass `&mut state` | `RT:examples/concepts/state` |
| 4 | Popup shows underlying text through it | no `Clear` | `frame.render_widget(Clear, r)` before the popup | `RT:ratatui-widgets/src/clear.rs` |
| 5 | Animation frozen until a key is pressed | blocking `event::read()` | `event::poll(tick)` or async `EventStream` | `RT:examples/apps/async-github` |
| 6 | Example code fails to compile | copied from `main` against the crates.io release | use tag `ratatui-v0.30.2` / branch `latest` | `ratatui-widgets/examples/README.md` |
| 7 | Misaligned rows after adding a link/escape | ANSI escapes inside `Span`/symbols break width math (#902) | style via `Style`; convert existing ANSI with `ansi-to-tui` | issue #902 |
| 8 | Build error `expected crossterm::… found crossterm::…` | two crossterm versions | `use ratatui::crossterm::…`, no direct dependency | `RT:ratatui/src/lib.rs` |
| 9 | Colors wrong in 256-color terminals / `NO_COLOR` makes the UI unreadable | no downgrading; crossterm strips all SGR under `NO_COLOR` (VERIFIED) | pick `Rgb`/`Indexed`/named by capability yourself; glyph-based selection/severity | §10 |
| 10 | Selected row loses its per-span colors (green glyph becomes plain text color) | `highlight_style` is patched over every cell of the row, so an `fg` there overrides span colors (VERIFIED: with `fg` set, `38;2;166;227;161` vanished from the row) | `highlight_style` = `bg` (+bold) only; give selected spans their colors when building the item | VERIFIED |
| 11 | Terminal background shows inside panels / around text | unwritten cells keep the terminal bg; `Block` only paints its own area | `frame.render_widget(Block::new().style(th.base), area)` first; bands: `Block::new().style(th.bar)` before the line | VERIFIED |
| 12 | Title hugs the corner (`╭Services────╮`) | `Block::title` starts at x+1 | prefix `Span::styled("─", border)` and pad the title with spaces | VERIFIED |
| 13 | Wide glyphs shift serialized rows by one | the cell after a wide symbol is a hidden blank | skip `width-1` cells (as `buffer_to_ansi` does) | VERIFIED |
| 14 | `cargo test` fails right after a UI change | insta new/changed snapshot → `.snap.new` | `INSTA_UPDATE=always cargo test` after reviewing the diff | VERIFIED |

## 14. Showcase apps and official examples worth reading

Real-world Ratatui apps: **gitui** (v0.28.1; tabbed workspace: `[tab bar | body | command bar]`, list + diff panes, popups for everything else; `RT` 0.30 + crossterm 0.29), **yazi** (v26.9.1; Miller columns `ratio [1,4,3]`, tabs, which-key, task overlay; `ratatui` fork + tokio + Lua), **helix** (in-tree `helix-tui` ratatui fork; editor + statusline + pickers/popups), **atuin** (shell-history search), **bottom** (system monitor), **television** (fuzzy finder), **openai/codex** (`codex-rs` TUI), **trippy**, **csvlens**. Lists: https://ratatui.rs/showcase/ and https://github.com/ratatui/awesome-ratatui (contents not fetched, UNVERIFIED). For the layout/key conventions of these apps see `../exemplars.md`.

Official examples at tag `ratatui-v0.30.2` (`RT:examples/apps/`): `demo2` + `demo` (dashboards; `demo2/src/theme.rs` is the Theme-struct pattern), `input-form` (focus enum + cursor), `popup` (`Clear` + centered rect), `todo-list` and `table` (stateful widgets, scrollbar), `async-github` (tokio `EventStream`), `inline` (`Viewport::Inline` + `insert_before`), `custom-widget` / `advanced-widget-impl` (implementing `Widget`), `constraint-explorer`, `constraints`, `flex` (layout solver), `canvas`, `chart`, `gauge`, `weather` (BarChart), `scrollbar`, `hyperlink` (OSC 8 workaround), `mouse-drawing`, `panic`, `tracing`, `user-input`, `color-explorer`, `modifiers`, `widget-ref-container`; `examples/concepts/state` (seven state-management patterns); `ratatui-widgets/examples/*` (`cargo run -p ratatui-widgets --example <name>`: barchart, block, calendar, canvas, chart, collapsed-borders, gauge, line-gauge, list, logo, paragraph, scrollbar, shadow, sparkline, table, tabs).
