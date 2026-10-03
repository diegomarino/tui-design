#!/usr/bin/env python3
"""Trigger evaluation runner for the tui-design skill (stdlib only).

For every query in trigger-evals.json it creates a fresh temporary project
directory that contains the skill, runs the chosen agent harness once per
repeat (strictly sequentially), and records whether the agent loaded the skill.

  claude: <tmp>/.claude/skills/tui-design   -> `claude -p ... --output-format stream-json --verbose`
          triggered = a tool_use named "Skill" whose input skill is tui-design
  codex : <tmp>/.agents/skills/tui-design   -> `codex exec --json ...`
          triggered = a command event that reads tui-design/SKILL.md

A run is stopped as soon as the verdict is known (skill loaded, or the agent
did other real work first), which keeps cost low. Never run in parallel: the
runs share your account's rate limits and the model's behavior is timing
sensitive.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent
SKILL_DIR = EVALS_DIR.parent / "skills" / "tui-design"
SKILL_NAME = "tui-design"
DEFAULT_QUERIES = EVALS_DIR / "trigger-evals.json"
# Tools the agent may legitimately call before the Skill tool without that
# counting as "decided not to use the skill".
PRELUDE_TOOLS = {"Skill", "ToolSearch"}


def install_skill(project: Path, harness: str) -> Path:
    rel = ".claude/skills" if harness == "claude" else ".agents/skills"
    dest = project / rel / SKILL_NAME
    dest.parent.mkdir(parents=True, exist_ok=True)
    # The queries live in evals/, outside the skill, so the agent cannot read what it is graded on.
    shutil.copytree(SKILL_DIR, dest, ignore=shutil.ignore_patterns("__pycache__", ".git", ".DS_Store"))
    return dest


def build_command(harness: str, query: str, model: str | None, project: Path) -> list[str]:
    if harness == "claude":
        cmd = ["claude", "-p", "--output-format", "stream-json", "--verbose", "--no-session-persistence"]
        if model:
            cmd += ["--model", model]
        return cmd + ["--", query]
    cmd = ["codex", "exec", "--json", "--skip-git-repo-check", "--ephemeral",
           "--sandbox", "read-only", "-C", str(project)]
    if model:
        cmd += ["-m", model]
    return cmd + ["--", query]


# --- event inspection -------------------------------------------------------

def claude_event(ev: dict) -> tuple[str, str | None]:
    """Return (verdict, note). verdict in {"hit", "other_tool", "done", "error", ""}."""
    t = ev.get("type")
    if t == "assistant":
        for block in (ev.get("message") or {}).get("content") or []:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name = block.get("name")
            if name == "Skill":
                skill = str((block.get("input") or {}).get("skill", ""))
                if skill == SKILL_NAME or skill.endswith(":" + SKILL_NAME):
                    return "hit", skill
                return "other_tool", f"Skill:{skill}"
            if name not in PRELUDE_TOOLS:
                return "other_tool", str(name)
    elif t == "result":
        if ev.get("is_error"):
            return "error", str(ev.get("result") or ev.get("subtype"))[:300]
        return "done", None
    return "", None


def codex_event(ev: dict) -> tuple[str, str | None]:
    t = ev.get("type", "")
    item = ev.get("item") or {}
    itype = item.get("type") or item.get("item_type")
    if itype in ("command_execution", "local_shell_call", "exec_command"):
        cmd = item.get("command")
        if isinstance(cmd, list):
            cmd = " ".join(map(str, cmd))
        cmd = str(cmd or "")
        if f"{SKILL_NAME}/SKILL.md" in cmd:
            return "hit", cmd[:200]
        if t in ("item.started", "item.completed"):
            return "", None  # exploring (ls, rg...) may precede the skill read
    if itype == "agent_message" and t == "item.completed" and len(str(item.get("text", ""))) > 300:
        return "done", "answered without reading the skill"  # a real answer, not commentary
    if t == "turn.completed":
        return "done", None
    if t in ("error", "turn.failed"):
        return "error", json.dumps(ev)[:300]
    return "", None


def run_once(harness: str, query: str, model: str | None, timeout: int) -> dict:
    with tempfile.TemporaryDirectory(prefix="tui-design-eval-") as tmp:
        project = Path(tmp)
        install_skill(project, harness)
        if harness == "codex" and shutil.which("git"):
            subprocess.run(["git", "init", "-q"], cwd=project, check=False)
        cmd = build_command(harness, query, model, project)
        printable = " ".join(shlex_quote(c) for c in cmd)
        print(f"    $ (cd {project}) {printable}", flush=True)
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        inspect = claude_event if harness == "claude" else codex_event
        start = time.time()
        proc = subprocess.Popen(cmd, cwd=project, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, text=True)
        timed_out = threading.Event()

        def _kill():
            timed_out.set()
            proc.kill()

        timer = threading.Timer(timeout, _kill)
        timer.start()
        stderr_buf: list[str] = []
        threading.Thread(target=lambda: stderr_buf.append(proc.stderr.read()), daemon=True).start()
        verdict, note, tools = "", None, []
        try:
            for line in proc.stdout:
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                v, n = inspect(ev)
                if v:
                    verdict, note = v, n
                    if v in ("other_tool", "done", "error", "hit"):
                        break
        finally:
            timer.cancel()
            if proc.poll() is None:
                proc.kill()
            proc.wait()
        elapsed = round(time.time() - start, 1)
        stderr = "".join(stderr_buf).strip()[-300:]
    run = {"command": printable, "triggered": verdict == "hit", "elapsed_s": elapsed}
    if verdict == "hit":
        run["evidence"] = note
    elif timed_out.is_set():
        # Skill loads happen early, so a long run with no skill load counts as "not
        # triggered"; it is flagged so slow or hung runs stay visible in the JSON.
        run["truncated"] = f"killed after {timeout}s without loading the skill"
    elif verdict == "error" or (verdict == "" and proc.returncode not in (0, None, -9)):
        run["error"] = note or stderr or f"exit code {proc.returncode}"
    elif verdict == "":
        run["error"] = "no verdict (stream ended without result)" + (f": {stderr}" if stderr else "")
    else:
        run["first_action"] = note
    return run


def shlex_quote(s: str) -> str:
    import shlex
    return shlex.quote(s)


# --- reporting --------------------------------------------------------------

def summarize(queries: list[dict], results: dict[str, list[dict]]) -> dict:
    tp = fp = tn = fn = errors = 0
    rows, misfires = [], []
    for q in queries:
        runs = results.get(q["id"], [])
        valid = [r for r in runs if "error" not in r]
        k = sum(1 for r in valid if r["triggered"])
        errors += len(runs) - len(valid)
        if q["should_trigger"]:
            tp += k
            fn += len(valid) - k
        else:
            fp += k
            tn += len(valid) - k
        ok = (k == len(valid)) if q["should_trigger"] else (k == 0)
        rows.append({"id": q["id"], "should_trigger": q["should_trigger"], "triggered": k,
                     "valid_runs": len(valid), "errors": len(runs) - len(valid), "ok": ok or not valid})
        if valid and not ok:
            misfires.append({"id": q["id"], "kind": "missed" if q["should_trigger"] else "false trigger",
                             "triggered": f"{k}/{len(valid)}", "query": q["query"]})
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "errors": errors,
            "precision": precision, "recall": recall, "per_query": rows, "misfires": misfires}


def print_report(queries: list[dict], summary: dict) -> None:
    by_id = {q["id"]: q for q in queries}
    print("\n=== Per query (triggered k / valid runs n) ===")
    for r in summary["per_query"]:
        want = "trigger " if r["should_trigger"] else "no-trig "
        flag = "ok  " if r["ok"] else "MISS"
        err = f"  ({r['errors']} errored)" if r["errors"] else ""
        print(f"{flag} {r['id']} [{want}] {r['triggered']}/{r['valid_runs']}{err}  {by_id[r['id']]['query'][:70]}")
    p, rc = summary["precision"], summary["recall"]
    print("\n=== Summary ===")
    print(f"TP={summary['tp']} FN={summary['fn']} FP={summary['fp']} TN={summary['tn']} errored_runs={summary['errors']}")
    print(f"precision={'n/a' if p is None else f'{p:.2f}'}  recall={'n/a' if rc is None else f'{rc:.2f}'}")
    if summary["misfires"]:
        print("\n=== Misfires ===")
        for m in summary["misfires"]:
            print(f"- {m['id']} {m['kind']} ({m['triggered']}): {m['query']}")
    else:
        print("\nNo misfires.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--harness", choices=["claude", "codex"], default="claude")
    ap.add_argument("--ids", help="comma-separated query ids, e.g. T01,N03 (default: all)")
    ap.add_argument("--repeat", type=int, default=1, help="runs per query (default 1)")
    ap.add_argument("--model", help="model passed to the harness (default: harness default)")
    ap.add_argument("--timeout", type=int, default=120, help="per-run timeout in seconds; a run that has not loaded the skill by then counts as not triggered (default 120)")
    ap.add_argument("--queries", type=Path, default=DEFAULT_QUERIES)
    ap.add_argument("--out", type=Path, help="write full results JSON here")
    args = ap.parse_args()

    if not shutil.which(args.harness):
        print(f"error: `{args.harness}` not found on PATH", file=sys.stderr)
        return 2
    queries = json.loads(args.queries.read_text())["queries"]
    if args.ids:
        wanted = [i.strip() for i in args.ids.split(",") if i.strip()]
        unknown = set(wanted) - {q["id"] for q in queries}
        if unknown:
            print(f"error: unknown ids {sorted(unknown)}", file=sys.stderr)
            return 2
        queries = [q for q in queries if q["id"] in wanted]

    results: dict[str, list[dict]] = {}
    total = len(queries) * args.repeat
    n = 0
    for q in queries:
        results[q["id"]] = []
        for rep in range(1, args.repeat + 1):
            n += 1
            print(f"[{n}/{total}] {q['id']} run {rep}/{args.repeat} (expect {'trigger' if q['should_trigger'] else 'no trigger'})", flush=True)
            run = run_once(args.harness, q["query"], args.model, args.timeout)
            results[q["id"]].append(run)
            status = "TRIGGERED" if run["triggered"] else ("ERROR: " + run["error"] if "error" in run else "not triggered" + (" (truncated by timeout)" if "truncated" in run else ""))
            print(f"    -> {status} ({run['elapsed_s']}s)", flush=True)

    summary = summarize(queries, results)
    print_report(queries, summary)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps({
            "harness": args.harness, "model": args.model, "repeat": args.repeat,
            "date": time.strftime("%Y-%m-%d"), "queries": {q["id"]: q for q in queries},
            "runs": results, "summary": summary}, indent=2, ensure_ascii=False))
        print(f"\nresults written to {args.out}")
    return 1 if summary["misfires"] else 0


if __name__ == "__main__":
    sys.exit(main())
