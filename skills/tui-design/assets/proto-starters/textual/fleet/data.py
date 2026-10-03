"""Mock data for the Fleet demo screen (same text as assets/demo/fleet--normal--80x24.mock)."""
from dataclasses import dataclass

CONTEXT = "prod-eu · 12:04:31"
MESSAGE = ("deployed api-gateway v2.4.1", " · 2m ago")


@dataclass(frozen=True)
class Event:
    time: str
    kind: str  # ok | warn | info | error
    text: str


@dataclass(frozen=True)
class Service:
    name: str
    status: str  # running | degraded | failed | stopped
    replicas: str
    version: str
    uptime: str
    cpu: int
    mem: int
    err: int
    events: tuple[Event, ...]


SERVICES = (
    Service("api-gateway", "running", "3/3", "v2.4.1", "6d 4h", 31, 68, 92, (
        Event("12:01", "ok", "deploy v2.4.1 finished"),
        Event("11:58", "warn", "p95 latency 820 ms"),
        Event("11:40", "info", "scaled 2 → 3 replicas"),
        Event("11:02", "error", "health check timeout"),
    )),
    Service("auth", "running", "2/2", "v1.9.0", "12d 2h", 12, 41, 3, (
        Event("11:47", "ok", "rotated signing keys"),
        Event("09:15", "info", "scaled 1 → 2 replicas"),
    )),
    Service("billing", "degraded", "1/2", "v3.1.0", "1d 7h", 74, 82, 17, (
        Event("12:03", "warn", "replica 2 not ready"),
        Event("11:55", "warn", "queue depth 4.2k"),
        Event("10:20", "ok", "deploy v3.1.0 finished"),
    )),
    Service("search", "failed", "0/2", "v0.8.2", "0m", 0, 0, 100, (
        Event("12:02", "error", "crash loop (exit 137)"),
        Event("12:00", "error", "out of memory"),
        Event("11:30", "ok", "index rebuilt"),
    )),
    Service("worker", "running", "4/4", "v5.0.3", "6d 4h", 58, 52, 1, (
        Event("12:04", "ok", "drained 128 jobs"),
        Event("11:10", "info", "scaled 3 → 4 replicas"),
    )),
    Service("cron", "stopped", "0/0", "v1.2.0", "—", 0, 0, 0, (
        Event("08:00", "info", "paused by ops"),
    )),
)
