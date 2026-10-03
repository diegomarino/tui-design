//! The Fleet screen. Immediate mode: `render` rebuilds every widget each frame from `App`.

use ratatui::Frame;
use ratatui::layout::{Alignment, Constraint, Layout, Rect};
use ratatui::style::Style;
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, BorderType, List, ListItem, ListState, Paragraph};

use crate::data::{SERVICES, Status};
use crate::theme::Theme;

pub const MIN_W: u16 = 80;
pub const MIN_H: u16 = 24;
const LIST_W: u16 = 32; // fixed list pane width; the detail pane takes the rest

pub struct App {
    pub sel: usize,
    pub focus: usize, // 0 = list, 1 = detail
    pub msg: String,
    pub msg_age: String,
    pub quit: bool,
}

impl Default for App {
    fn default() -> Self {
        Self { sel: 0, focus: 0, msg: "deployed api-gateway v2.4.1".into(), msg_age: "2m ago".into(), quit: false }
    }
}

fn pad(s: &str, w: usize) -> String {
    format!("{s:<w$}")
}

fn status_style(th: &Theme, s: Status) -> Style {
    match s {
        Status::Running => th.success,
        Status::Degraded => th.warning,
        Status::Failed => th.error,
        Status::Stopped => th.faint,
    }
}

pub fn render(f: &mut Frame, app: &App, th: &Theme) {
    let area = f.area();
    f.render_widget(Block::new().style(th.base), area); // paint bg.base once, widgets patch on top
    if area.width < MIN_W || area.height < MIN_H {
        let text = format!("Terminal too small — need {MIN_W}×{MIN_H}, have {}×{}", area.width, area.height);
        let [_, mid, _] = Layout::vertical([Constraint::Fill(1), Constraint::Length(1), Constraint::Fill(1)]).areas(area);
        f.render_widget(Paragraph::new(text).style(th.warning).alignment(Alignment::Center), mid);
        return;
    }
    let [header, body, message, footer] =
        Layout::vertical([Constraint::Length(1), Constraint::Fill(1), Constraint::Length(1), Constraint::Length(1)]).areas(area);
    let [left, right] = Layout::horizontal([Constraint::Length(LIST_W), Constraint::Fill(1)]).areas(body);

    render_header(f, header, th);
    render_list(f, left, app, th);
    render_detail(f, right, app, th);
    f.render_widget(
        Line::from(vec![
            Span::raw(" "),
            Span::styled("✓", th.success),
            Span::styled(format!(" {}", app.msg), th.text),
            Span::styled(format!(" · {}", app.msg_age), th.faint),
        ]),
        message,
    );
    render_footer(f, footer, app, th);
}

/// Left part fills the band, right part is a fixed-width column (Layout splits, no manual padding).
fn band(f: &mut Frame, area: Rect, style: Style, left: Line, right: Line) {
    let [l, r] = Layout::horizontal([Constraint::Fill(1), Constraint::Length(right.width() as u16)]).areas(area);
    f.render_widget(Paragraph::new(left).style(style), l);
    f.render_widget(Paragraph::new(right).style(style), r);
}

fn render_header(f: &mut Frame, area: Rect, th: &Theme) {
    let left = Line::from(vec![
        Span::styled(" Fleet ", th.header_app),
        Span::styled("│", th.header_sep),
        Span::styled(" 1 Services ", th.tab_active),
        Span::styled(" 2 Logs ", th.tab_inactive),
        Span::styled(" 3 Config ", th.tab_inactive),
    ]);
    band(f, area, th.header, left, Line::from(Span::styled("prod-eu · 12:04:31 ", th.header)));
}

fn render_footer(f: &mut Frame, area: Rect, app: &App, th: &Theme) {
    let hint = |k: &'static str, d: &'static str| [Span::styled(k, th.key), Span::styled(format!(" {d}  "), th.key_desc)];
    let mut left = vec![Span::raw(" ")];
    let hints: &[(&'static str, &'static str)] = if app.focus == 0 {
        &[("↑↓", "select"), ("enter", "open"), ("/", "filter"), ("r", "restart"), ("tab", "pane")]
    } else {
        &[("r", "restart"), ("tab", "pane")]
    };
    for (k, d) in hints {
        left.extend(hint(k, d));
    }
    let mut right = Vec::new();
    right.extend(hint("?", "help"));
    right.extend([Span::styled("q", th.key), Span::styled(" quit ", th.key_desc)]);
    band(f, area, th.footer, Line::from(left), Line::from(right));
}

/// Rounded box with the title embedded in the top edge (" Title " after "╭─").
fn pane<'a>(title: &str, focused: bool, th: &Theme) -> Block<'a> {
    let bs = if focused { th.border_focus } else { th.border_default };
    Block::bordered()
        .border_type(BorderType::Rounded)
        .border_style(bs)
        .style(th.base)
        .title(Line::from(vec![Span::styled("─", bs), Span::styled(format!(" {title} "), th.title)]))
}

fn render_list(f: &mut Frame, area: Rect, app: &App, th: &Theme) {
    let block = pane(&format!("Services ({})", SERVICES.len()), app.focus == 0, th);
    let inner = block.inner(area);
    f.render_widget(block, area);
    let items: Vec<ListItem> = SERVICES
        .iter()
        .enumerate()
        .map(|(i, s)| {
            let selected = i == app.sel;
            let st = status_style(th, s.status);
            let sel_name = if app.focus == 0 { th.sel_fg } else { th.sel_fg_inactive };
            let (name_style, word_style) = match (selected, s.status) {
                (true, Status::Running) => (sel_name, th.success),
                (true, _) => (sel_name, st),
                (false, Status::Running) => (th.name, th.muted),
                (false, Status::Stopped) => (th.name_faint, st),
                (false, _) => (th.name, st),
            };
            ListItem::new(Line::from(vec![
                Span::raw(" "),
                if selected { Span::styled("❯", th.cursor) } else { Span::raw(" ") },
                Span::raw(" "),
                Span::styled(s.status.glyph(), st),
                Span::raw(" "),
                Span::styled(pad(s.name, 14), name_style),
                Span::styled(pad(s.status.label(), 10), word_style),
            ]))
        })
        .collect();
    // The List only paints the selected row's background; spans keep their own colors.
    let hl = if app.focus == 0 { th.row_selected } else { th.row_selected_inactive };
    f.render_stateful_widget(List::new(items).highlight_style(hl), inner, &mut ListState::default().with_selected(Some(app.sel)));
}

fn render_detail(f: &mut Frame, area: Rect, app: &App, th: &Theme) {
    let svc = &SERVICES[app.sel];
    let block = pane(svc.name, app.focus == 1, th);
    let inner = block.inner(area);
    f.render_widget(block, area);

    let label = |k: &str| Span::styled(pad(k, 10), th.muted);
    let bar_w = (inner.width as usize).saturating_sub(26).clamp(10, 40); // 20 cells at 80 cols
    let gauge = |name: &str, pct: u16| {
        let sty = if pct >= 80 { th.ramp_high } else if pct >= 50 { th.ramp_mid } else { th.ramp_low };
        let n = pct as usize * bar_w / 100;
        Line::from(vec![
            Span::raw(" "),
            label(name),
            Span::styled("█".repeat(n), sty),
            Span::styled("░".repeat(bar_w - n), th.faint),
            Span::styled(format!(" {}", pad(&format!("{pct}%"), 3)), th.text),
        ])
    };
    let mut lines = vec![
        Line::raw(""),
        Line::from(vec![
            Span::raw(" "),
            label("Status"),
            Span::styled(format!("{} {}", svc.status.glyph(), svc.status.label()), status_style(th, svc.status)),
            Span::styled(format!(" · {} replicas", svc.replicas), th.muted),
        ]),
        Line::from(vec![Span::raw(" "), label("Version"), Span::styled(svc.version, th.text)]),
        Line::from(vec![Span::raw(" "), label("Uptime"), Span::styled(svc.uptime, th.text)]),
        Line::raw(""),
        gauge("CPU", svc.cpu),
        gauge("Memory", svc.mem),
        gauge("Errors", svc.errs),
        Line::raw(""),
        Line::from(vec![Span::raw(" "), Span::styled("Recent events", th.title)]),
    ];
    for e in &svc.events {
        let (glyph, gs, ts) = match e.kind {
            "ok" => ("✓", th.success, th.text),
            "warn" => ("▲", th.warning, th.text),
            "err" => ("✗", th.error, th.text),
            _ => ("·", th.faint, th.muted),
        };
        lines.push(Line::from(vec![
            Span::raw(" "),
            Span::styled(pad(e.at, 7), th.faint),
            Span::styled(glyph, gs),
            Span::styled(format!(" {}", e.text), ts),
        ]));
    }
    f.render_widget(Paragraph::new(lines), inner);
}
