#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Generate the binary / derived fixtures of the behavior evals from their sources (ground truth).

  screenshot-audit/backupd--normal--80x24.mock   ground truth of the screenshot (written by this script)
  screenshot-audit/screenshot.png                rendered with the skill's render_mockup.py + ansi_render.py
  screenshot-audit/palette.json                  every color in the frame (SGR truecolor + theme fg/bg; the window
                                                 chrome reuses them): what pixel sampling can find
  build-textual/jobs--normal--80x24.mock         the screen the build case asks to implement

The .mock files are generated here so the ground truth and the PNG never drift apart. Run after changing a
design below or the skill's renderer; commit every output. `--check` regenerates in a temp dir and reports
whether the committed files are up to date (exit 1 when not), without touching them.

  python3 evals/fixtures/gen_fixtures.py            # stdlib; PNG through the skill's ansi_render.py
  python3 evals/fixtures/gen_fixtures.py --check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parents[1] / "skills" / "tui-design"
SCRIPTS = SKILL / "scripts"
SHOT_THEME = "tokyonight-night"
SHOT_TITLE = "backupd"


# ------------------------------------------------------------------ tiny .mock builder

def seg(spec: str | None, text: str) -> str:
    text = text.replace("{", "{{").replace("}", "}}")
    return text if not spec else "{" + spec + "}" + text + "{/}"


def row(cols: int, *parts: tuple[str | None, str], fill: str | None = None) -> str:
    """One body line: (spec, text) segments, padded to `cols` cells (all glyphs used here are 1 cell)."""
    width = sum(len(t) for _, t in parts)
    if width > cols:
        raise ValueError(f"row is {width} cells, > {cols}: {parts!r}")
    pad = cols - width
    out = "".join(seg(s, t) for s, t in parts)
    if pad:
        out += seg(fill, " " * pad)
    return out


def backupd_mock() -> str:
    """80x24 backup monitor with deliberate, countable flaws: an alarm-red title, a double frame (box inside a box),
    bracket chips, a constant REPO column, a 7-row dead band, F-key-only hints on two footer rows."""
    W = 80
    jobs = [
        ("OK", "home-photos", "nas-01:/photos", "03:00", "412 GB"),
        ("OK", "mail-archive", "mx-02:/var/mail", "03:15", "38 GB"),
        ("FAIL", "db-dump", "pg-01:/dumps", "03:30", "0 B"),
        ("OK", "wiki", "web-03:/srv/wiki", "03:45", "2.1 GB"),
        ("WARN", "laptops", "vpn:/home", "04:00", "96 GB"),
        ("OK", "git-mirror", "git-01:/repos", "04:10", "57 GB"),
        ("OK", "configs", "nas-01:/etc", "04:20", "12 MB"),
        ("WARN", "media-cache", "nas-01:/cache", "04:30", "1.3 TB"),
    ]
    chip = {"OK": "status.success", "FAIL": "status.error", "WARN": "status.warning"}
    selected = 2
    B, I = "border.default", "border.focus"
    lines = [
        "#! tui-mockup 1",
        "#! size: 80x24",
        "#! title: backupd — backup jobs monitor (screenshot audit ground truth)",
        "#! state: normal",
        f"#! theme: {SHOT_THEME}",
        "#! caps: attrs=bold,dim,inverse colors=truecolor glyphs=unicode source=assumed",
        "#! region r1 header 0,0,80,1",
        "#! region r2 table 2,2,76,11 Jobs (8)",
        "#! region r3 statusbar 0,21,80,1",
        "#! region r4 keybar 0,22,80,2",
        "#! focus r2",
        f"#! selected r2 {selected + 1}",
        "#! note: deliberate flaws for the screenshot-audit eval: alarm-red title, double frame, [OK]/[FAIL] chips,",
        "#! note: constant REPO column, 7 blank rows inside the frame, F-key hints over two footer rows",
    ]
    body = [row(W, ("status.error bold", "BACKUPD MONITOR v2.1"),
                ("fg.muted", "    host: nas-01   user: root   2026-10-02 09:14:07"))]
    body.append(row(W, (B, "╔" + "═" * 78 + "╗")))
    title = "─ Jobs (8) "
    body.append(row(W, (B, "║ "), (I, "┌" + title + "─" * (74 - len(title)) + "┐"), (B, " ║")))

    def cells(status, job, target, repo, last, size):
        return f" {status:<7}{job:<14}{target:<18}{repo:<10}{last:<10}{size:>8}".ljust(74)

    hdr = cells("STATUS", "JOB", "TARGET", "REPO", "LAST RUN", "SIZE")
    body.append(row(W, (B, "║ "), (I, "│"), ("table.header bold", hdr), (I, "│"), (B, " ║")))
    for i, (st, job, target, last, size) in enumerate(jobs):
        text = cells("", job, target, "s3-main", last, size)[8:]
        tag = f"[{st}]"
        if i == selected:
            parts = [(B, "║ "), (I, "│"), ("on:selection.bg", " "), (chip[st] + " bold on:selection.bg", f"{tag:<7}"),
                     ("selection.fg on:selection.bg", text), (I, "│"), (B, " ║")]
        else:
            parts = [(B, "║ "), (I, "│"), (None, " "), (chip[st] + " bold", f"{tag:<7}"),
                     ("fg.default", text), (I, "│"), (B, " ║")]
        body.append(row(W, *parts))
    body.append(row(W, (B, "║ "), (I, "└" + "─" * 74 + "┘"), (B, " ║")))
    for _ in range(7):
        body.append(row(W, (B, "║" + " " * 78 + "║")))
    body.append(row(W, (B, "╚" + "═" * 78 + "╝")))
    body.append(row(W, ("status.error", " Last error: db-dump: connection refused (exit 2)"),
                    ("fg.faint", "  · 5h41m ago")))
    keys1 = "[F1] Help  [F2] Run now  [F3] Logs  [F5] Refresh  [F8] Delete"
    keys2 = "[F9] Settings  [F10] Quit  [Tab] Next pane  [/] Filter"
    body.append(row(W, ("keyhint.desc", " " + keys1)))
    body.append(row(W, ("keyhint.desc", " " + keys2)))
    assert len(body) == 24, len(body)
    return "\n".join(lines + body) + "\n"


def jobs_build_mock() -> str:
    """80x24 list + detail screen for the build case: header, bordered list (focused), detail panel, keybar."""
    W = 80
    items = [("✓", "status.success", "nightly-etl", "ok"), ("✓", "status.success", "invoice-run", "ok"),
             ("✗", "status.error", "geo-import", "failed"), ("▲", "status.warning", "thumbs-gen", "slow"),
             ("✓", "status.success", "mail-digest", "ok"), ("✓", "status.success", "audit-export", "ok")]
    sel = 2
    LW = 28            # list box width (cols 0..27); detail box cols 28..79 (52 wide)
    DW = W - LW
    lines = [
        "#! tui-mockup 1",
        "#! size: 80x24",
        "#! title: Batch jobs — list + detail (build-case design)",
        "#! state: normal",
        "#! caps: attrs=bold,dim,inverse colors=truecolor glyphs=unicode source=assumed",
        "#! region r1 header 0,0,80,1",
        f"#! region r2 list 0,1,{LW},22 Jobs (6)",
        f"#! region r3 detail {LW},1,{DW},22 geo-import",
        "#! region r4 keybar 0,23,80,1",
        "#! focus r2",
        f"#! selected r2 {sel}",
    ]
    body = [row(W, ("accent.primary bold on:statusbar.bg", " batchctl "),
                ("statusbar.fg on:statusbar.bg", " prod · 6 jobs · 1 failed"), fill="on:statusbar.bg")]
    detail = [("fg.muted", "job      "), ("fg.default", "geo-import")], \
             [("fg.muted", "status   "), ("status.error bold", "✗ failed")], \
             [("fg.muted", "started  "), ("fg.default", "2026-10-02 03:10")], \
             [("fg.muted", "duration "), ("fg.default", "4m12s")], \
             [("fg.muted", "exit     "), ("fg.default", "1")], \
             [], \
             [("fg.muted", "last log")], \
             [("fg.faint", "03:14:20 "), ("fg.default", "fetch tiles: 412/980")], \
             [("fg.faint", "03:14:22 "), ("status.error", "error: quota exceeded")]
    dt = "─ geo-import "
    lt = "─ Jobs (6) "
    for y in range(22):
        if y == 0:
            left = [("border.focus", "╭"), ("fg.title bold", lt), ("border.focus", "─" * (LW - 2 - len(lt)) + "╮")]
            right = [("border.default", "╭"), ("fg.title bold", dt), ("border.default", "─" * (DW - 2 - len(dt)) + "╮")]
        elif y == 21:
            left = [("border.focus", "╰" + "─" * (LW - 2) + "╯")]
            right = [("border.default", "╰" + "─" * (DW - 2) + "╯")]
        else:
            i = y - 1
            if i < len(items):
                g, tok, name, word = items[i]
                inner = f" {g} {name:<15}{word:>7} "
                if i == sel:
                    mid = [("on:selection.bg", " "), (tok + " bold on:selection.bg", g),
                           ("selection.fg bold on:selection.bg", f" {name:<15}{word:>7} ")]
                else:
                    mid = [(None, " "), (tok, g), ("fg.default", f" {name:<15}"), ("fg.muted", f"{word:>7} ")]
                assert len(inner) == LW - 2, (len(inner), inner)
            else:
                mid = [(None, " " * (LW - 2))]
            left = [("border.focus", "│")] + mid + [("border.focus", "│")]
            d = detail[i] if i < len(detail) else []
            used = 1 + sum(len(t) for _, t in d)
            right = [("border.default", "│"), (None, " ")] + list(d) + [(None, " " * (DW - 2 - used)),
                                                                     ("border.default", "│")]
        body.append(row(W, *left, *right))
    body.append(row(W, ("keyhint.key bold", " j/k"), ("keyhint.desc", " move  "), ("keyhint.key bold", "enter"),
                    ("keyhint.desc", " open  "), ("keyhint.key bold", "r"), ("keyhint.desc", " rerun  "),
                    ("keyhint.key bold", "l"), ("keyhint.desc", " logs"),
                    (None, " " * 27), ("keyhint.key bold", "?"), ("keyhint.desc", " help  "),
                    ("keyhint.key bold", "q"), ("keyhint.desc", " quit ")))
    assert len(body) == 24, len(body)
    return "\n".join(lines + body) + "\n"


# ------------------------------------------------------------------ rendering and palette

SGR_RX = re.compile(r"\x1b\[([0-9;:]*)m")


def ansi_colors(ansi: str) -> set[str]:
    out = set()
    for m in SGR_RX.finditer(ansi):
        p = [x for x in re.split("[;:]", m.group(1)) if x != ""]
        i = 0
        while i < len(p):
            if p[i] in ("38", "48") and i + 4 < len(p) and p[i + 1] == "2":
                r, g, b = (int(x) for x in p[i + 2:i + 5])
                out.add(f"#{r:02x}{g:02x}{b:02x}")
                i += 5
            else:
                i += 1
    return out


def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(f"failed ({p.returncode}): {' '.join(cmd)}\n{p.stdout}\n{p.stderr}")
    return p.stdout + p.stderr


def build(out: Path) -> list[Path]:
    shot = out / "screenshot-audit"
    shot.mkdir(parents=True, exist_ok=True)
    mock = shot / "backupd--normal--80x24.mock"
    mock.write_text(backupd_mock())
    lint = run([sys.executable, str(SCRIPTS / "render_mockup.py"), str(mock), "--check"])
    if not re.search(r"\b0 error\(s\)", lint):
        raise SystemExit("screenshot mock does not lint clean:\n" + lint)
    with tempfile.TemporaryDirectory() as td:
        ansi = Path(td) / "frame.ansi"
        run([sys.executable, str(SCRIPTS / "render_mockup.py"), str(mock), "--theme", SHOT_THEME, "-o", str(ansi)])
        png = shot / "screenshot.png"
        run([sys.executable, str(SCRIPTS / "ansi_render.py"), str(ansi), "--theme", SHOT_THEME, "--title", SHOT_TITLE,
             "--format", "png", "-o", str(png)])
        theme = json.loads((SKILL / "references" / "themes" / f"{SHOT_THEME}.json").read_text())
        frame_cols = ansi_colors(ansi.read_text())
    term = {theme["terminal"]["background"].lower(), theme["terminal"]["foreground"].lower()}
    palette = {
        "source": f"{mock.name} rendered with theme {SHOT_THEME} (render_mockup.py + ansi_render.py); the window "
                  "chrome uses the theme background and border.default, both already in the frame",
        "theme": SHOT_THEME,
        "colors": sorted(frame_cols | term),
    }
    (shot / "palette.json").write_text(json.dumps(palette, indent=2) + "\n")

    bt = out / "build-textual"
    bt.mkdir(parents=True, exist_ok=True)
    jm = bt / "jobs--normal--80x24.mock"
    jm.write_text(jobs_build_mock())
    lint = run([sys.executable, str(SCRIPTS / "render_mockup.py"), str(jm), "--check"])
    if not re.search(r"\b0 error\(s\)", lint):
        raise SystemExit("build mock does not lint clean:\n" + lint)
    return [mock, png, shot / "palette.json", jm]


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="regenerate in a temp dir and compare with the committed files")
    ap.add_argument("--out", type=Path, default=HERE, help="output root (default: this directory)")
    a = ap.parse_args()
    if not a.check:
        for p in build(a.out):
            print(f"wrote {p.relative_to(a.out)}")
        return 0
    with tempfile.TemporaryDirectory() as td:
        stale = []
        for p in build(Path(td)):
            rel = p.relative_to(td)
            committed = HERE / rel
            if not committed.exists() or digest(committed) != digest(p):
                stale.append(str(rel))
        print("up to date" if not stale else "stale: " + ", ".join(stale))
        return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
