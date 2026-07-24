# Autopilot — autonomous target selection

When `/prospect` runs with **no input** (or input `auto`), don't ask for
keywords — choose the next targets here, act, and log why.

**Weekly rhythm:** Mon/Wed/Fri = new prospecting (this file). Tue/Thu =
follow-ups to non-repliers (`config/followups.md`), not new prospecting.

## Per-run budget
- **2 segments** per run (a segment = one industry × one Triangle sub-market).
- ~8–10 companies per segment (~15–20 companies total); pull every useful
  contact per company, not just decision-makers (see SKILL.md Step 3).
- Hard stop: don't enrich a 3rd segment in one run (ZoomInfo credit control).

## The universe
- **Core industries** (bread-and-butter): home services, healthcare, auto,
  legal/financial.
- **Expansion industries** (proven or promising): sports, hospitality &
  restaurants, commercial real estate, banking/wealth, insurance, med spa.
- **Triangle sub-markets:** Chapel Hill/Carrboro · Durham · Raleigh ·
  Cary/Apex/Morrisville · Wake Forest/North Raleigh · Hillsborough/Graham.

## How to pick the 2 segments (priority order)
1. **Dedupe first.** Load `tracker/prospects.csv`. Never re-pull a company
   already there (match on company name / ZoomInfo ID). Skip a segment that's
   already well-covered (≥6 companies logged in the last ~60 days).
2. **Double down on what's working.** If any industry has contacts at
   `Interested: 50%` or better in the tracker, make **one** of the two
   segments that industry in an uncovered sub-market — warm categories earn
   more at-bats.
3. **Breadth rotation.** Fill the other segment with the **least-recently-
   covered** core industry × sub-market, so coverage spreads evenly.
4. **Explore occasionally.** Roughly every 3rd–4th run, make one segment a
   new expansion industry we haven't tried, to find new veins (this is how
   "sports" got discovered).
5. **Never re-target** anyone marked `Not Interested: 0%`.

## Write down the reasoning (every run)
Before pulling data, append one line to `tracker/autopilot-log.md`:
`YYYY-MM-DD | seg1: <industry> / <submarket> · seg2: <industry> / <submarket> | why: <one sentence>`
Then run the normal pipeline (SKILL.md Steps 0–8) for both segments.

## Draft policy
Auto-create Gmail drafts for every A/B contact (**never send**), following
`config/voice.md`.
**Gate:** keep auto-drafting OFF until Tyler signs off on the email voice.
Until then, autopilot still fills the tracker and stages finished drafts in
`outbox/` for review. Flip the scheduled Routine on once the voice is locked.

## Guardrails
- Stay in the Triangle unless told otherwise.
- If a segment returns nothing, widen one filter once (drop employee minimum /
  widen metro to state), then move on and note it.
- Respect the ZoomInfo credit rules in SKILL.md (batch enrichments; never
  re-enrich companies/contacts already in the tracker).
