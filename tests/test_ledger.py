"""evals/ledger.py: a record built from synthetic runs, upsert by campaign, no absolute paths or hosts."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))
import ledger  # noqa: E402


def run(case, model, arm, passed, graded, cost, error=None):
    return {"run_id": f"{case}__{model}__{arm}__r1", "case": case, "model": model, "arm": arm, "rep": 1,
            "error": error, "score": {"passed": passed, "graded": graded}, "cost_usd": cost, "cost_basis": "billed",
            "tokens": {"input": 10, "cached": 100 if arm == "skill" else 20, "output": 5}, "wall_s": 60,
            "skill_loaded": arm == "skill", "started_at": "2026-10-02T10:00:00",
            "identity": {"model": model, "effort": "high", "skill_hash": "abc", "adapter_version": "omp/1"}}


class Ledger(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.d = self.tmp / "camp-1"
        (self.d / "runs").mkdir(parents=True)
        for r in (run("a", "m1", "skill", 4, 5, 0.2), run("a", "m1", "baseline", 2, 5, 0.1),
                  run("b", "m1", "skill", 0, 5, 0.9, error="timeout")):
            (self.d / "runs" / f"{r['run_id']}.json").write_text(json.dumps(r))
        (self.d / "run.log").write_text("[1/3] a · m1@high · skill · rep 1\n    -> a__m1__skill__r1: 4/5\n")
        (self.d / "export-state.json").write_text(json.dumps({"version": 1, "targets": {
            "phoenix|https://private.host:6006|ds": {}}}))

    def test_record(self):
        rec = ledger.build(self.d, "x")
        m = rec["per_model"]["m1"]
        self.assertEqual((m["skill_pass_pct"], m["baseline_pass_pct"], m["delta_pts"]), (80.0, 40.0, 40.0))
        self.assertEqual(m["errors"], {"skill": 1, "baseline": 0})
        self.assertEqual(rec["errored_runs"], 1)
        self.assertEqual(rec["exported_to"], ["phoenix:ds"])
        self.assertNotIn(str(self.tmp), json.dumps(rec))          # no absolute paths
        self.assertNotIn("private.host", json.dumps(rec))         # no hosts

    def test_upsert_replaces_campaign(self):
        lp = self.tmp / "ledger.jsonl"
        ledger.upsert(lp, ledger.build(self.d, "first"))
        ledger.upsert(lp, ledger.build(self.d, "second"))
        lines = lp.read_text().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["label"], "second")


if __name__ == "__main__":
    unittest.main()
