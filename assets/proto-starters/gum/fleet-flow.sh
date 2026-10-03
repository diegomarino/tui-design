#!/usr/bin/env bash
# fleet-flow.sh [theme.json] [--yes] - the idiomatic gum flow for the Fleet domain:
#   gum choose a service -> gum confirm the restart -> gum spin while it "runs" -> styled result line.
# Linear prompts, one at a time: gum composes steps in a shell script, it does not keep a screen.
# --yes skips the confirm prompt (for scripted runs).
set -eo pipefail
here=$(cd "$(dirname "$0")" && pwd)
theme=$here/theme.json yes=0
for a in "$@"; do case $a in --yes) yes=1 ;; *) theme=$a ;; esac; done
. "$here/lib.sh"
load_theme "$theme" "${DEPTH:-truecolor}" || exit 2
gum_env                                   # GUM_CHOOSE_* / GUM_CONFIRM_* / GUM_SPIN_* from the tokens

svc=$(gum choose --header "Services (6)" --cursor "❯ " --height 8 \
  "● api-gateway   running" "● auth          running" "▲ billing       degraded" "✗ search        failed" \
  "● worker        running" "· cron          stopped") || exit 1
name=$(echo "$svc" | awk '{print $2}')
if [ "$yes" = 1 ] || gum confirm "Restart $name?"; then
  gum spin --spinner dot --title "Restarting $name…" -- sleep 2
  echo "$(S 'fg=status.success' '✓') $(S 'fg=fg.default' "restarted $name") $(S 'fg=fg.faint' '· just now')"
else
  echo "$(S 'fg=fg.faint' "cancelled · $name left running")"
fi
