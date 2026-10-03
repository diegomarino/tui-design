# Getting started

## Install

The [skills CLI](https://github.com/vercel-labs/skills) installs it for any agent that loads Agent Skills
(Claude Code, Codex, Cursor and others):

```bash
npx skills add diegomarino/tui-design                # into the current project
npx skills add diegomarino/tui-design -g             # for your user, all projects
npx skills add diegomarino/tui-design#v0.1.0         # pinned to a release
npx skills update tui-design
```

**From a clone**, copy the skill folder, and only that folder, to where your agent looks for skills.

```bash
git clone https://github.com/diegomarino/tui-design && cd tui-design
cp -R skills/tui-design .claude/skills/tui-design      # Claude Code, project scope (create .claude/skills first)
cp -R skills/tui-design .agents/skills/tui-design      # Codex and other agents that read .agents/skills
```

For user scope, copy it under your home directory's `.claude/skills/` or `.agents/skills/` instead. A symlink works
too: every script finds its files from its own location.

The installed folder is about 2.1 MB: SKILL.md, references, scripts, theme files, starters and the two test-card
reference PNGs. Evals, tests, docs and tools stay in the repository.

### Requirements

| For | Needs |
|---|---|
| every script | Python 3.11+ (standard library) |
| PNG renders (`ansi_render.py --format png`, `gallery.py --export … png`) | the `rsvg-convert` binary. If it is missing, the script names the package for this OS |
| smaller PNGs (`--quantize`) | `pngquant` (optional) |
| live capture (`capture_tui.sh`) | `tmux` ≥ 3.2 |
| screenshot audits (`prep_screenshot.py`, `sample_colors.py`) | `uv`, which fetches Pillow and numpy per run |
| a proto-starter | its toolchain: Node (Ink), uv (Textual), Go (Bubble Tea), Rust (Ratatui), gum + jq (gum) |

## First prompts

The agent loads the skill from its description, so plain requests work:

- "Sketch a log viewer for our job runner at 80×24 and at a 60-column split."
- "Review this screenshot of my TUI. What would you change first?"
- "I have a tmux popup plugin that shows deploy status. Make me a visual proposal; don't touch the code yet."
- "Map Gruvbox onto my Textual app's theme and check contrast at 16 colors."
- "My Bubble Tea app leaves the terminal broken after Ctrl-Z. Fix it."
- "Audit the running app in `./bin/dash`, measured, not from the code."

The description excludes web and native GUIs, terminal-emulator themes, editor themes and shell prompts.

## What the agent does

The skill routes each request to one of five branches ([SKILL.md](../skills/tui-design/SKILL.md), "Pick the branch"):

| You ask for | Branch | You get |
|---|---|---|
| opinions on a TUI or screenshot | quick review | findings ordered by user harm, each with its evidence and what it requires |
| a new screen, a redesign, mockups | design | three different concepts, then every state × size as linted `.mock` frames, a theme, a design-system document and an [HTML gallery](features/gallery.md) |
| code, a prototype, a theme in code, a rendering fix | build | a [proto-starter](features/starters.md) copied into your project, the theme exported, frames compared with the mockups |
| a measured audit | audit | a [description of the screen](features/audit.md) from a live capture or a screenshot, then a report against a 135-check list |
| only colors | color | a [scheme](features/themes.md) mapped onto 44 tokens, contrast checked at truecolor and 16 colors, exported |

Before any of that it classifies the product (full-screen app, inline picker, one-shot CLI, or plugin inside a host)
and asks what it cannot know: the terminal size, the stack, and for a plugin, what the host can draw. For a
plugin it asks you to run the [test card](features/host-verification.md) inside the host and send a screenshot.

Files go into a working directory (scratch or your project), with the generator script next to the frames. The
agent renders every frame to PNG and looks at it before showing it to you.

Next: [Concepts](concepts.md).
