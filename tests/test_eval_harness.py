"""evals/run_behavior_evals.py, the extensible parts: models.toml (presets, ID@EFFORT, validation, prices), the
adapter registry and the generic `command` adapter (a fake CLI, no model), prompts through a file never argv,
serial cases under --jobs, cases from evals/cases/ and --validate-cases, --resume adding repetitions, the spread
section, and the secret handling (allow-listed environment, no secret in argv, redaction, leak scan, campaign
stop, read confinement). No agent or model is called.

Skipped when evals/ is absent (the copy of the skill an agent works with has no evals/).
"""

import argparse
import gzip
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills" / "tui-design"
EVALS = REPO / "evals"
RUNNER = EVALS / "run_behavior_evals.py"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rbe = _load("run_behavior_evals_harness", RUNNER) if RUNNER.exists() else None
ex = _load("export_results_harness", EVALS / "export_results.py") if RUNNER.exists() else None

PROMPT = "Redesign the backup monitor so the queue column fits; marker ZEBRA-PROMPT-7731."
FAKE_SECRET = "sk-fake-test-0123456789abcdef"

ENV_DUMP_CLI = r'''
import json, os, sys
prompt = open(sys.argv[1]).read() if len(sys.argv) > 1 and sys.argv[1] != "-" else sys.stdin.read()
print(json.dumps({"env": dict(os.environ), "prompt": prompt, "argv": sys.argv}))
'''

ECHO_PROMPT_CLI = r'''
import json, os, sys
prompt = sys.stdin.read()
open(os.path.join(os.environ.get("WORKDIR", "."), "notes.md"), "w").write("notes: " + prompt)
open(sys.argv[1], "w").write("ANSWER " + prompt)
json.dump({"input": 1000, "cached": 0, "output": 50, "reasoning": 0, "cost_usd": 0.0012}, open(sys.argv[2], "w"))
'''


def models_doc(extra_models=(), presets=None, judges=None):
    """A minimal models.toml as a dict: two real-adapter models plus `extra_models`."""
    return {"defaults": {"models": "pair"},
            "judges": judges or {"text": "haiku", "vision": "haiku"},
            "presets": presets or {"pair": ["haiku", "glm@low"]},
            "models": [{"id": "haiku", "adapter": "claude", "effort": "low", "cost_basis": "api-equivalent",
                        "price": {"input": 1.0, "cached_input": 0.1, "output": 5.0}},
                       {"id": "glm", "adapter": "omp", "model": "z-ai/glm-5.3", "effort": "high",
                        "cost_basis": "billed", "price": {"input": 1.4, "output": 4.4}},
                       *extra_models]}


def cli_model(mid, script: Path, **kw):
    m = {"id": mid, "adapter": "command", "effort": "none", "command": [sys.executable, str(script), "{prompt_file}"]}
    m.update(kw)
    return m


def run_args(**kw):
    base = dict(no_judge=True, judge="haiku", vision_judge="haiku", judge_timeout=10, timeout=60,
                keep_workdirs=False, no_exec=True, rejudge=False)
    base.update(kw)
    return argparse.Namespace(**base)


class CatalogCase(unittest.TestCase):
    """Restores the shipped catalog and redactor after each test."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.addCleanup(rbe.set_catalog, None)
        self.addCleanup(rbe.set_redactor, None)
        rbe.set_redactor(rbe.Redactor({}))

    def use(self, doc):
        cat = rbe.parse_catalog(doc)
        rbe.set_catalog(cat)
        return cat

    def script(self, name, body):
        p = self.tmp / name
        p.write_text(body)
        return p


@unittest.skipIf(rbe is None, "evals/ not present (installed copy)")
class ModelsFile(CatalogCase):
    def test_shipped_file_keeps_run1_defaults(self):
        cat = rbe.load_catalog()
        self.assertEqual(cat.resolve(cat.default_models), [("z-ai/glm-5.3", "high"), ("qwen/qwen3.8-max-0902", "medium"),
                                                           ("opus", "medium"), ("gpt-6.1-sol", "medium")])
        self.assertEqual(cat.resolve("smoke"), [("z-ai/glm-5.3-flash", "low")])
        self.assertEqual((cat.judge, cat.vision_judge), ("haiku", "sonnet"))
        self.assertEqual(cat.get("gpt-6.1-sol").price, {"input": 2.0, "cached": 0.1, "cache_write": None, "output": 10.0})
        self.assertEqual(cat.get("opus").cost_basis, "api-equivalent")
        self.assertEqual({rbe.adapter_for(m) for m in ("z-ai/glm-5.3", "opus", "gpt-6.1-sol", "example-echo")},
                         {"omp", "claude", "codex", "command"})

    def test_presets_ids_and_effort_overrides(self):
        cat = self.use(models_doc())
        self.assertEqual(cat.resolve("pair"), [("haiku", "low"), ("glm", "low")])
        self.assertEqual(cat.resolve("pair@medium"), [("haiku", "medium"), ("glm", "medium")])
        self.assertEqual(cat.resolve("glm,haiku@high"), [("glm", "high"), ("haiku", "high")])
        self.assertEqual(cat.resolve("glm,glm"), [("glm", "high")])
        self.assertEqual(rbe.parse_model_spec("glm"), ("glm", "high"))
        self.assertEqual(rbe.parse_model_spec("glm@low"), ("glm", "low"))
        with self.assertRaises(rbe.ConfigError) as e:
            cat.resolve("glm,nope")
        self.assertIn("unknown model 'nope'", str(e.exception))
        self.assertIn("Known models: haiku, glm", str(e.exception))
        self.assertIn("Presets: pair", str(e.exception))
        with self.assertRaises(rbe.ConfigError):
            cat.resolve("glm@low,glm@high")              # run ids carry no effort: refuse the collision

    def test_validation_lists_every_problem(self):
        doc = models_doc(extra_models=[
            {"id": "x1", "adapter": "nope"},
            {"id": "x2", "adapter": "omp", "colour": "red"},
            {"id": "x3", "adapter": "codex", "cost_basis": "equivalent"},
            {"id": "x4", "adapter": "omp", "price": {"input": 1}},
            {"id": "x5", "adapter": "command", "command": ["agent", "--go"]},
            {"id": "x6", "adapter": "command", "command": ["agent", "{prompt_file}", "{bogus}"]},
            {"id": "glm", "adapter": "omp"}],
            presets={"pair": ["haiku", "ghost"]}, judges={"text": "haiku", "vision": "glm"})
        doc["adapters"] = {"claude": {"colour": 1}, "omp": {"pass_env": ["MY_API_KEY"]}, "ghost": {}}
        with self.assertRaises(rbe.ConfigError) as e:
            rbe.parse_catalog(doc)
        msg = str(e.exception)
        for needle in ("x1: adapter must be one of", "x2: unknown key(s) ['colour']", "x3: cost_basis 'equivalent' needs a price",
                       "x4: price needs numeric input and output", "x5: prompt_via 'arg' needs {prompt_file}",
                       "x6: unknown placeholder(s) ['bogus']", "glm: duplicate id", "unknown model 'ghost'",
                       "[judges] vision: adapter omp cannot run this judge", "[adapters.claude]: known keys",
                       "[adapters.omp]: pass_env must not name a secret", "[adapters.ghost]: no such adapter"):
            self.assertIn(needle, msg)

    def test_toml_file_and_list_models(self):
        p = self.tmp / "m.toml"
        p.write_text('[defaults]\nmodels = "one"\n[judges]\ntext = "haiku"\nvision = "haiku"\n[presets]\none = ["haiku"]\n'
                     '[[models]]\nid = "haiku"\nadapter = "claude"\neffort = "low"\nlabel = "Haiku"\n'
                     'price = { input = 1.0, output = 5.0 }\n')
        cat = rbe.load_catalog(p)
        self.assertEqual(cat.resolve(cat.default_models), [("haiku", "low")])
        txt = rbe.list_models(cat)
        self.assertIn("haiku", txt)
        self.assertIn("one          haiku   (default)", txt)
        p.write_text("[[models]\n")
        with self.assertRaises(rbe.ConfigError):
            rbe.load_catalog(p)

    def test_price_cache_feeds_the_estimator_only(self):
        cat = self.use(models_doc())
        lines = rbe.refresh_prices(cat, self.tmp / "prices.json", table={
            "z-ai/glm-5.3": {"input": 2.8, "cached": 0.5, "cache_write": None, "output": 8.8}})
        self.assertEqual(lines, [])                      # no openrouter_id in this catalog: nothing to fetch
        cat.models["glm"].openrouter_id = "z-ai/glm-5.3"
        lines = rbe.refresh_prices(cat, self.tmp / "prices.json", table={
            "z-ai/glm-5.3": {"input": 2.8, "cached": 0.5, "cache_write": None, "output": 8.8}})
        self.assertIn("glm: input 2.8", lines[0])
        rbe.load_price_cache(cat, self.tmp / "prices.json")
        self.assertEqual(rbe.estimate_cost("glm", 1_000_000, 0.0, 0)[1], 2.8)
        self.assertEqual(rbe.estimate_cost(cat.get("glm").price, 1_000_000, 0.0, 0)[1], 1.4)
        self.assertEqual(cat.price("glm", use_cache=False)[0]["input"], 1.4)

    def test_fetch_prices_parses_openrouter_without_a_key(self):
        payload = json.dumps({"data": [{"id": "a/b", "pricing": {"prompt": "0.000002", "completion": "0.00001",
                                                                 "input_cache_read": "0.0000002"}},
                                       {"id": "free/x", "pricing": {"prompt": "", "completion": None}}]}).encode()
        seen = {}

        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def fake_urlopen(req, timeout=None):
            seen["headers"] = dict(req.header_items())
            return Resp(payload)
        with mock.patch.object(rbe.urllib.request, "urlopen", fake_urlopen):
            table = rbe.fetch_openrouter_prices()
        self.assertEqual(table, {"a/b": {"input": 2.0, "cached": 0.2, "cache_write": None, "output": 10.0}})
        self.assertFalse(any(k.lower() == "authorization" for k in seen["headers"]))

    def test_main_list_models_and_unknown_model(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(rbe.main(["--list-models"]), 0)
        self.assertIn("frontier4", out.getvalue())
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(rbe.main(["--models", "llama-9", "--dry-run"]), 2)
        self.assertIn("Known models:", err.getvalue())

    def test_default_dry_run_matrix_is_run1(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(rbe.main(["--list-jobs"]), 0)
        lines = out.getvalue().splitlines()
        self.assertEqual(lines[-1], "192 jobs")
        self.assertEqual(lines[0], "plugin-caps-from-code__z-ai-glm-5.3__skill__r1 high")


@unittest.skipIf(rbe is None, "evals/ not present (installed copy)")
class PromptViaFile(CatalogCase):
    def test_no_adapter_puts_the_prompt_in_argv(self):
        self.use(models_doc(extra_models=[
            cli_model("cli-arg", Path("/x/agent.py")),
            {"id": "cli-stdin", "adapter": "command", "command": ["agent", "--run"], "prompt_via": "stdin"},
            {"id": "gpt", "adapter": "codex", "price": {"input": 2.0, "output": 10.0}}]))
        pf = self.tmp / "prompt.txt"
        pf.write_text(PROMPT)
        wd, home = self.tmp / "w", self.tmp / "h"
        for mid, adapter, via_stdin in (("glm", "omp", True), ("haiku", "claude", True), ("gpt", "codex", True),
                                        ("cli-stdin", "command", True), ("cli-arg", "command", False)):
            for arm in ("skill", "baseline"):
                inv = rbe.build_command(adapter, mid, "low", arm, pf, wd, home, ["Bash(tmux:*)"], self.tmp)
                joined = " ".join(inv.argv)
                self.assertNotIn("ZEBRA-PROMPT", joined, mid)
                self.assertNotIn("Redesign", joined, mid)
                self.assertEqual(inv.stdin, pf if via_stdin else None, mid)
                if not via_stdin:
                    self.assertIn(str(pf), inv.argv)
        for judge, vision in (("haiku", False), ("haiku", True), ("glm", False)):
            inv, _ = rbe.judge_command(judge, pf, vision)
            self.assertNotIn("ZEBRA-PROMPT", " ".join(inv.argv))
            self.assertEqual(inv.stdin, pf)

    def test_omp_reads_stdin_and_points_the_skill_arm_at_the_skill(self):
        self.use(models_doc())
        pf = self.tmp / "prompt.txt"
        pf.write_text(PROMPT)
        inv = rbe.build_command("omp", "glm", "high", "skill", pf, self.tmp / "w", self.tmp / "h", None, self.tmp)
        i = inv.argv.index("--append-system-prompt")
        hint = Path(inv.argv[i + 1]).read_text()
        self.assertIn(str(self.tmp / "w" / ".agents" / "skills" / rbe.SKILL_NAME), hint)
        base = rbe.build_command("omp", "glm", "high", "baseline", pf, self.tmp / "w", self.tmp / "h", None, self.tmp)
        self.assertNotIn("--append-system-prompt", base.argv)

    def test_run_one_feeds_the_prompt_file(self):
        cli = self.script("dump.py", ENV_DUMP_CLI)
        self.use(models_doc(extra_models=[cli_model("dump", cli)]))
        case = {"id": "c", "prompt": PROMPT, "area": "build", "assertions": [{"id": "a", "type": "no_new_files"}]}
        rec = rbe.run_one(case, "dump", "none", "baseline", 1, run_args(), rbe.Budget(None), self.tmp)
        got = json.loads(rec["final_answer"])
        self.assertEqual(got["prompt"], PROMPT)
        self.assertNotIn("ZEBRA", " ".join(got["argv"]))
        self.assertNotIn("ZEBRA", rec["command"])
        self.assertEqual(rec["prompt_via"], "file argument")


@unittest.skipIf(rbe is None, "evals/ not present (installed copy)")
class CommandAdapter(CatalogCase):
    def test_shipped_example_runs_end_to_end(self):
        case = {"id": "c", "prompt": "Sketch the queue screen at 80x24.", "area": "frames",
                "assertions": [{"id": "wrote", "type": "file_glob", "glob": "*.md"},
                               {"id": "said", "type": "answer_regex", "pattern": "ECHO\\[echo-1\\]"}]}
        for arm in ("skill", "baseline"):
            rec = rbe.run_one(case, "example-echo", "none", arm, 1, run_args(), rbe.Budget(None), self.tmp)
            self.assertIsNone(rec["error"], rec.get("stderr_tail"))
            self.assertEqual(rec["score"]["passed"], 2)
            self.assertEqual(rec["tokens"]["output"], 12)
            self.assertEqual(rec["cost_basis"], "unknown")
            self.assertEqual(rec["identity"]["adapter"], "command")
            self.assertEqual(rec["identity"]["adapter_version"], "echo-agent 1.0")
            self.assertTrue((self.tmp / f"{rec['run_id']}.files" / "echo-notes.md").is_file())
            self.assertEqual("Skill: True." in rec["final_answer"], arm == "skill")

    def test_stdin_prompt_answer_file_and_reported_cost(self):
        cli = self.script("agent.py", ECHO_PROMPT_CLI)
        self.use(models_doc(extra_models=[{
            "id": "mine", "adapter": "command", "command": [sys.executable, str(cli), "{run_dir}/answer.md",
                                                            "{run_dir}/usage.json"],
            "prompt_via": "stdin", "answer": "{run_dir}/answer.md", "usage": "{run_dir}/usage.json",
            "env": {"WORKDIR": "{workdir}"}, "cost_basis": "billed"}]))
        case = {"id": "c", "prompt": PROMPT, "area": "build", "assertions": [{"id": "a", "type": "file_glob",
                                                                             "glob": "notes.md"}]}
        rec = rbe.run_one(case, "mine", "none", "baseline", 1, run_args(), rbe.Budget(None), self.tmp)
        self.assertEqual(rec["final_answer"], "ANSWER " + PROMPT)
        self.assertEqual((rec["cost_usd"], rec["cost_basis"]), (0.0012, "billed"))
        self.assertEqual(rec["score"]["passed"], 1)
        self.assertEqual(rec["prompt_via"], "stdin")

    def test_missing_answer_file_is_an_error_and_no_usage_is_unknown(self):
        cli = self.script("quiet.py", "import sys\n")
        self.use(models_doc(extra_models=[cli_model("quiet", cli, answer="{run_dir}/nope.md")]))
        case = {"id": "c", "prompt": "p", "area": "build", "assertions": [{"id": "a", "type": "no_new_files"}]}
        rec = rbe.run_one(case, "quiet", "none", "baseline", 1, run_args(), rbe.Budget(None), self.tmp)
        self.assertIn("answer file not written", rec["error"])
        self.assertIsNone(rec["tokens"])
        self.assertEqual(rec["cost_basis"], "unknown")

    def test_python_adapter_plugin_registers(self):
        d = self.tmp / "adapters"
        d.mkdir()
        (d / "mycli.py").write_text(
            "class MyCli(Adapter):\n"
            "    name, provider, executable = 'mycli', 'acme', 'mycli'\n"
            "    def command(self, spec, effort, arm, prompt_file, workdir, home, extra_tools=None, run_dir=None):\n"
            "        return Invocation(['mycli', '--model', spec.model], {}, prompt_file)\n"
            "    def parse(self, lines, spec=None, place=None):\n"
            "        return {'final_answer': ''.join(lines), 'tool_calls': 0, 'tokens': empty_tokens(), 'cost_usd': 0.0,\n"
            "                'cost_basis': 'unknown', 'skill_loaded': None, 'error': None}\n"
            "register_adapter(MyCli())\n")
        old = rbe._PLUGINS_LOADED
        try:
            rbe._PLUGINS_LOADED = False
            self.assertEqual(rbe.load_adapter_plugins(d), ["mycli"])
            cat = self.use(models_doc(extra_models=[{"id": "m", "adapter": "mycli"}]))
            self.assertEqual(rbe.build_command("mycli", "m", "low", "skill", self.tmp / "p", self.tmp, self.tmp).argv,
                             ["mycli", "--model", "m"])
            self.assertEqual(cat.get("m").adapter, "mycli")
        finally:
            rbe.ADAPTERS.pop("mycli", None)
            rbe._PLUGINS_LOADED = old


@unittest.skipIf(rbe is None, "evals/ not present (installed copy)")
class Scheduling(unittest.TestCase):
    def test_serial_jobs_run_alone_under_jobs(self):
        active, peak, log = [0], {"serial": 0, "other": 0}, []
        lock = threading.Lock()

        def work(job):
            kind = "serial" if job[0].get("serial") else "other"
            with lock:
                active[0] += 1
                peak[kind] = max(peak[kind], active[0])
                log.append(job[0]["id"])
            time.sleep(0.05)
            with lock:
                active[0] -= 1
        jobs = [({"id": f"a{i}"},) for i in range(4)] + [({"id": f"s{i}", "serial": True},) for i in range(2)] + \
               [({"id": f"b{i}"},) for i in range(4)]
        rbe.run_jobs(jobs, 4, work)
        self.assertEqual(peak["serial"], 1)               # nothing else ran next to a serial job
        self.assertGreater(peak["other"], 1)              # ordinary jobs did run in parallel
        self.assertEqual(len(log), 10)
        self.assertLess(max(log.index(f"a{i}") for i in range(4)), log.index("s0"))
        self.assertLess(log.index("s1"), min(log.index(f"b{i}") for i in range(4)))

    def test_shipped_signal_cases_are_serial_and_hash_unchanged(self):
        cases = {c["id"]: c for c in rbe.load_cases()}
        self.assertTrue(cases["sigterm-restore"].get("serial"))
        c = dict(cases["sigterm-restore"])
        h = rbe.case_hash(c)
        c.pop("serial")
        self.assertEqual(rbe.case_hash(c), h)             # scheduling flags do not change a case's identity
        self.assertEqual(ex.case_hash(cases["sigterm-restore"]), h)

    def test_resume_with_more_reps_adds_only_new_reps(self):
        case = {"id": "c", "prompt": "p", "area": "build", "assertions": []}
        models = [("glm", "high")]
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp)
            for arm in ("skill", "baseline"):
                rid = rbe.run_id_for("c", "glm", arm, 1)
                (runs / f"{rid}.json").write_text(json.dumps({"run_id": rid, "error": None}))
            rid = rbe.run_id_for("c", "glm", "skill", 2)
            (runs / f"{rid}.json").write_text(json.dumps({"run_id": rid, "error": "timeout"}))
            kept, todo = rbe.resume_split(rbe.build_jobs([case], models, ["skill", "baseline"], 3), runs)
        self.assertEqual(len(kept), 2)
        self.assertEqual(sorted((j[3], j[4]) for j in todo),
                         [("baseline", 2), ("baseline", 3), ("skill", 2), ("skill", 3)])

    def test_summary_spread_across_reps(self):
        cases = [{"id": "c1", "area": "shell", "assertions": [{"id": "a", "type": "no_new_files"}]}]

        def run(arm, rep, rate):
            return {"run_id": f"c1-{arm}-{rep}", "case": "c1", "model": "opus", "arm": arm, "rep": rep,
                    "score": {"rate": rate, "neutral_rate": rate, "all_passed": rate == 1.0, "passed": 1, "graded": 1},
                    "assertions": [], "cost_usd": 0.1, "cost_basis": "api-equivalent"}
        runs = [run("skill", 1, 1.0), run("skill", 2, 0.5), run("skill", 3, 0.75), run("baseline", 1, 0.25)]
        md, data = rbe.summarize(runs, cases)
        self.assertIn("## Spread across repetitions", md)
        self.assertIn("| c1 | opus | 50%–100% (sd 25) | 25%–25% (sd –) | 3/1 |", md)
        self.assertAlmostEqual(data["cells"]["c1|opus"]["skill"]["rate_sd"], 0.25)
        md1, _ = rbe.summarize(runs[:1] + runs[3:], cases)
        self.assertNotIn("Spread across repetitions", md1)


@unittest.skipIf(rbe is None, "evals/ not present (installed copy)")
class CaseFiles(unittest.TestCase):
    CASE = {"id": "extra-1", "prompt": "Sketch the queue view.", "area": "frames",
            "assertions": [{"id": "a", "type": "no_new_files"}]}

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.main = self.tmp / "main.json"
        self.main.write_text(json.dumps({"banned_terms": ["forbiddenword"], "areas": ["custom"],
                                         "cases": [dict(self.CASE, id="main-1")]}))
        self.dir = self.tmp / "cases"
        self.dir.mkdir()

    def test_cases_dir_list_and_object_forms(self):
        (self.dir / "a.json").write_text(json.dumps([self.CASE]))
        (self.dir / "b.json").write_text(json.dumps({"cases": [dict(self.CASE, id="extra-2", area="custom")]}))
        cases = rbe.load_cases(self.main, cases_dir=self.dir)
        self.assertEqual([c["id"] for c in cases], ["main-1", "extra-1", "extra-2"])
        self.assertEqual(rbe.validate_case_files(rbe.case_files(self.main, self.dir)), [])

    def test_validation_errors_name_their_file(self):
        (self.dir / "bad.json").write_text(json.dumps([
            dict(self.CASE, id="main-1"),
            dict(self.CASE, id="x", assertions=[{"id": "a", "type": "telepathy"}]),
            dict(self.CASE, id="y", fixtures=[{"path": "s.png", "src": "no/such.png"}]),
            dict(self.CASE, id="z", prompt="the forbiddenword dashboard"),
            dict(self.CASE, id="w", serial="yes")]))
        errs = "\n".join(rbe.validate_case_files(rbe.case_files(self.main, self.dir)))
        for needle in ("main-1: duplicate id", "bad.json: x/a: unknown type 'telepathy'",
                       "bad.json: y: fixture src 'no/such.png' not found", "bad.json: z: neutral-domain rule",
                       "bad.json: w: serial must be true or false"):
            self.assertIn(needle, errs)
        out = io.StringIO()
        with redirect_stdout(out):
            code = rbe.main(["--validate-cases", "--cases-file", str(self.main), "--cases-dir", str(self.dir)])
        self.assertEqual(code, 1)
        self.assertIn("unknown type", out.getvalue())

    def test_shipped_cases_validate_with_the_neutral_rule(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(rbe.main(["--validate-cases"]), 0)
        self.assertIn("ok: 24 cases", out.getvalue())
        doc = json.loads((EVALS / "behavior-evals.json").read_text())
        banned = doc["banned_terms"]
        self.assertTrue(banned and all(isinstance(b, str) and b == b.lower() for b in banned), banned)
        for term in banned:     # every listed term is enforced on a case's text
            case = {"id": "n", "prompt": f"Design a screen about {term}", "area": "build",
                    "assertions": [{"id": "x", "type": "no_new_files"}]}
            errs = "\n".join(rbe.validate_cases({"cases": [case]}, banned=banned))
            self.assertIn("neutral-domain rule", errs, term)

    def test_run_token_makes_fixture_names_unique(self):
        case = {"id": "u", "prompt": "Fix watch-{run}.py", "area": "lifecycle",
                "fixtures": [{"path": "watch-{run}.py", "lines": ["print(1)"]}],
                "assertions": [{"id": "t", "type": "exec", "cmd": "python3 watch-{run}.py"}]}
        a = rbe.materialize_case(case, rbe.run_token("u__m1__skill__r1"))
        b = rbe.materialize_case(case, rbe.run_token("u__m2__skill__r1"))
        self.assertNotEqual(a["fixtures"][0]["path"], b["fixtures"][0]["path"])
        self.assertEqual(a["prompt"], f"Fix {a['fixtures'][0]['path']}")
        self.assertIn(a["fixtures"][0]["path"], a["assertions"][0]["cmd"])
        plain = {"id": "p", "prompt": "x {fg.muted} y", "area": "build", "assertions": []}
        self.assertIs(rbe.materialize_case(plain, "abc123"), plain)


@unittest.skipIf(rbe is None, "evals/ not present (installed copy)")
class Secrets(CatalogCase):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.dict(os.environ, {"FAKE_SERVICE_TOKEN": FAKE_SECRET, "EVAL_OMP_API_KEY": FAKE_SECRET + "x",
                                               "TMUX": "/tmp/tmux-501/default,1,0", "TMUX_PANE": "%1"})
        patcher.start()
        self.addCleanup(patcher.stop)
        rbe.set_redactor(rbe.Redactor.from_environment(self.tmp / "no-env-file"))

    def test_1_agent_and_exec_env_are_allow_listed(self):
        env = rbe.base_env(self.tmp / "h", self.tmp / "t", ["FAKE_SERVICE_TOKEN", "LC_ALL"])
        self.assertNotIn("FAKE_SERVICE_TOKEN", env)        # a secret-looking name is never passed through
        self.assertNotIn("TMUX", env)
        self.assertEqual(env["HOME"], str(self.tmp / "h"))
        self.assertEqual(env["TMUX_TMPDIR"], str(self.tmp / "t"))
        self.assertTrue(set(env) <= set(rbe.ALLOWED_ENV) | {"HOME", "TMPDIR", "TMUX_TMPDIR"} |
                        {k for k in env if k.startswith("LC_")})
        ex_env = rbe.exec_env(self.tmp / "h", self.tmp / "t")
        self.assertNotIn(FAKE_SECRET, json.dumps(ex_env))
        self.assertNotIn("TMUX", ex_env)
        cli = self.script("dump.py", ENV_DUMP_CLI)
        self.use(models_doc(extra_models=[cli_model("dump", cli)]))
        case = {"id": "c", "prompt": "hi", "area": "build", "assertions": [{"id": "a", "type": "no_new_files"}]}
        rec = rbe.run_one(case, "dump", "none", "baseline", 1, run_args(), rbe.Budget(None), self.tmp)
        seen = json.loads(rec["final_answer"])["env"]
        self.assertNotIn("FAKE_SERVICE_TOKEN", seen)
        self.assertNotIn("EVAL_OMP_API_KEY", seen)
        self.assertNotIn("TMUX", seen)
        self.assertNotEqual(seen["HOME"], str(Path.home()))   # command adapter: a fresh HOME
        self.assertIsNone(rec.get("secret_leak"))

    def test_2_no_secret_in_argv(self):
        self.use(models_doc())
        inv = rbe.build_command("omp", "glm", "high", "skill", self.tmp / "p", self.tmp / "w", self.tmp / "h")
        self.assertNotIn("--api-key", inv.argv)
        self.assertNotIn(FAKE_SECRET, " ".join(inv.argv))
        self.assertEqual(inv.argv[inv.argv.index("--profile") + 1], "tui-design-evals")
        inv, _ = rbe.judge_command("glm", self.tmp / "p")
        self.assertNotIn(FAKE_SECRET, " ".join(inv.argv))
        for adapter, mid in (("claude", "haiku"),):
            inv = rbe.build_command(adapter, mid, "low", "skill", self.tmp / "p", self.tmp / "w", self.tmp / "h")
            self.assertNotIn(FAKE_SECRET, " ".join(inv.argv) + json.dumps(inv.env))

    def test_3_artifacts_are_redacted_and_4_the_run_is_flagged(self):
        cli = self.script("leaky.py", "import sys, os\np = open(sys.argv[1]).read()\n"
                                      "open('leak.txt', 'w').write(p)\nprint('the key is ' + p)\n"
                                      "sys.stderr.write(p)\n")
        self.use(models_doc(extra_models=[cli_model("leaky", cli)]))
        case = {"id": "c", "prompt": FAKE_SECRET, "area": "build", "assertions": [{"id": "a", "type": "no_new_files"}]}
        rec = rbe.run_one(case, "leaky", "none", "baseline", 1, run_args(), rbe.Budget(None), self.tmp)
        self.assertIn("secret leak", rec["error"])
        self.assertEqual(rec["secret_leak"]["names"], ["FAKE_SERVICE_TOKEN"])
        self.assertIn("<redacted:FAKE_SERVICE_TOKEN>", rec["final_answer"])
        self.assertEqual(rbe.leak_scan(rbe.run_artifacts(self.tmp, rec["run_id"])), {})   # nothing raw on disk
        blob = b"".join(gzip.decompress(f.read_bytes()) if f.suffix == ".gz" else f.read_bytes()
                        for f in self.tmp.rglob("*") if f.is_file())
        self.assertNotIn(FAKE_SECRET.encode(), blob)
        self.assertIn(b"<redacted:FAKE_SERVICE_TOKEN>", blob)

    def test_4_leak_scan_finds_raw_values_in_gz_and_scrubs(self):
        runs = self.tmp / "runs"
        (runs / "r1.files").mkdir(parents=True)
        (runs / "r1.events.jsonl.gz").write_bytes(gzip.compress(f'{{"text": "{FAKE_SECRET}"}}\n'.encode()))
        (runs / "r1.files" / "out.txt").write_text("clean")
        (runs / "r1.json").write_text(json.dumps({"run_id": "r1", "error": None}))
        found = rbe.leak_scan(rbe.run_artifacts(runs, "r1"))
        self.assertEqual(found, {"r1.events.jsonl.gz": ["FAKE_SERVICE_TOKEN"]})
        rec = rbe.check_leaks(runs, {"run_id": "r1", "error": None}, [])
        self.assertIn("secret leak", rec["error"])
        self.assertEqual(rbe.leak_scan(rbe.run_artifacts(runs, "r1")), {})
        self.assertIn(b"<redacted:FAKE_SERVICE_TOKEN>", gzip.decompress((runs / "r1.events.jsonl.gz").read_bytes()))

    def test_4_a_leak_stops_the_campaign(self):
        cli = self.script("leaky.py", "import sys\nprint(open(sys.argv[1]).read())\n")
        mf = self.tmp / "models.toml"
        mf.write_text('[defaults]\nmodels = "leaky"\n[judges]\ntext = "haiku"\nvision = "haiku"\n'
                      '[[models]]\nid = "haiku"\nadapter = "claude"\n'
                      f'[[models]]\nid = "leaky"\nadapter = "command"\neffort = "none"\n'
                      f'command = [{json.dumps(sys.executable)}, {json.dumps(str(cli))}, "{{prompt_file}}"]\n')
        cf = self.tmp / "cases.json"
        cf.write_text(json.dumps({"cases": [
            {"id": "first", "prompt": "token " + FAKE_SECRET, "area": "build", "assertions": [{"id": "a", "type": "no_new_files"}]},
            {"id": "second", "prompt": "fine", "area": "build", "assertions": [{"id": "a", "type": "no_new_files"}]}]}))
        out = io.StringIO()
        with redirect_stdout(out):
            code = rbe.main(["--models-file", str(mf), "--cases-file", str(cf), "--cases-dir", str(self.tmp / "none"),
                             "--arms", "baseline", "--no-judge", "--no-exec", "--out", str(self.tmp / "res")])
        self.assertEqual(code, 3)
        self.assertIn("SECRET LEAK", out.getvalue())
        self.assertEqual([p.name for p in (self.tmp / "res" / "runs").glob("*.json")], ["first__leaky__baseline__r1.json"])
        self.assertIn("a secret reached", (self.tmp / "res" / "summary.md").read_text())

    def test_redactor_reads_the_env_file_and_ignores_short_values(self):
        envf = self.tmp / "env"
        envf.write_text(f'MY_SECRET_KEY="{FAKE_SECRET}2"\nSHORT_TOKEN=abc\nBASE_URL="https://example.org/a/long/path"\n')
        r = rbe.Redactor.from_environment(envf)
        self.assertIn("MY_SECRET_KEY", r.secrets)
        self.assertNotIn("SHORT_TOKEN", r.secrets)
        self.assertNotIn("BASE_URL", r.secrets)
        self.assertEqual(r.text(f"x {FAKE_SECRET}2 y")[0], "x <redacted:MY_SECRET_KEY> y")

    def test_exporter_strips_secrets_from_request_bodies(self):
        named = ex.payload_secrets(self.tmp / "none", {"FAKE_SERVICE_TOKEN": FAKE_SECRET, "PATH": "/usr/bin:/bin:/x"})
        self.assertEqual(named, {"FAKE_SERVICE_TOKEN": FAKE_SECRET})
        sent = {}

        class Resp(io.BytesIO):
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def fake_urlopen(req, timeout=None, context=None):
            sent["body"] = req.data
            return Resp(b"{}")
        old = ex._PAYLOAD_SECRETS
        try:
            ex._PAYLOAD_SECRETS = named
            with mock.patch.object(ex.urllib.request, "urlopen", fake_urlopen):
                ex.Http("https://lf.example", "Basic x", []).request("POST", "/x", {"output": "key " + FAKE_SECRET})
        finally:
            ex._PAYLOAD_SECRETS = old
        self.assertNotIn(FAKE_SECRET.encode(), sent["body"])
        self.assertIn(b"<redacted:FAKE_SERVICE_TOKEN>", sent["body"])

    def test_5_project_root_is_the_checkout_around_evals(self):
        root = self.tmp / "proj"
        (root / ".git").mkdir(parents=True)
        (root / "evals" / "sub").mkdir(parents=True)
        self.assertEqual(rbe.project_root(root / "evals" / "sub"), root)
        bare = self.tmp / "bare"
        (bare / "evals").mkdir(parents=True)
        self.assertEqual(rbe.project_root(bare / "evals"), bare)
        sys.path.insert(0, str(EVALS))
        try:
            import ledger
        finally:
            sys.path.remove(str(EVALS))
        if not os.environ.get("EVAL_LEDGER"):
            self.assertEqual(ledger.DEFAULT_LEDGER, EVALS / "ledger.jsonl")

    @unittest.skipUnless(shutil.which("sandbox-exec") and not os.environ.get("EVAL_NO_SANDBOX"), "macOS sandbox-exec")
    def test_5_confinement_denies_the_project_checkout(self):
        run_dir = Path(tempfile.mkdtemp(prefix="evalrun-"))
        self.addCleanup(shutil.rmtree, run_dir, True)
        (run_dir / "mine.txt").write_text("ok")
        prof = rbe.confine_profile(run_dir)
        self.assertIn(str(rbe.project_root().resolve()), prof)
        inside = subprocess.run(["sandbox-exec", "-p", prof, "cat", str(run_dir / "mine.txt")], capture_output=True)
        outside = subprocess.run(["sandbox-exec", "-p", prof, "cat", str(EVALS / "behavior-evals.json")],
                                 capture_output=True)
        self.assertEqual(inside.returncode, 0)
        self.assertNotEqual(outside.returncode, 0)
        self.assertIn(b"Operation not permitted", outside.stderr)


if __name__ == "__main__":
    unittest.main()
