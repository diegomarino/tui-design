---
name: tui-design
description: Design, mock up, build and review terminal UIs — full-screen TUIs, interactive CLIs and pickers, and plugin panels or popups inside a host (herdr, tmux, Neovim, k9s, lazygit). Use when designing, reviewing (from code, a live capture or a screenshot) or redesigning a TUI's layout, keybindings, states or colors, including requests that name a known TUI (lazygit, k9s, btop, yazi, helix, fzf); writing terminal mockups; building or fixing one in Ink, Textual, Bubble Tea, Ratatui or gum; mapping a color scheme (Catppuccin, Dracula, Nord, Gruvbox, Tokyo Night, Rosé Pine…) onto a TUI's theme; fixing misaligned glyphs, flicker, NO_COLOR, exit codes, signals, pipes or a broken terminal after exit; suspend or $EDITOR handoff; or profiling a slow TUI. Not for web or native GUIs, terminal-emulator, editor or shell-prompt themes.
license: MIT
---

# tui-design

Design, prototype, build and review terminal UIs with evidence instead of taste. Everything here is **terminal-honest**: a screen is a grid of cells, one font size, integer columns, colors and SGR attributes (bold, dim, italic, underline, inverse, strike), box-drawing for structure. A design that cannot be drawn in that grid — or that the host cannot draw — does not exist.

`SKILL_DIR` is this skill's base directory; run every script as `SKILL_DIR/scripts/<name>` (Python ones with `python3`, or `uv run` when the script header says so). `--help` is the source of truth for flags.

## Before any branch: classify and frame

1. **Product shape** (`references/layout-archetypes.md#product-shapes`): full-screen session · inline picker (summon–choose–exit) · one-shot CLI · **plugin or popup inside a host**. The shape fixes the output contract and who owns the screen, keys and styling. For an inline picker, a one-shot CLI or any app that can run in a pipe or script, the shell boundary (exit codes, Ctrl-C and SIGPIPE, which stream gets what, `--json`, cd on exit) is part of the design: `references/cli-contract.md`.
2. **Constraints that change the advice.** Ask before recommending when unknown: the host's or framework's **capability profile** (widgets, attributes such as italic, color depth, glyph level, reserved keys), the stack and where the code is, the usual terminal size, the theme, and what may change vs what must stay. Read the code when you have it.
   **Measure the host.** The profile is what the host can draw, not what the current code uses: a plugin drawing 8 curses colors today may run in a truecolor pane. For a plugin or popup inside a host, put this in the same message as your other questions: "run `python3 SKILL_DIR/scripts/test_card.py` inside the host (`--curses` if the app uses curses) and send me a screenshot" (it shows attributes, 16/256/24-bit color, fills and glyph widths; compare it with `assets/test-card/*--reference.png`). Record the result as the `#! caps:` line every mock carries, with `source=test-card` (or `docs` when the host documents it); until the screenshot arrives write `source=assumed`, which `--check` keeps warning about (`references/formats.md#capability-profile`).
3. **What already works.** Inventory the current UI's good decisions (alignment, striping, freshness cues…) and keep them unless you drop one on purpose and say so.

## Working rules (every branch)

- **Tokens, never raw colors.** Every color is a semantic token (`fg.muted`, `border.focus`, `status.error`…) from `references/themes/_tokens.json`, resolved by a theme. Mockups reject hex.
- **Single-width glyphs within the caps.** Use the safe set in `references/visual-vocabulary.md#v1-width-hazards-and-the-glyph-linter-policy`; emoji and East-Asian-wide glyphs shift columns. `render_mockup.py --check` enforces this and the `#! caps:` profile.
- **States × sizes.** Every screen exists in the required states and sizes of `references/formats.md#frame-naming`, with a too-small message below its minimum size.
- **Glyph + color.** Status is a glyph and a color (`✓` success, `▲` warning, `✗` error); color alone carries nothing, and a status marker never contradicts its content.
- **Hints in the footer.** Key hints live in the footer (`key verb  key verb`, context left, global right); only a modal or a which-key popup shows its own hints; `?` opens full help.
- **Any sketch shown to the user is a frame.** Build it with `mockkit.py` or pass it through `render_mockup.py --check` at a declared size — hand-typed box sketches drift off the grid. Text tables in chat must keep exact column widths too.
- **Render and look.** Before showing any frame, render it to PNG and inspect the image with this host's image tool (the Host tools table in `references/audit-protocol.md`). A frame you have not looked at is unverified.
- **Real data.** Fill frames from a real source: a snapshot or fixture in the repo, the user's screenshot, their examples. A value you invent is drawn in `fg.faint`, listed in a `#! note:` and named as invented in your answer; never present invented content as a finding.
- **Plain words for the user.** Never show internal labels (branch letters, check ids without their meaning); say "live capture" or "from the screenshot". Put assumptions in `#! note:` lines or the design doc, never as text inside the UI.
- **Artifacts stay in a working directory** (scratch or the current project), with the generator script next to the frames. Read the input and reference files that already exist before building, keep them as they are unless the task asks to change them, and put test or sample data in new files. Ask before writing into another repository the user names.
- **Read references by section.** Open the reference's **Sections** list (its first lines) and read only the line range of the section the step needs: `sed -n 'START,ENDp' FILE`, or the Read tool with offset=START, limit=END−START+1. Never read a whole reference, or the skill tree.
- **Private tmux only.** Any tmux you start (tests, captures, a host to try a plugin in) runs as `tmux -L <name>`; never run `tmux kill-server` without `-L`: the default server is the user's.
- **Slow startup.** When the user asks to profile a slow TUI or to shorten time to the first frame, read the startup column in `references/frameworks/choosing.md`. Those are measured startup times for the five frameworks. This skill has no profiler.
- **Gaps in this skill** found while working: tell the user; do not edit the installed copy.

## Pick the branch

| The user wants… | Branch |
|---|---|
| opinions or advice on a TUI or screenshot ("how would you improve it?", "is this useful?") | **C0. Quick review** |
| a new TUI, a redesign, a screen layout, mockups | **A. Design** |
| code in a framework, a prototype that runs, a theme applied in code, a rendering bug fixed | **B. Build** (after A, or from an agreed design) |
| a measured, evidence-backed audit of a running app or a screenshot | **C. Audit** |
| only colors: choose a scheme, map tokens, check contrast, export a theme | **D. Color** |

Branches chain: C0 → A → B → C (audit the result) is the full loop. Structural problems found in C0 go to A (mock the redesign) before any full audit.

## C0. Quick review

1. **Read** `references/audit-quick.md` (§0, the quick-review core) and the archetype file in `references/archetypes/` (chooser: `references/layout-archetypes.md#1-choose-an-archetype`) or the section of `references/interaction.md` that matches the screen. Done when you can name the archetype and the §0 items that apply.
2. **Frame**: product shape and constraints (above). For a plugin or an unknown stack, ask for the capability profile (for a plugin, the test-card screenshot) before recommending anything that needs it.
3. **Apply §0 and the two reflexes**: the countable clutter audit and the floor test (80×24 and a 60-column split). For a capture or a `.mock`, `ansi_grid.py --clutter` counts the clutter.
4. **Answer**: recommendation first; findings ordered by user harm (`references/audit-quick.md#order-findings-by-user-harm`), **one line each in this shape**: `- **<change>** — <evidence>. Needs: <what the host or terminal must provide, or "nothing new">` (e.g. `Needs: italic`, `Needs: a second pane`, `Needs: nothing new`); what to keep; open questions. Offer mockups (branch A) for structural changes and a full audit (C) when the user wants a measured report. Done when every applicable §0 item is pass, fail or n/a and every recommendation names its requirement.

## A. Design

1. **Frame the task.** Copy `references/templates/design-system.md` into the working directory; it is filled progressively by steps 1, 3, 5 and 7. Fill its §0 Brief (main job per screen, data shown, sizes, product shape, capability profile, what may change, what to keep). Done when each item has a concrete value, or is listed under Assumptions for the user to confirm.
2. **Diverge, then choose.** Reframe the user's job before restyling the current screen: sketch **3 genuinely different concepts** as one `normal` frame each (e.g. a queue/inbox, a map, a spotlight/palette, a dashboard of counts with drill-down — see `references/visual-craft.md#ambition-reframe-before-restyling` and the archetypes in `references/layout-archetypes.md#1-choose-an-archetype`), render and look at them, and compare them against the job. Pick one (or merge) with the user when the choice is theirs. Done when the chosen concept names its exemplar app (`references/exemplars.md#8-archetype-catalog-other-tuis`), its focus order, and why it beats the other two.
3. **Set interaction.** Keys, navigation model, help, confirmations, search from `references/interaction.md` (§1–§5); write them into the design system's §4 keymap. Check each key against `references/interaction.md#key-availability` (macOS F-keys and Option, the host's prefix and bindings); for a plugin, ask the user to run `SKILL_DIR/scripts/key_probe.py` with the footer's keys inside the host. Done when every action has a key that reaches the app, and §4 has the footer hint list for each screen, mode and overlay.
4. **Mock every state and size** with `mockkit.py` (widget helpers, archetype recipes and the states × sizes `matrix()`: `references/mockkit.md`; exact signatures: `references/mockkit-api.md`; format: `references/formats.md#mockup-format`; start from the nearest file in `assets/mockups/<archetype>/` or the demo `assets/demo/fleet--normal--80x24.mock`), named `<variant>--<state>--<cols>x<rows>.mock`, each with the `#! caps:` line. Done when every required state × size exists and `render_mockup.py FILE --check` reports 0 errors for each, and the `#! caps:` line says `source=test-card` or `docs` (or the user declined the test card and your answer says the profile is assumed). For a plugin inside a host, also draw the chosen frame there with `python3 SKILL_DIR/scripts/play_mock.py FRAME.mock` (`d` toggles 256 ↔ 16 colors) and get a screenshot before building.
5. **Pick the theme.** Choose a scheme from `references/color-schemes.md#how-to-choose` (default: one that passes every floor in both depths, e.g. `catppuccin-mocha`); confirm token roles in `references/color-tokens.md#the-44-tokens`. Done when `contrast_check.py ID` and `contrast_check.py ID --depth 16` both exit 0, or each failure is recorded in the design system.
6. **Craft pass.** Open `references/visual-craft.md#aesthetic-rubric` and score each key frame's PNG on C1 composition, C2 hierarchy, C3 color budget, C4 structure economy, C5 selection, C6 state at a glance, C7 typography, C8 signature (0–2 each, definitions there), at the caps depth and at 16 colors, into the design system's §10 table. Fix what scores below 2 when a cheap change lifts it, then re-score. Done when every key frame scores ≥ 12/16 with no 0 at both depths, and `render_mockup.py FILE --check` shows no `craft CRn` warning, or each one is waived with `#! note: craft-ok CRn <reason>`.
7. **Finish the design system.** Fill the remaining sections; take the 16-color column from `preview_theme.py ID --depth 16`. Done when no `{{` placeholder remains and unused rows are deleted.
8. **Show it.** Build a gallery (`gallery.py DIR… --themes a,b -o gallery.html`; each frame exports as TXT/ANSI/SVG/PNG), render key frames to PNG (`render_mockup.py FILE --theme ID -o f.ansi`, then `ansi_render.py f.ansi --theme ID --format png -o f.png`), look at them, and self-review with `references/audit-quick.md` (§0). List every behavior the mockups invent as an open decision. Done when every key frame PNG has been read, checklist failures are fixed or listed, open decisions are listed, and the user has the gallery path. Offer to publish the gallery when the user should judge visuals and your environment can publish pages.

## B. Build

1. **Choose the framework** with `references/frameworks/choosing.md#3-pick-x-when` unless the user fixed it, then read that framework's file in `references/frameworks/` (versions, layout API, pitfalls, one-frame capture recipe) and `references/lifecycle.md` (terminal cleanup, suspend, test pyramid). Bubble Tea code on the web is mostly v1; the v2 notes there are mandatory. Done when the framework and its pinned versions are written down.
2. **Start from the proto-starter** in `assets/proto-starters/<framework>/` (renders the Fleet demo, reads a flat theme JSON, has `--frame --cols --rows --theme --depth` and `capture.sh`). Copy it into the project and keep the frame mode. Done when the copy renders a frame at 80×24.
3. **Apply the theme.** Generate the starter's flat theme with `export_theme.py ID --target json -o theme.json`, and framework theme code with `--target textual|ink|lipgloss|ratatui|gum|css`. Name every style after its token; translate design terms with `references/vocabulary.md#2-master-table`. Done when no color literal remains outside the generated theme.
4. **Capture and compare.** For each state × size: frame mode (or `capture_tui.sh -s 80x24 -s 120x30 -o OUT -- CMD` for a running app), then `compare.py design.mock frame.ansi -o cmp.html`. Done when every difference from the mockup is fixed or listed with its framework reason (the starters' READMEs list known ones).
5. **Audit your own frames** with branch C, the live-capture path. Done when the audit report has no blocker.

## C. Audit

Follow `references/audit-protocol.md` exactly; it is the procedure, with the commands. Perception is separate from judgment:

- **Live capture (the app runs):** `capture_tui.sh` → `ansi_grid.py --describe` gives an exact description; a describer only labels roles and states.
- **Screenshot (image only):** `prep_screenshot.py` → `describe_prompt.py` builds each prompt → a vision subagent per prompt (pass 1 layout, pass 2 per leaf region; prompt text in `references/prompts/describe-tui.md`) → `sample_colors.py` (colors come from pixels, never from the model) → `merge_description.py`.
- **Fidelity:** `description_to_mock.py` → render → `compare.py` against the source; iterate at most twice.
- **Judge:** apply every check in `references/audit-checklist.md` to the validated description, citing region/element ids as evidence; write the report with `references/templates/audit-report.md`. Done when every check is pass, fail (with evidence) or n/a (with reason), and each unverifiable check has had one targeted re-description; any still unverifiable are listed in the report.

## D. Color

1. **Pick** a scheme in `references/color-schemes.md#how-to-choose` (per-scheme detail in `references/schemes/`), with roles from `references/color-tokens.md`; preview with `preview_theme.py ID`.
2. **Check** with `contrast_check.py ID` and `--depth 16`.
3. **Export** with `export_theme.py ID --target …`. A new theme follows `references/themes/catppuccin-mocha.json` and `references/formats.md#theme-json`, with a `provenance` entry per token.

Done when both depths pass, or every failure is noted in the theme's `notes` and told to the user.

## Reference map

| File | Reach for it when |
|---|---|
| `references/layout-archetypes.md` | product shapes, choosing/reviewing screen structure, breakpoints, states, too-small screens, tables and zebra striping; one file per archetype in `references/archetypes/` (incl. chat / agent sessions, forms and settings) |
| `references/interaction.md` | keys, navigation, help, confirmations, search, mouse, feedback timing, long waits, timeouts and stale data |
| `references/exemplars.md` | evidence from k9s, lazygit, lazydocker, gitui, yazi, btop, helix; screenshot corpus |
| `references/vocabulary.md` | translating a generic element (panel, list, tabs…) to a framework's name, or back |
| `references/frameworks/*.md` | building in Ink, Textual, Bubble Tea, Ratatui or gum; `choosing.md` to pick one (incl. startup time to first frame) |
| `references/lifecycle.md` | terminal cleanup on every exit, suspend/editor handoff, resize, non-blocking I/O, test pyramid |
| `references/cli-contract.md` | where the app meets the shell: exit codes (0/1/2/130/143), signals and `app \| head`, TTY checks on stdin and stdout, progress and paging, `--json`/NDJSON, error messages, cd on exit and `init` scripts; `SH-` checks |
| `references/visual-craft.md` | making it look good and ambitious: composition, hierarchy, color budget, signature elements, the aesthetic rubric and README test, reframing into 3 concepts, with a worked example |
| `references/color-tokens.md` | token roles, selection and focus styles, mapping tokens to app theme keys |
| `references/color-schemes.md`, `schemes/` | picking a scheme, a token's hex in a scheme, which schemes pass contrast |
| `references/terminal-capabilities.md` | color depth, NO_COLOR, dark/light detection, tmux, resize |
| `references/terminal-escapes.md` | emitting raw escape sequences, building without a framework, per-terminal feature support |
| `references/visual-vocabulary.md` | borders, bars, spinners, status glyphs, width hazards, icon levels and Nerd Fonts |
| `references/glyph-data.md` | raw glyph data: full box-drawing chart, wide-char lists, braille bit math, spinner frames, Nerd Font ranges |
| `references/accessibility.md` | color-vision deficiency, screen readers, plain mode, reduced motion |
| `references/tools.md` | which script does what, when to use it, its key flags; the HTML gallery (keys, export, viewing it locally) |
| `references/mockkit.md` | building frames in Python: quick start, which helper for which need (panel, table, listing, tree, keybar, overlay, toosmall), recipes per archetype, `matrix()` for every state × size |
| `references/mockkit-api.md` | the exact signature of a mockkit class, method or helper (instead of reading `mockkit.py`) |
| `references/formats.md` | `.mock` markup and `#! caps:` profile, theme JSON, 16-color specs, contrast floor values, frame naming and required states, vocabulary ids |
| `references/audit-quick.md` | §0 for any quick review or self-review, and the order of findings |
| `references/audit-checklist.md` | the full check list for an audit |
| `references/audit-protocol.md`, `prompts/describe-tui.md` | a full audit (live capture or screenshot pipeline) |
| `references/templates/` | design-system and audit-report documents |
| `references/schemas/tui-description.schema.json` | do not read; validate with `merge_description.py --validate`; field meanings are in `prompts/describe-tui.md` |
