//! Theme: flat resolved theme JSON -> a `Theme` struct of ready-made `Style`s
//! (the ratatui `examples/apps/demo2/src/theme.rs` pattern: one Style per UI role).
//! All colors come from semantic tokens; view code never writes a hex value.

use std::collections::HashMap;

use ratatui::style::{Color, Modifier, Style};
use serde::Deserialize;

/// Embedded default (catppuccin-mocha), produced by
/// `python3 $SKILL_DIR/scripts/export_theme.py catppuccin-mocha --target json -o theme.json`.
pub const DEFAULT_JSON: &str = include_str!("../theme.json");

#[derive(Deserialize)]
pub struct ThemeFile {
    pub tokens: HashMap<String, String>,
    #[serde(default)]
    pub ansi16: HashMap<String, String>, // token -> "<0..15|default|reverse|bg> [bold|dim|underline]"
}

pub fn hex(s: &str) -> Color {
    let v = u32::from_str_radix(s.trim_start_matches('#'), 16).unwrap_or(0xcccccc);
    Color::Rgb((v >> 16) as u8, (v >> 8) as u8, v as u8)
}

/// How tokens become `Style`s. TrueColor/256: the token's hex (Ratatui keeps `Color::Rgb`, the
/// output writer downsamples). Ansi16: the theme's per-token `ansi16` spec, i.e. a *semantic*
/// mapping onto the terminal's own palette, not a nearest-color guess. `bg` (fg tokens only) means text in
/// the terminal background color on the fill: drawn as the fill's slot as fg + REVERSED (see `fg_on`).
pub struct Resolver<'a> {
    file: &'a ThemeFile,
    ansi16: bool,
}

impl Resolver<'_> {
    /// (color, modifiers, is_bg_text) of a token's ansi16 spec.
    fn spec(&self, k: &str) -> (Color, Modifier, bool) {
        let spec = self.file.ansi16.get(k).map_or("default", |s| s.as_str());
        let mut it = spec.split_whitespace();
        let mut bg_text = false;
        let color = match it.next() {
            Some("reverse") => return (Color::Reset, Modifier::REVERSED, false),
            Some("bg") => {
                bg_text = true;
                Color::Reset
            }
            Some(n) => n.parse::<u8>().map_or(Color::Reset, Color::Indexed), // "default" -> Reset
            None => Color::Reset,
        };
        let mut m = Modifier::empty();
        for a in it {
            m |= match a {
                "bold" => Modifier::BOLD,
                "dim" => Modifier::DIM,
                "underline" => Modifier::UNDERLINED,
                _ => Modifier::empty(),
            };
        }
        (color, m, bg_text)
    }
    fn hex(&self, k: &str) -> Color {
        hex(self.file.tokens.get(k).or_else(|| self.file.tokens.get("fg.default")).map_or("#cccccc", |s| s))
    }
    /// Foreground style for a token.
    pub fn fg(&self, k: &str) -> Style {
        if !self.ansi16 {
            return Style::new().fg(self.hex(k));
        }
        let (c, m, _) = self.spec(k);
        Style::new().fg(c).add_modifier(m) // Reset is explicit so it overrides inherited colors
    }
    /// Foreground token drawn on the fill token `on` (fg + bg in one style). Only differs in 16-color
    /// mode for a `bg` spec: the fill's slot becomes the fg and the cell is REVERSED, so the text takes
    /// the terminal background color on the fill.
    pub fn fg_on(&self, k: &str, on: &str) -> Style {
        if self.ansi16 {
            let (_, m, bg_text) = self.spec(k);
            if bg_text {
                let (fill, _, _) = self.spec(on);
                return Style::new().fg(fill).bg(Color::Reset).add_modifier(m | Modifier::REVERSED);
            }
        }
        self.fg(k).patch(self.bg(on))
    }
    /// Background style for a token.
    pub fn bg(&self, k: &str) -> Style {
        if !self.ansi16 {
            return Style::new().bg(self.hex(k));
        }
        let (c, m, _) = self.spec(k);
        Style::new().bg(c).add_modifier(m)
    }
    pub fn reverse_selection(&self) -> bool {
        self.ansi16 && self.spec("selection.bg").1.contains(Modifier::REVERSED)
    }
}

pub struct Theme {
    pub base: Style, // paints bg.base under everything
    pub header: Style,
    pub header_app: Style,
    pub header_sep: Style,
    pub tab_active: Style,
    pub tab_inactive: Style,
    pub border_focus: Style,
    pub border_default: Style,
    pub title: Style,
    pub row_selected: Style,          // bg only: spans keep their own fg (List applies it on top); 16-color
                                      // selection.bg = "reverse" adds REVERSED to each cell, so every segment
                                      // is inverted with its own fg spec and bold, like the mock
    pub row_selected_inactive: Style, // same, for an unfocused pane
    pub cursor: Style,
    pub name: Style,
    pub name_faint: Style,
    pub muted: Style,
    pub faint: Style,
    pub text: Style,
    pub success: Style,
    pub warning: Style,
    pub error: Style,
    pub ramp_low: Style,
    pub ramp_mid: Style,
    pub ramp_high: Style,
    pub footer: Style,
    pub key: Style,
    pub key_desc: Style,
    pub sel_fg: Style, // selection.fg + bold, for text on the selected row
    pub sel_fg_inactive: Style, // same in an unfocused pane (16-color reverse selection: fg.default + bold, no inversion)
}

impl Theme {
    pub fn new(file: &ThemeFile, ansi16: bool) -> Self {
        let r = Resolver { file, ansi16 };
        let band = |k: &str| r.fg_on(k, "statusbar.bg");
        let bold = |s: Style| s.add_modifier(Modifier::BOLD);
        Self {
            base: r.fg_on("fg.default", "bg.base"),
            header: band("statusbar.fg"),
            header_app: bold(band("accent.primary")),
            header_sep: band("border.default"),
            // tab.active.bg falls back to bg.raised in the theme export
            tab_active: bold(r.fg_on("tab.active.fg", "tab.active.bg")),
            tab_inactive: band("tab.inactive.fg"),
            border_focus: r.fg("border.focus"),
            border_default: r.fg("border.default"),
            title: bold(r.fg("fg.title")),
            row_selected: r.bg("selection.bg"),
            row_selected_inactive: r.bg("selection.inactive.bg"),
            cursor: bold(r.fg("accent.primary")),
            name: r.fg("fg.default"),
            name_faint: r.fg("fg.faint"),
            muted: r.fg("fg.muted"),
            faint: r.fg("fg.faint"),
            text: r.fg("fg.default"),
            success: r.fg("status.success"),
            warning: r.fg("status.warning"),
            error: r.fg("status.error"),
            ramp_low: r.fg("ramp.low"),
            ramp_mid: r.fg("ramp.mid"),
            ramp_high: r.fg("ramp.high"),
            footer: band("statusbar.fg"),
            key: bold(band("keyhint.key")),
            key_desc: band("keyhint.desc"),
            sel_fg: bold(r.fg("selection.fg")),
            sel_fg_inactive: if r.reverse_selection() { bold(r.fg("fg.default")) } else { bold(r.fg("selection.fg")) },
        }
    }
}
