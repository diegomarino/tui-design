# Ink (React for terminals) — getting-started and design reference

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [1. Versions and install (as of 2026-10-01)](#1-versions-and-install-as-of-2026-10-01) · L23–36 — pinning versions and installing.
- [2. Mental model](#2-mental-model) · L38–44 — first contact: how the framework thinks.
- [3. Minimal app](#3-minimal-app-verified-runs-under-a-pty-with-npx-tsx-apptsx-its-test-passes) · L46–88 — a verified minimal app to copy.
- [4. Project layout](#4-project-layout) · L90–92 — file layout of a real app.
- [5. Layout system](#5-layout-system) · L94–123 — sizing panes, flex and grid, breakpoints.
- [6. Components](#6-components) · L125–137 — which built-in or ecosystem widget to use.
- [7. Focus, keys, mouse](#7-focus-keys-mouse) · L139–146 — key bindings, focus order, mouse.
- [8. Async, timers, performance](#8-async-timers-performance) · L148–167 — background work, streaming, frame rate, flicker.
- [9. Applying our theme tokens](#9-applying-our-theme-tokens) · L169–242 — wiring `export_theme.py` output into styles.
- [10. Color depth, NO_COLOR, wide characters, links, screens](#10-color-depth-no_color-wide-characters-links-screens) · L244–250 — colour depth, NO_COLOR, wide characters, alt screen vs inline.
- [11. Testing](#11-testing) · L252–274 — unit, snapshot and PTY tests.
- [12. One static frame at a forced size, as ANSI](#12-one-static-frame-at-a-forced-size-as-ansi-what-the-proto-starters-use) · L276–327 — frame mode: one ANSI frame at a forced size (for `compare.py`).
- [13. Pitfalls and anti-patterns](#13-pitfalls-and-anti-patterns-symptom--cause--fix) · L329–351 — something renders or behaves wrong (symptom → fix).
- [14. Showcase apps and official examples worth reading](#14-showcase-apps-and-official-examples-worth-reading) · L353–371 — real code worth reading.

Read this when you design, build, theme or capture a terminal UI with **Ink** (Node/TypeScript, React components, Yoga flexbox) or **@inkjs/ui**.

Source keys: `INK:` https://github.com/vadimdemedes/ink/blob/master/ (readme.md, src/…) · `INKUI:` https://github.com/vadimdemedes/ink-ui/blob/main/ · `ITL:` https://github.com/vadimdemedes/ink-testing-library/blob/master/. **VERIFIED** = run on 2026-10-01 with Node 26.9, Ink 7.1.1, React 19.3.0, @inkjs/ui 2.0.0 (also type-checked with `tsc --strict`). `UNVERIFIED` = not confirmed. `derived:` = inference.

## 1. Versions and install (as of 2026-10-01)

| Package | Version | Notes |
|---|---|---|
| `ink` | **7.1.1** (2026-07-16) | MIT; Node >=22; peer `react >=19.2.0`, `@types/react >=19.2.0` (VERIFIED in the published package.json; repo HEAD asks for 19.3, ahead of the tag). Check: `npm view ink` |
| `@inkjs/ui` | 2.0.0 (2024-05-22, dormant) | peer `ink >=5`; **works on Ink 7** (VERIFIED: all components render) |
| `ink-testing-library` | 4.0.0 (2024-05-22, dormant) | works on Ink 7 (VERIFIED) |
| `create-ink-app` | 3.0.2 | **template pins `ink ^4.1.0`, `react ^18.2.0`: stale**, bump after scaffolding (`vadimdemedes/create-ink-app/templates/ts/_package.json`) |

```sh
npm install ink react chalk string-width strip-ansi   # chalk/string-width/strip-ansi are Ink's deps; add them directly if you import them
npm install -D tsx typescript @types/react @types/node   # tsx runs .tsx without a build step
```
Master `readme.md` documents the **upcoming** release (e.g. `contentOffsetX/Y` is on master, absent from 7.1.1: `grep contentOffsetY node_modules/ink/build` = 0 hits, VERIFIED). Check `node_modules/ink/build/*.d.ts` before using a readme feature.

## 2. Mental model

- A React tree is the source of truth. `<Box>` = a Yoga flexbox node ("every `<div>` is `display:flex`"); `<Text>` = a text node measured with `string-width`. All text must be inside `<Text>` (a bare string throws: `Text string "x" must be rendered inside <Text> component`, VERIFIED). Source: INK:readme#getting-started, INK:src/reconciler.ts.
- Every commit re-renders the **whole** frame to a string; `log-update` erases the previous frame and writes the new one; throttled by `maxFps` (default 30); `incrementalRendering: true` rewrites only changed lines (INK:readme#maxfps).
- **Inline by default**: the live region sits below the cursor. Full screen is opt-in: `render(<App/>, {alternateScreen: true})` (Ink >=7.0) (INK:readme#alternatescreen).
- `<Static>` writes items once, above the live region, and never redraws them (logs, finished tasks) (INK:readme#static).
- Interactivity is auto-detected (`!isInCi && stdout.isTTY`); when non-interactive (CI/pipe) Ink writes **only the final frame** at unmount (INK:readme#interactive).

## 3. Minimal app (VERIFIED: runs under a pty with `npx tsx app.tsx`; its test passes)

```tsx
// app.tsx — run: npx tsx app.tsx
import React, {useState} from 'react';
import {render, Box, Text, useApp, useInput} from 'ink';

const items = ['Build', 'Test', 'Deploy'];

export function App() {
	const {exit} = useApp();
	const [cursor, setCursor] = useState(0);
	useInput((input, key) => {
		if (input === 'q' || key.escape) exit();
		if (key.upArrow || input === 'k') setCursor(c => Math.max(0, c - 1));
		if (key.downArrow || input === 'j') setCursor(c => Math.min(items.length - 1, c + 1));
	});
	return (
		<Box flexDirection="column" borderStyle="round" borderColor="cyan" paddingX={1}>
			<Text bold>Pipeline</Text>
			{items.map((item, i) => (
				<Text key={item} color={i === cursor ? 'cyan' : undefined}>{i === cursor ? '❯ ' : '  '}{item}</Text>
			))}
			<Text dimColor>↑/↓ move · q quit</Text>
		</Box>
	);
}
if (process.argv[1] === import.meta.filename) render(<App />);
```
Lifecycle: the process lives while the event loop has work (a `useInput` listener or timer). Exit with Ctrl+C (`exitOnCtrlC`, default true), `useApp().exit(errorOrResult?)`, `instance.unmount()`; `await instance.waitUntilExit()` to run code afterwards (INK:readme#app-lifecycle). `package.json` needs `"type": "module"`.

### Lifecycle, signals and exit status

Read in `build/ink.js`, `build/components/App.js`, `build/components/AppContext.d.ts` and `readme.md` of 7.1.1, and `signal-exit` 3.0.7 (Ink's dependency, `^3.0.7`); "Since" from the published tarballs. **VERIFIED** = run 2026-10-02 with Node 26.9 in an isolated `tmux -L` (bash job control for Ctrl+Z); `#{alternate_on}` and `stty -a` read after exit. The rules behind it: `../lifecycle.md` LC1, LC3, LC9-LC11.

| Path | Ink 7.1.1 | What you add | Since |
|---|---|---|---|
| quit | `useApp().exit(errorOrResult?)` or `instance.unmount()`; `waitUntilExit()` settles after the unmount writes are flushed: resolves with the value, rejects with an `Error` | write post-run output and set the status only after it: `process.exitCode = code`. Not `process.exit()`: it can cut pending writes (`derived:` from the flush note) | |
| Ctrl+C | `exitOnCtrlC` (default true) matches only the input byte `\x03` in raw mode (`App.js`) and calls `exit()` with no value → **status 0** (VERIFIED) | `exitOnCtrlC: false`; on `key.ctrl && input === 'c'` call `exit(new Error('cancelled'))`, catch the rejection, `process.exitCode = 130` | |
| SIGTERM | `exitOnCtrlC` is not a signal handler. The `Ink` constructor registers `signal-exit`, which unmounts and, when it is the only listener, re-raises the signal; Node's default handler then resets the TTY and exits 128 + 15 → **143, terminal restored** (VERIFIED) | nothing by default. If you add `process.on('SIGTERM', …)`, signal-exit stops acting (it checks `listeners.length === emitter.count`): call `instance.unmount()`, await `waitUntilExit()`, set `process.exitCode = 143` (VERIFIED: 143, restored) | |
| `$EDITOR` handoff | `await useApp().suspendTerminal(async () => runChild())`: stops output and input, leaves the alt screen, raw mode, bracketed paste and kitty flags off, cursor shown; when the callback settles (also on throw) re-enters and redraws from scratch. Without a callback it returns `{resume}` (also `await using`). A second suspension while one is active **throws**; non-interactive: the callback runs, no handoff (VERIFIED: the child saw `icanon`, alt screen off during, back and redrawn after) | reload changed data after it (the redraw keeps React state); keep suspension in one place | **7.1.0** (absent in 7.0.0, 7.0.1, 7.0.6) |
| Ctrl+Z | no API; raw mode delivers `\x1a` as input | UNVERIFIED: `suspendTerminal(() => new Promise(r => { process.once('SIGCONT', r); process.kill(process.pid, 'SIGTSTP'); }))` stopped the job and got SIGCONT on `fg`, but Ink did not re-enter the alt screen or redraw in our run. Prefer a shell-out key | |
| Windows | Node "Signal events": "'SIGTERM' is not supported on Windows, it can be listened on"; `SIGHUP` when the console window is closed (killed about 10 s later); `SIGBREAK` on Ctrl+Break (https://nodejs.org/api/process.html#signal-events) | a shell-out key through `suspendTerminal` instead of Ctrl+Z | |

## 4. Project layout

`create-ink-app --typescript` produces (gh `vadimdemedes/create-ink-app/templates/ts/`): `package.json` (`"bin": "dist/cli.js"`), `source/cli.tsx` (args via `meow`, then `render(<App/>)`), `source/app.tsx`, `source/test.tsx` (ava + ink-testing-library), `tsconfig.json` from `@sindresorhus/tsconfig`. Our recommendation (derived): keep `render()` only in `cli.tsx`; export `App` and pure view components from `app.tsx` so tests and frame capture import them without starting a render; put `theme.ts` (generated, section 9) beside them; `frame.tsx` for section 12.

## 5. Layout system

`<Box>` props as in 7.1.1 `build/styles.d.ts`:

| Group | Props |
|---|---|
| Size | `width`, `height` (cells or `"50%"`); `minWidth`, `maxWidth` (numbers only: Yoga #872); `minHeight`, `maxHeight`; `aspectRatio` |
| Spacing | `padding`, `paddingX/Y/Top/Bottom/Left/Right`, same for `margin*`; `gap`, `columnGap`, `rowGap` |
| Flex | `flexDirection` (`row` default, `column`, `*-reverse`); `flexGrow` (0); `flexShrink` (**1**); `flexBasis`; `flexWrap` |
| Align | `alignItems`, `alignSelf`, `justifyContent`, `alignContent` (default `flex-start`, unlike CSS `stretch`) |
| Position | `position` (`relative` default, `absolute`, `static`) with `top/right/bottom/left` |
| Visibility | `display` (`flex`\|`none`); `overflow`/`overflowX`/`overflowY` = `visible`\|`hidden` only (no scrollbars) |
| Border | `borderStyle`: `single double round bold singleDouble doubleSingle classic` or a custom `BoxStyle`; `borderColor`, `borderDimColor`, `borderBackgroundColor` (+ per side); `borderTop/Right/Bottom/Left` (booleans) |
| Fill | `backgroundColor` fills the box; child `<Text>` inherits it unless it sets its own (VERIFIED) — **but not the border cells** (section 13, item 4) |

`<Text>`: `color`, `backgroundColor`, `dimColor`, `bold`, `italic`, `underline`, `strikethrough`, `inverse`, `wrap` (`wrap` default, `hard`, `truncate`/`truncate-end`, `truncate-start`, `truncate-middle`). Only strings and nested `<Text>` inside.

Measuring: `measureElement(ref)` (returns zeros during render, call in an effect), `useBoxMetrics(ref)` → `{width,height,left,top,clientWidth,clientHeight,hasMeasured}`, `useWindowSize()` → `{columns, rows}` (re-renders on resize; falls back to 80x24).

**Archetype mapping** (patterns verified in the themed frame of section 9):

| Archetype | Ink recipe |
|---|---|
| Whole screen | root `<Box flexDirection="column" width={columns} height={rows}>`; `rows` from `useWindowSize()` (live) or a prop (frames) |
| Header / footer bands | first and last child `<Box height={1} flexShrink={0} paddingX={1}>`; left text, `<Spacer/>`, right text; middle child `<Box flexGrow={1}>` |
| List + detail | body `<Box flexGrow={1}>` containing the list pane `<Box width="40%" flexShrink={0} flexDirection="column" borderStyle="round">` and the detail pane `<Box flexGrow={1} …>` |
| Dashboard (cards) | body `<Box flexWrap="wrap">` with cards `width="50%"` (or rows of `flexGrow` boxes with `gap={1}`) |
| Table | one `<Box>` per row, one fixed-width `<Box width={n} flexShrink={0}><Text wrap="truncate">` per cell, one `flexGrow` cell; **never one hand-padded string per row** |
| Scrolling list | slice `items.slice(offset, offset + viewH)` and show `↑ N more` / `↓ N more`; slicing beats `overflow="hidden"` because goldens see what the user sees |
| Modal | `<Box position="absolute">` overlay and gate other `useInput` handlers with `isActive: !modalOpen` |

## 6. Components

| Need | Built in (Ink 7.1.1) | @inkjs/ui 2.0.0 (`INKUI:source/index.ts`) | Ecosystem (readme "Useful Components") |
|---|---|---|---|
| Layout/text | `Box`, `Text`, `Spacer`, `Newline`, `Transform`, `Static` | — | `ink-titled-box`, `ink-divider` |
| Input | hooks `useInput`, `usePaste`, `useCursor` | `TextInput` (`placeholder`, `defaultValue`, `suggestions`, `onChange`, `onSubmit`), `EmailInput`, `PasswordInput`, `ConfirmInput` | `ink-text-input`, `ink-quicksearch-input`, `ink-form` |
| Choice | — | `Select` (`options: {label,value}[]`, `visibleOptionCount` 5; inline list, not a dropdown), `MultiSelect` | `ink-select-input`, `ink-multi-select`, `ink-tab` |
| Feedback | — | `Spinner`, `ProgressBar` (`value` 0–100), `Badge`, `StatusMessage` (`variant`), `Alert` | `ink-spinner`, `ink-progress-bar`, `ink-task-list` |
| Lists | — | `UnorderedList`, `OrderedList` (items must wrap content in `<Text>`) | `ink-table` (static), `ink-scroll-view`, `ink-virtual-list` |
| Rich | — | — | `ink-markdown`, `ink-syntax-highlight`, `ink-chart` (sparkline/bar), `ink-link` (OSC 8), `ink-gradient`, `ink-big-text`, `ink-picture` |
| Theming | — | `ThemeProvider`, `extendTheme`, `defaultTheme`, `useComponentTheme` | — |

No table, tree, tabs, text area, modal, command palette, scroll view or mouse in core: compose them (names across frameworks: `../vocabulary.md`).

## 7. Focus, keys, mouse

- `useInput((input, key) => …, {isActive?})`. `key`: `upArrow downArrow leftArrow rightArrow return escape tab shift ctrl meta backspace delete pageUp pageDown home end` (+ `super hyper capsLock numLock eventType`). Since 7.0 Backspace sets `key.backspace` (before: `key.delete`) and plain Esc no longer sets `key.meta` (release v7.0.0). Many `useInput` hooks all receive every key: gate with `isActive`.
- Paste: `usePaste(handler)` enables bracketed paste; pasted text never reaches `useInput`. Kitty protocol: `render(…, {kittyKeyboard: {mode: 'auto'|'enabled'|'disabled', flags: […]}})` disambiguates Ctrl+I/Tab, Shift+Enter, Esc/Ctrl+[ (INK:readme#kittykeyboard).
- Focus: `useFocus({autoFocus, isActive, id})` → `{isFocused}`; Tab/Shift+Tab cycle in registration order; `useFocusManager()` → `focusNext/Previous/focus(id)/enableFocus/disableFocus/activeId`. No focus scope or trap (derived: gate `useInput` or `disableFocus()` while a modal is open). Don't mix `useFocus` with a custom focus model.
- Text cursor: `useCursor().setCursorPosition({x, y})` (compute `x` with `string-width`) for IME.
- **Mouse: none in core.** If you need it: enable SGR tracking yourself (`\x1b[?1002h\x1b[?1006h`, off on exit), parse `\x1b[<btn;x;y(M|m)`; this disables terminal text selection. Keep every action keyboard-reachable.
- Hand the TTY to `$EDITOR`/`less`: `useApp().suspendTerminal(cb?)` (7.1.0+; behavior in the §3 lifecycle table).

## 8. Async, timers, performance

- Async is plain React: `useEffect` with cleanup; `render(…, {concurrent: true})` enables Suspense/`useTransition` (examples `concurrent-suspense`, `use-transition`).
- Timers: `useAnimation({interval = 100, isActive})` → `{frame, time, delta, reset}`; all animations share one timer (INK:readme#useanimationoptions). Inject `now` into views; `Date.now()` in render breaks goldens.
- Cost: every state change re-serializes the whole frame. Mitigate: history to `<Static>`; lower `maxFps`; `incrementalRendering: true`; virtualize long lists; write side output with `useStdout().write` (`patchConsole: true` keeps `console.log` above the frame).
- **Keep the live region shorter than `rows`.** When output height exceeds `stdout.rows` Ink clears the terminal incl. scrollback (`ESC[3J`) on every frame: flicker + lost scrollback (issues #935, #990, #359, #450; `shouldClearTerminalForFrame` in `build/ink.js`).

### Debugging and profiling

stdout belongs to the frame, so a stray `console.log` or a profiler's progress text redraws over it. Checked 2026-10-02: **VERIFIED** = run here (Node 26.9); **docs** = read in the cited page, not run here; `derived:` = inference.

| Need | Tool | Command / setting | Notes and gotchas | Source |
|---|---|---|---|---|
| Output without corrupting the frame | `patchConsole` (default on) | `console.log(…)` inside the app prints above the live frame | disable only when you own all output; `useStdout().write` is the explicit path | INK:readme (`patchConsole`) |
| "Which frame went wrong?" | `render(<App/>, {debug: true})` | each update is rendered as separate output, without replacing the previous one (INK:readme `debug`: https://github.com/vadimdemedes/ink#debug) | **docs.** Frames pile up in the scrollback instead of overwriting: read the sequence in a tmux pane (`tmux capture-pane -S - -p`), or redirect stdout to a file (derived: non-TTY stdout, so test input via a script, not raw keys). `ink-testing-library` already runs with `debug: true` (§11) | INK:readme |
| Log lines you can tail | a file | `fs.appendFileSync('debug.log', JSON.stringify(x) + '\n')`, then `tail -f debug.log` in a second pane | derived: any logger with a file transport works; never `console.error` while the frame is live unless `patchConsole` is on | derived |
| Profile a slow render or update loop | `node --cpu-prof` | `node --cpu-prof --cpu-prof-dir=prof app.js` (a `.tsx` entry: build first, or `node --cpu-prof --import tsx app.tsx`, UNVERIFIED) | **VERIFIED:** writes `prof/CPU.<date>.<time>.<pid>.<tid>.<seq>.cpuprofile` **on exit**, so quit the app normally (`useApp().exit()`); a `kill -9` leaves nothing. Open the file in Chrome DevTools (Performance, Load profile) or `speedscope`. `--cpu-prof-interval` default 1000 us | https://nodejs.org/api/cli.html#--cpu-prof |
| Where the cost usually is | read the flame chart for | the render path (`Output`, Yoga layout, `string-width`), React re-renders of big lists, `useAnimation` / `setInterval` ticks that change state every frame | mitigations in the §8 "Cost" bullet. A spinner leaf that ticks keeps the render loop hot even when nothing else changes | §8 |

React DevTools (Components tab: tree, props): `npm i -D react-devtools-core`, run `DEV=true node app.js`, then `npx react-devtools` in another terminal; quit the app with Ctrl+C when done (INK:readme "Using React Devtools", **docs**). It shows the component tree, not the terminal frame; use `debug: true` for frames.

## 9. Applying our theme tokens

Ink has **no theme system in core**: colors are props (`color`, `backgroundColor`, `borderColor`, …) taking chalk names, `#rrggbb`, `rgb(r,g,b)` or `ansi256(n)`; unknown strings are silently ignored (INK:src/colorize.ts). So: generate a map of resolved hex and pass tokens as props. `SKILL_DIR/scripts/export_theme.py ID --target ink -o theme.mjs` (JS, valid in TS too; use `-o theme.ts` if you want that extension) writes a comment header, `import {defaultTheme, extendTheme} from '@inkjs/ui'`, then `export const theme = {...}` and `export const inkTheme = extendTheme(...)`. Real output for `catppuccin-mocha` (re-checked 2026-10-01; header comments omitted):

```ts
import {defaultTheme, extendTheme} from '@inkjs/ui';

export const theme = {          // every token of _tokens.json, tier-2 fallbacks resolved (43 keys)
  'bg.base': '#1e1e2e', 'bg.inset': '#181825', /* … */ 'ramp.high': '#f38ba8',
};
// Usage: <Text color={theme['status.error']} bold>failed</Text>

export const inkTheme = extendTheme(defaultTheme, {components: {
  Spinner: ..., ProgressBar: ..., Badge: ..., Alert: ..., StatusMessage: ..., Select: ...,   // token-colored style functions
}});
// <ThemeProvider theme={inkTheme}>…</ThemeProvider>
```

There is no `themeId`, `terminal` or `Token` export; the map is `theme` (the table below calls it `T`: `import {theme as T} from './theme.js'`). `inkTheme` themes only Spinner (`frame`), ProgressBar (`completed`/`remaining`), Badge (`label` = `fg.on-accent`), Alert (`container` border + `icon` by variant), StatusMessage (`icon`) and Select (`focusIndicator`/`selectedIndicator`/`label`); gaps: no `MultiSelect`, `ConfirmInput`, `UnorderedList` and no `Spinner` `label` override. The fuller hand-written theme below fills them.

Token → Ink mapping (rows for `bg.base`, `statusbar.*`, `border.*`, `fg.title`, `selection.*`, `status.*`, `keyhint.*` are VERIFIED in a rendered frame with the hex values read back from the ANSI; `tab.*`, `link`, `fg.muted/faint` use the same props, derived):

| Token(s) | Ink usage |
|---|---|
| `bg.base` | root `<Box backgroundColor={T['bg.base']}>`; add `borderBackgroundColor={T['bg.base']}` to every bordered Box |
| `statusbar.bg/fg` | header/footer band `<Box backgroundColor={T['statusbar.bg']}>` + `<Text color={T['statusbar.fg']}>` |
| `border.default` / `border.focus` | `borderColor={focused ? T['border.focus'] : T['border.default']}` |
| `fg.title` | `<Text bold color={T['fg.title']}>` for pane titles (put the title in a `<Box paddingX={1}>` inside the border: Ink has no border-title slot; `ink-titled-box` adds one) |
| `selection.bg/fg` | row `<Box backgroundColor={T['selection.bg']}>` + `<Text color={T['selection.fg']} bold>` + cursor glyph `<Text color={T['accent.primary']} bold>❯ </Text>` |
| `fg.muted`, `fg.faint` | `<Text color={…}>`; use `dimColor` only in 16-color mode (`ansi16` = `default dim`) |
| `status.*`, `ramp.*` | `<Text color={…}>` glyph + word (never color alone) |
| `keyhint.key/desc` | `<Text bold color={T['keyhint.key']}>q</Text><Text color={T['keyhint.desc']}> quit</Text>` |
| `tab.active.*` | active tab `<Text backgroundColor={T['tab.active.bg']} color={T['tab.active.fg']} bold> 1 Services </Text>`; inactive `color={T['tab.inactive.fg']}` |
| `link` | `<Text color={T['link']} underline>` (+ `ink-link` for OSC 8) |

**@inkjs/ui theming** is per-component style functions, not tokens (`Theme = {components: Record<Name, {styles?: Record<part, (props) => BoxProps|TextProps>, config?}>}`, INKUI:source/theme.tsx). Defaults use ANSI names (focus blue, selected green, progress magenta); override them with tokens. `extendTheme` is a deepmerge that **replaces functions** (VERIFIED: overriding `Alert.styles.container` dropped `flexGrow/gap/paddingX`), so spread the default output when changing one prop. VERIFIED, type-checks under `strict`:

```ts
// ui-theme.ts (hand-written extension of the exporter's `theme`)
import {defaultTheme, extendTheme} from '@inkjs/ui';
import {theme as T} from './theme.js';

type Variant = 'info' | 'success' | 'error' | 'warning';
const variantColor: Record<Variant, string> =
	{info: T['status.info'], success: T['status.success'], error: T['status.error'], warning: T['status.warning']};
const base = defaultTheme.components as Record<string, any>;
const over = (c: string, part: string, patch: (p: any) => object) => {
	const orig = base[c].styles[part];   // default style fn: keep its layout props, patch only colors
	return (p: any) => ({...orig(p), ...patch(p)});
};
const choice = {   // Select and MultiSelect share part names
	focusIndicator: () => ({color: T['accent.primary']}),
	selectedIndicator: () => ({color: T['status.success']}),
	label: ({isFocused, isSelected}: {isFocused: boolean; isSelected: boolean}) =>
		({color: isFocused ? T['accent.primary'] : isSelected ? T['status.success'] : T['fg.default']}),
};
export const uiTheme = extendTheme(defaultTheme, {components: {
	Spinner: {styles: {frame: () => ({color: T['accent.primary']}), label: () => ({color: T['fg.muted']})}},
	ProgressBar: {styles: {completed: () => ({color: T['accent.primary']}), remaining: () => ({color: T['fg.faint']})}},
	Select: {styles: choice}, MultiSelect: {styles: choice},
	Badge: {styles: {label: () => ({color: T['fg.on-accent']})}},   // fill = <Badge color={…}>
	StatusMessage: {styles: {icon: ({variant}: {variant: Variant}) => ({color: variantColor[variant]})}},
	Alert: {styles: {
		container: over('Alert', 'container', ({variant}) => ({borderColor: variantColor[variant as Variant]})),
		icon: ({variant}: {variant: Variant}) => ({color: variantColor[variant]}),
	}},
	ConfirmInput: {styles: {input: ({isFocused}: {isFocused: boolean}) => ({color: isFocused ? T['fg.default'] : T['fg.faint']})}},
	UnorderedList: {styles: {marker: () => ({color: T['fg.faint']})}},
}});
// usage: <ThemeProvider theme={uiTheme}>…</ThemeProvider>
```
Part names per component are in `node_modules/@inkjs/ui/build/components/<name>/theme.js` (Alert: container/iconContainer/icon/content/title/message; Select: container/option/selectedIndicator/focusIndicator/label/highlightedText; ProgressBar: container/completed/remaining + config chars; Spinner: container/frame/label; Badge: container/label; StatusMessage: container/iconContainer/icon/message; lists: list/listItem/marker/content).

**Paint or not?** Painting `bg.base` makes frames match the theme exactly (used for captures). In a real app prefer the terminal's own background unless the theme is a deliberate brand choice (derived).

## 10. Color depth, NO_COLOR, wide characters, links, screens

- Depth comes from chalk 5's vendored `supports-color`: `FORCE_COLOR=0|1|2|3`, `--color`; non-TTY gives 0; then `COLORTERM=truecolor`, known `TERM`/`TERM_PROGRAM`, `-256color`. **`FORCE_COLOR` is only a minimum** (VERIFIED: `COLORTERM=truecolor FORCE_COLOR=1` still emits `38;2;…`). Deterministic recipe: `TERM=dumb FORCE_COLOR=<1|2|3>` (VERIFIED: 1 → `93m`, 2 → `38;5;214`, 3 → `38;2;255;136;0`) or `import chalk from 'chalk'; chalk.level = 2;` before rendering (works because chalk is deduped: one `chalk@5.6.2`). chalk downsamples hex with its own algorithm; for 16-color fidelity use the theme's `ansi16` values (`../color-tokens.md`) and chalk names.
- **NO_COLOR is not honored** (VERIFIED in a real pty: with `COLORTERM=truecolor`, `NO_COLOR=1` still gave `chalk.level = 3`). Add at startup, before `render()`: `if ('NO_COLOR' in process.env && !process.env.FORCE_COLOR) chalk.level = 0;`. `chalk.level = 0` also drops bold/inverse (VERIFIED: `<Text color bold>` renders plain), so selection and focus need a glyph (`❯`) and severity needs a word or glyph, not only color.
- Wide chars: `string-width`; 7.0 fixed CJK truncation. VERIFIED: `日本語 ✔` aligns in bordered boxes. Still prefer single-cell glyphs (`../visual-vocabulary.md` V1); emoji break alignment.
- Hyperlinks: no core prop; OSC 8 passes through `<Text>`; use `ink-link`, or `<Transform>` that does not change visible width (INK:readme#transform).
- Alt screen vs inline: see section 2; `alternateScreen` is ignored when non-interactive. Quitting leaves a clean terminal; headless CLIs never need alt screen.

## 11. Testing

`ink-testing-library` 4.0.0: `render(tree)` → `{lastFrame(), frames, stdin.write(s), stdout, stderr, rerender(tree), unmount(), cleanup()}` (ITL:source/index.ts). Fake stdout has **fixed `columns = 100`**, no `rows`; Ink runs with `debug: true` (every update is a full frame), `exitOnCtrlC: false`, `patchConsole: false`. Keys: `'j'`, `'\u001B[A'` up, `'\u001B[B'` down, `'\u001B[C'` right, `'\u001B[D'` left, `'\r'` return, `'\u001B'` esc, `'\t'` tab; **await a tick after each write**. Frames contain ANSI only if chalk level > 0 (run with `TERM=dumb FORCE_COLOR=1`, or assert plain text). VERIFIED with the node:test runner (`npx tsx --test app.test.tsx`):

```tsx
import React from 'react'; import {test} from 'node:test'; import assert from 'node:assert/strict';
import {render} from 'ink-testing-library'; import {App} from './app.js';
const tick = () => new Promise(r => setTimeout(r, 20));
test('moves cursor with j and ↓', async () => {
	const {lastFrame, stdin, unmount} = render(<App />);
	assert.match(lastFrame()!, /❯ Build/);
	stdin.write('j'); await tick(); assert.match(lastFrame()!, /❯ Test/);
	stdin.write('\u001B[B'); await tick(); assert.match(lastFrame()!, /❯ Deploy/);
	unmount();
});
```
**Golden frames at a chosen width** use `renderToString` (not the library): VERIFIED invariant test (every line <= cols, row count = rows) at 80x24 and 120x30:
```tsx
import {renderToString} from 'ink'; import stringWidth from 'string-width'; import stripAnsi from 'strip-ansi';
const lines = stripAnsi(renderToString(<Screen cols={80} rows={24} />, {columns: 80})).split('\n');
assert.equal(lines.length, 24); for (const l of lines) assert.ok(stringWidth(l) <= 80);
```
Plan: golden frame per state (healthy/failing/empty) at 120 and 80 columns + pure-helper unit tests + interaction tests + the width assertion. Ink's own suite uses `node:test` (HEAD, 2026-10-01); concurrent mode may need `act()`.

## 12. One static frame at a forced size, as ANSI (what the proto-starters use)

**Option 1 — `renderToString(tree, {columns})`** (`build/render-to-string.js`; sync, no stdout/stdin). VERIFIED (`TERM=dumb FORCE_COLOR=3 COLS=60 ROWS=12 npx tsx frame.tsx > frame.ans`):

```tsx
import React from 'react';
import {renderToString, Box, Text, Spacer} from 'ink';
const COLS = Number(process.env.COLS ?? 60), ROWS = Number(process.env.ROWS ?? 12);
const App = ({cols, rows}: {cols: number; rows: number}) => (
	<Box flexDirection="column" width={cols} height={rows}>
		<Box borderStyle="round" borderColor="cyan" paddingX={1}>
			<Text bold color="cyan">Demo</Text><Spacer /><Text dimColor>{cols}x{rows}</Text>
		</Box>
		<Box flexGrow={1} gap={1}>
			<Box borderStyle="single" width="30%" flexDirection="column"><Text inverse>› item one</Text><Text>  item two</Text></Box>
			<Box borderStyle="single" flexGrow={1}><Text color="#ff8800">detail 日本語 ✔</Text></Box>
		</Box>
		<Text backgroundColor="blue" color="white"> q quit  ↑↓ move </Text>
	</Box>
);
process.stdout.write(renderToString(<App cols={COLS} rows={ROWS} />, {columns: COLS}) + '\n');
```
Caveats (all VERIFIED unless noted):
1. `columns` defaults to 80 and sets the root width; **there is no `rows` option**: give the root `<Box height={ROWS}>` explicitly, or `height="100%"`/`flexGrow` children collapse.
2. **`useWindowSize()` does not see `columns`**: it reads `process.stdout` (piped = 80x24). Pass cols/rows as props.
3. `useInput`/`useFocus`/`useApp` are no-ops. `useEffect` state updates are not in the output, `useLayoutEffect` updates are. `<Static>` output is prepended. Drive state through props.
4. Color depth is the chalk level (section 10): always set `TERM=dumb FORCE_COLOR=n` (or `chalk.level`); otherwise piped output has no color.
5. Output is exactly `rows` lines of `cols` cells (checked for a 60x16 frame).
6. A root `backgroundColor` does **not** paint border cells; add `borderBackgroundColor` per bordered Box (section 13, item 4) or the border cells show the terminal's background.

**Option 2 — `render()` with a fake stdout that has `columns` and `rows`**: use when the app relies on `useWindowSize`, effects or hooks. VERIFIED (`TERM=dumb FORCE_COLOR=3 npx tsx snap.tsx 120 30 > frame.ans`):
```tsx
import {EventEmitter} from 'node:events'; import {PassThrough} from 'node:stream';
import React from 'react'; import {render} from 'ink'; import {App} from './app.js';
const [cols = 80, rows = 24] = process.argv.slice(2).map(Number);
class FakeStdout extends EventEmitter {
	columns = cols; rows = rows; isTTY = false;     // non-interactive: no cursor/erase codes
	frames: string[] = [];
	write = (s: string) => { this.frames.push(s); return true; };
}
const stdout = new FakeStdout();
// REQUIRED if the app calls useInput, else Ink renders "Raw mode is not supported on the current process.stdin"
const stdin = Object.assign(new PassThrough(), {isTTY: true, setRawMode() {}, ref() {}, unref() {}});
const app = render(<App />, {stdout: stdout as any, stdin: stdin as any, debug: true, exitOnCtrlC: false, patchConsole: false});
await app.waitUntilRenderFlush();
const frame = stdout.frames.at(-1) ?? '';   // capture BEFORE unmount: the last write at unmount is just "\n"
app.unmount();
process.stdout.write(frame + '\n');
```
To reach another state: `stdin.write('j')`, wait a tick, then read `frames.at(-1)`. The frame height is the app's own (use `useWindowSize()` rows in the root `Box height`).

**Option 3 — ink-testing-library `lastFrame()`**: width fixed at 100 columns; fine for tests, wrong for prototypes at a chosen size.

## 13. Pitfalls and anti-patterns (symptom → cause → fix)

| # | Symptom | Cause | Fix |
|---|---|---|---|
| 1 | Throws `Text string "…" must be rendered inside <Text>`; or `<Box>` inside `<Text>` throws | Ink text nodes need `<Text>`; `<Text>` accepts only strings/`<Text>` (VERIFIED) | Wrap strings; invert nesting; @inkjs/ui list items need `<Text>` children |
| 2 | Flicker, scrollback wiped on every update | Frame taller than `stdout.rows` → full clear incl. `ESC[3J` (issues #935, #990) | Live region < `rows`; history into `<Static>`; clamp height with `useWindowSize` |
| 3 | Columns drift, rows merge or duplicate, emoji shift everything after them | One hand-padded `<Text>` per row; `padEnd`/`.length` count UTF-16 units; over-width line wraps in the terminal and the erase/repaint count drifts | One `<Box width flexShrink={0}>` + `<Text wrap="truncate">` per cell; single-width glyphs; assert every line <= cols |
| 4 | Panel border cells show the terminal's own background although the root has `backgroundColor` | `Box backgroundColor` fills the content area, not the border cells | Add `borderBackgroundColor={T['bg.base']}` to each bordered Box (VERIFIED on a 60x16 frame: 168 of 960 cells unpainted before, 0 after) |
| 5 | Fixed-width columns get squeezed | `flexShrink` defaults to 1 | `flexShrink={0}` on fixed cells; `flexGrow={1}` on the flex cell |
| 6 | Pressing a key triggers several handlers | Every `useInput` receives every key | `{isActive}` per hook; modal branch first ("steal input") |
| 7 | Backspace deletes forward / does nothing | Ink 7 sets `key.backspace`, not `key.delete` (release v7.0.0) | Check `key.backspace`; version-specific key tests |
| 8 | Code from the readme fails (`contentOffsetY` undefined) | Master readme documents unreleased features | Check `node_modules/ink/build/*.d.ts`; pin versions |
| 9 | Piped/CI run prints only one frame | non-interactive mode writes the final frame at unmount (INK:readme#interactive) | `interactive: true` / `CI=false` for live output; accept it for captures |
| 10 | Colors differ between laptop, CI and snapshots | chalk level depends on env; `FORCE_COLOR` is only a minimum (VERIFIED) | `TERM=dumb FORCE_COLOR=n` or `chalk.level` |
| 11 | `NO_COLOR=1` has no effect | chalk 5 ignores it (VERIFIED) | `chalk.level = 0` when `NO_COLOR` set; keep glyph cues (section 10) |
| 12 | `measureElement` returns zeros | Layout not computed during render | Call in `useEffect`/`useLayoutEffect` or use `useBoxMetrics` |
| 13 | `useWindowSize()` says 80x24 in a frame script | It reads `process.stdout`, not `renderToString`'s `columns` (VERIFIED) | Props for size; or Option 2 with a fake stdout |
| 14 | Custom @inkjs/ui theme loses layout props | `extendTheme` (deepmerge) replaces functions (VERIFIED) | Spread default style output, see `over()` in section 9 |
| 15 | Mutating an earlier `<Static>` item does nothing | Write-once items | Use live state for anything that changes; `Static` is wrong for newest-first/re-sorted feeds |
| 16 | `Raw mode is not supported` frame in a script | `useInput` with a non-TTY stdin (VERIFIED) | Fake TTY stdin (section 12) |
| 17 | Scaffolded app is Ink 4 / React 18 | create-ink-app template is stale | Bump to `ink@^7`, `react@^19.2`, Node 22 |
| 18 | Time-dependent goldens flake | `Date.now()` in render | Inject `now` |
| 19 | Ghost lines after narrowing the terminal | resize reflow | Re-render on `useWindowSize`; keep lines <= columns |

## 14. Showcase apps and official examples worth reading

Apps (`INK:readme#whos-using-ink`): **Claude Code**, Gemini CLI, GitHub Copilot CLI (agent chat + streaming), Cloudflare Wrangler, Shopify CLI, Prisma, Gatsby, argonaut (Argo CD).

Official examples (`INK:examples/`, `npm run example examples/<name>`):

| Example | Pattern |
|---|---|
| `jest` + `static` | `<Static>` for finished items above a live summary |
| `chat` | input line + growing message list (agent pattern) |
| `select-input` | hand-rolled list with `useInput` + `useIsScreenReaderEnabled` |
| `table` | table composed from fixed-width Boxes |
| `alternate-screen` | full-screen app: `alternateScreen`, `useWindowSize`, reducer loop |
| `use-focus`, `use-focus-with-id` | Tab cycling; `focus(id)` jump |
| `borders`, `box-backgrounds`, `border-backgrounds` | every border style; fill and inheritance |
| `incremental-rendering`, `render-throttle` | performance knobs |
| `router` | multi-screen with React Router `MemoryRouter` |
| `suspend-terminal`, `cursor-ime`, `aria` | editor hand-off, IME cursor, screen-reader roles |
| `scroll` | `contentOffsetY` (needs unreleased master) |
