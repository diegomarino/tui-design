# D. Editor + statusline + which-key

Part of [layout-archetypes.md](../layout-archetypes.md) (rules L1–L14 in §2). Sketch rows: `H` header, `M` message line, `K` keybar. § numbers on the **Exemplars** line are sections of [exemplars.md](../exemplars.md).

**Use** when the main object is a long text the user edits with many commands. **Avoid** forcing modal editing on users who only fill fields (use F).

```text
 gutter │ buffer (cursor line on bg.surface, selection on text-selection.bg)
        │                           ╭─ Goto ──────────────╮ which-key, bottom-right,
        │                           │ g  line <n>, else … │ after a prefix key
        │                           ╰───────────────── g ─╯
SL  NOR   internal/webhook/retry.go [+]        ● 1  ● 1   1 sel  13:9  g
M   (command results / errors)
```
- **Regions**: optional buffer tabs (row 0, helix `bufferline = "never"` by default [src]); gutter = diagnostic (1) + line number (3-4, right-aligned) + diff marker `▍` (1) + space; statusline left = mode chip, path, `[+]`; right = diagnostics counts, selections, `line:col`, pending keys; last row = message line.
- **Focus**: the buffer; popups/pickers take focus and give it back on `esc`. Splits move with `ctrl+w h/j/k/l`.
- **Discoverability**: which-key box appears after a prefix key and `idle-timeout = 250 ms` (helix), anchored bottom-right, ~40 cols single column (`code--normal--80x24`) or ~60 cols two columns for big menus (`Space`, `code--normal--120x30`); trailing `…` marks a submenu.
- **Responsive**: 80x24 = no bufferline, which-key single column; 120x30 = bufferline + 2-column which-key; 170x40 = vertical split or side file tree. Narrow: statusline drops right-hand items first (helix at 40x8 keeps `NOR f1.txt [+] 1 sel 1:2` [live]). No minimum; popups clamp to the screen.
- **States**: error = message line in `status.error` with the fix (`✗ 1 unsaved buffer: retry.go  :w save · :q! discard`, `code--error--80x24`), not a modal; diagnostics inline at line end, truncated with `…`.
- **Pitfalls**: global single-letter keys firing while typing in insert mode; destructive commands without undo (helix relies on undo instead of confirmations [src]); statusline crammed with low-value items.
- **Exemplars**: helix (§7).
