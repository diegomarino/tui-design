#!/usr/bin/env python3
"""Inventory of the framework versions the references pin, and (with --online)
how far behind the registries' latest releases they are.  Stdlib only.

    python3 scripts/check_versions.py                  # offline: inventory only
    python3 scripts/check_versions.py --online         # + latest per registry
    python3 scripts/check_versions.py --online --fail-on major

The pinned version is read from each framework file's version line/table in
`references/frameworks/*.md` (the regex per entry is in INVENTORY below, so a
reworded table shows up as `unparsed`, not as a silent pass).

Status, from comparing pinned and latest:
    current        same version (a partial pin such as 0.29 matches 0.29.x)
    patch behind   only the last component differs
    minor behind   the minor differs (major >= 1)
    major behind   the major differs; for 0.y versions the *minor* is the
                   breaking component (semver 0.x), so 0.30 -> 0.31 is major
    ahead          the pin is newer than the registry (a pre-release, or the
                   registry read failed upstream)
    unparsed       the pin could not be read from the reference file
    unknown        the registry lookup failed (offline mode prints "-")

Exit status is 0 unless `--fail-on major` is given and an entry is major
behind (the report never edits anything).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REFS = os.path.normpath(os.path.join(HERE, "..", "references", "frameworks"))

# (display name, reference file, regex with ONE group = pinned version,
#  registry kind, registry id)
# registry kinds: npm, pypi, crates, github (owner/repo releases/latest),
#                 goproxy (Go module path, charm.land vanity paths included).
INVENTORY = [
    ("Ink", "ink.md", r"^\| `ink` \| \*\*(\d[\w.\-]*)\*\*", "npm", "ink"),
    ("@inkjs/ui", "ink.md", r"^\| `@inkjs/ui` \| (\d[\w.\-]*)", "npm", "@inkjs/ui"),
    ("ink-testing-library", "ink.md", r"^\| `ink-testing-library` \| (\d[\w.\-]*)", "npm", "ink-testing-library"),
    ("Textual", "textual.md", r"^\| `textual` \| \*\*(\d[\w.\-]*)\*\*", "pypi", "textual"),
    ("textual-dev", "textual.md", r"^\| `textual-dev` \| (\d[\w.\-]*)", "pypi", "textual-dev"),
    ("Rich", "textual.md", r"^\| `rich` \| (\d[\w.\-]*)", "pypi", "rich"),
    ("Bubble Tea", "bubbletea.md", r"^\| Bubble Tea \|[^|]*\|\s*v(\d[\w.\-]*)", "goproxy", "charm.land/bubbletea/v2"),
    ("Bubbles", "bubbletea.md", r"^\| Bubbles \|[^|]*\|\s*v(\d[\w.\-]*)", "goproxy", "charm.land/bubbles/v2"),
    ("Lip Gloss", "bubbletea.md", r"^\| Lip Gloss \|[^|]*\|\s*v(\d[\w.\-]*)", "goproxy", "charm.land/lipgloss/v2"),
    ("Huh", "bubbletea.md", r"^\| Huh \|[^|]*\|\s*v(\d[\w.\-]*)", "goproxy", "charm.land/huh/v2"),
    ("Ratatui", "ratatui.md", r"^\| `ratatui` \| \*\*(\d[\w.\-]*)\*\*", "crates", "ratatui"),
    ("crossterm", "ratatui.md", r"default backend \(crossterm (\d[\w.\-]*)", "crates", "crossterm"),
    ("gum", "gum.md", r"^- \*\*gum (\d[\w.\-]*)\*\*", "github", "charmbracelet/gum"),
]

# ---------------------------------------------------------------- parsing

def parse_version(text):
    """'v2.0.10' / '0.30.2 (2026-06-19)' / '1.0.0-rc.1' -> (2, 0, 10); None if no digits."""
    m = re.match(r"\s*v?(\d+(?:\.\d+)*)", text or "")
    if not m:
        return None
    return tuple(int(p) for p in m.group(1).split("."))


def is_prerelease(text):
    return bool(re.match(r"\s*v?\d+(?:\.\d+)*[-+]", text or ""))


def read_pinned(refs_dir, filename, pattern):
    """First match of `pattern` (one capture group) in the file, else None."""
    path = os.path.join(refs_dir, filename)
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return None
    m = re.search(pattern, text, re.M)
    return m.group(1) if m else None


def inventory(refs_dir, entries=INVENTORY):
    """[{name, file, pinned, registry, registry_id}] with pinned None when unreadable."""
    out = []
    for name, fname, pattern, kind, rid in entries:
        out.append({"name": name, "file": fname, "pinned": read_pinned(refs_dir, fname, pattern),
                    "registry": kind, "registry_id": rid})
    return out


# ------------------------------------------------------------- comparison

def compare(pinned, latest):
    """Status string for a pinned vs latest version string (see module doc)."""
    p, l = parse_version(pinned), parse_version(latest)
    if p is None:
        return "unparsed"
    if l is None:
        return "unknown"
    n = len(p)                       # a partial pin (0.29) only compares what it states
    if p == (l + (0,) * n)[:n]:
        return "current"
    pp = (p + (0, 0, 0))[:3]
    ll = (l + (0, 0, 0))[:3]
    if pp > ll:
        return "ahead"
    if pp[0] != ll[0]:
        return "major behind"
    if pp[0] == 0:                   # 0.y: the minor is the breaking component
        return "major behind" if pp[1] != ll[1] else "patch behind"
    return "minor behind" if pp[1] != ll[1] else "patch behind"


# -------------------------------------------------------------- registries

USER_AGENT = "tui-design-check-versions/1 (stdlib urllib)"


def http_get_json(url, timeout=10, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json",
                                               **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:   # noqa: S310 (fixed https registry URLs)
        return json.loads(resp.read().decode("utf-8"))


def registry_url(kind, rid):
    q = urllib.parse.quote
    if kind == "npm":
        return "https://registry.npmjs.org/%s/latest" % q(rid, safe="@")
    if kind == "pypi":
        return "https://pypi.org/pypi/%s/json" % q(rid)
    if kind == "crates":
        return "https://crates.io/api/v1/crates/%s" % q(rid)
    if kind == "github":
        return "https://api.github.com/repos/%s/releases/latest" % rid
    if kind == "goproxy":
        return "https://proxy.golang.org/%s/@latest" % rid.lower()
    raise ValueError("unknown registry kind: %r" % kind)


def extract_latest(kind, doc):
    """Pull the version string out of a registry's JSON response."""
    if kind == "npm":
        return doc["version"]
    if kind == "pypi":
        return doc["info"]["version"]
    if kind == "crates":
        c = doc["crate"]
        return c.get("max_stable_version") or c["max_version"]
    if kind == "github":
        return doc["tag_name"]
    if kind == "goproxy":
        return doc["Version"]
    raise ValueError("unknown registry kind: %r" % kind)


def fetch_latest(kind, rid, timeout=10, getter=http_get_json):
    """Latest version string, or None when the lookup fails (never raises)."""
    headers = {}
    token = os.environ.get("GITHUB_TOKEN")
    if kind == "github" and token:
        headers["Authorization"] = "Bearer " + token
    try:
        doc = getter(registry_url(kind, rid), timeout=timeout, headers=headers)
        return extract_latest(kind, doc)
    except Exception:            # network, HTTP, JSON or shape errors: report "unknown", do not crash
        return None


# ------------------------------------------------------------------ report

def build_rows(refs_dir, online=False, timeout=10, fetcher=fetch_latest, entries=INVENTORY):
    rows = []
    for e in inventory(refs_dir, entries):
        latest = fetcher(e["registry"], e["registry_id"], timeout) if online else None
        if e["pinned"] is None:
            status = "unparsed"
        elif not online:
            status = "-"
        elif latest is None:
            status = "unknown"
        else:
            status = compare(e["pinned"], latest)
            if status == "ahead" and is_prerelease(latest):
                status = "current"
        rows.append({**e, "latest": latest, "status": status})
    return rows


def format_table(rows, online):
    if online:
        headers = ["package", "pinned", "latest", "status", "file"]
        body = [[r["name"], r["pinned"] or "?", r["latest"] or "-", r["status"], r["file"]] for r in rows]
    else:                            # offline: latest/status are meaningless, show the inventory only
        headers = ["package", "pinned", "registry", "file"]
        body = [[r["name"], r["pinned"] or "?", "%s:%s" % (r["registry"], r["registry_id"]), r["file"]]
                for r in rows]
    widths = [max(len(h), *(len(b[i]) for b in body)) for i, h in enumerate(headers)]

    def line(cells):
        return "  ".join(c.ljust(w) for c, w in zip(cells, widths)).rstrip()

    return "\n".join([line(headers), line(["-" * w for w in widths])] + [line(b) for b in body])


def exit_code(rows, fail_on):
    if fail_on == "major" and any(r["status"] == "major behind" for r in rows):
        return 1
    return 0


def main(argv=None, fetcher=fetch_latest):
    ap = argparse.ArgumentParser(description="Inventory the pinned framework versions; --online compares with the registries.")
    ap.add_argument("--online", action="store_true", help="query npm, PyPI, crates.io, the Go proxy and GitHub releases")
    ap.add_argument("--fail-on", choices=["major"], help="exit 1 when an entry is major behind (default: always exit 0)")
    ap.add_argument("--refs", default=DEFAULT_REFS, help="directory with the framework reference files (default: %(default)s)")
    ap.add_argument("--timeout", type=float, default=10.0, help="seconds per registry request (default 10)")
    ap.add_argument("--json", action="store_true", help="print JSON instead of the table")
    a = ap.parse_args(argv)
    rows = build_rows(a.refs, a.online, a.timeout, fetcher)
    if a.json:
        print(json.dumps(rows, indent=2))
    else:
        print(format_table(rows, a.online))
        unparsed = [r["name"] for r in rows if r["status"] == "unparsed"]
        unknown = [r["name"] for r in rows if r["status"] == "unknown"]
        if unparsed:
            print("\nunparsed (version line reworded? fix the regex in INVENTORY): " + ", ".join(unparsed), file=sys.stderr)
        if unknown:
            print("\nlookup failed (offline, rate-limited or renamed): " + ", ".join(unknown), file=sys.stderr)
        if not a.online:
            print("\noffline: inventory only; add --online for the latest releases", file=sys.stderr)
    return exit_code(rows, a.fail_on)


if __name__ == "__main__":
    sys.exit(main())
