#!/usr/bin/env python3
"""Key probe: which keys actually reach an app running inside this terminal, multiplexer or host popup.

The OS, the terminal and the host (tmux, zellij, herdr…) take some keys before the app sees them: macOS turns F-keys
into media keys unless `fn` is held, ⌘ shortcuts belong to the terminal, a host prefix belongs to the host. Run this
inside the real target, press every key the design's footer shows, and send a screenshot. A target that never turns
✓ does not reach the app: pick another key (references/interaction.md#key-availability).

Usage:
  python3 SKILL_DIR/scripts/key_probe.py [KEY …]     e.g.  f2 ctrl+s w a enter esc alt+s shift+tab ctrl+right
  (default targets: f1 f2 f5 ctrl+s ctrl+r alt+s shift+tab ctrl+right home end)
Keys are names like `w`, `W`, `enter`, `esc`, `tab`, `shift+tab`, `space`, `backspace`, `up`…`right`, `home`, `end`,
`pgup`, `pgdn`, `f1`…`f12`, `ctrl+x`, `alt+x`, `ctrl+right`. Press ctrl+c twice to quit.
"""

from __future__ import annotations

import argparse
import curses
import sys

DEFAULT = ["f1", "f2", "f5", "ctrl+s", "ctrl+r", "alt+s", "shift+tab", "ctrl+right", "home", "end"]
SPECIAL = {9: "tab", 10: "enter", 13: "enter", 27: "esc", 32: "space", 127: "backspace", 8: "backspace", 0: "ctrl+space"}
CURSES_NAMES = {"KEY_UP": "up", "KEY_DOWN": "down", "KEY_LEFT": "left", "KEY_RIGHT": "right", "KEY_HOME": "home",
                "KEY_END": "end", "KEY_PPAGE": "pgup", "KEY_NPAGE": "pgdn", "KEY_BTAB": "shift+tab", "KEY_DC": "delete",
                "KEY_IC": "insert", "KEY_BACKSPACE": "backspace", "KEY_ENTER": "enter",
                "kLFT5": "ctrl+left", "kRIT5": "ctrl+right", "kUP5": "ctrl+up", "kDN5": "ctrl+down",
                "kLFT3": "alt+left", "kRIT3": "alt+right", "kUP3": "alt+up", "kDN3": "alt+down",
                "kLFT2": "shift+left", "kRIT2": "shift+right"}
CSI_MODS = {"5": "ctrl+", "3": "alt+", "2": "shift+", "6": "ctrl+shift+"}
CSI_DIRS = {"A": "up", "B": "down", "C": "right", "D": "left", "H": "home", "F": "end"}


def key_name(codes: list[int], keyname=None) -> str:
    """Name one key press from the curses codes read in one burst (an escape sequence arrives as several codes)."""
    keyname = keyname or (lambda c: curses.keyname(c).decode("ascii", "replace"))
    if not codes:
        return ""
    if len(codes) == 1:
        c = codes[0]
        if c in SPECIAL:
            return SPECIAL[c]
        if 1 <= c <= 26:
            return "ctrl+" + chr(c + 96)
        if 32 < c < 127:
            return chr(c)
        if c >= 256:
            name = keyname(c)
            if name.startswith("KEY_F(") and name.endswith(")"):
                return "f" + name[6:-1]
            return CURSES_NAMES.get(name, name)
        return f"code {c}"
    if codes[0] == 27 and len(codes) == 2:
        inner = key_name(codes[1:], keyname)
        return "alt+" + inner if inner else "esc"
    text = "".join(chr(c) if c < 256 else "?" for c in codes[1:])
    if codes[0] == 27 and text.startswith("[1;") and len(text) == 5 and text[3] in CSI_MODS and text[4] in CSI_DIRS:
        return CSI_MODS[text[3]] + CSI_DIRS[text[4]]
    return "esc " + text if codes[0] == 27 else " ".join(key_name([c], keyname) for c in codes)


def run(stdscr, targets: list[str]) -> None:
    curses.curs_set(0)
    curses.raw()
    stdscr.keypad(True)
    curses.use_default_colors()
    try:
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, -1)
        ok_attr = curses.color_pair(1) | curses.A_BOLD
    except curses.error:
        ok_attr = curses.A_BOLD
    seen: set[str] = set()
    log: list[str] = []
    ctrl_c = 0
    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        put = lambda y, x, t, a=0: stdscr.addnstr(y, x, t, max(0, w - x - 1), a) if y < h - 1 else None
        put(0, 0, "KEY PROBE · press each key your footer shows · ctrl+c twice quits", curses.A_BOLD)
        put(1, 0, "a target that never turns ✓ is taken by the OS, the terminal or the host", curses.A_DIM)
        x = 0
        for t in targets:
            done = t in seen
            label = f"{'✓' if done else '·'} {t}"
            put(3, x, label, ok_attr if done else curses.A_DIM)
            x += len(label) + 3
        put(5, 0, "arrived (newest first):", curses.A_BOLD)
        for i, line in enumerate(log[: max(0, h - 8)]):
            put(6 + i, 2, line)
        stdscr.refresh()
        c = stdscr.getch()
        burst = [c]
        stdscr.nodelay(True)
        while (n := stdscr.getch()) != -1:
            burst.append(n)
        stdscr.nodelay(False)
        if burst == [curses.KEY_RESIZE]:
            continue
        name = key_name(burst)
        if name == "ctrl+c":
            ctrl_c += 1
            if ctrl_c >= 2:
                return
        else:
            ctrl_c = 0
        seen.add(name)
        log.insert(0, f"{name:<14} codes {' '.join(map(str, burst))}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("keys", nargs="*", help="key names to check (default: a set that often gets taken)")
    a = ap.parse_args(argv)
    curses.wrapper(run, [k.lower() if len(k) > 1 else k for k in (a.keys or DEFAULT)])
    return 0


if __name__ == "__main__":
    sys.exit(main())
