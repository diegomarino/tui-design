#!/usr/bin/env python3
"""WCAG contrast floors (contract section 3) for one, many or all themes.

Examples:
  python3 contrast_check.py catppuccin-mocha
  python3 contrast_check.py --all --format json
  python3 contrast_check.py --all --depth 16        # resolve ansi16 specs against terminal.ansi
  python3 contrast_check.py path/to/theme.json

Floors (ratio vs bg.base unless noted): fg.default >= 4.5 required (7 preferred, advisory);
fg.muted >= 4.5; fg.faint >= 3; status.{error,warning,success,info}, accent.primary, keyhint.key,
link >= 4.5; border.focus >= 3; selection.fg on selection.bg >= 4.5; fg.on-accent on accent.primary
and on each status.* >= 4.5.
Advisory (reported as `advisory`, never change the exit code; JSON rows carry "advisory": true):
fg.default (7 preferred); text on the selected row, i.e. fg.default, fg.muted, status.*, accent.primary
on selection.bg >= 4.5 and fg.faint on selection.bg >= 3; fg.on-accent on tab.active.bg >= 4.5 when the
theme fills the active tab (tab.active.bg differs from bg.base; at --depth 16 only when its ansi16 spec is
not `default`); FS-09: contrast of border.focus at least 1.5x that of border.default (one focus indicator).
--depth 16: a token becomes terminal.ansi[N] / terminal fg|bg (default); `dim` = blend(fg, bg, 0.55);
`reverse` (or the inverse attribute) swaps the pair. Bold-as-bright is not modelled.
Exit 0 = every required floor passes; 1 = a required floor fails; 2 = usage error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _theme import Theme, blend, contrast_ratio, list_themes, load_theme  # noqa: E402

STATUS = ["status.error", "status.warning", "status.success", "status.info"]
# (check name, fg token, bg token, floor, required)
CHECKS: list[tuple[str, str, str, float, bool]] = (
    [("fg.default", "fg.default", "bg.base", 4.5, True),
     ("fg.default (preferred)", "fg.default", "bg.base", 7.0, False),
     ("fg.muted", "fg.muted", "bg.base", 4.5, True),
     ("fg.faint", "fg.faint", "bg.base", 3.0, True)]
    + [(t, t, "bg.base", 4.5, True) for t in STATUS]
    + [("accent.primary", "accent.primary", "bg.base", 4.5, True),
       ("keyhint.key", "keyhint.key", "bg.base", 4.5, True),
       ("link", "link", "bg.base", 4.5, True),
       ("border.focus", "border.focus", "bg.base", 3.0, True),
       ("selection.fg on selection.bg", "selection.fg", "selection.bg", 4.5, True),
       ("fg.on-accent on accent.primary", "fg.on-accent", "accent.primary", 4.5, True)]
    + [(f"fg.on-accent on {t}", "fg.on-accent", t, 4.5, True) for t in STATUS]
    + [("fg.default on selection.bg", "fg.default", "selection.bg", 4.5, False),
       ("fg.muted on selection.bg", "fg.muted", "selection.bg", 4.5, False),
       ("fg.faint on selection.bg", "fg.faint", "selection.bg", 3.0, False)]
    + [(f"{t} on selection.bg", t, "selection.bg", 4.5, False) for t in STATUS]
    + [("accent.primary on selection.bg", "accent.primary", "selection.bg", 4.5, False)]
)
TAB_CHECK = ("fg.on-accent on tab.active.bg", "fg.on-accent", "tab.active.bg", 4.5, False)


def tab_is_filled(theme: Theme, depth: str) -> bool:
    """True when the active tab is painted on a fill of its own (not the base background)."""
    if depth == "16":
        return theme.ansi16["tab.active.bg"][0] != "default"
    return theme.hex("tab.active.bg") != theme.hex("bg.base")


def resolve_pair(theme: Theme, fg_tok: str, bg_tok: str, depth: str) -> tuple[str, str]:
    """Effective (fg hex, bg hex) of a cell drawn with fg_tok on bg_tok."""
    if depth != "16":
        return theme.hex(fg_tok), theme.hex(bg_tok)
    fcol, fattrs = theme.ansi16[fg_tok]
    bcol, _ = theme.ansi16[bg_tok]

    def hexof(col, default):
        return default if col in ("default", "reverse", "bg") else theme.ansi[col]

    if fcol == "bg":  # text in terminal bg on the fill (drawn as fill-slot + reverse)
        fill = theme.ansi[bcol] if isinstance(bcol, int) else theme.foreground
        fg = theme.background
        return (blend(fg, fill, 0.55) if "dim" in fattrs else fg), fill
    fg, bg = hexof(fcol, theme.foreground), hexof(bcol, theme.background)
    if fcol == "reverse" or bcol == "reverse" or "inverse" in fattrs:
        fg, bg = bg, fg
    if "dim" in fattrs:
        fg = blend(fg, bg, 0.55)
    return fg, bg


def run_theme(arg: str, depth: str) -> list[dict]:
    try:
        th = load_theme(arg)
    except (FileNotFoundError, ValueError, KeyError, OSError) as e:
        return [{"theme": Path(arg).stem, "check": "load", "fg": "", "bg": "", "fg_hex": "", "bg_hex": "",
                 "ratio": 0.0, "floor": 0.0, "pass": False, "required": True, "advisory": False, "error": str(e)}]
    rows = []
    checks = CHECKS + ([TAB_CHECK] if tab_is_filled(th, depth) else [])
    for name, ft, bt, floor, required in checks:
        fh, bh = resolve_pair(th, ft, bt, depth)
        ratio = contrast_ratio(fh, bh)
        rows.append({"theme": th.id, "check": name, "fg": ft, "bg": bt, "fg_hex": fh, "bg_hex": bh,
                     "ratio": round(ratio, 2), "floor": floor, "pass": ratio >= floor, "required": required,
                     "advisory": not required})
    # FS-09 (advisory): the focused border must stand out from inactive borders —
    # ratio = contrast(border.focus) / contrast(border.default), both against bg.base.
    ff, fb = resolve_pair(th, "border.focus", "bg.base", depth)
    df, db = resolve_pair(th, "border.default", "bg.base", depth)
    rel = contrast_ratio(ff, fb) / contrast_ratio(df, db)
    rows.append({"theme": th.id, "check": "border.focus vs border.default (FS-09, x)", "fg": "border.focus",
                 "bg": "border.default", "fg_hex": ff, "bg_hex": df, "ratio": round(rel, 2), "floor": 1.5,
                 "pass": rel >= 1.5, "required": False, "advisory": True})
    return rows


def to_markdown(rows: list[dict], depth: str) -> str:
    out = [f"Contrast floors, depth={depth} (WCAG 2.x ratio)", "",
           "| theme | check | fg | bg | ratio | floor | pass |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        if r["check"] == "load":
            out.append(f"| {r['theme']} | load | | | | | FAIL: {r['error']} |")
            continue
        verdict = "ok" if r["pass"] else ("FAIL" if r["required"] else "advisory")
        out.append(f"| {r['theme']} | {r['check']} | {r['fg']} {r['fg_hex']} | {r['bg']} {r['bg_hex']} "
                   f"| {r['ratio']:.2f} | {r['floor']:g} | {verdict} |")
    themes = sorted({r["theme"] for r in rows})
    out += ["", "Summary:"]
    for t in themes:
        tr = [r for r in rows if r["theme"] == t]
        fails = [r["check"] for r in tr if not r["pass"] and r["required"]]
        warns = [r["check"] for r in tr if not r["pass"] and not r["required"]]
        line = f"- {t}: {sum(r['pass'] for r in tr)}/{len(tr)} pass"
        if fails:
            line += "; FAIL: " + ", ".join(fails)
        if warns:
            line += "; advisory below floor: " + ", ".join(warns)
        out.append(line)
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check contract section 3 contrast floors for themes.", epilog=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("themes", nargs="*", help="theme ids or paths to theme .json")
    ap.add_argument("--all", action="store_true", help="every theme in references/themes/")
    ap.add_argument("--depth", choices=["truecolor", "16"], default="truecolor")
    ap.add_argument("--format", choices=["md", "json"], default="md")
    ap.add_argument("-o", "--out", help="write here instead of stdout")
    a = ap.parse_args(argv)
    names = list_themes() if a.all else a.themes
    if not names:
        ap.error("give one or more theme ids, or --all")
    rows: list[dict] = []
    for n in sorted(dict.fromkeys(names)):
        rows += run_theme(n, a.depth)
    text = (json.dumps({"depth": a.depth, "results": rows}, indent=2) + "\n") if a.format == "json" \
        else to_markdown(rows, a.depth)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 1 if any(not r["pass"] and r["required"] for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
