#!/usr/bin/env python3
"""pkgls: list the packages of the local mirror, or pick one interactively.

usage:
  pkgls.py list            one package per line: NAME VERSION STATUS
  pkgls.py pick            arrow keys / j k to move, Enter prints the chosen name, Ctrl-C cancels
"""
import os
import sys
import termios
import tty

BASE = ["alpha-utils", "brotli", "cairo", "curl", "expat", "ffmpeg", "gettext", "glib", "gmp", "harfbuzz",
        "icu4c", "jpeg-turbo", "libpng", "libtiff", "lz4", "mpfr", "ncurses", "openssl", "pcre2", "readline",
        "sqlite", "tcl-tk", "webp", "xz", "zstd"]


def packages():
    """The mirror index: 2400 entries (name, version, status)."""
    out = []
    for i in range(2400):
        name = f"{BASE[i % len(BASE)]}-{i // len(BASE):03d}"
        version = f"{1 + i % 7}.{i % 13}.{i % 5}"
        status = "outdated" if i % 9 == 0 else "ok"
        out.append((name, version, status))
    return out


def paint(text, code):
    return f"\x1b[{code}m{text}\x1b[0m"


def cmd_list():
    for name, version, status in packages():
        line = paint(f"{name:<22}", "1") + f" {version:<9} " + paint(status, "33" if status == "outdated" else "32")
        print(line, flush=True)
    return 0


def cmd_pick():
    items = [p[0] for p in packages()[:200]]
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    sel, top, rows = 0, 0, 10
    try:
        tty.setraw(fd)
        while True:
            if sel < top:
                top = sel
            if sel >= top + rows:
                top = sel - rows + 1
            out = ["\x1b[2J\x1b[H", "pick a package (enter = choose, ctrl-c = cancel)\r\n"]
            for i in range(top, min(top + rows, len(items))):
                mark = "\x1b[7m> " if i == sel else "  "
                out.append(f"{mark}{items[i]}\x1b[0m\r\n")
            sys.stdout.write("".join(out))
            sys.stdout.flush()
            ch = os.read(fd, 3)
            if ch == b"\x03":            # Ctrl-C
                return 0
            if ch in (b"\r", b"\n"):
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
                sys.stdout.write("\x1b[2J\x1b[H")
                print(items[sel])
                return 0
            if ch in (b"j", b"\x1b[B"):
                sel = min(sel + 1, len(items) - 1)
            elif ch in (b"k", b"\x1b[A"):
                sel = max(sel - 1, 0)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def main(argv):
    if len(argv) != 2 or argv[1] not in ("list", "pick"):
        print(__doc__)
        return 1
    return cmd_list() if argv[1] == "list" else cmd_pick()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
