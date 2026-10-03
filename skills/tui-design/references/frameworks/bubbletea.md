# Bubble Tea (Go, Elm architecture) — getting-started and design reference

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [1. Versions and install (as of 2026-10-01)](#1-versions-and-install-as-of-2026-10-01) · L23–51 — pinning versions and installing.
- [2. Mental model](#2-mental-model) · L53–59 — first contact: how the framework thinks.
- [3. Minimal app](#3-minimal-app-verified-built-and-run-in-tmux) · L61–121 — a verified minimal app to copy.
- [4. Project layout](#4-project-layout) · L123–138 — file layout of a real app.
- [5. Layout system](#5-layout-system) · L140–196 — sizing panes, flex and grid, breakpoints.
- [6. Components (Bubbles v2.2.1 and ecosystem)](#6-components-bubbles-v221-and-ecosystem) · L198–211 — which built-in or ecosystem widget to use.
- [7. Focus, keys, mouse](#7-focus-keys-mouse) · L213–219 — key bindings, focus order, mouse.
- [8. Async, timers, performance](#8-async-timers-performance) · L221–237 — background work, streaming, frame rate, flicker.
- [9. Applying our theme tokens](#9-applying-our-theme-tokens) · L239–289 — wiring `export_theme.py` output into styles.
- [10. Color profiles, NO_COLOR, wide characters, alt screen vs inline](#10-color-profiles-no_color-wide-characters-alt-screen-vs-inline) · L291–297 — colour depth, NO_COLOR, wide characters, alt screen vs inline.
- [11. Testing](#11-testing) · L299–312 — unit, snapshot and PTY tests.
- [12. One static frame at a forced size, as ANSI](#12-one-static-frame-at-a-forced-size-as-ansi-what-the-proto-starters-use) · L314–325 — frame mode: one ANSI frame at a forced size (for `compare.py`).
- [13. Pitfalls and anti-patterns](#13-pitfalls-and-anti-patterns-symptom--cause--fix--source) · L327–344 — something renders or behaves wrong (symptom → fix).
- [14. Showcase apps and official examples worth reading](#14-showcase-apps-and-official-examples-worth-reading) · L346–350 — real code worth reading.

Read this when you design, build, theme, test or capture a terminal UI with **Bubble Tea v2** + Lip Gloss v2 + Bubbles v2 (+ Huh forms). **Most Bubble Tea code on the web and in model memory is v1 and does not compile against v2: read the v1 → v2 table in §1 first.**

Source keys: `BT:` https://github.com/charmbracelet/bubbletea/blob/main/ · `BUB:` https://github.com/charmbracelet/bubbles/blob/main/ · `LG:` https://github.com/charmbracelet/lipgloss/blob/main/ · `HUH:` https://github.com/charmbracelet/huh/blob/main/ · `CP:` https://github.com/charmbracelet/colorprofile/blob/main/ · `X:` https://github.com/charmbracelet/x/blob/main/. **VERIFIED** = built and run on 2026-10-01 with Go 1.27.1, bubbletea v2.0.10, bubbles v2.2.1, lipgloss v2.0.6, huh v2.0.3, colorprofile v0.4.3: a Fleet demo (list + detail + header/footer bands + modal) that matches `assets/demo/fleet--normal--80x24.mock` **cell for cell** (char, fg, bg) at 80x24, plus golden/teatest tests and a tmux-driven interactive run. `UNVERIFIED` = not confirmed; `derived:` = inference.

## 1. Versions and install (as of 2026-10-01)

| Package | Import path (v2) | Latest | Notes |
|---|---|---|---|
| Bubble Tea | `tea "charm.land/bubbletea/v2"` | v2.0.10 (2026-09-24; v2.0.0 was 2026-02-24) | MIT; `go 1.26.0`; last v1 = v1.3.10 (2025-09-17, frozen, path `github.com/charmbracelet/bubbletea`) |
| Bubbles | `charm.land/bubbles/v2/<pkg>` | v2.2.1 | `cursor filepicker help key list paginator progress spinner stopwatch table textarea textinput timer tree viewport` |
| Lip Gloss | `charm.land/lipgloss/v2` (+ `/table /tree /list /compat`) | v2.0.6 | no border-title API (§5) |
| Huh | `charm.land/huh/v2` (+ `/spinner`) | v2.0.3 | forms; embeds in Bubble Tea |
| Glamour / Log / Gum | `charm.land/glamour/v2` · `charm.land/log/v2` · `charm.land/gum/v2` | v2.0.1 · v2.0.1 · v2.0.2 | |
| colorprofile | `github.com/charmbracelet/colorprofile` | v0.4.3 | required by Bubble Tea v2 |
| teatest | `github.com/charmbracelet/x/exp/teatest/v2` | **untagged**: pseudo-version `v2.0.0-20261001101533-953920dd3285` | `go get` resolves it; `x/exp/golden` is v0.1.0 |
| Third party | `github.com/lrstanley/bubblezone/v2` (mouse zones) v2.0.0 · `github.com/NimbleMarkets/ntcharts/v2` (charts) v2.5.0 | | `harmonica` (springs) still `github.com/charmbracelet/harmonica` v0.2.0 |

Source: `BT:go.mod`. Very active (repo pushed 2026-09-28, 45k stars); users: gh-dash, Superfile, chezmoi, Glow, Huh, Wishlist (`BT:README.md`). Install: `go mod init example.com/app && go get charm.land/bubbletea/v2@latest charm.land/bubbles/v2@latest charm.land/lipgloss/v2@latest`. **Upgrade the whole stack together.**

### The v1 → v2 break (generated code that shows a left-column tell is v1 and wrong)

| v1 tell (web examples) | v2 (use this) | Source |
|---|---|---|
| `github.com/charmbracelet/{bubbletea,bubbles,lipgloss,huh}` | `charm.land/{bubbletea,bubbles,lipgloss,huh}/v2` | `BT:UPGRADE_GUIDE_V2.md` |
| `View() string` on the root model | `View() tea.View`; `tea.NewView(s)`; modes are fields of the view | same, "The Big Idea" |
| `tea.WithAltScreen()`, `tea.EnterAltScreen`, `tea.EnableMouseCellMotion` | `v.AltScreen = true`, `v.MouseMode = tea.MouseModeCellMotion` in `View()` | same |
| `case tea.KeyMsg:` with `msg.Type`, `msg.Runes`, `case " ":` | `case tea.KeyPressMsg:` + `msg.String()` (`"space"`, `"ctrl+c"`, `"enter"`); `tea.KeyMsg` is now an interface (press+release) | same, "Key Messages" |
| `lipgloss.AdaptiveColor{Light,Dark}`, auto dark/light | `lipgloss.LightDark(isDark)(light, dark)`; get `isDark` from `tea.RequestBackgroundColor` → `tea.BackgroundColorMsg.IsDark()` | `LG:UPGRADE_GUIDE_V2.md` |
| bubbles styled themselves for the terminal | **bubbles v2 do not adapt**: `help.DefaultStyles(isDark)`, `list.DefaultStyles(isDark)`, `textinput.DefaultStyles(isDark)`… | `BUB:UPGRADE_GUIDE_V2.md` §4 |
| `viewport.New(80, 24)`, `m.Width = 40` on a bubble | `viewport.New(viewport.WithWidth(80), viewport.WithHeight(24))`, `m.SetWidth(40)` | `BUB:UPGRADE_GUIDE_V2.md` §2b |
| `Style.Render` downsampled colors itself | `Render` **always emits truecolor**; Bubble Tea / `lipgloss.Println` / a `colorprofile.Writer` downsample on output | `LG:UPGRADE_GUIDE_V2.md` |
| Width math from v1 | v2 `Style.Width(n)` = total block width **including border and padding**; `Height(n)` is a **minimum** (content grows it). VERIFIED: two `Width(30)` rounded panes join to 60 columns; `Height(12)` rendered 13 rows when the help line wrapped. v1 semantics UNVERIFIED (the guide does not list this change), so distrust inherited width arithmetic | VERIFIED |
| `lipgloss.WithWhitespaceForeground/Background` | `WithWhitespaceStyle(style)` | `LG:UPGRADE_GUIDE_V2.md` |

## 2. Mental model

- **Elm loop:** `type Model interface { Init() Cmd; Update(Msg) (Model, Cmd); View() View }` (`BT:tea.go`). `Msg` is any value; `Cmd` is `func() Msg` run **in its own goroutine**; its result re-enters `Update`. `Update` and `View` stay pure and fast; all I/O is a Cmd.
- **View after every Update**, diffed by a cell-based renderer (`cursed_renderer.go`, on `charmbracelet/ultraviolet`). You return a **string** of ANSI text; there is no layout engine, no widget tree: **layout = string composition** (Lip Gloss) and measuring (`lipgloss.Width/Height`).
- **Only the root returns `tea.View`.** Children (bubbles, `huh.Form`) expose `Update(msg) (T, tea.Cmd)` with their concrete type and `View() string`; the parent stores them by value, forwards every message and **reassigns**: `m.list, cmd = m.list.Update(msg)`.
- **Terminal modes are declarative** fields of `tea.View`: `Content, AltScreen, MouseMode, ReportFocus, WindowTitle, Cursor, ProgressBar, BackgroundColor, ForegroundColor, KeyboardEnhancements, OnMouse, DisableBracketedPasteMode` (`BT:tea.go` `type View struct`, checked in v2.0.10).
- **Sizing is pushed to you:** `tea.WindowSizeMsg{Width, Height}` at start and on resize; derive every child size from it. Inline (no alt screen) is the default.

## 3. Minimal app (VERIFIED: built and run in tmux)

```go
package main

import (
	"fmt"; "os"; "time"
	"charm.land/bubbles/v2/spinner"
	tea "charm.land/bubbletea/v2"
	"charm.land/lipgloss/v2"
)

type doneMsg struct{}
type model struct{ spin spinner.Model; done bool }

func work() tea.Msg { time.Sleep(2 * time.Second); return doneMsg{} } // runs off the UI goroutine
func (m model) Init() tea.Cmd { return tea.Batch(m.spin.Tick, work) }
func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyPressMsg:
		if s := msg.String(); s == "q" || s == "ctrl+c" { return m, tea.Quit }
	case doneMsg:
		m.done = true
		return m, tea.Quit
	}
	var cmd tea.Cmd
	m.spin, cmd = m.spin.Update(msg) // forward ticks or the spinner freezes
	return m, cmd
}

var box = lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).Padding(0, 1)

func (m model) View() tea.View {
	if m.done { return tea.NewView(box.Render("✓ done") + "\n") }
	return tea.NewView(box.Render(m.spin.View()+" working… (q to quit)") + "\n")
}

func main() {
	if _, err := tea.NewProgram(model{spin: spinner.New(spinner.WithSpinner(spinner.Dot))}).Run(); err != nil {
		fmt.Fprintln(os.Stderr, err); os.Exit(1)
	}
}
```
Debugging: stdout belongs to the TUI. `f, _ := tea.LogToFile("debug.log", "debug")` then `tail -f debug.log`; Delve: `dlv debug --headless --api-version=2 --listen=127.0.0.1:43000 .` (`BT:README.md`).

### Lifecycle, signals and exit status

Read in `BT:tea.go` (`handleSignals`, `eventLoop`, `Run`), `tty.go`, `tty_unix.go`, `tty_windows.go`, `options.go` at v2.0.10 (same behavior in v2.0.0). "Since" = first v1 tag with the API (module downloads of v0.26.6 / v0.27.0 and v1.2.4 / v1.3.0 compared). **VERIFIED** = run 2026-10-02 in an isolated `tmux -L` (bash job control for Ctrl+Z); `#{alternate_on}` and `stty -a` read after exit. The rules behind it: `../lifecycle.md` LC1, LC3, LC9-LC11.

| Path | What Bubble Tea v2 does | What you add | Since |
|---|---|---|---|
| quit key | `tea.Quit` → `Run()` restores and returns `(model, nil)` | exit 0 | |
| Ctrl+C | arrives as `tea.KeyPressMsg` `"ctrl+c"` (raw mode), not SIGINT | return `tea.Interrupt` → `Run()` returns `ErrProgramKilled` wrapping `tea.ErrInterrupted` → `if errors.Is(err, tea.ErrInterrupted) { os.Exit(130) }` (VERIFIED: 130, restored) | v1.3.0 |
| `kill -INT`, or ^C with non-TTY input | the default handler sends `InterruptMsg`: same as above | | |
| SIGTERM | the default handler sends `QuitMsg`: terminal restored, but `Run()` returns nil, so **status 0**, the same as a normal quit (VERIFIED) | `tea.WithoutSignalHandler()` + `signal.Notify(ch, syscall.SIGINT, syscall.SIGTERM)` → remember the signal, `p.Quit()` → after `Run()`: `os.Exit(143)` (VERIFIED: 143, restored). Notify SIGINT too: the option removes both handlers | |
| panic in `Update`, `View` or a Cmd | recovered; terminal restored; stack printed; `Run()` returns `ErrProgramKilled` wrapping `ErrProgramPanic` | exit 1; keep the default (`WithoutCatchPanics()` leaves the terminal "in a fairly unusable state", its doc comment) | |
| `os.Exit` inside `Update` | skips `Run()`'s restore (`derived:` `os.Exit` runs no deferred code) | never; return `tea.Quit` / `tea.Interrupt` and choose the status after `Run()` | |
| Ctrl+Z | a `KeyPressMsg` `"ctrl+z"`; nothing suspends by itself | return `tea.Suspend`: releases the terminal, sends SIGTSTP to the process group, on SIGCONT re-enters, repaints and sends `tea.ResumeMsg`; reload changed data in that branch (VERIFIED: alt screen off while stopped, back after `fg`, `ResumeMsg` received) | v0.27.0 |
| Windows | `suspendSupported = false`: `tea.Suspend` is ignored, no `ResumeMsg`. Console close, logoff and shutdown reach `signal.Notify` as `syscall.SIGTERM` (Go `os/signal` doc, "Windows"), so the default handler quits | a shell-out key instead of Ctrl+Z: `tea.ExecProcess(exec.Command(shell), cb)` with `%COMSPEC%` / `$SHELL` (`derived:`) | |

`Program.ReleaseTerminal()` restores the terminal and cancels the input reader; `RestoreTerminal()` re-enters **the program's** modes and repaints. It is the resume half of a handoff, not a final cleanup. For editors and shells prefer `tea.ExecProcess` (§8).

## 4. Project layout

No official scaffold (no `cargo generate` equivalent); examples keep everything in `main.go`; gh-dash and Superfile split per sub-model (`BT:examples/`). Recommended for design-system work (derived):

```
app/
├── go.mod                       # module example.com/app ; go 1.26+
├── main.go                      # flags, tea.NewProgram(...).Run()
├── model.go                     # root model, Update (messages, focus, modal state)
├── view.go                      # render(): pure layout composition from m.w, m.h
├── keys.go                      # keyMap of key.Binding + ShortHelp/FullHelp
├── theme/theme.go               # GENERATED: SKILL_DIR/scripts/export_theme.py ID --target lipgloss
├── theme/styles.go              # hand-written role styles/helpers built from theme.*
├── view_test.go + testdata/*.golden
└── cmd/frame/main.go            # optional: headless one-frame renderer (§12)
```

## 5. Layout system

Everything is string composition (`LG:join.go`, `position.go`, `size.go`, `style.go`):

| Need | API | Note |
|---|---|---|
| side by side / stacked | `lipgloss.JoinHorizontal(pos, a, b…)`, `JoinVertical(pos, …)`; `Position` is a float (`Top=0, Center=0.5, Bottom=1, Left=0, Right=1`) | blocks are **padded to the widest/tallest line**: one over-wide line widens the whole block (VERIFIED, §13 #2) |
| measure | `lipgloss.Width(s)`, `Height(s)`, `Size(s)` | ANSI- and wide-char-aware |
| fixed size | `Style.Width(n)` (total incl. border+padding), `Height(n)` (minimum), `MaxWidth(n)`/`MaxHeight(n)` (clip, ANSI-safe), `Inline(true)` | inner size = `w - style.GetHorizontalFrameSize()` |
| center / align in a box | `lipgloss.Place(w, h, hPos, vPos, s, WithWhitespaceStyle(st))`, `PlaceHorizontal`, `PlaceVertical`, `Style.Align/AlignVertical` | |
| borders | `Style.Border(lipgloss.RoundedBorder())`, `BorderForeground`, `BorderTop(false)`…; also `Normal Thick Double Block Hidden ASCII Markdown` | **no title in the border** (checked: no `BorderTitle` in v2.0.6): compose the top rule yourself |
| overlays | `lipgloss.NewLayer(s).X(x).Y(y).Z(z).ID("modal")` + `lipgloss.NewCompositor(layers…).Render()`; `Compositor.Hit(x,y)` for mouse | `LG:layer.go`; VERIFIED for a modal |
| free canvas | `lipgloss.NewCanvas(w, h).Compose(drawable)` | cell grid |
| static data | `lipgloss/v2/table`, `/list`, `/tree` | non-interactive; interactive ones are bubbles |
| wrap / tabs | `lipgloss.Wrap(s, width, breakpoints)` (keeps ANSI + OSC 8), `Style.TabWidth(n)` | |

Helpers used by every archetype below (VERIFIED; `st` takes `color.Color` values from the generated `theme` package, §9):

```go
func st(fg, bg color.Color, attrs ...string) lipgloss.Style { // ALWAYS set both: Lip Gloss never paints an inherited bg
	x := lipgloss.NewStyle().Foreground(fg).Background(bg)
	for _, a := range attrs { switch a { case "bold": x = x.Bold(true); case "faint": x = x.Faint(true); case "italic": x = x.Italic(true) } }
	return x
}
func fill(n int, s lipgloss.Style) string { return s.Render(strings.Repeat(" ", max(0, n))) }

// bar: exactly w cells; right part dropped if both do not fit; styled gap keeps the band's bg unbroken.
func bar(w int, left, right string, gap lipgloss.Style) string {
	if lipgloss.Width(left)+lipgloss.Width(right) > w { right = "" }
	out := left + fill(w-lipgloss.Width(left)-lipgloss.Width(right), gap) + right
	return lipgloss.NewStyle().MaxWidth(w).Render(out)
}

// titledBox: rounded box of exactly w×h with the title inside the top rule "╭─ Title ───╮"; rows are clipped, never widen.
func titledBox(title string, body []string, w, h int, focused bool) string {
	bc := theme.BorderDefault; if focused { bc = theme.BorderFocus }
	b, t := st(bc, theme.BgBase), st(theme.FgTitle, theme.BgBase, "bold")
	title = lipgloss.NewStyle().MaxWidth(max(0, w-6)).Render(title)               // title must fit between ╭─ and ╮
	rows := []string{b.Render("╭─") + t.Render(" "+title+" ") + b.Render(strings.Repeat("─", max(0, w-5-lipgloss.Width(title)))+"╮")}
	for i := 0; i < h-2; i++ {
		line := ""; if i < len(body) { line = body[i] }
		line = lipgloss.NewStyle().MaxWidth(w - 2).Render(line)                       // clip fixed-width rows
		rows = append(rows, b.Render("│")+line+fill(w-2-lipgloss.Width(line), st(theme.FgDefault, theme.BgBase))+b.Render("│"))
	}
	return strings.Join(append(rows, b.Render("╰"+strings.Repeat("─", w-2)+"╯")), "\n")
}
```

**Archetype recipes** (names from `../layout-archetypes.md`; code is the Fleet demo):

| Archetype | Recipe |
|---|---|
| **header + body + footer bands** | `bodyH := m.h - 3` (header, message line, keybar); `lipgloss.JoinVertical(lipgloss.Left, header, body, message, keybar)`. Header = `bar(m.w, " Fleet │ tabs…", "prod-eu · 12:04:31 ", st(theme.FgDefault, theme.StatusbarBg))`; active tab `st(theme.TabActiveFg, theme.BgRaised, "bold")`. Band bg = `theme.StatusbarBg` on **every** span including gaps. |
| **list + detail** | `listW := min(32, m.w*2/5)`; `JoinHorizontal(Top, titledBox("Services (6)", rows, listW, bodyH, true), titledBox(name, detail, m.w-listW, bodyH, false))`. Selected row: every span gets `bg = theme.SelectionBg`, cursor glyph `❯` in `AccentPrimary`, row padded with `fill` to the inner width. Focused pane = `BorderFocus`; the other `BorderDefault`. |
| **dashboard grid** | rows of `JoinHorizontal` cells with equal `w/n` (remainder to the last cell) stacked by `JoinVertical`; each cell a `titledBox`; severity bars as `█`/`░` runs in `RampLow/Mid/High` + `FgFaint` (see `gauge` in the demo). Recompute widths in `WindowSizeMsg`; never hard-code 80. |
| **modal overlay** | `lipgloss.NewCompositor(lipgloss.NewLayer(frame).ID("base"), lipgloss.NewLayer(box).X((m.w-boxW)/2).Y((m.h-boxH)/2).Z(1).ID("modal")).Render()`; `box` = bordered, `bg = theme.BgOverlay`, border `BorderFocus`, primary button `st(theme.FgOnAccent, theme.AccentPrimary, "bold")`. Modal state is a bool in the model; **while open, route all keys to it first** (focus trap). |
| **small terminals** | guard in `render()`: `if m.w < 40 \|\| m.h < 10 { return lipgloss.Place(m.w, m.h, lipgloss.Center, lipgloss.Center, lipgloss.NewStyle().MaxWidth(m.w).Render("terminal too small (need 40x10)")) }` (`Place` does not clip); `bar` drops its right part; keybar adds hints in priority order only while `Width` fits (VERIFIED at 20x6, 30x8, 40x12, 60x16, 80x24, 120x30, 170x40, with and without the modal: every frame exactly w×h; for ≥40x10 no cell with default bg). |

## 6. Components (Bubbles v2.2.1 and ecosystem)

| Concept | Built in (`charm.land/bubbles/v2/…`) | API essentials | Gap / ecosystem |
|---|---|---|---|
| selectable list (filter, pages, status, help) | `list` | `list.New(items, list.NewDefaultDelegate(), w, h)`; `Item` needs `FilterValue() string`; `SetItems`, `SetSize`, `SetFilteringEnabled`, `StartSpinner` | custom row look = your own `ItemDelegate` |
| table (interactive) | `table` | `table.New(table.WithColumns(c), WithRows(r), WithFocused(true), WithHeight(n))`, `SetStyles` | richer: Evertras `bubble-table` v0.23.0; static: `lipgloss/v2/table` |
| tree | `tree` (**new in v2.2.0**) | `tree.New(root, w, h)`, `ToggleCurrentNode` | static: `lipgloss/v2/tree` |
| text input / area | `textinput`, `textarea` (v2.2.0 adds selection + copy/cut/paste) | `.Focus() tea.Cmd` (returns the blink Cmd: return it), `.Blur()`, `.Value()`, `SetWidth`; `EchoMode` for passwords | |
| scroll view / pager | `viewport` | `viewport.New(WithWidth, WithHeight)`, `SetContent`, `SoftWrap`, `LeftGutterFunc` (line numbers), `SetHighlights` | Markdown: Glamour v2 inside a viewport |
| spinner / progress | `spinner`, `progress` | `spinner.New(spinner.WithSpinner(spinner.Dot))` + `.Tick`; `progress.New(progress.WithColors(c…))`, `SetPercent(p) tea.Cmd` (animated), `ViewAs(p)` (static), `SetWidth` | sparkline/charts: `ntcharts/v2` |
| key hints | `help` + `key` | `help.New()`, `ShortHelpView(bindings)`, `FullHelpView`; `key.NewBinding(key.WithKeys("k","up"), key.WithHelp("↑/k","up"))`, `key.Matches(msg, b…)`, `SetEnabled` | **gap**: help leaves the key/desc gap unstyled (§13 #3) |
| file picker, timer, stopwatch, paginator, cursor | same names | | |
| forms / select / confirm / multiselect | **Huh v2**: `NewInput NewText NewSelect[T] NewMultiSelect[T] NewConfirm NewNote NewFilePicker`; `NewGroup(...)`, `NewForm(...)`, `.WithTheme(huh.ThemeFunc(f))`, `.WithLayout`, `.WithAccessible(true)` | options: `huh.NewOptions("a","b")...` (VERIFIED: bare strings do not compile) | embed: `Update` returns `huh.Model` → `if f, ok := form.(*huh.Form); ok { m.form = f }`; done when `m.form.State == huh.StateCompleted` |
| **tabs, modal, toast, header/footer bar, panel with title, button, command palette** | **none**: compose (Lip Gloss borders, `Compositor`, `tea.Tick`) | `bubbletea/examples/tabs`, `examples/views`, `examples/canvas` | mouse zones: `bubblezone/v2`; toasts = timed layer |

## 7. Focus, keys, mouse

- **No focus manager.** Keep `focus` (int/enum) in the model; call `child.Focus()` / `child.Blur()` and **return the Cmd** from `Focus()`. Tab cycles (`BT:examples/textinputs`). Modal open ⇒ it consumes keys before anything else (VERIFIED: `if m.modal { switch msg.String() { case "y","enter","n","esc": m.modal = false }; return m, nil }`).
- **Keys (v2):** `tea.KeyPressMsg` / `tea.KeyReleaseMsg`; fields `Code rune`, `Text string`, `Mod`, `ShiftedCode`, `BaseCode`, `IsRepeat`; `msg.String()` → `"ctrl+c"`, `"space"`, `"enter"`, `"up"`, `"tab"`. Kitty keyboard: `v.KeyboardEnhancements.ReportEventTypes` → `tea.KeyboardEnhancementsMsg`. Paste: `tea.PasteMsg{Content}`.
- **Keymap + help (the discoverability pattern):** a `keyMap` struct of `key.Binding`; `key.Matches(msg, m.keys.Up)`; implement `ShortHelp() []key.Binding` and `FullHelp() [][]key.Binding` so `help.Model.View(km)` or your own renderer shows the same bindings. Disabled bindings (`SetEnabled(false)`) vanish from help.
- **Mouse:** `v.MouseMode = tea.MouseModeCellMotion | MouseModeAllMotion`; messages `MouseClickMsg, MouseReleaseMsg, MouseWheelMsg, MouseMotionMsg` (`msg.Mouse().X/.Y/.Button`); hit-test with `v.OnMouse` + `Compositor.Hit` (`BT:examples/clickable`) or BubbleZone.
- Terminal focus: `v.ReportFocus = true` → `tea.FocusMsg` / `tea.BlurMsg`. Filter all messages: `tea.WithFilter(func(Model, Msg) Msg)` (`examples/prevent-quit`).

## 8. Async, timers, performance

- `tea.Batch(cmds…)` concurrent, **no order**; `tea.Sequence(cmds…)` ordered. `tea.Tick(d, fn)` and `tea.Every(d, fn)` fire **once**: return them again from `Update` to loop (`BT:commands.go`).
- From outside the program: `p.Send(msg)` (goroutine-safe, `examples/send-msg`); channels: a Cmd that blocks on `<-ch` and is re-issued after each message (`examples/realtime`). External editor/pager: `tea.ExecProcess(exec.Command("vim", f), func(error) tea.Msg)`.
- Permanent lines above an **inline** UI: `tea.Println/Printf` (silently ignored in alt screen).
- Perf: renderer is cell-diffing; `tea.WithFPS(n)` default 60, max 120. Keep `View` free of I/O; cache expensive renders (Glamour output) in the model; debounce key-driven work (`examples/debounce`). `WithANSICompressor` and viewport `HighPerformanceRendering` are gone in v2.

### Debugging and profiling

stdout belongs to the TUI (the program renders on it), so log to a file and profile over a socket. Checked 2026-10-02: **VERIFIED** = run here (Go 1.27.1); **docs** = read in the cited page, not run here; `derived:` = inference.

| Need | Tool | Command / setting | Notes and gotchas | Source |
|---|---|---|---|---|
| Log without corrupting the screen | `tea.LogToFile` | `f, err := tea.LogToFile("debug.log", "debug"); if err != nil { … }; defer f.Close()`, then `log.Println(…)`; second pane: `tail -f debug.log` | **docs.** `LogToFile(path, prefix string) (*os.File, error)` sets the std `log` output to the file (append, created if missing, mode 0600). Gate it on an env var (`if os.Getenv("DEBUG") != ""`) as the README does. `tea.LogToFileWith(path, prefix, logger)` takes a Charm `log` logger. | BT:logging.go; BT:README.md "Logging Stuff" |
| Step through | headless Delve | `dlv debug --headless --api-version=2 --listen=127.0.0.1:43000 .`, then `dlv connect 127.0.0.1:43000` from a second pane | **docs.** The program owns the TTY, so the debugger UI cannot share it | BT:README.md "Debugging with Delve" |
| Profile a slow `Update` / `View` | `net/http/pprof` on loopback | in `main`: `import _ "net/http/pprof"`; `go func() { log.Println(http.ListenAndServe("127.0.0.1:6060", nil)) }()`; second pane: `go tool pprof 'http://127.0.0.1:6060/debug/pprof/profile?seconds=30'` (also `/heap`, `/goroutine`) | **VERIFIED:** the profile downloads and `go tool pprof -top` reads it. **Bind `127.0.0.1`, never `:6060`**: the handlers register on `http.DefaultServeMux` and expose heap and goroutine dumps. Prefer this to file-based `pprof.StartCPUProfile` (derived: a crash or `os.Exit` skips `StopCPUProfile` and the file is empty). Press the keys that make it slow while the 30 s runs; in pprof use `top`, `list <func>`, `web` | https://pkg.go.dev/net/http/pprof |
| Where the cost usually is | read `top -cum` for | `View` doing I/O or rebuilding Glamour / Lip Gloss output on every frame, `Update` blocking on work that belongs in a `tea.Cmd`, a `Tick` loop re-armed too often | derived: §8: cache expensive renders in the model, `tea.WithFPS(n)` (default 60), debounce key-driven work |  §8 |

## 9. Applying our theme tokens

`python3 SKILL_DIR/scripts/export_theme.py ID --target lipgloss -o theme/theme.go` writes `package theme` with **one `lipgloss.Color` var per token** (CamelCase of the token: `bg.base`→`BgBase`, `fg.on-accent`→`FgOnAccent`, `selection.inactive.bg`→`SelectionInactiveBg`) plus ready styles (`Base, Title, Muted, Faint, Pane, PaneFocused, Selected, StatusBar, KeyHintKey/KeyHintDesc, LinkStyle, Success, Warning, Error, Info, Chip*`). Shape (re-checked against the exporter output for `catppuccin-mocha` on 2026-10-01: 43 color vars, then 19 styles):

```go
package theme
import "charm.land/lipgloss/v2"
var (
	BgBase  = lipgloss.Color("#1e1e2e"); BgInset = lipgloss.Color("#181825"); BgSurface = lipgloss.Color("#313244")
	BgRaised = lipgloss.Color("#45475a"); BgOverlay = lipgloss.Color("#313244")
	FgDefault = lipgloss.Color("#cdd6f4"); FgMuted = lipgloss.Color("#a6adc8"); FgFaint = lipgloss.Color("#7f849c")
	BorderDefault = lipgloss.Color("#6c7086"); BorderFocus = lipgloss.Color("#b4befe"); AccentPrimary = lipgloss.Color("#89b4fa")
	SelectionBg = lipgloss.Color("#3b3d4f") // … every token of _tokens.json, tier-2 fallbacks already resolved
)
```
Color vars and style vars share one namespace: the link style is `LinkStyle` (the color is `Link`), and the key-hint **color** `KeyhintKey` differs from the key-hint **style** `KeyHintKey` only by case (pitfall 14).

**Runtime alternative** (VERIFIED, 50 lines): read `references/themes/<id>.json` + `_tokens.json`, resolve `tokens[tok]` (palette name or `#hex`), else follow `fallback`, into `map[string]string`; wrap with `lipgloss.Color`. Use only for theme switching at startup; generated consts give compile-time checks.

**Dark/light:** export one dark and one light theme into two packages and pick with `lipgloss.LightDark(isDark)(light.AccentPrimary, dark.AccentPrimary)`, where `isDark` comes from:
```go
func (m model) Init() tea.Cmd { return tea.RequestBackgroundColor }
// Update: case tea.BackgroundColorMsg: m.isDark = msg.IsDark(); m.help.Styles = help.DefaultStyles(m.isDark) …
```
In `View()` set `v.BackgroundColor = theme.BgBase; v.ForegroundColor = theme.FgDefault` so the terminal's own default colors match what you paint (OSC 11/10). Cells you do not paint still show the terminal background, hence `st()` always sets a bg.

**Bubbles and Huh** (VERIFIED to compile and render; `themed.go`): start from `DefaultStyles(isDark)`, override fields with tokens.

| Component field | Token |
|---|---|
| `help.Styles.ShortKey` / `ShortDesc` / `ShortSeparator` | `KeyhintKey` bold / `KeyhintDesc` / `FgFaint` |
| `list.Styles.Title` | `FgOnAccent` on `AccentPrimary`; `StatusBar`, `HelpStyle` → `FgMuted` |
| `list.DefaultItemStyles` `SelectedTitle/Desc` (left border bar) | `BorderForeground(AccentPrimary)`, title `SelectionFg`, desc `FgMuted`; `Normal*` → `FgDefault`/`FgMuted`; `Dimmed*` → `FgFaint` |
| `table.Styles.Header` / `Selected` | `TableHeader` bold / `SelectionFg` on `SelectionBg` bold |
| `textinput.Styles.Focused.{Prompt,Placeholder,Text}`; `Cursor` | `AccentPrimary`, `FgFaint`, `FgDefault`; `CursorBg` |
| `huh.Styles.Focused.{Base border, Title, Description, ErrorMessage, SelectSelector, SelectedOption, FocusedButton, BlurredButton, TextInput.*}` | `BorderFocus`, `FgTitle` bold, `FgMuted`, `StatusError`, `AccentPrimary`, `StatusSuccess`, `FgOnAccent` on `AccentPrimary`, `FgDefault` on `BgRaised` |

```go
func HuhTheme(isDark bool) *huh.Styles {
	t := huh.ThemeBase(isDark); f := &t.Focused
	f.Base = f.Base.BorderForeground(theme.BorderFocus); f.Card = f.Base
	f.Title = f.Title.Foreground(theme.FgTitle).Bold(true)
	f.FocusedButton = f.FocusedButton.Foreground(theme.FgOnAccent).Background(theme.AccentPrimary)
	// … remaining fields as in the table …
	t.Blurred = t.Focused // blurred = focused with the left bar hidden
	t.Blurred.Base = t.Focused.Base.BorderStyle(lipgloss.HiddenBorder()); t.Blurred.Card = t.Blurred.Base
	t.Blurred.NextIndicator, t.Blurred.PrevIndicator = lipgloss.NewStyle(), lipgloss.NewStyle()
	return t
} // use: huh.NewForm(groups...).WithTheme(huh.ThemeFunc(HuhTheme))
```
Huh's built-in `ThemeBase16` discards three style results (`t.Focused.TextInput.Cursor.Foreground(...)` without assignment) so its cursor/placeholder/prompt colors never apply (read in the `ThemeBase16` source): copy the pattern above, not that theme.

## 10. Color profiles, NO_COLOR, wide characters, alt screen vs inline

- **Profile:** `colorprofile.Detect(w, env)` → `NoTTY < ASCII < ANSI < ANSI256 < TrueColor`; Bubble Tea calls it on its output; force with `tea.WithColorProfile(colorprofile.TrueColor)`. Rules (`CP:env.go`, read): `TERM=dumb` ⇒ NoTTY unless `CLICOLOR_FORCE`; `COLORTERM=truecolor|24bit|yes|true` ⇒ TrueColor **except when `TERM` starts with `tmux` or `screen`** (the source comment: "tmux doesn't support $COLORTERM"); `TTY_FORCE=1` treats output as a TTY. **Consequence (VERIFIED):** inside tmux a Charm app gets 256 colors (`38;5;111`) even with `COLORTERM=truecolor`; launch it as `env TERM=xterm-256color COLORTERM=truecolor ./app` to get `38;2;r;g;b` (checked with `SKILL_DIR/scripts/capture_tui.sh … -- env TERM=xterm-256color COLORTERM=truecolor ./app`).
- **NO_COLOR (VERIFIED):** applied **only when the output is a TTY**: then profile = `ASCII` (colors dropped, bold/underline kept; observed 0 color SGR, bold kept). Piped, `NO_COLOR=1` alone gives no escapes anyway (NoTTY), but `NO_COLOR=1 CLICOLOR_FORCE=1` piped **still emits color** (CLICOLOR_FORCE wins; the doc comment claiming NO_COLOR precedence is wrong for that path). Never encode state by color alone: ASCII profile keeps only bold/reverse/underline, so selection needs a glyph (`❯`) and severity a glyph or word.
- **Downsampling is at output**: `Style.Render()` always yields truecolor; the program writer downsamples to the detected profile. 16-color fidelity = use the theme's `ansi16` values (`../color-tokens.md`) with `lipgloss.Complete(profile)(ansi, ansi256, truecolor)`.
- **Wide chars:** measured with `x/ansi`, `clipperhouse/displaywidth`, `uniseg`; CJK and emoji measured correctly. Prefer single-cell glyphs anyway (`../visual-vocabulary.md` V1). Hyperlinks: `Style.Hyperlink(url)` emits OSC 8 (v2).
- **Alt screen vs inline:** inline default; `v.AltScreen = true` per frame (toggle at runtime: `examples/altscreen-toggle`). `tea.Println` works inline only. Use inline for prompts/wizards/progress that should leave output in scrollback; alt screen for panes.

## 11. Testing

- **Pure frame test (preferred; VERIFIED):** `var m tea.Model = newModel(); m, _ = m.Update(tea.WindowSizeMsg{Width: 80, Height: 24}); golden.RequireEqual(t, m.View().Content)` with `golden "github.com/charmbracelet/x/exp/golden"`; first run / refresh: `go test ./... -update`; files `testdata/<TestName>.golden` keep the SGR (style regressions show as escaped diffs).
- **Flow test with teatest v2 (VERIFIED):**
```go
tm := teatest.NewTestModel(t, newModel(), teatest.WithInitialTermSize(80, 24),
	teatest.WithProgramOptions(tea.WithColorProfile(colorprofile.TrueColor)))
tm.Send(tea.KeyPressMsg{Code: 'r', Text: "r"})
teatest.WaitFor(t, tm.Output(), func(b []byte) bool { return bytes.Contains(b, []byte("Restart service")) }, teatest.WithDuration(2*time.Second))
tm.Send(tea.KeyPressMsg{Code: tea.KeyEscape}); tm.Send(tea.KeyPressMsg{Code: 'q', Text: "q"})
tm.WaitFinished(t, teatest.WithFinalTimeout(2*time.Second))   // tm.FinalModel(t).(model) for assertions
```
Import `github.com/charmbracelet/x/exp/teatest/v2`; it runs the real program on in-memory I/O with `WithoutSignals`. Use it for interaction flows only (goroutines); frame correctness belongs in golden tests. Upstream uses the same golden approach in `bubbletea/testdata`.
- **Assertions worth adding:** every line of `View().Content` has `lipgloss.Width == m.w`, `lipgloss.Height == m.h` at 40x12, 80x24, 120x30, 170x40; a modal frame equals the base frame outside the box.

## 12. One static frame at a forced size, as ANSI (what the proto-starters use)

v2 `Render()` is truecolor regardless of TTY, and `View().Content` is a plain string, so no terminal is needed (VERIFIED, `-static -w 80 -h 24`; 24 rows, max width 80):

```go
func renderFrame(m tea.Model, w, h int, p colorprofile.Profile, out io.Writer) {
	m, _ = m.Update(tea.WindowSizeMsg{Width: w, Height: h})        // the first message the runtime sends
	cw := &colorprofile.Writer{Forward: out, Profile: p}            // TrueColor | ANSI256 | ANSI | ASCII | NoTTY (strips all SGR)
	fmt.Fprint(cw, m.View().Content+"\n")
}
```
Observed: `TrueColor` → `ESC[38;2;137;180;250m…`; `ANSI256` → `38;5;111`; `ASCII` keeps bold only; `NoTTY` = plain text with box drawing intact (this is the `.txt` for audits); OSC 8 survives TrueColor. Caveats: `Init()` Cmds do not run, so feed the Msgs that produce "loaded"/"error"/"busy" state through `Update` before `View()` (spinner = frame 0); pre-set the model (`modal: true`) for overlay states. Check the result with `uv run SKILL_DIR/scripts/ansi_grid.py frame.ansi --cols 80 --rows 24` or diff against the mock: the Fleet demo had **0 differing cells** vs `render_mockup.py fleet--normal--80x24.mock`. A real-runtime capture (alt screen, resize, keys): `SKILL_DIR/scripts/capture_tui.sh -s 80x24 -s 120x30 -k Down -k r -o out -- env TERM=xterm-256color COLORTERM=truecolor ./app` (the `env` is what keeps truecolor, §10). Running a full `tea.NewProgram` with `WithOutput(buf)` for clean frames is UNVERIFIED (cursor-movement sequences).

## 13. Pitfalls and anti-patterns (symptom → cause → fix → source)

| # | Symptom | Cause | Fix | Source |
|---|---|---|---|---|
| 1 | Does not compile / odd behavior copied from a blog | v1 code against v2 (`View() string`, `tea.KeyMsg` struct, `WithAltScreen`, `AdaptiveColor`, `viewport.New(80,24)`) | §1 table; run `go build` before anything else | `BT:UPGRADE_GUIDE_V2.md` |
| 2 | Frame is 1+ columns too wide; panes drift apart; right pane starts at the wrong column | `JoinHorizontal` pads blocks to the widest line; a fixed-width row or a title longer than the pane widens it (VERIFIED at 40 columns: 41-wide frame) | clip every row (`MaxWidth(w-2)`), truncate titles to `w-6`, assert `Width(frame) == m.w` in tests | VERIFIED |
| 3 | 1-cell stripe in the wrong color between a key and its label on a filled footer | `help.Model.ShortHelpView` renders `key + " " + desc` with the **space unstyled** (VERIFIED in the SGR dump) | render hints yourself from `key.Binding.Help()` with bg on every span (`hint()` in the demo), or give the bar no bg | `BUB:help/help.go`, VERIFIED |
| 4 | Background "leaks": cells show the terminal bg inside a painted area | an inner `Render` ends with `ESC[m`, which cancels any outer `Background`; blank cells are never painted | give every span a bg (`st(fg,bg)`), pad with `fill(n, style)`, set `View.BackgroundColor`; check with a cell scan (0 cells with default bg in the demo) | VERIFIED; `LG:UPGRADE_GUIDE_V2.md` |
| 5 | Border title missing / hand-written `╭─ Title ─╮` misaligned | Lip Gloss v2 has no border-title API | `titledBox` (§5): compose the top row, `w-5-Width(title)` dashes | checked `lipgloss@v2.0.6` |
| 6 | Pane is taller/wider than computed | v2 `Width` is total incl. border+padding, `Height` is a minimum (wrapped content grows it) | derive inner sizes with `GetHorizontalFrameSize()`; clip with `MaxHeight`; size children from `WindowSizeMsg` | VERIFIED |
| 7 | Spinner or cursor frozen, list ignores keys | message not forwarded to the child, or the returned child not reassigned (value receivers) | `m.child, cmd = m.child.Update(msg)` for every message; `tea.Batch` the cmds | `BT:README.md` |
| 8 | UI corrupted by prints | `fmt.Println` shares the TUI's stdout | `tea.LogToFile`; `tea.Println` (inline only; dropped in alt screen) | `BT:README.md` (Debugging) |
| 9 | Animation stops after one tick | `tea.Tick`/`Every` fire once | return the Cmd again from `Update` | `BT:commands.go` |
| 10 | Dark-theme colors on a light terminal, unreadable bubble styles | bubbles v2 do not auto-adapt | request the background color, then `help.DefaultStyles(isDark)` etc. | `BUB:UPGRADE_GUIDE_V2.md` §4 |
| 11 | `huh` form never completes / nil-type panic | forgot `form.Init()` or the `(*huh.Form)` assertion after `Update` | §6 embed snippet; check `State == huh.StateCompleted` | `HUH:examples/bubbletea` |
| 12 | Colors are 256-color in tmux captures although `COLORTERM=truecolor` | colorprofile ignores `COLORTERM` when `TERM` starts with `tmux`/`screen` | `env TERM=xterm-256color COLORTERM=truecolor ./app` | `CP:env.go`, VERIFIED |
| 13 | `NO_COLOR` set but piped output still colored | `CLICOLOR_FORCE=1` also set; NO_COLOR only wins on a TTY | don't export CLICOLOR_FORCE for scripts honoring NO_COLOR | VERIFIED |
| 14 | `theme.KeyhintKey` (a color) used where a style is expected, or the reverse | token CamelCase `KeyhintKey` (color) and the ready style `KeyHintKey` differ only by case | colors feed `.Foreground(...)`, styles feed `.Render(...)` | §9 (re-checked 2026-10-01) |

## 14. Showcase apps and official examples worth reading

Real-world references (`BT:README.md`): **gh-dash** (multi-pane GitHub dashboard), **Superfile** (file manager, sub-model packages), chezmoi, Glow (Markdown pager), Huh, Mods, Wishlist; community list: github.com/charm-and-friends/charm-in-the-wild. Go apps built on other libraries for comparison: **lazygit / lazydocker** (jesseduffield/gocui + boxlayout: numbered left panel stack + main pane), **k9s** (tview fork: header with context-sensitive key hints, table, crumbs, flash row).

`BT:examples/` (63 dirs; the ones that teach a design pattern): `views` (multiple screens in one model), `composable-views` (two sub-models), `tabs` (tabs from borders), `list-fancy` (custom delegate, status messages), `table`, `table-resize`, `help` (key map → help bubble), `textinputs` (focus cycling), `split-editors` and `dynamic-textarea` (several textareas), `chat` (textarea + viewport), `pager`, `glamour` (Markdown), `canvas` and `clickable` (layers, hit-testing), `package-manager` (progress + `tea.Println` above an inline UI), `vanish` (inline UI that clears itself), `tui-daemon-combo` (TUI when interactive, plain logs when not), `realtime` and `send-msg` (external events), `exec` (spawn `$EDITOR`), `debounce`, `prevent-quit`, `altscreen-toggle`, `keyboard-enhancements`, `colorprofile`, `result` (return a value after quit). Huh: `HUH:examples/` `bubbletea` (embed), `theme`, `layout`, `dynamic`, `accessibility`, `spinner`.
