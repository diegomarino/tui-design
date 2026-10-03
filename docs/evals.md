# Evals

The repository measures the skill instead of asserting that it helps. Two harnesses live in [`evals/`](../evals/),
outside the installed folder, so an agent under test never sees the cases or their checks. This page is the
published result. How to run and extend the harness is [evals/README.md](../evals/README.md).

## Behavior

24 cases, the same prompt and the same fixtures in each arm. The `skill` arm has the skill installed. The
`baseline` arm does not. Each case is graded by 3–6 boolean assertions: program checks on the files and the
answer, executed checks that run the agent's code, judge questions answered yes or no by a model, and one
rubric scored from rendered PNGs. The cases cover 12 areas: host capabilities, frames, review, design ambition,
honest data, color, keys, lifecycle, the shell contract, audit, build, and archetypes.

The published run is the 2026-10-03 campaign: four models, one repetition, 192 runs.

| Model | Skill | Baseline | Δ |
|---|---|---|---|
| Opus 5.5 | 96 % | 62 % | +34 |
| GPT-6.1-Sol | 83 % | 58 % | +25 |
| Qwen3.8 Max | 96 % | 59 % | +37 |
| GLM-5.3 | 89 % | 60 % | +29 |

The skill arm costs 2.5–4× the baseline per run. About half the gain is assertions on the skill's own artifacts
(`.mock` frames, the `#! caps:` line, `test_card.py`), which a baseline cannot know. Without those, the deltas
are +20, +13, +24 and +14.

### By area

Delta in points, skill minus baseline.

| Area | Opus | GPT | Qwen | GLM |
|---|---|---|---|---|
| host (capabilities, measure vs assume) | +60 | +40 | +50 | +50 |
| frames (stated size, lint-clean) | +57 | +50 | +61 | +22 |
| review | +33 | +33 | +43 | +45 |
| ambition (three concepts, craft rubric) | +60 | +40 | +50 | +60 |
| data (real vs invented) | +50 | +50 | +50 | +50 |
| color | +38 | +25 | +13 | +25 |
| keys | +33 | +33 | +67 | +33 |
| lifecycle | +13 | +13 | +13 | +13 |
| shell | 0 | −17 | +33 | +33 |
| audit | 0 | +10 | +20 | +20 |
| build | +25 | −6 | +28 | +36 |
| archetypes | +23 | +26 | +34 | −7 |

The skill helps most where a baseline is weak: measuring the host, drawing a frame that is the stated size,
keeping real data separate from invented data, and proposing distinct concepts. Three cells are negative, each
from one case: GPT's build run never wrote the frame file the checks render (`build-textual-from-mock`); GLM's
picker did not return the chosen branch (`inline-picker-branch`); GPT's shell delta is one assertion.

### Limits of this number

- One repetition. The cases were written by the skill's author, from failures the skill was then built to fix.
  The judges are Anthropic models, including when they grade Opus.
- Two skill runs timed out and are excluded from the rates: GPT on `live-capture-audit`, Qwen on
  `screenshot-audit`.
- One baseline run was contaminated through Spotlight, discarded, and re-run.
- Two assertions were corrected after the run, and the campaign was regraded.
- The measured skill tree is `b3b54ed4` (commit `dcc20cd`). The skill in this repository has changed since
  that run, including the Python SIGPIPE `flush()` (`f35e7e5`). These numbers do not include those changes.
- Four cases in the repository were hardened after this run: `inline-picker-branch`,
  `editor-handoff-bubbletea`, `fix-broken-mock`, and `live-capture-audit`. The tables describe the earlier
  case set.

The machine-readable record of this run is [evals/ledger.jsonl](../evals/ledger.jsonl). Raw transcripts stay in
`evals/runs/`, which is gitignored.

## Trigger

30 queries, given only the skill's name and description. 17 should load the skill. 13 are near misses (web
dashboards, terminal-emulator themes, shell prompts, and the like). The run does not grade the answer.

The last full pass, on 2026-10-01 through Claude Code, once each, scored precision and recall 1.00. The
description has changed since that pass. That figure is historical until the released description is rerun.

## Repeat a run

```bash
python3 evals/run_behavior_evals.py --list-models                                  # models, presets, judges, prices
python3 evals/run_behavior_evals.py --validate-cases
python3 evals/run_behavior_evals.py --models smoke --cases sketch-80x24 --dry-run  # matrix and a cost estimate
python3 evals/run_behavior_evals.py --models example-echo --no-judge --cases sketch-80x24 --arms skill   # offline
python3 evals/run_trigger_evals.py --harness claude --ids T01,N03
```

A real run calls models and costs money. `--dry-run` estimates it and `--max-usd` caps it. Raw runs go to
`evals/runs/`. The harness is standard-library Python 3.11+. The repeat contract (case schema, isolation,
assertion types) is [evals/README.md](../evals/README.md). Adding a case or a model:
[architecture.md](contributing/architecture.md#add-an-eval-case).
