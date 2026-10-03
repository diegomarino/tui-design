"""play_mock.py: color mapping and a real curses draw inside a private tmux server."""

import os
import shutil
import subprocess
import sys
import time
import unittest
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "skills" / "tui-design" / "scripts"
SKILL = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import play_mock  # noqa: E402

DEMO = SKILL / "assets" / "demo" / "fleet--normal--80x24.mock"


class ColorNumber(unittest.TestCase):
    def test_palette_and_default(self):
        self.assertEqual(play_mock.color_number(None, "256"), -1)
        self.assertEqual(play_mock.color_number("p:5", "16"), 5)
        self.assertEqual(play_mock.color_number("p:203", "256"), 203)

    def test_truecolor_maps_to_256_only_at_256(self):
        n = play_mock.color_number("#ff0000", "256")
        self.assertTrue(16 <= n <= 255)
        self.assertEqual(play_mock.color_number("#ff0000", "16"), -1)

    def test_grid_has_frame_size(self):
        from _mock import parse_mock
        from _theme import load_theme
        mock = parse_mock(DEMO.read_text(encoding="utf-8"), str(DEMO))
        grid = play_mock.grid_for(mock, load_theme("catppuccin-mocha"), "256")
        self.assertEqual(len(grid.cells), mock.rows)


@unittest.skipUnless(shutil.which("tmux"), "tmux not installed")
class LiveDraw(unittest.TestCase):
    """Run the player in a private tmux server (-L, never the default one) and read the screen back."""

    def run_in_tmux(self, args, cols=110, rows=30):
        sock = f"play-mock-test-{uuid.uuid4().hex[:8]}"
        tm = ["tmux", "-L", sock]
        env = "TERM=xterm-256color"
        cmd = f"{env} {sys.executable} {SCRIPTS / 'play_mock.py'} {args}"
        subprocess.run(tm + ["new-session", "-d", "-x", str(cols), "-y", str(rows), cmd], check=True)
        try:
            screen = ""
            for _ in range(20):
                time.sleep(0.25)
                screen = subprocess.run(tm + ["capture-pane", "-p", "-e"], capture_output=True, text=True).stdout
                if screen.strip():
                    break
            subprocess.run(tm + ["send-keys", "q"], capture_output=True)
            return screen
        finally:
            subprocess.run(tm + ["kill-server"], capture_output=True)

    def test_probe_card(self):
        screen = self.run_in_tmux("--probe")            # delegates to test_card.py --curses
        self.assertIn("TEST CARD · curses", screen)
        self.assertIn("n/a in curses", screen)
        self.assertIn("\x1b[", screen)                  # colors / attributes reached the terminal

    def test_draws_demo_frame(self):
        screen = self.run_in_tmux(str(DEMO))
        self.assertIn("depth 256", screen)              # info line names the depth it drew at
        self.assertIn("Services (6)", screen)           # frame text reached the screen
        self.assertIn("\x1b[48;5;", screen)             # 256-color background fills, not just fg


if __name__ == "__main__":
    unittest.main()
