#!/usr/bin/env python3
"""A fake agent CLI for the `command` adapter: no model, no network, deterministic.

    echo_agent.py --model M --prompt-file FILE --workdir DIR [--usage FILE] [--skill DIR]
    echo_agent.py --version

Reads the prompt from --prompt-file (or stdin when it is "-"), writes `echo-notes.md` into the workdir, prints a
short final answer on stdout and, with --usage, a usage JSON file. With --skill it lists the skill's SKILL.md in
the answer, so a skill arm and a baseline arm differ. Used by the unit tests and as a template for wiring a real
CLI through models.toml.
"""
import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", action="store_true")
    ap.add_argument("--model", default="echo-1")
    ap.add_argument("--prompt-file", default="-")
    ap.add_argument("--workdir", default=".")
    ap.add_argument("--usage")
    ap.add_argument("--skill")
    a = ap.parse_args()
    if a.version:
        print("echo-agent 1.0")
        return 0
    prompt = sys.stdin.read() if a.prompt_file == "-" else Path(a.prompt_file).read_text()
    wd = Path(a.workdir)
    (wd / "echo-notes.md").write_text(f"# Notes\n\nRequest had {len(prompt.split())} words.\n")
    skill = f" Skill: {Path(a.skill, 'SKILL.md').is_file()}." if a.skill else ""
    print(f"ECHO[{a.model}] {prompt.strip().splitlines()[0][:80] if prompt.strip() else ''}{skill}")
    if a.usage:
        Path(a.usage).write_text(json.dumps({"input": len(prompt), "cached": 0, "output": 12, "reasoning": 0}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
