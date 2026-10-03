"""Tests for contrast_check.py, export_theme.py, preview_theme.py (stdlib unittest)."""

import ast
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "tui-design" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import contrast_check as cc  # noqa: E402
import export_theme as ex  # noqa: E402
import preview_theme as pv  # noqa: E402
from _theme import THEMES_DIR, contrast_ratio, blend, load_theme, load_token_defs  # noqa: E402

MOCHA = "catppuccin-mocha"
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def run(script, *args):
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True, text=True)


def variant(**mods):
    """Write a mocha variant to a temp file; mods: tokens={...}, ansi16={...}, terminal={...}."""
    data = json.loads((THEMES_DIR / f"{MOCHA}.json").read_text())
    data["id"] = "test-variant"
    for k, v in mods.items():
        data.setdefault(k, {}).update(v)
    d = tempfile.mkdtemp()
    p = Path(d) / "test-variant.json"
    p.write_text(json.dumps(data))
    return str(p)


class ContrastTests(unittest.TestCase):
    def test_mocha_passes(self):
        r = run("contrast_check.py", MOCHA)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("| catppuccin-mocha | fg.default |", r.stdout)

    def test_json_rows_and_ratio(self):
        r = run("contrast_check.py", MOCHA, "--format", "json")
        rows = json.loads(r.stdout)["results"]
        names = [x["check"] for x in rows]
        self.assertEqual(len([x for x in rows if not x["advisory"]]) + 1, 18)      # 17 required + fg.default (preferred)
        self.assertEqual(len(rows), 28)                                            # + 9 selection + 1 filled-tab + 1 FS-09 advisory
        self.assertEqual(names[:4], ["fg.default", "fg.default (preferred)", "fg.muted", "fg.faint"])
        self.assertIn("fg.on-accent on status.info", names)
        th = load_theme(MOCHA)
        row = next(x for x in rows if x["check"] == "fg.muted")
        self.assertAlmostEqual(row["ratio"], contrast_ratio(th.hex("fg.muted"), th.hex("bg.base")), places=2)
        self.assertEqual({"theme", "check", "fg", "bg", "ratio", "floor", "pass"} - set(row), set())

    def test_deterministic(self):
        a = run("contrast_check.py", MOCHA, "--format", "json").stdout
        self.assertEqual(a, run("contrast_check.py", MOCHA, "--format", "json").stdout)

    def test_failure_exit_1(self):
        p = variant(tokens={"fg.muted": "#2a2a3a"})
        r = run("contrast_check.py", p)
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL", r.stdout)

    def test_selected_row_and_tab_checks_are_advisory(self):
        names = {}
        for depth in ("truecolor", "16"):
            r = run("contrast_check.py", MOCHA, "--format", "json", "--depth", depth)
            rows = {x["check"]: x for x in json.loads(r.stdout)["results"]}
            for n in ("fg.default", "fg.muted", "fg.faint", "status.error", "status.warning", "status.success",
                      "status.info", "accent.primary"):
                self.assertTrue(rows[f"{n} on selection.bg"]["advisory"], (depth, n))
            self.assertEqual(rows["fg.faint on selection.bg"]["floor"], 3.0)
            self.assertEqual(rows["fg.muted on selection.bg"]["floor"], 4.5)
            self.assertEqual(rows["fg.default on selection.bg"]["bg"], "selection.bg")
            names[depth] = set(rows)
        self.assertIn("fg.on-accent on tab.active.bg", names["truecolor"])      # mocha fills the active tab
        self.assertNotIn("fg.on-accent on tab.active.bg", names["16"])          # ...but its 16-color spec is `default`

    def test_failing_advisory_never_fails_exit_code(self):
        p = variant(tokens={"selection.bg": "#2a2a3a", "tab.active.bg": "#2a2a3a"})   # dark fill: text on it fails
        r = run("contrast_check.py", p, "--format", "json")
        rows = {x["check"]: x for x in json.loads(r.stdout)["results"]}
        self.assertFalse(rows["fg.faint on selection.bg"]["pass"] and rows["fg.muted on selection.bg"]["pass"]
                         and rows["status.error on selection.bg"]["pass"] and rows["fg.on-accent on tab.active.bg"]["pass"])
        self.assertTrue(all(x["advisory"] for x in rows.values() if not x["pass"] and not x["required"]))
        self.assertEqual(r.returncode, 0 if all(x["pass"] for x in rows.values() if x["required"]) else 1)
        md = run("contrast_check.py", p).stdout
        self.assertIn("advisory", md)

    def test_preferred_is_advisory(self):
        p = variant(tokens={"fg.default": "#8a8aa0"})     # >= 4.5 but < 7
        r = run("contrast_check.py", p, "--format", "json")
        rows = {x["check"]: x for x in json.loads(r.stdout)["results"]}
        self.assertTrue(rows["fg.default"]["pass"])
        self.assertFalse(rows["fg.default (preferred)"]["pass"])
        self.assertEqual(r.returncode, 0)

    def test_depth16_resolution(self):
        th = load_theme(variant(ansi16={"fg.muted": "default dim", "selection.fg": "reverse", "fg.faint": "9"}))
        # dim: blend(fg, bg, .55)
        f, b = cc.resolve_pair(th, "fg.muted", "bg.base", "16")
        self.assertEqual((f, b), (blend(th.foreground, th.background, 0.55), th.background))
        # reverse on both: swapped default pair
        f, b = cc.resolve_pair(th, "selection.fg", "selection.bg", "16")
        self.assertEqual((f, b), (th.background, th.foreground))
        # palette index
        f, b = cc.resolve_pair(th, "fg.faint", "bg.base", "16")
        self.assertEqual(f, th.ansi[9])
        # truecolor ignores ansi16
        self.assertEqual(cc.resolve_pair(th, "fg.muted", "bg.base", "truecolor")[0], th.hex("fg.muted"))

    def test_all_and_missing(self):
        self.assertIn(run("contrast_check.py", "--all").returncode, (0, 1))
        self.assertEqual(run("contrast_check.py").returncode, 2)
        r = run("contrast_check.py", "no-such-theme")
        self.assertEqual(r.returncode, 1)
        self.assertIn("load", r.stdout)


class ExportTests(unittest.TestCase):
    def out(self, target):
        r = run("export_theme.py", MOCHA, "--target", target)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_json_shape(self):
        d = json.loads(self.out("json"))
        self.assertEqual(list(d), ["id", "name", "appearance", "terminal", "tokens", "ansi16"])
        self.assertEqual(list(d["terminal"]), ["background", "foreground", "cursor", "selection_background", "ansi"])
        self.assertEqual(len(d["terminal"]["ansi"]), 16)
        defs = load_token_defs()
        self.assertEqual(list(d["tokens"]), list(defs))
        self.assertEqual(list(d["ansi16"]), list(defs))
        self.assertTrue(all(re.fullmatch(r"#[0-9a-f]{6}", v) for v in d["tokens"].values()))
        th = load_theme(MOCHA)
        self.assertEqual(d["tokens"]["bg.base"], th.hex("bg.base"))
        # ansi16 = theme override if present, else the _tokens.json default (themes evolve; don't pin values)
        overrides = th.raw.get("ansi16", {})
        for tok in ("fg.muted", "selection.bg", "accent.primary"):
            self.assertEqual(d["ansi16"][tok], overrides.get(tok, defs[tok]["ansi16"]))

    def test_headers_name_theme_and_source(self):
        for t in (x for x in ex.TARGETS if x != "json"):
            o = self.out(t)
            self.assertIn("catppuccin-mocha", o.split("\n", 8)[0] + o.split("\n", 8)[1], t)
            self.assertIn("github.com/catppuccin", o, t)

    def test_textual(self):
        o = self.out("textual")
        ast.parse(o)
        for s in ('name="catppuccin-mocha"', 'primary="#89b4fa"', 'background="#1e1e2e"', "variables={",
                  '"footer-key-foreground"', '"block-cursor-background"', "dark=True"):
            self.assertIn(s, o)

    def test_css_custom_properties(self):
        o = self.out("css")
        self.assertIn("--bg-base: #1e1e2e;", o)
        self.assertIn("--text-selection-bg:", o)
        self.assertIn("--ansi-15:", o)
        self.assertEqual(o.count("{"), o.count("}"))

    def test_gum_env(self):
        o = self.out("gum")
        self.assertIn('export GUM_CHOOSE_CURSOR_FOREGROUND="#89b4fa"', o)
        self.assertIn("GUM_CONFIRM_SELECTED_BACKGROUND", o)
        if shutil.which("bash"):
            r = subprocess.run(["bash", "-n"], input=o, text=True, capture_output=True)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_all_tokens_exported(self):
        defs = load_token_defs()
        ink, go, rs = self.out("ink"), self.out("lipgloss"), self.out("ratatui")
        for t in defs:
            self.assertIn(f"'{t}':", ink)
            self.assertIn(ex.pascal(t) + " ", go)
            self.assertIn(f"pub const {ex.snake(t).upper()}: Color", rs)
        self.assertIn("extendTheme(defaultTheme", ink)
        self.assertIn('"charm.land/lipgloss/v2"', go)
        self.assertIn("pub const THEME: Theme", rs)

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_ink_syntax(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "theme.mjs"
            p.write_text(self.out("ink"))
            r = subprocess.run(["node", "--check", str(p)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)

    @unittest.skipUnless(shutil.which("gofmt"), "gofmt not installed")
    def test_go_is_gofmt_clean(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "theme.go"
            p.write_text(self.out("lipgloss"))
            r = subprocess.run(["gofmt", "-l", str(p)], capture_output=True, text=True)
            self.assertEqual((r.returncode, r.stdout.strip(), r.stderr), (0, "", ""))

    @unittest.skipUnless(shutil.which("rustfmt"), "rustfmt not installed")
    def test_rust_parses(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "theme.rs"
            p.write_text(self.out("ratatui"))
            r = subprocess.run(["rustfmt", "--edition", "2021", "--check", str(p)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_errors(self):
        self.assertEqual(run("export_theme.py", "no-such", "--target", "css").returncode, 2)
        self.assertEqual(run("export_theme.py", MOCHA, "--target", "nope").returncode, 2)


class PreviewTests(unittest.TestCase):
    def test_every_token_listed(self):
        o = run("preview_theme.py", MOCHA, "--depth", "none").stdout
        self.assertNotIn("\x1b", o)
        for t in load_token_defs():
            self.assertIn(t, o)
        self.assertIn("neutral ladder", o)
        self.assertIn("sample UI", o)

    def test_depths(self):
        tc = run("preview_theme.py", MOCHA).stdout
        self.assertIn("38;2;137;180;250", tc)
        self.assertRegex(run("preview_theme.py", MOCHA, "--depth", "256").stdout, r"38;5;\d+")
        d16 = run("preview_theme.py", MOCHA, "--depth", "16").stdout
        self.assertNotIn("38;2;", d16)
        self.assertNotIn("38;5;", d16)

    def test_lines_fit_width(self):
        for ln in ANSI.sub("", run("preview_theme.py", MOCHA).stdout).split("\n"):
            self.assertLessEqual(len(ln), pv.WIDTH)

    def test_missing_theme(self):
        self.assertEqual(run("preview_theme.py", "no-such").returncode, 2)


if __name__ == "__main__":
    unittest.main()
