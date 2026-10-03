"""Tests for render_mockup.py / _mock.py (stdlib unittest). Run: python3 -m unittest discover -s scripts/tests"""

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "tui-design" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import render_mockup as rm  # noqa: E402
from _mock import parse_mock, str_width  # noqa: E402
from _theme import load_theme  # noqa: E402

DEMO = SCRIPTS.parent / "assets" / "demo" / "fleet--normal--80x24.mock"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
HDR = "#! tui-mockup 1\n#! size: {}x{}\n"


def mk(body, cols=20, rows=3, extra=""):
    return HDR.format(cols, rows) + extra + body


def lint(body, cols=20, rows=3, extra="", **kw):
    return parse_mock(mk(body, cols, rows, extra), "t.mock", **kw).findings


def msgs(findings, level):
    return [f.msg for f in findings if f.level == level]


class WidthTests(unittest.TestCase):
    def test_widths(self):
        self.assertEqual(str_width("abc"), 3)
        self.assertEqual(str_width("漢字"), 4)
        self.assertEqual(str_width("é"), 1)       # combining acute = 0 cells
        self.assertEqual(str_width("│─╭"), 3)           # ambiguous counted as 1


class ParseTests(unittest.TestCase):
    def test_style_stack_spans_lines_and_escapes(self):
        m = parse_mock(mk("{status.error bold}ab\ncd{/}e {{x}}\n"), "t.mock")
        self.assertEqual([f for f in m.findings if f.level == "ERROR"], [])
        self.assertEqual(m.grid[0][0].style.fg, "status.error")
        self.assertEqual(m.grid[1][1].style.attrs, ("bold",))
        self.assertIsNone(m.grid[1][2].style.fg)
        self.assertEqual("".join(c.text for c in m.grid[1]), "cde {x}")

    def test_nesting_inherits(self):
        m = parse_mock(mk("{fg.muted on:selection.bg}a{status.error}b{/}c{/}d"), "t.mock")
        row = m.grid[0]
        self.assertEqual((row[1].style.fg, row[1].style.bg), ("status.error", "selection.bg"))
        self.assertEqual((row[2].style.fg, row[2].style.bg), ("fg.muted", "selection.bg"))
        self.assertEqual((row[3].style.fg, row[3].style.bg), (None, None))

    def test_header_and_regions(self):
        m = parse_mock(mk("x", extra="#! title: T\n#! state: busy\n#! region r1 list 0,0,10,3 Services (6)\n"), "t.mock")
        self.assertEqual((m.title, m.state), ("T", "busy"))
        self.assertEqual((m.regions[0].role, m.regions[0].w, m.regions[0].title), ("list", 10, "Services (6)"))
        self.assertEqual([f for f in m.findings if f.level == "ERROR"], [])

    def test_region_errors(self):
        f = lint("x", extra="#! region r1 nonsense 0,0,5,1\n#! region r2 list 15,0,10,1\n#! region r2 list 0,0,1,1\n#! region bad list 0,0,1,1\n")
        e = " | ".join(msgs(f, "ERROR"))
        self.assertIn("unknown region role", e)
        self.assertIn("outside size", e)
        self.assertIn("duplicate region id", e)
        self.assertIn("must match r<N>", e)

    def test_missing_header(self):
        f = parse_mock("hello\n", "t.mock").findings
        self.assertTrue(any("tui-mockup 1" in x.msg for x in f if x.level == "ERROR"))
        self.assertTrue(any("size" in x.msg for x in f if x.level == "ERROR"))


class LintTests(unittest.TestCase):
    def errs(self, body, **kw):
        return msgs(lint(body, **kw), "ERROR")

    def test_clean(self):
        self.assertEqual(lint("{accent.primary bold on:selection.bg}ok{/} ✓ done"), [])

    def test_overflow_and_rows(self):
        e = self.errs("x" * 21)
        self.assertTrue(any("exceeds cols=20" in x for x in e))
        e = self.errs("a\nb\nc\nd")
        self.assertTrue(any("exceed rows=3" in x for x in e))
        f = lint("x" * 21)
        self.assertEqual((f[0].line, f[0].col), (3, 21))

    def test_wide_counts_two(self):
        self.assertTrue(any("exceeds" in x for x in self.errs("漢" * 11)))
        self.assertFalse(any("exceeds" in x for x in self.errs("漢" * 10)))

    def test_tokens_attrs_hex(self):
        self.assertTrue(any("unknown token 'fg.nope'" in x for x in self.errs("{fg.nope}x{/}")))
        self.assertTrue(any("unknown token" in x for x in self.errs("{on:bg.nope}x{/}")))
        self.assertTrue(any("unknown attribute 'blink'" in x for x in self.errs("{blink}x{/}")))
        self.assertTrue(any("raw hex" in x for x in self.errs("{#ff0000}x{/}")))
        self.assertTrue(any("raw hex" in x for x in self.errs("{on:#ff0000}x{/}")))
        self.assertTrue(any("bg token" in x for x in self.errs("{bg.base}x{/}")))
        self.assertEqual(self.errs("{on:fg.default}x{/}"), [])           # any token is a color after on:
        self.assertTrue(any("not a fill" in x for x in self.errs("{on:fg.on-accent}x{/}")))

    def test_balance(self):
        self.assertTrue(any("never closed" in x for x in self.errs("{bold}x")))
        self.assertTrue(any("no open tag" in x for x in self.errs("x{/}")))
        self.assertTrue(any("stray '}'" in x for x in self.errs("a}b")))
        self.assertTrue(any("unterminated" in x for x in self.errs("a{b")))
        self.assertEqual(self.errs("{{ok}}"), [])

    def test_glyph_tiers(self):
        self.assertTrue(any("wide glyph" in x for x in self.errs("🟢 ok")))
        self.assertTrue(any("wide glyph" in x for x in self.errs("漢")))
        self.assertTrue(any("variation selector" in x for x in self.errs("❤\ufe0f")))
        self.assertTrue(any("zero-width joiner" in x for x in self.errs("a\u200db")))
        self.assertTrue(any("private-use" in x for x in self.errs("\ue0b0")))
        self.assertEqual(self.errs("\ue0b0", nerd=True), [])
        self.assertTrue(any("replacement" in x for x in self.errs("\ufffd")))
        f = lint("✔ ⚠")                                   # text-default emoji -> WARN with SAFE replacement
        self.assertEqual(self.errs("✔ ⚠"), [])
        self.assertEqual(len(msgs(f, "WARN")), 2)
        self.assertIn("✓", [x.hint for x in f if "✔" in x.msg][0])
        self.assertTrue(any("EAW=A" in x for x in msgs(lint("±"), "WARN")))   # A outside allow-list
        self.assertEqual(lint("✓✗❯░"), [])                                  # SAFE glyphs
        self.assertTrue(msgs(lint("╭─╮● ▲"), "INFO"))                        # chrome allow-list = INFO
        self.assertEqual(self.errs("╭─╮● ▲"), [])

    def test_strict_ambiguous(self):
        self.assertTrue(any("EAW=A" in x for x in self.errs("╭─╮", strict=True)))
        self.assertTrue(any("EAW=A" in x for x in self.errs("●", strict=True)))

    def test_glyph_findings_aggregate(self):
        f = [x for x in lint("───────") if x.level == "INFO"]
        self.assertEqual(len(f), 1)
        self.assertIn("7x", f[0].msg)

    def test_finding_format(self):
        f = lint("{fg.nope}x{/}")[0]
        self.assertRegex(f.fmt("a.mock"), r"^a\.mock:\d+:\d+: ERROR: .+")


class HeaderTests(unittest.TestCase):
    def test_note_is_accepted_and_repeatable(self):
        m = parse_mock(mk("x", extra="#! note: first\n#! note: second: with colon\n"), "t.mock")
        self.assertEqual(m.notes, ["first", "second: with colon"])
        self.assertEqual(m.findings, [])
        self.assertTrue(any("unknown header key 'nope'" in x for x in msgs(lint("x", extra="#! nope: 1\n"), "WARN")))


class BoxIntegrityTests(unittest.TestCase):
    REG = "#! region r1 panel 0,0,10,4 Box\n"
    BOX = "╭─ T ────╮\n│        │\n│        │\n╰────────╯"

    def errs(self, body, cols=12, rows=4):
        return [f for f in lint(body, cols, rows, extra=self.REG) if f.level == "ERROR"]

    def test_intact_box_and_titles_pass(self):
        self.assertEqual(self.errs(self.BOX), [])
        self.assertEqual(self.errs("╭─ T ─ r─╮\n│        │\n│        │\n╰─ b ────╯"), [])
        self.assertEqual(self.errs("┏━ T ━━━━┓\n┃        ┃\n┃        ┃\n┗━━━━━━━━┛"), [])
        self.assertEqual(self.errs("+- T ----+\n|        |\n|        |\n+--------+"), [])
        self.assertEqual(self.errs("╭─ T ────╮\n├────────┤\n│     ▐  │\n╰────────╯"), [])  # tees, scrollbar glyph

    def test_text_over_sides_corners_and_edges_is_error(self):
        e = self.errs("╭─ T ────╮\n│        X\n│        │\n╰────────╯")
        self.assertEqual(len(e), 1)
        self.assertEqual((e[0].line, e[0].col), (5, 10))                   # magic, size, region, then body row 1
        self.assertIn("region r1 border overwritten at (9,1) by 'X'", e[0].msg)
        self.assertEqual(len(self.errs("╭─ T ────╮\nX        │\n│        │\n╰────────╯")), 1)
        self.assertEqual(len(self.errs("╭─ T ────╮\n│        │\n│        │\n╰───────Z╯")), 1)   # next to corner
        self.assertEqual(len(self.errs("╭─ T ────X\n│        │\n│        │\n╰────────╯")), 1)   # corner itself
        self.assertEqual(len(self.errs("╭Title───╮\n│        │\n│        │\n╰────────╯")), 1)   # title touches corner
        self.assertEqual(self.errs("╭─ T ────╮\n│        │\n│        │\n╰─── x ──╯"), [])           # bottom title ok

    def test_short_row_counts_as_blank_border(self):
        e = self.errs("╭─ T ────╮\n│\n│        │\n╰────────╯")
        self.assertEqual(len(e), 1)
        self.assertIn("(9,1)", e[0].msg)

    def test_non_box_regions_are_ignored(self):
        f = lint("plain text here\nmore text here\n", 20, 4, extra="#! region r1 list 0,0,10,4\n")
        self.assertEqual([x for x in f if x.level == "ERROR"], [])

    def test_mutated_demo_fails_and_all_shipped_mockups_pass(self):
        text = DEMO.read_text(encoding="utf-8")
        bad = text.replace("running   {/} {border.focus}│{/}", "running   {/} {fg.default}X{/}", 1)
        self.assertNotEqual(bad, text)
        errs = [f for f in parse_mock(bad, "d.mock").findings if f.level == "ERROR"]
        self.assertEqual(len(errs), 1)
        self.assertIn("border overwritten at (31,3) by 'X'", errs[0].msg)
        files = sorted((SCRIPTS.parent / "assets" / "mockups").glob("*/*.mock")) + [DEMO]
        self.assertGreaterEqual(len(files), 29)
        for p in files:
            errs = [f for f in parse_mock(p.read_text(encoding="utf-8"), str(p)).findings if f.level == "ERROR"]
            self.assertEqual(errs, [], p.name)


class ChipTests(unittest.TestCase):
    """fg.on-accent (text) on a status/accent fill, at every depth."""

    def render(self, body, depth, theme="catppuccin-mocha"):
        return rm.render(parse_mock(mk(body, 12, 1), "t.mock"), load_theme(theme), depth)

    def test_chip_lints_clean(self):
        self.assertEqual(lint("{fg.on-accent on:status.warning} WARN {/}"), [])
        self.assertEqual(lint("{fg.on-accent bold on:accent.primary} X {/}"), [])

    def test_chip_at_all_depths(self):
        body = "{fg.on-accent on:status.warning} W {/}"
        t = self.render(body, "truecolor")
        self.assertIn("38;2;30;30;46", t)                       # fg.on-accent = base #1e1e2e
        self.assertIn("48;2;249;226;175", t)                    # status.warning #f9e2af fill
        t256 = self.render(body, "256")
        self.assertRegex(t256, r"38;5;\d+;48;5;\d+")
        self.assertNotIn(";2;249", t256)
        t16 = self.render(body, "16")                           # warning = slot 3 -> fill 33 + reverse (text = terminal bg)
        self.assertIn("\x1b[0;33;7m W ", t16)
        self.assertNotIn("38;", t16)
        self.assertNotIn("48;", t16)
        self.assertEqual(self.render(body, "none"), " W" + " " * 10 + "\n")

    def test_chip_16_color_fill_slots(self):
        # bright slots use 9x, plain fills in the other direction still use 4x/10x
        self.assertIn("\x1b[0;31;7m", self.render("{fg.on-accent on:status.error}x{/}", "16"))
        self.assertIn("\x1b[0;34;1;7m", self.render("{fg.on-accent bold on:accent.primary}x{/}", "16"))
        self.assertIn("\x1b[0;43m", self.render("{fg.default on:status.warning}x{/}", "16"))   # fg token as fill source
        from _theme import find_theme_file
        data = json.loads(find_theme_file("catppuccin-mocha").read_text())
        data["ansi16"] = {"status.info": "14"}
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "bright.json"
            path.write_text(json.dumps(data))
            self.assertIn("\x1b[0;96;7m", self.render("{fg.on-accent on:status.info}x{/}", "16", theme=str(path)))

    def test_fill_with_default_or_reverse_spec(self):
        t16 = self.render("{fg.on-accent on:selection.bg}x{/}", "16")     # reverse fill: no color code
        self.assertTrue(t16.startswith("\x1b[0;7m"))


class RenderTests(unittest.TestCase):
    def render(self, text, depth="truecolor", theme="catppuccin-mocha"):
        return rm.render(parse_mock(text, "t.mock"), load_theme(theme), depth)

    def test_frame_is_exact_grid_at_all_depths(self):
        m = parse_mock(DEMO.read_text(encoding="utf-8"), str(DEMO))
        self.assertEqual((m.cols, m.rows), (80, 24))
        for depth in ("truecolor", "256", "16", "none"):
            out = rm.render(m, load_theme("catppuccin-mocha"), depth)
            lines = out.split("\n")
            self.assertEqual(lines.pop(), "")                      # ends with newline
            self.assertEqual(len(lines), 24, depth)
            for ln in lines:
                self.assertEqual(str_width(ANSI.sub("", ln)), 80, (depth, ln))
                if depth != "none":
                    self.assertTrue(ln.endswith("\x1b[0m"))
        self.assertNotIn("\x1b", rm.render(m, load_theme("catppuccin-mocha"), "none"))

    def test_padding_blank_rows_and_truncation(self):
        out = self.render(mk("ab\n", 6, 3, ), "truecolor").split("\n")
        self.assertEqual(len(out), 4)
        self.assertEqual(ANSI.sub("", out[0]), "ab    ")
        self.assertEqual(ANSI.sub("", out[2]), " " * 6)
        self.assertIn("48;2;30;30;46", out[2])                      # bg.base #1e1e2e
        # too-long wide row is truncated to the grid (wide glyph straddling the edge becomes a space)
        out = self.render(mk("abcde漢", 6, 1), "none").split("\n")
        self.assertEqual(out[0], "abcde ")

    def test_depth_encodings(self):
        body = mk("{status.error on:selection.bg bold}x{/}", 4, 1)
        self.assertIn("38;2;243;139;168", self.render(body, "truecolor"))
        t256 = self.render(body, "256")
        self.assertRegex(t256, r"38;5;\d+")
        self.assertNotIn(";2;243", t256)
        t16 = self.render(body, "16")
        self.assertIn(";31", t16)                                    # status.error -> ANSI 1
        self.assertIn(";7", t16)                                     # selection.bg = reverse
        self.assertNotIn("38;", t16)
        self.assertEqual(self.render(body, "none"), "x   \n")

    def test_dim_in_16(self):
        # Use a copy of mocha without per-theme ansi16 overrides so the _tokens.json default applies.
        import json
        from _theme import find_theme_file
        data = json.loads(find_theme_file("catppuccin-mocha").read_text())
        data["ansi16"] = {}
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "plain.json"
            path.write_text(json.dumps(data))
            t16 = self.render(mk("{fg.muted}m{/}", 3, 1), "16", theme=str(path))
        self.assertIn(";2m", t16 + "m")                              # default fg.muted = 'default dim'


class CliTests(unittest.TestCase):
    def run_cli(self, *args, stdin=None):
        return subprocess.run([sys.executable, str(SCRIPTS / "render_mockup.py"), *args], capture_output=True,
                              text=True, input=stdin)

    def test_demo_check_ok(self):
        r = self.run_cli(str(DEMO), "--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(sum("INFO" in l for l in r.stdout.splitlines()), 1)      # collapsed summary
        self.assertIn("--verbose", r.stdout)
        self.assertNotIn("ERROR", r.stdout)
        v = self.run_cli(str(DEMO), "--check", "--verbose")
        self.assertGreater(sum("INFO" in l for l in v.stdout.splitlines()), 5)

    def test_demo_strict_fails(self):
        self.assertEqual(self.run_cli(str(DEMO), "--check", "--strict-ambiguous").returncode, 1)

    def test_lint_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.mock"
            p.write_text(mk("{fg.nope}x{/}\n"), encoding="utf-8")
            r = self.run_cli(str(p), "--check")
            self.assertEqual(r.returncode, 1)
            self.assertRegex(r.stdout, r"bad\.mock:3:1: ERROR: unknown token")
            ok = Path(d) / "ok.mock"
            ok.write_text(mk("{fg.muted}x{/}\n"), encoding="utf-8")
            self.assertEqual(self.run_cli(str(ok), "--check").returncode, 0)
            self.assertEqual(self.run_cli(str(ok), "--depth", "none").stdout.split("\n")[0], "x" + " " * 19)

    def test_missing_file_and_theme(self):
        self.assertEqual(self.run_cli("/nonexistent.mock").returncode, 2)
        self.assertEqual(self.run_cli(str(DEMO), "--theme", "no-such-theme").returncode, 2)

    def test_regions_json_and_out(self):
        with tempfile.TemporaryDirectory() as d:
            rj, out = Path(d) / "r.json", Path(d) / "o.ansi"
            r = self.run_cli(str(DEMO), "--regions-json", str(rj), "-o", str(out), "--depth", "16")
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(rj.read_text())
            self.assertEqual(data["size"], {"cols": 80, "rows": 24})
            self.assertEqual([x["id"] for x in data["regions"]], ["r1", "r2", "r3", "r4", "r5"])
            self.assertEqual(data["regions"][1]["bbox"], {"x": 0, "y": 1, "w": 32, "h": 21})
            self.assertEqual(len(out.read_text().splitlines()), 24)

    def test_stdin(self):
        r = self.run_cli("-", "--depth", "none", stdin=mk("hi", 4, 1))
        self.assertEqual((r.returncode, r.stdout), (0, "hi  \n"))


if __name__ == "__main__":
    unittest.main()
