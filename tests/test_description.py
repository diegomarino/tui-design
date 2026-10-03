"""Tests for description_to_mock.py, score_description.py, merge_description.py (stdlib unittest).
Run: python3 -m unittest discover -s scripts/tests"""

import argparse
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "tui-design" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import compare  # noqa: E402
import description_to_mock as d2m  # noqa: E402
import merge_description as md  # noqa: E402
import score_description as sd  # noqa: E402
from _mock import parse_mock  # noqa: E402
from _theme import load_theme  # noqa: E402

DEMO = SCRIPTS.parent / "assets" / "demo" / "fleet--normal--80x24.mock"
THEME = "catppuccin-mocha"


def run(*args, **kw):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, **kw)


def errors(mock_text):
    return [f for f in parse_mock(mock_text, "r.mock").findings if f.level == "ERROR"]


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.truth = sd.build_truth_from_mock(str(DEMO), THEME)
        cls.theme = load_theme(THEME)

    def score(self, hyp):
        return sd.score(hyp, self.truth, self.theme)

    @staticmethod
    def row(rep, group, metric):
        return next(r for r in rep.rows if r["group"] == group and r["metric"] == metric)


class DescriptionToMockTests(Base):
    def test_truth_roundtrip_is_cell_exact_and_lints_clean(self):
        text = d2m.description_to_mock(self.truth, THEME)
        self.assertEqual(errors(text), [])
        self.assertIn("#! region r2 list 0,1,32,21 Services (6)", text)
        a, b = self.tmp / "orig.mock", self.tmp / "recon.mock"
        a.write_text(DEMO.read_text())
        b.write_text(text)
        left, right = compare.load_side(str(a), "a", THEME), compare.load_side(str(b), "b", THEME)
        d = compare.cell_diff(left, right, THEME)
        self.assertEqual((d["text"], d["bg"], d["fg"]), (0, 0, 0))

    def test_only_asserted_content_is_drawn(self):
        skeleton = copy.deepcopy(self.truth)
        skeleton["elements"] = [e for e in skeleton["elements"] if e.get("name") != sd.RUN]
        text = d2m.description_to_mock(skeleton, THEME)
        self.assertEqual(errors(text), [])
        self.assertNotIn("api-gateway   ", text)               # row content was not asserted
        self.assertIn("select", text)                          # key hints were
        with_screen = d2m.description_to_mock(skeleton, THEME, use_screen_text=True)
        self.assertIn("running", with_screen)

    def test_border_styles_titles_and_sides(self):
        desc = {"meta": {"size": {"cols": 20, "rows": 5}}, "elements": [], "regions": [
            {"id": "r1", "role": "panel", "bbox": {"x": 0, "y": 0, "w": 10, "h": 5}, "border": {"style": "double"},
             "title": {"text": "Hi", "position": "top_left"}},
            {"id": "r2", "role": "panel", "bbox": {"x": 10, "y": 0, "w": 10, "h": 3}, "border": {"style": "ascii", "sides": ["top", "left"]},
             "title": {"text": "T", "position": "top_right"}}]}
        rows = d2m.description_to_mock(desc, THEME).split("\n")[-6:-1]
        self.assertTrue(rows[0].startswith("╔═ Hi ═══╗"), rows[0])
        self.assertEqual(rows[4][:10], "╚════════╝")
        self.assertTrue(rows[0][10:].startswith("+---"), rows[0])
        self.assertTrue(rows[1][10:].startswith("|"))
        self.assertEqual(errors("\n".join(["#! tui-mockup 1", "#! size: 20x5"] + rows)), [])

    def test_titles_never_break_the_border(self):
        """A title sits between the corner-adjacent border cells; padding only where it fits (lazygit: `╭─[1]─Status─╮`)."""
        def mock_for(regions, elements=(), screen=None):
            desc = {"meta": {"size": {"cols": 30, "rows": 4}}, "elements": list(elements), "regions": regions}
            if screen:
                desc["screen_text"] = screen
            return d2m.description_to_mock(desc, THEME, use_screen_text=False)
        reg = lambda i, x, w, title, pos="top_left": {"id": i, "role": "panel", "bbox": {"x": x, "y": 0, "w": w, "h": 3},
                                                         "border": {"style": "rounded"}, "title": {"text": title, "position": pos}}
        el = lambda i, x, text: {"id": i, "region": "r1", "type": "heading", "bbox": {"x": x, "y": 0, "w": len(text), "h": 1}, "text": text}
        # title element right after `╭─` (no padding in the app): no pad cells may be invented next to it
        text = mock_for([reg("r1", 0, 14, "[1]─Status")], [el("e1", 2, "[1]─Status")])
        self.assertEqual(errors(text), [])
        self.assertIn("╭─[1]─Status─╮", text.split("\n")[-5])
        # wide title in a narrow box, every position: truncated to fit, border intact
        for pos in ("top_left", "top_center", "top_right", "bottom_left"):
            text = mock_for([reg("r1", 0, 12, "A very long title indeed", pos)])
            self.assertEqual(errors(text), [], (pos, text))
        # screen_text decides the padding when present
        text = mock_for([reg("r1", 0, 16, "Files")], [], ["╭─Files────────╮"] + [""] * 3)
        self.assertEqual(errors(text), [])
        text = mock_for([reg("r1", 0, 16, "Files")], [], ["╭─ Files ──────╮"] + [""] * 3)
        self.assertIn("╭─ Files ──────╮", text)

    def test_noncanonical_colours_map_to_tokens_with_notes(self):
        red = self.theme.ansi[1]
        desc = {"meta": {"size": {"cols": 12, "rows": 1}}, "regions": [], "elements": [
            {"id": "e1", "region": "r0", "type": "text", "bbox": {"x": 0, "y": 0, "w": 3, "h": 1}, "text": "abc",
             "style": {"fg": {"token": "ansi.red", "source": "sgr"}}},
            {"id": "e2", "region": "r0", "type": "text", "bbox": {"x": 4, "y": 0, "w": 3, "h": 1}, "text": "def",
             "style": {"fg": {"token": "term.fg", "source": "sgr"}, "attrs": ["reverse", "blink"]}},
            {"id": "e3", "region": "r0", "type": "text", "bbox": {"x": 8, "y": 0, "w": 4, "h": 1}, "text": "g{}[?]",
             "style": {"fg": {"token": "p:208", "raw": "#ff8700", "source": "pixel"}}}]}
        text = d2m.description_to_mock(desc, THEME)
        self.assertEqual(errors(text), [])
        self.assertRegex(text, r"#! note: ansi\.red mapped to \S+ \(nearest fg token")
        self.assertIn("attribute 'blink' not representable", text)
        self.assertIn("{inverse}def{/}", text)
        self.assertIn("g{{}}?", text)                          # braces escaped, [?] -> ?
        self.assertIsNotNone(red)

    def test_cli(self):
        p = self.tmp / "t.json"
        p.write_text(json.dumps(self.truth))
        out = self.tmp / "o.mock"
        r = run(SCRIPTS / "description_to_mock.py", p, "-o", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(run(SCRIPTS / "render_mockup.py", out, "--check").returncode, 0)
        self.assertEqual(run(SCRIPTS / "description_to_mock.py", self.tmp / "missing.json").returncode, 2)


class ScoreTests(Base):
    def test_truth_vs_truth_is_perfect(self):
        rep = self.score(copy.deepcopy(self.truth))
        self.assertEqual(rep.failed, [])
        for g, m in (("regions", "mean IoU"), ("text", "CER (`[?]` = 1 sub)"), ("colour", "fg token accuracy"), ("recon", "text cells match")):
            self.assertEqual(self.row(rep, g, m)["value"] if g != "text" else 0.0, 1.0 if g != "text" else 0.0)
        self.assertEqual(self.row(rep, "key hints", "F1 (key, action)")["value"], 1.0)

    def test_dropping_a_region_fails_region_metrics(self):
        hyp = copy.deepcopy(self.truth)
        hyp["regions"] = [r for r in hyp["regions"] if r["id"] != "r3"]
        rep = self.score(hyp)
        self.assertLess(self.row(rep, "regions", "mean IoU")["value"], 0.9)
        self.assertEqual(self.row(rep, "regions", "mean IoU")["status"], "fail")
        self.assertAlmostEqual(self.row(rep, "regions", "recall @IoU>=0.5")["value"], 0.8)

    def test_text_errors_raise_cer(self):
        hyp = copy.deepcopy(self.truth)
        hyp["screen_text"][5] = hyp["screen_text"][5].replace("search", "seerch")        # 1 substitution
        hyp["screen_text"][6] = hyp["screen_text"][6].replace("worker", "w[?]rker")      # `[?]` = 1 sub, not hallucination
        rep = self.score(hyp)
        cer, hall = self.row(rep, "text", "CER (`[?]` = 1 sub)"), self.row(rep, "text", "hallucination CER")
        self.assertAlmostEqual(cer["value"], 2 / 1877)
        self.assertAlmostEqual(hall["value"], 1 / 1877)
        self.assertIn("1 `[?]`", hall["detail"])

    def test_heavy_text_damage_fails_gates(self):
        hyp = copy.deepcopy(self.truth)
        hyp["screen_text"] = [r[: len(r) // 2] for r in hyp["screen_text"]]
        rep = self.score(hyp)
        self.assertEqual(self.row(rep, "text", "CER (`[?]` = 1 sub)")["status"], "fail")
        self.assertEqual(self.row(rep, "text", "hallucination CER")["status"], "pass")      # deletions are not hallucinations

    def test_swapped_token_drops_colour_accuracy_but_rgb_equal_tokens_do_not(self):
        hyp = copy.deepcopy(self.truth)
        runs = [e for e in hyp["elements"] if e.get("name") == sd.RUN and e["style"]["fg"]["raw"] == self.theme.hex("fg.default")]
        self.assertTrue(runs)
        for e in runs:                                    # same RGB class, different token name: no penalty
            e["style"]["fg"] = {"token": "fg.title", "source": "vision"}
        self.assertEqual(self.row(self.score(hyp), "colour", "fg token accuracy")["value"], 1.0)
        for e in runs:                                    # different RGB: penalised
            e["style"]["fg"] = {"token": "status.error", "source": "vision"}
        row = self.row(self.score(hyp), "colour", "fg token accuracy")
        self.assertLess(row["value"], 0.95)
        self.assertEqual(row["status"], "fail")

    def test_roles_state_keyhints_neutrality_and_grid(self):
        hyp = copy.deepcopy(self.truth)
        for r in hyp["regions"]:
            r["role"] = "panel" if r["role"] in ("list", "detail", "statusbar") else r["role"]
        self.assertLess(self.row(self.score(hyp), "roles", "role/type accuracy")["value"], 0.85)
        hyp = copy.deepcopy(self.truth)
        hyp["regions"][1]["state"] = {"focused": True, "evidence": "x"}
        self.assertEqual(self.row(self.score(hyp), "state", "focus/selected exact")["status"], "fail")
        hyp = copy.deepcopy(self.truth)
        for e in hyp["elements"]:
            for h in e.get("key_hints", []):
                h["action"] = "other"
        self.assertEqual(self.row(self.score(hyp), "key hints", "F1 (key, action)")["status"], "fail")
        hyp = copy.deepcopy(self.truth)
        hyp["observations"] = [{"id": "o1", "text": "The footer is too cluttered and should be cleaner"}]
        row = self.row(self.score(hyp), "neutrality", "evaluative words")
        self.assertEqual((row["value"], row["status"]), (3, "fail"))
        hyp = copy.deepcopy(self.truth)
        hyp["meta"]["size"]["cols"] = 79
        self.assertEqual(self.row(self.score(hyp), "grid", "size")["status"], "fail")

    def test_underline_and_reverse_are_gated(self):
        hyp = copy.deepcopy(self.truth)
        truth = copy.deepcopy(self.truth)
        runs = [e for e in truth["elements"] if e.get("name") == sd.RUN and e["text"].strip()][:2]
        for e in runs:
            e["style"]["attrs"] = e["style"]["attrs"] + ["underline"]
        rep = sd.score(hyp, truth, self.theme)
        row = self.row(rep, "attributes", "underline P/R")
        self.assertEqual(row["status"], "fail")
        self.assertTrue(row["value"].endswith("/0.00"))

    def test_state_truth_from_mock_headers(self):
        reg = {r["id"]: r for r in self.truth["regions"]}
        self.assertTrue(reg["r2"]["state"]["focused"])
        sel = [e for e in self.truth["elements"] if (e.get("state") or {}).get("selected")]
        self.assertEqual([(e["region"], e["bbox"]["y"]) for e in sel], [("r2", 2)])       # `#! selected r2 0`: first interior row
        self.assertEqual(self.row(self.score(copy.deepcopy(self.truth)), "state", "focus/selected exact")["status"], "pass")
        by = lambda d: {r["id"]: r for r in d["regions"]}
        hyp = copy.deepcopy(self.truth)
        by(hyp)["r3"]["state"] = {"focused": True, "evidence": "x"}                       # r3 focused besides r2
        self.assertEqual(self.row(self.score(hyp), "state", "focus/selected exact")["status"], "fail")
        hyp = copy.deepcopy(self.truth)                                                   # the describer flags the interior of the focused pane
        by(hyp)["r2"]["state"] = {}
        hyp["regions"].append({"id": "r9", "role": "list", "bbox": {"x": 1, "y": 2, "w": 30, "h": 12}, "state": {"focused": True, "evidence": "x"}})
        self.assertEqual(self.row(self.score(hyp), "state", "focus/selected exact")["status"], "pass")
        hyp = copy.deepcopy(self.truth)                                                   # selection on the wrong row
        for e in hyp["elements"]:
            if (e.get("state") or {}).get("selected"):
                e["bbox"]["y"] += 3
        self.assertEqual(self.row(self.score(hyp), "state", "focus/selected exact")["status"], "fail")
        # a truth without state headers does not gate (info), however many flags the hypothesis asserts
        bare = copy.deepcopy(self.truth)
        for r in bare["regions"]:
            r.pop("state", None)
        bare["elements"] = [e for e in bare["elements"] if not (e.get("state") or {}).get("selected")]
        row = self.row(sd.score(copy.deepcopy(self.truth), bare, self.theme), "state", "focus/selected exact")
        self.assertEqual(row["status"], "info")

    def test_mock_headers_parse_and_lint(self):
        base = "#! tui-mockup 1\n#! size: 20x4\n#! region r1 list 0,0,10,4\n"
        m = parse_mock(base + "#! focus r1\n#! selected r1 2\nabc\n", "m")
        self.assertEqual((m.focus, m.selected), ("r1", [("r1", 2)]))
        self.assertEqual([f for f in m.findings if f.level in ("ERROR", "WARN")], [])
        for bad in ("#! focus r7\n", "#! focus\n", "#! selected r1\n", "#! selected r1 9\n", "#! selected r7 0\n", "#! focus r1\n#! focus r1\n"):
            self.assertTrue([f for f in parse_mock(base + bad + "abc\n", "m").findings if f.level == "ERROR"], bad)
        for f in SCRIPTS.parent.glob("assets/**/*.mock"):                                # shipped mocks stay lint-clean
            self.assertEqual([x for x in parse_mock(f.read_text(), str(f)).findings if x.level == "ERROR"], [], f.name)
        self.assertEqual(parse_mock(DEMO.read_text(), "d").focus, "r2")

    def test_chart_cells_leave_the_cer_and_reverse_blanks_are_backgrounds(self):
        truth = {"meta": {"size": {"cols": 12, "rows": 2}}, "regions": [
            {"id": "r1", "role": "chart", "bbox": {"x": 0, "y": 0, "w": 6, "h": 1}},
            {"id": "r2", "role": "panel", "bbox": {"x": 0, "y": 1, "w": 12, "h": 1}}],
            "elements": [], "screen_text": ["⣀⣤⣶⣿⣶⣤ cpu", "hello world "]}
        hyp = copy.deepcopy(truth)
        hyp["screen_text"] = ["[?*]" + " " * 5 + " cpu", "hello world "]      # as merged: the run takes one cell of its own region only
        rep = sd.score(hyp, truth, self.theme)
        self.assertEqual(self.row(rep, "text", "CER (`[?]` = 1 sub)")["value"], 0.0)       # chart cells are excluded
        chart = self.row(rep, "text", "chart CER (chart regions)")
        self.assertEqual(chart["status"], "info")
        self.assertGreater(chart["value"], 0.0)
        # reverse on blanks / full blocks is not gated: a bar written without `reverse` still scores
        bar = lambda attrs, ch: {"meta": {"size": {"cols": 4, "rows": 1}}, "regions": [], "screen_text": [ch * 4], "elements": [
            {"id": "e1", "region": "r0", "type": "text", "bbox": {"x": 0, "y": 0, "w": 4, "h": 1}, "text": ch * 4,
             "style": {"bg": {"token": "accent.primary", "source": "sgr"}, "attrs": attrs}}]}
        for ch in (" ", "\u2588"):
            rep = sd.score(bar([], ch), bar(["reverse"], ch), self.theme)
            self.assertEqual(self.row(rep, "attributes", "reverse P/R")["value"], None)
        rep = sd.score(bar([], "x"), bar(["reverse"], "x"), self.theme)                     # on a letter it is still gated
        self.assertEqual(self.row(rep, "attributes", "reverse P/R")["status"], "fail")

    def test_cli_exit_codes_and_formats(self):
        t = self.tmp / "truth.json"
        t.write_text(json.dumps(self.truth))
        r = run(SCRIPTS / "score_description.py", "-", t)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("**PASS**", r.stdout)
        bad = copy.deepcopy(self.truth)
        bad["screen_text"][0] = "x" * 80
        b = self.tmp / "bad.json"
        b.write_text(json.dumps(bad))
        r = run(SCRIPTS / "score_description.py", b, t, "--format", "json")
        self.assertEqual(r.returncode, 1)
        self.assertFalse(json.loads(r.stdout)["pass"])
        r = run(SCRIPTS / "score_description.py", t, "--truth-from-mock", DEMO, "--theme", THEME, "--save-truth", self.tmp / "st.json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(any(reg["id"] == "r2" and reg["role"] == "list" for reg in json.loads((self.tmp / "st.json").read_text())["regions"]))
        self.assertEqual(run(SCRIPTS / "score_description.py", self.tmp / "none.json", t).returncode, 2)

    def test_skeleton_scores_below_bar(self):
        """The ansi_grid --describe skeleton alone is a legitimate but weak hypothesis."""
        skel = copy.deepcopy(self.truth)
        skel["elements"] = [e for e in skel["elements"] if e.get("name") != sd.RUN]
        skel["regions"] = [r for r in skel["regions"] if r["role"] in ("screen", "keybar")]
        rep = self.score(skel)
        self.assertTrue(rep.failed)
        self.assertEqual(self.row(rep, "text", "CER (`[?]` = 1 sub)")["status"], "pass")      # screen_text is exact


class MergeTests(unittest.TestCase):
    def test_path_a_merge_validates(self):
        if not (shutil.which("uv") or _has_jsonschema()):
            self.skipTest("no jsonschema and no uv")
        tmp = Path(tempfile.mkdtemp())
        ansi = tmp / "f.ansi"
        self.assertEqual(run(SCRIPTS / "render_mockup.py", DEMO, "-o", ansi).returncode, 0)
        grid = tmp / "grid.json"
        self.assertEqual(run(SCRIPTS / "ansi_grid.py", ansi, "-o", grid).returncode, 0)
        rows = [r for r in ansi_rows(ansi)]
        p1 = {"regions": [{"id": "r1", "role": "list", "bbox": {"x": 0, "y": 1, "w": 32, "h": 21}},
                          {"id": "r2", "role": "detail", "bbox": {"x": 32, "y": 1, "w": 48, "h": 21}}],
              "anchor_lines": [], "focus_summary": "r1 border.focus frame", "uncertainties": []}
        (tmp / "p1.json").write_text(json.dumps(p1))
        (tmp / "p2").mkdir()
        for rid, (x, w) in (("r1", (0, 32)), ("r2", (32, 48))):
            els = [{"id": "e1", "region": rid, "type": "label", "bbox": {"x": x + 2, "y": 3, "w": 4, "h": 1}, "text": "wrong"}]
            (tmp / "p2" / f"{rid}.json").write_text(json.dumps({"region": rid, "rows": [{"y": y, "x": x, "text": rows[y][x:x + w]} for y in range(1, 22)],
                                                                 "elements": els, "uncertainties": []}))
        out = tmp / "d.json"
        r = run(SCRIPTS / "merge_description.py", "--pass1", tmp / "p1.json", "--pass2", tmp / "p2", "--grid", grid, "--theme", THEME, "-o", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(out.read_text())
        self.assertEqual(d["meta"]["source_path"], "capture")
        self.assertEqual(len(d["screen_text"]), 24)
        ids = [e["id"] for e in d["elements"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(e["text"] != "wrong" for e in d["elements"]))       # element text := screen_text slice
        self.assertTrue(d["regions"][0]["state"]["focused"])
        self.assertTrue(all(e["style"]["fg"]["source"] == "sgr" for e in d["elements"] if "style" in e and "fg" in e["style"]))
        bad = tmp / "bad.json"
        bad.write_text(json.dumps({"region": "r1", "rows": [], "elements": [{"id": "x"}]}))
        self.assertEqual(run(SCRIPTS / "merge_description.py", "--validate", bad, "--part", "describer_pass2").returncode, 1)

    def test_legacy_source_path_values_still_validate_and_score(self):
        """Old descriptions carry meta.source_path "A"/"B"; they must stay valid, scoreable and renderable."""
        if not (shutil.which("uv") or _has_jsonschema()):
            self.skipTest("no jsonschema and no uv")
        truth = sd.build_truth_from_mock(str(DEMO), THEME)
        self.assertEqual(truth["meta"]["source_path"], "capture")
        theme = load_theme(THEME)
        for value in ("capture", "screenshot", "A", "B"):
            doc = copy.deepcopy(truth)
            doc["meta"]["source_path"] = value
            self.assertEqual(md.validate([(doc, None)])[0], [], value)
            rep = sd.score(doc, truth, theme)
            self.assertTrue(rep.rows, value)
            self.assertEqual(errors(d2m.description_to_mock(doc, THEME)), [], value)
        bad = copy.deepcopy(truth)
        bad["meta"]["source_path"] = "C"
        self.assertTrue(md.validate([(bad, None)])[0])
        self.assertEqual(md.norm_path("A"), "capture")
        self.assertEqual(md.norm_path("B"), "screenshot")


class MergeStructureTests(unittest.TestCase):
    """Rules 13 (parent borders/titles from pass 1) and 14 (z-order) of merge_description.py, no pixels needed."""

    @staticmethod
    def build(modal=True):
        reg = lambda i, role, x, y, w, h, z=0, border=None, title=None, children=None: {
            "id": i, "role": role, "bbox": {"x": x, "y": y, "w": w, "h": h}, "z": z,
            **({"border": {"style": border}} if border else {}), **({"title": {"text": title, "position": "top_left"}} if title else {}),
            **({"children": children} if children is not None else {})}
        p1 = {"regions": [reg("r0", "screen", 0, 0, 20, 6, children=[
            reg("r1", "panel", 0, 0, 20, 6, border="rounded", title="Parent", children=[reg("r2", "list", 1, 1, 10, 4), reg("r3", "detail", 11, 1, 8, 4)]),
            *([reg("r4", "modal", 5, 2, 10, 3, z=1, border="single", title="M")] if modal else [])])], "anchor_lines": [], "focus_summary": "none visible", "uncertainties": []}
        rows = lambda x, w, ys, txt: [{"y": y, "x": x, "text": txt(y)[:w].ljust(w)} for y in ys]
        el = lambda i, rid, x, y, w, text: {"id": i, "region": rid, "type": "label", "bbox": {"x": x, "y": y, "w": w, "h": 1}, "text": text}
        p2 = [{"region": "r2", "rows": rows(1, 10, range(1, 5), lambda y: "left %d xxxxx" % y), "uncertainties": [],
               "elements": [el("e1", "r2", 1, 1, 10, "left 1 xxx"), el("e2", "r2", 6, 3, 4, "xxxx"), el("e3", "r2", 1, 4, 10, "left 4 xxx")]},
              {"region": "r3", "rows": rows(11, 8, range(1, 5), lambda y: "right %d" % y), "elements": [], "uncertainties": []},
              {"region": "r4", "rows": [{"y": 2, "x": 5, "text": "┌─ M ────┐"}, {"y": 3, "x": 5, "text": "│ ok     │"}, {"y": 4, "x": 5, "text": "└────────┘"}],
               "elements": [], "uncertainties": []}]
        a = argparse.Namespace(path=None, cols=20, rows=6, subject=None, model="m", theme=None)
        return a, p1, p2

    def test_parent_border_and_title_from_pass1(self):
        a, p1, p2 = self.build(modal=False)
        d = md.Merger(a, p1, p2[:2], None, None).run()
        t = d["screen_text"]
        self.assertTrue(t[0].startswith("╭") and t[0].endswith("╮") and " Parent " in t[0], t[0])
        self.assertEqual((t[5][0], t[5][-1], t[2][0], t[2][-1]), ("╰", "╯", "│", "│"))
        self.assertFalse(any("[?]" in r for r in t))
        self.assertTrue(any(u["kind"] == "position" and "rule 13" in u["note"] for u in d["uncertainties"]))   # convention noted (no cell ink)
        self.assertEqual(errors(d2m.description_to_mock(d, THEME, use_screen_text=True)), [])

    def test_higher_z_wins_and_covered_cells_are_occluded_not_unknown(self):
        a, p1, p2 = self.build()
        d = md.Merger(a, p1, p2, None, None).run()
        t = d["screen_text"]
        self.assertEqual(t[2][5:14], "┌─ M ────┐"[:9])                                    # the modal's own text owns the covered cells
        self.assertEqual((t[3][5], t[4][5]), ("│", "└"))
        self.assertEqual(t[3][1:5], "left")                                                # outside the modal the lower regions are intact
        self.assertFalse(any("[?]" in r for r in t), t)
        occ = [u for u in d["uncertainties"] if u["kind"] == "occluded"]
        self.assertTrue(occ and all("rule 14" in u["note"] for u in occ))
        self.assertEqual({u["ref"] for u in occ if u["ref"] in ("r2", "r3")}, {"r2", "r3"})
        modal = next(r for r, _ in md.walk(d["regions"]) if r["id"] == "r4")
        self.assertEqual(sorted(modal["occludes"]), ["r2", "r3"])
        ids = {e["id"]: e for e in d["elements"]}
        self.assertEqual(ids["e1"]["bbox"], {"x": 1, "y": 1, "w": 10, "h": 1})           # untouched
        self.assertNotIn("e2", ids)                                                      # (6..9, 3) lies wholly under the modal: dropped
        self.assertIn("e3", ids)

    def test_pass1_only_description_and_meta(self):
        a, p1, _ = self.build(modal=False)
        p1["anchor_lines"] = [{"y": 1, "x_start": 2, "text": "hello"}]
        grid = {"cols": 20, "rows": 6, "cell_px": [16.8, 36.0], "origin_px": [28.0, 84.0], "grid_confidence": 0.77, "advice": "ok",
                "image_size_px": [400, 300], "image": "/x/shot.png", "crop_px": [0, 40, 400, 300], "notes": ["title bar stripped"],
                "method": {"row_pitch": "comb"}, "pass1": {"file": "pass1.png", "scale": 1.0, "cell_px": [16.8, 36.0], "origin_px": [0.3, 0.2]}}
        crops = [{"id": "r2", "file": "region-r2.png", "bbox": {"x": 0, "y": 0, "w": 12, "h": 6}, "scale": 1.5, "cell_px": [25.2, 54.0], "origin_px": [1, 1]}]
        d = md.Merger(a, p1, [], grid, None, crops).run()
        self.assertEqual(d["elements"], [])
        self.assertIn("hello", d["screen_text"][1])
        self.assertTrue(any("pass 2 was not run" in u["note"] for u in d["uncertainties"]))
        img = d["meta"]["image"]
        self.assertEqual((img["cell_px"], img["width_px"], img["grid_confidence"]), ([16.8, 36.0], 400, "medium"))
        self.assertTrue(any("pass-1 image pass1.png" in x for x in img["preprocessing"]) and any("1 region crops" in x for x in img["preprocessing"]))
        self.assertIn("screenshot shot.png", d["meta"]["capture"]["tool"])
        # live capture: capture block from capture_tui.sh meta.json
        cap = md.Merger.capture_block({"tmux": "tmux 3.7c", "command": ["lazygit"], "env": {"TERM": "xterm"}, "keys": ["Enter"], "stable": True,
                                       "quiet_ms": 400, "cursor": {"x": 79, "y": 23, "visible": False}, "alternate_on": True})
        self.assertEqual(cap, {"tool": "capture_tui.sh / tmux 3.7c", "env": {"TERM": "xterm"}, "keys_sent": ["Enter"], "stable": True,
                               "quiet_ms": 400, "alternate_screen": True, "cursor": {"x": 79, "y": 23, "visible": False}})

    def test_cli_accepts_zero_pass2_files(self):
        if not (shutil.which("uv") or _has_jsonschema()):
            self.skipTest("no jsonschema and no uv")
        a, p1, _ = self.build()
        tmp = Path(tempfile.mkdtemp())
        (tmp / "p1.json").write_text(json.dumps(p1))
        r = run(SCRIPTS / "merge_description.py", "--pass1", tmp / "p1.json", "--cols", 20, "--rows", 6, "-o", tmp / "d.json")
        self.assertIn("pass-1-only", r.stderr)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads((tmp / "d.json").read_text())["elements"], [])


def _has_jsonschema():
    try:
        import jsonschema  # noqa: F401
        return True
    except ImportError:
        return False


def ansi_rows(path):
    from _ansi import parse_ansi
    return parse_ansi(Path(path).read_text()).text_rows()


if __name__ == "__main__":
    unittest.main()
