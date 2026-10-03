#!/usr/bin/env python3
"""Behavior evaluation runner for the tui-design skill (stdlib only, Python >= 3.11 for tomllib).

Question answered: when the skill is loaded, does the agent behave better than the same model without it? Each
run is one (case, model, arm, rep) in a fresh temp workdir with the case's fixtures written in. Arm `skill`
installs a copy of the skill (without __pycache__/); arm `baseline` does not. After the agent
finishes, program assertions are checked on the workdir and the final answer, and judge assertions are answered
yes/no by a judge model in one call.

Configuration is data:
  evals/models.toml       models (adapter, CLI model string, effort, cost basis, prices), presets, judges and the
                          adapters' isolation settings. --list-models prints it; --models takes presets, ids and
                          ID@EFFORT.
  behavior-evals.json     the cases, plus every evals/cases/*.json (--cases-dir); --validate-cases checks them.
  evals/adapters/*.py     optional Python adapters for CLIs that need a real event parser (see README).

Adapters: omp (OpenRouter models), claude (Claude Code), codex (Codex CLI) and command (any CLI from an argv
template in models.toml). The prompt always reaches the agent through a file in the run's temp dir (stdin or a
{prompt_file} argument), never through argv, so a `pkill -f <word>` by one agent cannot match another's prompt.

Outputs in --out (default <results root>/<timestamp>/; results root = evals/runs/, gitignored;
--results-root or $EVAL_RESULTS_ROOT overrides): runs/<run-id>.json (+ .events.jsonl.gz, .stderr.txt, .files/),
summary.md and summary.json. --dry-run prints the matrix and a cost estimate (median and p90 token counts of
earlier results, --estimate-from) without calling any model.

Assertion phases: static program checks on the workdir and answer; executed checks (exec, tty_probe,
frame_match) that run commands on the agent's output in the workdir with a timeout, no network (sandbox-exec
when available) and private tmux sockets only; then the text judge and the vision judge (vision_rubric renders
.mock frames to PNG with the skill's own scripts and scores them on the visual-craft rubric).
"""

import argparse
import gzip
import hashlib
import json
import os
import re
import runpy
import shlex
import signal
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ImportError:  # pragma: no cover - Python < 3.11
    tomllib = None

EVALS_DIR = Path(__file__).resolve().parent
DEFAULT_CASES = EVALS_DIR / "behavior-evals.json"
DEFAULT_CASES_DIR = EVALS_DIR / "cases"
FIXTURES_DIR = EVALS_DIR / "fixtures"
DEFAULT_RESULTS_ROOT = EVALS_DIR / "runs"
DEFAULT_MODELS_FILE = EVALS_DIR / "models.toml"
PRICE_CACHE_FILE = EVALS_DIR / "prices-cache.json"
ADAPTERS_DIR = EVALS_DIR / "adapters"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"


def find_skill_dir(evals_dir: Path = EVALS_DIR) -> Path:
    """$EVAL_SKILL_DIR, else ../skills/tui-design next to evals/ (the repo layout), else the only
    ../skills/*/ with a SKILL.md."""
    if os.environ.get("EVAL_SKILL_DIR"):
        return Path(os.environ["EVAL_SKILL_DIR"]).expanduser().resolve()
    default = evals_dir.parent / "skills" / "tui-design"
    if (default / "SKILL.md").is_file():
        return default
    found = sorted(p.parent for p in (evals_dir.parent / "skills").glob("*/SKILL.md"))
    return found[0] if len(found) == 1 else default


def skill_name_of(skill_dir: Path) -> str:
    """`name:` from SKILL.md's frontmatter, else the directory name."""
    try:
        m = re.search(r"^name:\s*['\"]?([\w.-]+)", (skill_dir / "SKILL.md").read_text(), re.M)
    except OSError:
        m = None
    return m.group(1) if m else skill_dir.name


def default_results_dir(skill_dir: Path | None = None) -> Path:
    """evals/runs/ (gitignored), whichever skill is under test; --results-root or $EVAL_RESULTS_ROOT overrides."""
    return DEFAULT_RESULTS_ROOT


SKILL_DIR = find_skill_dir()
SKILL_NAME = skill_name_of(SKILL_DIR)
RESULTS_DIR = Path(os.environ["EVAL_RESULTS_ROOT"]).expanduser() if os.environ.get("EVAL_RESULTS_ROOT") \
    else default_results_dir(SKILL_DIR)


def configure_paths(skill_dir: Path | None = None, results_root: Path | None = None) -> None:
    """--skill-dir / --results-root: every function reads these globals at call time."""
    global SKILL_DIR, SKILL_NAME, RESULTS_DIR, _SKILL_INDEX
    if skill_dir:
        SKILL_DIR = Path(skill_dir).expanduser().resolve()
        SKILL_NAME = skill_name_of(SKILL_DIR)
        _SKILL_INDEX = None
        if not results_root and not os.environ.get("EVAL_RESULTS_ROOT"):
            RESULTS_DIR = default_results_dir(SKILL_DIR)
    if results_root:
        RESULTS_DIR = Path(results_root).expanduser().resolve()


AREAS = ("host", "frames", "review", "ambition", "data", "color", "keys", "lifecycle", "shell", "audit", "build",
         "archetypes")   # default skill areas; a cases file may declare more with a top-level "areas" list

ARMS = ("skill", "baseline")

# Directories in the workdir that are infrastructure, not agent output.
INFRA_DIRS = {".agents", ".claude", ".git", ".tmp", "__pycache__", ".codex", "node_modules", ".venv"}
TEXT_SUFFIXES = {".mock", ".md", ".txt", ".py", ".go", ".json", ".toml", ".ansi", ".tcss", ".css", ".ts",
                 ".tsx", ".js", ".rs", ".yaml", ".yml", ".html", ".sh", ".mod"}
MAX_COPY_BYTES = 2_000_000

# Executed assertions: no network (outbound IP denied; unix sockets for tmux stay allowed).
SANDBOX_PROFILE = "(version 1)(allow default)(deny network-outbound (remote ip))"
# [sandbox] in models.toml: more paths an agent may not read (other copies of the skill, your own skill dirs) and
# whether Spotlight (mdfind) is cut off: a baseline agent once found an old copy of the skill through it.
SANDBOX_DEFAULTS = {"deny_read": [], "deny_spotlight": True}


# ============================================================ cases

ASSERTION_TYPES = {
    "answer_regex": {"pattern"},
    "transcript_regex": {"pattern"},
    "hex_near": {"palette"},
    "mock_craft": {"glob"},
    "exec": {"cmd"},
    "tty_probe": {"cmd"},
    "frame_match": {"mock", "frame"},
    "vision_rubric": {"glob"},
    "answer_box_widths": set(),
    "file_glob": {"glob"},
    "file_regex": {"glob", "pattern"},
    "files_contain": {"strings"},
    "mock_lint": {"glob"},
    "mock_caps": {"glob"},
    "mock_variants": {"glob"},
    "hex_known": {"sources"},
    "fixture_unchanged": {"path"},
    "no_new_files": set(),
    "judge": {"question"},
}
ANSI_ESCAPE_RX = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")   # CSI and OSC sequences
EXECUTED_TYPES = {"exec", "tty_probe", "frame_match"}     # run commands on the agent's output (workdir copy)
MODEL_TYPES = {"judge", "vision_rubric"}                  # graded by a model call


def validate_cases(doc: dict, areas: tuple[str, ...] | list[str] | None = None,
                   banned: list[str] | None = None) -> list[str]:
    """Return a list of problems; empty when the cases are usable. `areas`: allowed areas (default AREAS plus the
    doc's own top-level "areas"); `banned`: neutral-domain terms that must not appear in a case or its text
    fixtures (default the doc's top-level "banned_terms")."""
    errs: list[str] = []
    cases = doc.get("cases")
    if not isinstance(cases, list) or not cases:
        return ["'cases' must be a non-empty list"]
    areas = tuple(areas) if areas is not None else tuple(dict.fromkeys([*AREAS, *doc.get("areas", [])]))
    banned = [b.lower() for b in (banned if banned is not None else doc.get("banned_terms", []))]
    seen: set[str] = set()
    for i, c in enumerate(cases):
        if not isinstance(c, dict):
            errs.append(f"case {i}: not an object")
            continue
        cid = c.get("id") or f"#{i}"
        if not c.get("id"):
            errs.append(f"case {i}: missing id")
        elif cid in seen:
            errs.append(f"{cid}: duplicate id")
        seen.add(cid)
        if not isinstance(c.get("prompt"), str) or not c["prompt"].strip():
            errs.append(f"{cid}: missing prompt")
        if c.get("area") not in areas:
            errs.append(f"{cid}: area must be one of {', '.join(areas)}")
        if not isinstance(c.get("tags", []), list):
            errs.append(f"{cid}: tags must be a list")
        if "serial" in c and not isinstance(c["serial"], bool):
            errs.append(f"{cid}: serial must be true or false")
        if "timeout" in c and not (isinstance(c["timeout"], int) and c["timeout"] > 0):
            errs.append(f"{cid}: timeout must be a positive integer (seconds)")
        if banned:
            text = json.dumps(c, ensure_ascii=False).lower()
            for f in c.get("fixtures", []):
                try:
                    text += "\n" + fixture_text(f).lower()
                except OSError:
                    pass
            hits = [b for b in banned if b in text]
            if hits:
                errs.append(f"{cid}: neutral-domain rule: mentions {hits} (case text or fixtures)")
        for f in c.get("fixtures", []):
            p = f.get("path", "")
            if not p or p.startswith("/") or ".." in Path(p).parts:
                errs.append(f"{cid}: bad fixture path {p!r}")
            if sum(k in f for k in ("lines", "content", "src")) != 1:
                errs.append(f"{cid}: fixture {p!r} needs exactly one of lines/content/src")
            if "src" in f and not _fixture_src(f["src"]).is_file():
                errs.append(f"{cid}: fixture src {f['src']!r} not found under evals/fixtures/")
        for ref in c.get("judge_reference", []):
            if not _fixture_src(ref).is_file():
                errs.append(f"{cid}: judge_reference {ref!r} not found under evals/fixtures/")
        for r in c.get("requires", []):
            if not isinstance(r, dict) or not r.get("cmd"):
                errs.append(f"{cid}: each requires entry needs a cmd")
        asserts = c.get("assertions") or []
        if not asserts:
            errs.append(f"{cid}: no assertions")
        aids: set[str] = set()
        for a in asserts:
            aid = a.get("id", "?")
            if aid in aids:
                errs.append(f"{cid}/{aid}: duplicate assertion id")
            aids.add(aid)
            t = a.get("type")
            if t not in ASSERTION_TYPES:
                errs.append(f"{cid}/{aid}: unknown type {t!r}")
                continue
            missing = ASSERTION_TYPES[t] - set(a)
            if missing:
                errs.append(f"{cid}/{aid}: missing {sorted(missing)}")
            for key in ("pattern",):
                if key in a:
                    try:
                        re.compile(a[key])
                    except re.error as e:
                        errs.append(f"{cid}/{aid}: bad regex: {e}")
            if t == "file_regex" and a.get("mode", "any") not in ("any", "all", "none"):
                errs.append(f"{cid}/{aid}: mode must be any|all|none")
            known = {x.get("id"): x for x in asserts}
            deps = a.get("blocked_by", [])
            if not isinstance(deps, list) or not all(isinstance(d, str) for d in deps):
                errs.append(f"{cid}/{aid}: blocked_by must be a list of assertion ids")
                deps = []
            for dep in deps:
                if dep not in known or dep == aid:
                    errs.append(f"{cid}/{aid}: blocked_by names {dep!r}, not another assertion of this case")
                elif known[dep].get("blocked_by"):
                    errs.append(f"{cid}/{aid}: blocked_by {dep!r} has its own blocked_by (one level only)")
            if t == "hex_near" and not _fixture_src(a.get("palette", "")).is_file():
                errs.append(f"{cid}/{aid}: palette {a.get('palette')!r} not found under evals/fixtures/")
            for key in ("stdout_regex", "stdout_not_regex", "stderr_regex", "stderr_not_regex", "ready"):
                if key in a:
                    try:
                        re.compile(a[key])
                    except re.error as e:
                        errs.append(f"{cid}/{aid}: bad {key}: {e}")
            for fc in a.get("files", []) if t in EXECUTED_TYPES else []:
                if not fc.get("path"):
                    errs.append(f"{cid}/{aid}: files entry without path")
    return errs


def _fixture_src(rel: str) -> Path:
    """A path under evals/fixtures/ (rejects absolute paths and '..')."""
    if not rel or rel.startswith("/") or ".." in Path(rel).parts:
        return FIXTURES_DIR / "__invalid__"
    return FIXTURES_DIR / rel


def case_tags(case: dict) -> set[str]:
    """Explicit tags + area + depends_on + derived tags (executed, vision, tmux, judge, binary)."""
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
    return {t for t in tags if t}


def filter_cases(cases: list[dict], include: list[str] | None, exclude: list[str] | None) -> list[dict]:
    """--tag keeps cases carrying any of the tags; --exclude-tag then drops cases carrying any of those."""
    out = cases
    if include:
        out = [c for c in out if case_tags(c) & set(include)]
    if exclude:
        out = [c for c in out if not case_tags(c) & set(exclude)]
    return out


def case_files(cases_file: Path | None = DEFAULT_CASES, cases_dir: Path | None = DEFAULT_CASES_DIR) -> list[Path]:
    """The main cases file plus every *.json under the cases dir (sorted), when they exist."""
    out = [Path(cases_file)] if cases_file else []
    if cases_dir and Path(cases_dir).is_dir():
        out += sorted(p for p in Path(cases_dir).glob("*.json") if p.resolve() not in {o.resolve() for o in out})
    return out


def read_case_doc(path: Path) -> dict:
    """A cases file: {"cases": [...], optional "areas", "banned_terms"} or a bare list of cases."""
    doc = json.loads(Path(path).read_text())
    if isinstance(doc, list):
        return {"cases": doc}
    if not isinstance(doc, dict):
        raise ValueError(f"{path}: must be a list of cases or an object with 'cases'")
    return doc


def merge_case_docs(paths: list[Path]) -> tuple[dict, dict[str, str]]:
    """One doc with every case (file order), the union of declared areas and banned terms, and case id -> file."""
    merged: dict = {"cases": [], "areas": [], "banned_terms": []}
    origin: dict[str, str] = {}
    for p in paths:
        doc = read_case_doc(p)
        for c in doc.get("cases") or []:
            merged["cases"].append(c)
            if isinstance(c, dict) and c.get("id") and c["id"] not in origin:
                origin[c["id"]] = Path(p).name
        merged["areas"] += [a for a in doc.get("areas", []) if a not in merged["areas"]]
        merged["banned_terms"] += [b for b in doc.get("banned_terms", []) if b not in merged["banned_terms"]]
    return merged, origin


def validate_case_files(paths: list[Path]) -> list[str]:
    """--validate-cases: every problem across the files, each prefixed with the file of its case."""
    try:
        doc, origin = merge_case_docs(paths)
    except (OSError, ValueError) as e:
        return [f"cannot read cases: {e}"]
    errs = validate_cases(doc)
    out = []
    for e in errs:
        cid = re.split(r"[:/]", e, maxsplit=1)[0]
        out.append(f"{origin[cid]}: {e}" if cid in origin else e)
    return out


def load_cases(path: Path | list[Path] = DEFAULT_CASES, ids: list[str] | None = None,
               cases_dir: Path | None = None) -> list[dict]:
    """Cases from a file (or a list of files) plus, with cases_dir, every *.json there; validated together."""
    paths = case_files(path, cases_dir) if not isinstance(path, list) else list(path)
    doc, _ = merge_case_docs(paths)
    errs = validate_cases(doc)
    if errs:
        raise ValueError("invalid cases:\n  " + "\n  ".join(errs))
    cases = doc["cases"]
    if ids:
        unknown = set(ids) - {c["id"] for c in cases}
        if unknown:
            raise ValueError(f"unknown case ids: {sorted(unknown)}")
        cases = [c for c in cases if c["id"] in ids]
    return cases


RUN_TOKEN = "{run}"


def materialize_case(case: dict, token: str | None) -> dict:
    """Replace the literal `{run}` in every string of the case (fixture paths, prompt, assertions, judge_context)
    with a short per-run token, so a fixture can carry a unique file name per run (`watch-{run}.py`). Cases
    without `{run}` come back unchanged; case_hash is always computed on the template."""
    if not token or RUN_TOKEN not in json.dumps(case, ensure_ascii=False):
        return case

    def sub(x):
        if isinstance(x, str):
            return x.replace(RUN_TOKEN, token)
        if isinstance(x, list):
            return [sub(v) for v in x]
        if isinstance(x, dict):
            return {k: (v if k == "src" else sub(v)) for k, v in x.items()}
        return x
    return sub(case)


def run_token(run_id: str) -> str:
    return hashlib.sha256(run_id.encode()).hexdigest()[:6]


def fixture_bytes(f: dict) -> bytes:
    if "lines" in f:
        return ("\n".join(f["lines"]) + "\n").encode()
    if "content" in f:
        return f["content"].encode()
    return _fixture_src(f["src"]).read_bytes()


def fixture_text(f: dict) -> str:
    """Text of a text fixture; '' for a binary one (a src whose suffix is not a known text type)."""
    if "src" in f and Path(f["src"]).suffix not in TEXT_SUFFIXES:
        return ""
    return fixture_bytes(f).decode("utf-8", errors="replace")


# ============================================================ models (models.toml), presets, judges, prices

COST_BASES = ("billed", "api-equivalent", "equivalent", "unknown")
MODEL_KEYS = {"id", "adapter", "model", "effort", "cost_basis", "price", "openrouter_id", "timeout", "flags", "env",
              "provider", "label"}
PRICE_KEYS = {"input", "cached_input", "cache_write", "output"}


class ConfigError(ValueError):
    """models.toml is unusable, or a --models entry is unknown."""


@dataclass
class ModelSpec:
    id: str
    adapter: str
    model: str
    effort: str
    cost_basis: str | None = None
    price: dict | None = None        # {"input", "cached" (None = billed as input), "cache_write", "output"}, USD/M
    openrouter_id: str | None = None
    timeout: int | None = None
    flags: list = field(default_factory=list)
    env: dict = field(default_factory=dict)
    provider: str | None = None
    label: str = ""
    extra: dict = field(default_factory=dict)   # adapter-specific keys (the command adapter's template, ...)


@dataclass
class Catalog:
    models: dict
    presets: dict
    default_models: str
    judge: str
    vision_judge: str
    adapter_settings: dict = field(default_factory=dict)
    source: Path | None = None
    price_cache: dict = field(default_factory=dict)     # id -> price from --refresh-prices (estimator only)
    price_cache_info: str = ""
    sandbox: dict = field(default_factory=lambda: dict(SANDBOX_DEFAULTS))

    def get(self, mid: str) -> ModelSpec:
        if mid not in self.models:
            raise ConfigError(f"unknown model {mid!r}. Known models: {', '.join(self.models)}. Presets: "
                              f"{', '.join(self.presets) or '(none)'}. Add it to "
                              f"{self.source.name if self.source else 'models.toml'} (see --list-models).")
        return self.models[mid]

    def resolve(self, specs: str | list[str]) -> list[tuple[str, str]]:
        """'frontier4,opus@high' -> [(id, effort), ...]. A preset expands in place (PRESET@EFFORT sets the effort of
        every member); an id takes its default effort unless ID@EFFORT. Exact duplicates collapse; one id with two
        efforts is an error (run ids do not carry the effort)."""
        items = [x.strip() for x in (specs.split(",") if isinstance(specs, str) else specs) if x and x.strip()]
        out: list[tuple[str, str]] = []
        for item in items:
            name, _, eff = (s.strip() for s in item.partition("@"))
            for member in (self.presets[name] if name in self.presets else [name]):
                mid, _, meff = (s.strip() for s in member.partition("@"))
                pair = (mid, eff or meff or self.get(mid).effort)
                if pair not in out:
                    out.append(pair)
        efforts: dict[str, str] = {}
        for mid, eff in out:
            if efforts.setdefault(mid, eff) != eff:
                raise ConfigError(f"model {mid!r} asked at two efforts ({efforts[mid]}, {eff}); run one per invocation")
        return out

    def order(self) -> list[str]:
        """Display order: the default preset's members, then the models file order."""
        first = [m for m, _ in self.resolve(self.default_models)] if self.default_models else []
        return list(dict.fromkeys([*first, *self.models]))

    def price(self, mid: str, use_cache: bool = True) -> tuple[dict | None, str]:
        """(price, source): the --refresh-prices cache when it has the model and use_cache, else models.toml."""
        if use_cache and mid in self.price_cache:
            return self.price_cache[mid], "cache"
        spec = self.models.get(mid)
        return (spec.price if spec else None), "models.toml"


def _price(pr, where: str, errs: list[str]) -> dict | None:
    if not isinstance(pr, dict) or set(pr) - PRICE_KEYS or not {"input", "output"} <= set(pr) \
            or not all(isinstance(v, (int, float)) for v in pr.values()):
        errs.append(f"{where}: price needs numeric input and output (optional cached_input, cache_write), "
                    "USD per million tokens")
        return None
    return {"input": float(pr["input"]), "cached": float(pr["cached_input"]) if "cached_input" in pr else None,
            "cache_write": float(pr["cache_write"]) if "cache_write" in pr else None, "output": float(pr["output"])}


def parse_catalog(doc: dict, source: Path | None = None) -> Catalog:
    """Validate a parsed models.toml and build the Catalog; ConfigError lists every problem."""
    errs: list[str] = []
    models: dict[str, ModelSpec] = {}
    for i, m in enumerate(doc.get("models") or []):
        if not isinstance(m, dict) or not m.get("id"):
            errs.append(f"models[{i}]: missing id")
            continue
        where = m["id"]
        if where in models:
            errs.append(f"{where}: duplicate id")
            continue
        ad = ADAPTERS.get(m.get("adapter"))
        if ad is None:
            errs.append(f"{where}: adapter must be one of {', '.join(ADAPTERS)} (got {m.get('adapter')!r})")
            continue
        unknown = set(m) - MODEL_KEYS - set(ad.model_keys)
        if unknown:
            errs.append(f"{where}: unknown key(s) {sorted(unknown)} for adapter {ad.name}")
        basis = m.get("cost_basis")
        if basis is not None and basis not in COST_BASES:
            errs.append(f"{where}: cost_basis must be one of {', '.join(COST_BASES)}")
        price = _price(m["price"], where, errs) if "price" in m else None
        if basis == "equivalent" and price is None:
            errs.append(f"{where}: cost_basis 'equivalent' needs a price")
        if "timeout" in m and not (isinstance(m["timeout"], int) and m["timeout"] > 0):
            errs.append(f"{where}: timeout must be a positive integer (seconds)")
        flags = m.get("flags", [])
        if not isinstance(flags, list) or not all(isinstance(x, str) for x in flags):
            errs.append(f"{where}: flags must be a list of strings")
            flags = []
        env = m.get("env", {})
        if not isinstance(env, dict):
            errs.append(f"{where}: env must be a table")
            env = {}
        spec = ModelSpec(id=str(m["id"]), adapter=ad.name, model=str(m.get("model") or m["id"]),
                         effort=str(m.get("effort") or "medium"), cost_basis=basis, price=price,
                         openrouter_id=m.get("openrouter_id"), timeout=m.get("timeout"), flags=list(flags),
                         env={str(k): str(v) for k, v in env.items()}, provider=m.get("provider"),
                         label=str(m.get("label", "")), extra={k: m[k] for k in ad.model_keys if k in m})
        errs += [f"{where}: {e}" for e in ad.validate(spec)]
        models[spec.id] = spec
    if not models:
        errs.append("no [[models]] entries")
    presets: dict[str, list[str]] = {}
    for name, members in (doc.get("presets") or {}).items():
        if name in models:
            errs.append(f"preset {name!r}: same name as a model id")
        if not isinstance(members, list) or not members:
            errs.append(f"preset {name!r}: must be a non-empty list")
            continue
        for mem in members:
            if str(mem).partition("@")[0].strip() not in models:
                errs.append(f"preset {name!r}: unknown model {mem!r}")
        presets[name] = [str(x) for x in members]
    settings = doc.get("adapters") or {}
    for name, s in settings.items():
        if name not in ADAPTERS:
            errs.append(f"[adapters.{name}]: no such adapter")
        elif not isinstance(s, dict) or set(s) - set(ADAPTERS[name].all_defaults()):
            errs.append(f"[adapters.{name}]: known keys are {sorted(ADAPTERS[name].all_defaults())}")
        elif s.get("home", "temp") not in ("temp", "real"):
            errs.append(f"[adapters.{name}]: home must be 'temp' or 'real'")
        elif any(SECRET_NAME_RX.search(n) for n in s.get("pass_env", [])):
            errs.append(f"[adapters.{name}]: pass_env must not name a secret-looking variable")
    judges = doc.get("judges") or {}
    for role, need in (("text", "supports_judge"), ("vision", "supports_vision")):
        j = judges.get(role)
        spec = models.get(str(j).partition("@")[0]) if j else None
        if spec is None:
            errs.append(f"[judges] {role}: must name a model id (got {j!r})")
        elif not getattr(ADAPTERS[spec.adapter], need):
            errs.append(f"[judges] {role}: adapter {spec.adapter} cannot run this judge")
    sandbox = {**SANDBOX_DEFAULTS, **(doc.get("sandbox") or {})}
    if set(sandbox) - set(SANDBOX_DEFAULTS):
        errs.append(f"[sandbox]: known keys are {sorted(SANDBOX_DEFAULTS)}")
    elif not isinstance(sandbox["deny_read"], list) or not all(isinstance(x, str) for x in sandbox["deny_read"]):
        errs.append("[sandbox] deny_read: must be a list of paths")
    elif not isinstance(sandbox["deny_spotlight"], bool):
        errs.append("[sandbox] deny_spotlight: must be true or false")
    default_models = str((doc.get("defaults") or {}).get("models") or ",".join(models))
    if errs:
        raise ConfigError(f"invalid models file{f' {source}' if source else ''}:\n  " + "\n  ".join(errs))
    cat = Catalog(models=models, presets=presets, default_models=default_models, judge=str(judges["text"]),
                  vision_judge=str(judges["vision"]), adapter_settings=settings, source=source, sandbox=sandbox)
    try:
        cat.resolve(default_models)
    except ConfigError as e:
        raise ConfigError(f"[defaults] models: {e}") from None
    return cat


def load_price_cache(cat: Catalog, path: Path = PRICE_CACHE_FILE) -> None:
    """Attach the --refresh-prices cache (if any) to the catalog; only the estimator reads it."""
    try:
        doc = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return
    cat.price_cache = {k: v for k, v in (doc.get("models") or {}).items() if k in cat.models}
    cat.price_cache_info = f"{Path(path).name} ({doc.get('fetched_at', '?')})"


def load_catalog(path: Path = DEFAULT_MODELS_FILE, price_cache: Path | None = None) -> Catalog:
    if tomllib is None:
        raise ConfigError("reading models.toml needs Python >= 3.11 (tomllib)")
    load_adapter_plugins()
    try:
        doc = tomllib.loads(Path(path).read_text())
    except OSError as e:
        raise ConfigError(f"{path}: {e}") from None
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path}: {e}") from None
    cat = parse_catalog(doc, Path(path))
    if price_cache:
        load_price_cache(cat, price_cache)
    return cat


_CATALOG: Catalog | None = None


def catalog() -> Catalog:
    """The active catalog (models.toml next to the runner unless main() loaded --models-file)."""
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = load_catalog()
    return _CATALOG


def set_catalog(cat: Catalog | None) -> None:
    global _CATALOG
    _CATALOG = cat


def fetch_openrouter_prices(url: str = OPENROUTER_MODELS_URL, timeout: int = 30) -> dict[str, dict]:
    """OpenRouter's public model list -> {openrouter id: price per million}. No key is needed or sent."""
    req = urllib.request.Request(url, headers={"User-Agent": "tui-design-evals"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    out: dict[str, dict] = {}
    for m in data.get("data") or []:
        p = m.get("pricing") or {}

        def per_m(key):
            try:
                v = p.get(key)
                return round(float(v) * 1e6, 6) if v not in (None, "") else None
            except (TypeError, ValueError):
                return None
        if m.get("id") and per_m("prompt") is not None and per_m("completion") is not None:
            out[m["id"]] = {"input": per_m("prompt"), "cached": per_m("input_cache_read"),
                            "cache_write": per_m("input_cache_write"), "output": per_m("completion")}
    return out


def refresh_prices(cat: Catalog, path: Path = PRICE_CACHE_FILE, table: dict | None = None) -> list[str]:
    """--refresh-prices: write the OpenRouter price of every model with an openrouter_id to the cache file."""
    table = fetch_openrouter_prices() if table is None else table
    models, lines = {}, []
    for spec in cat.models.values():
        if not spec.openrouter_id:
            continue
        pr = table.get(spec.openrouter_id)
        if pr is None:
            lines.append(f"{spec.id}: {spec.openrouter_id} is not listed by OpenRouter (kept models.toml price)")
            continue
        models[spec.id] = {"openrouter_id": spec.openrouter_id, **pr}
        old = spec.price or {}
        lines.append(f"{spec.id}: input {pr['input']} cached {pr['cached']} output {pr['output']} USD/M"
                     f" (models.toml: {old.get('input')} / {old.get('cached')} / {old.get('output')})")
    Path(path).write_text(json.dumps({"fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                      "source": OPENROUTER_MODELS_URL, "models": models}, indent=2) + "\n")
    return lines


def adapter_for(model: str) -> str:
    """Adapter name of a model id in models.toml (ConfigError, a ValueError, when the id is unknown)."""
    return catalog().get(model.partition("@")[0].strip()).adapter


def model_spec(model: str) -> ModelSpec:
    return catalog().get(model.partition("@")[0].strip())


def parse_model_spec(spec: str) -> tuple[str, str]:
    """'z-ai/glm-5.3@high' -> ('z-ai/glm-5.3', 'high'); without @, the model's effort from models.toml."""
    mid, _, eff = (s.strip() for s in spec.partition("@"))
    return mid, eff or catalog().get(mid).effort


def slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9.]+", "-", s).strip("-")


def skill_rel(adapter: str, spec: ModelSpec | None = None) -> str:
    return ADAPTERS[adapter].skill_dir_rel(spec)


def install_skill(workdir: Path, adapter: str, skill_dir: Path | None = None, spec: ModelSpec | None = None) -> Path:
    dest = workdir / skill_rel(adapter, spec) / SKILL_NAME
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(skill_dir or SKILL_DIR, dest, ignore=shutil.ignore_patterns(*SKILL_IGNORE))
    return dest


# ============================================================ secrets: allow-listed environment, redaction, leak scan
#
# Agents, judges and executed checks never inherit the orchestrator's environment: they get an allow-list built
# from scratch (PATH, locale, TERM, user name, a HOME and TMPDIR, the adapter's own variables). No secret goes
# in argv. Every artifact is redacted before it is written (values of every variable named like a key, token,
# secret or password, from the environment and the evals env file), and each run's artifacts are scanned
# afterwards: a hit marks the run `secret leak` and stops the campaign.

ENV_FILE = Path(os.environ.get("EVAL_ENV_FILE") or "~/.config/tui-design-evals/env").expanduser()
ALLOWED_ENV = ("PATH", "LANG", "LANGUAGE", "TZ", "USER", "LOGNAME", "SHELL", "TERM", "COLORTERM")
SECRET_NAME_RX = re.compile(r"KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL", re.I)
SECRET_MIN_LEN = 8


def base_env(home: Path, tmpdir: Path, extra_names: list[str] | None = None) -> dict[str, str]:
    """A fresh environment: ALLOWED_ENV and LC_* from the orchestrator, HOME, TMPDIR and TMUX_TMPDIR, and only the
    `extra_names` an adapter setting passes through (never a name that looks like a secret)."""
    env = {k: os.environ[k] for k in ALLOWED_ENV if os.environ.get(k)}
    env.update({k: v for k, v in os.environ.items() if k.startswith("LC_")})
    for k in extra_names or []:
        if os.environ.get(k) and not SECRET_NAME_RX.search(k):
            env[k] = os.environ[k]
    env.setdefault("TERM", "xterm-256color")
    env.update({"HOME": str(home), "TMPDIR": str(tmpdir), "TMUX_TMPDIR": str(tmpdir)})
    return env


def parse_env_file(text: str) -> dict[str, str]:
    """KEY="value" / KEY=value / export KEY=value lines; comments and blank lines ignored."""
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip().removeprefix("export ").strip()
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        out[k] = v
    return out


class Redactor:
    """Known secret values (name -> value) and how to strip them from text and bytes."""

    def __init__(self, secrets: dict[str, str] | None = None):
        self.secrets = {k: v for k, v in (secrets or {}).items() if v and len(v) >= SECRET_MIN_LEN}
        self._order = sorted(self.secrets.items(), key=lambda kv: len(kv[1]), reverse=True)

    @classmethod
    def from_environment(cls, env_file: Path | None = None) -> "Redactor":
        names: dict[str, str] = {}
        env_file = ENV_FILE if env_file is None else env_file
        try:
            names.update({k: v for k, v in parse_env_file(Path(env_file).read_text()).items()
                          if SECRET_NAME_RX.search(k)})
        except OSError:
            pass
        names.update({k: v for k, v in os.environ.items() if SECRET_NAME_RX.search(k)})
        return cls(names)

    def text(self, s: str) -> tuple[str, list[str]]:
        hits = []
        for name, val in self._order:
            if val in s:
                s = s.replace(val, f"<redacted:{name}>")
                hits.append(name)
        return s, hits

    def data(self, b: bytes) -> tuple[bytes, list[str]]:
        hits = []
        for name, val in self._order:
            v = val.encode()
            if v in b:
                b = b.replace(v, f"<redacted:{name}>".encode())
                hits.append(name)
        return b, hits

    def find(self, b: bytes) -> list[str]:
        return [name for name, val in self._order if val.encode() in b]


_REDACTOR: Redactor | None = None


def redactor() -> Redactor:
    global _REDACTOR
    if _REDACTOR is None:
        _REDACTOR = Redactor.from_environment()
    return _REDACTOR


def set_redactor(r: Redactor | None) -> None:
    global _REDACTOR
    _REDACTOR = r


def redact_secrets(text: str) -> str:
    """`text` with every known secret value replaced by <redacted:NAME>."""
    return redactor().text(text)[0]


def write_redacted(path: Path, text: str, hits: list[str] | None = None) -> None:
    """Write text after redaction; the names of the secrets found are appended to `hits`."""
    clean, found = redactor().text(text)
    if hits is not None:
        hits.extend(found)
    path.write_text(clean)


def leak_scan(paths: list[Path], r: Redactor | None = None) -> dict[str, list[str]]:
    """{file name: [secret names]} for every raw secret value still present in these files (.gz decompressed,
    directories walked). Empty = clean."""
    r = r or redactor()
    found: dict[str, list[str]] = {}
    if not r.secrets:
        return found
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            files += [f for f in sorted(p.rglob("*")) if f.is_file()]
        elif p.is_file():
            files.append(p)
    for f in files:
        try:
            data = gzip.decompress(f.read_bytes()) if f.suffix == ".gz" else f.read_bytes()
        except (OSError, EOFError, gzip.BadGzipFile):
            data = f.read_bytes()
        names = r.find(data)
        if names:
            found[f.name] = names
    return found


def run_artifacts(runs_dir: Path, rid: str) -> list[Path]:
    return [runs_dir / f"{rid}{s}" for s in (".json", ".events.jsonl", ".events.jsonl.gz", ".stderr.txt", ".files")]


def scrub_files(paths: list[Path]) -> None:
    """Rewrite files that still hold a raw secret (after leak_scan found one): redacted bytes, gz recompressed."""
    for p in paths:
        for f in ([x for x in p.rglob("*") if x.is_file()] if p.is_dir() else [p] if p.is_file() else []):
            raw = f.read_bytes()
            gz = f.suffix == ".gz"
            data = gzip.decompress(raw) if gz else raw
            clean, hits = redactor().data(data)
            if hits:
                f.write_bytes(gzip.compress(clean) if gz else clean)


def project_root(start: Path = EVALS_DIR) -> Path:
    """The checkout around the evals: the first ancestor holding .git, else the evals dir's parent. Agents that
    confine reads never see it (it holds evals/ with every case's checks and the results)."""
    for d in [start, *start.parents]:
        if (d / ".git").exists():
            return d
    return start.parent


def _sb_quote(p: Path | str) -> str:
    return '"' + str(p).replace("\\", "\\\\").replace('"', '\\"') + '"'


def extra_deny_paths() -> list[Path]:
    """[sandbox] deny_read from models.toml plus EVAL_DENY_READ (os.pathsep-separated machine-local paths, from the
    environment or the evals env file; the environment wins)."""
    raw = list(catalog().sandbox.get("deny_read") or [])
    local = os.environ.get("EVAL_DENY_READ")
    if local is None:
        try:
            local = parse_env_file(ENV_FILE.read_text()).get("EVAL_DENY_READ")
        except OSError:
            local = None
    raw += [x for x in (local or "").split(os.pathsep) if x.strip()]
    return [Path(os.path.expanduser(x.strip())).resolve() for x in raw]


def confine_profile(run_dir: Path) -> str:
    """sandbox-exec profile for an agent: everything allowed except reading or writing the project checkout, the
    source skill, the evals, the results root, the evals env file and the [sandbox] deny_read paths, and (unless
    deny_spotlight = false) Spotlight lookups; the run's own temp dir stays allowed."""
    deny = {project_root().resolve(), SKILL_DIR.resolve(), EVALS_DIR.resolve(), Path(RESULTS_DIR).resolve(),
            ENV_FILE.parent.resolve(), *extra_deny_paths()}
    rules = ["(version 1)", "(allow default)"]
    rules += [f"(deny file-read* file-write* (subpath {_sb_quote(d)}))" for d in sorted(deny, key=str)]
    if catalog().sandbox.get("deny_spotlight", True):
        rules.append('(deny mach-lookup (global-name "com.apple.metadata.mds") (global-name "com.apple.metadata.mds.index"))')
    rules.append(f"(allow file-read* file-write* (subpath {_sb_quote(Path(run_dir).resolve())}))")
    return "".join(rules)


def confine_prefix(run_dir: Path | None) -> list[str]:
    """['sandbox-exec', '-p', PROFILE] on macOS (EVAL_NO_SANDBOX=1 disables it); [] elsewhere or without run_dir."""
    if run_dir is None or os.environ.get("EVAL_NO_SANDBOX") or not shutil.which("sandbox-exec"):
        return []
    return ["sandbox-exec", "-p", confine_profile(run_dir)]


# ============================================================ adapters (registry)

@dataclass
class Invocation:
    """How to start one agent or judge: argv, environment overrides, and the file fed on stdin (None = /dev/null).
    The prompt never appears in argv."""
    argv: list[str]
    env: dict[str, str] = field(default_factory=dict)
    stdin: Path | None = None
    shown_env: dict[str, str] | None = None      # what the run record stores (templates for ${VAR} values)

    def display(self) -> str:
        env = self.env if self.shown_env is None else self.shown_env
        pre = " ".join(f"{k}={v}" for k, v in env.items())
        cmd = " ".join(shlex.quote(c) for c in self.argv)
        return redact_secrets((pre + " " if pre else "") + cmd + (f" < {self.stdin}" if self.stdin else " < /dev/null"))


ADAPTERS: dict[str, "Adapter"] = {}
PLACEHOLDERS = ("prompt_file", "workdir", "model", "effort", "skill_dir", "home", "run_dir", "arm", "evals_dir")


def register_adapter(adapter: "Adapter") -> "Adapter":
    """Add (or replace) an adapter in the registry; plugins in evals/adapters/*.py call this."""
    ADAPTERS[adapter.name] = adapter
    return adapter


def _effort_flag(effort: str | None) -> str | None:
    return None if effort in (None, "", "none") else effort


def fill(template: str, values: dict[str, str]) -> str:
    """Replace {placeholder} names from PLACEHOLDERS (other braces are left alone)."""
    for k, v in values.items():
        template = template.replace("{" + k + "}", str(v))
    return template


def model_env(spec: ModelSpec | None, values: dict[str, str]) -> tuple[dict[str, str], dict[str, str]]:
    """(env to pass, env to record) for a model's `env` table: placeholders filled, ${VAR} expanded only in the
    first, so a secret taken from the environment is never written to a run record."""
    if not spec or not spec.env:
        return {}, {}
    shown = {k: fill(v, values) for k, v in spec.env.items()}
    return {k: os.path.expanduser(os.path.expandvars(v)) for k, v in shown.items()}, shown


class Adapter:
    """Base class of an agent CLI adapter. A subclass sets the class attributes and implements command() and
    parse(); judge_command() only when it can serve as a judge; tool_texts() for transcript_regex; live_cost() to
    stream billed cost for --max-usd. Register an instance with register_adapter()."""
    name = ""
    provider = ""
    executable = ""
    skill_rel = ".agents/skills"          # where the skill arm installs the skill, relative to the workdir
    default_cost_basis = "unknown"
    git_init = False                      # git-init the workdir before the run
    model_keys: frozenset = frozenset()   # extra per-model keys this adapter accepts in models.toml
    defaults: dict = {}                   # [adapters.<name>] settings and their defaults (plus COMMON below)
    COMMON = {"home": "temp",             # temp: a fresh empty HOME per run; real: the user's (CLI needs it)
              "confine_reads": False,     # macOS sandbox-exec: no reads of the project checkout (confine_profile)
              "pass_env": []}             # extra variable names passed through (never one that looks secret)
    supports_judge = False
    supports_vision = False

    def all_defaults(self) -> dict:
        return {**self.COMMON, **self.defaults}

    def setting(self, key: str):
        cat = _CATALOG if _CATALOG is not None else catalog()
        return (cat.adapter_settings.get(self.name) or {}).get(key, self.all_defaults().get(key))

    def wrap(self, argv: list[str], run_dir: Path | None) -> list[str]:
        """Prefix sandbox-exec read confinement when this adapter's confine_reads setting is on."""
        return (confine_prefix(run_dir) if self.setting("confine_reads") else []) + argv

    def environment(self, home: Path, tmpdir: Path) -> dict[str, str]:
        """The allow-listed base environment of a process this adapter starts (adapter variables come on top)."""
        real = self.setting("home") == "real"
        return base_env(Path.home() if real else home, tmpdir, self.setting("pass_env"))

    def exe(self, spec: ModelSpec | None = None) -> str:
        return self.executable

    def skill_dir_rel(self, spec: ModelSpec | None = None) -> str:
        return self.skill_rel

    def validate(self, spec: ModelSpec) -> list[str]:
        return []

    def command(self, spec: ModelSpec, effort: str, arm: str, prompt_file: Path, workdir: Path, home: Path,
                extra_tools: list[str] | None = None, run_dir: Path | None = None) -> Invocation:
        raise NotImplementedError

    def judge_command(self, spec: ModelSpec, effort: str | None, prompt_file: Path, vision: bool = False) -> Invocation:
        raise ValueError(f"adapter {self.name} cannot run a judge")

    def parse(self, lines: list[str], spec: ModelSpec | None = None, place: dict | None = None) -> dict:
        raise NotImplementedError

    def tool_texts(self, events: list[dict]) -> str:
        return ""

    def live_cost(self, line: str) -> float:
        return 0.0

    def version(self, spec: ModelSpec | None = None) -> str | None:
        exe = self.exe(spec)
        return _cli_version([exe, "--version"]) if exe else None

    def finish(self, parsed: dict, spec: ModelSpec | None) -> dict:
        """Apply the model's cost_basis (models.toml wins over the adapter default)."""
        if spec is not None and spec.cost_basis:
            parsed["cost_basis"] = spec.cost_basis
        return parsed


def _cli_version(argv: list[str]) -> str | None:
    if not argv or not shutil.which(argv[0]):
        return None
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return None
    out = (p.stdout or p.stderr).strip()
    return out.splitlines()[0][:120] if out else None


class OmpAdapter(Adapter):
    """omp (OpenRouter models). Skill under .agents/skills, --skills=NAME | --no-skills. The prompt goes on stdin
    from the prompt file (omp reads piped stdin as the message; `@file` would wrap it in a <file> block). The
    OpenRouter key lives in an isolated omp profile (--profile; one-time setup in README), never in argv or the
    agent's environment. Reads of the project checkout are denied (sandbox-exec), and the skill arm is told where
    the skill folder is (omp's skill:// URLs carry no path, so agents went looking with `find /`)."""
    name, provider, executable = "omp", "openrouter", "omp"
    default_cost_basis = "billed"
    defaults = {"profile": "tui-design-evals", "home": "real", "confine_reads": True,
                "skill_hint": "The {skill_name} skill is installed in the folder {skill_dir} (SKILL.md, references/, "
                              "scripts/). Read its files and run its scripts from that folder; nothing else on "
                              "this machine belongs to it."}
    supports_judge = True

    def profile_args(self) -> list[str]:
        prof = self.setting("profile")
        return ["--profile", prof] if prof else []

    def profile_ready(self) -> bool:
        prof = self.setting("profile")
        return not prof or (Path.home() / ".omp" / "profiles" / prof).is_dir()

    def command(self, spec, effort, arm, prompt_file, workdir, home, extra_tools=None, run_dir=None):
        cmd = ["omp", *self.profile_args(), "-p", "--no-session", "--no-rules", "--no-extensions", "--mode", "json",
               "--model", spec.model]
        if _effort_flag(effort):
            cmd += ["--thinking", effort]
        cmd += [f"--skills={SKILL_NAME}"] if arm == "skill" else ["--no-skills"]
        hint = self.setting("skill_hint")
        if arm == "skill" and hint and run_dir is not None:
            hint_file = Path(run_dir) / "skill-hint.md"
            if Path(run_dir).is_dir():
                hint_file.write_text(fill(hint, {"skill_name": SKILL_NAME,
                                                 "skill_dir": str(workdir / self.skill_rel / SKILL_NAME)}))
            cmd += ["--append-system-prompt", str(hint_file)]
        env, shown = model_env(spec, {"home": home, "workdir": workdir, "run_dir": run_dir or ""})
        return Invocation(self.wrap(cmd + spec.flags, run_dir), env, prompt_file, shown)

    def judge_command(self, spec, effort, prompt_file, vision=False):
        if vision:
            raise ValueError("the vision judge must be a claude model (it reads the PNGs with the Read tool)")
        cmd = ["omp", *self.profile_args(), "-p", "--no-session", "--no-rules", "--no-extensions", "--no-skills",
               "--no-tools", "--mode", "json", "--model", spec.model, "--thinking", effort or "low"]
        return Invocation(self.wrap(cmd, prompt_file.parent), {}, prompt_file)

    def parse(self, lines, spec=None, place=None):
        return self.finish(parse_omp(_parse_lines(lines)), spec)

    def tool_texts(self, events):
        return "\n".join(f"{e.get('toolName', '')} {json.dumps(e.get('args') or {}, ensure_ascii=False)}"
                         for e in events if e.get("type") == "tool_execution_start")

    def live_cost(self, line):
        if '"message_end"' not in line:
            return 0.0
        try:
            m = (json.loads(line).get("message") or {})
        except ValueError:
            return 0.0
        if m.get("role") != "assistant":
            return 0.0
        return float(((m.get("usage") or {}).get("cost") or {}).get("total") or 0)


class ClaudeAdapter(Adapter):
    """Claude Code. CLAUDE_CONFIG_DIR = a separate login, --strict-mcp-config, acceptEdits + allowed tools; the
    prompt goes on stdin (claude -p reads it when no prompt argument is given)."""
    name, provider, executable = "claude", "anthropic", "claude"
    skill_rel = ".claude/skills"
    default_cost_basis = "api-equivalent"
    defaults = {"config_dir": "~/.claude-eval", "allowed_tools": ["Bash(python3:*)", "Bash(uv run:*)"],
                "home": "real",           # the login's keychain entry is looked up through HOME
                "confine_reads": True}
    supports_judge = True
    supports_vision = True

    def config_env(self) -> dict[str, str]:
        return {"CLAUDE_CONFIG_DIR": str(Path(os.path.expanduser(self.setting("config_dir"))))}

    def command(self, spec, effort, arm, prompt_file, workdir, home, extra_tools=None, run_dir=None):
        cmd = ["claude", "-p", "--model", spec.model]
        if _effort_flag(effort):
            cmd += ["--effort", effort]
        cmd += ["--output-format", "stream-json", "--verbose", "--no-session-persistence",
                "--strict-mcp-config", "--permission-mode", "acceptEdits", *spec.flags,
                "--allowedTools", *self.setting("allowed_tools"), *(extra_tools or [])]
        env, shown = model_env(spec, {"home": home, "workdir": workdir, "run_dir": run_dir or ""})
        return Invocation(self.wrap(cmd, run_dir), {**self.config_env(), **env}, prompt_file,
                          {**self.config_env(), **shown})

    def judge_command(self, spec, effort, prompt_file, vision=False):
        tools = ["--tools", "Read", "--allowedTools", "Read"] if vision else ["--tools", ""]
        cmd = ["claude", "-p", "--model", spec.model, *tools, "--strict-mcp-config",
               "--output-format", "stream-json", "--verbose", "--no-session-persistence"]
        return Invocation(self.wrap(cmd, prompt_file.parent), self.config_env(), prompt_file)

    def parse(self, lines, spec=None, place=None):
        return self.finish(parse_claude(_parse_lines(lines)), spec)

    def tool_texts(self, events):
        out = []
        for e in events:
            if e.get("type") == "assistant":
                for b in (e.get("message") or {}).get("content") or []:
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        out.append(f"{b.get('name', '')} {json.dumps(b.get('input') or {}, ensure_ascii=False)}")
        return "\n".join(out)


class CodexAdapter(Adapter):
    """Codex CLI. CODEX_HOME = a separate login, HOME = a fresh empty dir, TMPDIR inside the workdir, plugins and
    apps disabled, workspace-write sandbox without /tmp; the prompt goes on stdin (`codex exec ... -`)."""
    name, provider, executable = "codex", "openai", "codex"
    default_cost_basis = "equivalent"
    git_init = True
    defaults = {"codex_home": "~/.codex-eval", "disable": ["plugins", "remote_plugin", "apps"],
                "confine_reads": False}   # codex runs its commands under its own seatbelt; nesting fails

    def command(self, spec, effort, arm, prompt_file, workdir, home, extra_tools=None, run_dir=None):
        cmd = ["codex", "exec", "--json", "--skip-git-repo-check", "--ephemeral",
               "--sandbox", "workspace-write", "-c", "approval_policy=never",
               "-c", "sandbox_workspace_write.exclude_slash_tmp=true",
               "-c", "sandbox_workspace_write.exclude_tmpdir_env_var=true"]
        for feat in self.setting("disable") or []:
            cmd += ["--disable", feat]
        cmd += ["-m", spec.model]
        if _effort_flag(effort):
            cmd += ["-c", f"model_reasoning_effort={effort}"]
        cmd += ["-C", str(workdir), *spec.flags, "-"]
        base = {"CODEX_HOME": str(Path(os.path.expanduser(self.setting("codex_home")))), "HOME": str(home),
                "TMPDIR": str(workdir / ".tmp")}
        env, shown = model_env(spec, {"home": home, "workdir": workdir, "run_dir": run_dir or ""})
        return Invocation(cmd, {**base, **env}, prompt_file, {**base, **shown})

    def parse(self, lines, spec=None, place=None):
        price = spec.price if spec is not None else None
        r = parse_codex(_parse_lines(lines), price)
        return self.finish(r, spec) if price else {**r, "cost_basis": "unknown"}

    def tool_texts(self, events):
        out = []
        for e in events:
            if e.get("type") == "item.completed":
                item = e.get("item") or {}
                if item.get("type") == "command_execution":
                    out.append(str(item.get("command") or ""))
                elif item.get("type") == "file_change":
                    out.append(json.dumps(item.get("changes") or [], ensure_ascii=False))
        return "\n".join(out)


class CommandAdapter(Adapter):
    """Any agent CLI from an argv template in models.toml (no code). Keys: command (argv with placeholders
    {prompt_file} {workdir} {model} {effort} {skill_dir} {home} {run_dir} {arm} {evals_dir}), prompt_via (arg |
    stdin), answer (stdout | path template), usage (optional path template of a JSON with input, cached,
    cache_write, output, reasoning, cost_usd), skill_path, skill_args, baseline_args, version_command."""
    name, provider = "command", "unknown"
    model_keys = frozenset({"command", "prompt_via", "answer", "usage", "skill_path", "skill_args",
                            "baseline_args", "version_command"})

    def validate(self, spec):
        x, errs = spec.extra, []
        cmd = x.get("command")
        if not isinstance(cmd, list) or not cmd or not all(isinstance(a, str) for a in cmd):
            return ["command must be a non-empty list of strings (an argv template)"]
        via = x.get("prompt_via", "arg")
        if via not in ("arg", "stdin"):
            errs.append("prompt_via must be 'arg' or 'stdin'")
        if via == "arg" and not any("{prompt_file}" in a for a in cmd):
            errs.append("prompt_via 'arg' needs {prompt_file} in command (or use prompt_via = 'stdin')")
        for key in ("skill_args", "baseline_args", "version_command"):
            if key in x and (not isinstance(x[key], list) or not all(isinstance(a, str) for a in x[key])):
                errs.append(f"{key} must be a list of strings")
        for key in ("answer", "usage", "skill_path"):
            if key in x and not isinstance(x[key], str):
                errs.append(f"{key} must be a string")
        text = json.dumps([cmd, x.get("skill_args", []), x.get("baseline_args", []), x.get("answer", ""),
                           x.get("usage", ""), spec.flags, spec.env])
        bad = sorted(set(re.findall(r"\{([a-z_]+)\}", text)) - set(PLACEHOLDERS))
        if bad:
            errs.append(f"unknown placeholder(s) {bad}; known: {', '.join(PLACEHOLDERS)}")
        return errs

    @staticmethod
    def values(spec, effort, arm, prompt_file, workdir, home, run_dir, skill_rel_path) -> dict[str, str]:
        skill = str(workdir / skill_rel_path / SKILL_NAME) if arm == "skill" else ""
        return {"prompt_file": str(prompt_file), "workdir": str(workdir), "model": spec.model,
                "effort": effort or "", "skill_dir": skill, "home": str(home), "run_dir": str(run_dir or ""),
                "arm": arm, "evals_dir": str(EVALS_DIR)}

    def exe(self, spec=None):
        return fill(spec.extra["command"][0], {"evals_dir": str(EVALS_DIR)}) if spec else ""

    def skill_dir_rel(self, spec=None):
        return (spec.extra.get("skill_path") if spec else None) or self.skill_rel

    def command(self, spec, effort, arm, prompt_file, workdir, home, extra_tools=None, run_dir=None):
        x = spec.extra
        v = self.values(spec, effort, arm, prompt_file, workdir, home, run_dir, self.skill_dir_rel(spec))
        argv = [fill(a, v) for a in [*x["command"], *spec.flags,
                                     *(x.get("skill_args", []) if arm == "skill" else x.get("baseline_args", []))]]
        env, shown = model_env(spec, v)
        return Invocation(self.wrap(argv, run_dir), env, prompt_file if x.get("prompt_via", "arg") == "stdin" else None,
                          shown)

    def parse(self, lines, spec=None, place=None):
        x, place = (spec.extra if spec else {}), (place or {})
        r = {"final_answer": "", "tool_calls": 0, "tokens": None, "cost_usd": 0.0, "cost_basis": "unknown",
             "skill_loaded": None, "error": None}
        answer = x.get("answer", "stdout")
        if answer == "stdout":
            r["final_answer"] = "".join(lines).strip()
        else:
            p = Path(fill(answer, place))
            r["final_answer"] = read_text(p).strip() if p.is_file() else ""
            if not p.is_file():
                r["error"] = f"answer file not written: {p.name}"
        if x.get("usage"):
            try:
                u = json.loads(Path(fill(x["usage"], place)).read_text())
            except (OSError, ValueError):
                u = None
            if isinstance(u, dict):
                r["tokens"] = {k: int(u.get(k) or 0) for k in _empty_tokens()}
                if u.get("cost_usd") is not None:
                    r["cost_usd"] = float(u["cost_usd"])
                    r["cost_basis"] = (spec.cost_basis if spec and spec.cost_basis else "billed")
                elif spec is not None and spec.price:
                    r["cost_usd"] = codex_cost(r["tokens"], spec.price)
                    r["cost_basis"] = "equivalent"
        if spec is not None and spec.cost_basis and r["cost_basis"] != "unknown":
            r["cost_basis"] = spec.cost_basis
        return r

    def version(self, spec=None):
        if spec is None or not spec.extra.get("version_command"):
            return None
        return _cli_version([fill(a, {"evals_dir": str(EVALS_DIR)}) for a in spec.extra["version_command"]])


for _ad in (OmpAdapter(), ClaudeAdapter(), CodexAdapter(), CommandAdapter()):
    register_adapter(_ad)

_PLUGINS_LOADED = False


def load_adapter_plugins(directory: Path = ADAPTERS_DIR) -> list[str]:
    """Run every evals/adapters/*.py once with Adapter, Invocation, register_adapter and the parsing helpers in
    its globals; each file defines an Adapter subclass and calls register_adapter(MyAdapter())."""
    global _PLUGINS_LOADED
    if _PLUGINS_LOADED or not directory.is_dir():
        return []
    _PLUGINS_LOADED = True
    names = []
    api = {"Adapter": Adapter, "Invocation": Invocation, "register_adapter": register_adapter,
           "ModelSpec": ModelSpec, "parse_lines": _parse_lines, "empty_tokens": _empty_tokens,
           "model_env": model_env, "fill": fill, "skill_hit": lambda s: _skill_hit(s), "price_cost": lambda t, p: codex_cost(t, p)}
    for path in sorted(directory.glob("*.py")):
        runpy.run_path(str(path), init_globals=api)
        names.append(path.stem)
    return names


def build_command(adapter: str, model: str, effort: str, arm: str, prompt_file: Path, workdir: Path, home: Path,
                  extra_tools: list[str] | None = None, run_dir: Path | None = None) -> Invocation:
    """The Invocation of one agent run. extra_tools: more Claude `--allowedTools` rules for a case (e.g.
    Bash(tmux:*) for a live capture); other adapters ignore them."""
    spec = model_spec(model)
    return ADAPTERS[adapter].command(spec, effort, arm, Path(prompt_file), workdir, home, extra_tools, run_dir)


@contextmanager
def prompt_file_for(text: str, prefix: str = "evalprompt-"):
    """A private temp file holding `text` (removed afterwards): how judges get their prompt."""
    d = Path(tempfile.mkdtemp(prefix=prefix))
    try:
        p = d / "prompt.txt"
        p.write_text(text, encoding="utf-8")
        yield p
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ============================================================ run identity (stable keys for exporters)

_ADAPTER_VERSIONS: dict[str, str | None] = {}
_VERSION_LOCK = threading.Lock()


def canonical(obj) -> str:
    """Canonical JSON: sorted keys, no whitespace, UTF-8 kept; equal objects give equal strings."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


HASH_EXCLUDED_KEYS = ("serial",)   # scheduling only: changes neither what the agent sees nor how it is graded


def case_hash(case: dict) -> str:
    """sha256 of the case's canonical JSON (prompt, fixtures, assertions, every field but HASH_EXCLUDED_KEYS),
    with the bytes of each `src` fixture and `judge_reference` file folded in, so editing a fixture file changes
    the hash too."""
    c = {k: v for k, v in json.loads(json.dumps(case)).items() if k not in HASH_EXCLUDED_KEYS}
    for f in c.get("fixtures", []):
        if "src" in f:
            f["src_sha256"] = sha256_bytes(_fixture_src(f["src"]).read_bytes())
    if c.get("judge_reference"):
        c["judge_reference_sha256"] = [sha256_bytes(_fixture_src(r).read_bytes()) for r in c["judge_reference"]]
    return sha256_text(canonical(c))


SKILL_IGNORE = ("evals", "__pycache__", ".git", ".DS_Store")


def tree_hash(root: Path, ignore: tuple[str, ...] = SKILL_IGNORE) -> str:
    """sha256 over (relative path, file sha256) of every file under root, skipping `ignore` names anywhere."""
    h = hashlib.sha256()
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in ignore)
        for fn in sorted(files):
            if fn in ignore:
                continue
            p = Path(dirpath) / fn
            if p.is_file():
                rel = p.relative_to(root).as_posix()
                h.update(rel.encode() + b"\0" + sha256_bytes(p.read_bytes()).encode() + b"\n")
    return h.hexdigest()


def adapter_version(adapter: str, spec: ModelSpec | None = None) -> str | None:
    """The CLI's version line (`<cli> --version`, or the model's version_command), cached for the session; None
    when the CLI is missing or fails."""
    key = f"{adapter}|{spec.id if adapter == 'command' and spec else ''}"
    with _VERSION_LOCK:
        if key not in _ADAPTER_VERSIONS:
            ad = ADAPTERS.get(adapter)
            _ADAPTER_VERSIONS[key] = ad.version(spec) if ad else None
        return _ADAPTER_VERSIONS[key]


def run_identity(case: dict, model: str, effort: str, arm: str, rep: int, judge: str | None,
                 vision_judge: str | None, skill_hash: str | None, adapter_ver: str | None) -> dict:
    """identity fields + run_key (all of them) + experiment_key (without case_id, case_hash and rep: 'this model,
    config, skill version and arm'). run_id stays the human-readable resume key."""
    spec = model_spec(model)
    adapter = spec.adapter
    provider = spec.provider or ADAPTERS[adapter].provider
    ident = {"case_id": case["id"], "case_hash": case_hash(case), "model": model, "provider": provider,
             "adapter": adapter, "adapter_version": adapter_ver, "effort": effort,
             "skill_hash": skill_hash if arm == "skill" else None, "judge": judge, "vision_judge": vision_judge,
             "arm": arm, "rep": rep}
    exp = {k: v for k, v in ident.items() if k not in ("case_id", "case_hash", "rep")}
    return {"identity": ident, "run_key": sha256_text(canonical(ident)), "experiment_key": sha256_text(canonical(exp))}


def dataset_entries(cases: list[dict]) -> list[dict]:
    """One item per case for dataset.json (what an exporter uploads as dataset items / examples)."""
    out = []
    for c in cases:
        out.append({
            "case_id": c["id"], "case_hash": case_hash(c), "area": c.get("area"), "tags": sorted(case_tags(c)),
            "depends_on": c.get("depends_on"), "lang": c.get("lang"), "source": c.get("source"), "prompt": c["prompt"],
            "fixtures": [{"path": f["path"], "src": f.get("src"), "sha256": sha256_bytes(fixture_bytes(f))}
                         for f in c.get("fixtures", [])],
            "assertions": [{k: a[k] for k in ("id", "type", "neutral", "question", "desc") if k in a}
                           for a in c["assertions"]],
        })
    return out


def write_dataset(out_dir: Path, cases: list[dict]) -> Path:
    p = out_dir / "dataset.json"
    p.write_text(json.dumps({"skill": SKILL_NAME, "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
                             "items": dataset_entries(cases)}, indent=2, ensure_ascii=False) + "\n")
    return p


def _empty_tokens() -> dict:
    return {"input": 0, "cached": 0, "cache_write": 0, "output": 0, "reasoning": 0}


def _parse_lines(text_or_lines) -> list[dict]:
    lines = text_or_lines.splitlines() if isinstance(text_or_lines, str) else text_or_lines
    out = []
    for line in lines:
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def _skill_hit(s: str) -> bool:
    return (f"skill://{SKILL_NAME}" in s or f"{SKILL_NAME}/SKILL.md" in s
            or f"skills/{SKILL_NAME}/" in s)


def parse_omp(events: list[dict]) -> dict:
    """Sum usage over assistant message_end events (turn_end repeats the same message)."""
    r = {"final_answer": "", "tool_calls": 0, "tokens": _empty_tokens(), "cost_usd": 0.0,
         "cost_basis": "billed", "skill_loaded": False, "error": None}
    for e in events:
        t = e.get("type")
        if t == "tool_execution_start":
            r["tool_calls"] += 1
            if _skill_hit(json.dumps(e.get("args") or {})):
                r["skill_loaded"] = True
        elif t == "message_end":
            m = e.get("message") or {}
            if m.get("role") != "assistant":
                continue
            u = m.get("usage") or {}
            tk = r["tokens"]
            tk["input"] += int(u.get("input") or 0)
            tk["cached"] += int(u.get("cacheRead") or 0)
            tk["cache_write"] += int(u.get("cacheWrite") or 0)
            tk["output"] += int(u.get("output") or 0)
            tk["reasoning"] += int(u.get("reasoningTokens") or 0)
            r["cost_usd"] += float((u.get("cost") or {}).get("total") or 0)
            texts = [b.get("text", "") for b in (m.get("content") or [])
                     if isinstance(b, dict) and b.get("type") == "text"]
            if any(x.strip() for x in texts):
                r["final_answer"] = "\n".join(texts).strip()
            if m.get("stopReason") == "error" or m.get("errorMessage"):
                r["error"] = str(m.get("errorMessage") or "stopReason=error")[:500]
    return r


def parse_claude(events: list[dict]) -> dict:
    r = {"final_answer": "", "tool_calls": 0, "tokens": _empty_tokens(), "cost_usd": 0.0,
         "cost_basis": "api-equivalent", "skill_loaded": False, "error": None}
    result = None
    for e in events:
        t = e.get("type")
        if t == "assistant":
            for b in (e.get("message") or {}).get("content") or []:
                if not isinstance(b, dict) or b.get("type") != "tool_use":
                    continue
                r["tool_calls"] += 1
                inp = b.get("input") or {}
                if b.get("name") == "Skill":
                    sk = str(inp.get("skill", ""))
                    if sk == SKILL_NAME or sk.endswith(":" + SKILL_NAME):
                        r["skill_loaded"] = True
                elif _skill_hit(json.dumps(inp)):
                    r["skill_loaded"] = True
        elif t == "result":
            result = e
    if result is None:
        r["error"] = "no result event"
        return r
    r["final_answer"] = str(result.get("result") or "")
    r["cost_usd"] = float(result.get("total_cost_usd") or 0)
    if result.get("is_error"):
        r["error"] = str(result.get("result") or result.get("subtype"))[:500]
    mu = result.get("modelUsage") or {}
    tk = r["tokens"]
    if mu:
        for v in mu.values():
            tk["input"] += int(v.get("inputTokens") or 0)
            tk["cached"] += int(v.get("cacheReadInputTokens") or 0)
            tk["cache_write"] += int(v.get("cacheCreationInputTokens") or 0)
            tk["output"] += int(v.get("outputTokens") or 0)
            tk["reasoning"] += int(v.get("thinkingTokens") or 0)
    else:
        u = result.get("usage") or {}
        tk["input"] = int(u.get("input_tokens") or 0)
        tk["cached"] = int(u.get("cache_read_input_tokens") or 0)
        tk["cache_write"] = int(u.get("cache_creation_input_tokens") or 0)
        tk["output"] = int(u.get("output_tokens") or 0)
        tk["reasoning"] = int((u.get("output_tokens_details") or {}).get("thinking_tokens") or 0)
    return r


def codex_cost(tokens: dict, price: dict) -> float:
    """Equivalent USD from a models.toml price. tokens['input'] is uncached input; output already includes reasoning
    (OpenAI semantics: reasoning_output_tokens is a subset of output_tokens); no cache price = billed as input."""
    cached = price["cached"] if price.get("cached") is not None else price["input"]
    return (tokens["input"] * price["input"] + tokens["cached"] * cached + tokens["output"] * price["output"]) / 1e6


def parse_codex(events: list[dict], price: dict | None = None) -> dict:
    r = {"final_answer": "", "tool_calls": 0, "tokens": _empty_tokens(), "cost_usd": 0.0,
         "cost_basis": "equivalent", "skill_loaded": False, "error": None}
    for e in events:
        t = e.get("type", "")
        item = e.get("item") or {}
        itype = item.get("type") or item.get("item_type")
        if t == "item.completed":
            if itype == "agent_message":
                r["final_answer"] = str(item.get("text") or "")
            elif itype in ("command_execution", "file_change", "mcp_tool_call", "web_search", "local_shell_call"):
                r["tool_calls"] += 1
            if itype == "command_execution" and _skill_hit(str(item.get("command") or "")):
                r["skill_loaded"] = True
        elif t == "turn.completed":
            u = e.get("usage") or {}
            inp = int(u.get("input_tokens") or 0)
            cached = int(u.get("cached_input_tokens") or 0)
            tk = r["tokens"]
            tk["input"] += max(inp - cached, 0)
            tk["cached"] += cached
            tk["cache_write"] += int(u.get("cache_write_input_tokens") or 0)
            tk["output"] += int(u.get("output_tokens") or 0)
            tk["reasoning"] += int(u.get("reasoning_output_tokens") or 0)
        elif t in ("turn.failed", "error"):
            r["error"] = json.dumps(e)[:500]
    r["cost_usd"] = codex_cost(r["tokens"], price) if price else 0.0
    if not price:
        r["cost_basis"] = "unknown"
    return r


def tool_texts(adapter: str, events: list[dict]) -> str:
    """Every tool call's input (commands, paths, arguments) as text, one per line, for transcript_regex."""
    ad = ADAPTERS.get(adapter)
    return ad.tool_texts(events) if ad else ""


def events_path(runs_dir: Path, rid: str) -> Path | None:
    """The saved events of a run: .events.jsonl.gz (current) or .events.jsonl (older runs)."""
    for name in (f"{rid}.events.jsonl.gz", f"{rid}.events.jsonl"):
        if (runs_dir / name).exists():
            return runs_dir / name
    return None


def read_events(path: Path | None) -> list[dict]:
    if path is None or not path.exists():
        return []
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
            return _parse_lines(fh.read())
    return _parse_lines(path.read_text(encoding="utf-8", errors="replace"))


def gzip_events(path: Path) -> Path:
    """Compress <run>.events.jsonl to .jsonl.gz and remove the plain file; returns the new path."""
    gz = path.with_name(path.name + ".gz")
    with open(path, "rb") as src, gzip.open(gz, "wb", compresslevel=6) as dst:
        shutil.copyfileobj(src, dst)
    path.unlink()
    return gz


# ============================================================ workdir helpers

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def write_fixtures(workdir: Path, fixtures: list[dict]) -> dict[str, str]:
    hashes = {}
    for f in fixtures:
        p = workdir / f["path"]
        p.parent.mkdir(parents=True, exist_ok=True)
        data = fixture_bytes(f)
        p.write_bytes(data)
        if "src" in f and os.access(_fixture_src(f["src"]), os.X_OK):
            p.chmod(0o755)
        hashes[f["path"]] = sha256_bytes(data)
    return hashes


def list_files(workdir: Path) -> list[str]:
    """Relative POSIX paths of every regular file outside INFRA_DIRS."""
    out = []
    for root, dirs, files in os.walk(workdir):
        dirs[:] = sorted(d for d in dirs if d not in INFRA_DIRS)
        for fn in sorted(files):
            if fn == ".DS_Store":
                continue
            p = Path(root) / fn
            if p.is_file() and not p.is_symlink():
                out.append(p.relative_to(workdir).as_posix())
    return out


def skill_file_index(root: Path, with_paths: bool = False) -> set[tuple[str, str]]:
    """{(basename, sha256)} of every non-empty file of a skill tree, to recognise copies of it in a workdir.
    with_paths adds ("path", relpath) entries of multi-segment paths (references/x.md…) for --regrade, where the
    skill may have changed since the run so a copy no longer matches byte for byte."""
    out = set()
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKILL_IGNORE]
        for fn in files:
            p = Path(dirpath) / fn
            if fn not in SKILL_IGNORE and p.is_file() and p.stat().st_size > 0:
                out.add((fn, sha256_bytes(p.read_bytes())))
                rel = p.relative_to(root).as_posix()
                if with_paths and "/" in rel:
                    out.add(("path", rel))
    return out


_SKILL_INDEX: set[tuple[str, str]] | None = None


def current_skill_index() -> set[tuple[str, str]]:
    global _SKILL_INDEX
    if _SKILL_INDEX is None:
        _SKILL_INDEX = skill_file_index(SKILL_DIR, with_paths=True)
    return _SKILL_INDEX


def classify_files(workdir: Path, fixture_hashes: dict[str, str],
                   skill_index: set[tuple[str, str]] | None = None) -> list[dict]:
    """Every file with status new / modified / fixture (unchanged input) / skill-copy (byte-identical to a skill
    file of the same name: the agent copied the skill into the workdir). Assertions ignore skill copies."""
    out = []
    for rel in list_files(workdir):
        p = workdir / rel
        data = p.read_bytes()
        digest = sha256_bytes(data)
        if rel in fixture_hashes:
            status = "fixture" if digest == fixture_hashes[rel] else "modified"
        elif skill_index and data and ((Path(rel).name, digest) in skill_index
                                       or any(("path", "/".join(rel.split("/")[i:])) in skill_index
                                              for i in range(rel.count("/")))):
            status = "skill-copy"
        else:
            status = "new"
        out.append({"path": rel, "status": status, "bytes": len(data)})
    return out


def glob_to_regex(pattern: str) -> re.Pattern:
    """'**/' matches zero or more directories, '*' and '?' stay within one segment."""
    i, out = 0, ""
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
        elif pattern.startswith("**", i):
            out += ".*"
            i += 2
        elif pattern[i] == "*":
            out += "[^/]*"
            i += 1
        elif pattern[i] == "?":
            out += "[^/]"
            i += 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return re.compile(out + r"\Z")


def match_glob(paths: list[str], pattern: str) -> list[str]:
    rx = glob_to_regex(pattern)
    return [p for p in paths if rx.match(p)]


def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def display_width(s: str) -> int:
    n = 0
    for ch in s:
        if unicodedata.combining(ch) or ch in "​‍️":
            continue
        n += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return n


BOX_CHARS = set("│┃║┌┐└┘╭╮╰╯├┤┬┴┼╔╗╚╝╠╣╦╩╬═─━╞╡╟╢")
EDGE_CHARS = set("│┃║┌┐└┘╭╮╰╯├┤╔╗╚╝╠╣╟╢╞╡|+")


def code_blocks(text: str) -> list[list[str]]:
    blocks, cur, inside = [], [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            if inside:
                blocks.append(cur)
                cur = []
            inside = not inside
            continue
        if inside:
            cur.append(line)
    if inside and cur:
        blocks.append(cur)
    return blocks


def box_sketch_widths(text: str) -> list[list[int]]:
    """For each fenced block drawn as a box (≥3 bordered rows with box-drawing glyphs),
    the display widths of its bordered rows (first and last non-space char are edges)."""
    result = []
    for block in code_blocks(text):
        if not any(ch in BOX_CHARS for line in block for ch in line):
            continue
        widths = []
        for line in block:
            s = line.rstrip()
            st = s.lstrip()
            if len(st) >= 2 and st[0] in EDGE_CHARS and st[-1] in EDGE_CHARS:
                widths.append(display_width(s))
        if len(widths) >= 3:
            result.append(widths)
    return result


HEX_RX = re.compile(r"(?<![0-9A-Za-z&])#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")


def hexes_in(text: str) -> set[str]:
    out = set()
    for h in HEX_RX.findall(text):
        h = h.lower()
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        out.add("#" + h)
    return out


def lint_mock(path: Path, skill_dir: Path | None = None) -> dict:
    """Run the skill's own linter on one file: {errors, warnings, exit, out}."""
    skill_dir = skill_dir or SKILL_DIR
    try:
        p = subprocess.run([sys.executable, str(skill_dir / "scripts" / "render_mockup.py"), str(path), "--check"],
                           capture_output=True, text=True, timeout=60)
        out = (p.stdout + p.stderr).strip()
        code = p.returncode
    except subprocess.TimeoutExpired:
        return {"errors": None, "warnings": None, "exit": None, "out": "timeout"}
    m = re.search(r"(\d+) error\(s\), (\d+) warning\(s\)", out)
    errors = int(m.group(1)) if m else None
    warnings = int(m.group(2)) if m else None
    craft = sorted(set(re.findall(r"WARN: craft (CR\d+)", out)))
    return {"errors": errors, "warnings": warnings, "exit": code, "out": out[-1500:], "craft": craft}


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgb_dist(a: str, b: str) -> float:
    return sum((x - y) ** 2 for x, y in zip(hex_rgb(a), hex_rgb(b))) ** 0.5


def contrast_ok(theme_id: str, skill_dir: Path | None = None) -> tuple[bool, str]:
    """The skill's contrast_check.py at truecolor and at 16 colors; ok when both exit 0."""
    skill_dir = skill_dir or SKILL_DIR
    res = []
    for extra in ([], ["--depth", "16"]):
        try:
            p = subprocess.run([sys.executable, str(skill_dir / "scripts" / "contrast_check.py"), theme_id, *extra],
                               capture_output=True, text=True, timeout=60)
            res.append(p.returncode)
        except subprocess.TimeoutExpired:
            res.append(None)
    return res == [0, 0], f"contrast_check {theme_id}: truecolor exit {res[0]}, 16 colors exit {res[1]}"


def mock_header(text: str) -> dict:
    hdr = {}
    for line in text.splitlines():
        if not line.startswith("#!"):
            break
        body = line[2:].strip()
        if ":" in body and not body.startswith("region") and not body.startswith("focus"):
            k, v = body.split(":", 1)
            hdr.setdefault(k.strip(), v.strip())
    return hdr


def parse_caps(value: str) -> dict:
    out = {}
    for tok in value.split():
        if "=" in tok:
            k, v = tok.split("=", 1)
            out[k] = v.split(",")
    return out


def mock_variant(rel: str) -> str:
    name = Path(rel).name
    if name.endswith(".mock"):
        name = name[:-5]
    return name.split("--")[0] if "--" in name else name


# ============================================================ assertions

def check_program(a: dict, ctx: dict) -> tuple[bool, str]:
    """Evaluate one program assertion. ctx: workdir, answer, files (classify_files output),
    skill_dir, fixture_hexes."""
    t = a["type"]
    wd: Path = ctx["workdir"]
    files = [f for f in ctx["files"] if f["status"] != "skill-copy"]
    all_paths = [f["path"] for f in files]
    produced = [f["path"] for f in files if f["status"] in ("new", "modified")]
    answer = ctx.get("answer") or ""

    if t == "answer_regex":
        n = len(re.findall(a["pattern"], answer))
        lo, hi = a.get("min", 1), a.get("max")
        ok = n >= lo and (hi is None or n <= hi)
        return ok, f"{n} match(es) (need >= {lo}{'' if hi is None else f', <= {hi}'})"

    if t == "transcript_regex":
        tr = ctx.get("transcript") or ""
        n = len(re.findall(a["pattern"], tr))
        lo, hi = a.get("min", 1), a.get("max")
        ok = n >= lo and (hi is None or n <= hi)
        return ok, f"{n} tool-call match(es) (need >= {lo}{'' if hi is None else f', <= {hi}'})"

    if t == "hex_near":
        pal = json.loads(_fixture_src(a["palette"]).read_text())
        colors = [c.lower() for c in pal.get("colors", [])]
        used: dict[str, str] = {}
        if a.get("scope", "answer") in ("answer", "both"):
            for h in hexes_in(answer):
                used.setdefault(h, "answer")
        if a.get("scope", "answer") in ("files", "both"):
            for p in match_glob(produced, a.get("files_glob", "**/*.md")):
                for h in hexes_in(read_text(wd / p)):
                    used.setdefault(h, p)
        lim = a.get("max_dist", 30)
        far = {}
        for h, where in used.items():
            d = min(rgb_dist(h, c) for c in colors)
            if d > lim:
                far[h] = (where, d)
        if len(used) < a.get("min_hex", 0):
            return False, f"{len(used)} hex value(s) reported, need >= {a.get('min_hex')}"
        if far:
            return False, f"{len(far)} of {len(used)} hex not in the screenshot (> {lim} RGB away): " + ", ".join(
                f"{h} ({w}, {d:.0f})" for h, (w, d) in sorted(far.items())[:8])
        return True, f"{len(used)} hex value(s), all within {lim} of the ground-truth palette ({len(colors)} colors)"

    if t == "mock_craft":
        matched = match_glob(all_paths, a["glob"])
        if len(matched) < a.get("min_files", 1):
            return False, f"{len(matched)} .mock file(s), need >= {a.get('min_files', 1)}"
        bad = []
        for p in matched:
            res = lint_mock(wd / p, ctx.get("skill_dir", SKILL_DIR))
            if res["errors"] is None:
                bad.append(f"{p}: does not lint")
            elif res["craft"]:
                bad.append(f"{p}: {','.join(res['craft'])}")
        return not bad, ("unwaived craft warnings: " + "; ".join(bad[:6]) if bad
                         else f"{len(matched)} file(s), no unwaived craft warning")

    if t == "answer_box_widths":
        sketches = box_sketch_widths(answer)
        if not sketches:
            return True, "no box sketch in the answer (vacuous pass)"
        bad = []
        for i, ws in enumerate(sketches):
            if len(set(ws)) > 1:
                bad.append(f"sketch {i + 1}: row widths {sorted(set(ws))}")
            elif a.get("max_width") and ws[0] > a["max_width"]:
                bad.append(f"sketch {i + 1}: {ws[0]} cols > {a['max_width']}")
        return (not bad), ("; ".join(bad) if bad else f"{len(sketches)} sketch(es), widths consistent")

    if t == "file_glob":
        n = len(match_glob(produced if a.get("produced_only", True) else all_paths, a["glob"]))
        lo, hi = a.get("min", 1), a.get("max")
        return n >= lo and (hi is None or n <= hi), f"{n} file(s) match {a['glob']}"

    if t == "file_regex":
        matched = match_glob(all_paths, a["glob"])
        mode = a.get("mode", "any")
        rx = re.compile(a["pattern"])
        prep = (lambda s: ANSI_ESCAPE_RX.sub("", s)) if a.get("strip_ansi") else (lambda s: s)
        hits = [p for p in matched if rx.search(prep(read_text(wd / p)))]
        if mode == "none":
            return not hits, (f"pattern found in {hits[:5]}" if hits else f"absent in {len(matched)} file(s)")
        if not matched:
            return False, f"no file matches {a['glob']}"
        if mode == "all":
            miss = [p for p in matched if p not in hits]
            return not miss, (f"missing in {miss[:5]}" if miss else f"present in all {len(matched)} file(s)")
        return bool(hits), f"present in {len(hits)}/{len(matched)} file(s)"

    if t == "files_contain":
        pool = match_glob(produced, a.get("glob", "**/*"))
        text = "\n".join(read_text(wd / p) for p in pool if Path(p).suffix in TEXT_SUFFIXES or not Path(p).suffix)
        found = [s for s in a["strings"] if s in text]
        need = a.get("min_distinct", 1)
        return len(found) >= need, f"{len(found)} of {len(a['strings'])} found in {len(pool)} produced file(s): {found[:8]}"

    if t == "mock_lint":
        matched = match_glob(all_paths, a["glob"])
        need = a.get("min_files", 1)
        if len(matched) < need:
            return False, f"{len(matched)} .mock file(s), need >= {need}"
        bad = []
        for p in matched:
            res = lint_mock(wd / p, ctx.get("skill_dir", SKILL_DIR))
            if res["errors"] is None or res["errors"] > a.get("max_errors", 0):
                bad.append(f"{p}: {res['errors']} error(s)")
        return not bad, ("; ".join(bad[:6]) if bad else f"{len(matched)} file(s), 0 errors")

    if t == "mock_caps":
        matched = match_glob(all_paths, a["glob"])
        if not matched:
            return False, f"no file matches {a['glob']}"
        problems = []
        for p in matched:
            caps_line = mock_header(read_text(wd / p)).get("caps")
            if caps_line is None:
                if a.get("require_line", True):
                    problems.append(f"{p}: no #! caps: line")
                continue
            caps = parse_caps(caps_line)
            for key, forbidden in (a.get("forbid") or {}).items():
                bad = set(caps.get(key, [])) & set(forbidden)
                if bad:
                    problems.append(f"{p}: {key}={','.join(sorted(bad))}")
        return not problems, ("; ".join(problems[:6]) if problems else f"{len(matched)} file(s) ok")

    if t == "mock_variants":
        matched = match_glob(all_paths, a["glob"])
        variants = sorted({mock_variant(p) for p in matched})
        need = a.get("min", 3)
        return len(variants) >= need, f"{len(variants)} variant(s): {variants[:10]}"

    if t == "hex_known":
        skill_dir = ctx.get("skill_dir", SKILL_DIR)
        fx: set[str] = set(ctx.get("fixture_hexes") or set())
        per_source: dict[Path, set[str]] = {}
        for src in a["sources"]:
            for p in sorted(skill_dir.glob(src)):
                per_source[p] = hexes_in(read_text(p))
        known = set(fx).union(*per_source.values()) if per_source else set(fx)
        scope = a.get("scope", "both")
        used: dict[str, str] = {}
        if scope in ("answer", "both"):
            for h in hexes_in(answer):
                used.setdefault(h, "answer")
        if scope in ("files", "both"):
            for p in match_glob(produced, a.get("files_glob", "**/*")):
                if Path(p).suffix in TEXT_SUFFIXES:
                    for h in hexes_in(read_text(wd / p)):
                        used.setdefault(h, p)
        unknown = {h: w for h, w in used.items() if h not in known}
        if unknown:
            return False, f"{len(unknown)} invented hex: " + ", ".join(f"{h} ({w})" for h, w in sorted(unknown.items())[:8])
        if len(used) < a.get("min_used", 0):
            return False, f"{len(used)} hex value(s) used, need >= {a['min_used']}"
        if not a.get("same_source"):
            return True, f"{len(used)} hex value(s) used, all known ({len(known)} known)"
        need = set(used) - fx
        owners = [p for p, hs in per_source.items() if need <= hs]
        if not owners:
            return False, f"{len(used)} known hex value(s), but no single source holds them all (mixed schemes)"
        names = [p.stem for p in owners]
        if a.get("contrast"):
            notes = []
            for p in owners:
                ok, note = contrast_ok(p.stem, skill_dir)
                notes.append(note)
                if ok:
                    return True, f"{len(used)} hex value(s), all from {p.stem}; {note}"
            return False, f"all from {', '.join(names)}, but contrast fails: " + "; ".join(notes[:3])
        return True, f"{len(used)} hex value(s), all from {', '.join(names[:4])}"

    if t == "fixture_unchanged":
        st = next((f["status"] for f in files if f["path"] == a["path"]), "deleted")
        return st == "fixture", f"{a['path']}: {st}"

    if t == "no_new_files":
        new = [p for p in produced]
        return not new, (f"produced {new[:8]}" if new else "no files written")

    raise ValueError(f"not a program assertion: {t}")


def grade_program(case: dict, ctx: dict) -> list[dict]:
    """Static program assertions (no command of the agent's is run, no model is called)."""
    out = []
    for a in case["assertions"]:
        if a["type"] in MODEL_TYPES or a["type"] in EXECUTED_TYPES:
            continue
        try:
            ok, detail = check_program(a, ctx)
        except Exception as e:  # a broken assertion must not kill the run
            ok, detail = None, f"assertion error: {e!r}"
        out.append({"id": a["id"], "type": a["type"], "kind": "program", "neutral": a.get("neutral", True),
                    "passed": ok, "detail": detail})
    return out


# ============================================================ executed assertions

PROBE_PY = r'''
import json, os, signal, subprocess, sys, time
out, pidfile, cmd = sys.argv[1], sys.argv[2], sys.argv[3]
signal.signal(signal.SIGINT, signal.SIG_IGN)       # Ctrl-C in the pane is for the child only

def _child():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.signal(signal.SIGTERM, signal.SIG_DFL)

p = subprocess.Popen(["/bin/bash", "-c", "exec " + cmd], preexec_fn=_child)
with open(pidfile, "w") as fh:
    fh.write(str(p.pid))
rc = p.wait()
status = rc if rc >= 0 else 128 - rc                # shell convention: killed by signal N -> 128+N
st = subprocess.run(["stty", "-a"], capture_output=True, text=True)
with open(out + ".tmp", "w") as fh:
    json.dump({"status": status, "raw_rc": rc, "stty": st.stdout + st.stderr}, fh)
os.replace(out + ".tmp", out)
time.sleep(60)                                      # keep the pane: the runner reads #{alternate_on} now
'''


_UV_DIRS: dict[str, str] | None = None


def _uv_dirs() -> dict[str, str]:
    """Real uv cache / python dirs, so `uv run --offline` works under a fresh HOME."""
    global _UV_DIRS
    if _UV_DIRS is None:
        _UV_DIRS = {}
        if shutil.which("uv"):
            for var, sub in (("UV_CACHE_DIR", "cache"), ("UV_PYTHON_INSTALL_DIR", "python")):
                try:
                    p = subprocess.run(["uv", sub, "dir"], capture_output=True, text=True, timeout=20)
                    if p.returncode == 0 and p.stdout.strip():
                        _UV_DIRS[var] = p.stdout.strip()
                except (OSError, subprocess.TimeoutExpired):
                    pass
    return _UV_DIRS


def exec_env(home: Path, tmux_dir: Path) -> dict[str, str]:
    """Environment for executed checks, allow-listed from scratch (base_env): no TMUX (a tmux client must never
    reach the user's server), a private TMUX_TMPDIR, a fresh HOME, uv offline with the real cache, plain TERM,
    and no secret of the orchestrator's."""
    env = base_env(home, tmux_dir)
    env["TMPDIR"] = os.environ.get("TMPDIR") or tempfile.gettempdir()
    env.update({"UV_OFFLINE": "1", "TERM": "xterm-256color", "PYTHONDONTWRITEBYTECODE": "1"})
    if os.environ.get("NO_COLOR"):
        env["NO_COLOR"] = os.environ["NO_COLOR"]
    env.update(_uv_dirs())
    return env


def sandbox_prefix() -> list[str]:
    """macOS sandbox-exec denying outbound IP (set EVAL_NO_SANDBOX=1 to disable); [] elsewhere."""
    if os.environ.get("EVAL_NO_SANDBOX") or not shutil.which("sandbox-exec"):
        return []
    return ["sandbox-exec", "-p", SANDBOX_PROFILE]


def _short_tmp(prefix: str) -> Path:
    """A short temp dir (unix socket paths are limited to ~104 bytes on macOS)."""
    base = "/tmp" if os.path.isdir("/tmp") and len(tempfile.gettempdir()) > 40 else None
    return Path(tempfile.mkdtemp(prefix=prefix, dir=base))


def check_files(wd: Path, checks: list[dict]) -> list[str]:
    """files: [{path, exists?, regex?, not_regex?, min_lines?, max_lines?}] -> list of problems."""
    probs = []
    for fc in checks or []:
        p = wd / fc["path"]
        if not p.is_file():
            if fc.get("exists", True):
                probs.append(f"{fc['path']}: missing")
            continue
        if fc.get("exists") is False:
            probs.append(f"{fc['path']}: should not exist")
        txt = p.read_bytes().decode("utf-8", errors="replace")
        if fc.get("regex") and not re.search(fc["regex"], txt):
            probs.append(f"{fc['path']}: no match for {fc['regex']!r} (got {txt[:80]!r})")
        if fc.get("not_regex") and re.search(fc["not_regex"], txt):
            m = re.search(fc["not_regex"], txt)
            probs.append(f"{fc['path']}: contains {m.group(0)!r}")
        n = len(txt.splitlines())
        if n < fc.get("min_lines", 0):
            probs.append(f"{fc['path']}: {n} line(s) < {fc['min_lines']}")
        if fc.get("max_lines") is not None and n > fc["max_lines"]:
            probs.append(f"{fc['path']}: {n} line(s) > {fc['max_lines']}")
    return probs


def requirement_ok(cmd: str, env: dict, cwd: Path, timeout: int = 120) -> tuple[bool, str]:
    try:
        p = subprocess.run(["bash", "-c", cmd], cwd=cwd, env=env, stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, timeout=timeout)
        return p.returncode == 0, (p.stdout + p.stderr).strip()[-200:]
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, repr(e)


def run_exec(a: dict, wd: Path, env: dict) -> tuple[bool | None, str]:
    """`bash -o pipefail -c CMD` in the workdir (stdin /dev/null, so stdout is never a TTY), then check the
    exit status, stdout/stderr and files."""
    if a.get("skip_unless"):
        ok, why = requirement_ok(a["skip_unless"], env, wd)
        if not ok:
            return None, f"skipped: requirement not met ({a['skip_unless']}): {why}"
    timeout = a.get("timeout", 30)
    try:
        p = subprocess.run(sandbox_prefix() + ["bash", "-o", "pipefail", "-c", a["cmd"]], cwd=wd, env=env,
                           stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"timeout after {timeout}s: {a['cmd']}"
    out = p.stdout.decode("utf-8", errors="replace")
    err = p.stderr.decode("utf-8", errors="replace")
    probs = []
    expect = a.get("expect_exit", [0])
    if expect is not None and p.returncode not in expect:
        probs.append(f"exit {p.returncode} not in {expect}")
    for key, text, want in (("stdout_regex", out, True), ("stdout_not_regex", out, False),
                            ("stderr_regex", err, True), ("stderr_not_regex", err, False)):
        if key in a:
            m = re.search(a[key], text)
            if want and not m:
                probs.append(f"{key.split('_')[0]} lacks {a[key]!r}")
            if not want and m:
                probs.append(f"{key.split('_')[0]} has {m.group(0)!r}")
    probs += check_files(wd, a.get("files", []))
    tail = (err.strip().splitlines() or [""])[-1][:160]
    if probs:
        return False, "; ".join(probs[:5]) + (f" | stderr: {tail}" if tail else "")
    return True, f"exit {p.returncode}; checks ok ({a['cmd']})"


def stty_flags_ok(stty: str, flags=("icanon", "echo", "isig")) -> tuple[bool, list[str]]:
    toks = set(stty.replace(";", " ").split())
    missing = [f for f in flags if f not in toks or f"-{f}" in toks]
    return not missing, missing


def run_tty_probe(a: dict, wd: Path, env: dict) -> tuple[bool | None, str]:
    """Run CMD in a pane of a private tmux server (`tmux -L evalprobe-<rand> -f /dev/null`, TMUX_TMPDIR in a temp
    dir), wait until the screen matches `ready`, send `actions` (keys, literal text, a signal to the app's pid),
    wait for the exit, then check the exit status (128+N for a signal), `stty -a` (icanon echo isig back on),
    #{alternate_on} while running and after exit, and files. Only that server is ever killed."""
    if not shutil.which("tmux"):
        return None, "skipped: tmux not found"
    if a.get("skip_unless"):
        ok, why = requirement_ok(a["skip_unless"], env, wd)
        if not ok:
            return None, f"skipped: requirement not met ({a['skip_unless']}): {why}"
    pdir = _short_tmp("ep")
    sock = f"evalprobe-{uuid.uuid4().hex[:8]}"
    penv = dict(env, TMUX_TMPDIR=str(pdir))
    T = ["tmux", "-L", sock, "-f", "/dev/null"]

    def tm(*args, check=False) -> str:
        p = subprocess.run(T + list(args), env=penv, capture_output=True, text=True, timeout=10)
        if check and p.returncode != 0:
            raise RuntimeError(f"tmux {args[0]} failed: {p.stderr.strip()}")
        return p.stdout

    (pdir / "probe.py").write_text(PROBE_PY)
    res, pidf = pdir / "res.json", pdir / "pid"
    cols, rows = (int(x) for x in a.get("size", "80x24").split("x"))
    inner = sandbox_prefix() + [sys.executable, str(pdir / "probe.py"), str(res), str(pidf), a["cmd"]]
    line = "env -u TMUX -u TMUX_PANE TERM=xterm-256color " + " ".join(shlex.quote(x) for x in inner)
    screen, probs, info = "", [], []
    try:
        tm("new-session", "-d", "-s", "p", "-x", str(cols), "-y", str(rows), "-c", str(wd), line, check=True)
        deadline = time.time() + a.get("ready_timeout", 8)
        ready_rx = re.compile(a.get("ready", r"\S"))
        ready = False
        while time.time() < deadline:
            screen = tm("capture-pane", "-p", "-t", "p")
            if ready_rx.search(screen):
                ready = True
                break
            if res.exists():
                break
            time.sleep(0.2)
        if not ready:
            last = " | ".join(x.strip() for x in screen.strip().splitlines()[-3:])[:200]
            return False, f"screen never matched {a.get('ready')!r} (exited: {res.exists()}; last rows: {last!r})"
        time.sleep(a.get("settle", 0.3))
        alt_during = tm("display", "-p", "-t", "p", "#{alternate_on}").strip() == "1"
        for act in a.get("actions", []):
            if "keys" in act:
                tm("send-keys", "-t", "p", *act["keys"].split())
            elif "text" in act:
                tm("send-keys", "-t", "p", "-l", act["text"])
            elif "signal" in act:
                pid = int(pidf.read_text().strip())
                os.kill(pid, getattr(signal, "SIG" + act["signal"].upper().removeprefix("SIG")))
            time.sleep(act.get("sleep", 0.4))
        deadline = time.time() + a.get("exit_timeout", 8)
        while time.time() < deadline and not res.exists():
            time.sleep(0.2)
        if not res.exists():
            screen = tm("capture-pane", "-p", "-t", "p")
            last = " | ".join(x.strip() for x in screen.strip().splitlines()[-3:])[:200]
            return False, f"the app did not exit after {a.get('actions')} (last rows: {last!r})"
        time.sleep(0.2)
        alt_after = tm("display", "-p", "-t", "p", "#{alternate_on}").strip() == "1"
        r = json.loads(res.read_text())
        info.append(f"exit {r['status']}")
        if "expect_status" in a and r["status"] not in a["expect_status"]:
            probs.append(f"exit status {r['status']} not in {a['expect_status']}")
        if a.get("stty_restored"):
            ok, missing = stty_flags_ok(r["stty"])
            info.append("stty restored" if ok else f"stty missing {missing}")
            if not ok:
                probs.append(f"terminal left without {' '.join(missing)}")
        if "alt_screen_during" in a:
            info.append(f"alt screen while running: {alt_during}")
            if alt_during != a["alt_screen_during"]:
                probs.append(f"alternate screen while running = {alt_during}, want {a['alt_screen_during']}")
        if "alt_screen_after" in a and alt_after != a["alt_screen_after"]:
            probs.append(f"alternate screen still on after exit" if alt_after else "alternate screen off after exit")
        probs += check_files(wd, a.get("files", []))
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as e:
        return None, f"probe error: {e!r}"
    finally:
        try:
            subprocess.run(T + ["kill-server"], env=penv, capture_output=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            pass
        shutil.rmtree(pdir, ignore_errors=True)
    return (not probs), ("; ".join(probs) if probs else "; ".join(info) + "; checks ok")


def run_frame_match(a: dict, wd: Path, env: dict, skill_dir: Path | None = None) -> tuple[bool | None, str]:
    """compare.py MOCK FRAME (the skill's own cell diff); pass when the text cells that differ are at most
    max_text_pct % (default 20) and, with max_any_pct, all differences too."""
    skill_dir = skill_dir or SKILL_DIR
    mock, frame = wd / a["mock"], wd / a["frame"]
    if not frame.is_file() or frame.stat().st_size == 0:
        return False, f"{a['frame']}: missing or empty"
    if not mock.is_file():
        return None, f"{a['mock']}: missing (fixture deleted?)"
    with tempfile.TemporaryDirectory() as td:
        try:
            p = subprocess.run([sys.executable, str(skill_dir / "scripts" / "compare.py"), str(mock), str(frame),
                                "-o", str(Path(td) / "cmp.html")], capture_output=True, text=True, timeout=120,
                               env=env)
        except subprocess.TimeoutExpired:
            return False, "compare.py timeout"
    rows = dict(re.findall(r"^\| (text|any difference) \| \d+ \| \d+ \| ([\d.]+)% \|", p.stdout, re.M))
    if "text" not in rows:
        return False, f"compare.py could not diff the frame: {(p.stdout + p.stderr).strip()[-200:]}"
    text_pct, any_pct = float(rows["text"]), float(rows.get("any difference", "nan"))
    ok = text_pct <= a.get("max_text_pct", 20) and ("max_any_pct" not in a or any_pct <= a["max_any_pct"])
    return ok, f"text cells differing {text_pct:.1f}% (max {a.get('max_text_pct', 20)}), any difference {any_pct:.1f}%"


def grade_executed(case: dict, wd: Path, env: dict, skill_dir: Path | None = None) -> list[dict]:
    """Executed assertions in case order, all in the same workdir (a later one may read an earlier one's file)."""
    skill_dir = skill_dir or SKILL_DIR
    out = []
    for a in case["assertions"]:
        if a["type"] not in EXECUTED_TYPES:
            continue
        try:
            if a["type"] == "exec":
                ok, detail = run_exec(a, wd, env)
            elif a["type"] == "tty_probe":
                ok, detail = run_tty_probe(a, wd, env)
            else:
                ok, detail = run_frame_match(a, wd, env, skill_dir)
        except Exception as e:  # never kill the run
            ok, detail = None, f"assertion error: {e!r}"
        out.append({"id": a["id"], "type": a["type"], "kind": "executed", "neutral": a.get("neutral", True),
                    "passed": ok, "detail": detail})
    return out


def executed_in_copy(case: dict, src: Path, skill_dir: Path | None = None) -> list[dict]:
    """Run the executed assertions in a scratch copy of `src` (the workdir or a saved .files dir), so their
    outputs never land in the results; HOME and TMUX_TMPDIR are fresh."""
    skill_dir = skill_dir or SKILL_DIR
    if not any(a["type"] in EXECUTED_TYPES for a in case["assertions"]):
        return []
    root = _short_tmp("ex")
    try:
        wd = root / "w"
        shutil.copytree(src, wd, symlinks=True,
                        ignore=shutil.ignore_patterns(".agents", ".claude", ".git", "__pycache__", ".tmp", ".venv"))
        (root / "h").mkdir()
        (root / "t").mkdir()
        return grade_executed(case, wd, exec_env(root / "h", root / "t"), skill_dir)
    finally:
        _kill_tmux_servers(root / "t")
        shutil.rmtree(root, ignore_errors=True)


def _kill_tmux_servers(tmux_dir: Path) -> None:
    """Kill every tmux server whose socket lives under tmux_dir (a run's private TMUX_TMPDIR), nothing else."""
    if not tmux_dir.is_dir() or not shutil.which("tmux"):
        return
    for sockdir in tmux_dir.glob("tmux-*"):
        for sock in sockdir.iterdir():
            try:
                subprocess.run(["tmux", "-S", str(sock), "kill-server"], capture_output=True, timeout=10,
                               env={k: v for k, v in os.environ.items() if k not in ("TMUX", "TMUX_PANE")})
            except (OSError, subprocess.TimeoutExpired):
                pass


def apply_blocked(case: dict, assertions: list[dict]) -> list[dict]:
    """An assertion with `blocked_by: [ids]` whose prerequisite failed gets an effective failed grade with a
    `blocked:` detail (for example probes that need an input file the agent overwrote). What it observed is kept in
    `observed_passed` / `observed_detail`; it is never turned into a pass, and nothing is restored."""
    deps = {a["id"]: a.get("blocked_by") or [] for a in case.get("assertions", [])}
    state = {a["id"]: a.get("passed") for a in assertions}
    out = []
    for a in assertions:
        failed = [d for d in deps.get(a["id"], []) if state.get(d) is False]
        if failed:
            a = {**a, "observed_passed": a.get("passed"), "observed_detail": a.get("detail"), "passed": False,
                 "detail": f"blocked: {', '.join(failed)} failed"}
        out.append(a)
    return out


def reapply_blocked(case: dict, assertions: list[dict]) -> list[dict]:
    """On regrade: restore any kept observation (a result re-run since then carries none), then block again from the
    current prerequisite grades, so a block whose prerequisite now passes is lifted."""
    unblocked = [{**{k: v for k, v in x.items() if k not in ("observed_passed", "observed_detail")},
                  "passed": x["observed_passed"], "detail": x.get("observed_detail")}
                 if "observed_passed" in x else x for x in assertions]
    return apply_blocked(case, unblocked)


def score(assertions: list[dict]) -> dict:
    graded = [a for a in assertions if a["passed"] is not None]
    neutral = [a for a in graded if a.get("neutral", True)]
    p = sum(1 for a in graded if a["passed"])
    pn = sum(1 for a in neutral if a["passed"])
    return {"passed": p, "graded": len(graded), "rate": (p / len(graded)) if graded else None,
            "neutral_passed": pn, "neutral_graded": len(neutral),
            "neutral_rate": (pn / len(neutral)) if neutral else None,
            "all_passed": bool(graded) and p == len(graded)}


# ============================================================ judge

JUDGE_PROMPT = """You grade an AI assistant's work on a user request about a terminal user interface.
Answer every question strictly "yes" or "no", using only the material below. When the material does not show
the behavior, answer "no". Do not reward effort or length.

Return ONLY a JSON object, no prose, no code fence:
{{"answers": [{{"id": "<question id>", "answer": "yes" or "no", "reason": "<one short sentence>"}}]}}

QUESTIONS
{questions}

USER REQUEST
{prompt}

FILES IN THE WORKING DIRECTORY AFTER THE RUN (status: new / modified / fixture = unchanged input)
{files}

FINAL ANSWER OF THE ASSISTANT
<<<
{answer}
>>>

CONTENTS OF SELECTED FILES THE ASSISTANT WROTE
{contents}
{reference}"""

REFERENCE_BLOCK = """
GROUND TRUTH FOR THE GRADER (the assistant never saw these files; use them only to check the answer's claims)
{refs}
"""


def judge_context(case: dict, ctx: dict, max_file: int = 8000, max_total: int = 40000) -> str:
    globs = case.get("judge_context") or []
    produced = [f["path"] for f in ctx["files"] if f["status"] in ("new", "modified")]
    chosen: list[str] = []
    for g in globs:
        for p in match_glob(produced, g):
            if p not in chosen and Path(p).suffix in TEXT_SUFFIXES:
                chosen.append(p)
    parts, total = [], 0
    for p in chosen:
        txt = read_text(ctx["workdir"] / p)
        if len(txt) > max_file:
            txt = txt[:max_file] + f"\n[... truncated, {len(txt)} chars]"
        if total + len(txt) > max_total:
            parts.append(f"--- {p} (omitted: context budget reached)")
            continue
        parts.append(f"--- {p}\n{txt}")
        total += len(txt)
    return "\n".join(parts) if parts else "(none selected)"


def build_judge_prompt(case: dict, ctx: dict) -> str:
    qs = [a for a in case["assertions"] if a["type"] == "judge"]
    questions = "\n".join(f"- {a['id']}: {a['question']}" for a in qs)
    shown = [f for f in ctx["files"] if f["status"] != "skill-copy"]
    copies = len(ctx["files"]) - len(shown)
    files = "\n".join(f"- {f['path']} ({f['status']}, {f['bytes']} bytes)" for f in shown) or "(none)"
    if copies:
        files += f"\n- ({copies} unchanged copies of the skill's own files, not listed)"
    answer = ctx.get("answer") or "(empty)"
    if len(answer) > 30000:
        answer = answer[:30000] + "\n[... truncated]"
    refs = "\n".join(f"--- {r}\n{_fixture_src(r).read_text(encoding='utf-8', errors='replace')}"
                     for r in case.get("judge_reference", []))
    return JUDGE_PROMPT.format(questions=questions, prompt=case["prompt"], files=files,
                               answer=answer, contents=judge_context(case, ctx),
                               reference=REFERENCE_BLOCK.format(refs=refs) if refs else "")


def parse_judge_reply(text: str, ids: list[str]) -> dict[str, tuple[bool | None, str]]:
    """Extract {id: (verdict, reason)} from the judge's reply; missing ids -> (None, ...)."""
    out: dict[str, tuple[bool | None, str]] = {i: (None, "judge gave no answer") for i in ids}
    obj = None
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end > start:
        try:
            obj = json.loads(t[start:end + 1])
        except ValueError:
            obj = None
    if not isinstance(obj, dict):
        # strict JSON failed (typically a reason quoting text with unescaped "): recover id/answer pairs by pattern
        items = [{"id": m["id"], "answer": m["answer"], "reason": (m["reason"] or "").strip()} for m in re.finditer(
            r'"id"\s*:\s*"(?P<id>[^"]+)"\s*,\s*"answer"\s*:\s*"(?P<answer>[^"]*)"'
            r'(?:\s*,\s*"reason"\s*:\s*"(?P<reason>.*?)"\s*\}(?=\s*(?:,|\])))?', t, re.S)]
        if not items:
            return {i: (None, "unparseable judge reply") for i in ids}
        obj = {"answers": items}
    for item in obj.get("answers") or []:
        if not isinstance(item, dict):
            continue
        aid = str(item.get("id", ""))
        ans = str(item.get("answer", "")).strip().lower()
        if aid in out:
            verdict = True if ans.startswith("y") else False if ans.startswith("n") else None
            out[aid] = (verdict, str(item.get("reason", ""))[:300])
    return out


def judge_command(judge: str, prompt_file: Path, vision: bool = False) -> tuple[Invocation, str]:
    """(Invocation, adapter name) of a judge call; the prompt is read from prompt_file on stdin. A judge spec may
    carry @EFFORT (omp judges default to low; Claude judges run without --effort, as before)."""
    model, _, eff = (x.strip() for x in judge.partition("@"))
    spec = model_spec(model)
    ad = ADAPTERS[spec.adapter]
    if vision and not ad.supports_vision:
        raise ValueError("the vision judge must be a claude model (it reads the PNGs with the Read tool)")
    if not vision and not ad.supports_judge:
        raise ValueError("judge must be a claude or omp model")
    return ad.judge_command(spec, eff or None, Path(prompt_file), vision), spec.adapter


def call_model(inv: Invocation, adapter: str, model: str, cwd: Path | None, timeout: int) -> tuple[dict, str | None]:
    """Run a judge Invocation with an allow-listed environment and parse its output; (parsed, error). cwd None =
    a private scratch dir (the text judge needs none, and a results dir may be unreadable under confinement)."""
    ad, spec = ADAPTERS[adapter], model_spec(model.partition("@")[0])
    scratch = Path(tempfile.mkdtemp(prefix="evaljudge-"))
    try:
        env = ad.environment(scratch, scratch)
        env.update(inv.env)
        with open(inv.stdin, "rb") if inv.stdin else open(os.devnull, "rb") as fin:
            p = subprocess.run(inv.argv, cwd=cwd or scratch, env=env, stdin=fin, capture_output=True, text=True,
                               timeout=timeout)
        parsed = ad.parse(redact_secrets(p.stdout).splitlines(keepends=True), spec)
        return parsed, parsed["error"] or (None if p.returncode == 0 else
                                           f"exit {p.returncode}: {redact_secrets(p.stderr[-300:])}")
    except subprocess.TimeoutExpired:
        return {"final_answer": "", "cost_usd": 0.0, "tokens": _empty_tokens(), "cost_basis": None}, "judge timeout"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def run_judge(case: dict, ctx: dict, judge: str, timeout: int, cwd: Path) -> dict:
    qs = [a for a in case["assertions"] if a["type"] == "judge"]
    if not qs:
        return {"results": [], "cost_usd": 0.0, "tokens": _empty_tokens(), "error": None, "model": judge}
    with prompt_file_for(redact_secrets(build_judge_prompt(case, ctx))) as pf:
        inv, adapter = judge_command(judge, pf)
        parsed, err = call_model(inv, adapter, judge, None, timeout)   # `cwd` kept for callers; the judge needs none
    verdicts = parse_judge_reply(parsed["final_answer"], [a["id"] for a in qs])
    results = []
    for a in qs:
        v, reason = verdicts[a["id"]]
        results.append({"id": a["id"], "type": "judge", "kind": "judge", "neutral": a.get("neutral", True),
                        "passed": v, "detail": reason})
    return {"results": results, "cost_usd": parsed["cost_usd"], "cost_basis": parsed.get("cost_basis"),
            "tokens": parsed["tokens"], "error": err, "model": judge, "raw": parsed["final_answer"][:4000]}


# ============================================================ vision judge (visual-craft rubric on rendered frames)

VISION_PROMPT = """You score terminal UI frames on a design rubric. Use the Read tool to open each image file listed
below (PNG renders of terminal mockups; the window title bar is not part of the design). Score every image on
each criterion C1-C8 with 0, 1 or 2 exactly as the rubric defines them, judging only what you see.

Be a strict reviewer. For each criterion first write the concrete evidence you see (a region, a row, a color, a
count), then the score. A 2 requires that nothing described in that criterion's 0 or 1 column applies anywhere
in the image: any dead band or empty box interior, a saturated chip inside the selection band, plain-text
counts, a box where a rule would do, or misalignment caps the criterion at 1. When in doubt, give 1. Most good
app frames score 12-15 in total; 16 is rare (see the calibration table).

RUBRIC
{rubric}

IMAGES
{images}

Return ONLY a JSON object, no prose, no code fence:
{{"frames": [{{"image": "<file name>", "evidence": {{"C1": "<what you see>", "C2": "…", "C3": "…", "C4": "…", "C5": "…", "C6": "…", "C7": "…", "C8": "…"}}, "scores": {{"C1": 0, "C2": 0, "C3": 0, "C4": 0, "C5": 0, "C6": 0, "C7": 0, "C8": 0}}}}]}}
"""
CRITERIA = [f"C{i}" for i in range(1, 9)]


def rubric_text(skill_dir: Path | None = None) -> str:
    """The '## Aesthetic rubric' section of references/visual-craft.md (read at run time, so it follows edits)."""
    skill_dir = skill_dir or SKILL_DIR
    txt = read_text(skill_dir / "references" / "visual-craft.md")
    m = re.search(r"^## Aesthetic rubric\s*$(.*?)(?=^## |\Z)", txt, re.M | re.S)
    return (m.group(1) if m else txt[:6000]).strip()


def pick_frames(paths: list[str], a: dict) -> list[str]:
    """Frames to score: those matching `prefer` (default '--normal--') if any, largest area first."""
    rx = re.compile(a.get("prefer", r"--normal--"))
    pool = [p for p in paths if rx.search(Path(p).name)] or list(paths)

    def area(p):
        m = re.search(r"(\d+)x(\d+)", Path(p).name)
        return int(m.group(1)) * int(m.group(2)) if m else 0
    return sorted(pool, key=lambda p: (-area(p), p))[: a.get("max_frames", 1)]


def render_png(mock: Path, out_png: Path, depth: str | None, skill_dir: Path | None = None) -> str | None:
    """render_mockup.py -> .ansi -> ansi_render.py -> .png with the mock's own theme; None ok, else the error."""
    skill_dir = skill_dir or SKILL_DIR
    ansi = out_png.with_suffix(".ansi")
    cmd = [sys.executable, str(skill_dir / "scripts" / "render_mockup.py"), str(mock), "-o", str(ansi)]
    if depth and depth != "caps":
        cmd += ["--depth", depth]
    theme = mock_header(read_text(mock)).get("theme")
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if p.returncode != 0 or not ansi.exists():
        return f"render_mockup failed: {(p.stdout + p.stderr).strip()[-200:]}"
    cmd = [sys.executable, str(skill_dir / "scripts" / "ansi_render.py"), str(ansi), "--format", "png",
           "--title", mock.stem, "-o", str(out_png)]
    if theme:
        cmd += ["--theme", theme]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if p.returncode != 0 or not out_png.exists():
        return f"ansi_render failed: {(p.stdout + p.stderr).strip()[-200:]}"
    return None


def parse_vision_reply(text: str, names: list[str]) -> dict[str, dict[str, int]]:
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = t.find("{"), t.rfind("}")
    try:
        obj = json.loads(t[start:end + 1]) if start != -1 and end > start else None
    except ValueError:
        obj = None
    out: dict[str, dict[str, int]] = {}
    for fr in (obj or {}).get("frames") or []:
        if not isinstance(fr, dict):
            continue
        name = Path(str(fr.get("image", ""))).name
        sc = fr.get("scores") or {}
        try:
            vals = {c: int(sc[c]) for c in CRITERIA}
        except (KeyError, TypeError, ValueError):
            continue
        if name in names and all(v in (0, 1, 2) for v in vals.values()):
            out[name] = vals
    return out


def rubric_verdict(scores: dict[str, int], min_total: int = 12) -> tuple[bool, int]:
    total = sum(scores.values())
    return total >= min_total and min(scores.values()) > 0, total


def vision_command(model: str, prompt_file: Path) -> Invocation:
    """The vision judge's Invocation (a claude model with only the Read tool; the prompt on stdin)."""
    return judge_command(model, prompt_file, vision=True)[0]


def run_vision(case: dict, ctx: dict, model: str, timeout: int, skill_dir: Path | None = None) -> dict:
    """For each vision_rubric assertion: render the chosen frames (each depth) to PNG in a private dir, ask the
    vision judge to score them C1-C8, pass when every image scores >= min_total (default 12) with no 0."""
    skill_dir = skill_dir or SKILL_DIR
    qs = [a for a in case["assertions"] if a["type"] == "vision_rubric"]
    rec = {"results": [], "cost_usd": 0.0, "cost_basis": None, "tokens": _empty_tokens(), "error": None,
           "model": model, "scores": {}}
    if not qs:
        return rec
    wd: Path = ctx["workdir"]
    all_paths = [f["path"] for f in ctx["files"] if f["status"] != "skill-copy"]
    for a in qs:
        res = {"id": a["id"], "type": a["type"], "kind": "vision", "neutral": a.get("neutral", True),
               "passed": None, "detail": ""}
        frames = pick_frames(match_glob(all_paths, a["glob"]), a)
        if not frames:
            res.update(passed=False, detail=f"no frame matches {a['glob']}")
            rec["results"].append(res)
            continue
        imgdir = Path(tempfile.mkdtemp(prefix="evalvision-"))
        try:
            names, errs = [], []
            for i, fr in enumerate(frames):
                for depth in a.get("depths", ["caps", "16"]):
                    name = f"frame{i + 1}-{depth}.png"
                    err = render_png(wd / fr, imgdir / name, depth, skill_dir)
                    if err:
                        errs.append(f"{fr} @{depth}: {err}")
                    else:
                        names.append(name)
            if errs:
                res.update(passed=False, detail="; ".join(errs[:3]))
                rec["results"].append(res)
                continue
            prompt = VISION_PROMPT.format(rubric=rubric_text(skill_dir), images="\n".join(f"- ./{n}" for n in names))
            with prompt_file_for(prompt) as pf:
                inv, adapter = judge_command(model, pf, vision=True)
                parsed, verr = call_model(inv, adapter, model, imgdir, timeout)
            if verr and not parsed.get("error"):
                parsed["error"] = "vision timeout" if verr == "judge timeout" else verr
            rec["cost_usd"] += parsed["cost_usd"]
            rec["cost_basis"] = parsed.get("cost_basis")
            for k in rec["tokens"]:
                rec["tokens"][k] += parsed["tokens"].get(k, 0)
            if parsed.get("error"):
                rec["error"] = parsed["error"]
            scores = parse_vision_reply(parsed["final_answer"], names)
            rec["scores"][a["id"]] = {"frames": frames, "scores": scores, "raw": parsed["final_answer"][:6000]}
            missing = [n for n in names if n not in scores]
            if missing:
                res.update(passed=None, detail=f"vision judge gave no valid scores for {missing}")
            else:
                verdicts = {n: rubric_verdict(scores[n], a.get("min_total", 12)) for n in names}
                ok = all(v[0] for v in verdicts.values())
                res.update(passed=ok, detail=f"{', '.join(frames)}: " + "; ".join(
                    f"{n} {t}/16 " + " ".join(f"{c}={scores[n][c]}" for c in CRITERIA)
                    for n, (v, t) in verdicts.items()))
        finally:
            shutil.rmtree(imgdir, ignore_errors=True)
        rec["results"].append(res)
    return rec


# ============================================================ budget

class Budget:
    """Running spend with a hard cap. basis 'all' counts agent + judge cost of every basis
    (billed, API-equivalent, equivalent); 'billed' counts only real OpenRouter USD."""

    def __init__(self, max_usd: float | None, basis: str = "all"):
        self.max = max_usd
        self.basis = basis
        self.spent = 0.0
        self.live: dict[str, float] = {}
        self.lock = threading.Lock()
        self.stopped = False

    def can_start(self) -> bool:
        with self.lock:
            if self.max is not None and self.spent + sum(self.live.values()) >= self.max:
                self.stopped = True
            return not self.stopped

    def update_live(self, run_id: str, usd: float) -> bool:
        """Record a live run's running cost; False when the cap is crossed."""
        with self.lock:
            self.live[run_id] = usd
            over = self.max is not None and self.spent + sum(self.live.values()) >= self.max
            if over:
                self.stopped = True
            return not over

    def counts(self, cost_basis: str | None) -> bool:
        return self.basis == "all" or cost_basis == "billed"

    def commit(self, run_id: str, usd: float) -> None:
        with self.lock:
            self.live.pop(run_id, None)
            self.spent += usd


# ============================================================ one run

def run_agent(adapter: str, inv: Invocation, workdir: Path, home: Path, timeout: int, budget: Budget, run_id: str,
              events_path: Path, spec: ModelSpec | None = None, place: dict | None = None) -> dict:
    """Start the agent with an allow-listed environment (never the orchestrator's: no keys, no TMUX, a private
    TMUX_TMPDIR so any tmux it starts gets its own server inside the workdir), the prompt file on stdin (or
    /dev/null), stream its stdout to the events file with every secret redacted, and parse it."""
    ad = ADAPTERS[adapter]
    env = ad.environment(home, workdir / ".tmp")
    env.update(inv.env)
    start = time.time()
    fin = open(inv.stdin, "rb") if inv.stdin else open(os.devnull, "rb")
    proc = subprocess.Popen(inv.argv, cwd=workdir, env=env, stdin=fin, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, bufsize=1, errors="replace")
    fin.close()
    timed_out, budget_kill = threading.Event(), threading.Event()

    def _kill():
        timed_out.set()
        proc.kill()

    timer = threading.Timer(timeout, _kill)
    timer.start()
    err_chunks: list[str] = []
    t_err = threading.Thread(target=lambda: err_chunks.append(proc.stderr.read()), daemon=True)
    t_err.start()
    lines: list[str] = []
    hits: list[str] = []
    live_cost = 0.0
    counts = budget.counts(spec.cost_basis if spec and spec.cost_basis else ad.default_cost_basis)
    with open(events_path, "w") as ev_out:
        for line in proc.stdout:
            line, found = redactor().text(line)
            hits += found
            ev_out.write(line)
            lines.append(line)
            if counts:
                inc = ad.live_cost(line)
                if inc:
                    live_cost += inc
                    if not budget.update_live(run_id, live_cost):
                        budget_kill.set()
                        proc.kill()
                        break
    timer.cancel()
    proc.wait()
    t_err.join(timeout=5)
    proc.stdout.close()
    proc.stderr.close()
    parsed = ad.parse(lines, spec, place)
    stderr, found = redactor().text("".join(err_chunks))
    return {"parsed": parsed, "exit_code": proc.returncode, "timed_out": timed_out.is_set(),
            "killed_for_budget": budget_kill.is_set(), "wall_s": round(time.time() - start, 1),
            "stderr": stderr, "secret_hits": sorted(set(hits + found))}


def run_id_for(case_id: str, model: str, arm: str, rep: int) -> str:
    return f"{case_id}__{slug(model)}__{arm}__r{rep}"


def copy_outputs(workdir: Path, dest: Path, skip: set[str] | None = None, hits: list[str] | None = None) -> None:
    """Copy the agent's files (minus skill copies and files over MAX_COPY_BYTES) with secrets redacted."""
    for rel in list_files(workdir):
        src = workdir / rel
        if src.stat().st_size > MAX_COPY_BYTES or (skip and rel in skip):
            continue
        d = dest / rel
        d.parent.mkdir(parents=True, exist_ok=True)
        data, found = redactor().data(src.read_bytes())
        if hits is not None:
            hits += found
        d.write_bytes(data)
        shutil.copystat(src, d)


def fixture_hexes(case: dict) -> set[str]:
    out: set[str] = set()
    for f in case.get("fixtures", []):
        out |= hexes_in(fixture_text(f))
    return out


def write_record(runs_dir: Path, rec: dict, hits: list[str] | None = None) -> Path:
    """runs/<run_id>.json, redacted."""
    p = runs_dir / f"{rec['run_id']}.json"
    write_redacted(p, json.dumps(rec, indent=2, ensure_ascii=False), hits)
    return p


PATH_TOKEN_RX = re.compile(r"(?<![\w.~:/$)}-])(?:~|/)[^\s\"'`|&;<>(){}\[\],=]+")   # absolute or ~ paths only
DISK_SEARCH_RX = re.compile(r"""(?:^|\\n|[;&|(`]|"command": ")\s*(mdfind|mdls|locate)(?=\s)""", re.M)   # as a command
RUN_ROOT_RX = re.compile(r"/evalrun-[^/\s\"']+")


def contamination(transcript: str, inside, skill_name: str = SKILL_NAME) -> list[str]:
    """What an agent reached outside its own run, from its tool calls: a path through a directory named after the
    skill (another copy of it, old results) or under a [sandbox] deny_read path (your own skills), or a whole-disk
    search command. `inside(path)` says whether a path is in the run's own temp dir. A hit marks the run
    `contaminated` (an error, so --resume runs it again)."""
    seg = re.compile(rf"/{re.escape(skill_name)}(?:-[\w.-]+)?(?:/|$)")
    home = str(Path.home())
    denied = tuple(str(p) for p in extra_deny_paths())
    hits = set()
    for tok in PATH_TOKEN_RX.findall(transcript or ""):
        tok = tok.rstrip("\\")
        full = home + tok[1:] if tok.startswith("~") else tok
        if not inside(tok) and (seg.search(tok) or (denied and full.startswith(denied))):
            hits.add(tok)
    hits |= set(DISK_SEARCH_RX.findall(transcript or ""))
    return sorted(hits)[:20]


def inside_root(root: Path):
    prefixes = tuple({str(root), str(root.resolve())})
    return lambda tok: tok.startswith(prefixes)


def scan_contamination(results_dir: Path) -> list[str]:
    """--scan-contamination: apply `contamination` to the saved runs of a results dir (the temp dirs are gone, so any
    path under an evalrun-* dir counts as inside); a hit sets the run's error so --resume repeats it."""
    out = []
    for jp in sorted((results_dir / "runs").glob("*.json")):
        rec = json.loads(jp.read_text())
        ev = jp.with_name(jp.name[:-5] + ".events.jsonl.gz")
        adapter = (rec.get("identity") or {}).get("adapter") or rec.get("adapter")
        if not rec.get("run_id") or not ev.is_file() or adapter not in ADAPTERS:
            continue
        with gzip.open(ev, "rt", encoding="utf-8", errors="replace") as f:
            events = [json.loads(l) for l in f if l.strip()]
        hits = contamination(ADAPTERS[adapter].tool_texts(events), lambda tok: bool(RUN_ROOT_RX.search(tok)))
        if hits and not rec.get("contamination"):
            rec["contamination"] = hits
            rec["error"] = f"contaminated: {', '.join(hits[:3])}"
            write_redacted(jp, json.dumps(rec, indent=2, ensure_ascii=False))
        if hits:
            out.append(f"{rec['run_id']}: {', '.join(hits[:5])}")
    return out


def check_leaks(runs_dir: Path, rec: dict, hits: list[str]) -> dict:
    """After a run: a secret the agent's output carried (redacted on the way, `hits`) or one still on disk (leak
    scan, then scrubbed) marks the run `secret leak` and records which secret and where."""
    arts = run_artifacts(runs_dir, rec["run_id"])
    found = leak_scan(arts)
    if found:
        scrub_files(arts)
    names = sorted(set(hits) | {n for ns in found.values() for n in ns})
    if names:
        rec["secret_leak"] = {"names": names, "files_with_raw_value": found}
        rec["error"] = f"secret leak: {', '.join(names)} reached the run's artifacts (redacted); campaign stopped"
        write_record(runs_dir, rec)
    return rec


def run_one(case: dict, model: str, effort: str, arm: str, rep: int, args, budget: Budget, runs_dir: Path) -> dict:
    spec = model_spec(model)
    adapter = spec.adapter
    ad = ADAPTERS[adapter]
    rid = run_id_for(case["id"], model, arm, rep)
    token = run_token(rid)
    template = case
    case = materialize_case(case, token)
    root = Path(tempfile.mkdtemp(prefix="evalrun-"))
    workdir, home = root / "project", root / "home"
    workdir.mkdir()
    home.mkdir()
    (workdir / ".tmp").mkdir()
    rec: dict = {"run_id": rid, "case": case["id"], "area": case.get("area"), "model": model, "adapter": adapter,
                 "effort": effort, "arm": arm, "rep": rep, "started_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    if case is not template:
        rec["run_token"] = token
    judges = (None, None) if args.no_judge else (args.judge, args.vision_judge)
    hits: list[str] = []

    def identify(skill_hash):
        rec.update(run_identity(template, model, effort, arm, rep, judges[0], judges[1], skill_hash,
                                adapter_version(adapter, spec)))
    try:
        for req in case.get("requires", []):        # cheap pre-check: skip instead of failing the agent
            ok, why = requirement_ok(req["cmd"], exec_env(home, workdir / ".tmp"), workdir)
            if not ok:
                identify(tree_hash(SKILL_DIR) if arm == "skill" else None)
                rec.update({"skipped": f"{req.get('why') or req['cmd']} ({why[-120:]})", "error": None,
                            "score": None, "assertions": [], "tokens": None, "cost_usd": 0.0, "cost_basis": None})
                write_record(runs_dir, rec)
                return rec
        hashes = write_fixtures(workdir, case.get("fixtures", []))
        if ad.git_init and shutil.which("git"):
            subprocess.run(["git", "init", "-q"], cwd=workdir, check=False, env=base_env(home, workdir / ".tmp"))
        skill_index = None
        if arm == "skill":
            dest = install_skill(workdir, adapter, spec=spec)
            identify(tree_hash(dest))
            skill_index = skill_file_index(dest)
        else:
            identify(None)
        prompt_path = root / "prompt.txt"            # outside the workdir; the agent gets it on stdin or by path
        prompt_path.write_text(case["prompt"], encoding="utf-8")
        inv = ad.command(spec, effort, arm, prompt_path, workdir, home, case.get("claude_tools"), root)
        rec["command"] = inv.display()
        rec["env"] = json.loads(redact_secrets(json.dumps(inv.env if inv.shown_env is None else inv.shown_env)))
        rec["prompt_via"] = "stdin" if inv.stdin else "file argument"
        ev_path = runs_dir / f"{rid}.events.jsonl"
        timeout = int(case.get("timeout") or spec.timeout or args.timeout)
        place = CommandAdapter.values(spec, effort, arm, prompt_path, workdir, home, root, ad.skill_dir_rel(spec))
        res = run_agent(adapter, inv, workdir, home, timeout, budget, rid, ev_path, spec, place)
        hits += res["secret_hits"]
        _kill_tmux_servers(workdir / ".tmp")
        p = res["parsed"]
        p["final_answer"], found = redactor().text(p["final_answer"] or "")
        hits += found
        (runs_dir / f"{rid}.stderr.txt").write_text(res["stderr"])
        files = classify_files(workdir, hashes, skill_index)
        ctx = {"workdir": workdir, "answer": p["final_answer"], "files": files, "skill_dir": SKILL_DIR,
               "fixture_hexes": fixture_hexes(case), "transcript": tool_texts(adapter, read_events(ev_path))}
        gzip_events(ev_path)
        assertions = grade_program(case, ctx)
        copies = {f["path"] for f in files if f["status"] == "skill-copy"}
        copy_outputs(workdir, runs_dir / f"{rid}.files", copies, hits)
        if getattr(args, "no_exec", False):
            assertions += [{"id": a["id"], "type": a["type"], "kind": "executed", "neutral": a.get("neutral", True),
                            "passed": None, "detail": "not run (--no-exec)"}
                           for a in case["assertions"] if a["type"] in EXECUTED_TYPES]
        else:
            assertions += executed_in_copy(case, workdir)
        judge = {"results": [], "cost_usd": 0.0, "tokens": _empty_tokens(), "error": None, "model": None}
        vision = {"results": [], "cost_usd": 0.0, "tokens": _empty_tokens(), "error": None, "model": None}
        if not args.no_judge and not hits:           # never send a leaked secret on to a judge
            judge = run_judge(case, ctx, args.judge, args.judge_timeout, root)
            assertions += judge.pop("results")
            vision = run_vision(case, ctx, args.vision_judge, args.judge_timeout)
            assertions += vision.pop("results")
        error = p["error"]
        if res["timed_out"]:
            error = f"timeout after {timeout}s"
        elif res["killed_for_budget"]:
            error = "killed: --max-usd reached"
        elif res["exit_code"] not in (0, None) and not error:
            error = f"exit code {res['exit_code']}"
        contam = contamination(ctx["transcript"], inside_root(root))
        if contam:
            rec["contamination"] = contam
            error = f"contaminated: {', '.join(contam[:3])}"
        rec.update({
            "wall_s": res["wall_s"], "exit_code": res["exit_code"], "timed_out": res["timed_out"],
            "killed_for_budget": res["killed_for_budget"], "error": error,
            "stderr_tail": res["stderr"][-2000:], "final_answer": p["final_answer"],
            "tool_calls": p["tool_calls"], "skill_loaded": p["skill_loaded"],
            "files": [f for f in files if f["status"] not in ("fixture", "skill-copy")],
            "skill_copies": len(copies),
            "assertions": (assertions := apply_blocked(case, assertions)), "score": score(assertions),
            "tokens": p["tokens"], "cost_usd": round(p["cost_usd"], 6), "cost_basis": p["cost_basis"],
            "judge": judge, "vision": vision,
        })
    finally:
        spent = float(rec.get("cost_usd") or 0) if budget.counts(rec.get("cost_basis")) else 0.0
        for k in ("judge", "vision"):
            jr = rec.get(k) or {}
            if budget.counts(jr.get("cost_basis")):
                spent += float(jr.get("cost_usd") or 0)
        budget.commit(rid, spent)
        _kill_tmux_servers(workdir / ".tmp")
        if args.keep_workdirs:
            rec["workdir"] = str(workdir)
        else:
            shutil.rmtree(root, ignore_errors=True)
    write_record(runs_dir, rec, hits)
    return check_leaks(runs_dir, rec, hits)


# ============================================================ regrade from saved files

def regrade(out_dir: Path, cases: list[dict], args) -> list[dict]:
    """Re-check program assertions on saved run files: static ones in place, executed ones in a scratch copy of
    .files/ (skipped with --no-exec: earlier results kept). The text and vision judges run again only with
    --rejudge; otherwise their earlier verdicts are kept. Skipped runs stay skipped."""
    by_id = {c["id"]: c for c in cases}
    runs = []
    runs_dir = out_dir / "runs"
    for jp in sorted(runs_dir.glob("*.json")):
        rec = json.loads(jp.read_text())
        template = by_id.get(rec.get("case"))
        files_dir = runs_dir / f"{rec['run_id']}.files"
        if template is None or rec.get("skipped") or not files_dir.is_dir():
            runs.append(rec)
            continue
        case = materialize_case(template, rec.get("run_token") or run_token(rec["run_id"]))
        rec["area"] = case.get("area")
        hashes = {f["path"]: sha256_bytes(fixture_bytes(f)) for f in case.get("fixtures", [])}
        files = classify_files(files_dir, hashes, current_skill_index())
        events = read_events(events_path(runs_dir, rec["run_id"]))
        ctx = {"workdir": files_dir, "answer": rec.get("final_answer", ""), "files": files,
               "skill_dir": SKILL_DIR, "fixture_hexes": fixture_hexes(case),
               "transcript": tool_texts(rec.get("adapter") or adapter_for(rec["model"]), events)}
        ctx["answer"] = redact_secrets(ctx["answer"] or "")
        old = {a["id"]: a for a in rec.get("assertions", [])}
        assertions = grade_program(case, ctx)
        exec_ids = [a["id"] for a in case["assertions"] if a["type"] in EXECUTED_TYPES]
        if getattr(args, "no_exec", False):
            assertions += [old[i] for i in exec_ids if i in old]
        else:
            assertions += executed_in_copy(case, files_dir)
        if args.rejudge:
            j = run_judge(case, ctx, args.judge, args.judge_timeout, files_dir)
            assertions += j.pop("results")
            rec["judge"] = j
            v = run_vision(case, ctx, args.vision_judge, args.judge_timeout)
            assertions += v.pop("results")
            rec["vision"] = v
        else:
            ids = [a["id"] for a in case["assertions"] if a["type"] in MODEL_TYPES]
            raw = (rec.get("judge") or {}).get("raw")
            if raw and any(old.get(i, {}).get("passed") is None and old[i].get("type") == "judge" for i in ids):
                reparsed = parse_judge_reply(raw, [a["id"] for a in case["assertions"] if a["type"] == "judge"])
                for i, (v, reason) in reparsed.items():   # a stored reply the parser now reads: no new judge call
                    if i in old and old[i].get("passed") is None and v is not None:
                        old[i] = {**old[i], "passed": v, "detail": reason}
            assertions += [old[i] for i in ids if i in old]
        rec["files"] = [f for f in files if f["status"] not in ("fixture", "skill-copy")]
        assertions = reapply_blocked(case, assertions)
        rec["assertions"], rec["score"] = assertions, score(assertions)
        rec["graded_case_hash"] = case_hash(template)   # identity keeps the hash of the case the agent ran
        write_redacted(jp, json.dumps(rec, indent=2, ensure_ascii=False))
        runs.append(rec)
    return runs


# ============================================================ summary

def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def _pct(x):
    return "n/a" if x is None else f"{x * 100:.0f}%"


def _usd(x):
    return "–" if x is None else f"{x:.4f}"


def _delta(a, b):
    return "n/a" if a is None or b is None else f"{(a - b) * 100:+.0f}"


def _cell(rs: list[dict]) -> dict:
    """Aggregate of one group of runs (same arm); skipped runs are counted apart and never graded."""
    skipped = [r for r in rs if r.get("skipped")]
    rs = [r for r in rs if not r.get("skipped")]
    ok = [r for r in rs if not r.get("error") and r.get("score")]
    rates = [r["score"]["rate"] for r in ok if r["score"].get("rate") is not None]
    return {
        "n": len(rs), "errors": len(rs) - len(ok), "skipped": len(skipped),
        "rate": _mean([r["score"]["rate"] for r in ok]),
        "graded_runs": len(rates),
        "rate_min": min(rates) if rates else None, "rate_max": max(rates) if rates else None,
        "rate_sd": statistics.stdev(rates) if len(rates) >= 2 else None,
        "neutral_rate": _mean([r["score"]["neutral_rate"] for r in ok]),
        "all_pass": _mean([1.0 if r["score"]["all_passed"] else 0.0 for r in ok]),
        "cost": _mean([r.get("cost_usd") for r in rs]),
        "tokens": {k: _mean([(r.get("tokens") or {}).get(k) for r in rs])
                   for k in ("input", "cached", "cache_write", "output", "reasoning")},
        "tool_calls": _mean([r.get("tool_calls") for r in rs]),
        "skill_loaded": sum(1 for r in rs if r.get("skill_loaded")),
        "wall_s": _mean([r.get("wall_s") for r in rs]),
    }


def summarize(runs: list[dict], cases: list[dict]) -> tuple[str, dict]:
    case_order = [c["id"] for c in cases]
    area_of = {c["id"]: c.get("area", "?") for c in cases}
    try:
        order = catalog().order()
    except ConfigError:
        order = []
    models = sorted({r["model"] for r in runs}, key=lambda m: (order.index(m) if m in order else len(order), m))
    rows, agg = [], {}
    for cid in case_order:
        for m in models:
            cell = {arm: _cell([r for r in runs if r["case"] == cid and r["model"] == m and r["arm"] == arm])
                    for arm in ARMS}
            if any(cell[a]["n"] or cell[a]["skipped"] for a in ARMS):
                agg[f"{cid}|{m}"] = cell
                rows.append((cid, m, cell))
    basis_tot: dict[str, float] = {}
    for r in runs:
        if r.get("skipped"):
            continue
        basis_tot[r.get("cost_basis", "?")] = basis_tot.get(r.get("cost_basis", "?"), 0) + float(r.get("cost_usd") or 0)
    judge_tot = sum(float((r.get("judge") or {}).get("cost_usd") or 0) for r in runs)
    vision_tot = sum(float((r.get("vision") or {}).get("cost_usd") or 0) for r in runs)
    judge_basis = sorted({(r.get(k) or {}).get("cost_basis") or "?" for r in runs for k in ("judge", "vision")
                          if float((r.get(k) or {}).get("cost_usd") or 0) > 0})
    graded_runs = [r for r in runs if not r.get("skipped")]

    L = ["# Behavior evals: summary", "",
         f"{len(graded_runs)} runs ({len(runs) - len(graded_runs)} skipped) · models: {', '.join(models)} · "
         f"generated {time.strftime('%Y-%m-%d %H:%M')}", "",
         "Pass rate = mean share of graded assertions passed per run (errored and skipped runs excluded). "
         "`neutral` excludes assertions on the skill's own artifact format (.mock frames, `#! caps:`, its scripts). "
         "Delta = skill − baseline, in points.", ""]

    # per skill area
    L += ["## Per skill area", "",
          "| area | cases | model | skill | baseline | Δ | Δ neutral | runs s/b | skipped |",
          "|---|---|---|---|---|---|---|---|---|"]
    area_data = {}
    for area in dict.fromkeys([*AREAS, *area_of.values()]):
        cids = [c for c in case_order if area_of.get(c) == area]
        for m in models:
            cell = {arm: _cell([r for r in runs if r["case"] in cids and r["model"] == m and r["arm"] == arm])
                    for arm in ARMS}
            if not any(cell[a]["n"] or cell[a]["skipped"] for a in ARMS):
                continue
            s_, b_ = cell["skill"], cell["baseline"]
            area_data[f"{area}|{m}"] = {"cases": cids, "skill": s_, "baseline": b_}
            L.append(f"| {area} | {len(cids)} | {m} | {_pct(s_['rate'])} | {_pct(b_['rate'])} | "
                     f"{_delta(s_['rate'], b_['rate'])} | {_delta(s_['neutral_rate'], b_['neutral_rate'])} | "
                     f"{s_['n']}/{b_['n']} | {s_['skipped'] + b_['skipped']} |")

    L += ["", "## Per case", "",
          "| case | area | model | skill | baseline | Δ | Δ neutral | all-pass s/b | skill loaded | cost/run s · b (USD) | tokens/run s · b (in/cached/out/reason) | errors s/b |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]

    def tk(t):
        return "/".join("–" if t[k] is None else f"{t[k] / 1000:.0f}k" for k in ("input", "cached", "output", "reasoning"))

    for cid, m, c in rows:
        s_, b_ = c["skill"], c["baseline"]
        L.append(f"| {cid} | {area_of.get(cid)} | {m} | {_pct(s_['rate'])} | {_pct(b_['rate'])} | "
                 f"{_delta(s_['rate'], b_['rate'])} | "
                 f"{_delta(s_['neutral_rate'], b_['neutral_rate'])} | {_pct(s_['all_pass'])} / {_pct(b_['all_pass'])} | "
                 f"{s_['skill_loaded']}/{s_['n']} (base {b_['skill_loaded']}) | "
                 f"{_usd(s_['cost'])} · {_usd(b_['cost'])} | "
                 f"{tk(s_['tokens'])} · {tk(b_['tokens'])} | {s_['errors']}/{b_['errors']} |")

    # spread across repetitions (only when some cell has more than one graded run)
    multi = [(cid, m, c) for cid, m, c in rows if any(c[a]["graded_runs"] > 1 for a in ARMS)]
    if multi:
        def spread(x):
            if not x["graded_runs"]:
                return "–"
            sd = "–" if x["rate_sd"] is None else f"{x['rate_sd'] * 100:.0f}"
            return f"{_pct(x['rate_min'])}–{_pct(x['rate_max'])} (sd {sd})"
        L += ["", "## Spread across repetitions", "",
              "Pass rate per run of each cell: min–max and standard deviation in points (graded runs only).", "",
              "| case | model | skill min–max (sd) | baseline min–max (sd) | graded runs s/b |", "|---|---|---|---|---|"]
        for cid, m, c in multi:
            L.append(f"| {cid} | {m} | {spread(c['skill'])} | {spread(c['baseline'])} | "
                     f"{c['skill']['graded_runs']}/{c['baseline']['graded_runs']} |")

    # per-assertion pass counts
    L += ["", "## Per assertion (passed / graded, skill vs baseline, all models)", "",
          "| case | assertion | kind | neutral | skill | baseline |", "|---|---|---|---|---|---|"]
    for c in cases:
        for a in c["assertions"]:
            cnt = {}
            for arm in ARMS:
                vals = [x["passed"] for r in runs if r["case"] == c["id"] and r["arm"] == arm and not r.get("error")
                        and not r.get("skipped")
                        for x in r.get("assertions", []) if x["id"] == a["id"] and x["passed"] is not None]
                cnt[arm] = f"{sum(vals)}/{len(vals)}" if vals else "–"
            if any(v != "–" for v in cnt.values()):
                kind = ("judge" if a["type"] == "judge" else "vision" if a["type"] == "vision_rubric"
                        else "executed" if a["type"] in EXECUTED_TYPES else "program")
                L.append(f"| {c['id']} | {a['id']} | {kind} | "
                         f"{'yes' if a.get('neutral', True) else 'no'} | {cnt['skill']} | {cnt['baseline']} |")

    L += ["", "## Spend", ""]
    for basis, usd in sorted(basis_tot.items()):
        L.append(f"- agent runs, {basis}: ${usd:.4f}")
    L.append(f"- judge ({', '.join(judge_basis) or 'none'}): text ${judge_tot:.4f} + vision ${vision_tot:.4f}")
    L.append(f"- total: ${sum(basis_tot.values()) + judge_tot + vision_tot:.4f} "
             "(billed = real OpenRouter USD; api-equivalent = Claude subscription, not billed; equivalent = computed)")
    skipped = [r for r in runs if r.get("skipped")]
    if skipped:
        L += ["", "## Skipped runs (excluded from pass rates)", ""] + [f"- {r['run_id']}: {r['skipped']}" for r in skipped]
    errs = [r for r in runs if r.get("error")]
    if errs:
        L += ["", "## Errored runs", ""] + [f"- {r['run_id']}: {r['error']}" for r in errs]
    data = {"runs": len(runs), "skipped": len(skipped), "cells": agg, "areas": area_data,
            "spend_by_basis": basis_tot, "judge_usd": judge_tot, "vision_usd": vision_tot}
    return "\n".join(L) + "\n", data


# ============================================================ dry run / estimate

def latest_results_dir() -> Path | None:
    """Newest results dir with saved runs in the results root."""
    dirs = []
    for root in [RESULTS_DIR]:
        if root.is_dir():
            dirs += [d for d in root.iterdir() if (d / "runs").is_dir() and any((d / "runs").glob("*.json"))]
    return max(dirs, key=lambda d: max(p.stat().st_mtime for p in (d / "runs").glob("*.json"))) if dirs else None


def _median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def _p90(xs):
    """Nearest-rank 90th percentile."""
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    k = max(0, -(-9 * len(xs) // 10) - 1)
    return xs[k]


def token_profile(runs: list[dict]) -> dict:
    """Per (case, arm) and overall: median and p90 of total input (uncached + cache write + cached) and output
    (incl. reasoning), median cached share and median judge (text + vision) USD. Medians, so one runaway loop does
    not move the typical figure; p90 shows the tail separately."""
    prof: dict = {}
    runs = [r for r in runs if r.get("tokens") and not r.get("skipped")]
    keys = {(r["case"], r["arm"]) for r in runs} | {("*", r["arm"]) for r in runs} | {("*", "*")}
    for case_id, arm in keys:
        rs = [r for r in runs if (case_id == "*" or r["case"] == case_id) and (arm == "*" or r["arm"] == arm)]
        if not rs:
            continue
        tins = [r["tokens"]["input"] + r["tokens"]["cached"] + r["tokens"]["cache_write"] for r in rs]
        outs = [max(r["tokens"]["output"], r["tokens"]["reasoning"]) for r in rs]
        shares = [(r["tokens"]["cached"] / t) if t else 0.0 for r, t in zip(rs, tins)]
        jus = [float((r.get("judge") or {}).get("cost_usd") or 0) + float((r.get("vision") or {}).get("cost_usd") or 0)
               for r in rs]
        prof[(case_id, arm)] = {"input_total": _median(tins), "output": _median(outs),
                                "cached_share": _median(shares) or 0.0,
                                "p90_input": _p90(tins), "p90_output": _p90(outs),
                                "judge_usd": _median(jus), "n": len(rs)}
    return prof


def estimate_cost(model: str | dict, input_total: float, cached_share: float, output: float) -> tuple[float, float]:
    """(low, high) USD for one run: low applies the observed cache share, high assumes no cache hits. `model` is a
    model id (its price: the --refresh-prices cache, else models.toml) or a price dict."""
    pr = model if isinstance(model, dict) else catalog().price(model)[0]
    cached_price = pr["cached"] if pr["cached"] is not None else pr["input"]
    low = (input_total * (1 - cached_share) * pr["input"] + input_total * cached_share * cached_price
           + output * pr["output"]) / 1e6
    high = (input_total * pr["input"] + output * pr["output"]) / 1e6
    return low, high


def dry_run(cases: list[dict], models: list[tuple[str, str]], arms: list[str], reps: int,
            ref_dirs: list[Path]) -> str:
    n = len(cases) * len(models) * len(arms) * reps
    L = [f"DRY RUN: {len(cases)} cases × {len(models)} models × {len(arms)} arms × {reps} reps = {n} runs", ""]
    serial = sum(1 for c in cases if c.get("serial"))
    if serial:
        L.append(f"{serial} serial case(s) run alone even under --jobs: "
                 + ", ".join(c["id"] for c in cases if c.get("serial")))
    for m, e in models:
        a = adapter_for(m)
        inv = build_command(a, m, e, arms[0], Path("<prompt-file>"), Path("<workdir>"), Path("<fresh-home>"),
                            run_dir=Path("<run-dir>"))
        argv = ["<confine-reads>" if x.startswith("(version 1)") else x for x in inv.argv]
        shown = inv.env if inv.shown_env is None else inv.shown_env
        line = " ".join(f"{k}={v}" for k, v in shown.items()) + " " + " ".join(shlex.quote(c) for c in argv)
        L.append(f"  [{a}] {redact_secrets(line.strip())}" + (f" < {inv.stdin}" if inv.stdin else " < /dev/null"))
    tags: dict[str, int] = {}
    for c in cases:
        for t in case_tags(c):
            tags[t] = tags.get(t, 0) + 1
    L.append("")
    L.append("cases per tag: " + ", ".join(f"{t} {k}" for t, k in sorted(tags.items())))
    L.append("")
    runs = []
    for d in ref_dirs:
        for p in sorted((Path(d) / "runs").glob("*.json")):
            try:
                runs.append(json.loads(p.read_text()))
            except ValueError:
                continue
    runs = [r for r in runs if r.get("tokens")]  # errored/killed runs included: their tokens were spent
    if not runs:
        L.append("No earlier results to estimate from (run a smoke first, or pass --estimate-from DIR).")
        return "\n".join(L)
    prof = token_profile(runs)
    known = {c["id"] for c in cases if any((c["id"], arm) in prof for arm in arms)}
    L.append(f"Token profile from {', '.join(str(d) for d in ref_dirs)} ({len(runs)} runs, model(s): "
             f"{', '.join(sorted({r['model'] for r in runs}))}); {len(known)}/{len(cases)} cases have runs there.")
    L.append("Per run = tokens × model prices. 'median' = the median run of each arm (all cases pooled) with the "
             "median cache share; 'med/nocache' = same tokens, every input token at the input price; 'p90/nocache' = "
             "the 90th-percentile run of each arm as if every run were one, no cache (a ceiling, not an estimate); 'per-case/nocache' = each case's "
             "own median run, clipped at its arm's p90 run so one runaway loop cannot dominate (keeps heavy cases heavy).")
    L.append("")
    L.append(f"{'model':<24} {'basis':<15} {'runs':>5} {'median':>9} {'med/nocache':>12} {'p90/nocache':>12} "
             f"{'per-case/nocache':>17}")
    g = [0.0, 0.0, 0.0, 0.0]
    judge_med = 0.0
    for m, _e in models:
        price, src = catalog().price(m)
        if price is None:
            L.append(f"{m:<24} (no price in models.toml; skipped)")
            continue
        row = [0.0, 0.0, 0.0, 0.0]
        for c in cases:
            for arm in arms:
                pa = prof.get(("*", arm)) or prof.get(("*", "*"))
                pc = prof.get((c["id"], arm)) or pa
                if not pa:
                    continue
                lo, hi = estimate_cost(price, pa["input_total"], pa["cached_share"], pa["output"])
                _, hi90 = estimate_cost(price, pa["p90_input"], 0.0, pa["p90_output"])
                _, hic = estimate_cost(price, min(pc["input_total"], pa["p90_input"]), 0.0,
                                       min(pc["output"], pa["p90_output"]))
                for i, v in enumerate((lo, hi, hi90, hic)):
                    row[i] += v * reps
                judge_med += (pc["judge_usd"] or 0) * reps
        g = [a + b for a, b in zip(g, row)]
        basis = model_spec(m).cost_basis or ADAPTERS[adapter_for(m)].default_cost_basis
        L.append(f"{m:<24} {basis:<15} {len(cases) * len(arms) * reps:>5} {row[0]:>9.2f} {row[1]:>12.2f} "
                 f"{row[2]:>12.2f} {row[3]:>17.2f}" + ("  (OpenRouter price cache)" if src == "cache" else ""))
    L.append(f"{'judges (per-case median)':<24} {'api-equivalent':<15} {n:>5} {judge_med:>9.2f} {judge_med:>12.2f} "
             f"{judge_med:>12.2f} {judge_med:>17.2f}")
    L.append(f"{'TOTAL':<24} {'':<15} {n:>5} " + " ".join(f"{v + judge_med:>{w}.2f}" for v, w in zip(g, (9, 12, 12, 17))))
    L.append("")
    L.append("Caveat: the profile comes from the smoke model at low effort; larger models at medium/high effort "
             "usually make more tool calls and emit more reasoning, so read 'med/nocache' as the typical figure "
             "and 'p90/nocache' as the planning ceiling for --max-usd. A case with no earlier run (or a cheap judge-only "
             "case) is priced like the pooled median run of its arm.")
    return "\n".join(L)


# ============================================================ scheduling

def build_jobs(cases: list[dict], models: list[tuple[str, str]], arms: list[str], reps: int) -> list[tuple]:
    """Every (case, model, effort, arm, rep), interleaved by case so all models advance together."""
    return [(c, m, e, arm, rep) for c in cases for (m, e) in models for rep in range(1, reps + 1) for arm in arms]


def resume_split(jobs: list[tuple], runs_dir: Path) -> tuple[list[dict], list[tuple]]:
    """(kept runs, jobs still to run): a job is kept when its run file finished without error and was not
    skipped; failed, skipped and missing ones run again. A larger --reps only adds the new repetitions."""
    done = {}
    for f in runs_dir.glob("*.json"):
        try:
            r = json.loads(f.read_text())
        except ValueError:
            continue
        if isinstance(r, dict) and r.get("run_id") and not r.get("error") and not r.get("skipped"):
            done[r["run_id"]] = r
    kept = [done[run_id_for(c["id"], m, arm, rep)] for c, m, e, arm, rep in jobs
            if run_id_for(c["id"], m, arm, rep) in done]
    todo = [j for j in jobs if run_id_for(j[0]["id"], j[1], j[3], j[4]) not in done]
    return kept, todo


def run_jobs(jobs: list[tuple], parallel: int, work, is_serial=lambda j: bool(j[0].get("serial"))) -> None:
    """Run jobs in order. Consecutive ordinary jobs share a pool of `parallel` workers; a serial job (case
    `serial: true`, e.g. signal tests) waits for the pool to drain and runs alone."""
    batch: list[tuple] = []

    def flush():
        if parallel > 1 and len(batch) > 1:
            with ThreadPoolExecutor(max_workers=parallel) as ex:
                list(ex.map(work, batch))
        else:
            for j in batch:
                work(j)
        batch.clear()

    for j in jobs:
        if is_serial(j):
            flush()
            work(j)
        else:
            batch.append(j)
    flush()


def list_models(cat: Catalog) -> str:
    """--list-models: models, presets, judges and the price source."""
    L = [f"models ({cat.source}):", "",
         f"{'id':<24} {'adapter':<8} {'cli model':<24} {'effort':<7} {'basis':<15} {'in/cached/out USD/M':<22} label"]
    for spec in cat.models.values():
        pr, src = cat.price(spec.id)
        price = "–" if not pr else "/".join("–" if pr.get(k) is None else f"{pr[k]:g}" for k in ("input", "cached", "output"))
        basis = spec.cost_basis or ADAPTERS[spec.adapter].default_cost_basis
        L.append(f"{spec.id:<24} {spec.adapter:<8} {spec.model:<24} {spec.effort:<7} {basis:<15} "
                 f"{price + (' *' if src == 'cache' else ''):<22} {spec.label}")
    L += ["", "presets:"] + [f"  {k:<12} {', '.join(v)}" + ("   (default)" if k == cat.default_models else "")
                             for k, v in cat.presets.items()]
    L += ["", f"judges: text {cat.judge} · vision {cat.vision_judge}"]
    L.append("prices: models.toml" + (f"; * = OpenRouter cache {cat.price_cache_info} (estimator only)"
                                         if cat.price_cache else "; refresh the estimator's copy with --refresh-prices"))
    L.append(f"adapters: {', '.join(ADAPTERS)}")
    return "\n".join(L)


def preflight(models: list[tuple[str, str]], judges: list[str]) -> list[str]:
    """Problems that would make every run of a model fail: a missing CLI, an omp profile not set up."""
    errs = []
    for mid in dict.fromkeys([m for m, _ in models] + [j.partition("@")[0] for j in judges]):
        spec = model_spec(mid)
        ad = ADAPTERS[spec.adapter]
        exe = ad.exe(spec)
        if exe and not shutil.which(exe):
            errs.append(f"{mid}: `{exe}` not found on PATH")
        if isinstance(ad, OmpAdapter) and not ad.profile_ready():
            errs.append(f"{mid}: omp profile {ad.setting('profile')!r} is not set up (one-time setup: README, "
                        "'omp profile for the evals'); the key never goes in argv or the agent's environment")
    return errs


# ============================================================ main

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", help="comma-separated case ids (default: all)")
    ap.add_argument("--cases-file", type=Path, default=DEFAULT_CASES)
    ap.add_argument("--cases-dir", type=Path, default=DEFAULT_CASES_DIR,
                    help="also load every *.json here (a list of cases or {cases: [...]}); default evals/cases/")
    ap.add_argument("--validate-cases", action="store_true", help="check the cases (schema, ids, fixtures, "
                    "assertion types, neutral-domain terms) and exit non-zero on errors")
    ap.add_argument("--tag", action="append", default=[],
                    help="keep cases with any of these tags (comma-separated, repeatable): an area (shell, audit…), "
                         "a depends_on value (wave2) or a derived tag (executed, tmux, vision, judge, fixture-files)")
    ap.add_argument("--exclude-tag", action="append", default=[], help="drop cases with any of these tags")
    ap.add_argument("--models-file", type=Path, default=DEFAULT_MODELS_FILE, help="models, presets, judges (TOML)")
    ap.add_argument("--list-models", action="store_true", help="print the models, presets and judges, then exit")
    ap.add_argument("--refresh-prices", action="store_true",
                    help=f"fetch OpenRouter's public prices into {PRICE_CACHE_FILE.name} (the estimator uses it)")
    ap.add_argument("--models", help="comma-separated presets, model ids or ID@EFFORT (default: [defaults] models "
                                     "in models.toml, the 4 models of the published comparison)")
    ap.add_argument("--arms", default="skill,baseline")
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--judge", help="text judge model (default: [judges] text in models.toml)")
    ap.add_argument("--vision-judge", help="vision judge for vision_rubric (default: [judges] vision)")
    ap.add_argument("--no-judge", action="store_true", help="skip judge and vision assertions (graded as missing)")
    ap.add_argument("--no-exec", action="store_true",
                    help="skip executed assertions (live: graded as missing; --regrade: keep earlier results)")
    ap.add_argument("--dry-run", action="store_true", help="print the matrix and a cost estimate; call nothing")
    ap.add_argument("--list-jobs", action="store_true", help="print every job's run id and effort, then exit")
    ap.add_argument("--estimate-from", type=Path, action="append",
                    help="results dir whose token counts drive --dry-run (repeatable; default: newest)")
    ap.add_argument("--max-usd", type=float, help="hard stop: no new run starts, and a live omp run is killed, "
                                                  "once agent + judge spend (all bases) reaches this")
    ap.add_argument("--budget-basis", choices=["all", "billed"], default="all",
                    help="what --max-usd counts: all = agent + judge of every basis (default); "
                         "billed = only real OpenRouter USD")
    ap.add_argument("--skill-dir", type=Path, help="the skill under test (default: ../skills/tui-design, or "
                                                   "$EVAL_SKILL_DIR)")
    ap.add_argument("--results-root", type=Path, help="where timestamped results dirs go (default: evals/runs/, "
                                                      "or $EVAL_RESULTS_ROOT)")
    ap.add_argument("--out", type=Path, help="results dir (default <results root>/<timestamp>/)")
    ap.add_argument("--timeout", type=int, default=900, help="seconds per agent run (default 900; a case's or "
                                                             "model's own timeout wins)")
    ap.add_argument("--judge-timeout", type=int, default=300)
    ap.add_argument("--jobs", type=int, default=1, help="parallel runs (default 1); serial cases still run alone")
    ap.add_argument("--keep-workdirs", action="store_true")
    ap.add_argument("--resume", type=Path, metavar="DIR", help="continue a results dir: keep runs that finished without error, run only the failed, skipped or missing ones (a larger --reps adds only the new repetitions)")
    ap.add_argument("--stop-after-errors", type=int, default=2, metavar="N", help="stop scheduling a model after N consecutive errored runs (quota, auth, rate limit…); its remaining jobs stay for --resume (default 2, 0 = never)")
    ap.add_argument("--regrade", type=Path, help="re-check assertions on a results dir's saved files; no agent runs")
    ap.add_argument("--rejudge", action="store_true", help="with --regrade: also call the text and vision judges again")
    ap.add_argument("--scan-contamination", type=Path, metavar="DIR",
                    help="mark saved runs whose agent read the skill outside its run dir or searched the disk; no agent runs")
    args = ap.parse_args(argv)

    configure_paths(args.skill_dir, args.results_root)
    try:
        cat = load_catalog(args.models_file, PRICE_CACHE_FILE)
    except ConfigError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    set_catalog(cat)
    if args.list_models:
        print(list_models(cat))
        return 0
    if args.refresh_prices:
        try:
            lines = refresh_prices(cat, PRICE_CACHE_FILE)
        except (OSError, ValueError) as e:
            print(f"error: could not fetch OpenRouter prices: {redact_secrets(str(e))}", file=sys.stderr)
            return 1
        print("\n".join(lines) + f"\nwrote {PRICE_CACHE_FILE}")
        return 0
    files = case_files(args.cases_file, args.cases_dir)
    if args.validate_cases:
        errs = validate_case_files(files)
        n = len(merge_case_docs(files)[0]["cases"]) if not errs or "cannot read" not in errs[0] else 0
        print("\n".join(f"error: {e}" for e in errs) if errs else
              f"ok: {n} cases in {', '.join(p.name for p in files)}")
        return 1 if errs else 0

    ids = [i.strip() for i in args.cases.split(",") if i.strip()] if args.cases else None
    split = lambda xs: [t.strip() for x in xs for t in x.split(",") if t.strip()]  # noqa: E731
    try:
        cases = filter_cases(load_cases(files, ids), split(args.tag), split(args.exclude_tag))
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if not cases:
        print("error: no case left after --cases/--tag/--exclude-tag", file=sys.stderr)
        return 2
    args.judge = args.judge or cat.judge
    args.vision_judge = args.vision_judge or cat.vision_judge
    try:
        models = cat.resolve(args.models or cat.default_models)
        for j in (args.judge, args.vision_judge):
            cat.get(j.partition("@")[0])
    except ConfigError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    if set(arms) - set(ARMS):
        print(f"error: arms must be among {ARMS}", file=sys.stderr)
        return 2
    jobs = build_jobs(cases, models, arms, args.reps)
    if args.list_jobs:
        for c, m, e, arm, rep in jobs:
            print(f"{run_id_for(c['id'], m, arm, rep)} {e}" + (" serial" if c.get("serial") else ""))
        print(f"{len(jobs)} jobs")
        return 0

    if args.scan_contamination:
        found = scan_contamination(args.scan_contamination)
        print("\n".join(found) or "no contaminated runs")
        return 0
    if args.regrade:
        runs = regrade(args.regrade, cases, args)
        if not args.cases and not args.tag and not args.exclude_tag:
            write_dataset(args.regrade, cases)
        md, data = summarize(runs, cases)
        (args.regrade / "summary.md").write_text(md)
        (args.regrade / "summary.json").write_text(json.dumps(data, indent=2))
        print(md)
        return 0

    if args.dry_run:
        refs = args.estimate_from or ([latest_results_dir()] if latest_results_dir() else [])
        print(dry_run(cases, models, arms, args.reps, refs))
        return 0

    judges = [] if args.no_judge else [args.judge] + (
        [args.vision_judge] if any(a["type"] == "vision_rubric" for c in cases for a in c["assertions"]) else [])
    problems = preflight(models, judges)
    if problems:
        print("error: " + "\n       ".join(problems), file=sys.stderr)
        return 2
    out = args.resume or args.out or (RESULTS_DIR / time.strftime("%Y%m%d-%H%M%S"))
    runs_dir = out / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps({
        "cases": [c["id"] for c in cases], "models": models, "arms": arms, "reps": args.reps,
        "tags": split(args.tag), "exclude_tags": split(args.exclude_tag),
        "judge": None if args.no_judge else args.judge, "vision_judge": None if args.no_judge else args.vision_judge,
        "no_exec": args.no_exec, "max_usd": args.max_usd, "budget_basis": args.budget_basis, "timeout": args.timeout,
        "models_file": args.models_file.name, "case_files": [p.name for p in files],
        "started": time.strftime("%Y-%m-%dT%H:%M:%S")}, indent=2))

    write_dataset(out, cases)
    budget = Budget(args.max_usd, args.budget_basis)
    runs: list[dict] = []
    if args.resume:                                  # keep clean runs; failed, skipped or missing ones run again
        kept, todo = resume_split(jobs, runs_dir)
        runs.extend(kept)
        print(f"resume: {len(kept)} run(s) kept, {len(todo)} to run", flush=True)
        jobs = todo
    lock = threading.Lock()
    counter = {"n": 0}
    streak: dict[str, int] = {}                      # consecutive errored runs per model
    stopped: dict[str, str] = {}                     # model -> last error, once the breaker trips
    leak = threading.Event()                         # a secret reached a run's artifacts: stop everything

    def work(job):
        c, m, e, arm, rep = job
        if leak.is_set() or not budget.can_start() or m in stopped:
            return None
        with lock:
            counter["n"] += 1
            k = counter["n"]
        print(f"[{k}/{len(jobs)}] {c['id']} · {m}@{e} · {arm} · rep {rep}", flush=True)
        rec = run_one(c, m, e, arm, rep, args, budget, runs_dir)
        if rec.get("secret_leak"):
            leak.set()
            print(f"    !! {rec['run_id']}: SECRET LEAK ({', '.join(rec['secret_leak']['names'])}); artifacts "
                  "redacted, campaign stopped", flush=True)
        if rec.get("skipped"):
            print(f"    -> {rec['run_id']}: SKIPPED ({rec['skipped']})", flush=True)
            with lock:
                runs.append(rec)
            return rec
        sc = rec.get("score") or {}
        extra = float((rec.get("judge") or {}).get("cost_usd") or 0) + float((rec.get("vision") or {}).get("cost_usd") or 0)
        print(f"    -> {rec['run_id']}: {sc.get('passed')}/{sc.get('graded')} passed · ${rec.get('cost_usd', 0):.4f} "
              f"({rec.get('cost_basis')}) + judges ${extra:.4f} · "
              f"{rec.get('wall_s')}s · tools {rec.get('tool_calls')} · skill_loaded={rec.get('skill_loaded')}"
              + (f" · ERROR {rec['error']}" if rec.get("error") else "")
              + f" · spent ${budget.spent:.4f}", flush=True)
        with lock:
            runs.append(rec)
            streak[m] = streak.get(m, 0) + 1 if rec.get("error") else 0
            if args.stop_after_errors and streak[m] >= args.stop_after_errors and m not in stopped:
                stopped[m] = str(rec.get("error"))[:200]
                print(f"    !! {m}: {streak[m]} errors in a row, no more runs for this model ({stopped[m]})", flush=True)
        return rec

    run_jobs(jobs, args.jobs, work)
    ran = {r["run_id"] for r in runs}
    not_started = sum(1 for j in jobs if run_id_for(j[0]["id"], j[1], j[3], j[4]) not in ran)
    errored = sum(1 for r in runs if r.get("error"))
    md, data = summarize(runs, cases)
    if leak.is_set():
        md += ("\n**Stopped: a secret reached a run's artifacts** (see `secret_leak` in the run JSON; the files are "
               "redacted). Find how it got there before running again.\n")
    if stopped:
        md += "\n**Models stopped after repeated errors:** " + "; ".join(f"{k} ({v})" for k, v in stopped.items()) + "\n"
    if not_started and not budget.can_start():
        md += f"\n**Stopped by --max-usd ${args.max_usd}.**\n"
    if not_started or errored:
        md += (f"\n**{not_started} run(s) not started, {errored} errored.** Continue with the same arguments plus "
               f"`--resume {out}`: clean runs are kept, only these run again.\n")
    (out / "summary.md").write_text(md)
    (out / "summary.json").write_text(json.dumps(data, indent=2))
    print("\n" + md)
    print(f"results in {out}")
    return 3 if leak.is_set() else 0


if __name__ == "__main__":
    sys.exit(main())
