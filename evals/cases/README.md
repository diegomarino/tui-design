# Extra cases

Every `*.json` file here is loaded next to `../behavior-evals.json` (a list of cases, or `{"cases": [...]}`).
Schema, assertion types and the neutral-domain rule: [../README.md](../README.md), "Case schema" and
"Extending". Check a new file with `python3 evals/run_behavior_evals.py --validate-cases`, then smoke it with
`--cases <id> --models smoke --arms skill,baseline`.
