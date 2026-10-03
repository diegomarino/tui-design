#!/usr/bin/env bash
# capture.sh THEME_ID_OR_JSON OUT_DIR [DEPTH]
# Builds the starter in a temp dir (nothing is written next to the source) and writes
#   OUT_DIR/ratatui--normal--80x24.ansi  and  OUT_DIR/ratatui--normal--120x30.ansi
# DEPTH = truecolor (default) | 256 | 16.  Needs: cargo (Rust >= 1.88, edition 2024), python3. Honors CARGO_HOME/CARGO_TARGET_DIR.
# A theme ID needs SKILL_DIR=/path/to/tui-design (or this starter still inside the skill); a JSON path does not.
set -euo pipefail
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
command -v cargo >/dev/null || { echo "cargo not found (need Rust >= 1.88; rustup is user-level)" >&2; exit 2; }
tmp=$(mktemp -d "${TMPDIR:-/tmp}/fleet-rt.XXXXXX"); trap 'rm -rf "$tmp"' EXIT
mkdir -p "$out"
mkdir "$tmp/src"; cp "$here"/Cargo.toml "$tmp/"; cp "$here"/src/*.rs "$tmp/src/"; cp "$here"/theme.json "$tmp/"
if [ -f "$theme" ]; then cp "$theme" "$tmp/theme.json"; else skill=$(find_skill) || exit 2; python3 "$skill/scripts/export_theme.py" "$theme" --target json -o "$tmp/theme.json"; fi
( cd "$tmp" && CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-$tmp/target}" cargo build --quiet --release )
bin="${CARGO_TARGET_DIR:-$tmp/target}/release/fleet"
for size in 80x24 120x30; do
  "$bin" --frame --cols "${size%x*}" --rows "${size#*x}" --theme "$tmp/theme.json" --depth "$depth" > "$out/ratatui--normal--$size.ansi"
  echo "wrote $out/ratatui--normal--$size.ansi"
done
