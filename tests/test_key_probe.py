"""key_probe.py: key naming from curses code bursts, and a live run in a private tmux server."""

import shutil
import subprocess
import sys
import time
import unittest
import uuid
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "tui-design" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import key_probe  # noqa: E402

NAMES = {266: "KEY_F(2)", 353: "KEY_BTAB", 562: "kRIT5", 259: "KEY_UP"}
name = lambda codes: key_probe.key_name(codes, lambda c: NAMES.get(c, f"k{c}"))


class Naming(unittest.TestCase):
    def test_plain_and_control(self):
        self.assertEqual(name([119]), "w")
        self.assertEqual(name([19]), "ctrl+s")
        self.assertEqual(name([9]), "tab")
        self.assertEqual(name([10]), "enter")
        self.assertEqual(name([27]), "esc")

    def test_curses_keys(self):
        self.assertEqual(name([266]), "f2")
        self.assertEqual(name([353]), "shift+tab")
        self.assertEqual(name([562]), "ctrl+right")
        self.assertEqual(name([259]), "up")

    def test_escape_sequences(self):
        self.assertEqual(name([27, 115]), "alt+s")
        self.assertEqual(name([27] + [ord(c) for c in "[1;5C"]), "ctrl+right")
        self.assertTrue(name([27] + [ord(c) for c in "[99~"]).startswith("esc "))


@unittest.skipUnless(shutil.which("tmux"), "tmux not installed")
class Live(unittest.TestCase):
    def test_keys_arrive(self):
        sock = f"key-probe-test-{uuid.uuid4().hex[:8]}"
        tm = ["tmux", "-L", sock]
        cmd = f"TERM=xterm-256color {sys.executable} {SCRIPTS / 'key_probe.py'} f2 ctrl+s w alt+s"
        subprocess.run(tm + ["new-session", "-d", "-x", "100", "-y", "20", cmd], check=True)
        try:
            time.sleep(1.2)
            for k in ("w", "C-s", "F2", "M-s"):
                subprocess.run(tm + ["send-keys", k])
                time.sleep(0.25)
            time.sleep(0.4)
            screen = subprocess.run(tm + ["capture-pane", "-p"], capture_output=True, text=True).stdout
            for k in ("f2", "ctrl+s", "w", "alt+s"):
                self.assertIn(f"✓ {k}", screen)
        finally:
            subprocess.run(tm + ["kill-server"], capture_output=True)


if __name__ == "__main__":
    unittest.main()
