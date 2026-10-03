#!/usr/bin/env bash
# capture.sh THEME_ID_OR_JSON OUT_DIR [DEPTH]
# Static frames: OUT_DIR/gum--normal--80x24.ansi and gum--normal--120x30.ansi (fleet-static.sh).
# Interactive frame (private tmux socket, never the default server): OUT_DIR/gum-flow--choose--80x24.ansi,
# the `gum choose` screen of fleet-flow.sh after pressing Down once. Needs gum, jq, python3, tmux (for the flow).
# A theme ID needs SKILL_DIR=/path/to/tui-design (or this starter still inside the skill); a JSON path does not.
set -eo pipefail
here=$(cd "$(dirname "$0")" && pwd)
# Skill lookup, needed only to turn a theme ID into JSON: $SKILL_DIR first, then the relative path
# (works when this starter still sits inside the skill). Copied starters need SKILL_DIR.
find_skill() {
  local c
  for c in "${SKILL_DIR:-}" "$here/../../.."; do
    if [ -n "$c" ] && [ -f "$c/scripts/export_theme.py" ]; then (cd "$c" && pwd); return 0; fi
  done
  echo "capture.sh: cannot find the tui-design skill (scripts/export_theme.py). Set SKILL_DIR=/path/to/tui-design," >&2
  echo "            or pass a theme JSON file instead of a theme ID." >&2
  return 1
}
theme=${1:?usage: capture.sh THEME_ID_OR_JSON OUT_DIR [DEPTH]}
out=${2:?usage: capture.sh THEME_ID_OR_JSON OUT_DIR [DEPTH]}
depth=${3:-${DEPTH:-truecolor}}
for c in gum jq; do command -v $c >/dev/null || { echo "$c not found (brew install $c)" >&2; exit 2; }; done
mkdir -p "$out"
tj=$(mktemp "${TMPDIR:-/tmp}/fleet-gum.XXXXXX"); trap 'rm -f "$tj"' EXIT
if [ -f "$theme" ]; then cp "$theme" "$tj"; else skill=$(find_skill) || exit 2; python3 "$skill/scripts/export_theme.py" "$theme" --target json -o "$tj"; fi
for size in 80x24 120x30; do
  "$here/fleet-static.sh" --cols "${size%x*}" --rows "${size#*x}" --theme "$tj" --depth "$depth" > "$out/gum--normal--$size.ansi"
  echo "wrote $out/gum--normal--$size.ansi"
done
if command -v tmux >/dev/null; then
  sock=gumcap$$; trap 'tmux -L "$sock" kill-server 2>/dev/null; rm -f "$tj"' EXIT   # only our own socket
  tmux -L "$sock" -f /dev/null new-session -d -s cap -x 80 -y 24 -e COLORTERM=truecolor -e TERM=xterm-256color \
    "DEPTH=$depth '$here/fleet-flow.sh' '$tj'; sleep 5"
  sleep 1.2; tmux -L "$sock" send-keys -t cap Down; sleep 0.4
  tmux -L "$sock" capture-pane -t cap -p -e > "$out/gum-flow--choose--80x24.ansi"
  echo "wrote $out/gum-flow--choose--80x24.ansi"
else
  echo "tmux not found: skipped the interactive flow capture" >&2
fi
