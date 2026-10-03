"""Parser/renderer edge cases for _ansi.py, ansi_render.py, ansi_grid.py (stdlib unittest).

Run:  python3 -m unittest discover -s scripts/tests -v     (from the skill root)
"""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "tui-design" / "scripts"))
import ansi_grid  # noqa: E402
import ansi_render  # noqa: E402
from _ansi import Resolver, char_width, parse_ansi  # noqa: E402
from _theme import load_theme  # noqa: E402

E = "\x1b"
THEME = load_theme("catppuccin-mocha")


def cells(text, **kw):
    return parse_ansi(text, **kw).cells[0]


class ParserTests(unittest.TestCase):
    def test_16_colours(self):
        c = cells(f"{E}[31;44mx{E}[91;104my")
        self.assertEqual((c[0].style.fg, c[0].style.bg), ("p:1", "p:4"))
        self.assertEqual((c[1].style.fg, c[1].style.bg), ("p:9", "p:12"))

    def test_256_and_truecolor_semicolon(self):
        c = cells(f"{E}[38;5;208;48;2;1;2;3mx")
        self.assertEqual((c[0].style.fg, c[0].style.bg), ("p:208", "#010203"))

    def test_colon_params(self):
        c = cells(f"{E}[38:2::10:20:30mx{E}[48:2:1:2:3my{E}[38:5:99mz")
        self.assertEqual(c[0].style.fg, "#0a141e")
        self.assertEqual(c[1].style.bg, "#010203")
        self.assertEqual(c[2].style.fg, "p:99")

    def test_underline_styles(self):
        a = cells(f"{E}[4:3mc{E}[4:2md{E}[4:0me{E}[4mf{E}[21mg{E}[24mh")
        self.assertEqual([sorted(x.style.attrs) for x in a],
                         [["curly_underline"], ["double_underline"], [], ["underline"], ["double_underline"], []])

    def test_tmux_overline_quirk(self):
        a = cells(f"{E}[5:3ma{E}[55mb{E}[53mc")
        self.assertEqual([sorted(x.style.attrs) for x in a], [["overline"], [], ["overline"]])

    def test_attributes_and_resets(self):
        a = cells(f"{E}[1;2;3;7;9mx{E}[22my{E}[23;27;29mz{E}[0mw")
        self.assertEqual(sorted(a[0].style.attrs), ["bold", "dim", "italic", "reverse", "strike"])
        self.assertEqual(sorted(a[1].style.attrs), ["italic", "reverse", "strike"])
        self.assertEqual(a[2].style.attrs, frozenset())

    def test_underline_colour(self):
        a = cells(f"{E}[4;58;2;255;200;0mx{E}[59my")
        self.assertEqual(a[0].style.ul, "#ffc800")
        self.assertIsNone(a[1].style.ul)

    def test_state_carries_across_lines(self):
        g = parse_ansi(f"{E}[32mab\ncd")
        self.assertEqual(g.cells[1][0].style.fg, "p:2")

    def test_wide_chars(self):
        g = parse_ansi("a日b")
        row = g.cells[0]
        self.assertEqual([(c.ch, c.w) for c in row], [("a", 1), ("日", 2), ("", 0), ("b", 1)])
        self.assertEqual(g.text_rows(), ["a日b"])
        self.assertEqual(g.cols, 4)

    def test_zero_width_combines(self):
        row = cells("éx❤️")
        self.assertEqual([c.ch for c in row], ["é", "x", "❤️"])
        self.assertEqual(char_width("‍"), 0)
        self.assertEqual(char_width("\U0001F680"), 2)

    def test_osc8_link(self):
        row = cells(f"{E}]8;;https://x.test{E}\\hi{E}]8;;{E}\\!")
        self.assertEqual([c.style.link for c in row], ["https://x.test", "https://x.test", None])
        row = cells(f"{E}]8;id=1;https://y.test\x07a{E}]8;;\x07")
        self.assertEqual(row[0].style.link, "https://y.test")

    def test_other_escapes_skipped_not_emulated(self):
        row = cells(f"a{E}[2Kb{E}[10;5Hc{E}[?25l{E}]0;title\x07d")
        self.assertEqual("".join(c.ch for c in row), "abcd")

    def test_pad_and_crop(self):
        g = parse_ansi("abc\nd", cols=2, rows=3)
        self.assertEqual((g.cols, g.rows), (2, 3))
        self.assertEqual(g.text_rows(), ["ab", "d ", "  "])
        g = parse_ansi("a日", cols=2)                       # wide char cropped in half -> blank
        self.assertEqual(g.text_rows(), ["a "])

    def test_tab(self):
        self.assertEqual(parse_ansi("a\tb").text_rows(), ["a       b"])


class ResolverTests(unittest.TestCase):
    def test_resolution(self):
        r = Resolver(THEME)
        g = parse_ansi(f"{E}[7mx{E}[7;31my{E}[8mz")
        fg, bg = r.painted(g.cells[0][0].style)          # reverse on defaults
        self.assertEqual((fg, bg), (THEME.background, THEME.foreground))
        fg, bg = r.painted(g.cells[0][1].style)          # reverse + fg red -> bg red, fg = theme bg
        self.assertEqual((fg, bg), (THEME.background, THEME.ansi[1]))
        self.assertEqual(r.hex("p:196"), "#ff0000")
        self.assertEqual(r.slot("p:3", "term.fg"), "ansi.yellow")
        self.assertEqual(r.slot("p:208", "term.fg"), "p:208")
        self.assertIsNone(r.slot("#123456", "term.fg"))


class RenderTests(unittest.TestCase):
    def render(self, text, **kw):
        return ansi_render.render_svg(parse_ansi(text), THEME, **kw)

    def test_per_glyph_x_and_runs(self):
        svg, geo = self.render("ab 日 cd")
        self.assertIn('x="14 22.4"', svg)                  # first run: a b (cols 0,1)
        self.assertIn('text-anchor="middle"', svg)         # wide char centred
        self.assertEqual(geo["cols"], 8)
        self.assertEqual(geo["origin_px"], [14, 42])

    def test_dim_inverse_and_lines(self):
        svg, _ = self.render(f"{E}[2mdim{E}[0m {E}[7minv{E}[0m {E}[9ms{E}[53mo{E}[4:3mc{E}[21md")
        self.assertIn('fill-opacity="0.55"', svg)
        self.assertIn(f'fill="{THEME.foreground}"/>', svg)    # inverse bg rect uses theme fg
        self.assertIn("<polyline", svg)                       # curly
        self.assertGreaterEqual(svg.count("<line"), 2)        # strike + overline
        self.assertIn("xml:space=\"preserve\"", svg)

    def test_no_chrome_and_escape(self):
        svg, geo = self.render("<&>", chrome=False)
        self.assertIn("&lt;&amp;&gt;", svg)
        self.assertNotIn("<circle", svg)
        self.assertEqual(geo["origin_px"][1], 8)


class GridTests(unittest.TestCase):
    def test_grid_json(self):
        colors = ansi_grid.Colors(THEME)
        d = ansi_grid.build_grid_json(parse_ansi(f"{E}[31m日{E}[0mx"), colors)
        self.assertEqual((d["cols"], d["rows"]), (3, 1))
        c = d["cells"][0]
        self.assertEqual(c[1], {"ch": "", "w": 0})
        self.assertEqual(c[0]["fg"]["slot"], "ansi.red")
        self.assertEqual(c[0]["fg"]["raw"], THEME.ansi[1])
        self.assertIn("status.error", c[0]["fg"]["tokens"])
        self.assertEqual(c[2]["bg"]["slot"], "term.bg")
        json.dumps(d)

    def test_box_and_hints(self):
        text = ("╭─ Title ──╮\n│ hi       │\n╰──────────╯\n"
                "┌┐╔═╗\n└┘╚═╝\n"
                " q quit   ? help\n")
        colors = ansi_grid.Colors(THEME)
        desc = ansi_grid.Describer(parse_ansi(text, cols=20), THEME, colors, None).run()
        roles = [(r["role"], r["bbox"]["x"], r["bbox"]["y"], r["bbox"]["w"], r["bbox"]["h"]) for r in desc["regions"]]
        self.assertIn(("panel", 0, 0, 12, 3), roles)
        self.assertIn(("panel", 0, 3, 2, 2), roles)
        self.assertIn(("panel", 2, 3, 3, 2), roles)
        box = next(r for r in desc["regions"] if r["bbox"]["w"] == 12)
        self.assertEqual(box["title"]["text"], "Title")
        self.assertEqual(box["border"]["style"], "rounded")
        self.assertEqual([e["key_hints"][0]["key"] for e in desc["elements"]], ["q", "?"])
        self.assertEqual(desc["regions"][-1]["role"], "keybar")
        self.assertEqual(desc["meta"]["source_path"], "capture")


class RsvgHintTests(unittest.TestCase):
    def test_error_names_rsvg_convert_and_the_package_for_this_os(self):
        hint = ansi_render.rsvg_install_hint
        self.assertEqual(f"rsvg-convert not found: {hint('darwin')}",
                         "rsvg-convert not found: brew install librsvg")
        self.assertEqual(hint("linux", "ID=ubuntu\nID_LIKE=debian\n"), "apt install librsvg2-bin")
        self.assertEqual(hint("linux", "ID=fedora\n"), "dnf install librsvg2-tools")
        self.assertEqual(hint("linux", 'ID="arch"\nID_LIKE=archlinux\n'), "pacman -S librsvg")
        self.assertEqual(hint("linux", "ID=alpine\n"), "apk add rsvg-convert")
        unknown = hint("linux", "ID=slackware\n")
        self.assertIn("brew install librsvg", unknown)
        self.assertIn("apt install librsvg2-bin", unknown)
        self.assertIn("apk add rsvg-convert", unknown)


if __name__ == "__main__":
    unittest.main()


class RenderGeometryTests(unittest.TestCase):
    """Browser-safe SVG: no text run spans spaces; full blocks become one merged rectangle."""

    def test_spaces_split_runs_and_blocks_are_rects(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "tui-design" / "scripts"))
        from _ansi import parse_ansi
        from _theme import load_theme
        from ansi_render import render_svg
        svg, _ = render_svg(parse_ansi("ab      cd ████\n", 20, 1), load_theme("catppuccin-mocha"), chrome=False)
        texts = re.findall(r">([^<]*)</text>", svg)
        self.assertIn("ab", texts)
        self.assertIn("cd", texts)
        self.assertFalse(any(" " in t for t in texts))
        self.assertNotIn("█", svg)
        self.assertEqual(len(re.findall(r'<rect x="[^"]+" y="[^"]+" width="[^"]+" height="[^"]+" fill="#cdd6f4"', svg)), 1)
