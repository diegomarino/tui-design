# B. List + detail

Part of [layout-archetypes.md](../layout-archetypes.md) (rules L1–L14 in §2). Sketch rows: `H` header, `M` message line, `K` keybar. § numbers on the **Exemplars** line are sections of [exemplars.md](../exemplars.md).

**Use** when the operator picks one item from tens to hundreds and reads or acts on it. **Avoid** for one-shot comparison across many attributes (use I).

```text
H  Review │ 1 Inbox  2 Mine (3)  3 Team (12)        acme/payments
╭─ Inbox (7) ─ focus ─────╮╭─ #482 ──────────────────── open ─╮
│ ❯ ✓ #482 Retry webho… 2h ││ title / meta / fields / text    │
╰──────────────── 1 of 7 ─╯╰──────────────────────────────────╯
M  ✓ merged #473 into main · 4m ago
K  ↑↓ select  enter open  a approve  / filter  tab pane      ? help  q quit
```
- **Focus**: list → detail → (list) with `tab`/`shift+tab`, `h`/`l`, or `1`-`n` jump keys printed in titles (lazygit `[1]`…`[5]`); `enter` drills into the item (pushes a view, `esc` pops). Detail follows the list cursor without stealing focus.
- **Keys**: `↑↓`/`jk` move, `enter` open, item verbs on letters (`a`, `c`, `m`), `/` filter, `[`/`]` tabs inside a pane.
- **Responsive**: 80x24 = list 36 cols (≈45 %), one-line rows, detail truncates sections with `…3 more` (`prs--normal--80x24`); 120x30 = list gets AUTHOR column + header row, detail adds Checks (`--120x30`); 170x40 = third pane (diff/preview) or side-by-side detail sections. ≤84 cols and ≥46 rows → stack list over detail (lazygit portrait). Short terminals: collapse unfocused panes to title bars. Floor ≈ 9 rows (lazygit/lazydocker).
- **States**: empty = list says why and where to go (`2 your open PRs (3)`), detail shows faint "No pull request selected" (`prs--empty--80x24`); busy = list rows as `░` skeleton at final widths; error = message in the list pane, detail keeps last selection marked stale.
- **Pitfalls**: list rows that wrap (keep 1 line, depth goes to detail); detail that resets scroll on every refresh; selection lost after refresh (select by stable id, not index).
- **Exemplars**: lazygit, gitui, lazydocker (§2, §4, §3).
