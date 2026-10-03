# Textual (Python, TCSS, retained widget DOM) — getting-started and design reference

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [1. Versions and install (as of 2026-10-01)](#1-versions-and-install-as-of-2026-10-01) · L23–38 — pinning versions and installing.
- [2. Mental model](#2-mental-model) · L40–46 — first contact: how the framework thinks.
- [3. Minimal app](#3-minimal-app-verified-headless-with-run_test-and-pilot) · L48–101 — a verified minimal app to copy.
- [4. Project layout](#4-project-layout) · L103–105 — file layout of a real app.
- [5. Layout system](#5-layout-system) · L107–135 — sizing panes, flex and grid, breakpoints.
- [6. Widgets](#6-widgets) · L137–152 — which built-in or ecosystem widget to use.
- [7. Focus, keys, actions, screens, mouse](#7-focus-keys-actions-screens-mouse) · L154–161 — key bindings, focus order, mouse.
- [8. Async, timers, performance](#8-async-timers-performance) · L163–181 — background work, streaming, frame rate, flicker.
- [9. Applying our theme tokens](#9-applying-our-theme-tokens) · L183–256 — wiring `export_theme.py` output into styles.
- [10. Color depth, NO_COLOR, wide characters, links, screens](#10-color-depth-no_color-wide-characters-links-screens) · L258–265 — colour depth, NO_COLOR, wide characters, alt screen vs inline.
- [11. Testing](#11-testing) · L267–281 — unit, snapshot and PTY tests.
- [12. One static frame at a forced size, as ANSI](#12-one-static-frame-at-a-forced-size-as-ansi-what-the-proto-starters-use) · L283–315 — frame mode: one ANSI frame at a forced size (for `compare.py`).
- [13. Pitfalls and anti-patterns](#13-pitfalls-and-anti-patterns-symptom--cause--fix--source) · L317–336 — something renders or behaves wrong (symptom → fix).
- [14. Showcase apps and official examples worth reading](#14-showcase-apps-and-official-examples-worth-reading) · L338–355 — real code worth reading.

Read this when you design, build, theme or capture a terminal UI with **Textual** (Python; Rich underneath; also runs in a browser).

Source keys: `TX:` https://github.com/Textualize/textual/blob/main/ (docs also at https://textual.textualize.io/) · `PTS:` https://github.com/Textualize/pytest-textual-snapshot/blob/main/. **VERIFIED** = run on 2026-10-01 with Python 3.14.7, Textual 8.2.8, Rich 15.0.0. `UNVERIFIED` = not confirmed. `derived:` = inference.

## 1. Versions and install (as of 2026-10-01)

| Package | Version | Notes | Source |
|---|---|---|---|
| `textual` | **8.2.8** (2026-06-30) | MIT; Python >=3.9,<4; `rich>=14.2.0`; extra `textual[syntax]` = tree-sitter grammars for `TextArea`/`Markdown` highlighting | PyPI; TX:CHANGELOG.md |
| `rich` | 15.0.0 | rendering backend | PyPI |
| `textual-dev` | 1.8.0 | the `textual` CLI: `run --dev`, `console`, `serve`, `keys`, `borders`, `colors` | TX:docs/guide/devtools.md |
| `pytest-textual-snapshot` | 1.1.0 | SVG snapshots via syrupy; **pins `syrupy==4.8.0`, which caps pytest below 9** (not run here) | PTS:pyproject.toml |

```sh
uv add textual                                   # or: pip install textual   (textual[syntax] for highlighting)
uv add --dev textual-dev pytest pytest-asyncio pytest-textual-snapshot
python -m textual            # built-in widget tour and demo
textual run --dev app.py     # live CSS reload + devtools; run `textual console` in another tab for logs
```
Maintenance: very active (37k stars; releases roughly every 1–2 weeks). AI-generated PRs are accepted only if labelled and linked to an approved issue (TX:AI_POLICY.md). Textual builds on **Rich**: widgets accept Rich renderables (`Table`, `Syntax`, `Panel`, `Text`).

## 2. Mental model

- **Retained DOM of widgets.** `App` → stack of `Screen`s → widgets. Build declaratively in `compose()` with `yield` and `with` containers; change at runtime with `mount()`/`remove()`; find with CSS selectors `query()` / `query_one()` (TX:docs/guide/app.md).
- **TCSS styles it**: `CSS` / `CSS_PATH` (`.tcss`) / `DEFAULT_CSS` class vars; selectors, pseudo-classes (`:focus`, `:hover`, `:dark`, `:light`, `:inline`, `:ansi`, `:nocolor`), theme variables (`$primary`, …). `textual run --dev` live-reloads CSS (TX:docs/guide/CSS.md).
- **Reactive attributes**: `reactive(default, layout=False, repaint=True, init=True, always_update=False, recompose=False)`, `var()`; magic methods `watch_<name>`, `validate_<name>`, `compute_<name>` (TX:docs/guide/reactivity.md).
- **Message pump**: every App/Screen/Widget has an async queue; handlers `on_<snake_message>` or `@on(Widget.Message, "selector")`; messages bubble up the DOM (TX:docs/guide/events.md).
- **Workers** run slow or blocking work off the loop (section 8). The compositor repaints only dirty regions, up to `TEXTUAL_FPS` (default 60).

## 3. Minimal app (VERIFIED headless with `run_test()` and Pilot)

```python
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Button, Footer, Header, Label


class CounterApp(App):
    CSS = """
    Screen { align: center middle; }
    #count { width: auto; padding: 1 2; border: round $accent; }
    Horizontal { height: auto; width: auto; }
    """
    BINDINGS = [("+", "inc", "Increment"), ("q", "quit", "Quit")]

    count = reactive(0)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(id="count")
        with Horizontal():
            yield Button("+1", id="inc", variant="primary")
        yield Footer()

    def watch_count(self, value: int) -> None:
        self.query_one("#count", Label).update(f"Count: {value}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.action_inc()

    def action_inc(self) -> None:
        self.count += 1


if __name__ == "__main__":
    CounterApp().run()
```
Run: `python counter.py` or `textual run --dev counter.py`.

### Lifecycle, signals and exit status

Read in `textual/app.py` (`exit`, `return_code`, `suspend`, `action_suspend_process`, `_handle_exception`), `drivers/linux_driver.py` and `drivers/web_driver.py` of 8.2.8; "Since" from `TX:CHANGELOG.md`. **VERIFIED** = run 2026-10-02 in an isolated `tmux -L` (bash job control for Ctrl+Z); `#{alternate_on}` and `stty -a` read after exit. The rules behind it: `../lifecycle.md` LC1, LC3, LC9-LC11.

| Path | Textual 8.2.8 | What you add | Since |
|---|---|---|---|
| quit | `ctrl+q` / `action_quit` / `self.exit(result=None, return_code=0, message=None)`; the driver restores; `run()` returns `result`, **not** the code | `app.run()` then `sys.exit(app.return_code)` (the property's own docstring example). VERIFIED: `self.exit(return_code=3)` → status 3. Without it the process exits 0 | `return_code` 0.36.0 |
| unhandled exception | `_handle_exception` sets `return_code = 1`, restores, prints the traceback | the same `sys.exit(app.return_code)` | |
| Ctrl+C | bound to `help_quit`: a notice, the app keeps running (VERIFIED) | for a cancel status bind it to an action that calls `self.exit(return_code=130)` | |
| SIGTERM | **no handler** in the desktop drivers (only `web_driver.py` handles SIGINT/SIGTERM). Python's default kills the process: status 143, but **the alt screen, hidden cursor and raw mode survive** (VERIFIED) | in `on_mount`: `asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, lambda: self.exit(return_code=143))` (Unix only), plus `sys.exit(app.return_code)` (VERIFIED: 143, restored). Do not restore the terminal from a `signal.signal` handler yourself | |
| `$EDITOR` handoff | `with self.suspend(): subprocess.run([editor, path])`: publishes `app_suspend_signal`, leaves application mode, runs the block, resumes, publishes `app_resume_signal`, `refresh(layout=True)`. Raises `SuspendNotSupported` when the driver cannot suspend (Textual Web) | reload the data after the `with` (the refresh repaints the old state); catch `SuspendNotSupported` and offer a non-terminal path | 0.48.0 |
| Ctrl+Z | not bound by default. `action_suspend_process` publishes `app_suspend_signal` and sends SIGTSTP; the driver leaves application mode, stops, and on SIGCONT re-enters and publishes `app_resume_signal` (VERIFIED: alt screen off while stopped, back after `fg`) | `BINDINGS = [("ctrl+z", "suspend_process", "Suspend")]`; reload in `self.app_resume_signal.subscribe(self, callback)` | 0.48.0 |
| Windows | `suspend()` is supported ("Unix-like operating systems and Microsoft Windows", its docstring); `action_suspend_process` is "a non-operation" on Windows and Textual Web; `inline=True` unsupported (§13 #13) | a shell-out action through `suspend()` instead of Ctrl+Z | |

## 4. Project layout

`pyproject.toml`; `src/<pkg>/__init__.py`; app module with a sibling `app.tcss` loaded via `CSS_PATH = "app.tcss"` (a relative path resolves next to the module); `tests/` (TX:docs/how-to/package-with-hatch.md, TX:docs/guide/app.md#css). derived: split into `screens/` and `widgets/` subpackages as it grows; each widget ships its own `DEFAULT_CSS`; keep `theme.py` (generated, section 9) beside the app module.

## 5. Layout system

- `layout: vertical` (default) | `horizontal` | `grid` (TX:docs/styles/layout.md). Grid: `grid-size: <cols> [<rows>]`, `grid-columns` / `grid-rows` (`1fr 2fr 10 auto`), `grid-gutter`, `column-span`, `row-span`.
- `dock: top|right|bottom|left` pins a widget to an edge outside the flow (`Header`, `Footer`).
- Units: cells, `%` (of parent), `fr`, `w`/`h` (% of available), `vw`/`vh` (% of terminal), `auto`. `box-sizing: border-box` (default). `padding`/`margin`: 1, 2 (vertical horizontal) or 4 values. `align: <h> <v>` (children), `content-align`, `text-align`.
- Overflow `auto|scroll|hidden` per axis; `scrollbar-size`, `scrollbar-gutter`. Layers: `layers`/`layer`, `offset`, `position: relative|absolute`, `display: none`, `opacity`, `tint`, `keyline`.
- **Border types** (`BORDER_CHARS`, TX:src/textual/_border.py): `ascii blank block dashed double heavy hidden hkey inner none outer panel round solid tab tall thick vkey wide`; syntax `border: <type> <color>`, per side `border-top…`; titles `border-title-*` / `border-subtitle-*` (set `widget.border_title` / `border_subtitle`); `outline` takes no layout space. Preview with `textual borders`.
- Responsive: `App.HORIZONTAL_BREAKPOINTS` / `VERTICAL_BREAKPOINTS` add size classes (TX:examples/breakpoints.py).

| Container | Default CSS | Use |
|---|---|---|
| `Container` | `1fr × 1fr`, layout vertical, overflow hidden | generic box |
| `Vertical` / `Horizontal` | `1fr × 1fr` | expanding column/row |
| `VerticalGroup` / `HorizontalGroup` | `width 1fr; height auto` | **non-expanding** (use inside scroll views) |
| `VerticalScroll` / `HorizontalScroll` / `ScrollableContainer` | `overflow` auto | scrolling |
| `Center` / `Right` / `Middle` / `CenterMiddle` | alignment helpers | |
| `Grid` / `ItemGrid` | `layout: grid` (ItemGrid: auto columns, `height: auto`) | |

**Archetype mapping:**

| Archetype | Textual recipe |
|---|---|
| Whole screen | `Screen` (implicit); `Header` docks top, `Footer` docks bottom, the rest fills |
| Header / footer bands | `Header()` and `Footer()` (Footer renders `BINDINGS` as key hints, so it *is* the keybar); custom band: `Static(id="band")` with `height: 1; dock: top` |
| List + detail | `Horizontal` containing `ListView`/`OptionList` (`width: 40%; border: round …`) and a detail `VerticalScroll` (`width: 1fr`) |
| Dashboard (cards) | `Grid` with `grid-size: 2; grid-gutter: 1`, each card a bordered `Static`/`Vertical`; `ItemGrid` for auto columns |
| Table | `DataTable` (`cursor_type = "row"`) |
| Tabs | `Tabs` + `Tab` for a bare row; `TabbedContent` + `TabPane` with content |
| Modal | `ModalScreen[T]` (section 7) |

## 6. Widgets

All in `textual.widgets.__all__` unless noted (TX:src/textual/widgets/__init__.py, TX:docs/widget_gallery.md):

| Need | Built in | Ecosystem (PyPI, 2026-10-01) |
|---|---|---|
| Text | `Label`, `Static` (base for renderables), `Pretty`, `Digits`, `Rule`, `Placeholder` | — |
| Buttons/toggles | `Button` (`variant=default/primary/success/warning/error`), `Checkbox`, `Switch`, `RadioButton`+`RadioSet`, `SelectionList` | — |
| Input | `Input` (validators, `password`, suggester), `MaskedInput`, `TextArea` (`textual[syntax]`, `TextArea.code_editor()`) | `textual-textarea` 0.18.4, `textual-autocomplete` 4.0.6, `textual-slider` 0.2.0 |
| Choice | `Select` (**overlay dropdown**), `OptionList` (Rich renderables), `ListView`+`ListItem` (widget items) | — |
| Data | `DataTable` (cell/row/column/none cursor, sort, fixed rows/cols), `Tree`, `DirectoryTree` | `textual-universal-directorytree` 1.7.0, `textual-fspicker` 1.0.1 |
| Navigation | `Tabs`+`Tab`, `TabbedContent`+`TabPane`, `ContentSwitcher`, `Collapsible` | — |
| Chrome | `Header` (title, sub-title, clock), `Footer`, `KeyPanel`/`HelpPanel` | — |
| Feedback | `ProgressBar` (`total`, `progress`, `show_eta`, `show_percentage`), `LoadingIndicator` (or `widget.loading = True`), `Sparkline`, `Tooltip` (`widget.tooltip = …`) | `textual-plotext` 1.0.1 (charts) |
| Rich content | `Markdown`, `MarkdownViewer` (TOC + navigation), `Log` (plain, fast), `RichLog` (renderables), `Link` | `textual-image` 0.14.1, `rich-pixels` 3.0.1, `textual-canvas` 1.1.0 |
| Outside `__all__` | `App.notify(msg, *, title="", severity="information"\|"warning"\|"error", timeout=None)` → toasts (thread-safe); `textual.screen.ModalScreen`, `Screen`; command palette `textual.command.Provider`/`Hit`/`Hits`; `textual.canvas.Canvas` (internal) | `textual-serve` 1.1.3 (browser), `textual-speedups` 0.2.1 |

## 7. Focus, keys, actions, screens, mouse

- **Focus**: one widget receives keys; Tab/Shift+Tab are Screen bindings (`app.focus_next/previous`). `can_focus` is a class attribute (`class W(Widget, can_focus=True)`); `widget.focus()`, `Screen.AUTO_FOCUS` (selector), CSS `:focus` / `:focus-within`, `Focus`/`Blur` events; disabled widgets cannot focus (TX:docs/guide/input.md).
- **Bindings**: `BINDINGS = [("key", "action", "Description"), Binding(...)]`; `Binding(key, action, description="", show=True, key_display=None, priority=False, tooltip="", id=None, system=False, group=None)`; `key` may list alternatives (`"r,t"`). Lookup: focused widget → DOM → Screen → App; `priority=True` first. Defaults: `ctrl+q` quit, `ctrl+c` help_quit, `ctrl+p` command palette. **Bindings cannot change at runtime**: use `check_action(action, parameters) -> bool|None` and `refresh_bindings()` (TX:docs/guide/actions.md).
- **Actions**: `action_<name>()`; string syntax `"app.bell"`, `"add_bar('red')"`; namespaces `app.`, `screen.`, `focused.`; markup links `[@click=app.bell]bell[/]`.
- **Screens** (TX:docs/guide/screens.md): `push_screen(screen|name, callback=None, wait_for_dismiss=False)`, `pop_screen()`, `switch_screen()`, `install_screen(screen, name)`; `ModalScreen[ResultType]` with `self.dismiss(result)`; `await self.app.push_screen_wait(...)`; `MODES = {"name": ScreenClass}` + `switch_mode(name)` keep a stack per mode.
- **Command palette**: Ctrl+P (`App.COMMAND_PALETTE_BINDING`, `ENABLE_COMMAND_PALETTE = True`); extend with `COMMANDS = {MyProvider}` or `App.get_system_commands(screen)`; theme switching is built in. It also adds a `^p palette` entry to the Footer (VERIFIED).
- **Mouse**: on by default (`run(mouse=True)`); events `Click`, `MouseDown/Up/Move`, `MouseScrollUp/Down`, `Enter`, `Leave`; drag-select text, Ctrl+C copies. Kitty keyboard protocol is on by default (`TEXTUAL_DISABLE_KITTY_KEY` to disable); `textual keys` shows what a terminal sends.

## 8. Async, timers, performance

- Workers: `self.run_worker(coro_or_fn, name="", group="default", exit_on_error=True, exclusive=False, thread=False)` or `@work(...)`. `exclusive=True` cancels earlier workers in the group (type-ahead search). Thread workers need `thread=True`; touch the UI only via `self.app.call_from_thread(fn, …)` or `post_message`; check `get_current_worker().is_cancelled`. States `PENDING → RUNNING → SUCCESS|ERROR|CANCELLED` → `Worker.StateChanged` (TX:docs/guide/workers.md). Workers die with their DOM node.
- Timers: `set_interval(interval, callback, *, name, repeat=0, pause=False)`, `set_timer(delay, callback)`, `call_later`, `call_after_refresh`; animation `widget.styles.animate("opacity", value=0.0, duration=…)`; `TEXTUAL_ANIMATIONS=none|basic|full` (TX:src/textual/message_pump.py).
- Never block in a handler (awaiting an HTTP call inside `on_input_changed` freezes typing). `Log` over `RichLog` for huge line counts (derived); `DataTable` over thousands of widgets (derived); `TEXTUAL_FPS` caps frame rate.

### Debugging and profiling

stdout belongs to the app. Textual redirects it, so `print()` is safe, but the output has to go somewhere you can read. Checked 2026-10-02: **docs** = read in the cited page, not run here; `derived:` = inference.

| Need | Tool | Command / setting | Notes and gotchas | Source |
|---|---|---|---|---|
| Print / log without corrupting the screen | devtools console (`textual-dev`) | terminal A: `textual console`; terminal B: `textual run --dev app.py`; in code `print(...)`, `from textual import log; log(locals())`, `self.log("msg", key=value)` | **docs.** "Anything you `print` … will be displayed in the console window" (devtools capture stdout). Needs `--dev`: without it nothing connects | https://textual.textualize.io/guide/devtools/ |
| Noise control | console filters | `textual console -v` (verbose), `textual console -x EVENT -x SYSTEM -x DEBUG -x INFO` (groups: `EVENT DEBUG INFO WARNING ERROR PRINT SYSTEM LOGGING WORKER`) | **docs.** Start with `-x EVENT -x SYSTEM` when hunting your own `log` calls | same |
| Port clash | custom port | `textual console --port 7342` and `textual run --dev --port 7342 app.py` | **docs.** | same |
| What does this terminal send? | key inspector | `textual keys` | in the `textual` CLI (§1) | TX:docs/guide/devtools.md |
| Profile a slow render or update loop | `py-spy` | second terminal, while the app runs: `sudo py-spy record --idle --pid <app pid> -o profile.svg` (`--format speedscope` for speedscope), Ctrl-C there to write the file | **docs.** Attach by PID instead of `py-spy record -- python app.py`: derived: py-spy prints its own status to the terminal that launched it, which is the TUI's. Attaching to a running PID usually needs root; launching under py-spy does not (README, "When do you need to run as sudo?"; on macOS root is needed for both: UNVERIFIED) | https://github.com/benfred/py-spy#readme |
| Why `--idle` | py-spy flag | `--idle` includes frames py-spy considers idle | **docs.** By default py-spy keeps only threads that are running code and drops sleeping ones. derived: Textual's asyncio loop spends most of its time parked awaiting events, so a default recording can be nearly empty; with `--idle` you see time awaiting vs. time in your handler. Not run here (py-spy not installed) | py-spy README, "How do you detect if a thread is idle or not?" |
| Where the cost usually is | read the profile for | handlers that block the loop (an HTTP call in `on_input_changed`), `render` / `render_line` of a custom widget, CSS recalculation on a huge DOM | derived: see §8: workers or `thread=True` for I/O, `DataTable` over thousands of widgets, `TEXTUAL_FPS` caps the frame rate. `DataTable.add_rows` as a bulk-insert speed-up is UNVERIFIED |  §8 |

## 9. Applying our theme tokens

Textual's color system is generative: a `Theme` gives ~11 base colors and derives ~170 variables; `Theme.variables` overrides any of them **and may add new ones** (VERIFIED: custom names are usable as `$tok-status-info` in TCSS and `[$tok-status-success]…[/]` in markup). `SKILL_DIR/scripts/export_theme.py ID --target textual -o theme.py` emits a module with a docstring header and one `THEME = Theme(...)`: the 11 base slots plus a **fixed override list** of Textual's own variables, nothing per token. Real output for `catppuccin-mocha` (re-checked 2026-10-01; header docstring lines omitted):

```python
from textual.theme import Theme

THEME = Theme(
    name="catppuccin-mocha",
    primary="#89b4fa", secondary="#cba6f7", accent="#89b4fa",
    warning="#f9e2af", error="#f38ba8", success="#a6e3a1",
    foreground="#cdd6f4", background="#1e1e2e", surface="#313244", panel="#45475a",
    dark=True,
    variables={
        "border": "#b4befe", "border-blurred": "#6c7086",
        "block-cursor-foreground": "#cdd6f4", "block-cursor-background": "#3b3d4f",
        "block-cursor-blurred-foreground": "#cdd6f4", "block-cursor-blurred-background": "#313244",
        "footer-foreground": "#bac2de", "footer-background": "#181825",
        "footer-key-foreground": "#89b4fa", "footer-description-foreground": "#cdd6f4",
        "input-cursor-background": "#f5e0dc", "input-cursor-foreground": "#11111b",
        "input-selection-background": "#3b3d4f", "input-selection-foreground": "#cdd6f4",
        "scrollbar": "#9399b2", "scrollbar-background": "#45475a",
        "link-color": "#89b4fa", "text-muted": "#a6adc8", "text-disabled": "#7f849c",
        "block-cursor-text-style": "bold", "link-style": "underline",
    },
)
```

Register it with `App.register_theme(THEME); App.theme = THEME.name`. The exporter does **not** emit a per-token variable (`$tok-status-info`, `$tok-tab-active-fg`, `$tok-ramp-low`…); for tokens Textual has no slot for, build them from the flat theme (`export_theme.py ID --target json -o theme.json`) and merge them into `variables=`, as the starter does in `fleet/theme.py` (`"tok-" + token.replace(".", "-")`; the pattern was VERIFIED with a stand-in generator):

```python
import json
TOKENS: dict[str, str] = json.load(open("theme.json"))["tokens"]     # every token, fallbacks resolved
CUSTOM_VARIABLES = {"tok-" + k.replace(".", "-"): v for k, v in TOKENS.items()}   # "status.error" -> $tok-status-error
# then: Theme(..., variables={**CUSTOM_VARIABLES, <the exporter's dict>})
```

| Token | Textual |
|---|---|
| `bg.base` / `bg.surface` / `bg.raised` | `Theme.background` (`$background`, Screen) / `surface` (`$surface`) / `panel` (`$panel`: Header, DataTable header) |
| `fg.default`, `fg.muted`, `fg.faint` | `Theme.foreground`; `$text-muted`; `$text-disabled` (exported; `$foreground-muted`/`$foreground-disabled` are derived by Textual) |
| `accent.primary` / `accent.secondary` | `primary` (+`accent`) / `secondary` |
| `status.success/warning/error` | `success` / `warning` / `error` (`status.info` → custom `$tok-status-info`) |
| `border.focus` / `border.default` | `$border` (focused widget) / `$border-blurred`; for your own panes use `border: round $tok-border-default` and `:focus-within { border: round $tok-border-focus; }` |
| `selection.*` | `$block-cursor-*` (ListView, OptionList, DataTable, focused Tabs); inactive: `$block-cursor-blurred-*` |
| `statusbar.*`, `keyhint.*` | `$footer-*`; custom bands: `background: $tok-statusbar-bg; color: $tok-statusbar-fg;` |
| `cursor.*`, `text-selection.*`, `link`, `scrollbar.*` | `$input-cursor-*`, `$input-selection-*`, `$link-color` (+ `$link-style`), `$scrollbar`, `$scrollbar-background` |
| everything else (`tab.*`, `ramp.*`, `diff.*`, `mark`, `table.header`, …) | custom `$tok-tab-active-fg`, `$tok-ramp-low`, … in TCSS (`$tok-` + token with `.` → `-`; you add them, see above) |

App wiring. Custom `$vars` must exist **when the CSS is parsed**, i.e. before the first screen: either register the theme in `__init__` or return the variables from `get_theme_variable_defaults()` (both VERIFIED to give byte-identical frames; the failure mode is section 13, item 1):

```python
from textual.app import App
from theme import THEME, CUSTOM_VARIABLES   # your merge of exporter THEME + CUSTOM_VARIABLES

class FleetApp(App):
    CSS = """
    Screen        { background: $tok-bg-base; color: $tok-fg-default; }
    #band         { height: 1; background: $tok-statusbar-bg; color: $tok-statusbar-fg; padding: 0 1; }
    Tab           { color: $tok-tab-inactive-fg; background: $tok-statusbar-bg; }
    Tab.-active   { color: $tok-tab-active-fg; background: $tok-tab-active-bg; text-style: bold; }
    #services     { width: 40%; border: round $tok-border-default; border-title-color: $tok-fg-title; background: $tok-bg-base; }
    #services:focus-within { border: round $tok-border-focus; }
    ListView, ListView:focus { background: $tok-bg-base; background-tint: transparent; }
    """
    def __init__(self) -> None:
        super().__init__()
        self.register_theme(THEME)        # before CSS parsing
        self.theme = THEME.name
    # alternative: def get_theme_variable_defaults(self): return CUSTOM_VARIABLES   (then register in on_mount)
```
Read back in a test: `app.theme_variables["tok-status-error"] == "#f38ba8"` (VERIFIED). Colors observed in a rendered 60x14 frame equal the tokens exactly: highlighted row bg `#3b3d4f` (`selection.bg`), focused border `#b4befe`, blurred `#6c7086`, footer keys `#89b4fa`, footer text `#a6adc8`, `[$status-success]●[/]` `#a6e3a1`.

16-color / terminal-palette mode: `App(ansi_color=True)` or `Theme(ansi=True)` (built-ins `ansi-dark`, `ansi-light`) makes Textual emit native ANSI colors so the user's terminal palette shows through; that is the route for our `ansi16` mappings (per-token `ansi_red`-style color names; the exact mapping is UNVERIFIED).

## 10. Color depth, NO_COLOR, wide characters, links, screens

- Color system: Rich `Console(color_system=…)`; `TEXTUAL_COLOR_SYSTEM=auto|standard|256|truecolor|windows` (default `auto`: `COLORTERM`/`TERM`). **By default Textual converts the 16 ANSI colors to its own truecolor values** and never emits themeable ANSI codes; translucent terminal backgrounds therefore do not show through (TX:docs/FAQ.md "ANSI themes"). Downsampled frames use Rich's own quantizer (VERIFIED: `#1e1e2e` → `48;5;16` at 256 colors, `37;40` at "standard"), not our OKLab mapping.
- **NO_COLOR honored**: `App.no_color = "NO_COLOR" in environ`; adds the `Monochrome()` filter (`NoColor()` in ANSI mode); CSS pseudo-class `:nocolor` (TX:src/textual/app.py).
- Wide chars via Rich cell widths (VERIFIED: CJK and `✔` align inside a bordered `ListView`).
- Hyperlinks: OSC 8 (TX:src/textual/strip.py); markup `[link="https://…"]x[/link]`, `Link` widget, `App.open_url()`.
- **Alt screen by default** (`App.run()`, "application mode"). Inline: `App.run(inline=True, inline_no_clear=False)` renders below the prompt (pseudo-class `:inline`; **not supported on Windows**) (TX:docs/guide/app.md#run-inline). `App.suspend()` hands the terminal to a subprocess.
- macOS Terminal.app: 256 colors only, box-drawing glitches, Cmd/Option never arrive; recommend iTerm2/Kitty/WezTerm; bind portable keys (letters, F1–F10, `ctrl+…`) (TX:docs/FAQ.md).

## 11. Testing

- `async with app.run_test(*, headless=True, size=(80, 24), tooltips=False, notifications=False, message_hook=None) as pilot:` needs an async test (`pytest-asyncio` with `asyncio_mode = auto` in `pytest.ini`, VERIFIED). Pilot (TX:src/textual/pilot.py): `press(*keys)` (names as in `textual keys`), `click(widget|selector|type, offset=(0,0), times=1, button=1, shift/meta/control)`, `double_click`, `hover`, `mouse_down/up`, `resize_terminal(w, h)`, `pause(delay=None)`, `wait_for_animation()`, `exit(result)`.

```python
async def test_counter():
    app = CounterApp()
    async with app.run_test(size=(60, 16)) as pilot:
        await pilot.press("+", "+")
        await pilot.click("#inc")
        await pilot.pause()
        assert app.count == 3          # VERIFIED
```
- Snapshots: `pytest-textual-snapshot` fixture `snap_compare(app_or_path, press=(), terminal_size=(80, 24), run_before=async_fn(pilot))` stores **SVG** via syrupy; first run fails, then `pytest --snapshot-update` (TX:docs/guide/testing.md#snapshot-testing; not run here). Animations make snapshots flaky: `wait_for_animation` is on by default; consider `TEXTUAL_ANIMATIONS=none`.
- ANSI golden (our recommendation, derived): reuse the `frame_to_ansi` helper of section 12 and compare text files; it keeps colors that SVG diffs hide.

## 12. One static frame at a forced size, as ANSI (what the proto-starters use)

Built-ins export **SVG only**: `App.export_screenshot(*, title=None, simplify=False) -> str`, `App.save_screenshot(filename=None, path=None, ...)`, env `TEXTUAL_SCREENSHOT=<seconds>`. There is **no public ANSI/text export**, and Rich's `console.export_text(styles=True)` leaks the compositor's cursor-move control codes (`ESC[row;1H`) (VERIFIED). Working recipe (VERIFIED again 2026-10-01 on the themed app at 60x14 in truecolor, 256 and standard; uses a **private API**: pin the Textual version):

```python
import asyncio, io, sys
from rich.console import Console
from textual.app import App

def frame_to_ansi(app: App, color_system: str = "truecolor") -> str:
    """Current screen as ANSI lines (no cursor-move codes). color_system: truecolor | 256 | standard."""
    width, height = app.size
    console = Console(width=width, height=height, file=io.StringIO(), force_terminal=True,
                      color_system=color_system, legacy_windows=False, safe_box=False)
    update = app.screen._compositor.render_update(full=True, screen_stack=app._background_screens)
    return "\n".join("".join(strip.render(console) for strip in line) for line in update.strips) + "\n"

def frame_to_text(app: App) -> str:
    update = app.screen._compositor.render_update(full=True)
    return "\n".join("".join(s.text for s in line) for line in update.strips) + "\n"

async def snapshot(app: App, cols=120, rows=30, keys=(), color_system="truecolor") -> str:
    async with app.run_test(size=(cols, rows)) as pilot:    # notifications=True to capture toasts
        if keys:
            await pilot.press(*keys)
        await pilot.pause()                  # settle layout/messages
        return frame_to_ansi(app, color_system)

if __name__ == "__main__":
    from myapp import MyApp
    sys.stdout.write(asyncio.run(snapshot(MyApp(), 120, 30)))
```
Caveats: (1) output is exactly `rows` lines of `cols` cells, each line ending `ESC[0m`; (2) truecolor emits `38;2;…`, `256` → `38;5;…`, `standard` → `91;40`-style, all by Rich's quantizer; (3) `run_test` suppresses notifications and tooltips by default; (4) await `pilot.pause()` (and `wait_for_animation()` if animating) before capture; set `TEXTUAL_ANIMATIONS=none` for determinism; (5) the screen is whatever `size` you give: drive responsive classes by choosing the size; (6) the alternative without private APIs is `App.run(headless=True, size=(w, h), auto_pilot=fn)` + `export_screenshot()` inside `auto_pilot` → SVG, which cannot be converted to ANSI.

## 13. Pitfalls and anti-patterns (symptom → cause → fix → source)

| # | Symptom | Cause | Fix | Source |
|---|---|---|---|---|
| 1 | `Error in stylesheet … $tok-bg-base` (undefined variable) at startup | CSS is parsed before `on_mount`; custom variables of a theme registered later do not exist yet | Register + set the theme in `__init__`, or override `get_theme_variable_defaults()` | VERIFIED (this file §9) |
| 2 | Cursor/selection highlight disappears after you style the widget | App CSS beats a widget's `DEFAULT_CSS` regardless of specificity; `ListItem { background: … }` overrides `ListItem.-highlight` | Style the container, or scope (`ListItem.-highlight`), never blanket-set item backgrounds | VERIFIED; TX:src/textual/widgets/_list_item.py |
| 3 | Focused pane is slightly lighter than `bg.base` (`#262737` vs `#1e1e2e`) | Focusable built-ins set `background-tint: $foreground 5%` on `:focus` (ListView, OptionList, DataTable, Input, Tree, Log, …) | `background-tint: transparent` on the widget (and `:focus`) when you need the exact token color | VERIFIED; `rg background-tint widgets/` |
| 4 | Active tab looks like a list cursor | A focused `Tabs` paints the active tab with `$block-cursor-*` | Override `Tab.-active` colors (section 9) | TX:src/textual/widgets/_tabs.py |
| 5 | Footer shows `^p palette` you did not ask for | `ENABLE_COMMAND_PALETTE = True` by default | `ENABLE_COMMAND_PALETTE = False` | VERIFIED |
| 6 | UI freezes while typing | Blocking I/O or slow `await` inside a handler | `@work` / `run_worker` (`exclusive=True` for type-ahead) | TX:docs/guide/workers.md |
| 7 | Crash or garbage updating the UI from a thread | Widgets touched off the loop | `call_from_thread` / `post_message`; `@work(thread=True)` for sync work | TX:docs/guide/workers.md |
| 8 | `Horizontal`/`Vertical` inside `VerticalScroll` stretches or collapses | They are `1fr` high | `HorizontalGroup` / `VerticalGroup` (`height: auto`) | TX:src/textual/containers.py |
| 9 | `query_one` fails in `__init__` | DOM not mounted | Use `on_mount`; `recompose=True` reactives rebuild structure | TX:docs/guide/app.md |
| 10 | Mutating a reactive list/dict triggers no watcher | In-place mutation | `self.mutate_reactive(Cls.attr)` | TX:docs/guide/reactivity.md |
| 11 | Binding cannot be added/removed at runtime | `BINDINGS` are static | `check_action` + `refresh_bindings()` | TX:docs/guide/actions.md |
| 12 | Terminal's ANSI theme is ignored, translucent background not shown | Textual converts ANSI colors to truecolor | `App(ansi_color=True)` / `ansi-dark` theme | TX:docs/FAQ.md |
| 13 | `inline=True` fails on Windows | Unsupported | Alt-screen mode on Windows | TX:docs/guide/app.md |
| 14 | Snapshot tests flake | Animations; `syrupy==4.8.0` pin conflicts with pytest 9 | `wait_for_animation`, `TEXTUAL_ANIMATIONS=none`; pin pytest <9 or use ANSI goldens (section 11) | PTS:pyproject.toml |
| 15 | Cmd/Option shortcuts never fire on macOS | Terminal.app/Terminal emulators do not forward them | Portable keys only | TX:docs/FAQ.md |
| 16 | Frame helper breaks after a Textual upgrade | `_compositor`/`_background_screens` are private | Pin `textual==8.2.8`; re-run the helper in CI | VERIFIED (section 12) |

## 14. Showcase apps and official examples worth reading

Apps (stars 2026-10-01): **Posting** (darrenburns/posting, HTTP client, 12.5k), **Harlequin** (tconbeer/harlequin, SQL IDE, 6.4k), **Memray** live mode (bloomberg/memray), **Toolong** (log viewer, dormant), **Dolphie** (MySQL monitor), **Elia** (LLM chat), **Toad** (batrachianai/toad, AI-agent TUI, pins `textual[syntax]==8.2.7`), **mistral-vibe** (coding-agent CLI, pins `textual==8.2.8` + `textual-speedups`). The built-in `python -m textual` demo has a Projects page.

Official examples (`TX:examples/`, `python <file>`):

| Example | Pattern |
|---|---|
| `code_browser.py` + `.tcss` | `DirectoryTree` sidebar + scrolling code view; toggling the sidebar via a reactive; Header/Footer |
| `calculator.py` | `Grid` of Buttons, reactive `var`, `Digits` |
| `dictionary.py` | `Input` → async worker lookup → `Markdown` |
| `mother.py` | LLM chat: `VerticalScroll` of streamed `Markdown` + `Input` |
| `sidebar.py` | animated off-canvas sidebar (`offset` animation) |
| `breakpoints.py` | responsive `Grid` via `HORIZONTAL_BREAKPOINTS` |
| `color_command.py` | custom command-palette `Provider` |
| `theme_sandbox.py` | every widget under each theme (theme QA) |
| `five_by_five.py` | custom Widgets, help `Screen`, bindings |
| `json_tree.py`, `markdown.py` | `Tree` from data; `MarkdownViewer` + TOC |
