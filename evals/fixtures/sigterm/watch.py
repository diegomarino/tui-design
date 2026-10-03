#!/usr/bin/env python3
"""queuewatch: live view of the work queues, redrawn every second. q quits.

Usually started under a supervisor, e.g.  timeout 8h python3 watch.py   or as a container's main process.
"""
import os
import select
import sys
import termios
import time

QUEUES = ["ingest", "resize", "transcode", "notify", "billing", "export"]


def depth(name, t):
    return (sum(map(ord, name)) * 7 + int(t)) % 40


def draw(now):
    out = ["\x1b[H\x1b[2J", "\x1b[1mQUEUEWATCH\x1b[0m  " + time.strftime("%H:%M:%S", time.localtime(now)), ""]
    for q in QUEUES:
        d = depth(q, now)
        out.append(f"{q:<10} {d:>3} " + "#" * (d // 2))
    out += ["", "q quit"]
    sys.stdout.write("\r\n".join(out))
    sys.stdout.flush()


def main():
    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)
    sys.stdout.write("\x1b[?1049h\x1b[?25l")      # alternate screen, hide cursor
    mode = termios.tcgetattr(fd)
    mode[3] &= ~(termios.ICANON | termios.ECHO)    # keys one by one, not echoed
    termios.tcsetattr(fd, termios.TCSANOW, mode)
    try:
        while True:
            draw(time.time())
            ready, _, _ = select.select([fd], [], [], 1.0)
            if ready and os.read(fd, 1) == b"q":
                return 0
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)
        sys.stdout.write("\x1b[?25h\x1b[?1049l")
        sys.stdout.flush()


if __name__ == "__main__":
    sys.exit(main())
