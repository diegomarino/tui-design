"""Craft lint (CR1–CR7) and the caps `source` key: each rule fires on its pattern and stays quiet on good frames."""

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "skills" / "tui-design" / "scripts"
SKILL = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from _mock import parse_mock  # noqa: E402


def mock(body: str, cols=60, rows=12, header="", path="x--normal--60x12.mock"):
    text = f"#! tui-mockup 1\n#! size: {cols}x{rows}\n{header}" + body
    return parse_mock(text, path)


def rules(m):
    return sorted({f.msg.split(":")[0].split()[-1] for f in m.findings if f.tag == "craft"})


TABLE = "NAME        RUNNER   STATE\n" + "".join(f"item-{i}      worker   {'idle' if i % 2 else 'done'}\n" for i in range(7))


class CraftRules(unittest.TestCase):
    def test_cr1_bracket_chip_but_not_controls(self):
        self.assertIn("CR1", rules(mock("[ Items ]   Groups\n")))
        self.assertEqual(rules(mock("[x] keep  [+] modified  [9/18]  [ok]\n")), [])

    def test_cr2_labels_and_slashes(self):
        self.assertIn("CR2", rules(mock("Group: alpha / Tab: build\n")))
        self.assertIn("CR2", rules(mock("Item / a1:b2 / worker / idle\n")))
        self.assertEqual(rules(mock("cwd   ~/Dev/project/app\n")), [])

    def test_cr3_constant_column(self):
        self.assertIn("CR3", rules(mock(TABLE)))

    def test_cr4_loud_placeholder_and_quiet_one(self):
        loud = "".join(f"(none)  a{i}\n" for i in range(3))
        quiet = "".join(f"{{fg.faint}}(none){{/}}  a{i}\n" for i in range(3))
        self.assertIn("CR4", rules(mock(loud)))
        self.assertNotIn("CR4", rules(mock(quiet)))

    def test_cr5_dead_gutter(self):
        rows = "".join(f"a{i}:b1{' ' * 30}idle\n" for i in range(6))
        self.assertIn("CR5", rules(mock("ID    STATE\n" + rows)))

    def test_cr6_dead_band_not_in_empty_state(self):
        body = "top\n" + "\n" * 6 + "bottom\n"
        self.assertIn("CR6", rules(mock(body)))
        self.assertNotIn("CR6", rules(mock(body, path="x--empty--60x12.mock")))

    def test_cr7_footer_rows(self):
        k = "{keyhint.key}q{/} quit  {keyhint.key}r{/} refresh\n"
        self.assertIn("CR7", rules(mock("body\n" + "\n" * 8 + k + k, rows=12)))
        self.assertNotIn("CR7", rules(mock("body\n" + "\n" * 9 + k, rows=12)))

    def test_waiver(self):
        self.assertEqual(rules(mock("[ Items ]\n", header="#! note: craft-ok CR1 matches the host's tab style\n")), [])

    def test_shipped_frames_are_clean(self):
        showcase = SKILL.parents[1] / "docs" / "showcase"      # the worked example, kept outside the skill
        files = list((SKILL / "assets" / "mockups").glob("*/*.mock")) + list(showcase.glob("*/*.mock"))
        self.assertTrue(files)
        for f in files:
            m = parse_mock(f.read_text(encoding="utf-8"), str(f))
            self.assertEqual(rules(m), [], f.name)


class CapsSource(unittest.TestCase):
    def warns(self, caps):
        m = mock("hi\n", header=f"#! caps: {caps}\n")
        return [f for f in m.findings if f.tag == "caps" and f.level == "WARN"], m

    def test_measured_sources_are_quiet(self):
        for src in ("test-card", "docs"):
            self.assertEqual(self.warns(f"colors=256 source={src}")[0], [])

    def test_code_assumed_and_missing_warn_with_the_test_card(self):
        for spec in ("colors=16 source=code", "colors=16 source=assumed", "colors=16"):
            w, _ = self.warns(spec)
            self.assertEqual(len(w), 1, spec)
            self.assertIn("test_card.py", w[0].hint)

    def test_bad_source_is_an_error(self):
        m = mock("hi\n", header="#! caps: source=vibes\n")
        self.assertTrue(any(f.level == "ERROR" and "source" in f.msg for f in m.findings))

    def test_no_caps_line_no_warning(self):
        self.assertEqual([f for f in mock("hi\n").findings if f.tag == "caps"], [])


if __name__ == "__main__":
    unittest.main()
