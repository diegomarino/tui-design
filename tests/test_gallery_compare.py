"""Tests for gallery.py and compare.py (stdlib unittest). Run: python3 -m unittest discover -s scripts/tests"""

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "tui-design" / "scripts"
SKILL = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import compare  # noqa: E402
import gallery  # noqa: E402
from _theme import list_themes  # noqa: E402

ASSETS = SCRIPTS.parent / "assets"
DEMO_DIR = ASSETS / "demo"
DEMO = DEMO_DIR / "fleet--normal--80x24.mock"
MOCK = "#! tui-mockup 1\n#! size: 20x3\n#! title: Tiny {}\n#! state: {}\n{{accent.primary bold}}Hello{{/}} world\n{{status.error}}err{{/}}\n"


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)


class GalleryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def make_design(self, name="tiny"):
        d = self.tmp / name
        d.mkdir()
        (d / "alpha--normal--20x3.mock").write_text(MOCK.format("A", "normal"))
        (d / "alpha--error--20x3.mock").write_text(MOCK.format("A", "error"))
        (d / "beta--normal--20x3.mock").write_text(MOCK.format("B", "normal"))
        (d / "beta--normal--20x3.ansi").write_text("\x1b[31mred\x1b[0m plain\n")      # shadowed by the .mock
        (d / "gamma--busy--10x2.ansi").write_text("\x1b[38;2;1;2;3mabc\x1b[0m\nxyz\n")
        return d

    def test_discover_parses_names_and_prefers_mock(self):
        fr = gallery.discover([self.make_design()])
        keys = sorted((f.design, f.variant, f.state, f.size, f.path.suffix) for f in fr)
        self.assertEqual(keys, [("tiny", "alpha", "error", "20x3", ".mock"), ("tiny", "alpha", "normal", "20x3", ".mock"),
                                ("tiny", "beta", "normal", "20x3", ".mock"), ("tiny", "gamma", "busy", "10x2", ".ansi")])

    def test_gallery_cli_html_is_self_contained(self):
        d = self.make_design()
        themes = ["catppuccin-mocha"] + [t for t in list_themes() if t != "catppuccin-mocha"][:2]
        out = self.tmp / "g.html"
        r = run(SCRIPTS / "gallery.py", d, "--themes", ",".join(themes), "--title", "T <x>", "-o", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        html = out.read_text()
        self.assertNotRegex(html, r'(src|href)=["\']https?:')
        self.assertIn("<title>T &lt;x&gt;</title>", html)
        for sel in ("sel-d", "sel-v", "sel-s", "sel-z", "sel-t", "btn-split", "ArrowRight", "ArrowDown"):
            self.assertIn(sel, html)
        data = json.loads(re.search(r'<script type="application/json" id="data">(.*?)</script>', html, re.S).group(1))
        self.assertEqual(len(data["frames"]), 4 * len(themes))
        self.assertEqual(data["order"]["t"], themes)
        self.assertEqual(data["order"]["s"], ["normal", "busy", "error"])
        # one skeleton per frame, shared by all themes; every placeholder has a colour in the per-theme string
        tpls = re.findall(r'<template id="s(\d+)">(.*?)</template>', html, re.S)
        self.assertEqual(len(tpls), 4)
        for f in data["frames"]:
            body = dict(tpls)[str(f["svg"])]
            self.assertGreaterEqual(len(f["c"]) // 6, 1 + max(int(i) for i in re.findall(r'="@(\d+)"', body)))
        by_theme = {}
        for f in data["frames"]:
            by_theme.setdefault(f["svg"], set()).add(f["c"])
        self.assertTrue(all(len(v) > 1 for v in by_theme.values()))     # themes really change the colours

    def test_lint_summary_and_title_in_caption_data(self):
        d = self.make_design()
        (d / "bad--normal--20x3.mock").write_text("#! tui-mockup 1\n#! size: 20x3\n{nope}x{/}\n")
        out = self.tmp / "g.html"
        self.assertEqual(run(SCRIPTS / "gallery.py", d, "-o", out).returncode, 0)
        html = out.read_text()
        data = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1))
        bad = next(f for f in data["frames"] if f["v"] == "bad")
        self.assertGreaterEqual(bad["cap"]["lint"]["errors"], 1)
        alpha = next(f for f in data["frames"] if f["v"] == "alpha" and f["s"] == "normal")
        self.assertEqual(alpha["cap"]["title"], "Tiny A")

    def test_demo_and_mockups_render(self):
        out = self.tmp / "g.html"
        dirs = [DEMO_DIR] + ([ASSETS / "mockups"] if (ASSETS / "mockups").is_dir() else [])
        r = run(SCRIPTS / "gallery.py", *dirs, "--themes", "catppuccin-mocha", "-o", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("fleet", out.read_text())

    def test_errors(self):
        empty = self.tmp / "empty"
        empty.mkdir()
        self.assertEqual(run(SCRIPTS / "gallery.py", empty, "-o", self.tmp / "x.html").returncode, 2)
        self.assertEqual(run(SCRIPTS / "gallery.py", self.tmp / "nope", "-o", self.tmp / "x.html").returncode, 2)
        self.assertEqual(run(SCRIPTS / "gallery.py", self.make_design(), "--themes", "no-such-theme", "-o", self.tmp / "x.html").returncode, 2)


class CompareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def pair(self, a_text, b_text):
        a, b = self.tmp / "a.mock", self.tmp / "b.mock"
        a.write_text(a_text)
        b.write_text(b_text)
        return a, b

    def diff(self, a, b):
        left, right = compare.load_side(str(a), "a", "catppuccin-mocha"), compare.load_side(str(b), "b", "catppuccin-mocha")
        cols, rows = max(left.grid.cols, right.grid.cols), max(left.grid.rows, right.grid.rows)
        compare.render_side(left, "catppuccin-mocha", cols, rows)
        compare.render_side(right, "catppuccin-mocha", cols, rows)
        return compare.cell_diff(left, right, "catppuccin-mocha")

    def test_identical_has_no_diff(self):
        a, b = self.pair(MOCK.format("A", "normal"), MOCK.format("A", "normal"))
        d = self.diff(a, b)
        self.assertEqual((d["text"], d["bg"], d["fg"], d["any"]), (0, 0, 0, 0))

    def test_text_bg_fg_are_counted_separately(self):
        a = MOCK.format("A", "normal")
        b = a.replace("Hello", "Hallo").replace("{status.error}err", "{status.success}err").replace("world", "{on:selection.bg}world{/}")
        d = self.diff(*self.pair(a, b))
        self.assertEqual(d["text"], 1)                 # e -> a
        self.assertEqual(d["bg"], 5)                   # "world"
        self.assertEqual(d["fg"], 3)                   # "err" recoloured
        self.assertEqual(d["any"], 9)
        self.assertGreaterEqual(d["ink"], 3)             # fg denominator = cells with ink on both sides

    def test_cli_writes_page_and_summary(self):
        a, b = self.pair(MOCK.format("A", "normal"), MOCK.format("A", "normal").replace("Hello", "Hallo"))
        out = self.tmp / "c.html"
        r = run(SCRIPTS / "compare.py", a, b, "--labels", "left,right", "-o", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("| text | 1 |", r.stdout)
        html = out.read_text()
        for needle in ("data-mode=\"overlay\"", "data-mode=\"blink\"", "data-mode=\"diff\"", "text differs"):
            self.assertIn(needle, html)
        self.assertNotRegex(html, r'(src|href)=["\']https?:')

    def test_image_side_disables_cell_diff(self):
        a, _ = self.pair(MOCK.format("A", "normal"), MOCK.format("A", "normal"))
        svg = self.tmp / "i.svg"
        svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10"/></svg>')
        out = self.tmp / "c.html"
        r = run(SCRIPTS / "compare.py", svg, a, "-o", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("unavailable", r.stdout)
        self.assertNotIn('data-mode="diff"', out.read_text())

    def test_different_sizes_use_union(self):
        a, b = self.pair(MOCK.format("A", "normal"), MOCK.format("A", "normal").replace("20x3", "24x4"))
        d = self.diff(a, b)
        self.assertEqual((d["cols"], d["rows"]), (24, 4))

    def test_missing_file_is_exit_2(self):
        self.assertEqual(run(SCRIPTS / "compare.py", self.tmp / "nope.ansi", DEMO, "-o", self.tmp / "c.html").returncode, 2)


if __name__ == "__main__":
    unittest.main()


class GalleryExportTests(unittest.TestCase):
    """--export writes txt/ansi/svg(/png) per frame x theme; the exported ANSI equals a direct render."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_export_matches_direct_render(self):
        demo = SKILL / "assets" / "demo"
        out = self.tmp / "exp"
        r = run(SCRIPTS / "gallery.py", demo, "--themes", "catppuccin-latte", "--export", out, "--formats", "txt,ansi,svg")
        self.assertEqual(r.returncode, 0, r.stderr)
        base = out / "demo" / "fleet--normal--80x24--catppuccin-latte"
        for ext in ("txt", "ansi", "svg"):
            self.assertTrue(base.with_suffix("." + ext).exists(), ext)
        direct = run(SCRIPTS / "render_mockup.py", demo / "fleet--normal--80x24.mock", "--theme", "catppuccin-latte").stdout
        from _ansi import parse_ansi
        a, b = parse_ansi(direct, 80, 24), parse_ansi(base.with_suffix(".ansi").read_text(), 80, 24)
        self.assertEqual([repr(c) for row in a.cells for c in row], [repr(c) for row in b.cells for c in row])
        self.assertIn("api-gateway", base.with_suffix(".txt").read_text())
        self.assertNotIn("\x1b", base.with_suffix(".txt").read_text())
        self.assertFalse((out / "gallery.html").exists())          # --export alone writes no page

    def test_page_carries_export_data(self):
        out = self.tmp / "g.html"
        self.assertEqual(run(SCRIPTS / "gallery.py", SKILL / "assets" / "demo", "-o", out).returncode, 0)
        html = out.read_text()
        for needle in ('data-x="png"', '"ansi":[', '"text":[', "Copy ANSI"):
            self.assertIn(needle, html)

    def test_bad_format_is_usage_error(self):
        r = run(SCRIPTS / "gallery.py", SKILL / "assets" / "demo", "--export", self.tmp / "x", "--formats", "gif")
        self.assertEqual(r.returncode, 2)
