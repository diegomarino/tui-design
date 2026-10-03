# A. Multi-pane dashboard

Part of [layout-archetypes.md](../layout-archetypes.md) (rules L1–L14 in §2). Sketch rows: `H` header, `M` message line, `K` keybar. § numbers on the **Exemplars** line are sections of [exemplars.md](../exemplars.md).

**Use** for monitoring several live sources where noticing beats navigating. **Avoid** when the user mostly acts on one item (use B or I) or when sources are not live.

```text
H  Pulse │ build-03 · linux 6.8 …                 14:22:07
╭─ 1 cpu ──────────────── graph + per-core gauges ───────╮
╰────────────────────────────────────────────────────────╯
╭─ 2 mem ──────────╮╭─ 4 proc (focus: the only table) ───╮
╰──────────────────╯│                                    │
╭─ 3 net ──────────╮│                                    │
╰──────────────────╯╰─────────────────────────── 1/412 ──╯
M  ▲ cpu above 60% for 5m · since 14:17
K  ↑↓ select  enter details  / filter  s sort  k kill  1-4 boxes   ? help  q quit
```
- **Focus**: only one interactive pane (btop: the proc box owns selection [src]); other boxes are read-only. Number keys toggle boxes; `p` cycles saved layouts (btop presets).
- **Keys**: `1`-`n` show/hide box (number shown in the title), `p`/`P` preset, `+`/`-` sample interval, `/` filter the table, `s`/`←→` sort column.
- **Responsive**: 80x24 = every box, labels abbreviated, 4-row graphs, table 5 columns (`sysmon--normal--80x24`); 120x30 = taller graph, USER and COMMAND columns, disks in mem box (`--120x30`); 170x40 = per-core graphs, per-process sparklines wider, a 5th box. Min = sum of enabled box minimums; below it [§2.2](../layout-archetypes.md#22-the-too-small-screen).
- **States**: busy = boxes drawn with axes, values `…`; degraded = header `STALE 42s` chip, everything `fg.faint`, sample time in titles, `k kill` disabled (`sysmon--error--80x24`).
- **Pitfalls**: color-only gauges (always print `64%`); graphs without a time axis (`-3m … now`); every box focusable (Tab cycling through read-only boxes is noise); jittering widths when numbers change (fixed numeric widths).
- **Exemplars**: btop, lazydocker ([exemplars.md](../exemplars.md) §6, §3).
