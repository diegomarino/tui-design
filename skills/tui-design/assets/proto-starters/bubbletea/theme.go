package main

import (
	_ "embed"
	"encoding/json"
	"fmt"
	"image/color"
	"os"
	"strings"

	"charm.land/lipgloss/v2"
)

// Default theme: catppuccin-mocha, exported with
//
//	python3 $SKILL_DIR/scripts/export_theme.py catppuccin-mocha --target json -o theme.json
//
//go:embed theme.json
var defaultThemeJSON []byte

// Theme is the flat, resolved theme JSON (tier-2 token fallbacks already applied).
type Theme struct {
	ID     string            `json:"id"`
	Tokens map[string]string `json:"tokens"`
	ANSI16 map[string]string `json:"ansi16"` // token -> "<0..15|default|reverse|bg> [bold|dim|underline]"
}

// LoadTheme reads a theme JSON file; an empty path loads the embedded default.
func LoadTheme(path string) (Theme, error) {
	data := defaultThemeJSON
	if path != "" {
		b, err := os.ReadFile(path)
		if err != nil {
			return Theme{}, err
		}
		data = b
	}
	var t Theme
	if err := json.Unmarshal(data, &t); err != nil {
		return Theme{}, fmt.Errorf("theme json: %w", err)
	}
	return t, nil
}

// resolver turns tokens into styles. Truecolor/256 mode uses the token's hex (Render() always
// emits truecolor; the output writer downsamples). ansi16 mode uses the theme's per-token
// "ansi16" spec instead: a semantic mapping onto the terminal's own 16 colors, not a
// nearest-color guess ("default" = no color, "reverse" = reverse video, "bg" = fg tokens
// only: text in the terminal background color on the fill, drawn as the fill's slot + reverse).
type resolver struct {
	t      Theme
	ansi16 bool
}

// spec parses a token's ansi16 spec. "bg" (fg tokens only) is reported via bgText; fgOn resolves it
// because only it knows the fill.
func (r resolver) spec(token string) (c color.Color, attrs []string, reverse, bgText bool) {
	f := strings.Fields(r.t.ANSI16[token])
	switch {
	case len(f) == 0 || f[0] == "default":
		return lipgloss.NoColor{}, f[min(1, len(f)):], false, false
	case f[0] == "reverse":
		return lipgloss.NoColor{}, nil, true, false
	case f[0] == "bg":
		return lipgloss.NoColor{}, f[1:], false, true
	}
	return lipgloss.Color(f[0]), f[1:], false, false // "4" -> ANSI color 4
}

func (r resolver) hex(token string) color.Color {
	if h, ok := r.t.Tokens[token]; ok {
		return lipgloss.Color(h)
	}
	return lipgloss.Color(r.t.Tokens["fg.default"]) // partial theme never crashes the UI
}

// bg returns the background color of a token (NoColor in 16-color mode when it is "default"/"reverse").
func (r resolver) bg(token string) color.Color {
	if !r.ansi16 {
		return r.hex(token)
	}
	c, _, _, _ := r.spec(token)
	return c
}

// fg returns a style carrying the token's foreground (+ attributes in 16-color mode).
func (r resolver) fg(token string) lipgloss.Style {
	st := lipgloss.NewStyle()
	if !r.ansi16 {
		return st.Foreground(r.hex(token))
	}
	c, attrs, rev, _ := r.spec(token)
	return applyAttrs(st.Foreground(c).Reverse(rev), attrs)
}

// fgOn is fg for text drawn on the fill token `on`. Only differs in 16-color mode for a "bg" spec:
// the fill's slot becomes the foreground and the cell is reversed, so the text takes the terminal
// background color on the fill. The returned style paints no background of its own in that case.
func (r resolver) fgOn(token, on string) lipgloss.Style {
	if r.ansi16 {
		if _, attrs, _, bgText := r.spec(token); bgText {
			fill, _, _, _ := r.spec(on)
			return applyAttrs(lipgloss.NewStyle().Foreground(fill).Reverse(true), attrs)
		}
	}
	return r.fg(token).Background(r.bg(on))
}

func applyAttrs(st lipgloss.Style, attrs []string) lipgloss.Style {
	for _, a := range attrs {
		switch a {
		case "bold":
			st = st.Bold(true)
		case "dim":
			st = st.Faint(true)
		case "underline":
			st = st.Underline(true)
		}
	}
	return st
}

// Styles is the lipgloss v2 style sheet for the Fleet screen: one field per UI role,
// every field built from tokens only (no hex in view code). Lip Gloss v2 styles are
// immutable values.
type Styles struct {
	Base                            lipgloss.Style // paints bg.base under everything
	Header, HeaderApp, HeaderSep    lipgloss.Style
	TabActive, TabInactive, HeaderR lipgloss.Style
	BorderFocus, BorderDefault      lipgloss.Style
	Title                           lipgloss.Style
	RowSel, RowSelInactive          lipgloss.Style // selected list row (focused / unfocused pane)
	SelReverse                      bool           // 16-color: selection = reverse video, row is drawn uncolored
	Cursor                          lipgloss.Style
	Name, NameFaint                 lipgloss.Style
	Muted, Faint, Default           lipgloss.Style
	Success, Warning, Error         lipgloss.Style
	RampLow, RampMid, RampHigh      lipgloss.Style
	FooterBar, KeyKey, KeyDesc      lipgloss.Style
	SelBg, SelInactiveBg            color.Color
}

func NewStyles(t Theme, ansi16 bool) Styles {
	r := resolver{t, ansi16}
	fg := func(token string) lipgloss.Style { return r.fgOn(token, "bg.base") }
	band := func(token string) lipgloss.Style { return r.fgOn(token, "statusbar.bg") }
	_, _, selRev, _ := r.spec("selection.bg")
	selRev = selRev && ansi16
	// Selected-row name. 16-color mode with selection.bg = "reverse": the active row is inverted per
	// segment (each segment keeps its own fg spec + bold, like render_mockup.py --depth 16; see listPane),
	// the unfocused row has no fill (selection.inactive.bg = default) and only the name is bold.
	selActive := r.fgOn("selection.fg", "selection.bg").Bold(true)
	selInactive := r.fgOn("selection.fg", "selection.inactive.bg").Bold(true)
	if selRev {
		selInactive = fg("fg.default").Bold(true)
	}
	return Styles{
		Base:           fg("fg.default"),
		Header:         band("statusbar.fg"),
		HeaderApp:      band("accent.primary").Bold(true),
		HeaderSep:      band("border.default"),
		TabActive:      r.fgOn("tab.active.fg", "tab.active.bg").Bold(true), // fill falls back to bg.raised in the theme export
		TabInactive:    band("tab.inactive.fg"),
		HeaderR:        band("statusbar.fg"),
		BorderFocus:    fg("border.focus"),
		BorderDefault:  fg("border.default"),
		Title:          fg("fg.title").Bold(true),
		RowSel:         selActive,
		RowSelInactive: selInactive,
		SelReverse:     selRev,
		Cursor:         fg("accent.primary").Bold(true),
		Name:           fg("fg.default"),
		NameFaint:      fg("fg.faint"),
		Muted:          fg("fg.muted"),
		Faint:          fg("fg.faint"),
		Default:        fg("fg.default"),
		Success:        fg("status.success"),
		Warning:        fg("status.warning"),
		Error:          fg("status.error"),
		RampLow:        fg("ramp.low"),
		RampMid:        fg("ramp.mid"),
		RampHigh:       fg("ramp.high"),
		FooterBar:      band("statusbar.fg"),
		KeyKey:         band("keyhint.key").Bold(true),
		KeyDesc:        band("keyhint.desc"),
		SelBg:          r.bg("selection.bg"),
		SelInactiveBg:  r.bg("selection.inactive.bg"),
	}
}
