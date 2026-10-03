# G. Command palette overlay

Part of [layout-archetypes.md](../layout-archetypes.md) (rules L1–L14 in §2). Sketch rows: `H` header, `M` message line, `K` keybar. § numbers on the **Exemplars** line are sections of [exemplars.md](../exemplars.md).

**Use** when there are more actions than a footer can list (≈15+), as a universal entry point and as executable help. **Avoid** as the only way to reach frequent actions.

```text
 (app behind: every glyph fg.faint, highlights removed)
      ╭─ Command palette ─────────────────── ctrl+p ─╮
      │ ❯ rest█                             4 of 112 │  <- input + count
      ├──────────────────────────────────────────────┤
      │ Services                                     │  <- group (fg.muted bold)
      │ ❯ Restart service      api-gateway        r  │  <- match chars search.match
      ├──────────────────────────────────────────────┤
      │ Rolling restart of api-gateway: 3 replicas…  │  <- description of selection
      ╰──────────────────────────────────────────────╯
K  ↑↓ select  enter run  tab complete  ctrl+u clear                  esc close
```
- **Geometry**: centered horizontally, top at ~row 3 (not vertically centered, so results grow downward); width `min(cols - 16, 80)`; height fixed while open (empty/no-match uses the same box, `palette--empty--80x24`).
- **Content**: each row = label (fuzzy matched chars in `search.match bold`), context (`fg.muted`), bound key right-aligned in `keyhint.key` — the palette teaches the shortcuts. Empty query shows `Recent` then `All commands` (`palette--normal--120x30`). Optional prefixes (`>` commands, `@` items, `:` views) listed in the bottom band.
- **Focus**: steals all input until `esc`/`enter`; footer switches to palette hints; the app behind is faded (all `fg.faint`, no selection), never interactive.
- **Responsive**: 80x24 = 64 wide, 8 result rows; 120x30 = 80 wide, 15 rows + category column; 170x40 = add a preview pane at the right of the results (helix pickers) — toggle it off below ~100 cols (helix `ctrl+t`).
- **Pitfalls**: results that reorder while typing the same prefix (stable ordering for ties); no indication of bound keys; executing on single click/hover; palette that cannot list disabled commands (show them faint with the reason).
- **Exemplars**: helix `Space ?` and pickers, yazi help-as-palette, lazygit `?` searchable keybindings menu (§7, §5, §2).
