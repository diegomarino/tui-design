# E. Log / stream viewer

Part of [layout-archetypes.md](../layout-archetypes.md) (rules L1–L14 in §2). Sketch rows: `H` header, `M` message line, `K` keybar. § numbers on the **Exemplars** line are sections of [exemplars.md](../exemplars.md).

**Use** for append-only, time-ordered events (logs, audit trails, chat). **Avoid** for state that changes in place (use A or I).

```text
H  Tail │ api-gateway · 3 pods · prod-eu                  ● following | PAUSED
   (regular+: 2-row rate histogram with error buckets in status.error)
   TIME         LVL POD  MESSAGE                       <- table.header
   14:22:00.311 ERR b81d POST /v1/charges 502 … err="context
                         deadline exceeded" retry=1/5  <- hanging indent
M  1,204 lines · 12/s · ✗ 9  ▲ 23                   level info+  wrap on
K  / filter  n next match  f follow  w wrap  l level         ? help  q quit
```
- **Core state = follow vs paused.** Following: new lines appear at the bottom, header shows `● following`. Any upward scroll pauses: header `PAUSED` chip, a counter `↓ 38 new lines  G to resume` above the message line, cursor row visible (`stream--normal--120x30`). Explicit, never silent: scrolling back stops auto-follow.
- **Columns**: time (fixed, `fg.faint`), level (3 letters, colored: `ERR` bold `status.error`, `WRN` `status.warning`, `INF` `status.info`, `DBG` `fg.faint`), source (short id at 80, full at 120), message (flex). Error rows: message stays `fg.default` (L9). `key=` in `fg.faint`, values in `fg.default`; key=value pairs never split across lines.
- **Keys**: `/` filter, `n`/`N` next/prev match, `f` follow, `G` end + resume, `w` wrap, `t` timestamps, `l` level, `0`-`6` time window (k9s log view [src]), `enter` inspect one line.
- **Responsive**: 80x24 = 4-char source ids, wrap max 2 rows per entry then `…`; 120x30 = histogram band, full pod names, line counter; 170x40 = side panel with the selected line's fields (JSON pretty-print).
- **States**: empty = filter matched nothing, stream still live (`stream--empty--80x24`: `No lines match /timeout/ at level err+`, `1,204 lines scanned … still following`); disconnected = keep lines, header chip `DISCONNECTED 12s`, retry countdown in the message line.
- **Striping**: optional for wide logs; parity from the oldest line so following never flips it ([§2.4](../layout-archetypes.md#24-zebra-striping-tables-logs-long-lists) Z5).
- **Pitfalls**: unbounded memory (keep a ring buffer, show `older lines dropped`); re-rendering all lines per event (virtualize to visible rows); ANSI/control sequences from log text (strip them at the display boundary).
- **Exemplars**: k9s log view, lazydocker Logs tab (§1, §3); lnav (catalog, unverified).
