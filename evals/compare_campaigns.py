#!/usr/bin/env python3
"""Compare two behavior-eval campaigns case by case (works on partial results dirs, so it can run mid-campaign).

For every (case, model) present in both dirs for the chosen arm: pass rate, which assertions flipped, tokens,
cost, wall time, tool calls, errors and whether the skill loaded. Then a per-model summary and flags worth a look
(a pass-rate drop, a new error or timeout, the skill not loading, a token or cost rise). With one repetition a
single case flipping is noise; token and cost changes and loaded/not-loaded are the low-noise signals.

Usage:
  python3 evals/compare_campaigns.py OLD_DIR NEW_DIR [--arm skill] [--cases a,b] [--models m1,m2] [--md OUT.md]
"""

from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from pathlib import Path


def load(d: Path, arm: str) -> dict[tuple[str, str, int], dict]:
    out = {}
    for f in sorted((d / "runs").glob("*.json")):
        try:
            r = json.loads(f.read_text())
        except ValueError:
            continue
        if isinstance(r, dict) and r.get("run_id") and r.get("arm") == arm:
            out[(r["case"], r["model"], int(r.get("rep") or 1))] = r
    return out


def tokens(r: dict) -> int:
    t = r.get("tokens") or {}
    return sum(int(t.get(k) or 0) for k in ("input", "cached", "output"))


def rate(r: dict) -> float | None:
    sc = r.get("score") or {}
    return sc["passed"] / sc["graded"] if not r.get("error") and sc.get("graded") else None


def flips(a: dict, b: dict) -> list[str]:
    pa = {x.get("id"): x.get("passed") for x in a.get("assertions") or []}
    pb = {x.get("id"): x.get("passed") for x in b.get("assertions") or []}
    return [f"{k} {'✓→✗' if pa[k] else '✗→✓'}" for k in pa if k in pb and pa[k] is not None and pb[k] is not None
            and bool(pa[k]) != bool(pb[k])]


def pct(new: float, old: float) -> str:
    return f"{(new - old) / old * 100:+.0f}%" if old else "n/a"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("old", type=Path)
    ap.add_argument("new", type=Path)
    ap.add_argument("--arm", default="skill", choices=["skill", "baseline"])
    ap.add_argument("--cases", help="comma-separated case ids to keep")
    ap.add_argument("--models", help="comma-separated model ids to keep")
    ap.add_argument("--md", type=Path, help="also write the report as Markdown here")
    a = ap.parse_args(argv)
    old, new = load(a.old, a.arm), load(a.new, a.arm)
    keep_c = set(a.cases.split(",")) if a.cases else None
    keep_m = set(a.models.split(",")) if a.models else None
    keys = sorted(k for k in new if k in old and (not keep_c or k[0] in keep_c) and (not keep_m or k[1] in keep_m))
    lines = [f"# {a.new.name} vs {a.old.name} ({a.arm} arm)", "",
             f"{len(keys)} comparable runs (same case, model, rep). Old skill "
             f"{', '.join(sorted({((old[k].get('identity') or {}).get('skill_hash') or 'none')[:8] for k in keys})) or '-'} → new "
             f"{', '.join(sorted({((new[k].get('identity') or {}).get('skill_hash') or 'none')[:8] for k in keys})) or '-'}.", "",
             "| case | model | pass old → new | flipped | tokens | cost | wall | tools | loaded | errors |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    per_model: dict[str, dict[str, list]] = {}
    flags = []
    for k in keys:
        o, n = old[k], new[k]
        ro, rn = rate(o), rate(n)
        f = flips(o, n)
        to, tn = tokens(o), tokens(n)
        co, cn = float(o.get("cost_usd") or 0), float(n.get("cost_usd") or 0)
        wo, wn = float(o.get("wall_s") or 0), float(n.get("wall_s") or 0)
        lo, ln = bool(o.get("skill_loaded")), bool(n.get("skill_loaded"))
        eo, en = o.get("error") or "", n.get("error") or ""
        fmt = lambda x: "err" if x is None else f"{x * 100:.0f}%"
        lines.append(f"| {k[0]} | {k[1].split('/')[-1]} | {fmt(ro)} → {fmt(rn)} | {', '.join(f) or '—'} | {pct(tn, to)} | "
                     f"${co:.2f} → ${cn:.2f} | {wo / 60:.1f} → {wn / 60:.1f} min | {o.get('tool_calls', '?')} → "
                     f"{n.get('tool_calls', '?')} | {'y' if lo else 'n'} → {'y' if ln else 'n'} | "
                     f"{(eo[:20] or '—')} → {(en[:20] or '—')} |")
        m = per_model.setdefault(k[1], {"ro": [], "rn": [], "tok": [], "co": [], "cn": [], "wo": [], "wn": []})
        if ro is not None and rn is not None:
            m["ro"].append(ro); m["rn"].append(rn)
        if to and tn:
            m["tok"].append(tn / to)
        m["co"].append(co); m["cn"].append(cn); m["wo"].append(wo); m["wn"].append(wn)
        if ro is not None and rn is not None and rn < ro - 0.19:
            flags.append(f"pass drop {k[0]} · {k[1]}: {ro * 100:.0f}% → {rn * 100:.0f}% ({', '.join(f)})")
        if en and not eo:
            flags.append(f"new error {k[0]} · {k[1]}: {en[:60]}")
        if a.arm == "skill" and lo and not ln:
            flags.append(f"skill no longer loaded {k[0]} · {k[1]}")
        if a.arm == "skill" and ln and not lo:
            flags.append(f"skill now loads {k[0]} · {k[1]}")
        if to and tn > to * 1.25:
            flags.append(f"tokens up {pct(tn, to)} {k[0]} · {k[1]}")
    lines += ["", "## Per model", "", "| model | runs | mean pass old → new | median token ratio | cost old → new | wall old → new |",
              "|---|---|---|---|---|---|"]
    for mdl, m in sorted(per_model.items()):
        mp = lambda xs: f"{st.mean(xs) * 100:.0f}%" if xs else "n/a"
        ratio = f"{st.median(m['tok']):.2f}×" if m["tok"] else "n/a"
        lines.append(f"| {mdl} | {len(m['co'])} | {mp(m['ro'])} → {mp(m['rn'])} | {ratio} | ${sum(m['co']):.2f} → ${sum(m['cn']):.2f} | "
                     f"{sum(m['wo']) / 60:.0f} → {sum(m['wn']) / 60:.0f} min |")
    lines += ["", "## Flags", ""] + ([f"- {x}" for x in flags] or ["- none"])
    lines += ["", "Read with care: one repetition per case, so a single flip is not a finding; tokens, cost and "
              "loaded/not-loaded are the low-noise signals."]
    text = "\n".join(lines) + "\n"
    sys.stdout.write(text)
    if a.md:
        a.md.write_text(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
