"""Flat resolved theme JSON -> Textual Theme + token lookups.

Input: python3 SKILL_DIR/scripts/export_theme.py ID --target json -o theme.json

Mapping (idiomatic Textual):
  * a registered `Theme` carries the slots Textual understands
      primary/accent <- accent.primary, secondary <- accent.secondary,
      success/warning/error <- status.*, foreground <- fg.default, background <- bg.base,
      surface <- bg.surface, panel <- bg.raised, dark <- appearance
  * every design token additionally becomes a theme *variable* `$tok-<token-with-dashes>`
    (e.g. border.focus -> $tok-border-focus), usable in TCSS. These are the "explicit token
    colors where Textual variables do not cover a token".
  * rich/markup text uses `Tokens.sty(token)` which returns a style string like
    "#a6adc8" (truecolor/256) or "ansi_blue bold" (16-color, from the theme's `ansi16` map).

Depth:
  truecolor / 256 -> hex everywhere (Rich down-samples to 256 at output).
  16              -> `ansi_<name>` colors + App(ansi_color=True): the terminal's own palette.
                     `bg` (fg tokens only) = text in the terminal background color on the fill:
                     drawn as the fill token's slot as foreground + reverse.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from textual.theme import Theme

ANSI_NAMES = [
    "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white",
    "bright_black", "bright_red", "bright_green", "bright_yellow",
    "bright_blue", "bright_magenta", "bright_cyan", "bright_white",
]


def var_name(token: str) -> str:
    return "tok-" + token.replace(".", "-")


class Tokens:
    def __init__(self, data: dict, depth: str = "truecolor") -> None:
        self.data = data
        self.depth = depth  # truecolor | 256 | 16

    @property
    def ansi_mode(self) -> bool:
        return self.depth == "16"

    def _a16(self, token: str) -> tuple[str, set[str]]:
        """Parse '<color> [attrs]' -> (textual color, attrs); `reverse` and `bg` come back as attrs."""
        color, attrs = "ansi_default", set()
        for word in self.data["ansi16"].get(token, "default").split():
            if word.isdigit():
                color = "ansi_" + ANSI_NAMES[int(word)]
            elif word in ("bold", "dim", "underline"):
                attrs.add(word)
            elif word in ("reverse", "bg"):
                attrs.add(word)
        return color, attrs

    def color(self, token: str) -> str:
        """A CSS/markup color for the token ('#rrggbb' or 'ansi_x')."""
        if self.ansi_mode:
            return self._a16(token)[0]
        return self.data["tokens"][token]

    def sty(self, token: str, on: str | None = None, bold: bool = False) -> str:
        """Rich/Textual markup style string for a foreground token (+ optional bg token)."""
        parts: list[str] = []
        attrs: set[str] = set()
        if self.ansi_mode:
            color, attrs = self._a16(token)
            if "bg" in attrs:
                # terminal-background text on the fill: the fill's slot as foreground, then reverse
                color = self._a16(on)[0] if on else "ansi_default"
                attrs = (attrs - {"bg"}) | {"reverse"}
                on = None
            parts.append(color)
        else:
            parts.append(self.data["tokens"][token])
        if bold:
            attrs.add("bold")
        if on:
            if self.ansi_mode and "reverse" in self._a16(on)[1]:
                attrs.add("reverse")
            else:
                parts.append("on " + self.color(on))
        parts.extend(sorted(a for a in attrs if a != "reverse") + (["reverse"] if "reverse" in attrs else []))
        return " ".join(parts)

    def variables(self) -> dict[str, str]:
        return {var_name(t): self.color(t) for t in self.data["tokens"]}


def load_theme_json(arg: str | Path) -> dict:
    """--theme value -> flat theme dict: an existing file is read as-is, anything else is a theme ID
    exported through the skill's export_theme.py (SKILL_DIR env first, then the relative path when this
    starter still sits inside the skill)."""
    p = Path(arg)
    if p.is_file():
        return json.loads(p.read_text())
    if p.suffix.lower() == ".json" or os.sep in str(arg) or "/" in str(arg):
        sys.exit(f"theme file not found: {arg}")
    here = Path(__file__).resolve()
    for root in (os.environ.get("SKILL_DIR"), here.parents[4]):   # fleet/theme.py -> skill root is 4 levels up
        script = Path(root) / "scripts" / "export_theme.py" if root else None
        if script and script.is_file():
            out = subprocess.run([sys.executable, str(script), str(arg), "--target", "json"],
                                 capture_output=True, text=True)
            if out.returncode:
                sys.exit(out.stderr.strip() or f"export_theme.py failed for theme ID {arg!r}")
            return json.loads(out.stdout)
    sys.exit(f"cannot resolve theme ID {arg!r}: the tui-design skill was not found.\n"
             "Set SKILL_DIR=/path/to/tui-design, or pass a theme JSON file to --theme.")


def load_tokens(theme: str | Path, depth: str = "truecolor") -> Tokens:
    return Tokens(load_theme_json(theme), depth)


def make_theme(tk: Tokens) -> Theme:
    t = tk.data["tokens"]
    return Theme(
        name=tk.data["id"],
        primary=t["accent.primary"],
        secondary=t["accent.secondary"],
        accent=t["accent.primary"],
        success=t["status.success"],
        warning=t["status.warning"],
        error=t["status.error"],
        foreground=t["fg.default"],
        background=t["bg.base"],
        surface=t["bg.surface"],
        panel=t["bg.raised"],
        dark=tk.data["appearance"] == "dark",
        variables=tk.variables(),
    )
