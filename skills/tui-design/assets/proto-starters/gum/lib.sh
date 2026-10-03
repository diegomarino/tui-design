# lib.sh - theme tokens -> gum styling. Source it; needs gum >= 2 and jq. Bash 3.2 compatible (macOS).
#   load_theme theme.json [truecolor|256|16]   sets T_<token> / A_<token> variables and the color mode
#   S "fg=status.success bg=selection.bg bold" "text"   one styled span (a gum style call)
#   gum_env                                    export GUM_* variables for gum choose/confirm/spin/...
# Token names are sanitized: "border.focus" -> T_border_focus, "fg.on-accent" -> T_fg_on_accent.

load_theme() {
  local file=$1; DEPTH=${2:-truecolor}
  command -v gum >/dev/null || { echo "gum not found: brew install gum (or a release binary)" >&2; return 2; }
  command -v jq  >/dev/null || { echo "jq not found: brew install jq" >&2; return 2; }
  eval "$(jq -r '(.tokens | to_entries[] | "T_" + (.key | gsub("[.-]"; "_")) + "=" + (.value | @sh)),
                 ((.ansi16 // {}) | to_entries[] | "A_" + (.key | gsub("[.-]"; "_")) + "=" + (.value | @sh))' "$file")"
  # gum/lipgloss emit truecolor and colorprofile downsamples from the environment, so force it.
  export CLICOLOR_FORCE=1
  case $DEPTH in
    truecolor) export COLORTERM=truecolor TERM=${TERM:-xterm-256color} ;;
    256|16)    unset COLORTERM; export TERM=xterm-256color ;;
    *) echo "depth must be truecolor, 256 or 16" >&2; return 2 ;;
  esac
}

_tok() { echo "${1//[.-]/_}"; }

# _color KIND TOKEN -> sets C (color string for gum, may be empty) and A (extra flags), REV=1 when "reverse",
# BGTEXT=1 when an fg token's spec is "bg" (text in the terminal background color on the fill)
_color() {
  local v key; key=$(_tok "$2")
  C=; A=
  if [ "$DEPTH" = 16 ]; then                       # semantic mapping: the theme's ansi16 spec, not nearest-color
    v=A_$key; set -- $1 ${!v:-default}
    case $2 in reverse) REV=1 ;; bg) [ "$1" = fg ] && BGTEXT=1 ;; default) ;; *) C=$2 ;; esac
    if [ "$1" = fg ]; then
      shift 2
      for a in "$@"; do case $a in bold) A="$A --bold" ;; dim) A="$A --faint" ;; underline) A="$A --underline" ;; esac; done
    fi
  else
    v=T_$key; C=${!v}
  fi
}

S() { # S "fg=TOKEN bg=TOKEN bold dim italic underline" TEXT   (defaults: fg.default on bg.base)
  local fgt=fg.default bgt=bg.base w flags= fgc bgc extra= REV=0 BGTEXT=0 out
  for w in $1; do
    case $w in fg=*) fgt=${w#fg=} ;; bg=*) bgt=${w#bg=} ;; bold) flags="$flags --bold" ;; dim) flags="$flags --faint" ;;
               italic) flags="$flags --italic" ;; underline) flags="$flags --underline" ;; esac
  done
  _color fg "$fgt"; fgc=$C; extra=$A
  _color bg "$bgt"; bgc=$C
  # "bg" (16-color): the fill's slot as foreground, then reverse, so the text takes the terminal background
  [ "$BGTEXT" = 1 ] && { fgc=$bgc; bgc=; REV=1; }
  # gum style has no reverse-video flag: wrap its output in SGR 7 ... SGR 0 (lipgloss keeps and ignores it)
  out=$(gum style $flags $extra --foreground "$fgc" --background "$bgc" "$2")
  if [ "$REV" = 1 ]; then printf '\033[7m%s\033[0m\n' "$out"; else printf '%s\n' "$out"; fi
}

gum_env() { # same mapping as export_theme.py --target gum, from the flat JSON tokens
  local t
  t() { local v; v=T_$(_tok "$1"); echo "${!v}"; }
  export GUM_CHOOSE_CURSOR_FOREGROUND=$(t accent.primary) GUM_CHOOSE_SELECTED_FOREGROUND=$(t status.success) \
         GUM_CHOOSE_ITEM_FOREGROUND=$(t fg.default) GUM_CHOOSE_HEADER_FOREGROUND=$(t fg.title) \
         GUM_CONFIRM_PROMPT_FOREGROUND=$(t fg.default) GUM_CONFIRM_SELECTED_FOREGROUND=$(t fg.on-accent) \
         GUM_CONFIRM_SELECTED_BACKGROUND=$(t accent.primary) GUM_CONFIRM_UNSELECTED_FOREGROUND=$(t fg.default) \
         GUM_CONFIRM_UNSELECTED_BACKGROUND=$(t bg.raised) GUM_SPIN_SPINNER_FOREGROUND=$(t accent.primary) \
         GUM_SPIN_TITLE_FOREGROUND=$(t fg.default)
}
