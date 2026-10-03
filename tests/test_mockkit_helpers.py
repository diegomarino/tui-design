"""Tests for mockkit's layout math, truncation, widget helpers, caps degradation and the states x sizes matrix."""

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "tui-design" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _mock import parse_mock  # noqa: E402
from mockkit import (Canvas, CanvasError, Col, Node, Rect, _fit_runs, chip, fit, fold_runs, frame_name,  # noqa: E402
                     hint_runs, layout, matrix, scroll_pos, scroll_range, size_class, spark, tab_runs, times,
                     tree_rows, truncate, width)


def rows_of(c: Canvas) -> list[str]:
    return c.plain().split("\n")


def bg_at(c: Canvas, x: int, y: int):
    return c.cells[y][x].bg


def fg_at(c: Canvas, x: int, y: int):
    return c.cells[y][x].fg


def lint_errors(c: Canvas) -> list[str]:
    return c.lint()


class LayoutMath(unittest.TestCase):
    def test_fixed_and_flex(self):
        self.assertEqual(layout(80, [32, "*"]), [(0, 32), (32, 48)])
        self.assertEqual([s for _, s in layout(10, ["*", "*", "*"])], [4, 3, 3])     # leftover to the first
        self.assertEqual([s for _, s in layout(10, ["2*", "*"])], [7, 3])
        self.assertEqual(layout(10, [3, "*"], gap=1), [(0, 3), (4, 6)])
        self.assertEqual([s for _, s in layout(100, [0.25, None])], [25, 75])
        self.assertEqual([s for _, s in layout(10, [2, "1fr", 3])], [2, 5, 3])
        self.assertEqual(sum(s for _, s in layout(117, ["*", 42, "3*"], gap=1)) + 2, 117)

    def test_overflow_and_bad_sizes_explain(self):
        with self.assertRaises(CanvasError) as cm:
            layout(60, [32, 40])
        self.assertIn("need 72 cells but only 60", str(cm.exception))
        self.assertIn("size_class", str(cm.exception))
        for bad in (-1, 1.5, "x", True):
            with self.assertRaises(CanvasError):
                layout(10, [bad])

    def test_rect(self):
        r = Rect(0, 0, 80, 24)
        head, body, msg, keys = r.split_v([1, "*", 1, 1])
        self.assertEqual((head, body, msg, keys), (Rect(0, 0, 80, 1), Rect(0, 1, 80, 21), Rect(0, 22, 80, 1),
                                                   Rect(0, 23, 80, 1)))
        left, right = body.split_h([32, "*"])
        self.assertEqual((left, right), (Rect(0, 1, 32, 21), Rect(32, 1, 48, 21)))
        self.assertEqual(left.inner, Rect(1, 2, 30, 19))
        self.assertEqual(r.inset(0, 2, 0, 1), Rect(0, 2, 80, 21))
        self.assertEqual(r.inset(2, 1), Rect(2, 1, 76, 22))
        self.assertEqual(r.take(3, "bottom"), (Rect(0, 21, 80, 3), Rect(0, 0, 80, 21)))
        self.assertEqual(r.take(10, "right")[0], Rect(70, 0, 10, 24))
        self.assertEqual(r.center(40, 10), Rect(20, 7, 40, 10))
        self.assertEqual(r.row(-1), Rect(0, 23, 80, 1))
        x, y, w, h = left
        self.assertEqual((x, y, w, h, left.right, left.bottom), (0, 1, 32, 21, 32, 22))

    def test_size_class(self):
        self.assertEqual([size_class(c) for c in (40, 60, 80, 100, 120, 170)],
                         ["tiny", "narrow", "compact", "regular", "regular", "wide"])


class Truncation(unittest.TestCase):
    def test_sides(self):
        self.assertEqual(truncate("abcdef", 4), "abc⋯")
        self.assertEqual(truncate("abcdef", 4, "start"), "⋯def")
        self.assertEqual(truncate("abcdef", 4, "middle"), "ab⋯f")
        self.assertEqual(truncate("~/Dev/project/worktrees", 10, "start"), "⋯worktrees")
        self.assertEqual(truncate("short", 9), "short")
        self.assertEqual(truncate("abc", 2, ellipsis="..."), "ab")         # no room for the ellipsis: hard cut
        self.assertEqual(truncate("abcdef", 5, ellipsis="..."), "ab...")
        self.assertEqual(truncate("abc", 0), "")

    def test_fit_align_and_wide(self):
        self.assertEqual(fit("ab", 6, "c"), "  ab  ")
        self.assertEqual(fit("abcdef", 4, side="start"), "⋯def")
        self.assertEqual(width(fit("漢字漢", 4)), 4)                       # a cut wide glyph leaves a pad space
        self.assertEqual(fit("a…", 3, ellipsis="…"), "a… ")
        with self.assertRaises(CanvasError):
            fit("a", 3, "x")

    def test_runs_keep_styles(self):
        out = _fit_runs([("✗ ", "status.error"), ("Sources failing", "fg.default")], 8)
        self.assertEqual(out, [("✗ ", "status.error"), ("Sourc⋯", "fg.default")])
        self.assertEqual(_fit_runs([("ab", "fg.muted")], 4, "r"), [("  ", None), ("ab", "fg.muted")])


class SmallHelpers(unittest.TestCase):
    def test_fold_times_scroll(self):
        self.assertEqual(fold_runs("aabccc"), [("a", 2), ("b", 1), ("c", 3)])
        self.assertEqual(fold_runs([("x", 1), ("x", 2), ("y", 3)], key=lambda t: t[0]), [(("x", 1), 2), (("y", 3), 1)])
        self.assertEqual(times("Question", 2), "Question ×2")
        self.assertEqual(times("Task", 1), "Task")
        self.assertEqual(scroll_range(0, 15, 175), "1-15/175")
        self.assertEqual(scroll_range(170, 15, 175), "171-175/175")
        self.assertEqual(scroll_range(0, 5, 0), "0/0")
        self.assertEqual(scroll_pos(11, 90), "12/90")

    def test_runs_builders(self):
        self.assertEqual(chip("WARN"), (" WARN ", "fg.on-accent on:status.warning"))
        self.assertEqual("".join(s for s, _ in hint_runs([("q", "quit"), ("?", "help")])), "q quit  ? help")
        self.assertEqual(hint_runs([("F2", "apply", "off")])[0], ("F2", "fg.faint"))
        self.assertEqual("".join(s for s, _ in tab_runs(["Services", ("Logs", 3)])), " 1 Services  2 Logs 3 ")
        self.assertEqual(spark([0, 7]), "▁█")
        self.assertEqual(spark([0, 7], ascii=True), "_#")


class TextAndErrors(unittest.TestCase):
    def test_clip_stops_before_border(self):
        c = Canvas(12, 3)
        c.box(0, 0, 10, 3, "T")
        self.assertEqual(c.text(1, 1, "abcdefghijkl", "fg.muted", clip=True), 9)
        self.assertEqual(rows_of(c)[1], "│abcdefg⋯│")
        c2 = Canvas(10, 1)
        c2.text(6, 0, "abcdef", clip=True)
        self.assertEqual(rows_of(c2)[0], "      abc⋯")
        c2.text(0, 0, "xyz", clip=2)
        self.assertTrue(rows_of(c2)[0].startswith("x⋯"))

    def test_border_error_names_box_and_free_span(self):
        c = Canvas(40, 5)
        c.box(0, 0, 20, 5, "Services")
        with self.assertRaises(CanvasError) as cm:
            c.text(15, 2, "too long text")
        msg = str(cm.exception)
        self.assertIn("box 'Services'", msg)
        self.assertIn("(19,2)", msg)
        self.assertIn("x=15..18 (4 cells)", msg)

    def test_overflow_error_suggests_fit(self):
        c = Canvas(10, 2)
        with self.assertRaises(CanvasError) as cm:
            c.text(5, 0, "abcdefgh")
        self.assertIn("only 5 fit", str(cm.exception))
        self.assertIn("fit(s, 5)", str(cm.exception))

    def test_token_suggestions(self):
        c = Canvas(10, 1)
        with self.assertRaises(CanvasError) as cm:
            c.text(0, 0, "x", "fg.mutted")
        self.assertIn("did you mean 'fg.muted'", str(cm.exception))
        with self.assertRaises(CanvasError) as cm:
            c.region("r1", "lsit", 0, 0, 1, 1)
        self.assertIn("did you mean list", str(cm.exception))

    def test_box_overlap_names_other_box(self):
        c = Canvas(30, 6)
        c.box(0, 0, 12, 6, "Left")
        with self.assertRaises(CanvasError) as cm:
            c.box(11, 0, 12, 6, "Right")
        self.assertIn("'Left'", str(cm.exception))

    def test_lint_messages_name_cells(self):
        c = Canvas(6, 2)
        c.text(1, 1, "漢")
        errs = lint_errors(c)
        self.assertTrue(errs and "(x=1,y=1)" in errs[0], errs)
        with self.assertRaises(CanvasError) as cm:
            c.save(Path(tempfile.gettempdir()) / "never-written-2.mock")
        self.assertIn("(x=1,y=1)", str(cm.exception))
        d = Canvas(10, 4)
        d.box(0, 0, 10, 4, region="panel")
        d.text(0, 2, "x", force=True)                       # forced over the border: the linter catches it
        self.assertTrue(any("canvas row y=2" in e for e in lint_errors(d)), lint_errors(d))


class TableTests(unittest.TestCase):
    COLS = [Col("", 1), Col("NAME"), Col("AGE", 4, "r", spec="fg.muted")]

    def rows(self, n):
        return [[("●", "status.success"), f"svc-{i}", f"{i}m"] for i in range(n)]

    def test_columns_header_and_selection(self):
        c = Canvas(30, 8)
        inner = c.panel(Rect(0, 0, 30, 8), "Services", role="list", focus=True)
        info = c.table(inner, columns=self.COLS, rows=self.rows(3), selected=1, cursor="❯")
        self.assertEqual([(x, w) for _, x, w in info.cols], [(4, 1), (6, 17), (24, 4)])
        r = rows_of(c)
        self.assertEqual(r[1], "│     NAME               AGE │")
        self.assertEqual(r[3], "│ ❯ ● svc-1               1m │")
        self.assertTrue(all(bg_at(c, x, 3) == "selection.bg" for x in range(1, 29)))   # full interior width
        self.assertEqual(fg_at(c, 6, 3), "selection.fg")                              # neutral -> selection.fg
        self.assertEqual(fg_at(c, 4, 3), "status.success")                            # semantic kept
        self.assertEqual(fg_at(c, 6, 2), "fg.default")
        self.assertIn("#! selected r1 2", c.to_mock())                                # header is interior row 0
        self.assertIn("#! focus r1", c.to_mock())
        self.assertEqual(info.range, "1-3/3")
        self.assertEqual(lint_errors(c), [])

    def test_truncation_sides_and_hide_below(self):
        cols = [Col("PATH", truncate="start"), Col("ID", 5, truncate="middle"), Col("EXTRA", 6, hide_below=40)]
        c = Canvas(30, 3)
        info = c.table(Rect(0, 0, 30, 3), columns=cols, rows=[["~/Dev/project/very/long/path", "w58:p12", "x"]])
        self.assertEqual([col.name for col, _, _ in info.cols], ["PATH", "ID"])         # EXTRA hidden below 40
        self.assertEqual(rows_of(c)[1], " ⋯roject/very/long/path w5⋯12")
        c2 = Canvas(50, 3)
        self.assertEqual(len(c2.table(Rect(0, 0, 50, 3), columns=cols, rows=[["a", "b", "c"]]).cols), 3)

    def test_too_narrow_explains(self):
        c = Canvas(20, 3)
        with self.assertRaises(CanvasError) as cm:
            c.table(Rect(0, 0, 20, 3), columns=[Col("A", 10), Col("B", 10)], rows=[])
        self.assertIn("hide_below", str(cm.exception))
        with self.assertRaises(CanvasError) as cm:
            c.table(Rect(0, 0, 20, 3), columns=[Col("A", 15), Col("B", min=5)], rows=[])
        self.assertIn("min 5", str(cm.exception))

    def test_zebra_parity_anchored_to_data(self):
        def striped(c, info):
            return [bg_at(c, 0, y) == "bg.stripe" for y in info.rows_y]

        c = Canvas(20, 6)
        info = c.table(Rect(0, 0, 20, 6), columns=self.COLS, rows=self.rows(10), header=False, zebra=True)
        self.assertEqual(striped(c, info), [False, True, False, True, False, True])
        c = Canvas(20, 6)                                   # scrolled by one: data row 1 is still striped
        info = c.table(Rect(0, 0, 20, 6), columns=self.COLS, rows=self.rows(10), header=False, zebra=True, offset=1)
        self.assertEqual(striped(c, info)[0], True)
        # newest-first feed: a new event on top never flips the stripes of existing events
        events = [f"e{i}" for i in range(7, 0, -1)]                     # newest first, e1 is the oldest
        c1, c2 = Canvas(20, 8), Canvas(20, 8)
        i1 = c1.table(Rect(0, 0, 20, 8), columns=[Col()], rows=[[e] for e in events], header=False,
                      zebra="newest-first")
        i2 = c2.table(Rect(0, 0, 20, 8), columns=[Col()], rows=[["e8"]] + [[e] for e in events], header=False,
                      zebra="newest-first")
        s1 = dict(zip(events, striped(c1, i1)))
        s2 = dict(zip(["e8"] + events, striped(c2, i2)))
        self.assertTrue(all(s1[e] == s2[e] for e in events))
        self.assertFalse(s1["e1"])                                       # oldest = sequence 0, phase 1: plain
        c3 = Canvas(20, 4)
        i3 = c3.table(Rect(0, 0, 20, 4), columns=[Col()], rows=[["a"], ["b"], ["c"]], header=False,
                      zebra=lambda i, row: row[0] == "b", selected=2, stripe="bg.inset")
        self.assertEqual([bg_at(c3, 0, y) for y in i3.rows_y], [None, "bg.inset", "selection.bg"])   # Z3

    def test_inactive_stale_row_spec_skeleton(self):
        c = Canvas(20, 6)
        c.region("r1", "table", 0, 0, 20, 6)
        c.table(Rect(0, 0, 20, 6), columns=self.COLS, rows=self.rows(2), selected=0, inactive=True, cursor="❯",
                region="r1", skeleton=2)
        self.assertEqual(bg_at(c, 0, 1), "selection.inactive.bg")
        self.assertNotIn("❯", c.plain())
        self.assertNotIn("#! selected", c.to_mock())                     # focus is elsewhere: not recorded
        self.assertEqual(fg_at(c, 6, 1), "fg.default")
        self.assertIn("░", rows_of(c)[3])
        s = Canvas(20, 3)
        s.table(Rect(0, 0, 20, 3), columns=self.COLS, rows=self.rows(2), header=False, stale=True)
        self.assertEqual({fg_at(s, x, 0) for x in (1, 3)}, {"fg.faint"})
        rs = Canvas(20, 3)
        rs.table(Rect(0, 0, 20, 3), columns=self.COLS, rows=self.rows(2), header=False,
                 row_spec=lambda i, row: "fg.faint" if i == 1 else None)
        self.assertEqual((fg_at(rs, 3, 1), fg_at(rs, 1, 1), fg_at(rs, 3, 0)), ("fg.faint", "status.success", "fg.default"))

    def test_dict_rows_and_unknown_height(self):
        c = Canvas(20, 5)
        info = c.table(1, 1, 18, columns=[Col("name"), Col("n", 3, "r")], rows=[{"name": "a", "n": 1}, {"name": "b"}])
        self.assertEqual(info.shown, 2)
        self.assertEqual(rows_of(c)[2], "  a              1")

    def test_listing_and_tree(self):
        c = Canvas(30, 8)
        inner = c.panel(c.rect, "Files", role="tree", focus=True)
        info = c.tree(inner, nodes=[("src", [("lib", ["a.py", "b.py"]), "main.py"]), "README"], selected=2, cursor="❯")
        r = rows_of(c)
        self.assertEqual([ln[1:].rstrip(" │") for ln in r[1:7]],
                         ["   src", "   ├── lib", " ❯ │   ├── a.py", "   │   └── b.py", "   └── main.py", "   README"])
        self.assertEqual(fg_at(c, 4, 2), "fg.faint")                                   # guides are faint
        self.assertEqual(len(info.items), 6)
        self.assertIn("#! selected r1 2", c.to_mock())
        lst = Canvas(20, 3)
        lst.listing(Rect(0, 0, 20, 3), items=["one", ("two", "status.error")], selected=1)
        self.assertEqual(rows_of(lst)[1], " ❯ two")

    def test_tree_rows_guides_folds_ascii(self):
        nodes = [("root", [("a", ["a1"]), Node("b", ["hidden"], open=False)])]
        self.assertEqual([p for p, *_ in tree_rows(nodes)], ["", "├── ", "│   └── ", "└── "])
        self.assertEqual([p for p, *_ in tree_rows(nodes, indent=3, ascii=True)], ["", "|- ", "|  `- ", "`- "])
        self.assertEqual([p for p, *_ in tree_rows(nodes, folds=True)], ["▾ ", "├── ▾ ", "│   └──   ", "└── ▸ "])
        with self.assertRaises(CanvasError):
            tree_rows(nodes, indent=5)


class WidgetTests(unittest.TestCase):
    def test_gauge_math(self):
        c = Canvas(30, 4)
        self.assertEqual(c.gauge(0, 0, 24, .68, label_w=4), 24)
        self.assertEqual(rows_of(c)[0], "█" * 13 + "░" * 7 + " 68%")      # floor, never overstated
        self.assertEqual((fg_at(c, 0, 0), fg_at(c, 19, 0)), ("ramp.mid", "fg.faint"))
        c.gauge(0, 1, 10, .2)
        self.assertEqual(fg_at(c, 0, 1), "ramp.low")
        c.gauge(0, 2, 15, .95, label="19/20", label_w=6, ramp="accent.primary")
        self.assertEqual(rows_of(c)[2], "█" * 8 + "░" + " 19/20")
        c.gauge(0, 3, 10, .55, label=None, smooth=True)
        self.assertEqual(rows_of(c)[3], "█████▌░░░░")
        with self.assertRaises(CanvasError):
            c.gauge(0, 0, 4, .5)

    def test_scrollbar(self):
        c = Canvas(10, 10)
        self.assertFalse(c.scrollbar(9, 0, 10, 0, 10, 8))                 # fits: hidden
        self.assertTrue(c.scrollbar(9, 0, 10, 45, 10, 100))
        col = "".join(r[9] if len(r) > 9 else " " for r in rows_of(c)[:10])
        self.assertEqual(col, "││││█│││││")
        b = Canvas(10, 10)
        b.box(0, 0, 10, 10, region="list")
        b.scrollbar(9, 1, 8, 0, 4, 8)                                      # on the box side: only the thumb
        col = "".join(r[9] for r in rows_of(b)[1:9])
        self.assertEqual(col, "████││││")
        self.assertEqual(lint_errors(b), [])

    def test_keybar_inside_panel_drop_and_errors(self):
        c = Canvas(40, 6)
        inner = c.panel(c.rect, "P")
        c.keybar(inner.bottom - 1, [("⏎", "stage"), ("esc", "cancel")], right=[("q", "close")], bg=None,
                 x=inner.x, w=inner.w)
        self.assertEqual(rows_of(c)[4], "│ ⏎ stage  esc cancel          q close │")
        self.assertEqual(lint_errors(c), [])
        d = Canvas(34, 1)
        with self.assertRaises(CanvasError) as cm:
            d.keybar(0, [("a", "alpha"), ("b", "bravo"), ("c", "charlie")])
        self.assertIn("'c charlie'", str(cm.exception))
        self.assertIn("overflow='drop'", str(cm.exception))
        d.keybar(0, [("a", "alpha"), ("b", "bravo"), ("c", "charlie")], overflow="drop", region="keybar")
        self.assertEqual(rows_of(d)[0], " a alpha  b bravo  ? help  q quit")
        self.assertIn("#! region r1 keybar 0,0,34,1", d.to_mock())

    def test_band_tabs_message_chip_kv_lines(self):
        c = Canvas(40, 8)
        end, start = c.band(0, [(" App ", "accent.primary bold")] + tab_runs(["A", "B"], 1), "ctx ", pad=0,
                            region=("r1", "header"))
        self.assertEqual(rows_of(c)[0], " App  1 A  2 B                      ctx")
        self.assertEqual((end, start), (15, 36))
        self.assertEqual((bg_at(c, 11, 0), bg_at(c, 6, 0)), ("tab.active.bg", "statusbar.bg"))
        with self.assertRaises(CanvasError):
            c.band(1, "x" * 30, "y" * 15)
        self.assertEqual(c.tabs(0, 1, ["One", "Two"]), 14)
        c.message(2, "warn", "p95 latency 820 ms", "4m ago")
        self.assertEqual(rows_of(c)[2], " ▲ p95 latency 820 ms · 4m ago")
        self.assertEqual(c.chip(0, 3, "STALE 42s", "status.warning"), 11)
        self.assertEqual((fg_at(c, 1, 3), bg_at(c, 1, 3)), ("fg.on-accent", "status.warning"))
        self.assertEqual(c.kv(1, 4, [("Status", [("● running", "status.success")]), None, ("Version", "v2")]), 7)
        self.assertEqual(rows_of(c)[4], " Status   ● running")
        self.assertEqual(rows_of(c)[6], " Version  v2")
        e = Canvas(12, 3)
        e.box(0, 0, 12, 3)
        self.assertEqual(e.lines(1, 1, ["a long line here"]), 2)
        self.assertEqual(rows_of(e)[1], "│a long li⋯│")

    def test_overlay_and_center(self):
        c = Canvas(40, 12)
        base = c.panel(c.rect, "Base", role="list", focus=True)
        c.text(base.x, base.y, "row", "fg.default bold")
        inner = c.overlay(24, 7, "Confirm", hints=[("y", "yes"), ("n", "no")])
        self.assertEqual(inner, Rect(9, 3, 22, 3))
        c.center(inner, lines=["Delete 3 items?"])
        m = c.to_mock()
        self.assertIn("#! region r2 modal 8,2,24,7 Confirm", m)
        self.assertIn("#! focus r2", m)
        self.assertEqual((fg_at(c, 1, 1), c.cells[1][1].attrs), ("fg.faint", ()))     # base faded
        self.assertIn("Delete 3 items?", c.plain())
        self.assertIn("y yes  n no", c.plain())
        self.assertEqual(lint_errors(c), [])
        with self.assertRaises(CanvasError) as cm:
            c.overlay(50, 5)
        self.assertIn("min(50, c.cols - 4)", str(cm.exception))

    def test_toosmall(self):
        c = Canvas(40, 10, state="toosmall")
        c.toosmall((60, 16), app="App")
        p = c.plain()
        for s in ("Terminal too small", "Width    40   needs 60  ✗", "Height   10   needs 16  ✗", "q quit"):
            self.assertIn(s, p)
        self.assertEqual(lint_errors(c), [])


class CapsTests(unittest.TestCase):
    def test_helpers_drop_their_own_attributes(self):
        c = Canvas(40, 8, caps="attrs=dim")
        inner = c.panel(c.rect.inset(0, 0, 0, 1), "Services", role="list", focus=True)
        c.table(inner, columns=[Col("NAME"), Col("N", 3)], rows=[["a", "1"]], selected=0, cursor="❯")
        c.tabs(1, 5, ["One"])
        c.keybar(7, [("↑↓", "move")])
        self.assertNotIn("bold", c.to_mock())
        self.assertEqual(lint_errors(c), [])
        with self.assertRaises(CanvasError):                     # an attribute you pass yourself still raises
            c.text(1, 1, "x", "italic")

    def test_ascii_glyphs_in_helpers(self):
        c = Canvas(40, 10, caps="glyphs=ascii")
        inner = c.panel(c.rect, "Tree", role="tree", focus=True)
        c.tree(inner.take(4)[0], nodes=[("src", ["a", "b"])], selected=1, cursor="❯")
        c.table(inner.take(4)[1].take(2)[0], columns=[Col("", 1, ascii_width=4), Col("NAME", 6)],
                rows=[[("✓", "status.success"), "averylongname"]], header=False)
        c.gauge(1, 7, 12, .5, label_w=4)
        r = rows_of(c)
        self.assertTrue(r[0].startswith("+- Tree -"))
        self.assertEqual(r[2], "| > |-- a" + " " * 30 + "|")
        self.assertEqual(r[5], "| [ok] ave...".ljust(39) + "|")
        self.assertEqual(r[7], "|####---- 50%".ljust(39) + "|")
        self.assertEqual(c.g("cursor") + c.g("ok") + c.status("warn")[0], ">[ok][!]")
        self.assertEqual(lint_errors(c), [])
        with self.assertRaises(CanvasError) as cm:
            c.text(1, 8, "✓ done")                           # low-level text stays strict
        self.assertIn("fallback=True", str(cm.exception))
        with self.assertRaises(CanvasError):
            c.g("nope")

    def test_fallback_degrades_everything(self):
        c = Canvas(30, 4, caps="attrs=dim glyphs=ascii", fallback=True)
        c.box(0, 0, 30, 4, "Événements", title_spec="fg.title bold italic")
        c.text(1, 1, "✓ done — 2 → 3", "status.success bold")
        c.hline(0, 2, 30, ends=("├", "┤"))
        r = rows_of(c)
        self.assertEqual(r[1], "|[ok] done - 2 -> 3".ljust(29) + "|")
        self.assertEqual(r[2], "+----------------------------+")
        self.assertNotIn("bold", c.to_mock())
        self.assertEqual(lint_errors(c), [])


class MatrixTests(unittest.TestCase):
    def test_frame_name(self):
        self.assertEqual(frame_name("observe", "error", 120, 30), "observe--error--120x30.mock")
        with self.assertRaises(CanvasError) as cm:
            frame_name("Observe Screen", "normal", 80, 24)
        self.assertIn("'observe-screen'", str(cm.exception))
        with self.assertRaises(CanvasError):
            frame_name("x", "a--b", 80, 24)

    def test_matrix_builds_names_and_lints(self):
        seen = []

        def build(c, state):
            seen.append((state, c.cols, c.rows, c.caps.spec()))
            if state == "toosmall":
                return c.toosmall((80, 24))
            inner = c.panel(c.rect.inset(0, 0, 0, 1), "Items", role="list", focus=True)
            c.listing(inner, items=[] if state == "empty" else ["a", "b"], selected=None if state == "empty" else 0)
            c.keybar(c.rows - 1, [("↑↓", "move")], region="keybar")

        with tempfile.TemporaryDirectory() as d:
            paths = matrix(build, "items", d, states=("normal", "empty"), extra=[("toosmall", (60, 18))],
                           skip=lambda s, w, h: s == "empty" and w == 120, theme="nord-dark", caps="attrs=bold,dim",
                           title=lambda s, w, h: f"Items {s} {w}", render=True)
            names = sorted(p.name for p in paths)
            self.assertEqual(names, ["items--empty--80x24.mock", "items--normal--120x30.mock",
                                     "items--normal--80x24.mock", "items--toosmall--60x18.mock"])
            for p in paths:
                m = parse_mock(p.read_text(encoding="utf-8"), str(p))
                self.assertEqual([f for f in m.findings if f.level == "ERROR"], [])
                self.assertEqual((m.theme, m.caps.spec()), ("nord-dark", "attrs=bold,dim"))
                self.assertTrue(p.with_suffix(".ansi").exists())
            self.assertIn("#! title: Items normal 120", (Path(d) / "items--normal--120x30.mock").read_text())
        self.assertEqual(len(seen), 4)

    def test_matrix_reports_every_failing_frame(self):
        def build(c, state):
            c.text(0, 0, "x" * 100)                          # too wide at 80, fits at 120

        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(CanvasError) as cm:
                matrix(build, "wide", d, states=("normal", "error"), sizes=((80, 24), (120, 30)))
            msg = str(cm.exception)
            self.assertIn("2 of 4 frame(s) failed", msg)
            self.assertIn("wide--normal--80x24.mock: text", msg)
            self.assertIn("wide--error--80x24.mock", msg)
            self.assertTrue((Path(d) / "wide--normal--120x30.mock").exists())


class QuietOutput(unittest.TestCase):
    """save() and matrix() print one summary line, one line per distinct warning; verbose lists everything."""

    @staticmethod
    def build(c, state):
        body, keys = c.rect.split_v(["*", 1])
        lst = c.panel(body, "Runs", role="list", focus=True)
        c.listing(lst, items=["[ api ]", "#1841 web"], selected=0)       # CR1 bracket chip: a WARN
        c.keybar(keys.y, [("enter", "open")])

    def run_quiet(self, fn, env=None):
        import contextlib
        import io
        import os
        from unittest import mock
        buf = io.StringIO()
        with mock.patch.dict(os.environ, env or {}, clear=False), contextlib.redirect_stdout(buf):
            if not env:
                os.environ.pop("MOCKKIT_VERBOSE", None)
            fn()
        return buf.getvalue().splitlines()

    def test_matrix_default_is_one_summary_plus_grouped_warnings(self):
        with tempfile.TemporaryDirectory() as d:
            out = self.run_quiet(lambda: matrix(self.build, "q", d, states=("normal", "empty"),
                                                caps="attrs=bold,dim source=test-card"))
        self.assertEqual(out[0], f"mockkit: saved 4 frames · 0 errors · 4 warnings → {d}")
        self.assertEqual(len(out), 2, out)                       # the CR1 warning is shared by all 4 frames
        self.assertIn("WARN: craft CR1", out[1])
        self.assertIn("4 frames: q--normal--80x24.mock", out[1])
        self.assertFalse(any("INFO" in line for line in out))

    def test_matrix_verbose_param_and_env_list_every_frame(self):
        for kw, env in (({"verbose": True}, None), ({}, {"MOCKKIT_VERBOSE": "1"})):
            with self.subTest(kw=kw, env=env), tempfile.TemporaryDirectory() as d:
                out = self.run_quiet(lambda: matrix(self.build, "q", d, caps="attrs=bold,dim source=test-card",
                                                    **kw), env=env)
                self.assertTrue(out[0].startswith("mockkit: saved 2 frames"))
                self.assertTrue(any(line.startswith("  q--normal--80x24.mock · 0 errors · 1 warning · ") for line in out))
                self.assertTrue(any(": INFO: " in line for line in out))

    def test_save_summary_and_report_false(self):
        with tempfile.TemporaryDirectory() as d:
            c = Canvas(20, 3, caps="attrs=bold,dim source=test-card")
            c.text(0, 0, "hi")
            out = self.run_quiet(lambda: c.save(Path(d) / "x--normal--20x3.mock"))
            self.assertEqual(out, [f"mockkit: saved x--normal--20x3.mock · 0 errors · 0 warnings → {d}"])
            self.assertEqual(self.run_quiet(lambda: c.save(Path(d) / "y.mock", report=False)), [])

    def test_save_unchecked_prints_errors_in_full(self):
        with tempfile.TemporaryDirectory() as d:
            c = Canvas(20, 3, caps="attrs=bold source=test-card")
            c.cells[0][0].ch = "日"                                # a wide glyph sneaked past the writer
            out = self.run_quiet(lambda: c.save(Path(d) / "z.mock", check=False))
        self.assertIn("1 error", out[0])
        self.assertTrue(out[1].startswith("  ") and "ERROR" in out[1], out)

    def test_matrix_failure_prints_summary_then_raises(self):
        def bad(c, state):
            if state == "error":
                c.text(0, 0, "x", "fg.nope")
        with tempfile.TemporaryDirectory() as d:
            def go():
                with self.assertRaises(CanvasError):
                    matrix(bad, "b", d, states=("normal", "error"), sizes=((80, 24),),
                           caps="attrs=bold,dim source=test-card")
            out = self.run_quiet(go)
        self.assertEqual(out, [f"mockkit: saved 1 of 2 frames · 1 error · 0 warnings → {d}"])


class GuideRecipes(unittest.TestCase):
    """Every code block in references/mockkit.md runs and lints at the sizes it claims."""
    GUIDE = SCRIPTS.parent / "references" / "mockkit.md"

    def blocks(self):
        import re
        return re.findall(r"```python\n(.*?)```", self.GUIDE.read_text(encoding="utf-8"), re.S)

    def ns(self):
        import mockkit
        return {k: getattr(mockkit, k) for k in mockkit.__all__}

    def test_quick_start(self):
        code = self.blocks()[0]
        with tempfile.TemporaryDirectory() as d:
            code = code.replace("SKILL_DIR/scripts", str(SCRIPTS)).replace('"out/fleet--normal--80x24.mock"',
                                                                            repr(f"{d}/fleet--normal--80x24.mock"))
            exec(compile(code, "<quick start>", "exec"), {})
            self.assertTrue((Path(d) / "fleet--normal--80x24.mock").exists())

    def test_recipes_build_at_every_size(self):
        recipes = [b for b in self.blocks() if b.startswith("def screen(c, state)")]
        self.assertEqual(len(recipes), 6)
        for code in recipes:
            ns = self.ns()
            exec(compile(code, "<recipe>", "exec"), ns)
            sizes = ((80, 8),) if "sizes=((80, 8),)" in code else ((80, 24), (120, 30), (60, 24))
            for state in ("normal", "empty", "error"):
                for cols, rows in sizes:
                    with self.subTest(recipe=code.splitlines()[0], state=state, size=(cols, rows)):
                        c = Canvas(cols, rows, state=state, caps="attrs=bold,dim")
                        ns["screen"](c, state)
                        self.assertEqual(c.lint(), [])

    def test_matrix_block(self):
        recipe = next(b for b in self.blocks() if b.startswith("def screen(c, state)"))
        code = next(b for b in self.blocks() if "matrix(build" in b)
        with tempfile.TemporaryDirectory() as d:
            code = code.replace('"design/frames"', repr(f"{d}/frames")).replace('"design/gallery.html"',
                                                                                repr(f"{d}/gallery.html"))
            code = code.replace("png=True", "render=True")
            ns = self.ns()
            exec(compile(recipe + "\n" + code, "<matrix>", "exec"), ns)
            self.assertEqual(len(ns["paths"]), 10)
            self.assertTrue((Path(d) / "frames" / "fleet--toosmall--60x18.mock").exists())
            self.assertTrue((Path(d) / "gallery.html").exists())



class GuideAPI(unittest.TestCase):
    """references/mockkit-api.md names every public class, function and Canvas/Rect method."""

    def test_every_public_name_documented(self):
        import inspect
        import mockkit
        doc = (SCRIPTS.parent / "references" / "mockkit-api.md").read_text(encoding="utf-8")
        missing = [n for n in mockkit.__all__ if f"`{n}" not in doc]
        for cls in (mockkit.Canvas, mockkit.Rect):
            for n, v in vars(cls).items():
                if not n.startswith("_") and (inspect.isfunction(v) or isinstance(v, property)):
                    if f"`.{n}" not in doc:
                        missing.append(f"{cls.__name__}.{n}")
        self.assertEqual(missing, [], "add these to references/mockkit-api.md")


if __name__ == "__main__":
    unittest.main()
