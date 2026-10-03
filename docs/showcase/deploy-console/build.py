#!/usr/bin/env python3
"""Showcase: three concepts for one deploy console, built with mockkit.

Job: ship releases safely - see what is rolling out, spot what is unhealthy, approve or reject what waits
for a human. Data: invented but plausible (7 services, staging and prod), embedded below.

    python3 build.py            # writes the .mock frames next to this file
    python3 build.py --png      # also renders PNGs at 256 and 16 colors into ./png/
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parents[2] / "skills" / "tui-design"   # repo root / skills / tui-design
sys.path.insert(0, str(SKILL / "scripts"))
from mockkit import Canvas, fit, spark  # noqa: E402

CAPS = "attrs=bold,dim,underline,inverse colors=256 glyphs=unicode widgets=list,input source=assumed"
THEME = "catppuccin-mocha"

# Rubric scores read off the PNGs (visual-craft.md#aesthetic-rubric), written into each frame's notes.
SCORES = {
    "feed--normal--120x30": "rubric 256: 15/16 (C8 1) · 16: 15/16 (C8 1)",
    "feed--normal--80x24": "rubric 256: 15/16 (C7 1) · 16: 15/16 (C7 1)",
    "board--normal--120x30": "rubric 256: 15/16 (C1 1) · 16: 14/16 (C1 1, C4 1)",
    "board--normal--80x24": "rubric 256: 15/16 (C7 1) · 16: 14/16 (C4 1, C7 1)",
    "approvals--normal--120x30": "rubric 256: 16/16 · 16: 15/16 (C4 1)",
    "approvals--normal--80x24": "rubric 256: 15/16 (C7 1) · 16: 14/16 (C4 1, C7 1)",
}

# --- data -------------------------------------------------------------------------------------------
# service, team, staging version, prod version, prod state, pods, error-rate series (6h), p95 series (ms)
SERVICES = [
    ("web", "storefront", "v3.18.1", "v3.18.0", "ok", "8/8", [3, 3, 4, 3, 3, 4, 3, 3, 3, 4, 3, 3], 180),
    ("api", "platform", "v2.5.0", "v2.4.1", "ok", "6/6", [4, 5, 4, 4, 5, 4, 4, 5, 4, 4, 4, 5], 240),
    ("worker", "platform", "v1.12.4", "v1.12.4", "ok", "4/4", [1, 1, 2, 1, 1, 1, 2, 1, 1, 1, 1, 1], 90),
    ("payments", "billing", "v1.9.3", "v1.9.2", "warn", "6/6", [4, 4, 5, 4, 6, 9, 12, 14, 16, 17, 18, 18], 412),
    ("search", "discovery", "v0.14.0", "v0.13.2", "rolling", "3/5", [2, 2, 3, 2, 2, 3, 2, 2, 3, 2, 3, 3], 310),
    ("auth", "identity", "v4.2.1", "v4.2.1", "ok", "4/4", [1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1], 60),
    ("notify", "messaging", "v0.8.0", "v0.7.9", "fail", "4/4", [2, 2, 2, 3, 2, 2, 9, 11, 3, 2, 2, 2], 150),
]
SV = [dict(zip(("name", "team", "stg", "prod", "st", "pods", "err", "p95"), s)) for s in SERVICES]

# time, state, service, env, from, to, message, actor
TODAY = [
    ("14:21", "fail", "notify", "prod", "v0.7.9", "v0.8.0", "health check failed on 2 of 4 pods, rolled back", "sam"),
    ("14:05", "todo", "payments", "staging", "v1.9.2", "v1.9.3", "deployed, approval requested for prod", "sam"),
    ("13:58", "todo", "api", "staging", "v2.4.1", "v2.5.0", "deployed, approval requested for prod", "priya"),
    ("13:40", "warn", "payments", "prod", "", "v1.9.2", "error rate 1.8% over the 1.0% alert line", "alerts"),
    ("13:12", "ok", "auth", "prod", "v4.2.0", "v4.2.1", "deployed, approved by priya", "alex"),
    ("12:47", "ok", "worker", "prod", "v1.12.3", "v1.12.4", "deployed, approved by sam", "alex"),
    ("12:30", "ok", "web", "prod", "v3.17.4", "v3.18.0", "deployed, approved by alex", "jordan"),
    ("11:55", "ok", "api", "prod", "v2.4.0", "v2.4.1", "hotfix deployed, approved by sam", "priya"),
    ("11:20", "ok", "search", "staging", "v0.13.2", "v0.14.0", "deployed", "priya"),
    ("10:48", "ok", "notify", "staging", "v0.7.9", "v0.8.0", "deployed", "sam"),
    ("10:02", "ok", "worker", "staging", "v1.12.3", "v1.12.4", "deployed", "alex"),
    ("09:40", "ok", "auth", "staging", "v4.2.0", "v4.2.1", "deployed", "alex"),
]
YESTERDAY = [
    ("18:12", "ok", "payments", "prod", "v1.9.1", "v1.9.2", "deployed, approved by priya", "sam"),
    ("17:30", "ok", "web", "staging", "v3.17.4", "v3.18.0", "deployed", "jordan"),
    ("16:05", "fail", "search", "staging", "v0.13.2", "v0.13.3", "migration timed out, rolled back", "priya"),
    ("15:20", "ok", "auth", "prod", "v4.1.9", "v4.2.0", "deployed, approved by sam", "alex"),
]
ROLLING = [  # service, env, from, to, done pods, total pods, actor, started
    ("search", "prod", "v0.13.2", "v0.14.0", 3, 5, "priya", "4m ago"),
    ("web", "staging", "v3.18.0", "v3.18.1", 1, 2, "jordan", "1m ago"),
]
# service, from, to, env, title, requester, age, approvals (have, need), checks (pass, total, warn)
WAITING = [
    ("payments", "v1.9.2", "v1.9.3", "prod", "fix currency rounding on partial refunds", "sam", "42m", (1, 2), (6, 6, 0)),
    ("api", "v2.4.1", "v2.5.0", "prod", "paginate /v2/orders, drop the legacy cursor", "priya", "18m", (0, 2), (5, 6, 1)),
    ("web", "v3.18.0", "v3.18.1", "prod", "checkout banner behind a feature flag", "jordan", "6m", (0, 1), (3, 6, 0)),
    ("notify", "v0.7.9", "v0.8.1", "prod", "retry the queue client with backoff", "sam", "2m", (0, 2), (1, 6, 0)),
]
DECIDED = [  # state, service, version, who (and why, for a rejection), when
    ("ok", "auth", "v4.2.1", "priya", "13:10"),
    ("ok", "worker", "v1.12.4", "sam", "12:44"),
    ("ok", "web", "v3.18.0", "alex", "12:28"),
    ("fail", "worker", "v1.13.0-rc1", "priya: load test", "11:58"),
    ("ok", "api", "v2.4.1", "sam", "11:52"),
]

META = {"web": "v3.18.1 rolling on staging", "api": "v2.5.0 waits for approval",
        "payments": "v1.9.3 waits for approval", "search": "rolling to prod, 3 of 5 pods",
        "notify": "v0.8.0 failed in prod, rolled back"}


NEXT = {"web": ("●", "status.info", "on staging"), "api": ("◇", "accent.primary", "approval"),
        "payments": ("◇", "accent.primary", "approval"), "search": ("●", "status.info", "3/5 pods"),
        "notify": ("✗", "status.error", "rolled back")}


def series(n, base, peak=None, start=0.6, seed=7):
    """A deterministic noisy series of n points; with peak, it ramps from base to peak after `start`."""
    out, r = [], seed
    for i in range(n):
        r = (r * 1103515245 + 12345) % 2 ** 31
        v = base + (r % 3) - 1
        if peak is not None and i > n * start:
            v += (peak - base) * min(1.0, (i - n * start) / (n * 0.25))
        out.append(max(0, v))
    return out


ST = {"ok": ("✓", "status.success"), "warn": ("▲", "status.warning"), "fail": ("✗", "status.error"),
      "rolling": ("●", "status.info")}
TODO = ("◇", "accent.primary")       # waiting for a human: a to-do in the accent, never an alarm hue
ST["todo"] = TODO


# --- shared helpers -----------------------------------------------------------------------------------
def rule(c, x, y, w, label, count=None, right=None):
    """Section header: bold label, muted count, faint rule to the end of the column, optional right note."""
    end = c.runs(x, y, [(label, "fg.title bold")] + ([(f"  {count}", "fg.muted")] if count is not None else []))
    stop = c.rtext(x + w, y, right, "fg.faint") - 1 if right else x + w
    if stop - end - 1 > 0:
        c.text(end + 1, y, "─" * (stop - end - 1), "border.default")


def header(c, subtitle, right):
    c.band(0, [("deploy", "accent.primary bold"), ("  " + subtitle, "fg.muted")], right, bg=None, pad=2,
           region="header")


def counts(wide):
    out = [("● ", "status.info"), ("2", "fg.default bold"), (" rolling  ", "fg.muted"), (TODO[0] + " ", TODO[1]),
           ("4", "accent.primary bold"), (" to approve  ", "fg.muted"), ("✗ ", "status.error"), ("1", "fg.default bold"),
           (" failed", "fg.muted")]
    return out + ([("  · updated 12s ago", "fg.faint")] if wide else [])


def band_select(c, x, y, w, h=1):
    """A plain band; callers draw the row in selection.fg, so 16-color reverse video gives one even band.
    No accent bar here: blank cells after it would inherit its color and show as an accent block in reverse."""
    c.fill(x, y, w, h, "on:selection.bg")
    for yy in range(y, y + h):
        c.text(x, yy, " " * w, "selection.fg")


def meter(c, x, y, w, done, total, spec="status.info"):
    fill = round(w * done / total)
    return c.runs(x, y, [("━" * fill, spec), ("━" * (w - fill), "fg.faint")])


def reg(c, role, x, y, w, h, title=None):
    rid = f"r{len(c._regions) + 1}"
    c.region(rid, role, x, y, w, h, title)
    return rid


def save(c, name, notes):
    for n in notes + [SCORES[name], "Data is invented for the showcase (services, versions, people)."]:
        c.note(n)
    out = HERE / f"{name}.mock"
    c.save(out)
    return out


def svc(name):
    return next(s for s in SV if s["name"] == name)


# --- concept A: feed / timeline --------------------------------------------------------------------------
def feed(cols, rows):
    c = Canvas(cols, rows, title="deploy — release feed", state="normal", theme=THEME, caps=CAPS)
    wide = cols >= 100
    header(c, "release feed · all services" if wide else "feed", counts(wide))
    x, w = 2, cols - 4
    rule(c, x, 2, w, "Rolling now", len(ROLLING))
    y = 3
    sw, ew, mw = (10, 9, 24) if wide else (9, 8, 12)
    for s, env, frm, to, done, total, who, started in ROLLING:
        e = c.runs(x + 6, y, [("● ", "status.info"), (fit(s, sw), "fg.default bold"), (fit(env, ew), "fg.muted")])
        if wide:
            e = c.runs(e, y, [(frm, "fg.faint"), (" → ", "fg.faint"), (fit(to, 10), "fg.default")])
        e = meter(c, e + 1, y, mw, done, total)
        c.runs(e + 2, y, [(f"{done}/{total}", "fg.default bold"), (" pods", "fg.muted")])
        if wide:
            c.rruns(x + w, y, [(who, "fg.muted"), ("  started " + started, "fg.faint")])
        y += 1
    y += 1
    rule(c, x, y, w, "Today", len(TODAY), right="newest first")
    y += 1
    body_bottom = rows - 2
    rid = reg(c, "list", 1, y, cols - 2, body_bottom - y + 1, "Release feed")
    c.focus(rid)
    rail_x = x + 6

    def event(y, ev, sel=False, day_end=False):
        t, st, s, env, frm, to, msg, who = ev
        g, tok = ST[st]
        if sel:
            band_select(c, 1, y, cols - 2, 3 if wide else 2)
            c.selected_at(rid, y)
        n = "selection.fg" if sel else None
        c.text(x, y, t, n or "fg.faint")
        c.text(rail_x, y, g, n or tok)
        e = c.runs(rail_x + 2, y, [(fit(s, sw), (n or "fg.default") + (" bold" if sel else "")),
                                   (fit(env, ew), n or "fg.muted")])
        if wide:
            vs = f"{frm} → {to}" if frm else to
            e = c.text(e, y, fit(vs, 20), n or "fg.faint")
            mlen = x + w - e - 9
        else:
            e = c.text(e, y, fit(to, 9), n or "fg.faint")
            mlen = x + w - e
        c.text(e, y, fit(msg, mlen), n or ("fg.default" if st in ("fail", "warn") else "fg.muted"))
        if wide:
            c.rtext(x + w, y, who, n or "fg.faint")
        if sel:   # expanded in place: why it failed, what happened next; hanging indent under the service
            lines = (["/healthz returned 503 on pods 2 and 4 after 90s · auto rollback to v0.7.9 done at 14:23",
                      "commit 4f2a91c  switch the queue client to v2 · 7 files · retry is waiting for approval"]
                     if wide else ["503 on 2 of 4 pods · rolled back to v0.7.9 at 14:23"])
            for k, ln in enumerate(lines, 1):
                c.text(rail_x, y + k, "│", "selection.fg")
                c.text(rail_x + 2, y + k, fit(ln, x + w - rail_x - 2), "selection.fg")
            return y + 1 + len(lines)
        return y + 1

    room = body_bottom - y + 1
    extra = 2 if wide else 1
    n_today = min(len(TODAY), room - extra)
    for i, ev in enumerate(TODAY[:n_today]):
        y = event(y, ev, sel=i == 0)
    left = body_bottom - y + 1
    if left >= 3:
        y += 1 if left >= 5 else 0
        rule(c, x, y, w, "Yesterday", len(YESTERDAY))
        y += 1
        for ev in YESTERDAY[:body_bottom - y + 1]:
            y = event(y, ev)
    c.keybar(rows - 1, [("↑↓", "move"), ("enter", "expand"), ("l", "logs"), ("r", "retry"), ("/", "filter"),
                        ("tab", "view")] if wide else [("↑↓", "move"), ("enter", "expand"), ("l", "logs"),
                                                       ("/", "filter")],
             right=[("?", "help"), ("q", "quit")], region="keybar", bg=None)
    return save(c, f"feed--normal--{cols}x{rows}",
                ["Concept A (feed): events newest first; live rollouts pinned on top; the selected event opens in place."])


# --- concept B: dashboard + drill-down -------------------------------------------------------------------
def env_strip(c, x, y, label, key, lw):
    e = c.text(x, y, fit(label, lw), "fg.muted")
    for s in SV:
        st = s["st"] if key == "prod" else ("rolling" if s["name"] == "web" else "ok")
        g, tok = ST[st]
        e = c.text(e, y, g + " ", tok)
    return e


def board(cols, rows):
    c = Canvas(cols, rows, title="deploy — service health", state="normal", theme=THEME, caps=CAPS)
    wide = cols >= 100
    n = {k: sum(s["st"] == k for s in SV) for k in ST}
    right = [("✓ ", "status.success"), (str(n["ok"]), "fg.default bold"), (" healthy  ", "fg.muted"),
             ("▲ ", "status.warning"), (str(n["warn"]), "fg.default bold"), (" degraded  ", "fg.muted"),
             ("✗ ", "status.error"), (str(n["fail"]), "fg.default bold"), (" failed  ", "fg.muted"),
             ("● ", "status.info"), (str(n["rolling"]), "fg.default bold"), (" rolling", "fg.muted")]
    header(c, "service health · prod" if wide else "health", right)
    sel = svc("payments")
    lw = 68 if wide else cols - 4
    x = 2
    # matrix of services: one row per service, prod state in front
    rule(c, x, 2, lw, "Services", len(SV), right="staging → prod")
    hy = 3
    cols_w = [("SERVICE", 10), ("STAGING", 10), ("PROD", 11), ("ERRORS 6h", 18 if wide else 16), ("P95", 7)]
    cols_w.append(("TEAM", 10) if wide else ("NEXT", 14))
    xx = x + 2
    for name, cw in cols_w:
        c.text(xx + (cw - len(name) - 1 if name == "P95" else 0), hy, name, "table.header bold")
        xx += cw
    ty = hy + 1
    per = 2 if wide else 1
    rid = reg(c, "list", 1, ty, lw + 1, len(SV) * per, "Services")
    c.focus(rid)
    for i, s in enumerate(SV):
        y = ty + i * per
        is_sel = s is sel
        if is_sel:
            band_select(c, 1, y, lw + 1, per)
            c.selected_at(rid, y)
        nt = "selection.fg" if is_sel else None
        g, tok = ST[s["st"]]
        xx = x + 2
        c.text(xx, y, fit(s["name"], 10), (nt or "fg.default") + " bold" if is_sel else "fg.default")
        xx += 10
        drift = s["stg"] != s["prod"]
        c.text(xx, y, fit(s["stg"], 10), nt or ("fg.default" if drift else "fg.faint"))
        xx += 10
        c.runs(xx, y, [(g + " ", nt or tok), (fit(s["prod"], 9), nt or "fg.default")])
        xx += 11
        sw = 12 if wide else 10
        pct = s["err"][-1] / 10
        c.runs(xx, y, [(spark(s["err"], lo=0, hi=20)[-sw:], nt or ("status.warning" if s["st"] == "warn" else "fg.muted")),
                       (f"{pct:4.1f}%", (nt or "fg.default") + (" bold" if s["st"] == "warn" else ""))])
        xx += 18 if wide else 16
        c.text(xx, y, f"{s['p95']:>4}ms", nt or "fg.muted")
        xx += 7
        if wide:
            c.text(xx, y, fit(s["team"], 10), nt or "fg.faint")
        else:
            g2, t2, word = NEXT.get(s["name"], (" ", None, "in sync"))
            c.runs(xx, y, [(g2 + " ", nt or t2 or "fg.faint"), (fit(word, 12), nt or ("fg.muted" if t2 else "fg.faint"))])
        if wide:
            meta = f"{s['pods']} pods · " + META.get(s["name"], "in sync")
            c.text(x + 12, y + 1, fit(meta, lw - 12), nt or "fg.faint")
    y = ty + len(SV) * per + 1
    # environment strips: one glyph per service, same order as the rows
    if wide:
        rule(c, x, y, lw, "Environments")
        y += 1
    for label, key in (("staging", "stg"), ("prod", "prod")):
        e = env_strip(c, x + 2, y, label, key, 10)
        summ = "6 ok · 1 rolling" if key == "stg" else "4 ok · 1 degraded · 1 rolling · 1 failed"
        c.text(e + 2, y, summ, "fg.muted")
        y += 1
    y += 1
    if wide:
        rule(c, x, y, lw, "Alerts", 2)
        y += 1
        for st, txt, age in (("warn", "payments prod error rate 1.8%, alert line 1.0%", "52m"),
                             ("fail", "notify prod v0.8.0 failed health checks, rolled back", "21m")):
            c.runs(x + 2, y, [(ST[st][0] + " ", ST[st][1]), (txt, "fg.default")])
            c.rtext(x + lw, y, age, "fg.faint")
            y += 1
    # drill-down: the selected service
    if wide:
        dx, dy, dw, dh = x + lw + 2, 2, cols - (x + lw + 2), rows - 3
    else:
        dx, dy, dw, dh = 0, y, cols, rows - 1 - y
    c.fill(dx, dy, dw, dh, "on:bg.surface")
    reg(c, "detail", dx, dy, dw, dh, sel["name"])
    px, pw = dx + 2, dw - 4
    yy = dy + (1 if wide else 0)
    c.runs(px, yy, [(sel["name"], "fg.title bold"), ("  prod  ", "fg.muted"), ("▲ ", "status.warning"),
                    ("degraded", "status.warning bold")])
    c.rtext(px + pw, yy, sel["team"] + " team", "fg.faint")
    yy += 2 if wide else 1
    if wide:
        yy = c.kv(px, yy, [("version", [("v1.9.2", "fg.default"), ("  since yesterday 18:12", "fg.faint")]),
                           ("next", [(TODO[0] + " ", TODO[1]), ("v1.9.3", "fg.default"), ("  waits for 1 more approval", "fg.muted")]),
                           ("pods", [("6/6", "fg.default"), (" ready", "fg.muted")])], key_w=9, w=pw, key_spec="fg.faint")
        yy += 1
        c.runs(px, yy, [("Error rate", "fg.title bold"), ("  6h", "fg.faint")])
        c.rruns(px + pw, yy, [("1.8%", "status.warning bold"), ("  alert 1.0%", "fg.faint")])
        yy += 1
        c.text(px, yy, spark(series(pw, 4, 18), lo=0, hi=20), "status.warning")
        yy += 2
        c.runs(px, yy, [("p95 latency", "fg.title bold"), ("  6h", "fg.faint")])
        c.rruns(px + pw, yy, [("412 ms", "fg.default bold"), ("  was 240", "fg.faint")])
        yy += 1
        c.text(px, yy, spark(series(pw, 6, 13, seed=3), lo=0, hi=16), "fg.muted")
        yy += 2
        rule(c, px, yy, pw, "Recent deploys", 3)
        yy += 1
        for st, ver, when, who in (("ok", "v1.9.2", "yesterday 18:12", "sam"), ("ok", "v1.9.1", "3 days ago", "sam"),
                                   ("fail", "v1.9.0", "4 days ago, rolled back", "priya")):
            c.runs(px, yy, [(ST[st][0] + " ", ST[st][1]), (fit(ver, 8), "fg.default"), (when, "fg.muted")])
            c.rtext(px + pw, yy, who, "fg.faint")
            yy += 1
        yy += 1
        rule(c, px, yy, pw, "Next", "v1.9.3 on staging")
        yy += 1
        c.runs(px, yy, [("✓ ", "status.success"), ("6/6 checks", "fg.default"), ("  errors 0.2%  p95 380 ms", "fg.muted")])
        yy += 1
        c.runs(px, yy, [("●○", "accent.primary"), (" 1 of 2 approvals", "fg.default"), ("  priya approved 20m ago", "fg.faint")])
        yy += 2
        c.text(px, yy, fit("errors rose at 13:12, after auth v4.2.1 shipped", pw), "fg.muted")
    else:
        c.runs(px, yy, [("errors ", "fg.muted"), (spark(sel["err"], lo=0, hi=20), "status.warning"), (" 1.8%", "status.warning bold"),
                        ("  alert 1.0%", "fg.faint"), ("   p95 ", "fg.muted"), ("412 ms", "fg.default bold")])
        yy += 1
        c.runs(px, yy, [("next  ", "fg.muted"), (TODO[0] + " ", TODO[1]), ("v1.9.3", "fg.default"),
                        ("  waits for 1 more approval", "fg.muted")])
        yy += 1
        c.runs(px, yy, [("last  ", "fg.muted"), ("✓ ", "status.success"), ("v1.9.2", "fg.default"),
                        ("  yesterday 18:12 by sam", "fg.faint")])
        yy += 2
        c.runs(px, yy, [("v1.9.3 on staging  ", "fg.muted"), ("✓ ", "status.success"), ("6/6 checks", "fg.default"),
                        ("  errors 0.2%  ", "fg.muted"), ("●○", "accent.primary"), (" 1 of 2 approvals", "fg.muted")])
        yy += 1
        c.text(px, yy, "errors rose at 13:12, after auth v4.2.1 shipped", "fg.faint")
    c.keybar(rows - 1, [("↑↓", "service"), ("enter", "open"), ("e", "staging/prod"), ("l", "logs"),
                        ("a", "approvals")] if wide else [("↑↓", "service"), ("enter", "open"), ("l", "logs")],
             right=[("?", "help"), ("q", "quit")], region="keybar", bg=None)
    return save(c, f"board--normal--{cols}x{rows}",
                ["Concept B (dashboard): services × environments with health first; the selected service drills down."])


# --- concept C: approval queue ----------------------------------------------------------------------------
def pips(have, need):
    return "●" * have + "○" * (need - have)


def approvals(cols, rows):
    c = Canvas(cols, rows, title="deploy — approvals", state="normal", theme=THEME, caps=CAPS)
    wide = cols >= 100
    header(c, "approvals waiting for you" if wide else "approvals",
           [(TODO[0] + " ", TODO[1]), (str(len(WAITING)), "accent.primary bold"), (" waiting  ", "fg.muted"),
            ("oldest ", "fg.muted"), ("42m", "fg.default bold")]
           + ([("  ✓ ", "status.success"), ("4", "fg.default bold"), (" approved today", "fg.muted")] if wide else []))
    lw = 52 if wide else 34
    lx = 1
    cx = lx + lw + 1
    h = 3 if wide else 2
    rule(c, lx + 1, 2, lw - 1, "Waiting", len(WAITING), right="oldest first")
    y = 3
    rq = reg(c, "list", lx, y, lw, len(WAITING) * (h + 1) - 1, "Waiting")
    c.focus(rq)
    for i, (s, frm, to, env, title, who, age, (have, need), (ok, tot, warn)) in enumerate(WAITING):
        sel = i == 0
        if sel:   # the selected card continues into the detail surface: one shape, no box
            c.fill(lx, y, cx - lx, h, "on:bg.surface")
            for yy in range(y, y + h):
                c.text(lx, yy, "▌", "accent.primary")
            c.selected_at(rq, y)
        tx = lx + 2
        c.runs(tx, y, [(TODO[0] + " ", TODO[1]), (s, "fg.default bold" if sel else "fg.default"),
                       ("  " + (f"{frm} → {to}" if wide else to), "fg.muted")])
        c.rruns(lx + lw - 1, y, [(env, "fg.muted")] + ([("  " + age, "fg.faint")] if wide else []))
        c.text(tx + 2, y + 1, fit(title, lw - 5), "fg.default" if sel else "fg.muted")
        if wide:
            chk = ([("▲ ", "status.warning"), (f"{tot - warn}/{tot} checks, 1 warning", "fg.muted")] if warn else
                   [("✓ ", "status.success"), (f"{ok}/{tot} checks", "fg.muted")] if ok == tot else
                   [("● ", "status.info"), (f"{ok}/{tot} checks running", "fg.muted")])
            c.runs(tx + 2, y + 2, [(who, "fg.faint"), ("  ", None), (pips(have, need), "accent.primary"),
                                   (f" {have}/{need} approvals  ", "fg.faint")] + chk)
        y += h + 1
    rule(c, lx + 1, y, lw - 1, "Decided today", len(DECIDED))
    y += 1
    for st, s, ver, what, when in DECIDED[:rows - 2 - y]:
        c.runs(lx + 3, y, [(ST[st][0] + " ", ST[st][1]), (fit(s, 9), "fg.default"), (fit(ver, 12), "fg.faint")])
        if wide:
            c.text(lx + 27, y, fit(what, lw - 34), "fg.muted")
        c.rtext(lx + lw - 1, y, when, "fg.faint")
        y += 1

    # detail surface: the selected request
    s, frm, to, env, title, who, age, (have, need), _ = WAITING[0]
    top, bottom = 2, rows - 2
    c.fill(cx, top, cols - cx, bottom - top + 1, "on:bg.surface")
    reg(c, "detail", cx, top, cols - cx, bottom - top + 1, f"{s} {to}")
    x, w = cx + 2, cols - cx - 4
    y = top + 1
    c.runs(x, y, [(s, "fg.default bold"), (" › ", "fg.faint"), (env, "fg.default"), (" › ", "fg.faint"),
                  (frm, "fg.muted"), (" → ", "fg.faint"), (to, "fg.default bold")])
    if wide:
        c.rtext(x + w, y, "release r-2291", "fg.faint")
    y += 2 if wide else 1
    c.text(x, y, fit(title, w), "fg.title bold")
    y += 1
    c.text(x, y, fit(f"{'requested by ' if wide else ''}{who} · {age} ago · on staging since 14:05", w), "fg.muted")
    y += 2
    rule(c, x, y, w, "Approvals", f"{have} of {need}")
    y += 1
    c.runs(x, y, [("✓ ", "status.success"), (fit("priya", 9), "fg.default"), ("approved 20m ago", "fg.faint")])
    y += 1
    c.runs(x, y, [(TODO[0] + " ", TODO[1]), (fit("you", 9), "fg.default bold"), ("your call", "accent.primary")])
    y += 2
    checks = [("unit", "412 passed"), ("integration", "38 passed"), ("lint", "clean"), ("migration", "dry run ok"),
              ("canary 5%", "30m, errors 0.2%"), ("security", "no findings")]
    rule(c, x, y, w, "Checks", "6/6")
    y += 1
    if wide:
        half = w // 2
        for k, (name, res) in enumerate(checks):
            xx = x + (k % 2) * half
            c.runs(xx, y + k // 2, [("✓ ", "status.success"), (fit(name, 12), "fg.default"), (fit(res, half - 15), "fg.faint")])
        y += 4
    else:
        c.runs(x, y, [("✓ ", "status.success"), ("unit · integration · lint", "fg.muted")])
        y += 1
        c.runs(x, y, [("✓ ", "status.success"), ("migration · canary · security", "fg.muted")])
        y += 2
    files = [("src/refunds/rounding.py", 120, 41), ("src/refunds/test_rounding.py", 74, 12),
             ("migrations/0042_refund_scale.sql", 14, 0), ("docs/refunds.md", 6, 34)]
    rule(c, x, y, w, "Changes", "12 commits · +214 −87" if wide else "+214 −87")
    y += 1
    nf = len(files)
    pw = w - 15 if wide else w - 11
    bw = 10 if wide else 6
    for path, add, rem in files[:nf]:
        tot = add + rem
        a = max(1, round(bw * add / 160)) if add else 0
        r = max(1, round(bw * rem / 160)) if rem else 0
        c.text(x, y, fit(path, pw - bw - 1, side="start"), "fg.muted")
        c.runs(x + pw - bw, y, [("■" * a, "diff.added"), ("■" * r, "diff.removed")])
        c.rruns(x + w, y, [(f"+{add}", "diff.added")] + ([(f" −{rem}", "diff.removed")] if rem else []))
        y += 1
    iy = bottom - 1
    c.text(x, iy - 1, "Note for the requester" if wide else "Note", "fg.muted")
    c.fill(x, iy, w, 1, "on:bg.raised")
    c.text(x, iy, " " * w, "fg.faint underline")
    c.text(x + 1, iy, "optional; required to reject", "fg.faint underline")
    reg(c, "input", x, iy, w, 1, "Note")
    if wide:
        y += 1
        c.runs(x, y, [("1 migration", "fg.default"), (fit(" adds a column, no rewrite · rollback: v1.9.2", w - 11), "fg.faint")])
    c.keybar(rows - 1, [("↑↓", "request"), ("a", "approve"), ("x", "reject"), ("d", "full diff"), ("n", "note"),
                        ("l", "staging logs")] if wide else [("↑↓", "request"), ("a", "approve"), ("x", "reject"),
                                                             ("d", "diff")],
             right=[("?", "help"), ("q", "quit")], region="keybar", bg=None)
    return save(c, f"approvals--normal--{cols}x{rows}",
                ["Concept C (queue): requests waiting for a human as cards; the selected card joins its evidence."])


def render(paths):
    png = HERE / "png"
    png.mkdir(exist_ok=True)
    for p in paths:
        for depth in ("256", "16"):
            ansi = png / f"{p.stem}--{depth}.ansi"
            subprocess.run([sys.executable, str(SKILL / "scripts/render_mockup.py"), str(p), "--depth", depth,
                            "-o", str(ansi)], check=True)
            subprocess.run([sys.executable, str(SKILL / "scripts/ansi_render.py"), str(ansi), "--format", "png",
                            "--quantize", "--title", f"{p.stem} · {depth} colors", "-o",
                            str(png / f"{p.stem}--{depth}.png")], check=True)
            ansi.unlink()


if __name__ == "__main__":
    out = [build(*size) for size in ((120, 30), (80, 24)) for build in (feed, board, approvals)]
    for p in out:
        print(p.name)
    if "--png" in sys.argv:
        render(out)
