#!/usr/bin/env bash
# Smoke tests for capture_tui.sh using only /bin/sh programs (no lazygit/btop needed).
# Run: bash tests/test_capture.sh   exit 0 = pass. Uses private tmux sockets only.
HERE=$(cd "$(dirname "$0")" && pwd)
SKILL="$HERE/../skills/tui-design"
CAP="$SKILL/scripts/capture_tui.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/captest.XXXXXX")
trap 'rm -rf "$TMP"' EXIT
FAIL=0
ok() { if [ "$1" = 0 ]; then echo "ok   $2"; else echo "FAIL $2"; FAIL=1; fi; }
before=$(ls "${TMUX_TMPDIR:-/tmp}"/tmux-"$(id -u)" 2>/dev/null | grep -c '^tui-capture-')

# 1. styled text, wide glyphs, overline normalization, padding, exit status
"$CAP" -s 40x5 -o "$TMP/a" -- sh -c 'printf "\033[1;31mhi\033[0m \033[53mover\033[55m \346\227\245\346\234\254 end\n"; exit 3' >/dev/null
[ -f "$TMP/a/40x5.ansi" ]; ok $? "writes .ansi"
python3 - "$TMP/a" <<'PY'
import json, re, sys, unicodedata
d = sys.argv[1]
ansi = open(d + "/40x5.ansi", encoding="utf-8").read().split("\n")[:-1]
txt = open(d + "/40x5.txt", encoding="utf-8").read().split("\n")[:-1]
meta = json.load(open(d + "/40x5.meta.json"))
w = lambda s: sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in re.sub(r"\x1b\[[0-9;:]*m", "", s))
checks = {
    "5 rows": len(ansi) == 5 and len(txt) == 5,
    "every .ansi row is 40 cells": all(w(r) == 40 for r in ansi),
    "every .txt row is 40 cells": all(w(r) == 40 for r in txt),
    "no 5:3 left": "5:3" not in "".join(ansi) and "\x1b[53m" in "".join(ansi),
    "wide glyphs kept": "日本" in txt[0],
    "meta size/cursor/alt": meta["size"] == {"cols": 40, "rows": 5} and "x" in meta["cursor"] and meta["alternate_on"] is False,
    "exit status recorded": meta["exited"] is True and meta["exit_status"] == 3,
    "env defaults": meta["env"].get("TERM") == "xterm-256color" and meta["env"].get("COLORTERM") == "truecolor",
}
bad = [k for k, v in checks.items() if not v]
print("\n".join(("ok   " if v else "FAIL ") + k for k, v in checks.items()))
sys.exit(1 if bad else 0)
PY
[ $? = 0 ] || FAIL=1

# 2. unstable screen -> stable=false and volatile cells; -k keys; resize in one run
"$CAP" -s 30x4 -w 1 -o "$TMP/b" -- sh -c 'i=0; while :; do printf "\033[H tick %s" $i; i=$((i+1)); sleep 0.05; done' >/dev/null
python3 -c "import json,sys; m=json.load(open('$TMP/b/30x4.meta.json')); sys.exit(0 if (m['stable'] is False and m['volatile']['cells']>0 and m['volatile']['boxes']) else 1)"
ok $? "unstable screen is flagged with volatile boxes"

"$CAP" -s 30x4 -s 20x3 -k "text:ab" -o "$TMP/c" -- cat >/dev/null
grep -q '^ab' "$TMP/c/30x4.txt" && [ -f "$TMP/c/20x3.txt" ]
ok $? "keys sent; second size resized in the same session"

# 3. SGR carry-over: tmux omits the opening SGR of a row when it equals the previous row's closing state
"$CAP" -s 10x4 -o "$TMP/d" -- sh -c 'printf "\033[44;31mAAAAAAAAAA\033[44;31mBBBBBBBBBB\033[44;31mCCCCCCCCCC"; sleep 3' >/dev/null
python3 - "$TMP/d/10x4.ansi" <<'PY'
import sys
rows = open(sys.argv[1], encoding="utf-8").read().split("\n")[:3]
sys.exit(0 if all("44" in r.split("A")[0].split("B")[0].split("C")[0] and "31" in r.split("A")[0].split("B")[0].split("C")[0] for r in rows) else 1)
PY
ok $? "every row re-opens the active SGR (self-contained lines)"

# 3b. cell-exact against a headless frame: demo mockup cat-ed inside tmux must equal ansi_grid of the same ANSI
if python3 "$SKILL/scripts/render_mockup.py" "$SKILL/assets/demo/fleet--normal--80x24.mock" -o "$TMP/fleet.ansi" 2>/dev/null; then
  "$CAP" -s 80x24 -o "$TMP/e" -- sh -c "printf '%s' \"\$(cat $TMP/fleet.ansi)\"; sleep 5" >/dev/null
  python3 "$SKILL/scripts/ansi_grid.py" "$TMP/fleet.ansi" --cols 80 --rows 24 -o "$TMP/t.json"
  python3 "$SKILL/scripts/ansi_grid.py" "$TMP/e/80x24.ansi" --cols 80 --rows 24 -o "$TMP/c.json"
  python3 - "$TMP/t.json" "$TMP/c.json" <<'PY'
import json, sys
a, b = (json.load(open(f))["cells"] for f in sys.argv[1:3])
def key(c):
    return (c["ch"], None if c["ch"] == " " else c["fg"]["raw"], c["bg"]["raw"], () if c["ch"] == " " else tuple(c["attrs"]))
diff = [(x, y) for y in range(24) for x in range(80) if key(a[y][x]) != key(b[y][x])]
print("cells differing from headless frame:", len(diff), diff[:5])
sys.exit(1 if diff else 0)
PY
  ok $? "capture of the demo screen equals the headless grid"
fi

# 4. errors
"$CAP" -- /nonexistent/cmd >/dev/null 2>&1; [ $? = 2 ]; ok $? "missing command exits 2"
"$CAP" -s bad -- true >/dev/null 2>&1; [ $? = 2 ]; ok $? "bad size exits 2"
"$CAP" --help | grep -q Examples; ok $? "--help has examples"

# 5. fresh sizes: each restart must terminate the preceding private session
cat > "$TMP/fresh-app.sh" <<'SH'
#!/bin/sh
pid_file=$1
if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
  printf '\033[H already-running\n'
  exit 7
fi
printf '%s\n' "$$" > "$pid_file"
trap 'rm -f "$pid_file"; exit 0' EXIT HUP INT TERM
while :; do printf '\033[H running\n'; sleep 0.1; done
SH
chmod +x "$TMP/fresh-app.sh"
"$CAP" -f -s 20x3 -s 21x3 -w 0.5 -o "$TMP/f" -- "$TMP/fresh-app.sh" "$TMP/fresh.pid" >/dev/null
grep -q 'running' "$TMP/f/21x3.txt" && ! grep -q 'already-running' "$TMP/f/21x3.txt"
ok $? "fresh sizes stop the prior session before restart"

# 6. cleanup: no sockets or servers of ours left behind
sleep 0.3
after=$(ls "${TMUX_TMPDIR:-/tmp}"/tmux-"$(id -u)" 2>/dev/null | grep -c '^tui-capture-')
[ "$after" = "$before" ]; ok $? "no tui-capture sockets left"
! ps ax | grep -v grep | grep -q 'tmux.*-L tui-capture-'; ok $? "no tui-capture tmux server left"
exit $FAIL
