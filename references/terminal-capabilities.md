# Terminal capabilities: what to detect, what to assume, how to degrade

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [D1. Should I emit color at all?](#d1-should-i-emit-color-at-all-no_color-force_color-flags) · L20–52 — NO_COLOR, FORCE_COLOR, `--color` flags, pipes.
- [D2. Which color depth? (16 / 256 / truecolor)](#d2-which-color-depth-16--256--truecolor) · L54–92 — detecting colour depth.
- [D3. How do I downsample truecolor to 256 and 16?](#d3-how-do-i-downsample-truecolor-to-256-and-16) · L94–169 — mapping a theme to fewer colours.
- [D4. Which text attributes can I rely on? (SGR)](#d4-which-text-attributes-can-i-rely-on-sgr) · L171–202 — bold, dim, italic, underline support.
- [D5. Is the terminal dark or light?](#d5-is-the-terminal-dark-or-light) · L204–217 — dark/light detection.
- [D6-D8. Queries, escape-sequence modes, per-terminal support](#d6-d8-queries-escape-sequence-modes-per-terminal-support-moved) · L219–223 — pointer to `terminal-escapes.md`.
- [D9. What must the user configure under tmux or GNU screen?](#d9-what-must-the-user-configure-under-tmux-or-gnu-screen) · L225–243 — colours, keys or passthrough break under a multiplexer.
- [D10. How do I handle resize signals?](#d10-how-do-i-handle-resize-signals) · L245–253 — SIGWINCH and redraw on resize.
- [Source index](#source-index) · L255–261 — resolving a source key.

Raw escape sequences, query replies and the per-terminal support matrix are in [terminal-escapes.md](terminal-escapes.md).

Evidence tags: `[Sn]` = [source index](#source-index) (read 2026-10-01). `derived:` = own inference or computation (reproducible). `UNVERIFIED` = not confirmed from a primary source.

---

## D1. Should I emit color at all? (NO_COLOR, FORCE_COLOR, flags)

**Rule** (`derived:` from the conventions and library sources below). Resolve in this order, first match wins:

| # | Condition | Result |
|---|---|---|
| 1 | `--color=never\|always\|auto` flag, or user config key | obey it (no-color.org: user config and per-instance flags "should override" `NO_COLOR`) |
| 2 | `FORCE_COLOR` / `CLICOLOR_FORCE` non-empty | color on; depth from D2 (a numeric `FORCE_COLOR` is a level 0-3) |
| 3 | `NO_COLOR` non-empty (any value) | no color; **keep** bold, underline, inverse, and all glyph/word cues |
| 4 | stdout not a TTY, or `TERM=dumb`, or `TERM` unset | no color, no animation, no cursor addressing |
| 5 | else | detect depth (D2) |

**When**: every program that writes SGR. This is the single home for NO_COLOR precedence; other files link here. This order puts `FORCE_COLOR` above `NO_COLOR`, which matches force-color.org's own priority example; Charm's colorprofile does the opposite (below). Pick one, document it in `--help`.

**Example**: `NO_COLOR=1 myapp` renders the Fleet screen with `❯` marker + inverse selection row, `● running` / `✗ failed` words, no hue. Test it: `NO_COLOR=1 python3 SKILL_DIR/scripts/render_mockup.py FILE.mock --depth none`.

**Sources**: [S38] no-color.org ("when present and **not an empty string** (regardless of its value) … prevents the addition of ANSI color"; "other styling like bold, italic, and underline should remain unaffected"); force-color.org; bixense.com/clicolors; clig.dev [S37]: disable color when stdout/stderr is not a TTY, `NO_COLOR` set and non-empty, `TERM=dumb`, `--no-color`; optionally `MYAPP_NO_COLOR`.

### What the libraries actually do (source read; check before trusting a framework default)

| Library | `NO_COLOR` | `FORCE_COLOR` / `CLICOLOR_FORCE` | Notes | Source |
|---|---|---|---|---|
| **supports-color** (chalk, Ink) | **no branch at all** (grep: zero hits); flags `--no-color`, `--color=never\|16m\|256` | `FORCE_COLOR`: `true`/empty -> enable only (level detected); `false` -> 0; digits clamp 0..3. **Version split**: current main returns an *exact* level for a numeric value; chalk 5.6.2's vendored copy treats it as a *minimum* (verified: `COLORTERM=truecolor FORCE_COLOR=1` still emits `38;2;...`; `TERM=xterm FORCE_COLOR=3` still emits 16-color) | deterministic test recipe that works on both: `TERM=dumb FORCE_COLOR=n` (n=1 -> `93m`, 2 -> `38;5;214`, 3 -> `38;2;255;136;0`), or `chalk.level = n`. Honor `NO_COLOR` yourself: `chalk.level = 0` | [S18] |
| **termenv** (Go, older Charm) | `NO_COLOR != ""` -> `Ascii` profile; also `CLICOLOR=0` unless `CLICOLOR_FORCE` | `CLICOLOR_FORCE != ""` | `NO_COLOR` wins over `CLICOLOR*` | [S24] `termenv_unix.go`/`termenv.go` |
| **colorprofile** (Charm, Bubble Tea v2 / Lip Gloss v2; v0.4.3) | parsed with Go `strconv.ParseBool`: `1 t T TRUE true True` disable, **`NO_COLOR=yes` or any other string does not** (deviates from no-color.org). Applied **only when the output is a TTY**: `if envNoColor(env) && isatty` | `CLICOLOR_FORCE` (ParseBool) raises to at least ANSI. **Observed (gum 2.0.1): `NO_COLOR=1 CLICOLOR_FORCE=1 gum style ... \| cat` still emits color**, contradicting the doc comment "NO_COLOR takes precedence". `TTY_FORCE=1` treats output as a TTY | profile order `NoTTY < ASCII < ANSI < ANSI256 < TrueColor`; result = max(env, terminfo `Tc`/`RGB`, `tmux info`) unless NO_COLOR; its `TERM` test `strings.Contains(term, "st")` is a substring match | [S24] `env.go` |
| **Rich** (Python; Textual builds on it) | `NO_COLOR != ""` -> `no_color` (colors stripped, bold kept) | `FORCE_COLOR` (non-empty -> terminal), `TTY_COMPATIBLE`, `TTY_INTERACTIVE=0\|1` | `TERM` dumb/unknown -> no color | [S19] |
| **Textual** | `"NO_COLOR" in environ` (**even when empty**, unlike no-color.org); adds a `Monochrome()` line filter; CSS pseudo-class `:nocolor` | `TEXTUAL_COLOR_SYSTEM=auto\|standard\|256\|truecolor\|windows` | by default converts ANSI-16 to its own truecolor; opt in to themeable ANSI with `App(ansi_color=True)` / `ansi-dark`, `ansi-light` themes | `src/textual/app.py` |
| **crossterm** (Ratatui default backend) | non-empty -> every `Colored` formats to nothing | none | **no depth detection**; the app must detect truecolor itself | [S24] `colored.rs` |
| **Ratatui** | **no handling** (grep of 0.30.2: no hits) | none | emits whatever `Color` you set; map styles to modifiers-only yourself | source read |
| **blessed** (Python 1.50.0) | non-empty disables | `FORCE_COLOR`/`CLICOLOR_FORCE` enable | color count from terminfo + `COLORTERM` | source read |


---

## D2. Which color depth? (16 / 256 / truecolor)

**Rule**: env heuristics, then an optional in-band probe, then a user override flag (`--color=16|256|truecolor`). Truecolor detection is heuristic in every library (`derived:`).

Heuristic chain (`derived:` from [S14], [S18], [S19], [S24]):

1. `COLORTERM` in {`truecolor`, `24bit`} -> 24-bit. Exception: `TERM=screen*` or `tmux*` without tmux evidence -> cap at 256 (termenv requires `TERM_PROGRAM=tmux`; colorprofile asks `tmux info` for `Tc`/`RGB`).
2. `TERM` ends `-direct`, or terminfo has `RGB` (ncurses >= 6.0-20180121) / `Tc` (tmux) -> 24-bit.
3. `TERM` in {`xterm-kitty`, `xterm-ghostty`, `wezterm`, `alacritty`, `foot`, `contour`, `rio`} or `WT_SESSION` set -> 24-bit (supports-color and termenv/colorprofile lists).
4. `TERM_PROGRAM=iTerm.app` with version >= 3 -> 24-bit. `Apple_Terminal` -> 256 in supports-color; **stale from macOS 26 (Tahoe)**, which added truecolor [S14].
5. `TERM` contains `256color` -> 256.
6. `TERM` matches `color|ansi|xterm|screen|vt100|rxvt|linux` -> 16. `CLICOLOR=1` alone -> 16.
7. Optional upgrade by probe (below).

**Environment reality**: `COLORTERM` is not forwarded by `ssh`/`sudo` by default (needs `SendEnv`/`AcceptEnv`/`env_keep`); apps under tmux see `TERM=tmux-256color|screen-256color` and often no `COLORTERM` [S14][S10]. So env-only detection under-reports truecolor over ssh and inside multiplexers; this is why the probe exists.

**SGR forms** [S1][S14][S2]:

| Depth | Set fg / bg | Notes |
|---|---|---|
| 16 | `30-37` / `40-47`; bright `90-97` / `100-107` (aixterm; less portable for backgrounds) | exact RGB is chosen by the user's theme |
| 256 | `38;5;N` / `48;5;N` (or colon `38:5:N`) | 0-15 theme, 16-231 cube, 232-255 grey |
| truecolor | `38;2;R;G;B` / `48;2;R;G;B` | **emit the semicolon form**: Windows Terminal and Ghostty accept only semicolons per [S14]. ISO colon forms `38:2::R:G:B`, `38:2:R:G:B` exist; xterm: "after the first colon, colons must be used"; foot tolerates the missing colour-space-id variant |
| underline color | `58;2;R;G;B`, `58:5:N`; reset `59` | terminfo `Setulc`/`Su` |

**In-band truecolor probe** (transparent to ssh/sudo, [S14]):

```text
send   ESC[48:2:1:2:3m  ESC P $ q m ESC \          # DECRQSS "read back SGR"
reply  ESC P 1 $ r 4 8 : 2 : 1 : 2 : 3 m ESC \     -> truecolor with colon syntax OK
reply  ESC P 1 $ r 4 0 m ESC \                     -> color not accepted
reply  ESC P 0 $ r ESC \                           -> DECRQSS unsupported
```

No reply "within a few centiseconds" -> probably no truecolor [S14]. Send `ESC[0m` afterwards. Terminfo route (Bubble Tea v2): `tea.RequestCapability("RGB")` answered by `tea.ColorProfileMsg`. XTGETTCAP (`DCS + q <hex> ST`) works on xterm, kitty*, WezTerm*, Ghostty*, not iTerm2* [S17]. Query mechanics (DA1 sentinel, timeouts): `terminal-escapes.md` D6.

**Example**: Ratatui app startup: `let truecolor = matches!(env::var("COLORTERM").as_deref(), Ok("truecolor"|"24bit"));` then pick the `Color::Rgb` or `Color::Indexed` theme; crossterm will not do it for you.

---

## D3. How do I downsample truecolor to 256 and 16?

**Rule**: author themes in truecolor; derive 256 by OKLab nearest over indices **16-255 only**; do **not** derive 16-color mechanically, hand-author the 16-color mapping per theme; **re-check contrast on the quantized pair**. Implemented in `SKILL_DIR/scripts/_theme.py` (`palette256`, `nearest256`, `oklab`, `sgr(..., depth=)`; read it instead of re-deriving the math); token fallbacks in [color-tokens.md](color-tokens.md).

### The xterm 256 palette (exact, [S1b] `256colres.pl`)

```text
cube index   = 16 + 36*r + 6*g + b          r,g,b in 0..5
cube level   = 0, 95, 135, 175, 215, 255    (n ? n*40+55 : 0)  -- first step is 95, then +40
grey index   = 232 + i   (i in 0..23)       level = 8 + 10*i  -> 8, 18, ... 238 (no pure black/white; use 16 and 231)
0..15        = NOT fixed: the user's theme
```

`SKILL_DIR/scripts/_theme.py` `palette256(ansi16)` builds the full 256-entry palette from the theme's 16 slots using exactly these formulas.


### What indices 0-15 look like in practice (why 16-color is theme roulette)

| idx | xterm default | VGA (UNVERIFIED, from memory) | Windows Terminal Campbell [S8] | kitty default [S4] |
|---|---|---|---|---|
| 0 black | 000000 | 000000 | 0C0C0C | 000000 |
| 1 red | CD0000 | AA0000 | C50F1F | CC0403 |
| 2 green | 00CD00 | 00AA00 | 13A10E | 19CB00 |
| 3 yellow | CDCD00 | AA5500 | C19C00 | CECB00 |
| 4 blue | 0000EE | 0000AA | 0037DA | 0D73CC |
| 5 magenta | CD00CD | AA00AA | 881798 | CB1ED1 |
| 6 cyan | 00CDCD | 00AAAA | 3A96DD | 0DCDCD |
| 7 white | E5E5E5 | AAAAAA | CCCCCC | DDDDDD |
| 8 br.black | 7F7F7F | 555555 | 767676 | 767676 |
| 9 br.red | FF0000 | FF5555 | E74856 | F2201F |
| 10 br.green | 00FF00 | 55FF55 | 16C60C | 23FD00 |
| 11 br.yellow | FFFF00 | FFFF55 | F9F1A5 | FFFD00 |
| 12 br.blue | 5C5CFF | 5555FF | 3B78FF | 1A8FFF |
| 13 br.magenta | FF00FF | FF55FF | B4009E | FD28FF |
| 14 br.cyan | 00FFFF | 55FFFF | 61D6D6 | 14FFFF |
| 15 br.white | FFFFFF | FFFFFF | F2F2F2 | FFFFFF |

xterm column derived from `XTerm-col.ad` X11 names [S1b]. Never assume an ANSI slot's name equals its hue in a given theme (Dracula's "blue" slot is purple; Solarized `bright_black` equals the background, see [accessibility.md](accessibility.md)).

### How shipping libraries pick the nearest color

| Implementation | Method | Source |
|---|---|---|
| tmux `colour_find_rgb` | `to6(v) = v<48 ? 0 : v<114 ? 1 : (v-35)//40`; exact-hit shortcut; grey candidate `(avg-3)//10`; picks cube vs grey by squared RGB distance; only 16-255 | [S10] `colour.c` |
| termenv `hexToANSI256Color` | same cube thresholds, cube-vs-grey by HSLuv distance. `derived:` its grey index averages the *cube indices* (0..5), not 0..255 values, which looks like a porting slip: verify before copying | [S24] |
| Rich `Color.downgrade` | saturation < 0.15 -> grey ramp; else cube by level index; 16-color via "redmean" weighted RGB | [S19] |
| Windows legacy console | nearest of its 16 colors | [S8] |
| termstandard | Euclidean "gives poor results"; CIEDE2000 better but slow | [S14] |

**Measurement** (`derived:`, 4000 uniform random sRGB samples, indices 16-255, error scored with CIEDE2000, validated on Sharma's test pairs):

| Method | agrees with CIEDE2000 pick | mean dE00 | p95 dE00 |
|---|---|---|---|
| Euclidean RGB | 60.3 % | 6.46 | 16.9 |
| redmean (Rich) | 60.6 % | 6.45 | 17.2 |
| tmux fast formula | 61.2 % | 6.40 | 16.9 |
| **OKLab Euclidean** | **69.5 %** | **5.74** | **13.2** |
| CIEDE2000 brute force | 100 % | 5.08 | 10.3 |

To 16 colors the mean error is 18.1 (Euclid), 15.5 (OKLab), 13.9 (CIEDE2000): huge under any metric, and the 16 colors are the user's anyway.

### Rules

| Depth | Rule | Example |
|---|---|---|
| truecolor -> 256 | brute-force OKLab nearest over **16-255** (240 candidates); an exact palette hit wins at distance 0; never include 0-15 | `#f38ba8` -> index chosen by `_theme.nearest256()`; CIEDE2000 only for golden tests |
| any -> 16 | hand-authored per-theme table (`ansi16` in the theme JSON, defaults in `themes/_tokens.json`); mechanical mapping is unsafe: `#f38ba8` maps to 9 (OKLab) or 13 (CIEDE2000) | `fg.faint` -> `8` is invisible on Solarized, so Solarized overrides it |
| 16-color backgrounds | prefer `40-47`; `100-107` are aixterm and less portable [S1] | selection = `reverse` rather than a bright background |
| none (`NO_COLOR`, dumb) | drop color SGR, keep bold/underline/inverse | `python3 SKILL_DIR/scripts/render_mockup.py F.mock --depth none` |
| after quantizing | recompute WCAG for every emitted fg/bg pair; fail < 4.5 text, < 3 UI | `python3 SKILL_DIR/scripts/contrast_check.py ID --depth 16` |
| theme downsampling | quantize fg and bg separately, then re-check the pair | quantization can break a passing pair |

Reference implementation: `SKILL_DIR/scripts/_theme.py` (`oklab` = Ottosson matrices on linearized sRGB; `nearest256` = brute-force OKLab distance over indices 16-255 (an exact palette hit has distance 0, so it needs no shortcut); `blend` models dim text). Golden-test against CIEDE2000 if you port it.


---

## D4. Which text attributes can I rely on? (SGR)

**Rule**: bold, underline, inverse, dim, italic and strike are safe everywhere that matters; treat blink, overline, curly underline, and hidden as enhancements. Never let an attribute be the *only* carrier of state (selection = marker + inverse).

| SGR | Attribute | Off | Support and caveats |
|---|---|---|---|
| 1 | bold | 22 | glyph weight and/or bright color (see below) |
| 2 | faint/dim | 22 | alpha-blend toward bg, modelled as blend 0.55 ([formats.md](formats.md#contrast-floors)); contrast **not guaranteed** ([accessibility.md](accessibility.md)); Ghostty `faint-opacity` (1.2.0+) [S6] |
| 3 | italic | 23 | font-dependent |
| 4 | underline | 24 | substyles `4:1` single, `4:2` double, `4:3` curly, `4:4` dotted, `4:5` dashed (kitty-originated); `21` = double (ECMA-48 3rd) [S4][S1] |
| 5 / 6 | blink slow / rapid | 25 | varies; WCAG 2.2.2: blinking > 5 s needs a stop mechanism |
| 7 | inverse | 27 | swaps fg/bg; guarantees the original pair's contrast |
| 8 | hidden | 28 | foot: "not visible, but is copiable" [S2] |
| 9 | strikethrough | 29 | |
| 53 / 55 | overline on/off | | **Alacritty rejects 51-55** [S3]; foot has no 53 [S2]; WezTerm, Windows Terminal, tmux parse it |
| 58 / 59 | underline color set/reset | | terminfo `Su`, `Smulx`, `Setulc` |
| `CSI # {` / `CSI # }` | XTPUSHSGR / XTPOPSGR (stack of 10) | | xterm-ish [S1]; lets components restore style |

terminfo / tmux feature names for detection: `Su`/`Smulx` styled underline, `Setulc`/`Setulc1` underline color, `Smol` overline, `Tc`/`RGB` truecolor, `Ss`/`Se` cursor style, `Ms` clipboard, `Hls` hyperlinks, `Sync` synchronized updates, `Sxl` sixel, `Spb` OSC 9;4 progress, `Nobr` "terminal does not use bright colors for bold" [S10].

### Bold-as-bright

| Terminal | Behavior | Source |
|---|---|---|
| xterm | `boldColors` resource maps colors 0-7 to 8-15 when bold; default true | [S1c] |
| Windows Terminal | `intenseTextStyle: none\|bold\|bright\|all`, **default `bright`** (bold text = bright color, not a bold glyph) | [S8] |
| Alacritty | `draw_bold_text_with_bright_colors` default **false** | [S3] |
| Ghostty | `bold-color` = color or `bright` (1.2.0+) | [S6] |

**Rule**: never rely on bold changing hue. Emphasize with bold plus an explicit color, and check contrast for both outcomes (0-7 vs 8-15). Request bright variants explicitly with `90-97`.

---

## D5. Is the terminal dark or light?

**Rule** (single home for dark/light detection): ask the terminal, in this order; never block startup (render dark defaults, upgrade when the reply arrives).

| Step | How | Sources |
|---|---|---|
| 1 | `DECRQM ?2031`: `CSI ? 2031 $ p`; if `Pm` is 1 or 2, send `CSI ? 2031 h` (push updates) and `CSI ? 996 n` (query). Reply `CSI ? 997 ; 1 n` = dark, `CSI ? 997 ; 2 n` = light. Supported: Contour, Ghostty >= 1.0.0, kitty >= 0.38.1, VTE >= 0.82.0, tmux >= 3.6, iTerm2, foot. WezTerm: "not yet". Neovim and Helix already use it | [S9][S2][S7][S10] |
| 2 | `OSC 11 ; ? ST` + DA1 sentinel (`terminal-escapes.md` D6). Parse `rgb:RRRR/GGGG/BBBB` (1-4 hex digits per channel). **Dark if CIE L*/100 <= 0.5** (terminal-colorsaurus rule); tmux's cheap rule: `r+g+b > 382` on 8-bit channels = light | [S13][S10] |
| 3 | `COLORFGBG` last field = background palette index (rxvt convention). "Dark for 0-6 and 8, light for 7 and 15" is recollection, `UNVERIFIED`; termenv reads the index | [S24] |
| 4 | flag/config; default to dark and keep contrast floors valid on both | |

**Example** (kitty, Ghostty): send `ESC[?2031h ESC[?996n ESC[c`; handle `ESC[?997;2n` by switching to the light theme; on exit send `ESC[?2031l`.

---

## D6-D8. Queries, escape-sequence modes, per-terminal support (moved)

In [terminal-escapes.md](terminal-escapes.md): **D6** queries (DA1 sentinel, OSC 4/10/11, DECRQM, CPR, XTVERSION), **D7** modes with exact enable/disable sequences and the restore-on-exit checklist, **D8** the 12-terminal support matrix. Rule: query only with a DA1 sentinel and a hard timeout, never block startup on a reply, and treat no answer as "unknown", not "unsupported".

---

## D9. What must the user configure under tmux or GNU screen?

**tmux** (3.8 current; all from [S10] unless noted):

| Need | Setting | Notes |
|---|---|---|
| Truecolor | `set -as terminal-features ',xterm-256color:RGB'` (glob on the outer `$TERM`); legacy spelling `terminal-overrides ',*:Tc'` ("Tc ... is equivalent to the RGB capability") | feature names: `256 appesc clipboard ccolour cstyle extkeys focus hyperlinks ignorefkeys margins mouse osc7 overline progressbar rectfill RGB sixel strikethrough sync title usstyle utf8`; append `@` to disable (e.g. `xterm*:sync@`); tmux auto-detects a few common terminals; 3.3 also treats the outer `COLORTERM` as an RGB hint |
| Passthrough | `set -g allow-passthrough on` (`all` also for invisible panes); wrap as `ESC P tmux ; <seq with every ESC doubled> ESC \` | needed for kitty graphics, notifications, anything tmux does not parse; kitty graphics also need Unicode placeholders (`derived:` from [S4]) |
| Keys | `set -g extended-keys on` (+ `extended-keys-format csi-u`) | tmux does **not** implement the kitty keyboard protocol |
| Clipboard | `set -g set-clipboard on\|external\|off`, and the terminal must allow OSC 52 | xterm needs `disallowedWindowOps: 20,21,SetXprop` |
| Focus events | `set -g focus-events on` | |
| Hyperlinks / sync / themes | native since 3.4 / 3.7 / 3.8 | |
| Env | apps see `TERM=tmux-256color\|screen-256color`, often no `COLORTERM`; termenv/colorprofile deliberately do not upgrade to truecolor from `TERM=screen*\|tmux*` alone [S24]. Whether `COLORTERM` survives into new panes depends on `update-environment` (UNVERIFIED, not tested) | |

**Capture for audits**: `capture-pane -p -e`, never `-J` for grids, pad rows to `pane_width`, overline arrives as `5:3`, private `tmux -L` server; the procedure is in `audit-protocol.md`.

**GNU screen** (5.0.0, 2024; secondary sources [S15]): truecolor only with `truecolor on` and the 5.x status-line color syntax is incompatible with 4.x; stock builds strip OSC 8; no OSC 10/11 answers [S13]; `altscreen` off by default (†). Treat as a 256-color, no-extras target.

---

## D10. How do I handle resize signals?

**Rule**: the too-small screen, the minimum-size computation and the degradation order are defined once in [layout-archetypes.md §2.1-2.2](layout-archetypes.md#21-size-classes-and-what-to-show); this section covers only how the app learns the size.

**Signals**: SIGWINCH (BSD/Linux, not POSIX): set a dirty flag and read the size with `TIOCGWINSZ` in the event loop, never draw inside the handler (racy; [S45]). Alternatives: in-band resize 2048 (`terminal-escapes.md` D7), Windows `WINDOW_BUFFER_SIZE_EVENT`. Coalesce bursts (drag-resize emits dozens), redraw fully after resize (reflow corrupts diff state), clamp negative widths (unsigned underflow is the classic crash) (`derived:`). Keep handling resize and quit while the too-small screen is shown.

**Baseline sizes**: 80x24 is the de-facto assumed minimum (origin VT100; no citation retrieved, `UNVERIFIED`). Counter-data: Windows Terminal opens at **120x30** (`initialCols`/`initialRows`) [S8]; kitty's default window is 640x400 px (cell count depends on font) [S4]. The skill's standard mockup sizes are 80x24, 120x30, 170x40 ([formats.md](formats.md#frame-naming)).

---

## Source index

Specs and data: **S1** xterm ctlseqs https://invisible-island.net/xterm/ctlseqs/ctlseqs.html (patch #411, 2026/08/23); **S1b** `256colres.pl`, `XTerm-col.ad` https://github.com/ThomasDickey/xterm-snapshots ; **S1c** xterm(1) https://invisible-island.net/xterm/manpage/xterm.html ; **S37** https://clig.dev/ ; **S38** https://no-color.org/ https://force-color.org/ https://bixense.com/clicolors/ ; **S45** in-band resize https://gist.github.com/rockorager/e695fb2924d36b2bcf1fff4a3704bd83 .

Terminals/multiplexers: **S2** foot https://codeberg.org/dnkl/foot/src/branch/master/doc/foot-ctlseqs.7.scd ; **S3** Alacritty https://github.com/alacritty/alacritty (`extra/man/alacritty-escapes.7.scd`, `CHANGELOG.md`, `docs/features.md`) ; **S4** kitty https://sw.kovidgoyal.net/kitty/ (underlines, keyboard-protocol, text-sizing-protocol, desktop-notifications, clipboard, faq, changelog, conf) ; **S5** WezTerm https://wezterm.org/escape-sequences.html and config pages ; **S6** Ghostty https://ghostty.org/docs/config/reference , /docs/vt/reference ; **S7** iTerm2 https://iterm2.com/documentation-escape-codes.html , https://iterm2.com/downloads.html ; **S8** Windows Terminal https://github.com/microsoft/terminal (`DispatchTypes.hpp`, `OutputStateMachineEngine.cpp`, `defaults.json`), https://devblogs.microsoft.com/commandline/ (1.22, 1.25 Preview), https://github.com/MicrosoftDocs/terminal ; **S9** Contour https://github.com/contour-terminal/vt-extensions , https://gist.github.com/christianparpart/d8a62cc1ab659194337d73e399004036 (2026), https://github.com/contour-terminal/terminal-unicode-core (2027) ; **S10** tmux https://github.com/tmux/tmux (`tmux.1`, `CHANGES`, `colour.c`) ; **S11** OSC 8 https://gist.github.com/egmontkob/eb114294efbcd5adb1944c9f3cb5feda , https://github.com/Alhadis/OSC8-Adoption ; **S12** https://www.arewesixelyet.com/ ; **S13** terminal-colorsaurus https://github.com/bash/terminal-colorsaurus (`doc/terminal-survey.md`, `doc/feature-detection.md`) ; **S14** https://github.com/termstandard/colors ; **S15** screen 5.0 (secondary) https://lwn.net/Articles/987700/ ; **S16** Terminal.app (secondary) https://gabebw.com/blog/2024/01/06/hyperlinks-in-the-terminal ; **S17** third-party matrices (`*`) https://docs.otty.sh/vt/terminal-comparison , https://tmuxai.dev/terminal-compatibility/ , https://terminaltrove.com/terminals/konsole/ ; **S21** Ghostty `grapheme-width-method` https://ghostty.org/docs/config/reference .

Libraries/apps (source read): **S18** supports-color https://github.com/chalk/supports-color/blob/main/index.js ; **S19** Rich https://github.com/Textualize/rich (`console.py`, `color.py`, `palette.py`) ; **S24** termenv https://github.com/muesli/termenv , colorprofile https://github.com/charmbracelet/colorprofile (`env.go`), crossterm https://github.com/crossterm-rs/crossterm (`style/types/colored.rs`) ; **S26** lazygit https://github.com/jesseduffield/lazygit (`docs/Config.md`) ; **S31** btop https://github.com/aristocratos/btop (`src/btop.cpp`, `btop_draw.cpp`, `btop_tools.cpp`) ; **S42** Claude Code accessibility https://code.claude.com/docs/en/accessibility .
