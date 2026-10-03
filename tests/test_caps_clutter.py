"""Tests for the capability profile (`#! caps:`), --glyphs inventory, mockkit junction ends, em dash tier and
ansi_grid --clutter (stdlib unittest). Run: python3 -m unittest discover -s scripts/tests"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "tui-design" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import ansi_grid  # noqa: E402
import render_mockup as rm  # noqa: E402
from _ansi import parse_ansi  # noqa: E402
from _mock import ascii_fallback, parse_caps, parse_mock, v9_fallbacks  # noqa: E402
from _theme import load_theme  # noqa: E402
from mockkit import Canvas, CanvasError  # noqa: E402

DEMO = SCRIPTS.parent / "assets" / "demo" / "fleet--normal--80x24.mock"
CLUTTER = Path(__file__).resolve().parent / "fixtures" / "clutter--bad--60x14.mock"
HDR = "#! tui-mockup 1\n#! size: 20x3\n"


def lint(body, extra="", **kw):
    return parse_mock(HDR + extra + body, "t.mock", **kw).findings


def msgs(findings, level):
    return [f.msg for f in findings if f.level == level]


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)


class CapsParseTests(unittest.TestCase):
    def test_parse_and_defaults(self):
        c, errs = parse_caps("attrs=bold,dim,inverse colors=16 glyphs=unicode widgets=tabs,list")
        self.assertEqual(errs, [])
        self.assertEqual((c.attrs, c.colors, c.glyphs, c.widgets), (("bold", "dim", "inverse"), "16", "unicode", ("tabs", "list")))
        self.assertEqual(c.depth, "16")
        d, _ = parse_caps("")
        self.assertEqual((len(d.attrs), d.colors, d.glyphs, d.depth), (6, "truecolor", "unicode", "truecolor"))
        self.assertEqual(parse_caps("colors=none")[0].depth, "nocolor")
        self.assertEqual(parse_caps("attrs=none")[0].attrs, ())

    def test_bad_values_are_errors(self):
        for bad in ("attrs=blink", "colors=8", "glyphs=emoji", "speed=fast", "attrs"):
            self.assertTrue(parse_caps(bad)[1], bad)
        f = lint("x", extra="#! caps: colors=8\n")
        self.assertTrue(any("caps" in m for m in msgs(f, "ERROR")))

    def test_header_line_is_not_an_unknown_key(self):
        f = lint("x", extra="#! caps: attrs=bold source=test-card\n")
        self.assertEqual([x for x in f if x.level in ("ERROR", "WARN")], [])
        self.assertTrue(any("duplicate" in m for m in msgs(lint("x", extra="#! caps: attrs=bold\n#! caps: colors=16\n"), "ERROR")))


class CapsEnforcementTests(unittest.TestCase):
    def test_attribute_outside_attrs_is_error_naming_the_cell(self):
        f = lint("ab{italic}cd{/} {bold}e{/}", extra="#! caps: attrs=bold,dim\n")
        e = msgs(f, "ERROR")
        self.assertEqual(len(e), 1)
        self.assertIn("'italic'", e[0])
        self.assertIn("x=2,y=0", e[0])
        self.assertEqual(lint("{italic}x{/}"), [])                        # default profile allows everything

    def test_attribute_from_cli_flag(self):
        e = msgs(lint("{strike}x{/}", caps="attrs=bold"), "ERROR")
        self.assertEqual(len(e), 1)
        # CLI overrides the header key by key
        e = msgs(lint("{strike}x{/}", extra="#! caps: attrs=bold colors=16\n", caps="attrs=bold,strike"), "ERROR")
        self.assertEqual(e, [])

    def test_ascii_glyphs_error_with_v9_hint(self):
        f = lint("ok ✓ ─", extra="#! caps: glyphs=ascii\n")
        e = [x for x in f if x.level == "ERROR"]
        self.assertEqual(len(e), 2)
        check = next(x for x in e if "✓" in x.msg)
        self.assertIn("[ok]", check.hint)
        self.assertEqual(lint("plain ascii | + -", extra="#! caps: glyphs=ascii source=docs\n"), [])

    def test_unicode_blocks_nerd_and_nerd_allows_it(self):
        self.assertTrue(msgs(lint("", extra="#! caps: glyphs=unicode\n"), "ERROR"))
        self.assertTrue(msgs(lint("", extra="#! caps: glyphs=unicode\n", nerd=True), "ERROR"))   # explicit caps win
        self.assertEqual(msgs(lint("", extra="#! caps: glyphs=nerd\n"), "ERROR"), [])
        self.assertTrue(msgs(lint(""), "ERROR"))                                                 # today's default
        self.assertEqual(msgs(lint("", nerd=True), "ERROR"), [])

    def test_colors_16_gives_info_and_default_depth(self):
        f = lint("x", extra="#! caps: colors=16\n")
        info = [x for x in f if x.level == "INFO"]
        self.assertEqual(len(info), 1)
        self.assertIn("--depth 16", info[0].msg)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.mock"
            p.write_text(HDR + "#! caps: colors=16\n{accent.primary}hi{/}\n\n\n")
            out16 = run(SCRIPTS / "render_mockup.py", p).stdout
            out_tc = run(SCRIPTS / "render_mockup.py", p, "--depth", "truecolor").stdout
            self.assertNotIn("38;2;", out16)
            self.assertIn("38;2;", out_tc)
            chk = run(SCRIPTS / "render_mockup.py", p, "--check")
            self.assertIn("caps colors=16", chk.stdout)
            self.assertNotIn("ambiguous-width", chk.stdout)             # not collapsed into the glyph summary
            nc = Path(d) / "b.mock"
            nc.write_text(HDR + "{accent.primary bold}hi{/}\n\n\n")
            out = run(SCRIPTS / "render_mockup.py", nc, "--caps", "colors=none").stdout
            self.assertNotIn("38;", out)
            self.assertIn(";1", out.split("hi")[0])                      # bold survives (nocolor keeps attributes)

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.mock"
            p.write_text(HDR + "{italic}x{/}\n\n\n")
            self.assertEqual(run(SCRIPTS / "render_mockup.py", p, "--check").returncode, 0)
            r = run(SCRIPTS / "render_mockup.py", p, "--check", "--caps", "attrs=bold,dim,inverse")
            self.assertEqual(r.returncode, 1)
            self.assertIn("italic", r.stdout)

    def test_shipped_demo_passes_default_profile(self):
        self.assertEqual([f for f in parse_mock(DEMO.read_text(encoding="utf-8"), "d").findings if f.level == "ERROR"], [])


class MockkitCapsTests(unittest.TestCase):
    def test_header_written_and_roundtrips(self):
        c = Canvas(20, 4, caps="attrs=bold,dim colors=16")
        c.text(1, 1, "hi", "bold")
        self.assertIn("#! caps: attrs=bold,dim colors=16", c.to_mock())
        with tempfile.TemporaryDirectory() as d:
            p = c.save(Path(d) / "x--normal--20x4.mock")
            self.assertEqual(parse_mock(p.read_text(), str(p)).caps.colors, "16")
        self.assertNotIn("#! caps", Canvas(20, 4).to_mock())

    def test_writes_violating_caps_raise(self):
        c = Canvas(20, 4, caps="attrs=bold,dim")
        for bad in (lambda: c.text(0, 0, "x", "italic"), lambda: c.text(0, 0, "x", "fg.muted underline")):
            with self.assertRaises(CanvasError):
                bad()
        c.box(0, 0, 10, 4, "T")                              # default title_spec is bold: allowed here
        with self.assertRaises(CanvasError):
            c.box(10, 0, 10, 4, "T", title_spec="fg.title italic")
        a = Canvas(12, 4, caps="glyphs=ascii attrs=bold")
        with self.assertRaises(CanvasError) as cm:
            a.box(0, 0, 12, 4)                                 # rounded corners are non-ASCII
        self.assertIn("ascii", str(cm.exception))
        a.box(0, 0, 12, 4, border="ascii")
        with self.assertRaises(CanvasError) as cm:
            a.text(2, 1, "✓")
        self.assertIn("[ok]", str(cm.exception))
        a.text(2, 1, "ok", "bold")
        with self.assertRaises(CanvasError):
            Canvas(10, 3, caps="glyphs=unicode").text(0, 0, "")
        Canvas(10, 3, caps="glyphs=nerd").text(0, 0, "")
        with self.assertRaises(CanvasError):
            Canvas(10, 3, caps="colors=7")

    def test_box_fails_before_drawing_anything(self):
        c = Canvas(12, 4, caps="attrs=dim")
        with self.assertRaises(CanvasError):
            c.box(0, 0, 12, 4, "T")                          # default title_spec carries bold
        self.assertEqual(c.plain().strip(), "")


class MockkitJoinTests(unittest.TestCase):
    def two_boxes(self):
        c = Canvas(20, 6)
        c.box(0, 0, 10, 6)
        c.box(10, 0, 10, 6)
        return c

    def test_tee_ends_join_borders_without_force(self):
        c = self.two_boxes()
        c.hline(0, 2, 10, ends=("├", "┤"))
        row = c.plain().split("\n")[2]
        self.assertEqual((row[0], row[9]), ("├", "┤"))
        c2 = Canvas(11, 6)
        c2.box(0, 0, 11, 6)
        c2.vline(5, 0, 6, ends=("┬", "┴"))
        rows = c2.plain().split("\n")
        self.assertEqual((rows[0][5], rows[5][5]), ("┬", "┴"))
        self.assertTrue(all(rows[y][5] == "│" for y in range(1, 5)))
        c2.save(Path(tempfile.mkdtemp()) / "j.mock")

    def test_only_junction_glyphs_skip_force(self):
        c = self.two_boxes()
        with self.assertRaises(CanvasError):
            c.hline(0, 2, 10, ends=("x", "y"))               # not junction glyphs
        with self.assertRaises(CanvasError):
            c.hline(0, 3, 10, ends=("│", "│"))
        with self.assertRaises(CanvasError):
            c.hline(0, 4, 10)                                # no ends: still protected
        c.hline(0, 4, 10, ends=("x", "y"), force=True)   # force keeps working
        c = self.two_boxes()
        with self.assertRaises(CanvasError):
            c.hline(0, 2, 11, ends=("├", "┤"))               # interior crossing of the second box's border is still refused

    def test_only_the_ends_are_exempt(self):
        c = self.two_boxes()
        c.hline(0, 2, 10, ends=("├", "┤"))
        with self.assertRaises(CanvasError):
            c.vline(5, 1, 4, ends=("┬", "┴"))                # middle cell (5,2) is a protected hline cell


class DashTierTests(unittest.TestCase):
    def test_em_and_en_dash_are_info(self):
        for d in ("—", "–"):
            f = lint(f"a {d} b")
            self.assertEqual(msgs(f, "WARN"), [], d)
            self.assertEqual(len(msgs(f, "INFO")), 1, d)
            self.assertEqual(msgs(f, "ERROR"), [], d)
        self.assertTrue(msgs(lint("a — b", strict=True), "ERROR"))       # --strict-ambiguous still promotes it
        self.assertTrue(msgs(lint("±"), "WARN"))                         # other A-class glyphs keep their WARN

    def test_dash_fallback(self):
        self.assertEqual(ascii_fallback("—"), "-")


class V9Tests(unittest.TestCase):
    def test_v9_parse_and_tolerates_absence(self):
        fb = v9_fallbacks()
        self.assertEqual((fb.get("✓"), fb.get("▲"), fb.get("╭"), fb.get("▂")), ("[ok]", "[!]", "+", "."))
        self.assertEqual(ascii_fallback("└"), "+")
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(v9_fallbacks(Path(d) / "missing.md"), {})
            nov9 = Path(d) / "x.md"
            nov9.write_text("# nothing\n")
            self.assertEqual(v9_fallbacks(nov9), {})
        self.assertEqual(ascii_fallback("⌘"), "")                        # unknown glyph -> empty


class GlyphInventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.a = Path(self.tmp.name) / "a.mock"
        self.a.write_text(HDR + "✓ ✓ ● — ✔\n│\n\n")
        self.b = Path(self.tmp.name) / "b.mock"
        self.b.write_text(HDR + "✓ 🟢 \n\n\n")

    def test_table_columns_and_tiers(self):
        rows, rc = rm.glyph_inventory([str(self.a), str(self.b)], False, False, None)
        by = {r["glyph"]: r for r in rows}
        self.assertEqual(rc, 1)                                           # 🟢 and PUA are ERROR
        self.assertEqual((by["✓"]["count"], by["✓"]["tier"], by["✓"]["ascii_fallback"]), (3, "OK", "[ok]"))
        self.assertEqual(by["✓"]["first_file"], str(self.a))
        self.assertEqual((by["🟢"]["tier"], by["🟢"]["emoji"], by["🟢"]["eaw"]), ("ERROR", "emoji_presentation", "W"))
        self.assertEqual((by["✔"]["tier"], by["✔"]["emoji"]), ("WARN", "text_default"))
        self.assertEqual((by["—"]["tier"], by["—"]["name"]), ("INFO", "em dash"))
        self.assertTrue(by[""]["pua"])
        self.assertEqual(by["●"]["codepoint"], "U+25CF")
        self.assertNotIn("a", by)                                         # ASCII is not inventoried
        tiers = [r["tier"] for r in rows]
        self.assertEqual(tiers, sorted(tiers, key=lambda t: -rm.TIER_RANK[t]))   # worst first

    def test_cli_md_json_and_exit(self):
        r = run(SCRIPTS / "render_mockup.py", "--glyphs", self.a)
        self.assertEqual(r.returncode, 0)
        self.assertIn("| Glyph | Code | Name | EAW | Emoji | PUA/Nerd | Tier | ASCII fallback | Count | First file |", r.stdout)
        self.assertIn("U+2713", r.stdout)
        r = run(SCRIPTS / "render_mockup.py", "--glyphs", self.a, self.b, "--format", "json")
        self.assertEqual(r.returncode, 1)
        doc = json.loads(r.stdout)
        self.assertEqual(doc["errors"], 2)
        self.assertEqual(len(doc["files"]), 2)
        self.assertEqual(run(SCRIPTS / "render_mockup.py", "--glyphs", self.a, "--caps", "glyphs=ascii").returncode, 1)
        self.assertEqual(run(SCRIPTS / "render_mockup.py", self.a, self.b).returncode, 2)     # several files need --glyphs

    def test_demo_inventory_is_clean(self):
        r = run(SCRIPTS / "render_mockup.py", "--glyphs", DEMO, "--format", "json")
        self.assertEqual(r.returncode, 0)
        glyphs = {g["glyph"]: g for g in json.loads(r.stdout)["glyphs"]}
        self.assertIn("╭", glyphs)
        self.assertEqual(glyphs["╭"]["ascii_fallback"], "+")


def metrics(path):
    return json.loads(run(SCRIPTS / "ansi_grid.py", path, "--clutter", "--format", "json").stdout)


class ClutterTests(unittest.TestCase):
    def test_demo_metrics(self):
        m = metrics(DEMO)
        self.assertEqual(m["size"], {"cols": 80, "rows": 24})
        self.assertEqual(m["border_nesting"]["max_depth"], 1)
        self.assertFalse(m["border_nesting"]["notable"])
        self.assertEqual(m["border_nesting"]["boxes"], 2)
        self.assertEqual(m["repeated_markers"]["items"], [])
        self.assertGreater(m["chrome_share"]["share_pct"], 10)
        self.assertFalse(m["chrome_share"]["notable"])                       # 30.8 % is below the calibrated 50 %
        self.assertEqual(m["duplicate_signals"]["rows_flagged"], 0)          # "✗ search  failed": glyph + word is the baseline
        self.assertTrue(any("Services" in b["region"] for b in m["blank_share"]["regions"]))
        self.assertEqual(set(m["verdicts"]), {"chrome_share", "border_nesting", "repeated_markers", "duplicate_signals", "blank_share"})

    def test_cluttered_fixture_trips_every_threshold(self):
        m = metrics(CLUTTER)
        self.assertTrue(m["chrome_share"]["notable"])
        self.assertGreater(m["chrome_share"]["share_pct"], 50)
        self.assertEqual(m["border_nesting"]["max_depth"], 3)
        self.assertTrue(m["border_nesting"]["notable"])
        glyphs = {i["glyph"]: i for i in m["repeated_markers"]["items"]}
        self.assertEqual(set(glyphs), {"●", "✓"})
        self.assertEqual((glyphs["●"]["rows_hit"], glyphs["●"]["rows"]), (8, 8))
        self.assertTrue(m["repeated_markers"]["notable"])
        self.assertEqual(m["duplicate_signals"]["by_encoding"], {"glyph+tag+word": 8})
        self.assertTrue(m["duplicate_signals"]["notable"])
        for k in ("chrome_share", "border_nesting", "repeated_markers", "duplicate_signals"):
            self.assertIn("notable", m["verdicts"][k])

    def test_markdown_output_and_ansi_input(self):
        r = run(SCRIPTS / "ansi_grid.py", CLUTTER, "--clutter")
        self.assertEqual(r.returncode, 0)
        self.assertIn("| chrome share |", r.stdout)
        self.assertIn("notable (> 1", r.stdout)
        # an .ansi frame gives the same numbers as the .mock it was rendered from
        mock = parse_mock(CLUTTER.read_text(encoding="utf-8"), str(CLUTTER))
        theme = load_theme("catppuccin-mocha")
        grid = parse_ansi(rm.render(mock, theme, "truecolor"))
        direct = ansi_grid.clutter_metrics(grid, theme, "x.ansi")
        self.assertEqual(direct["border_nesting"]["max_depth"], 3)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "f.ansi"
            p.write_text(rm.render(mock, theme, "truecolor"))
            self.assertEqual(metrics(p)["chrome_share"], direct["chrome_share"])

    def test_duplicate_signal_rules(self):
        th = load_theme("catppuccin-mocha")

        def dup(*rows):
            return ansi_grid.clutter_metrics(parse_ansi("\n".join(rows)), th)["duplicate_signals"]["by_encoding"]
        self.assertEqual(dup("✗ search   failed", "▲ billing  degraded warn", "● api      running"), {})   # glyph + word
        self.assertEqual(dup("[x] search  failed", "[OK] api"), {})                                       # tag + word
        self.assertEqual(dup("[OK] ✓ api"), {"glyph+tag": 1})
        self.assertEqual(dup("[!] ▲ api   warn"), {"glyph+tag+word": 1})
        self.assertEqual(dup("Source Source error"), {"repeated-word": 1})
        self.assertEqual(dup("4182 postgres postgres 38.2"), {})                                          # no status on the row

    def test_curated_references_are_not_notable(self):
        """Calibration guard: the curated good references stay below every threshold."""
        th = load_theme("catppuccin-mocha")
        files = sorted((SCRIPTS.parent / "assets" / "mockups").glob("*/*.mock")) + [DEMO]
        self.assertGreaterEqual(len(files), 29)
        notable = []
        for p in files:
            mock = parse_mock(p.read_text(encoding="utf-8"), str(p))
            m = ansi_grid.clutter_metrics(parse_ansi(rm.render(mock, th, "truecolor")), th, p.name)
            for k in ("border_nesting", "repeated_markers", "duplicate_signals"):
                if m[k]["notable"]:
                    notable.append((p.name, k))
            self.assertLessEqual(m["chrome_share"]["share_pct"], 60, p.name)
        self.assertEqual(notable, [])

    def test_ascii_rules_count_as_chrome_and_plain_text_is_clean(self):
        plain = ["Name      State", "alpha     ready", "beta      idle ", "gamma     ready"]
        g = parse_ansi("\n".join(plain))
        m = ansi_grid.clutter_metrics(g, load_theme("catppuccin-mocha"))
        self.assertEqual(m["chrome_share"]["chrome_cells"], 0)
        self.assertEqual(m["border_nesting"]["max_depth"], 0)
        ruled = parse_ansi("+--------+\n| name   |\n+--------+")
        r = ansi_grid.clutter_metrics(ruled, load_theme("catppuccin-mocha"))
        self.assertGreater(r["chrome_share"]["share_pct"], 60)


if __name__ == "__main__":
    unittest.main()
