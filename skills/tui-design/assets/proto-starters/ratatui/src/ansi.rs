//! Headless frame capture: render into a `TestBackend` buffer, then serialize the cells as
//! ANSI text (wide-char safe) with our own color-depth mapping. Ratatui itself always keeps
//! `Color::Rgb`; downsampling is a property of the *output*, so it lives here.

use std::fmt::Write as _;

use ratatui::buffer::Buffer;
use ratatui::style::{Color, Modifier};
use ratatui::text::Span;

#[derive(Clone)]
pub enum Depth {
    TrueColor,
    Ansi256,
    /// 16 colors: the Theme is built from the per-token `ansi16` specs, so cells already carry
    /// `Color::Indexed(0..15)`/`Reset`; an `Rgb` that slips through is mapped to the 256 cube.
    Ansi16,
}

fn dist(a: [u8; 3], b: [u8; 3]) -> i32 {
    (0..3).map(|i| (a[i] as i32 - b[i] as i32).pow(2)).sum()
}

fn nearest_256(c: [u8; 3]) -> u8 {
    let cube = [0u8, 95, 135, 175, 215, 255];
    let (mut best, mut bd) = (16u8, i32::MAX);
    for i in 16..=255u8 {
        let rgb = if i < 232 {
            let n = i - 16;
            [cube[(n / 36) as usize], cube[((n / 6) % 6) as usize], cube[(n % 6) as usize]]
        } else {
            let g = 8 + 10 * (i - 232);
            [g, g, g]
        };
        let d = dist(c, rgb);
        if d < bd {
            (best, bd) = (i, d);
        }
    }
    best
}

/// Append `;<params>` for one color. `fg` selects 30/90/38 vs 40/100/48 families.
fn sgr_color(out: &mut String, c: Color, fg: bool, depth: &Depth) {
    let base = if fg { 30 } else { 40 };
    let c = match c {
        Color::Reset => return,
        Color::Rgb(r, g, b) => match depth {
            Depth::TrueColor => {
                let _ = write!(out, ";{};2;{r};{g};{b}", base + 8);
                return;
            }
            Depth::Ansi256 | Depth::Ansi16 => {
                let _ = write!(out, ";{};5;{}", base + 8, nearest_256([r, g, b]));
                return;
            }
        },
        other => other,
    };
    let code = match c {
        Color::Black => base,
        Color::Red => base + 1,
        Color::Green => base + 2,
        Color::Yellow => base + 3,
        Color::Blue => base + 4,
        Color::Magenta => base + 5,
        Color::Cyan => base + 6,
        Color::Gray => base + 7,
        Color::DarkGray => base + 60,
        Color::LightRed => base + 61,
        Color::LightGreen => base + 62,
        Color::LightYellow => base + 63,
        Color::LightBlue => base + 64,
        Color::LightMagenta => base + 65,
        Color::LightCyan => base + 66,
        Color::White => base + 67,
        Color::Indexed(i) if i < 8 => base + i as u16,
        Color::Indexed(i) if i < 16 => base + 60 + (i as u16 - 8),
        Color::Indexed(i) => {
            let _ = write!(out, ";{};5;{i}", base + 8);
            return;
        }
        _ => return,
    };
    let _ = write!(out, ";{code}");
}

/// One line per buffer row, each ending in `ESC[0m\n`. Exactly `area.height` lines.
pub fn buffer_to_ansi(buf: &Buffer, depth: &Depth) -> String {
    let mut out = String::new();
    let a = buf.area;
    for y in a.top()..a.bottom() {
        let mut last = None;
        let mut skip = 0usize;
        for x in a.left()..a.right() {
            let cell = &buf[(x, y)];
            if skip > 0 {
                skip -= 1; // trailing cells of a wide glyph
                continue;
            }
            let key = (cell.fg, cell.bg, cell.modifier);
            if last != Some(key) {
                out.push_str("\x1b[0");
                sgr_color(&mut out, cell.fg, true, depth);
                sgr_color(&mut out, cell.bg, false, depth);
                for (flag, code) in [
                    (Modifier::BOLD, 1),
                    (Modifier::DIM, 2),
                    (Modifier::ITALIC, 3),
                    (Modifier::UNDERLINED, 4),
                    (Modifier::REVERSED, 7),
                    (Modifier::CROSSED_OUT, 9),
                ] {
                    if cell.modifier.contains(flag) {
                        let _ = write!(out, ";{code}");
                    }
                }
                out.push('m');
                last = Some(key);
            }
            out.push_str(cell.symbol());
            let w = Span::raw(cell.symbol()).width();
            if w > 1 {
                skip = w - 1;
            }
        }
        out.push_str("\x1b[0m\n");
    }
    out
}
