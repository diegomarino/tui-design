# Python adapters

Every `*.py` file here is executed once by `../run_behavior_evals.py` with `Adapter`, `Invocation`,
`register_adapter` and the parsing helpers in its globals, and registers an adapter for a CLI whose event stream
needs a real parser. Most CLIs do not need one: the `command` adapter in `../models.toml` takes an argv
template. Contract and a full example: [../README.md](../README.md), "Extending".
