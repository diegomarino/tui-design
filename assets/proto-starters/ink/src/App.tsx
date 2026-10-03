// Fleet: header band + focused list + detail panel + message line + key-hint bar.
// Layout is computed from the terminal size (useWindowSize): list width fixed at 32,
// detail takes the rest. Below 80x24 a centered "too small" notice replaces the UI.
import React, {useState, type ReactNode} from 'react';
import {Box, Text, useApp, useInput, useWindowSize} from 'ink';
import {SERVICES, CONTEXT, MESSAGE, type EventKind, type Service, type Status} from './data.ts';
import type {Theme} from './theme.ts';

const MIN_COLS = 80;
const MIN_ROWS = 24;
const LIST_W = 32;

const GLYPH: Record<Status, string> = {running: '●', degraded: '▲', failed: '✗', stopped: '·'};
const STATUS_TOKEN: Record<Status, string> = {
	running: 'status.success', degraded: 'status.warning', failed: 'status.error', stopped: 'fg.faint',
};
const EVENT_GLYPH: Record<EventKind, [string, string]> = {
	ok: ['✓', 'status.success'], warn: ['▲', 'status.warning'], info: ['·', 'fg.faint'], error: ['✗', 'status.error'],
};

const pad = (s: string, n: number) => s + ' '.repeat(Math.max(0, n - [...s].length));
const rampToken = (pct: number) => (pct < 50 ? 'ramp.low' : pct < 80 ? 'ramp.mid' : 'ramp.high');

/** A <Text> styled from a token. */
function T({t, k, on, bold, dim, children}: {t: Theme; k: string; on?: string; bold?: boolean; dim?: boolean; children?: ReactNode}) {
	return <Text {...t.text(k, {on, bold, dim})}>{children}</Text>;
}

/** Rounded pane. Ink has no border titles, so the top edge is drawn as a Text line and
 *  the box below omits its own top border. */
function Pane({t, width, height, title, focused, children}: {
	t: Theme; width: number; height: number; title: string; focused: boolean; children: ReactNode;
}) {
	const edge = focused ? 'border.focus' : 'border.default';
	const fill = '─'.repeat(Math.max(0, width - 5 - [...title].length));
	return (
		<Box flexDirection="column" width={width} height={height}>
			<Text wrap="truncate">
				<T t={t} k={edge}>╭─</T>
				<T t={t} k="fg.title" bold> {title} </T>
				<T t={t} k={edge}>{fill}╮</T>
			</Text>
			<Box
				flexDirection="column" flexGrow={1} overflow="hidden"
				borderStyle="round" borderTop={false} borderColor={t.color(edge)}
			>
				{children}
			</Box>
		</Box>
	);
}

function Header({t, cols}: {t: Theme; cols: number}) {
	const bg = 'statusbar.bg';
	return (
		<Box width={cols} height={1} backgroundColor={t.color(bg)}>
			<Text wrap="truncate">
				<T t={t} k="accent.primary" on={bg} bold> Fleet </T>
				<T t={t} k="border.default" on={bg}>│</T>
				<T t={t} k="tab.active.fg" on="tab.active.bg" bold> 1 Services </T>
				<T t={t} k="tab.inactive.fg" on={bg}> 2 Logs  3 Config </T>
			</Text>
			<Box flexGrow={1} />
			<T t={t} k="statusbar.fg" on={bg}>{CONTEXT} </T>
		</Box>
	);
}

function ServiceList({t, selected}: {t: Theme; selected: number}) {
	return (
		<>
			{SERVICES.map((s, i) => {
				const stok = STATUS_TOKEN[s.status];
				const name = pad(s.name, 14);
				const status = pad(s.status, 10);
				if (i === selected) {
					const on = 'selection.bg';
					return (
						<Text key={s.name} wrap="truncate">
							<T t={t} k="fg.default" on={on}> </T>
							<T t={t} k="accent.primary" on={on} bold>❯</T>
							<T t={t} k="fg.default" on={on}> </T>
							<T t={t} k={stok} on={on}>{GLYPH[s.status]}</T>
							<T t={t} k="fg.default" on={on}> </T>
							<T t={t} k="selection.fg" on={on} bold>{name}</T>
							<T t={t} k={stok} on={on}>{status}</T>
							<T t={t} k="fg.default" on={on}> </T>
						</Text>
					);
				}
				const faint = s.status === 'stopped';
				return (
					<Text key={s.name} wrap="truncate">
						{'   '}
						<T t={t} k={stok}>{GLYPH[s.status]}</T>{' '}
						<T t={t} k={faint ? 'fg.faint' : 'fg.default'}>{name}</T>
						<T t={t} k={s.status === 'running' ? 'fg.muted' : stok}>{status}</T>{' '}
					</Text>
				);
			})}
		</>
	);
}

function Gauge({t, label, pct, width}: {t: Theme; label: string; pct: number; width: number}) {
	const filled = Math.floor((pct * width) / 100);
	return (
		<Text wrap="truncate">
			{' '}<T t={t} k="fg.muted">{pad(label, 10)}</T>
			<T t={t} k={rampToken(pct)}>{'█'.repeat(filled)}</T>
			<T t={t} k="fg.faint">{'░'.repeat(width - filled)}</T>
			<T t={t} k="fg.default"> {String(pct).padStart(2)}%</T>
		</Text>
	);
}

function Detail({t, s, width}: {t: Theme; s: Service; width: number}) {
	const stok = STATUS_TOKEN[s.status];
	const barW = Math.min(60, Math.max(10, width - 28));
	const field = (label: string, value: ReactNode) => (
		<Text wrap="truncate">{' '}<T t={t} k="fg.muted">{pad(label, 10)}</T>{value}</Text>
	);
	return (
		<>
			<Text> </Text>
			{field('Status', (
				<>
					<T t={t} k={stok}>{GLYPH[s.status]} {s.status}</T>
					<T t={t} k="fg.muted"> · {s.replicas} replicas</T>
				</>
			))}
			{field('Version', <T t={t} k="fg.default">{s.version}</T>)}
			{field('Uptime', <T t={t} k="fg.default">{s.uptime}</T>)}
			<Text> </Text>
			<Gauge t={t} label="CPU" pct={s.cpu} width={barW} />
			<Gauge t={t} label="Memory" pct={s.mem} width={barW} />
			<Gauge t={t} label="Errors" pct={s.err} width={barW} />
			<Text> </Text>
			<Text>{' '}<T t={t} k="fg.title" bold>Recent events</T></Text>
			{s.events.map(e => {
				const [glyph, tok] = EVENT_GLYPH[e.kind];
				return (
					<Text key={e.time + e.text} wrap="truncate">
						{' '}<T t={t} k="fg.faint">{e.time}  </T>
						<T t={t} k={tok}>{glyph}</T>
						<T t={t} k={e.kind === 'info' ? 'fg.muted' : 'fg.default'}> {e.text}</T>
					</Text>
				);
			})}
		</>
	);
}

function KeyBar({t, cols}: {t: Theme; cols: number}) {
	const bg = 'statusbar.bg';
	const hint = (key: string, desc: string, gap = '  ') => (
		<>
			<T t={t} k="keyhint.key" on={bg} bold>{key}</T>
			<T t={t} k="keyhint.desc" on={bg}> {desc}{gap}</T>
		</>
	);
	return (
		<Box width={cols} height={1} backgroundColor={t.color(bg)}>
			<Text wrap="truncate">
				<T t={t} k="fg.default" on={bg}> </T>
				{hint('↑↓', 'select')}{hint('enter', 'open')}{hint('/', 'filter')}{hint('r', 'restart')}{hint('tab', 'pane')}
			</Text>
			<Box flexGrow={1} />
			<Text wrap="truncate">{hint('?', 'help')}{hint('q', 'quit', ' ')}</Text>
		</Box>
	);
}

export function App({theme: t}: {theme: Theme}) {
	const {exit} = useApp();
	const {columns: cols, rows} = useWindowSize();
	const [selected, setSelected] = useState(0);
	const [focus, setFocus] = useState<'list' | 'detail'>('list');

	useInput((input, key) => {
		if (input === 'q') exit();
		else if (key.tab) setFocus(f => (f === 'list' ? 'detail' : 'list'));
		else if (focus === 'list' && (key.upArrow || input === 'k')) setSelected(i => Math.max(0, i - 1));
		else if (focus === 'list' && (key.downArrow || input === 'j')) setSelected(i => Math.min(SERVICES.length - 1, i + 1));
	});

	if (cols < MIN_COLS || rows < MIN_ROWS) {
		return (
			<Box width={cols} height={rows} justifyContent="center" alignItems="center">
				<Text {...t.text('status.warning')}>Terminal too small — need {MIN_COLS}×{MIN_ROWS}, have {cols}×{rows}</Text>
			</Box>
		);
	}

	const s = SERVICES[selected]!;
	const bodyH = rows - 3;
	const detailW = cols - LIST_W;
	return (
		<Box flexDirection="column" width={cols} height={rows}>
			<Header t={t} cols={cols} />
			<Box height={bodyH}>
				<Pane t={t} width={LIST_W} height={bodyH} title={`Services (${SERVICES.length})`} focused={focus === 'list'}>
					<ServiceList t={t} selected={selected} />
				</Pane>
				<Pane t={t} width={detailW} height={bodyH} title={s.name} focused={focus === 'detail'}>
					<Detail t={t} s={s} width={detailW} />
				</Pane>
			</Box>
			<Text wrap="truncate">
				{' '}<T t={t} k="status.success">✓</T>
				<T t={t} k="fg.default"> {MESSAGE.text}</T>
				<T t={t} k="fg.faint">{MESSAGE.age}</T>
			</Text>
			<KeyBar t={t} cols={cols} />
		</Box>
	);
}
