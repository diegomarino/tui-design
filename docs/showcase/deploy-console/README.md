# Showcase: deploy console, three concepts

Worked example for the skill's [visual-craft.md](../../../skills/tui-design/references/visual-craft.md): one job
reframed into three concepts with different anchors, each frame at 120x30 and 80x24, rendered at 256 and 16 colors
and scored with the rubric. The skill describes this example in words; the frames, the generator and the PNGs live
here, outside the installed folder.

- **Job.** Ship releases safely: see what is rolling out (often, at a glance), spot what is unhealthy (any time),
  approve or reject what waits for a human (several times a day, one at a time).
- **Data.** Invented but plausible: 7 services, staging and prod, 4 requests waiting, 12 events today. Every
  frame says so in a `#! note:`; a real design fills the frames from a snapshot of the real system.
- **Capability profile.** `#! caps: attrs=bold,dim,underline,inverse colors=256 glyphs=unicode source=assumed`.
  A free-standing full-screen app has no host to measure, so the profile is assumed (italic left out, 256 colors
  as the floor of a modern terminal) and `--check` warns about it on purpose. Before building, run
  `python3 skills/tui-design/scripts/test_card.py` in the terminals the team uses and change `source=` to `test-card`.
- **Build.** `python3 docs/showcase/deploy-console/build.py --png` (from the repository root) writes the six
  `.mock` frames here and the PNGs into `png/` (`<frame>--256.png`, `<frame>--16.png`). The rubric scores live
  in `build.py` (`SCORES`) and land in each frame's notes.

| Concept | Anchor | Signature | Makes fast | Makes slow | Rubric 256 / 16 (120x30 · 80x24) |
|---|---|---|---|---|---|
| **A. Feed** (`feed--*`) | events, newest first; the selected event opens in place with its cause | live rollouts pinned above the timeline as meters (`━━━━━━──── 3/5 pods`) | "what changed, and when"; reading a failure in context | comparing services; acting on a backlog | 15/15 · 15/15 |
| **B. Board** (`board--*`) | services × environments with prod health first; the selected service drills down | the staging/prod strip (one glyph per service) plus error and latency sparklines | "is everything OK?"; finding the degraded service | the history behind a change | 15/14 · 15/14 |
| **C. Approvals** (`approvals--*`) | requests waiting for a human, as cards; the selected card joins a surface with its evidence | the joined card, approval pips `●○ 1/2`, diff bars | approving or rejecting with the checks, diff and staging data on one screen | seeing system health | 16/15 · 15/14 |

Recommendation: **C** as the home screen for the people who approve, with **B** behind one key (`tab`) for health
and A's expanded event as the detail view of a failure. Approving is the verb that needs a human; health and
history support it.

Open decisions the frames invent: whether one approval may come from the requester's own team; whether a note is
required to reject (the frames say yes); what "degraded" means (the frames use an error-rate alert line of 1.0%);
whether `r` in the feed retries a failed rollout directly or files a new approval request.
