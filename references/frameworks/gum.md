# gum (Charm, shell-script UI components) — getting-started and design reference

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [1. When gum is right, when it is wrong, versions, install](#1-when-gum-is-right-when-it-is-wrong-versions-install) · L23–37 — pinning versions and installing.
- [2. Mental model](#2-mental-model) · L39–45 — first contact: how the framework thinks.
- [3. Minimal app](#3-minimal-app-verified-ran-in-tmux-keys-driven-exit-codes-asserted) · L47–64 — a verified minimal app to copy.
- [4. Project layout (derived)](#4-project-layout-derived) · L66–75 — file layout of a real app.
- [5. Layout system (there is none: compose blocks of text)](#5-layout-system-there-is-none-compose-blocks-of-text) · L77–89 — composing blocks of text side by side or stacked.
- [6. Components: command catalog](#6-components-command-catalog-gum-201---help-every-interactive-command-also-has---timeout0s---no-show-help---padding0-0) · L91–114 — which gum command to use, with its flags.
- [7. Focus, keys, mouse](#7-focus-keys-mouse) · L116–118 — key bindings, focus order, mouse.
- [8. Async, timers, performance](#8-async-timers-performance) · L120–133 — background work, streaming, frame rate, flicker.
- [9. Applying our theme tokens](#9-applying-our-theme-tokens) · L135–168 — wiring `export_theme.py` output into styles.
- [10. Color profile, NO_COLOR, wide characters, alt screen](#10-color-profile-no_color-wide-characters-alt-screen) · L170–176 — colour depth, NO_COLOR, wide characters, alt screen vs inline.
- [11. Testing](#11-testing) · L178–188 — unit, snapshot and PTY tests.
- [12. One static frame at a forced size, as ANSI](#12-one-static-frame-at-a-forced-size-as-ansi-what-the-proto-starters-use) · L190–219 — frame mode: one ANSI frame at a forced size (for `compare.py`).
- [13. Pitfalls and anti-patterns](#13-pitfalls-and-anti-patterns-symptom--cause--fix--source) · L221–237 — something renders or behaves wrong (symptom → fix).
- [14. Showcase scripts and official examples worth reading](#14-showcase-scripts-and-official-examples-worth-reading) · L239–241 — real code worth reading.

Read this when a task is **a script that needs a prompt, a picker, a confirmation, a spinner or a styled summary** (deploy scripts, git helpers, installers, dotfile aliases), or when you must style/capture gum output. If the task is a persistent multi-pane or live-updating UI, gum is the wrong tool: use `bubbletea.md`, `ratatui.md`, `textual.md` or `ink.md` (decision table in §1).

Source keys: `GUM:` https://github.com/charmbracelet/gum/blob/main/ · `CP:` https://github.com/charmbracelet/colorprofile/blob/main/. **VERIFIED** = run on 2026-10-01 with **gum 2.0.1** (installed locally; latest release is 2.0.2) on macOS in tmux 3.7c and plain pipes; flags/env vars were extracted from `gum <cmd> --help`. `UNVERIFIED` = not confirmed; `derived:` = inference.

## 1. When gum is right, when it is wrong, versions, install

| Situation | gum? | Why / alternative |
|---|---|---|
| Wizard in a shell script (choose, input, confirm, then act) | **yes** | one `gum <cmd>` per step; result on stdout, UI on stderr |
| "Pick one / pick many, then pipe it" (`$EDITOR $(gum filter)`) | **yes** | `gum filter`, `gum choose --no-limit` |
| Confirm a destructive step, show progress of one command | **yes** | `gum confirm`, `gum spin` |
| Styled one-shot output (summary card, banner, table, log lines) | **yes** | `gum style`, `join`, `format`, `table --print`, `log` |
| Calling from Python/JS/Ruby via subprocess | yes | `GUM:examples/gum.py`, `gum.js`, `gum.rb` |
| Persistent multi-pane app, live dashboard, shared state between steps, custom keys, mouse | **no** | each call is a fresh tiny Bubble Tea program: `bubbletea.md` / `ratatui.md` |
| Form with validation, groups, dynamic fields in Go | no | use Huh (`bubbletea.md` §6) |
| Must run unattended / in CI | only behind a TTY check | without a TTY gum fails (§11) |

- **gum 2.0.2** (2026-09-24); 2.0.0 (2026-08-20) was the Bubble Tea/Lip Gloss v2 port with no UX changes. Module `charm.land/gum/v2`, MIT, 24k stars (https://github.com/charmbracelet/gum/releases).
- Install: `brew install gum` · `dnf install gum` · `nix-env -iA nixpkgs.gum` · `flox install gum` · `winget install charmbracelet.gum` · `scoop install charm-gum` · Charm apt repo · `go install charm.land/gum/v2@latest` (`GUM:README.md`).

## 2. Mental model

- **One command = one mini app.** It starts a Bubble Tea program, renders on **stderr** (every interactive command uses `tea.WithOutput(os.Stderr)`), prints the **result to stdout**, exits. So `x=$(gum choose …)` captures only the answer while the UI stays visible (`GUM:choose/command.go`).
- **Exit codes** (`GUM:internal/exit/exit.go`): `0` ok (confirm: yes) · `1` no/error (confirm: no) · `130` aborted with ctrl+c · `124` timeout. VERIFIED: ctrl+c in `choose` → 130; `Esc` on `confirm` → 1. Always branch on the code: `x=$(gum choose …) || exit 130`.
- **Static vs interactive:** `style`, `join`, `format`, `log`, `table --print` print text and need no TTY; `choose confirm file filter input pager spin table write` need a real TTY.
- **State lives in the shell** (variables, files, exit codes). There is no focus model, no layout engine, no event loop you can touch.
- **Styling is flags or env vars**, mapped to Lip Gloss styles: `--<part>.foreground/.background` ↔ `GUM_<CMD>_<PART>_FOREGROUND/BACKGROUND`; flags override env (`GUM:README.md` "Customization").

## 3. Minimal app (VERIFIED: ran in tmux; keys driven; exit codes asserted)

```sh
#!/bin/sh
svc=$(gum choose --header "Restart which service?" --height 8 api-gateway auth billing search worker cron) || exit 130
gum confirm "Restart $svc in prod-eu?" --affirmative "Restart" --negative "Cancel" --default=false || { echo "cancelled"; exit 1; }
gum spin --spinner dot --title "Restarting $svc..." --show-error -- sleep 2      # any external command
gum style --foreground 2 --bold "✓ $svc restarted"                              # (use theme hex, §9)
```
Observed: `--default=false` + Enter → "No" focused, exit 1 (safe default for destructive actions); the confirm help line shows `←→ toggle • enter submit • y Restart • n Cancel` (the shortcut keys are the first letters of your labels); `gum spin` swallows the command's stdout unless `--show-output` (or `--show-stdout/--show-stderr/--show-error`).

### Lifecycle, signals and exit status

Each command is a Bubble Tea v2 program (gum 2.0.1 pins `charm.land/bubbletea/v2 v2.0.9`, `GUM:go.mod`) and inherits its signal handling (`bubbletea.md` §3). **VERIFIED** = run 2026-10-02 with gum 2.0.1 in an isolated `tmux -L`. The rules behind it: `../lifecycle.md` LC1, LC9-LC11.

- **SIGTERM restores the terminal but is not reported as 143**: Bubble Tea turns it into a normal quit. `gum choose` and `gum input` → 1; **`gum confirm` → the focused button's answer: 0 (yes) with the default focus**, 1 with `--default=false` (`GUM:confirm/command.go` returns the model's `confirmation` after any `Run()`). Make a terminated script stop by itself: `trap 'exit 143' TERM` at the top, and `--default=false` on destructive confirms (§13 #9, #13).
- **Ctrl+Z does nothing** inside `gum choose` (raw mode; the command does not implement suspend). The script between commands is plain shell: job control works there as usual.
- **Exit status reaches the process already** (0 / 1 / 130 / 124, §2): branch on it, `x=$(gum choose …) || exit $?`.

## 4. Project layout (derived)

```
tools/deploy/
├── deploy.sh             # the wizard; #!/usr/bin/env bash; set -eu
├── lib/gum-theme.sh      # GENERATED: python3 SKILL_DIR/scripts/export_theme.py ID --target gum > lib/gum-theme.sh   (export GUM_* env)
├── lib/ui.sh             # tok(), c(), hint(), die() helpers (below); sourced by deploy.sh
└── theme.json            # GENERATED: python3 SKILL_DIR/scripts/export_theme.py ID --target json  (flat resolved tokens, for `gum style` flags)
```
One script, `source lib/gum-theme.sh` at the top, helpers in `lib/ui.sh`. No build step. (`--target json` emits the flat resolved theme; without the script, read `references/themes/<id>.json` with jq: `.tokens[$t]` is a palette name or `#hex`; tier-2 tokens that are unmapped need the fallback from `_tokens.json`.)

## 5. Layout system (there is none: compose blocks of text)

Only two tools: `gum style` (box model for one block) and `gum join` (blocks side by side or stacked). Both are Lip Gloss: v2 `--width`/`--height` include border and padding (VERIFIED: `--width 32` with a rounded border and `--padding '0 1'` printed 32 columns).

| Need | Command | Notes |
|---|---|---|
| bordered card | `gum style --border rounded --border-foreground "$FOCUS" --padding '0 1' --width 32 --height 8 "line 1" "line 2"` | borders `none hidden normal rounded thick double`; each positional arg is one line; `--margin "v h"`, `--padding "v h"`, `--align left\|center\|right`, `--trim` |
| side by side | `gum join --horizontal --align top "$left" "$right"` | blocks padded to the tallest; `--align top\|middle\|bottom`; `--vertical --align left\|center\|right` for stacking |
| full-width band | `gum style --background "$BAR_BG" --foreground "$BAR_FG" --width "$(tput cols)" --bold " Fleet · prod-eu"` | `tput cols` = 80 when there is no TTY |
| inline colored span | `c() { gum style --foreground "$1" -- "$2"; }` then `"$(c "$OK" ●) api-gateway"` | spans inside blocks: ANSI-aware width |
| centered modal-like prompt | none: `gum confirm` / `gum input` draw inline at the cursor | gum never takes over the screen (no alt screen) |

Archetype fit: **wizard / prompt flow** (native), **summary card + side-by-side cards** (static `join`), **table picker** (`gum table`), **header band + status line** (static `style`). **list + detail, dashboard, persistent header/footer, live modal** are not achievable as interactive UI: print a static `join` snapshot, or switch framework.

## 6. Components: command catalog (gum 2.0.1 `--help`; every interactive command also has `--timeout=0s`, `--[no-]show-help`, `--padding="0 0"`)

Style prefixes: `--<prefix>.foreground` / `.background` ↔ env `GUM_<CMD>_<PREFIX>_FOREGROUND|BACKGROUND` (defaults shown are ANSI-256 numbers unless `#hex`). Command names: `GUM_CHOOSE_…`, etc.

| Command | Purpose | Key flags | Style prefixes (default fg) |
|---|---|---|---|
| `choose [opts…]` | pick from args or stdin lines | `--limit=1`, `--no-limit`, `--ordered`, `--height=10`, `--cursor="> "`, `--header="Choose:"`, `--cursor-prefix="• "`, `--selected-prefix="✓ "`, `--unselected-prefix="• "`, `--selected=a,b` (`*` = all), `--select-if-one`, `--input-delimiter`, `--output-delimiter`, `--label-delimiter` (label:value), `--[no-]strip-ansi` | `cursor`(212) `header`(99) `item`(none) `selected`(212) |
| `confirm [prompt]` | yes/no; exit 0/1 | `--default` (`--default=false`), `--affirmative="Yes"`, `--negative="No"`, `--show-output` | `prompt`(#7571F9) `selected`(230 on 212) `unselected`(254 on 235) |
| `file [path]` | file picker | `-c/--cursor=">"`, `-a/--all`, `--[no-]permissions`, `--[no-]size`, `--file`, `--directory`, `--height=10`, `--header` | `cursor`(212) `symlink`(36) `directory`(99) `file` `permissions`(244) `selected`(212) `file-size`(240) `header`(99) |
| `filter [opts…]` | fuzzy filter (stdin or args) | `--limit`, `--no-limit`, `--placeholder="Filter..."`, `--prompt="> "`, `--header`, `--value`, `--reverse`, `--[no-]fuzzy`, `--[no-]fuzzy-sort`, `--[no-]strict`, `--width`, `--height`, `--indicator="•"`, `--selected-prefix="◉ "`, `--unselected-prefix="○ "`, `--select-if-one` | `indicator`(212) `selected-indicator`(212)† `unselected-prefix`(240) `header`(99) `text` `cursor-text` `match`(212) `prompt`(240) `placeholder`(240) |
| `input` | single-line prompt | `--placeholder`, `--prompt="> "`, `--value`, `--char-limit=400`, `--width`, `--password`, `--header`, `--cursor.mode=blink` | `prompt` `placeholder`(240) `cursor`(212) `header`(240) |
| `write` | multi-line prompt (enter submits, ctrl+j newline, ctrl+e `$EDITOR`) | `--width`, `--height=5`, `--header`, `--placeholder`, `--prompt="┃ "`, `--show-cursor-line`, `--show-line-numbers`, `--value`, `--char-limit`, `--max-lines` | `base` `cursor-line-number`(7) `cursor-line` `cursor`(212) `end-of-buffer`(0) `line-number`(7) `header`(240) `placeholder`(240) `prompt`(7) |
| `spin <cmd…>` | spinner while an external command runs | `-s/--spinner=dot` (`line dot minidot jump pulse points globe moon monkey meter hamburger`), `--title="Loading..."`, `-a/--align`, `--show-output`, `--show-error`, `--show-stdout`, `--show-stderr` | `spinner`(212) `title` |
| `table` | select a row of CSV (stdin or `-f`) | `-s/--separator=","`, `-c/--columns`, `-w/--widths`, `--height`, `-p/--print` (static, no selection), `-b/--border=rounded`, `-r/--return-column`, `--lazy-quotes`, `--fields-per-record`, `--[no-]hide-count` | `border` `cell` `header` `selected`(212) |
| `pager [content]` | scroll text | `--show-line-numbers`, `--[no-]soft-wrap`; root `--foreground/--background` | `line-number`(237) `match`(212) `match-highlight`(235 on 225)‡ `help`(241) |
| `style [text…]` | style a block (Lip Gloss) | `--foreground`, `--background`, `--border`, `--border-foreground`, `--border-background`, `--align`, `--width`, `--height`, `--margin "v h"`, `--padding "v h"`, `--bold`, `--faint`, `--italic`, `--strikethrough`, `--underline`, `--trim` | env vars are **un-prefixed**: `$FOREGROUND $BACKGROUND $BORDER $BORDER_FOREGROUND $ALIGN $WIDTH $HEIGHT $MARGIN $PADDING $BOLD …` |
| `join <text…>` | join blocks | `--horizontal`, `--vertical`, `--align` | none |
| `format [tmpl…]` | markdown / template / code / emoji | `-t/--type=markdown\|template\|code\|emoji`, `--theme="pink"` (Glamour theme), `-l/--language` | none; template funcs e.g. `{{ Bold "x" }}`, `{{ Color "99" "0" " tag " }}` |
| `log <text…>` | leveled, structured log line (**stderr**, VERIFIED; renders `INFO deployed service=api`) | `-l/--level=none\|debug\|info\|warn\|error\|fatal`, `-s/--structured` (key value pairs), `-t/--time=kitchen\|rfc822…`, `--prefix`, `-f/--format` (printf), `--formatter=text\|json\|logfmt`, `-o/--file`, `--min-level` (`$GUM_LOG_LEVEL`) | `level` `time` `prefix` `message` `key` `value` `separator` |
| `version-check` | semver check of gum itself | | |

† env var for `--selected-indicator.*` is `GUM_FILTER_SELECTED_PREFIX_*`. ‡ env var for `--match-highlight.*` is `GUM_PAGER_MATCH_HIGH_*`. (Both read from `--help`; naming quirks, not typos.)

Not in gum: tabs, tree, progress bar (only a spinner; draw bars with `style`), toasts, modals, multi-pane layout.

## 7. Focus, keys, mouse

No focus model: each command owns the keyboard until it returns. Keys come from the on-screen help line (VERIFIED strings): `choose` `←↓↑→ navigate • enter submit` (multi: `x toggle • … • ctrl+a select all`; `j`/`k` also move, VERIFIED); `confirm` `←→ toggle • enter submit • y <Yes-label first letter> • n …`; `input` `enter submit`; `write` `ctrl+j insert newline • ctrl+e open editor • enter submit`; `filter` `↓↑ navigate • esc blur search • enter submit`. Abort = ctrl+c (130). Keys cannot be rebound; mouse support is UNVERIFIED (none seen in the flags). Hide the help line with `--show-help=false` (env `GUM_<CMD>_SHOW_HELP=false`); see §9 for why you may want to.

## 8. Async, timers, performance

- `gum spin` is the only async primitive: it runs **one external command** (`gum spin --title "…" -- cmd args`). VERIFIED: a shell **function** fails (`exec: "f": executable file not found in $PATH`, exit 1); wrap it: `gum spin -- bash -c '…'` (functions must be exported with `export -f` under bash, or put the logic in a script). Exit status of the command is returned.
- Timeouts: `--timeout=5s` on every interactive command (exit 124); `confirm --timeout` returns the selected value, or the `--default` if one was given (`--help`).
- Nothing runs in the background and nothing refreshes; for live output run the command yourself and print lines (`gum log`). Each invocation costs one process start (milliseconds): fine for wizards, wrong inside tight loops.

### Debugging and profiling

gum has no debug flag and no profiler worth using (one process per call). The part that applies: gum draws on **stderr**, so shell tracing and `2>` redirects collide with the UI. Checked 2026-10-02 with bash 5 and gum installed locally.

| Need | Tool | Command / setting | Notes and gotchas | Source |
|---|---|---|---|---|
| Trace the script without breaking the UI | bash `BASH_XTRACEFD` | `exec 3>trace.log; BASH_XTRACEFD=3; set -x`, then `tail -f trace.log` in a second pane | **VERIFIED:** the trace lands in the file, stderr stays empty (bash 4.1+; macOS `/bin/bash` 3.2 lacks it, use Homebrew bash). Plain `set -x` writes to stderr, the same stream as the UI | https://www.gnu.org/software/bash/manual/bash.html#index-BASH_005fXTRACEFD |
| Leveled log lines from the script | `gum log` | `gum log -o debug.log -l debug -s "msg" key value` (`-o/--file` logs to a file; `--min-level` / `$GUM_LOG_LEVEL` filters) | **VERIFIED:** `DEBUG msg key=value` lands in the file, nothing on stderr. Without `-o` it prints on stderr (§6), the stream the UI uses | `gum log --help` |

## 9. Applying our theme tokens

`python3 SKILL_DIR/scripts/export_theme.py ID --target gum > lib/gum-theme.sh` writes `export GUM_<CMD>_<PART>_<ATTR>="#rrggbb"` lines (VERIFIED: all 33 variables exist in gum 2.0.1's `--help`; sample for catppuccin-mocha):

```sh
export GUM_CHOOSE_CURSOR_FOREGROUND="#89b4fa"     # accent.primary
export GUM_CHOOSE_SELECTED_FOREGROUND="#a6e3a1"   # status.success
export GUM_CHOOSE_ITEM_FOREGROUND="#cdd6f4"       # fg.default
export GUM_CHOOSE_HEADER_FOREGROUND="#cdd6f4"
export GUM_FILTER_INDICATOR_FOREGROUND="#89b4fa"  ; export GUM_FILTER_MATCH_FOREGROUND="#f9e2af"   # search.match
export GUM_FILTER_PROMPT_FOREGROUND="#89b4fa"     ; export GUM_FILTER_PLACEHOLDER_FOREGROUND="#7f849c"   # fg.faint
export GUM_INPUT_PROMPT_FOREGROUND="#89b4fa"      ; export GUM_INPUT_CURSOR_FOREGROUND="#f5e0dc"         # cursor.bg
export GUM_CONFIRM_PROMPT_FOREGROUND="#cdd6f4"
export GUM_CONFIRM_SELECTED_FOREGROUND="#1e1e2e"  ; export GUM_CONFIRM_SELECTED_BACKGROUND="#89b4fa"    # fg.on-accent on accent.primary
export GUM_CONFIRM_UNSELECTED_FOREGROUND="#cdd6f4"; export GUM_CONFIRM_UNSELECTED_BACKGROUND="#45475a"  # on bg.raised
export GUM_SPIN_SPINNER_FOREGROUND="#89b4fa"      ; export GUM_TABLE_BORDER_FOREGROUND="#6c7086"
export GUM_TABLE_SELECTED_FOREGROUND="#cdd6f4"    ; export GUM_TABLE_SELECTED_BACKGROUND="#3b3d4f"   # selection.fg on selection.bg
# … FILE_*, WRITE_*, TABLE_HEADER, CHOOSE/INPUT/FILTER headers: same pattern
```
Besides `--target gum`, `--target json` writes the **flat resolved theme** used for `gum style` flags and by every proto-starter: `id`, `name`, `appearance`, `terminal` (`background`, `foreground`, `cursor`, `selection_background`, `ansi` ×16), `tokens` (all 43, hex, fallbacks resolved) and `ansi16` (a spec per token, e.g. `"fg.on-accent": "bg"`; grammar in [formats.md](../formats.md#theme-json)). Re-checked 2026-10-01 for `catppuccin-mocha`: 33 `export` lines, all in the sample above.

VERIFIED effect (tmux, truecolor): `confirm` with `--default=false` shows the focused **Cancel** as `38;2;30;30;46` on `48;2;137;180;250` and the unfocused **Restart** on `48;2;69;71;90`; the choose cursor is `38;2;137;180;250`.

Token → gum part mapping for parts the exporter does not cover (set them yourself):

| Part | Token | Notes |
|---|---|---|
| `GUM_CONFIRM_PROMPT_FOREGROUND` for a destructive prompt | `status.warning` | pair with `--default=false`; `selected` styles whichever button has focus, so a red selected background would also paint **Cancel**: keep `accent.primary` |
| `GUM_CHOOSE_SELECTED_FOREGROUND` | `mark` (multi-select check) or `status.success` | `selected` styles the ✓-marked items |
| `GUM_FILE_DIRECTORY_FOREGROUND` / `SYMLINK` | `accent.secondary` / `status.info` | |
| `GUM_LOG_LEVEL_FOREGROUND` etc. | `status.*` | use `--level.foreground` per call: one var cannot differ per level |
| `gum style` flags | tokens from `theme.json`: `tok() { jq -r --arg t "$1" '.tokens[$t]' theme.json; }` | `--border-foreground "$(tok border.focus)"`, band `--background "$(tok statusbar.bg)"` |

**Known holes (VERIFIED):** the key-hint help line of `choose/confirm/input/write/filter` has **no style flag**: bubbles' fixed greys `#626262`/`#4A4A4A`/`#3C3C3C` (SGR `38;2;60;60;60`) are drawn; on a dark `bg.base` such as `#1e1e2e` the separator is ≈1.5:1 (< the 3.0 floor for `fg.faint`, see [formats.md](../formats.md#contrast-floors)). Hide it (`--show-help=false`) and print your own hint line with `gum style --foreground "$(tok keyhint.desc)"`, or accept it. Only `pager` has `--help.foreground`. `gum` has no dark/light switch: choose the theme in the wrapper (`export_theme.py light-id`).

## 10. Color profile, NO_COLOR, wide characters, alt screen

- Profile and NO_COLOR follow `colorprofile`, exactly as in Bubble Tea (`bubbletea.md` §10): `TERM=dumb` → none unless `CLICOLOR_FORCE`; `COLORTERM` is ignored when `TERM` starts with `tmux`/`screen`; NO_COLOR applies only on a TTY (colors dropped, bold kept); piped, `CLICOLOR_FORCE=1` beats `NO_COLOR=1` (VERIFIED for gum too). Hex colors are downsampled to the profile (VERIFIED: `#ff00aa` → `38;2;255;0;170` / `38;5;199` / `91m`).
- **stdout is a pipe inside `$(...)`, so color is stripped** (VERIFIED: `a=$(gum style --foreground '#ff00aa' hi)` gives plain `hi` even with `COLORTERM=truecolor`). Fix for composed blocks (§12 recipe): `if [ -z "${NO_COLOR:-}" ] && [ -t 1 ]; then export CLICOLOR_FORCE=1 COLORTERM=truecolor; fi` at the top of the script.
- Generic env names: `gum style` reads `$WIDTH`, `$HEIGHT`, `$BORDER`, `$ALIGN`, `$MARGIN`, `$PADDING`, `$FOREGROUND`, `$BACKGROUND`, `$BOLD`… (VERIFIED: an exported `WIDTH=20` made `gum style --border rounded hi` 20 columns wide). Do not export variables with those names in scripts that call `gum style`.
- Wide chars and emoji are measured by Lip Gloss; prefer single-cell glyphs (`../visual-vocabulary.md` V1). Everything is **inline** (no alt screen); interactive widgets redraw in place and clear on exit.
- Accessibility: gum has no screen-reader mode; offer `--yes` / non-interactive paths and keep meaning in text, not color alone.

## 11. Testing

- **gum needs a TTY** (VERIFIED, no controlling terminal): `echo | gum choose a b` → `unable to pick selection: bubbletea: error opening TTY: … open /dev/tty: device not configured`, exit 1. Guard: `[ -t 0 ] && [ -t 2 ] || { echo "non-interactive: use --yes/--service NAME" >&2; exit 2; }`.
- **tmux harness** (VERIFIED; private socket, never the default server):
```sh
T=guntest$$; tmux -L $T -f /dev/null new-session -d -s c -x 80 -y 14 "env TERM=xterm-256color ./wizard.sh; echo rc=\$? > "${TMPDIR:-/tmp}/rc.$T"; sleep 5"
sleep 1; tmux -L $T send-keys -t c Down Down; tmux -L $T send-keys -t c Enter     # drive
tmux -L $T capture-pane -t c -p | grep -q 'Restart billing' || exit 1             # assert on text
tmux -L $T kill-server                                                             # only your own socket
```
Assert on `capture-pane -p` text and the exit code; use `-p -e` only when styles matter (§12). Allow ~0.3 s after each key (`gum` renders asynchronously). Static commands (`style`, `join`, `format`, `table --print`) are testable as plain pipes: compare stdout with `NO_COLOR=1`-free `CLICOLOR_FORCE=1` output stripped of SGR.

## 12. One static frame at a forced size, as ANSI (what the proto-starters use)

**Static commands** print through `colorprofile` on stdout: force color when piping. VERIFIED recipe for a composed "services" card (list + detail via `join`, tokens from `theme.json`; 9 lines × 72 columns, truecolor):

```sh
#!/bin/sh
set -eu
J=$(python3 SKILL_DIR/scripts/export_theme.py "${1:-catppuccin-mocha}" --target json); tok() { printf '%s' "$J" | jq -r --arg t "$1" '.tokens[$t]'; }
if [ -z "${NO_COLOR:-}" ] && [ -t 1 ]; then export CLICOLOR_FORCE=1 COLORTERM=truecolor; fi   # needed inside $(...)
OK=$(tok status.success) WARN=$(tok status.warning) ERR=$(tok status.error) MUTED=$(tok fg.muted) FAINT=$(tok fg.faint)
FOCUS=$(tok border.focus) BORDER=$(tok border.default) TITLE=$(tok fg.title)
c() { gum style --foreground "$1" -- "$2"; }
row() { printf '%s %-13s %s' "$(c "$1" "$2")" "$3" "$(c "$4" "$5")"; }
LIST=$(gum style --border rounded --border-foreground "$FOCUS" --padding '0 1' --width 32 --height 8 \
  "$(gum style --bold --foreground "$TITLE" 'Services (6)')" \
  "$(row "$OK" ● api-gateway "$MUTED" running)" "$(row "$WARN" ▲ billing "$WARN" degraded)" "$(row "$ERR" ✗ search "$ERR" failed)")
DETAIL=$(gum style --border rounded --border-foreground "$BORDER" --padding '0 1' --width 40 --height 8 \
  "$(gum style --bold --foreground "$TITLE" 'api-gateway')" "$(c "$MUTED" 'Version  ')v2.4.1" \
  "$(c "$MUTED" 'CPU      ')$(c "$OK" ██████)$(c "$FAINT" ░░░░░░░░░░░░░░) 31%")
gum join --horizontal --align top "$LIST" "$DETAIL"
```
Capture: `CLICOLOR_FORCE=1 COLORTERM=truecolor ./summary.sh > frame.ansi` (VERIFIED: `38;2;…` throughout, every line 72 cells). Without `CLICOLOR_FORCE` a pipe gives plain text (useful as the `.txt` for audits). Note this is a **fixed-size static card**, not the Fleet demo screen: gum cannot produce the full-screen list+detail+footer layout as interactive UI; use it for the wizard/summary prototypes and a `join` snapshot of the screen for comparison only.

**Interactive commands** (VERIFIED with `choose`, `confirm`, `spin`): run in a detached pane of a private tmux server (`tmux -L <name>`) at the target size and capture with `-p -e`; to get truecolor you must pass `TERM` and `COLORTERM` **to the command itself** because tmux sets `TERM=tmux-256color` for panes and colorprofile then ignores `COLORTERM` (without it hex colors come out as `38;5;n`):
```sh
SKILL_DIR/scripts/capture_tui.sh -s 60x10 -k Down -o out -- env TERM=xterm-256color COLORTERM=truecolor \
    gum choose --header "Pick one" Alpha Bravo Charlie      # out/60x10.{ansi,txt,meta.json}
# by hand: tmux -L cap new-session -d -s cap -x 60 -y 10 "env TERM=xterm-256color COLORTERM=truecolor gum choose …; sleep 5"; sleep 1; tmux -L cap capture-pane -t cap -p -e > frame.ansi; tmux -L cap kill-server
```
tmux re-encodes SGR (`39`/`49` instead of `0`, runs of unchanged attributes omitted) and returns exactly W×H cells with trailing blank lines. `SKILL_DIR/scripts/capture_tui.sh` appends `ESC[0m` per line, which drops the carried-over background on the first cells of each row (see `ratatui.md` §12); for style-exact work prefer the static recipe above. The same tmux technique captures any binary (Bubble Tea, Ratatui) when a real-runtime frame is needed.

## 13. Pitfalls and anti-patterns (symptom → cause → fix → source)

| # | Symptom | Cause | Fix | Source |
|---|---|---|---|---|
| 1 | Composed blocks (`$(gum style …)` inside `gum join`) are uncolored | `$()` makes stdout a pipe; colorprofile strips color (VERIFIED) | `export CLICOLOR_FORCE=1 COLORTERM=truecolor` when stdout is a TTY and `NO_COLOR` is unset | `CP:env.go`, VERIFIED |
| 2 | `x=$(gum choose …)` is empty and the script continues | user aborted (130) or no TTY (1) and the exit code was ignored | `x=$(gum choose …) \|\| exit 130`; TTY guard (§11) | `GUM:internal/exit/exit.go` |
| 3 | `gum spin -- myfunc` fails: `executable file not found in $PATH` | spin execs a program, not a shell function | `gum spin -- bash -c '…'` or a script | VERIFIED |
| 4 | Spinner shows, but the command's output vanished | `spin` discards stdout by default | `--show-output` / `--show-error` | `gum spin --help` |
| 5 | Truecolor expected, got 256-color in tmux captures | `TERM=tmux-256color` ⇒ `COLORTERM` ignored | `env TERM=xterm-256color COLORTERM=truecolor gum …` | `CP:env.go`, VERIFIED |
| 6 | `gum style` mysteriously narrow/wide or colored | generic env vars (`WIDTH`, `HEIGHT`, `BORDER`, `FOREGROUND`, …) exported by the script | rename script variables; or pass explicit flags (flags win) | `gum style --help`, VERIFIED |
| 7 | Key-hint line is nearly invisible on a dark theme | bubbles' fixed `#3C3C3C`-class greys, no style flag | `--show-help=false` + own hint line | VERIFIED, §9 |
| 8 | A theme var has no effect | wrong env name: `--selected-indicator.*` ⇒ `GUM_FILTER_SELECTED_PREFIX_*`; `--match-highlight.*` ⇒ `GUM_PAGER_MATCH_HIGH_*`; `style` vars are un-prefixed | copy names from `gum <cmd> --help` | `gum <cmd> --help` |
| 9 | Destructive confirm accepted by a stray Enter | `confirm` defaults to Yes | `--default=false`; label the buttons with the verb (`--affirmative "Delete"`) | VERIFIED |
| 10 | `NO_COLOR` ignored in a pipeline | `CLICOLOR_FORCE` also set (it wins when piped) | set only one of them; test both | VERIFIED |
| 11 | Wizard hangs/fails in CI | no TTY | `[ -t 0 ]` guard + flags/env for non-interactive input | VERIFIED |
| 12 | Heavy use inside loops is slow/flickery | one process and one TUI start per call | gather input once, loop in the shell; use `gum log` for lines | derived |
| 13 | A `kill -TERM` during `gum confirm` lets the script go on as if the user said yes | Bubble Tea turns SIGTERM into a normal quit; `confirm` returns the focused answer (default: yes → 0) (VERIFIED) | `--default=false` on destructive confirms; `trap 'exit 143' TERM` in the script | §3 lifecycle, `GUM:confirm/command.go` |

## 14. Showcase scripts and official examples worth reading

`GUM:examples/`: `commit.sh` (Conventional Commit wizard: choose + input + write + confirm), `git-branch-manager.sh` (multi-select then act), `git-stage.sh` (stage files via choose), `diyfetch` (system-info card from `style` + `join`: the template for §12), `demo.sh`, `magic.sh`, `kaomoji.sh`, `skate.sh`, `filter-key-value.sh`, `posix.sh`, `gum.py` / `gum.js` / `gum.rb` (calling gum from other languages), and `*.tape` VHS recordings of each command. README one-liners: `$EDITOR $(gum filter)`, `git log --oneline | gum filter | cut -d' ' -f1`, `brew list | gum choose --no-limit | xargs brew uninstall`, `alias please="gum input --password | sudo -nS"`. Real-world: **Glow** and **Mods** (same Charm family, full Bubble Tea apps rather than scripts), Wishlist. For script UX, `huh` (`bubbletea.md` §6) is the Go-library equivalent with grouped forms and `WithAccessible(true)`.
