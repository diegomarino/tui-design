// Fleet: the tui-design canonical demo screen in Bubble Tea v2 + Lip Gloss v2.
//
//	go run .                                   interactive (alt screen): up/down/j/k select, tab pane, r restart, q quit
//	go run . --frame --cols 120 --rows 30 --theme theme.json --depth truecolor   one static ANSI frame, then exit
package main

import (
	"flag"
	"fmt"
	"io"
	"os"
	"strings"

	tea "charm.land/bubbletea/v2"
	"github.com/charmbracelet/colorprofile"
)

type model struct {
	st          Styles
	w, h        int
	sel, focus  int // focus: 0 = list, 1 = detail
	msg, msgAge string
}

func newModel(t Theme, ansi16 bool) model {
	return model{st: NewStyles(t, ansi16), msg: "deployed api-gateway v2.4.1", msgAge: "2m ago"}
}

func (m model) Init() tea.Cmd { return nil }

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.w, m.h = msg.Width, msg.Height
	case tea.KeyPressMsg:
		switch msg.String() {
		case "q", "ctrl+c":
			return m, tea.Quit
		case "tab", "shift+tab":
			m.focus = 1 - m.focus
		case "up", "k":
			if m.focus == 0 && m.sel > 0 {
				m.sel--
			}
		case "down", "j":
			if m.focus == 0 && m.sel < len(services)-1 {
				m.sel++
			}
		case "r":
			m.msg, m.msgAge = "restart requested for "+services[m.sel].name, "just now"
		}
	}
	return m, nil
}

// View returns the whole screen. In v2 the terminal modes live on the View value.
func (m model) View() tea.View {
	v := tea.NewView(m.view())
	v.AltScreen = true
	v.BackgroundColor = m.st.Base.GetBackground()
	return v
}

func main() {
	var (
		frame      = flag.Bool("frame", false, "print one static frame and exit")
		cols       = flag.Int("cols", 80, "frame width")
		rows       = flag.Int("rows", 24, "frame height")
		themePath  = flag.String("theme", "", "flat theme JSON (default: embedded catppuccin-mocha)")
		depth      = flag.String("depth", "truecolor", "frame color depth: truecolor|256|16")
		selected   = flag.Int("selected", 0, "frame: selected service index")
		focusRight = flag.Bool("focus-detail", false, "frame: focus the detail pane")
	)
	flag.Parse()

	th, err := LoadTheme(*themePath)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	m := newModel(th, *depth == "16")

	if !*frame {
		if _, err := tea.NewProgram(m).Run(); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		return
	}

	profile := map[string]colorprofile.Profile{"truecolor": colorprofile.TrueColor, "256": colorprofile.ANSI256, "16": colorprofile.ANSI}[*depth]
	if profile == colorprofile.Unknown {
		fmt.Fprintln(os.Stderr, "--depth must be truecolor, 256 or 16")
		os.Exit(2)
	}
	m.sel = max(0, min(*selected, len(services)-1))
	if *focusRight {
		m.focus = 1
	}
	renderFrame(m, *cols, *rows, profile, os.Stdout)
}

// renderFrame sends the same WindowSizeMsg the runtime would, takes the View content
// (Render() always emits truecolor) and downsamples it with a colorprofile.Writer.
func renderFrame(m model, w, h int, p colorprofile.Profile, out io.Writer) {
	next, _ := m.Update(tea.WindowSizeMsg{Width: w, Height: h})
	content := next.(model).view()
	cw := &colorprofile.Writer{Forward: out, Profile: p}
	fmt.Fprint(cw, strings.TrimRight(content, "\n")+"\n")
}
