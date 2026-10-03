"""Docs links: no broken relative link or anchor, and nothing in the skill links outside it (tools/check_links.py)."""
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_links  # noqa: E402


class DocsLinkTests(unittest.TestCase):
    def test_no_broken_links(self):
        files = check_links.markdown_files()
        self.assertTrue(any(f.name == "SKILL.md" for f in files))
        problems = [p for f in files for p in check_links.check(f)]
        self.assertEqual(problems, [])

    def test_slug_rules(self):
        self.assertEqual(check_links.slug("3. Pick X when…"), "3-pick-x-when")
        self.assertEqual(check_links.slug("Token → theme-system keys"), "token--theme-system-keys")
        self.assertEqual(check_links.slug("States × sizes in one call"), "states--sizes-in-one-call")
        self.assertEqual(check_links.slug("Live capture (the app runs)"), "live-capture-the-app-runs")

    def test_detects_a_link_leaving_the_skill(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve()                # /var -> /private/var on macOS
            skill = root / "skills" / "tui-design"
            (skill / "references").mkdir(parents=True)
            (root / "README.md").write_text("# Top\n", encoding="utf-8")
            (skill / "references" / "tools.md").write_text("# Tools\n\n## Gallery\n", encoding="utf-8")
            probe = skill / "references" / "probe.md"
            probe.write_text("[out](../../../README.md) [in](tools.md#gallery) [bad](tools.md#nope) `[code](x.md)`\n",
                             encoding="utf-8")
            with mock.patch.object(check_links, "ROOT", root), mock.patch.object(check_links, "SKILL", skill):
                problems = check_links.check(probe)
        self.assertEqual(len(problems), 2, problems)
        self.assertIn("leaves skills/tui-design/", problems[0])
        self.assertIn("#nope", problems[1])


if __name__ == "__main__":
    unittest.main()
