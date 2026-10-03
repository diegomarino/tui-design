// Mock data for the Fleet demo screen (identical text to assets/demo/fleet--normal--80x24.mock).

export type Status = 'running' | 'degraded' | 'failed' | 'stopped';
export type EventKind = 'ok' | 'warn' | 'info' | 'error';

export interface Service {
	name: string;
	status: Status;
	replicas: string;
	version: string;
	uptime: string;
	cpu: number;
	mem: number;
	err: number;
	events: {time: string; kind: EventKind; text: string}[];
}

export const CONTEXT = 'prod-eu · 12:04:31';
export const MESSAGE = {text: 'deployed api-gateway v2.4.1', age: ' · 2m ago'};

export const SERVICES: Service[] = [
	{
		name: 'api-gateway', status: 'running', replicas: '3/3', version: 'v2.4.1', uptime: '6d 4h', cpu: 31, mem: 68, err: 92,
		events: [
			{time: '12:01', kind: 'ok', text: 'deploy v2.4.1 finished'},
			{time: '11:58', kind: 'warn', text: 'p95 latency 820 ms'},
			{time: '11:40', kind: 'info', text: 'scaled 2 → 3 replicas'},
			{time: '11:02', kind: 'error', text: 'health check timeout'},
		],
	},
	{
		name: 'auth', status: 'running', replicas: '2/2', version: 'v1.9.0', uptime: '12d 2h', cpu: 12, mem: 41, err: 3,
		events: [
			{time: '11:47', kind: 'ok', text: 'rotated signing keys'},
			{time: '09:15', kind: 'info', text: 'scaled 1 → 2 replicas'},
		],
	},
	{
		name: 'billing', status: 'degraded', replicas: '1/2', version: 'v3.1.0', uptime: '1d 7h', cpu: 74, mem: 82, err: 17,
		events: [
			{time: '12:03', kind: 'warn', text: 'replica 2 not ready'},
			{time: '11:55', kind: 'warn', text: 'queue depth 4.2k'},
			{time: '10:20', kind: 'ok', text: 'deploy v3.1.0 finished'},
		],
	},
	{
		name: 'search', status: 'failed', replicas: '0/2', version: 'v0.8.2', uptime: '0m', cpu: 0, mem: 0, err: 100,
		events: [
			{time: '12:02', kind: 'error', text: 'crash loop (exit 137)'},
			{time: '12:00', kind: 'error', text: 'out of memory'},
			{time: '11:30', kind: 'ok', text: 'index rebuilt'},
		],
	},
	{
		name: 'worker', status: 'running', replicas: '4/4', version: 'v5.0.3', uptime: '6d 4h', cpu: 58, mem: 52, err: 1,
		events: [
			{time: '12:04', kind: 'ok', text: 'drained 128 jobs'},
			{time: '11:10', kind: 'info', text: 'scaled 3 → 4 replicas'},
		],
	},
	{
		name: 'cron', status: 'stopped', replicas: '0/0', version: 'v1.2.0', uptime: '—', cpu: 0, mem: 0, err: 0,
		events: [{time: '08:00', kind: 'info', text: 'paused by ops'}],
	},
];
