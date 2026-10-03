#!/usr/bin/env python3
"""Experiment ledger for behavior-eval campaigns.

Builds one reproducible record per results dir from the per-run files (not from `config.json`, which a `--resume`
pass overwrites): which skill, case set, runner, judges and models ran, the passes it took (from `*.log`), pass
rates per model and per area, cost by basis, tokens, errors, and where it was exported. The record is upserted into
a JSONL ledger keyed by the results dir name, so re-running after `--regrade` or a resume replaces the entry.

Usage:
  python3 evals/ledger.py RESULTS_DIR [--ledger PATH] [--label TEXT] [--print]
  python3 evals/ledger.py --list [--ledger PATH]

Default ledger: evals/ledger.jsonl (or $EVAL_LEDGER). The ledger holds only what the runs can prove; the
interpretation of a campaign is written by people (the published one: docs/evals.md).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES_FILE = HERE / "behavior-evals.json"
CASES_DIR = HERE / "cases"


RUNS_ROOT = HERE / "runs"     # default results root of run_behavior_evals.py (gitignored)
DEFAULT_LEDGER = Path(os.environ["EVAL_LEDGER"]) if os.environ.get("EVAL_LEDGER") else HERE / "ledger.jsonl"


def sha(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def case_files() -> list[Path]:
    extra = sorted(CASES_DIR.glob("*.json")) if CASES_DIR.is_dir() else []
    return ([CASES_FILE] if CASES_FILE.is_file() else []) + extra


def case_set_hash() -> str | None:
    """sha256 of behavior-evals.json alone (comparable with older records), or over it plus every cases/*.json."""
    files = case_files()
    if len(files) <= 1:
        return sha(CASES_FILE)
    h = hashlib.sha256()
    for f in files:
        h.update(f.name.encode() + b"\0" + f.read_bytes() + b"\n")
    return h.hexdigest()


def read_cases() -> list[dict]:
    out = []
    for f in case_files():
        doc = json.loads(f.read_text())
        out += doc if isinstance(doc, list) else doc.get("cases", [])
    return out


def load_runs(d: Path) -> list[dict]:
    runs = []
    for f in sorted((d / "runs").glob("*.json")):
        try:
            r = json.loads(f.read_text())
        except ValueError:
            continue
        if isinstance(r, dict) and r.get("run_id"):
            runs.append(r)
    return runs


def passes(d: Path) -> list[dict]:
    """One entry per log file: start line, how many jobs it planned, how many finished, breaker or budget stops."""
    out = []
    for log in sorted(d.glob("*.log"), key=lambda f: f.stat().st_mtime):
        t = log.read_text(errors="replace")
        planned = re.findall(r"^\[\d+/(\d+)\]", t, re.M)
        out.append({
            "log": log.name,
            "planned": int(planned[-1]) if planned else 0,
            "finished": len(re.findall(r"^\s+-> ", t, re.M)),
            "kept_from_resume": int((re.findall(r"resume: (\d+) run\(s\) kept", t) or ["0"])[0]),
            "breakers": re.findall(r"^\s+!! (.*)$", t, re.M),
            "budget_stop": "Stopped by --max-usd" in t,
        })
    return out


def pct(xs: list[float]) -> float | None:
    return round(100 * st.mean(xs), 1) if xs else None


def build(d: Path, label: str = "", baseline_from: Path | None = None) -> dict:
    runs = load_runs(d)
    if baseline_from:   # skill-only campaign: compare against another campaign's baselines for the same cases/models
        mine = {(r.get("case"), r.get("model")) for r in runs if r.get("arm") == "skill"}
        runs = runs + [r for r in load_runs(baseline_from) if r.get("arm") == "baseline" and (r.get("case"), r.get("model")) in mine]
    areas = {}
    for c in read_cases():
        areas[c["id"]] = c.get("area") or (c.get("tags") or ["?"])[0]
    ids = [r.get("identity") or {} for r in runs]
    per_model = defaultdict(lambda: defaultdict(list))
    per_area = defaultdict(lambda: defaultdict(list))
    cost = defaultdict(float)
    judge_cost = 0.0
    for r in runs:
        m, arm = r.get("model", "?"), r.get("arm", "?")
        borrowed = bool(baseline_from) and r.get("arm") == "baseline"
        if not borrowed:                                       # borrowed baselines were paid by their own campaign
            cost[r.get("cost_basis") or "?"] += float(r.get("cost_usd") or 0)
        j = r.get("judge") or {}
        judge_cost += float(j.get("cost_usd") or 0) if isinstance(j, dict) and not borrowed else 0
        pm = per_model[m]
        if r.get("error"):
            pm[f"{arm}_errors"].append(1)
            continue
        sc = r.get("score") or {}
        if sc.get("graded"):
            rate = sc["passed"] / sc["graded"]
            pm[arm].append(rate)
            per_area[(areas.get(r.get("case"), "?"), m)][arm].append(rate)
        tok = r.get("tokens") or {}
        pm[f"{arm}_tokens"].append(sum(tok.get(k, 0) for k in ("input", "cached", "output")))
        pm[f"{arm}_cost"].append(float(r.get("cost_usd") or 0))
        pm[f"{arm}_wall"].append(float(r.get("wall_s") or 0))
        if arm == "skill":
            pm["skill_loaded"].append(1 if r.get("skill_loaded") else 0)
    models = {}
    for m, v in sorted(per_model.items()):
        s, b = pct(v["skill"]), pct(v["baseline"])
        models[m] = {
            "skill_pass_pct": s, "baseline_pass_pct": b,
            "delta_pts": round(s - b, 1) if s is not None and b is not None else None,
            "skill_loaded": f"{sum(v['skill_loaded'])}/{len(v['skill_loaded'])}",
            "cost_per_run_usd": {"skill": round(st.mean(v["skill_cost"]), 4) if v["skill_cost"] else None,
                                 "baseline": round(st.mean(v["baseline_cost"]), 4) if v["baseline_cost"] else None},
            "token_ratio_median": round(st.median(v["skill_tokens"]) / st.median(v["baseline_tokens"]), 1)
            if v["skill_tokens"] and v["baseline_tokens"] and st.median(v["baseline_tokens"]) else None,
            "wall_median_s": {"skill": round(st.median(v["skill_wall"])) if v["skill_wall"] else None,
                              "baseline": round(st.median(v["baseline_wall"])) if v["baseline_wall"] else None},
            "errors": {"skill": len(v["skill_errors"]), "baseline": len(v["baseline_errors"])},
        }
    areas_out = {}
    for (area, m), v in sorted(per_area.items()):
        s, b = pct(v["skill"]), pct(v["baseline"])
        areas_out.setdefault(area, {})[m] = round(s - b, 1) if s is not None and b is not None else None
    uniq = lambda key: sorted({i.get(key) for i in ids if i.get(key)})
    state = d / "export-state.json"
    targets = json.loads(state.read_text()).get("targets", {}) if state.is_file() else {}
    exported = sorted({f"{k.split('|')[0]}:{k.split('|')[-1]}" for k in targets})   # platform:dataset, no host
    return {
        "campaign": d.name,
        "label": label,
        "results_dir": str(d.relative_to(HERE)) if d.is_relative_to(HERE) else d.name,   # no absolute paths
        "runs": len([r for r in runs if not baseline_from or r.get("arm") == "skill"]),
        "baseline_from": baseline_from.name if baseline_from else None,
        "errored_runs": sum(1 for r in runs if r.get("error")),
        "started": min((r.get("started_at") for r in runs if r.get("started_at")), default=None),
        "skill_hashes": uniq("skill_hash"),
        "case_set_hash": case_set_hash(),
        "runner_hash": sha(HERE / "run_behavior_evals.py"),
        "models_hash": sha(HERE / "models.toml"),
        "adapters": uniq("adapter_version"),
        "judges": uniq("judge"), "vision_judges": uniq("vision_judge"),
        "models": [f"{m}@{e}" for m, e in sorted({(i.get("model"), i.get("effort")) for i in ids if i.get("model")})],
        "cases": len({r.get("case") for r in runs}),
        "passes": passes(d),
        "per_model": models,
        "delta_by_area": areas_out,
        "cost_usd": {k: round(v, 2) for k, v in sorted(cost.items())} | {"judges_api_equivalent": round(judge_cost, 2)},
        "exported_to": exported,
    }


def upsert(ledger: Path, rec: dict) -> None:
    lines = [json.loads(l) for l in ledger.read_text().splitlines() if l.strip()] if ledger.is_file() else []
    lines = [l for l in lines if l.get("campaign") != rec["campaign"]] + [rec]
    lines.sort(key=lambda l: l.get("started") or "")
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text("".join(json.dumps(l, ensure_ascii=False, sort_keys=True) + "\n" for l in lines))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results_dir", nargs="?", type=Path)
    ap.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    ap.add_argument("--label", default="", help="short human name for the campaign")
    ap.add_argument("--print", action="store_true", help="print the record instead of writing it")
    ap.add_argument("--baseline-from", type=Path, help="for a skill-only campaign: take baseline runs from this campaign (same case and model)")
    ap.add_argument("--list", action="store_true", help="list the campaigns in the ledger")
    a = ap.parse_args(argv)
    if a.list:
        for l in (a.ledger.read_text().splitlines() if a.ledger.is_file() else []):
            r = json.loads(l)
            deltas = ", ".join(f"{m.split('/')[-1]} {v['delta_pts']:+}" for m, v in r["per_model"].items()
                               if v.get("delta_pts") is not None)
            print(f"{r['campaign']:40} {r['runs']:4} runs · {deltas} · billed ${r['cost_usd'].get('billed', 0)}")
        return 0
    if not a.results_dir:
        ap.error("give a results dir, or --list")
    rec = build(a.results_dir.resolve(), a.label, a.baseline_from.resolve() if a.baseline_from else None)
    if a.print:
        print(json.dumps(rec, indent=2, ensure_ascii=False))
    else:
        upsert(a.ledger, rec)
        print(f"ledger: {a.ledger} ← {rec['campaign']} ({rec['runs']} runs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
