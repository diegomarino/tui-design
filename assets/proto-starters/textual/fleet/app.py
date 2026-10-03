"""Fleet: header band + focused list + detail panel + message line + key-hint bar."""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.content import Content
from textual.events import Resize
from textual.geometry import Size
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from .data import CONTEXT, MESSAGE, SERVICES, Service
from .theme import Tokens, make_theme

MIN_COLS, MIN_ROWS = 80, 24
GLYPH = {"running": "●", "degraded": "▲", "failed": "✗", "stopped": "·"}
STATUS_TOKEN = {
    "running": "status.success", "degraded": "status.warning",
    "failed": "status.error", "stopped": "fg.faint",
}
EVENT = {  # kind -> (glyph, token)
    "ok": ("✓", "status.success"), "warn": ("▲", "status.warning"),
    "info": ("·", "fg.faint"), "error": ("✗", "status.error"),
}


def pad(s: str, n: int) -> str:
    return s + " " * max(0, n - len(s))


class Tokened:
    """Mixin: widgets that build markup from design tokens."""
    tk: Tokens

    def m(self, text: str, token: str, on: str | None = None, bold: bool = False) -> str:
        return f"[{self.tk.sty(token, on=on, bold=bold)}]{text}[/]"


class ServiceList(Tokened, Widget, can_focus=True):
    """Selectable list. Focus = border.focus (see app.tcss `:focus`)."""
    BINDINGS = [
        Binding("up,k", "move(-1)", "Up", show=False),
        Binding("down,j", "move(1)", "Down", show=False),
    ]
    index = reactive(0)

    def __init__(self, tk: Tokens, **kw) -> None:
        super().__init__(**kw)
        self.tk = tk

    def action_move(self, delta: int) -> None:
        self.index = max(0, min(len(SERVICES) - 1, self.index + delta))

    class Selected(Message):
        def __init__(self, index: int) -> None:
            super().__init__()
            self.index = index

    def watch_index(self, index: int) -> None:
        self.post_message(self.Selected(index))

    def render(self) -> Content:
        lines = []
        for i, s in enumerate(SERVICES):
            stok = STATUS_TOKEN[s.status]
            name, status = pad(s.name, 14), pad(s.status, 10)
            if i == self.index:
                on = "selection.bg"
                m = lambda t, k, b=False: self.m(t, k, on=on, bold=b)  # noqa: E731
                lines.append(
                    m(" ", "fg.default") + m("❯", "accent.primary", True) + m(" ", "fg.default")
                    + m(GLYPH[s.status], stok) + m(" ", "fg.default") + m(name, "selection.fg", True)
                    + m(status, stok) + m(" ", "fg.default")
                )
            else:
                faint = s.status == "stopped"
                lines.append(
                    "   " + self.m(GLYPH[s.status], stok) + " "
                    + self.m(name, "fg.faint" if faint else "fg.default")
                    + self.m(status, "fg.muted" if s.status == "running" else stok) + " "
                )
        return Content.from_markup("\n".join(lines))


class Detail(Tokened, Widget, can_focus=True):
    service = reactive(SERVICES[0], layout=True)

    def __init__(self, tk: Tokens, **kw) -> None:
        super().__init__(**kw)
        self.tk = tk

    def gauge(self, label: str, pct: int, width: int) -> str:
        filled = pct * width // 100
        tok = "ramp.low" if pct < 50 else "ramp.mid" if pct < 80 else "ramp.high"
        return (" " + self.m(pad(label, 10), "fg.muted") + self.m("█" * filled, tok)
                + self.m("░" * (width - filled), "fg.faint") + self.m(f" {pct:>2}%", "fg.default"))

    def render(self) -> Content:
        s: Service = self.service
        stok = STATUS_TOKEN[s.status]
        w = self.size.width
        bar = min(60, max(10, w + 2 - 28))   # +2: widget width excludes the border columns
        field = lambda label, value: " " + self.m(pad(label, 10), "fg.muted") + value  # noqa: E731
        lines = [
            "",
            field("Status", self.m(f"{GLYPH[s.status]} {s.status}", stok)
                  + self.m(f" · {s.replicas} replicas", "fg.muted")),
            field("Version", self.m(s.version, "fg.default")),
            field("Uptime", self.m(s.uptime, "fg.default")),
            "",
            self.gauge("CPU", s.cpu, bar),
            self.gauge("Memory", s.mem, bar),
            self.gauge("Errors", s.err, bar),
            "",
            " " + self.m("Recent events", "fg.title", bold=True),
        ]
        for e in s.events:
            glyph, tok = EVENT[e.kind]
            lines.append(" " + self.m(f"{e.time}  ", "fg.faint") + self.m(glyph, tok)
                         + self.m(f" {e.text}", "fg.muted" if e.kind == "info" else "fg.default"))
        return Content.from_markup("\n".join(lines))


class FleetApp(App):
    CSS_PATH = "app.tcss"
    BINDINGS = [Binding("q", "quit", "Quit")]   # tab -> focus_next is built in

    def __init__(self, tokens: Tokens, **kw) -> None:
        # 16-color depth: keep ANSI colors native instead of converting them to truecolor.
        super().__init__(ansi_color=tokens.ansi_mode, **kw)
        self.tk = tokens
        theme = make_theme(tokens)
        self.register_theme(theme)
        self.theme = theme.name

    def m(self, text: str, token: str, on: str | None = None, bold: bool = False) -> str:
        return f"[{self.tk.sty(token, on=on, bold=bold)}]{text}[/]"

    def hint(self, key: str, desc: str, gap: str = "  ") -> str:
        bar = "statusbar.bg"
        return self.m(key, "keyhint.key", bar, True) + self.m(f" {desc}{gap}", "keyhint.desc", bar)

    def compose(self) -> ComposeResult:
        bar = "statusbar.bg"
        with Vertical(id="main"):
            with Horizontal(id="header"):
                yield Static(
                    self.m(" Fleet ", "accent.primary", bar, True) + self.m("│", "border.default", bar)
                    + self.m(" 1 Services ", "tab.active.fg", "tab.active.bg", True)
                    + self.m(" 2 Logs  3 Config ", "tab.inactive.fg", bar),
                    id="tabs")
                yield Static(self.m(f"{CONTEXT} ", "statusbar.fg", bar), id="context")
            with Horizontal(id="body"):
                yield ServiceList(self.tk, id="services")
                yield Detail(self.tk, id="detail")
            yield Static(
                " " + self.m("✓", "status.success") + self.m(f" {MESSAGE[0]}", "fg.default")
                + self.m(MESSAGE[1], "fg.faint"), id="message")
            with Horizontal(id="keybar"):
                yield Static(
                    self.m(" ", "fg.default", bar) + self.hint("↑↓", "select") + self.hint("enter", "open")
                    + self.hint("/", "filter") + self.hint("r", "restart") + self.hint("tab", "pane"),
                    id="hints-left")
                yield Static(self.hint("?", "help") + self.hint("q", "quit", " "), id="hints-right")
        yield Static("", id="notice")

    def on_mount(self) -> None:
        sv, dt = self.query_one("#services"), self.query_one("#detail")
        sv.border_title = f"Services ({len(SERVICES)})"
        dt.border_title = SERVICES[0].name
        sv.focus()
        self._check_size(self.size)

    def on_resize(self, event: Resize) -> None:
        self._check_size(event.size)

    def _check_size(self, size: Size) -> None:
        small = size.width < MIN_COLS or size.height < MIN_ROWS
        self.screen.set_class(small, "too-small")
        if small:
            self.query_one("#notice", Static).update(
                self.m(f"Terminal too small — need {MIN_COLS}×{MIN_ROWS}, have {size.width}×{size.height}",
                       "status.warning"))

    def on_service_list_selected(self, event: ServiceList.Selected) -> None:
        svc = SERVICES[event.index]
        self.query_one("#services").refresh()
        self.query_one("#detail", Detail).service = svc
        self.query_one("#detail").border_title = svc.name
