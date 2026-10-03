#!/usr/bin/env bash
# Pre-publish check: fail on private markers anywhere in the repo.
#
#   bash tools/check_public.sh        exit 0 = clean, 1 = hits (printed as file:line: text)
#
# Looks for: the owner's name (the GitHub handle is allowed where the public install or the published
# gallery is named: LICENSE, README.md, CREDITS.md, docs/getting-started.md, CHANGELOG.md and
# docs/features/gallery.md), local paths (/Users/, /home/<user>/, /private/tmp, temp session dirs), private
# hostnames (*.ts.net), e-mail addresses, agent session ids, API keys and tokens, private project names, and
# files that must never ship (raw eval runs, export state, caches, local skill copies). Text files are grepped;
# binary files (PNGs) are scanned for embedded paths and names. Extend the patterns below rather than bypassing
# the check.
set -u
cd "$(dirname "$0")/.." || exit 2

SELF="tools/check_public.sh"
# Files allowed to carry fake secrets (test fixtures of the redaction code), and the pattern allowed there.
FAKE_SECRET_FILES="tests/test_export_results.py tests/test_eval_harness.py tests/test_behavior_evals.py"
FAKE_SECRET_RX='pk-lf-(public|test|fake)|sk-lf-(secret|test|fake)|FAKE|fake|dummy|placeholder|example'
# Files where the GitHub handle may appear.
HANDLE_FILES="LICENSE README.md CREDITS.md docs/getting-started.md CHANGELOG.md docs/features/gallery.md"
HANDLE="diegomarino"

# Case-insensitive markers (owner, paths, hosts, private projects).
PRIVATE_RX='diego|marino|petalo|\.ts\.net|tailscale|batutas|itemize|marplanner|lucasquiz|gh-delta|(^|[^a-z])orca([^a-z]|$)'
# Local paths (case-sensitive: /Home/End in prose is not a path).
PATH_RX='/Users/|/home/[a-z][a-z0-9_-]*/|/private/tmp|/var/folders/|claude-[0-9]{3}/'
# Secrets and ids (case-sensitive).
SECRET_RX='sk-or-v1-|sk-ant-|sk-proj-|sk-[A-Za-z0-9_-]{20,}|pk-lf-|sk-lf-|ghp_[A-Za-z0-9]{20,}|github_pat_|AKIA[0-9A-Z]{16}|xox[bap]-|eyJ[A-Za-z0-9_-]{10,}|(session|rollout)[ _-]?(id)?[ :=_-]*[0-9a-f]{8}-[0-9a-f]{4}-'
EMAIL_RX='[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}'
EMAIL_OK_RX='@(example\.(com|org|net|invalid)|users\.noreply\.github\.com)|@[0-9]+\.[0-9]+|noreply@|git@github\.com'

hits=0
report() { printf '%s\n' "$1"; hits=$((hits + 1)); }

in_list() { case " $2 " in *" $1 "*) return 0;; esac; return 1; }

files=$(git ls-files --cached --others --exclude-standard 2>/dev/null || find . -type f -not -path './.git/*' | sed 's|^\./||')

while IFS= read -r f; do
  [ -f "$f" ] || continue
  [ "$f" = "$SELF" ] && continue
  if grep -Iq . "$f" 2>/dev/null || [ ! -s "$f" ]; then
    # text file
    while IFS= read -r line; do
      text=${line#*:}
      if in_list "$f" "$HANDLE_FILES"; then
        text=$(printf '%s' "$text" | sed -E "s/@?$HANDLE//g")
      fi
      printf '%s' "$text" | grep -Eiq "$PRIVATE_RX" && report "$f:$line"
    done < <(grep -Ein "$PRIVATE_RX" "$f" 2>/dev/null)
    while IFS= read -r line; do report "$f:$line  [local path]"; done < <(grep -En "$PATH_RX" "$f" 2>/dev/null)
    while IFS= read -r line; do
      if in_list "$f" "$FAKE_SECRET_FILES" && printf '%s' "$line" | grep -Eq "$FAKE_SECRET_RX"; then continue; fi
      report "$f:$line  [secret/id pattern]"
    done < <(grep -En "$SECRET_RX" "$f" 2>/dev/null)
    while IFS= read -r line; do
      rest=$(printf '%s' "$line" | grep -Eo "$EMAIL_RX" | grep -Ev "$EMAIL_OK_RX")
      [ -n "$rest" ] && report "$f:$line  [e-mail]"
    done < <(grep -En "$EMAIL_RX" "$f" 2>/dev/null)
  else
    # binary file: embedded paths, hosts, names
    if LC_ALL=C grep -aEiq '/Users/|/home/[a-z]+/|/private/tmp|\.ts\.net|diego|marino|batutas|itemize' "$f"; then
      report "$f: binary file holds a private path or name"
    fi
  fi
done <<< "$files"

# Files and folders that must never ship.
while IFS= read -r f; do
  case "$f" in
    *__pycache__*|*.pyc|*.events.jsonl*|*export-state.json|.claude/*|*/.claude/*|.agents/*|*/.agents/*|.remember/*|evals/runs/*|*.DS_Store|*prices-cache.json)
      report "$f  [must not be published]";;
  esac
done <<< "$files"

if [ "$hits" -gt 0 ]; then
  echo "check_public: $hits hit(s)" >&2
  exit 1
fi
echo "check_public: clean ($(printf '%s\n' "$files" | grep -c .) files checked)"
