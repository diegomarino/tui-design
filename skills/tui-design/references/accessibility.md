# Accessibility for terminal UIs: contrast, color-vision, screen readers, affordances

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [A1. Contrast: WCAG formula, our floors, and what the terminal changes](#a1-contrast-wcag-formula-our-floors-and-what-the-terminal-changes) · L18–87 — contrast maths and floors.
- [A2. Color-vision deficiency (CVD)](#a2-color-vision-deficiency-cvd) · L89–124 — CVD-safe status and selection cues.
- [A3. Screen readers and TUIs: the realistic state](#a3-screen-readers-and-tuis-the-realistic-state) · L126–153 — screen-reader and linear modes.
- [A4. Recommended affordances (checklist for design and audit)](#a4-recommended-affordances-checklist-for-design-and-audit) · L155–186 — the accessibility checklist.
- [A5. Audit protocol hooks (what to run, what to look for)](#a5-audit-protocol-hooks-what-to-run-what-to-look-for) · L188–201 — accessibility checks in an audit.
- [A6. Gaps and unverified items](#a6-gaps-and-unverified-items) · L203–215 — what is not verified.
- [Source index](#source-index) · L217–219 — resolving a source key.

Floor values: [formats.md](formats.md#contrast-floors); check a theme with `SKILL_DIR/scripts/contrast_check.py`.

Tags: `[Sn]`/`[UR]` = [source index](#source-index) at the bottom; `derived:` own inference/computation (numbers re-run 2026-10-01 with `SKILL_DIR/scripts/_theme.py`); `UNVERIFIED` not confirmed from a primary source.

---

## A1. Contrast: WCAG formula, our floors, and what the terminal changes

**Formula** (WCAG 2.2 [S39]; footnote: before May 2021 the constant was 0.03928, "no practical effect"):

```text
L  = 0.2126*R + 0.7152*G + 0.0722*B            channel c = c8/255; C = c/12.92 if c <= 0.04045 else ((c+0.055)/1.055)^2.4
ratio = (L1 + 0.05) / (L2 + 0.05)              L1 lighter, L2 darker; range 1:1 .. 21:1
```

```python
def lum(rgb):  r,g,b = (srgb_to_lin(c) for c in rgb); return 0.2126*r + 0.7152*g + 0.0722*b
def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True); return (la+0.05)/(lb+0.05)   # white/black = 21.0
```

**Success criteria and the terminal reading** (`derived:` column):

| SC | Level | Requirement | In a terminal |
|---|---|---|---|
| 1.4.3 Contrast (Minimum) | AA | text >= **4.5:1**; large text (>= 18 pt, or 14 pt bold) >= 3:1; inactive components, decoration, logotypes exempt | cell text is user-sized: treat **all text as normal (4.5:1)** |
| 1.4.6 Contrast (Enhanced) | AAA | **7:1** (large 4.5:1) | target for a `high-contrast` theme and for `fg.default` |
| 1.4.11 Non-text Contrast | AA | UI components, states, graphical objects >= **3:1** against adjacent colors | borders you rely on, focus markers, bar fill vs track, sparkline ink, scrollbar thumb vs track, selected row vs normal row |
| 1.4.1 Use of Color | A | color is not "the only visual means of conveying information, indicating an action, prompting a response, or distinguishing a visual element" | status = glyph/word + color; selection = marker + color |
| 2.4.7 Focus Visible | AA | keyboard focus indicator is visible | focused row/field has a non-color cue (marker `❯`, inverse, bold) |
| 2.2.2 Pause, Stop, Hide | A | auto-starting moving/blinking/auto-updating content lasting > **5 s** needs pause/stop/hide | spinners, tickers, SGR 5 blink: provide `--no-animation`/reduced motion; do not use blink |
| 2.3.3 Animation from Interactions | AAA | motion triggered by interaction can be disabled | animated scroll/transitions need an off switch |

**APCA** (`Myndex/SAPC-APCA`, "Lc"): polarity-aware, proposed for WCAG 3; the README fetched describes APCA-W3 0.0.98G-4g and does not state it is normative [S39b]. WCAG 3 is a draft, so cite WCAG 2.2 ratios; use APCA only as an advisory second opinion for thin text on dark backgrounds. Lc tier thresholds: `UNVERIFIED` in this research.

### Our floors

The values (ratio vs `bg.base` unless noted) live in one place: [formats.md](formats.md#contrast-floors), checked by `SKILL_DIR/scripts/contrast_check.py` at truecolor and with `--depth 16`. Rationale, so you can judge an exception:

- **Text pairs** (`fg.default`, `fg.muted`, `status.*`, `accent.primary`, `keyhint.key`, `link`, `selection.fg` on `selection.bg`, `fg.on-accent` chips): 4.5, WCAG 1.4.3; `fg.default` prefers 7 (1.4.6). Secondary text is still text.
- **`fg.faint` (3.0)** is a deliberate relaxation for the "inactive/decorative" role only (disabled items, placeholders, guides, separators, line numbers). **Never put information needed to operate the app in `fg.faint`** (`derived:`).
- **`border.focus` (3.0)**: 1.4.11 focus indicator.
- **Not in the floors**: `border.default`, `selection.bg` vs `bg.base`, `scrollbar.thumb` vs track: advisory 3.0 **only if it is the sole indicator** (1.4.11); otherwise a second cue must exist.

Policy: report failures; fix only when the official palette has a compliant alternative with the same role, otherwise keep the official mapping and add a note in the theme JSON. Run:

```bash
python3 SKILL_DIR/scripts/contrast_check.py catppuccin-mocha            # truecolor floors
python3 SKILL_DIR/scripts/contrast_check.py --all --depth 16            # re-check the hand-authored 16-color mapping
```

### What the terminal changes (computed, `derived:`)

1. **You do not own the background.** GitHub CLI team: "A terminal's background color is not set by the application. That task is handled by the user's terminal emulator", so they limited themselves to the 4-bit ANSI palette and let users re-theme [S40]. Inherit default fg/bg for body text; use indexed 0-15 only for semantic accents; **whenever you set fg or bg with RGB, set both**.
2. **Default xterm 16 colors fail often** (ratio):

   | Color (xterm default) | on `#000000` | on `#FFFFFF` | on `#1E1E2E` |
   |---|---|---|---|
   | 1 red `CD0000` | 3.60 | 5.84 | 2.81 |
   | 2 green `00CD00` | 9.73 | **2.16** | 7.60 |
   | 3 yellow `CDCD00` | 12.33 | **1.70** | 9.63 |
   | 4 blue `0000EE` | **2.23** | 9.40 | **1.75** |
   | 5 magenta `CD00CD` | 4.48 | 4.69 | 3.50 |
   | 6 cyan `00CDCD` | 10.61 | **1.98** | 8.29 |
   | 7 white `E5E5E5` | 16.67 | **1.26** | 13.02 |
   | 8 bright black `7F7F7F` | 5.24 | 4.00 | 4.10 |
   | 9 bright red `FF0000` | 5.25 | 4.00 | 4.10 |
   | 12 bright blue `5C5CFF` | 4.43 | 4.74 | 3.46 |

   Dark blue on black, and yellow/cyan/green/white on white, are the classic failures. **Bright black as "muted text" is theme roulette**: in the Solarized Dark Xresources `*color8: S_base03` is **identical to `*background: S_base03`** (invisible text) [S47], and Solarized's comment color `base01 #586E75` on `base03 #002B36` is 2.79:1. Never use ANSI 8/90 as muted text without a per-theme override (`ansi16` in the theme JSON); use SGR 2 or an explicit checked color.
3. **Dim/faint (SGR 2) lowers contrast by construction.** Terminals blend toward the background; Ghostty exposes `faint-opacity` (1.2.0+) [S6]. The skill models dim as `blend(fg, bg, 0.55)` ([formats.md](formats.md#contrast-floors)), but real terminals differ. Default fg `#DDD` over black: 50 % = **4.12:1 (fails 4.5)**, 0.55 = 4.89, 60 % = 5.69, 66 % = 6.75, 70 % = 7.56; black on white: 50 % = 3.95, 0.55 = 4.74. The default 16-color mapping for `fg.muted` is `default dim` (`themes/_tokens.json`): treat dim as a tertiary style, test it in the worst-case terminal, or replace it with an explicit color.
4. **Bold-as-bright** shifts colors 0-7 to 8-15 on xterm and Windows Terminal (default `intenseTextStyle: bright`): check both outcomes ([terminal-capabilities.md](terminal-capabilities.md) D4).
5. **Selection / cursor row.** Inverse video (SGR 7) guarantees the original fg/bg ratio. A "tinted background" selection usually fails 1.4.11: `#2A2A3A` on `#1E1E2E` is **1.16:1**; Catppuccin Mocha `selection.bg #3b3d4f` is 1.54:1, `#45475a` 1.80:1, `#585b70` 2.46:1; none reach 3:1. So selection always carries a marker glyph and bold or inverse (the Fleet demo: `❯` + bold + `selection.bg`).
6. **After downsampling** (256/16), re-run the check on the quantized pair; quantization can break a passing pair ([terminal-capabilities.md](terminal-capabilities.md) D3).

---

## A2. Color-vision deficiency (CVD)

**Rule**: never color alone (WCAG 1.4.1). Use warm-vs-cool pairs with a luminance difference **and** a glyph. Okabe and Ito: "Use not only different colors but also a combination of different shapes, positions, line types and coloring patterns"; "avoid the combination of colors that have the same brightness but differ only in hue" [S39c].

**Their barrier-free palette** (rationale quoted from the page: vermilion because "recognizable also to protanopes", bluish green so it "won't be confused with red or brown", reddish purple because violet looks like blue, avoid yellow-green): black, orange, sky blue, bluish green, yellow, blue, vermilion, reddish purple. 8-bit values widely published from Wong 2011: `E69F00 56B4E9 009E73 F0E442 0072B2 D55E00 CC79A7` (`UNVERIFIED` hex source; the page itself quotes vermilion #FF2000 and light red #FF1414) [S39c].

**Simulation** (`derived:`; Machado et al. 2009 severity-1.0 matrices in linear RGB, white-preservation sanity-checked; delta-E 2000 between the pair under each type, 0 = identical):

| Pair | normal | protan | deutan | tritan | luminance contrast |
|---|---|---|---|---|---|
| xterm red `CD0000` / green `00CD00` (the default "bad/good") | 80.3 | 42.9 | **19.6** | 69.8 | 2.71 |
| bright red / bright green | 86.6 | 42.4 | 19.5 | 75.6 | - |
| xterm yellow `CDCD00` / green `00CD00` | 22.1 | **3.2** | 8.3 | 35.2 | - |
| xterm magenta / bright blue `5C5CFF` | 20.8 | 9.2 | **7.2** | 58.6 | - |
| Okabe-Ito vermilion `D55E00` / bluish green `009E73` | 54.4 | 18.2 | 20.5 | 62.7 | **1.13** |
| **Okabe-Ito vermilion / sky blue `56B4E9`** | 52.3 | 52.2 | 52.8 | 62.7 | 1.68 |
| **Okabe-Ito orange `E69F00` / blue `0072B2`** | 55.3 | 55.5 | 62.6 | 51.4 | 2.30 |
| **yellow `F0E442` / blue `0072B2`** | 70.4 | 63.1 | 67.8 | 47.2 | 3.92 |

Reading: the classic green/red pair collapses for deuteranopes, and even the Okabe-Ito red/green pair is weak because their **luminance is equal (1.13:1)**: the **Okabe-Ito red/green luminance trap**. Prefer warm-vs-cool (orange/blue, vermilion/sky blue) plus a luminance step plus a glyph.

**Okabe-Ito colors as text** (`derived:`): on black orange 9.32, sky blue 9.10, bluish green 6.14, yellow 15.88, blue **4.05**, vermilion 5.43, reddish purple 6.86; on white blue 5.19 but orange **2.25**, sky blue **2.31**, yellow **1.32**, bluish green 3.42, vermilion 3.87, reddish purple 3.06. One hex set cannot serve both backgrounds: ship **two palettes** (dark and light); see `color-schemes.md`.

**The channel rule**: each semantic state = {glyph, word, color, position}; remove any one channel and the other three still carry it.

| State | Glyph | Word | Color token | Position/shape |
|---|---|---|---|---|
| success | `✓` | `passed` | `status.success` | leftmost status column |
| failure | `✗` | `failed` | `status.error` | same column; bold row text |
| warning | `▲` | `degraded` | `status.warning` | same column |
| selected | `❯` | (row text bold) | `accent.primary` + `selection.bg` | marker column, inverse/bold |
| gauge high | `█`... + number | `92%` | `ramp.high` | bar length + trailing number |

Test it: render the UI in greyscale and with `NO_COLOR=1` (`python3 SKILL_DIR/scripts/render_mockup.py FILE.mock --depth none`); every state must still be distinguishable. Apps doing this: GitHub CLI `accessible_colors` (4-bit ANSI palette "designed for better contrast") [S43]; Claude Code `dark-daltonized` / `light-daltonized` themes via `theme` or `/theme` [S42]; btop's too-small screen uses red/green numbers **and** words ("Needed for current config") [S31].

---

## A3. Screen readers and TUIs: the realistic state

**Reality check** (primary sources and individual user reports, not studies):

- There is no accessibility tree for terminal apps; the screen reader sees the terminal's text grid and the **cursor**. Speakup "prioritizes the cursor's location update over the character echo ... you hear 'Column 2'" instead of the typed letter. Full-screen frameworks that move the hardware cursor to paint timers and spinners make "the cursor ... teleporting all over the screen"; with NVDA/Speakup "you end up hearing random bits of conversation mixed with timer updates" (blind developer essay "The text mode lie", 2026-01-05; names Ink, Bubble Tea and tcell as offenders; praises irssi for VT100 scrolling regions and nano/vim for letting the cursor be pinned or hidden) [UR].
- NVDA user report on an agent TUI (2026): "Every repaint of a terminal line is an update event for the screen reader, which re-homes the review cursor at the newest output"; the alt screen has no scrollback so earlier turns cannot be re-read; approval prompts that change while navigating are unsafe; requests an opt-in static plain-text mode "modelled on the equivalent mode in Claude Code" [UR].
- VoiceOver on macOS user report: the reader "keeps repeating 'box drawing light horizontal' bunch of times before and after prompt field"; braille spinners are "supposed to be used for Braille display"; wants a flatter mode and `User:`/`Assistant:` role labels [UR].
- GitHub CLI team (2025-05, `gh a11y` public preview, gh 2.72): "non-alphanumeric visual cues and constant screen redraws" are hard for speech synthesis; the old braille spinner redrew the screen and "Speech synthesis screen readers do not handle this well", so it became static text (`Working...` fallback); prompts rebuilt on `charmbracelet/huh` [S40].

| What | Works | Breaks |
|---|---|---|
| Linear, append-only text with labels | yes (reader reads new lines in order) | |
| Box-drawing chrome | | read aloud as "box drawing light horizontal" [UR] |
| Braille/emoji spinners and per-frame redraw | | each repaint is an update event; braille announced cell by cell [S40][UR] |
| Alt screen (1049) | | no scrollback to re-read [UR][S42] |
| Cursor used as paintbrush | | cursor teleports, reader reads random fragments [UR] |
| Arrow-key menus and mouse-driven UI | | readers use the mouse for review; menus invisible to speech [S43] |
| Input prompts that change while awaiting an answer | | unsafe approvals [UR] |

### The best-documented models (copy their structure)

- **Claude Code screen-reader mode** [S42]: opt-in via `--ax-screen-reader`, env `CLAUDE_AX_SCREEN_READER=1`, or setting `axScreenReader: true` (precedence flag > env > setting; env `0` forces off); first line confirms `[Screen Reader Mode: on via flag|env|settings]`; **no box-drawing chrome, no color-only cues, no redraw of unchanged content, spinners as static text, tables as `Header: value` sentences**; everything stays in scrollback (no fullscreen/alt screen); waits 3 s after the confirmation line before drawing the prompt (`CLAUDE_AX_STARTUP_QUIET_MS`) and, before writing a new or changed line, moves the cursor to line start and waits **50 ms** (`CLAUDE_AX_PREPARK_MS`) so the reader starts at character 1; the cursor stays on the input caret; typing writes only changed characters; deleted words/lines are announced; permission-mode changes announced once; messages carry searchable labels `you: claude: thinking: tool: tool error: error: warning: Permission Required: Cost:`; OSC 133 markers at turn boundaries (iTerm2 Cmd+Shift+Up; VS Code Ctrl/Cmd+Up; Windows Terminal `scrollToMark`; macOS Terminal ignores them); menus become numbered lists (`Select with numbers`); yes/no prompts are typed `y`/`n`; terminal bell when a reply finishes, a prompt needs an answer, or a > 5 s tool completes. Limits: it does not auto-enable when a screen reader is detected; alt-screen attach views still lack scrollback. Related: `CLAUDE_CODE_ACCESSIBILITY=1` keeps the terminal cursor visible and moves it to the highlighted row in menus (for magnifier users); setting `prefersReducedMotion` reduces spinners/shimmer.
- **GitHub CLI** [S43]: `gh config set accessible_prompter enabled` (numbered lists instead of arrow-key menus), `accessible_colors enabled` (4-bit ANSI palette), `spinner disabled` (text progress).
- **Copilot CLI** [S43]: `--screen-reader`, settings `"screenReader": true`, `"stream": false` (complete blocks instead of token streaming), `"mouse": false`. Windows Terminal mark mode (`Ctrl+Shift+M`) lets a user read output line by line.
- **huh** [S44]: `form.WithAccessible(true)` ("Accessible forms will drop TUIs in favor of standard prompts"; README recommends `os.Getenv("ACCESSIBLE") != ""`); `Spinner.WithAccessible` is static.
- **Frameworks**: no mainstream TUI framework (Ratatui, Bubble Tea, Ink, Textual) is documented as screen-reader accessible; huh is the exception. Textual's accessibility was a 2023 roadmap item (LWN, secondary), current state `UNVERIFIED`; `textual serve` runs a TUI in a browser as a workaround (secondary reports).

---

## A4. Recommended affordances (checklist for design and audit)

Each item: rule, example, source/basis.

| # | Affordance | Example | Basis |
|---|---|---|---|
| 1 | **A linear mode exists and is reachable without the TUI**: `--plain`, `--no-tui`/`--screen-reader`, `--json`; env var `MYAPP_SCREEN_READER`; config key; honor the user's explicit choice. There is **no universal non-interactive flag**: `--no-input` (clig.dev) is one spelling among many; the cross-tool convention is to skip prompts when stdin or stdout is not a TTY and when the needed value arrives by flag or env var (`GH_TOKEN`) | `myapp --plain` prints "plain, tabular text format"; `--json` for machines; no prompts when stdin is not a TTY | clig.dev [S37]; huh README [S44] |
| 2 | **Respect NO_COLOR** (and `TERM=dumb`, non-TTY; precedence rules live only in D1): drop color, **keep** bold/underline/inverse and glyph/word cues | selection stays inverse + `❯`; `● running` text intact | [S38]; precedence in [terminal-capabilities.md](terminal-capabilities.md) D1 |
| 3 | **No information in color alone** (A2 channel rule) | `✗ failed`, not a red dot | WCAG 1.4.1 |
| 4 | **Never animate by redrawing**: no rewriting spinners/progress in linear mode; emit periodic *new* lines ("Still working: 40 %") at a low rate or only at start/finish | `Working...` static line | [S40][S42] |
| 5 | **Reduced motion**: there is no cross-tool env standard (searched: no `NO_ANIMATION`/`REDUCE_MOTION` convention). Chain (`derived:`): `--no-animation` > `MYAPP_REDUCE_MOTION`/`MYAPP_NO_ANIMATION` > config key > auto-off when not a TTY, `TERM=dumb`, `CI` set, or screen-reader mode. OS probes (`defaults read com.apple.universalaccess reduceMotion`, `gsettings get org.gnome.desktop.interface enable-animations`) are plausible but `UNVERIFIED` | Claude Code `prefersReducedMotion`; gh `spinner disabled` | [S42][S43] |
| 6 | **Cursor discipline**: keep the real cursor on the logical focus (input caret, selected row); do not use it as a paintbrush; write only changed cells; batch updates with synchronized output 2026 | hide the cursor only if focus is announced another way | [UR][S42] |
| 7 | **Keep scrollback in linear mode**: no alt screen; history stays re-readable | `1049h` only in the full TUI | [S42][UR] |
| 8 | **Text over decoration** in linear mode: no box-drawing chrome, no braille spinners, no emoji-only status; role labels `error:`, `warning:`, `tool:`; tables as `Header: value` | `error: could not save config` | [S42][UR] |
| 9 | **Prompts as numbered lists or typed y/n**; announce valid ranges; Escape cancels | `Select with numbers [1-4]:` | [S42][S43] |
| 10 | **Audible attention cue**: BEL on completion or when input is needed; optional OSC 9/777/99 notification | bell when a >5 s task finishes | [S42] |
| 11 | **Orientation aids**: OSC 133 prompt marks, searchable labels; window title (OSC 2) stating state/mode (the title idea is `derived:`, effect on readers `UNVERIFIED`) | | [S42] |
| 12 | **No time-outs on input**; no content changing while a prompt awaits an answer | approval text frozen until answered | [UR] |
| 13 | **Mouse off in linear mode** (readers use mouse events for review) | no `1000/1006` | [S43] |
| 14 | **Keyboard-only**: every action reachable by key; visible focus (marker + inverse); discoverable key hints in the footer | `? help  q quit` footer (Fleet) | WCAG 2.1.1/2.4.7 |
| 15 | **High-contrast and CVD themes**: `--theme high-contrast` (text >= 7:1, borders/focus >= 4.5:1, bold selection, no color-only cues) and a CVD-safe theme (A2); a 16-color ANSI-only theme so the user's own (possibly high-contrast) terminal palette decides | Claude Code daltonized themes | [S40][S42][S43] |
| 16 | **Announce state changes via text**: permission/mode/filter changes print one line; errors persist until acknowledged (do not auto-clear a toast that carries the only error text) | `mode: plan (changed)` | `derived:` from [S42] |
| 17 | **Ctrl-C exits promptly**; do not trap it without a visible way out | | [S37] |
| 18 | **Do not auto-detect screen readers**: no standard env var exists (Claude Code lists "does not auto-enable" as a limitation); expose the switch instead of guessing | | [S42] |
| 19 | Magnifier users: keep the cursor visible and parked on focus (`CLAUDE_CODE_ACCESSIBILITY=1` model) | | [S42] |
| 20 | Braille displays mirror cell text, so frequent rewrites thrash them (`derived:`; no primary source fetched) | | |

**clig.dev rules a TUI must still honor** (verbatim, [S37]): disable color when "stdout or stderr is not an interactive terminal (a TTY)", when "The `NO_COLOR` environment variable is set and it is not empty (regardless of its value)", when "The `TERM` environment variable has the value `dumb`", when "The user passes the option `--no-color`"; "If stdout is not an interactive terminal, don't display any animations. This will stop progress bars turning into Christmas trees in CI log output."; "If human-readable output breaks machine-readable output, use `--plain`"; "Display output as formatted JSON if `--json` is passed."; "Only use prompts or interactive elements if stdin is an interactive terminal (a TTY)"; "If `--no-input` is passed, don't prompt or do anything interactive."; "If a user hits Ctrl-C (the INT signal), exit as soon as possible."; "hiding logs behind progress bars when things go well ... but if there is an error, make sure you print out the logs." clig.dev also says "Use symbols and emoji where it makes things clearer": that is advice for line-oriented CLI output; in column-aligned TUIs the width hazards in [visual-vocabulary.md](visual-vocabulary.md) V1 outweigh it.

**NO_COLOR vs FORCE_COLOR**: the precedence order and the library conflict (colorprofile vs force-color.org) are documented once, in [terminal-capabilities.md](terminal-capabilities.md) D1; do not restate them in a design system, link to it.

---

## A5. Audit protocol hooks (what to run, what to look for)

| Check | How | Pass |
|---|---|---|
| Contrast floors | `python3 SKILL_DIR/scripts/contrast_check.py ID` and `--depth 16` | exit 0; failures listed with the token pair |
| Greyscale / `NO_COLOR` legibility | `SKILL_DIR/scripts/render_mockup.py F.mock --depth none`; run the real app with `NO_COLOR=1` | every status and the selection still distinguishable |
| Glyph safety | `SKILL_DIR/scripts/render_mockup.py F.mock --check` (and `--strict-ambiguous` to promote ambiguous-width chrome glyphs from INFO to ERROR for aligned layouts) | no ERROR; WARNs justified |
| Dim text | find `dim`/SGR 2 on information-bearing text; blend with `blend(fg, bg, 0.55)` over `bg.base` (and re-check at 50 % as the worst case) | >= 4.5:1 or it is decoration |
| Animation | search for spinners/tickers/blink; check `--no-animation`, non-TTY and `CI` behavior | static text under each |
| Linear mode | run `--plain`/`--screen-reader`, pipe to `cat`, check labels and absence of box drawing/alt screen | readable top to bottom |
| Keyboard | every action has a key; focus visible without color | |
| Too-small | resize to 60x18 and 40x10 (a `toosmall` mockup frame sits one size below the minimum, [formats.md](formats.md#frame-naming)) | message with current/needed size in words ([layout-archetypes.md §2.2](layout-archetypes.md#22-the-too-small-screen)) |

---

## A6. Gaps and unverified items

| Item | Status |
|---|---|
| Reduced-motion OS probes | plausible, not verified, may need permissions |
| Windows high-contrast / macOS "Increase contrast" | not observable from inside a terminal (`UNVERIFIED`) |
| APCA Lc thresholds | page excerpt lacked them |
| Textual current screen-reader support | only a 2023 roadmap mention (LWN, secondary) |
| Screen-reader behavior on OSC 2 title changes; braille-display thrash | no primary source |
| Okabe-Ito 8-bit hex | commonly published (Wong 2011), not re-verified on the source page |
| Screen-reader user reports [UR] | individual reports, not studies |

---

## Source index

**S6** Ghostty https://ghostty.org/docs/config/reference ; **S31** btop https://github.com/aristocratos/btop ; **S37** CLI Guidelines https://clig.dev/ ; **S38** https://no-color.org/ , https://force-color.org/ , https://bixense.com/clicolors/ ; **S39** WCAG 2.2 https://www.w3.org/TR/WCAG22/ ; **S39b** APCA https://github.com/Myndex/SAPC-APCA ; **S39c** Okabe-Ito / Jfly "Color Universal Design" https://jfly.uni-koeln.de/color/ ; **S40** GitHub Blog, "Building a more accessible GitHub CLI" (2025-05-02) https://github.blog/engineering/user-experience/building-a-more-accessible-github-cli/ , changelog https://github.blog/changelog/2025-05-01-improved-accessibility-features-in-github-cli/ ; **S42** Claude Code, "Use Claude Code with a screen reader" https://code.claude.com/docs/en/accessibility ; **S43** GitHub Accessibility, "Using Git, GitHub CLI, and Copilot CLI with a Screen Reader" https://accessibility.github.com/documentation/guide/cli/ ; **S44** huh https://github.com/charmbracelet/huh ; **S47** Solarized Xresources https://github.com/solarized/xresources (`Xresources.dark`) ; **UR** screen-reader user reports on agent TUIs (NVDA, VoiceOver; 2026), individual reports, not studies. Computation: `SKILL_DIR/scripts/_theme.py` (`contrast_ratio`, `blend`); CVD simulation as in A2.
