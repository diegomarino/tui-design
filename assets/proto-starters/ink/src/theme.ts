// Theme tokens -> Ink props.
//
// Input is the flat resolved theme JSON from
//   python3 SKILL_DIR/scripts/export_theme.py ID --target json -o theme.json
// Ink has no theme system of its own: every <Text>/<Box> takes color props, so we
// expose a small token object and spread its results into components:
//   <Text {...t.text('fg.muted')}>        -> color (+ bold/dim/underline)
//   <Text {...t.text('keyhint.key', {on: 'statusbar.bg', bold: true})}>
//   <Box borderColor={t.color('border.focus')} backgroundColor={t.color('statusbar.bg')}>
//
// Depth handling:
//   truecolor / 256 -> hex strings; chalk (chalk.level 3 / 2) down-samples them.
//   16              -> the theme's `ansi16` map (e.g. "4 bold", "default dim", "reverse", "bg")
//                      becomes named colors (chalk level 1 emits SGR 30-37/90-97),
//                      so a 16-color terminal keeps its own palette.
//                      "bg" (fg tokens only) = text in the terminal background color on the fill:
//                      drawn as the fill token's slot as foreground + inverse (SGR 7).

export type Depth = 'truecolor' | '256' | '16';

export interface ThemeJson {
	id: string;
	name: string;
	appearance: 'dark' | 'light';
	terminal: {background: string; foreground: string; ansi: string[]; [k: string]: unknown};
	tokens: Record<string, string>;
	ansi16: Record<string, string>;
}

export interface StyleProps {
	color?: string;
	backgroundColor?: string;
	bold?: boolean;
	dimColor?: boolean;
	italic?: boolean;
	underline?: boolean;
	inverse?: boolean;
}

export interface StyleOpts {
	/** background token, e.g. 'statusbar.bg' */
	on?: string;
	bold?: boolean;
	dim?: boolean;
	italic?: boolean;
	underline?: boolean;
}

const ANSI_NAMES = [
	'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white',
	'blackBright', 'redBright', 'greenBright', 'yellowBright', 'blueBright', 'magentaBright', 'cyanBright', 'whiteBright',
] as const;

interface Ansi16Spec {
	color?: string;
	bold?: boolean;
	dim?: boolean;
	underline?: boolean;
	reverse?: boolean;
	bgText?: boolean;   // "bg": terminal-background-colored text on the fill
}

/** Parse "<color> [attrs]" where color is 0..15 | default | reverse | bg. */
function parseAnsi16(spec: string): Ansi16Spec {
	const out: Ansi16Spec = {};
	for (const word of spec.trim().split(/\s+/)) {
		if (/^\d+$/.test(word)) out.color = ANSI_NAMES[Number(word)];
		else if (word === 'reverse') out.reverse = true;
		else if (word === 'bg') out.bgText = true;
		else if (word === 'bold') out.bold = true;
		else if (word === 'dim') out.dim = true;
		else if (word === 'underline') out.underline = true;
		// 'default' -> no color prop (terminal default)
	}
	return out;
}

export function createTheme(json: ThemeJson, depth: Depth) {
	const hex = (token: string): string => {
		const v = json.tokens[token];
		if (!v) throw new Error(`theme ${json.id}: unknown token "${token}"`);
		return v;
	};
	const a16 = (token: string): Ansi16Spec => parseAnsi16(json.ansi16[token] ?? 'default');

	/** Color for a Box prop (borderColor, backgroundColor) or a Text color. undefined = terminal default. */
	const color = (token: string): string | undefined =>
		depth === '16' ? a16(token).color : hex(token);

	/** Spread-able Text props for a foreground token (+ optional background token and attributes). */
	const text = (fg: string, o: StyleOpts = {}): StyleProps => {
		const p: StyleProps = {};
		if (depth === '16') {
			const s = a16(fg);
			const b = o.on ? a16(o.on) : undefined;
			if (s.bgText) {
				// terminal-background text on the fill: the fill's slot as foreground, then inverse
				p.color = b?.color;
				p.inverse = true;
			} else {
				p.color = s.color;
				if (s.reverse) p.inverse = true;
				if (b?.reverse) p.inverse = true;     // e.g. selection.bg = "reverse"
				else if (b?.color) p.backgroundColor = b.color;
			}
			if (s.bold) p.bold = true;
			if (s.dim) p.dimColor = true;
			if (s.underline) p.underline = true;
		} else {
			p.color = hex(fg);
			if (o.on) p.backgroundColor = hex(o.on);
		}
		if (o.bold) p.bold = true;
		if (o.dim) p.dimColor = true;
		if (o.italic) p.italic = true;
		if (o.underline) p.underline = true;
		return p;
	};

	return {id: json.id, name: json.name, depth, color, text};
}

export type Theme = ReturnType<typeof createTheme>;
