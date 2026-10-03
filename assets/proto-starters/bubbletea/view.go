package main

import (
	"fmt"
	"strings"

	"charm.land/lipgloss/v2"
)

const (
	minW, minH = 80, 24
	listW      = 32 // fixed list pane width (border included); detail takes the rest
)

// pad extends s with bg.base spaces to exactly w cells (and truncates if it is wider).
func (m model) pad(s string, w int) string {
	if lipgloss.Width(s) > w {
		s = lipgloss.NewStyle().MaxWidth(w).Render(s)
	}
	if n := w - lipgloss.Width(s); n > 0 {
		s += m.st.Base.Render(strings.Repeat(" ", n))
	}
	return s
}

// sp returns n spaces painted with bg.base (a bare " " would show the terminal background).
func (m model) sp(n int) string { return m.st.Base.Render(strings.Repeat(" ", n)) }

func padTo(s string, w int) string { // plain-text pad, for fixed columns
	return s + strings.Repeat(" ", max(0, w-lipgloss.Width(s)))
}

// view composes the screen as strings: header, [list | detail], message, footer.
// Lip Gloss v2 sizing: Width() is the outer width (border + padding included) and
// Height() is a MINIMUM, so every row is fitted by hand and the root is clipped.
func (m model) view() string {
	if m.w < minW || m.h < minH {
		msg := fmt.Sprintf("Terminal too small — need %d×%d, have %d×%d", minW, minH, m.w, m.h)
		return lipgloss.Place(m.w, m.h, lipgloss.Center, lipgloss.Center, m.st.Warning.Render(msg),
			lipgloss.WithWhitespaceStyle(m.st.Base))
	}
	bodyH := m.h - 3
	body := lipgloss.JoinHorizontal(lipgloss.Top,
		m.listPane(listW, bodyH), m.detailPane(m.w-listW, bodyH))
	out := lipgloss.JoinVertical(lipgloss.Left, m.header(), body, m.message(), m.footer())
	return lipgloss.NewStyle().MaxWidth(m.w).MaxHeight(m.h).Render(out)
}

func (m model) header() string {
	s := m.st
	left := s.HeaderApp.Render(" Fleet ") + s.HeaderSep.Render("│") +
		s.TabActive.Render(" 1 Services ") + s.TabInactive.Render(" 2 Logs ") + s.TabInactive.Render(" 3 Config ")
	right := s.HeaderR.Render("prod-eu · 12:04:31 ")
	fill := max(0, m.w-lipgloss.Width(left)-lipgloss.Width(right))
	return left + s.Header.Render(strings.Repeat(" ", fill)) + right
}

func (m model) message() string {
	s := m.st
	return m.pad(m.sp(1)+s.Success.Render("✓")+s.Default.Render(" "+m.msg)+s.Faint.Render(" · "+m.msgAge), m.w)
}

func (m model) footer() string {
	s := m.st
	hint := func(k, d string) string { return s.KeyKey.Render(k) + s.KeyDesc.Render(" "+d+"  ") }
	left := s.FooterBar.Render(" ") + hint("↑↓", "select") + hint("enter", "open") + hint("/", "filter") +
		hint("r", "restart") + hint("tab", "pane")
	if m.focus == 1 {
		left = s.FooterBar.Render(" ") + hint("r", "restart") + hint("tab", "pane")
	}
	right := s.KeyKey.Render("?") + s.KeyDesc.Render(" help  ") + s.KeyKey.Render("q") + s.KeyDesc.Render(" quit ")
	fill := max(0, m.w-lipgloss.Width(left)-lipgloss.Width(right))
	return left + s.FooterBar.Render(strings.Repeat(" ", fill)) + right
}

// pane draws a rounded box with the title embedded in the top edge. Lip Gloss has no
// border titles, so the top edge is built by hand and the lipgloss border is used for
// the other three sides (BorderTop(false)). w and h are OUTER sizes.
func (m model) pane(title string, lines []string, w, h int, focused bool) string {
	bs := m.st.BorderDefault
	if focused {
		bs = m.st.BorderFocus
	}
	dashes := max(0, w-5-lipgloss.Width(title))
	top := bs.Render("╭─") + m.st.Title.Render(" "+title+" ") + bs.Render(strings.Repeat("─", dashes)+"╮")

	inner := w - 2
	fitted := make([]string, 0, h-2)
	for i := 0; i < h-2; i++ {
		line := ""
		if i < len(lines) {
			line = lines[i]
		}
		fitted = append(fitted, m.pad(line, inner))
	}
	box := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).BorderTop(false).
		BorderForeground(bs.GetForeground()).BorderBackground(m.st.Base.GetBackground()).
		Background(m.st.Base.GetBackground()). // paints the Height() padding rows
		Width(w).Height(h - 1).                // outer size minus the hand-drawn top row
		Render(strings.Join(fitted, "\n"))
	return top + "\n" + box
}

// statusStyle returns the color style for a service status.
func (m model) statusStyle(st status) lipgloss.Style {
	switch st {
	case running:
		return m.st.Success
	case degraded:
		return m.st.Warning
	case failed:
		return m.st.Error
	}
	return m.st.Faint
}

func (m model) listPane(w, h int) string {
	s := m.st
	var lines []string
	for i, svc := range services {
		sty := m.statusStyle(svc.st)
		if i == m.sel {
			bg, selName := s.SelBg, s.RowSel
			rev := s.SelReverse // 16-color, selection.bg = "reverse": invert each segment, keeping its fg spec
			if m.focus != 0 {
				bg, selName, rev = s.SelInactiveBg, s.RowSelInactive, false
			}
			on := func(x lipgloss.Style) lipgloss.Style {
				if rev {
					x = x.Reverse(true)
				}
				return x.Background(bg)
			}
			word := on(sty)
			if svc.st == running { // selected row: the "running" word is success-colored
				word = on(s.Success)
			}
			lines = append(lines, on(s.Default).Render(" ")+on(s.Cursor).Render("❯")+on(s.Default).Render(" ")+
				on(sty).Render(svc.st.glyph())+on(s.Default).Render(" ")+
				on(selName).Render(padTo(svc.name, 14))+word.Render(padTo(svc.st.String(), 10))+on(s.Default).Render(" "))
			continue
		}
		name, word := s.Name, sty
		if svc.st == running {
			word = s.Muted
		}
		if svc.st == stopped {
			name = s.NameFaint
		}
		lines = append(lines, m.sp(3)+sty.Render(svc.st.glyph())+m.sp(1)+name.Render(padTo(svc.name, 14))+
			word.Render(padTo(svc.st.String(), 10))+m.sp(1))
	}
	return m.pane(fmt.Sprintf("Services (%d)", len(services)), lines, w, h, m.focus == 0)
}

func (m model) detailPane(w, h int) string {
	s := m.st
	svc := services[m.sel]
	inner := w - 2
	label := func(k string) string { return s.Muted.Render(padTo(k, 10)) }
	bw := min(max(inner-26, 10), 40) // gauge width: 20 cells at the 80-col layout
	gauge := func(name string, pct int) string {
		sty := s.RampLow
		if pct >= 80 {
			sty = s.RampHigh
		} else if pct >= 50 {
			sty = s.RampMid
		}
		n := pct * bw / 100
		return m.sp(1) + label(name) + sty.Render(strings.Repeat("█", n)) + s.Faint.Render(strings.Repeat("░", bw-n)) +
			s.Default.Render(" "+padTo(fmt.Sprintf("%d%%", pct), 3))
	}
	glyphStyle := map[string]lipgloss.Style{"ok": s.Success, "warn": s.Warning, "info": s.Faint, "err": s.Error}
	glyph := map[string]string{"ok": "✓", "warn": "▲", "info": "·", "err": "✗"}
	lines := []string{
		"",
		m.sp(1) + label("Status") + m.statusStyle(svc.st).Render(svc.st.glyph()+" "+svc.st.String()) +
			s.Muted.Render(" · "+svc.replicas+" replicas"),
		m.sp(1) + label("Version") + s.Default.Render(svc.version),
		m.sp(1) + label("Uptime") + s.Default.Render(svc.uptime),
		"",
		gauge("CPU", svc.cpu), gauge("Memory", svc.mem), gauge("Errors", svc.errs),
		"",
		m.sp(1) + s.Title.Render("Recent events"),
	}
	for _, e := range svc.events {
		text := s.Default
		if e.kind == "info" {
			text = s.Muted
		}
		lines = append(lines, m.sp(1)+s.Faint.Render(padTo(e.at, 7))+glyphStyle[e.kind].Render(glyph[e.kind])+text.Render(" "+e.text))
	}
	return m.pane(svc.name, lines, w, h, m.focus == 1)
}
