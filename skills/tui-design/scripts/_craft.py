"""Craft lint: the countable README-test failures of references/visual-craft.md, as WARN findings on a parsed .mock.

Each rule names a pattern that fails the README test and the principle that fixes it. They are heuristics on the cell
grid, so a frame may waive one on purpose with a header line `#! note: craft-ok CRn <reason>`.

  CR1 bracket chips      `[ Items ]`, `[ Apply: F2 ]`, `Search: [ … ]`             P9, P11
  CR2 label noise        2+ `Label:` prefixes on one row, or `a / b / c` detail lines  P11
  CR3 constant column    a table column with one value on every row (6+ rows)          P2, P10
  CR4 loud placeholder   `(none)` / `(untitled)` ×3+ at full weight                     P2
  CR5 dead gutter        16+ empty columns between columns on every row of a table     P1, P11
  CR6 dead band          a run of blank rows ≥ 1/5 of the frame (not in empty/busy)    P1, P10
  CR7 footer sprawl      key hints spread over 2+ footer rows                          P9
"""

from __future__ import annotations

import re

BRACKET = re.compile(r"\[\s*([^\[\]]{1,40}?)\s*\]")
CHECKBOX = re.compile(r"^(?:[^A-Za-z]{0,8}|[A-Za-z]{1,2})$")   # [ ] [x] [+] [9/18] [ok] [i]: controls, counters, ASCII status
LABEL = re.compile(r"(?:^|(?<=\s))[A-Z][A-Za-z]+(?: [a-z]+)?: (?=\S)")
SLASHED = re.compile(r"\S+ / \S+ / \S+")
PLACEHOLDER = re.compile(r"^\((?:[a-z][a-z /-]{1,20})\)$|^<(?:none|empty|unset)>$")
WORD = re.compile(r"\S+")
QUIET = ("muted", "faint", "disabled", "subtle")
GUTTER, BLOCK, CONST_ROWS = 16, 5, 6
SPARSE_STATES = ("empty", "toosmall", "busy", "loading")


def _rows(m):
    """Per body row: (text with one char per cell column, styles per column)."""
    out = []
    for cells in m.grid:
        chars, styles = [], []
        for c in cells:
            chars.append(c.text[:1] or " ")
            styles.append(c.style)
            if c.width == 2:
                chars.append("\0")
                styles.append(c.style)
        pad = m.cols - len(chars)
        out.append(("".join(chars) + " " * max(0, pad), styles + [None] * max(0, pad)))
    return out


def _quiet(style) -> bool:
    return style is None or "dim" in style.attrs or any(q in (style.fg or "") for q in QUIET)


def _blocks(rows):
    """Runs of consecutive non-blank rows: [(first_y, last_y)]."""
    out, start = [], None
    for y, (t, _) in enumerate(rows + [(" ", [])]):
        blank = not t.strip(" \0")
        if not blank and start is None:
            start = y
        elif blank and start is not None:
            out.append((start, y - 1))
            start = None
    return out


def craft_findings(m) -> list[tuple[int, int, str, str]]:
    """(row y, col x, message, hint) per craft problem; rows/cols 0-based into the body grid."""
    rows = _rows(m)
    found: list[tuple[int, int, str, str]] = []
    waived = {n.split()[1] for n in m.notes if n.startswith("craft-ok ") and len(n.split()) > 1}

    def add(rule, y, x, msg, hint):
        if rule not in waived:
            found.append((y, x, f"craft {rule}: {msg}", hint + f"; waive with '#! note: craft-ok {rule} <reason>'"))

    # CR1, CR2: per-row text patterns
    for y, (t, _) in enumerate(rows):
        chips = [mt for mt in BRACKET.finditer(t) if not CHECKBOX.match(mt.group(1))]
        if chips:
            add("CR1", y, chips[0].start(), f"bracket chip {chips[0].group(0)!r}" + (f" (+{len(chips) - 1} more)" if len(chips) > 1 else ""),
                "mark the active tab with accent + bold or an underline; keys go in the footer as `key verb` (visual-craft P9, P11)")
        labels = LABEL.findall(t)
        if len(labels) >= 2:
            add("CR2", y, t.find(labels[0]), f"{len(labels)} 'Label:' prefixes on one row",
                "use aligned key–value rows (key in fg.muted, value in fg.default) or a breadcrumb with › (P11)")
        elif (ms := SLASHED.search(t)):
            add("CR2", y, ms.start(), f"slash-joined detail {ms.group(0)[:40]!r}",
                "use aligned key–value rows or a breadcrumb with › (P11)")

    # CR3 constant column, CR5 dead gutter: per table block (first row may be a header)
    for y0, y1 in _blocks(rows):
        body = list(range(y0 + 1, y1 + 1))
        if len(body) < BLOCK:
            continue
        cols = None
        for y in body:
            toks = {(mt.start(), mt.group(0)) for mt in WORD.finditer(rows[y][0]) if re.search(r"[A-Za-z0-9]", mt.group(0))}
            cols = toks if cols is None else cols & toks
        others_vary = len({rows[y][0] for y in body}) > 1
        for x, tok in sorted(cols or ()):
            if len(tok) >= 2 and others_vary and len(body) >= CONST_ROWS:
                add("CR3", body[0], x, f"column value {tok!r} is the same on all {len(body)} rows",
                    "a value every row shares is not information: move it to the header or the detail (P2, P10)")
                break
        empty = [all(rows[y][0][x] == " " for y in body) for x in range(m.cols)]
        used = [x for x in range(m.cols) if not empty[x]]
        if used:
            run = best = 0
            best_end = 0
            for x in range(used[0], used[-1] + 1):
                run = run + 1 if empty[x] else 0
                if run > best:
                    best, best_end = run, x
            if best >= GUTTER:
                add("CR5", body[0], best_end - best + 1, f"{best} empty columns between two columns on all {len(body)} rows",
                    "size the column to its longest value and give the width to one flex column (P1, P11)")

    # CR4 loud placeholder
    loud: dict[str, list[tuple[int, int]]] = {}
    for y, (t, st) in enumerate(rows):
        for mt in WORD.finditer(t):
            if PLACEHOLDER.match(mt.group(0)) and not _quiet(st[mt.start()]):
                loud.setdefault(mt.group(0), []).append((y, mt.start()))
    for tok, where in loud.items():
        if len(where) >= 3:
            add("CR4", where[0][0], where[0][1], f"placeholder {tok!r} ×{len(where)} at full weight",
                "say it once per row as a glyph plus a dim or accent word, quieter than real values (P2)")

    # CR6 dead band (sparse states center a message on purpose)
    state = m.state or next((s for s in SPARSE_STATES if f"--{s}--" in m.path), "")
    run, limit = 0, (m.rows + 1 if state in SPARSE_STATES else max(4, m.rows // 5))
    for y, (t, st) in enumerate(rows + [("x", [])]):
        blank = not t.strip(" \0") and all(s is None or not s.bg for s in st)
        if blank:
            run += 1
            continue
        if run >= limit and y - run > 0 and y < len(rows):
            add("CR6", y - run, 0, f"{run} blank rows inside the frame",
                "size the list to the data and give the rows to the detail, a summary or a roster (P1, P10)")
        run = 0

    # CR7 footer sprawl: trailing rows that carry key hints
    def keyrow(st):
        return sum(1 for i, s in enumerate(st) if s and s.fg == "keyhint.key" and (i == 0 or not st[i - 1] or st[i - 1].fg != "keyhint.key")) >= 2
    n, y = 0, len(rows) - 1
    while y >= 0 and (keyrow(rows[y][1]) or (n == 0 and not rows[y][0].strip())):
        n += keyrow(rows[y][1])
        y -= 1
    if n >= 2:
        add("CR7", y + 1, 0, f"key hints spread over {n} footer rows",
            "one footer row: context keys left, global keys right; the rest goes in ? help (P9)")
    return found
