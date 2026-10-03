"""python -m fleet [--frame --cols N --rows N] [--theme theme.json|ID] [--depth truecolor|256|16]"""
from __future__ import annotations

import argparse
import asyncio
import io
import sys
from pathlib import Path

from rich.console import Console

from .app import FleetApp
from .theme import load_tokens

DEFAULT_THEME = Path(__file__).resolve().parent.parent / "theme.json"
COLOR_SYSTEM = {"truecolor": "truecolor", "256": "256", "16": "standard"}


def frame_to_ansi(app: FleetApp, depth: str) -> str:
    """Current screen as ANSI, exactly rows lines. PRIVATE API: App.screen._compositor
    (hence the exact textual== pin). Public alternative: App.export_screenshot() (SVG only)."""
    width, height = app.size
    console = Console(width=width, height=height, file=io.StringIO(), force_terminal=True,
                      color_system=COLOR_SYSTEM[depth], legacy_windows=False, safe_box=False)
    update = app.screen._compositor.render_update(full=True, screen_stack=app._background_screens)
    return "\n".join("".join(strip.render(console) for strip in line) for line in update.strips) + "\n"


async def capture(tokens, cols: int, rows: int) -> str:
    app = FleetApp(tokens)
    async with app.run_test(size=(cols, rows)) as pilot:
        await pilot.pause()
        return frame_to_ansi(app, tokens.depth)


def main() -> int:
    p = argparse.ArgumentParser(prog="fleet", description="Fleet demo screen (Textual).")
    p.add_argument("--frame", action="store_true", help="print one ANSI frame and exit")
    p.add_argument("--cols", type=int, default=80)
    p.add_argument("--rows", type=int, default=24)
    p.add_argument("--theme", default=str(DEFAULT_THEME),
                   help="flat theme JSON path (export_theme.py --target json) or a theme ID (needs SKILL_DIR)")
    p.add_argument("--depth", choices=["truecolor", "256", "16"], default="truecolor")
    a = p.parse_args()
    tokens = load_tokens(a.theme, a.depth)
    if a.frame:
        sys.stdout.write(asyncio.run(capture(tokens, a.cols, a.rows)))
    else:
        FleetApp(tokens).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
