#!/usr/bin/env bash
# capture_tui.sh - Live capture: run a TUI in a detached tmux pane and dump the
# rendered cell grid (ANSI + plain text + metadata) at one or more terminal sizes.
#
# Bash 3.2 (macOS) compatible. Needs: tmux (>= 3.2 for `new-session -e`) and python3 (stdlib only).
# SAFETY: uses a private tmux server (`tmux -L tui-capture-$$ -f /dev/null`); only that socket is
# ever killed (trap on exit). The default tmux server and the user's tmux.conf are never touched.

PROG=$(basename "$0")

usage() {
  cat <<EOF
Usage: $PROG [OPTIONS] -- CMD [ARGS...]

Run CMD in a detached pane of a private tmux server (tmux -L tui-capture-PID; the default server is
never touched), wait for the screen to settle, and write per size:
  OUTDIR/<cols>x<rows>.ansi       capture-pane -p -e, padded to cols x rows, tmux's "5:3" -> "53"
  OUTDIR/<cols>x<rows>.txt        plain capture-pane -p (same padding rule)
  OUTDIR/<cols>x<rows>.meta.json  command, size, env, keys, stable, cursor, alternate_on, volatile boxes...

Options:
  -s COLSxROWS   terminal size; repeatable (default 80x24). The session starts at the first size;
                 later sizes use resize-window on the same running app (responsive audit).
  -k KEYS        keys to send once, after the first size has settled and before the first capture.
                 Repeatable (sent in order). KEYS = space-separated tmux key names ("Down Down Enter",
                 "C-x", "Escape"); prefix "text:" sends the rest literally ("text:hello world").
  -f             fresh session per size instead of resize: the app restarts at each size and the
                 -k keys are replayed in every session.
  -e VAR=VAL     environment for the app; repeatable. Defaults: TERM=xterm-256color COLORTERM=truecolor
                 (not tmux's own TERM: Charm tools such as gum/bubbletea ignore COLORTERM when TERM
                 starts with tmux/screen and would fall back to 256 colors).
  -C DIR         working directory of the app (default: current directory).
  -w SECONDS     max seconds to wait for a stable screen (default 5).
  -q MS          quiet period: screen must be unchanged this long (default 400).
  -p SECONDS     after settling, keep sampling this long and mark cells that change as volatile
                 (default 0). Use >= 2x the app's refresh interval for live UIs (btop: -p 3).
  -d MS          delay after each -k group (default 200).
  -o OUTDIR      output directory (default ./tui-capture).
  -h, --help     this help.

If the screen never settles within -w, two captures ~0.6 s apart are compared and the differing
cells are recorded as volatile ("stable": false in meta.json). Exit: 0 ok, 2 usage/environment error.

Examples:
  $PROG -s 80x24 -s 120x30 -o out -- lazygit
  $PROG -s 100x30 -k "Down Down Enter" -o out -- /opt/homebrew/bin/k9s
  $PROG -s 120x30 -p 3 -e NO_COLOR=1 -o out -- btop        # btop redraws every ~2 s: probe 3 s
  $PROG -s 60x10 -o out -- sh -c 'printf "\\033[1;31mhi\\033[0m\\n"'

Quirks handled: tmux prints overline (SGR 53) as "5:3", which parsers read as blink; the .ansi output
rewrites it to "53". tmux also carries SGR state across rows (a row that starts in the previous row's closing
style has no SGR at its start), so every .ansi row is made self-contained: re-open the active state, text,
reset, pad. Trailing styled spaces are kept (capture-pane -N). Wide glyph widths use East Asian Width.
EOF
}

die() { echo "$PROG: $*" >&2; exit 2; }

SIZES=()
KEYS=()
ENVS=()
CWD=$PWD
MAXWAIT=5
QUIET=400
PROBE=0
KDELAY=200
OUT=./tui-capture
FRESH=0

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    -s) [ $# -ge 2 ] || die "-s needs COLSxROWS"; SIZES[${#SIZES[@]}]=$2; shift 2 ;;
    -k) [ $# -ge 2 ] || die "-k needs KEYS"; KEYS[${#KEYS[@]}]=$2; shift 2 ;;
    -e) [ $# -ge 2 ] || die "-e needs VAR=VAL"; ENVS[${#ENVS[@]}]=$2; shift 2 ;;
    -C) [ $# -ge 2 ] || die "-C needs DIR"; CWD=$2; shift 2 ;;
    -w) [ $# -ge 2 ] || die "-w needs SECONDS"; MAXWAIT=$2; shift 2 ;;
    -q) [ $# -ge 2 ] || die "-q needs MS"; QUIET=$2; shift 2 ;;
    -p) [ $# -ge 2 ] || die "-p needs SECONDS"; PROBE=$2; shift 2 ;;
    -d) [ $# -ge 2 ] || die "-d needs MS"; KDELAY=$2; shift 2 ;;
    -o) [ $# -ge 2 ] || die "-o needs OUTDIR"; OUT=$2; shift 2 ;;
    -f) FRESH=1; shift ;;
    --) shift; break ;;
    -*) die "unknown option $1 (see --help)" ;;
    *) break ;;
  esac
done

[ $# -ge 1 ] || { usage >&2; exit 2; }
command -v tmux >/dev/null 2>&1 || die "tmux not found: brew install tmux"
command -v python3 >/dev/null 2>&1 || die "python3 not found"
[ ${#SIZES[@]} -gt 0 ] || SIZES[0]=80x24
for s in "${SIZES[@]}"; do
  case "$s" in [0-9]*x[0-9]*) ;; *) die "bad size '$s' (want COLSxROWS)" ;; esac
done
case "$MAXWAIT$QUIET$PROBE$KDELAY" in *[!0-9.]*) die "-w/-q/-p/-d must be numbers" ;; esac
[ -d "$CWD" ] || die "working directory not found: $CWD"
CWD=$(cd "$CWD" && pwd)

# Resolve the command to an absolute path (the tmux server's cwd differs from ours).
CMD0=$1; shift
case "$CMD0" in
  /*) ABS=$CMD0 ;;
  */*) ABS=$(cd "$(dirname "$CMD0")" 2>/dev/null && pwd)/$(basename "$CMD0") ;;
  *) ABS=$(type -P "$CMD0" 2>/dev/null) || ABS= ;;
esac
[ -n "$ABS" ] && [ -x "$ABS" ] || die "command not found or not executable: $CMD0"
CMDV=("$ABS" "$@")

mkdir -p "$OUT" || die "cannot create $OUT"
OUT=$(cd "$OUT" && pwd)
TMP=$(mktemp -d "${TMPDIR:-/tmp}/tui-capture.XXXXXX") || die "mktemp failed"

# Private server. Only ever kill this socket.
SOCK="tui-capture-$$"
T() { tmux -L "$SOCK" -f /dev/null "$@"; }
SESS=cap0
SESSN=0
SOCKPATH=
cleanup() {
  T kill-server >/dev/null 2>&1
  # kill-server leaves the (now dead) socket file behind: remove only ours
  [ -n "$SOCKPATH" ] && case "$SOCKPATH" in */"$SOCK") rm -f "$SOCKPATH" ;; esac
  rm -rf "$TMP"
}
trap cleanup EXIT
trap 'exit 130' INT TERM

# Environment: defaults unless overridden by -e.
has_env() { local k; for k in ${ENVS[@]+"${ENVS[@]}"}; do [ "${k%%=*}" = "$1" ] && return 0; done; return 1; }
has_env TERM || ENVS[${#ENVS[@]}]="TERM=xterm-256color"
has_env COLORTERM || ENVS[${#ENVS[@]}]="COLORTERM=truecolor"
ENVARGS=()
for e in "${ENVS[@]}"; do ENVARGS[${#ENVARGS[@]}]=-e; ENVARGS[${#ENVARGS[@]}]=$e; done

start_session() {  # $1 = COLSxROWS
  local c=${1%x*} r=${1#*x}
  SESS="cap$SESSN"; SESSN=$((SESSN + 1))      # unique name per session; the private server dies at exit
  # Wrapper keeps the pane alive after CMD exits (tmux drops the output of instantly-exiting
  # commands otherwise) and records the exit status. The app still runs directly on the pty.
  T new-session -d -s "$SESS" -x "$c" -y "$r" -c "$CWD" "${ENVARGS[@]}" \
    sh -c '"$@"; echo $? > "$0"; exec sleep 86400' "$TMP/exit.$SESS" "${CMDV[@]}" \
    || die "tmux new-session failed (tmux >= 3.2 needed for -e)"
  SOCKPATH=$(T display -p -t "$SESS" '#{socket_path}' 2>/dev/null)
}

snap() { T capture-pane -p -e -N -t "$SESS" 2>/dev/null; }   # -N keeps styled trailing spaces (without it the last bg cells are dropped)

# Poll until the pane is unchanged for QUIET ms. Sets STABLE (1/0).
wait_stable() {
  local max_polls need polls=0 same=0 last= cur
  max_polls=$(awk "BEGIN{printf \"%d\", $MAXWAIT*10}"); need=$(awk "BEGIN{printf \"%d\", $QUIET/100}")
  [ "$need" -ge 1 ] || need=1
  STABLE=0
  while [ "$polls" -lt "$max_polls" ]; do
    cur=$(snap | cksum)
    if [ "$cur" = "$last" ]; then same=$((same + 1)); else same=0; last=$cur; fi
    [ "$same" -ge "$need" ] && { STABLE=1; return; }
    polls=$((polls + 1)); sleep 0.1
  done
}

send_keys() {
  local k
  for k in ${KEYS[@]+"${KEYS[@]}"}; do
    case "$k" in
      text:*) T send-keys -t "$SESS" -l -- "${k#text:}" ;;
      *) T send-keys -t "$SESS" $k ;;   # intentional word splitting: several key names
    esac
    sleep "$(awk "BEGIN{print $KDELAY/1000}")"
  done
}

write_frame() {  # $1 = COLSxROWS requested
  local c r pw ph base cur
  pw=$(T display -p -t "$SESS" '#{pane_width}'); ph=$(T display -p -t "$SESS" '#{pane_height}')
  base="$OUT/${pw}x${ph}"
  [ "${pw}x${ph}" = "$1" ] || echo "$PROG: warning: requested $1 but pane is ${pw}x${ph}" >&2
  # Frames: 0 = the final settled capture; further frames sampled for volatility.
  rm -f "$TMP"/cap.*
  snap > "$TMP/cap.0"
  T capture-pane -p -t "$SESS" > "$TMP/plain.txt"
  T display -p -t "$SESS" '#{cursor_x} #{cursor_y} #{cursor_flag} #{alternate_on}' > "$TMP/state.txt"
  if [ -s "$TMP/exit.$SESS" ]; then cp "$TMP/exit.$SESS" "$TMP/exit"; else rm -f "$TMP/exit"; fi
  local n=1 probe=$PROBE
  if [ "$STABLE" = 0 ]; then probe=$(awk "BEGIN{p=$PROBE; print (p<0.6)?0.6:p}"); fi
  if awk "BEGIN{exit !($probe>0)}"; then
    local end_polls=$(awk "BEGIN{printf \"%d\", $probe*1000/250}") i=0
    while [ "$i" -lt "$end_polls" ]; do
      sleep 0.25; snap > "$TMP/cap.$n"; n=$((n + 1)); i=$((i + 1))
    done
    [ "$n" -gt 1 ] || { sleep 0.6; snap > "$TMP/cap.1"; n=2; }
  fi
  CMDJ=$(printf '%s\n' "${CMDV[@]}"); ENVJ=$(printf '%s\n' "${ENVS[@]}")
  KEYJ=$(printf '%s\n' ${KEYS[@]+"${KEYS[@]}"})
  TMUXV=$(tmux -V)
  python3 - "$base" "$pw" "$ph" "$n" "$STABLE" "$QUIET" "$TMP" "$TMUXV" "$CWD" "$MAXWAIT" "$PROBE" "$CMDJ" "$ENVJ" "$KEYJ" <<'PY'
import json, sys, unicodedata, re
base, cols, rows, ncap, stable, quiet, tmp, tmuxv, cwd, maxwait, probe, cmdj, envj, keyj = sys.argv[1:15]
cols, rows, ncap = int(cols), int(rows), int(ncap)
TOK = re.compile(r'\x1b\[([0-9;:]*)m|\x1b\](?:8;[^\x07\x1b]*)(?:\x1b\\|\x07)|(.)', re.S)

def cw(ch):
    if unicodedata.combining(ch) or unicodedata.category(ch) in ("Mn", "Me", "Cf"):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1

def fix_sgr(m):  # tmux emits overline (53) as "5:3"
    return "\x1b[" + re.sub(r'(^|;)5:3(?=;|$)', r'\g<1>53', m.group(1)) + "m"

def sgr_state(state, params):
    """Track the active SGR as the sequences applied since the last reset (replayable verbatim)."""
    parts = params.split(";") if params else ["0"]
    if parts[0] in ("", "0"):
        state = []
        params = ";".join(parts[1:])
    return state + [params] if params else state


def pad_ansi(text):
    """Make every line self-contained. tmux carries SGR state across lines (a line that starts with the
    style the previous one ended with has no SGR at its start), so each row re-opens the active state,
    then resets and pads to the pane width."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    out, state = [], []
    for ln in lines[:rows]:
        ln = re.sub(r'\x1b\[([0-9;:]*)m', fix_sgr, ln)
        prefix = "\x1b[0m" + ("\x1b[" + ";".join(state) + "m" if state else "")
        w = 0
        for m in TOK.finditer(ln):
            if m.group(2) is not None:
                w += cw(m.group(2))
            elif m.group(1) is not None:
                state = sgr_state(state, m.group(1))
        out.append(prefix + ln + "\x1b[0m" + " " * max(0, cols - w))
    out += [" " * cols] * (rows - len(out))
    return out


def cells(text):
    """Per-cell (char, sgr-state) keys for volatility diffing."""
    grid = []
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    st = ""
    for ln in lines[:rows]:
        row = []
        for m in TOK.finditer(ln):
            if m.group(2) is None:
                if m.group(1) is not None:
                    p = m.group(1)
                    st = "" if p in ("", "0") else st + ";" + p   # state carries across lines (tmux)
                continue
            ch = m.group(2)
            w = cw(ch)
            if w == 0:
                if row:
                    row[-1] = (row[-1][0] + ch, row[-1][1])
                continue
            row.append((ch, st))
            if w == 2:
                row.append(("", st))
        row += [(" ", "")] * (cols - len(row))
        grid.append(row[:cols])
    grid += [[(" ", "")] * cols] * (rows - len(grid))
    return grid

def pad_plain(text):
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    out = []
    for ln in lines[:rows]:
        w = sum(cw(c) for c in ln)
        out.append(ln + " " * max(0, cols - w))
    return out + [" " * cols] * (rows - len(out))

raw0 = open(f"{tmp}/cap.0", encoding="utf-8", errors="replace").read()
ansi = pad_ansi(raw0)
open(base + ".ansi", "w", encoding="utf-8").write("\n".join(ansi) + "\n")
plain = pad_plain(open(f"{tmp}/plain.txt", encoding="utf-8", errors="replace").read())
open(base + ".txt", "w", encoding="utf-8").write("\n".join(plain) + "\n")

diff = set()
g0 = cells(raw0)
for i in range(1, ncap):
    gi = cells(open(f"{tmp}/cap.{i}", encoding="utf-8", errors="replace").read())
    for y in range(rows):
        for x in range(cols):
            if g0[y][x] != gi[y][x]:
                diff.add((x, y))

# Merge differing cells into boxes: horizontal runs per row, then merge runs touching on adjacent rows.
runs = []
for y in range(rows):
    xs = sorted(x for (x, yy) in diff if yy == y)
    s = p = None
    for x in xs:
        if s is None:
            s = p = x
        elif x <= p + 1:
            p = x
        else:
            runs.append([s, y, p, y]); s = p = x
    if s is not None:
        runs.append([s, y, p, y])
boxes = []
changed = True
while changed:
    changed = False
    out = []
    for r in runs:
        for b in out:
            if r[0] <= b[2] + 1 and r[2] >= b[0] - 1 and r[1] <= b[3] + 1 and r[3] >= b[1] - 1:
                b[0], b[1], b[2], b[3] = min(b[0], r[0]), min(b[1], r[1]), max(b[2], r[2]), max(b[3], r[3])
                changed = True
                break
        else:
            out.append(list(r))
    runs = out
boxes = sorted(({"x": b[0], "y": b[1], "w": b[2] - b[0] + 1, "h": b[3] - b[1] + 1} for b in runs),
               key=lambda b: (b["y"], b["x"]))

st = open(f"{tmp}/state.txt").read().split()
cx, cy, cflag, alt = int(st[0]), int(st[1]), int(st[2]), int(st[3])
try:
    exit_status = int(open(f"{tmp}/exit").read().strip())
except (OSError, ValueError):
    exit_status = None
meta = {
    "command": cmdj.split("\n"),
    "cwd": cwd,
    "size": {"cols": cols, "rows": rows},
    "env": dict(e.split("=", 1) for e in envj.split("\n") if "=" in e),
    "keys": [k for k in keyj.split("\n") if k],
    "stable": stable == "1",
    "quiet_ms": int(float(quiet)),
    "max_wait_s": float(maxwait),
    "probe_s": float(probe),
    "samples": ncap,
    "cursor": {"x": cx, "y": cy, "visible": bool(cflag)},
    "alternate_on": bool(alt),
    "exited": exit_status is not None,
    "exit_status": exit_status,
    "volatile": {"cells": len(diff), "boxes": boxes},
    "tmux": tmuxv,
    "normalized": ["tmux 5:3 -> 53 (overline)", "rows padded to pane width"],
}
open(base + ".meta.json", "w").write(json.dumps(meta, indent=2) + "\n")
print(f"{base}.ansi  stable={meta['stable']} alt={meta['alternate_on']} volatile_cells={len(diff)} boxes={len(boxes)}")
PY
}

N=${#SIZES[@]}
i=0
for s in "${SIZES[@]}"; do
  if [ "$i" -eq 0 ] || [ "$FRESH" = 1 ]; then
    [ "$i" -eq 0 ] || T kill-session -t "$SESS" || die "kill-session failed for $SESS"
    start_session "$s"
    wait_stable
    send_keys
    [ ${#KEYS[@]} -gt 0 ] && wait_stable
  else
    T resize-window -t "$SESS" -x "${s%x*}" -y "${s#*x}" || die "resize-window failed for $s"
    sleep 0.2
    wait_stable
  fi
  write_frame "$s"
  i=$((i + 1))
done
exit 0
