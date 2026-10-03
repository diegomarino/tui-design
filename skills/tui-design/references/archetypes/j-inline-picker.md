# J. Inline picker (summon–choose–exit)

Part of [layout-archetypes.md](../layout-archetypes.md) (rules L1–L14 in §2). Sketch rows: `H` header, `M` message line, `K` keybar. § numbers on the **Exemplars** line are sections of [exemplars.md](../exemplars.md).

**Use** when the user summons the tool from a shell or a host key to pick one or a few items and go back to what they were doing (branch, file, history entry, process, context). **Avoid** when the user stays to browse, compare or act repeatedly (B or I in the alt screen), or when the choice needs a preview larger than the bounded height allows (go full-screen; fzf without `--height` is full-screen too).

```text
~/src/payments $ git switch "$(pick-branch)"            <- scrollback stays visible
❯ fe█                                          4/37     <- query + match count
  ❯ feature/login-retry              2h  alex           <- ❯ + selection.bg
    feature/webhook-backoff          1d  ana            <- matches search.match bold
    fix/ledger-rounding              3d  alex
    release/2026.10                  5d  ci
↑↓ move  enter switch  tab mark                esc cancel
```
After `enter` the viewport is erased (or replaced by a receipt on stderr) and only `feature/login-retry` reaches stdout:
```text
~/src/payments $ git switch "$(pick-branch)"
✓ feature/login-retry                                   <- receipt, stderr, fg.muted
Switched to branch 'feature/login-retry'
```
- **Regions**: query line (prompt glyph, input, match count right-aligned, spinner while the source streams) · result list (cursor, mark column, label flex with matched chars, metadata right in `fg.muted`) · optional preview (right at ≥ 100 cols, toggled below that) · one hint row. No outer border by default: the scrollback is the frame.
- **Streams and exit**: candidates from stdin or a command; keys from `/dev/tty`; drawing on `/dev/tty` (or stderr); stdout gets only the chosen value(s), one per line, no ANSI. Exit 0 = chosen, 1 = nothing matched or chosen, 130 = cancelled (fzf adds 2 = error; gum uses 0/1/130). On exit erase the viewport (fzf default) or leave one receipt line; never a half-drawn viewport.
- **Keys**: printable keys type into the query, so no single-letter commands (`q` is a query character); `↑↓` / `ctrl-p` `ctrl-n` move, `enter` accept, `tab` mark (count shows `2 marked`), `esc` / `ctrl-c` cancel, preview toggle on a ctrl chord (fzf users bind `ctrl-/:toggle-preview`). Hint row ≤ 5 verbs.
- **Size**: viewport height = `min(items + chrome, max(min-height, 40% of rows))` (fzf `--height 40%`, `--min-height` default 10); width = terminal width. Minimum (`derived:`) ≈ 40x6: query, ≥ 3 result rows, hint. Fewer rows than that: switch to the alt screen instead of clipping. No TTY to open: do not prompt; fail with a message naming the non-interactive form (`--select NAME`; fzf `--filter=QUERY`).
- **Responsive**: 60 cols = label only, metadata dropped right-to-left (L3); 80 = label + 1-2 metadata columns, preview off; 120 = preview pane on the right (≈ 50 %).
- **States**: busy = rows appear as they stream, count `⠋ 120/…`, the cursor stays on the same item (select by id, not index); empty = `0/0` and why (`no local branches`) in `fg.muted`, `enter` does nothing; no match = `0/37`, one faint line `no match for "zz"`, query still editable; error (source command failed) = restore, message on stderr, non-zero exit.
- **Pitfalls**: UI bytes on stdout (breaks `$(…)`); rows re-sorting under the cursor while streaming; full-screen for five items; the viewport left on screen after cancel; ANSI or the receipt on stdout.
- **Startup budget: summon to first frame ≤ 100 ms** (users summon a picker dozens of times a day; the same bound as key → visible change in [interaction.md](../interaction.md) §8). Measured hello-world first frames are in the "Startup" column of [frameworks/choosing.md](../frameworks/choosing.md) §3: Go, Rust and gum fit with room; Ink (~120 ms) and Textual (~90 ms) spend the budget before your code runs, so measure yours (`hyperfine --warmup 3 'pickf --filter=x < list'` times start-up without drawing) and keep `--version`, `completion` and `init` off the UI import path.
- **Shell contract**: exit codes, Esc/Ctrl-C = 130, drawing on `/dev/tty`, piped candidates, no-TTY failure and **cd on exit through a shell function** live in [cli-contract.md](../cli-contract.md) (CC1, CC9-CC10, CC21-CC22); check them with SH-02, SH-03, SH-04, SH-07, SH-08 and SH-14.
- **Mockups**: none shipped; build them with `SKILL_DIR/scripts/mockkit.py`, named by the drawn area (`branches--normal--80x8.mock` = shell line + viewport), plus `--empty` and a receipt frame.
- **Exemplars**: fzf (`--height`, `--layout=reverse`), gum `choose`/`filter` ([frameworks/gum.md](../frameworks/gum.md)); inline support per framework: [frameworks/choosing.md](../frameworks/choosing.md) §4 "Inline".
