//! Mock data for the canonical "Fleet" demo screen (same text as assets/demo/fleet--normal--80x24.mock).

#[derive(Clone, Copy, PartialEq)]
pub enum Status {
    Running,
    Degraded,
    Failed,
    Stopped,
}

impl Status {
    pub fn label(self) -> &'static str {
        ["running", "degraded", "failed", "stopped"][self as usize]
    }
    pub fn glyph(self) -> &'static str {
        ["●", "▲", "✗", "·"][self as usize]
    }
}

pub struct Event {
    pub at: &'static str,
    pub kind: &'static str, // ok | warn | info | err
    pub text: &'static str,
}

pub struct Service {
    pub name: &'static str,
    pub version: &'static str,
    pub uptime: &'static str,
    pub status: Status,
    pub replicas: &'static str,
    pub cpu: u16,
    pub mem: u16,
    pub errs: u16,
    pub events: [Event; 4],
}

const fn ev(at: &'static str, kind: &'static str, text: &'static str) -> Event {
    Event { at, kind, text }
}

use Status::*;

pub const SERVICES: [Service; 6] = [
    Service { name: "api-gateway", version: "v2.4.1", uptime: "6d 4h", status: Running, replicas: "3/3", cpu: 31, mem: 68, errs: 92,
        events: [ev("12:01", "ok", "deploy v2.4.1 finished"), ev("11:58", "warn", "p95 latency 820 ms"),
                 ev("11:40", "info", "scaled 2 → 3 replicas"), ev("11:02", "err", "health check timeout")] },
    Service { name: "auth", version: "v1.9.0", uptime: "12d 2h", status: Running, replicas: "2/2", cpu: 12, mem: 41, errs: 3,
        events: [ev("11:55", "ok", "token cache warmed"), ev("10:20", "info", "rotated signing keys"),
                 ev("09:03", "ok", "deploy v1.9.0 finished"), ev("08:59", "info", "scaled 1 → 2 replicas")] },
    Service { name: "billing", version: "v3.1.2", uptime: "2d 9h", status: Degraded, replicas: "1/2", cpu: 58, mem: 77, errs: 34,
        events: [ev("12:03", "warn", "queue depth 1.2k"), ev("11:47", "err", "replica billing-2 restarted"),
                 ev("11:20", "warn", "p95 latency 640 ms"), ev("09:10", "ok", "deploy v3.1.2 finished")] },
    Service { name: "search", version: "v0.8.7", uptime: "5m", status: Failed, replicas: "0/2", cpu: 0, mem: 0, errs: 100,
        events: [ev("12:04", "err", "OOMKilled (exit 137)"), ev("12:03", "err", "readiness probe failed"),
                 ev("11:59", "info", "deploy v0.8.7 started"), ev("11:30", "ok", "reindex finished")] },
    Service { name: "worker", version: "v2.0.3", uptime: "6d 4h", status: Running, replicas: "4/4", cpu: 44, mem: 52, errs: 1,
        events: [ev("12:02", "ok", "job batch #4812 done"), ev("11:45", "info", "scaled 3 → 4 replicas"),
                 ev("11:10", "ok", "job batch #4811 done"), ev("10:35", "ok", "job batch #4810 done")] },
    Service { name: "cron", version: "v1.2.0", uptime: "—", status: Stopped, replicas: "0/0", cpu: 0, mem: 0, errs: 0,
        events: [ev("03:00", "ok", "nightly cleanup finished"), ev("02:59", "info", "job started"),
                 ev("Tue", "info", "paused by ops"), ev("Mon", "ok", "deploy v1.2.0 finished")] },
];
