#!/usr/bin/env -S npx tsx
// Fleet starter entry point.
//   tsx src/cli.tsx                                   interactive (alternate screen)
//   tsx src/cli.tsx --frame --cols 120 --rows 30 \
//       --theme theme.json --depth truecolor          print ONE frame as ANSI, exit
// --theme takes a flat theme JSON path or a theme ID (an ID is exported with
// $SKILL_DIR/scripts/export_theme.py; see loadThemeJson).
import {execFileSync} from 'node:child_process';
import {EventEmitter} from 'node:events';
import {existsSync, readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {PassThrough} from 'node:stream';
import {fileURLToPath} from 'node:url';
import chalk from 'chalk';
import React from 'react';
import {render} from 'ink';
import {App} from './App.tsx';
import {createTheme, type Depth, type ThemeJson} from './theme.ts';

function parseArgs(argv: string[]) {
	const a: {frame: boolean; cols: number; rows: number; theme: string; depth?: Depth} = {
		frame: false, cols: 80, rows: 24,
		theme: fileURLToPath(new URL('../theme.json', import.meta.url)),
	};
	for (let i = 0; i < argv.length; i++) {
		const k = argv[i];
		if (k === '--frame') a.frame = true;
		else if (k === '--cols') a.cols = Number(argv[++i]);
		else if (k === '--rows') a.rows = Number(argv[++i]);
		else if (k === '--theme') a.theme = argv[++i]!;
		else if (k === '--depth') a.depth = argv[++i] as Depth;
		else {
			process.stderr.write(`usage: cli.tsx [--frame --cols N --rows N] [--theme theme.json|ID] [--depth truecolor|256|16]\n`);
			process.exit(2);
		}
	}
	if (a.depth && !['truecolor', '256', '16'].includes(a.depth)) {
		process.stderr.write(`bad --depth ${a.depth}\n`);
		process.exit(2);
	}
	return a;
}

/** --theme value -> theme JSON: an existing file is read as-is, anything else is a theme ID exported
 *  through the skill's export_theme.py (SKILL_DIR env first, then the relative path when this
 *  starter still sits inside the skill). */
function loadThemeJson(arg: string): ThemeJson {
	if (existsSync(arg)) return JSON.parse(readFileSync(arg, 'utf8')) as ThemeJson;
	if (/[\\/]|\.json$/i.test(arg)) {
		process.stderr.write(`theme file not found: ${arg}\n`);
		process.exit(2);
	}
	const here = fileURLToPath(new URL('.', import.meta.url));
	for (const root of [process.env.SKILL_DIR, resolve(here, '../../../..')]) {
		const script = root && resolve(root, 'scripts/export_theme.py');
		if (script && existsSync(script)) {
			return JSON.parse(execFileSync('python3', [script, arg, '--target', 'json'], {encoding: 'utf8'})) as ThemeJson;
		}
	}
	process.stderr.write(
		`cannot resolve theme ID "${arg}": the tui-design skill was not found.\n` +
		`Set SKILL_DIR=/path/to/tui-design, or pass a theme JSON file to --theme.\n`);
	process.exit(2);
}

const args = parseArgs(process.argv.slice(2));
const themeJson = loadThemeJson(args.theme);
// Default depth: truecolor. Chalk's level is what actually down-samples hex colors (3/2) and
// turns named colors into SGR 30-37/90-97 (1), so set it explicitly instead of sniffing env.
const depth: Depth = args.depth ?? 'truecolor';
if (args.frame || args.depth) chalk.level = depth === 'truecolor' ? 3 : depth === '256' ? 2 : 1;
const theme = createTheme(themeJson, depth);

if (!args.frame) {
	render(<App theme={theme} />, {alternateScreen: true});
} else {
	// ONE frame at a forced size: render() into a fake non-TTY stdout that reports columns/rows
	// (so useWindowSize works), capture the last full frame, unmount.
	const {cols, rows} = args;
	const frames: string[] = [];
	const stdout = Object.assign(new EventEmitter(), {
		columns: cols, rows, isTTY: false,
		write: (s: string) => (frames.push(s), true),
	});
	// useInput needs a stdin that claims raw-mode support, otherwise Ink renders an error frame.
	const stdin = Object.assign(new PassThrough(), {isTTY: true, setRawMode() {}, ref() {}, unref() {}});
	const app = render(<App theme={theme} />, {
		stdout: stdout as never, stdin: stdin as never, debug: true, exitOnCtrlC: false, patchConsole: false,
	});
	await app.waitUntilRenderFlush();
	const frame = frames.at(-1) ?? '';   // capture BEFORE unmount: the unmount write is just "\n"
	app.unmount();
	// Ink drops trailing blank rows; pad so the frame is exactly `rows` lines.
	const lines = frame.replace(/\n+$/, '').split('\n');
	while (lines.length < rows) lines.push('');
	process.stdout.write(lines.slice(0, rows).join('\n') + '\n');
}
