# H. Tree browser

Part of [layout-archetypes.md](../layout-archetypes.md) (rules L1–L14 in §2). Sketch rows: `H` header, `M` message line, `K` keybar. § numbers on the **Exemplars** line are sections of [exemplars.md](../exemplars.md).

**Use** when containment is the point (disk usage, dependency trees, k8s ownership). **Avoid** deep trees where siblings matter more than ancestors (use C).

```text
H  Usage │ ~/src · 48.2 GiB · 212,904 files            scanned in 4.1s
╭─ ~/src ──────────────────────────────────────────── sort size ↓ ─╮
│    SIZE     % SHARE             NAME                             │
│   21.4G   44% ███████░░░░░░░░░  ├─ ▾ monorepo/                   │
│ ❯  9.8G   46% ███████░░░░░░░░░  │  ├─ ▸ node_modules/            │
╰─────────────────────────────────────────────────────────── 3/13 ─╯
M  ~/src/monorepo/node_modules · 9.8 GiB · 184,211 files · modified 3d ago
```
- **Columns**: numbers first (fixed, right-aligned), then share bar relative to the **parent** + `%` printed, then the tree column (flex). Guides `├─ └─ │` in `border.default`, expanders `▸`/`▾` in `fg.muted`, containers in `accent.primary`.
- **Keys**: `→`/`l` expand (or enter), `←`/`h` collapse (or go to parent), `enter` open, `space` mark, `s` sort, `d` delete with confirmation (see [interaction.md](../interaction.md) §6).
- **Responsive**: 80x24 = 16-cell bars, 3 numeric columns (`diskusage--normal--80x24`); 120x30 = 30-cell bars + FILES + MODIFIED (`--120x30`); 170x40 = add a detail pane for the selected node (largest files). Deep nesting: indent 3 cells per level; beyond the available width, collapse ancestors into a breadcrumb in the title.
- **States**: busy scan (`diskusage--busy--80x24`): totals only for finished subtrees, `%` and bars hidden under unfinished parents, queued rows `·` faint, spinner on live rows, `order frozen until scan ends` in the title, `d delete` disabled, `esc stop scan`.
- **Pitfalls**: re-sorting while the user navigates; bars relative to the root (children look empty); hiding the numbers behind bars only.
- **Exemplars**: k9s xray, ncdu/gdu (catalog, unverified).
