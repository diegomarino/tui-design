//! Fleet: the tui-design canonical demo screen in Ratatui 0.30.
//!
//!   cargo run                                  interactive: up/down/j/k select, tab pane, r restart, q quit
//!   cargo run -- --frame --cols 120 --rows 30 --theme theme.json --depth truecolor
//!                                              print ONE static ANSI frame (exactly --rows lines) and exit

mod ansi;
mod data;
mod theme;
mod ui;

use ratatui::DefaultTerminal;
use ratatui::Terminal;
use ratatui::backend::TestBackend;
use ratatui::crossterm::event::{self, Event, KeyCode, KeyEventKind, KeyModifiers};

use ansi::Depth;
use theme::{Theme, ThemeFile};
use ui::App;

fn run(terminal: &mut DefaultTerminal, app: &mut App, th: &Theme) -> std::io::Result<()> {
    while !app.quit {
        terminal.draw(|f| ui::render(f, app, th))?; // immediate mode: redraw everything
        if let Event::Key(key) = event::read()? {
            if key.kind != KeyEventKind::Press {
                continue; // Windows also reports releases
            }
            let last = data::SERVICES.len() - 1;
            match key.code {
                KeyCode::Char('q') => app.quit = true,
                KeyCode::Char('c') if key.modifiers.contains(KeyModifiers::CONTROL) => app.quit = true,
                KeyCode::Tab | KeyCode::BackTab => app.focus = 1 - app.focus,
                KeyCode::Up | KeyCode::Char('k') if app.focus == 0 => app.sel = app.sel.saturating_sub(1),
                KeyCode::Down | KeyCode::Char('j') if app.focus == 0 => app.sel = (app.sel + 1).min(last),
                KeyCode::Char('r') => {
                    app.msg = format!("restart requested for {}", data::SERVICES[app.sel].name);
                    app.msg_age = "just now".into();
                }
                _ => {}
            }
        }
    }
    Ok(())
}

fn usage() -> ! {
    eprintln!("usage: fleet [--frame [--cols N] [--rows N] [--depth truecolor|256|16] [--selected I] [--focus-detail]] [--theme theme.json]");
    std::process::exit(2)
}

fn main() {
    let (mut frame, mut cols, mut rows, mut theme_path, mut depth) = (false, 80u16, 24u16, None, "truecolor".to_string());
    let (mut selected, mut focus) = (0usize, 0usize);
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        let mut val = || args.next().unwrap_or_else(|| usage());
        match a.as_str() {
            "--frame" => frame = true,
            "--cols" => cols = val().parse().unwrap_or_else(|_| usage()),
            "--rows" => rows = val().parse().unwrap_or_else(|_| usage()),
            "--theme" => theme_path = Some(val()),
            "--depth" => depth = val(),
            "--selected" => selected = val().parse().unwrap_or_else(|_| usage()),
            "--focus-detail" => focus = 1,
            _ => usage(),
        }
    }
    let json = match &theme_path {
        Some(p) => std::fs::read_to_string(p).unwrap_or_else(|e| {
            eprintln!("{p}: {e}");
            std::process::exit(2)
        }),
        None => theme::DEFAULT_JSON.to_string(),
    };
    let file: ThemeFile = serde_json::from_str(&json).unwrap_or_else(|e| {
        eprintln!("theme json: {e}");
        std::process::exit(2)
    });
    let th = Theme::new(&file, depth == "16");
    let mut app = App { sel: selected.min(data::SERVICES.len() - 1), focus, ..App::default() };

    if !frame {
        ratatui::run(|terminal| run(terminal, &mut app, &th)).expect("terminal error"); // raw mode + alt screen + panic hook
        return;
    }
    let depth = match depth.as_str() {
        "truecolor" => Depth::TrueColor,
        "256" => Depth::Ansi256,
        "16" => Depth::Ansi16,
        _ => usage(),
    };
    let mut terminal = Terminal::new(TestBackend::new(cols, rows)).unwrap();
    terminal.draw(|f| ui::render(f, &app, &th)).unwrap();
    print!("{}", ansi::buffer_to_ansi(terminal.backend().buffer(), &depth));
}
