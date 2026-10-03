# Credits

## gfargo/tui-design-skill

[gfargo/tui-design-skill](https://github.com/gfargo/tui-design-skill) (MIT) is an earlier agent skill for
terminal interfaces. These ideas were adopted from it and rewritten in this skill's own words and structure; no
file or paragraph was copied:

- **product shapes**: full-screen session, inline picker, one-shot CLI, plugin inside a host
  (`references/layout-archetypes.md`);
- **the two review reflexes**: a countable clutter audit and the floor test at 80×24 and a 60-column split
  (`references/audit-quick.md`, `references/audit-checklist.md`);
- **the lifecycle contract** and **test pyramid** (`references/lifecycle.md`);
- **the review order**: findings ordered by user harm;
- **trigger evals** for the skill description (`evals/trigger-evals.json`);
- **the inline picker** archetype (`references/archetypes/j-inline-picker.md`);
- the shell boundary of `references/cli-contract.md` (exit codes, SIGPIPE, TTY checks, cd on exit) follows gaps
  found in a comparison with that skill.

## Color schemes

The theme files in `skills/tui-design/references/themes/` contain color values taken from each scheme's
official sources; token mappings, 16-color fallbacks and notes are this project's. Each theme JSON records its
sources and license in its `license` and `sources` fields. Licenses below were checked against the upstream
repositories (GitHub license detection and the files themselves) on 2026-10-03.

| Scheme | Upstream used | License found |
|---|---|---|
| Catppuccin (Latte, Frappé, Macchiato, Mocha) | [catppuccin/palette](https://github.com/catppuccin/palette), [catppuccin/kitty](https://github.com/catppuccin/kitty), [style guide](https://github.com/catppuccin/catppuccin) | MIT |
| Dracula | [dracula/dracula-theme](https://github.com/dracula/dracula-theme), [dracula/kitty](https://github.com/dracula/kitty) | MIT |
| Dracula Alucard | spec in [dracula/draculatheme.com](https://github.com/dracula/draculatheme.com) | **unclear**: that repository has no LICENSE file and no license field; the Dracula project's other repositories are MIT |
| Everforest (Dark, Light) | [sainnhe/everforest](https://github.com/sainnhe/everforest) | MIT |
| Gruvbox (Dark, Light) | [morhetz/gruvbox](https://github.com/morhetz/gruvbox), [morhetz/gruvbox-contrib](https://github.com/morhetz/gruvbox-contrib) | **unclear**: `package.json` of morhetz/gruvbox says `"license": "MIT"`, but neither repository has a LICENSE file |
| Kanagawa (Wave, Dragon, Lotus) | [rebelot/kanagawa.nvim](https://github.com/rebelot/kanagawa.nvim) | MIT |
| Nord | [nordtheme/nord](https://github.com/nordtheme/nord), [nordtheme/alacritty](https://github.com/nordtheme/alacritty) | MIT |
| One Dark | [joshdick/onedark.vim](https://github.com/joshdick/onedark.vim) | MIT |
| One Light | [atom/one-light-syntax](https://github.com/atom/one-light-syntax) | MIT |
| Rosé Pine (main, Moon, Dawn) | [rose-pine/palette](https://github.com/rose-pine/palette), [rose-pine/kitty](https://github.com/rose-pine/kitty) | MIT |
| Solarized (Dark, Light) | [altercation/solarized](https://github.com/altercation/solarized), [solarized/xresources](https://github.com/solarized/xresources) | MIT, Copyright (c) 2011 Ethan Schoonover |
| Tokyo Night (Night, Storm, Moon, Day) | [folke/tokyonight.nvim](https://github.com/folke/tokyonight.nvim) (`extras/`) | Apache-2.0 for the repository; the generated `extras/kitty` files used here carry a `license: MIT` header. Only color values are used |

Color values are arguably facts rather than creative expression; they are credited here regardless.

## Other material

- **Exemplar TUIs** studied and cited with short quotes and links: k9s, lazygit, lazydocker, gitui, yazi, btop,
  helix. The screenshot corpus in `references/exemplars.md` lists URLs only; no screenshot is redistributed.
- **Frameworks** whose documentation is cited with short quotes and links: Ink, Textual, Bubble Tea (and Lip
  Gloss, Bubbles, Huh), Ratatui, gum. The starters in `assets/proto-starters/` depend on them but vendor no code.
- [Command Line Interface Guidelines](https://clig.dev) and the framework and terminal documentation linked from
  each reference, quoted briefly with sources.
- `tests/fixtures/lazygit-120x30.ansi` is a capture of [lazygit](https://github.com/jesseduffield/lazygit) (MIT)
  running on a throwaway repository, used to calibrate the screenshot tools.
- [herdr](https://github.com/herdrdev/herdr), tmux, Neovim, k9s and lazygit are named as example hosts for
  plugins; no code from them is included.
- The skill is packaged for the [skills CLI](https://github.com/vercel-labs/skills) (`npx skills`).
