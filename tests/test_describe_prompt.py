"""Tests for describe_prompt.py (stdlib unittest).
Run: python3 -m unittest discover -s scripts/tests"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "tui-design" / "scripts"
SKILL = SCRIPTS.parent
TOOL = SCRIPTS / "describe_prompt.py"
SCHEMA = json.loads((SKILL / "references" / "schemas" / "tui-description.schema.json").read_text())
PROMPT_MD = SKILL / "references" / "prompts" / "describe-tui.md"


def run(*args):
    return subprocess.run([sys.executable, str(TOOL), *map(str, args)], capture_output=True, text=True)


def has_validator():
    try:
        import jsonschema  # noqa: F401
        return True
    except ImportError:
        return bool(shutil.which("uv"))


PASS1 = {"regions": [{"id": "r0", "role": "screen", "bbox": {"x": 0, "y": 0, "w": 80, "h": 24}, "children": [
    {"id": "r1", "role": "header", "bbox": {"x": 0, "y": 0, "w": 80, "h": 1}},
    {"id": "r2", "role": "panel", "bbox": {"x": 0, "y": 1, "w": 40, "h": 22}, "title": {"text": "Outer"},
     "children": [{"id": "r3", "role": "list", "bbox": {"x": 1, "y": 2, "w": 38, "h": 10}}]}]}],
    "anchor_lines": [], "focus_summary": "none visible", "uncertainties": []}


class Base(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d)
        for name in ("pass1.png", "pass1-ruler.png", "region-r3.png", "region-r3-ruler.png", "region-r1.png"):
            (self.d / name).write_bytes(b"")
        self.grid = {"cols": 80, "rows": 24, "cell_px": [16.8, 36.0], "origin_px": [27.3, 82.6],
                     "grid_confidence": 0.97, "advice": "ok",
                     "pass1": {"file": "pass1.png", "cell_px": [10.5, 22.5], "origin_px": [0.2, 0.4], "scale": 0.625}}
        self.write("grid.json", self.grid)
        self.write("pass1.json", PASS1)
        self.write("crops.json", [{"id": "r3", "file": "region-r3.png", "bbox": {"x": 0, "y": 1, "w": 40, "h": 12},
                                   "scale": 1.2, "cell_px": [20.16, 43.2], "origin_px": [0.4, 0.8]},
                                  {"id": "r1", "file": "region-r1.png", "bbox": {"x": 0, "y": 0, "w": 80, "h": 2},
                                   "scale": 1.0, "cell_px": [16.8, 36.0], "origin_px": [0.3, 0.6]}])

    def write(self, name, obj):
        (self.d / name).write_text(json.dumps(obj))
        return self.d / name

    def prompt(self, *extra, code=0):
        r = run("--grid", self.d / "grid.json", *extra)
        self.assertEqual(r.returncode, code, r.stderr)
        return r.stdout


class TestPass1(Base):
    def test_facts_come_from_the_pass1_image(self):
        out = self.prompt("--pass", "1")
        self.assertIn("80 columns x 24 rows", out)
        self.assertIn("0.97 (advice: ok)", out)
        self.assertIn("cell (0,0) has its top-left corner at pixel (0.2,0.4); each cell is 10.5 x 22.5 px", out)
        self.assertIn(str((self.d / "pass1.png").resolve()), out)
        self.assertNotIn("pass1-ruler.png", out)          # advice ok: plain image only
        self.assertNotRegex(out, r"\{\{[a-z_]+\}\}")
        self.assertIn("w = 80", out)                       # full-width band rule filled
        self.assertIn("PASS 1 — LAYOUT", out)
        self.assertNotIn("PASS 2", out)

    def test_check_ruler_adds_the_ruler(self):
        self.grid["advice"] = "check-ruler"
        self.write("grid.json", self.grid)
        r = run("--pass", "1", "--grid", self.d / "grid.json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("pass1-ruler.png", r.stdout)
        self.assertIn("check-ruler", r.stderr)

    def test_give_size_is_refused_unless_forced(self):
        self.grid["advice"] = "give-size"
        self.write("grid.json", self.grid)
        r = run("--pass", "1", "--grid", self.d / "grid.json")
        self.assertEqual(r.returncode, 3)
        self.assertIn("--cols", r.stderr)
        self.assertIn("advice: give-size", self.prompt("--pass", "1", "--force"))

    def test_output_file(self):
        out = self.d / "p.txt"
        self.prompt("--pass", "1", "-o", out)
        self.assertIn("OUTPUT CONTRACT", out.read_text())

    def test_earlier_grid_format(self):
        g = {"cols": 80, "rows": 24, "cell_px": [16.8, 36.0], "origin_px": [27.34, 82.65], "grid_confidence": 0.99,
             "pass1": {"scale": 1.0, "cell_px_scaled": [16.8, 36.01],
                       "tiles": [{"file": "pass1.png", "ruler": "pass1-ruler.png", "cols": [0, 80]}]}}
        self.write("grid.json", g)
        out = self.prompt("--pass", "1")
        self.assertIn("pixel (0.34,0.65); each cell is 16.8 x 36.01 px", out)
        self.assertIn("advice: ok", out)

    def test_tiled_pass1(self):
        (self.d / "pass1-2.png").write_bytes(b"")
        self.grid["pass1"] = {"file": "pass1-1.png", "cell_px": [9.0, 20.0], "origin_px": [0.1, 0.2], "scale": 0.54,
                              "tiles": [{"file": "pass1-1.png", "cols": [0, 42], "origin_px": [0.1, 0.2]},
                                        {"file": "pass1-2.png", "cols": [38, 80], "origin_px": [0.5, 0.2]}]}
        self.write("grid.json", self.grid)
        out = self.prompt("--pass", "1", "--tile", "2")
        self.assertIn("pass1-2.png  (plain, columns 38..79)", out)
        self.assertIn("cell (38,0) has its top-left corner at pixel (0.5,0.2)", out)


class TestPass2(Base):
    def test_leaf_region_with_crop(self):
        out = self.prompt("--pass", "2", "--crops", self.d / "crops.json", "--pass1", self.d / "pass1.json",
                          "--region", "r3")
        self.assertIn("PASS 2 — DETAIL OF REGION r3", out)
        self.assertIn("cells x=0..39, y=1..12", out)       # region + 1-cell margin
        self.assertIn("each cell is 20.16 x 43.2 px", out)
        self.assertIn("cell (0,1) has its top-left corner", out)
        self.assertIn('"e301"', out)
        self.assertIn("region-r3-ruler.png", out)
        rec = re.search(r"The pass-1 record of this region is:\n(.*)\n", out).group(1)
        self.assertEqual(json.loads(rec)["id"], "r3")
        self.assertNotIn("children", rec)
        self.assertNotRegex(out, r"\{\{[a-z_]+\}\}")

    def test_parent_region_is_refused(self):
        r = run("--pass", "2", "--grid", self.d / "grid.json", "--crops", self.d / "crops.json",
                "--pass1", self.d / "pass1.json", "--region", "r2")
        self.assertEqual(r.returncode, 2)
        self.assertIn("leaf", r.stderr)

    def test_missing_crop_is_reported(self):
        PASS1["regions"][0]["children"].append({"id": "r9", "role": "other", "bbox": {"x": 50, "y": 5, "w": 4, "h": 2}})
        try:
            self.write("pass1.json", PASS1)
            r = run("--pass", "2", "--grid", self.d / "grid.json", "--crops", self.d / "crops.json",
                    "--pass1", self.d / "pass1.json", "--region", "r9")
        finally:
            PASS1["regions"][0]["children"].pop()
        self.assertEqual(r.returncode, 2)
        self.assertIn("--regions", r.stderr)

    def test_without_crops_uses_the_full_screen(self):
        out = self.prompt("--pass", "2", "--pass1", self.d / "pass1.json", "--region", "r1")
        self.assertIn("The image is the full screen; describe only region r1: cells x=0..79, y=0..0", out)

    def test_live_capture_addendum(self):
        sk = self.write("sk.json", {"screen_text": ["Fleet  1 Services", "╭─ Outer ─╮"] + [""] * 22})
        out = self.prompt("--pass", "2", "--crops", self.d / "crops.json", "--pass1", self.d / "pass1.json",
                          "--region", "r1", "--path", "capture", "--text", sk)
        self.assertIn("GIVEN TEXT", out)
        self.assertIn("00|Fleet  1 Services", out)
        self.assertIn("01|╭─ Outer ─╮", out)
        r = run("--pass", "1", "--grid", self.d / "grid.json", "--path", "capture")
        self.assertEqual(r.returncode, 2)

    def test_legacy_path_aliases(self):
        sk = self.write("sk2.json", {"screen_text": ["Fleet  1 Services"] + [""] * 23})
        a = self.prompt("--pass", "1", "--path", "A", "--text", sk)
        b = self.prompt("--pass", "1", "--path", "capture", "--text", sk)
        self.assertEqual(a, b)
        self.assertEqual(self.prompt("--pass", "1", "--path", "B"),
                         self.prompt("--pass", "1", "--path", "screenshot"))
        self.assertEqual(run("--pass", "1", "--grid", self.d / "grid.json", "--path", "C").returncode, 2)


class TestContract(unittest.TestCase):
    def enums(self, node, acc):
        if isinstance(node, dict):
            if "enum" in node:
                acc.update(v for v in node["enum"] if isinstance(v, str))
            for v in node.values():
                self.enums(v, acc)
        elif isinstance(node, list):
            for v in node:
                self.enums(v, acc)
        return acc

    def test_every_allowed_value_is_listed(self):
        p1 = run("--contract", "1").stdout
        p2 = run("--contract", "2").stdout
        d = SCHEMA["$defs"]
        for v in self.enums(d["region"], set()):
            self.assertIn(f'"{v}"', p1)
        for v in self.enums(d["element"]["properties"]["type"], set()):
            self.assertIn(f'"{v}"', p2)
        for v in ("top_left", "bottom_right", "start", "end", "both", "high", "medium", "low"):
            self.assertIn(f'"{v}"', p1 + p2)
        for k in d["describer_pass1"]["properties"]:
            self.assertIn(f"  {k}:", p1)
        for k in d["describer_pass2"]["properties"]:
            self.assertIn(f"  {k}:", p2)
        self.assertIn("never id strings", p1)
        self.assertIn("never true/false", p2)

    def test_describer_subset(self):
        both = run("--contract", "1").stdout + run("--contract", "2").stdout
        for absent in ("ink_mismatch", "disagreement", "token_candidates", "attrs_source", '"pixel"', '"sgr"'):
            self.assertNotIn(absent, both)


class TestPromptFile(unittest.TestCase):
    @unittest.skipUnless(has_validator(), "no jsonschema and no uv")
    def test_worked_examples_validate(self):
        blocks = re.findall(r"```json\n(.*?)```", PROMPT_MD.read_text(), re.S)
        parts = ["describer_pass1", "describer_pass2", "describer_pass2"]
        self.assertEqual(len(blocks), len(parts))
        with tempfile.TemporaryDirectory() as tmp:
            for i, (b, part) in enumerate(zip(blocks, parts)):
                f = Path(tmp) / f"ex{i}.json"
                f.write_text(b)
                r = subprocess.run([sys.executable, str(SCRIPTS / "merge_description.py"), "--validate", str(f),
                                    "--part", part], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
