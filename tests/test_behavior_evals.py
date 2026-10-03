"""evals/run_behavior_evals.py: case loading, assertion checks on fixture transcripts, cost math, executed
assertions (exec, private-tmux tty probes, frame match), the vision-judge plumbing and the fixture generator.
No agent or model is called.

Skipped when evals/ is absent (the copy of the skill an agent works with has no evals/).
"""

import argparse
import gzip
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills" / "tui-design"
RUNNER = REPO / "evals" / "run_behavior_evals.py"
CASES = REPO / "evals" / "behavior-evals.json"

if RUNNER.exists():
    _spec = importlib.util.spec_from_file_location("run_behavior_evals", RUNNER)
    rbe = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(rbe)
else:  # pragma: no cover
    rbe = None

GOOD_MOCK = """#! tui-mockup 1
#! size: 20x4
#! caps: attrs=bold,dim colors=256 glyphs=unicode source=assumed
#! region r1 list 0,0,20,4 Jobs
{border.focus}╭─{/}{fg.title bold} Jobs {/}{border.focus}───────────╮{/}
{border.focus}│{/} {fg.default}build{/}            {border.focus}│{/}
{border.focus}│{/} {fg.muted}deploy{/}           {border.focus}│{/}
{border.focus}╰──────────────────╯{/}
"""
BAD_MOCK = GOOD_MOCK.replace("{fg.muted}deploy{/}", "{#ff0000 italic}deploy-everything{/}")


def ev(*objs):
    return [json.dumps(o) for o in objs]


@unittest.skipIf(rbe is None, "evals/ not present (installed copy)")
class CaseLoading(unittest.TestCase):
    def test_shipped_cases_are_valid(self):
        doc = json.loads(CASES.read_text())
        self.assertEqual(rbe.validate_cases(doc), [])
        cases = rbe.load_cases(CASES)
        self.assertTrue(20 <= len(cases) <= 30)
        for c in cases:
            self.assertTrue(c["assertions"])
        # every skill area has at least one case; both languages are used
        self.assertEqual({c["area"] for c in cases}, set(rbe.AREAS))
        self.assertEqual({c["lang"] for c in cases}, {"en", "es"})

    def test_validation_catches_problems(self):
        doc = {"cases": [
            {"id": "a", "prompt": "p", "fixtures": [{"path": "../x", "lines": []}],
             "assertions": [{"id": "q", "type": "nope"}]},
            {"id": "a", "prompt": "", "assertions": [{"id": "r", "type": "answer_regex", "pattern": "("}]},
        ]}
        errs = "\n".join(rbe.validate_cases(doc))
        for needle in ("bad fixture path", "unknown type", "duplicate id", "missing prompt", "bad regex"):
            self.assertIn(needle, errs)

    def test_subset_and_unknown_ids(self):
        ids = [c["id"] for c in rbe.load_cases(CASES)][:2]
        self.assertEqual([c["id"] for c in rbe.load_cases(CASES, ids)], ids)
        with self.assertRaises(ValueError):
            rbe.load_cases(CASES, ["no-such-case"])

    def test_no_leaky_test_data(self):
        text = json.dumps(json.loads(CASES.read_text())["cases"], ensure_ascii=False).lower()
        fx = rbe.FIXTURES_DIR
        for f in fx.rglob("*"):
            if f.is_file() and f.suffix in rbe.TEXT_SUFFIXES:
                text += f.read_text(errors="replace").lower()
        banned = json.loads(CASES.read_text())["banned_terms"]
        self.assertTrue(banned)
        for term in banned:
            self.assertNotIn(term.lower(), text)

    def test_new_fields_validated(self):
        base = {"id": "a", "prompt": "p", "area": "shell", "assertions": [{"id": "x", "type": "no_new_files"}]}
        self.assertEqual(rbe.validate_cases({"cases": [base]}), [])
        bad = [dict(base, area="nope"),
               dict(base, id="b", fixtures=[{"path": "x.png", "src": "no/such.png"}]),
               dict(base, id="c", fixtures=[{"path": "x", "src": "screenshot-audit/screenshot.png", "lines": []}]),
               dict(base, id="d", judge_reference=["missing.mock"]),
               dict(base, id="e", assertions=[{"id": "y", "type": "exec"}]),
               dict(base, id="f", assertions=[{"id": "y", "type": "hex_near", "palette": "nope.json"}]),
               dict(base, id="g", requires=[{"why": "no cmd"}])]
        errs = "\n".join(rbe.validate_cases({"cases": bad}))
        for needle in ("area must be", "not found under evals/fixtures", "exactly one of lines/content/src",
                       "judge_reference", "missing ['cmd']", "palette", "requires entry"):
            self.assertIn(needle, errs)

    def test_tags_and_filters(self):
        cases = rbe.load_cases(CASES)
        wave2 = rbe.filter_cases(cases, ["wave2"], None)
        self.assertTrue(wave2 and all(c.get("depends_on") == "wave2" for c in wave2))
        rest = rbe.filter_cases(cases, None, ["wave2"])
        self.assertEqual(len(rest) + len(wave2), len(cases))
        ex = rbe.filter_cases(cases, ["executed"], None)
        self.assertTrue(all(set(a["type"] for a in c["assertions"]) & rbe.EXECUTED_TYPES for c in ex))
        self.assertIn("vision", {t for c in cases for t in rbe.case_tags(c)})
        self.assertEqual([c["id"] for c in rbe.filter_cases(cases, ["shell"], ["tmux"])], [])
        self.assertTrue(rbe.filter_cases(cases, ["shell", "audit"], None))

    def test_default_results_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "skills" / "tui-design"
            skill.mkdir(parents=True)
            self.assertEqual(rbe.default_results_dir(skill), REPO / "evals" / "runs")
            self.assertEqual(rbe.default_results_dir(), REPO / "evals" / "runs")

    def test_default_skill_dir_is_next_to_evals(self):
        self.assertEqual(rbe.find_skill_dir(REPO / "evals"), SKILL)


@unittest.skipIf(rbe is None, "evals/ not present (installed copy)")
class Models(unittest.TestCase):
    def test_adapters_and_efforts(self):
        self.assertEqual(rbe.adapter_for("z-ai/glm-5.3"), "omp")
        self.assertEqual(rbe.adapter_for("opus"), "claude")
        self.assertEqual(rbe.adapter_for("gpt-6.1-sol"), "codex")
        self.assertEqual(rbe.parse_model_spec("z-ai/glm-5.3"), ("z-ai/glm-5.3", "high"))
        self.assertEqual(rbe.parse_model_spec("qwen/qwen3.8-max-0902"), ("qwen/qwen3.8-max-0902", "medium"))
        self.assertEqual(rbe.parse_model_spec("z-ai/glm-5.3-flash@low"), ("z-ai/glm-5.3-flash", "low"))
        with self.assertRaises(ValueError):
            rbe.adapter_for("llama3")

    def test_commands_isolate_arms(self):
        wd, home, pf = Path("/w"), Path("/h"), Path("/r/prompt.txt")
        inv = rbe.build_command("omp", "z-ai/glm-5.3", "high", "skill", pf, wd, home)
        self.assertIn("--skills=tui-design", inv.argv)
        inv = rbe.build_command("omp", "z-ai/glm-5.3", "high", "baseline", pf, wd, home)
        self.assertIn("--no-skills", inv.argv)
        inv = rbe.build_command("claude", "opus", "medium", "skill", pf, wd, home)
        self.assertTrue(inv.env["CLAUDE_CONFIG_DIR"].endswith(".claude-eval"))
        self.assertIn("acceptEdits", inv.argv)
        self.assertIn("--strict-mcp-config", inv.argv)
        inv = rbe.build_command("claude", "opus", "medium", "skill", pf, wd, home, ["Bash(tmux:*)"])
        self.assertIn("Bash(tmux:*)", inv.argv)
        self.assertGreater(inv.argv.index("Bash(tmux:*)"), inv.argv.index("--allowedTools"))
        inv = rbe.build_command("codex", "gpt-6.1-sol", "medium", "skill", pf, wd, home)
        self.assertEqual(inv.env["HOME"], "/h")
        self.assertTrue(inv.env["CODEX_HOME"].endswith(".codex-eval"))
        self.assertIn("workspace-write", inv.argv)
        self.assertIn("model_reasoning_effort=medium", inv.argv)
        for feat in ("plugins", "remote_plugin", "apps"):
            self.assertIn(feat, inv.argv)
        self.assertEqual(inv.argv[-1], "-")             # codex reads the prompt from stdin

    def test_install_skill_excludes_evals(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = rbe.install_skill(Path(tmp), "claude")
            self.assertTrue((dest / "SKILL.md").exists())
            self.assertFalse((dest / "evals").exists())
            self.assertEqual(list(dest.rglob("__pycache__")), [])
            self.assertEqual(dest.relative_to(tmp).as_posix(), ".claude/skills/tui-design")


@unittest.skipIf(rbe is None, "evals/ not present (installed copy)")
class TranscriptParsing(unittest.TestCase):
    def test_omp_sums_assistant_message_end_only(self):
        msg1 = {"role": "assistant", "content": [{"type": "toolCall"}],
                "usage": {"input": 100, "output": 10, "cacheRead": 50, "cacheWrite": 0, "reasoningTokens": 4,
                          "cost": {"total": 0.01}}}
        msg2 = {"role": "assistant", "content": [{"type": "text", "text": "Done."}],
                "usage": {"input": 200, "output": 20, "cacheRead": 0, "cacheWrite": 5, "cost": {"total": 0.02}}}
        lines = ev({"type": "message_end", "message": {"role": "user", "content": []}},
                   {"type": "message_end", "message": msg1},
                   {"type": "tool_execution_start", "toolName": "read", "args": {"path": "skill://tui-design"}},
                   {"type": "turn_end", "message": msg1},
                   {"type": "message_end", "message": msg2},
                   {"type": "turn_end", "message": msg2})
        r = rbe.parse_omp(rbe._parse_lines(lines))
        self.assertAlmostEqual(r["cost_usd"], 0.03)
        self.assertEqual(r["tokens"], {"input": 300, "cached": 50, "cache_write": 5, "output": 30, "reasoning": 4})
        self.assertEqual(r["final_answer"], "Done.")
        self.assertEqual(r["tool_calls"], 1)
        self.assertTrue(r["skill_loaded"])

    def test_claude_stream(self):
        lines = ev({"type": "system", "subtype": "init"},
                   {"type": "assistant", "message": {"content": [
                       {"type": "tool_use", "name": "Skill", "input": {"skill": "tui-design"}}]}},
                   {"type": "assistant", "message": {"content": [
                       {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}]}},
                   {"type": "result", "result": "Answer", "total_cost_usd": 0.5, "is_error": False,
                    "modelUsage": {"claude-opus": {"inputTokens": 10, "outputTokens": 300,
                                                   "cacheReadInputTokens": 1000, "cacheCreationInputTokens": 200,
                                                   "thinkingTokens": 50}}})
        r = rbe.parse_claude(rbe._parse_lines(lines))
        self.assertEqual(r["final_answer"], "Answer")
        self.assertEqual(r["tool_calls"], 2)
        self.assertTrue(r["skill_loaded"])
        self.assertEqual(r["cost_usd"], 0.5)
        self.assertEqual(r["tokens"], {"input": 10, "cached": 1000, "cache_write": 200, "output": 300, "reasoning": 50})
        self.assertEqual(rbe.parse_claude([])["error"], "no result event")

    def test_codex_cost_is_equivalent(self):
        lines = ev({"type": "item.completed", "item": {"type": "command_execution",
                                                        "command": "cat .agents/skills/tui-design/SKILL.md"}},
                   {"type": "item.completed", "item": {"type": "file_change"}},
                   {"type": "item.completed", "item": {"type": "agent_message", "text": "Fixed."}},
                   {"type": "turn.completed", "usage": {"input_tokens": 1_000_000, "cached_input_tokens": 600_000,
                                                        "output_tokens": 100_000, "reasoning_output_tokens": 40_000}})
        r = rbe.parse_codex(rbe._parse_lines(lines), rbe.catalog().get("gpt-6.1-sol").price)
        self.assertEqual(rbe.parse_codex(rbe._parse_lines(lines))["cost_basis"], "unknown")   # no price, no cost
        self.assertEqual(r["tokens"]["input"], 400_000)
        self.assertEqual(r["tokens"]["cached"], 600_000)
        # 0.4M × $2 + 0.6M × $0.10 + 0.1M × $10 (reasoning already inside output)
        self.assertAlmostEqual(r["cost_usd"], 0.8 + 0.06 + 1.0)
        self.assertEqual(r["cost_basis"], "equivalent")
        self.assertEqual(r["tool_calls"], 2)
        self.assertTrue(r["skill_loaded"])
        self.assertEqual(r["final_answer"], "Fixed.")


@unittest.skipIf(rbe is None, "evals/ not present (installed copy)")
class Transcripts(unittest.TestCase):
    def test_tool_texts_per_adapter(self):
        omp = rbe._parse_lines(ev({"type": "tool_execution_start", "toolName": "bash",
                                   "args": {"command": "bash scripts/capture_tui.sh -s 80x24"}}))
        self.assertIn("capture_tui.sh", rbe.tool_texts("omp", omp))
        cl = rbe._parse_lines(ev({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": "tmux -L x capture-pane -p"}}]}}))
        self.assertIn("capture-pane", rbe.tool_texts("claude", cl))
        cx = rbe._parse_lines(ev({"type": "item.completed", "item": {"type": "command_execution",
                                                                     "command": "python3 sample_colors.py s.png"}}))
        self.assertIn("sample_colors.py", rbe.tool_texts("codex", cx))
        ctx = {"workdir": Path("."), "files": [], "answer": "", "transcript": rbe.tool_texts("claude", cl)}
        self.assertTrue(rbe.check_program({"type": "transcript_regex", "pattern": "capture_tui\\.sh|capture-pane"}, ctx)[0])
        self.assertFalse(rbe.check_program({"type": "transcript_regex", "pattern": "sample_colors"}, ctx)[0])

    def test_events_gzip_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp)
            plain = runs / "r1.events.jsonl"
            plain.write_text("\n".join(ev({"type": "result", "result": "ok"})) + "\n")
            self.assertEqual(rbe.events_path(runs, "r1"), plain)
            gz = rbe.gzip_events(plain)
            self.assertFalse(plain.exists())
            self.assertEqual(rbe.events_path(runs, "r1"), gz)
            self.assertEqual(rbe.read_events(gz), [{"type": "result", "result": "ok"}])
            self.assertIsNone(rbe.events_path(runs, "nope"))
            self.assertEqual(rbe.read_events(None), [])


@unittest.skipIf(rbe is None, "evals/ not present (installed copy)")
class CostMath(unittest.TestCase):
    def test_estimate_low_high(self):
        lo, hi = rbe.estimate_cost("opus", 1_000_000, 0.5, 100_000)
        self.assertAlmostEqual(lo, 0.5 * 4 + 0.5 * 0.2 + 0.1 * 20)
        self.assertAlmostEqual(hi, 4 + 2)
        lo, hi = rbe.estimate_cost("z-ai/glm-5.3", 1_000_000, 0.5, 0)
        self.assertAlmostEqual(lo, 1.4)  # no cache price: cached tokens billed as input
        self.assertAlmostEqual(hi, 1.4)

    def test_budget_hard_stop(self):
        b = rbe.Budget(1.0)
        self.assertTrue(b.can_start())
        self.assertTrue(b.update_live("r1", 0.4))
        self.assertFalse(b.update_live("r2", 0.7))
        b.commit("r1", 0.4)
        b.commit("r2", 0.7)
        self.assertAlmostEqual(b.spent, 1.1)
        self.assertFalse(b.can_start())
        self.assertTrue(rbe.Budget(None).can_start())

    def test_token_profile(self):
        runs = [{"case": "c", "arm": "skill", "tokens": {"input": 100, "cached": 300, "cache_write": 0,
                                                         "output": 50, "reasoning": 20},
                 "judge": {"cost_usd": 0.01}}]
        p = rbe.token_profile(runs)[("c", "skill")]
        self.assertEqual(p["input_total"], 400)
        self.assertAlmostEqual(p["cached_share"], 0.75)
        self.assertEqual(p["output"], 50)

    def test_dry_run_reports_median_and_p90(self):
        def run(case, tin, out):
            return {"run_id": f"{case}-{tin}", "case": case, "arm": "skill", "model": "z-ai/glm-5.3-flash",
                    "tokens": {"input": tin, "cached": 0, "cache_write": 0, "output": out, "reasoning": 0}}
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "runs").mkdir()
            for i, r in enumerate([run("a", 100_000, 1000), run("b", 120_000, 1000), run("c", 110_000, 1000),
                                   run("d", 9_000_000, 50_000)]):
                (Path(tmp) / "runs" / f"{i}.json").write_text(json.dumps(r))
            cases = [{"id": x, "prompt": "p", "area": "build", "assertions": []} for x in "abcd"]
            txt = rbe.dry_run(cases, [("z-ai/glm-5.3", "high")], ["skill"], 1, [Path(tmp)])
        row = next(line for line in txt.splitlines() if line.startswith("z-ai/glm-5.3 "))
        median, mnc, p90, per_case = (float(x) for x in row.split()[-4:])
        one = (115_000 * 1.40 + 1000 * 4.40) / 1e6                 # pooled median run, GLM prices
        self.assertAlmostEqual(median, round(4 * one, 2), places=2)
        self.assertGreater(p90, 10 * median)                        # the runaway shows up only in the tail
        self.assertLess(per_case, p90)                              # clipped at the arm's p90

    def test_token_profile_median_resists_a_runaway(self):
        def run(tin, out):
            return {"case": "c", "arm": "skill", "tokens": {"input": tin, "cached": 0, "cache_write": 0,
                                                            "output": out, "reasoning": 0}}
        runs = [run(100, 10), run(120, 12), run(110, 11), run(5_000_000, 900)]
        runs.append({"case": "c", "arm": "skill", "skipped": "no textual", "tokens": None})
        p = rbe.token_profile(runs)[("c", "skill")]
        self.assertEqual(p["input_total"], 115)          # median of 100,110,120,5M
        self.assertEqual(p["p90_input"], 5_000_000)
        self.assertEqual(p["n"], 4)
        self.assertEqual(rbe._p90(list(range(1, 11))), 9)
        self.assertEqual(rbe._median([3, 1, 2]), 2)


@unittest.skipIf(rbe is None, "evals/ not present (installed copy)")
class Assertions(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def ctx(self, answer="", fixtures=None):
        hashes = rbe.write_fixtures(self.tmp, fixtures or [])
        return hashes, (lambda: {"workdir": self.tmp, "answer": answer, "files": rbe.classify_files(self.tmp, hashes),
                                 "skill_dir": SKILL, "fixture_hexes": set()})

    def check(self, a, ctx):
        return rbe.check_program(a, ctx)[0]

    def test_glob(self):
        paths = ["a.mock", "d/b.mock", "d/e/c.mock", "x.txt"]
        self.assertEqual(rbe.match_glob(paths, "**/*.mock"), ["a.mock", "d/b.mock", "d/e/c.mock"])
        self.assertEqual(rbe.match_glob(paths, "*.mock"), ["a.mock"])
        self.assertEqual(rbe.match_glob(paths, "d/*.mock"), ["d/b.mock"])

    def test_files_classified_and_infra_ignored(self):
        _, mk = self.ctx(fixtures=[{"path": "in.txt", "lines": ["x"]}, {"path": "keep.txt", "lines": ["y"]}])
        (self.tmp / "in.txt").write_text("changed")
        (self.tmp / "new.md").write_text("n")
        (self.tmp / ".agents" / "skills").mkdir(parents=True)
        (self.tmp / ".agents" / "skills" / "s.md").write_text("s")
        st = {f["path"]: f["status"] for f in mk()["files"]}
        self.assertEqual(st, {"in.txt": "modified", "keep.txt": "fixture", "new.md": "new"})
        self.assertFalse(self.check({"type": "fixture_unchanged", "path": "in.txt"}, mk()))
        self.assertTrue(self.check({"type": "fixture_unchanged", "path": "keep.txt"}, mk()))
        self.assertFalse(self.check({"type": "no_new_files"}, mk()))

    def test_skill_copies_are_ignored(self):
        dest = rbe.install_skill(self.tmp / "inst", "omp")
        idx = rbe.skill_file_index(dest)
        (self.tmp / "references").mkdir()
        shutil.copy(SKILL / "references" / "formats.md", self.tmp / "references" / "formats.md")
        shutil.copy(SKILL / "assets" / "demo" / "fleet--normal--80x24.mock", self.tmp / "fleet--normal--80x24.mock")
        (self.tmp / "mine.md").write_text("my report #123456")
        shutil.rmtree(self.tmp / "inst")
        files = rbe.classify_files(self.tmp, {}, idx)
        st = {f["path"]: f["status"] for f in files}
        self.assertEqual(st["references/formats.md"], "skill-copy")
        self.assertEqual(st["fleet--normal--80x24.mock"], "skill-copy")
        self.assertEqual(st["mine.md"], "new")
        ctx = {"workdir": self.tmp, "answer": "", "files": files, "skill_dir": SKILL, "fixture_hexes": set()}
        self.assertFalse(rbe.check_program({"type": "mock_lint", "glob": "**/*.mock"}, ctx)[0])   # copy not counted
        # --regrade: a copy of an older skill version is still recognised by its path
        (self.tmp / "skill" / "references").mkdir(parents=True)
        (self.tmp / "skill" / "references" / "formats.md").write_text("older text")
        loose = {f["path"]: f["status"] for f in rbe.classify_files(self.tmp, {}, rbe.skill_file_index(SKILL, True))}
        self.assertEqual(loose["skill/references/formats.md"], "skill-copy")
        self.assertEqual(loose["mine.md"], "new")
        self.assertTrue(rbe.check_program({"type": "hex_near", "palette": "screenshot-audit/palette.json",
                                           "scope": "files", "files_glob": "references/*.md"}, ctx)[0])

    def test_mock_lint_and_caps(self):
        _, mk = self.ctx()
        a = {"type": "mock_lint", "glob": "**/*.mock", "min_files": 1}
        self.assertFalse(self.check(a, mk()))  # no files
        (self.tmp / "d").mkdir()
        (self.tmp / "d" / "ok--normal--20x4.mock").write_text(GOOD_MOCK)
        self.assertTrue(self.check(a, mk()))
        (self.tmp / "d" / "bad--normal--20x4.mock").write_text(BAD_MOCK)
        ok, detail = rbe.check_program(a, mk())
        self.assertFalse(ok)
        self.assertIn("bad--normal", detail)
        caps = {"type": "mock_caps", "glob": "**/*.mock", "forbid": {"source": ["code"]}, "require_line": True}
        self.assertTrue(self.check(caps, mk()))
        (self.tmp / "d" / "c.mock").write_text(GOOD_MOCK.replace("source=assumed", "source=code"))
        self.assertFalse(self.check(caps, mk()))
        self.assertTrue(self.check({"type": "mock_variants", "glob": "**/*.mock", "min": 3}, mk()))
        self.assertFalse(self.check({"type": "mock_variants", "glob": "**/*.mock", "min": 4}, mk()))

    def test_file_regex_modes(self):
        _, mk = self.ctx()
        (self.tmp / "main.go").write_text("return m, tea.ExecProcess(c, done)\n")
        self.assertTrue(self.check({"type": "file_regex", "glob": "main.go", "pattern": r"tea\.ExecProcess\(",
                                    "mode": "all"}, mk()))
        self.assertTrue(self.check({"type": "file_regex", "glob": "main.go", "pattern": r"\bc\.Run\(\)",
                                    "mode": "none"}, mk()))
        self.assertFalse(self.check({"type": "file_regex", "glob": "*.mock", "pattern": "x", "mode": "any"}, mk()))

    def test_answer_regex_and_box_widths(self):
        good = "Plan:\n```\n┌────┐\n│ ab │\n│ cd │\n└────┘\n```\n"
        bad = "```\n┌────┐\n│ ab  │\n│ cd │\n└────┘\n```"
        wide = "```\n┌──────┐\n│ 界界 │\n│ abcd │\n└──────┘\n```"
        _, mk = self.ctx(answer=good)
        a = {"type": "answer_box_widths", "max_width": 80}
        self.assertTrue(self.check(a, mk()))
        _, mk = self.ctx(answer=bad)
        self.assertFalse(self.check(a, mk()))
        _, mk = self.ctx(answer=wide)
        self.assertTrue(self.check(a, mk()))  # wide glyphs count 2 cells
        _, mk = self.ctx(answer="no sketch at all")
        self.assertTrue(self.check(a, mk()))
        _, mk = self.ctx(answer="At 80x24 the list wins; in a 60-column split only one pane fits.")
        self.assertTrue(self.check({"type": "answer_regex", "pattern": r"(?i)\b80\s*[x×]\s*24\b"}, mk()))
        self.assertFalse(self.check({"type": "answer_regex", "pattern": "zzz"}, mk()))
        self.assertFalse(self.check({"type": "answer_regex", "pattern": r"\d+", "min": 4}, mk()))

    def test_hex_known(self):
        a = {"type": "hex_known", "scope": "both",
             "sources": ["references/schemes/gruvbox.md", "references/themes/gruvbox-*.json"]}
        _, mk = self.ctx(answer="selection bg #504945, error #fb4934, `#FB4934` too")
        self.assertTrue(self.check(a, mk()))
        _, mk = self.ctx(answer="error #ff5555")
        self.assertFalse(self.check(a, mk()))
        _, mk = self.ctx(answer="no colors, issue #12 and &#123;")
        self.assertTrue(self.check(a, mk()))

    def test_files_contain(self):
        _, mk = self.ctx(fixtures=[{"path": "data.json", "lines": ["alpha beta gamma"]}])
        a = {"type": "files_contain", "strings": ["alpha", "beta", "gamma"], "min_distinct": 2}
        self.assertFalse(self.check(a, mk()))  # fixture itself does not count
        (self.tmp / "f.mock").write_text("alpha  beta")
        self.assertTrue(self.check(a, mk()))

    def test_judge_reply_parsing(self):
        reply = 'Sure:\n```json\n{"answers": [{"id": "a", "answer": "Yes", "reason": "ok"},' \
                ' {"id": "b", "answer": "no", "reason": "missing"}]}\n```'
        v = rbe.parse_judge_reply(reply, ["a", "b", "c"])
        self.assertEqual(v["a"][0], True)
        self.assertEqual(v["b"][0], False)
        self.assertIsNone(v["c"][0])
        self.assertTrue(all(x[0] is None for x in rbe.parse_judge_reply("garbage", ["a"]).values()))

    def test_judge_reply_unescaped_quotes(self):
        # a judge quoting the answer inside a reason without escaping breaks strict JSON; verdicts are still clear
        reply = '```json\n{\n  "answers": [\n    {\n      "id": "a",\n      "answer": "no",\n' \
                '      "reason": "the fix comes last"\n    },\n    {\n      "id": "b",\n      "answer": "yes",\n' \
                '      "reason": "names rows and hides 3 behind "… 3 more"."\n    }\n  ]\n}\n```'
        v = rbe.parse_judge_reply(reply, ["a", "b", "c"])
        self.assertEqual(v["a"], (False, "the fix comes last"))
        self.assertIs(v["b"][0], True)
        self.assertIn("3 more", v["b"][1])
        self.assertIsNone(v["c"][0])

    def test_score_neutral_split(self):
        s = rbe.score([{"passed": True, "neutral": True}, {"passed": False, "neutral": False},
                       {"passed": None, "neutral": True}])
        self.assertEqual((s["passed"], s["graded"], s["neutral_passed"], s["neutral_graded"]), (1, 2, 1, 1))
        self.assertFalse(s["all_passed"])

    def test_hex_near_palette(self):
        pal = json.loads((rbe.FIXTURES_DIR / "screenshot-audit" / "palette.json").read_text())["colors"]
        a = {"type": "hex_near", "palette": "screenshot-audit/palette.json", "scope": "answer", "max_dist": 30}
        _, mk = self.ctx(answer=f"title {pal[0]} and text {pal[-1]}")
        self.assertTrue(self.check(a, mk()))
        r, g, b = rbe.hex_rgb(pal[0])
        near = f"#{min(r + 8, 255):02x}{g:02x}{b:02x}"
        _, mk = self.ctx(answer=f"bg {near}")
        self.assertTrue(self.check(a, mk()))             # sampling slop is fine
        _, mk = self.ctx(answer="accent #00ff00")
        ok, detail = rbe.check_program(a, mk())
        self.assertFalse(ok)
        self.assertIn("#00ff00", detail)
        _, mk = self.ctx(answer="no colors")
        self.assertTrue(self.check(a, mk()))
        self.assertFalse(self.check(dict(a, min_hex=1), mk()))
        (self.tmp / "report.md").write_text("fg #00ff00")
        _, mk = self.ctx(answer="")
        self.assertFalse(self.check(dict(a, scope="both"), mk()))

    def test_hex_known_same_source_and_contrast(self):
        out = self.tmp / "theme.py"
        subprocess.run([sys.executable, str(SKILL / "scripts" / "export_theme.py"), "catppuccin-mocha",
                        "--target", "textual", "-o", str(out)], check=True, capture_output=True)
        a = {"type": "hex_known", "sources": ["references/themes/*.json"], "scope": "files", "files_glob": "theme.py",
             "min_used": 6, "same_source": True}
        _, mk = self.ctx()
        ok, detail = rbe.check_program(a, mk())
        self.assertTrue(ok, detail)
        self.assertIn("catppuccin-mocha", detail)
        ok, detail = rbe.check_program(dict(a, contrast=True), mk())
        self.assertTrue(ok, detail)
        out.write_text(out.read_text() + '\nEXTRA = "#fb4934"  # a gruvbox red\n')
        ok, detail = rbe.check_program(a, mk())
        self.assertFalse(ok)
        self.assertIn("no single source", detail)
        out.write_text('X = "#1e1e2e"\n')
        self.assertFalse(self.check(a, mk()))           # min_used

    def test_mock_craft(self):
        a = {"type": "mock_craft", "glob": "**/*.mock", "min_files": 1}
        _, mk = self.ctx()
        self.assertFalse(self.check(a, mk()))
        (self.tmp / "ok--normal--20x4.mock").write_text(GOOD_MOCK)
        self.assertTrue(self.check(a, mk()))
        chip = GOOD_MOCK.replace("{fg.muted}deploy{/}          ", "{fg.muted}[ Items ]{/}       ")
        (self.tmp / "chip--normal--20x4.mock").write_text(chip)
        ok, detail = rbe.check_program(a, mk())
        self.assertFalse(ok)
        self.assertIn("CR1", detail)
        waived = chip.replace("#! region", "#! note: craft-ok CR1 tab label in a test\n#! region")
        (self.tmp / "chip--normal--20x4.mock").write_text(waived)
        self.assertTrue(self.check(a, mk()))

    def test_shipped_broken_fixture_fails_lint(self):
        case = next(c for c in rbe.load_cases(CASES) if c["id"] == "fix-broken-mock")
        hashes, mk = self.ctx(fixtures=case["fixtures"])
        results = {r["id"]: r["passed"] for r in rbe.grade_program(case, mk())}
        self.assertFalse(results["lint-clean"])
        self.assertFalse(results["no-hex"])
        self.assertTrue(results["caps-kept"])



def _fixed_watch(src: str) -> str:
    """The SIGTERM fixture with the LC9 fix: route SIGTERM into the normal cleanup, then exit 143."""
    return src.replace("def main():", "import signal\n\n\ndef _term(signum, frame):\n    raise SystemExit(143)\n\n\n"
                                       "def main():\n    signal.signal(signal.SIGTERM, _term)")


@unittest.skipIf(rbe is None, "evals/ not present (installed copy)")
class Executed(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.env = rbe.exec_env(self.tmp / "h", self.tmp / "t")

    def test_exec_checks(self):
        (self.tmp / "w").mkdir()
        wd = self.tmp / "w"
        ok, d = rbe.run_exec({"cmd": "printf 'a\\nb\\n' > out.txt; echo hi", "stdout_regex": "hi",
                              "files": [{"path": "out.txt", "min_lines": 2, "not_regex": "\\x1b\\["}]}, wd, self.env)
        self.assertTrue(ok, d)
        ok, d = rbe.run_exec({"cmd": "printf '\\033[1mx\\033[0m' > out.txt",
                              "files": [{"path": "out.txt", "not_regex": "\\x1b\\["}]}, wd, self.env)
        self.assertFalse(ok)
        ok, d = rbe.run_exec({"cmd": "echo Traceback >&2; exit 3", "expect_exit": [0],
                              "stderr_not_regex": "Traceback"}, wd, self.env)
        self.assertFalse(ok)
        self.assertIn("exit 3", d)
        ok, d = rbe.run_exec({"cmd": "sleep 5", "timeout": 1}, wd, self.env)
        self.assertFalse(ok)
        self.assertIn("timeout", d)
        ok, d = rbe.run_exec({"cmd": "true", "skip_unless": "exit 1"}, wd, self.env)
        self.assertIsNone(ok)
        self.assertIn("skipped", d)
        ok, d = rbe.run_exec({"cmd": "test -z \"$TMUX\" && test \"$TMUX_TMPDIR\" = " + str(self.tmp / "t")}, wd, self.env)
        self.assertTrue(ok, d)                          # never the user's tmux server

    def test_shell_contract_fixture_fails_pipe_checks(self):
        case = next(c for c in rbe.load_cases(CASES) if c["id"] == "shell-contract-cli")
        wd = self.tmp / "w"
        wd.mkdir()
        rbe.write_fixtures(wd, case["fixtures"])
        by = {a["id"]: a for a in case["assertions"]}
        self.assertFalse(rbe.run_exec(by["pipe-head-quiet"], wd, self.env)[0])
        self.assertFalse(rbe.run_exec(by["plain-when-redirected"], wd, self.env)[0])
        self.assertFalse(rbe.run_exec(by["usage-exit-2"], wd, self.env)[0])

    def test_frame_match(self):
        wd = self.tmp / "w"
        wd.mkdir()
        mock = rbe.FIXTURES_DIR / "build-textual" / "jobs--normal--80x24.mock"
        shutil.copy(mock, wd / "design.mock")
        subprocess.run([sys.executable, str(SKILL / "scripts" / "render_mockup.py"), str(wd / "design.mock"),
                        "-o", str(wd / "frame.ansi")], check=True, capture_output=True)
        ok, d = rbe.run_frame_match({"mock": "design.mock", "frame": "frame.ansi"}, wd, self.env)
        self.assertTrue(ok, d)
        self.assertIn("0.0%", d)
        shutil.copy(SKILL / "assets" / "demo" / "fleet--normal--80x24.mock", wd / "other.mock")
        subprocess.run([sys.executable, str(SKILL / "scripts" / "render_mockup.py"), str(wd / "other.mock"),
                        "-o", str(wd / "other.ansi")], check=True, capture_output=True)
        self.assertFalse(rbe.run_frame_match({"mock": "design.mock", "frame": "other.ansi"}, wd, self.env)[0])
        self.assertFalse(rbe.run_frame_match({"mock": "design.mock", "frame": "missing.ansi"}, wd, self.env)[0])

    def test_stty_flags(self):
        self.assertTrue(rbe.stty_flags_ok("lflags: icanon isig iexten echo echoe -echok")[0])
        ok, missing = rbe.stty_flags_ok("lflags: -icanon isig iexten -echo")
        self.assertFalse(ok)
        self.assertEqual(missing, ["icanon", "echo"])

    @unittest.skipIf(shutil.which("tmux") is None, "tmux not installed")
    def test_tty_probe_sigterm_fixture_and_fix(self):
        case = next(c for c in rbe.load_cases(CASES) if c["id"] == "sigterm-restore")
        a = next(x for x in case["assertions"] if x["id"] == "sigterm-clean-143")
        wd = self.tmp / "w"
        wd.mkdir()
        rbe.write_fixtures(wd, case["fixtures"])
        ok, d = rbe.run_tty_probe(a, wd, self.env)
        self.assertFalse(ok, d)                         # the shipped fixture leaves the terminal raw
        self.assertIn("echo", d)
        self.assertIn("alternate screen", d)
        (wd / "watch.py").write_text(_fixed_watch((wd / "watch.py").read_text()))
        ok, d = rbe.run_tty_probe(a, wd, self.env)
        self.assertTrue(ok, d)
        self.assertIn("exit 143", d)
        self.assertEqual(list((self.tmp / "t").glob("tmux-*/*")), [])   # no server left behind

    @unittest.skipIf(shutil.which("tmux") is None, "tmux not installed")
    def test_tty_probe_picker_contract(self):
        wd = self.tmp / "w"
        wd.mkdir()
        (wd / "pick.py").write_text(
            "import os, sys, termios, tty\n"
            "items = ['alpha', 'beta']\n"
            "tty_fd = os.open('/dev/tty', os.O_RDWR)\n"
            "old = termios.tcgetattr(tty_fd)\n"
            "tty.setcbreak(tty_fd)\n"
            "try:\n"
            "    os.write(tty_fd, b'> alpha\\r\\n  beta\\r\\n')\n"
            "    sel = 0\n"
            "    while True:\n"
            "        ch = os.read(tty_fd, 3)\n"
            "        if ch == b'\\x1b[B': sel = 1\n"
            "        elif ch in (b'\\r', b'\\n'): break\n"
            "        elif ch == b'\\x1b': sys.exit(130)\n"
            "finally:\n"
            "    termios.tcsetattr(tty_fd, termios.TCSADRAIN, old)\n"
            "print(items[sel])\n")
        a = {"cmd": "python3 pick.py > choice.txt", "ready": "alpha", "actions": [{"keys": "Down"}, {"keys": "Enter"}],
             "expect_status": [0], "stty_restored": True, "alt_screen_during": False,
             "files": [{"path": "choice.txt", "regex": "\\Abeta\\n?\\Z"}]}
        ok, d = rbe.run_tty_probe(a, wd, self.env)
        self.assertTrue(ok, d)
        ok, d = rbe.run_tty_probe(dict(a, actions=[{"keys": "Escape"}], expect_status=[130],
                                       files=[{"path": "choice.txt", "regex": "\\A\\Z"}]), wd, self.env)
        self.assertTrue(ok, d)
        ok, d = rbe.run_tty_probe(dict(a, ready="never-shown", ready_timeout=1), wd, self.env)
        self.assertFalse(ok)
        self.assertIn("never matched", d)

    def test_executed_in_copy_leaves_source_untouched(self):
        src = self.tmp / "files"
        src.mkdir()
        (src / "a.txt").write_text("x")
        case = {"assertions": [{"id": "w", "type": "exec", "cmd": "echo y > made.txt && test -f a.txt"}]}
        res = rbe.executed_in_copy(case, src)
        self.assertTrue(res[0]["passed"], res)
        self.assertEqual(res[0]["kind"], "executed")
        self.assertFalse((src / "made.txt").exists())


@unittest.skipIf(rbe is None, "evals/ not present (installed copy)")
class Vision(unittest.TestCase):
    def test_rubric_and_parsing(self):
        txt = rbe.rubric_text()
        self.assertIn("C1", txt)
        self.assertIn("C8", txt)
        names = ["frame1-caps.png", "frame1-16.png"]
        reply = '```json\n{"frames": [{"image": "./frame1-caps.png", "scores": {"C1": 2, "C2": 2, "C3": 1, "C4": 2, ' \
                '"C5": 2, "C6": 1, "C7": 2, "C8": 1}}, {"image": "frame1-16.png", "scores": {"C1": 2, "C2": 2, ' \
                '"C3": 2, "C4": 2, "C5": 0, "C6": 2, "C7": 2, "C8": 2}}, {"image": "x.png", "scores": {}}]}\n```'
        sc = rbe.parse_vision_reply(reply, names)
        self.assertEqual(set(sc), set(names))
        self.assertEqual(rbe.rubric_verdict(sc["frame1-caps.png"]), (True, 13))
        self.assertEqual(rbe.rubric_verdict(sc["frame1-16.png"]), (False, 14))   # a 0 fails the bar
        self.assertEqual(rbe.parse_vision_reply("garbage", names), {})

    def test_pick_frames_and_render(self):
        paths = ["d/a--normal--80x24.mock", "d/a--normal--120x30.mock", "d/a--error--120x30.mock", "d/b--normal--60x18.mock"]
        self.assertEqual(rbe.pick_frames(paths, {}), ["d/a--normal--120x30.mock"])
        self.assertEqual(rbe.pick_frames(paths, {"max_frames": 2})[1], "d/a--normal--80x24.mock")
        self.assertEqual(rbe.pick_frames(["x.mock"], {}), ["x.mock"])
        with tempfile.TemporaryDirectory() as tmp:
            png = Path(tmp) / "f.png"
            err = rbe.render_png(SKILL / "assets" / "demo" / "fleet--normal--80x24.mock", png, "16")
            self.assertIsNone(err)
            self.assertEqual(png.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
            bad = Path(tmp) / "bad.mock"
            bad.write_text("not a mock")
            self.assertIsNotNone(rbe.render_png(bad, Path(tmp) / "b.png", None))

    def test_vision_needs_claude_and_missing_frames_fail(self):
        with self.assertRaises(ValueError):
            rbe.vision_command("z-ai/glm-5.3-flash", Path("/p/prompt.txt"))
        self.assertEqual(rbe.catalog().vision_judge, "sonnet")
        self.assertEqual(rbe.catalog().judge, "haiku")
        inv = rbe.vision_command("haiku", Path("/p/prompt.txt"))
        self.assertIn("Read", inv.argv)
        self.assertEqual(inv.stdin, Path("/p/prompt.txt"))
        self.assertTrue(inv.env["CLAUDE_CONFIG_DIR"].endswith(".claude-eval"))
        case = {"assertions": [{"id": "v", "type": "vision_rubric", "glob": "**/*.mock", "neutral": False}]}
        rec = rbe.run_vision(case, {"workdir": Path("."), "files": []}, "haiku", 10)
        self.assertEqual(rec["results"][0]["passed"], False)
        self.assertEqual(rec["cost_usd"], 0.0)          # no frame -> no model call


@unittest.skipIf(rbe is None, "evals/ not present (installed copy)")
class RunsAndSummary(unittest.TestCase):
    def args(self, **kw):
        base = dict(no_judge=True, judge="haiku", vision_judge="haiku", judge_timeout=10, timeout=10,
                    keep_workdirs=False, no_exec=False, rejudge=False)
        base.update(kw)
        return argparse.Namespace(**base)

    def test_requires_skips_without_calling_the_agent(self):
        case = {"id": "needs-x", "prompt": "p", "area": "build", "requires": [{"cmd": "exit 1", "why": "x missing"}],
                "assertions": [{"id": "a", "type": "no_new_files"}]}
        with tempfile.TemporaryDirectory() as tmp:
            budget = rbe.Budget(1.0)
            rec = rbe.run_one(case, "z-ai/glm-5.3-flash", "low", "skill", 1, self.args(), budget, Path(tmp))
            self.assertIn("x missing", rec["skipped"])
            self.assertIsNone(rec["score"])
            self.assertEqual(len(rec["run_key"]), 64)
            self.assertEqual(rec["identity"]["case_id"], "needs-x")
            self.assertEqual(rec["identity"]["skill_hash"], rbe.tree_hash(SKILL))
            self.assertEqual(budget.spent, 0.0)
            self.assertTrue((Path(tmp) / f"{rec['run_id']}.json").exists())

    def test_summary_areas_and_skipped(self):
        cases = [{"id": "c1", "area": "shell", "assertions": [{"id": "a", "type": "no_new_files"}]},
                 {"id": "c2", "area": "build", "assertions": [{"id": "a", "type": "no_new_files"}]}]
        sc = lambda ok: rbe.score([{"passed": ok, "neutral": True}])  # noqa: E731
        runs = [{"run_id": "c1-s", "case": "c1", "model": "opus", "arm": "skill", "score": sc(True),
                 "assertions": [{"id": "a", "passed": True}], "cost_usd": 0.1, "cost_basis": "api-equivalent"},
                {"run_id": "c1-b", "case": "c1", "model": "opus", "arm": "baseline", "score": sc(False),
                 "assertions": [{"id": "a", "passed": False}], "cost_usd": 0.1, "cost_basis": "api-equivalent"},
                {"run_id": "c2-s", "case": "c2", "model": "opus", "arm": "skill", "skipped": "no textual",
                 "score": None, "assertions": []}]
        md, data = rbe.summarize(runs, cases)
        self.assertIn("## Per skill area", md)
        self.assertIn("| shell | 1 | opus | 100% | 0% | +100 |", md)
        self.assertIn("## Skipped runs", md)
        self.assertIn("c2-s: no textual", md)
        self.assertEqual(data["skipped"], 1)
        self.assertEqual(data["areas"]["build|opus"]["skill"]["skipped"], 1)

    def test_regrade_reads_gz_events_and_reruns_executed(self):
        case = {"id": "c", "prompt": "p", "area": "shell", "fixtures": [],
                "assertions": [{"id": "t", "type": "transcript_regex", "pattern": "capture-pane"},
                               {"id": "e", "type": "exec", "cmd": "test -f out.txt"}]}
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            (runs / "c__opus__skill__r1.files").mkdir(parents=True)
            (runs / "c__opus__skill__r1.files" / "out.txt").write_text("x")
            with gzip.open(runs / "c__opus__skill__r1.events.jsonl.gz", "wt") as fh:
                fh.write(json.dumps({"type": "assistant", "message": {"content": [
                    {"type": "tool_use", "name": "Bash", "input": {"command": "tmux -L p capture-pane -p"}}]}}) + "\n")
            (runs / "c__opus__skill__r1.json").write_text(json.dumps(
                {"run_id": "c__opus__skill__r1", "case": "c", "model": "opus", "adapter": "claude", "arm": "skill",
                 "final_answer": "", "assertions": []}))
            out = rbe.regrade(Path(tmp), [case], self.args())
            res = {a["id"]: a["passed"] for a in out[0]["assertions"]}
            self.assertEqual(res, {"t": True, "e": True})
            self.assertEqual(list((runs / "c__opus__skill__r1.files").iterdir())[0].name, "out.txt")


@unittest.skipIf(rbe is None, "evals/ not present (installed copy)")
class BlockedBy(unittest.TestCase):
    CASE = {"id": "c", "assertions": [{"id": "kept", "type": "fixture_unchanged", "path": "in.txt"},
                                      {"id": "probe", "type": "tty_probe", "cmd": "x", "blocked_by": ["kept"]}]}

    def test_failed_prerequisite_blocks_but_keeps_what_was_observed(self):
        out = rbe.apply_blocked(self.CASE, [{"id": "kept", "passed": False}, {"id": "probe", "passed": True, "detail": "ok"}])
        probe = out[1]
        self.assertIs(probe["passed"], False)
        self.assertTrue(probe["detail"].startswith("blocked: kept"))
        self.assertEqual((probe["observed_passed"], probe["observed_detail"]), (True, "ok"))

    def test_passing_prerequisite_changes_nothing(self):
        a = [{"id": "kept", "passed": True}, {"id": "probe", "passed": False, "detail": "exit 1"}]
        self.assertEqual(rbe.apply_blocked(self.CASE, a), a)

    def test_regrade_lifts_a_block_whose_prerequisite_now_passes(self):
        blocked = rbe.apply_blocked(self.CASE, [{"id": "kept", "passed": False}, {"id": "probe", "passed": True, "detail": "ok"}])
        again = rbe.reapply_blocked(self.CASE, [{"id": "kept", "passed": True}, blocked[1]])
        self.assertEqual(again[1], {"id": "probe", "passed": True, "detail": "ok"})

    def test_repeated_regrades_are_stable(self):
        a = [{"id": "kept", "passed": False}, {"id": "probe", "passed": False, "detail": "exit 1"}]
        once = rbe.apply_blocked(self.CASE, a)
        twice = rbe.reapply_blocked(self.CASE, rbe.reapply_blocked(self.CASE, once))
        self.assertEqual(once, twice)

    def test_fresh_execution_replaces_the_old_observation(self):
        fresh = rbe.reapply_blocked(self.CASE, [{"id": "kept", "passed": False}, {"id": "probe", "passed": False, "detail": "new"}])
        self.assertEqual((fresh[1]["observed_passed"], fresh[1]["observed_detail"]), (False, "new"))

    def test_dependency_chains_are_rejected(self):
        chain = {"id": "c", "prompt": "p", "assertions": [
            {"id": "a", "type": "judge", "question": "q?"},
            {"id": "b", "type": "judge", "question": "q?", "blocked_by": ["a"]},
            {"id": "c", "type": "judge", "question": "q?", "blocked_by": ["b"]}]}
        self.assertTrue(any("one level only" in e for e in rbe.validate_cases({"cases": [chain]})))

    def test_file_regex_can_ignore_ansi(self):
        wd = Path(tempfile.mkdtemp())
        (wd / "audit").mkdir()
        (wd / "audit" / "s.txt").write_text("\x1b[4mNAME\x1b[0m  \x1b[4mSTATUS\x1b[0m\n")
        a = {"type": "file_regex", "glob": "audit/**/*.txt", "pattern": r"(?m)^NAME[ \t]+STATUS", "mode": "any"}
        ctx = {"workdir": wd, "files": [{"path": "audit/s.txt", "status": "new"}], "answer": "", "transcript": ""}
        self.assertFalse(rbe.check_program(a, ctx)[0])
        self.assertTrue(rbe.check_program({**a, "strip_ansi": True}, ctx)[0])

    def test_unknown_dependency_is_a_case_error(self):
        bad = {"id": "c", "prompt": "p", "assertions": [{"id": "p1", "type": "judge", "question": "q?", "blocked_by": ["nope"]}]}
        self.assertTrue(any("blocked_by" in e for e in rbe.validate_cases({"cases": [bad]})))


@unittest.skipIf(rbe is None, "evals/ not present (installed copy)")
class Contamination(unittest.TestCase):
    ROOT = "/scratch/T/evalrun-abc123"

    def hits(self, text):
        with mock.patch.object(rbe, "extra_deny_paths", return_value=[Path.home() / ".claude" / "skills"]):
            return rbe.contamination(text, rbe.inside_root(Path(self.ROOT)), "tui-design")

    def test_other_copy_of_the_skill_and_old_results(self):
        t = ('read {"path": "/srv/u/Dev/scratch/tui-design/skill/tui-design/SKILL.md"}\n'
             'bash {"command": "cat /srv/u/old/tui-design-release/evals/runs/x.mock"}')
        self.assertEqual(len(self.hits(t)), 2)

    def test_own_run_and_relative_paths_are_fine(self):
        t = (f'read {{"path": "{self.ROOT}/project/.agents/skills/tui-design/SKILL.md"}}\n'
             'bash {"command": "ls .agents/skills/tui-design/references; S=\\"$(dirname \\"$0\\")/../.claude/skills/tui-design\\""}\n'
             'read {"path": "skill://tui-design"}')
        self.assertEqual(self.hits(t), [])

    def test_denied_dirs_and_disk_search(self):
        t = 'bash {"command": "ls ~/.claude/skills; mdfind -name logview | head"}'
        self.assertEqual(self.hits(t), ["mdfind", "~/.claude/skills"])

    def test_search_words_in_prose_are_not_commands(self):
        t = 'todo {"items": ["Read layout.md and locate the entry point"]}'
        self.assertEqual(self.hits(t), [])

    def test_sandbox_section(self):
        doc = tomllib.loads((REPO / "evals" / "models.toml").read_text())
        doc["sandbox"] = {"deny_read": "~/x"}
        with self.assertRaises(rbe.ConfigError):
            rbe.parse_catalog(doc, None)
        doc["sandbox"] = {"deny_read": ["~/x"], "deny_spotlight": False}
        self.assertEqual(rbe.parse_catalog(doc, None).sandbox["deny_read"], ["~/x"])
        self.assertIn("com.apple.metadata.mds", rbe.confine_profile(Path("/tmp/r")))


@unittest.skipIf(rbe is None, "evals/ not present (installed copy)")
class Identity(unittest.TestCase):
    CASE = {"id": "c", "prompt": "p", "area": "shell", "assertions": [{"id": "a", "type": "no_new_files"}]}

    def ident(self, case=None, **kw):
        base = dict(model="opus", effort="medium", arm="skill", rep=1, judge="haiku", vision_judge="haiku",
                    skill_hash="s1", adapter_ver="2.0")
        base.update(kw)
        return rbe.run_identity(case or self.CASE, base["model"], base["effort"], base["arm"], base["rep"],
                                base["judge"], base["vision_judge"], base["skill_hash"], base["adapter_ver"])

    def test_hash_stable_across_key_order(self):
        reordered = {"assertions": [{"type": "no_new_files", "id": "a"}], "area": "shell", "prompt": "p", "id": "c"}
        self.assertEqual(rbe.case_hash(self.CASE), rbe.case_hash(reordered))
        self.assertEqual(self.ident()["run_key"], self.ident(case=reordered)["run_key"])
        self.assertEqual(rbe.canonical({"b": 1, "a": [1, {"d": 2, "c": 3}]}), '{"a":[1,{"c":3,"d":2}],"b":1}')

    def test_keys_change_with_inputs(self):
        k0 = self.ident()
        for change in (dict(case=dict(self.CASE, prompt="other")), dict(model="sonnet"), dict(effort="high"),
                       dict(skill_hash="s2"), dict(judge="sonnet"), dict(adapter_ver="2.1")):
            k = self.ident(**change)
            self.assertNotEqual(k["run_key"], k0["run_key"], change)
        self.assertNotEqual(self.ident(rep=2)["run_key"], k0["run_key"])
        # experiment_key ignores case and rep, not model/config/skill/arm
        self.assertEqual(self.ident(rep=2)["experiment_key"], k0["experiment_key"])
        self.assertEqual(self.ident(case=dict(self.CASE, id="other"))["experiment_key"], k0["experiment_key"])
        self.assertNotEqual(self.ident(skill_hash="s2")["experiment_key"], k0["experiment_key"])
        self.assertNotEqual(self.ident(arm="baseline")["experiment_key"], k0["experiment_key"])
        base = self.ident(arm="baseline")["identity"]
        self.assertIsNone(base["skill_hash"])            # baseline never carries a skill hash
        self.assertEqual(k0["identity"]["provider"], "anthropic")

    def test_case_hash_follows_fixture_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = rbe.FIXTURES_DIR
            try:
                rbe.FIXTURES_DIR = Path(tmp)
                (Path(tmp) / "f.txt").write_text("one")
                case = dict(self.CASE, fixtures=[{"path": "f.txt", "src": "f.txt"}])
                h1 = rbe.case_hash(case)
                (Path(tmp) / "f.txt").write_text("two")
                self.assertNotEqual(rbe.case_hash(case), h1)
            finally:
                rbe.FIXTURES_DIR = old

    def test_tree_hash_matches_installed_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = rbe.install_skill(Path(tmp), "omp")
            self.assertEqual(rbe.tree_hash(dest), rbe.tree_hash(SKILL))
            (dest / "SKILL.md").write_text("changed")
            self.assertNotEqual(rbe.tree_hash(dest), rbe.tree_hash(SKILL))

    def test_dataset_entries(self):
        cases = rbe.load_cases(CASES)
        with tempfile.TemporaryDirectory() as tmp:
            items = json.loads(rbe.write_dataset(Path(tmp), cases).read_text())["items"]
        self.assertEqual([i["case_id"] for i in items], [c["id"] for c in cases])
        shot = next(i for i in items if i["case_id"] == "screenshot-audit")
        self.assertEqual(shot["fixtures"][0]["src"], "screenshot-audit/screenshot.png")
        self.assertEqual(len(shot["fixtures"][0]["sha256"]), 64)
        self.assertTrue(any("question" in a for a in shot["assertions"]))
        self.assertIn("audit", shot["tags"])


@unittest.skipIf(rbe is None, "evals/ not present (installed copy)")
class Fixtures(unittest.TestCase):
    def test_generated_fixtures_are_current(self):
        p = subprocess.run([sys.executable, str(rbe.FIXTURES_DIR / "gen_fixtures.py"), "--check"],
                           capture_output=True, text=True, timeout=300)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_screenshot_ground_truth(self):
        shot = rbe.FIXTURES_DIR / "screenshot-audit"
        self.assertEqual((shot / "screenshot.png").read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        lint = rbe.lint_mock(shot / "backupd--normal--80x24.mock")
        self.assertEqual(lint["errors"], 0)
        self.assertIn("CR1", lint["craft"])              # the deliberate flaws are visible to the lint
        pal = json.loads((shot / "palette.json").read_text())["colors"]
        self.assertTrue(8 <= len(pal) <= 16)
        self.assertTrue(all(len(c) == 7 and c.startswith("#") for c in pal))

    def test_binary_fixture_copied_byte_exact(self):
        case = next(c for c in rbe.load_cases(CASES) if c["id"] == "screenshot-audit")
        with tempfile.TemporaryDirectory() as tmp:
            hashes = rbe.write_fixtures(Path(tmp), case["fixtures"])
            png = Path(tmp) / "screenshot.png"
            self.assertEqual(png.read_bytes(), (rbe.FIXTURES_DIR / "screenshot-audit" / "screenshot.png").read_bytes())
            st = {f["path"]: f["status"] for f in rbe.classify_files(Path(tmp), hashes)}
            self.assertEqual(st, {"screenshot.png": "fixture"})
            self.assertEqual(rbe.fixture_text(case["fixtures"][0]), "")   # binary: no hex scan


if __name__ == "__main__":
    unittest.main()
