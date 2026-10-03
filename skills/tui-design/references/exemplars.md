# Exemplars: seven real TUIs, torn down

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [1. k9s — Kubernetes resource browser](#1-k9s--kubernetes-resource-browser) · L30–60 — evidence from k9s.
- [2. lazygit — git client](#2-lazygit--git-client) · L62–97 — evidence from lazygit.
- [3. lazydocker — Docker / compose dashboard](#3-lazydocker--docker--compose-dashboard) · L99–118 — evidence from lazydocker.
- [4. gitui — fast git client](#4-gitui--fast-git-client) · L120–137 — evidence from gitui.
- [5. yazi — async file manager](#5-yazi--async-file-manager) · L139–165 — evidence from yazi.
- [6. btop++ — system monitor](#6-btop--system-monitor) · L167–191 — evidence from btop.
- [7. helix — modal editor](#7-helix--modal-editor) · L193–220 — evidence from helix.
- [8. Archetype catalog (other TUIs)](#8-archetype-catalog-other-tuis) · L222–253 — naming an exemplar for a concept or archetype.
- [9. Screenshot corpus (test set for screenshot audits)](#9-screenshot-corpus-test-set-for-screenshot-audits) · L255–281 — test images for the screenshot pipeline.

Each app was read in source at the commit below (default config and docs too) and six were run live in tmux, 2026-10 (`[live]` = exact captured text, `[src]` = read in source). k9s was not run (no cluster): source, README and official screenshot only. `UNVERIFIED` = not checked; verify before relying on it.

| § | App | Version / commit | Language · UI library | Primary archetype | Config dir (macOS / Linux) | Keys remappable | Mouse default |
|---|---|---|---|---|---|---|---|
| 1 | k9s | v0.51.0 · `7064f96` | Go · `derailed/tview` fork + `tcell/v2` | I table explorer (+ E logs, H xray, G `:`) | `~/Library/Application Support/k9s` / `$XDG_CONFIG_HOME/k9s` (`K9S_CONFIG_DIR`) | no (only add `hotkeys.yaml`, plugins) | off (`ui.enableMouse`) |
| 2 | lazygit | v0.65.1 · `ff375b1` | Go · `jesseduffield/gocui` + `lazycore/boxlayout` | A + B | `~/Library/Application Support/lazygit/config.yml` / `~/.config/lazygit/config.yml` | yes (`keybinding.*`) | on |
| 3 | lazydocker | v0.25.2 · `7e7aadc` | Go · same gocui fork | A + B + E | `~/Library/Application Support/jesseduffield/lazydocker/config.yml` / `~/.config/lazydocker/config.yml` | no | on |
| 4 | gitui | v0.28.1 · `2fa693c` | Rust · ratatui 0.30 + crossterm 0.29 | tabs + B | `~/.config/gitui/` (both) | yes (`key_bindings.ron`) | none observed (`UNVERIFIED`) |
| 5 | yazi | v26.9.1 · `d0798b4` | Rust · ratatui fork, tokio, Lua plugins | C Miller columns | `~/.config/yazi/` (`YAZI_CONFIG_HOME`) | yes (`keymap.toml`, prepend/append) | on (`mouse_events`) |
| 6 | btop++ | v1.4.7 · `d3389d7` | C++20 · custom ANSI renderer | A dashboard (+ I proc table) | `~/.config/btop/btop.conf` | no (opt-in `vim_keys`) | on |
| 7 | helix | 25.07.1 · `ba40e54` | Rust · in-tree `helix-tui` (ratatui fork) + crossterm | D editor (+ G pickers) | `~/.config/helix/` (+ `.helix/` per workspace) | yes (`[keys.normal]`) | on (`mouse = true`) |

Permalink pattern for every `[src]` claim: `https://github.com/<org>/<repo>/blob/<sha>/<path>`.

---

## 1. k9s — Kubernetes resource browser

**Regions** (vertical flex in `internal/view/app.go layout()` [src]): header 7 rows (cluster info · context key hints · logo) | prompt 3 rows, inserted only while `:` or `/` is active | content table | crumbs 1 row | flash 1 row.

```text
 Context: prod-eu   <?>      Help       <0> all          (logo)
 Cluster: prod-eu   <ctrl-d> Delete     <1> default
 K9s Rev: v0.51.0   <d>      Describe                    <- hints: max 6 rows, then a new column
╭──────────────────────── Pods(all)[12] ────────────────────────╮
│ NAMESPACE  NAME              READY STATUS  RESTARTS CPU  MEM  AGE │
╰───────────────────────────────────────────────────────────────╯
  <pods>                                       <- crumbs (view stack)
  (flash: level + message, clears after 6 s)
```

**Copy** — why it works:
1. Header hints are the **registered actions of the current view** (`visible=true` only) → hints can never drift from behavior (`internal/ui/menu.go`).
2. `:resource` command + aliases (`:po`, `:dp`, `:svc`, `:ctx`) → O(1) navigation across hundreds of kinds without menus; crumbs show the stack; `[` `]` history, `-` last view.
3. Marks (`space`, `ctrl+space` range) + bulk verbs with counted confirmation `Delete 3 marked pods?`.
4. `readOnly` config removes dangerous bindings entirely: safety by absence.
5. Loading ≠ empty ≠ error: `Synchronizing …` until the informer cache syncs, only then `No resources found …` (`internal/view/browser.go`).

**Don't copy**: built-in keys cannot be remapped and `ctrl+d` delete clashes with tmux/terminals (issue #625, 35 +1); emoji in flash/prompt (`😡`, `🐶>`) are width hazards (disable with `noIcons`); misleading `Ruroh? 'V1/pods' command not found` on expired auth (#3730) — say "credentials expired" instead (see `../assets/mockups/table-explorer/pods--error--80x24.mock`).

**Small terminals**: no min-size screen; `ctrl+e` hides the 7-row header, `ctrl+g` the crumbs, `ctrl+w` toggles wide columns (`derived:` hints simply truncate).

**Config / theme**: `config.yaml`, `aliases.yaml`, `hotkeys.yaml`, `plugins.yaml`, `views.yaml`; skins `$XDG_DATA_HOME/k9s/skins/<name>.yaml` (YAML, JSON schema `internal/config/json/schemas/skin.json`; samples in the repo's `skins/`). `k9s info` prints all paths. Refresh `refreshRate` 2 s.

**Screenshots**: `screen_po.png` 1138x542 (pods table + header; old v0.1.6 build), `screen_logs.png` 1137x565, `k9s_xray.png` 1024x500, `screen_dp.png` 1136x543 — URLs in §9.

---

## 2. lazygit — git client

**Regions** ([live] 120x36): left stack of 5 numbered side windows (each with tabs in its title and a `n of m` counter), right main view (diff/log of the selected item), command log under it, 1-row options line. Side width `gui.sidePanelWidth: 0.3333`; rounded borders, focused border green bold.

```text
╭─[1]─Status───────────────────────────╮╭─[0]─Unstaged changes──────────────────
│repo → main                           ││diff --git a/f1.txt b/f1.txt
╰──────────────────────────────────────╯│@@ -1 +1,2 @@
╭─[2]─Files - Worktrees - Submodules───╮│ line 1
│▼ /                                   ││+mod
│   M f1.txt                           ││
╰───────────────────────────────2 of 5─╯│
╭─[3]─Local branches - Remotes - Tags──╮│
╰───────────────────────────────1 of 2─╯╰──────────────────────────────────────
Stage: <space> | Commit: c | Edit: e | Stash: s | Discard: d | Reset: D | Keybindings: ?      Donate Ask Question 0.65.1
```
(trimmed tmux capture at 120x36; throwaway demo repo, right side cut)

**Copy**:
1. Two-tier help: context-sensitive options line + `?` searchable keybindings menu (`--- Local ---` first, `1 of 65`, `enter` runs the row).
2. Numbered window titles `[n]` double as jump keys; counters `x of y` show list position.
3. Tabs inside a window (`Files - Worktrees - Submodules`, `[` `]`) → 10+ views in 5 slots.
4. One verb per letter across contexts (`d` destroy, `space` primary, `enter` go in, `o` open, `e` edit) — explicit design principle (VISION.md).
5. Disabled actions stay visible with a reason; menus show a tooltip box for the selected item; command log teaches the git commands it ran.

**Don't copy**: `Label: key | Label: key` footer is verbose at 80 cols (truncates to `… | Edit: e | ...` at 70); `,`/`.` for paging and `<`/`>` for top/bottom diverge from every other exemplar.

**Responsive** [src + live]: portrait (side windows on top) when `width <= 84 && height >= 46` (`portraitModeAutoMaxWidth`, `portraitModeAutoMinHeight`); short heights collapse unfocused side windows to 1-row title bars `╶─[3]─Local branches…─╴`; main view splits side-by-side when width ≥ 200 or height ≤ 30 (`mainPanelSplitMode: flexible`); below `max(9, sideWindows+4)` rows or 10 cols → one box `Not enough space to render panels` (`pkg/gui/layout.go`). `+`/`_` cycle screen modes (normal/half/full).

**Feedback**: spinner `●∙∙ ∙●∙ ∙∙● ∙●∙` at 180 ms; toasts when the affected item is off-screen; `z`/`Z` undo/redo via reflog; confirm on quit only with `confirmOnQuit: true`.

**Config / theme**: `config.yml` (+ repo-level `.git/lazygit.yml`, `.lazygit.yml`; JSON schema `schema/config.json`); theme under `gui.theme` as color lists (`activeBorderColor: [green, bold]`); `nerdFontsVersion: ""` (icons off by default).

**Screenshots**: README hero 1072x1090 (§9). Demo GIF paths `UNVERIFIED`.

---

## 3. lazydocker — Docker / compose dashboard

**Regions** ([live] 120x36): lazygit shell — left numbered resource lists (`[1]` Project and `[2]` Services only inside a compose project, `[3]` Containers, `[4]` Images, `[5]` Volumes, `[6]` Networks), right tabbed main view `Logs - Stats - Env - Config - Top`, 1-row static hint line `PgUp/PgDn: scroll, b: view bulk commands, q: quit, x: menu, ← → ↑ ↓: navigate`.

**Copy**:
1. Shared design language with lazygit — knowing one teaches the other.
2. `x` (or `?`) opens a per-panel menu listing every key of the focused panel, then global keys after a blank separator — a cheap alternative to a full help screen.
3. Tabbed detail for a live item (Logs/Stats/Env/Config/Top) = dashboard + detail in one pane.
4. Bulk actions behind one `b` menu instead of multi-select.
5. Statuses as words + color (`running (healthy)`, `restarting`, `exited`; `containerStatusHealthStyle: long|short|icon`).

**Don't copy**: static footer that does not change with focus; keybindings not configurable; no copy from logs (issue #167, 25 +1).

**Responsive**: floor 9 rows / 10 cols; portrait when `width <= 84 && height > 45` (`pkg/gui/arrangement.go`); `screenMode: normal|half|fullscreen`.

**Config / theme**: `config.yml`, `gui.theme.{activeBorderColor, inactiveBorderColor, selectedLineBgColor, optionsTextColor}`; `customCommands`; `logs.{timestamps, since: '60m', tail}`.

**Screenshots**: README hero 726x413; demo GIF `docs/resources/demo3.gif` (§9).

---

## 4. gitui — fast git client

**Regions** ([live] 110x32): 2-row tab bar (`Status [1] | Log [2] | Files [3] | Stashing [4] | Stashes [5]`, repo path right, left-truncated with `[…]`), tab body (Status = Unstaged / Staged lists left, Diff right), 1..n-row command bar `Stage All [a] Stage [Enter] … more [.]`. Popups use thick `┏━┓` borders vs thin `┌─┐` panes.

**Copy**:
1. Key shown in every tab label (`Status [1]`).
2. `more [.]` command bar: 1 row by default, `.` expands to the full multi-row list (`cmdbar.rs`).
3. Popup border weight distinguishes modal layers from panes.
4. Help popup shows a one-line description under the selected command.
5. Disabled commands greyed (`disabled_fg`) rather than hidden.

**Don't copy**: arrows-only default (vim keys need `vim_style_key_config.ron`); `h` = help clashes with vim left; no too-small handling — at 60x15 the tab bar is cut mid-label `Stashing [4]  |`, at 30x6 panes shrink to a few chars [live].

**Config / theme**: `~/.config/gitui/key_bindings.ron` (RON, `-k` flag), `key_symbols.ron` (rename `⏎`, `⇧`), `theme.ron` (`-t` flag).

**Screenshots**: `s00-diff.png` and `s01-log.png` 4064x2338 (Retina, window chrome), `rebase.png` 2194x1476, `light-theme.png` 1540x1160 (§9).

---

## 5. yazi — async file manager

**Regions** ([live] 120x34): header (cwd left, tabs right when >1), three columns `ratio = [1, 4, 3]` parent | current | preview, status bar (` NOR ` mode chip, size, name | permissions, `Top`/`NN%`/`Bot`, `index/total`). Overlays: which-key band, help, input, confirm, pick, tasks (`w`), spot (`tab`).

```text
~/project                                               (tabs)
  docs        │ src                          │ preview: text, image,
  repo        │ f1.txt   <- cursor row       │ archive list, dir listing
 NOR  96B  src                      drwxr-xr-x  Top   1/5
```

**Copy**:
1. Prefix chords + which-key (`g` goto, `,` sort, `c` copy, `m` linemode, `t` tabs): large key space, still discoverable; every binding has a `desc` used by help and which-key.
2. Help (`~`/`F1`) is a filterable, **executable** list — a command palette for free.
3. Async everything + task manager: the UI never blocks on I/O.
4. Filter (`f`, live narrowing) vs find (`/` `?` + `n`/`N`) are separate tools.
5. Reversible delete by default (`d` trash, `D` permanent; dialog `Trash 1 selected file?`, `[Y]es (N)o`).

**Don't copy**: no min-size handling — at 30x8 the status bar overlaps itself [live]; Nerd Font icons on by default (decoration must not carry meaning; see [visual-vocabulary.md](visual-vocabulary.md) V7); help on `~`/`F1` because `?` is find-previous (fine for yazi, but `?` is the cross-app default).

**Responsive**: pure ratio shrink — at 80 cols the parent column elides names with `…`; `ratio = [0, 1, 0]` single-column is implied by ratio semantics but `UNVERIFIED`.

**Config / theme**: `yazi.toml`, `keymap.toml` (`{ on = ["g","g"], run = "arrow top", desc = "Go to top" }`, `prepend_keymap`), `theme.toml` (+ `theme-dark.toml`/`theme-light.toml` chosen by terminal mode), flavors in `~/.config/yazi/flavors/*.yazi`, `init.lua`, `package.toml`; schemas at `yazi-rs.github.io/schemas/*.json`.

**Screenshots**: none static in the README (only an MP4, §9) — use `SKILL_DIR/scripts/capture_tui.sh` for own captures.

---

## 6. btop++ — system monitor

**Regions** ([live] 120x40 and 80x24): boxes `cpu` (top, full width), `mem` (+ `disks`) and `net` (left column), `proc` (right, tall). Rounded borders with **title chips embedded in the borders** (`┤¹cpu├`, `┤menu├`, `┤preset *├`, clock, `┤- 2000ms +├`; proc bottom border `┤↑ select ↓├┤info ↵├┤terminate├┤kill├┤signals├ 0/1586`). The superscript number is the box's toggle key.

**Copy**:
1. Titles as toolbars: toggles and context hints live in the borders and appear only when relevant (selection hints only when a process is selected).
2. Explicit too-small screen with **current and needed** size, recomputed from enabled boxes, still responsive to `q` and `1`-`4`:
   ```text
           Terminal size too small:
             Width = 70 Height = 20
          Needed for current config:
            Width = 80 Height = 24
   ```
   Box minimums: Cpu 60x8, Gpu 41x8, Mem 36x10, Net 36x6, Proc 44x16 (`btop_draw.cpp`, `btop_tools.cpp`).
3. Presets (`p`/`P`) = saved layouts, one key to switch.
4. Graceful compression at the minimum: abbreviated labels (`U`/`A`/`C`/`F`), no per-column graphs at 80x24.
5. Rendering ladder: braille → block → tty (`graph_symbol`, `-t/--tty`, `-l/--low-color`).

**Don't copy**: help on `h` and kill on `k` (conflicts with vim keys; `vim_keys` moves them to shift); no visible footer hints when nothing is selected.

**Config / theme**: `~/.config/btop/btop.conf` (key = value, rewritten on exit; `-c FILE`), themes `~/.config/btop/themes/*.theme` and `/usr/local/share/btop/themes` (`theme[main_bg]="#282a36"`), `color_theme`, `theme_background`, `truecolor`, `rounded_corners`, `update_ms = 2000`.

**Screenshots**: `normal.png`, `main-menu.png`, `options-menu.png`, `tty.png`, `alt.png` 1045x658; `help-menu.png` 919x738 (§9).

---

## 7. helix — modal editor

**Regions** ([live] 100x30): buffer with gutters (diagnostics | line numbers | diff), `~` past EOF; statusline (left: mode, spinner, file name, `[+]`; right: diagnostics, selections, register, position, encoding; separator `│`); 1-row message line. Optional bufferline (`"never"` by default), splits (`ctrl+w v/s`), file explorer, pickers (centered, with preview).

```text
    1  line 1
    2 |mod                                   <- "|" diff marker in the gutter
    ~
 NOR   f1.txt [+]                     1 sel  1:2
 Loaded 2 files.                              <- message line
```

**Copy**:
1. Which-key ("auto-info") after `idle-timeout = 250 ms`: zero cost for experts, discoverable for novices; box titled with the mode (`Goto`, `Space`), pending key echoed.
2. Every key maps to a named command; `Space ?` palette lists all commands with their keys; `:` prompt has fuzzy completion + a doc box.
3. Selection-first (noun then verb): the selection is visible before the action → fewer mistakes, no confirmation dialogs needed.
4. Pickers with live preview for files, buffers, symbols, diagnostics, jumplist (`Space '` reopens the last).
5. Errors on the message line instead of modals: `'quit': 1 unsaved buffer remaining: ["f1.txt"]` [live].

**Don't copy**: no single-key quit is right for an editor, wrong for a browser/dashboard; popup/picker keymaps not remappable.

**Small terminals**: no minimum; at 40x8 the statusline drops right-hand items and keeps `NOR f1.txt [+]  1 sel 1:2` [live]; popups clamp (`derived:`).

**Config / theme**: `config.toml`, `languages.toml`, themes `~/.config/helix/themes/<name>.toml` (`theme = "name"` or `:theme`); `mouse = true`, `scrolloff = 5`, `auto-info = true`, `idle-timeout = 250`, `bufferline = "never"`, `cursorline = false`.

**Screenshot**: `screenshot.png` 2023x1530 (§9).

---

## 8. Archetype catalog (other TUIs)

Archetype letters as in [layout-archetypes.md](layout-archetypes.md) §1. Rows k9s…helix are verified (§1-7); **every other row is from general knowledge and `UNVERIFIED`** (sources not checked).

| App | Archetype(s) | One-line reason | Verified |
|---|---|---|---|
| k9s | I (primary), E logs, H xray, G `:` | single resource table, command-driven view switching | yes |
| lazygit | A + B | 5 stacked list windows driving a main view; popups for forms | yes |
| lazydocker | A + B + E | same shell; tabbed detail incl. logs/stats | yes |
| gitui | B + tabs | 5 tabs; list + diff inside; popups for forms | yes |
| yazi | C (+ B preview) | parent / current / preview | yes |
| btop++ | A + I | live graph boxes, one interactive table | yes |
| helix | D (+ G) | modal buffer + statusline, pickers, which-key | yes |
| htop | I + A-lite | sortable process table, header meters, F-key footer (`F1 Help … F10 Quit`) | UNVERIFIED |
| ncdu | H + I | size tree/list browser, one pane | UNVERIFIED |
| tig | B (+ E) | log/status/blame list → pager split | UNVERIFIED |
| mutt / neomutt | B + I | index list + pager, optional sidebar | UNVERIFIED |
| ranger | C | the original Miller-columns manager | UNVERIFIED |
| nnn | I / H | single-pane file list, context letters | UNVERIFIED |
| lnav | E | log viewer with histogram, filters, SQL | UNVERIFIED |
| posting | F + B | request form/editor + response pane, palette `ctrl+p` | UNVERIFIED |
| harlequin | G + I + D | SQL editor + results grid + catalog tree | UNVERIFIED |
| dolphie | A + I | MySQL dashboard panels + process table | UNVERIFIED |
| spotify-player | B + A-lite | playlist/track lists with a playback bar | UNVERIFIED |
| bottom (btm) | A | widget grid (cpu/mem/net/proc), expandable widget | UNVERIFIED |
| gdu | H + I | disk-usage tree/list browser | UNVERIFIED |
| glow | E (pager) + B | markdown viewer with a file list | UNVERIFIED |
| superfile | C (+ A) | multi-panel file manager | UNVERIFIED |
| atuin (search) | G | fuzzy history palette, inline or full screen | UNVERIFIED |
| zellij | A (multiplexer chrome) | tab bar + mode-colored key-hint bar, floating panes | UNVERIFIED |

---

## 9. Screenshot corpus (test set for screenshot audits)

Exact URLs and pixel sizes (measured 2026-10). Use them to calibrate screenshot-path audits ([audit-protocol.md](audit-protocol.md)): `uv run SKILL_DIR/scripts/prep_screenshot.py IMAGE -o OUTDIR` then describe with [prompts/describe-tui.md](prompts/describe-tui.md). Cell grids are not given; estimate with `prep_screenshot.py` (`grid.json`).

| ID | App | URL | Pixels | Shows | Caveats |
|---|---|---|---|---|---|
| k9s-pods | k9s | `https://raw.githubusercontent.com/derailed/k9s/master/assets/screen_po.png` | 1138x542 | header (cluster info, hints, logo) + pods table | old v0.1.6 build |
| k9s-logs | k9s | `https://raw.githubusercontent.com/derailed/k9s/master/assets/screen_logs.png` | 1137x565 | log view | |
| k9s-xray | k9s | `https://raw.githubusercontent.com/derailed/k9s/master/assets/k9s_xray.png` | 1024x500 | xray tree (archetype H) | logo, not a screenshot: use `screen_po.png` |
| k9s-deploy | k9s | `https://raw.githubusercontent.com/derailed/k9s/master/assets/screen_dp.png` | 1136x543 | deployments table | |
| lazygit-hero | lazygit | `https://user-images.githubusercontent.com/8456633/174470852-339b5011-5800-4bb9-a628-ff230aa8cd4e.png` | 1072x1090 | full layout (side windows + main + options line) | resolves to a logo, not a screenshot: use `https://raw.githubusercontent.com/jesseduffield/lazygit/assets/demo/commit_and_push-compressed.gif` |
| lazydocker-hero | lazydocker | `https://user-images.githubusercontent.com/8456633/59972109-8e9c8480-95cc-11e9-8350-38f7f86ba76d.png` | 726x413 | lists + tabbed main | resolves to a logo, not a screenshot: use `lazydocker-demo` |
| lazydocker-demo | lazydocker | `https://raw.githubusercontent.com/jesseduffield/lazydocker/master/docs/resources/demo3.gif` | — | animated demo | GIF; not for stills |
| gitui-diff | gitui | `https://raw.githubusercontent.com/gitui-org/gitui/master/assets/screenshots/s00-diff.png` | 4064x2338 | Status tab: lists + diff, command bar chips | Retina, window chrome |
| gitui-log | gitui | `https://raw.githubusercontent.com/gitui-org/gitui/master/assets/screenshots/s01-log.png` | 4064x2338 | Log tab | Retina, window chrome |
| gitui-rebase | gitui | `https://raw.githubusercontent.com/gitui-org/gitui/master/assets/rebase.png` | 2194x1476 | rebase view | |
| gitui-light | gitui | `https://raw.githubusercontent.com/gitui-org/gitui/master/assets/light-theme.png` | 1540x1160 | light theme | light-mode test case |
| btop-normal | btop | `https://raw.githubusercontent.com/aristocratos/btop/main/Img/normal.png` | 1045x658 | all four boxes | |
| btop-menu | btop | `https://raw.githubusercontent.com/aristocratos/btop/main/Img/main-menu.png` | 1045x658 | main menu overlay | |
| btop-help | btop | `https://raw.githubusercontent.com/aristocratos/btop/main/Img/help-menu.png` | 919x738 | help popup | |
| btop-options | btop | `https://raw.githubusercontent.com/aristocratos/btop/main/Img/options-menu.png` | 1045x658 | options popup | |
| btop-tty | btop | `https://raw.githubusercontent.com/aristocratos/btop/main/Img/tty.png` | 1045x658 | 16-color tty mode | 16-color test case |
| btop-alt | btop | `https://raw.githubusercontent.com/aristocratos/btop/main/Img/alt.png` | 1045x658 | alternative layout/theme | |
| helix-main | helix | `https://raw.githubusercontent.com/helix-editor/helix/master/screenshot.png` | 2023x1530 | editor + statusline + popup | |
| yazi-video | yazi | `https://github.com/sxyazi/yazi/assets/17523360/92ff23fa-0cd5-4f04-b387-894c12265cc7` | — | MP4 demo | not usable for stills (gap) |

Gaps: no static yazi screenshot (capture your own with `SKILL_DIR/scripts/capture_tui.sh -s 120x34 -- yazi`); lazygit/lazydocker GIF paths other than `demo3.gif` `UNVERIFIED`; `screen_po.png` is an old v0.1.6 build, so its header differs from v0.51.0.
