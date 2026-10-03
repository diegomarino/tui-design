# CLI contract: where a TUI meets the shell

**Sections** — read only the line range you need (`sed -n 'START,ENDp'` on this file, or Read with offset/limit):
- [1. Exit codes](#1-exit-codes) · L20–56 — choosing exit codes (0/1/2/130/143…).
- [2. Signals](#2-signals) · L58–79 — Ctrl-C, SIGTERM, SIGPIPE and `app | head`.
- [3. TTY checks and streams](#3-tty-checks-and-streams) · L81–106 — what goes to stdout, stderr and `/dev/tty`.
- [4. Progress, paging and color: only on a TTY](#4-progress-paging-and-color-only-on-a-tty) · L108–117 — spinners, pagers and colour when piped.
- [5. Machine output](#5-machine-output) · L119–127 — `--json` and NDJSON.
- [6. Error messages](#6-error-messages) · L129–147 — wording and placement of errors.
- [7. Shell integration for pickers and file managers](#7-shell-integration-for-pickers-and-file-managers) · L149–158 — cd on exit, `init` scripts, key bindings.
- [8. Checklist (`SH-` ids)](#8-checklist-sh--ids) · L160–182 — reviewing the shell contract (SH-*).
- [Source index](#source-index) · L184–206 — resolving a source key.

Read this when a TUI, an inline picker or an interactive CLI has to behave inside the shell: exit codes, Ctrl-C and other signals, `app | head`, TTY checks on stdin and stdout, progress and paging, `--json`, error messages, and shell integration (cd on exit, `init` scripts, completions). **Out of scope:** general CLI argument design (flag naming, subcommand trees, help text); see [clig].

`derived:` = our inference. `measured:` = run on macOS 26 (zsh, isolated `tmux -L`), 2026-10, with the version named in the row. Source keys resolve in the [index](#source-index) at the end. Terminal restore on every exit path: [lifecycle.md](lifecycle.md) LC1. Examples use three neutral tools: a log tool `logq`, a file picker `pickf` and a deploy CLI `shipit`.

---

## 1. Exit codes

| Code | Meaning | Use it when | Source |
|---|---|---|---|
| **0** | success | the command did what was asked; a picker returned a choice | [bash-exit] |
| **1** | general failure | runtime error; a picker found or chose nothing (fzf, skim "No Match") | [fzf-man], [skim] |
| **2** | usage error | bad flag or argument. Go `flag.ExitOnError` calls `os.Exit(2)`; Python argparse exits 2 (measured); clap `USAGE_CODE = 2`. **Exceptions:** commander.js `error()` defaults to 1; Cobra returns the error and `main` picks the code | [go-flag], [clap-src], [commander-src] |
| 124 | timed out | GNU `timeout`; gum `--timeout` | [gum-exit] |
| 126 / 127 | found but not executable / not found | reserved for the shell; never return them yourself (fzf uses them only for its `become` action) | [bash-exit], [fzf-man] |
| **128+N** | killed by signal N | **129** SIGHUP, **130** SIGINT, 137 SIGKILL, **141** SIGPIPE, **143** SIGTERM (bash: "128+N") | [bash-exit] |
| 64-78 | `sysexits.h` | do not adopt: "This interface has been deprecated … Its use is discouraged" | [sysexits] |

| # | Rule | When | Concrete example | Source |
|---|---|---|---|---|
| CC1 | **A picker returns 0 chosen · 1 nothing matched or chosen · 2 error · 130 cancelled.** Cancel by Esc and by Ctrl-C both give 130 (the fzf/skim convention; `derived:` follow it, scripts already branch on it). Never exit 0 on cancel | inline pickers, confirm prompts | `f=$(pickf) \|\| exit $?` stops the script on cancel; with exit 0 on cancel it would go on with an empty `$f` | see the table below |
| CC2 | **The framework's status must reach the process.** Most frameworks exit 0 after Ctrl-C because in raw mode Ctrl-C is a key (§2), not a signal. Map cancel to 130 and errors to 1 yourself, **after** the terminal is restored | every TUI | Bubble Tea: return `tea.Interrupt`, then `os.Exit(130)` on `tea.ErrInterrupted` | framework table below |

**What pickers actually return on cancel**

| Tool | Chosen / none / error / cancel | Cancel keys | Source |
|---|---|---|---|
| fzf 0.74.4 | 0 / 1 / 2 / **130** | Esc and Ctrl-C → 130 (measured) | [fzf-man] "130 Interrupted with CTRL-C or ESC" |
| skim | 0 / 1 / — / **130** | "Aborted by Ctrl-C/Ctrl-G/ESC/etc..." | [skim] |
| gum 2.0.1 | 0 / 1 / 1 / **130**; 124 timeout | Ctrl-C → 130; **Esc → 1** in `choose`, `input` (measured); in `filter` Esc blurs the search and does not exit | [gum-exit]; measured |
| peco | cancel → **0** by default | `--on-cancel error` makes it non-zero ("for historical and back-compatibility reasons") | [peco] |

**Getting the status out of each framework**

| Framework | Ctrl-C arrives as | Default status | Make the status reach the shell | Source |
|---|---|---|---|---|
| Bubble Tea v2.0.10 | `KeyPressMsg` "ctrl+c" in raw mode; a real SIGINT becomes `InterruptMsg` | `tea.Quit` → `Run()` returns nil → **0** (measured) | on ctrl+c return `tea.Interrupt`; `if errors.Is(err, tea.ErrInterrupted) { os.Exit(130) }`; other `err` → `os.Exit(1)` (measured 130) | [bt-pkg]; `tea.go` `handleSignals` |
| Textual | ctrl+c is bound to `help_quit` (shows a notice, does not quit); ctrl+q quits | 0; unhandled exception → 1 | `self.exit(result, return_code=130)`; after `app.run()`: `sys.exit(app.return_code or 0)` (the docs' own snippet); `run()` returns `result` | [tx-guide], [tx-api] |
| Ink 7.1.1 | `exitOnCtrlC` (default true) calls `exit()` with no value | `waitUntilExit()` resolves → **0** (measured) | `exitOnCtrlC: false`; on ctrl+c `exit(new Error('cancelled'))` → `waitUntilExit()` rejects → `process.exitCode = 130` (measured). Set `process.exitCode`, do not call `process.exit()`: it can drop pending stdout writes | [ink-readme], [node-proc] |
| Ratatui 0.30.2 | `KeyEvent` `Char('c')` + `CONTROL` | whatever `main` returns: `Ok(())` → 0, `Err` → 1 | `fn main() -> std::process::ExitCode`; leave `ratatui::run` (it restores), then `ExitCode::from(130)` | [ratatui.md](frameworks/ratatui.md) §3 |
| gum | n/a | already 0 / 1 / 130 / 124 | branch on it: `svc=$(gum choose …) \|\| exit $?` | [gum.md](frameworks/gum.md) §2 |

---

## 2. Signals

**Raw mode changes what Ctrl-C is.** A full-screen or inline TUI turns off `ISIG`, so Ctrl-C reaches the app as the byte `0x03`, not as SIGINT: "since bubbletea puts the terminal in raw mode, we need to handle it in a per-program basis" [bt-pkg]; Ink: in raw mode "Ctrl+C is ignored by default and the process is expected to handle it manually" [ink-readme]. A real SIGINT arrives only in line mode (one-shot CLIs, spinners, before raw mode starts) or from `kill -INT`.

| # | Rule | When | Concrete example | Source |
|---|---|---|---|---|
| CC3 | **Ctrl-C once: stop, say so, clean up, exit 130. Twice: skip the rest of the cleanup**, still restore the terminal, exit 130 | long cleanups (uploads, rollbacks) | `shipit deploy`: `^C stopping… (rolling back api; ^C again to skip)`; a picker cancels at once, it has nothing to clean | [clig] "exit as soon as possible … Tell the user what will happen when they hit Ctrl-C again" |
| CC4 | **After a real signal, die by that signal**: clean up, reset the handler to `SIG_DFL`, re-send it to yourself, so the parent sees "killed by SIGINT" and a calling script stops too. `exit(130)` is the fallback when the "signal" was a key in raw mode | one-shot CLIs and spinners in line mode | Python does this for an uncaught `KeyboardInterrupt` (3.8+; measured 130). Node's default handler exits with `128 + signal number` (an exit code, not a re-raise) | [cracauer] "You cannot 'fake' the proper exit status by an exit(3)"; [py38]; [node-proc] |
| CC5 | **SIGTERM: same cleanup path, exit 143.** Check each framework: measured with `kill -TERM` against a running app: **Ratatui 0.30.2 `ratatui::run` exits 143 and leaves raw mode, the alt screen and a hidden cursor** (no handler); Bubble Tea v2 restores the terminal but `Run()` returns nil, so the status is **0**; Ink 7.1.1 restores and exits 143 | every full-screen TUI | Ratatui: `signal_hook::flag::register(SIGTERM, flag)`, poll the flag between `event::poll(timeout)` calls, return to restore, exit 143. Bubble Tea: `tea.WithoutSignalHandler()` + your own `signal.Notify` → `p.Quit()` → `os.Exit(143)` (`derived:`; this also removes its SIGINT handling) | measured; [bt-pkg] (SIGTERM → `QuitMsg`) |
| CC6 | **SIGHUP: the terminal is gone.** Do not draw or prompt; save unsaved work to a file; exit 129. Go, Node and Python terminate by default; a handler in Node removes that default | ssh drop, terminal window closed | an editor-like TUI writes `~/.local/state/logq/recover.json` and exits | [go-signal], [node-proc]; `derived:` no drawing |
| CC7 | **SIGPIPE: `app \| head -1` ends silently**: nothing on stderr, status 0 or 141 (141 is what `yes \| head -1` gives), or 1 with Python's recipe | anything that writes to stdout | `logq list \| head -1` prints one line and stops | table below |

**SIGPIPE per language** (writing 100 000 lines into `| head -1`, measured):

| Language | Default on a closed stdout | Measured status and stderr | Fix | Source |
|---|---|---|---|---|
| Go 1.27 | "A write to a broken pipe on file descriptors 1 or 2 … will cause the program to exit with a SIGPIPE signal" | **141**, silent | none needed; do not `signal.Notify` or `Ignore` SIGPIPE (then writes return `syscall.EPIPE` and you must handle it) | [go-signal] |
| Rust 1.98 | libstd sets SIGPIPE to `SIG_IGN` before `main`, so writes return `BrokenPipe` and `println!` panics | **101**, `failed printing to stdout: Broken pipe (os error 32)` | write with `writeln!(out, …)` and return `Ok(())` on `io::ErrorKind::BrokenPipe` (measured 0). `-Zon-broken-pipe=kill` is nightly-only | [rust-pipe] |
| Python 3.14 | "SIGPIPE is ignored" → `BrokenPipeError` | **120**, traceback + `Exception ignored while flushing sys.stdout` | the docs' recipe, in the entry point: `try:` run the command, then **`sys.stdout.flush()` as the try's last line** → `except BrokenPipeError:` → `os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())` → `sys.exit(1)` (measured 1, silent). Without that flush the last buffered chunk is written at interpreter exit, outside the try: 120 and the traceback again. `signal(SIGPIPE, SIG_DFL)` gives 141 silently, but the process dies without running `finally` or `atexit`: only for a disposable filter with no cleanup, never in an app that restores the terminal | [py-signal] |
| Node 26 | "SIGPIPE is ignored by default" → `EPIPE` `'error'` event | `process.stdout.write`: **1**, `Unhandled 'error' event … write EPIPE`; `console.log`: 0, silent, keeps looping | `process.stdout.on('error', e => { if (e.code === 'EPIPE') process.exit(0); throw e; })` (measured 0) | [node-proc] |

---

## 3. TTY checks and streams

Test stdin and stdout **separately** (and stderr when you draw there). Go `term.IsTerminal(int(os.Stdout.Fd()))` ([x-term]); Rust `io::stdout().is_terminal()` (`std::io::IsTerminal`, stable 1.70, [rust-isterm]); Python `sys.stdout.isatty()`; Node `process.stdout.isTTY` (`true` or `undefined`, measured); shell `[ -t 1 ]`.

| stdin | stdout | Behave like this | Example |
|---|---|---|---|
| TTY | TTY | full UI allowed | `pickf` |
| TTY | pipe or file | **picker:** UI on `/dev/tty` or stderr, only the result on stdout. **Anything else:** plain output: no color, no spinner, no alt screen, no cursor addressing | `vim "$(pickf)"`; `logq tail > out.txt` |
| pipe | TTY | read data from stdin, **never prompt on it**; a picker reads candidates from stdin and keys from `/dev/tty` | `git ls-files \| pickf` |
| pipe | pipe | pure filter; a picker with no terminal to open fails at once with a message naming the non-interactive form | `pickf --filter=main < list` (fzf `--filter=STR`) |
| TTY, but data was expected on stdin | any | print usage and exit 2 instead of waiting | `logq parse` with nothing piped |

| # | Rule | When | Concrete example | Source |
|---|---|---|---|---|
| CC8 | **Show help instead of hanging** when the command needs piped input and stdin is a TTY | filters, parsers | `logq parse` → `usage: … \| logq parse` on stderr, exit 2 | [clig] "display help immediately and quit" |
| CC9 | **A picker draws on `/dev/tty` or stderr; stdout gets only the answer.** Measured: fzf 0.74.4 still draws with stdout to a file and stderr to `/dev/null` (it opens `/dev/tty`); gum 2.0.1 draws on stderr (blank screen with `2>/dev/null`, choice still on stdout) | inline pickers, prompts inside `$(…)` | per framework: next table | [fzf-man] `--no-tty-default`; [gum.md](frameworks/gum.md) §2 |
| CC10 | **No terminal at all** (cron, CI, `ssh -T`): do not prompt, do not hang; exit non-zero with the flag that avoids the prompt | anything interactive | gum: `error opening TTY … open /dev/tty: device not configured`, exit 1 ([gum.md](frameworks/gum.md) §11); better: `pickf: no terminal; pass --select NAME`, exit 2 | LC8; [clig] |

| Framework | Keys from `/dev/tty` when stdin is piped | Draw somewhere other than stdout | Source |
|---|---|---|---|
| Bubble Tea v2 | automatic: if stdin is not a terminal, `Run()` opens the TTY (`OpenTTY`) | `tea.WithOutput(os.Stderr)` (gum does this) | `tea.go` source (v2.0.10) |
| Ratatui / crossterm 0.29 | automatic: crossterm's `tty_fd()` uses stdin if it is a TTY, else opens `/dev/tty` | `CrosstermBackend::new(io::stderr())` with `Viewport::Inline(n)` | [crossterm-src] |
| Ink 7.1.1 | manual: `stdin: new tty.ReadStream(fs.openSync('/dev/tty', 'r'))`; with plain piped stdin Ink throws `Raw mode is not supported` (measured) | `render(<App/>, {stdout: process.stderr})` (measured with `exitOnCtrlC: false`, Enter → 0 + answer on stdout, Ctrl-C → 130) | [ink-readme] |
| Textual | the Linux driver reads keys from stdin's fd; piped stdin + keys from `/dev/tty` **UNVERIFIED**, so pass data by file or argument | the driver already writes to `sys.__stderr__`; `app.run(inline=True)` | `drivers/linux_driver.py` source |

---

## 4. Progress, paging and color: only on a TTY

| # | Rule | When | Concrete example | Source |
|---|---|---|---|---|
| CC11 | **Progress and spinners go to stderr, and only when stderr is a TTY**; otherwise one line at start and one at finish (A4 #4). Respond within 100 ms; `derived:` start the spinner after ~200 ms so fast runs do not flash. Hide noisy logs while things succeed, print them on failure | any wait > ~1 s | `shipit deploy 2>deploy.log` → the log has `deploying api…` / `done in 41s`, no `\r` frames | [clig] "<100ms", "don't display any animations" |
| CC12 | **Page only when stdout is a TTY**; use `$PAGER`; if `LESS` is unset, set it (git sets `FRX`; clig suggests `less -FIRX`: quit if one screen, pass color, case-insensitive search, keep output in scrollback); offer `--no-pager` | long output | `logq show 42` pages in a terminal; `logq show 42 \| grep err` never waits for `q` | [git-config] core.pager; [clig] |
| CC13 | **Color decision lives in [terminal-capabilities.md](terminal-capabilities.md) D1** (`--color`, `FORCE_COLOR`, `NO_COLOR`, non-TTY, `TERM=dumb`); do not restate it. Decide **per stream**: stdout piped means no SGR on stdout even when stderr is a TTY | every program that writes SGR | `logq list > out.txt`: file has no `\e[`; the stderr spinner may stay colored | D1 |
| CC14 | **stdout is data, stderr is everything else** (logs, warnings, progress, prompts' chrome, the receipt). While a full-screen UI runs, LC5 applies | always | `logq list 2>/dev/null` still prints every row | [clig] "Send messaging to stderr" |

---

## 5. Machine output

| # | Rule | When | Concrete example | Source |
|---|---|---|---|---|
| CC15 | **Offer `--json`** on every command whose output a script may read: list, get, status, the result of a picker in batch mode. Never switch to JSON by TTY detection alone: the flag decides | list/status commands; anything users pipe to `jq` | `logq list --since 1h --json \| jq -r '.level'` | [clig] "Display output as formatted JSON if `--json` is passed" |
| CC16 | **Lists and streams as NDJSON**: one JSON object per line, `\n`-terminated, no newlines inside, UTF-8, so `head`, `grep` and `jq -c` work while it streams. One result = one object | `--json` on lists, `--follow` | `{"ts":"2026-10-02T10:14:03Z","level":"error","msg":"timeout"}` per line | [ndjson] "MUST NOT contain newlines"; [jsonl] |
| CC17 | **Stable keys, no color, no progress** in machine output: keys only added, never renamed (a rename is a breaking change, `derived:`); timestamps ISO 8601 UTC; errors still go to stderr with a non-zero code; `--plain` for tab-separated text when the human format breaks parsing | `--json`, `--plain` | `logq list --json --color=always` still emits no SGR (`derived:`) | [clig] `--plain` |

---

## 6. Error messages

| # | Rule | When | Concrete example | Source |
|---|---|---|---|---|
| CC18 | **Anatomy: what failed · why (with the value) · what to do next · where to read more.** Put the most important line last; rewrite errors for humans; one line per repeated error group | every error on stderr | below | [clig] "Catch errors and rewrite them for humans", "Put the most important information at the end" |
| CC19 | **The exit code matches the class**: usage → 2 plus a usage hint; runtime → 1; cancel → 130. stdout stays empty on failure | always | `shipit deploy --env` (missing value) → `usage: shipit deploy --env NAME`, exit 2 | §1 |
| CC20 | **Unexpected errors**: a short message by default, the traceback behind `--debug` or an env var, plus a bug-report URL. In a TUI: one line in the message line while it runs, the full error on stderr after the terminal is restored (LC5) | crashes, panics | `shipit: internal error (run with SHIPIT_DEBUG=1); report: https://example.com/shipit/issues` | [clig] "Make it effortless to submit bug reports" |

```text
$ shipit deploy api --env prod-eu
error: deploy of api to prod-eu failed
  why:  image registry.example.com/api:1.4.2 not found (HTTP 404)
  docs: https://docs.example.com/shipit/errors#image-not-found
  next: push it first: docker push registry.example.com/api:1.4.2
$ echo $?
1
```

---

## 7. Shell integration for pickers and file managers

| # | Rule | When | Concrete example | Source |
|---|---|---|---|---|
| CC21 | **cd on exit needs a shell function**: a child process cannot change its parent's directory. The tool hands back a path, the function `cd`s. Three shipped mechanisms: path on stdout (lf `cd "$(command lf -print-last-dir "$@")"`), a cwd file (yazi `--cwd-file`, function `y`; `q` changes dir, `Q` quits without), a command file (broot `--outcmd FILE`, function `br` `eval`s it). Do not `cd` on cancel or non-zero exit; offer a quit key that does not change dir | file managers, directory pickers | `pcd() { local d; d=$(command pickf --dirs "$@") \|\| return; [ -d "$d" ] && builtin cd -- "$d"; }` | [lfcd], [yazi], [broot-sh] |
| CC22 | **Ship shell code as an `init` subcommand** that prints to stdout; the user adds `eval "$(tool init zsh)"` (zoxide: at the end of `~/.zshrc`, after `compinit`; `--cmd j` renames the commands) or `source <(fzf --zsh)`. Keep it fast and side-effect free (`derived:`: it runs on every shell start) | cd wrappers, key bindings, hooks | `eval "$(pickf init zsh)"` defines `pcd` and binds Ctrl-T | [zoxide], [fzf-man] `--zsh` |
| CC23 | **Completions are printed, not installed**: Cobra adds a `completion` command (`source <(app completion bash)`); clap via `clap_complete`; click `eval "$(_FOO_BAR_COMPLETE=zsh_source foo-bar)"`; yargs `.completion()` | any CLI with subcommands or enumerable values | `pickf completion zsh > "${fpath[1]}/_pickf"` | [cobra], [clap-complete], [click], [yargs] |
| CC24 | **Never edit rc files silently**: print the line for the user to add, or ask first, say exactly what will change, and remember a refusal | `init`, completions, first run | broot asks before registering `br`, records `refused`, retries only on `broot --install`; prints the function with `--print-shell-function bash` | [broot-sh]; [clig] "ask the user for consent" |

---

## 8. Checklist (`SH-` ids)

Same columns as the audit checklist; `pipestatus[1]` is zsh (bash: `PIPESTATUS[0]`). `cap+k X` = `SKILL_DIR/scripts/capture_tui.sh … -k X`, run the command as `sh -c 'APP; echo $? > rc'`.

| ID | Rule → fail when | Sev | Kind | Verify | Source |
|---|---|---|---|---|---|
| SH-01 | `app list \| head -1` ends silently. Fail when stderr has a traceback, panic or `EPIPE`, or the app's status is not 0 or 141 (1 accepted for Python's documented recipe). | M | bug | `app list 2>err \| head -1; echo ${pipestatus[1]}; [ ! -s err ]` | CC7 |
| SH-02 | Ctrl-C in the picker or TUI exits 130. Fail when `echo $?` gives 0 or 1. | M | bug | `cap+k C-c`, read `rc` | CC1, CC2 |
| SH-03 | Esc (cancel) in a picker exits non-zero (130, or a documented 1). Fail when 0. | M | bug | `cap+k Escape`, read `rc` | CC1 |
| SH-04 | A chosen value reaches stdout alone. Fail when `out.txt` holds chrome, a receipt or any ESC byte. | B | bug | `app > out.txt` + `cap+k Enter`; `grep -c $'\e' out.txt` = 0 | CC9, P2 |
| SH-05 | Output to a file is plain. Fail when `app > out.txt` contains ESC bytes, `\r` spinner frames or `?1049h`. | M | bug | `app > out.txt; grep -c $'[\e\r]' out.txt` = 0 | CC11, CC13; extends TC-03 |
| SH-06 | SIGTERM restores the terminal and exits 143. Fail (B) when raw mode, the alt screen or a hidden cursor survive; (m) when the status is 0. | B/m | bug | LC1 restore check with `kill -TERM` from another pane; `#{alternate_on}` | CC5 |
| SH-07 | Piped data does not break the UI: `printf 'a\nb\n' \| pickf` still takes keys; `echo x \| app` never prompts on stdin. | M | bug | `cap` of `printf … \| pickf` + `-k Down Enter` | CC9, table §3 |
| SH-08 | No terminal: fail when the app hangs or prompts; pass when it exits non-zero within 1 s naming the non-interactive flag. | M | bug | Linux: `setsid -w app </dev/null >out 2>err; echo $?` | CC10, LC8 |
| SH-09 | A command that expects stdin, run with stdin on a TTY, prints usage and exits 2. Fail when it waits. | m | bug | `cap@80x24`, no keys, check `rc` after 1 s | CC8 |
| SH-10 | Exit codes match the class: usage 2, runtime 1, cancel 130; stdout empty on failure. Fail when a usage error exits 1 without a usage hint, or any failure exits 0. | M | bug | `app --bogus; echo $?`; force a runtime error | CC19, §1 |
| SH-11 | Errors say what, why, next. Fail when stderr shows a bare `Error: ENOENT`, or a stack trace without `--debug`. | m | style | read stderr of a forced error | CC18, CC20 |
| SH-12 | `--json` is parseable and plain. Fail when `app list --json \| jq -c . >/dev/null` fails, the output has SGR, or a list is neither NDJSON nor one documented array. | M | bug | the command above; `grep -c $'\e'` | CC15-CC17 |
| SH-13 | Pager and progress only on a TTY. Fail when `app log \| cat` waits for `q`, or `app sync 2>err` leaves spinner frames in `err`. | M | bug | run piped / redirected | CC11, CC12 |
| SH-14 | cd on exit works both ways. Fail when the wrapper does not change dir after a choice, or does after cancel / the no-cd quit key. | M | bug | `pcd`, choose, `pwd`; again with Esc | CC21 |
| SH-15 | rc files untouched without consent. Fail when `~/.zshrc` / `~/.bashrc` checksums change after first run or `init` without a prompt that named the change. | B | bug | `shasum ~/.zshrc` before / after | CC24 |

---

## Source index

- [bash-exit] https://www.gnu.org/software/bash/manual/html_node/Exit-Status.html
- [sysexits] https://man.freebsd.org/cgi/man.cgi?query=sysexits&sektion=3
- [clig] https://clig.dev/
- [cracauer] https://www.cons.org/cracauer/sigint.html
- [fzf-man] `man fzf` 0.74.4 (EXIT STATUS, `--filter`, `--zsh`, `--no-tty-default`); https://github.com/junegunn/fzf/blob/master/src/constants.go
- [skim] https://github.com/skim-rs/skim#exit-code
- [peco] https://github.com/peco/peco#--on-cancel-successerror
- [gum-exit] https://github.com/charmbracelet/gum/blob/main/internal/exit/exit.go
- [go-flag] https://pkg.go.dev/flag · [clap-src] https://github.com/clap-rs/clap/blob/master/clap_builder/src/util/mod.rs · [commander-src] https://github.com/tj/commander.js/blob/master/lib/command.js (`error()`)
- [bt-pkg] https://pkg.go.dev/charm.land/bubbletea/v2 (`Run`, `ErrInterrupted`, `InterruptMsg`, `WithOutput`, `WithoutSignalHandler`); source `tea.go` v2.0.10
- [tx-guide] https://textual.textualize.io/guide/app/#return-code · [tx-api] https://textual.textualize.io/api/app/
- [ink-readme] https://github.com/vadimdemedes/ink/blob/master/readme.md (`exit(errorOrResult)`, `waitUntilExit`, `exitOnCtrlC`, `isRawModeSupported`)
- [crossterm-src] https://github.com/crossterm-rs/crossterm/blob/master/src/terminal/sys/file_descriptor.rs (`tty_fd`)
- [go-signal] https://pkg.go.dev/os/signal · [x-term] https://pkg.go.dev/golang.org/x/term
- [rust-pipe] https://doc.rust-lang.org/beta/unstable-book/compiler-flags/on-broken-pipe.html · [rust-isterm] https://doc.rust-lang.org/std/io/trait.IsTerminal.html
- [py-signal] https://docs.python.org/3/library/signal.html#note-on-sigpipe · [py38] https://docs.python.org/3/whatsnew/3.8.html (uncaught `KeyboardInterrupt` exits via SIGINT)
- [node-proc] https://nodejs.org/api/process.html (signal events, a note on process I/O, `process.exitCode`)
- [git-config] https://git-scm.com/docs/git-config#Documentation/git-config.txt-corepager
- [ndjson] https://github.com/ndjson/ndjson-spec · [jsonl] https://jsonlines.org/
- [yazi] https://yazi-rs.github.io/docs/quick-start#shell-wrapper · [broot-sh] https://dystroy.org/broot/install-br/ and https://github.com/Canop/broot/blob/main/src/shell_install/bash.rs · [lfcd] https://github.com/gokcehan/lf/blob/master/etc/lfcd.sh · [zoxide] https://github.com/ajeetdsouza/zoxide
- [cobra] https://github.com/spf13/cobra/blob/main/site/content/completions/_index.md · [clap-complete] https://docs.rs/clap_complete · [click] https://click.palletsprojects.com/en/stable/shell-completion/ · [yargs] https://github.com/yargs/yargs/blob/main/docs/api.md
