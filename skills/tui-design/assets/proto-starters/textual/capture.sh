#!/usr/bin/env bash
# capture.sh [THEME_ID_OR_JSON] [OUT_DIR] [DEPTH]      (defaults: catppuccin-mocha, ./frames, truecolor)
#   DEPTH=256 ./capture.sh catppuccin-latte out/       (DEPTH may also be the third argument or the env var)
# Writes OUT_DIR/textual--normal--80x24.ansi and OUT_DIR/textual--normal--120x30.ansi.
# Uses `uv run` (project-local .venv, created on first run; no global installs).
# A theme ID needs SKILL_DIR=/path/to/tui-design (or this starter still inside the skill); a JSON path does not.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Skill lookup, needed only to turn a theme ID into JSON: $SKILL_DIR first, then the relative path
# (works when this starter still sits inside the skill). Copied starters need SKILL_DIR.
find_skill() {
  local c
  for c in "${SKILL_DIR:-}" "$HERE/../../.."; do
    if [ -n "$c" ] && [ -f "$c/scripts/export_theme.py" ]; then (cd "$c" && pwd); return 0; fi
  done
  echo "capture.sh: cannot find the tui-design skill (scripts/export_theme.py). Set SKILL_DIR=/path/to/tui-design," >&2
  echo "            or pass a theme JSON file instead of a theme ID." >&2
  return 1
}
THEME="${1:-catppuccin-mocha}"
OUT="${2:-frames}"
DEPTH="${3:-${DEPTH:-truecolor}}"
command -v uv >/dev/null || { echo "uv not found: brew install uv" >&2; exit 2; }
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
TJSON="$(mktemp "${TMPDIR:-/tmp}/fleet-theme.XXXXXX")"
trap 'rm -f "$TJSON"' EXIT
if [ -f "$THEME" ]; then cp "$THEME" "$TJSON"; else SKILL="$(find_skill)" || exit 2; python3 "$SKILL/scripts/export_theme.py" "$THEME" --target json -o "$TJSON"; fi
for size in 80x24 120x30; do
  cols="${size%x*}"; rows="${size#*x}"
  (cd "$HERE" && uv run python -m fleet --frame --cols "$cols" --rows "$rows" \
      --theme "$TJSON" --depth "$DEPTH") > "$OUT/textual--normal--$size.ansi"
  echo "wrote $OUT/textual--normal--$size.ansi"
done
