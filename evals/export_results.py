#!/usr/bin/env python3
"""Export behavior-eval results of the tui-design skill to Langfuse and/or Arize Phoenix (stdlib only).

    python3 evals/export_results.py RESULTS_DIR --to langfuse,phoenix [--dataset-name NAME]
                                    [--dry-run] [--insecure] [--verify]

RESULTS_DIR is a directory written by evals/run_behavior_evals.py (config.json, runs/<run_id>.json, optional
dataset.json). What gets created:

  dataset     one per case set (default name `tui-design-behavior`), one item / example per case:
              input = {prompt, fixtures (paths), case_id}, expected output = the assertion list,
              metadata = {case_id, case_hash, area, tags, origin, lang, depends_on}.
  experiment  one per experiment_key (model + provider + adapter + effort + skill hash + judges + arm), named
              e.g. `glm-5.3-flash · low · skill · 1a2b3c4d`; every identity field goes into its metadata.
  run         one per run record (rep = repetition); errored runs carry the error and no pass/fail scores;
              skipped runs are not exported.
  scores      one per graded assertion (1/0) + pass_rate (+ cost_usd, tokens_total, skill_loaded on Langfuse).

Langfuse (v4, events_only): dataset via POST /api/public/v2/datasets, items via POST /api/public/dataset-items
(upsert on id `tui-design:<case_id>@<case_hash[:12]>`), the dataset run via POST /api/public/dataset-run-items
(only once per run: the endpoint appends a row on every call), the run's trace as OTLP/JSON spans with the
`langfuse.experiment.*` attributes on POST /api/public/otel/v1/traces (trace and span ids derived from run_key,
so a re-send replaces the spans), scores via POST /api/public/scores (upsert on a deterministic id).
Phoenix: dataset via POST /v1/datasets/upload (create, then append only new or changed examples; examples carry
a stable `example_ids` entry), experiments looked up by metadata.experiment_key before POST
/v1/datasets/{id}/experiments, runs via POST /v1/experiments/{id}/runs (upsert on example + repetition),
evaluations via POST /v1/experiment_evaluations (upsert on run + name).

Re-exporting the same directory (e.g. after --regrade) updates scores and evaluations in place and creates
nothing twice. The remote ids are kept in RESULTS_DIR/export-state.json (the only file this script writes).

Credentials: LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL, PHOENIX_BASE_URL, PHOENIX_API_KEY
from the environment, else from ~/.config/tui-design-evals/env (KEY="value" lines). Secret values are never
printed or written; error messages are redacted. TLS certificates are verified; --insecure skips that.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent
DEFAULT_CASES = EVALS_DIR / "behavior-evals.json"
FIXTURES_DIR = EVALS_DIR / "fixtures"
DEFAULT_ENV_FILE = Path("~/.config/tui-design-evals/env").expanduser()
DEFAULT_DATASET = "tui-design-behavior"
STATE_FILE = "export-state.json"
SKILL_NAME = "tui-design"

PROVIDERS = {"omp": "openrouter", "claude": "anthropic", "codex": "openai"}   # same as run_behavior_evals
EXECUTED_TYPES = {"exec", "tty_probe", "frame_match"}
MODEL_KINDS = {"judge", "vision"}                     # assertion `kind` graded by a model -> Phoenix LLM
SECRET_KEYS = ("LANGFUSE_SECRET_KEY", "LANGFUSE_PUBLIC_KEY", "PHOENIX_API_KEY")
CONFIG_KEYS = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL",
               "PHOENIX_BASE_URL", "PHOENIX_API_KEY", "PHOENIX_PROJECT_NAME", "EVAL_EXPORT_TO")
COMMENT_MAX = 1000          # score comment / evaluation explanation
ANSWER_MAX = 60000          # final answer uploaded as output
LF_ENVIRONMENT = "sdk-experiment"   # the environment the Langfuse SDK's experiment runner uses


class ExportError(Exception):
    pass


# ============================================================ credentials and redaction

def parse_env_file(text: str) -> dict[str, str]:
    """KEY="value" / KEY=value / export KEY=value lines; # comments and blank lines ignored."""
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        if k.startswith("export "):
            k = k[len("export "):].strip()
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        out[k] = v
    return out


def load_config(env_file: Path = DEFAULT_ENV_FILE, environ: dict | None = None) -> dict[str, str]:
    """Variables already in the environment win; the env file fills in the rest."""
    environ = os.environ if environ is None else environ
    cfg = {}
    if env_file and Path(env_file).is_file():
        cfg.update({k: v for k, v in parse_env_file(Path(env_file).read_text()).items() if k in CONFIG_KEYS})
    cfg.update({k: environ[k] for k in CONFIG_KEYS if environ.get(k)})
    return cfg


def secrets_of(cfg: dict) -> list[str]:
    """Every secret string that must never appear in output: the keys themselves and the Basic-auth token."""
    vals = [cfg[k] for k in SECRET_KEYS if cfg.get(k)]
    if cfg.get("LANGFUSE_PUBLIC_KEY") and cfg.get("LANGFUSE_SECRET_KEY"):
        vals.append(basic_token(cfg["LANGFUSE_PUBLIC_KEY"], cfg["LANGFUSE_SECRET_KEY"]))
    return sorted({v for v in vals if len(v) >= 4}, key=len, reverse=True)


def redact(text, secrets: list[str]) -> str:
    s = str(text)
    for v in secrets:
        s = s.replace(v, "***")
    return re.sub(r"(?i)(authorization['\"]?\s*[:=]\s*['\"]?)(basic|bearer)\s+\S+", r"\1\2 ***", s)


SECRET_NAME_RX = re.compile(r"KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL", re.I)
_PAYLOAD_SECRETS: dict[str, str] | None = None


def payload_secrets(env_file: Path = DEFAULT_ENV_FILE, environ: dict | None = None) -> dict[str, str]:
    """name -> value of every variable named like a key, token, secret or password (8+ chars), from the environment
    and the env file: stripped from every request body before it leaves this machine (defense in depth; the runner
    already redacts run artifacts)."""
    environ = os.environ if environ is None else environ
    out = {}
    if env_file and Path(env_file).is_file():
        out.update({k: v for k, v in parse_env_file(Path(env_file).read_text()).items() if SECRET_NAME_RX.search(k)})
    out.update({k: v for k, v in environ.items() if SECRET_NAME_RX.search(k)})
    return {k: v for k, v in out.items() if v and len(v) >= 8}


def redact_named(text: str, named: dict[str, str]) -> str:
    for name, val in sorted(named.items(), key=lambda kv: len(kv[1]), reverse=True):
        text = text.replace(val, f"<redacted:{name}>")
    return text


def basic_token(public: str, secret: str) -> str:
    return base64.b64encode(f"{public}:{secret}".encode()).decode()


# ============================================================ identity (same definition as run_behavior_evals)

def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _fixture_src(rel: str, fixtures_dir: Path = FIXTURES_DIR) -> Path:
    if not rel or rel.startswith("/") or ".." in Path(rel).parts:
        return fixtures_dir / "__invalid__"
    return fixtures_dir / rel


def fixture_bytes(f: dict, fixtures_dir: Path = FIXTURES_DIR) -> bytes:
    if "lines" in f:
        return ("\n".join(f["lines"]) + "\n").encode()
    if "content" in f:
        return f["content"].encode()
    return _fixture_src(f["src"], fixtures_dir).read_bytes()


HASH_EXCLUDED_KEYS = ("serial",)   # same as run_behavior_evals: scheduling only, not part of the case's identity


def case_hash(case: dict, fixtures_dir: Path = FIXTURES_DIR) -> str:
    """sha256 of the case's canonical JSON with the bytes of each `src` fixture and judge_reference folded in."""
    c = {k: v for k, v in json.loads(json.dumps(case)).items() if k not in HASH_EXCLUDED_KEYS}
    for f in c.get("fixtures", []):
        if "src" in f:
            f["src_sha256"] = sha256_bytes(_fixture_src(f["src"], fixtures_dir).read_bytes())
    if c.get("judge_reference"):
        c["judge_reference_sha256"] = [sha256_bytes(_fixture_src(r, fixtures_dir).read_bytes())
                                       for r in c["judge_reference"]]
    return sha256_text(canonical(c))


def case_tags(case: dict) -> list[str]:
    tags = set(case.get("tags", [])) | {case.get("area", "")}
    if case.get("depends_on"):
        tags.add(case["depends_on"])
    types = {a.get("type") for a in case.get("assertions", [])}
    if types & EXECUTED_TYPES:
        tags.add("executed")
    if "tty_probe" in types:
        tags.add("tmux")
    if "vision_rubric" in types:
        tags.add("vision")
    if "judge" in types:
        tags.add("judge")
    if any("src" in f for f in case.get("fixtures", [])):
        tags.add("fixture-files")
    return sorted(t for t in tags if t)


def dataset_entry(case: dict, fixtures_dir: Path = FIXTURES_DIR) -> dict:
    """Same shape as run_behavior_evals.dataset_entries (used when the results dir has no dataset.json)."""
    return {
        "case_id": case["id"], "case_hash": case_hash(case, fixtures_dir), "area": case.get("area"),
        "tags": case_tags(case), "depends_on": case.get("depends_on"), "lang": case.get("lang"),
        "source": case.get("source"), "prompt": case["prompt"],
        "fixtures": [{"path": f["path"], "src": f.get("src"), "sha256": sha256_bytes(fixture_bytes(f, fixtures_dir))}
                     for f in case.get("fixtures", [])],
        "assertions": [{k: a[k] for k in ("id", "type", "neutral", "question", "desc") if k in a}
                       for a in case["assertions"]],
    }


def identity_fields(case_id: str, chash: str | None, model: str, adapter: str, adapter_version, effort: str,
                    skill_hash, judge, vision_judge, arm: str, rep: int) -> dict:
    return {"case_id": case_id, "case_hash": chash, "model": model, "provider": PROVIDERS.get(adapter, adapter),
            "adapter": adapter, "adapter_version": adapter_version, "effort": effort,
            "skill_hash": skill_hash if arm == "skill" else None, "judge": judge, "vision_judge": vision_judge,
            "arm": arm, "rep": rep}


def keys_for(ident: dict) -> tuple[str, str]:
    """(run_key, experiment_key): all fields / all but case_id, case_hash and rep."""
    exp = {k: v for k, v in ident.items() if k not in ("case_id", "case_hash", "rep")}
    return sha256_text(canonical(ident)), sha256_text(canonical(exp))


def run_identity(rec: dict, config: dict, entries: dict[str, dict]) -> dict:
    """identity / run_key / experiment_key of a run record: the runner's own when present, else derived with the
    same definition (adapter_version and skill_hash are unknown for those older records -> null)."""
    if rec.get("identity") and rec.get("run_key") and rec.get("experiment_key"):
        return {"identity": rec["identity"], "run_key": rec["run_key"], "experiment_key": rec["experiment_key"],
                "identity_source": "runner"}
    entry = entries.get(rec["case"])
    judge = None if config.get("no_judge") else ((rec.get("judge") or {}).get("model") or config.get("judge"))
    vision = None if config.get("no_judge") else ((rec.get("vision") or {}).get("model") or config.get("vision_judge"))
    ident = identity_fields(rec["case"], entry["case_hash"] if entry else None, rec["model"], rec["adapter"],
                            None, rec["effort"], None, judge, vision, rec["arm"], int(rec.get("rep") or 1))
    run_key, exp_key = keys_for(ident)
    return {"identity": ident, "run_key": run_key, "experiment_key": exp_key, "identity_source": "derived"}


# ============================================================ loading a results dir

def load_entries(results_dir: Path, cases_path: Path = DEFAULT_CASES,
                 fixtures_dir: Path = FIXTURES_DIR) -> dict[str, dict]:
    """case_id -> dataset entry: dataset.json of the results dir first, the cases file for the rest."""
    out: dict[str, dict] = {}
    for c in read_cases(cases_path):
        try:
            out[c["id"]] = dataset_entry(c, fixtures_dir)
        except OSError:     # a src fixture missing on this machine
            continue
    ds = results_dir / "dataset.json"
    if ds.is_file():
        for e in json.loads(ds.read_text()).get("items", []):
            out[e["case_id"]] = e
    return out


def read_cases(cases_path: Path | None) -> list[dict]:
    """The cases file plus every *.json in the `cases/` dir next to it (each a list or {cases: [...]})."""
    if not cases_path:
        return []
    files = [Path(cases_path)] if Path(cases_path).is_file() else []
    extra = Path(cases_path).parent / "cases"
    if extra.is_dir():
        files += sorted(extra.glob("*.json"))
    out = []
    for f in files:
        doc = json.loads(f.read_text())
        out += doc if isinstance(doc, list) else doc.get("cases") or []
    return [c for c in out if isinstance(c, dict) and c.get("id")]


def load_runs(results_dir: Path) -> list[dict]:
    runs_dir = results_dir / "runs"
    if not runs_dir.is_dir():
        raise ExportError(f"{results_dir}: no runs/ directory (not a run_behavior_evals results dir?)")
    return [json.loads(p.read_text()) for p in sorted(runs_dir.glob("*.json"))]


def load_results(results_dir: Path, cases_path: Path = DEFAULT_CASES, fixtures_dir: Path = FIXTURES_DIR) -> dict:
    """Everything the exporters need, keyed and normalised; no network."""
    config = json.loads((results_dir / "config.json").read_text()) if (results_dir / "config.json").is_file() else {}
    entries = load_entries(results_dir, cases_path, fixtures_dir)
    runs, skipped, unknown = [], [], []
    for rec in load_runs(results_dir):
        if rec.get("skipped"):
            skipped.append(rec["run_id"])
            continue
        if rec.get("case") not in entries and not rec.get("identity"):
            unknown.append(rec["run_id"])
            continue
        ids = run_identity(rec, config, entries)
        runs.append({**ids, "rec": rec})
    used = {}
    for r in runs:
        cid, chash = r["identity"]["case_id"], r["identity"]["case_hash"]
        entry = entries.get(cid)
        if entry is None:
            unknown.append(r["rec"]["run_id"])
            continue
        if chash and chash != entry["case_hash"]:
            r["ran_case_hash"] = chash          # the case changed since this run; link to the current item
        r["entry"] = entry
        used[cid] = entry
    runs = [r for r in runs if "entry" in r]
    return {"config": config, "entries": used, "runs": runs, "skipped": skipped, "unknown": unknown}


# ============================================================ naming and ids

def item_id(dataset_name: str, entry: dict) -> str:
    prefix = SKILL_NAME if dataset_name == DEFAULT_DATASET else dataset_name
    return f"{prefix}:{entry['case_id']}@{entry['case_hash'][:12]}"[:255]


def model_short(model: str) -> str:
    return model.split("/")[-1]


def experiment_name(ident: dict) -> str:
    parts = [model_short(ident["model"]), ident["effort"], ident["arm"]]
    if ident["arm"] == "skill":
        parts.append(ident["skill_hash"][:8] if ident.get("skill_hash") else "skill-unknown")
    return " · ".join(parts)


def experiment_description(ident: dict) -> str:
    sk = ident.get("skill_hash")
    return (f"tui-design behavior evals: {ident['model']} via {ident['adapter']} ({ident['provider']}), "
            f"effort {ident['effort']}, arm {ident['arm']}"
            + (f", skill {sk[:12]}" if sk else (", skill version unknown" if ident["arm"] == "skill" else ""))
            + f", judge {ident.get('judge') or 'none'}"
            + (f", vision judge {ident['vision_judge']}" if ident.get("vision_judge") else ""))


def experiment_metadata(r: dict, results_dir_name: str) -> dict:
    ident = r["identity"]
    md = {k: v for k, v in ident.items() if k not in ("case_id", "case_hash", "rep")}
    md.update({"experiment_key": r["experiment_key"], "identity_source": r["identity_source"],
               "skill": SKILL_NAME, "results_dir": results_dir_name})
    return md


def lf_run_name(r: dict) -> str:
    return f"{experiment_name(r['identity'])} · {r['experiment_key'][:8]}"


def hex_id(kind: str, key: str, n: int) -> str:
    return sha256_text(f"{kind}:{key}")[:n]


def trace_id(run_key: str) -> str:
    return hex_id("trace", run_key, 32)


def span_id(run_key: str, kind: str = "run") -> str:
    return hex_id(f"span-{kind}", run_key, 16)


def score_id(run_key: str, name: str) -> str:
    return hex_id(f"score:{name}", run_key, 32)


def truncate(s, n: int) -> str:
    s = "" if s is None else str(s)
    return s if len(s) <= n else s[: n - 15] + " …[truncated]"


# ============================================================ run facts shared by both systems

def run_times(rec: dict) -> tuple[float, float]:
    """(start, end) epoch seconds: started_at is local time without zone; end = start + wall_s."""
    try:
        start = time.mktime(time.strptime(rec["started_at"], "%Y-%m-%dT%H:%M:%S"))
    except (KeyError, ValueError, TypeError):
        start = 0.0
    return start, start + float(rec.get("wall_s") or 0)


def iso(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def tokens_total(rec: dict) -> int:
    t = rec.get("tokens") or {}
    return int(sum(float(t.get(k) or 0) for k in ("input", "cached", "cache_write", "output")))


def graded(rec: dict) -> list[dict]:
    """Assertions with a verdict; none for an errored run (excluded from pass rates by design)."""
    if rec.get("error"):
        return []
    return [a for a in rec.get("assertions", []) if a.get("passed") is not None]


def pass_rate(rec: dict) -> float | None:
    g = graded(rec)
    return (sum(1 for a in g if a["passed"]) / len(g)) if g else None


def item_input(entry: dict) -> dict:
    return {"prompt": entry["prompt"], "fixtures": [f["path"] for f in entry.get("fixtures", [])],
            "case_id": entry["case_id"]}


def item_expected(entry: dict) -> list[dict]:
    return [{k: a[k] for k in ("id", "type", "neutral", "question", "desc", "pattern") if k in a}
            for a in entry.get("assertions", [])]


def item_metadata(entry: dict) -> dict:
    return {"case_id": entry["case_id"], "case_hash": entry["case_hash"], "area": entry.get("area"),
            "tags": entry.get("tags", []), "origin": entry.get("source"), "lang": entry.get("lang"),
            "depends_on": entry.get("depends_on"), "skill": SKILL_NAME}


def run_metadata(r: dict) -> dict:
    rec = r["rec"]
    md = dict(r["identity"])
    md.update({"run_key": r["run_key"], "experiment_key": r["experiment_key"], "run_id": rec["run_id"],
               "identity_source": r["identity_source"], "area": r["entry"].get("area"),
               "tokens": rec.get("tokens"), "tokens_total": tokens_total(rec), "cost_usd": rec.get("cost_usd"),
               "cost_basis": rec.get("cost_basis"), "wall_s": rec.get("wall_s"), "tool_calls": rec.get("tool_calls"),
               "skill_loaded": rec.get("skill_loaded"), "error": rec.get("error"), "pass_rate": pass_rate(rec),
               "judge_cost_usd": (rec.get("judge") or {}).get("cost_usd"),
               "vision_cost_usd": (rec.get("vision") or {}).get("cost_usd")})
    if r.get("ran_case_hash"):
        md["ran_case_hash"] = r["ran_case_hash"]
    if rec.get("graded_case_hash"):
        md["graded_case_hash"] = rec["graded_case_hash"]
    return md


def run_output(rec: dict) -> dict:
    return {"final_answer": truncate(rec.get("final_answer"), ANSWER_MAX),
            "files": [f"{f.get('path')} ({f.get('status')})" for f in rec.get("files") or []],
            "tokens": rec.get("tokens"), "cost_usd": rec.get("cost_usd"), "wall_s": rec.get("wall_s"),
            "tool_calls": rec.get("tool_calls"), "skill_loaded": rec.get("skill_loaded")}


# ============================================================ payload builders (pure)

def lf_item_payload(dataset_name: str, entry: dict) -> dict:
    return {"datasetName": dataset_name, "id": item_id(dataset_name, entry), "input": item_input(entry),
            "expectedOutput": item_expected(entry), "metadata": item_metadata(entry)}


def lf_scores(r: dict) -> list[dict]:
    """Per-assertion BOOLEAN scores + pass_rate, cost_usd, tokens_total (NUMERIC) and skill_loaded (BOOLEAN)."""
    rec, tid = r["rec"], trace_id(r["run_key"])
    base = {"traceId": tid, "environment": LF_ENVIRONMENT}
    out = []
    for a in graded(rec):
        out.append({**base, "id": score_id(r["run_key"], a["id"]), "name": a["id"], "value": 1 if a["passed"] else 0,
                    "dataType": "BOOLEAN", "comment": truncate(a.get("detail"), COMMENT_MAX),
                    "metadata": {"type": "judge" if a.get("kind") in MODEL_KINDS else "program",
                                 "kind": a.get("kind"), "assertion_type": a.get("type"),
                                 "neutral": a.get("neutral", True), "area": r["entry"].get("area"),
                                 "case_id": r["identity"]["case_id"]}})
    rate = pass_rate(rec)
    if rate is not None:
        g = graded(rec)
        out.append({**base, "id": score_id(r["run_key"], "pass_rate"), "name": "pass_rate", "value": rate,
                    "dataType": "NUMERIC", "comment": f"{sum(1 for a in g if a['passed'])}/{len(g)} graded assertions"})
    if rec.get("cost_usd") is not None:
        out.append({**base, "id": score_id(r["run_key"], "cost_usd"), "name": "cost_usd",
                    "value": float(rec["cost_usd"]), "dataType": "NUMERIC", "comment": rec.get("cost_basis")})
    if rec.get("tokens"):
        out.append({**base, "id": score_id(r["run_key"], "tokens_total"), "name": "tokens_total",
                    "value": tokens_total(rec), "dataType": "NUMERIC"})
    if rec.get("skill_loaded") is not None:
        out.append({**base, "id": score_id(r["run_key"], "skill_loaded"), "name": "skill_loaded",
                    "value": 1 if rec["skill_loaded"] else 0, "dataType": "BOOLEAN"})
    return out


def _otel_value(v) -> dict:
    if isinstance(v, bool):
        return {"boolValue": v}
    if isinstance(v, int):
        return {"intValue": str(v)}
    if isinstance(v, float):
        return {"doubleValue": v}
    if isinstance(v, list):
        return {"arrayValue": {"values": [_otel_value(x) for x in v]}}
    return {"stringValue": v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)}


def _flat(prefix: str, md: dict) -> dict:
    """Langfuse reads `<prefix>.<key>` attributes as metadata keys; values as strings like the SDK sends them."""
    out = {}
    for k, v in md.items():
        if v is None:
            continue
        out[f"{prefix}.{k}"] = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    return out


def lf_spans(r: dict, run_name: str, dataset_id: str, experiment_id: str, dataset_name: str,
             results_dir_name: str) -> list[dict]:
    """OTLP/JSON spans of one run: a root span (the experiment item) and a generation child with usage and cost."""
    rec, entry = r["rec"], r["entry"]
    tid, root, gen = trace_id(r["run_key"]), span_id(r["run_key"]), span_id(r["run_key"], "gen")
    start, end = run_times(rec)
    inp = json.dumps(item_input(entry), ensure_ascii=False)
    out = truncate(rec.get("final_answer"), ANSWER_MAX)
    err = rec.get("error")
    exp_attrs = {
        "langfuse.environment": LF_ENVIRONMENT,
        "langfuse.experiment.id": experiment_id,
        "langfuse.experiment.name": run_name,
        "langfuse.experiment.description": experiment_description(r["identity"]),
        "langfuse.experiment.dataset.id": dataset_id,
        "langfuse.experiment.item.id": item_id(dataset_name, entry),
        "langfuse.experiment.item.root_observation_id": root,
        "langfuse.experiment.item.expected_output": json.dumps(item_expected(entry), ensure_ascii=False),
        **_flat("langfuse.experiment.metadata", experiment_metadata(r, results_dir_name)),
        **_flat("langfuse.experiment.item.metadata", item_metadata(entry)),
    }
    root_attrs = {
        **exp_attrs,
        "langfuse.trace.name": f"{entry['case_id']} · {r['identity']['arm']}",
        "langfuse.trace.input": inp, "langfuse.trace.output": out,
        "langfuse.trace.tags": [SKILL_NAME, "behavior-eval", r["identity"]["arm"], model_short(r["identity"]["model"])],
        "langfuse.observation.type": "span", "langfuse.observation.input": inp, "langfuse.observation.output": out,
        **_flat("langfuse.trace.metadata", run_metadata(r)),
    }
    if err:
        root_attrs.update({"langfuse.observation.level": "ERROR", "langfuse.observation.status_message": str(err)})
    t = rec.get("tokens") or {}
    usage = {k2: int(t.get(k1) or 0) for k1, k2 in (("input", "input"), ("cached", "input_cached"),
                                                     ("cache_write", "input_cache_write"), ("output", "output"),
                                                     ("reasoning", "output_reasoning")) if t.get(k1)}
    gen_attrs = {**exp_attrs, "langfuse.observation.type": "generation",
                 "langfuse.observation.model.name": r["identity"]["model"],
                 "langfuse.observation.model.parameters": json.dumps({"effort": r["identity"]["effort"]}),
                 "langfuse.observation.output": out}
    if usage:
        gen_attrs["langfuse.observation.usage_details"] = json.dumps(usage)
    if rec.get("cost_usd") is not None:
        gen_attrs["langfuse.observation.cost_details"] = json.dumps({"total": float(rec["cost_usd"])})
    if err:
        gen_attrs.update({"langfuse.observation.level": "ERROR", "langfuse.observation.status_message": str(err)})

    def span(sid, parent, name, attrs):
        s = {"traceId": tid, "spanId": sid, "name": name, "kind": 1,
             "startTimeUnixNano": str(int(start * 1e9)), "endTimeUnixNano": str(int(end * 1e9)),
             "attributes": [{"key": k, "value": _otel_value(v)} for k, v in attrs.items()],
             "status": {"code": 2, "message": str(err)} if err else {"code": 1}}
        if parent:
            s["parentSpanId"] = parent
        return s
    return [span(root, None, "experiment-item-run", root_attrs),
            span(gen, root, f"agent {r['identity']['adapter']}", gen_attrs)]


def otlp_body(spans: list[dict]) -> dict:
    return {"resourceSpans": [{"resource": {"attributes": [
        {"key": "service.name", "value": {"stringValue": "tui-design-evals"}}]},
        "scopeSpans": [{"scope": {"name": "langfuse-sdk", "version": "export_results"}, "spans": spans}]}]}


def px_example(entry: dict, dataset_name: str) -> dict:
    return {"id": item_id(dataset_name, entry), "input": item_input(entry),
            "output": {"assertions": item_expected(entry)}, "metadata": item_metadata(entry)}


def px_run_payload(r: dict, example_node_id: str) -> dict:
    rec = r["rec"]
    start, end = run_times(rec)
    return {"dataset_example_id": example_node_id, "output": run_output(rec),
            "repetition_number": int(r["identity"]["rep"] or 1), "start_time": iso(start), "end_time": iso(end),
            "error": rec.get("error") or None}


def px_evaluations(r: dict, run_id: str) -> list[dict]:
    rec = r["rec"]
    _, end = run_times(rec)
    out = []
    for a in graded(rec):
        out.append({"experiment_run_id": run_id, "name": a["id"],
                    "annotator_kind": "LLM" if a.get("kind") in MODEL_KINDS else "CODE",
                    "start_time": iso(end), "end_time": iso(end),
                    "result": {"score": 1.0 if a["passed"] else 0.0, "label": "pass" if a["passed"] else "fail",
                               "explanation": truncate(a.get("detail"), COMMENT_MAX)},
                    "metadata": {"kind": a.get("kind"), "assertion_type": a.get("type"),
                                 "neutral": a.get("neutral", True), "area": r["entry"].get("area"),
                                 "case_id": r["identity"]["case_id"]}})
    rate = pass_rate(rec)
    if rate is not None:
        g = graded(rec)
        out.append({"experiment_run_id": run_id, "name": "pass_rate", "annotator_kind": "CODE",
                    "start_time": iso(end), "end_time": iso(end),
                    "result": {"score": rate, "label": None,
                               "explanation": f"{sum(1 for a in g if a['passed'])}/{len(g)} graded assertions"}})
    return out


# ============================================================ state file

def state_path(results_dir: Path) -> Path:
    return results_dir / STATE_FILE


def load_state(results_dir: Path) -> dict:
    p = state_path(results_dir)
    if p.is_file():
        try:
            st = json.loads(p.read_text())
            if isinstance(st, dict):
                st.setdefault("version", 1)
                st.setdefault("targets", {})
                return st
        except json.JSONDecodeError:
            pass
    return {"version": 1, "targets": {}}


def save_state(results_dir: Path, state: dict, secrets: list[str]) -> None:
    text = json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if any(s in text for s in secrets):          # belt and braces: the state never holds credentials
        raise ExportError("refusing to write export-state.json: it would contain a secret value")
    tmp = state_path(results_dir).with_suffix(".json.tmp")
    tmp.write_text(text)
    tmp.replace(state_path(results_dir))


def target_state(state: dict, system: str, base_url: str, dataset_name: str) -> dict:
    key = f"{system}|{base_url.rstrip('/')}|{dataset_name}"
    t = state["targets"].setdefault(key, {})
    for k in ("dataset", "experiments", "runs", "items"):
        t.setdefault(k, {})
    return t


# ============================================================ HTTP

class Http:
    def __init__(self, base_url: str, auth: str, secrets: list[str], insecure: bool = False, timeout: int = 60):
        self.base = base_url.rstrip("/")
        self.auth = auth
        self.secrets = secrets
        self.timeout = timeout
        self.ctx = ssl._create_unverified_context() if insecure else ssl.create_default_context()
        self.calls = 0

    def request(self, method: str, path: str, body=None, query: dict | None = None, headers: dict | None = None,
                ok: tuple[int, ...] = ()):
        url = self.base + path
        if query:
            url += "?" + urllib.parse.urlencode({k: v for k, v in query.items() if v is not None}, doseq=True)
        global _PAYLOAD_SECRETS
        if _PAYLOAD_SECRETS is None:
            _PAYLOAD_SECRETS = payload_secrets()
        data = redact_named(json.dumps(body, ensure_ascii=False), _PAYLOAD_SECRETS).encode() if body is not None else None
        h = {"Authorization": self.auth, "Accept": "application/json"}
        if data is not None:
            h["Content-Type"] = "application/json"
        h.update(headers or {})
        req = urllib.request.Request(url, data=data, method=method, headers=h)
        self.calls += 1
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=self.ctx) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                status = resp.status
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            e.close()
            if e.code in ok:
                return e.code, _json_or_text(raw)
            raise ExportError(f"{method} {self.base}{path} -> HTTP {e.code}: {redact(raw[:500], self.secrets)}") from None
        except urllib.error.URLError as e:
            reason = e.reason
            if isinstance(reason, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(reason):
                raise ExportError(f"TLS certificate verification failed for {self.base} ({redact(reason, self.secrets)}). "
                                  "Fix the certificate or trust store; or re-run with --insecure to skip verification "
                                  "for this export (not recommended).") from None
            raise ExportError(f"{method} {self.base}{path}: {redact(reason, self.secrets)}") from None
        except (TimeoutError, OSError) as e:
            raise ExportError(f"{method} {self.base}{path}: {redact(e, self.secrets)}") from None
        return status, _json_or_text(raw)


def _json_or_text(raw: str):
    try:
        return json.loads(raw) if raw else None
    except json.JSONDecodeError:
        return raw


def _q(s: str) -> str:
    return urllib.parse.quote(s, safe="")


# ============================================================ Langfuse

def stale_experiment_keys(data: dict, st: dict) -> set[str]:
    """Experiments of this dir that hold a run no longer in its results (re-run under a new identity, removed, or
    contaminated and replaced). Neither platform deletes one run of an experiment, so --prune drops the experiment
    and the export recreates it from the current runs."""
    live = {r["run_key"] for r in data["runs"]}
    by_id = {e.get("id") or e.get("dataset_run_id"): k for k, e in st.get("experiments", {}).items()}
    return {rs.get("experiment_key") or by_id.get(rs.get("experiment_id"))
            for rk, rs in st.get("runs", {}).items() if rk not in live} - {None}


def forget_experiment(st: dict, ek: str) -> tuple[dict, dict[str, dict]]:
    """Remove an experiment and its runs from the state; return them, runs keyed by run_key (for remote deletes)."""
    exp = st.get("experiments", {}).pop(ek, None) or {}
    ids = {exp.get("id"), exp.get("dataset_run_id")} - {None}
    keys = [rk for rk, rs in st.get("runs", {}).items()
            if rs.get("experiment_key") == ek or rs.get("experiment_id") in ids]
    return exp, {rk: st["runs"].pop(rk) for rk in keys}


class LangfuseExporter:
    name = "langfuse"

    def __init__(self, cfg: dict, secrets: list[str], insecure: bool):
        missing = [k for k in ("LANGFUSE_BASE_URL", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY") if not cfg.get(k)]
        if missing:
            raise ExportError(f"langfuse: missing {', '.join(missing)}")
        self.base = cfg["LANGFUSE_BASE_URL"].rstrip("/")
        self.http = Http(self.base, "Basic " + basic_token(cfg["LANGFUSE_PUBLIC_KEY"], cfg["LANGFUSE_SECRET_KEY"]),
                         secrets, insecure)

    def export(self, data: dict, dataset_name: str, st: dict, results_dir_name: str) -> dict:
        c = {"items_created": 0, "items_updated": 0, "items_unchanged": 0, "experiments": 0,
             "run_items_created": 0, "run_items_existing": 0, "traces_sent": 0, "scores_upserted": 0,
             "scores_deleted": 0, "errored_runs": 0}
        _, ds = self.http.request("POST", "/api/public/v2/datasets", {
            "name": dataset_name, "description": "tui-design skill behavior-eval cases: one item per case "
            "(input = prompt + fixtures, expected output = assertions)", "metadata": {"skill": SKILL_NAME}})
        st["dataset"] = {"name": dataset_name, "id": ds["id"], "project_id": ds.get("projectId")}
        existing = self._items(dataset_name)
        for cid, entry in sorted(data["entries"].items()):
            p = lf_item_payload(dataset_name, entry)
            cur = existing.get(p["id"])
            if cur and (cur.get("input"), cur.get("expectedOutput"), cur.get("metadata")) == \
                    (p["input"], p["expectedOutput"], p["metadata"]) and cur.get("status", "ACTIVE") == "ACTIVE":
                c["items_unchanged"] += 1
            else:
                self.http.request("POST", "/api/public/dataset-items", p)
                c["items_created" if cur is None else "items_updated"] += 1
            st["items"][p["id"]] = cid

        by_exp: dict[str, list[dict]] = {}
        for r in data["runs"]:
            by_exp.setdefault(r["experiment_key"], []).append(r)
        for ek, runs in sorted(by_exp.items()):
            run_name = lf_run_name(runs[0])
            exp_st = st["experiments"].setdefault(ek, {})
            exp_st["run_name"] = run_name
            md = experiment_metadata(runs[0], results_dir_name)
            spans = []
            for r in runs:
                rs = st["runs"].setdefault(r["run_key"], {})
                rs.update({"trace_id": trace_id(r["run_key"]), "observation_id": span_id(r["run_key"]),
                           "run_id": r["rec"]["run_id"], "experiment_key": ek})
                if rs.get("run_item_id") and exp_st.get("dataset_run_id"):
                    c["run_items_existing"] += 1
                else:
                    _, ri = self.http.request("POST", "/api/public/dataset-run-items", {
                        "runName": run_name, "runDescription": experiment_description(r["identity"]),
                        "metadata": md, "datasetItemId": item_id(dataset_name, r["entry"]),
                        "traceId": trace_id(r["run_key"]), "observationId": span_id(r["run_key"]),
                        "createdAt": iso(run_times(r["rec"])[0])})
                    rs["run_item_id"] = ri["id"]
                    exp_st["dataset_run_id"] = ri["datasetRunId"]
                    c["run_items_created"] += 1
                spans += lf_spans(r, run_name, ds["id"], exp_st["dataset_run_id"], dataset_name, results_dir_name)
                c["errored_runs"] += 1 if r["rec"].get("error") else 0
            for i in range(0, len(spans), 20):
                self.http.request("POST", "/api/public/otel/v1/traces", otlp_body(spans[i:i + 20]),
                                  headers={"x-langfuse-ingestion-version": "4"})
            c["traces_sent"] += len(runs)
            c["experiments"] += 1
            for r in runs:
                rs = st["runs"][r["run_key"]]
                scores = lf_scores(r)
                for s in scores:
                    self.http.request("POST", "/api/public/scores", s)
                c["scores_upserted"] += len(scores)
                new_ids = sorted(s["id"] for s in scores)
                for stale in sorted(set(rs.get("score_ids", [])) - set(new_ids)):   # assertion gone after a regrade
                    self.http.request("DELETE", f"/api/public/scores/{_q(stale)}", ok=(404,))
                    c["scores_deleted"] += 1
                rs["score_ids"] = new_ids
        return c

    def _items(self, dataset_name: str) -> dict[str, dict]:
        out, page = {}, 1
        while True:
            _, res = self.http.request("GET", "/api/public/dataset-items",
                                       query={"datasetName": dataset_name, "page": page, "limit": 100})
            for it in res.get("data", []):
                out[it["id"]] = it
            if page >= int((res.get("meta") or {}).get("totalPages") or 1):
                return out
            page += 1

    def urls(self, st: dict) -> list[str]:
        ds = st.get("dataset") or {}
        pid, did = ds.get("project_id"), ds.get("id")
        if not (pid and did):
            return []
        out = [f"dataset: {self.base}/project/{pid}/datasets/{did}",
               f"experiments: {self.base}/project/{pid}/experiments"]
        runs = [e["dataset_run_id"] for e in st["experiments"].values() if e.get("dataset_run_id")]
        if runs:
            out.append(f"compare: {self.base}/project/{pid}/datasets/{did}/compare?" +
                       "&".join(f"runs={_q(x)}" for x in sorted(set(runs))))
        return out

    def drop_experiment(self, dataset_name: str, st: dict, ek: str, live: set[str]) -> None:
        exp, runs = forget_experiment(st, ek)
        if exp.get("run_name"):
            self.http.request("DELETE", f"/api/public/datasets/{_q(dataset_name)}/runs/{_q(exp['run_name'])}",
                              ok=(404,))
        for rk, rs in runs.items():      # only stale traces: a live run's trace id is re-sent at once, and Langfuse
            if rk not in live and rs.get("trace_id"):   # deletes asynchronously, so it could remove the new one too
                self.http.request("DELETE", f"/api/public/traces/{_q(rs['trace_id'])}", ok=(404,))

    def verify(self, data: dict, dataset_name: str, st: dict) -> list[str]:
        items = self._items(dataset_name)
        want_items = {item_id(dataset_name, e) for e in data["entries"].values()}
        lines = [f"dataset items: {len(items)} in dataset, {len(want_items & set(items))}/{len(want_items)} "
                 "of this dir present"]
        since = iso(min(run_times(r["rec"])[0] for r in data["runs"]) - 86400) if data["runs"] else "2000-01-01T00:00:00Z"
        for ek, e in sorted(st["experiments"].items()):
            n_runs = sum(1 for r in data["runs"] if r["experiment_key"] == ek)
            _, res = self.http.request("GET", "/api/public/experiment-items",
                                       query={"fromStartTime": since, "experimentId": e.get("dataset_run_id"),
                                              "limit": 100})
            got = res.get("data", [])
            traces = {x["traceId"] for x in got}
            lines.append(f"experiment {e['run_name']!r}: {len(got)} items ({len(traces)} distinct traces), "
                         f"expected {n_runs}")
        n_scores, want = 0, 0
        for r in data["runs"]:
            _, res = self.http.request("GET", "/api/public/v3/scores",
                                       query={"traceId": trace_id(r["run_key"]), "limit": 100})
            n_scores += len(res.get("data", []))
            want += len(lf_scores(r))
        lines.append(f"scores on this dir's traces: {n_scores}, expected {want} (score reads may lag a few minutes)")
        return lines


# ============================================================ Phoenix

class PhoenixExporter:
    name = "phoenix"

    def __init__(self, cfg: dict, secrets: list[str], insecure: bool):
        missing = [k for k in ("PHOENIX_BASE_URL", "PHOENIX_API_KEY") if not cfg.get(k)]
        if missing:
            raise ExportError(f"phoenix: missing {', '.join(missing)}")
        self.base = cfg["PHOENIX_BASE_URL"].rstrip("/")
        self.http = Http(self.base, "Bearer " + cfg["PHOENIX_API_KEY"], secrets, insecure)

    def _dataset(self, name: str) -> dict | None:
        _, res = self.http.request("GET", "/v1/datasets", query={"name": name, "limit": 100})
        for d in res.get("data", []):
            if d["name"] == name:
                return d
        return None

    def _examples(self, dataset_id: str) -> dict[str, dict]:
        _, res = self.http.request("GET", f"/v1/datasets/{_q(dataset_id)}/examples")
        return {e["id"]: e for e in res["data"]["examples"]}

    def _experiments(self, dataset_id: str) -> list[dict]:
        out, cursor = [], None
        while True:
            _, res = self.http.request("GET", f"/v1/datasets/{_q(dataset_id)}/experiments",
                                       query={"limit": 100, "cursor": cursor})
            out += res.get("data", [])
            cursor = res.get("next_cursor")
            if not cursor:
                return out

    def _runs(self, experiment_id: str) -> list[dict]:
        out, cursor = [], None
        while True:
            _, res = self.http.request("GET", f"/v1/experiments/{_q(experiment_id)}/runs",
                                       query={"limit": 100, "cursor": cursor})
            out += res.get("data", [])
            cursor = res.get("next_cursor")
            if not cursor:
                return out

    def _upload(self, action: str, name: str, examples: list[dict]) -> dict:
        body = {"action": action, "name": name, "inputs": [e["input"] for e in examples],
                "outputs": [e["output"] for e in examples], "metadata": [e["metadata"] for e in examples],
                "example_ids": [e["id"] for e in examples]}
        if action == "create":
            body["description"] = "tui-design skill behavior-eval cases: one example per case"
        _, res = self.http.request("POST", "/v1/datasets/upload", body, query={"sync": "true"})
        return res["data"]

    def export(self, data: dict, dataset_name: str, st: dict, results_dir_name: str) -> dict:
        c = {"examples_created": 0, "examples_updated": 0, "examples_unchanged": 0, "experiments_created": 0,
             "experiments_existing": 0, "runs_created": 0, "runs_updated": 0, "runs_existing": 0, "evaluations_upserted": 0, "errored_runs": 0}
        wanted = [px_example(e, dataset_name) for _, e in sorted(data["entries"].items())]
        ds = self._dataset(dataset_name)
        if ds is None:
            res = self._upload("create", dataset_name, wanted)
            c["examples_created"] = res["num_created_examples"]
            dataset_id = res["dataset_id"]
        else:
            dataset_id = ds["id"]
            have = self._examples(dataset_id)
            todo = []
            for e in wanted:
                cur = have.get(e["id"])
                if cur and (cur["input"], cur["output"], cur["metadata"]) == (e["input"], e["output"], e["metadata"]):
                    c["examples_unchanged"] += 1
                else:
                    todo.append(e)
                    c["examples_created" if cur is None else "examples_updated"] += 1
            if todo:
                self._upload("append", dataset_name, todo)
        st["dataset"] = {"name": dataset_name, "id": dataset_id}
        node = {eid: e["node_id"] for eid, e in self._examples(dataset_id).items()}

        remote = {(x.get("metadata") or {}).get("experiment_key"): x for x in self._experiments(dataset_id)}
        by_exp: dict[str, list[dict]] = {}
        for r in data["runs"]:
            by_exp.setdefault(r["experiment_key"], []).append(r)
        for ek, runs in sorted(by_exp.items()):
            md = experiment_metadata(runs[0], results_dir_name)
            name = experiment_name(runs[0]["identity"])
            reps = max(int(r["identity"]["rep"] or 1) for r in runs)
            exp = remote.get(ek)
            if exp is None:
                _, res = self.http.request("POST", f"/v1/datasets/{_q(dataset_id)}/experiments", {
                    "name": name, "description": experiment_description(runs[0]["identity"]),
                    "metadata": md, "repetitions": reps})
                exp = res["data"]
                c["experiments_created"] += 1
            else:
                c["experiments_existing"] += 1
                if exp.get("metadata") != md or exp.get("name") != name:
                    self.http.request("PATCH", f"/v1/experiments/{_q(exp['id'])}", {
                        "name": name, "description": experiment_description(runs[0]["identity"]), "metadata": md})
            st["experiments"][ek] = {"id": exp["id"], "name": name}
            have_runs = {(x["dataset_example_id"], x["repetition_number"]): x for x in self._runs(exp["id"])}
            for r in runs:
                ex_id = item_id(dataset_name, r["entry"])
                payload = px_run_payload(r, node[ex_id])
                cur = have_runs.get((payload["dataset_example_id"], payload["repetition_number"]))
                if cur and not cur.get("error"):
                    run_id = cur["id"]      # a successful run cannot be updated (409); its evaluations can
                    c["runs_existing"] += 1
                else:                       # new, or replacing an errored run (allowed upsert)
                    _, res = self.http.request("POST", f"/v1/experiments/{_q(exp['id'])}/runs", payload)
                    run_id = res["data"]["id"]
                    c["runs_created" if cur is None else "runs_updated"] += 1
                c["errored_runs"] += 1 if r["rec"].get("error") else 0
                evals = {}
                for ev in px_evaluations(r, run_id):
                    _, er = self.http.request("POST", "/v1/experiment_evaluations", ev)
                    evals[ev["name"]] = er["data"]["id"]
                c["evaluations_upserted"] += len(evals)
                st["runs"][r["run_key"]] = {"experiment_id": exp["id"], "run_id": run_id, "example_id": ex_id,
                                           "run_name": r["rec"]["run_id"], "evaluation_ids": evals}
        return c

    def drop_experiment(self, dataset_name: str, st: dict, ek: str, live: set[str]) -> None:
        exp, _ = forget_experiment(st, ek)
        if exp.get("id"):
            self.http.request("DELETE", f"/v1/experiments/{_q(exp['id'])}", ok=(404,))

    def urls(self, st: dict) -> list[str]:
        did = (st.get("dataset") or {}).get("id")
        if not did:
            return []
        exps = sorted(e["id"] for e in st["experiments"].values())
        out = [f"dataset: {self.base}/datasets/{_q(did)}/examples",
               f"experiments: {self.base}/datasets/{_q(did)}/experiments"]
        if exps:
            out.append(f"compare: {self.base}/datasets/{_q(did)}/compare?" +
                       "&".join(f"experimentId={_q(x)}" for x in exps))
        return out

    def verify(self, data: dict, dataset_name: str, st: dict) -> list[str]:
        ds = self._dataset(dataset_name)
        if ds is None:
            return ["dataset missing"]
        ex = self._examples(ds["id"])
        want = {item_id(dataset_name, e) for e in data["entries"].values()}
        exps = self._experiments(ds["id"])
        keys = [(x.get("metadata") or {}).get("experiment_key") for x in exps]
        lines = [f"examples: {len(ex)} in dataset, {len(want & set(ex))}/{len(want)} of this dir present",
                 f"experiments: {len(exps)} on dataset; per experiment_key of this dir: "
                 + ", ".join(f"{k[:8]}={keys.count(k)}" for k in sorted(st['experiments']))]
        for ek, e in sorted(st["experiments"].items()):
            _, res = self.http.request("GET", f"/v1/experiments/{_q(e['id'])}/json")
            rows = res if isinstance(res, list) else []
            n_ann = sum(len(x.get("annotations") or []) for x in rows)
            want_runs = [r for r in data["runs"] if r["experiment_key"] == ek]
            want_ann = sum(len(px_evaluations(r, "x")) for r in want_runs)
            lines.append(f"experiment {e['name']!r}: {len(rows)} runs (expected {len(want_runs)}), "
                         f"{n_ann} evaluations (expected {want_ann})")
        return lines


# ============================================================ CLI

def plan(data: dict, dataset_name: str, state: dict, systems: list[str], cfg: dict) -> list[str]:
    """What an export would do, from the results dir and the state file only (no network)."""
    out = [f"dataset {dataset_name!r}: {len(data['entries'])} item(s)/example(s): "
           + ", ".join(item_id(dataset_name, e) for _, e in sorted(data["entries"].items()))]
    by_exp: dict[str, list[dict]] = {}
    for r in data["runs"]:
        by_exp.setdefault(r["experiment_key"], []).append(r)
    for ek, runs in sorted(by_exp.items()):
        n_err = sum(1 for r in runs if r["rec"].get("error"))
        n_scores = sum(len(lf_scores(r)) for r in runs)
        n_evals = sum(len(px_evaluations(r, "x")) for r in runs)
        out.append(f"experiment {lf_run_name(runs[0])!r} ({runs[0]['identity_source']} identity): {len(runs)} run(s), "
                   f"{n_err} errored; langfuse scores {n_scores}, phoenix evaluations {n_evals}")
    for system in systems:
        base = cfg.get("LANGFUSE_BASE_URL" if system == "langfuse" else "PHOENIX_BASE_URL") or "<base url unset>"
        st = state["targets"].get(f"{system}|{base.rstrip('/')}|{dataset_name}")
        done = sum(1 for r in data["runs"] if st and r["run_key"] in st.get("runs", {}))
        out.append(f"{system} ({base}): {len(data['runs']) - done} run(s) new, {done} already exported "
                   "(would be updated in place)")
    if data["skipped"]:
        out.append(f"skipped runs (not exported): {len(data['skipped'])}")
    if data["unknown"]:
        out.append(f"runs whose case is unknown (not exported): {', '.join(data['unknown'])}")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results_dir", type=Path)
    ap.add_argument("--to", help="comma-separated: langfuse, phoenix (default: EVAL_EXPORT_TO from the environment or the env file; set it to the platforms you want on by default)")
    ap.add_argument("--dataset-name", default=DEFAULT_DATASET)
    ap.add_argument("--cases", type=Path, default=DEFAULT_CASES,
                    help="cases file used when the results dir has no dataset.json / identity fields")
    ap.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    ap.add_argument("--dry-run", action="store_true", help="print what would be exported; no network, no writes")
    ap.add_argument("--insecure", action="store_true", help="skip TLS certificate verification (not recommended)")
    ap.add_argument("--verify", action="store_true",
                    help="after exporting (or alone with --no-export), count remote items/runs/scores")
    ap.add_argument("--no-export", action="store_true", help="with --verify: only count, export nothing")
    ap.add_argument("--prune", action="store_true",
                    help="delete and recreate this dir's experiments that hold runs no longer in its results")
    args = ap.parse_args(argv)

    cfg = load_config(args.env_file)
    targets = args.to or os.environ.get("EVAL_EXPORT_TO") or cfg.get("EVAL_EXPORT_TO") or ""
    systems = [s.strip() for s in targets.split(",") if s.strip()]
    bad = set(systems) - {"langfuse", "phoenix"}
    if bad or not systems:
        ap.error("no export target: pass --to langfuse,phoenix or set EVAL_EXPORT_TO in the env file"
                 if not systems else f"unknown system(s) {sorted(bad)}; use langfuse and/or phoenix")
    print(f"export targets: {', '.join(systems)}" + ("" if args.to else " (from EVAL_EXPORT_TO)"))
    results_dir = args.results_dir.resolve()
    secrets = secrets_of(cfg)
    try:
        data = load_results(results_dir, args.cases)
        state = load_state(results_dir)
        if args.dry_run:
            print(f"dry run: {results_dir.name}: {len(data['runs'])} run(s) to export")
            for line in plan(data, args.dataset_name, state, systems, cfg):
                print("  " + line)
            return 0
        if not data["runs"]:
            raise ExportError("nothing to export (no non-skipped runs with a known case)")
        for system in systems:
            cls = LangfuseExporter if system == "langfuse" else PhoenixExporter
            ex = cls(cfg, secrets, args.insecure)
            st = target_state(state, system, ex.base, args.dataset_name)
            stale = stale_experiment_keys(data, st)
            if stale and not args.prune:
                print(f"{system}: {len(stale)} experiment(s) hold runs no longer in this dir; --prune recreates them")
            if not args.no_export:
                try:
                    if args.prune:
                        live = {r["run_key"] for r in data["runs"]}
                        for ek in sorted(stale):
                            ex.drop_experiment(args.dataset_name, st, ek, live)
                        print(f"{system}: pruned {len(stale)} experiment(s)")
                    counts = ex.export(data, args.dataset_name, st, results_dir.name)
                finally:
                    save_state(results_dir, state, secrets)      # keep what was created even on a failure
                print(f"{system}: " + ", ".join(f"{k} {v}" for k, v in counts.items()) +
                      f" ({ex.http.calls} requests)")
            for u in ex.urls(st):
                print(f"  {u}")
            if args.verify:
                for line in ex.verify(data, args.dataset_name, st):
                    print(f"  verify: {line}")
        return 0
    except ExportError as e:
        print(f"error: {redact(e, secrets)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
