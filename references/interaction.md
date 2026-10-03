# Interaction: keys, navigation, discoverability, feedback

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [1. Default key bindings](#1-default-key-bindings) · L19–66 — choosing keys: what the 7 reference apps ship, key availability (macOS, hosts, reserved keys).
- [2. Navigation models](#2-navigation-models) · L68–86 — how focus moves between panes, views and drill-downs.
- [3. Discoverability](#3-discoverability) · L88–157 — footer hint grammar (§3.1), the `?` help overlay (§3.2), which-key popups (§3.3).
- [4. Confirmations and destructive actions](#4-confirmations-and-destructive-actions) · L159–188 — delete, kill, quit with unsaved work, approvals.
- [5. Search and filter](#5-search-and-filter) · L190–204 — `/` search, live filter, match highlighting.
- [6. Selection and multi-select](#6-selection-and-multi-select) · L206–214 — marking several items and bulk actions.
- [7. Mouse](#7-mouse) · L216–227 — whether and how to support clicks, wheel and drag.
- [8. Feedback timing](#8-feedback-timing) · L229–257 — spinners, progress, toasts; §8.1 long waits, timeouts and stale data.
- [9. Implementation hooks](#9-implementation-hooks) · L259–271 — the binding, focus and palette APIs per framework.
- [10. Audit checklist (interaction)](#10-audit-checklist-interaction) · L273–285 — a quick tick list for reviewing keys and feedback.

`n/7` = how many of seven reference apps ship that default (k9s v0.51.0, lazygit v0.65.1, lazydocker v0.25.2, gitui v0.28.1, yazi v26.9.1, btop v1.4.7, helix 25.07.1; read in source and run live, 2026-10). `[live]` = seen in a capture of the running app, `[src]` = read in its source or default config, `derived:` = our inference.

---

## 1. Default key bindings

Rule: ship the consensus key for every action that has one (≥5/7), and **also** bind the arrow/Home/End/PgUp/PgDn variant so non-vim users never need to learn anything. Where the exemplars diverge, apply the decision rule in the last column.

| Action | Ship this | Consensus | Divergence → decision rule |
|---|---|---|---|
| Move up/down | `↑`/`↓` **and** `k`/`j` | arrows 7/7, `j`/`k` 5/7 (gitui, btop opt-in) | none — always both |
| Move left/right | `←`/`→` **and** `h`/`l` | 5/7 | meaning differs: pane switch (lazygit), parent/child (yazi), sort column (btop). Rule: `h`/`l` = the spatial neighbor of the focused thing (pane, level, column) |
| Open / drill in | `enter` | 7/7 | yazi also `l`/`o`; gitui also `→` |
| Back / cancel / close | `esc` | 7/7 | `esc` must exit every transient state (popup, filter, mode, selection) — lazygit, yazi, helix |
| Quit | `q` at the root view, plus `ctrl+c` | `q` 5/7, `ctrl+c` 6/7 | k9s uses `q` = back in sub-views and `:q` to quit; helix `:q` (q records macros). Rule: `q` quits from the root, goes back elsewhere; editors use `:q`. Ask only when work would be lost (lazygit `confirmOnQuit`, default off) |
| Help | `?` | 4/7 (k9s, lazygit, lazydocker, btop) | gitui `h`, yazi `~`/`F1` (`?` = find previous), helix `Space ?`. Rule: `?`; if `?` is search-backward or focus is in a text input, use `F1` (bind `F1` everywhere anyway) |
| Search / filter | `/` | 6/7 (gitui `f`) | yazi splits `f` filter vs `/` find. Rule: `/` = filter the focused list; add `n`/`N` when it is "find next" over text |
| Command line | `:` | 4/7 (k9s, helix; lazygit/yazi = shell command) | Rule: `:` = typed app command with completion; shell commands only behind an explicit verb |
| Switch pane | `tab`/`shift+tab`, digits `1`-`9` printed in titles | digits 5/7 | k9s has no panes (`[` `]` history, `-` last view). Rule: digits jump, tab cycles, title shows `[2]` |
| Tabs inside a pane | `[` / `]` | lazygit, lazydocker, yazi | — |
| Page up/down | `PgUp`/`PgDn` **and** `ctrl+b`/`ctrl+f`; half page `ctrl+u`/`ctrl+d` | PgUp/PgDn 5/7 | lazygit `,`/`.`. Rule: never use `ctrl+d` for anything but half-page-down, except EOF on an **empty** text input (quit or end of input, the shell convention chat sessions keep, archetype K) |
| Top / bottom | `Home`/`End` **and** `g`/`G` | Home/End 5/7 | yazi/helix `gg` (because `g` is a chord prefix). Rule: `gg` if you have `g`-prefixed chords, else `g` |
| Select / mark | `space` (toggle + move down) | 5/7 | `v` range (lazygit, yazi, helix), `ctrl+a` all, `ctrl+r` invert (yazi) |
| Refresh | automatic + `ctrl+r` | auto 4/7 | k9s `ctrl+r`, lazygit `R`. Rule: refresh automatically and show freshness; manual `ctrl+r` (keep `r` for a verb such as restart/rename) |
| Delete | `d` → confirm; `D` = irreversible variant | `d` 4/7 | k9s `ctrl+d` (clashes with tmux/terminals, top complaint #625), gitui `shift+D`, btop `t`/`k`. Rule: `d` trash/remove with confirm, `D` permanent (yazi) |
| Confirm / cancel in dialogs | `enter` / `esc`, plus `y` / `n` | 7/7 / 7/7 | k9s needs `tab` to reach OK — avoid |
| Copy | `y` | 4/7 (lazygit, gitui, yazi, helix) | k9s `c`, lazygit `ctrl+o`. Rule: `y` yank; `c` stays a verb (comment/create/change) |
| Sort | `s` cycle column, `S` reverse — tables: `shift+<column letter>` | no consensus | k9s `shift+n/a/s`, yazi `,` + letter, btop `←→` + `r`. Rule: show the sort in the title/header (`CPU↓`) whatever the key |
| Apply / save staged changes | a letter verb on the review surface (`w` write, `a` apply, `c` commit) that opens a one-line summary (`apply 3 names?  enter yes · esc back`); `ctrl+s` as an alias | no consensus: lazygit `c` commit, helix and vim `:w`, k9s `ctrl+s` | Rule: a staged batch is applied with a letter plus a confirm line that counts the changes; F-keys only as aliases (see Key availability) |
| Undo | `u` (editors) / `z` (actions) | 2/7 | lazygit `z`/`Z`, helix `u`/`U`. Rule: prefer undo over confirmation for reversible actions |
| Zoom / screen mode | `+` / `_` or `f` | lazygit, lazydocker; k9s logs `f` | — |

**Never give another meaning to:** `ctrl+z` — in raw mode it does **not** suspend by itself (the terminal stops turning it into SIGTSTP), so either implement suspend through the framework (Bubble Tea `tea.Suspend`, Textual `suspend_process`; otherwise restore the terminal, raise SIGTSTP, redraw on resume: [lifecycle.md](lifecycle.md) LC3) or leave it unbound; `ctrl+\` (SIGQUIT), `ctrl+s`/`ctrl+q` without disabling XON/XOFF flow control, and anything that needs to tell `ctrl+i` from `tab`, `ctrl+m` from `enter`, `ctrl+[` from `esc` unless the kitty keyboard protocol is negotiated (see [terminal-escapes.md](terminal-escapes.md) D7). Printable keys must not act globally while a text input has focus — the form mockup's footer uses `ctrl+c cancel`, not `q` (`../assets/mockups/form-wizard/setup--normal--80x24.mock`).

### Key availability

A key in the footer is a promise. Before shipping one, check that it **reaches the app** on the user's platform and inside the host; the OS, the terminal and a multiplexer or plugin host take keys first.

| Layer | Takes | Rule |
|---|---|---|
| macOS | **F1–F12** are media/brightness keys unless `fn` is held or "Use F1, F2, etc. keys as standard function keys" is on; **⌘** shortcuts belong to the terminal app; `ctrl+←/→` switch Spaces; `ctrl+space` switches input source (`derived:` macOS defaults) | never make an F-key or ⌘ the only way to do something; F-keys are aliases (`F1` help, `F2` rename) next to a letter |
| Terminal | **Option/Alt** types characters on macOS unless "Option as Meta/Alt" is set (Terminal.app, iTerm2 profile, Ghostty `macos-option-as-alt`); `ctrl+shift+…` and ⌘ are terminal shortcuts; `ctrl+s`/`ctrl+q` are flow control unless the app turns XON/XOFF off (curses `raw()` does) (`derived:`) | `alt+x` only as an alias; `ctrl+s` only when the app owns raw mode |
| Multiplexer / host | the prefix and its table: tmux `ctrl+b`, screen `ctrl+a`, zellij mode keys (`ctrl+p` `ctrl+t` `ctrl+n` `ctrl+s` `ctrl+o` `ctrl+g` `ctrl+q` in the default layout), and the host's own bindings (read its config: `tmux list-keys`, `~/.config/zellij/config.kdl`, the host's config file) | inside a host, never bind its prefix or its unprefixed bindings; letters and `enter`/`esc`/arrows almost always pass |
| Text input focus | every printable key | inside an input only `enter`, `esc`, `tab`, arrows and `ctrl+` keys act |

**Safe core** (reaches the app everywhere checked): letters, digits, `enter`, `esc`, `tab`, `shift+tab`, arrows, `space`, `backspace`, `/`, `?`, `ctrl+` letters not taken above.

**Check it.** At design time, list the footer keys and cross out what the table and the host's config take. In the target, run `python3 SKILL_DIR/scripts/key_probe.py KEY…` (the footer's keys) inside the host and ask for a screenshot: a key that never turns ✓ does not arrive. An app cannot detect at runtime that a key was taken (it simply never sees it), so the fix is a design choice or a user-remappable key, not runtime detection. When a convention says F-key (`F2` rename, `F5` refresh), keep it as an alias and put the letter first in the footer.

**Remapping**: make keys configurable when users live in the app (lazygit `keybinding.universal.*` YAML, yazi `keymap.toml` with `prepend_keymap`, helix `[keys.normal]`, gitui `key_bindings.ron`); k9s and lazydocker do not allow remapping built-ins and collect complaints for it (k9s #625).

---

## 2. Navigation models

| Model | Mechanism | Visible state | Use when | Exemplar |
|---|---|---|---|---|
| Pane focus cycle | `tab`/`shift+tab`, `h`/`l`, digit jump | focused border `border.focus`; `[n]` in titles | 2-5 persistent panes | lazygit (`[1]`-`[5]`, `0` = main), lazydocker |
| View stack | `enter` pushes, `esc` pops; `[`/`]` history, `-` previous view | breadcrumb `prod-eu › payments › pods` in the header or a crumbs row | drill-down through levels (cluster → ns → pod → container → logs) | k9s (crumbs row, `ctrl+g` hides it) |
| Tabs | digits, `tab`, `[`/`]` | tab bar with the key in the label (`Status [1]`, ` 1 Services `) | 3-7 peer workspaces | gitui, yazi, canonical demo |
| Modes | `i`/`v`/`esc` (editor), `/`, `:` | mode chip at the left of the statusline (` NOR `, ` INS `, ` SEL `) in `accent.primary inverse` | text editing, visual selection | helix, yazi (`NOR`/`SEL`) |
| Command line | `:` + name, aliases, completion | 1-row prompt at the bottom (helix) or a 3-row box above the content (k9s) | hundreds of targets (resource kinds, files) | k9s `:pod`, `:dp`; helix `:` with doc box |
| Prefix chords | `g`, `space`, `,`, `ctrl+w` + key | which-key popup + pending key in the statusline | > ~30 actions; group by verb family | yazi (`g`, `,`, `c`, `m`, `t`), helix (`g`, `space`, `m`, `z`) |

Rules:
1. `enter` goes deeper, `esc` comes back — everywhere, including inside popups (7/7).
2. Coming back restores cursor, scroll and filter of the previous view.
3. Show where you are: breadcrumb or tab bar always visible; counters `1 of 7` / `[9/18]` in titles (lazygit, k9s).
4. One verb per letter across views (lazygit VISION: `d` destroy, `n` new, `space` primary, `enter` go in, `o` open, `e` edit).
5. Modal input routing: a popup owns all keys until closed; restore the previous focus target on close.

---

## 3. Discoverability

Two tiers always, a third when there are chords: (1) persistent context hints in the footer, (2) `?` full, searchable list, (3) which-key on prefix. Add a command palette when actions exceed what the footer can hold.

### 3.1 Footer hint grammar

Hints live in the footer, plus a modal's or a which-key popup's own hints (they take over input).

```text
 ↑↓ select  enter open  a approve  / filter  tab pane            ? help  q quit
 └─ key in keyhint.key bold, verb in keyhint.desc ─┘              └ global, right ┘
```

| Rule | Example |
|---|---|
| Pairs are `key verb`: literal lowercase key, then a one-word verb | `d describe`, `ctrl+d delete`, `shift+tab prev` |
| Separator: two spaces by default ([canonical demo](formats.md#canonical-demo)); `·` in `fg.faint` is allowed app-wide; one choice, never mixed | `enter open  a approve` / `enter open · a approve` |
| Left = verbs for the focused pane, most frequent first; right = global (`? help  q quit`) | demo footer |
| Change the left group with focus/mode; a modal or which-key popup shows only its own hints (`enter run  esc close`) | palette footer; lazygit popup `Confirm: <enter> \| Close/Cancel: <esc>` |
| Fit: ~5-6 pairs at 80 cols, ~8-10 at 120; drop from the end of the left group, never drop help/quit; or offer `more [.]` (gitui expands to a multi-row bar) | `pods--normal--80x24` vs `--120x30`; lazygit truncates with `...` at 70 cols |
| Item exists but verb not allowed → keep it, render `fg.faint`, say why in the message line; no item at all → hide item verbs | `k kill` faint while stale (`sysmon--error--80x24`); empty inbox footer shows only `2 mine  3 team  r refresh`; lazygit VISION.md: "if a keybinding is disabled, give a reason" |
| Arrows as glyphs (`↑↓`, `←→`), modifiers spelled (`ctrl+`, `shift+`, `alt+`); key-cap symbols `⏎ ⎋` only if the font is known | `↑↓ select`, `shift+tab prev`; gitui `key_symbols.ron` lets users rename `⏎`/`⇧` |

Formats in the wild (pick one; never mix): lazygit `Stage: <space> | Commit: c`, gitui `Stage [Enter]`, k9s header `<d> Describe`, lazydocker `b: view bulk commands`. The skill's grammar is `key verb` (demo).

### 3.2 `?` help overlay

Content checklist (lazygit `?` menu, yazi `~`, btop `F1`, gitui `h`):
- [ ] Title + a filter input (`Type to filter`, lazygit; yazi help has a filter box).
- [ ] Groups: **current context first** (lazygit `--- Local ---`), then navigation, then global.
- [ ] Rows: key column (right-aligned or fixed width, `keyhint.key`) + description (`fg.default`); submenus end with `…`.
- [ ] Disabled rows stay visible in `fg.faint` with the reason.
- [ ] `enter` executes the selected row (yazi, lazygit) — help doubles as a palette.
- [ ] Position counter (`1 of 65`, lazygit) and `esc close` in the footer.
- [ ] Generated from the same keymap table the app dispatches on (k9s hints are the registered actions, so they never drift).

```text
╭─ Keys · Services ───────────────────────── / filter ─╮
│ Services                                             │
│   enter      open service                            │
│   r          restart                                 │
│   d          delete…                                 │
│   l          logs              (needs 1 pod)         │  <- disabled: fg.faint + reason
│ Navigation                                           │
│   ↑↓ / j k   move                                    │
│   tab        next pane                               │
│ Global                                               │
│   ctrl+p     command palette                         │
│   q          quit                                    │
╰──────────────────────────────────────────── 1 of 24 ─╯
```

### 3.3 Which-key popups

- Trigger: a prefix key (`g`, `space`, `,`). Delay: helix waits `editor.idle-timeout = 250 ms` (no popup for fast experts); yazi shows it immediately. Rule: 250 ms default, configurable, `auto-info = false` to disable (helix).
- Placement: bottom-right box (helix Goto ~43 cols; Space ~66 cols, 2 columns) or a full-width bottom band (yazi, 3 columns). Never cover the cursor line.
- Rows: `key  description`, key column fixed; the pending key echoed in the statusline (`g`) and in the box border.
- Mockups: `../assets/mockups/editor/code--normal--80x24.mock` (Goto, 1 column), `--120x30` (Space, 2 columns).

### 3.4 Other mechanisms

| Mechanism | Rule | Exemplar |
|---|---|---|
| Command palette | every command has a name, a group and (if bound) its key shown right-aligned; fuzzy match highlighted in `search.match`; `ctrl+p` (Textual default) or `space ?` (helix) | [archetype G](archetypes/g-command-palette.md); Textual `COMMAND_PALETTE_BINDING = "ctrl+p"` |
| Jump labels in titles | `[1] Status`, `Status [1]`, ` 1 cpu ` — the label is the key | lazygit, gitui, btop superscripts |
| Tooltips under menus | selected menu item explained in a box below ("Discard both staged and unstaged changes in 'f1.txt'.") | lazygit menus [live] |
| Command echo / log | show the underlying command the app ran (teaches + builds trust) | lazygit command log pane |
| Onboarding | first-run popup with one action (`Press <enter> to get started`), `:tutor`; empty states that teach (layout §2.3) | lazygit, helix |

---

## 4. Confirmations and destructive actions

Confirmation effort proportional to irreversibility:

| Reversibility | Pattern | Keys | Wording example | Exemplar |
|---|---|---|---|---|
| Undoable | do it; message line offers undo | `z`/`u` | `✓ dropped commit 5a64f77 · z undo` | lazygit `z` (reflog), helix undo instead of dialogs |
| Recoverable (trash, soft delete) | small dialog, default = yes | `y`/`enter` yes, `n`/`esc` no | `Trash 1 selected file?` + path, `[Y]es  (N)o` | yazi `d` |
| Destructive, single item | dialog: verb + object in the title, consequence in the body, default focus on the safe button | `enter` = focused button, `esc` cancel, `y`/`n` shortcuts | `Delete pod api-worker-6b9fd-2mncr?` | k9s `ctrl+d` (Cancel/OK), gitui `confirm file reset?` |
| Destructive, bulk | count + list in the dialog | same | `Delete 3 marked pods?` + names | k9s marks |
| Irreversible and remote / prod | typed confirmation of the name | type, then `enter` | `Type payments to delete the namespace` | k9s `Confirm:` field |

Wording and styling rules:
- Title = verb + object + `?`; body = the consequence and scope, in human terms; buttons named with the verb (`Delete` / `Cancel`), not `OK`.
- Destructive dialogs use a `status.error` border and the verb in `status.error bold`; neutral confirmations use `border.focus`.
- `esc` always cancels; default focus on the non-destructive choice for destructive actions.
- Offer the reversible path next to the irreversible one (`d` trash vs `D` delete — yazi).
- `readOnly` mode removes dangerous bindings entirely (k9s): safety by absence.

```text
╭─ Delete pod? ────────────────────────────────────────╮   <- border status.error
│ api-worker-6b9fd-2mncr will be terminated; its       │
│ ReplicaSet schedules a replacement.                  │
│                                                      │
│                       [ Cancel ]   [ Delete ]        │   <- Cancel focused (selection.bg)
╰──────────────────────────────────────────────────────╯
 enter confirm focused  ←→ switch  y delete  n/esc cancel
```

---

## 5. Search and filter

| Rule | Example |
|---|---|
| `/` opens a 1-row input in place (pane title, bottom line or a small box above the list), never a full-screen modal | lazydocker bottom `filter:`; k9s 3-row prompt above the table |
| Narrow live as you type; `enter` commits and returns focus to the list; `esc` clears and restores the previous cursor | btop `Enter`/`Esc`; k9s `Esc` clears |
| Distinguish **filter** (hide non-matching) from **find** (jump `n`/`N`) | yazi `f` filter vs `/` find |
| Keep the active filter visible after committing: title `/api`, count `[9/18]` | `pods--normal--80x24`; k9s `Pods(ns)[12]` + filter text |
| Default semantics: smart-case substring for lists, fuzzy for palettes/pickers, regex behind a prefix (`!` inverse, `-l` labels) | k9s `/! x`, `/-l app=x`; btop `!` regex |
| Highlight matched characters in `search.match` bold | palette `Rest`art |
| No results → empty state naming the query and the way out (`esc clear filter`) | `stream--empty--80x24` |
| Clamp cursor and scroll after filtering, deletion or a smaller viewport | 12 rows, cursor on row 10, filter leaves 4: cursor on row 4 |
| Tag async search results with the query that produced them; drop stale ones | results for `ap` arriving after the user typed `api` are discarded |

---

## 6. Selection and multi-select

- Cursor ≠ mark. Cursor = one row, `selection.bg` + `❯`. Marks = any number of rows, `mark` token (`▌` in the left gutter or `●` in a mark column), counted in the title/status bar (`2 marked`, `2 selected`).
- Keys: `space` toggles the mark and moves down (yazi), `v` starts a range (lazygit, yazi), `ctrl+space` marks a range (k9s), `ctrl+a` all and `ctrl+r` invert (yazi), `esc` clears marks (yazi; k9s `ctrl+\`).
- Verbs act on marks when any exist, else on the cursor row; say which in the footer (`ctrl+d delete 2`) — mockup `../assets/mockups/table-explorer/pods--normal--120x30.mock`.
- Keep marks across filter changes; show hidden marked items (`2 marked · 1 hidden by filter`) (`derived:`).
- Bulk actions without marks: a `b` bulk menu (lazydocker) is an alternative when multi-select is rare.

---

## 7. Mouse

| Rule | Detail |
|---|---|
| Optional, never required | every action reachable by keyboard; mouse adds click-to-focus, click-to-select, wheel-scroll |
| Defaults in the wild | on: lazygit, lazydocker, yazi, btop, helix, Textual (`run(mouse=True)`); off: k9s (`ui.enableMouse`); none in Ink core |
| Tracking steals native text selection | provide a toggle (config + key) and document the terminal's bypass modifier (varies by terminal: Shift in most, Option in iTerm2) |
| Protocol | SGR mouse `CSI ?1002h` + `CSI ?1006h`; wheel = buttons 64/65 with coordinates; avoid 1003 (all-motion flood) unless hover matters ([terminal-capabilities.md](terminal-capabilities.md) D7) |
| Clicks never trigger destructive verbs directly | a click selects; a key or a confirmation acts |
| Links via OSC 8 work without mouse tracking | degrade to plain text where unsupported (Terminal.app) |

---

## 8. Feedback timing

| Event | Timing | Source |
|---|---|---|
| Key press → visible change | same frame; < 100 ms | — |
| Show a loading indicator | only after ~100-300 ms (avoid flashes); no measured convention, pick a value and keep it | [layout-archetypes.md §2.3](layout-archetypes.md#23-states-every-archetype-must-design) |
| Which-key popup | 250 ms idle after a prefix | helix `idle-timeout = 250` [src] |
| Spinner frame interval | 70-130 ms typical; lazygit `●∙∙` at 180 ms | cli-spinners; lazygit `gui.spinner.rate: 180` [src] |
| Spinner vs progress bar | spinner for ~1-5 s; bar with count (`[3/7]`, `42%`) beyond ~5 s | — |
| Transient flash message | k9s clears after 6 s (`DefaultFlashDelay`); keep errors until the next user action | k9s `model/flash.go` [src] |
| Message line with age | persistent last event + relative age (`· 4m ago`) instead of a vanishing toast | canonical demo (a ticking age = honest liveness) |
| Auto-refresh cadence | k9s `refreshRate` 2 s; btop `update_ms = 2000`, `+`/`-` step 100 ms | [src] |
| Stale marker | as soon as one refresh is missed: `STALE 42s` chip + faint values | `sysmon--error--80x24`, `pods--error--80x24` (`derived:`) |
| Too-small screen poll | btop re-checks size every 100 ms; also react to SIGWINCH | btop [src] |
| Reduced motion / non-TTY / screen reader | replace spinners with static text (`Working…`) | GitHub CLI, huh, Claude Code (visual-vocabulary.md V6) |

### 8.1 Long waits, timeouts and stale data

None of this is an established TUI convention (lazygit and gh apply it piecemeal); the rows are `derived:` unless a source says otherwise. Shell-side progress (stderr, non-TTY) is [cli-contract.md](cli-contract.md) CC11.

| # | Rule | When | Concrete example | Source |
|---|---|---|---|---|
| T1 | **Show elapsed time once a wait passes ~1 s**, counting up next to the verb, plus the cancel key; switch to a determinate count or bar when the total is known | any request, scan or tool run | `⠹ fetching pods · 4s   esc cancel`; at 5 s still counting, never a frozen spinner | `derived:` from web guidance (indicator at 1 s, determinate past ~3 s) |
| T2 | **Cancel beats auto-timeout.** Esc (or the documented key) cancels the in-flight request at any time and returns to the last good state; an automatic timeout, when you need one, is long, stated in the message, and ends in an error state with a retry key, not a silent retry loop | network and subprocess calls | after 30 s: `✗ api did not answer in 30s (timeout) · r retry  esc back`; the list behind still shows the last good data, marked stale | `derived:`; [layout-archetypes.md §2.3](layout-archetypes.md#23-states-every-archetype-must-design) error rows; TC-08 (Ctrl-C acts within 1 s) |
| T3 | **Retries are visible and bounded**: attempt count, next delay, and a way to stop; back off instead of hammering | reconnecting sources | header `DISCONNECTED 12s` chip; message line `retry 3/5 in 8s · esc stop` | k9s `apiServerTimeout` / `maxConnRetry` settings (connection loss is a designed-for case); archetype E "disconnected" |
| T4 | **Stale data stays, marked as stale**: keep the last good values, fade them, show their age, disable verbs that act on them. This is the `degraded` variant of the `error` state ([layout-archetypes.md §2.3](layout-archetypes.md#23-states-every-archetype-must-design)) | any live view after one missed refresh | `STALE 42s` chip, values in `fg.faint`, `k kill` disabled (`sysmon--error--80x24`) | table above, "Stale marker" row; ST-07 |
| T5 | **Transient failures never rewrite persistent config.** A device, server or plugin missing at startup or during a run is shown as unavailable; it is not removed from the user's settings, layout or presets, and it comes back when the source returns | anything that saves layout or settings | btop's open bug: a temporarily missing GPU makes it reset `shown_boxes` to the defaults; do instead `gpu1  ▲ not detected` in its box or the setup list, config untouched | [btop #906](https://github.com/aristocratos/btop/issues/906) (also #902: presets edited on cycle); archetype F rule F7 |

---

## 9. Implementation hooks

| Framework | Bindings + hints | Focus | Palette / help |
|---|---|---|---|
| Ink 7 | `useInput((input, key) => …, {isActive})`; render your own footer | `useFocus` / `useFocusManager` (tab order = registration order; no focus trap: gate modals with `isActive`) | build it; no built-in |
| Textual | `BINDINGS = [Binding("d", "delete", "Delete", show=True)]` feeds the `Footer`; `check_action()` hides/disables | `can_focus`, `focus_next` on tab | built-in command palette `ctrl+p` (`COMMANDS = {Provider}`) |
| Bubble Tea v2 | `key.Binding` + `help.Model` (`ShortHelp`/`FullHelp`) renders footer and `?` view | app-owned `focusIndex`, call `Focus()`/`Blur()` | build it (list with filter) |
| Ratatui | app-owned key map; compose the footer as a `Line` of styled spans | app-owned enum + `next()` on tab | build it |
| gum | per-command keys (`gum choose`, `gum filter`) | n/a | `gum filter` is a ready fuzzy picker |

Details and versions: [frameworks/ink.md](frameworks/ink.md), [frameworks/textual.md](frameworks/textual.md), [frameworks/bubbletea.md](frameworks/bubbletea.md), [frameworks/ratatui.md](frameworks/ratatui.md), [frameworks/gum.md](frameworks/gum.md).

---

## 10. Audit checklist (interaction)

- [ ] Arrows, `enter`, `esc` work everywhere; `j`/`k` too in lists.
- [ ] `esc` leaves every popup, filter, mode and selection.
- [ ] Footer shows context verbs left, `? help  q quit` right; changes with focus; fits 80 cols without wrapping.
- [ ] `?` (or `F1`) opens a filterable list generated from the real keymap.
- [ ] Every destructive verb has a confirmation proportional to reversibility, with verb + object in the title.
- [ ] `/` filter shows the active query and match count; no-match state explains the way out.
- [ ] Marks are distinct from the cursor and counted; verbs say whether they apply to marks.
- [ ] No printable key acts globally while a text input is focused.
- [ ] Every footer key reaches the app on the target platform and inside the host (Key availability; `key_probe.py`); no action is reachable only by an F-key, ⌘ or Alt.
- [ ] Mouse is optional; tracking can be turned off.
- [ ] Loading/stale/error feedback appears within the timings of §8 and is never color-only.
