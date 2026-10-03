# Contributing

Thanks for helping. The skill folder `skills/tui-design/` is the product: the skills CLI treats **any commit
under it** as an update for every user on their next `npx skills update`, so changes there land finished,
tested and linted. Docs, evals, tests and tools live outside it and are never installed.

## Before a pull request

From the repository root (Python 3.11+, standard library only for the tests; `tmux` for the capture tests):

```bash
python3 -m unittest discover -s tests -p 'test_*.py'     # skill scripts, eval harness, docs links; no model calls
bash tests/test_capture.sh                               # live capture through a private tmux server
python3 tools/check_links.py                             # relative links; nothing in the skill links outside it
python3 tools/gen_toc.py                                 # after editing a reference: its Sections line ranges
bash tools/check_public.sh                               # pre-publish check: must print "clean"
python3 evals/run_behavior_evals.py --validate-cases     # if you touched evals/
python3 skills/tui-design/scripts/render_mockup.py path/to/frame.mock --check   # every .mock you touched: 0 errors
```

If a change affects what the docs show, regenerate the images with `uv run tools/make_screenshots.py` and look at
them before committing.

## Rules for the skill folder

- Links inside `skills/tui-design/` are relative and never leave that folder (an installed copy has nothing
  else). Scripts compute paths from their own location, so they work from a copy or a symlink.
- Nothing human-facing goes in it (screenshots, showcases, project docs); that belongs in `docs/`.
- Every tmux command uses a private socket: `tmux -L <name>`. Never `tmux kill-server` without `-L`.
- References are read by line range: after editing one, run `python3 tools/gen_toc.py` to regenerate its
  **Sections** list (`tests/test_toc.py` fails on stale ranges); a new `##` heading needs its "read this when" text.

## How to

[docs/contributing/architecture.md](docs/contributing/architecture.md) explains how the scripts fit together and
how to add a [theme](docs/contributing/architecture.md#add-a-theme), a
[framework](docs/contributing/architecture.md#add-a-framework), an
[eval case](docs/contributing/architecture.md#add-an-eval-case) or a
[model](docs/contributing/architecture.md#add-a-model).

## Reporting eval results

If you run the evals, add the campaign to `evals/ledger.jsonl` with `python3 evals/ledger.py evals/runs/<dir>
--label "…"` and describe it in the pull request: models and versions, repetitions, judges, cost, and what
changed. Raw runs in `evals/runs/` hold full agent transcripts; never commit them.
