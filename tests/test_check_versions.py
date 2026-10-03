"""Tests for check_versions.py: parsing and comparison on fixtures, no network (stdlib unittest)."""

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "tui-design" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import check_versions as cv  # noqa: E402

FIXTURES = {
    "ink.md": "| `ink` | **7.1.1** (2026-07-16) | MIT |\n| `@inkjs/ui` | 2.0.0 (2024-05-22, dormant) | peer |\n"
              "| `ink-testing-library` | 4.0.0 (x) | works |\n",
    "textual.md": "| `textual` | **8.2.8** (2026-06-30) | MIT |\n| `rich` | 15.0.0 | backend |\n"
                  "| `textual-dev` | 1.8.0 | CLI |\n",
    "bubbletea.md": "| Bubble Tea | `tea \"charm.land/bubbletea/v2\"` | v2.0.10 (2026-09-24) | MIT |\n"
                    "| Bubbles | `charm.land/bubbles/v2/<pkg>` | v2.2.1 | x |\n"
                    "| Lip Gloss | `charm.land/lipgloss/v2` (+ `/table`) | v2.0.6 | x |\n"
                    "| Huh | `charm.land/huh/v2` | v2.0.3 | forms |\n",
    "ratatui.md": "| `ratatui` | **0.30.2** (2026-06-19) | umbrella |\n"
                  "| `ratatui-crossterm` | 0.1.2 | default backend (crossterm 0.29; feature x) |\n",
    "gum.md": "- **gum 2.0.2** (2026-09-24); 2.0.0 was the port.\nverified with **gum 2.0.1** (installed)\n",
}


def make_refs(overrides=None):
    d = tempfile.TemporaryDirectory()
    files = {**FIXTURES, **(overrides or {})}
    for name, text in files.items():
        (Path(d.name) / name).write_text(text, encoding="utf-8")
    return d


class ParseTests(unittest.TestCase):
    def test_parse_version(self):
        self.assertEqual(cv.parse_version("v2.0.10"), (2, 0, 10))
        self.assertEqual(cv.parse_version("0.30.2 (2026-06-19)"), (0, 30, 2))
        self.assertEqual(cv.parse_version("0.29"), (0, 29))
        self.assertEqual(cv.parse_version("1.0.0-rc.1"), (1, 0, 0))
        self.assertIsNone(cv.parse_version("latest"))
        self.assertIsNone(cv.parse_version(None))

    def test_is_prerelease(self):
        self.assertTrue(cv.is_prerelease("v2.0.0-beta.1"))
        self.assertFalse(cv.is_prerelease("v2.0.0"))

    def test_inventory_reads_every_entry(self):
        with make_refs() as d:
            inv = {e["name"]: e["pinned"] for e in cv.inventory(d)}
        self.assertEqual(len(inv), 13)
        self.assertEqual(inv["Ink"], "7.1.1")
        self.assertEqual(inv["@inkjs/ui"], "2.0.0")
        self.assertEqual(inv["Bubble Tea"], "2.0.10")
        self.assertEqual(inv["Lip Gloss"], "2.0.6")
        self.assertEqual(inv["Ratatui"], "0.30.2")
        self.assertEqual(inv["crossterm"], "0.29")
        self.assertEqual(inv["gum"], "2.0.2")      # the "latest" line, not the "verified with" one
        self.assertTrue(all(v for v in inv.values()))

    def test_reworded_line_is_unparsed_not_silent(self):
        with make_refs({"ink.md": "no table here\n"}) as d:
            inv = {e["name"]: e["pinned"] for e in cv.inventory(d)}
        self.assertIsNone(inv["Ink"])
        self.assertEqual(inv["Textual"], "8.2.8")

    def test_missing_file_is_unparsed(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(all(e["pinned"] is None for e in cv.inventory(d)))

    def test_real_references_parse(self):
        """The shipped reference files still match every regex (a reworded table would break the audit)."""
        missing = [e["name"] for e in cv.inventory(cv.DEFAULT_REFS) if e["pinned"] is None]
        self.assertEqual(missing, [])


class CompareTests(unittest.TestCase):
    def test_statuses(self):
        cases = [
            ("7.1.1", "7.1.1", "current"),
            ("2.0.10", "v2.0.10", "current"),
            ("2.0.1", "v2.0.2", "patch behind"),
            ("2.1.0", "2.3.5", "minor behind"),
            ("7.1.1", "8.0.0", "major behind"),
            ("0.30.2", "0.30.5", "patch behind"),
            ("0.30.2", "0.31.0", "major behind"),      # 0.y: the minor breaks
            ("0.29", "0.29.4", "current"),              # partial pin matches its line
            ("0.29", "0.30.0", "major behind"),
            ("3.0.0", "2.9.9", "ahead"),
            ("1.0.0", "1.0.0", "current"),
        ]
        for pinned, latest, want in cases:
            with self.subTest(pinned=pinned, latest=latest):
                self.assertEqual(cv.compare(pinned, latest), want)

    def test_unparsed_and_unknown(self):
        self.assertEqual(cv.compare(None, "1.0.0"), "unparsed")
        self.assertEqual(cv.compare("1.0.0", None), "unknown")
        self.assertEqual(cv.compare("1.0.0", "garbage"), "unknown")


class RegistryTests(unittest.TestCase):
    def test_urls(self):
        self.assertEqual(cv.registry_url("npm", "@inkjs/ui"), "https://registry.npmjs.org/@inkjs%2Fui/latest")
        self.assertEqual(cv.registry_url("pypi", "textual"), "https://pypi.org/pypi/textual/json")
        self.assertEqual(cv.registry_url("crates", "ratatui"), "https://crates.io/api/v1/crates/ratatui")
        self.assertEqual(cv.registry_url("github", "charmbracelet/gum"),
                         "https://api.github.com/repos/charmbracelet/gum/releases/latest")
        self.assertEqual(cv.registry_url("goproxy", "charm.land/bubbletea/v2"),
                         "https://proxy.golang.org/charm.land/bubbletea/v2/@latest")
        with self.assertRaises(ValueError):
            cv.registry_url("rubygems", "x")

    def test_extract_latest_from_fixture_payloads(self):
        self.assertEqual(cv.extract_latest("npm", {"name": "ink", "version": "7.1.1"}), "7.1.1")
        self.assertEqual(cv.extract_latest("pypi", {"info": {"version": "8.2.8"}}), "8.2.8")
        self.assertEqual(cv.extract_latest("crates", {"crate": {"max_version": "0.31.0-rc.1",
                                                                "max_stable_version": "0.30.2"}}), "0.30.2")
        self.assertEqual(cv.extract_latest("crates", {"crate": {"max_version": "0.29.0"}}), "0.29.0")
        self.assertEqual(cv.extract_latest("github", {"tag_name": "v2.0.2"}), "v2.0.2")
        self.assertEqual(cv.extract_latest("goproxy", {"Version": "v2.0.10", "Time": "x"}), "v2.0.10")

    def test_fetch_latest_swallows_errors(self):
        def boom(url, timeout=10, headers=None):
            raise OSError("offline")
        self.assertIsNone(cv.fetch_latest("npm", "ink", getter=boom))

        def bad_shape(url, timeout=10, headers=None):
            return {"unexpected": True}
        self.assertIsNone(cv.fetch_latest("pypi", "textual", getter=bad_shape))

    def test_fetch_latest_uses_the_injected_getter(self):
        seen = []

        def fake(url, timeout=10, headers=None):
            seen.append(url)
            return {"info": {"version": "9.9.9"}}
        self.assertEqual(cv.fetch_latest("pypi", "rich", getter=fake), "9.9.9")
        self.assertEqual(seen, ["https://pypi.org/pypi/rich/json"])


def fake_fetcher(table):
    def f(kind, rid, timeout=10):
        return table.get(rid)
    return f


class ReportTests(unittest.TestCase):
    LATEST = {"ink": "8.0.0", "@inkjs/ui": "2.0.0", "ink-testing-library": "4.0.0", "textual": "8.2.9",
              "textual-dev": "1.8.0", "rich": "15.0.0", "charm.land/bubbletea/v2": "v2.0.10",
              "charm.land/bubbles/v2": "v2.2.1", "charm.land/lipgloss/v2": "v2.0.6", "charm.land/huh/v2": "v2.0.3",
              "ratatui": "0.31.0", "crossterm": "0.29.0", "charmbracelet/gum": "v2.0.2"}

    def test_offline_never_calls_the_fetcher(self):
        def explode(*a, **k):
            raise AssertionError("network used offline")
        with make_refs() as d:
            rows = cv.build_rows(d, online=False, fetcher=explode)
        self.assertTrue(all(r["status"] == "-" and r["latest"] is None for r in rows))

    def test_online_rows(self):
        with make_refs() as d:
            rows = {r["name"]: r for r in cv.build_rows(d, online=True, fetcher=fake_fetcher(self.LATEST))}
        self.assertEqual(rows["Ink"]["status"], "major behind")
        self.assertEqual(rows["Textual"]["status"], "patch behind")
        self.assertEqual(rows["Ratatui"]["status"], "major behind")
        self.assertEqual(rows["crossterm"]["status"], "current")
        self.assertEqual(rows["gum"]["status"], "current")

    def test_failed_lookup_is_unknown_and_missing_pin_unparsed(self):
        with make_refs({"gum.md": "nothing\n"}) as d:
            rows = {r["name"]: r for r in cv.build_rows(d, online=True, fetcher=fake_fetcher({}))}
        self.assertEqual(rows["Ink"]["status"], "unknown")
        self.assertEqual(rows["gum"]["status"], "unparsed")

    def test_prerelease_latest_does_not_count_as_ahead(self):
        with make_refs() as d:
            rows = cv.build_rows(d, online=True, fetcher=fake_fetcher({"ink": "7.0.0-beta.1"}))
        self.assertEqual({r["name"]: r for r in rows}["Ink"]["status"], "current")

    def test_table_columns(self):
        with make_refs() as d:
            rows = cv.build_rows(d, online=True, fetcher=fake_fetcher(self.LATEST))
        head = cv.format_table(rows, True).splitlines()[0].split()
        self.assertEqual(head[:4], ["package", "pinned", "latest", "status"])
        offline = cv.format_table(cv.build_rows(cv.DEFAULT_REFS), False)
        self.assertIn("npm:ink", offline)

    def test_exit_code(self):
        rows = [{"status": "current"}, {"status": "major behind"}]
        self.assertEqual(cv.exit_code(rows, None), 0)
        self.assertEqual(cv.exit_code(rows, "major"), 1)
        self.assertEqual(cv.exit_code([{"status": "minor behind"}], "major"), 0)


class MainTests(unittest.TestCase):
    def run_main(self, argv, fetcher=None):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cv.main(argv, fetcher=fetcher or fake_fetcher({}))
        return code, out.getvalue(), err.getvalue()

    def test_offline_prints_inventory_and_exits_zero(self):
        with make_refs() as d:
            code, out, err = self.run_main(["--refs", d])
        self.assertEqual(code, 0)
        self.assertIn("Bubble Tea", out)
        self.assertIn("offline", err)

    def test_fail_on_major(self):
        with make_refs() as d:
            code, _, _ = self.run_main(["--refs", d, "--online", "--fail-on", "major"],
                                       fetcher=fake_fetcher(ReportTests.LATEST))
            self.assertEqual(code, 1)
            code, _, _ = self.run_main(["--refs", d, "--online"], fetcher=fake_fetcher(ReportTests.LATEST))
            self.assertEqual(code, 0)

    def test_json_output(self):
        with make_refs() as d:
            code, out, _ = self.run_main(["--refs", d, "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(len(json.loads(out)), 13)


if __name__ == "__main__":
    unittest.main()
