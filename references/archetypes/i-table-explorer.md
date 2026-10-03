# I. Table / grid explorer

Part of [layout-archetypes.md](../layout-archetypes.md) (rules L1–L14 in §2). Sketch rows: `H` header, `M` message line, `K` keybar. § numbers on the **Exemplars** line are sections of [exemplars.md](../exemplars.md).

**Use** for many records with comparable attributes and sort/filter needs. **Avoid** when each record needs prose (use B) or when the data are streamed events (E).

```text
H  Kube │ prod-eu › payments › pods                    admin@prod-eu
╭─ Pods(payments)[9/18] ──────────────────────────────────── /api ─╮
│   NAME↑                     READY STATUS        RS  CPU   MEM AGE│
│ ❯ api-gateway-7f9c4b-b81dm    1/1 Running        0  41m 212Mi 6d │
│   api-worker-6b9fd-2mncr      0/1 ✗ CrashLoop…  14   0m  18Mi 47m│
╰──────────────────────────────────────────────────────────────────╯
M  ✓ deleted pod api-worker-6b9fd-zz01m · 4s ago
K  enter open  l logs  d describe  s shell  ctrl+d delete   : command  ? help
```
- **Header row** in `table.header bold`; the sort column header in `accent.primary` with `↑`/`↓`. Only non-normal statuses get a glyph + color (`✗` error, `▲` warning, `·` done/faint); normal rows stay `fg.default` so failures pop. Thresholded cells color only the cell (`RS 14` warning, `READY 0/1` error).
- **Keys**: `↑↓`/`jk`, `g`/`G` ends, `/` filter (title shows `/api` and `[9/18]`), `shift+<letter>` sort by column (k9s `shift-n/a/s` [src]), `space` mark, `ctrl+space` range, verbs on the marked set (`ctrl+d delete 2`), `enter` drill down (view stack + breadcrumb in the header), `:` command / resource switch.
- **Responsive**: 80x24 = 8 columns, NAME flex (`pods--normal--80x24`); 120x30 = + IP, NODE, marks, sort by CPU (`--120x30`); 170x40 = + LABELS/NOMINATED columns or a describe side pane. Column priority list decides what drops first; k9s exposes a "wide" toggle (`ctrl-w`) and a hideable header (`ctrl-e`) to regain space [src].
- **States**: loading = `Synchronizing pods in "payments"…` in the message line, table frame and header drawn, no "No resources found" until synced (k9s [src]); error/stale = banner row inside the table (`✗ Unauthorized: credentials for prod-eu expired 3m ago`), rows `fg.faint`, header `STALE 3m`, mutating verbs disabled (`pods--error--80x24`).
- **Striping**: wide tables with ≥ ~8 rows may stripe alternate records in `bg.stripe` ([§2.4](../layout-archetypes.md#24-zebra-striping-tables-logs-long-lists)); never color rows by status.
- **Pitfalls**: coloring whole rows (rainbow tables); misaligned units (`12m` vs `0.012`); sort that resets after refresh; cursor jumping when rows insert above it (keep selection by id).
- **Exemplars**: k9s (§1), btop proc box (§6), htop (catalog, unverified).
