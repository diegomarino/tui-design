# Visual vocabulary: glyphs, borders, bars, spinners, status markers

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [V1. Width hazards and the glyph linter policy](#v1-width-hazards-and-the-glyph-linter-policy) · L21–75 — a glyph shifts columns or the lint flags it.
- [V2. Box-drawing sets: which one, when](#v2-box-drawing-sets-which-one-when) · L77–111 — choosing a border set.
- [V3. Bars, gauges, sparklines, braille charts](#v3-bars-gauges-sparklines-braille-charts) · L113–151 — drawing quantities.
- [V4. Scrollbars, trees, separators, arrows, bullets](#v4-scrollbars-trees-separators-arrows-bullets) · L153–172 — structural glyphs inside panes.
- [V5. Status glyph table (role -> glyph -> ASCII -> token)](#v5-status-glyph-table-role---glyph---ascii---token) · L174–196 — the safe status glyphs and their tokens.
- [V6. Spinners](#v6-spinners) · L198–215 — busy indicators and frame rates.
- [V7. Nerd Fonts and icon levels](#v7-nerd-fonts-and-icon-levels) · L217–235 — whether to use icons and how to fall back.
- [V8. Glyphs for empty, loading, error, skeleton](#v8-glyphs-for-empty-loading-error-skeleton) · L237–249 — state glyphs.
- [V9. ASCII fallback map](#v9-ascii-fallback-map-the-seed-for-the-renderer-and-any---ascii-mode) · L251–274 — an ASCII-only host or `glyphs=ascii` caps.
- [Source index](#source-index) · L276–278 — resolving a source key.

Read this when you choose or audit any non-ASCII glyph (borders, bars, status markers, spinners, icons), when a mockup fails `render_mockup.py --check`, or when you need an ASCII fallback. Raw data (Box Drawing chart, EAW=W list, braille bit math, spinner provenance, Nerd Font ranges) is in [glyph-data.md](glyph-data.md).

Evidence tags: `[Sn]` = [source index](#source-index); `derived:` = inference or own computation; `UNVERIFIED` = not confirmed. Unicode data: **EastAsianWidth 18.0.0** (2026-06-29), emoji-data 2026-01-30, emoji-variation-sequences 2026-01-09 [S23].

---

## V1. Width hazards and the glyph linter policy

Three parties must agree on how many cells a string takes: the app (layout math), the terminal (cursor advance), the font (glyph size). kitty's author: "If the two disagree, then the entire user interface can be broken ... there is no such shared database in reality" [S20]. Rule of thumb: EAW **W and F = 2 cells**; N, Na, H = 1; combining marks (Mn/Me) and Cf = 0; **A (ambiguous) = 1 unless the terminal is in "ambiguous-wide" mode, then 2** [S22]. UAX #11: ambiguous characters "should be treated as narrow" when context cannot be established; private-use code points have ambiguous width, so **every PUA code point is class A** [S22]. Measured on 18.0.0 (`derived:` from [S23]):

- **A covers almost every structural glyph**: Box Drawing except U+254C-254F and U+2574-257F; Block Elements except U+2590-2591 and U+2596-259F; `● ○ ◆ ■ ▲ ▼ ★ … · • → ×`; every Nerd Font / Powerline icon. A linter that refused A would refuse all borders, hence the tiers below.
- **Text-default emoji + VS16 is the real trap**: `⚠ ✔ ✖ ⚙ ❤ ℹ ⏺ ⏸ ✳ ▶ ♥` are width 1 bare, **2 cells after U+FE0F** in terminals that follow the kitty/Ghostty/Windows Terminal grapheme algorithm [S20][S21][S9]; a font may also draw a color-emoji bitmap that overflows without FE0F.
- `☰` U+2630 and `⚡` U+26A1 are **W** (Nerd Fonts also patches them [S25]). `░` is N but `▒ ▓ █ ▀ ▄ ▌` are A; `◉ ▸ ▹ ► ◄ ◂ ▴ ▾ ∙ ⠿` N while `● ○ ◆ ■ ▲ ▼ ▶ ◀ • ·` A; `✓` N but `√` A; `…` U+2026 is A (use `⋯` U+22EF, N, or `...`).
- "Ambiguous = wide" is a user setting in xterm (`cjkWidth`), iTerm2, WezTerm (`treat_east_asian_ambiguous_width_as_wide`, default false) and Windows Terminal [S1c][S7][S5][S8]. When it is on and the app assumes 1, every `│ ─ ●` doubles, right borders shift, lines wrap early. A TUI cannot detect it: **keep column-aligned content free of A-class glyphs where cheap, offer an ASCII mode, and treat borders as the accepted risk**.
- k9s puts emoji (W) in its flash line (`😎 😗 😡`, auto-clears after 6 s); it works because that is a single unaligned row. Keep W glyphs out of aligned columns.

### Linter policy (what `SKILL_DIR/scripts/render_mockup.py --check` enforces)

Implemented in `SKILL_DIR/scripts/_mock.py` (`classify_glyph`). Output `file:line:col: ERROR|WARN|INFO: msg`; exit 1 on any ERROR. Checks run in this order and the first match wins:

| Tier | Rule |
|---|---|
| **ERROR** | U+FE0F / U+FE0E, U+200D (ZWJ), regional indicators U+1F1E6-1F1FF, skin-tone modifiers U+1F3FB-1F3FF, U+FFFD, control characters; **any non-ASCII glyph under `#! caps: glyphs=ascii`** (hint = its V9 fallback); **PUA** (category Co, or U+F0000-10FFFF) unless `--allow-nerd-font` or `glyphs=nerd` (under an explicit `glyphs=unicode` PUA stays ERROR even with the flag); **EAW W/F** anywhere in the body (this includes every `Emoji_Presentation=Yes` code point) |
| **WARN** | tab; Mn/Me combining marks; **text-default emoji** (the `TEXT_EMOJI` set: `✔ ✖ ⚠ ⚙ ❤ ℹ ⏺ ⏸ ▶ ◀ ♥ ✳ ▪ ↩ © ® ™ ...`; checked before the A-class rules, so `▶ ◀ ♥` are WARN although A); U+2800 braille blank; an **A-class glyph outside the chrome set** (with a replacement hint) |
| **INFO** (ERROR under `--strict-ambiguous`) | the dashes **`—` U+2014 and `–` U+2013** in copy (EAW=A, single-width in monospace fonts; strict replacement `-` or `─`); an **A-class chrome glyph**: any EAW=A code point in Box Drawing + Block Elements U+2500-259F, any EAW=A code point in **Geometric Shapes U+25A0-25FF**, and the symbol set `● ○ ◆ ■ ▲ ▼ ★ … · • → × √ ← ↑ ↓` |
| **OK** | N, Na, H (including the N members of the chrome blocks: `╌╍╎╏`, `╴-╿`, `▐ ░ ▖-▟`), Braille U+2800-28FF, sextants U+1FB00-1FB3B, octants U+1CD00-1CDE5 (N, thin font support: `UNVERIFIED` where drawn) |

Glyph levels come from the capability profile ([formats.md](formats.md#capability-profile)): `#! caps: glyphs=ascii|unicode|nerd` (default `unicode`), or `--caps "glyphs=…"` for a file without the header; the other switches are `--strict-ambiguous` and `--allow-nerd-font`. Not implemented: a "declared wide-content region" exemption (a W glyph is an ERROR wherever it appears) and an N-only (`unicode-safe`) level; use `--strict-ambiguous` for that. A line-width comparison under A=1 and A=2, the UTF-8 gate and the ASCII-fallback requirement below are conventions for application code and reviews, not lint checks: every non-ASCII glyph used in chrome should have an entry in the V9 fallback map. Width-table generation and the UTF-8 gate: [glyph-data.md](glyph-data.md) G2.

### Width hazard table (computed from the Unicode files; tier = linter result)

**Em** = `Emoji=Yes`; **+FE0F** = cells after U+FE0F under the kitty algorithm (bare width is 1 unless EAW is W/F).

| Glyph | Codepoint | EAW | Em | +FE0F | Tier | Use instead |
|---|---|---|---|---|---|---|
| ✔ | U+2714 heavy check | N | Y | **2** | WARN | `✓` |
| ✖ | U+2716 heavy mult x | N | Y | **2** | WARN | `✗` or `✕` |
| ⚠ | U+26A0 warning | N | Y | **2** | WARN | `▲` (INFO) or `▴` (N) |
| ℹ | U+2139 info | N | Y | **2** | WARN | `i` |
| ⚙ | U+2699 gear | N | Y | **2** | WARN | a text label or `⋮` U+22EE |
| ❤ ♥ | U+2764, U+2665 | N / A | Y | **2** | WARN | a word |
| ⏺ | U+23FA record | N | Y | **2** | WARN | `◉` U+25C9 or `⬤` U+2B24 |
| ⏸ | U+23F8 pause | N | Y | **2** | WARN | the word `paused` |
| ✳ | U+2733 eight spoked | N | Y | **2** | WARN | `✱` U+2731 or `✶` U+2736 |
| ▶ | U+25B6 right tri | A | Y | **2** | WARN | `▸` U+25B8 (N) or `❯` U+276F (N) |
| ✅ ❌ ⛔ | U+2705, U+274C, U+26D4 | W | Y | 2 | ERROR | `✓` / `✗` |
| ⏳ ⌛ | U+23F3, U+231B | W | Y | 2 | ERROR | a spinner (V6) or `⋯` |
| ⚡ ⭐ | U+26A1, U+2B50 | W | Y | 2 | ERROR | a word / `★` (chrome) or `✶` |
| ☰ | U+2630 trigram | **W** | - | 2 | ERROR | the word `menu` |
| 🔒 🟢 | U+1F512, U+1F7E2 | W | Y | 2 | ERROR | a word / `●` with a status token |
| ● ○ ◆ ■ ▲ ▼ ★ | U+25CF, 25CB, 25C6, 25A0, 25B2, 25BC, 2605 | A | - | 1 | INFO | `◉ ◌ ▴ ▾ ✶` for N-only |
| … · • → × | U+2026, 00B7, 2022, 2192, 00D7 | A | - | 1 | INFO | `⋯`, `∙`, `➜`, `✕` |
| — – | U+2014, U+2013 | A | - | 1 | INFO | fine in copy; `-` or `─` when strict |
| ▒ ▓ █ ─ │ ╭ | U+2592, 2593, 2588, 2500, 2502, 256D | A | - | 1 | INFO | chrome; see V2 |
| PUA (Powerline, Nerd Font) | U+E0B0, U+F07B, U+F0001 | A | - | 1 | ERROR (without `glyphs=nerd` or `--allow-nerd-font`) | V7 |

**SAFE list** (N-class, not emoji; 1 cell in every mode, linter OK): `✓ ✗ ✘ ✕ ◉ ◌ ◦ ∙ ‣ ⬤ ▸ ◂ ▴ ▾ ► ◄ ❯ › » ➜ ➤ ⋯ ⋮ ☐ ☒ ▰ ▱ ✶ ✦ ✧ ✱ ⚬ ↻ ⠿ ░ ⌘ ⎋ ⏎ ⌫` (key caps: font coverage uneven off macOS). Not SAFE despite looking plain: `↩ U+21A9`, `▪ U+25AA` (Emoji=Yes, WARN). **Usable in copy** (A-class, INFO): `— –` (em and en dash), `· … → ×`; keep them out of fixed-width columns when cheap.

Safe-emission rules (`derived:`): (1) never emit U+FE0F/FE0E/200D/regional indicators/skin tones in layout text; (2) treat any `Emoji=Yes` glyph as risky even when EAW=N; (3) never truncate between a base glyph and its trailing mark; (4) budget `…` as 1 cell and verify.

---

## V2. Box-drawing sets: which one, when

Chart of all 128 code points: [glyph-data.md](glyph-data.md) G1.

| Set | Code points | When to use | Evidence |
|---|---|---|---|
| **light** (default) | `┌ ┐ └ ┘ ─ │ ├ ┤ ┬ ┴ ┼` | structure everywhere: panels, tables, dividers | Lip Gloss `Normal`, Ratatui `PLAIN` [S24][S29] |
| **rounded** | light + `╭ ╮ ╯ ╰` | friendly/dashboard apps; the focused pane. Fleet demo, **lazygit** (`gui.border: rounded`), **btop** (title chips `┤¹cpu├`) | [S26][S31] |
| **heavy** | `┏ ┓ ┗ ┛ ━ ┃ ┣ ┫ ┳ ┻ ╋` | emphasis: the single focused pane or a destructive confirm (**gitui** confirm popups) | Lip Gloss `Thick`, Ratatui `THICK` |
| **double** | `╔ ╗ ╚ ╝ ═ ║ ╠ ╣ ╦ ╩ ╬` | sparingly: title banners, about/splash, one modal; two double rules on one screen look noisy (`derived:`) | Lip Gloss `Double` |
| **dashed** | `┄┅┆┇` 2504-2507, `┈┉┊┋` 2508-250B, `╌╍╎╏` 254C-254F (the only dashes that are **N**) | secondary/placeholder regions, "drop here", disabled panes | Ratatui ships 6 dashed sets [S29] |
| **mixed** | light/heavy U+250D-254A; single/double `╒╓╕╖╘╙╛╜╞╟╡╢╤╥╧╨╪╫` | heavy header rule over a light body; table with a double header rule | |
| **half-lines** (N) | `╴ ╵ ╶ ╷ ╸ ╹ ╺ ╻ ╼ ╽ ╾ ╿` | collapsed panel rows (lazygit `╶─[3]─Local branches - Remotes - Tags──1 of 2─╴`); scrollbar tracks | |
| **block borders** | Lip Gloss `OuterHalfBlock` `▛▀▜ ▌▐ ▙▄▟`, `InnerHalfBlock` `▗▄▖ ▐▌ ▝▀▘`, `Block` `█`, `Hidden` = spaces | filled "card" look; `Hidden` keeps geometry without ink | [S24] |
| **ASCII** | `+ - \|` (Lip Gloss `ASCII`) | `TERM=linux`, no UTF-8, screen-reader or `--ascii` mode, text pasted into tickets | [S24] |

```text
light        rounded      heavy        double       dashed 3     dashed 2 (N)  ASCII        outer half   inner half
┌───┬───┐    ╭───┬───╮    ┏━━━┳━━━┓    ╔═══╦═══╗    ┌┄┄┄┬┄┄┄┐    ┌╌╌╌┬╌╌╌┐     +---+---+    ▛▀▀▀▀▀▜      ▗▄▄▄▄▄▖
│ A │ B │    │ A │ B │    ┃ A ┃ B ┃    ║ A ║ B ║    ┆ A ┆ B ┆    ╎ A ╎ B ╎     | A | B |    ▌ ABC ▐      ▐ ABC ▌
├───┼───┤    ├───┼───┤    ┣━━━╋━━━┫    ╠═══╬═══╣    ├┄┄┄┼┄┄┄┤    ├╌╌╌┼╌╌╌┤     +---+---+    ▙▄▄▄▄▄▟      ▝▀▀▀▀▀▘
│ C │ D │    │ C │ D │    ┃ C ┃ D ┃    ║ C ║ D ║    ┆ C ┆ D ┆    ╎ C ╎ D ╎     | C | D |
└───┴───┘    ╰───┴───╯    ┗━━━┻━━━┛    ╚═══╩═══╝    └┄┄┄┴┄┄┄┘    └╌╌╌┴╌╌╌┘     +---+---+
```

| Rule | When | Example |
|---|---|---|
| One border family per screen, plus at most one emphasis family | always | rounded everywhere, heavy only for the destructive confirm modal |
| Focus is shown by color **and** weight: `border.focus` + (heavy or `fg.title bold` title) | multi-pane screens | unfocused `border.default` light; focused `border.focus` rounded; add `❯` in the focused list (not color alone) |
| Build tables from `─` and `│` rules, not per-cell boxes | tables that truncate/scroll | one header rule `├──┼──┤`, no row boxes |
| Put titles in the top border with a space either side: `╭─ Services (6) ─────╮` | panes | the title is plain text so it survives `NO_COLOR` and screen capture |
| Treat rounded corners as font-dependent (some fonts draw `╭╮╰╯` sharp); verify box glyphs in the target fonts | shipping defaults | |
| Alacritty draws its own box/powerline glyphs (U+E0B0-E0B3, box thickness from cell width) [S3]; a CJK main font can make A glyphs literally double-width [S1c] | debugging misaligned borders | |

---

## V3. Bars, gauges, sparklines, braille charts

Block Elements (U+2580-259F):

| Role | Glyphs |
|---|---|
| halves | `▀`2580 upper, `▄`2584 lower, `▌`258C left, `▐`2590 right (N) |
| **vertical eighths (fill from bottom)** | `▁▂▃▄▅▆▇█` U+2581-2588 |
| **horizontal eighths (fill from left)** | `▏▎▍▌▋▊▉█` U+258F-2588 |
| shades | `░`2591 ~25 % (N), `▒`2592 ~50 %, `▓`2593 ~75 % |
| quadrants (mask TL=1 TR=2 BL=4 BR=8) | 1`▘` 2`▝` 3`▀` 4`▖` 5`▌` 6`▞` 7`▛` 8`▗` 9`▚` 10`▐` 11`▜` 12`▄` 13`▙` 14`▟` 15`█`, 0 = space |
| sextants / octants | U+1FB00-1FB3B (2x3), U+1CD00-1CDE5 (2x4); EAW N, font support thin: assume absent |

**Progress bars**: **always print the number** (`42%` or `21/50`) beside a bar; color and length are invisible to speech and fail WCAG 1.4.1 alone. Keep the unfilled track visible (>= 3:1 vs bg; Bubbles' default empty `#606060` is 3.34:1 on black, 6.29:1 on white). Sub-cell precision: whole cells `█`, last cell `▏▎▍▌▋▊▉` by `idx = round(frac*8)` [S29 `gauge.rs`]. Samples (20 cells; the Fleet demo uses `█`/`░` with `ramp.low|mid|high` + `fg.faint`):

```text
  5% █░░░░░░░░░░░░░░░░░░░ 5%       68% █████████████▋░░░░░░ 68%       100% ████████████████████ 100%
```

| Style | Glyphs | Source / note |
|---|---|---|
| block + shade | `█` filled / `░` empty | indicatif default `█░`; Bubbles default, colors `#7571F9` / `#606060` [S34][S33] |
| sub-cell | `█` + `▏▎▍▌▋▊▉` | Ratatui `Gauge` [S29]; ASCII `#` / `=` + `>` |
| heavy line | `━` filled, `─` unfilled in a dimmer token; half cells `╸` / `╺` (N) | Textual `Bar` [S30]; Ratatui `LineGauge` [S29]. `━━━━━━━━━━━━━━──────` 68 % |
| parallelogram meter | `▰` U+25B0 / `▱` U+25B1 (**both N**: the best N-class pair) | cli-spinners `aesthetic`, Bubbles `Meter` [S32][S33]. `▰▰▰▰▰▰▰▱▱▱` |
| ASCII | `[=====>    ]`, `[#####-----]` | universal fallback |

Severity gauges (Fleet's CPU/Memory/Errors): fill color from `ramp.low` -> `ramp.mid` -> `ramp.high`, never green-to-red alone: add the number and, for the worst band, a glyph (`▲`) ([accessibility.md](accessibility.md)).

**Sparklines**: `▁▂▃▄▅▆▇█` (all A): Textual `Sparkline.BARS`, Ratatui `NINE_LEVELS` [S30][S29]. `idx = round((v-min)/(max-min)*7)`; use `▁` as the floor so the axis is visible; empty = space. Sample for `3 5 2 8 13 9 21 18 7 4 6 12 30 27 15 9`:

```text
▁▂▁▃▄▃▆▅▂▁▂▃█▇▄▃          unicode (A-class)
_._,-,=~._.,#+-,          ASCII fallback  _ . , - ~ = + #
```

**Braille** (U+2800-28FF, 2x4 dots, all EAW N) gives the most resolution per cell: `code point = 0x2800 + mask`. Bit math and btop's 25-glyph mapping: [glyph-data.md](glyph-data.md) G3. Degradation ladder (btop [S31]): braille (N) -> quadrants (N) -> shades -> ASCII (`.:|#`). Caveats: U+2800 blank may render nothing and breaks copy/paste alignment in some fonts; screen readers announce each cell as "braille pattern dots-..." and GitHub CLI called braille spinners inaccessible [S40].

---

## V4. Scrollbars, trees, separators, arrows, bullets

| Element | Rule | Glyphs |
|---|---|---|
| Scrollbar | thumb vs track differ by **glyph**, not only color; thumb >= 1 cell; hide when content fits (`derived:`) | Ratatui `DOUBLE_VERTICAL`: track `║`, thumb `█`, ends `▲ ▼`; `VERTICAL`: `│ █ ↑ ↓` [S29]. Textual: reverse-video thumb, partial ends `▁-▇` / `▉-▏` [S30]. N-only: `╷╵╹╻` + `█` |
| Tree guides | 4 cells per level; each guide is A. `├── ` `└── ` `│   `, rounded last `╰── `; ASCII per `tree --charset=ascii` (`UNVERIFIED` citation) | sample below |
| Separators | `─` / `-`; `│` / `\|`; inline dot `·` (A), `∙` (N) or ` \| ` | `prod-eu · 12:04:31` (Fleet header) |
| Breadcrumb | `›` U+203A, `»` U+00BB, `❯` U+276F (N), or `/` | `Services › api-gateway › Logs` |
| Arrows (N-safe) | `➜ ➤ ► ◄ ▸ ◂ ▴ ▾ ⏎ ⌫ ⎋ ⌘ ⌥ ⌃` | key-cap glyphs: font coverage uneven off macOS |
| Arrows (A-class, avoid in aligned columns) | `← ↑ → ↓ ⇒ ⇧ ▲ ▼ ▶ ◀` | `▶ ◀` are also text-default emoji (WARN) |
| Bullets | `∙ ‣ ◦` (N); `• ·` (A); ASCII `-`, `*` | |
| Ellipsis | `⋯` U+22EF (N) or `...`; `…` U+2026 is A | truncate by cells, budget the ellipsis as 1 |

```text
├── src            |-- src
│   └── main.rs    |   `-- main.rs
└── README         `-- README
```

---

## V5. Status glyph table (role -> glyph -> ASCII -> token)

**The single table**; the V9 fallback map, design-system templates and mockups derive from it. **Rule**: every status carries **glyph + word + color token + position**; remove any one and the others still say it ([accessibility.md](accessibility.md)). *Default* matches the Fleet demo and uses chrome-set A-class glyphs (INFO); *Strict (N-only)* keeps alignment under ambiguous-wide. One ASCII fallback per role.

| Role | Default | Strict (N-only) | ASCII | Token | Word cue |
|---|---|---|---|---|---|
| success / done / passed | `✓` | `✓` | `[ok]` | `status.success` | `ok`, `passed` |
| failure / error | `✗` | `✗` | `[x]` | `status.error` | `failed` |
| warning / degraded | `▲` | `▴` | `[!]` | `status.warning` | `degraded`, `warn` |
| info / note | `i` | `i` | `[i]` | `status.info` | `info` |
| running / healthy (steady state) | `●` | `◉` | `[*]` | `status.success` (healthy) or `accent.primary` (busy) | `running` |
| working / loading (activity in progress) | spinner (V6) or `⋯` | `⋯` | `...` | `accent.primary` | `loading...` |
| pending / idle / stopped | `·` | `◦` | `.` | `fg.faint` | `stopped`, `pending` |
| selected / current row | `❯` | `❯` | `>` | `accent.primary` on `selection.bg` | (+ inverse row) |
| marked / multi-select | `●` | `◉` | `*` | `mark` | |
| checkbox | `☐` / `☒` | same | `[ ]` / `[x]` | `fg.default` | |
| radio | `◉` / `◌` | same | `(*)` / `( )` | `fg.default` | |
| diff added / removed / changed | `+` / `-` / `~` | same | same | `diff.added` / `diff.removed` / `diff.changed` | |
| link | underlined text (OSC 8 enhances) | same | `text (url)` | `link` | URL visible somewhere |

Avoid: `✔ ✖` (emoji, +FE0F wide), `✅ ❌ ⚠ ⏳` (wide or emoji), `⏺ ⏸` (emoji), `!` or `⚠` as the warning marker (use `▲`; `!` is only the ASCII `[!]`), `○` as pending in strict mode (A), `▶` as current-row marker (A + emoji). Fleet's status column and event list use `●` (running), `▲` (degraded), `✗` (failed), `·` (stopped), `✓` (finished) with the word beside each (`../assets/demo/fleet--normal--80x24.mock`).

---

## V6. Spinners

Recommended N-class sets (width 1 in both ambiguity modes), exact frames from `sindresorhus/cli-spinners` [S32]; all 19 compared sets, width verdicts and who ships what: [glyph-data.md](glyph-data.md) G4.

| Name | ms | Frames |
|---|---|---|
| `dots` (default) | 80 | ⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏ |
| `dots2` | 80 | ⣾ ⣽ ⣻ ⢿ ⡿ ⣟ ⣯ ⣷ |
| `dots3` | 80 | ⠋ ⠙ ⠚ ⠞ ⠖ ⠦ ⠴ ⠲ ⠳ ⠓ |
| `star` | 70 | ✶ ✸ ✹ ✺ ✹ ✷ |
| `arc` | 100 | ◜ ◠ ◝ ◞ ◡ ◟ |
| `arrow3` | 120 | ▹▹▹▹▹ ▸▹▹▹▹ ▹▸▹▹▹ ▹▹▸▹▹ ▹▹▹▸▹ ▹▹▹▹▸ |
| `aesthetic` | 80 | ▰▱▱▱▱▱▱ ▰▰▱▱▱▱▱ ... ▰▰▰▰▰▰▰ (then loops) |
| `line` (ASCII fallback) | 130 | - \ \| / |

**Rules** (`derived:`): (1) constant frame width (jitter shifts the label); (2) prefer the N-class sets above; avoid emoji sets (`moon`, `earth`: W, FE0F traps) and A-class ones (`pipe`, `growVertical`, `bouncingBall`, lazygit's `●∙∙`); (3) 70-130 ms is the shipping range; (4) redraw only the spinner cell, wrap bigger updates in synchronized output ([terminal-escapes.md](terminal-escapes.md) D7); (5) replace with static text (`Working...`) when not a TTY, `TERM=dumb`, `CI` set, reduced motion or screen-reader mode ([accessibility.md](accessibility.md) A4).

---

## V7. Nerd Fonts and icon levels

Nerd Fonts patches icons into the **Private Use Area**; all PUA is EAW **A**, so no width is defined and the linter reports PUA as ERROR unless the frame declares `#! caps: glyphs=nerd` (or `--allow-nerd-font`). Code-point ranges and how lazygit, starship and yazi handle it: [glyph-data.md](glyph-data.md) G5.

**Detection is impossible**: the terminal cannot report the active font, and DA1/XTVERSION say nothing about glyph coverage; a "print and measure with CPR" probe measures advance, not glyph presence (`derived:` from the query list in [terminal-escapes.md](terminal-escapes.md) D6). So apps either ask the user or ship both modes.

| # | Rule | When | Concrete example | Source |
|---|---|---|---|---|
| N1 | **Nerd Fonts are never required.** Every screen works and reads the same at the `unicode` and `ascii` levels; icons are decoration next to a word, never the only carrier of meaning | any app that shows icons | file list: icon + `src/`; branch: icon + `main`; the word stays when the icon goes | `derived:` |
| N2 | **Three levels `nerd → unicode → ascii`, default `unicode`**, resolved through one `icon(role)` function; the user opts in with a flag, config key or env var, never by detection | apps with icons | `--icons=nerd\|unicode\|ascii`, `MYAPP_ICONS=nerd`; `icon("dir")` = `U+F07B` (nerd) / `▸` (unicode, SAFE list) / `>` (ascii), each followed by a space and `src/` | lazygit `gui.nerdFontsVersion` (default `""` = no icons) [S26]; starship presets `nerd-font-symbols` / `no-nerd-font` / `plain-text-symbols` [S27] |
| N3 | **Reserve 2 cells per icon** (icon + space) and assert it in tests; never end a fixed-width column on a PUA glyph | icon columns | `▸ src/` and `U+F07B src/` both start the name at the same column | kitty gives a PUA glyph 2 cells only when a space follows [S4]; glyph-data G5 |
| N4 | **Recommend the *Mono* variant** (`… Nerd Font Mono`) to users who want icons in aligned columns: its icons are scaled to one cell. The plain variant draws bigger icons that spill into the next cell (hence the space); `Propo` is proportional, not for terminals | install docs, design-system glyph section | "Icons: install JetBrainsMono Nerd Font **Mono** and run with `--icons=nerd`" | Nerd Fonts README [S25] |
| N5 | **Offer the symbols-only font** as the alternative: users keep their own font and add `Symbols Nerd Font` as a fallback in the terminal | users attached to their font | kitty `symbol_map U+F000-U+F2FF Symbols Nerd Font Mono`; WezTerm / Ghostty font fallback lists | Nerd Fonts README [S25] |
| N6 | **The font lives in the user's terminal**: an npm, pip, cargo or brew package cannot install it into the terminal's font setting. Ship the levels, document the install, never bundle a font and assume it is used | packaging, README | README: "Icons need a Nerd Font set in your terminal; without one, keep the default `unicode` level" | `derived:` |
| N7 | **Pin the code-point generation.** Nerd Fonts v3 moved Material Design icons from U+F500-FD46 to U+F0001+ (Plane 15); an app that hard-codes one set shows wrong glyphs on the other. Prefer icons outside the moved range, or make the version a setting | apps choosing nerd glyphs | lazygit asks `nerdFontsVersion: "2"` or `"3"` | [S25]; [S26]; glyph-data G5 |

**Mockups:** declare the level in the header, `#! caps: glyphs=unicode` (default) or `glyphs=nerd` / `glyphs=ascii` ([formats.md](formats.md#capability-profile)); mock the `unicode` level for every frame and add `nerd` or `ascii` twins only for screens whose width or wording changes. The design system's glyph section records the level, the env var or flag, and the icon table per role.

---

## V8. Glyphs for empty, loading, error, skeleton

Behavior, text patterns and rules for these states (k9s sync-before-empty, lazygit panel texts, skeleton screens) live in [layout-archetypes.md §2.3](layout-archetypes.md#23-states-every-archetype-must-design). Glyph lines only:

| State | Glyph | Fallback |
|---|---|---|
| loading | `⋯` or a V6 spinner, in `accent.primary` | `...` |
| empty | none (a sentence naming the reason and the key that fills it); `·` for an empty cell | `-` |
| error / failed | `✗` in `status.error` | `[x]` |
| stale / degraded | `▲` in `status.warning`, values `fg.faint` | `[!]` |
| skeleton placeholder | `░` in `fg.faint` at final widths (N) | `.` |

---

## V9. ASCII fallback map (the seed for the renderer and any `--ascii` mode)

Format `role: [default glyph, ASCII]`. Status and widget roles mirror V5 exactly (one ASCII per role); the strict glyphs are in V5.

```yaml
ok:        ["✓", "[ok]"]        warn:      ["▲", "[!]"]         # not ⚠ (text-default emoji)
fail:      ["✗", "[x]"]         info:      ["i", "[i]"]
running:   ["●", "[*]"]         working:   ["⋯", "..."]         # or a V6 spinner / "..."
pending:   ["·", "."]           cursor:    ["❯", ">"]
marked:    ["●", "*"]           bullet:    ["∙", "-"]
check_on:  ["☒", "[x]"]         check_off: ["☐", "[ ]"]
radio_on:  ["◉", "(*)"]         radio_off: ["◌", "( )"]
ellipsis:  ["⋯", "..."]         crumb:     ["›", ">"]           # "…" U+2026 is class A
rule_h:    ["─", "-"]           rule_v:    ["│", "|"]
corners:   ["╭ ╮ ╰ ╯", "+"]     tees/cross: ["├ ┤ ┬ ┴ ┼", "+"]   # "┌ ┐ └ ┘" for sharp
tree_mid:  ["├── ", "|-- "]     tree_last: ["└── ", "`-- "]     tree_pipe: ["│   ", "|   "]
bar_full:  ["█", "#"]           bar_empty: ["░", "-"]           bar_8: ["▏▎▍▌▋▊▉", "="]
spark:     ["▁▂▃▄▅▆▇█", "_.,-~=+#"]   shade: ["░▒▓█", ".:+#"]
scroll_thumb: ["█", "#"]        scroll_track: ["│", "|"]
```

An ASCII frame must keep the same width per line as its Unicode twin: the multi-cell replacements (`[ok]`, `[x]`, `[!]`, `[i]`, `[*]`, `...`, `(*)`, `[ ]`) need reserved width, so give status slots 4 cells in ASCII mode and truncate by cells (`derived:`). In mockups, `#! caps: glyphs=ascii` makes the linter reject every non-ASCII glyph and suggest its entry from this map ([formats.md](formats.md#capability-profile)); the map itself is for the application.

---

## Source index

**S1c** xterm(1) https://invisible-island.net/xterm/manpage/xterm.html ; **S3** Alacritty changelog https://github.com/alacritty/alacritty/blob/master/CHANGELOG.md ; **S4** kitty FAQ + text sizing https://sw.kovidgoyal.net/kitty/faq/ , https://sw.kovidgoyal.net/kitty/text-sizing-protocol/ ; **S5** WezTerm https://wezterm.org/config/fonts.html ; **S6** Ghostty https://ghostty.org/docs/config/reference ; **S7** iTerm2 https://iterm2.com/downloads.html ; **S8** Windows Terminal 1.25 Preview https://devblogs.microsoft.com/commandline/windows-terminal-preview-1-25-release/ ; **S9** Contour terminal-unicode-core https://github.com/contour-terminal/terminal-unicode-core ; **S19** Rich https://github.com/Textualize/rich ; **S20** kitty text sizing / width algorithm https://sw.kovidgoyal.net/kitty/text-sizing-protocol/ ; **S21** Ghostty `grapheme-width-method` (config reference) ; **S22** UAX #11 https://www.unicode.org/reports/tr11/ ; **S23** Unicode data https://www.unicode.org/Public/UCD/latest/ucd/EastAsianWidth.txt , .../emoji/emoji-data.txt , .../emoji/emoji-variation-sequences.txt , https://www.unicode.org/Public/emoji/latest/emoji-sequences.txt ; **S24** Lip Gloss `borders.go` https://github.com/charmbracelet/lipgloss ; **S25** Nerd Fonts https://github.com/ryanoasis/nerd-fonts (README: font variants Mono / default / Propo, Symbols Nerd Font; `glyphnames.json`; wiki "Glyph Sets and Code Points") ; **S26** lazygit https://github.com/jesseduffield/lazygit (`docs/Config.md`, `pkg/i18n/english.go`) ; **S27** starship presets https://starship.rs/presets/ ; **S28** yazi https://yazi-rs.github.io/docs/installation/ ; **S29** Ratatui `symbols/*.rs`, `widgets/{gauge,scrollbar}.rs` https://github.com/ratatui/ratatui ; **S30** Textual `scrollbar.py`, `renderables/{bar,sparkline}.py`, `widget.py` https://github.com/Textualize/textual ; **S31** btop https://github.com/aristocratos/btop (`src/btop_draw.cpp`) ; **S32** cli-spinners https://github.com/sindresorhus/cli-spinners ; **S33** Bubbles https://github.com/charmbracelet/bubbles (`spinner/spinner.go`, `progress/progress.go`) ; **S34** indicatif https://github.com/console-rs/indicatif (`src/style.rs`) ; **S35** ora, is-unicode-supported https://github.com/sindresorhus/ora ; **S36** drawille https://github.com/asciimoo/drawille ; **S37** CLI Guidelines https://clig.dev/ ; **S40** GitHub Blog "Building a more accessible GitHub CLI" https://github.blog/engineering/user-experience/building-a-more-accessible-github-cli/ ; **S42** Claude Code https://code.claude.com/docs/en/accessibility ; **S43** https://accessibility.github.com/documentation/guide/cli/ ; **S44** huh https://github.com/charmbracelet/huh ; **S46** k9s `internal/view/browser.go` https://github.com/derailed/k9s . Linter implementation: `SKILL_DIR/scripts/_mock.py` (`classify_glyph`). This index also serves [glyph-data.md](glyph-data.md).
