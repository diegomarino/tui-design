# Audit — {{App or screen name}} ({{YYYY-MM-DD}})

<!--
Template: copy into the working directory (ask before writing into the user's repository; then
<project>/docs/tui/audit-<date>.md) and fill it in. Delete these comments and any section that has no content
(say "none" in §3, §4 and §9 rather than deleting them).
Read this when: writing up the judge step of references/audit-protocol.md §7, or a mock review (audit-quick.md §0:
cite frame files and #! region ids instead of description ids; drop the Fidelity and Calibration rows).
Shape: what the screen shows → findings with evidence → rendering bugs (not style) → likely mechanism → root
causes → fixes. Rules:
- Recommendation first: the report opens with the change to make; every finding opens with its fix, then the evidence.
- Findings follow audit-quick.md "Order findings by user harm".
- Every finding cites a checklist id (audit-checklist.md) plus region/element ids from the description, and
  quotes the evidence (text, bbox, token, ratio). A finding without an id is not admissible.
- Every fix names what it requires (an attribute, colour depth, glyph level, widget, key) so it can be checked
  against the host's capability profile (TC-10).
- Section 1 is neutral (taken from the description). Judgment starts at §2.
- Bugs and style issues stay separate. A bug needs a mechanism and a reproduction command.
-->

| Field | Value |
|---|---|
| Subject | {{command line (live capture) or image file (screenshot)}} |
| Product shape | {{full-screen app · inline picker · one-shot CLI · plugin inside a host (name it)}} |
| Capability profile | {{`#! caps:` line or host limits; "unknown: asked the user"}} |
| Framework / version | {{e.g. Ink 7.1.1 + React 19.2; unknown}} |
| Perception path | {{live capture: capture_tui.sh / screenshot: prep_screenshot.py, describer model X, prompts from describe_prompt.py, n schema retries / mock review}} |
| Sizes × states audited | {{120x30 normal, 80x24 normal, 60x24 normal, 80x24 empty}} |
| Theme(s) | {{theme_guess (residual, bg_match) or chosen theme ids; light theme used for CA-09; "no theme fit: raw colours, token checks n/a"}} |
| Description files | {{audit/<variant>--<state>--<size>/description.json …}} |
| Fidelity | {{text 99.6% / bg 100% of cells (live capture cell diff) · screenshot: visual pass, 1 re-crop of region r3}} |
| Calibration | {{screenshot only: score_description.py result + date, or "not calibrated for this screen kind"}} |
| Checklist coverage | {{n pass · n fail · n n/a · n unverifiable (after one targeted re-description each)}} |

**Recommendation:** {{the one to three changes that matter most, in the imperative, each with its F-id: "Separate the delivery marker from the review verdict (F1); fold the 8 identical error rows (F3)." Then whether to mock a redesign before fixing piecemeal.}}

## 1. What the screen shows

<!-- One subsection per screen/state. List regions in reading order with ids and roles, the key content,
     and the focus/selection state as recorded. Quote text verbatim. No adjectives of quality. -->

### {{Screen}} — {{state}} @ {{cols}}x{{rows}}

- `r1` header (y=0): {{" Fleet │ 1 Services  2 Logs  3 Config … prod-eu · 12:04:31"}}
- `r2` list "Services (6)", focused ({{evidence}}): 6 rows; `e201` selected ({{evidence}})
- `r3` detail "api-gateway": {{label/value lines, 3 gauges, "Recent events" with 4 rows}}
- `r4` statusbar: {{message line}} · `r5` keybar: {{n}} hints, left group {{…}}, right group {{…}}
- Uncertain or volatile: {{u-ids / volatile boxes, or "none"}}

## 2. Findings, ordered by user harm

<!-- One row per failed check per location. Order: harm tier (audit-quick.md "Order findings by user harm"),
     blockers first, then M before m inside a tier, then check id.
     Fix first: the change to make, in the imperative. Requires = what the fix needs from the host or framework
     ("nothing", "italic", "256 colours", "a second pane", "a text-input widget").
     Kind: bug = output differs from what the code meant to draw; style = drawn as intended, breaks a rule.
     Where = screen/state/size + ids. Evidence = quoted values. Details go in §5 and §6. -->

| # | Fix (do this) | Tier | Check | Sev | Kind | Where | Evidence | Requires |
|---|---|---|---|---|---|---|---|---|
| F1 | per-cell truncation: every cell has a width and truncates (B1) | 3 width | DA-02 | B | bug | Activity/normal/120x40 · `e412` | row 17 = `… 25 older not shownOST /api/orders/:id/refund must reject ex… · 15h ago` (two logical rows on one line) | nothing |
| F2 | show the review verdict in its own word and colour; `[OK]` only for delivery | 4 truth | ST-10 | M | style | Review/normal/120x30 · `e305` | `[OK] Independent review BLOCK…` | nothing |
| F3 | selected row: use `selection.fg` for every span | 7 contrast | CA-06 | M | style | Fleet/normal/80x24 · `e207` span 19..25 | `fg.faint #7f849c` on `selection.bg #3b3d4f` = 2.89:1 (floor 3.0) | nothing |
| F{{n}} | {{…}} | {{tier}} | {{id}} | {{B/M/m}} | {{bug/style}} | {{…}} | {{…}} | {{…}} |

## 3. Keep (what works)

<!-- What already works and must survive the fixes and any redesign, with evidence ids. A redesign that drops one
     of these must say so and why (checklist MR-03). Examples: "selection marker ❯ e201 carries FS-03 at 1.54:1 bg
     contrast"; "key-hint grammar is uniform across 3 screens, ID-03 pass"; "zebra striping in r4 (wide table, 25-col
     gap) keeps rows traceable"; "explicit fresh/stale/unknown evidence words, ST-07 pass". -->

- {{…}}

## 4. Open decisions

<!-- Behaviour the recommendations or a redesign invent that the current code or host may not support, and choices
     only the user can make. One line each: the decision, the options, what each needs (code, data, host capability).
     Examples: "fold non-consecutive repeats into ×N? needs grouping by event key in the model"; "60-column split:
     list-only fallback or the too-small message?"; "italic for staged names: needs a host with italic; else bold". -->

- {{decision — options — what it needs}}

## 5. Rendering bugs (bugs, not style)

<!-- Number them B1, B2… Quote the corrupted output literally. Give the likely mechanism with the evidence
     that supports it (which rows sit next to it, which width, which framework behaviour), the fix in the
     target framework's vocabulary, and the exact command that reproduces it. "Reproduce before declaring fixed." -->

**B1. {{Merged line}}** ({{F1}}; checks DA-02, FR-01)
- Observed: `{{literal text}}` at {{screen/state/size, row y, ids}}.
- Likely mechanism: {{e.g. rows built as one <Text> exceed the terminal width; the terminal wraps the overflow and
  Ink's line accounting drifts, so the next erase/repaint lands one row off. All artifacts sit next to over-width rows.}}
- Fix: {{e.g. every row = <Box> cells with width + wrap="truncate"; fixed cells flexShrink={0}}}.
- Reproduce: `{{SKILL_DIR/scripts/capture_tui.sh -s 120x40 -k … -o audit/repro/ -- /abs/app}}`, then check `ST` row widths (DA-02).

## 6. Style and design issues

<!-- Group by harm tier, in the same order as §2. For each: the fix first, then the problem in one sentence,
     the evidence ids, and why it matters for the screen's main question. Merge findings with one root cause. -->

### {{Tier, e.g. 5 Clutter}}
- **{{Fix}}** ({{F-ids}}): {{problem in one sentence with evidence}}.

## 7. Root causes (implementation level)

<!-- When source is available: file:line for each cause. Typical causes: single-string rows with hand padding
     (no cells, no truncation); String.length instead of cell width; fixed constants instead of terminal size;
     no shared theme (colours/glyphs inlined per view); missing chrome (no header context, footer without help). -->

1. **{{Cause}}**: {{file:line …}}. Explains {{F-ids}}.

## 8. Fix plan mapped to framework vocabulary

<!-- Use the generic concept ids from references/vocabulary.md and the target framework's names from
     references/frameworks/<fw>.md. Fill only the column for the target framework; delete the others. -->

| Fixes | Concept | Change | {{Ink}} | {{Textual}} | {{Bubble Tea + Lip Gloss}} | {{Ratatui}} |
|---|---|---|---|---|---|---|
| F1, F4 | table / layout container | rows become fixed-width cells that truncate | `<Box width={n} flexShrink={0}><Text wrap="truncate">` | `DataTable` / `Horizontal` + `width` | `lipgloss.NewStyle().Width(n).MaxWidth(n)` | `Table` with `Constraint::Length(n)` |
| F3 | theme / style | selected row: all spans use `selection.fg` | {{…}} | {{…}} | {{…}} | {{…}} |

Work order follows §2 (user harm). Theme/token fixes often close many findings at once
(see [design-system.md](design-system.md)); do them early inside their tier. When the findings are structural
(tiers 1, 4, 5, 6 dominate), mock the redesign first (branch A) and audit the result after it is built.

## 9. Not verifiable / tentative

<!-- Checks still unverifiable after their one targeted re-description, checks marked n/a for lack of evidence
     (behaviour on a screenshot; token checks with no theme fit), and findings that rest on uncertain fields
     ([?], uncertainties[], low confidence). For each: what fact is missing, what was tried, what would settle it. -->

| Check | Status | Why not verified | Tried | What would settle it |
|---|---|---|---|---|
| {{ID-05}} | {{n/a}} | {{screenshot only: key behaviour not observable}} | {{—}} | {{live capture: cap+k r}} |
| {{FS-03}} | {{unverifiable}} | {{r3 rows carry no state evidence}} | {{pass-2 re-crop of r3 with "also report the selected row"}} | {{live capture}} |

## 10. Severity summary

| | bug | style | total |
|---|---|---|---|
| Blocker | {{n}} | {{n}} | {{n}} |
| Major | {{n}} | {{n}} | {{n}} |
| Minor | {{n}} | {{n}} | {{n}} |

Blockers: {{F-ids, one line each}}.
