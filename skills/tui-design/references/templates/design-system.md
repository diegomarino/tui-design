# {{App}} — TUI design system

<!--
Template: copy it with `cp` into the working directory (ask before writing into the user's repository; then {{project}}/docs/tui/design-system.md or next to the theme module) and fill it by editing; do not print it. Delete this comment block when done.
Read this when: starting a TUI, or after an audit whose findings trace back to inlined colours/glyphs/hint grammars.
Each rule names the audit checklist ids it satisfies; tokens come from references/themes/_tokens.json, values from references/themes/{{theme-id}}.json.
Fill-in rules:
- Keep the canonical token NAMES. Change only "Meaning here" / "Used for", and the theme that resolves them.
- Every glyph must be single-width (check: python3 SKILL_DIR/scripts/render_mockup.py {{mock}} --check).
- Delete rows you do not use. Do not invent new tokens; if one is truly missing, note it under "Open questions".
- Example values below are the canonical Fleet demo on catppuccin-mocha (checked against themes/catppuccin-mocha.json).
  Replace them with your theme's values: hex and ratios from python3 SKILL_DIR/scripts/contrast_check.py {{theme-id}},
  the 16-colour column pasted from python3 SKILL_DIR/scripts/preview_theme.py {{theme-id}} --depth 16.
-->

**Rule zero:** define everything below once, in `{{src/tui/theme.ts | theme.py | styles.go | theme.rs}}`, and import it everywhere. Never inline a colour, glyph or key label in a view. Generate the theme code with `python3 SKILL_DIR/scripts/export_theme.py {{theme-id}} --target {{ink|textual|lipgloss|ratatui|gum|css}}`.

| Decision | Value |
|---|---|
| Framework / version | {{Ink 7.1.1 + React 19.2 · Textual 8.2.8 · Bubble Tea v2 + Lip Gloss v2 · Ratatui 0.30.2}} |
| Default theme | {{catppuccin-mocha}} (dark) · light counterpart {{catppuccin-latte}} |
| Theme selection | {{--theme flag > APP_THEME env > config key > dark/light detection > default}} |
| Colour depth policy | truecolor when detected; 256 via OKLab nearest; 16 via each token's `ansi16`; NO_COLOR → attributes + glyphs only ([terminal-capabilities.md](../terminal-capabilities.md) D1) |
| Glyph policy | single-width glyphs only; icon level {{unicode}} by default (§2.1); ASCII fallback column in §2 when {{TERM=linux / non-UTF-8 locale}} |
| Target sizes | primary {{120x30}}, must work {{80x24}} and a 60-column split, minimum {{60x16}} (below: size message) |
| Capability profile | `{{#! caps: …}}` (from §0; copied into every mock) |

## 0. Brief

Filled in branch A step 1 (and C0 framing), before any mockup or recommendation. Ask the user for any item that changes the advice; do not guess a host's limits.

| Item | Value |
|---|---|
| Product shape | {{full-screen app · inline picker (summon–choose–exit) · one-shot CLI · plugin inside a host (name the host: herdr, tmux popup, nvim float, k9s plugin…)}}. It fixes the output contract and who owns the screen, keys and styling ([layout-archetypes.md](../layout-archetypes.md#product-shapes)) |
| Main job per screen | {{screen → the one thing the user does there}} |
| Data shown | {{entities, typical/maximum counts, longest field lengths, update rate}} |
| Target terminals and sizes | {{e.g. iTerm2/Ghostty/tmux; usual 120x30; must work 80x24 and a 60-column split}} |
| Framework and constraints | {{framework + version, or "not decided"; code location}} |
| Capability profile | {{host/framework limits: attributes (bold dim inverse underline italic strike: which exist), colour depth (16 / 256 / truecolor / host theme only), glyph level (ascii / unicode / nerd), widgets available (list, table, text input, tabs, modal…), keys the host reserves}} |
| `#! caps:` line | `{{#! caps: attrs=bold,dim,inverse colors=16 glyphs=unicode}}`: put it in every mock so `render_mockup.py --check` rejects anything outside it (exact keys: [formats.md](../formats.md#capability-profile)) |
| What may change / what must stay | {{may: layout, panes, columns, keys…; must stay: data model, a pane the user relies on, host keybindings…}} |
| Keep from the current UI | {{what already works and survives the redesign: aligned columns, zebra striping, freshness cues, key X…}} (drop one only on purpose, with the reason here; checklist MR-03) |
| Archetype and exemplar | {{e.g. list + detail, like lazygit}} (step 2) |

Every recommendation and mock element that needs more than the profile names its requirement ("needs italic", "needs a text-input widget") so the user can filter by what the host supports (checklist TC-10).

**Assumptions** (decisions taken without the user; confirm each before building):

- {{assumption — why it was needed}}

**Open decisions** (behaviour the mockups invent that the code may not support yet, e.g. folding non-consecutive events into `×2`):

- {{decision — options — what it needs from the code}}

## 1. Colour tokens

<!-- Tier 1 must be mapped by every theme; tier 2 falls back as listed in _tokens.json. "Ratio" = WCAG vs bg.base,
     from python3 SKILL_DIR/scripts/contrast_check.py {{theme-id}}. Floors: ../formats.md#contrast-floors. Token roles: ../color-tokens.md. -->

| Token | {{theme-id}} | 16-colour | Ratio | Meaning here | Used for |
|---|---|---|---|---|---|
| `bg.base` | `#1e1e2e` | default | — | app background | body of every pane |
| `bg.inset` | `#181825` | default | — | chrome below base | {{header/status bands}} |
| `bg.surface` | `#313244` | default | — | raised fill | {{inputs, popups, modal body}} |
| `bg.raised` | `#45475a` | default | — | highest neutral fill | {{active tab bg}} |
| `fg.default` | `#cdd6f4` | default | 11.34 | body text | {{names, values}} |
| `fg.muted` | `#a6adc8` | 15 | 7.37 | secondary text | {{labels, unfocused text}} |
| `fg.faint` | `#7f849c` | default dim | 4.44 | tertiary | {{timestamps, disabled, guides}} |
| `fg.title` | `#cdd6f4` | default bold | 11.34 | panel/section titles | {{panel titles}} |
| `fg.on-accent` | `#1e1e2e` | bg | — | text on chromatic fills | {{chips, badges}} |
| `border.default` | `#6c7086` | 8 | 3.36 | inactive borders, rules | {{unfocused panes}} |
| `border.focus` | `#b4befe` | 4 | 9.17 | focused pane border | {{focused pane}} |
| `accent.primary` | `#89b4fa` | 4 | 7.79 | identity accent | {{cursor glyph ❯, app name, spinner}} |
| `accent.secondary` | `#cba6f7` | 5 | 8.07 | second accent | {{marks}} |
| `selection.bg` / `.fg` | `#3b3d4f` / `#cdd6f4` | reverse | 1.54 vs base; fg 7.38 | cursor row, focused pane | {{list/table cursor row}} |
| `selection.inactive.bg` | `#313244` | default | — | cursor row, unfocused pane | {{…}} |
| `status.success` | `#a6e3a1` | 2 | 11.03 | healthy, done | {{running, ✓ events}} |
| `status.warning` | `#f9e2af` | 3 | 12.91 | degraded, attention | {{degraded, ▲ events}} |
| `status.error` | `#f38ba8` | 1 | 7.08 | failed, destructive | {{failed, ✗ events}} |
| `status.info` | `#94e2d5` | 6 | 11.01 | neutral information | {{…}} |
| `keyhint.key` / `.desc` | `#89b4fa` / `#cdd6f4` | 4 / default dim | 7.79 / 11.34 | key / action label | {{footer}} |
| `statusbar.bg` / `.fg` | `#181825` / `#bac2de` | default / default | — / 9.26 | bars | {{header, footer}} |
| `tab.active.fg` / `tab.inactive.fg` | `#89b4fa` / `#a6adc8` | 4 bold / default dim | 7.79 / 7.37 | tabs | {{tab strip}} |
| `ramp.low` / `.mid` / `.high` | `#a6e3a1` / `#f9e2af` / `#f38ba8` | 2 / 3 / 1 | ≥7.08 | gauge severity | {{CPU/memory/error gauges}} |
| {{`table.header`, `link`, `search.match`, `mark`, `scrollbar.*`, `diff.*`, `cursor.*`, `bg.overlay`}} | | | | | {{only if used}} |

Rules (keep, or edit with a reason):
- **Dim/faint is a layer, not a colour.** Use it for secondary text only (ages, ids, hints, disabled rows). Primary content on warning/error rows is never dim (LH-08, CT-06).
- **Bold means "look here now"**: focused panel title, failing item id, key glyphs in hints. Never bold whole paragraphs (LH-07).
- **Chromatic fills are for short chips only** (§3), with `fg.on-accent` text.
- **Never colour alone.** Every status has glyph + word + colour; selection has a marker + bg; focus has border colour + title bold (CT-03, FS-02, FS-03).
- **Interaction states never borrow status hues**: selection, focus and current tab use neutral or accent tokens (CT-05).
- {{App-specific rule, e.g. "ages always fg.faint, right-aligned"}}

## 2. Glyph vocabulary: single-width only

<!-- Hard rule: every glyph occupies exactly one cell in every terminal mode. No emoji, no VS16, no PUA (Nerd Font
     icons only behind an opt-in flag with this ASCII column as fallback). Width classes SAFE (1 cell everywhere) / AMBIG (2 cells in CJK-ambiguous mode) from
     ../visual-vocabulary.md (V5 status table is the home for glyphs, strict alternatives and ASCII fallbacks; copy from
     it, do not invent). Pick ONE glyph per concept app-wide (GW-04). -->

| Concept | Glyph | ASCII | Token | Width | Notes |
|---|---|---|---|---|---|
| ok / done | `✓` | `[ok]` | `status.success` | SAFE | not `✔` (text-default emoji) |
| warning | `▲` | `[!]` | `status.warning` | AMBIG | strict alternative `▴` (V5); never `⚠`, never `!` as the marker |
| error / failed | `✗` | `[x]` | `status.error` | SAFE | not `✖`, `❌`, `⛔` |
| idle / n/a | `·` | `.` | `fg.faint` | AMBIG | strict alternative `◦` (V5) |
| running / healthy | `●` | `[*]` | `status.success` | AMBIG | strict alternative `◉` (V5) |
| pending / busy | `⋯` or spinner | `...` | `accent.primary` | SAFE | spinner frames: [visual-vocabulary.md](../visual-vocabulary.md) |
| selection cursor | `❯` | `>` | `accent.primary` bold | SAFE | one cursor glyph app-wide |
| collapsed / expanded | `▸` / `▾` | `>` / `v` | `fg.muted` | SAFE | |
| breadcrumb separator | `›` | `>` | `fg.faint` | SAFE | |
| truncation | `⋯` or `…` | `...` | inherit | SAFE / AMBIG | pick one (GW-08) |
| checkbox on / off | `☒` / `☐` | `[x]` / `[ ]` | `accent.primary` / `fg.muted` | — | check with `--check` |
| gauge fill / empty | `█` / `░` | `#` / `-` | `ramp.*` / `fg.faint` | AMBIG / SAFE | always print the number (CA-12) |
| tree guides | `├── └── │` | `\|--` `` `-- `` `\|` | `border.default` | AMBIG | |
| {{concept}} | {{glyph}} | {{ascii}} | {{token}} | {{class}} | {{…}} |

Status rows (ok, warning, error, idle, running, pending, cursor, checkbox) copy [visual-vocabulary.md](../visual-vocabulary.md) V5; keep the two in step. Inventory every glyph the mocks use with `python3 SKILL_DIR/scripts/render_mockup.py --glyphs {{design}}/*.mock` (width class, emoji/PUA flag, lint tier, ASCII fallback) and check it against this table.

### 2.1 Icon level

Icons resolve through one `icon(role)` lookup with three levels, `nerd → unicode → ascii`; the glyph column above is the `unicode` level and the ASCII column the `ascii` level. Add a `Nerd` column only when the `nerd` level is offered. Detail and evidence: [visual-vocabulary.md](../visual-vocabulary.md) V7.

| Decision | Value |
|---|---|
| Default level | {{unicode}} (never `nerd` by default: the app cannot detect the font) |
| How the user opts in | {{--icons nerd\|unicode\|ascii flag > APP_ICONS env > config key}}; `ascii` also when {{TERM=linux / non-UTF-8 locale}} |
| Host limit | the glyph level of the `#! caps:` line caps this choice |
| Slot width | 2 cells per icon (icon + space), asserted in tests; icon always next to a word, never the only carrier of meaning |
| Nerd Font advice for users | the font lives in the user's terminal and cannot ship with the app. Recommend a Nerd Font **Mono** variant (e.g. JetBrainsMono Nerd Font Mono: icons stay one cell) or the symbols-only Nerd Font as a fallback font. Pin the Nerd Fonts major version you target: v3 moved code points (lazygit's `nerdFontsVersion` setting is the precedent) |

## 3. Chips

A chip is one short word, colour-filled, padded with exactly one space on each side, with text in `fg.on-accent`: ` LIVE `, ` stale `, ` 3 new `. Chips replace parenthetical strings like `(4) · reader-mode · stale`. Check `fg.on-accent` ≥ 4.5 on each fill (CA-05).

| Chip | Fill token | Meaning | Where |
|---|---|---|---|
| ` {{live}} ` | `status.success` | {{data streaming}} | {{header right}} |
| ` {{stale}} ` | `status.warning` | {{data older than N s}} | {{panel title}} |
| ` {{…}} ` | | | |

## 4. Key-hint grammar and keymap

<!-- One grammar app-wide (ID-03). Keep the lingua-franca defaults below unless you have a reason. -->

- **Format:** `<key> <verb>`, grammar defined in [../interaction.md](../interaction.md) §3.1 (do not restate it; record only the choices). Separator: {{two spaces (default) | `·` in fg.faint}}. Key in `keyhint.key` bold, verb in `keyhint.desc`. Alternatives joined with `/`: `j/k move`.
- **Footer layout:** context hints left, global hints right (`? help  q quit`) (ID-04). Hints live in the footer, plus a modal's or a which-key popup's own hints (ID-11).
- **Narrow widths:** drop context hints from the right end in reverse priority and end with `…`. Never wrap to a second row (RS-04). `?` and `q` are always kept.
- **Help:** `?` opens an overlay with every binding of the current context in aligned key/action columns. Esc closes it (ID-02, ID-07).

| Action | Key(s) | Scope | Hint label | Priority (1 = last dropped) |
|---|---|---|---|---|
| move | `↑↓` / `j/k` | lists | `↑↓ select` | 2 |
| open / confirm | `enter` | lists, dialogs | `enter open` | 3 |
| back / cancel / close | `esc` | everywhere transient | (implicit) | — |
| search / filter | `/` | lists | `/ filter` | 4 |
| next pane | `tab` / `shift+tab` | global | `tab pane` | 5 |
| help | `?` | global | `? help` | 1 |
| quit | `q`, `ctrl+c` | global (not while typing) | `q quit` | 1 |
| {{destructive verb}} | {{d}} | {{…}} | {{d delete}} | {{…}} (confirm with verb + object, ID-09) |

## 5. Layout constants

| Constant | Value | Why |
|---|---|---|
| App padding | 1 cell left/right inside panes | content never touches borders (DA-07) |
| Cursor column | 2 cells (`❯ ` / `  `) | text does not shift on select (DA-08) |
| Status glyph column | 2 cells (`● `) | |
| Id / name column | {{14}} cells, truncate end | |
| Status word column | {{10}} cells | |
| Age / number column | {{7}} cells, right-aligned | single eye movement down the column (DA-05) |
| Label column (detail) | {{10}} cells | values align (DA-06) |
| Panel split | {{list 32 cols fixed · detail flex}} at ≥ 80 cols | |
| Zebra striping (tables) | {{off · on for wide tables with long gaps or > ~8 rows: stripe `bg.stripe` (else `bg.inset`), darker than base so stripe < inactive selection < selection; parity anchored to the data (e.g. oldest item), not the viewport; whole multi-line records}} | rules: [layout-archetypes.md §2.4](../layout-archetypes.md#24-zebra-striping-tables-logs-long-lists); never meaning-bearing (gone in 16 colours and NO_COLOR) |
| Borders | rounded; focused pane `border.focus`, others `border.default`; title top-left, `fg.title` bold | one style per level (GW-07) |
| Rules / separators | `─` in `border.default`; titled rule `── Title ──────` | |
| Modals | rounded, `bg.surface`, width `min(cols-4, {{60}})`, centred | |

## 6. Contrast layering (how a screen reads at a glance)

1. **Look here now:** chips, bold, status colours, `accent.primary` cursor. A few cells per screen.
2. **Content:** `fg.default` names and values.
3. **Context:** `fg.muted` labels, `fg.faint` ages, ids and hints.

If the screen looks uniformly bright, demote. If it looks uniformly dim, promote primary content out of `fg.faint`/dim.

## 7. States

| State | Visual (tokens + attrs) | Non-colour cue (required) | Example text |
|---|---|---|---|
| focused pane | `border.focus` border, `fg.title` bold title | border colour + bold title + cursor `❯` visible only here | |
| selected row, focused pane | `selection.bg` + `selection.fg`, all spans | `❯` marker | `❯ ● api-gateway   running` |
| selected row, unfocused pane | `selection.inactive.bg` | no `❯`, row still highlighted | |
| current tab | `tab.active.fg` bold on `bg.raised` | bold + fill | ` 1 Services ` |
| disabled | `fg.faint` | reason text | `restart (read-only mode)` |
| loading | `fg.muted` + spinner | words | `Loading services…` |
| empty | `fg.muted` | what appears + how to fill | `No services yet. Press n to add one.` |
| error | `status.error` glyph + word | what · why · next key | `✗ Cannot reach api (timeout 5s). r retry` |
| stale | `status.warning` chip | chip word | ` stale ` |
| too small | `status.error` / `status.success` numbers | words: current vs needed | `Terminal 58x14 · needs 60x16 · q quit` |

## 8. Responsive behaviour

| Size | Layout | What collapses |
|---|---|---|
| ≥ {{120x30}} | {{list + detail + events}} | nothing |
| {{80x24}} | {{list + detail}} | {{events move below gauges; hints elide}} |
| 60-column split ({{60x24}}) | {{list only; enter opens detail full-screen}}: the primary pane wins | {{detail pane; optional columns; context hints elide}} |
| {{60x16}} | {{list only; enter opens detail full-screen}} | {{detail pane}} |
| < {{60x16}} | size message (§7 "too small") | everything; `q` still quits |

## 9. Verification

```bash
python3 SKILL_DIR/scripts/contrast_check.py {{theme-id}} {{light-theme-id}}            # §1 floors, dark and light
python3 SKILL_DIR/scripts/render_mockup.py {{design}}/{{variant}}--normal--80x24.mock --check   # glyph widths, tokens, #! caps:
python3 SKILL_DIR/scripts/render_mockup.py --glyphs {{design}}/*.mock                           # glyph inventory vs §2
python3 SKILL_DIR/scripts/gallery.py {{design}}/ --themes {{theme-id}},{{light-theme-id}} -o gallery.html
```

Golden frames to keep: every required state and size in [../formats.md](../formats.md#frame-naming). Audit the built app with [../audit-protocol.md](../audit-protocol.md) (live-capture path).

## 10. Craft scores

Score each key frame from its PNG with the aesthetic rubric in [../visual-craft.md](../visual-craft.md#aesthetic-rubric) (read the 0/1/2 definitions there; do not score from memory), at the caps depth and at 16 colors. Pass: ≥ 12/16 and no 0. `render_mockup.py FILE --check` craft warnings (CR1–CR7) must be fixed or waived in the frame.

| Frame | Depth | C1 composition | C2 hierarchy | C3 color budget | C4 structure | C5 selection | C6 state at a glance | C7 typography | C8 signature | Total | Fix made |
|---|---|---|---|---|---|---|---|---|---|---|---|
| {{variant--normal--COLSxROWS}} | {{256}} | | | | | | | | | | |
| {{variant--normal--COLSxROWS}} | 16 | | | | | | | | | | |

## Open questions

- {{e.g. warning glyph: default ▲ or the strict alternative from V5? Decide after testing the target font.}}
