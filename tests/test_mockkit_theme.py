"""Regression: mockkit's .ansi/.png/gallery output takes a theme id OR a path to a theme .json.

Bug: matrix(..., png=True, theme="my.json") rendered the .ansi with the custom theme but then passed
`Theme.id` to ansi_render.py, which looks ids up in references/themes/ only ("theme 'my-brand' not found").
render_mockup.py --theme and _theme.load_theme accept both forms; mockkit now does too.
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "tui-design" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _theme import THEMES_DIR, load_theme  # noqa: E402
from mockkit import CanvasError, matrix, theme_arg  # noqa: E402


def build(c, state):
    c.text(1, 1, "hello", "accent.primary bold")


def write_custom_theme(directory: Path, theme_id: str = "my-brand-unbundled") -> Path:
    data = json.loads((THEMES_DIR / "catppuccin-mocha.json").read_text())
    data["id"], data["name"] = theme_id, "My Brand"
    p = directory / "brand.json"
    p.write_text(json.dumps(data))
    return p


class ThemeArgTests(unittest.TestCase):
    def test_bundled_id_passes_through(self):
        self.assertEqual(theme_arg("dracula-classic"), "dracula-classic")

    def test_path_becomes_absolute(self):
        with tempfile.TemporaryDirectory() as d:
            p = write_custom_theme(Path(d))
            self.assertEqual(theme_arg(str(p)), str(p.resolve()))

    def test_unknown_theme_names_the_bundled_ones(self):
        with self.assertRaises(FileNotFoundError) as cm:
            theme_arg("no-such-theme")
        self.assertIn("catppuccin-mocha", str(cm.exception))


class MatrixCustomThemeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.theme = write_custom_theme(self.dir)
        # the custom id must not be a bundled one, or the bug would not show
        self.assertNotIn(load_theme(str(self.theme)).id, [p.stem for p in THEMES_DIR.glob("*.json")])

    def tearDown(self):
        self._tmp.cleanup()

    def test_render_with_theme_path(self):
        paths = matrix(build, "hello", self.dir / "out", sizes=((40, 8),), theme=str(self.theme), render=True)
        self.assertTrue(paths[0].with_suffix(".ansi").exists())

    @unittest.skipUnless(shutil.which("rsvg-convert"), "PNG needs rsvg-convert")
    def test_png_with_theme_path(self):
        """The reported bug: png=True with a custom theme path."""
        paths = matrix(build, "hello", self.dir / "out", sizes=((40, 8),), theme=str(self.theme), png=True)
        self.assertGreater(paths[0].with_suffix(".png").stat().st_size, 0)

    @unittest.skipUnless(shutil.which("rsvg-convert"), "PNG needs rsvg-convert")
    def test_png_with_bundled_id_still_works(self):
        paths = matrix(build, "hello", self.dir / "out", sizes=((40, 8),), theme="nord-dark", png=True)
        self.assertGreater(paths[0].with_suffix(".png").stat().st_size, 0)

    def test_gallery_with_theme_path(self):
        gal = self.dir / "gallery.html"
        matrix(build, "hello", self.dir / "out", sizes=((40, 8),), theme=str(self.theme), gallery=gal)
        self.assertGreater(gal.stat().st_size, 0)

    def test_missing_theme_path_is_a_clear_error(self):
        with self.assertRaises((CanvasError, FileNotFoundError)):
            matrix(build, "hello", self.dir / "out", sizes=((40, 8),), theme=str(self.dir / "gone.json"), render=True)


if __name__ == "__main__":
    unittest.main()
