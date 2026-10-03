# C. Miller columns

Part of [layout-archetypes.md](../layout-archetypes.md) (rules L1–L14 in §2). Sketch rows: `H` header, `M` message line, `K` keybar. § numbers on the **Exemplars** line are sections of [exemplars.md](../exemplars.md).

**Use** for hierarchies where siblings and parent context matter while moving (file systems, nested configs, S3 buckets). **Avoid** for flat collections (B) or when the preview is the main task (D).

```text
H  ~/src/payments/internal/webhook                         1  2
 parent  │ current (cursor, sizes right)          │ preview of hovered item
         │                                        │ (text, dir listing, error)
M  NOR  4.1 KiB  retry.go                       -rw-r--r--  Go  5/9  Top
K  h parent  l open  space select  y yank  d trash  / find     F1 help  q quit
```
- **Focus**: always the middle column; `h`/`←` = parent becomes current, `l`/`→`/`enter` = enter or open. Hovered parent entry keeps `selection.inactive.bg` so the path is visible.
- **Ratios**: yazi `ratio = [1, 4, 3]` (parent : current : preview) [src]. At 80 cols → 10 / 39 / 29 (`files--normal--80x24`); at 120 → 15 / 59 / 44 with size + mtime columns and marked files (`▌` in `mark`, `2 selected` in the status bar).
- **Responsive** (`derived:`; yazi only shrinks by ratio): below ~70 cols drop the parent column to a breadcrumb in the header; below ~45 cols drop the preview (yazi's `ratio = [0, 1, 0]` is UNVERIFIED as a supported value). 170x40: wider preview with line numbers and image/archive previews.
- **States**: errors stay **local to the column** that failed (`files--error--80x24`: `✗ Permission denied` in the preview, `l open` disabled, navigation still works); empty dir = faint "empty directory" in the current column; slow preview = spinner in the preview only.
- **Pitfalls**: preview loads blocking the cursor (tag preview requests with the item id, drop stale results); losing the cursor position when returning to a parent (restore it); preview text not truncated (clip with a faint `…`).
- **Exemplars**: yazi (§5); ranger (catalog).
