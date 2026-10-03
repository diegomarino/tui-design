"""test_card.py: the raw card's escapes, its 80x24 budget, and that the skill's own ANSI parser reads it."""

import re
import subprocess
import sys
import unicodedata
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "skills" / "tui-design" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import test_card  # noqa: E402
from _ansi import parse_ansi  # noqa: E402


def visible_width(line: str) -> int:
    t = re.sub(r"\x1b\]8;;[^\x1b]*\x1b\\", "", line)
    t = re.sub(r"\x1b\[[0-9;:?]*[A-Za-z]", "", t)
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in t)


class RawCard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = subprocess.run([sys.executable, str(SCRIPTS / "test_card.py")],
                                 capture_output=True, text=True, check=True).stdout

    def test_fits_80x24(self):
        lines = self.out.rstrip("\n").split("\n")
        self.assertLessEqual(len(lines), 24)
        for i, line in enumerate(lines):
            self.assertLessEqual(visible_width(line), 80, f"row {i}")

    def test_emits_what_frameworks_can(self):
        for needle in ("\x1b[0;9m", "48;2;", "4:3", "58;2;", "53m", "\x1b]8;;https://example.com"):
            self.assertIn(needle, self.out)

    def test_glyph_rows_match_reference_length(self):
        plain = re.sub(r"\x1b\[[0-9;:]*m", "", self.out)
        rows = {l.split()[0]: l for l in plain.splitlines() if l.split()}
        self.assertEqual(rows["ref"].count("|"), len(test_card.CORE) + 1)
        self.assertEqual(rows["core"].count("|"), len(test_card.CORE) + 1)

    def test_parses_with_skill_parser(self):
        grid = parse_ansi(self.out, 80, 24)
        attrs = {a for row in grid.cells for c in row if c.w for a in c.style.attrs}
        self.assertTrue({"bold", "italic", "strike"} <= attrs, attrs)

    def test_curses_card_drops_raw_only_features(self):
        rows = test_card.card("curses", "info", 256)
        text = "".join(t for row in rows for t, _ in row)
        self.assertIn("n/a in curses", text)
        self.assertFalse(any(st["link"] or isinstance(st["bg"], str) for row in rows for _, st in row))

    def test_low_color_curses_card(self):
        text = "".join(t for row in test_card.card("curses", "info", 8) for t, _ in row)
        self.assertIn("design at 16", text)


if __name__ == "__main__":
    unittest.main()
