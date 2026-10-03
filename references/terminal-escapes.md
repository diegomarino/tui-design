# Terminal escapes: queries, modes and the per-terminal support matrix

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [D6. What can I ask the terminal, safely?](#d6-what-can-i-ask-the-terminal-safely) · L14–35 — querying the terminal (colours, size, features) without hanging on one that never answers.
- [D7. Which modes and protocols do I enable, and with what exact sequences?](#d7-which-modes-and-protocols-do-i-enable-and-with-what-exact-sequences) · L37–76 — the exact sequences for alt screen, mouse, paste, focus, keyboard protocols, and the restore-on-exit checklist.
- [D8. Which terminals support what? (12-terminal matrix)](#d8-which-terminals-support-what-12-terminal-matrix) · L78–123 — whether a feature works in a given terminal (12-terminal matrix).

Read this when you emit raw escape sequences, build without a framework, or need per-terminal support: queries (D6), modes with exact sequences and the restore-on-exit checklist (D7), the 12-terminal support matrix (D8). Color depth, NO_COLOR, dark/light detection, tmux/screen and resize are in [terminal-capabilities.md](terminal-capabilities.md).

Evidence tags: `[Sn]` = [source index](terminal-capabilities.md#source-index) (read 2026-10-01). `derived:` = inference or own computation. `UNVERIFIED` = not confirmed from a primary source. In the matrix, `†` = prior knowledge not re-verified, `*` = only a third-party matrix says so (Otty/tmuxai/Terminal Trove contradict each other and first-party docs; low confidence).

---

## D6. What can I ask the terminal, safely?

**Rule**: all replies arrive on **stdin**, in order, interleaved with user input. Read from the tty in raw mode, time-box every query, batch queries in one write, and **always append a DA1 sentinel** (`CSI c`): terminals answer in order, so if the DA1 reply arrives first, the earlier queries are unsupported and no timeout is needed. Still keep a hard timeout (colorsaurus default 1 s) because a terminal without DA1 or a slow ssh link hangs otherwise [S13]. Without the sentinel, late replies leak into the shell as `^[]11;rgb:...`.

| Query | Send | Reply | Notes |
|---|---|---|---|
| Primary DA (DA1) | `CSI c` | `CSI ? Pp ; Ps ; ... c` | Ps 4 = Sixel, 22 = ANSI color, 1 = 132 cols, 6 = selective erase [S1]; nearly universal [S13] |
| Secondary DA | `CSI > c` | `CSI > Pp ; Pv ; Pc c` | terminal type + version |
| XTVERSION | `CSI > 0 q` | `DCS > \| name(version) ST` | foot: `ESC P > \| foot(1.x) ESC \` [S1][S2] |
| DECRQM (private) | `CSI ? Ps $ p` | `CSI ? Ps ; Pm $ y` | Pm 0 unknown, 1 set, 2 reset, 3 perm. set, 4 perm. reset. Works for 2026, 2027, 2031, 2048, 1016, 2004 [S9] |
| Cursor position | `CSI 6 n` | `CSI row ; col R` | also a width probe: print the glyph, ask CPR (`derived:`) |
| Text area size | `CSI 18 t` chars, `CSI 14 t` px, `CSI 16 t` cell px | `CSI 8;rows;cols t`, `CSI 4;h;w t`, `CSI 6;h;w t` | Alacritty marks most `CSI t` unsupported (22/23 partial); foot answers 13-19 approximately on Wayland; Windows Terminal 1.22 added 14/16 [S1][S3][S2][S8] |
| Palette entry | `OSC 4 ; c ; ? ST` | `OSC 4 ; c ; rgb:RRRR/GGGG/BBBB ST` | several `c;?` pairs allowed |
| Default fg / bg | `OSC 10 ; ? ST` / `OSC 11 ; ? ST` | `OSC 10 ; rgb:RRRR/GGGG/BBBB ST` | 16 bits/channel is the norm (Ghostty `osc-color-report-format` default 16-bit [S6]). **Terminators**: macOS Terminal and Terminology always reply with BEL even if asked with ST; old urxvt replies with bare ESC [S13]; accept `ESC \` and BEL |
| Theme mode | `CSI ? 996 n` | `CSI ? 997 ; 1\|2 n` | detection order: `terminal-capabilities.md` D5 |
| SGR read-back | `DCS $ q m ST` | `DCS 1 $ r <sgr> m ST` | truecolor probe (`terminal-capabilities.md` D2) |
| XTGETTCAP | `DCS + q <hex-cap> ST` | | xterm, kitty*, WezTerm*, Ghostty*, not iTerm2* [S17] |
| Kitty keyboard flags | `CSI ? u` | `CSI ? flags u` | pair with DA1 |

**Timing/ssh/tmux** (`derived:` plus sources): termenv waits `OSCTimeout = 5 s` [S24], colorsaurus 1 s, the termstandard probe "a few centiseconds"; over ssh budget one RTT per round trip and batch. On macOS use `select` or the stdin fd, `poll(2)` on `/dev/tty` is unreliable [S13]. GNU screen does not answer OSC 10/11 [S13]. tmux answers OSC 4 since 3.3, forwards OSC 10/11 to the first attached client since 3.4, forwards unset OSC 4 since 3.6 (also mode 2031, guessing theme from bg), 3.7 reports DECRQM 2026 and handles OSC 9;4, **3.8** adds built-in light/dark themes and reports the *terminal's* theme to panes [S10]. No answer is not "no feature": it may be slow. Never block startup on a query.

---

## D7. Which modes and protocols do I enable, and with what exact sequences?

**Rule**: enable only what you handle; query support first where a reply exists (DECRQM); on every exit path restore everything (checklist after the table).

| Feature | Enable / disable | Events or reply | Notes (sources) |
|---|---|---|---|
| Alternate screen | `CSI ? 1049 h` / `l` | | saves cursor, switches, clears. 1047 = buffer only, 47 = legacy; "use this with terminfo-based applications rather than the 47 mode" [S1]. No scrollback on alt screen: bad for screen-reader review and for pipelines ([accessibility.md](accessibility.md)) |
| Bracketed paste | `CSI ? 2004 h` / `l` | text wrapped in `ESC[200~ ... ESC[201~` | strip embedded `ESC[201~` from untrusted paste [S1] |
| Focus events | `CSI ? 1004 h` / `l` | `CSI I` in, `CSI O` out | tmux needs `set -g focus-events on` [S1][S10] |
| Mouse | 1000 press/release, 1002 + drag, 1003 + all motion (skip 1001, "hang-prone") | | [S1] |
| Mouse encoding | **1006 SGR**: `CSI < Cb ; Cx ; Cy M` press, `m` release. 1016 = SGR-Pixels (same format, pixel coords). 1005 UTF-8 and 1015 urxvt are legacy ("not an improvement over 1006"). Default X10 encoding caps at col/row 223 (`derived:`) | | `Cb` low bits 0/1/2 = left/middle/right; `+4` shift, `+8` meta, `+16` ctrl, `+32` motion; wheel = 64 up, 65 down; buttons 6-7 `+64`, 8-11 `+128` [S1]. Enable 1006 together with 1000/1002/1003 |
| Alternate scroll | `CSI ? 1007 h` | wheel -> arrow keys on alt screen | [S1] |
| Synchronized output | `CSI ? 2026 h` ... `CSI ? 2026 l` | | wrap every frame; no consensus timeout [S9]; query DECRQM first; tmux >= 3.7 |
| Grapheme clusters | `CSI ? 2027 h` / `l` | | every UTS #29 cluster in one cell; VS16 forces width 2; VS15 does not change width [S9] |
| In-band resize | `CSI ? 2048 h` / `l` | `CSI 48;rows;cols;ypx;xpx t` | reports immediately on enable; px 0 if unknown [S45] |
| Theme push | `CSI ? 2031 h` / `l` | `CSI ? 997 ; 1\|2 n` | `terminal-capabilities.md` D5 |
| Kitty keyboard | push `CSI > flags u`; pop `CSI < n u`; set `CSI = flags ; mode u` (mode 1 set, 2 add, 3 remove); query `CSI ? u` | flags 1 disambiguate, 2 event types (press/repeat/release), 4 alternate keys, 8 all keys as escapes, 16 associated text | separate stacks for main/alt screen; with flag 1 Ctrl-C arrives as `CSI 99;5u`, not SIGINT; Enter/Tab/Backspace stay legacy so a crash cannot brick the shell [S4]. **Always pop on exit** |
| modifyOtherKeys | `CSI > 4 ; 2 m` | `CSI 27 ; mods ; key ~` | older; tmux speaks `extended-keys` (`xterm` or `csi-u` format) [S10] |
| Hyperlinks (OSC 8) | `OSC 8 ; id=x ; URI ST` text `OSC 8 ; ; ST` | | `id` is the only defined param; URI <= ~2083 bytes (VTE, iTerm2); bytes 32-126 (percent-encode); close with empty URI; always visible fallback text; use `id` for wrapped/multi-line links [S11] |
| Clipboard (OSC 52) | `OSC 52 ; Pc ; base64 ST`; query with `?` | | `Pc` = c/p/q/s/0-7; policies differ (matrix); kitty also has OSC 5522 (MIME-aware) [S1][S4] |
| Notifications | iTerm2 `OSC 9 ; msg ST`; urxvt/VTE-style `OSC 777 ; notify ; title ; body ST`; kitty `OSC 99 ; i=ID:p=body ; text ST` | | [S7][S2][S4]; fallback `BEL` |
| Progress | `OSC 9 ; 4 ; st ; pr ST`: st 0 clear, 1 value 0-100, 2 error, 3 indeterminate, 4 paused (ConEmu) | | iTerm2 [S7], kitty draws a bar (0.47+) [S4], Ghostty `progress-style` [S6], tmux stores it (3.7) [S10]; Bubble Tea v2 exposes `View.ProgressBar` |
| Shell integration | `OSC 133 ; A` prompt start, `C` output start, `D ; exit` end | | FinalTerm origin; Claude Code emits it at turn boundaries [S2][S42] |
| CWD | `OSC 7 ; file://host/path ST` | | [S2] |
| Title | `OSC 0/2 ; text ST`; push/pop `CSI 22 ; 2 t` / `CSI 23 ; 2 t` | | restore on exit; tmux `allow-rename` [S1] |
| Cursor style | `CSI Ps SP q`: 0 default, 1/2 block blink/steady, 3/4 underline, 5/6 bar | | [S8] |
| Graphics | Sixel `DCS q ... ST`; kitty `APC G ... ST`; iTerm2 `OSC 1337 ; File=... : base64 BEL` | | detect Sixel via DA1 param 4 [S1]; kitty text sizing `OSC 66 ; w=N ; text ST` [S4] |
| Soft reset | `CSI ! p` | | crash-path recovery [S1] |

**Restore-on-exit checklist** (`derived:`): disable mouse (1000/1002/1003/1006/1016), 2004, 1004, 2026 if mid-frame, 2031, 2048; pop kitty keyboard; show cursor `CSI ? 25 h`; reset cursor shape `CSI 0 SP q`; `SGR 0`; leave alt screen `1049 l`; pop title. Run it from `atexit` and SIGINT/SIGTERM/SIGHUP handlers and from panic hooks (Ratatui `init` installs one; install `color_eyre` first, then init).

**Example startup/shutdown** (Fleet-class fullscreen app):

```text
start:  ESC[?1049h ESC[?25l ESC[?1006h ESC[?1002h ESC[?2004h ESC[?1004h ESC[>1u   (+ ESC[?2031h if `terminal-capabilities.md` D5 step 1 works)
frame:  ESC[?2026h  ...cells...  ESC[?2026l
stop:   ESC[<u ESC[?1004l ESC[?2004l ESC[?1002l ESC[?1006l ESC[?25h ESC[0 q ESC[0m ESC[?1049l
```

---

## D8. Which terminals support what? (12-terminal matrix)

Legend: `Y` yes, `N` no, `~` partial/conditional, `?` unknown. `†` prior knowledge not re-verified; `*` third-party matrix only.

| Feature | iTerm2 | kitty | WezTerm | Ghostty | Alacritty | Windows Terminal | Terminal.app | GNOME/VTE | Konsole | foot | tmux | GNU screen |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Truecolor (38;2) | Y | Y | Y | Y | Y | Y | Y (macOS 26+; N before) | Y (>=0.36) | Y | Y | Y (>=2.2; needs RGB/Tc) | ~ (5.0, opt-in `truecolor on`) |
| Styled underline 4:2-4:5 + 58 | Y† | Y | Y | Y† | Y | Y | ? | Y† | ? | Y | Y (`usstyle`) | N† |
| Overline 53 | ? | Y† | Y | Y† | **N** (declined) | Y | ? | Y† | ? | **N** | Y (`overline`) | N† |
| Bold/dim/italic/inverse/hidden/strike | Y† | Y | Y | Y† | Y | Y | ~† | Y† | Y† | Y | Y | ~† |
| Alt screen 1049 | Y† | Y† | Y† | Y† | Y | Y | Y† | Y† | Y† | Y | Y | ~† (`altscreen` off by default) |
| Bracketed paste 2004 | Y† | Y† | Y† | Y† | Y | Y | Y† | Y† | Y† | Y | Y | ? |
| Focus events 1004 | Y† | Y† | Y† | Y† | Y | Y | ? | Y† | Y† | Y | Y (`focus-events`) | ? |
| Mouse 1000/1002/1003 + SGR 1006 | Y† | Y† | Y† | Y† | Y (1003 not in man page, UNVERIFIED) | Y | ~† | Y† | Y† | Y | Y† | ? |
| SGR-Pixels 1016 | Y | Y* | Y* | Y* | **N** | **N** | ? | ? | ? | Y | ? | ? |
| Synchronized output 2026 | Y | Y | Y | Y | Y | Y (stable 1.24) | ? | N (Contour table, undated, may be stale) | ? | Y | Y (>=3.7) | N† |
| Grapheme clustering / 2027 | ? | Y (own algorithm, 0.40+) | Y | Y (`grapheme-width-method=unicode` default) | N* | Y (1.22+, mode 2027) | ? | ? | ? | Y | ? | N† |
| Color scheme 996 / 2031 | Y | Y (>=0.38.1) | **N** ("not yet") | Y (>=1.0.0) | Y* | ? | ? | Y (>=0.82.0) | ? | Y | Y (>=3.6) | N† |
| OSC 8 hyperlinks | Y (3.1) | Y (0.19) | Y | Y | Y (0.11) | Y (1.4) | **N** (swallowed) | Y (0.50) | Y (since 2020; "disabled by default") | Y (1.7.0) | Y (>=3.4) | **N** (stock strips; patches exist) |
| OSC 52 write / read | ~† / ~† (pref) | Y† / ask† | Y† / ? | Y / ask | Y / off by default | Y / **N** | **N** / N | N† / N† | ? / ? | Y / Y | Y (`set-clipboard`) / ? | N† |
| Notifications | OSC 9 | OSC 99 | OSC 9* | OSC 9 (+99*) | **none** | 9 = ConEmu actions; 777 = urxvt handler (toast ?) | N† | ? | ? | 9, 777, 99 | none native (passthrough) | N† |
| Progress OSC 9;4 | Y | Y (>=0.47) | Y* | Y | N | Y† | N† | ? | ? | ? | Y (stores; >=3.7) | N† |
| Kitty keyboard protocol | Y (3.7.x) | Y | ~ (`enable_kitty_keyboard`, default false) | Y | Y (0.13) | Y (Preview 1.25, 2026-03) | N† | N† | N* | Y | **N** (extended-keys only) | N† |
| Kitty graphics | Y | Y | Y* | Y | N* | N* | N† | N† | ? (sources conflict) | N† | ~ (passthrough only) | N† |
| Sixel | Y (3.3.0) | **N** (declined) | Y | **N** | **N** (declined) | Y (1.22) | **N** | **N** (removed from stable) | Y (22.04) | Y (1.2.0) | ~ (`--enable-sixel` build) | N† |
| iTerm2 inline images (`OSC 1337`) | Y | N* | Y | N* | N* | N* | N† | N† | ? | N† | ~ (passthrough) | N† |
| OSC 10/11 color query | Y | Y | Y | Y | Y | Y (>=1.22) | Y (BEL-terminated) | Y | Y | Y | Y (>=3.4) | **N** |
| DECRQM | Y | Y* | Y* | Y* | Y | Y | ? | Y† | ? | Y | Y | N† |
| XTVERSION | Y* | Y* | Y* | Y* | Y* | ? | N† | ? | ? | Y | Y† | N† |
| "Ambiguous = wide" setting | Y | N† | Y (`treat_east_asian_ambiguous_width_as_wide`, default false) | N† | N† | Y (text measurement) | Y† | Y† | ? | ? | N† | ? |

**Row evidence** (what each cell rests on):
- **Truecolor**: [S14] list (iTerm2 >= v3, kitty, WezTerm, Ghostty, Alacritty, WT, VTE >= 0.36, Konsole, foot, "Terminal.app ... since MacOS 26", tmux "starting from version 2.2", screen "has support in 'master'"); iTerm2 "Set COLORTERM=truecolor to advertise 24-bit capability" [S7]; screen 5.0 `truecolor [on|off]` (secondary, [S15]).
- **Underline/overline/attributes**: kitty [S4]; WezTerm [S5]; Alacritty changelog and `alacritty-escapes(7)`: implements `0-9, 21-49, 58, 59, 90-97, 100-107`, rejects `11-19` and `51-55` [S3]; foot [S2]; WT `Overline = 53`, `UnderlineColor = 58` in `DispatchTypes.hpp` [S8]; tmux features `usstyle`, `overline`, `strikethrough` [S10].
- **Mouse/focus/paste/alt**: Alacritty modes `1 3 6 7 12 25 1000 1002 1004 1005 1006 1007 1042 1049 2004 2026` [S3]; foot lists 1000-1007, 1015, 1016, 1049, 2004, 2026, 2027, 2031, 2048 (TODO), 8452 [S2]; WT enum `1000 1002 1003 1004 1005 1006 1007 1049 2004 2026 2027 9001` [S8].
- **Sync output**: [S9] adoption table (WT, kitty, iTerm2, foot, WezTerm yes; VTE "not yet"; Alacritty since 0.13.0; Konsole unknown); WT stable 1.24 per the 1.25 Preview post [S8]; tmux 3.7 [S10]; iTerm2 "Add DECSET 2026" [S7].
- **2027 / theme**: [S9] palette-update doc adoption table, [S2], [S7] "DECSET 2031 and DECDSR 997", [S10], WT `GCM_GraphemeClusterMode = 2027` and 1.22 blog [S8], Ghostty [S21].
- **OSC 8**: Alhadis adoption list (versions as shown) [S11]; Terminal.app and screen from secondary reports [S15][S16].
- **OSC 52**: Ghostty "allow clipboard reading after prompting the user and allow writing unconditionally" [S6]; Alacritty "OSC 52 paste ability is now disabled by default; use `terminal.osc52`" [S3]; WT source: the `queryClipboard` branch does nothing, only set is dispatched [S8]; foot read+write [S2]; tmux `set-clipboard`, `Ms` [S10]; Terminal.app none (issue reports, [S16]).
- **Kitty keyboard**: [S4]; Alacritty 0.13 [S3]; foot [S2]; WT `KKP_KittyKeyboard*` in source and 1.25 Preview post [S8]; WezTerm [S5]; iTerm2 3.7.x changelog [S7]; tmux man: only `extended-keys` [S10].
- **Sixel**: verbatim from Are We Sixel Yet [S12] (iTerm2 "from version 3.3.0", WT "from version 1.22.10352.0", Konsole "landed in version 22.04", foot "from version 1.2.0", tmux "compiled with --enable-sixel", xterm "enabled by default since patch #359"; kitty, Ghostty, Alacritty declined; VTE "removes SIXEL support from every stable release").
- **OSC 10/11**: terminal-colorsaurus survey: all tested yes except GNU Screen, Linux console, PuTTY, MobaXterm, ConEmu; macOS Terminal replies BEL [S13].
- **Ambiguous-wide**: xterm `cjkWidth` [S1c]; iTerm2 changelog [S7]; WezTerm [S5]; WT 1.25 post mentions an "Ambiguous" option [S8].
- **Gaps**: VTE sync 2026 is from Contour's undated table; Terminal.app OSC 8/52 from issue reports, not Apple docs; Terminal.app `COLORTERM` behavior unknown (searched); Alacritty 1003 implemented per third party but absent from its man page; VTE `NEWS` not retrievable (GitLab 404). Third-party matrices (Otty, tmuxai, Terminal Trove) were used only for cells marked `*`; vtdn.dev pages are AI-generated placeholders and were not used.

**How to use the matrix**: design for the lowest common denominator in the top 5 rows (truecolor with 256 fallback, bold/underline/inverse, alt screen, bracketed paste); treat OSC 8, OSC 52, 2026, 2031, kitty keyboard as *progressive enhancements* with a no-op fallback; never make graphics (sixel/kitty/iTerm2) required. Check live: DECRQM for 2026/2027/2031, DA1 for sixel, XTVERSION for identification.
