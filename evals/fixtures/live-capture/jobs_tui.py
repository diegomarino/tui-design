#!/usr/bin/env python3
"""cronview: scheduled jobs on this host. Run: python3 jobs_tui.py   (j/k move, r refresh, q quit)"""
import curses
import json
from pathlib import Path

COLUMNS = [("NAME", 26), ("SCHEDULE", 16), ("LAST RUN", 20), ("NEXT RUN", 16), ("DURATION", 12), ("STATUS", 10)]
OPTIONAL = ("DURATION", "LAST RUN")   # dropped, in this order, when the terminal is too narrow


def plan_columns(width):
    """Fit the columns to the terminal width (drop optional ones until the table fits)."""
    cols = list(COLUMNS)
    for name in OPTIONAL:
        if sum(w for _, w in cols) <= width:
            break
        cols = [c for c in cols if c[0] != name]
    return cols
STATE_PAIR = {"ok": 1, "failed": 2, "late": 3, "running": 4}


def load():
    return json.loads((Path(__file__).parent / "jobs.json").read_text())["jobs"]


def put(win, y, x, text, attr=0):
    try:
        win.addstr(y, x, text, attr)
    except curses.error:
        pass  # off-screen: ignore


def draw(stdscr, jobs, sel, cols):
    stdscr.erase()
    h, w = stdscr.getmaxyx()
    put(stdscr, 0, 0, "CRONVIEW", curses.color_pair(5) | curses.A_BOLD)
    put(stdscr, 0, 12, f"host build-07   {len(jobs)} jobs   tz UTC")
    x = 0
    for title, width in cols:
        put(stdscr, 2, x, title.ljust(width), curses.A_UNDERLINE)
        x += width
    y = 4
    for i, j in enumerate(jobs):
        if y >= h - 3:
            break
        attr = curses.A_BOLD if i == sel else 0
        x = 0
        field = {"NAME": j["name"], "SCHEDULE": j["schedule"], "LAST RUN": j["last_run"],
                 "NEXT RUN": j["next_run"], "DURATION": j["duration"], "STATUS": None}
        for title, width in cols:
            v = field[title]
            if v is None:
                put(stdscr, y, x, "●", curses.color_pair(STATE_PAIR.get(j["state"], 0)) | attr)
            else:
                put(stdscr, y, x, str(v)[:width - 1].ljust(width), attr)
            x += width
        y += 2
    put(stdscr, h - 2, 0, "j/k: move up/down   enter: open job details   r: refresh now   l: show logs")
    put(stdscr, h - 1, 0, "e: edit schedule   d: disable job   x: delete job   /: filter   q: quit")
    stdscr.refresh()


def main(stdscr):
    curses.start_color()
    curses.use_default_colors()
    for n, c in ((1, curses.COLOR_GREEN), (2, curses.COLOR_RED), (3, curses.COLOR_YELLOW),
                 (4, curses.COLOR_BLUE), (5, curses.COLOR_CYAN)):
        curses.init_pair(n, c, -1)
    curses.curs_set(0)
    jobs, sel = load(), 0
    cols = plan_columns(stdscr.getmaxyx()[1])
    while True:
        draw(stdscr, jobs, sel, cols)
        k = stdscr.getch()
        if k in (ord("q"), 27):
            return
        if k in (ord("j"), curses.KEY_DOWN):
            sel = min(sel + 1, len(jobs) - 1)
        elif k in (ord("k"), curses.KEY_UP):
            sel = max(sel - 1, 0)
        elif k == ord("r"):
            jobs = load()


if __name__ == "__main__":
    curses.wrapper(main)
