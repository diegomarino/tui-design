"""The Sections list of every reference carries exact, current line ranges (tools/gen_toc.py).

An edit to a reference that moves a section without re-running `python3 tools/gen_toc.py` fails here.
"""

import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import gen_toc  # noqa: E402


class SectionsLists(unittest.TestCase):
    def test_every_list_is_current(self):
        found = [msg for p in gen_toc.managed() for msg in gen_toc.problems(p)]
        self.assertEqual(found, [], "run python3 tools/gen_toc.py, then write any placeholder text")

    def test_every_reference_with_sections_has_a_list(self):
        managed = set(gen_toc.managed())
        missing = []
        for p in sorted(gen_toc.REFS.rglob("*.md")):
            if p.relative_to(gen_toc.REFS).parts[0] in gen_toc.EXCLUDED or p in managed:
                continue
            if len(gen_toc.sections(p.read_text(encoding="utf-8").split("\n"))) >= 2:
                missing.append(str(p.relative_to(gen_toc.ROOT)))
        self.assertEqual(missing, [], "add a list with python3 tools/gen_toc.py --init FILE")

    def test_ranges_start_on_their_heading_and_cover_the_section(self):
        for p in gen_toc.managed():
            lines = p.read_text(encoding="utf-8").split("\n")
            start, stop = gen_toc.find_block(lines)
            entries = [gen_toc.ENTRY.match(e) for e in lines[start + 1:stop]]
            secs = gen_toc.sections(lines)
            self.assertEqual(len(entries), len(secs), p.name)
            for m, line, (text, anchor, a, b) in zip(entries, lines[start + 1:stop], secs):
                with self.subTest(file=p.name, section=text):
                    self.assertIsNotNone(m)
                    self.assertIn(f"· L{a}–{b} — ", line)
                    self.assertEqual(lines[a - 1], f"## {text}")
                    self.assertTrue(lines[b - 1].strip())

    def test_generation_is_idempotent_and_converges(self):
        text = "\n".join(["# T", "", gen_toc.HEADER, "- [A](#a) — read A.", "", "## A", "", "a", "",
                          "## B", "b", ""])
        once = gen_toc.generate(text)
        self.assertEqual(gen_toc.generate(once), once)
        lines = once.split("\n")
        self.assertIn("- [A](#a) · L7–9 — read A.", lines)
        self.assertIn(f"- [B](#b) · L11–12 — {gen_toc.PLACEHOLDER}", lines)
        self.assertEqual(lines[6], "## A")
        self.assertEqual(lines[10], "## B")

    def test_renamed_heading_keeps_its_text(self):
        text = "\n".join(["# T", "", gen_toc.HEADER, "- [Old](#old) · L6–6 — read it.", "", "## New", "x"])
        self.assertIn("- [New](#new) · L6–7 — read it.", gen_toc.generate(text).split("\n"))


if __name__ == "__main__":
    unittest.main()
