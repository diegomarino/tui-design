# Glyph data appendix: charts, width data, braille math, spinner provenance, Nerd Font ranges

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [G1. Box Drawing chart (U+2500-257F, 128 code points, 16 per row)](#g1-box-drawing-chart-u2500-257f-128-code-points-16-per-row) · L14–29 — finding a box-drawing code point (joins, heavy, double, rounded).
- [G2. Width data](#g2-width-data) · L31–51 — deciding whether a code point is wide, ambiguous or zero-width.
- [G3. Braille bit math and btop's graph mapping](#g3-braille-bit-math-and-btops-graph-mapping) · L53–81 — drawing braille graphs: dot bits and btop's value-to-dot mapping.
- [G4. Spinner provenance and exact frames](#g4-spinner-provenance-and-exact-frames) · L83–125 — copying a spinner's exact frames and interval, and where it comes from.
- [G5. Nerd Fonts: ranges and per-app strategy](#g5-nerd-fonts-ranges-and-per-app-strategy) · L127–159 — Nerd Font code-point ranges and how apps gate icons behind a setting.

Data only; the rules are in [visual-vocabulary.md](visual-vocabulary.md), whose [source index](visual-vocabulary.md#source-index) resolves the `[Sn]` tags. `derived:` = own computation from the Unicode files (EastAsianWidth 18.0.0); `UNVERIFIED` = not confirmed.

---

## G1. Box Drawing chart (U+2500-257F, 128 code points, 16 per row)

```text
U+2500: ─ ━ │ ┃ ┄ ┅ ┆ ┇ ┈ ┉ ┊ ┋ ┌ ┍ ┎ ┏
U+2510: ┐ ┑ ┒ ┓ └ ┕ ┖ ┗ ┘ ┙ ┚ ┛ ├ ┝ ┞ ┟
U+2520: ┠ ┡ ┢ ┣ ┤ ┥ ┦ ┧ ┨ ┩ ┪ ┫ ┬ ┭ ┮ ┯
U+2530: ┰ ┱ ┲ ┳ ┴ ┵ ┶ ┷ ┸ ┹ ┺ ┻ ┼ ┽ ┾ ┿
U+2540: ╀ ╁ ╂ ╃ ╄ ╅ ╆ ╇ ╈ ╉ ╊ ╋ ╌ ╍ ╎ ╏
U+2550: ═ ║ ╒ ╓ ╔ ╕ ╖ ╗ ╘ ╙ ╚ ╛ ╜ ╝ ╞ ╟
U+2560: ╠ ╡ ╢ ╣ ╤ ╥ ╦ ╧ ╨ ╩ ╪ ╫ ╬ ╭ ╮ ╯
U+2570: ╰ ╱ ╲ ╳ ╴ ╵ ╶ ╷ ╸ ╹ ╺ ╻ ╼ ╽ ╾ ╿
```

Width classes: [visual-vocabulary.md](visual-vocabulary.md) V1 (all EAW **A** except the N dashes U+254C-254F and half-lines U+2574-257F).

---

## G2. Width data

**BMP symbols with EAW=W** (regenerate, do not hard-code; 76 code points in U+2000-2BFF, 36 runs): U+231A-231B, 2329-232A, 23E9-23EC, 23F0, 23F3, 25FD-25FE, 2614-2615, **2630-2637**, 2648-2653, 267F, 268A-268F, 2693, 26A1, 26AA-26AB, 26BD-26BE, 26C4-26C5, 26CE, 26D4, 26EA, 26F2-26F3, 26F5, 26FA, 26FD, 2705, 270A-270B, 2728, 274C, 274E, 2753-2755, 2757, 2795-2797, 27B0, 27BF, 2B1B-2B1C, 2B50, 2B55; plus U+3000, U+FF01-FF60, U+FFE0-FFE6 and 47 runs (1195 code points) in U+1F000-1FAFF.

**Generating width tables** at build time from `EastAsianWidth.txt` + `emoji-data.txt` (Unicode revises yearly [S20]):

```python
def parse(fn):                       # lines look like "XXXX..YYYY ; W  # comment"
    for l in open(fn, encoding="utf8"):
        l = l.split("#")[0].strip()
        if not l: continue
        a, b = (x.strip() for x in l.split(";")[:2])
        lo, _, hi = a.partition("..")
        yield int(lo, 16), int(hi or lo, 16), b.split()[0]
```

Width function for layout (`derived:`): `cells(g) = 2 if EAW in {W,F} or Emoji_Presentation; 0 for Mn/Me/Cf; else 1`. An application test can evaluate it with A=1 and A=2 and fail when a line's width differs.

**UTF-8 gate**: treat the terminal as Unicode-capable unless `TERM=linux` (kernel console) or the locale is not UTF-8; on Windows the `is-unicode-supported` whitelist is `WT_SESSION`, `TERM_PROGRAM=vscode`, `TERM=xterm-256color|alacritty|rxvt-unicode*`, ConEmu/Cmder, JetBrains JediTerm; `ora` then falls back to its ASCII `line` spinner [S35].

---

## G3. Braille bit math and btop's graph mapping

Braille is U+2800-28FF (256 code points, all EAW N): `code point = 0x2800 + mask`; 2x4 dot grid, bits (drawille `pixel_map` [S36]):

```text
 col0  col1
 0x01  0x08   row 0
 0x02  0x10   row 1
 0x04  0x20   row 2
 0x40  0x80   row 3
```

```python
PIXEL = ((0x01,0x08),(0x02,0x10),(0x04,0x20),(0x40,0x80))
def cell(px):   # px[y][x] in {0,1}, 4 rows x 2 cols
    return chr(0x2800 + sum(PIXEL[y][x] for y in range(4) for x in range(2) if px[y][x]))
```

**btop's line/area mapping** (`braille_up`, `derived:` verified against `btop_draw.cpp` [S31]): each cell holds two columns with 4 fill levels each; bottom-up fill bits per column are left `[0x40, 0x04, 0x02, 0x01]`, right `[0x80, 0x20, 0x10, 0x08]`; level 0/0 is a plain space; cell index = `5*left_level + right_level` (0-4 each). `braille_down` fills from the top. The 25 glyphs, in index order:

```text
 ⢀ ⢠ ⢰ ⢸ ⡀ ⣀ ⣠ ⣰ ⣸ ⡄ ⣄ ⣤ ⣴ ⣼ ⡆ ⣆ ⣦ ⣶ ⣾ ⡇ ⣇ ⣧ ⣷ ⣿
```

Sample (16 values scaled 0-4 -> 8 cells): `⢀⣠⣾⣷⣤⣰⣿⣄`.

btop's graph degradation ladder: `braille` -> `block` (quadrants `▗▐▖▄▟▌▙█▘▝▀▜▛`) -> `tty` (shades ` ░▒█`, forced in `tty_mode`) [S31].

---

## G4. Spinner provenance and exact frames

Source of truth: `sindresorhus/cli-spinners` `spinners.json` (**90** spinners, fetched 2026-10-01) [S32]. Width = max cells of one frame (A=1 / A=2). Recommended subset, its frames and the rules: `visual-vocabulary.md` V6.

| Name | ms | Frames | Non-ASCII code points | Width | Verdict | Rich | Bubbles |
|---|---|---|---|---|---|---|---|
| `dots` | 80 | 10 | U+2807 280B 280F 2819 2826 2827 2834 2838 2839 283C | 1/1 | safe | yes | MiniDot (12 fps = 83 ms) |
| `dots2` | 80 | 8 | U+287F 28BF 28DF 28EF 28F7 28FB 28FD 28FE | 1/1 | safe | yes | Dot (+ trailing space, 10 fps) |
| `dots3` | 80 | 10 | U+280B 2813 2816 2819 281A 281E 2826 2832 2833 2834 | 1/1 | safe | yes | |
| `dots12` | 80 | 56 | 28 braille code points (incl. blank U+2800) | 2/2 | safe | yes | |
| `line` | 130 | 4 | ASCII | 1/1 | safe | yes | Line (`\| / - \`, 10 fps) |
| `line2` | 100 | 6 | U+2013 2014 2802 | 1/2 | AMBIG | yes | |
| `pipe` | 100 | 8 | U+250C 2510 2514 2518 251C 2524 252C 2534 | 1/2 | AMBIG | yes | |
| `simpleDots` | 400 | 4 | ASCII | 3/3 | safe | yes | |
| `star` | 70 | 6 | U+2736 2737 2738 2739 273A | 1/1 | safe | yes | |
| `growVertical` | 120 | 10 | U+2581 2583-2587 | 1/2 | AMBIG | yes | |
| `growHorizontal` | 120 | 12 | U+2589-258F | 1/2 | AMBIG | yes | |
| `arc` | 100 | 6 | U+25DC-25E1 | 1/1 | safe | yes | |
| `circle` | 120 | 3 | U+2299 25E0 25E1 | 1/2 | AMBIG | yes | |
| `bouncingBar` | 80 | 16 | ASCII | 6/6 | safe | yes | |
| `bouncingBall` | 80 | 10 | U+25CF | 8/9 | AMBIG | yes | |
| `moon` | 80 | 8 | U+1F311-1F318 | 3/3 | **WIDE** | yes | Moon (8 fps) |
| `arrow3` | 120 | 6 | U+25B8 25B9 | 5/5 | safe | yes | |
| `point` | 125 | 5 | U+2219 25CF | 3/4 | AMBIG | yes | Points (7 fps) |
| `aesthetic` | 80 | 8 | U+25B0 25B1 | 7/7 | safe | yes | Meter (own variant) |

Frames of the non-recommended sets cited above (exact):

```text
point       125  ∙∙∙ ●∙∙ ∙●∙ ∙∙● ∙∙∙
bouncingBar  80  [    ] [=   ] [==  ] [=== ] [====] [ ===] [  ==] [   =] [    ] [   =] ...
```

Who ships what:

- **cli-spinners** -> `ora` (default `dots`; `line` when `!isUnicodeSupported()`), `ink-spinner` (`derived:` uses cli-spinners), listr2 (`UNVERIFIED`) [S32][S35].
- **Rich** ships **73 of the 90** names verbatim (`python -m rich.spinner`); missing e.g. `dots13`, `dots14`, `dotsCircle`, `sand`, `rollingLine`, `binary`, the emoji "fingerDance..." family, `fish`; Textual builds on Rich [S19][S32].
- **Bubbles** (Go) ships 12 of its own: `Line` `| / - \` 10 fps; `Dot` `⣾⣽⣻⢿⡿⣟⣯⣷` (+ trailing space) 10 fps; `MiniDot` `⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏` 12 fps; `Jump` `⢄⢂⢁⡁⡈⡐⡠` 10 fps; `Pulse` `█▓▒░` 8 fps; `Points` `∙∙∙ ●∙∙ ∙●∙ ∙∙●` 7 fps; `Globe` `🌍🌎🌏` 4 fps; `Moon` 8 fps; `Monkey` `🙈🙉🙊` 3 fps; `Meter` `▱▱▱ ▰▱▱ ▰▰▱ ▰▰▰ ▰▰▱ ▰▱▱ ▱▱▱` 7 fps; `Hamburger` `☱☲☴☲` 3 fps; `Ellipsis` `"" . .. ...` 3 fps [S33].
- **indicatif** (Rust): default tick `⠁⠁⠉⠙⠚⠒⠂⠂⠒⠲⠴⠤⠄⠄⠤⠠⠠⠤⠦⠖⠒⠐⠐⠒⠓⠋⠉⠈⠈ ` (29 braille frames + 1 trailing space) and progress chars `█░` [S34].
- **lazygit**: `gui.spinner.frames: [●∙∙, ∙●∙, ∙∙●, ∙●∙]`, `rate: 180` ms [S26]; `●` is A so the spinner jumps from 3 to 4 cells in ambiguous-wide mode (use `◉` to avoid).
- **GitHub CLI** replaced the braille spinner with static `Working…` in accessible mode (and `gh config set spinner disabled`) [S40][S43]; **huh** `Spinner.WithAccessible(true)` is static [S44]; **Claude Code** shows static text in screen-reader mode and honors `prefersReducedMotion` [S42].

---

## G5. Nerd Fonts: ranges and per-app strategy

Current release **v3.5.1** (2026-08-21) [S25]. Icons sit in the PUA, including Plane 15 (EAW **A**, no defined width): kitty treats PUA as 1 cell and gives 2 only when followed by a space/en-space (override `narrow_symbols`; text sizing protocol `OSC 66` since 0.40 removes the guesswork) [S4]. Nerd Fonts ships three variants per family: monospaced (Mono), double-width, proportional [S25].

| Set | Range |
|---|---|
| IEC Power Symbols | U+23FB-23FE, U+2B58 |
| Box Drawing (patched copy) | U+2500-259F |
| Powerline Extra (hamburger) | **U+2630** (also EAW=W in Unicode) |
| Octicons | U+2665, **U+26A1** (EAW=W), U+F400-F533 |
| Heavy Angle Brackets | U+276C-2771 |
| Braille | U+2800-28FF |
| Pomicons | U+E000-E00A |
| Powerline | U+E0A0-E0A2, U+E0B0-E0B3 |
| Powerline Extra | U+E0A3, U+E0B4-E0C8, U+E0CA, U+E0CC-E0D7 |
| Font Awesome Extension | U+E200-E2A9 |
| Weather Icons | U+E300-E3E3 |
| Seti-UI + Custom | U+E5FA-E6BB |
| Devicons | U+E700-E958 |
| Codicons | U+EA60-EC84 |
| Font Awesome | U+ED00-EFCE, U+F000-F2FF |
| Progress | U+EE00-EE0B |
| Font Logos | U+F300-F384 |
| **Material Design (v3)** | **U+F0001-U+F1AF0** (Plane 15; v2's U+F500-FD46 is deprecated) |

How shipping apps handle the missing detection:

| App | Strategy | Source |
|---|---|---|
| **lazygit** | config key `gui.nerdFontsVersion: ''\|'2'\|'3'`; **empty (default) = no icons**; legacy `showIcons` maps to `"2"`; `showFileIcons` toggles | [S26] |
| **starship** | presets: `starship preset nerd-font -o ~/.config/starship.toml`; `no-nerd-font` ("no Nerd Font symbols are used anywhere"); `plain-text` ("Great if you don't have access to Unicode") | [S27] |
| **yazi** | built-in icon rules (nvim-web-devicons derived); install docs list nerd-fonts as "recommended"; no auto-detection documented. Icons on by default | [S28] |
| terminals | WezTerm bundles a Nerd Font Symbols fallback [S5]; Ghostty `adjust-icon-height` [S6]; Alacritty draws only U+E0B0-E0B3 itself [S3]; kitty `symbol_map` [S4] | |
