"""Tests for mockkit.py and the .mock features it relies on (stdlib unittest)."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "tui-design" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import render_mockup as rm  # noqa: E402
from _mock import parse_mock  # noqa: E402
from _theme import load_theme  # noqa: E402
from mockkit import Canvas, CanvasError, Col, bar, fit, tab_runs, width  # noqa: E402

DEMO = SCRIPTS.parent / "assets" / "demo" / "fleet--normal--80x24.mock"


def build_fleet() -> Canvas:
    """The canonical Fleet demo screen, drawn with mockkit."""
    c = Canvas(80, 24, title="Fleet — list + detail demo (canonical starter screen)", state="normal")
    # header band
    c.region("r1", "header", 0, 0, 80, 1)
    c.fill(0, 0, 80, 1, "on:statusbar.bg")
    c.text(0, 0, " Fleet ", "accent.primary bold")
    c.text(7, 0, "│", "border.default")
    c.text(8, 0, " 1 Services ", "tab.active.fg bold on:tab.active.bg")
    c.text(20, 0, " 2 Logs ", "tab.inactive.fg")
    c.text(28, 0, " 3 Config ", "tab.inactive.fg")
    c.rtext(80, 0, "prod-eu · 12:04:31 ", "statusbar.fg")
    # list pane
    c.box(0, 1, 32, 21, "Services (6)", spec="border.focus", region=("r2", "list"))
    c.fill(1, 2, 30, 1, "on:selection.bg")
    c.text(2, 2, "❯", "accent.primary bold")
    c.text(4, 2, "●", "status.success")
    c.text(6, 2, "api-gateway   ", "selection.fg bold")
    c.text(20, 2, "running   ", "status.success")
    rows = [("●", "status.success", "auth          ", "running   ", "fg.muted"),
            ("▲", "status.warning", "billing       ", "degraded  ", "status.warning"),
            ("✗", "status.error", "search        ", "failed    ", "status.error"),
            ("●", "status.success", "worker        ", "running   ", "fg.muted"),
            ("·", "fg.faint", "cron          ", "stopped   ", "fg.faint")]
    for i, (g, gs, name, st, ss) in enumerate(rows):
        y = 3 + i
        c.text(4, y, g, gs)
        c.text(6, y, name, "fg.faint" if g == "·" else "fg.default")
        c.text(20, y, st, ss)
    # detail pane
    c.box(32, 1, 48, 21, "api-gateway", region=("r3", "detail"))
    c.text(34, 3, "Status    ", "fg.muted")
    c.text(44, 3, "● running", "status.success")
    c.text(53, 3, " · 3/3 replicas", "fg.muted")
    for y, k, v in ((4, "Version   ", "v2.4.1"), (5, "Uptime    ", "6d 4h")):
        c.text(34, y, k, "fg.muted")
        c.text(44, y, v, "fg.default")
    for y, k, frac, ramp, pct in ((7, "CPU       ", 6, "ramp.low", " 31%"), (8, "Memory    ", 13, "ramp.mid", " 68%"),
                                  (9, "Errors    ", 18, "ramp.high", " 92%")):
        c.text(34, y, k, "fg.muted")
        filled, empty = bar(frac / 20, 20)
        c.text(44, y, filled, ramp)
        c.text(44 + frac, y, empty[:20 - frac], "fg.faint")
        c.text(64, y, pct, "fg.default")
    c.text(34, 11, "Recent events", "fg.title bold")
    for y, t, g, gs, msg, ms in ((12, "12:01  ", "✓", "status.success", " deploy v2.4.1 finished", "fg.default"),
                                 (13, "11:58  ", "▲", "status.warning", " p95 latency 820 ms", "fg.default"),
                                 (14, "11:40  ", "·", "fg.faint", " scaled 2 → 3 replicas", "fg.muted"),
                                 (15, "11:02  ", "✗", "status.error", " health check timeout", "fg.default")):
        c.text(34, y, t, "fg.faint")
        c.text(41, y, g, gs)
        c.text(42, y, msg, ms)
    # message line and key hints
    c.region("r4", "statusbar", 0, 22, 80, 1)
    c.text(1, 22, "✓", "status.success")
    c.text(2, 22, " deployed api-gateway v2.4.1", "fg.default")
    c.text(30, 22, " · 2m ago", "fg.faint")
    c.region("r5", "keybar", 0, 23, 80, 1)
    c.keybar(23, [("↑↓", "select"), ("enter", "open"), ("/", "filter"), ("r", "restart"), ("tab", "pane")])
    return c


def build_fleet_helpers() -> Canvas:
    """The same Fleet screen with the widget helpers: layout by Rect splits, no coordinate arithmetic."""
    c = Canvas(80, 24, title="Fleet — list + detail demo (canonical starter screen)", state="normal")
    _, body, msg, keys = c.rect.split_v([1, "*", 1, 1])
    c.band(0, [(" Fleet ", "accent.primary bold"), ("│", "border.default")] + tab_runs(["Services", "Logs", "Config"]),
           [("prod-eu · 12:04:31 ", "statusbar.fg")], pad=0, region="header")
    left, right = body.split_h([32, "*"])
    lst = c.panel(left, "Services (6)", role="list", focus=True)
    svc = [("running", "api-gateway", ("running", "status.success")), ("running", "auth", ("running", "fg.muted")),
           ("warn", "billing", ("degraded", "status.warning")), ("fail", "search", ("failed", "status.error")),
           ("running", "worker", ("running", "fg.muted")), ("pending", ("cron", "fg.faint"), ("stopped", "fg.faint"))]
    c.table(lst, header=False, selected=0, cursor="❯", rows=[[c.status(g), n, st] for g, n, st in svc],
            columns=[Col("", 1), Col("", 13, sel="selection.fg bold"), Col("")])
    det = c.panel(right, "api-gateway", role="detail").inset(1, 1, 1, 0)
    y = c.kv(det.x, det.y, [("Status", [("● running", "status.success"), (" · 3/3 replicas", "fg.muted")]),
                            ("Version", "v2.4.1"), ("Uptime", "6d 4h"), None], key_w=10)
    for i, (label, v) in enumerate((("CPU", .31), ("Memory", .68), ("Errors", .92))):
        c.text(det.x, y + i, label, "fg.muted")
        c.gauge(det.x + 10, y + i, 24, v, label_w=4)
    c.text(det.x, y + 4, "Recent events", "fg.title bold")
    for i, (t, g, text, sp) in enumerate((("12:01", "ok", "deploy v2.4.1 finished", "fg.default"),
                                          ("11:58", "warn", "p95 latency 820 ms", "fg.default"),
                                          ("11:40", "pending", "scaled 2 → 3 replicas", "fg.muted"),
                                          ("11:02", "fail", "health check timeout", "fg.default"))):
        c.runs(det.x, y + 5 + i, [(t + "  ", "fg.faint"), c.status(g), (" " + text, sp)])
    c.region("r4", "statusbar", *msg)
    c.message(msg.y, "ok", "deployed api-gateway v2.4.1", "2m ago")
    c.keybar(keys.y, [("↑↓", "select"), ("enter", "open"), ("/", "filter"), ("r", "restart"), ("tab", "pane")],
             region="keybar")
    return c


def cell_grid(mock):
    """Normalized (text, fg, bg, attrs) grid of the rendered frame: blank cells ignore their foreground."""
    out = []
    for y in range(mock.rows):
        row = rm.fit_row(mock.grid[y], mock.cols) if y < len(mock.grid) else []
        line = []
        for c in row:
            fg = c.style.fg or "fg.default"
            attrs = tuple(sorted(c.style.attrs))
            if c.text == " " and not set(attrs) & {"inverse", "underline", "strike"}:
                fg, attrs = None, ()
            line.append((c.text, fg, c.style.bg or "bg.base", attrs))
        out.append(line)
    return out


class FleetEquivalence(unittest.TestCase):
    def test_check_passes_and_grid_equals_demo(self):
        c = build_fleet()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "fleet--normal--80x24.mock"
            c.save(p)
            r = subprocess.run([sys.executable, str(SCRIPTS / "render_mockup.py"), str(p), "--check"],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("0 error(s), 0 warning(s)", r.stderr)
            mine = parse_mock(p.read_text(encoding="utf-8"), str(p))
        orig = parse_mock(DEMO.read_text(encoding="utf-8"), str(DEMO))
        self.assertEqual(cell_grid(mine), cell_grid(orig))
        self.assertEqual([(r.id, r.role, r.x, r.y, r.w, r.h, r.title) for r in mine.regions],
                         [(r.id, r.role, r.x, r.y, r.w, r.h, r.title) for r in orig.regions])
        for depth in ("none",):                    # plain text identical, row for row
            th = load_theme("catppuccin-mocha")
            self.assertEqual(rm.render(mine, th, depth), rm.render(orig, th, depth))

    def test_helper_build_equals_demo(self):
        c = build_fleet_helpers()
        self.assertEqual(c.lint(), [])
        mine = parse_mock(c.to_mock())
        orig = parse_mock(DEMO.read_text(encoding="utf-8"), str(DEMO))
        self.assertEqual(cell_grid(mine), cell_grid(orig))
        self.assertEqual([(r.id, r.role, r.x, r.y, r.w, r.h, r.title) for r in mine.regions],
                         [(r.id, r.role, r.x, r.y, r.w, r.h, r.title) for r in orig.regions])
        self.assertEqual((mine.focus, mine.selected), (orig.focus, orig.selected))


class CanvasBasics(unittest.TestCase):
    def test_merge_escape_header(self):
        c = Canvas(20, 3, title="T", state="busy", theme="nord-dark")
        c.text(0, 0, "ab{c}", "fg.muted")
        c.text(5, 0, "d", "fg.muted")
        c.note("n1")
        c.note("n2")
        out = c.to_mock().split("\n")
        self.assertEqual(out[:6], ["#! tui-mockup 1", "#! size: 20x3", "#! title: T", "#! state: busy",
                                   "#! theme: nord-dark", "#! note: n1"])
        self.assertIn("{fg.muted}ab{{c}}d{/}", out)
        m = parse_mock(c.to_mock())
        self.assertEqual(m.notes, ["n1", "n2"])
        self.assertEqual([f for f in m.findings if f.level in ("ERROR", "WARN")], [])

    def test_trailing_blanks_trimmed_and_blank_rides_in_run(self):
        c = Canvas(20, 2)
        c.text(0, 0, "a", "fg.muted")
        c.text(2, 0, "b", "fg.muted")
        row = c.to_mock().split("\n")[-3]
        self.assertEqual(row, "{fg.muted}a b{/}")

    def test_bg_preserved_under_text_and_fill(self):
        c = Canvas(10, 1)
        c.fill(0, 0, 10, 1, "selection.bg")          # bare bg token accepted
        c.text(1, 0, "x", "status.error")
        self.assertIn("{status.error on:selection.bg} x        {/}", c.to_mock())   # blanks join the run

    def test_overflow_and_bad_input_raise(self):
        c = Canvas(10, 3)
        for bad in (lambda: c.text(8, 0, "abc"), lambda: c.text(-1, 0, "a"), lambda: c.text(0, 3, "a"),
                    lambda: c.text(0, 0, "a\nb"), lambda: c.text(0, 0, "x", "fg.nope"),
                    lambda: c.text(0, 0, "x", "#ff0000"), lambda: c.text(0, 0, "x", "bg.base"),
                    lambda: c.text(0, 0, "x", "on:fg.on-accent"), lambda: c.text(0, 0, "x", "blink"),
                    lambda: c.fill(0, 0, 11, 1, "on:bg.raised"), lambda: c.fill(0, 0, 1, 1, "fg.muted"),
                    lambda: c.box(0, 0, 11, 3), lambda: c.box(0, 0, 10, 3, border="wavy"),
                    lambda: c.region("x1", "list", 0, 0, 1, 1), lambda: c.region("r1", "nope", 0, 0, 1, 1),
                    lambda: c.region("r1", "list", 5, 0, 9, 1)):
            with self.assertRaises(CanvasError):
                bad()
        self.assertEqual(c.to_mock().count("{"), 0)       # nothing was written by a failed call

    def test_wide_glyphs_use_two_cells(self):
        c = Canvas(6, 1)
        self.assertEqual(c.text(0, 0, "漢字", "fg.muted"), 4)
        with self.assertRaises(CanvasError):
            c.text(5, 0, "漢")
        c.text(1, 0, "x", None)                            # cuts 漢 in half
        self.assertTrue(c.plain().startswith(" x"))
        self.assertEqual(width("漢a"), 3)
        # to_mock keeps one cell per 2-wide glyph; the linter flags wide glyphs, so save() refuses
        c2 = Canvas(6, 1)
        c2.text(0, 0, "漢")
        with self.assertRaises(CanvasError):
            c2.save(Path(tempfile.gettempdir()) / "never-written.mock")

    def test_helpers(self):
        self.assertEqual(fit("abcdef", 4), "abc⋯")
        self.assertEqual(fit("ab", 4, "r"), "  ab")
        self.assertEqual(bar(0.5, 4), ("██", "░░"))
        self.assertEqual(width(fit("漢字漢", 5)), 5)


class BorderGuard(unittest.TestCase):
    def test_text_onto_border_raises_unless_forced(self):
        c = Canvas(20, 5)
        c.box(0, 0, 20, 5, "T", region=("r1", "panel"))
        for bad in (lambda: c.text(19, 2, "x"), lambda: c.text(0, 2, "x"), lambda: c.text(5, 0, "x"),
                    lambda: c.text(10, 4, "x"), lambda: c.runs(18, 2, [("a", None), ("b", None)])):
            with self.assertRaises(CanvasError):
                bad()
        c.text(1, 2, "ok")
        c.text(19, 2, "|", force=True)
        self.assertIn("|", c.plain().split("\n")[2])

    def test_second_box_and_lines_guarded(self):
        c = Canvas(20, 6)
        c.box(0, 0, 10, 6)
        with self.assertRaises(CanvasError):
            c.box(9, 0, 10, 6)                               # shares a border column
        c.box(10, 0, 10, 6)
        with self.assertRaises(CanvasError):
            c.hline(0, 2, 10)                                # runs over the first box's sides
        c.hline(1, 2, 8)
        with self.assertRaises(CanvasError):
            c.text(3, 2, "x")                                # hline is border too
        c.hline(0, 4, 10, ends=("├", "┤"), force=True)
        with self.assertRaises(CanvasError):
            c.vline(5, 1, 4)                                 # crosses the hline at y=2
        c.vline(5, 1, 1)

    def test_title_must_fit_and_stay_off_corners(self):
        c = Canvas(20, 3)
        with self.assertRaises(CanvasError):
            c.box(0, 0, 10, 3, "far too long a title")
        c.box(0, 0, 12, 3, "a", title_right="b")
        self.assertEqual(c.plain().split("\n")[0], "╭─ a ── b ─╮")

    def test_clear_allows_modal_over_boxes(self):
        c = Canvas(20, 6)
        c.box(0, 0, 20, 6)
        c.box(5, 1, 10, 4, "M", clear=True, fill="bg.raised", border="heavy")
        self.assertIn("┏", c.plain())
        m = parse_mock(c.to_mock())
        self.assertEqual([f for f in m.findings if f.level == "ERROR"], [])

    def test_regions_sorted_and_auto_id(self):
        c = Canvas(20, 6)
        c.box(0, 0, 10, 6, "A", region="list")
        c.region("r5", "keybar", 0, 5, 20, 1)
        c.box(10, 0, 10, 5, "B", region="detail")
        regs = [l for l in c.to_mock().split("\n") if l.startswith("#! region")]
        self.assertEqual(regs, ["#! region r1 list 0,0,10,6 A", "#! region r2 detail 10,0,10,5 B",
                                "#! region r5 keybar 0,5,20,1"])

    def test_keybar_overlap_raises(self):
        c = Canvas(30, 2)
        with self.assertRaises(CanvasError):
            c.keybar(1, [("a", "a long left verb"), ("b", "another long verb")])


class ModuleDocExample(unittest.TestCase):
    def test_docstring_example_runs_and_lints(self):
        import mockkit
        src = mockkit.__doc__.split("Example", 1)[1].split("API (", 1)[0]
        code = "\n".join(l[4:] for l in src.splitlines()[1:] if l.startswith("    "))
        with tempfile.TemporaryDirectory() as d:
            code = code.replace('"hello--normal--40x8.mock"', repr(str(Path(d) / "hello--normal--40x8.mock")))
            exec(compile(code, "<docstring>", "exec"), {})
            p = Path(d) / "hello--normal--40x8.mock"
            r = subprocess.run([sys.executable, str(SCRIPTS / "render_mockup.py"), str(p), "--check"],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("0 error(s), 0 warning(s)", r.stderr)


if __name__ == "__main__":
    unittest.main()
