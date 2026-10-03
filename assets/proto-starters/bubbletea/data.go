package main

// Mock data for the canonical "Fleet" demo screen (same text as assets/demo/fleet--normal--80x24.mock).

type status int

const (
	running status = iota
	degraded
	failed
	stopped
)

type event struct {
	at   string
	kind string // ok | warn | info | err
	text string
}

type service struct {
	name, version, uptime string
	st                    status
	replicas              string
	cpu, mem, errs        int // percent
	events                []event
}

var services = []service{
	{"api-gateway", "v2.4.1", "6d 4h", running, "3/3", 31, 68, 92, []event{
		{"12:01", "ok", "deploy v2.4.1 finished"},
		{"11:58", "warn", "p95 latency 820 ms"},
		{"11:40", "info", "scaled 2 → 3 replicas"},
		{"11:02", "err", "health check timeout"}}},
	{"auth", "v1.9.0", "12d 2h", running, "2/2", 12, 41, 3, []event{
		{"11:55", "ok", "token cache warmed"},
		{"10:20", "info", "rotated signing keys"},
		{"09:03", "ok", "deploy v1.9.0 finished"},
		{"08:59", "info", "scaled 1 → 2 replicas"}}},
	{"billing", "v3.1.2", "2d 9h", degraded, "1/2", 58, 77, 34, []event{
		{"12:03", "warn", "queue depth 1.2k"},
		{"11:47", "err", "replica billing-2 restarted"},
		{"11:20", "warn", "p95 latency 640 ms"},
		{"09:10", "ok", "deploy v3.1.2 finished"}}},
	{"search", "v0.8.7", "5m", failed, "0/2", 0, 0, 100, []event{
		{"12:04", "err", "OOMKilled (exit 137)"},
		{"12:03", "err", "readiness probe failed"},
		{"11:59", "info", "deploy v0.8.7 started"},
		{"11:30", "ok", "reindex finished"}}},
	{"worker", "v2.0.3", "6d 4h", running, "4/4", 44, 52, 1, []event{
		{"12:02", "ok", "job batch #4812 done"},
		{"11:45", "info", "scaled 3 → 4 replicas"},
		{"11:10", "ok", "job batch #4811 done"},
		{"10:35", "ok", "job batch #4810 done"}}},
	{"cron", "v1.2.0", "—", stopped, "0/0", 0, 0, 0, []event{
		{"03:00", "ok", "nightly cleanup finished"},
		{"02:59", "info", "job started"},
		{"Tue", "info", "paused by ops"},
		{"Mon", "ok", "deploy v1.2.0 finished"}}},
}

func (s status) String() string {
	return [...]string{"running", "degraded", "failed", "stopped"}[s]
}

func (s status) glyph() string {
	return [...]string{"●", "▲", "✗", "·"}[s]
}
