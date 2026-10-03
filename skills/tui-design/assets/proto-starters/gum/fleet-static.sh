#!/usr/bin/env bash
# fleet-static.sh [--cols N] [--rows N] [--theme theme.json] [--depth truecolor|256|16]
# ONE static Fleet frame built only from `gum style` + `gum join`, printed as exactly --rows lines.
# gum cannot make a live multi-pane app (see README); this is the closest static equivalent.
set -eo pipefail
here=$(cd "$(dirname "$0")" && pwd)
cols=80 rows=24 theme=$here/theme.json depth=truecolor
while [ $# -gt 0 ]; do
  case $1 in
    --cols) cols=$2; shift 2 ;; --rows) rows=$2; shift 2 ;; --theme) theme=$2; shift 2 ;;
    --depth) depth=$2; shift 2 ;; --frame) shift ;;   # --frame accepted for parity with the other starters
    *) echo "usage: fleet-static.sh [--cols N] [--rows N] [--theme theme.json] [--depth truecolor|256|16]" >&2; exit 2 ;;
  esac
done
export LC_ALL=${LC_ALL:-en_US.UTF-8}   # wc -m counts characters, not bytes
. "$here/lib.sh"
load_theme "$theme" "$depth" || exit 2

if [ "$cols" -lt 80 ] || [ "$rows" -lt 24 ]; then
  msg="Terminal too small — need 80×24, have ${cols}×${rows}"
  top=$(( (rows - 1) / 2 ))
  for ((i = 0; i < rows; i++)); do
    if [ $i -eq $top ]; then S "fg=status.warning" "$(printf '%*s%s%*s' $(( (cols - ${#msg}) / 2 )) '' "$msg" $(( cols - ${#msg} - (cols - ${#msg}) / 2 )) '')"
    else S "" "$(printf '%*s' "$cols" '')"; fi
  done
  exit 0
fi

vw() { printf %s "$1" | sed $'s/\x1b\\[[0-9;]*m//g' | wc -m | tr -d ' '; }   # visible width (all glyphs used here are 1 cell)
rep() { local s=; local i; for ((i = 0; i < $2; i++)); do s="$s$1"; done; printf %s "$s"; }
pad() { printf "%-$2s" "$1"; }
JH() { gum join --horizontal "$@"; }
JV() { gum join --vertical "$@"; }

# --- header band: app name | tabs ........ right-aligned context
hl="$(S 'fg=accent.primary bg=statusbar.bg bold' ' Fleet ')$(S 'fg=border.default bg=statusbar.bg' '│')$(S 'fg=tab.active.fg bg=tab.active.bg bold' ' 1 Services ')$(S 'fg=tab.inactive.fg bg=statusbar.bg' ' 2 Logs  3 Config ')"
hr=$(S 'fg=statusbar.fg bg=statusbar.bg' 'prod-eu · 12:04:31 ')
header=$(JH "$hl" "$(S 'bg=statusbar.bg' "$(rep ' ' $((cols - $(vw "$hl") - $(vw "$hr"))))")" "$hr")

# --- left box: Services (6). gum borders cannot carry a title, so the title is the first content line.
row() { # row GLYPH_TOKEN GLYPH NAME_TOKEN NAME WORD_TOKEN WORD [BG_TOKEN] [CURSOR]
  local bg=${7:+bg=$7} cur=${8:- }
  local b=${7:-bg.base}
  printf '%s%s%s%s%s%s' "$(S "bg=$b" " ")" "$(S "fg=accent.primary bold $bg" "$cur")" "$(S "bg=$b" " ")" \
    "$(S "fg=$1 $bg" "$2")" "$(S "bg=$b" " ")" "$(S "fg=$3 $bg ${9:-}" "$(pad "$4" 14)")$(S "fg=$5 $bg" "$(pad "$6" 10)")$(S "bg=$b" " ")"
}
left_content=$(printf '%s\n' \
  "$(S 'fg=fg.title bold' ' Services (6)')" \
  "$(row status.success ● selection.fg api-gateway status.success running selection.bg ❯ bold)" \
  "$(row status.success ● fg.default auth fg.muted running)" \
  "$(row status.warning ▲ fg.default billing status.warning degraded)" \
  "$(row status.error ✗ fg.default search status.error failed)" \
  "$(row status.success ● fg.default worker fg.muted running)" \
  "$(row fg.faint · fg.faint cron fg.faint stopped)")
body_h=$((rows - 3))
left=$(gum style --border rounded --border-foreground "$(_color fg border.focus; echo "${C:-}")" --background "$(_color bg bg.base; echo "${C:-}")" \
  --border-background "$(_color bg bg.base; echo "${C:-}")" --width 32 --height "$body_h" "$left_content")

# --- right box: api-gateway detail
inner=$((cols - 32 - 2)); bw=$((inner - 26)); [ $bw -lt 10 ] && bw=10; [ $bw -gt 40 ] && bw=40
lab() { S 'fg=fg.muted' " $(pad "$1" 10)"; }
gauge() { # gauge LABEL PCT RAMP_TOKEN
  local n=$(( $2 * bw / 100 ))
  printf '%s%s%s%s' "$(lab "$1")" "$(S "fg=$3" "$(rep █ $n)")" "$(S 'fg=fg.faint' "$(rep ░ $((bw - n)))")" "$(S 'fg=fg.default' " $(pad "$2%" 3)")"
}
ev() { printf '%s%s%s' "$(S 'fg=fg.faint' " $(pad "$1" 7)")" "$(S "fg=$2" "$3")" "$(S "fg=${4:-fg.default}" " $5")"; }
right_content=$(printf '%s\n' \
  "$(S 'fg=fg.title bold' ' api-gateway')" \
  "$(lab Status)$(S 'fg=status.success' '● running')$(S 'fg=fg.muted' ' · 3/3 replicas')" \
  "$(lab Version)$(S 'fg=fg.default' v2.4.1)" \
  "$(lab Uptime)$(S 'fg=fg.default' '6d 4h')" \
  "$(S '' ' ')" \
  "$(gauge CPU 31 ramp.low)" "$(gauge Memory 68 ramp.mid)" "$(gauge Errors 92 ramp.high)" \
  "$(S '' ' ')" \
  "$(S 'fg=fg.title bold' ' Recent events')" \
  "$(ev 12:01 status.success ✓ fg.default 'deploy v2.4.1 finished')" \
  "$(ev 11:58 status.warning ▲ fg.default 'p95 latency 820 ms')" \
  "$(ev 11:40 fg.faint · fg.muted 'scaled 2 → 3 replicas')" \
  "$(ev 11:02 status.error ✗ fg.default 'health check timeout')")
right=$(gum style --border rounded --border-foreground "$(_color fg border.default; echo "${C:-}")" --background "$(_color bg bg.base; echo "${C:-}")" \
  --border-background "$(_color bg bg.base; echo "${C:-}")" --width $((cols - 32)) --height "$body_h" "$right_content")
body=$(JH "$left" "$right")

# --- message line + footer key hints
msgl="$(S '' ' ')$(S 'fg=status.success' '✓')$(S 'fg=fg.default' ' deployed api-gateway v2.4.1')$(S 'fg=fg.faint' ' · 2m ago')"
message=$(JH "$msgl" "$(S '' "$(rep ' ' $((cols - $(vw "$msgl"))))")")
k() { S 'fg=keyhint.key bg=statusbar.bg bold' "$1"; }
d() { S 'fg=keyhint.desc bg=statusbar.bg' " $1  "; }
fl="$(S 'bg=statusbar.bg' ' ')$(k '↑↓')$(d select)$(k enter)$(d open)$(k /)$(d filter)$(k r)$(d restart)$(k tab)$(d pane)"
fr="$(k '?')$(d help)$(k q)$(S 'fg=keyhint.desc bg=statusbar.bg' ' quit ')"
footer=$(JH "$fl" "$(S 'bg=statusbar.bg' "$(rep ' ' $((cols - $(vw "$fl") - $(vw "$fr"))))")" "$fr")

JV "$header" "$body" "$message" "$footer" | head -n "$rows"
