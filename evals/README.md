# Evals

Two kinds: **trigger evals** (does the agent load the skill when it should?) and **behavior evals**
(once loaded, does the agent behave better than the same model without it?). Both runners are stdlib
Python and live outside the installable skill (`../skills/tui-design/`), which they copy into a temp project
per run, so an agent under test never sees the cases or their checks.

Published scores: [docs/evals.md](../docs/evals.md). This file is how to run and extend the harness.
Commands below run from the repository root.

## Trigger evals

These evals measure one thing: given only the skill's frontmatter `description`
(name + description are what the agent sees before deciding), does the agent
load `tui-design` for TUI work and leave it alone for near-miss requests?
They do not grade the quality of the skill's output.

- `trigger-evals.json`: 17 should-trigger (`T01`..`T17`, English and Spanish) and
  13 near-miss should-not-trigger (`N01`..`N13`: web/React, native GUI, terminal
  emulator and editor themes, Nerd Font setup, bash without UI, REST API, CSS
  dashboards, Jupyter, argparse, starship, git). Fields: `id`, `query`,
  `should_trigger`, `area`.
- `run_trigger_evals.py`: stdlib runner. Writes a JSON report with `--out` (keep it under `evals/runs/`,
  which is gitignored).

### How it works

For each query, in strict sequence, the runner creates a fresh temp project
containing a copy of the skill (the queries stay in `evals/`, so the agent cannot read
them), runs the harness once, and stops the run as soon as the verdict is
known.

| Harness | Skill location in temp project | Command | Triggered when |
|---|---|---|---|
| `claude` | `.claude/skills/tui-design` | `claude -p --output-format stream-json --verbose --no-session-persistence -- QUERY` | a `Skill` tool_use whose `skill` is `tui-design` |
| `codex` | `.agents/skills/tui-design` (temp dir is `git init`ed) | `codex exec --json --skip-git-repo-check --ephemeral --sandbox read-only -C TMP -- QUERY` | a command event that reads `tui-design/SKILL.md` |

The exact command is printed for every run.

### Run

```bash
python3 evals/run_trigger_evals.py --harness claude --ids T01,N03        # subset
python3 evals/run_trigger_evals.py --harness claude --repeat 3 --out evals/runs/trigger-claude.json
python3 evals/run_trigger_evals.py --harness codex --model <model> --timeout 180
```

Options: `--harness claude|codex`, `--ids`, `--repeat N`, `--model`, `--timeout`
(seconds per run, default 120), `--out`. Exit code is 1 if there are misfires.
Never run two copies at once; runs share rate limits and timing.

The output lists triggered k/n per query, TP/FN/FP/TN, precision and recall, and
the misfires (missed should-trigger queries and false triggers).

### Cost

Every run is a real model call. A full pass is 30 runs per repeat; use
`--repeat 3` or more for a rate, since triggering is stochastic. Runs end early
on a hit (a few seconds), but a non-trigger run lasts until the agent answers
or the timeout hits (Claude about 10-25 s, Codex up to the timeout on long
"write me X" prompts). A run killed by the timeout without loading the skill
counts as not triggered and is flagged `truncated` in the JSON. Start with
`--ids`, run the full set only after a description change.

### Caveats

- User-level skills, plugins and `CLAUDE.md` still load, so results reflect your
  real setup. A copy of `tui-design` installed globally would shadow the temp
  copy; the runner reports the skill name it saw in `evidence`.
- Codex's skill discovery and event format change between versions; the check
  is a `tui-design/SKILL.md` substring in the command, verified on codex-cli 0.159.3.
- Errored runs (auth, flags) are excluded from the metrics and counted as `errored_runs`.
- A trigger rate holds for the description it was measured on; rerun the full set after editing the
  description. The published figure is in [docs/evals.md](../docs/evals.md).

### Interpreting misfires

- Missed should-trigger query: the description lacks the words the user would
  use. Add the concrete trigger (framework, known TUI name, symptom) to the
  description, not to the body, since the body is not read until after triggering.
- False trigger on a near-miss: the description is too broad or the exclusion is
  missing. Tighten the wording or extend the "Not for ..." clause.
- Then rerun the **full** set, not just the failing ids: a wording change that
  fixes one query commonly moves another. Compare against the previous results file.

## Behavior evals

These answer a different question: **once the skill is loaded, does the agent behave better than the
same model without it?** Each case is a realistic request (English or Spanish) built from a failure
seen in live design and review sessions with agents (labelled T1–T8 in each case's `source`), a gap found in a
comparison with [gfargo/tui-design-skill](https://github.com/gfargo/tui-design-skill), or one of the skill's
branches, in neutral domains (deploy console, log viewer, package updater, backup monitor, CI runners). No case
uses a real product, plugin or person: `banned_terms` in `behavior-evals.json` lists names that must never
appear, and `--validate-cases` (also a unit test) enforces it.

- `behavior-evals.json`: 24 cases, one **skill area** each. Fields: `id`, `source` (which finding or
  reference it guards), `lang`, `area`, `tags` (optional), `depends_on` (optional, e.g. `wave2`), `prompt`,
  `fixtures` (files written into the run's workdir: `lines` or `content` inline, or `src` = a file under
  `fixtures/`, binary allowed), `requires` (optional pre-checks; when one fails the run is **skipped**,
  not failed, and no agent is called), `claude_tools` (optional extra `--allowedTools` rules for Claude,
  e.g. `Bash(tmux:*)` for a live capture), `judge_context` (globs of files the judge reads),
  `judge_reference` (ground-truth files under `fixtures/` shown only to the judge), `assertions`.
- `fixtures/`: binary and multi-line fixtures, plus `gen_fixtures.py`, which writes the screenshot
  ground truth (`screenshot-audit/backupd--normal--80x24.mock`), renders it with the skill's own
  `render_mockup.py` + `ansi_render.py` into `screenshot.png`, records every color of the frame in
  `palette.json`, and writes the build case's design mock. Run it after changing those designs or the
  renderer; `--check` (also a unit test) fails when the committed files are stale.
- `run_behavior_evals.py`: stdlib runner (Python ≥ 3.11). Unit tests (no agent or model calls; the tty probes use a
  private tmux server): `tests/test_behavior_evals.py`, `tests/test_eval_harness.py`, `tests/test_export_results.py`
  and `tests/test_ledger.py`.
- Results: `evals/runs/<dir>/` (gitignored: raw runs hold full agent transcripts). Each holds
  `config.json`, `summary.md`, `summary.json`, and `runs/<case>__<model>__<arm>__r<n>.json` with the final
  answer, tool-call count, files produced, every assertion result, tokens (input / cached / cache write /
  output / reasoning), cost and its basis, wall time, exit status, judge and vision-judge cost. Next to each:
  `.events.jsonl.gz` (raw agent events, gzipped after the run; readers accept the plain `.jsonl` of older
  runs), `.stderr.txt`, and `.files/` (the workdir minus the skill copy), so a run can be re-graded without
  calling the agent again.

| Case | Area | Guards against |
|---|---|---|
| `plugin-caps-from-code` (es) | host | designing a tmux-popup plugin with the 8 colors the code uses instead of asking/measuring what the host draws |
| `host-verify-tools` (es) | host | trusting that a host panel passes ctrl+enter, alt+arrows, italic and 24-bit color instead of having the user run `test_card.py` and `key_probe.py` inside it |
| `sketch-80x24` | frames | hand-typed sketches off the grid; a frame labelled 80x24 that is not |
| `floor-60-split` | frames | no 80×24 / 60-column frames; no "which pane wins" or minimum size |
| `fix-broken-mock` | frames | a frame that fails `--check`; "fixing" a caps violation by loosening the profile |
| `review-clutter-floor` | review | clutter described instead of counted; no 80×24 / 60-column floor answer; recommendation buried |
| `quick-review-host-plugin` (es) | review | quick review without "what each suggestion requires" or host-constraint questions; writing files when told not to |
| `redesign-three-concepts` (es) | ambition | a redesign that is "the same table, improved"; dropping what works; invented package data |
| `craft-rubric-redesign` | ambition | a shipped frame that looks dull: rendered to PNG and scored by a vision judge on the visual-craft rubric C1–C8 (≥ 12/16, no 0, at the caps depth and 16 colors); unwaived `craft CRn` warnings |
| `real-vs-invented-data` | data | invented values (a "triggered by" column absent from the data) presented as real |
| `gruvbox-roles-16` (es) | color | invented hex values; colors not tied to roles; no concrete 16-color answer |
| `theme-export-textual` | color | a hand-made theme mixing invented or cross-scheme hexes; a scheme that fails contrast at 16 colors (`contrast_check.py` run by the grader on the matched theme) |
| `footer-keys-macos` | keys | F-key-only actions on macOS; unconfirmed batch/destructive actions |
| `editor-handoff-bubbletea` | lifecycle | running `$EDITOR` inside `Update` instead of `tea.ExecProcess`; no reload after the editor returns |
| `sigterm-restore` | lifecycle | SIGTERM leaving the terminal raw and on the alternate screen, or "fixed" with exit 0 instead of 143 (executed: `kill -TERM` in a private tmux pane, then `stty -a`) |
| `shell-contract-cli` | shell | a traceback on `| head -1`, escape codes in a redirected file, exit 0 on Ctrl-C, a picker that draws on stdout, usage errors on stdout with 1 (all executed) |
| `screenshot-audit` | audit | judging a screenshot before describing it; colors invented instead of sampled (every hex must be within 30 RGB of the ground-truth palette); a description that does not match the ground-truth mock |
| `live-capture-audit` (es) | audit | auditing a running curses app by reading its code instead of capturing it (the table is cut at 80 columns, 5 of 14 jobs are hidden: only a capture shows it) |
| `build-textual-from-mock` | build | a Textual build that cannot print a headless frame or drifts from the design (`compare.py` cell diff ≤ 25 % text cells); skipped when Textual is not in the uv cache |
| `picker-startup-budget` (wave2) | build | choosing Ink for a 50×/day picker without a ≤ 100 ms startup budget or a measurement |
| `profile-slow-render` (es, wave2) | build | improvising instead of a profiler recipe (`py-spy --idle` from another terminal) for a slow Textual DataTable |
| `inline-picker-branch` (es) | archetypes | a `$(picker)` that uses the alternate screen, draws on stdout or exits 0 on cancel (executed) |
| `chat-session-design` (wave2) | archetypes | an agent-session screen without input box, streaming and approval states, or an inline-vs-alt-screen decision |
| `settings-screen` (es, wave2) | archetypes | settings without validation timing, required-field marking, persistence model, Esc on unsaved changes |

Cases with `depends_on: wave2` specify topics other references are adding (chat archetype, settings
screens, startup budget, profiling); they may fail until those land. Filter them with `--exclude-tag wave2`.

**Tags.** `--tag` / `--exclude-tag` (comma-separated, repeatable) match a case's explicit `tags`, its `area`,
its `depends_on` value, and derived tags: `executed` (has exec / tty_probe / frame_match), `tmux` (has a
tty_probe), `vision` (has vision_rubric), `judge`, `fixture-files` (has a `src` fixture). Examples:
`--tag shell,lifecycle`, `--tag executed --exclude-tag tmux`, `--exclude-tag wave2,vision`.

### Assertions

Boolean, four kinds; each kind runs in its own phase.

**Program** assertions are checked by code on the workdir and the final answer: `answer_regex` (min/max
matches), `answer_box_widths` (every fenced box sketch has rows of one display width), `file_glob`,
`file_regex` (`any` / `all` / `none` of the matching files), `files_contain` (strings in files the agent
wrote), `mock_lint` (the skill's own `render_mockup.py --check`, 0 errors), `mock_craft` (no unwaived
`craft CRn` warning in that `--check`), `mock_caps` (forbidden `#! caps:` values such as `source=code`),
`mock_variants` (distinct concept prefixes), `hex_known` (every hex in the answer/files exists in the named
scheme files; `min_used`, `same_source` = all from one theme file, `contrast` = that theme passes
`contrast_check.py` at truecolor and 16 colors), `hex_near` (every hex reported is within `max_dist` RGB of a
ground-truth palette in `fixtures/`), `transcript_regex` (a pattern over the agent's tool calls, e.g. it ran
`capture_tui.sh` or `capture-pane`), `fixture_unchanged`, `no_new_files`.

**Executed** assertions run commands on the agent's output after the run, in a scratch copy of the workdir
(never in the results), with a fresh `HOME`, `TMUX` unset and a private `TMUX_TMPDIR`, `uv` offline on the
real cache, outbound network denied by `sandbox-exec` on macOS (`EVAL_NO_SANDBOX=1` disables it), and a
timeout each. In case order, sharing one copy:
- `exec`: `bash -o pipefail -c CMD` with stdin `/dev/null` (stdout is never a TTY); checks `expect_exit`,
  `stdout_regex` / `stdout_not_regex` / `stderr_regex` / `stderr_not_regex`, and `files` (`exists`, `regex`,
  `not_regex`, `min_lines`, `max_lines`). `skip_unless: CMD` grades it as missing when the requirement fails.
- `tty_probe`: CMD in a pane of a private server (`tmux -L evalprobe-<rand> -f /dev/null`, only that server
  is ever killed), wrapped by a probe that records the exit status (128+N for a signal) and `stty -a` after
  the app exits. Waits for `ready` (regex on the screen), sends `actions` (`keys` as tmux key names, `text`,
  or `signal` to the app's pid), then checks `expect_status`, `stty_restored` (icanon echo isig back on),
  `alt_screen_during`, `alt_screen_after`, `files`.
- `frame_match`: the skill's `compare.py MOCK FRAME`; pass when at most `max_text_pct` % (default 20) of the
  text cells differ.

**Judge** assertions are yes/no questions answered in one call per run by a judge model that reads the
request, the final answer, the file list, the files in `judge_context` and the `judge_reference` ground
truth; keep them few and crisp. **Vision** assertions (`vision_rubric`) render the agent's chosen `.mock`
frame (`prefer`, default `--normal--`, largest size; `max_frames`) to PNG with the skill's
`render_mockup.py` + `ansi_render.py` at each of `depths` (default the caps depth and 16 colors), then a
Claude vision judge (`--vision-judge`, default `[judges] vision` = `sonnet`, `--tools Read` limited to that image directory)
scores every image C1–C8 with the rubric text read from `references/visual-craft.md`; pass = every image
≥ `min_total` (12) with no 0. An assertion that cannot be graded (judge failure, a skipped requirement)
counts as missing, not as a fail.

`neutral: false` marks assertions on the skill's own artifact format or scripts (`.mock` frames, `#! caps:`,
`test_card.py`), which a baseline cannot know about. `summary.md` reports the pass rate with all assertions
and the delta on neutral ones only; quote the neutral delta when claiming the skill changes behavior, not
just format. It has one table per **skill area** (host, frames, review, ambition, data, color, keys,
lifecycle, shell, audit, build, archetypes), one per case, one per assertion, the spend, and the skipped
and errored runs.

### Configuration

The runner is configured by data, so models, adapters, cases, judges and repetitions change without editing
Python. It needs **Python ≥ 3.11** (`tomllib` reads `models.toml`); everything else is the standard library.

| File | Holds |
|---|---|
| `models.toml` | every model (adapter, CLI model string, default effort, cost basis, prices, optional timeout, flags, env, label), named **presets** (`frontier4` = the four models of the published comparison, `smoke`, `cheap`), the default `--models`, the text and vision **judges**, and each adapter's isolation settings (`[adapters.<name>]`) |
| `behavior-evals.json` + `cases/*.json` | the cases (schema below); `--cases-dir` points elsewhere |
| `adapters/*.py` (optional) | Python adapters for CLIs that need a real event parser (see Extending) |
| `prices-cache.json` (generated) | OpenRouter prices fetched by `--refresh-prices`; only the `--dry-run` estimator reads it |
| `examples/echo_agent.py` | an offline fake agent wired as the `example-echo` model: the `command` adapter's reference and test fixture |

`--models` takes presets, model ids and `ID@EFFORT` (`--models frontier4`, `--models smoke,opus@high`,
`--models cheap@low`); an unknown id fails with the list of known ones. `--list-models` prints the table.
Without `--models` the runner uses `[defaults] models` (`frontier4`), and the judges default to `[judges]`
(`haiku` text, `sonnet` vision), so a dry run of `frontier4` is 192 jobs.
Paths: `--skill-dir` (default `skills/tui-design/` next to `evals/`, or `$EVAL_SKILL_DIR`) and `--results-root`
(default `evals/runs/`, or `$EVAL_RESULTS_ROOT`).

### Case schema

```json
{"cases": [{
  "id": "queue-80x24",
  "lang": "en",
  "area": "frames",
  "source": "why this case exists",
  "prompt": "Sketch the queue screen of backupd at 80x24 and save it as a .mock frame.",
  "fixtures": [{"path": "queue.json", "src": "queue/queue.json"}],
  "assertions": [
    {"id": "has-frame", "type": "file_glob", "glob": "**/*.mock", "neutral": false},
    {"id": "says-size", "type": "answer_regex", "pattern": "80\\s*[x×]\\s*24"},
    {"id": "names-floor", "type": "judge", "question": "Does the answer say what hides first below 80 columns?"}
  ]
}]}
```

A file under `cases/` may also be a bare list of cases. Fields: `id` (unique across all files), `prompt`,
`area` (one of the default areas, or one a file declares in a top-level `areas` list), `assertions`
(non-empty), and optionally `lang`, `source`, `tags`, `depends_on`, `fixtures` (each `path` plus exactly one of
`lines`, `content`, or `src` = a file under `fixtures/`), `requires` (`[{cmd, why}]`: when a check fails the
run is skipped, not failed), `claude_tools` (extra `--allowedTools` rules for Claude), `judge_context` (globs of
files the judge reads), `judge_reference` (ground truth under `fixtures/`, shown only to the judge), `timeout`
(seconds; wins over the model's and `--timeout`), `serial: true` (run alone even under `--jobs N`; for signal
or process-sensitive cases such as `sigterm-restore` and `live-capture-audit`). The literal `{run}` in any string
of a case (fixture paths, prompt, assertions) becomes a per-run token, for a fixture name that must be unique
per run (`watch-{run}.py`). The shipped cases keep fixed names on purpose: the name is part of the prompt the
agent reads, and renaming changes their `case_hash`. Signal cases are
`serial` instead. `serial` is left out of `case_hash` (it changes scheduling only).

A top-level `banned_terms` list enforces the neutral-domain rule: `--validate-cases` fails a case whose JSON or
text fixtures contain one. `--validate-cases` checks
every file (ids unique, assertion types and required keys, regexes compile, fixtures and palettes exist, the
banned terms) and exits 1 on any error, naming the file of each problem.

| Assertion type | Required keys | Optional keys |
|---|---|---|
| `answer_regex` | `pattern` | `min` (1), `max` |
| `transcript_regex` | `pattern` (over the agent's tool calls) | `min`, `max` |
| `answer_box_widths` | — | `max_width` |
| `file_glob` | `glob` | `min`, `max`, `produced_only` (true) |
| `file_regex` | `glob`, `pattern` | `mode` any / all / none |
| `files_contain` | `strings` | `glob`, `min_distinct` (1) |
| `fixture_unchanged` | `path` | — |
| `no_new_files` | — | — |
| `mock_lint` | `glob` | `min_files`, `max_errors` (0) |
| `mock_craft` | `glob` | `min_files` |
| `mock_caps` | `glob` | `forbid` (`{key: [values]}`), `require_line` (true) |
| `mock_variants` | `glob` | `min` (3) |
| `hex_known` | `sources` (globs in the skill) | `scope`, `files_glob`, `min_used`, `same_source`, `contrast` |
| `hex_near` | `palette` (under `fixtures/`) | `scope`, `files_glob`, `max_dist` (30), `min_hex` |
| `exec` | `cmd` | `expect_exit` ([0]), `stdout_regex`, `stdout_not_regex`, `stderr_regex`, `stderr_not_regex`, `files`, `timeout`, `skip_unless` |
| `tty_probe` | `cmd` | `size`, `ready`, `actions`, `expect_status`, `stty_restored`, `alt_screen_during`, `alt_screen_after`, `files`, `skip_unless` |
| `frame_match` | `mock`, `frame` | `max_text_pct` (20), `max_any_pct` |
| `judge` | `question` | — |
| `vision_rubric` | `glob` | `prefer`, `max_frames`, `depths`, `min_total` (12) |

Every assertion takes `id` (unique in its case), `type`, `neutral` (default true) and `desc`. What each one
checks is described under Assertions above. A new assertion *type* needs Python (`check_program` or the
executed / judge phases in `run_behavior_evals.py` plus `ASSERTION_TYPES`); new cases never do.

### Isolation per adapter

One run = (case, model, arm, rep) in a fresh temp dir (`<tmp>/evalrun-*/project`, a neutral path). Arm `skill`
copies the skill there without `__pycache__/`; arm `baseline` does not. The prompt is written to
`<tmp>/evalrun-*/prompt.txt` (outside the workdir) and reaches the agent on stdin, never in argv: a
`pkill -f` on a word from the prompt kills every process whose command line holds that word, including concurrent
agents carrying it in their prompt. Every agent runs with an **allow-listed environment** built from
scratch: `PATH`, locale (`LANG`, `LC_*`), `TERM`, `USER`, `LOGNAME`, `SHELL`, `TZ`, a `HOME`, `TMPDIR` and
`TMUX_TMPDIR=<workdir>/.tmp`, plus only the adapter's own variables. Nothing else of the orchestrator's
environment reaches it (no API key, no `TMUX`, no Claude Code session variables), so any tmux it starts gets a
server inside the run's temp dir, which the runner kills afterwards.

| Adapter | Skill path | Prompt | Isolation (settings in `[adapters.<name>]`) |
|---|---|---|---|
| `omp` | `.agents/skills/<skill>` | stdin from the prompt file (omp reads piped stdin as the message; `@file` would wrap it in a `<file>` block) | `omp --profile tui-design-evals -p --no-session --no-rules --no-extensions --mode json --model M --thinking T --skills=<skill>` (baseline `--no-skills`). The OpenRouter key lives in that omp profile's vault, never in argv or the environment. HOME stays real (omp finds its profiles under `~/.omp`). Reads are confined (below). The skill arm gets `--append-system-prompt <tmp>/skill-hint.md` naming the skill folder (omp's `skill://` URLs carry no path, so agents searched with `find /`). Cost = sum of `usage.cost.total` over assistant `message_end` events (billed); streamed for `--max-usd` |
| `claude` | `.claude/skills/<skill>` | stdin (`claude -p` with no prompt argument) | `CLAUDE_CONFIG_DIR=~/.claude-eval claude -p --model M --effort E --output-format stream-json --verbose --no-session-persistence --strict-mcp-config --permission-mode acceptEdits --allowedTools 'Bash(python3:*)' 'Bash(uv run:*)'`. HOME stays real (Claude Code finds its login in the keychain through HOME). Reads are confined. Cost: the `result` event's `total_cost_usd` (API-equivalent) |
| `codex` | `.agents/skills/<skill>` (workdir `git init`ed) | stdin (`codex exec … -`) | `CODEX_HOME=~/.codex-eval HOME=<fresh empty dir> TMPDIR=<workdir>/.tmp codex exec --json --skip-git-repo-check --ephemeral --sandbox workspace-write -c approval_policy=never -c sandbox_workspace_write.exclude_slash_tmp=true -c sandbox_workspace_write.exclude_tmpdir_env_var=true --disable plugins --disable remote_plugin --disable apps -m M -c model_reasoning_effort=E -C <workdir> -`. Equivalent cost from the `price` in `models.toml` (reasoning is inside `output_tokens`) |
| `command` | `skill_path` (default `.agents/skills`) | `{prompt_file}` argument or stdin (`prompt_via`) | the argv template of the model; HOME is a fresh dir; see Extending |

**Read confinement** (`confine_reads`, on for omp and claude): on macOS the agent runs under `sandbox-exec`
with a profile that denies reading or writing the project checkout (the first ancestor of `evals/` holding
`.git`), the source skill, `evals/`, the results root and the evals env file
(`~/.config/tui-design-evals/`), while the run's temp dir stays allowed. The checkout is denied because
`evals/` holds every case's checks. `EVAL_NO_SANDBOX=1` turns it off. Limits: other OSes get no
confinement (the agent can read anything the user can); codex keeps it off because it sandboxes its own commands
with seatbelt and a nested `sandbox-exec` fails, so a codex agent can still read absolute paths (its HOME is
empty, and the workdir path gives no hint of the checkout); the CLI's own login stays readable by its agent
(`~/.omp/profiles/<name>`, `~/.claude-eval`, `~/.codex-eval/auth.json`): that is a known exposure of running an
agent CLI at all.

The `[sandbox]` table of `models.toml` extends the profile: `deny_read` lists more paths an agent may not read
(default: your own `~/.claude/skills` and `~/.agents/skills`), and `deny_spotlight = true` (the default) cuts off
Spotlight, so `mdfind` finds nothing. Machine-local paths, such as another checkout or a working copy holding an
older skill and old results, go in `EVAL_DENY_READ` (`os.pathsep`-separated, in the environment or the evals env
file) instead of the shared file. A profile that denies only the checkout still leaves those paths readable.

**Contamination check.** After each run the runner reads the agent's tool calls. The run is marked
`error: contaminated: …`, with the paths in a `contamination` list, when the agent:

- reached a path outside its own temp dir through a directory named after the skill (another copy of it, old
  results);
- reached a path under a `deny_read` entry;
- ran a whole-disk search (`mdfind`, `mdls`, `locate`).

The check also works where there is no sandbox (codex, other OSes). A contaminated run is excluded from pass rates
like any error, and `--resume` runs it again. `--scan-contamination DIR` applies the same check to the saved runs
of an older results dir and marks the hits, without calling any agent.

**Secrets, defense in depth.** Before anything is written (events `.jsonl.gz`, stderr, the run JSON with the
final answer, files copied from the workdir), the value of every variable whose name contains KEY, TOKEN,
SECRET, PASSWORD or CREDENTIAL (8+ characters), from the orchestrator's environment and from the evals env file,
is replaced with `<redacted:NAME>`; the exporter strips the same values from every request body. After each run a
**leak scan** reads that run's artifacts (gzip included): a secret that reached them (even redacted on the way)
marks the run `error: secret leak …` with a `secret_leak` block, skips its judges, and stops the campaign (exit
code 3). A model's `env` table may reference `${VAR}`; that is an explicit choice to expose that variable to
the agent, and the run record stores the template, not the value.

**Separate logins for Claude Code and Codex (one-time setup).** The claude and codex adapters run the CLIs
against dedicated config dirs so your own skills, plugins, hooks and memory never reach an agent under test:
log in once with `CLAUDE_CONFIG_DIR="$HOME/.claude-eval" claude` (then `/login`) and
`CODEX_HOME="$HOME/.codex-eval" codex login`; check them before a campaign with
`CLAUDE_CONFIG_DIR="$HOME/.claude-eval" claude auth status` and `CODEX_HOME="$HOME/.codex-eval" codex login status`.
The paths are settings (`[adapters.claude] config_dir`, `[adapters.codex] codex_home`).

**omp profile for the evals (one-time setup).** The omp adapter uses `omp --profile tui-design-evals` (change
it with `[adapters.omp] profile`). Create the profile and store the OpenRouter key in its vault once, with
omp's own login flow: run `omp --profile tui-design-evals`, log in to OpenRouter with the key meant for evals,
then quit. Check it with `echo 'Reply with OK.' | omp --profile tui-design-evals -p --no-tools --model
z-ai/glm-5.3-flash`. Until the profile exists the runner refuses omp models before starting. The key
never goes in argv (visible in `ps`) or in the agent's environment (an agent that runs `env` would record it).

Permissions: Claude gets `acceptEdits` (writes inside the workdir) plus Bash for `python3` and `uv run` only;
read-only shell commands are allowed by default and anything else (network, other binaries) is denied in `-p`
mode. Codex gets `workspace-write` with `/tmp` and `$TMPDIR` excluded (TMPDIR points into the workdir so
Python's `tempfile` still works) and never asks for approval. Executed assertions get the same allow-listed
environment (fresh HOME, private TMUX_TMPDIR, uv offline) and no network.

Isolation findings (2026-10-02): `~/.codex-eval` still loads OpenAI's curated remote plugins, including
a `superpowers` skill that announced itself in a probe run; `--disable plugins --disable remote_plugin
--disable apps` removes them and project skills still load. `~/.claude-eval` still connects the
claude.ai MCP connectors (Figma, Drive…), so `--strict-mcp-config` drops them; Claude Code's built-in
skills (`design`, `dataviz`…) stay in both arms. Codex writes a `trust_level` entry per workdir into
`~/.codex-eval/config.toml` (that is the CLI's own doing).

Judges get their prompt from a private temp file on stdin and the same allow-listed environment. Text judge:
`[judges] text` (`haiku`) through the isolated Claude profile with `--tools ""` (about $0.02-0.03 per run,
API-equivalent); an omp model works too (`--judge z-ai/glm-5.3-flash`), recorded in each run's `judge` block.
Vision judge: `[judges] vision` (`sonnet`), `--tools Read` in a temp dir holding only the rendered PNGs (about
$0.05 per scored frame pair). On the smoke frame haiku gave 16/16 and missed two half-empty boxes; sonnet gave
8/16 with C1 = 0 for the same image at the same cost.

**Run identity.** Every run JSON carries `identity` (case_id, case_hash, model, provider, adapter,
adapter_version from `<cli> --version`, effort, skill_hash = sha256 over the installed skill copy or null for
the baseline, judge, vision_judge, arm, rep), `run_key` = sha256 of its canonical JSON, and `experiment_key` =
the same without case_id, case_hash and rep ("this model + config + skill version + arm"). `case_hash` covers
the case's canonical JSON (minus `serial`) plus the bytes of its `src` fixtures and `judge_reference` files.
`run_id` stays the resume key. `dataset.json` in each results dir lists every case (id, hash, area, tags,
prompt, fixtures with sha256, assertions with their questions): what an exporter uploads as dataset items.
After `--regrade` a run also records `graded_case_hash` (its `identity` keeps the case the agent actually ran).
Files the agent copied verbatim from the skill (status `skill-copy`) are ignored by every assertion and not
saved in `.files/`.

### Run

```bash
python3 evals/run_behavior_evals.py --list-models                     # models, presets, judges, prices
python3 evals/run_behavior_evals.py --validate-cases                  # schema + neutral-domain check
python3 evals/run_behavior_evals.py --dry-run --reps 3                # matrix + cost estimate, no calls
python3 evals/run_behavior_evals.py --cases review-clutter-floor,real-vs-invented-data \
    --models smoke --budget-basis billed --max-usd 1                  # smoke
python3 evals/run_behavior_evals.py --tag executed --exclude-tag wave2 --models smoke --max-usd 1
python3 evals/run_behavior_evals.py --models z-ai/glm-5.3,opus --reps 3 --max-usd 40 --jobs 2
python3 evals/run_behavior_evals.py --regrade evals/runs/<dir> [--rejudge] [--no-exec]
python3 evals/fixtures/gen_fixtures.py [--check]                      # regenerate the screenshot fixture
```

Options: `--cases ID,ID`, `--cases-file`, `--cases-dir DIR`, `--validate-cases`, `--tag T,T` / `--exclude-tag
T,T` (repeatable), `--models-file`, `--list-models`, `--models` (presets, ids, `ID@EFFORT`), `--arms
skill,baseline`, `--reps N`, `--judge MODEL`, `--vision-judge MODEL` (a Claude model), `--no-judge`,
`--no-exec` (live: executed assertions graded as missing; with `--regrade`: earlier executed results kept),
`--dry-run` (with `--estimate-from DIR`, repeatable, default the newest results dir), `--list-jobs` (every run
id and effort), `--refresh-prices`, `--max-usd X`, `--budget-basis all|billed`, `--skill-dir`, `--results-root`,
`--out DIR`, `--timeout` (seconds per run, default 900; a case's `timeout`, then a model's, win: Qwen3.8 Max
sets `timeout = 2400` in `models.toml`, the others use the default), `--jobs N`
(serial cases still run alone), `--keep-workdirs`, `--resume DIR` (keeps clean runs; failed, skipped and
missing ones run again; a larger `--reps` adds only the new repetitions), `--stop-after-errors N`, `--regrade
DIR [--rejudge]`.

`--regrade` re-checks static assertions on the saved `.files/`, re-runs executed ones in a scratch copy, and
keeps the earlier text and vision verdicts unless `--rejudge`. `--dry-run` estimates from **median** token
counts per case and arm (one runaway loop does not move it) and prints the p90 tail separately: `median`
applies the median cache share, `med/nocache` bills every input token, `p90/nocache` is the planning ceiling.
With more than one repetition `summary.md` adds a "Spread across repetitions" table (per case and model: min–max
pass rate and standard deviation per arm), and `summary.json` carries `rate_min`, `rate_max`, `rate_sd` per cell.

`--max-usd` is a hard stop on agent + judge spend of every basis (billed, API-equivalent and equivalent
alike; `--budget-basis billed` counts only billed USD): no run starts once it is reached, and a live omp run
is killed as soon as its streamed cost crosses it (Claude and Codex report cost only at the end, so one run can
overshoot). A killed run is reported as errored and excluded from pass rates.

### Interpreting results

- Use ≥ 3 reps before reading a delta; agent behavior is stochastic and one run per arm is a plumbing check.
- A case where both arms pass is not a win; a case where both fail points at a gap in the skill (or a too
  strict assertion: open the run's `.files/` and answer before changing either).
- `skill loaded` in the table counts skill-arm runs that actually opened the skill; a skill-arm run that
  never loaded it is a trigger miss, which the trigger evals measure. A baseline with `skill loaded > 0` is
  contaminated and must be discarded.
- When an assertion is mis-graded, fix it in `behavior-evals.json` and re-grade the saved runs with
  `--regrade` instead of re-running the agents.

## Extending

Everything below is data: no Python edit, except a new assertion type or a CLI whose output needs a real parser.

**Add a model.** Append a table to `models.toml`; its `id` is what `--models` takes and what every run records
(run ids, identity, summaries), so keep it stable once it has results.

```toml
[[models]]
id = "moonshotai/kimi-k3"         # omp passes `model` (default: id) to --model
adapter = "omp"
effort = "medium"                 # default; override per run with moonshotai/kimi-k3@high; "none" omits the flag
cost_basis = "billed"             # billed | api-equivalent | equivalent | unknown
price = { input = 0.60, cached_input = 0.15, output = 2.50 }   # USD per million tokens
openrouter_id = "moonshotai/kimi-k3"   # for --refresh-prices
timeout = 1800                    # optional, seconds (a case's own timeout still wins)
label = "Kimi K3 (OpenRouter)"
```

Optional: `flags = ["--some-cli-flag"]` (appended to the adapter's command), `env = { FOO = "bar" }`
(placeholders `{home}` `{workdir}` `{run_dir}`; `${VAR}` takes a value from your environment, which then
reaches the agent, so never point it at a secret), `provider` (recorded in the identity). `--list-models`
checks the file; any unknown key or bad value fails with every problem listed.

**Add a preset.** `[presets] mine = ["moonshotai/kimi-k3", "opus@high"]`, then `--models mine` (or
`--models mine@low` to set every member's effort). To change what a bare command runs, set `[defaults] models`.

**Plug in any agent CLI (the `command` adapter).** The contract:

- `command`: the argv template. Placeholders: `{prompt_file}` (the prompt, a file outside the workdir),
  `{workdir}` (the agent's cwd, with the fixtures), `{model}`, `{effort}`, `{skill_dir}` (the installed skill
  in the skill arm, empty in the baseline), `{home}` (a fresh HOME), `{run_dir}` (the run's private temp dir,
  outside the workdir: put answer and usage files there), `{arm}`, `{evals_dir}`.
- `prompt_via = "arg"` (the template carries `{prompt_file}`) or `"stdin"` (the prompt file is fed on stdin).
  The prompt itself never goes in argv.
- `answer = "stdout"` (all of stdout is the final answer) or a path template (`"{run_dir}/answer.md"`).
- `usage` (optional): a path template of a JSON object `{input, cached, cache_write, output, reasoning,
  cost_usd}`. With `cost_usd` the run's cost is that number (basis: the model's `cost_basis`, default billed);
  with tokens only and a `price`, an equivalent cost; without usage, tokens are null and the basis is `unknown`.
- `skill_path` (where the skill arm installs the skill, default `.agents/skills`), `skill_args` /
  `baseline_args` (appended per arm), `version_command` (recorded as `adapter_version`).
- The process gets the allow-listed environment, a fresh HOME and the run's timeout; a non-zero exit is an
  error; tool calls and `skill_loaded` are unknown (null), so `transcript_regex` cannot match.

```toml
[[models]]
id = "my-agent"
adapter = "command"
model = "my-model-2"
effort = "medium"
command = ["my-agent", "run", "--model", "{model}", "--effort", "{effort}", "--prompt-file", "{prompt_file}",
           "--cwd", "{workdir}", "--final-answer", "{run_dir}/answer.md", "--usage-json", "{run_dir}/usage.json"]
prompt_via = "arg"
answer = "{run_dir}/answer.md"
usage = "{run_dir}/usage.json"
skill_args = ["--skills-dir", "{workdir}/.agents/skills"]
baseline_args = ["--no-skills"]
version_command = ["my-agent", "--version"]
```

Try the plumbing offline first: `--models example-echo --no-judge --cases sketch-80x24 --arms skill` runs the
fake agent in `examples/echo_agent.py` through the whole pipeline at zero cost. Settings shared by all command
models (`home`, `confine_reads`, `pass_env`) go under `[adapters.command]`.

**Write a Python adapter** when a CLI streams events you want parsed (tool calls, tokens, live cost). Drop a file
in `evals/adapters/`; the runner executes every `*.py` there with `Adapter`, `Invocation`, `register_adapter`,
`ModelSpec`, `parse_lines`, `empty_tokens`, `model_env`, `fill`, `skill_hit` and `price_cost` in its globals:

```python
class MyCli(Adapter):
    name, provider, executable = "mycli", "acme", "mycli"
    skill_rel = ".agents/skills"            # where the skill arm installs the skill
    default_cost_basis = "equivalent"
    defaults = {"config_dir": "~/.mycli-eval"}   # [adapters.mycli] keys (plus home, confine_reads, pass_env)

    def command(self, spec, effort, arm, prompt_file, workdir, home, extra_tools=None, run_dir=None):
        argv = ["mycli", "exec", "--json", "--model", spec.model, "--effort", effort, *spec.flags]
        env = {"MYCLI_HOME": self.setting("config_dir")}
        return Invocation(self.wrap(argv, run_dir), env, prompt_file)   # prompt on stdin, never in argv

    def parse(self, lines, spec=None, place=None):
        r = {"final_answer": "", "tool_calls": 0, "tokens": empty_tokens(), "cost_usd": 0.0,
             "cost_basis": self.default_cost_basis, "skill_loaded": False, "error": None}
        for e in parse_lines(lines):        # JSON lines of stdout, secrets already redacted
            ...                             # fill final_answer, tool_calls, tokens, skill_loaded (skill_hit(text))
        if spec is not None and spec.price:
            r["cost_usd"] = price_cost(r["tokens"], spec.price)
        return self.finish(r, spec)         # applies the model's cost_basis

    def tool_texts(self, events):           # optional: what transcript_regex matches
        return ""

register_adapter(MyCli())
```

Optional hooks: `judge_command()` (with `supports_judge` / `supports_vision`), `live_cost(line)` (streamed
billed USD for `--max-usd`), `version()`. Then use `adapter = "mycli"` in `models.toml`.

**Add a case.** Write `evals/cases/<topic>.json` (a list of cases or `{"cases": [...]}`; see Case schema for
the fields and assertion types), put any `src` fixture under `fixtures/`, then
`python3 run_behavior_evals.py --validate-cases` and a smoke: `--cases <id> --models smoke --arms skill,baseline`.
Keep domains neutral (the banned terms), prefer a few crisp judge questions, give each new executed check a
positive and a negative control in the unit tests, and mark a case `serial: true` if it sends signals or kills
processes by name.

**Change repetitions.** `--reps 3`. To add repetitions to an existing results dir, re-run the same command with
the larger `--reps` and `--resume <dir>`: finished runs are kept and only the new repetitions run. With more than
one repetition the summary reports the spread per case.

**Change judges.** `[judges] text` / `vision` in `models.toml` (any model id whose adapter supports it: claude
or omp for text, claude for vision), or per run `--judge` / `--vision-judge`; `ID@EFFORT` is accepted. The judge
is part of each run's identity, so a different judge starts new experiments in the exporters.

**Refresh prices.** `python3 run_behavior_evals.py --refresh-prices` fetches OpenRouter's public
`/api/v1/models` (no key is sent) for every model with an `openrouter_id` and writes `prices-cache.json`; the
`--dry-run` estimator then uses those prices (marked `*` in `--list-models`). Recorded run costs keep using the
reviewed `price` in `models.toml`; copy a new price there when you accept it.

**Export targets.** `python3 export_results.py RESULTS_DIR` exports to the platforms in `EVAL_EXPORT_TO`
(environment or `~/.config/tui-design-evals/env`, e.g. `"langfuse,phoenix"`); `--to phoenix` overrides per
export. It reads `cases/*.json` next to `behavior-evals.json` for older dirs without `dataset.json`, and strips
every known secret value from request bodies. See "Export to Langfuse / Phoenix" below.

**Ledger.** After a campaign (and after each resume or `--regrade`): `python3 evals/ledger.py evals/runs/<dir>
--label "…"` upserts one record into `evals/ledger.jsonl` (or `$EVAL_LEDGER`, or `--ledger PATH`): models and
effort, pass rates per model and area, cost by basis, and the hashes of the skill, the case set
(`behavior-evals.json` plus `cases/*.json`), the runner and `models.toml`. Records hold no absolute paths or
hosts. `python3 evals/ledger.py --list` prints them. The published interpretation is
[docs/evals.md](../docs/evals.md).

## Export to Langfuse / Phoenix

`evals/export_results.py` uploads a results dir to [Langfuse](https://langfuse.com) and/or
[Arize Phoenix](https://phoenix.arize.com) (self-hosted or cloud) as a dataset plus experiments, with one score
per assertion. Standard library only. Re-running it on the same dir updates in place and creates no duplicates.

```bash
python3 evals/export_results.py evals/runs/<dir> --to langfuse,phoenix --dry-run    # plan only: no network
python3 evals/export_results.py evals/runs/<dir> --to langfuse,phoenix --verify     # export, then count remote objects
python3 evals/export_results.py evals/runs/<dir> --to phoenix --verify --no-export  # count only
python3 evals/export_results.py evals/runs/<dir> --prune --verify                   # recreate experiments with stale runs
```

A re-export updates runs in place, but neither platform can delete one run of an experiment. When a results
dir loses a run (a contaminated run re-run under a newer CLI version, or an assertion that is no longer graded),
the export warns that some experiments hold runs that are gone. `--prune` deletes those experiments of this dir
(the Phoenix experiment; the Langfuse dataset run and the traces of the stale runs) and exports them again from the
current runs. Langfuse ingests asynchronously, so a count right after a prune can lag for a minute.

Credentials come from the environment or from `~/.config/tui-design-evals/env` (`KEY="value"` lines; the
environment wins): `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL`, `PHOENIX_BASE_URL`,
`PHOENIX_API_KEY`, and optionally `EVAL_EXPORT_TO` (default targets when `--to` is omitted). The script never
prints or writes a key, redacts error messages, verifies TLS (it offers `--insecure` only when verification
fails), and strips every known secret value from request bodies.

| Object | One per | Name |
|---|---|---|
| dataset | case set | `tui-design-behavior` (`--dataset-name`) |
| item / example | case version | `tui-design:<case_id>@<case_hash[:12]>`: input = prompt + fixtures, expected output = the assertions |
| experiment | `experiment_key` (model + effort + arm + skill version + judges) | e.g. `opus · medium · skill · <skill_hash[:8]>` |
| run / trace | run record | final answer, produced files, tokens, cost, wall time; errors in `error` |
| scores | graded assertion | assertion id, 1/0, evidence as comment; plus `pass_rate` |

An edited case gets a new item next to the old one, so older runs keep pointing at the case they ran. Errored
runs are uploaded with their error and no pass/fail scores; skipped runs are not exported. The only file the
exporter writes is `<results dir>/export-state.json` (remote ids, no credentials; gitignored). Langfuse traces go
through its OTLP endpoint (`/api/public/otel/v1/traces`); Phoenix examples use stable ids and are only appended,
never replaced. After an export the script prints the dataset, experiment and compare-view URLs of each
platform; the compare view puts the skill and baseline arms side by side per assertion.
