"""evals/export_results.py: identity derivation (checked against run_behavior_evals), payload building for
Langfuse and Phoenix, redaction, credentials loading, the state file and --dry-run. No network.

Skipped when evals/ is absent (the copy of the skill an agent works with has no evals/).
"""

import importlib.util
import io
import json
import shutil
import ssl
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills" / "tui-design"
EXPORTER = REPO / "evals" / "export_results.py"
RUNNER = REPO / "evals" / "run_behavior_evals.py"
CASES = REPO / "evals" / "behavior-evals.json"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ex = _load("export_results", EXPORTER) if EXPORTER.exists() else None
rbe = _load("run_behavior_evals_for_export", RUNNER) if RUNNER.exists() else None

CASE = {"id": "demo-case", "area": "layout", "lang": "en", "source": "T0.1", "prompt": "Sketch it",
        "fixtures": [{"path": "app/main.py", "lines": ["print('hi')"]}],
        "assertions": [{"id": "has-frame", "type": "file_glob", "neutral": True, "glob": "*.mock",
                        "desc": "a frame exists"},
                       {"id": "asks-size", "type": "judge", "neutral": True, "question": "Does it ask?"}]}
SECRETS_CFG = {"LANGFUSE_PUBLIC_KEY": "pk-lf-public-1234", "LANGFUSE_SECRET_KEY": "sk-lf-secret-5678",
               "LANGFUSE_BASE_URL": "https://lf.example:3100", "PHOENIX_BASE_URL": "https://px.example:6006",
               "PHOENIX_API_KEY": "px-api-key-9999", "PHOENIX_PROJECT_NAME": "proj"}


def record(arm="skill", error=None, rep=1, passed=(True, False), skipped=None, **extra):
    rec = {"run_id": f"demo-case__z-ai-glm-5.3-flash__{arm}__r{rep}", "case": "demo-case",
           "model": "z-ai/glm-5.3-flash", "adapter": "omp", "effort": "low", "arm": arm, "rep": rep,
           "started_at": "2026-10-02T13:20:03", "wall_s": 10.5, "error": error, "final_answer": "done",
           "tool_calls": 3, "skill_loaded": arm == "skill", "files": [{"path": "a.mock", "status": "new"}],
           "assertions": [{"id": "has-frame", "type": "file_glob", "kind": "program", "neutral": True,
                           "passed": passed[0], "detail": "x" * 3000},
                          {"id": "asks-size", "type": "judge", "kind": "judge", "neutral": True,
                           "passed": passed[1], "detail": "no question asked"},
                          {"id": "not-run", "type": "exec", "kind": "executed", "neutral": True,
                           "passed": None, "detail": "not run (--no-exec)"}],
           "tokens": {"input": 100, "cached": 50, "cache_write": 0, "output": 20, "reasoning": 5},
           "cost_usd": 0.0123, "cost_basis": "billed", "judge": {"model": "haiku", "cost_usd": 0.01}}
    if skipped:
        rec["skipped"] = skipped
    rec.update(extra)
    return rec


def write_results(root: Path, recs, config=None, dataset=None) -> Path:
    d = root / "res"
    (d / "runs").mkdir(parents=True)
    (d / "config.json").write_text(json.dumps(config or {"judge": "haiku"}))
    for r in recs:
        (d / "runs" / f"{r['run_id']}.json").write_text(json.dumps(r))
    if dataset is not None:
        (d / "dataset.json").write_text(json.dumps({"items": dataset}))
    return d


def cases_file(root: Path) -> Path:
    p = root / "cases.json"
    p.write_text(json.dumps({"cases": [CASE]}))
    return p


@unittest.skipIf(ex is None, "evals/ not present")
class TestIdentity(unittest.TestCase):
    def test_case_hash_matches_runner(self):
        self.assertIsNotNone(rbe)
        for c in json.loads(CASES.read_text())["cases"]:
            self.assertEqual(ex.case_hash(c), rbe.case_hash(c), c["id"])

    def test_dataset_entry_matches_runner(self):
        cases = json.loads(CASES.read_text())["cases"][:5]
        self.assertEqual([ex.dataset_entry(c) for c in cases], rbe.dataset_entries(cases))

    def test_derived_keys_match_runner_definition(self):
        case = json.loads(CASES.read_text())["cases"][0]
        want = rbe.run_identity(case, "z-ai/glm-5.3-flash", "low", "skill", 2, "haiku", None, None, None)
        rec = record(rep=2) | {"case": case["id"]}
        got = ex.run_identity(rec, {"judge": "haiku"}, {case["id"]: ex.dataset_entry(case)})
        self.assertEqual(got["identity"], want["identity"])
        self.assertEqual((got["run_key"], got["experiment_key"]), (want["run_key"], want["experiment_key"]))
        self.assertEqual(got["identity_source"], "derived")

    def test_runner_identity_is_used_as_is(self):
        rec = record(identity={"case_id": "demo-case", "rep": 1}, run_key="r" * 64, experiment_key="e" * 64)
        got = ex.run_identity(rec, {}, {})
        self.assertEqual((got["run_key"], got["experiment_key"], got["identity_source"]),
                         ("r" * 64, "e" * 64, "runner"))

    def test_experiment_key_ignores_case_and_rep(self):
        a = ex.identity_fields("c1", "h1", "m/x", "omp", None, "low", "abc", "haiku", None, "skill", 1)
        b = ex.identity_fields("c2", "h2", "m/x", "omp", None, "low", "abc", "haiku", None, "skill", 3)
        self.assertNotEqual(ex.keys_for(a)[0], ex.keys_for(b)[0])
        self.assertEqual(ex.keys_for(a)[1], ex.keys_for(b)[1])

    def test_baseline_drops_skill_hash(self):
        self.assertIsNone(ex.identity_fields("c", "h", "m", "omp", None, "low", "abc", None, None,
                                             "baseline", 1)["skill_hash"])


@unittest.skipIf(ex is None, "evals/ not present")
class TestLoadAndNames(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_load_skips_skipped_and_unknown(self):
        recs = [record(), record(arm="baseline"), record(arm="skill", rep=2, skipped="no go"),
                record(arm="skill", rep=3) | {"case": "gone", "run_id": "gone__x"}]
        d = write_results(self.tmp, recs)
        data = ex.load_results(d, cases_file(self.tmp))
        self.assertEqual(len(data["runs"]), 2)
        self.assertEqual(len(data["skipped"]), 1)
        self.assertEqual(data["unknown"], ["gone__x"])
        self.assertEqual(list(data["entries"]), ["demo-case"])

    def test_dataset_json_wins_over_cases_file(self):
        entry = ex.dataset_entry(CASE) | {"case_hash": "f" * 64}
        d = write_results(self.tmp, [record()], dataset=[entry])
        data = ex.load_results(d, cases_file(self.tmp))
        self.assertEqual(data["runs"][0]["identity"]["case_hash"], "f" * 64)

    def test_item_id(self):
        e = ex.dataset_entry(CASE)
        self.assertEqual(ex.item_id("tui-design-behavior", e), f"tui-design:demo-case@{e['case_hash'][:12]}")
        self.assertTrue(ex.item_id("other-set", e).startswith("other-set:demo-case@"))
        self.assertLessEqual(len(ex.item_id("x" * 300, e)), 255)

    def test_experiment_names(self):
        sk = ex.identity_fields("c", "h", "z-ai/glm-5.3-flash", "omp", None, "low", "1a2b3c4d5e", "haiku", None,
                                "skill", 1)
        self.assertEqual(ex.experiment_name(sk), "glm-5.3-flash · low · skill · 1a2b3c4d")
        self.assertEqual(ex.experiment_name(sk | {"skill_hash": None}), "glm-5.3-flash · low · skill · skill-unknown")
        self.assertEqual(ex.experiment_name(sk | {"arm": "baseline"}), "glm-5.3-flash · low · baseline")

    def test_ids_are_deterministic_hex(self):
        self.assertEqual(ex.trace_id("k"), ex.trace_id("k"))
        self.assertRegex(ex.trace_id("k"), r"^[0-9a-f]{32}$")
        self.assertRegex(ex.span_id("k"), r"^[0-9a-f]{16}$")
        self.assertNotEqual(ex.span_id("k"), ex.span_id("k", "gen"))
        self.assertNotEqual(ex.score_id("k", "a"), ex.score_id("k", "b"))


@unittest.skipIf(ex is None, "evals/ not present")
class TestPayloads(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        d = write_results(self.tmp, [record(), record(arm="baseline", error="timeout after 900s")])
        self.data = ex.load_results(d, cases_file(self.tmp))
        self.ok, self.err = sorted(self.data["runs"], key=lambda r: r["rec"]["arm"], reverse=True)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_langfuse_item(self):
        p = ex.lf_item_payload("tui-design-behavior", self.ok["entry"])
        self.assertEqual(p["input"], {"prompt": "Sketch it", "fixtures": ["app/main.py"], "case_id": "demo-case"})
        self.assertEqual([a["id"] for a in p["expectedOutput"]], ["has-frame", "asks-size"])
        self.assertEqual(p["expectedOutput"][1]["question"], "Does it ask?")
        self.assertEqual(p["metadata"]["origin"], "T0.1")
        self.assertEqual(p["metadata"]["case_hash"], self.ok["entry"]["case_hash"])

    def test_langfuse_scores(self):
        s = {x["name"]: x for x in ex.lf_scores(self.ok)}
        self.assertEqual(set(s), {"has-frame", "asks-size", "pass_rate", "cost_usd", "tokens_total", "skill_loaded"})
        self.assertEqual((s["has-frame"]["value"], s["has-frame"]["dataType"]), (1, "BOOLEAN"))
        self.assertEqual(s["asks-size"]["value"], 0)
        self.assertEqual(s["has-frame"]["metadata"]["type"], "program")
        self.assertEqual(s["asks-size"]["metadata"]["type"], "judge")
        self.assertLessEqual(len(s["has-frame"]["comment"]), ex.COMMENT_MAX)
        self.assertEqual(s["pass_rate"]["value"], 0.5)
        self.assertEqual(s["tokens_total"]["value"], 170)
        self.assertEqual(s["has-frame"]["traceId"], ex.trace_id(self.ok["run_key"]))
        self.assertEqual(s["has-frame"]["id"], ex.score_id(self.ok["run_key"], "has-frame"))

    def test_errored_run_has_no_pass_fail_scores(self):
        names = {x["name"] for x in ex.lf_scores(self.err)}
        self.assertFalse(names & {"has-frame", "asks-size", "pass_rate"})
        self.assertEqual(ex.px_evaluations(self.err, "run1"), [])
        self.assertEqual(ex.px_run_payload(self.err, "node")["error"], "timeout after 900s")

    def test_langfuse_spans(self):
        spans = ex.lf_spans(self.ok, "run name", "ds1", "exp1", "tui-design-behavior", "res")
        root, gen = spans
        attrs = {a["key"]: a["value"] for a in root["attributes"]}
        self.assertEqual(root["traceId"], ex.trace_id(self.ok["run_key"]))
        self.assertEqual(gen["parentSpanId"], root["spanId"])
        self.assertEqual(attrs["langfuse.experiment.id"]["stringValue"], "exp1")
        self.assertEqual(attrs["langfuse.experiment.item.id"]["stringValue"],
                         ex.item_id("tui-design-behavior", self.ok["entry"]))
        self.assertEqual(attrs["langfuse.experiment.item.root_observation_id"]["stringValue"], root["spanId"])
        self.assertEqual(attrs["langfuse.trace.metadata.rep"]["stringValue"], "1")
        self.assertEqual(attrs["langfuse.trace.output"]["stringValue"], "done")
        self.assertIn("langfuse.experiment.metadata.experiment_key", attrs)
        gattrs = {a["key"]: a["value"] for a in gen["attributes"]}
        self.assertEqual(json.loads(gattrs["langfuse.observation.cost_details"]["stringValue"]), {"total": 0.0123})
        self.assertEqual(int(root["endTimeUnixNano"]) - int(root["startTimeUnixNano"]), 10_500_000_000)
        err_root = ex.lf_spans(self.err, "n", "d", "e", "tui-design-behavior", "res")[0]
        self.assertEqual(err_root["status"]["code"], 2)

    def test_phoenix_payloads(self):
        e = ex.px_example(self.ok["entry"], "tui-design-behavior")
        self.assertEqual(e["output"]["assertions"][0]["id"], "has-frame")
        run = ex.px_run_payload(self.ok, "node1")
        self.assertEqual((run["dataset_example_id"], run["repetition_number"], run["error"]), ("node1", 1, None))
        self.assertEqual(run["output"]["files"], ["a.mock (new)"])
        self.assertRegex(run["start_time"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        evs = {x["name"]: x for x in ex.px_evaluations(self.ok, "run1")}
        self.assertEqual(set(evs), {"has-frame", "asks-size", "pass_rate"})
        self.assertEqual(evs["has-frame"]["annotator_kind"], "CODE")
        self.assertEqual(evs["asks-size"]["annotator_kind"], "LLM")
        self.assertEqual(evs["asks-size"]["result"]["label"], "fail")
        self.assertEqual(evs["pass_rate"]["result"]["score"], 0.5)

    def test_dry_run_plan_and_no_network(self):
        out = io.StringIO()
        with mock.patch("urllib.request.urlopen", side_effect=AssertionError("network")), redirect_stdout(out), \
                mock.patch.object(ex, "load_config", return_value=SECRETS_CFG):
            rc = ex.main([str(self.tmp / "res"), "--to", "langfuse,phoenix", "--dry-run",
                          "--cases", str(self.tmp / "cases.json")])
        self.assertEqual(rc, 0)
        self.assertIn("2 run(s) new", out.getvalue())
        self.assertFalse((self.tmp / "res" / ex.STATE_FILE).exists())
        for s in ex.secrets_of(SECRETS_CFG):
            self.assertNotIn(s, out.getvalue())


@unittest.skipIf(ex is None, "evals/ not present")
class TestPrune(unittest.TestCase):
    def test_stale_runs_mark_their_experiment_on_both_state_shapes(self):
        data = {"runs": [{"run_key": "r1"}]}
        lf = {"experiments": {"E1": {"dataset_run_id": "d1"}, "E2": {"dataset_run_id": "d2"}},
              "runs": {"r1": {"experiment_key": "E1"}, "old": {"experiment_key": "E2"}}}
        px = {"experiments": {"E1": {"id": "x1"}, "E2": {"id": "x2"}},
              "runs": {"r1": {"experiment_id": "x1"}, "old": {"experiment_id": "x2"}}}
        self.assertEqual(ex.stale_experiment_keys(data, lf), {"E2"})
        self.assertEqual(ex.stale_experiment_keys(data, px), {"E2"})
        self.assertEqual(ex.stale_experiment_keys({"runs": [{"run_key": "r1"}, {"run_key": "old"}]}, px), set())

    def test_forget_removes_the_experiment_and_its_runs(self):
        px = {"experiments": {"E1": {"id": "x1"}, "E2": {"id": "x2"}},
              "runs": {"a": {"experiment_id": "x1"}, "b": {"experiment_id": "x2"}, "c": {"experiment_id": "x2"}}}
        exp, runs = ex.forget_experiment(px, "E2")
        self.assertEqual(exp, {"id": "x2"})
        self.assertEqual(sorted(runs), ["b", "c"])
        self.assertEqual(list(px["runs"]), ["a"])
        self.assertEqual(list(px["experiments"]), ["E1"])

    def test_langfuse_drop_deletes_only_stale_traces(self):
        lf = ex.LangfuseExporter.__new__(ex.LangfuseExporter)
        calls = []
        lf.http = type("H", (), {"request": lambda self, m, path, *a, **k: calls.append((m, path)) or (200, {})})()
        st = {"experiments": {"E": {"dataset_run_id": "d", "run_name": "qwen · baseline"}},
              "runs": {"live": {"experiment_key": "E", "trace_id": "t1"}, "old": {"experiment_key": "E", "trace_id": "t2"}}}
        lf.drop_experiment("ds", st, "E", {"live"})
        self.assertIn(("DELETE", "/api/public/traces/t2"), calls)
        self.assertNotIn(("DELETE", "/api/public/traces/t1"), calls)
        self.assertTrue(any(p.startswith("/api/public/datasets/ds/runs/") for _, p in calls))


@unittest.skipIf(ex is None, "evals/ not present")
class TestSecretsAndState(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_env_file_parsing_and_precedence(self):
        f = self.tmp / "env"
        f.write_text('# creds\nLANGFUSE_PUBLIC_KEY="pk-file"\nexport PHOENIX_API_KEY=\'px-file\'\n'
                     'LANGFUSE_BASE_URL=https://h:3100\nUNRELATED=1\n\n')
        cfg = ex.load_config(f, {"PHOENIX_API_KEY": "px-env"})
        self.assertEqual(cfg["LANGFUSE_PUBLIC_KEY"], "pk-file")
        self.assertEqual(cfg["PHOENIX_API_KEY"], "px-env")
        self.assertEqual(cfg["LANGFUSE_BASE_URL"], "https://h:3100")
        self.assertNotIn("UNRELATED", cfg)
        self.assertEqual(ex.load_config(self.tmp / "missing", {}), {})

    def test_redaction(self):
        secrets = ex.secrets_of(SECRETS_CFG)
        token = ex.basic_token("pk-lf-public-1234", "sk-lf-secret-5678")
        msg = f"failed sk-lf-secret-5678 and px-api-key-9999 Authorization: Basic {token}"
        red = ex.redact(msg, secrets)
        for s in ("sk-lf-secret-5678", "px-api-key-9999", token):
            self.assertNotIn(s, red)
        self.assertIn("***", red)
        self.assertNotIn("abc123", ex.redact("Authorization: Bearer abc123", []))

    def test_http_error_is_redacted(self):
        http = ex.Http("https://px.example", "Bearer px-api-key-9999", ex.secrets_of(SECRETS_CFG))
        err = urllib.error.HTTPError("https://px.example/v1", 401, "no", {}, io.BytesIO(b"bad key px-api-key-9999"))
        with mock.patch("urllib.request.urlopen", side_effect=err):
            with self.assertRaises(ex.ExportError) as cm:
                http.request("GET", "/v1/datasets")
        self.assertNotIn("px-api-key-9999", str(cm.exception))
        self.assertIn("HTTP 401", str(cm.exception))

    def test_tls_failure_suggests_insecure(self):
        http = ex.Http("https://px.example", "Bearer x", [])
        err = urllib.error.URLError(ssl.SSLCertVerificationError(1, "CERTIFICATE_VERIFY_FAILED"))
        with mock.patch("urllib.request.urlopen", side_effect=err):
            with self.assertRaises(ex.ExportError) as cm:
                http.request("GET", "/v1/datasets")
        self.assertIn("--insecure", str(cm.exception))
        self.assertEqual(http.ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertEqual(ex.Http("https://x", "a", [], insecure=True).ctx.verify_mode, ssl.CERT_NONE)

    def test_state_roundtrip_and_secret_guard(self):
        st = ex.load_state(self.tmp)
        self.assertEqual(st, {"version": 1, "targets": {}})
        t = ex.target_state(st, "langfuse", "https://h:3100/", "ds")
        t["runs"]["k"] = {"trace_id": "t"}
        ex.save_state(self.tmp, st, ["sk-secret"])
        again = ex.load_state(self.tmp)
        self.assertEqual(again["targets"]["langfuse|https://h:3100|ds"]["runs"]["k"], {"trace_id": "t"})
        t["runs"]["k"]["oops"] = "sk-secret"
        with self.assertRaises(ex.ExportError):
            ex.save_state(self.tmp, st, ["sk-secret"])
        self.assertNotIn("sk-secret", (self.tmp / ex.STATE_FILE).read_text())

    def test_main_reports_redacted_error(self):
        d = write_results(self.tmp, [record()])
        err = io.StringIO()
        with mock.patch.object(ex, "load_config", return_value=SECRETS_CFG), redirect_stderr(err), \
                redirect_stdout(io.StringIO()), mock.patch(
                    "urllib.request.urlopen", side_effect=urllib.error.URLError("refused sk-lf-secret-5678")):
            rc = ex.main([str(d), "--to", "langfuse", "--cases", str(cases_file(self.tmp))])
        self.assertEqual(rc, 1)
        self.assertIn("error:", err.getvalue())
        self.assertNotIn("sk-lf-secret-5678", err.getvalue())


if __name__ == "__main__":
    unittest.main()
